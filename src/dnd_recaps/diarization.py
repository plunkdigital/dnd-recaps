"""Session-wide local diarization and conservative, evidence-preserving alignment."""

from bisect import bisect_left, bisect_right
import copy
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
import subprocess
import tempfile
import time


MODEL = "pyannote/speaker-diarization-community-1"


def torch_cuda():
    try:
        import torch
    except (ImportError, OSError):
        raise ValueError("Install the diarization environment; see docs/local-diarization.md.") from None
    if not torch.cuda.is_available():
        raise ValueError("PyTorch cannot access CUDA. Diarization will not fall back to CPU.")
    return torch


def create_pipeline(root):
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("Set HF_TOKEN locally and accept the Community-1 model conditions; see docs/local-diarization.md.")
    torch = torch_cuda()
    # Session-only configuration; no global telemetry or authentication files written.
    os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    try:
        from pyannote.audio import Pipeline
        pipeline = Pipeline.from_pretrained(MODEL, token=token,
                                            cache_dir=str(root / ".cache/huggingface/hub"))
        pipeline.to(torch.device("cuda:0"))
    except Exception:
        # Model/provider errors may contain credentials or request details.
        raise ValueError("Diarization initialization failed. Check model acceptance, HF_TOKEN, CUDA and package compatibility.") from None
    if pipeline.device.type != "cuda":
        raise ValueError("Diarization pipeline did not initialize on CUDA; refusing CPU fallback.")
    print("Diarization neural inference device: cuda:0; clustering/postprocessing also use CPU.", flush=True)
    return pipeline


def validate_turns(turns):
    for turn in turns:
        if not (math.isfinite(turn["start"]) and math.isfinite(turn["end"])
                and 0 <= turn["start"] < turn["end"] and isinstance(turn["speaker"], str)
                and turn["speaker"]):
            raise ValueError("Invalid diarization turn; no labelled transcript published.")
    return sorted(turns, key=lambda item: (item["start"], item["end"], item["speaker"]))


class TurnIndex:
    def __init__(self, turns):
        self.turns = validate_turns(turns)
        self.starts = [turn["start"] for turn in self.turns]
        self.max_ends = []
        for turn in self.turns:
            self.max_ends.append(max(turn["end"], self.max_ends[-1] if self.max_ends else 0))

    def attribute(self, start, end):
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start <= end):
            raise ValueError("Invalid transcript timestamps for speaker alignment.")
        if end == start:
            return "session:unknown", []
        high = bisect_left(self.starts, end)
        low = bisect_right(self.max_ends, start, 0, high)
        intersections = {}
        for turn in self.turns[low:high]:
            left, right = max(start, turn["start"]), min(end, turn["end"])
            if right > left:
                intersections.setdefault(turn["speaker"], []).append((left, right))
        candidates = []
        for label, spans in intersections.items():
            total, previous_end = 0, start
            for left, right in sorted(spans):
                total += max(0, right - max(left, previous_end))
                previous_end = max(previous_end, right)
            candidates.append({"speaker": "session:" + label, "overlap_seconds": round(total, 6)})
        candidates.sort(key=lambda item: (-item["overlap_seconds"], item["speaker"]))
        duration = end - start
        # Keep genuine overlapping speech and competing boundary evidence ambiguous.
        if (not candidates or candidates[0]["overlap_seconds"] < 0.8 * duration
                or (len(candidates) > 1 and candidates[1]["overlap_seconds"] > 0.1 * duration)):
            return "session:unknown", candidates
        return candidates[0]["speaker"], candidates


def align_transcript(transcript, turns):
    index = TurnIndex(turns)
    result = copy.deepcopy(transcript)
    for segment in result["segments"]:
        label, candidates = index.attribute(segment["start"], segment["end"])
        segment.update(speaker=label, speaker_candidates=candidates)
        words = segment.get("words", [])
        # Legacy ASR without matching words stays at conservative segment resolution.
        if not words or "".join(word["word"] for word in words).strip() != segment["text"].strip():
            continue
        spans = []
        previous = segment["start"] - 0.5
        for word in words:
            if word["start"] < previous or word["end"] > segment["end"] + 0.5:
                raise ValueError("Non-monotonic or out-of-range word timestamps; alignment stopped.")
            label, candidates = index.attribute(word["start"], word["end"])
            previous = word["end"]
            if spans and spans[-1]["speaker"] == label:
                spans[-1]["text"] += word["word"]
                spans[-1]["end"] = word["end"]
            else:
                spans.append({"start": word["start"], "end": word["end"], "speaker": label,
                              "text": word["word"]})
        segment["speaker_spans"] = spans
        segment["speaker"] = spans[0]["speaker"] if len(spans) == 1 else "session:unknown"
    result.update(backend="faster-whisper-cuda+pyannote", speaker_labels=True,
                  detected_speakers=sorted({"session:" + turn["speaker"] for turn in turns}),
                  speaker_scope="session", alignment="overlap-v1", diarization_model=MODEL)
    return result


