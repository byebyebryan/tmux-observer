"""Local prepared stream uses its actual clock and never owns a source worker."""

import os
import tempfile
import time
import unittest
from pathlib import Path

import test_owner

from tmux_observer._clock import boottime_ms, domain
from tmux_observer_client._local_stream import LocalConnection
from tmux_observer_client._remote_state import RemoteState


class LocalStreamTests(unittest.TestCase):
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
