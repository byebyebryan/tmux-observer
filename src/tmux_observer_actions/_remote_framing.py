# Adapted from rofi-tmux-plus 0.7.0a2; Copyright (c) 2026 Bryan; MIT.
"""Pure, bounded legacy action response framing; no discovery/transport I/O."""

import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass

from ._native_inputs import validate_session_id
from .errors import ContractError, clean_message
from .model import Pane, Session, SessionReference

_MARKER_PREFIX = "\x1eROFI_PLUS_REACHED_V1:"


_MARKER_SUFFIX = "\x1f\n"


_TRANSPORT_MARKERS = (
    "could not resolve hostname",
    "name or service not known",
    "temporary failure in name resolution",
    "connection refused",
    "connection timed out",
    "operation timed out",
    "no route to host",
    "network is unreachable",
    "connection reset by peer",
    "kex_exchange_identification",
)


_MAX_OUTPUT = 1024 * 1024


_MAX_LINE = 64 * 1024


_MAX_FIELD = 16 * 1024


_MAX_SESSIONS = 256


_MAX_PANES = 512


_MAX_NUMBER = 2**63 - 1


_HEX = re.compile(r"^[0-9A-Fa-f]*$", re.ASCII)


_PANE_ID = re.compile(r"^%[0-9]+$", re.ASCII)


_NATIVE_HOSTNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$", re.ASCII)


_PENDING_OPTION = "@rofi_tmux_plus_pending"


def generate_nonce() -> str:
    return secrets.token_hex(16)


def _marker(nonce: str) -> str:
    return f"{_MARKER_PREFIX}{nonce}{_MARKER_SUFFIX}"


def parse_reached_marker(stderr: str, nonce: str) -> tuple[bool, str]:
    marker = _marker(nonce)
    if stderr.count(marker) != 1:
        return False, stderr
    return True, stderr.replace(marker, "", 1)


def _transport_failure(stderr: str, *, timed_out: bool) -> bool:
    if timed_out:
        return True
    lowered = stderr.casefold()
    return any(marker in lowered for marker in _TRANSPORT_MARKERS)


def _drop_output_newline(value: bytes) -> bytes:
    return value[:-1] if value.endswith(b"\n") else value


def _decode_field(value: str) -> str:
    if len(value) > _MAX_FIELD * 2 or len(value) % 2 or not _HEX.fullmatch(value):
        raise ContractError("operation_failed", "remote tmux field exceeds the framing limit")
    try:
        raw = bytes.fromhex(value)
    except ValueError as error:
        raise ContractError("operation_failed", "remote tmux framing is invalid") from error
    raw = _drop_output_newline(raw)
    if len(raw) > _MAX_FIELD:
        raise ContractError("operation_failed", "remote tmux field exceeds the framing limit")
    return raw.decode("utf-8", errors="replace")


def _number(value: str, *, nullable: bool = False) -> int | None:
    if nullable and value == "":
        return None
    if not value.isascii() or not value.isdecimal():
        raise ContractError("operation_failed", "remote tmux emitted an invalid numeric field")
    try:
        number = int(value)
    except ValueError as error:
        raise ContractError(
            "operation_failed", "remote tmux emitted an invalid numeric field"
        ) from error
    if number > _MAX_NUMBER:
        raise ContractError("operation_failed", "remote tmux emitted an invalid numeric field")
    return number


def _native_hostname(value: str) -> str | None:
    return value if _NATIVE_HOSTNAME.fullmatch(value) else None


@dataclass(slots=True)
class _SessionParts:
    created_at: int
    name: str | None
    activity_at: int | None
    last_attached_at: int | None
    attached_clients: int | None
    pending: bool
    window_count: int | None
    session_path: str | None
    current_window: str | None
    current_path: str | None
    options: dict[str, str | None]
    panes: list[Pane]


@dataclass(frozen=True, slots=True)
class ParsedRemoteInventory:
    generation: str | None
    sessions: tuple[Session, ...]
    status: str | None
    native_hostname: str | None
    error_message: str | None = None


