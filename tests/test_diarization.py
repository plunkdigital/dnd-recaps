import contextlib
import copy
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dnd_recaps import cli, diarization


class AlignmentTests(unittest.TestCase):
    def test_speaker_coverage_gaps_overlap_and_boundaries(self):
        index = diarization.TurnIndex([
            {"start": 0, "end": 2, "speaker": "A"},
            {"start": 2, "end": 4, "speaker": "B"},
            {"start": 3, "end": 4, "speaker": "A"}])
        self.assertEqual(index.attribute(0, 1)[0], "session:A")
        self.assertEqual(index.attribute(2, 3)[0], "session:B")
        self.assertEqual(index.attribute(1, 3)[0], "session:unknown")
        self.assertEqual(index.attribute(3, 4)[0], "session:unknown")
        self.assertEqual(index.attribute(4, 5)[0], "session:unknown")
        self.assertEqual(index.attribute(1, 1)[0], "session:unknown")

    def test_overlapping_same_label_is_not_counted_twice(self):
        index = diarization.TurnIndex([{"start": 0, "end": 2, "speaker": "A"},
                                      {"start": 1, "end": 3, "speaker": "A"}])
        label, candidates = index.attribute(0, 4)
        self.assertEqual(label, "session:unknown")  # Only 75 percent covered, not 100.
        self.assertEqual(candidates[0]["overlap_seconds"], 3)

    def test_word_turns_preserve_text_ids_and_source(self):
        source = {"segments": [{"id": "c0000:s0000", "start": 0, "end": 4,
                  "speaker": "c0000:unknown", "text": "Hello there.", "words": [
                      {"start": 0, "end": 1, "word": "Hello"},
                      {"start": 2, "end": 3, "word": " there."}]}]}
        before = copy.deepcopy(source)
        result = diarization.align_transcript(source, [{"start": 0, "end": 2, "speaker": "A"},
                                                       {"start": 2, "end": 4, "speaker": "B"}])
        self.assertEqual(source, before)
        segment = result["segments"][0]
        self.assertEqual(segment["id"], "c0000:s0000")
        self.assertEqual(segment["text"], "Hello there.")
        self.assertEqual("".join(span["text"] for span in segment["speaker_spans"]), segment["text"])
        self.assertEqual([s["speaker"] for s in segment["speaker_spans"]], ["session:A", "session:B"])
        rendered = cli.render(result["segments"])
        self.assertEqual(rendered.count("[c0000:s0000]"), 2)
        self.assertIn("session:A: Hello", rendered)
        self.assertIn("session:B: there.", rendered)

    def test_mismatched_legacy_words_do_not_drop_text_or_invent_speakers(self):
        transcript = {"segments": [{"id": "c0000:s0000", "start": 0, "end": 2,
                      "speaker": "unknown", "text": "Keep every word.",
                      "words": [{"start": 0, "end": 1, "word": "incomplete"}]}]}
        result = diarization.align_transcript(transcript, [
            {"start": 0, "end": 1, "speaker": "A"}, {"start": 1, "end": 2, "speaker": "B"}])
        self.assertNotIn("speaker_spans", result["segments"][0])
        self.assertEqual(result["segments"][0]["speaker"], "session:unknown")
        self.assertIn("Keep every word.", cli.render(result["segments"]))

    def test_bad_turns_are_rejected(self):
        for start, end in ((-1, 2), (2, 1), (0, float("nan"))):
            with self.subTest(start=start), self.assertRaises(ValueError):
                diarization.TurnIndex([{"start": start, "end": end, "speaker": "A"}])


class LocalPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root / "sessions/fixture"
        source = self.dest / "audio/original.wav"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"synthetic audio source")
        cli.save_json(self.dest / "manifest.json", {"source": {
            "path": "audio/original.wav", "sha256": cli.digest(source)}})
        self.transcript = {"segments": [{"id": "c0000:s0000", "start": 0, "end": 2,
                                        "speaker": "unknown", "text": "Hello."}]}
        cli.save_json(self.dest / "transcripts/cuda/transcript.json", self.transcript)

    def test_torch_gpu_is_required(self):
        fake = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict(sys.modules, {"torch": fake}), self.assertRaises(ValueError):
            diarization.torch_cuda()

    def test_no_token_stops_before_model_or_gpu_initialization(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(diarization, "torch_cuda") as check:
            with self.assertRaises(ValueError):
                diarization.create_pipeline(self.root)
            check.assert_not_called()

    def test_pipeline_uses_cuda_and_sanitizes_provider_errors(self):
        factory = Mock()
        factory.from_pretrained.return_value.device.type = "cuda"
        torch = SimpleNamespace(device=lambda name: name)
        fake_module = SimpleNamespace(Pipeline=factory)
        with patch.dict(os.environ, {"HF_TOKEN": "synthetic-token"}, clear=True), \
                patch.object(diarization, "torch_cuda", return_value=torch), \
                patch.dict(sys.modules, {"pyannote.audio": fake_module}), contextlib.redirect_stdout(io.StringIO()):
            pipeline = diarization.create_pipeline(self.root)
            pipeline.to.assert_called_once_with("cuda:0")
            self.assertEqual(os.environ["PYANNOTE_METRICS_ENABLED"], "0")
            factory.from_pretrained.side_effect = ValueError("sensitive-provider-details")
            with self.assertRaises(ValueError) as error:
                diarization.create_pipeline(self.root)
            self.assertNotIn("sensitive-provider-details", str(error.exception))
            self.assertNotIn("synthetic-token", str(error.exception))

    def test_cached_turns_survive_asr_corrections_without_repeating_diarization(self):
        turns = [{"start": 0, "end": 3, "speaker": "SPEAKER_00"}]
        raw = self.dest / "transcripts/cuda/transcript.json"
        original = raw.read_bytes()
        with patch.object(diarization, "version", return_value="fixture"), \
                patch.object(diarization, "create_pipeline") as create, \
                patch.object(diarization, "run_turns", return_value={"turns": turns, "embeddings": {}}) as infer, \
                contextlib.redirect_stdout(io.StringIO()):
            diarization.diarize(self.root, self.dest)
            self.assertEqual(raw.read_bytes(), original)
            self.transcript["segments"][0]["text"] = "Human corrected name."
            cli.save_json(raw, self.transcript)
            diarization.diarize(self.root, self.dest)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(infer.call_count, 1)
        result = cli.read_json(self.dest / "transcripts/cuda-diarized/transcript.json")
        self.assertEqual(result["segments"][0]["text"], "Human corrected name.")
        self.assertEqual(result["segments"][0]["speaker"], "session:SPEAKER_00")
        self.assertFalse((self.dest / "transcripts/transcript.json").exists())

    def test_failed_diarization_does_not_publish_or_cache_success(self):
        with patch.object(diarization, "version", return_value="fixture"), \
                patch.object(diarization, "create_pipeline"), \
                patch.object(diarization, "run_turns", side_effect=ValueError("failed")), \
                self.assertRaises(ValueError):
            diarization.diarize(self.root, self.dest)
        self.assertFalse((self.dest / "transcripts/cuda-diarized/transcript.json").exists())
        self.assertEqual(list((self.dest / "transcripts/cuda-diarized/turns").glob("*.json")), [])

    def test_embedding_windows_receive_preloaded_waveform_instead_of_file(self):
        waveform = object()
        reader = Mock(return_value=(waveform, 16000))
        audio_factory = Mock(return_value=reader)
        annotation = Mock()
        annotation.itertracks.return_value = [(SimpleNamespace(start=0, end=3), None, "SPEAKER_00")]
        pipeline = Mock(return_value=SimpleNamespace(speaker_diarization=annotation,
                                                    speaker_embeddings=None))
        hook = Mock()
        hook.__enter__ = Mock(return_value="synthetic-hook")
        hook.__exit__ = Mock(return_value=False)
        with patch.object(diarization.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                patch.dict(sys.modules, {
                    "pyannote.audio.core.io": SimpleNamespace(Audio=audio_factory),
                    "pyannote.audio.pipelines.utils.hook": SimpleNamespace(ProgressHook=lambda: hook)}), \
                contextlib.redirect_stdout(io.StringIO()):
            result = diarization.run_turns(pipeline, self.dest / "audio/original.wav", self.dest, 4)
        audio_factory.assert_called_once_with(sample_rate=16000, mono="downmix")
        reader.assert_called_once()
        pipeline.assert_called_once_with({"waveform": waveform, "sample_rate": 16000},
                                         hook="synthetic-hook", num_speakers=4)
        self.assertEqual(result["turns"], [{"start": 0, "end": 3, "speaker": "SPEAKER_00"}])
        self.assertEqual(result["embeddings"], {})

    def test_preload_failure_does_not_run_pipeline_or_expose_decoder_details(self):
        pipeline = Mock()
        audio_factory = Mock(return_value=Mock(side_effect=RuntimeError("private decoder detail")))
        with patch.object(diarization.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                patch.dict(sys.modules, {
                    "pyannote.audio.core.io": SimpleNamespace(Audio=audio_factory),
                    "pyannote.audio.pipelines.utils.hook": SimpleNamespace(ProgressHook=Mock())}):
            with self.assertRaises(ValueError) as error:
                diarization.run_turns(pipeline, self.dest / "audio/original.wav", self.dest)
        self.assertNotIn("private decoder detail", str(error.exception))
        pipeline.assert_not_called()

    def test_diarize_cli_loads_only_hf_setting_and_never_calls_cloud(self):
        config = self.root / "synthetic-config.env"
        config.write_text("HF_TOKEN=synthetic-only\nOPENAI_API_KEY=must-not-import\n", encoding="utf-8")
        args = ["dnd-recaps", "--root", str(self.root), "--env-file", config.name, "diarize", "fixture"]
        with patch.dict(os.environ, {}, clear=True), patch.object(cli.sys, "argv", args), \
                patch.object(diarization, "diarize") as local, patch.object(cli, "api") as api:
            cli.main()
            self.assertEqual(os.environ["HF_TOKEN"], "synthetic-only")
            self.assertNotIn("OPENAI_API_KEY", os.environ)
        local.assert_called_once_with(self.root, self.dest, None)
        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
