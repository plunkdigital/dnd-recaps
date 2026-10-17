"""Complete CLI regressions for classification recovery and safe failures."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli, relevance
from summary_fixtures import response


ROOT = Path(__file__).resolve().parents[1]


class DirectSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("context", "prompts", "config"):
            shutil.copytree(ROOT / name, self.root / name)
        self.dest = self.root / "sessions/fixture"
        cli.save_json(self.dest / "session.json", {"session_number": 1, "context_policy": "recording_only"})
        self.argv = ["dnd-recaps", "--root", str(self.root), "--env-file", "config/codex-test.env",
                     "summarize", "fixture", "--transcript-backend", "cuda-diarized", "--allow-cloud"]

    def test_full_cli_repairs_bad_cached_classification_and_finishes_multiwindow_story(self):
        segments = [{"id": f"c0000:s{i:04d}", "start": i * 10, "end": i * 10 + 9,
                     "speaker": "unknown", "text": "Azlor crossed the gate and examined the rune. " * 13}
                    for i in range(70)]
        cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json", {"segments": segments})
        calls = {"legacy": 0, "strict": 0, "scene": 0, "final": 0}
        def reply(endpoint, body):
            payload = json.loads(body)
            fmt = payload.get("text", {}).get("format")
            if fmt is None:
                calls["legacy"] += 1
                return response("A non-JSON relevance response matching the observed failure shape.")
            if fmt["name"] == "campaign_source_labels":
                expected = fmt["schema"]["properties"]["classifications"]["required"]
                self.assertLessEqual(len(expected), 32)
                calls["strict"] += 1
                return response(json.dumps({"classifications": {
                    source: {"category": "campaign", "question": ""} for source in expected}}))
            if "Chronological scene evidence v2" in payload["instructions"]:
                calls["scene"] += 1
                return response(json.dumps({"blocks": [{"markdown": "Azlor crossed the gate and examined the rune.", "evidence": [1]}]}))
            calls["final"] += 1
            return response(json.dumps({"blocks": [
                {"markdown": "# Session recap", "evidence": []},
                {"markdown": "## The tale", "evidence": []},
                *[{"markdown": ("Azlor crossed the gate and examined the rune. " * 10).strip(),
                   "evidence": [1 + i % 2]} for i in range(8)]]}))
        with patch.object(cli.sys, "argv", self.argv), patch.object(cli, "api", side_effect=reply) as api, \
                patch.dict(cli.os.environ, {"OPENAI_API_KEY": "synthetic"}, clear=True), \
                patch.object(cli, "generation_cached", return_value=True), contextlib.redirect_stdout(io.StringIO()):
            cli.main()
            cache = self.dest / "summaries/cuda-diarized/cache"
            saved = {p: p.read_bytes() for p in cache.glob("*.json")}
            count = api.call_count
            cli.main()
            self.assertEqual(api.call_count, count)
            self.assertTrue(all(p.read_bytes() == value for p, value in saved.items()))
        report = cli.read_json(self.dest / "summaries/cuda-diarized/manual-check.draft.json")
        self.assertEqual(report["unclassified_source_ids"], [])
        self.assertEqual(set(report["campaign_source_ids"]), {segment["id"] for segment in segments})
        provenance = cli.read_json(self.dest / "summaries/cuda-diarized/provenance.json")
        self.assertEqual(provenance["relevance_extraction_version"], 2)
        self.assertEqual(provenance["narrative_method"], "chronological_original_evidence_v2")
        self.assertGreater(calls["scene"], 1)
        self.assertEqual(calls["final"], 1)
        recap = (self.dest / "summaries/cuda-diarized/recap.draft.md").read_text()
        self.assertNotIn("Previously", recap)

    def test_fresh_cli_uses_structured_labels_without_requesting_legacy_json(self):
        cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json", {"segments": [
            {"id": "c0000:s0000", "start": 0, "end": 1, "speaker": "unknown", "text": "The gate opened."}]})
        def reply(endpoint, body):
            payload = json.loads(body)
            self.assertIn("text", payload)
            if payload["text"]["format"]["name"] == "campaign_source_labels":
                return response(json.dumps({"classifications": {"c0000:s0000": {"category": "campaign", "question": ""}}}))
            return response(json.dumps({"blocks": [{"markdown": "# Session recap", "evidence": []},
                                                    {"markdown": "The gate opened.", "evidence": [1]}]}))
        with patch.object(cli.sys, "argv", self.argv), patch.object(cli, "api", side_effect=reply) as api, \
                patch.dict(cli.os.environ, {"OPENAI_API_KEY": "synthetic"}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            cli.main()
        self.assertEqual(api.call_count, 2)

    def test_repair_preserves_valid_cached_categories_and_classifies_only_omissions(self):
        cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json", {"segments": [
            {"id": "c0000:s0000", "start": 0, "end": 1, "speaker": "unknown", "text": "UNRELATED_SENTINEL"},
            {"id": "c0000:s0001", "start": 2, "end": 3, "speaker": "unknown", "text": "The gate opened."}]})
        def reply(endpoint, body):
            payload = json.loads(body)
            if "text" not in payload:
                return response(json.dumps({"items": [{"source_ids": ["c0000:s0000"], "category": "unrelated"}]}))
            schema = payload["text"]["format"]
            if schema["name"] == "campaign_source_labels":
                self.assertEqual(schema["schema"]["properties"]["classifications"]["required"], ["c0000:s0001"])
                return response(json.dumps({"classifications": {"c0000:s0001": {"category": "campaign", "question": ""}}}))
            self.assertNotIn("UNRELATED_SENTINEL", payload["input"])
            return response(json.dumps({"blocks": [{"markdown": "The gate opened.", "evidence": [1]}]}))
        with patch.object(cli.sys, "argv", self.argv), patch.object(cli, "api", side_effect=reply), \
                patch.dict(cli.os.environ, {"OPENAI_API_KEY": "synthetic"}, clear=True), \
                patch.object(cli, "generation_cached", return_value=True), contextlib.redirect_stdout(io.StringIO()):
            cli.main()
        report = cli.read_json(self.dest / "summaries/cuda-diarized/manual-check.draft.json")
        self.assertEqual(report["campaign_source_ids"], ["c0000:s0001"])
        self.assertEqual(report["unclassified_source_ids"], [])

    def test_native_labels_have_exact_required_ids_and_uncertain_questions(self):
        expected = {f"c0000:s{i:04d}" for i in range(65)}
        seen = set()
        def reply(endpoint, body):
            payload = json.loads(body)
            schema = payload["text"]["format"]["schema"]
            ids = schema["properties"]["classifications"]["required"]
            self.assertFalse(seen.intersection(ids))
            seen.update(ids)
            return response(json.dumps({"classifications": {
                identity: {"category": "uncertain", "question": "Does this concern the campaign?"} for identity in ids}}))
        with patch.object(cli, "api", side_effect=reply) as api:
            items = relevance.classify_sources("Reference", "Transcript context", expected, "fixture", self.root / "cache")
        self.assertEqual(api.call_count, 3)
        self.assertEqual(seen, expected)
        self.assertTrue(all(item["category"] == "uncertain" and item["question"] for item in items))

    def test_partial_native_schema_cannot_claim_complete_classification(self):
        with patch.object(cli, "api", return_value=response(json.dumps({"classifications": {
                "c0000:s0000": {"category": "campaign", "question": ""}}}))), contextlib.redirect_stdout(io.StringIO()):
            items = relevance.classify_sources("Reference", "Transcript", {"c0000:s0000", "c0000:s0001"},
                                               "fixture", self.root / "cache")
        self.assertTrue(all(item["category"] == "uncertain" for item in items))
        self.assertEqual({source for item in items for source in item["source_ids"]}, {"c0000:s0000", "c0000:s0001"})

    def test_duplicate_native_keys_do_not_select_a_winning_category(self):
        text = '{"classifications":{"c0000:s0000":{"category":"campaign","question":""},"c0000:s0000":{"category":"unrelated","question":""}}}'
        with patch.object(cli, "api", return_value=response(text)), contextlib.redirect_stdout(io.StringIO()):
            items = relevance.classify_sources("Reference", "Transcript", {"c0000:s0000"}, "fixture", self.root / "cache")
        self.assertEqual(items[0]["category"], "uncertain")

    def test_cli_exception_reports_type_without_private_details(self):
        with patch.object(cli.sys, "argv", self.argv), \
                patch.object(cli, "summarize", side_effect=TypeError("PRIVATE_VALUE_MUST_NOT_LEAK")), \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit):
                cli.main()
        self.assertIn("TypeError", stderr.getvalue())
        self.assertIn("cli.py:", stderr.getvalue())
        self.assertNotIn("PRIVATE_VALUE", stderr.getvalue())

    def test_summary_modules_are_loaded_before_provider_work(self):
        for name in ("narrative", "relevance", "campaign"):
            self.assertIn("dnd_recaps." + name, sys.modules)
            self.assertIs(getattr(cli, name), sys.modules["dnd_recaps." + name])
