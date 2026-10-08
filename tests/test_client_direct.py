"""Independent Mesh fixtures and fresh composition/transport policy cases."""

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tmux_observer.public import encode_document, validate_observation
from tmux_observer_client._command import BoundedCompleted
from tmux_observer_client._errors import ContractError
from tmux_observer_client.direct import DirectInventory, failed_row
from tmux_observer_client.mesh import HostMeshAdapter, _parse_snapshot

ROOT = Path(__file__).resolve().parent.parent


def legacy_validator():
    directory = ROOT / "tests/fixtures/legacy-tmux-session-v1"
    sums = (directory / "SHA256SUMS").read_bytes()
    manifest = json.loads((ROOT / "docs/extraction-manifest.json").read_text())
    assert hashlib.sha256(sums).hexdigest() == manifest["contractBundles"]["tmux-session-v1"]
    expected = {
        name: digest
        for digest, name in (line.split("  ", 1) for line in sums.decode().splitlines())
    }
    schemas = []
    for path in sorted((directory / "schemas").glob("*.json")):
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == expected[str(path.relative_to(directory))]
        )
        schemas.append(json.loads(path.read_text()))
    registry = Registry().with_resources(
        (value["$id"], Resource.from_contents(value)) for value in schemas
    )
    value = next(value for value in schemas if value["$id"] == "inventory.schema.json")
    return Draft202012Validator(value, registry=registry)


class MeshTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "tests/fixtures/legacy-mesh.json").read_text())

    def load(self, payload, code=0):
        return HostMeshAdapter(
            which=lambda _name: "/owned/provider",
            runner=lambda *_a, **_kw: subprocess.CompletedProcess(
                [], code, encode_document(payload), b""
            ),
        )

    def test_missing_only_fallback_and_ambiguous_or_broken_authority_fails(self):
        self.assertIsNone(HostMeshAdapter(which=lambda _name: None).load())
        for change in ("version", "collision", "local_order", "route_index", "nonzero"):
            with self.subTest(change=change):
                value = self.fixture()
                if change == "version":
                    value["schemaVersion"] = 2
                elif change == "collision":
                    value["hosts"][2]["aliases"].append(
                        value["hosts"][1]["routes"][0]["destination"]
                    )
                elif change == "local_order":
                    value["hosts"].reverse()
                elif change == "route_index":
                    value["hosts"][1]["routes"][0]["configuredIndex"] = 8
                with self.assertRaises(ContractError):
                    self.load(value, 1 if change == "nonzero" else 0).load()

    def test_direct_mesh_keeps_128_capacity_and_casefold_alias_policy(self):
        value = self.fixture()
        row = value["hosts"][1]
        value["hosts"] = [value["hosts"][0]] + [
            {
                **row,
                "id": f"h{i}",
                "aliases": [],
                "routes": [
                    {
                        "destination": f"r{i}",
                        "configuredIndex": 0,
                        "lastReachableAt": None,
                        "lastUnreachableAt": None,
                    }
                ],
            }
            for i in range(127)
        ]
        value["future"] = {"diagnostic": True}
        self.assertEqual(len(self.load(value).load().hosts), 128)
        mesh = self.load(self.fixture()).load()
        self.assertEqual(mesh.resolve_host("BETA-NATIVE").host_id, "beta")
        self.assertEqual(mesh.local_host.host_id, "alpha")


class FakeMesh:
    def __init__(self):
        self.snapshot = _parse_snapshot(
            json.loads((ROOT / "tests/fixtures/legacy-mesh.json").read_text())
        )
        self.reports = []

    def load(self, **_kwargs):
        return self.snapshot

    def report_route(self, **kwargs):
        self.reports.append(kwargs)
        return True


class Local:
    def collect(self, **_profile):
        value = json.loads((ROOT / "contracts/observation-v1/fixtures/complete.json").read_text())
        value["source"]["hostId"] = "alpha"
        for row in value["sessions"]:
            row["hostId"] = "alpha"
        return value


