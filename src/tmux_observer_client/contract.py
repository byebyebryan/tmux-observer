"""Supported pure prepared Fleet contract (C4), without transport or desktop scans."""

from tmux_observer._validation_common import ValidationError

from ._contract_validation import FLEET_PROTOCOL, validate_fleet_frame, validate_fleet_view

__all__ = [
    "FLEET_PROTOCOL",
    "ValidationError",
    "validate_fleet_frame",
    "validate_fleet_view",
    "validate_operation_error",
    "validate_request",
]


def validate_request(value):
    from tmux_observer._request_validation import validate_request as validate

    validate(value)
    if value["protocol"] != FLEET_PROTOCOL:
        raise ValidationError("wrong request domain")
    return value


def validate_operation_error(value):
    from tmux_observer._request_validation import validate_operation_error as validate

    validate(value)
    if value["protocol"] != FLEET_PROTOCOL:
        raise ValidationError("wrong error domain")
    return value
