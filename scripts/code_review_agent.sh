#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Autonomous Motion Design Studio — Automated Code Review Agent
# Analyzes git diffs using local/remote LLMs and publishes reviews via GitHub CLI (gh).
# ==============================================================================

# ---------------------------------------------------------------------------
# CLI Argument Validation & Environment Resolution
# ---------------------------------------------------------------------------
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <commit_id> '<user_context>' [path/to/custom_system_prompt.txt]"
  echo "Example: $0 HEAD 'Validate Remotion deterministic math and schema sync'"
  exit 1
fi

COMMIT_ID="$1"
USER_CONTEXT="$2"
CUSTOM_PROMPT_FILE="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}" && if [ -d ".git" ]; then pwd; else cd .. && pwd; fi)"

# Auto-detect workspace default prompt if no custom prompt provided
if [ -z "${CUSTOM_PROMPT_FILE}" ] && [ -f "${WORKSPACE_ROOT}/prompts/code_review_system_prompt.txt" ]; then
  CUSTOM_PROMPT_FILE="${WORKSPACE_ROOT}/prompts/code_review_system_prompt.txt"
fi

# Endpoint & Model Defaults (Local llama-swap/vllm or OpenAI-compatible)
# Coding & code review uses qwen-coder; creative thinking uses qwen
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8080/v1}"
MODEL_NAME="${MODEL_NAME:-qwen-coder}"
OPENAI_API_KEY="${OPENAI_API_KEY:-dummy-key}"
DRY_RUN="${DRY_RUN:-0}"

# ---------------------------------------------------------------------------
# Dependency Verification
# ---------------------------------------------------------------------------
for cmd in git curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[-] Error: Required utility '$cmd' is not installed or not in PATH." >&2
    echo "    Install with: sudo apt-get install -y $cmd" >&2
    exit 1
  fi
done

GH_AVAILABLE=true
if ! command -v gh >/dev/null 2>&1; then
  GH_AVAILABLE=false
fi

# ---------------------------------------------------------------------------
# 1. Extract Diff and Resolve Branch
# ---------------------------------------------------------------------------
echo "==> Resolving commit: ${COMMIT_ID}"
if ! git rev-parse --verify "${COMMIT_ID}^{commit}" >/dev/null 2>&1; then
  echo "[-] Error: Commit '${COMMIT_ID}' does not exist in git history." >&2
  exit 1
fi

FULL_COMMIT_SHA=$(git rev-parse "${COMMIT_ID}")
SHORT_SHA="${FULL_COMMIT_SHA:0:7}"

echo "==> Extracting diff for commit: ${SHORT_SHA} (${FULL_COMMIT_SHA})"
DIFF_CONTENT=$(git show --unified=3 --no-color "${FULL_COMMIT_SHA}")

if [ -z "${DIFF_CONTENT}" ]; then
  echo "[-] Error: Diff is empty or commit has no changes." >&2
  exit 1
fi

# Keep diff snippet bounded to fit comfortably within the LLM KV-cache slot
DIFF_SNIPPET=$(echo "${DIFF_CONTENT}" | head -n 200 || true)

# Resolve local or remote branch containing this commit
BRANCH_NAME=$(git branch --contains "${FULL_COMMIT_SHA}" --format="%(refname:short)" | grep -v 'HEAD' | head -n 1 || true)
if [ -z "${BRANCH_NAME}" ]; then
  BRANCH_NAME="review-${SHORT_SHA}"
fi

# ---------------------------------------------------------------------------
# 2. Build LLM System & User Prompts
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPT="You are a Senior Staff Software Engineer and Automated Code Reviewer.
Your goal is to inspect code diffs for:
1. Logic bugs, edge cases, off-by-one errors, and null/None pointer risks.
2. Security vulnerabilities (OWASP Top 10, sanitization, credentials).
3. Performance regressions, N+1 queries, race conditions, memory leaks.
4. Test coverage completeness and determinism.

Be concise, constructive, and actionable. Return ONLY valid raw JSON with this exact structure:
{
  \"summary\": \"High-level summary of review findings...\",
  \"verdict\": \"APPROVE\",
  \"comments\": [
    {
      \"path\": \"path/to/file.ext\",
      \"line\": 10,
      \"side\": \"RIGHT\",
      \"body\": \"Actionable review comment\"
    }
  ]
}
Note: verdict must be one of: \"APPROVE\", \"REQUEST_CHANGES\", or \"COMMENT\"."

