"""Bounded new-client discovery and retained local Kitty display associations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tmux_observer._clock import boottime_ms

from ._desktop_input import reference
from ._niri_observation import _niri_windows
from ._process_evidence import _proc
from .attachments import current_attachments
from .bindings_contract import BINDINGS_PROTOCOL, validate_bindings


@dataclass(frozen=True)
class Resolution:
    # Window/process identities stay internal. They confer no action authority.
    window: tuple[int, int, int] | None
    resolved_at: int | None
    reason: str


@dataclass
class Entry:
    resolution: Resolution
    attempts: int
    retry_at: int


def window_signature(windows):
    if windows is None:
        return None
    ids, values = set(), []
    for row in windows:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] <= 0:
            return None
        if row["id"] in ids:
            return None
        ids.add(row["id"])
        if row.get("app_id") == "kitty":
            if type(row.get("pid")) is not int or row["pid"] <= 0:
                return None
            values.append((row["id"], row["pid"]))
    return tuple(sorted(values))


def discover_clients(
    clients, *, uid, deadline, windows_reader=_niri_windows, proc_reader=_proc, now=boottime_ms
):
    """Follow only new client ancestors, with one bounded opening/closing capture."""
    unknown = lambda reason: {key: Resolution(None, None, reason) for key in clients}
    if not clients:
        return {}

    def windows():
        if now() >= deadline:
            return None
        return windows_reader(
            ("niri",), timeout_seconds=max(0.001, min(1, (deadline - now()) / 1000))
        )

    opening = window_signature(windows())
    if opening is None:
        return unknown("compositor_unavailable")
    by_pid = {}
    for window_id, pid in opening:
        by_pid.setdefault(pid, []).append(window_id)
    processes, candidates = {}, {}
    reads = 0

    def read(pid):
        nonlocal reads
        if pid in processes:
            return processes[pid]
        if now() >= deadline or reads >= 4096:
            return None
        reads += 1
        value = proc_reader(pid)
        processes[pid] = value
        return value

    for key in clients:
        pid, start = key
        seen = set()
        candidates[key] = Resolution(None, None, "window_unresolved")
        for _ in range(64):
            if pid in seen or pid <= 0:
                break
            seen.add(pid)
            process = read(pid)
            if process is None or process.uid != uid:
                candidates[key] = Resolution(None, None, "process_unavailable")
                break
            if pid == key[0] and process.start != start:
                candidates[key] = Resolution(None, None, "process_unavailable")
                break
            if pid in by_pid:
                if not process.argv or Path(process.argv[0]).name != "kitty":
                    candidates[key] = Resolution(None, None, "process_unavailable")
                elif len(by_pid[pid]) != 1:
                    candidates[key] = Resolution(None, None, "ambiguous_match")
                else:
                    candidates[key] = Resolution(
                        (by_pid[pid][0], pid, process.start), None, "retained_native_association"
                    )
                break
            pid = process.ppid
    # Preserve the entire ancestry bracket, not just the numeric client PID.
    for pid, previous in processes.items():
        if previous is None:
            continue
        if now() >= deadline or reads >= 4096:
            return unknown("process_unavailable")
        reads += 1
        if proc_reader(pid) != previous:
            return unknown("process_unavailable")
    if window_signature(windows()) != opening or now() >= deadline:
        return unknown("process_unavailable")
    finished = now()
    return {
        key: Resolution(result.window, finished if result.window else None, result.reason)
        for key, result in candidates.items()
    }


class RetainedBindings:
    """One adapter-owned cache; callers serialize work and publish accepted inputs."""

    def __init__(self, *, discover=discover_clients, now=boottime_ms):
        self.discover, self.now = discover, now
        self.scope = None
        self.entries = {}
        self.discovery_jobs = self.discovery_clients = 0

    @property
    def retry_at(self):
        return min(
            (
                entry.retry_at
                for entry in self.entries.values()
                if entry.resolution.window is None and entry.attempts < 3
            ),
            default=None,
        )

    def prepare(self, host, *, context_id, epoch, deadline, force=False, enabled=True):
        if host is None or host["owner"]["publisherId"] is None:
            return None
        now = self.now()
        frame = current_attachments(host, host.get("localAttachments"), now)
        state, error = "ready", None
        if not enabled:
            state, error = (
                "unsupported",
                {"code": "unsupported_desktop", "message": "local Kitty adapter disabled"},
            )
        elif frame is None:
            state, error = (
                "unavailable",
                {
                    "code": "attachment_unverified",
                    "message": "no complete current local client sample",
                },
            )
        mappings = {}
        if state == "ready":
            scope = (
                host["hostId"],
                frame["source"]["uid"],
                frame["publisherId"],
                tuple(sorted(frame["clock"].items())),
                frame["pidNamespace"],
                frame["snapshot"]["serverGeneration"],
                context_id,
                epoch,
            )
            if scope != self.scope:
                self.scope, self.entries = scope, {}
            clients = frame["snapshot"]["clients"]
            live = {(client["clientPid"], client["processStartTicks"]) for client in clients}
            self.entries = {key: entry for key, entry in self.entries.items() if key in live}
            refs = {reference(row) for row in host["sessions"]}
            for client in clients:
                ref = reference(client["sessionRef"])
                if ref in refs:
                    mappings.setdefault(ref, []).append(
                        (client["clientPid"], client["processStartTicks"])
                    )
            wanted = {key for keys in mappings.values() for key in keys}
            due = {
                key
                for key in wanted
                if force
                or key not in self.entries
                or (
                    self.entries[key].resolution.window is None
                    and self.entries[key].attempts < 3
                    and self.entries[key].retry_at <= now
                )
            }
            if due:
                self.discovery_jobs += 1
                self.discovery_clients += len(due)
                discovered = self.discover(due, uid=frame["source"]["uid"], deadline=deadline)
                if (
                    self.now() >= deadline
                    or self.now() >= frame["receipt"]["expiresAt"]
                    or self.now() >= host["owner"]["localExpiry"]
                ):
                    # A rejected late result cannot seed a later retained positive.
                    discovered = {}
                for key in due:
                    previous = self.entries.get(key)
                    result = discovered.get(key, Resolution(None, None, "window_unresolved"))
                    self.entries[key] = Entry(
                        result,
                        1 if force or previous is None else previous.attempts + 1,
                        self.now() + 1000,
                    )
        prepared_at = self.now()
        if state == "ready" and (
            prepared_at >= deadline
            or prepared_at >= frame["receipt"]["expiresAt"]
            or prepared_at >= host["owner"]["localExpiry"]
        ):
            state, error = (
                "unavailable",
                {"code": "deadline", "message": "local binding inputs expired during preparation"},
            )
        rows = []
        for row in host["sessions"]:
            keys = mappings.get(reference(row), [])
            association = {
                "state": "unknown",
                "resolvedAt": None,
                "reason": "attachment_unverified",
            }
            if state == "ready":
                if row["attachedClients"] != len(keys):
                    association["reason"] = "attachment_count_changed"
                elif not keys:
                    association.update(state="none", reason="no_native_clients")
                else:
                    resolved = [
                        self.entries[key].resolution
                        for key in keys
                        if self.entries[key].resolution.window
                    ]
                    if resolved:
                        association.update(
                            state="open",
                            resolvedAt=min(item.resolved_at for item in resolved),
                            reason="retained_native_association",
                        )
                    else:
                        association["reason"] = self.entries[keys[0]].resolution.reason
            rows.append(
                {
                    "sessionRef": row_reference(row),
                    "attachedClients": row["attachedClients"],
                    "association": association,
                }
            )
        return validate_bindings(
            {
                "protocol": BINDINGS_PROTOCOL,
                "schemaVersion": 1,
                "clock": dict(host["owner"]["clock"]),
                "contextId": context_id,
                "epoch": epoch,
                "encodedAt": prepared_at,
                "hostId": host["hostId"],
                "publisherId": host["owner"]["publisherId"],
                "serverGeneration": host["owner"]["serverGeneration"],
                "receipt": {
                    "state": state,
                    "preparedAt": prepared_at,
                    "associationStartedAt": frame["receipt"]["startedAt"] if frame else None,
                    "ownerExpiresAt": host["owner"]["localExpiry"],
                    "associationExpiresAt": frame["receipt"]["expiresAt"] if frame else None,
                    "expiresAt": min(host["owner"]["localExpiry"], frame["receipt"]["expiresAt"])
                    if state == "ready"
                    else None,
                    "error": error,
                },
                "rows": rows,
            }
        )


def row_reference(row):
    return {key: row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")}
