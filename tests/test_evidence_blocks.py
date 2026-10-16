import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli, relevance
from summary_fixtures import response


class EvidenceBlockTests(unittest.TestCase):
    def test_code_renders_exact_ids_from_numeric_references(self):
        mapping = {1: "c0000:s0004", 2: "c0002:s0017"}
        output = json.dumps({"blocks": [{"markdown": "## The tale", "evidence": []},
                                        {"markdown": "The gate opened.", "evidence": [2, 1]}]})
        self.assertEqual(relevance.render_evidence_blocks(output, mapping),
                         "## The tale\n\nThe gate opened. [c0002:s0017] [c0000:s0004]")

    def test_invalid_numeric_references_or_inline_markers_are_rejected(self):
        for refs in ([0], [-1], [2], [True], [1.0], ["1"], ["1-3"], [1, 1], None):
            with self.subTest(refs=refs):
                raw = json.dumps({"blocks": [{"markdown": "Fact", "evidence": refs}]})
                self.assertIsNone(relevance.render_evidence_blocks(raw, {1: "c0000:s0000"}))
        for text in ("Fact [E1]", "Fact c0000:s0000", "Fact [c0000:s0000–s0003]"):
            raw = json.dumps({"blocks": [{"markdown": text, "evidence": [1]}]})
            self.assertIsNone(relevance.render_evidence_blocks(raw, {1: "c0000:s0000"}))

    def test_factual_blocks_cannot_hide_behind_one_cited_block(self):
        raw = json.dumps({"blocks": [{"markdown": "Unsupported event.", "evidence": []},
                                     {"markdown": "Supported event.", "evidence": [1]}]})
        self.assertIsNone(relevance.render_evidence_blocks(raw, {1: "c0000:s0000"}))

    def test_same_numeric_text_with_different_ids_has_different_cache_identity(self):
        a, text_a, mapping_a = relevance.citation_transport("Write", "Event [c0000:s0001]")
        b, text_b, mapping_b = relevance.citation_transport("Write", "Event [c0003:s0080]")
        self.assertEqual(text_a, text_b)
        self.assertNotEqual(a, b)
        self.assertNotEqual(mapping_a, mapping_b)

    def test_numeric_contract_runs_and_reuses_raw_response_cache(self):
        raw = response(json.dumps({"blocks": [{"markdown": "The gate opened.", "evidence": [1]}]}))
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "api", return_value=raw) as api:
            cache = Path(directory)
            result = relevance.generate_cited("Write", "Evidence [c0007:s0042]", "fixture", cache, "final recap")
            again = relevance.generate_cited("Write", "Evidence [c0007:s0042]", "fixture", cache, "final recap")
            self.assertEqual(result, "The gate opened. [c0007:s0042]")
            self.assertEqual(again, result)
            self.assertEqual(api.call_count, 1)
            sent = json.loads(api.call_args.args[1])
            self.assertIn("Narrative evidence blocks v1", sent["instructions"])
            self.assertEqual(sent["input"], "Evidence [E1]")
            self.assertEqual(cli.read_json(next(cache.glob("*.json"))), raw)

    def test_bad_reference_retry_uses_only_supplied_evidence(self):
        outputs = [response(json.dumps({"blocks": [{"markdown": "Bad", "evidence": [999]}]})),
                   response(json.dumps({"blocks": [{"markdown": "Valid", "evidence": [1]}]}))]
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "api", side_effect=outputs) as api, \
                contextlib.redirect_stdout(io.StringIO()):
            result = relevance.generate_cited("Write", "Evidence [c0000:s0000]", "fixture", Path(directory), "recap")
        self.assertEqual(result, "Valid [c0000:s0000]")
        self.assertNotIn("999", json.loads(api.call_args.args[1])["input"])

    def test_malformed_json_does_not_become_valid_narrative_evidence(self):
        for raw in ('{"blocks":null}', '[]', '{"blocks":[]}', '{"blocks":[{"markdown":"Story"}]}'):
            with self.subTest(raw=raw):
                self.assertIsNone(relevance.render_evidence_blocks(raw, {1: "c0000:s0000"}))
