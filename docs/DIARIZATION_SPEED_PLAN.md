# Diarization embedding performance

2026-10-16: user reports first-session ASR completes in about 323 seconds;
segmentation takes 12 seconds, embeddings show 42 percent and `0:16:29`.
Progress display alone does not establish whether the time is elapsed or remaining.

- [x] Inspect installed model configuration and embedding/audio IO implementations.
- [x] Preload the prepared mono waveform once and test pipeline input/cache reuse.
- [x] Check equivalent synthetic file/waveform crops using the installed audio reader.
- [x] Run offline suite and document measurement limits and running-job behavior.

Model configuration already sets segmentation and embedding batch sizes to 32.
Do not claim batch size 1 or promise a particular speedup. File-based embedding
crops repeatedly construct TorchCodec decoders; waveform input uses tensor slices.
Keep CUDA neural inference, model settings, TF32 policy, evidence IDs, and completed
turn caches unchanged. No running process is interrupted or hot-patched.

Result: installed pyannote Audio reader with synthetic PCM, 100 crops: 100 decoder
constructions and 0.723 seconds for file input; one construction and 0.050 seconds
including initial loading for waveform input. All cropped samples exactly matched.
This isolates CPU IO overhead and is not a GPU or full-recording speed benchmark.
All 54 offline tests passed; real embedding throughput remains unmeasured by the
agent. No recordings or credentials were read and no model inference was run.
