#!/usr/bin/env python3
"""
Orchestration Script: Build 60-Second Cricket Explainer Video
Following the 5-Phase Production Flow:
1. Synthesizes Edge-TTS voiceovers per scene.
2. Calls local Whisper on llama-swap for word-level captions and timing authority.
3. Generates 5 hero Wan 2.1 16:9 video clips via local ComfyUI.
4. Serializes deterministic props.json for Remotion.
5. Renders Remotion MainComposition with full-bleed clips, kinetic captions, and brand overlays.
6. Applies FFmpeg broadcast audio mastering (EBU R128 -16 LUFS).
"""

import os
import sys
import json
import time
import asyncio
import logging
import subprocess
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ensure local bin is in PATH for ffmpeg and ffprobe
if "/home/pkbala/.local/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"/home/pkbala/.local/bin:{os.environ.get('PATH', '')}"

import httpx
from engine import tts
from engine.captions import transcribe, extract_words, narration_end_ms
from engine.video_gen import WanClient, generate_clip, VideoGenError
from engine.audio import execute_mastering, raw_video_has_audio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cricket_orchestrator")

JOB_ID = "cricket_story_60s"
WIDTH = 1920
HEIGHT = 1080
FPS = 30
WAN_MODEL = os.environ.get("WAN_MODEL", "wan2.1_t2v_1.3B_bf16.safetensors")
FALLBACK_MODEL = os.environ.get("WAN_FALLBACK_MODEL", "wan2.1_t2v_14B_fp8_e4m3fn.safetensors")
COMFYUI_URL = os.environ.get("WAN_COMFYUI_URL", "http://127.0.0.1:8080/comfyui")
WHISPER_URL = os.environ.get("WHISPER_URL", "http://127.0.0.1:8080/v1/audio/transcriptions")
EDGE_TTS_VOICE = os.environ.get("EDGE_TTS_VOICE", "en-US-AriaNeural")

REMOTION_ROOT = ROOT / "remotion"
PUBLIC_DIR = REMOTION_ROOT / "public"
JOBS_DIR = ROOT / "jobs" / JOB_ID
OUTPUT_DIR = ROOT / "output"

