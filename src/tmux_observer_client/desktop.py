"""Independent endpoint-local observations with exact native client joins."""

from __future__ import annotations

import os
from dataclasses import dataclass

from tmux_observer._clock import boottime_ms, domain
from tmux_observer.native import Session

from ._desktop_input import input_hash, reference
from ._desktop_scan import DesktopConfig, ViewerTarget, _niri_windows, observe_local_viewers
from ._desktop_types import LocalViewerObservation
from .attachments import CachedClients, current_attachments
from .desktop_contract import DESKTOP_PROTOCOL, validate_desktop


@dataclass
class DesktopResult:
    state: str
    observations: dict
    error: dict | None
    association: dict | None = None
    bindings: dict | None = None

    def __iter__(self):
        return iter((self.state, self.observations, self.error))


def association_batch(
    hosts, observations, *, context_id, epoch, started, now, state="ready", error=None
):
    dependencies, rows = [], []
    for host in hosts:
        owner = host["owner"]
        association = (
            current_attachments(host, host.get("localAttachments"), now) if host["local"] else None
        )
        dependencies.append(
            {
                "hostId": host["hostId"],
                "local": host["local"],
                "publisherId": owner["publisherId"],
                "serverGeneration": owner["serverGeneration"],
                "ownerExpiresAt": owner["localExpiry"],
                "associationExpiresAt": association["receipt"]["expiresAt"]
                if association
                else None,
            }
        )
        for row in host["sessions"]:
            observation = observations.get(reference(row))
            presence = {
                "state": "unknown",
                "confidence": None,
                "evidence": "unknown",
                "reason": "inventory_incomplete",
            }
            if observation is not None:
                presence.update(
                    state=observation.state,
                    confidence=observation.confidence,
                    evidence=observation.evidence
                    or ("absence" if observation.state == "none" else "unknown"),
                    reason=observation.reason,
                )
                if observation.state == "open" and observation.evidence == "launch_reference":
                    presence["confidence"] = "matched"
                positive = observation.state in ("open", "none")
                unsupported_open = observation.state == "open" and (
                    not row["attachedClients"]
                    or (observation.evidence == "launch_reference" and not observation.qualified)
                )
                if positive and (
                    state != "ready"
                    or owner["localExpiry"] <= now
                    or host["local"]
                    and association is None
                    or unsupported_open
                ):
                    presence = {
                        "state": "unknown",
                        "confidence": None,
                        "evidence": "unknown",
                        "reason": "attachment_unverified",
                    }
            rows.append(
                {
                    "sessionRef": {
                        key: row[key]
                        for key in ("hostId", "serverGeneration", "sessionId", "createdAt")
                    },
                    "attachedClients": row["attachedClients"],
                    "presence": presence,
                }
            )
    return validate_desktop(
        {
            "protocol": DESKTOP_PROTOCOL,
            "schemaVersion": 1,
            "clock": domain(),
            "contextId": context_id,
            "epoch": epoch,
            "encodedAt": now,
            "receipt": {
                "state": state,
                "startedAt": started,
                "acceptedAt": now,
                "expiresAt": started + 10000,
                "inputHash": input_hash(hosts, now=now),
                "error": error,
            },
            "dependencies": dependencies,
            "rows": rows,
        }
    )


def scan(hosts, *, deadline, config=None, context_id=None, epoch=0):
    from .public import desktop_context_id

    context_id = desktop_context_id() if context_id is None else context_id
    started = deadline - 2000
    config = DesktopConfig() if config is None else config
    targets = []
    for host in hosts:
        for row in host["sessions"]:
            session = Session(
                reference(row),
                row["name"],
                row["activityAt"],
                row["lastAttachedAt"],
                row["attachedClients"],
                row["pending"],
                row["windowCount"],
                row["sessionPath"],
                row["currentWindow"],
                row["currentPath"],
            )
            targets.append(
                ViewerTarget(
                    session,
                    host["local"],
                    host["owner"]["source"]["nativeHostname"],
                    host.get("route"),
                    host.get("remoteExecutable") or "ssh",
                )
            )
    if not os.environ.get("NIRI_SOCKET"):
        return (
            "unsupported",
            {},
            {
                "code": "unsupported_desktop",
                "message": "desktop context has no compositor endpoint",
            },
        )
    if not targets:
        windows = _niri_windows(
            ("niri",), timeout_seconds=max(0.001, min(1, (deadline - boottime_ms()) / 1000))
        )
        if windows is None or boottime_ms() >= deadline:
            return (
                "failed",
                {},
                {
                    "code": "compositor_unavailable",
                    "message": "empty desktop input still requires a compositor read",
                },
            )
        modern = association_batch(
            hosts, {}, context_id=context_id, epoch=epoch, started=started, now=boottime_ms()
        )
        return DesktopResult("ready", {}, None, modern)
    batch = observe_local_viewers(
        targets, config, local_tmux=CachedClients(hosts, deadline), deadline=deadline / 1000
    )
    if boottime_ms() >= deadline:
        return (
            "failed",
            {},
            {"code": "deadline", "message": "desktop scan exceeded its start-based budget"},
        )
    observations = {
        key: {"reason": None, **value.as_dict()} for key, value in batch.observations.items()
    }
    if observations and all(
        value["reason"] == "compositor_unavailable" for value in observations.values()
    ):
        return (
            "failed",
            {},
            {"code": "compositor_unavailable", "message": "desktop compositor could not be read"},
        )
    modern = association_batch(
        hosts,
        batch.observations,
        context_id=context_id,
        epoch=epoch,
        started=started,
        now=boottime_ms(),
    )
    return DesktopResult("ready", observations, None, modern)


def scan_remote(hosts, *, deadline, context_id, epoch):
    """Keep fresh remote observations without rediscovering stable local clients."""
    started = deadline - 2000
    result = scan(
        [host for host in hosts if not host["local"]],
        deadline=deadline,
        context_id=context_id,
        epoch=epoch,
    )
    state, observations, error = result
    if state != "ready":
        return result
    observations.update(
        {
            reference(row): {"state": "unknown", "reason": "retained_association_only"}
            for host in hosts
            if host["local"]
            for row in host["sessions"]
        }
    )
    # Preserve the remote adapter's evidence classes and confidence exactly.
    # Only the local legacy rows become unknown; retained local evidence has
    # its own versioned extension and cannot impersonate a fresh C3 capture.
    modern = association_batch(
        hosts,
        {
            ref: LocalViewerObservation("unknown", reason="retained_association_only")
            for ref in observations
        },
        context_id=context_id,
        epoch=epoch,
        started=started,
        now=boottime_ms(),
    )
    remote_rows = {reference(row["sessionRef"]): row for row in result.association["rows"]}
    modern["rows"] = [remote_rows.get(reference(row["sessionRef"]), row) for row in modern["rows"]]
    return DesktopResult(state, observations, error, validate_desktop(modern))
