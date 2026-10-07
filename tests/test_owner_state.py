"""Deterministic scheduler/receipt proof, independent of native execution."""

import copy
import json
import unittest
from pathlib import Path

from tmux_observer._owner_state import OwnerState
from tmux_observer.public import validate_service_frame


def observation(start=100):
    path = (
        Path(__file__).resolve().parent.parent / "contracts/observation-v1/fixtures/complete.json"
    )
    value = json.loads(path.read_text())
    value["sample"].update(startedAt=start, finishedAt=start + 20)
    return value


def state():
    value = observation()
    return OwnerState(value["source"], value["clock"])


class OwnerStateTests(unittest.TestCase):
    def test_warming_and_reads_do_not_schedule(self):
        owner = state()
        for now in (0, 100, 200):
            frame = owner.frame(now)
            self.assertIsNone(frame["snapshot"])
            self.assertEqual(frame["receipt"]["attempted"], 0)
        self.assertIsNone(owner.job)
        self.assertEqual(owner.begin(100), 1)
        self.assertIsNone(owner.begin(101))
        self.assertTrue(owner.frame(110)["receipt"]["inFlight"])

    def test_acceptance_bound_to_native_start_and_unchanged_samples(self):
        owner = state()
        token = owner.begin(100)
        self.assertTrue(owner.finish(token, observation(), 125))
        first = owner.frame(130)
        self.assertEqual(first["receipt"]["expiresAt"], 10100)
        self.assertEqual(first["receipt"]["remainingMs"], 9970)
        token = owner.begin(2100)
        self.assertTrue(owner.finish(token, observation(2100), 2125))
        second = owner.frame(2130)
        self.assertEqual(second["viewRevision"], first["viewRevision"])
        self.assertEqual(second["receipt"]["accepted"], 2)
        self.assertEqual(second["receipt"]["expiresAt"], 12100)

    def test_native_failure_preserves_history_but_invalidates_membership(self):
        owner = state()
        owner.finish(owner.begin(100), observation(), 125)
        retained = owner.frame(130)["snapshot"]
        for result in ("partial", "failed", "unsupported"):
            token = owner.begin(owner.next_due)
            start = owner.job[1]
            failed = observation(start)
            failed.update(serverGeneration=None, sessions=[])
            failed["sample"].update(
                coverage=result, error={"code": "unavailable", "message": "native unavailable"}
            )
            self.assertFalse(owner.finish(token, failed, start + 25))
            frame = owner.frame(start + 30)
            self.assertEqual(frame["snapshot"], retained)
            self.assertEqual(frame["receipt"]["accepted"], 1)
            self.assertEqual(frame["receipt"]["remainingMs"], 0)
            validate_service_frame(frame)

    def test_expiry_does_not_schedule_or_renew(self):
        owner = state()
        owner.finish(owner.begin(100), observation(), 125)
        frame = owner.frame(10100, kind="heartbeat")
        self.assertEqual(frame["receipt"]["state"], "expired")
        self.assertEqual(frame["receipt"]["remainingMs"], 0)
        self.assertEqual(frame["receipt"]["accepted"], 1)
        self.assertEqual(owner.frame(10200)["viewRevision"], frame["viewRevision"])
        self.assertIsNone(owner.job)

    def test_suspend_late_sample_never_accepted(self):
        owner = state()
        token = owner.begin(100)
        self.assertFalse(owner.finish(token, observation(), 100000))
        frame = owner.frame(100000)
        self.assertEqual(frame["error"]["code"], "deadline")
        self.assertIsNone(frame["snapshot"])
        self.assertEqual(frame["receipt"]["accepted"], 0)

    def test_coalesced_hint_needs_successor_and_honors_spacing(self):
        owner = state()
        token = owner.begin(100)
        for _ in range(20):
            owner.hint(110)
        self.assertTrue(owner.successor)
        owner.finish(token, observation(), 125)
        self.assertEqual(owner.next_due, 1100)
        self.assertFalse(owner.due(1099))
        self.assertEqual(owner.begin(1100), 2)
        self.assertIsNone(owner.begin(1101))

    def test_wrong_scope_profile_and_old_sample_rejected(self):
        for mutate in (
            lambda v: v["source"].update(hostId="other"),
            lambda v: v["clock"].update(timeNamespace="time:11"),
            lambda v: v["sample"].update(startedAt=99),
            lambda v: v["capabilities"].update(panes=True),
        ):
            owner = state()
            token = owner.begin(100)
            value = observation()
            mutate(value)
            self.assertFalse(owner.finish(token, value, 125))
            self.assertEqual(owner.frame(130)["error"]["code"], "invalid_sample")

    def test_stop_and_old_completion_do_not_change_new_incarnation(self):
        owner = state()
        token = owner.begin(100)
        owner.stop()
        self.assertFalse(owner.finish(token, observation(), 125))
        self.assertFalse(owner.due(2100))
        self.assertIsNone(owner.begin(2100))
        replacement = state()
        self.assertNotEqual(owner.publisher_id, replacement.publisher_id)
        self.assertFalse(replacement.finish(token, observation(), 125))

    def test_successor_spacing_uses_actual_native_start(self):
        owner = state()
        token = owner.begin(100)
        owner.hint(110)
        self.assertTrue(owner.finish(token, observation(150), 175))
        self.assertEqual(owner.next_due, 1150)
        self.assertFalse(owner.due(1149))

    def test_returned_frames_cannot_mutate_retained_state(self):
        owner = state()
        owner.finish(owner.begin(100), observation(), 125)
        frame = owner.frame(130)
        original = copy.deepcopy(frame)
        frame["snapshot"]["sessions"].clear()
        frame["source"]["hostId"] = "other"
        self.assertEqual(owner.frame(130), original)
