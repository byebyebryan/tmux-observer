"""Pure observation contract; imports no implementations."""

from ._validation_common import (
    HOST,
    OPTION,
    SESSION,
    ValidationError,
    array,
    boolean,
    clock,
    enum,
    error,
    integer,
    nullable,
    obj,
    string,
)
from ._wire import DOCUMENT_LIMIT, _encode_after_validation, validate_tree

OBSERVATION_PROTOCOL = "tmux-observer.observation.v1"


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


def scope_key(value: dict) -> tuple:
    return value["hostId"], value["uid"], value["server"]


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
    plain = validate_tree(value)
    return _observation_after_tree(value, plain=plain)


def _observation_after_tree(value: object, *, plain: bool) -> dict:
    """Check semantics/bytes after a complete enclosing plain-tree check."""
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
    _encode_after_validation(value, limit=DOCUMENT_LIMIT, plain=plain)
    return value
