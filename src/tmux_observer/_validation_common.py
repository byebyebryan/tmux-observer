"""Bounded structural primitives shared by independent contract domains."""

import re

from ._wire import MAX_INT

OWNER_LEASE_MS = 10_000
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
HOST = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
TOKEN = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}"
SESSION = r"\$[0-9]+"
OPTION = r"@[A-Za-z0-9_.-]+"
SHA256 = r"sha256:[0-9a-f]{64}"
CONTEXT = r"[0-9a-f]{32}"


class ValidationError(ValueError):
    """The document violates supported structure or semantics."""


def obj(value: object, *keys: str) -> dict:
    if not isinstance(value, dict) or any(key not in value for key in keys):
        raise ValidationError("missing object or required field")
    return value


def integer(value: object, *, maximum: int = MAX_INT) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValidationError("invalid nonnegative integer")
    return value


def string(value: object, pattern: str | None = None, *, maximum: int = 16_384) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValidationError("invalid bounded string")
    if pattern and not re.fullmatch(pattern, value):
        raise ValidationError("invalid token syntax")
    return value


def nullable(value: object, validator):
    return None if value is None else validator(value)


def array(value: object, *, maximum: int) -> list:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValidationError("invalid bounded array")
    return value


def boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValidationError("invalid boolean")
    return value


def enum(value: object, choices: tuple[str, ...]) -> str:
    if value not in choices or not isinstance(value, str):
        raise ValidationError("unsupported variant")
    return value


def error(value: object) -> dict | None:
    if value is None:
        return None
    value = obj(value, "code", "message")
    string(value["code"], TOKEN, maximum=64)
    if not isinstance(value["message"], str) or len(value["message"]) > 4096:
        raise ValidationError("invalid diagnostic")
    return value


def clock(value: object) -> dict:
    value = obj(value, "bootId", "timeNamespace")
    string(value["bootId"], UUID, maximum=36)
    string(value["timeNamespace"], r"time:[0-9]+", maximum=64)
    return value


def clock_key(value: dict) -> tuple:
    return value["bootId"], value["timeNamespace"]


def exact(value, *keys):
    value = obj(value, *keys)
    if set(value) != set(keys):
        raise ValidationError("unknown field in closed contract")
    return value


def version(value, protocol):
    if value["protocol"] != protocol or type(value["schemaVersion"]) is not int:
        raise ValidationError("unsupported protocol")
    if value["schemaVersion"] != 1:
        raise ValidationError("unsupported version")


def positive(value, maximum=2**63 - 1):
    value = integer(value, maximum=maximum)
    if value == 0:
        raise ValidationError("zero identity")
    return value


def closed_error(value):
    if value is None:
        return None
    exact(value, "code", "message")
    return error(value)
