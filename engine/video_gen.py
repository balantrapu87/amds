"""
Wan 2.1 text-to-video generation via local ComfyUI (127.0.0.1:8080/comfyui).

- Clip planning: full 81-frame (5.06s @ 30fps) clips plus a tail that is the
  smallest 4n+1 length covering the remainder (Wan latents require 4n+1 frames).
- Workflow builder: validated 8-node API graph (UNET/CLIP/VAE loaders,
  EmptyHunyuanLatentVideo, positive/negative CLIPTextEncode, KSampler,
  VAEDecode, SaveWEBM + SaveAnimatedWEBP).
- Retry policy: 3 attempts on the 14B primary, then 3 on the 1.3B fallback,
  then a hard VideoGenError. A process-wide lock guarantees single-flight
  generation (one ComfyUI prompt at a time).
- Output: fetched WEBP frames converted to H.264 MP4 at the job fps.
"""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

FULL_CLIP_FRAMES = 81  # 5.06s @ 30fps — Wan's longest 4n+1 length

DEFAULT_MODEL = os.environ.get("WAN_MODEL", "wan2.1_t2v_14B_fp8_e4m3fn.safetensors")
FALLBACK_MODEL = os.environ.get("WAN_FALLBACK_MODEL", "wan2.1_t2v_1.3B_fp16.safetensors")

_NEGATIVE_PROMPT = (
    "Bright tones, overexposed, static, blurred details, subtitles, style, works, "
    "paintings, images, static, overall gray, worst quality, low quality, JPEG "
    "compression residue, ugly, incomplete, extra fingers, poorly drawn hands, "
    "poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, "
    "still picture, messy background, three legs, many people in the background, "
    "walking backwards"
)

# Serializes all ComfyUI generation: one prompt at a time.
_GEN_LOCK = threading.Lock()


class VideoGenError(RuntimeError):
    """Raised when Wan video generation exhausts its retry budget."""


def plan_clips(scene_seconds: float, fps: int = 30) -> List[int]:
    """Split a scene duration into Wan-compatible 4n+1 clip lengths.

    Uses as many full 81-frame clips as possible; the remainder is covered by
    the smallest 4n+1 length (5..81) that is >= the remainder.
    """
    total_frames = max(1, int(round(scene_seconds * fps)))
    clips: List[int] = []
    remaining = total_frames
    while remaining > 0:
        if remaining <= FULL_CLIP_FRAMES:
            tail = next(f for f in range(5, FULL_CLIP_FRAMES + 1, 4) if f >= remaining)
            clips.append(tail)
            break
        clips.append(FULL_CLIP_FRAMES)
        remaining -= FULL_CLIP_FRAMES
    return clips


def latent_size(job_width: int, job_height: int) -> tuple[int, int]:
    """Map job aspect to Wan's native latent sizes (16:9 -> 1216x704)."""
    if job_width >= job_height:
        return (1216, 704)
    return (704, 1216)


def build_workflow(
    prompt: str,
    width: int,
    height: int,
    length: int,
    seed: int,
    model: str,
    filename_prefix: str,
) -> Dict[str, Any]:
    """Build the ComfyUI API-format Wan 2.1 T2V workflow (8 generation nodes)."""
    if length % 4 != 1 or not (5 <= length <= 81):
        raise VideoGenError(f"Invalid latent length {length}: must be 4n+1 in [5, 81]")
    return {
        "37": {"class_type": "UNETLoader", "inputs": {"unet_name": model, "weight_dtype": "default"}},
        "38": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "39": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "40": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": width, "height": height, "length": length, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["38", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": _NEGATIVE_PROMPT, "clip": ["38", 0]}},
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed, "steps": 40, "cfg": 6.0,
                "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0,
                "model": ["37", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["40", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["39", 0]}},
        "47": {"class_type": "SaveWEBM", "inputs": {"filename_prefix": filename_prefix, "codec": "vp9", "fps": 16.0, "crf": 20.0, "images": ["8", 0]}},
        "28": {"class_type": "SaveAnimatedWEBP", "inputs": {"filename_prefix": filename_prefix, "fps": 16, "lossless": False, "quality": 90, "method": "default", "images": ["8", 0]}},
    }


