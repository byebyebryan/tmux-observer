"""Pure optional host-local native attachment profile and delivery contract.

These records never enter the default remote owner export. Process identities
are scoped by source UID, kernel boot and PID namespace, not by numeric PID alone.
"""

from ._delivery_validation import receipt
from ._native_validation import reference, sample, scope_key, source
from ._validation_common import (
    HOST,
    TOKEN,
    UUID,
    ValidationError,
    array,
    clock,
    clock_key,
    exact,
    integer,
    nullable,
    positive,
    string,
    version,
)
from ._validation_common import (
    closed_error as error,
)
from ._wire import ENVELOPE_LIMIT, encode_document, validate_tree

ATTACHMENTS_PROTOCOL = "tmux-observer.attachments.v1"
ATTACHMENT_DELIVERY_PROTOCOL = "tmux-observer.attachments-delivery.v1"
ATTACHMENTS_LIMIT = 256 * 1024
CLIENT_LIMIT = 512
PID_NAMESPACE = r"pid:[0-9]+"


def validate_attachments(value):
    validate_tree(value)
    value = exact(
        value,
        "protocol",
        "schemaVersion",
        "source",
        "clock",
        "pidNamespace",
        "sample",
        "serverGeneration",
        "sessions",
        "clients",
    )
    version(value, ATTACHMENTS_PROTOCOL)
    exact(value["source"], "hostId", "uid", "server", "nativeHostname")
    exact(value["clock"], "bootId", "timeNamespace")
    owner = source(value["source"])
    clock(value["clock"])
    string(value["pidNamespace"], PID_NAMESPACE, maximum=64)
    exact(value["sample"], "startedAt", "finishedAt", "observedAt", "coverage", "error")
    error(value["sample"]["error"])
    sampled = sample(value["sample"])
    generation = nullable(value["serverGeneration"], string)
    sessions = array(value["sessions"], maximum=256)
    clients = array(value["clients"], maximum=CLIENT_LIMIT)
    if sampled["coverage"] != "complete" and (generation is not None or sessions or clients):
        raise ValidationError("incomplete association profile has authoritative facts")
    if generation is None and (sessions or clients):
        raise ValidationError("absent server has native associations")
    refs = set()
    ids = set()
    for row in sessions:
        exact(row, "hostId", "serverGeneration", "sessionId", "createdAt")
        ref = reference(row)
        if ref[:2] != (owner["hostId"], generation) or ref[2] in ids:
            raise ValidationError("association reference conflicts with source")
        refs.add(ref)
        ids.add(ref[2])
    pids = set()
    for row in clients:
        row = exact(row, "sessionRef", "clientPid", "processStartTicks")
        exact(row["sessionRef"], "hostId", "serverGeneration", "sessionId", "createdAt")
        if reference(row["sessionRef"]) not in refs:
            raise ValidationError("client outside accepted association roster")
        pid = positive(row["clientPid"], 2**31 - 1)
        positive(row["processStartTicks"])
        if pid in pids:
            raise ValidationError("duplicate native client")
        pids.add(pid)
    encode_document(value, limit=ATTACHMENTS_LIMIT)
    return value


def validate_attachment_delivery(value):
    validate_tree(value)
    value = exact(
        value,
        "protocol",
        "schemaVersion",
        "publisherId",
        "requestId",
        "source",
        "clock",
        "pidNamespace",
        "encodedAt",
        "receipt",
        "snapshot",
        "error",
    )
    version(value, ATTACHMENT_DELIVERY_PROTOCOL)
    string(value["publisherId"], UUID, maximum=36)
    nullable(value["requestId"], lambda item: string(item, TOKEN, maximum=64))
    exact(value["source"], "hostId", "uid", "server", "nativeHostname")
    exact(value["clock"], "bootId", "timeNamespace")
    owner = source(value["source"])
    domain = clock(value["clock"])
    string(value["pidNamespace"], PID_NAMESPACE, maximum=64)
    now = integer(value["encodedAt"])
    evidence = receipt(value["receipt"])
    problem = error(value["error"])
    snapshot = value["snapshot"]
    if snapshot is not None:
        validate_attachments(snapshot)
        if (
            scope_key(snapshot["source"]) != scope_key(owner)
            or clock_key(snapshot["clock"]) != clock_key(domain)
            or snapshot["pidNamespace"] != value["pidNamespace"]
            or snapshot["sample"]["coverage"] != "complete"
        ):
            raise ValidationError("invalid retained local association scope")
    if evidence["state"] == "warming" and snapshot is not None:
        raise ValidationError("warming associations have a snapshot")
    if evidence["state"] == "ready":
        if snapshot is None or problem is not None:
            raise ValidationError("ready associations lack successful native sample")
        sampled = snapshot["sample"]
        if (
            sampled["startedAt"] != evidence["startedAt"]
            or not sampled["finishedAt"] <= evidence["acceptedAt"] <= now
            or evidence["remainingMs"] != max(0, evidence["expiresAt"] - now)
        ):
            raise ValidationError("association receipt is not bound to native sample")
    if evidence["state"] in ("failed", "unsupported") and problem is None:
        raise ValidationError("failed association source lacks diagnostic")
    overhead = {**value, "snapshot": None}
    encode_document(overhead, limit=ENVELOPE_LIMIT)
    encode_document(value, limit=ATTACHMENTS_LIMIT + ENVELOPE_LIMIT)
    return value


def validate_attachment_request(value):
    validate_tree(value)
    value = exact(value, "protocol", "schemaVersion", "operation", "requestId", "expectedHost")
    version(value, ATTACHMENT_DELIVERY_PROTOCOL)
    if value["operation"] != "snapshot":
        raise ValidationError("local association endpoint supports cached snapshot only")
    string(value["requestId"], TOKEN, maximum=64)
    string(value["expectedHost"], HOST)
    encode_document(value, limit=ENVELOPE_LIMIT)
    return value


def validate_attachment_error(value):
    validate_tree(value)
    keys = ["protocol", "schemaVersion", "kind", "error"]
    if isinstance(value, dict) and "requestId" in value:
        keys.append("requestId")
        nullable(value["requestId"], lambda item: string(item, TOKEN, maximum=64))
    value = exact(value, *keys)
    version(value, ATTACHMENT_DELIVERY_PROTOCOL)
    if value["kind"] != "operation_error" or error(value["error"]) is None:
        raise ValidationError("invalid local attachment operation error")
    encode_document(value, limit=ENVELOPE_LIMIT)
    return value


__all__ = [
    "ATTACHMENTS_LIMIT",
    "ATTACHMENTS_PROTOCOL",
    "ATTACHMENT_DELIVERY_PROTOCOL",
    "CLIENT_LIMIT",
    "validate_attachment_delivery",
    "validate_attachment_error",
    "validate_attachment_request",
    "validate_attachments",
]
