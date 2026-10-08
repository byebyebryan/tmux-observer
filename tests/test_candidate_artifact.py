"""Committed snapshot and exact artifact boundaries, without host services."""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    "candidate_artifact", str(Path(__file__).resolve().parents[1] / "scripts/candidate-artifact")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
artifact = importlib.util.module_from_spec(spec)
loader.exec_module(artifact)


class CandidateArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.payload = {
            "tmux_observer/__init__.py": b"# observer\n",
            "tmux_observer_client/__init__.py": b"# client\n",
            "tmux_observer-0.1.0a1.dist-info/licenses/LICENSE": b"license fixture\n",
            "tmux_observer-0.1.0a1.data/data/share/tmux-observer/systemd/owner.service": b"[Unit]\nDescription=fixture\n",
        }
        for bundle in ("observation-v1", "service-v1", "fleet-v1"):
            prefix = "tmux_observer-0.1.0a1.data/data/share/tmux-observer/contracts/" + bundle
            self.payload[prefix + "/schema.json"] = b"{}\n"
            self.payload[prefix + "/SHA256SUMS"] = (
                artifact.sha256(b"{}\n") + "  schema.json\n"
            ).encode()
        for name, raw in self.payload.items():
            target = self.source / artifact.source_member(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self.payload.update(
            {
                "tmux_observer-0.1.0a1.dist-info/METADATA": b"Metadata-Version: 2.4\nName: tmux-observer\nVersion: 0.1.0a1\nRequires-Python: >=3.11\n",
                "tmux_observer-0.1.0a1.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: setuptools (84.0.0)\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
                "tmux_observer-0.1.0a1.dist-info/RECORD": b"",
            }
        )
        self.wheel = self.root / "tmux_observer-0.1.0a1-py3-none-any.whl"
        self.write_wheel()
        members, package = artifact.wheel_contents(self.wheel)
        self.value = {
            "schemaVersion": 1,
            "state": "built_unaccepted",
            "source": {"commit": "a" * 40, "tree": "b" * 40, "epoch": 1700000000},
            "package": package,
            "wheel": {
                "file": self.wheel.name,
                "bytes": self.wheel.stat().st_size,
                "sha256": artifact.sha256(self.wheel.read_bytes()),
            },
            "members": members,
            "sourceFiles": artifact.verify_source_payload(self.source, members),
            "contractBundles": {
                bundle: artifact.sha256(
                    (self.source / "contracts" / bundle / "SHA256SUMS").read_bytes()
                )
                for bundle in ("observation-v1", "service-v1", "fleet-v1")
            },
        }
        self.descriptor = self.root / "candidate.json"
        self.write_descriptor()

    def write_wheel(self):
        with zipfile.ZipFile(self.wheel, "w") as output:
            for name, raw in self.payload.items():
                output.writestr(name, raw)

    def write_descriptor(self):
        self.descriptor.write_text(json.dumps(self.value))

    def test_exact_candidate_verifies_without_importing_package(self):
        value, wheel = artifact.verify(self.descriptor)
        self.assertEqual(value, self.value)
        self.assertEqual(wheel, self.wheel)

    def test_changed_bytes_rejected_even_when_byte_count_is_updated(self):
        self.payload["tmux_observer/__init__.py"] = b"# changed observer\n"
        self.write_wheel()
        self.value["wheel"]["bytes"] = self.wheel.stat().st_size
        self.write_descriptor()
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            artifact.verify(self.descriptor)

    def test_members_and_source_mapping_must_match_actual_wheel(self):
        self.value["members"]["tmux_observer/__init__.py"]["sha256"] = "0" * 64
        self.write_descriptor()
        with self.assertRaisesRegex(ValueError, "content manifest differs"):
            artifact.verify(self.descriptor)
        self.value["members"], _ = artifact.wheel_contents(self.wheel)
        self.value["sourceFiles"]["tmux_observer/__init__.py"] = "src/elsewhere.py"
        self.write_descriptor()
        with self.assertRaisesRegex(ValueError, "source-member mapping differs"):
            artifact.verify(self.descriptor)

    def test_source_payload_requires_complete_unchanged_committed_files(self):
        omitted = dict(self.value["members"])
        del omitted["tmux_observer/__init__.py"]
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            artifact.verify_source_payload(self.source, omitted)
        (self.source / "src/tmux_observer/new.py").write_text("# missing in wheel\n")
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            artifact.verify_source_payload(self.source, self.value["members"])
        (self.source / "src/tmux_observer/new.py").unlink()
        (self.source / "src/tmux_observer/__init__.py").write_text("# changed\n")
        with self.assertRaisesRegex(ValueError, "differs from committed source"):
            artifact.verify_source_payload(self.source, self.value["members"])

    def test_contract_digest_must_match_packaged_manifest(self):
        self.value["contractBundles"]["fleet-v1"] = "0" * 64
        self.write_descriptor()
        with self.assertRaisesRegex(ValueError, "contract bundle digest differs"):
            artifact.verify(self.descriptor)

    def test_descriptor_cannot_promote_or_use_ambiguous_json(self):
        self.value["state"] = "accepted"
        self.write_descriptor()
        with self.assertRaisesRegex(ValueError, "cannot assert acceptance"):
            artifact.verify(self.descriptor)
        self.value["state"] = "built_unaccepted"
        self.write_descriptor()
        raw = self.descriptor.read_text().replace(
            '"schemaVersion": 1', '"schemaVersion": 1, "schemaVersion": 1'
        )
        self.descriptor.write_text(raw)
        with self.assertRaisesRegex(ValueError, "duplicate candidate descriptor key"):
            artifact.verify(self.descriptor)

    def test_descriptor_and_wheel_symlinks_are_rejected(self):
        link = self.root / "linked.json"
        link.symlink_to(self.descriptor)
        with self.assertRaisesRegex(ValueError, "invalid candidate descriptor"):
            artifact.verify(link)
        stored = self.root / "stored.whl"
        self.wheel.rename(stored)
        self.wheel.symlink_to(stored)
        with self.assertRaisesRegex(ValueError, "invalid wheel file"):
            artifact.verify(self.descriptor)

    def test_archive_paths_duplicate_members_and_links_are_rejected(self):
        for name in ("", ".", "../escape", "/absolute", "a/../escape", "a//b", "C:/escape", "a\\b"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe artifact"):
                artifact.safe_member(name)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.wheel, "a") as output:
                output.writestr("tmux_observer/__init__.py", b"duplicate")
        with self.assertRaisesRegex(ValueError, "duplicate/directory"):
            artifact.wheel_contents(self.wheel)
        self.write_wheel()
        with zipfile.ZipFile(self.wheel, "a") as output:
            item = zipfile.ZipInfo("tmux_observer/link.py")
            item.create_system = 3
            item.external_attr = 0o120777 << 16
            output.writestr(item, b"target.py")
        with self.assertRaisesRegex(ValueError, "wheel symlink"):
            artifact.wheel_contents(self.wheel)

    def test_unexpected_package_payload_is_rejected(self):
        self.payload["other_package/__init__.py"] = b"# unexpected\n"
        self.write_wheel()
        members, _ = artifact.wheel_contents(self.wheel)
        with self.assertRaisesRegex(ValueError, "unexpected wheel member"):
            artifact.verify_source_payload(self.source, members)

    def test_existing_or_dangling_output_is_preserved_before_build_commands(self):
        existing = self.root / "existing"
        existing.mkdir()
        marker = existing / "keep"
        marker.write_bytes(b"preserved")
        dangling = self.root / "dangling"
        dangling.symlink_to(self.root / "missing")
        with patch.object(artifact, "command") as run:
            for output in (existing, dangling):
                with (
                    self.subTest(output=output),
                    self.assertRaisesRegex(ValueError, "new directory"),
                ):
                    artifact.build(self.source, "HEAD", output)
            run.assert_not_called()
        self.assertEqual(marker.read_bytes(), b"preserved")
        self.assertTrue(dangling.is_symlink())

    def test_snapshot_uses_commit_and_preserves_worktree_drift(self):
        repo = self.root / "git"
        repo.mkdir()
        artifact.command(["git", "-C", str(repo), "init"])
        committed = repo / "file.txt"
        committed.write_bytes(b"committed\n")
        artifact.command(["git", "-C", str(repo), "add", "file.txt"])
        artifact.command(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Fixture",
            ]
        )
        committed.write_bytes(b"uncommitted\n")
        untracked = repo / "untracked.txt"
        untracked.write_bytes(b"untracked\n")
        output = self.root / "snapshot"
        output.mkdir()
        identity = artifact.snapshot(repo, "HEAD", output)
        self.assertEqual((output / "file.txt").read_bytes(), b"committed\n")
        self.assertFalse((output / "untracked.txt").exists())
        self.assertEqual(committed.read_bytes(), b"uncommitted\n")
        self.assertEqual(untracked.read_bytes(), b"untracked\n")
        self.assertEqual(
            identity["commit"],
            artifact.command(["git", "-C", str(repo), "rev-parse", "HEAD"]).decode().strip(),
        )


if __name__ == "__main__":
    unittest.main()
