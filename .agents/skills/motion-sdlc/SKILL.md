---
name: motion-sdlc
description: Executes the 5-Phase Agentic SDLC (Spec -> Red Test -> Green Implementation -> Quality Gate -> Review Gate) for AI Motion Design Studio.

---

# Motion Studio SDLC Execution Playbook

When tasked with implementing a feature or bugfix in this repository, execute these exact steps in order:

### Step 1: Contract Synchronization (Spec Gate)
1. Inspect `engine/schemas.py` and `remotion/src/types.ts`.
2. Add or modify fields to satisfy the feature requirements.
3. Validate that Pydantic models compile:
   ```bash
   python3 -c "import engine.schemas as s; print('Schemas OK')"
   ```
   *(Note: If a project virtualenv exists, invoke via `.venv/bin/python3`)*.
4. Never proceed to implementation code until contracts in both languages are aligned.

### Step 2: Red Phase (Author Failing Tests)
1. Write a new test file or test case under `tests/` (Pytest) or `remotion/src/__tests__/` (Vitest/Jest).
2. Assert schema validation, edge cases, and expected serialized output.
3. Run the test and confirm failure:
   ```bash
   pytest tests/
   # If frontend test runner is configured in remotion/package.json:
   npm --prefix remotion test -- --run
   ```
4. Record the failure trace. If the test passes immediately, rewrite it to test the actual new capability. The Red phase is satisfied **only** when tests fail with expected assertions.

### Step 3: Green Phase (Minimal Implementation)
1. Write the minimal code in `engine/` or `remotion/src/` to satisfy the failing test.
2. In Remotion, strictly adhere to the Deterministic Frame Law:
   - Derivation must come strictly from `useCurrentFrame()` and `useVideoConfig()`.
   - Never use `Date.now()`, `Math.random()`, or unbounded `requestAnimationFrame()`.
3. Preserve existing architectural patterns (`<Series>`, `<Sequence>`, `<ThreeScene>`, `<KineticScene>`).
4. Ensure vector assets preserve IDs and classes per `remotion/svgo.config.mjs` for GSAP targeting.

### Step 4: Quality Gate & Automated Self-Healing Loop

Track the loop iteration counter (`ATTEMPT ∈ {1, 2, 3}`). Run each gate sequentially without masking exit codes (do **not** append `|| true`):

```bash
# Tier 1: Static Type Analysis
python3 -m mypy engine/schemas.py engine/api.py
npm --prefix remotion run build -- --bundle-cache=false

# Tier 2: Automated Test Suites
pytest tests/
# If frontend test runner is configured in remotion/package.json:
npm --prefix remotion test -- --run

# Tier 3: Headless Chromium Frame Rasterization
(cd remotion && npx remotion still src/index.ts MainComposition /tmp/smoke.png \
  --props='{"scenes":[],"theme":{}}' \
  --gl=angle \
  --overwrite)
```

#### Self-Healing & Rollback Policy

* **On Failure (Attempt 1 or 2):**
  1. Capture the exact file path, failing line number, and stderr/traceback.
  2. Implement a minimal, targeted patch strictly addressing the reported error.
  3. Increment `ATTEMPT` and restart Tier 1.

* **On Failure (Attempt 3 - Budget Exhausted):**
  Halt speculative modifications immediately and revert only the changed and created feature files (never perform a blanket global clean):
  ```bash
  # Tier 4 Exhaustion Fallback: Target only feature code scopes
  git restore --staged --worktree engine/ remotion/ tests/
  git clean -fd engine/ remotion/ tests/
  rm -f /tmp/smoke.png
  echo "Quality gate failed after 3 attempts. Target code paths restored to clean baseline."
  exit 1
  ```
  *(Alternative to preserve work for post-mortem analysis: `git stash push -u -m "sdlc-failed-attempt-$(date +%s)" -- engine/ remotion/ tests/`)*

* **On Success (All Tiers Exit 0):**
  Remove transient artifacts, create the verified commit, and proceed to Step 5:
  ```bash
  rm -f /tmp/smoke.png
  git add engine/ remotion/ tests/
  git commit -m "feat(motion-sdlc): implement verified feature with green test gate"
  ```

### Step 5: Automated Code Review & PR Gate (Review Gate)

1. Run the Code Review Agent against the verified commit:
   ```bash
   ./scripts/code_review_agent.sh HEAD "feat(motion-sdlc): verify feature implementation" prompts/code_review_system_prompt.txt
   ```
2. The agent executes automated architectural and security diff analysis:
   - Queries local `llama-swap` using `qwen-coder` (designated coding and code review model).
   - Assesses Deterministic Frame Law, dual-schema synchronization, audio mastering curve, and OWASP safety.
   - Auto-resolves or creates the GitHub PR using `gh pr create` and submits structured inline line comments and review verdict.
   *(Note: `qwen` is reserved for creative narrative thinking and storyboard synthesis in `engine/api.py`)*.
3. Review Resolution:
   - **`APPROVE`:** All quality tiers and code review checks pass. The feature is verified and ready for merge.
   - **`REQUEST_CHANGES`:** Treat inline comments as red test assertions. Apply targeted minimal patches addressing each review comment, then rerun Step 4 Quality Gate and Step 5 Review Gate.
   - **`COMMENT`:** Review informational notes and resolve non-blocking improvements.

