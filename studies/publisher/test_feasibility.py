"""Decision-driving publisher semantics, factory failures and owned native SSH."""

import asyncio
import copy
import io
import json
import os
import shlex
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cli_entry import load_cli
from generic_publisher import CachedPublication, CachedPublisher
from jsonschema.exceptions import ValidationError as SchemaValidationError
from mesh_plus.api import (
    Bridge,
    Client,
    Endpoint,
    Reader,
    ReadGuard,
    current_sessions,
    reconstructed,
)
from mesh_plus.evidence import clock_domain
from mesh_plus.observer import ObserverAdapter, ObserverCodec
from mesh_plus.protocol import ProtocolError
from mesh_plus.transport import IPCServer, boottime_ms, connect_ipc, connect_ssh
from native_fixture import NativeFixture
from native_source import NativeGuard, TmuxCachedSource, make_tmux_publisher

from tmux_observer.delivery import validate_service_frame
from tmux_observer.mesh_profile import TmuxMeshProfile

ROOT = Path(__file__).resolve().parents[2]
STUDY = Path(__file__).resolve().parent
DETAILS = {}


def native_frame(name="tmux-local"):
    response = json.loads((ROOT / "tests/fixtures/mesh-sdk-v1" / (name + ".json")).read_text())
    host = response["mesh"]["hosts"][0]
    rows = [row for row in response["sessions"] if row["hostId"] == host["hostId"]]
    frame = TmuxMeshProfile().restore_native(host["owner"], rows)
    return rebase(frame)


def rebase(frame):
    frame = copy.deepcopy(frame)
    shift = boottime_ms() - 100 - frame["encodedAt"]
    clock = clock_domain()
    timestamps = {
        "startedAt",
        "finishedAt",
        "encodedAt",
        "acceptedAt",
        "expiresAt",
        "lastAttemptAt",
    }

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "clock":
                    value[key] = clock.copy()
                elif key in timestamps and type(item) is int:
                    value[key] = item + shift
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(frame)
    frame["source"]["uid"] = os.getuid()
    if frame["snapshot"] is not None:
        frame["snapshot"]["source"]["uid"] = os.getuid()
    return frame


class MemorySource:
    def __init__(self, frame):
        self.frame = frame
        self.reads = 0

    async def snapshot(self):
        self.reads += 1
        return copy.deepcopy(self.frame)


def publisher(frame=None):
    frame = native_frame() if frame is None else frame
    return CachedPublisher(
        "tmux",
        frame["source"]["hostId"],
        "tmux_default",
        MemorySource(frame),
        profile=TmuxMeshProfile(),
    )


