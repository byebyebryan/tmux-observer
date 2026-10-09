"""Pure prepared binding guards/projection; never schedules discovery."""

import copy

from .attachments import current_attachments

REF_KEYS = ("hostId", "serverGeneration", "sessionId", "createdAt")


def binding_key(host, *, now, context_id, epoch):
    if host is None:
        return None
    profile = current_attachments(host, host.get("localAttachments"), now)
    return (
        context_id,
        epoch,
        host["hostId"],
        host["owner"]["publisherId"],
        host["owner"]["serverGeneration"],
        tuple(sorted(host["owner"]["clock"].items())),
        tuple(
            sorted(
                (*(row[key] for key in REF_KEYS), row["attachedClients"])
                for row in host["sessions"]
            )
        ),
        None
        if profile is None
        else (
            profile["source"]["uid"],
            profile["pidNamespace"],
            tuple(
                sorted(
                    (
                        client["clientPid"],
                        client["processStartTicks"],
                        *(client["sessionRef"][key] for key in REF_KEYS),
                    )
                    for client in profile["snapshot"]["clients"]
                )
            ),
        ),
    )


def project_bindings(batch, *, accepted_key, current_key, now):
    if batch is None or current_key is None or current_key != accepted_key:
        return None
    result = copy.deepcopy(batch)
    result["encodedAt"] = now
    receipt = result["receipt"]
    if receipt["state"] == "ready" and receipt["expiresAt"] <= now:
        receipt.update(
            state="expired",
            error={"code": "binding_expired", "message": "native binding dependencies expired"},
        )
        for row in result["rows"]:
            row["association"] = {
                "state": "unknown",
                "resolvedAt": None,
                "reason": "binding_expired",
            }
    return result
