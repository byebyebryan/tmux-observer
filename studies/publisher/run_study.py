"""Explicit isolated study runner; emits scope/provenance and passing case IDs."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import unittest
import zipfile
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_wheel(path, expected, package_root, prefixes):
    raw = path.read_bytes()
    assert sha(raw) == expected, path.name
    matched = 0
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if any(name.startswith(prefix + "/") for prefix in prefixes) and not name.endswith("/"):
                assert (package_root / name).read_bytes() == archive.read(name), name
                matched += 1
    return {"file": path.name, "sha256": expected, "installedPayloadFiles": matched}


def ordinary():
    records = {}
    for name, args in (
        (
            "references",
            [
                "list-sessions",
                "-F",
                "#{pid}|#{socket_path}|#{session_id}|#{session_created}|#{session_attached}",
            ],
        ),
        ("hooks", ["show-hooks"]),
    ):
        result = subprocess.run(
            ["tmux", "-L", "default", *args], capture_output=True, timeout=3, check=False
        )
        records[name] = {"exit": result.returncode, "sha256": sha(result.stdout)}
    return records


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = "pass"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = "fail"

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = "error"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test.id()] = "skip"

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcomes[test.id()] = "fail"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--observer-wheel", type=Path, required=True)
    parser.add_argument("--mesh-wheel", type=Path, required=True)
    parser.add_argument("--baseline-wheel", type=Path, required=True)
    parser.add_argument("--baseline-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode, "run with -I -B"
    study = Path(__file__).resolve().parent
    root = study.parents[1]
    sys.path[:0] = [str(study), str(root / "tests_mesh")]

    import mesh_plus
    from cli_entry import cli_candidate

    import tmux_observer

    assert mesh_plus.__version__ == "0.1.0a13"
    assert tmux_observer.__version__ == "0.6.0a6"
    installed = Path(tmux_observer.__file__).resolve().parent.parent
    assert installed.is_relative_to(Path(sys.prefix))
    core = verify_wheel(
        args.observer_wheel,
        "232e604ab64c99657852b884720afaefdbcd45be00a56a797793b402e36ff640",
        installed,
        ("tmux_observer", "tmux_observer_client", "tmux_observer_actions"),
    )
    mesh = verify_wheel(
        args.mesh_wheel,
        "62b42bc76e7d79d95d89c41ee6f73c5e0169d24e2f1ac911c151c13f1f2b6f07",
        Path(mesh_plus.__file__).resolve().parent.parent,
        ("mesh_plus",),
    )
    assert (
        sha(args.baseline_wheel.read_bytes())
        == "c9fecd77e3ea181d43447784824616232874cfc9ead12a30460d0682bdc3684d"
    )
    baseline_check = subprocess.run(
        [
            str(args.baseline_python),
            "-I",
            "-B",
            "-c",
            "import mesh_plus,tmux_observer; assert mesh_plus.__version__=='0.1.0a10'; assert tmux_observer.__version__=='0.6.0a6'; print(mesh_plus.__file__)",
        ],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    baseline_root = Path(baseline_check.stdout.strip()).parent.parent
    baseline = verify_wheel(
        args.baseline_wheel,
        "c9fecd77e3ea181d43447784824616232874cfc9ead12a30460d0682bdc3684d",
        baseline_root,
        ("mesh_plus",),
    )
    verify_wheel(
        args.observer_wheel,
        core["sha256"],
        baseline_root,
        ("tmux_observer", "tmux_observer_client", "tmux_observer_actions"),
    )
    os.environ["TMUX_PUBLISHER_BASELINE_PYTHON"] = str(args.baseline_python.absolute())
    original, candidate = cli_candidate()
    inputs = {
        "observer": core,
        "mesh": mesh,
        "baselineMesh": baseline,
        "cli": {
            "releasedSha256": sha(original.encode()),
            "candidateSha256": sha(candidate.encode()),
            "change": "trusted-Python-factory-injection-only",
        },
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in (
                "attrs",
                "jsonschema",
                "jsonschema-specifications",
                "referencing",
                "rpds-py",
            )
        },
        "code": {
            p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(study.glob("*.py"))
        },
        "nativeFixture": {
            "path": "tests_mesh/native_fixture.py",
            "sha256": sha((root / "tests_mesh/native_fixture.py").read_bytes()),
        },
    }
    before = ordinary()
    started = time.monotonic()
    import test_feasibility

    suite = unittest.defaultTestLoader.loadTestsFromModule(test_feasibility)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    from mesh_plus.testing import profile_suite, run_suite

    from tmux_observer.mesh_profile import TmuxMeshProfile

    conformance = run_suite(
        profile_suite(lambda _domain: TmuxMeshProfile(), domain="tmux"), domain="tmux"
    )
    after = ordinary()
    report = {
        "format": "tmux-observer.publisher-feasibility.v1",
        "state": "research-only",
        "python": sys.version.split()[0],
        "inputs": inputs,
        "tests": result.testsRun,
        "cases": result.outcomes,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
        "seconds": round(time.monotonic() - started, 3),
        "native": test_feasibility.DETAILS,
        "profileConformance": conformance,
        "ordinaryDefaultServer": {"before": before, "after": after, "preserved": before == after},
        "scope": {
            "actualSSH": True,
            "ownedDefaultServers": True,
            "nativeCollection": "scheduled-owner-only",
            "copiedCliIsReleasedAPI": False,
            "meshSourceEdited": False,
            "runtimeAdopted": False,
            "resourceSoak": False,
            "GUI": False,
            "physicalSuspend": False,
        },
        "ok": result.wasSuccessful()
        and result.testsRun > 0
        and len(result.outcomes) == result.testsRun
        and all(v == "pass" for v in result.outcomes.values())
        and before == after
        and conformance["ok"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": report["ok"], "tests": report["tests"], "output": str(args.output)}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
