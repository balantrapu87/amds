---
name: remotion-motion-director
description: Directs deterministic, visually consistent short-form videos in Remotion using definitive hero image assets, tight scene pacing, and pre-planned audio and word-level karaoke captions.
---

# Remotion Motion Director Skill

A disciplined protocol for authoring and verifying high-retention short-form videos (9:16 and 16:9) in Autonomous Motion Design Studio (AMDS) using pure Remotion animations, definitive static assets, tight scene pacing, and audio-synced captions.

---

## Core Tenets

```
┌────────────────────────────────────────────────────────────────────────┐
│                   REMOTION MOTION DIRECTOR PIPELINE                    │
├────────────────────────────────────────────────────────────────────────┤
│  1. Definitive Image Ingestion  -->  Hero PNGs / SVGs with alpha       │
│  2. Consistent Canvas System    -->  Single persistent backdrop & palette │
│  3. Minimal Pacing Law          -->  Scenes tightly cut to spoken words│
│  4. Audio & Word-Sync Gate      -->  100% verified narration & captions│
│  5. Pre-Flight Visual QA        -->  Zero color/font/layout drift      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Always Ask for & Ingest Definitive Images
- **Never guess or prompt AI diffusion for key brand subjects.** Generative video (ComfyUI / Wan) produces color shifting, unstable subjects, and mismatched lighting between shots.
- **Request or specify definitive assets upfront:**
  - **Background**: One hero atmospheric plate (e.g. `assets/stadium_night.jpg` or dark glassmorphic gradient) used consistently across the entire video.
  - **Hero Cutouts**: High-resolution PNGs with transparent backgrounds (e.g. `ipl_trophy.png`, `bcci_logo.png`, `saikia.png`, `money_pile.png`).
  - **Graphic Badges**: Clean SVGs or vector badges (`ban_cross.svg`, `calendar_march.svg`).
- If definitive image assets are missing, prompt the user for them before starting production.

---

## 2. Use Pure Remotion for All Animations
- All dynamic motion is executed programmatically inside Remotion:
  - **Entrances & Exits**: Frame-based GSAP or Remotion `spring({ frame, fps, config })`.
  - **Subject Movement**: Subtle Ken-Burns zoom, float (`Math.sin(frame / 15)`), or directional pop-in.
  - **Background Continuity**: The background plate persists across scene transitions with a continuous, slow camera push (`interpolate(frame, [0, totalFrames], [1.0, 1.08])`).
- **Deterministic Frame Law**: Every visual change must strictly be a pure function of `(frame, fps)`. Never use `Date.now()`, `Math.random()`, or wall-clock timers.

---

## 3. Strict Visual & Color Consistency Check Before Submission
Before rendering or submitting any story payload:
- **Unified Palette**: Confirm the theme tokens in `props.json` or `job.json` use a locked 3-color palette:
  - `background_hex`: Shared dark canvas (e.g. `#0B0F1A`)
  - `primary_hex`: Signature brand tone (e.g. `#3B82F6` or `#22C55E`)
  - `accent_hex`: Eye-catching highlight / gold (e.g. `#F59E0B`)
  - `surface_hex`: Unified frosted card background (e.g. `#111827CC`)
- **No Style Jumping**: Never switch between full-bleed raw video in one scene and a glass card in the next. Keep the layout language (brand chip, card padding, typography) identical across every scene sequence.

---

## 4. Audio, Timing & Caption Planning
- **Narration Authority**: Audio duration dictates visual duration.
- **Word-Level Timing**:
  - Always generate or verify TTS voiceover (`edge-tts`) first.
  - Run transcription (Whisper) to extract exact `[start_ms, end_ms]` timestamps for every spoken word.
- **Caption Placement**:
  - Pinned to the reserved top band or safe lower third (`TopCaptions` / `KaraokeCaptions`).
  - Single active word highlight or tight single-line pill.
  - Must never collide with the brand chip (top-left) or cover hero subject images.

---

## 5. Pre-Submission Audio & Caption Gate
- **Zero-Tolerance Checklist**:
  - [ ] Every scene with a script has a resolved, playable audio file (`audio_file` in Remotion public assets).
  - [ ] Word-level captions array is populated and validated (`end_ms > start_ms >= 0`).
  - [ ] Audio ducking curve verified: BGM ducked by voice track (-18 dB threshold, 4:1 ratio).
  - [ ] EBU R128 normalization target verified (-16 LUFS, -1.5 dBTP).
- **Never trigger final video render or handoff if audio or captions are missing.**

---

## 6. Minimal Scene Length Law
- **No Lingering Dead Air**:
  - Cut each scene immediately after the last spoken word:
    $$\text{duration\_frames} = \text{round}\left(\frac{\text{last\_word\_end\_ms} + 250\text{ms}}{1000} \times \text{fps}\right)$$
  - Keep hook scenes ultra-tight: `1.5s` to `3.5s` maximum.
  - Split complex narrative into fast, snappy micro-scenes (`3s` to `7s`) rather than long static blocks.
- **Respect 9:16 Platform Safe Areas**:
  - Keep all titles, images, and captions within the safe zone: `7-12%` buffer on Left & Top, `10-15%` buffer on Right & Bottom.
