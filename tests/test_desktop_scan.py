"""Inherited display presence regressions; action tests remain with Tmux Plus."""

# Adapted from rofi-tmux-plus 0.6.0; Copyright (c) 2026 Bryan; MIT.
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from tmux_observer.public import Session, SessionReference
from tmux_observer_client._desktop_scan import DesktopConfig as Config
from tmux_observer_client._desktop_scan import (
    ViewerTarget,
    _ObservationProcessIndex,
    _Proc,
    _read_metadata_detailed,
    _remote_attach_argv,
    observe_local_viewers,
)


def _kitty_window(window_id: int, pid: int, title: str = "other") -> dict[str, object]:
    return {"id": window_id, "pid": pid, "app_id": "kitty", "title": title}


def _proc(pid: int, ppid: int, start: int, tty: int, argv: tuple[str, ...]) -> _Proc:
    return _Proc(pid, ppid, pid, 1, tty, start, argv)


def _observation_session(
    host_id: str = "alpha",
    *,
    session_id: str = "$7",
    name: str = "fixture",
    attached_clients: int | None = 0,
    pending: bool = False,
) -> Session:
    return Session(
        SessionReference(host_id, "tmux-v1:10:20:/tmp/default", session_id, 30),
        name,
        31,
        31,
        attached_clients,
        pending,
        1,
        "/tmp",
        "main",
        "/tmp",
    )


