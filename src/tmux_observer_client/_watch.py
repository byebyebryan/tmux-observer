"""Read-only prepared fleet stream; no stdin control, activation or fallback."""

from __future__ import annotations

import collections
import fcntl
import os
import selectors
import sys
import uuid

from tmux_observer._clock import boottime_ms, domain
from tmux_observer._ipc import IPCError, connect
from tmux_observer._request_validation import validate_operation_error, validate_request
from tmux_observer.native import FRAME_LIMIT, REQUEST_LIMIT, decode_document, encode_document
from tmux_observer_client.contract import FLEET_PROTOCOL, validate_fleet_frame

from .public import fleet_socket


def stream_fleet(context_id, *, path=None, expected_host=None, publisher_id=None):
    request = {
        "protocol": FLEET_PROTOCOL,
        "schemaVersion": 1,
        "operation": "watch",
        "requestId": uuid.uuid4().hex,
        "contextId": context_id,
    }
    if expected_host is not None:
        request["expectedHost"] = expected_host
    if publisher_id is not None:
        request["publisherId"] = publisher_id
    written, flags = 0, None
    fd = sys.stdout.fileno()
    try:
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        os.set_blocking(fd, False)
        validate_request(request)
        clock = domain()
        with (
            connect(
                fleet_socket(context_id) if path is None else path, deadline=boottime_ms() + 2000
            ) as sock,
            selectors.PollSelector() as selector,
        ):
            outgoing = bytearray(encode_document(request, limit=REQUEST_LIMIT))
            incoming, outputs = bytearray(), collections.deque()
            first_byte = output_at = None
            started = last_frame = boottime_ms()
            reader = sequence = revision = encoded_at = None
            ended = False
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

            def deadlines(now):
                if (
                    reader is None
                    and now >= started + 2000
                    or now >= last_frame + 10000
                    or first_byte is not None
                    and now >= first_byte + 2000
                    or output_at is not None
                    and now >= output_at + 2000
                ):
                    raise IPCError("deadline", "fleet stream framing or liveness deadline exceeded")

            while True:
                deadlines(boottime_ms())
                if ended and not outputs:
                    raise IPCError("disconnected", "prepared fleet stream ended")
                interest(
                    sock,
                    0
                    if ended
                    else (selectors.EVENT_READ if len(outputs) < 2 else 0)
                    | (selectors.EVENT_WRITE if outgoing else 0),
                    "fleet",
                )
                interest(fd, selectors.EVENT_WRITE if outputs else 0, "output")
                for key, events in selector.select(0.05):
                    now = boottime_ms()
                    deadlines(now)
                    if key.data == "fleet":
                        if events & selectors.EVENT_WRITE:
                            try:
                                count = sock.send(outgoing)
                            except BlockingIOError:
                                count = 0
                            del outgoing[:count]
                        if events & selectors.EVENT_READ:
                            chunk = sock.recv(min(65536, FRAME_LIMIT + 1 - len(incoming)))
                            if not chunk:
                                # Drain already validated output within its
                                # existing budget. Never accept buffered input
                                # or append an error to a started JSON record.
                                ended = True
                                incoming.clear()
                                first_byte = None
                                continue
                            if first_byte is None:
                                first_byte = now
                            incoming.extend(chunk)
                            if (
                                len(incoming) > FRAME_LIMIT
                                and not 0 <= incoming.find(b"\n") < FRAME_LIMIT
                            ):
                                raise IPCError(
                                    "frame_limit", "fleet stream exceeded its document bound"
                                )
                    else:
                        raw, offset = outputs[0]
                        if output_at is None:
                            output_at = now
                        try:
                            count = os.write(fd, memoryview(raw)[offset:])
                        except BlockingIOError:
                            count = 0
                        written += count
                        offset += count
                        if offset == len(raw):
                            outputs.popleft()
                            output_at = now if outputs else None
                        else:
                            outputs[0] = raw, offset
                while b"\n" in incoming and len(outputs) < 2:
                    began = first_byte
                    raw, _, rest = incoming.partition(b"\n")
                    raw = bytes(raw) + b"\n"
                    value = decode_document(raw, limit=FRAME_LIMIT)
                    if value.get("kind") == "operation_error":
                        validate_operation_error(value)
                        if value["protocol"] != FLEET_PROTOCOL or value.get("requestId") not in (
                            None,
                            request["requestId"],
                        ):
                            raise IPCError("scope_mismatch", "foreign fleet operation error")
                        raise IPCError(value["error"]["code"], "fleet watch rejected")
                    validate_fleet_frame(value)
                    if value["snapshot"] is None:
                        raise IPCError("invalid_stream", "fleet watch omitted its prepared view")
                    if (
                        value["contextId"] != context_id
                        or any(
                            value["clock"][field] != clock[field]
                            for field in ("bootId", "timeNamespace")
                        )
                        or expected_host is not None
                        and value["snapshot"]["mesh"]["localHostId"] != expected_host
                    ):
                        raise IPCError("scope_mismatch", "foreign fleet stream context")
                    if reader is None:
                        if (
                            value["kind"] != "resync"
                            or value["sequence"] != 0
                            or value["requestId"] != request["requestId"]
                            or publisher_id is not None
                            and value["readerId"] != publisher_id
                        ):
                            raise IPCError("stale_scope", "fleet watch handshake differs")
                        reader = value["readerId"]
                    if (
                        value["readerId"] != reader
                        or sequence is not None
                        and (
                            value["sequence"] <= sequence
                            or value["sequence"] != sequence + 1
                            and value["kind"] not in ("gap", "resync")
                        )
                        or revision is not None
                        and value["viewRevision"] < revision
                        or encoded_at is not None
                        and value["encodedAt"] < encoded_at
                    ):
                        raise IPCError("stale_scope", "fleet stream incarnation or order changed")
                    sequence, revision, encoded_at = (
                        value["sequence"],
                        value["viewRevision"],
                        value["encodedAt"],
                    )
                    checked = boottime_ms()
                    if began is not None and checked >= began + 2000:
                        raise IPCError("deadline", "late fleet validation rejected")
                    incoming, first_byte = bytearray(rest), began if rest else None
                    last_frame = checked
                    if not outputs:
                        output_at = checked
                    outputs.append((raw, 0))
    except (IPCError, OSError, ValueError) as error:
        code = error.code if isinstance(error, IPCError) else "invalid_stream"
        if written == 0:
            try:
                os.write(
                    fd,
                    encode_document(
                        {
                            "protocol": FLEET_PROTOCOL,
                            "schemaVersion": 1,
                            "kind": "operation_error",
                            "error": {"code": code, "message": "prepared fleet stream unavailable"},
                        },
                        limit=REQUEST_LIMIT,
                    ),
                )
            except OSError:
                pass
        print("tmux-observer-client watch stopped: " + code, file=sys.stderr)
        return 1
    finally:
        if flags is not None:
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)