class PureTests(unittest.TestCase):
    def test_factory_entry_keeps_authority_fast_path_native_and_sdk_free(self):
        code = """import sys
class Fence:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("native_source","generic_publisher","tmux_observer",
                                "mesh_plus.api","mesh_plus.protocol","jsonschema")):
            raise ImportError("authority loaded state SDK/native publisher")
sys.meta_path.insert(0,Fence())
sys.path.insert(0,STUDY_PATH)
sys.argv=["mesh-plus","mesh","list","--json"]
import cli_entry
assert cli_entry.main()==0
""".replace("STUDY_PATH", repr(str(STUDY)))
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [os.sys.executable, "-I", "-B", "-c", code],
                env={**os.environ, "XDG_CONFIG_HOME": temporary, "XDG_STATE_HOME": temporary},
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
        catalog = json.loads(result.stdout)
        self.assertEqual(catalog["schemaVersion"], 1)
        self.assertTrue(catalog["localHostId"])
        self.assertTrue(all(host["local"] for host in catalog["hosts"]))

    def test_generic_publisher_runs_without_native_or_reference_packages(self):
        code = """import asyncio,copy,json,sys
class Fence:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("tmux_observer", "agent_observer", "mesh_plus.observer")):
            raise ImportError("native/reference import")
sys.meta_path.insert(0,Fence())
sys.path.insert(0,STUDY_PATH)
from generic_publisher import CachedPublisher
from mesh_plus.testing.sample import Publisher
async def run():
    domains=[]
    for domain in ("tmux","agent"):
        fixture=Publisher(domain,"fixture-local")
        class Native:
            async def snapshot(self): return copy.deepcopy(fixture.frame)
        p=CachedPublisher(domain,"fixture-local","default",Native(),profile=fixture.state_profile)
        proof=await p.proof({"nonce":"a"*32})
        p.validate(proof)
        domains.append(domain)
    print(json.dumps(domains))
asyncio.run(run())
""".replace("STUDY_PATH", repr(str(STUDY)))
        result = subprocess.run(
            [os.sys.executable, "-I", "-B", "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout), ["tmux", "agent"])

    def test_candidate_and_proof_match_independent_reference(self):
        frame = native_frame()
        owned = publisher(frame)
        reference = ObserverAdapter("tmux", owned.host, owned.source, "/unused")
        for nonce in (None, "1" * 32):
            now = boottime_ms()
            with (
                patch("generic_publisher.boottime_ms", return_value=now),
                patch("mesh_plus.observer.boottime_ms", return_value=now),
            ):
                actual = owned.wrap(copy.deepcopy(frame), nonce)
                expected = reference.wrap(copy.deepcopy(frame), nonce)
            for payload in (actual, expected):
                payload.pop("bridgeId")
            self.assertEqual(actual, expected)
        self.assertNotIsInstance(owned, ObserverAdapter)

    def test_empty_warming_and_historical_states_preserve_native(self):
        warming = json.loads((ROOT / "contracts/service-v1/fixtures/warming.json").read_text())
        frames = [native_frame("tmux-empty"), native_frame("tmux-historical"), rebase(warming)]
        for frame in frames:
            with self.subTest(kind=frame["receipt"]["state"]):
                owned = publisher(frame)
                payload = owned.wrap(frame, "2" * 32)
                self.assertEqual(payload["ownerFrame"], frame)
                ObserverCodec("tmux", owned.host, owned.source).validate(payload)
                if frame["receipt"]["state"] != "ready":
                    self.assertTrue(all(r["remainingMs"] == 0 for r in payload["remaining"]))
        self.assertIsNone(frames[-1]["snapshot"])
        self.assertTrue(frames[1]["snapshot"]["sessions"])
        self.assertEqual(frames[0]["snapshot"]["sessions"], [])

    def test_proof_forgery_and_same_counter_lease_renewal_reject(self):
        owned = publisher()
        proof = owned.wrap(owned.native.frame, "3" * 32)
        for mutate in (
            lambda p: p.update(ownerDigest="sha256:" + "f" * 64),
            lambda p: p.update(nonce=None),
            lambda p: p.update(remaining=[]),
            lambda p: p["remaining"][0].update(remainingMs=2**50),
        ):
            altered = copy.deepcopy(proof)
            mutate(altered)
            with self.assertRaises((ProtocolError, SchemaValidationError)):
                owned.validate(altered)
        altered = copy.deepcopy(owned.native.frame)
        for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
            altered["receipt"][key] += 1
        altered["encodedAt"] += 1
        altered["snapshot"]["sample"]["startedAt"] += 1
        altered["snapshot"]["sample"]["finishedAt"] += 1
        validate_service_frame(altered)
        with self.assertRaisesRegex(ProtocolError, "source_lease_renewal"):
            owned.wrap(altered)
        self.assertEqual(owned.sequence, 1)

    def test_native_scope_uid_clock_request_and_order_reject(self):
        frame = native_frame()
        frame["viewRevision"] = 2
        host, request = frame["source"]["hostId"], frame["requestId"]
        first_mutations = (
            lambda f: (
                f["source"].update(uid=os.getuid() + 1),
                f["snapshot"]["source"].update(uid=os.getuid() + 1),
            ),
            lambda f: (
                f["clock"].update(timeNamespace="time:999999"),
                f["snapshot"]["clock"].update(timeNamespace="time:999999"),
            ),
            lambda f: f.update(requestId="wrong-request"),
        )
        for mutate in first_mutations:
            bad = copy.deepcopy(frame)
            mutate(bad)
            validate_service_frame(bad)
            with self.assertRaises(ValueError):
                NativeGuard(host, request).accept(bad)
        with self.assertRaisesRegex(ValueError, "native_host"):
            NativeGuard("wrong-host", request).accept(frame)
        for field, value, code in (
            ("sequence", frame["sequence"] + 2, "native_stream_order"),
            ("viewRevision", 1, "native_revision_regression"),
            ("publisherId", "99999999-9999-4999-8999-999999999999", "native_publisher_restart"),
            ("encodedAt", frame["encodedAt"] - 1, "native_clock_regression"),
        ):
            guard = NativeGuard(host, request)
            guard.accept(frame)
            later = copy.deepcopy(frame)
            later.update(kind="view", requestId=None, sequence=frame["sequence"] + 1)
            later[field] = value
            if field == "encodedAt":
                later["receipt"]["remainingMs"] += 1
            validate_service_frame(later)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, code):
                guard.accept(later)

    def test_publication_owns_source_data_and_restart_resets_receipt_binding(self):
        owned = publisher()
        frame = copy.deepcopy(owned.native.frame)
        payload = owned.wrap(frame)
        frame["snapshot"]["sessions"].clear()
        self.assertTrue(payload["ownerFrame"]["snapshot"]["sessions"])
        warming = rebase(
            json.loads((ROOT / "contracts/service-v1/fixtures/warming.json").read_text())
        )
        warming["publisherId"] = payload["ownerFrame"]["publisherId"]
        with self.assertRaisesRegex(ProtocolError, "source_receipt_regression"):
            owned.wrap(warming)
        warming["publisherId"] = "99999999-9999-4999-8999-999999999999"
        restarted = owned.wrap(warming, "9" * 32)
        self.assertEqual(restarted["remaining"][0]["remainingMs"], 0)

    def test_default_and_omitted_factory_retain_reference_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "sources.toml"
            config.write_text(
                'version=1\nhost="fixture-local"\n[sources.tmux_default]\n'
                'domain="tmux"\nsocket="/unused"\n'
            )
            config.chmod(0o600)
            cli = load_cli()
            for factories in (None, {}, {"agent": lambda *_: self.fail("wrong domain")}):
                adapter = cli.configured_adapter(
                    config, "tmux_default", publisher_factories=factories
                )
                self.assertIsInstance(adapter, ObserverAdapter)

    def test_selected_factory_failure_binding_and_config_selector_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "sources.toml"
            content = 'version=1\nhost="fixture-local"\n[sources.tmux_default]\n'
            config.write_text(content + 'domain="tmux"\nsocket="/unused"\n')
            config.chmod(0o600)
            cli = load_cli()

            def unavailable(*_):
                raise ImportError("selected factory unavailable")

            with patch(
                "mesh_plus.observer.ObserverAdapter", side_effect=AssertionError("fallback")
            ):
                with self.assertRaisesRegex(ImportError, "selected factory unavailable"):
                    cli.configured_adapter(
                        config, "tmux_default", publisher_factories={"tmux": unavailable}
                    )
                wrong = publisher()
                wrong.host = "wrong-host"
                with self.assertRaisesRegex(ProtocolError, "factory_binding"):
                    cli.configured_adapter(
                        config, "tmux_default", publisher_factories={"tmux": lambda *_: wrong}
                    )
            config.write_text(
                content + 'domain="tmux"\nsocket="/unused"\nfactory="untrusted.module"\n'
            )
            with self.assertRaisesRegex(ProtocolError, "source_descriptor_shape"):
                cli.configured_adapter(
                    config, "tmux_default", publisher_factories={"tmux": unavailable}
                )

    def test_main_captures_factory_mapping_and_rejects_unreviewed_domain(self):
        cli = load_cli()
        original = {"tmux": lambda *_: None}
        observed = []

        async def run(_args, *, publisher_factories):
            original.clear()
            observed.extend(publisher_factories)
            return 0

        with (
            patch.object(cli, "run", run),
            patch("sys.argv", ["mesh-plus", "doctor"]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(cli.main(publisher_factories=original), 0)
        self.assertEqual(observed, ["tmux"])
        with self.assertRaisesRegex(ValueError, "publisher_factory_mapping"):
            cli.main(publisher_factories={"arbitrary-module": lambda *_: None})


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_watch_publication_owns_native_barrier_and_frame(self):
        frame = native_frame()
        barrier = {"viewRevision": frame["viewRevision"]}
        closed = asyncio.Event()

        class Native:
            async def watch(self):
                try:
                    yield CachedPublication(frame, frame["publisherId"], barrier)
                finally:
                    closed.set()

        owned = CachedPublisher(
            "tmux", frame["source"]["hostId"], "tmux_default", Native(), profile=TmuxMeshProfile()
        )
        iterator = owned.watch()
        publication = await anext(iterator)
        barrier["viewRevision"] += 1
        frame["snapshot"]["sessions"].clear()
        self.assertNotEqual(publication.barrier, barrier)
        self.assertTrue(publication.payload["ownerFrame"]["snapshot"]["sessions"])
        await iterator.aclose()
        self.assertTrue(closed.is_set())

    async def test_cancellation_during_acquisition_closes_late_admitted_channel(self):
        started, finish = asyncio.Event(), asyncio.Event()

        class Channel:
            closed = 0

            async def close(self):
                self.closed += 1

        channel = Channel()

        async def connect(*_args, **_kwargs):
            started.set()
            await finish.wait()
            return channel

        native = TmuxCachedSource("fixture-local", "/unused")
        with patch("native_source.connect_ipc", connect):
            task = asyncio.create_task(native.snapshot())
            await started.wait()
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            finish.set()
            await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(channel.closed, 1)
        self.assertEqual(native.active, 0)

    async def test_guard_construction_failure_retires_admitted_native_connection(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "owner.sock"
            closed = asyncio.Event()

            async def owner(reader, writer):
                try:
                    await reader.read()
                finally:
                    writer.close()
                    await writer.wait_closed()
                    closed.set()

            server = await asyncio.start_unix_server(owner, path=path)
            path.chmod(0o600)
            source = TmuxCachedSource("fixture-local", path)
            try:
                with (
                    patch("native_source.NativeGuard", side_effect=ValueError("clock unavailable")),
                    self.assertRaisesRegex(ValueError, "clock unavailable"),
                ):
                    await source.snapshot()
                await asyncio.wait_for(closed.wait(), 1)
                self.assertEqual(source.active, 0)
            finally:
                server.close()
                await server.wait_closed()

    async def test_receiver_rejects_valid_shape_wrong_proof_nonce(self):
        frame = native_frame()
        frame["source"]["hostId"] = "fixture-remote"
        frame["snapshot"]["source"]["hostId"] = "fixture-remote"
        for row in frame["snapshot"]["sessions"]:
            row["hostId"] = "fixture-remote"

        class Forged(CachedPublisher):
            async def proof(self, parameters):
                value = await super().proof(parameters)
                value["nonce"] = "f" * 64
                return value

        profile = TmuxMeshProfile()
        adapter = Forged(
            "tmux", "fixture-remote", "tmux_default", MemorySource(frame), profile=profile
        )
        codec = profile.bind("fixture-remote", "tmux_default")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bridge.sock"
            server = await IPCServer(path, Bridge(adapter).serve).start()

            async def connect():
                return await Client.connect(
                    await connect_ipc(path),
                    host=codec.host,
                    source=codec.source,
                    profile=codec.profile_id,
                    codec=codec.validate_bridge,
                )

            try:
                reader = Reader(
                    "tmux",
                    [Endpoint("fixture-remote", False, "sha256:" + "a" * 64, connect, codec)],
                    local_host="viewer",
                    catalog_revision="sha256:" + "b" * 64,
                    profile=profile,
                )
                response = await reader.snapshot()
                self.assertEqual(
                    current_sessions(
                        response,
                        boottime_ms(),
                        response["mesh"]["reader"]["clock"],
                        profile=profile,
                    ),
                    [],
                )
                self.assertGreater(adapter.native.reads, 0)
            finally:
                await server.close()

    async def test_nonce_admission_precedes_new_cached_read_and_expiry_stays_zero(self):
        frame = native_frame()
        owned = publisher(frame)
        with self.assertRaises(ProtocolError):
            await owned.proof({"nonce": "invalid"})
        self.assertEqual(owned.native.reads, 0)
        proof = await owned.proof({"nonce": "4" * 32})
        self.assertEqual(owned.native.reads, 1)
        self.assertEqual(proof["ownerFrame"], frame)
        expired = frame["receipt"]["expiresAt"] + 1
        with patch("generic_publisher.boottime_ms", return_value=expired):
            proof = await owned.proof({"nonce": "5" * 32})
        self.assertEqual(owned.native.reads, 2)
        self.assertEqual(proof["remaining"][0]["remainingMs"], 0)
        self.assertEqual(proof["ownerFrame"]["receipt"], frame["receipt"])

    async def test_native_ipc_repeated_cancellation_retires_channels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "owner.sock"
            clients = set()

            async def stalled(reader, writer):
                task = asyncio.current_task()
                clients.add(task)
                try:
                    await reader.readuntil(b"\n")
                    await reader.read()
                finally:
                    writer.close()
                    await writer.wait_closed()
                    clients.remove(task)

            server = await asyncio.start_unix_server(stalled, path=path)
            path.chmod(0o600)
            native = TmuxCachedSource("fixture-local", path)
            try:
                for _ in range(5):
                    task = asyncio.create_task(native.snapshot())
                    for _ in range(100):
                        if native.active:
                            break
                        await asyncio.sleep(0.005)
                    self.assertEqual(native.active, 1)
                    task.cancel()
                    await asyncio.sleep(0)
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    self.assertEqual(native.active, 0)
                for _ in range(100):
                    if not clients:
                        break
                    await asyncio.sleep(0.005)
                self.assertFalse(clients)
            finally:
                server.close()
                await server.wait_closed()
                for task in list(clients):
                    task.cancel()
                await asyncio.gather(*clients, return_exceptions=True)


class StudyFixture(NativeFixture):
    def __init__(self):
        super().__init__()
        self.closed = False

    def env(self, role):
        env = super().env(role)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def close(self):
        if not self.closed:
            super().close()
            self.closed = True


class NativeTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_native_factory_fixed_ssh_recovery_old_bridge_and_passivity(self):
        fixture = StudyFixture()
        baseline_python = os.environ["TMUX_PUBLISHER_BASELINE_PYTHON"]
        self.addCleanup(fixture.close)
        for role in ("local", "remote"):
            fixture.native(role, "new-session", "-d", "-s", "publisher-owned-" + role, "sleep 180")
        owners = {role: fixture.start_owner(role)[0] for role in ("local", "remote")}
        before = {
            role: {
                "refs": fixture.native(
                    role,
                    "list-sessions",
                    "-F",
                    "#{pid}|#{socket_path}|#{session_id}|#{session_created}|#{session_attached}",
                ),
                "hooks": fixture.native(role, "show-hooks"),
                "options": fixture.native(role, "show-options", "-g"),
            }
            for role in ("local", "remote")
        }
        fixture.start_ssh()
        trace = fixture.root / "factory-trace.jsonl"
        forced = fixture.root / "forced.py"
        forced.write_text(
            forced.read_text().replace(
                "os.execv(",
                "os.environ['TMUX_PUBLISHER_STUDY_TRACE'] = " + repr(str(trace)) + "\nos.execv(",
            )
        )
        forced.chmod(0o600)
        config = fixture.root / "sources.toml"

        def select_cli(python, entry=None):
            argv = (
                [python, "-I", "-B", str(entry)]
                if entry
                else [python, "-I", "-B", "-m", "mesh_plus.cli"]
            )
            fixture.write(
                fixture.bin / "mesh-plus",
                "#!/bin/sh\nexec "
                + shlex.join(argv)
                + ' "$@" --config '
                + shlex.quote(str(config))
                + "\n",
                executable=True,
            )

        select_cli(os.sys.executable, STUDY / "cli_entry.py")
        profile = TmuxMeshProfile()
        local_config = fixture.root / "local-sources.toml"
        fixture.write(
            local_config,
            'version=1\nhost="fixture-local"\n[sources.tmux_default]\n'
            'domain="tmux"\nsocket=' + json.dumps(str(fixture.local / "owner.sock")) + "\n",
        )
        with patch.dict(os.environ, {"TMUX_PUBLISHER_STUDY_TRACE": str(trace)}):
            adapter = load_cli().configured_adapter(
                local_config, "tmux_default", publisher_factories={"tmux": make_tmux_publisher}
            )
        source = adapter.native
        self.assertIsInstance(source, TmuxCachedSource)
        path = fixture.local / "mesh.sock"
        server = await IPCServer(path, Bridge(adapter).serve, max_clients=2).start()

        async def make_reader():
            local_codec = profile.bind("fixture-local", "tmux_default")
            remote_codec = profile.bind("fixture-remote", "tmux_default")

            async def local():
                return await Client.connect(
                    await connect_ipc(path),
                    host=local_codec.host,
                    source=local_codec.source,
                    profile=local_codec.profile_id,
                    codec=local_codec.validate_bridge,
                )

            async def remote():
                return await Client.connect(
                    await connect_ssh(
                        "fixture-remote", "tmux_default", executable=str(fixture.bin / "ssh")
                    ),
                    host=remote_codec.host,
                    source=remote_codec.source,
                    profile=remote_codec.profile_id,
                    codec=remote_codec.validate_bridge,
                )

            revision = "sha256:" + "6" * 64

            async def check_catalog():
                return revision

            return Reader(
                "tmux",
                [
                    Endpoint("fixture-local", True, None, local, local_codec),
                    Endpoint("fixture-remote", False, "sha256:" + "7" * 64, remote, remote_codec),
                ],
                local_host="fixture-local",
                catalog_revision=revision,
                catalog_check=check_catalog,
                profile=profile,
            )

        def current(frame):
            return current_sessions(
                frame, boottime_ms(), frame["mesh"]["reader"]["clock"], profile=profile
            )

        def references(rows):
            return sorted(
                tuple(row[k] for k in ("hostId", "serverGeneration", "sessionId", "createdAt"))
                for row in rows
            )

        async def wait_for(stream, predicate):
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                frame = await asyncio.wait_for(anext(stream), deadline - time.monotonic())
                guard.accept(frame)
                if predicate(frame):
                    return frame
            self.fail("owned replacement stream did not reach required state")

        stream = None
        guard = None
        try:
            first = await (await make_reader()).snapshot()
            self.assertEqual(len(current(first)), 2)
            expected = references(current(first))
            for host in first["mesh"]["hosts"]:
                native = reconstructed(first, host, profile=profile)
                self.assertEqual(native["source"]["hostId"], host["hostId"])
                self.assertEqual(
                    native["snapshot"]["sessions"],
                    [r for r in first["sessions"] if r["hostId"] == host["hostId"]],
                )
            reader = await make_reader()
            request_id = "8" * 32
            guard = ReadGuard(
                "tmux", request_id, host_ids=["fixture-local", "fixture-remote"], profile=profile
            )
            stream = reader.watch(request_id=request_id)
            await wait_for(stream, lambda f: len(current(f)) == 2)
            fixture.native(
                "remote", "rename-session", "-t", "publisher-owned-remote", "publisher-renamed"
            )
            changed = await wait_for(
                stream, lambda f: any(r["name"] == "publisher-renamed" for r in current(f))
            )
            self.assertEqual(references(current(changed)), expected)
            epoch = reconstructed(changed, changed["mesh"]["hosts"][1], profile=profile)[
                "publisherId"
            ]
            owners["remote"].terminate()
            owners["remote"].wait(3)
            await wait_for(
                stream, lambda f: not any(r["hostId"] == "fixture-remote" for r in current(f))
            )
            fixture.start_owner("remote")
            recovered = await wait_for(
                stream,
                lambda f: (
                    len(current(f)) == 2
                    and reconstructed(f, f["mesh"]["hosts"][1], profile=profile)["publisherId"]
                    != epoch
                ),
            )
            self.assertEqual(references(current(recovered)), expected)
            await stream.aclose()
            stream = None
            guard.disconnect()
            self.assertEqual(guard.current(boottime_ms(), recovered["mesh"]["reader"]["clock"]), [])
            for role in ("local", "remote"):
                for key, command in (
                    (
                        "refs",
                        (
                            "list-sessions",
                            "-F",
                            "#{pid}|#{socket_path}|#{session_id}|#{session_created}|#{session_attached}",
                        ),
                    ),
                    ("hooks", ("show-hooks",)),
                    ("options", ("show-options", "-g")),
                ):
                    self.assertEqual(fixture.native(role, *command), before[role][key])
                self.assertEqual(fixture.native(role, "list-clients", "-F", "#{client_pid}"), b"")
            select_cli(baseline_python)
            old = await (await make_reader()).snapshot()
            self.assertEqual(references(current(old)), expected)
            select_cli(os.sys.executable)
            reference = await (await make_reader()).snapshot()
            self.assertEqual(references(current(reference)), expected)
            select_cli(os.sys.executable, STUDY / "cli_entry.py")
            fixture.native("remote", "kill-server")
            deadline = time.monotonic() + 6
            while True:
                empty = await (await make_reader()).snapshot()
                if not any(r["hostId"] == "fixture-remote" for r in empty["sessions"]):
                    break
                self.assertLess(time.monotonic(), deadline)
                await asyncio.sleep(0.2)
            native = reconstructed(empty, empty["mesh"]["hosts"][1], profile=profile)
            self.assertEqual(native["receipt"]["state"], "ready")
            self.assertIsNone(native["snapshot"]["serverGeneration"])
            events = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertTrue(any(e["event"] == "factory" for e in events))
            self.assertEqual(
                {e["host"] for e in events if e["event"] == "factory"},
                {"fixture-local", "fixture-remote"},
            )
            self.assertTrue(any(e.get("operation") == "watch" for e in events))
            self.assertTrue(
                all(e["operation"] in {"status", "watch"} for e in events if "operation" in e)
            )
            DETAILS["native"] = {
                "ownedOwners": 2,
                "rows": 2,
                "transport": "actual-fixed-SSH-command",
                "referenceBridgeVersions": ["0.1.0a10", "0.1.0a13"],
                "factoryInvocations": sum(e["event"] == "factory" for e in events),
                "factoryHosts": ["fixture-local", "fixture-remote"],
                "updateRestartEmptyPassivity": True,
            }
        finally:
            if stream is not None:
                await stream.aclose()
            if guard is not None:
                guard.disconnect()
            await server.close()
            self.assertEqual(source.active, 0)
            self.assertFalse(path.exists())
            fixture.close()
            self.assertFalse(fixture.root.exists())
            self.assertTrue(all(p.poll() is not None for p in fixture.processes))
            DETAILS["cleanup"] = {
                "nativeSourceChannels": 0,
                "fixtureRootRemoved": True,
                "ownedParentsRetired": True,
            }
