"""Verify the ordinary chezmoi source, installed controls and provider bytes."""

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--host", choices=("snap", "starship"), required=True)
args = parser.parse_args()
root = Path.home() / ".local/share/chezmoi"
loader = importlib.machinery.SourceFileLoader("ops", str(root / "scripts/tmux-observer-operations"))
spec = importlib.util.spec_from_loader(loader.name, loader)
ops = importlib.util.module_from_spec(spec)
loader.exec_module(ops)
env = ops.environment()
tuple_bytes = ops.TUPLE.read_bytes()
selected = json.loads(tuple_bytes)
assert hashlib.sha256(tuple_bytes).hexdigest() == "645943a612f240df63e0f1694b04b22072e47811555abd776ff71740bd093429"
targets = [str(Path.home() / relative) for relative in
           [selected[k]["prefix"] for k in ("core", "frontend", "meshProvider")]
           + ops.control_paths(args.host)]
ops.run(["chezmoi", "--source", str(root), "verify", *targets], env=env, timeout=180)
provider = selected["meshProvider"]
for name, expected in provider["files"].items():
    path = Path.home() / provider["prefix"] / name
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    assert len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"]
    assert bool(path.stat().st_mode & 0o111) == expected["executable"]
result = {"host": args.host, "result": "passed", "selectionSha256": hashlib.sha256(tuple_bytes).hexdigest(),
          "ordinarySourceScopedVerify": True, "scopedPaths": len(targets), "providerFiles": len(provider["files"]),
          "nativeActions": False, "foregroundInput": False}
Path(f"/tmp/tmux-cpu-cp4-normal-source-verify-{args.host}.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
