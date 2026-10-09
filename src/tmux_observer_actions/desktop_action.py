"""Fresh, uniquely compatible focus targets. No passive presence authorizes it."""

from pathlib import Path

from tmux_observer_client._desktop_context import context_fingerprint

from ._progress import mark
from .errors import ContractError
from .viewer_service import (
    _niri_windows,
    _proc,
    _process_tree,
    _remote_attach_matches,
    _title_matches,
    focus_window,
)


def focus_verified(viewer, *, revalidate, niri_command=("niri",)):
    context = context_fingerprint("action")
    current = revalidate()
    if current.status != "verified" or len(current.viewers) != 1:
        mark("focus", "ambiguous")
        raise ContractError("viewer_ambiguous", "viewer identity is no longer unique")
    if current.viewers[0] != viewer:
        raise ContractError("viewer_stale", "viewer identity changed before focus")
    root, attachment = _proc(viewer.window_pid), _proc(viewer.attachment_pid)
    windows = _niri_windows(niri_command)
    if (
        root is None
        or attachment is None
        or root.start != viewer.window_start
        or attachment.start != viewer.attachment_start
        or attachment.ppid != viewer.window_pid
        or attachment.argv != viewer.attachment_argv
        or attachment.tty_nr != viewer.tty_nr
        or windows is None
        or sum(
            row.get("id") == viewer.window_id
            and row.get("pid") == viewer.window_pid
            and row.get("app_id") == "kitty"
            for row in windows
            if isinstance(row, dict)
        )
        != 1
    ):
        raise ContractError("viewer_stale", "viewer process/window identity changed before focus")
    if context_fingerprint("action") != context:
        raise ContractError("viewer_stale", "desktop context changed before focus")
    focused = focus_window(viewer.window_id, niri_command=niri_command)
    mark("focus", "confirmed" if focused else "failed")
    return focused


def focus_session_window(
    session_name,
    native_hostname,
    *,
    session=None,
    local_tmux=None,
    remote_route=None,
    remote_executable="ssh",
    niri_command=("niri",),
    validate_session=None,
):
    """Qualified focus is an action result, not confirmed session binding."""
    if session is None or session.name != session_name:
        return False
    context = context_fingerprint("action")
    windows = _niri_windows(niri_command)
    if windows is None:
        return False

    def candidates(rows):
        return [
            row
            for row in rows
            if isinstance(row, dict) and _title_matches(row.get("title"), session, native_hostname)
        ]

    rows = candidates(windows)
    if len(rows) > 1:
        mark("focus", "ambiguous")
        raise ContractError(
            "viewer_ambiguous",
            "multiple matching windows require explicit new-view intent",
            session.reference.host_id,
        )
    if not rows:
        return False
    row = rows[0]
    if (
        type(row.get("id")) is not int
        or type(row.get("pid")) is not int
        or row.get("app_id") != "kitty"
    ):
        return False
    root = _proc(row["pid"])
    if root is None or not root.argv or Path(root.argv[0]).name != "kitty":
        return False
    tree, complete = _process_tree(root.pid)
    if not complete:
        return False
    if remote_route is None:
        if local_tmux is None:
            return False
        # Native reference and attachment are freshly read without a service.
        local_tmux.find(session.reference)
        pids = set(local_tmux.client_pids(session.reference.session_id))
        compatible = [proc for proc in tree if proc.pid in pids]
    else:
        if not session.attached_clients:
            return False
        shells = {
            (Path(remote_executable).name, *tty, remote_route) for tty in ((), ("-t",), ("-tt",))
        }
        compatible = [
            proc
            for proc in tree
            if proc.tty_nr
            and proc.argv
            and (
                _remote_attach_matches(
                    proc.argv, remote_executable, remote_route, session.reference.session_id
                )
                or (Path(proc.argv[0]).name, *proc.argv[1:]) in shells
            )
        ]
    if not compatible:
        return False
    if _proc(root.pid) != root or any(_proc(proc.pid) != proc for proc in compatible):
        raise ContractError("viewer_stale", "compatible process identity changed before focus")
    if validate_session is not None:
        native = validate_session()
        if (
            native.reference != session.reference
            or remote_route is not None
            and not native.attached_clients
        ):
            raise ContractError("viewer_stale", "native session changed before focus")
    closing = _niri_windows(niri_command)
    if closing is None:
        return False
    final = candidates(closing)
    if len(final) != 1:
        mark("focus", "ambiguous")
        raise ContractError("viewer_ambiguous", "matching window identity is no longer unique")
    if any(final[0].get(key) != row.get(key) for key in ("id", "pid", "app_id")):
        raise ContractError("viewer_stale", "matching window identity changed before focus")
    if local_tmux is not None:
        local_tmux.find(session.reference)
        current = set(local_tmux.client_pids(session.reference.session_id))
        if not any(proc.pid in current for proc in compatible):
            raise ContractError("viewer_stale", "native attachment changed before focus")
    if context_fingerprint("action") != context:
        raise ContractError("viewer_stale", "desktop context changed before focus")
    focused = focus_window(row["id"], niri_command=niri_command)
    mark("focus", "confirmed" if focused else "failed")
    return focused
