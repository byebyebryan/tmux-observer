"""Local coordinator input; never imported by installed acceptance workers."""

import hashlib
import importlib.machinery
import importlib.util
import subprocess


def stage_wheel(directory, evidence, *, repo, descriptor=None, env=None):
    """Build the checkout, or copy and verify one frozen candidate without building."""
    if descriptor is None:
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(directory), str(repo)],
            cwd=repo,
            env=env,
            capture_output=True,
            timeout=30,
            check=True,
        )
        wheels = list(directory.glob("*.whl"))
        if len(wheels) != 1:
            raise ValueError("one acceptance wheel required")
        return wheels[0]

    loader = importlib.machinery.SourceFileLoader(
        "acceptance_candidate_input", str(repo / "scripts/candidate-artifact")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    candidate = importlib.util.module_from_spec(spec)
    loader.exec_module(candidate)
    value, wheel = candidate.verify(descriptor)

    # Some native cases inject races through checkout classes. Do not label
    # those cases as candidate acceptance unless their whole packaged payload
    # agrees, including newly tracked files. Ignore generated/untracked caches.
    tracked = (
        subprocess.check_output(
            [
                "git",
                "-C",
                str(repo),
                "ls-files",
                "-z",
                "--",
                "LICENSE",
                "src/tmux_observer",
                "src/tmux_observer_client",
                "contracts",
                "systemd",
            ],
            timeout=10,
        )
        .decode()
        .split("\0")
    )
    candidate.require(
        set(value["sourceFiles"].values()) == set(filter(None, tracked)),
        "candidate payload coverage differs from harness checkout",
    )
    for member, filename in value["sourceFiles"].items():
        candidate.require(
            candidate.sha256((repo / filename).read_bytes()) == value["members"][member]["sha256"],
            "candidate payload differs from harness checkout: " + filename,
        )

    # Validate the copied inputs again before installation. Exclusive writes
    # preserve any existing wheel/descriptor in the caller's owned directory.
    raw = wheel.read_bytes()
    candidate.require(
        len(raw) == value["wheel"]["bytes"] and candidate.sha256(raw) == value["wheel"]["sha256"],
        "candidate changed before staging",
    )
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / wheel.name
    with destination.open("xb") as output:
        output.write(raw)
    staged_descriptor = directory / "candidate.json"
    descriptor_raw = descriptor.read_bytes()
    with staged_descriptor.open("xb") as output:
        output.write(descriptor_raw)
    staged, copied = candidate.verify(staged_descriptor)
    candidate.require(staged == value, "candidate descriptor changed before staging")
    evidence["harnessCommit"] = (
        subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=10)
        .decode()
        .strip()
    )
    evidence["harnessTreeDirty"] = bool(
        subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], timeout=10)
    )
    evidence["sourceCommit"] = value["source"]["commit"]
    evidence["sourceTreeDirty"] = False
    evidence["artifactInput"] = {
        "state": value["state"],
        "source": value["source"],
        "wheelSha256": value["wheel"]["sha256"],
        "descriptorSha256": hashlib.sha256(descriptor_raw).hexdigest(),
        "sourceFilesMatchHarness": True,
    }
    return copied
