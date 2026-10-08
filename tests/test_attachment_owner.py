"""Optional local source over real IPC; default owner exports remain PID-free."""

import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests.test_owner import SyntheticCollector, request
from tmux_observer._clock import boottime_ms, pid_namespace
from tmux_observer._ipc import IPCError, exchange
from tmux_observer.attachments import ATTACHMENT_DELIVERY_PROTOCOL
from tmux_observer.owner import OwnerPublisher


class SyntheticAssociations:
    def __init__(self, collector):
        self.collector = collector
        self.namespace = pid_namespace()
        self.calls = 0
        self.fail = False
        self.entered = threading.Event()
        self.release = None

    def sample(self, observation, deadline):
        self.calls += 1
        self.entered.set()
        if self.release is not None:
            self.release.wait(0.8)
        now = boottime_ms()
        refs = [
            {key: row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")}
            for row in observation["sessions"]
        ]
        value = {
            "protocol": "tmux-observer.attachments.v1",
            "schemaVersion": 1,
            "source": self.collector.source,
            "clock": self.collector.clock,
            "pidNamespace": self.namespace,
            "sample": {
                "startedAt": now,
                "finishedAt": now,
                "observedAt": 1700000000000,
                "coverage": "complete",
                "error": None,
            },
            "serverGeneration": observation["serverGeneration"],
            "sessions": refs,
            "clients": [],
        }
        if self.fail:
            value.update(serverGeneration=None, sessions=[], clients=[])
            value["sample"].update(
                coverage="failed",
                error={"code": "association_failed", "message": "fixture join unavailable"},
            )
        return value


def association_request(**extra):
    return {
        "protocol": ATTACHMENT_DELIVERY_PROTOCOL,
        "schemaVersion": 1,
        "operation": "snapshot",
        "requestId": "local-read",
        "expectedHost": "fixture-local",
        **extra,
    }


class AttachmentOwnerTests(unittest.TestCase):
    def start(self, path, *, failure=False, release=None):
        collector = SyntheticCollector()
        associations = SyntheticAssociations(collector)
        associations.fail = failure
        associations.release = release
        publisher = OwnerPublisher(
            "fixture-local",
            path=path,
            collector=collector,
            local_attachments=True,
            attachment_collector=associations,
        )
        thread = threading.Thread(target=publisher.run)
        thread.start()
        self.addCleanup(publisher.stop)
        self.addCleanup(lambda: thread.join(timeout=3))
        # unittest cleanup runs in reverse registration order.
        self.addCleanup(publisher.stop)
        until = time.monotonic() + 2
        while time.monotonic() < until:
            try:
                frame = exchange(request(), path=path)
            except (IPCError, OSError):
                time.sleep(0.01)
                continue
            if frame["receipt"]["state"] == "ready":
                return publisher, thread, collector, associations
            time.sleep(0.01)
        self.fail("owner source did not become ready")

    def profile(self, publisher):
        until = time.monotonic() + 2
        while time.monotonic() < until:
            frame = exchange(association_request(), path=publisher.attachment_path)
            if frame["receipt"]["state"] != "warming":
                return frame
            time.sleep(0.01)
        self.fail("optional profile did not finish")

    def test_many_cached_reads_share_source_and_echo_nonce(self):
        with tempfile.TemporaryDirectory(prefix="observer-local-profile-") as temporary:
            publisher, thread, collector, associations = self.start(Path(temporary) / "owner.sock")
            try:
                self.assertEqual(self.profile(publisher)["receipt"]["state"], "ready")
                # Freeze only this owned synthetic source's next scheduled slot;
                # elapsed cadence renewal is independent of read amplification.
                publisher.state.next_due = boottime_ms() + 60000
                for index in range(20):
                    frame = exchange(
                        association_request(requestId=f"read-{index}"),
                        path=publisher.attachment_path,
                    )
                    self.assertEqual(frame["requestId"], f"read-{index}")
                    self.assertEqual(frame["receipt"]["attempted"], 1)
                self.assertEqual(collector.calls, 1)
                self.assertEqual(associations.calls, 1)
                owner = exchange(request(), path=publisher.path)
                self.assertNotIn("clients", owner)
                self.assertNotIn("localAttachments", owner)
                self.assertNotIn("pidNamespace", owner)
                for operation in ("refresh", "watch", "kill"):
                    with self.assertRaises(ValueError):
                        exchange(
                            association_request(operation=operation), path=publisher.attachment_path
                        )
                with self.assertRaises(IPCError) as error:
                    exchange(
                        association_request(expectedHost="other"), path=publisher.attachment_path
                    )
                self.assertEqual(error.exception.code, "scope_mismatch")
            finally:
                publisher.stop()
                thread.join(timeout=3)
            self.assertFalse(publisher.path.exists())
            self.assertFalse(publisher.attachment_path.exists())

    def test_failure_is_independent_of_healthy_roster(self):
        with tempfile.TemporaryDirectory(prefix="observer-local-failure-") as temporary:
            publisher, thread, _collector, _associations = self.start(
                Path(temporary) / "owner.sock", failure=True
            )
            try:
                failed = self.profile(publisher)
                owner = exchange(request(), path=publisher.path)
                self.assertEqual(failed["receipt"]["state"], "failed")
                self.assertEqual(failed["receipt"]["remainingMs"], 0)
                self.assertEqual(owner["receipt"]["state"], "ready")
                self.assertEqual(len(owner["snapshot"]["sessions"]), 1)
            finally:
                publisher.stop()
                thread.join(timeout=3)

    def test_slow_profile_does_not_delay_prepared_roster_or_schedule_on_read(self):
        with tempfile.TemporaryDirectory(prefix="observer-local-slow-") as temporary:
            release = threading.Event()
            publisher, thread, collector, associations = self.start(
                Path(temporary) / "owner.sock", release=release
            )
            try:
                self.assertTrue(associations.entered.wait(1))
                frame = exchange(association_request(), path=publisher.attachment_path)
                self.assertEqual(frame["receipt"]["state"], "warming")
                self.assertTrue(frame["receipt"]["inFlight"])
                self.assertEqual(
                    exchange(request(), path=publisher.path)["receipt"]["state"], "ready"
                )
                self.assertEqual(collector.calls, 1)
                release.set()
                self.assertEqual(self.profile(publisher)["receipt"]["state"], "ready")
            finally:
                release.set()
                publisher.stop()
                thread.join(timeout=3)

    def test_absent_profile_is_typed_without_owner_activation(self):
        with tempfile.TemporaryDirectory(prefix="observer-profile-absent-") as temporary:
            path = Path(temporary) / "attachments.sock"
            with self.assertRaises(IPCError) as error:
                exchange(association_request(), path=path)
            self.assertEqual(error.exception.code, "service_absent")
            self.assertFalse(path.exists())
