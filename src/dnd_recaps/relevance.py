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


def classification_format(expected):
    return {"type": "json_schema", "name": "campaign_source_labels", "strict": True,
            "schema": {"type": "object", "additionalProperties": False,
                       "required": ["classifications"], "properties": {"classifications": {
                           "type": "object", "additionalProperties": False,
                           "required": sorted(expected),
                           "properties": {source: {"$ref": "#/$defs/classification"} for source in sorted(expected)}}},
                       "$defs": {"classification": {"type": "object", "additionalProperties": False,
                                 "required": ["category", "question"], "properties": {
                                     "category": {"type": "string", "enum": ["campaign", "unrelated", "uncertain"]},
                                     "question": {"type": "string", "maxLength": 240}}}}}}


def classify_sources(instructions, source, expected, model, cache):
    from .cli import generate

    if len(expected) > 32:
        ordered = sorted(expected)
        return [item for index in range(0, len(ordered), 32)
                for item in classify_sources(instructions, source, set(ordered[index:index + 32]), model, cache)]
    task = ("\nCampaign relevance extraction v1 compatibility; required per-source classification v2. "
            "Return ONLY the schema's classifications object. Each required source ID is a key, with "
            "category campaign, unrelated or uncertain, and question. Do not return event notes or ID lists. "
            "Use surrounding dialogue to classify short replies, rolls, corrections and campaign planning. "
            "Exclude clearly unrelated personal/social chatter. If relevance is truly unclear, choose uncertain "
            "and supply a short neutral review question without private details or possible secrets. "
            "For campaign/unrelated use an empty question. Names and prior context do not establish new events. "
            "Only classify the required IDs; the rest of the batch is context. Required IDs: " + json.dumps(sorted(expected)))
    output = generate(instructions + task, source, model, cache, response_format=classification_format(expected))
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate classification field.")
            result[key] = value
        return result
    try:
        data = json.loads(output, object_pairs_hook=unique_fields)
        labels = data["classifications"]
        if not isinstance(labels, dict) or set(labels) != expected:
            raise ValueError
        items = []
        for identity in sorted(expected):
            record = labels[identity]
            category, question = record["category"], record["question"]
            if category not in {"campaign", "unrelated", "uncertain"} or not isinstance(question, str) or len(question) > 240:
                raise ValueError
            item = {"source_ids": [identity], "category": category}
            if category == "campaign":
                item["note"] = "Campaign speech; consult original transcript for events."
            elif category == "uncertain":
                item.update(topic="Campaign relevance requires review",
                            question=question.strip() or "Is this source span related to the campaign?")
            items.append(item)
        return parse_extraction(json.dumps({"items": items}), expected)
    except (ValueError, KeyError, TypeError):
        # Complete validated legacy classifications can still pass during
        # migration; malformed results remain withheld, never guessed.
        return recover_omitted_sources(output, expected)


def citations(text):
    return set(re.findall(r"\[(c\d+:s\d+)\]", text))


def valid_citations(text, allowed):
    matches = list(re.finditer(r"\[(c\d+:s\d+)\]", text))
    if not matches or not {match[1] for match in matches} <= allowed:
        return False
    if any(citations(line) for line in text.splitlines() if re.match(r"^#{1,6}\s", line)):
        return False
    if any(len(re.findall(r"\[c\d+:s\d+\]", paragraph)) > 3 for paragraph in text.split("\n\n")):
        return False
    # Do not let one valid reference conceal compressed, bare, or invented IDs.
    remaining = re.sub(r"\[c\d+:s\d+\]", "", text)
    return re.search(r"\bc\d+\s*:\s*s\d+\b|\[\s*s\d+\b|\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]", remaining) is None


