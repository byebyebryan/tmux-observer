"""One host-local passive publisher. Subscriber operations do not collect."""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from tmux_observer.delivery import SERVICE_PROTOCOL
from tmux_observer.native import OBSERVATION_PROTOCOL

from ._clock import boottime_ms
from ._hub import SocketHub
from ._ipc import owner_socket
from ._owner_state import OwnerState
from ._tickets import TicketError, TicketStore


class OwnerPublisher:
    def __init__(self, host_id, *, path=None, collector=None):
        if (
            not isinstance(host_id, str)
            or len(host_id) > 128
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", host_id)
        ):
            raise ValueError("invalid service host ID")
        if collector is None:
            from .collector import Collector

            collector = Collector(host_id)
        if collector.source["hostId"] != host_id:
            raise ValueError("collector scope differs from fixed publisher configuration")
        self.collector = collector
        self.state = OwnerState(collector.source, collector.clock)
        self.tickets = TicketStore(self.state.publisher_id)
        self.path = owner_socket() if path is None else path
        self.stop_event = threading.Event()
        self.hub = None
        self.future = None
        self.token = None

    def handle(self, peer, request, now):
        hub = self.hub
        rid = request["requestId"]
        if request["expectedHost"] != self.state.source["hostId"]:
            hub.error(
                peer,
                "scope_mismatch",
                "requested host differs from publisher configuration",
                request_id=rid,
                close=not peer.watch,
            )
            return
        if request.get("publisherId", self.state.publisher_id) != self.state.publisher_id:
            hub.error(
                peer,
                "stale_scope",
                "publisher incarnation changed",
                request_id=rid,
                close=not peer.watch,
            )
            return
        operation = request["operation"]
        if operation == "watch":
            if peer.watch:
                hub.error(peer, "invalid_request", "watch is already established", request_id=rid)
                return
            peer.watch = True
            hub.frame(peer, now, kind="resync", request_id=rid)
        elif operation in ("status", "snapshot", "probe"):
            hub.frame(
                peer, now, kind="view" if operation == "snapshot" else "status", request_id=rid
            )
            peer.closing = not peer.watch
            hub.interest(peer)
        elif operation in ("refresh", "refresh_status"):
            if not hub.can_reply(peer):
                hub.error(peer, "backpressure", "publisher reply slot is occupied", request_id=rid)
                return
            try:
                if operation == "refresh":
                    scope = (self.state.source["hostId"], "owner")
                    value = self.tickets.admit(
                        request["sources"],
                        now,
                        minimum={scope: self.state.evidence["attempted"] + 1},
                        coalesced=self.state.job is not None
                        or any(item.terminal_at is None for item in self.tickets.entries.values()),
                    )
                    self.state.hint(now)
                else:
                    value = self.tickets.lookup(request["ticketId"], now)
                hub.frame(peer, now, kind="refresh_result", request_id=rid, ticket=value)
                peer.closing = not peer.watch
                hub.interest(peer)
            except TicketError as error:
                hub.error(peer, error.code, str(error), request_id=rid, close=not peer.watch)

    def publish_tickets(self, values, now):
        for value in values:
            for peer in list(self.hub.peers):
                if peer.watch and not peer.closing:
                    self.hub.frame(peer, now, kind="refresh_result", ticket=value)

    def sample(self, job):
        _token, started, deadline = job
        try:
            remaining = deadline - boottime_ms()
            if remaining <= 0:
                raise TimeoutError()
            return self.collector.collect(budget_ms=min(2000, remaining))
        except (OSError, ValueError):
            return {
                "protocol": OBSERVATION_PROTOCOL,
                "schemaVersion": 1,
                "source": self.collector.source,
                "clock": self.collector.clock,
                "sample": {
                    "startedAt": started,
                    "finishedAt": boottime_ms(),
                    "observedAt": time.time_ns() // 1_000_000,
                    "coverage": "failed",
                    "error": {
                        "code": "collection_failed",
                        "message": "native collection did not return a supported sample",
                    },
                },
                "serverGeneration": None,
                "sessions": [],
                "capabilities": {"panes": False, "options": []},
            }

    def run(self):
        self.hub = SocketHub(
            self.path,
            protocol=SERVICE_PROTOCOL,
            now=boottime_ms,
            make_frame=self.state.frame,
            handle_request=self.handle,
            share_broadcast_body=True,
        )
        last_revision = self.state.revision
        next_heartbeat = boottime_ms() + 3000
        try:
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="tmux-observer-native"
            ) as executor:
                while not self.stop_event.is_set():
                    now = boottime_ms()
                    sampled = False
                    self.state.expire(now)
                    self.publish_tickets(self.tickets.expire(now), now)
                    if self.future is not None and self.future.done():
                        sampled = True
                        result = self.future.result()
                        now = boottime_ms()
                        accepted = self.state.finish(self.token, result, now)
                        self.publish_tickets(
                            self.tickets.finish(
                                (self.state.source["hostId"], "owner"),
                                self.token,
                                now,
                                accepted=accepted,
                                error=self.state.problem,
                            ),
                            now,
                        )
                        self.future = None
                    if self.future is None and self.state.due(now):
                        self.token = self.state.begin(now)
                        self.publish_tickets(
                            self.tickets.begin(
                                (self.state.source["hostId"], "owner"), self.token, now, now
                            ),
                            now,
                        )
                        self.future = executor.submit(self.sample, self.state.job)
                    if self.state.revision != last_revision:
                        self.hub.broadcast(now, kind="view")
                        last_revision = self.state.revision
                    elif sampled or now >= next_heartbeat:
                        self.hub.broadcast(now, kind="heartbeat")
                    if now >= next_heartbeat:
                        next_heartbeat = now + 3000
                    self.hub.poll(now)
                self.state.stop()
        finally:
            self.state.stop()
            self.hub.close()

    def stop(self):
        self.stop_event.set()
