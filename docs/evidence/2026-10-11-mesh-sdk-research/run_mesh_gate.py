"""Research only: preserve the real installed SDK; vary admission in memory."""

import argparse
import importlib.metadata
import json
import shlex
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

root = Path("/home/bryan/code/tmux-observer")
sys.path[:0] = [str(root / "tests_mesh"), str(root / "tests")]
parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("baseline", "admission-only", "explicit-profile", "mixed-native"))
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
from tmux_observer_client import _mesh_worker as worker

record = {"mode": args.mode, "mesh": importlib.metadata.version("mesh-plus"),
          "observer": importlib.metadata.version("tmux-observer")}
if args.mode == "baseline":
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(root / "tests_mesh")))
else:
    try:
        worker.MeshWorker("owned", authority=object())
    except ValueError as error:
        record["unmodifiedAdmission"] = str(error)
    else:
        raise AssertionError("unmodified Observer unexpectedly admits a11")
    with patch.object(worker, "__version__", "0.1.0a10"):
        if args.mode == "admission-only":
            suite = unittest.defaultTestLoader.discover(str(root / "tests_mesh"))
            result = unittest.TextTestRunner(verbosity=1).run(suite)
        else:
            from mesh_plus.api import ReadGuard, configured_reader
            from profile_probe import TmuxProfile
            profile = TmuxProfile()
            async def configured(*positional, **keyword):
                return await configured_reader(*positional, **keyword, profile=profile)
            def guard(*positional, **keyword):
                return ReadGuard(*positional, **keyword, profile=profile)
            import native_fixture
            original_ssh = native_fixture.NativeFixture.start_ssh
            def mixed_ssh(fixture):
                original_ssh(fixture)
                old_python = Path(__file__).parent / "a10/bin/python"
                fixture.write(fixture.bin / "mesh-plus",
                              "#!/bin/sh\nexec " + shlex.join([str(old_python), "-m", "mesh_plus.cli"])
                              + ' "$@" --config ' + shlex.quote(str(fixture.root / "sources.toml"))
                              + "\n", executable=True)
            with patch.object(worker, "configured_reader", configured), patch.object(worker, "ReadGuard", guard), \
                    patch("mesh_plus.state.ReferenceProfile", side_effect=AssertionError("implicit profile")), \
                    patch.object(native_fixture.NativeFixture, "start_ssh",
                                 mixed_ssh if args.mode == "mixed-native" else original_ssh):
                suite = unittest.defaultTestLoader.loadTestsFromName(
                    "test_native_mesh.NativeMeshTests" if args.mode == "mixed-native" else "test_fleet_mesh.MeshFleetTests")
                result = unittest.TextTestRunner(verbosity=1).run(suite)
                if args.mode == "mixed-native":
                    record["remoteBridgeSDK"] = "0.1.0a10"
record.update(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
              skipped=len(result.skipped), status="passed" if result.wasSuccessful() else "failed")
args.output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
raise SystemExit(not result.wasSuccessful())
