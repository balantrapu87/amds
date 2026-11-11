#!/usr/bin/env bash
# Submit an AMDS payload to POST /render and poll until the job completes.
# Usage: scripts/run_job.sh [jobs/simple_5s_video.json]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PAYLOAD="${1:-jobs/simple_5s_video.json}"
BASE_URL="${AMDS_BASE_URL:-http://127.0.0.1:8000}"
POLL_INTERVAL="${AMDS_POLL_INTERVAL:-5}"
POLL_ATTEMPTS="${AMDS_POLL_ATTEMPTS:-120}"

if [[ ! -f "$PAYLOAD" ]]; then
    echo "[run_job] payload not found: $PAYLOAD" >&2
    exit 2
fi

if ! curl -sf -m 2 "$BASE_URL/health" >/dev/null 2>&1; then
    echo "[run_job] engine not healthy; starting it detached"
    ./start_engine.sh --daemon
fi

echo "[run_job] submitting $PAYLOAD to POST $BASE_URL/render"
RESP="$(curl -sS -X POST "$BASE_URL/render" \
    -H 'Content-Type: application/json' \
    --data-binary @"$PAYLOAD")"
echo "[run_job] $RESP"

JOB_ID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["job_id"])' "$RESP" 2>/dev/null || true)"
if [[ -z "$JOB_ID" ]]; then
    echo "[run_job] no job_id in response (payload rejected; see body above)" >&2
    exit 1
fi
echo "[run_job] job_id=$JOB_ID"

for i in $(seq 1 "$POLL_ATTEMPTS"); do
    STATUS_JSON="$(curl -sS -m 5 "$BASE_URL/jobs/$JOB_ID" 2>/dev/null || echo '{}')"
    LINE="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get("status",""), d.get("step",""), str(d.get("error") or "")[:200])' "$STATUS_JSON" 2>/dev/null || true)"
    echo "[run_job] poll $i: $LINE"

    case "$LINE" in
        completed*)
            python3 -c 'import json,sys; print("OUTPUT:", json.loads(sys.argv[1]).get("output_path"))' "$STATUS_JSON"
            exit 0
            ;;
        failed*)
            echo "[run_job] job failed" >&2
            printf '%s\n' "$STATUS_JSON" >&2
            exit 1
            ;;
    esac

    sleep "$POLL_INTERVAL"
done

echo "[run_job] timed out after $POLL_ATTEMPTS polls" >&2
exit 1
