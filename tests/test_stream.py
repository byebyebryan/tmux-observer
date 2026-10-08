"""Actual CLI pipes and owner IPC, including disconnect and stream fencing."""

import json
import os
import selectors
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import test_owner
from test_owner import request

from tmux_observer._clock import boottime_ms
from tmux_observer._ipc import Endpoint, exchange
from tmux_observer._owner_state import OwnerState
from tmux_observer.public import decode_document, encode_document, validate_service_frame


class StreamTests(unittest.TestCase):
    def launch(self, path, operation="bridge", host="fixture-local"):
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tmux_observer",
                operation,
                "--expected-host",
                host,
                "--socket",
                str(path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.addCleanup(self.cleanup_process, process)
        return process

    @staticmethod
    def cleanup_process(process):
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=3)

    def read_line(self, process, pending):
        deadline = time.monotonic() + 3
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while b"\n" not in pending:
                self.assertLess(time.monotonic(), deadline, "CLI did not emit a frame")
                if not selector.select(0.05):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                self.assertTrue(chunk, "CLI ended before a complete frame")
                pending.extend(chunk)
        raw, _, rest = pending.partition(b"\n")
        pending[:] = rest
        return decode_document(bytes(raw) + b"\n", limit=1064960)

    def test_bridge_nonce_reads_and_eof_leave_publisher_alive(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-bridge-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = test_owner.OwnerTests().start(path)
            try:
                process = self.launch(path)
                pending = bytearray()
                first = validate_service_frame(self.read_line(process, pending))
                self.assertEqual(first["kind"], "resync")
                for index in range(8):
                    process.stdin.write(encode_document(request("probe", requestId=f"p-{index}")))
                    process.stdin.flush()
                    frame = validate_service_frame(self.read_line(process, pending))
                    self.assertEqual(frame["requestId"], f"p-{index}")
                    self.assertEqual(frame["publisherId"], first["publisherId"])
                    self.assertEqual(frame["sequence"], index + 1)
                self.assertEqual(collector.calls, 1)
                process.stdin.close()
                process.stdin = None
                self.assertEqual(process.wait(timeout=3), 0)
                self.assertEqual(
                    exchange(request(), path=path)["publisherId"], first["publisherId"]
                )
            finally:
                publisher.stop()
                thread.join(timeout=3)
            self.assertFalse(thread.is_alive())

    def test_missing_service_and_invalid_context_are_typed_without_autostart(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-missing-") as temporary:
            path = Path(temporary) / "missing" / "owner.sock"
            for operation, host in (("watch", "fixture-local"), ("bridge", "bad host")):
                process = self.launch(path, operation, host)
                output, _diagnostic = process.communicate(timeout=3)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(decode_document(output)["kind"], "operation_error")
                self.assertFalse(path.parent.exists())

    def test_foreign_bridge_request_ends_only_that_client(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-bridge-scope-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, _collector = test_owner.OwnerTests().start(path)
            try:
                process = self.launch(path)
                self.read_line(process, bytearray())
                process.stdin.write(encode_document(request("probe", expectedHost="other")))
                process.stdin.flush()
                self.assertEqual(process.wait(timeout=3), 1)
                self.assertEqual(exchange(request(), path=path)["receipt"]["state"], "ready")
            finally:
                publisher.stop()
                thread.join(timeout=3)

    def test_fragmented_large_frames_and_publisher_replay_fencing(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-bridge-wire-") as temporary:
            path = Path(temporary) / "owner.sock"
            errors = []
            with Endpoint(path) as endpoint:

                def serve():
                    try:
                        endpoint.socket.settimeout(3)
                        sock, _ = endpoint.socket.accept()
                        with sock:
                            sock.settimeout(3)
                            watch = decode_document(sock.makefile("rb").readline())
                            sample = json.loads(
                                (
                                    Path(__file__).resolve().parent.parent
                                    / "contracts/observation-v1/fixtures/complete.json"
                                ).read_text()
                            )
                            from tmux_observer._clock import domain

                            sample["source"].update(hostId="fixture-local", uid=os.getuid())
                            sample["clock"] = domain()
                            now = boottime_ms()
                            sample["sample"].update(startedAt=now, finishedAt=now)
                            row = sample["sessions"][0]
                            sample["sessions"] = [
                                {**row, "sessionId": "$" + str(i), "name": "x" * 16000}
                                for i in range(60)
                            ]
                            state = OwnerState(sample["source"], sample["clock"])
                            state.finish(state.begin(now), sample, now)
                            first = state.frame(
                                now, kind="resync", sequence=0, request_id=watch["requestId"]
                            )
                            second = state.frame(now, kind="heartbeat", sequence=1)
                            raw = encode_document(first, limit=1064960) + encode_document(
                                second, limit=1064960
                            )
                            for start in range(0, len(raw), 31001):
                                sock.sendall(raw[start : start + 31001])
                            sock.recv(16384)  # Reader acknowledges both complete records.
                            # Replayed sequence must end the bridge without forwarding it.
                            sock.sendall(encode_document(second, limit=1064960))
                            time.sleep(0.2)
                    except (OSError, ValueError, KeyError, TypeError) as error:
                        errors.append(error)

                thread = threading.Thread(target=serve)
                thread.start()
                process = self.launch(path)
                pending = bytearray()
                first = validate_service_frame(self.read_line(process, pending))
                second = validate_service_frame(self.read_line(process, pending))
                self.assertEqual((first["sequence"], second["sequence"]), (0, 1))
                process.stdin.write(encode_document(request("probe")))
                process.stdin.flush()
                self.assertEqual(process.wait(timeout=3), 1)
                thread.join(timeout=3)
                self.assertFalse(errors, errors)
