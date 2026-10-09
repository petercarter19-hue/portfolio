import copy
import io
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import ExitStack, nullcontext, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import delivery_preflight as preflight
from scripts import worktree_lifecycle as lifecycle_registry


ROOT = Path(__file__).resolve().parents[1]
COMPAT_FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "delivery_control_compat" / "manifest.json")
    .read_text(encoding="utf-8")
)
PRE_SAFE_CUSTODY_REF = COMPAT_FIXTURE["pre_safe_custody_ref"]
MAIN = "a" * 40
HEAD = "b" * 40
CANDIDATE = "c" * 40
BASE = "d" * 40


_IDENTITY_ENVIRONMENT = None


def setUpModule() -> None:
    global _IDENTITY_ENVIRONMENT
    _IDENTITY_ENVIRONMENT = patch.dict(
        os.environ,
        {
            "CODEX_THREAD_ID": "",
            "PEERSLATE_CALLER_REF": "",
            "PEERSLATE_CALLER_CONTEXT": "",
        },
    )
    _IDENTITY_ENVIRONMENT.start()


def tearDownModule() -> None:
    assert _IDENTITY_ENVIRONMENT is not None
    _IDENTITY_ENVIRONMENT.stop()


def claimed_surfaces(package, *product_paths):
    return [*product_paths, *preflight.control_relative_paths(package)]


def index():
    return {
        "schema_version": 3,
        "updated_at": "2026-08-23T00:00:00Z",
        "model": "generic_package_claims_v1",
        "claims_path": preflight.CLAIMS_REL,
        "rules": {
            "writer_capacity": "unbounded_while_disjoint",
            "reviewers_consume_writer_claim": False,
            "assigned_repository_authority": "through_merge_unless_explicitly_write_only",
            "production_operations": "manual_exact_main_sha_plus_owner_reference",
        },
        "legacy_snapshot": {
            "commit": MAIN,
            "path": preflight.INDEX_REL,
            "blob": "e" * 40,
        },
    }


def claim(package="PS-EXAMPLE-001", number=1, **overrides):
    value = {
        "schema_version": 1,
        "package": package,
        "state": "active",
        "outcome": "Deliver one bounded outcome.",
        "assignment": "implementation",
        "writer_ref": f"task:writer-{number}",
        "branch": f"work/2026-08-23-example-{number}",
        "delivery_path": "Protected",
        "repository_authority": "through_merge",
        "production_authority": "withheld",
        "activated_from_main": MAIN,
        "owner_outcome_ref": f"task:owner/turn:{number}",
        "surfaces": claimed_surfaces(package, f"src/package-{number}"),
        "evidence_surfaces": [preflight.evidence_relative_path(package)],
        "domains": [f"product:package-{number}"],
        "review_requirement": "independent",
        "handoff": None,
        "checkpoint_sha": None,
        "merged_sha": None,
        "closed_at": None,
    }
    value.update(overrides)
    value["_relative_path"] = preflight.claim_relative_path(value["package"])
    return value


def receipt(package="PS-EXAMPLE-001", **overrides):
    value = {
        "schema_version": 1,
        "package": package,
        "candidate_sha": CANDIDATE,
        "review_type": "independent",
        "reviewer_ref": "agent:independent-reviewer",
        "result": "pass",
        "reviewed_at": "2026-08-23T00:00:00Z",
        "findings": [],
        "evidence_ref": "task:review/evidence:1",
    }
    value.update(overrides)
    return value


def facts(**overrides):
    value = {
        "repository": str(ROOT),
        "branch": "work/2026-08-23-example-1",
        "head": HEAD,
        "origin_main": MAIN,
        "ahead": 1,
        "behind": 0,
        "clean": True,
        "branch_paths": ("src/package-1/change.py",),
        "main_paths": (),
        "worktree_paths": (),
        "fetched": True,
        "origin_url": "https://peerslate19@dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site",
    }
    value.update(overrides)
    return preflight.RepoFacts(**value)


def args(intent, **overrides):
    value = {
        "package": "PS-EXAMPLE-001",
        "intent": intent,
        "fetch": True,
        "require_clean": True,
        "candidate_sha": "",
        "candidate_worktree": "",
        "task_ref": "task:writer-1",
    }
    value.update(overrides)
    return Namespace(**value)


