"""Bounded single-line JSON; adapted from the pinned Tmux Plus wire boundary.

Copyright (c) 2026 Bryan Bai. SPDX-License-Identifier: MIT.
"""

from __future__ import annotations

import json
import math
import re

DOCUMENT_LIMIT = 1_048_576
ENVELOPE_LIMIT = 16_384
FRAME_LIMIT = DOCUMENT_LIMIT + ENVELOPE_LIMIT
REQUEST_LIMIT = 16_384
STRING_LIMIT = 16_384
MAX_DEPTH = 32
MAX_NODES = 100_000
MAX_INT = 2**63 - 1
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


class WireError(ValueError):
    """Bounded input is not an unambiguous supported JSON record."""


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise WireError("duplicate object key")
        result[key] = value
    return result


def _integer(value: str) -> int:
    if len(value.lstrip("-")) > 19:
        raise WireError("integer exceeds the wire bound")
    result = int(value)
    if not -MAX_INT <= result <= MAX_INT:
        raise WireError("integer exceeds the wire bound")
    return result


def _float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise WireError("non-finite number")
    return result


def _constant(_value: str) -> object:
    raise WireError("non-finite number")


def _preflight(text: str) -> None:
    """Bound parser nesting and token allocation before json constructs objects."""
    depth = nodes = 0
    quoted = escaped = atom = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
            nodes += 1
            atom = False
        elif char in "[{":
            depth += 1
            nodes += 1
            atom = False
        elif char in "]}":
            depth -= 1
            atom = False
        elif char in ",:" or char.isspace():
            atom = False
        elif not atom:
            nodes += 1
            atom = True
        if depth > MAX_DEPTH or nodes > MAX_NODES:
            raise WireError("JSON structure exceeds the wire bound")


def validate_tree(value: object) -> None:
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise WireError("JSON structure exceeds the wire bound")
        if isinstance(item, str):
            if len(item) > STRING_LIMIT or _CONTROL_CHARACTERS.search(item) is not None:
                raise WireError("unclean or oversized string")
            try:
                item.encode("utf-8", "strict")
            except UnicodeError as error:
                raise WireError("invalid Unicode string") from error
        elif isinstance(item, dict):
            if depth == MAX_DEPTH:
                raise WireError("JSON structure exceeds the wire bound")
            if any(not isinstance(key, str) for key in item):
                raise WireError("object key is not a string")
            pending.extend((key, depth + 1) for key in item)
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            if depth == MAX_DEPTH:
                raise WireError("JSON structure exceeds the wire bound")
            pending.extend((child, depth + 1) for child in item)
        elif item is None or isinstance(item, bool):
            continue
        elif isinstance(item, int):
            if not -MAX_INT <= item <= MAX_INT:
                raise WireError("integer exceeds the wire bound")
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise WireError("non-finite number")
        else:
            raise WireError("unsupported JSON value")


def decode_document(raw: bytes, *, limit: int = DOCUMENT_LIMIT) -> object:
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise WireError("record exceeds the wire bound")
    if raw.count(b"\n") != 1 or not raw.endswith(b"\n"):
        raise WireError("record requires exactly one final LF")
    if b"\x00" in raw or raw.startswith(b"\xef\xbb\xbf"):
        raise WireError("NUL or byte-order mark")
    body = raw[:-1]
    if not body or body[-1:] in (b"\r", b" ", b"\t"):
        raise WireError("empty record or trailing whitespace")
    try:
        text = body.decode("utf-8", "strict")
        _preflight(text)
        value, end = json.JSONDecoder(
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_float,
            parse_constant=_constant,
        ).raw_decode(text)
        if end != len(text):
            raise WireError("trailing data")
        validate_tree(value)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise WireError("invalid bounded JSON record") from error
    return value


def encode_document(value: object, *, limit: int = DOCUMENT_LIMIT) -> bytes:
    validate_tree(value)
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        result = raw.encode("utf-8", "strict") + b"\n"
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise WireError("value cannot be encoded") from error
    if len(result) > limit:
        raise WireError("record exceeds the wire bound")
    return result
