"""One checked wire admission keeps ownership and bounded byte accounting."""

import copy
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tmux_observer.delivery import validate_service_frame
from tmux_observer.native import FRAME_LIMIT, encode_document
from tmux_observer_client._errors import ContractError
from tmux_observer_client._owner_document import OwnerDocument
from tmux_observer_client._remote_state import RemoteState
from tmux_observer_client.fleet import POOL_LIMIT, FleetPublisher


class OwnerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(
            (Path(__file__).parents[1] / "contracts/service-v1/fixtures/ready.json").read_text()
        )
        self.value["source"]["uid"] = self.value["snapshot"]["source"]["uid"] = os.getuid()
        self.value.update(kind="resync", sequence=0, requestId="owned-watch")
        self.host = self.value["source"]["hostId"]
        self.owner = RemoteState(self.host, local_clock=self.value["clock"])
        self.owner.start("owned-watch", 100)
        self.connection = SimpleNamespace(state=self.owner)
        self.fleet = FleetPublisher(self.host, scanner=False)

    def test_admission_reuses_checked_sizes_and_validates_once(self):
        import tmux_observer_client._owner_document as admission

        with patch.object(
            admission, "_checked_service_frame", wraps=admission._checked_service_frame
        ) as check:
            document = self.fleet.before_input(self.connection, self.value, 150)
            self.owner.receive(document, 150)
            self.fleet.owner_frame(self.connection, self.value, False, 150)
        self.assertEqual(check.call_count, 1)
        self.assertEqual(document.full_size, len(encode_document(self.value, limit=FRAME_LIMIT)))
        self.assertEqual(
            document.header_size,
            len(encode_document({**self.value, "snapshot": None}, limit=FRAME_LIMIT)),
        )
        self.assertEqual(self.fleet.retained[self.host], document.full_size + document.header_size)

    def test_decoder_mutation_cannot_change_retained_facts_or_sizes(self):
        document = self.fleet.before_input(self.connection, self.value, 150)
        self.owner.receive(document, 150)
        size = self.owner.confirmed_size
        self.value["snapshot"]["sessions"][0]["name"] = "mutated"
        self.value["receipt"]["expiresAt"] = 999999
        validate_service_frame(self.owner.confirmed)
        self.assertEqual(size, len(encode_document(self.owner.confirmed, limit=FRAME_LIMIT)))
        self.assertNotEqual(self.owner.confirmed["snapshot"]["sessions"][0]["name"], "mutated")
        self.assertNotEqual(self.owner.expiry, 999999)

    def test_capacity_checked_before_retaining_document(self):
        self.fleet.retained["other"] = POOL_LIMIT - 1
        with (
            patch.object(OwnerDocument, "retained", side_effect=AssertionError("must not retain")),
            self.assertRaises(ContractError) as caught,
        ):
            self.fleet.before_input(self.connection, self.value, 150)
        self.assertEqual(caught.exception.code, "capacity")
        self.assertIsNone(self.owner.confirmed)

    def test_standalone_receiver_still_checks_untrusted_wire(self):
        value = copy.deepcopy(self.value)
        value["snapshot"]["sessions"][0]["attachedClients"] = -1
        with self.assertRaises(ContractError):
            self.owner.receive(value, 150)
        self.assertIsNone(self.owner.confirmed)

    def test_checked_document_cannot_skip_scope_and_handshake_guards(self):
        value = copy.deepcopy(self.value)
        value["requestId"] = "foreign"
        with self.assertRaises(ContractError):
            self.owner.receive(OwnerDocument(value), 150)
        self.assertEqual(self.owner.expiry, 0)
        self.assertIsNone(self.owner.confirmed)

    def test_reconnect_drops_candidate_accounting_but_retains_historical_confirmed(self):
        self.owner.receive(self.value, 150)
        old_size = self.owner.confirmed_size
        self.owner.start("new-watch", 200)
        self.assertEqual(self.owner.candidate_size, 0)
        self.assertEqual(self.owner.confirmed_size, old_size)
        self.assertEqual(self.owner.expiry, 0)
