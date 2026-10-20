"""Released public feed APIs with the Tmux profile and Service v1 fixtures."""

import copy
import unittest

from mesh_plus.api import CachedPublisher
from mesh_plus.view_feed import FeedEncoder, FeedReceiver
from test_native_source import native

from tmux_observer.mesh_profile import TmuxMeshProfile


class _UnusedSource:
    async def snapshot(self):
        raise AssertionError("feed profile test only wraps its owned fixture")

    async def watch(self):
        if False:
            yield None


class ViewFeedTmuxProfileTests(unittest.TestCase):
    def flow(self):
        profile = TmuxMeshProfile()
        codec = profile.bind("fixture-local", "default")
        publisher = CachedPublisher(
            "tmux", "fixture-local", "default", _UnusedSource(), profile=profile
        )
        encoder = FeedEncoder(profile, codec, selector={})
        receiver = FeedReceiver(profile, codec, selector={})
        self.addCleanup(encoder.close)
        self.addCleanup(receiver.close)
        return publisher, encoder, receiver, profile

    def exchange(self, flow, frame):
        publisher, encoder, receiver, _profile = flow
        candidate = publisher.wrap(frame)
        message = encoder.encode(candidate)
        try:
            applied = receiver.apply(message.payload)
            try:
                restored = copy.deepcopy(applied.candidate["ownerFrame"])
                self.assertEqual(restored, candidate["ownerFrame"])
                return {
                    "kind": message.kind,
                    "owner": restored,
                    "upserts": copy.deepcopy(applied.upserts),
                    "removals": copy.deepcopy(applied.removals),
                    "order": copy.deepcopy(applied.order),
                }
            finally:
                applied.close()
        finally:
            message.close()

    @staticmethod
    def accepted_again(frame, *, increment_revision=False):
        result = copy.deepcopy(frame)
        result["encodedAt"] += 1
        result["receipt"]["attempted"] += 1
        result["receipt"]["accepted"] += 1
        result["receipt"]["acceptedAttempt"] += 1
        for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
            result["receipt"][key] += 1
        sample = result["snapshot"]["sample"]
        sample["startedAt"] += 1
        sample["finishedAt"] += 1
        if increment_revision:
            result["viewRevision"] += 1
        return result

    def test_metadata_order_partial_expiry_and_complete_identity_rebirth(self):
        flow = self.flow()
        initial = native()
        first = copy.deepcopy(initial["snapshot"]["sessions"][0])
        for index in range(8):
            row = copy.deepcopy(first)
            row.update(
                sessionId=f"${index + 3}",
                createdAt=first["createdAt"] + index + 2,
                name=f"fixture-{index}-" + "x" * 128,
            )
            initial["snapshot"]["sessions"].append(row)
        first_result = self.exchange(flow, initial)
        self.assertEqual(first_result["kind"], "replacement")

        metadata = self.accepted_again(initial)
        metadata_result = self.exchange(flow, metadata)
        self.assertEqual(metadata_result["kind"], "delta")
        self.assertEqual(metadata_result["upserts"], [])
        self.assertEqual(metadata_result["removals"], [])
        self.assertIsNone(metadata_result["order"])
        self.assertEqual(metadata_result["owner"]["receipt"]["accepted"], 2)
        self.assertEqual(
            metadata_result["owner"]["snapshot"]["sessions"], initial["snapshot"]["sessions"]
        )

        reordered = self.accepted_again(metadata, increment_revision=True)
        reordered["snapshot"]["sessions"].reverse()
        order_result = self.exchange(flow, reordered)
        self.assertEqual(order_result["kind"], "delta")
        expected_order = [
            [row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")]
            for row in reordered["snapshot"]["sessions"]
        ]
        self.assertEqual(order_result["order"], expected_order)
        self.assertEqual(order_result["owner"], reordered)

        partial = copy.deepcopy(reordered)
        partial["encodedAt"] += 1
        partial["receipt"]["attempted"] += 1
        partial["receipt"]["lastAttemptAt"] = partial["encodedAt"]
        partial["receipt"]["lastAttemptResult"] = "partial"
        partial["receipt"]["state"] = "failed"
        partial["receipt"]["remainingMs"] = 0
        partial_result = self.exchange(flow, partial)
        self.assertEqual(partial_result["owner"]["receipt"]["lastAttemptResult"], "partial")
        self.assertEqual(
            partial_result["owner"]["snapshot"]["sessions"], reordered["snapshot"]["sessions"]
        )

        expired_flow = self.flow()
        expired = native()
        receipt = expired["receipt"]
        receipt["state"] = "expired"
        receipt["startedAt"] = expired["encodedAt"] - receipt["leaseMs"]
        receipt["acceptedAt"] = expired["encodedAt"] - 1
        receipt["expiresAt"] = expired["encodedAt"]
        receipt["lastAttemptAt"] = receipt["startedAt"]
        receipt["remainingMs"] = 0
        expired["snapshot"]["sample"]["startedAt"] = receipt["startedAt"]
        expired["snapshot"]["sample"]["finishedAt"] = receipt["acceptedAt"]
        expired_result = self.exchange(expired_flow, expired)
        self.assertEqual(expired_result["owner"]["receipt"]["state"], "expired")
        self.assertEqual(
            expired_result["owner"]["snapshot"]["sessions"], expired["snapshot"]["sessions"]
        )

        reborn = native()
        reborn["viewRevision"] += 1
        reborn["receipt"]["attempted"] = 2
        reborn["receipt"]["accepted"] = 2
        reborn["receipt"]["acceptedAttempt"] = 2
        new_generation = "tmux-v1:1700000001:4322:/tmp/tmux-fixture/default"
        reborn["snapshot"]["serverGeneration"] = new_generation
        for row in reborn["snapshot"]["sessions"]:
            row["serverGeneration"] = new_generation
            if row["sessionId"] == expired["snapshot"]["sessions"][0]["sessionId"]:
                row["createdAt"] += 50
        old_row = expired["snapshot"]["sessions"][0]
        new_row = reborn["snapshot"]["sessions"][0]
        self.assertEqual(old_row["sessionId"], new_row["sessionId"])
        self.assertNotEqual(old_row["createdAt"], new_row["createdAt"])
        self.assertNotEqual(old_row["serverGeneration"], new_row["serverGeneration"])
        reborn_result = self.exchange(expired_flow, reborn)
        self.assertEqual(reborn_result["owner"], reborn)
        if reborn_result["kind"] == "delta":
            old_key = [
                old_row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")
            ]
            new_key = [
                new_row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")
            ]
            self.assertIn(old_key, reborn_result["removals"])
            self.assertIn(new_key, [operation["key"] for operation in reborn_result["upserts"]])

        warming_flow = self.flow()
        warming = native("warming")
        warming_result = self.exchange(warming_flow, warming)
        self.assertEqual(warming_result["owner"]["snapshot"], None)
        self.assertEqual(warming_result["owner"]["receipt"]["state"], "warming")


if __name__ == "__main__":
    unittest.main()
