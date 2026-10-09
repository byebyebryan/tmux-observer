"""Aggregate projections and independent desktop acceptance; no source jobs."""

from __future__ import annotations

import copy
import hashlib
import uuid

from tmux_observer._wire import WireError
from tmux_observer.native import encode_document
from tmux_observer_client.contract import FLEET_PROTOCOL, validate_fleet_frame, validate_fleet_view

from ._binding_projection import binding_key, project_bindings
from ._contract_validation import viewer
from ._desktop_input import input_hash, reference
from ._remote_state import RemoteState
from .bindings_contract import validate_fleet_bindings
from .desktop_contract import validate_desktop
from .public import owner_current


class FleetState:
    def __init__(self, host_id, context_id, clock):
        self.host_id = host_id
        self.context_id = context_id
        self.clock = copy.deepcopy(clock)
        self.reader_id = str(uuid.uuid4())
        self.revision = 0
        self.signature = None
        self.mesh = {"state": "warming", "revision": None, "localHostId": host_id}
        self.descriptions = []
        self.owners = {}
        self.error = None
        self.desktop = {
            "contextId": context_id,
            "epoch": 0,
            "state": "warming",
            "startedAt": None,
            "acceptedAt": None,
            "expiresAt": None,
            "inputHash": None,
            "error": None,
        }
        self.viewers = {}
        self.attachments = None
        self.association = None
        self.bindings = None
        self.bindings_key = None
        self.binding_epoch = 0
        validate_fleet_view(self.view(0))

    def catalog(self, snapshot):
        if snapshot is None:
            descriptions = [
                {
                    "hostId": self.host_id,
                    "display": self.host_id,
                    "local": True,
                    "routes": (),
                    "remoteExecutable": None,
                }
            ]
            state, revision = "local_only", None
        else:
            if snapshot.local_host_id != self.host_id:
                self.catalog_error(
                    "scope_mismatch", "Mesh local host differs from configured owner"
                )
                return False
            if len(snapshot.hosts) > 16:
                self.mesh.update(state="capacity", revision=snapshot.revision)
                self.error = {
                    "code": "capacity",
                    "message": "prepared fleet supports at most 16 owners",
                }
                self.invalidate_desktop()
                return False
            descriptions = [
                {
                    "hostId": host.host_id,
                    "display": host.display,
                    "local": host.local,
                    "routes": host.routes,
                    "remoteExecutable": snapshot.policy.executable,
                }
                for host in snapshot.hosts
            ]
            state, revision = "ready", snapshot.revision
        changed = self.mesh != {"state": state, "revision": revision, "localHostId": self.host_id}
        self.mesh = {"state": state, "revision": revision, "localHostId": self.host_id}
        self.descriptions = descriptions
        self.error = None
        wanted = {host["hostId"] for host in descriptions}
        self.owners = {key: owner for key, owner in self.owners.items() if key in wanted}
        for host in descriptions:
            self.owners.setdefault(
                host["hostId"],
                RemoteState(host["hostId"], local_clock=self.clock if host["local"] else None),
            )
        if changed:
            self.invalidate_desktop()
        return True

    def catalog_error(self, code, message):
        self.mesh["state"] = "unavailable"
        self.error = {"code": code, "message": message}
        self.invalidate_desktop()

    def invalidate_desktop(self):
        self.desktop["epoch"] += 1
        self.desktop.update(
            state="warming",
            startedAt=None,
            acceptedAt=None,
            expiresAt=None,
            inputHash=None,
            error=None,
        )
        self.viewers = {}
        self.association = None

    def hosts(self, now):
        result = []
        for description in self.descriptions:
            state = self.owners[description["hostId"]]
            owner, rows = state.project()
            if self.mesh["state"] not in ("ready", "local_only"):
                owner["localExpiry"] = 0
            host = {
                "hostId": description["hostId"],
                "display": description["display"],
                "local": description["local"],
                "owner": owner,
                "sessions": rows,
            }
            result.append(host)
        return result

    def inputs(self, now):
        result = []
        descriptions = {host["hostId"]: host for host in self.descriptions}
        for host in self.hosts(now):
            if owner_current({"mesh": self.mesh}, host, now=now):
                description = descriptions[host["hostId"]]
                routes = description["routes"]
                host["route"] = getattr(self.owners[host["hostId"]], "selected_route", None)
                if not host["local"] and host["route"] is None and routes:
                    # Only a selected live transport supplies route context.
                    continue
                host["remoteExecutable"] = description["remoteExecutable"]
                if host["local"]:
                    host["localAttachments"] = self.attachments
                result.append(host)
        return result

    def input_key(self, now):
        return input_hash(self.inputs(now), now=now)

    def local_input(self, now):
        description = next((item for item in self.descriptions if item["local"]), None)
        if description is None:
            return None
        owner, rows = self.owners[description["hostId"]].project()
        host = {
            "hostId": description["hostId"],
            "display": description["display"],
            "local": True,
            "owner": owner,
            "sessions": rows,
            "route": None,
            "remoteExecutable": description["remoteExecutable"],
            "localAttachments": self.attachments,
        }
        return host if owner_current({"mesh": self.mesh}, host, now=now) else None

    def binding_key(self, now):
        return binding_key(
            self.local_input(now), now=now, context_id=self.context_id, epoch=self.binding_epoch
        )

    def invalidate_bindings(self):
        self.binding_epoch += 1
        self.bindings = self.bindings_key = None

    def accept_bindings(self, value, *, key, epoch, started, finished, now):
        if (
            value is None
            or epoch != self.binding_epoch
            or key != self.binding_key(now)
            or not started <= finished <= now < started + 2000
        ):
            return False
        host = self.local_input(now)
        try:
            validate_fleet_bindings(
                value, host, context_id=self.context_id, clock_value=self.clock, now=now
            )
            if value["epoch"] != epoch or not started <= value["receipt"]["preparedAt"] <= finished:
                return False
        except (ValueError, TypeError, KeyError):
            return False
        self.bindings, self.bindings_key = copy.deepcopy(value), key
        return True

    def accept_desktop(
        self, *, epoch, key, started, finished, now, state, observations, error, association=None
    ):
        if epoch != self.desktop["epoch"] or key != self.input_key(now):
            return False
        previous = copy.deepcopy(self.desktop), self.viewers, self.association
        if not started <= finished <= now < started + 2000:
            state, observations, error = (
                "failed",
                {},
                {"code": "deadline", "message": "late desktop result rejected"},
            )
        if state == "ready":
            expected = {reference(row) for host in self.inputs(now) for row in host["sessions"]}
            if set(observations) != expected:
                state, observations, error = (
                    "failed",
                    {},
                    {
                        "code": "invalid_desktop",
                        "message": "desktop result lacks exact current reference coverage",
                    },
                )
        try:
            if state == "ready":
                if association is not None:
                    validate_desktop(association)
                    if (
                        association["contextId"] != self.context_id
                        or association["epoch"] != epoch
                        or association["clock"] != self.clock
                        or association["receipt"]["inputHash"] != key
                        or association["receipt"]["startedAt"] != started
                        or not started <= association["encodedAt"] <= finished
                    ):
                        raise ValueError("desktop association is not bound to accepted job")
                    inputs = {host["hostId"]: host for host in self.inputs(now)}
                    expected_rows = {
                        reference(row): row for host in inputs.values() for row in host["sessions"]
                    }
                    if set(expected_rows) != {
                        reference(row["sessionRef"]) for row in association["rows"]
                    }:
                        raise ValueError("desktop association lacks complete input coverage")
                    for row in association["rows"]:
                        if (
                            row["attachedClients"]
                            != expected_rows[reference(row["sessionRef"])]["attachedClients"]
                        ):
                            raise ValueError("desktop association changed native attachment facts")
                    if {dep["hostId"] for dep in association["dependencies"]} != set(inputs):
                        raise ValueError("desktop association changed source coverage")
                    for dep in association["dependencies"]:
                        host = inputs[dep["hostId"]]
                        owner = host["owner"]
                        profile = host.get("localAttachments")
                        if (
                            dep["local"] != host["local"]
                            or dep["publisherId"] != owner["publisherId"]
                            or dep["serverGeneration"] != owner["serverGeneration"]
                            or dep["ownerExpiresAt"] > owner["localExpiry"]
                            or dep["associationExpiresAt"] is not None
                            and (
                                profile is None
                                or dep["associationExpiresAt"] > profile["receipt"]["expiresAt"]
                            )
                        ):
                            raise ValueError("desktop association changed dependency authority")
                encode_document(list(observations.values()), limit=16 * 1048576)
                for host in self.inputs(now):
                    for row in host["sessions"]:
                        presence = viewer(observations[reference(row)])
                        if presence.get("confidence") == "matched" and not row["attachedClients"]:
                            raise ValueError("unqualified matched viewer")
                self.desktop.update(
                    state="ready",
                    startedAt=started,
                    acceptedAt=now,
                    expiresAt=started + 10000,
                    inputHash=key,
                    error=None,
                )
                self.viewers = copy.deepcopy(observations)
                self.association = copy.deepcopy(association)
            elif state in ("failed", "unsupported") and error is not None:
                self.desktop.update(state=state, error=copy.deepcopy(error))
            else:
                raise ValueError("invalid desktop outcome")
            self.view(now)
        except (ValueError, TypeError, KeyError):
            # A faulty adapter cannot poison accepted state or expose authority.
            self.desktop, self.viewers, self.association = previous
            self.desktop.update(
                state="failed",
                error={"code": "invalid_desktop", "message": "invalid desktop outcome rejected"},
            )
            self.view(now)
            return False
        return state == "ready"

    def view(self, now, *, ticket=None, _input_key=None, _binding_key=None):
        hosts = self.hosts(now)
        desktop = copy.deepcopy(self.desktop)
        if desktop["state"] == "ready":
            if now >= desktop["expiresAt"]:
                desktop["state"] = "expired"
            elif desktop["inputHash"] != (
                self.input_key(now) if _input_key is None else _input_key
            ):
                desktop["state"] = "warming"
        for host in hosts:
            current = owner_current({"mesh": self.mesh}, host, now=now)
            for row in host["sessions"]:
                if not current:
                    presence = {"state": "unknown", "reason": "owner_unavailable"}
                elif desktop["state"] != "ready":
                    presence = {"state": "unknown", "reason": "desktop_unavailable"}
                else:
                    presence = self.viewers.get(
                        reference(row), {"state": "unknown", "reason": "inventory_incomplete"}
                    )
                row["localViewer"] = copy.deepcopy(presence)
            if host["local"] and self.bindings is not None:
                host["localBindings"] = project_bindings(
                    self.bindings,
                    accepted_key=self.bindings_key,
                    current_key=self.binding_key(now) if _binding_key is None else _binding_key,
                    now=now,
                )
        value = {
            "protocol": FLEET_PROTOCOL,
            "schemaVersion": 1,
            "readerId": self.reader_id,
            "clock": copy.deepcopy(self.clock),
            "contextId": self.context_id,
            "encodedAt": now,
            "viewRevision": self.revision,
            "mesh": copy.deepcopy(self.mesh),
            "desktop": desktop,
            "hosts": hosts,
            "ticket": copy.deepcopy(ticket),
            "error": copy.deepcopy(self.error),
        }
        try:
            validate_fleet_view(value)
        except WireError:
            # No truncated complete fleet is ever published.
            value = {
                **value,
                "mesh": {**self.mesh, "state": "capacity"},
                "hosts": [],
                "error": {
                    "code": "capacity",
                    "message": "prepared fleet exceeds its document bound",
                },
            }
            validate_fleet_view(value)
        # Hosts already own their projected owner/session trees; desktop,
        # bindings and presence are independent copies too. Copy only the
        # remaining shared fields above instead of copying all sessions twice.
        return value

    def material(self, now, *, _view=None):
        view = self.view(now) if _view is None else _view
        value = {
            "mesh": view["mesh"],
            "desktop": {
                key: view["desktop"][key]
                for key in ("contextId", "epoch", "state", "inputHash", "error")
            },
            "error": view["error"],
            "hosts": [
                {
                    "hostId": host["hostId"],
                    "display": host["display"],
                    "local": host["local"],
                    "owner": {
                        "publisherId": host["owner"]["publisherId"],
                        "transport": host["owner"]["transport"],
                        "state": host["owner"]["receipt"]["state"]
                        if host["owner"]["receipt"]
                        else "warming",
                        "current": owner_current(view, host, now=now),
                        "error": host["owner"]["error"],
                    },
                    "sessions": host["sessions"],
                    "localBindings": None
                    if host.get("localBindings") is None
                    else {
                        "epoch": host["localBindings"]["epoch"],
                        "rows": host["localBindings"]["rows"],
                        "state": host["localBindings"]["receipt"]["state"],
                        "error": host["localBindings"]["receipt"]["error"],
                    },
                }
                for host in view["hosts"]
            ],
        }
        signature = hashlib.sha256(encode_document(value)).digest()
        changed = signature != self.signature
        if changed:
            self.signature = signature
            self.revision += 1
        return changed

    def frame(self, now, *, kind="view", sequence=0, request_id=None, ticket=None, _view=None):
        # Only the publisher supplies a validated projection whose dependencies
        # have not changed or crossed a lease boundary. Revalidate the complete
        # outgoing frame at its current time, and never expose the retained tree.
        view = self.view(now) if _view is None else copy.deepcopy(_view)
        view.update(encodedAt=now, viewRevision=self.revision)
        return validate_fleet_frame(
            {
                "protocol": FLEET_PROTOCOL,
                "schemaVersion": 1,
                "readerId": self.reader_id,
                "clock": copy.deepcopy(self.clock),
                "contextId": self.context_id,
                "encodedAt": now,
                "sequence": sequence,
                "viewRevision": self.revision,
                "snapshot": view,
                "requestId": request_id,
                "error": view["error"],
                "ticket": ticket,
                "kind": kind,
            }
        )
