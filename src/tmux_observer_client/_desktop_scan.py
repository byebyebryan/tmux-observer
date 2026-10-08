"""Extracted display-only viewer scan; no launch, focus or close implementation."""

# Adapted from rofi-tmux-plus 0.6.0; Copyright (c) 2026 Bryan; MIT.
from __future__ import annotations

import json
import os
import shutil
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tmux_observer._clock import boottime_ms
from tmux_observer._wire import _pairs, _preflight
from tmux_observer.native import Session, SessionReference

from ._command import run_bounded
from ._errors import ContractError


@dataclass(frozen=True)
class DesktopConfig:
    terminal: tuple[str, ...] = ("kitty",)


_METADATA_ENV = "ROFI_TMUX_PLUS_VIEWER_V1"


_MAX_NIRI_BYTES = 1024 * 1024


_MAX_PROC_FILE = 256 * 1024


_MAX_OBSERVATION_PROCESSES = 4096


_MAX_CHILDREN_BYTES = 64 * 1024


_MAX_DEPTH = 12


def kitty_configured(config: DesktopConfig) -> bool:
    """Return true only when the configured terminal executable is Kitty itself."""
    return bool(config.terminal) and Path(config.terminal[0]).name.casefold() == "kitty"


@dataclass(frozen=True, slots=True)
class _Proc:
    pid: int
    ppid: int
    pgrp: int
    session: int
    tty_nr: int
    start: int
    argv: tuple[str, ...]


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
        rows = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(rows, list) or len(rows) > 512:
        return None
    return rows


def _proc(pid: int) -> _Proc | None:
    try:
        raw_stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        close = raw_stat.rfind(")")
        if close < 0:
            return None
        fields = raw_stat[close + 1 :].split()
        if len(fields) < 20:
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
        return _Proc(pid, ppid, pgrp, session, tty_nr, start, argv)
    except (OSError, UnicodeError, ValueError):
        return None


def _is_tmux_attach(argv: Sequence[str], session_id: str) -> bool:
    if not argv or Path(argv[0]).name != "tmux":
        return False
    return len(argv) >= 5 and "attach-session" in argv and argv[-2:] == ("-t", session_id)


def _remote_attach_argv(executable: str, route: str, session_id: str) -> tuple[str, ...]:
    # Match the process argv used by RemoteLifecycle._launch. OpenSSH receives
    # one remote shell command whose session ID is quoted as a literal target.
    import shlex

    remote = " ".join(
        shlex.quote(item) for item in ("tmux", "-u", "attach-session", "-t", session_id)
    )
    return (Path(executable).name, "-t", route, remote)


@dataclass(frozen=True, slots=True)
class ViewerTarget:
    """One current owner reference and its local attachment route context."""

    session: Session
    local_owner: bool
    native_hostname: str | None
    remote_route: str | None = None
    remote_executable: str = "ssh"


@dataclass(frozen=True, slots=True)
class LocalViewerObservation:
    state: str
    confidence: str | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {"state": self.state}
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class ViewerObservationBatch:
    observed_at: int
    observations: Mapping[SessionReference, LocalViewerObservation]


@dataclass(frozen=True, slots=True)
class _MetadataState:
    status: str
    reference: SessionReference | None = None


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


def _observation_title_targets(
    targets: Sequence[ViewerTarget],
) -> Callable[[object], set[SessionReference]]:
    by_hostname: dict[str, list[ViewerTarget]] = {}
    for target in targets:
        if not target.session.name or not target.native_hostname:
            continue
        hostname = target.native_hostname.split(".", 1)[0].casefold()
        by_hostname.setdefault(hostname, []).append(target)

    def matching(value: object) -> set[SessionReference]:
        if not isinstance(value, str):
            return set()
        title = value.casefold()
        result: set[SessionReference] = set()
        for hostname, rows in by_hostname.items():
            if not title.rstrip().endswith(f"@ {hostname}"):
                continue
            for target in rows:
                name = target.session.name
                if name and title.startswith(f"{name.casefold()}:"):
                    result.add(target.session.reference)
        return result

    return matching


