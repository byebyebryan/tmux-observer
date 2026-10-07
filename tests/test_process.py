"""Exercise limits against owned processes, not mocked subprocess output."""

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tmux_observer._clock import boottime_ms
from tmux_observer._process import ProcessError, ReadRunner


class ProcessTests(unittest.TestCase):
    def run_code(self, code, budget=2000):
        runner = ReadRunner((sys.executable, "-c", code))
        return runner(["display-message", "-p", "#{session_id}"], boottime_ms() + budget)

    def test_stdout_and_stderr_are_bounded(self):
        for code in ("import os; os.write(1, b'x'*1100000)", "import os; os.write(2, b'x'*70000)"):
            with self.assertRaises(ProcessError) as error:
                self.run_code(code)
            self.assertEqual(error.exception.code, "output_limit")

    def test_invalid_utf8_and_missing_executable(self):
        with self.assertRaises(ProcessError) as error:
            self.run_code("import os; os.write(1, b'\\xff')")
        self.assertEqual(error.exception.code, "malformed_metadata")
        with self.assertRaises(ProcessError) as error:
            ReadRunner(("/tmux-observer-owned-nonexistent",))(
                ["display-message", "-p", "#{session_id}"], boottime_ms() + 1000
            )
        self.assertEqual(error.exception.code, "tmux_missing")

    def test_own_descendants_holding_pipes_are_killed(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-process-") as temporary:
            marker = Path(temporary) / "pid"
            code = (
                "import os,time; pid=os.fork(); "
                + f"open({str(marker)!r},'w').write(str(pid)) if pid else time.sleep(20)"
            )
            before = time.monotonic()
            with self.assertRaises(ProcessError) as error:
                self.run_code(code, budget=300)
            self.assertEqual(error.exception.code, "deadline")
            self.assertLess(time.monotonic() - before, 2)
            pid = int(marker.read_text())
            # An adopted child may briefly remain as a zombie; it cannot run.
            status = Path(f"/proc/{pid}/stat")
            until = time.monotonic() + 0.5
            while (
                status.exists()
                and status.read_text().split()[2] != "Z"
                and time.monotonic() < until
            ):
                time.sleep(0.01)
            if status.exists():
                self.assertEqual(status.read_text().split()[2], "Z")

    def test_suspend_jump_rejects_output_before_acceptance(self):
        # Model a BOOTTIME jump while wall/monotonic poll scheduling stays short.
        with (
            patch("tmux_observer._process.boottime_ms", side_effect=[100, 100, 5000]),
            self.assertRaises(ProcessError) as error,
        ):
            ReadRunner((sys.executable, "-c", "import time; time.sleep(1)"))(
                ["display-message", "-p", "#{session_id}"], 2100
            )
        self.assertEqual(error.exception.code, "deadline")
