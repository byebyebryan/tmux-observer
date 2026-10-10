"""Explicit Mesh integration gate; uses real IPC with owned synthetic publishers."""

import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path

import test_owner
from mesh_plus.catalog import Catalog
from test_fleet import Scanner

from tmux_observer._clock import boottime_ms
from tmux_observer._ipc import IPCError
from tmux_observer_client.contract import validate_fleet_frame
from tmux_observer_client.mesh_fleet import MeshFleetPublisher
from tmux_observer_client.public import read_cached


class Authority:
    def __init__(self):
        self.calls = 0
        self.failed = False
        self.payload = {
            "schemaVersion": 1,
            "generatedAt": 1,
            "meshRevision": "sha256:" + "a" * 64,
            "localHostId": "fixture-local",
            "sshPolicy": {
                "executable": "ssh",
                "connectTimeoutSeconds": 2,
                "connectionAttempts": 1,
                "routeHealthTtlSeconds": 300,
            },
            "hosts": [
                {
                    "id": "fixture-local",
                    "display": "fixture",
                    "local": True,
                    "aliases": [],
                    "routes": [],
                }
            ],
        }

    async def load(self):
        self.calls += 1
        if self.failed:
            raise ValueError("fixture authority unavailable")
        return Catalog(copy.deepcopy(self.payload))


class MeshFleetTests(unittest.TestCase):
    def wait(self, check, budget=5):
        until = time.monotonic() + budget
        while time.monotonic() < until:
            try:
                value = check()
            except IPCError:
                value = None
            if value:
                return value
            time.sleep(0.01)
        self.fail("owned Mesh fleet condition did not complete")

    def start(self, root):
        owner, owner_thread, collector = test_owner.OwnerTests().start(root / "owner.sock")
        authority, scanner = Authority(), Scanner()
        fleet = MeshFleetPublisher(
            "fixture-local",
            path=root / "fleet.sock",
            owner_path=root / "owner.sock",
            scanner=scanner,
            authority=authority,
        )
        errors = []

        def run():
            try:
                fleet.run()
            except Exception as error:  # noqa: BLE001 - surface owned thread failures
                errors.append(error)

        thread = threading.Thread(target=run)
        thread.start()

        def cleanup():
            fleet.stop()
            thread.join(10)
            owner.stop()
            owner_thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors, errors)

        self.addCleanup(cleanup)

        def ready():
            frame = self.read(fleet)
            view = frame["snapshot"]
            return (
                frame
                if (
                    view["mesh"]["state"] == "ready"
                    and view["desktop"]["state"] == "ready"
                    and view["hosts"][0]["owner"]["localExpiry"] > boottime_ms()
                )
                else None
            )

        self.wait(ready)
        return fleet, owner, collector, scanner, authority

    def read(self, fleet, **kwargs):
        return validate_fleet_frame(
            read_cached(
                fleet.state.context_id, path=fleet.path, expected_host="fixture-local", **kwargs
            )
        )

    def test_cached_reads_share_one_mesh_reader_and_never_schedule_collection(self):
        with tempfile.TemporaryDirectory(prefix="tmux-mesh-test-") as temporary:
            fleet, _owner, collector, scanner, authority = self.start(Path(temporary))
            before = collector.calls, len(scanner.calls), authority.calls
            for operation in ("snapshot", "status", "probe") * 5:
                self.read(fleet, operation=operation)
            self.assertEqual((collector.calls, len(scanner.calls), authority.calls), before)
            self.assertTrue(all(c.future is None for c in fleet.connections.values()))

    def test_grouped_refresh_requires_mesh_confirmed_native_attempt(self):
        with tempfile.TemporaryDirectory(prefix="tmux-mesh-refresh-") as temporary:
            fleet, _owner, _collector, _scanner, _authority = self.start(Path(temporary))
            ticket = self.read(
                fleet,
                operation="refresh",
                sources=[
                    {"hostId": "fixture-local", "source": source} for source in ("owner", "desktop")
                ],
            )["ticket"]

            def terminal():
                frame = self.read(
                    fleet,
                    operation="refresh_status",
                    publisher_id=ticket["publisherId"],
                    ticket_id=ticket["id"],
                )
                return (
                    frame
                    if frame["ticket"]["state"] in ("complete", "failed", "deadline")
                    else None
                )

            frame = self.wait(terminal)
            self.assertEqual(frame["ticket"]["state"], "complete", frame["ticket"])
            source = frame["snapshot"]["hosts"][0]["owner"]["receipt"]
            self.assertGreaterEqual(source["startedAt"], ticket["requestedAt"])
            self.assertGreaterEqual(frame["snapshot"]["desktop"]["startedAt"], source["acceptedAt"])

    def test_authority_loss_retains_metadata_with_no_current_viewer(self):
        with tempfile.TemporaryDirectory(prefix="tmux-mesh-catalog-") as temporary:
            fleet, _owner, _collector, _scanner, authority = self.start(Path(temporary))
            authority.failed = True

            def failed():
                frame = self.read(fleet)
                return frame if frame["snapshot"]["mesh"]["state"] == "unavailable" else None

            frame = self.wait(failed, budget=7)
            host = frame["snapshot"]["hosts"][0]
            self.assertEqual(host["owner"]["localExpiry"], 0)
            self.assertTrue(host["sessions"])
            self.assertEqual(host["sessions"][0]["localViewer"]["state"], "unknown")

    def test_seventeenth_owner_reports_capacity_retains_history_and_recovers(self):
        with tempfile.TemporaryDirectory(prefix="tmux-mesh-capacity-") as temporary:
            fleet, _owner, _collector, _scanner, authority = self.start(Path(temporary))
            original = copy.deepcopy(authority.payload)
            authority.payload["hosts"].extend(
                {
                    "id": f"fixture-{index:02d}",
                    "display": f"Fixture {index}",
                    "local": False,
                    "aliases": [],
                    "routes": [
                        {
                            "destination": f"fixture-{index:02d}",
                            "configuredIndex": 0,
                            "lastReachableAt": None,
                            "lastUnreachableAt": None,
                        }
                    ],
                }
                for index in range(16)
            )
            authority.payload["meshRevision"] = "sha256:" + "b" * 64

            def capacity():
                frame = self.read(fleet)
                return frame if frame["snapshot"]["mesh"]["state"] == "capacity" else None

            frame = self.wait(capacity, budget=9)
            self.assertEqual(frame["snapshot"]["error"]["code"], "capacity")
            self.assertEqual(len(frame["snapshot"]["hosts"]), 1)
            self.assertTrue(frame["snapshot"]["hosts"][0]["sessions"])
            self.assertEqual(frame["snapshot"]["hosts"][0]["owner"]["localExpiry"], 0)
            authority.payload = original

            def recovered():
                frame = self.read(fleet)
                return (
                    frame
                    if frame["snapshot"]["mesh"]["state"] == "ready"
                    and frame["snapshot"]["hosts"][0]["owner"]["localExpiry"] > boottime_ms()
                    else None
                )

            self.wait(recovered, budget=9)


if __name__ == "__main__":
    unittest.main()
