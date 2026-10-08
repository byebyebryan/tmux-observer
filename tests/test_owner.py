"""Concrete publisher sharing over real Unix IPC with a synthetic source."""

import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tmux_observer._clock import boottime_ms, domain
from tmux_observer._ipc import IPCError, connect, exchange
from tmux_observer.owner import OwnerPublisher
from tmux_observer.public import (
    SERVICE_PROTOCOL,
    decode_document,
    encode_document,
    validate_service_frame,
)


class SyntheticCollector:
    def __init__(self):
        self.source = {
            "hostId": "fixture-local",
            "uid": os.getuid(),
            "server": "default",
            "nativeHostname": "fixture",
        }
        self.clock = domain()
        self.calls = 0

    def collect(self, *, budget_ms):
        self.calls += 1
        started = boottime_ms()
        root = Path(__file__).resolve().parent.parent
        value = json.loads((root / "contracts/observation-v1/fixtures/complete.json").read_text())
        value.update(source=self.source, clock=self.clock)
        value["sample"].update(startedAt=started, finishedAt=boottime_ms())
        return value


def request(operation="snapshot", **extra):
    return {
        "protocol": SERVICE_PROTOCOL,
        "schemaVersion": 1,
        "operation": operation,
        "requestId": "request-1",
        "expectedHost": "fixture-local",
        **extra,
    }


class OwnerTests(unittest.TestCase):
    def start(self, path):
        collector = SyntheticCollector()
        publisher = OwnerPublisher("fixture-local", path=path, collector=collector)
        thread = threading.Thread(target=publisher.run)
        thread.start()
        until = time.monotonic() + 2
        while time.monotonic() < until:
            try:
                frame = exchange(request(), path=path)
            except IPCError:
                time.sleep(0.01)
                continue
            if frame["receipt"]["state"] == "ready":
                return publisher, thread, collector
            time.sleep(0.01)
        publisher.stop()
        thread.join(timeout=3)
        raise AssertionError("synthetic publisher did not become ready")

    def test_many_reads_share_one_sample_and_probes_echo_nonce(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-owner-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = self.start(path)
            try:
                for index in range(20):
                    frame = exchange(request("probe", requestId=f"probe-{index}"), path=path)
                    self.assertEqual(frame["receipt"]["attempted"], 1)
                    self.assertEqual(frame["requestId"], f"probe-{index}")
                self.assertEqual(collector.calls, 1)
            finally:
                publisher.stop()
                thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(path.exists())

    def test_scope_and_unknown_ticket_fail_without_sampling(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-owner-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = self.start(path)
            try:
                for selected, code in (
                    (request(expectedHost="other"), "scope_mismatch"),
                    (request(publisherId="22222222-2222-4222-8222-222222222222"), "stale_scope"),
                    (
                        request(
                            "refresh_status",
                            ticketId="33333333-3333-4333-8333-333333333333",
                            publisherId=publisher.state.publisher_id,
                        ),
                        "ticket_not_found",
                    ),
                ):
                    with self.assertRaises(IPCError) as error:
                        exchange(selected, path=path)
                    self.assertEqual(error.exception.code, code)
                self.assertEqual(collector.calls, 1)
            finally:
                publisher.stop()
                thread.join(timeout=3)

    def test_watch_and_probe_share_stream_with_monotonic_sequence(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-owner-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = self.start(path)
            try:
                with connect(path, deadline=boottime_ms() + 1000) as sock:
                    sock.settimeout(2)
                    sock.sendall(encode_document(request("watch")))
                    stream = sock.makefile("rb")
                    first = validate_service_frame(decode_document(stream.readline()))
                    self.assertEqual(first["kind"], "resync")
                    sock.sendall(encode_document(request("probe", requestId="probe-2")))
                    second = validate_service_frame(decode_document(stream.readline()))
                    self.assertEqual(second["requestId"], "probe-2")
                    self.assertEqual(second["sequence"], first["sequence"] + 1)
                    self.assertEqual(second["receipt"]["accepted"], first["receipt"]["accepted"])
                    stream.close()
                self.assertEqual(collector.calls, 1)
            finally:
                publisher.stop()
                thread.join(timeout=3)

    def test_malformed_request_is_typed_and_does_not_stop_other_readers(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-owner-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, _collector = self.start(path)
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect(str(path))
                    sock.sendall(b'{"protocol":"invalid"}\n')
                    value = decode_document(sock.makefile("rb").readline())
                    self.assertEqual(value["kind"], "operation_error")
                self.assertEqual(exchange(request(), path=path)["receipt"]["state"], "ready")
            finally:
                publisher.stop()
                thread.join(timeout=3)

    def test_refresh_accepted_during_old_job_requires_one_successor(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-causal-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = self.start(path)
            entered = threading.Event()
            release = threading.Event()
            original = collector.collect

            def blocked(*, budget_ms):
                if collector.calls == 1:
                    entered.set()
                    if not release.wait(0.8):
                        raise TimeoutError("owned test release deadline")
                return original(budget_ms=budget_ms)

            collector.collect = blocked
            try:
                scopes = [{"hostId": "fixture-local", "source": "owner"}]
                first = exchange(request("refresh", sources=scopes), path=path)["ticket"]
                self.assertTrue(entered.wait(1.5))
                later = [
                    exchange(request("refresh", sources=scopes, requestId=f"late-{i}"), path=path)[
                        "ticket"
                    ]
                    for i in range(4)
                ]
                self.assertTrue(all(value["state"] == "coalesced" for value in later))
                release.set()
                until = time.monotonic() + 3
                while time.monotonic() < until:
                    values = [
                        exchange(
                            request(
                                "refresh_status",
                                ticketId=value["id"],
                                publisherId=value["publisherId"],
                            ),
                            path=path,
                        )["ticket"]
                        for value in [first, *later]
                    ]
                    if all(value["state"] == "complete" for value in values):
                        break
                    time.sleep(0.03)
                self.assertEqual(values[0]["sources"][0]["attempt"], 2)
                self.assertTrue(
                    all(
                        value["state"] == "complete" and value["sources"][0]["attempt"] == 3
                        for value in values[1:]
                    )
                )
                self.assertEqual(collector.calls, 3)
                for _ in range(4):
                    exchange(
                        request(
                            "refresh_status", ticketId=first["id"], publisherId=first["publisherId"]
                        ),
                        path=path,
                    )
                self.assertEqual(collector.calls, 3)
            finally:
                release.set()
                publisher.stop()
                thread.join(timeout=3)

    def test_unchanged_native_acceptance_publishes_receipt_before_periodic_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-renewal-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, _collector = self.start(path)
            try:
                with connect(path, deadline=boottime_ms() + 1000) as sock:
                    sock.settimeout(2.4)
                    sock.sendall(encode_document(request("watch")))
                    with sock.makefile("rb") as stream:
                        first = validate_service_frame(decode_document(stream.readline()))
                        next_frame = validate_service_frame(decode_document(stream.readline()))
                        self.assertEqual(next_frame["viewRevision"], first["viewRevision"])
                        self.assertEqual(next_frame["receipt"]["acceptedAttempt"], 2)
                        self.assertEqual(next_frame["kind"], "heartbeat")
            finally:
                publisher.stop()
                thread.join(timeout=3)
