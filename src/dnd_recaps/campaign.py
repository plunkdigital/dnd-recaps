"""Time-bounded spelling hints and explicit reviewed prior-session continuity."""

import json
import difflib
import re


def name_reference(root, metadata):
    path = root / "context/campaign/names.json"
    if not path.exists():
        return ""
    number = metadata.get("session_number")
    if type(number) is not int or number < 1:
        return ""  # Unknown chronology cannot authorize later names.
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for item in data["names"]:
        if type(item["from_session"]) is not int or item["from_session"] < 1:
            raise ValueError("Invalid name reference session number.")
        if item["from_session"] <= number:
            names = [item["name"], *item["aliases"]]
            if any(not isinstance(name, str) or not name.strip() for name in names):
                raise ValueError("Invalid campaign spelling reference.")
            entries.append(" / ".join(names))
    result = "; ".join(entries)
    if len(result) > 900:
        raise ValueError("Campaign spelling hints exceed 900 characters; condense names.json.")
    return result


def previous_recap(root, dest, metadata, backend):
    """Only the immediately preceding recording, never a future or draft recap."""
    number = metadata.get("session_number")
    if type(number) is not int or number <= 1:
        return "", None
    matches = []
    for path in sorted((root / "sessions").glob("*/session.json")):
        if path.parent == dest:
            continue
        prior = json.loads(path.read_text(encoding="utf-8"))
        if type(prior.get("archived", False)) is not bool:
            raise ValueError("Session archived must be true or false.")
        if prior.get("archived", False):
            continue
        if (prior.get("session_number") == number - 1
                and prior.get("campaign") == metadata.get("campaign")):
            matches.append(path.parent)
    if len(matches) > 1:
        raise ValueError("Multiple preceding sessions match; resolve session_number metadata.")
    if not matches:
        return "", None
    directory = matches[0] / "summaries"
    candidates = ([directory / backend / "recap.reviewed.md"] if backend != "openai" else [])
    candidates.append(directory / "recap.reviewed.md")
    for path in candidates:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if text.strip():
                return text, str(path.relative_to(root))
    return "", None


def name_checks(spelling, segments):
    """Suggest likely spelling errors without changing source words or identity."""
    words = set(re.findall(r"\b[A-Za-z]{4,}\b", spelling))
    known = {word.casefold() for word in words}
    found = {}
    for segment in segments:
        for word in re.findall(r"\b[A-Z][a-z]{3,}\b", segment["text"]):
            if word.casefold() in known:
                continue
            candidates = sorted(name for name in words if
                                difflib.SequenceMatcher(None, word.casefold(), name.casefold()).ratio() >= 0.72)
            if candidates:
                key = (word, tuple(candidates))
                found.setdefault(key, []).append(segment["id"])
    return [{"heard": word, "candidates": list(candidates), "source_ids": sorted(set(ids)),
             "status": "unreviewed_spelling_suggestion"}
            for (word, candidates), ids in sorted(found.items())]
