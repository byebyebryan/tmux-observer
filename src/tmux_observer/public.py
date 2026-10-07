"""Supported pure models, strict framing and semantic protocol validators.

All clock values are supplied by the caller. Importing this facade executes no
native commands, network/IPC operations, service activation or lifecycle code.
"""

from ._models import Pane, Session, SessionReference
from ._validation import (
    FLEET_PROTOCOL,
    OBSERVATION_PROTOCOL,
    SERVICE_PROTOCOL,
    ValidationError,
    remote_expiry,
    validate_fleet_frame,
    validate_fleet_view,
    validate_observation,
    validate_operation_error,
    validate_request,
    validate_service_frame,
)
from ._wire import (
    DOCUMENT_LIMIT,
    FRAME_LIMIT,
    REQUEST_LIMIT,
    WireError,
    decode_document,
    encode_document,
)

__all__ = [
    "DOCUMENT_LIMIT",
    "FLEET_PROTOCOL",
    "FRAME_LIMIT",
    "OBSERVATION_PROTOCOL",
    "REQUEST_LIMIT",
    "SERVICE_PROTOCOL",
    "Pane",
    "Session",
    "SessionReference",
    "ValidationError",
    "WireError",
    "decode_document",
    "encode_document",
    "remote_expiry",
    "validate_fleet_frame",
    "validate_fleet_view",
    "validate_observation",
    "validate_operation_error",
    "validate_request",
    "validate_service_frame",
]
