"""Mesh-owned design candidate, isolated from the released package.

Uses a13 Mesh internals as a prototype of a future public CachedPublisher.
No native producer, reference adapter or collector imports belong here.
"""

import asyncio
import copy
import re
import uuid
from dataclasses import dataclass

from mesh_plus.api import Publication
from mesh_plus.evidence import clock_domain, digest
from mesh_plus.protocol import check
from mesh_plus.state import inspect_state, resolve_profile, validate_bridge
from mesh_plus.transport import boottime_ms, finish_owned


@dataclass(frozen=True)
class CachedPublication:
    frame: dict
    epoch: str
    barrier: dict


class CachedPublisher:
    capabilities = ("snapshot", "proof", "subscribe")

    def __init__(self, domain, host, source, native, *, profile):
        self.state_profile = resolve_profile(domain, profile)
        self.codec = self.state_profile.bind(host, source)
        self.host, self.source = host, source
        self.profile = self.state_profile.descriptor.profile_id
        self.native = native
        self.bridge_id = str(uuid.uuid4())
        self.sequence = 0
        self.owner_binding = None
        self.accepted = {}

    def validate(self, payload):
        validate_bridge(self.state_profile, self.codec, payload)
        return payload

    def wrap(self, frame, nonce=None):
        # A native source may retain its input; queued publication owns its bytes.
        frame = copy.deepcopy(frame)
        state = inspect_state(self.state_profile, self.codec, frame)
        check(state.clock == clock_domain(), "source_clock_context")
        now = boottime_ms()
        check(state.emitted_ms <= now, "source_future_frame")
        binding = state.publisher, tuple(sorted(state.clock.items()))
        if binding == self.owner_binding:
            for receipt in state.receipts:
                previous = self.accepted.get((receipt["sourceId"], receipt["component"]))
                if previous is not None:
                    check(receipt["accepted"] >= previous[0], "source_receipt_regression")
                    check(
                        receipt["accepted"] != previous[0] or receipt["expiry"] == previous[1],
                        "source_lease_renewal",
                    )
        remaining = [
            {
                **{key: value for key, value in receipt.items() if key != "expiry"},
                "remainingMs": max(0, receipt["expiry"] - now)
                if receipt["health"] in {"current", "partial"}
                else 0,
            }
            for receipt in state.receipts
        ]
        result = {
            "meshProtocol": 1,
            "kind": "proof" if nonce is not None else "candidate",
            "nonce": nonce,
            "bridgeId": self.bridge_id,
            "sequence": self.sequence + 1,
            "sourceId": self.source,
            "hostId": self.host,
            "clock": state.clock,
            "encodedAtMs": now,
            "ownerFrame": frame,
            "ownerDigest": digest(frame),
            "remaining": remaining if nonce is not None else [],
            "error": None,
        }
        self.validate(result)
        # Failed admission cannot mutate the last accepted binding/counters.
        self.owner_binding = binding
        self.accepted = {
            (r["sourceId"], r["component"]): (r["accepted"], r["expiry"]) for r in state.receipts
        }
        self.sequence += 1
        return result

    async def snapshot(self, parameters):
        check(parameters == {}, "snapshot_parameters")
        return self.wrap(await self.native.snapshot())

    async def proof(self, parameters):
        check(
            set(parameters) == {"nonce"}
            and isinstance(parameters["nonce"], str)
            and re.fullmatch(r"[0-9a-f]{32,64}", parameters["nonce"]),
            "proof_parameters",
        )
        # A new checked cached reply follows nonce admission, never a watch copy.
        return self.wrap(await self.native.snapshot(), parameters["nonce"])

    async def watch(self):
        iterator = self.native.watch().__aiter__()
        try:
            async for native in iterator:
                state = inspect_state(self.state_profile, self.codec, native.frame)
                check(native.epoch == state.publisher, "native_epoch_binding")
                yield Publication(
                    self.wrap(native.frame), native.epoch, copy.deepcopy(native.barrier)
                )
        finally:
            await finish_owned(asyncio.create_task(iterator.aclose()))
