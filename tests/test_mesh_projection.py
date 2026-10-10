"""Fleet compatibility retains original native evidence across Mesh delivery."""

import copy
import json
import os
import unittest
from pathlib import Path

from tmux_observer_client._mesh_projection import MeshOwnerState


class MeshProjectionTests(unittest.TestCase):
    def setUp(self):
        self.frame = json.loads(
            (
                Path(__file__).resolve().parent.parent / "contracts/service-v1/fixtures/ready.json"
            ).read_text()
        )
        self.frame["source"]["uid"] = os.getuid()
        self.frame["snapshot"]["source"]["uid"] = os.getuid()
        self.clock = self.frame["clock"]
        self.host_id = self.frame["source"]["hostId"]

    def outcome(self, *, local=True):
        frame = copy.deepcopy(self.frame)
        return {
            "hostId": self.host_id,
            "local": local,
            "delivery": {
                "status": "ready",
                "epoch": 1,
                "error": None,
                "proof": None
                if local
                else {
                    "nonce": "a" * 32,
                    "bridgeEncodedAtMs": 150,
                    "sentAtMs": 1000,
                    "receivedAtMs": 1020,
                    "marginMs": 100,
                },
            },
            "owner": {
                "metadata": {
                    key: value for key, value in frame["snapshot"].items() if key != "sessions"
                },
                "service": {key: value for key, value in frame.items() if key != "snapshot"},
            },
            "receipts": [
                {
                    "sourceId": "default",
                    "component": "native",
                    "accepted": 1,
                    "health": "current",
                    "expiresAtMs": 10100 if local else 10850,
                }
            ],
        }, frame["snapshot"]["sessions"]

    def accept(self, state, host, rows, *, now=200):
        state.accept_mesh(
            host,
            rows,
            reader_id="reader",
            reader_clock=self.clock,
            now=now,
            selected_route=None if host["local"] else "route",
        )

    def test_local_delivery_and_repeated_reads_do_not_renew_native_evidence(self):
        state = MeshOwnerState(self.host_id, local_clock=self.clock)
        host, rows = self.outcome()
        self.accept(state, host, rows)
        revision = state.fact_revision
        self.accept(state, host, rows, now=300)
        self.assertEqual(state.expiry, 10100)
        self.assertEqual(state.fact_revision, revision)
        self.assertEqual(state.confirmed["receipt"], self.frame["receipt"])
        self.accept(state, host, rows, now=10101)
        self.assertEqual(state.expiry, 0)
        self.assertEqual(len(state.project()[1]), 1)

    def test_remote_proof_reencodes_only_the_header_in_the_source_clock(self):
        state = MeshOwnerState(self.host_id)
        host, rows = self.outcome(local=False)
        self.accept(state, host, rows, now=1050)
        projected = state.project_header()
        self.assertEqual(projected["encodedAt"], 150)
        self.assertEqual(projected["receipt"]["remainingMs"], 9950)
        self.assertEqual(projected["proof"]["remainingMs"], 9950)
        self.assertEqual(state.confirmed["encodedAt"], 130)
        self.assertEqual(state.confirmed["receipt"]["expiresAt"], 10100)
        self.assertEqual(state.expiry, 10850)

    def test_outage_retains_descriptors_but_revokes_validity_and_scope(self):
        state = MeshOwnerState(self.host_id, local_clock=self.clock)
        host, rows = self.outcome()
        self.accept(state, host, rows)
        epoch = state.epoch
        host.update(owner=None, receipts=[])
        host["delivery"].update(
            status="unavailable", error={"code": "disconnected", "message": "fixture"}
        )
        self.accept(state, host, [])
        self.assertEqual(state.expiry, 0)
        self.assertIsNone(state.scope)
        self.assertGreater(state.epoch, epoch)
        self.assertEqual(len(state.project()[1]), 1)

    def test_same_publisher_counter_regression_after_outage_is_rejected(self):
        state = MeshOwnerState(self.host_id, local_clock=self.clock)
        host, rows = self.outcome()
        self.accept(state, host, rows)
        outage = copy.deepcopy(host)
        outage.update(owner=None, receipts=[])
        outage["delivery"]["status"] = "unavailable"
        self.accept(state, outage, [])
        host["owner"]["service"]["viewRevision"] = 0
        with self.assertRaises(ValueError):
            self.accept(state, host, rows)
        self.assertEqual(state.expiry, 0)

    def test_foreign_clock_and_missing_remote_proof_cannot_grant_validity(self):
        local = MeshOwnerState(self.host_id, local_clock={**self.clock, "timeNamespace": "time:20"})
        host, rows = self.outcome()
        with self.assertRaises(ValueError):
            self.accept(local, host, rows)
        remote = MeshOwnerState(self.host_id)
        host, rows = self.outcome(local=False)
        host["delivery"]["proof"] = None
        with self.assertRaises(ValueError):
            self.accept(remote, host, rows)
        self.assertEqual(remote.expiry, 0)

    def test_warming_restart_retains_history_and_complete_empty_removes_rows(self):
        state = MeshOwnerState(self.host_id, local_clock=self.clock)
        host, rows = self.outcome()
        self.accept(state, host, rows)
        warming = json.loads(
            (
                Path(__file__).resolve().parent.parent
                / "contracts/service-v1/fixtures/warming.json"
            ).read_text()
        )
        warming["source"]["uid"] = os.getuid()
        warming["publisherId"] = "22222222-2222-4222-8222-222222222222"
        host["owner"] = {
            "metadata": None,
            "service": {key: value for key, value in warming.items() if key != "snapshot"},
        }
        host["receipts"] = []
        self.accept(state, host, [])
        self.assertEqual(state.expiry, 0)
        self.assertEqual(len(state.project()[1]), 1)
        host, _ = self.outcome()
        host["owner"]["service"]["publisherId"] = warming["publisherId"]
        host["owner"]["metadata"]["serverGeneration"] = None
        self.accept(state, host, [])
        self.assertEqual(state.project()[1], [])
        self.assertEqual(state.expiry, 10100)

    def test_pool_reservation_failure_precedes_retained_state_mutation(self):
        state = MeshOwnerState(self.host_id, local_clock=self.clock)
        host, rows = self.outcome()

        def reject(_size):
            raise ValueError("fixture pool full")

        with self.assertRaises(ValueError):
            state.accept_mesh(
                host, rows, reader_id="reader", reader_clock=self.clock, now=200, reserve=reject
            )
        self.assertIsNone(state.confirmed)
        self.assertEqual(state.epoch, 0)
        self.assertEqual(state.expiry, 0)
