# Autonomous Motion Studio — Agentic SDLC Framework

An authoritative, zero-redundancy Software Development Life Cycle (SDLC) tailored for **Google Antigravity** operating on the Autonomous Motion Design Studio.

---

## 1. Executive Summary & Design Philosophy

Traditional AI development loops suffer from five critical failure modes:
1. **Contract Divergence:** Python (Pydantic v2) and Remotion (TypeScript) models desynchronize, causing silent runtime deserialization errors.
2. **Animation Non-Determinism:** AI introduces wall-clock time (`Date.now()`), unbounded `requestAnimationFrame()`, or `Math.random()`, corrupting multi-threaded Remotion renders.
3. **Tautological Tests:** Tests written after code that merely echo implementation bugs rather than validating contracts.
4. **Silent Headless Render Failures:** Code passes TypeScript compilation but crashes Chromium ANGLE/WebGL during headless frame rasterization.
5. **Context Thrashing & Gold-Plating:** Agents perform speculative mass edits instead of minimal targeted patches, breaking adjacent scenes.

This framework replaces fragmented sub-agent prompt duplicates and conflicting workflow files with a **single, unified 5-Phase TDD & Code Review Relay** natively integrated into Antigravity workspace rules and skills.

```
+───────────────────────────────────────────────────────────────────────────────────+
│                                 AGENTIC SDLC RELAY                                │
+───────────────────────────────────────────────────────────────────────────────────+
       │
       ▼
 [ Phase 1: Spec Gate ] ──────> Freeze Dual-Language Contracts (Pydantic + TypeScript)
       │                        * Zero business logic allowed
       ▼
 [ Phase 2: Red Gate ]  ──────> Write Failing Tests (pytest + vitest)
       │                        * MUST execute and fail before any code is written
       ▼
 [ Phase 3: Green Gate ] ─────> Minimal Targeted Patch
       │                        * Frame-driven math: (frame, fps) only
       ▼
 [ Phase 4: Quality Gate ] ───> 4-Tier Automated Verification:
       │                        1. Static Typecheck (mypy + tsc)
       │                        2. Test Execution (pytest + npm test)
       │                        3. Headless Smoke Render (npx remotion still)
       │                        4. Bounded Self-Healing Loop (Max 3 retries)
       ▼
 [ Phase 5: Review Gate ] ────> Automated LLM Code Review & PR Submission:
                                1. Inspect diff with domain-specific LLM reviewer
                                2. Enforce determinism, contracts, audio, and OWASP
                                3. Auto-create PR & post inline line reviews via gh CLI
                                4. Bounded review-feedback resolution loop
```

---

## 2. The 5-Phase Agentic SDLC Lifecycle

### Phase 1: Contract & Spec Freeze (`Spec Gate`)
* **Objective:** Establish the immutable source of truth before writing a single line of application code.
* **Actions:**
  1. Define or update Pydantic v2 models in `engine/schemas.py`.
  2. Mirror the definitions into Remotion TypeScript interfaces in `remotion/src/types/`.
  3. Enforce domain invariants:
     - Hex colors strictly validated against `^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$`.
     - Lucide icon names validated against supported token exports.
     - Frame durations and dimensions must be positive, bounded integers.
* **Exit Condition:** Schemas compile with zero syntax/type errors. No feature code is written in this phase.

### Phase 2: Deterministic Test Authoring (`TDD Red Gate`)
* **Objective:** Guarantee measurable regression prevention by authoring executable tests against the Phase 1 contracts.
* **Actions:**
  1. Write unit and contract tests in `tests/` (Pytest) and `remotion/src/__tests__/` (Vitest/Jest).
  2. Assert edge cases: missing fields, out-of-bound frame counts, negative durations, invalid hex codes.
  3. **Mandatory Red Execution:** Execute the test suite using `run_command`:
     ```bash
     pytest tests/test_feature.py
     npm --prefix remotion test
     ```
* **Exit Condition:** The newly added tests **MUST FAIL** with clear, expected assertion errors. If a test passes before implementation exists, it is invalid and must be rewritten.

### Phase 3: Targeted Implementation (`TDD Green Gate`)
* **Objective:** Produce minimal sufficient code to satisfy the failing tests.
* **Rules of Engagement:**
  1. **Strict Determinism Law:** All visual transformations must derive strictly from `(frame, fps)` via `useCurrentFrame()`. Never use `Date.now()`, `Math.random()`, or wall-clock timing.
  2. **Minimal Patching:** Modify only the necessary functions or components. Do not rewrite unrelated files.
  3. **Asset Ingestion Compliance:** SVG icons and assets must preserve ID and class attributes per `remotion/svgo.config.mjs` for GSAP selector compatibility.
* **Exit Condition:** Source code is fully drafted with zero placeholder ellipses or pseudocode.

