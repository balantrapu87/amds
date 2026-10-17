# TASK: Low-Level Design (LLD) & Implementation Spec for Autonomous Motion Design Studio

You are acting as a Principal Systems & Graphics Architect. You are tasked with generating the complete, production-ready Low-Level Design (LLD) and core implementation files for the Autonomous Motion Studio based on the provided HLD (architecture/hld.md).

## Context & Target Environment
- Host OS: Ubuntu 24.04 LTS
- Hardware: AMD Ryzen 9 9950X (16 physical cores, 32 threads), 64 GB DDR5, AMD Radeon AI PRO R9700 (32 GB VRAM)
- Runtimes: Docker Engine, Node.js 22 LTS, Python 3.12, FFmpeg 6.x+, Remotion 4.x

## Required LLD Deliverables
Produce a comprehensive technical implementation document that includes:

### 1. Detailed Schema Specifications
- Provide the complete Pydantic v2 data models for:
  - `ThemeTokens` (colors, font family, padding, radii)
  - `SceneNode` (ID, frame start, duration, layout type, Lucide icon ID, Three.js mesh/camera parameters, text elements)
  - `AudioManifest` (voiceover path, BGM path, target LUFS, ducking sensitivity)
  - `StudioJobPayload` (root container contract with validation rules)

### 2. Remotion Composition Architecture (TypeScript / React)
- Write the complete code for `src/Root.tsx` registering `MainComposition`.
- Implement `src/MainComposition.tsx` which maps over scenes using `<Series>` or `<Sequence>`.
- Implement `src/components/ThreeScene.tsx`:
  - Show how `@react-three/fiber` integrates with Remotion.
  - Implement deterministic scene rotation driven by `useCurrentFrame()` instead of `useFrame()`.
- Implement `src/components/KineticScene.tsx`:
  - Show how GSAP timelines are controlled via Remotion frame ticks (`frame / fps`).
  - Render dynamic Lucide icons via `<DynamicIcon name={scene.icon_asset} />`.

### 3. SVGO & Asset Ingestion Subsystem
- Provide the complete `svgo.config.mjs` setup that ensures element IDs and class attributes remain untouched for GSAP programmatic selectors.
- Write the Node script that ingests raw SVGs, validates them, and caches them in the bundle.

### 4. Headless FastAPI Dispatcher (`engine/api.py`)
- Complete endpoint code for `POST /render`:
  1. Validates incoming payload using Pydantic.
  2. If raw topic brief is provided, calls `http://local-ai:8080/v1/chat/completions` with grammar/schema enforcement.
  3. Writes `props.json` to the filesystem.
  4. Spawns `npx remotion render` as a tracked background sub-process with concurrency set to 16.
  5. Triggers the FFmpeg audio mastering filtergraph on render completion.
  6. Returns job status and final file path.

### 5. Deterministic Audio Mastering Filtergraph
- Provide the exact FFmpeg command string and filter_complex breakdown covering:
  - BGM baseline level scaling.
  - Two-channel sidechain compression (`sidechaincompress`) keyed to the voice track.
  - Auto-ducking curve parameters (threshold, ratio, attack, release).
  - EBU R128 `loudnorm` filter pass.
  - Stream muxing without re-encoding the video track (`-c:v copy`).

### 6. Deployment Scripts
- Provide a complete `docker-compose.yml` for:
  - `fastapi-engine` (ROCm-enabled)
  - `remotion-worker` (headless chromium)
  - `llm-server` (Qwen3.8 --ctx-size 16384 uses existing llama-swap) 
- Provide a `quickstart.sh` script that:
  1. Pulls images and builds containers.
  2. Runs `docker compose up`.
  3. POSTs a sample payload to `/render`.
  4. Follows the job status until completion.
  5. Saves the final MP4 to a local `./output` directory.

Generate clean, production-grade code and configuration files without placeholders or omitted boilerplate.