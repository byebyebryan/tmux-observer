"""Bounded local process trees and launch annotations; no native tmux reads."""

import json
import os
from collections import deque
from collections.abc import Mapping

from tmux_observer._clock import boottime_ms
from tmux_observer._wire import _pairs, _preflight
from tmux_observer.native import SessionReference

from ._desktop_types import _MetadataState, _Proc

_METADATA_ENV = "ROFI_TMUX_PLUS_VIEWER_V1"
_MAX_PROC_FILE = 256 * 1024
_MAX_OBSERVATION_PROCESSES = 4096
_MAX_CHILDREN_BYTES = 64 * 1024
_MAX_DEPTH = 12


def _proc(pid: int) -> _Proc | None:
    try:
        directory = os.open(
            f"/proc/{pid}", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        )
        try:
            uid = os.fstat(directory).st_uid
            if uid != os.getuid():
                return None
            fd = os.open("stat", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory)
            try:
                raw = os.read(fd, 4097)
            finally:
                os.close(fd)
        finally:
            os.close(directory)
        if len(raw) > 4096:
            return None
        raw_stat = raw.decode("utf-8", "strict")
        close = raw_stat.rfind(")")
        if close < 0:
            return None
        fields = raw_stat[close + 1 :].split()
        if len(fields) < 20 or fields[0] in ("Z", "X", "x"):
            return None
        ppid, pgrp, session, tty_nr, start = (
            int(fields[1]),
            int(fields[2]),
            int(fields[3]),
            int(fields[4]),
            int(fields[19]),
        )
        fd = os.open(f"/proc/{pid}/cmdline", os.O_RDONLY | os.O_CLOEXEC)
        try:
            raw_cmdline = os.read(fd, 32 * 1024 + 1)
        finally:
            os.close(fd)
        if len(raw_cmdline) > 32 * 1024:
            return None
        argv = tuple(part.decode("utf-8", "replace") for part in raw_cmdline.split(b"\0") if part)
        return _Proc(pid, ppid, pgrp, session, tty_nr, start, argv, uid)
    except (OSError, UnicodeError, ValueError):
        return None


def _child_bytes(pid):
    with open(f"/proc/{pid}/task/{pid}/children", "rb") as stream:
        return stream.read(_MAX_CHILDREN_BYTES + 1)


