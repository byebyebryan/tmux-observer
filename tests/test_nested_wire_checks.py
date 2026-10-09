"""Nested tree reuse must preserve independent semantic and byte boundaries."""

import copy
import json
import unittest
from pathlib import Path

from tmux_observer import public
from tmux_observer._wire import ENVELOPE_LIMIT
from tmux_observer.attachments import ATTACHMENTS_LIMIT, validate_attachment_delivery

ROOT = Path(__file__).resolve().parents[1]


def fixture(bundle, name):
    return json.loads((ROOT / "contracts" / bundle / "fixtures" / (name + ".json")).read_text())


class NestedWireChecks(unittest.TestCase):
    def test_mutation_during_outer_schema_checks_requires_a_new_nested_tree_check(self):
        class ChangingEnvelope(dict):
            def __getitem__(self, key):
                if key == "schemaVersion":
                    dict.__getitem__(self, "snapshot")["extension"] = "unclean\n"
                return super().__getitem__(key)

        for bundle, name, validator in (
            ("service-v1", "ready", public.validate_service_frame),
            ("attachments-v1", "delivery-ready", validate_attachment_delivery),
            ("fleet-v1", "frame", public.validate_fleet_frame),
        ):
            with self.subTest(bundle=bundle), self.assertRaises(ValueError):
                validator(ChangingEnvelope(fixture(bundle, name)))

    def test_mutating_nested_python_containers_keep_the_full_wire_fallback(self):
        class ChangingSnapshot(dict):
            def __getitem__(self, key):
                if key == "schemaVersion":
                    self["extension"] = "unclean\n"
                return super().__getitem__(key)

        for bundle, name, validator in (
            ("service-v1", "ready", public.validate_service_frame),
            ("attachments-v1", "delivery-ready", validate_attachment_delivery),
            ("fleet-v1", "frame", public.validate_fleet_frame),
        ):
            value = fixture(bundle, name)
            value["snapshot"] = ChangingSnapshot(value["snapshot"])
            with self.subTest(bundle=bundle), self.assertRaises(ValueError):
                validator(value)

    def test_service_snapshot_byte_limit_still_applies_within_a_larger_envelope(self):
        value = fixture("service-v1", "ready")
        value["snapshot"]["extension"] = ["x" * 16384] * 64
        raw = public.encode_document(value["snapshot"], limit=public.FRAME_LIMIT)
        self.assertGreater(len(raw), public.DOCUMENT_LIMIT)
        self.assertLess(
            len(public.encode_document(value, limit=public.FRAME_LIMIT)), public.FRAME_LIMIT
        )
        with self.assertRaises(ValueError):
            public.validate_service_frame(value)

    def test_association_snapshot_keeps_its_smaller_byte_limit(self):
        value = fixture("attachments-v1", "delivery-ready")
        snapshot = value["snapshot"]
        generation = "g" * 16000
        snapshot["serverGeneration"] = generation
        snapshot["sessions"][0]["serverGeneration"] = generation
        client = copy.deepcopy(snapshot["clients"][0])
        client["sessionRef"]["serverGeneration"] = generation
        snapshot["clients"] = [
            {**copy.deepcopy(client), "clientPid": client["clientPid"] + offset}
            for offset in range(15)
        ]
        self.assertGreater(len(public.encode_document(snapshot)), ATTACHMENTS_LIMIT)
        self.assertLess(len(public.encode_document(value)), ATTACHMENTS_LIMIT + ENVELOPE_LIMIT)
        with self.assertRaises(ValueError):
            validate_attachment_delivery(value)

    def test_envelope_headers_keep_their_independent_byte_limit(self):
        for bundle, name, validator in (
            ("service-v1", "ready", public.validate_service_frame),
            ("attachments-v1", "delivery-ready", validate_attachment_delivery),
            ("fleet-v1", "frame", public.validate_fleet_frame),
        ):
            value = fixture(bundle, name)
            if bundle == "attachments-v1":
                value["source"]["nativeHostname"] = "x" * 16384
            else:
                value["extension"] = "x" * 16384
            self.assertGreater(
                len(public.encode_document({**value, "snapshot": None})),
                ENVELOPE_LIMIT,
            )
            with self.subTest(bundle=bundle), self.assertRaises(ValueError):
                validator(value)


if __name__ == "__main__":
    unittest.main()
