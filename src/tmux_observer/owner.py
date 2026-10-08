"""One host-local passive publisher. Subscriber operations do not collect."""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tmux_observer.delivery import SERVICE_PROTOCOL
from tmux_observer.native import OBSERVATION_PROTOCOL

from ._clock import boottime_ms
from ._hub import SocketHub
from ._ipc import owner_socket
from ._owner_state import OwnerState
from ._tickets import TicketError, TicketStore


class OwnerPublisher:
    def __init__(
        self,
        host_id,
        *,
        path=None,
        collector=None,
        local_attachments=False,
        attachment_collector=None,
        attachment_path=None,
    ):
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
        self.path = owner_socket() if path is None else Path(path)
        self.stop_event = threading.Event()
        self.hub = None
        self.future = None
        self.token = None
        if (
            type(local_attachments) is not bool
            or attachment_collector is not None
            and not local_attachments
        ):
            raise ValueError("invalid fixed local association profile")
        self.attachment_collector = None
        self.attachment_state = None
        self.attachment_hub = None
        self.attachment_future = None
        self.attachment_token = None
        self.attachment_path = (
            self.path.parent / "attachments.sock" if attachment_path is None else attachment_path
        )
        if local_attachments:
            from ._attachment_state import AttachmentState
            from .attachment_collector import AttachmentCollector

            self.attachment_collector = attachment_collector or AttachmentCollector(collector)
            if self.attachment_collector.collector is not collector:
                raise ValueError("association profile must use the fixed owner reader")
            self.attachment_state = AttachmentState(
                collector.source,
                collector.clock,
                self.attachment_collector.namespace,
                publisher_id=self.state.publisher_id,
            )

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

    def handle_attachments(self, peer, request, now):
        hub = self.attachment_hub
        if request["expectedHost"] != self.state.source["hostId"]:
            hub.error(
                peer,
                "scope_mismatch",
                "requested host differs from fixed owner",
                request_id=request["requestId"],
                close=True,
            )
            return
        hub.frame(peer, now, request_id=request["requestId"])
        peer.closing = True
        hub.interest(peer)

    def sample_attachments(self, observation, deadline):
        try:
            return self.attachment_collector.sample(observation, deadline)
        except (OSError, ValueError, AttributeError):
            now = boottime_ms()
            return {
                "protocol": "tmux-observer.attachments.v1",
                "schemaVersion": 1,
                "source": self.collector.source,
                "clock": self.collector.clock,
                "pidNamespace": self.attachment_collector.namespace,
                "sample": {
                    "startedAt": now,
                    "finishedAt": now,
                    "observedAt": time.time_ns() // 1_000_000,
                    "coverage": "failed",
                    "error": {
                        "code": "association_unavailable",
                        "message": "native association sample failed",
                    },
                },
                "serverGeneration": None,
                "sessions": [],
                "clients": [],
            }

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
            if self.attachment_state is not None:
                from .attachments import ATTACHMENT_DELIVERY_PROTOCOL, validate_attachment_request

                self.attachment_hub = SocketHub(
                    self.attachment_path,
                    protocol=ATTACHMENT_DELIVERY_PROTOCOL,
                    now=boottime_ms,
                    make_frame=self.attachment_state.frame,
                    handle_request=self.handle_attachments,
                    request_validator=validate_attachment_request,
                )
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="tmux-observer-native"
            ) as executor:
                while not self.stop_event.is_set():
                    now = boottime_ms()
                    sampled = False
                    if self.attachment_state is not None:
                        self.attachment_state.expire(now)
                    if self.attachment_future is not None and self.attachment_future.done():
                        association = self.attachment_future.result()
                        self.attachment_state.finish(
                            self.attachment_token, association, boottime_ms()
                        )
                        self.attachment_future = None
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
                        if self.attachment_state is not None:
                            # The roster is accepted/published independently before
                            # optional associations consume this same native worker.
                            self.attachment_future = executor.submit(
                                self.sample_attachments, result, self.attachment_state.job[2]
                            )
                    if (
                        self.future is None
                        and self.attachment_future is None
                        and self.state.due(now)
                    ):
                        self.token = self.state.begin(now)
                        if self.attachment_state is not None:
                            self.attachment_state.next_due = now
                            self.attachment_token = self.attachment_state.begin(now)
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
                    if self.attachment_hub is not None:
                        self.attachment_hub.poll(boottime_ms(), timeout=0)
                self.state.stop()
        finally:
            self.state.stop()
            self.hub.close()
            if self.attachment_state is not None:
                self.attachment_state.stop()
            if self.attachment_hub is not None:
                self.attachment_hub.close()

    def stop(self):
        self.stop_event.set()
