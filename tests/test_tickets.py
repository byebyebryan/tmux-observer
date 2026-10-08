"""Post-request causality, coalescing, capacity and retained terminal outcomes."""

import unittest

from tmux_observer._tickets import RETENTION_MS, TicketError, TicketStore

HOST = {"hostId": "fixture-local", "source": "owner"}
SCOPE = ("fixture-local", "owner")
PUBLISHER = "11111111-1111-4111-8111-111111111111"


class TicketTests(unittest.TestCase):
    def test_existing_attempt_cannot_complete_later_requests(self):
        store = TicketStore(PUBLISHER)
        first = store.admit([HOST], 100, minimum={SCOPE: 2}, coalesced=True)
        self.assertFalse(store.begin(SCOPE, 1, 90, 110))
        self.assertFalse(store.finish(SCOPE, 1, 120, accepted=True))
        self.assertEqual(store.lookup(first["id"], 121)["state"], "coalesced")
        self.assertFalse(store.begin(SCOPE, 2, 99, 122))
        running = store.begin(SCOPE, 2, 130, 130)
        self.assertEqual(running[0]["state"], "running")
        complete = store.finish(SCOPE, 2, 150, accepted=True)[0]
        self.assertEqual(complete["sources"][0]["attempt"], 2)
        self.assertEqual(complete["state"], "complete")
        self.assertEqual(store.lookup(first["id"], 10000), complete)

    def test_many_tickets_share_eligible_attempt(self):
        store = TicketStore(PUBLISHER)
        ids = [
            store.admit([HOST], index + 100, minimum={SCOPE: 3}, coalesced=index > 0)["id"]
            for index in range(32)
        ]
        self.assertEqual(len(store.begin(SCOPE, 3, 200, 200)), 32)
        self.assertEqual(len(store.finish(SCOPE, 3, 250, accepted=True)), 32)
        self.assertTrue(all(store.lookup(key, 251)["state"] == "complete" for key in ids))

    def test_failure_mixed_success_and_late_results_are_honest(self):
        store = TicketStore(PUBLISHER)
        desktop = {"hostId": "fixture-local", "source": "desktop"}
        ds = ("fixture-local", "desktop")
        ticket = store.admit([HOST, desktop], 100, minimum={SCOPE: 1, ds: 1})
        store.begin(SCOPE, 1, 110, 110)
        store.begin(ds, 1, 110, 110)
        store.finish(SCOPE, 1, 150, accepted=True)
        store.finish(ds, 1, 151, accepted=False, error={"code": "failed", "message": "fixture"})
        value = store.lookup(ticket["id"], 152)
        self.assertEqual(value["state"], "failed")
        self.assertEqual([row["state"] for row in value["sources"]], ["complete", "failed"])
        late = store.admit([HOST], 200, minimum={SCOPE: 2})
        store.begin(SCOPE, 2, 210, 210)
        results = store.finish(SCOPE, 2, 15200, accepted=True)
        self.assertEqual(results[0]["state"], "deadline")
        self.assertEqual(store.lookup(late["id"], 15201)["state"], "deadline")

    def test_capacity_retention_and_copies(self):
        store = TicketStore(PUBLISHER)
        first = store.admit([HOST], 100, minimum={SCOPE: 1})
        first["sources"][0]["state"] = "failed"
        self.assertEqual(store.lookup(first["id"], 100)["state"], "accepted")
        for _ in range(63):
            store.admit([HOST], 100, minimum={SCOPE: 1})
        with self.assertRaises(TicketError) as issue:
            store.admit([HOST], 100, minimum={SCOPE: 1})
        self.assertEqual(issue.exception.code, "capacity")
        store.begin(SCOPE, 1, 101, 101)
        store.finish(SCOPE, 1, 102, accepted=True)
        store.lookup(first["id"], 102 + RETENTION_MS - 1)
        with self.assertRaises(TicketError):
            store.lookup(first["id"], 102 + RETENTION_MS)
        self.assertEqual(len(store.entries), 0)
