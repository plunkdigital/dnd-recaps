import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dnd_recaps import cli


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "synthetic-config.env"

    def test_loads_only_known_settings_without_shell_execution(self):
        marker = self.root / "must-not-exist"
        self.config.write_text(
            '# Synthetic values only\nexport OPENAI_API_KEY="fake-key" # comment\n'
            'RECAP_MODEL=fixture-model # comment\nUNRELATED=ignore-me\n', encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            cli.load_environment(self.config)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "fake-key")
            self.assertEqual(os.environ["RECAP_MODEL"], "fixture-model")
            self.assertNotIn("UNRELATED", os.environ)
        self.config.write_text(f"OPENAI_API_KEY=$(touch {marker})\n", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            cli.load_environment(self.config)
            self.assertTrue(os.environ["OPENAI_API_KEY"].startswith("$(touch"))
        self.assertFalse(marker.exists())

    def test_process_environment_wins_and_missing_file_is_optional(self):
        self.config.write_text("OPENAI_API_KEY='fake-file-key'\n", encoding="utf-8")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-process-key"}, clear=True):
            cli.load_environment(self.config)
            cli.load_environment(self.root / "absent-config.env")
            self.assertEqual(os.environ["OPENAI_API_KEY"], "fake-process-key")

    def test_invalid_configuration_never_leaks_values_or_partially_loads(self):
        self.config.write_text('RECAP_MODEL=fixture-model\nOPENAI_API_KEY="fake-sensitive-value\n', encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as error:
                cli.load_environment(self.config)
            self.assertNotIn("fake-sensitive-value", str(error.exception))
            self.assertNotIn("RECAP_MODEL", os.environ)

    def test_cloud_flag_checked_before_any_config_read(self):
        args = ["dnd-recaps", "--root", str(self.root), "transcribe", "fixture"]
        with patch.object(cli.sys, "argv", args), patch.object(cli, "load_environment") as load, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main()
            load.assert_not_called()

    def test_prepare_and_help_never_load_configuration(self):
        args = ["dnd-recaps", "--root", str(self.root), "prepare", "fixture", "fake.wav"]
        with patch.object(cli.sys, "argv", args), patch.object(cli, "prepare"), \
                patch.object(cli, "load_environment") as load:
            cli.main()
            load.assert_not_called()
        with patch.object(cli.sys, "argv", ["dnd-recaps", "--help"]), \
                patch.object(cli, "load_environment") as load, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main()
            load.assert_not_called()

    def test_cli_loads_explicit_fixture_and_model_precedence(self):
        self.config.write_text("OPENAI_API_KEY=fake-only\nRECAP_MODEL=file-model\n", encoding="utf-8")
        base = ["dnd-recaps", "--root", str(self.root), "--env-file", self.config.name,
                "summarize", "fixture", "--allow-cloud"]
        for extra, expected in (([], "file-model"), (["--model", "cli-model"], "cli-model")):
            with patch.dict(os.environ, {}, clear=True), patch.object(cli.sys, "argv", base + extra), \
                    patch.object(cli, "summarize") as summarize:
                cli.main()
                self.assertEqual(summarize.call_args.args[2], expected)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "fake-only")

    def test_safe_config_has_no_usable_key(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {}, clear=True):
            cli.load_environment(root / "config/codex-test.env")
            self.assertNotIn("OPENAI_API_KEY", os.environ)

    def test_default_recap_model_and_process_override_without_secret_configuration(self):
        self.config.write_text("OPENAI_API_KEY=fake-only\n", encoding="utf-8")
        args = ["dnd-recaps", "--root", str(self.root), "--env-file", self.config.name,
                "summarize", "fixture", "--allow-cloud"]
        for settings, expected in (({}, "gpt-6-astra"), ({"RECAP_MODEL": "process-model"}, "process-model")):
            with patch.dict(os.environ, settings, clear=True), patch.object(cli.sys, "argv", args), \
                    patch.object(cli, "summarize") as summarize:
                cli.main()
                self.assertEqual(summarize.call_args.args[2], expected)

    def test_supplied_campaign_context_fits_request_budget(self):
        root = Path(__file__).resolve().parents[1]
        names = ("overview.md", "characters.md", "glossary.md", "state.md")
        context = "\n".join((root / "context/campaign" / name).read_text(encoding="utf-8")
                            for name in names)
        metadata = (root / "templates/session.json").read_text(encoding="utf-8")
        self.assertLessEqual(len((context + metadata).encode("utf-8")), cli.MAX_SUMMARY_INPUT_BYTES)


if __name__ == "__main__":
    unittest.main()
