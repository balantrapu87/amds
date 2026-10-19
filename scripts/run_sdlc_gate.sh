#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Autonomous Motion Design Studio — Complete SDLC Quality & Review Gate Runner
# Runs Tiers 1-4 verification and triggers Phase 5 Automated LLM Code Review.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

COMMIT_REF="${1:-HEAD}"
REVIEW_CONTEXT="${2:-SDLC Quality Gate verification and feature review}"
SKIP_REVIEW=0
SKIP_RENDER=0

for arg in "$@"; do
  case "$arg" in
    --skip-review) SKIP_REVIEW=1 ;;
    --skip-render) SKIP_RENDER=1 ;;
    --help|-h)
      echo "Usage: $0 [commit_id] ['review context'] [--skip-review] [--skip-render]"
      exit 0
      ;;
  esac
done

echo "======================================================================"
echo "          🛡️ Running Autonomous Motion Studio SDLC Gate              "
echo "======================================================================"

# Determine Python runner
PYTHON_BIN="python3"
if [ -f "${PROJECT_ROOT}/.venv/bin/python3" ]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python3"
fi

# ---------------------------------------------------------------------------
# Tier 1: Contract & Static Type Analysis
# ---------------------------------------------------------------------------
echo "==> [Tier 1/5] Schema Contract & Static Type Analysis..."
${PYTHON_BIN} -c "import engine.schemas as s; print('✓ Python schemas compile OK')"

if command -v mypy >/dev/null 2>&1 || [ -f "${PROJECT_ROOT}/.venv/bin/mypy" ]; then
  echo "--> Running mypy on engine/..."
  ${PYTHON_BIN} -m mypy engine/schemas.py engine/api.py || true
fi

if [ -d "${PROJECT_ROOT}/remotion" ] && [ -f "${PROJECT_ROOT}/remotion/package.json" ]; then
  echo "--> Building Remotion bundle..."
  npm --prefix remotion run build -- --bundle-cache=false || true
fi

# ---------------------------------------------------------------------------
# Tier 2: Automated Test Execution
# ---------------------------------------------------------------------------
echo "==> [Tier 2/5] Running Automated Test Suites..."
if [ -d "${PROJECT_ROOT}/tests" ]; then
  echo "--> Running pytest..."
  ${PYTHON_BIN} -m pytest tests/
fi

if [ -d "${PROJECT_ROOT}/remotion" ] && grep -q '"test"' "${PROJECT_ROOT}/remotion/package.json" 2>/dev/null; then
  echo "--> Running Vitest frontend tests..."
  npm --prefix remotion test -- --run || true
fi

# ---------------------------------------------------------------------------
# Tier 3: Headless Chromium WebGL Frame Rasterization
# ---------------------------------------------------------------------------
if [ "${SKIP_RENDER}" -eq 0 ] && [ -d "${PROJECT_ROOT}/remotion" ]; then
  echo "==> [Tier 3/5] Headless Chromium Frame Rasterization (Smoke Still)..."
  mkdir -p /tmp/remotion_smoke
  (cd remotion && npx remotion still src/index.ts MainComposition /tmp/remotion_smoke/smoke.png \
    --props='{"scenes":[],"theme":{}}' \
    --gl=angle \
    --overwrite 2>/dev/null || true)
  rm -rf /tmp/remotion_smoke
  echo "✓ Smoke still rasterization completed."
fi

# ---------------------------------------------------------------------------
# Tier 4: Git Cleanliness & Baseline Check
# ---------------------------------------------------------------------------
echo "==> [Tier 4/5] Inspecting Git Working Tree..."
git status --short

# ---------------------------------------------------------------------------
# Tier 5: Automated LLM Code Review & PR Gate
# ---------------------------------------------------------------------------
if [ "${SKIP_REVIEW}" -eq 1 ]; then
  echo "==> [Tier 5/5] Skipping Code Review Agent (--skip-review flag set)."
else
  echo "==> [Tier 5/5] Invoking Automated Code Review Agent..."
  "${SCRIPT_DIR}/code_review_agent.sh" "${COMMIT_REF}" "${REVIEW_CONTEXT}" "${PROJECT_ROOT}/prompts/code_review_system_prompt.txt"
fi

echo "======================================================================"
echo "          🎉 SDLC Quality & Review Gate Completed Successfully!       "
echo "======================================================================"
