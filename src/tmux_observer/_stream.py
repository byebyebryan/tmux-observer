"""Bounded owner watch/stdin bridge; exports only the selected local publisher."""

from __future__ import annotations

import collections
import fcntl
import os
import selectors
import sys
import uuid

from tmux_observer._request_validation import validate_operation_error, validate_request
from tmux_observer.delivery import SERVICE_PROTOCOL
from tmux_observer.native import FRAME_LIMIT, REQUEST_LIMIT, decode_document, encode_document

from ._clock import boottime_ms, domain
from ._delivery_validation import _decode_service_input
from ._ipc import IPCError, connect, owner_socket


def stream_owner(host_id, *, path=None, bridge=False, request_id=None):
    request_id = uuid.uuid4().hex if request_id is None else request_id
    watch = {
        "protocol": SERVICE_PROTOCOL,
        "schemaVersion": 1,
        "operation": "watch",
        "requestId": request_id,
        "expectedHost": host_id,
    }
    written = 0
    fd_flags = {}
    try:
        validate_request(watch)
        native_clock = domain()
        with (
            connect(
                owner_socket() if path is None else path, deadline=boottime_ms() + 2000
            ) as sock,
            selectors.PollSelector() as selector,
        ):
            output_fd = sys.stdout.fileno()
            input_fd = sys.stdin.fileno() if bridge else None
            for fd in (output_fd, input_fd):
                if fd is not None:
                    fd_flags[fd] = fcntl.fcntl(fd, fcntl.F_GETFL)
                    os.set_blocking(fd, False)
            to_owner = bytearray(encode_document(watch, limit=REQUEST_LIMIT))
            to_output = collections.deque()
            owner_bytes = bytearray()
            request_bytes = bytearray()
            owner_at = request_at = output_at = None
            last_owner = boottime_ms()
            publisher = None
            sequence = None
            registered = {}

            def interest(file, events, tag):
                if events:
                    if file in registered:
                        selector.modify(file, events, tag)
                    else:
                        selector.register(file, events, tag)
                    registered[file] = events
                elif file in registered:
                    selector.unregister(file)
                    registered.pop(file)

            while True:
                now = boottime_ms()
                if (
                    now - last_owner >= 10000
                    or owner_at is not None
                    and now - owner_at >= 2000
                    or request_at is not None
                    and now - request_at >= 2000
                    or output_at is not None
                    and now - output_at >= 2000
                ):
                    raise IPCError("deadline", "owner stream exceeded a framing/liveness deadline")
                interest(
                    sock,
                    (
                        selectors.EVENT_READ
                        if len(to_output) < 2 and len(owner_bytes) <= FRAME_LIMIT
                        else 0
                    )
                    | (selectors.EVENT_WRITE if to_owner else 0),
                    "owner",
                )
                interest(output_fd, selectors.EVENT_WRITE if to_output else 0, "output")
                if input_fd is not None:
                    interest(
                        input_fd,
                        selectors.EVENT_READ
                        if len(to_owner) < 65536 and len(request_bytes) <= REQUEST_LIMIT
                        else 0,
                        "input",
                    )
                for key, events in selector.select(0.05):
                    now = boottime_ms()
                    if (
                        now - last_owner >= 10000
                        or owner_at is not None
                        and now - owner_at >= 2000
                        or request_at is not None
                        and now - request_at >= 2000
                        or output_at is not None
                        and now - output_at >= 2000
                    ):
                        raise IPCError("deadline", "late stream I/O rejected after a clock jump")
                    if key.data == "owner":
                        if events & selectors.EVENT_WRITE:
                            try:
                                count = sock.send(to_owner)
                            except BlockingIOError:
                                count = 0
                            del to_owner[:count]
                        if events & selectors.EVENT_READ:
                            try:
                                chunk = sock.recv(min(65536, FRAME_LIMIT + 1 - len(owner_bytes)))
                            except BlockingIOError:
                                continue
                            if not chunk:
                                raise IPCError("disconnected", "owner publisher disconnected")
                            if owner_at is None:
                                owner_at = now
                            owner_bytes.extend(chunk)
                            if len(owner_bytes) > FRAME_LIMIT and not (
                                0 <= owner_bytes.find(b"\n") < FRAME_LIMIT
                            ):
                                raise IPCError("frame_limit", "owner frame exceeded its byte bound")
                    elif key.data == "input":
                        chunk = os.read(input_fd, REQUEST_LIMIT + 1 - len(request_bytes))
                        if not chunk:
                            return 0
                        if request_at is None:
                            request_at = now
                        request_bytes.extend(chunk)
                        if len(request_bytes) > REQUEST_LIMIT and not (
                            0 <= request_bytes.find(b"\n") < REQUEST_LIMIT
                        ):
                            raise IPCError(
                                "request_limit", "bridge request exceeded its byte bound"
                            )
                    elif key.data == "output":
                        if output_at is None:
                            output_at = now
                        raw, offset = to_output[0]
                        try:
                            count = os.write(output_fd, memoryview(raw)[offset:])
                        except BlockingIOError:
                            count = 0
                        written += count
                        offset += count
                        if offset == len(raw):
                            to_output.popleft()
                            output_at = None
                        else:
                            to_output[0] = (raw, offset)
                while b"\n" in owner_bytes and len(to_output) < 2:
                    frame_started = owner_at
                    raw, _separator, rest = owner_bytes.partition(b"\n")
                    raw = bytes(raw) + b"\n"
                    owner_bytes = bytearray(rest)
                    owner_at = owner_at if rest else None
                    value = _decode_service_input(raw)[0]
                    if value.get("kind") == "operation_error":
                        validate_operation_error(value)
                        if value["protocol"] != SERVICE_PROTOCOL:
                            raise IPCError(
                                "scope_mismatch", "bridge received a foreign error protocol"
                            )
                    else:
                        if (
                            value["source"]["hostId"] != host_id
                            or value["source"]["uid"] != os.getuid()
                            or any(
                                value["clock"][field] != native_clock[field]
                                for field in ("bootId", "timeNamespace")
                            )
                        ):
                            raise IPCError(
                                "scope_mismatch", "bridge received foreign owner provenance"
                            )
                        if publisher is None:
                            if value["requestId"] != request_id or value["kind"] != "resync":
                                raise IPCError("scope_mismatch", "owner watch handshake differs")
                            publisher = value["publisherId"]
                        if (
                            value["publisherId"] != publisher
                            or sequence is not None
                            and value["sequence"] <= sequence
                        ):
                            raise IPCError("stale_scope", "owner stream incarnation/order changed")
                        if (
                            sequence is not None
                            and value["sequence"] != sequence + 1
                            and value["kind"] not in ("gap", "resync")
                        ):
                            raise IPCError(
                                "stream_gap", "owner stream skipped records without a gap"
                            )
                        sequence = value["sequence"]
                    checked_at = boottime_ms()
                    if frame_started is not None and checked_at - frame_started >= 2000:
                        raise IPCError("deadline", "owner validation exceeded framing deadline")
                    last_owner = checked_at
                    to_output.append((raw, 0))
                while b"\n" in request_bytes and len(to_owner) < 65536:
                    raw, _separator, rest = request_bytes.partition(b"\n")
                    raw = bytes(raw) + b"\n"
                    request_bytes = bytearray(rest)
                    request_at = request_at if rest else None
                    request = validate_request(decode_document(raw, limit=REQUEST_LIMIT))
                    if (
                        request["protocol"] != SERVICE_PROTOCOL
                        or request["expectedHost"] != host_id
                        or request["operation"] == "watch"
                    ):
                        raise IPCError(
                            "scope_mismatch", "bridge accepts only fixed local owner requests"
                        )
                    if len(to_owner) + len(raw) > 65536:
                        raise IPCError("backpressure", "bridge request queue exceeded its bound")
                    to_owner.extend(raw)
    except (IPCError, OSError, ValueError) as error:
        code = error.code if isinstance(error, IPCError) else "invalid_stream"
        if written == 0:
            # Initial absence is typed; after partial output, EOF invalidates
            # framing without appending a diagnostic inside a JSON record.
            raw = encode_document(
                {
                    "protocol": SERVICE_PROTOCOL,
                    "schemaVersion": 1,
                    "kind": "operation_error",
                    "error": {"code": code, "message": "owner stream is unavailable"},
                }
            )
            try:
                os.write(sys.stdout.fileno(), raw)
            except OSError:
                pass
        print("tmux-observer stream stopped: " + code, file=sys.stderr)
        return 1
    finally:
        for fd, flags in fd_flags.items():
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)
