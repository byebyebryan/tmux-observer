"""Exact generation/reference client joins and passive adapter admission."""

import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tmux_observer._clock import boottime_ms
from tmux_observer.public import Session, SessionReference
from tmux_observer_client import _desktop_scan
from tmux_observer_client._desktop_scan import ViewerTarget
from tmux_observer_client._errors import ContractError
from tmux_observer_client.desktop import LocalClients, scan


class DesktopTests(unittest.TestCase):
    def target(self):
        row = Session(
            SessionReference("fixture", "generation", "$0", 123),
            "owned",
            None,
            None,
            1,
            False,
            1,
            "/tmp",
            "main",
            "/tmp",
        )
        return ViewerTarget(row, True, "fixture")

    def collector(self, rows, generations=("generation", "generation")):
        values = iter(generations)
        return SimpleNamespace(
            generation=lambda *_args: next(values),
            read=lambda *_args: "fixture",
            rows=lambda *_args: rows,
        )

    def test_local_client_join_checks_generation_created_at_and_duplicate_pid(self):
        target = self.target()
        valid = LocalClients(
            [target], boottime_ms() + 2000, collector=self.collector([("1234", "$0", "123")])
        )
        self.assertEqual(valid.client_pids_by_session(), {"$0": {1234}})
        for rows, generations in (
            ([("1234", "$0", "124")], ("generation", "generation")),
            ([("1234", "$0", "123")], ("generation", "restarted")),
            ([("1234", "$0", "123"), ("1234", "$0", "123")], ("generation", "generation")),
            ([("1234", "$0", "123")], ("foreign", "foreign")),
        ):
            with self.subTest(rows=rows, generations=generations), self.assertRaises(ContractError):
                LocalClients(
                    [target], boottime_ms() + 2000, collector=self.collector(rows, generations)
                ).client_pids_by_session()

    def test_empty_input_still_requires_independent_compositor_read(self):
        with (
            patch.dict(os.environ, NIRI_SOCKET="/owned/fixture"),
            patch("tmux_observer_client.desktop._niri_windows", return_value=None) as read,
        ):
            state, values, error = scan([], deadline=boottime_ms() + 2000)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(state, "failed")
        self.assertFalse(values)
        self.assertEqual(error["code"], "compositor_unavailable")

    def test_passive_module_has_no_action_implementations_or_handles(self):
        for name in (
            "Viewer",
            "ViewerInspection",
            "focus_window",
            "close_viewer",
            "launch_metadata",
            "effective_destroy_unattached",
            "LocalLifecycle",
            "TmuxClient",
        ):
            self.assertFalse(hasattr(_desktop_scan, name), name)
        script = "import sys; import tmux_observer_client.public; print(','.join(sys.modules))"
        modules = subprocess.check_output([sys.executable, "-I", "-c", script], text=True)
        for name in (
            "tmux_observer.collector",
            "tmux_observer.owner",
            "tmux_observer_client.ssh",
            "tmux_observer_client.desktop",
            "tmux_observer_client.direct",
        ):
            self.assertNotIn(name, modules)

    def test_metadata_float_duplicate_and_deep_json_are_not_valid_markers(self):
        for payload in (
            b'{"schemaVersion":1.0}',
            b'{"schemaVersion":1,"schemaVersion":1}',
            b'{"schemaVersion":1,"nested":' + b"[" * 50 + b"0" + b"]" * 50 + b"}",
        ):
            raw = b"ROFI_TMUX_PLUS_VIEWER_V1=" + payload + b"\0"
            with (
                patch("tmux_observer_client._desktop_scan.os.open", return_value=55),
                patch("tmux_observer_client._desktop_scan.os.read", return_value=raw),
                patch("tmux_observer_client._desktop_scan.os.close"),
            ):
                value, present, readable = _desktop_scan._read_metadata_detailed(123)
            self.assertIsNone(value)
            self.assertTrue(present and readable)
