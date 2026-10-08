"""Safety failures in the physical acceptance harness; never invoke host power."""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

loader = importlib.machinery.SourceFileLoader(
    "suspend_acceptance", str(Path(__file__).resolve().parents[1] / "scripts/accept-native-suspend")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
harness = importlib.util.module_from_spec(spec)
loader.exec_module(harness)


class SuspendAcceptanceTests(unittest.TestCase):
    def test_sleep_block_inhibitor_refused_and_delay_metadata_kept_private(self):
        rows = [["sleep:shutdown", "private who", "private why", "block", 1000, 123]]
        with (
            patch.object(
                harness,
                "command",
                return_value=SimpleNamespace(stdout=json.dumps({"data": [rows]}).encode()),
            ),
            self.assertRaisesRegex(RuntimeError, "sleep-block"),
        ):
            harness.inhibitors()
        rows[0][3] = "delay"
        with patch.object(
            harness,
            "command",
            return_value=SimpleNamespace(stdout=json.dumps({"data": [rows]}).encode()),
        ):
            self.assertEqual(
                harness.inhibitors(), [{"what": "sleep:shutdown", "mode": "delay", "uid": 1000}]
            )

    def test_existing_rtc_alarm_refused_before_any_privileged_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            alarm = Path(temporary) / "wakealarm"
            alarm.write_text("1800000000\n")
            with patch.object(harness, "ALARM", alarm), patch.object(harness, "command") as run:
                with self.assertRaisesRegex(RuntimeError, "already armed"):
                    harness.preflight()
                run.assert_not_called()
            self.assertEqual(alarm.read_text(), "1800000000\n")

    def test_new_block_inhibitor_after_arm_cleans_owned_alarm_without_suspend(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alarm = root / "wakealarm"
            alarm.write_text("1800000000\n")
            with (
                patch.object(harness, "load", return_value=SimpleNamespace(private_root=Mock())),
                patch.object(harness, "preflight", return_value={}),
                patch.object(harness, "inhibitors", side_effect=[[], RuntimeError("sleep block")]),
                patch.object(harness, "arm_alarm", return_value="1800000000"),
                patch.object(harness, "ALARM", alarm),
                patch.object(harness.time, "sleep"),
                patch.object(harness, "command") as run,
                patch.object(harness, "clear_owned_alarm") as clear,
            ):
                # The initial empty-alarm check is before arming; simulate that
                # transition rather than actually changing a hardware interface.
                with patch.object(Path, "read_text", side_effect=["", "1800000000"]):
                    self.assertEqual(harness.power(root), 1)
                run.assert_not_called()
                clear.assert_called_once_with("1800000000")
            result = json.loads((root / "power.json").read_text())
            self.assertEqual(result["state"], "failed")
            self.assertTrue(result["alarmArmed"])
            self.assertEqual(result["ownedAlarmCleanup"], "cleared_or_already_fired")

    def test_successful_systemctl_enqueue_does_not_prove_physical_sleep(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alarm = Mock()
            alarm.read_text.side_effect = ["", "1800000000"]
            with (
                patch.object(harness, "load", return_value=SimpleNamespace(private_root=Mock())),
                patch.object(harness, "preflight", return_value={}),
                patch.object(harness, "inhibitors", return_value=[]),
                patch.object(harness, "arm_alarm", return_value="1800000000"),
                patch.object(harness, "ALARM", alarm),
                patch.object(harness.time, "sleep"),
                patch.object(
                    harness, "clocks", side_effect=[{"boottimeMs": 0}, {"boottimeMs": 90000}]
                ),
                patch.object(harness, "command") as run,
                patch.object(harness, "clear_owned_alarm") as clear,
            ):
                self.assertEqual(harness.power(root), 1)
                run.assert_called_once_with(
                    ["sudo", "-n", "systemctl", "--check-inhibitors=yes", "suspend"], timeout=15
                )
                clear.assert_called_once_with("1800000000")
            result = json.loads((root / "power.json").read_text())
            self.assertEqual(result["state"], "failed")
            self.assertIn("no physical", result["error"]["message"])

    def test_first_resumed_unavailable_read_is_retained_without_positive_frame(self):
        endpoint = SimpleNamespace(host_id="snap")
        monitor = harness.Monitor(endpoint)

        def unavailable():
            monitor.stop.set()
            raise OSError("fresh endpoint unavailable")

        endpoint.frame = unavailable
        with patch.object(
            harness,
            "clocks",
            side_effect=[
                {"boottimeMs": 0, "monotonicMs": 0},
                {"boottimeMs": 20050, "monotonicMs": 50},
                {"boottimeMs": 20060, "monotonicMs": 60},
            ],
        ):
            monitor.run()
        self.assertEqual(len(monitor.records), 1)
        result = monitor.records[0]
        self.assertEqual(result["suspendDeltaMs"], 20000)
        self.assertIn("unavailable", result["firstResponseAfterLocalResume"])
        self.assertFalse(monitor.frames)


if __name__ == "__main__":
    unittest.main()
