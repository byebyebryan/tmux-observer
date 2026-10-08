"""Bounded generic framing of known read protocols; no domain implementations."""

from ._delivery_validation import SERVICE_PROTOCOL
from ._native_validation import OBSERVATION_PROTOCOL
from ._validation_common import (
    CONTEXT,
    HOST,
    SHA256,
    TOKEN,
    UUID,
    ValidationError,
    array,
    enum,
    error,
    nullable,
    obj,
    string,
)
from ._wire import encode_document, validate_tree

# Routing discriminator only; semantic Fleet models live in client.contract.
FLEET_PROTOCOL = "tmux-observer.fleet.v1"


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
