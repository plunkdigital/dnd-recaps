"""One chronological scene pass over original evidence, then one story pass."""

import re


def story_problem(recap, windows, substantial):
    from .relevance import citations

    if re.search(r"(?im)^#{1,6}\s+Previously\b", recap):
        return "Current-session story incorrectly includes Previously."
    if not substantial:
        return None
    match = re.search(r"(?ims)^## The tale[^\n]*\n(.*?)(?=^## |\Z)", recap)
    if not match:
        return "A substantial recording needs a separate The tale section."
    tale = match[1]
    count = len(re.findall(r"\b[\w']+\b", re.sub(r"\[c\d+:s\d+\]", "", tale)))
    if not 600 <= count <= 1100:
        return "The tale needs 600-1000 words (with a small upper tolerance), rather than a short plot inventory."
    if len(windows) >= 6:
        cited = citations(tale)
        for third, label in enumerate(("opening", "middle", "ending")):
            section = windows[len(windows) * third // 3:len(windows) * (third + 1) // 3]
            if not any(cited.intersection(window["source_ids"]) for window in section):
                return f"The tale lacks evidence from the {label} third of retained recording windows."
    return None


def build_story(instructions, segments, allowed, model, cache):
    from .cli import render
    from .relevance import citations, generate_cited, source_batches

    selected = sorted((segment for segment in segments if segment["id"] in allowed),
                      key=lambda segment: (segment["start"], segment["id"]))
    windows = source_batches(selected, render, limit=24000)
    coverage, notes = [], []
    for index, (text, expected) in enumerate(windows, 1):
        if len(windows) > 1:
            print(f"Chronological scene notes: window {index}/{len(windows)}", flush=True)
            task = ("\nChronological scene evidence v2. This is a partial session, in recording order. "
                    "Read the original transcript, not previous extracted prose. Return compact scene notes, "
                    "at most 180 words total. Capture consequential choices and resolved outcomes, social "
                    "scenes, exploration, conflicts, clues and explicit changes. Preserve names, distinguish "
                    "plans, past recollections and NPC claims. Select exact supporting utterances for each "
                    "finding, at most three references per paragraph. Do not cite an entire window. "
                    "Keep events in order; mark uncertain names. Do not write the final recap. "
                    "Do not add section headings or generic atmosphere. Include the stopping situation "
                    "only if present. Material excluded by relevance review is absent; never reconstruct it.")
            note = generate_cited(instructions + task, text, model, cache, f"scene window {index}", compact=True)
            if len(note) > 2400:
                raise ValueError("Scene notes exceed their compact evidence budget; cached response retained. No new draft published.")
        else:
            note = text
        notes.append(note)
        coverage.append({"window": index, "source_ids": sorted(expected),
                         "retained_evidence_ids": sorted(citations(note)),
                         "start": min(s["start"] for s in selected if s["id"] in expected),
                         "end": max(s["end"] for s in selected if s["id"] in expected)})
    if not notes:
        return ("# Session recap\n\nNo campaign events were established for inclusion in this draft. "
                "See the separate manual-check draft for any topics withheld pending review."), coverage
    evidence = "\n\n".join(f"Recording window {i}:\n{note}" for i, note in enumerate(notes, 1))
    if len(evidence) > 64000:
        raise ValueError("Scene outline exceeds 64,000 characters. Split the session explicitly; no evidence was truncated.")
    task = ("\nWrite the final recap using the required sections. The recording windows are chronological. "
            "Represent consequential scenes throughout the beginning, middle and ending, not just the "
            "first and last windows. Write 600-1000 words in The tale when evidence supports it. "
            "Use supported character decisions and consequences to connect scenes. Keep the appendix "
            "compact. Do not write Previously; code handles verified prior-session continuity separately.")
    print("Generating final recap from chronological evidence...", flush=True)
    substantial = sum(len(s["text"].split()) for s in selected) >= 3000
    for attempt in range(2):
        recap = generate_cited(instructions + task, evidence, model, cache, "final recap")
        problem = story_problem(recap, coverage, substantial)
        if problem is None:
            break
        if attempt:
            raise ValueError(problem + " Quality recovery failed; responses retained. No new draft published.")
        print("Story quality check failed; rewriting once from the same chronological evidence.", flush=True)
        task += "\nStory quality recovery v2. " + problem + " Rebuild from all supplied evidence; do not invent missing scenes."
    for window in coverage:
        window["recap_evidence_ids"] = sorted(citations(recap).intersection(window["source_ids"]))
    return recap, coverage