class LocalViewerObservationTests(unittest.TestCase):
    def _observe(
        self,
        windows: list[object],
        processes: dict[int, _Proc],
        targets: tuple[ViewerTarget, ...],
        *,
        clients: dict[str, set[int]] | None = None,
        metadata: dict[int, tuple[dict[str, object] | None, bool, bool]] | None = None,
        children: dict[int, bytes] | None = None,
        unreadable_children: set[int] | None = None,
        incarnations=None,
        failed_clients=False,
        process_after=None,
        final_windows=None,
    ) -> tuple[object, Mock, Mock, list[int], list[int]]:
        tmux = Mock()
        tmux.client_incarnations = incarnations
        if failed_clients:
            tmux.client_pids_by_session.side_effect = OSError("fixture unavailable")
        tmux.client_pids_by_session.return_value = {} if clients is None else clients
        process_reads: list[int] = []
        child_reads: list[int] = []
        metadata_rows = metadata or {}
        child_rows = children or {}
        unreadable = unreadable_children or set()

        def read_process(pid: int) -> _Proc | None:
            process_reads.append(pid)
            if process_after is not None and process_reads.count(pid) > 1:
                return process_after.get(pid)
            return processes.get(pid)

        def read_children(pid: int) -> bytes:
            child_reads.append(pid)
            if pid in unreadable:
                raise PermissionError("fixture process tree is unreadable")
            return child_rows.get(pid, b"")

        with (
            patch(
                "tmux_observer_client._desktop_scan._niri_windows",
                side_effect=[windows, windows if final_windows is None else final_windows],
            ) as niri,
            patch("tmux_observer_client._process_evidence._proc", side_effect=read_process),
            patch(
                "tmux_observer_client._process_evidence._child_bytes",
                autospec=True,
                side_effect=read_children,
            ),
            patch(
                "tmux_observer_client._process_evidence._read_metadata_detailed",
                side_effect=lambda pid: metadata_rows.get(pid, (None, False, True)),
            ),
        ):
            batch = observe_local_viewers(
                targets,
                Config(terminal=("kitty",)),
                local_tmux=tmux,
                now_millis=lambda: 1_234,
            )
        self.assertEqual(niri.call_count, 2)
        return batch, tmux, niri, process_reads, child_reads

    def test_profile_incarnation_and_uid_conflict_cannot_confirm_current_join(self):
        session = _observation_session(attached_clients=1)
        targets = (self._target(session, local=True),)
        processes = {
            10: _proc(10, 1, 100, 0, ("kitty",)),
            20: _proc(20, 10, 200, 41, ("tmux", "attach-session", "-t", "$7")),
        }
        for expected in ((999, 200), (None, 201)):
            result, *_ = self._observe(
                [_kitty_window(101, 10)],
                processes,
                targets,
                clients={"$7": {20}},
                children={10: b"20"},
                incarnations={20: expected},
            )
            self.assertEqual(result.observations[session.reference].state, "unknown")

    def test_process_and_window_reuse_during_capture_revoke_join(self):
        session = _observation_session(attached_clients=1)
        targets = (self._target(session, local=True),)
        processes = {
            10: _proc(10, 1, 100, 0, ("kitty",)),
            20: _proc(20, 10, 200, 41, ("tmux", "attach-session", "-t", "$7")),
        }
        for kwargs in (
            {"process_after": {**processes, 20: _proc(20, 10, 201, 41, ("tmux",))}},
            {"final_windows": [_kitty_window(101, 11)]},
        ):
            result, *_ = self._observe(
                [_kitty_window(101, 10)],
                processes,
                targets,
                clients={"$7": {20}},
                children={10: b"20"},
                **kwargs,
            )
            self.assertEqual(result.observations[session.reference].state, "unknown")

    def test_empty_compositor_with_failed_profile_is_unknown_not_absent(self):
        session = _observation_session()
        result, *_ = self._observe(
            [], {}, (self._target(session, local=True),), failed_clients=True
        )
        self.assertEqual(result.observations[session.reference].state, "unknown")

    def test_title_churn_without_binding_change_preserves_current_evidence(self):
        session = _observation_session("beta", attached_clients=1)
        processes = {
            10: _proc(10, 1, 100, 0, ("kitty",)),
            20: _proc(20, 10, 200, 41, ("ssh", "beta")),
        }
        browser = {"id": 102, "pid": 11, "app_id": "browser", "title": "before"}
        batch, *_ = self._observe(
            [_kitty_window(101, 10, "fixture: before @ beta-native"), browser],
            processes,
            (self._target(session, local=False, route="beta"),),
            children={10: b"20"},
            final_windows=[
                _kitty_window(101, 10, "fixture: after @ beta-native"),
                {**browser, "title": "after"},
            ],
        )
        self.assertEqual(
            batch.observations[session.reference].as_dict(),
            {"state": "open", "confidence": "matched"},
        )

    def test_title_binding_change_and_final_duplicate_revoke_positive_evidence(self):
        session = _observation_session("beta", attached_clients=1)
        window = _kitty_window(101, 10, "fixture: task @ beta-native")
        for final in (
            [_kitty_window(101, 10, "other: task @ beta-native")],
            [window, window],
        ):
            batch, *_ = self._observe(
                [window],
                {
                    10: _proc(10, 1, 100, 0, ("kitty",)),
                    20: _proc(20, 10, 200, 41, ("ssh", "beta")),
                },
                (self._target(session, local=False, route="beta"),),
                children={10: b"20"},
                final_windows=final,
            )
            self.assertEqual(batch.observations[session.reference].state, "unknown")

    def test_irrelevant_windows_start_no_process_scans(self):
        session = _observation_session()
        result, _, _, process_reads, _ = self._observe(
            [{"id": 101, "pid": 10, "app_id": "browser", "title": "other"}],
            {},
            (self._target(session, local=False, route="fixture-route"),),
        )
        self.assertEqual(result.observations[session.reference].state, "none")
        self.assertEqual(process_reads, [])

    @staticmethod
    def _target(session: Session, *, local: bool, route: str | None = None) -> ViewerTarget:
        return ViewerTarget(
            session,
            local,
            "alpha-native" if local else "beta-native.example",
            route,
            "ssh",
        )

    @staticmethod
    def _marked(session: Session) -> tuple[dict[str, object] | None, bool, bool]:
        return (
            {
                "schemaVersion": 1,
                "launchId": "fixture-launch",
                "sessionRef": session.reference.as_dict(),
            },
            True,
            True,
        )

    def test_local_launch_marker_and_old_attach_argv_cannot_override_current_join(self) -> None:
        original = _observation_session(session_id="$7")
        current = _observation_session(session_id="$8")
        targets = (
            self._target(original, local=True),
            self._target(current, local=True),
        )
        batch, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, ("tmux", "attach-session", "-t", "$7")),
            },
            targets,
            clients={"$8": {20}},
            metadata={10: self._marked(original)},
            children={10: b"20"},
        )
        observations = batch.observations
        self.assertEqual(
            observations[original.reference].as_dict(),
            {
                "state": "unknown",
                "reason": "conflicting_metadata",
            },
        )
        self.assertEqual(
            observations[current.reference].as_dict(),
            {
                "state": "open",
                "confidence": "confirmed",
            },
        )

    def test_current_local_pid_join_confirms_nonliteral_attach_argv(self) -> None:
        session = _observation_session()
        target = self._target(session, local=True)
        batch, tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 0, ("tmux", "-C")),
            },
            (target,),
            clients={"$7": {20}},
            children={10: b"20"},
        )
        self.assertEqual(
            batch.observations[session.reference].as_dict(),
            {
                "state": "open",
                "confidence": "confirmed",
            },
        )
        tmux.run.assert_not_called()

    def test_observation_can_confirm_presence_without_a_close_safe_layout_or_handle(self) -> None:
        session = _observation_session(attached_clients=0)
        target = self._target(session, local=True)
        batch, tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, ("tmux", "attach-session", "-t", "$7")),
                21: _proc(21, 10, 201, 42, ("zsh",)),
            },
            (target,),
            clients={"$7": {20}},
            children={10: b"20 21"},
        )
        self.assertEqual(
            batch.observations[session.reference].as_dict(),
            {"state": "open", "confidence": "confirmed"},
        )
        self.assertNotIn("viewerId", batch.observations[session.reference].as_dict())
        tmux.run.assert_not_called()

    def test_marked_remote_is_confirmed_and_qualified_legacy_remote_is_matched(self) -> None:
        session = _observation_session("beta")
        target = self._target(session, local=False, route="beta")
        remote_argv = _remote_attach_argv("ssh", "beta", "$7")
        processes = {
            10: _proc(10, 1, 100, 0, ("kitty",)),
            20: _proc(20, 10, 200, 41, remote_argv),
        }
        window = _kitty_window(101, 10, "fixture: task @ beta-native")
        marked, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [window],
            processes,
            (target,),
            metadata={10: self._marked(session)},
            children={10: b"20"},
        )
        self.assertEqual(
            marked.observations[session.reference].as_dict(),
            {
                "state": "open",
                "confidence": "confirmed",
            },
        )
        legacy, tmux, _niri, _process_reads, _child_reads = self._observe(
            [window], processes, (target,), children={10: b"20"}
        )
        self.assertEqual(
            legacy.observations[session.reference].as_dict(),
            {
                "state": "open",
                "confidence": "matched",
            },
        )
        tmux.client_pids_by_session.assert_not_called()

    def test_fixed_default_remote_launch_accepts_absolute_ssh_path(self):
        session = _observation_session("beta", attached_clients=1)
        target = self._target(session, local=False, route="beta")
        argv = _remote_attach_argv("ssh", "beta", "$7", fixed_default=True)
        result, *_ = self._observe(
            [_kitty_window(101, 10, "fixture: task @ beta-native")],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, ("/usr/bin/ssh", *argv[1:])),
            },
            (target,),
            metadata={10: self._marked(session)},
            children={10: b"20"},
        )
        self.assertEqual(result.observations[session.reference].confidence, "confirmed")
        self.assertTrue(result.observations[session.reference].qualified)

    def test_manual_remote_shell_with_unique_owner_title_is_only_matched(self) -> None:
        session = _observation_session("beta", attached_clients=1)
        other = _observation_session("beta", session_id="$8", name="other", attached_clients=1)
        targets = tuple(self._target(row, local=False, route="beta") for row in (session, other))
        for argv in (("ssh", "beta"), ("/usr/bin/ssh", "-t", "beta"), ("ssh", "-tt", "beta")):
            with self.subTest(argv=argv):
                batch, tmux, _niri, _process_reads, _child_reads = self._observe(
                    [_kitty_window(101, 10, "fixture: task @ beta-native")],
                    {
                        10: _proc(10, 1, 100, 0, ("kitty",)),
                        20: _proc(20, 10, 200, 41, ("zsh",)),
                        30: _proc(30, 20, 300, 41, argv),
                    },
                    targets,
                    children={10: b"20", 20: b"30"},
                )
                self.assertEqual(
                    batch.observations[session.reference].as_dict(),
                    {"state": "open", "confidence": "matched"},
                )
                self.assertEqual(batch.observations[other.reference].as_dict(), {"state": "none"})
                tmux.client_pids_by_session.assert_not_called()
                tmux.run.assert_not_called()

    def test_manual_shell_requires_peer_process_title_and_owner_attachment(self) -> None:
        cases = (
            (("ssh", "other"), 41, 1, "fixture: task @ beta-native"),
            (("ssh", "beta", "sleep 60"), 41, 1, "fixture: task @ beta-native"),
            (("zsh",), 41, 1, "fixture: task @ beta-native"),
            (("ssh", "beta"), 0, 1, "fixture: task @ beta-native"),
            (("ssh", "beta"), 41, 0, "fixture: task @ beta-native"),
            (("ssh", "beta"), 41, None, "fixture: task @ beta-native"),
            (("ssh", "beta"), 41, 1, "other: task @ beta-native"),
            (("ssh", "beta"), 41, 1, "fixture: task @ other-native"),
        )
        for argv, tty, clients, title in cases:
            with self.subTest(argv=argv, tty=tty, clients=clients, title=title):
                session = _observation_session("beta", attached_clients=clients)
                batch, _tmux, _niri, _process_reads, _child_reads = self._observe(
                    [_kitty_window(101, 10, title)],
                    {
                        10: _proc(10, 1, 100, 0, ("kitty",)),
                        20: _proc(20, 10, 200, tty, argv),
                    },
                    (self._target(session, local=False, route="beta"),),
                    children={10: b"20"},
                )
                self.assertNotEqual(batch.observations[session.reference].state, "open")

    def test_manual_shell_cannot_override_conflicts_partial_scan_or_pending(self) -> None:
        session = _observation_session("beta", attached_clients=1)
        other = _observation_session("beta", session_id="$8", attached_clients=1)
        pending = _observation_session("beta", attached_clients=1, pending=True)
        window = _kitty_window(101, 10, "fixture: task @ beta-native")
        cases = (
            (session, {"metadata": {10: self._marked(other)}}, "conflicting_metadata"),
            (session, {"metadata": {10: (None, True, True)}}, "conflicting_metadata"),
            (session, {"metadata": {10: (None, False, False)}}, "process_unavailable"),
            (session, {"unreadable_children": {20}}, "process_unavailable"),
            (pending, {}, "pending_registration"),
        )
        for selected, extra, reason in cases:
            with self.subTest(reason=reason):
                batch, _tmux, _niri, _process_reads, _child_reads = self._observe(
                    [window],
                    {
                        10: _proc(10, 1, 100, 0, ("kitty",)),
                        20: _proc(20, 10, 200, 41, ("ssh", "beta")),
                    },
                    (self._target(selected, local=False, route="beta"),),
                    children={10: b"20"},
                    **extra,
                )
                self.assertEqual(
                    batch.observations[selected.reference].as_dict(),
                    {"state": "unknown", "reason": reason},
                )
        duplicate, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [window, _kitty_window(102, 11, "fixture: task @ beta-native")],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                11: _proc(11, 1, 101, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, ("ssh", "beta")),
                21: _proc(21, 11, 201, 42, ("ssh", "beta")),
            },
            (self._target(session, local=False, route="beta"),),
            children={10: b"20", 11: b"21"},
        )
        self.assertEqual(
            duplicate.observations[session.reference].as_dict(),
            {"state": "unknown", "reason": "ambiguous_match"},
        )

    def test_global_remote_client_count_does_not_imply_a_local_viewer(self) -> None:
        session = _observation_session("beta", attached_clients=4)
        target = self._target(session, local=False, route="beta")
        batch, _tmux, _niri, _process_reads, _child_reads = self._observe([], {}, (target,))
        self.assertEqual(batch.observations[session.reference].as_dict(), {"state": "none"})

    def test_title_collision_and_contradictory_metadata_are_unknown(self) -> None:
        first = _observation_session("beta", name="same")
        second = _observation_session("gamma", name="same")
        first_target = self._target(first, local=False, route="beta")
        second_target = ViewerTarget(second, False, "beta-native.example", "gamma", "ssh")
        collision, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10, "same: task @ beta-native")],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, _remote_attach_argv("ssh", "beta", "$7")),
            },
            (first_target, second_target),
            children={10: b"20"},
        )
        for session in (first, second):
            self.assertEqual(
                collision.observations[session.reference].as_dict(),
                {"state": "unknown", "reason": "ambiguous_match"},
            )

        marked_other = _observation_session("beta", session_id="$8")
        contradictory, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, _remote_attach_argv("ssh", "beta", "$7")),
            },
            (first_target,),
            metadata={10: self._marked(marked_other)},
            children={10: b"20"},
        )
        self.assertEqual(
            contradictory.observations[first.reference].as_dict(),
            {"state": "unknown", "reason": "conflicting_metadata"},
        )

    def test_unreadable_process_or_metadata_and_pending_registration_fail_closed(self) -> None:
        session = _observation_session("beta")
        target = self._target(session, local=False, route="beta")
        unreadable, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {10: _proc(10, 1, 100, 0, ("kitty",))},
            (target,),
            unreadable_children={10},
        )
        self.assertEqual(
            unreadable.observations[session.reference].as_dict(),
            {
                "state": "unknown",
                "reason": "process_unavailable",
            },
        )

        metadata_unreadable, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {
                10: _proc(10, 1, 100, 0, ("kitty",)),
                20: _proc(20, 10, 200, 41, _remote_attach_argv("ssh", "beta", "$7")),
            },
            (target,),
            metadata={10: (None, False, False)},
            children={10: b"20"},
        )
        self.assertEqual(
            metadata_unreadable.observations[session.reference].as_dict(),
            {
                "state": "unknown",
                "reason": "process_unavailable",
            },
        )

        pending, _tmux, _niri, _process_reads, _child_reads = self._observe(
            [_kitty_window(101, 10)],
            {10: _proc(10, 1, 100, 0, ("kitty",))},
            (target,),
            metadata={10: self._marked(session)},
            children={10: b""},
        )
        self.assertEqual(
            pending.observations[session.reference].as_dict(),
            {
                "state": "unknown",
                "reason": "pending_registration",
            },
        )

    def test_boolean_launch_schema_version_is_rejected(self) -> None:
        raw = b'ROFI_TMUX_PLUS_VIEWER_V1={"schemaVersion":true}\0'
        with (
            patch("tmux_observer_client._process_evidence.os.open", return_value=55),
            patch("tmux_observer_client._process_evidence.os.read", return_value=raw),
            patch("tmux_observer_client._process_evidence.os.close"),
        ):
            value, present, readable = _read_metadata_detailed(123)
        self.assertIsNone(value)
        self.assertTrue(present)
        self.assertTrue(readable)

    def test_budget_is_shared_and_never_caches_past_cap_or_deadline(self) -> None:
        with patch("tmux_observer_client._process_evidence._proc", return_value=None) as read_proc:
            capped = _ObservationProcessIndex(process_limit=2)
            self.assertIsNone(capped.proc(10))
            self.assertIsNone(capped.proc(11))
            self.assertIsNone(capped.proc(12))
            self.assertIsNone(capped.proc(13))
        self.assertEqual(len(capped.processes), 2)
        self.assertEqual(read_proc.call_count, 2)

        shared = _ObservationProcessIndex(process_limit=1)
        with (
            patch(
                "tmux_observer_client._process_evidence._proc",
                return_value=_proc(10, 1, 100, 0, ("kitty",)),
            ),
            patch(
                "tmux_observer_client._process_evidence._read_metadata_detailed"
            ) as read_metadata,
        ):
            shared.proc(10)
            result = shared.metadata_state(10)
        self.assertEqual(result.status, "unreadable")
        self.assertFalse(shared.metadata)
        read_metadata.assert_not_called()

        expired = _ObservationProcessIndex(deadline=0)
        with patch("tmux_observer_client._process_evidence._proc") as read_expired:
            self.assertIsNone(expired.proc(10))
            self.assertIsNone(expired.proc(11))
        self.assertFalse(expired.processes)
        read_expired.assert_not_called()
