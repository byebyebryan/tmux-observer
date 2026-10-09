# Adapted from rofi-tmux-plus 0.7.0a2; Copyright (c) 2026 Bryan; MIT.
"""Pure legacy result checks retained independently of the new action contract."""

import re

from ._legacy_wire import WireError, validate_string_bounds

_ERROR_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$", re.ASCII)


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", re.ASCII)


_REVISION = re.compile(r"^sha256:[0-9a-f]{64}$", re.ASCII)


_VIEWER_ID = re.compile(r"^tv1_[A-Za-z0-9_-]{43}$", re.ASCII)


def _validate_public_result(command: str, result: object) -> None:
    if (
        not isinstance(result, dict)
        or type(result.get("schemaVersion")) is not int
        or result.get("schemaVersion") != 1
    ):
        raise WireError("producer returned an invalid schema version")
    if command == "inventory":
        if "ok" in result:
            raise WireError("inventory response must not carry an ok field")
        _require_fields(result, "generatedAt", "meshRevision", "hosts")
        if not _integer_field(result.get("generatedAt"), 0, 2**63 - 1):
            raise WireError("inventory timestamp is invalid")
        _revision_field(result.get("meshRevision"))
        hosts = result.get("hosts")
        if not isinstance(hosts, list) or not hosts or len(hosts) > 128:
            raise WireError("inventory host count exceeded its limit")
        host_ids: set[str] = set()
        for host in hosts:
            if not isinstance(host, dict):
                raise WireError("inventory host row is invalid")
            _validate_host_row(host)
            host_id = host["hostId"].casefold()
            if host_id in host_ids:
                raise WireError("inventory host identities are ambiguous")
            host_ids.add(host_id)
            sessions = host.get("sessions")
            if not isinstance(sessions, list) or len(sessions) > 256:
                raise WireError("inventory session count exceeded its limit")
            pane_count = 0
            for session in sessions:
                if not isinstance(session, dict):
                    raise WireError("inventory session row is invalid")
                _validate_session(session, limit=16_384)
                if session["hostId"] != host["hostId"]:
                    raise WireError("inventory session host identity is invalid")
                panes = session.get("panes")
                if panes is not None and (not isinstance(panes, list) or len(panes) > 512):
                    raise WireError("inventory pane count exceeded its limit")
                if panes is not None:
                    for pane in panes:
                        _validate_pane(pane, limit=16_384)
                    pane_count += len(panes)
            if pane_count > 512:
                raise WireError("inventory pane count exceeded its host limit")
        validate_string_bounds(result, limit=16_384)
        return
    if command == "viewers":
        _require_fields(
            result, "ok", "meshRevision", "sessionRef", "status", "viewers", "closeSafe"
        )
        if result.get("ok") is not True:
            raise WireError("viewer inspection success response must have ok=true")
        _revision_field(result.get("meshRevision"))
        reference = result.get("sessionRef")
        if not isinstance(reference, dict):
            raise WireError("viewer session reference is invalid")
        _validate_reference(reference, limit=4_096)
        status = result.get("status")
        if not isinstance(status, str) or status not in {
            "none",
            "verified",
            "unverified",
            "ambiguous",
            "unsupported",
        }:
            raise WireError("viewer status is invalid")
        if type(result.get("closeSafe")) is not bool:
            raise WireError("viewer closeSafe field is invalid")
        viewers = result.get("viewers")
        if not isinstance(viewers, list) or len(viewers) > 512:
            raise WireError("viewer inventory exceeded its limit")
        viewer_ids: set[str] = set()
        window_ids: set[int] = set()
        for viewer in viewers:
            if not isinstance(viewer, dict):
                raise WireError("viewer row is invalid")
            _require_fields(viewer, "viewerId", "windowId")
            viewer_id = viewer.get("viewerId")
            if (
                not isinstance(viewer_id, str)
                or len(viewer_id) > 4_096
                or _VIEWER_ID.fullmatch(viewer_id) is None
            ):
                raise WireError("viewer ID is invalid")
            window_id = viewer.get("windowId")
            if not _integer_field(window_id, 0, 2**63 - 1):
                raise WireError("viewer window ID is invalid")
            if viewer_id in viewer_ids or window_id in window_ids:
                raise WireError("viewer identities are ambiguous")
            viewer_ids.add(viewer_id)
            window_ids.add(window_id)
        if (status == "verified") != bool(viewers):
            raise WireError("viewer status and verified handles disagree")
        if "reason" in result:
            _string_field(result.get("reason"), nullable=False, limit=512)
        validate_string_bounds(result, limit=4_096)
        return
    if command == "close-viewer":
        _require_fields(
            result, "ok", "meshRevision", "sessionRef", "viewerId", "closed", "alreadyClosed"
        )
        if result.get("ok") is not True:
            raise WireError("viewer close success response must have ok=true")
        _revision_field(result.get("meshRevision"))
        reference = result.get("sessionRef")
        if not isinstance(reference, dict):
            raise WireError("viewer session reference is invalid")
        _validate_reference(reference, limit=4_096)
        viewer_id = result.get("viewerId")
        if not isinstance(viewer_id, str) or _VIEWER_ID.fullmatch(viewer_id) is None:
            raise WireError("viewer ID is invalid")
        if type(result.get("closed")) is not bool or type(result.get("alreadyClosed")) is not bool:
            raise WireError("viewer close result fields are invalid")
        if result["closed"] == result["alreadyClosed"]:
            raise WireError("viewer close result fields must be exclusive")
        validate_string_bounds(result, limit=4_096)
        return
    _require_fields(result, "ok", "meshRevision")
    if result.get("ok") is not True:
        raise WireError("lifecycle success response must have ok=true")
    _revision_field(result.get("meshRevision"))
    if command == "kill":
        _require_fields(result, "reference", "observedClients")
        reference = result.get("reference")
        if not isinstance(reference, dict):
            raise WireError("kill reference is invalid")
        _validate_reference(reference, limit=4_096)
        if not _integer_field(result.get("observedClients"), 0, 2**31 - 1):
            raise WireError("observed client count is invalid")
    else:
        _require_fields(result, "session")
        session = result.get("session")
        if not isinstance(session, dict):
            raise WireError("lifecycle session is invalid")
        _validate_session(session, limit=4_096)
        has_focus = "focused" in result
        has_launch = "terminalLaunched" in result
        if command == "open" and not has_focus:
            raise WireError("open response must include focused")
        if command == "open" and not has_launch:
            raise WireError("open response must include terminalLaunched")
        if has_focus != has_launch:
            raise WireError("lifecycle focus and launch fields must be paired")
        if has_focus:
            if type(result["focused"]) is not bool or type(result["terminalLaunched"]) is not bool:
                raise WireError("lifecycle focus fields are invalid")
            if result["focused"] == result["terminalLaunched"]:
                raise WireError("lifecycle focus fields must be exclusive")
        if "viewerId" in result:
            viewer_id = result.get("viewerId")
            if not isinstance(viewer_id, str) or _VIEWER_ID.fullmatch(viewer_id) is None:
                raise WireError("viewer ID is invalid")
    validate_string_bounds(result, limit=4_096)


