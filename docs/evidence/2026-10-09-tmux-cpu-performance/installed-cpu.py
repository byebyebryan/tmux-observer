"""Passive one-minute deployed sample; not a replacement for the ten-minute gate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--host", choices=("snap", "starship"), required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
hz = os.sysconf("SC_CLK_TCK")


def process(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return {"birth": fields[19], "ticks": int(fields[11]) + int(fields[12])}


def main_pid(unit):
    return int(subprocess.check_output([
        "systemctl", "--user", "show", unit, "--property=MainPID", "--value"
    ], text=True).strip())


units = subprocess.check_output([
    "systemctl", "--user", "list-units", "tmux-observer-fleet@*.service",
    "--state=running", "--plain", "--no-legend", "--no-pager"
], text=True).splitlines()
assert len(units) == 1, "expected one managed desktop fleet"
fleet_unit = units[0].split()[0]
pids = {"owner": main_pid(f"tmux-observer-owner@{args.host}.service"),
        "fleet": main_pid(fleet_unit)}
assert all(pids.values())
groups = {}
for role, pid in pids.items():
    group = next(row[3:] for row in Path(f"/proc/{pid}/cgroup").read_text().splitlines()
                 if row.startswith("0::"))
    groups[role] = Path("/sys/fs/cgroup") / group.lstrip("/")
bridges = []
for path in Path("/proc").iterdir():
    if not path.name.isdigit():
        continue
    try:
        argv = path.joinpath("cmdline").read_bytes().split(b"\0")
        if (str(Path.home() / ".local/share/tmux-observer/bin/tmux-observer").encode() in argv
                and b"bridge" in argv and b"--expected-host" in argv
                and argv[argv.index(b"--expected-host") + 1] == args.host.encode()):
            bridges.append(int(path.name))
    except (OSError, IndexError):
        pass
assert len(bridges) == 1, "expected one steady incoming bridge"
pids["incomingBridge"] = bridges[0]


def sample():
    values = {}
    for role, group in groups.items():
        values[role] = int(dict(row.split() for row in (group / "cpu.stat").read_text().splitlines())["usage_usec"])
    return {"at": time.monotonic(), "groups": values,
            "processes": {role: process(pid) for role, pid in pids.items()}}


first = sample()
for _ in range(6):
    time.sleep(10)
last = sample()
elapsed = last["at"] - first["at"]
for role, pid in pids.items():
    assert first["processes"][role]["birth"] == last["processes"][role]["birth"], "process restarted"
assert main_pid(f"tmux-observer-owner@{args.host}.service") == pids["owner"]
assert main_pid(fleet_unit) == pids["fleet"]
cpu = {role + "IncludingChildren": (last["groups"][role] - first["groups"][role]) / elapsed / 10000
       for role in groups}
cpu["incomingBridge"] = (last["processes"]["incomingBridge"]["ticks"] - first["processes"]["incomingBridge"]["ticks"]) / hz / elapsed * 100
cpu["physicalHostTotal"] = sum(cpu.values())
result = {"schemaVersion": 1, "host": args.host, "result": "passed",
          "selectionSha256": hashlib.sha256((root / "docs/tmux-observer-operations-tuple.json").read_bytes()).hexdigest(),
          "durationSeconds": elapsed, "cpuPercentOfOneCore": cpu,
          "instrumentation": "procfs and cgroup counters; no profiler, native actions or foreground input",
          "limits": ["Descriptive one-minute sample, not the ten-minute acceptance gate",
                     "Incoming bridge serves the peer fleet; logical aggregation uses the peer's incoming bridge",
                     "Active desktops differ from prior samples; no causal whole-service savings claim"]}
Path(f"/tmp/tmux-cpu-cp4-installed-cpu-{args.host}.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
