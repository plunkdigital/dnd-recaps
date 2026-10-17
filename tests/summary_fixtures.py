"""Synthetic responses use real request source numbers, without provider calls."""

import json
import re


def response(text):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]}


def summary_reply(final_text, checks=None, previously=""):
    def reply(endpoint, body):
        payload = json.loads(body)
        def numbers(text):
            return {source: int(number) for number, source in re.findall(r"\[(\d+)\|(c\d+:s\d+)\]", text)}
        current, prior = numbers(payload["input"]), numbers(payload["instructions"])
        def blocks(text, lookup):
            result = []
            for paragraph in text.split("\n\n"):
                if not paragraph.strip():
                    continue
                ids = re.findall(r"\[(c\d+:s\d+)\]", paragraph)
                result.append({"markdown": re.sub(r"\[c\d+:s\d+\]", "", paragraph).strip(),
                               "sources": [lookup.get(i, len(lookup) + 1) for i in ids]})
            return result
        questions = [{"sources": [current.get(i, len(current) + 1) for i in check["source_ids"]],
                      "topic": check["topic"], "question": check["question"]} for check in checks or []]
        return response(json.dumps({"recap_blocks": blocks(final_text, current),
                                    "previously_blocks": blocks(previously, prior),
                                    "manual_checks": questions}))
    return reply
