"""Common Kitty lifecycle, stable-client work bounds and retained evidence."""

import copy
import os
import unittest
from dataclasses import replace
from unittest.mock import Mock

from tests.test_prepared_attachments import prepared
from tmux_observer_client._desktop_input import reference
from tmux_observer_client._desktop_types import _Proc
from tmux_observer_client._local_bindings import Resolution, RetainedBindings, discover_clients


class LocalBindingCacheTests(unittest.TestCase):
    def setUp(self):
        self.host, self.frame, self.started = prepared()
        self.time = self.started
        self.discover = Mock(
            side_effect=lambda clients, **kw: {
                key: Resolution((99, 10, 55), self.time, "retained_native_association")
                for key in clients
            }
        )
        self.adapter = RetainedBindings(discover=self.discover, now=lambda: self.time)

    def run_job(self, **kwargs):
        return self.adapter.prepare(
            self.host,
            context_id="0" * 32,
            epoch=kwargs.pop("epoch", 0),
            deadline=self.time + 2000,
            **kwargs,
        )

    def renew(self, milliseconds):
        self.time += milliseconds
        self.frame["encodedAt"] += milliseconds
        for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
            self.frame["receipt"][key] += milliseconds
        for key in ("startedAt", "finishedAt"):
            self.frame["snapshot"]["sample"][key] += milliseconds
        for key in ("attempted", "accepted", "acceptedAttempt"):
            self.frame["receipt"][key] += 1
        self.host["owner"]["localExpiry"] += milliseconds

    def test_bootstrap_then_receipt_renewal_keeps_discovery_time_without_native_work(self):
        first = self.run_job()
        resolved = first["rows"][0]["association"]["resolvedAt"]
        for _ in range(20):
            self.renew(2000)
            result = self.run_job()
            self.assertEqual(result["rows"][0]["association"]["resolvedAt"], resolved)
            self.assertGreater(result["receipt"]["expiresAt"], first["receipt"]["expiresAt"])
        self.discover.assert_called_once()
        self.assertIsNone(self.adapter.retry_at)
        self.assertEqual(result["rows"][0]["association"]["state"], "open")

    def test_detach_removes_binding_and_new_incarnation_requires_discovery(self):
        self.run_job()
        client = copy.deepcopy(self.frame["snapshot"]["clients"][0])
        self.frame["snapshot"]["clients"] = []
        self.host["sessions"][0]["attachedClients"] = 0
        detached = self.run_job()
        self.assertEqual(detached["rows"][0]["association"]["state"], "none")
        self.assertEqual(self.adapter.entries, {})
        self.discover.assert_called_once()
        client["processStartTicks"] += 1
        self.frame["snapshot"]["clients"] = [client]
        self.host["sessions"][0]["attachedClients"] = 1
        self.run_job()
        self.assertEqual(self.discover.call_count, 2)

    def test_client_session_switch_reuses_the_original_window_binding(self):
        initial = self.run_job()
        new = copy.deepcopy(self.host["sessions"][0])
        new.update(sessionId="$8", name="second")
        self.host["sessions"][0]["attachedClients"] = 0
        self.host["sessions"].append(new)
        ref = reference(new).as_dict()
        self.frame["snapshot"]["sessions"].append(ref)
        self.frame["snapshot"]["clients"][0]["sessionRef"] = ref
        switched = self.run_job()
        self.discover.assert_called_once()
        self.assertEqual(switched["rows"][0]["association"]["state"], "none")
        self.assertEqual(switched["rows"][1]["association"], initial["rows"][0]["association"])

    def test_new_client_same_aggregate_count_does_not_inherit_old_binding(self):
        self.run_job()
        self.frame["snapshot"]["clients"][0]["clientPid"] += 1
        self.run_job()
        self.assertEqual(self.discover.call_count, 2)
        self.assertEqual(len(self.adapter.entries), 1)

    def test_failure_or_expiry_revokes_claims_without_proving_detach(self):
        self.run_job()
        self.host["localAttachments"] = None
        failed = self.run_job()
        self.assertEqual(failed["receipt"]["state"], "unavailable")
        self.assertEqual(failed["rows"][0]["association"]["state"], "unknown")
        self.assertEqual(len(self.adapter.entries), 1)
        self.host["localAttachments"] = self.frame
        recovered = self.run_job()
        self.discover.assert_called_once()
        self.assertEqual(recovered["rows"][0]["association"]["state"], "open")
        self.time = self.frame["receipt"]["expiresAt"]
        self.assertEqual(self.run_job()["rows"][0]["association"]["state"], "unknown")

    def test_count_race_remains_unknown_until_native_inputs_agree(self):
        self.host["sessions"][0]["attachedClients"] = 0
        result = self.run_job()
        self.assertEqual(result["rows"][0]["association"]["reason"], "attachment_count_changed")
        self.host["sessions"][0]["attachedClients"] = 1
        self.assertEqual(self.run_job()["rows"][0]["association"]["state"], "open")
        self.discover.assert_called_once()

    def test_unknown_new_client_gets_only_three_spaced_settling_attempts(self):
        self.discover.side_effect = lambda clients, **kw: {
            key: Resolution(None, None, "window_unresolved") for key in clients
        }
        self.run_job()
        for elapsed in (0, 999, 1, 1000, 1000, 1000):
            self.renew(elapsed)
            result = self.run_job()
        self.assertEqual(self.discover.call_count, 3)
        self.assertEqual(result["rows"][0]["association"]["state"], "unknown")
        self.assertIsNone(self.adapter.retry_at)
        self.run_job(force=True)
        self.assertEqual(self.discover.call_count, 4)

    def test_scope_change_and_explicit_refresh_rediscover_existing_client(self):
        self.run_job()
        self.renew(2000)
        refreshed = self.run_job(force=True)
        self.assertEqual(refreshed["rows"][0]["association"]["resolvedAt"], self.time)
        self.run_job(epoch=1)
        self.assertEqual(self.discover.call_count, 3)
        self.host["owner"]["publisherId"] = "33333333-3333-3333-3333-333333333333"
        self.frame["publisherId"] = self.host["owner"]["publisherId"]
        self.run_job(epoch=1)
        self.assertEqual(self.discover.call_count, 4)

    def test_discovery_running_past_its_native_budget_cannot_publish_positive(self):
        original = self.discover.side_effect

        def late(clients, **kw):
            result = original(clients, **kw)
            self.time = kw["deadline"]
            return result

        self.discover.side_effect = late
        result = self.run_job()
        self.assertEqual(result["receipt"]["state"], "unavailable")
        self.assertEqual(result["rows"][0]["association"]["state"], "unknown")


