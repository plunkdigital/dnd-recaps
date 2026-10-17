"""One whole-recording request: story prose plus separate human review questions."""

import hashlib
import json
import re


TASK = """
Whole-transcript recap v1. Read the complete chronological recording below and
write the player recap directly. Ignore unrelated chatter. Withhold ambiguous
campaign material and return neutral review questions with exact source IDs.
Also flag uncertain names and possible audience issues without quoting secrets.
Return recap_markdown, previously_markdown, and manual_checks in the specified JSON.
recap_markdown contains current-session sections only, never Previously. Use an
empty recap_markdown if no campaign events were established; do not invent a story.
previously_markdown is a short paragraph using only the supplied reviewed prior
recap's citations; leave it empty if there is no reviewed prior recap. No heading.
Do not cite any manual_checks source_ids in recap_markdown. Code supplies question
timestamps. A question is not an event. Preserve significant scenes throughout the
recording, including the precise stopping situation. Length and pacing are editorial
guidance, not per-paragraph quotas. Use canonical source IDs directly in prose.
"""

RESPONSE_FORMAT = {
    "type": "json_schema", "name": "session_recap", "strict": True,
    "schema": {"type": "object", "additionalProperties": False,
               "required": ["recap_markdown", "previously_markdown", "manual_checks"],
               "properties": {
                   "recap_markdown": {"type": "string"},
                   "previously_markdown": {"type": "string"},
                   "manual_checks": {"type": "array", "items": {
                       "type": "object", "additionalProperties": False,
                       "required": ["source_ids", "topic", "question"],
                       "properties": {"source_ids": {"type": "array", "items": {"type": "string"}},
                                      "topic": {"type": "string"}, "question": {"type": "string"}}}},
               }},
}


def citations(text):
    return set(re.findall(r"\[(c\d+:s\d+)\]", text))


def validate_citations(text, allowed):
    refs = citations(text)
    remaining = re.sub(r"\[c\d+:s\d+\]", "", text)
    malformed = re.search(r"\bc\d+\s*:\s*s\d+\b|\[\s*(?:s|E)?\d+(?:\s*[,–-]\s*\d+)*\s*\]", remaining)
    if not refs or not refs <= allowed or malformed:
        raise ValueError("Recap has missing, unknown or malformed source citations. "
                         "Inspect the saved response; no new drafts published.")


def parse(output, segments, previous):
    """Validate references and completion shape, without grading prose mechanically."""
    try:
        data = json.loads(output)
        if set(data) != {"recap_markdown", "previously_markdown", "manual_checks"}:
            raise ValueError
        story, opening, checks = data["recap_markdown"], data["previously_markdown"], data["manual_checks"]
        if not isinstance(story, str) or not isinstance(opening, str) or not isinstance(checks, list):
            raise ValueError
        allowed = {s["id"] for s in segments}
        blocked = set()
        for check in checks:
            if not isinstance(check, dict) or set(check) != {"source_ids", "topic", "question"}:
                raise ValueError
            ids = check["source_ids"]
            if (not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids)
                    or not set(ids) <= allowed or len(set(ids)) != len(ids)
                    or any(not isinstance(check[k], str) or not check[k].strip() for k in ("topic", "question"))):
                raise ValueError
            blocked.update(ids)
    except (ValueError, KeyError, TypeError):
        raise ValueError("Malformed recap/review response. Inspect the saved response; no new drafts published.") from None
    if re.search(r"(?im)^#{1,6}\s+Previously\b", story):
        raise ValueError("Previously belongs only to reviewed prior context, not the current story. No new drafts published.")
    if story.strip():
        validate_citations(story, allowed - blocked)
    else:
        story = "# Session recap\n\nNo campaign events were established for this draft. See the manual review questions."
    if opening.strip():
        if not previous:
            raise ValueError("Previously requires a reviewed previous recap. No new drafts published.")
        validate_citations(opening, citations(previous))
    return story, opening.strip(), checks


def cell(text):
    return " ".join(text.split()).replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def render_checks(checks, segments, backend, transcript_hash):
    by_id = {segment["id"]: segment for segment in segments}
    lines = ["# Manual campaign relevance checks", "",
             "Model review questions from the full transcript. Human review: pending.",
             "This is not an exhaustive classification or a guarantee that every ambiguity was detected.",
             f"Transcript backend: `{backend}`. Transcript SHA-256: `{transcript_hash}`.", "",
             "Flagged source segments were withheld from the recap's citations. Check the source audio.",
             "Keep decisions and reviewer/date in manual-check.md or review.md; this draft is replaced on rerun.", ""]
    if not checks:
        lines.append("The model reported no review questions. Verify relevance, names and audience before sharing.")
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
