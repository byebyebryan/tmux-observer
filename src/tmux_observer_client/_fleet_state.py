"""Aggregate projections and independent desktop acceptance; no source jobs."""

from __future__ import annotations

import copy
import hashlib
import uuid

from tmux_observer.native import encode_document
from tmux_observer_client.contract import FLEET_PROTOCOL, validate_fleet_frame, validate_fleet_view

from ._contract_validation import viewer
from ._desktop_input import input_hash, reference
from ._remote_state import RemoteState
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
                result.append(host)
        return result

    def input_key(self, now):
        return input_hash(self.inputs(now))

    def accept_desktop(self, *, epoch, key, started, finished, now, state, observations, error):
        if epoch != self.desktop["epoch"] or key != self.input_key(now):
            return False
        previous = copy.deepcopy(self.desktop), self.viewers
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
            elif state in ("failed", "unsupported") and error is not None:
                self.desktop.update(state=state, error=copy.deepcopy(error))
            else:
                raise ValueError("invalid desktop outcome")
            self.view(now)
        except (ValueError, TypeError, KeyError):
            # A faulty adapter cannot poison accepted state or expose authority.
            self.desktop, self.viewers = previous
            self.desktop.update(
                state="failed",
                error={"code": "invalid_desktop", "message": "invalid desktop outcome rejected"},
            )
            self.view(now)
            return False
        return state == "ready"

    def view(self, now, *, ticket=None):
        hosts = self.hosts(now)
        desktop = copy.deepcopy(self.desktop)
        if desktop["state"] == "ready":
            if now >= desktop["expiresAt"]:
                desktop["state"] = "expired"
            elif desktop["inputHash"] != self.input_key(now):
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
        value = {
            "protocol": FLEET_PROTOCOL,
            "schemaVersion": 1,
            "readerId": self.reader_id,
            "clock": self.clock,
            "contextId": self.context_id,
            "encodedAt": now,
            "viewRevision": self.revision,
            "mesh": self.mesh,
            "desktop": desktop,
            "hosts": hosts,
            "ticket": ticket,
            "error": self.error,
        }
        try:
            encode_document(value)
        except ValueError:
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
        return copy.deepcopy(validate_fleet_view(value))

    def material(self, now):
        view = self.view(now)
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

    def frame(self, now, *, kind="view", sequence=0, request_id=None, ticket=None):
        view = self.view(now)
        return validate_fleet_frame(
            {
                "protocol": FLEET_PROTOCOL,
                "schemaVersion": 1,
                "readerId": self.reader_id,
                "clock": self.clock,
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
