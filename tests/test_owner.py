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

    def test_scope_and_unimplemented_control_fail_without_sampling(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-owner-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = self.start(path)
            try:
                for selected, code in (
                    (request(expectedHost="other"), "scope_mismatch"),
                    (request(publisherId="22222222-2222-4222-8222-222222222222"), "stale_scope"),
                    (
                        request(
                            "refresh", sources=[{"hostId": "fixture-local", "source": "owner"}]
                        ),
                        "unsupported_operation",
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
