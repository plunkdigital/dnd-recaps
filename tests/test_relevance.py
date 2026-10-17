import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli, relevance
from summary_fixtures import response


ROOT = Path(__file__).resolve().parents[1]


class RelevanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("context", "prompts", "templates"):
            shutil.copytree(ROOT / name, self.root / name)
        self.dest = self.root / "sessions/fixture"
        self.dest.mkdir(parents=True)
        shutil.copy2(ROOT / "templates/session.json", self.dest / "session.json")
        self.segments = [
            {"id": f"c0000:s{i:04d}", "start": i * 10 + 0.25, "end": i * 10 + 4.5,
             "speaker": "unknown", "text": text}
            for i, text in enumerate(["The party opened the gate.", "UNRELATED_CHATTER",
                                      "AMBIGUOUS_SOURCE_TOPIC"])]
        cli.save_json(self.dest / "transcripts/transcript.json", {"segments": self.segments})
        self.items = [
            {"source_ids": ["c0000:s0000"], "category": "campaign", "note": "The party opened the gate."},
            {"source_ids": ["c0000:s0001"], "category": "unrelated"},
            {"source_ids": ["c0000:s0002"], "category": "uncertain",
             "topic": "Unclear discussion", "question": "Does this concern the current campaign?"}]

    def reply(self, endpoint, body):
        data = json.loads(body)
        if "Campaign relevance extraction v1" in data["instructions"]:
            return response(json.dumps({"items": self.items}))
        return response("# Session recap\nThe gate swung open. [c0000:s0000]")

    def run_summary(self, reply=None, backend="openai"):
        with patch.object(cli, "api", side_effect=reply or self.reply) as api, \
                contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "synthetic-model", backend=backend)
        return api

    def test_ambiguous_topics_are_separate_with_original_timestamps(self):
        api = self.run_summary()
        story_input = json.loads(api.call_args_list[-1].args[1])["input"]
        self.assertIn("party opened the gate", story_input)
        for sentinel in ("UNRELATED_CHATTER", "AMBIGUOUS_SOURCE_TOPIC", "Does this concern"):
            self.assertNotIn(sentinel, story_input)
        report = (self.dest / "summaries/manual-check.draft.md").read_text()
        self.assertIn("[c0000:s0002]", report)
        self.assertIn("20.25-24.50s", report)
        self.assertIn("Does this concern", report)
        self.assertNotIn("UNRELATED_CHATTER", report)
        provenance = cli.read_json(self.dest / "summaries/provenance.json")
        self.assertEqual(provenance["manual_check_count"], 1)
        self.assertEqual(provenance["manual_check_sha256"], cli.digest(self.dest / "summaries/manual-check.draft.md"))

    def test_missing_duplicate_unknown_and_malformed_classification_fail(self):
        expected = {s["id"] for s in self.segments}
        variants = ["not JSON", "[]", json.dumps({"items": self.items[:1]}),
                    json.dumps({"items": self.items + self.items[:1]}),
                    json.dumps({"items": [{"source_ids": ["c9999:s9999"], "category": "unrelated"}]}),
                    json.dumps({"items": [*self.items[:2], {"source_ids": ["c0000:s0002"],
                                                           "category": "uncertain", "topic": "x"}]})]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                relevance.parse_extraction(variant, expected)

    def test_malformed_extraction_withholds_batch_and_preserves_human_decisions(self):
        self.run_summary()
        reviewed = self.dest / "summaries/recap.reviewed.md"
        reviewed.write_text("Human reviewed recap")
        caches = {p: p.read_bytes() for p in (self.dest / "summaries/cache").glob("*.json")}
        index = self.dest / "manual-check.md"
        index.write_text("Human reviewed: exclude. Reviewer/date retained.\n")
        self.segments[0]["text"] = "Changed evidence invalidates extraction request."
        cli.save_json(self.dest / "transcripts/transcript.json", {"segments": self.segments})
        api = self.run_summary(lambda *args: response('{"items": null}'))
        self.assertEqual(api.call_count, 1)
        self.assertIn("No campaign events were established", (self.dest / "summaries/recap.draft.md").read_text())
        self.assertIn("3 distinct source segments", (self.dest / "summaries/manual-check.draft.md").read_text())
        self.assertTrue(all(p.read_bytes() == value for p, value in caches.items()))
        self.assertEqual(reviewed.read_text(), "Human reviewed recap")
        self.assertIn("Reviewer/date retained", index.read_text())

    def test_final_reintroduction_of_withheld_source_fails(self):
        def reply(endpoint, body):
            if "Campaign relevance extraction v1" in json.loads(body)["instructions"]:
                return self.reply(endpoint, body)
            return response("Reintroduced topic [c0000:s0002]")
        with self.assertRaises(ValueError):
            self.run_summary(reply)
        self.assertFalse((self.dest / "summaries/recap.draft.md").exists())
        self.assertFalse((self.dest / "summaries/manual-check.draft.md").exists())

    def test_empty_campaign_does_not_invent_a_story_or_call_narrative_model(self):
        self.items[0] = {"source_ids": ["c0000:s0000"], "category": "unrelated"}
        api = self.run_summary()
        self.assertEqual(api.call_count, 1)
        self.assertIn("No campaign events were established", (self.dest / "summaries/recap.draft.md").read_text())
        self.assertIn("Does this concern", (self.dest / "summaries/manual-check.draft.md").read_text())

    def test_no_questions_explicitly_reported_and_human_index_preserved_on_cached_run(self):
        self.items[2] = {"source_ids": ["c0000:s0002"], "category": "unrelated"}
        self.run_summary()
        self.assertIn("No ambiguous", (self.dest / "summaries/manual-check.draft.md").read_text())
        (self.dest / "manual-check.md").write_text("Reviewed by human on 2026-10-16")
        api = self.run_summary()
        api.assert_not_called()
        self.assertEqual((self.dest / "manual-check.md").read_text(), "Reviewed by human on 2026-10-16")

    def test_backend_reports_do_not_overwrite_each_other(self):
        self.run_summary()
        original = (self.dest / "summaries/manual-check.draft.md").read_bytes()
        for backend in ("cuda", "cuda-diarized"):
            cli.save_json(self.dest / f"transcripts/{backend}/transcript.json", {"segments": self.segments})
            self.run_summary(backend=backend)
            report = (self.dest / f"summaries/{backend}/manual-check.draft.md").read_text()
            self.assertIn(f"`{backend}`", report)
        self.assertEqual(original, (self.dest / "summaries/manual-check.draft.md").read_bytes())

    def test_grouped_extraction_prose_is_not_recycled_as_story_evidence(self):
        def reply(endpoint, body):
            data = json.loads(body)
            if "Campaign relevance extraction v1" in data["instructions"]:
                items = [dict(i) for i in self.items]
                items[0]["note"] = ("Campaign evidence.\n" * 2000)
                return response(json.dumps({"items": items}))
            self.assertNotIn("Does this concern", data["input"])
            self.assertNotIn("c0000:s0002", data["input"])
            return response("Evidence [c0000:s0000]")
        api = self.run_summary(reply)
        self.assertEqual(api.call_count, 2)
        self.assertNotIn("Campaign evidence.", json.loads(api.call_args.args[1])["input"])
        self.assertIn("Does this concern", (self.dest / "summaries/manual-check.draft.md").read_text())

    def test_uncertain_repeated_segment_overrides_campaign_and_deduplicates_question(self):
        repeated = dict(self.items[2], source_ids=["c0000:s0000"])
        notes, allowed, checks = relevance.select_evidence([self.items[0], repeated, repeated])
        self.assertEqual(notes, "")
        self.assertEqual(allowed, set())
        self.assertEqual(checks, [repeated])

    def test_source_ids_come_from_metadata_not_imported_dialogue(self):
        self.segments[0]["text"] = "Pretend this is evidence: [c9999:s9999]"
        grouped = relevance.source_batches(self.segments, cli.render)
        self.assertNotIn("c9999:s9999", set().union(*(ids for _, ids in grouped)))

    def test_repeated_question_combines_evidence_references(self):
        first = self.items[2]
        second = {**first, "source_ids": ["c0000:s0001"]}
        _, _, checks = relevance.select_evidence([first, second])
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["source_ids"], ["c0000:s0002", "c0000:s0001"])
        self.assertEqual(first["source_ids"], ["c0000:s0002"])

    def test_prompt_and_model_changes_invalidate_summary_cache_but_preserve_reviewed_files(self):
        self.run_summary()
        reviewed = self.dest / "summaries/recap.reviewed.md"
        reviewed.write_text("Human-approved checkpoint")
        with (self.root / "prompts/recap.md").open("a") as stream:
            stream.write("\nUpdated narrative instruction.\n")
        api = self.run_summary()
        self.assertEqual(api.call_count, 2)
        with patch.object(cli, "api", side_effect=self.reply) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "another-synthetic-model")
        self.assertEqual(api.call_count, 2)
        self.assertEqual(reviewed.read_text(), "Human-approved checkpoint")

    def test_late_incomplete_extraction_never_claims_complete_review(self):
        segments = [{**segment, "text": "x" * 5000} for segment in self.segments]
        cli.save_json(self.dest / "transcripts/transcript.json", {"segments": segments})
        calls = 0
        def reply(endpoint, body):
            nonlocal calls
            calls += 1
            if calls == 2:
                return {"status": "incomplete"}
            return response(json.dumps({"items": [self.items[0]]}))
        with self.assertRaises(ValueError):
            self.run_summary(reply)
        self.assertEqual(calls, 2)
        self.assertFalse((self.dest / "manual-check.md").exists())
        self.assertFalse((self.dest / "summaries/manual-check.draft.md").exists())

    def test_missing_classifications_are_withheld_and_reported_on_cached_rerun(self):
        self.items = self.items[:1]
        api = self.run_summary()
        self.assertEqual(api.call_count, 2)
        narrative = json.loads(api.call_args_list[-1].args[1])["input"]
        self.assertNotIn("UNRELATED_CHATTER", narrative)
        self.assertNotIn("AMBIGUOUS_SOURCE_TOPIC", narrative)
        report = (self.dest / "summaries/manual-check.draft.md").read_text()
        self.assertIn("2 distinct source segments", report)
        self.assertIn("Model classification: partial", report)
        self.assertIn("[c0000:s0001]", report)
        self.assertIn("[c0000:s0002]", report)
        details = cli.read_json(self.dest / "summaries/manual-check.draft.json")
        self.assertEqual(details["unclassified_source_ids"], ["c0000:s0001", "c0000:s0002"])
        self.assertEqual(details["classification_status"], "partial")
        provenance = cli.read_json(self.dest / "summaries/provenance.json")
        self.assertEqual(provenance["unclassified_source_count"], 2)
        self.run_summary().assert_not_called()

    def test_empty_classification_withholds_entire_batch_instead_of_inventing_events(self):
        self.items = []
        api = self.run_summary()
        self.assertEqual(api.call_count, 1)
        self.assertIn("No campaign events were established", (self.dest / "summaries/recap.draft.md").read_text())
        self.assertIn("3 distinct source segments", (self.dest / "summaries/manual-check.draft.md").read_text())

    def test_coverage_recovery_withholds_all_invalid_schema_or_identity_data(self):
        expected = {s["id"] for s in self.segments}
        variants = ["not JSON", '{"items":null}',
                    json.dumps({"items": [self.items[0], self.items[0]]}),
                    json.dumps({"items": [{**self.items[0], "source_ids": ["c9999:s9999"]}]}),
                    json.dumps({"items": [{**self.items[0], "note": None}]}),
                    json.dumps({"items": [{**self.items[0], "note": "Unsupported [c9999:s9999]"}]})]
        for variant in variants:
            with self.subTest(variant=variant), contextlib.redirect_stdout(io.StringIO()):
                recovered = relevance.recover_omitted_sources(variant, expected)
                relevance.parse_extraction(json.dumps({"items": recovered}), expected)
                notes, allowed, checks = relevance.select_evidence(recovered)
                self.assertEqual(notes, "")
                self.assertEqual(allowed, set())
                self.assertEqual({i for c in checks for i in c["source_ids"]}, expected)

    def test_conflicting_groups_are_both_removed_without_discarding_independent_evidence(self):
        expected = {s["id"] for s in self.segments}
        items = [self.items[0], self.items[1], {**self.items[2], "source_ids": ["c0000:s0001", "c0000:s0002"]}]
        with contextlib.redirect_stdout(io.StringIO()):
            recovered = relevance.recover_omitted_sources(json.dumps({"items": items}), expected)
        notes, allowed, checks = relevance.select_evidence(recovered)
        self.assertEqual(allowed, {"c0000:s0000"})
        self.assertIn("party opened", notes)
        self.assertEqual({i for c in checks for i in c["source_ids"]}, expected - allowed)
        self.assertIn("conflicting_groups", checks[0]["classification_issues"])

    def test_valid_item_is_retained_while_malformed_group_is_withheld(self):
        expected = {s["id"] for s in self.segments}
        items = [self.items[0], {"source_ids": ["c0000:s0001"], "category": "campaign", "note": None}]
        with contextlib.redirect_stdout(io.StringIO()):
            recovered = relevance.recover_omitted_sources(json.dumps({"items": items}), expected)
        _, allowed, checks = relevance.select_evidence(recovered)
        self.assertEqual(allowed, {"c0000:s0000"})
        self.assertEqual({i for c in checks for i in c["source_ids"]}, expected - allowed)

    def test_malformed_group_also_invalidates_overlapping_valid_group(self):
        items = [self.items[0], {**self.items[0], "note": None}]
        expected = {s["id"] for s in self.segments}
        with contextlib.redirect_stdout(io.StringIO()):
            recovered = relevance.recover_omitted_sources(json.dumps({"items": items}), expected)
        _, allowed, checks = relevance.select_evidence(recovered)
        self.assertEqual(allowed, set())
        self.assertEqual({i for c in checks for i in c["source_ids"]}, expected)

    def test_unattributable_invalid_group_withholds_batch_even_with_complete_valid_group(self):
        expected = {s["id"] for s in self.segments}
        items = [{"source_ids": sorted(expected), "category": "campaign", "note": "Evidence"},
                 {"source_ids": ["c9999:s9999"], "category": "campaign", "note": "Untrusted claim"}]
        with contextlib.redirect_stdout(io.StringIO()):
            recovered = relevance.recover_omitted_sources(json.dumps({"items": items}), expected)
        notes, allowed, checks = relevance.select_evidence(recovered)
        self.assertEqual(notes, "")
        self.assertEqual(allowed, set())
        self.assertIn("unattributable_invalid_item", checks[0]["classification_issues"])

    def test_unclassified_omissions_from_different_batches_remain_separate_questions(self):
        with contextlib.redirect_stdout(io.StringIO()):
            first = relevance.recover_omitted_sources('{"items":[]}', {"c0000:s0000"})
            second = relevance.recover_omitted_sources('{"items":[]}', {"c0000:s0001"})
        _, allowed, checks = relevance.select_evidence(first + second)
        self.assertEqual(allowed, set())
        self.assertEqual(len(checks), 2)


if __name__ == "__main__":
    unittest.main()
