import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import campaign, cli, narrative, relevance
from summary_fixtures import response


ROOT = Path(__file__).resolve().parents[1]


class CampaignTests(unittest.TestCase):
    def test_short_story_and_missing_middle_fail_even_with_valid_citations(self):
        windows = [{"source_ids": [f"c{i:04d}:s0000"]} for i in range(9)]
        short = "## The tale\n\nA short plot inventory. [c0000:s0000]"
        self.assertIn("600", narrative.story_problem(short, windows, True))
        long = "## The tale\n\n" + ("The party explored the ruin. " * 125) + "[c0000:s0000] [c0008:s0000]"
        self.assertIn("middle", narrative.story_problem(long, windows, True))
        self.assertIsNone(narrative.story_problem(long + " [c0004:s0000]", windows, True))

    def test_name_reference_has_spellings_without_later_history_or_identity_reveals(self):
        early = campaign.name_reference(ROOT, {"session_number": 1})
        for name in ("Azlor", "Balder Enginnson", "Orlen Vex", "Cricket", "Crick"):
            self.assertIn(name, early)
        for name in ("Jack", "Yilthowral", "Thaddeus", "Esmeraldor", "cauldron", "dragon"):
            self.assertNotIn(name, early)
        self.assertNotIn("Sefik Kaltro /", campaign.name_reference(ROOT, {"session_number": 3}))
        self.assertEqual(campaign.name_reference(ROOT, {}), "")

    def test_name_suggestions_do_not_change_transcript_or_approve_identity(self):
        segments = [{"id": "c0000:s0001", "text": "Aslor spoke to Azlor and Crick."}]
        original = json.dumps(segments)
        checks = campaign.name_checks("Azlor; Crick; Cricket", segments)
        self.assertEqual(checks, [{"heard": "Aslor", "candidates": ["Azlor"],
                                  "source_ids": ["c0000:s0001"],
                                  "status": "unreviewed_spelling_suggestion"}])
        self.assertEqual(json.dumps(segments), original)

    def test_previous_context_selects_only_immediate_reviewed_session_and_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "sessions/current"
            for number in (1, 2, 4):
                dest = root / f"sessions/s{number}"
                cli.save_json(dest / "session.json", {"campaign": "test", "session_number": number})
                cli.write(dest / "summaries/cuda-diarized/recap.draft.md", "DRAFT_SENTINEL")
                cli.write(dest / "summaries/cuda-diarized/recap.reviewed.md", f"Reviewed {number}")
            self.assertEqual(campaign.previous_recap(root, current, {"campaign": "test", "session_number": 1}, "cuda-diarized"), ("", None))
            text, path = campaign.previous_recap(root, current, {"campaign": "test", "session_number": 3}, "cuda-diarized")
            self.assertEqual(text, "Reviewed 2")
            self.assertIn("s2/", path)
            (root / path).unlink()
            self.assertEqual(campaign.previous_recap(root, current, {"campaign": "test", "session_number": 3}, "cuda-diarized"), ("", None))

    def test_chronological_windows_read_original_middle_and_end_without_repeated_reduction(self):
        segments = [{"id": f"c{i:04d}:s0000", "start": i * 100, "end": i * 100 + 10,
                     "speaker": "unknown", "text": label + " " + "x" * 12000}
                    for i, label in enumerate(("BEGINNING", "MIDDLE", "ENDING"))]
        allowed = {s["id"] for s in segments}
        scene_inputs = []
        def reply(endpoint, body):
            data = json.loads(body)
            if "Chronological scene evidence v2" in data["instructions"]:
                scene_inputs.append(data["input"])
                label = next(label for label in ("BEGINNING", "MIDDLE", "ENDING") if label in data["input"])
                return response(json.dumps({"blocks": [{"markdown": label + " outcome", "evidence": [1]}]}))
            self.assertIn("BEGINNING outcome", data["input"])
            self.assertIn("MIDDLE outcome", data["input"])
            self.assertIn("ENDING outcome", data["input"])
            return response(json.dumps({"blocks": [{"markdown": "# Session recap", "evidence": []},
                                                    {"markdown": "All three scenes.", "evidence": [1, 2, 3]}]}))
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "api", side_effect=reply) as api, contextlib.redirect_stdout(io.StringIO()):
            text, coverage = narrative.build_story("Story", list(reversed(segments)), allowed, "fixture", Path(directory))
        self.assertEqual(len(scene_inputs), 3)
        self.assertEqual(api.call_count, 4)
        self.assertEqual([w["start"] for w in coverage], [0, 100, 200])
        self.assertTrue(all(w["recap_evidence_ids"] for w in coverage))
        self.assertEqual(relevance.citations(text), allowed)

    def test_section_citation_dumps_and_leaked_ranges_are_rejected(self):
        mapping = {i: f"c0000:s{i:04d}" for i in range(1, 6)}
        for markdown, refs in (("# Session recap", [1]), ("Story", [1, 2, 3, 4]),
                               ("First paragraph.\n\nSecond paragraph.", [1]),
                               ("Claim [62,63,113–132]", [1])):
            with self.subTest(markdown=markdown):
                self.assertIsNone(relevance.render_evidence_blocks(
                    json.dumps({"blocks": [{"markdown": markdown, "evidence": refs}]}), mapping))

    def test_first_session_previously_is_rejected_instead_of_published(self):
        segment = {"id": "c0000:s0000", "start": 0, "end": 1, "speaker": "unknown", "text": "The gate opened."}
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "api", return_value=response(
                "# Session recap\n\n## Previously\n\nThe gate opened. [c0000:s0000]")), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "Previously"):
                narrative.build_story("Story", [segment], {segment["id"]}, "fixture", Path(directory))
