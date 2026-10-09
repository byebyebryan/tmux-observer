"""Retained local projection, native dependency joins and conservative old views."""

import copy
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests import test_fleet_state
from tmux_observer_client._desktop_input import reference
from tmux_observer_client._desktop_types import LocalViewerObservation
from tmux_observer_client._local_bindings import Resolution, RetainedBindings
from tmux_observer_client.contract import validate_fleet_view
from tmux_observer_client.desktop import DesktopResult, association_batch, scan_remote
from tmux_observer_client.fleet import FleetPublisher


class FleetBindingTests(unittest.TestCase):
    def setUp(self):
        test_fleet_state.FleetStateTests.setUp(self)
        self.state.owners[self.host_id].confirmed["snapshot"]["sessions"][0]["attachedClients"] = 1
        self.frame["snapshot"]["sessions"][0]["attachedClients"] = 1
        self.profile = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "contracts/attachments-v1/fixtures/delivery-ready.json"
            ).read_text()
        )
        for value in (self.profile, self.profile["snapshot"]):
            value["source"]["uid"] = os.getuid()
        self.state.attachments = self.profile
        self.enterContext(
            patch("tmux_observer_client.attachments.domain", return_value=self.state.clock)
        )
        self.enterContext(
            patch(
                "tmux_observer_client.attachments.pid_namespace",
                return_value=self.profile["pidNamespace"],
            )
        )
        self.discover = Mock(
            side_effect=lambda clients, **kwargs: {
                key: Resolution((99, 10, 100), 200, "retained_native_association")
                for key in clients
            }
        )
        self.adapter = RetainedBindings(discover=self.discover, now=lambda: 200)
        self.key = self.state.binding_key(200)
        self.batch = self.adapter.prepare(
            self.state.local_input(200),
            context_id=self.state.context_id,
            epoch=self.state.binding_epoch,
            deadline=2200,
        )
        self.assertTrue(self.accept(self.batch))

    def accept(self, value, **overrides):
        arguments = {
            "key": self.key,
            "epoch": self.state.binding_epoch,
            "started": 190,
            "finished": 200,
            "now": 201,
        }
        arguments.update(overrides)
        return self.state.accept_bindings(value, **arguments)

    def test_retained_positive_does_not_extend_or_confirm_the_desktop_receipt(self):
        view = validate_fleet_view(self.state.view(201))
        host = view["hosts"][0]
        self.assertEqual(view["desktop"]["state"], "warming")
        self.assertEqual(host["sessions"][0]["localViewer"]["state"], "unknown")
        self.assertEqual(host["localBindings"]["rows"][0]["association"]["state"], "open")
        self.assertEqual(host["localBindings"]["rows"][0]["association"]["resolvedAt"], 200)
        self.state.invalidate_desktop()
        self.assertIsNotNone(self.state.view(202)["hosts"][0]["localBindings"])
        self.discover.assert_called_once()

    def test_projection_owns_every_mutable_source_and_binding_branch(self):
        expected = self.state.view(201)
        value = self.state.view(201)
        value["clock"]["bootId"] = "changed"
        value["mesh"]["state"] = "unavailable"
        value["desktop"]["epoch"] = 99
        host = value["hosts"][0]
        host["owner"]["source"]["uid"] += 1
        host["sessions"][0]["name"] = "changed"
        host["localBindings"]["rows"][0]["association"]["reason"] = "changed"
        self.assertEqual(expected, self.state.view(201))

    def test_local_binding_inputs_do_not_project_remote_owner_history(self):
        remote = {**self.state.descriptions[0], "hostId": "remote", "local": False}
        self.state.descriptions.append(remote)
        self.state.owners["remote"] = Mock()
        self.state.owners["remote"].project.side_effect = AssertionError("remote projection")
        self.assertEqual(self.key, self.state.binding_key(201))
        self.state.owners["remote"].project.assert_not_called()

    def test_remote_renewal_does_not_rebuild_local_binding_key(self):
        publisher = SimpleNamespace(
            binding_adapter=True,
            state=self.state,
            cached_binding_key=None,
            cached_binding_dependencies=None,
            binding_expiry=None,
        )
        self.state.binding_key = Mock(wraps=self.state.binding_key)
        first = FleetPublisher.current_binding_key(publisher, 201)
        self.state.owners["remote"] = Mock(sequence=100, expiry=3000)
        self.assertEqual(first, FleetPublisher.current_binding_key(publisher, 202))
        self.state.binding_key.assert_called_once()
        self.state.owners[self.host_id].sequence += 1
        FleetPublisher.current_binding_key(publisher, 203)
        self.assertEqual(self.state.binding_key.call_count, 2)

    def test_wire_rejects_mixed_native_scope_counts_and_action_handles(self):
        baseline = self.state.view(201)
        for mutate in (
            lambda b: b.update(contextId="1" * 32),
            lambda b: b.update(publisherId="33333333-3333-3333-3333-333333333333"),
            lambda b: b["rows"][0].update(attachedClients=2),
            lambda b: b["rows"][0].update(windowId=99),
            lambda b: b.update(rows=[]),
            lambda b: b["receipt"].update(ownerExpiresAt=10101),
        ):
            invalid = copy.deepcopy(baseline)
            mutate(invalid["hosts"][0]["localBindings"])
            with self.assertRaises(ValueError):
                validate_fleet_view(invalid)

    def test_changed_client_with_same_count_immediately_hides_old_binding(self):
        self.profile["snapshot"]["clients"][0]["processStartTicks"] += 1
        view = self.state.view(202)
        self.assertIsNone(view["hosts"][0]["localBindings"])
        self.assertFalse(self.accept(self.batch, now=202))
        self.discover.assert_called_once()

    def test_scope_replacement_late_completion_and_mutable_alias_are_rejected(self):
        self.batch["rows"][0]["association"]["resolvedAt"] = 0
        self.assertEqual(
            self.state.view(202)["hosts"][0]["localBindings"]["rows"][0]["association"][
                "resolvedAt"
            ],
            200,
        )
        self.assertFalse(self.accept(self.batch, now=2190))
        self.state.invalidate_bindings()
        self.assertFalse(self.accept(self.batch, epoch=0))
        self.assertNotIn("localBindings", self.state.view(202)["hosts"][0])

    def test_missing_failed_or_expired_native_profile_never_proves_absence(self):
        self.state.attachments = None
        self.assertIsNone(self.state.view(202)["hosts"][0]["localBindings"])
        self.state.attachments = self.profile
        self.assertIsNone(self.state.view(10100)["hosts"][0]["localBindings"])
        self.discover.assert_called_once()

    def test_renewing_native_delivery_does_not_change_material_or_discovery_time(self):
        self.state.material(201)
        renewed = copy.deepcopy(self.batch)
        renewed["encodedAt"] = 203
        renewed["receipt"]["preparedAt"] = 203
        self.assertTrue(self.accept(renewed, started=202, finished=203, now=204))
        self.assertFalse(self.state.material(204))
        self.assertEqual(
            self.state.view(204)["hosts"][0]["localBindings"]["rows"][0]["association"][
                "resolvedAt"
            ],
            200,
        )

    def test_old_binding_expires_when_new_native_receipts_arrive_without_reconciliation(self):
        owner = self.state.owners[self.host_id]
        refreshed = copy.deepcopy(self.frame)
        refreshed.update(kind="view", requestId=None, sequence=1)
        refreshed["encodedAt"] += 10000
        for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
            refreshed["receipt"][key] += 10000
            self.profile["receipt"][key] += 10000
        for key in ("startedAt", "finishedAt"):
            refreshed["snapshot"]["sample"][key] += 10000
            self.profile["snapshot"]["sample"][key] += 10000
        for key in ("attempted", "accepted", "acceptedAttempt"):
            refreshed["receipt"][key] += 1
            self.profile["receipt"][key] += 1
        self.profile["encodedAt"] += 10000
        owner.receive(refreshed, 10150)
        self.assertEqual(self.key, self.state.binding_key(10200))
        view = self.state.view(10200)
        binding = view["hosts"][0]["localBindings"]
        self.assertEqual(binding["receipt"]["state"], "expired")
        self.assertEqual(binding["rows"][0]["association"]["state"], "unknown")
        self.discover.assert_called_once()


