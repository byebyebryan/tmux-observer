"""Bounded fan-out and slow-reader behavior over owned socket pairs."""

import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_broadcast_shares_only_identical_unsolicited_sequences_and_preserves_nonce_reply(self):
        source, reader = socket.socketpair()
        source.setblocking(False)
        extra = Peer(source, 100, watch=True)
        self.hub.peers.add(extra)
        self.hub.selector.register(source, 1, extra)
        try:
            with patch.object(self.hub, "make_frame", wraps=self.owner.frame) as render:
                self.hub.broadcast(130, kind="heartbeat")
                self.assertEqual(render.call_count, 1)
            self.assertIs(self.peer.started.raw, extra.started.raw)
            self.hub.frame(self.peer, 131, kind="status", request_id="protected-probe")
            reply = self.peer.queued.raw
            self.hub.broadcast(132, kind="heartbeat")
            self.assertEqual(self.peer.queued.raw, reply)
            self.assertEqual(decode_document(reply)["requestId"], "protected-probe")
            self.assertTrue(self.peer.gaps)
            value = validate_service_frame(decode_document(extra.queued.raw))
            self.assertEqual(
                (value["sequence"], value["kind"], value["encodedAt"]), (1, "heartbeat", 132)
            )
            self.hub.frame(self.peer, 133, request_id="another-probe")
            self.assertEqual(
                decode_document(self.peer.controls[-1].raw)["error"]["code"], "backpressure"
            )
            self.hub.broadcast(134, kind="heartbeat")
            gap = validate_service_frame(decode_document(extra.queued.raw))
            self.assertEqual((gap["sequence"], gap["kind"], gap["encodedAt"]), (2, "gap", 134))
        finally:
            reader.close()

    def extra_peer(self, *, sequence=4, gaps=True):
        source, reader = socket.socketpair()
        self.addCleanup(reader.close)
        source.setblocking(False)
        peer = Peer(source, 100, watch=True, sequence=sequence, gaps=gaps)
        self.hub.peers.add(peer)
        self.hub.selector.register(source, 1, peer)
        return peer

    def test_opted_in_body_sharing_preserves_independent_envelopes_offsets_and_replies(self):
        extra = self.extra_peer()
        self.hub.share_broadcast_body = True
        with patch.object(self.hub, "make_frame", wraps=self.owner.frame) as render:
            self.hub.broadcast(130, kind="heartbeat")
            self.assertEqual(render.call_count, 1)
            own = validate_service_frame(decode_document(self.peer.started.raw))
            other = validate_service_frame(decode_document(extra.started.raw))
            self.assertEqual((own["kind"], own["sequence"]), ("heartbeat", 0))
            self.assertEqual((other["kind"], other["sequence"]), ("gap", 4))
            self.assertEqual(own["snapshot"], other["snapshot"])
            self.assertEqual(own["receipt"], other["receipt"])
            self.peer.started.offset = 1
            self.assertEqual(extra.started.offset, 0)
            self.hub.frame(self.peer, 131, kind="status", request_id="fresh-query")
            self.assertEqual(render.call_count, 2)
            reply = validate_service_frame(decode_document(self.peer.queued.raw))
            reply_raw = self.peer.queued.raw
            self.assertEqual((reply["requestId"], reply["encodedAt"]), ("fresh-query", 131))
            self.hub.broadcast(132, kind="heartbeat")
            self.assertEqual(self.peer.queued.raw, reply_raw)
            self.assertEqual(decode_document(self.peer.queued.raw), reply)

    def test_shared_body_ends_with_broadcast_and_recomputes_remaining_validity(self):
        extra = self.extra_peer()
        self.hub.share_broadcast_body = True
        self.hub.broadcast(130, kind="heartbeat")
        before = decode_document(extra.started.raw)
        with patch.object(self.hub, "make_frame", wraps=self.owner.frame) as render:
            self.hub.broadcast(230, kind="heartbeat")
            self.assertEqual(render.call_count, 1)
        after = validate_service_frame(decode_document(extra.queued.raw))
        self.assertEqual(after["encodedAt"], 230)
        self.assertEqual(after["receipt"]["remainingMs"], before["receipt"]["remainingMs"] - 100)

    def test_factories_with_envelope_dependent_bodies_are_not_implicitly_shared(self):
        extra = self.extra_peer()

        def varied(now, **kwargs):
            value = self.owner.frame(now, **kwargs)
            value["snapshot"]["sessions"][0]["name"] = str(kwargs["sequence"])
            return value

        with patch.object(self.hub, "make_frame", side_effect=varied) as render:
            self.hub.broadcast(130, kind="heartbeat")
            self.assertEqual(render.call_count, 2)
        own = validate_service_frame(decode_document(self.peer.started.raw))
        other = validate_service_frame(decode_document(extra.started.raw))
        self.assertNotEqual(own["snapshot"], other["snapshot"])

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
