"""Action SDK and pure framing have no UI/service/discovery dependency."""

import subprocess
import sys
import unittest


class ActionImportTests(unittest.TestCase):
    def test_sdk_imports_without_rofi_or_observation_services(self):
        script = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        blocked = ("rofi_tmux_plus", "tmux_observer.owner", "tmux_observer.collector", "tmux_observer.attachment_collector", "tmux_observer_client.fleet", "tmux_observer_client.direct", "tmux_observer_client._ssh")
        if any(fullname == item or fullname.startswith(item + ".") for item in blocked):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
from tmux_observer_actions.public import ActionClient
ActionClient()
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pure_legacy_framing_imports_without_native_or_desktop_implementations(self):
        script = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ("tmux_observer_actions.tmux", "tmux_observer_actions.lifecycle", "tmux_observer_actions.viewer_service", "tmux_observer.collector", "tmux_observer_client.fleet"):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
from tmux_observer_actions import _remote_framing, _legacy_validation
assert _remote_framing._number("1") == 1
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
