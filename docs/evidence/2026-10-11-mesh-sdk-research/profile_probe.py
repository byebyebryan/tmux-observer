"""Disposable Tmux profile feasibility model; not production implementation."""

import copy
from dataclasses import dataclass

from mesh_plus.api import NativeState, descriptor
from tmux_observer.delivery import validate_service_frame
from tmux_observer.native import FRAME_LIMIT, OBSERVATION_PROTOCOL


def require(value, code):
    if not value:
        raise ValueError(code)


class TmuxProfile:
    def __init__(self):
        self.descriptor = descriptor("tmux")
        require(self.descriptor.native_protocol == OBSERVATION_PROTOCOL, "native_protocol")
        require(self.descriptor.frame_bytes == FRAME_LIMIT, "native_frame_limit")

    def bind(self, host, source):
        return TmuxCodec(self, host, source)

    def validate_response(self, response):
        require(response["protocol"] == self.descriptor.profile_id, "profile_protocol")

    def restore_native(self, owner, records):
        metadata = owner["metadata"]
        snapshot = None if metadata is None else {**metadata, "sessions": list(records)}
        return {**owner["service"], "snapshot": snapshot}

    def record_host(self, record):
        return record["hostId"]

    def record_identity(self, record):
        return tuple(record[k] for k in ("hostId", "serverGeneration", "sessionId", "createdAt"))

    def record_receipts(self, record, state):
        return frozenset((r["sourceId"], r["component"]) for r in state.receipts
                         if r["sourceId"] == "default" and r["health"] in {"current", "partial"}) or None

    def record_eligible(self, record, state):
        return True


@dataclass(frozen=True)
class TmuxCodec:
    profile: TmuxProfile
    host: str
    source: str

    @property
    def profile_id(self):
        return self.profile.descriptor.profile_id

    def validate_bridge(self, payload):
        # This is the Reader-bound domain hook. Mesh Reader independently checks
        # the complete bridge/proof envelope. It is not the old direct-Client
        # TmuxMeshCodec API and is not a standalone Mesh proof validator.
        require(payload["hostId"] == self.host and payload["sourceId"] == self.source,
                "domain_bridge_binding")
        self.inspect_native(payload["ownerFrame"])

    def inspect_native(self, frame):
        validate_service_frame(frame)
        require(frame["source"]["hostId"] == self.host, "owner_host_scope")
        snapshot = frame["snapshot"]
        original = frame["receipt"]
        owner = {
            "protocol": self.profile.descriptor.native_protocol,
            "version": self.profile.descriptor.native_version,
            "metadata": None if snapshot is None else {
                k: copy.deepcopy(v) for k, v in snapshot.items() if k != "sessions"
            },
            "service": {k: copy.deepcopy(v) for k, v in frame.items() if k != "snapshot"},
        }
        receipts = [{"sourceId": "default", "component": "native",
                     "accepted": original["accepted"], "expiry": original["expiresAt"],
                     "health": "current" if original["state"] == "ready" else "stale"}]
        return NativeState(owner, [] if snapshot is None else copy.deepcopy(snapshot["sessions"]),
                           copy.deepcopy(frame["clock"]), frame["publisherId"], frame["encodedAt"], receipts)
