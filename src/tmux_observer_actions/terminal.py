"""Single-dispatch terminal adapter; accepted spawn is not attachment proof."""

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence

from ._progress import mark
from .config import Config


def _terminal_argv(config: Config, command: Sequence[str], *, systemd_run: str | None) -> list[str]:
    """Build terminal argv without allowing systemd-run to expand ``$N`` IDs."""
    terminal = [*config.terminal, "-e", *command]
    if systemd_run is None:
        return terminal
    return [
        systemd_run,
        "--user",
        "--scope",
        "--collect",
        "--quiet",
        "--expand-environment=no",
        "--",
        *terminal,
    ]


def spawn_terminal_command(
    config: Config, command: Sequence[str], *, env: Mapping[str, str] | None = None
) -> None:
    """Detach a terminal command in a collectable user scope when available."""
    argv = _terminal_argv(config, command, systemd_run=shutil.which("systemd-run"))
    child_env = os.environ.copy()
    if env is not None:
        child_env.update(env)
    child_env.pop("TMUX", None)
    child_env.pop("TMUX_PANE", None)
    mark("terminalSpawn", "uncertain")
    try:
        subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            env=child_env,
        )
    except OSError:
        mark("terminalSpawn", "failed")
        raise
    mark("terminalSpawn", "confirmed")
    mark("attachment", "unverified")
