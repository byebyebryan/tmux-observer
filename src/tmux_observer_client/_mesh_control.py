"""Explicit one-shot Observer controls, independent of Mesh state delivery."""

import shlex

from tmux_observer._clock import boottime_ms
from tmux_observer._ipc import IPCError, exchange
from tmux_observer._request_validation import validate_operation_error, validate_request
from tmux_observer.delivery import SERVICE_PROTOCOL, validate_service_frame
from tmux_observer.native import FRAME_LIMIT, decode_document

from ._command import run_bounded
from ._errors import ContractError
from .direct import ssh_argv


class OwnerControl:
    def __init__(
        self,
        state,
        executor,
        *,
        path=None,
        host=None,
        route=None,
        policy=None,
        remote_exec=None,
        on_frame=None,
        on_error=None,
    ):
        self.state, self.executor = state, executor
        self.path, self.host, self.route, self.policy = path, host, route, policy
        self.remote_exec, self.on_frame, self.on_error = remote_exec, on_frame, on_error
        self.future = self.request = None
        self.sent_at = None
        self.closed = False
        self.binding = state.epoch, state.scope, state.selected_route

    def send(self, request, now):
        validate_request(request)
        if (
            self.closed
            or self.future is not None
            or request["operation"] not in ("refresh", "refresh_status")
            or request["expectedHost"] != self.state.host_id
            or self.state.scope is None
            or request["publisherId"] != self.state.scope[0]
        ):
            raise ContractError("operation_failed", "Observer control scope is closed or busy")
        self.request = request
        self.sent_at = now
        self.future = self.executor.submit(self.exchange, request)

    def exchange(self, request):
        if self.state.local_clock is not None:
            return exchange(request, path=self.path, budget_ms=1900)
        args = [
            request["operation"],
            "--expected-host",
            request["expectedHost"],
            "--publisher-id",
            request["publisherId"],
            "--request-id",
            request["requestId"],
        ]
        if request["operation"] == "refresh_status":
            args += ["--ticket-id", request["ticketId"]]
        program = self.remote_exec + " " + shlex.join(args)
        result = run_bounded(
            ssh_argv(self.route.destination, self.policy, program),
            timeout=1.9,
            stdout_limit=FRAME_LIMIT,
            stderr_limit=65536,
        )
        if result.timed_out or result.overflow_streams or result.returncode not in (0, 1):
            raise IPCError("owner_unavailable", "explicit remote Observer control failed")
        value = decode_document(result.stdout_bytes, limit=FRAME_LIMIT)
        if value.get("kind") == "operation_error":
            validate_operation_error(value)
            if value["protocol"] != SERVICE_PROTOCOL or result.returncode != 1:
                raise ValueError("foreign Observer control error")
            raise IPCError(value["error"]["code"], value["error"]["message"])
        if result.returncode != 0:
            raise ValueError("Observer control exit differs from its result")
        return value

    def poll(self, now):
        if self.future is None or not self.future.done():
            return
        future, request = self.future, self.request
        self.future = self.request = None
        if self.closed:
            return
        try:
            value = validate_service_frame(future.result())
            now = boottime_ms()
            if now >= self.sent_at + 2000:
                raise IPCError("deadline", "Observer control reply exceeded its admission deadline")
            scope = self.state.scope
            if (
                scope is None
                or value["requestId"] != request["requestId"]
                or value["publisherId"] != request["publisherId"]
                or value["source"]["hostId"] != self.state.host_id
                or (
                    value["source"]["uid"],
                    value["source"]["server"],
                    value["clock"]["bootId"],
                    value["clock"]["timeNamespace"],
                )
                != scope[1:]
                or value["kind"] != "refresh_result"
                or value["sequence"] != 0
            ):
                raise ValueError("Observer control reply differs from Mesh owner scope")
            self.on_frame(self, value, False, now)
        except (IPCError, ContractError, OSError, ValueError) as error:
            self.on_error(
                self,
                {
                    "requestId": request["requestId"],
                    "error": {
                        "code": error.code
                        if isinstance(error, (IPCError, ContractError))
                        else "invalid_refresh",
                        "message": "explicit Observer control failed",
                    },
                },
                now,
            )

    def fail(self, _code, _message):
        self.closed = True
        if self.future is not None:
            self.future.cancel()
