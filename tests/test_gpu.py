import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dnd_recaps import cli, gpu
from summary_fixtures import summary_reply


ROOT = Path(__file__).resolve().parents[1]


class GpuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root / "sessions/fixture"
        self.dest.mkdir(parents=True)
        self.chunks = []
        for i in range(2):
            path = self.dest / f"audio/c{i:04d}.mp3"
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(f"synthetic-{i}".encode())
            self.chunks.append({"id": f"c{i:04d}", "path": str(path.relative_to(self.dest)),
                                "sha256": cli.digest(path), "offset_seconds": i * 1195})
        cli.save_json(self.dest / "manifest.json", {"chunks": self.chunks})

    def segment(self, text="Mira opens the door."):
        return SimpleNamespace(start=1, end=3, text=text)

    def test_no_gpu_fails_before_model_download(self):
        ct2 = SimpleNamespace(get_cuda_device_count=lambda: 0)
        whisper = Mock()
        with patch.dict(sys.modules, {"ctranslate2": ct2, "faster_whisper": whisper}), self.assertRaises(ValueError):
            gpu.create_model("turbo", self.root / "models")
        whisper.WhisperModel.assert_not_called()

    def test_explicit_cuda_and_compute_type_and_cpu_rejection(self):
        whisper = Mock()
        whisper.WhisperModel.return_value.model.device = "cuda"
        with patch.object(gpu, "cuda_runtime", return_value={"device": "cuda:0"}), \
                patch.object(gpu, "check_decoder"), \
                patch.dict(sys.modules, {"faster_whisper": whisper}), contextlib.redirect_stdout(io.StringIO()):
            gpu.create_model("turbo", self.root / "models")
            kwargs = whisper.WhisperModel.call_args.kwargs
            self.assertEqual(kwargs["device"], "cuda")
            self.assertEqual(kwargs["compute_type"], "int8_float16")
            whisper.WhisperModel.return_value.model.device = "cpu"
            with self.assertRaises(ValueError):
                gpu.create_model("turbo", self.root / "models")

    def test_decoder_check_sanitizes_incompatible_pyav_before_model_download(self):
        decoder = Mock(side_effect=TypeError("private decoder detail"))
        whisper = Mock()
        with patch.object(gpu, "cuda_runtime", return_value={"device": "cuda:0"}), \
                patch.dict(sys.modules, {"faster_whisper": whisper,
                                        "faster_whisper.audio": SimpleNamespace(decode_audio=decoder)}):
            with self.assertRaisesRegex(ValueError, "PyAV below 19") as error:
                gpu.create_model("turbo", self.root / "models")
        self.assertNotIn("private decoder detail", str(error.exception))
        whisper.WhisperModel.assert_not_called()

    def test_backend_typeerror_does_not_save_partial_chunk_or_leak_details(self):
        def fail_after_segment():
            yield self.segment()
            raise TypeError("private backend detail")
        engine = Mock()
        engine.transcribe.return_value = (fail_after_segment(), SimpleNamespace(language="en"))
        with patch.object(gpu, "create_model", return_value=engine), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "No partial chunk saved") as error:
                gpu.transcribe(self.dest)
        self.assertNotIn("private backend detail", str(error.exception))
        self.assertFalse((self.dest / "transcripts/cuda/raw/c0000.json").exists())

    def test_local_cache_offsets_unknown_speakers_and_cloud_isolation(self):
        cloud = self.dest / "transcripts/raw/c0000.json"
        cli.write(cloud, "cloud-result-must-stay")
        engine = Mock()
        engine.transcribe.side_effect = lambda *a, **kw: (iter([self.segment()]), SimpleNamespace(language="en"))
        with patch.object(gpu, "create_model", return_value=engine) as create, \
                patch.object(cli, "api") as api, contextlib.redirect_stdout(io.StringIO()):
            gpu.transcribe(self.dest)
            gpu.transcribe(self.dest)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(engine.transcribe.call_count, 2)
        api.assert_not_called()
        self.assertEqual(cloud.read_text(), "cloud-result-must-stay")
        data = cli.read_json(self.dest / "transcripts/cuda/transcript.json")
        self.assertFalse(data["speaker_labels"])
        self.assertEqual(data["segments"][1]["start"], 1196)
        self.assertEqual(data["segments"][1]["speaker"], "c0001:unknown")
        with patch.object(gpu, "create_model") as create, self.assertRaises(ValueError):
            gpu.transcribe(self.dest, "large-v3")
        create.assert_not_called()

    def test_failed_generator_preserves_only_completed_chunks(self):
        def fail_after_segment():
            yield self.segment()
            raise RuntimeError("inference failed")
        engine = Mock()
        engine.transcribe.side_effect = [(iter([self.segment()]), SimpleNamespace(language="en")),
                                        (fail_after_segment(), SimpleNamespace(language="en"))]
        with patch.object(gpu, "create_model", return_value=engine), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                gpu.transcribe(self.dest)
        self.assertTrue((self.dest / "transcripts/cuda/raw/c0000.json").exists())
        self.assertFalse((self.dest / "transcripts/cuda/raw/c0001.json").exists())
        self.assertFalse((self.dest / "transcripts/cuda/transcript.json").exists())

    def test_word_timestamps_use_full_recording_offsets(self):
        engine = Mock()
        segment = self.segment("Hello.")
        segment.words = [SimpleNamespace(start=1, end=3, word="Hello.")]
        engine.transcribe.side_effect = lambda *a, **kw: (iter([segment]), SimpleNamespace(language="en"))
        with patch.object(gpu, "create_model", return_value=engine), contextlib.redirect_stdout(io.StringIO()):
            gpu.transcribe(self.dest)
        data = cli.read_json(self.dest / "transcripts/cuda/transcript.json")
        self.assertEqual(data["segments"][1]["words"][0]["start"], 1196)
        self.assertTrue(engine.transcribe.call_args.kwargs["word_timestamps"])

    def test_name_hints_apply_to_new_audio_but_do_not_rewrite_cached_evidence(self):
        cli.save_json(self.dest / "session.json", {"session_number": 1})
        cli.save_json(self.root / "context/campaign/names.json", {"names": [
            {"name": "Azlor", "aliases": [], "from_session": 1},
            {"name": "FutureName", "aliases": [], "from_session": 2}]})
        engine = Mock()
        engine.transcribe.side_effect = lambda *a, **kw: (iter([self.segment()]), SimpleNamespace(language="en"))
        with patch.object(gpu, "create_model", return_value=engine), contextlib.redirect_stdout(io.StringIO()):
            gpu.transcribe(self.dest)
        self.assertIn("Azlor", engine.transcribe.call_args.kwargs["hotwords"])
        self.assertNotIn("FutureName", engine.transcribe.call_args.kwargs["hotwords"])
        caches = {p: p.read_bytes() for p in (self.dest / "transcripts/cuda/raw").glob("*.json")}
        cli.save_json(self.root / "context/campaign/names.json", {"names": [
            {"name": "DifferentName", "aliases": [], "from_session": 1}]})
        with patch.object(gpu, "create_model") as create, contextlib.redirect_stdout(io.StringIO()) as log:
            gpu.transcribe(self.dest)
        create.assert_not_called()
        self.assertIn("current spelling hints were not applied", log.getvalue())
        self.assertTrue(all(p.read_bytes() == content for p, content in caches.items()))

    def test_legacy_wordless_caches_are_reused_without_inference(self):
        parameters = {"beam_size": 5, "vad_filter": True, "condition_on_previous_text": False, "task": "transcribe"}
        for chunk in self.chunks:
            cli.save_json(self.dest / f"transcripts/cuda/raw/{chunk['id']}.json", {
                "input": {"sha256": chunk["sha256"], "backend": "faster-whisper-cuda", "model": "turbo",
                          "compute_type": "int8_float16", "parameters": parameters},
                "response": {"segments": [{"start": 1, "end": 3, "speaker": "unknown", "text": "Hello."}]}})
        with patch.object(gpu, "create_model") as create, contextlib.redirect_stdout(io.StringIO()):
            gpu.transcribe(self.dest)
        create.assert_not_called()
        self.assertEqual(len(cli.read_json(self.dest / "transcripts/cuda/transcript.json")["segments"]), 2)

    def test_silent_chunk_is_recorded_without_fabricating_speech(self):
        engine = Mock()
        engine.transcribe.side_effect = [(iter([]), SimpleNamespace(language="en")),
                                        (iter([self.segment()]), SimpleNamespace(language="en"))]
        with patch.object(gpu, "create_model", return_value=engine), contextlib.redirect_stdout(io.StringIO()):
            gpu.transcribe(self.dest)
        data = cli.read_json(self.dest / "transcripts/cuda/transcript.json")
        self.assertEqual(len(data["segments"]), 1)
        self.assertTrue(cli.read_json(self.dest / "transcripts/cuda/raw/c0000.json")["response"]["no_speech"])

    def test_gpu_cli_does_not_load_secrets_or_require_cloud_flag(self):
        args = ["dnd-recaps", "--root", str(self.root), "transcribe", "fixture", "--backend", "cuda"]
        with patch.object(cli.sys, "argv", args), patch.object(gpu, "transcribe") as local, \
                patch.object(cli, "load_environment") as load, patch.object(cli, "api") as api:
            cli.main()
        local.assert_called_once_with(self.dest, "turbo")
        load.assert_not_called()
        api.assert_not_called()

    def test_cuda_summary_uses_only_selected_transcript_and_separate_output(self):
        for name in ("context", "prompts", "templates"):
            shutil.copytree(ROOT / name, self.root / name)
        shutil.copy2(ROOT / "templates/session.json", self.dest / "session.json")
        transcript = cli.read_json(ROOT / "examples/transcript.json")
        cli.save_json(self.dest / "transcripts/cuda/transcript.json", transcript)
        cli.write(self.dest / "transcripts/transcript.json", "CLOUD_INPUT_SENTINEL")
        cli.write(self.dest / "summaries/recap.draft.md", "CLOUD_RECAP_SENTINEL")
        with patch.object(cli, "api", side_effect=summary_reply("A tale [c0000:s0002]")) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "fixture-model", backend="cuda")
        self.assertNotIn("CLOUD_INPUT_SENTINEL", api.call_args.args[1].decode())
        self.assertEqual((self.dest / "summaries/recap.draft.md").read_text(), "CLOUD_RECAP_SENTINEL")
        self.assertTrue((self.dest / "summaries/cuda/recap.draft.md").exists())
        self.assertEqual(cli.read_json(self.dest / "summaries/cuda/provenance.json")["transcription_backend"], "cuda")

    def test_diarized_summary_excludes_unreviewed_proposals_and_vectors(self):
        for name in ("context", "prompts", "templates"):
            shutil.copytree(ROOT / name, self.root / name)
        shutil.copy2(ROOT / "templates/session.json", self.dest / "session.json")
        cli.save_json(self.dest / "transcripts/cuda-diarized/transcript.json",
                      cli.read_json(ROOT / "examples/transcript.json"))
        cli.write(self.dest / "transcripts/cuda-diarized/speaker-proposals.json", "UNREVIEWED_VOICE_NAME")
        cli.write(self.root / "recordings/catalog/voice-profiles.json", "PRIVATE_VECTOR_DATA")
        with patch.object(cli, "api", side_effect=summary_reply("A tale [c0000:s0002]")) as api, contextlib.redirect_stdout(io.StringIO()):
            cli.summarize(self.root, self.dest, "fixture-model", backend="cuda-diarized")
        payload = api.call_args.args[1].decode()
        self.assertNotIn("UNREVIEWED_VOICE_NAME", payload)
        self.assertNotIn("PRIVATE_VECTOR_DATA", payload)
        self.assertTrue((self.dest / "summaries/cuda-diarized/recap.draft.md").exists())


if __name__ == "__main__":
    unittest.main()
