"""Remote authority derives only from matching timely proofs in one epoch."""

from __future__ import annotations

import copy
import uuid

from tmux_observer.public import SERVICE_PROTOCOL, remote_expiry, validate_service_frame

from ._errors import ContractError


class RemoteState:
    def __init__(self, host_id):
        self.host_id = host_id
        self.epoch = 0
        self.transport = "absent"
        self.handshake = None
        self.scope = None
        self.sequence = None
        self.candidate = None
        self.confirmed = None
        self.expiry = 0
        self.proof = None
        self.pending = None
        self.last_frame = None
        self.next_probe = 0
        self.error = None

    def start(self, nonce, now):
        self.epoch += 1
        self.transport = "connecting"
        self.handshake = (nonce, now + 15000)
        self.scope = self.sequence = self.pending = self.candidate = None
        self.last_frame = None
        self.expiry = 0
        self.proof = None
        self.error = None

    def fail(self, code, message):
        self.transport = "failed"
        self.handshake = self.pending = None
        self.expiry = 0
        self.proof = None
        self.error = {"code": code, "message": message}

    def receive(self, value, now):
        try:
            validate_service_frame(value)
            if value["source"]["hostId"] != self.host_id:
                raise ValueError("foreign logical host")
            scope = (
                value["publisherId"],
                value["source"]["uid"],
                value["source"]["server"],
                value["clock"]["bootId"],
                value["clock"]["timeNamespace"],
            )
            if self.handshake is not None:
                nonce, deadline = self.handshake
                if (
                    now >= deadline
                    or value["kind"] != "resync"
                    or value["requestId"] != nonce
                    or value["sequence"] != 0
                ):
                    raise ValueError("invalid or late owner handshake")
                self.scope = scope
                self.handshake = None
                self.transport = "ready"
                self.next_probe = now
            elif self.transport != "ready" or scope != self.scope:
                raise ValueError("owner incarnation or transport epoch changed")
            if self.sequence is not None and (
                value["sequence"] <= self.sequence
                or value["sequence"] != self.sequence + 1
                and value["kind"] not in ("gap", "resync")
            ):
                raise ValueError("replayed or unmarked skipped sequence")
            self.sequence = value["sequence"]
            self.last_frame = now  # Liveness only; never renews positive validity.
            # Pushes carry candidates, not a second retained full owner snapshot.
            # A matching probe supplies the full document that becomes confirmed.
            self.candidate = copy.deepcopy({**value, "snapshot": None})
            evidence = value["receipt"]
            if evidence["state"] != "ready":
                self.confirmed = copy.deepcopy(value)
                self.expiry = 0
                self.proof = None
                self.error = copy.deepcopy(value["error"])
            matched = self.pending is not None and value["requestId"] == self.pending["requestId"]
            if matched:
                pending = self.pending
                self.pending = None
                if value["kind"] != "status" or now >= pending["sentAt"] + 2000:
                    raise ValueError("late or malformed matching probe")
                remaining = evidence["remainingMs"]
                expiry = remote_expiry(pending["sentAt"], now, remaining, 100)
                self.confirmed = copy.deepcopy(value)
                self.proof = {
                    "requestId": pending["requestId"],
                    "sentAt": pending["sentAt"],
                    "receivedAt": now,
                    "remainingMs": remaining,
                    "marginMs": 100,
                }
                self.expiry = expiry if evidence["state"] == "ready" else 0
                self.error = copy.deepcopy(value["error"])
                self.next_probe = now + 3000
            elif evidence["state"] == "ready" and (
                self.confirmed is None
                or evidence["acceptedAttempt"] != self.confirmed["receipt"]["acceptedAttempt"]
                or value["kind"] in ("gap", "resync")
            ):
                self.next_probe = min(self.next_probe, now)
            return matched
        except (ValueError, KeyError, TypeError) as error:
            self.fail("invalid_owner_stream", "remote owner provenance, order or proof failed")
            raise ContractError("operation_failed", "invalid remote owner stream") from error

    def probe(self, now):
        if self.transport != "ready" or self.pending is not None or now < self.next_probe:
            return None
        value = {
            "protocol": SERVICE_PROTOCOL,
            "schemaVersion": 1,
            "operation": "probe",
            "requestId": uuid.uuid4().hex,
            "expectedHost": self.host_id,
            "publisherId": self.scope[0],
        }
        self.pending = {"requestId": value["requestId"], "sentAt": now}
        return value

    def expire(self, now):
        if self.handshake is not None and now >= self.handshake[1]:
            self.fail("deadline", "owner subscription setup exceeded its deadline")
        elif self.pending is not None and now >= self.pending["sentAt"] + 2000:
            self.fail("deadline", "owner probe exceeded its send-based deadline")
        elif self.last_frame is not None and now - self.last_frame >= 10000:
            self.fail("deadline", "owner subscription became silent")

    def project(self):
        frame = self.confirmed or self.candidate
        snapshot = frame["snapshot"] if frame is not None else None
        owner = {
            "source": frame["source"] if frame else None,
            "clock": frame["clock"] if frame else None,
            "publisherId": frame["publisherId"] if frame else None,
            "encodedAt": frame["encodedAt"] if frame else None,
            "serverGeneration": snapshot["serverGeneration"] if snapshot else None,
            "sample": snapshot["sample"] if snapshot else None,
            "receipt": frame["receipt"] if frame else None,
            "transport": self.transport,
            "localExpiry": self.expiry,
            "proof": self.proof,
            "error": self.error,
        }
        return copy.deepcopy(owner), copy.deepcopy(snapshot["sessions"] if snapshot else [])
