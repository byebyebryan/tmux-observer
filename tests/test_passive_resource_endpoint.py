"""The actual-session resource endpoint must never acquire native write authority."""

import importlib.machinery
import importlib.util
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


class PassiveEndpointTests(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader(
            "passive_resource_test",
            str(Path(__file__).resolve().parents[1] / "scripts/accept-native-fleet"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.module = importlib.util.module_from_spec(spec)
        loader.exec_module(self.module)
        self.root = Path("/tmp/to-fleet-" + uuid.uuid4().hex)
        self.root.mkdir(mode=0o700)
        self.addCleanup(shutil.rmtree, self.root)

    def test_passive_endpoint_refuses_mutations_before_starting_any_command(self):
        endpoint = self.module.Endpoint(self.root, "snap", native_fixture=False)
        with patch.object(self.module, "command") as command:
            for args in (("kill-server",), ("new-session", "-d"), ("rename-session", "changed")):
                with self.subTest(args=args), self.assertRaises(AssertionError):
                    endpoint.native(*args)
            command.assert_not_called()

    def test_passive_cleanup_never_kills_an_ordinary_server(self):
        endpoint = self.module.Endpoint(self.root, "snap", native_fixture=False)
        (self.root / "native").mkdir(mode=0o700)
        with patch.object(endpoint, "native") as native:
            endpoint.close()
            native.assert_not_called()

    def test_ordinary_native_path_and_default_owned_fixture_stay_separate(self):
        with patch.dict("os.environ", {"TMUX_TMPDIR": "/tmp/explicit-native"}):
            passive = self.module.Endpoint(self.root, "snap", native_fixture=False)
            fixture = self.module.Endpoint(self.root, "snap")
        self.assertEqual(passive.env["TMUX_TMPDIR"], "/tmp/explicit-native")
        self.assertEqual(fixture.env["TMUX_TMPDIR"], str(self.root / "native"))

    def test_ordinary_additions_and_name_sort_changes_preserve_full_baseline_references(self):
        endpoint = self.module.Endpoint(self.root, "snap", native_fixture=False)
        endpoint.baseline = "$1|11\n$2|22"
        endpoint.hooks = ""
        endpoint.passive_generation = "generation"
        with (
            patch.object(endpoint, "native", return_value=""),
            patch.object(
                endpoint, "independent_native", return_value={"serverGeneration": "generation"}
            ),
            patch.object(endpoint, "roster", return_value="$3|33\n$2|22\n$1|11"),
        ):
            self.assertEqual(
                endpoint.dispatch({"operation": "passivity"}),
                {
                    "preserved": True,
                    "baselineSessions": 2,
                    "currentSessions": 3,
                    "addedReferences": 1,
                },
            )

    def test_ordinary_loss_reuse_and_duplicate_references_remain_failed_preservation(self):
        endpoint = self.module.Endpoint(self.root, "snap", native_fixture=False)
        endpoint.baseline = "$1|11\n$2|22"
        endpoint.hooks = ""
        endpoint.passive_generation = "generation"
        for roster in ("$1|11", "$1|11\n$2|23", "$1|11\n$2|22\n$2|22"):
            with (
                self.subTest(roster=roster),
                patch.object(endpoint, "native", return_value=""),
                patch.object(
                    endpoint, "independent_native", return_value={"serverGeneration": "generation"}
                ),
                patch.object(endpoint, "roster", return_value=roster),
                self.assertRaises(AssertionError),
            ):
                endpoint.dispatch({"operation": "passivity"})


if __name__ == "__main__":
    unittest.main()
