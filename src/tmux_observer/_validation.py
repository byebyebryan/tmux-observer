"""Pure protocol validation. No observation, routing, IPC or native imports."""

from __future__ import annotations

import re

from ._wire import DOCUMENT_LIMIT, ENVELOPE_LIMIT, MAX_INT, encode_document, validate_tree

OBSERVATION_PROTOCOL = "tmux-observer.observation.v1"
SERVICE_PROTOCOL = "tmux-observer.service.v1"
FLEET_PROTOCOL = "tmux-observer.fleet.v1"
OWNER_LEASE_MS = 10_000
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
HOST = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
TOKEN = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}"
SESSION = r"\$[0-9]+"
OPTION = r"@[A-Za-z0-9_.-]+"
SHA256 = r"sha256:[0-9a-f]{64}"
CONTEXT = r"[0-9a-f]{32}"


class ValidationError(ValueError):
    """The document violates supported structure or semantics."""


def obj(value: object, *keys: str) -> dict:
    if not isinstance(value, dict) or any(key not in value for key in keys):
        raise ValidationError("missing object or required field")
    return value


def integer(value: object, *, maximum: int = MAX_INT) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValidationError("invalid nonnegative integer")
    return value


def string(value: object, pattern: str | None = None, *, maximum: int = 16_384) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValidationError("invalid bounded string")
    if pattern and not re.fullmatch(pattern, value):
        raise ValidationError("invalid token syntax")
    return value


def nullable(value: object, validator):
    return None if value is None else validator(value)


def array(value: object, *, maximum: int) -> list:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValidationError("invalid bounded array")
    return value


def boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValidationError("invalid boolean")
    return value


def enum(value: object, choices: tuple[str, ...]) -> str:
    if value not in choices or not isinstance(value, str):
        raise ValidationError("unsupported variant")
    return value


def error(value: object) -> dict | None:
    if value is None:
        return None
    value = obj(value, "code", "message")
    string(value["code"], TOKEN, maximum=64)
    if not isinstance(value["message"], str) or len(value["message"]) > 4096:
        raise ValidationError("invalid diagnostic")
    return value


def clock(value: object) -> dict:
    value = obj(value, "bootId", "timeNamespace")
    string(value["bootId"], UUID, maximum=36)
    string(value["timeNamespace"], r"time:[0-9]+", maximum=64)
    return value


def source(value: object) -> dict:
    value = obj(value, "hostId", "uid", "server", "nativeHostname")
    string(value["hostId"], HOST)
    integer(value["uid"], maximum=2**32 - 1)
    if value["server"] != "default":
        raise ValidationError("unsupported server scope")
    nullable(value["nativeHostname"], string)
    return value


def reference(value: object) -> tuple:
    value = obj(value, "hostId", "serverGeneration", "sessionId", "createdAt")
    return (
        string(value["hostId"], HOST),
        string(value["serverGeneration"]),
        string(value["sessionId"], SESSION),
        integer(value["createdAt"]),
    )


def clock_key(value: dict) -> tuple:
    return value["bootId"], value["timeNamespace"]


def scope_key(value: dict) -> tuple:
    return value["hostId"], value["uid"], value["server"]


def validate_operation_error(value: object) -> dict:
    validate_tree(value)
    value = obj(value, "protocol", "schemaVersion", "kind", "error")
    enum(value["protocol"], (OBSERVATION_PROTOCOL, SERVICE_PROTOCOL, FLEET_PROTOCOL))
    if (
        type(value["schemaVersion"]) is not int
        or value["schemaVersion"] != 1
        or value["kind"] != "operation_error"
        or error(value["error"]) is None
    ):
        raise ValidationError("invalid operation error")
    encode_document(value, limit=16_384)
    return value


