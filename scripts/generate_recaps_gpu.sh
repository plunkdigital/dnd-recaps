#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" != "--allow-cloud" || "$#" != 1 ]]; then
  printf '%s\n' 'Usage: bash scripts/generate_recaps_gpu.sh --allow-cloud' \
    'Local CUDA transcription and speaker separation; text recaps use the paid OpenAI API.'
  exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd -- "$repo_root"
runner=(bash "$script_dir/gpu_python.sh" -m dnd_recaps)
"${runner[@]}" gpu-check
"${runner[@]}" diarization-check
for session_id in \
  session-001-spice-bag \
  session-002-there-goes-my-hero \
  session-003-dark-cauldron \
  session-004-its-the-kraken \
  session-005-marys-pub \
  session-006-dwarf-dungeon; do
  "${runner[@]}" transcribe "$session_id" --backend cuda
  "${runner[@]}" diarize "$session_id"
  "${runner[@]}" summarize "$session_id" --transcript-backend cuda-diarized --allow-cloud
done
printf '%s\n' 'Labelled transcripts and recaps are ready in each session’s cuda-diarized/ directories.'