def citation_transport(instructions, source, compact=False):
    ids = sorted(citations(source))
    mapping = {index: identity for index, identity in enumerate(ids, 1)}
    numbers = {identity: index for index, identity in mapping.items()}
    text = re.sub(r"\[(c\d+:s\d+)\]", lambda match: f"[E{numbers[match[1]]}]", source)
    fingerprint = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
    contract = ("\nNarrative evidence blocks v2. Return ONLY a JSON object, without code fences: "
                '{"blocks":[{"markdown":"Heading or prose", "evidence":[1,2]}]}. '
                "Evidence numbers are examples only. Use only numeric evidence handles [E<number>] "
                "actually present in this input. This overrides literal citation formatting in earlier instructions: "
                "put integer reference numbers in evidence arrays, never in prose. Code writes canonical citations. "
                "Never use ranges, shorthand, strings, or invented reference numbers. "
                "Write the requested story sections or compact notes in markdown blocks. "
                "Each prose block is ONE paragraph or ONE appendix bullet with 1-3 supporting evidence numbers. "
                "Put each heading in its own block with an EMPTY evidence array; headings have no citations. "
                "Never append a source inventory to a title or section. Keep paragraphs under 1600 characters. "
                "Do not put source IDs or [E<number>] markers in markdown. "
                "A markdown string is a SINGLE LINE. No brackets, line breaks or embedded citations. "
                "Evidence numbers are local to this request and must not be reused from another request. "
                "Evidence mapping SHA-256: " + fingerprint)
    if compact:
        contract += ("\nCompact scene contract v1: return 1-4 factual blocks, each at most 45 "
                     "whitespace-separated words and 400 characters, at most 180 words TOTAL. "
                     "No headings or appendix. Each block must have 1-3 supporting evidence numbers. "
                     "Select the consequential outcomes and uncertainties; do not inventory every utterance.")
    return instructions + contract, text, mapping


def narrative_response_format(mapping, compact=False):
    if not mapping:
        raise ValueError("Narrative generation requires source evidence references.")
    # Count words locally. The old repeated-token regex is implicated in short
    # incomplete responses despite ample output-token budget.
    pattern = r"^[^\[\]\r\n]+$"
    result = {"type": "json_schema", "name": "narrative_evidence_blocks", "strict": True,
            "schema": {"type": "object", "additionalProperties": False, "required": ["blocks"],
                       "properties": {"blocks": {
                           "type": "array", "minItems": 1,
                           "items": {"type": "object", "additionalProperties": False,
                                     "required": ["markdown", "evidence"],
                                     "properties": {
                                         "markdown": {"type": "string", "minLength": 1,
                                                      "maxLength": 400 if compact else 1600, "pattern": pattern},
                                         "evidence": {"type": "array", "minItems": 1 if compact else 0, "maxItems": 3,
                                                      "items": {"type": "integer", "minimum": 1,
                                                                "maximum": len(mapping)}}}}}}}}
    if compact:
        result["schema"]["properties"]["blocks"]["maxItems"] = 4
    return result


def render_evidence_blocks(output, mapping, compact=False):
    try:
        data = json.loads(output)
    except ValueError:
        # Backward-compatible acceptance still requires strict canonical IDs.
        if not valid_citations(output, set(mapping.values())):
            return None
        if compact:
            # Old Markdown caches remain evidence only when they satisfy the
            # same scene budget. Never truncate or discard a response fragment.
            prose = re.sub(r"\[c\d+:s\d+\]", "", output)
            paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip()]
            if (not 1 <= len(paragraphs) <= 4 or len(output) > 2400
                    or any(len(p) > 400 or len(p.split()) > 45 or "\n" in p or p.startswith("#") for p in paragraphs)):
                return None
        return output
    try:
        blocks = data["blocks"]
        if not isinstance(blocks, list) or not blocks or (compact and len(blocks) > 4):
            return None
        rendered = []
        for block in blocks:
            text, refs = block["markdown"], block["evidence"]
            if (not isinstance(text, str) or not text.strip() or not isinstance(refs, list)
                    or any(type(ref) is not int or ref not in mapping for ref in refs)
                    or len(refs) != len(set(refs)) or len(refs) > 3 or len(text) > (400 if compact else 1600)
                    or re.search(r"[\[\]\r\n]", text)
                    or re.search(r"\bc\d+\s*:\s*s\d+\b|\[E\d+\]|\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]", text)):
                return None
            if compact and (not refs or text.lstrip().startswith("#") or len(text.split()) > 45):
                return None
            prose = "\n".join(line for line in text.splitlines()
                              if not re.match(r"^#{1,6}\s", line)).strip()
            if refs and (not prose or "\n\n" in prose):
                return None
            if not refs and not all(re.fullmatch(r"#{1,6}\s+.+|Not established\.?", line.strip())
                                    for line in text.splitlines() if line.strip()):
                return None
            rendered.append(text.strip() + (" " + " ".join(f"[{mapping[ref]}]" for ref in refs) if refs else ""))
        result = "\n\n".join(rendered)
        return result if valid_citations(result, set(mapping.values())) else None
    except (KeyError, TypeError):
        return None