def _require_fields(value: dict[str, object], *names: str) -> None:
    if any(name not in value for name in names):
        raise WireError("producer response is missing a required field")


def _integer_field(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _revision_field(value: object) -> None:
    if value is not None and (not isinstance(value, str) or _REVISION.fullmatch(value) is None):
        raise WireError("mesh revision is invalid")


def _string_field(value: object, *, nullable: bool, limit: int) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value or len(value) > limit:
        raise WireError("response string field is invalid")


def _validate_reference(reference: dict[str, object], *, limit: int) -> None:
    _require_fields(reference, "hostId", "serverGeneration", "sessionId", "createdAt")
    _string_field(reference.get("hostId"), nullable=False, limit=limit)
    if _IDENTIFIER.fullmatch(reference["hostId"]) is None:  # type: ignore[arg-type]
        raise WireError("reference host ID is invalid")
    _generation_field(reference.get("serverGeneration"), limit=limit)
    _string_field(reference.get("sessionId"), nullable=False, limit=4_096)
    if not re.fullmatch(r"\$[0-9]+", reference["sessionId"]):  # type: ignore[arg-type]
        raise WireError("reference session ID is invalid")
    if not _integer_field(reference.get("createdAt"), 0, 2**63 - 1):
        raise WireError("reference timestamp is invalid")


def _validate_session(session: dict[str, object], *, limit: int) -> None:
    _require_fields(
        session,
        "hostId",
        "serverGeneration",
        "sessionId",
        "createdAt",
        "name",
        "activityAt",
        "lastAttachedAt",
        "attachedClients",
        "pending",
        "windowCount",
        "sessionPath",
        "currentWindow",
        "currentPath",
    )
    _validate_reference(session, limit=limit)
    _string_field(session.get("name"), nullable=True, limit=limit)
    for key in ("activityAt", "lastAttachedAt"):
        value = session.get(key)
        if value is not None and not _integer_field(value, 0, 2**63 - 1):
            raise WireError(f"session field {key} is invalid")
    for key in ("windowCount", "attachedClients"):
        value = session.get(key)
        if value is not None and not _integer_field(value, 0, 2**31 - 1):
            raise WireError(f"session field {key} is invalid")
    if type(session.get("pending")) is not bool:
        raise WireError("session pending field is invalid")
    for key in ("sessionPath", "currentWindow", "currentPath"):
        _string_field(session.get(key), nullable=True, limit=limit)
    panes = session.get("panes")
    if panes is not None:
        if not isinstance(panes, list) or len(panes) > 512:
            raise WireError("session panes are invalid")
        for pane in panes:
            _validate_pane(pane, limit=limit)
    options = session.get("options")
    if options is not None:
        _validate_options(options, limit=limit)


def _validate_pane(value: object, *, limit: int) -> None:
    if not isinstance(value, dict):
        raise WireError("session pane is invalid")
    _require_fields(value, "paneId", "pid", "currentPath", "currentCommand")
    _string_field(value.get("paneId"), nullable=False, limit=4_096)
    if not isinstance(value["paneId"], str) or re.fullmatch(r"%[0-9]+", value["paneId"]) is None:
        raise WireError("session pane ID is invalid")
    pid = value.get("pid")
    if pid is not None and not _integer_field(pid, 0, 2**31 - 1):
        raise WireError("session pane PID is invalid")
    for key in ("currentPath", "currentCommand"):
        _string_field(value.get(key), nullable=True, limit=limit)


def _validate_options(value: object, *, limit: int) -> None:
    if not isinstance(value, dict):
        raise WireError("session options are invalid")
    for name, option_value in value.items():
        if not isinstance(name, str) or re.fullmatch(r"@[A-Za-z0-9_.-]+", name, re.ASCII) is None:
            raise WireError("session option name is invalid")
        _string_field(option_value, nullable=True, limit=limit)


def _generation_field(value: object, *, limit: int) -> None:
    _string_field(value, nullable=False, limit=limit)
    assert isinstance(value, str)
    if any(ord(char) <= 0x1F or 0x7F <= ord(char) <= 0x9F for char in value):
        raise WireError("server generation is invalid")


def _validate_host_row(host: dict[str, object]) -> None:
    _require_fields(
        host,
        "hostId",
        "display",
        "local",
        "status",
        "observedAt",
        "nativeHostname",
        "serverGeneration",
        "route",
        "sessions",
    )
    _string_field(host.get("hostId"), nullable=False, limit=16_384)
    if _IDENTIFIER.fullmatch(host["hostId"]) is None:  # type: ignore[arg-type]
        raise WireError("host ID is invalid")
    _string_field(host.get("display"), nullable=False, limit=16_384)
    if type(host.get("local")) is not bool:
        raise WireError("host local field is invalid")
    status = host.get("status")
    if not isinstance(status, str) or status not in {"ok", "unreachable", "tmux_missing", "error"}:
        raise WireError("host status is invalid")
    if not _integer_field(host.get("observedAt"), 0, 2**63 - 1):
        raise WireError("host observation timestamp is invalid")
    _string_field(host.get("nativeHostname"), nullable=True, limit=16_384)
    generation = host.get("serverGeneration")
    if generation is not None:
        _generation_field(generation, limit=16_384)
    _string_field(host.get("route"), nullable=True, limit=16_384)
    sessions = host.get("sessions")
    if not isinstance(sessions, list) or len(sessions) > 256:
        raise WireError("inventory sessions are invalid")
    error = host.get("error")
    if error is not None:
        if not isinstance(error, dict):
            raise WireError("inventory host error is invalid")
        _require_fields(error, "code", "message")
        code = error.get("code")
        if not isinstance(code, str) or len(code) > 64 or _ERROR_CODE.fullmatch(code) is None:
            raise WireError("inventory host error code is invalid")
        _string_field(error.get("message"), nullable=False, limit=4_096)
        if "hostId" in error:
            host_error_id = error.get("hostId")
            _string_field(host_error_id, nullable=False, limit=4_096)
            if _IDENTIFIER.fullmatch(host_error_id) is None:  # type: ignore[arg-type]
                raise WireError("inventory host error ID is invalid")
    if status != "ok" and error is None:
        raise WireError("failed inventory host is missing its error")
    if status == "ok" and error is not None:
        raise WireError("successful inventory host must not carry an error")
    if status != "ok" and sessions:
        raise WireError("failed inventory host must not carry sessions")
