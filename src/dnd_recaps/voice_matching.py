"""Local voice-profile proposals. Matches never approve their own identities."""

from collections import Counter
from datetime import datetime, timezone
import math


def unit_vector(values):
    values = [float(value) for value in values]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("Invalid voice embedding.")
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("Empty voice embedding.")
    return [value / norm for value in values]


def speech_durations(turns):
    groups = {}
    for turn in turns:
        groups.setdefault("session:" + turn["speaker"], []).append((turn["start"], turn["end"]))
    totals = {}
    for label, spans in groups.items():
        previous, total = 0, 0
        for start, end in sorted(spans):
            total += max(0, end - max(start, previous))
            previous = max(previous, end)
        totals[label] = total
    return totals


def suggest_matches(embeddings, durations, profiles, people, session_id, model_key,
                    reviewed=None, min_cosine=0.75, min_margin=0.1, min_speech_seconds=15,
                    audio_sha256=None):
    if not (-1 <= min_cosine <= 1 and 0 <= min_margin <= 2 and min_speech_seconds >= 0):
        raise ValueError("Invalid voice-matching thresholds in context/speakers.json.")
    reviewed = reviewed or {}
    proposals = []
    for label, vector in sorted(embeddings.items()):
        vector = unit_vector(vector)
        candidates = []
        for identity, profile in profiles.items():
            if identity not in people:
                continue
            samples = [sample["embedding"] for sample in profile.get("samples", [])
                       if sample["session_id"] != session_id and sample["model_key"] == model_key
                       and (audio_sha256 is None or sample.get("audio_sha256") != audio_sha256)
                       and len(sample["embedding"]) == len(vector)]
            if not samples:
                continue
            samples = [unit_vector(sample) for sample in samples]
            centroid = unit_vector([sum(column) / len(samples) for column in zip(*samples)])
            cosine = sum(a * b for a, b in zip(vector, centroid))
            candidates.append({"speaker_id": identity, "display_name": people[identity]["display_name"],
                               "cosine_similarity": round(max(-1, min(1, cosine)), 6)})
        candidates.sort(key=lambda candidate: (-candidate["cosine_similarity"], candidate["speaker_id"]))
        margin = (candidates[0]["cosine_similarity"] - candidates[1]["cosine_similarity"]
                  if len(candidates) > 1 else None)
        if label in reviewed:
            status = "already_reviewed"
        elif durations.get(label, 0) < min_speech_seconds:
            status = "insufficient_speech"
        elif not candidates:
            status = "no_enrolled_comparison"
        elif candidates[0]["cosine_similarity"] < min_cosine:
            status = "below_threshold"
        elif margin is not None and margin < min_margin:
            status = "ambiguous"
        else:
            status = "proposed"
        proposals.append({"local_label": label, "status": status, "review_required": True,
                          "speech_seconds": round(durations.get(label, 0), 3),
                          "candidates": candidates, "margin": round(margin, 6) if margin is not None else None})
    counts = Counter(item["candidates"][0]["speaker_id"] for item in proposals
                     if item["status"] == "proposed")
    for item in proposals:
        item["duplicate_proposal"] = (item["status"] == "proposed" and
                                      counts[item["candidates"][0]["speaker_id"]] > 1)
    return proposals


def voice_cache(dest, transcript):
    from .cli import read_json

    path = dest / transcript["diarization_cache"]
    expected = (dest / "transcripts/cuda-diarized/turns").resolve()
    if path.suffix != ".json" or path.resolve().parent != expected:
        raise ValueError("Voice features must come from this session's diarization cache.")
    return read_json(path)


def write_proposals(root, dest, transcript):
    from .cli import read_json, save_json, write

    registry_path = root / "context/speakers.json"
    registry = read_json(registry_path) if registry_path.exists() else {"people": {}}
    profiles_path = root / "recordings/catalog/voice-profiles.json"
    profiles = read_json(profiles_path).get("profiles", {}) if profiles_path.exists() else {}
    cached = voice_cache(dest, transcript)
    settings = registry.get("voice_matching", {})
    model_key = cached["input"]["model"] + ":" + cached["input"]["pyannote_version"]
    proposals = suggest_matches(cached.get("embeddings", {}), speech_durations(cached["turns"]),
                                profiles, registry["people"], dest.name, model_key,
                                transcript.get("reviewed_speaker_map"),
                                audio_sha256=cached["input"]["audio_sha256"], **settings)
    directory = dest / "transcripts/cuda-diarized"
    save_json(directory / "speaker-proposals.json", {"schema_version": 1, "model_key": model_key,
              "thresholds": {"min_cosine": settings.get("min_cosine", 0.75),
                             "min_margin": settings.get("min_margin", 0.1),
                             "min_speech_seconds": settings.get("min_speech_seconds", 15)},
              "approved": False, "proposals": proposals})
    lines = ["# Speaker matches for review", "", "Cosine similarity is not a probability or verified identity.",
             "Only explicit map-speaker review can approve a match. Voice vectors remain local and are not sent to recap generation.", "",
             "| Local label | Status | Best candidate | Cosine | Competing margin |", "| --- | --- | --- | --- | --- |"]
    for item in proposals:
        candidate = item["candidates"][0] if item["candidates"] else {}
        status = item["status"] + (" (duplicate candidate)" if item["duplicate_proposal"] else "")
        lines.append(f"| {item['local_label']} | {status} | {candidate.get('speaker_id', '')} | {candidate.get('cosine_similarity', '')} | {item['margin']} |")
    lines += ["", "For a verified identity, run map-speaker with the displayed local label and stable player ID.",
              "New identities require --name; later sessions reuse the same ID. Initial enrollment needs a known speaker, not a numeric-label guess.", ""]
    write(directory / "speaker-proposals.md", "\n".join(lines))


def enroll_reviewed_voice(root, dest, transcript, label, identity):
    from .cli import read_json, save_json

    cached = voice_cache(dest, transcript)
    path = root / "recordings/catalog/voice-profiles.json"
    data = read_json(path) if path.exists() else {"schema_version": 1, "profiles": {}}
    # A correction removes any earlier profile assignment for this exact source/cluster.
    for profile in data["profiles"].values():
        profile["samples"] = [sample for sample in profile["samples"]
                              if not (sample["session_id"] == dest.name and sample["local_label"] == label)]
    embedding = cached.get("embeddings", {}).get(label)
    registry = read_json(root / "context/speakers.json")
    minimum = registry.get("voice_matching", {}).get("min_speech_seconds", 15)
    if embedding is not None and speech_durations(cached["turns"]).get(label, 0) >= minimum:
        model_key = cached["input"]["model"] + ":" + cached["input"]["pyannote_version"]
        profile = data["profiles"].setdefault(identity, {"samples": []})
        profile["samples"].append({"session_id": dest.name, "local_label": label,
                                  "audio_sha256": cached["input"]["audio_sha256"],
                                  "diarization_cache": transcript["diarization_cache"],
                                  "model_key": model_key, "embedding": unit_vector(embedding),
                                  "reviewed_at": datetime.now(timezone.utc).isoformat()})
    save_json(path, data)
