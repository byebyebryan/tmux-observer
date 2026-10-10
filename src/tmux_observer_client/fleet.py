"""Prepared per-desktop aggregation; reads never schedule native collection."""

from __future__ import annotations

import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from tmux_observer._clock import boottime_ms, domain
from tmux_observer._hub import SocketHub
from tmux_observer._ipc import IPCError
from tmux_observer._tickets import TicketError
from tmux_observer_client.contract import FLEET_PROTOCOL

from ._binding_projection import project_bindings
from ._desktop_context import context_fingerprint
from ._errors import ContractError
from ._fleet_state import FleetState
from ._fleet_tickets import FleetTickets
from ._local_stream import LocalConnection
from ._owner_document import OwnerDocument
from .attachments import read_local_attachments
from .direct import REMOTE_EXEC
from .mesh import HostMeshAdapter
from .public import desktop_context_id, fleet_socket
from .ssh import RemoteConnection

POOL_LIMIT = 16 * 1048576


@dataclass
class Retry:
    next_at: int = 0
    failures: int = 0
    route: int = 0


@dataclass
class DesktopJob:
    attempt: int
    epoch: int
    key: str
    parents: set
    hosts: list
    started: list = field(default_factory=list)
    begun: bool = False
    binding_key: tuple | None = None
    binding_epoch: int = 0


