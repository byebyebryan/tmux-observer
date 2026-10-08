"""Composed owner/fleet recovery with independent clocks and withheld callbacks."""

import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tmux_observer._owner_state import OwnerState
from tmux_observer.public import validate_fleet_frame
from tmux_observer_client._desktop_input import reference
from tmux_observer_client._errors import ContractError
from tmux_observer_client.fleet import FleetPublisher
from tmux_observer_client.mesh import MeshHost, MeshPolicy, MeshRoute, MeshSnapshot
from tmux_observer_client.public import owner_current


class RecoverySimulationTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).resolve().parent.parent / "contracts/observation-v1/fixtures"
        self.template = json.loads((fixture / "complete.json").read_text())
        self.template["source"]["uid"] = os.getuid()
        self.now = 100_000
        self.native = {}
        self.owners = {}
        for host, offset in (("fixture-local", 0), ("fixture-remote", 900_000)):
            sample = copy.deepcopy(self.template)
            sample["source"].update(hostId=host, nativeHostname=host)
            if offset:
                sample["clock"]["bootId"] = "22222222-2222-4222-8222-222222222222"
            for row in sample["sessions"]:
                row.update(hostId=host, attachedClients=1)
            self.native[host] = sample
            owner = OwnerState(sample["source"], sample["clock"])
            self.owners[host] = owner
            self.collect(host, self.now + offset)
        with patch("tmux_observer_client.fleet.domain", return_value=self.template["clock"]):
            self.fleet = FleetPublisher("fixture-local", fingerprint=lambda _context: 0)
        hosts = (
            MeshHost("fixture-local", "local", True, (), ()),
            MeshHost(
                "fixture-remote", "remote", False, (), (MeshRoute("remote-route", 0, None, None),)
            ),
        )
        mesh = MeshSnapshot(
            "sha256:" + "a" * 64, "fixture-local", MeshPolicy("ssh", 2, 1, 300), hosts
        )
        self.fleet.catalog_result((self.now, self.now, mesh, None), self.now)
        self.join_owner("fixture-local", self.now + 130, self.now + 130)
        self.join_owner("fixture-remote", self.now + 900_130, self.now + 130)
        self.prove_remote(self.now + 900_150, self.now + 150)
        self.scan(self.now + 180)
        self.original = self.read(self.now + 210)
        self.assertTrue(all(self.current(self.original, host) for host in self.original["hosts"]))
        self.assertTrue(
            all(row["localViewer"]["state"] == "open" for row in self.rows(self.original))
        )

    def collect(self, host, started):
        owner = self.owners[host]
        sample = copy.deepcopy(self.native[host])
        sample["sample"].update(startedAt=started, finishedAt=started + 20)
        self.assertTrue(owner.finish(owner.begin(started), sample, started + 25))
        return sample

    def join_owner(self, host, encoded, received):
        remote = self.fleet.state.owners[host]
        nonce = "watch-" + host
        remote.start(nonce, received - 10)
        remote.receive(
            self.owners[host].frame(encoded, kind="resync", sequence=0, request_id=nonce), received
        )
        if host == "fixture-remote":
            remote.selected_route = "remote-route"

    def prove_remote(self, encoded, sent):
        remote = self.fleet.state.owners["fixture-remote"]
        request = remote.probe(sent)
        self.assertIsNotNone(request)
        value = self.owners["fixture-remote"].frame(
            encoded, sequence=remote.sequence + 1, request_id=request["requestId"]
        )
        remote.receive(value, sent + 10)

    def scan(self, started):
        state = self.fleet.state
        observations = {
            reference(row): {"state": "open", "confidence": "confirmed", "reason": None}
            for host in state.inputs(started)
            for row in host["sessions"]
        }
        self.assertTrue(
            state.accept_desktop(
                epoch=state.desktop["epoch"],
                key=state.input_key(started),
                started=started,
                finished=started + 10,
                now=started + 20,
                state="ready",
                observations=observations,
                error=None,
            )
        )

    def read(self, now):
        return validate_fleet_frame(self.fleet.frame(now, kind="status"))["snapshot"]

    @staticmethod
    def rows(view):
        return [row for host in view["hosts"] for row in host["sessions"]]

    @staticmethod
    def current(view, host):
        return owner_current(view, host, now=view["encodedAt"])

    def test_peer_silence_and_buffered_heartbeat_do_not_hide_expiry_or_block_local(self):
        now = self.now + 30_000
        self.collect("fixture-local", now)
        local = self.fleet.state.owners["fixture-local"]
        local.receive(self.owners["fixture-local"].frame(now + 30, sequence=1), now + 30)
        remote = self.fleet.state.owners["fixture-remote"]
        heartbeat = self.owners["fixture-remote"].frame(
            self.now + 900_200, kind="heartbeat", sequence=2
        )
        # The packet was prepared before the outage and delivered after it.
        remote.receive(heartbeat, now + 30)
        self.scan(now + 40)
        first = self.read(now + 70)
        local_host, remote_host = first["hosts"]
        self.assertTrue(self.current(first, local_host))
        self.assertFalse(self.current(first, remote_host))
        self.assertEqual(local_host["sessions"][0]["localViewer"]["state"], "open")
        self.assertEqual(remote_host["sessions"][0]["localViewer"]["state"], "unknown")
        self.assertEqual(
            reference(remote_host["sessions"][0]),
            reference(self.original["hosts"][1]["sessions"][0]),
        )
        # A recovered transport has to prove newly collected facts, then renew the join.
        self.collect("fixture-remote", now + 900_080)
        self.join_owner("fixture-remote", now + 900_110, now + 110)
        unproved = self.read(now + 115)
        self.assertFalse(self.current(unproved, unproved["hosts"][1]))
        self.prove_remote(now + 900_120, now + 120)
        renewed = self.read(now + 135)
        self.assertTrue(self.current(renewed, renewed["hosts"][1]))
        self.assertEqual(renewed["hosts"][1]["sessions"][0]["localViewer"]["state"], "unknown")
        self.scan(now + 140)
        self.assertEqual(
            self.read(now + 170)["hosts"][1]["sessions"][0]["localViewer"]["state"], "open"
        )

    def test_first_read_after_paused_callbacks_rejects_history_and_late_work(self):
        remote = self.fleet.state.owners["fixture-remote"]
        sent = self.now + 4000
        request = remote.probe(sent)
        buffered = self.owners["fixture-remote"].frame(
            sent + 900_000, sequence=2, request_id=request["requestId"]
        )
        local_owner = self.owners["fixture-local"]
        token = local_owner.begin(sent)
        late_native = copy.deepcopy(self.native["fixture-local"])
        late_native["sample"].update(startedAt=sent, finishedAt=sent + 20)
        desktop = copy.deepcopy(self.fleet.state.desktop)
        viewers = copy.deepcopy(self.fleet.state.viewers)
        # No scheduler/probe/desktop callbacks run across this 30-second gap.
        now = sent + 30_000
        first = self.read(now)
        self.assertEqual(first["desktop"]["state"], "expired")
        self.assertTrue(all(not self.current(first, host) for host in first["hosts"]))
        self.assertTrue(all(row["localViewer"]["state"] == "unknown" for row in self.rows(first)))
        self.assertEqual(
            [reference(row) for row in self.rows(first)],
            [reference(row) for row in self.rows(self.original)],
        )
        with self.assertRaises(ContractError):
            remote.receive(buffered, now)
        self.assertEqual(remote.expiry, 0)
        self.assertFalse(local_owner.finish(token, late_native, now))
        self.assertEqual(local_owner.frame(now)["receipt"]["accepted"], 1)
        self.assertFalse(
            self.fleet.state.accept_desktop(
                epoch=desktop["epoch"],
                key=desktop["inputHash"],
                started=sent,
                finished=sent + 20,
                now=now,
                state="ready",
                observations=viewers,
                error=None,
            )
        )
        self.collect("fixture-local", now + 10)
        local = self.fleet.state.owners["fixture-local"]
        local.receive(self.owners["fixture-local"].frame(now + 40, sequence=1), now + 40)
        self.collect("fixture-remote", now + 900_010)
        self.join_owner("fixture-remote", now + 900_040, now + 40)
        self.prove_remote(now + 900_050, now + 50)
        before_scan = self.read(now + 70)
        self.assertTrue(all(self.current(before_scan, host) for host in before_scan["hosts"]))
        self.assertTrue(
            all(row["localViewer"]["state"] == "unknown" for row in self.rows(before_scan))
        )
        self.scan(now + 80)
        after = self.read(now + 110)
        self.assertTrue(all(row["localViewer"]["state"] == "open" for row in self.rows(after)))
        self.assertEqual(
            [reference(row) for row in self.rows(after)],
            [reference(row) for row in self.rows(self.original)],
        )