def sample(value: object) -> dict:
    value = obj(value, "startedAt", "finishedAt", "observedAt", "coverage", "error")
    start = integer(value["startedAt"])
    finish = integer(value["finishedAt"])
    integer(value["observedAt"])
    if finish < start:
        raise ValidationError("regressing sample clock")
    coverage = enum(value["coverage"], ("complete", "partial", "failed", "unsupported"))
    problem = error(value["error"])
    if (coverage == "complete") != (problem is None):
        raise ValidationError("sample coverage/error mismatch")
    return value


def session(value: object) -> dict:
    value = obj(
        value,
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
    reference(value)
    if "viewerId" in value or "closeSafe" in value:
        raise ValidationError("action authority in passive session")
    for key in ("name", "sessionPath", "currentWindow", "currentPath"):
        nullable(value[key], string)
    for key in ("activityAt", "lastAttachedAt", "attachedClients", "windowCount"):
        nullable(value[key], integer)
    boolean(value["pending"])
    if "options" in value:
        for name, child in obj(value["options"]).items():
            string(name, OPTION)
            if child is not None and not isinstance(child, str):
                raise ValidationError("invalid option value")
    if "panes" in value:
        seen = set()
        for pane in array(value["panes"], maximum=512):
            pane = obj(pane, "paneId", "pid", "currentPath", "currentCommand")
            pane_id = string(pane["paneId"], r"%[0-9]+")
            if pane_id in seen:
                raise ValidationError("duplicate pane identity")
            seen.add(pane_id)
            nullable(pane["pid"], integer)
            nullable(pane["currentPath"], string)
            nullable(pane["currentCommand"], string)
    return value


def validate_observation(value: object) -> dict:
    validate_tree(value)
    value = obj(
        value,
        "protocol",
        "schemaVersion",
        "source",
        "clock",
        "sample",
        "serverGeneration",
        "sessions",
        "capabilities",
    )
    if value["protocol"] != OBSERVATION_PROTOCOL or type(value["schemaVersion"]) is not int:
        raise ValidationError("unsupported observation protocol")
    if value["schemaVersion"] != 1:
        raise ValidationError("unsupported observation version")
    owner = source(value["source"])
    clock(value["clock"])
    sampled = sample(value["sample"])
    generation = nullable(value["serverGeneration"], string)
    rows = array(value["sessions"], maximum=256)
    caps = obj(value["capabilities"], "panes", "options")
    with_panes = boolean(caps["panes"])
    options = array(caps["options"], maximum=100_000)
    for name in options:
        string(name, OPTION)
    if len(set(options)) != len(options):
        raise ValidationError("duplicate requested option")
    if (sampled["coverage"] != "complete" or generation is None) and rows:
        raise ValidationError("incomplete/absent source has authoritative rows")
    if sampled["coverage"] != "complete" and generation is not None:
        raise ValidationError("incomplete source has authoritative generation")
    ids = set()
    pane_ids = set()
    for row in rows:
        session(row)
        ref = reference(row)
        if ref[0] != owner["hostId"] or ref[1] != generation or ref[2] in ids:
            raise ValidationError("session scope or identity conflict")
        ids.add(ref[2])
        if ("panes" in row) != with_panes or ("options" in row) != bool(options):
            raise ValidationError("unrequested native capability")
        if options and set(row["options"]) != set(options):
            raise ValidationError("option coverage mismatch")
        for pane in row.get("panes", []):
            if pane["paneId"] in pane_ids:
                raise ValidationError("duplicate owner pane identity")
            pane_ids.add(pane["paneId"])
    if len(pane_ids) > 512:
        raise ValidationError("owner pane capacity exceeded")
    encode_document(value, limit=DOCUMENT_LIMIT)
    return value


def receipt(value: object) -> dict:
    value = obj(
        value,
        "state",
        "attempted",
        "accepted",
        "acceptedAttempt",
        "startedAt",
        "acceptedAt",
        "expiresAt",
        "lastAttemptAt",
        "lastAttemptResult",
        "leaseMs",
        "remainingMs",
        "inFlight",
    )
    state = enum(value["state"], ("warming", "ready", "failed", "unsupported", "expired"))
    attempted = integer(value["attempted"])
    accepted = integer(value["accepted"])
    accepted_attempt = integer(value["acceptedAttempt"])
    if not accepted <= accepted_attempt <= attempted or (accepted == 0) != (accepted_attempt == 0):
        raise ValidationError("invalid sample counters")
    lease = integer(value["leaseMs"], maximum=OWNER_LEASE_MS)
    remaining = integer(value["remainingMs"], maximum=OWNER_LEASE_MS)
    if lease == 0 or remaining > lease or (state != "ready" and remaining != 0):
        raise ValidationError("invalid lease projection")
    for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
        nullable(value[key], integer)
    result = enum(
        value["lastAttemptResult"], ("none", "complete", "partial", "failed", "unsupported")
    )
    boolean(value["inFlight"])
    if (attempted == 0) != (value["lastAttemptAt"] is None) or (
        attempted == 0 and result != "none"
    ):
        raise ValidationError("invalid attempted sample")
    if (
        attempted == 0
        and value["inFlight"]
        or result == "none"
        and (accepted or attempted and not value["inFlight"])
    ):
        raise ValidationError("invalid unfinished attempt")
    fields = (value["startedAt"], value["acceptedAt"], value["expiresAt"])
    if accepted == 0:
        if any(field is not None for field in fields) or state == "ready":
            raise ValidationError("unaccepted native receipt")
    elif any(field is None for field in fields):
        raise ValidationError("missing accepted sample clock")
    elif not value["startedAt"] <= value["acceptedAt"] < value["expiresAt"]:
        raise ValidationError("invalid accepted sample interval")
    elif value["expiresAt"] != value["startedAt"] + lease:
        raise ValidationError("lease must start at sample start")
    if accepted and (
        value["lastAttemptAt"] < value["startedAt"]
        or attempted == accepted_attempt
        and value["lastAttemptAt"] != value["startedAt"]
    ):
        raise ValidationError("attempt clock is not bound to accepted sample")
    if state == "warming" and (attempted and not value["inFlight"] or accepted):
        raise ValidationError("invalid warming state")
    if state == "ready" and (result != "complete" or remaining == 0):
        raise ValidationError("failed/expired source reported ready")
    if (
        state == "warming"
        and result != "none"
        or state == "failed"
        and result not in ("partial", "failed")
        or state == "unsupported"
        and result != "unsupported"
    ):
        raise ValidationError("receipt state/result mismatch")
    return value


def ticket(value: object) -> dict:
    value = obj(value, "id", "publisherId", "state", "requestedAt", "deadlineAt", "sources")
    string(value["id"], UUID, maximum=36)
    string(value["publisherId"], UUID, maximum=36)
    state = enum(
        value["state"],
        ("accepted", "coalesced", "running", "complete", "failed", "stale_scope", "deadline"),
    )
    start = integer(value["requestedAt"])
    end = integer(value["deadlineAt"])
    if not start < end <= start + 15_000:
        raise ValidationError("invalid refresh deadline")
    rows = array(value["sources"], maximum=32)
    if not rows:
        raise ValidationError("empty refresh scope")
    seen = set()
    states = []
    for row in rows:
        row = obj(row, "hostId", "source", "state", "attempt", "error")
        key = (string(row["hostId"], HOST), enum(row["source"], ("owner", "desktop")))
        if key in seen:
            raise ValidationError("duplicate refresh scope")
        seen.add(key)
        child = enum(
            row["state"], ("pending", "running", "complete", "failed", "stale_scope", "deadline")
        )
        states.append(child)
        nullable(row["attempt"], integer)
        if child == "complete" and (row["attempt"] is None or row["attempt"] == 0):
            raise ValidationError("completed refresh lacks native attempt")
        issue = error(row["error"])
        if (child in ("failed", "stale_scope", "deadline")) != (issue is not None):
            raise ValidationError("refresh result/error mismatch")
    if state == "complete" and any(child != "complete" for child in states):
        raise ValidationError("partial success reported complete")
    if state in ("complete", "failed", "stale_scope", "deadline") and any(
        child in ("pending", "running") for child in states
    ):
        raise ValidationError("terminal ticket has pending work")
    if state == "failed" and all(child == "complete" for child in states):
        raise ValidationError("failed ticket has only successes")
    if state in ("accepted", "coalesced", "running") and all(
        child not in ("pending", "running") for child in states
    ):
        raise ValidationError("nonterminal ticket has no outstanding work")
    encode_document(value, limit=16_384)
    return value


def validate_service_frame(value: object) -> dict:
    validate_tree(value)
    value = obj(
        value,
        "protocol",
        "schemaVersion",
        "kind",
        "publisherId",
        "source",
        "clock",
        "encodedAt",
        "sequence",
        "viewRevision",
        "receipt",
        "snapshot",
        "requestId",
        "error",
        "ticket",
    )
    if (
        value["protocol"] != SERVICE_PROTOCOL
        or type(value["schemaVersion"]) is not int
        or value["schemaVersion"] != 1
    ):
        raise ValidationError("unsupported service protocol")
    kind = enum(
        value["kind"], ("status", "view", "heartbeat", "gap", "resync", "error", "refresh_result")
    )
    publisher = string(value["publisherId"], UUID, maximum=36)
    owner = source(value["source"])
    domain = clock(value["clock"])
    now = integer(value["encodedAt"])
    integer(value["sequence"])
    integer(value["viewRevision"])
    nullable(value["requestId"], lambda item: string(item, TOKEN, maximum=64))
    error(value["error"])
    evidence = receipt(value["receipt"])
    snapshot = value["snapshot"]
    if snapshot is not None:
        validate_observation(snapshot)
        if (
            scope_key(snapshot["source"]) != scope_key(owner)
            or snapshot["sample"]["coverage"] != "complete"
        ):
            raise ValidationError("invalid retained owner snapshot")
        if snapshot["capabilities"]["panes"] or snapshot["capabilities"]["options"]:
            raise ValidationError("expanded service metadata profile")
    if evidence["state"] == "warming" and snapshot is not None:
        raise ValidationError("warming source has an authoritative snapshot")
    if evidence["state"] == "ready":
        if snapshot is None or clock_key(snapshot["clock"]) != clock_key(domain):
            raise ValidationError("ready source has no same-clock sample")
        sampled = snapshot["sample"]
        if (
            sampled["startedAt"] != evidence["startedAt"]
            or not sampled["finishedAt"] <= evidence["acceptedAt"] <= now
        ):
            raise ValidationError("receipt is not bound to accepted native sample")
        if evidence["remainingMs"] != max(0, evidence["expiresAt"] - now):
            raise ValidationError("incorrect encoded remaining validity")
    if value["ticket"] is not None:
        ticket(value["ticket"])
        if value["ticket"]["publisherId"] != publisher:
            raise ValidationError("ticket publisher mismatch")
    if kind == "refresh_result" and value["ticket"] is None:
        raise ValidationError("refresh result lacks ticket")
    if kind == "error" and value["error"] is None:
        raise ValidationError("protocol error lacks diagnostic")
    overhead = dict(value)
    overhead["snapshot"] = None
    encode_document(overhead, limit=ENVELOPE_LIMIT)
    encode_document(value, limit=DOCUMENT_LIMIT + ENVELOPE_LIMIT)
    return value


def validate_request(value: object) -> dict:
    validate_tree(value)
    value = obj(value, "protocol", "schemaVersion", "operation", "requestId")
    protocol = enum(value["protocol"], (SERVICE_PROTOCOL, FLEET_PROTOCOL))
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValidationError("unsupported request version")
    operation = enum(
        value["operation"], ("status", "snapshot", "watch", "probe", "refresh", "refresh_status")
    )
    string(value["requestId"], TOKEN, maximum=64)
    if protocol == SERVICE_PROTOCOL:
        string(obj(value, "expectedHost")["expectedHost"], HOST)
    else:
        string(obj(value, "contextId")["contextId"], CONTEXT, maximum=32)
    if "publisherId" in value:
        string(value["publisherId"], UUID, maximum=36)
    if "meshRevision" in value:
        nullable(value["meshRevision"], lambda child: string(child, SHA256, maximum=71))
    for key, pattern in (("expectedHost", HOST), ("contextId", CONTEXT)):
        if key in value:
            string(value[key], pattern)
    if operation == "refresh" or "sources" in value:
        scopes = array(obj(value, "sources")["sources"], maximum=32)
        if not scopes:
            raise ValidationError("empty refresh request")
        seen = set()
        for scope in scopes:
            scope = obj(scope, "hostId", "source")
            pair = (string(scope["hostId"], HOST), enum(scope["source"], ("owner", "desktop")))
            if pair in seen or (
                protocol == SERVICE_PROTOCOL and pair != (value["expectedHost"], "owner")
            ):
                raise ValidationError("unsupported refresh scope")
            seen.add(pair)
    if operation == "refresh_status" or "ticketId" in value:
        string(obj(value, "ticketId")["ticketId"], UUID, maximum=36)
        string(obj(value, "publisherId")["publisherId"], UUID, maximum=36)
    encode_document(value, limit=16_384)
    return value


def remote_expiry(sent_at: int, received_at: int, remaining_ms: int, margin_ms: int = 100) -> int:
    integer(sent_at)
    integer(received_at)
    integer(remaining_ms, maximum=OWNER_LEASE_MS)
    integer(margin_ms, maximum=OWNER_LEASE_MS)
    if not sent_at <= received_at <= sent_at + 2000:
        raise ValidationError("invalid or expired probe round trip")
    expiry = received_at + max(0, remaining_ms - (received_at - sent_at) - margin_ms)
    return integer(expiry)


def viewer(value: object) -> dict:
    value = obj(value, "state", "reason")
    state = enum(value["state"], ("open", "none", "unknown"))
    nullable(value["reason"], lambda child: string(child, TOKEN, maximum=64))
    if state == "open":
        enum(obj(value, "confidence")["confidence"], ("confirmed", "matched"))
    elif "confidence" in value:
        raise ValidationError("non-open viewer has confidence")
    if "viewerId" in value or "closeSafe" in value:
        raise ValidationError("action authority in passive viewer")
    return value


def validate_fleet_view(value: object) -> dict:
    validate_tree(value)
    value = obj(
        value,
        "protocol",
        "schemaVersion",
        "readerId",
        "clock",
        "contextId",
        "encodedAt",
        "viewRevision",
        "mesh",
        "desktop",
        "hosts",
        "ticket",
        "error",
    )
    if (
        value["protocol"] != FLEET_PROTOCOL
        or type(value["schemaVersion"]) is not int
        or value["schemaVersion"] != 1
    ):
        raise ValidationError("unsupported fleet protocol")
    string(value["readerId"], UUID, maximum=36)
    clock(value["clock"])
    context = string(value["contextId"], CONTEXT, maximum=32)
    now = integer(value["encodedAt"])
    integer(value["viewRevision"])
    error(value["error"])
    mesh = obj(value["mesh"], "revision", "state", "localHostId")
    nullable(mesh["revision"], lambda item: string(item, SHA256, maximum=71))
    mesh_state = enum(mesh["state"], ("ready", "local_only", "warming", "unavailable", "capacity"))
    local_host = nullable(mesh["localHostId"], lambda item: string(item, HOST))
    desktop = obj(
        value["desktop"],
        "contextId",
        "epoch",
        "state",
        "startedAt",
        "acceptedAt",
        "expiresAt",
        "inputHash",
        "error",
    )
    if desktop["contextId"] != context:
        raise ValidationError("desktop context mismatch")
    integer(desktop["epoch"])
    desktop_state = enum(desktop["state"], ("warming", "ready", "failed", "unsupported", "expired"))
    for key in ("startedAt", "acceptedAt", "expiresAt"):
        nullable(desktop[key], integer)
    nullable(desktop["inputHash"], lambda item: string(item, SHA256, maximum=71))
    error(desktop["error"])
    if desktop_state == "ready":
        if any(
            desktop[key] is None for key in ("startedAt", "acceptedAt", "expiresAt", "inputHash")
        ):
            raise ValidationError("ready desktop has no accepted receipt")
        if (
            not desktop["startedAt"]
            <= desktop["acceptedAt"]
            <= now
            < desktop["expiresAt"]
            <= desktop["startedAt"] + 10_000
        ):
            raise ValidationError("invalid desktop lease")
        if desktop["error"] is not None:
            raise ValidationError("ready desktop has a failed receipt")
    hosts = array(value["hosts"], maximum=128)
    seen = set()
    local_count = 0
    if mesh_state in ("ready", "local_only") and len(hosts) > 16:
        raise ValidationError("prepared host capacity exceeded")
    for index, host in enumerate(hosts):
        host = obj(host, "hostId", "display", "local", "owner", "sessions")
        host_id = string(host["hostId"], HOST)
        string(host["display"])
        if host_id in seen:
            raise ValidationError("duplicate fleet host")
        seen.add(host_id)
        local = boolean(host["local"])
        local_count += local
        if local and (index != 0 or host_id != local_host):
            raise ValidationError("local host/order mismatch")
        owner = obj(
            host["owner"],
            "source",
            "clock",
            "publisherId",
            "encodedAt",
            "serverGeneration",
            "sample",
            "receipt",
            "transport",
            "localExpiry",
            "proof",
            "error",
        )
        transport = enum(
            owner["transport"], ("local", "connecting", "ready", "failed", "absent", "incompatible")
        )
        error(owner["error"])
        generation = nullable(owner["serverGeneration"], string)
        expiry = nullable(owner["localExpiry"], integer)
        evidence = None if owner["receipt"] is None else receipt(owner["receipt"])
        if owner["source"] is not None and source(owner["source"])["hostId"] != host_id:
            raise ValidationError("fleet source relabeling")
        nullable(owner["clock"], clock)
        nullable(owner["publisherId"], lambda item: string(item, UUID, maximum=36))
        nullable(owner["encodedAt"], integer)
        nullable(owner["sample"], sample)
        proof = owner["proof"]
        if proof is not None:
            proof = obj(proof, "requestId", "sentAt", "receivedAt", "remainingMs", "marginMs")
            string(proof["requestId"], TOKEN, maximum=64)
            bound = remote_expiry(
                proof["sentAt"], proof["receivedAt"], proof["remainingMs"], proof["marginMs"]
            )
            if proof["receivedAt"] > now or proof["marginMs"] < 100:
                raise ValidationError("future or insufficiently conservative proof")
            if expiry is not None and expiry > bound:
                raise ValidationError("remote lease exceeds conservative proof")
        current = (
            evidence is not None
            and evidence["state"] == "ready"
            and expiry is not None
            and expiry > now
        )
        if current:
            if (
                mesh_state not in ("ready", "local_only")
                or owner["source"] is None
                or owner["clock"] is None
                or owner["publisherId"] is None
                or owner["sample"] is None
            ):
                raise ValidationError("current fleet owner lacks provenance/authority")
            if (
                owner["sample"]["coverage"] != "complete"
                or owner["sample"]["startedAt"] != evidence["startedAt"]
                or owner["encodedAt"] is None
                or not owner["sample"]["finishedAt"] <= evidence["acceptedAt"] <= owner["encodedAt"]
            ):
                raise ValidationError("fleet sample/receipt mismatch")
            if owner["error"] is not None or evidence["remainingMs"] != max(
                0, evidence["expiresAt"] - owner["encodedAt"]
            ):
                raise ValidationError("invalid current owner source projection")
            if local:
                if (
                    transport != "local"
                    or clock_key(owner["clock"]) != clock_key(value["clock"])
                    or expiry > evidence["expiresAt"]
                ):
                    raise ValidationError("invalid local owner lease")
            elif (
                transport != "ready"
                or proof is None
                or proof["remainingMs"] != evidence["remainingMs"]
            ):
                raise ValidationError("unproven remote current owner")
        ids = set()
        for row in array(host["sessions"], maximum=256):
            session(row)
            ref = reference(row)
            if ref[0] != host_id or ref[1] != generation or ref[2] in ids:
                raise ValidationError("fleet row identity conflict")
            ids.add(ref[2])
            if "panes" in row or "options" in row:
                raise ValidationError("expanded fleet metadata profile")
            presence = viewer(obj(row, "localViewer")["localViewer"])
            if presence["state"] in ("open", "none") and (not current or desktop_state != "ready"):
                raise ValidationError("viewer membership lacks independent current evidence")
            if presence.get("confidence") == "matched" and (
                row["attachedClients"] is None or row["attachedClients"] == 0
            ):
                raise ValidationError("qualified match lacks owner attachment evidence")
    if mesh_state in ("ready", "local_only") and (local_count != 1 or local_host not in seen):
        raise ValidationError("missing logical local host")
    if mesh_state == "local_only" and (len(hosts) != 1 or mesh["revision"] is not None):
        raise ValidationError("invalid local-only composition")
    if mesh_state == "ready" and mesh["revision"] is None:
        raise ValidationError("ready mesh lacks route revision")
    if value["ticket"] is not None:
        ticket(value["ticket"])
        if value["ticket"]["publisherId"] != value["readerId"]:
            raise ValidationError("fleet ticket incarnation mismatch")
    encode_document(value, limit=DOCUMENT_LIMIT)
    return value


def validate_fleet_frame(value: object) -> dict:
    validate_tree(value)
    value = obj(
        value,
        "protocol",
        "schemaVersion",
        "kind",
        "readerId",
        "clock",
        "contextId",
        "encodedAt",
        "sequence",
        "viewRevision",
        "snapshot",
        "requestId",
        "error",
        "ticket",
    )
    if (
        value["protocol"] != FLEET_PROTOCOL
        or type(value["schemaVersion"]) is not int
        or value["schemaVersion"] != 1
    ):
        raise ValidationError("unsupported fleet frame protocol")
    kind = enum(
        value["kind"], ("status", "view", "heartbeat", "gap", "resync", "error", "refresh_result")
    )
    string(value["readerId"], UUID, maximum=36)
    clock(value["clock"])
    string(value["contextId"], CONTEXT, maximum=32)
    integer(value["encodedAt"])
    integer(value["sequence"])
    integer(value["viewRevision"])
    nullable(value["requestId"], lambda child: string(child, TOKEN, maximum=64))
    error(value["error"])
    snapshot = value["snapshot"]
    if snapshot is not None:
        validate_fleet_view(snapshot)
        if any(
            snapshot[key] != value[key]
            for key in ("readerId", "contextId", "encodedAt", "viewRevision")
        ) or clock_key(snapshot["clock"]) != clock_key(value["clock"]):
            raise ValidationError("fleet frame/view binding mismatch")
    if value["ticket"] is not None:
        ticket(value["ticket"])
        if value["ticket"]["publisherId"] != value["readerId"]:
            raise ValidationError("fleet frame ticket incarnation mismatch")
    if (
        kind == "error"
        and value["error"] is None
        or kind == "refresh_result"
        and value["ticket"] is None
    ):
        raise ValidationError("missing fleet control outcome")
    overhead = dict(value)
    overhead["snapshot"] = None
    encode_document(overhead, limit=ENVELOPE_LIMIT)
    encode_document(value, limit=DOCUMENT_LIMIT + ENVELOPE_LIMIT)
    return value