SCENES_DEF = [
    {
        "id": "scene-1-arena",
        "headline": "The Arena of Cricket",
        "subtitle": "Two Teams, One Epic Quest",
        "body_text": "Imagine stepping into a colossal green arena with two teams of eleven players! One team defends the field, while two batters conquer it by scoring runs!",
        "voiceover_text": "Imagine stepping into a colossal green arena with two teams of eleven players! One team takes the field to defend their kingdom, while two brave batters step up to score runs!",
        "video_prompt": "Cinematic wide-angle aerial drone shot gliding over a lush green cricket stadium under glowing floodlights, stadium crowd cheering, cinematic 16:9 lighting, ultra-detailed.",
        "icon_asset": "Trophy",
    },
    {
        "id": "scene-2-pitch",
        "headline": "The 22-Yard Duel",
        "subtitle": "Bowler Attacks, Batter Defends",
        "body_text": "At the center lies a twenty-two yard strip called the pitch. The bowler charges in, rocketing the ball toward three wooden stumps called wickets!",
        "voiceover_text": "At the center lies a twenty-two yard battle strip called the pitch. The bowler charges in, rocketing the ball toward three wooden stumps! But the batter stands guard with a willow bat!",
        "video_prompt": "Dramatic low-angle slow motion tracking shot of a fast bowler running in and hurling a red cricket ball on a sunny pitch, dust kicking up, dynamic camera motion.",
        "icon_asset": "Target",
    },
    {
        "id": "scene-3-runs",
        "headline": "Scoring Runs",
        "subtitle": "Singles, Fours, and Giant Sixes",
        "body_text": "Batters sprint between wickets to score runs. If the ball zooms across the grass to the rope, that's 4 runs. If it flies into the sky over the rope—that's a massive 6!",
        "voiceover_text": "Crack! When the batter hits the ball and sprints between wickets, that's one run. If the ball zooms across the grass to the rope, that's four runs! And if it rockets into the sky over the rope—that's a huge six!",
        "video_prompt": "Dynamic slow motion action shot of a cricket bat striking a leather ball with explosive energy, camera tracking the ball soaring high into the stadium sky toward the boundary.",
        "icon_asset": "Flame",
    },
    {
        "id": "scene-4-wickets",
        "headline": "Guarding the Castle",
        "subtitle": "Bowled, Caught, and Run Out",
        "body_text": "The fielding team hunts for wickets! If the ball hits the stumps—you're bowled! If a fielder catches it in the air—you're caught! Outside your crease—you're run out!",
        "voiceover_text": "Watch out! The fielding team wants wickets! If the ball hits the wooden stumps—you're bowled! If a fielder snatches it in the air—you're caught! And if you get caught outside your crease—you're run out!",
        "video_prompt": "Close-up cinematic slow motion of wooden cricket stumps shattering and bails flying into the air as the ball crashes into the wicket, dramatic particles.",
        "icon_asset": "Shield",
    },
    {
        "id": "scene-5-victory",
        "headline": "The Ultimate Victory",
        "subtitle": "Chasing the Target & Lifting the Cup",
        "body_text": "Once all batters get their turn, the teams switch! Team two chases the target score. The team with the most runs hoists the championship cup!",
        "voiceover_text": "Once all batters get their turn, the teams switch! Now team two chases the score. Whoever scores the most runs lifts the championship cup! That is the thrill of cricket!",
        "video_prompt": "Cinematic celebration shot of cricket players cheering together on the pitch, golden confetti raining down, fireworks exploding above the stadium in the night sky.",
        "icon_asset": "Crown",
    },
]


