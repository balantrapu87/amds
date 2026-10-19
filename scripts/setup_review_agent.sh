#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Autonomous Motion Design Studio — Code Review Agent Setup & Health Check
# ==============================================================================

echo "======================================================================"
echo "    🔍 Verifying Prerequisites for Autonomous Code Review Agent       "
echo "======================================================================"

MISSING_PKGS=()

for cmd in jq curl git; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "  [✓] $cmd is installed ($(command -v "$cmd"))"
  else
    echo "  [✗] $cmd is NOT installed."
    MISSING_PKGS+=("$cmd")
  fi
done

if command -v gh >/dev/null 2>&1; then
  echo "  [✓] gh (GitHub CLI) is installed ($(command -v "$cmd"))"
  if gh auth status >/dev/null 2>&1; then
    echo "  [✓] gh is authenticated with GitHub"
  else
    echo "  [!] gh is installed but not authenticated. Run: gh auth login"
  fi
else
  echo "  [✗] gh (GitHub CLI) is NOT installed."
  MISSING_PKGS+=("gh")
fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
  echo ""
  echo "[-] Missing dependencies detected: ${MISSING_PKGS[*]}"
  echo "    Install them on Ubuntu / Debian with:"
  echo "    sudo apt-get update && sudo apt-get install -y ${MISSING_PKGS[*]}"
  echo ""
  echo "    If 'gh' is not in standard apt repos, follow official instructions:"
  echo "    https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
fi

# Ensure all scripts are executable
chmod +x "$(dirname "${BASH_SOURCE[0]}")"/*.sh 2>/dev/null || true
if [ -f "$(dirname "${BASH_SOURCE[0]}")/../code_review_agent.sh" ]; then
  chmod +x "$(dirname "${BASH_SOURCE[0]}")/../code_review_agent.sh" 2>/dev/null || true
fi

echo ""
echo "==> Checking LLM inference endpoint & models..."
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8080/v1}"
if MODELS_JSON=$(curl --noproxy "*" -s -f -m 5 "${OPENAI_BASE_URL}/models" 2>/dev/null); then
  echo "  [✓] LLM endpoint is REACHABLE at ${OPENAI_BASE_URL}"
  if echo "${MODELS_JSON}" | grep -q '"qwen-coder"'; then
    echo "  [✓] Model 'qwen-coder' is available (designated for coding & code review)"
  else
    echo "  [!] Warning: Model 'qwen-coder' not found in models list."
  fi
  if echo "${MODELS_JSON}" | grep -q '"qwen"'; then
    echo "  [✓] Model 'qwen' is available (designated for thinking & creative writing)"
  else
    echo "  [!] Warning: Model 'qwen' not found in models list."
  fi
else
  echo "  [!] LLM endpoint at ${OPENAI_BASE_URL} is currently unreachable."
  echo "      Make sure your local LLM container (llama-swap/vllm) or remote API is active."
fi

echo "======================================================================"
echo "Setup check complete."
