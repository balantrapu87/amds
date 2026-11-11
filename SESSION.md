# Jarvis-Amds — Session Resume Guide

Autonomous AI video studio. Brief in → mastered 9:16 video out.
Last active: 2026-10-31. Owner: Pawan (Telegram DM 7079318490).

## How to resume
1. Read this file, `CONVENTIONS.md`, and `FEEDBACK.md` in this directory.
2. Restart the engine (it dies when the shell session ends):
   ```
   cd /opt/data/workspace/amds
   # load .env.local (export lines), then:
   .venv/bin/uvicorn engine.api:app --host 0.0.0.0 --port 8000   # detached (start_new_session)
   # verify: curl http://127.0.0.1:8000/health
   ```
3. Submit a render:
   ```
   curl -X POST http://127.0.0.1:8000/render -H 'Content-Type: application/json' -d @jobs/amds_story.json
   ```
   The engine re-bundles Remotion source every job — TSX edits are picked up automatically.
   Pipeline: TTS (edge-tts) → Whisper word timings → Remotion (SwiftShader, CPU) → FFmpeg master.

## Layout
- `engine/` — FastAPI orchestrator (api.py, captions.py, tts.py, schemas.py)
- `remotion/src/` — React/Remotion compositions
  - `MainComposition.tsx` — shared `GlassBackdrop` + per-scene `Series`, brand chip top-left, `TopCaptions` overlaid
  - `components/GlassBackdrop.tsx` — dark glassmorphism, identical for every scene (drifting orbs + grid + sheen)
  - `components/KineticScene.tsx` — 2D text scene: icon badge, headline, subtitle, body
  - `components/TopCaptions.tsx` — word-level karaoke pill, top-center, single line
  - `components/ExplainerSlide.tsx` — 4:5 still-image composition (rendered via `remotion still`)
  - `utils/captions.ts` — pure caption math (getActiveWordIndex, getCaptionWindow)
- `jobs/` — story payloads (`amds_story.json`: theme + scenes with voiceover_text)
- `output/` — rendered MP4s per job id + `output/explainer/` still PNGs
- `FEEDBACK.md` — user review notes (authoritative for next iteration)
- `CONVENTIONS.md` — screen geometry, safe areas, pacing rules

## Current state
- Video renders end-to-end and is verified: shared glass background, single-line top captions, audio-synced.
- 5 explainer stills rendered (`output/explainer/01-brief.png` … `05-delivery.png`).
- Engine concurrency: 4. Whisper timing works (word-level, though many words are ~1ms blips — captions only flash briefly; see FEEDBACK.md for the fix).
- BGM is still a sine-tone mock. Drop a real track in `jobs/` to re-render.

## Open items from user feedback (next iteration)
1. Fill the vertical space — frames are text + one icon only; use the generated images/diagrams as visual fillers between content.
2. LLM must understand 9:16 geometry and compose diagrams/icons/pictures, not just text.
3. Audio + captions are too fast — slow to human pace.
4. Captions: show exactly ONE word at a time (not a rolling window).
5. Safe-area buffers: 7–12% free on left & top, 10–15% on right & bottom (Shorts/TikTok/IG UI overlays).
6. LLM judge step: inspect rendered frames before stitching; reject/clipping-check frames.
