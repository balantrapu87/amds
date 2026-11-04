#!/usr/bin/env python3
"""Standalone Wan 2.1 text-to-video generation through the llama-swap gateway.

Runs entirely outside the chat session: one LLM-eviction at submit time, the
gateway video group stays alive via polling, and the LLM is swapped back in at
the end so chat can resume immediately.

Usage:
    .venv/bin/python scripts/generate_video.py \
        --prompt "A cinematic shot of a cricket stadium at dusk" \
        --seconds 5.0 --narration "What a strike!" \
        --out-dir output/wan_5s

Output files (stable names):
    <out-dir>/wan_video.mp4   H.264 video, 81 frames max = 5.06s @ 16fps
    <out-dir>/wan_video.mp3   edge-tts narration (only with --narration)
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from engine import tts  # noqa: E402
from engine.video_gen import WanClient, VideoGenError, generate_clip  # noqa: E402

logger = logging.getLogger("generate_video")

LLM_GATEWAY = "http://127.0.0.1:8080"  # llama-swap unified gateway (LLM route)


def frames_for(seconds: float) -> int:
    """Wan latent length: largest 4n+1 <= round(seconds*16)+1, clamped to [5, 81].

    81 frames @ 16fps = 5.06s is Wan 14B's maximum clip.
    """
    if seconds > 5.1:
        raise ValueError("--seconds must be <= 5.1 (Wan max is 81 frames = 5.06s @ 16fps)")
    target = int(round(seconds * 16)) + 1
    length = target - ((target - 1) % 4)
    return max(5, min(81, length))


def reactivate_llm(timeout: float = 1800.0) -> None:
    """Swap the LLM back in via the gateway so chat can resume immediately.

    The request blocks until the manager has evicted ComfyUI, relaunched
    llama-server, and its /health check passes.
    """
    logger.info("Reactivating LLM via gateway (blocks until healthy)...")
    try:
        httpx.get(f"{LLM_GATEWAY}/v1/models", timeout=timeout)
        logger.info("LLM is back — chat can resume.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM reactivation failed (%s); resume chat manually.", exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prompt", required=True, help="text-to-video prompt")
    ap.add_argument("--seconds", type=float, default=5.0, help="clip length, max ~5.06 (default 5.0)")
    ap.add_argument("--width", type=int, default=1920, help="job width (16:9 or 9:16)")
    ap.add_argument("--height", type=int, default=1080, help="job height")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model", default=os.environ.get("WAN_MODEL", "wan2.1_t2v_14B_fp8_e4m3fn.safetensors"))
    ap.add_argument("--narration", default=None, help="TTS voiceover text (edge-tts MP3)")
    ap.add_argument("--voice", default=os.environ.get("EDGE_TTS_VOICE", "en-US-AriaNeural"))
    ap.add_argument("--gateway", default="http://127.0.0.1:8080/comfyui", help="llama-swap ComfyUI route")
    ap.add_argument("--out-dir", default=str(ROOT / "output"), help="output directory")
    args = ap.parse_args()

    frames = frames_for(args.seconds)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "wan_video.mp4"
    audio_path = out_dir / "wan_video.mp3" if args.narration else None

    logger.info("Prompt:   %s", args.prompt)
    logger.info("Clip:     %d frames (%.2fs @ 16fps), model=%s, seed=%d", frames, frames / 16, args.model, args.seed)
    logger.info("VIDEO:    %s", video_path)
    logger.info("AUDIO:    %s", audio_path if audio_path else "(none)")

    client = WanClient(args.gateway)
    try:
        t0 = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                # Submit evicts the LLM via llama-swap; polling keeps the
                # video group alive (TTL 600s) for the whole generation.
                generate_clip(
                    client, args.prompt, args.width, args.height, frames,
                    args.seed, str(video_path), fps=16, model=args.model,
                )
                last_error = None
                break
            except (VideoGenError, httpx.HTTPError) as exc:
                last_error = exc
                logger.warning("Generation attempt %d/3 failed: %s", attempt, exc)
                if attempt < 3:
                    time.sleep(30)
        if last_error is not None:
            raise SystemExit(f"Video generation failed after 3 attempts: {last_error}")
        logger.info("Video done in %.0fs: %s", time.monotonic() - t0, video_path)

        if audio_path is not None and args.narration:
            asyncio.run(tts.synthesize(args.narration, str(audio_path), args.voice))
            logger.info("Audio done: %s", audio_path)
    finally:
        client.close()

    # Swap the LLM back in before exiting so the user can chat immediately.
    reactivate_llm()
    print(f"VIDEO: {video_path}")
    print(f"AUDIO: {audio_path}")


if __name__ == "__main__":
    main()
