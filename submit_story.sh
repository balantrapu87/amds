#!/usr/bin/env bash
set -euo pipefail
# Submit the drafted explainer video payload and poll to completion.
PAYLOAD=$(cat /opt/data/workspace/amds/jobs/amds_story.json)
RESP=$(curl -s -X POST http://127.0.0.1:8000/render -H 'Content-Type: application/json' -d "$PAYLOAD")
echo "$RESP"
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
echo "JOB_ID=$JOB_ID"
for i in $(seq 1 90); do
  R=$(curl -s -m 3 "http://127.0.0.1:8000/jobs/$JOB_ID" 2>/dev/null || echo '{}')
  STATUS=$(echo "$R" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('status',''),d.get('step',''),str(d.get('error',''))[:120])" 2>/dev/null)
  echo "poll $i: $STATUS"
  case "$STATUS" in completed*|failed*) echo "FINAL: $STATUS"; echo "$R" | python3 -m json.tool; break;; esac
  sleep 8
done
