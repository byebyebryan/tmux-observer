"""Bounded, reaped subprocess capture for hostile external process output."""

# Adapted from rofi-tmux-plus 0.6.0; Copyright (c) 2026 Bryan; MIT.

from __future__ import annotations

import os
import selectors
import signal
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from tmux_observer._clock import boottime_ms

_CHUNK_SIZE = 16 * 1024


class ProcessLaunchError(OSError):
    """Popen failed before creating the command; later I/O errors differ."""


@dataclass(frozen=True, slots=True)
class BoundedCompleted:
    """A fully reaped process result whose captured streams never exceed their caps."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    overflow_streams: frozenset[str] = frozenset()
    # Keep the historical decoded fields for the remote framing callers, but
    # retain the complete bounded bytes for strict public JSON consumers.
    stdout_bytes: bytes | None = None
    stderr_bytes: bytes | None = None


def run_bounded(
    argv: Sequence[str],
    *,
    timeout: float,
    stdout_limit: int,
    stderr_limit: int,
    env: Mapping[str, str] | None = None,
) -> BoundedCompleted:
    """Capture bounded output, including when a descendant holds a pipe open."""
    if timeout <= 0 or stdout_limit < 1 or stderr_limit < 1:
        raise ValueError("bounded process limits must be positive")
    deadline = (boottime_ms() / 1000) + timeout
    try:
        process = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            start_new_session=True,
            env=env,
        )
    except OSError as error:
        raise ProcessLaunchError(error.errno, "command process could not be created") from error
    assert process.stdout is not None
    assert process.stderr is not None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    overflow_streams: set[str] = set()
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    timed_out = False

    def stop_group() -> None:
        try:
            if os.name == "posix":
                # The leader may have exited while its children still own pipes.
                os.killpg(process.pid, signal.SIGKILL)
            elif process.poll() is None:  # pragma: no cover - POSIX runtime
                process.kill()
        except ProcessLookupError:
            pass

    poller = selectors.DefaultSelector()
    try:
        poller.register(process.stdout, selectors.EVENT_READ, "stdout")
        poller.register(process.stderr, selectors.EVENT_READ, "stderr")
        while poller.get_map():
            remaining_time = deadline - (boottime_ms() / 1000)
            if remaining_time <= 0:
                timed_out = True
                break
            for key, _events in poller.select(min(remaining_time, 0.05)):
                if (boottime_ms() / 1000) >= deadline:
                    timed_out = True
                    break
                label = key.data
                buffer = buffers[label]
                remaining_bytes = limits[label] - len(buffer)
                chunk = os.read(key.fileobj.fileno(), min(_CHUNK_SIZE, remaining_bytes + 1))
                if not chunk:
                    poller.unregister(key.fileobj)
                    continue
                buffer.extend(chunk[:remaining_bytes])
                if len(chunk) > remaining_bytes:
                    overflow_streams.add(label)
                    break
            if overflow_streams or timed_out:
                break
        if not timed_out and not overflow_streams:
            while process.poll() is None:
                remaining = deadline - (boottime_ms() / 1000)
                if remaining <= 0:
                    timed_out = True
                    break
                try:
                    process.wait(timeout=min(remaining, 0.05))
                except subprocess.TimeoutExpired:
                    pass
        if (boottime_ms() / 1000) >= deadline:
            timed_out = True
        if timed_out or overflow_streams:
            stop_group()
            process.wait()
    finally:
        stop_group()
        process.wait()
        poller.close()
        process.stdout.close()
        process.stderr.close()
    stdout = bytes(buffers["stdout"])
    stderr = bytes(buffers["stderr"])
    return BoundedCompleted(
        process.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        timed_out=timed_out,
        overflow_streams=frozenset(overflow_streams),
        stdout_bytes=stdout,
        stderr_bytes=stderr,
    )
