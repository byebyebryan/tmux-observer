"""Supported pure owner-delivery contract (C2), without Fleet definitions."""

from ._delivery_validation import SERVICE_PROTOCOL, remote_expiry, validate_service_frame
from ._validation_common import ValidationError

__all__ = [
    "SERVICE_PROTOCOL",
    "ValidationError",
    "remote_expiry",
    "validate_operation_error",
    "validate_request",
    "validate_service_frame",
]


def validate_request(value):
    from tmux_observer._request_validation import validate_request as validate

    validate(value)
    if value["protocol"] != SERVICE_PROTOCOL:
        raise ValidationError("wrong request domain")
    return value


def validate_operation_error(value):
    from tmux_observer._request_validation import validate_operation_error as validate

    validate(value)
    if value["protocol"] != SERVICE_PROTOCOL:
        raise ValidationError("wrong error domain")
    return value
