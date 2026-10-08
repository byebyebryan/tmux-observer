"""Bounded desktop evidence types; no I/O or operation handles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from tmux_observer.native import Session, SessionReference


@dataclass(frozen=True)
class DesktopConfig:
    terminal: tuple[str, ...] = ("kitty",)


def kitty_configured(config: DesktopConfig) -> bool:
    """Return true only when the configured terminal executable is Kitty itself."""
    return bool(config.terminal) and Path(config.terminal[0]).name.casefold() == "kitty"


@dataclass(frozen=True, slots=True)
class _Proc:
    pid: int
    ppid: int
    pgrp: int
    session: int
    tty_nr: int
    start: int
    argv: tuple[str, ...]
    uid: int | None = None


@dataclass(frozen=True, slots=True)
class ViewerTarget:
    """One current owner reference and its local attachment route context."""

    session: Session
    local_owner: bool
    native_hostname: str | None
    remote_route: str | None = None
    remote_executable: str = "ssh"


@dataclass(frozen=True, slots=True)
class LocalViewerObservation:
    state: str
    confidence: str | None = None
    reason: str | None = None
    evidence: str | None = None
    qualified: bool = False

    def as_dict(self) -> dict[str, str]:
        result = {"state": self.state}
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class ViewerObservationBatch:
    observed_at: int
    observations: Mapping[SessionReference, LocalViewerObservation]


@dataclass(frozen=True, slots=True)
class _MetadataState:
    status: str
    reference: SessionReference | None = None
