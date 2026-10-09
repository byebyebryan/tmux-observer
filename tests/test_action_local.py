# Extracted action regressions from Tmux Plus; Copyright (c) 2026 Bryan; MIT.
"""Inherited full-reference/holding-wrapper/rollback native action regressions."""

import os
import secrets
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tmux_observer_actions.config import Config
from tmux_observer_actions.errors import ContractError, NoServer
from tmux_observer_actions.host import local_host
from tmux_observer_actions.lifecycle import LocalLifecycle
from tmux_observer_actions.tmux import TmuxClient


class IsolatedServer(unittest.TestCase):
    def setUp(self) -> None:
        self._original_shell = os.environ.get("SHELL")
        os.environ["SHELL"] = "/bin/sh"
        self.socket = f"rofi-tmux-plus-test-{secrets.token_hex(8)}"
        self.argv = ("tmux", "-L", self.socket, "-f", "/dev/null")
        self.client = TmuxClient(self.argv, timeout_seconds=2)
        self.host = local_host("Local.Example")
        self.lifecycle = LocalLifecycle(
            self.client,
            Config(terminal=("true",)),
            host=self.host,
            niri_command=("definitely-not-niri",),
            terminal_spawner=lambda _session_id: None,
        )

    def tearDown(self) -> None:
        # Exact generated socket only; this never addresses the user's default
        # server.  The executable prefix is asserted in the test below too.
        subprocess.run(
            [*self.argv, "kill-server"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if self._original_shell is None:
            os.environ.pop("SHELL", None)
        else:
            os.environ["SHELL"] = self._original_shell

    def create_direct(self, name: str = "alpha") -> tuple[str, int]:
        return self.client.create_detached(name, "/tmp", ["/bin/sh", "-c", "sleep 30"])

    def test_open_accepts_external_rename_but_mutations_require_observed_name(self) -> None:
        self.create_direct("before")
        _generation = self.client.server_generation()
        sessions = [self.client.descriptor(self.host.host_id, _generation, "$0")]
        reference = sessions[0].reference
        self.client.rename(reference.session_id, "after")
        opened = self.lifecycle.open(
            self.host.host_id,
            None,
            reference.server_generation,
            reference.session_id,
            reference.created_at,
        )
        self.assertTrue(opened["terminalLaunched"])
        self.assertEqual(
            set(opened),
            {"schemaVersion", "ok", "meshRevision", "session", "focused", "terminalLaunched"},
        )
        self.assertNotIn("options", opened["session"])
        with self.assertRaisesRegex(ContractError, "selected tmux session changed"):
            self.lifecycle.rename(
                self.host.host_id,
                None,
                reference.server_generation,
                reference.session_id,
                reference.created_at,
                "before",
                "new",
            )

    def test_open_required_options_match_before_focus_or_terminal_launch(self) -> None:
        self.create_direct()
        generation = self.client.server_generation()
        sessions = [self.client.descriptor(self.host.host_id, generation, "$0")]
        self.assertIsNotNone(generation)
        reference = sessions[0].reference
        self.client.set_option(reference.session_id, "@provider", "expected")
        focused = MagicMock(return_value=True)
        spawned = MagicMock()
        lifecycle = LocalLifecycle(
            self.client,
            Config(terminal=("true",)),
            host=self.host,
            terminal_spawner=spawned,
        )
        lifecycle._focus_matching_window = focused  # type: ignore[method-assign]

        opened = lifecycle.open(
            self.host.host_id,
            None,
            reference.server_generation,
            reference.session_id,
            reference.created_at,
            required_options=(("@provider", "expected"),),
        )
        self.assertTrue(opened["focused"])
        self.assertNotIn("options", opened["session"])
        focused.assert_called_once()
        spawned.assert_not_called()

        focused.reset_mock()
        self.client.unset_option(reference.session_id, "@provider")
        with self.assertRaises(ContractError) as missing:
            lifecycle.open(
                self.host.host_id,
                None,
                reference.server_generation,
                reference.session_id,
                reference.created_at,
                required_options=(("@provider", "expected"),),
            )
        self.assertEqual(missing.exception.code, "stale_session")
        focused.assert_not_called()
        spawned.assert_not_called()

        self.client.set_option(reference.session_id, "@provider", "different")
        with self.assertRaises(ContractError) as mismatched:
            lifecycle.open(
                self.host.host_id,
                None,
                reference.server_generation,
                reference.session_id,
                reference.created_at,
                required_options=(("@provider", "expected"),),
            )
        self.assertEqual(mismatched.exception.code, "stale_session")
        focused.assert_not_called()
        spawned.assert_not_called()

    def test_restart_with_reused_id_is_stale(self) -> None:
        self.create_direct("first")
        _generation = self.client.server_generation()
        sessions = [self.client.descriptor(self.host.host_id, _generation, "$0")]
        old = sessions[0].reference
        self.client.try_run(["kill-server"])
        time.sleep(0.1)
        self.create_direct("second")
        with self.assertRaisesRegex(ContractError, "tmux server changed"):
            self.lifecycle.open(
                self.host.host_id, None, old.server_generation, old.session_id, old.created_at
            )

    def test_create_default_and_collision(self) -> None:
        made = self.lifecycle.create(
            self.host.host_id, None, "managed", "/tmp", [("@provider", "x")], [], False, None, False
        )
        self.assertFalse(made["session"]["pending"])
        self.assertNotIn("options", made["session"])
        self.assertEqual(self.client.option(made["session"]["sessionId"], "@provider"), "x")
        with self.assertRaisesRegex(ContractError, "exact name already exists"):
            self.lifecycle.create(
                self.host.host_id, None, "managed", "/tmp", [], [], False, None, False
            )

    def test_invalid_cwd_never_falls_back(self) -> None:
        with self.assertRaisesRegex(ContractError, "cwd must name an existing directory"):
            self.lifecycle.create(
                self.host.host_id,
                None,
                "managed",
                "/definitely/not/a/directory",
                [],
                [],
                False,
                None,
                False,
            )

    def test_first_post_token_metadata_failure_rolls_back_exact_session(self) -> None:
        original = self.client.set_option

        def fail_after_guard(session_id: str, name: str, value: str) -> None:
            if name == "@fail":
                raise ContractError("operation_failed", "synthetic option failure")
            original(session_id, name, value)

        self.client.set_option = fail_after_guard  # type: ignore[method-assign]
        with self.assertRaisesRegex(ContractError, "synthetic option failure"):
            self.lifecycle.create(
                self.host.host_id,
                None,
                "will-rollback",
                "/tmp",
                [("@fail", "x")],
                [],
                False,
                None,
                False,
            )
        with self.assertRaises(NoServer):
            self.client.session_ids()

    def test_early_holder_disappearance_returns_stable_operation_failure(self) -> None:
        """A holder that disappears before server identity is read has a stable error."""
        original_path = os.environ.get("PATH", "")
        with tempfile.TemporaryDirectory() as directory:
            fake_tmux = Path(directory) / "tmux"
            fake_tmux.write_text(
                "#!/bin/sh\n"
                "new_session=0\n"
                "socket=\n"
                "previous=\n"
                'for value in "$@"; do\n'
                '  [ "$value" = "new-session" ] && new_session=1\n'
                '  [ "$previous" = "-L" ] && socket="$value"\n'
                '  previous="$value"\n'
                "done\n"
                'if [ "$new_session" = 1 ]; then\n'
                '  output=$(/usr/bin/tmux "$@") || exit $?\n'
                '  printf "%s\\n" "$output"\n'
                '  session_id=$(printf "%s\\n" "$output" | awk \'{print $1}\')\n'
                '  while /usr/bin/tmux -L "$socket" -f /dev/null has-session -t "$session_id" 2>/dev/null; do\n'
                "    sleep 0.01\n"
                "  done\n"
                "  exit 0\n"
                "fi\n"
                'for value in "$@"; do\n'
                '  [ "$value" = "@rofi_tmux_plus_operation" ] && exit 1\n'
                "done\n"
                'exec /usr/bin/tmux "$@"\n',
                encoding="utf-8",
            )
            fake_tmux.chmod(0o755)
            os.environ["PATH"] = f"{directory}:{original_path}"
            try:
                with self.assertRaises(ContractError) as raised:
                    self.lifecycle.create(
                        self.host.host_id,
                        None,
                        "token-install-failure",
                        "/tmp",
                        [],
                        [],
                        False,
                        None,
                        False,
                    )
                self.assertEqual(raised.exception.code, "operation_failed")
                self.assertEqual(
                    raised.exception.message,
                    "holding wrapper did not install its operation token",
                )
            finally:
                os.environ["PATH"] = original_path
        with self.assertRaises(NoServer):
            self.client.session_ids()

    def test_token_or_reference_mismatch_is_never_killed_by_rollback(self) -> None:
        original = self.client.set_option

        def replace_token_then_fail(session_id: str, name: str, value: str) -> None:
            if name == "@fail":
                original(session_id, "@rofi_tmux_plus_operation", "someone-else")
                raise ContractError("operation_failed", "synthetic option failure")
            original(session_id, name, value)

        self.client.set_option = replace_token_then_fail  # type: ignore[method-assign]
        with self.assertRaisesRegex(ContractError, "synthetic option failure"):
            self.lifecycle.create(
                self.host.host_id,
                None,
                "must-survive",
                "/tmp",
                [("@fail", "x")],
                [],
                False,
                None,
                False,
            )
        generation = self.client.server_generation()
        sessions = [self.client.descriptor(self.host.host_id, generation, "$0")]
        self.assertIsNotNone(generation)
        self.assertEqual([session.name for session in sessions], ["must-survive"])

    def test_bookkeeping_cleanup_failure_after_release_keeps_success(self) -> None:
        def fail_unset(_session_id: str, _name: str) -> None:
            raise ContractError("operation_failed", "synthetic cleanup failure")

        self.client.unset_option = fail_unset  # type: ignore[method-assign]
        made = self.lifecycle.create(
            self.host.host_id, None, "released", "/tmp", [], [], False, None, False
        )
        self.assertTrue(made["ok"])
        self.assertIn(made["session"]["sessionId"], self.client.session_ids())

    def test_deferred_session_times_out_and_removes_its_own_pending_session(self) -> None:
        made = self.lifecycle.create(
            self.host.host_id,
            None,
            "deferred",
            "/tmp",
            [],
            ["/bin/sh", "-c", "sleep 30"],
            True,
            1,
            False,
        )
        self.assertTrue(made["session"]["pending"])
        time.sleep(2.1)
        with self.assertRaises(NoServer):
            self.client.session_ids()
