"""Owner-native cached Service v1 acquisition for the optional Mesh publisher."""

import asyncio
import os
import uuid
from pathlib import Path

from mesh_plus.api import CachedPublication
from mesh_plus.transport import connect_ipc, finish_owned, within_deadline

from ._clock import boottime_ms, domain
from .delivery import SERVICE_PROTOCOL, validate_service_frame
from .native import FRAME_LIMIT, REQUEST_LIMIT, ValidationError, decode_document, encode_document

SETUP_MS = 2000
FRAME_MS = 2000
SILENCE_MS = 15000


def require(condition, code):
    if not condition:
        raise ValidationError(code)


class NativeGuard:
    """Connection-bound native scope, stream order and original receipt history."""

    def __init__(self, host, request_id, operation="status"):
        self.host, self.request_id = host, request_id
        self.initial_kind = "resync" if operation == "watch" else "status"
        self.clock = domain()
        self.previous = None

    def accept(self, frame):
        validate_service_frame(frame)
        require(frame["source"]["hostId"] == self.host, "native_host")
        require(frame["source"]["uid"] == os.getuid(), "native_uid")
        require(frame["clock"] == self.clock, "native_clock")
        require(frame["encodedAt"] <= boottime_ms(), "native_future")
        require(frame["kind"] not in {"error", "gap"}, "native_gap_or_error")
        current = (
            frame["publisherId"],
            frame["sequence"],
            frame["viewRevision"],
            frame["encodedAt"],
            frame["receipt"]["accepted"],
            frame["receipt"]["expiresAt"],
        )
        if self.previous is None:
            require(frame["requestId"] == self.request_id, "native_request")
            require(frame["kind"] == self.initial_kind and current[1] == 0, "native_initial_frame")
        else:
            epoch, sequence, revision, emitted, accepted, expiry = self.previous
            require(current[0] == epoch, "native_publisher_restart")
            require(current[1] == sequence + 1, "native_stream_order")
            require(current[2] >= revision, "native_revision_regression")
            require(current[3] >= emitted, "native_clock_regression")
            require(current[4] >= accepted, "native_receipt_regression")
            require(current[4] != accepted or current[5] == expiry, "native_lease_renewal")
        self.previous = current
        return frame


class TmuxCachedSource:
    """Fixed local owner socket; operations own every admitted connection."""

    def __init__(self, host, path):
        self.host, self.path = host, Path(path)

    async def frames(self, operation):
        require(operation in {"status", "watch"}, "native_cached_operation")
        deadline = boottime_ms() + SETUP_MS
        opening = asyncio.create_task(connect_ipc(self.path, maximum=FRAME_LIMIT))
        try:
            channel = await finish_owned(opening)
        except BaseException:
            # Cancellation can follow successful admission before its result is
            # delivered. The acquired connection still belongs to this operation.
            if opening.done() and not opening.cancelled() and opening.exception() is None:
                await finish_owned(asyncio.create_task(opening.result().close()))
            raise
        try:
            require(boottime_ms() < deadline, "native_setup_deadline")
            request_id = uuid.uuid4().hex
            guard = NativeGuard(self.host, request_id, operation)
            request = {
                "protocol": SERVICE_PROTOCOL,
                "schemaVersion": 1,
                "operation": operation,
                "requestId": request_id,
                "expectedHost": self.host,
            }
            channel.writer.write(encode_document(request, limit=REQUEST_LIMIT))
            await within_deadline(channel.writer.drain(), deadline)
            first = True
            while True:
                silence = deadline if first else boottime_ms() + SILENCE_MS
                initial = await within_deadline(channel.reader.readexactly(1), silence)
                framed = boottime_ms() + FRAME_MS
                limit = min(framed, deadline) if first else framed
                raw = (
                    initial
                    if initial == b"\n"
                    else initial + await within_deadline(channel.reader.readuntil(b"\n"), limit)
                )
                require(len(raw) <= FRAME_LIMIT, "native_capacity")
                frame = guard.accept(decode_document(raw, limit=FRAME_LIMIT))
                require(boottime_ms() < limit, "native_frame_deadline")
                first = False
                yield frame
                if operation != "watch":
                    return
        finally:
            await finish_owned(asyncio.create_task(channel.close()))

    async def snapshot(self):
        iterator = self.frames("status")
        try:
            return await anext(iterator)
        finally:
            await finish_owned(asyncio.create_task(iterator.aclose()))

    async def watch(self):
        iterator = self.frames("watch")
        try:
            async for frame in iterator:
                if frame["kind"] != "heartbeat":
                    yield CachedPublication(
                        frame, frame["publisherId"], {"viewRevision": frame["viewRevision"]}
                    )
        finally:
            await finish_owned(asyncio.create_task(iterator.aclose()))
