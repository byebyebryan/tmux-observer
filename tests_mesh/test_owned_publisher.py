"""Observer factory behavior through the installed public generic Mesh API."""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_owner
from mesh_plus.api import CachedPublisher

from tmux_observer._mesh_source import TmuxCachedSource
from tmux_observer.mesh import TmuxMeshAdapter
from tmux_observer.mesh_publisher import make_publisher

ROOT = Path(__file__).resolve().parents[1]


class FactoryTests(unittest.TestCase):
    def test_factory_and_worker_import_without_reference_or_native_implementations(self):
        program = """import sys
sys.path.insert(0,SOURCE)
class Fence:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('mesh_plus.observer','tmux_observer.collector',
                                'tmux_observer.owner','tmux_observer_actions',
                                'tmux_observer_client.desktop')):
            raise ImportError('owned publisher loaded reference/native implementation')
sys.meta_path.insert(0,Fence())
from tmux_observer.mesh_publisher import make_publisher
from tmux_observer_client._mesh_worker import MeshWorker
from unittest.mock import patch
with patch('asyncio.open_unix_connection',side_effect=AssertionError('constructor opened socket')):
    publisher=make_publisher('fixture-local','tmux_default','/absent-owner.sock')
    worker=MeshWorker('fixture-local',authority=object())
assert (publisher.host,publisher.source,publisher.profile)==(
    'fixture-local','tmux_default','tmux-observer.mesh-candidate.v1')
print('owned-factory')
""".replace("SOURCE", repr(str(ROOT / "src")))
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", program],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "owned-factory")

    def test_compatibility_adapter_composes_owned_publisher(self):
        adapter = TmuxMeshAdapter("fixture-local", "/absent-owner.sock")
        self.assertIsInstance(adapter.publisher, CachedPublisher)
        self.assertIsInstance(adapter.native, TmuxCachedSource)
        self.assertEqual(adapter.source, "tmux_default")
        self.assertEqual(adapter.capabilities, ("snapshot", "proof", "subscribe"))

    def test_lazy_installed_launcher_keeps_authority_path_state_free(self):
        program = """import sys
class Fence:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('tmux_observer','mesh_plus.api','mesh_plus.protocol','jsonschema')):
            raise ImportError('authority imported state/native publisher')
sys.meta_path.insert(0,Fence())
from mesh_plus.cli import main
def factory(host,source,socket):
    from tmux_observer.mesh_publisher import make_publisher
    return make_publisher(host,source,socket)
sys.argv=['mesh-plus','mesh','list','--json']
raise SystemExit(main(publisher_factories={'tmux':factory}))
"""
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", program],
                env={**os.environ, "XDG_CONFIG_HOME": temporary, "XDG_STATE_HOME": temporary},
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
        catalog = json.loads(result.stdout)
        self.assertEqual(catalog["schemaVersion"], 1)
        self.assertTrue(all(host["local"] for host in catalog["hosts"]))


class ProofTests(unittest.IsolatedAsyncioTestCase):
    async def test_proof_nonce_precedes_new_cached_native_acquisition(self):
        with tempfile.TemporaryDirectory(prefix="tmux-publisher-owner-") as temporary:
            owner, thread, collector = test_owner.OwnerTests().start(Path(temporary) / "owner.sock")
            publisher = make_publisher("fixture-local", "tmux_default", owner.path)
            try:
                original = publisher.native.snapshot
                with patch.object(publisher.native, "snapshot", wraps=original) as snapshot:
                    for invalid in ({}, {"nonce": "invalid"}, None):
                        with self.assertRaises(ValueError):
                            await publisher.proof(invalid)
                    self.assertEqual(snapshot.call_count, 0)
                    before = collector.calls
                    candidate = await publisher.snapshot({})
                    proof = await publisher.proof({"nonce": "a" * 32})
                    self.assertEqual(snapshot.call_count, 2)
                    self.assertEqual(proof["nonce"], "a" * 32)
                    self.assertEqual(proof["ownerFrame"]["receipt"]["accepted"], 1)
                    self.assertEqual(
                        candidate["ownerFrame"]["snapshot"], proof["ownerFrame"]["snapshot"]
                    )
                    self.assertEqual(collector.calls, before)
                    watch = publisher.watch()
                    await anext(watch)
                    await watch.aclose()
            finally:
                owner.stop()
                await asyncio.to_thread(thread.join, 3)
            self.assertFalse(thread.is_alive())
