"""Aggregate freshness, desktop epochs, authority failure and document caps."""

import copy
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from tmux_observer.public import validate_fleet_view
from tmux_observer_client._desktop_input import reference
from tmux_observer_client._fleet_state import FleetState


class FleetStateTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent.parent
        self.frame = json.loads((root / "contracts/service-v1/fixtures/ready.json").read_text())
        self.frame["source"]["uid"] = os.getuid()
        self.frame["snapshot"]["source"]["uid"] = os.getuid()
        self.host_id = self.frame["source"]["hostId"]
        self.state = FleetState(self.host_id, "0" * 32, self.frame["clock"])
        self.state.catalog(None)
        owner = self.state.owners[self.host_id]
        owner.start("watch", 100)
        self.frame.update(kind="resync", requestId="watch", sequence=0)
        owner.receive(self.frame, 150)

    def desktop(self, now=200):
        key = self.state.input_key(now)
        observations = {
            reference(row): {"state": "open", "confidence": "confirmed", "reason": None}
            for host in self.state.inputs(now)
            for row in host["sessions"]
        }
        return self.state.accept_desktop(
            epoch=self.state.desktop["epoch"],
            key=key,
            started=160,
            finished=180,
            now=now,
            state="ready",
            observations=observations,
            error=None,
        )

    def test_owner_and_desktop_leases_are_independent(self):
        self.assertTrue(self.desktop())
        first = self.state.view(200)
        self.assertEqual(first["hosts"][0]["sessions"][0]["localViewer"]["state"], "open")
        expiry = self.state.owners[self.host_id].expiry
        self.state.invalidate_desktop()
        view = validate_fleet_view(self.state.view(201))
        self.assertEqual(view["desktop"]["state"], "warming")
        self.assertEqual(view["hosts"][0]["owner"]["localExpiry"], expiry)
        self.assertEqual(view["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown")
        self.desktop(202)
        self.state.owners[self.host_id].fail("disconnected", "fixture")
        view = self.state.view(203)
        self.assertEqual(view["hosts"][0]["owner"]["localExpiry"], 0)
        self.assertEqual(view["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown")

    def test_old_context_input_and_late_results_never_publish_viewer_membership(self):
        epoch, key = self.state.desktop["epoch"], self.state.input_key(200)
        observations = {
            reference(row): {"state": "none", "reason": None}
            for host in self.state.inputs(200)
            for row in host["sessions"]
        }
        self.state.invalidate_desktop()
        self.assertFalse(
            self.state.accept_desktop(
                epoch=epoch,
                key=key,
                started=150,
                finished=170,
                now=200,
                state="ready",
                observations=observations,
                error=None,
            )
        )
        epoch = self.state.desktop["epoch"]
        self.assertFalse(
            self.state.accept_desktop(
                epoch=epoch,
                key=key,
                started=150,
                finished=2000,
                now=2150,
                state="ready",
                observations=observations,
                error=None,
            )
        )
        self.assertEqual(self.state.desktop["state"], "failed")
        self.assertFalse(
            self.state.accept_desktop(
                epoch=epoch,
                key="sha256:" + "f" * 64,
                started=2151,
                finished=2160,
                now=2170,
                state="ready",
                observations=observations,
                error=None,
            )
        )

    def test_missing_reference_coverage_and_owner_expiry_fail_closed(self):
        self.assertFalse(
            self.state.accept_desktop(
                epoch=self.state.desktop["epoch"],
                key=self.state.input_key(200),
                started=150,
                finished=170,
                now=200,
                state="ready",
                observations={},
                error=None,
            )
        )
        self.assertEqual(self.state.desktop["error"]["code"], "invalid_desktop")
        self.desktop()
        view = self.state.view(11000)
        self.assertEqual(view["desktop"]["state"], "expired")
        self.assertEqual(view["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown")

    def test_mesh_failure_invalidates_all_current_authority_without_local_fallback(self):
        self.desktop()
        self.state.catalog_error("invalid_config", "provider failed")
        view = self.state.view(210)
        self.assertEqual(view["mesh"]["state"], "unavailable")
        self.assertTrue(view["hosts"][0]["sessions"])
        self.assertEqual(view["hosts"][0]["owner"]["localExpiry"], 0)
        self.assertEqual(view["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown")

    def test_invalid_adapter_result_cannot_poison_accepted_state(self):
        self.desktop()
        accepted = copy.deepcopy(self.state.desktop)
        observations = {
            reference(row): {
                "state": "open",
                "confidence": "confirmed",
                "reason": None,
                "closeSafe": True,
            }
            for host in self.state.inputs(210)
            for row in host["sessions"]
        }
        self.assertFalse(
            self.state.accept_desktop(
                epoch=self.state.desktop["epoch"],
                key=self.state.input_key(210),
                started=200,
                finished=205,
                now=210,
                state="ready",
                observations=observations,
                error=None,
            )
        )
        view = self.state.view(211)
        self.assertEqual(view["desktop"]["state"], "failed")
        self.assertEqual(view["desktop"]["startedAt"], accepted["startedAt"])
        self.assertEqual(view["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown")
        self.assertTrue(self.desktop(220))

    def test_capacity_is_explicit_instead_of_truncated_complete(self):
        snapshot = SimpleNamespace(
            local_host_id=self.host_id, hosts=[None] * 17, revision="sha256:" + "a" * 64
        )
        self.assertFalse(self.state.catalog(snapshot))
        view = self.state.view(200)
        self.assertEqual(view["mesh"]["state"], "capacity")
        self.assertEqual(view["error"]["code"], "capacity")
        self.state.catalog(None)
        owner = self.state.owners[self.host_id]
        owner.confirmed = copy.deepcopy(self.frame)
        row = owner.confirmed["snapshot"]["sessions"][0]
        owner.confirmed["snapshot"]["sessions"] = [
            {**row, "sessionId": "$" + str(i), "name": "n" * 16384} for i in range(70)
        ]
        view = self.state.view(200)
        self.assertEqual(view["mesh"]["state"], "capacity")
        self.assertFalse(view["hosts"])

    def test_receipt_renewal_does_not_invent_material_revision(self):
        self.state.material(200)
        revision = self.state.revision
        owner = self.state.owners[self.host_id]
        owner.confirmed["receipt"].update(
            attempted=2,
            accepted=2,
            acceptedAttempt=2,
            startedAt=200,
            acceptedAt=220,
            lastAttemptAt=200,
            expiresAt=10200,
            remainingMs=9970,
        )
        owner.confirmed["snapshot"]["sample"].update(startedAt=200, finishedAt=210)
        owner.confirmed["encodedAt"] = 230
        owner.expiry = 10200
        self.assertFalse(self.state.material(230))
        self.assertEqual(self.state.revision, revision)
        owner.confirmed["snapshot"]["sessions"][0]["name"] = "renamed"
        self.assertTrue(self.state.material(231))

    def test_malformed_projection_is_rejected_independently_of_capacity(self):
        owner = self.state.owners[self.host_id]
        owner.confirmed["snapshot"]["sessions"][0]["attachedClients"] = "invalid"
        with self.assertRaises(ValueError):
            self.state.view(200)
