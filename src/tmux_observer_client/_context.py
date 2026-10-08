"""Explicit per-context user-unit handoff. Cached readers never import this."""

from __future__ import annotations

import contextlib
import fcntl
import os
import re
import stat
import tempfile
import unicodedata
from pathlib import Path

from tmux_observer._clock import domain
from tmux_observer._ipc import IPCError, private_parent

from ._command import run_bounded
from .public import desktop_context_id, fleet_socket

LIMIT = 65536
KEYS = (
    "PATH",
    "XDG_RUNTIME_DIR",
    "NIRI_SOCKET",
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "SSH_AUTH_SOCK",
    "TMUX_TMPDIR",
)


def unit_name(context):
    fleet_socket(context)  # Validate before constructing a manager operation.
    return f"tmux-observer-fleet@{context}.service"


def context_file(context):
    return fleet_socket(context).with_name(f"context-{context}.env")


def render(host_id, environment):
    if (
        not isinstance(host_id, str)
        or len(host_id) > 128
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", host_id) is None
    ):
        raise IPCError("invalid_context", "invalid fixed owner host ID")
    context = desktop_context_id(environment)
    clock = domain()
    values = {key: environment.get(key, "") for key in KEYS}
    values["XDG_RUNTIME_DIR"] = str(
        Path(environment.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    )
    values["TMUX_OBSERVER_HOST_ID"] = host_id
    lines = [
        f"# tmux-observer context v1 uid={os.getuid()} context={context}",
        f"# boot={clock['bootId']} namespace={clock['timeNamespace']}",
    ]
    for key, value in values.items():
        if (
            not isinstance(value, str)
            or len(value) > 16384
            or any(unicodedata.category(char).startswith("C") or char == "\ufeff" for char in value)
        ):
            raise IPCError("invalid_context", "context environment has invalid characters or size")
        # EnvironmentFile double quoting; no shell expansion or arbitrary keys.
        value = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(key + '="' + value + '"')
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    if len(raw) > LIMIT:
        raise IPCError("capacity", "context environment exceeds its file bound")
    return context, raw


def read_file(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise IPCError("unsafe_context", "context file is missing or unsafe") from error
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > LIMIT
        ):
            raise IPCError("unsafe_context", "context file must be private and user-owned")
        raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise IPCError("capacity", "context file exceeded its bound")
        return raw, info.st_ino


@contextlib.contextmanager
def registry(context):
    path = context_file(context)
    private_parent(path, create=True)
    fd = os.open(
        path.parent / ".contexts.lock", os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600
    )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise IPCError("unsafe_context", "context registry lease is unsafe")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise IPCError(
                "context_busy", "another explicit context operation is running"
            ) from error
        yield path
    finally:
        os.close(fd)


def publish(path, raw):
    if path.exists() or path.is_symlink():
        existing, _inode = read_file(path)
        if existing != raw:
            raise IPCError(
                "context_conflict", "stop the existing context before replacing its environment"
            )
        return
    if len(list(path.parent.glob("context-*.env"))) >= 16:
        raise IPCError("capacity", "captured desktop context capacity exceeded")
    fd, temporary = tempfile.mkstemp(prefix=".context-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Link a complete private file without ever replacing another context.
        os.link(temporary, path)
    finally:
        Path(temporary).unlink()


def manager(operation, context, runner):
    value = runner(
        ["systemctl", "--user", operation, unit_name(context)],
        timeout=7,
        stdout_limit=16384,
        stderr_limit=16384,
    )
    if value.returncode != 0 or value.timed_out or value.overflow_streams:
        raise IPCError("context_operation_failed", "explicit user-unit operation failed")


def prepare_context(host_id, *, start=False, runner=run_bounded):
    context, raw = render(host_id, os.environ)
    with registry(context) as path:
        publish(path, raw)
        if start:
            manager("reset-failed", context, runner)
            manager("start", context, runner)
    return {
        "schemaVersion": 1,
        "contextId": context,
        "unit": unit_name(context),
        "environmentFile": str(path),
        "state": "start_requested" if start else "prepared",
    }


def stop_context(context, *, runner=run_bounded):
    with registry(context) as path:
        identity = None
        if path.exists() or path.is_symlink():
            raw, identity = read_file(path)
            prefix = f"# tmux-observer context v1 uid={os.getuid()} context={context}\n".encode()
            if not raw.startswith(prefix):
                raise IPCError(
                    "unsafe_context", "context file is not a captured observer environment"
                )
        manager("stop", context, runner)
        if identity is not None:
            if path.lstat().st_ino != identity:
                raise IPCError("context_conflict", "context file was replaced during stop")
            path.unlink()
    return {
        "schemaVersion": 1,
        "contextId": context,
        "unit": unit_name(context),
        "environmentFile": str(path),
        "state": "stopped",
    }
