"""Bounded read-only Niri window adapter."""

import json
import os
import shutil
import socket
import struct
from collections.abc import Sequence

from tmux_observer._clock import boottime_ms
from tmux_observer._wire import _constant, _pairs, _preflight

from ._command import run_bounded

_MAX_NIRI_BYTES = 1024 * 1024


def _socket_windows(path, timeout_seconds):
    """One fixed passive request; no actions, subscriptions or retained socket."""
    deadline = boottime_ms() + timeout_seconds * 1000
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        remaining = deadline - boottime_ms()
        if remaining <= 0:
            raise ValueError("expired compositor read")
        stream.settimeout(remaining / 1000)
        stream.connect(path)
        _pid, uid, _gid = struct.unpack(
            "3i", stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        if uid != os.getuid():
            raise ValueError("foreign compositor peer")
        remaining = deadline - boottime_ms()
        if remaining <= 0:
            raise ValueError("expired compositor read")
        stream.settimeout(remaining / 1000)
        stream.sendall(b'"Windows"\n')
        raw = bytearray()
        while b"\n" not in raw:
            remaining = deadline - boottime_ms()
            if remaining <= 0:
                raise ValueError("expired compositor read")
            stream.settimeout(remaining / 1000)
            chunk = stream.recv(min(65536, _MAX_NIRI_BYTES + 1 - len(raw)))
            if not chunk:
                raise ValueError("incomplete compositor reply")
            raw.extend(chunk)
            if len(raw) > _MAX_NIRI_BYTES:
                raise ValueError("oversized compositor reply")
        if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
            raise ValueError("ambiguous compositor reply")
        text = raw.decode("utf-8", "strict")
        _preflight(text)
        reply = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
        if (
            not isinstance(reply, dict)
            or set(reply) != {"Ok"}
            or not isinstance(reply["Ok"], dict)
            or set(reply["Ok"]) != {"Windows"}
        ):
            raise ValueError("foreign compositor reply")
        rows = reply["Ok"]["Windows"]
        if not isinstance(rows, list) or len(rows) > 512 or boottime_ms() >= deadline:
            raise ValueError("invalid or late compositor window list")
        return rows


def _niri_windows(
    niri_command: Sequence[str], *, timeout_seconds: float = 1.0
) -> list[object] | None:
    path = os.environ.get("NIRI_SOCKET")
    if not path:
        return None
    if tuple(niri_command) == ("niri",):
        try:
            return _socket_windows(path, timeout_seconds)
        except (OSError, ValueError, RecursionError):
            return None
    if not niri_command or shutil.which(niri_command[0]) is None:
        return None
    try:
        completed = run_bounded(
            [*niri_command, "msg", "-j", "windows"],
            timeout=timeout_seconds,
            stdout_limit=_MAX_NIRI_BYTES,
            stderr_limit=65536,
        )
    except (OSError, ValueError):
        return None
    if completed.timed_out or completed.overflow_streams:
        return None
    raw = completed.stdout_bytes
    if completed.returncode != 0 or not isinstance(raw, bytes) or len(raw) > _MAX_NIRI_BYTES:
        return None
    try:
        text = raw.decode("utf-8", "strict")
        _preflight(text)
        rows = json.loads(text, object_pairs_hook=_pairs)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(rows, list) or len(rows) > 512:
        return None
    return rows
