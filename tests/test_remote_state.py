"""Remote-clock proof and stream epochs, independent of SSH process plumbing."""

import copy
import json
import unittest
from pathlib import Path

from tmux_observer.public import validate_service_frame
from tmux_observer_client._errors import ContractError
from tmux_observer_client._remote_state import RemoteState


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.frame = json.loads(
            (
                Path(__file__).resolve().parent.parent / "contracts/service-v1/fixtures/ready.json"
            ).read_text()
        )
        self.host = self.frame["source"]["hostId"]
        self.remote = RemoteState(self.host)

    def handshake(self):
        self.remote.start("handshake", 100)
        frame = copy.deepcopy(self.frame)
        frame.update(kind="resync", requestId="handshake", sequence=0)
        self.remote.receive(frame, 150)

    def confirm(self, sent=200, received=250):
        request = self.remote.probe(sent)
        frame = copy.deepcopy(self.frame)
        frame.update(
            kind="status", requestId=request["requestId"], sequence=self.remote.sequence + 1
        )
        self.remote.receive(frame, received)
        return frame

    def test_handshake_and_heartbeats_do_not_establish_or_extend_positive_lease(self):
        self.handshake()
        self.assertEqual(self.remote.expiry, 0)
        frame = self.confirm()
        remaining = frame["receipt"]["remainingMs"]
        self.assertEqual(self.remote.expiry, 250 + max(0, remaining - 50 - 100))
        expiry = self.remote.expiry
        for index in range(2, 5):
            frame.update(kind="heartbeat", requestId=None, sequence=index)
            self.remote.receive(frame, 300 + index * 100)
        self.assertEqual(self.remote.expiry, expiry)
        self.assertEqual(self.remote.proof["receivedAt"], 250)

    def test_wrong_nonce_does_not_adopt_candidate_or_renew_receipt(self):
        self.handshake()
        self.confirm()
        original = self.remote.confirmed
        expiry = self.remote.expiry
        request = self.remote.probe(4000)
        frame = copy.deepcopy(self.frame)
        frame.update(kind="status", requestId="wrong", sequence=2)
        self.remote.receive(frame, 4100)
        self.assertEqual(self.remote.confirmed, original)
        self.assertEqual(self.remote.expiry, expiry)
        self.assertEqual(self.remote.pending["requestId"], request["requestId"])
        self.remote.expire(6000)
        self.assertEqual(self.remote.expiry, 0)
        self.assertEqual(self.remote.transport, "failed")

    def test_late_probe_and_suspend_jump_fail_before_accepting(self):
        for now in (2200, 999999):
            self.setUp()
            self.handshake()
            request = self.remote.probe(200)
            frame = copy.deepcopy(self.frame)
            frame.update(kind="status", requestId=request["requestId"], sequence=1)
            with self.assertRaises(ContractError):
                self.remote.receive(frame, now)
            self.assertEqual(self.remote.expiry, 0)

    def test_failure_invalidates_immediately_and_retains_historical_metadata(self):
        self.handshake()
        self.confirm()
        frame = copy.deepcopy(self.remote.confirmed)
        frame.update(
            kind="view",
            requestId=None,
            sequence=2,
            error={"code": "native_failed", "message": "fixture"},
        )
        frame["receipt"].update(state="failed", remainingMs=0, lastAttemptResult="failed")
        self.remote.receive(frame, 300)
        owner, rows = self.remote.project()
        self.assertTrue(rows)
        self.assertEqual(owner["receipt"]["state"], "failed")
        self.assertEqual(owner["localExpiry"], 0)

    def test_gap_needs_proof_but_replays_and_scope_changes_are_fatal(self):
        for change in ("replay", "unmarked_gap", "publisher", "clock", "uid", "host"):
            with self.subTest(change=change):
                self.setUp()
                self.handshake()
                self.confirm()
                frame = copy.deepcopy(self.remote.confirmed)
                frame.update(kind="view", requestId=None, sequence=2)
                if change == "replay":
                    frame["sequence"] = 1
                elif change == "unmarked_gap":
                    frame["sequence"] = 3
                elif change == "publisher":
                    frame["publisherId"] = "22222222-2222-4222-8222-222222222222"
                elif change == "clock":
                    frame["clock"]["timeNamespace"] = "time:98765"
                    frame["snapshot"]["clock"]["timeNamespace"] = "time:98765"
                elif change == "uid":
                    frame["source"]["uid"] += 1
                    frame["snapshot"]["source"]["uid"] += 1
                else:
                    frame["source"]["hostId"] = "other"
                with self.assertRaises(ContractError):
                    self.remote.receive(frame, 300)
                self.assertEqual(self.remote.expiry, 0)
        self.setUp()
        self.handshake()
        self.confirm()
        frame = copy.deepcopy(self.frame)
        frame.update(kind="gap", requestId=None, sequence=10)
        self.remote.receive(frame, 300)
        self.assertEqual(self.remote.expiry, 0)
        self.assertIsNone(self.remote.proof)
        self.assertIsNotNone(self.remote.probe(301))

    def test_counter_or_encoder_time_regression_is_not_a_new_receipt(self):
        for key in ("receipt", "encodedAt", "viewRevision"):
            with self.subTest(key=key):
                self.setUp()
                self.handshake()
                self.confirm()
                frame = copy.deepcopy(self.remote.confirmed)
                frame.update(kind="heartbeat", requestId=None, sequence=2)
                if key == "receipt":
                    # Individually valid but older receipt from this incarnation.
                    frame["receipt"].update(
                        state="warming",
                        attempted=0,
                        accepted=0,
                        acceptedAttempt=0,
                        startedAt=None,
                        acceptedAt=None,
                        expiresAt=None,
                        lastAttemptAt=None,
                        lastAttemptResult="none",
                        remainingMs=0,
                    )
                    frame["snapshot"] = None
                else:
                    frame[key] -= 1
                    if key == "encodedAt":
                        frame["receipt"]["remainingMs"] = frame["receipt"]["expiresAt"] - frame[key]
                validate_service_frame(frame)
                with self.assertRaises(ContractError):
                    self.remote.receive(frame, 300)
                self.assertEqual(self.remote.expiry, 0)

    def test_new_transport_epoch_cannot_reuse_old_handshake_or_proof(self):
        self.handshake()
        self.confirm()
        old = copy.deepcopy(self.remote.confirmed)
        self.remote.start("new-handshake", 400)
        self.assertEqual(self.remote.expiry, 0)
        self.assertEqual(self.remote.epoch, 2)
        with self.assertRaises(ContractError):
            self.remote.receive(old, 450)
        self.assertEqual(self.remote.transport, "failed")