def generate_cited(instructions, source, model, cache, stage, recovery=None, compact=False):
    from .cli import generate, generation_request, read_json, SummaryOutputLimit

    if recovery is None:
        recovery = {"splits": 0}
    transported, text, mapping = citation_transport(instructions, source, compact=compact)
    response_format = narrative_response_format(mapping, compact=compact)
    if compact:
        # Completed old scenes are still valid evidence under identical inputs
        # and mappings. Keep their raw bodies and identities; skip old failures.
        legacy_format = json.loads(json.dumps(response_format))
        legacy_format["schema"]["properties"]["blocks"]["items"]["properties"]["markdown"]["pattern"] = r"^([^\s\[\]]+[ \t]+){0,44}[^\s\[\]]+$"
        _, legacy_cache, _ = generation_request(transported, text, model, cache, legacy_format)
        if legacy_cache.exists():
            raw = read_json(legacy_cache)
            if raw.get("status") == "completed" and not any(
                    part.get("type") == "refusal" for item in raw.get("output", []) for part in item.get("content", [])):
                previous = "\n".join(part["text"] for item in raw.get("output", []) if item.get("type") == "message"
                                     for part in item.get("content", []) if part.get("type") == "output_text")
                rendered = render_evidence_blocks(previous, mapping, compact=True)
                if rendered is not None:
                    return rendered
        transported += ("\nFor new compact output, aim for 25-35 words per block, finishing the finding "
                        "well before the 45-word/400-character local limits. Do not pad blocks to the limits.")
    try:
        output = generate(transported, text, model, cache, response_format=response_format)
    except SummaryOutputLimit:
        return reduce_after_cutoff(instructions, source, model, cache, stage, recovery, compact=compact)
    rendered = render_evidence_blocks(output, mapping, compact=compact)
    if rendered is not None:
        return rendered
    print(f"Citation validation failed during {stage}; regenerating once from supplied evidence.", flush=True)
    # The invalid draft is deliberately not used as evidence or fed back into the
    # rewrite. Reconstruct from the same validated input; never guess replacements.
    repair = ("\nCitation recovery attempt 1. The previous response failed evidence-block validation. "
              "Rewrite from the supplied evidence only using the JSON blocks contract. "
              "Put supporting integer evidence numbers in each block's evidence array. "
              "Each markdown string MUST be a single line, with no brackets or embedded citations. "
              "Separate paragraphs into distinct blocks; never share evidence across several paragraphs. "
              "Do not put citations or evidence handles in prose, and never invent or expand ranges. "
              "If evidence cannot support a claim, omit it. The permitted numbers are: " + json.dumps(list(mapping)))
    if compact:
        repair += " Compact-note recovery: at most four blocks, at most 45 words and 400 characters EACH. No headings."
    try:
        output = generate(transported + repair, text, model, cache, response_format=response_format)
    except SummaryOutputLimit:
        return reduce_after_cutoff(instructions, source, model, cache, stage, recovery, compact=compact)
    rendered = render_evidence_blocks(output, mapping, compact=compact)
    if rendered is None:
        raise ValueError(f"Citation validation failed during {stage}, including one recovery attempt. "
                         "No new recap/review pair published. Original responses and completed audio stages remain cached.")
    return rendered


def reduce_after_cutoff(instructions, source, model, cache, stage, recovery, compact=False):
    """Bounded recovery using whole evidence lines, never the provider's partial text."""
    lines = source.splitlines(keepends=True)
    if recovery["splits"] >= 3 or len(lines) < 2:
        raise ValueError(f"Output limit during {stage}; bounded recovery cannot split further. "
                         "Diagnostic and completed responses remain cached. No new recap/review pair published.")
    recovery["splits"] += 1
    # Balance at a line boundary so each side retains its original citations.
    cumulative = 0
    boundaries = []
    for index, line in enumerate(lines[:-1], 1):
        cumulative += len(line)
        boundaries.append((abs(len(source) / 2 - cumulative), index))
    boundary = min(boundaries)[1]
    parts = ["".join(lines[:boundary]), "".join(lines[boundary:])]
    if any(not citations(part) for part in parts):
        raise ValueError(f"Output limit during {stage}; cannot split evidence without losing source references. "
                         "No new recap/review pair published.")
    print(f"Output-token cutoff during {stage}; reducing two smaller evidence groups "
          f"(split {recovery['splits']}/3).", flush=True)
    recovery_task = ("\nOutput-limit recovery v1. This input is partial session evidence. "
               "Override story formatting for this step: produce compact chronological evidence notes only, "
               "at most 600 words. Retain consequential outcomes, choices, clues, resources, uncertainties, "
               "unresolved threads and stopping information present here. Cite only 1-3 exact supporting "
               "IDs per finding, not a complete ID inventory. No invented events or final recap.")
    reduced = [generate_cited(instructions + recovery_task, part, model, cache, stage + " partial recovery", recovery,
                             compact=compact)
               for part in parts]
    return generate_cited(instructions, "\n".join(reduced), model, cache, stage, recovery, compact=compact)


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


