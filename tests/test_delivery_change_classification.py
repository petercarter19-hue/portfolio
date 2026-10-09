"""Adversarial immutable-target tests for administrative CI classification."""

from __future__ import annotations

import json
import os
import copy
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts.classify_delivery_change import (
    CLAIMS,
    ROOT,
    TRUSTED_BLOBS,
    Context,
    Decision,
    InvalidChange,
    azure_main_tip,
    _transition,
    classify,
    main,
    target_validator,
    verify_coherence,
)


def command(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


class RepositoryFixture:
    def __init__(self, *, target_has_classifier: bool = True) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        command(self.root, "init", "-b", "main")
        command(self.root, "config", "user.name", "CI Fixture")
        command(self.root, "config", "user.email", "ci@example.invalid")
        for path in TRUSTED_BLOBS:
            if path == "scripts/classify_delivery_change.py" and not target_has_classifier:
                continue
            self.write(path, (ROOT / path).read_bytes())
        command(self.root, "add", ".")
        command(self.root, "commit", "-m", "trusted target")
        self.target = command(self.root, "rev-parse", "HEAD")
        command(self.root, "checkout", "-b", "work/test-claim")

    def write(self, path: str, body: str | bytes) -> None:
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body.encode("utf-8") if isinstance(body, str) else body)

    def claim(self, package: str = "PS-CI-SYNTHETIC-001") -> dict:
        stem = f"{CLAIMS}/{package}"
        return {
            "schema_version": 1,
            "package": package,
            "state": "active",
            "outcome": "Synthetic claim-only activation for immutable-target CI testing.",
            "assignment": "implementation",
            "writer_ref": "session:00000000-0000-0000-0000-000000000001",
            "branch": "work/2026-09-16-ci-synthetic-001",
            "delivery_path": "Protected",
            "repository_authority": "through_merge",
            "production_authority": "withheld",
            "activated_from_main": self.target,
            "owner_outcome_ref": "session:owner/synthetic-ci-proof",
            "surfaces": [
                stem + ".json", stem.replace("lane_claims/", "lane_claims/evidence/") + ".md",
                stem.replace("lane_claims/", "lane_claims/receipts/") + ".json",
                "tests/test_delivery_change_classification.py",
            ],
            "evidence_surfaces": [stem.replace("lane_claims/", "lane_claims/evidence/") + ".md"],
            "domains": ["testing:ci:synthetic-claim"],
            "review_requirement": "independent",
            "handoff": None,
            "checkpoint_sha": None,
            "merged_sha": None,
            "closed_at": None,
        }

    def finish(self, claims: list[dict], extras: dict[str, str] | None = None) -> tuple[Context, str]:
        for item in claims:
            self.write(f"{CLAIMS}/{item['package']}.json", json.dumps(item) + "\n")
        for path, body in (extras or {}).items():
            self.write(path, body)
        command(self.root, "add", "-A")
        command(self.root, "commit", "-m", "candidate source")
        source = command(self.root, "rev-parse", "HEAD")
        command(self.root, "checkout", "main")
        command(self.root, "merge", "--no-ff", "--no-edit", "work/test-claim")
        merge = command(self.root, "rev-parse", "HEAD")
        ctx = Context(
            "PullRequest", "refs/pull/87/merge", merge, source,
            "refs/heads/main", "False", "87",
            "https://dev.azure.com/example/project/_git/repository",
            "https://example@dev.azure.com/example/project/_git/repository",
            "https://dev.azure.com/example/", "project", "0" * 8 + "-0000-0000-0000-000000000000",
        )
        return ctx, source

    def cleanup(self) -> None:
        self.temp.cleanup()


