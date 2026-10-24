"""Independent owner-native semantics and the frozen Mesh differential oracle."""

import asyncio
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import test_owner
from mesh_plus.api import (
    Bridge,
    Endpoint,
    Reader,
    ReadGuard,
    configured_reader,
    current_sessions,
    reconstructed,
    validate_response,
)
from mesh_plus.protocol import ProtocolError
from mesh_plus.transport import IPCServer, boottime_ms

from tmux_observer.mesh import TmuxMeshAdapter, TmuxMeshCodec
from tmux_observer.mesh_profile import TmuxMeshProfile
from tmux_observer.native import ValidationError

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests/fixtures/mesh-sdk-v1"


def native(name="ready"):
    return json.loads((ROOT / f"contracts/service-v1/fixtures/{name}.json").read_text())


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = TmuxMeshProfile()
        self.frame = native()
        self.codec = self.profile.bind("fixture-local", "tmux_default")

    def test_fixed_oracle_roundtrips_and_effective_selections(self):
        baseline = json.loads(
            (ROOT / "tests/fixtures/mesh-inputs/profile-baseline.json").read_text()
        )
        expected = {sample["fixture"]: sample for sample in baseline["samples"]}
        checksums = (FIXTURES / "SHA256SUMS").read_text().splitlines()
        self.assertEqual(len(checksums), 6)
        with patch(
            "mesh_plus.state.ReferenceProfile", side_effect=AssertionError("implicit profile")
        ):
            for line in checksums:
                digest, name = line.split()
                raw = (FIXTURES / name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                response = json.loads(raw)
                with self.subTest(fixture=name):
                    validate_response(response, profile=self.profile)
                    frames = [
                        reconstructed(response, host, profile=self.profile)
                        for host in response["mesh"]["hosts"]
                        if host["owner"] is not None
                    ]
                    self.assertEqual(frames, expected[name]["native"])
                    reader = response["mesh"]["reader"]
                    for index, now in enumerate(
                        (reader["encodedAtMs"], reader["encodedAtMs"] + 1000, 2**52)
                    ):
                        self.assertEqual(
                            current_sessions(response, now, reader["clock"], profile=self.profile),
                            expected[name]["effective"][index],
                        )

    def test_native_receipts_and_complete_identity_are_preserved(self):
        state = self.codec.inspect_native(self.frame)
        self.assertEqual(state.owner["service"]["receipt"], self.frame["receipt"])
        self.assertEqual(
            state.receipts,
            [
                {
                    "sourceId": "default",
                    "component": "native",
                    "accepted": 1,
                    "expiry": 10100,
                    "health": "current",
                }
            ],
        )
        row = state.records[0]
        self.assertEqual(
            self.profile.record_identity(row),
            (
                "fixture-local",
                self.frame["snapshot"]["serverGeneration"],
                "$2",
                1700000001,
            ),
        )
        self.assertEqual(
            self.profile.record_receipts(row, state), frozenset({("default", "native")})
        )
        for key in ("hostId", "serverGeneration", "sessionId", "createdAt"):
            altered = {**row, key: "changed"}
            self.assertNotEqual(
                self.profile.record_identity(row), self.profile.record_identity(altered)
            )

    def test_mesh_proof_and_receipt_checks_remain_compulsory(self):
        base = json.loads((FIXTURES / "tmux-fleet.json").read_text())
        remote = next(i for i, host in enumerate(base["mesh"]["hosts"]) if not host["local"])
        mutations = (
            (
                "forged digest",
                lambda f: f["mesh"]["hosts"][remote]["delivery"]["proof"].update(
                    payloadDigest="sha256:" + "f" * 64
                ),
            ),
            (
                "extended expiry",
                lambda f: f["mesh"]["hosts"][remote]["receipts"][0].update(expiresAtMs=2**51),
            ),
            ("removed receipt", lambda f: f["mesh"]["hosts"][remote].update(receipts=[])),
            ("duplicate identity", lambda f: f["sessions"].append(copy.deepcopy(f["sessions"][0]))),
            ("foreign row", lambda f: f["sessions"][0].update(hostId="foreign")),
        )
        for label, mutate in mutations:
            response = copy.deepcopy(base)
            mutate(response)
            with self.subTest(mutation=label), self.assertRaises(ProtocolError):
                validate_response(response, profile=self.profile)

        class EmptyEvidence(TmuxMeshProfile):
            def record_receipts(self, record, state):
                return frozenset()

        reader = base["mesh"]["reader"]
        self.assertEqual(
            current_sessions(base, reader["encodedAtMs"], reader["clock"], profile=EmptyEvidence()),
            [],
        )

    def test_warming_empty_and_failed_history_remain_distinct(self):
        warming = self.codec.inspect_native(native("warming"))
        self.assertIsNone(warming.owner["metadata"])
        self.assertEqual(warming.records, [])
        self.assertEqual(warming.receipts[0]["health"], "stale")
        empty = copy.deepcopy(self.frame)
        empty["snapshot"]["sessions"] = []
        empty["snapshot"]["serverGeneration"] = None
        state = self.codec.inspect_native(empty)
        self.assertIsNotNone(state.owner["metadata"])
        self.assertEqual(state.records, [])
        self.assertEqual(state.receipts[0]["health"], "current")
        failed = copy.deepcopy(self.frame)
        failed["receipt"].update(
            state="failed",
            remainingMs=0,
            attempted=2,
            lastAttemptAt=130,
            lastAttemptResult="failed",
        )
        state = self.codec.inspect_native(failed)
        self.assertEqual(len(state.records), 1)
        self.assertEqual(state.receipts[0]["health"], "stale")
        self.assertIsNone(self.profile.record_receipts(state.records[0], state))
        self.assertEqual(self.profile.restore_native(state.owner, state.records), failed)

    def test_native_admission_rejects_wrong_scope_types_and_bounds(self):
        mutations = (
            lambda f: f.update(sequence=True),
            lambda f: f["receipt"].update(accepted=True),
            lambda f: f["snapshot"]["sessions"][0].update(hostId="foreign"),
            lambda f: f["snapshot"]["sessions"][0].update(name="x" * 16385),
            lambda f: f.update(protocol="unsupported"),
        )
        for mutate in mutations:
            frame = copy.deepcopy(self.frame)
            mutate(frame)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.codec.inspect_native(frame)
        with self.assertRaises(ValidationError):
            self.profile.bind("other", "tmux_default").inspect_native(self.frame)

    def test_owned_projection_and_restoration_do_not_alias_input(self):
        state = self.codec.inspect_native(self.frame)
        restored = self.profile.restore_native(state.owner, state.records)
        self.frame["snapshot"]["sessions"][0]["name"] = "input changed"
        self.frame["receipt"]["accepted"] = 99
        restored["snapshot"]["sessions"][0]["name"] = "output changed"
        restored["source"]["hostId"] = "output changed"
        self.assertEqual(state.records[0]["name"], "fixture")
        self.assertEqual(state.owner["service"]["receipt"]["accepted"], 1)
        self.assertEqual(state.owner["service"]["source"]["hostId"], "fixture-local")

    def test_binding_is_immutable_and_checked_before_dispatch(self):
        with self.assertRaises(FrozenInstanceError):
            self.codec.host = "other"
        with self.assertRaises(FrozenInstanceError):
            self.profile.descriptor = None
        for host, source in (("Invalid Host", "tmux_default"), ("local", "bad-source")):
            with self.assertRaises(ValidationError):
                self.profile.bind(host, source)
        with self.assertRaisesRegex(ProtocolError, "endpoint_codec_binding"):
            Reader(
                "tmux",
                [Endpoint("other", True, None, lambda: None, self.codec)],
                local_host="other",
                profile=self.profile,
            )

    def test_callbacks_perform_no_file_process_or_socket_io(self):
        state = self.codec.inspect_native(self.frame)
        response = json.loads((FIXTURES / "tmux-local.json").read_text())
        payload = {
            "hostId": self.codec.host,
            "sourceId": self.codec.source,
            "ownerFrame": self.frame,
        }
        row = state.records[0]
        with ExitStack() as stack:
            for target in (
                "builtins.open",
                "pathlib.Path.open",
                "socket.socket",
                "subprocess.Popen",
            ):
                stack.enter_context(patch(target, side_effect=AssertionError("callback I/O")))
            self.profile.bind(self.codec.host, self.codec.source)
            self.profile.validate_response(response)
            self.profile.restore_native(state.owner, state.records)
            self.profile.record_host(row)
            self.profile.record_identity(row)
            self.profile.record_receipts(row, state)
            self.profile.record_eligible(row, state)
            self.codec.validate_bridge(payload)
            self.codec.inspect_native(self.frame)

    def test_profile_import_excludes_reference_and_native_implementations(self):
        script = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        blocked = ('mesh_plus.observer', 'agent_observer', 'tmux_observer.owner',
                   'tmux_observer.collector', 'tmux_observer._ipc',
                   'tmux_observer_client', 'tmux_observer_actions', 'rofi_tmux_plus')
        if any(fullname == p or fullname.startswith(p + '.') for p in blocked):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
from tmux_observer.mesh_profile import TmuxMeshProfile
TmuxMeshProfile().bind('local', 'tmux_default')
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_direct_codec_keeps_complete_proof_admission(self):
        payload = {
            "meshProtocol": 1,
            "kind": "proof",
            "nonce": "a" * 32,
            "bridgeId": "11111111-1111-4111-8111-111111111111",
            "sequence": 1,
            "sourceId": "tmux_default",
            "hostId": "fixture-local",
            "clock": self.frame["clock"],
            "encodedAtMs": 150,
            "ownerFrame": self.frame,
            "ownerDigest": "sha256:" + "f" * 64,
            "remaining": [],
            "error": None,
        }
        with self.assertRaisesRegex(ProtocolError, "owner_digest"):
            TmuxMeshCodec("fixture-local").validate(payload)

    def test_worker_admission_keeps_reviewed_library_authority(self):
        from tmux_observer_client._mesh_worker import MeshWorker

        authority = object()
        with patch("mesh_plus.library_authority.LibraryMeshAuthority", return_value=authority):
            worker = MeshWorker("fixture-local")
        self.assertIs(worker.authority, authority)
        self.assertFalse(worker.view_feed)
        self.assertTrue(MeshWorker("fixture-local", authority=authority, view_feed=True).view_feed)
        with self.assertRaisesRegex(ValueError, "boolean"):
            MeshWorker("fixture-local", authority=authority, view_feed=1)
        for version in (
            "0.1.0a10",
            "0.1.0a11",
            "0.1.0a12",
            "0.1.0a13",
            "0.1.0a14",
            "0.1.0a15",
            "0.1.0a16",
            "0.1.0a17",
            "0.1.0a18",
            "0.1.0a23",
            "0.1.0a25",
        ):
            with (
                self.subTest(version=version),
                patch("tmux_observer_client._mesh_worker.__version__", version),
                self.assertRaisesRegex(ValueError, "reviewed mesh-plus 0.1.0a24"),
            ):
                MeshWorker("fixture-local", authority=authority)


class ProfileIPCTests(unittest.IsolatedAsyncioTestCase):
    async def test_configured_poll_watch_disconnect_and_owned_retirement(self):
        profile = TmuxMeshProfile()
        with tempfile.TemporaryDirectory(prefix="tmux-sdk-ipc-") as temporary:
            root = Path(temporary)
            owner, thread, _collector = test_owner.OwnerTests().start(root / "owner.sock")
            server = None
            stream = None
            try:
                adapter = TmuxMeshAdapter("fixture-local", root / "owner.sock")
                path = root / "bridge.sock"
                server = await IPCServer(path, Bridge(adapter).serve, max_clients=2).start()
                with patch(
                    "mesh_plus.state.ReferenceProfile",
                    side_effect=AssertionError("implicit profile"),
                ):
                    reader = await configured_reader(
                        "tmux",
                        source="tmux_default",
                        socket=path,
                        scope="local",
                        local_host="fixture-local",
                        profile=profile,
                    )
                    response = await reader.snapshot()
                    self.assertTrue(
                        current_sessions(
                            response,
                            boottime_ms(),
                            response["mesh"]["reader"]["clock"],
                            profile=profile,
                        )
                    )
                    request_id = "a" * 32
                    guard = ReadGuard("tmux", request_id, profile=profile)
                    stream = reader.watch(request_id=request_id, proof_interval=0.1)
                    for _ in range(20):
                        response = await asyncio.wait_for(anext(stream), 3)
                        guard.accept(response)
                        clock = response["mesh"]["reader"]["clock"]
                        if guard.current(boottime_ms(), clock):
                            break
                    self.assertTrue(guard.current(boottime_ms(), clock))
                    guard.disconnect()
                    self.assertEqual(guard.current(boottime_ms(), clock), [])
                    await stream.aclose()
                    stream = None
                    self.assertEqual(reader.inspect()["activeConnections"], 0)
                    self.assertEqual(reader.inspect()["cleanupFailures"], 0)
            finally:
                if stream is not None:
                    await stream.aclose()
                if server is not None:
                    await server.close()
                owner.stop()
                thread.join(3)
                self.assertFalse(thread.is_alive())
