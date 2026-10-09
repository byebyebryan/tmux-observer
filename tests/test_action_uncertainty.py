"""Lost acknowledgements never redispatch writes to another route."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_action_remote import _action_output
from tests.test_action_sdk import request
from tmux_observer_actions._progress import Progress, current
from tmux_observer_actions.errors import ContractError
from tmux_observer_actions.public import ActionClient, ActionConfig
from tmux_observer_actions.remote_lifecycle import RemoteLifecycle
from tmux_observer_actions.tmux import TmuxClient
from tmux_observer_client.mesh import MeshHost, MeshPolicy, MeshRoute, MeshSnapshot, MeshStaleError


class WriteUncertaintyTests(unittest.TestCase):
    def test_complete_write_ack_survives_later_route_report_failure(self):
        nonce = "0" * 32
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, _action_output("KILL"), "\x1eROFI_PLUS_REACHED_V1:" + nonce + "\x1f\n"
            )
        )
        adapter = Mock()
        adapter.report_route.side_effect = MeshStaleError()
        host = MeshHost(
            "remote",
            "Remote",
            False,
            (),
            (MeshRoute("first", 0, None, None), MeshRoute("second", 1, None, None)),
        )
        remote = RemoteLifecycle(
            adapter, ActionConfig(), runner=runner, nonce_factory=lambda: nonce
        )
        progress = Progress("kill")
        token = current.set(progress)
        try:
            with self.assertRaises(MeshStaleError):
                remote.kill(
                    host,
                    MeshPolicy("ssh", 1, 1, 60),
                    "sha256:" + "b" * 64,
                    "tmux-v1:10:20:/tmp/tmux",
                    "$0",
                    11,
                    "before",
                )
        finally:
            current.reset(token)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(progress.outcome["nativeEffect"], "confirmed")
        self.assertEqual(progress.outcome["transport"], "confirmed")
        self.assertEqual(progress.reference["sessionId"], "$0")

    def test_response_target_mismatch_precedes_terminal_launch(self):
        nonce = "0" * 32
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, _action_output("OPEN"), "\x1eROFI_PLUS_REACHED_V1:" + nonce + "\x1f\n"
            )
        )
        spawned = Mock()
        host = MeshHost("remote", "Remote", False, (), (MeshRoute("first", 0, None, None),))
        remote = RemoteLifecycle(
            Mock(),
            ActionConfig(),
            runner=runner,
            nonce_factory=lambda: nonce,
            terminal_spawner=spawned,
        )
        with self.assertRaises(ContractError):
            remote.open(
                host,
                MeshPolicy("ssh", 1, 1, 60),
                "sha256:" + "b" * 64,
                "tmux-v1:10:20:/tmp/tmux",
                "$1",
                11,
                None,
            )
        spawned.assert_not_called()

    def test_real_owned_transport_loses_ack_and_is_dispatched_once(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-lost-ack-") as directory:
            root = Path(directory)
            executable, counter = root / "ssh", root / "counter"
            executable.write_text(
                '#!/bin/sh\nprintf x >> "$(dirname "$0")/counter"\n'
                'printf "Connection timed out\\n" >&2\nexit 255\n'
            )
            executable.chmod(0o700)
            adapter = Mock()
            revision = "sha256:" + "a" * 64
            local = MeshHost("local", "Local", True, (), ())
            remote = MeshHost(
                "remote",
                "Remote",
                False,
                (),
                (
                    MeshRoute("first", 0, None, None),
                    MeshRoute("second", 1, None, None),
                ),
            )
            adapter.load.return_value = MeshSnapshot(
                revision, "local", MeshPolicy(str(executable), 1, 1, 60), (local, remote)
            )
            action = ActionClient(ActionConfig(), mesh_adapter=adapter)
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": directory}):
                result = action.execute(
                    request(
                        "create",
                        "remote",
                        parameters={
                            "name": "owned",
                            "cwd": "/tmp",
                            "options": {},
                            "command": [],
                            "deferUntilAttached": False,
                            "attachTimeout": None,
                            "open": False,
                        },
                    )
                )
            self.assertEqual(counter.read_bytes(), b"x")
            self.assertFalse(result["ok"])
            self.assertEqual(result["outcome"]["nativeEffect"], "uncertain")
            self.assertEqual(result["outcome"]["transport"], "uncertain")
            self.assertEqual(result["error"]["code"], "action_uncertain")
            self.assertFalse(result["automaticRetry"])
            adapter.report_route.assert_not_called()

    def test_error_after_dispatch_preserves_uncertainty_without_second_route(self):
        host = MeshHost(
            "remote",
            "Remote",
            False,
            (),
            (MeshRoute("first", 0, None, None), MeshRoute("second", 1, None, None)),
        )
        runner = Mock(side_effect=OSError("owned capture failure"))
        remote = RemoteLifecycle(Mock(), ActionConfig(), runner=runner)
        progress = Progress("rename")
        token = current.set(progress)
        try:
            with self.assertRaises(ContractError):
                remote._action(
                    host, MeshPolicy("ssh", 1, 1, 60), "sha256:" + "b" * 64, "rename", []
                )
        finally:
            current.reset(token)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(progress.outcome["nativeEffect"], "uncertain")
        self.assertEqual(progress.outcome["transport"], "uncertain")

    def test_native_capture_error_after_dispatch_does_not_claim_no_effect(self):
        progress = Progress("kill")
        token = current.set(progress)
        try:
            with (
                patch(
                    "tmux_observer_actions.tmux.run_bounded",
                    side_effect=OSError("owned pipe failure"),
                ),
                self.assertRaises(ContractError),
            ):
                TmuxClient().kill("$0")
        finally:
            current.reset(token)
        self.assertEqual(progress.outcome["nativeEffect"], "uncertain")

    def test_native_spawn_failure_has_no_effect(self):
        progress = Progress("kill")
        token = current.set(progress)
        try:
            with self.assertRaises(ContractError):
                TmuxClient(("/does-not-exist-owned-tmux",)).kill("$0")
        finally:
            current.reset(token)
        self.assertEqual(progress.outcome["nativeEffect"], "none")

    def test_marked_malformed_ack_is_uncertain_and_never_retried(self):
        nonce = "0" * 32
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, "malformed\n", "\x1eROFI_PLUS_REACHED_V1:" + nonce + "\x1f\n"
            )
        )
        adapter = Mock()
        host = MeshHost(
            "remote",
            "Remote",
            False,
            (),
            (MeshRoute("first", 0, None, None), MeshRoute("second", 1, None, None)),
        )
        remote = RemoteLifecycle(
            adapter, ActionConfig(), runner=runner, nonce_factory=lambda: nonce
        )
        progress = Progress("create")
        token = current.set(progress)
        try:
            with self.assertRaises(ContractError):
                remote._action(
                    host, MeshPolicy("ssh", 1, 1, 60), "sha256:" + "b" * 64, "create", []
                )
        finally:
            current.reset(token)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(progress.outcome["nativeEffect"], "uncertain")
        self.assertEqual(progress.outcome["transport"], "uncertain")
