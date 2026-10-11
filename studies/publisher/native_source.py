"""Observer-owned cached IPC design candidate. No collection or reference imports."""

import asyncio
import json
import os
import uuid
from pathlib import Path

from generic_publisher import CachedPublication, CachedPublisher
from mesh_plus.transport import connect_ipc, finish_owned, within_deadline

from tmux_observer._clock import boottime_ms, domain
from tmux_observer.delivery import SERVICE_PROTOCOL, validate_service_frame
from tmux_observer.mesh_profile import TmuxMeshProfile
from tmux_observer.native import FRAME_LIMIT, REQUEST_LIMIT, decode_document, encode_document


def require(condition, code):
    if not condition:
        raise ValueError(code)


class NativeGuard:
    """Native per-connection ordering, scope and kernel-clock association."""

    def __init__(self, host, request_id):
        self.host, self.request_id = host, request_id
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
        )
        if self.previous is None:
            require(frame["requestId"] == self.request_id, "native_request")
        else:
            epoch, sequence, revision, emitted = self.previous
            require(current[0] == epoch, "native_publisher_restart")
            require(current[1] == sequence + 1, "native_stream_order")
            require(current[2] >= revision, "native_revision_regression")
            require(current[3] >= emitted, "native_clock_regression")
        self.previous = current
        return frame


class TmuxCachedSource:
    def __init__(self, host, path, *, trace=None):
        self.host, self.path = host, Path(path)
        self.trace = None if trace is None else Path(trace)
        self.active = 0
        self.reads = 0

    def note(self, event, **fields):
        if self.trace is not None:
            fd = os.open(self.trace, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as output:
                output.write(
                    json.dumps({"event": event, "host": self.host, "at": boottime_ms(), **fields})
                    + "\n"
                )

    async def frames(self, operation):
        require(operation in {"status", "watch"}, "native_cached_operation")
        deadline = boottime_ms() + 2000
        opening = asyncio.create_task(connect_ipc(self.path, maximum=FRAME_LIMIT))
        try:
            channel = await finish_owned(opening)
        except BaseException:
            # Cancellation can arrive after opening succeeded but before the
            # result was delivered. Retire that admitted connection explicitly.
            if opening.done() and not opening.cancelled() and opening.exception() is None:
                await finish_owned(asyncio.create_task(opening.result().close()))
            raise
        self.active += 1
        self.reads += 1
        try:
            require(boottime_ms() < deadline, "native_setup_deadline")
            request_id = uuid.uuid4().hex
            guard = NativeGuard(self.host, request_id)
            self.note("cached_request", operation=operation, read=self.reads)
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
                # A first byte fixes a separate complete-frame budget.
                silence = deadline if first else boottime_ms() + 15000
                initial = await within_deadline(channel.reader.readexactly(1), silence)
                framed = boottime_ms() + 2000
                raw = (
                    initial
                    if initial == b"\n"
                    else initial
                    + await within_deadline(
                        channel.reader.readuntil(b"\n"), min(framed, deadline) if first else framed
                    )
                )
                require(len(raw) <= FRAME_LIMIT, "native_capacity")
                frame = guard.accept(decode_document(raw, limit=FRAME_LIMIT))
                require(
                    boottime_ms() < min(framed, deadline) if first else boottime_ms() < framed,
                    "native_frame_deadline",
                )
                first = False
                self.note(
                    "cached_reply", operation=operation, accepted=frame["receipt"]["accepted"]
                )
                yield frame
                if operation != "watch":
                    return
        finally:
            try:
                await finish_owned(asyncio.create_task(channel.close()))
            finally:
                self.active -= 1
                self.note("cached_closed", active=self.active)

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


def make_tmux_publisher(host, source, socket):
    native = TmuxCachedSource(host, socket, trace=os.environ.get("TMUX_PUBLISHER_STUDY_TRACE"))
    native.note("factory", implementation="observer-owned-study")
    return CachedPublisher("tmux", host, source, native, profile=TmuxMeshProfile())