class _ObservationProcessIndex:
    """Shared bounded process, child-list, and launch-metadata reads for one scan."""

    def __init__(
        self,
        *,
        process_limit: int = _MAX_OBSERVATION_PROCESSES,
        deadline: float | None = None,
    ) -> None:
        self.process_limit = process_limit
        self.deadline = deadline
        self.processes: dict[int, _Proc | None] = {}
        self.children: dict[int, tuple[tuple[int, ...] | None, bool]] = {}
        self.metadata: dict[int, _MetadataState] = {}
        self.incomplete = False
        self._read_count = 0

    def _can_read(self) -> bool:
        if self.deadline is not None and (boottime_ms() / 1000) >= self.deadline:
            self.incomplete = True
            return False
        if self._read_count >= self.process_limit:
            self.incomplete = True
            return False
        return True

    def _begin_read(self) -> None:
        self._read_count += 1

    def proc(self, pid: int) -> _Proc | None:
        if pid in self.processes:
            return self.processes[pid]
        if not self._can_read():
            return None
        self._begin_read()
        result = _proc(pid)
        self.processes[pid] = result
        if result is None:
            self.incomplete = True
        return result

    def revalidate(self, pid: int) -> bool:
        if not self._can_read():
            return False
        self._begin_read()
        previous = self.processes.get(pid)
        return previous is not None and _proc(pid) == previous

    def child_pids(self, pid: int) -> tuple[tuple[int, ...] | None, bool]:
        if pid in self.children:
            return self.children[pid]
        if not self._can_read():
            return None, False
        self._begin_read()
        try:
            raw = _child_bytes(pid)
            if len(raw) > _MAX_CHILDREN_BYTES:
                result = (None, False)
            else:
                text = raw.decode("ascii")
                values = text.split()
                if len(values) > self.process_limit or any(
                    not value.isdecimal() or int(value) <= 0 for value in values
                ):
                    result = (None, False)
                else:
                    result = (tuple(int(value) for value in values), True)
        except (OSError, UnicodeError, ValueError):
            result = (None, False)
        self.children[pid] = result
        if not result[1]:
            self.incomplete = True
        return result

    def tree(self, root_pid: int) -> tuple[_Proc | None, tuple[_Proc, ...], bool]:
        root = self.proc(root_pid)
        if root is None:
            return None, (), False
        rows: list[_Proc] = []
        queue: deque[tuple[int, int]] = deque([(root_pid, 0)])
        seen = {root_pid}
        complete = True
        while queue:
            if self.deadline is not None and (boottime_ms() / 1000) >= self.deadline:
                complete = False
                break
            pid, depth = queue.popleft()
            if pid != root_pid:
                proc = self.proc(pid)
                if proc is None:
                    complete = False
                    continue
                rows.append(proc)
            if depth >= _MAX_DEPTH or len(seen) > self.process_limit:
                complete = False
                break
            child_pids, children_complete = self.child_pids(pid)
            if not children_complete or child_pids is None:
                complete = False
                continue
            for child in child_pids:
                if self.deadline is not None and (boottime_ms() / 1000) >= self.deadline:
                    complete = False
                    break
                if child in seen:
                    complete = False
                    continue
                seen.add(child)
                if len(seen) > self.process_limit:
                    complete = False
                    self.incomplete = True
                    break
                queue.append((child, depth + 1))
        if not complete:
            self.incomplete = True
        return root, tuple(rows), complete

    def metadata_state(self, pid: int) -> _MetadataState:
        if pid in self.metadata:
            return self.metadata[pid]
        if not self._can_read():
            return _MetadataState("unreadable")
        self._begin_read()
        metadata, marker_present, readable = _read_metadata_detailed(pid)
        if pid not in self.metadata:
            if not readable:
                result = _MetadataState("unreadable")
            elif not marker_present:
                result = _MetadataState("absent")
            elif metadata is None:
                result = _MetadataState("invalid")
            else:
                reference = _metadata_reference(metadata)
                launch_id = metadata.get("launchId")
                if (
                    reference is None
                    or not isinstance(launch_id, str)
                    or not launch_id
                    or len(launch_id) > 128
                ):
                    result = _MetadataState("invalid")
                else:
                    result = _MetadataState("valid", reference)
            self.metadata[pid] = result
        return self.metadata[pid]


def _metadata_reference(metadata: Mapping[str, object]) -> SessionReference | None:
    value = metadata.get("sessionRef")
    if not isinstance(value, dict) or set(value) != {
        "hostId",
        "serverGeneration",
        "sessionId",
        "createdAt",
    }:
        return None
    host_id = value.get("hostId")
    generation = value.get("serverGeneration")
    session_id = value.get("sessionId")
    created_at = value.get("createdAt")
    if (
        not isinstance(host_id, str)
        or not host_id
        or len(host_id) > 4096
        or not isinstance(generation, str)
        or not generation
        or len(generation) > 4096
        or not isinstance(session_id, str)
        or not session_id.startswith("$")
        or not session_id[1:].isascii()
        or not session_id[1:].isdecimal()
        or not isinstance(created_at, int)
        or isinstance(created_at, bool)
        or created_at < 0
    ):
        return None
    return SessionReference(host_id, generation, session_id, created_at)


def _read_metadata_detailed(pid: int) -> tuple[dict[str, object] | None, bool, bool]:
    try:
        fd = os.open(f"/proc/{pid}/environ", os.O_RDONLY | os.O_CLOEXEC)
        try:
            raw = os.read(fd, _MAX_PROC_FILE + 1)
        finally:
            os.close(fd)
    except OSError:
        return None, False, False
    if len(raw) > _MAX_PROC_FILE:
        return None, True, False
    found = [
        part[len(_METADATA_ENV) + 1 :]
        for part in raw.split(b"\0")
        if part.startswith(_METADATA_ENV.encode() + b"=")
    ]
    if not found:
        return None, False, True
    if len(found) != 1:
        return None, True, True
    try:
        text = found[0].decode("utf-8", "strict")
        _preflight(text)
        value = json.loads(text, object_pairs_hook=_pairs)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, True, True
    schema_version = value.get("schemaVersion") if isinstance(value, dict) else None
    if not isinstance(value, dict) or type(schema_version) is not int or schema_version != 1:
        return None, True, True
    return value, True, True
