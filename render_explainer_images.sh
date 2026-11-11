#!/usr/bin/env bash
set -euo pipefail
# Render the 5 explainer slide images (4:5, 1080x1350) from the ExplainerSlide composition.
cd /opt/data/workspace/amds/remotion
mkdir -p ../output/explainer

# Each entry: file|icon|kicker|title|body
slides=(
  "01-brief|message-square-text|Step 01 — The input|You type a brief.|One sentence of intent goes into the API. No timeline, no keyframes, no manual GUI — the whole creative input is plain language."
  "02-storyboard|brain-circuit|Step 02 — The brain|A local LLM writes the storyboard.|Qwen 3.8 27B on your GPU turns the brief into a deterministic scene graph: copy, icons, and exact frame timing as structured JSON."
  "03-render|film|Step 03 — The engine|Remotion renders every frame.|Every pixel is a pure function of the frame clock. Parallel, headless, and perfectly deterministic — no wall time, no drift."
  "04-audio|audio-lines|Step 04 — The sound|Voice and music, mastered.|Neural TTS synthesizes the narration, then FFmpeg ducks the music under it and normalizes to broadcast loudness."
  "05-delivery|package-check|Step 05 — The result|Out comes a mastered MP4.|From brief to final video with zero human intervention in the middle. Fully autonomous, end to end."
)

for entry in "${slides[@]}"; do
  IFS='|' read -r file icon kicker title body <<< "$entry"
  idx=$((10#${file%%-*}))
  total=5
  echo ">>> rendering $file"
  npx remotion still src/index.ts ExplainerSlide "../output/explainer/$file.png" \
    --frame=0 --width=1080 --height=1350 \
    --props='{"index":'"$((idx-1))"',"total":'"$total"',"icon":"'"$icon"'","kicker":"'"$kicker"'","title":"'"$title"'","body":"'"$body"'"}' \
    --log=warn
done
echo "ALL EXPLAINER IMAGES DONE"
ls -la ../output/explainer/
