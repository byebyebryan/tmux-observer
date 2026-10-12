"""Cached-only selected Agent facade probe; no provider collection or service restart."""

import argparse
import asyncio
import importlib.metadata
import json
import secrets
from pathlib import Path

from mesh_plus.api import Client
from mesh_plus.observer import ObserverCodec
from mesh_plus.transport import connect_ipc, connect_ssh


def receipts(frame):
    return {
        (source["provider"], source["namespace"], component["name"]): (
            component["accepted"],
            component["expiresBoottimeMs"],
        )
        for source in frame["sources"]
        for component in source["components"]
    }


async def run(args):
    codec = ObserverCodec("agent", args.host, "agent")
    reports = []
    for _ in range(2):
        channel = (
            await connect_ipc(args.socket)
            if args.socket
            else await connect_ssh(args.host, "agent", executable=str(args.ssh))
        )
        client = await Client.connect(
            channel,
            host=args.host,
            source="agent",
            profile="agent-observer.mesh-candidate.v1",
            codec=codec.validate,
        )
        try:
            baseline = await client.request()
            nonce = secrets.token_hex(16)
            proof = await client.request("proof", {"nonce": nonce})
            assert proof["nonce"] == nonce
            assert proof["ownerFrame"]["hostScope"] == args.host
            if baseline["ownerFrame"]["serviceId"] == proof["ownerFrame"]["serviceId"]:
                original = receipts(baseline["ownerFrame"])
                for key, (accepted, expiry) in receipts(proof["ownerFrame"]).items():
                    if key in original and accepted == original[key][0]:
                        assert expiry == original[key][1], "cached proof renewed a native sample"
            stream = await client.subscribe()
            while (frame := await asyncio.wait_for(anext(stream), 5))["kind"] != "data":
                pass
            assert frame["payload"]["ownerFrame"]["hostScope"] == args.host
            await stream.close()
            reports.append(
                {
                    "snapshotRows": len(baseline["ownerFrame"]["snapshot"]["sessions"]),
                    "proofRows": len(proof["ownerFrame"]["snapshot"]["sessions"]),
                    "watchRows": len(frame["payload"]["ownerFrame"]["snapshot"]["sessions"]),
                    "originalReceiptLeases": "preserved",
                }
            )
        finally:
            await client.close()
        assert channel.closed
    return {
        "state": "passed",
        "host": args.host,
        "transport": "IPC" if args.socket else "fixed SSH",
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("mesh-plus", "agent-observer", "tmux-observer")
        },
        "reconnectedSamples": reports,
        "cleanup": "owned channels retired",
        "limits": ["Cached delivery only; no Agent producer migration or collection parity claim"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--socket", type=Path)
    choice.add_argument("--ssh", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args)), indent=2))