class RemoteCaptureCompatibilityTests(unittest.TestCase):
    def test_remote_scan_preserves_evidence_and_only_changes_local_legacy_rows(self):
        from tests.test_prepared_attachments import prepared

        local, _profile, now = prepared()
        remote = copy.deepcopy(local)
        remote.update(local=False, hostId="fixture-remote")
        remote["owner"]["source"]["hostId"] = remote["hostId"]
        remote["sessions"][0]["hostId"] = remote["hostId"]
        remote.pop("localAttachments")
        ref = reference(remote["sessions"][0])
        for evidence in ("launch_reference", "qualified_title"):
            legacy = {ref: {"state": "open", "confidence": "matched", "reason": None}}
            modern = association_batch(
                [remote],
                {
                    ref: LocalViewerObservation(
                        "open",
                        confidence="matched",
                        evidence=evidence,
                        qualified=True,
                    )
                },
                context_id="0" * 32,
                epoch=0,
                started=now,
                now=now,
            )
            original = DesktopResult("ready", legacy, None, modern)
            with patch("tmux_observer_client.desktop.scan", return_value=original) as scanner:
                result = scan_remote(
                    [local, remote], deadline=now + 2000, context_id="0" * 32, epoch=0
                )
            self.assertEqual(scanner.call_args.args[0], [remote])
            self.assertEqual(result.observations[ref], legacy[ref])
            rows = {reference(row["sessionRef"]): row for row in result.association["rows"]}
            self.assertEqual(rows[ref]["presence"]["evidence"], evidence)
            self.assertEqual(rows[reference(local["sessions"][0])]["presence"]["state"], "unknown")
