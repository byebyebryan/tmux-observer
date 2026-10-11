"""Pinned baseline comparison and owned synthetic profile experiments."""

import argparse
import asyncio
import copy
import hashlib
import importlib.abc
import importlib.metadata
import json
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

MESH = Path("/home/bryan/code/mesh-plus")
OBSERVER = Path("/home/bryan/code/tmux-observer")


class BlockNativeImplementations(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        prefixes = ("mesh_plus.observer", "agent_observer", "tmux_observer.collector",
                    "tmux_observer.owner", "tmux_observer._ipc", "tmux_observer.mesh",
                    "tmux_observer_actions", "tmux_observer_client")
        if any(fullname == p or fullname.startswith(p + ".") for p in prefixes):
            raise ImportError("research blocked implementation import: " + fullname)


def samples(profile=None):
    from mesh_plus.view import current_sessions, reconstructed, validate_response
    kwargs = {} if profile is None else {"profile": profile}
    result = []
    for path in sorted((MESH / "contracts/mesh-read-v1/examples").glob("tmux-*.json")):
        if "wss" in path.name:
            continue
        response = json.loads(path.read_text())
        validate_response(response, **kwargs)
        reader = response["mesh"]["reader"]
        result.append({"fixture": path.name,
                       "native": [reconstructed(response, h, **kwargs) for h in response["mesh"]["hosts"]
                                  if h["owner"] is not None],
                       "effective": [current_sessions(response, now, reader["clock"], **kwargs)
                                     for now in (reader["encodedAtMs"], reader["encodedAtMs"] + 1000, 2**52)]})
    return result


async def ipc(profile):
    from mesh_plus.api import Bridge, ReadGuard, configured_reader
    from mesh_plus.transport import IPCServer, boottime_ms
    sys.path.insert(0, str(MESH / "tests"))
    from sdk_fixture import Publisher
    publisher = Publisher("tmux", "owned", "tmux_default")
    publisher.state_profile = profile
    publisher.codec = profile.bind("owned", "tmux_default")
    publisher.validate = publisher.codec.validate_bridge
    with tempfile.TemporaryDirectory(prefix="tmux-sdk-profile-") as temporary:
        socket = Path(temporary) / "bridge.sock"
        server = await IPCServer(socket, Bridge(publisher).serve).start()
        try:
            reader = await configured_reader("tmux", source="tmux_default", socket=socket,
                                             scope="local", local_host="owned", profile=profile)
            frame = await reader.snapshot()
            assert frame["sessions"]
            request_id = "a" * 32
            guard = ReadGuard("tmux", request_id, profile=profile)
            stream = reader.watch(mode="local", request_id=request_id, proof_interval=0.1)
            try:
                for _ in range(20):
                    frame = await asyncio.wait_for(anext(stream), 3)
                    guard.accept(frame)
                    if frame["mesh"]["kind"] not in ("heartbeat", "gap") and guard.current(
                            boottime_ms(), frame["mesh"]["reader"]["clock"]):
                        break
                else:
                    raise AssertionError("explicit owner profile never became current")
                guard.disconnect()
                assert not guard.current(boottime_ms(), frame["mesh"]["reader"]["clock"])
            finally:
                await stream.aclose()
            metrics = reader.inspect()
            assert metrics["activeConnections"] == 0 and metrics["cleanupFailures"] == 0
        finally:
            await server.close()
    assert publisher.watchers == 0
    return {"snapshot": "passed", "watch": "passed", "disconnectRevocation": "passed",
            "ownedCleanup": "passed", "configuredSource": "tmux_default",
            "nativeReceiptSource": "default"}


def adversarial(profile):
    from mesh_plus.api import current_sessions, validate_response
    from mesh_plus.reader import Endpoint, Reader
    base = json.loads((MESH / "contracts/mesh-read-v1/examples/tmux-fleet.json").read_text())
    remote = next(i for i, h in enumerate(base["mesh"]["hosts"]) if not h["local"])
    cases = []
    def mutate(name, callback):
        value = copy.deepcopy(base); callback(value)
        try:
            validate_response(value, profile=profile)
        except Exception as error:
            cases.append({"case": name, "rejected": True, "error": getattr(error, "code", type(error).__name__)})
        else:
            raise AssertionError("accepted adversarial case " + name)
    mutate("forged owner digest", lambda v: v["mesh"]["hosts"][remote]["delivery"]["proof"].update(payloadDigest="sha256:" + "f" * 64))
    mutate("extended receipt expiry", lambda v: v["mesh"]["hosts"][remote]["receipts"][0].update(expiresAtMs=2**51))
    mutate("removed original receipt", lambda v: v["mesh"]["hosts"][remote].update(receipts=[]))
    mutate("duplicate complete identity", lambda v: v["sessions"].append(copy.deepcopy(v["sessions"][0])))
    mutate("record outside host scope", lambda v: v["sessions"][0].update(hostId="foreign"))
    for path in (OBSERVER / "contracts/service-v1/fixtures").glob("*.json"):
        if path.name not in ("ready.json", "warming.json"):
            continue
        frame = json.loads(path.read_text())
        codec = profile.bind(frame["source"]["hostId"], "tmux_default")
        state = codec.inspect_native(frame)
        assert profile.restore_native(state.owner, state.records) == frame
        altered = copy.deepcopy(frame); altered["sequence"] = True
        try:
            codec.inspect_native(altered)
        except Exception:
            cases.append({"case": path.name + " native bool counter", "rejected": True})
        else:
            raise AssertionError("native semantic validation was bypassed")
    codec = profile.bind("other", "tmux_default")
    try:
        Reader("tmux", [Endpoint("local", True, None, lambda: None, codec)], local_host="local", profile=profile)
    except Exception:
        cases.append({"case": "wrong endpoint binding", "rejected": True})
    else:
        raise AssertionError("wrong endpoint binding accepted")
    class NoEvidence(type(profile)):
        def record_receipts(self, record, state):
            return frozenset()
    assert not current_sessions(base, base["mesh"]["reader"]["encodedAtMs"],
                                base["mesh"]["reader"]["clock"], profile=NoEvidence())
    cases.append({"case": "empty required evidence", "positiveRows": 0})
    return cases


def purity(profile):
    frame = json.loads((OBSERVER / "contracts/service-v1/fixtures/ready.json").read_text())
    response = json.loads((MESH / "contracts/mesh-read-v1/examples/tmux-local.json").read_text())
    deny = AssertionError("profile callback performed I/O")
    with patch("builtins.open", side_effect=deny), patch.object(Path, "open", side_effect=deny), \
            patch.object(socket, "socket", side_effect=deny), patch.object(subprocess, "Popen", side_effect=deny):
        codec = profile.bind(frame["source"]["hostId"], "tmux_default")
        profile.validate_response(response)
        state = codec.inspect_native(frame)
        assert profile.restore_native(state.owner, state.records) == frame
        record = state.records[0]
        assert profile.record_host(record) == codec.host
        assert len(profile.record_identity(record)) == 4
        assert profile.record_receipts(record, state)
        assert profile.record_eligible(record, state)
        codec.validate_bridge({"hostId": codec.host, "sourceId": codec.source, "ownerFrame": frame})
    return {"callbacks": 9, "fileProcessSocketIOBlocked": True, "status": "passed"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("baseline", "profile"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"mesh": importlib.metadata.version("mesh-plus"),
              "observer": importlib.metadata.version("tmux-observer"), "mode": args.mode}
    if args.mode == "baseline":
        record["samples"] = samples()
    else:
        sys.meta_path.insert(0, BlockNativeImplementations())
        from profile_probe import TmuxProfile
        profile = TmuxProfile()
        with patch("mesh_plus.state.ReferenceProfile", side_effect=AssertionError("implicit reference profile")):
            record["samples"] = samples(profile)
            record["adversarial"] = adversarial(profile)
            record["purity"] = purity(profile)
            record["ipc"] = asyncio.run(ipc(profile))
        record["referenceProfileRequired"] = False
        record["implementationImportsBlocked"] = True
    record["sampleDigest"] = hashlib.sha256(json.dumps(record["samples"], sort_keys=True).encode()).hexdigest()
    record["status"] = "passed"
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "samples"}))


if __name__ == "__main__":
    main()
