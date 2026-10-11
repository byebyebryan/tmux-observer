#!/usr/bin/env python3
"""Owned filesystem checks for coordinated rollback; no desktop or native actions."""

import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import stat
import subprocess
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    "operations", str(Path(__file__).resolve().parents[1] / "scripts/tmux-observer-operations")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
operations = importlib.util.module_from_spec(spec)
loader.exec_module(operations)


class CoordinatedRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tmux-rollback-test-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.patch = patch.object(operations, "HOME", self.home)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.selection = {}
        for kind in ("core", "frontend"):
            root = self.home / kind
            root.mkdir()
            raw = ("old-" + kind).encode()
            (root / "module.py").write_bytes(raw)
            (root / "module.py").chmod(0o755)
            self.selection[kind] = {
                "prefix": kind,
                "files": {
                    "module.py": {
                        "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "executable": True,
                    }
                },
            }
        raw = b'{"source":"old"}\n'
        (self.home / "frontend/release-manifest.json").write_bytes(raw)
        self.selection["frontend"]["manifestSha256"] = hashlib.sha256(raw).hexdigest()
        (self.home / "core/__pycache__").mkdir()
        (self.home / "core/__pycache__/generated.pyc").write_bytes(b"generated")
        self.captured = {
            "payloads": operations.capture_payloads(self.selection, self.home / "before.json")
        }
        for kind in ("core", "frontend"):
            (self.home / kind / "module.py").write_text("selected-" + kind)
        (self.home / "unrelated").write_text("ordinary")

    def test_context_fleet_discovery_rejects_missing_or_ambiguous_contexts(self):
        import subprocess

        for text, expected in (
            ("", None),
            (
                "tmux-observer-fleet@one.service loaded active running owned\n",
                "tmux-observer-fleet@one.service",
            ),
            (
                "tmux-observer-fleet@one.service loaded active running owned\ntmux-observer-fleet@two.service loaded active running owned\n",
                None,
            ),
        ):
            with (
                self.subTest(text=text),
                patch.object(
                    operations,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, text, ""),
                ),
            ):
                if expected is None:
                    with self.assertRaisesRegex(RuntimeError, "exactly one"):
                        operations.active_fleet_unit()
                else:
                    self.assertEqual(operations.active_fleet_unit(), expected)

    def assert_selected_survives(self):
        for kind in ("core", "frontend"):
            self.assertEqual((self.home / kind / "module.py").read_text(), "selected-" + kind)
        self.assertEqual((self.home / "unrelated").read_text(), "ordinary")

    def corrupt_archive(self, names):
        saved = self.captured["payloads"]["core"]
        archive = Path(saved["archive"])
        saved["files"] = {}
        with warnings.catch_warnings(), zipfile.ZipFile(archive, "w") as zipped:
            warnings.simplefilter("ignore", UserWarning)
            for name, mode in names:
                raw = b"owned"
                info = zipfile.ZipInfo(name)
                info.external_attr = mode << 16
                zipped.writestr(info, raw)
                saved["files"][name] = {
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
        saved["archiveSha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()

    def test_both_packages_restore_with_modes_and_without_generated_caches(self):
        finalized = []
        with operations.staged_payloads(self.captured, self.selection) as staged:

            def finalize():
                for kind in ("core", "frontend"):
                    self.assertEqual((self.home / kind / "module.py").read_text(), "old-" + kind)
                finalized.append(True)

            operations.replace_payloads(staged, finalize)
        self.assertEqual(finalized, [True])
        self.assertFalse((self.home / "core/__pycache__").exists())
        self.assertEqual(stat.S_IMODE((self.home / "core/module.py").stat().st_mode), 0o755)
        self.assertEqual(list(self.home.glob(".tmux-rollback-*")), [])
        self.assertEqual((self.home / "unrelated").read_text(), "ordinary")

    def test_finalize_failure_restores_the_complete_selected_tuple(self):
        with (
            operations.staged_payloads(self.captured, self.selection) as staged,
            self.assertRaisesRegex(RuntimeError, "owned failure"),
        ):
            operations.replace_payloads(
                staged, lambda: (_ for _ in ()).throw(RuntimeError("owned failure"))
            )
        self.assert_selected_survives()
        self.assertEqual(list(self.home.glob(".tmux-rollback-*")), [])

    def test_second_package_rename_failure_restores_first_selected_package(self):
        original = Path.rename
        with operations.staged_payloads(self.captured, self.selection) as staged:
            failed = staged[1][1]

            def rename(path, target):
                if path == failed:
                    raise OSError("owned second-rename failure")
                return original(path, target)

            with patch.object(Path, "rename", rename), self.assertRaises(OSError):
                operations.replace_payloads(staged, lambda: self.fail("must not finalize"))
        self.assert_selected_survives()

    def test_partial_control_restore_failure_puts_selected_controls_back(self):
        for name in ("control-a", "control-b"):
            (self.home / name).write_text("selected")
        selected = {name: operations.node(self.home / name) for name in ("control-a", "control-b")}
        before = {name: {**value, "data": "b2xk"} for name, value in selected.items()}
        original = operations.write_control

        def write(relative, value):
            if relative == "control-b" and value == before[relative]:
                raise OSError("owned write failure")
            return original(relative, value)

        with (
            patch.object(operations, "write_control", write),
            self.assertRaises(OSError),
        ):
            operations.restore_controls(before, selected)
        self.assertEqual({name: operations.node(self.home / name) for name in selected}, selected)

    def test_hostile_archive_members_and_coverage_are_rejected_before_replacement(self):
        for names in (
            [("../escape", stat.S_IFREG | 0o644)],
            [("/absolute", stat.S_IFREG | 0o644)],
            [("link", stat.S_IFLNK | 0o777)],
            [("setuid", stat.S_IFREG | 0o4644)],
            [("duplicate", stat.S_IFREG | 0o644)] * 2,
        ):
            self.corrupt_archive(names)
            with (
                self.subTest(names=names),
                self.assertRaises(RuntimeError),
                operations.staged_payloads(self.captured, self.selection),
            ):
                self.fail("unsafe staging accepted")
            self.assert_selected_survives()
        self.assertFalse((self.home.parent / "escape").exists())

    def test_legacy_frontend_only_capture_is_rejected(self):
        with (
            self.assertRaisesRegex(RuntimeError, "both Observer and frontend"),
            operations.staged_payloads({"frontendArchive": "old.zip"}, self.selection),
        ):
            self.fail("incomplete baseline accepted")
        self.assert_selected_survives()

    def test_corrupt_archive_rejected_before_service_stop_in_cli(self):
        captured = {
            **self.captured,
            "host": "snap",
            "operation": "capture",
            "controls": {},
        }
        before = self.home / "before.json"
        before.write_text(json.dumps(captured))
        Path(captured["payloads"]["core"]["archive"]).write_bytes(b"changed")
        selection = self.home / "selection.json"
        selection.write_text(json.dumps(self.selection))
        with (
            patch.object(operations, "TUPLE", selection),
            patch.object(operations, "native_references", return_value=[]),
            patch.object(operations, "installed", return_value={}),
            patch.object(operations, "run") as run,
            patch(
                "sys.argv",
                [
                    "operations",
                    "rollback",
                    "--host",
                    "snap",
                    "--before",
                    str(before),
                    "--output",
                    str(self.home / "result.json"),
                    "--source",
                    str(self.home),
                    "--selection",
                    str(selection),
                    "--frontend-verifier",
                    str(self.home / "frontend-verifier"),
                ],
            ),
        ):
            run.return_value.stdout = ""
            with self.assertRaisesRegex(RuntimeError, "archive drift"):
                operations.main()
            self.assertEqual(
                [call.args[0] for call in run.call_args_list], [["pgrep", "-x", "rofi"]]
            )
        self.assert_selected_survives()

    def test_headless_rollback_rejects_desktop_baseline_before_stop(self):
        captured = {**self.captured, "host": "snap", "operation": "capture", "scope": "desktop"}
        before = self.home / "before.json"
        before.write_text(json.dumps(captured))
        selection = self.home / "selection.json"
        selection.write_text(json.dumps(self.selection))
        with (
            patch.object(operations, "native_references", return_value=[]),
            patch.object(operations, "installed", return_value={}),
            patch.object(operations, "run") as runner,
            patch(
                "sys.argv",
                [
                    "operations",
                    "rollback",
                    "--host",
                    "snap",
                    "--scope",
                    "owner",
                    "--before",
                    str(before),
                    "--output",
                    str(self.home / "result.json"),
                    "--source",
                    str(self.home),
                    "--selection",
                    str(selection),
                    "--frontend-verifier",
                    str(self.home / "verifier"),
                ],
            ),
        ):
            runner.return_value.stdout = ""
            with self.assertRaisesRegex(RuntimeError, "baseline scope differs"):
                operations.main()
            self.assertEqual(
                [call.args[0] for call in runner.call_args_list], [["pgrep", "-x", "rofi"]]
            )
        self.assert_selected_survives()

    def test_headless_paired_rollback_stops_only_owner(self):
        captured = {
            **self.captured,
            "host": "snap",
            "operation": "capture",
            "scope": "owner",
            "controls": {},
        }
        before = self.home / "before.json"
        before.write_text(json.dumps(captured))
        selection = self.home / "selection.json"
        selection.write_text(json.dumps(self.selection))
        with (
            patch.object(operations, "native_references", return_value=[]),
            patch.object(
                operations,
                "native_identity",
                return_value={"serverGeneration": "generation", "references": []},
            ),
            patch.object(operations, "installed", return_value={}),
            patch.object(operations, "control_paths", return_value=[]),
            patch.object(
                operations, "active_fleet_unit", side_effect=AssertionError("fleet discovery")
            ),
            patch.object(operations, "verify_frontend"),
            patch.object(operations, "run") as runner,
            patch("builtins.print"),
            patch(
                "sys.argv",
                [
                    "operations",
                    "rollback",
                    "--host",
                    "snap",
                    "--scope",
                    "owner",
                    "--before",
                    str(before),
                    "--output",
                    str(self.home / "result.json"),
                    "--source",
                    str(self.home),
                    "--selection",
                    str(selection),
                    "--frontend-verifier",
                    str(self.home / "verifier"),
                ],
            ),
        ):
            runner.return_value.stdout = ""
            operations.main()
            stops = [call.args[0] for call in runner.call_args_list if "stop" in call.args[0]]
            self.assertEqual(
                stops, [["systemctl", "--user", "stop", "tmux-observer-owner@snap.service"]]
            )
        self.assertEqual((self.home / "core/module.py").read_text(), "old-core")
        self.assertEqual((self.home / "frontend/module.py").read_text(), "old-frontend")


class PreparedReadinessTests(unittest.TestCase):
    def setUp(self):
        self.reference = {
            "hostId": "snap",
            "serverGeneration": "generation",
            "sessionId": "$1",
            "createdAt": 1,
        }
        source = {"hostId": "snap", "uid": 1000}
        clock = {"bootId": "boot", "clock": "boottime"}
        self.frame = {
            "clock": clock,
            "snapshot": {
                "mesh": {"state": "ready"},
                "desktop": {"state": "ready", "expiresAt": 20},
                "hosts": [
                    {
                        "hostId": "snap",
                        "local": True,
                        "owner": {
                            "source": source,
                            "publisherId": "publisher",
                            "serverGeneration": "generation",
                            "receipt": {"state": "ready"},
                            "localExpiry": 20,
                        },
                        "sessions": [self.reference],
                    }
                ],
            },
        }
        self.profile = {
            "source": source,
            "clock": clock,
            "publisherId": "publisher",
            "receipt": {"state": "ready", "expiresAt": 20},
            "snapshot": {
                "serverGeneration": "generation",
                "sessions": [self.reference],
            },
        }

    def ready(self, frame=None, profile=None):
        return operations.prepared_ready(
            self.frame if frame is None else frame,
            "snap",
            10,
            profile=self.profile if profile is None else profile,
            local_attachments=True,
        )

    def test_healthy_owner_cannot_replace_current_desktop(self):
        self.assertTrue(self.ready())
        for state in ("warming", "failed", "unsupported", "expired"):
            frame = copy.deepcopy(self.frame)
            frame["snapshot"]["desktop"]["state"] = state
            with self.subTest(state=state):
                self.assertFalse(self.ready(frame))
        frame = copy.deepcopy(self.frame)
        frame["snapshot"]["desktop"]["expiresAt"] = 10
        self.assertFalse(self.ready(frame))

    def test_required_profile_must_be_present_current_and_same_scope(self):
        self.assertFalse(self.ready(profile={}))
        for key, value in (
            ("publisherId", "other"),
            ("clock", {"bootId": "other", "clock": "boottime"}),
            ("source", {"hostId": "snap", "uid": 2000}),
            ("receipt", {"state": "ready", "expiresAt": 10}),
            ("receipt", {"state": "failed", "expiresAt": 20}),
            ("snapshot", {"serverGeneration": "other", "sessions": [self.reference]}),
            ("snapshot", {"serverGeneration": "generation", "sessions": []}),
        ):
            profile = copy.deepcopy(self.profile)
            profile[key] = value
            with self.subTest(key=key, value=value):
                self.assertFalse(self.ready(profile=profile))
        frame = copy.deepcopy(self.frame)
        frame["snapshot"]["hosts"][0]["owner"]["localExpiry"] = 10
        self.assertFalse(self.ready(frame))

    def test_old_selection_does_not_require_the_new_profile(self):
        self.assertTrue(operations.prepared_ready(self.frame, "snap", 10))
        self.assertFalse(operations.prepared_ready(self.frame, "snap", 10, local_attachments=True))

    def test_required_local_bindings_have_their_own_context_and_lease(self):
        self.frame["contextId"] = "context"
        host = self.frame["snapshot"]["hosts"][0]
        host["localBindings"] = {
            "contextId": "context",
            "clock": self.frame["clock"],
            "publisherId": "publisher",
            "receipt": {"state": "ready", "expiresAt": 15},
        }

        def ready(frame):
            return operations.prepared_ready(
                frame,
                "snap",
                10,
                profile=self.profile,
                local_attachments=True,
                local_bindings=True,
            )

        self.assertTrue(ready(self.frame))
        for mutate in (
            lambda batch: batch.update(contextId="changed"),
            lambda batch: batch.update(clock={"bootId": "changed"}),
            lambda batch: batch.update(publisherId="changed"),
            lambda batch: batch["receipt"].update(expiresAt=10),
            lambda batch: batch["receipt"].update(state="expired"),
        ):
            frame = copy.deepcopy(self.frame)
            mutate(frame["snapshot"]["hosts"][0]["localBindings"])
            self.assertFalse(ready(frame))
        self.frame["snapshot"]["desktop"]["state"] = "warming"
        self.assertFalse(ready(self.frame))
        self.frame["snapshot"]["mesh"]["state"] = "local_only"
        self.assertTrue(ready(self.frame))
        del self.frame["snapshot"]["hosts"][0]["localBindings"]
        self.assertFalse(ready(self.frame))


if __name__ == "__main__":
    unittest.main()


class HeadlessOperationsTests(unittest.TestCase):
    def setUp(self):
        self.reference = {
            "hostId": "snap",
            "serverGeneration": "generation",
            "sessionId": "$1",
            "createdAt": 1,
        }
        self.frame = {
            "source": {"hostId": "snap", "uid": 1000},
            "clock": {"bootId": "boot", "timeNamespace": "time:1"},
            "publisherId": "publisher",
            "receipt": {"state": "ready"},
            "snapshot": {"serverGeneration": "generation", "sessions": [self.reference]},
        }

    def test_scope_requires_its_explicit_service_topology(self):
        for scope, desktop, fleets, accepted in (
            ("owner", "inactive", "", True),
            ("owner", "active", "", False),
            ("owner", "failed", "", False),
            ("owner", "inactive", "tmux-observer-fleet@one.service active\n", False),
            ("desktop", "inactive", "", False),
            ("desktop", "active", "tmux-observer-fleet@one.service active\n", True),
        ):

            def run(argv, desktop_state=desktop, fleet_output=fleets, **_kwargs):
                return subprocess.CompletedProcess(
                    argv, 0, desktop_state if "is-active" in argv else fleet_output, ""
                )

            with (
                self.subTest(scope=scope, desktop=desktop, fleets=fleets),
                patch.object(operations, "run", run),
            ):
                if accepted:
                    operations.check_service_scope(scope)
                else:
                    with self.assertRaises(RuntimeError):
                        operations.check_service_scope(scope)

    def test_required_attachment_profile_keeps_full_owner_binding(self):
        profile = {**copy.deepcopy(self.frame), "receipt": {"state": "ready", "expiresAt": 20}}
        self.assertTrue(operations.owner_profile_ready(self.frame, profile, 10))
        for key, value in (
            ("publisherId", "other"),
            ("source", {"hostId": "snap", "uid": 2000}),
            ("clock", {"bootId": "other", "timeNamespace": "time:1"}),
            ("receipt", {"state": "failed", "expiresAt": 20}),
            ("receipt", {"state": "ready", "expiresAt": 10}),
            ("snapshot", {"serverGeneration": "other", "sessions": [self.reference]}),
            ("snapshot", {"serverGeneration": "generation", "sessions": []}),
        ):
            altered = {**profile, key: value}
            with self.subTest(key=key, value=value):
                self.assertFalse(operations.owner_profile_ready(self.frame, altered, 10))

    def exercise(self, operation, *, changed_generation=False, unchanged_publisher=False):
        with tempfile.TemporaryDirectory(prefix="tmux-headless-ops-") as temporary:
            root = Path(temporary)
            selection = root / "selection.json"
            selection.write_text('{"requirements":{"localAttachments":true}}\n')
            identity = {
                "serverGeneration": "generation",
                "references": [("snap", "generation", "$1", 1)],
            }
            after_identity = (
                {**identity, "serverGeneration": "other"} if changed_generation else identity
            )
            recovered = {
                **self.frame,
                "publisherId": "publisher" if unchanged_publisher else "restarted",
            }
            frames = [self.frame, recovered] if operation == "recover" else [self.frame]

            def run(argv, **_kwargs):
                if argv[-2:] == ["inventory", "--json"]:
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        '{"schemaVersion":1,"hosts":[{"hostId":"snap","status":"ok","sessions":[]}]}',
                        "",
                    )
                if argv == ["systemctl", "--user", "restart", "tmux-observer-owner@snap.service"]:
                    return subprocess.CompletedProcess(argv, 0, "", "")
                raise AssertionError("unexpected headless command: " + str(argv))

            with (
                patch.object(operations, "HOME", root),
                patch.object(operations, "installed", return_value={}) as installed,
                patch.object(operations, "native_references", return_value=[]),
                patch.object(operations, "native_identity", side_effect=[identity, after_identity]),
                patch.object(operations, "owner_scope_ready", side_effect=frames),
                patch.object(
                    operations, "fleet_ready", side_effect=AssertionError("fleet readiness")
                ),
                patch.object(operations, "environment", return_value={}),
                patch.object(operations, "run", side_effect=run) as runner,
                patch("builtins.print"),
                patch(
                    "sys.argv",
                    [
                        "operations",
                        operation,
                        "--host",
                        "snap",
                        "--scope",
                        "owner",
                        "--source",
                        str(root),
                        "--selection",
                        str(selection),
                        "--frontend-verifier",
                        str(root / "verifier"),
                        "--output",
                        str(root / "result.json"),
                    ],
                ),
            ):
                operations.main()
                installed.assert_called_once_with(
                    {"requirements": {"localAttachments": True}}, "snap", scope="owner"
                )
                result = json.loads((root / "result.json").read_text())
                self.assertEqual(result["scope"], "owner")
                self.assertNotIn("preparedFrameBytes", result)
                return result, [call.args[0] for call in runner.call_args_list]

    def test_verify_and_recovery_do_not_require_or_start_a_desktop(self):
        verified, commands = self.exercise("verify")
        self.assertEqual(len(commands), 1)
        self.assertTrue(verified["nativeGenerationPreserved"])
        recovered, commands = self.exercise("recover")
        self.assertEqual(
            commands[0], ["systemctl", "--user", "restart", "tmux-observer-owner@snap.service"]
        )
        self.assertEqual(recovered["after"]["publisherId"], "restarted")
        self.assertTrue(recovered["completeReferencesSurvive"])

    def test_recovery_rejects_unchanged_publisher_and_native_generation_drift(self):
        with self.assertRaisesRegex(RuntimeError, "owner incarnation"):
            self.exercise("recover", unchanged_publisher=True)
        with self.assertRaisesRegex(RuntimeError, "native server generation"):
            self.exercise("verify", changed_generation=True)


class FrontendBoundaryTests(unittest.TestCase):
    def test_explicit_frontend_missing_rejected(self):
        with (
            patch.object(operations, "FRONTEND_VERIFIER", Path("/nonexistent/frontend-verifier")),
            self.assertRaises(RuntimeError),
        ):
            operations.verify_frontend(Path("/nonexistent/prefix"))

    def test_delegate_public_prefix_and_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            verifier = Path(temporary) / "verifier"
            verifier.write_text("# owned fixture\n")
            with (
                patch.object(operations, "FRONTEND_VERIFIER", verifier),
                patch.object(operations, "run") as runner,
            ):
                runner.return_value.stdout = '{"status":"accepted"}'
                operations.verify_frontend(Path(temporary) / "prefix")
                self.assertEqual(
                    runner.call_args.args[0][-3:],
                    [str(verifier), "--prefix", str(Path(temporary) / "prefix")],
                )
                runner.return_value.stdout = '{"status":"failed"}'
                with self.assertRaises(RuntimeError):
                    operations.verify_frontend(Path(temporary) / "prefix")
