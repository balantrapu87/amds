# Jarvis-Amds — Conventions (authoritative for all future renders)

## Screen geometry (9:16, 1080x1920)
- Safe-area buffers for platform UI overlays (Shorts, TikTok, Instagram):
  - LEFT: 7–12% free space
  - TOP: 7–12% free space
  - RIGHT: 10–15% free space
  - BOTTOM: 10–15% free space
- All content (cards, headlines, icons, captions) must live inside the safe area.

## Captions
- Word-level, audio-synced via Whisper timings.
- Show exactly ONE word at a time (no rolling multi-word window).
- Position: top band, single line, never overlapping card content.
- Brand chip: top-left corner (never top-center — that collides with captions).
- Hidden entirely when no word is active (no full-sentence dumps).

## Pacing
- Audio and captions must be at a human pace — NOT the default TTS speed.
  (User: "captions and audio speed are very fast for humans.")
- Scenes auto-extend to fit narration (Whisper is the length authority) — keep this.

## Visuals
- Shared dark glassmorphism background across ALL scenes (no per-scene background changes, no 3D wireframe geometry).
- Frames must explain using pictures, diagrams AND icons — not text + one icon only.
- Fill vertical space: generated explainer images can act as fillers between content blocks.
- The LLM drafts the storyboard with screen geometry in mind (it must know the 9:16 canvas + safe areas before choosing layout).

## QA (judge step)
- Before stitching, an LLM judge inspects sampled frames:
  - no overlap between captions and content
  - no text clipped or out of safe area
  - no empty dead space dominating the frame
  - icons/images present and legible
- Reject or re-render frames that fail.

## Determinism
- Every pixel is a pure function of the frame clock (no wall time, no drift).
