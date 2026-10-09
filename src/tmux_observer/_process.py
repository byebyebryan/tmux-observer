"""Bounded native read processes with a single absolute BOOTTIME deadline."""

from __future__ import annotations

import os
import re
import selectors
import signal
import subprocess
from dataclasses import dataclass

from ._clock import boottime_ms

READ_FIELDS = frozenset(
    (
        "socket_path",
        "start_time",
        "pid",
        "session_id",
        "session_created",
        "session_name",
        "session_activity",
        "session_last_attached",
        "session_attached",
        "session_windows",
        "session_path",
        "window_name",
        "pane_current_path",
        "pane_id",
        "pane_pid",
        "pane_current_command",
        "client_pid",
    )
)


READ_COMMAND_LIMIT = 64


def allowed_read(args: list[str]) -> bool:
    """Admit bounded chains only when every individual command is a read."""
    commands, current = [], []
    for argument in args:
        if argument == ";":
            commands.append(current)
            current = []
        else:
            current.append(argument)
    commands.append(current)
    return len(commands) <= READ_COMMAND_LIMIT and all(_allowed_command(row) for row in commands)


def _allowed_command(args: list[str]) -> bool:
    if not args:
        return False
    if args[0] == "show-options":
        return (
            len(args) == 5
            and args[1:3] == ["-q", "-t"]
            and re.fullmatch(r"\$[0-9]+", args[3]) is not None
            and re.fullmatch(r"@[A-Za-z0-9_.-]+", args[4]) is not None
        )
    if args[0] == "display-message":
        valid = (
            len(args) == 3
            and args[1] == "-p"
            or len(args) == 5
            and args[1:3] == ["-p", "-t"]
            and re.fullmatch(r"[$%][0-9]+", args[3]) is not None
        )
    elif args[0] == "list-sessions" or args[0] == "list-clients":
        valid = len(args) == 3 and args[1] == "-F"
    elif args[0] == "list-panes":
        valid = (
            len(args) == 4
            and args[1:3] == ["-a", "-F"]
            or len(args) == 5
            and args[1] == "-t"
            and re.fullmatch(r"\$[0-9]+", args[2]) is not None
            and args[3] == "-F"
        )
    else:
        return False
    if not valid:
        return False
    for part in args[-1].split("\t"):
        match = re.fullmatch(r"#\{(?:q/a:)?([a-z_]+)\}", part)
        if match is None or match[1] not in READ_FIELDS:
            return False
    return True


class ProcessError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


class ReadRunner:
    """Fixed server/environment. A private prefix is injectable for owned tests."""

    def __init__(self, prefix: tuple[str, ...] = ("tmux", "-u", "-L", "default")):
        self.prefix = prefix
        self.env = dict(os.environ)
        for key in ("TMUX", "TMUX_PANE"):
            self.env.pop(key, None)
        # Keep deterministic English diagnostics while preserving UTF-8 names
        # and the tab separators in metadata formats (the default prefix uses -u).
        self.env["LC_ALL"] = "C"

    def __call__(self, args: list[str], deadline: int) -> Completed:
        if not allowed_read(args):
            raise ValueError("non-read command rejected")
        if boottime_ms() >= deadline:
            raise ProcessError("deadline", "native read exceeded its deadline")
        try:
            process = subprocess.Popen(
                [*self.prefix, *args],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                start_new_session=True,
            )
        except FileNotFoundError as error:
            raise ProcessError("tmux_missing", "tmux executable is unavailable") from error
        except OSError as error:
            raise ProcessError("execution_failed", "native read could not start") from error
        buffers = [bytearray(), bytearray()]
        try:
            with selectors.DefaultSelector() as selector:
                for index, stream in enumerate((process.stdout, process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, index)
                while selector.get_map():
                    remaining = deadline - boottime_ms()
                    if remaining <= 0:
                        raise ProcessError("deadline", "native read exceeded its deadline")
                    for key, _events in selector.select(min(remaining / 1000, 0.05)):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        buffers[key.data].extend(chunk)
                        if len(buffers[key.data]) > (1_048_576 if key.data == 0 else 65_536):
                            raise ProcessError(
                                "output_limit", "native read exceeded its output limit"
                            )
                while process.poll() is None:
                    remaining = deadline - boottime_ms()
                    if remaining <= 0:
                        raise ProcessError("deadline", "native read exceeded its deadline")
                    try:
                        process.wait(timeout=min(remaining / 1000, 0.05))
                    except subprocess.TimeoutExpired:
                        pass
                if boottime_ms() >= deadline:
                    raise ProcessError("deadline", "late native output rejected")
                return Completed(
                    process.returncode, *(bytes(b).decode("utf-8", "strict") for b in buffers)
                )
        except UnicodeError as error:
            raise ProcessError("malformed_metadata", "native output is not UTF-8") from error
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdout.close()
            process.stderr.close()