def observe_local_viewers(
    targets: Sequence[ViewerTarget],
    config: DesktopConfig,
    *,
    local_tmux: object,
    niri_command: Sequence[str] = ("niri",),
    now_millis: Callable[[], int] = lambda: boottime_ms(),
    deadline: float | None = None,
) -> ViewerObservationBatch:
    """Observe local Kitty/Niri viewer presence for a bulk set of current sessions.

    This is a display observation only. It creates no Viewer handles and reads
    no destroy-unattached option, so its results cannot authorize close actions.
    """
    observed_at = now_millis()
    unique: dict[SessionReference, ViewerTarget] = {}
    for target in targets:
        unique[target.session.reference] = target
    refs = tuple(unique)
    if not refs:
        return ViewerObservationBatch(observed_at, {})

    def unknown_all(reason: str) -> ViewerObservationBatch:
        return ViewerObservationBatch(
            observed_at,
            {reference: LocalViewerObservation("unknown", reason=reason) for reference in refs},
        )

    if not kitty_configured(config):
        return unknown_all("unsupported_desktop")
    scan_deadline = (
        min((boottime_ms() / 1000) + 2.0, deadline)
        if deadline is not None
        else (boottime_ms() / 1000) + 2.0
    )
    if (boottime_ms() / 1000) >= scan_deadline:
        return unknown_all("process_unavailable")
    windows = _niri_windows(
        niri_command, timeout_seconds=min(1.0, scan_deadline - (boottime_ms() / 1000))
    )
    if windows is None:
        return unknown_all("compositor_unavailable")

    local_client_pids: dict[str, set[int]] | None = None
    if any(target.local_owner for target in unique.values()):
        try:
            local_client_pids = local_tmux.client_pids_by_session()  # type: ignore[attr-defined]
        except (ContractError, OSError, ValueError, AttributeError):
            local_client_pids = None

    title_targets = _observation_title_targets(tuple(unique.values()))
    targets_by_ref = unique
    local_by_session_id: dict[str, ViewerTarget] = {
        target.session.reference.session_id: target
        for target in unique.values()
        if target.local_owner
    }
    client_owner_by_pid: dict[int, ViewerTarget] = {}
    if local_client_pids is not None:
        for session_id, pids in local_client_pids.items():
            target = local_by_session_id.get(session_id)
            if target is None:
                continue
            for pid in pids:
                client_owner_by_pid[pid] = target
    remote_by_argv: dict[tuple[str, ...], ViewerTarget] = {}
    remote_shell_by_argv: dict[tuple[str, ...], set[SessionReference]] = {}
    unsupported_remote: set[SessionReference] = set()
    for target in unique.values():
        if target.local_owner:
            continue
        if not target.remote_route:
            unsupported_remote.add(target.session.reference)
            continue
        argv = _remote_attach_argv(
            target.remote_executable,
            target.remote_route,
            target.session.reference.session_id,
        )
        remote_by_argv[argv] = target
        # A manually opened SSH shell does not name a tmux target. With a
        # current owner attachment and a unique matching title it can supply
        # only qualified display presence, never a verified operation handle.
        if target.session.attached_clients is not None and target.session.attached_clients > 0:
            for tty_options in ((), ("-t",), ("-tt",)):
                shell_argv = (
                    Path(target.remote_executable).name,
                    *tty_options,
                    target.remote_route,
                )
                remote_shell_by_argv.setdefault(shell_argv, set()).add(target.session.reference)

    index = _ObservationProcessIndex(deadline=scan_deadline)
    confirmed: set[SessionReference] = set()
    matched_windows: dict[SessionReference, set[tuple[int, int]]] = {}
    unresolved: dict[SessionReference, set[str]] = {}
    scan_incomplete = False

    def add_unknown(reference: SessionReference, reason: str) -> None:
        unresolved.setdefault(reference, set()).add(reason)

    for row in windows:
        if not isinstance(row, dict):
            scan_incomplete = True
            continue
        app_id = row.get("app_id")
        window_id = row.get("id")
        window_pid = row.get("pid")
        if not isinstance(app_id, str):
            scan_incomplete = True
            continue
        if (
            type(window_id) is not int
            or window_id <= 0
            or type(window_pid) is not int
            or window_pid <= 0
        ):
            if app_id == "kitty":
                scan_incomplete = True
            continue
        title_refs = title_targets(row.get("title"))
        if app_id != "kitty" and not title_refs:
            continue

        root, tree, complete = index.tree(window_pid)
        if not complete and app_id == "kitty":
            scan_incomplete = True
        if root is None:
            for reference in title_refs:
                add_unknown(reference, "process_unavailable")
            continue
        if app_id == "kitty" and (not root.argv or Path(root.argv[0]).name != "kitty"):
            for reference in title_refs:
                add_unknown(reference, "process_unavailable")
            if title_refs:
                scan_incomplete = True
            continue

        process_refs: set[SessionReference] = set()
        local_exact_refs: set[SessionReference] = set()
        local_argv_refs: set[SessionReference] = set()
        local_conflict_refs: set[SessionReference] = set()
        remote_shell_refs: set[SessionReference] = set()
        for proc in tree:
            current_local_target = client_owner_by_pid.get(proc.pid)
            if current_local_target is not None:
                current_ref = current_local_target.session.reference
                local_exact_refs.add(current_ref)
                process_refs.add(current_ref)
            if proc.tty_nr == 0:
                continue
            if proc.argv:
                shell_argv = (Path(proc.argv[0]).name, *proc.argv[1:])
                remote_shell_refs.update(
                    title_refs.intersection(remote_shell_by_argv.get(shell_argv, ()))
                )
            target: ViewerTarget | None = None
            if proc.argv and Path(proc.argv[0]).name == "tmux":
                for session_id, local_target in local_by_session_id.items():
                    if _is_tmux_attach(proc.argv, session_id):
                        target = local_target
                        local_argv_refs.add(target.session.reference)
                        if (
                            current_local_target is not None
                            and current_local_target.session.reference != target.session.reference
                        ):
                            local_conflict_refs.add(target.session.reference)
                        break
            if target is None:
                remote_target = remote_by_argv.get(proc.argv)
                if remote_target is not None:
                    process_refs.add(remote_target.session.reference)

        metadata = (
            index.metadata_state(window_pid) if app_id == "kitty" else _MetadataState("absent")
        )
        marker_ref = metadata.reference if metadata.status == "valid" else None
        if marker_ref in targets_by_ref and local_exact_refs and marker_ref not in local_exact_refs:
            local_conflict_refs.add(marker_ref)  # type: ignore[arg-type]
        candidates = title_refs | process_refs | local_argv_refs | local_conflict_refs
        if len(title_refs) > 1:
            for reference in title_refs:
                add_unknown(reference, "ambiguous_match")
        if marker_ref in targets_by_ref:
            candidates.add(marker_ref)  # type: ignore[arg-type]
        for reference in candidates:
            if reference not in targets_by_ref:
                continue
            target = targets_by_ref[reference]
            attached = reference in process_refs
            local_exact = reference in local_exact_refs
            local_argv = reference in local_argv_refs
            local_conflict = reference in local_conflict_refs
            title_match = reference in title_refs
            if app_id != "kitty":
                add_unknown(reference, "unsupported_desktop")
                continue
            if reference in unsupported_remote:
                add_unknown(reference, "attachment_unverified")
                continue
            if metadata.status == "unreadable":
                add_unknown(reference, "process_unavailable")
                continue
            if metadata.status == "invalid":
                add_unknown(reference, "conflicting_metadata")
                continue
            # A current local tmux client PID-to-session join is the live
            # attachment authority.  Kitty launch metadata and argv can name
            # the session the client originally attached before switching.
            if target.local_owner and local_exact:
                confirmed.add(reference)
                continue
            if metadata.status == "valid":
                if marker_ref != reference:
                    if title_match or attached or local_exact or local_argv or local_conflict:
                        add_unknown(reference, "conflicting_metadata")
                    continue
                if target.local_owner and local_conflict:
                    add_unknown(reference, "conflicting_metadata")
                elif target.local_owner:
                    reason = (
                        "attachment_unverified"
                        if local_client_pids is None
                        else "pending_registration"
                    )
                    add_unknown(reference, reason)
                elif attached:
                    confirmed.add(reference)
                else:
                    add_unknown(reference, "pending_registration")
                continue
            # With no marker, only the live local tmux client/session join is
            # enough for Confirmed. Legacy matches stay qualified by title and
            # an observed attachment process.
            if local_exact:
                confirmed.add(reference)
            elif local_conflict:
                add_unknown(reference, "conflicting_metadata")
            elif target.local_owner and (local_argv or title_match):
                add_unknown(
                    reference,
                    "attachment_unverified"
                    if local_client_pids is None
                    else "pending_registration",
                )
            elif (attached or reference in remote_shell_refs) and title_match:
                matched_windows.setdefault(reference, set()).add((window_id, window_pid))
            elif attached or title_match:
                add_unknown(reference, "attachment_unverified")

    for reference in refs:
        target = targets_by_ref[reference]
        if target.session.pending and reference not in confirmed:
            add_unknown(reference, "pending_registration")
        if reference in confirmed:
            continue
        if scan_incomplete or index.incomplete:
            add_unknown(reference, "process_unavailable")

    observations: dict[SessionReference, LocalViewerObservation] = {}
    for reference in refs:
        if reference in confirmed:
            observations[reference] = LocalViewerObservation("open", confidence="confirmed")
            continue
        candidates = matched_windows.get(reference, set())
        reasons = unresolved.get(reference, set())
        if len(candidates) > 1:
            reasons.add("ambiguous_match")
        if reasons:
            priority = (
                "ambiguous_match",
                "conflicting_metadata",
                "pending_registration",
                "process_unavailable",
                "unsupported_desktop",
                "attachment_unverified",
            )
            reason = next((item for item in priority if item in reasons), "inventory_incomplete")
            observations[reference] = LocalViewerObservation("unknown", reason=reason)
        elif len(candidates) == 1:
            observations[reference] = LocalViewerObservation("open", confidence="matched")
        else:
            observations[reference] = LocalViewerObservation("none")

    return ViewerObservationBatch(now_millis(), observations)
