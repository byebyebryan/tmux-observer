"""Private Unix endpoints and bounded explicit reads. Never starts publishers."""

from __future__ import annotations

import fcntl
import os
import selectors
import socket
import stat
import struct
from pathlib import Path

from tmux_observer._request_validation import validate_operation_error, validate_request
from tmux_observer.delivery import SERVICE_PROTOCOL, validate_service_frame
from tmux_observer.native import FRAME_LIMIT, REQUEST_LIMIT, decode_document, encode_document

from ._clock import boottime_ms, domain


class IPCError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def owner_socket() -> Path:
    root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return root / "tmux-observer" / "owner.sock"


def private_parent(path: Path, *, create=False):
    if not path.is_absolute() or len(os.fsencode(path)) >= 108:
        raise IPCError("invalid_endpoint", "invalid Unix endpoint path")
    if create:
        path.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = path.parent.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise IPCError("unsafe_endpoint", "endpoint parent must be private and user-owned")


def same_user(sock: socket.socket) -> bool:
    _pid, uid, _gid = struct.unpack(
        "3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    )
    return uid == os.getuid()


class Endpoint:
    """Exclusive publisher lease. Never replaces a live or foreign endpoint."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock = None
        self.socket = None
        self.inode = None
        private_parent(self.path, create=True)
        try:
            self.lock = os.open(
                str(self.path) + ".lock",
                os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
            )
            info = os.fstat(self.lock)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise IPCError("unsafe_endpoint", "invalid publisher lease file")
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise IPCError("publisher_running", "publisher lease is already held") from error
            if self.path.exists() or self.path.is_symlink():
                info = self.path.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                    raise IPCError("unsafe_endpoint", "refusing a foreign endpoint")
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                    probe.settimeout(0.1)
                    try:
                        probe.connect(str(self.path))
                    except ConnectionRefusedError:
                        pass
                    except OSError as error:
                        raise IPCError(
                            "endpoint_uncertain", "cannot establish that endpoint is abandoned"
                        ) from error
                    else:
                        raise IPCError("publisher_running", "a live endpoint already exists")
                self.path.unlink()
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.bind(str(self.path))
            self.inode = self.path.lstat().st_ino
            self.path.chmod(0o600)
            self.socket.listen(32)
            self.socket.setblocking(False)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.socket is not None:
            self.socket.close()
        if self.inode is not None:
            try:
                if self.path.lstat().st_ino == self.inode:
                    self.path.unlink()
            except FileNotFoundError:
                pass
        if self.lock is not None:
            os.close(self.lock)
            self.lock = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def connect(path: Path, *, deadline: int) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        private_parent(path)
        info = path.lstat()
        if (
            not stat.S_ISSOCK(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise IPCError("unsafe_endpoint", "endpoint must be private and user-owned")
        sock.settimeout(max(0.001, (deadline - boottime_ms()) / 1000))
        sock.connect(str(path))
        if not same_user(sock):
            raise IPCError("wrong_peer", "publisher peer UID differs")
        if boottime_ms() >= deadline:
            raise IPCError("deadline", "late endpoint connection rejected")
        sock.setblocking(False)
        return sock
    except FileNotFoundError as error:
        sock.close()
        raise IPCError("service_absent", "owner publisher is unavailable") from error
    except ConnectionRefusedError as error:
        sock.close()
        raise IPCError("service_absent", "owner publisher is unavailable") from error
    except BaseException:
        sock.close()
        raise


def exchange(request: dict, *, path: Path | None = None, budget_ms=2000) -> dict:
    """One read/control request. The caller explicitly chooses refresh, if any."""
    validate_request(request)
    raw = encode_document(request, limit=REQUEST_LIMIT)
    deadline = boottime_ms() + budget_ms
    with (
        connect(owner_socket() if path is None else path, deadline=deadline) as sock,
        selectors.DefaultSelector() as selector,
    ):
        selector.register(sock, selectors.EVENT_WRITE)
        sent = 0
        buffer = bytearray()
        while True:
            remaining = deadline - boottime_ms()
            if remaining <= 0:
                raise IPCError("deadline", "publisher response exceeded its deadline")
            for _key, events in selector.select(min(0.05, remaining / 1000)):
                if events & selectors.EVENT_WRITE:
                    sent += sock.send(raw[sent:])
                    if sent == len(raw):
                        selector.modify(sock, selectors.EVENT_READ)
                if events & selectors.EVENT_READ:
                    chunk = sock.recv(65536)
                    if not chunk:
                        raise IPCError("disconnected", "publisher closed before a complete record")
                    buffer.extend(chunk)
                    if len(buffer) > FRAME_LIMIT:
                        raise IPCError("frame_limit", "publisher record exceeded its bound")
                    if b"\n" in buffer:
                        if boottime_ms() >= deadline:
                            raise IPCError("deadline", "late publisher response rejected")
                        value = decode_document(bytes(buffer), limit=FRAME_LIMIT)
                        if value.get("kind") == "operation_error":
                            validate_operation_error(value)
                            if value["protocol"] != request["protocol"]:
                                raise IPCError("scope_mismatch", "wrong service error protocol")
                            raise IPCError(value["error"]["code"], value["error"]["message"])
                        if request["protocol"] == SERVICE_PROTOCOL:
                            validate_service_frame(value)
                            scope_matches = (
                                value["source"]["hostId"] == request["expectedHost"]
                                and value["source"]["uid"] == os.getuid()
                            )
                            incarnation = value["publisherId"]
                        else:
                            validate_fleet_frame(value)
                            scope_matches = value["contextId"] == request["contextId"]
                            if "expectedHost" in request:
                                scope_matches &= (
                                    value["snapshot"] is not None
                                    and value["snapshot"]["mesh"]["localHostId"]
                                    == request["expectedHost"]
                                )
                            incarnation = value["readerId"]
                        if (
                            value["protocol"] != request["protocol"]
                            or not scope_matches
                            or value["requestId"] != request["requestId"]
                            or value["sequence"] != 0
                        ):
                            raise IPCError(
                                "scope_mismatch", "publisher response does not match request scope"
                            )
                        local_clock = domain()
                        if any(
                            value["clock"][key] != local_clock[key]
                            for key in ("bootId", "timeNamespace")
                        ):
                            raise IPCError("scope_mismatch", "publisher clock domain differs")
                        if "publisherId" in request and incarnation != request["publisherId"]:
                            raise IPCError("stale_scope", "publisher incarnation changed")
                        if boottime_ms() >= deadline:
                            raise IPCError("deadline", "publisher validation exceeded its deadline")
                        return value


def validate_fleet_frame(value):
    """Load prepared-domain validation only for an explicit Fleet request."""
    from tmux_observer_client.contract import validate_fleet_frame as validate

    return validate(value)
