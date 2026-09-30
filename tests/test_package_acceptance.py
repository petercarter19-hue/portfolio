"""Focused end-to-end checks for the agent-invoked package acceptance record."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import package_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "PS-ACCEPTANCE-TEST-001"
RECORD = f"docs/governance/lane_claims/evidence/{PACKAGE}.md"


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


class PackageAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self._initialize()

    def _initialize(self, *, baseline_exit=0, late_plan=False, mixed_plan=False,
                    criterion_ids=("behavior", "manual-proof")):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "Acceptance Test")
        git(self.repo, "config", "user.email", "acceptance@example.invalid")
        (self.repo / "README.md").write_text("Accepted base\n", encoding="utf-8")
        base = self._commit("Accepted main")
        git(self.repo, "update-ref", "refs/remotes/origin/main", base)
        git(self.repo, "checkout", "-qb", "work/acceptance-test")
        if late_plan:
            (self.repo / "implementation.txt").write_text(
                "Implementation predates acceptance\n", encoding="utf-8"
            )
            self._commit("Implementation before plan")
        self.record = {
            "schema_version": 1,
            "package": PACKAGE,
            "plan_sha": None,
            "baseline": [
                {"command": "python -B -m unittest tests.example", "exit_code": baseline_exit,
                 "observation": "The focused suite result was observed before implementation."}
            ],
            "criteria": [
                {"id": criterion_ids[0], "expected": "Expected behavior works.",
                 "verification": "Focused command plus observed behavior."},
                {"id": criterion_ids[1], "expected": "The operator can verify the flow.",
                 "verification": "Manual source with provenance."},
            ],
            "candidate_sha": None,
            "checks": [],
        }
        self._write()
        if mixed_plan:
            (self.repo / "implementation.txt").write_text(
                "Implementation mixed with plan\n", encoding="utf-8"
            )
        self.plan = self._commit("Predefine acceptance")
        self.record["plan_sha"] = self.plan
        (self.repo / "implementation.txt").write_text("working behavior\n", encoding="utf-8")
        self._write()
        self.candidate = self._commit("Implement candidate")
        self.record["candidate_sha"] = self.candidate
        self.record["checks"] = [
            {"criterion_id": criterion_ids[0], "result": "pass", "kind": "automated",
             "candidate_sha": self.candidate, "source_ref": "command:focused-suite",
             "observed": "The focused command exercised the behavior and all assertions passed."},
            {"criterion_id": criterion_ids[1], "result": "pass", "kind": "manual",
             "candidate_sha": self.candidate, "source_ref": "evidence:operator-note-1",
             "observed": "The operator completed the expected flow and observed the saved result.",
             "provenance": {"observer_ref": "session:reviewer", "captured_at": "2026-09-27T20:00:00Z",
                            "source_ref": "evidence:operator-note-1"}},
        ]
        self._write()
        self._commit("Record candidate proof")

    def _write(self):
        path = self.repo / RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Package acceptance\n\n```package-acceptance-json\n"
            + json.dumps(self.record, indent=2) + "\n```\n",
            encoding="utf-8",
        )

    def _commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)
        return git(self.repo, "rev-parse", "HEAD")

    def _change(self, update):
        update(self.record)
        self._write()
        self._commit("Change proof")

    def test_valid_committed_candidate_and_evidence_tail(self):
        result = acceptance.validate(self.repo, PACKAGE, self.candidate)
        self.assertEqual("pass", result["result"])
        self.assertEqual(2, result["criteria"])

    def test_underscore_identifiers_preserve_exact_plan_and_candidate_binding(self):
        self._initialize(criterion_ids=("three_empty_accounts", "manual_proof"))
        self.assertEqual("pass", acceptance.validate(self.repo, PACKAGE, self.candidate)["result"])
        self._change(lambda record: record["criteria"][0].update(id="three-empty-accounts"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "identifiers changed"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_invalid_and_duplicate_identifiers_still_refuse(self):
        for invalid in ("bad id", "Uppercase", "1first", "bad/id", "bad.id"):
            record = json.loads(json.dumps(self.record))
            record["criteria"][0]["id"] = invalid
            with self.assertRaisesRegex(acceptance.AcceptanceError, "invalid criterion id"):
                acceptance._criteria(record, PACKAGE)
        record = json.loads(json.dumps(self.record))
        record["criteria"][1]["id"] = record["criteria"][0]["id"]
        with self.assertRaisesRegex(acceptance.AcceptanceError, "duplicate criterion id"):
            acceptance._criteria(record, PACKAGE)

    def test_documented_normal_task_command_invokes_helper(self):
        start = (ROOT / "START_HERE.md").read_text(encoding="utf-8")
        workflow = (ROOT / "docs" / "AI_WORKFLOW.md").read_text(encoding="utf-8")
        completion = (ROOT / "docs" / "templates"
                      / "OWNER_TECHNICAL_COMPLETION_REPORT.md").read_text(encoding="utf-8")
        command = "python -B scripts/package_acceptance.py check --package <PACKAGE-ID> --candidate <REVIEWED-SHA>"
        self.assertIn(command, start)
        self.assertIn("scripts/package_acceptance.py check", workflow)
        self.assertIn("scripts/package_acceptance.py check", completion)
        run = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "package_acceptance.py"),
             "check", "--package", PACKAGE, "--candidate", self.candidate,
             "--repo", str(self.repo)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual("pass", json.loads(run.stdout)["result"])

    def test_read_only_explicit_skip_needs_no_record(self):
        run = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "package_acceptance.py"),
             "check", "--package", PACKAGE, "--read-only", "--repo", str(self.repo / "missing")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, run.returncode)
        self.assertEqual("skip", json.loads(run.stdout)["result"])

    def test_missing_record_refuses_completion(self):
        (self.repo / RECORD).unlink()
        self._commit("Remove proof")
        with self.assertRaisesRegex(acceptance.AcceptanceError, "missing acceptance record"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_failed_or_blocked_result_refuses_completion(self):
        for status in ("fail", "blocked"):
            with self.subTest(status=status):
                self._change(lambda record: record["checks"][0].update(result=status))
                with self.assertRaisesRegex(acceptance.AcceptanceError, "failed, blocked"):
                    acceptance.validate(self.repo, PACKAGE, self.candidate)
                self._change(lambda record: record["checks"][0].update(result="pass"))

    def test_unmapped_criterion_refuses_completion(self):
        self._change(lambda record: record["checks"].pop())
        with self.assertRaisesRegex(acceptance.AcceptanceError, "criteria without candidate proof"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_unknown_criterion_refuses_completion(self):
        self._change(lambda record: record["checks"][0].update(criterion_id="unknown"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "unknown criterion"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_stale_check_and_stale_candidate_refuse_completion(self):
        self._change(lambda record: record["checks"][0].update(candidate_sha=self.plan))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "stale candidate proof"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)
        self._change(lambda record: record["checks"][0].update(candidate_sha=self.candidate))
        self._change(lambda record: record.update(candidate_sha=self.plan))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "missing or stale"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_changed_predefined_criterion_refuses_completion(self):
        self._change(lambda record: record["criteria"][0].update(expected="Weaker outcome."))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "criteria changed"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_unresolved_red_baseline_refuses_completion(self):
        self._initialize(baseline_exit=1)
        with self.assertRaisesRegex(acceptance.AcceptanceError, "unresolved baseline"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_red_baseline_resolved_by_exact_candidate_check_passes(self):
        self._initialize(baseline_exit=1)
        self._change(lambda record: record["checks"][0].update(
            resolves_baseline_command="python -B -m unittest tests.example"
        ))
        self.assertEqual(
            "pass", acceptance.validate(self.repo, PACKAGE, self.candidate)["result"]
        )

    def test_red_baseline_cannot_be_resolved_by_unrelated_command(self):
        self._initialize(baseline_exit=1)
        self._change(lambda record: record["checks"][0].update(
            resolves_baseline_command="python -B -m unittest tests.other"
        ))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "exact failed baseline"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_plan_after_implementation_refuses_completion(self):
        self._initialize(late_plan=True)
        with self.assertRaisesRegex(acceptance.AcceptanceError, "parent must be on authoritative main"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_implementation_mixed_into_plan_refuses_completion(self):
        self._initialize(mixed_plan=True)
        with self.assertRaisesRegex(acceptance.AcceptanceError, "only its fixed evidence"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_early_plan_survives_disjoint_main_reconciliation(self):
        git(self.repo, "checkout", "-q", "main")
        (self.repo / "main-only.txt").write_text("Disjoint main advance\n", encoding="utf-8")
        advanced_main = self._commit("Advance main")
        git(self.repo, "update-ref", "refs/remotes/origin/main", advanced_main)
        git(self.repo, "checkout", "-q", "work/acceptance-test")
        git(self.repo, "merge", "--no-ff", "-m", "Reconcile main", "main")
        self.candidate = git(self.repo, "rev-parse", "HEAD")
        self.record["candidate_sha"] = self.candidate
        for check in self.record["checks"]:
            check["candidate_sha"] = self.candidate
        self._write()
        self._commit("Record reconciled candidate proof")
        self.assertEqual(
            "pass", acceptance.validate(self.repo, PACKAGE, self.candidate)["result"]
        )

    def test_manual_and_browser_provenance_is_required(self):
        self._change(lambda record: record["checks"][1].pop("provenance"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "lacks exact provenance"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)
        self._change(lambda record: record["checks"][1].update(kind="browser"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "lacks exact provenance"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_manual_provenance_must_match_exact_source_and_time(self):
        self._change(lambda record: record["checks"][1]["provenance"].update(
            source_ref="evidence:another-note"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "inconsistent source"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)
        self._change(lambda record: record["checks"][1]["provenance"].update(
            source_ref="evidence:operator-note-1", captured_at="yesterday"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "invalid capture time"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_generic_process_exit_is_not_semantic_proof(self):
        self._change(lambda record: record["checks"][0].update(observed="exit 0"))
        with self.assertRaisesRegex(acceptance.AcceptanceError, "semantic observation"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)

    def test_post_candidate_implementation_drift_refuses_completion(self):
        (self.repo / "implementation.txt").write_text("changed after review\n", encoding="utf-8")
        self._commit("Unreviewed implementation")
        with self.assertRaisesRegex(acceptance.AcceptanceError, "implementation changed"):
            acceptance.validate(self.repo, PACKAGE, self.candidate)


if __name__ == "__main__":
    unittest.main()
