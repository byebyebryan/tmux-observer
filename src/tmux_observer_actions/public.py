"""UI-neutral explicit action SDK. It needs neither Rofi nor Observer services."""

import copy

from tmux_observer._validation_common import ValidationError

from ._legacy_validation import _validate_public_result
from ._legacy_wire import WireError
from ._progress import Progress, current, mark
from .config import ActionConfig
from .contract import ACTION_PROTOCOL, validate_action_request, validate_action_result
from .errors import ContractError
from .lifecycle_service import LifecycleService


class ActionClient:
    """One explicit request, one result, with no uncertain-action retries."""

    def __init__(self, config=None, *, mesh_adapter=None, local_tmux=None, remote_lifecycle=None):
        self._service = LifecycleService(
            config or ActionConfig(),
            mesh_adapter=mesh_adapter,
            local_tmux=local_tmux,
            remote_lifecycle=remote_lifecycle,
        )

    def execute(self, request):
        # Caller mutations after dispatch cannot replace frozen action intent.
        request = validate_action_request(copy.deepcopy(request))
        progress = Progress(request["operation"], request["sessionRef"], request["hostId"])
        token = current.set(progress)
        result = None
        problem = None
        revision = request["meshRevision"]
        try:
            result = self._dispatch(request)
            _validate_public_result(request["operation"], result)
            revision = result["meshRevision"]
            legacy_ref = result.get("sessionRef", result.get("session", result.get("reference")))
            progress.reference = {
                key: legacy_ref[key]
                for key in ("hostId", "serverGeneration", "sessionId", "createdAt")
            }
            if request["operation"] in ("create", "rename", "kill"):
                mark("nativeEffect", "confirmed")
            if request["operation"] == "close-viewer":
                mark("viewerClose", "confirmed" if result["closed"] else "already_closed")
        except (ContractError, ValidationError, WireError, OSError) as error:
            problem = {
                "code": getattr(error, "code", "operation_failed"),
                "message": getattr(error, "message", "action response could not be validated"),
            }
            result = None
        finally:
            current.reset(token)
        response = {
            "protocol": ACTION_PROTOCOL,
            "schemaVersion": 1,
            "requestId": request["requestId"],
            "operation": request["operation"],
            "hostId": request["hostId"],
            "meshRevision": revision,
            "sessionRef": progress.reference,
            "ok": problem is None,
            "outcome": progress.outcome,
            "legacyResult": result,
            "error": problem,
            "automaticRetry": False,
        }
        return validate_action_result(response, request=request)

    def _dispatch(self, request):
        operation, parameters = request["operation"], request["parameters"]
        scope = (request["hostId"], request["meshRevision"])
        if operation == "create":
            return self._service.create(
                *scope,
                parameters["name"],
                parameters["cwd"],
                tuple(parameters["options"].items()),
                tuple(parameters["command"]),
                parameters["deferUntilAttached"],
                parameters["attachTimeout"],
                parameters["open"],
            )
        ref, guards = request["sessionRef"], request["guards"]
        target = (*scope, ref["serverGeneration"], ref["sessionId"], ref["createdAt"])
        name, options = guards["expectedName"], tuple(guards["requiredOptions"].items())
        if operation == "open":
            policy = parameters["viewerPolicy"]
            return self._service.open(*target, name, options, policy == "verified", policy == "new")
        if operation == "rename":
            return self._service.rename(*target, name, parameters["name"], required_options=options)
        if operation == "kill":
            return self._service.kill(*target, name, required_options=options)
        if operation == "viewers":
            return self._service.viewers(*target, name, options)
        return self._service.close_viewer(*target, parameters["viewerId"], name, options)


__all__ = ["ActionClient", "ActionConfig", "LifecycleService"]
