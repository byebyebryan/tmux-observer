"""Pure retained local display associations; no fresh desktop or action claim."""

from tmux_observer._native_validation import reference
from tmux_observer._validation_common import (
    CONTEXT,
    HOST,
    TOKEN,
    UUID,
    ValidationError,
    array,
    clock,
    closed_error,
    enum,
    exact,
    integer,
    nullable,
    string,
    version,
)
from tmux_observer._wire import DOCUMENT_LIMIT, _encode_after_validation, validate_tree

BINDINGS_PROTOCOL = "tmux-observer.bindings.v1"


def validate_bindings(value):
    plain = validate_tree(value)
    exact(
        value,
        "protocol",
        "schemaVersion",
        "clock",
        "contextId",
        "epoch",
        "encodedAt",
        "hostId",
        "publisherId",
        "serverGeneration",
        "receipt",
        "rows",
    )
    version(value, BINDINGS_PROTOCOL)
    exact(value["clock"], "bootId", "timeNamespace")
    clock(value["clock"])
    string(value["contextId"], CONTEXT, maximum=32)
    integer(value["epoch"])
    now = integer(value["encodedAt"])
    host = string(value["hostId"], HOST)
    string(value["publisherId"], UUID, maximum=36)
    generation = nullable(value["serverGeneration"], string)
    receipt = exact(
        value["receipt"],
        "state",
        "preparedAt",
        "associationStartedAt",
        "ownerExpiresAt",
        "associationExpiresAt",
        "expiresAt",
        "error",
    )
    state = enum(receipt["state"], ("ready", "unavailable", "unsupported", "expired"))
    keys = (
        "preparedAt",
        "associationStartedAt",
        "ownerExpiresAt",
        "associationExpiresAt",
        "expiresAt",
    )
    for key in keys:
        nullable(receipt[key], integer)
    problem = closed_error(receipt["error"])
    if state == "ready":
        if any(receipt[key] is None for key in keys) or problem is not None:
            raise ValidationError("ready bindings lack native receipts")
        if not (
            receipt["associationStartedAt"]
            <= receipt["preparedAt"]
            <= now
            < receipt["expiresAt"]
            <= min(receipt["ownerExpiresAt"], receipt["associationExpiresAt"])
            and receipt["associationExpiresAt"] <= receipt["associationStartedAt"] + 10000
        ):
            raise ValidationError("invalid retained native dependency interval")
    elif problem is None:
        raise ValidationError("unavailable bindings lack diagnostic")
    refs, ids = set(), set()
    for row in array(value["rows"], maximum=256):
        exact(row, "sessionRef", "attachedClients", "association")
        exact(row["sessionRef"], "hostId", "serverGeneration", "sessionId", "createdAt")
        ref = reference(row["sessionRef"])
        if ref[0] != host or ref[1] != generation or ref in refs or ref[2] in ids:
            raise ValidationError("retained reference outside local source")
        refs.add(ref)
        ids.add(ref[2])
        attached = nullable(row["attachedClients"], integer)
        association = exact(row["association"], "state", "resolvedAt", "reason")
        present = enum(association["state"], ("open", "none", "unknown"))
        resolved = nullable(association["resolvedAt"], integer)
        reason = string(association["reason"], TOKEN, maximum=64)
        if present in ("open", "none") and state != "ready":
            raise ValidationError("retained association lacks current native dependencies")
        if present == "open":
            if (
                attached is None
                or attached == 0
                or resolved is None
                or not resolved <= receipt["preparedAt"]
                or reason != "retained_native_association"
            ):
                raise ValidationError("invalid retained positive")
        elif present == "none":
            if attached != 0 or resolved is not None or reason != "no_native_clients":
                raise ValidationError("retained negative requires zero current clients")
        elif resolved is not None:
            raise ValidationError("unknown binding has a resolved association")
    _encode_after_validation(value, limit=DOCUMENT_LIMIT, plain=plain)
    return value


def validate_fleet_bindings(value, host, *, context_id, clock_value, now):
    """Bind the known Fleet v1 extension to its enclosing native source."""
    validate_bindings(value)
    owner = host["owner"]
    if (
        not host["local"]
        or value["hostId"] != host["hostId"]
        or value["publisherId"] != owner["publisherId"]
        or value["serverGeneration"] != owner["serverGeneration"]
        or value["contextId"] != context_id
        or value["clock"] != clock_value
        or value["encodedAt"] > now
    ):
        raise ValidationError("retained bindings changed enclosing scope")
    expected = {reference(row): row["attachedClients"] for row in host["sessions"]}
    actual = {reference(row["sessionRef"]): row["attachedClients"] for row in value["rows"]}
    if actual != expected:
        raise ValidationError("retained bindings changed native coverage/counts")
    if value["receipt"]["state"] == "ready" and (
        owner["localExpiry"] is None
        or value["receipt"]["ownerExpiresAt"] > owner["localExpiry"]
        or value["receipt"]["expiresAt"] <= now
        or owner["receipt"] is None
        or owner["receipt"]["state"] != "ready"
        or owner["transport"] != "local"
    ):
        raise ValidationError("retained bindings exceed enclosing owner authority")
    return value


__all__ = ["BINDINGS_PROTOCOL", "validate_bindings", "validate_fleet_bindings"]
