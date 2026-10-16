"""Validated campaign selection and a separate, durable human review deliverable."""

import hashlib
import json
import re


EXTRACTION_TASK = """
Campaign relevance extraction v1. Return one JSON object, without Markdown fences:
{"items": [{"source_ids": ["c0000:s0000"], "category": "campaign", "note": "Grounded evidence notes"},
           {"source_ids": ["c0000:s0001"], "category": "unrelated"},
           {"source_ids": ["c0000:s0002"], "category": "uncertain", "topic": "Neutral topic label", "question": "What needs human review?"}]}
These are format examples, never evidence or actual IDs to copy.
Account for EVERY distinct source ID in the supplied batch exactly once. Group
related IDs where useful. Use only IDs actually present in this batch. Classify
clearly non-campaign chatter as unrelated and omit its content entirely. Preserve
relevant out-of-character campaign decisions, rulings, retcons and corrections.
If campaign relevance cannot be established, choose uncertain, not campaign.
For mixed campaign/unrelated material in one segment, retain only campaign facts;
if the boundary is unclear choose uncertain for the whole segment. Treat jokes,
plans, previous-session recollections and NPC claims as such, not resolved events.
For campaign items, extract compact chronological evidence notes, preserving
outcomes, consequential choices, clues, resource changes, uncertainty, unresolved
threads and the stopping situation. Do not write a final recap yet. For uncertain
items, use a short neutral topic and actionable question, with no personal details,
secret content, invented quotes or inferred answers. Do not narrate them as events.
Do not add timestamps: code obtains them from the original transcript.
"""


def citations(text):
    return set(re.findall(r"\[(c\d+:s\d+)\]", text))


def source_batches(segments, render, limit=8000):
    from .cli import batches

    result, text, ids = [], "", set()
    for segment in segments:
        # IDs come from metadata, never citation-like strings spoken in dialogue.
        for part in batches(render([segment]), limit=limit):
            if len(text) + len(part) > limit:
                result.append((text, ids))
                text, ids = "", set()
            text += part
            ids.add(segment["id"])
    if text:
        result.append((text, ids))
    return result


def parse_extraction(text, expected):
    try:
        data = json.loads(text)
        items = data["items"]
        if not isinstance(items, list):
            raise ValueError
        seen = set()
        for item in items:
            ids = item["source_ids"]
            category = item["category"]
            if (not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids)
                    or len(set(ids)) != len(ids) or not set(ids) <= expected or seen.intersection(ids)
                    or category not in {"campaign", "unrelated", "uncertain"}):
                raise ValueError
            seen.update(ids)
            fields = ("note",) if category == "campaign" else (("topic", "question") if category == "uncertain" else ())
            for field in fields:
                if not isinstance(item[field], str) or not item[field].strip():
                    raise ValueError
                if not citations(item[field]) <= set(ids):
                    raise ValueError
        if seen != expected:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise ValueError("Campaign relevance extraction is malformed or does not cover the batch's source IDs. "
                         "No new recap/review pair published; inspect cached output.") from None
    return items


def select_evidence(items):
    # A segment repeated across a text-batch boundary is withheld if ANY batch
    # finds its relevance uncertain. Keep questions out of narrative reduction.
    blocked = {source for item in items if item["category"] != "campaign" for source in item["source_ids"]}
    notes, allowed, checks, seen = [], set(), [], {}
    for item in items:
        ids = item["source_ids"]
        if item["category"] == "campaign" and not blocked.intersection(ids):
            refs = " ".join(f"[{i}]" for i in ids)
            # Each bounded reduction fragment must retain its own source pointers.
            notes.extend(line.strip() + " " + refs for line in item["note"].splitlines() if line.strip())
            allowed.update(ids)
        elif item["category"] == "uncertain":
            key = tuple(" ".join(item[field].casefold().split()) for field in ("topic", "question"))
            if key not in seen:
                seen[key] = len(checks)
                checks.append({**item, "source_ids": list(ids)})
            else:
                existing = checks[seen[key]]["source_ids"]
                existing.extend(i for i in ids if i not in existing)
    return "\n".join(notes), allowed, checks


def cell(text):
    return " ".join(text.split()).replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def render_checks(checks, segments, backend, transcript_hash):
    by_id = {segment["id"]: segment for segment in segments}
    lines = ["# Manual campaign relevance checks", "",
             "Extraction: complete for all transcript batches. Human review: pending.",
             "This is model-generated selection, not a guarantee that every ambiguity was detected.",
             f"Transcript backend: `{backend}`. Transcript SHA-256: `{transcript_hash}`.", "",
             "Ambiguous material was withheld from the draft. Check the source audio before deciding.",
             "Record decisions and reviewer/date in the session's manual-check.md or review.md;",
             "this generated draft is replaced on rerun. Do not edit it to retain decisions.", ""]
    if not checks:
        lines.append("No ambiguous campaign-relevance topics were identified in this complete extraction.")
    else:
        lines += ["| Segment IDs | Recording timestamps | Neutral topic | Review question | Decision and reviewer/date |",
                  "| --- | --- | --- | --- | --- |"]
        for check in sorted(checks, key=lambda c: min(by_id[i]["start"] for i in c["source_ids"])):
            ids = sorted(check["source_ids"], key=lambda i: (by_id[i]["start"], i))
            stamps = "; ".join(f"{i}: {by_id[i]['start']:.2f}-{by_id[i]['end']:.2f}s" for i in ids)
            refs = " ".join(f"[{i}]" for i in ids)
            lines.append(f"| {refs} | {stamps} | {cell(check['topic'])} | {cell(check['question'])} | Pending |")
    return "\n".join(lines) + "\n"


def publish_checks(dest, summary_dir, report, details):
    from .cli import save_json, write

    write(summary_dir / "manual-check.draft.md", report)
    save_json(summary_dir / "manual-check.draft.json", details)
    # Human-owned index/decision log. Never overwrite it on reruns or backend changes.
    index = dest / "manual-check.md"
    if not index.exists():
        write(index, "# Manual campaign relevance review\n\n"
              "Review the generated draft for the backend you used. A missing report is not a completed review.\n\n"
              "- [OpenAI transcript review](summaries/manual-check.draft.md)\n"
              "- [CUDA transcript review](summaries/cuda/manual-check.draft.md)\n"
              "- [CUDA diarized transcript review](summaries/cuda-diarized/manual-check.draft.md)\n\n"
              "## Human decisions\n\n"
              "Record source IDs, transcript hash/backend, include/exclude/unresolved, reviewer/date, and reasons here.\n"
              "Log accepted corrections and evidence in review.md. Decisions are not applied automatically;\n"
              "update evidence/context with review references as appropriate and regenerate the recap.\n")
    return hashlib.sha256(report.encode()).hexdigest()
