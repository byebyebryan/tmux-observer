"""Concrete Mesh/Fleet integration over owned tmux servers and real SSH."""

import threading
import unittest

import test_fleet_mesh
from native_fixture import NativeFixture

from tmux_observer._clock import boottime_ms
from tmux_observer_client.mesh_fleet import MeshFleetPublisher


class NativeMeshTests(unittest.TestCase):
    wait = test_fleet_mesh.MeshFleetTests.wait
    read = test_fleet_mesh.MeshFleetTests.read

    def test_two_hosts_passivity_refresh_restart_empty_and_cleanup(self):
        fixture = NativeFixture()
        self.addCleanup(fixture.close)
        for role in ("local", "remote"):
            fixture.native(role, "new-session", "-d", "-s", "mesh-owned-" + role, "sleep 120")
        before = {
            role: {
                "sessions": fixture.native(
                    role,
                    "list-sessions",
                    "-F",
                    "#{session_id}|#{session_created}|#{session_attached}",
                ),
                "hooks": fixture.native(role, "show-hooks"),
                "options": fixture.native(role, "show-options", "-g"),
            }
            for role in ("local", "remote")
        }
        local_owner, _ = fixture.start_owner("local")
        remote_owner, _ = fixture.start_owner("remote")
        fixture.start_ssh()
        authority = test_fleet_mesh.Authority()
        authority.payload["sshPolicy"]["executable"] = str(fixture.bin / "ssh")
        authority.payload["hosts"].append(
            {
                "id": "fixture-remote",
                "display": "remote",
                "local": False,
                "aliases": [],
                "routes": [
                    {
                        "destination": "fixture-remote",
                        "configuredIndex": 0,
                        "lastReachableAt": None,
                        "lastUnreachableAt": None,
                    }
                ],
            }
        )

        async def report_route(**_kwargs):
            return True

        authority.report_route = report_route
        fleet = MeshFleetPublisher(
            "fixture-local",
            path=fixture.local / "fleet.sock",
            owner_path=fixture.local / "owner.sock",
            authority=authority,
            scanner=False,
            remote_exec=str(fixture.bin / "tmux-observer"),
        )
        errors = []

        def run():
            try:
                fleet.run()
            except Exception as error:  # noqa: BLE001 - report all owned thread failures
                errors.append(error)

        thread = threading.Thread(target=run)
        thread.start()

        def cleanup():
            fleet.stop()
            thread.join(10)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors, errors)

        self.addCleanup(cleanup)

        def ready():
            frame = self.read(fleet)
            self.last_view = frame["snapshot"]
            hosts = frame["snapshot"]["hosts"]
            return (
                frame
                if len(hosts) == 2
                and all(host["owner"]["localExpiry"] > boottime_ms() for host in hosts)
                else None
            )

        try:
            first = self.wait(ready, budget=8)
        except AssertionError as error:
            raise AssertionError(
                {
                    "view": self.last_view,
                    "sshd": (fixture.root / "sshd.log").read_text()[-1024:],
                    "mesh": (fixture.root / "mesh.log").read_text()[-2048:]
                    if (fixture.root / "mesh.log").exists()
                    else None,
                }
            ) from error
        self.assertIsNotNone(first["snapshot"]["hosts"][1]["owner"]["proof"])
        for _ in range(10):
            self.read(fleet)
        for role in ("local", "remote"):
            self.assertEqual(
                fixture.native(
                    role,
                    "list-sessions",
                    "-F",
                    "#{session_id}|#{session_created}|#{session_attached}",
                ),
                before[role]["sessions"],
            )
            self.assertEqual(fixture.native(role, "show-hooks"), before[role]["hooks"])
            self.assertEqual(fixture.native(role, "show-options", "-g"), before[role]["options"])
            self.assertEqual(fixture.native(role, "list-clients", "-F", "#{client_pid}"), b"")
        ticket = self.read(
            fleet, operation="refresh", sources=[{"hostId": "fixture-remote", "source": "owner"}]
        )["ticket"]

        def terminal():
            frame = self.read(
                fleet,
                operation="refresh_status",
                publisher_id=ticket["publisherId"],
                ticket_id=ticket["id"],
            )
            return frame if frame["ticket"]["state"] in ("complete", "failed", "deadline") else None

        complete = self.wait(terminal, budget=8)
        self.assertEqual(complete["ticket"]["state"], "complete", complete["ticket"])
        remote = complete["snapshot"]["hosts"][1]
        self.assertGreaterEqual(remote["owner"]["proof"]["sentAt"], ticket["requestedAt"])
        publisher = remote["owner"]["publisherId"]
        remote_owner.terminate()
        remote_owner.wait(3)

        def unavailable():
            frame = self.read(fleet)
            host = frame["snapshot"]["hosts"][1]
            return frame if host["owner"]["localExpiry"] == 0 and host["sessions"] else None

        self.wait(unavailable, budget=5)
        fixture.start_owner("remote")

        def restarted():
            frame = ready()
            return (
                frame
                if frame and frame["snapshot"]["hosts"][1]["owner"]["publisherId"] != publisher
                else None
            )

        self.wait(restarted, budget=8)
        fixture.native("remote", "kill-server")

        def empty():
            frame = ready()
            host = frame["snapshot"]["hosts"][1] if frame else None
            return (
                frame
                if host and not host["sessions"] and host["owner"]["serverGeneration"] is None
                else None
            )

        self.wait(empty, budget=6)
        self.assertEqual(fixture.native("remote", "list-sessions", ok=False), b"")
        self.assertIsNone(local_owner.poll())
