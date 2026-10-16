#!/usr/bin/env bash
set -euo pipefail
allow_cloud=false
continue_on_error=false
first_session=1
usage() {
  printf '%s\n' 'Usage: scripts/generate_recaps_gpu.sh --allow-cloud [--from-session 1-6] [--continue-on-error]' \
    'Local CUDA transcription and speaker separation; text recaps use the paid OpenAI API.'
}
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --allow-cloud) allow_cloud=true; shift ;;
    --continue-on-error) continue_on_error=true; shift ;;
    --from-session)
      if [[ "$#" -lt 2 || ! "$2" =~ ^[1-6]$ ]]; then
        usage >&2
        exit 2
      fi
      first_session="$2"
      shift 2
      ;;
    *) usage >&2; exit 2 ;;
  esac
done
if [[ "$allow_cloud" != true ]]; then
  usage >&2
  exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd -- "$repo_root"
runner=(bash "$script_dir/gpu_python.sh" -m dnd_recaps)
mkdir -p "$repo_root/recordings/catalog/batch-runs"
log_dir="$(mktemp -d "$repo_root/recordings/catalog/batch-runs/gpu-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
exec > >(tee -a "$log_dir/run.log") 2>&1
printf 'Batch log: %s\n' "$log_dir/run.log"
printf 'session\tstage\texit_code\n' > "$log_dir/status.tsv"
"${runner[@]}" gpu-check
"${runner[@]}" diarization-check
sessions=(
  session-001-spice-bag
  session-002-there-goes-my-hero
  session-003-dark-cauldron
  session-004-its-the-kraken
  session-005-marys-pub
  session-006-dwarf-dungeon
)
run_session() {
  local session_id="$1" stage code
  local -a arguments
  for stage in transcribe diarize summarize; do
    case "$stage" in
      transcribe) arguments=(transcribe "$session_id" --backend cuda) ;;
      diarize) arguments=(diarize "$session_id") ;;
      summarize) arguments=(summarize "$session_id" --transcript-backend cuda-diarized --allow-cloud) ;;
    esac
    printf '\n%s: %s (%s UTC)\n' "$session_id" "$stage" "$(date -u +%FT%TZ)"
    if "${runner[@]}" "${arguments[@]}"; then
      code=0
    else
      code=$?
    fi
    printf '%s\t%s\t%s\n' "$session_id" "$stage" "$code" >> "$log_dir/status.tsv"
    if [[ "$code" -ne 0 ]]; then
      printf 'FAILED: %s at %s (exit %s). Later stages for this session were skipped.\n' "$session_id" "$stage" "$code"
      return "$code"
    fi
  done
}
failed=()
for session_id in "${sessions[@]:first_session-1}"; do
  if run_session "$session_id"; then
    printf 'Completed: %s\n' "$session_id"
  else
    failed+=("$session_id")
    if [[ "$continue_on_error" != true ]]; then
      break
    fi
  fi
done
printf '\nStage status: %s\n' "$log_dir/status.tsv"
if [[ "${#failed[@]}" -gt 0 ]]; then
  printf 'Failed sessions: %s\n' "${failed[*]}"
  exit 1
fi
printf '%s\n' 'Selected sessions completed. Review each session manual-check.md and cuda-diarized recap draft.'
