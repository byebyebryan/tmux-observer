"""Local prepared stream uses its actual clock and never owns a source worker."""

import os
import tempfile
import time
import unittest
from pathlib import Path

import test_owner

from tmux_observer._clock import boottime_ms, domain
from tmux_observer.public import SERVICE_PROTOCOL
from tmux_observer_client._local_stream import LocalConnection
from tmux_observer_client._remote_state import RemoteState


class LocalStreamTests(unittest.TestCase):
    def test_known_control_failure_preserves_owner_and_unknown_error_closes_stream(self):
        for handled in (True, False):
            with (
                self.subTest(handled=handled),
                tempfile.TemporaryDirectory(prefix="tmux-observer-local-control-") as temporary,
            ):
                path = Path(temporary) / "owner.sock"
                publisher, thread, _collector = test_owner.OwnerTests().start(path)
                failures = []

                def error(_connection, value, _now, failures=failures, handled=handled):
                    failures.append(value)
                    return handled and value.get("requestId") == "known-control"

                connection = LocalConnection(
                    "fixture-local", boottime_ms(), path=path, on_error=error
                )
                try:
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline and connection.state.confirmed is None:
                        connection.poll(boottime_ms())
                        time.sleep(0.005)
                    self.assertIsNotNone(connection.state.confirmed)
                    connection.send(
                        {
                            "protocol": SERVICE_PROTOCOL,
                            "schemaVersion": 1,
                            "operation": "status",
                            "requestId": "known-control",
                            "expectedHost": "fixture-local",
                            "publisherId": "11111111-1111-4111-8111-111111111111",
                        },
                        boottime_ms(),
                    )
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline and not failures:
                        connection.poll(boottime_ms())
                        time.sleep(0.005)
                    self.assertEqual(failures[0]["error"]["code"], "stale_scope")
                    self.assertEqual(connection.closed, not handled)
                    if handled:
                        self.assertGreater(connection.state.expiry, boottime_ms())
                    else:
                        self.assertEqual(connection.state.expiry, 0)
                finally:
                    connection.close()
                    publisher.stop()
                    thread.join(timeout=3)

    def test_local_read_shares_source_and_uses_owner_absolute_expiry(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-local-stream-") as temporary:
            path = Path(temporary) / "owner.sock"
            publisher, thread, collector = test_owner.OwnerTests().start(path)
            connection = LocalConnection("fixture-local", boottime_ms(), path=path)
            try:
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline and connection.state.confirmed is None:
                    connection.poll(boottime_ms())
                    time.sleep(0.01)
                owner, rows = connection.state.project()
                self.assertTrue(rows)
                self.assertEqual(owner["transport"], "local")
                self.assertIsNone(owner["proof"])
                self.assertEqual(owner["localExpiry"], owner["receipt"]["expiresAt"])
                self.assertEqual(collector.calls, 1)
                self.assertEqual(owner["source"]["uid"], os.getuid())
            finally:
                connection.close()
                publisher.stop()
                thread.join(timeout=3)

    def test_foreign_clock_local_frame_cannot_supply_positive_lease(self):
        import json

        from tmux_observer_client._errors import ContractError

        frame = json.loads(
            (
                Path(__file__).resolve().parent.parent / "contracts/service-v1/fixtures/ready.json"
            ).read_text()
        )
        state = RemoteState(frame["source"]["hostId"], local_clock=domain())
        state.start("nonce", 100)
        frame.update(kind="resync", requestId="nonce", sequence=0)
        with self.assertRaises(ContractError):
            state.receive(frame, 150)
        self.assertEqual(state.expiry, 0)
