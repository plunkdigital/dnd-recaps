"""Optional GPU ASR. Local audio never passes through the cloud adapter."""

from importlib.metadata import version
import math
import time
import tempfile
import wave


def check_decoder():
    """Exercise the actual ASR decoder with synthetic silence before loading weights."""
    try:
        from faster_whisper.audio import decode_audio
        with tempfile.TemporaryDirectory() as directory:
            from pathlib import Path
            path = Path(directory) / "decoder-check.wav"
            with wave.open(str(path), "wb") as audio:
                audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                audio.writeframes(bytes(3200))
            decoded = decode_audio(str(path))
            if len(decoded) != 1600:
                raise ValueError("Unexpected synthetic decode length.")
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        raise ValueError("ASR audio decoder check failed. Install requirements-gpu-diarization.lock "
                         "in this repository's .venv; faster-whisper 1.2.1 requires PyAV below 19. "
                         "No recording was transcribed.") from None


def cuda_runtime():
    try:
        import ctranslate2
    except (ImportError, OSError):
        raise ValueError("Install this repository's CUDA extra in .venv; see docs/gpu-transcription.md.") from None
    try:
        count = ctranslate2.get_cuda_device_count()
        if count < 1:
            raise ValueError("No CUDA GPU is visible. GPU transcription requires CUDA; no CPU fallback.")
        supported = ctranslate2.get_supported_compute_types("cuda", device_index=0)
        if "int8_float16" not in supported:
            raise ValueError("GPU does not support int8_float16. No CPU fallback; inspect CUDA compatibility.")
    except (RuntimeError, OSError):
        raise ValueError("CUDA initialization failed. Check GPU access, driver, CUDA 12 and cuDNN 9. No CPU fallback.") from None
    return {"cuda_devices": count, "device": "cuda:0", "compute_type": "int8_float16",
            "ctranslate2_version": version("ctranslate2")}


def create_model(model_name, download_root):
    status = cuda_runtime()  # Check hardware before downloading model weights.
    check_decoder()
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_name, device="cuda", device_index=0,
                             compute_type="int8_float16", download_root=str(download_root))
        if model.model.device != "cuda":
            raise ValueError("Model did not initialize on CUDA. Refusing CPU fallback.")
    except (ImportError, RuntimeError, OSError):
        raise ValueError("GPU model initialization failed. Check local packages, GPU memory, model download, and CUDA libraries.") from None
    print(f"ASR device: {status['device']}; model: {model_name}; compute: int8_float16", flush=True)
    return model


def transcribe(dest, model_name="turbo"):
    from .cli import digest, normalize, read_json, render, save_json, write

    manifest = read_json(dest / "manifest.json")
    output = dest / "transcripts/cuda"
    engine = None
    all_segments = []
    parameters = {"beam_size": 5, "vad_filter": True, "condition_on_previous_text": False,
                  "task": "transcribe", "word_timestamps": True}
    from .campaign import name_reference
    root = dest.parent.parent
    hints = name_reference(root, read_json(dest / "session.json")) if (dest / "session.json").exists() else ""
    if hints:
        # Unlike initial_prompt, hotwords are supplied to every decoding window
        # even though prior decoded text is deliberately not carried forward.
        parameters["hotwords"] = hints
    for chunk in manifest["chunks"]:
        path = dest / chunk["path"]
        if digest(path) != chunk["sha256"]:
            raise ValueError("Audio chunk changed; cannot reuse GPU transcription cache.")
        identity = {"sha256": chunk["sha256"], "backend": "faster-whisper-cuda",
                    "model": model_name, "compute_type": "int8_float16", "parameters": parameters}
        cache = output / "raw" / (chunk["id"] + ".json")
        if cache.exists():
            cached = read_json(cache)
            # Existing segmentation defines evidence IDs. Hints apply only to
            # new chunks; never replace old raw responses to retrofit spellings.
            existing = cached["input"]
            compatible = {**existing, "parameters": {key: value for key, value in existing["parameters"].items()
                                                      if key not in {"initial_prompt", "hotwords"}}}
            current = {**identity, "parameters": {key: value for key, value in parameters.items()
                                                  if key not in {"initial_prompt", "hotwords"}}}
            old = {**current, "parameters": {key: value for key, value in current["parameters"].items()
                                              if key != "word_timestamps"}}
            if compatible not in (current, old):
                raise ValueError("GPU cache settings differ. Preserve existing results and use a new session ID for another model.")
            if any(existing["parameters"].get(key) != parameters.get(key) for key in ("initial_prompt", "hotwords")):
                print(f"Preserving {chunk['id']} cached segmentation; current spelling hints were not applied to this chunk.", flush=True)
            raw = cached["response"]
        else:
            if engine is None:
                engine = create_model(model_name, dest.parent.parent / ".cache/whisper")
            print(f"GPU transcribing {chunk['id']}… (timestamps only; speakers unknown)", flush=True)
            start = time.monotonic()
            try:
                segments, info = engine.transcribe(str(path), **parameters)
                # Iterating the generator actually runs inference. Cache only after it completes.
                records = []
                for item in segments:
                    if not item.text.strip():
                        continue
                    words = []
                    for word in getattr(item, "words", None) or []:
                        if not (math.isfinite(word.start) and math.isfinite(word.end)
                                and 0 <= word.start <= word.end and isinstance(word.word, str)):
                            raise ValueError("ASR returned invalid word timestamps; no partial chunk saved.")
                        words.append({"start": word.start, "end": word.end, "word": word.word})
                    records.append({"start": item.start, "end": item.end, "text": item.text,
                                    "speaker": "unknown", "words": words})
            except (RuntimeError, OSError):
                raise ValueError("GPU transcription failed. Completed chunks remain cached. No CPU fallback; check memory and CUDA libraries.") from None
            except TypeError:
                raise ValueError("GPU transcription backend raised TypeError. Check the ASR decoder/package compatibility "
                                 "against requirements-gpu-diarization.lock. No partial chunk saved; completed caches remain.") from None
            raw = {"segments": records, "no_speech": not records,
                   "language": info.language, "device": "cuda:0", "speaker_labels": False,
                   "elapsed_seconds": round(time.monotonic() - start, 2)}
            if records:
                normalize(raw, chunk)
            save_json(cache, {"input": identity, "response": raw})
            print(f"Saved {chunk['id']} after {raw['elapsed_seconds']:.1f}s", flush=True)
        if not (raw.get("no_speech") is True and raw.get("segments") == []):
            normalized = normalize(raw, chunk)
            for segment, record in zip(normalized, raw["segments"]):
                segment["words"] = [{**word, "start": word["start"] + chunk["offset_seconds"],
                                     "end": word["end"] + chunk["offset_seconds"]}
                                    for word in record.get("words", [])]
            all_segments.extend(normalized)
    if not all_segments:
        raise ValueError("GPU ASR detected no speech; inspect audio before generating a recap.")
    all_segments.sort(key=lambda item: (item["start"], item["id"]))
    save_json(output / "transcript.json", {"schema_version": 1, "backend": "faster-whisper-cuda",
              "model": model_name, "speaker_labels": False, "segments": all_segments})
    write(output / "transcript.md", render(all_segments))
    print("GPU transcript ready under transcripts/cuda/. Speaker identities remain unknown.")
