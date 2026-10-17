"""Synthetic complete responses for the single-request recap workflow."""

import json


def response(text):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]}


def summary_reply(final_text, checks=None, previously=""):
    def reply(endpoint, body):
        return response(json.dumps({"recap_markdown": final_text,
                                    "previously_markdown": previously,
                                    "manual_checks": checks or []}))
    return reply
