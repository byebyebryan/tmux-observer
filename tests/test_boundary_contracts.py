"""Independent corpus, authority/freshness conflicts and import boundaries."""

import copy
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tmux_observer.attachments import (
    validate_attachment_delivery,
    validate_attachment_error,
    validate_attachment_request,
    validate_attachments,
)
from tmux_observer_actions.contract import validate_action_request, validate_action_result
from tmux_observer_client.desktop_contract import legacy_viewer, validate_desktop

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "boundary_reader", str(ROOT / "scripts/read-boundary-contract")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
reader = importlib.util.module_from_spec(spec)
loader.exec_module(reader)
VALIDATORS = {
    "attachments": validate_attachments,
    "attachment-error": validate_attachment_error,
    "attachment-request": validate_attachment_request,
    "attachment-delivery": validate_attachment_delivery,
    "desktop": validate_desktop,
    "action-request": validate_action_request,
    "action-result": validate_action_result,
}


def fixture(bundle, name):
    return json.loads((ROOT / "contracts" / bundle / "fixtures" / (name + ".json")).read_text())


class BoundaryContracts(unittest.TestCase):
    def accept(self, kind, value):
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
        reader.base.wire(raw, 1048576 + 16384)
        self.assertIs(VALIDATORS[kind](value), value)
        reader.verify(kind, value)

    def reject(self, kind, value):
        with self.assertRaises(ValueError):
            VALIDATORS[kind](value)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            reader.verify(kind, value)

    def test_independent_valid_and_invalid_corpus(self):
        for bundle in ("attachments-v1", "desktop-v1", "action-v1"):
            for case in fixture(bundle, "index")["cases"]:
                with self.subTest(bundle=bundle, case=case["file"]):
                    method = self.accept if case["accept"] else self.reject
                    method(case["kind"], fixture(bundle, case["file"].removesuffix(".json")))

    def test_native_identity_namespace_and_process_bounds(self):
        base = fixture("attachments-v1", "complete")
        for path, replacement in (
            (("schemaVersion",), True),
            (("pidNamespace",), "global"),
            (("clients", 0, "clientPid"), 0),
            (("clients", 0, "processStartTicks"), True),
            (("clients", 0, "sessionRef", "createdAt"), 1),
            (("clients", 0, "sessionRef", "serverGeneration"), "replacement"),
        ):
            value = copy.deepcopy(base)
            child = value
            for key in path[:-1]:
                child = child[key]
            child[path[-1]] = replacement
            with self.subTest(path=path):
                self.reject("attachments", value)
        for value in (base, fixture("desktop-v1", "native-confirmed")):
            kind = "attachments" if "clients" in value else "desktop"
            self.reject(kind, {**value, "viewerId": "not-a-passive-handle"})
        value = copy.deepcopy(base)
        value["source"]["closeSafe"] = True
        self.reject("attachments", value)

    def test_receipt_cannot_be_renewed_by_encoding(self):
        base = fixture("attachments-v1", "delivery-ready")
        for mutate in (
            lambda v: v.update(encodedAt=v["receipt"]["expiresAt"]),
            lambda v: v["snapshot"]["sample"].update(startedAt=101),
            lambda v: v["receipt"].update(remainingMs=10000),
            lambda v: v["snapshot"]["clock"].update(timeNamespace="time:11"),
            lambda v: v["source"].update(hostId="other"),
        ):
            value = copy.deepcopy(base)
            mutate(value)
            self.reject("attachment-delivery", value)
        value = copy.deepcopy(base)
        value["receipt"].update(
            state="failed",
            remainingMs=0,
            attempted=2,
            lastAttemptAt=130,
            lastAttemptResult="failed",
        )
        value["error"] = {"code": "association_failed", "message": "current associations unknown"}
        self.accept("attachment-delivery", value)

    def test_desktop_owner_and_association_leases_are_independent(self):
        base = fixture("desktop-v1", "native-confirmed")
        for mutate in (
            lambda v: v["dependencies"][0].update(ownerExpiresAt=130),
            lambda v: v["dependencies"][0].update(associationExpiresAt=None),
            lambda v: v["dependencies"][0].update(local=False),
            lambda v: v["rows"][0].update(attachedClients=0),
            lambda v: v["receipt"].update(expiresAt=130),
            lambda v: v["receipt"].update(expiresAt=10101),
            lambda v: v["rows"][0]["sessionRef"].update(serverGeneration="changed"),
        ):
            value = copy.deepcopy(base)
            mutate(value)
            self.reject("desktop", value)
        value = copy.deepcopy(base)
        value["rows"][0]["presence"].update(state="none", confidence=None, evidence="absence")
        value["dependencies"][0]["associationExpiresAt"] = None
        self.reject("desktop", value)
        value["dependencies"][0]["associationExpiresAt"] = 10100
        self.accept("desktop", value)

    def test_launch_projection_is_an_explicit_legacy_choice(self):
        presence = fixture("desktop-v1", "remote-launch-matched")["rows"][0]["presence"]
        self.assertEqual(legacy_viewer(presence)["confidence"], "matched")
        self.assertEqual(
            legacy_viewer(presence, legacy_launch_confirmation=True)["confidence"], "confirmed"
        )

    def test_create_needs_no_reference_and_mutation_keeps_guards(self):
        value = fixture("action-v1", "request-create")
        self.accept("action-request", value)
        value["sessionRef"] = fixture("action-v1", "request-open")["sessionRef"]
        self.reject("action-request", value)
        for operation in ("rename", "kill"):
            value = fixture("action-v1", "request-" + operation)
            value["guards"]["expectedName"] = None
            self.reject("action-request", value)
        value = fixture("action-v1", "request-open")
        value["parameters"]["tmuxExecutable"] = "/tmp/arbitrary"
        self.reject("action-request", value)

    def test_action_result_binding_uncertainty_and_compatibility(self):
        request = fixture("action-v1", "request-open")
        result = fixture("action-v1", "spawn-unverified")
        validate_action_result(result, request=request)
        for key, replacement in (
            ("requestId", "different"),
            ("operation", "viewers"),
            ("hostId", "other"),
        ):
            bad = {**request, key: replacement}
            with self.assertRaises(ValueError):
                validate_action_result(result, request=bad)
        for mutate in (
            lambda v: v["outcome"].update(transport="uncertain"),
            lambda v: v["outcome"].update(terminalSpawn="uncertain"),
            lambda v: v["legacyResult"]["session"].update(createdAt=1),
            lambda v: v["legacyResult"].update(schemaVersion=True),
            lambda v: v["legacyResult"].update(terminalLaunched=False),
            lambda v: v["legacyResult"].update(focused=True),
        ):
            value = copy.deepcopy(result)
            mutate(value)
            self.reject("action-result", value)
        value = fixture("action-v1", "create-uncertain")
        self.accept("action-result", value)
        self.assertFalse(value["automaticRetry"])

    def test_domain_imports_with_implementations_unavailable(self):
        cases = (
            (
                ("tmux_observer_client", "tmux_observer_actions"),
                "import tmux_observer.native, tmux_observer.public, tmux_observer.delivery, tmux_observer.attachments, tmux_observer.owner",
            ),
            (
                (
                    "tmux_observer.collector",
                    "tmux_observer.owner",
                    "tmux_observer_actions",
                    "tmux_observer_client.desktop",
                    "tmux_observer_client.ssh",
                    "tmux_observer_client.fleet",
                ),
                "import tmux_observer_client.contract, tmux_observer_client.desktop_contract, tmux_observer_client.public",
            ),
            (
                (
                    "rofi_tmux_plus",
                    "tmux_observer.collector",
                    "tmux_observer.owner",
                    "tmux_observer_client.desktop",
                    "tmux_observer_client.ssh",
                ),
                "import tmux_observer_actions.contract",
            ),
        )
        for blocked, statement in cases:
            code = f"""import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if any(fullname == p or fullname.startswith(p + '.') for p in {blocked!r}):
            raise ImportError('blocked implementation ' + fullname)
sys.meta_path.insert(0, Block())
{statement}
"""
            with self.subTest(blocked=blocked):
                result = subprocess.run(
                    [sys.executable, "-c", code], capture_output=True, text=True, check=False
                )
                self.assertEqual(result.returncode, 0, result.stderr)