if [ -n "${CUSTOM_PROMPT_FILE}" ] && [ -f "${CUSTOM_PROMPT_FILE}" ]; then
  echo "==> Using custom review prompt: ${CUSTOM_PROMPT_FILE}"
  SYSTEM_PROMPT=$(cat "${CUSTOM_PROMPT_FILE}")
else
  SYSTEM_PROMPT="${DEFAULT_SYSTEM_PROMPT}"
fi

USER_PROMPT="/no_think
### User Context & Review Scope:
${USER_CONTEXT}

### Git Commit Diff:
\`\`\`diff
${DIFF_SNIPPET}
\`\`\`

Provide your concise code review strictly as the requested JSON object without markdown fences or preamble."

# ---------------------------------------------------------------------------
# 3. Query LLM via curl
# ---------------------------------------------------------------------------
echo "==> Requesting structured review from ${MODEL_NAME} at ${OPENAI_BASE_URL}..."

REQUEST_PAYLOAD=$(jq -n \
  --arg model "${MODEL_NAME}" \
  --arg system "${SYSTEM_PROMPT}" \
  --arg user "${USER_PROMPT}" \
  '{
    model: $model,
    messages: [
      {role: "system", content: $system},
      {role: "user", content: $user}
    ],
    temperature: 0.1,
    max_tokens: 4098,
    response_format: {type: "json_object"}
  }')

if ! RAW_RESPONSE=$(curl --noproxy "*" -sS "${OPENAI_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${REQUEST_PAYLOAD}" 2>&1); then
  echo "[-] Error: Failed to connect to LLM endpoint at ${OPENAI_BASE_URL}/chat/completions" >&2
  echo "    Details: ${RAW_RESPONSE}" >&2
  echo "    Ensure local-ai (llama-swap/vllm) or OPENAI_BASE_URL is reachable." >&2
  exit 1
fi

# Extract assistant content (or fallback to reasoning_content if content is empty)
LLM_CONTENT=$(echo "${RAW_RESPONSE}" | jq -r '.choices[0].message.content // empty' 2>/dev/null || true)
if [ -z "${LLM_CONTENT}" ]; then
  LLM_CONTENT=$(echo "${RAW_RESPONSE}" | jq -r '.choices[0].message.reasoning_content // empty' 2>/dev/null || true)
fi

if [ -z "${LLM_CONTENT}" ]; then
  echo "[-] Error: LLM returned empty response or unparseable payload." >&2
  echo "${RAW_RESPONSE}" >&2
  exit 1
fi

CLEAN_JSON=$(echo "${LLM_CONTENT}" | sed -e 's/^```json//g' -e 's/^```//g' -e 's/```$//g' | jq '.' 2>/dev/null || true)

# Fallback: extract JSON object if surrounded by markdown commentary
if [ -z "${CLEAN_JSON}" ] || [ "${CLEAN_JSON}" = "null" ]; then
  CLEAN_JSON=$(echo "${LLM_CONTENT}" | grep -Pzo '(?s)\{.*\}' | tr -d '\0' | jq '.' 2>/dev/null || true)
fi

# Validate JSON parsing
if [ -z "${CLEAN_JSON}" ] || [ "${CLEAN_JSON}" = "null" ]; then
  echo "[-] Error: Failed to parse valid JSON from LLM output." >&2
  echo "Raw LLM output:" >&2
  echo "${LLM_CONTENT}" >&2
  exit 1
fi

VERDICT=$(echo "${CLEAN_JSON}" | jq -r '.verdict // "COMMENT"')
SUMMARY=$(echo "${CLEAN_JSON}" | jq -r '.summary // "No summary provided."')
INLINE_COMMENTS=$(echo "${CLEAN_JSON}" | jq '.comments // []')

echo "======================================================================"
echo "                   🤖 Automated Code Review Result                    "
echo "======================================================================"
echo "Commit:  ${SHORT_SHA} (${BRANCH_NAME})"
echo "Verdict: ${VERDICT}"
echo ""
echo "Summary:"
echo "${SUMMARY}"
echo ""
COMMENTS_COUNT=$(echo "${INLINE_COMMENTS}" | jq 'length')
echo "Inline Comments: ${COMMENTS_COUNT}"
if [ "${COMMENTS_COUNT}" -gt 0 ]; then
  echo "${INLINE_COMMENTS}" | jq -r '.[] | " - [\(.path):\(.line)] \(.body)"'
