"""Cached association input validation; no native collection or activation."""

import copy
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from tmux_observer._clock import boottime_ms, domain, pid_namespace
from tmux_observer._ipc import exchange, owner_socket
from tmux_observer._wire import validate_tree
from tmux_observer.attachments import ATTACHMENT_DELIVERY_PROTOCOL, validate_attachment_delivery

from ._errors import ContractError


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if type(value) is list:
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value):
    if type(value) is MappingProxyType:
        return {key: _thaw(child) for key, child in value.items()}
    if type(value) is tuple:
        return [_thaw(child) for child in value]
    return value


@dataclass(frozen=True, slots=True, init=False)
class _PreparedAttachments:
    """Private immutable receipt; never a wire record or a validation bypass flag."""

    frame: object
    references: frozenset

    def __init__(self, value):
        # Only exact JSON types can become trusted immutable state. Copy before
        # semantic validation so the caller retains no mutable alias.
        if not validate_tree(value):
            raise ValueError("prepared association input must be plain JSON")
        value = copy.deepcopy(value)
        validate_attachment_delivery(value)
        snapshot = value["snapshot"]
        refs = (
            frozenset(
                tuple(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
                for row in snapshot["sessions"]
            )
            if snapshot is not None
            else frozenset()
        )
        object.__setattr__(self, "frame", _freeze(value))
        object.__setattr__(self, "references", refs)

    def __getitem__(self, key):
        return self.frame[key]

    def __deepcopy__(self, memo):
        return self


def read_local_attachments(host_id, *, owner_path=None, budget_ms=250):
    path = owner_socket() if owner_path is None else Path(owner_path)
    return exchange(
        {
            "protocol": ATTACHMENT_DELIVERY_PROTOCOL,
            "schemaVersion": 1,
            "operation": "snapshot",
            "requestId": uuid.uuid4().hex,
            "expectedHost": host_id,
        },
        path=path.parent / "attachments.sock",
        budget_ms=budget_ms,
    )


def current_attachments(host, frame, now):
    if frame is None:
        return None
    prepared = type(frame) is _PreparedAttachments
    if not prepared:
        validate_attachment_delivery(frame)
    owner = host["owner"]
    snapshot = frame["snapshot"]
    if (
        not host["local"]
        or frame["source"]["hostId"] != host["hostId"]
        or frame["source"]["uid"] != os.getuid()
        or frame["clock"] != domain()
        or frame["pidNamespace"] != pid_namespace()
        or frame["publisherId"] != owner["publisherId"]
        or frame["receipt"]["state"] != "ready"
        or frame["receipt"]["expiresAt"] <= now
        or owner["localExpiry"] <= now
        or snapshot is None
        or snapshot["serverGeneration"] != owner["serverGeneration"]
    ):
        return None
    expected = {
        tuple(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
        for row in host["sessions"]
    }
    actual = (
        frame.references
        if prepared
        else {
            tuple(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
            for row in snapshot["sessions"]
        }
    )
    if not expected <= actual:
        return None
    return frame


def association_facts(host, frame, now):
    current = current_attachments(host, frame, now)
    if current is None:
        return None
    value = current["snapshot"]
    return {
        key: _thaw(value[key]) if type(current) is _PreparedAttachments else value[key]
        for key in ("source", "clock", "pidNamespace", "serverGeneration", "sessions", "clients")
    } | {"publisherId": current["publisherId"]}


class CachedClients:
    def __init__(self, hosts, deadline):
        self.hosts = [host for host in hosts if host["local"]]
        self.deadline = deadline
        self.client_incarnations = {}

    def client_pids_by_session(self):
        if not self.hosts:
            return {}
        if len(self.hosts) != 1 or boottime_ms() >= self.deadline:
            raise ContractError("operation_failed", "local association scope unavailable")
        host = self.hosts[0]
        frame = current_attachments(host, host.get("localAttachments"), boottime_ms())
        if frame is None:
            raise ContractError("operation_failed", "prepared local association unavailable")
        result = {row["sessionId"]: set() for row in host["sessions"]}
        for client in frame["snapshot"]["clients"]:
            session_id = client["sessionRef"]["sessionId"]
            if session_id in result:
                result[session_id].add(client["clientPid"])
                self.client_incarnations[client["clientPid"]] = (
                    frame["source"]["uid"],
                    client["processStartTicks"],
                )
        return result
