"""Tmux-specific Fleet v1 projection of already guarded Mesh host outcomes.

Mesh owns transport admission and remote validity. This adapter retains native
records, compares their counters, and preserves historical metadata on outages.
It performs no reads, network work, desktop scans or collection scheduling.
"""

import copy
import os

from ._owner_document import OwnerDocument
from ._remote_state import RemoteState


class MeshOwnerState(RemoteState):
    def __init__(self, host_id, *, local_clock=None):
        super().__init__(host_id, local_clock=local_clock)
        self.mesh_binding = None
        self.projection_encoded_at = None
        self.selected_route = None

    def accept_mesh(
        self, host, rows, *, reader_id, reader_clock, now, selected_route=None, reserve=None
    ):
        """Accept only after the enclosing replacement passed Mesh ReadGuard."""
        if host["hostId"] != self.host_id:
            raise ValueError("foreign Mesh host outcome")
        local = self.local_clock is not None
        if host["local"] != local or local and reader_clock != self.local_clock:
            raise ValueError("Mesh local clock or host binding differs")
        delivery = host["delivery"]
        owner = host["owner"]
        frame = None
        document = None
        scope = None
        if owner is not None:
            metadata = owner["metadata"]
            snapshot = None if metadata is None else {**metadata, "sessions": rows}
            document = OwnerDocument({**owner["service"], "snapshot": snapshot})
            frame = document.value
            if frame["source"]["hostId"] != self.host_id:
                raise ValueError("Mesh owner source differs")
            if local and (
                frame["clock"] != self.local_clock or frame["source"]["uid"] != os.getuid()
            ):
                raise ValueError("Mesh local native scope differs")
            scope = (
                frame["publisherId"],
                frame["source"]["uid"],
                frame["source"]["server"],
                frame["clock"]["bootId"],
                frame["clock"]["timeNamespace"],
            )
            previous = self.confirmed
            previous_scope = (
                (
                    previous["publisherId"],
                    previous["source"]["uid"],
                    previous["source"]["server"],
                    previous["clock"]["bootId"],
                    previous["clock"]["timeNamespace"],
                )
                if previous is not None
                else None
            )
            if previous is not None and scope == previous_scope:
                before, after = previous["receipt"], frame["receipt"]
                if (
                    frame["viewRevision"] < previous["viewRevision"]
                    or frame["encodedAt"] < previous["encodedAt"]
                    or any(after[key] < before[key] for key in ("attempted", "accepted"))
                    or before["acceptedAttempt"] is not None
                    and (
                        after["acceptedAttempt"] is None
                        or after["acceptedAttempt"] < before["acceptedAttempt"]
                    )
                ):
                    raise ValueError("Mesh native counters regressed")
        elif rows:
            raise ValueError("Mesh rows lack an owner")

        evidence = host["receipts"]
        expiry = 0
        proof = None
        encoded_at = frame["encodedAt"] if frame is not None else None
        if delivery["status"] == "ready" and frame is not None:
            if len(evidence) != (0 if frame["snapshot"] is None else 1):
                raise ValueError("Mesh native receipt coverage differs")
            if evidence:
                receipt = evidence[0]
                if (
                    receipt["sourceId"] != "default"
                    or receipt["component"] != "native"
                    or receipt["accepted"] != frame["receipt"]["accepted"]
                ):
                    raise ValueError("Mesh native receipt binding differs")
                current = receipt["health"] == "current"
                if current:
                    expiry = receipt["expiresAtMs"]
                    if type(expiry) is not int or expiry <= now:
                        # Queueing consumes validity, never renews the Mesh receipt.
                        expiry = 0
                if local:
                    if current and expiry > frame["receipt"]["expiresAt"]:
                        raise ValueError("Mesh local expiry exceeds native receipt")
                else:
                    bound = delivery["proof"]
                    if current and bound is None:
                        raise ValueError("Mesh positive remote receipt lacks proof")
                    if bound is not None:
                        encoded_at = bound["bridgeEncodedAtMs"]
                        remaining = max(0, frame["receipt"]["expiresAt"] - encoded_at)
                        proof = {
                            "requestId": bound["nonce"],
                            "sentAt": bound["sentAtMs"],
                            "receivedAt": bound["receivedAtMs"],
                            "remainingMs": remaining,
                            "marginMs": bound["marginMs"],
                        }

        if document is not None and reserve is not None:
            full_size = (
                document.full_size
                if frame["snapshot"] is not None or self.confirmed is None
                else self.confirmed_size
            )
            reserve(document.header_size + full_size)
        binding = (reader_id, delivery["epoch"], scope, selected_route)
        if binding != self.mesh_binding:
            self.epoch += 1
            self.mesh_binding = binding
        self.scope = scope
        self.handshake = self.pending = None
        self.last_frame = now
        self.expiry = expiry
        self.proof = proof
        self.selected_route = selected_route if delivery["status"] == "ready" else None
        self.transport = {
            "ready": "ready",
            "connecting": "connecting",
            "unavailable": "failed",
            "incompatible": "incompatible",
        }.get(delivery["status"], "failed")
        self.error = copy.deepcopy(delivery["error"] or (frame["error"] if frame else None))
        if document is not None:
            self.candidate = document.header()
            self.candidate_size = document.header_size
            # Warming is not an authoritative empty inventory. Preserve the last
            # complete descriptors with no current validity until a roster arrives.
            if frame["snapshot"] is not None or self.confirmed is None:
                self.confirm(document)
                self.projection_encoded_at = encoded_at

    def project_header(self):
        result = super().project_header()
        if (
            self.projection_encoded_at is not None
            and result["receipt"] is not None
            and result["receipt"]["expiresAt"] is not None
        ):
            # Fleet v1 binds remainingMs to encodedAt. Mesh proves a later cached
            # bridge encoding in the same SOURCE clock, so re-encode this header
            # without changing any original sample, acceptance or expiry value.
            result["encodedAt"] = self.projection_encoded_at
            result["receipt"]["remainingMs"] = max(
                0, result["receipt"]["expiresAt"] - self.projection_encoded_at
            )
        return result

    def expire(self, now):
        # Mesh owns channel liveness and proof scheduling. Local rendering still
        # checks expiry independently; polling this state schedules no work.
        return None
