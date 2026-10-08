"""Pure explicit action contract (C5). Importing it performs no action."""

from tmux_observer._native_validation import reference
from tmux_observer._validation_common import (
    HOST,
    OPTION,
    SHA256,
    TOKEN,
    ValidationError,
    array,
    boolean,
    enum,
    exact,
    integer,
    nullable,
    string,
    version,
)
from tmux_observer._validation_common import (
    closed_error as error,
)
from tmux_observer._wire import DOCUMENT_LIMIT, REQUEST_LIMIT, encode_document, validate_tree

ACTION_PROTOCOL = "tmux-observer.action.v1"
OPERATIONS = ("open", "create", "rename", "kill", "viewers", "close-viewer")


def options(value):
    if not isinstance(value, dict) or len(value) > 64:
        raise ValidationError("invalid action option map")
    for key, child in value.items():
        string(key, OPTION, maximum=256)
        if not isinstance(child, str):
            raise ValidationError("invalid option value")


def clean_text(value, maximum=16384, *, empty=False):
    if empty and value == "":
        return value
    return string(value, maximum=maximum)


def validate_action_request(value):
    validate_tree(value)
    value = exact(
        value,
        "protocol",
        "schemaVersion",
        "requestId",
        "operation",
        "hostId",
        "meshRevision",
        "sessionRef",
        "guards",
        "parameters",
    )
    version(value, ACTION_PROTOCOL)
    string(value["requestId"], TOKEN, maximum=64)
    operation = enum(value["operation"], OPERATIONS)
    host = string(value["hostId"], HOST)
    nullable(value["meshRevision"], lambda item: string(item, SHA256, maximum=71))
    guards = exact(value["guards"], "expectedName", "requiredOptions")
    nullable(guards["expectedName"], clean_text)
    options(guards["requiredOptions"])
    if operation == "create":
        if value["sessionRef"] is not None or guards != {
            "expectedName": None,
            "requiredOptions": {},
        }:
            raise ValidationError("create cannot target an existing reference")
        parameters = exact(
            value["parameters"],
            "name",
            "cwd",
            "options",
            "command",
            "deferUntilAttached",
            "attachTimeout",
            "open",
        )
        clean_text(parameters["name"])
        nullable(parameters["cwd"], clean_text)
        options(parameters["options"])
        for argument in array(parameters["command"], maximum=128):
            clean_text(argument, empty=True)
        boolean(parameters["deferUntilAttached"])
        boolean(parameters["open"])
        if parameters["attachTimeout"] is not None:
            timeout = integer(parameters["attachTimeout"], maximum=3600)
            if timeout == 0:
                raise ValidationError("zero attach timeout")
    else:
        exact(value["sessionRef"], "hostId", "serverGeneration", "sessionId", "createdAt")
        if reference(value["sessionRef"])[0] != host:
            raise ValidationError("action host differs from exact target")
        if operation == "open":
            parameters = exact(value["parameters"], "viewerPolicy")
            enum(parameters["viewerPolicy"], ("reuse_unique", "verified", "new"))
        elif operation == "rename":
            clean_text(exact(value["parameters"], "name")["name"])
        elif operation == "close-viewer":
            string(exact(value["parameters"], "viewerId")["viewerId"], maximum=512)
        else:
            exact(value["parameters"])
        if operation in ("rename", "kill") and guards["expectedName"] is None:
            raise ValidationError("destructive/rename intent lacks name guard")
    encode_document(value, limit=REQUEST_LIMIT)
    return value


