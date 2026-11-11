#!/usr/bin/env bash
# Poll a job until done, then report the output file.
JOB_ID=$(cat /tmp/amds_job_id.txt | cut -d= -f2)
OUT=/opt/data/workspace/amds/output/$JOB_ID.mp4
for i in $(seq 1 75); do
  R=$(curl -s -m 3 "http://127.0.0.1:8000/jobs/$JOB_ID" 2>/dev/null || echo '{}')
  STATUS=$(echo "$R" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('status',''),d.get('step',''),str(d.get('error',''))[:100])" 2>/dev/null)
  echo "poll $i: $STATUS"
  case "$STATUS" in
    completed*) echo "DONE -> $OUT"; ls -la "$OUT"; break;;
    failed*) echo "FAILED:"; echo "$R" | python3 -m json.tool; break;;
  esac
  sleep 8
done
