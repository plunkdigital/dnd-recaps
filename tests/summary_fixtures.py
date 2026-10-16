"""Synthetic provider replies for the selection and story stages."""

import json
import re


def response(text):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]}


def summary_reply(final_text):
    def reply(endpoint, body):
        data = json.loads(body)
        if "Campaign relevance extraction v1" in data["instructions"]:
            ids = sorted(set(re.findall(r"\[(c\d+:s\d+)\]", data["input"])))
            return response(json.dumps({"items": [{"source_ids": ids, "category": "campaign",
                                                   "note": "Grounded campaign evidence."}]}))
        return response(final_text)
    return reply
