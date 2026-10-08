"""Bounded refresh outcomes. Admission and lookup never execute a source."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass

from ._validation import ticket as validate_ticket
from .public import encode_document

TERMINAL = frozenset(("complete", "failed", "stale_scope", "deadline"))
RETENTION_MS = 600000


class TicketError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass
class Entry:
    value: dict
    minimum: dict
    terminal_at: int | None = None


class TicketStore:
    def __init__(self, publisher_id):
        self.publisher_id = publisher_id
        self.entries = {}

    def purge(self, now):
        self.entries = {
            key: entry
            for key, entry in self.entries.items()
            if entry.terminal_at is None or now - entry.terminal_at < RETENTION_MS
        }

    def admit(self, scopes, now, *, minimum, coalesced=False):
        self.purge(now)
        value = {
            "id": str(uuid.uuid4()),
            "publisherId": self.publisher_id,
            "state": "coalesced" if coalesced else "accepted",
            "requestedAt": now,
            "deadlineAt": now + 15000,
            "sources": [
                {**scope, "state": "pending", "attempt": None, "error": None} for scope in scopes
            ],
        }
        validate_ticket(value)
        raw = encode_document(value, limit=16384)
        if (
            len(self.entries) >= 64
            or sum(len(encode_document(e.value)) for e in self.entries.values()) + len(raw)
            > 1048576
        ):
            raise TicketError("capacity", "refresh ticket capacity exceeded")
        self.entries[value["id"]] = Entry(value, dict(minimum))
        return copy.deepcopy(value)

    def lookup(self, ticket_id, now):
        self.purge(now)
        if ticket_id not in self.entries:
            raise TicketError("ticket_not_found", "refresh ticket is unknown or no longer retained")
        return copy.deepcopy(self.entries[ticket_id].value)

    def update_state(self, entry, now):
        value = entry.value
        states = [row["state"] for row in value["sources"]]
        if all(state == "complete" for state in states):
            value["state"] = "complete"
        elif all(state in TERMINAL for state in states):
            value["state"] = (
                "deadline" if all(state == "deadline" for state in states) else "failed"
            )
        elif any(state == "running" for state in states):
            value["state"] = "running"
        if value["state"] in TERMINAL:
            entry.terminal_at = now
        validate_ticket(value)

    def begin(self, scope, attempt, started, now):
        self.expire(now)
        changed = []
        for entry in self.entries.values():
            if entry.terminal_at is not None or started < entry.value["requestedAt"]:
                continue
            for row in entry.value["sources"]:
                key = (row["hostId"], row["source"])
                if key == scope and row["state"] == "pending" and attempt >= entry.minimum[key]:
                    row.update(state="running", attempt=attempt)
                    self.update_state(entry, now)
                    changed.append(copy.deepcopy(entry.value))
        return changed

    def finish(self, scope, attempt, now, *, accepted, error=None):
        changed = self.expire(now)
        for entry in self.entries.values():
            if entry.terminal_at is not None:
                continue
            for row in entry.value["sources"]:
                if (
                    (row["hostId"], row["source"]) == scope
                    and row["state"] == "running"
                    and row["attempt"] == attempt
                ):
                    row.update(
                        state="complete" if accepted else "failed",
                        error=None
                        if accepted
                        else copy.deepcopy(
                            error
                            or {
                                "code": "collection_failed",
                                "message": "requested native attempt failed",
                            }
                        ),
                    )
                    self.update_state(entry, now)
                    changed.append(copy.deepcopy(entry.value))
        return changed

    def expire(self, now):
        self.purge(now)
        changed = []
        for entry in self.entries.values():
            if entry.terminal_at is None and now >= entry.value["deadlineAt"]:
                for row in entry.value["sources"]:
                    if row["state"] not in TERMINAL:
                        row.update(
                            state="deadline",
                            error={
                                "code": "deadline",
                                "message": "refresh source exceeded its deadline",
                            },
                        )
                self.update_state(entry, now)
                changed.append(copy.deepcopy(entry.value))
        return changed