def validate_action_result(value, *, request=None):
    validate_tree(value)
    value = exact(
        value,
        "protocol",
        "schemaVersion",
        "requestId",
        "operation",
        "hostId",
        "meshRevision",
        "sessionRef",
        "ok",
        "outcome",
        "legacyResult",
        "error",
        "automaticRetry",
    )
    version(value, ACTION_PROTOCOL)
    string(value["requestId"], TOKEN, maximum=64)
    operation = enum(value["operation"], OPERATIONS)
    host = string(value["hostId"], HOST)
    nullable(value["meshRevision"], lambda item: string(item, SHA256, maximum=71))
    if value["sessionRef"] is not None:
        exact(value["sessionRef"], "hostId", "serverGeneration", "sessionId", "createdAt")
        if reference(value["sessionRef"])[0] != host:
            raise ValidationError("result retargeted host")
    ok = boolean(value["ok"])
    if value["automaticRetry"] is not False:
        raise ValidationError("action results never authorize automatic retry")
    problem = error(value["error"])
    if ok == (problem is not None):
        raise ValidationError("action result/error mismatch")
    outcome = exact(
        value["outcome"],
        "nativeEffect",
        "terminalSpawn",
        "attachment",
        "focus",
        "viewerClose",
        "transport",
    )
    native = enum(outcome["nativeEffect"], ("none", "confirmed", "uncertain"))
    spawn = enum(outcome["terminalSpawn"], ("not_requested", "confirmed", "failed", "uncertain"))
    enum(outcome["attachment"], ("not_requested", "confirmed", "unverified"))
    enum(outcome["focus"], ("not_requested", "confirmed", "failed", "ambiguous"))
    enum(
        outcome["viewerClose"],
        ("not_requested", "confirmed", "already_closed", "failed", "uncertain"),
    )
    enum(outcome["transport"], ("local", "confirmed", "uncertain"))
    if operation in ("open", "viewers", "close-viewer") and native != "none":
        raise ValidationError("viewer operation claims native mutation")
    if ok and (
        value["sessionRef"] is None
        or native == "uncertain"
        or spawn == "uncertain"
        or outcome["transport"] == "uncertain"
    ):
        raise ValidationError("successful result lacks exact/effect certainty")
    if ok and operation in ("create", "rename", "kill") and native != "confirmed":
        raise ValidationError("successful native write lacks confirmed effect")
    if operation != "close-viewer" and outcome["viewerClose"] != "not_requested":
        raise ValidationError("unrequested viewer close")
    if operation not in ("open", "create") and (
        spawn != "not_requested"
        or outcome["attachment"] != "not_requested"
        or outcome["focus"] != "not_requested"
    ):
        raise ValidationError("unrequested presentation effect")
    if (native == "confirmed" or outcome["attachment"] == "confirmed") and value[
        "sessionRef"
    ] is None:
        raise ValidationError("confirmed effect lacks full reference")
    legacy = value["legacyResult"]
    if ok:
        if (
            not isinstance(legacy, dict)
            or legacy.get("ok") is not True
            or type(legacy.get("schemaVersion")) is not int
            or legacy.get("schemaVersion") != 1
        ):
            raise ValidationError("missing compatibility success")
        if legacy.get("meshRevision") != value["meshRevision"]:
            raise ValidationError("compatibility route projection mismatch")
        legacy_ref = legacy.get("sessionRef", legacy.get("session", legacy.get("reference")))
        if legacy_ref is None or reference(legacy_ref) != reference(value["sessionRef"]):
            raise ValidationError("compatibility target projection mismatch")
        if operation == "open" or operation == "create" and "terminalLaunched" in legacy:
            focused = boolean(legacy.get("focused"))
            launched = boolean(legacy.get("terminalLaunched"))
            if (outcome["focus"] == "confirmed") != focused or (spawn == "confirmed") != launched:
                raise ValidationError("compatibility presentation projection mismatch")
            if operation == "open" and not focused and not launched:
                raise ValidationError("successful open has no completed focus or spawn")
        if operation == "close-viewer":
            closed = boolean(legacy.get("closed"))
            already = boolean(legacy.get("alreadyClosed"))
            expected = "confirmed" if closed else "already_closed"
            if closed == already or outcome["viewerClose"] != expected:
                raise ValidationError("compatibility close projection mismatch")
    elif legacy is not None:
        raise ValidationError("failed result has compatibility success")
    if request is not None:
        validate_action_request(request)
        if any(value[key] != request[key] for key in ("requestId", "operation", "hostId")):
            raise ValidationError("action result does not match request")
        if request["meshRevision"] is not None and value["meshRevision"] != request["meshRevision"]:
            raise ValidationError("action result changed requested route revision")
        if operation != "create" and value["sessionRef"] != request["sessionRef"]:
            raise ValidationError("action result retargeted exact reference")
    encode_document(value, limit=DOCUMENT_LIMIT)
    return value


__all__ = ["ACTION_PROTOCOL", "validate_action_request", "validate_action_result"]
