import copy
import io
import json
import subprocess
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import delivery_preflight as preflight


ROOT = Path(__file__).resolve().parents[1]
MAIN = "a" * 40
HEAD = "b" * 40
CANDIDATE = "c" * 40
BASE = "d" * 40


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
    }
    value.update(overrides)
    return Namespace(**value)


class NormalizationTests(unittest.TestCase):
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

    def test_impossible_closed_timestamp_is_rejected(self):
        errors = preflight.validate_claim(
            claim(
                state="closed",
                merged_sha=MAIN,
                closed_at="2026-99-99T99:99:99Z",
            )
        )
        self.assertTrue(any("UTC closed_at" in error for error in errors))


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
        ]
        patches.extend(extra_patches.values())
        entered = [item.start() for item in patches]
        try:
            return preflight.evaluate(request, root=ROOT)
        finally:
            for item in reversed(patches):
                item.stop()

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


class CurrentRepositoryTests(unittest.TestCase):
    def test_current_index_claims_and_legacy_snapshot_are_valid(self):
        current_index = preflight.load_index(ROOT)
        current_claims = preflight.load_claims(ROOT)
        self.assertEqual([], preflight.validate_index(current_index))
        self.assertEqual([], preflight.validate_claim_set(current_claims))
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


if __name__ == "__main__":
    unittest.main()
