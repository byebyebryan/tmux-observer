"""Prepared profile authority, modern projection and implementation isolation."""

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tmux_observer._clock import boottime_ms, domain, pid_namespace
from tmux_observer.attachments import validate_attachment_delivery
from tmux_observer_client._desktop_input import input_hash, reference
from tmux_observer_client._desktop_types import LocalViewerObservation
from tmux_observer_client._errors import ContractError
from tmux_observer_client.attachments import (
    CachedClients,
    _PreparedAttachments,
    association_facts,
    current_attachments,
)
from tmux_observer_client.desktop import association_batch


def prepared():
    frame = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "contracts/attachments-v1/fixtures/delivery-ready.json"
        ).read_text()
    )
    now = boottime_ms()
    offset = now - frame["encodedAt"]
    frame["encodedAt"] += offset
    for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
        frame["receipt"][key] += offset
    for key in ("startedAt", "finishedAt"):
        frame["snapshot"]["sample"][key] += offset
    for value in (frame, frame["snapshot"]):
        value["source"]["uid"] = os.getuid()
        value["clock"] = domain()
        value["pidNamespace"] = pid_namespace()
    validate_attachment_delivery(frame)
    ref = copy.deepcopy(frame["snapshot"]["sessions"][0])
    host = {
        "hostId": ref["hostId"],
        "local": True,
        "owner": {
            "publisherId": frame["publisherId"],
            "source": frame["source"],
            "clock": frame["clock"],
            "serverGeneration": ref["serverGeneration"],
            "localExpiry": now + 9000,
        },
        "sessions": [ref | {"name": "fixture", "attachedClients": 1, "pending": False}],
        "localAttachments": frame,
    }
    return host, frame, now


