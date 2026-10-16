import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from dnd_recaps import cli, speakers, voice_matching


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.people = {"alex": {"display_name": "Alex"}, "bea": {"display_name": "Bea"}}
        self.profiles = {"alex": {"samples": [{"session_id": "old", "model_key": "model-v1",
                                               "audio_sha256": "old-audio", "embedding": [1, 0]}]},
                         "bea": {"samples": [{"session_id": "old", "model_key": "model-v1",
                                               "audio_sha256": "old-audio", "embedding": [0, 1]}]}}

    def suggest(self, vector, **kwargs):
        return voice_matching.suggest_matches({"session:SPEAKER_02": vector},
                                              {"session:SPEAKER_02": 30}, self.profiles,
                                              self.people, "new", "model-v1", **kwargs)[0]

    def test_strong_match_is_only_a_review_proposal(self):
        result = self.suggest([1, 0])
        self.assertEqual(result["status"], "proposed")
        self.assertTrue(result["review_required"])
        self.assertEqual(result["candidates"][0]["speaker_id"], "alex")
        self.assertNotIn("approved", result)

    def test_ambiguous_and_weak_matches_remain_unresolved(self):
        self.assertEqual(self.suggest([1, 1], min_cosine=0.6)["status"], "ambiguous")
        self.assertEqual(self.suggest([-1, -1])["status"], "below_threshold")

    def test_source_replays_and_incompatible_models_do_not_self_match(self):
        self.assertEqual(self.suggest([1, 0], audio_sha256="old-audio")["status"], "no_enrolled_comparison")
        for profile in self.profiles.values():
            profile["samples"][0]["model_key"] = "different-model"
        self.assertEqual(self.suggest([1, 0])["status"], "no_enrolled_comparison")

    def test_short_clusters_and_duplicate_proposals_are_flagged(self):
        result = voice_matching.suggest_matches(
            {"a": [1, 0], "b": [1, 0], "c": [0, 1]}, {"a": 30, "b": 30, "c": 1},
            self.profiles, self.people, "new", "model-v1")
        self.assertTrue(result[0]["duplicate_proposal"])
        self.assertTrue(result[1]["duplicate_proposal"])
        self.assertEqual(result[2]["status"], "insufficient_speech")


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cli.save_json(self.root / "context/speakers.json", {"schema_version": 1, "people": {}})

    def session(self, name, label):
        dest = self.root / "sessions" / name
        pointer = "transcripts/cuda-diarized/turns/fixture.json"
        cli.save_json(dest / pointer, {"input": {"model": "model", "pyannote_version": "v1",
                      "audio_sha256": name}, "turns": [{"start": 0, "end": 30, "speaker": label}],
                      "embeddings": {"session:" + label: [1, 0]}})
        cli.save_json(dest / "session.json", {"speaker_map": {}})
        data = {"diarization_cache": pointer, "detected_speakers": ["session:" + label],
                "segments": [{"id": "c0000:s0000", "start": 0, "end": 2,
                              "speaker": "session:" + label, "text": "Hello."}]}
        cli.save_json(dest / "transcripts/cuda-diarized/transcript.json", data)
        return dest, data

    def test_review_enrolls_profile_and_future_sessions_only_propose_it(self):
        first, first_data = self.session("first", "SPEAKER_00")
        with contextlib.redirect_stdout(io.StringIO()):
            speakers.map_speaker(self.root, first, "SPEAKER_00", "alex", "Alex")
        second, second_data = self.session("second", "SPEAKER_02")
        voice_matching.write_proposals(self.root, second, second_data)
        proposal = cli.read_json(second / "transcripts/cuda-diarized/speaker-proposals.json")
        self.assertEqual(proposal["proposals"][0]["status"], "proposed")
        self.assertFalse(proposal["approved"])
        unreviewed = speakers.apply_reviewed_speakers(self.root, second, second_data)
        self.assertNotIn("speaker_name", unreviewed["segments"][0])
        with contextlib.redirect_stdout(io.StringIO()):
            speakers.map_speaker(self.root, second, "SPEAKER_02", "alex")
        accepted = cli.read_json(second / "transcripts/cuda-diarized/transcript.json")
        self.assertEqual(accepted["segments"][0]["speaker_id"], "alex")
        self.assertIn("(Alex)", cli.render(accepted["segments"]))
        profiles = cli.read_json(self.root / "recordings/catalog/voice-profiles.json")
        self.assertEqual(len(profiles["profiles"]["alex"]["samples"]), 2)

    def test_reclustering_invalidates_label_mapping_and_corrections_remove_old_profile(self):
        dest, data = self.session("first", "SPEAKER_00")
        with contextlib.redirect_stdout(io.StringIO()):
            speakers.map_speaker(self.root, dest, "SPEAKER_00", "alex", "Alex")
        labelled = cli.read_json(dest / "transcripts/cuda-diarized/transcript.json")
        labelled["diarization_cache"] = "transcripts/cuda-diarized/turns/new-clusters.json"
        remapped = speakers.apply_reviewed_speakers(self.root, dest, labelled)
        self.assertNotIn("speaker_name", remapped["segments"][0])
        with contextlib.redirect_stdout(io.StringIO()):
            speakers.map_speaker(self.root, dest, "SPEAKER_00", "bea", "Bea")
        profiles = cli.read_json(self.root / "recordings/catalog/voice-profiles.json")["profiles"]
        self.assertEqual(profiles["alex"]["samples"], [])
        self.assertEqual(len(profiles["bea"]["samples"]), 1)

    def test_mapping_absent_label_cannot_enroll_an_identity(self):
        dest, _ = self.session("first", "SPEAKER_00")
        with self.assertRaises(ValueError):
            speakers.map_speaker(self.root, dest, "SPEAKER_99", "alex", "Alex")
        self.assertEqual(cli.read_json(self.root / "context/speakers.json")["people"], {})


if __name__ == "__main__":
    unittest.main()
