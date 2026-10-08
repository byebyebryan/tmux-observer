"""Owner-scheduled association receipt; shares no lifetime with desktop scans."""

import copy

from ._owner_state import OwnerState
from .attachments import (
    ATTACHMENT_DELIVERY_PROTOCOL,
    ATTACHMENTS_LIMIT,
    validate_attachment_delivery,
    validate_attachments,
)
from .native import encode_document


class AttachmentState(OwnerState):
    def __init__(self, source, clock, pid_namespace, *, publisher_id):
        self.pid_namespace = pid_namespace
        super().__init__(source, clock, publisher_id=publisher_id)

    def validate_sample(self, observation):
        validate_attachments(observation)
        if observation["pidNamespace"] != self.pid_namespace:
            raise ValueError("local PID namespace changed")

    def facts(self, value):
        return (
            None
            if value is None
            else encode_document(
                {
                    key: value[key]
                    for key in (
                        "source",
                        "clock",
                        "pidNamespace",
                        "serverGeneration",
                        "sessions",
                        "clients",
                    )
                },
                limit=ATTACHMENTS_LIMIT,
            )
        )

    def frame(self, now, *, request_id=None, **_unused):
        self.expire(now)
        evidence = dict(self.evidence)
        evidence["remainingMs"] = (
            max(0, evidence["expiresAt"] - now) if evidence["state"] == "ready" else 0
        )
        return copy.deepcopy(
            validate_attachment_delivery(
                {
                    "protocol": ATTACHMENT_DELIVERY_PROTOCOL,
                    "schemaVersion": 1,
                    "publisherId": self.publisher_id,
                    "requestId": request_id,
                    "source": self.source,
                    "clock": self.clock,
                    "pidNamespace": self.pid_namespace,
                    "encodedAt": now,
                    "receipt": evidence,
                    "snapshot": self.snapshot,
                    "error": self.problem,
                }
            )
        )