class WanClient:
    """Thin ComfyUI API client (prompt -> history -> view)."""

    def __init__(self, base_url: str, timeout: float = 600.0, transport: Optional[httpx.BaseTransport] = None) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def submit(self, workflow: Dict[str, Any]) -> str:
        resp = self._http.post("/prompt", json={"prompt": workflow})
        resp.raise_for_status()
        return resp.json()["prompt_id"]

    def wait(self, prompt_id: str, poll_interval: float = 2.0, timeout: float = 3600.0) -> Dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = self._http.get(f"/history/{prompt_id}")
            resp.raise_for_status()
            entry = resp.json().get(prompt_id)
            if entry:
                if entry.get("status") == "error":
                    raise VideoGenError(f"ComfyUI prompt failed: {entry.get('status_message', 'unknown')}")
                return entry
            time.sleep(poll_interval)
        raise VideoGenError(f"ComfyUI poll timeout after {timeout}s for {prompt_id}")

    def fetch_file(self, filename: str, out_path: Path, subfolder: str = "") -> Path:
        resp = self._http.get(
            "/view",
            params={"filename": filename, "subfolder": subfolder, "type": "output"},
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        return out_path

    def close(self) -> None:
        self._http.close()


def convert_to_mp4(webp_path: Path, out_path: Path, fps: int) -> Path:
    """Transcode an animated WEBP into H.264 MP4 at the job frame rate."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(webp_path),
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_path.exists():
        raise VideoGenError(f"ffmpeg conversion failed: {proc.stderr[-300:]}")
    return out_path


def generate_clip(
    client: WanClient,
    prompt: str,
    job_width: int,
    job_height: int,
    frames: int,
    seed: int,
    out_path: str,
    fps: int = 30,
    model: Optional[str] = None,
) -> Path:
    """Generate one Wan clip and return the path of its MP4."""
    model = model or DEFAULT_MODEL
    width, height = latent_size(job_width, job_height)
    out = Path(out_path)
    workflow = build_workflow(prompt, width, height, frames, seed, model, out.stem)

    prompt_id = client.submit(workflow)
    entry = client.wait(prompt_id)
    saved = entry.get("outputs", {}).get("28")
    if not saved or "filename" not in saved:
        raise VideoGenError("ComfyUI finished without a SaveAnimatedWEBP output.")

    webp_path = out.with_suffix(".webp")
    client.fetch_file(saved["filename"], webp_path, saved.get("subfolder", ""))
    convert_to_mp4(webp_path, out, fps)
    webp_path.unlink(missing_ok=True)
    return out


def generate_scene_clips(
    client: WanClient,
    prompt: str,
    job_width: int,
    job_height: int,
    scene_seconds: float,
    seed: int,
    out_dir,
    fps: int = 30,
    primary_model: Optional[str] = None,
    fallback_model: Optional[str] = None,
) -> List[str]:
    """Generate all clips for a scene; returns MP4 paths in order.

    Retry policy: 3 attempts on the primary model, then 3 on the fallback,
    then a hard VideoGenError. Seeds vary per attempt for diversity.
    """
    primary = primary_model or DEFAULT_MODEL
    fallback = fallback_model or FALLBACK_MODEL
    clips = plan_clips(scene_seconds, fps)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: List[str] = []

    with _GEN_LOCK:
        for i, frames in enumerate(clips):
            out_path = out_dir / f"scene-{i}.mp4"
            last_error: Optional[Exception] = None
            for attempt, model in enumerate((primary, primary, primary, fallback, fallback, fallback)):
                attempt_seed = seed + i * 1000 + attempt
                try:
                    path = generate_clip(client, prompt, job_width, job_height, frames,
                                         attempt_seed, str(out_path), fps=fps, model=model)
                    results.append(str(path))
                    logger.info("Wan clip ready: %s (model=%s, frames=%d)", path.name, model, frames)
                    break
                except VideoGenError as exc:
                    last_error = exc
                    logger.warning("Wan attempt failed (model=%s): %s", model, exc)
            else:
                raise VideoGenError(
                    f"All Wan attempts exhausted for clip {i}: {last_error}"
                )
    return results
