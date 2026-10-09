"""Legacy fresh-view projection from an explicit native job's accepted profile.

This adapter consumes native input; it never schedules or performs collection.
The explicit direct orchestrator owns the optional passive native job.
"""

import os

from tmux_observer._clock import boottime_ms, domain, pid_namespace
from tmux_observer.attachments import validate_attachments
from tmux_observer.native import Session, SessionReference

from ._desktop_scan import DesktopConfig, ViewerTarget, observe_local_viewers
from ._errors import ContractError


class FreshClients:
    def __init__(self, host, profile, deadline):
        self.host, self.profile, self.deadline = host, profile, deadline
        self.client_incarnations = {}

    def client_pids_by_session(self):
        profile, host, now = self.profile, self.host, boottime_ms()
        if profile is None or host is None:
            raise ContractError("operation_failed", "fresh local associations unavailable")
        validate_attachments(profile)
        if (
            now >= self.deadline
            or profile["source"]["hostId"] != host["hostId"]
            or profile["source"]["uid"] != os.getuid()
            or profile["clock"] != domain()
            or profile["pidNamespace"] != pid_namespace()
            or profile["sample"]["coverage"] != "complete"
            or not profile["sample"]["finishedAt"] <= now < profile["sample"]["startedAt"] + 10000
            or profile["serverGeneration"] != host["serverGeneration"]
        ):
            raise ContractError("operation_failed", "fresh local association scope expired")
        keys = ("hostId", "serverGeneration", "sessionId", "createdAt")
        expected = {tuple(row[key] for key in keys) for row in host["sessions"]}
        actual = {tuple(row[key] for key in keys) for row in profile["sessions"]}
        if expected != actual:
            raise ContractError("operation_failed", "fresh local association references differ")
        result = {row["sessionId"]: set() for row in host["sessions"]}
        for client in profile["clients"]:
            result[client["sessionRef"]["sessionId"]].add(client["clientPid"])
            self.client_incarnations[client["clientPid"]] = (
                profile["source"]["uid"],
                client["processStartTicks"],
            )
        return result


def enrich(response, *, endpoint, executable, profile, deadline, config=None):
    """Project display-only legacy presence; no handles or action authority."""
    hosts = response["hosts"]
    targets = []
    rows = {}
    for host in hosts:
        for row in host["sessions"]:
            reference = SessionReference(
                *(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
            )
            session = Session(
                reference,
                *(
                    row[key]
                    for key in (
                        "name",
                        "activityAt",
                        "lastAttachedAt",
                        "attachedClients",
                        "pending",
                        "windowCount",
                        "sessionPath",
                        "currentWindow",
                        "currentPath",
                    )
                ),
            )
            targets.append(
                ViewerTarget(
                    session,
                    host["local"],
                    host["nativeHostname"],
                    host.get("route"),
                    executable or "ssh",
                )
            )
            rows[reference] = row
    local = next((host for host in hosts if host["local"] and host["hostId"] == endpoint), None)
    batch = observe_local_viewers(
        targets,
        config or DesktopConfig(),
        local_tmux=FreshClients(local, profile, deadline),
        deadline=deadline / 1000,
    )
    for reference, observation in batch.observations.items():
        rows[reference]["localViewer"] = observation.as_dict()
    return response