class NormalizationTests(unittest.TestCase):
    def test_optional_local_head_enumeration_is_exact_and_git_portable(self):
        def run_git(cwd, *arguments):
            result = subprocess.run(
                ["git", *arguments],
                cwd=cwd,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return result.stdout.strip()

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            run_git(repo, "init", "--initial-branch=main")
            run_git(repo, "config", "user.email", "preflight@peerslate.invalid")
            run_git(repo, "config", "user.name", "Preflight Test")
            (repo / "README.md").write_text("main\n", encoding="utf-8")
            run_git(repo, "add", "README.md")
            run_git(repo, "commit", "-m", "seed main")
            expected = run_git(repo, "rev-parse", "HEAD")
            run_git(
                repo,
                "branch",
                "work/2026-08-27-source/descendant",
                expected,
            )

            self.assertIsNone(
                preflight._optional_local_branch_sha(
                    repo, "work/2026-08-27-source"
                )
            )
            self.assertEqual(
                preflight._optional_local_branch_sha(repo, "main"), expected
            )

    def test_optional_local_head_enumeration_refuses_ambiguous_or_invalid_proof(self):
        exact_ref = "refs/heads/work/2026-08-27-source"
        valid = f"{HEAD}\0commit\0{exact_ref}\n"
        cases = {
            "command_failure": subprocess.CompletedProcess(
                [], 128, stdout="", stderr="enumeration failed"
            ),
            "malformed": subprocess.CompletedProcess(
                [], 0, stdout=f"{HEAD}\0{exact_ref}\n", stderr=""
            ),
            "duplicate": subprocess.CompletedProcess(
                [], 0, stdout=valid + valid, stderr=""
            ),
            "invalid_sha": subprocess.CompletedProcess(
                [], 0, stdout=f"invalid\0commit\0{exact_ref}\n", stderr=""
            ),
            "non_commit": subprocess.CompletedProcess(
                [], 0, stdout=f"{HEAD}\0blob\0{exact_ref}\n", stderr=""
            ),
            "unexpected_ref": subprocess.CompletedProcess(
                [],
                0,
                stdout=f"{HEAD}\0commit\0refs/heads/work/unexpected\n",
                stderr="",
            ),
        }
        for case, result in cases.items():
            with self.subTest(case=case), patch.object(
                preflight, "_git_result", return_value=result
            ), self.assertRaises(preflight.PreflightError):
                preflight._optional_local_branch_sha(
                    ROOT, "work/2026-08-27-source"
                )

    def test_authoritative_claim_blob_proof_requires_one_exact_ordinary_blob(self):
        path = preflight.claim_relative_path("PS-EXAMPLE-001")
        valid = subprocess.CompletedProcess(
            [], 0, stdout=f"100644 blob {HEAD}\t{path}\0", stderr=""
        )
        with patch.object(preflight, "_git_result", return_value=valid):
            self.assertEqual(
                preflight._claim_blob_at_commit(ROOT, MAIN, "PS-EXAMPLE-001"),
                HEAD,
            )

        invalid = {
            "missing": subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            "duplicate": subprocess.CompletedProcess(
                [],
                0,
                stdout=(
                    f"100644 blob {HEAD}\t{path}\0"
                    f"100644 blob {HEAD}\t{path}\0"
                ),
                stderr="",
            ),
            "symlink": subprocess.CompletedProcess(
                [], 0, stdout=f"120000 blob {HEAD}\t{path}\0", stderr=""
            ),
            "wrong_path": subprocess.CompletedProcess(
                [], 0, stdout=f"100644 blob {HEAD}\tother.json\0", stderr=""
            ),
            "command_failure": subprocess.CompletedProcess(
                [], 128, stdout="", stderr="tree lookup failed"
            ),
        }
        for case, result in invalid.items():
            with self.subTest(case=case), patch.object(
                preflight, "_git_result", return_value=result
            ), self.assertRaises(preflight.PreflightError):
                preflight._claim_blob_at_commit(ROOT, MAIN, "PS-EXAMPLE-001")

    def test_exact_main_fetch_uses_real_remote(self):
        def run_git(cwd, *arguments):
            result = subprocess.run(
                ["git", *arguments],
                cwd=cwd,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return result.stdout.strip()

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "origin.git"
            repo = base / "repo"
            run_git(base, "init", "--bare", str(remote))
            repo.mkdir()
            run_git(repo, "init", "--initial-branch=main")
            run_git(repo, "config", "user.email", "preflight@peerslate.invalid")
            run_git(repo, "config", "user.name", "Preflight Test")
            (repo / "README.md").write_text("main\n", encoding="utf-8")
            run_git(repo, "add", "README.md")
            run_git(repo, "commit", "-m", "seed main")
            expected = run_git(repo, "rev-parse", "HEAD")
            run_git(repo, "remote", "add", "origin", str(remote))
            run_git(repo, "push", "-u", "origin", "main")
            old_branch = "work/2026-08-25-real-terminal-old"
            successor = "work/2026-08-27-real-terminal-recovery"
            run_git(
                repo,
                "push",
                "origin",
                f"{expected}:refs/heads/{old_branch}",
                f"{expected}:refs/heads/{successor}",
            )

            self.assertEqual(
                preflight._exact_fetch_origin_branch(repo, "main"), expected
            )
            self.assertEqual(
                preflight._remote_branch_tuple(
                    repo, ("main", old_branch, successor)
                ),
                {
                    "main": expected,
                    old_branch: expected,
                    successor: expected,
                },
            )

    def test_exact_branch_fetch_refuses_a_tip_that_moves_during_proof(self):
        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        with patch.object(
            preflight, "_remote_branch_tip", side_effect=[HEAD, CANDIDATE]
        ), patch.object(preflight, "_git", side_effect=fake_git), self.assertRaises(
            preflight.PreflightError
        ):
            preflight._exact_fetch_origin_branch(
                ROOT, "work/2026-08-27-moving-branch"
            )

    def test_paths_are_repository_relative_and_normalized(self):
        self.assertEqual("docs/example", preflight.normalize_path("docs/example"))
        for unsafe in (
            "", "../secret", "/absolute", "C:/absolute", ".git/config",
            "docs/example/", "docs\\example", "docs/*.md", "docs/NUL.txt",
            "docs/trailing.", "docs//double",
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                preflight.normalize_path(unsafe)

    def test_hierarchical_paths_collide_but_siblings_do_not(self):
        self.assertTrue(preflight.paths_overlap("src/auth", "src/auth/routes.py"))
        self.assertTrue(preflight.paths_overlap("SRC/Auth", "src/auth"))
        self.assertFalse(preflight.paths_overlap("src/auth", "src/authoring"))

    def test_surface_extension_accepts_file_targets_and_refuses_broad_targets(self):
        blob = subprocess.CompletedProcess([], 0, stdout="blob\n", stderr="")
        tree = subprocess.CompletedProcess([], 0, stdout="tree\n", stderr="")
        missing = subprocess.CompletedProcess([], 128, stdout="", stderr="missing")
        with patch.object(preflight, "_git_result", return_value=blob):
            self.assertFalse(
                preflight.extension_surface_is_broad(
                    ROOT, "origin/main", "tests/test_database_service.py"
                )
            )
        with patch.object(preflight, "_git_result", return_value=tree):
            self.assertTrue(
                preflight.extension_surface_is_broad(ROOT, "origin/main", "tests")
            )
        with patch.object(preflight, "_git_result", return_value=missing):
            self.assertTrue(
                preflight.extension_surface_is_broad(
                    ROOT, "origin/main", "tests/test_future_service.py"
                )
            )
            self.assertTrue(
                preflight.extension_surface_is_broad(
                    ROOT, "origin/main", "tests/future-service"
                )
            )
            self.assertTrue(
                preflight.extension_surface_is_broad(
                    ROOT, "origin/main", "tests\\unsafe.py"
                )
            )

    def test_hierarchical_domains_collide_but_siblings_do_not(self):
        self.assertTrue(
            preflight.domains_overlap("shared:auth", "shared:auth:callback")
        )
        self.assertFalse(
            preflight.domains_overlap("shared:auth", "shared:authoring")
        )

    def test_porcelain_status_keeps_leading_status_columns(self):
        with patch.object(
            preflight,
            "_git_nul",
            return_value=[" M docs/file.md", "R  new/name.md", "old/name.md"],
        ):
            self.assertEqual(
                ("docs/file.md", "new/name.md", "old/name.md"),
                preflight._status_paths(ROOT),
            )

    def test_diff_paths_include_both_sides_of_a_rename(self):
        with patch.object(
            preflight, "_git_nul", return_value=["R100", "old.md", "new.md"]
        ):
            self.assertEqual(("new.md", "old.md"), preflight._diff_paths(ROOT, "a..b"))

    def test_copy_status_and_diff_include_only_the_destination(self):
        with patch.object(
            preflight, "_git_nul", return_value=["C  new.md", "old.md"]
        ):
            self.assertEqual(("new.md",), preflight._status_paths(ROOT))
        with patch.object(
            preflight, "_git_nul", return_value=["C100", "old.md", "new.md"]
        ):
            self.assertEqual(("new.md",), preflight._diff_paths(ROOT, "a..b"))

    def test_real_git_rename_keeps_both_endpoints_before_and_after_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.check_call(["git", "init", "-q"], cwd=repo)
            (repo / "old.md").write_text("owned\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "old.md"], cwd=repo)
            subprocess.check_call(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"],
                cwd=repo,
            )
            (repo / "old.md").rename(repo / "new.md")
            self.assertEqual(("new.md", "old.md"), preflight._status_paths(repo))
            subprocess.check_call(["git", "add", "-A"], cwd=repo)
            subprocess.check_call(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "rename"],
                cwd=repo,
            )
            self.assertEqual(("new.md", "old.md"), preflight._diff_paths(repo, "HEAD^..HEAD"))

    def test_real_git_copy_keeps_only_destination_unstaged_staged_and_committed(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.check_call(["git", "init", "-q"], cwd=repo)
            subprocess.check_call(["git", "config", "status.renames", "copies"], cwd=repo)
            subprocess.check_call(["git", "config", "diff.renames", "copies"], cwd=repo)
            (repo / "old.md").write_text("owned\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "old.md"], cwd=repo)
            subprocess.check_call(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"],
                cwd=repo,
            )
            (repo / "new.md").write_text("owned\n", encoding="utf-8")
            self.assertEqual(("new.md",), preflight._status_paths(repo))
            subprocess.check_call(["git", "add", "new.md"], cwd=repo)
            self.assertEqual(("new.md",), preflight._status_paths(repo))
            subprocess.check_call(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "copy"],
                cwd=repo,
            )
            self.assertEqual(("new.md",), preflight._diff_paths(repo, "HEAD^..HEAD"))


class ClaimValidationTests(unittest.TestCase):
    def test_valid_protected_claim_passes(self):
        self.assertEqual([], preflight.validate_claim(claim()))

    def test_claims_cannot_grant_production(self):
        errors = preflight.validate_claim(claim(production_authority="granted"))
        self.assertTrue(any("may not grant production" in error for error in errors))

    def test_writer_reference_is_opaque_not_a_person_identity(self):
        errors = preflight.validate_claim(claim(writer_ref="Peter Carter"))
        self.assertTrue(any("opaque" in error for error in errors))

    def test_handoff_destination_must_remain_bound_to_claim_identity(self):
        value = claim(
            writer_ref="agent:replacement-writer",
            branch="work/2026-08-27-example-recovery",
            handoff={
                "type": "owner_reassignment",
                "from_ref": "session:prior-writer",
                "to_ref": "agent:different-writer",
                "from_branch": "work/2026-08-25-example-old",
                "to_branch": "work/2026-08-27-different-recovery",
                "checkpoint_sha": HEAD,
                "owner_authorization_ref": "session:owner/decision:1",
            },
        )
        errors = preflight.validate_claim(value)
        self.assertTrue(any("current writer_ref" in error for error in errors))
        self.assertTrue(any("current claim branch" in error for error in errors))

    def test_protected_claim_requires_independent_review(self):
        errors = preflight.validate_claim(claim(review_requirement="self"))
        self.assertTrue(any("Protected" in error for error in errors))

    def test_reviewers_are_claim_free_and_narrower_writers_are_explicit(self):
        errors = preflight.validate_claim(claim(assignment="review_only"))
        self.assertTrue(any("claim-free" in error for error in errors))
        self.assertEqual([], preflight.validate_claim(claim(repository_authority="write_only")))

    def test_evidence_must_stay_inside_the_package_claim(self):
        errors = preflight.validate_claim(
            claim(evidence_surfaces=["unclaimed/evidence"])
        )
        self.assertTrue(any("outside the claim" in error for error in errors))

    def test_claim_receipt_and_evidence_paths_are_permanently_package_reserved(self):
        for other_path in preflight.control_relative_paths("PS-OTHER-001"):
            with self.subTest(other_path=other_path):
                value = claim(
                    state="closed",
                    merged_sha=MAIN,
                    closed_at="2026-08-23T00:00:00Z",
                )
                value["surfaces"].append(other_path)
                errors = preflight.validate_claim(value)
                self.assertTrue(
                    any("cross-package control path" in error for error in errors)
                )

        missing = claim()
        missing["surfaces"].remove(
            preflight.receipt_relative_path(missing["package"])
        )
        errors = preflight.validate_claim(missing)
        self.assertTrue(any("exact claim, receipt, and evidence" in error for error in errors))

    def test_broad_parent_of_control_records_is_forbidden(self):
        value = claim()
        value["surfaces"].append("docs/governance")
        errors = preflight.validate_claim(value)
        self.assertTrue(any("broad or cross-package" in error for error in errors))

    def test_runtime_or_initiative_paths_cannot_be_post_review_evidence(self):
        for unsafe in (["app.py"], ["docs/initiatives/PS-EXAMPLE-001"]):
            with self.subTest(unsafe=unsafe):
                errors = preflight.validate_claim(
                    claim(surfaces=["app.py", *unsafe], evidence_surfaces=unsafe)
                )
                self.assertTrue(any("runtime-inert" in error for error in errors))

    def test_paused_and_closed_claims_require_exact_receipts(self):
        paused = claim(state="paused")
        self.assertTrue(any("checkpoint_sha" in e for e in preflight.validate_claim(paused)))
        closed = claim(state="closed", checkpoint_sha=None)
        errors = preflight.validate_claim(closed)
        self.assertTrue(any("merged_sha" in e for e in errors))
        self.assertTrue(any("closed_at" in e for e in errors))

    def test_superseded_claim_validation(self):
        def superseded(**overrides):
            value = dict(
                state="superseded",
                checkpoint_sha=HEAD,
                superseded_at="2026-09-01T00:00:00Z",
                supersession={
                    "owner_authorization_ref": "task:owner/decision:supersede",
                    "superseded_by": ["PS-REPLACEMENT-001"],
                },
            )
            value.update(overrides)
            return claim(**value)

        self.assertEqual([], preflight.validate_claim(superseded()))
        self.assertEqual(
            [],
            preflight.validate_claim(
                superseded(
                    supersession={
                        "owner_authorization_ref": "task:owner/decision:supersede",
                        "withdrawal_reason": "Scope review failed; work withdrawn.",
                    }
                )
            ),
        )
        self.assertTrue(
            any(
                "checkpoint_sha" in e
                for e in preflight.validate_claim(superseded(checkpoint_sha=None))
            )
        )
        self.assertTrue(
            any(
                "superseded_at" in e
                for e in preflight.validate_claim(superseded(superseded_at=None))
            )
        )
        self.assertTrue(
            any(
                "must not record a merged_sha" in e
                for e in preflight.validate_claim(superseded(merged_sha=MAIN))
            )
        )
        self.assertTrue(
            any(
                "must not record closed_at" in e
                for e in preflight.validate_claim(
                    superseded(closed_at="2026-09-01T00:00:00Z")
                )
            )
        )
        self.assertTrue(
            any(
                "supersession record" in e
                for e in preflight.validate_claim(superseded(supersession=None))
            )
        )
        self.assertTrue(
            any(
                "owner_authorization_ref" in e
                for e in preflight.validate_claim(
                    superseded(supersession={"superseded_by": ["PS-REPLACEMENT-001"]})
                )
            )
        )
        self.assertTrue(
            any(
                "replacement package references" in e
                for e in preflight.validate_claim(
                    superseded(
                        supersession={
                            "owner_authorization_ref": "task:owner/decision:supersede",
                        }
                    )
                )
            )
        )
        self.assertTrue(
            any(
                "admits only" in e
                for e in preflight.validate_claim(
                    superseded(
                        supersession={
                            "owner_authorization_ref": "task:owner/decision:supersede",
                            "superseded_by": ["PS-REPLACEMENT-001"],
                            "bypass": True,
                        }
                    )
                )
            )
        )

    def test_only_superseded_claims_may_carry_supersession_fields(self):
        errors = preflight.validate_claim(
            claim(
                supersession={
                    "owner_authorization_ref": "task:owner/decision:supersede",
                    "superseded_by": ["PS-REPLACEMENT-001"],
                }
            )
        )
        self.assertTrue(
            any("only superseded claims" in e for e in errors), errors
        )
        errors = preflight.validate_claim(
            claim(superseded_at="2026-09-01T00:00:00Z")
        )
        self.assertTrue(
            any("only superseded claims" in e for e in errors), errors
        )

    def test_superseded_branch_stays_reserved(self):
        superseded = claim(
            package="PS-SUPERSEDED-001",
            number=1,
            state="superseded",
            checkpoint_sha=HEAD,
            superseded_at="2026-09-01T00:00:00Z",
            supersession={
                "owner_authorization_ref": "task:owner/decision:supersede",
                "withdrawal_reason": "Withdrawn after failed scope review.",
            },
        )
        rival = claim(package="PS-RIVAL-001", number=2, branch=superseded["branch"])
        errors = preflight.validate_claim_set(
            {
                "ps-superseded-001": superseded,
                "ps-rival-001": rival,
            }
        )
        self.assertTrue(
            any("branch collision" in e for e in errors), errors
        )

    def test_impossible_closed_timestamp_is_rejected(self):
        errors = preflight.validate_claim(
            claim(
                state="closed",
                merged_sha=MAIN,
                closed_at="2026-99-99T99:99:99Z",
            )
        )
        self.assertTrue(any("UTC closed_at" in error for error in errors))


class SafeCustodyClaimTests(unittest.TestCase):
    def _transition(self):
        before = claim(
            surfaces=claimed_surfaces(
                "PS-EXAMPLE-001", "src/released.py", "src/retained.py"
            ),
            domains=["product:example"],
        )
        after = copy.deepcopy(before)
        after["surfaces"] = claimed_surfaces("PS-EXAMPLE-001", "src/retained.py")
        responsibilities = [
            {"responsibility": "Maintain retained behavior", "domain": "product:example"}
        ]
        rationale = "The released file has no remaining package dependency."
        file_proofs = [{
            "path": "src/released.py",
            "main_mode": "100644",
            "main_blob": "a" * 40,
            "checkpoint_mode": "100644",
            "checkpoint_blob": "a" * 40,
            "unpublished_delta": False,
            "accepted_introduction": None,
        }]
        fixed_evidence = preflight.evidence_relative_path(before["package"])
        after["scope_release"] = {
            "schema_version": 1,
            "operation_id": "f" * 64,
            "control_branch": "work/2026-09-13-delivery-release-surfaces-example",
            "control_lease_sha256": "9" * 64,
            "quiescence_ref": "task:writer-quiescent",
            "prior_claim_sha256": preflight.canonical_claim_sha256(before),
            "reduction_sha256": preflight.scope_reduction_sha256(
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                before_domains=before["domains"],
                after_domains=after["domains"],
                retained_responsibilities=responsibilities,
                release_rationale=rationale,
                released_file_proofs=file_proofs,
                fixed_evidence_ref=fixed_evidence,
            ),
            "checkpoint_sha": HEAD,
            "prepared_from_main": MAIN,
            "released_surfaces": ["src/released.py"],
            "released_file_proofs": file_proofs,
            "prior_domains": before["domains"],
            "new_domains": after["domains"],
            "retained_responsibilities": responsibilities,
            "release_rationale": rationale,
            "fixed_evidence_ref": fixed_evidence,
            "registry_schema": 2,
            "index_schema": 4,
        }
        return before, after

    def _registry(self, after):
        proof = after["scope_release"]
        registry = {
            "schema_version": 2,
            "safe_custody": {
                "schema_version": 1,
                "migration": {
                    "from_schema": 1,
                    "to_schema": 2,
                    "before_sha256": "1" * 64,
                    "after_sha256": "",
                    "migrated_at": "2026-09-13T00:00:00Z",
                },
                "scope_releases": [{
                    "operation_id": proof["operation_id"],
                    "package": after["package"],
                    "task_ref": after["writer_ref"],
                    "worktree": str(ROOT),
                    "branch": after["branch"],
                    "control_branch": proof["control_branch"],
                    "control_lease_sha256": proof["control_lease_sha256"],
                    "quiescence_ref": proof["quiescence_ref"],
                    "checkpoint_sha": proof["checkpoint_sha"],
                    "prior_claim_sha256": proof["prior_claim_sha256"],
                    "reduction_sha256": proof["reduction_sha256"],
                    "intended_claim_sha256": preflight.canonical_claim_sha256(after),
                    "prepared_from_main": proof["prepared_from_main"],
                    "prepared_at": "2026-09-13T00:00:00Z",
                    "state": "pending",
                    "terminal_at": None,
                }],
                "reconciliations": [],
                "package_blocks": {
                    after["package"].casefold(): {
                        "kind": "scope_release",
                        "operation_id": proof["operation_id"],
                    }
                },
            },
        }
        lifecycle_registry._seal_safe_custody_after_sha256(registry)
        return registry

    def _domain_only_transition(self, before_domains, after_domains):
        before, after = self._transition()
        before["domains"] = before_domains
        after["surfaces"] = copy.deepcopy(before["surfaces"])
        after["domains"] = after_domains
        proof = after["scope_release"]
        proof["released_surfaces"] = []
        proof["released_file_proofs"] = []
        proof["prior_domains"] = before_domains
        proof["new_domains"] = after_domains
        proof["retained_responsibilities"] = [
            {
                "responsibility": "Maintain retained behavior",
                "domain": after_domains[0],
            }
        ]
        proof["prior_claim_sha256"] = preflight.canonical_claim_sha256(before)
        proof["reduction_sha256"] = preflight.scope_reduction_sha256(
            before_surfaces=before["surfaces"],
            after_surfaces=after["surfaces"],
            before_domains=before_domains,
            after_domains=after_domains,
            retained_responsibilities=proof["retained_responsibilities"],
            release_rationale=proof["release_rationale"],
            released_file_proofs=[],
            fixed_evidence_ref=proof["fixed_evidence_ref"],
        )
        return before, after

    def test_schema_three_stays_compatible_and_schema_four_is_strict(self):
        self.assertEqual([], preflight.validate_index(index()))
        future = index()
        future["schema_version"] = 4
        future["capabilities"] = copy.deepcopy(preflight.SAFE_CUSTODY_CAPABILITIES)
        self.assertEqual([], preflight.validate_index(future))
        future["capabilities"]["registry_schema"] = 1
        self.assertTrue(any("capabilities" in item for item in preflight.validate_index(future)))

    def test_exact_monotonic_release_and_freeze_link_pass(self):
        before, after = self._transition()
        self.assertEqual([], preflight.validate_claim(after))
        self.assertEqual(
            [],
            preflight.validate_scope_release_transition(
                before, after, registry=self._registry(after)
            ),
        )

    def test_release_rejects_stale_proof_expansion_and_fixed_control_removal(self):
        before, after = self._transition()
        stale = copy.deepcopy(after)
        stale["scope_release"]["prior_claim_sha256"] = "0" * 64
        self.assertTrue(any(
            "prior_claim_sha256" in item
            for item in preflight.validate_scope_release_transition(before, stale)
        ))
        expanded = copy.deepcopy(after)
        expanded["domains"] = ["product:other"]
        self.assertTrue(any(
            "expands or moves" in item
            for item in preflight.validate_scope_release_transition(before, expanded)
        ))
        removed_control = copy.deepcopy(after)
        removed_control["surfaces"].remove(preflight.claim_relative_path(before["package"]))
        self.assertTrue(any(
            "fixed claim" in item
            for item in preflight.validate_scope_release_transition(before, removed_control)
        ))

    def test_domain_change_rejects_permutation_without_path_reduction(self):
        before, after = self._domain_only_transition(
            ["product:alpha", "product:beta"],
            ["product:beta", "product:alpha"],
        )
        errors = preflight.validate_scope_release_transition(before, after)
        self.assertTrue(any("strictly reduce semantic authority" in item for item in errors), errors)

    def test_domain_change_rejects_redundant_descendant_without_path_reduction(self):
        before, after = self._domain_only_transition(
            ["product:example"],
            ["product:example", "product:example:child"],
        )
        errors = preflight.validate_scope_release_transition(before, after)
        self.assertTrue(any("strictly reduce semantic authority" in item for item in errors), errors)

    def test_domain_change_accepts_strict_semantic_narrowing(self):
        cases = (
            (["product:example"], ["product:example:child"]),
            (["product:alpha", "product:beta"], ["product:alpha"]),
        )
        for before_domains, after_domains in cases:
            with self.subTest(before=before_domains, after=after_domains):
                before, after = self._domain_only_transition(
                    before_domains, after_domains
                )
                self.assertEqual(
                    [], preflight.validate_scope_release_transition(before, after)
                )

    def test_release_proof_rejects_type_confusion_and_unknown_fields(self):
        before, after = self._transition()
        after["scope_release"]["released_surfaces"] = "src/released.py"
        after["scope_release"]["unexpected"] = True
        errors = preflight.validate_scope_release_transition(before, after)
        self.assertTrue(any("exact safe_custody_v1 field set" in item for item in errors))
        self.assertTrue(any("released_surfaces" in item for item in errors))

    def test_released_file_git_proof_recomputes_and_rejects_candidate_escape(self):
        def run_git(repo, *arguments):
            result = subprocess.run(
                ["git", *arguments], cwd=repo, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            return result.stdout.strip()

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            run_git(repo, "init", "--initial-branch=main")
            run_git(repo, "config", "user.email", "tests@peerslate.invalid")
            run_git(repo, "config", "user.name", "PeerSlate Tests")
            (repo / "src").mkdir()
            (repo / "src" / "released.py").write_text("released\n", encoding="utf-8")
            (repo / "src" / "retained.py").write_text("base\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "base")
            run_git(repo, "checkout", "-b", "work/2026-09-13-safe-custody-test")
            (repo / "src" / "retained.py").write_text("candidate\n", encoding="utf-8")
            run_git(repo, "add", "src/retained.py")
            run_git(repo, "commit", "-m", "candidate retained work")
            checkpoint = run_git(repo, "rev-parse", "HEAD")
            run_git(repo, "checkout", "main")
            (repo / "main.txt").write_text("main\n", encoding="utf-8")
            run_git(repo, "add", "main.txt")
            run_git(repo, "commit", "-m", "advance main")
            prepared_main = run_git(repo, "rev-parse", "HEAD")
            run_git(repo, "checkout", "work/2026-09-13-safe-custody-test")

            before, after = self._transition()
            proof = after["scope_release"]
            proof["checkpoint_sha"] = checkpoint
            proof["prepared_from_main"] = prepared_main
            proof["released_file_proofs"] = preflight.build_scope_release_file_proofs(
                root=repo,
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                checkpoint_sha=checkpoint,
                prepared_from_main=prepared_main,
                accepted_introductions=[],
            )
            proof["reduction_sha256"] = preflight.scope_reduction_sha256(
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                before_domains=before["domains"],
                after_domains=after["domains"],
                retained_responsibilities=proof["retained_responsibilities"],
                release_rationale=proof["release_rationale"],
                released_file_proofs=proof["released_file_proofs"],
                fixed_evidence_ref=proof["fixed_evidence_ref"],
            )
            self.assertEqual(
                [], preflight.validate_scope_release_transition(before, after, root=repo)
            )

            (repo / "escape.py").write_text("unclaimed\n", encoding="utf-8")
            run_git(repo, "add", "escape.py")
            run_git(repo, "commit", "-m", "unclaimed candidate escape")
            escaped_checkpoint = run_git(repo, "rev-parse", "HEAD")
            proof["checkpoint_sha"] = escaped_checkpoint
            proof["released_file_proofs"] = preflight.build_scope_release_file_proofs(
                root=repo,
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                checkpoint_sha=escaped_checkpoint,
                prepared_from_main=prepared_main,
                accepted_introductions=[],
            )
            proof["reduction_sha256"] = preflight.scope_reduction_sha256(
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                before_domains=before["domains"],
                after_domains=after["domains"],
                retained_responsibilities=proof["retained_responsibilities"],
                release_rationale=proof["release_rationale"],
                released_file_proofs=proof["released_file_proofs"],
                fixed_evidence_ref=proof["fixed_evidence_ref"],
            )
            errors = preflight.validate_scope_release_transition(before, after, root=repo)
            self.assertTrue(any("escapes retained surfaces" in item for item in errors), errors)

            run_git(repo, "checkout", "main")
            (repo / "src" / "released.py").write_text("changed on main\n", encoding="utf-8")
            run_git(repo, "add", "src/released.py")
            run_git(repo, "commit", "-m", "change released path on main")
            changed_main = run_git(repo, "rev-parse", "HEAD")
            with self.assertRaisesRegex(preflight.PreflightError, "differs between"):
                preflight.build_scope_release_file_proofs(
                    root=repo,
                    before_surfaces=before["surfaces"],
                    after_surfaces=after["surfaces"],
                    checkpoint_sha=escaped_checkpoint,
                    prepared_from_main=changed_main,
                    accepted_introductions=[],
                )

    def test_released_file_accepts_exact_reviewed_squash_introduction(self):
        def run_git(repo, *arguments):
            result = subprocess.run(
                ["git", *arguments], cwd=repo, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            return result.stdout.strip()

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            run_git(repo, "init", "--initial-branch=main")
            run_git(repo, "config", "user.email", "tests@peerslate.invalid")
            run_git(repo, "config", "user.name", "PeerSlate Tests")
            intro_package = "PS-INTRODUCER-001"
            intro_claim_path = repo / preflight.claim_relative_path(intro_package)
            intro_receipt_path = repo / preflight.receipt_relative_path(intro_package)
            intro_evidence_path = repo / preflight.evidence_relative_path(intro_package)
            intro_claim_path.parent.mkdir(parents=True)
            intro_receipt_path.parent.mkdir(parents=True)
            intro_evidence_path.parent.mkdir(parents=True)
            intro_claim_path.write_text(
                json.dumps({
                    "package": intro_package,
                    "writer_ref": "task:introducer",
                    "review_requirement": "independent",
                }) + "\n",
                encoding="utf-8",
            )
            intro_evidence_path.write_text("review evidence\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "released.py").write_text("old\n", encoding="utf-8")
            (repo / "src" / "retained.py").write_text("base\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "base")
            base = run_git(repo, "rev-parse", "HEAD")

            run_git(repo, "checkout", "-b", "reviewed-candidate")
            (repo / "src" / "released.py").write_text("reviewed\n", encoding="utf-8")
            run_git(repo, "add", "src/released.py")
            run_git(repo, "commit", "-m", "reviewed candidate")
            candidate = run_git(repo, "rev-parse", "HEAD")
            intro_receipt_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "package": intro_package,
                    "candidate_sha": candidate,
                    "review_type": "independent",
                    "reviewer_ref": "task:independent-reviewer",
                    "result": "pass",
                    "reviewed_at": "2026-09-13T00:00:00Z",
                    "findings": [],
                    "evidence_ref": preflight.evidence_relative_path(intro_package),
                }) + "\n",
                encoding="utf-8",
            )
            run_git(repo, "add", preflight.receipt_relative_path(intro_package))
            run_git(repo, "commit", "-m", "record exact review")
            reviewed_tip = run_git(repo, "rev-parse", "HEAD")

            run_git(repo, "checkout", "main")
            run_git(
                repo,
                "checkout",
                reviewed_tip,
                "--",
                "src/released.py",
                preflight.receipt_relative_path(intro_package),
            )
            run_git(repo, "commit", "-m", "squash accepted candidate")
            accepted_main = run_git(repo, "rev-parse", "HEAD")

            run_git(repo, "checkout", "-b", "work/2026-09-13-release", base)
            (repo / "src" / "released.py").write_text("reviewed\n", encoding="utf-8")
            (repo / "src" / "retained.py").write_text("candidate\n", encoding="utf-8")
            run_git(repo, "add", "src")
            run_git(repo, "commit", "-m", "matching branch bytes")
            checkpoint = run_git(repo, "rev-parse", "HEAD")

            before, after = self._transition()
            proof = after["scope_release"]
            introduction = {
                "path": "src/released.py",
                "package": intro_package,
                "candidate_sha": candidate,
                "merged_sha": accepted_main,
                "receipt_ref": preflight.receipt_relative_path(intro_package),
            }
            proof["checkpoint_sha"] = checkpoint
            proof["prepared_from_main"] = accepted_main
            proof["released_file_proofs"] = preflight.build_scope_release_file_proofs(
                root=repo,
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                checkpoint_sha=checkpoint,
                prepared_from_main=accepted_main,
                accepted_introductions=[introduction],
            )
            proof["reduction_sha256"] = preflight.scope_reduction_sha256(
                before_surfaces=before["surfaces"],
                after_surfaces=after["surfaces"],
                before_domains=before["domains"],
                after_domains=after["domains"],
                retained_responsibilities=proof["retained_responsibilities"],
                release_rationale=proof["release_rationale"],
                released_file_proofs=proof["released_file_proofs"],
                fixed_evidence_ref=proof["fixed_evidence_ref"],
            )
            self.assertEqual(
                [], preflight.validate_scope_release_transition(before, after, root=repo)
            )

    def test_prechange_delivery_client_refuses_schema_four(self):
        def run_git(cwd, *arguments):
            result = subprocess.run(
                ["git", *arguments], cwd=cwd, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            return result.stdout.strip()

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = base / "repo"
            remote = base / "origin.git"
            repo.mkdir()
            run_git(base, "init", "--bare", str(remote))
            run_git(repo, "init", "--initial-branch=main")
            run_git(repo, "config", "user.email", "tests@peerslate.invalid")
            run_git(repo, "config", "user.name", "PeerSlate Tests")
            (repo / "scripts").mkdir()
            governance = repo / "docs" / "governance"
            (governance / "lane_claims").mkdir(parents=True)
            old_delivery = run_git(
                ROOT,
                "show",
                f"{PRE_SAFE_CUSTODY_REF}:{COMPAT_FIXTURE['clients']['delivery']['path']}",
            )
            old_lifecycle = run_git(
                ROOT,
                "show",
                f"{PRE_SAFE_CUSTODY_REF}:{COMPAT_FIXTURE['clients']['lifecycle']['path']}",
            )
            (repo / "scripts" / "delivery_preflight.py").write_text(
                old_delivery + "\n", encoding="utf-8"
            )
            (repo / "scripts" / "worktree_lifecycle.py").write_text(
                old_lifecycle + "\n", encoding="utf-8"
            )
            future = index()
            future["schema_version"] = COMPAT_FIXTURE["clients"]["delivery"]["future_schema"]
            future["capabilities"] = copy.deepcopy(preflight.SAFE_CUSTODY_CAPABILITIES)
            (governance / "CURRENT_LANES.json").write_text(
                json.dumps(future, indent=2) + "\n", encoding="utf-8"
            )
            candidate_claim = claim()
            candidate_claim.pop("_relative_path")
            (governance / "lane_claims" / "PS-EXAMPLE-001.json").write_text(
                json.dumps(candidate_claim, indent=2) + "\n", encoding="utf-8"
            )
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "schema four fixture")
            run_git(repo, "remote", "add", "origin", str(remote))
            run_git(repo, "push", "-u", "origin", "main")
            run_git(repo, "checkout", "-b", candidate_claim["branch"])
            before = run_git(repo, "status", "--porcelain=v1")
            result = subprocess.run(
                [
                    sys.executable, "-B", str(repo / "scripts" / "delivery_preflight.py"),
                    "--repo", str(repo), "--package", "PS-EXAMPLE-001",
                    "--intent", "write", "--fetch", "--require-clean",
                    "--task-ref", candidate_claim["writer_ref"],
                ],
                cwd=repo, text=True, encoding="utf-8", stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(2, result.returncode, payload)
            self.assertTrue(any(
                COMPAT_FIXTURE["clients"]["delivery"]["expected_error"] in item
                for item in payload["errors"]
            ), payload["errors"])
            self.assertEqual(before, run_git(repo, "status", "--porcelain=v1"))


class ScopeReleaseCloseGitTests(unittest.TestCase):
    def run_git(self, repo, *arguments):
        result = subprocess.run(
            ["git", *arguments], cwd=repo, text=True, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        return result.stdout.strip()

    def make_history(self, repo, *, receipt_candidate=None, wrong_blob=False):
        self.run_git(repo, "init", "--initial-branch=main")
        self.run_git(repo, "config", "user.email", "tests@peerslate.invalid")
        self.run_git(repo, "config", "user.name", "PeerSlate Tests")
        before, after = SafeCustodyClaimTests()._transition()
        package = before["package"]
        claim_path = preflight.claim_relative_path(package)
        receipt_path = preflight.receipt_relative_path(package)
        evidence_path = preflight.evidence_relative_path(package)

        def write_claim(value):
            (repo / claim_path).write_text(
                json.dumps({key: item for key, item in value.items()
                            if key != "_relative_path"}, indent=2) + "\n",
                encoding="utf-8",
            )

        (repo / claim_path).parent.mkdir(parents=True)
        (repo / evidence_path).parent.mkdir(parents=True)
        (repo / receipt_path).parent.mkdir(parents=True)
        (repo / "src").mkdir()
        write_claim(before)
        (repo / evidence_path).write_text("Review evidence\n", encoding="utf-8")
        (repo / "src/released.py").write_text("old\n", encoding="utf-8")
        (repo / "src/retained.py").write_text("old\n", encoding="utf-8")
        self.run_git(repo, "add", ".")
        self.run_git(repo, "commit", "-m", "base claim and product")

        self.run_git(repo, "checkout", "-b", before["branch"])
        (repo / "src/released.py").write_text("reviewed\n", encoding="utf-8")
        (repo / "src/retained.py").write_text("reviewed\n", encoding="utf-8")
        self.run_git(repo, "add", "src")
        self.run_git(repo, "commit", "-m", "reviewed product candidate")
        candidate = self.run_git(repo, "rev-parse", "HEAD")

        self.run_git(repo, "checkout", "main")
        self.run_git(repo, "checkout", candidate, "--", "src/released.py", "src/retained.py")
        (repo / receipt_path).write_text(
            json.dumps(receipt(
                candidate_sha=receipt_candidate or candidate,
                evidence_ref=evidence_path,
            ), indent=2) + "\n", encoding="utf-8",
        )
        self.run_git(repo, "add", ".")
        self.run_git(repo, "commit", "-m", "accept reviewed product")
        merged = self.run_git(repo, "rev-parse", "HEAD")

        proof = after["scope_release"]
        proof["checkpoint_sha"] = candidate
        proof["prepared_from_main"] = merged
        proof["released_file_proofs"] = preflight.build_scope_release_file_proofs(
            root=repo,
            before_surfaces=before["surfaces"],
            after_surfaces=after["surfaces"],
            checkpoint_sha=candidate,
            prepared_from_main=merged,
            accepted_introductions=[{
                "path": "src/released.py",
                "package": package,
                "candidate_sha": candidate,
                "merged_sha": merged,
                "receipt_ref": receipt_path,
            }],
        )
        if wrong_blob:
            proof["released_file_proofs"][0]["checkpoint_blob"] = "0" * 40
        proof["reduction_sha256"] = preflight.scope_reduction_sha256(
            before_surfaces=before["surfaces"],
            after_surfaces=after["surfaces"],
            before_domains=before["domains"],
            after_domains=after["domains"],
            retained_responsibilities=proof["retained_responsibilities"],
            release_rationale=proof["release_rationale"],
            released_file_proofs=proof["released_file_proofs"],
            fixed_evidence_ref=proof["fixed_evidence_ref"],
        )
        write_claim(after)
        self.run_git(repo, "add", claim_path)
        self.run_git(repo, "commit", "-m", "accept partial scope release")
        self.run_git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        return before, after, candidate, merged, claim_path

    def test_close_accepts_only_exact_reviewed_released_path(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            before, after, candidate, merged, claim_path = self.make_history(repo)
            candidate_paths = ("src/released.py", "src/retained.py")
            allowed, errors = preflight._close_released_candidate_paths(
                repo, after, candidate, merged, candidate_paths
            )
            self.assertEqual([], errors)
            self.assertEqual({"src/released.py"}, allowed)
            self.assertEqual(
                [], [path for path in preflight._scope_errors(
                    candidate_paths, after["surfaces"]
                ) if path not in allowed],
            )
            closed = copy.deepcopy(after)
            closed.update(state="closed", merged_sha=merged,
                          closed_at="2026-09-20T00:00:00Z")
            self.assertEqual([], preflight.validate_claim(closed))
            self.assertTrue(any("scope_release" in error for error in
                                preflight.validate_claim({**after, "state": "paused",
                                                          "checkpoint_sha": candidate})))
            transition_errors = []
            preflight._require_control_delta(
                root=repo, claim=closed,
                facts=SimpleNamespace(branch_paths=(claim_path,)),
                allowed_fields={"state", "merged_sha", "closed_at"},
                errors=transition_errors,
            )
            self.assertEqual([], transition_errors)

            unrelated = ("src/released.py", "src/unrelated.py")
            allowed, errors = preflight._close_released_candidate_paths(
                repo, after, candidate, merged, unrelated
            )
            self.assertEqual([], errors)
            self.assertEqual(
                ["src/unrelated.py"],
                [path for path in preflight._scope_errors(
                    unrelated, after["surfaces"]
                ) if path not in allowed],
            )

    def test_close_rejects_changed_or_ambiguous_release_and_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            before, after, candidate, merged, claim_path = self.make_history(repo)
            for reviewed, accepted in (("f" * 40, merged), (candidate, "e" * 40)):
                with self.subTest(reviewed=reviewed, accepted=accepted):
                    allowed, errors = preflight._close_released_candidate_paths(
                        repo, after, reviewed, accepted, ("src/released.py",)
                    )
                    self.assertEqual(set(), allowed)
                    self.assertTrue(any("candidate, merge, and receipt" in error
                                        for error in errors), errors)

            changed = copy.deepcopy(after)
            changed["scope_release"]["release_rationale"] = "Changed after acceptance"
            allowed, errors = preflight._close_released_candidate_paths(
                repo, changed, candidate, merged, ("src/released.py",)
            )
            self.assertEqual(set(), allowed)
            self.assertTrue(any("one exact accepted main proof introduction" in error
                                for error in errors), errors)
            closed = copy.deepcopy(changed)
            closed.update(state="closed", merged_sha=merged,
                          closed_at="2026-09-20T00:00:00Z")
            transition_errors = []
            preflight._require_control_delta(
                root=repo, claim=closed,
                facts=SimpleNamespace(branch_paths=(claim_path,)),
                allowed_fields={"state", "merged_sha", "closed_at"},
                errors=transition_errors,
            )
            self.assertTrue(any("outside" in error for error in transition_errors))

            (repo / claim_path).write_text(
                json.dumps({key: item for key, item in before.items()
                            if key != "_relative_path"}, indent=2) + "\n",
                encoding="utf-8",
            )
            self.run_git(repo, "add", claim_path)
            self.run_git(repo, "commit", "-m", "restore prior claim")
            (repo / claim_path).write_text(
                json.dumps({key: item for key, item in after.items()
                            if key != "_relative_path"}, indent=2) + "\n",
                encoding="utf-8",
            )
            self.run_git(repo, "add", claim_path)
            self.run_git(repo, "commit", "-m", "repeat release proof")
            self.run_git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            allowed, errors = preflight._close_released_candidate_paths(
                repo, after, candidate, merged, ("src/released.py",)
            )
            self.assertEqual(set(), allowed)
            self.assertTrue(any("one exact accepted main proof introduction" in error
                                for error in errors), errors)

    def test_close_rejects_forged_review_and_git_blob(self):
        for change in ("receipt", "blob"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                _, after, candidate, merged, _ = self.make_history(
                    repo,
                    receipt_candidate="f" * 40 if change == "receipt" else None,
                    wrong_blob=change == "blob",
                )
                allowed, errors = preflight._close_released_candidate_paths(
                    repo, after, candidate, merged, ("src/released.py",)
                )
                self.assertEqual(set(), allowed)
                self.assertTrue(any("accepted introduction" in error or
                                    "released file proofs do not match exact Git objects" in error
                                    for error in errors), errors)


class ConcurrencyTests(unittest.TestCase):
    def test_disjoint_writers_have_no_numeric_cap(self):
        claims = {
            value["package"].casefold(): value
            for value in (
                claim(package=f"PS-PACKAGE-{number:03d}", number=number)
                for number in range(1, 51)
            )
        }
        self.assertEqual([], preflight.validate_claim_set(claims))

    def test_reviewer_consumes_no_writer_claim(self):
        claims = {"ps-example-001": claim()}
        self.assertEqual([], preflight.validate_claim_set(claims))
        reviewer = claim(package="PS-REVIEW-001", number=2, assignment="review_only")
        errors = preflight.validate_claim_set({**claims, "ps-review-001": reviewer})
        self.assertTrue(any("claim-free" in error for error in errors))

    def test_duplicate_branch_fails(self):
        first = claim(package="PS-FIRST-001", number=1)
        second = claim(
            package="PS-SECOND-001",
            number=2,
            branch=first["branch"],
        )
        errors = preflight.validate_claim_set(
            {"ps-first-001": first, "ps-second-001": second}
        )
        self.assertTrue(any("branch collision" in error for error in errors))

    def test_path_collision_fails(self):
        first = claim(package="PS-FIRST-001", number=1, surfaces=["src/shared"])
        second = claim(
            package="PS-SECOND-001",
            number=2,
            surfaces=["src/shared/child"],
        )
        errors = preflight.validate_claim_set(
            {"ps-first-001": first, "ps-second-001": second}
        )
        self.assertTrue(any("path collision" in error for error in errors))

    def test_domain_collision_fails(self):
        first = claim(package="PS-FIRST-001", number=1, domains=["shared:auth"])
        second = claim(
            package="PS-SECOND-001",
            number=2,
            domains=["shared:auth:callback"],
        )
        errors = preflight.validate_claim_set(
            {"ps-first-001": first, "ps-second-001": second}
        )
        self.assertTrue(any("domain collision" in error for error in errors))

    def test_read_reports_active_path_and_domain_collisions_without_authorizing(self):
        first = claim(
            package="PS-FIRST-001",
            number=1,
            surfaces=claimed_surfaces("PS-FIRST-001", "src/shared"),
            domains=["shared:auth"],
        )
        second = claim(
            package="PS-SECOND-001",
            number=2,
            surfaces=claimed_surfaces("PS-SECOND-001", "src/shared/child"),
            domains=["shared:auth:callback"],
        )
        claims = {"ps-first-001": first, "ps-second-001": second}

        errors, warnings, diagnostics = preflight.validate_claim_set_admission(
            intent="read",
            candidate_claims=claims,
        )

        self.assertEqual([], errors)
        self.assertEqual(2, len(warnings))
        self.assertTrue(all("non-authorizing" in warning for warning in warnings))
        self.assertTrue(
            any("path collision" in item for item in diagnostics["claim_collisions"])
        )
        self.assertTrue(
            any("domain collision" in item for item in diagnostics["claim_collisions"])
        )

    def test_read_keeps_non_scope_claim_defects_fatal(self):
        first = claim(package="PS-FIRST-001", number=1)
        second = claim(
            package="PS-SECOND-001",
            number=2,
            branch=first["branch"],
        )

        errors, _, _ = preflight.validate_claim_set_admission(
            intent="read",
            candidate_claims={"ps-first-001": first, "ps-second-001": second},
        )

        self.assertTrue(any("branch collision" in error for error in errors))

    def test_collision_prefix_package_labels_cannot_spoof_read_warnings(self):
        for package_label in ("path collision", "domain collision"):
            malformed = claim(package=package_label)
            malformed["_relative_path"] = "docs/governance/lane_claims/wrong.json"

            errors, warnings, diagnostics = (
                preflight.validate_claim_set_admission(
                    intent="read",
                    candidate_claims={package_label: malformed},
                )
            )

            with self.subTest(package_label=package_label):
                self.assertTrue(
                    any("claim package must be" in error for error in errors), errors
                )
                self.assertTrue(
                    any("claim path must be" in error for error in errors), errors
                )
                self.assertEqual([], warnings)
                self.assertNotIn("claim_collisions", diagnostics)

    def test_every_mutating_intent_keeps_a_candidate_collision_fatal(self):
        first = claim(
            package="PS-FIRST-001",
            number=1,
            surfaces=claimed_surfaces("PS-FIRST-001", "src/shared"),
            domains=["shared:auth"],
        )
        second = claim(
            package="PS-SECOND-001",
            number=2,
            surfaces=claimed_surfaces("PS-SECOND-001", "src/shared/child"),
            domains=["shared:auth:callback"],
        )
        claims = {"ps-first-001": first, "ps-second-001": second}

        for intent in sorted(preflight.MUTATING_INTENTS):
            with self.subTest(intent=intent):
                errors, _, diagnostics = preflight.validate_claim_set_admission(
                    intent=intent,
                    candidate_claims=claims,
                    authority_claims=claims,
                )
                self.assertTrue(
                    any("path collision" in error for error in errors), errors
                )
                self.assertTrue(
                    any("domain collision" in error for error in errors), errors
                )
                self.assertIn("candidate_claim_collisions", diagnostics)

    def test_exact_candidate_state_may_remove_authority_scope_collisions(self):
        first = claim(
            package="PS-FIRST-001",
            number=1,
            surfaces=claimed_surfaces("PS-FIRST-001", "src/shared"),
            domains=["shared:auth"],
        )
        second = claim(
            package="PS-SECOND-001",
            number=2,
            surfaces=claimed_surfaces("PS-SECOND-001", "src/shared/child"),
            domains=["shared:auth:callback"],
        )
        authority = {"ps-first-001": first, "ps-second-001": second}
        paused = copy.deepcopy(first)
        paused["state"] = "paused"
        paused["checkpoint_sha"] = HEAD
        candidate = {"ps-first-001": paused, "ps-second-001": second}

        errors, warnings, diagnostics = preflight.validate_claim_set_admission(
            intent="pause",
            candidate_claims=candidate,
            authority_claims=authority,
        )

        self.assertEqual([], errors)
        self.assertEqual(2, len(warnings))
        self.assertTrue(
            all("removed by exact candidate" in warning for warning in warnings)
        )
        self.assertIn("authority_claim_collisions", diagnostics)

        incomplete_candidate = {"ps-first-001": paused}
        errors, _, _ = preflight.validate_claim_set_admission(
            intent="pause",
            candidate_claims=incomplete_candidate,
            authority_claims=authority,
        )
        self.assertTrue(any("path collision" in error for error in errors))
        self.assertTrue(any("domain collision" in error for error in errors))

    def test_paused_product_scope_and_closed_branch_do_not_block_new_work(self):
        paused = claim(
            package="PS-PAUSED-001",
            number=1,
            state="paused",
            checkpoint_sha=HEAD,
            domains=["product:reusable"],
        )
        active = claim(
            package="PS-ACTIVE-001",
            number=2,
            surfaces=claimed_surfaces("PS-ACTIVE-001", "src/package-1"),
            domains=["product:reusable"],
        )
        closed = claim(
            package="PS-CLOSED-001",
            number=3,
            state="closed",
            branch=active["branch"],
            merged_sha=MAIN,
            closed_at="2026-08-23T00:00:00Z",
        )
        errors = preflight.validate_claim_set(
            {
                "ps-paused-001": paused,
                "ps-closed-001": closed,
                "ps-active-001": active,
            }
        )
        self.assertEqual([], errors)

    def test_paused_branch_remains_reserved(self):
        paused = claim(
            package="PS-PAUSED-001",
            number=1,
            state="paused",
            checkpoint_sha=HEAD,
        )
        active = claim(
            package="PS-ACTIVE-001",
            number=2,
            branch=paused["branch"],
        )
        errors = preflight.validate_claim_set(
            {"ps-paused-001": paused, "ps-active-001": active}
        )
        self.assertTrue(any("branch collision" in error for error in errors))

    def test_legacy_bootstrap_maps_every_active_lane_without_scope_widening(self):
        writer_id = "11111111-1111-4111-8111-111111111111"
        superseded_id = "22222222-2222-4222-8222-222222222222"
        value = claim(writer_ref=f"task:{writer_id}")
        legacy_index = {
            "schema_version": 2,
            "active_lanes": [{
                "package": value["package"],
                "branch": value["branch"],
                "delivery_path": value["delivery_path"],
                "outcome": "Implement and merge accepted work.",
                "exclusions": [],
                "writer": (
                    f"Sole implementation writer is task {writer_id}. "
                    f"Previously named session {superseded_id} is superseded "
                    "and must not write."
                ),
                "writable_surfaces": ["src/package-1/"],
                "exclusive_domains": value["domains"],
            }],
        }
        self.assertEqual(
            [],
            preflight.validate_legacy_bootstrap(
                index(), {"ps-example-001": value}, legacy_index, MAIN
            ),
        )
        widened = copy.deepcopy(value)
        widened["surfaces"] = ["src"]
        errors = preflight.validate_legacy_bootstrap(
            index(), {"ps-example-001": widened}, legacy_index, MAIN
        )
        self.assertTrue(any("widens" in error for error in errors))
        impostor = copy.deepcopy(value)
        impostor["writer_ref"] = "agent:implementation"
        errors = preflight.validate_legacy_bootstrap(
            index(), {"ps-example-001": impostor}, legacy_index, MAIN
        )
        self.assertTrue(any("sole current writer" in error for error in errors))

        withheld_index = copy.deepcopy(legacy_index)
        withheld_lane = withheld_index["active_lanes"][0]
        withheld_lane["outcome"] = "Implement the candidate and stop before merge."
        withheld_lane["exclusions"] = ["no implementation-candidate merge"]
        narrowed = copy.deepcopy(value)
        narrowed["repository_authority"] = "write_only"
        self.assertEqual(
            [],
            preflight.validate_legacy_bootstrap(
                index(), {"ps-example-001": narrowed}, withheld_index, MAIN
            ),
        )
        errors = preflight.validate_legacy_bootstrap(
            index(), {"ps-example-001": value}, withheld_index, MAIN
        )
        self.assertTrue(any("preserve the legacy boundary" in error for error in errors))
        superseded = copy.deepcopy(value)
        superseded["writer_ref"] = f"session:{superseded_id}"
        errors = preflight.validate_legacy_bootstrap(
            index(), {"ps-example-001": superseded}, legacy_index, MAIN
        )
        self.assertTrue(any("sole current writer" in error for error in errors))


class ReviewReceiptTests(unittest.TestCase):
    def test_exact_independent_pass_receipt_is_valid(self):
        self.assertEqual([], preflight.validate_receipt(receipt(), claim()))

    def test_writer_cannot_self_issue_independent_receipt(self):
        value = claim(writer_ref="agent:same")
        errors = preflight.validate_receipt(
            receipt(reviewer_ref="agent:same"), value
        )
        self.assertTrue(any("differ" in error for error in errors))

    def test_routine_and_bounded_self_review_receipts_bind_to_the_writer(self):
        for delivery_path in ("Routine", "Bounded"):
            with self.subTest(delivery_path=delivery_path):
                value = claim(
                    delivery_path=delivery_path,
                    review_requirement="self",
                )
                self.assertEqual(
                    [],
                    preflight.validate_receipt(
                        receipt(
                            review_type="self",
                            reviewer_ref=value["writer_ref"],
                        ),
                        value,
                    ),
                )
                errors = preflight.validate_receipt(
                    receipt(
                        review_type="self",
                        reviewer_ref="agent:not-the-writer",
                    ),
                    value,
                )
                self.assertTrue(any("equal the writer_ref" in error for error in errors))

    def test_moved_sha_and_nonpass_review_fail(self):
        errors = preflight.validate_receipt(
            receipt(candidate_sha="short", result="reject"), claim()
        )
        self.assertTrue(any("candidate_sha" in error for error in errors))
        self.assertTrue(any("result must be pass" in error for error in errors))

    def test_unresolved_findings_fail_closed(self):
        errors = preflight.validate_receipt(
            receipt(findings=[{"severity": "P1", "status": "open"}]), claim()
        )
        self.assertTrue(any("unresolved" in error for error in errors))

    def test_impossible_review_timestamp_is_rejected(self):
        errors = preflight.validate_receipt(
            receipt(reviewed_at="2026-99-99T99:99:99Z"), claim()
        )
        self.assertTrue(any("UTC timestamp" in error for error in errors))


class LocalWorktreeRegistryTests(unittest.TestCase):
    def write_registry(self, common, records, **overrides):
        registry = {
            "schema_version": 1,
            "repository_common_dir": str(common),
            "repository_primary_root": str(common.parent / "repo"),
            "initialized_at": "2026-08-23T00:00:00Z",
            "initialized_by": "task:registry-init",
            "managed_root": str(common.parent / "managed"),
            "evidence_root": str(common.parent / "evidence"),
            "policy_activation_worktree_count": len(records),
            "worktrees": records,
            "pending": None,
            "evidence_allocations": [],
            "owner_reassignment_preparations": [],
        }
        registry.update(overrides)
        path = common / preflight.WORKTREE_REGISTRY_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(registry), encoding="utf-8")
        return path

    def record(self, path, **overrides):
        value = {
            "path": str(path),
            "kind": "durable",
            "state": "active",
            "package": "PS-EXAMPLE-001",
            "branch": "work/2026-08-23-example-1",
            "head": HEAD,
            "task_ref": "task:writer-1",
            "lease": None,
            "created_at": "2026-08-23T00:00:00Z",
            "updated_at": "2026-08-23T00:00:00Z",
        }
        value.update(overrides)
        return value

    def owner_reassignment_claim(self):
        successor = "work/2026-08-27-example-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        value = claim(
            writer_ref="agent:replacement-writer",
            branch=successor,
            handoff={
                "type": "owner_reassignment",
                "from_ref": "session:prior-writer",
                "to_ref": "agent:replacement-writer",
                "from_branch": "work/2026-08-25-example-old",
                "to_branch": successor,
                "checkpoint_sha": HEAD,
                "owner_authorization_ref": owner_ref,
            },
        )
        return value, owner_ref

    def owner_reassignment_registry_record(self, path, control_branch):
        return self.record(
            path,
            kind="control_singleton",
            package="PS-EXAMPLE-001",
            branch=control_branch,
            task_ref="agent:replacement-writer",
            lease={
                "task_ref": "agent:replacement-writer",
                "purpose": "control",
                "package": "PS-EXAMPLE-001",
                "acquired_at": "2026-08-27T00:00:00Z",
            },
        )

    def owner_reassignment_preparation(self, value, control_branch, source_snapshot):
        handoff = value["handoff"]
        preparation = {
            "schema_version": 1,
            "status": "completed",
            "package": value["package"],
            "owner_authorization_ref": handoff["owner_authorization_ref"],
            "from_ref": handoff["from_ref"],
            "to_ref": handoff["to_ref"],
            "from_branch": handoff["from_branch"],
            "to_branch": handoff["to_branch"],
            "checkpoint_sha": handoff["checkpoint_sha"],
            "control_branch": control_branch,
            "prepared_from_main": MAIN,
            "new_branch_response": (
                f"*\t{HEAD}:refs/heads/{handoff['to_branch']}\t[new branch]"
            ),
            "source_snapshot": source_snapshot,
            "prepared_at": "2026-08-27T00:00:00Z",
        }
        preparation["preparation_id"] = lifecycle_registry._preparation_digest(
            preparation
        )
        return preparation

    def check(
        self,
        common,
        worktree,
        request=None,
        value=None,
        repo_facts=None,
        *,
        simulate_ci=False,
    ):
        request = request or args("write")
        value = value or claim()
        repo_facts = repo_facts or facts(repository=str(worktree))
        environment = {key: "" for key in preflight.CI_ENVIRONMENT_KEYS}
        environment.update(
            CODEX_THREAD_ID="",
            PEERSLATE_CALLER_REF="",
            PEERSLATE_CALLER_CONTEXT="",
        )
        if simulate_ci:
            environment["TF_BUILD"] = "True"
        with patch.dict(os.environ, environment), patch.object(
            preflight, "_git_common_dir", return_value=common
        ):
            return preflight.evaluate_local_worktree_context(
                root=worktree,
                args=request,
                claim=value,
                facts=repo_facts,
            )

    def test_missing_registry_is_advisory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            context, errors, warnings = self.check(base / "common", base / "worktree")
            self.assertEqual([], errors)
            self.assertEqual("not_initialized", context["registry"])
            self.assertTrue(any("not initialized" in item for item in warnings))

    def test_ci_skips_machine_local_enforcement(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            context, errors, warnings = self.check(
                base / "common", base / "worktree", simulate_ci=True
            )
            self.assertEqual([], errors)
            self.assertEqual("ci_skipped", context["registry"])
            self.assertTrue(any("CI" in item for item in warnings))

    def test_owner_reassignment_rejects_ci_and_uninitialized_registry_bypass(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-example"
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo_facts = facts(
                repository=str(base / "managed" / "_control"),
                branch=control_branch,
            )
            context, errors, warnings = self.check(
                base / "common",
                base / "managed" / "_control",
                request=request,
                value=value,
                repo_facts=repo_facts,
                simulate_ci=True,
            )
            self.assertEqual("ci_skipped", context["registry"])
            self.assertTrue(any("cannot bypass" in item for item in errors))
            self.assertEqual([], warnings)

            context, errors, warnings = self.check(
                base / "common",
                base / "managed" / "_control",
                request=request,
                value=value,
                repo_facts=repo_facts,
            )
            self.assertEqual("not_initialized", context["registry"])
            self.assertTrue(any("initialized registry" in item for item in errors))
            self.assertEqual([], warnings)

    def test_owner_reassignment_requires_no_lock_pending_or_missing_preparation(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-example"
        )
        for state in (
            "missing_preparation",
            "missing_pending_field",
            "pending",
            "locked",
            "duplicate_control",
            "duplicate_control_retired",
        ):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                common = base / "common"
                current = base / "managed" / "_control"
                overrides = {}
                if state == "pending":
                    overrides["pending"] = {
                        "operation": "owner_reassignment_branch_create"
                    }
                records = [
                    self.owner_reassignment_registry_record(
                        current, control_branch
                    )
                ]
                if state in {"duplicate_control", "duplicate_control_retired"}:
                    duplicate_control = self.owner_reassignment_registry_record(
                        base / "managed" / "other-control", control_branch
                    )
                    if state == "duplicate_control_retired":
                        duplicate_control["state"] = "retired"
                        duplicate_control["lease"] = None
                    records.append(duplicate_control)
                registry_path = self.write_registry(
                    common,
                    records,
                    **overrides,
                )
                if state == "missing_pending_field":
                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    registry.pop("pending")
                    registry_path.write_text(json.dumps(registry), encoding="utf-8")
                if state == "locked":
                    (
                        common
                        / preflight.WORKTREE_REGISTRY_REL.parent
                        / preflight.WORKTREE_LOCK_DIRECTORY_NAME
                    ).mkdir()
                repo_facts = facts(repository=str(current), branch=control_branch)
                context, errors, _ = self.check(
                    common,
                    current,
                    request=request,
                    value=value,
                    repo_facts=repo_facts,
                )
                self.assertFalse(
                    context["owner_reassignment_preparation_valid"]
                )
                expected = {
                    "missing_preparation": "completed preparation tuple",
                    "missing_pending_field": "pending registry ambiguity",
                    "pending": "pending registry ambiguity",
                    "locked": "active registry lock",
                    "duplicate_control": "one exact deterministic active",
                    "duplicate_control_retired": "one exact deterministic active",
                }[state]
                self.assertTrue(any(expected in item for item in errors), errors)

    def test_owner_reassignment_preparation_is_exact_mutation_bound_and_single_use(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-example"
        )
        source_snapshot = {
            "local_branch_sha": HEAD,
            "worktrees": [],
            "durable_records": [],
        }
        variants = (
            "valid",
            "mismatched_tuple",
            "source_mutated",
            "source_raced",
            "namespace_mutated",
            "duplicate_completed",
            "replayed_tuple",
            "consumed",
        )
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                common = base / "common"
                current = base / "managed" / "_control"
                preparation = self.owner_reassignment_preparation(
                    value, control_branch, source_snapshot
                )
                if variant == "mismatched_tuple":
                    preparation["checkpoint_sha"] = "f" * 40
                    preparation["preparation_id"] = lifecycle_registry._preparation_digest(
                        preparation
                    )
                elif variant == "consumed":
                    preparation["status"] = "consumed"
                    preparation["consumed_at"] = "2026-08-27T00:01:00Z"
                    preparation["consumed_on_main"] = MAIN
                preparations = [preparation]
                if variant == "duplicate_completed":
                    preparations.append(copy.deepcopy(preparation))
                elif variant == "replayed_tuple":
                    consumed = copy.deepcopy(preparation)
                    consumed["status"] = "consumed"
                    consumed["consumed_at"] = "2026-08-27T00:01:00Z"
                    consumed["consumed_on_main"] = MAIN
                    preparations.append(consumed)
                self.write_registry(
                    common,
                    [
                        self.owner_reassignment_registry_record(
                            current, control_branch
                        )
                    ],
                    owner_reassignment_preparations=preparations,
                )
                repo_facts = facts(repository=str(current), branch=control_branch)
                current_snapshot = (
                    {
                        **source_snapshot,
                        "local_branch_sha": "e" * 40,
                    }
                    if variant == "source_mutated"
                    else source_snapshot
                )
                snapshot_patch = (
                    patch.object(
                        preflight,
                        "_live_preparation_source_snapshot",
                        side_effect=[
                            source_snapshot,
                            {
                                **source_snapshot,
                                "local_branch_sha": "e" * 40,
                            },
                        ],
                    )
                    if variant == "source_raced"
                    else patch.object(
                        preflight,
                        "_live_preparation_source_snapshot",
                        return_value=current_snapshot,
                    )
                )
                namespace_errors = (
                    ["owner-reassignment successor namespace changed after preparation"]
                    if variant == "namespace_mutated"
                    else []
                )
                with snapshot_patch, patch.object(
                    preflight,
                    "_owner_reassignment_namespace_errors",
                    return_value=namespace_errors,
                ):
                    context, errors, _ = self.check(
                        common,
                        current,
                        request=request,
                        value=value,
                        repo_facts=repo_facts,
                    )
                if variant == "valid":
                    self.assertEqual([], errors)
                    self.assertTrue(
                        context["owner_reassignment_preparation_valid"]
                    )
                else:
                    self.assertFalse(
                        context["owner_reassignment_preparation_valid"]
                    )
                    expected = (
                        "source snapshot no longer matches"
                        if variant in {"source_mutated", "source_raced"}
                        else "successor namespace changed"
                        if variant == "namespace_mutated"
                        else "preparation history is invalid"
                        if variant
                        in {
                            "mismatched_tuple",
                            "duplicate_completed",
                            "replayed_tuple",
                            "consumed",
                        }
                        else "completed preparation tuple"
                    )
                    self.assertTrue(any(expected in item for item in errors), errors)

    def test_owner_reassignment_continuity_is_descendant_and_claim_blob_bound(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        prepared_control = (
            "work/2026-08-27-delivery-owner-reassignment-prepared"
        )
        fresh_control = (
            "work/2026-08-27-delivery-owner-reassignment-continuity"
        )
        descendant_main = "f" * 40
        source_snapshot = {
            "local_branch_sha": HEAD,
            "worktrees": [],
            "durable_records": [],
        }
        cases = {
            "valid": (fresh_control, descendant_main, 0, True, "same"),
            "equal_main": (fresh_control, MAIN, 0, True, "same"),
            "non_descendant": (fresh_control, descendant_main, 0, False, "same"),
            "reused_control": (prepared_control, descendant_main, 0, True, "same"),
            "changed_claim": (fresh_control, descendant_main, 0, True, "changed"),
            "missing_claim": (fresh_control, descendant_main, 0, True, "missing"),
            "stale_control": (fresh_control, descendant_main, 1, True, "same"),
        }
        for case, (
            current_control,
            current_main,
            behind,
            is_descendant,
            claim_state,
        ) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                common = base / "common"
                current = base / "managed" / "_control"
                preparation = self.owner_reassignment_preparation(
                    value, prepared_control, source_snapshot
                )
                self.write_registry(
                    common,
                    [
                        self.owner_reassignment_registry_record(
                            current, current_control
                        )
                    ],
                    owner_reassignment_preparations=[preparation],
                )
                repo_facts = facts(
                    repository=str(current),
                    branch=current_control,
                    origin_main=current_main,
                    behind=behind,
                )

                def claim_blob(_root, commit, _package):
                    if claim_state == "missing":
                        raise preflight.PreflightError("claim missing")
                    if claim_state == "changed" and commit == current_main:
                        return CANDIDATE
                    return HEAD

                with patch.object(
                    preflight,
                    "_live_preparation_source_snapshot",
                    return_value=source_snapshot,
                ), patch.object(
                    preflight,
                    "_owner_reassignment_namespace_errors",
                    return_value=[],
                ), patch.object(
                    preflight, "_is_ancestor", return_value=is_descendant
                ), patch.object(
                    preflight, "_claim_blob_at_commit", side_effect=claim_blob
                ):
                    context, errors, _ = self.check(
                        common,
                        current,
                        request=request,
                        value=value,
                        repo_facts=repo_facts,
                    )
                if case == "valid":
                    self.assertEqual([], errors)
                    self.assertTrue(
                        context["owner_reassignment_preparation_valid"]
                    )
                else:
                    self.assertFalse(
                        context["owner_reassignment_preparation_valid"]
                    )
                    expected = {
                        "equal_main": "strict descendant",
                        "non_descendant": "strict descendant",
                        "reused_control": "distinct fresh control branch",
                        "changed_claim": "byte-identical authoritative target claim",
                        "missing_claim": "continuity claim proof failed",
                        "stale_control": "control branch from current main",
                    }[case]
                    self.assertTrue(any(expected in item for item in errors), errors)

    def test_registry_preparation_field_defaults_for_existing_schema_one_state(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "managed" / "package"
            path = self.write_registry(common, [self.record(current)])
            registry = json.loads(path.read_text(encoding="utf-8"))
            registry.pop("owner_reassignment_preparations")
            path.write_text(json.dumps(registry), encoding="utf-8")
            context, errors, _ = self.check(common, current)
            self.assertEqual([], errors)
            self.assertTrue(context["enforced"])

    def test_owner_reassignment_preflight_reuses_strict_history_validator(self):
        value, _owner_ref = self.owner_reassignment_claim()
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-schema-reuse"
        )
        source_snapshot = {
            "local_branch_sha": HEAD,
            "worktrees": [],
            "durable_records": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            control = self.owner_reassignment_registry_record(
                base / "managed" / "_control", control_branch
            )
            baseline = self.owner_reassignment_preparation(
                value, control_branch, source_snapshot
            )

            def consumed(preparation, *, receiver=True):
                preparation["status"] = "consumed"
                preparation["consumed_at"] = "2026-08-27T00:01:00Z"
                preparation["consumed_on_main"] = MAIN
                records = [control]
                if receiver:
                    receiver_record = self.record(
                        base / "managed" / "receiver",
                        package=value["package"],
                        branch=value["handoff"]["to_branch"],
                        head=HEAD,
                        task_ref=value["handoff"]["to_ref"],
                        owner_reassignment_preparation_id=preparation[
                            "preparation_id"
                        ],
                    )
                    records.append(receiver_record)
                return records

            cases = {}
            poisoned = copy.deepcopy(baseline)
            poisoned["schema_version"] = True
            poisoned["preparation_id"] = lifecycle_registry._preparation_digest(poisoned)
            cases["boolean_schema"] = (poisoned, [control])

            poisoned = copy.deepcopy(baseline)
            poisoned["from_ref"] = {"spoof": "session:prior-writer"}
            poisoned["preparation_id"] = lifecycle_registry._preparation_digest(poisoned)
            cases["object_reference"] = (poisoned, [control])

            poisoned = copy.deepcopy(baseline)
            poisoned["checkpoint_sha"] = int("1" * 40)
            poisoned["preparation_id"] = lifecycle_registry._preparation_digest(poisoned)
            cases["numeric_sha"] = (poisoned, [control])

            poisoned = copy.deepcopy(baseline)
            poisoned["source_snapshot"]["local_branch_sha"] = int("2" * 40)
            poisoned["preparation_id"] = lifecycle_registry._preparation_digest(poisoned)
            cases["invalid_snapshot"] = (poisoned, [control])

            poisoned = copy.deepcopy(baseline)
            poisoned["prepared_at"] = "2026-08-27 00:00:00"
            poisoned["preparation_id"] = lifecycle_registry._preparation_digest(poisoned)
            cases["invalid_timestamp"] = (poisoned, [control])

            poisoned = copy.deepcopy(baseline)
            poisoned_records = consumed(poisoned)
            poisoned["consumed_on_main"] = True
            cases["poisoned_consumed_history"] = (poisoned, poisoned_records)

            poisoned = copy.deepcopy(baseline)
            orphan_records = consumed(poisoned, receiver=False)
            cases["orphan_consumed"] = (poisoned, orphan_records)

            for name, (preparation, records) in cases.items():
                with self.subTest(name=name):
                    registry = {
                        "schema_version": 1,
                        "worktrees": copy.deepcopy(records),
                        "pending": None,
                        "owner_reassignment_preparations": [preparation],
                    }
                    errors = preflight._owner_reassignment_preparation_errors(
                        root=base,
                        registry=registry,
                        claim=value,
                        facts=facts(
                            repository=str(base / "managed" / "_control"),
                            branch=control_branch,
                        ),
                    )
                    self.assertTrue(
                        any("preparation history is invalid" in item for item in errors),
                        errors,
                    )

    def test_owner_reassignment_local_check_rejects_type_confused_control_lease(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-lease-type"
        )
        source_snapshot = {
            "local_branch_sha": HEAD,
            "worktrees": [],
            "durable_records": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "managed" / "_control"
            control = self.owner_reassignment_registry_record(
                current, control_branch
            )
            control["lease"]["acquired_at"] = {"spoof": "2026-08-27T00:00:00Z"}
            self.write_registry(
                common,
                [control],
                owner_reassignment_preparations=[
                    self.owner_reassignment_preparation(
                        value, control_branch, source_snapshot
                    )
                ],
            )
            with patch.object(
                preflight,
                "_live_preparation_source_snapshot",
                return_value=source_snapshot,
            ), patch.object(
                preflight,
                "_owner_reassignment_namespace_errors",
                return_value=[],
            ):
                context, errors, _ = self.check(
                    common,
                    current,
                    request=request,
                    value=value,
                    repo_facts=facts(
                        repository=str(current), branch=control_branch
                    ),
                )
            self.assertFalse(context["owner_reassignment_preparation_valid"])
            self.assertTrue(
                any("control acquired_at" in item for item in errors), errors
            )

    def test_owner_reassignment_final_snapshot_rejects_lease_lock_pending_race(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-final-race"
        )
        source_snapshot = {
            "local_branch_sha": HEAD,
            "worktrees": [],
            "durable_records": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "managed" / "_control"
            registry_path = self.write_registry(
                common,
                [
                    self.owner_reassignment_registry_record(
                        current, control_branch
                    )
                ],
                owner_reassignment_preparations=[
                    self.owner_reassignment_preparation(
                        value, control_branch, source_snapshot
                    )
                ],
            )
            source_proof_calls = 0

            def racing_source_proof(_root, _registry, _handoff):
                nonlocal source_proof_calls
                source_proof_calls += 1
                if source_proof_calls == 2:
                    live_registry = json.loads(
                        registry_path.read_text(encoding="utf-8")
                    )
                    live_registry["worktrees"][0]["lease"] = None
                    live_registry["pending"] = {
                        "operation": "create",
                        "path": str(base / "racing-path"),
                    }
                    registry_path.write_text(
                        json.dumps(live_registry), encoding="utf-8"
                    )
                    (
                        registry_path.parent
                        / preflight.WORKTREE_LOCK_DIRECTORY_NAME
                    ).mkdir()
                return source_snapshot

            repo_facts = facts(repository=str(current), branch=control_branch)
            with patch.object(
                preflight,
                "_live_preparation_source_snapshot",
                side_effect=racing_source_proof,
            ), patch.object(
                preflight,
                "_owner_reassignment_namespace_errors",
                return_value=[],
            ):
                context, errors, _ = self.check(
                    common,
                    current,
                    request=request,
                    value=value,
                    repo_facts=repo_facts,
                )
            self.assertEqual(source_proof_calls, 2, errors)
            self.assertFalse(context["owner_reassignment_preparation_valid"])
            self.assertTrue(
                any("lock appeared during final live proof" in item for item in errors),
                errors,
            )

    def test_owner_reassignment_final_mutex_catches_post_proof_prelock_race(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-prelock-race"
        )
        source_snapshot = {
            "local_branch_sha": HEAD,
            "worktrees": [],
            "durable_records": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "managed" / "_control"
            registry_path = self.write_registry(
                common,
                [self.owner_reassignment_registry_record(current, control_branch)],
                owner_reassignment_preparations=[
                    self.owner_reassignment_preparation(
                        value, control_branch, source_snapshot
                    )
                ],
            )
            lock_path = (
                registry_path.parent / preflight.WORKTREE_LOCK_DIRECTORY_NAME
            )
            real_mkdir = os.mkdir
            race_injected = False

            def racing_mkdir(path, *arguments, **keywords):
                nonlocal race_injected
                if Path(path) == lock_path:
                    live_registry = json.loads(
                        registry_path.read_text(encoding="utf-8")
                    )
                    live_registry["worktrees"][0]["lease"] = None
                    live_registry["pending"] = {
                        "operation": "create",
                        "path": str(base / "racing-path"),
                    }
                    registry_path.write_text(
                        json.dumps(live_registry), encoding="utf-8"
                    )
                    race_injected = True
                return real_mkdir(path, *arguments, **keywords)

            repo_facts = facts(repository=str(current), branch=control_branch)
            with patch.object(
                preflight,
                "_live_preparation_source_snapshot",
                return_value=source_snapshot,
            ), patch.object(
                preflight,
                "_owner_reassignment_namespace_errors",
                return_value=[],
            ), patch.object(
                preflight.os,
                "mkdir",
                side_effect=racing_mkdir,
            ):
                context, errors, _ = self.check(
                    common,
                    current,
                    request=request,
                    value=value,
                    repo_facts=repo_facts,
                )
            self.assertTrue(race_injected)
            self.assertFalse(context["owner_reassignment_preparation_valid"])
            self.assertTrue(
                any("registry changed during final live proof" in item for item in errors),
                errors,
            )
            self.assertTrue(any("pending ambiguity" in item for item in errors), errors)
            self.assertTrue(
                any("lost its exact active leased" in item for item in errors), errors
            )
            self.assertFalse(lock_path.exists())

    def test_real_git_owner_reassignment_final_snapshot_rejects_registry_race(self):
        value, owner_ref = self.owner_reassignment_claim()
        request = args(
            "owner-reassignment",
            task_ref=value["writer_ref"],
            owner_authorization_ref=owner_ref,
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-real-git-race"
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "origin.git"
            repo = base / "repo"
            repo.mkdir()
            preflight._git(base, "init", "--bare", str(remote))
            preflight._git(repo, "init", "--initial-branch=main")
            preflight._git(repo, "config", "user.email", "tests@peerslate.invalid")
            preflight._git(repo, "config", "user.name", "PeerSlate Tests")
            claim_path = (
                repo
                / "docs"
                / "governance"
                / "lane_claims"
                / f"{value['package']}.json"
            )
            claim_path.parent.mkdir(parents=True)
            claim_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "package": value["package"],
                        "state": "active",
                        "writer_ref": value["handoff"]["from_ref"],
                        "branch": value["handoff"]["from_branch"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            preflight._git(repo, "add", ".")
            preflight._git(repo, "commit", "-m", "initialize real Git race fixture")
            preflight._git(repo, "remote", "add", "origin", str(remote))
            preflight._git(repo, "push", "-u", "origin", "main")
            main_sha = preflight._git(repo, "rev-parse", "HEAD")
            old_branch = value["handoff"]["from_branch"]
            successor = value["handoff"]["to_branch"]
            preflight._git(repo, "branch", old_branch, main_sha)
            preflight._git(
                repo, "push", "origin", f"{old_branch}:refs/heads/{old_branch}"
            )
            preflight._git(
                repo, "push", "origin", f"{main_sha}:refs/heads/{successor}"
            )
            control_path = base / "managed" / "_control"
            control_path.parent.mkdir()
            preflight._git(
                repo,
                "worktree",
                "add",
                "-b",
                control_branch,
                str(control_path),
                "origin/main",
            )
            common = preflight._git_common_dir(control_path)

            value["handoff"]["checkpoint_sha"] = main_sha
            source_snapshot = {
                "local_branch_sha": main_sha,
                "worktrees": [],
                "durable_records": [],
            }
            record = self.owner_reassignment_registry_record(
                control_path, control_branch
            )
            record["head"] = main_sha
            preparation = self.owner_reassignment_preparation(
                value, control_branch, source_snapshot
            )
            preparation.update(
                {
                    "checkpoint_sha": main_sha,
                    "prepared_from_main": main_sha,
                    "new_branch_response": (
                        f"*\t{main_sha}:refs/heads/{successor}\t[new branch]"
                    ),
                }
            )
            preparation["preparation_id"] = lifecycle_registry._preparation_digest(
                preparation
            )
            registry_path = self.write_registry(
                common,
                [record],
                repository_primary_root=str(repo),
                managed_root=str(control_path.parent),
                evidence_root=str(base / "evidence"),
                owner_reassignment_preparations=[preparation],
            )
            repo_facts = facts(
                repository=str(control_path),
                branch=control_branch,
                head=main_sha,
                origin_main=main_sha,
            )
            real_source_proof = preflight._live_preparation_source_snapshot
            source_proof_calls = 0

            def racing_source_proof(root, registry, handoff):
                nonlocal source_proof_calls
                snapshot = real_source_proof(root, registry, handoff)
                source_proof_calls += 1
                if source_proof_calls == 2:
                    live_registry = json.loads(
                        registry_path.read_text(encoding="utf-8")
                    )
                    live_registry["worktrees"][0]["lease"] = None
                    live_registry["pending"] = {
                        "operation": "create",
                        "path": str(base / "racing-path"),
                    }
                    registry_path.write_text(
                        json.dumps(live_registry), encoding="utf-8"
                    )
                    (
                        registry_path.parent
                        / preflight.WORKTREE_LOCK_DIRECTORY_NAME
                    ).mkdir()
                return snapshot

            environment = {key: "" for key in preflight.CI_ENVIRONMENT_KEYS}
            with patch.dict(os.environ, environment), patch.object(
                preflight,
                "_live_preparation_source_snapshot",
                side_effect=racing_source_proof,
            ):
                context, errors, _ = preflight.evaluate_local_worktree_context(
                    root=control_path,
                    args=request,
                    claim=value,
                    facts=repo_facts,
                )
            self.assertEqual(source_proof_calls, 2, errors)
            self.assertFalse(context["owner_reassignment_preparation_valid"])
            self.assertTrue(
                any("lock appeared during final live proof" in item for item in errors),
                errors,
            )

    def test_initialized_registry_rejects_unregistered_current_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            self.write_registry(common, [])
            context, errors, _ = self.check(common, base / "new-worktree")
            self.assertEqual("unregistered", context["registry"])
            self.assertTrue(any("ad hoc worktree" in item for item in errors))

    def test_exact_durable_context_passes_and_unrelated_legacy_only_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "managed" / "package"
            records = [
                self.record(current),
                self.record(
                    base / "legacy",
                    kind="grandfathered_observation",
                    package=None,
                    branch=None,
                    head=None,
                    task_ref=None,
                ),
            ]
            self.write_registry(common, records)
            context, errors, warnings = self.check(common, current)
            self.assertEqual([], errors)
            self.assertTrue(context["enforced"])
            self.assertTrue(any("grandfathered" in item for item in warnings))

    def test_grandfathered_or_wrong_task_current_workspace_cannot_mutate(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "legacy"
            self.write_registry(
                common,
                [
                    self.record(
                        current,
                        kind="grandfathered_observation",
                        package=None,
                        branch="work/2026-08-23-example-1",
                        task_ref=None,
                    )
                ],
            )
            _, errors, _ = self.check(common, current)
            self.assertTrue(any("durable" in item for item in errors))

            self.write_registry(common, [self.record(current)])
            _, errors, _ = self.check(
                common, current, request=args("write", task_ref="task:other")
            )
            self.assertTrue(any("writer_ref" in item for item in errors))

    def test_control_transition_requires_exact_singleton_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            current = base / "managed" / "_control"
            control_branch = "work/2026-08-23-delivery-activation-example"
            lease = {
                "task_ref": "task:writer-1",
                "purpose": "control",
                "package": "PS-EXAMPLE-001",
                "acquired_at": "2026-08-23T00:00:00Z",
            }
            self.write_registry(
                common,
                [
                    self.record(
                        current,
                        kind="control_singleton",
                        branch=control_branch,
                        lease=lease,
                    )
                ],
            )
            request = args("extend-surfaces", task_ref="task:writer-1")
            repo_facts = facts(repository=str(current), branch=control_branch)
            context, errors, _ = self.check(
                common, current, request=request, repo_facts=repo_facts
            )
            self.assertEqual([], errors)
            self.assertEqual("control_singleton", context["current_kind"])

            request = args("extend-surfaces", task_ref="task:other")
            _, errors, _ = self.check(
                common, current, request=request, repo_facts=repo_facts
            )
            self.assertTrue(any("another task" in item for item in errors))

    def test_corrupt_initialized_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common = base / "common"
            path = common / preflight.WORKTREE_REGISTRY_REL
            path.parent.mkdir(parents=True)
            path.write_text("{broken", encoding="utf-8")
            context, errors, _ = self.check(common, base / "worktree")
            self.assertEqual("invalid", context["registry"])
            self.assertTrue(any("valid JSON" in item for item in errors))


class EvaluationTests(unittest.TestCase):
    def run_evaluate(
        self, request, value, repo_facts, *, origin_claims=None,
        origin_index=None, candidate_claims=None, **extra_patches
    ):
        if origin_claims is None:
            origin_claims = {value["package"].casefold(): copy.deepcopy(value)}
        if candidate_claims is None:
            candidate_claims = {value["package"].casefold(): value}
        patches = [
            patch.object(preflight, "load_index", return_value=index()),
            patch.object(
                preflight, "load_index_at_ref", return_value=origin_index or index()
            ),
            patch.object(
                preflight,
                "load_claims",
                return_value=candidate_claims,
            ),
            patch.object(preflight, "load_claims_at_ref", return_value=origin_claims),
            patch.object(preflight, "collect_repo_facts", return_value=repo_facts),
            patch.object(preflight, "_verify_legacy_snapshot"),
            patch.object(
                preflight,
                "evaluate_local_worktree_context",
                return_value=(
                    {
                        "registry": (
                            "initialized"
                            if request.intent == "owner-reassignment"
                            else "test_stub"
                        ),
                        "enforced": request.intent == "owner-reassignment",
                        "current_kind": (
                            "control_singleton"
                            if request.intent == "owner-reassignment"
                            else None
                        ),
                        "owner_reassignment_preparation_valid": (
                            request.intent == "owner-reassignment"
                        ),
                    },
                    [],
                    [],
                ),
            ),
        ]
        patches.extend(extra_patches.values())
        entered = [item.start() for item in patches]
        try:
            return preflight.evaluate(request, root=ROOT)
        finally:
            for item in reversed(patches):
                item.stop()

    def surface_extension_evaluation(
        self,
        *,
        before=None,
        after=None,
        request=None,
        repo_facts=None,
        origin_claims=None,
        candidate_claims=None,
        broad=False,
        registry_context=None,
        registry_errors=None,
    ):
        before = before or claim(
            surfaces=claimed_surfaces(
                "PS-EXAMPLE-001", "services/database_service.py"
            )
        )
        if after is None:
            after = copy.deepcopy(before)
            after["surfaces"].append("tests/test_database_service.py")
        request = request or args("extend-surfaces")
        repo_facts = repo_facts or facts(
            branch="work/2026-08-25-delivery-extend-surfaces-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )
        return self.run_evaluate(
            request,
            after,
            repo_facts,
            origin_claims=origin_claims
            or {before["package"].casefold(): before},
            candidate_claims=candidate_claims,
            origin_claim=patch.object(
                preflight, "_origin_claim", return_value=before
            ),
            broad=patch.object(
                preflight, "extension_surface_is_broad", return_value=broad
            ),
            local_registry=patch.object(
                preflight,
                "evaluate_local_worktree_context",
                return_value=(
                    registry_context
                    or {
                        "registry": "initialized",
                        "enforced": True,
                        "current_kind": "control_singleton",
                    },
                    registry_errors or [],
                    [],
                ),
            ),
        )

    def test_local_registry_context_is_reported_and_enforced(self):
        value = claim()
        context = {"registry": "initialized", "current_kind": "durable"}
        payload, errors, warnings = self.run_evaluate(
            args("write"),
            value,
            facts(),
            local_registry=patch.object(
                preflight,
                "evaluate_local_worktree_context",
                return_value=(context, ["registry blocker"], ["legacy warning"]),
            ),
        )
        self.assertEqual(context, payload["worktree_registry"])
        self.assertIn("registry blocker", errors)
        self.assertIn("legacy warning", warnings)

    def test_read_with_caller_context_validates_local_registry(self):
        value = claim()
        context = {"registry": "initialized", "current_kind": "durable"}
        local_registry = patch.object(
            preflight,
            "evaluate_local_worktree_context",
            return_value=(context, ["registry blocker"], ["legacy warning"]),
        )
        with patch.dict(os.environ, {"PEERSLATE_CALLER_CONTEXT": ""}):
            payload, errors, warnings = self.run_evaluate(
                args("read", caller_context="a" * 32),
                value,
                facts(),
                local_registry=local_registry,
            )

        self.assertEqual(context, payload["worktree_registry"])
        self.assertIn("registry blocker", errors)
        self.assertIn("legacy warning", warnings)

    def test_write_allows_disjoint_main_movement(self):
        value = claim()
        repo_facts = facts(main_paths=("docs/unrelated.md",))
        _, errors, _ = self.run_evaluate(args("write"), value, repo_facts)
        self.assertEqual([], errors)

    def test_azure_origin_is_exact_not_a_substring(self):
        value = claim()
        _, errors, _ = self.run_evaluate(
            args("write"), value,
            facts(origin_url="https://evil.example/dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"),
        )
        self.assertTrue(any("authoritative Azure" in error for error in errors))

    def test_write_blocks_current_main_path_collision(self):
        value = claim()
        repo_facts = facts(main_paths=("src/package-1/other.py",))
        _, errors, _ = self.run_evaluate(args("write"), value, repo_facts)
        self.assertTrue(any("current main moved" in error for error in errors))

    def test_write_blocks_out_of_scope_change(self):
        value = claim()
        repo_facts = facts(branch_paths=("outside/file.py",))
        _, errors, _ = self.run_evaluate(args("write"), value, repo_facts)
        self.assertTrue(any("outside the claim" in error for error in errors))

    def test_writer_cannot_expand_its_branch_claim(self):
        authoritative = claim()
        widened = claim(surfaces=["src"])
        _, errors, _ = self.run_evaluate(
            args("write"), widened, facts(branch_paths=("src/escalated.py",)),
            origin_claims={"ps-example-001": authoritative},
        )
        self.assertTrue(any("authoritative origin/main" in error for error in errors))

    def test_stale_branch_cannot_ignore_new_origin_collision(self):
        value = claim()
        collision = claim(
            package="PS-COLLISION-001", number=2,
            surfaces=["src/package-1/child"], domains=["product:collision"],
        )
        _, errors, _ = self.run_evaluate(
            args("write"), value, facts(),
            origin_claims={"ps-example-001": value, "ps-collision-001": collision},
        )
        self.assertTrue(any("path collision" in error for error in errors))

    def test_review_only_claim_cannot_write(self):
        value = claim(assignment="review_only")
        _, errors, _ = self.run_evaluate(args("write"), value, facts())
        self.assertTrue(any("claim-free" in error for error in errors))

    def test_explicit_write_only_assignment_can_write_but_not_merge(self):
        value = claim(repository_authority="write_only")
        _, errors, _ = self.run_evaluate(args("write"), value, facts())
        self.assertEqual([], errors)
        _, errors, _ = self.merge_evaluation(value=value)
        self.assertTrue(any("through merge" in error for error in errors))

    def test_owner_reauthorizes_write_only_claim_then_self_reviewed_merge_passes(self):
        before = claim(
            delivery_path="Bounded",
            repository_authority="write_only",
            review_requirement="self",
        )
        after = claim(
            delivery_path="Bounded",
            repository_authority="through_merge",
            review_requirement="self",
            owner_outcome_ref="task:owner/turn:authorize-merge",
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-authorize-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )
        _, errors, _ = self.run_evaluate(
            args("authorize"),
            after,
            control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
        )
        self.assertEqual([], errors)
        self_receipt = receipt(
            review_type="self",
            reviewer_ref=after["writer_ref"],
        )
        _, errors, _ = self.merge_evaluation(
            value=after,
            review_receipt=self_receipt,
        )
        self.assertEqual([], errors)

    def test_authority_transition_requires_prior_narrowing_and_new_owner_reference(self):
        before = claim(repository_authority="through_merge")
        after = claim(
            repository_authority="through_merge",
            owner_outcome_ref=before["owner_outcome_ref"],
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-authorize-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )
        _, errors, _ = self.run_evaluate(
            args("authorize"),
            after,
            control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
        )
        self.assertTrue(any("write_only" in error for error in errors))
        self.assertTrue(any("new owner_outcome_ref" in error for error in errors))

    def test_surface_extension_appends_representative_exact_file(self):
        _, errors, _ = self.surface_extension_evaluation()
        self.assertEqual([], errors)

    def test_surface_extension_refuses_removal_replacement_reorder_or_other_field(self):
        before = claim(
            surfaces=claimed_surfaces(
                "PS-EXAMPLE-001", "services/database_service.py"
            )
        )
        variants = {}

        removed = copy.deepcopy(before)
        removed["surfaces"].pop()
        variants["removal"] = removed

        replaced = copy.deepcopy(before)
        replaced["surfaces"][-1] = "tests/test_database_service.py"
        variants["replacement"] = replaced

        reordered = copy.deepcopy(before)
        reordered["surfaces"][0], reordered["surfaces"][1] = (
            reordered["surfaces"][1],
            reordered["surfaces"][0],
        )
        variants["reorder"] = reordered

        for label, after in variants.items():
            with self.subTest(label=label):
                _, errors, _ = self.surface_extension_evaluation(
                    before=before, after=after
                )
                self.assertTrue(any("must append" in error for error in errors))

        other_field = copy.deepcopy(before)
        other_field["surfaces"].append("tests/test_database_service.py")
        other_field["outcome"] = "Quietly expanded outcome."
        _, errors, _ = self.surface_extension_evaluation(
            before=before, after=other_field
        )
        self.assertTrue(any("changed fields outside" in error for error in errors))

        deleted_null = copy.deepcopy(before)
        deleted_null["surfaces"].append("tests/test_database_service.py")
        deleted_null.pop("closed_at")
        _, errors, _ = self.surface_extension_evaluation(
            before=before, after=deleted_null
        )
        self.assertTrue(any("changed fields outside" in error for error in errors))

        unknown_null = copy.deepcopy(before)
        unknown_null["surfaces"].append("tests/test_database_service.py")
        unknown_null["unknown"] = None
        _, errors, _ = self.surface_extension_evaluation(
            before=before, after=unknown_null
        )
        self.assertTrue(any("changed fields outside" in error for error in errors))

    def test_surface_extension_refuses_wrong_context_inactive_stale_dirty_or_extra_path(self):
        before = claim(
            surfaces=claimed_surfaces(
                "PS-EXAMPLE-001", "services/database_service.py"
            )
        )
        after = copy.deepcopy(before)
        after["surfaces"].append("tests/test_database_service.py")
        claim_path = preflight.claim_relative_path(after["package"])

        cases = (
            (
                "wrong branch",
                args("extend-surfaces"),
                facts(branch="work/2026-08-25-example-1", branch_paths=(claim_path,)),
                "delivery-extend-surfaces",
            ),
            (
                "wrong task",
                args("extend-surfaces", task_ref="task:other"),
                facts(
                    branch="work/2026-08-25-delivery-extend-surfaces-example",
                    branch_paths=(claim_path,),
                ),
                "task context",
            ),
            (
                "stale main",
                args("extend-surfaces"),
                facts(
                    branch="work/2026-08-25-delivery-extend-surfaces-example",
                    branch_paths=(claim_path,),
                    behind=1,
                ),
                "current origin/main",
            ),
            (
                "dirty",
                args("extend-surfaces"),
                facts(
                    branch="work/2026-08-25-delivery-extend-surfaces-example",
                    branch_paths=(claim_path,),
                    clean=False,
                ),
                "not clean",
            ),
            (
                "unrelated path",
                args("extend-surfaces"),
                facts(
                    branch="work/2026-08-25-delivery-extend-surfaces-example",
                    branch_paths=(claim_path, "docs/unrelated.md"),
                ),
                "change only",
            ),
        )
        for label, request, repo_facts, expected in cases:
            with self.subTest(label=label):
                _, errors, _ = self.surface_extension_evaluation(
                    before=before,
                    after=after,
                    request=request,
                    repo_facts=repo_facts,
                )
                self.assertTrue(any(expected in error for error in errors), errors)

        paused_before = copy.deepcopy(before)
        paused_before["state"] = "paused"
        paused_before["checkpoint_sha"] = HEAD
        paused_after = copy.deepcopy(paused_before)
        paused_after["surfaces"].append("tests/test_database_service.py")
        _, errors, _ = self.surface_extension_evaluation(
            before=paused_before, after=paused_after
        )
        self.assertTrue(any("active origin claim" in error for error in errors))

        _, errors, _ = self.surface_extension_evaluation(
            before=before,
            after=after,
            request=args("extend-surfaces", package="PS-WRONG-001"),
        )
        self.assertTrue(any("no branch claim" in error for error in errors))

        _, errors, _ = self.surface_extension_evaluation(
            before=before,
            after=after,
            registry_context={
                "registry": "not_initialized",
                "enforced": False,
                "current_kind": None,
            },
        )
        self.assertTrue(any("proved leased _control" in error for error in errors))

    def test_surface_extension_refuses_malformed_duplicate_broad_and_control_paths(self):
        before = claim(
            surfaces=claimed_surfaces(
                "PS-EXAMPLE-001", "services/database_service.py"
            )
        )
        variants = (
            ("malformed", "tests\\test_database_service.py", False, "normalized"),
            ("non-string", 7, False, "path must be a string"),
            ("duplicate", before["surfaces"][0], False, "duplicate"),
            ("broad", "tests", True, "broad paths"),
            (
                "cross-package control",
                preflight.claim_relative_path("PS-OTHER-001"),
                False,
                "cross-package control path",
            ),
        )
        for label, addition, broad, expected in variants:
            after = copy.deepcopy(before)
            after["surfaces"].append(addition)
            with self.subTest(label=label):
                _, errors, _ = self.surface_extension_evaluation(
                    before=before, after=after, broad=broad
                )
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_surface_extension_refuses_overlaps_inside_the_target_claim(self):
        before = claim(
            surfaces=claimed_surfaces(
                "PS-EXAMPLE-001", "services/database_service.py"
            )
        )
        additions = (
            ["SERVICES/database_service.py"],
            ["services/database_service.py/child.py"],
            [
                "tests/test_database_service.py",
                "tests/test_database_service.py/child.py",
            ],
        )
        for appended in additions:
            after = copy.deepcopy(before)
            after["surfaces"].extend(appended)
            with self.subTest(appended=appended):
                _, errors, _ = self.surface_extension_evaluation(
                    before=before, after=after
                )
                self.assertTrue(
                    any("overlap the target claim" in error for error in errors),
                    errors,
                )

    def test_surface_extension_reruns_exact_parent_and_child_collisions_from_main(self):
        collision_paths = (
            "tests/test_database_service.py",
            "tests",
            "tests/test_database_service.py/case",
        )
        for collision_path in collision_paths:
            before = claim(
                surfaces=claimed_surfaces(
                    "PS-EXAMPLE-001", "services/database_service.py"
                )
            )
            after = copy.deepcopy(before)
            after["surfaces"].append("tests/test_database_service.py")
            other = claim(
                package="PS-OTHER-001",
                number=2,
                surfaces=claimed_surfaces("PS-OTHER-001", collision_path),
            )
            with self.subTest(collision_path=collision_path):
                _, errors, _ = self.surface_extension_evaluation(
                    before=before,
                    after=after,
                    origin_claims={
                        before["package"].casefold(): before,
                        other["package"].casefold(): other,
                    },
                    candidate_claims={before["package"].casefold(): after},
                )
                self.assertTrue(any("path collision" in error for error in errors), errors)

    def test_release_and_legacy_grant_are_not_repository_permissions(self):
        value = claim()
        for intent, phrase in (("release", "production"), ("grant", "retired")):
            with self.subTest(intent=intent):
                _, errors, _ = self.run_evaluate(args(intent), value, facts())
                self.assertTrue(any(phrase in error for error in errors))

    def test_activation_adds_one_claim_without_a_capacity_gate(self):
        value = claim(activated_from_main=MAIN)
        repo_facts = facts(
            branch="work/2026-08-23-delivery-activation-example",
            branch_paths=(preflight.claim_relative_path(value["package"]),),
        )
        _, errors, _ = self.run_evaluate(
            args("activate"), value, repo_facts, origin_claims={}
        )
        self.assertEqual([], errors)

    def test_disjoint_activation_cannot_ignore_an_existing_authority_collision(self):
        existing = claim(
            package="PS-EXISTING-001",
            number=2,
            surfaces=claimed_surfaces("PS-EXISTING-001", "src/shared"),
            domains=["product:shared"],
        )
        colliding = claim(
            package="PS-COLLIDING-001",
            number=3,
            surfaces=claimed_surfaces("PS-COLLIDING-001", "src/shared/child"),
            domains=["product:shared:child"],
        )
        new_claim = claim(activated_from_main=MAIN)
        repo_facts = facts(
            branch="work/2026-08-23-delivery-activation-example",
            branch_paths=(preflight.claim_relative_path(new_claim["package"]),),
        )
        authority = {
            "ps-existing-001": existing,
            "ps-colliding-001": colliding,
        }
        candidate = {**authority, "ps-example-001": new_claim}

        _, errors, _ = self.run_evaluate(
            args("activate"),
            new_claim,
            repo_facts,
            origin_claims=authority,
            candidate_claims=candidate,
        )

        self.assertTrue(any("path collision" in error for error in errors))
        self.assertTrue(any("domain collision" in error for error in errors))

    def test_activation_rejects_existing_claim_mutation(self):
        value = claim(activated_from_main=MAIN)
        before = copy.deepcopy(value)
        before["outcome"] = "Old outcome"
        repo_facts = facts(
            branch="work/2026-08-23-delivery-activation-example",
            branch_paths=(preflight.claim_relative_path(value["package"]),),
        )
        _, errors, _ = self.run_evaluate(
            args("activate"), value, repo_facts,
            origin_claims={value["package"].casefold(): before},
        )
        self.assertTrue(any("add exactly one" in error for error in errors))

    def test_activation_requires_fresh_active_lifecycle_state(self):
        repo_facts = facts(
            branch="work/2026-08-23-delivery-activation-example",
            branch_paths=(preflight.claim_relative_path("PS-EXAMPLE-001"),),
        )
        invalid = (
            claim(state="paused", checkpoint_sha=HEAD),
            claim(
                state="closed",
                merged_sha=MAIN,
                closed_at="2026-08-23T00:00:00Z",
            ),
            claim(handoff={"preseeded": True}),
        )
        for value in invalid:
            with self.subTest(state=value["state"], handoff=value["handoff"]):
                _, errors, _ = self.run_evaluate(
                    args("activate"), value, repo_facts, origin_claims={}
                )
                self.assertTrue(
                    any(
                        "fresh active claim" in error
                        or "preseed lifecycle history" in error
                        for error in errors
                    )
                )

    def test_transfer_binds_both_refs_and_remote_checkpoint(self):
        before = claim(writer_ref="task:writer-before")
        handoff = {
            "from_ref": "task:writer-before",
            "to_ref": "task:writer-after",
            "checkpoint_sha": HEAD,
            "relinquished": True,
        }
        after = claim(writer_ref="task:writer-after", handoff=handoff)
        control_facts = facts(
            branch="work/2026-08-23-delivery-transfer-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        _, errors, _ = self.run_evaluate(
            args("transfer"), after, control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        self.assertEqual([], errors)
        bad = copy.deepcopy(after)
        bad["handoff"]["checkpoint_sha"] = "f" * 40
        _, errors, _ = self.run_evaluate(
            args("transfer"), bad, control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        self.assertTrue(any("fetched branch tip" in error for error in errors))

    def test_owner_reassignment_binds_distinct_provenance_and_both_remote_branches(self):
        before = claim(
            writer_ref="session:prior-writer",
            branch="work/2026-08-25-example-old",
        )
        successor = "work/2026-08-27-example-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        handoff = {
            "type": "owner_reassignment",
            "from_ref": before["writer_ref"],
            "to_ref": "agent:replacement-writer",
            "from_branch": before["branch"],
            "to_branch": successor,
            "checkpoint_sha": HEAD,
            "owner_authorization_ref": owner_ref,
        }
        after = claim(
            writer_ref=handoff["to_ref"],
            branch=successor,
            handoff=handoff,
        )
        control_facts = facts(
            branch="work/2026-08-27-delivery-owner-reassignment-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )

        with patch.object(
            preflight, "_exact_fetch_origin_branch", return_value=HEAD
        ) as exact_fetch:
            _, errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=handoff["to_ref"],
                    owner_authorization_ref=owner_ref,
                ),
                after,
                control_facts,
                origin_claims={"ps-example-001": before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
            )
        self.assertEqual([], errors)
        self.assertEqual(
            [before["branch"], successor, before["branch"]],
            [call.args[1] for call in exact_fetch.call_args_list],
        )

        malformed = copy.deepcopy(after)
        malformed["handoff"]["relinquished"] = True
        self.assertTrue(
            any(
                "exact owner_reassignment" in error
                or "exact owner_reassignment shape" in error
                for error in preflight.validate_claim(malformed)
            )
        )

        widened = copy.deepcopy(after)
        widened["outcome"] = "Silently replace the governed outcome."
        with patch.object(
            preflight, "_exact_fetch_origin_branch", return_value=HEAD
        ):
            _, widened_errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=handoff["to_ref"],
                    owner_authorization_ref=owner_ref,
                ),
                widened,
                control_facts,
                origin_claims={"ps-example-001": before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
            )
        self.assertTrue(
            any("changed fields outside" in error for error in widened_errors)
        )

    def test_owner_reassignment_terminal_mutex_rejects_post_context_mutation(self):
        before = claim(
            writer_ref="session:prior-writer",
            branch="work/2026-08-25-terminal-old",
        )
        successor = "work/2026-08-27-terminal-recovery"
        owner_ref = "session:owner/decision:terminal-race"
        handoff = {
            "type": "owner_reassignment",
            "from_ref": before["writer_ref"],
            "to_ref": "agent:terminal-receiver",
            "from_branch": before["branch"],
            "to_branch": successor,
            "checkpoint_sha": HEAD,
            "owner_authorization_ref": owner_ref,
        }
        after = claim(
            writer_ref=handoff["to_ref"], branch=successor, handoff=handoff
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-terminal-race"
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            current = base / "managed" / "_control"
            registry_path = base / "common" / preflight.WORKTREE_REGISTRY_REL
            registry_path.parent.mkdir(parents=True)
            registry = {
                "schema_version": 1,
                "worktrees": [
                    {
                        "path": str(current),
                        "kind": "control_singleton",
                        "state": "active",
                        "package": after["package"],
                        "branch": control_branch,
                        "head": MAIN,
                        "task_ref": handoff["to_ref"],
                        "lease": {
                            "task_ref": handoff["to_ref"],
                            "purpose": "control",
                            "package": after["package"],
                            "acquired_at": "2026-08-27T00:00:00Z",
                        },
                    }
                ],
                "pending": None,
                "owner_reassignment_preparations": [],
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            registry_context = {
                "registry": "initialized",
                "enforced": True,
                "current_kind": "control_singleton",
                "path": str(registry_path),
                "owner_reassignment_preparation_valid": True,
                "_owner_reassignment_registry_snapshot": copy.deepcopy(registry),
            }
            mutation_injected = False

            def racing_fetch(_root, branch):
                nonlocal mutation_injected
                if not mutation_injected:
                    changed = json.loads(registry_path.read_text(encoding="utf-8"))
                    changed["worktrees"][0]["lease"] = None
                    registry_path.write_text(json.dumps(changed), encoding="utf-8")
                    mutation_injected = True
                return MAIN if branch == "main" else HEAD

            control_facts = facts(
                repository=str(current),
                branch=control_branch,
                branch_paths=(preflight.claim_relative_path(after["package"]),),
            )
            payload, errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=handoff["to_ref"],
                    owner_authorization_ref=owner_ref,
                ),
                after,
                control_facts,
                origin_claims={after["package"].casefold(): before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
                registry=patch.object(
                    preflight,
                    "evaluate_local_worktree_context",
                    return_value=(registry_context, [], []),
                ),
                preparation=patch.object(
                    preflight,
                    "_owner_reassignment_preparation_errors",
                    return_value=[],
                ),
                remote=patch.object(
                    preflight, "_exact_fetch_origin_branch", side_effect=racing_fetch
                ),
                remote_tuple=patch.object(
                    preflight,
                    "_remote_branch_tuple",
                    return_value={
                        "main": MAIN,
                        handoff["from_branch"]: HEAD,
                        handoff["to_branch"]: HEAD,
                    },
                ),
            )
            self.assertTrue(mutation_injected)
            self.assertFalse(
                payload["worktree_registry"][
                    "owner_reassignment_preparation_valid"
                ]
            )
            self.assertTrue(
                any("changed before terminal owner proof" in item for item in errors),
                errors,
            )
            self.assertFalse(
                (
                    registry_path.parent
                    / preflight.WORKTREE_LOCK_DIRECTORY_NAME
                ).exists()
            )

            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            final_registry_context = {
                "registry": "initialized",
                "enforced": True,
                "current_kind": "control_singleton",
                "path": str(registry_path),
                "owner_reassignment_preparation_valid": True,
                "_owner_reassignment_registry_snapshot": copy.deepcopy(registry),
            }
            changed_claim = copy.deepcopy(after)
            changed_claim["branch"] += "-raced"
            claim_read_count = 0

            def racing_branch_claims(_root=ROOT):
                nonlocal claim_read_count
                claim_read_count += 1
                selected = changed_claim if claim_read_count >= 3 else after
                return {after["package"].casefold(): selected}

            payload, errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=handoff["to_ref"],
                    owner_authorization_ref=owner_ref,
                ),
                after,
                control_facts,
                origin_claims={after["package"].casefold(): before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
                registry=patch.object(
                    preflight,
                    "evaluate_local_worktree_context",
                    return_value=(final_registry_context, [], []),
                ),
                preparation=patch.object(
                    preflight,
                    "_owner_reassignment_preparation_errors",
                    return_value=[],
                ),
                remote=patch.object(
                    preflight,
                    "_exact_fetch_origin_branch",
                    side_effect=lambda _root, branch: MAIN if branch == "main" else HEAD,
                ),
                branch_claims=patch.object(
                    preflight, "load_claims", side_effect=racing_branch_claims
                ),
                remote_tuple=patch.object(
                    preflight,
                    "_remote_branch_tuple",
                    return_value={
                        "main": MAIN,
                        handoff["from_branch"]: HEAD,
                        handoff["to_branch"]: HEAD,
                    },
                ),
            )
            self.assertGreaterEqual(claim_read_count, 3)
            self.assertFalse(
                payload["worktree_registry"][
                    "owner_reassignment_preparation_valid"
                ]
            )
            self.assertTrue(
                any("branch claim changed at terminal boundary" in item for item in errors),
                errors,
            )
            self.assertFalse(
                (
                    registry_path.parent
                    / preflight.WORKTREE_LOCK_DIRECTORY_NAME
                ).exists()
            )

            tuple_registry_context = {
                "registry": "initialized",
                "enforced": True,
                "current_kind": "control_singleton",
                "path": str(registry_path),
                "owner_reassignment_preparation_valid": True,
                "_owner_reassignment_registry_snapshot": copy.deepcopy(registry),
            }
            payload, errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=handoff["to_ref"],
                    owner_authorization_ref=owner_ref,
                ),
                after,
                control_facts,
                origin_claims={after["package"].casefold(): before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
                registry=patch.object(
                    preflight,
                    "evaluate_local_worktree_context",
                    return_value=(tuple_registry_context, [], []),
                ),
                preparation=patch.object(
                    preflight,
                    "_owner_reassignment_preparation_errors",
                    return_value=[],
                ),
                remote=patch.object(
                    preflight,
                    "_exact_fetch_origin_branch",
                    side_effect=lambda _root, branch: MAIN if branch == "main" else HEAD,
                ),
                remote_tuple=patch.object(
                    preflight,
                    "_remote_branch_tuple",
                    return_value={
                        "main": CANDIDATE,
                        handoff["from_branch"]: HEAD,
                        handoff["to_branch"]: HEAD,
                    },
                ),
            )
            self.assertFalse(
                payload["worktree_registry"][
                    "owner_reassignment_preparation_valid"
                ]
            )
            self.assertTrue(
                any("remote or claim state changed" in item for item in errors),
                errors,
            )

    def test_owner_reassignment_terminal_rejects_type_confused_control_lease(self):
        before = claim(
            writer_ref="session:prior-writer",
            branch="work/2026-08-25-terminal-lease-old",
        )
        successor = "work/2026-08-27-terminal-lease-recovery"
        owner_ref = "session:owner/decision:terminal-lease-type"
        handoff = {
            "type": "owner_reassignment",
            "from_ref": before["writer_ref"],
            "to_ref": "agent:terminal-lease-receiver",
            "from_branch": before["branch"],
            "to_branch": successor,
            "checkpoint_sha": HEAD,
            "owner_authorization_ref": owner_ref,
        }
        after = claim(
            writer_ref=handoff["to_ref"], branch=successor, handoff=handoff
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-terminal-lease"
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            current = base / "managed" / "_control"
            registry_path = base / "common" / preflight.WORKTREE_REGISTRY_REL
            registry_path.parent.mkdir(parents=True)
            registry = {
                "schema_version": 1,
                "worktrees": [
                    {
                        "path": str(current),
                        "kind": "control_singleton",
                        "state": "active",
                        "package": after["package"],
                        "branch": control_branch,
                        "head": MAIN,
                        "task_ref": handoff["to_ref"],
                        "lease": {
                            "task_ref": handoff["to_ref"],
                            "purpose": "control",
                            "package": after["package"],
                            "acquired_at": {
                                "spoof": "2026-08-27T00:00:00Z"
                            },
                        },
                    }
                ],
                "pending": None,
                "owner_reassignment_preparations": [],
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            registry_context = {
                "registry": "initialized",
                "enforced": True,
                "current_kind": "control_singleton",
                "path": str(registry_path),
                "owner_reassignment_preparation_valid": True,
                "_owner_reassignment_registry_snapshot": copy.deepcopy(registry),
            }
            control_facts = facts(
                repository=str(current), branch=control_branch
            )
            authority_claims = {after["package"].casefold(): before}
            with patch.object(
                preflight,
                "_owner_reassignment_preparation_errors",
                return_value=[],
            ), patch.object(
                preflight,
                "_exact_fetch_origin_branch",
                side_effect=lambda _root, branch: MAIN if branch == "main" else HEAD,
            ), patch.object(
                preflight,
                "_remote_branch_tuple",
                return_value={
                    "main": MAIN,
                    handoff["from_branch"]: HEAD,
                    handoff["to_branch"]: HEAD,
                },
            ), patch.object(
                preflight, "load_claims_at_ref", return_value=authority_claims
            ), patch.object(
                preflight,
                "load_claims",
                return_value={after["package"].casefold(): after},
            ):
                errors = preflight._final_owner_reassignment_boundary_errors(
                    root=base,
                    args=args(
                        "owner-reassignment",
                        task_ref=handoff["to_ref"],
                        owner_authorization_ref=owner_ref,
                    ),
                    claim=after,
                    facts=control_facts,
                    authority_claims=authority_claims,
                    registry_context=registry_context,
                )
            self.assertFalse(
                registry_context["owner_reassignment_preparation_valid"]
            )
            self.assertTrue(
                any("control acquired_at" in item for item in errors), errors
            )

    def test_owner_reassignment_rejects_control_intent_substring_spoofing(self):
        before = claim(
            writer_ref="session:prior-writer",
            branch="work/2026-08-25-example-old",
        )
        successor = "work/2026-08-27-example-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        after = claim(
            writer_ref="agent:replacement-writer",
            branch=successor,
            handoff={
                "type": "owner_reassignment",
                "from_ref": before["writer_ref"],
                "to_ref": "agent:replacement-writer",
                "from_branch": before["branch"],
                "to_branch": successor,
                "checkpoint_sha": HEAD,
                "owner_authorization_ref": owner_ref,
            },
        )
        spoofed_facts = facts(
            branch=(
                "work/2026-08-27-delivery-transfer-owner-reassignment-spoof"
            ),
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )
        with patch.object(
            preflight, "_exact_fetch_origin_branch", return_value=HEAD
        ):
            _, errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=after["writer_ref"],
                    owner_authorization_ref=owner_ref,
                ),
                after,
                spoofed_facts,
                origin_claims={"ps-example-001": before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
            )
        self.assertTrue(
            any(
                "delivery-owner-reassignment control branch" in error
                for error in errors
            ),
            errors,
        )

    def test_owner_reassignment_fails_closed_on_checkpoint_authority_and_collision(self):
        before = claim(
            writer_ref="session:prior-writer",
            branch="work/2026-08-25-example-old",
        )
        successor = "work/2026-08-27-example-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        handoff = {
            "type": "owner_reassignment",
            "from_ref": before["writer_ref"],
            "to_ref": "agent:replacement-writer",
            "from_branch": before["branch"],
            "to_branch": successor,
            "checkpoint_sha": HEAD,
            "owner_authorization_ref": owner_ref,
        }
        after = claim(
            writer_ref=handoff["to_ref"],
            branch=successor,
            handoff=handoff,
        )
        collision = claim(
            package="PS-COLLISION-001",
            number=2,
            branch=successor,
            surfaces=claimed_surfaces("PS-COLLISION-001", "src/collision"),
            domains=["product:collision"],
        )
        control_facts = facts(
            branch="work/2026-08-27-delivery-owner-reassignment-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )
        authority = {
            "ps-example-001": before,
            "ps-collision-001": collision,
        }
        candidate = {
            "ps-example-001": after,
            "ps-collision-001": collision,
        }
        with patch.object(
            preflight,
            "_exact_fetch_origin_branch",
            side_effect=[HEAD, CANDIDATE, HEAD],
        ):
            _, errors, _ = self.run_evaluate(
                args(
                    "owner-reassignment",
                    task_ref=handoff["to_ref"],
                    owner_authorization_ref="session:owner/wrong:ref",
                ),
                after,
                control_facts,
                origin_claims=authority,
                candidate_claims=candidate,
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
            )
        self.assertTrue(any("owner authorization" in error for error in errors))
        self.assertTrue(any("successor branch" in error for error in errors))
        self.assertTrue(any("branch collision" in error for error in errors))

    def test_receiver_write_is_refused_until_owner_reassignment_merges(self):
        before = claim(
            writer_ref="session:prior-writer",
            branch="work/2026-08-25-example-old",
        )
        successor = "work/2026-08-27-example-recovery"
        after = copy.deepcopy(before)
        after.update(
            {
                "writer_ref": "agent:replacement-writer",
                "branch": successor,
                "handoff": {
                    "type": "owner_reassignment",
                    "from_ref": before["writer_ref"],
                    "to_ref": "agent:replacement-writer",
                    "from_branch": before["branch"],
                    "to_branch": successor,
                    "checkpoint_sha": HEAD,
                    "owner_authorization_ref": "session:owner/decision:1",
                },
            }
        )
        _, errors, _ = self.run_evaluate(
            args("write", task_ref=after["writer_ref"]),
            after,
            facts(branch=successor),
            origin_claims={"ps-example-001": before},
            candidate_claims={"ps-example-001": after},
        )
        self.assertTrue(
            any("differs from authoritative origin/main" in error for error in errors)
        )

    def test_pause_and_close_cannot_rewrite_transfer_provenance(self):
        handoff = {
            "from_ref": "task:writer-before",
            "to_ref": "task:writer-1",
            "checkpoint_sha": HEAD,
            "relinquished": True,
        }
        before = claim(handoff=handoff)

        paused = claim(state="paused", checkpoint_sha=HEAD, handoff=None)
        pause_facts = facts(
            branch="work/2026-08-23-delivery-pause-example",
            branch_paths=(preflight.claim_relative_path(paused["package"]),),
        )

        def pause_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        _, pause_errors, _ = self.run_evaluate(
            args("pause"),
            paused,
            pause_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            git=patch.object(preflight, "_git", side_effect=pause_git),
        )
        self.assertTrue(
            any("changed fields outside" in error for error in pause_errors)
        )

        closed = claim(
            state="closed",
            merged_sha=MAIN,
            closed_at="2026-08-23T01:00:00Z",
            handoff=None,
        )
        close_facts = facts(
            branch="work/2026-08-23-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )
        _, close_errors, _ = self.run_evaluate(
            args("close"),
            closed,
            close_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=None
            ),
            ancestor=patch.object(preflight, "_is_ancestor", return_value=True),
        )
        self.assertTrue(
            any("changed fields outside" in error for error in close_errors)
        )

    def test_pause_and_close_cannot_rewrite_owner_reassignment_provenance(self):
        successor = "work/2026-08-27-example-recovery"
        handoff = {
            "type": "owner_reassignment",
            "from_ref": "session:prior-writer",
            "to_ref": "task:writer-1",
            "from_branch": "work/2026-08-25-example-old",
            "to_branch": successor,
            "checkpoint_sha": HEAD,
            "owner_authorization_ref": "session:owner/decision:1",
        }
        before = claim(branch=successor, handoff=handoff)
        paused = claim(
            branch=successor,
            state="paused",
            checkpoint_sha=HEAD,
            handoff=None,
        )
        pause_facts = facts(
            branch="work/2026-08-27-delivery-pause-example",
            branch_paths=(preflight.claim_relative_path(paused["package"]),),
        )

        def pause_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        _, pause_errors, _ = self.run_evaluate(
            args("pause"),
            paused,
            pause_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            git=patch.object(preflight, "_git", side_effect=pause_git),
        )
        self.assertTrue(any("changed fields outside" in e for e in pause_errors))

        closed = claim(
            branch=successor,
            state="closed",
            merged_sha=MAIN,
            closed_at="2026-08-27T01:00:00Z",
            handoff=None,
        )
        close_facts = facts(
            branch="work/2026-08-27-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )
        _, close_errors, _ = self.run_evaluate(
            args("close"),
            closed,
            close_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=None
            ),
            ancestor=patch.object(preflight, "_is_ancestor", return_value=True),
        )
        self.assertTrue(any("changed fields outside" in e for e in close_errors))

    def test_pause_passes_only_when_its_exact_candidate_removes_the_collision(self):
        before = claim(
            surfaces=claimed_surfaces("PS-EXAMPLE-001", "src/shared"),
            domains=["product:shared"],
        )
        other = claim(
            package="PS-OTHER-001",
            number=2,
            surfaces=claimed_surfaces("PS-OTHER-001", "src/shared/child"),
            domains=["product:shared:child"],
        )
        after = copy.deepcopy(before)
        after["state"] = "paused"
        after["checkpoint_sha"] = HEAD
        control_facts = facts(
            branch="work/2026-08-23-delivery-pause-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        payload, errors, warnings = self.run_evaluate(
            args("pause"),
            after,
            control_facts,
            origin_claims={"ps-example-001": before, "ps-other-001": other},
            candidate_claims={"ps-example-001": after, "ps-other-001": other},
            origin_claim=patch.object(
                preflight, "_origin_claim", return_value=before
            ),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )

        self.assertEqual([], errors)
        self.assertEqual(2, len(warnings))
        self.assertIn("authority_claim_collisions", payload)

    def test_resume_reactivates_the_exact_preserved_checkpoint(self):
        before = claim(state="paused", checkpoint_sha=HEAD)
        after = claim(state="active", checkpoint_sha=HEAD)
        control_facts = facts(
            branch="work/2026-08-23-delivery-resume-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        _, errors, _ = self.run_evaluate(
            args("resume"),
            after,
            control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        self.assertEqual([], errors)

        stale = claim(state="paused", checkpoint_sha=CANDIDATE)
        stale_after = claim(state="active", checkpoint_sha=CANDIDATE)
        _, errors, _ = self.run_evaluate(
            args("resume"),
            stale_after,
            control_facts,
            origin_claims={"ps-example-001": stale},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=stale),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        self.assertTrue(any("fetched branch tip" in error for error in errors))

    def test_resume_reruns_current_path_collisions(self):
        before = claim(state="paused", checkpoint_sha=HEAD)
        after = claim(state="active", checkpoint_sha=HEAD)
        other = claim(
            package="PS-OTHER-001",
            number=2,
            surfaces=claimed_surfaces("PS-OTHER-001", "src/package-1/child"),
            domains=["product:package-1:child"],
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-resume-example",
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        _, errors, _ = self.run_evaluate(
            args("resume"),
            after,
            control_facts,
            origin_claims={"ps-example-001": before, "ps-other-001": other},
            candidate_claims={"ps-example-001": after},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        self.assertTrue(any("path collision" in error for error in errors))
        self.assertTrue(any("domain collision" in error for error in errors))

    def merge_evaluation(
        self, *, value=None, post_paths=(), ancestor=True, remote_tip=HEAD,
        review_receipt=None,
    ):
        value = value or claim()
        repo_facts = facts()

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[:2] == ("rev-parse", f"refs/remotes/origin/{value['branch']}"):
                return remote_tip
            if command[0] == "merge-base":
                return BASE
            raise AssertionError(command)

        def fake_diff(_root, range_spec):
            if range_spec == f"{BASE}..{CANDIDATE}":
                return ("src/package-1/change.py",)
            if range_spec == f"{CANDIDATE}..{HEAD}":
                return tuple(post_paths)
            if range_spec == f"{BASE}..{MAIN}":
                return ("docs/unrelated.md",)
            raise AssertionError(range_spec)

        return self.run_evaluate(
            args("merge"),
            value,
            repo_facts,
            receipt=patch.object(
                preflight,
                "load_receipt",
                return_value=review_receipt or receipt(),
            ),
            git=patch.object(preflight, "_git", side_effect=fake_git),
            ancestor=patch.object(preflight, "_is_ancestor", return_value=ancestor),
            diff=patch.object(preflight, "_diff_paths", side_effect=fake_diff),
        )

    def test_merge_accepts_exact_review_and_disjoint_main_movement(self):
        payload, errors, _ = self.merge_evaluation()
        self.assertEqual([], errors)
        self.assertEqual(CANDIDATE, payload["candidate_sha"])

    def test_routine_and_bounded_self_review_receipts_complete_merge(self):
        for delivery_path in ("Routine", "Bounded"):
            with self.subTest(delivery_path=delivery_path):
                value = claim(
                    delivery_path=delivery_path,
                    review_requirement="self",
                )
                self_receipt = receipt(
                    review_type="self",
                    reviewer_ref=value["writer_ref"],
                )
                _, errors, _ = self.merge_evaluation(
                    value=value,
                    review_receipt=self_receipt,
                )
                self.assertEqual([], errors)

    def test_merge_allows_only_receipt_or_evidence_after_review(self):
        allowed = preflight.receipt_relative_path("PS-EXAMPLE-001")
        _, errors, _ = self.merge_evaluation(post_paths=(allowed,))
        self.assertEqual([], errors)
        _, errors, _ = self.merge_evaluation(post_paths=("src/package-1/change.py",))
        self.assertTrue(any("evidence-only" in error for error in errors))

    def test_merge_rejects_moved_candidate_or_remote_tip(self):
        _, errors, _ = self.merge_evaluation(ancestor=False)
        self.assertTrue(any("not an ancestor" in error for error in errors))
        _, errors, _ = self.merge_evaluation(remote_tip="f" * 40)
        self.assertTrue(any("remote branch tip" in error for error in errors))

    def test_current_main_can_verify_a_frozen_preclaim_worktree(self):
        value = claim()

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            if command[0] == "merge-base":
                return BASE
            raise AssertionError(command)

        def fake_diff(_root, range_spec):
            return {
                f"{BASE}..{CANDIDATE}": ("src/package-1/change.py",),
                f"{CANDIDATE}..{HEAD}": (),
                f"{BASE}..{MAIN}": ("docs/unrelated.md",),
            }[range_spec]

        verifier_facts = facts(
            branch="main", head=MAIN, origin_main=MAIN,
            branch_paths=(), main_paths=(),
        )
        with tempfile.TemporaryDirectory() as directory:
            frozen = Path(directory)
            with (
                patch.object(preflight, "_git_common_dir", return_value=Path("same")),
                patch.object(preflight, "collect_repo_facts", side_effect=[facts(), verifier_facts]),
                patch.object(preflight, "load_index", return_value=index()) as load_index,
                patch.object(preflight, "load_claims", return_value={"ps-example-001": value}) as load_claims,
                patch.object(preflight, "load_index_at_ref", return_value=index()),
                patch.object(preflight, "load_claims_at_ref", return_value={"ps-example-001": value}),
                patch.object(preflight, "load_receipt", side_effect=[None, receipt()]),
                patch.object(preflight, "_verify_legacy_snapshot"),
                patch.object(preflight, "_git", side_effect=fake_git),
                patch.object(preflight, "_diff_paths", side_effect=fake_diff),
                patch.object(preflight, "_is_ancestor", return_value=True),
            ):
                _, errors, _ = preflight.evaluate(
                    args("merge", candidate_worktree=str(frozen)), root=ROOT
                )
            self.assertEqual([], errors)
            load_index.assert_called_once_with(ROOT)
            load_claims.assert_called_once_with(ROOT)

    def test_close_requires_reviewed_bytes_at_the_recorded_merge(self):
        before = claim()
        closed = claim(
            state="closed", merged_sha=MAIN,
            closed_at="2026-08-23T01:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            if command[0] == "merge-base":
                return BASE
            raise AssertionError(command)

        def fake_diff(_root, range_spec):
            if range_spec in (f"{BASE}..{CANDIDATE}", f"{MAIN}^..{MAIN}"):
                return ("src/package-1/change.py",)
            raise AssertionError(range_spec)

        common = dict(
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=receipt()
            ),
            ancestor=patch.object(preflight, "_is_ancestor", return_value=True),
            git=patch.object(preflight, "_git", side_effect=fake_git),
            diff=patch.object(preflight, "_diff_paths", side_effect=fake_diff),
        )
        with patch.object(
            preflight, "_git_result",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ):
            _, errors, _ = self.run_evaluate(args("close"), closed, control_facts, **common)
        self.assertEqual([], errors)
        with patch.object(
            preflight, "_git_result",
            return_value=subprocess.CompletedProcess([], 1, "", ""),
        ):
            _, errors, _ = self.run_evaluate(args("close"), closed, control_facts, **common)
        self.assertTrue(any("reviewed candidate bytes" in error for error in errors))

    def test_close_ignores_runtime_inert_review_tail_bytes(self):
        before = claim()
        closed = claim(
            state="closed", merged_sha=MAIN,
            closed_at="2026-08-23T01:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )
        receipt_path = preflight.receipt_relative_path(closed["package"])
        evidence_path = closed["evidence_surfaces"][0]

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            if command[0] == "merge-base":
                return BASE
            raise AssertionError(command)

        def fake_diff(_root, range_spec):
            if range_spec in (f"{BASE}..{CANDIDATE}", f"{MAIN}^..{MAIN}"):
                return ("src/package-1/change.py", receipt_path, evidence_path)
            raise AssertionError(range_spec)

        def fake_git_result(_root, *command):
            path = command[-1]
            return subprocess.CompletedProcess(
                [], 1 if path in {receipt_path, evidence_path} else 0, "", ""
            )

        with (
            patch.object(preflight, "_origin_claim", return_value=before),
            patch.object(
                preflight, "load_receipt_at_ref", return_value=receipt()
            ),
            patch.object(preflight, "_is_ancestor", return_value=True),
            patch.object(preflight, "_git", side_effect=fake_git),
            patch.object(preflight, "_diff_paths", side_effect=fake_diff),
            patch.object(preflight, "_git_result", side_effect=fake_git_result),
        ):
            _, errors, _ = self.run_evaluate(
                args("close"),
                closed,
                control_facts,
                origin_claims={"ps-example-001": before},
            )
        self.assertEqual([], errors)

    def test_self_reviewed_bounded_claim_can_close_after_merge(self):
        before = claim(delivery_path="Bounded", review_requirement="self")
        closed = claim(
            delivery_path="Bounded",
            review_requirement="self",
            state="closed",
            merged_sha=MAIN,
            closed_at="2026-08-23T01:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            if command[0] == "merge-base":
                return BASE
            raise AssertionError(command)

        def fake_diff(_root, range_spec):
            if range_spec in (f"{BASE}..{CANDIDATE}", f"{MAIN}^..{MAIN}"):
                return ("src/package-1/change.py",)
            raise AssertionError(range_spec)

        self_receipt = receipt(
            review_type="self",
            reviewer_ref=before["writer_ref"],
        )
        with patch.object(
            preflight,
            "_git_result",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ):
            _, errors, _ = self.run_evaluate(
                args("close"),
                closed,
                control_facts,
                origin_claims={"ps-example-001": before},
                origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
                origin_receipt=patch.object(
                    preflight, "load_receipt_at_ref", return_value=self_receipt
                ),
                ancestor=patch.object(preflight, "_is_ancestor", return_value=True),
                git=patch.object(preflight, "_git", side_effect=fake_git),
                diff=patch.object(preflight, "_diff_paths", side_effect=fake_diff),
            )
        self.assertEqual([], errors)

    def test_close_requires_the_preserved_remote_candidate_branch(self):
        before = claim()
        closed = claim(
            state="closed",
            merged_sha=MAIN,
            closed_at="2026-08-23T01:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )

        _, errors, _ = self.run_evaluate(
            args("close"),
            closed,
            control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=receipt()
            ),
            ancestor=patch.object(preflight, "_is_ancestor", return_value=True),
            git=patch.object(
                preflight,
                "_git",
                side_effect=preflight.PreflightError("remote branch not found"),
            ),
        )
        self.assertTrue(
            any("re-push the exact reviewed branch" in error for error in errors)
        )

    def test_close_rejects_remote_branch_without_the_reviewed_candidate(self):
        before = claim()
        closed = claim(
            state="closed",
            merged_sha=MAIN,
            closed_at="2026-08-23T01:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-08-23-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(closed["package"]),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            raise AssertionError(command)

        _, errors, _ = self.run_evaluate(
            args("close"),
            closed,
            control_facts,
            origin_claims={"ps-example-001": before},
            origin_claim=patch.object(preflight, "_origin_claim", return_value=before),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=receipt()
            ),
            ancestor=patch.object(preflight, "_is_ancestor", side_effect=[True, False]),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        self.assertTrue(
            any("does not contain the reviewed candidate" in error for error in errors)
        )

    def _historical_bootstrap_close(
        self,
        *,
        package="PS-DELIVERY-CONTROL-SIMPLIFICATION-001",
        candidate_sha="ff3959815f3e4a9ca4dc5dd404a42a5e11ec462a",
        merged_sha="1b6b5d4905af32edfee43c02d6e2bdb58d31898c",
        extra_paths=(
            "docs/governance/lane_claims/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json",
            "docs/governance/lane_claims/receipts/"
            "PS-SYNTHETIC-MULTI-MEMBER-QA-001.json",
        ),
        candidate_bytes_match=True,
    ):
        """PS-DELIVERY-SIMPLIFICATION-CLOSE-REPAIR-001 scaffold: evaluate a
        close whose reviewed candidate carries ``extra_paths`` outside the
        claim, returning the error list."""
        before = claim(package=package)
        closed = claim(
            package=package,
            state="closed",
            merged_sha=merged_sha,
            closed_at="2026-09-01T00:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-09-01-delivery-close-simplification",
            branch_paths=(preflight.claim_relative_path(package),),
        )

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return HEAD
            if command[0] == "merge-base":
                return BASE
            raise AssertionError(command)

        def fake_diff(_root, range_spec):
            if range_spec in (
                f"{BASE}..{candidate_sha}",
                f"{merged_sha}^..{merged_sha}",
            ):
                return ("src/package-1/change.py", *extra_paths)
            raise AssertionError(range_spec)

        with patch.object(
            preflight,
            "_git_result",
            return_value=subprocess.CompletedProcess(
                [], 0 if candidate_bytes_match else 1, "", ""
            ),
        ):
            _, errors, _ = self.run_evaluate(
                args("close", package=package),
                closed,
                control_facts,
                origin_claims={package.casefold(): before},
                origin_claim=patch.object(
                    preflight, "_origin_claim", return_value=before
                ),
                origin_receipt=patch.object(
                    preflight,
                    "load_receipt_at_ref",
                    return_value=receipt(
                        package=package, candidate_sha=candidate_sha
                    ),
                ),
                ancestor=patch.object(
                    preflight, "_is_ancestor", return_value=True
                ),
                git=patch.object(preflight, "_git", side_effect=fake_git),
                diff=patch.object(
                    preflight, "_diff_paths", side_effect=fake_diff
                ),
            )
        return errors

    def test_close_tolerates_only_the_exact_simplification_bootstrap_tuple(self):
        self.assertEqual([], self._historical_bootstrap_close())

    def test_bootstrap_close_exception_is_keyed_to_the_exact_package(self):
        errors = self._historical_bootstrap_close(
            package="PS-EXAMPLE-001",
        )
        self.assertTrue(
            any("outside its claim" in error for error in errors), errors
        )

    def test_bootstrap_close_exception_is_keyed_to_the_exact_candidate(self):
        errors = self._historical_bootstrap_close(candidate_sha=CANDIDATE)
        self.assertTrue(
            any("outside its claim" in error for error in errors), errors
        )

    def test_bootstrap_close_exception_is_keyed_to_the_exact_merge(self):
        errors = self._historical_bootstrap_close(merged_sha=MAIN)
        self.assertTrue(
            any("outside its claim" in error for error in errors), errors
        )

    def test_bootstrap_close_exception_admits_no_additional_path(self):
        smuggled = "docs/governance/lane_claims/PS-OTHER-BOOTSTRAP-001.json"
        errors = self._historical_bootstrap_close(
            extra_paths=(
                "docs/governance/lane_claims/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json",
                "docs/governance/lane_claims/receipts/"
                "PS-SYNTHETIC-MULTI-MEMBER-QA-001.json",
                smuggled,
            ),
        )
        self.assertTrue(
            any(
                "outside its claim" in error and smuggled in error
                for error in errors
            ),
            errors,
        )
        self.assertFalse(
            any(
                "PS-SYNTHETIC-MULTI-MEMBER-QA" in error for error in errors
            ),
            errors,
        )

    def test_bootstrap_close_exception_still_requires_candidate_bytes(self):
        errors = self._historical_bootstrap_close(candidate_bytes_match=False)
        self.assertTrue(
            any("reviewed candidate bytes" in error for error in errors),
            errors,
        )

    def test_bootstrap_close_exception_still_requires_the_receipt(self):
        before = claim(package="PS-DELIVERY-CONTROL-SIMPLIFICATION-001")
        closed = claim(
            package="PS-DELIVERY-CONTROL-SIMPLIFICATION-001",
            state="closed",
            merged_sha="1b6b5d4905af32edfee43c02d6e2bdb58d31898c",
            closed_at="2026-09-01T00:00:00Z",
        )
        control_facts = facts(
            branch="work/2026-09-01-delivery-close-simplification",
            branch_paths=(
                preflight.claim_relative_path(before["package"]),
            ),
        )
        _, errors, _ = self.run_evaluate(
            args("close", package=before["package"]),
            closed,
            control_facts,
            origin_claims={before["package"].casefold(): before},
            origin_claim=patch.object(
                preflight, "_origin_claim", return_value=before
            ),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=None
            ),
            ancestor=patch.object(preflight, "_is_ancestor", return_value=True),
        )
        self.assertTrue(
            any(
                "requires the merged package review receipt" in error
                for error in errors
            ),
            errors,
        )


class SupersedeIntentTests(EvaluationTests):
    """PS-DELIVERY-SUPERSEDE-DISPOSITION-001: the terminal unmerged
    disposition. Every gate is exercised fail-closed; a delivered, merged,
    active, or receipt-bearing package can never take this path, and a
    superseded claim is terminal."""

    OWNER_REF = "task:owner/decision:supersede-omnibus"

    def _paused(self):
        return claim(
            state="paused",
            checkpoint_sha=HEAD,
        )

    def _superseded(self, **overrides):
        value = dict(
            state="superseded",
            checkpoint_sha=HEAD,
            superseded_at="2026-09-01T00:00:00Z",
            supersession={
                "owner_authorization_ref": self.OWNER_REF,
                "superseded_by": ["PS-REPLACEMENT-001"],
            },
        )
        value.update(overrides)
        return claim(**value)

    def _replacement(self, state="closed"):
        value = claim(package="PS-REPLACEMENT-001", number=3, state=state)
        if state == "closed":
            value["merged_sha"] = MAIN
            value["closed_at"] = "2026-08-30T00:00:00Z"
        return value

    def _run(
        self,
        *,
        before=None,
        after=None,
        replacement_state="closed",
        receipt_value=None,
        remote_tip=None,
        checkpoint_on_main=False,
        owner_ref=None,
        branch="work/2026-09-01-delivery-supersede-example",
    ):
        before = before if before is not None else self._paused()
        after = after if after is not None else self._superseded()
        replacement = self._replacement(replacement_state)
        control_facts = facts(
            branch=branch,
            branch_paths=(preflight.claim_relative_path(after["package"]),),
        )
        tip = remote_tip if remote_tip is not None else HEAD

        def fake_git(_root, *command):
            if command[0] == "fetch":
                return ""
            if command[0] == "rev-parse":
                return tip
            raise AssertionError(command)

        _, errors, _ = self.run_evaluate(
            args(
                "supersede",
                owner_authorization_ref=(
                    owner_ref if owner_ref is not None else self.OWNER_REF
                ),
            ),
            after,
            control_facts,
            origin_claims={
                after["package"].casefold(): before,
                "ps-replacement-001": replacement,
            },
            candidate_claims={
                after["package"].casefold(): after,
                "ps-replacement-001": replacement,
            },
            origin_claim=patch.object(
                preflight, "_origin_claim", return_value=before
            ),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=receipt_value
            ),
            ancestor=patch.object(
                preflight, "_is_ancestor", return_value=checkpoint_on_main
            ),
            git=patch.object(preflight, "_git", side_effect=fake_git),
        )
        return errors

    def test_supersede_happy_path_passes(self):
        self.assertEqual([], self._run())

    def test_supersede_accepts_a_withdrawal_reason_instead_of_replacements(self):
        after = self._superseded(
            supersession={
                "owner_authorization_ref": self.OWNER_REF,
                "withdrawal_reason": "Pre-activation scope review failed.",
            }
        )
        self.assertEqual([], self._run(after=after))

    def test_supersede_refuses_an_accepted_receipt(self):
        errors = self._run(receipt_value=receipt())
        self.assertTrue(
            any("accepted review receipt" in e for e in errors), errors
        )

    def test_supersede_requires_a_paused_origin_claim(self):
        errors = self._run(before=claim(state="active"))
        self.assertTrue(
            any("paused origin claim" in e for e in errors), errors
        )

    def test_supersede_requires_closed_replacements(self):
        errors = self._run(replacement_state="active")
        self.assertTrue(
            any("must be a closed claim" in e for e in errors), errors
        )

    def test_supersede_requires_the_exact_owner_reference(self):
        errors = self._run(owner_ref="task:owner/decision:other")
        self.assertTrue(
            any(
                "must equal --owner-authorization-ref" in e for e in errors
            ),
            errors,
        )
        errors = self._run(owner_ref="")
        self.assertTrue(
            any("requires --owner-authorization-ref" in e for e in errors),
            errors,
        )

    def test_supersede_requires_the_preserved_checkpoint_tip(self):
        errors = self._run(remote_tip=MAIN)
        self.assertTrue(
            any("equal the fetched branch tip" in e for e in errors), errors
        )

    def test_supersede_refuses_a_checkpoint_reachable_from_main(self):
        errors = self._run(checkpoint_on_main=True)
        self.assertTrue(
            any("already reachable from origin/main" in e for e in errors),
            errors,
        )

    def test_supersede_is_a_mutating_control_intent(self):
        self.assertIn("supersede", preflight.MUTATING_INTENTS)
        self.assertIn("supersede", preflight.CONTROL_INTENTS)

    def test_supersede_requires_its_control_branch_pattern(self):
        errors = self._run(branch="work/2026-09-01-delivery-close-example")
        self.assertTrue(
            any("delivery-supersede control branch" in e for e in errors),
            errors,
        )

    def test_superseded_claims_are_terminal(self):
        superseded = self._superseded()
        resumed = self._superseded(state="active")
        control_facts = facts(
            branch="work/2026-09-01-delivery-resume-example",
            branch_paths=(preflight.claim_relative_path(superseded["package"]),),
        )
        _, errors, _ = self.run_evaluate(
            args("resume"),
            resumed,
            control_facts,
            origin_claims={superseded["package"].casefold(): superseded},
            origin_claim=patch.object(
                preflight, "_origin_claim", return_value=superseded
            ),
        )
        self.assertTrue(
            any("resume requires a paused origin claim" in e for e in errors),
            errors,
        )
        closed = self._superseded(
            state="closed", merged_sha=MAIN, closed_at="2026-09-01T01:00:00Z"
        )
        control_facts = facts(
            branch="work/2026-09-01-delivery-close-example",
            branch_paths=(preflight.claim_relative_path(superseded["package"]),),
        )
        _, errors, _ = self.run_evaluate(
            args("close"),
            closed,
            control_facts,
            origin_claims={superseded["package"].casefold(): superseded},
            origin_claim=patch.object(
                preflight, "_origin_claim", return_value=superseded
            ),
            origin_receipt=patch.object(
                preflight, "load_receipt_at_ref", return_value=None
            ),
        )
        self.assertTrue(
            any(
                "close requires an active or paused origin claim" in e
                for e in errors
            ),
            errors,
        )


class EvidenceErrataTests(unittest.TestCase):
    """PS-CLOSED-CLAIM-EVIDENCE-ERRATA-001: the owner-authorized amendment of
    a CLOSED package's one fixed runtime-inert evidence file, admitted without
    reopening or mutating any claim. Every gate is exercised fail-closed, and
    the happy path proves the full stack admits exactly the intended shape.

    Borrows EvaluationTests.run_evaluate by reference rather than
    subclassing, so the parent's own tests are not silently re-collected and
    duplicated under this class.
    """

    run_evaluate = EvaluationTests.run_evaluate

    OWNER_REF = "session:owner-errata/decision:1"
    MARKER = f"<!-- evidence-errata-authorization: {OWNER_REF} -->"
    EVIDENCE = preflight.evidence_relative_path("PS-EXAMPLE-001")

    def closed_claim(self, **overrides):
        return claim(
            state="closed",
            merged_sha=CANDIDATE,
            closed_at="2026-08-24T00:00:00Z",
            **overrides,
        )

    def errata_args(self, **overrides):
        value = {"owner_authorization_ref": self.OWNER_REF}
        value.update(overrides)
        return args("evidence-errata", **value)

    def errata_facts(self, **overrides):
        value = {
            "branch": "work/2026-08-25-delivery-evidence-errata-example",
            "branch_paths": (self.EVIDENCE,),
            "ahead": 1,
            "behind": 0,
        }
        value.update(overrides)
        return facts(**value)

    def file_patches(self, *, head_has_marker=True, origin_has_marker=False,
                     ordinary=True):
        """Patch the two file inspections the intent performs.

        ``_tracked_regular_blob`` answers requirement 7 and the two
        ``_git_result(... "show" ...)`` calls answer requirement 8, so the
        evaluation tests can drive both without a fixture repository.
        """
        head_text = "Evidence body.\n" + (self.MARKER if head_has_marker else "")
        origin_text = "Evidence body.\n" + (self.MARKER if origin_has_marker else "")

        def fake_git_result(root, *git_args):
            if git_args and git_args[0] == "show":
                ref = git_args[1]
                text = origin_text if ref.startswith("origin/main:") else head_text
                return subprocess.CompletedProcess([], 0, text, "")
            return subprocess.CompletedProcess([], 0, "", "")

        return {
            "blob": patch.object(
                preflight, "_tracked_regular_blob", return_value=ordinary
            ),
            "git_result": patch.object(
                preflight, "_git_result", side_effect=fake_git_result
            ),
        }

    def run_errata(self, *, request=None, value=None, repo_facts=None,
                   origin_claims=None, candidate_claims=None, **file_kwargs):
        value = value if value is not None else self.closed_claim()
        return self.run_evaluate(
            request or self.errata_args(),
            value,
            repo_facts or self.errata_facts(),
            origin_claims=origin_claims,
            candidate_claims=candidate_claims,
            **self.file_patches(**file_kwargs),
        )

    def test_the_exact_intended_shape_is_admitted(self):
        _, errors, _ = self.run_errata()
        self.assertEqual([], errors)

    def test_an_active_claim_is_refused(self):
        value = claim()
        _, errors, _ = self.run_errata(value=value)
        self.assertTrue(any("only to a closed claim" in e for e in errors))

    def test_a_paused_claim_is_refused(self):
        value = claim(state="paused", checkpoint_sha=CANDIDATE)
        _, errors, _ = self.run_errata(value=value)
        self.assertTrue(any("only to a closed claim" in e for e in errors))

    def test_a_reopened_or_mutated_branch_claim_is_refused(self):
        authority = self.closed_claim()
        mutated = self.closed_claim(outcome="A quietly rewritten outcome.")
        _, errors, _ = self.run_errata(
            value=mutated,
            origin_claims={"ps-example-001": authority},
        )
        self.assertTrue(any("reopen or mutate" in e for e in errors))

    def test_any_other_claim_change_is_refused(self):
        authority = self.closed_claim()
        stray = claim(package="PS-STRAY-001", number=2,
                      surfaces=["src/package-2"], domains=["product:stray"])
        _, errors, _ = self.run_errata(
            value=authority,
            origin_claims={"ps-example-001": copy.deepcopy(authority)},
            candidate_claims={
                "ps-example-001": authority,
                "ps-stray-001": stray,
            },
        )
        self.assertTrue(any("add, remove, or change any claim" in e for e in errors))

    def test_a_missing_authoritative_claim_is_refused(self):
        value = self.closed_claim()
        _, errors, _ = self.run_errata(
            value=value,
            origin_claims={},
            candidate_claims={"ps-example-001": value},
        )
        self.assertTrue(
            any("no authoritative claim exists on origin/main" in e for e in errors)
        )

    def test_the_control_branch_pattern_is_required(self):
        _, errors, _ = self.run_errata(
            repo_facts=self.errata_facts(
                branch="work/2026-08-25-delivery-close-example"
            ),
        )
        self.assertTrue(
            any("delivery-evidence-errata" in e for e in errors)
        )

    def test_a_missing_owner_reference_is_refused(self):
        _, errors, _ = self.run_errata(
            request=self.errata_args(owner_authorization_ref=""),
        )
        self.assertTrue(
            any("--owner-authorization-ref" in e for e in errors)
        )

    def test_a_malformed_owner_reference_is_refused(self):
        _, errors, _ = self.run_errata(
            request=self.errata_args(owner_authorization_ref="not an opaque ref"),
        )
        self.assertTrue(
            any("--owner-authorization-ref" in e for e in errors)
        )

    def test_the_owner_reference_is_rejected_on_unrelated_intents(self):
        value = claim()
        _, errors, _ = self.run_evaluate(
            args("write", owner_authorization_ref=self.OWNER_REF),
            value,
            facts(),
        )
        self.assertTrue(
            any(
            "valid only for evidence-errata, owner-reassignment, supersede, or repair admission"
            in e
            for e in errors
        )
        )

    def test_a_second_path_riding_along_is_refused(self):
        _, errors, _ = self.run_errata(
            repo_facts=self.errata_facts(
                branch_paths=(self.EVIDENCE, "workshop_routes.py"),
            ),
        )
        self.assertTrue(any("must change only" in e for e in errors))

    def test_a_wrong_single_path_is_refused(self):
        _, errors, _ = self.run_errata(
            repo_facts=self.errata_facts(branch_paths=("workshop_routes.py",)),
        )
        self.assertTrue(any("must change only" in e for e in errors))

    def test_more_than_one_commit_is_refused(self):
        _, errors, _ = self.run_errata(repo_facts=self.errata_facts(ahead=2))
        self.assertTrue(any("exactly one commit ahead" in e for e in errors))

    def test_a_stale_branch_behind_main_is_refused(self):
        _, errors, _ = self.run_errata(
            repo_facts=self.errata_facts(ahead=1, behind=1)
        )
        self.assertTrue(any("zero behind" in e for e in errors))

    def test_a_missing_marker_in_the_amendment_is_refused(self):
        _, errors, _ = self.run_errata(head_has_marker=False)
        self.assertTrue(any("authorization marker" in e for e in errors))

    def test_a_marker_already_on_main_is_refused(self):
        _, errors, _ = self.run_errata(origin_has_marker=True)
        self.assertTrue(any("already contains this exact" in e for e in errors))

    def test_a_non_ordinary_file_is_refused(self):
        _, errors, _ = self.run_errata(ordinary=False)
        self.assertTrue(any("ordinary tracked file" in e for e in errors))

    def test_a_claim_without_the_single_fixed_evidence_surface_is_refused(self):
        value = self.closed_claim(
            evidence_surfaces=[self.EVIDENCE, "docs/extra.md"]
        )
        _, errors, _ = self.run_errata(value=value)
        self.assertTrue(
            any("single fixed evidence surface" in e for e in errors)
        )

    def test_the_mechanism_requires_fetch_and_clean(self):
        _, errors, _ = self.run_errata(
            request=self.errata_args(fetch=False, require_clean=False),
        )
        self.assertTrue(any("requires --fetch" in e for e in errors))
        self.assertTrue(any("requires --require-clean" in e for e in errors))


class CurrentRepositoryTests(unittest.TestCase):
    def test_current_index_claims_and_legacy_snapshot_are_valid(self):
        current_index = preflight.load_index(ROOT)
        current_claims = preflight.load_claims(ROOT)
        self.assertEqual([], preflight.validate_index(current_index))
        claim_errors, _ = preflight.split_claim_set_errors(current_claims)
        self.assertEqual([], claim_errors)
        legacy = current_index["legacy_snapshot"]
        blob = subprocess.check_output(
            ["git", "rev-parse", f"{legacy['commit']}:{legacy['path']}"],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(legacy["blob"], blob)

    def test_live_control_plane_is_small_and_has_no_bespoke_packages(self):
        script = (ROOT / "scripts" / "delivery_preflight.py").read_text(
            encoding="utf-8"
        )
        ledger = (ROOT / preflight.INDEX_REL).read_text(encoding="utf-8")
        self.assertLess(len(ledger.splitlines()), 40)
        self.assertNotIn("MAX_ACTIVE_LANES", script)
        self.assertNotIn("max_production_capable_lanes", script)
        self.assertNotIn("PS-INTERVIEW", script)
        self.assertNotIn("PS-SIGNIN", script)

    def test_standing_workshop_authority_and_continuity_are_narrowly_routed(self):
        standing_ref = (
            "session:01a04348-7e3e-7a11-a443-752498be91b5/"
            "owner-direction:2026-08-27/workshop-use-disclosure-standing-completion"
        )
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        start = (ROOT / "START_HERE.md").read_text(encoding="utf-8")
        decisions = (
            ROOT / "docs" / "governance" / "DECISIONS.md"
        ).read_text(encoding="utf-8")
        decisions_normalized = " ".join(decisions.split())
        lifecycle = (
            ROOT / "docs" / "governance" / "WORKTREE_LIFECYCLE.md"
        ).read_text(encoding="utf-8")
        lifecycle_normalized = " ".join(lifecycle.split())

        self.assertIn("standing bounded Workshop", agents)
        self.assertIn("standing bounded Workshop", start)
        self.assertIn(standing_ref, decisions_normalized)
        for boundary in (
            "active or paused",
            "failed gate or defect",
            "expires",
            "production deployment",
            "schema application or rollback",
            "destructive action",
            "credential access",
            "spending",
            "materially revised visual direction",
        ):
            self.assertIn(boundary, decisions_normalized)
        for proof in (
            "strict ancestor",
            "byte-identical",
            "for-each-ref",
            "never edits the preparation",
        ):
            self.assertIn(proof, lifecycle_normalized)

    def test_read_preflight_passes_in_the_current_worktree(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = preflight.main(
                [
                    "--package",
                    "PS-DELIVERY-CONTROL-SIMPLIFICATION-001",
                    "--intent",
                    "read",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(0, result, payload)
        self.assertEqual("pass", payload["result"])
        self.assertIn("withheld", payload["authority"]["production"])


class ReconciledProductCloseGitTests(unittest.TestCase):
    """Real Git objects for the content-equivalent synchronization graph."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.remote = Path(self.temp.name) / "remote.git"
        self.root.mkdir()
        self.run_git("init", "-q", "-b", "main")
        self.run_git("config", "user.name", "Reconciliation Test")
        self.run_git("config", "user.email", "test@example.invalid")
        subprocess.run(["git", "init", "--bare", "-q", str(self.remote)], check=True)
        self.run_git("remote", "add", "origin", str(self.remote))
        self.package = "PS-TEST-RECONCILED-001"
        self.product = "src/product.txt"
        self.claim = claim(
            package=self.package, writer_ref="task:writer-reconciled",
            branch="work/reconciled-product-test",
            surfaces=claimed_surfaces(self.package, self.product),
        )
        self.evidence = preflight.evidence_relative_path(self.package)
        self.receipt_path = preflight.receipt_relative_path(self.package)
        self.write(self.product, "old\n")
        self.base = self.commit("base")
        self.run_git("checkout", "-q", "-b", "original")
        self.write(self.product, "new\n")
        self.original = self.commit("reviewed product")
        self.run_git("checkout", "-q", "main")
        self.write("docs/unrelated.txt", "main advanced\n")
        self.commit("unrelated main")
        self.write(self.product, "new\n")
        self.merged = self.commit("independent product introduction")
        tree = self.run_git("rev-parse", f"{self.merged}^{{tree}}")
        self.sync = self.run_git("commit-tree", tree, "-p", self.original,
                                 "-p", self.merged, "-m", "sync reviewed product")
        self.run_git("branch", self.claim["branch"], self.sync)
        self.run_git("checkout", "-q", self.claim["branch"])
        self.write(self.evidence, "# Independent review evidence\n")
        self.write(self.receipt_path, json.dumps(self.review(self.original)))
        self.historical = self.commit("historical C review")
        self.final_review = self.review(self.sync)
        self.write(self.receipt_path, json.dumps(self.final_review))
        self.tip = self.commit("final S review")
        self.run_git("push", "-q", "origin", self.claim["branch"])
        self.run_git("checkout", "-q", "main")
        self.write(self.evidence, "# Independent review evidence\n")
        self.write(self.receipt_path, json.dumps(self.final_review))
        self.introduction = self.commit("accept final review records")
        self.run_git("push", "-q", "origin", "main")

    def run_git(self, *arguments):
        completed = subprocess.run(
            ["git", *arguments], cwd=self.root, text=True,
            encoding="utf-8", capture_output=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        return completed.stdout.strip()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message):
        self.run_git("add", "-A")
        self.run_git("commit", "-q", "-m", message)
        return self.run_git("rev-parse", "HEAD")

    def review(self, candidate_sha, **overrides):
        value = receipt(
            package=self.package, candidate_sha=candidate_sha,
            reviewer_ref="agent:independent-reconciled-reviewer",
            evidence_ref=self.evidence,
        )
        value.update(overrides)
        return value

    def verify(self, **overrides):
        values = {
            "root": self.root, "claim": self.claim, "receipt": self.final_review,
            "candidate": self.sync, "merged": self.merged,
            "remote_tip": self.tip, "pinned_main": self.introduction,
        }
        values.update(overrides)
        return preflight._reconciled_product_close_errors(**values)

    def test_corporate_shaped_product_is_admitted(self):
        self.assertEqual(self.merged, self.run_git("merge-base", self.sync, self.merged))
        self.assertEqual((), preflight._diff_paths(self.root, f"{self.merged}..{self.sync}"))
        self.assertEqual([], self.verify())

    def test_add_delete_and_rename_have_explicit_raw_path_coverage(self):
        pre_m = self.run_git("rev-parse", f"{self.merged}^")
        for action in ("add", "delete", "rename"):
            with self.subTest(action=action):
                def change():
                    if action == "add":
                        self.write("src/added.txt", "added\n")
                    elif action == "delete":
                        self.run_git("rm", "-q", self.product)
                    else:
                        self.run_git("mv", self.product, "src/renamed.txt")
                self.run_git("checkout", "-q", "--detach", self.base)
                change()
                c = self.commit(action + " reviewed")
                self.run_git("checkout", "-q", "--detach", pre_m)
                change()
                m = self.commit(action + " introduced")
                tree = self.run_git("rev-parse", f"{m}^{{tree}}")
                s = self.run_git("commit-tree", tree, "-p", c, "-p", m,
                                 "-m", action + " sync")
                surfaces = claimed_surfaces(
                    self.package, self.product, "src/added.txt", "src/renamed.txt"
                )
                errors = self.verify(candidate=s, merged=m,
                                     claim={**self.claim, "surfaces": surfaces})
                self.assertTrue(any("M is not on pinned main" in e for e in errors), errors)

    def test_wrong_ordered_parent_or_merged_commit_refuses(self):
        self.assertTrue(self.verify(merged=self.original))
        tree = self.run_git("rev-parse", f"{self.merged}^{{tree}}")
        reversed_sync = self.run_git("commit-tree", tree, "-p", self.merged,
                                     "-p", self.original, "-m", "reversed")
        self.assertTrue(self.verify(candidate=reversed_sync))
        extra_sync = self.run_git("commit-tree", tree, "-p", self.original,
                                  "-p", self.merged, "-p", self.base,
                                  "-m", "extra parent")
        self.assertTrue(self.verify(candidate=extra_sync))

    def test_ambiguous_derived_base_refuses(self):
        old_tree = self.run_git("rev-parse", f"{self.base}^{{tree}}")
        new_tree = self.run_git("rev-parse", f"{self.original}^{{tree}}")
        a1 = self.run_git("commit-tree", new_tree, "-p", self.base, "-m", "A1")
        b1 = self.run_git("commit-tree", old_tree, "-p", self.base, "-m", "B1")
        c = self.run_git("commit-tree", new_tree, "-p", a1, "-p", b1, "-m", "C")
        pre_m = self.run_git("commit-tree", old_tree, "-p", b1, "-p", a1, "-m", "pre-M")
        m = self.run_git("commit-tree", new_tree, "-p", pre_m, "-m", "M")
        s = self.run_git("commit-tree", new_tree, "-p", c, "-p", m, "-m", "S")
        self.assertEqual(2, len(self.run_git("merge-base", "--all", c, pre_m).splitlines()))
        self.assertTrue(self.verify(candidate=s, merged=m))

    def test_exact_product_delta_and_claim_are_required(self):
        self.assertTrue(self.verify(claim={**self.claim, "surfaces": claimed_surfaces(self.package)}))
        self.assertTrue(self.verify(merged=self.base))
        altered = self.run_git("commit-tree", self.run_git("rev-parse", f"{self.original}^{{tree}}"),
                               "-p", self.original, "-p", self.merged, "-m", "wrong tree")
        self.assertTrue(self.verify(candidate=altered))

    def test_empty_extra_blob_and_mode_product_deltas_refuse(self):
        pre_m = self.run_git("rev-parse", f"{self.merged}^")
        same_tree = self.run_git("rev-parse", f"{pre_m}^{{tree}}")
        empty_m = self.run_git("commit-tree", same_tree, "-p", pre_m, "-m", "empty M")
        self.assertTrue(self.verify(merged=empty_m))
        self.run_git("checkout", "-q", "--detach", self.merged)
        self.write("src/extra.txt", "extra\n")
        extra_tree_commit = self.commit("extra product")
        extra_tree = self.run_git("rev-parse", f"{extra_tree_commit}^{{tree}}")
        extra_m = self.run_git("commit-tree", extra_tree, "-p", pre_m, "-m", "extra M")
        extra_s = self.run_git("commit-tree", extra_tree, "-p", self.original,
                               "-p", extra_m, "-m", "extra S")
        self.assertTrue(self.verify(candidate=extra_s, merged=extra_m))
        self.run_git("checkout", "-q", "--detach", self.merged)
        self.write(self.product, "wrong blob\n")
        blob_tree_commit = self.commit("wrong blob")
        blob_tree = self.run_git("rev-parse", f"{blob_tree_commit}^{{tree}}")
        blob_m = self.run_git("commit-tree", blob_tree, "-p", pre_m, "-m", "blob M")
        blob_s = self.run_git("commit-tree", blob_tree, "-p", self.original,
                              "-p", blob_m, "-m", "blob S")
        self.assertTrue(self.verify(candidate=blob_s, merged=blob_m))
        self.run_git("checkout", "-q", "--detach", self.merged)
        self.run_git("update-index", "--chmod=+x", self.product)
        mode_tree = self.run_git("write-tree")
        mode_m = self.run_git("commit-tree", mode_tree, "-p", pre_m, "-m", "mode M")
        mode_s = self.run_git("commit-tree", mode_tree, "-p", self.original,
                              "-p", mode_m, "-m", "mode S")
        self.assertTrue(self.verify(candidate=mode_s, merged=mode_m))

    def test_receipt_and_record_integrity_are_required(self):
        self.assertTrue(self.verify(receipt=self.review(self.original)))
        self.assertTrue(self.verify(remote_tip=self.historical))

    def test_duplicate_or_malformed_historical_receipt_refuses(self):
        for content, expected in (
            ('{"candidate_sha":"one","candidate_sha":"two"}', "duplicate review receipt JSON key"),
            ("{bad JSON", "malformed review receipt JSON"),
        ):
            with self.subTest(content=content):
                self.run_git("checkout", "-q", "--detach", self.sync)
                self.write(self.evidence, "# Independent review evidence\n")
                self.write(self.receipt_path, content)
                self.commit("invalid historical receipt")
                self.write(self.receipt_path, json.dumps(self.final_review))
                restored_tip = self.commit("restore accepted final S receipt")
                errors = self.verify(remote_tip=restored_tip)
                self.assertTrue(any(expected in e for e in errors), errors)

    def test_missing_or_invalid_historical_review_refuses(self):
        self.run_git("checkout", "-q", "--detach", self.sync)
        self.write(self.evidence, "# Independent review evidence\n")
        self.write(self.receipt_path, json.dumps(self.final_review))
        no_h = self.commit("final review with no historical C review")
        errors = self.verify(remote_tip=no_h)
        self.assertTrue(any("historical" in e for e in errors), errors)
        self.run_git("checkout", "-q", "--detach", self.sync)
        self.write(self.evidence, "# Independent review evidence\n")
        self.write(self.receipt_path, json.dumps(self.review(
            self.original, findings=[{"status": "open"}],
        )))
        self.commit("unresolved C review")
        self.write(self.receipt_path, json.dumps(self.final_review))
        invalid_h_tip = self.commit("final review after invalid historical")
        errors = self.verify(remote_tip=invalid_h_tip)
        self.assertTrue(any("historical independent PASS is invalid" in e for e in errors), errors)

        self.run_git("checkout", "-q", "--detach", self.sync)
        self.write(self.evidence, "# Independent review evidence\n")
        self.write(self.receipt_path, json.dumps(self.review(
            self.original, reviewer_ref=self.claim["writer_ref"],
        )))
        self.commit("self C review")
        self.write(self.receipt_path, json.dumps(self.final_review))
        self_tip = self.commit("final review after self historical")
        errors = self.verify(remote_tip=self_tip)
        self.assertTrue(any("historical independent PASS is invalid" in e for e in errors), errors)

    def test_intermediate_s_receipt_survives_fixed_evidence_edits(self):
        self.run_git("checkout", "-q", self.claim["branch"])
        self.write(self.evidence, "# Temporary evidence revision\n")
        self.commit("revise fixed evidence")
        self.write(self.evidence, "# Independent review evidence\n")
        restored_tip = self.commit("restore fixed evidence")
        self.run_git("push", "-q", "origin", self.claim["branch"])
        self.assertEqual([], self.verify(remote_tip=restored_tip))

    def test_unrelated_main_symlink_after_e_does_not_block(self):
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"], cwd=self.root,
            input="target", text=True, encoding="utf-8", capture_output=True,
            check=True,
        ).stdout.strip()
        self.run_git("update-index", "--add", "--cacheinfo",
                     f"120000,{blob},docs/unrelated-link")
        self.run_git("commit", "-q", "-m", "unrelated symlink after E")
        later_main = self.run_git("rev-parse", "HEAD")
        self.run_git("push", "-q", "origin", "main")
        self.assertEqual([], self.verify(pinned_main=later_main))

    def test_ambiguous_historical_state_and_introduction_refuse(self):
        self.run_git("checkout", "-q", "--detach", self.historical)
        self.write(self.evidence, "# Updated historical evidence\n")
        another_h = self.commit("second historical state")
        self.write(self.receipt_path, json.dumps(self.final_review))
        final_after_two = self.commit("final after two historical states")
        self.assertTrue(self.verify(remote_tip=final_after_two))
        self.run_git("checkout", "-q", "main")
        self.run_git("rm", "-q", self.evidence, self.receipt_path)
        self.commit("remove fixed records")
        self.write(self.evidence, "# Independent review evidence\n")
        self.write(self.receipt_path, json.dumps(self.final_review))
        second_e = self.commit("second introduction")
        self.assertTrue(self.verify(pinned_main=second_e))

    def test_tail_rejects_claim_unrelated_evidence_and_merge(self):
        self.run_git("checkout", "-q", self.claim["branch"])
        for path in (preflight.claim_relative_path(self.package),
                     "docs/governance/lane_claims/evidence/PS-OTHER-001.md"):
            self.write(path, "unexpected\n")
            changed = self.commit("unrelated tail edit")
            self.assertTrue(self.verify(remote_tip=changed))
        tree = self.run_git("rev-parse", f"{self.tip}^{{tree}}")
        merge_tail = self.run_git("commit-tree", tree, "-p", self.tip,
                                  "-p", self.merged, "-m", "tail merge")
        self.assertTrue(self.verify(remote_tip=merge_tail))

    def test_accepted_fixed_records_cannot_change(self):
        self.run_git("checkout", "-q", self.claim["branch"])
        self.write(self.evidence, "# Changed final evidence\n")
        changed = self.commit("changed final evidence")
        self.assertTrue(self.verify(remote_tip=changed))

    def test_tail_rejects_product_edit_and_revert(self):
        self.run_git("checkout", "-q", self.claim["branch"])
        self.write(self.product, "transient\n")
        self.commit("product edit")
        self.write(self.product, "new\n")
        reverted = self.commit("product revert")
        self.assertTrue(self.verify(remote_tip=reverted))

    def test_remote_ref_movement_or_absence_refuses(self):
        self.run_git("checkout", "-q", self.claim["branch"])
        self.write(self.evidence, "changed evidence\n")
        moved = self.commit("branch moved")
        self.run_git("push", "-q", "origin", self.claim["branch"])
        self.assertTrue(self.verify())
        self.assertTrue(self.verify(remote_tip=moved))
        self.run_git("push", "-q", "origin", ":" + self.claim["branch"])
        self.assertTrue(self.verify())

    def test_remote_main_movement_refuses(self):
        self.write("docs/main-later.txt", "new main\n")
        self.commit("main moved")
        self.run_git("push", "-q", "origin", "main")
        errors = self.verify()
        self.assertTrue(any("pinned main moved" in e or "remote main" in e for e in errors), errors)


class OperationsOnlyCloseTests(unittest.TestCase):
    """Exercise completion admission with real custody/receipt validators."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.claim = claim(
            surfaces=claimed_surfaces("PS-EXAMPLE-001", *sorted(
                lifecycle_registry.CLOSED_CUSTODY_REQUIRED_SURFACES)),
            domains=sorted(lifecycle_registry.CLOSED_CUSTODY_REQUIRED_DOMAINS),
        )
        self.evidence_path = preflight.evidence_relative_path(self.claim["package"])
        self.review = receipt(evidence_ref=self.evidence_path)
        self.accepted = receipt(candidate_sha=BASE, evidence_ref=self.evidence_path)
        self.historical_claim = copy.deepcopy(self.claim)
        self.proof = {
            "schema_version": 1,
            "cleanup_package": self.claim["package"],
            "cleanup_task_ref": self.claim["writer_ref"],
            "cleanup_path": str(self.root / "cleanup"),
            "cleanup_branch": self.claim["branch"],
            "cleanup_head": HEAD,
            "reviewed_candidate": BASE,
            "reviewer_ref": self.accepted["reviewer_ref"],
            "lifecycle_script_blob": "f" * 40,
            "owner_authorization_ref": self.claim["owner_outcome_ref"],
            "source_unavailable_ref": "session:target-unavailable/evidence-1",
            "target_package": "PS-TARGET-001",
            "source_task_ref": "session:original-target-writer",
            "target_path": str(self.root / "retired-target"),
            "target_branch": "work/2026-08-23-target",
            "registry_previous_head": BASE,
            "expected_head": HEAD,
            "authoritative_main": MAIN,
            "target_server_head": HEAD,
            "recorded_at": "2026-09-05T10:00:00Z",
        }
        self.target_claim = {
            "state": "closed", "writer_ref": self.proof["source_task_ref"],
            "branch": self.proof["target_branch"],
        }
        self.record = {
            "state": "retired", "kind": "durable", "lease": None,
            "package": self.proof["target_package"],
            "task_ref": self.proof["source_task_ref"],
            "branch": self.proof["target_branch"], "head": HEAD,
            "path": self.proof["target_path"], "retired_at": self.proof["recorded_at"],
            "closed_custody_retirement": self.proof,
        }
        self.registry = {"pending": None, "worktrees": [self.record, {
            "state": "active", "kind": "durable", "lease": None,
            "package": self.claim["package"], "task_ref": self.claim["writer_ref"],
            "branch": self.claim["branch"], "path": self.proof["cleanup_path"],
        }]}
        self.completion = {
            "schema_version": 1, "package": self.claim["package"],
            "retirements": [copy.deepcopy(self.proof)],
        }
        self.raw_override = None
        self.changed_blob = None

    def run_close(self, lifecycle_overrides=None, **overrides):
        def git(_root, *command):
            if command[0] == "show":
                return self.raw_override if self.raw_override is not None else (
                    "# Completion\n```peerslate-closed-custody-completion\n"
                    + json.dumps(self.completion) + "\n```\n"
                )
            if command[0] == "rev-parse":
                return "e" * 40 if command[1] == self.changed_blob else "f" * 40
            raise AssertionError(command)

        def json_at_ref(_root, _ref, path):
            return self.target_claim if "PS-TARGET-001" in path else self.historical_claim

        context = Namespace(root=self.root, registry_path=self.root / "registry.json")
        defaults = {
            "_is_ci_environment": False, "_tracked_regular_blob": True,
            "_is_ancestor": True,
        }
        with ExitStack() as stack:
            for name, value in {**defaults, **overrides}.items():
                stack.enter_context(patch.object(preflight, name, return_value=value))
            local_defaults = {
                "_repo_context": context, "_registry_lock": nullcontext(),
                "_load_registry": self.registry, "_assert_registry_identity": None,
                "_active_claim": self.claim, "_worktree_at": None,
                "_remote_branch_tip": HEAD,
            }
            for name, value in {**local_defaults, **(lifecycle_overrides or {})}.items():
                stack.enter_context(patch.object(lifecycle_registry, name, return_value=value))
            stack.enter_context(patch.object(preflight, "_git", side_effect=git))
            stack.enter_context(patch.object(preflight, "_json_at_ref", side_effect=json_at_ref))
            stack.enter_context(patch.object(preflight, "load_receipt_at_ref", return_value=self.accepted))
            mutation = stack.enter_context(patch.object(lifecycle_registry, "_atomic_write"))
            removal = stack.enter_context(patch.object(lifecycle_registry, "_ordinary_worktree_remove"))
            errors = preflight._operations_only_close_errors(
                self.root, self.claim, self.review, CANDIDATE, MAIN, HEAD,
                (self.evidence_path,),
            )
            mutation.assert_not_called()
            removal.assert_not_called()
            return errors

    def test_exact_reviewed_completed_custody_passes_without_mutation(self):
        self.assertEqual([], self.run_close())

    def test_empty_arbitrary_or_duplicate_key_evidence_refuses(self):
        for raw in ("audit only", "", "```peerslate-closed-custody-completion\n"
                    '{"schema_version":1,"schema_version":1}\n```'):
            with self.subTest(raw=raw):
                self.raw_override = raw
                self.assertTrue(self.run_close())
        self.raw_override = None
        self.completion["retirements"] = []
        self.assertTrue(self.run_close())

    def test_custody_evidence_tampering_or_omission_refuses(self):
        for field, value in (
            ("source_unavailable_ref", "session:invented"),
            ("owner_authorization_ref", "session:other-owner"),
            ("expected_head", BASE), ("target_path", str(self.root / "wrong")),
        ):
            with self.subTest(field=field):
                original = self.completion["retirements"][0][field]
                self.completion["retirements"][0][field] = value
                self.assertTrue(self.run_close())
                self.completion["retirements"][0][field] = original
        self.completion["retirements"] *= 2
        self.assertTrue(self.run_close())

    def test_unauthenticated_or_changed_mechanism_review_refuses(self):
        for field, value in (
            ("candidate_sha", CANDIDATE), ("reviewer_ref", "agent:other-reviewer"),
            ("review_type", "self"), ("result", "fail"),
            ("evidence_ref", "task:unrelated-evidence"),
        ):
            with self.subTest(field=field):
                old = self.accepted[field]
                self.accepted[field] = value
                self.assertTrue(self.run_close())
                self.accepted[field] = old
        self.historical_claim["owner_outcome_ref"] = "session:old-authority"
        self.assertTrue(self.run_close())

    def test_evidence_receipt_and_mechanism_bytes_are_immutable(self):
        for ref, path in (
            (CANDIDATE, self.evidence_path),
            (HEAD, preflight.receipt_relative_path(self.claim["package"])),
            (BASE, "scripts/worktree_lifecycle.py"),
            (MAIN, "scripts/delivery_preflight.py"),
            (HEAD, "tests/test_delivery_preflight.py"),
        ):
            with self.subTest(ref=ref, path=path):
                self.changed_blob = f"{ref}:{path}"
                self.assertTrue(self.run_close())

    def test_wrong_policy_pending_or_duplicate_custody_refuses(self):
        for field, value in (
            ("delivery_path", "Bounded"), ("review_requirement", "self"),
            ("repository_authority", "write_only"), ("domains", []),
        ):
            with self.subTest(field=field):
                old = self.claim[field]
                self.claim[field] = value
                self.assertTrue(self.run_close())
                self.claim[field] = old
        self.registry["pending"] = {"operation": "unresolved"}
        self.assertTrue(self.run_close())
        self.registry["pending"] = None
        self.registry["worktrees"].append(copy.deepcopy(self.record))
        self.assertTrue(self.run_close())
        self.registry["worktrees"][-1] = None
        self.assertTrue(self.run_close())

    def test_local_source_independence_and_live_absence_remain_required(self):
        self.assertTrue(self.run_close(_is_ci_environment=True))
        self.assertTrue(self.run_close(_tracked_regular_blob=False))
        self.assertTrue(self.run_close(_is_ancestor=False))
        self.assertTrue(self.run_close(lifecycle_overrides={"_load_registry": None}))
        self.assertTrue(self.run_close(lifecycle_overrides={"_remote_branch_tip": BASE}))
        self.assertTrue(self.run_close(lifecycle_overrides={"_worktree_at": {"head": HEAD}}))
        Path(self.proof["target_path"]).mkdir()
        self.assertTrue(self.run_close())

    def test_registry_and_evidence_cannot_reassign_or_reuse_source_authority(self):
        for field, value in (
            ("source_unavailable_ref", self.claim["writer_ref"]),
            ("source_unavailable_ref", self.proof["source_task_ref"]),
            ("owner_authorization_ref", "session:other-owner"),
            ("cleanup_task_ref", "session:other-cleanup-writer"),
            ("lifecycle_script_blob", BASE),
        ):
            with self.subTest(field=field, value=value):
                old = self.proof[field]
                self.proof[field] = value
                self.completion["retirements"][0][field] = value
                self.assertTrue(self.run_close())
                self.proof[field] = old
                self.completion["retirements"][0][field] = old

    def test_closed_target_original_writer_and_current_completion_review_required(self):
        self.target_claim["state"] = "paused"
        self.assertTrue(self.run_close())
        self.target_claim["state"] = "closed"
        self.target_claim["writer_ref"] = "session:other-source"
        self.assertTrue(self.run_close())
        self.target_claim["writer_ref"] = self.proof["source_task_ref"]
        self.review["reviewer_ref"] = self.claim["writer_ref"]
        self.assertTrue(self.run_close())


class RepairAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'candidate'
        self.root.mkdir()
        self.manifest_path = Path(self.temp.name) / 'approval.json'
        self.package = 'PS-REPAIR-TEST-001'
        self.claim_path = preflight.claim_relative_path(self.package)
        self.files = {self.claim_path: 'a' * 40, '.gitleaks.toml': 'b' * 40}
        self.args = SimpleNamespace(package=self.package, intent='repair-activate',
            task_ref='agent:cursor/actual-receiver', owner_authorization_ref='session:pete/decision',
            repair_manifest=str(self.manifest_path), candidate_sha='c' * 40, candidate_worktree='')
        self.facts = SimpleNamespace(origin_main='d' * 40, head='c' * 40,
            branch='work/2026-09-06-delivery-activation-repair-test',
            branch_paths=tuple(self.files), worktree_paths=(), main_paths=())
        self.claim = dict(package=self.package, writer_ref=self.args.task_ref,
            owner_outcome_ref=self.args.owner_authorization_ref, delivery_path='Protected',
            review_requirement='independent', repository_authority='through_merge',
            production_authority='withheld',
            surfaces=sorted(set(self.files) | set(preflight.control_relative_paths(self.package))))
        self.manifest = {'authorization': dict(schema_version=1, package=self.package,
            writer_ref=self.args.task_ref, owner_authorization_ref=self.args.owner_authorization_ref,
            failure_evidence_ref='task:ci/build-2515', base_sha=self.facts.origin_main,
            branch=self.facts.branch, files=dict(self.files)),
            'precommit_review': dict(reviewer_ref='agent:claude/independent-reviewer',
                review_ref='session:review/precommit', result='pass', authorization_sha256=''),
            'merge_review': None}
        self.sign_manifest()

    def sign_manifest(self):
        self.manifest['precommit_review']['authorization_sha256'] = hashlib.sha256(
            json.dumps(self.manifest['authorization'], sort_keys=True,
                separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

    def git(self, root, *args):
        if args[0] == 'rev-parse':
            return self.files[args[1].split(':', 1)[1]]
        if args[0] == 'ls-tree':
            return '100644 blob ' + self.files[args[-1]] + '\t' + args[-1]
        raise AssertionError(args)

    def evaluate(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
        with patch.object(preflight, '_git', side_effect=self.git):
            return preflight.validate_repair_admission(self.root, self.args, self.facts, self.claim)

    def test_admits_exact_independent_owner_selected_repair_without_claiming_ci(self):
        facts, errors = self.evaluate()
        self.assertEqual([], errors)
        self.assertIn('not verified', facts['server_ci'])

    def test_classifier_repair_files_require_the_same_bound_independent_review(self):
        for filename in ('scripts/classify_delivery_change.py',
                         'tests/test_delivery_change_classification.py'):
            with self.subTest(filename=filename):
                self.files = {self.claim_path: 'a' * 40, filename: 'b' * 40}
                self.manifest['authorization']['files'] = dict(self.files)
                self.facts.branch_paths = tuple(self.files)
                self.claim['surfaces'] = sorted(set(self.files) |
                    set(preflight.control_relative_paths(self.package)))
                self.sign_manifest()
                self.assertEqual([], self.evaluate()[1])
                self.manifest['precommit_review']['authorization_sha256'] = '0' * 64
                self.assertTrue(any('precommit' in error for error in self.evaluate()[1]))

    def test_write_only_activation_passes_direct_and_full_admission(self):
        self.claim['repository_authority'] = 'write_only'
        self.assertEqual([], self.evaluate()[1])
        self.assertEqual([], self.evaluate_full()[1])

    def test_write_only_merge_fails_even_with_exact_independent_receipt(self):
        self.claim['repository_authority'] = 'write_only'
        self.args.intent = 'repair-merge'
        self.manifest['merge_review'] = self.receipt()
        for errors in (self.evaluate()[1], self.evaluate_full()[1]):
            self.assertTrue(any('exact owner-selected Protected independent claim' in e for e in errors), errors)

    def test_through_merge_activation_and_merge_remain_valid(self):
        for intent in ('repair-activate', 'repair-merge'):
            with self.subTest(intent=intent):
                self.args.intent = intent
                self.manifest['merge_review'] = self.receipt() if intent == 'repair-merge' else None
                self.assertEqual([], self.evaluate()[1])
                self.assertEqual([], self.evaluate_full()[1])

    def test_write_only_activation_preserves_other_claim_gates(self):
        self.claim['repository_authority'] = 'write_only'
        original = copy.deepcopy(self.claim)
        for field, value in (('writer_ref', 'agent:other/writer'),
                             ('owner_outcome_ref', 'session:other/owner'),
                             ('delivery_path', 'Standard'),
                             ('review_requirement', 'self'),
                             ('production_authority', 'allowed'),
                             ('repository_authority', 'unrestricted'), ('repository_authority', [])):
            with self.subTest(field=field):
                self.claim = dict(original, **{field: value})
                self.assertTrue(any('exact owner-selected Protected independent claim' in e for e in self.evaluate()[1]))

    def test_write_only_activation_preserves_manifest_schema_owner_and_review_binding(self):
        self.claim['repository_authority'] = 'write_only'
        baseline = copy.deepcopy(self.manifest)
        cases = [('extra_authorization_key', lambda m: m['authorization'].update(extra=True)),
                 ('different_owner', lambda m: m['authorization'].update(owner_authorization_ref='session:other/owner')),
                 ('different_file', lambda m: m['authorization']['files'].update({'.gitleaks.toml': 'f' * 40})),
                 ('stale_review', lambda m: m['precommit_review'].update(authorization_sha256='0' * 64)),
                 ('self_review', lambda m: m['precommit_review'].update(reviewer_ref=self.args.task_ref))]
        for label, mutate in cases:
            with self.subTest(case=label):
                self.manifest = copy.deepcopy(baseline)
                mutate(self.manifest)
                self.assertTrue(self.evaluate()[1])

    def test_all_runtimes_use_same_role_predicates(self):
        for runtime in ('codex', 'cursor', 'claude', 'another-runtime'):
            with self.subTest(runtime=runtime):
                ref = 'agent:' + runtime + '/actual-receiver'
                self.args.task_ref = self.claim['writer_ref'] = ref
                self.manifest['authorization']['writer_ref'] = ref
                self.sign_manifest()
                self.assertEqual([], self.evaluate()[1])

    def test_rejects_unapproved_blob_change(self):
        self.files['.gitleaks.toml'] = 'e' * 40
        self.assertTrue(any('blob' in e for e in self.evaluate()[1]))

    def test_rejects_changed_owner_manifest_without_new_review(self):
        self.manifest['authorization']['failure_evidence_ref'] = 'task:other/failure'
        self.assertTrue(any('precommit' in e for e in self.evaluate()[1]))

    def test_rejects_self_review(self):
        self.manifest['precommit_review']['reviewer_ref'] = self.args.task_ref
        self.assertTrue(any('precommit' in e for e in self.evaluate()[1]))

    def test_rejects_new_pipeline_or_product_surface_even_with_matching_hashes(self):
        for path in ('azure-pipelines.yml', 'app.py'):
            with self.subTest(path=path):
                self.files[path] = 'f' * 40
                self.manifest['authorization']['files'] = dict(self.files)
                self.facts.branch_paths = tuple(self.files)
                self.claim['surfaces'].append(path)
                self.sign_manifest()
                self.assertTrue(any('unsupported surface' in e for e in self.evaluate()[1]))

    def test_rejects_scope_reservation_beyond_manifest(self):
        self.claim['surfaces'].append('app.py')
        self.assertTrue(any('reserve exactly' in e for e in self.evaluate()[1]))

    def test_rejects_another_claim(self):
        self.files[preflight.claim_relative_path('PS-OTHER-001')] = 'f' * 40
        self.manifest['authorization']['files'] = dict(self.files)
        self.sign_manifest()
        self.assertTrue(any('unsupported surface' in e for e in self.evaluate()[1]))

    def test_rejects_uncommitted_or_divergent_candidate(self):
        self.facts.worktree_paths = ('extra.txt',)
        self.assertTrue(any('clean tree' in e for e in self.evaluate()[1]))
        self.facts.worktree_paths = ()
        self.facts.main_paths = ('main-moved.txt',)
        self.assertTrue(any('divergent' in e for e in self.evaluate()[1]))

    def test_rejects_symlink_file_mode(self):
        original = self.git
        def symlink(root, *args):
            return original(root, *args).replace('100644', '120000')
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
        with patch.object(preflight, '_git', side_effect=symlink):
            errors = preflight.validate_repair_admission(self.root, self.args, self.facts, self.claim)[1]
        self.assertTrue(any('mode' in e for e in errors))

    def receipt(self):
        return dict(schema_version=1, package=self.package, candidate_sha=self.facts.head,
            review_type='independent', reviewer_ref='agent:independent/exact-commit',
            result='pass', reviewed_at='2026-09-06T12:00:00Z', findings=[],
            evidence_ref='session:review/exact-commit')

    def test_merge_requires_exact_reviewed_commit(self):
        self.args.intent = 'repair-merge'
        self.assertTrue(self.evaluate()[1])
        self.manifest['merge_review'] = self.receipt()
        self.assertEqual([], self.evaluate()[1])
        self.manifest['merge_review']['candidate_sha'] = 'f' * 40
        self.assertTrue(any('exact HEAD' in e for e in self.evaluate()[1]))

    def test_rejects_failed_review_and_production_authority(self):
        self.args.intent = 'repair-merge'
        self.manifest['merge_review'] = self.receipt()
        self.manifest['merge_review']['result'] = 'revise'
        self.claim['production_authority'] = 'allowed'
        self.assertGreaterEqual(len(self.evaluate()[1]), 2)

    def test_ordinary_activation_still_is_a_distinct_mode(self):
        parser = preflight.build_parser()
        for intent in ('activate', 'repair-activate', 'repair-merge'):
            self.assertEqual(intent, parser.parse_args(['--package', self.package,
                '--intent', intent]).intent)

    def evaluate_full(self, *, registry='initialized', other_claim=None):
        value = claim(package=self.package, **{
            key: val for key, val in self.claim.items() if key != 'package'})
        repo_facts = facts(**vars(self.facts))
        request = args(self.args.intent, **{
            key: val for key, val in vars(self.args).items() if key != 'intent'},
            lease_token='opaque-current-token')
        value['activated_from_main'] = self.facts.origin_main
        candidate = {self.package.casefold(): value}
        authority = {}
        if other_claim:
            authority[other_claim['package'].casefold()] = other_claim
            candidate.update(authority)
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
        with patch.object(preflight, '_git', side_effect=self.git):
            return EvaluationTests().run_evaluate(request, value, repo_facts,
                origin_claims=authority, candidate_claims=candidate,
                local=patch.object(preflight, 'evaluate_local_worktree_context',
                    return_value=({'registry': registry}, [], [])))

    def test_full_admission_preserves_ordinary_one_claim_only_and_collision_gates(self):
        self.assertEqual([], self.evaluate_full()[1])
        self.args.intent = 'activate'
        self.assertTrue(any('activation must change only' in e for e in self.evaluate_full()[1]))
        self.args.intent = 'repair-activate'
        other = claim(package='PS-OTHER-001', number=2,
            surfaces=claimed_surfaces('PS-OTHER-001', '.gitleaks.toml'))
        self.assertTrue(any('collision' in e for e in self.evaluate_full(other_claim=other)[1]))

    def test_full_admission_rejects_ci_or_uninitialized_registry_bypass(self):
        for state in ('ci_skipped', 'not_initialized', 'test_stub'):
            with self.subTest(state=state):
                self.assertTrue(any('initialized receiver-leased' in e
                                    for e in self.evaluate_full(registry=state)[1]))

    def test_full_merge_reuses_activation_gates_and_requires_exact_receipt(self):
        self.args.intent = 'repair-merge'
        self.assertTrue(any('receipt' in e for e in self.evaluate_full()[1]))
        self.manifest['merge_review'] = self.receipt()
        self.assertEqual([], self.evaluate_full()[1])


if __name__ == "__main__":
    unittest.main()
