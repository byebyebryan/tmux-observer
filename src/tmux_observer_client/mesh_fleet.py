"""Mesh cached-state transport with the existing Observer Fleet v1 projection."""

from concurrent.futures import ThreadPoolExecutor

from tmux_observer._clock import boottime_ms
from tmux_observer._ipc import IPCError

from ._errors import ContractError
from ._mesh_control import OwnerControl
from ._mesh_projection import MeshOwnerState
from ._mesh_worker import MeshWorker
from .fleet import POOL_LIMIT, FleetPublisher
from .mesh import _parse_snapshot


class MeshFleetPublisher(FleetPublisher):
    def __init__(self, host_id, *, source="tmux_default", authority=None, **kwargs):
        super().__init__(host_id, **kwargs)
        self.worker = MeshWorker(
            host_id, owner_path=self.owner_path, source=source, authority=authority
        )
        self.mesh_reader = None
        self.control_executor = None

    def disconnect(self, now, *, remotes_only=False, code="stale_scope"):
        super().disconnect(now, remotes_only=remotes_only, code=code)
        for owner in self.state.owners.values():
            if not remotes_only or owner.local_clock is None:
                owner.fail(code, "Mesh delivery association was replaced")
        if code == "clock_jump":
            self.worker.restart()

    def catalog_tick(self, _executor, now):
        if not self.worker.thread.is_alive():
            raise IPCError("mesh_unavailable", "owned Mesh reader stopped")
        for event in self.worker.take():
            now = boottime_ms()
            if event[0] == "error":
                self.catalog_failure(now, event[1], "Mesh cached-state reader is unavailable")
                self.mesh_reader = None
                continue
            _, frame, catalog = event
            reader = frame["mesh"]["reader"]
            if reader["clock"] != self.state.clock or reader["encodedAtMs"] > now:
                self.catalog_failure(now, "scope_mismatch", "Mesh reader clock differs")
                self.worker.restart()
                continue
            if reader["id"] != self.mesh_reader:
                self.disconnect(now)
                self.tickets.invalidate(now)
                self.state.invalidate_bindings()
                self.state.invalidate_desktop()
                snapshot = _parse_snapshot(catalog.payload)
                if not self.state.catalog(snapshot):
                    self.worker.restart()
                    continue
                self.snapshot = snapshot
                self.mesh_reader = reader["id"]
                for host in self.state.descriptions:
                    previous = self.state.owners[host["hostId"]]
                    if not isinstance(previous, MeshOwnerState):
                        self.state.owners[host["hostId"]] = MeshOwnerState(
                            host["hostId"], local_clock=self.state.clock if host["local"] else None
                        )
                self.retained = {
                    host: size for host, size in self.retained.items() if host in self.state.owners
                }
            try:
                for host in frame["mesh"]["hosts"]:
                    owner = self.state.owners[host["hostId"]]
                    rows = [row for row in frame["sessions"] if row["hostId"] == host["hostId"]]
                    selected_route = None
                    if not host["local"]:
                        selected = next(
                            (
                                route
                                for entry in catalog.hosts
                                if entry["id"] == host["hostId"]
                                for route in entry["routes"]
                                if catalog.route_token(entry["id"], route)
                                == host["delivery"]["routeToken"]
                            ),
                            None,
                        )
                        if selected is None:
                            raise ValueError("Mesh selected route is not in the captured catalog")
                        selected_route = selected["destination"]
                    owner.accept_mesh(
                        host,
                        rows,
                        reader_id=reader["id"],
                        reader_clock=reader["clock"],
                        now=now,
                        selected_route=selected_route,
                        reserve=lambda size, host_id=owner.host_id: self.reserve_owner(
                            host_id, size
                        ),
                    )
                    self.retained[owner.host_id] = owner.confirmed_size + owner.candidate_size
                    if sum(self.retained.values()) > POOL_LIMIT:
                        raise ValueError("Mesh retained native owner pool exceeded its bound")
                    self.tickets.settle(owner.host_id, boottime_ms())
                self.mark_changed()
            except (ContractError, IPCError, ValueError, KeyError, TypeError):
                self.catalog_failure(now, "invalid_owner_stream", "Mesh native projection failed")
                self.mesh_reader = None
                self.worker.restart()
                break

    def reserve_owner(self, host, size):
        if size + sum(value for key, value in self.retained.items() if key != host) > POOL_LIMIT:
            self.capacity = True
            raise ContractError("capacity", "Mesh retained native owner pool exceeded its bound")

    def connection_tick(self, now):
        # Control facades are idle until FleetTickets sends an explicit request.
        for host, connection in list(self.connections.items()):
            connection.poll(now)
            owner = self.state.owners.get(host)
            if (
                owner is None
                or owner.transport != "ready"
                or connection.closed
                or connection.binding != (owner.epoch, owner.scope, owner.selected_route)
            ):
                connection.fail("stale_scope", "Mesh owner is unavailable")
                self.tickets.owner_lost(host, now)
                del self.connections[host]
        if self.state.mesh["state"] != "ready":
            return
        for host in self.snapshot.hosts:
            owner = self.state.owners[host.host_id]
            if owner.transport != "ready" or host.host_id in self.connections:
                continue
            route = next(
                (route for route in host.routes if route.destination == owner.selected_route), None
            )
            if not host.local and route is None:
                continue
            self.connections[host.host_id] = OwnerControl(
                owner,
                self.control_executor,
                path=self.owner_path,
                host=host,
                route=route,
                policy=self.snapshot.policy,
                remote_exec=self.remote_exec,
                on_frame=self.tickets.receive,
                on_error=self.tickets.operation_error,
            )

    def report_tick(self, _executor, _now):
        # Mesh alone owns route reports for state channels.
        pass

    def run(self):
        self.control_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tmux-control")
        self.worker.start()
        try:
            super().run()
        finally:
            self.worker.close()
            self.control_executor.shutdown(wait=True, cancel_futures=True)
