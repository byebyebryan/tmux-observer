"""Concrete Mesh/Fleet integration over owned tmux servers and real SSH."""

import json
import threading
import unittest
from unittest.mock import patch

import test_fleet_mesh
from native_fixture import NativeFixture

from tmux_observer._clock import boottime_ms
from tmux_observer_client import _mesh_worker
from tmux_observer_client.mesh_fleet import MeshFleetPublisher


class NativeMeshTests(unittest.TestCase):
    setUp = test_fleet_mesh.MeshFleetTests.setUp
    wait = test_fleet_mesh.MeshFleetTests.wait
    read = test_fleet_mesh.MeshFleetTests.read

    def test_two_hosts_passivity_refresh_restart_empty_and_cleanup(self):
        self._run_two_hosts_passivity_refresh_restart_empty_and_cleanup()

    def test_view_feed_two_hosts_passivity_refresh_restart_empty_and_cleanup(self):
        self._run_two_hosts_passivity_refresh_restart_empty_and_cleanup(view_feed=True)

    def _run_two_hosts_passivity_refresh_restart_empty_and_cleanup(self, *, view_feed=False):
        fixture = NativeFixture()
        self.addCleanup(fixture.close)
        factories = []
        original_factory = _mesh_worker.make_publisher

        def local_factory(host, source, socket):
            factories.append((host, source))
            return original_factory(host, source, socket)

        factory_patch = patch.object(_mesh_worker, "make_publisher", local_factory)
        factory_patch.start()
        self.addCleanup(factory_patch.stop)
        for role in ("local", "remote"):
            if not (view_feed and role == "remote"):
                fixture.native(role, "new-session", "-d", "-s", "mesh-owned-" + role, "sleep 120")
        before = {
            role: {
                "sessions": fixture.native(
                    role,
                    "list-sessions",
                    "-F",
                    "#{session_id}|#{session_created}|#{session_attached}",
                    ok=not (view_feed and role == "remote"),
                ),
                "hooks": None
                if view_feed and role == "remote"
                else fixture.native(role, "show-hooks"),
                "options": None
                if view_feed and role == "remote"
                else fixture.native(role, "show-options", "-g"),
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
            view_feed=view_feed,
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
        self.assertEqual(factories, [("fixture-local", "tmux_default")])
        if fixture.publisher_mode == "owned":
            commands = [
                json.loads(line)
                for line in (fixture.root / "mesh-commands.jsonl").read_text().splitlines()
            ]
            remote_commands = [
                command
                for command in commands
                if command and command[0] in {"bridge", "view-feed-bridge"}
            ]
            expected_command = "view-feed-bridge" if view_feed else "bridge"
            self.assertTrue(remote_commands)
            self.assertTrue(
                all(
                    command[0] == expected_command and "--stdio" in command
                    for command in remote_commands
                ),
                remote_commands,
            )
            remote_factories = [
                json.loads(line)
                for line in (fixture.root / "factory.jsonl").read_text().splitlines()
            ]
            self.assertTrue(remote_factories)
            self.assertTrue(
                all(
                    row == {"host": "fixture-remote", "source": "tmux_default"}
                    for row in remote_factories
                )
            )
        if view_feed:
            initial_remote = first["snapshot"]["hosts"][1]
            initial_rows = initial_remote["sessions"]
            self.assertEqual(initial_rows, [])
            initial_proof = initial_remote["owner"]["proof"]["sentAt"]
            initial_expiry = initial_remote["owner"]["localExpiry"]

            def renewed_without_session_change():
                frame = self.read(fleet)
                remote = frame["snapshot"]["hosts"][1]
                return (
                    frame
                    if remote["sessions"] == initial_rows
                    and remote["owner"]["proof"]["sentAt"] > initial_proof
                    and remote["owner"]["localExpiry"] > initial_expiry
                    else None
                )

            self.wait(renewed_without_session_change, budget=7)
            fixture.native("remote", "new-session", "-d", "-s", "mesh-owned-remote", "sleep 120")
            initial_id = (
                fixture.native(
                    "remote", "display-message", "-p", "-t", "mesh-owned-remote", "#{session_id}"
                )
                .decode()
                .strip()
            )

            def seeded():
                frame = self.read(fleet)
                rows = frame["snapshot"]["hosts"][1]["sessions"]
                return frame if [row["sessionId"] for row in rows] == [initial_id] else None

            seeded_frame = self.wait(seeded, budget=7)
            initial_rows = seeded_frame["snapshot"]["hosts"][1]["sessions"]
            before["remote"].update(
                sessions=fixture.native(
                    "remote",
                    "list-sessions",
                    "-F",
                    "#{session_id}|#{session_created}|#{session_attached}",
                ),
                hooks=fixture.native("remote", "show-hooks"),
                options=fixture.native("remote", "show-options", "-g"),
            )
            for name in ("mesh-feed-z", "mesh-feed-a"):
                fixture.native("remote", "new-session", "-d", "-s", name, "sleep 120")
            native_order = fixture.native("remote", "list-sessions", "-F", "#{session_id}")
            native_order = native_order.decode().splitlines()
            renamed_id = (
                fixture.native(
                    "remote", "display-message", "-p", "-t", "mesh-feed-a", "#{session_id}"
                )
                .decode()
                .strip()
            )

            def inserted():
                frame = self.read(fleet)
                rows = frame["snapshot"]["hosts"][1]["sessions"]
                return frame if [row["sessionId"] for row in rows] == native_order else None

            inserted_frame = self.wait(inserted, budget=7)
            inserted_rows = inserted_frame["snapshot"]["hosts"][1]["sessions"]
            self.assertEqual(
                sorted(row["name"] for row in inserted_rows),
                ["mesh-feed-a", "mesh-feed-z", "mesh-owned-remote"],
            )
            fixture.native("remote", "rename-session", "-t", "mesh-feed-a", "mesh-feed-renamed")

            def metadata_changed():
                frame = self.read(fleet)
                rows = frame["snapshot"]["hosts"][1]["sessions"]
                return (
                    frame
                    if [row["sessionId"] for row in rows] == native_order
                    and next(row for row in rows if row["sessionId"] == renamed_id)["name"]
                    == "mesh-feed-renamed"
                    else None
                )

            self.wait(metadata_changed, budget=7)
            fixture.native("remote", "kill-session", "-t", "mesh-feed-z")
            fixture.native("remote", "kill-session", "-t", "mesh-feed-renamed")

            def removed():
                frame = self.read(fleet)
                rows = frame["snapshot"]["hosts"][1]["sessions"]
                return frame if rows == initial_rows else None

            self.wait(removed, budget=7)
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
            local = frame["snapshot"]["hosts"][0]
            return (
                frame
                if host["owner"]["localExpiry"] == 0
                and host["sessions"]
                and local["owner"]["localExpiry"] > boottime_ms()
                else None
            )

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
        current = self.read(fleet)
        old_generation = current["snapshot"]["hosts"][1]["owner"]["serverGeneration"]
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
        fixture.native("remote", "new-session", "-d", "-s", "mesh-feed-reborn", "sleep 120")

        def reborn():
            frame = ready()
            host = frame["snapshot"]["hosts"][1] if frame else None
            return (
                frame
                if host
                and host["owner"]["serverGeneration"] != old_generation
                and len(host["sessions"]) == 1
                else None
            )

        self.wait(reborn, budget=8)
        self.assertIsNone(local_owner.poll())
