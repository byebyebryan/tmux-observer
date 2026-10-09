"""Projection work reduction preserves lease boundaries and publication order."""

import copy
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from tmux_observer.public import validate_fleet_frame
from tmux_observer_client._desktop_input import input_hash, reference
from tmux_observer_client._fleet_state import FleetState
from tmux_observer_client._fleet_tickets import FleetTickets
from tmux_observer_client.fleet import FleetPublisher


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent.parent
        self.owner_frame = json.loads(
            (root / "contracts/service-v1/fixtures/ready.json").read_text()
        )
        self.owner_frame["source"]["uid"] = os.getuid()
        self.owner_frame["snapshot"]["source"]["uid"] = os.getuid()
        self.host = self.owner_frame["source"]["hostId"]
        self.fleet = FleetPublisher(self.host)
        state = FleetState(self.host, "0" * 32, self.owner_frame["clock"])
        state.catalog(None)
        self.fleet.state = state
        self.fleet.tickets = FleetTickets(state)
        owner = state.owners[self.host]
        owner.start("owned-watch", 100)
        self.owner_frame.update(kind="resync", requestId="owned-watch", sequence=0)
        owner.receive(self.owner_frame, 150)
        observations = {
            reference(row): {"state": "none", "reason": None}
            for host in state.inputs(200)
            for row in host["sessions"]
        }
        self.assertTrue(
            state.accept_desktop(
                epoch=state.desktop["epoch"],
                key=state.input_key(200),
                started=160,
                finished=180,
                now=200,
                state="ready",
                observations=observations,
                error=None,
            )
        )
        self.fleet.state.material = Mock(wraps=state.material)

    def frame(self, now):
        return validate_fleet_frame(self.fleet.frame(now))

    def test_stable_ticks_skip_projection_but_reads_remain_validated(self):
        first = self.frame(200)
        self.fleet.publish_needed = False
        for now in range(201, 301):
            self.fleet.project_changed(now)
            frame = self.frame(now)
            self.assertEqual(frame["viewRevision"], first["viewRevision"])
            self.assertEqual(frame["encodedAt"], now)
            self.assertEqual(
                frame["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "none"
            )
        self.assertEqual(self.fleet.state.material.call_count, 1)
        self.assertFalse(self.fleet.publish_needed)

    def test_read_at_lease_expiry_updates_revision_and_keeps_watcher_publication_pending(self):
        first = self.frame(200)
        self.fleet.publish_needed = False
        expired = self.frame(10100)
        row = expired["snapshot"]["hosts"][0]["sessions"][0]
        self.assertEqual(row["localViewer"]["state"], "unknown")
        self.assertGreater(expired["viewRevision"], first["viewRevision"])
        self.assertTrue(self.fleet.publish_needed)
        # The read cannot consume the broadcast needed by existing watchers.
        self.fleet.project_changed(10101)
        self.assertTrue(self.fleet.publish_needed)
        desktop_expired = self.frame(10160)
        self.assertEqual(desktop_expired["snapshot"]["desktop"]["state"], "expired")
        self.assertGreater(desktop_expired["viewRevision"], expired["viewRevision"])
        self.assertIsNone(self.fleet.projection_expiry)

    def test_validated_owner_update_invalidates_projection_and_old_desktop_join(self):
        before = self.fleet.current_input_key(200)
        first = self.frame(200)
        value = copy.deepcopy(self.owner_frame)
        value.update(kind="view", sequence=1, requestId=None, encodedAt=1130, viewRevision=2)
        value["snapshot"]["sessions"][0]["name"] = "renamed"
        value["snapshot"]["sample"].update(startedAt=1100, finishedAt=1120)
        value["receipt"].update(
            attempted=2,
            accepted=2,
            acceptedAttempt=2,
            startedAt=1100,
            acceptedAt=1125,
            expiresAt=11100,
            lastAttemptAt=1100,
            remainingMs=9970,
        )
        owner = self.fleet.state.owners[self.host]
        matched = owner.receive(value, 1150)
        self.fleet.owner_frame(SimpleNamespace(state=owner), value, matched, 1150)
        changed = self.frame(1150)
        self.assertNotEqual(self.fleet.current_input_key(1150), before)
        self.assertGreater(changed["viewRevision"], first["viewRevision"])
        self.assertEqual(changed["snapshot"]["hosts"][0]["sessions"][0]["name"], "renamed")
        self.assertEqual(changed["snapshot"]["desktop"]["state"], "warming")

    def test_disconnection_invalidates_positives_without_waiting_for_old_expiry(self):
        self.assertNotEqual(self.fleet.current_input_key(200), input_hash([]))
        first = self.frame(200)
        owner = self.fleet.state.owners[self.host]
        self.fleet.connections[self.host] = SimpleNamespace(state=owner, fail=owner.fail)
        self.fleet.disconnect(300)
        failed = self.frame(300)
        self.assertEqual(self.fleet.current_input_key(300), input_hash([]))
        self.assertGreater(failed["viewRevision"], first["viewRevision"])
        host = failed["snapshot"]["hosts"][0]
        self.assertEqual(host["owner"]["localExpiry"], 0)
        self.assertEqual(host["sessions"][0]["localViewer"]["state"], "unknown")

    def test_scheduler_reuses_input_hash_but_invalidates_at_owner_expiry(self):
        self.fleet.fingerprint = lambda _: self.fleet.context_fingerprint
        self.fleet.last_desktop_start = 10**12
        self.fleet.desktop_input = self.fleet.state.input_key(200)
        self.fleet.state.input_key = Mock(wraps=self.fleet.state.input_key)
        executor = Mock()
        for now in range(201, 301):
            self.fleet.desktop_tick(executor, now)
        self.assertEqual(self.fleet.state.input_key.call_count, 1)
        self.fleet.desktop_tick(executor, 10100)
        self.assertEqual(self.fleet.current_input_key(10100), input_hash([]))
        self.assertEqual(self.fleet.state.input_key.call_count, 2)
        executor.submit.assert_not_called()

    def test_published_mutation_cannot_change_retained_projection(self):
        first = self.frame(200)
        first["snapshot"]["hosts"][0]["sessions"][0]["localViewer"] = {
            "state": "open",
            "confidence": "confirmed",
            "reason": None,
        }
        first["snapshot"]["desktop"]["expiresAt"] = 10**12
        next_frame = self.frame(201)
        self.assertEqual(
            next_frame["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "none"
        )
        expired = self.frame(10160)
        self.assertEqual(expired["snapshot"]["desktop"]["state"], "expired")
        self.assertEqual(
            expired["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown"
        )

    def test_prepared_reads_reuse_input_hash_until_dependency_expiry(self):
        self.fleet.state.input_key = Mock(wraps=self.fleet.state.input_key)
        for now in range(200, 301):
            self.frame(now)
        self.assertEqual(self.fleet.state.input_key.call_count, 1)
        frame = self.frame(10100)
        self.assertEqual(self.fleet.state.input_key.call_count, 2)
        self.assertEqual(
            frame["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown"
        )

    def test_new_owner_hashed_by_scheduler_is_not_hashed_again_by_projection(self):
        self.frame(200)
        owner = self.fleet.state.owners[self.host]
        value = copy.deepcopy(self.owner_frame)
        value.update(kind="heartbeat", sequence=1, requestId=None, encodedAt=220)
        value["receipt"]["remainingMs"] = value["receipt"]["expiresAt"] - 220
        matched = owner.receive(value, 220)
        self.fleet.owner_frame(SimpleNamespace(state=owner), value, matched, 220)
        self.fleet.state.input_key = Mock(wraps=self.fleet.state.input_key)
        self.fleet.current_input_key(220)
        frame = self.frame(221)
        self.assertEqual(self.fleet.state.input_key.call_count, 1)
        self.assertEqual(frame["snapshot"]["hosts"][0]["owner"]["encodedAt"], 220)