class RepairChangeClassificationTests(unittest.TestCase):
    def fixture(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.cleanup)
        return fixture

    def repair_claim(self, fixture, paths):
        claim = fixture.claim()
        claim["surfaces"] = claim["surfaces"][:3] + list(paths)
        return claim

    def decision(self, fixture, claim, extras):
        ctx, _ = fixture.finish([claim], extras)
        return classify(fixture.root, ctx, target_tip=lambda _: fixture.target)

    def advance_target(self, fixture, files):
        command(fixture.root, "checkout", "main")
        for path, body in files.items():
            fixture.write(path, body)
        command(fixture.root, "add", "-A")
        command(fixture.root, "commit", "-m", "accepted target setup")
        fixture.target = command(fixture.root, "rev-parse", "HEAD")
        command(fixture.root, "checkout", "work/test-claim")
        command(fixture.root, "merge", "--ff-only", "main")

    def test_scanner_repair_runs_full_for_each_supported_caller(self):
        for caller in ("session:00000000-0000-0000-0000-000000000001",
                       "agent:claude/actual-writer", "agent:other-runtime/writer"):
            with self.subTest(caller=caller):
                fixture = self.fixture()
                extras = {".gitleaks.toml": "# bounded scanner repair\n",
                          "tests/test_operational_readiness.py": "# scanner regression\n"}
                claim = self.repair_claim(fixture, extras)
                claim["writer_ref"] = caller
                decision = self.decision(fixture, claim, extras)
                self.assertEqual("full", decision.disposition)
                self.assertEqual("bounded required-check repair activation", decision.reason)
                self.assertEqual(fixture.target, decision.target)
                verify_coherence(decision.record("BuildJob"),
                                 decision.record("InterviewStudioBrowserCI"), decision)

    def test_classifier_and_test_only_repairs_use_full_not_control_shortcut(self):
        for paths in (("scripts/classify_delivery_change.py",
                       "tests/test_delivery_change_classification.py"),
                      ("tests/test_operational_readiness.py",)):
            with self.subTest(paths=paths):
                fixture = self.fixture()
                extras = {path: "# bounded gate repair\n" for path in paths}
                self.assertEqual("full", self.decision(
                    fixture, self.repair_claim(fixture, paths), extras).disposition)

    def test_candidate_validator_cannot_execute_or_expand_target_repair_boundary(self):
        fixture = self.fixture()
        marker = fixture.root / "candidate_validator_executed"
        candidate = ("from pathlib import Path\n"
                     f"Path({str(marker)!r}).write_text('ran')\n"
                     "REPAIR_SURFACES = frozenset({'app.py'})\n")
        extras = {"scripts/delivery_preflight.py": candidate, "app.py": "# product\n"}
        with self.assertRaises(InvalidChange):
            self.decision(fixture, self.repair_claim(fixture, extras), extras)
        self.assertFalse(marker.exists())

    def test_weakened_stale_or_nonfresh_repair_claim_is_rejected(self):
        cases = (
            {"delivery_path": "Routine", "review_requirement": "self"},
            {"repository_authority": "unrestricted"},
            {"production_authority": "allowed"},
            {"activated_from_main": "a" * 40},
            {"state": "paused", "checkpoint_sha": "a" * 40},
            {"handoff": {"from_ref": "agent:old", "to_ref": "agent:new"}},
            {"scope_release": None},
            {"checkpoint_sha": "a" * 40},
            {"owner_outcome_ref": "session:00000000-0000-0000-0000-000000000001"},
        )
        for change in cases:
            with self.subTest(change=change):
                fixture = self.fixture()
                extras = {".gitleaks.toml": "# scanner repair\n"}
                claim = self.repair_claim(fixture, extras)
                claim.update(change)
                with self.assertRaises(InvalidChange):
                    self.decision(fixture, claim, extras)

    def test_surplus_missing_or_broad_reservation_is_rejected(self):
        for surfaces in ((".gitleaks.toml", "START_HERE.md"), (), ("scripts",)):
            with self.subTest(surfaces=surfaces):
                fixture = self.fixture()
                with self.assertRaises(InvalidChange):
                    self.decision(fixture, self.repair_claim(fixture, surfaces),
                                  {".gitleaks.toml": "# repair\n"})

    def test_product_pipeline_or_evidence_tail_cannot_join_repair(self):
        for forbidden in ("app.py", "azure-pipelines.yml",
                          f"{CLAIMS}/receipts/PS-CI-SYNTHETIC-001.json",
                          f"{CLAIMS}/evidence/PS-CI-SYNTHETIC-001.md"):
            with self.subTest(forbidden=forbidden):
                fixture = self.fixture()
                extras = {".gitleaks.toml": "# repair\n", forbidden: "{}\n"}
                claim = self.repair_claim(fixture, (".gitleaks.toml",))
                if forbidden in ("app.py", "azure-pipelines.yml"):
                    claim["surfaces"].append(forbidden)
                with self.assertRaises(InvalidChange):
                    self.decision(fixture, claim, extras)

    def test_existing_claim_modification_cannot_become_repair_activation(self):
        fixture = self.fixture()
        claim = self.repair_claim(fixture, (".gitleaks.toml",))
        self.advance_target(fixture, {f"{CLAIMS}/{claim['package']}.json": json.dumps(claim)})
        claim.update(activated_from_main=fixture.target, outcome="Changed existing claim.")
        with self.assertRaises(InvalidChange):
            self.decision(fixture, claim, {".gitleaks.toml": "# repair\n"})

    def test_full_target_and_candidate_claim_sets_still_reject_collisions(self):
        for collision in ("path", "domain", "branch", "invalid_target"):
            with self.subTest(collision=collision):
                fixture = self.fixture()
                prior = fixture.claim("PS-EXISTING-001")
                prior["branch"] = "work/existing"
                prior["domains"] = ["testing:existing"]
                prior["surfaces"] = prior["surfaces"][:3] + ["unrelated.py"]
                if collision == "path":
                    prior["surfaces"][-1] = ".gitleaks.toml"
                elif collision == "domain":
                    prior["domains"] = ["testing:ci"]
                elif collision == "branch":
                    prior["branch"] = fixture.claim()["branch"]
                else:
                    prior["unknown_field"] = True
                self.advance_target(fixture, {f"{CLAIMS}/{prior['package']}.json": json.dumps(prior)})
                with self.assertRaises(InvalidChange):
                    self.decision(fixture, self.repair_claim(fixture, (".gitleaks.toml",)),
                                  {".gitleaks.toml": "# repair\n"})

    def test_multiple_or_malformed_or_misnamed_claims_fail_in_mixed_delta(self):
        for kind in ("multiple", "malformed", "misnamed"):
            with self.subTest(kind=kind):
                fixture = self.fixture()
                claim = self.repair_claim(fixture, (".gitleaks.toml",))
                extras = {".gitleaks.toml": "# repair\n"}
                if kind == "multiple":
                    extras[f"{CLAIMS}/PS-OTHER-001.json"] = json.dumps(fixture.claim("PS-OTHER-001"))
                elif kind == "malformed":
                    extras[f"{CLAIMS}/{claim['package']}.json"] = '{"package": "duplicate", "package": "other"}'
                else:
                    extras[f"{CLAIMS}/PS-WRONG-NAME-001.json"] = json.dumps(claim)
                    claim = None
                ctx, _ = fixture.finish([claim] if claim else [], extras)
                with self.assertRaises(InvalidChange):
                    classify(fixture.root, ctx, target_tip=lambda _: fixture.target)

    def test_deleted_renamed_and_changed_file_modes_are_rejected(self):
        for kind in ("delete", "rename", "executable", "claim_executable", "prior_executable"):
            with self.subTest(kind=kind):
                fixture = self.fixture()
                # These fixtures set tree modes through the index. Do not let
                # POSIX working-file permissions undo that setup at add -A.
                command(fixture.root, "config", "core.filemode", "false")
                if kind == "prior_executable":
                    command(fixture.root, "checkout", "main")
                    command(fixture.root, "update-index", "--chmod=+x", ".gitleaks.toml")
                    command(fixture.root, "commit", "-m", "accepted executable fixture")
                    fixture.target = command(fixture.root, "rev-parse", "HEAD")
                    command(fixture.root, "checkout", "work/test-claim")
                    command(fixture.root, "merge", "--ff-only", "main")
                claim = self.repair_claim(fixture, (".gitleaks.toml", "START_HERE.md"))
                extras = {"START_HERE.md": "# gate documentation\n"}
                if kind == "rename":
                    command(fixture.root, "mv", ".gitleaks.toml", "START_HERE.md")
                elif kind == "delete":
                    command(fixture.root, "rm", ".gitleaks.toml")
                else:
                    extras[".gitleaks.toml"] = "# repair\n"
                if kind in ("executable", "claim_executable", "prior_executable"):
                    fixture.write(f"{CLAIMS}/{claim['package']}.json", json.dumps(claim))
                    command(fixture.root, "add", "-A")
                    mode_path = f"{CLAIMS}/{claim['package']}.json" if kind == "claim_executable" else ".gitleaks.toml"
                    command(fixture.root, "update-index", "--chmod=-x" if kind == "prior_executable" else "--chmod=+x", mode_path)
                    command(fixture.root, "commit", "-m", "mode change")
                ctx, _ = fixture.finish([claim], extras)
                if kind in ("executable", "claim_executable", "prior_executable"):
                    expected_mode = "100644" if kind == "prior_executable" else "100755"
                    self.assertEqual(expected_mode, command(
                        fixture.root, "ls-tree", ctx.merge, "--", mode_path).split()[0])
                    if kind == "prior_executable":
                        self.assertEqual("100755", command(
                            fixture.root, "ls-tree", fixture.target, "--", mode_path).split()[0])
                with self.assertRaises(InvalidChange):
                    classify(fixture.root, ctx, target_tip=lambda _: fixture.target)


class DeliveryChangeClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = RepositoryFixture()
        self.addCleanup(self.fixture.cleanup)

    def test_one_plain_activation_on_immutable_target_is_eligible(self):
        ctx, source = self.fixture.finish([self.fixture.claim()])
        decision = classify(self.fixture.root, ctx, target_tip=lambda _: self.fixture.target)
        self.assertEqual("control_only_validated", decision.disposition)
        self.assertEqual("activation", decision.reason)
        self.assertEqual((source, self.fixture.target, ctx.merge),
                         (decision.source, decision.target, decision.merge))
        self.assertEqual(64, len(decision.classifier_sha256))

    def test_ordinary_transition_field_whitelist_and_tracked_extension(self):
        before = self.fixture.claim()
        authorized = copy.deepcopy(before)
        before["repository_authority"] = "write_only"
        authorized["owner_outcome_ref"] = "session:owner/new-authorization"
        with target_validator(self.fixture.root, self.fixture.target) as validator:
            self.assertEqual("authorize", _transition(self.fixture.target, "", before,
                             authorized, self.fixture.root, validator))
        before = self.fixture.claim()
        extended = copy.deepcopy(before)
        extended["surfaces"].append("scripts/classify_delivery_change.py")
        with target_validator(self.fixture.root, self.fixture.target) as validator:
            self.assertEqual("extend-surfaces", _transition(self.fixture.target, "", before,
                             extended, self.fixture.root, validator))
        extended["surfaces"][-1] = "scripts/untracked.py"
        with target_validator(self.fixture.root, self.fixture.target) as validator:
            with self.assertRaises(InvalidChange):
                _transition(self.fixture.target, "", before, extended, self.fixture.root, validator)
        paused = copy.deepcopy(before)
        paused.update(state="paused", checkpoint_sha=self.fixture.target)
        with target_validator(self.fixture.root, self.fixture.target) as validator:
            self.assertEqual("pause", _transition(self.fixture.target, "", before,
                             paused, self.fixture.root, validator))
        resumed = copy.deepcopy(paused)
        resumed["state"] = "active"
        with target_validator(self.fixture.root, self.fixture.target) as validator:
            self.assertEqual("resume", _transition(self.fixture.target, "", paused,
                             resumed, self.fixture.root, validator))
        malicious = copy.deepcopy(before)
        malicious["writer_ref"] = "session:other"
        with target_validator(self.fixture.root, self.fixture.target) as validator:
            with self.assertRaises(InvalidChange):
                _transition(self.fixture.target, "", before, malicious, self.fixture.root, validator)

    def test_claim_plus_product_or_receipt_is_illegal_control_delta(self):
        for extras in ({"app.py": "product change\n"},
                       {f"{CLAIMS}/receipts/PS-CI-SYNTHETIC-001.json": "{}\n"}):
            with self.subTest(extras=extras):
                fixture = RepositoryFixture()
                self.addCleanup(fixture.cleanup)
                ctx, _ = fixture.finish([fixture.claim()], extras)
                with self.assertRaises(InvalidChange):
                    classify(fixture.root, ctx, target_tip=lambda _: fixture.target)

    def test_product_only_unknown_delta_runs_full(self):
        ctx, _ = self.fixture.finish([], {"app.py": "product change\n"})
        self.assertEqual("full", classify(self.fixture.root, ctx,
                         target_tip=lambda _: self.fixture.target).disposition)

    def test_candidate_scripts_init_cannot_run_for_product_or_mixed_claim(self):
        for claim_only in (False, True):
            with self.subTest(claim_only=claim_only):
                fixture = RepositoryFixture()
                self.addCleanup(fixture.cleanup)
                marker = fixture.root / "candidate_init_ran"
                attacker = ("from pathlib import Path\n"
                            f"Path({str(marker)!r}).write_text('ran')\n"
                            "raise SystemExit(0)\n")
                extras = {"scripts/__init__.py": attacker}
                if not claim_only:
                    extras["app.py"] = "product change\n"
                ctx, _ = fixture.finish([fixture.claim()] if claim_only else [], extras)
                if claim_only:
                    with self.assertRaises(InvalidChange):
                        classify(fixture.root, ctx, target_tip=lambda _: fixture.target)
                else:
                    self.assertEqual("full", classify(fixture.root, ctx,
                                     target_tip=lambda _: fixture.target).disposition)
                self.assertFalse(marker.exists(), "candidate package initializer executed")

    def test_candidate_validator_change_and_product_runs_full_without_execution(self):
        ctx, _ = self.fixture.finish([], {
            "scripts/delivery_preflight.py": "raise SystemExit(0)\n",
            "app.py": "product change\n",
        })
        self.assertEqual("full", classify(self.fixture.root, ctx,
                         target_tip=lambda _: self.fixture.target).disposition)

    def test_documented_org_level_source_uri_matches_same_repo_identity(self):
        ctx, _ = self.fixture.finish([self.fixture.claim()])
        documented = replace(ctx,
            source_repo_uri="https://dev.azure.com/example/_git/repository")
        self.assertEqual("control_only_validated", classify(self.fixture.root, documented,
                         target_tip=lambda _: self.fixture.target).disposition)
        for changed in (
            replace(documented, repository_id=""),
            replace(documented, repository_id="-" * 36),
            replace(documented, source_repo_uri="https://dev.azure.com/other/_git/repository"),
            replace(documented, source_repo_uri="https://dev.azure.com/example/_git/other"),
            replace(ctx, source_repo_uri="https://dev.azure.com/example/other/_git/repository"),
        ):
            with self.subTest(changed=changed):
                self.assertEqual("full", classify(self.fixture.root, changed,
                                 target_tip=lambda _: self.fixture.target).disposition)

    def test_changed_validator_or_classifier_cannot_certify_its_own_fast_path(self):
        for guard in ("scripts/delivery_preflight.py", "scripts/worktree_lifecycle.py",
                      "scripts/classify_delivery_change.py", "azure-pipelines.yml",
                      ".gitleaks.toml", "docs/governance/CURRENT_LANES.json"):
            with self.subTest(guard=guard):
                fixture = RepositoryFixture()
                self.addCleanup(fixture.cleanup)
                ctx, _ = fixture.finish([fixture.claim()], {guard: "tampered\n"})
                with self.assertRaises(InvalidChange):
                    classify(fixture.root, ctx, target_tip=lambda _: fixture.target)

    def test_fork_wrong_target_drift_and_source_mismatch_go_full(self):
        ctx, _ = self.fixture.finish([self.fixture.claim()])
        cases = (
            (replace(ctx, fork="True"), self.fixture.target),
            (replace(ctx, target_branch="refs/heads/other"), self.fixture.target),
            (replace(ctx, source="a" * 40), self.fixture.target),
            (replace(ctx, source_repo_uri="https://elsewhere.invalid/repo"), self.fixture.target),
            (ctx, "b" * 40),
        )
        for case, tip in cases:
            with self.subTest(case=case, tip=tip):
                self.assertEqual("full", classify(self.fixture.root, case,
                    target_tip=lambda _: tip).disposition)

    def test_duplicate_unknown_field_or_illegal_activation_fails_not_docs_fallback(self):
        for bad in ("{\"package\":\"X\",\"package\":\"Y\"}",
                    json.dumps({**self.fixture.claim(), "state": "paused"}),
                    json.dumps({**self.fixture.claim(), "self_certified": True})):
            with self.subTest(bad=bad[:40]):
                fixture = RepositoryFixture()
                self.addCleanup(fixture.cleanup)
                path = f"{CLAIMS}/PS-CI-SYNTHETIC-001.json"
                fixture.write(path, bad)
                ctx, _ = fixture.finish([], {})
                with self.assertRaises(InvalidChange):
                    classify(fixture.root, ctx, target_tip=lambda _: fixture.target)

    def test_multi_claim_transition_fails_control_validation(self):
        first = self.fixture.claim()
        second = self.fixture.claim("PS-CI-SYNTHETIC-002")
        second["domains"] = ["testing:ci:second-synthetic-claim"]
        second["branch"] = "work/2026-09-16-ci-synthetic-002"
        second["surfaces"][-1] = "tests/test_second_synthetic_claim.py"
        ctx, _ = self.fixture.finish([first, second])
        with self.assertRaises(InvalidChange):
            classify(self.fixture.root, ctx, target_tip=lambda _: self.fixture.target)

    def test_missing_target_classifier_is_full(self):
        fixture = RepositoryFixture(target_has_classifier=False)
        self.addCleanup(fixture.cleanup)
        ctx, _ = fixture.finish([fixture.claim()], {
            "scripts/classify_delivery_change.py": (ROOT / "scripts/classify_delivery_change.py").read_text(encoding="utf-8")
        })
        self.assertEqual("full", classify(fixture.root, ctx,
                         target_tip=lambda _: fixture.target).disposition)

    def test_guard_change_and_claim_is_invalid_not_self_certified(self):
        self.fixture.write("scripts/classify_delivery_change.py", "temporary\n")
        command(self.fixture.root, "add", ".")
        command(self.fixture.root, "commit", "-m", "source changed")
        ctx, _ = self.fixture.finish([self.fixture.claim()])
        with self.assertRaises(InvalidChange):
            classify(self.fixture.root, ctx, target_tip=lambda _: self.fixture.target)

    def test_coherence_refuses_missing_job_mismatch_or_drift(self):
        decision = Decision("control_only_validated", "activation", "a" * 40,
                            "b" * 40, "c" * 40, "d" * 64)
        build = decision.record("BuildJob")
        browser = decision.record("InterviewStudioBrowserCI")
        verify_coherence(build, browser, decision)
        with self.assertRaises(InvalidChange):
            verify_coherence(build, build, decision)
        with self.assertRaises(InvalidChange):
            verify_coherence(build, browser, replace(decision, target="e" * 40))
        with self.assertRaises(InvalidChange):
            verify_coherence(build, {**browser, "disposition": "full"}, decision)

    def test_bootstrap_full_artifacts_cohere_on_non_pr_main_run(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"BUILD_REASON": "IndividualCI"}):
            build, browser = Path(folder) / "build.json", Path(folder) / "browser.json"
            for job, path in (("BuildJob", build), ("InterviewStudioBrowserCI", browser)):
                self.assertEqual(0, main(["classify", "--force-full", "--no-vso",
                                          "--job", job, "--output", str(path)]))
            self.assertEqual(0, main(["verify", "--build", str(build),
                                      "--browser", str(browser)]))

    def test_initial_pr_rollout_bootstrap_is_full_without_live_target_api(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"BUILD_REASON": "PullRequest"}):
            build, browser = Path(folder) / "build.json", Path(folder) / "browser.json"
            for job, path in (("BuildJob", build), ("InterviewStudioBrowserCI", browser)):
                self.assertEqual(0, main(["classify", "--force-full", "--no-vso",
                                          "--job", job, "--output", str(path)]))
            self.assertEqual(0, main(["verify", "--bootstrap-full", "--build", str(build),
                                      "--browser", str(browser)]))

    def test_bootstrap_cli_cannot_import_candidate_shadow_of_stdlib(self):
        marker = self.fixture.root / "candidate_json_ran"
        self.fixture.write("scripts/json.py", "from pathlib import Path\n"
                           f"Path({str(marker)!r}).write_text('ran')\n"
                           "raise SystemExit(0)\n")
        output = self.fixture.root / "bootstrap-disposition.json"
        command_line = [sys.executable, "-I", "-B",
                        str(self.fixture.root / "scripts/classify_delivery_change.py"),
                        "classify", "--force-full", "--no-vso",
                        "--job", "BuildJob", "--output", str(output)]
        result = subprocess.run(command_line, cwd=self.fixture.root, capture_output=True,
                                text=True, env={**os.environ, "BUILD_REASON": "PullRequest",
                                                "BUILD_SOURCESDIRECTORY": str(self.fixture.root)})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("full", json.loads(output.read_text(encoding="utf-8"))["disposition"])
        self.assertFalse(marker.exists(), "candidate module shadow executed")

    def test_pipeline_classifier_and_verifier_launches_are_isolated(self):
        pipeline = (ROOT / "azure-pipelines.yml").read_text(encoding="utf-8")
        self.assertEqual(3, pipeline.count(
            'python -I -B "$(Agent.TempDirectory)/trusted-delivery-classifier.py"'))
        self.assertEqual(3, pipeline.count("python -I -B scripts/classify_delivery_change.py"))
        self.assertNotIn('python -B "$(Agent.TempDirectory)/trusted-delivery-classifier.py"', pipeline)
        self.assertNotIn("python -B scripts/classify_delivery_change.py", pipeline)

    def test_azure_main_ref_requires_exact_single_reference(self):
        ctx = Context("PullRequest", "refs/pull/1/merge", "a" * 40, "b" * 40,
                      "refs/heads/main", "False", "1", "https://example.invalid/repo",
                      "https://example.invalid/repo", "https://dev.azure.com/example/",
                      "project", "00000000-0000-0000-0000-000000000000", "fake-token")
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def read(self, _limit):
                return json.dumps({"count": 1, "value": [
                    {"name": "refs/heads/main", "objectId": "b" * 40}]}).encode()
        with patch("urllib.request.urlopen", return_value=Response()) as opener:
            self.assertEqual("b" * 40, azure_main_tip(ctx))
            self.assertIn("Authorization", opener.call_args.args[0].headers)


if __name__ == "__main__":
    unittest.main()
