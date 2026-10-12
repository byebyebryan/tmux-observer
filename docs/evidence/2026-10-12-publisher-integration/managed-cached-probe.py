import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

h = Path.home()
selection = json.loads((h / ".local/share/chezmoi/deployments/tmux-observer.json").read_text())
roots = [selection["sharedMesh"]["readerSdk"]["prefix"], selection["core"]["prefix"]] + [
    x["prefix"]
    for x in selection["sharedMesh"]["packages"]
    if x["name"] not in ("mesh-plus", "tmux-reader-sdk")
]
sys.path[:0] = [str(h / p) for p in roots]
import mesh_plus
from mesh_plus.api import Bridge, ReadGuard, configured_reader
from mesh_plus.library_authority import LibraryMeshAuthority
from mesh_plus.transport import IPCServer, boottime_ms

import tmux_observer
from tmux_observer.mesh_profile import TmuxMeshProfile
from tmux_observer.mesh_publisher import make_publisher


async def main(host):
    profile = TmuxMeshProfile()
    owner = (
        Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid())))
        / "tmux-observer/owner.sock"
    )
    with tempfile.TemporaryDirectory(prefix="tmux-sdk-cached-") as name:
        endpoint = Path(name) / "read.sock"
        adapter = make_publisher(host, "tmux_default", owner)
        server = await IPCServer(endpoint, Bridge(adapter).serve, max_clients=2).start()
        stream = None
        try:
            reader = await configured_reader(
                "tmux",
                source="tmux_default",
                socket=endpoint,
                scope="fleet",
                authority=LibraryMeshAuthority(),
                profile=profile,
            )
            snap = await reader.snapshot()
            assert snap["mesh"]["status"] == "complete", snap["mesh"]["status"]
            assert len(snap["mesh"]["hosts"]) == 2
            expected = {
                (r["hostId"], r["serverGeneration"], r["sessionId"], r["createdAt"])
                for r in snap["sessions"]
            }
            guard = ReadGuard("tmux", "b" * 32, profile=profile)
            stream = reader.watch(request_id="b" * 32, proof_interval=0.1)
            for _ in range(30):
                frame = await asyncio.wait_for(anext(stream), 5)
                guard.accept(frame)
                if expected <= {
                    (r["hostId"], r["serverGeneration"], r["sessionId"], r["createdAt"])
                    for r in guard.current(boottime_ms(), frame["mesh"]["reader"]["clock"])
                }:
                    break
            rows = guard.current(boottime_ms(), frame["mesh"]["reader"]["clock"])
            assert expected <= {
                (r["hostId"], r["serverGeneration"], r["sessionId"], r["createdAt"]) for r in rows
            }
            guard.disconnect()
            await stream.aclose()
            stream = None
            metrics = reader.inspect()
            assert metrics["activeConnections"] == 0 and metrics["cleanupFailures"] == 0
            result = {
                "state": "passed",
                "host": host,
                "readerSdk": mesh_plus.__version__,
                "observer": tmux_observer.__version__,
                "profile": "explicit TmuxMeshProfile",
                "snapshotHosts": len(snap["mesh"]["hosts"]),
                "currentRows": len(rows),
                "snapshotAndWatch": True,
                "ownedRetirement": True,
                "limits": [
                    "Cached owner facts; no collection, refresh, action, graphical input or persistent service selected"
                ],
            }
        finally:
            if stream:
                await stream.aclose()
            await server.close()
        return result


Path(sys.argv[2]).write_text(json.dumps(asyncio.run(main(sys.argv[1])), indent=2) + "\n")
print("managed explicit-profile cached delivery passed")
