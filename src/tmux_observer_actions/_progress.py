"""Per-call effect accounting, independent of native facts or UI state."""

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class Progress:
    operation: str
    reference: dict | None = None
    host_id: str | None = None
    outcome: dict = field(
        default_factory=lambda: {
            "nativeEffect": "none",
            "terminalSpawn": "not_requested",
            "attachment": "not_requested",
            "focus": "not_requested",
            "viewerClose": "not_requested",
            "transport": "local",
        }
    )


current = ContextVar("tmux_action_progress", default=None)


def mark(key, value):
    progress = current.get()
    if progress is not None:
        previous = progress.outcome[key]
        progress.outcome[key] = value
        return previous
    return None


def native_started():
    progress = current.get()
    if (
        progress is not None
        and progress.operation in ("create", "rename", "kill")
        and progress.outcome["nativeEffect"] != "confirmed"
    ):
        return mark("nativeEffect", "uncertain")
    return None


def native_confirmed(reference):
    progress = current.get()
    if progress is not None:
        progress.reference = reference.as_dict()
        mark("nativeEffect", "confirmed")
