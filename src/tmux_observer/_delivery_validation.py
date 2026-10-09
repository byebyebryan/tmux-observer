"""Pure service contract; imports no implementations."""

from ._native_validation import (
    _observation_after_tree,
    scope_key,
    source,
    validate_observation,
)
from ._validation_common import (
    HOST,
    OWNER_LEASE_MS,
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
from ._wire import (
    DOCUMENT_LIMIT,
    ENVELOPE_LIMIT,
    _decode_and_check,
    _encode_after_validation,
    encode_document,
    validate_tree,
)

SERVICE_PROTOCOL = "tmux-observer.service.v1"


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
    return _checked_service_frame(value)[0]


def _checked_service_frame(value: object) -> tuple[dict, int, int]:
    """Return the same checked frame and its already bounded encoded sizes."""
    plain = validate_tree(value)
    return _service_after_tree(value, plain=plain)


def _decode_service_frame(raw: bytes) -> tuple[dict, int, int]:
    return _decode_and_check(raw, limit=DOCUMENT_LIMIT + ENVELOPE_LIMIT, check=_service_after_tree)


def _decode_service_input(raw: bytes) -> tuple[dict, int, int]:
    def check(value, *, plain):
        if isinstance(value, dict) and value.get("kind") == "operation_error":
            from ._request_validation import validate_operation_error

            return validate_operation_error(value), 0, 0
        return _service_after_tree(value, plain=plain)

    return _decode_and_check(raw, limit=DOCUMENT_LIMIT + ENVELOPE_LIMIT, check=check)


def _service_after_tree(value: object, *, plain: bool) -> tuple[dict, int, int]:
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
        if plain:
            _observation_after_tree(snapshot, plain=True)
        else:
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
    header_size = len(_encode_after_validation(overhead, limit=ENVELOPE_LIMIT, plain=plain))
    full_size = len(
        _encode_after_validation(value, limit=DOCUMENT_LIMIT + ENVELOPE_LIMIT, plain=plain)
    )
    return value, full_size, header_size


def remote_expiry(sent_at: int, received_at: int, remaining_ms: int, margin_ms: int = 100) -> int:
    integer(sent_at)
    integer(received_at)
    integer(remaining_ms, maximum=OWNER_LEASE_MS)
    integer(margin_ms, maximum=OWNER_LEASE_MS)
    if not sent_at <= received_at <= sent_at + 2000:
        raise ValidationError("invalid or expired probe round trip")
    expiry = received_at + max(0, remaining_ms - (received_at - sent_at) - margin_ms)
    return integer(expiry)
