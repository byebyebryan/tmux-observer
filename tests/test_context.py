"""Private captured environments and explicit, fixed unit operations."""

import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tmux_observer._ipc import IPCError
from tmux_observer_client._context import context_file, prepare_context, render, stop_context
from tmux_observer_client.public import desktop_context_id


class ContextTests(unittest.TestCase):
    def test_allowlist_private_capture_and_conflicting_owner_are_not_silently_rebound(self):
        with (
            tempfile.TemporaryDirectory(prefix="tmux-context-") as temporary,
            patch.dict(
                os.environ,
                {
                    "XDG_RUNTIME_DIR": temporary,
                    "NIRI_SOCKET": "/run/example compositor.sock",
                    "DISPLAY": ':1 "quote" \\backslash $dollar `backtick`',
                    "SECRET_TOKEN": "not captured",
                    "TMUX": "ambient native socket",
                },
            ),
        ):
            value = prepare_context("snap")
            path = Path(value["environmentFile"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            raw = path.read_text()
            self.assertNotIn("SECRET_TOKEN", raw)
            self.assertNotIn("ambient native socket", raw)
            self.assertIn('DISPLAY=":1 \\"quote\\" \\\\backslash $dollar `backtick`"', raw)
            self.assertEqual(prepare_context("snap"), value)
            with self.assertRaises(IPCError) as error:
                prepare_context("starship")
            self.assertEqual(error.exception.code, "context_conflict")
            self.assertEqual(path.read_text(), raw)

    def test_headless_capture_and_different_desktops_have_independent_files(self):
        with (
            tempfile.TemporaryDirectory(prefix="tmux-context-") as temporary,
            patch.dict(
                os.environ,
                {
                    "XDG_RUNTIME_DIR": temporary,
                    "NIRI_SOCKET": "",
                    "DISPLAY": "",
                    "WAYLAND_DISPLAY": "",
                },
            ),
        ):
            headless = prepare_context("snap")
            with patch.dict(os.environ, {"NIRI_SOCKET": "/run/desktop-a.sock"}):
                desktop = prepare_context("snap")
            self.assertNotEqual(headless["contextId"], desktop["contextId"])
            self.assertTrue(Path(headless["environmentFile"]).exists())
            self.assertTrue(Path(desktop["environmentFile"]).exists())
            self.assertIn('NIRI_SOCKET=""', Path(headless["environmentFile"]).read_text())

    def test_unsafe_files_registry_and_environment_injection_are_rejected(self):
        with (
            tempfile.TemporaryDirectory(prefix="tmux-context-") as temporary,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": temporary}),
        ):
            context = desktop_context_id()
            path = context_file(context)
            path.parent.mkdir(mode=0o700)
            target = Path(temporary) / "other"
            target.write_text("preserve me")
            path.symlink_to(target)
            with self.assertRaises(IPCError):
                prepare_context("snap")
            self.assertEqual(target.read_text(), "preserve me")
            path.unlink()
            os.mkfifo(path, mode=0o600)
            with self.assertRaises(IPCError):
                prepare_context("snap")
            path.unlink()
            path.write_text("unsafe")
            path.chmod(0o644)
            with self.assertRaises(IPCError):
                prepare_context("snap")
            path.unlink()
            with (
                patch.dict(os.environ, {"DISPLAY": ':1\nTMUX_OBSERVER_HOST_ID="foreign"'}),
                self.assertRaises(IPCError),
            ):
                prepare_context("snap")
            lease = path.parent / ".contexts.lock"
            with lease.open("r+") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(IPCError) as error:
                    prepare_context("snap")
                self.assertEqual(error.exception.code, "context_busy")

    def test_explicit_start_stop_and_failed_stop_preserve_other_contexts(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return SimpleNamespace(returncode=0, timed_out=False, overflow_streams=set())

        with (
            tempfile.TemporaryDirectory(prefix="tmux-context-") as temporary,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": temporary}),
        ):
            first = prepare_context("snap", start=True, runner=runner)
            with patch.dict(os.environ, {"NIRI_SOCKET": "/different-context"}):
                second = prepare_context("snap")
            first_path = Path(first["environmentFile"])
            self.assertEqual([item[0][2] for item in calls], ["reset-failed", "start"])
            self.assertTrue(all(item[0][3] == first["unit"] for item in calls))

            def failed(_argv, **_kwargs):
                return SimpleNamespace(returncode=1, timed_out=False, overflow_streams=set())

            with self.assertRaises(IPCError):
                stop_context(first["contextId"], runner=failed)
            self.assertTrue(first_path.exists())
            stop_context(first["contextId"], runner=runner)
            self.assertFalse(first_path.exists())
            self.assertTrue(Path(second["environmentFile"]).exists())
            self.assertEqual(calls[-1][0], ["systemctl", "--user", "stop", first["unit"]])

    def test_capacity_and_rendered_runtime_scope_are_explicit(self):
        with (
            tempfile.TemporaryDirectory(prefix="tmux-context-") as temporary,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": temporary}),
        ):
            for index in range(16):
                with patch.dict(os.environ, {"NIRI_SOCKET": f"/context-{index}"}):
                    prepare_context("snap")
            with self.assertRaises(IPCError) as error:
                prepare_context("snap")
            self.assertEqual(error.exception.code, "capacity")
            _context, raw = render("snap", {"XDG_RUNTIME_DIR": "/run/a separate runtime"})
            self.assertIn(b'XDG_RUNTIME_DIR="/run/a separate runtime"', raw)

    def test_new_unloaded_instance_can_start_but_start_failure_is_not_success(self):
        calls = []

        def runner(argv, **_kwargs):
            calls.append(argv[2])
            return SimpleNamespace(
                returncode=1 if argv[2] == "reset-failed" else 0,
                timed_out=False,
                overflow_streams=set(),
            )

        with (
            tempfile.TemporaryDirectory(prefix="tmux-context-") as temporary,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": temporary}),
        ):
            value = prepare_context("snap", start=True, runner=runner)
            self.assertEqual(value["state"], "start_requested")
            self.assertEqual(calls, ["reset-failed", "start"])

            def failed(_argv, **_kwargs):
                return SimpleNamespace(returncode=1, timed_out=False, overflow_streams=set())

            with self.assertRaises(IPCError):
                prepare_context("snap", start=True, runner=failed)
            self.assertTrue(Path(value["environmentFile"]).exists())
