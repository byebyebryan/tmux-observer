"""Pure legacy scalar bounds used at the action compatibility boundary."""

from collections.abc import Mapping


class WireError(ValueError):
    """The bytes do not represent one canonical JSON document."""


def validate_string_bounds(value: object, *, limit: int) -> None:
    """Reject oversized nested strings before response serialization."""
    if isinstance(value, str):
        if len(value) > limit:
            raise WireError("response string exceeded its limit")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise WireError("response object key is not a string")
            if len(key) > limit:
                raise WireError("response object key exceeded its limit")
            validate_string_bounds(child, limit=limit)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            validate_string_bounds(child, limit=limit)
