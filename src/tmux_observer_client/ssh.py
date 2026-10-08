"""One owned non-PTY SSH bridge per remote owner, with bounded live framing."""

from __future__ import annotations

import collections
import os
import selectors
import shlex
import signal
import subprocess
import uuid

from tmux_observer._clock import boottime_ms
from tmux_observer.public import (
    FRAME_LIMIT,
    REQUEST_LIMIT,
    SERVICE_PROTOCOL,
    decode_document,
    encode_document,
    validate_operation_error,
    validate_request,
)

from ._errors import ContractError
from ._remote_state import RemoteState
from .direct import REACHED, REMOTE_EXEC, ssh_argv


class RemoteConnection:
    def __init__(
        self, host, route, policy, now, *, state=None, remote_exec=REMOTE_EXEC, on_frame=None
    ):
        self.host = host
        self.route = route
        self.state = state or RemoteState(host.host_id)
        self.nonce = uuid.uuid4().hex
        self.state.start(self.nonce, now)
        program = "printf '\\036TMUX_OBSERVER_REACHED_V1:%s\\037\\n' " + shlex.quote(self.nonce)
        program += (
            " >&2; exec "
            + remote_exec
            + " "
            + " ".join(
                map(
                    shlex.quote,
                    ("bridge", "--expected-host", host.host_id, "--request-id", self.nonce),
                )
            )
        )
        self.process = subprocess.Popen(
            ssh_argv(route.destination, policy, program),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.selector = selectors.DefaultSelector()
        for name, stream in (("stdout", self.process.stdout), ("stderr", self.process.stderr)):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.incoming = bytearray()
        self.first_byte = None
        self.stderr = bytearray()
        self.outgoing = collections.deque()
        self.output_at = None
        self.on_frame = on_frame
        self.closed = False
        self.reached_reported = False

    @property
    def reached(self):
        return (
            len(self.stderr) <= 65536
            and bytes(self.stderr).count((REACHED + self.nonce + "\x1f\n").encode()) == 1
        )

    @property
    def unreachable(self):
        if self.reached or len(self.stderr) > 65536:
            return False
        diagnostic = bytes(self.stderr).decode(errors="replace").casefold()
        return (
            self.state.error is not None
            and self.state.error["code"] == "deadline"
            or any(
                text in diagnostic
                for text in (
                    "could not resolve hostname",
                    "name or service not known",
                    "connection refused",
                    "connection timed out",
                    "operation timed out",
                    "no route to host",
                    "network is unreachable",
                    "connection reset by peer",
                    "kex_exchange_identification",
                )
            )
        )

    def send(self, request, now):
        validate_request(request)
        if (
            self.closed
            or request["protocol"] != SERVICE_PROTOCOL
            or request["expectedHost"] != self.host.host_id
            or request["operation"] == "watch"
        ):
            raise ContractError("operation_failed", "remote request has a foreign or closed scope")
        raw = encode_document(request, limit=REQUEST_LIMIT)
        if sum(len(item) for item in self.outgoing) + len(raw) > 65536:
            raise ContractError("operation_failed", "remote request queue exceeded its bound")
        self.outgoing.append(raw)
        if self.output_at is None:
            self.output_at = now
        if self.process.stdin not in self.selector.get_map():
            self.selector.register(self.process.stdin, selectors.EVENT_WRITE, "stdin")

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=1)
        self.selector.close()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()
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
            self.fail("deadline", "remote framing exceeded its first-byte/send deadline")
            return False
        return True

    def poll(self, now):
        if self.closed or not self.check_deadlines(now):
            return
        if self.process.poll() is not None:
            # Exit cannot preserve buffered positives. Bounded diagnostics can
            # still distinguish a transport failure from a reached owner.
            try:
                while len(self.stderr) <= 65536:
                    chunk = os.read(self.process.stderr.fileno(), 65537 - len(self.stderr))
                    if not chunk:
                        break
                    self.stderr.extend(chunk)
            except BlockingIOError:
                pass
            self.fail("disconnected", "SSH bridge ended")
            return
        try:
            for key, _events in self.selector.select(0):
                now = boottime_ms()
                if not self.check_deadlines(now):
                    return
                if key.data == "stdin":
                    try:
                        sent = os.write(key.fileobj.fileno(), self.outgoing[0])
                    except BlockingIOError:
                        continue
                    if sent == len(self.outgoing[0]):
                        self.outgoing.popleft()
                        self.output_at = now if self.outgoing else None
                    else:
                        self.outgoing[0] = self.outgoing[0][sent:]
                    if not self.outgoing:
                        self.selector.unregister(self.process.stdin)
                elif key.data == "stderr":
                    chunk = os.read(key.fileobj.fileno(), min(65536, 65537 - len(self.stderr)))
                    if not chunk:
                        self.selector.unregister(key.fileobj)
                    self.stderr.extend(chunk)
                    if len(self.stderr) > 65536:
                        raise ValueError("SSH stderr exceeded its bound")
                else:
                    chunk = os.read(
                        key.fileobj.fileno(), min(65536, FRAME_LIMIT + 1 - len(self.incoming))
                    )
                    if not chunk:
                        self.fail("disconnected", "SSH bridge stdout ended")
                        return
                    if self.first_byte is None:
                        self.first_byte = now
                    self.incoming.extend(chunk)
            for _ in range(8):
                if b"\n" not in self.incoming:
                    break
                first_byte = self.first_byte
                raw, _, rest = self.incoming.partition(b"\n")
                value = decode_document(bytes(raw) + b"\n", limit=FRAME_LIMIT)
                now = boottime_ms()
                if first_byte is not None and now - first_byte >= 2000:
                    raise ValueError("late frame rejected after parsing")
                self.incoming = bytearray(rest)
                self.first_byte = first_byte if rest else None
                if value.get("kind") == "operation_error":
                    validate_operation_error(value)
                    if value["protocol"] != SERVICE_PROTOCOL:
                        raise ValueError("foreign owner error")
                    self.fail(
                        "owner_unavailable", "remote owner returned a scoped operation failure"
                    )
                    return
                matched = self.state.receive(value, now)
                if self.on_frame is not None:
                    self.on_frame(self, value, matched, now)
            if len(self.incoming) > FRAME_LIMIT:
                raise ValueError("owner frame exceeded its bound")
            request = self.state.probe(boottime_ms())
            if request is not None:
                self.send(request, boottime_ms())
        except (OSError, ValueError, ContractError) as error:
            self.fail("invalid_owner_stream", "remote owner stream failed its bounded protocol")
            if isinstance(error, ContractError) and error.code == "stale_mesh":
                raise
