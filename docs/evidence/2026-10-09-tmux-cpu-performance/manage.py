"""Scoped three-package deployment; private preservation baselines stay in /tmp."""

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import re
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=("preflight", "apply", "reselect", "preserve", "rollback-provider"))
parser.add_argument("--host", required=True, choices=("snap", "starship"))
args = parser.parse_args()
loader = importlib.machinery.SourceFileLoader("ops", str(ROOT / "scripts/tmux-observer-operations"))
spec = importlib.util.spec_from_loader(loader.name, loader)
ops = importlib.util.module_from_spec(spec)
loader.exec_module(ops)
HOME = Path.home()
env = ops.environment()
stem = Path("/tmp/tmux-cpu-cp4-" + args.host)
selection = json.loads(ops.TUPLE.read_text())
roots = [selection[k]["prefix"] for k in ("core", "frontend", "meshProvider")]
targets = [str(HOME / relative) for relative in roots + ops.control_paths(args.host)]


def execute(argv, suffix=None, timeout=180):
    result = ops.run(argv, env=env, check=False, timeout=timeout)
    if suffix:
        Path(str(stem) + suffix).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("failed " + str(argv[:4]) + ": " + result.stderr[-1200:])
    return result.stdout


def native():
    def tmux(*argv):
        return execute(["/usr/bin/tmux", "-L", "default", *argv])

    references = sorted(tmux("list-sessions", "-F", "#{session_id}|#{session_created}").splitlines())
    digest = lambda text: hashlib.sha256(text.encode()).hexdigest()
    return {
        "generation": tmux("display-message", "-p", "#{start_time}|#{pid}|#{socket_path}").strip(),
        "references": references,
        "globalHooks": digest(tmux("show-hooks", "-g")),
        "sessionHooks": {ref: digest(tmux("show-hooks", "-t", ref.split("|")[0])) for ref in references},
    }


def unrelated():
    paths = (".config/kitty/kitty.conf", ".local/bin/rofi-agent-plus", ".local/bin/rofi-agent-plus-rofi",
             ".local/bin/agent-observer", ".local/bin/agent-observer-client")
    return {relative: ops.node(HOME / relative) for relative in paths}


def provider_files(expected):
    prefix = HOME / selection["meshProvider"]["prefix"]
    for name, value in expected.items():
        path = prefix / name
        assert path.is_file() and not path.is_symlink(), "provider file missing/linked: " + name
        raw = path.read_bytes()
        assert len(raw) == value["bytes"] and hashlib.sha256(raw).hexdigest() == value["sha256"], name
        assert bool(path.stat().st_mode & 0o111) == value["executable"], name
    return len(expected)


def mesh():
    value = json.loads(execute([str(HOME / ".local/bin/rofi-ssh-plus"), "mesh", "list", "--json"]))
    assert value["localHostId"] == args.host and {row["id"] for row in value["hosts"]} == {"snap", "starship"}
    return value["meshRevision"]


baseline_path = Path(str(stem) + "-preservation-before.json")
old_files = json.loads(Path("/tmp/tmux-cpu-cp4-provider-before-files.json").read_text())
result = {"host": args.host, "phase": args.phase, "result": "passed",
          "selectionSha256": hashlib.sha256(ops.TUPLE.read_bytes()).hexdigest()}
