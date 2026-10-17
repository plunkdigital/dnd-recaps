import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli
from summary_fixtures import summary_reply


ROOT = Path(__file__).resolve().parents[1]


def response(text):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("context", "prompts", "templates"):
            shutil.copytree(ROOT / name, self.root / name)
        self.dest = self.root / "sessions/test"
        self.dest.mkdir(parents=True)
        shutil.copy2(ROOT / "templates/session.json", self.dest / "session.json")

    def seed_transcript(self):
        cli.save_json(self.dest / "transcripts/transcript.json",
                      cli.read_json(ROOT / "examples/transcript.json"))

    def test_session_ids_cannot_escape(self):
        for name in ("../escape", "/tmp/x", "has space", "", "UPPER"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                cli.session_path(self.root, name)
        self.assertEqual(cli.session_path(self.root, "session-001"),
                         self.root / "sessions/session-001")

    def test_normalization_offsets_and_chunk_local_speakers(self):
        raw = {"segments": [{"start": 2, "end": 4, "speaker": "A", "text": "Hello"}]}
        segment = cli.normalize(raw, {"id": "c0001", "offset_seconds": 1195})[0]
        self.assertEqual(segment["start"], 1197)
        self.assertEqual(segment["end"], 1199)
        self.assertEqual(segment["speaker"], "c0001:A")
        self.assertEqual(segment["id"], "c0001:s0000")
        with self.assertRaises(ValueError):
            cli.normalize({"segments": []}, {"id": "c0001"})

    def test_transcription_resumes_and_detects_changed_audio(self):
        chunk = self.dest / "audio/chunks/c0000.mp3"
        chunk.parent.mkdir(parents=True)
        chunk.write_bytes(b"synthetic audio")
        cli.save_json(self.dest / "manifest.json", {"chunks": [{
            "id": "c0000", "path": "audio/chunks/c0000.mp3",
            "offset_seconds": 0, "sha256": cli.digest(chunk)}]})
        raw = {"segments": [{"start": 0, "end": 1, "speaker": "A", "text": "The gate opens."}]}
        with patch.object(cli, "api", return_value=raw) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.transcribe(self.dest)
            cli.transcribe(self.dest)
            self.assertEqual(api.call_count, 1)
            chunk.write_bytes(b"different audio")
            with self.assertRaises(ValueError):
                cli.transcribe(self.dest)
            self.assertEqual(api.call_count, 1)

    def test_summary_caches_and_never_loads_dm_secrets(self):
        self.seed_transcript()
        (self.root / "context/dm/secret.md").write_text("SECRET_SENTINEL", encoding="utf-8")
        (self.root / "context/dm/SPOILERS-rime-of-the-frostmaiden.md").write_text(
            "TRACKED_DM_REFERENCE_SENTINEL", encoding="utf-8")
        output = summary_reply("# Session recap\nMira accepted the key. [c0000:s0002]")
        with patch.object(cli, "api", side_effect=output) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "test-model")
            cli.summarize(self.root, self.dest, "test-model")
            self.assertEqual(api.call_count, 1)
            payload = json.loads(api.call_args.args[1])
            self.assertNotIn("SECRET_SENTINEL", json.dumps(payload))
            self.assertNotIn("TRACKED_DM_REFERENCE_SENTINEL", json.dumps(payload))
            self.assertFalse(payload["store"])
            (self.root / "context/campaign/state.md").write_text("Updated reviewed state", encoding="utf-8")
            cli.summarize(self.root, self.dest, "test-model")
            self.assertEqual(api.call_count, 2)
            transcript = cli.read_json(self.dest / "transcripts/transcript.json")
            transcript["segments"][0]["text"] = "Human correction"
            cli.save_json(self.dest / "transcripts/transcript.json", transcript)
            cli.summarize(self.root, self.dest, "test-model")
            self.assertEqual(api.call_count, 3)

    def test_incomplete_output_never_publishes_recap(self):
        self.seed_transcript()
        with patch.object(cli, "api", return_value={"status": "incomplete"}), self.assertRaises(ValueError):
            cli.summarize(self.root, self.dest, "test-model")
        self.assertFalse((self.dest / "summaries/recap.draft.md").exists())

    def test_early_recordings_exclude_later_historical_context(self):
        self.seed_transcript()
        metadata = cli.read_json(self.dest / "session.json")
        metadata["context_policy"] = "recording_only"
        cli.save_json(self.dest / "session.json", metadata)
        for name in ("characters.md", "glossary.md", "state.md"):
            (self.root / "context/campaign" / name).write_text("LATER_SESSION_SENTINEL", encoding="utf-8")
        output = summary_reply("The guard offered a key. [c0000:s0002]")
        with patch.object(cli, "api", side_effect=output) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "test-model")
        self.assertNotIn("LATER_SESSION_SENTINEL", api.call_args.args[1].decode())
        provenance = cli.read_json(self.dest / "summaries/provenance.json")
        self.assertEqual(provenance["context_files"], ["overview.md"])

    def test_unknown_history_policy_fails_before_cloud_processing(self):
        self.seed_transcript()
        metadata = cli.read_json(self.dest / "session.json")
        metadata["context_policy"] = "misspelled-policy"
        cli.save_json(self.dest / "session.json", metadata)
        with patch.object(cli, "api") as api, self.assertRaises(ValueError):
            cli.summarize(self.root, self.dest, "test-model")
        api.assert_not_called()

    def test_reviewed_previous_session_is_used_without_rebinding_its_citations(self):
        self.seed_transcript()
        metadata = cli.read_json(self.dest / "session.json")
        metadata.update(session_number=2, campaign="test", context_policy="recording_only")
        cli.save_json(self.dest / "session.json", metadata)
        prior = self.root / "sessions/prior"
        cli.save_json(prior / "session.json", {"session_number": 1, "campaign": "test"})
        reviewed = prior / "summaries/recap.reviewed.md"
        cli.write(reviewed, "The old bridge fell. [c0000:s0002]")
        reply = summary_reply("# Session recap\n\n## The tale\n\nThe key was accepted. [c0000:s0002]",
                              previously="The bridge had fallen. [c0000:s0002]")
        with patch.object(cli, "api", side_effect=reply), contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "fixture")
        recap = (self.dest / "summaries/recap.draft.md").read_text()
        self.assertIn("## Previously", recap)
        self.assertIn("[Session 1: c0000:s0002]", recap)
        self.assertIn("accepted. [c0000:s0002]", recap)
        provenance = cli.read_json(self.dest / "summaries/provenance.json")
        self.assertEqual(provenance["previous_reviewed_sha256"], cli.digest(reviewed))
        self.assertEqual(provenance["previous_reviewed_recap"], "sessions/prior/summaries/recap.reviewed.md")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg unavailable")
    def test_nonzero_chunk_seek_preserves_late_audio(self):
        import array
        import math
        import subprocess
        import wave
        source = self.root / "silence-then-tone.wav"
        samples = array.array("h", [0] * 16000 + [
            round(10000 * math.sin(2 * math.pi * 440 * i / 8000)) for i in range(16000)])
        if cli.sys.byteorder != "little":
            samples.byteswap()
        with wave.open(str(source), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(samples.tobytes())
        target = self.root / "late.mp3"
        cli.encode_chunk(source, target, 3)
        result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(target), "-f", "s16le",
                                 "-ac", "1", "-ar", "8000", "pipe:1"], capture_output=True, check=True)
        decoded = array.array("h")
        decoded.frombytes(result.stdout)
        if cli.sys.byteorder != "little":
            decoded.byteswap()
        self.assertAlmostEqual(len(decoded) / 8000, 1, delta=0.1)
        self.assertGreater(sum(abs(v) for v in decoded) / len(decoded), 1000)

    def test_unknown_citation_never_publishes_recap(self):
        self.seed_transcript()
        with patch.object(cli, "api", side_effect=summary_reply("Invented [c9999:s9999]")), self.assertRaises(ValueError):
            cli.summarize(self.root, self.dest, "test-model")
        self.assertFalse((self.dest / "summaries/recap.draft.md").exists())

    def test_full_transcript_including_middle_and_end_is_sent_once(self):
        segments = [{"id": f"c0000:s{i:04d}", "start": i, "end": i + 1,
                     "speaker": "unknown", "text": "x" * 1000} for i in range(100)]
        cli.save_json(self.dest / "transcripts/transcript.json", {"segments": segments})
        with patch.object(cli, "api", side_effect=summary_reply("# Session recap\nA tale [c0000:s0000]")) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "test-model")
        self.assertEqual(api.call_count, 1)
        payload = json.loads(api.call_args.args[1])
        self.assertEqual(payload["input"], cli.render(segments))
        self.assertEqual(payload["text"]["format"]["name"], "session_recap")

    def test_cloud_flag_is_required_before_api_use(self):
        with patch.object(cli.sys, "argv", ["dnd-recaps", "transcribe", "test"]), \
                patch.object(cli, "api") as api, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                cli.main()
            self.assertEqual(exc.exception.code, 1)
            api.assert_not_called()

    def test_failed_preparation_leaves_no_ready_session(self):
        audio = self.root / "source.wav"
        audio.write_bytes(b"synthetic source")
        with patch.object(cli.shutil, "which", return_value="/fake/ffmpeg"), \
                patch.object(cli, "run_media", side_effect=["1.0", ValueError("Conversion failed")]):
            with self.assertRaises(ValueError):
                cli.prepare(self.root, "failed", audio)
        self.assertFalse((self.root / "sessions/failed").exists())
        self.assertEqual(audio.read_bytes(), b"synthetic source")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg unavailable")
    def test_prepare_preserves_source_and_refuses_overwrite(self):
        import wave
        audio = self.root / "source.wav"
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\x00\x00" * 8000)
        original_hash = cli.digest(audio)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.prepare(self.root, "prepared", audio)
        manifest = cli.read_json(self.root / "sessions/prepared/manifest.json")
        self.assertEqual(manifest["source"]["sha256"], original_hash)
        self.assertEqual(cli.digest(audio), original_hash)
        self.assertEqual(len(manifest["chunks"]), 1)
        with self.assertRaises(ValueError):
            cli.prepare(self.root, "prepared", audio)


if __name__ == "__main__":
    unittest.main()
