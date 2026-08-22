"""Cross-file invariants of the extraction slice: registries, roles, gates."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import app as app_module
from services.database_service import ALLOWED_PROCEDURES
from services.interview_ai.bundles import load_bundle

ROOT = Path(__file__).resolve().parents[2]

FROZEN_PROVIDER_CONFIG = {
    "coach": 2400,
    "revision": 1300,
    "planning_hints": 500,
    "grounded_example": 1300,
    "generic_example": 1300,
}


class DimensionRegistryTests(unittest.TestCase):
    def test_contract_file_carries_the_live_registry_unchanged(self):
        contract = json.loads(
            (ROOT / "prompts" / "interview" / "contracts"
             / "dimension-registry-1.json").read_text(encoding="utf-8")
        )
        live = {
            family: list(keys)
            for family, keys in app_module.INTERVIEW_FAMILY_DIMENSIONS.items()
        }
        self.assertEqual(contract["families"], live)


class ProviderConfigTests(unittest.TestCase):
    def test_every_bundle_keeps_the_frozen_model_and_max_tokens(self):
        bundles_root = ROOT / "prompts" / "interview" / "bundles"
        for specialist, max_tokens in FROZEN_PROVIDER_CONFIG.items():
            bundle_dir = next((bundles_root / specialist).iterdir())
            bundle = load_bundle(bundle_dir, expected_specialist=specialist)
            self.assertEqual(bundle.model, "claude-haiku-4-5-20251001")
            self.assertEqual(bundle.max_tokens, max_tokens)


class InputManifestTests(unittest.TestCase):
    """C5: the concrete bundle manifests describe the real provider inputs."""

    def _manifest(self, specialist):
        bundle_dir = next(
            (ROOT / "prompts" / "interview" / "bundles" / specialist).iterdir()
        )
        schema = json.loads(
            (bundle_dir / "schema.json").read_text(encoding="utf-8")
        )
        return schema["input_manifest"]

    def test_model_answer_specialists_accept_the_prior_validated_answer(self):
        for specialist in ("grounded_example", "generic_example"):
            manifest = self._manifest(specialist)
            self.assertIn("answer", manifest, specialist)
            self.assertEqual(
                manifest["answer"]["provenance"], "server_derived", specialist,
            )
            self.assertIn("never member History", manifest["answer"]["note"])
            self.assertNotIn("history_selection", manifest, specialist)

    def test_coach_and_revision_answers_are_member_submitted(self):
        for specialist in ("coach", "revision"):
            manifest = self._manifest(specialist)
            self.assertEqual(
                manifest["answer"]["provenance"], "member_submitted",
                specialist,
            )

    def test_planning_hints_is_structurally_question_only(self):
        manifest = self._manifest("planning_hints")
        self.assertEqual(sorted(manifest), ["question", "role_context"])

    def test_generic_example_accepts_no_member_evidence(self):
        self.assertNotIn("member_evidence", self._manifest("generic_example"))


class TelemetrySinkAuthorityTests(unittest.TestCase):
    def test_app_allowlist_holds_append_and_never_purge(self):
        self.assertIn("usp_AppendInterviewAIServerCall", ALLOWED_PROCEDURES)
        self.assertNotIn("usp_PurgeInterviewAIServerCalls", ALLOWED_PROCEDURES)

    def test_purge_script_refuses_without_its_own_identity(self):
        completed = subprocess.run(
            [sys.executable,
             str(ROOT / "scripts" / "interview_ai"
                 / "run_interview_telemetry_purge.py"),
             "--expect-database", "peerslate"],
            capture_output=True, text=True, cwd=str(ROOT),
            env={**os.environ,
                 "INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING": ""},
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "refused")


class PipelineIsolationTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = (ROOT / "azure-pipelines.yml").read_text(
            encoding="utf-8"
        )

    def _stage_body(self, stage_name):
        start = self.pipeline.index("stage: %s" % stage_name)
        remainder = self.pipeline[start + 1:]
        next_stage = remainder.find("\n  - stage: ")
        end = start + 1 + next_stage if next_stage != -1 else len(self.pipeline)
        return self.pipeline[start:end]

    def test_neither_schedule_can_trigger_the_other_stage(self):
        """C4: both schedule-gated stages pin their own schedule display
        name, so the Interview cron can never run Community maintenance
        and the Community cron can never run the Interview purge."""
        community = self._stage_body("CommunityMaintenance")
        interview = self._stage_body("InterviewTelemetryMaintenance")
        self.assertIn(
            "eq(variables['Build.CronSchedule.DisplayName'], "
            "'Community maintenance hourly')",
            community,
        )
        self.assertNotIn("Interview telemetry retention nightly", community)
        self.assertIn(
            "eq(variables['Build.CronSchedule.DisplayName'], "
            "'Interview telemetry retention nightly')",
            interview,
        )
        self.assertNotIn("Community maintenance hourly", interview)

    def test_interview_retention_reuses_no_community_controls(self):
        interview = self._stage_body("InterviewTelemetryMaintenance")
        self.assertIn("interviewTelemetryMaintenanceEnabled", interview)
        self.assertIn("INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING", interview)
        self.assertNotIn("communityMaintenance", interview)
        self.assertNotIn("AZURE_SQL_CONNECTIONSTRING", interview)
        self.assertIn(
            "ne(variables['interviewTelemetryMaintenanceEnabled'], 'true')",
            interview,
        )
        self.assertIn("condition: always()", interview)

    def test_the_retention_schedule_exists_and_is_nightly(self):
        self.assertIn(
            "displayName: Interview telemetry retention nightly",
            self.pipeline,
        )
        self.assertIn("cron: '41 2 * * *'", self.pipeline)


class MigrationProposalTests(unittest.TestCase):
    def test_registry_entry_is_a_gated_unapplied_proposal_on_plat_001(self):
        registry = json.loads(
            (ROOT / "SQL FIles" / "Migrations" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        entries = [m for m in registry["migrations"]
                   if m["id"] == "PS-INTERVIEW-AI-EXTRACT-001"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        # C3: the proposal carries a disposable-database gate proof. The
        # gate database name must be a throwaway, never production, and
        # the registry deliberately records no applied-ness claim.
        self.assertIsNotNone(entry["gate"])
        self.assertIn("gate", entry["gate"]["gate_database"])
        self.assertNotIn("peerslate-database", entry["gate"]["gate_database"])
        self.assertEqual(entry["requires"], ["PS-PLAT-001"])
        self.assertTrue((ROOT / entry["forward"]).is_file())
        self.assertTrue((ROOT / entry["rollback"]).is_file())

    def test_forward_sql_separates_the_two_roles(self):
        """Run 1419 (2026-08-22) proved the governed apply identity holds
        db_ddladmin only and cannot CREATE ROLE or GRANT, so the two
        execute-only roles moved out of the migration into the
        administrator-run authority script. The forward SQL now carries
        schema only; the separation is asserted where it actually lives."""
        forward = (
            ROOT / "SQL FIles" / "Migrations" / "proposed"
            / "PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("DATEADD(DAY, -90,", forward)
        for forbidden in ("GRANT ", "DENY ", "CREATE ROLE", "ALTER ROLE",
                          "CREATE USER"):
            self.assertNotIn(forbidden, forward)
        authority = (
            ROOT / "scripts" / "configure_interview_telemetry_sql_authority.py"
        ).read_text(encoding="utf-8")
        self.assertIn("(APPEND_ROLE, APPEND_PROCEDURE),", authority)
        self.assertIn("(MAINTENANCE_ROLE, PURGE_PROCEDURE),", authority)
        self.assertIn(
            'GRANT EXECUTE ON OBJECT::dbo.{procedure} TO [{role}];', authority
        )
        for forbidden in ("GRANT INSERT", "GRANT SELECT", "GRANT DELETE",
                          "GRANT UPDATE"):
            self.assertNotIn(forbidden, authority)


if __name__ == "__main__":
    unittest.main()
