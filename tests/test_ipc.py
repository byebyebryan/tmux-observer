"""Endpoint ownership tests use disposable private directories and sockets."""

import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from tmux_observer._clock import boottime_ms
from tmux_observer._ipc import Endpoint, IPCError, connect, exchange


class IPCTests(unittest.TestCase):
    def test_exclusive_lease_and_socket_permissions(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ipc-") as temporary:
            path = Path(temporary) / "owner.sock"
            with Endpoint(path):
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                inode = path.stat().st_ino
                with self.assertRaises(IPCError) as error:
                    Endpoint(path)
                self.assertEqual(error.exception.code, "publisher_running")
                self.assertEqual(path.stat().st_ino, inode)
                with connect(path, deadline=boottime_ms() + 1000):
                    pass
            self.assertFalse(path.exists())

    def test_stale_socket_can_be_reclaimed_but_live_unleased_socket_cannot(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ipc-") as temporary:
            path = Path(temporary) / "owner.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as old:
                old.bind(str(path))
            with Endpoint(path):
                pass
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as live:
                live.bind(str(path))
                live.listen()
                inode = path.stat().st_ino
                with self.assertRaises(IPCError) as error:
                    Endpoint(path)
                self.assertEqual(error.exception.code, "publisher_running")
                self.assertEqual(path.stat().st_ino, inode)

    def test_symlinks_and_nonprivate_parents_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ipc-") as temporary:
            path = Path(temporary) / "owner.sock"
            path.symlink_to(Path(temporary) / "unrelated")
            with self.assertRaises(IPCError):
                Endpoint(path)
            self.assertTrue(path.is_symlink())
            path.unlink()
            Path(temporary).chmod(0o755)
            with self.assertRaises(IPCError):
                Endpoint(path)

    def test_no_service_read_does_not_create_anything(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ipc-") as temporary:
            path = Path(temporary) / "owner.sock"
            before = list(Path(temporary).iterdir())
            request = {
                "protocol": "tmux-observer.service.v1",
                "schemaVersion": 1,
                "operation": "snapshot",
                "requestId": "request-1",
                "expectedHost": "fixture-local",
            }
            with self.assertRaises(IPCError) as error:
                exchange(request, path=path)
            self.assertEqual(error.exception.code, "service_absent")
            self.assertEqual(list(Path(temporary).iterdir()), before)

    def test_client_rejects_oversized_or_incomplete_records(self):
        for output in (b"x" * 1100000, b"{}"):
            with tempfile.TemporaryDirectory(prefix="tmux-observer-ipc-") as temporary:
                path = Path(temporary) / "owner.sock"
                with Endpoint(path) as endpoint:
                    endpoint.socket.setblocking(True)

                    def serve(record=output):
                        peer, _address = endpoint.socket.accept()
                        with peer:
                            peer.recv(16384)
                            try:
                                peer.sendall(record)
                            except BrokenPipeError:
                                pass

                    worker = threading.Thread(target=serve)
                    worker.start()
                    request = {
                        "protocol": "tmux-observer.service.v1",
                        "schemaVersion": 1,
                        "operation": "status",
                        "requestId": "request-1",
                        "expectedHost": "fixture-local",
                    }
                    with self.assertRaises(IPCError):
                        exchange(request, path=path)
                    worker.join(timeout=2)
                    self.assertFalse(worker.is_alive())

    def test_endpoint_cleanup_preserves_replaced_inode(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ipc-") as temporary:
            path = Path(temporary) / "owner.sock"
            endpoint = Endpoint(path)
            path.unlink()
            path.write_text("replacement")
            endpoint.close()
            self.assertEqual(path.read_text(), "replacement")
            self.assertEqual(os.getuid(), path.stat().st_uid)
