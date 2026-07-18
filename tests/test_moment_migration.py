import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
RUNNER = ROOT / "scripts" / "apply_sql_migrations.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("moment_migrations", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dynamic_procedure_batches(sql):
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    return {
        match.group(1): batch
        for batch in batches
        if (match := re.search(r"PROCEDURE dbo\.(usp_[A-Za-z0-9_]+)", batch))
    }


class MomentMigrationTests(unittest.TestCase):
    def setUp(self):
        self.forward = MIGRATIONS / "PS-MOMENT-001_moments.sql"
        self.rollback = MIGRATIONS / "PS-MOMENT-001_moments_rollback.sql"
        self.verification = VERIFICATION / "PS-MOMENT-001_owner_isolation_verify.sql"

    def test_forward_rollback_and_real_verification_exist(self):
        self.assertTrue(self.forward.exists())
        self.assertTrue(self.rollback.exists())
        self.assertTrue(self.verification.exists())

    def test_forward_requires_capture_lifecycle_and_is_transactional(self):
        sql = self.forward.read_text(encoding="utf-8")

        self.assertIn("PS-AUTH-001", sql)
        self.assertIn("PS-CAPTURE-001", sql)
        self.assertIn("PS-CAPTURE-002", sql)
        self.assertIn("SET XACT_ABORT ON", sql)
        self.assertIn("BEGIN TRANSACTION", sql)
        self.assertIn("COMMIT TRANSACTION", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("migration_id = N'PS-MOMENT-001'", sql)

    def test_normalized_private_version_and_source_tables_preserve_boundaries(self):
        sql = self.forward.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE dbo.moments", sql)
        self.assertIn("CREATE TABLE dbo.moment_versions", sql)
        self.assertIn("CREATE TABLE dbo.moment_sources", sql)
        self.assertIn("CK_moments_visibility CHECK (visibility = N'private')", sql)
        self.assertIn("CK_moments_confirmation_state", sql)
        self.assertIn("UQ_moment_versions_number", sql)
        self.assertIn("UQ_moment_sources_owner_version", sql)
        self.assertIn("source_revision_number", sql)
        self.assertIn("source_revision_key", sql)
        self.assertIn("source_state IN (N'available', N'deleted')", sql)

        source_table = sql.split("CREATE TABLE dbo.moment_sources", 1)[1].split(
            "CREATE INDEX IX_moment_sources_capture", 1
        )[0]
        self.assertNotIn("source_body", source_table)
        self.assertNotRegex(source_table, r"\bbody\b")
        self.assertNotIn("correction_note", source_table)

    def test_procedures_are_owner_resolving_concurrent_and_explicit(self):
        sql = self.forward.read_text(encoding="utf-8")
        batches = dynamic_procedure_batches(sql)

        self.assertEqual(
            set(batches),
            {
                "usp_CreateOrReopenMomentProposal",
                "usp_GetMomentForOwner",
                "usp_SaveMomentProposal",
                "usp_ConfirmMoment",
                "usp_DiscardMomentProposal",
                "usp_DeleteCapture",
            },
        )
        for name in {
            "usp_CreateOrReopenMomentProposal",
            "usp_GetMomentForOwner",
            "usp_SaveMomentProposal",
            "usp_ConfirmMoment",
            "usp_DiscardMomentProposal",
        }:
            self.assertIn("@UserKey nvarchar(300)", batches[name])
            self.assertIn("owner_profile_id = @ProfileId", batches[name])
            self.assertNotIn("@OwnerProfileId", batches[name])

        self.assertIn("@ExpectedRowVersion binary(8)", batches["usp_SaveMomentProposal"])
        self.assertIn("moment.row_version = @ExpectedRowVersion", batches["usp_SaveMomentProposal"])
        self.assertIn("@ExpectedProposalVersion int", batches["usp_ConfirmMoment"])
        self.assertIn(
            "moment.current_version_number = @ExpectedProposalVersion",
            batches["usp_ConfirmMoment"],
        )
        self.assertIn("moment.status = N''proposal''", batches["usp_ConfirmMoment"])
        self.assertIn("source_link.source_state", batches["usp_ConfirmMoment"])
        self.assertIn("N''source_deleted'' AS outcome", batches["usp_ConfirmMoment"])

    def test_source_is_read_live_by_exact_pin_and_later_correction_is_only_reported(self):
        sql = self.forward.read_text(encoding="utf-8")
        get_batch = dynamic_procedure_batches(sql)["usp_GetMomentForOwner"]

        self.assertIn("source_link.source_revision_number = 0 THEN capture.body", get_batch)
        self.assertIn("ELSE revision.body", get_batch)
        self.assertIn("revision.revision_id = source_link.capture_revision_id", get_batch)
        self.assertIn("latest_source_revision_number", get_batch)
        self.assertIn("newer_source_available", get_batch)
        self.assertNotIn("UPDATE dbo.captures", get_batch)
        self.assertNotIn("UPDATE dbo.capture_revisions", get_batch)

        create_batch = dynamic_procedure_batches(sql)["usp_CreateOrReopenMomentProposal"]
        self.assertIn("@SourceRevisionNumber", create_batch)
        self.assertIn("source_revision_number", create_batch)
        self.assertNotIn("capture.body", create_batch)
        self.assertNotIn("revision.body", create_batch)

    def test_save_and_confirm_lock_source_row_while_checking_source_state(self):
        sql = self.forward.read_text(encoding="utf-8")
        batches = dynamic_procedure_batches(sql)

        for procedure_name in ("usp_SaveMomentProposal", "usp_ConfirmMoment"):
            procedure = batches[procedure_name]
            self.assertIn(
                "JOIN dbo.moment_sources AS source_link WITH (UPDLOCK, HOLDLOCK)",
                procedure,
            )
            self.assertIn("@SourceState = source_link.source_state", procedure)

    def test_capture_delete_tombstones_before_removing_source_text(self):
        sql = self.forward.read_text(encoding="utf-8")
        delete_batch = dynamic_procedure_batches(sql)["usp_DeleteCapture"]

        tombstone_at = delete_batch.index("UPDATE dbo.moment_sources")
        revision_delete_at = delete_batch.index("DELETE dbo.capture_revisions")
        capture_delete_at = delete_batch.index("DELETE dbo.captures")
        self.assertLess(tombstone_at, revision_delete_at)
        self.assertLess(revision_delete_at, capture_delete_at)
        self.assertIn("source_state = N''deleted''", delete_batch)
        self.assertIn("capture_revision_id = NULL", delete_batch)
        self.assertIn("capture_id = NULL", delete_batch)
        self.assertIn("owner_profile_id = @ProfileId", delete_batch)
        self.assertIn("moment_source_tombstone_count", delete_batch)
        self.assertNotIn("@MetadataJson = @Original", delete_batch)
        self.assertNotIn("@MetadataJson = @Body", delete_batch)

    def test_no_automatic_publication_placement_journal_or_resume_writes(self):
        sql = self.forward.read_text(encoding="utf-8")

        forbidden_writes = (
            "INSERT dbo.slate_entities",
            "INSERT dbo.slate_entity_relations",
            "INSERT dbo.entity_publication_versions",
            "UPDATE dbo.entity_publication_versions",
            "INSERT dbo.journal",
            "INSERT dbo.career_",
            "publication_status",
            "dbo.moment_placements",
        )
        for statement in forbidden_writes:
            self.assertNotIn(statement, sql)

    def test_rollback_is_guarded_and_restores_exact_capture_002_delete_shape(self):
        sql = self.rollback.read_text(encoding="utf-8")

        self.assertIn("moments contains member records", sql)
        self.assertIn("moment_versions contains member proposals", sql)
        self.assertIn("moment_sources contains source relationships", sql)
        self.assertIn("sys.foreign_keys", sql)
        self.assertIn("sys.sql_expression_dependencies", sql)
        self.assertIn("a later table depends on PS-MOMENT-001", sql)
        self.assertIn("DROP TABLE dbo.moment_sources", sql)
        self.assertIn("DROP TABLE dbo.moment_versions", sql)
        self.assertIn("DROP TABLE dbo.moments", sql)
        self.assertIn("migration_id = N'PS-MOMENT-001'", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)

        batches = dynamic_procedure_batches(sql)
        self.assertEqual(set(batches), {"usp_DeleteCapture"})
        restored_delete = batches["usp_DeleteCapture"]
        self.assertIn("DELETE dbo.capture_revisions", restored_delete)
        self.assertIn("DELETE dbo.captures", restored_delete)
        self.assertNotIn("moment_sources", restored_delete)
        self.assertNotIn("tombstoned_moment_source_count", restored_delete)

    def test_rollback_refuses_later_migration_or_protected_procedure_change(self):
        forward_sql = self.forward.read_text(encoding="utf-8")
        sql = self.rollback.read_text(encoding="utf-8")

        self.assertIn("@MomentAppliedAtUtc", sql)
        self.assertIn("migration.applied_at_utc > @MomentAppliedAtUtc", sql)
        self.assertIn(
            "Rollback blocked: a migration later than PS-MOMENT-001 is present.",
            sql,
        )
        self.assertIn("PS_MOMENT_001_DEFINITION_HASH", forward_sql)
        self.assertIn("PS_MOMENT_001_DEFINITION_HASH", sql)
        self.assertIn("HASHBYTES", forward_sql)
        self.assertIn("HASHBYTES", sql)
        self.assertIn("FROM @ProtectedProcedures AS protected_procedure", sql)
        self.assertIn("property.value", sql)
        self.assertIn("OBJECT_DEFINITION(procedure_object.object_id)", sql)
        self.assertIn("@level1name = N'usp_DeleteCapture'", sql)
        self.assertIn(
            "Rollback blocked: a protected procedure changed after PS-MOMENT-001.",
            sql,
        )

        guard_at = sql.index("DECLARE @MomentAppliedAtUtc")
        restore_at = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture")
        self.assertLess(guard_at, restore_at)

    def test_verification_proves_required_owner_source_state_and_negative_paths(self):
        sql = self.verification.read_text(encoding="utf-8")

        self.assertIn("@SubjectA", sql)
        self.assertIn("@SubjectB", sql)
        self.assertIn("Cross-owner", sql)
        self.assertIn("Stale row version", sql)
        self.assertIn("Stale proposal version", sql)
        self.assertIn("source_revision_number = 1", sql)
        self.assertIn("latest_source_revision_number = 2", sql)
        self.assertIn("source_state = N'deleted'", sql)
        self.assertIn("source_body IS NULL", sql)
        self.assertIn("source-deleted unconfirmed proposal", sql)
        self.assertIn("Confirmed canonical content", sql)
        self.assertIn("automatically published, placed, or wrote downstream", sql)
        self.assertIn("Audit metadata contains private Capture or Moment content", sql)
        self.assertNotIn("INSERT @MomentResult", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("CAST(1 AS bit) AS verified", sql)

    def test_runner_selects_and_verifies_moment_only(self):
        runner = load_runner()

        paths = runner.selected_optional_migrations(["PS-MOMENT-001"])

        self.assertEqual(paths, [self.forward])
        self.assertEqual(runner.MOMENT_VERIFY_PATH, self.verification)
        self.assertNotIn(self.forward.name, runner.MIGRATION_FILENAMES)


if __name__ == "__main__":
    unittest.main()
