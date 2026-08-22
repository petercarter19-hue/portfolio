"""B3: external runtime-lock verification — live, tampered, and gated."""

import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from services.interview_ai import runtime_lock

ROOT = Path(__file__).resolve().parents[2]


class RuntimeLockManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = runtime_lock.load_manifest()

    def test_the_running_environment_verifies(self):
        self.assertEqual(runtime_lock.verify_runtime_lock(self.manifest), [])

    def test_manifest_covers_the_four_interview_roots(self):
        names = {record["name"] for record in self.manifest["distributions"]}
        for root_name in ("anthropic", "itsdangerous", "python-dotenv",
                          "mssql-python"):
            self.assertIn(root_name, names)
        self.assertGreaterEqual(len(names), 25,
                                "the transitive closure went missing")

    def test_every_record_is_complete(self):
        for record in self.manifest["distributions"]:
            for field in ("name", "version", "edges", "production_abi",
                          "production_platform", "artifact_filename",
                          "artifact_sha256", "platform_independent",
                          "installed_projection", "responsible_version"):
                self.assertIn(field, record, record["name"])
            self.assertRegex(record["artifact_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(record["edges"], record["name"])
            projection = record["installed_projection"]
            self.assertTrue(projection["files"], record["name"])
            self.assertRegex(
                projection["projection_sha256"], r"^[0-9a-f]{64}$",
            )

    def test_lock_and_constraints_mirror_the_manifest_versions(self):
        lock = (ROOT / "prompts" / "interview" / "control"
                / "interview-runtime-lock.txt").read_text(encoding="utf-8")
        constraints = (ROOT / "prompts" / "interview" / "control"
                       / "interview-runtime-constraints.txt").read_text(
            encoding="utf-8")
        for record in self.manifest["distributions"]:
            pin = "%s==%s" % (record["name"], record["version"])
            self.assertIn(pin, lock)
            self.assertIn("--hash=sha256:%s" % record["artifact_sha256"],
                          lock)
            self.assertIn(pin, constraints)

    def test_wrong_version_in_manifest_is_a_violation(self):
        tampered = json.loads(json.dumps(self.manifest))
        target = next(record for record in tampered["distributions"]
                      if record["name"] == "anthropic")
        target["version"] = "0.999.0"
        violations = runtime_lock.verify_runtime_lock(tampered)
        self.assertTrue(any("wrong version" in v and "anthropic" in v
                            for v in violations))

    def test_tampered_projection_hash_is_a_violation(self):
        tampered = json.loads(json.dumps(self.manifest))
        target = next(record for record in tampered["distributions"]
                      if record["name"] == "itsdangerous")
        target["installed_projection"]["files"][0]["sha256"] = "f" * 64
        violations = runtime_lock.verify_runtime_lock(tampered)
        self.assertTrue(any("itsdangerous" in v for v in violations))

    def test_missing_distribution_record_detects_absence(self):
        tampered = json.loads(json.dumps(self.manifest))
        tampered["distributions"].append({
            "name": "definitely-not-installed-xyz",
            "version": "1.0",
            "platform_independent": False,
            "installed_projection": {"files": [],
                                     "projection_sha256": "0" * 64},
        })
        violations = runtime_lock.verify_runtime_lock(tampered)
        self.assertTrue(any("missing distribution" in v for v in violations))

    def test_projection_rules_exclude_only_nondeterministic_files(self):
        self.assertFalse(runtime_lock.is_projected_path(
            "pkg/__pycache__/mod.cpython-314.pyc"))
        self.assertFalse(runtime_lock.is_projected_path(
            "pkg-1.0.dist-info/RECORD"))
        self.assertFalse(runtime_lock.is_projected_path(
            "pkg-1.0.dist-info/INSTALLER"))
        self.assertTrue(runtime_lock.is_projected_path(
            "pkg-1.0.dist-info/METADATA"))
        self.assertTrue(runtime_lock.is_projected_path("pkg/native.so"))
        self.assertTrue(runtime_lock.is_projected_path("pkg/module.py"))


if __name__ == "__main__":
    unittest.main()
