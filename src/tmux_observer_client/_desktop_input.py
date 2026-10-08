"""Pure full-reference desktop input hashing."""

import hashlib

from tmux_observer._clock import boottime_ms
from tmux_observer.native import SessionReference, encode_document

from .attachments import association_facts


def reference(row):
    return SessionReference(
        *(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
    )


def input_hash(hosts, *, now=None):
    now = boottime_ms() if now is None else now
    values = [
        {
            "hostId": host["hostId"],
            "local": host["local"],
            "publisherId": host["owner"]["publisherId"],
            "clock": host["owner"]["clock"],
            "route": host.get("route"),
            "localAttachments": association_facts(host, host.get("localAttachments"), now)
            if host["local"]
            else None,
            "sessions": [
                {
                    key: row[key]
                    for key in (
                        "hostId",
                        "serverGeneration",
                        "sessionId",
                        "createdAt",
                        "name",
                        "attachedClients",
                        "pending",
                    )
                }
                for row in host["sessions"]
            ],
        }
        for host in hosts
    ]
    return "sha256:" + hashlib.sha256(encode_document(values, limit=16 * 1048576)).hexdigest()
