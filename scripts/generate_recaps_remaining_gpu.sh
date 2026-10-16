#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" != 1 || "${1:-}" != "--allow-cloud" ]]; then
  printf '%s\n' 'Usage: scripts/generate_recaps_remaining_gpu.sh --allow-cloud' \
    'Processes sessions 2-6. Local audio inference; paid OpenAI text stages. Continues after session failures.' >&2
  exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/generate_recaps_gpu.sh" --allow-cloud --from-session 2 --continue-on-error
