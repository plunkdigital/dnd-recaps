#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
python_cmd="$repo_root/.venv/bin/python"
if [[ ! -x "$python_cmd" ]]; then
  printf '%s\n' 'Missing local .venv. See docs/gpu-transcription.md for setup.' >&2
  exit 1
fi
cd -- "$repo_root"
export PYTHONPATH="$repo_root/src"
# Configure the library loader before importing CTranslate2, as required by CUDA.
cuda_libraries="$("$python_cmd" -c 'import pathlib, site; print(":".join(str(p) for s in site.getsitepackages() for p in sorted(pathlib.Path(s).glob("nvidia/*/lib"))))')"
export LD_LIBRARY_PATH="$cuda_libraries${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$python_cmd" "$@"