def parse_remote_inventory(
    output: str,
    *,
    host_id: str,
    panes_requested: bool,
    option_names: Sequence[str],
) -> ParsedRemoteInventory:
    """Parse fixed remote framing without allowing tmux fields to delimit records."""
    encoded = output.encode("utf-8", errors="replace")
    if len(encoded) > _MAX_OUTPUT:
        raise ContractError("operation_failed", "remote tmux output exceeded the consumer limit")
    generation: str | None = None
    records: dict[str, _SessionParts] = {}
    seen_generation = False
    seen_native_hostname = False
    native_hostname: str | None = None
    status: str | None = None
    error_message: str | None = None
    pane_count = 0
    for line in output.splitlines():
        if len(line.encode("utf-8", errors="replace")) > _MAX_LINE:
            raise ContractError(
                "operation_failed", "remote tmux record exceeded the consumer limit"
            )
        parts = line.split("\t")
        kind = parts[0]
        if kind == "H":
            if (
                len(parts) != 2
                or seen_native_hostname
                or seen_generation
                or status is not None
                or records
            ):
                raise ContractError("operation_failed", "remote tmux hostname framing is invalid")
            native_hostname = _native_hostname(_decode_field(parts[1]))
            seen_native_hostname = True
            continue
        if kind == "T":
            if (
                len(parts) != 2
                or parts[1] not in {"M", "N"}
                or not seen_native_hostname
                or seen_generation
                or status is not None
                or records
            ):
                raise ContractError("operation_failed", "remote tmux status framing is invalid")
            status = "tmux_missing" if parts[1] == "M" else "no_server"
            continue
        if kind == "E":
            if (
                len(parts) != 2
                or not seen_native_hostname
                or seen_generation
                or status is not None
                or records
            ):
                raise ContractError("operation_failed", "remote tmux error framing is invalid")
            status = "tmux_error"
            error_message = clean_message(_decode_field(parts[1]), limit=240)
            continue
        if kind == "G":
            if len(parts) != 4 or not seen_native_hostname or seen_generation or status is not None:
                raise ContractError("operation_failed", "remote tmux server framing is invalid")
            socket_path, started, pid = (_decode_field(value) for value in parts[1:])
            if not socket_path:
                raise ContractError("operation_failed", "remote tmux server identity is invalid")
            _number(started)
            _number(pid)
            generation = f"tmux-v1:{started}:{pid}:{socket_path}"
            seen_generation = True
            continue
        if kind == "D":
            if len(parts) != 12 or not seen_generation or status is not None:
                raise ContractError("operation_failed", "remote tmux session framing is invalid")
            (
                session_id,
                created,
                name,
                activity,
                last,
                attached,
                windows,
                path,
                current_window,
                current_path,
                pending,
            ) = (_decode_field(value) for value in parts[1:])
            try:
                validate_session_id(session_id)
            except ContractError as error:
                raise ContractError(
                    "operation_failed", "remote tmux session identity is invalid"
                ) from error
            if session_id in records or len(records) >= _MAX_SESSIONS or pending not in {"0", "1"}:
                raise ContractError("operation_failed", "remote tmux session framing is invalid")
            created_at = _number(created)
            assert created_at is not None
            records[session_id] = _SessionParts(
                created_at,
                name or None,
                _number(activity, nullable=True),
                _number(last, nullable=True),
                _number(attached, nullable=True),
                pending == "1",
                _number(windows, nullable=True),
                path or None,
                current_window or None,
                current_path or None,
                {},
                [],
            )
            continue
        if kind == "O":
            if len(parts) != 4 or not seen_generation or status is not None:
                raise ContractError("operation_failed", "remote tmux option framing is invalid")
            session_id, name = (_decode_field(value) for value in parts[1:3])
            if (
                session_id not in records
                or name not in option_names
                or name in records[session_id].options
            ):
                raise ContractError("operation_failed", "remote tmux option framing is invalid")
            records[session_id].options[name] = None if parts[3] == "-" else _decode_field(parts[3])
            continue
        if kind == "P":
            if len(parts) != 6 or not seen_generation or status is not None:
                raise ContractError("operation_failed", "remote tmux pane framing is invalid")
            session_id, pane_id, pid, current_path, command = (
                _decode_field(value) for value in parts[1:]
            )
            if (
                not panes_requested
                or session_id not in records
                or pane_count >= _MAX_PANES
                or not _PANE_ID.fullmatch(pane_id)
            ):
                raise ContractError("operation_failed", "remote tmux pane framing is invalid")
            records[session_id].panes.append(
                Pane(pane_id, _number(pid, nullable=True), current_path or None, command or None)
            )
            pane_count += 1
            continue
        raise ContractError("operation_failed", "remote tmux emitted an unknown framing record")
    if status is not None:
        return ParsedRemoteInventory(None, (), status, native_hostname, error_message)
    if not seen_generation:
        raise ContractError("operation_failed", "remote tmux output omitted server identity")
    assert generation is not None
    sessions: list[Session] = []
    for session_id, parts in records.items():
        if set(parts.options) != set(option_names):
            raise ContractError("operation_failed", "remote tmux output omitted a requested option")
        sessions.append(
            Session(
                SessionReference(host_id, generation, session_id, parts.created_at),
                parts.name,
                parts.activity_at,
                parts.last_attached_at,
                parts.attached_clients,
                parts.pending,
                parts.window_count,
                parts.session_path,
                parts.current_window,
                parts.current_path,
                tuple(parts.panes) if panes_requested else None,
                parts.options if option_names else None,
            )
        )
    return ParsedRemoteInventory(generation, tuple(sessions), None, native_hostname)
