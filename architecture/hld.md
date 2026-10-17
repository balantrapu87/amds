# High-Level Design (HLD): Autonomous Motion Design Video Studio

## 1. System Overview & Objectives

The system is an autonomous, code-driven motion design factory that transforms a natural language topic or brief into a fully mastered vertical or widescreen MP4 video. It replaces the traditional manual 10-step creative workflow (from storyboarding in Excalidraw to encoding in FFmpeg) with a headless, programmatic pipeline orchestrated by a local LLM and rendered across CPU and GPU hardware.

### Key Goals

* **Autonomous Pipeline:** Zero manual GUI intervention from topic brief to final MP4.
* **Deterministic Output:** Absolute frame accuracy using Remotion's frame clock instead of system wall-clock time.
* **Resource Isolation:** Keep LLM weights pinned in GPU VRAM (ROCm/AMD) while offloading parallel Chromium frame rasterization and audio DSP to the multi-core host CPU.
* **Production-Grade Audio:** Automated sidechain ducking and EBU R128 (-16 LUFS) broadcast compliance.

---

## 2. Architecture & Data Flow

```
                      +---------------------------------------+
                      |       Client / Job Trigger            |
                      |   POST /render (Topic, Audio, Config) |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Host System (FastAPI Orchestrator / Docker Network)                               |
|                                                                                   |
|  Phase 1: Semantic Generation & Design Tokenization                              |
|  +-----------------------------------------------------------------------------+  |
|  |  Local LLM Container (llama.cpp server / ROCm on Radeon AI PRO R9700)       |  |
|  |  - Ingests Brief + Schema Guardrails                                        |  |
|  |  - Emits JSON Storyboard Contract (Scene Timing, Copy, Layout, Lucide IDs)  |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          | Storyboard JSON                        |
|                                          v                                        |
|  +-----------------------------------------------------------------------------+  |
|  |  Asset & Design Resolver (Node.js / Python)                                 |  |
|  |  - Injects Penpot Design Tokens (CSS Variables)                             |  |
|  |  - Verifies Fontsource imports (@fontsource/inter)                          |  |
|  |  - Sanitizes SVGs with SVGO (preserving layer IDs for GSAP targeting)       |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          | Hydrated Bundle                        |
|                                          v                                        |
|  Phase 2 & 3: Deterministic Motion Composition & Headless Rasterization           |
|  +-----------------------------------------------------------------------------+  |
|  |  Remotion Multi-Threaded Engine (16 CPU Cores / Headless Chromium)         |  |
|  |  - GSAP Driver: useCurrentFrame() -> Tweens & Easing math                  |  |
|  |  - Three.js: Offscreen WebGL Canvas -> Rotating 3D models & lights         |  |
|  |  - Emits: Raw Video Stream (No Audio)                                       |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          | Raw MP4                                |
|                                          v                                        |
|  Phase 4: Audio Mastering & Final Assembly                                        |
|  +-----------------------------------------------------------------------------+  |
|  |  FFmpeg Mastering Engine                                                    |  |
|  |  - Sidechain Compression (Voiceover ducks BGM volume automatically)         |  |
|  |  - EBU R128 Integrated Normalization (-16 LUFS, -1.5 dBTP)                   |  |
|  |  - Muxing: Merges Mastered Audio + Raw Canvas Video                         |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |                                        |
+------------------------------------------|----------------------------------------+
                                           v
                              +-------------------------+
                              |   Final Stitched MP4    |
                              |  (Delivery File Out)    |
                              +-------------------------+

```

---

## 3. Component Breakdown

| Layer | Component | Hardware Target | Responsibility |
| --- | --- | --- | --- |
| **Orchestration** | FastAPI Worker | System CPU / RAM | Job validation, queue management, process dispatch. |
| **Intelligence** | Qwen3.8-27B-UD-Q6_K.gguf | AMD GPU via ROCm (~20 GB VRAM) | Storyboard JSON generation, typography sizing, Lucide icon tagging. |
| **Asset Pipeline** | SVGO / Fontsource | System Node.js | Strips unnecessary SVG bloat; locks XML IDs; resolves local webfonts. |
| **Motion & 3D** | GSAP + Three.js | Chromium Engine (ANGLE/WebGL) | Deterministic vector transitions, 3D meshes, frame-by-frame canvas updates. |
| **Render Engine** | Remotion Core | 16-Core Host CPU | Parallel frame stitching, headless page evaluation via Chromium. |
| **Audio & Encode** | FFmpeg CLI | System CPU + VCN Encoder | Sidechain ducking filtergraph, loudnorm audio filter, MP4 packaging. |

---

## 4. Hardware Sizing & Concurrency

* **VRAM Partitioning (32 GB Budget):**
* `local-ai-engine`: 20–22 GB resident footprint (Qwen3.8 27B Q6_K_M  --ctx-size 16384).
* `remotion-render`: 2–4 GB dynamic VRAM allocation for ANGLE/WebGL canvas contexts.
* *Safety Margin:* ~6 GB reserved headroom preventing out-of-memory driver crashes.


* **CPU & Thread Pool (16 Physical Cores):**
* LLM inference runs GPU-offloaded (`-ngl 99`), consuming minimal CPU cycles.
* Remotion render concurrency configured to 16 workers, saturating the CPU during the render phase without starving OS I/O.



---

## 5. Security, Storage & Failure Safeguards

* **Data Isolation:** Assets, models, and render artifacts reside on local NVMe volumes (`./models`, `./assets`, `./output`). No media leaves the local machine.
* **Container Boundaries:** `motion-api` runs unprivileged, mounting only local working directories. The `local-ai` container accesses `/dev/kfd` and `/dev/dri` via dedicated render group mappings.
* **Deterministic Time-Stepping:** Strictly ban `Date.now()`, `performance.now()`, or `window.requestAnimationFrame()` inside React components. All scene state must be calculated as a pure function: `State = f(currentFrame, fps)`.
* **SVG Injection Guard:** All SVGO processing executes within an isolated Node execution sandbox to reject malicious XML payloads or external entity expansions (XXE).

---

