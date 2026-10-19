# Autonomous Motion Studio: Engineering Guardrails

## 1. Deterministic Frame Law
- All animations in Remotion (`ThreeScene`, `KineticScene`) MUST be pure functions of `(frame, fps)`.
- FORBIDDEN: `Date.now()`, `performance.now()`, `Math.random()`, `setInterval()`, `setTimeout()`.
- Randomization must use seeded pseudo-random algorithms keyed to the scene or frame index.

## 2. TDD Quality Gate
- Never write implementation code before a failing test exists in `tests/` or `remotion/src/__tests__/`.
- Every feature PR must include:
  1. Pydantic schema update in `engine/schemas.py`.
  2. TypeScript type update in `remotion/src/types/`.
  3. Passing contract test verifying JSON serialization between Engine and Remotion.

## 3. Hardware & Concurrency Limits
- Target: AMD Ryzen 9 9950X (16 cores, 32 threads) and AMD Radeon AI PRO R9700 (32 GB VRAM).
- Default Remotion render concurrency is 16 (`--concurrency=16`).
- Chromium ANGLE profile must be used for headless WebGL rendering without exceeding 4 GB VRAM per worker.

## 4. Audio Mastering Integrity
- All audio filter modifications must preserve the 2-channel sidechain ducking curve:
  - BGM baseline ducked by voice track (-18 dB threshold, 4:1 ratio).
  - Final output normalized to EBU R128 (-16 LUFS, -1.5 dBTP).
  - Video stream must be copied without re-encoding (`-c:v copy`).

## 5. Automated Code Review Gate
- Before PR merge or feature completion, all commits MUST pass the automated code review agent (`scripts/code_review_agent.sh`).
- The review inspects git diffs against:
  1. Deterministic Frame Law (zero wall-clock or unseeded random calls).
  2. Dual-contract synchronization (Pydantic v2 `engine/schemas.py` <-> TypeScript `remotion/src/types/`).
  3. Audio mastering curve integrity (-18 dB, 4:1 ratio, EBU R128 -16 LUFS).
  4. Security, input sanitization, and headless Chromium ANGLE WebGL compatibility.
- If the agent returns `REQUEST_CHANGES`, the self-healing loop must address all inline line comments before the PR is approved.

