"""Bounded read-only Niri window adapter."""

import json
import os
import shutil
from collections.abc import Sequence

from tmux_observer._wire import _pairs, _preflight

from ._command import run_bounded

_MAX_NIRI_BYTES = 1024 * 1024


def _niri_windows(
    niri_command: Sequence[str], *, timeout_seconds: float = 1.0
) -> list[object] | None:
    if not os.environ.get("NIRI_SOCKET") or shutil.which(niri_command[0]) is None:
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
