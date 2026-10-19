# GOAL: Execute First End-to-End SDLC Relay for Motion Studio Baseline

You are operating under the `motion-sdlc` skill and `.agents/rules/` guardrails. 

### Reference Architecture & Specifications
- **High-Level Design (HLD):** Follow the approved system topology (decoupled LLM orchestrator, headless Remotion Chromium canvas, FFmpeg sidechain ducking, and 16-thread CPU allocation on the Ryzen 9 9950X).
read /architecture/hld.md

- **Low-Level Design (LLD):** Implement the exact component boundaries, schemas, and determinism constraints established in the approved LLD specification. Do NOT re-architect or introduce alternative libraries.
read /architecture/lld.md


### Step 1: Spec Gate (Contract Synchronization)
1. In `engine/schemas.py`, define the foundational Pydantic v2 models:
   - `ThemeTokens`: `background_hex`, `primary_hex`, `text_hex`, `font_family`.
   - `SceneNode`: `scene_id`, `duration_frames` (minimum 15), `render_layer` (`"three_dimensional"` | `"kinetic_typography"`), `headline`, `icon_asset`.
   - `StoryboardContract`: `fps` (default 30), `width` (default 1080), `height` (default 1920), `theme`, `scenes`.
2. Mirror these interfaces 1:1 into `remotion/src/types/storyboard.ts`.
3. Verify that `engine/schemas.py` compiles with zero errors:

```bash
python3 -c "import engine.schemas as s; print('Schemas OK')"
```

---

### Step 2: Red Phase (Failing Contract & Determinism Tests)

1. Create `tests/test_contracts.py` (Pytest):
* Test that valid JSON parses correctly into `StoryboardContract`.
* Test that invalid hex colors, negative durations, or empty scene lists fail with a `ValidationError`.


2. Create `remotion/src/__tests__/math.test.ts` (Vitest):
* Test a deterministic frame interpolation helper: `frameToRadian(frame, fps, speed)` asserting exact expected values at frames 0, 15, and 30.


3. Run both test suites and **verify failure** (Red state):
```bash
pytest tests/test_contracts.py
npm --prefix remotion test -- --run

```


Confirm that the test runners exit with non-zero codes due to missing implementation.

---

### Step 3: Green Phase (Minimal Implementation)

1. In `remotion/src/utils/math.ts`, implement the pure deterministic `frameToRadian` function.
2. In `remotion/src/Root.tsx` and `remotion/src/MainComposition.tsx`, implement the basic sequence mapper reading from the storyboard contract props.
3. Ensure no visual transformation uses wall-clock time (`Date.now()`) or unseeded `Math.random()`.

---

### Step 4: Quality Gate & Verification

Execute the strict 4-tier check defined in `motion-sdlc`:

```bash
# Tier 1: Type check
python3 -m mypy engine/schemas.py
npm --prefix remotion run build -- --bundle-cache=false

# Tier 2: Unit tests
pytest tests/test_contracts.py
npm --prefix remotion test -- --run

# Tier 3: Headless Chromium smoke render
npx --prefix remotion remotion still src/index.ts MainComposition /tmp/smoke.png --props='{"fps":30,"width":1080,"height":1920,"theme":{"background_hex":"#0b0f19","primary_hex":"#38bdf8","text_hex":"#f8fafc","font_family":"Inter"},"scenes":[{"scene_id":"s1","duration_frames":30,"render_layer":"kinetic_typography","headline":"Test Hook","icon_asset":"Zap"}]}' --gl=angle --overwrite

```

If any tier fails, apply targeted fixes (up to 3 attempts). If all tiers exit with code 0, commit the verified baseline changes to git:
```bash
git commit -m "feat(motion-sdlc): implement verified baseline contracts and determinism tests"
```

---

### Step 5: Automated Code Review Gate

Run the automated code reviewer against the commit:
```bash
./scripts/code_review_agent.sh HEAD "Initial baseline contract and determinism implementation" prompts/code_review_system_prompt.txt
```
Ensure verdict is `APPROVE` before finalizing the baseline.

```

<FollowUp label="Want the baseline `engine/schemas.py` and `remotion/src/types/storyboard.ts` template ready before running?" query="Generate the initial engine/schemas.py and remotion/src/types/storyboard.ts baseline files matching this prompt."/>

```