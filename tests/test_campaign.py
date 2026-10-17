import json
from pathlib import Path
import tempfile
import unittest

from dnd_recaps import campaign, cli


ROOT = Path(__file__).resolve().parents[1]


class CampaignTests(unittest.TestCase):
    def test_name_reference_has_spellings_without_later_history_or_identity_reveals(self):
        early = campaign.name_reference(ROOT, {"session_number": 1})
        for name in ("Azlor", "Balder Enginnson", "Orlen Vex", "Cricket", "Crick"):
            self.assertIn(name, early)
        for name in ("Jack", "Yilthowral", "Thaddeus", "Esmeraldor", "cauldron", "dragon"):
            self.assertNotIn(name, early)
        self.assertNotIn("Sefik Kaltro /", campaign.name_reference(ROOT, {"session_number": 3}))
        self.assertEqual(campaign.name_reference(ROOT, {}), "")

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
