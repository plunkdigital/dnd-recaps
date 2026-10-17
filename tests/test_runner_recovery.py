"""Synthetic regressions reproducing the observed overnight failure shapes."""

import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import campaign, cli, relevance
from summary_fixtures import response


def blocks(*texts):
    return json.dumps({"blocks": [{"markdown": text, "evidence": [1]} for text in texts]})


class OvernightRecoveryTests(unittest.TestCase):
    def test_schema_excludes_inline_markers_and_multiple_paragraphs(self):
        schema = relevance.narrative_response_format({1: "c0000:s0001"})
        pattern = schema["schema"]["properties"]["blocks"]["items"]["properties"]["markdown"]["pattern"]
        for invalid in ("The gate opened [1].", "Choice [62,63,113-132].",
                        "A paragraph.\n\nA second paragraph.", "Fact [E1].", "One line.\n"):
            with self.subTest(invalid=invalid):
                self.assertIsNone(re.fullmatch(pattern, invalid))
                self.assertIsNone(relevance.render_evidence_blocks(blocks(invalid), {1: "c0000:s0001"}))
        self.assertIsNotNone(re.fullmatch(pattern, "The gate opened."))

    def test_compact_schema_bounds_total_output_without_losing_source_ids(self):
        mapping = {1: "c0000:s0001", 2: "c0000:s0002", 3: "c0000:s0003"}
        schema = relevance.narrative_response_format(mapping, compact=True)["schema"]["properties"]["blocks"]
        self.assertEqual(schema["maxItems"], 4)
        properties = schema["items"]["properties"]
        self.assertEqual(properties["evidence"]["minItems"], 1)
        for length in (46, 98):
            self.assertIsNone(re.fullmatch(properties["markdown"]["pattern"], "word " * (length - 1) + "word"))
        self.assertIsNotNone(re.fullmatch(properties["markdown"]["pattern"], "word " * 44 + "word"))
        maximum = {"blocks": [{"markdown": "word " * 44 + "word", "evidence": [1, 2, 3]} for _ in range(4)]}
        rendered = relevance.render_evidence_blocks(json.dumps(maximum), mapping, compact=True)
        self.assertIsNotNone(rendered)
        self.assertLessEqual(len(rendered), 2400)
        self.assertEqual(relevance.citations(rendered), set(mapping.values()))

    def test_each_observed_bad_shape_gets_one_recovery_from_original_evidence(self):
        invalid_responses = {
            "session3_numeric_markers": blocks("A clue [1,2,3] changed the plan."),
            "session5_shared_paragraph": blocks("A resolved action.\n\nAnother resolved action."),
            "session6_490_words": blocks(*["word " * 97 + "word" for _ in range(5)]),
        }
        valid = blocks("The party opened the gate.")
        for failure, invalid in invalid_responses.items():
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory, \
                    patch.object(cli, "api", side_effect=[response(invalid), response(valid)]) as api, \
                    contextlib.redirect_stdout(io.StringIO()):
                cache = Path(directory)
                result = relevance.generate_cited("Scene", "Original gate evidence [c0000:s0001]",
                                                  "fixture", cache, "scene window 1", compact=True)
                repeated = relevance.generate_cited("Scene", "Original gate evidence [c0000:s0001]",
                                                    "fixture", cache, "scene window 1", compact=True)
                self.assertEqual(result, "The party opened the gate. [c0000:s0001]")
                self.assertEqual(repeated, result)
                self.assertEqual(api.call_count, 2)
                first, recovery = [json.loads(call.args[1]) for call in api.call_args_list]
                self.assertEqual(first["input"], recovery["input"])
                self.assertNotIn("A resolved action", recovery["input"])
                self.assertIn("Compact-note recovery", recovery["instructions"])
                self.assertEqual(first["text"]["format"], recovery["text"]["format"])
                self.assertEqual(len(list(cache.glob("*.json"))), 2)

    def test_repeated_oversize_is_rejected_without_truncation_or_repeated_billing(self):
        invalid = blocks(*["word " * 97 + "word" for _ in range(5)])
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "api", return_value=response(invalid)) as api, \
                contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, "including one recovery attempt"):
                    relevance.generate_cited("Scene", "Evidence [c0000:s0001]", "fixture", Path(directory),
                                              "scene window 1", compact=True)
            self.assertEqual(api.call_count, 2)
            for path in Path(directory).glob("*.json"):
                self.assertEqual(cli.read_json(path), response(invalid))

    def test_compact_budget_survives_output_cutoff_split_recovery(self):
        original = "First evidence [c0000:s0001]\nSecond evidence [c0000:s0002]"
        def reply(endpoint, body):
            data = json.loads(body)
            schema = data["text"]["format"]["schema"]["properties"]["blocks"]
            self.assertEqual(schema["maxItems"], 4)
            if data["input"] == relevance.citation_transport("", original)[1]:
                return {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": []}
            return response(blocks("Completed compact evidence."))
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "api", side_effect=reply), \
                contextlib.redirect_stdout(io.StringIO()):
            result = relevance.generate_cited("Scene", original, "fixture", Path(directory), "scene 1", compact=True)
        self.assertIn("Completed compact evidence", result)

    def test_archived_duplicate_is_excluded_but_active_duplicates_remain_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = {"campaign": "test", "session_number": 4}
            prior = root / "sessions/canonical"
            archive = root / "sessions/interrupted"
            cli.save_json(prior / "session.json", {"campaign": "test", "session_number": 3})
            cli.save_json(archive / "session.json", {"campaign": "test", "session_number": 3, "archived": True})
            cli.write(archive / "summaries/recap.reviewed.md", "ARCHIVED_MUST_NOT_ENTER_CONTEXT")
            self.assertEqual(campaign.previous_recap(root, root / "sessions/current", metadata, "cuda-diarized"), ("", None))
            cli.write(prior / "summaries/recap.reviewed.md", "Reviewed canonical history [c0000:s0001]")
            result, path = campaign.previous_recap(root, root / "sessions/current", metadata, "cuda-diarized")
            self.assertIn("canonical history", result)
            self.assertIn("canonical/", path)
            cli.save_json(archive / "session.json", {"campaign": "test", "session_number": 3, "archived": False})
            with self.assertRaisesRegex(ValueError, "Multiple preceding"):
                campaign.previous_recap(root, root / "sessions/current", metadata, "cuda-diarized")