class PreparedAttachmentsTests(unittest.TestCase):
    def test_prepared_receipt_has_no_mutable_alias_and_preserves_wire_input_hash(self):
        host, frame, now = prepared()
        original = input_hash([host], now=now)
        immutable = _PreparedAttachments(frame)
        host["localAttachments"] = immutable
        self.assertEqual(original, input_hash([host], now=now))
        self.assertEqual(CachedClients([host], now + 2000).client_pids_by_session(), {"$2": {123}})
        frame["snapshot"]["clients"][0]["processStartTicks"] += 1
        facts = association_facts(host, immutable, now)
        facts["clients"][0]["clientPid"] = 999
        self.assertEqual(original, input_hash([host], now=now))
        with self.assertRaises(TypeError):
            immutable["snapshot"]["clients"][0]["clientPid"] = 999
        self.assertIs(copy.deepcopy(immutable), immutable)

    def test_prepared_receipt_still_checks_current_scope_and_every_lease_boundary(self):
        host, frame, now = prepared()
        immutable = _PreparedAttachments(frame)
        self.assertIs(current_attachments(host, immutable, now), immutable)
        for mutate in (
            lambda value: value.update(local=False),
            lambda value: value.update(hostId="other"),
            lambda value: value["owner"].update(publisherId="other"),
            lambda value: value["owner"].update(serverGeneration="other"),
            lambda value: value["owner"].update(localExpiry=now),
            lambda value: value["sessions"][0].update(createdAt=1),
        ):
            changed = copy.deepcopy(host)
            mutate(changed)
            self.assertIsNone(current_attachments(changed, immutable, now))
        self.assertIsNone(current_attachments(host, immutable, frame["receipt"]["expiresAt"]))
        with patch("tmux_observer_client.attachments.domain", return_value={"bootId": "other"}):
            self.assertIsNone(current_attachments(host, immutable, now))
        with patch("tmux_observer_client.attachments.pid_namespace", return_value="pid:999"):
            self.assertIsNone(current_attachments(host, immutable, now))
        with patch("tmux_observer_client.attachments.os.getuid", return_value=os.getuid() + 1):
            self.assertIsNone(current_attachments(host, immutable, now))

    def test_prepared_receipt_cannot_admit_malformed_or_exotic_python_records(self):
        _host, frame, _now = prepared()

        class Exotic(dict):
            pass

        for value in (Exotic(frame), {**frame, "protocol": "wrong"}):
            with self.assertRaises(ValueError):
                _PreparedAttachments(value)
        frame["snapshot"]["clients"][0]["sessionRef"]["createdAt"] += 1
        with self.assertRaises(ValueError):
            _PreparedAttachments(frame)

    def test_local_only_scan_handles_absent_remote_executable(self):
        from tmux_observer_client.desktop import scan

        host, _frame, now = prepared()
        host["remoteExecutable"] = None
        host["sessions"][0].update(
            activityAt=None,
            lastAttachedAt=None,
            windowCount=1,
            sessionPath="/tmp",
            currentWindow="shell",
            currentPath="/tmp",
        )
        with (
            patch.dict(os.environ, NIRI_SOCKET="/owned/fixture"),
            patch("tmux_observer_client._desktop_scan._niri_windows", return_value=[]),
        ):
            result = scan([host], deadline=now + 2000)
        self.assertEqual(result.state, "ready")
        self.assertEqual(result.association["rows"][0]["presence"]["state"], "none")

    def test_coordinator_rejects_forged_modern_native_facts_and_missing_rows(self):
        from tests.test_attachment_collector import AssociationFixture
        from tmux_observer._attachment_state import AttachmentState
        from tmux_observer._owner_state import OwnerState
        from tmux_observer.attachment_collector import AttachmentCollector
        from tmux_observer.collector import Collector
        from tmux_observer_client._fleet_state import FleetState

        collector = Collector("fixture", runner=AssociationFixture())
        owner = OwnerState(collector.source, collector.clock)
        token = owner.begin(boottime_ms())
        profile = AttachmentState(
            collector.source, collector.clock, pid_namespace(), publisher_id=owner.publisher_id
        )
        profile_token = profile.begin(boottime_ms())
        value = collector.collect()
        self.assertTrue(owner.finish(token, value, boottime_ms()))
        sampled = AttachmentCollector(collector, process_identity=lambda *_: 500).sample(
            value, boottime_ms() + 2000
        )
        self.assertTrue(profile.finish(profile_token, sampled, boottime_ms()))
        state = FleetState("fixture", "0" * 32, collector.clock)
        state.catalog(None)
        state.owners["fixture"].start("watch", boottime_ms())
        state.owners["fixture"].receive(
            owner.frame(boottime_ms(), kind="resync", request_id="watch"), boottime_ms()
        )
        state.attachments = profile.frame(boottime_ms())
        now = boottime_ms()
        hosts = state.inputs(now)
        raw = {
            reference(row): LocalViewerObservation("none")
            for host in hosts
            for row in host["sessions"]
        }
        modern = association_batch(
            hosts,
            raw,
            context_id=state.context_id,
            epoch=state.desktop["epoch"],
            started=now,
            now=now,
        )
        legacy = {ref: {"state": "none", "reason": None} for ref in raw}
        arguments = {
            "epoch": state.desktop["epoch"],
            "key": state.input_key(now),
            "started": now,
            "finished": now,
            "now": now,
            "state": "ready",
            "observations": legacy,
            "error": None,
        }
        self.assertTrue(state.accept_desktop(**arguments, association=modern))
        for mutate in (
            lambda batch: batch.update(rows=[]),
            lambda batch: batch["rows"][0].update(attachedClients=99),
            lambda batch: batch["dependencies"][0].update(ownerExpiresAt=now + 20000),
        ):
            bad = copy.deepcopy(modern)
            mutate(bad)
            self.assertFalse(state.accept_desktop(**arguments, association=bad))
            self.assertEqual(state.desktop["state"], "failed")

    def test_cached_profile_requires_full_identity_receipt_and_process_scope(self):
        host, frame, now = prepared()
        clients = CachedClients([host], now + 2000)
        self.assertEqual(clients.client_pids_by_session(), {"$2": {123}})
        self.assertEqual(clients.client_incarnations, {123: (os.getuid(), 456)})
        for field, value in (
            ("publisherId", "22222222-2222-4222-8222-222222222222"),
            ("pidNamespace", "pid:999"),
            ("clock", {**domain(), "timeNamespace": "time:999"}),
        ):
            bad = copy.deepcopy(frame)
            bad[field] = value
            if field != "publisherId":
                bad["snapshot"][field] = value
            self.assertIsNone(current_attachments(host, bad, now))
        self.assertIsNone(current_attachments(host, frame, frame["receipt"]["expiresAt"]))
        changed = copy.deepcopy(host)
        changed["sessions"][0]["createdAt"] += 1
        self.assertIsNone(current_attachments(changed, frame, now))
        host["localAttachments"] = None
        with self.assertRaises(ContractError):
            CachedClients([host], now + 2000).client_pids_by_session()

    def test_signature_tracks_binding_and_incarnation_but_not_lease_renewal(self):
        host, frame, now = prepared()
        original = input_hash([host], now=now)
        renewed = copy.deepcopy(frame)
        renewed["receipt"]["attempted"] += 1
        renewed["receipt"]["accepted"] += 1
        renewed["receipt"]["acceptedAttempt"] += 1
        for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
            renewed["receipt"][key] += 10
        renewed["encodedAt"] += 10
        for key in ("startedAt", "finishedAt"):
            renewed["snapshot"]["sample"][key] += 10
        host["localAttachments"] = renewed
        self.assertEqual(original, input_hash([host], now=now + 10))
        renewed["snapshot"]["clients"][0]["processStartTicks"] += 1
        self.assertNotEqual(original, input_hash([host], now=now + 10))
        self.assertNotEqual(original, input_hash([host], now=renewed["receipt"]["expiresAt"]))

    def test_modern_projection_distinguishes_launch_intent_and_current_binding(self):
        host, _frame, now = prepared()
        ref = reference(host["sessions"][0])
        observed = {
            ref: LocalViewerObservation("open", "confirmed", evidence="current_native_association")
        }
        value = association_batch(
            [host], observed, context_id="0" * 32, epoch=1, started=now - 10, now=now
        )
        self.assertEqual(value["rows"][0]["presence"]["confidence"], "confirmed")
        host["local"] = False
        observed[ref] = LocalViewerObservation(
            "open", "confirmed", evidence="launch_reference", qualified=True
        )
        value = association_batch(
            [host], observed, context_id="0" * 32, epoch=1, started=now - 10, now=now
        )
        self.assertEqual(value["rows"][0]["presence"]["confidence"], "matched")
        observed[ref] = LocalViewerObservation("open", "confirmed", evidence="launch_reference")
        value = association_batch(
            [host], observed, context_id="0" * 32, epoch=1, started=now - 10, now=now
        )
        self.assertEqual(value["rows"][0]["presence"]["state"], "unknown")
        host["local"] = True
        host["localAttachments"] = None
        observed[ref] = LocalViewerObservation("none")
        value = association_batch(
            [host], observed, context_id="0" * 32, epoch=1, started=now - 10, now=now
        )
        self.assertEqual(value["rows"][0]["presence"]["state"], "unknown")

    def test_desktop_imports_with_native_collectors_and_actions_blocked(self):
        code = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("tmux_observer.collector", "tmux_observer.attachment_collector", "tmux_observer_actions", "rofi_tmux_plus")):
            raise ImportError(fullname)
sys.meta_path.insert(0, Block())
import tmux_observer_client.desktop
import tmux_observer_client._desktop_matching
"""
        subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True)

    def test_headless_reader_requires_no_desktop_implementation(self):
        code = """
import importlib.abc, os, sys
os.environ.pop("NIRI_SOCKET", None)
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "tmux_observer_client.desktop" or fullname.startswith(("tmux_observer_client._desktop_scan", "tmux_observer_client._process_evidence", "tmux_observer_client._niri_observation", "tmux_observer_actions")):
            raise ImportError(fullname)
sys.meta_path.insert(0, Block())
from tmux_observer_client.fleet import FleetPublisher
reader = FleetPublisher("fixture")
assert not reader.profile_enabled
assert reader.scanner([], deadline=1)[0] == "unsupported"
"""
        subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True)
