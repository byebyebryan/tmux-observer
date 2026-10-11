"""Ordinary native and delivery consumers do not require optional Mesh."""

import subprocess
import sys
import unittest


class NativeImportTests(unittest.TestCase):
    def test_native_facades_import_without_mesh(self):
        script = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'mesh_plus' or fullname.startswith('mesh_plus.'):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
from tmux_observer import native, delivery, public
assert native.FRAME_LIMIT > 0
assert delivery.SERVICE_PROTOCOL == 'tmux-observer.service.v1'
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