fi
echo "======================================================================"

# ---------------------------------------------------------------------------
# 4. Check or Create PR using `gh`
# ---------------------------------------------------------------------------
if [ "${GH_AVAILABLE}" = "false" ]; then
  echo "[!] GitHub CLI ('gh') is not installed. Skipping remote PR submission."
  echo "    To submit PRs: sudo apt-get install -y gh && gh auth login"
  if [ "${VERDICT}" = "REQUEST_CHANGES" ]; then
    echo "[-] Verdict is REQUEST_CHANGES. Halting SDLC gate." >&2
    exit 1
  fi
  exit 0
fi

if [ "${DRY_RUN}" = "1" ]; then
  echo "==> DRY_RUN=1 enabled. Skipping remote GitHub operations."
  if [ "${VERDICT}" = "REQUEST_CHANGES" ]; then
    exit 1
  fi
  exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "[!] GitHub CLI is not authenticated. Skipping remote PR submission."
  echo "    Authenticate with: gh auth login"
  if [ "${VERDICT}" = "REQUEST_CHANGES" ]; then
    echo "[-] Verdict is REQUEST_CHANGES. Halting SDLC gate." >&2
    exit 1
  fi
  exit 0
fi

echo "==> Resolving Pull Request for branch '${BRANCH_NAME}'..."

# Locate existing PR for branch
PR_NUMBER=$(gh pr list --head "${BRANCH_NAME}" --state open --json number --jq '.[0].number // empty' 2>/dev/null || true)

if [ -z "${PR_NUMBER}" ]; then
  echo "==> No open PR found for branch '${BRANCH_NAME}'. Creating one..."
  # Ensure the branch is pushed to origin
  git push -u origin "${BRANCH_NAME}" 2>/dev/null || true

  PR_URL=$(gh pr create \
    --head "${BRANCH_NAME}" \
    --title "Code Review: ${USER_CONTEXT}" \
    --body "Automated review for commit \`${COMMIT_ID}\`.\n\n**Scope:** ${USER_CONTEXT}")
  PR_NUMBER=$(echo "${PR_URL}" | grep -oE '[0-9]+$')
  echo "==> Created PR #${PR_NUMBER} (${PR_URL})"
else
  echo "==> Found existing open PR #${PR_NUMBER}"
fi

# ---------------------------------------------------------------------------
# 5. Submit GitHub Review via `gh api`
# ---------------------------------------------------------------------------
echo "==> Submitting review and inline line comments via gh api..."

# Map LLM verdict to GitHub Review event type
case "${VERDICT}" in
  "APPROVE")
    EVENT_TYPE="APPROVE"
    ;;
  "REQUEST_CHANGES")
    EVENT_TYPE="REQUEST_CHANGES"
    ;;
  *)
    EVENT_TYPE="COMMENT"
    ;;
esac

REVIEW_BODY="### 🤖 Automated Code Review

**Verdict:** \`${EVENT_TYPE}\`

${SUMMARY}"

# Format REST payload: repos/{owner}/{repo}/pulls/{pull_number}/reviews
REVIEW_PAYLOAD=$(jq -n \
  --arg body "${REVIEW_BODY}" \
  --arg event "${EVENT_TYPE}" \
  --arg commit_id "${FULL_COMMIT_SHA}" \
  --argjson comments "${INLINE_COMMENTS}" \
  '{
    commit_id: $commit_id,
    body: $body,
    event: $event,
    comments: $comments
  }')

gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/{owner}/{repo}/pulls/${PR_NUMBER}/reviews" \
  --input - <<< "${REVIEW_PAYLOAD}" > /dev/null

echo "==> Successfully submitted review on PR #${PR_NUMBER}!"

if [ "${EVENT_TYPE}" = "REQUEST_CHANGES" ]; then
  echo "[-] Code review requested changes on commit ${SHORT_SHA}." >&2
  exit 1
fi

echo "==> Review gate passed successfully."
exit 0
