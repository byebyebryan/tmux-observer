"""Qualified focus needs unique, current and compatible action evidence."""

import unittest
from dataclasses import replace
from unittest.mock import patch

from tmux_observer_actions.desktop_action import focus_session_window, focus_verified
from tmux_observer_actions.errors import ContractError
from tmux_observer_actions.model import Session, SessionReference
from tmux_observer_actions.viewer_service import Viewer, ViewerInspection, _Proc


class FreshFocusTests(unittest.TestCase):
    def setUp(self):
        self.session = Session(
            SessionReference("owner", "generation", "$0", 1),
            "owned",
            1,
            1,
            1,
            False,
            1,
            "/tmp",
            "main",
            "/tmp",
        )
        self.window = {"id": 7, "pid": 10, "app_id": "kitty", "title": "owned: work @ owner"}
        self.root = _Proc(10, 1, 10, 1, 0, 2, ("kitty",), 1000)
        self.client = _Proc(20, 10, 20, 1, 4, 3, ("ssh", "owner-route"), 1000)

    def _focus(self, windows, process=None):
        with (
            patch("tmux_observer_actions.desktop_action._niri_windows", side_effect=windows),
            patch(
                "tmux_observer_actions.desktop_action._proc",
                side_effect=process or {10: self.root, 20: self.client}.get,
            ),
            patch(
                "tmux_observer_actions.desktop_action._process_tree",
                return_value=([self.client], True),
            ),
            patch("tmux_observer_actions.desktop_action.focus_window", return_value=True) as focus,
        ):
            try:
                result = focus_session_window(
                    "owned", "owner", session=self.session, remote_route="owner-route"
                )
            except ContractError as error:
                return error, focus
        return result, focus

    def test_qualified_manual_ssh_can_focus_without_a_close_handle(self):
        result, focus = self._focus(
            [[self.window], [{**self.window, "title": "owned: changed command @ owner"}]]
        )
        self.assertIs(result, True)
        focus.assert_called_once_with(7, niri_command=("niri",))

    def test_duplicate_titles_never_focus_first_match(self):
        result, focus = self._focus([[self.window, {**self.window, "id": 8, "pid": 11}]])
        self.assertEqual(result.code, "viewer_ambiguous")
        focus.assert_not_called()

    def test_closing_capture_duplicate_and_reused_window_revoke_focus(self):
        for closing in ([self.window, {**self.window, "id": 8}], [{**self.window, "pid": 11}]):
            result, focus = self._focus([[self.window], closing])
            self.assertIsInstance(result, ContractError)
            focus.assert_not_called()

    def test_process_birth_change_and_incompatible_route_cannot_focus(self):
        reads = []

        def changed(pid):
            reads.append(pid)
            if pid == 10:
                return self.root
            return replace(self.client, start=self.client.start + 1)

        result, focus = self._focus([[self.window]], changed)
        self.assertEqual(result.code, "viewer_stale")
        focus.assert_not_called()
        self.client = replace(self.client, argv=("ssh", "other-route"))
        result, focus = self._focus([[self.window]])
        self.assertIs(result, False)
        focus.assert_not_called()

    def test_verified_handle_rechecks_exact_process_and_window_before_focus(self):
        attachment = replace(self.client, argv=("tmux", "attach-session", "-t", "$0"))
        viewer = Viewer(
            "tv1_" + "a" * 43,
            7,
            10,
            2,
            20,
            3,
            "owned-launch",
            self.session.reference.as_dict(),
            attachment.argv,
            4,
        )
        inspection = ViewerInspection("verified", (viewer,), True)
        with (
            patch(
                "tmux_observer_actions.desktop_action._proc",
                side_effect={10: self.root, 20: attachment}.get,
            ),
            patch("tmux_observer_actions.desktop_action._niri_windows", return_value=[self.window]),
            patch("tmux_observer_actions.desktop_action.focus_window", return_value=True) as focus,
        ):
            self.assertTrue(focus_verified(viewer, revalidate=lambda: inspection))
        focus.assert_called_once()
        with (
            patch("tmux_observer_actions.desktop_action.focus_window") as focus,
            self.assertRaises(ContractError),
        ):
            focus_verified(
                viewer,
                revalidate=lambda: replace(
                    inspection, viewers=(viewer, replace(viewer, window_id=8))
                ),
            )
        focus.assert_not_called()
