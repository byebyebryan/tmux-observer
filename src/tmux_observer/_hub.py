"""Bounded Unix framing/fan-out shared by the two concrete publisher roles."""

from __future__ import annotations

import collections
import selectors
import socket
from dataclasses import dataclass, field

from ._ipc import Endpoint, same_user
from ._wire import MAX_INT
from .public import FRAME_LIMIT, REQUEST_LIMIT, decode_document, encode_document, validate_request

GLOBAL_OUTPUT_LIMIT = 72 * 1024 * 1024
CONTROL_LIMIT = 64 * 1024


@dataclass
class Record:
    raw: bytes
    reply: bool
    offset: int = 0
    started_at: int | None = None


@dataclass(eq=False)
class Peer:
    sock: socket.socket
    opened_at: int
    incoming: bytearray = field(default_factory=bytearray)
    incoming_at: int | None = None
    watch: bool = False
    closing: bool = False
    sequence: int = 0
    started: Record | None = None
    queued: Record | None = None
    controls: collections.deque = field(default_factory=collections.deque)
    gaps: bool = False
    handled: int = 0

    def bytes_held(self):
        return sum(
            len(record.raw) for record in (self.started, self.queued) if record is not None
        ) + sum(len(record.raw) for record in self.controls)


class SocketHub:
    def __init__(
        self, path, *, protocol, now, make_frame, handle_request, share_broadcast_body=False
    ):
        self.endpoint = Endpoint(path)
        self.protocol = protocol
        self.make_frame = make_frame
        self.handle_request = handle_request
        self.peers = set()
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.endpoint.socket, selectors.EVENT_READ, None)
        self.now = now
        # The concrete publishers' unsolicited bodies depend only on state/now.
        # Other factories retain per-envelope rendering unless they opt in.
        self.share_broadcast_body = share_broadcast_body

    def close_peer(self, peer):
        if peer not in self.peers:
            return
        self.selector.unregister(peer.sock)
        peer.sock.close()
        self.peers.remove(peer)

    def close(self):
        for peer in list(self.peers):
            self.close_peer(peer)
        self.selector.close()
        self.endpoint.close()

    def interest(self, peer):
        if peer not in self.peers:
            return
        if peer.closing and peer.started is None and peer.queued is None and not peer.controls:
            self.close_peer(peer)
            return
        events = 0 if peer.closing else selectors.EVENT_READ
        if peer.started is not None or peer.queued is not None or peer.controls:
            events |= selectors.EVENT_WRITE
        self.selector.modify(peer.sock, events, peer)

    def error(self, peer, code, message, *, request_id=None, close=False):
        value = {
            "protocol": self.protocol,
            "schemaVersion": 1,
            "kind": "operation_error",
            "error": {"code": code, "message": message},
        }
        if request_id is not None:
            value["requestId"] = request_id
        raw = encode_document(value, limit=REQUEST_LIMIT)
        if sum(len(item.raw) for item in peer.controls) + len(raw) > CONTROL_LIMIT:
            self.close_peer(peer)
            return
        peer.controls.append(Record(raw, True))
        peer.closing |= close
        self.enforce_memory(peer)
        self.interest(peer)

    def can_reply(self, peer):
        return peer.queued is None or not peer.queued.reply

    def frame(
        self, peer, now, *, kind="view", request_id=None, ticket=None, encoded=None, body=None
    ):
        reply = request_id is not None
        if peer.queued is not None and peer.queued.reply:
            if reply:
                self.error(
                    peer, "backpressure", "publisher reply slot is occupied", request_id=request_id
                )
            else:
                peer.gaps = True
            return False
        if peer.queued is not None:
            peer.gaps = True
        if peer.gaps and not reply:
            kind = "gap"
            peer.gaps = False
        key = kind, peer.sequence
        raw = encoded.get(key) if encoded is not None and not reply and ticket is None else None
        if raw is None:
            shared = (
                body is not None
                and not reply
                and ticket is None
                and kind in ("view", "heartbeat", "gap")
                and type(peer.sequence) is int
                and 0 <= peer.sequence <= MAX_INT
            )
            if shared and body:
                value = {**body[0], "kind": kind, "sequence": peer.sequence}
            else:
                value = self.make_frame(
                    now, kind=kind, sequence=peer.sequence, request_id=request_id, ticket=ticket
                )
                if shared:
                    body.append(value)
            raw = encode_document(value, limit=FRAME_LIMIT)
            if encoded is not None and not reply and ticket is None:
                encoded[key] = raw
        peer.sequence += 1
        record = Record(raw, reply)
        if peer.started is None and not peer.controls:
            peer.started = record
        else:
            peer.queued = record
        self.enforce_memory(peer)
        self.interest(peer)
        return peer in self.peers

    def enforce_memory(self, peer):
        if sum(item.bytes_held() for item in self.peers) > GLOBAL_OUTPUT_LIMIT:
            self.close_peer(peer)

    def broadcast(self, now, *, kind):
        # A broadcast has one publisher state and clock instant. Only identical
        # unsolicited envelope kinds/sequences can share immutable encoded bytes.
        # This cache ends with the broadcast; replies/tickets never enter it.
        encoded = {}
        body = [] if self.share_broadcast_body else None
        for peer in list(self.peers):
            if peer.watch and not peer.closing:
                self.frame(peer, now, kind=kind, encoded=encoded, body=body)

    def accept(self, now):
        for _ in range(8):
            try:
                sock, _address = self.endpoint.socket.accept()
            except BlockingIOError:
                break
            sock.setblocking(False)
            if not same_user(sock):
                sock.close()
                continue
            if len(self.peers) >= 32:
                raw = encode_document(
                    {
                        "protocol": self.protocol,
                        "schemaVersion": 1,
                        "kind": "operation_error",
                        "error": {
                            "code": "capacity",
                            "message": "publisher reader capacity exceeded",
                        },
                    }
                )
                try:
                    sock.send(raw)
                except (BlockingIOError, OSError):
                    pass
                sock.close()
                continue
            peer = Peer(sock, now)
            self.peers.add(peer)
            self.selector.register(sock, selectors.EVENT_READ, peer)

    def read(self, peer, now):
        try:
            chunk = peer.sock.recv(REQUEST_LIMIT + 1 - len(peer.incoming))
        except BlockingIOError:
            return
        if not chunk:
            self.close_peer(peer)
            return
        if peer.incoming_at is None:
            peer.incoming_at = now
        peer.incoming.extend(chunk)
        if len(peer.incoming) > REQUEST_LIMIT and not (
            0 <= peer.incoming.find(b"\n") < REQUEST_LIMIT
        ):
            self.error(peer, "request_limit", "request exceeded its byte bound", close=True)
            return
        self.process_requests(peer, now)

    def process_requests(self, peer, now):
        for _ in range(8):
            if b"\n" not in peer.incoming:
                break
            raw, _separator, rest = peer.incoming.partition(b"\n")
            peer.incoming = bytearray(rest)
            peer.incoming_at = peer.incoming_at if rest else None
            try:
                request = validate_request(decode_document(bytes(raw) + b"\n", limit=REQUEST_LIMIT))
                if request["protocol"] != self.protocol or peer.handled and not peer.watch:
                    raise ValueError("unsupported request stream")
            except (ValueError, TypeError, KeyError):
                self.error(
                    peer,
                    "invalid_request",
                    "unsupported or malformed publisher request",
                    close=True,
                )
                return
            peer.handled += 1
            self.handle_request(peer, request, now)
            if peer not in self.peers or peer.closing:
                break

    def write(self, peer, now):
        for _ in range(4):
            if peer.started is None:
                if peer.controls:
                    peer.started = peer.controls.popleft()
                elif peer.queued is not None:
                    peer.started, peer.queued = peer.queued, None
                else:
                    break
            record = peer.started
            if record.started_at is None:
                record.started_at = now
            try:
                sent = peer.sock.send(memoryview(record.raw)[record.offset :])
            except BlockingIOError:
                break
            if not sent:
                self.close_peer(peer)
                return
            record.offset += sent
            if record.offset != len(record.raw):
                break
            peer.started = None
        self.interest(peer)

    def poll(self, now, timeout=0.05):
        for peer in list(self.peers):
            if not peer.closing and (
                peer.incoming_at is not None
                and now - peer.incoming_at >= 2000
                or peer.handled == 0
                and now - peer.opened_at >= 2000
            ):
                self.error(peer, "deadline", "request assembly exceeded its deadline", close=True)
            if peer in self.peers and not peer.closing and b"\n" in peer.incoming:
                self.process_requests(peer, now)
            if (
                peer.started is not None
                and peer.started.started_at is not None
                and now - peer.started.started_at >= 2000
            ):
                self.close_peer(peer)
        for key, events in self.selector.select(timeout):
            peer = key.data
            if peer is None:
                self.accept(self.now())
                continue
            if peer not in self.peers:
                continue
            try:
                if events & selectors.EVENT_READ:
                    self.read(peer, self.now())
                # A read can admit a reply after select captured read-only
                # readiness. Try its bounded nonblocking write now instead of
                # waiting behind the publishers' next source-processing tick.
                if peer in self.peers and (
                    events & selectors.EVENT_WRITE
                    or peer.started is not None
                    or peer.queued is not None
                    or peer.controls
                ):
                    self.write(peer, self.now())
            except OSError:
                self.close_peer(peer)
