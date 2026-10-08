"""Prepared IPC facade. Imports no collector, network loop or write client."""

import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from tmux_observer._clock import boottime_ms, domain
from tmux_observer._ipc import exchange
from tmux_observer_client.contract import FLEET_PROTOCOL


def desktop_context_id(environment=None):
    environment = os.environ if environment is None else environment
    value = {
        "uid": os.getuid(),
        "clock": domain(),
        "desktop": {
            key: environment.get(key, "") for key in ("NIRI_SOCKET", "DISPLAY", "WAYLAND_DISPLAY")
        },
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:32]


def fleet_socket(context_id):
    if not isinstance(context_id, str) or re.fullmatch(r"[0-9a-f]{32}", context_id) is None:
        raise ValueError("invalid desktop context ID")
    root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return root / "tmux-observer-client" / f"fleet-{context_id}.sock"


def read_cached(
    context_id,
    *,
    expected_host=None,
    operation="snapshot",
    path=None,
    publisher_id=None,
    sources=None,
    ticket_id=None,
):
    request = {
        "protocol": FLEET_PROTOCOL,
        "schemaVersion": 1,
        "operation": operation,
        "requestId": uuid.uuid4().hex,
        "contextId": context_id,
    }
    if expected_host is not None:
        request["expectedHost"] = expected_host
    if publisher_id is not None:
        request["publisherId"] = publisher_id
    if sources is not None:
        request["sources"] = sources
    if ticket_id is not None:
        request["ticketId"] = ticket_id
    return exchange(request, path=fleet_socket(context_id) if path is None else path, budget_ms=250)


def owner_current(view, host, *, now=None):
    now = boottime_ms() if now is None else now
    owner = host["owner"]
    return (
        view["mesh"]["state"] in ("ready", "local_only")
        and owner["receipt"] is not None
        and owner["receipt"]["state"] == "ready"
        and owner["localExpiry"] is not None
        and owner["localExpiry"] > now
    )