class FleetPublisher:
    def __init__(
        self,
        host_id,
        *,
        context_id=None,
        path=None,
        mesh=None,
        owner_path=None,
        remote_exec=REMOTE_EXEC,
        scanner=None,
        fingerprint=context_fingerprint,
        local_connection=LocalConnection,
        remote_connection=RemoteConnection,
    ):
        context = desktop_context_id()
        if context_id is not None and context_id != context:
            raise ValueError("fleet context differs from captured startup environment")
        self.state = FleetState(host_id, context, domain())
        self.path = fleet_socket(context) if path is None else path
        self.mesh = HostMeshAdapter() if mesh is None else mesh
        self.owner_path = owner_path
        self.remote_exec = remote_exec
        self.desktop_enabled = scanner is not False and bool(os.environ.get("NIRI_SOCKET"))
        self.profile_enabled = scanner is None and self.desktop_enabled
        if scanner is None:
            # Import the optional implementation only for a captured desktop.
            if self.desktop_enabled:
                from .desktop import scan

                scanner = scan
            else:
                scanner = lambda _hosts, **_kw: (
                    "unsupported",
                    {},
                    {"code": "unsupported_desktop", "message": "desktop adapter is disabled"},
                )
        elif scanner is False:
            scanner = lambda _hosts, **_kw: (
                "unsupported",
                {},
                {"code": "unsupported_desktop", "message": "desktop adapter is disabled"},
            )
        self.scanner, self.fingerprint = scanner, fingerprint
        self.attachment_future = None
        self.binding_adapter = None
        if self.profile_enabled:
            from ._local_bindings import RetainedBindings

            self.binding_adapter = RetainedBindings()
        self.binding_future = self.binding_job = None
        self.binding_dependencies = None
        self.cached_binding_key = self.cached_binding_dependencies = None
        self.binding_expiry = None
        self.last_binding_start = 0
        self.next_attachment = 0
        self.local_connection, self.remote_connection = local_connection, remote_connection
        self.tickets = FleetTickets(self.state)
        self.stop_event = threading.Event()
        self.hub = None
        self.snapshot = None
        self.connections = {}
        self.retries = {}
        self.retained = {}
        self.capacity = False
        self.catalog_future = self.report_future = self.desktop_future = None
        self.reports = {}
        self.report_revision = None
        self.next_mesh = 0
        self.desktop_attempt = 0
        self.desktop_job = None
        self.next_desktop = self.last_desktop_start = 0
        self.desktop_input = None
        self.context_fingerprint = fingerprint(context)
        self.projection_dirty = True
        self.projection_expiry = None
        self.publish_needed = False
        self.input_key_dirty = True
        self.cached_input_key = None
        self.cached_input_dependencies = None
        self.prepared_view = None
        self.prepared_dependencies = None
        self.input_expiry = None
        self.attachment_value = self.attachment_facts = None
        self.attachment_revision = 0
        self.binding_value = self.binding_facts = None
        self.binding_revision = 0

    def handle(self, peer, request, now):
        rid = request["requestId"]
        if (
            request["contextId"] != self.state.context_id
            or request.get("expectedHost", self.state.host_id) != self.state.host_id
        ):
            self.hub.error(
                peer,
                "scope_mismatch",
                "requested fleet context or local host differs",
                request_id=rid,
                close=not peer.watch,
            )
            return
        if request.get("publisherId", self.state.reader_id) != self.state.reader_id:
            self.hub.error(
                peer,
                "stale_scope",
                "fleet reader incarnation changed",
                request_id=rid,
                close=not peer.watch,
            )
            return
        operation = request["operation"]
        if operation == "watch":
            if peer.watch:
                self.hub.error(
                    peer, "invalid_request", "watch is already established", request_id=rid
                )
                return
            peer.watch = True
            self.hub.frame(peer, now, kind="resync", request_id=rid)
        elif operation in ("status", "snapshot", "probe"):
            self.hub.frame(
                peer, now, kind="view" if operation == "snapshot" else "status", request_id=rid
            )
            peer.closing = not peer.watch
            self.hub.interest(peer)
        elif operation in ("refresh", "refresh_status"):
            if not self.hub.can_reply(peer):
                self.hub.error(peer, "backpressure", "fleet reply slot is occupied", request_id=rid)
                return
            try:
                value = (
                    self.tickets.admit(
                        request["sources"], now, desktop_attempt=self.desktop_attempt
                    )
                    if operation == "refresh"
                    else self.tickets.store.lookup(request["ticketId"], now)
                )
                self.hub.frame(peer, now, kind="refresh_result", request_id=rid, ticket=value)
                peer.closing = not peer.watch
                self.hub.interest(peer)
            except TicketError as error:
                self.hub.error(peer, error.code, str(error), request_id=rid, close=not peer.watch)

    def mark_changed(self):
        self.projection_dirty = True

    def attachment_dependencies(self, now):
        value = self.state.attachments
        if value is not self.attachment_value:
            snapshot = value["snapshot"] if value is not None else None
            facts = (
                None
                if value is None
                else (
                    *(value[key] for key in ("source", "clock", "publisherId", "pidNamespace")),
                    None
                    if snapshot is None
                    else tuple(
                        snapshot[key]
                        for key in (
                            "source",
                            "clock",
                            "pidNamespace",
                            "serverGeneration",
                            "sessions",
                            "clients",
                        )
                    ),
                )
            )
            self.attachment_revision += facts != self.attachment_facts
            self.attachment_value, self.attachment_facts = value, facts
        current = (
            value is not None
            and value["receipt"]["state"] == "ready"
            and value["receipt"]["expiresAt"] > now
        )
        return self.attachment_revision, current

    def binding_dependencies_for_projection(self, now):
        value = self.state.bindings
        if value is not self.binding_value:
            facts = (
                None
                if value is None
                else (
                    value["epoch"],
                    value["rows"],
                    value["receipt"]["state"],
                    value["receipt"]["error"],
                )
            )
            self.binding_revision += facts != self.binding_facts
            self.binding_value, self.binding_facts = value, facts
        current = (
            value is not None
            and value["receipt"]["state"] == "ready"
            and value["receipt"]["expiresAt"] > now
        )
        return self.binding_revision, current

    @staticmethod
    def owner_current(owner, now):
        return (
            owner.confirmed is not None
            and owner.confirmed["receipt"]["state"] == "ready"
            and owner.expiry > now
        )

    def input_dependencies(self, now):
        return (
            tuple(self.state.mesh.items()),
            id(self.state.descriptions),
            self.attachment_dependencies(now),
            tuple(
                (
                    host,
                    owner.epoch,
                    owner.input_revision,
                    self.owner_current(owner, now),
                    owner.transport,
                    getattr(owner, "selected_route", None),
                )
                for host, owner in self.state.owners.items()
            ),
        )

    def current_input_key(self, now):
        dependencies = self.input_dependencies(now)
        if self.input_key_dirty or dependencies != self.cached_input_dependencies:
            self.cached_input_key = self.state.input_key(now)
            self.cached_input_dependencies = dependencies
            self.input_key_dirty = False
            self.input_expiry = min(
                (owner.expiry for owner in self.state.owners.values() if owner.expiry > now),
                default=None,
            )
            attachment = self.state.attachments
            if attachment is not None and attachment["receipt"]["state"] == "ready":
                expiry = attachment["receipt"]["expiresAt"]
                if expiry > now:
                    self.input_expiry = min(self.input_expiry or expiry, expiry)
        return self.cached_input_key

    def project_changed(self, now):
        input_key = self.current_input_key(now)
        binding_key = self.current_binding_key(now)
        dependencies = (
            tuple(self.state.mesh.items()),
            id(self.state.descriptions),
            self.state.error,
            tuple(
                self.state.desktop[key]
                for key in ("contextId", "epoch", "state", "inputHash", "error")
            ),
            self.state.desktop["state"] == "ready" and self.state.desktop["expiresAt"] > now,
            id(self.state.viewers),
            input_key,
            binding_key,
            self.state.bindings_key,
            self.binding_dependencies_for_projection(now),
            self.state.binding_epoch,
            tuple(
                (
                    host,
                    owner.epoch,
                    owner.fact_revision,
                    self.owner_current(owner, now),
                    owner.transport,
                    owner.error,
                    getattr(owner, "selected_route", None),
                )
                for host, owner in self.state.owners.items()
            ),
        )
        if dependencies == self.prepared_dependencies:
            if self.projection_dirty:
                # Checked receipts move leases and health metadata, not facts.
                # Outgoing frames still validate the complete owned projection.
                for host in self.prepared_view["hosts"]:
                    owner = self.state.owners[host["hostId"]]
                    host["owner"] = owner.project_header()
                    if self.state.mesh["state"] not in ("ready", "local_only"):
                        host["owner"]["localExpiry"] = 0
                    if host["local"] and self.state.bindings is not None:
                        projected = project_bindings(
                            self.state.bindings,
                            accepted_key=self.state.bindings_key,
                            current_key=binding_key,
                            now=now,
                        )
                        if projected is not None:
                            host["localBindings"] = projected
                        else:
                            host.pop("localBindings", None)
                desktop = self.prepared_view["desktop"]
                for key in ("startedAt", "acceptedAt", "expiresAt"):
                    desktop[key] = self.state.desktop[key]
                self.update_expiries(now)
                self.projection_dirty = False
            return
        # Only validated input/health changes or an actual lease boundary need
        # the full projection/hash. Reads still render and validate at their now.
        view = self.state.view(now, _input_key=input_key, _binding_key=binding_key)
        self.publish_needed |= self.state.material(now, _view=view)
        self.prepared_view = view
        self.prepared_dependencies = dependencies
        self.projection_dirty = False
        self.update_expiries(now)

    def update_expiries(self, now):
        expiries = [owner.expiry for owner in self.state.owners.values() if owner.expiry > now]
        if self.state.attachments is not None:
            expiry = self.state.attachments["receipt"]["expiresAt"]
            if expiry is not None and expiry > now:
                expiries.append(expiry)
        desktop = self.state.desktop
        if desktop["state"] == "ready" and desktop["expiresAt"] > now:
            expiries.append(desktop["expiresAt"])
        if self.state.bindings is not None:
            expiry = self.state.bindings["receipt"]["expiresAt"]
            if expiry is not None and expiry > now:
                expiries.append(expiry)
        self.projection_expiry = min(expiries, default=None)

    def current_binding_key(self, now):
        if self.binding_adapter is None:
            return None
        owner = self.state.owners.get(self.state.host_id)
        dependencies = (
            tuple(self.state.mesh.items()),
            self.attachment_dependencies(now),
            self.state.binding_epoch,
            None
            if owner is None
            else (
                owner.epoch,
                owner.input_revision,
                self.owner_current(owner, now),
                owner.transport,
                owner.error,
            ),
        )
        if dependencies != self.cached_binding_dependencies:
            self.cached_binding_key = self.state.binding_key(now)
            self.cached_binding_dependencies = dependencies
            expiries = [owner.expiry] if owner is not None and owner.expiry > now else []
            if self.state.attachments is not None:
                expiry = self.state.attachments["receipt"]["expiresAt"]
                if expiry is not None and expiry > now:
                    expiries.append(expiry)
            self.binding_expiry = min(expiries, default=None)
        return self.cached_binding_key

    def frame(self, now, **kwargs):
        self.project_changed(now)
        return self.state.frame(now, _view=self.prepared_view, **kwargs)

    def disconnect(self, now, *, remotes_only=False, code="stale_scope"):
        self.mark_changed()
        for host, connection in list(self.connections.items()):
            if remotes_only and connection.state.local_clock is not None:
                continue
            connection.fail(code, "fleet association was replaced")
            self.tickets.fail_host(
                host, now, code=code, state="stale_scope", message="owner association was replaced"
            )
            del self.connections[host]
        self.retries = {}

    def catalog_failure(self, now, code, message):
        self.mark_changed()
        self.state.catalog_error(code, message)
        self.tickets.invalidate(now)
        self.disconnect(now)
        self.reports.clear()

    def catalog_result(self, result, now):
        self.mark_changed()
        started, finished, snapshot, error = result
        if not started <= finished <= now < started + 5000:
            error = {"code": "deadline", "message": "Mesh recheck exceeded its actual-start budget"}
        if error is not None:
            self.catalog_failure(now, error["code"], error["message"])
            return
        previous = self.state.mesh.copy(), self.state.catalog_identity
        if not self.state.catalog(snapshot):
            self.tickets.invalidate(now)
            self.disconnect(now)
            return
        if previous != (self.state.mesh, self.state.catalog_identity):
            self.tickets.invalidate(now)
            self.disconnect(now)
            self.reports.clear()
        self.snapshot = snapshot
        self.retained = {
            host: size for host, size in self.retained.items() if host in self.state.owners
        }

    def load_catalog(self):
        started = boottime_ms()
        try:
            snapshot, error = self.mesh.load(timeout_seconds=5), None
        except (ContractError, OSError, ValueError):
            snapshot, error = (
                None,
                {"code": "mesh_unavailable", "message": "present Mesh provider recheck failed"},
            )
        return started, boottime_ms(), snapshot, error

    def before_input(self, connection, value, now):
        document = value if isinstance(value, OwnerDocument) else OwnerDocument(value)
        value = document.value
        owner = connection.state
        header_size = document.header_size
        will_confirm = (
            owner.local_clock is not None
            or value["receipt"]["state"] != "ready"
            or owner.pending is not None
            and value["requestId"] == owner.pending["requestId"]
        )
        full_size = document.full_size if will_confirm else owner.confirmed_size
        if (
            sum(size for host, size in self.retained.items() if host != owner.host_id)
            + header_size
            + full_size
            > POOL_LIMIT
        ):
            self.capacity = True
            raise ContractError("capacity", "retained owner document pool exceeded its bound")
        return document

    def owner_frame(self, connection, value, matched, now):
        self.mark_changed()
        owner = connection.state
        self.retained[owner.host_id] = owner.confirmed_size + owner.candidate_size
        self.tickets.receive(connection, value, matched, now)

    def queue_report(self, connection, now, status):
        if self.snapshot is None:
            return
        # One latest route outcome per configured host; no subscriber multiplication.
        self.reports[connection.state.host_id] = {
            "host_id": connection.state.host_id,
            "route": connection.route.destination,
            "status": status,
            "mesh_revision": self.snapshot.revision,
            "observed_at": time.time_ns() // 1000000,
        }
        connection.reached_reported = True
        connection.next_report_at = now + max(
            1000, self.snapshot.policy.route_health_ttl_seconds * 500
        )

    def report(self, value):
        try:
            self.mesh.report_route(**value, timeout_seconds=2)
            return None
        except ContractError as error:
            return error.code
        except (OSError, ValueError):
            return "operation_failed"

    def report_tick(self, executor, now):
        if self.report_future is not None and self.report_future.done():
            error = self.report_future.result()
            self.report_future = None
            relevant = self.report_revision == self.state.mesh["revision"]
            if relevant and error == "stale_mesh":
                self.catalog_failure(now, "stale_mesh", "Mesh revision changed during route report")
                self.next_mesh = now
            elif relevant and error is not None:
                self.next_mesh = min(self.next_mesh, now)
        if self.report_future is None and self.reports:
            host = next(iter(self.reports))
            value = self.reports.pop(host)
            if (
                self.state.mesh["state"] == "ready"
                and value["mesh_revision"] == self.state.mesh["revision"]
            ):
                self.report_future = executor.submit(self.report, value)
                self.report_revision = value["mesh_revision"]

    def connection_tick(self, now):
        for host, connection in list(self.connections.items()):
            connection.poll(now)
            now = boottime_ms()
            remote = connection.state.local_clock is None
            if (
                remote
                and connection.reached
                and (
                    not connection.reached_reported
                    or now >= getattr(connection, "next_report_at", now + 1)
                )
            ):
                self.queue_report(connection, now, "reachable")
            if connection.closed:
                retry = self.retries.setdefault(host, Retry())
                if remote and connection.unreachable:
                    self.queue_report(connection, now, "unreachable")
                    retry.route += 1
                else:
                    retry.route = 0
                retry.failures += 1
                base = min(30000, 1000 * 2 ** min(retry.failures - 1, 5))
                retry.next_at = now + int(random.uniform(base, min(30000, base * 1.2)))
                self.tickets.owner_lost(host, now)
                self.mark_changed()
                del self.connections[host]
            elif connection.state.transport == "ready":
                self.retries.setdefault(host, Retry()).failures = 0
        if self.state.mesh["state"] not in ("ready", "local_only"):
            return
        connecting = sum(
            c.state.transport == "connecting" and c.state.local_clock is None
            for c in self.connections.values()
        )
        for description in self.state.descriptions:
            host = description["hostId"]
            retry = self.retries.setdefault(host, Retry())
            if (
                host in self.connections
                or now < retry.next_at
                or not description["local"]
                and connecting >= 4
            ):
                continue
            owner = self.state.owners[host]
            try:
                if description["local"]:
                    connection = self.local_connection(
                        host,
                        now,
                        path=self.owner_path,
                        state=owner,
                        on_frame=self.owner_frame,
                        on_input=self.before_input,
                        on_error=self.tickets.operation_error,
                    )
                else:
                    mesh_host = next(h for h in self.snapshot.hosts if h.host_id == host)
                    route = mesh_host.routes[retry.route % len(mesh_host.routes)]
                    connection = self.remote_connection(
                        mesh_host,
                        route,
                        self.snapshot.policy,
                        now,
                        state=owner,
                        remote_exec=self.remote_exec,
                        on_frame=self.owner_frame,
                        on_input=self.before_input,
                        on_error=self.tickets.operation_error,
                    )
                    owner.selected_route = route.destination
                    connecting += 1
                self.connections[host] = connection
                self.mark_changed()
            except (IPCError, ContractError, OSError, ValueError):
                self.mark_changed()
                owner.fail("owner_unavailable", "prepared owner subscription could not start")
                retry.failures += 1
                retry.next_at = now + min(30000, 1000 * 2 ** min(retry.failures - 1, 5))

    def desktop_eligible(self, now):
        result = set()
        for ticket_id in self.tickets.desktop_ready():
            rows = self.tickets.store.entries[ticket_id].value["sources"]
            if all(
                row["state"] != "complete" or self.state.owners[row["hostId"]].expiry > now
                for row in rows
                if row["source"] == "owner"
            ):
                result.add(ticket_id)
        return result

    def attachment_work(self):
        try:
            from .attachments import _PreparedAttachments

            return _PreparedAttachments(
                read_local_attachments(self.state.host_id, owner_path=self.owner_path)
            )
        except (IPCError, OSError, ValueError):
            return None

    def attachment_tick(self, executor, now):
        if not self.profile_enabled:
            return
        if self.attachment_future is not None and self.attachment_future.done():
            value = self.attachment_future.result()
            self.state.attachments = value
            # A receipt-only renewal also moves the next projection expiry.
            # The prepared projection computes the new hash once; comparison
            # here previously repeated that work without changing admission.
            self.mark_changed()
            self.attachment_future = None
        if self.attachment_future is None and now >= self.next_attachment:
            self.attachment_future = executor.submit(self.attachment_work)
            self.next_attachment = now + 2000

    def desktop_work(self, job):
        started = boottime_ms()
        job.started.append(started)
        try:
            kwargs = (
                {"context_id": self.state.context_id, "epoch": job.epoch}
                if self.profile_enabled
                else {}
            )
            bindings = None
            scanner = self.scanner
            if self.profile_enabled:
                if job.parents:
                    local = next((host for host in job.hosts if host["local"]), None)
                    bindings = self.binding_adapter.prepare(
                        local,
                        context_id=self.state.context_id,
                        epoch=job.binding_epoch,
                        deadline=started + 2000,
                        force=True,
                    )
                else:
                    from .desktop import scan_remote

                    scanner = scan_remote
            result = scanner(job.hosts, deadline=started + 2000, **kwargs)
            if bindings is not None and hasattr(result, "bindings"):
                result.bindings = bindings
            state, observations, _error = result
            if state not in ("ready", "failed", "unsupported") or not isinstance(
                observations, dict
            ):
                raise ValueError("invalid desktop adapter result")
        except (OSError, ValueError, TypeError, KeyError, AttributeError, ContractError):
            result = (
                "failed",
                {},
                {"code": "desktop_failed", "message": "passive desktop scan failed"},
            )
        return started, boottime_ms(), result

    def binding_work(self, host, epoch):
        started = boottime_ms()
        try:
            value = self.binding_adapter.prepare(
                host, context_id=self.state.context_id, epoch=epoch, deadline=started + 2000
            )
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            value = None
        return started, boottime_ms(), value

    def binding_tick(self, executor, now):
        if self.binding_adapter is None:
            return
        if self.binding_future is not None and self.binding_future.done():
            started, finished, value = self.binding_future.result()
            self.last_binding_start = started
            key, epoch = self.binding_job
            self.state.accept_bindings(
                value, key=key, epoch=epoch, started=started, finished=finished, now=now
            )
            self.mark_changed()
            self.binding_future = self.binding_job = None
        # One shared adapter and executor also serve explicit rediscovery.
        if self.binding_future is not None or self.desktop_future is not None:
            return
        key = self.current_binding_key(now)
        if key is None:
            return
        owner = self.state.owners.get(self.state.host_id)
        dependencies = key, id(self.state.attachments), owner.expiry
        retry_at = self.binding_adapter.retry_at
        if now >= self.last_binding_start + 1000 and (
            dependencies != self.binding_dependencies or retry_at is not None and now >= retry_at
        ):
            self.binding_dependencies = dependencies
            self.binding_job = key, self.state.binding_epoch
            self.binding_future = executor.submit(
                self.binding_work, self.state.local_input(now), self.state.binding_epoch
            )

    def desktop_tick(self, executor, now):
        fingerprint = self.fingerprint(self.state.context_id)
        if fingerprint != self.context_fingerprint:
            self.context_fingerprint = fingerprint
            self.mark_changed()
            self.state.invalidate_desktop()
            self.state.invalidate_bindings()
            self.tickets.invalidate(now, desktop_only=True)
            self.next_desktop = now
            self.desktop_input = None
        job = self.desktop_job
        if job is not None and job.started and not job.begun:
            job.begun = True
            self.last_desktop_start = job.started[0]
            self.tickets.desktop_begin(job.parents, job.attempt, job.started[0], now)
        if self.desktop_future is not None and self.desktop_future.done():
            self.mark_changed()
            started, finished, result = self.desktop_future.result()
            state, observations, error = result
            now = boottime_ms()
            obsolete = job.epoch != self.state.desktop[
                "epoch"
            ] or job.key != self.current_input_key(now)
            accepted = self.state.accept_desktop(
                epoch=job.epoch,
                key=job.key,
                started=started,
                finished=finished,
                now=now,
                state=state,
                observations=observations,
                error=error,
                association=getattr(result, "association", None),
            )
            if getattr(result, "bindings", None) is not None:
                self.state.accept_bindings(
                    result.bindings,
                    key=job.binding_key,
                    epoch=job.binding_epoch,
                    started=started,
                    finished=finished,
                    now=now,
                )
            self.tickets.desktop_finish(
                job.attempt,
                now,
                accepted=accepted,
                error=self.state.desktop["error"],
                obsolete=obsolete,
            )
            self.desktop_future = self.desktop_job = None
            self.next_desktop = started + 3000
        if (
            self.state.mesh["state"] not in ("ready", "local_only")
            or self.desktop_future is not None
        ):
            return
        eligible = self.desktop_eligible(now)
        if (
            self.profile_enabled
            and not eligible
            and not any(not host["local"] for host in self.state.descriptions)
        ):
            return
        changed = self.desktop_input != self.current_input_key(now)
        if now >= self.last_desktop_start + 1000 and (
            now >= self.next_desktop or eligible or changed
        ):
            self.desktop_attempt += 1
            job = DesktopJob(
                self.desktop_attempt,
                self.state.desktop["epoch"],
                self.current_input_key(now),
                eligible,
                self.state.inputs(now),
                binding_key=self.current_binding_key(now),
                binding_epoch=self.state.binding_epoch,
            )
            self.desktop_job = job
            self.desktop_input = job.key
            self.desktop_future = executor.submit(self.desktop_work, job)

    def publish_tickets(self, now):
        for value in self.tickets.take_changes():
            for peer in list(self.hub.peers):
                if peer.watch and not peer.closing:
                    self.hub.frame(peer, now, kind="refresh_result", ticket=value)

    def catalog_tick(self, executor, now):
        if self.catalog_future is not None and self.catalog_future.done():
            self.catalog_result(self.catalog_future.result(), now)
            self.catalog_future = None
        if self.catalog_future is None and now >= self.next_mesh:
            self.catalog_future = executor.submit(self.load_catalog)
            self.next_mesh = now + 15000

    def run(self):
        self.hub = SocketHub(
            self.path,
            protocol=FLEET_PROTOCOL,
            now=boottime_ms,
            make_frame=self.frame,
            handle_request=self.handle,
            share_broadcast_body=True,
        )
        previous = boottime_ms()
        next_heartbeat = previous + 3000
        mesh_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tmux-mesh")
        report_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tmux-route-report")
        desktop_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tmux-desktop")
        try:
            while not self.stop_event.is_set():
                now = boottime_ms()
                if now - previous >= 3000:
                    self.disconnect(now, remotes_only=True, code="clock_jump")
                    self.state.invalidate_desktop()
                    self.state.invalidate_bindings()
                    self.tickets.invalidate(now, desktop_only=True)
                previous = now
                self.catalog_tick(mesh_executor, now)
                self.connection_tick(now)
                now = boottime_ms()
                if self.capacity:
                    self.catalog_failure(
                        now, "capacity", "retained owner document pool exceeded its bound"
                    )
                    self.state.mesh["state"] = "capacity"
                    self.capacity = False
                self.report_tick(report_executor, now)
                self.tickets.tick(self.connections, now)
                self.attachment_tick(desktop_executor, now)
                self.binding_tick(desktop_executor, now)
                self.desktop_tick(desktop_executor, now)
                now = boottime_ms()
                self.project_changed(now)
                self.publish_tickets(now)
                if self.publish_needed:
                    self.publish_needed = False
                    self.hub.broadcast(now, kind="view")
                elif now >= next_heartbeat:
                    self.hub.broadcast(now, kind="heartbeat")
                if now >= next_heartbeat:
                    next_heartbeat = now + 3000
                self.hub.poll(now)
        finally:
            self.disconnect(boottime_ms())
            self.hub.close()
            for executor in (mesh_executor, report_executor, desktop_executor):
                executor.shutdown(wait=True, cancel_futures=True)

    def stop(self):
        self.stop_event.set()
