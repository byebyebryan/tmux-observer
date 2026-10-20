"""Verify retained pilot receipts and the unchanged candidate runtime payload."""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, help="optional original local pilot cache")
    args = parser.parse_args()
    record = read("qualification.json")
    assert record["state"] == "qualified_bounded_pilot_no_promotion"
    for name, entry in record["files"].items():
        raw = (HERE / name).read_bytes()
        assert sha256(raw) == entry["sha256"], name
        assert len(raw) == entry["bytes"], name
    candidate = read("candidate.json")
    assert candidate["source"]["commit"] == record["sourceCommit"]
    assert candidate["package"]["version"] == "0.6.0a9"
    assert candidate["wheel"]["sha256"] == record["observerWheelSha256"]
    # Documentation closeout can advance HEAD, but candidate runtime and all
    # frozen native schemas must remain the exact reviewed wheel source.
    for member, source in candidate["sourceFiles"].items():
        assert sha256((ROOT / source).read_bytes()) == candidate["members"][member]["sha256"], (
            source
        )
    for version in ("311", "314"):
        installed = read(f"installed-{version}.json")
        assert installed["mode"] == "installed" and installed["state"] == "passed"
        assert installed["observerSource"] == record["sourceCommit"]
        assert installed["observerWheel"] == record["observerWheelSha256"]
        parity = read(f"installed-parity-{version}.json")
        assert parity["meshVersion"] == "0.1.0a24"
        assert parity["observerVersion"] == "0.6.0a9"
        assert len(parity["meshRuntimeSchemaFiles"]) == 107
        for kind, count in (
            ("source-check", 405),
            ("installed", record["installedTests"]),
            ("sdk-feed", 40),
        ):
            log = gzip.decompress((HERE / f"{kind}-{version}.log.gz").read_bytes()).decode()
            assert re.search(rf"\nRan {count} tests in ", log), (kind, version)
            assert "\nFAILED" not in log and "(skipped=" not in log
    trials = read("measurements.json")["trials"]
    assert len(trials) == 8
    for workload in ("mostly-static", "all-changing"):
        selected = [t for t in trials if t["workload"] == workload]
        assert len(selected) == 4
        expected = selected[0]["usefulOutputs"]
        for trial in selected:
            assert trial["state"] == "passed" and trial["cleanup"]
            assert trial["modeOfQualification"] == "installed" and not trial["gcEnabled"]
            assert trial["usefulOutputs"] == expected
            assert trial["nativePassivity"] and trial["plannedReconnects"] == 1
            assert trial["freshProofNonces"] == 8 and trial["projectedFrames"] == 18
            assert trial["sessionsPerOwner"] == 16 and trial["stages"] == 3
            assert trial["cpuSeconds"] > 0 and trial["sampledSummedRssPeakBytes"] > 0
            metrics = trial["readerMetrics"]
            assert all(m["activeConnections"] == 0 and not m["partial"] for m in metrics)
            assert sum(m["operations"]["proofRequests"] for m in metrics) == 8
            snapshots = sum(m["operations"]["snapshotRequests"] for m in metrics)
            assert snapshots == (12 if trial["mode"] == "feed" else 8)
            mesh_bytes = sum(m["sentBytes"] + m["receivedBytes"] for m in metrics)
            native_bytes = sum(
                t["requestBytes"] + t["frameBytes"]
                for t in [trial["nativeLocal"], *trial["nativeRemote"]]
            )
            assert trial["meshBytes"] == mesh_bytes and trial["nativeBytes"] == native_bytes
            assert trial["totalCompletedJsonBytes"] == mesh_bytes + native_bytes
            for package, entry in trial["inputs"]["packages"].items():
                assert "/src/" not in entry["location"]
                for filename, digest in entry["files"].items():
                    assert digest == candidate["members"][package + "/" + filename]["sha256"]
    if args.artifacts:
        mesh = args.artifacts / "artifacts/mesh_plus-0.1.0a24-py3-none-any.whl"
        observer = args.artifacts / "observer-a9" / candidate["wheel"]["file"]
        assert sha256(mesh.read_bytes()) == record["meshWheelSha256"]
        assert sha256(observer.read_bytes()) == record["observerWheelSha256"]
    print(
        "PASS: exact source/artifact receipts, dual-version gates and eight matched installed trials"
    )


if __name__ == "__main__":
    main()
