"""Whole-session recap behavior and failures, without audio or paid requests."""

import contextlib
import hashlib
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

    def test_reasoning_model_request_and_cache_are_separate_from_legacy_requests(self):
        for model in ("gpt-6-astra", "gpt-5.4", "gpt-5.4-2026-03-05"):
            with self.subTest(model=model):
                encoded, cache, _ = cli.generation_request("instructions", "dialogue", model, self.out)
                payload = json.loads(encoded)
                self.assertEqual(payload["reasoning"], {"effort": "medium"})
                self.assertEqual(payload["max_output_tokens"], 25000)
                self.assertFalse(payload["store"])
                legacy = dict(payload)
                legacy.pop("reasoning")
                legacy["max_output_tokens"] = 8192
                self.assertNotEqual(cache.stem, hashlib.sha256(json.dumps(legacy, ensure_ascii=False).encode()).hexdigest())
        encoded, _, _ = cli.generation_request("instructions", "dialogue", "gpt-4.1-mini", self.out)
        self.assertNotIn("reasoning", json.loads(encoded))
        self.assertEqual(json.loads(encoded)["max_output_tokens"], 8192)

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
        provenance = cli.read_json(self.out / "provenance.json")
        self.assertEqual(provenance["narrative_method"], "full_transcript_v2")
        raw = self.dest / provenance["response_cache"]
        self.assertEqual(raw.stem, provenance["request_sha256"])
        self.assertEqual(cli.digest(raw), provenance["response_sha256"])

    def test_unknown_or_malformed_citations_fail_without_retries(self):
        question = {"source_ids": ["c0000:s0001"], "topic": "Unclear", "question": "Campaign related?"}
        for text in ("Invented [c9999:s9999]",
                     "Partial [c0000:s0000] [1-8]", "Bare c0000:s0000", "No references"):
            self.revise_prompt(text)
            with self.subTest(text=text), patch.object(cli, "api", side_effect=summary_reply(text, [question])) as api:
                with self.assertRaises(ValueError):
                    self.run_summary()
                self.assertEqual(api.call_count, 1)
                self.assertFalse((self.out / "recap.draft.md").exists())

    def test_review_question_can_share_a_source_with_a_settled_event(self):
        question = {"source_ids": ["c0000:s0000"], "topic": "Identity",
                    "question": "Who is the person mentioned in this passage?"}
        with patch.object(cli, "api", side_effect=summary_reply(STORY, [question])) as api:
            self.run_summary()
            self.run_summary()
        self.assertEqual(api.call_count, 1)
        draft = (self.out / "recap.draft.md").read_text()
        self.assertIn("Azlor opened the gate. [^current-1]", draft)
        self.assertIn("[^current-1]: [c0000:s0000]", draft)
        report = cli.read_json(self.out / "manual-check.draft.json")
        self.assertEqual(report["checks"][0]["recap_source_ids"], ["c0000:s0000"])
        self.assertIn("Also cited in recap", (self.out / "manual-check.draft.md").read_text())
        self.assertIn("uncertain detail was omitted", (self.out / "manual-check.draft.md").read_text())

    def test_evidence_footnotes_preserve_paragraph_sources_and_prior_scope(self):
        story = ("# Session recap\n\n## Previously\n\n"
                 "Old event. [Session 1: c0000:s0000](../prior/recap.reviewed.md)\n\n"
                 "## The tale\n\nFirst event. [c0000:s0000] [c0001:s0009]\n\n"
                 "Second event. [c0002:s0004]")
        rendered = recap.evidence_footnotes(story)
        body, evidence = rendered.split("## Evidence")
        self.assertEqual(recap.citations(body), set())
        self.assertEqual(recap.citations(evidence), recap.citations(story))
        self.assertIn("First event. [^current-1]", body)
        self.assertIn("Second event. [^current-2]", body)
        self.assertIn("[^current-1]: [c0000:s0000] [c0001:s0009]", evidence)
        self.assertIn("[^current-2]: [c0002:s0004]", evidence)
        self.assertIn("[Session 1: c0000:s0000](../prior/recap.reviewed.md)", body)
        self.assertEqual(recap.evidence_footnotes("No established events."), "No established events.")

    def test_completed_single_block_with_many_sources_and_questions_is_reviewable(self):
        segments = [{"id": f"c0000:s{i:04d}"} for i in range(4623)]
        # Shape of the real response: one block, a broad source inventory and one
        # source shared with a question. No size gate or invented replacement IDs.
        numbers = list(range(1, 4624, 20)) + [530, 530]
        data = {"recap_blocks": [{"markdown": "A settled event.\n\nA later scene.", "sources": numbers}],
                "previously_blocks": [], "manual_checks": [
                    {"sources": [511, 530, 988, 1084], "topic": "Identity", "question": "Who is this?"}]}
        story, _, checks = recap.parse(json.dumps(data), segments, "")
        self.assertEqual(recap.citations(story), {segments[i - 1]["id"] for i in numbers})
        self.assertEqual(checks[0]["recap_source_ids"], ["c0000:s0529"])
        self.assertIn("A settled event.\n\nA later scene.", story)

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
        draft = (self.out / "recap.draft.md").read_text()
        self.assertIn(long.replace("[c0000:s0000]", "[^current-1]"), draft)
        self.assertIn("[^current-1]: [c0000:s0000]", draft)

    def test_compact_input_preserves_words_and_speaker_changes_without_repeated_headers(self):
        segments = [{"id": "c0000:s0000", "start": 10, "end": 19, "speaker": "unknown",
                     "text": "I offer peace. No, the gate stays shut.", "speaker_spans": [
                         {"speaker": "session:0", "speaker_name": "Player A", "text": "I offer"},
                         {"speaker": "session:0", "speaker_name": "Player A", "text": "peace."},
                         {"speaker": "session:1", "text": "No, the gate stays shut."}]}]
        original = json.dumps(segments)
        self.assertEqual(recap.transcript_input(segments),
                         "[c0000:s0000] session:0 (Player A): I offer peace.\n"
                         "session:1: No, the gate stays shut.\n")
        self.assertEqual(json.dumps(segments), original)
        self.assertEqual(recap.transcript_input([]), "")

    def test_corrected_text_overrides_stale_spans_and_invalidates_summary_cache(self):
        path = self.dest / "transcripts/cuda-diarized/transcript.json"
        self.segments[0]["speaker_spans"] = [dict(self.segments[0], speaker_name="Unreviewed identity")]
        cli.save_json(path, {"segments": self.segments})
        with patch.object(cli, "api", side_effect=summary_reply(STORY)) as api:
            self.run_summary()
            self.segments[0]["text"] = "Azlor did not open the gate."
            cli.save_json(path, {"segments": self.segments})
            self.run_summary()
            self.assertEqual(api.call_count, 2)
            supplied = json.loads(api.call_args.args[1])["input"]
        self.assertIn("Azlor did not open the gate.", supplied)
        self.assertNotIn("Azlor opened the gate.", supplied)
        self.assertNotIn("Unreviewed identity", supplied)
        self.assertIn("speaker attribution unavailable", supplied)
        self.assertEqual(cli.read_json(path)["segments"], self.segments)

    def test_transcript_timing_change_invalidates_cache_and_updates_review_timestamps(self):
        question = {"source_ids": ["c0000:s0001"], "topic": "Unclear", "question": "Campaign related?"}
        with patch.object(cli, "api", side_effect=summary_reply(STORY, [question])) as api:
            self.run_summary()
            self.segments[1].update(start=25, end=28)
            cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json", {"segments": self.segments})
            self.run_summary()
        self.assertEqual(api.call_count, 2)
        report = (self.out / "manual-check.draft.md").read_text()
        self.assertIn("25.00-28.00s", report)
        self.assertNotIn("20.00-24.00s", report)

    def test_source_numbers_use_exact_ids_even_with_gaps_and_different_chunks(self):
        segments = [{"id": "c0003:s0025"}, {"id": "c0012:s0008"}]
        data = {"recap_blocks": [{"markdown": "A supported outcome.", "sources": [2]}],
                "previously_blocks": [], "manual_checks": [
                    {"sources": [1], "topic": "Unclear", "question": "Campaign related?"}]}
        story, _, questions = recap.parse(json.dumps(data), segments, "")
        self.assertEqual(story, "A supported outcome. [c0012:s0008]")
        self.assertEqual(questions[0]["source_ids"], ["c0003:s0025"])
        for invalid in (0, 3, -1, True, "2", 1.5):
            data["recap_blocks"][0]["sources"] = [invalid]
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "Invalid source reference in recap block 1"):
                recap.parse(json.dumps(data), segments, "")

    def test_schema_bounds_references_and_disables_unavailable_previous_opening(self):
        schema = recap.response_format(4623, 0)["schema"]["properties"]
        for sources in (schema["recap_blocks"]["items"]["properties"]["sources"],
                        schema["manual_checks"]["items"]["properties"]["sources"]):
            self.assertEqual(sources["items"], {"type": "integer", "minimum": 1, "maximum": 4623})
        self.assertEqual(schema["previously_blocks"]["maxItems"], 0)
        self.assertEqual(schema["recap_blocks"]["items"]["properties"]["markdown"], {"type": "string"})

    def test_mapping_changes_invalidate_cache_and_prior_numbers_are_separate(self):
        first = recap.number_sources("Event [c0000:s0000]", ["c0000:s0000"])
        second = recap.number_sources("Event [c0008:s0042]", ["c0008:s0042"])
        self.assertIn("[1|", first)
        self.assertIn("[1|", second)
        self.assertNotEqual(cli.generation_request("Write", first, "fixture", self.out)[1],
                            cli.generation_request("Write", second, "fixture", self.out)[1])
        data = {"recap_blocks": [{"markdown": "Current event.", "sources": [1]}],
                "previously_blocks": [{"markdown": "Prior event.", "sources": [1]}],
                "manual_checks": []}
        story, previous, _ = recap.parse(json.dumps(data), [{"id": "c0008:s0042"}], "Prior [c0000:s0000]")
        self.assertIn("[c0008:s0042]", story)
        self.assertIn("[c0000:s0000]", previous)

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
