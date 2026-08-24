import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_repository_evidence_policy.py"
SPEC = importlib.util.spec_from_file_location("evidence_policy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RepositoryEvidencePolicyTests(unittest.TestCase):
    def test_large_exact_duplicates_are_reviewed(self):
        self.assertEqual(MODULE.validate_policy(), [])

    def test_allowlist_has_only_complete_existing_groups(self):
        allowlist = MODULE.load_allowlist()
        actual = MODULE.collect_large_duplicate_groups(
            allowlist["threshold_bytes"]
        )
        self.assertEqual(set(actual), {entry["sha256"] for entry in allowlist["entries"]})


class GeneratedEvidenceStoragePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.scan_roots = (
            self.root / "docs" / "initiatives",
            self.root / "artifacts",
        )
        for scan_root in self.scan_roots:
            scan_root.mkdir(parents=True)
        self.allowlist_path = (
            self.root / "docs" / "governance" / "EVIDENCE_DUPLICATE_ALLOWLIST.json"
        )
        self.allowlist_path.parent.mkdir(parents=True)
        self.allowlist_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "threshold_bytes": 1_000_000,
                    "entries": [],
                }
            ),
            encoding="utf-8",
        )
        self.set_directory = (
            self.root / "docs" / "initiatives" / "PS-TEST-001" / "evidence" / "run-1"
        )
        self.set_directory.mkdir(parents=True)

    def _repo_path(self, path):
        return path.relative_to(self.root).as_posix()

    def _write_bytes(self, name, content):
        path = self.set_directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _file_record(self, path):
        content = path.read_bytes()
        return {
            "path": self._repo_path(path),
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
        }

    def _base_manifest(self, storage_mode, items, repository_proof):
        return {
            "schema_version": 1,
            "evidence_set_id": "PS-TEST-001/run-1",
            "generated": True,
            "storage_mode": storage_mode,
            "declared_set_bytes": sum(item["bytes"] for item in items),
            "declared_item_count": len(items),
            "worktree_count": {"current_full": 1, "projected_full": 1},
            "source_sha": "1" * 40,
            "base_sha": "2" * 40,
            "final_sha": "3" * 40,
            "verified_at": "2026-08-23T12:00:00Z",
            "retention_owner": "PeerSlate package owner",
            "recovery_owner": "PeerSlate repository owner",
            "complete_verified": True,
            "repository_proof": repository_proof,
            "items": items,
            "external_custody": None,
            "repository_exception": None,
        }

    def _write_manifest(self, manifest):
        path = self.set_directory / MODULE.STORAGE_MANIFEST_NAME
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return path

    def _validate(self, changed_paths=(), added_paths=(), live_count=None):
        return MODULE.validate_policy(
            root=self.root,
            scan_roots=self.scan_roots,
            allowlist_path=self.allowlist_path,
            changed_paths=changed_paths,
            added_paths=added_paths,
            live_full_worktree_count=live_count,
        )

    def test_preexisting_large_file_is_not_retroactively_invalidated(self):
        self._write_bytes("legacy.bin", b"x" * 1_000_000)
        self.assertEqual(self._validate(), [])

    def test_new_large_file_requires_storage_manifest_inventory(self):
        evidence = self._write_bytes("new.bin", b"x" * 1_000_000)
        errors = self._validate(
            changed_paths=[self._repo_path(evidence)],
            added_paths=None,
        )
        self.assertTrue(
            any("new large evidence is not inventoried" in error for error in errors),
            errors,
        )

    def test_repo_canonical_manifest_validates_real_bytes_and_hashes(self):
        evidence = self._write_bytes("new.bin", b"x" * 1_000_000)
        record = self._file_record(evidence)
        manifest = self._base_manifest("repo_canonical", [record], record.copy())
        manifest_path = self._write_manifest(manifest)

        changed = [self._repo_path(manifest_path), self._repo_path(evidence)]
        self.assertEqual(self._validate(changed, changed), [])

    def test_repo_canonical_above_replication_trigger_requires_reviewed_exception(self):
        evidence = self._write_bytes("new.bin", b"x" * 1_000_000)
        record = self._file_record(evidence)
        manifest = self._base_manifest("repo_canonical", [record], record.copy())
        manifest_path = self._write_manifest(manifest)
        changed = [self._repo_path(manifest_path), self._repo_path(evidence)]

        errors = self._validate(changed, changed, live_count=1074)
        self.assertTrue(any("repository_exception is required" in error for error in errors), errors)

        manifest["repository_exception"] = {
            "rationale": (
                "Repository custody is required because this canonical fixture is the "
                "only runnable proof used by the governed validation suite."
            ),
            "review_ref": "review:PS-TEST-001:independent-pass",
        }
        self._write_manifest(manifest)
        self.assertEqual(self._validate(changed, changed, live_count=1074), [])

    def test_external_manifest_requires_complete_custody_and_accepts_pinned_azure(self):
        proof = self._write_bytes("SUMMARY.md", b"verified external evidence summary\n")
        proof_record = self._file_record(proof)
        external_item = {
            "path": "captures/full-session.webm",
            "sha256": "a" * 64,
            "bytes": 20_000_000,
        }
        manifest = self._base_manifest("external", [external_item], proof_record)
        manifest["worktree_count"] = {"current_full": 61, "projected_full": 61}
        manifest["external_custody"] = {
            "provider": "azure_devops",
            "immutable_coordinate": "azure://peerslate/build/1234/artifact/evidence",
            "sole_custody": True,
            "retention_pinned": True,
            "retention_policy_ref": "azure-retention:permanent-evidence-v1",
        }
        manifest_path = self._write_manifest(manifest)
        changed = [self._repo_path(manifest_path), self._repo_path(proof)]
        self.assertEqual(self._validate(changed, changed), [])

        manifest["external_custody"]["retention_pinned"] = False
        manifest["external_custody"]["retention_policy_ref"] = None
        self._write_manifest(manifest)
        errors = self._validate(changed, changed)
        self.assertTrue(any("Azure sole custody requires retention_pinned" in e for e in errors), errors)
        self.assertTrue(any("Azure sole custody requires retention_policy_ref" in e for e in errors), errors)

    def test_manifest_detects_repository_ledger_hash_mismatch(self):
        evidence = self._write_bytes("new.bin", b"x" * 1_000_000)
        record = self._file_record(evidence)
        record["sha256"] = "f" * 64
        manifest = self._base_manifest("repo_canonical", [record], record.copy())
        manifest_path = self._write_manifest(manifest)
        changed = [self._repo_path(manifest_path), self._repo_path(evidence)]

        errors = self._validate(changed, changed)
        self.assertTrue(any("sha256 mismatch" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
