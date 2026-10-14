"""Owner-certified static rules, independent of optional Fleet adoption."""

import copy
import json
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from mesh_plus.api import PreparationState, PreparedReadGuard, ReadGuard
from mesh_plus.protocol import ProtocolError

from tmux_observer import __version__
from tmux_observer.mesh_preparation import make_preparation
from tmux_observer.mesh_profile import TmuxMeshProfile

ROOT = Path(__file__).resolve().parents[1]


class PreparationTests(unittest.TestCase):
    def guard(self, response):
        return PreparedReadGuard(
            "tmux",
            response["mesh"]["requestId"],
            profile=TmuxMeshProfile(),
            preparation=make_preparation(),
            host_ids=response["mesh"]["scope"]["hostIds"],
        )

    def response(self, name):
        response = json.loads((ROOT / "tests/fixtures/mesh-sdk-v1" / name).read_text())
        response["mesh"]["operation"] = "watch"
        response["mesh"]["reader"].update(sequence=1, revision=1)
        return response

    def test_all_frozen_fixtures_full_rows_raw_export_and_expiry_equal_legacy(self):
        for path in sorted((ROOT / "tests/fixtures/mesh-sdk-v1").glob("*.json")):
            response = self.response(path.name)
            legacy = ReadGuard("tmux", response["mesh"]["requestId"], profile=TmuxMeshProfile())
            guard = self.guard(response)
            with self.subTest(fixture=path.name):
                legacy.accept(response)
                guard.accept(response)
                reader = response["mesh"]["reader"]
                times = {reader["encodedAtMs"], reader["encodedAtMs"] + 1000, 2**52}
                times.update(
                    r["expiresAtMs"]
                    for h in response["mesh"]["hosts"]
                    for r in h["receipts"]
                    if r["expiresAtMs"] is not None
                )
                for now in sorted(times):
                    self.assertEqual(
                        guard.current(now, reader["clock"]), legacy.current(now, reader["clock"])
                    )
                self.assertEqual(guard.snapshot(), response)
                original = copy.deepcopy(response)
                guard.snapshot()["sessions"].clear()
                response["sessions"].clear()
                self.assertEqual(guard.snapshot(), original)
                guard.disconnect()
                self.assertIsNone(guard.snapshot())

    def test_rule_policy_matches_supported_profile_for_every_receipt_health(self):
        from mesh_plus.api import NativeState

        response = self.response("tmux-local.json")
        row = response["sessions"][0]
        profile = TmuxMeshProfile()
        preparation = make_preparation()
        for health in (
            "current",
            "partial",
            "stale",
            "unknown",
            "warming",
            "unavailable",
            "unsupported",
        ):
            for receipts in (
                [],
                [{"sourceId": "default", "component": "native", "health": health}],
                [{"sourceId": "foreign", "component": "native", "health": health}],
            ):
                state = PreparationState(
                    MappingProxyType({}),
                    (MappingProxyType(row),),
                    MappingProxyType({}),
                    "owner",
                    0,
                    tuple(MappingProxyType(r) for r in receipts),
                )
                native = NativeState({}, [row], {}, "owner", 0, receipts)
                rules = preparation.prepare_rules(state)
                self.assertEqual(len(rules), 1)
                self.assertEqual(rules[0].identity, profile.record_identity(row))
                self.assertEqual(rules[0].required, profile.record_receipts(row, native))
                self.assertIs(rules[0].eligible, profile.record_eligible(row, native))

    def test_rules_are_static_with_no_clock_environment_or_process_reads(self):
        from mesh_plus.api import PreparationState

        preparation = make_preparation()
        row = self.response("tmux-local.json")["sessions"][0]
        state = PreparationState(
            MappingProxyType({}),
            (MappingProxyType(row),),
            MappingProxyType({}),
            "owner",
            0,
            (
                MappingProxyType(
                    {"sourceId": "default", "component": "native", "health": "current"}
                ),
            ),
        )
        expected = preparation.prepare_rules(state)
        with (
            patch("time.time", side_effect=AssertionError("clock")),
            patch("os.getenv", side_effect=AssertionError("environment")),
            patch("subprocess.Popen", side_effect=AssertionError("process")),
            patch("tmux_observer._clock.boottime_ms", side_effect=AssertionError("clock")),
        ):
            self.assertEqual(preparation.prepare_rules(state), expected)
            self.assertEqual(preparation.prepare_rules(state), expected)

    def test_implementation_binding_and_version_change_retires_guard(self):
        response = self.response("tmux-local.json")
        preparation = make_preparation()
        self.assertIn(__version__, preparation.descriptor.implementation_id)
        self.assertEqual(preparation.descriptor.interface_version, 1)
        guard = PreparedReadGuard(
            "tmux",
            response["mesh"]["requestId"],
            profile=TmuxMeshProfile(),
            preparation=preparation,
        )
        guard.accept(response)
        preparation.descriptor = replace(preparation.descriptor, implementation_id="changed-owner")
        with self.assertRaisesRegex(ProtocolError, "preparation_binding"):
            guard.current(
                response["mesh"]["reader"]["encodedAtMs"], response["mesh"]["reader"]["clock"]
            )
        self.assertIsNone(guard._generation)

    def test_module_import_does_not_require_mesh_or_native_or_desktop(self):
        script = """import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'mesh_plus','subprocess','tmux_observer_client','tmux_observer_actions'}:
   raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
import tmux_observer.mesh_preparation
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fleet_worker_retains_legacy_guard_by_default(self):
        from mesh_plus.api import ReadGuard

        from tmux_observer_client import _mesh_worker

        self.assertIs(_mesh_worker.ReadGuard, ReadGuard)
