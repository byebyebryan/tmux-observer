"""Fixed-source refresh grouping over already established owner subscriptions."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass

from tmux_observer._tickets import TERMINAL, TicketError, TicketStore
from tmux_observer.public import SERVICE_PROTOCOL

from ._errors import ContractError


@dataclass
class Child:
    parents: set
    epoch: int
    publisher: str
    request_id: str
    sent_at: int
    ticket: dict | None = None
    lookup_id: str | None = None
    lookup_at: int | None = None
    next_lookup: int = 0


class FleetTickets:
    def __init__(self, state):
        self.state = state
        self.store = TicketStore(state.reader_id)
        self.pending = {}
        self.children = {}
        self.changes = {}

    def admit(self, scopes, now, *, desktop_attempt):
        if self.state.mesh["state"] not in ("ready", "local_only"):
            raise TicketError("mesh_unavailable", "refresh requires current Mesh authority")
        for scope in scopes:
            host, source = scope["hostId"], scope["source"]
            if host not in self.state.owners or source == "desktop" and host != self.state.host_id:
                raise TicketError("scope_mismatch", "refresh source is not configured here")
        value = self.store.admit(
            scopes,
            now,
            minimum={
                (scope["hostId"], scope["source"]): desktop_attempt + 1
                if scope["source"] == "desktop"
                else 1
                for scope in scopes
            },
            coalesced=any(
                scope["hostId"] in self.children or self.pending.get(scope["hostId"])
                for scope in scopes
                if scope["source"] == "owner"
            ),
        )
        for scope in scopes:
            if scope["source"] == "owner":
                self.pending.setdefault(scope["hostId"], set()).add(value["id"])
        return value

    def take_changes(self):
        values, self.changes = self.changes, {}
        return list(values.values())

    def record(self, values):
        # Bound queued notifications to the store's 64 ticket IDs.
        self.changes.update((value["id"], value) for value in values)

    def desktop_ready(self):
        return {
            key
            for key, entry in self.store.entries.items()
            if entry.terminal_at is None
            and all(
                row["state"] in TERMINAL
                for row in entry.value["sources"]
                if row["source"] == "owner"
            )
            and any(
                row["source"] == "desktop" and row["state"] == "pending"
                for row in entry.value["sources"]
            )
        }

    def desktop_begin(self, ids, attempt, started, now):
        self.record(
            self.store.begin(
                (self.state.host_id, "desktop"),
                attempt,
                started,
                now,
                ids=ids,
            )
        )

    def desktop_finish(self, attempt, now, *, accepted=False, error=None, obsolete=False):
        scope = self.state.host_id, "desktop"
        self.record(
            self.store.requeue(scope, attempt, now)
            if obsolete
            else self.store.finish(scope, attempt, now, accepted=accepted, error=error)
        )

    def update(self, ids, host, now, *, state, attempt=None, error=None):
        self.record(
            self.store.set_source(
                ids,
                (host, "owner"),
                now,
                state=state,
                attempt=attempt,
                error=error,
            )
        )

    def fail_host(
        self,
        host,
        now,
        *,
        code="owner_unavailable",
        message="owner source unavailable",
        state="failed",
    ):
        ids = self.pending.pop(host, set())
        child = self.children.pop(host, None)
        if child is not None:
            ids |= child.parents
        self.update(ids, host, now, state=state, error={"code": code, "message": message})

    def invalidate(self, now, *, desktop_only=False):
        if not desktop_only:
            for host in set(self.pending) | set(self.children):
                self.fail_host(
                    host,
                    now,
                    code="stale_scope",
                    state="stale_scope",
                    message="fleet source scope changed",
                )
        self.record(
            self.store.set_source(
                list(self.store.entries),
                (self.state.host_id, "desktop"),
                now,
                state="stale_scope",
                error={"code": "stale_scope", "message": "desktop context changed"},
            )
        )

    def owner_lost(self, host, now):
        self.fail_host(
            host, now, code="stale_scope", state="stale_scope", message="owner subscription ended"
        )
        affected = [
            key
            for key, entry in self.store.entries.items()
            if any(
                row["hostId"] == host and row["source"] == "owner" for row in entry.value["sources"]
            )
        ]
        self.record(
            self.store.set_source(
                affected,
                (self.state.host_id, "desktop"),
                now,
                state="stale_scope",
                error={"code": "stale_scope", "message": "requested owner association ended"},
            )
        )

    def dispatch(self, host, connection, now):
        """One child per owner; later parents wait for one eligible successor."""
        if host in self.children or not self.pending.get(host):
            return
        owner = self.state.owners[host]
        if connection is None or connection.closed or owner.transport != "ready":
            self.fail_host(host, now)
            return
        ids = self.pending.pop(host)
        child = Child(ids, owner.epoch, owner.scope[0], uuid.uuid4().hex, now)
        self.children[host] = child
        self.update(ids, host, now, state="running")
        try:
            connection.send(
                {
                    "protocol": SERVICE_PROTOCOL,
                    "schemaVersion": 1,
                    "operation": "refresh",
                    "requestId": child.request_id,
                    "expectedHost": host,
                    "publisherId": child.publisher,
                    "sources": [{"hostId": host, "source": "owner"}],
                },
                now,
            )
        except (ValueError, OSError, ContractError):
            self.fail_host(
                host, now, code="backpressure", message="owner refresh could not be queued"
            )

    def operation_error(self, connection, value, now):
        """Only a known control error is handled; probe/stream errors stay fatal."""
        host = connection.state.host_id
        child = self.children.get(host)
        if child is None or value.get("requestId") not in {
            key for key in (child.request_id, child.lookup_id) if key is not None
        }:
            return False
        self.fail_host(host, now, code=value["error"]["code"], message=value["error"]["message"])
        return True

    def receive(self, connection, value, matched, now):
        host = connection.state.host_id
        child = self.children.get(host)
        if child is None:
            return
        if child.epoch != connection.state.epoch or child.publisher != value["publisherId"]:
            self.fail_host(
                host,
                now,
                code="stale_scope",
                state="stale_scope",
                message="owner subscription incarnation changed",
            )
            return
        ticket = value.get("ticket")
        acknowledgement = value["requestId"] == child.request_id
        lookup = child.lookup_id is not None and value["requestId"] == child.lookup_id
        if ticket is not None and (
            acknowledgement
            or lookup
            or child.ticket is not None
            and ticket["id"] == child.ticket["id"]
        ):
            if (
                ticket["publisherId"] != child.publisher
                or len(ticket["sources"]) != 1
                or (ticket["sources"][0]["hostId"], ticket["sources"][0]["source"])
                != (host, "owner")
                or child.ticket is not None
                and ticket["id"] != child.ticket["id"]
            ):
                self.fail_host(
                    host, now, code="invalid_refresh", message="foreign child refresh outcome"
                )
                return
            # Lost/coalesced notifications cannot roll a child back to pending.
            if child.ticket is not None:
                old = child.ticket["sources"][0]
                new = ticket["sources"][0]
                if (
                    old["state"] in TERMINAL
                    and new != old
                    or old["state"] == "running"
                    and new["state"] == "pending"
                    or old["attempt"] is not None
                    and new["attempt"] != old["attempt"]
                ):
                    self.fail_host(
                        host, now, code="invalid_refresh", message="child refresh outcome regressed"
                    )
                    return
            child.ticket = copy.deepcopy(ticket)
            if lookup:
                child.lookup_id = child.lookup_at = None
            child.next_lookup = now + 1000
        elif acknowledgement or lookup:
            self.fail_host(
                host, now, code="invalid_refresh", message="owner omitted requested refresh outcome"
            )
            return
        self.settle(host, now)

    def settle(self, host, now):
        child = self.children.get(host)
        if child is None or child.ticket is None:
            return
        row = child.ticket["sources"][0]
        if row["state"] in ("failed", "stale_scope", "deadline"):
            self.update(
                child.parents,
                host,
                now,
                state=row["state"],
                attempt=row["attempt"],
                error=row["error"],
            )
            del self.children[host]
        elif row["state"] != "complete":
            self.update(child.parents, host, now, state="running", attempt=row["attempt"])
        else:
            owner = self.state.owners[host]
            frame = owner.confirmed
            proof = owner.proof
            if (
                frame is not None
                and frame["publisherId"] == child.publisher
                and frame["receipt"]["state"] == "ready"
                and frame["receipt"]["acceptedAttempt"] >= row["attempt"]
                and owner.expiry > now
                and (
                    owner.local_clock is not None
                    or proof is not None
                    and proof["sentAt"] >= child.sent_at
                    and proof["receivedAt"] >= child.sent_at
                )
            ):
                self.update(child.parents, host, now, state="complete", attempt=row["attempt"])
                del self.children[host]
            elif owner.local_clock is None and owner.pending is None:
                owner.next_probe = min(owner.next_probe, now)

    def tick(self, connections, now):
        self.record(self.store.expire(now))
        live = {key for key, entry in self.store.entries.items() if entry.terminal_at is None}
        for host in list(self.children):
            child = self.children[host]
            child.parents &= live
            if not child.parents:
                del self.children[host]
                continue
            owner = self.state.owners.get(host)
            connection = connections.get(host)
            if (
                owner is None
                or connection is None
                or connection.closed
                or owner.transport != "ready"
                or owner.epoch != child.epoch
                or owner.scope[0] != child.publisher
            ):
                self.fail_host(
                    host,
                    now,
                    code="stale_scope",
                    state="stale_scope",
                    message="owner subscription scope became unavailable",
                )
                continue
            if (
                child.ticket is None
                and now >= child.sent_at + 2000
                or child.lookup_at is not None
                and now >= child.lookup_at + 2000
            ):
                self.fail_host(
                    host,
                    now,
                    code="deadline",
                    message="owner refresh acknowledgement exceeded its deadline",
                )
                continue
            self.settle(host, now)
            if host not in self.children:
                continue
            if (
                child.ticket is not None
                and child.ticket["state"] not in TERMINAL
                and child.lookup_id is None
                and now >= child.next_lookup
            ):
                child.lookup_id, child.lookup_at = uuid.uuid4().hex, now
                try:
                    connection.send(
                        {
                            "protocol": SERVICE_PROTOCOL,
                            "schemaVersion": 1,
                            "operation": "refresh_status",
                            "requestId": child.lookup_id,
                            "expectedHost": host,
                            "publisherId": child.publisher,
                            "ticketId": child.ticket["id"],
                        },
                        now,
                    )
                except (ValueError, OSError, ContractError):
                    self.fail_host(
                        host,
                        now,
                        code="backpressure",
                        message="owner refresh lookup could not be queued",
                    )
        for host in list(self.pending):
            self.pending[host] &= live
            if not self.pending[host]:
                del self.pending[host]
            else:
                self.dispatch(host, connections.get(host), now)
