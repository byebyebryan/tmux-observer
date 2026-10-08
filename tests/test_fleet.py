"""Real fleet Unix IPC and scheduler faults with isolated synthetic sources."""

import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_owner

from tmux_observer._clock import boottime_ms
from tmux_observer._ipc import IPCError
from tmux_observer.public import validate_fleet_frame
from tmux_observer_client._desktop_input import reference
from tmux_observer_client._errors import ContractError
from tmux_observer_client.fleet import POOL_LIMIT, FleetPublisher
from tmux_observer_client.mesh import MeshHost, MeshPolicy, MeshRoute, MeshSnapshot
from tmux_observer_client.public import read_cached


class MissingMesh:
    def __init__(self):
        self.calls = 0

    def load(self, **_kwargs):
        self.calls += 1


class Scanner:
    def __init__(self):
        self.calls = []

    def __call__(self, hosts, *, deadline):
        self.calls.append((boottime_ms(), copy.deepcopy(hosts)))
        return (
            "ready",
            {
                reference(row): {"state": "none", "reason": None}
                for host in hosts
                for row in host["sessions"]
            },
            None,
        )


class FleetTests(unittest.TestCase):
    def wait(self, condition, *, budget=3):
        until = time.monotonic() + budget
        value = None
        while time.monotonic() < until:
            try:
                value = condition()
            except IPCError:
                value = None
            if value:
                return value
            time.sleep(0.01)
        self.fail("isolated fleet condition did not complete")

    def start(self, root, *, owner=True):
        owner_path, fleet_path = root / "owner.sock", root / "fleet.sock"
        publisher, owner_thread, collector = (
            test_owner.OwnerTests().start(owner_path) if owner else (None, None, None)
        )
        scanner, mesh, errors, fingerprint = Scanner(), MissingMesh(), [], [0]
        fleet = FleetPublisher(
            "fixture-local",
            path=fleet_path,
            mesh=mesh,
            owner_path=owner_path,
            scanner=scanner,
            fingerprint=lambda _context: fingerprint[0],
        )

        def run():
            try:
                fleet.run()
            except Exception as error:  # noqa: BLE001 - propagate any owned thread failure to the test
                errors.append(error)

        thread = threading.Thread(target=run)
        thread.start()

        def cleanup():
            fleet.stop()
            thread.join(timeout=6)
            if publisher is not None:
                publisher.stop()
                owner_thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors, errors)

        self.addCleanup(cleanup)

        def ready():
            frame = self.read(fleet)
            view = frame["snapshot"]
            return (
                frame
                if view["mesh"]["state"] == "local_only"
                and view["desktop"]["state"] == "ready"
                and (not owner or view["hosts"][0]["sessions"])
                else None
            )

        self.wait(ready)
        return fleet, publisher, collector, scanner, mesh, fingerprint

    def read(self, fleet, **kwargs):
        return validate_fleet_frame(
            read_cached(
                fleet.state.context_id, path=fleet.path, expected_host="fixture-local", **kwargs
            )
        )

    def test_many_cached_reads_and_probe_errors_share_sources(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-") as temporary:
            fleet, _owner, collector, scanner, mesh, _fingerprint = self.start(Path(temporary))
            calls, scans, catalog_reads = collector.calls, len(scanner.calls), mesh.calls
            for _ in range(12):
                frame = self.read(fleet)
                self.assertEqual(
                    frame["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "none"
                )
            for operation in ("status", "probe"):
                self.read(fleet, operation=operation)
            with self.assertRaises(IPCError) as error:
                self.read(fleet, publisher_id="11111111-1111-4111-8111-111111111111")
            self.assertEqual(error.exception.code, "stale_scope")
            self.assertEqual(
                (collector.calls, len(scanner.calls), mesh.calls), (calls, scans, catalog_reads)
            )

    def test_grouped_refresh_reconciles_desktop_after_actual_owner_sample(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-refresh-") as temporary:
            fleet, _owner, collector, scanner, _mesh, _fingerprint = self.start(Path(temporary))
            sources = [
                {"hostId": "fixture-local", "source": source} for source in ("owner", "desktop")
            ]
            value = self.read(fleet, operation="refresh", sources=sources)["ticket"]

            def complete():
                frame = self.read(
                    fleet,
                    operation="refresh_status",
                    publisher_id=value["publisherId"],
                    ticket_id=value["id"],
                )
                return (
                    frame
                    if frame["ticket"]["state"] in ("complete", "failed", "deadline")
                    else None
                )

            frame = self.wait(complete, budget=4)
            self.assertEqual(frame["ticket"]["state"], "complete", frame["ticket"])
            view = frame["snapshot"]
            owner = view["hosts"][0]["owner"]
            self.assertGreaterEqual(owner["receipt"]["startedAt"], value["requestedAt"])
            self.assertGreaterEqual(view["desktop"]["startedAt"], owner["receipt"]["acceptedAt"])
            self.assertEqual(
                frame["ticket"]["sources"][0]["attempt"], owner["receipt"]["acceptedAttempt"]
            )
            before = collector.calls, len(scanner.calls)
            for _ in range(8):
                self.read(
                    fleet,
                    operation="refresh_status",
                    publisher_id=value["publisherId"],
                    ticket_id=value["id"],
                )
            self.assertEqual((collector.calls, len(scanner.calls)), before)

    def test_missing_owner_is_prepared_failure_without_a_direct_fallback(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-missing-") as temporary:
            fleet, _owner, _collector, scanner, _mesh, _fingerprint = self.start(
                Path(temporary), owner=False
            )
            frame = self.read(fleet)
            self.assertFalse(frame["snapshot"]["hosts"][0]["sessions"])
            self.assertEqual(frame["snapshot"]["hosts"][0]["owner"]["localExpiry"], 0)
            before = len(scanner.calls)
            ticket = self.read(
                fleet, operation="refresh", sources=[{"hostId": "fixture-local", "source": "owner"}]
            )["ticket"]

            def failed():
                value = self.read(
                    fleet,
                    operation="refresh_status",
                    publisher_id=ticket["publisherId"],
                    ticket_id=ticket["id"],
                )["ticket"]
                return value if value["state"] == "failed" else None

            self.wait(failed)
            self.assertEqual(len(scanner.calls), before)

    def test_context_replacement_ends_old_join_and_preserves_owner_validity(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-context-") as temporary:
            fleet, _owner, _collector, scanner, _mesh, fingerprint = self.start(Path(temporary))
            entered, release = threading.Event(), threading.Event()

            def blocked(hosts, *, deadline):
                entered.set()
                release.wait(1.5)
                return scanner(hosts, deadline=deadline)

            fleet.scanner = blocked
            ticket = self.read(
                fleet,
                operation="refresh",
                sources=[{"hostId": "fixture-local", "source": "desktop"}],
            )["ticket"]
            try:
                self.assertTrue(entered.wait(2))
                fingerprint[0] += 1

                def stale():
                    frame = self.read(
                        fleet,
                        operation="refresh_status",
                        publisher_id=ticket["publisherId"],
                        ticket_id=ticket["id"],
                    )
                    return frame if frame["ticket"]["state"] == "stale_scope" else None

                frame = self.wait(stale)
                self.assertGreater(
                    frame["snapshot"]["hosts"][0]["owner"]["localExpiry"], boottime_ms()
                )
                self.assertEqual(
                    frame["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown"
                )
            finally:
                release.set()

    def test_connection_setup_has_four_remote_slots_and_single_owner_binding(self):
        fleet = FleetPublisher("fixture-local", mesh=MissingMesh())
        hosts = (MeshHost("fixture-local", "local", True, (), ()),) + tuple(
            MeshHost(
                f"remote-{i}", f"remote {i}", False, (), (MeshRoute(f"route-{i}", 0, None, None),)
            )
            for i in range(15)
        )
        snapshot = MeshSnapshot(
            "sha256:" + "a" * 64, "fixture-local", MeshPolicy("ssh", 2, 1, 300), hosts
        )
        now = boottime_ms()
        fleet.catalog_result((now, now, snapshot, None), now)
        created = []

        class Connection:
            def __init__(self, host, _now, **kwargs):
                self.state, self.closed = kwargs["state"], False
                self.state.start("test-nonce", _now)
                self.reached = self.unreachable = self.reached_reported = False
                self.route = SimpleNamespace(destination=host)
                created.append(host)

            def poll(self, _now):
                pass

        fleet.local_connection = Connection
        fleet.remote_connection = lambda host, route, _policy, now, **kwargs: Connection(
            route.destination, now, **kwargs
        )
        fleet.connection_tick(now)
        self.assertEqual(len(created), 5)
        fleet.connection_tick(now)
        self.assertEqual(len(created), 5)
        for connection in list(fleet.connections.values()):
            connection.state.transport = "ready"
        fleet.connection_tick(now)
        self.assertEqual(len(created), 9)
        self.assertEqual(len(fleet.connections), len(set(fleet.connections)))

    def test_retained_pool_reserves_before_copying_and_mesh_failure_removes_authority(self):
        fleet = FleetPublisher("fixture-local", mesh=MissingMesh())
        now = boottime_ms()
        fleet.catalog_result((now, now, None, None), now)
        fixture = (
            Path(__file__).resolve().parent.parent / "contracts/service-v1/fixtures/ready.json"
        )
        frame = json.loads(fixture.read_text())
        owner = fleet.state.owners["fixture-local"]
        connection = SimpleNamespace(state=owner)
        fleet.retained["other"] = POOL_LIMIT - 1
        with self.assertRaises(ContractError) as error:
            fleet.before_input(connection, frame, now)
        self.assertEqual(error.exception.code, "capacity")
        self.assertIsNone(owner.confirmed)
        self.assertTrue(fleet.capacity)
        fleet.catalog_failure(now, "invalid_config", "provider failed")
        view = fleet.state.view(now)
        self.assertEqual(view["mesh"]["state"], "unavailable")
        self.assertEqual(view["hosts"][0]["owner"]["localExpiry"], 0)
