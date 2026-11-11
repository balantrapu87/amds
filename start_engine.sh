#!/usr/bin/env bash
# Start the AMDS FastAPI engine with the llama-swap-backed local config.
# Usage:
#   ./start_engine.sh            # foreground
#   ./start_engine.sh --daemon   # background, log + pidfile in /tmp
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# shellcheck disable=SC1091
source ./.env.local

if [[ -x ./.venv/bin/uvicorn ]]; then
    UVICORN=(./.venv/bin/uvicorn)
else
    UVICORN=(python3 -m uvicorn)
fi

if [[ "${1:-}" == "--daemon" ]]; then
    if curl -sf -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "AMDS engine already running on :8000"
        exit 0
    fi

    nohup "${UVICORN[@]}" engine.api:app --host 0.0.0.0 --port 8000 \
        >>/tmp/amds-engine.log 2>&1 &
    echo $! >/tmp/amds-engine.pid

    for _ in $(seq 1 30); do
        if curl -sf -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then
            echo "AMDS engine started (pid $(cat /tmp/amds-engine.pid)); log: /tmp/amds-engine.log"
            exit 0
        fi
        sleep 1
    done

    echo "AMDS engine did not become healthy; last log lines:" >&2
    tail -20 /tmp/amds-engine.log >&2 || true
    exit 1
fi

exec "${UVICORN[@]}" engine.api:app --host 0.0.0.0 --port 8000
