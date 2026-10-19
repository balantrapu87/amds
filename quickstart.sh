#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Quickstart script for Autonomous Motion Design Studio
# Builds containers, starts services, submits render job, and tracks delivery.
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${PROJECT_DIR}/output"
mkdir -p "${OUTPUT_DIR}" "${PROJECT_DIR}/jobs" "${PROJECT_DIR}/assets/audio"

echo "======================================================================"
echo "      🚀 Launching Autonomous Motion Design Studio Engine            "
echo "======================================================================"

# 1. Ensure external docker network exists
if ! docker network inspect llama-swap_default >/dev/null 2>&1; then
    echo "[Network] Creating bridge network 'llama-swap_default'..."
    docker network create llama-swap_default
fi

# 2. Build and start containers
echo "[Compose] Building and launching containers via docker-compose..."
cd "${PROJECT_DIR}"
docker compose build
docker compose up -d fastapi-engine

# 3. Wait for FastAPI health check
echo "[Health] Waiting for Motion API to become ready..."
for i in {1..30}; do
    if curl -s -f http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "✓ Motion API is UP and healthy on port 8000."
        break
    fi
    echo -n "."
    sleep 2
    if [ "$i" -eq 30 ]; then
        echo -e "\n✗ Timeout waiting for Motion API. Check docker logs with: docker logs motion-engine"
        exit 1
    fi
done

# 4. Generate mock audio if not present
VOICEOVER_PATH="/app/jobs/sample_vo.wav"
BGM_PATH="/app/jobs/sample_bgm.wav"

docker exec motion-engine ffmpeg -y -f lavfi -i "sine=frequency=440:duration=6" -c:a pcm_s16le /app/jobs/sample_vo.wav >/dev/null 2>&1 || true
docker exec motion-engine ffmpeg -y -f lavfi -i "sine=frequency=220:duration=6" -c:a pcm_s16le /app/jobs/sample_bgm.wav >/dev/null 2>&1 || true

# 5. Submit sample render job
echo -e "\n[Job Dispatch] Submitting sample render payload to POST /render..."

SAMPLE_PAYLOAD=$(cat <<EOF
{
  "payload": {
    "job_id": "quickstart-demo",
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "theme": {
      "primary_color": "#6366F1",
      "secondary_color": "#8B5CF6",
      "accent_color": "#06B6D4",
      "background_color": "#0F172A",
      "surface_color": "#1E293B",
      "text_color": "#F8FAFC",
      "text_muted_color": "#94A3B8",
      "font_family": "Inter, sans-serif",
      "border_radius": 16,
      "padding": 32
    },
    "audio": {
      "voiceover_path": "${VOICEOVER_PATH}",
      "bgm_path": "${BGM_PATH}",
      "target_lufs": -16.0,
      "true_peak_db": -1.5,
      "ducking_threshold_db": -20.0,
      "ducking_ratio": 4.0,
      "ducking_attack_ms": 15.0,
      "ducking_release_ms": 250.0,
      "bgm_volume_db": -14.0
    },
    "scenes": [
      {
        "id": "scene-intro",
        "duration_in_frames": 60,
        "layout_type": "hybrid",
        "title": "Autonomous Motion",
        "subtitle": "100% Code-Driven Factory",
        "body_text": "Zero manual GUI intervention from storyboard to final mastered MP4.",
        "voiceover_text": "Welcome to the autonomous motion studio, a fully code driven video factory.",
        "icon_asset": "zap",
        "three_params": {
          "geometry": "torus",
          "wireframe": true,
          "camera_fov": 45,
          "camera_position": [0, 0, 5],
          "mesh_position": [0, 0, 0],
          "mesh_scale": [1.2, 1.2, 1.2],
          "rotation_speed_x": 0.2,
          "rotation_speed_y": 0.8,
          "rotation_speed_z": 0.1
        }
      },
      {
        "id": "scene-tech",
        "duration_in_frames": 90,
        "layout_type": "kinetic_typography",
        "title": "GSAP + Chromium Headless",
        "subtitle": "Hardware-Accelerated Frame Ticks",
        "body_text": "Timeline stepped deterministically across 16 parallel CPU workers.",
        "voiceover_text": "Every frame is a pure function of time, stepped across sixteen parallel workers.",
        "icon_asset": "cpu"
      },
      {
        "id": "scene-audio",
        "duration_in_frames": 60,
        "layout_type": "hybrid",
        "title": "EBU R128 Mastered",
        "subtitle": "Auto-Ducking Sidechain Audio",
        "body_text": "Integrated loudness normalization compliant with broadcast standards.",
        "voiceover_text": "Audio is mastered to broadcast loudness, with narration synthesized by local edge TTS.",
        "icon_asset": "activity",
        "three_params": {
          "geometry": "icosahedron",
          "wireframe": true,
          "camera_fov": 45,
          "camera_position": [0, 0, 5],
          "mesh_position": [0, 0, 0],
          "mesh_scale": [1.4, 1.4, 1.4],
          "rotation_speed_x": 0.3,
          "rotation_speed_y": 0.4,
          "rotation_speed_z": 0.0
        }
      }
    ]
  }
}
EOF
)

RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/render \
  -H "Content-Type: application/json" \
  -d "${SAMPLE_PAYLOAD}")

echo "Response: ${RESPONSE}"

JOB_ID=$(echo "${RESPONSE}" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4 || echo "")

if [ -z "${JOB_ID}" ]; then
  echo "✗ Failed to obtain Job ID from response."
  exit 1
fi

echo "✓ Job dispatched with ID: ${JOB_ID}"

# 6. Poll job status until completion
echo -e "\n[Monitoring] Tracking job status at /jobs/${JOB_ID}..."
while true; do
    STATUS_JSON=$(curl -s "http://127.0.0.1:8000/jobs/${JOB_ID}")
    STATUS=$(echo "${STATUS_JSON}" | grep -o '"status":"[^"]*' | cut -d'"' -f4 || echo "unknown")
    STEP=$(echo "${STATUS_JSON}" | grep -o '"step":"[^"]*' | cut -d'"' -f4 || echo "unknown")

    echo "  -> Status: [${STATUS}] | Step: [${STEP}]"

    if [ "${STATUS}" = "completed" ]; then
        OUTPUT_FILE="${OUTPUT_DIR}/${JOB_ID}.mp4"
        echo -e "\n======================================================================"
        echo "🎉 Render & Audio Mastering Finished Successfully!"
        echo "Deliverable MP4: ${OUTPUT_FILE}"
        echo "======================================================================"
        break
    elif [ "${STATUS}" = "failed" ]; then
        echo -e "\n✗ Job failed!"
        echo "${STATUS_JSON}"
        exit 1
    fi

    sleep 3
done
