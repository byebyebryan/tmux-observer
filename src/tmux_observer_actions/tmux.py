# Adapted from rofi-tmux-plus 0.7.0a2; Copyright (c) 2026 Bryan; MIT.
"""Default-server-only tmux process boundary and machine-readable inventory."""

from __future__ import annotations

import os
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from tmux_observer_client._command import ProcessLaunchError, run_bounded

from ._native_inputs import validate_required_options, validate_session_id, validate_user_option
from ._progress import mark, native_started
from .errors import ContractError, NoServer, TmuxMissing, clean_message
from .model import Session, SessionReference

_SESSION_ID = re.compile(r"^\$[0-9]+$")
_PENDING_OPTION = "@rofi_tmux_plus_pending"

__all__ = [
    "Completed",
    "TmuxClient",
    "validate_required_options",
    "validate_session_id",
    "validate_user_option",
]


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


class TmuxClient:
    """A narrowly scoped client; public callers can never select a socket.

    Tests may supply an explicit executable prefix (``tmux -L unique``), but
    the public CLI constructs this class with the default server only.
    """

    def __init__(
        self,
        executable: Sequence[str] = ("tmux", "-u", "-L", "default"),
        *,
        timeout_seconds: float = 3.0,
    ) -> None:
        if not executable:
            raise ValueError("tmux executable must not be empty")
        self._executable = tuple(executable)
        self._timeout_seconds = timeout_seconds
        self._deadline: float | None = None

    def _run(self, args: Sequence[str], *, timeout: float | None = None) -> Completed:
        argv = [*self._executable, *args]
        selected_timeout = self._timeout_seconds if timeout is None else timeout
        if self._deadline is not None:
            selected_timeout = min(selected_timeout, self._deadline - time.monotonic())
            if selected_timeout <= 0:
                raise ContractError(
                    "operation_failed", "tmux inventory exceeded the local deadline"
                )
        env = os.environ.copy()
        env.pop("TMUX", None)
        env.pop("TMUX_PANE", None)
        mutation = bool(
            args and args[0] in {"new-session", "set-option", "rename-session", "kill-session"}
        )
        previous = native_started() if mutation else None
        try:
            result = run_bounded(
                argv,
                timeout=selected_timeout,
                stdout_limit=1024 * 1024,
                stderr_limit=65536,
                env=env,
            )
        except ProcessLaunchError as error:
            if previous is not None:
                mark("nativeEffect", previous)
            if isinstance(error.__cause__, FileNotFoundError):
                raise TmuxMissing() from error
            raise ContractError(
                "operation_failed", "could not create tmux command process"
            ) from error
        except OSError as error:
            raise ContractError(
                "operation_failed", f"could not execute tmux: {clean_message(error)}"
            ) from error
        if result.timed_out or result.overflow_streams:
            raise ContractError("operation_failed", "tmux exceeded its deadline or output limit")
        return Completed(result.returncode, result.stdout, result.stderr)

    @property
    def attach_argv(self):
        return self._executable

    @staticmethod
    def _without_final_newline(value: str) -> str:
        return value.removesuffix("\n")

    @staticmethod
    def _no_server(result: Completed) -> bool:
        text = f"{result.stdout}\n{result.stderr}".casefold()
        return (
            "no server running" in text
            or "failed to connect to server" in text
            or "error connecting to" in text
        )

    def run(self, args: Sequence[str], *, no_server: bool = False) -> str:
        result = self._run(args)
        if result.returncode == 0:
            return self._without_final_newline(result.stdout)
        if no_server and self._no_server(result):
            raise NoServer()
        raise ContractError("operation_failed", clean_message(result.stderr or result.stdout))

    def try_run(self, args: Sequence[str]) -> Completed:
        return self._run(args)

    def format(self, target: str | None, template: str, *, no_server: bool = False) -> str:
        args = ["display-message", "-p"]
        if target is not None:
            args.extend(["-t", target])
        args.append(template)
        return self.run(args, no_server=no_server)

    def server_generation(self) -> str:
        # One format per process means a newline, tab, or delimiter in a path
        # can never corrupt the result.  The socket is opaque in the contract.
        socket_path = self.format(None, "#{socket_path}", no_server=True)
        started = self.format(None, "#{start_time}", no_server=True)
        pid = self.format(None, "#{pid}", no_server=True)
        if not socket_path or not started.isdecimal() or not pid.isdecimal():
            raise ContractError("operation_failed", "tmux returned an incomplete server identity")
        return f"tmux-v1:{started}:{pid}:{socket_path}"

    def session_ids(self) -> list[str]:
        output = self.run(["list-sessions", "-F", "#{session_id}"], no_server=True)
        if not output:
            return []
        ids = output.splitlines()
        if len(ids) != len(set(ids)) or any(not _SESSION_ID.fullmatch(item) for item in ids):
            raise ContractError("operation_failed", "tmux returned an invalid session inventory")
        return ids

    def client_pids(self, session_id: str) -> list[int]:
        """Return the exact local client PIDs attached to one stable session ID."""
        validate_session_id(session_id)
        output = self.run(["list-clients", "-t", session_id, "-F", "#{client_pid}"], no_server=True)
        if not output:
            return []
        values = output.splitlines()
        if len(values) > 512 or len(values) != len(set(values)):
            raise ContractError("operation_failed", "tmux returned an invalid client inventory")
        result: list[int] = []
        for value in values:
            if not value.isdecimal() or int(value) <= 0:
                raise ContractError("operation_failed", "tmux returned an invalid client PID")
            result.append(int(value))
        return result

    def option(self, session_id: str, name: str) -> str | None:
        validate_user_option(name)
        present = self.run(["show-options", "-q", "-t", session_id], no_server=True)
        if not any(line == name or line.startswith(f"{name} ") for line in present.splitlines()):
            return None
        result = self.try_run(["show-options", "-qv", "-t", session_id, name])
        if result.returncode == 0:
            return self._without_final_newline(result.stdout)
        if self._no_server(result):
            raise NoServer()
        raise ContractError("operation_failed", clean_message(result.stderr or result.stdout))

    def descriptor(
        self,
        host_id: str,
        generation: str,
        session_id: str,
        *,
        option_names: Iterable[str] = (),
    ) -> Session:
        if not _SESSION_ID.fullmatch(session_id):
            raise ContractError("operation_failed", "tmux returned an invalid session id")
        # Dynamic fields are read independently.  tmux permits unusual external
        # names and paths; this avoids a separator-based protocol entirely.
        created = _int_or_none(self.format(session_id, "#{session_created}", no_server=True))
        if created is None:
            raise ContractError(
                "operation_failed", "tmux returned an invalid session creation time"
            )
        name = self.format(session_id, "#{session_name}", no_server=True)
        activity = _int_or_none(self.format(session_id, "#{session_activity}", no_server=True))
        last_attached = _int_or_none(
            self.format(session_id, "#{session_last_attached}", no_server=True)
        )
        attached = _int_or_none(self.format(session_id, "#{session_attached}", no_server=True))
        windows = _int_or_none(self.format(session_id, "#{session_windows}", no_server=True))
        path = self.format(session_id, "#{session_path}", no_server=True)
        current_window = self.format(session_id, "#{window_name}", no_server=True)
        current_path = self.format(session_id, "#{pane_current_path}", no_server=True)
        pending = self.option(session_id, _PENDING_OPTION) is not None
        selected_options = {name: self.option(session_id, name) for name in option_names}
        return Session(
            SessionReference(host_id, generation, session_id, created),
            name or None,
            activity,
            last_attached,
            attached,
            pending,
            windows,
            path or None,
            current_window or None,
            current_path or None,
            None,
            selected_options if option_names else None,
        )

    def find(self, reference: SessionReference) -> Session:
        try:
            current_generation = self.server_generation()
        except NoServer as error:
            raise ContractError(
                "stale_session", "the selected tmux server is no longer running", reference.host_id
            ) from error
        if current_generation != reference.server_generation:
            raise ContractError(
                "stale_session",
                "the selected tmux server changed; refresh and try again",
                reference.host_id,
            )
        if self.try_run(["has-session", "-t", reference.session_id]).returncode:
            raise ContractError(
                "session_not_found", "the selected tmux session no longer exists", reference.host_id
            )
        if (
            self.format(reference.session_id, "#{session_id}", no_server=True)
            != reference.session_id
        ):
            raise ContractError(
                "stale_session", "the selected tmux session changed", reference.host_id
            )
        descriptor = self.descriptor(reference.host_id, current_generation, reference.session_id)
        if (
            descriptor.reference.created_at != reference.created_at
            or self.server_generation() != reference.server_generation
        ):
            raise ContractError(
                "stale_session",
                "the selected tmux session changed; refresh and try again",
                reference.host_id,
            )
        return descriptor

    def create_detached(self, name: str, cwd: str, command: Sequence[str]) -> tuple[str, int]:
        result = self._run(
            [
                "new-session",
                "-d",
                "-P",
                "-F",
                "#{session_id} #{session_created}",
                "-s",
                name,
                "-c",
                cwd,
                *command,
            ]
        )
        if result.returncode != 0:
            diagnostic = clean_message(result.stderr or result.stdout)
            if (
                "duplicate session" in diagnostic.casefold()
                or "already exists" in diagnostic.casefold()
            ):
                raise ContractError(
                    "session_exists", "a tmux session with that exact name already exists"
                )
            raise ContractError("operation_failed", diagnostic)
        fields = self._without_final_newline(result.stdout).split(" ")
        if len(fields) != 2 or not _SESSION_ID.fullmatch(fields[0]) or not fields[1].isdecimal():
            raise ContractError("operation_failed", "tmux did not return the new session identity")
        return fields[0], int(fields[1])

    def set_option(self, session_id: str, name: str, value: str) -> None:
        validate_user_option(name)
        self.run(["set-option", "-q", "-t", session_id, name, value])

    def unset_option(self, session_id: str, name: str) -> None:
        validate_user_option(name)
        result = self.try_run(["set-option", "-qu", "-t", session_id, name])
        if result.returncode and not self._no_server(result):
            raise ContractError("operation_failed", clean_message(result.stderr or result.stdout))

    def rename(self, session_id: str, name: str) -> None:
        self.run(["rename-session", "-t", session_id, name])

    def kill(self, session_id: str) -> None:
        self.run(["kill-session", "-t", session_id])

    def has_name(self, name: str, *, except_session_id: str | None = None) -> bool:
        try:
            ids = self.session_ids()
        except NoServer:
            return False
        for session_id in ids:
            if (
                session_id != except_session_id
                and self.format(session_id, "#{session_name}", no_server=True) == name
            ):
                return True
        return False
