"""
Headless FastAPI Dispatcher for Autonomous Motion Design Studio.
Manages job validation, LLM storyboard generation via llama-swap,
Remotion multi-core render dispatch, and deterministic audio mastering.
"""

import os
import json
import uuid
import hashlib
import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from engine.schemas import (
    RenderRequest,
    StudioJobPayload,
    SceneNode,
    ThemeTokens,
    AudioManifest,
    CaptionWord,
    SceneLayoutType,
    GeometryType,
    ThreeParams,
)
from engine.audio import execute_mastering, raw_video_has_audio
from engine.tts import synthesize_script, probe_duration
from engine.captions import transcribe, normalize_words, extract_words, narration_end_ms, CaptionError
from engine.video_gen import WanClient, generate_scene_clips, plan_clips, VideoGenError

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("motion_api")

app = FastAPI(
    title="Autonomous Motion Design Studio Engine",
    version="1.0.0",
    description="Deterministic headless video generation and audio mastering API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration defaults
# Model Routing:
# - Creative writing, narrative thinking, storyboard synthesis: 'qwen'
# - Code generation, programmatic transforms, code review: 'qwen-coder'
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen")
LLM_CODER_MODEL = os.getenv("LLM_CODER_MODEL", "qwen-coder")
REMOTION_ROOT = os.getenv("REMOTION_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "remotion")))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output")))
JOBS_DIR = os.getenv("JOBS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "jobs")))
RENDER_CONCURRENCY = int(os.getenv("RENDER_CONCURRENCY", "16"))
# Local AI services
WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:8080/v1/audio/transcriptions")
WAN_COMFYUI_URL = os.getenv("WAN_COMFYUI_URL", "http://127.0.0.1:8080/comfyui")
# Scene narration tail (ms) appended after the last spoken word before the cut.
NARRATION_TAIL_MS = int(os.getenv("NARRATION_TAIL_MS", "750"))

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)

# In-memory job state registry
JOB_REGISTRY: Dict[str, Dict[str, Any]] = {}