### Phase 4: Multi-Tier Verification & Headless Smoke Render (`Quality Gate`)
* **Objective:** Prevent silent pipeline failures through a rigorous 4-tier verification gate.
* **Execution Pipeline:**
  1. **Tier 1 (Type Checking):**
     ```bash
     python -m mypy engine/
     npm --prefix remotion run build -- --bundle-cache=false
     ```
  2. **Tier 2 (Test Convergence):**
     ```bash
     pytest tests/
     npm --prefix remotion test
     ```
  3. **Tier 3 (Headless Smoke Render):**
     Rasterize a single representative still frame using Remotion headless Chromium to verify WebGL/Three.js shader compilation:
     ```bash
     npx --prefix remotion remotion still src/index.ts MainComposition output/smoke_test.png --props='{"scenes":[],"theme":{}}'
     ```
  4. **Tier 4 (Bounded Self-Healing):**
     - If any step fails, extract the exact file, line number, and stack trace.
     - Implement a targeted fix and re-run Tier 1–3.
     - **Max Retries:** 3 iterations. If the gate does not turn green in 3 attempts, roll back the branch and halt.
* **Exit Condition:** All 3 tiers pass with Exit Code 0.

### Phase 5: Automated LLM Code Review & PR Gate (`Review Gate`)
* **Objective:** Ensure architectural compliance, determinism invariants, security, and schema synchronization through automated LLM diff inspection and GitHub PR line comments before merge.
* **Actions:**
  1. Trigger `scripts/code_review_agent.sh` against the verified commit:
     ```bash
     ./scripts/code_review_agent.sh HEAD "feat(motion-sdlc): verify feature implementation" prompts/code_review_system_prompt.txt
     ```
  2. The agent executes automated static & architectural diff analysis:
     - Extracts the commit git diff and queries the local LLM (`OPENAI_BASE_URL`).
     - Assesses Deterministic Frame Law, dual-schema sync, audio mastering rules, and OWASP safety.
     - Auto-resolves or creates the GitHub PR using `gh pr create`.
     - Submits structured PR reviews with inline line comments and verdict (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`).
  3. Bounded Review-Feedback Healing Loop:
     - **`APPROVE`:** Quality Gate and Review Gate complete. PR is approved and ready for merge.
     - **`REQUEST_CHANGES`:** Treat inline comments as red test assertions. Apply targeted minimal patches addressing each review comment, then rerun Phase 4 (Quality Gate) and Phase 5 (Review Gate).
     - **`COMMENT`:** Inspect non-blocking recommendations.
* **Exit Condition:** LLM code reviewer returns verdict `APPROVE`.

---

## 3. Antigravity Native Workspace Architecture

Antigravity natively discovers customizations through `.agents/` (or `.agent/`). We organize the project into **Rules** (unconditional guardrails) and **Skills** (procedural runbooks).

```
AI Motion Design Studio/
├── .agents/
│   ├── rules/
│   │   ├── 01-sdlc-guardrails.md         # Invariants: TDD, determinism, audio, code review
│   │   └── 02-hardware-constraints.md     # 9950X concurrency, VRAM budget, headless ANGLE
│   └── skills/
│       └── motion-sdlc/
│           └── SKILL.md                  # Complete 5-phase execution runbook for Antigravity
├── engine/                               # Python FastAPI backend & Pydantic models
│   ├── api.py
│   ├── audio.py
│   └── schemas.py
├── prompts/                              # Prompts & system instructions
│   ├── Agentic-SDLC.md                   # SDLC Master Specification
│   └── code_review_system_prompt.txt     # Specialized automated code reviewer prompt
├── remotion/                             # TypeScript Remotion video composition engine
│   ├── src/
│   ├── package.json
│   └── svgo.config.mjs
├── scripts/                              # Automation & SDLC runners
│   ├── code_review_agent.sh              # Automated LLM code review & PR agent
│   ├── run_sdlc_gate.sh                  # 5-Phase SDLC Quality & Review runner
│   └── setup_review_agent.sh             # Dependency & LLM connectivity checker
└── tests/                                # Backend integration & contract test suites
```

### Slash-Command Alignment
Instead of inventing custom unsupported workflow syntaxes, this SDLC maps directly to Antigravity's native modalities:
* **/plan**: Used by the developer or agent at the start of a feature to draft the Phase 1 schema diff and Phase 2 test matrix.
* **/goal**: Used when delegating end-to-end autonomous execution of the Red-Green-Verify loop to ensure Antigravity will not stop until all Quality Gates pass.

---

## 4. Concrete Workspace Rule: `01-sdlc-guardrails.md`

Save this file to `.agents/rules/01-sdlc-guardrails.md` so Antigravity automatically enforces it on every turn:

```markdown
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
```

---

## 5. Concrete Antigravity Skill: `motion-sdlc/SKILL.md`

Save this file to `.agents/skills/motion-sdlc/SKILL.md`. Antigravity progressively activates this skill when executing feature development:

```markdown
---
name: motion-sdlc
description: Executes the 5-Phase Agentic SDLC (Spec -> Red Test -> Green Implementation -> Quality Gate -> Review Gate) for AI Motion Design Studio.
---

# Motion Studio SDLC Execution Playbook

When tasked with implementing a feature or bugfix, execute these exact steps in order:

### Step 1: Contract Synchronization
1. Inspect `engine/schemas.py` and `remotion/src/types/`.
2. Add or modify fields to satisfy the feature requirements.
3. Validate that Pydantic models compile:
   `python3 -c "import engine.schemas as s; print('Schemas OK')"`

### Step 2: Red Phase (Author Failing Tests)
1. Write a new test file or test case under `tests/test_<feature>.py`.
2. Assert schema validation, edge cases, and expected serialized output.
3. Run the test and confirm failure:
   `pytest tests/test_<feature>.py`
   Record the failure trace.

### Step 3: Green Phase (Minimal Implementation)
1. Write the minimal code in `engine/` or `remotion/src/` to satisfy the failing test.
2. Ensure Remotion components hook into `useCurrentFrame()` and `useVideoConfig()`.

### Step 4: Quality Gate & Smoke Render
1. Run static type analysis:
   `python3 -m mypy engine/schemas.py engine/api.py`
   `npm --prefix remotion run build`
2. Run full test suite:
   `pytest tests/`
3. Execute smoke render:
   `npx --prefix remotion remotion still src/index.ts MainComposition /tmp/smoke.png`
4. If any error occurs, perform root-cause isolation and patch (up to 3 iterations).
5. On success, create the verified commit:
   `git commit -m "feat(motion-sdlc): implement verified feature with green test gate"`

### Step 5: Automated Code Review & PR Gate
1. Run the code review agent against the verified commit:
   `./scripts/code_review_agent.sh HEAD "feat(motion-sdlc): verify feature implementation" prompts/code_review_system_prompt.txt`
2. If `REQUEST_CHANGES` is returned, address inline comments and repeat the quality gate.
3. Once `APPROVE` is returned, submit or merge the GitHub PR.
```

---

## 6. Mistake-Reduction Matrix

| Failure Mode | Root Cause | SDLC Gate | Automated Guardrail |
| :--- | :--- | :--- | :--- |
| **Python / Remotion Type Mismatch** | Modifying backend payload without updating frontend types. | **Phase 1 (Spec Gate)** | Dual-contract synchronization requirement + contract serialization tests. |
| **Animation Flickering or Frame Skipping** | Using wall-clock time or unseeded random generators in Three.js/GSAP. | **Phase 3 (Green Gate)** | Global Rule: Deterministic Frame Law. Disallows `Date.now()` and `Math.random()`. |
| **Broken Headless WebGL / Chromium Crash** | Three.js shader or DOM element fails in headless Chromium sandbox. | **Phase 4 (Quality Gate)** | Mandatory Tier 3 Smoke Render (`npx remotion still`) before task completion. |
| **False-Positive Tests** | Tests written after implementation that confirm bugs as features. | **Phase 2 (Red Gate)** | TDD Red Gate: Agent must execute tests and verify failure before authoring code. |
| **Runaway Edit Thrashing** | Agent modifies whole files repeatedly when a test fails. | **Phase 4 (Quality Gate)** | Bounded Self-Healing: Max 3 retries with stack-trace extraction or automated rollback. |
| **Audio Ducking Clipping** | Altering audio filter without verifying LUFS normalization. | **Phase 4 (Quality Gate)** | Audio mastering contract test verifying EBU R128 (-16 LUFS) compliance. |
| **Architectural or Security Regression** | Code passes unit tests but violates domain laws, schema parity, or OWASP. | **Phase 5 (Review Gate)** | Automated LLM Code Review Agent checks commit diff, generates inline GitHub PR comments, and blocks on `REQUEST_CHANGES`. |

---

## 7. Fast-Reference Checklist for Antigravity

Before marking any motion feature complete, verify every checkbox:

- [ ] **Contract Frozen:** `engine/schemas.py` and `remotion/src/types/` are synchronized.
- [ ] **Red Phase Proven:** Test was created and executed in a failing state first.
- [ ] **Deterministic Math:** No `Date.now()`, `Math.random()`, or wall-clock dependencies.
- [ ] **Static Analysis Clean:** `mypy` and `tsc` emit 0 errors.
- [ ] **Test Suite Green:** All `pytest` and `npm test` checks pass.
- [ ] **Headless Render Verified:** Remotion smoke still rendered without Chromium/WebGL exceptions.
- [ ] **Automated Review Passed:** `scripts/code_review_agent.sh` returned verdict `APPROVE`.