"""Consolidated B5: the 22-case hostile matrix for the strict
deployable evaluation-set manifest.

Cases 1-21 attack the shared parser directly (the same code path boot
and release resolution execute). Case 22 is the substitution attack a
self-consistent manifest can hide from a parser — a swapped file digest
with a recomputed aggregate — and is defeated at resolution against the
registry record.
"""

import json
import tempfile
import unittest
from pathlib import Path

from services.interview_ai import evaluation_manifest
from services.interview_ai import release as release_module
from services.interview_ai.evaluation_manifest import (
    EvaluationManifestError,
    aggregate_hash,
)

from tests.interview_ai.test_release_resolution import (
    RELEASE_ID,
    _scratch_release_root,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT / "prompts" / "interview" / "contracts" / "evaluation-set-1.json"
)


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _reaggregated(manifest):
    """Recompute the aggregate so only the rule under test can fire."""
    manifest["total_source_count"] = len(manifest["files"])
    manifest["evaluation_set_hash"] = aggregate_hash(manifest["files"])
    return manifest


class EvaluationManifestHostileMatrixTests(unittest.TestCase):
    def _rejects(self, manifest, fragment):
        with self.assertRaises(EvaluationManifestError) as caught:
            evaluation_manifest.parse_manifest(manifest)
        self.assertIn(fragment, str(caught.exception))

    def test_eval_case_0_control_the_committed_manifest_parses(self):
        entries, aggregate = evaluation_manifest.parse_manifest_bytes(
            MANIFEST_PATH.read_bytes()
        )
        self.assertEqual(len(entries), 42)
        self.assertEqual(aggregate, _manifest()["evaluation_set_hash"])

    def test_eval_case_1_duplicate_path(self):
        manifest = _manifest()
        manifest["files"].insert(1, dict(manifest["files"][0]))
        self._rejects(manifest, "duplicate")

    def test_eval_case_2_absolute_path(self):
        manifest = _manifest()
        manifest["files"][0]["path"] = "/etc/passwd"
        self._rejects(manifest, "repository-relative")

    def test_eval_case_3_parent_traversal_path(self):
        manifest = _manifest()
        manifest["files"][0]["path"] = "../secrets/key.pem"
        self._rejects(manifest, "traversal-free")

    def test_eval_case_4_backslash_path(self):
        manifest = _manifest()
        manifest["files"][0]["path"] = (
            manifest["files"][0]["path"].replace("/", "\\")
        )
        self._rejects(manifest, "forward slashes")

    def test_eval_case_5_dot_segment_path(self):
        manifest = _manifest()
        manifest["files"][0]["path"] = "./" + manifest["files"][0]["path"]
        self._rejects(manifest, "traversal-free")

    def test_eval_case_6_reordered_entries(self):
        manifest = _reaggregated(_manifest())
        manifest["files"][0], manifest["files"][1] = (
            manifest["files"][1], manifest["files"][0],
        )
        self._rejects(manifest, "sorted")

    def test_eval_case_7_uppercase_hex_digest(self):
        manifest = _manifest()
        manifest["files"][0]["sha256"] = manifest["files"][0]["sha256"].upper()
        self._rejects(manifest, "lowercase hex")

    def test_eval_case_8_short_digest(self):
        manifest = _manifest()
        manifest["files"][0]["sha256"] = manifest["files"][0]["sha256"][:63]
        self._rejects(manifest, "lowercase hex")

    def test_eval_case_9_entry_missing_key(self):
        manifest = _manifest()
        del manifest["files"][0]["category"]
        self._rejects(manifest, "exactly path, sha256, and category")

    def test_eval_case_10_entry_extra_key(self):
        manifest = _manifest()
        manifest["files"][0]["note"] = "extra"
        self._rejects(manifest, "exactly path, sha256, and category")

    def test_eval_case_11_top_level_missing_key(self):
        manifest = _manifest()
        del manifest["projection_version"]
        self._rejects(manifest, "top-level keys")

    def test_eval_case_12_top_level_extra_key(self):
        manifest = _manifest()
        manifest["comment"] = "extra"
        self._rejects(manifest, "top-level keys")

    def test_eval_case_13_wrong_schema(self):
        manifest = _manifest()
        manifest["schema"] = "interview-evaluation-set@1"
        self._rejects(manifest, "schema")

    def test_eval_case_14_wrong_responsible_version(self):
        manifest = _manifest()
        manifest["responsible_version"] = "interview-contracts@5"
        self._rejects(manifest, "responsible_version")

    def test_eval_case_15_wrong_projection_version(self):
        manifest = _manifest()
        manifest["projection_version"] = "peerslate.interview.evalset.v2"
        self._rejects(manifest, "projection_version")

    def test_eval_case_16_wrong_total_count_field(self):
        manifest = _manifest()
        manifest["total_source_count"] = 41
        self._rejects(manifest, "does not match the entry count")

    def test_eval_case_17_extra_entry(self):
        manifest = _manifest()
        extra = dict(manifest["files"][0])
        extra["path"] = "zzz/extra-fixture.json"
        manifest["files"].append(extra)
        _reaggregated(manifest)
        self._rejects(manifest, "exactly 42 sources")

    def test_eval_case_18_missing_entry(self):
        manifest = _manifest()
        manifest["files"].pop()
        _reaggregated(manifest)
        self._rejects(manifest, "exactly 42 sources")

    def test_eval_case_19_wrong_category_value(self):
        manifest = _manifest()
        manifest["files"][0]["category"] = "documentation"
        self._rejects(manifest, "closed enum")

    def test_eval_case_20_wrong_category_distribution(self):
        manifest = _manifest()
        for entry in manifest["files"]:
            if entry["category"] == "parity_fixture":
                entry["category"] = "golden_document"
                break
        _reaggregated(manifest)
        self._rejects(manifest, "golden documents")

    def test_eval_case_21_aggregate_mismatch(self):
        manifest = _manifest()
        manifest["evaluation_set_hash"] = "a" * 64
        self._rejects(manifest, "recomputed")

    def test_eval_case_22_substituted_digest_defeated_at_resolution(self):
        """A parser cannot know file bytes: swap one recorded digest and
        recompute the aggregate, and the manifest parses cleanly — but the
        registry record's evaluation_set_hash no longer matches, so
        resolution fails closed."""
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            manifest_path = (
                scratch_root / "prompts" / "interview" / "contracts"
                / "evaluation-set-1.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["sha256"] = "b" * 64
            _reaggregated(manifest)
            # Self-consistent: the shared parser accepts it.
            evaluation_manifest.parse_manifest(manifest)
            manifest_path.write_text(
                json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )


if __name__ == "__main__":
    unittest.main()
