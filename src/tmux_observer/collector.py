"""Passive default-server metadata bracketed by generation and full references.

Adapted from Tmux Plus 0.6.0; no lifecycle code is included.
Copyright (c) 2026 Bryan Bai. SPDX-License-Identifier: MIT.
"""

from __future__ import annotations

import os
import re
import socket
import time

from tmux_observer.native import OBSERVATION_PROTOCOL, validate_observation

from ._clock import boottime_ms, domain
from ._models import Pane, Session, SessionReference
from ._process import ProcessError, ReadRunner
from ._tmux_wire import TmuxWireError, decode_tmux_argument
from .annotations import (
    PENDING,  # noqa: F401 - retained legacy constant export
    PlusPendingProfile,
)

FIELDS = (
    "session_id",
    "session_created",
    "session_name",
    "session_activity",
    "session_last_attached",
    "session_attached",
    "session_windows",
    "session_path",
    "window_name",
    "pane_current_path",
)
GENERATION = ("socket_path", "start_time", "pid")
PANES = ("session_id", "pane_id", "pane_pid", "pane_current_path", "pane_current_command")


class NoServer(Exception):
    pass


class FastUnavailable(Exception):
    pass


class Race(Exception):
    pass


def format_fields(fields):
    return "\t".join("#{q/a:" + field + "}" for field in fields)


def number(text: str, *, required: bool = False) -> int | None:
    if not text and not required:
        return None
    if not re.fullmatch(r"[0-9]+", text) or len(text) > 19 or int(text) > 2**63 - 1:
        raise ProcessError("malformed_metadata", "native numeric metadata is invalid")
    return int(text)


