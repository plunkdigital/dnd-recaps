import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli, relevance
from summary_fixtures import response


class CitationRecoveryTests(unittest.TestCase):
    def test_exact_individual_ids_only(self):
        allowed = {"c0000:s0001", "c0000:s0004"}
        self.assertTrue(relevance.valid_citations("A claim [c0000:s0001] [c0000:s0004]", allowed))
        bad = ["No citation", "[c9999:s9999]", "[c0000:s0001–s0004]",
               "[c0000:s0001-c0000:s0004]", "[c0000:s0001, c0000:s0004]",
               "[c0000:s0001] and c0000:s0004", "[c0000:s0001] and [s0004]",
               "[c0000:s0001] [c0000:s0004–s0010]",
               "[c0000:s0001] [c0000:s9999]", "[c0000:s0001] [c0000 : s0004]"]
        for text in bad:
            with self.subTest(text=text):
                self.assertFalse(relevance.valid_citations(text, allowed))

    def test_single_rewrite_reuses_evidence_and_preserves_both_cached_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            source = "Grounded evidence [c0000:s0001] [c0000:s0004]"
            invalid = "INVALID_DRAFT_SENTINEL [c0000:s0001–s0004]"
            valid = "Grounded story [c0000:s0001] [c0000:s0004]"
            with patch.object(cli, "api", side_effect=[response(invalid), response(valid)]) as api, \
                    contextlib.redirect_stdout(io.StringIO()):
                output = relevance.generate_cited("Write a tale", source, "fixture-model", cache, "final recap")
                repeated = relevance.generate_cited("Write a tale", source, "fixture-model", cache, "final recap")
            self.assertEqual(output, valid)
            self.assertEqual(repeated, valid)
            self.assertEqual(api.call_count, 2)
            self.assertEqual(len(list(cache.glob("*.json"))), 2)
            retry = json.loads(api.call_args_list[1].args[1])
            self.assertEqual(retry["input"], "Grounded evidence [E1] [E2]")
            self.assertNotIn("INVALID_DRAFT_SENTINEL", json.dumps(retry))
            self.assertIn("Citation recovery attempt 1", retry["instructions"])

    def test_second_failure_stops_with_stage_specific_error(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(cli, "api", return_value=response("Still unsupported [c9999:s9999]")) as api, \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "note reduction level 2, including one recovery attempt"):
                relevance.generate_cited("Reduce", "Notes [c0000:s0001]", "fixture", Path(directory),
                                         "note reduction level 2")
            self.assertEqual(api.call_count, 2)

    def test_correct_first_response_needs_no_recovery(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(cli, "api", return_value=response("Story [c0000:s0001]")) as api:
            relevance.generate_cited("Write", "Notes [c0000:s0001]", "fixture", Path(directory), "final recap")
            self.assertEqual(api.call_count, 1)

    def test_incomplete_response_does_not_retry_or_become_a_cached_success(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(cli, "api", return_value={"status": "incomplete"}) as api:
            with self.assertRaises(ValueError):
                relevance.generate_cited("Write", "Notes [c0000:s0001]", "fixture", Path(directory), "final recap")
            self.assertEqual(api.call_count, 1)
            self.assertEqual(list(Path(directory).glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
