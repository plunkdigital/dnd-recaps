> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# GPU decoder compatibility fix

User failure reported 2026-10-16. CUDA discovery and diarization initialization
succeeded in the user's terminal; first ASR chunk failed before producing a cache.

- [x] Reproduce with synthetic audio without credentials or real recordings.
- [x] Pin a compatible decoder in optional dependencies and both lockfiles.
- [x] Add a synthetic decoder preflight and regression coverage.
- [x] Verify the installed decoder, offline suite, and update operator guidance.

Cause: faster-whisper 1.2.1 passes `metadata_errors` to `av.open`, which PyAV
19.0.1 rejects with TypeError. The top-level privacy-safe handler hid that detail.
Keep raw exception text private, preserve caches, and never fall back from CUDA.
The public Whisper model's unauthenticated download warning is independent:
HF_TOKEN is loaded only by the operator's diarization command, not local ASR.

Result: PyAV 18.0.0 decodes synthetic WAV and VAD returns no speech for silence.
All 52 offline tests pass, including preflight privacy and partial-generator failure
coverage. Dependency compatibility checks pass. User-run real GPU inference remains
the next check; no real audio, protected configuration, or paid API was used here.
