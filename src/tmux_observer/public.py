"""Legacy public facade; new consumers use native/delivery/client.contract.

Native imports stay native. Legacy delivery/Fleet attributes are resolved only
when requested; their shape and behavior remain compatible.
"""

from .native import (
    DOCUMENT_LIMIT,
    FRAME_LIMIT,
    OBSERVATION_PROTOCOL,
    REQUEST_LIMIT,
    Pane,
    Session,
    SessionReference,
    ValidationError,
    WireError,
    decode_document,
    encode_document,
    validate_observation,
)

_LEGACY = {
    "SERVICE_PROTOCOL": "tmux_observer.delivery",
    "remote_expiry": "tmux_observer.delivery",
    "validate_service_frame": "tmux_observer.delivery",
    "FLEET_PROTOCOL": "tmux_observer_client.contract",
    "validate_fleet_view": "tmux_observer_client.contract",
    "validate_fleet_frame": "tmux_observer_client.contract",
    "validate_request": "tmux_observer._validation",
    "validate_operation_error": "tmux_observer._validation",
}

__all__ = [
    "DOCUMENT_LIMIT",
    "FRAME_LIMIT",
    "OBSERVATION_PROTOCOL",
    "REQUEST_LIMIT",
    "Pane",
    "Session",
    "SessionReference",
    "ValidationError",
    "WireError",
    "decode_document",
    "encode_document",
    "validate_observation",
]
__all__.extend(_LEGACY)


def __getattr__(name):
    import importlib

    if name not in _LEGACY:
        raise AttributeError(name)
    return getattr(importlib.import_module(_LEGACY[name]), name)