async def generate_storyboard_from_brief(
    brief: str,
    width: int,
    height: int,
    fps: int,
    voiceover_path: str,
    bgm_path: Optional[str] = None,
) -> StudioJobPayload:
    """
    Calls local LLM (Qwen 3.8 27B via llama-swap) with JSON Schema guidance
    to synthesize a complete, deterministic StudioJobPayload from a natural language brief.
    """
    logger.info(f"Synthesizing storyboard from brief via {LLM_ENDPOINT} using model '{LLM_MODEL}'")

    system_prompt = (
        "You are an expert Autonomous Motion Graphics Designer. You convert creative briefs "
        "into structured, deterministic video storyboard JSON specifications matching the StudioJobPayload schema. "
        "Rules:\n"
        "1. Return ONLY valid JSON matching the schema.\n"
        "2. Break the topic into 3 to 5 scenes.\n"
        "3. Each scene must specify duration_in_frames (between 60 and 180 frames at 30fps).\n"
        "4. Layout types: 'kinetic_typography', 'three_d_mesh', or 'hybrid'.\n"
        "5. Valid Lucide icons only (e.g. 'activity', 'cpu', 'layers', 'zap', 'shield', 'code', 'database').\n"
        "6. Provide high-contrast, modern dark-mode theme tokens (hex codes).\n"
        "7. Each scene MUST include 'voiceover_text': a narration script worded to fit its "
        "duration_frames (roughly 2.5 words per second of scene time) so the synthesized "
        "voiceover matches the scene it plays over.\n"
        "8. When the brief calls for live-action or photorealistic footage, mark that scene "
        "'render_layer': 'hybrid' and add 'video_prompts': 1-3 cinematic text-to-video prompts "
        "(subject, camera move, lighting, mood). Omit video_prompts for pure typography slides.\n"
    )

    user_prompt = (
        f"Generate a motion design storyboard for the following brief:\n"
        f"\"{brief}\"\n"
        f"Target Resolution: {width}x{height}, FPS: {fps}.\n"
        f"Voiceover: {voiceover_path}\n"
    )

    schema_example = {
        "job_id": str(uuid.uuid4()),
        "fps": fps,
        "width": width,
        "height": height,
        "theme": {
            "primary_color": "#6366F1",
            "secondary_color": "#8B5CF6",
            "accent_color": "#06B6D4",
            "background_color": "#0F172A",
            "surface_color": "#1E293B",
            "text_color": "#F8FAFC",
            "text_muted_color": "#94A3B8",
            "font_family": "Inter, sans-serif",
            "border_radius": 16,
            "padding": 32
        },
        "audio": {
            "voiceover_path": voiceover_path,
            "bgm_path": bgm_path or "",
            "target_lufs": -16.0,
            "true_peak_db": -1.5,
            "ducking_threshold_db": -20.0,
            "ducking_ratio": 4.0,
            "ducking_attack_ms": 15.0,
            "ducking_release_ms": 250.0,
            "bgm_volume_db": -12.0
        },
        "scenes": [
            {
                "scene_id": "scene-1",
                "duration_frames": 90,
                "render_layer": "hybrid",
                "headline": "Title Here",
                "subtitle": "Subtitle Here",
                "body_text": "Key description here",
                "icon_asset": "cpu",
                "voiceover_text": "Narration for this scene, worded to fit its duration.",
                "video_prompts": ["A cinematic description of the scene visuals, camera movement and lighting"],
                "three_params": {
                    "geometry": "torus",
                    "wireframe": True,
                    "camera_fov": 45.0,
                    "camera_position": [0.0, 0.0, 5.0],
                    "mesh_position": [0.0, 0.0, 0.0],
                    "mesh_scale": [1.0, 1.0, 1.0],
                    "rotation_speed_x": 0.2,
                    "rotation_speed_y": 0.5,
                    "rotation_speed_z": 0.0
                }
            }
        ]
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt + f"\nRespond strictly with a JSON object following this shape:\n{json.dumps(schema_example)}\n/no_think"}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(LLM_ENDPOINT, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(raw_content)

            # Ensure essential audio paths are populated
            if "audio" not in parsed_json:
                parsed_json["audio"] = {}
            parsed_json["audio"]["voiceover_path"] = voiceover_path
            if bgm_path:
                parsed_json["audio"]["bgm_path"] = bgm_path

            parsed_json["job_id"] = str(uuid.uuid4())
            parsed_json["fps"] = fps
            parsed_json["width"] = width
            parsed_json["height"] = height

            job_payload = StudioJobPayload.model_validate(parsed_json)
            return job_payload

    except Exception as e:
        logger.warning(f"LLM semantic generation fallback due to: {type(e).__name__}: {e}. Generating deterministic template.")
        # Fallback to high-quality procedural template
        return StudioJobPayload(
            job_id=str(uuid.uuid4()),
            fps=fps,
            width=width,
            height=height,
            theme=ThemeTokens(),
            audio=AudioManifest(
                voiceover_path=voiceover_path,
                bgm_path=bgm_path,
                target_lufs=-16.0,
                true_peak_db=-1.5,
                ducking_threshold_db=-20.0,
                ducking_ratio=4.0,
                ducking_attack_ms=15.0,
                ducking_release_ms=250.0,
                bgm_volume_db=-12.0
            ),
            scenes=[
                SceneNode(
                    scene_id="scene-intro",
                    duration_frames=90,
                    render_layer="hybrid",
                    headline=brief[:60] if brief else "Autonomous Motion",
                    subtitle="Generated programmatically via code-driven engine",
                    body_text="Deterministic frame-locked rendering with hardware acceleration",
                    icon_asset="zap",
                    voiceover_text="Welcome to the autonomous motion studio, where every frame is generated by code.",
                    three_params=ThreeParams(geometry=GeometryType.TORUS, wireframe=True)
                ),
                SceneNode(
                    scene_id="scene-deep-dive",
                    duration_frames=120,
                    render_layer="kinetic_typography",
                    headline="Zero Manual Intervention",
                    subtitle="Chromium headless rasterization + Remotion pure frame clock",
                    body_text="Multi-threaded concurrency pinned across all CPU cores",
                    icon_asset="cpu",
                    voiceover_text="Rendering is fully deterministic, stepped across every available CPU core."
                ),
                SceneNode(
                    scene_id="scene-conclusion",
                    duration_frames=90,
                    render_layer="hybrid",
                    headline="Broadcast Audio Standards",
                    subtitle="EBU R128 Loudnorm & Dynamic Sidechain Ducking",
                    body_text="Engineered for web, social and broadcast formats",
                    icon_asset="activity",
                    voiceover_text="Audio is mastered to broadcast loudness, with narration synthesized by local edge TTS.",
                    three_params=ThreeParams(geometry=GeometryType.ICOSAHEDRON, wireframe=True)
                )
            ]
        )


async def synthesize_voiceover(job_id: str, job_payload: StudioJobPayload) -> None:
    """Pipeline stage: script -> audio.

    Synthesizes per-scene narration via local edge-tts and resolves each scene's
    audio_file (public-relative) so Remotion can embed the voiceover. TTS failures
    are non-fatal: the render proceeds without narration.
    """
    scenes_dicts = [scene.model_dump() for scene in job_payload.scenes]
    if not any((scene.get("voiceover_text") or "").strip() for scene in scenes_dicts):
        logger.info(f"[{job_id}] No scene narration present; skipping TTS stage.")
        return

    audio_root = os.path.join(REMOTION_ROOT, "public", "audio")
    try:
        resolved = await synthesize_script(scenes_dicts, audio_root, job_id)
    except Exception as e:  # noqa: BLE001 - TTS must never hard-fail the render
        logger.warning(f"[{job_id}] TTS synthesis stage failed: {e}. Continuing without narration.")
        return

    for scene, audio_file in zip(job_payload.scenes, resolved):
        scene.audio_file = audio_file
    narrated = sum(1 for a in resolved if a)
    logger.info(f"[{job_id}] TTS complete: {narrated}/{len(resolved)} scenes narrated.")


async def apply_whisper_timing(job_id: str, job_payload: StudioJobPayload) -> None:
    """Pipeline stage: audio -> exact narration length + word-level captions.

    Whisper is the length authority: each narrated scene's duration becomes
    (last word end + NARRATION_TAIL_MS), capped by the measured MP3 length
    (ffprobe sanity bound so Whisper hallucinations can't stretch scenes).
    Failures are non-fatal: the authored duration is kept and no captions set.
    """
    for scene in job_payload.scenes:
        if not scene.audio_file:
            continue
        mp3_path = os.path.join(REMOTION_ROOT, "public", "audio", scene.audio_file)
        try:
            payload = await asyncio.to_thread(transcribe, mp3_path, WHISPER_URL)
            words = extract_words(payload)
            if not words:
                logger.warning(f"[{job_id}] Whisper returned no words for {scene.scene_id}; keeping authored duration.")
                continue
            end_ms = narration_end_ms(words, tail_ms=NARRATION_TAIL_MS)
            try:
                audio_seconds = probe_duration(mp3_path)
                if audio_seconds > 0:
                    end_ms = min(end_ms, int(audio_seconds * 1000))
            except Exception:  # noqa: BLE001 - ffprobe missing: skip the sanity cap
                logger.warning(f"[{job_id}] ffprobe unavailable; skipping audio-length cap for {scene.scene_id}.")
            scene.captions = [CaptionWord(**w) for w in words]
            scene.duration_frames = max(15, min(1800, round(end_ms / 1000 * job_payload.fps)))
            logger.info(f"[{job_id}] Scene {scene.scene_id} timed to narration: {scene.duration_frames}f, {len(words)} caption words.")
        except Exception as e:  # noqa: BLE001 - timing must never hard-fail the render
            logger.warning(f"[{job_id}] Whisper timing failed for {scene.scene_id}: {e}. Keeping authored duration.")


async def attach_wan_clips(job_id: str, job_payload: StudioJobPayload) -> None:
    """Pipeline stage: video_prompts -> generated Wan 2.1 clips (full-bleed source).

    Scenes carrying video_prompts (and no pre-resolved clips) get one Wan clip
    per planned 4n+1 segment. Deterministic per-scene seed. A generation failure
    after the full retry budget is a hard stop: video scenes must have clips.
    """
    for scene in job_payload.scenes:
        if not scene.video_prompts or scene.clips:
            continue
        if not (scene.voiceover_text or "").strip():
            continue  # video scenes are timed by narration; no narration, no video
        try:
            client = WanClient(WAN_COMFYUI_URL)
            scene_seconds = scene.duration_frames / job_payload.fps
            seed = int(hashlib.sha256(f"{job_id}:{scene.scene_id}".encode()).hexdigest()[:8], 16)
            out_dir = os.path.join(REMOTION_ROOT, "public", "video", job_id, scene.scene_id)
            clip_lengths = plan_clips(scene_seconds, job_payload.fps)
            paths = await asyncio.to_thread(
                generate_scene_clips,
                client, scene.video_prompts,
                job_payload.width, job_payload.height,
                scene_seconds, seed, out_dir, job_payload.fps,
            )
            public_root = os.path.join(REMOTION_ROOT, "public")
            scene.clips = [os.path.relpath(p, public_root) for p in paths]
            scene.clip_frames = clip_lengths[: len(paths)]
            client.close()
            logger.info(f"[{job_id}] Wan clips attached to scene {scene.scene_id}: {scene.clips}")
        except VideoGenError:
            raise  # hard stop per design: exhausts 3x14B + 3x1.3B
        except Exception as e:  # noqa: BLE001 - ComfyUI unreachable etc.
            raise VideoGenError(f"Wan video generation unavailable for scene {scene.scene_id}: {e}") from e


async def execute_render_pipeline(job_id: str, job_payload: StudioJobPayload):
    """
    Asynchronous worker task:
    1. Writes props.json.
    2. Runs `npx remotion render` with concurrency=16.
    3. Runs FFmpeg sidechain mastering.
    4. Updates job status to completed.
    """
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    props_path = os.path.join(job_dir, "props.json")
    raw_video_path = os.path.join(job_dir, "raw_canvas.mp4")
    final_video_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")

    try:
        JOB_REGISTRY[job_id]["status"] = "preparing"
        JOB_REGISTRY[job_id]["step"] = "tts_synthesis"

        # 1. Script -> Audio: synthesize per-scene narration via local edge-tts.
        await synthesize_voiceover(job_id, job_payload)

        JOB_REGISTRY[job_id]["status"] = "preparing"
        JOB_REGISTRY[job_id]["step"] = "whisper_timing"

        # 2. Audio -> exact timing: Whisper word timestamps become scene
        #    durations and karaoke captions (Whisper is the length authority).
        await apply_whisper_timing(job_id, job_payload)

        JOB_REGISTRY[job_id]["status"] = "preparing"
        JOB_REGISTRY[job_id]["step"] = "wan_video_generation"

        # 3. video_prompts -> Wan 2.1 full-bleed clips (hard stop on failure).
        await attach_wan_clips(job_id, job_payload)

        JOB_REGISTRY[job_id]["status"] = "preparing"
        JOB_REGISTRY[job_id]["step"] = "writing_props"

        # 2. Serialize deterministic props.json (scenes now carry resolved audio_file)
        with open(props_path, "w", encoding="utf-8") as f:
            f.write(job_payload.model_dump_json(indent=2))

        JOB_REGISTRY[job_id]["status"] = "rendering"
        JOB_REGISTRY[job_id]["step"] = "remotion_rasterization"

        # 2. Spawn Remotion render command
        remotion_cmd = [
            "npx", "remotion", "render",
            "MainComposition",
            raw_video_path,
            f"--props={props_path}",
            f"--concurrency={RENDER_CONCURRENCY}",
            "--gl=angle",
            "--log=info"
        ]

        logger.info(f"[{job_id}] Spawning Remotion render: {' '.join(remotion_cmd)}")

        process = await asyncio.create_subprocess_exec(
            *remotion_cmd,
            cwd=REMOTION_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace")[-1000:]
            logger.error(f"[{job_id}] Remotion render failed: {err_msg}")
            JOB_REGISTRY[job_id]["status"] = "failed"
            JOB_REGISTRY[job_id]["error"] = f"Remotion failed: {err_msg}"
            return

        JOB_REGISTRY[job_id]["status"] = "mastering"
        JOB_REGISTRY[job_id]["step"] = "ffmpeg_audio_ducking"

        # 3. Deterministic Audio Mastering (narration already muxed by Remotion)
        voiceover_embedded = raw_video_has_audio(raw_video_path)
        logger.info(
            f"[{job_id}] Executing audio mastering on {raw_video_path} "
            f"(voiceover_embedded={voiceover_embedded})"
        )
        mastered_path = execute_mastering(
            raw_video_path=raw_video_path,
            output_mp4_path=final_video_path,
            audio=job_payload.audio,
            voiceover_embedded=voiceover_embedded
        )

        JOB_REGISTRY[job_id]["status"] = "completed"
        JOB_REGISTRY[job_id]["step"] = "done"
        JOB_REGISTRY[job_id]["output_path"] = mastered_path
        logger.info(f"[{job_id}] Render job succeeded. Output: {mastered_path}")

    except Exception as e:
        logger.exception(f"[{job_id}] Pipeline execution encountered exception: {e}")
        JOB_REGISTRY[job_id]["status"] = "failed"
        JOB_REGISTRY[job_id]["error"] = str(e)


@app.post("/render")
async def post_render(request: RenderRequest, background_tasks: BackgroundTasks):
    """
    Submits a video generation and mastering job.
    Accepts either an explicit StudioJobPayload or a topic brief.
    """
    job_id = str(uuid.uuid4())

    # Ensure mock voiceover exists if caller didn't provide a real one in test mode
    vo_path = request.voiceover_path or (request.payload.audio.voiceover_path if request.payload else None)
    if not vo_path or not os.path.exists(vo_path):
        dummy_dir = os.path.join(JOBS_DIR, "assets")
        os.makedirs(dummy_dir, exist_ok=True)
        vo_path = os.path.join(dummy_dir, "silence_vo.wav")
        if not os.path.exists(vo_path):
            os.system(f"ffmpeg -y -f lavfi -i anullsrc=r=48000:cl=stereo -t 10 -c:a pcm_s16le {vo_path} >/dev/null 2>&1")

    if request.payload:
        job_payload = request.payload
        job_payload.job_id = job_id
        if not os.path.exists(job_payload.audio.voiceover_path):
            job_payload.audio.voiceover_path = vo_path
    else:
        job_payload = await generate_storyboard_from_brief(
            brief=request.brief or "Autonomous Motion Studio",
            width=request.width,
            height=request.height,
            fps=request.fps,
            voiceover_path=vo_path,
            bgm_path=request.bgm_path
        )
        job_payload.job_id = job_id

    # Register initial status
    JOB_REGISTRY[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "step": "enqueued",
        "duration_frames": job_payload.total_duration_in_frames,
        "duration_seconds": job_payload.total_duration_seconds,
        "output_path": None,
        "error": None,
    }

    # Dispatch to background task
    background_tasks.add_task(execute_render_pipeline, job_id, job_payload)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "message": "Render job accepted and queued for execution.",
            "duration_frames": job_payload.total_duration_in_frames,
            "duration_seconds": job_payload.total_duration_seconds,
            "scenes_count": len(job_payload.scenes)
        }
    )


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Retrieves real-time status, step, and output artifact paths for a job."""
    if job_id not in JOB_REGISTRY:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return JOB_REGISTRY[job_id]


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestrators."""
    return {"status": "ok", "service": "motion-api", "concurrency": RENDER_CONCURRENCY}
