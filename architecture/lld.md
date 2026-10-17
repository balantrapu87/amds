# Low-Level Design (LLD): Autonomous Motion Design Studio

## 1. System Architecture & Component Mapping

```
                                +-----------------------------------+
                                | Client / Workflow Orchestrator    |
                                +-----------------+-----------------+
                                                  |
                                                  | POST /render (Job payload or Brief)
                                                  v
+--------------------------------------------------------------------------------------------------------+
|                                  FastAPI Dispatcher (`engine/api.py`)                                  |
|                                                                                                        |
|  1. Ingestion & Validation   <-- Pydantic v2 Models (`engine/schemas.py`)                              |
|  2. Semantic Compilation     --> llama-swap Gateway (http://llama-swap:8080/v1/chat/completions)      |
|  3. Payload Synthesis        --> Serializes deterministic `props.json`                                 |
|  4. Execution Dispatch       --> Async Subprocess: `remotion render` (Concurrency: 16)                 |
|  5. Audio Mastering          --> Deterministic FFmpeg Filtergraph (`engine/audio.py`)                  |
|  6. Final Delivery           --> Artifact saved in `./output/<job_id>.mp4`                             |
+--------------------------------------------------------------------------------------------------------+
        |                                                                           |
        v                                                                           v
+-------------------------------------------------+     +------------------------------------------------+
| Remotion Canvas Renderer (TypeScript / React)   |     | FFmpeg Mastering Subsystem                     |
|                                                 |     |                                                |
| - Root (`src/Root.tsx`): MainComposition        |     | - Inputs: [0:v] raw video, [1:a] VO, [2:a] BGM |
| - Composition (`src/MainComposition.tsx`):      |     | - BGM baseline attenuation & sidechain ducking |
|   `<Series>` sequenced SceneNodes               |     | - Auto-ducking parameters: -18dB thr, 4:1 rat  |
| - 3D Engine (`src/components/ThreeScene.tsx`):  |     | - EBU R128 `loudnorm` (-16 LUFS, -1.5 dBTP)    |
|   `@react-three/fiber` driven by frame ticks    |     | - Direct stream copy for video (`-c:v copy`)   |
| - 2D Engine (`src/components/KineticScene.tsx`):|     +------------------------------------------------+
|   GSAP timeline stepped via `frame / fps`       |
|   Dynamic Lucide icon resolver                  |
+-------------------------------------------------+
```

---

## 2. Complete Schema Specifications

The system is governed by strict Pydantic v2 schemas guaranteeing deterministic scene layouts, valid hex colors, typography specifications, and frame math.

### 2.1 Theme Tokens
- `primary_color`, `secondary_color`, `accent_color`, `background_color`, `text_color` validated with hex regex `^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$`.
- `font_family`: Standardized typography (e.g. `@fontsource/inter`).
- `border_radius`: Pixel corner radius.
- `padding`: Base rem/pixel padding units.

### 2.2 SceneNode
- `id`: Unique slug identifier.
- `scene_type`: Enum of `kinetic_typography` | `three_d_mesh` | `hybrid`.
- `duration_in_frames`: Frame count (at 30 or 60 fps).
- `title`, `subtitle`, `body_text`: Programmatic copy strings.
- `icon_asset`: Valid Lucide icon identifier (e.g. `activity`, `cpu`, `layers`, `zap`).
- `three_params`: Camera FOV, position `[x, y, z]`, mesh geometry type (`box`, `sphere`, `torus`, `icosahedron`), wireframe flag, and rotational speeds.

### 2.3 AudioManifest
- `voiceover_path`: Relative or absolute path to voice WAV/MP3.
- `bgm_path`: Relative or absolute path to background music track.
- `target_lufs`: Target integrated loudness (-16.0 LUFS standard for web/mobile).
- `ducking_threshold`: Sidechain trigger threshold in dB (default `-20.0dB`).
- `ducking_ratio`: Ratio for sidechain compression (default `4.0`).
- `ducking_attack_ms`: Attack envelope in milliseconds (default `15.0ms`).
- `ducking_release_ms`: Release recovery envelope in milliseconds (default `250.0ms`).

### 2.4 StudioJobPayload
- `job_id`: UUID4 string identifier.
- `fps`: Target frame rate (default 30).
- `width` & `height`: Resolution (default `1080x1920` for 9:16 vertical shorts, or `1920x1080` for 16:9).
- `theme`: `ThemeTokens` configuration.
- `audio`: `AudioManifest` specifications.
- `scenes`: Ordered list of `SceneNode` instances.

---

## 3. Remotion Execution Architecture

### 3.1 Pure Function Time Model
In accordance with Remotion's headless architecture:
- `Date.now()`, `performance.now()`, and `requestAnimationFrame()` are prohibited in rendering components.
- GSAP animations must never use `timeline.play()` or real-time tickers. Instead, the timeline is paused at initialization (`gsap.timeline({ paused: true })`), and advanced purely using:
  ```ts
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const timeInSeconds = frame / fps;
  timeline.seek(timeInSeconds);
  ```
- Three.js components render inside `@remotion/three` or `@react-three/fiber` canvas, using `useCurrentFrame()` to update mesh rotational angles:
  ```ts
  meshRef.current.rotation.y = (frame / fps) * rotationSpeedY * Math.PI * 2;
  ```

### 3.2 Dynamic Icon Resolution
Lucide icons are resolved dynamically through `lucide-react/dynamic` or by index lookup, preserving fast bundle resolution while allowing LLM storyboards to choose from the icon catalog.

---

## 4. Asset Ingestion & SVGO Sanitization

To ensure vector elements can be targeted by GSAP selectors (`#layer-accent`, `.kinetic-path`):
- `svgo.config.mjs` is configured with `cleanupIds: false`, `removeUnknownsAndDefaults: false`, and `prefixIds: false`.
- The Node ingestion script validates that SVGs do not contain `<script>` tags or external entity expansions (preventing XXE attacks) before moving them into `public/assets/`.

---

## 5. Headless FastAPI Dispatcher (`engine/api.py`)

The engine provides an asynchronous, non-blocking REST API:
- `POST /render`:
  1. Accepts either a raw `brief` or a pre-compiled `StudioJobPayload`.
  2. If brief is given, queries `http://localhost:8080/v1/chat/completions` (llama-swap / Qwen 3.8 27B) with JSON schema enforcement to produce the storyboard.
  3. Writes `props.json` to temporary job directory.
  4. Spawns `npx remotion render MainComposition out_raw.mp4 --props=props.json --concurrency=16 --gl=angle`.
  5. Runs the FFmpeg sidechain mastering pipeline to mix voiceover and auto-ducked BGM with the video track.
  6. Emits status and final artifact link.
- `GET /jobs/{job_id}`: Polls real-time progress and logs.

---

## 6. Deterministic Audio Filtergraph

```
[1:a] voiceover ----------------------+---> [vo_loud] ----------+
                                      |                         |
[2:a] bgm -------> [bgm_scaled] ------> [sidechaincompress] ----+---> [amix] ---> [loudnorm] ---> [mastered_audio]
                                        (threshold=-20dB,
                                         ratio=4, attack=15ms,
                                         release=250ms)
```

The FFmpeg filtergraph applies sidechain compression so the background music automatically attenuates when speech occurs, followed by EBU R128 loudness normalization (`-16 LUFS`, `-1.5 dBTP`) and muxing into the final MP4 with `-c:v copy`.
