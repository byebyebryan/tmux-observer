"""Observer-owned pure Tmux profile for the optional Mesh SDK interface v1.

Mesh owns envelope, proof and lease admission. These callbacks supply native
semantics through the supported Observer facades and perform no native I/O.
The bound codec is a Reader hook; direct Delivery clients keep TmuxMeshCodec's
complete bridge validation API.
"""

import copy
import re
from dataclasses import dataclass, field

from mesh_plus.api import SDK_INTERFACE_VERSION, NativeState, ProfileDescriptor, descriptor

from .delivery import validate_service_frame
from .native import FRAME_LIMIT, OBSERVATION_PROTOCOL, ValidationError


@dataclass(frozen=True)
class TmuxMeshProfile:
    """Lossless Service v1 projection with complete native session identities."""

    descriptor: ProfileDescriptor = field(init=False)

    def __post_init__(self):
        selected = descriptor("tmux")
        if (
            SDK_INTERFACE_VERSION != 1
            or selected.native_protocol != OBSERVATION_PROTOCOL
            or selected.native_version != 1
            or selected.frame_bytes != FRAME_LIMIT
        ):
            raise ValidationError("unsupported Mesh native profile")
        object.__setattr__(self, "descriptor", selected)

    def bind(self, host, source):
        return TmuxMeshStateCodec(self, host, source)

    def validate_response(self, response):
        if response["protocol"] != self.descriptor.profile_id:
            raise ValidationError("wrong Mesh Tmux profile")

    def restore_native(self, owner, records):
        metadata = owner["metadata"]
        return copy.deepcopy(
            {
                **owner["service"],
                "snapshot": None if metadata is None else {**metadata, "sessions": list(records)},
            }
        )

    def record_host(self, record):
        return record["hostId"]

    def record_identity(self, record):
        return tuple(
            record[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")
        )

    def record_receipts(self, record, state):
        return (
            frozenset(
                (receipt["sourceId"], receipt["component"])
                for receipt in state.receipts
                if receipt["sourceId"] == "default" and receipt["health"] in {"current", "partial"}
            )
            or None
        )

    def record_eligible(self, record, state):
        return True


@dataclass(frozen=True)
class TmuxMeshStateCodec:
    """Immutable endpoint binding, independent of the reference adapter."""

    profile: TmuxMeshProfile
    host: str
    source: str

    def __post_init__(self):
        if (
            not isinstance(self.host, str)
            or len(self.host) > 16_384
            or re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", self.host) is None
            or not isinstance(self.source, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,127}", self.source) is None
        ):
            raise ValidationError("invalid Mesh endpoint binding")

    @property
    def profile_id(self):
        return self.profile.descriptor.profile_id

    def validate_bridge(self, payload):
        # Reader checks the envelope/proof, then invokes inspect_native for
        # whole-frame admission. Avoid repeating that pure native validation.
        if payload["hostId"] != self.host or payload["sourceId"] != self.source:
            raise ValidationError("Mesh bridge endpoint mismatch")

    def inspect_native(self, frame):
        validate_service_frame(frame)
        if frame["source"]["hostId"] != self.host:
            raise ValidationError("Mesh native owner host mismatch")
        frame = copy.deepcopy(frame)
        snapshot = frame.pop("snapshot")
        receipt = frame["receipt"]
        owner = {
            "protocol": self.profile.descriptor.native_protocol,
            "version": self.profile.descriptor.native_version,
            "metadata": None
            if snapshot is None
            else {key: value for key, value in snapshot.items() if key != "sessions"},
            "service": frame,
        }
        return NativeState(
            owner,
            [] if snapshot is None else snapshot["sessions"],
            copy.deepcopy(frame["clock"]),
            frame["publisherId"],
            frame["encodedAt"],
            [
                {
                    "sourceId": "default",
                    "component": "native",
                    "accepted": receipt["accepted"],
                    "expiry": receipt["expiresAt"],
                    "health": "current" if receipt["state"] == "ready" else "stale",
                }
            ],
        )


__all__ = ["TmuxMeshProfile", "TmuxMeshStateCodec"]
