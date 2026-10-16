#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--allow-cloud" || "$#" != 1 ]]; then
  printf '%s\n' 'Usage: bash scripts/generate_recaps.sh --allow-cloud' \
    'Runs paid OpenAI transcription and recap generation for all six prepared recordings.' \
    'Run locally: loads the ignored .env without displaying its contents.'
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd -- "$repo_root"
export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"
python_cmd=python3
if [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_cmd="$repo_root/.venv/bin/python"
fi

session_ids=(
  session-001-spice-bag
  session-002-there-goes-my-hero
  session-003-dark-cauldron
  session-004-its-the-kraken
  session-005-marys-pub
  session-006-dwarf-dungeon
)

# Check the entire batch before starting paid work.
for session_id in "${session_ids[@]}"; do
  if [[ ! -f "sessions/$session_id/manifest.json" || ! -f "sessions/$session_id/session.json" ]]; then
    printf 'Missing prepared session: %s\n' "$session_id" >&2
    exit 1
  fi
done

for session_id in "${session_ids[@]}"; do
  printf '\nProcessing %s\n' "$session_id"
  "$python_cmd" -m dnd_recaps transcribe "$session_id" --allow-cloud
  "$python_cmd" -m dnd_recaps summarize "$session_id" --allow-cloud
done
printf '\nAll six draft recaps generated. Review facts and audience before sharing.\n'
