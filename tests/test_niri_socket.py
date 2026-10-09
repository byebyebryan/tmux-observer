"""Owned Niri socket framing, fixed read-only request and deadline checks."""

import contextlib
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tmux_observer_client import _niri_observation as niri


@contextlib.contextmanager
def compositor(reply, *, delay=0, fragmented=False):
    with tempfile.TemporaryDirectory(prefix="niri-read-") as private:
        path = Path(private) / "ipc.sock"
        requests = []
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(path))
            server.listen(1)
            server.settimeout(0.5)

            def serve():
                try:
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(0.5)
                        request = bytearray()
                        while b"\n" not in request:
                            chunk = connection.recv(64)
                            if not chunk:
                                return
                            request.extend(chunk)
                        requests.append(bytes(request))
                        time.sleep(delay)
                        if fragmented:
                            for byte in reply:
                                connection.sendall(bytes([byte]))
                        else:
                            connection.sendall(reply)
                except OSError:
                    pass

            thread = threading.Thread(target=serve)
            thread.start()
            try:
                with patch.dict(os.environ, NIRI_SOCKET=str(path)):
                    yield requests
            finally:
                thread.join(timeout=1)
                assert not thread.is_alive()


class NiriSocketTests(unittest.TestCase):
    def read(self, *, timeout=0.2):
        with (
            patch.object(niri, "run_bounded", side_effect=AssertionError("no compositor process")),
            patch.object(niri.shutil, "which", side_effect=AssertionError("no executable lookup")),
        ):
            return niri._niri_windows(("niri",), timeout_seconds=timeout)

    def test_fragmented_native_reply_preserves_titles_and_needs_no_cli(self):
        rows = [{"id": 1, "pid": 2, "title": "Unicode 界\nnext", "app_id": "kitty"}]
        raw = (json.dumps({"Ok": {"Windows": rows}}) + "\n").encode()
        with compositor(raw, fragmented=True) as requests:
            self.assertEqual(self.read(), rows)
        self.assertEqual(requests, [b'"Windows"\n'])

    def test_current_empty_reply_is_distinct_from_protocol_or_framing_failure(self):
        with compositor(b'{"Ok":{"Windows":[]}}\n'):
            self.assertEqual(self.read(), [])
        for raw in (
            b'{"Err":"unavailable"}\n',
            b'{"Ok":{"Workspaces":[]}}\n',
            b'{"Ok":{"Windows":[]},"Ok":{"Windows":[]}}\n',
            b'{"Ok":{"Windows":{}}}\n',
            b'{"Ok":{"Windows":[]}}',
            b'{"Ok":{"Windows":[]}}\nextra\n',
            b'{"Ok":{"Windows":[NaN]}}\n',
        ):
            with self.subTest(raw=raw), compositor(raw):
                self.assertIsNone(self.read())

    def test_record_and_window_count_caps_do_not_prove_empty(self):
        for raw, limit in (
            ((json.dumps({"Ok": {"Windows": [None] * 513}}) + "\n").encode(), 1024 * 1024),
            (b'{"Ok":{"Windows":[]}}\n', 10),
        ):
            with (
                self.subTest(limit=limit),
                compositor(raw),
                patch.object(niri, "_MAX_NIRI_BYTES", limit),
            ):
                self.assertIsNone(self.read())

    def test_slow_socket_and_post_parse_deadline_reject_late_results(self):
        with compositor(b'{"Ok":{"Windows":[]}}\n', delay=0.08):
            start = time.monotonic()
            self.assertIsNone(self.read(timeout=0.02))
            self.assertLess(time.monotonic() - start, 0.07)
        now = [0]
        original = json.loads

        def parse(*args, **kwargs):
            result = original(*args, **kwargs)
            now[0] = 1000
            return result

        with (
            compositor(b'{"Ok":{"Windows":[]}}\n'),
            patch.object(niri, "boottime_ms", side_effect=lambda: now[0]),
            patch.object(niri.json, "loads", side_effect=parse),
        ):
            self.assertIsNone(self.read(timeout=0.2))

    def test_foreign_peer_and_missing_socket_fail_without_a_second_transport(self):
        with (
            compositor(b'{"Ok":{"Windows":[]}}\n'),
            patch.object(niri.struct, "unpack", return_value=(1, os.getuid() + 1, 1)),
        ):
            self.assertIsNone(self.read())
        with patch.dict(os.environ, NIRI_SOCKET="/absent/owned-niri-fixture.sock"):
            self.assertIsNone(self.read())


if __name__ == "__main__":
    unittest.main()
