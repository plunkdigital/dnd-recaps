#!/usr/bin/env bash
set -euo pipefail
allow_cloud=false
continue_on_error=false
first_session=1
last_session=6
summaries_only=false
usage() {
  printf '%s\n' 'Usage: scripts/generate_recaps_gpu.sh --allow-cloud [--from-session 1-6] [--through-session 1-6] [--continue-on-error] [--summaries-only]' \
    'Local CUDA transcription and speaker separation; text recaps use the paid OpenAI API.'
}
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --allow-cloud) allow_cloud=true; shift ;;
    --continue-on-error) continue_on_error=true; shift ;;
    --summaries-only) summaries_only=true; shift ;;
    --through-session)
      if [[ "$#" -lt 2 || ! "$2" =~ ^[1-6]$ ]]; then
        usage >&2
        exit 2
      fi
      last_session="$2"
      shift 2
      ;;
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
if [[ "$last_session" -lt "$first_session" ]]; then
  usage >&2
  exit 2
fi
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
implementation_fingerprint() {
  local path
  for path in "$repo_root"/src/dnd_recaps/*.py "$repo_root"/prompts/*.md \
      "$script_dir"/*.sh "$repo_root"/context/campaign/*.md "$repo_root"/context/campaign/names.json; do
    if [[ -f "$path" ]]; then
      sha256sum "$path" || return "$?"
    fi
  done | sha256sum
}
implementation_version="$(implementation_fingerprint)"
printf '%s\n' "$implementation_version" > "$log_dir/implementation.sha256"
check_implementation() {
  if [[ "$(implementation_fingerprint)" != "$implementation_version" ]]; then
    printf '%s\n' 'Error: pipeline files changed during this run. Stopping before another stage; start a new run after edits finish.'
    printf '%s\timplementation-check\t86\n' "$1" >> "$log_dir/status.tsv"
    return 86
  fi
}
if [[ "$summaries_only" != true ]]; then
  "${runner[@]}" gpu-check
  check_implementation preflight
  "${runner[@]}" diarization-check
  check_implementation preflight
fi
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
  local -a stages=(transcribe diarize summarize)
  if [[ "$summaries_only" == true ]]; then
    stages=(summarize)
  fi
  for stage in "${stages[@]}"; do
    check_implementation "$session_id" || return "$?"
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
    check_implementation "$session_id" || return "$?"
    if [[ "$code" -ne 0 ]]; then
      printf 'FAILED: %s at %s (exit %s). Later stages for this session were skipped.\n' "$session_id" "$stage" "$code"
      return "$code"
    fi
  done
}
failed=()
for session_id in "${sessions[@]:first_session-1:last_session-first_session+1}"; do
  if run_session "$session_id"; then
    printf 'Completed: %s\n' "$session_id"
  else
    code=$?
    failed+=("$session_id")
    if [[ "$continue_on_error" != true || "$code" -eq 86 ]]; then
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
