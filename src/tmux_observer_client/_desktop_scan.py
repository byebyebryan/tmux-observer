"""Read-only desktop orchestration and compatibility imports for extracted roles."""

import json
from pathlib import Path

from tmux_observer._clock import boottime_ms

from ._desktop_matching import _observation_title_targets, _remote_attach_argv, match_viewers
from ._desktop_types import (
    DesktopConfig,
    LocalViewerObservation,
    ViewerObservationBatch,
    ViewerTarget,
    _Proc,
    kitty_configured,
)
from ._errors import ContractError
from ._niri_observation import _niri_windows
from ._process_evidence import (
    _child_bytes,
    _ObservationProcessIndex,
    _proc,
    _read_metadata_detailed,
)

__all__ = [
    "DesktopConfig",
    "LocalViewerObservation",
    "ViewerObservationBatch",
    "ViewerTarget",
    "_ObservationProcessIndex",
    "_Proc",
    "_child_bytes",
    "_proc",
    "_read_metadata_detailed",
    "_remote_attach_argv",
    "observe_local_viewers",
]


class CapturedEvidence:
    """Immutable lookup surface supplied to matching after all process reads."""

    def __init__(self, trees, metadata, incomplete):
        self.trees, self.metadata, self.incomplete = trees, metadata, incomplete

    def tree(self, pid):
        return self.trees.get(pid, (None, (), False))

    def metadata_state(self, pid):
        return self.metadata[pid]


def observe_local_viewers(
    targets, config, *, local_tmux, niri_command=("niri",), now_millis=boottime_ms, deadline=None
):
    observed_at = now_millis()
    refs = {target.session.reference for target in targets}

    def unknown(reason):
        return ViewerObservationBatch(
            observed_at, {ref: LocalViewerObservation("unknown", reason=reason) for ref in refs}
        )

    if not refs:
        return ViewerObservationBatch(observed_at, {})
    if not kitty_configured(config):
        return unknown("unsupported_desktop")
    end = (
        min(boottime_ms() / 1000 + 2, deadline)
        if deadline is not None
        else boottime_ms() / 1000 + 2
    )
    if boottime_ms() / 1000 >= end:
        return unknown("process_unavailable")
    windows = _niri_windows(
        niri_command, timeout_seconds=max(0.001, min(1, end - boottime_ms() / 1000))
    )
    if windows is None:
        return unknown("compositor_unavailable")
    clients = None
    if any(target.local_owner for target in targets):
        try:
            clients = local_tmux.client_pids_by_session()
        except (ContractError, OSError, ValueError, AttributeError):
            pass
    index = _ObservationProcessIndex(deadline=end)
    trees, metadata = {}, {}
    from ._desktop_types import _MetadataState

    title_targets = _observation_title_targets(targets)

    for window in windows:
        if not isinstance(window, dict) or type(window.get("pid")) is not int or window["pid"] <= 0:
            continue
        pid = window["pid"]
        if window.get("app_id") != "kitty" and not title_targets(window.get("title")):
            continue
        trees[pid] = index.tree(pid)
        metadata[pid] = (
            index.metadata_state(pid)
            if window.get("app_id") == "kitty"
            else _MetadataState("absent")
        )
    # Recheck all relevant process incarnations after the shared capture. Only
    # captured immutable evidence reaches the matching policy.
    changed = set()
    attachment_executables = {
        "tmux",
        *(Path(target.remote_executable).name for target in targets if target.remote_executable),
    }
    relevant_pids = (
        set(trees)
        | {
            pid
            for pid, proc in index.processes.items()
            if proc is not None and proc.argv and Path(proc.argv[0]).name in attachment_executables
        }
        | {pid for pids in (clients or {}).values() for pid in pids if pid in index.processes}
    )
    for pid in relevant_pids:
        if not index.revalidate(pid):
            changed.add(pid)
    for pid, (root, tree, complete) in tuple(trees.items()):
        if pid in changed or any(proc.pid in changed for proc in tree):
            trees[pid] = (None, (), False)
            index.incomplete = True
    final_windows = _niri_windows(
        niri_command, timeout_seconds=max(0.001, min(1, end - boottime_ms() / 1000))
    )

    def identities(rows):
        return sorted(
            json.dumps(
                [
                    row.get("id"),
                    row.get("pid"),
                    row.get("app_id"),
                    sorted(
                        json.dumps(ref.as_dict(), sort_keys=True)
                        for ref in title_targets(row.get("title"))
                    ),
                ],
                sort_keys=True,
            )
            for row in rows
            if isinstance(row, dict) and type(row.get("id")) is int
        )

    def duplicate_ids(rows):
        ids = [row["id"] for row in rows if isinstance(row, dict) and type(row.get("id")) is int]
        return len(ids) != len(set(ids))

    if (
        final_windows is None
        or duplicate_ids(windows)
        or duplicate_ids(final_windows)
        or identities(windows) != identities(final_windows)
        or boottime_ms() / 1000 >= end
    ):
        return unknown("process_unavailable")
    return match_viewers(
        targets,
        windows=windows,
        index=CapturedEvidence(trees, metadata, index.incomplete),
        local_client_pids=clients,
        client_incarnations=getattr(local_tmux, "client_incarnations", None),
        observed_at=observed_at,
        now_millis=now_millis,
    )
