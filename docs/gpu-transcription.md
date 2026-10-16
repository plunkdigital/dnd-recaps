# Local GPU transcription

The original backend sends audio to OpenAI and cannot use your GPU. The optional
CUDA backend uses faster-whisper/CTranslate2 locally. The user reports a 3080 GPU;
actual inference must be verified in the user's terminal because this runtime
cannot access it, even with escalation. No running cloud job was stopped.

## Verify and run

The optional dependencies are already installed in this checkout's own `.venv`.
From your WSL terminal in this repository:

```bash
nvidia-smi
./scripts/gpu_python.sh -m dnd_recaps gpu-check
```

The checker must report a positive `cuda_devices` count, `device: cuda:0`, and
`compute_type: int8_float16`. It does not load secrets, recordings, or model weights.
That check alone does not prove model inference works. For the first recording:

```bash
./scripts/gpu_python.sh -m dnd_recaps transcribe session-001-spice-bag --backend cuda
```

This requests CUDA explicitly, verifies the model's device, and fails instead of
falling back to CPU. Model weights download into ignored `.cache/whisper/` on first
use. Look for `ASR device: cuda:0` and completed-chunk timings. In another terminal,
`watch -n 1 nvidia-smi` shows GPU memory and utilization during inference. Activity
varies across preprocessing and inference; 100 percent utilization is not required.

To run all six recordings with GPU transcription, local diarization, and cloud text
recaps, first complete the model-access setup in [local diarization](local-diarization.md):

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud
```

This is a separate batch. Choose deliberately before running duplicate transcription
work. It does not cancel or modify an existing cloud job; previously completed cloud
results remain reusable. An in-flight cloud request may complete after its caller stops.

## Output and quality boundaries

- CUDA transcripts and raw caches live under `sessions/<id>/transcripts/cuda/`.
  Their text recaps and provenance live under `sessions/<id>/summaries/cuda/`.
  Neither backend overwrites or implicitly consumes the other backend's outputs.
- The local model defaults to `turbo` with `int8_float16` compute. The alternative
  `--local-model large-v3` uses the larger model. Use a fresh session ID for a
  different local model; cache settings must not be mixed silently.
- Plain CUDA ASR leaves speakers unknown. The new separate diarization stage writes
  `transcripts/cuda-diarized/` and its recaps to `summaries/cuda-diarized/`. Acoustic
  labels are session-local; cross-session voice suggestions require explicit review.
- Audio stays local for ASR. Text recaps still use the paid OpenAI API and load
  `.env` only for that cloud stage. DM exclusions and historical-context policies
  remain in force. Recaps remain unreviewed drafts.
- Completed chunks survive failures. Silence-only chunks are recorded without
  fabricated speech, and a failing segment generator never saves a partial success.

## Environment and verification

Installed and import-checked on Python 3.14.4: faster-whisper 1.2.1, CTranslate2
4.8.3, cuBLAS 12.8.4.1, and cuDNN 9.19.0.56. The resolved Linux/Python 3.14 pins
are in `requirements-cuda.lock`. To reproduce on that platform:

```bash
/usr/bin/python3 -m venv .venv
uv --cache-dir .cache/uv pip install --python .venv/bin/python -r requirements-cuda.lock
```

Without uv, use `.venv/bin/python -m pip install -r requirements-cuda.lock`.
Other Python/platform combinations need a compatible resolution from the `cuda`
extra. The wrapper sets CUDA library paths before launching Python. Do not borrow
a sibling environment or change global drivers/settings without a demonstrated need.
If `nvidia-smi` fails in the user's terminal, Windows/WSL GPU exposure must be fixed;
Python package installation cannot make an inaccessible GPU visible.

All 50 offline tests pass after adding diarization and voice-match review. Imports work; the real checker correctly reports no
visible CUDA device here. NVML also reports operating-system blocking outside the
sandbox. No model weights or local ASR run were attempted after that failure.
GPU inference, VRAM consumption, transcript quality, and throughput are unverified.

Sources reviewed 2026-10-16: [faster-whisper usage and GPU requirements](https://github.com/SYSTRAN/faster-whisper)
and [CTranslate2 device discovery](https://opennmt.net/CTranslate2/python/ctranslate2.get_cuda_device_count.html).
Published benchmarks are not measurements of this computer.
