"""Verify redacted managed cohort receipts and optional canonical selection."""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path)
    args = parser.parse_args()
    expected_files = set()
    for line in (HERE / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert name not in expected_files and "/" not in name
        expected_files.add(name)
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    assert expected_files == {
        p.name for p in HERE.iterdir() if p.is_file() and p.name != "SHA256SUMS"
    }
    record = read("deployment.json")
    assert record["state"] == "accepted_managed_full_view_update"
    assert record["observer"]["version"] == "0.6.0a9"
    assert record["frontend"]["version"] == "0.12.0a8"
    assert record["mesh"]["version"] == "0.1.0a24"
    assert not record["viewFeed"] and not record["semanticDelta"]
    for host, value in record["hosts"].items():
        assert host in {"snap", "starship"} and value["state"] == "passed"
        assert value["scope"] == "desktop"
        assert {h["hostId"] for h in value["freshHosts"]} == {"snap", "starship"}
        assert value["preexistingReferencesSurvive"]
        assert value["nativeGenerationAndCompleteReferencesPreserved"]
        assert value["independentAgentControlsAndServiceIdentitiesPreserved"]
        for key in ("meshState", "desktopState", "localBindingState"):
            assert value["prepared"][key] == "ready"
        assert {h["hostId"] for h in value["prepared"]["hosts"]} == {"snap", "starship"}
        assert all(
            h["transport"] == ("local" if h["local"] else "ready")
            for h in value["prepared"]["hosts"]
        )
        assert value["installedPayloads"]["core"] == 182
        assert value["installedPayloads"]["frontend"] == 383
        assert value["installedPayloads"]["mesh-plus-tmux-a24"] == 112
        audit = value["audit"]
        assert not audit["viewFeed"] and not audit["semanticDelta"]
        assert audit["bridgeRejectsFeedCommand"] and audit["runningFleetViewFeedFlagAbsent"]
        for version in audit["versions"].values():
            assert version == {"mesh": "0.1.0a24", "observer": "0.6.0a9"}
    candidate = read("frontend-candidate.json")
    assert candidate["observer"]["wheelSha256"] == record["observer"]["sha256"]
    assert candidate["wheel"]["sha256"] == record["frontend"]["wheelSha256"]
    assert len(candidate["observer"]["modules"]) == 87
    if args.selection:
        assert hashlib.sha256(args.selection.read_bytes()).hexdigest() == record["selectionSha256"]
        selected = json.loads(args.selection.read_text())
        assert selected["sharedMesh"]["tmuxBridge"]["viewFeed"] is False
        for name in ("core", "frontend"):
            for relative, entry in selected[name]["files"].items():
                raw = (Path.home() / selected[name]["prefix"] / relative).read_bytes()
                assert (
                    len(raw) == entry["bytes"]
                    and hashlib.sha256(raw).hexdigest() == entry["sha256"]
                )
    print("PASS: exact paired artifacts, both desktop deployments and full-view selection")


if __name__ == "__main__":
    main()
