"""Exercise real acceptance CLI dispatch without starting a fixture or host action."""

import argparse
import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def dispatch(name, arguments, *, status):
    source = ast.parse((SCRIPTS / name).read_text(), filename=name)
    guard = source.body[-1]
    if not isinstance(guard, ast.If):
        raise TypeError("expected final CLI guard")
    code = compile(ast.Module(body=[guard], type_ignores=[]), name, "exec")
    coordinator, worker = Mock(return_value=status), Mock(return_value=0)
    namespace = {
        "__name__": "__main__",
        "__doc__": "owned test",
        "argparse": argparse,
        "Path": Path,
        "main": coordinator,
        "worker": worker,
    }
    with patch("sys.argv", [name, *arguments]):
        try:
            exec(code, namespace)  # noqa: S102 - trusted CLI guard; runtime callbacks replaced
        except SystemExit as error:
            return error.code, coordinator, worker
    return None, coordinator, worker


class AcceptanceCLIStatusTests(unittest.TestCase):
    def test_failed_resource_status_reaches_cli_for_both_coordinators(self):
        for script in ("accept-native-remote-desktop", "accept-installed-capacity"):
            with self.subTest(script=script):
                code, coordinator, worker = dispatch(
                    script, ["--output", "/owned/output.json"], status=1
                )
                self.assertEqual(code, 1)
                coordinator.assert_called_once()
                worker.assert_not_called()

    def test_passed_resource_status_and_frozen_input_reach_cli(self):
        for script in ("accept-native-remote-desktop", "accept-installed-capacity"):
            with self.subTest(script=script):
                code, coordinator, worker = dispatch(
                    script,
                    ["--artifact", "/owned/candidate.json", "--output", "/owned/output.json"],
                    status=0,
                )
                self.assertEqual(code, 0)
                coordinator.assert_called_once()
                self.assertIn(
                    Path("/owned/candidate.json"),
                    (*coordinator.call_args.args, *coordinator.call_args.kwargs.values()),
                )
                worker.assert_not_called()

    def test_frozen_input_in_private_worker_mode_is_rejected_before_execution(self):
        for script, arguments in (
            ("accept-native-remote-desktop", ["--worker", "/owned/root", "--host-id", "snap"]),
            ("accept-installed-capacity", ["--root", "/owned/root", "--role", "fleet"]),
        ):
            with self.subTest(script=script), patch("sys.stderr"):
                code, coordinator, worker = dispatch(
                    script, [*arguments, "--artifact", "/owned/candidate.json"], status=0
                )
                self.assertEqual(code, 2)
                coordinator.assert_not_called()
                worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