class DirectTests(unittest.TestCase):
    def test_legacy_empty_option_failure_preserves_core_empty_versus_absent_values(self):
        class EmptyOptions(Local):
            def collect(self, **kwargs):
                value = super().collect(**kwargs)
                value["capabilities"]["options"] = ["@empty", "@missing"]
                value["sessions"][0]["options"] = {"@empty": "", "@missing": None}
                validate_observation(value)
                self.value = value
                return value

        local = EmptyOptions()
        direct = DirectInventory(mesh=FakeMesh(), local=local)
        with self.assertRaises(ContractError) as failure:
            direct.inventory(requested_hosts=["alpha"], option_names=["@empty", "@missing"])
        self.assertEqual(failure.exception.code, "operation_failed")
        self.assertEqual(local.value["sessions"][0]["options"], {"@empty": "", "@missing": None})

    def test_complete_and_failed_rows_conform_to_pinned_legacy_inventory_schema(self):
        mesh = FakeMesh()
        value = DirectInventory(mesh=mesh, local=Local(), runner=self.runner([])).inventory(
            requested_hosts=["alpha", "beta"]
        )
        validator = legacy_validator()
        validator.validate(value)
        self.assertIsNone(value["hosts"][0]["route"])
        self.assertEqual(value["hosts"][1]["route"], mesh.snapshot.hosts[1].routes[0].destination)
        for host in mesh.snapshot.hosts:
            for code in ("operation_failed", "host_unreachable"):
                with self.subTest(host=host.host_id, code=code):
                    response = {**value, "hosts": [failed_row(host, code, "owned failure")]}
                    validator.validate(response)
                    self.assertIsNone(response["hosts"][0]["route"])

    def runner(self, calls, *, kind="complete"):
        def run(argv, **_bounds):
            calls.append(argv)
            nonce = re.search(r"REACHED_V1:%s\\037\\n' ([a-f0-9]{32})", argv[-1])[1]
            host_id = re.search(r"--host-id ([A-Za-z0-9_.-]+)", argv[-1])[1]
            value = Local().collect()
            value["source"]["hostId"] = host_id
            for row in value["sessions"]:
                row["hostId"] = host_id
            stderr = "\x1eTMUX_OBSERVER_REACHED_V1:" + nonce + "\x1f\n"
            raw = encode_document(value) if kind == "complete" else b'{"broken":true}\n'
            if kind == "auth":
                stderr = "Permission denied (publickey)"
            return BoundedCompleted(
                0 if kind == "complete" else 255,
                raw.decode(),
                stderr,
                stdout_bytes=raw,
                stderr_bytes=stderr.encode(),
            )

        return run

    def test_fresh_projection_order_scope_options_and_selected_owner_only(self):
        mesh, calls = FakeMesh(), []
        direct = DirectInventory(mesh=mesh, local=Local(), runner=self.runner(calls))
        value = direct.inventory(requested_hosts=["BETA-NATIVE", "alpha", "beta"])
        self.assertEqual([row["hostId"] for row in value["hosts"]], ["alpha", "beta"])
        self.assertTrue(all(row["status"] == "ok" for row in value["hosts"]))
        self.assertEqual(len(calls), 1)
        self.assertIn("-T", calls[0])
        self.assertIn("ControlPath=none", calls[0])
        self.assertIn("StrictHostKeyChecking=yes", calls[0])
        self.assertIn("collect --host-id beta", calls[0][-1])
        self.assertNotIn("bridge", calls[0][-1])
        self.assertEqual(mesh.reports[0]["status"], "reachable")
        self.assertEqual(mesh.reports[0]["mesh_revision"], mesh.snapshot.revision)
        with self.assertRaises(ContractError):
            direct.inventory(mesh_revision="sha256:" + "b" * 64)

    def test_reached_malformed_stops_route_retry_and_auth_is_not_unreachable(self):
        for kind in ("broken", "auth"):
            with self.subTest(kind=kind):
                mesh, calls = FakeMesh(), []
                direct = DirectInventory(
                    mesh=mesh, local=Local(), runner=self.runner(calls, kind=kind)
                )
                value = direct.inventory(requested_hosts=["beta"])
                self.assertEqual(value["hosts"][0]["status"], "error")
                if kind == "broken":
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(mesh.reports[0]["status"], "reachable")
                else:
                    self.assertFalse(mesh.reports)

    def test_provider_failure_cannot_turn_into_local_only_inventory(self):
        mesh = FakeMesh()

        def broken(**_kwargs):
            raise ContractError("invalid_config", "fixture")

        mesh.load = broken
        with self.assertRaises(ContractError):
            DirectInventory(mesh=mesh, local=Local()).inventory()
