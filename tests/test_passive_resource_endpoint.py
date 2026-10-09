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


if __name__ == "__main__":
    unittest.main()
