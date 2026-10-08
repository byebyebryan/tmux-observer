"""Grouped post-request work, child provenance and lost-notification recovery."""

import copy
import unittest
from types import SimpleNamespace

from tmux_observer._tickets import TicketError, TicketStore
from tmux_observer.public import validate_request
from tmux_observer_client._errors import ContractError
from tmux_observer_client._fleet_tickets import FleetTickets

READER = "11111111-1111-4111-8111-111111111111"
PUBLISHER = "22222222-2222-4222-8222-222222222222"
CHILD_ID = "33333333-3333-4333-8333-333333333333"
OWNER = {"hostId": "fixture", "source": "owner"}
DESKTOP = {"hostId": "fixture", "source": "desktop"}


class Connection:
    def __init__(self, owner):
        self.state, self.closed, self.requests, self.reject = owner, False, [], False

    def send(self, value, now):
        validate_request(value)
        if self.reject:
            raise ContractError("operation_failed", "bounded queue full")
        self.requests.append((copy.deepcopy(value), now))


class FleetTicketTests(unittest.TestCase):
    def setUp(self):
        self.owner = SimpleNamespace(
            host_id="fixture",
            epoch=1,
            scope=(PUBLISHER,),
            transport="ready",
            confirmed=None,
            expiry=0,
            proof=None,
            local_clock=None,
            pending=None,
            next_probe=10000,
        )
        self.state = SimpleNamespace(
            host_id="fixture",
            reader_id=READER,
            mesh={"state": "ready"},
            owners={"fixture": self.owner},
        )
        self.tickets = FleetTickets(self.state)
        self.connection = Connection(self.owner)
        self.connections = {"fixture": self.connection}

    def admit(self, now=100, scopes=None):
        return self.tickets.admit([OWNER] if scopes is None else scopes, now, desktop_attempt=4)

    def value(self, parent, now=200):
        return self.tickets.store.lookup(parent["id"], now)

    def reply(
        self,
        *,
        state="accepted",
        row_state="pending",
        attempt=None,
        request=None,
        error=None,
        ticket_id=CHILD_ID,
        now=200,
    ):
        child = self.tickets.children["fixture"]
        value = {
            "publisherId": PUBLISHER,
            "requestId": child.request_id if request is None else request,
            "ticket": {
                "id": ticket_id,
                "publisherId": PUBLISHER,
                "state": state,
                "requestedAt": 9000,
                "deadlineAt": 24000,
                "sources": [{**OWNER, "state": row_state, "attempt": attempt, "error": error}],
            },
        }
        self.tickets.receive(self.connection, value, False, now)

    def proof(self, attempt, *, sent=160, received=230):
        self.owner.confirmed = {
            "publisherId": PUBLISHER,
            "receipt": {"state": "ready", "acceptedAttempt": attempt},
        }
        self.owner.expiry = 10000
        self.owner.proof = {"sentAt": sent, "receivedAt": received}

    def test_many_pending_requests_share_one_child_but_later_requests_need_successor(self):
        parents = [self.admit(100 + i) for i in range(32)]
        self.tickets.tick(self.connections, 150)
        self.assertEqual(len(self.connection.requests), 1)
        self.assertTrue(all(self.value(p)["state"] == "running" for p in parents))
        later = self.admit(151)
        self.tickets.tick(self.connections, 160)
        self.assertEqual(len(self.connection.requests), 1)
        self.assertEqual(self.value(later)["state"], "coalesced")
        self.proof(8)
        self.reply(state="complete", row_state="complete", attempt=8, now=240)
        self.assertTrue(all(self.value(p, 241)["state"] == "complete" for p in parents))
        self.assertEqual(self.value(later, 241)["state"], "coalesced")
        self.tickets.tick(self.connections, 242)
        self.assertEqual(len(self.connection.requests), 2)
        self.assertEqual(self.connection.requests[-1][1], 242)
        self.assertEqual(self.value(later, 243)["state"], "running")

    def test_child_completion_requires_post_request_matching_proof_and_native_attempt(self):
        parent = self.admit()
        self.tickets.tick(self.connections, 150)
        self.proof(7, sent=140)
        self.reply(state="complete", row_state="complete", attempt=8)
        self.assertEqual(self.value(parent)["state"], "running")
        self.assertEqual(self.owner.next_probe, 200)
        self.proof(8, sent=140)
        self.tickets.tick(self.connections, 210)
        self.assertEqual(self.value(parent, 211)["state"], "running")
        self.proof(8, sent=220)
        self.tickets.tick(self.connections, 240)
        value = self.value(parent, 241)
        self.assertEqual(value["state"], "complete")
        self.assertEqual(value["sources"][0]["attempt"], 8)
        count = len(self.connection.requests)
        self.value(parent, 10000)
        self.assertEqual(len(self.connection.requests), count)

    def test_lost_terminal_notification_has_one_shared_bounded_status_lookup(self):
        parents = [self.admit(100 + i) for i in range(20)]
        self.tickets.tick(self.connections, 150)
        self.reply(state="running", row_state="running", attempt=8)
        self.tickets.tick(self.connections, 1199)
        self.assertEqual(len(self.connection.requests), 1)
        self.tickets.tick(self.connections, 1200)
        lookup = self.connection.requests[-1][0]
        self.assertEqual(lookup["operation"], "refresh_status")
        self.tickets.tick(self.connections, 1210)
        self.assertEqual(len(self.connection.requests), 2)
        self.proof(8, sent=1250, received=1270)
        self.reply(
            state="complete", row_state="complete", attempt=8, request=lookup["requestId"], now=1300
        )
        self.assertTrue(all(self.value(p, 1301)["state"] == "complete" for p in parents))

    def test_scope_and_control_errors_end_only_affected_outcomes(self):
        parent = self.admit(scopes=[OWNER, DESKTOP])
        self.tickets.tick(self.connections, 150)
        child = self.tickets.children["fixture"]
        error = {"error": {"code": "capacity", "message": "owner tickets full"}}
        self.assertFalse(self.tickets.operation_error(self.connection, error, 160))
        self.assertFalse(
            self.tickets.operation_error(
                self.connection,
                {**error, "requestId": "unknown-probe"},
                160,
            )
        )
        self.assertTrue(
            self.tickets.operation_error(
                self.connection,
                {**error, "requestId": child.request_id},
                160,
            )
        )
        self.assertEqual(self.owner.transport, "ready")
        self.tickets.store.begin(("fixture", "desktop"), 5, 170, 170)
        self.tickets.store.finish(("fixture", "desktop"), 5, 180, accepted=True)
        value = self.value(parent)
        self.assertEqual(value["state"], "failed")
        self.assertEqual([row["state"] for row in value["sources"]], ["failed", "complete"])
        later = self.admit(201)
        self.tickets.tick(self.connections, 220)
        self.owner.epoch += 1
        self.tickets.tick(self.connections, 230)
        self.assertEqual(self.value(later, 231)["state"], "stale_scope")

    def test_foreign_child_and_regressed_outcomes_fail_without_false_success(self):
        parent = self.admit()
        self.tickets.tick(self.connections, 150)
        self.reply(state="running", row_state="running", attempt=8)
        self.reply(state="accepted", row_state="pending", attempt=None, now=210)
        self.assertEqual(self.value(parent, 211)["state"], "failed")
        later = self.admit(220)
        self.tickets.tick(self.connections, 230)
        self.reply(state="running", row_state="running", attempt=8, now=240)
        self.reply(ticket_id="44444444-4444-4444-8444-444444444444", now=250)
        self.assertEqual(self.value(later, 251)["state"], "failed")

    def test_queue_ack_and_overall_deadlines_are_bounded(self):
        parent = self.admit()
        self.connection.reject = True
        self.tickets.tick(self.connections, 150)
        self.assertEqual(self.value(parent)["sources"][0]["error"]["code"], "backpressure")
        self.connection.reject = False
        parent = self.admit(210)
        self.tickets.tick(self.connections, 220)
        self.tickets.tick(self.connections, 2220)
        self.assertEqual(self.value(parent, 2221)["sources"][0]["error"]["code"], "deadline")
        parent = self.admit(2300)
        self.tickets.tick(self.connections, 2310)
        self.reply(now=2400)
        self.tickets.tick(self.connections, 17300)
        self.assertEqual(self.value(parent, 17301)["state"], "deadline")
        self.assertFalse(self.tickets.children)

    def test_admission_fixed_scope_and_desktop_context_invalidation(self):
        with self.assertRaises(TicketError):
            self.admit(scopes=[{"hostId": "foreign", "source": "owner"}])
        self.state.mesh["state"] = "unavailable"
        with self.assertRaises(TicketError):
            self.admit()
        self.state.mesh["state"] = "ready"
        parent = self.admit(scopes=[OWNER, DESKTOP])
        self.tickets.tick(self.connections, 150)
        self.tickets.invalidate(160, desktop_only=True)
        self.assertIn("fixture", self.tickets.children)
        self.assertEqual(self.value(parent)["sources"][1]["state"], "stale_scope")
        self.tickets.invalidate(170)
        self.assertEqual(self.value(parent)["state"], "stale_scope")
        self.assertFalse(self.tickets.children)

    def test_external_source_update_is_transactional_and_preserves_known_attempt(self):
        store = TicketStore(READER)
        parent = store.admit([OWNER], 100, minimum={("fixture", "owner"): 1})
        store.set_source([parent["id"]], ("fixture", "owner"), 110, state="running", attempt=8)
        before = store.lookup(parent["id"], 111)
        with self.assertRaises(ValueError):
            store.set_source([parent["id"]], ("fixture", "owner"), 120, state="complete", attempt=7)
        self.assertEqual(store.lookup(parent["id"], 121), before)
        with self.assertRaises(ValueError):
            store.set_source([parent["id"]], ("fixture", "owner"), 122, state="failed", error=None)
        self.assertEqual(store.lookup(parent["id"], 123), before)
        store.set_source(
            [parent["id"]],
            ("fixture", "owner"),
            130,
            state="stale_scope",
            error={"code": "stale_scope", "message": "replaced"},
        )
        value = store.lookup(parent["id"], 131)
        self.assertEqual(value["state"], "stale_scope")
        self.assertEqual(value["sources"][0]["attempt"], 8)

    def test_desktop_waits_for_owner_outcome_and_retries_obsolete_join(self):
        parent = self.admit(scopes=[OWNER, DESKTOP])
        direct = self.admit(101, scopes=[DESKTOP])
        self.tickets.tick(self.connections, 150)
        eligible = self.tickets.desktop_ready()
        self.assertEqual(eligible, {direct["id"]})
        self.tickets.desktop_begin(eligible, 5, 160, 160)
        self.tickets.desktop_finish(5, 170, accepted=True)
        self.assertEqual(self.value(direct)["state"], "complete")
        self.assertEqual(self.value(parent)["sources"][1]["state"], "pending")
        self.proof(8, sent=180, received=190)
        self.reply(state="complete", row_state="complete", attempt=8, now=200)
        eligible = self.tickets.desktop_ready()
        self.assertEqual(eligible, {parent["id"]})
        self.tickets.desktop_begin(eligible, 6, 210, 210)
        self.tickets.desktop_finish(6, 220, obsolete=True)
        self.assertEqual(self.value(parent, 221)["state"], "coalesced")
        self.assertEqual(self.tickets.desktop_ready(), {parent["id"]})
        self.tickets.desktop_begin({parent["id"]}, 6, 230, 230)
        self.assertEqual(self.value(parent, 231)["sources"][1]["state"], "pending")
        self.tickets.desktop_begin({parent["id"]}, 7, 240, 240)
        self.tickets.desktop_finish(7, 250, accepted=True)
        self.assertEqual(self.value(parent, 251)["state"], "complete")
