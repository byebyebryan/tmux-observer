import argparse
import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--host", required=True)
p.add_argument("--scope", choices=("owner", "desktop"), required=True)
p.add_argument("--label", required=True)
a = p.parse_args()
h = Path.home()
w = Path("/tmp/tmux-publisher-integration-LvK1aJ")
source = h / ".local/share/chezmoi"
loader = importlib.machinery.SourceFileLoader("owned_ops", str(w / "operations"))
spec = importlib.util.spec_from_loader(loader.name, loader)
ops = importlib.util.module_from_spec(spec)
loader.exec_module(ops)
ops.ROOT = source
ops.TUPLE = source / "deployments/tmux-observer.json"
ops.FRONTEND_VERIFIER = h / "code/rofi-tmux-plus/scripts/check-installed-artifact"
before = json.loads((w / ("before-" + a.host + ".json")).read_text())
selection = json.loads(ops.TUPLE.read_text())
targets = [h / selection[k]["prefix"] for k in ("core", "frontend")] + [
    h / selection["sharedMesh"]["readerSdk"]["prefix"],
    h / ".local/bin/mesh-plus",
    h / ".local/share/tmux-observer/bin/tmux-observer-client",
    h / ".config/systemd/user/tmux-observer-owner@.service",
    h / ".config/systemd/user/tmux-observer-fleet@.service",
]


def run(argv, label):
    r = subprocess.run(list(map(str, argv)), capture_output=True, timeout=180, check=False)
    (w / (a.label + "-" + label + ".log")).write_bytes(r.stdout + r.stderr)
    if r.returncode:
        raise RuntimeError(label + " failed; private log retained")
    return r.stdout


def stop():
    if a.scope == "desktop":
        run(["systemctl", "--user", "stop", "tmux-observer-desktop.service"], "stop-desktop")
    run(["systemctl", "--user", "stop", "tmux-observer-owner@" + a.host + ".service"], "stop-owner")


def start():
    run(["systemctl", "--user", "daemon-reload"], "reload")
    run(
        ["systemctl", "--user", "start", "tmux-observer-owner@" + a.host + ".service"],
        "start-owner",
    )
    ops.owner_scope_ready(a.host, local_attachments=True)
    if a.scope == "desktop":
        run(["systemctl", "--user", "start", "tmux-observer-desktop.service"], "start-desktop")


with ops.staged_payloads(before, selection) as staged:
    stop()
    try:
        run(["chezmoi", "--source", source, "apply", "--force", *targets], "apply")
        start()
        run(
            [
                "/usr/bin/python3",
                w / "operations",
                "verify",
                "--host",
                a.host,
                "--scope",
                a.scope,
                "--source",
                source,
                "--selection",
                ops.TUPLE,
                "--frontend-verifier",
                ops.FRONTEND_VERIFIER,
                "--output",
                w / (a.label + "-" + a.host + ".json"),
            ],
            "verify",
        )
    except BaseException:
        stop()
        selected = {path: ops.node(h / path) for path in before["controls"]}
        changed = {
            ".local/bin/mesh-plus",
            ".local/share/tmux-observer/bin/tmux-observer-client",
            ".config/systemd/user/tmux-observer-owner@.service",
            ".config/systemd/user/tmux-observer-fleet@.service",
        }
        assert all(
            value == before["controls"][path]
            for path, value in selected.items()
            if path not in changed
        ), "unrelated control changed; preserve it for explicit reconciliation"
        ops.replace_payloads(staged, lambda: ops.restore_controls(before["controls"], selected))
        start()
        raise
print("selected and verified", a.host, a.scope)
