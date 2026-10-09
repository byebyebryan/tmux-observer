"""Native association races and independent source state; native proof is separate."""

import copy
import os
import unittest

from tests.test_collector import NativeFixture
from tmux_observer._attachment_state import AttachmentState
from tmux_observer._clock import boottime_ms
from tmux_observer._process import Completed, ProcessError, allowed_read
from tmux_observer.attachment_collector import (
    CLIENT_FIELDS,
    AttachmentCollector,
    pid_namespace,
    process_start,
)
from tmux_observer.collector import Collector


class AssociationFixture(NativeFixture):
    def __init__(self):
        super().__init__()
        self.client_rows = "123\t$1\t101\n"
        self.client_reads = 0
        self.client_after = None

    def __call__(self, args, deadline):
        if args == ["list-clients", "-F", CLIENT_FIELDS]:
            self.calls.append((args, deadline))
            self.client_reads += 1
            if self.client_after is not None:
                return self.client_after(self.client_reads)
            return Completed(0, self.client_rows, "")
        return super().__call__(args, deadline)


class AttachmentCollectorTests(unittest.TestCase):
    def source(self):
        native = AssociationFixture()
        collector = Collector("fixture", runner=native)
        observation = collector.collect()
        return native, collector, observation

    def sample(self, collector, observation, *, process=None):
        return AttachmentCollector(
            collector, process_identity=process or (lambda *_args: 500)
        ).sample(observation, boottime_ms() + 2000)

    def test_complete_native_client_maps_only_full_references(self):
        native, collector, observation = self.source()
        value = self.sample(collector, observation)
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertEqual(value["clients"][0]["sessionRef"]["createdAt"], 101)
        self.assertEqual(value["clients"][0]["processStartTicks"], 500)
        self.assertEqual(native.client_reads, 2)
        self.assertTrue(all(allowed_read(args) for args, _deadline in native.calls))

    def test_closing_client_and_generation_share_one_bounded_read_chain(self):
        native, collector, observation = self.source()
        value = self.sample(collector, observation)
        self.assertEqual(value["sample"]["coverage"], "complete")
        chained = [
            args for args, _deadline in native.calls if ";" in args and args[0] == "list-clients"
        ]
        self.assertEqual(len(chained), 1)
        self.assertEqual(chained[0][:3], ["list-clients", "-F", CLIENT_FIELDS])
        self.assertEqual(chained[0][4:6], ["list-sessions", "-F"])

    def test_empty_closing_rows_keep_live_generation_instead_of_proving_absence(self):
        native, collector, observation = self.source()
        native.client_rows = ""
        native.final = ""
        value = self.sample(collector, observation)
        self.assertEqual(value["sample"]["coverage"], "failed")
        self.assertEqual(value["clients"], [])
        self.assertIsNone(value["serverGeneration"])

    def test_client_switch_during_sample_is_unknown_not_old_binding(self):
        native, collector, observation = self.source()
        native.client_after = lambda count: Completed(0, f"123\t${count}\t101\n", "")
        value = self.sample(collector, observation)
        self.assertEqual(value["sample"]["coverage"], "failed")
        self.assertEqual(value["clients"], [])
        self.assertIsNone(value["serverGeneration"])
        self.assertEqual(observation["sample"]["coverage"], "complete")

    def test_process_reuse_uid_failure_and_missing_process_revoke_join(self):
        for identity in ("reuse", "uid", "missing"):
            _native, collector, observation = self.source()
            calls = 0

            def process(*_args, selected=identity):
                nonlocal calls
                calls += 1
                if selected == "uid":
                    raise ProcessError("process_scope", "wrong UID")
                if selected == "missing":
                    raise FileNotFoundError()
                return 500 + calls

            with self.subTest(identity=identity):
                value = self.sample(collector, observation, process=process)
                self.assertEqual(value["sample"]["coverage"], "failed")
                self.assertEqual(value["sessions"], [])
                self.assertEqual(value["clients"], [])

    def test_generation_or_created_at_reuse_rejects_previous_owner_basis(self):
        for changed in ("generation", "created"):
            native, collector, observation = self.source()
            if changed == "generation":
                native.generation = "/tmp/fixture/default\t110\t210\n"
            else:
                native.final = "$1\t999\n"
            with self.subTest(changed=changed):
                value = self.sample(collector, observation)
                self.assertEqual(value["sample"]["coverage"], "failed")
                self.assertEqual(value["clients"], [])

    def test_duplicate_partial_and_over_capacity_cannot_prove_absence(self):
        for rows in ("123\t$1\t101\n" * 2, "malformed\n", "123\t$1\t101\n" * 513):
            native, collector, observation = self.source()
            native.client_rows = rows
            value = self.sample(collector, observation)
            self.assertEqual(value["sample"]["coverage"], "failed")
            self.assertEqual(value["clients"], [])
        native, collector, observation = self.source()
        native.client_rows = ""
        value = self.sample(collector, observation)
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertEqual(len(value["sessions"]), 1)
        self.assertEqual(value["clients"], [])

    def test_real_process_identity_is_bounded_uid_and_deadline_checked(self):
        self.assertGreater(process_start(os.getpid(), os.getuid(), boottime_ms() + 500), 0)
        with self.assertRaises(ProcessError):
            process_start(os.getpid(), os.getuid() + 1, boottime_ms() + 500)
        with self.assertRaises(ProcessError):
            process_start(os.getpid(), os.getuid(), boottime_ms())
        _native, collector, observation = self.source()
        value = AttachmentCollector(collector, namespace="pid:0").sample(
            observation, boottime_ms() + 500
        )
        self.assertEqual(value["sample"]["coverage"], "failed")

    def test_independent_receipt_expiry_and_failure_retain_history(self):
        _native, collector, observation = self.source()
        sampled = self.sample(collector, observation)
        sampled["sample"].update(startedAt=110, finishedAt=120)
        state = AttachmentState(
            collector.source,
            collector.clock,
            pid_namespace(),
            publisher_id="11111111-1111-4111-8111-111111111111",
        )
        self.assertIsNone(state.frame(100)["snapshot"])
        self.assertTrue(state.finish(state.begin(100), sampled, 125))
        first = state.frame(130)
        self.assertEqual(first["receipt"]["expiresAt"], 10110)
        self.assertEqual(first["receipt"]["remainingMs"], 9980)
        self.assertEqual(state.frame(10110)["receipt"]["state"], "expired")
        self.assertEqual(state.evidence["accepted"], 1)
        token = state.begin(10110)
        failed = copy.deepcopy(sampled)
        failed.update(serverGeneration=None, sessions=[], clients=[])
        failed["sample"].update(
            startedAt=10110,
            finishedAt=10120,
            coverage="failed",
            error={"code": "association_failed", "message": "fixture source failure"},
        )
        self.assertFalse(state.finish(token, failed, 10125))
        frame = state.frame(10130)
        self.assertEqual(frame["receipt"]["remainingMs"], 0)
        self.assertEqual(frame["snapshot"], sampled)
