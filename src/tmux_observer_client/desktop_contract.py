"""Pure desktop association contract (C3); no compositor or process reads."""

from tmux_observer._native_validation import reference
from tmux_observer._validation_common import (
    CONTEXT,
    HOST,
    SHA256,
    UUID,
    ValidationError,
    array,
    boolean,
    clock,
    enum,
    exact,
    integer,
    nullable,
    string,
    version,
)
from tmux_observer._validation_common import (
    closed_error as error,
)
from tmux_observer._wire import (
    DOCUMENT_LIMIT,
    _encode_after_validation,
    validate_tree,
)

DESKTOP_PROTOCOL = "tmux-observer.desktop.v1"
EVIDENCE = (
    "current_native_association",
    "qualified_title",
    "launch_reference",
    "absence",
    "unknown",
)


def validate_desktop(value):
    plain = validate_tree(value)
    value = exact(
        value,
        "protocol",
        "schemaVersion",
        "clock",
        "contextId",
        "epoch",
        "encodedAt",
        "receipt",
        "dependencies",
        "rows",
    )
    version(value, DESKTOP_PROTOCOL)
    exact(value["clock"], "bootId", "timeNamespace")
    clock(value["clock"])
    string(value["contextId"], CONTEXT, maximum=32)
    integer(value["epoch"])
    now = integer(value["encodedAt"])
    sampled = exact(
        value["receipt"], "state", "startedAt", "acceptedAt", "expiresAt", "inputHash", "error"
    )
    state = enum(sampled["state"], ("warming", "ready", "failed", "unsupported", "expired"))
    for key in ("startedAt", "acceptedAt", "expiresAt"):
        nullable(sampled[key], integer)
    nullable(sampled["inputHash"], lambda item: string(item, SHA256, maximum=71))
    problem = error(sampled["error"])
    if state == "ready":
        if any(
            sampled[key] is None for key in ("startedAt", "acceptedAt", "expiresAt", "inputHash")
        ):
            raise ValidationError("ready desktop lacks receipt")
        if (
            not sampled["startedAt"]
            <= sampled["acceptedAt"]
            <= now
            < sampled["expiresAt"]
            <= sampled["startedAt"] + 10000
            or problem is not None
        ):
            raise ValidationError("invalid desktop receipt")
    elif state in ("failed", "unsupported") and problem is None:
        raise ValidationError("failed desktop lacks diagnostic")
    elif state == "warming" and any(
        sampled[key] is not None for key in ("startedAt", "acceptedAt", "expiresAt", "inputHash")
    ):
        raise ValidationError("warming desktop has accepted facts")
    dependencies = {}
    for dependency in array(value["dependencies"], maximum=16):
        dependency = exact(
            dependency,
            "hostId",
            "local",
            "publisherId",
            "serverGeneration",
            "ownerExpiresAt",
            "associationExpiresAt",
        )
        host = string(dependency["hostId"], HOST)
        local = boolean(dependency["local"])
        string(dependency["publisherId"], UUID, maximum=36)
        nullable(dependency["serverGeneration"], string)
        integer(dependency["ownerExpiresAt"])
        nullable(dependency["associationExpiresAt"], integer)
        if host in dependencies or not local and dependency["associationExpiresAt"] is not None:
            raise ValidationError("duplicate dependency or remote PID association")
        dependencies[host] = dependency
    if sum(item["local"] for item in dependencies.values()) > 1:
        raise ValidationError("multiple local association scopes")
    refs = set()
    session_ids = set()
    counts = {}
    for row in array(value["rows"], maximum=16 * 256):
        row = exact(row, "sessionRef", "attachedClients", "presence")
        exact(row["sessionRef"], "hostId", "serverGeneration", "sessionId", "createdAt")
        ref = reference(row["sessionRef"])
        dependency = dependencies.get(ref[0])
        if (
            ref in refs
            or (ref[0], ref[2]) in session_ids
            or dependency is None
            or ref[1] != dependency["serverGeneration"]
        ):
            raise ValidationError("desktop reference outside accepted inputs")
        refs.add(ref)
        session_ids.add((ref[0], ref[2]))
        counts[ref[0]] = counts.get(ref[0], 0) + 1
        if counts[ref[0]] > 256:
            raise ValidationError("desktop owner row capacity exceeded")
        attached = nullable(row["attachedClients"], integer)
        presence = exact(row["presence"], "state", "confidence", "evidence", "reason")
        present = enum(presence["state"], ("open", "none", "unknown"))
        confidence = nullable(
            presence["confidence"], lambda item: enum(item, ("confirmed", "matched"))
        )
        evidence = enum(presence["evidence"], EVIDENCE)
        nullable(
            presence["reason"],
            lambda item: string(item, r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", maximum=64),
        )
        if present in ("open", "none") and (
            state != "ready" or dependency["ownerExpiresAt"] <= now
        ):
            raise ValidationError("desktop claim lacks independent current owner")
        if (
            present == "none"
            and dependency["local"]
            and (
                dependency["associationExpiresAt"] is None
                or dependency["associationExpiresAt"] <= now
            )
        ):
            raise ValidationError("local absence lacks complete current native join")
        if present == "open":
            if attached is None or attached == 0 or confidence is None:
                raise ValidationError("open claim lacks native attachments")
            if evidence == "current_native_association":
                if (
                    confidence != "confirmed"
                    or not dependency["local"]
                    or dependency["associationExpiresAt"] is None
                    or dependency["associationExpiresAt"] <= now
                ):
                    raise ValidationError("confirmation lacks current local native join")
            elif evidence not in ("qualified_title", "launch_reference") or confidence != "matched":
                raise ValidationError("launch/title evidence cannot confirm current binding")
        elif confidence is not None or evidence != ("absence" if present == "none" else "unknown"):
            raise ValidationError("invalid non-open evidence")
    _encode_after_validation(value, limit=DOCUMENT_LIMIT, plain=plain)
    return value


def legacy_viewer(presence, *, legacy_launch_confirmation=False):
    """Explicit Fleet/Tmux v1 projection; callers select legacy launch semantics."""
    result = {"state": presence["state"], "reason": presence["reason"]}
    if presence["state"] == "open":
        result["confidence"] = (
            "confirmed"
            if legacy_launch_confirmation and presence["evidence"] == "launch_reference"
            else presence["confidence"]
        )
    return result


__all__ = ["DESKTOP_PROTOCOL", "legacy_viewer", "validate_desktop"]
