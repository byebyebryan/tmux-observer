"""Owner sampling state. No native, IPC, routing or lifecycle imports."""

from __future__ import annotations

import copy
import uuid

from tmux_observer.delivery import SERVICE_PROTOCOL, validate_service_frame
from tmux_observer.native import encode_document, validate_observation

CADENCE_MS = 2000
BUDGET_MS = 2000
LEASE_MS = 10000
MIN_SPACING_MS = 1000


class OwnerState:
    def __init__(self, source: dict, clock: dict, *, publisher_id: str | None = None):
        self.source = copy.deepcopy(source)
        self.clock = copy.deepcopy(clock)
        self.publisher_id = publisher_id or str(uuid.uuid4())
        self.snapshot = None
        self.problem = None
        self.revision = 0
        self.active = True
        self.next_due = 0
        self.job = None
        self.successor = False
        self.evidence = {
            "state": "warming",
            "attempted": 0,
            "accepted": 0,
            "acceptedAttempt": 0,
            "startedAt": None,
            "acceptedAt": None,
            "expiresAt": None,
            "lastAttemptAt": None,
            "lastAttemptResult": "none",
            "leaseMs": LEASE_MS,
            "remainingMs": 0,
            "inFlight": False,
        }
        self.frame(0)

    def due(self, now: int) -> bool:
        return self.active and self.job is None and now >= self.next_due

    def begin(self, now: int) -> int | None:
        if not self.due(now):
            return None
        self.evidence["attempted"] += 1
        self.evidence.update(lastAttemptAt=now, inFlight=True)
        token = self.evidence["attempted"]
        self.job = (token, now, now + BUDGET_MS)
        self.next_due = now + CADENCE_MS
        return token

    def hint(self, now: int) -> None:
        """A fixed-source passive hint; callers implement bounded ticket admission."""
        if not self.active:
            return
        if self.job is not None:
            self.successor = True
        else:
            earliest = (
                now
                if self.evidence["lastAttemptAt"] is None
                else max(now, self.evidence["lastAttemptAt"] + MIN_SPACING_MS)
            )
            self.next_due = min(self.next_due, earliest)

    def failure(self, code: str, message: str, result: str = "failed") -> None:
        state = "unsupported" if result == "unsupported" else "failed"
        if self.evidence["state"] != state:
            self.revision += 1
        self.problem = {"code": code, "message": message}
        self.evidence.update(state=state, lastAttemptResult=result, remainingMs=0)

    def finish(self, token: int, observation: dict, now: int) -> bool:
        if not self.active or self.job is None or self.job[0] != token:
            return False
        _, job_start, deadline = self.job
        self.job = None
        self.evidence["inFlight"] = False
        successor = self.successor
        if successor:
            self.next_due = min(self.next_due, max(now, job_start + MIN_SPACING_MS))
            self.successor = False
        try:
            self.validate_sample(observation)
            if any(
                observation["source"][key] != self.source[key]
                for key in ("hostId", "uid", "server")
            ) or any(
                observation["clock"][key] != self.clock[key] for key in ("bootId", "timeNamespace")
            ):
                raise ValueError("source/clock mismatch")
            sampled = observation["sample"]
            if not job_start <= sampled["startedAt"] <= sampled["finishedAt"] <= now:
                raise ValueError("sample is not bound to started job")
        except (ValueError, KeyError, TypeError):
            self.failure("invalid_sample", "native sample violates publisher scope or profile")
            return False
        self.evidence["lastAttemptAt"] = sampled["startedAt"]
        if successor:
            self.next_due = max(self.next_due, sampled["startedAt"] + MIN_SPACING_MS)
        if now >= deadline:
            self.failure("deadline", "late native sample rejected")
            return False
        result = sampled["coverage"]
        if result != "complete":
            problem = sampled["error"]
            self.failure(problem["code"], problem["message"], result)
            return False

        if self.evidence["state"] != "ready" or self.facts(self.snapshot) != self.facts(
            observation
        ):
            self.revision += 1
        self.snapshot = copy.deepcopy(observation)
        self.problem = None
        self.evidence["accepted"] += 1
        self.evidence.update(
            state="ready",
            acceptedAttempt=token,
            startedAt=sampled["startedAt"],
            acceptedAt=now,
            expiresAt=sampled["startedAt"] + LEASE_MS,
            lastAttemptResult="complete",
        )
        return True

    def validate_sample(self, observation):
        validate_observation(observation)
        if observation["capabilities"]["panes"] or observation["capabilities"]["options"]:
            raise ValueError("expanded shared metadata profile")

    def facts(self, value):
        return (
            None
            if value is None
            else encode_document(
                {
                    key: value[key]
                    for key in ("source", "clock", "serverGeneration", "sessions", "capabilities")
                }
            )
        )

    def expire(self, now: int) -> None:
        if self.evidence["state"] == "ready" and now >= self.evidence["expiresAt"]:
            self.evidence["state"] = "expired"
            self.revision += 1

    def frame(self, now: int, *, kind="status", sequence=0, request_id=None, ticket=None) -> dict:
        self.expire(now)
        evidence = dict(self.evidence)
        evidence["remainingMs"] = (
            max(0, evidence["expiresAt"] - now) if evidence["state"] == "ready" else 0
        )
        value = {
            "protocol": SERVICE_PROTOCOL,
            "schemaVersion": 1,
            "kind": kind,
            "publisherId": self.publisher_id,
            "source": self.source,
            "clock": self.clock,
            "encodedAt": now,
            "sequence": sequence,
            "viewRevision": self.revision,
            "receipt": evidence,
            "snapshot": self.snapshot,
            "requestId": request_id,
            "error": self.problem,
            "ticket": ticket,
        }
        return copy.deepcopy(validate_service_frame(value))

    def stop(self) -> None:
        self.active = False
        if self.job is not None:
            self.job = None
            self.evidence["inFlight"] = False
            self.failure("stopped", "publisher stopped before sampling completed")