def probe_mp4_duration(mp4_path: Path) -> float:
    """Probe duration of an MP4 file in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mp4_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


async def step_1_tts(scenes_data):
    logger.info("=== STEP 1: Synthesizing Edge-TTS Voiceovers ===")
    audio_dir = PUBLIC_DIR / "audio" / JOB_ID
    audio_dir.mkdir(parents=True, exist_ok=True)

    for i, sc in enumerate(scenes_data):
        audio_filename = f"scene-{i}.mp3"
        out_path = audio_dir / audio_filename
        sc["audio_rel_path"] = f"{JOB_ID}/{audio_filename}"
        sc["audio_abs_path"] = str(out_path)

        logger.info(f"Synthesizing VO for Scene {i+1}: {sc['id']}...")
        await tts.synthesize(sc["voiceover_text"], str(out_path), voice=EDGE_TTS_VOICE)
        logger.info(f" -> Generated: {out_path} ({out_path.stat().st_size} bytes)")


def step_2_whisper(scenes_data):
    logger.info("=== STEP 2: Transcribing Audio with Local Whisper on llama-swap ===")
    for i, sc in enumerate(scenes_data):
        audio_path = sc["audio_abs_path"]
        logger.info(f"Transcribing Scene {i+1} audio: {audio_path}...")
        try:
            payload = transcribe(audio_path, WHISPER_URL, timeout=120.0)
            words = extract_words(payload)
            sc["captions"] = words
            
            # Whisper timing authority: duration = last word end + 750ms tail
            end_ms = narration_end_ms(words, tail_ms=750)
            audio_dur = tts.probe_duration(audio_path)
            if audio_dur > 0:
                end_ms = max(end_ms, int(audio_dur * 1000) + 500)
            
            # Duration in frames at 30 fps (clamp to minimum 240 frames ~ 8s for comfortable storytelling)
            sc["duration_frames"] = max(240, round(end_ms / 1000.0 * FPS))
            logger.info(f" -> Words: {len(words)}, Duration: {sc['duration_frames']} frames (~{sc['duration_frames']/FPS:.2f}s)")
        except Exception as e:
            logger.warning(f"Whisper transcription failed for Scene {i+1}: {e}. Using fallback timing.")
            audio_dur = tts.probe_duration(audio_path)
            sc["duration_frames"] = max(300, round((audio_dur + 1.0) * FPS))
            sc["captions"] = []


def step_3_wan_video(scenes_data):
    logger.info("=== STEP 3: Generating Wan 2.1 Video Clips via ComfyUI ===")
    client = WanClient(COMFYUI_URL, timeout=1200.0)
    video_base_dir = PUBLIC_DIR / "video" / JOB_ID

    try:
        for i, sc in enumerate(scenes_data):
            scene_dir = video_base_dir / f"scene-{i}"
            scene_dir.mkdir(parents=True, exist_ok=True)
            clip_path = scene_dir / "scene-0.mp4"
            rel_clip_path = f"video/{JOB_ID}/scene-{i}/scene-0.mp4"

            if clip_path.exists() and clip_path.stat().st_size > 100000:
                logger.info(f"Clip already exists for Scene {i+1}: {clip_path}")
                dur = probe_mp4_duration(clip_path)
                sc["clips"] = [rel_clip_path]
                sc["clip_frames"] = [max(1, round(dur * FPS))]
                continue

            prompt = sc["video_prompt"]
            seed = 42 + i * 101
            logger.info(f"Generating Wan clip for Scene {i+1} (prompt: '{prompt[:60]}...')...")
            
            # Retry loop: primary 14B -> fallback 1.3B
            last_err = None
            for model_name in (WAN_MODEL, WAN_MODEL, FALLBACK_MODEL):
                try:
                    logger.info(f" -> Attempting generation with model: {model_name}...")
                    generate_clip(
                        client=client,
                        prompt=prompt,
                        job_width=WIDTH,
                        job_height=HEIGHT,
                        frames=81,  # 81 frames (~5.06s @ 16fps)
                        seed=seed,
                        out_path=str(clip_path),
                        fps=FPS,
                        model=model_name,
                    )
                    last_err = None
                    break
                except (VideoGenError, httpx.HTTPError) as exc:
                    last_err = exc
                    logger.warning(f"Attempt with {model_name} failed: {exc}. Retrying...")
                    time.sleep(10)
            
            if last_err is not None or not clip_path.exists():
                raise RuntimeError(f"Wan video generation failed for Scene {i+1}: {last_err}")

            dur = probe_mp4_duration(clip_path)
            clip_frames_count = max(1, round(dur * FPS))
            sc["clips"] = [rel_clip_path]
            sc["clip_frames"] = [clip_frames_count]
            logger.info(f" -> Clip generated: {clip_path} (Duration: {dur:.2f}s, {clip_frames_count} frames)")
    finally:
        client.close()


def step_4_serialize_props(scenes_data) -> Path:
    logger.info("=== STEP 4: Serializing props.json for Remotion ===")
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    props_path = JOBS_DIR / "props.json"

    # Construct final scenes array conforming to SceneNode
    scenes_json = []
    for sc in scenes_data:
        scenes_json.append({
            "scene_id": sc["id"],
            "id": sc["id"],
            "duration_frames": sc["duration_frames"],
            "duration_in_frames": sc["duration_frames"],
            "render_layer": "kinetic_typography",
            "layout_type": "kinetic_typography",
            "headline": sc["headline"],
            "title": sc["headline"],
            "subtitle": sc["subtitle"],
            "body_text": sc["body_text"],
            "icon_asset": sc["icon_asset"],
            "voiceover_text": sc["voiceover_text"],
            "audio_file": sc["audio_rel_path"],
            "clips": sc.get("clips", []),
            "clip_frames": sc.get("clip_frames", []),
            "captions": sc.get("captions", []),
        })

    payload = {
        "job_id": JOB_ID,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "channel_name": "CRICKET 101",
        "theme": {
            "background_hex": "#08131E",
            "background_color": "#08131E",
            "primary_hex": "#22C55E",
            "primary_color": "#22C55E",
            "secondary_color": "#38BDF8",
            "accent_color": "#F59E0B",
            "surface_color": "#0F2236",
            "text_hex": "#F8FAFC",
            "text_color": "#F8FAFC",
            "text_muted_color": "#94A3B8",
            "font_family": "Inter, sans-serif",
            "border_radius": 16,
            "padding": 32,
        },
        "audio": {
            "voiceover_path": "embedded",
            "bgm_path": None,
            "target_lufs": -16.0,
            "true_peak_db": -1.5,
            "ducking_threshold_db": -20.0,
            "ducking_ratio": 4.0,
            "ducking_attack_ms": 15.0,
            "ducking_release_ms": 250.0,
            "bgm_volume_db": -12.0,
        },
        "scenes": scenes_json,
    }

    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info(f"props.json written to: {props_path}")
    return props_path


def step_5_remotion_render(props_path: Path) -> Path:
    logger.info("=== STEP 5: Rendering Remotion MainComposition ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_video_path = JOBS_DIR / "raw_canvas.mp4"

    if raw_video_path.exists() and raw_video_path.stat().st_size > 1000000:
        logger.info(f"Raw canvas video already rendered: {raw_video_path} ({raw_video_path.stat().st_size} bytes)")
        return raw_video_path

    cmd = [
        "npx", "remotion", "render",
        "MainComposition",
        str(raw_video_path),
        f"--props={props_path}",
        "--concurrency=16",
        "--gl=angle",
        "--log=info",
    ]
    logger.info(f"Running: {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REMOTION_ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error(f"Remotion render failed! Stderr: {proc.stderr[-1500:]}")
        raise RuntimeError("Remotion render failed.")

    logger.info(f"Raw canvas rendered in {time.time() - t0:.1f}s: {raw_video_path}")
    return raw_video_path


def step_6_ffmpeg_mastering(raw_video_path: Path, props_path: Path) -> Path:
    logger.info("=== STEP 6: Deterministic FFmpeg Broadcast Audio Mastering ===")
    final_output_path = OUTPUT_DIR / f"{JOB_ID}.mp4"

    with open(props_path, "r", encoding="utf-8") as f:
        props = json.load(f)

    from engine.schemas import AudioManifest
    audio_manifest = AudioManifest(**props["audio"])
    has_audio = raw_video_has_audio(str(raw_video_path))
    logger.info(f"Raw video voiceover embedded: {has_audio}")

    mastered_path = execute_mastering(
        raw_video_path=str(raw_video_path),
        output_mp4_path=str(final_output_path),
        audio=audio_manifest,
        voiceover_embedded=has_audio,
    )
    logger.info(f"Mastered final video ready: {mastered_path}")
    return Path(mastered_path)


def main():
    logger.info("Starting Video Orchestration Pipeline for Cricket 101...")
    start_time = time.time()

    scenes = [dict(s) for s in SCENES_DEF]

    # Step 1: TTS
    asyncio.run(step_1_tts(scenes))

    # Step 2: Whisper
    step_2_whisper(scenes)

    # Step 3: Wan 2.1 Video Generation
    step_3_wan_video(scenes)

    # Step 4: Write Props
    props_path = step_4_serialize_props(scenes)

    # Step 5: Remotion Render
    raw_video = step_5_remotion_render(props_path)

    # Step 6: Mastering
    final_video = step_6_ffmpeg_mastering(raw_video, props_path)

    elapsed = time.time() - start_time
    logger.info(f"🎉 Pipeline successfully completed in {elapsed:.1f}s ({elapsed/60:.2f} min)!")
    logger.info(f"FINAL DELIVERABLE: {final_video}")
    print(f"OUTPUT_VIDEO: {final_video}")


if __name__ == "__main__":
    main()
