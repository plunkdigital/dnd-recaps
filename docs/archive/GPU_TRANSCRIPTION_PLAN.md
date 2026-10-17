> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# GPU transcription

User request, 2026-10-16: use the local GPU to reduce transcription time.

- [x] Inspect existing backend and GPU accessibility without interrupting paid work.
- [x] Add an optional CUDA-only backend with separate caches and clear speaker limits.
- [x] Add local execution and setup guidance, preserving the cloud path.
- [x] Verify routing, cache isolation, and fail-fast GPU requirements; record live limits.

Observed: the current backend sends serial requests to OpenAI. No completed raw
transcript chunks are visible yet. `nvidia-smi` exists in WSL, but NVML reports
"GPU access blocked by the operating system" both inside and outside the sandbox.
GPU model, VRAM, CUDA execution, and actual speed require local-terminal evidence.
No ASR dependencies are installed in this repository. Do not borrow sibling virtual
environments; process Python import paths currently expose a sibling's pip module.
Use an isolated project environment for optional packages. The user subsequently
identified their GPU as a 3080; no VRAM figure or successful local CUDA check was supplied.

Do not stop or replace the running cloud batch. Local ASR output must use a separate
path so an active cloud run and its later summary cannot overwrite or consume it.
Whisper timestamps alone do not identify real speakers. The later authorized
diarization and reviewed voice-matching work is tracked in `LOCAL_DIARIZATION_PLAN.md`.

Result: dedicated `.venv` installed using `/usr/bin/python3`, optional dependencies
and imports verified, resolved dependencies recorded in `requirements-cuda.lock`.
All 29 tests pass on system Python and the project environment. The wrapper configures
GPU library paths before Python starts. CUDA selection, CPU rejection, generator
completion, silence handling, and cloud/local transcript and recap isolation are tested.
Shell syntax checks pass. Both real GPU discovery attempts (ordinary and elevated)
returned no visible CUDA device; no model download or local inference followed.
Performance and actual GPU use remain open until the operator runs the GPU checker
and a first transcription locally. No cloud process was stopped, no secret read,
no recording uploaded by the agent, and no commit or push performed.