def run_turns(pipeline, source, directory, num_speakers=None):
    # Use standard waveform input through a temporary PCM file. CPU decoding does
    # not imply CPU neural inference, and model memory is not shared with ASR.
    with tempfile.TemporaryDirectory(dir=directory, prefix="decode-") as temporary:
        from pathlib import Path
        audio = Path(temporary) / "mono.wav"
        decoded = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(source),
                                  "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
                                  "-c:a", "pcm_s16le", str(audio)], capture_output=True)
        if decoded.returncode:
            raise ValueError("Could not decode audio for diarization; original remains unchanged.")
        options = {"num_speakers": num_speakers} if num_speakers else {}
        try:
            from pyannote.audio.pipelines.utils.hook import ProgressHook
            with ProgressHook() as hook:
                output = pipeline(str(audio), hook=hook, **options)
            turns = [{"start": turn.start, "end": turn.end, "speaker": label}
                     for turn, _, label in output.speaker_diarization.itertracks(yield_label=True)]
            from .voice_matching import unit_vector
            embeddings = {}
            if output.speaker_embeddings is not None:
                for label, vector in zip(output.speaker_diarization.labels(), output.speaker_embeddings):
                    try:
                        embeddings["session:" + label] = unit_vector(vector)
                    except ValueError:
                        continue  # Zero/unavailable centroids cannot establish a voice profile.
        except Exception:
            raise ValueError("Local diarization failed. Check CUDA memory and audio decoder compatibility; completed caches remain.") from None
    return {"turns": validate_turns(turns), "embeddings": embeddings}


def diarize(root, dest, num_speakers=None):
    from .cli import digest, read_json, render, save_json, write

    if num_speakers is not None and num_speakers < 1:
        raise ValueError("Speaker count must be positive and count people, not PCs/NPC voices.")
    manifest = read_json(dest / "manifest.json")
    source = dest / manifest["source"]["path"]
    if digest(source) != manifest["source"]["sha256"]:
        raise ValueError("Original audio hash differs; cannot diarize changed evidence.")
    transcript_path = dest / "transcripts/cuda/transcript.json"
    transcript = read_json(transcript_path)
    try:
        engine_version = version("pyannote.audio")
    except PackageNotFoundError:
        raise ValueError("Install the diarization environment; see docs/local-diarization.md.") from None
    identity = {"cache_schema": 2, "audio_sha256": digest(source), "model": MODEL, "num_speakers": num_speakers,
                "pyannote_version": engine_version, "scope": "session"}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = dest / "transcripts/cuda-diarized"
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / "turns" / (key + ".json")
    if cache.exists():
        stored = read_json(cache)
        if stored["input"] != identity:
            raise ValueError("Diarization cache identity mismatch.")
        turns = validate_turns(stored["turns"])
    else:
        pipeline = create_pipeline(root)
        started = time.monotonic()
        inference = run_turns(pipeline, source, directory, num_speakers)
        turns = inference["turns"]
        if not turns:
            raise ValueError("No speaker turns detected; inspect the audio before continuing.")
        save_json(cache, {"input": identity, "turns": turns, "embeddings": inference["embeddings"], "device": "cuda:0",
                          "elapsed_seconds": round(time.monotonic() - started, 2)})
    if not turns:
        raise ValueError("Diarization cache has no speaker turns; inspect audio and cache before continuing.")
    labelled = align_transcript(transcript, turns)
    labelled.update(diarization_cache=str(cache.relative_to(dest)),
                    source_transcript_sha256=digest(transcript_path))
    from .speakers import apply_reviewed_speakers
    labelled = apply_reviewed_speakers(root, dest, labelled)
    save_json(directory / "transcript.json", labelled)
    write(directory / "transcript.md", render(labelled["segments"]))
    from .voice_matching import write_proposals
    write_proposals(root, dest, labelled)
    print("Session-local speaker labels ready under transcripts/cuda-diarized/. Human identity mapping still required.")
