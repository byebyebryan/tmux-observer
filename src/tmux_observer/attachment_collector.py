"""Optional passive native association sample; never called by desktop scans."""

import os
import time

from ._clock import boottime_ms, pid_namespace
from ._process import ProcessError
from .attachments import ATTACHMENTS_PROTOCOL, CLIENT_LIMIT, validate_attachments
from .collector import FIELDS, GENERATION, FastUnavailable, NoServer, Race, format_fields, number
from .native import validate_observation

CLIENT_FIELDS = "#{client_pid}\t#{session_id}\t#{session_created}"


def process_start(pid, uid, deadline):
    """Read one bounded process incarnation without argv, environment or contents."""
    if boottime_ms() >= deadline:
        raise ProcessError("deadline", "local process identity read exceeded deadline")
    directory = os.open(f"/proc/{pid}", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        if os.fstat(directory).st_uid != uid:
            raise ProcessError("process_scope", "native client process belongs to another UID")
        handle = os.open("stat", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory)
        try:
            raw = os.read(handle, 4097)
        finally:
            os.close(handle)
        if len(raw) > 4096:
            raise ValueError("process stat capacity")
        text = raw.decode("utf-8", "strict")
        if text.split("(", 1)[0].strip() != str(pid):
            raise ValueError("process stat PID mismatch")
        fields = text[text.rindex(")") + 2 :].split()
        if fields[0] in ("Z", "X", "x"):
            raise ValueError("native client process is not live")
        start = number(fields[19], required=True)
        if start == 0 or boottime_ms() >= deadline:
            raise ValueError("unavailable or late process incarnation")
        return start
    finally:
        os.close(directory)


class AttachmentCollector:
    """One fixed collector/source; owner scheduling supplies its absolute deadline."""

    def __init__(self, collector, *, namespace=None, process_identity=process_start):
        self.collector = collector
        self.namespace = pid_namespace() if namespace is None else namespace
        self.process_identity = process_identity

    def clients(self, references, deadline):
        native = self.collector
        rows = native.rows(
            native.read(["list-clients", "-F", CLIENT_FIELDS], deadline, absent=True), 3
        )
        return self.client_rows(rows, references)

    @staticmethod
    def client_rows(rows, references):
        if len(rows) > CLIENT_LIMIT:
            raise ProcessError("capacity", "local native client capacity exceeded")
        clients = {}
        for pid, session_id, created_at in rows:
            identifier = number(pid, required=True)
            if identifier == 0 or identifier > 2**31 - 1 or identifier in clients:
                raise ValueError("invalid or duplicate native client PID")
            ref = references.get(session_id)
            if ref is None or number(created_at, required=True) != ref["createdAt"]:
                raise Race()
            clients[identifier] = ref
        return clients

    def closing_bracket(self, references, deadline):
        """Read closing clients and full native scope with one passive process."""
        native = self.collector
        output = native.read(
            [
                "list-clients",
                "-F",
                CLIENT_FIELDS,
                ";",
                "list-sessions",
                "-F",
                format_fields((*FIELDS[:2], *GENERATION)),
            ],
            deadline,
            absent=True,
            empty=True,
        )
        client_lines, session_lines = [], []
        for line in output.splitlines():
            width = len(line.split("\t"))
            if width == 3 and not session_lines:
                client_lines.append(line)
            elif width == 5:
                session_lines.append(line)
            else:
                raise FastUnavailable()
        clients = self.client_rows(native.rows("\n".join(client_lines), 3), references)
        identities, generation = native.final_rows(
            native.rows("\n".join(session_lines), 5), deadline
        )
        return clients, identities, generation

    def sample(self, observation, deadline):
        started = boottime_ms()
        value = {
            "protocol": ATTACHMENTS_PROTOCOL,
            "schemaVersion": 1,
            "source": self.collector.source,
            "clock": self.collector.clock,
            "pidNamespace": self.namespace,
            "sample": {
                "startedAt": started,
                "finishedAt": started,
                "observedAt": time.time_ns() // 1_000_000,
                "coverage": "complete",
                "error": None,
            },
            "serverGeneration": None,
            "sessions": [],
            "clients": [],
        }
        try:
            validate_observation(observation)
            if (
                observation["sample"]["coverage"] != "complete"
                or observation["source"] != self.collector.source
                or observation["clock"] != self.collector.clock
            ):
                raise ValueError("unavailable owner basis")
            if self.namespace != pid_namespace():
                raise ValueError("PID namespace changed")
            # The accepted fixed-owner sample provides the opening generation
            # and complete reference bracket. Its start begins this conservative
            # lease; profile reads close that bracket within the same deadline.
            value["sample"]["startedAt"] = observation["sample"]["startedAt"]
            deadline = min(deadline, observation["sample"]["startedAt"] + 2000)
            if boottime_ms() >= deadline:
                raise ProcessError(
                    "deadline", "owner basis no longer fits the native sampling budget"
                )
            generation = observation["serverGeneration"]
            fast = True
            if generation is None:
                for _probe in range(2):
                    try:
                        self.collector.generation(deadline, fast)
                    except NoServer:
                        continue
                    raise Race()
            if generation is not None:
                references = {
                    row["sessionId"]: {
                        key: row[key]
                        for key in ("hostId", "serverGeneration", "sessionId", "createdAt")
                    }
                    for row in observation["sessions"]
                }
                first = self.clients(references, deadline)
                births = {
                    pid: self.process_identity(pid, self.collector.source["uid"], deadline)
                    for pid in first
                }
                try:
                    second, identities, final_generation = self.closing_bracket(
                        references, deadline
                    )
                except FastUnavailable:
                    second = self.clients(references, deadline)
                    identities, final_generation = self.collector.final_bracket(deadline, False)
                if (
                    first != second
                    or identities != {sid: ref["createdAt"] for sid, ref in references.items()}
                    or generation != final_generation
                ):
                    raise Race()
                final_births = {
                    pid: self.process_identity(pid, self.collector.source["uid"], deadline)
                    for pid in second
                }
                if births != final_births or self.namespace != pid_namespace():
                    raise Race()
                value.update(
                    serverGeneration=generation,
                    sessions=list(references.values()),
                    clients=[
                        {
                            "sessionRef": second[pid],
                            "clientPid": pid,
                            "processStartTicks": births[pid],
                        }
                        for pid in sorted(second)
                    ],
                )
            if boottime_ms() >= deadline:
                raise ProcessError("deadline", "late native association sample rejected")
        except (
            OSError,
            ValueError,
            ProcessError,
            FastUnavailable,
            NoServer,
            Race,
            IndexError,
        ) as problem:
            code = problem.code if isinstance(problem, ProcessError) else "association_unavailable"
            value.update(serverGeneration=None, sessions=[], clients=[])
            value["sample"].update(
                coverage="unsupported" if code == "tmux_missing" else "failed",
                error={"code": code, "message": "local native association sample unavailable"},
            )
        value["sample"]["finishedAt"] = boottime_ms()
        return validate_attachments(value)
