import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BatchScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        for name in ("generate_recaps_gpu.sh", "generate_recaps_remaining_gpu.sh"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        (self.root / "scripts/gpu_python.sh").write_text('''#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$BATCH_CALLS"
if [[ "${3:-}" == "${FAIL_STAGE:-unused}" && "${4:-}" == "${FAIL_SESSION:-}" ]]; then
  exit 7
fi
''')
        self.calls = self.root / "calls.txt"

    def run_batch(self, script="generate_recaps_remaining_gpu.sh", args=("--allow-cloud",), **settings):
        return subprocess.run(["bash", str(self.root / "scripts" / script), *args], cwd="/tmp",
                              env={"PATH": os.defpath, "BATCH_CALLS": str(self.calls), **settings},
                              text=True, capture_output=True, timeout=10)

    def test_remaining_sessions_in_order_with_cloud_flag_and_private_logs(self):
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        calls = self.calls.read_text().splitlines()
        self.assertEqual(calls[:2], ["-m dnd_recaps gpu-check", "-m dnd_recaps diarization-check"])
        self.assertEqual(len(calls), 17)
        self.assertFalse(any("session-001" in line for line in calls))
        for index, number in enumerate(range(2, 7)):
            stages = calls[2 + index * 3:5 + index * 3]
            self.assertTrue(stages[0].startswith(f"-m dnd_recaps transcribe session-{number:03d}"))
            self.assertIn("--backend cuda", stages[0])
            self.assertIn("diarize", stages[1])
            self.assertIn("--transcript-backend cuda-diarized --allow-cloud", stages[2])
        run = next((self.root / "recordings/catalog/batch-runs").iterdir())
        self.assertIn("Selected sessions completed", (run / "run.log").read_text())
        self.assertEqual(len((run / "status.tsv").read_text().splitlines()), 16)

    def test_overnight_continues_after_failure_skips_later_stages_and_returns_failure(self):
        result = self.run_batch(FAIL_STAGE="diarize", FAIL_SESSION="session-003-dark-cauldron")
        self.assertEqual(result.returncode, 1)
        calls = self.calls.read_text()
        self.assertNotIn("summarize session-003", calls)
        self.assertIn("summarize session-006", calls)
        self.assertIn("Failed sessions: session-003-dark-cauldron", result.stdout)
        status = next((self.root / "recordings/catalog/batch-runs").glob("*/status.tsv")).read_text()
        self.assertIn("session-003-dark-cauldron\tdiarize\t7", status)

    def test_original_batch_default_still_stops_on_failure(self):
        result = self.run_batch(script="generate_recaps_gpu.sh", FAIL_STAGE="diarize",
                                FAIL_SESSION="session-003-dark-cauldron")
        self.assertEqual(result.returncode, 1)
        calls = self.calls.read_text()
        self.assertIn("transcribe session-001", calls)
        self.assertNotIn("session-004", calls)

    def test_invalid_or_unapproved_arguments_never_start_stages(self):
        for script, args in (("generate_recaps_remaining_gpu.sh", ()),
                             ("generate_recaps_remaining_gpu.sh", ("--allow-cloud", "extra")),
                             ("generate_recaps_gpu.sh", ("--from-session", "2")),
                             ("generate_recaps_gpu.sh", ("--allow-cloud", "--from-session")),
                             ("generate_recaps_gpu.sh", ("--allow-cloud", "--from-session", "7")),
                             ("generate_recaps_gpu.sh", ("--allow-cloud", "--from-session", "0"))):
            with self.subTest(script=script, args=args):
                self.assertEqual(self.run_batch(script=script, args=args).returncode, 2)
                self.assertFalse(self.calls.exists())

    def test_failed_preflight_stops_even_with_continue_enabled(self):
        result = self.run_batch(FAIL_STAGE="gpu-check")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.calls.read_text().splitlines(), ["-m dnd_recaps gpu-check"])


if __name__ == "__main__":
    unittest.main()