if args.phase == "preflight":
    assert provider_files(old_files) == len(old_files)
    baseline = {"native": native(), "unrelated": unrelated(), "meshRevision": mesh()}
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n")
    baseline_path.chmod(0o600)
    rendered = execute(["chezmoi", "--source", str(ROOT), "execute-template", "--file", str(ROOT / ".chezmoiexternal.toml")])
    externals = tomllib.loads(rendered)
    for kind in ("core", "frontend", "meshProvider"):
        selected = selection[kind]
        assert externals[selected["prefix"]]["url"] == selected["url"]
        assert externals[selected["prefix"]]["checksum"]["sha256"] == selected["sha256"]
    for relative in (".config/niri/config.kdl", ".config/niri/dms/binds.kdl"):
        assert execute(["chezmoi", "--source", str(ROOT), "cat", str(HOME / relative)]).encode() == (HOME / relative).read_bytes()
    execute(["chezmoi", "--source", str(ROOT), "diff", *targets], "-diff.log")
    execute(["chezmoi", "--source", str(ROOT), "--dry-run", "apply", "--verbose", *targets], "-dry-run.log")
    raw = Path(str(stem) + "-dry-run.log").read_text()
    changed = re.findall(r"^diff --git a/(.*?) b/", raw, re.M)
    assert all(any(name == root or name.startswith(root + "/") for root in roots)
               or name in ops.control_paths(args.host) for name in changed)
    result.update(scopedPaths=len(targets), priorProviderFiles=len(old_files), changedFileHeaders=len(changed),
                  dryRunSha256=hashlib.sha256(raw.encode()).hexdigest(), niriControlsByteUnchanged=True)
elif args.phase in ("apply", "reselect"):
    if args.phase == "reselect":
        baseline = json.loads(Path("/tmp/tmux-cpu-cp4-before-" + args.host + ".json").read_text())
        for relative, value in baseline["controls"].items():
            assert ops.node(HOME / relative) == value, "rollback control drift: " + relative
        for saved in baseline["payloads"].values():
            for name, value in saved["files"].items():
                path = HOME / saved["prefix"] / name
                assert path.is_file() and not path.is_symlink()
                raw = path.read_bytes()
                assert len(raw) == value["bytes"] and hashlib.sha256(raw).hexdigest() == value["sha256"]
        provider_files(old_files)
    execute(["systemctl", "--user", "stop", "tmux-observer-desktop.service", f"tmux-observer-owner@{args.host}.service"])
    execute(["chezmoi", "--source", str(ROOT), *(["--force"] if args.phase == "reselect" else []), "apply", "--verbose", *targets], "-" + args.phase + ".log")
    execute(["systemctl", "--user", "daemon-reload"])
    execute(["systemctl", "--user", "start", f"tmux-observer-owner@{args.host}.service"])
    execute(["systemctl", "--user", "start", "tmux-observer-desktop.service"])
    execute(["niri", "validate", "--config", str(HOME / ".config/niri/config.kdl")], "-niri-validate.log")
    result.update(scopedPaths=len(targets), providerFiles=provider_files(selection["meshProvider"]["files"]),
                  ownerStartedBeforeDesktop=True, niriValidation=True)
elif args.phase == "rollback-provider":
    # Paired rollback has already stopped services. Restore this separately owned
    # immutable provider through its previous managed source, then check all bytes.
    assert execute(["systemctl", "--user", "show", f"tmux-observer-owner@{args.host}.service", "--property=ActiveState", "--value"]).strip() == "inactive"
    execute(["chezmoi", "--source", "/tmp/tmux-fleet-fp4-managed-checkout", "--force", "apply", str(HOME / selection["meshProvider"]["prefix"])], "-rollback-provider.log")
    result.update(providerFiles=provider_files(old_files), immutablePriorProviderRestored=True)
else:
    before = json.loads(baseline_path.read_text())
    after = native()
    initial = before["native"]
    assert initial["generation"] == after["generation"] and initial["globalHooks"] == after["globalHooks"]
    assert set(initial["references"]) <= set(after["references"])
    assert all(after["sessionHooks"].get(ref) == value for ref, value in initial["sessionHooks"].items())
    assert before["unrelated"] == unrelated() and before["meshRevision"] == mesh()
    result.update(ordinaryReferencesPreserved=len(initial["references"]), currentReferences=len(after["references"]),
                  generationAndHooksPreserved=True, unrelatedControlsPreserved=True, meshRevisionPreserved=True,
                  providerFiles=provider_files(selection["meshProvider"]["files"]), foregroundInput=False)
Path(str(stem) + "-" + args.phase + ".json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
