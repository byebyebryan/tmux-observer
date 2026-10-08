"""Prepared facade scope checks and read-time expiry using an independent frame."""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tmux_observer._clock import domain
from tmux_observer._ipc import Endpoint, IPCError
from tmux_observer.public import validate_fleet_frame
from tmux_observer_client.public import owner_current, read_cached


class CachedTests(unittest.TestCase):
    def test_validation_finishing_at_or_after_deadline_cannot_return_success(self):
        fixture = json.loads(
            (
                Path(__file__).resolve().parent.parent / "contracts/fleet-v1/fixtures/frame.json"
            ).read_text()
        )
        fixture["clock"] = domain()
        fixture["snapshot"]["clock"] = domain()
        for host in fixture["snapshot"]["hosts"]:
            if host["local"]:
                host["owner"]["clock"] = domain()
        context = fixture["contextId"]
        for finished in (1249, 1250, 1251):
            with (
                self.subTest(finished=finished),
                tempfile.TemporaryDirectory(prefix="tmux-observer-cached-validation-") as temporary,
            ):
                path = Path(temporary) / "fleet.sock"
                clock = [1000]
                errors = []
                with Endpoint(path) as endpoint:

                    def serve(errors=errors):
                        try:
                            endpoint.socket.settimeout(1)
                            sock, _ = endpoint.socket.accept()
                            with sock, sock.makefile("rb") as stream:
                                request = json.loads(stream.readline())
                                sock.sendall(
                                    json.dumps(
                                        {**fixture, "requestId": request["requestId"]}
                                    ).encode()
                                    + b"\n"
                                )
                        except (OSError, ValueError) as error:
                            errors.append(error)

                    def validate(value, clock=clock, finished=finished):
                        result = validate_fleet_frame(value)
                        clock[0] = finished
                        return result

                    thread = threading.Thread(target=serve)
                    thread.start()
                    try:
                        with (
                            patch(
                                "tmux_observer._ipc.boottime_ms",
                                side_effect=lambda clock=clock: clock[0],
                            ),
                            patch("tmux_observer._ipc.validate_fleet_frame", side_effect=validate),
                        ):
                            if finished < 1250:
                                self.assertEqual(
                                    read_cached(context, path=path)["contextId"], context
                                )
                            else:
                                with self.assertRaises(IPCError) as error:
                                    read_cached(context, path=path)
                                self.assertEqual(error.exception.code, "deadline")
                    finally:
                        thread.join(timeout=2)
                        self.assertFalse(thread.is_alive())
                        self.assertFalse(errors, errors)

    def test_slow_prepared_reply_has_a_foreground_deadline_without_fallback(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-cached-deadline-") as temporary:
            path = Path(temporary) / "fleet.sock"
            with Endpoint(path) as endpoint:

                def serve():
                    endpoint.socket.settimeout(1)
                    sock, _address = endpoint.socket.accept()
                    with sock:
                        sock.recv(16384)
                        time.sleep(0.4)

                thread = threading.Thread(target=serve)
                thread.start()
                began = time.monotonic()
                with self.assertRaises(IPCError) as error:
                    read_cached("0" * 32, path=path)
                self.assertEqual(error.exception.code, "deadline")
                self.assertLess(time.monotonic() - began, 0.35)
                thread.join(timeout=1)
                self.assertFalse(thread.is_alive())

    def test_missing_reader_creates_nothing(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-cached-missing-") as temporary:
            path = Path(temporary) / "absent" / "fleet.sock"
            with self.assertRaises((IPCError, OSError)):
                read_cached("0" * 32, path=path)
            self.assertFalse(path.parent.exists())

    def test_context_incarnation_and_expected_host_are_bound_and_expiry_is_checked_at_read(self):
        fixture = json.loads(
            (
                Path(__file__).resolve().parent.parent / "contracts/fleet-v1/fixtures/frame.json"
            ).read_text()
        )
        fixture["clock"] = domain()
        fixture["snapshot"]["clock"] = domain()
        for host in fixture["snapshot"]["hosts"]:
            if host["local"]:
                host["owner"]["clock"] = domain()
        local = fixture["snapshot"]["mesh"]["localHostId"]
        context = fixture["contextId"]
        with tempfile.TemporaryDirectory(prefix="tmux-observer-cached-") as temporary:
            path = Path(temporary) / "fleet.sock"
            errors = []
            with Endpoint(path) as endpoint:

                def serve():
                    try:
                        endpoint.socket.settimeout(3)
                        for _ in range(3):
                            sock, _ = endpoint.socket.accept()
                            with sock:
                                sock.settimeout(2)
                                with sock.makefile("rb") as stream:
                                    request = json.loads(stream.readline())
                                frame = {
                                    **fixture,
                                    "requestId": request["requestId"],
                                    "sequence": 0,
                                }
                                sock.sendall(
                                    json.dumps(frame, separators=(",", ":")).encode() + b"\n"
                                )
                    except (OSError, ValueError) as error:
                        errors.append(error)

                thread = threading.Thread(target=serve)
                thread.start()
                value = read_cached(context, expected_host=local, path=path)
                self.assertFalse(owner_current(value["snapshot"], value["snapshot"]["hosts"][0]))
                for extra in (
                    {"expected_host": "foreign"},
                    {"publisher_id": "22222222-2222-4222-8222-222222222222"},
                ):
                    with self.assertRaises(IPCError):
                        read_cached(context, path=path, **extra)
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertFalse(errors, errors)
