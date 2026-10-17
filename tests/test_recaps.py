"""Whole-session recap behavior and failures, without audio or paid requests."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli, recap
from summary_fixtures import response, summary_reply


ROOT = Path(__file__).resolve().parents[1]
STORY = "# Session recap\n\n## The tale\n\nAzlor opened the gate. [c0000:s0000]"


class RecapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("context", "prompts", "config"):
            shutil.copytree(ROOT / name, self.root / name)
        self.dest = self.root / "sessions/test"
        cli.save_json(self.dest / "session.json", {"session_number": 1, "context_policy": "recording_only"})
        self.segments = [
            {"id": "c0000:s0000", "start": 10, "end": 14, "speaker": "unknown", "text": "Azlor opened the gate."},
            {"id": "c0000:s0001", "start": 20, "end": 24, "speaker": "unknown", "text": "Ambiguous chatter."}]
        cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json", {"segments": self.segments})
        self.out = self.dest / "summaries/cuda-diarized"

    def revise_prompt(self, revision):
        with (self.root / "prompts/recap.md").open("a") as stream:
            stream.write(f"\nSynthetic revision {revision}\n")

    def run_summary(self):
        with contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "fixture", "cuda-diarized")

    def test_one_request_caches_and_preserves_human_logs_and_raw_transcript(self):
        transcript = self.dest / "transcripts/cuda-diarized/transcript.json"
        original = transcript.read_bytes()
        cli.write(self.dest / "manual-check.md", "Human decisions")
        cli.write(self.dest / "review.md", "Human corrections")
        cli.write(self.out / "recap.reviewed.md", "Approved copy")
        question = {"source_ids": ["c0000:s0001"], "topic": "Unclear reference", "question": "Does this concern the campaign?"}
        with patch.object(cli, "api", side_effect=summary_reply(STORY, [question])) as api:
            self.run_summary()
            self.run_summary()
        self.assertEqual(api.call_count, 1)
        self.assertEqual(transcript.read_bytes(), original)
        self.assertEqual((self.dest / "manual-check.md").read_text(), "Human decisions")
        self.assertEqual((self.dest / "review.md").read_text(), "Human corrections")
        self.assertEqual((self.out / "recap.reviewed.md").read_text(), "Approved copy")
        report = (self.out / "manual-check.draft.md").read_text()
        self.assertIn("20.00-24.00s", report)
        self.assertIn("not an exhaustive classification", report)
        self.assertNotIn("c0000:s0001", (self.out / "recap.draft.md").read_text())
        self.assertEqual(cli.read_json(self.out / "provenance.json")["narrative_method"], "full_transcript_v1")

    def test_unknown_or_withheld_or_malformed_citations_fail_without_retries(self):
        question = {"source_ids": ["c0000:s0001"], "topic": "Unclear", "question": "Campaign related?"}
        for text in ("Invented [c9999:s9999]", "Withheld [c0000:s0001]",
                     "Partial [c0000:s0000] [1-8]", "Bare c0000:s0000", "No references"):
            self.revise_prompt(text)
            with self.subTest(text=text), patch.object(cli, "api", side_effect=summary_reply(text, [question])) as api:
                with self.assertRaises(ValueError):
                    self.run_summary()
                self.assertEqual(api.call_count, 1)
                self.assertFalse((self.out / "recap.draft.md").exists())

    def test_invalid_manual_questions_and_previous_context_never_publish(self):
        invalid = [
            {"source_ids": ["c9999:s9999"], "topic": "Unknown", "question": "What?"},
            {"source_ids": [], "topic": "Missing source", "question": "What?"},
            {"source_ids": ["c0000:s0001"], "topic": "", "question": "What?"}]
        for question in invalid:
            self.revise_prompt(question)
            with self.subTest(question=question), patch.object(cli, "api", side_effect=summary_reply(STORY, [question])):
                with self.assertRaises(ValueError):
                    self.run_summary()
        self.revise_prompt("prior")
        with patch.object(cli, "api", side_effect=summary_reply(STORY, previously="Old event [c0000:s0000]")):
            with self.assertRaisesRegex(ValueError, "reviewed previous"):
                self.run_summary()
        self.revise_prompt("Previously heading")
        with patch.object(cli, "api", side_effect=summary_reply(STORY + "\n## Previously\nOld event")):
            with self.assertRaisesRegex(ValueError, "Previously"):
                self.run_summary()
        self.assertFalse((self.out / "manual-check.draft.md").exists())

    def test_incomplete_refused_and_invalid_responses_leave_successful_outputs_intact(self):
        with patch.object(cli, "api", side_effect=summary_reply(STORY)):
            self.run_summary()
        before = {p: p.read_bytes() for p in self.out.glob("*") if p.is_file()}
        failures = [
            {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": []},
            {"status": "failed", "output": []},
            {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "Private"}]}]},
            response("Malformed JSON")]
        for index, raw in enumerate(failures):
            with (self.root / "prompts/recap.md").open("a") as stream:
                stream.write(f"\nPrompt revision {index}\n")
            with self.subTest(index=index), patch.object(cli, "api", return_value=raw) as api:
                for _ in range(2):
                    with self.assertRaises(ValueError):
                        self.run_summary()
                self.assertEqual(api.call_count, 1)
                self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_oversized_input_stops_before_upload_without_truncation(self):
        self.segments[0]["text"] = "é" * cli.MAX_SUMMARY_INPUT_BYTES
        cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json", {"segments": self.segments})
        with patch.object(cli, "api") as api, self.assertRaisesRegex(ValueError, "750,000"):
            self.run_summary()
        api.assert_not_called()

    def test_no_events_returns_plain_empty_account_and_manual_review(self):
        with patch.object(cli, "api", side_effect=summary_reply("")) as api:
            self.run_summary()
        self.assertEqual(api.call_count, 1)
        self.assertIn("No campaign events were established", (self.out / "recap.draft.md").read_text())

    def test_editorial_length_is_not_a_machine_quota(self):
        long = "# Session recap\n\n" + "The party crossed the threshold. " * 300 + "[c0000:s0000]"
        with patch.object(cli, "api", side_effect=summary_reply(long)):
            self.run_summary()
        self.assertIn(long, (self.out / "recap.draft.md").read_text())

    def test_model_prompt_and_names_invalidate_the_request_cache(self):
        with patch.object(cli, "api", side_effect=summary_reply(STORY)) as api:
            self.run_summary()
            cli.summarize(self.root, self.dest, "other-model", "cuda-diarized")
            with (self.root / "prompts/recap.md").open("a") as stream:
                stream.write("\nUse deliberate pacing.\n")
            self.run_summary()
            names = self.root / "context/campaign/names.json"
            data = cli.read_json(names)
            data["names"][0]["aliases"].append("Synthetic spelling")
            cli.save_json(names, data)
            self.run_summary()
        self.assertEqual(api.call_count, 4)

    def test_cli_uses_explicit_test_config_and_redacts_unexpected_exception(self):
        argv = ["dnd-recaps", "--root", str(self.root), "--env-file", "config/codex-test.env",
                "summarize", "test", "--transcript-backend", "cuda-diarized", "--allow-cloud"]
        with patch.object(cli.sys, "argv", argv), patch.object(cli, "summarize", side_effect=TypeError("PRIVATE_VALUE")), contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit):
                cli.main()
        self.assertIn("TypeError", stderr.getvalue())
        self.assertNotIn("PRIVATE_VALUE", stderr.getvalue())