def recover_omitted_sources(text, expected):
    """Withhold anything unclassified or invalid; never guess campaign relevance."""
    try:
        return parse_extraction(text, expected)
    except ValueError:
        pass
    # Only independently valid items are candidates. Unknown IDs, malformed
    # fields and internal duplicates invalidate the whole item, not just its IDs.
    candidates = []
    issues = set()
    invalid_sources = set()
    try:
        data = json.loads(text)
        if not isinstance(data["items"], list):
            raise ValueError
        for item in data["items"]:
            raw_ids = item.get("source_ids", []) if isinstance(item, dict) else []
            item_sources = ({source for source in raw_ids if isinstance(source, str) and source in expected}
                            if isinstance(raw_ids, list) else set())
            try:
                declared = set(item["source_ids"])
                if not declared <= expected:
                    raise ValueError
                candidates.extend(parse_extraction(json.dumps({"items": [item]}), declared))
            except (ValueError, KeyError, TypeError):
                issues.add("invalid_item")
                invalid_sources.update(item_sources)
    except (ValueError, KeyError, TypeError):
        issues.add("invalid_response")
    counts = {}
    for item in candidates:
        for source in item["source_ids"]:
            counts[source] = counts.get(source, 0) + 1
    disputed = {source for source, count in counts.items() if count > 1}
    if disputed:
        issues.add("conflicting_groups")
    # Do not pick a winning classification or rewrite group evidence. Remove
    # every group touching a disputed source, withholding the entire group.
    blocked = disputed | invalid_sources
    items = [item for item in candidates if not blocked.intersection(item["source_ids"])]
    declared = {source for item in items for source in item["source_ids"]}
    missing = sorted(expected - declared)
    if not missing:
        # An invalid item with no usable source pointers cannot be located safely.
        # Withhold the batch rather than attach invented IDs or pick valid-looking
        # material from a response whose conflict cannot be attributed.
        items = []
        missing = sorted(expected)
        issues.add("unattributable_invalid_item")
    items.append({
        "source_ids": missing, "category": "uncertain", "reason": "unclassified_sources",
        "topic": "Unclassified recording segments",
        "question": "These segments lack a valid, nonconflicting classification. Are they campaign-related? "
                    "Review each source span; they may concern different topics. Withheld pending review.",
        "classification_issues": sorted(issues or {"omitted_sources"}),
    })
    # The augmented result must satisfy exactly the same complete-coverage check.
    result = parse_extraction(json.dumps({"items": items}), expected)
    print(f"Relevance extraction left {len(missing)} source IDs unclassified or invalid; "
          "withheld and added to manual checks.", flush=True)
    return result


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
            if item.get("reason") == "unclassified_sources":
                # Unclassified spans may concern unrelated topics. Keep each
                # extraction batch's omission group separate and manageable.
                key += (tuple(sorted(ids)),)
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
    unclassified = {source for check in checks if check.get("reason") == "unclassified_sources"
                    for source in check["source_ids"]}
    status = ("Extraction coverage: complete, including withheld unclassified spans. "
              "Model classification: partial or invalid. Human review: pending." if unclassified else
              "Extraction: complete for all transcript batches. Human review: pending.")
    lines = ["# Manual campaign relevance checks", "", status,
             "This is model-generated selection, not a guarantee that every ambiguity was detected.",
             f"Transcript backend: `{backend}`. Transcript SHA-256: `{transcript_hash}`.", "",
             "Material with unclear campaign relevance was withheld. Check the source audio before deciding.",
             "Spelling suggestions alone do not exclude an event or establish a character identity.",
             "Record decisions and reviewer/date in the session's manual-check.md or review.md;",
             "this generated draft is replaced on rerun. Do not edit it to retain decisions.", ""]
    if unclassified:
        lines += [f"Model classification left {len(unclassified)} distinct source segments "
                  "unclassified or invalid. These were withheld and require manual review.", ""]
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
