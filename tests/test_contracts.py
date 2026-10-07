"""Synthetic acceptance cases shared with an independently implemented reader."""

import copy
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tmux_observer import public

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader(
    "acceptance_reader", str(ROOT / "scripts/read-contract")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
reader = importlib.util.module_from_spec(spec)
loader.exec_module(reader)
VALIDATORS = {
    "observation": public.validate_observation,
    "service": public.validate_service_frame,
    "fleet": public.validate_fleet_view,
    "fleet-frame": public.validate_fleet_frame,
    "request": public.validate_request,
    "operation-error": public.validate_operation_error,
}


def fixture(bundle, name):
    return json.loads((ROOT / "contracts" / bundle / "fixtures" / (name + ".json")).read_text())


def bytes_of(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"


def change(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


class ContractTests(unittest.TestCase):
    def accept(self, kind, value):
        raw = bytes_of(value)
        limit = public.FRAME_LIMIT if kind in ("service", "fleet-frame") else public.DOCUMENT_LIMIT
        self.assertEqual(public.decode_document(raw, limit=limit), reader.wire(raw, limit))
        self.assertIs(VALIDATORS[kind](value), value)
        reader.verify(kind, value)

    def reject(self, kind, value):
        with self.assertRaises(ValueError):
            VALIDATORS[kind](value)
        with self.assertRaises(ValueError):
            reader.verify(kind, value)

    def test_hand_assembled_fixtures(self):
        for bundle, default in (
            ("observation-v1", "observation"),
            ("service-v1", "service"),
            ("fleet-v1", "fleet"),
        ):
            index = fixture(bundle, "index")
            for case in index["cases"]:
                kind = {"request.schema.json": "request", "frame.schema.json": "fleet-frame"}.get(
                    case.get("schema"), default
                )
                with self.subTest(bundle=bundle, case=case):
                    self.accept(kind, fixture(bundle, case["file"].removesuffix(".json")))

    def test_unknown_extensions_and_opaque_generation(self):
        value = fixture("observation-v1", "complete")
        value["future"] = {"bounded": [1, True, None, "safe"]}
        value["serverGeneration"] = " --opaque generation / with spaces "
        value["sessions"][0]["serverGeneration"] = value["serverGeneration"]
        self.accept("observation", value)

        frame = fixture("service-v1", "ready")
        frame["snapshot"]["capabilities"]["futureDiagnostic"] = "bounded"
        self.accept("service", frame)

    def test_identity_and_coverage_conflicts(self):
        base = fixture("observation-v1", "complete")
        cases = [
            (("schemaVersion",), True),
            (("schemaVersion",), 1.0),
            (("source", "server"), "alternate"),
            (("sessions", 0, "hostId"), "other"),
            (("sessions", 0, "serverGeneration"), "other"),
            (("sessions", 0, "createdAt"), True),
            (("sessions", 0, "sessionId"), "name"),
            (("sessions", 0, "attachedClients"), -1),
            (("sessions", 0, "pending"), 1),
            (("sessions", 0, "viewerId"), "action-handle"),
            (("sample", "finishedAt"), 99),
            (("sample", "coverage"), "failed"),
            (("sample", "error"), {"code": "failed", "message": "failure"}),
            (("serverGeneration",), None),
        ]
        for path, replacement in cases:
            value = copy.deepcopy(base)
            change(value, path, replacement)
            with self.subTest(path=path):
                self.reject("observation", value)
        value = copy.deepcopy(base)
        value["sessions"].append(copy.deepcopy(value["sessions"][0]))
        self.reject("observation", value)

    def test_explicit_capability_coverage(self):
        value = fixture("observation-v1", "complete")
        value["capabilities"] = {"panes": True, "options": ["@empty", "@absent"]}
        row = value["sessions"][0]
        row["options"] = {"@empty": "", "@absent": None}
        row["panes"] = [{"paneId": "%1", "pid": None, "currentPath": None, "currentCommand": None}]
        self.accept("observation", value)
        for mutation in (
            lambda v: v["sessions"][0]["options"].pop("@absent"),
            lambda v: v["capabilities"].update(panes=False),
            lambda v: v["sessions"][0]["panes"].append(v["sessions"][0]["panes"][0]),
        ):
            invalid = copy.deepcopy(value)
            mutation(invalid)
            self.reject("observation", invalid)

    def test_ready_sample_and_receipt_binding(self):
        base = fixture("service-v1", "ready")
        cases = [
            (("receipt", "acceptedAttempt"), 2),
            (("receipt", "accepted"), 0),
            (("receipt", "expiresAt"), 10125),
            (("receipt", "remainingMs"), 10000),
            (("receipt", "lastAttemptResult"), "failed"),
            (("receipt", "lastAttemptResult"), "none"),
            (("receipt", "lastAttemptAt"), 101),
            (("snapshot", "sample", "startedAt"), 101),
            (("snapshot", "sample", "finishedAt"), 126),
            (("snapshot", "clock", "timeNamespace"), "time:11"),
            (("snapshot", "source", "uid"), 1001),
            (("snapshot",), None),
        ]
        for path, replacement in cases:
            value = copy.deepcopy(base)
            change(value, path, replacement)
            with self.subTest(path=path):
                self.reject("service", value)

    def test_failed_source_retains_history_without_validity(self):
        value = fixture("service-v1", "ready")
        value["receipt"].update(
            state="failed",
            remainingMs=0,
            attempted=2,
            lastAttemptAt=150,
            lastAttemptResult="failed",
        )
        self.accept("service", value)
        value["receipt"]["remainingMs"] = 100
        self.reject("service", value)

    def test_warming_is_not_complete_empty(self):
        value = fixture("service-v1", "warming")
        value["snapshot"] = fixture("observation-v1", "no-server")
        self.reject("service", value)
        value["snapshot"] = None
        value["receipt"].update(attempted=1, lastAttemptAt=100, inFlight=True)
        self.accept("service", value)
        value["receipt"]["inFlight"] = False
        self.reject("service", value)

    def test_ticket_mixed_success_and_incarnation(self):
        value = fixture("service-v1", "ready")
        ticket = {
            "id": "22222222-2222-4222-8222-222222222222",
            "publisherId": value["publisherId"],
            "state": "complete",
            "requestedAt": 130,
            "deadlineAt": 15000,
            "sources": [
                {
                    "hostId": "fixture-local",
                    "source": "owner",
                    "state": "complete",
                    "attempt": 2,
                    "error": None,
                }
            ],
        }
        value.update(kind="refresh_result", ticket=ticket)
        self.accept("service", value)
        ticket["sources"].append(
            {
                "hostId": "fixture-remote",
                "source": "owner",
                "state": "failed",
                "attempt": 2,
                "error": {"code": "failed", "message": "read failed"},
            }
        )
        self.reject("service", value)
        ticket["state"] = "failed"
        self.accept("service", value)
        ticket["publisherId"] = ticket["id"]
        self.reject("service", value)

    def test_requests_are_fixed_scope_and_known_fields_typed(self):
        base = fixture("service-v1", "request")
        for additions in (
            {"contextId": False},
            {"sources": [{"hostId": "other", "source": "owner"}]},
            {"publisherId": "bad"},
            {"meshRevision": "bad"},
            {"ticketId": "22222222-2222-4222-8222-222222222222"},
        ):
            with self.subTest(additions=additions):
                self.reject("request", {**base, **additions})
        self.accept(
            "request",
            {
                **base,
                "operation": "refresh",
                "sources": [{"hostId": "fixture-local", "source": "owner"}],
            },
        )

    def test_viewer_membership_requires_independent_current_sources(self):
        base = fixture("fleet-v1", "local")
        value = copy.deepcopy(base)
        value["hosts"][0]["sessions"][0]["localViewer"] = {"state": "none", "reason": None}
        self.reject("fleet", value)
        value["desktop"].update(
            state="ready",
            startedAt=100,
            acceptedAt=125,
            expiresAt=10100,
            inputHash="sha256:" + "a" * 64,
            error=None,
        )
        self.accept("fleet", value)
        value["hosts"][0]["sessions"][0]["localViewer"] = {
            "state": "open",
            "reason": None,
            "confidence": "matched",
        }
        self.reject("fleet", value)
        value["hosts"][0]["sessions"][0]["attachedClients"] = 1
        self.accept("fleet", value)
        for path, replacement in (
            (("contextId",), "1" * 32),
            (("desktop", "expiresAt"), 130),
            (("hosts", 0, "owner", "localExpiry"), 130),
            (("mesh", "state"), "unavailable"),
            (("hosts", 0, "owner", "clock", "timeNamespace"), "time:11"),
        ):
            invalid = copy.deepcopy(value)
            change(invalid, path, replacement)
            self.reject("fleet", invalid)

    def test_remote_proof_is_conservative_and_not_future(self):
        value = fixture("fleet-v1", "local")
        remote = copy.deepcopy(value["hosts"][0])
        remote.update(hostId="fixture-remote", local=False)
        remote["sessions"][0]["hostId"] = "fixture-remote"
        owner = remote["owner"]
        owner["source"]["hostId"] = "fixture-remote"
        owner.update(
            transport="ready",
            localExpiry=9970,
            proof={
                "requestId": "probe-1",
                "sentAt": 120,
                "receivedAt": 130,
                "remainingMs": 9970,
                "marginMs": 100,
            },
        )
        value["hosts"].append(remote)
        value["mesh"].update(state="ready", revision="sha256:" + "b" * 64)
        self.accept("fleet", value)
        for path, replacement in (
            (("hosts", 1, "owner", "localExpiry"), 10100),
            (("hosts", 1, "owner", "proof", "receivedAt"), 131),
            (("hosts", 1, "owner", "proof", "marginMs"), 0),
            (("hosts", 1, "owner", "proof"), None),
        ):
            invalid = copy.deepcopy(value)
            change(invalid, path, replacement)
            self.reject("fleet", invalid)

    def test_fleet_frame_binding(self):
        value = fixture("fleet-v1", "frame")
        value["snapshot"]["viewRevision"] += 1
        self.reject("fleet-frame", value)

    def test_remote_expiry_bounds(self):
        for rtt in (0, 1, 100, 2000):
            for remaining in (0, 100, 1000, 10000):
                expiry = public.remote_expiry(1000, 1000 + rtt, remaining)
                self.assertEqual(expiry, 1000 + rtt + max(0, remaining - rtt - 100))
                self.assertLessEqual(expiry - (1000 + rtt), remaining)
        for args in ((1000, 999, 100), (1000, 3001, 100), (0, 0, True)):
            with self.assertRaises(ValueError):
                public.remote_expiry(*args)

    def test_pure_import_has_no_native_or_service_modules(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import tmux_observer.public; assert not any(any(s in n for s in ('collector', 'service', 'network', 'lifecycle', 'subprocess', 'socket')) for n in sys.modules if n.startswith('tmux_observer') or n in ('subprocess', 'socket'))",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class WireTests(unittest.TestCase):
    def test_adversarial_bytes(self):
        records = [
            b"{}",
            b"{}\n\n",
            b"{} \n",
            b" {}\n",
            b"{}{}\n",
            b'{"x":1,"x":2}\n',
            b"\xef\xbb\xbf{}\n",
            b'{"x":"\xff"}\n',
            b'{"x":"\\u0000"}\n',
            b'{"x":"\\ud800"}\n',
            b'{"x":NaN}\n',
            b'{"x":1e999}\n',
            b'{"x":9223372036854775808}\n',
            b"[" * 33 + b"0" + b"]" * 33 + b"\n",
            bytes_of("a" * 16385),
        ]
        for raw in records:
            with self.subTest(raw=raw[:80]):
                with self.assertRaises(ValueError):
                    public.decode_document(raw)
                with self.assertRaises((ValueError, UnicodeError)):
                    reader.wire(raw, public.DOCUMENT_LIMIT)

    def test_node_byte_and_envelope_limits(self):
        raw = bytes_of([0] * 100000)
        with self.assertRaises(ValueError):
            public.decode_document(raw)
        with self.assertRaises(ValueError):
            reader.wire(raw, public.DOCUMENT_LIMIT)
        with self.assertRaises(ValueError):
            public.decode_document(b"{}\n", limit=2)
        value = fixture("service-v1", "ready")
        value["extension"] = "a" * 16384
        with self.assertRaises(ValueError):
            public.validate_service_frame(value)
        with self.assertRaises(ValueError):
            reader.verify("service", value)

    def test_maximum_nesting_round_trip(self):
        value = 0
        for _ in range(32):
            value = [value]
        raw = public.encode_document(value)
        self.assertEqual(public.decode_document(raw), value)
        self.assertEqual(reader.wire(raw, public.DOCUMENT_LIMIT), value)
        with self.assertRaises(ValueError):
            public.encode_document([value])
