"""One whole-recording request: story prose plus separate human review questions."""

import hashlib
import json
import re


TASK = """
Read the complete chronological recording and write the player story directly.
Return recap_blocks, previously_blocks and manual_checks.
Each input source is marked [number|original ID]. Each story block has markdown
prose and a sources array containing only supporting source numbers.
Write each heading or narrative paragraph as a block; headings have empty sources.
Choose sources for the specific claims in that paragraph, not a sampling of the
recording. Do not put the entire story and an inventory of sources in one block.
Do not type citation markers into markdown; code appends the original source IDs.
Use [] for recap_blocks if the recording establishes no campaign events.
Previously uses only the separately
numbered reviewed prior recap; use [] when none is supplied. Do not put Previously
inside recap_blocks. Current and prior source numbers have separate scopes.
Manual checks contain sources, topic and question. They concern the uncertain
detail, which may share context with a settled event. Never treat a question as an
answer. Follow the recap instructions for grounded storytelling and exclusions.
"""


def citations(text):
    return set(re.findall(r"\[(c\d+:s\d+)\]", text))


def evidence_footnotes(story):
    """Move current-source lists out of the reading flow without changing evidence."""
    notes = []

    def move(match):
        label = f"current-{len(notes) + 1}"
        notes.append(f"[^{label}]: {match[0].strip()}")
        return f" [^{label}]"

    story = re.sub(r"(?: \[c\d+:s\d+\])+(?=\n|$)", move, story)
    return story + ("\n\n## Evidence\n\n" + "\n\n".join(notes) if notes else "")


def number_sources(text, ids):
    numbers = {source: index for index, source in enumerate(ids, 1)}
    # Keep canonical IDs in the request so cache identity also binds the lookup.
    return re.sub(r"\[(c\d+:s\d+)\]",
                  lambda m: f"[{numbers[m[1]]}|{m[1]}]", text)


def transcript_input(segments):
    """Full dialogue with one evidence header per segment, without repeated timing."""
    lines = []
    for segment in segments:
        spans = segment.get("speaker_spans") or [segment]
        # Normalized JSON is the editable evidence. Diarization spans may still
        # contain the original words after a human corrects the parent text.
        if segment["text"].split() != [word for span in spans for word in span["text"].split()]:
            lines.append(f"[{segment['id']}] (speaker attribution unavailable): {segment['text'].strip()}")
            continue
        turns = []
        for span in spans:
            label = span["speaker"]
            if span.get("speaker_name"):
                label += f" ({span['speaker_name']})"
            if turns and turns[-1][0] == label:
                turns[-1][1] += " " + span["text"].strip()
            else:
                turns.append([label, span["text"].strip()])
        dialogue = "\n".join(f"{label}: {text}" for label, text in turns)
        lines.append(f"[{segment['id']}] {dialogue}")
    return "\n".join(lines) + ("\n" if lines else "")


def response_format(current_count, previous_count):
    def sources(count):
        return {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": max(1, count)}}
    def blocks(count):
        result = {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["markdown", "sources"],
            "properties": {"markdown": {"type": "string"}, "sources": sources(count)}}}
        if not count:
            result["maxItems"] = 0
        return result
    question_sources = {**sources(current_count), "minItems": 1}
    return {"type": "json_schema", "name": "session_recap", "strict": True,
            "schema": {"type": "object", "additionalProperties": False,
                       "required": ["recap_blocks", "previously_blocks", "manual_checks"],
                       "properties": {
                           "recap_blocks": blocks(current_count),
                           "previously_blocks": blocks(previous_count),
                           "manual_checks": {"type": "array", "items": {
                               "type": "object", "additionalProperties": False,
                               "required": ["sources", "topic", "question"],
                               "properties": {"sources": question_sources, "topic": {"type": "string"},
                                              "question": {"type": "string"}}}}}}}


def resolve_sources(values, ids, location):
    if not isinstance(values, list) or any(type(v) is not int or not 1 <= v <= len(ids) for v in values):
        raise ValueError(f"Invalid source reference in {location}; expected integers from 1 to {len(ids)}. "
                         "Saved response preserved; no new drafts published.")
    return list(dict.fromkeys(ids[v - 1] for v in values))


