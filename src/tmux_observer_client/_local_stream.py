"""Prepared local owner subscription. No collector or child process."""

from __future__ import annotations

import selectors
import uuid

from tmux_observer._clock import boottime_ms, domain
from tmux_observer._ipc import IPCError, connect, owner_socket
from tmux_observer._request_validation import validate_operation_error, validate_request
from tmux_observer.delivery import SERVICE_PROTOCOL
from tmux_observer.native import FRAME_LIMIT, REQUEST_LIMIT, encode_document

from ._errors import ContractError
from ._owner_document import OwnerDocument
from ._remote_state import RemoteState


class LocalConnection:
    def __init__(
        self, host_id, now, *, path=None, state=None, on_frame=None, on_error=None, on_input=None
    ):
        self.state = state or RemoteState(host_id, local_clock=domain())
        self.nonce = uuid.uuid4().hex
        self.state.start(self.nonce, now)
        self.sock = connect(owner_socket() if path is None else path, deadline=now + 2000)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ | selectors.EVENT_WRITE)
        self.outgoing = bytearray(
            encode_document(
                {
                    "protocol": SERVICE_PROTOCOL,
                    "schemaVersion": 1,
                    "operation": "watch",
                    "requestId": self.nonce,
                    "expectedHost": host_id,
                },
                limit=REQUEST_LIMIT,
            )
        )
        self.output_at = now
        self.incoming = bytearray()
        self.first_byte = None
        self.on_frame = on_frame
        self.on_error = on_error
        self.on_input = on_input
        self.closed = False

    def send(self, value, now):
        validate_request(value)
        if (
            self.closed
            or value["protocol"] != SERVICE_PROTOCOL
            or value["expectedHost"] != self.state.host_id
            or value["operation"] == "watch"
        ):
            raise ContractError("operation_failed", "local request has a foreign or closed scope")
        raw = encode_document(value, limit=REQUEST_LIMIT)
        if len(raw) + len(self.outgoing) > 65536:
            raise ContractError("operation_failed", "local owner control queue exceeded its bound")
        self.outgoing.extend(raw)
        if self.output_at is None:
            self.output_at = now
        self.selector.modify(self.sock, selectors.EVENT_READ | selectors.EVENT_WRITE)

    def close(self):
        if not self.closed:
            self.closed = True
            self.selector.close()
            self.sock.close()
            self.incoming.clear()
            self.outgoing.clear()

    def fail(self, code, message):
        self.state.fail(code, message)
        self.close()

    def check_deadlines(self, now):
        self.state.expire(now)
        if self.state.transport == "failed":
            self.close()
            return False
        if (
            self.first_byte is not None
            and now - self.first_byte >= 2000
            or self.output_at is not None
            and now - self.output_at >= 2000
        ):
            self.fail("deadline", "local owner framing deadline exceeded")
            return False
        return True

    def poll(self, now):
        if self.closed or not self.check_deadlines(now):
            return
        try:
            for _key, events in self.selector.select(0):
                now = boottime_ms()
                if not self.check_deadlines(now):
                    return
                if events & selectors.EVENT_WRITE:
                    try:
                        sent = self.sock.send(self.outgoing)
                    except BlockingIOError:
                        sent = 0
                    del self.outgoing[:sent]
                    if not self.outgoing:
                        self.output_at = None
                        self.selector.modify(self.sock, selectors.EVENT_READ)
                if events & selectors.EVENT_READ:
                    chunk = self.sock.recv(min(65536, FRAME_LIMIT + 1 - len(self.incoming)))
                    if not chunk:
                        raise IPCError("disconnected", "local owner subscription ended")
                    if self.first_byte is None:
                        self.first_byte = now
                    self.incoming.extend(chunk)
            for _ in range(8):
                if b"\n" not in self.incoming:
                    break
                first_byte = self.first_byte
                raw, _, rest = self.incoming.partition(b"\n")
                value, document = OwnerDocument.decode_input(bytes(raw) + b"\n")
                now = boottime_ms()
                if first_byte is not None and now - first_byte >= 2000:
                    raise ValueError("local frame parsing exceeded its deadline")
                self.incoming = bytearray(rest)
                self.first_byte = first_byte if rest else None
                if value.get("kind") == "operation_error":
                    validate_operation_error(value)
                    if value["protocol"] != SERVICE_PROTOCOL:
                        raise ValueError("foreign owner error")
                    if self.on_error is not None and self.on_error(self, value, now):
                        continue
                    raise IPCError(
                        "owner_unavailable", "local owner returned a scoped operation failure"
                    )
                if self.on_input is not None:
                    admitted = self.on_input(self, document, now)
                else:
                    admitted = None
                matched = self.state.receive(
                    admitted if isinstance(admitted, OwnerDocument) else document, now
                )
                if self.on_frame is not None:
                    self.on_frame(self, value, matched, now)
            if len(self.incoming) > FRAME_LIMIT:
                raise ValueError("local owner frame exceeded its byte bound")
            value = self.state.probe(boottime_ms())
            if value is not None:
                self.send(value, boottime_ms())
        except (IPCError, OSError, ValueError, ContractError) as error:
            self.fail(
                "capacity"
                if isinstance(error, ContractError) and error.code == "capacity"
                else "owner_unavailable",
                "local owner subscription failed its bounded protocol",
            )
