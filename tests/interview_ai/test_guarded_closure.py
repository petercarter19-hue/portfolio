"""Guarded dependency closure and tripwire (correction C1).

Three mechanical guards, run as repository tests so they execute in CI's
existing test step:

1. Closure — the import graph from every guarded entry point
   (services/interview_ai/*.py) must resolve, transitively, to stdlib
   modules, the closed external allowlist (each pinned in the locked
   requirements.txt, whose bytes are themselves a manifest entry), or a
   mutable repository file recorded in guarded-paths.json. An unmanifested
   mutable dependency fails here.
2. Recompute — every guarded blob and every digest recomputes from the
   committed bytes (delegated to the builder's --verify byte-lock, which
   the bundle-identity suite runs; this module re-checks the blob hashes
   directly for defense in depth).
3. Tripwire — a guarded path changing without the required
   contracts_version / guardian_set_version change fails, with the message
   naming the rule.
"""

import ast
import json
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from services.interview_ai import tripwire
from services.interview_ai.constants import (
    CONTRACTS_VERSION,
    GUARDIAN_SET_VERSION,
)
from services.interview_ai.identity import runtime_core_digest, sha256_hex

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "services" / "interview_ai"
GUARDED_PATHS = ROOT / "prompts" / "interview" / "contracts" / "guarded-paths.json"
REGISTRY_PATH = ROOT / "prompts" / "interview" / "control" / "registry.json"

sys.path.insert(0, str(ROOT / "scripts" / "interview_ai"))
import build_release_identity  # noqa: E402

# The closed external allowlist: import name -> pinned distribution name.
# Anything else imported from guarded code is a closure failure, even if it
# happens to be installed.
EXTERNAL_ALLOWLIST = {
    "anthropic": "anthropic",
    "itsdangerous": "itsdangerous",
    "mssql_python": "mssql-python",
    "dotenv": "python-dotenv",
}

# Repository-local import names -> repository paths.
REPO_MODULE_PATHS = {
    "db": "db.py",
    "services.database_service": "services/database_service.py",
}


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


class GuardedClosureTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(GUARDED_PATHS.read_text(encoding="utf-8"))
        cls.manifest_paths = {
            entry["path"] for entry in cls.manifest["entries"]
        }
        cls.registry_record = json.loads(
            REGISTRY_PATH.read_text(encoding="utf-8")
        )["active_release_set"]

    def test_import_closure_resolves_to_manifested_dependencies_only(self):
        stdlib = set(sys.stdlib_module_names)
        pending = sorted(PACKAGE_ROOT.glob("*.py"))
        visited = set()
        problems = []
        while pending:
            path = pending.pop()
            relative = path.relative_to(ROOT).as_posix()
            if relative in visited:
                continue
            visited.add(relative)
            if relative not in self.manifest_paths:
                problems.append(
                    "guarded code reaches unmanifested file: %s" % relative
                )
                continue
            for name in sorted(_module_imports(path)):
                top = name.split(".")[0]
                if top in stdlib:
                    continue
                if name.startswith("services.interview_ai"):
                    continue
                if name in REPO_MODULE_PATHS:
                    pending.append(ROOT / REPO_MODULE_PATHS[name])
                    continue
                if top in EXTERNAL_ALLOWLIST:
                    continue
                problems.append(
                    "%s imports %s, which is neither stdlib, allowlisted "
                    "external, nor a manifested repository module"
                    % (relative, name)
                )
        self.assertEqual(problems, [])

    def test_package_files_and_dependency_lock_are_all_manifested(self):
        expected = {
            path.relative_to(ROOT).as_posix()
            for path in PACKAGE_ROOT.glob("*.py")
        }
        expected.update(REPO_MODULE_PATHS.values())
        expected.add("requirements.txt")
        self.assertLessEqual(
            expected, self.manifest_paths,
            "the guarded manifest is missing required entries",
        )

    def test_every_external_allowlist_entry_is_pinned_in_the_lock(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        for distribution in sorted(set(EXTERNAL_ALLOWLIST.values())):
            self.assertRegex(
                requirements,
                r"(?m)^%s==" % distribution.replace("-", "[-_]"),
                "%s must be exact-pinned in requirements.txt" % distribution,
            )

    def test_the_locked_sdk_coordinate_matches_the_manifest(self):
        externals = self.manifest["external_artifacts"]
        names = {artifact["name"] for artifact in externals}
        self.assertIn("anthropic", names)
        anthropic_artifact = next(
            artifact for artifact in externals
            if artifact["name"] == "anthropic"
        )
        coordinate = anthropic_artifact["coordinate"]
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn(coordinate, requirements)
        self.assertEqual(
            externals, build_release_identity.EXTERNAL_ARTIFACTS,
        )
        for item in anthropic_artifact["artifacts"]:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_every_guarded_blob_recomputes(self):
        from services.interview_ai.fragments import (
            extract_fragments,
            split_fragment_path,
        )
        fragment_cache = {}
        for entry in self.manifest["entries"]:
            base_path, fragment_name = split_fragment_path(entry["path"])
            file_path = ROOT / base_path
            self.assertTrue(file_path.is_file(), entry["path"])
            if fragment_name is None:
                content = file_path.read_bytes()
            else:
                if base_path not in fragment_cache:
                    fragment_cache[base_path] = extract_fragments(
                        file_path.read_bytes()
                    )
                content = fragment_cache[base_path][fragment_name]
            self.assertEqual(
                sha256_hex(content), entry["sha256"],
                "guarded blob drifted: %s" % entry["path"],
            )

    def test_registry_identity_matches_the_working_tree(self):
        recomputed = runtime_core_digest(
            build_release_identity.guarded_manifest_entries(),
            build_release_identity.EXTERNAL_ARTIFACTS,
        )
        self.assertEqual(
            recomputed, self.registry_record["runtime_core_digest"],
        )


class VersionTripwireTests(unittest.TestCase):
    """B1: the tripwire compares against an IMMUTABLE prior version anchor
    that the ordinary builder never writes, so regenerating manifest and
    registry cannot silence it. The proof matrix below runs on the pure
    evaluation function with explicit prior/candidate inputs; the live
    test anchors the working tree; the drift simulations construct the
    exact defeat sequence the reviewers proved (edit a guarded file,
    regenerate everything, leave versions unchanged) as candidate
    snapshots."""

    ANCHORS_PATH = (
        ROOT / "prompts" / "interview" / "contracts" / "version-anchors.json"
    )

    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(
            cls.ANCHORS_PATH.read_text(encoding="utf-8")
        )
        cls.prior = {
            key: cls.document["anchors"][-1][key]
            for key in ("entries", "external_artifacts",
                        "guardian_set_version", "contracts_version",
                        "runtime_core_digest")
        }

    def _candidate_from_disk(self):
        return tripwire.identity_snapshot(
            build_release_identity.guarded_manifest_entries(),
            build_release_identity.EXTERNAL_ARTIFACTS,
            GUARDIAN_SET_VERSION,
            CONTRACTS_VERSION,
        )

    # -- the live control -------------------------------------------------

    def test_anchor_file_is_excluded_from_the_identity_it_pins(self):
        manifest = json.loads(GUARDED_PATHS.read_text(encoding="utf-8"))
        self.assertNotIn(
            "prompts/interview/contracts/version-anchors.json",
            {entry["path"] for entry in manifest["entries"]},
        )

    def test_anchor_chain_is_tamper_evident_and_recomputes(self):
        self.assertTrue(tripwire.verify_anchor_chain(self.document))
        tampered = json.loads(json.dumps(self.document))
        tampered["anchors"][-1]["runtime_core_digest"] = "f" * 64
        with self.assertRaises(tripwire.TripwireViolation):
            tripwire.verify_anchor_chain(tampered)

    def test_live_tripwire_working_tree_matches_the_anchor(self):
        violations = tripwire.evaluate_version_tripwire(
            self.prior, self._candidate_from_disk(),
        )
        self.assertEqual(
            violations, [],
            "TRIPWIRE: a guarded change arrived without the responsible "
            "contracts_version or guardian_set_version change. Bump the "
            "version AND record the new anchor with --write-anchor.",
        )

    # -- the proof matrix on the pure control -----------------------------

    def _synthetic(self, guardian="g@1", contracts="c@1", entries=None,
                   externals=None):
        entries = entries if entries is not None else [
            {"path": "services/interview_ai/a.py", "sha256": "1" * 64},
            {"path": "scripts/interview_ai/build_release_identity.py",
             "sha256": "2" * 64},
        ]
        externals = externals if externals is not None else [
            {"name": "anthropic", "coordinate": "anthropic==0.112.0",
             "artifacts": [{"filename": "a.whl", "sha256": "3" * 64}]},
        ]
        return tripwire.identity_snapshot(
            entries, externals, guardian, contracts,
        )

    def test_1_unchanged_identity_and_versions_passes(self):
        self.assertEqual(
            tripwire.evaluate_version_tripwire(
                self._synthetic(), self._synthetic(),
            ),
            [],
        )

    def test_2_changed_guarded_path_without_version_change_fails(self):
        candidate = self._synthetic(entries=[
            {"path": "services/interview_ai/a.py", "sha256": "9" * 64},
            {"path": "scripts/interview_ai/build_release_identity.py",
             "sha256": "2" * 64},
        ])
        violations = tripwire.evaluate_version_tripwire(
            self._synthetic(), candidate,
        )
        self.assertTrue(any(
            "services/interview_ai/a.py" in violation
            for violation in violations
        ))

    def test_3_changed_external_digest_without_version_change_fails(self):
        candidate = self._synthetic(externals=[
            {"name": "anthropic", "coordinate": "anthropic==0.113.0",
             "artifacts": [{"filename": "b.whl", "sha256": "4" * 64}]},
        ])
        violations = tripwire.evaluate_version_tripwire(
            self._synthetic(), candidate,
        )
        self.assertTrue(any("anthropic" in v for v in violations))

    def test_4_changed_manifest_builder_without_version_change_fails(self):
        candidate = self._synthetic(entries=[
            {"path": "services/interview_ai/a.py", "sha256": "1" * 64},
            {"path": "scripts/interview_ai/build_release_identity.py",
             "sha256": "8" * 64},
        ])
        violations = tripwire.evaluate_version_tripwire(
            self._synthetic(), candidate,
        )
        self.assertTrue(any(
            "build_release_identity.py" in violation
            for violation in violations
        ))

    def test_5_changed_identity_with_version_change_passes(self):
        candidate = self._synthetic(contracts="c@2", entries=[
            {"path": "services/interview_ai/a.py", "sha256": "9" * 64},
            {"path": "scripts/interview_ai/build_release_identity.py",
             "sha256": "2" * 64},
        ])
        self.assertEqual(
            tripwire.evaluate_version_tripwire(
                self._synthetic(), candidate,
            ),
            [],
        )

    def test_6_regenerated_but_inconsistent_candidate_fails(self):
        candidate = self._synthetic()
        candidate["runtime_core_digest"] = "e" * 64
        violations = tripwire.evaluate_version_tripwire(
            self._synthetic(), candidate,
        )
        self.assertTrue(any("recompute" in v for v in violations))

    def test_7_the_reviewers_defeat_sequence_now_fails(self):
        """Edit a guarded file, regenerate manifest AND registry perfectly,
        leave both versions unchanged: the regenerated candidate is fully
        self-consistent, and the anchor still trips it."""
        drifted_entries = [dict(entry) for entry in self.prior["entries"]]
        target = next(
            entry for entry in drifted_entries
            if entry["path"] == "services/interview_ai/telemetry.py"
        )
        target["sha256"] = "a" * 64  # the simulated telemetry.py edit
        candidate = tripwire.identity_snapshot(
            drifted_entries,
            self.prior["external_artifacts"],
            self.prior["guardian_set_version"],
            self.prior["contracts_version"],
        )
        # Perfect regeneration: the candidate recomputes from itself...
        self.assertEqual(
            candidate["runtime_core_digest"],
            runtime_core_digest(
                candidate["entries"], candidate["external_artifacts"],
            ),
        )
        # ...and the anchor still rejects it.
        violations = tripwire.evaluate_version_tripwire(self.prior, candidate)
        self.assertTrue(any(
            "services/interview_ai/telemetry.py" in violation
            for violation in violations
        ))

    # -- the anchor discipline -------------------------------------------

    def test_anchoring_refuses_drift_under_unchanged_versions(self):
        document = {"schema": "interview-version-anchors@1", "anchors": []}
        tripwire.append_anchor(
            document, self._synthetic(), "2026-08-21", "test baseline",
        )
        drifted = self._synthetic(entries=[
            {"path": "services/interview_ai/a.py", "sha256": "9" * 64},
            {"path": "scripts/interview_ai/build_release_identity.py",
             "sha256": "2" * 64},
        ])
        with self.assertRaises(tripwire.TripwireViolation):
            tripwire.append_anchor(
                document, drifted, "2026-08-21", "unlawful re-anchor",
            )

    def test_anchoring_accepts_a_version_bumped_change_and_chains(self):
        document = {"schema": "interview-version-anchors@1", "anchors": []}
        tripwire.append_anchor(
            document, self._synthetic(), "2026-08-21", "test baseline",
        )
        bumped = self._synthetic(contracts="c@2", entries=[
            {"path": "services/interview_ai/a.py", "sha256": "9" * 64},
            {"path": "scripts/interview_ai/build_release_identity.py",
             "sha256": "2" * 64},
        ])
        self.assertTrue(tripwire.append_anchor(
            document, bumped, "2026-08-22", "lawful version bump",
        ))
        self.assertEqual(len(document["anchors"]), 2)
        self.assertTrue(tripwire.verify_anchor_chain(document))

    def test_anchoring_the_same_identity_twice_is_a_noop(self):
        document = {"schema": "interview-version-anchors@1", "anchors": []}
        tripwire.append_anchor(
            document, self._synthetic(), "2026-08-21", "test baseline",
        )
        self.assertFalse(tripwire.append_anchor(
            document, self._synthetic(), "2026-08-21", "again",
        ))
        self.assertEqual(len(document["anchors"]), 1)


if __name__ == "__main__":
    unittest.main()
