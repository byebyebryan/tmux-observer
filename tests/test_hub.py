"""Bounded fan-out and slow-reader behavior over owned socket pairs."""

import json
import socket
import tempfile
import unittest
from pathlib import Path

from tmux_observer._hub import Peer, SocketHub
from tmux_observer._owner_state import OwnerState
from tmux_observer.public import SERVICE_PROTOCOL, decode_document, validate_service_frame


class HubTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tmux-observer-hub-")
        root = Path(__file__).resolve().parent.parent
        sample = json.loads((root / "contracts/observation-v1/fixtures/complete.json").read_text())
        owner = OwnerState(sample["source"], sample["clock"])
        owner.finish(owner.begin(100), sample, 125)
        self.owner = owner
        self.hub = SocketHub(
            Path(self.temporary.name) / "owner.sock",
            protocol=SERVICE_PROTOCOL,
            now=lambda: 130,
            make_frame=owner.frame,
            handle_request=lambda *_args: None,
        )
        source, self.reader = socket.socketpair()
        source.setblocking(False)
        self.reader.setblocking(False)
        self.peer = Peer(source, 100, watch=True)
        self.hub.peers.add(self.peer)
        self.hub.selector.register(source, 1, self.peer)

    def tearDown(self):
        self.hub.close()
        self.reader.close()
        self.temporary.cleanup()

    def test_coalescing_retains_started_record_and_marks_gap(self):
        self.hub.frame(self.peer, 130)
        started = self.peer.started.raw
        self.hub.frame(self.peer, 131)
        self.hub.frame(self.peer, 132)
        self.assertEqual(self.peer.started.raw, started)
        queued = validate_service_frame(decode_document(self.peer.queued.raw))
        self.assertEqual(queued["kind"], "gap")
        self.assertEqual(queued["sequence"], 2)
        self.assertEqual(queued["encodedAt"], 132)

    def test_nonce_replies_are_not_replaced_by_background_views(self):
        self.hub.frame(self.peer, 130, kind="resync", request_id="watch-1")
        self.hub.frame(self.peer, 131, kind="status", request_id="probe-1")
        self.hub.frame(self.peer, 132)
        self.assertEqual(decode_document(self.peer.queued.raw)["requestId"], "probe-1")
        self.assertFalse(self.hub.frame(self.peer, 133, kind="status", request_id="probe-2"))
        error = decode_document(self.peer.controls[0].raw)
        self.assertEqual(error["error"]["code"], "backpressure")
        self.assertEqual(error["requestId"], "probe-2")

    def test_partial_frame_is_preserved_and_stalled_reader_disconnected(self):
        # A valid producer document close to the byte cap, not arbitrary wire.
        sample = json.loads(
            (
                Path(__file__).resolve().parent.parent
                / "contracts/observation-v1/fixtures/complete.json"
            ).read_text()
        )
        row = sample["sessions"][0]
        sample["sessions"] = [
            {**row, "sessionId": "$" + str(index), "name": "x" * 16000} for index in range(60)
        ]
        self.owner.finish(
            self.owner.begin(2100),
            {**sample, "sample": {**sample["sample"], "startedAt": 2100, "finishedAt": 2120}},
            2125,
        )
        self.peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
        self.hub.frame(self.peer, 2130)
        started = self.peer.started.raw
        self.hub.write(self.peer, 2130)
        self.assertGreater(self.peer.started.offset, 0)
        self.assertLess(self.peer.started.offset, len(started))
        for now in range(2131, 2141):
            self.hub.frame(self.peer, now)
        self.assertEqual(self.peer.started.raw, started)
        self.assertLessEqual(self.peer.bytes_held(), 2 * 1064960)
        self.hub.poll(4130, timeout=0)
        self.assertNotIn(self.peer, self.hub.peers)
