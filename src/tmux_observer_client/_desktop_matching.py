"""Pure association matching; no compositor, process, native or action I/O."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from tmux_observer.native import SessionReference

from ._desktop_types import (
    LocalViewerObservation,
    ViewerObservationBatch,
    ViewerTarget,
    _MetadataState,
)


def _is_tmux_attach(argv: Sequence[str], session_id: str) -> bool:
    if not argv or Path(argv[0]).name != "tmux":
        return False
    return len(argv) >= 5 and "attach-session" in argv and argv[-2:] == ("-t", session_id)


def _remote_attach_argv(
    executable: str, route: str, session_id: str, *, fixed_default=False
) -> tuple[str, ...]:
    # Match the process argv used by RemoteLifecycle._launch. OpenSSH receives
    # one remote shell command whose session ID is quoted as a literal target.
    import shlex

    server = ("-L", "default") if fixed_default else ()
    remote = " ".join(
        shlex.quote(item) for item in ("tmux", "-u", *server, "attach-session", "-t", session_id)
    )
    return (Path(executable).name, "-t", route, remote)


def _observation_title_targets(
    targets: Sequence[ViewerTarget],
) -> Callable[[object], set[SessionReference]]:
    by_hostname: dict[str, list[ViewerTarget]] = {}
    for target in targets:
        if not target.session.name or not target.native_hostname:
            continue
        hostname = target.native_hostname.split(".", 1)[0].casefold()
        by_hostname.setdefault(hostname, []).append(target)

    def matching(value: object) -> set[SessionReference]:
        if not isinstance(value, str):
            return set()
        title = value.casefold()
        result: set[SessionReference] = set()
        for hostname, rows in by_hostname.items():
            if not title.rstrip().endswith(f"@ {hostname}"):
                continue
            for target in rows:
                name = target.session.name
                if name and title.startswith(f"{name.casefold()}:"):
                    result.add(target.session.reference)
        return result

    return matching


def match_viewers(
    targets,
    *,
    windows,
    index,
    local_client_pids,
    client_incarnations=None,
    observed_at=0,
    now_millis=lambda: 0,
):
    """Pure policy over captured compositor/process/native input evidence."""
    unique = {target.session.reference: target for target in targets}
    refs = tuple(unique)
    title_targets = _observation_title_targets(tuple(unique.values()))
    targets_by_ref = unique
    local_by_session_id: dict[str, ViewerTarget] = {
        target.session.reference.session_id: target
        for target in unique.values()
        if target.local_owner
    }
    client_owner_by_pid: dict[int, ViewerTarget] = {}
    if local_client_pids is not None:
        for session_id, pids in local_client_pids.items():
            target = local_by_session_id.get(session_id)
            if target is None:
                continue
            for pid in pids:
                client_owner_by_pid[pid] = target
    remote_by_argv: dict[tuple[str, ...], ViewerTarget] = {}
    remote_shell_by_argv: dict[tuple[str, ...], set[SessionReference]] = {}
    unsupported_remote: set[SessionReference] = set()
    for target in unique.values():
        if target.local_owner:
            continue
        if not target.remote_route:
            unsupported_remote.add(target.session.reference)
            continue
        for fixed_default in (False, True):
            argv = _remote_attach_argv(
                target.remote_executable,
                target.remote_route,
                target.session.reference.session_id,
                fixed_default=fixed_default,
            )
            remote_by_argv[argv] = target
        # A manually opened SSH shell does not name a tmux target. With a
        # current owner attachment and a unique matching title it can supply
        # only qualified display presence, never a verified operation handle.
        if target.session.attached_clients is not None and target.session.attached_clients > 0:
            for tty_options in ((), ("-t",), ("-tt",)):
                shell_argv = (
                    Path(target.remote_executable).name,
                    *tty_options,
                    target.remote_route,
                )
                remote_shell_by_argv.setdefault(shell_argv, set()).add(target.session.reference)

    confirmed: set[SessionReference] = set()
    qualified_launch: set[SessionReference] = set()
    matched_windows: dict[SessionReference, set[tuple[int, int]]] = {}
    unresolved: dict[SessionReference, set[str]] = {}
    scan_incomplete = False

    def add_unknown(reference: SessionReference, reason: str) -> None:
        unresolved.setdefault(reference, set()).add(reason)

    for row in windows:
        if not isinstance(row, dict):
            scan_incomplete = True
            continue
        app_id = row.get("app_id")
        window_id = row.get("id")
        window_pid = row.get("pid")
        if not isinstance(app_id, str):
            scan_incomplete = True
            continue
        if (
            type(window_id) is not int
            or window_id <= 0
            or type(window_pid) is not int
            or window_pid <= 0
        ):
            if app_id == "kitty":
                scan_incomplete = True
            continue
        title_refs = title_targets(row.get("title"))
        if app_id != "kitty" and not title_refs:
            continue

        root, tree, complete = index.tree(window_pid)
        if not complete and app_id == "kitty":
            scan_incomplete = True
        if root is None:
            for reference in title_refs:
                add_unknown(reference, "process_unavailable")
            continue
        if app_id == "kitty" and (not root.argv or Path(root.argv[0]).name != "kitty"):
            for reference in title_refs:
                add_unknown(reference, "process_unavailable")
            if title_refs:
                scan_incomplete = True
            continue

        process_refs: set[SessionReference] = set()
        local_exact_refs: set[SessionReference] = set()
        local_argv_refs: set[SessionReference] = set()
        local_conflict_refs: set[SessionReference] = set()
        remote_shell_refs: set[SessionReference] = set()
        for proc in tree:
            current_local_target = client_owner_by_pid.get(proc.pid)
            if current_local_target is not None and client_incarnations is not None:
                expected = client_incarnations.get(proc.pid)
                if expected != (proc.uid, proc.start):
                    add_unknown(current_local_target.session.reference, "process_unavailable")
                    current_local_target = None
            if current_local_target is not None:
                current_ref = current_local_target.session.reference
                local_exact_refs.add(current_ref)
                process_refs.add(current_ref)
            if proc.tty_nr == 0:
                continue
            if proc.argv:
                shell_argv = (Path(proc.argv[0]).name, *proc.argv[1:])
                remote_shell_refs.update(
                    title_refs.intersection(remote_shell_by_argv.get(shell_argv, ()))
                )
            target: ViewerTarget | None = None
            if proc.argv and Path(proc.argv[0]).name == "tmux":
                for session_id, local_target in local_by_session_id.items():
                    if _is_tmux_attach(proc.argv, session_id):
                        target = local_target
                        local_argv_refs.add(target.session.reference)
                        if (
                            current_local_target is not None
                            and current_local_target.session.reference != target.session.reference
                        ):
                            local_conflict_refs.add(target.session.reference)
                        break
            if target is None:
                remote_target = (
                    remote_by_argv.get((Path(proc.argv[0]).name, *proc.argv[1:]))
                    if proc.argv
                    else None
                )
                if remote_target is not None:
                    process_refs.add(remote_target.session.reference)

        metadata = (
            index.metadata_state(window_pid) if app_id == "kitty" else _MetadataState("absent")
        )
        marker_ref = metadata.reference if metadata.status == "valid" else None
        if marker_ref in targets_by_ref and local_exact_refs and marker_ref not in local_exact_refs:
            local_conflict_refs.add(marker_ref)  # type: ignore[arg-type]
        candidates = title_refs | process_refs | local_argv_refs | local_conflict_refs
        if len(title_refs) > 1:
            for reference in title_refs:
                add_unknown(reference, "ambiguous_match")
        if marker_ref in targets_by_ref:
            candidates.add(marker_ref)  # type: ignore[arg-type]
        for reference in candidates:
            if reference not in targets_by_ref:
                continue
            target = targets_by_ref[reference]
            attached = reference in process_refs
            local_exact = reference in local_exact_refs
            local_argv = reference in local_argv_refs
            local_conflict = reference in local_conflict_refs
            title_match = reference in title_refs
            if app_id != "kitty":
                add_unknown(reference, "unsupported_desktop")
                continue
            if reference in unsupported_remote:
                add_unknown(reference, "attachment_unverified")
                continue
            if metadata.status == "unreadable":
                add_unknown(reference, "process_unavailable")
                continue
            if metadata.status == "invalid":
                add_unknown(reference, "conflicting_metadata")
                continue
            # A current local tmux client PID-to-session join is the live
            # attachment authority.  Kitty launch metadata and argv can name
            # the session the client originally attached before switching.
            if target.local_owner and local_exact:
                confirmed.add(reference)
                continue
            if metadata.status == "valid":
                if marker_ref != reference:
                    if title_match or attached or local_exact or local_argv or local_conflict:
                        add_unknown(reference, "conflicting_metadata")
                    continue
                if target.local_owner and local_conflict:
                    add_unknown(reference, "conflicting_metadata")
                elif target.local_owner:
                    reason = (
                        "attachment_unverified"
                        if local_client_pids is None
                        else "pending_registration"
                    )
                    add_unknown(reference, reason)
                elif attached:
                    confirmed.add(reference)
                    if title_match and len(title_refs) == 1:
                        qualified_launch.add(reference)
                else:
                    add_unknown(reference, "pending_registration")
                continue
            # With no marker, only the live local tmux client/session join is
            # enough for Confirmed. Legacy matches stay qualified by title and
            # an observed attachment process.
            if local_exact:
                confirmed.add(reference)
            elif local_conflict:
                add_unknown(reference, "conflicting_metadata")
            elif target.local_owner and (local_argv or title_match):
                add_unknown(
                    reference,
                    "attachment_unverified"
                    if local_client_pids is None
                    else "pending_registration",
                )
            elif (attached or reference in remote_shell_refs) and title_match:
                matched_windows.setdefault(reference, set()).add((window_id, window_pid))
            elif attached or title_match:
                add_unknown(reference, "attachment_unverified")

    for reference in refs:
        target = targets_by_ref[reference]
        if target.local_owner and local_client_pids is None:
            add_unknown(reference, "attachment_unverified")
        if target.session.pending and reference not in confirmed:
            add_unknown(reference, "pending_registration")
        if reference in confirmed:
            continue
        if scan_incomplete or index.incomplete:
            add_unknown(reference, "process_unavailable")

    observations: dict[SessionReference, LocalViewerObservation] = {}
    for reference in refs:
        if reference in confirmed:
            observations[reference] = LocalViewerObservation(
                "open",
                confidence="confirmed",
                evidence="current_native_association"
                if targets_by_ref[reference].local_owner
                else "launch_reference",
                qualified=reference in qualified_launch,
            )
            continue
        candidates = matched_windows.get(reference, set())
        reasons = unresolved.get(reference, set())
        if len(candidates) > 1:
            reasons.add("ambiguous_match")
        if reasons:
            priority = (
                "ambiguous_match",
                "conflicting_metadata",
                "pending_registration",
                "process_unavailable",
                "unsupported_desktop",
                "attachment_unverified",
            )
            reason = next((item for item in priority if item in reasons), "inventory_incomplete")
            observations[reference] = LocalViewerObservation("unknown", reason=reason)
        elif len(candidates) == 1:
            observations[reference] = LocalViewerObservation(
                "open", confidence="matched", evidence="qualified_title", qualified=True
            )
        else:
            observations[reference] = LocalViewerObservation("none")

    return ViewerObservationBatch(now_millis(), observations)
