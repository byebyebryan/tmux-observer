"""Independent structured action proof against isolated native tmux servers."""

import copy
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tmux_observer_actions._progress import mark
from tmux_observer_actions.errors import ContractError
from tmux_observer_actions.host import local_host
from tmux_observer_actions.public import ActionClient, ActionConfig
from tmux_observer_actions.tmux import TmuxClient


def request(operation, host, reference=None, name=None, parameters=None, options=None):
    return {
        "protocol": "tmux-observer.action.v1",
        "schemaVersion": 1,
        "requestId": "owned-request",
        "operation": operation,
        "hostId": host,
        "meshRevision": None,
        "sessionRef": reference,
        "guards": {"expectedName": name, "requiredOptions": options or {}},
        "parameters": parameters or {},
    }


class StructuredNativeActions(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory(prefix="tmux-observer-action-sdk-")
        self.environment = patch.dict(
            os.environ,
            {
                "TMUX_TMPDIR": self.root.name,
                "XDG_RUNTIME_DIR": self.root.name,
                "SHELL": "/bin/sh",
            },
        )
        self.environment.start()
        self.host = local_host().host_id
        self.mesh = Mock()
        self.mesh.load.return_value = None
        self.native = TmuxClient()
        self.client = ActionClient(ActionConfig(terminal=("true",)), mesh_adapter=self.mesh)
        # Keep fixture default/alternate servers alive; bypass ordinary config.
        for socket in ("default", "alternate"):
            subprocess.run(
                [
                    "tmux",
                    "-L",
                    socket,
                    "-f",
                    "/dev/null",
                    "new-session",
                    "-d",
                    "-s",
                    "owned-anchor",
                    "sleep",
                    "60",
                ],
                check=True,
                capture_output=True,
            )

    def tearDown(self):
        # Both names are inside this test's owned TMUX_TMPDIR, not user sockets.
        for socket in ("default", "alternate"):
            subprocess.run(["tmux", "-L", socket, "kill-server"], check=False, capture_output=True)
        end = time.monotonic() + 2

        def server_alive():
            return any(
                subprocess.run(
                    ["tmux", "-L", socket, "list-sessions"], check=False, capture_output=True
                ).returncode
                == 0
                for socket in ("default", "alternate")
            )

        while server_alive() and time.monotonic() < end:
            time.sleep(0.01)
        self.assertFalse(server_alive())
        self.environment.stop()
        self.root.cleanup()

    def create(self, name="owned-created", *, open_after=False):
        return self.client.execute(
            request(
                "create",
                self.host,
                parameters={
                    "name": name,
                    "cwd": "/tmp",
                    "options": {"@owned": "value"},
                    "command": ["sleep", "30"],
                    "deferUntilAttached": False,
                    "attachTimeout": None,
                    "open": open_after,
                },
            )
        )

    def test_default_scope_ignores_ambient_alternate_and_sdk_needs_no_service(self):
        alternate = TmuxClient(("tmux", "-L", "alternate"))
        generation = alternate.server_generation()
        path = generation.split(":", 3)[-1]
        with patch.dict(os.environ, {"TMUX": f"{path},1,0", "TMUX_PANE": "%0"}):
            created = self.create()
        self.assertTrue(created["ok"], created)
        self.assertEqual(created["outcome"]["nativeEffect"], "confirmed")
        self.assertEqual(created["outcome"]["terminalSpawn"], "not_requested")
        self.assertEqual(created["outcome"]["transport"], "local")
        self.assertFalse(created["automaticRetry"])
        self.assertIn("/default", created["sessionRef"]["serverGeneration"])
        self.assertEqual(alternate.session_ids(), ["$0"])
        self.assertFalse((Path(self.root.name) / "tmux-observer").exists())

    def test_rename_kill_guards_and_full_reference_are_independent_of_prepared_roster(self):
        created = self.create()
        reference = created["sessionRef"]
        rename = request(
            "rename",
            self.host,
            reference,
            "owned-created",
            {"name": "owned-renamed"},
            {"@owned": "wrong"},
        )
        refused = self.client.execute(rename)
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["outcome"]["nativeEffect"], "none")
        self.assertEqual(refused["error"]["code"], "stale_session")
        rename["guards"]["requiredOptions"]["@owned"] = "value"
        with (
            patch.object(
                TmuxClient,
                "session_ids",
                side_effect=AssertionError("prepared roster is unavailable"),
            ),
            patch.object(TmuxClient, "has_name", return_value=False),
        ):
            changed = self.client.execute(rename)
        self.assertTrue(changed["ok"], changed)
        self.assertEqual(changed["sessionRef"], reference)
        kill = request("kill", self.host, reference, "owned-created")
        self.assertFalse(self.client.execute(kill)["ok"])
        kill["guards"]["expectedName"] = "owned-renamed"
        killed = self.client.execute(kill)
        self.assertTrue(killed["ok"], killed)
        self.assertEqual(killed["outcome"]["nativeEffect"], "confirmed")
        self.assertEqual(killed["sessionRef"], reference)
        self.assertEqual(self.native.session_ids(), ["$0"])

    def test_committed_create_survives_terminal_failure_and_reports_effect(self):
        def failed_terminal(*_args, **_kwargs):
            mark("terminalSpawn", "failed")
            raise OSError("owned synthetic missing terminal")

        with patch(
            "tmux_observer_actions.lifecycle.spawn_terminal_command", side_effect=failed_terminal
        ):
            result = self.create(open_after=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["outcome"]["nativeEffect"], "confirmed")
        self.assertEqual(result["outcome"]["terminalSpawn"], "failed")
        self.assertIsNone(result["legacyResult"])
        self.assertIsNotNone(result["sessionRef"])
        self.assertIn(result["sessionRef"]["sessionId"], self.native.session_ids())
        self.assertFalse(result["automaticRetry"])

    def test_reused_id_and_invalid_request_cannot_authorize_action(self):
        created = self.create()
        original = created["sessionRef"]
        changed = copy.deepcopy(original)
        changed["createdAt"] += 1
        result = self.client.execute(request("kill", self.host, changed, "owned-created"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["outcome"]["nativeEffect"], "none")
        invalid = request("kill", self.host, original, None)
        with patch.object(self.client, "_dispatch") as dispatch, self.assertRaises(ValueError):
            self.client.execute(invalid)
        dispatch.assert_not_called()

    def test_invalid_source_alias_is_rejected_before_create(self):
        with patch.object(TmuxClient, "create_detached") as write:
            result = self.client.execute(
                request(
                    "create",
                    "wrong-host",
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
        self.assertFalse(result["ok"])
        self.assertEqual(result["outcome"]["nativeEffect"], "none")
        write.assert_not_called()


class ActionOutcomeTests(unittest.TestCase):
    def test_configuration_rejects_controls_and_boolean_timeout(self):
        for options in ({"terminal": ("bad\x00",)}, {"attach_timeout_seconds": True}):
            with self.assertRaises(ContractError):
                ActionConfig(**options)
