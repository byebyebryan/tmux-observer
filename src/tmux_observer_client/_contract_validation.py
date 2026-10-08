"""Pure fleet contract; imports no implementations."""

from tmux_observer._delivery_validation import receipt, remote_expiry, ticket
from tmux_observer._native_validation import reference, sample, session, source
from tmux_observer._validation_common import (
    CONTEXT,
    HOST,
    SHA256,
    TOKEN,
    UUID,
    ValidationError,
    array,
    boolean,
    clock,
    clock_key,
    enum,
    error,
    integer,
    nullable,
    obj,
    string,
)
from tmux_observer._wire import DOCUMENT_LIMIT, ENVELOPE_LIMIT, encode_document, validate_tree

FLEET_PROTOCOL = "tmux-observer.fleet.v1"


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
