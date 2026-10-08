"""Independent endpoint-local observations with exact native client joins."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from tmux_observer._clock import boottime_ms
from tmux_observer._process import ProcessError
from tmux_observer.collector import Collector, FastUnavailable, NoServer
from tmux_observer.public import Session, SessionReference, encode_document

from ._desktop_scan import DesktopConfig, ViewerTarget, _niri_windows, observe_local_viewers
from ._errors import ContractError


def context_fingerprint(context_id):
    path = os.environ.get("NIRI_SOCKET", "")
    try:
        stat = Path(path).stat() if path else None
        identity = (stat.st_dev, stat.st_ino) if stat else None
    except OSError:
        identity = None
    return context_id, path, identity


def reference(row):
    return SessionReference(
        *(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
    )


def input_hash(hosts):
    values = [
        {
            "hostId": host["hostId"],
            "local": host["local"],
            "publisherId": host["owner"]["publisherId"],
            "clock": host["owner"]["clock"],
            "route": host.get("route"),
            "sessions": [
                {
                    key: row[key]
                    for key in (
                        "hostId",
                        "serverGeneration",
                        "sessionId",
                        "createdAt",
                        "name",
                        "attachedClients",
                        "pending",
                    )
                }
                for row in host["sessions"]
            ],
        }
        for host in hosts
    ]
    return "sha256:" + hashlib.sha256(encode_document(values, limit=16 * 1048576)).hexdigest()


class LocalClients:
    def __init__(self, targets, deadline, *, collector=None):
        self.targets = [target for target in targets if target.local_owner]
        self.deadline = deadline
        self.collector = collector

    def client_pids_by_session(self):
        if not self.targets:
            return {}
        collector = self.collector or Collector(self.targets[0].session.reference.host_id)
        expected = {
            target.session.reference.session_id: target.session.reference for target in self.targets
        }
        generations = {item.server_generation for item in expected.values()}
        try:
            try:
                generation = collector.generation(self.deadline, True)
            except FastUnavailable:
                generation = collector.generation(self.deadline, False)
            if generations != {generation}:
                raise ValueError("owner generation differs from desktop native join")
            rows = collector.rows(
                collector.read(
                    [
                        "list-clients",
                        "-F",
                        "#{client_pid}\t#{session_id}\t#{session_created}",
                    ],
                    self.deadline,
                ),
                3,
            )
            result = {key: set() for key in expected}
            seen = set()
            if len(rows) > 512:
                raise ValueError("desktop client capacity exceeded")
            for pid, session_id, created in rows:
                if (
                    not pid.isascii()
                    or not pid.isdecimal()
                    or not created.isascii()
                    or not created.isdecimal()
                    or re.fullmatch(r"\$[0-9]+", session_id) is None
                ):
                    raise ValueError("invalid native client join")
                native_pid = int(pid)
                if native_pid <= 0 or native_pid > 2**31 - 1 or native_pid in seen:
                    raise ValueError("duplicate or invalid native client PID")
                seen.add(native_pid)
                if session_id in expected:
                    if int(created) != expected[session_id].created_at:
                        raise ValueError("created-at conflict in desktop native join")
                    result[session_id].add(native_pid)
            if (
                collector.generation(self.deadline, False) != generation
                or boottime_ms() >= self.deadline
            ):
                raise ValueError("native desktop join changed or exceeded its deadline")
            return result
        except (ProcessError, FastUnavailable, NoServer, ValueError) as error:
            raise ContractError("operation_failed", "local attachment join unavailable") from error


def scan(hosts, *, deadline, config=None):
    config = DesktopConfig() if config is None else config
    targets = []
    for host in hosts:
        for row in host["sessions"]:
            session = Session(
                reference(row),
                row["name"],
                row["activityAt"],
                row["lastAttachedAt"],
                row["attachedClients"],
                row["pending"],
                row["windowCount"],
                row["sessionPath"],
                row["currentWindow"],
                row["currentPath"],
            )
            targets.append(
                ViewerTarget(
                    session,
                    host["local"],
                    host["owner"]["source"]["nativeHostname"],
                    host.get("route"),
                    host.get("remoteExecutable", "ssh"),
                )
            )
    if not os.environ.get("NIRI_SOCKET"):
        return (
            "unsupported",
            {},
            {
                "code": "unsupported_desktop",
                "message": "desktop context has no compositor endpoint",
            },
        )
    if not targets:
        windows = _niri_windows(
            ("niri",), timeout_seconds=max(0.001, min(1, (deadline - boottime_ms()) / 1000))
        )
        if windows is None or boottime_ms() >= deadline:
            return (
                "failed",
                {},
                {
                    "code": "compositor_unavailable",
                    "message": "empty desktop input still requires a compositor read",
                },
            )
        return "ready", {}, None
    batch = observe_local_viewers(
        targets, config, local_tmux=LocalClients(targets, deadline), deadline=deadline / 1000
    )
    if boottime_ms() >= deadline:
        return (
            "failed",
            {},
            {"code": "deadline", "message": "desktop scan exceeded its start-based budget"},
        )
    observations = {
        key: {"reason": None, **value.as_dict()} for key, value in batch.observations.items()
    }
    if observations and all(
        value["reason"] == "compositor_unavailable" for value in observations.values()
    ):
        return (
            "failed",
            {},
            {"code": "compositor_unavailable", "message": "desktop compositor could not be read"},
        )
    return "ready", observations, None