def render_blocks(blocks, ids, location):
    if not isinstance(blocks, list):
        raise ValueError(f"Malformed {location} blocks; no new drafts published.")
    rendered, cited = [], set()
    for index, block in enumerate(blocks, 1):
        where = f"{location} block {index}"
        if (not isinstance(block, dict) or set(block) != {"markdown", "sources"}
                or not isinstance(block["markdown"], str) or not block["markdown"].strip()):
            raise ValueError(f"Malformed {where}; no new drafts published.")
        refs = resolve_sources(block["sources"], ids, where)
        text = block["markdown"].strip()
        if re.search(r"\bc\d+\s*:\s*s\d+\b|\[\s*(?:source\s+|E)?\d+[^\]]*\]", text):
            raise ValueError(f"{where} contains inline source markers; use its sources array. No new drafts published.")
        cited.update(refs)
        rendered.append(text + (" " + " ".join(f"[{ref}]" for ref in refs) if refs else ""))
    if blocks and not cited:
        raise ValueError(f"{location} has no source references; no new drafts published.")
    return "\n\n".join(rendered)


def parse(output, segments, previous):
    """Check source references without grading the prose by arbitrary quotas."""
    try:
        data = json.loads(output)
    except ValueError:
        raise ValueError("Recap response is not valid JSON; saved response preserved, no new drafts published.") from None
    if (not isinstance(data, dict) or set(data) != {"recap_blocks", "previously_blocks", "manual_checks"}
            or not isinstance(data["manual_checks"], list)):
        raise ValueError("Recap response does not match its requested format; no new drafts published.")
    ids = [s["id"] for s in segments]
    checks = []
    for index, check in enumerate(data["manual_checks"], 1):
        if (not isinstance(check, dict) or set(check) != {"sources", "topic", "question"}
                or any(not isinstance(check[k], str) or not check[k].strip() for k in ("topic", "question"))):
            raise ValueError(f"Malformed manual question {index}; no new drafts published.")
        refs = resolve_sources(check["sources"], ids, f"manual question {index}")
        if not refs:
            raise ValueError(f"Manual question {index} has no source references; no new drafts published.")
        checks.append({"source_ids": refs, "topic": check["topic"], "question": check["question"]})
    story = render_blocks(data["recap_blocks"], ids, "recap")
    # A question can concern a name or one unresolved detail in an otherwise
    # relevant utterance. Shared source IDs do not prove the uncertain claim was
    # narrated; expose the overlap for review rather than discard the whole story.
    story_sources = citations(story)
    for check in checks:
        check["recap_source_ids"] = [source for source in check["source_ids"] if source in story_sources]
    if re.search(r"(?im)^#{1,6}\s+Previously\b", story):
        raise ValueError("Previously belongs only to reviewed prior context, not the current story. No new drafts published.")
    if data["previously_blocks"] and not previous:
        raise ValueError("Previously requires a reviewed previous recap. No new drafts published.")
    opening = render_blocks(data["previously_blocks"], sorted(citations(previous)), "previous opening")
    if not story:
        story = "# Session recap\n\nNo campaign events were established for this draft. See the manual review questions."
    return story, opening, checks


def cell(text):
    return " ".join(text.split()).replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def render_checks(checks, segments, backend, transcript_hash):
    by_id = {segment["id"]: segment for segment in segments}
    lines = ["# Manual campaign relevance checks", "",
             "Model review questions from the full transcript. Human review: pending.",
             "This is not an exhaustive classification or a guarantee that every ambiguity was detected.",
             f"Transcript backend: `{backend}`. Transcript SHA-256: `{transcript_hash}`.", "",
             "Questions identify uncertain details. Their source passages may also support settled events.",
             "For shared sources, check that the tale omits the uncertain detail and unrelated conversation.",
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
            question = cell(check['question'])
            if check.get("recap_source_ids"):
                shared = " ".join(f"[{source}]" for source in check["recap_source_ids"])
                question += f" **Also cited in recap:** {shared}. Verify the uncertain detail was omitted."
            lines.append(f"| {refs} | {stamps} | {cell(check['topic'])} | {question} | Pending |")
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