class KittyAncestorDiscoveryTests(unittest.TestCase):
    def setUp(self):
        uid = os.getuid()
        self.processes = {
            10: _Proc(10, 1, 10, 10, 0, 100, ("/usr/bin/kitty",), uid),
            20: _Proc(20, 10, 20, 20, 5, 200, ("zsh",), uid),
            30: _Proc(30, 20, 20, 20, 5, 300, ("tmux", "attach-session"), uid),
        }
        self.rows = [{"id": 99, "pid": 10, "app_id": "kitty", "title": "arbitrary"}]
        self.windows = Mock(return_value=self.rows)
        self.process = Mock(side_effect=self.processes.get)

    def discover(self):
        return discover_clients(
            {(30, 300)},
            uid=os.getuid(),
            deadline=2000,
            windows_reader=self.windows,
            proc_reader=self.process,
            now=lambda: 1000,
        )[(30, 300)]

    def test_unique_parent_chain_needs_no_descendant_or_environment_scan(self):
        result = self.discover()
        self.assertEqual(result.window, (99, 10, 100))
        self.assertEqual(result.resolved_at, 1000)
        self.assertEqual(self.windows.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in self.process.call_args_list], [30, 20, 10, 30, 20, 10]
        )

    def test_shared_terminal_process_multiple_os_windows_is_ambiguous(self):
        self.rows.append({"id": 100, "pid": 10, "app_id": "kitty"})
        result = self.discover()
        self.assertIsNone(result.window)
        self.assertEqual(result.reason, "ambiguous_match")

    def test_uid_or_client_incarnation_mismatch_cannot_bind(self):
        for replacement in (
            replace(self.processes[30], start=301),
            replace(self.processes[30], uid=os.getuid() + 1),
        ):
            self.processes[30] = replacement
            self.assertIsNone(self.discover().window)

    def test_closing_capture_or_process_reuse_revokes_discovery(self):
        for changed in ([], [dict(self.rows[0], pid=11)], [self.rows[0], self.rows[0]]):
            self.windows.side_effect = [self.rows, changed]
            self.assertIsNone(self.discover().window)
        self.windows.side_effect = None
        calls = {}

        def reused(pid):
            calls[pid] = calls.get(pid, 0) + 1
            proc = self.processes[pid]
            return replace(proc, start=proc.start + 1) if calls[pid] > 1 else proc

        self.process.side_effect = reused
        self.assertIsNone(self.discover().window)

    def test_cyclic_or_unreadable_ancestry_remains_unresolved(self):
        self.processes[20] = replace(self.processes[20], ppid=30)
        self.assertIsNone(self.discover().window)
        del self.processes[20]
        self.assertEqual(self.discover().reason, "process_unavailable")
