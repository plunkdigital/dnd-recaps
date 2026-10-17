import contextlib
import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli, relevance
from summary_fixtures import response


def cutoff():
    raw = response("PARTIAL_TEXT_MUST_NOT_BE_USED")
    raw.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
    return raw


class SummaryLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)
        self.source = "\n".join(f"Original evidence {i} [c0000:s{i:04d}]" for i in range(4))

    def test_output_cutoff_is_preserved_separately_and_reused_without_rebilling(self):
        with patch.object(cli, "api", return_value=cutoff()) as api:
            for _ in range(2):
                with self.assertRaises(cli.SummaryOutputLimit):
                    cli.generate("instructions", self.source, "fixture", self.cache)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(list(self.cache.glob("*.json")), [])
        saved = cli.read_json(next((self.cache / "incomplete").glob("*.json")))
        self.assertEqual(saved["status"], "incomplete")

    def test_split_reduce_recombine_never_uses_partial_text_and_caches_all_work(self):
        def reply(endpoint, body):
            data = json.loads(body)
            if data["input"] == relevance.citation_transport("", self.source)[1]:
                return cutoff()
            first = min(int(n) for n in re.findall(r"\[E(\d+)\]", data["input"]))
            prefix = "Compact evidence" if "Output-limit recovery v1" in data["instructions"] else "Final story"
            return response(json.dumps({"blocks": [{"markdown": prefix, "evidence": [first]}]}))
        with patch.object(cli, "api", side_effect=reply) as api, contextlib.redirect_stdout(io.StringIO()):
            result = relevance.generate_cited("Write", self.source, "fixture", self.cache, "final recap")
            again = relevance.generate_cited("Write", self.source, "fixture", self.cache, "final recap")
        self.assertEqual(result, again)
        self.assertIn("Final story", result)
        self.assertEqual(api.call_count, 4)
        for call in api.call_args_list[1:]:
            self.assertNotIn("PARTIAL_TEXT_MUST_NOT_BE_USED", call.args[1].decode())
        self.assertEqual(len(list(self.cache.glob("*.json"))), 3)
        self.assertEqual(len(list((self.cache / "incomplete").glob("*.json"))), 1)

    def test_non_limit_incomplete_or_failed_responses_never_split(self):
        variants = [("incomplete", None), ("incomplete", "content_filter"),
                    ("failed", "max_output_tokens"), ("incomplete", "PRIVATE_REASON_SENTINEL")]
        for index, (status, reason) in enumerate(variants):
            raw = {"status": status, "incomplete_details": {"reason": reason}, "output": []}
            with self.subTest(status=status, reason=reason), patch.object(cli, "api", return_value=raw) as api:
                with self.assertRaises(ValueError) as error:
                    relevance.generate_cited("Write", self.source, "fixture", self.cache / str(index), "final recap")
                self.assertNotIsInstance(error.exception, cli.SummaryOutputLimit)
                self.assertNotIn("PRIVATE_REASON_SENTINEL", str(error.exception))
                self.assertEqual(api.call_count, 1)

    def test_recovery_budget_is_bounded_and_does_not_publish_partial_text(self):
        state = {"splits": 3}
        with patch.object(cli, "api", return_value=cutoff()) as api:
            with self.assertRaisesRegex(ValueError, "bounded recovery"):
                relevance.generate_cited("Write", self.source, "fixture", self.cache, "final recap", state)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(list(self.cache.glob("*.json")), [])

    def test_single_evidence_line_is_not_truncated_to_force_a_split(self):
        with patch.object(cli, "api", return_value=cutoff()) as api:
            with self.assertRaisesRegex(ValueError, "cannot split further"):
                relevance.generate_cited("Write", "Single evidence [c0000:s0001]", "fixture", self.cache, "final recap")
        self.assertEqual(api.call_count, 1)

    def test_repeated_cutoffs_consume_at_most_three_splits(self):
        source = "\n".join(f"Evidence {i} [c0000:s{i:04d}]" for i in range(8))
        with patch.object(cli, "api", return_value=cutoff()) as api, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "bounded recovery"):
                relevance.generate_cited("Write", source, "fixture", self.cache, "final recap")
        self.assertEqual(api.call_count, 4)

    def test_cutoff_during_citation_repair_also_uses_bounded_split(self):
        def reply(endpoint, body):
            data = json.loads(body)
            if data["input"] == relevance.citation_transport("", self.source)[1]:
                return cutoff() if "Citation recovery attempt 1" in data["instructions"] else response("No citations")
            first = min(int(n) for n in re.findall(r"\[E(\d+)\]", data["input"]))
            return response(json.dumps({"blocks": [{"markdown": "Grounded result", "evidence": [first]}]}))
        with patch.object(cli, "api", side_effect=reply) as api, contextlib.redirect_stdout(io.StringIO()):
            result = relevance.generate_cited("Write", self.source, "fixture", self.cache, "final recap")
        self.assertTrue(relevance.valid_citations(result, relevance.citations(self.source)))
        self.assertEqual(api.call_count, 5)

    def test_network_error_does_not_trigger_smaller_requests(self):
        with patch.object(cli, "api", side_effect=ValueError("Synthetic network failure")) as api:
            with self.assertRaisesRegex(ValueError, "network failure"):
                relevance.generate_cited("Write", self.source, "fixture", self.cache, "final recap")
        self.assertEqual(api.call_count, 1)

    def test_short_cutoff_matches_live_failure_and_does_not_split(self):
        raw = cutoff()
        raw["usage"] = {"output_tokens": 294, "output_tokens_details": {"reasoning_tokens": 0}}
        with patch.object(cli, "api", return_value=raw) as api:
            for _ in range(2):
                with self.assertRaisesRegex(cli.SummaryShortOutput, "294/5000"):
                    relevance.generate_cited("Scene", self.source, "fixture", self.cache, "scene window 4", compact=True)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(list(self.cache.glob("*.json")), [])
        self.assertEqual(cli.read_json(next((self.cache / "incomplete").glob("*.json"))), raw)

    def test_completed_older_word_regex_scene_is_reused_without_provider_call(self):
        instructions, source, mapping = relevance.citation_transport("Scene", self.source, compact=True)
        old_format = relevance.narrative_response_format(mapping, compact=True)
        old_format["schema"]["properties"]["blocks"]["items"]["properties"]["markdown"]["pattern"] = r"^([^\s\[\]]+[ \t]+){0,44}[^\s\[\]]+$"
        _, cache, _ = cli.generation_request(instructions, source, "fixture", self.cache, old_format)
        raw = response(json.dumps({"blocks": [{"markdown": "The gate opened.", "evidence": [1]}]}))
        cli.save_json(cache, raw)
        before = cache.read_bytes()
        with patch.object(cli, "api", side_effect=AssertionError("No provider call allowed")):
            rendered = relevance.generate_cited("Scene", self.source, "fixture", self.cache, "scene window 1", compact=True)
        self.assertEqual(rendered, "The gate opened. [c0000:s0000]")
        self.assertEqual(cache.read_bytes(), before)
        self.assertEqual(len(list(self.cache.glob("*.json"))), 1)

    def test_old_short_incomplete_does_not_poison_the_simplified_schema(self):
        instructions, source, mapping = relevance.citation_transport("Scene", self.source, compact=True)
        old_format = relevance.narrative_response_format(mapping, compact=True)
        old_format["schema"]["properties"]["blocks"]["items"]["properties"]["markdown"]["pattern"] = r"^([^\s\[\]]+[ \t]+){0,44}[^\s\[\]]+$"
        _, _, diagnostic = cli.generation_request(instructions, source, "fixture", self.cache, old_format)
        old = cutoff()
        old["usage"] = {"output_tokens": 227}
        cli.save_json(diagnostic, old)
        completed = response(json.dumps({"blocks": [{"markdown": "A completed finding.", "evidence": [1]}]}))
        with patch.object(cli, "api", return_value=completed) as api:
            result = relevance.generate_cited("Scene", self.source, "fixture", self.cache, "scene window 4", compact=True)
        self.assertEqual(api.call_count, 1)
        self.assertIn("A completed finding", result)
        sent = json.loads(api.call_args.args[1])
        self.assertEqual(sent["text"]["format"]["schema"]["properties"]["blocks"]["items"]["properties"]["markdown"]["pattern"],
                         r"^[^\[\]\r\n]+$")
        self.assertEqual(cli.read_json(diagnostic), old)

    def test_full_budget_exhaustion_still_gets_bounded_split_recovery(self):
        raw = cutoff()
        raw["usage"] = {"output_tokens": 5000}
        state = {"splits": 3}
        with patch.object(cli, "api", return_value=raw), self.assertRaisesRegex(ValueError, "bounded recovery"):
            relevance.generate_cited("Scene", self.source, "fixture", self.cache, "scene window 4", state, compact=True)