class Collector:
    def __init__(self, host_id: str, *, runner=None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", host_id) or len(host_id) > 16384:
            raise ValueError("invalid logical host ID")
        self.source = {
            "hostId": host_id,
            "uid": os.getuid(),
            "server": "default",
            "nativeHostname": socket.gethostname(),
        }
        self.clock = domain()
        self.runner = ReadRunner() if runner is None else runner
        self.annotation_profile = PlusPendingProfile()

    def read(self, args, deadline, *, absent=False, empty=False):
        result = self.runner(args, deadline)
        if result.returncode == 0:
            return result.stdout.removesuffix("\n")
        diagnostic = result.stderr.removesuffix("\n")
        # LC_ALL=C, exact absence classes. Permission/other connect errors fail.
        if absent and (
            re.fullmatch(r"no server running on [^\r\n]+", diagnostic)
            or re.fullmatch(
                r"error connecting to [^\r\n]+ \((No such file or directory|Connection refused)\)",
                diagnostic,
            )
        ):
            raise NoServer()
        if empty and diagnostic == "no sessions":
            return ""
        raise ProcessError("collection_failed", "native metadata read failed")

    @staticmethod
    def rows(text, count):
        result = []
        for line in text.split("\n") if text else ():
            parts = line.split("\t")
            if len(parts) != count:
                raise FastUnavailable()
            try:
                result.append(tuple(decode_tmux_argument(part) for part in parts))
            except TmuxWireError as error:
                raise FastUnavailable() from error
        return result

    def generation(self, deadline, fast):
        if fast:
            rows = self.rows(
                self.read(
                    ["display-message", "-p", format_fields(GENERATION)], deadline, absent=True
                ),
                3,
            )
            if len(rows) != 1:
                raise FastUnavailable()
            return self.fast_generation(rows[0])
        else:
            path, start, pid = (
                self.field(None, field, deadline, absent=True) for field in GENERATION
            )
            if not path:
                raise ProcessError("malformed_metadata", "missing native server identity")
        number(start, required=True)
        number(pid, required=True)
        return f"tmux-v1:{start}:{pid}:{path}"

    @staticmethod
    def fast_generation(fields):
        path, start, pid = fields
        if not path or not start.isdecimal() or not pid.isdecimal():
            raise FastUnavailable()
        number(start, required=True)
        number(pid, required=True)
        return f"tmux-v1:{start}:{pid}:{path}"

    def field(self, target, name, deadline, *, absent=False):
        args = ["display-message", "-p"]
        if target is not None:
            args.extend(["-t", target])
        return self.read([*args, "#{" + name + "}"], deadline, absent=absent)

    def table(self, deadline, fast):
        if fast:
            rows = self.rows(
                self.read(
                    ["list-sessions", "-F", format_fields(FIELDS)],
                    deadline,
                    absent=True,
                    empty=True,
                ),
                len(FIELDS),
            )
        else:
            ids = self.read(
                ["list-sessions", "-F", "#{session_id}"], deadline, absent=True, empty=True
            ).splitlines()
            self.identities([(sid, "0") for sid in ids])
            rows = [(sid, *(self.field(sid, name, deadline) for name in FIELDS[1:])) for sid in ids]
        self.identities(rows)
        return rows

    def opening_bracket(self, deadline, fast):
        if not fast:
            return self.generation(deadline, False), self.table(deadline, False)
        output = self.read(
            [
                "display-message",
                "-p",
                format_fields(GENERATION),
                ";",
                "list-sessions",
                "-F",
                format_fields(FIELDS),
            ],
            deadline,
            absent=True,
            empty=True,
        )
        if not output:
            # Some native versions return `no sessions` for a live empty
            # server; retain its independent generation and empty roster read.
            return self.generation(deadline, True), self.table(deadline, True)
        opening, separator, table = output.partition("\n")
        generations = self.rows(opening, 3)
        if len(generations) != 1:
            raise FastUnavailable()
        generation = self.fast_generation(generations[0])
        rows = self.rows(table if separator else "", len(FIELDS))
        self.identities(rows)
        return generation, rows

    @staticmethod
    def identities(rows):
        if len(rows) > 256:
            raise ProcessError("capacity", "native session capacity exceeded")
        result = {}
        for row in rows:
            sid, created = row[:2]
            if not re.fullmatch(r"\$[0-9]+", sid) or sid in result:
                raise ProcessError("malformed_metadata", "native session identity is invalid")
            result[sid] = number(created, required=True)
        return result

    def final_bracket(self, deadline, fast):
        if fast:
            rows = self.rows(
                self.read(
                    ["list-sessions", "-F", format_fields((*FIELDS[:2], *GENERATION))],
                    deadline,
                    absent=True,
                    empty=True,
                ),
                5,
            )
            return self.final_rows(rows, deadline)
        else:
            ids = self.read(
                ["list-sessions", "-F", "#{session_id}"], deadline, absent=True, empty=True
            ).splitlines()
            self.identities([(sid, "0") for sid in ids])
            rows = [(sid, self.field(sid, "session_created", deadline)) for sid in ids]
        return self.identities(rows), self.generation(deadline, False)

    def final_rows(self, rows, deadline):
        identities = self.identities(rows)
        if not rows:
            # A live empty server still requires its own generation probe.
            return identities, self.generation(deadline, True)
        generations = {self.fast_generation(row[2:]) for row in rows}
        if len(generations) != 1:
            raise Race()
        return identities, generations.pop()

    def options(self, sid, names, deadline):
        return self.annotation_profile.sample(self.read, sid, names, deadline)

    def panes(self, ids, deadline, fast):
        result = {sid: [] for sid in ids}
        if fast:
            rows = self.rows(
                self.read(["list-panes", "-a", "-F", format_fields(PANES)], deadline, absent=True),
                5,
            )
        else:
            rows = []
            for sid in ids:
                pane_ids = self.read(
                    ["list-panes", "-t", sid, "-F", "#{pane_id}"], deadline, absent=True
                ).splitlines()
                if len(pane_ids) > 512 or any(
                    not re.fullmatch(r"%[0-9]+", pid) for pid in pane_ids
                ):
                    raise ProcessError("malformed_metadata", "native pane identity is invalid")
                rows.extend(
                    (sid, pid, *(self.field(pid, field, deadline) for field in PANES[2:]))
                    for pid in pane_ids
                )
        seen = set()
        if len(rows) > 512:
            raise ProcessError("capacity", "native pane capacity exceeded")
        for sid, pane_id, pid, path, command in rows:
            if sid not in result or pane_id in seen or not re.fullmatch(r"%[0-9]+", pane_id):
                raise Race()
            seen.add(pane_id)
            result[sid].append(Pane(pane_id, number(pid), path or None, command or None))
        return result

    def batch(self, deadline, fast, with_panes, names):
        try:
            generation, rows = self.opening_bracket(deadline, fast)
        except NoServer:
            try:
                self.generation(deadline, fast)
            except NoServer:
                return None, []
            raise Race()
        try:
            identities = self.identities(rows)
            if (
                fast
                and not names
                and not with_panes
                and type(self.annotation_profile) is PlusPendingProfile
            ):
                options, closing = self.annotation_profile.sample_pending_and_closing(
                    self.read,
                    identities,
                    deadline,
                    ["list-sessions", "-F", format_fields((*FIELDS[:2], *GENERATION))],
                )
                final_ids, final_generation = self.final_rows(self.rows(closing, 5), deadline)
                panes = {sid: [] for sid in identities}
            else:
                options = (
                    {sid: self.options(sid, names, deadline) for sid in identities}
                    if names
                    else self.annotation_profile.sample_pending(self.read, identities, deadline)
                )
                panes = (
                    self.panes(identities, deadline, fast)
                    if with_panes and rows
                    else {sid: [] for sid in identities}
                )
                final_ids, final_generation = self.final_bracket(deadline, fast)
        except NoServer as error:
            raise Race() from error
        if generation != final_generation or identities != final_ids:
            raise Race()
        sessions = []
        for (
            sid,
            created,
            name,
            activity,
            attached_at,
            attached,
            windows,
            path,
            window,
            current,
        ) in rows:
            pending, selected = options[sid]
            sessions.append(
                Session(
                    SessionReference(
                        self.source["hostId"], generation, sid, number(created, required=True)
                    ),
                    name or None,
                    number(activity),
                    number(attached_at),
                    number(attached),
                    pending,
                    number(windows),
                    path or None,
                    window or None,
                    current or None,
                    tuple(panes[sid]) if with_panes else None,
                    selected if names else None,
                ).as_dict()
            )
        return generation, sessions

    def collect(self, *, panes=False, option_names=(), budget_ms=2000):
        if type(panes) is not bool or type(budget_ms) is not int or not 1 <= budget_ms <= 2000:
            raise ValueError("invalid collection profile or budget")
        names = tuple(dict.fromkeys(option_names))
        if any(
            not isinstance(name, str)
            or not re.fullmatch(r"@[A-Za-z0-9_.-]+", name)
            or len(name) > 16384
            for name in names
        ):
            raise ValueError("invalid requested user option")
        started = boottime_ms()
        deadline = started + budget_ms
        generation, sessions, coverage, issue = None, [], "complete", None
        fast = True
        try:
            for attempt in range(2):
                try:
                    try:
                        generation, sessions = self.batch(deadline, fast, panes, names)
                    except FastUnavailable:
                        fast = False
                        generation, sessions = self.batch(deadline, fast, panes, names)
                    break
                except Race:
                    if attempt:
                        raise ProcessError(
                            "unstable_source", "native identity changed during collection"
                        ) from None
            if boottime_ms() >= deadline:
                raise ProcessError("deadline", "late native sample rejected")
        except (ProcessError, FastUnavailable) as error:
            code = error.code if isinstance(error, ProcessError) else "malformed_metadata"
            coverage = "unsupported" if code == "tmux_missing" else "failed"
            issue = {"code": code, "message": str(error) or "native metadata is invalid"}
            generation, sessions = None, []
        value = {
            "protocol": OBSERVATION_PROTOCOL,
            "schemaVersion": 1,
            "source": self.source,
            "clock": self.clock,
            "sample": {
                "startedAt": started,
                "finishedAt": boottime_ms(),
                "observedAt": time.time_ns() // 1_000_000,
                "coverage": coverage,
                "error": issue,
            },
            "serverGeneration": generation,
            "sessions": sessions,
            "capabilities": {"panes": panes, "options": list(names)},
        }
        try:
            return validate_observation(value)
        except ValueError:
            value.update(serverGeneration=None, sessions=[])
            value["sample"].update(
                coverage="failed",
                error={
                    "code": "malformed_metadata",
                    "message": "native metadata violates the observation boundary",
                },
            )
            return validate_observation(value)
