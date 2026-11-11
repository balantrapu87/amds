# AMDS — Autonomous Motion Design Studio

FastAPI engine + Remotion renderer. Submit a storyboard JSON, get a mastered MP4.

## Requirements

- Python virtualenv at `.venv/` with `engine/requirements.txt`
- Node + Remotion dependencies in `remotion/node_modules`
- `ffmpeg` / `ffprobe` on `PATH`
- `.env.local` for local service endpoints (llama-swap via `host.docker.internal:8080`)

## Quick start

```bash
# 1. Start the engine detached (health-checked, logs to /tmp/amds-engine.log)
./start_engine.sh --daemon
curl -s http://127.0.0.1:8000/health

# 2. Submit a payload and poll until the MP4 is ready
./scripts/run_job.sh jobs/simple_5s_video.json
```

`scripts/run_job.sh` starts the engine automatically if `/health` is down, so a
single command is enough:

```bash
./scripts/run_job.sh jobs/amds_story.json
```

## API

| Method | Path               | Purpose                                   |
| ------ | ------------------ | ----------------------------------------- |
| POST   | `/render`          | Accept a render job (returns `job_id`)    |
| GET    | `/jobs/{job_id}`   | Status, step, `output_path`, `error`      |
| GET    | `/health`          | Liveness check                            |

There is no `/submit_job` endpoint. Submit to **`POST /render`**.

### Payload essentials

- `payload.audio` is **required** — at minimum `{"voiceover_path": "..."}`.
  Relative/absolute paths must exist inside the engine environment.
- `payload.theme.border_radius` and `payload.theme.padding` are **integers**
  (`12`, `24`), not CSS strings (`"12px"`).
- `payload.scenes[]` requires `scene_id`, `duration_frames`, and `headline`.
  `render_layer` defaults to `kinetic_typography`.
- `jobs/simple_5s_video.json` is a minimal valid example; `jobs/amds_story.json`
  is the full 5-scene explainer.

Validate a payload without rendering:

```bash
.venv/bin/python - <<'PY'
import json
from engine.schemas import RenderRequest
RenderRequest(**json.load(open("jobs/simple_5s_video.json")))
print("valid")
PY
```

## Layout

- `engine/` — FastAPI orchestrator (`api.py`, `schemas.py`, `tts.py`, `captions.py`, `audio.py`, `video_gen.py`)
- `remotion/src/` — React/Remotion compositions
- `jobs/` — storyboard payloads and per-job artifacts (`jobs/<job_id>/`)
- `output/` — final MP4s
- `start_engine.sh` — foreground/daemon engine launcher
- `scripts/run_job.sh` — submit + poll helper
- `SESSION.md`, `CONVENTIONS.md`, `FEEDBACK.md` — project state and visual rules
