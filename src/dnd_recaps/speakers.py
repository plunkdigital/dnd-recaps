"""Reviewed human aliases, distinct from session-local diarization labels."""

import copy
from datetime import datetime, timezone
import re


def apply_reviewed_speakers(root, dest, transcript):
    from .cli import read_json

    registry_path = root / "context/speakers.json"
    metadata_path = dest / "session.json"
    people = read_json(registry_path).get("people", {}) if registry_path.exists() else {}
    mappings = read_json(metadata_path).get("speaker_map", {}) if metadata_path.exists() else {}
    reviewed = {}
    for label, record in mappings.items():
        if not isinstance(record, dict) or record.get("status") != "reviewed":
            continue
        if (not record.get("diarization_cache") or
                record["diarization_cache"] != transcript.get("diarization_cache")):
            continue  # Reclustering can reuse numeric labels for a different person.
        identity = record.get("speaker_id")
        if identity in people:
            reviewed[label] = {"speaker_id": identity, "display_name": people[identity]["display_name"]}
    result = copy.deepcopy(transcript)
    for segment in result["segments"]:
        for span in [segment] + segment.get("speaker_spans", []):
            span.pop("speaker_name", None)
            span.pop("speaker_id", None)
            identity = reviewed.get(span["speaker"])
            if identity:
                span["speaker_id"] = identity["speaker_id"]
                span["speaker_name"] = identity["display_name"]
    result["reviewed_speaker_map"] = reviewed
    return result


def map_speaker(root, dest, label, identity, display_name=None):
    from .cli import read_json, render, save_json, write

    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", identity):
        raise ValueError("Stable speaker ID must be lowercase letters, digits, underscores or dashes.")
    if display_name is not None and (not display_name.strip() or len(display_name) > 80
                                     or any(ord(char) < 32 for char in display_name)):
        raise ValueError("Speaker display name must be 1–80 printable characters.")
    label = label if label.startswith("session:") else "session:" + label
    path = dest / "transcripts/cuda-diarized/transcript.json"
    transcript = read_json(path)
    if label not in transcript.get("detected_speakers", []):
        raise ValueError("Speaker label is absent from this recording; inspect its diarized transcript first.")
    registry_path = root / "context/speakers.json"
    registry = read_json(registry_path) if registry_path.exists() else {"schema_version": 1, "people": {}}
    people = registry["people"]
    if identity not in people:
        if display_name is None:
            raise ValueError("New stable speaker IDs require --name with a table-approved player alias.")
        people[identity] = {"display_name": display_name.strip()}
    elif display_name is not None and people[identity]["display_name"] != display_name.strip():
        raise ValueError("Stable ID already has another display name. Resolve the registry instead of silently renaming it.")
    metadata = read_json(dest / "session.json")
    mapping = metadata.setdefault("speaker_map", {})
    previous = mapping.get(label)
    mapping[label] = {"speaker_id": identity, "status": "reviewed",
                      "diarization_cache": transcript["diarization_cache"],
                      "source": "explicit operator map-speaker command",
                      "reviewed_at": datetime.now(timezone.utc).isoformat()}
    metadata.setdefault("speaker_map_history", []).append({"label": label, "previous": previous,
                                                          "replacement": mapping[label]})
    # Registry creation alone is harmless if interrupted before session mapping.
    save_json(registry_path, registry)
    save_json(dest / "session.json", metadata)
    labelled = apply_reviewed_speakers(root, dest, transcript)
    from .voice_matching import enroll_reviewed_voice, write_proposals
    enroll_reviewed_voice(root, dest, labelled, label, identity)
    save_json(path, labelled)
    write(path.with_suffix(".md"), render(labelled["segments"]))
    write_proposals(root, dest, labelled)
    print(f"Mapped {label} to stable speaker {identity}. Regenerate this session's recap to apply the reviewed name.")
