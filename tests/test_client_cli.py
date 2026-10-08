"""Explicit cached CLI failures and bounded real fleet stream framing."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import test_owner

from tmux_observer._clock import domain
from tmux_observer._ipc import Endpoint
from tmux_observer.public import FRAME_LIMIT, decode_document, encode_document, validate_fleet_frame
from tmux_observer_client.public import read_cached


class ClientCLITests(unittest.TestCase):
    def command(self, *args):
        return [sys.executable, "-m", "tmux_observer_client.cli", *map(str, args)]

    def test_missing_cached_service_and_invalid_scope_never_activate_or_collect(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-client-cli-") as temporary:
            path = Path(temporary) / "absent.sock"
            cases = (
                ("snapshot", "--access", "cached", "--socket", path, "--json"),
                ("watch", "--socket", path, "--json"),
                ("snapshot", "--access", "cached", "--panes", "--json"),
                ("refresh", "--source", "fixture-local:launch", "--json"),
                ("refresh_status", "--ticket-id", "11111111-1111-4111-8111-111111111111", "--json"),
                ("fleet", "--host-id", "fixture-local", "--context-id", "0" * 32, "--socket", path),
            )
            for args in cases:
                with self.subTest(args=args):
                    result = subprocess.run(
                        self.command(*args), capture_output=True, timeout=3, check=False
                    )
                    value = decode_document(result.stdout)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(value["protocol"], "tmux-observer.fleet.v1")
                    self.assertEqual(value["kind"], "operation_error")
                    self.assertFalse(path.exists())
                    self.assertFalse(path.with_suffix(".lock").exists())

    def test_explicit_fleet_cli_serves_cached_queries_and_stops_only_its_subscription(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-cli-") as temporary:
            root = Path(temporary)
            owner_path = root / "tmux-observer" / "owner.sock"
            publisher, owner_thread, _collector = test_owner.OwnerTests().start(owner_path)
            environment = {**os.environ, "XDG_RUNTIME_DIR": temporary, "PATH": temporary}
            for key in ("NIRI_SOCKET", "DISPLAY", "WAYLAND_DISPLAY"):
                environment.pop(key, None)
            context = (
                subprocess.run(
                    self.command("context"),
                    env=environment,
                    capture_output=True,
                    timeout=2,
                    check=True,
                )
                .stdout.decode()
                .strip()
            )
            path = root / "fleet.sock"
            process = subprocess.Popen(
                self.command(
                    "fleet", "--host-id", "fixture-local", "--context-id", context, "--socket", path
                ),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                until = time.monotonic() + 2
                while time.monotonic() < until:
                    result = subprocess.run(
                        self.command(
                            "snapshot",
                            "--access",
                            "cached",
                            "--context-id",
                            context,
                            "--socket",
                            path,
                            "--json",
                        ),
                        env=environment,
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
                    if result.returncode == 0:
                        frame = validate_fleet_frame(
                            decode_document(result.stdout, limit=FRAME_LIMIT)
                        )
                        if frame["snapshot"]["hosts"] and frame["snapshot"]["hosts"][0]["sessions"]:
                            break
                    time.sleep(0.02)
                else:
                    self.fail("explicit isolated fleet CLI did not prepare owner rows")
                self.assertEqual(frame["snapshot"]["mesh"]["state"], "local_only")
                self.assertEqual(
                    frame["snapshot"]["hosts"][0]["sessions"][0]["localViewer"]["state"], "unknown"
                )
                self.assertEqual(read_cached(context, path=path)["readerId"], frame["readerId"])
                process.terminate()
                stdout, stderr = process.communicate(timeout=3)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertFalse(stdout)
                self.assertFalse(path.exists())
                self.assertTrue(owner_path.exists())
                self.assertTrue(owner_thread.is_alive())
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=3)
                publisher.stop()
                owner_thread.join(timeout=3)

    def fixture(self):
        root = Path(__file__).resolve().parent.parent
        frame = json.loads((root / "contracts/fleet-v1/fixtures/frame.json").read_text())
        frame["clock"] = frame["snapshot"]["clock"] = domain()
        frame["snapshot"]["hosts"][0]["owner"]["clock"] = domain()
        frame["snapshot"]["hosts"][0]["owner"]["source"]["uid"] = os.getuid()
        return frame

    def server(self, path, frame, *, foreign=False, trickle=False):
        endpoint, errors = Endpoint(path), []

        def run():
            try:
                until = time.monotonic() + 2
                while True:
                    try:
                        sock, _address = endpoint.socket.accept()
                        break
                    except BlockingIOError:
                        if time.monotonic() >= until:
                            raise TimeoutError("owned watch client did not connect")
                        time.sleep(0.005)
                with sock:
                    sock.settimeout(2.5)
                    request = decode_document(sock.makefile("rb").readline(16385))
                    value = copy.deepcopy(frame)
                    value.update(kind="resync", sequence=0, requestId=request["requestId"])
                    raw = encode_document(validate_fleet_frame(value), limit=FRAME_LIMIT)
                    sock.sendall(raw[:17])
                    time.sleep(2.1 if trickle else 0.02)
                    try:
                        sock.sendall(raw[17:])
                        if not trickle:
                            time.sleep(0.03)
                            value.update(kind="view", sequence=1, requestId=None)
                            if foreign:
                                value["readerId"] = value["snapshot"]["readerId"] = (
                                    "22222222-2222-4222-8222-222222222222"
                                )
                            sock.sendall(
                                encode_document(validate_fleet_frame(value), limit=FRAME_LIMIT)
                            )
                            time.sleep(0.2)
                    except BrokenPipeError:
                        if not trickle:
                            raise
            except (OSError, ValueError) as error:
                errors.append(error)
            finally:
                endpoint.close()

        thread = threading.Thread(target=run)
        thread.start()
        return thread, errors

    def test_fragmented_near_cap_stream_keeps_complete_records(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-watch-") as temporary:
            path, frame = Path(temporary) / "fleet.sock", self.fixture()
            frame["snapshot"]["extension"] = ["x" * 16384] * 60
            thread, errors = self.server(path, frame)
            result = subprocess.run(
                self.command(
                    "watch", "--context-id", frame["contextId"], "--socket", path, "--json"
                ),
                capture_output=True,
                timeout=4,
                check=False,
            )
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors, errors)
            records = result.stdout.splitlines(keepends=True)
            self.assertEqual(
                len(records), 2, (result.stderr.decode(), [len(raw) for raw in records])
            )
            for sequence, raw in enumerate(records):
                value = validate_fleet_frame(decode_document(raw, limit=FRAME_LIMIT))
                self.assertEqual(value["sequence"], sequence)
                self.assertEqual(len(value["snapshot"]["extension"]), 60)
            self.assertEqual(result.returncode, 1)  # End of subscription invalidates its lifetime.

    def test_reader_restart_and_trickled_initial_frame_never_append_false_records(self):
        for trickle in (False, True):
            with (
                self.subTest(trickle=trickle),
                tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-watch-fault-") as temporary,
            ):
                path, frame = Path(temporary) / "fleet.sock", self.fixture()
                thread, errors = self.server(path, frame, foreign=not trickle, trickle=trickle)
                result = subprocess.run(
                    self.command(
                        "watch", "--context-id", frame["contextId"], "--socket", path, "--json"
                    ),
                    capture_output=True,
                    timeout=4,
                    check=False,
                )
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertFalse(errors, errors)
                records = result.stdout.splitlines(keepends=True)
                self.assertEqual(len(records), 1)
                value = decode_document(records[0], limit=FRAME_LIMIT)
                self.assertEqual(value["kind"], "operation_error" if trickle else "resync")
                self.assertEqual(result.returncode, 1)

    def test_full_stdout_pipe_has_a_send_based_cutoff_even_before_first_write(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-fleet-watch-blocked-") as temporary:
            path, frame = Path(temporary) / "fleet.sock", self.fixture()
            thread, errors = self.server(path, frame)
            read_fd, write_fd = os.pipe()
            os.set_blocking(write_fd, False)
            try:
                while True:
                    try:
                        os.write(write_fd, b"x" * 4096)
                    except BlockingIOError:
                        break
                began = time.monotonic()
                process = subprocess.Popen(
                    self.command(
                        "watch", "--context-id", frame["contextId"], "--socket", path, "--json"
                    ),
                    stdout=write_fd,
                    stderr=subprocess.PIPE,
                )
                try:
                    _stdout, stderr = process.communicate(timeout=3)
                    self.assertEqual(process.returncode, 1)
                    self.assertIn(b"deadline", stderr)
                    self.assertLess(time.monotonic() - began, 3)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.communicate(timeout=3)
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertFalse(errors, errors)
            finally:
                os.close(write_fd)
                os.close(read_fd)
