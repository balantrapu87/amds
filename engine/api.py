"""
Headless FastAPI Dispatcher for Autonomous Motion Design Studio.
Manages job validation, LLM storyboard generation via llama-swap,
Remotion multi-core render dispatch, and deterministic audio mastering.
"""

import os
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
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
    SceneLayoutType,
    GeometryType,
    ThreeParams,
)
from engine.audio import execute_mastering

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
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen")
REMOTION_ROOT = os.getenv("REMOTION_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "remotion")))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output")))
JOBS_DIR = os.getenv("JOBS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "jobs")))
RENDER_CONCURRENCY = int(os.getenv("RENDER_CONCURRENCY", "16"))

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
                "id": "scene-1",
                "duration_in_frames": 90,
                "layout_type": "hybrid",
                "title": "Title Here",
                "subtitle": "Subtitle Here",
                "body_text": "Key description here",
                "icon_asset": "cpu",
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
            {"role": "user", "content": user_prompt + f"\nRespond strictly with a JSON object following this shape:\n{json.dumps(schema_example)}"}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
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
        logger.warning(f"LLM semantic generation fallback due to: {e}. Generating deterministic template.")
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
                    id="scene-intro",
                    duration_in_frames=90,
                    layout_type=SceneLayoutType.HYBRID,
                    title=brief[:60] if brief else "Autonomous Motion",
                    subtitle="Generated programmatically via code-driven engine",
                    body_text="Deterministic frame-locked rendering with hardware acceleration",
                    icon_asset="zap",
                    three_params=ThreeParams(geometry=GeometryType.TORUS, wireframe=True)
                ),
                SceneNode(
                    id="scene-deep-dive",
                    duration_in_frames=120,
                    layout_type=SceneLayoutType.KINETIC_TYPOGRAPHY,
                    title="Zero Manual Intervention",
                    subtitle="Chromium headless rasterization + Remotion pure frame clock",
                    body_text="Multi-threaded concurrency pinned across all CPU cores",
                    icon_asset="cpu"
                ),
                SceneNode(
                    id="scene-conclusion",
                    duration_in_frames=90,
                    layout_type=SceneLayoutType.HYBRID,
                    title="Broadcast Audio Standards",
                    subtitle="EBU R128 Loudnorm & Dynamic Sidechain Ducking",
                    body_text="Engineered for web, social and broadcast formats",
                    icon_asset="activity",
                    three_params=ThreeParams(geometry=GeometryType.ICOSAHEDRON, wireframe=True)
                )
            ]
        )


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
        JOB_REGISTRY[job_id]["step"] = "writing_props"

        # 1. Serialize deterministic props.json
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

        # 3. Deterministic Audio Mastering
        logger.info(f"[{job_id}] Executing audio mastering on {raw_video_path}")
        mastered_path = execute_mastering(
            raw_video_path=raw_video_path,
            output_mp4_path=final_video_path,
            audio=job_payload.audio
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
