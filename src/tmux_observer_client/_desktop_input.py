"""Pure full-reference desktop input hashing."""

import hashlib

from tmux_observer.public import SessionReference, encode_document


def reference(row):
    return SessionReference(
        *(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt"))
    )


def input_hash(hosts):
    values = [
        {
            "hostId": host["hostId"],
            "local": host["local"],
            "publisherId": host["owner"]["publisherId"],
            "clock": host["owner"]["clock"],
            "route": host.get("route"),
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
