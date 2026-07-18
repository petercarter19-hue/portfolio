import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
RUNNER = ROOT / "scripts" / "apply_sql_migrations.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("capture_migrations", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CaptureMigrationTests(unittest.TestCase):
    def setUp(self):
        self.forward = MIGRATIONS / "PS-CAPTURE-001_captures.sql"
        self.rollback = MIGRATIONS / "PS-CAPTURE-001_captures_rollback.sql"
        self.verification = (
            VERIFICATION / "PS-CAPTURE-001_owner_isolation_verify.sql"
        )
        self.lifecycle_forward = (
            MIGRATIONS / "PS-CAPTURE-002_capture_lifecycle.sql"
        )
        self.lifecycle_rollback = (
            MIGRATIONS / "PS-CAPTURE-002_capture_lifecycle_rollback.sql"
        )
        self.lifecycle_verification = (
            VERIFICATION / "PS-CAPTURE-002_lifecycle_verify.sql"
        )

    def test_forward_rollback_and_isolation_verification_exist(self):
        self.assertTrue(self.forward.exists())
        self.assertTrue(self.rollback.exists())
        self.assertTrue(self.verification.exists())

    def test_forward_is_transactional_private_and_owner_scoped(self):
        sql = self.forward.read_text(encoding="utf-8")

        self.assertIn("SET XACT_ABORT ON", sql)
        self.assertIn("BEGIN TRANSACTION", sql)
        self.assertIn("COMMIT TRANSACTION", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("DEFAULT N'private'", sql)
        self.assertIn("usp_CreateCapture", sql)
        self.assertIn("usp_ListCapturesForOwner", sql)
        self.assertGreaterEqual(sql.count("@UserKey nvarchar(300)"), 2)
        self.assertNotIn("@OwnerProfileId", sql)
        self.assertIn("capture.owner_profile_id = @ProfileId", sql)
        self.assertIn("NCHAR(9)", sql)
        self.assertIn("NCHAR(10)", sql)
        self.assertIn("NCHAR(13)", sql)
        self.assertIn("@ActionType = N''capture.created''", sql)
        self.assertIn("@MetadataJson = @AuditMetadataJson", sql)
        self.assertNotIn("@MetadataJson = CONCAT", sql)
        self.assertNotIn("@MetadataJson = @Body", sql)

    def test_rollback_refuses_member_data_and_later_dependencies(self):
        sql = self.rollback.read_text(encoding="utf-8")

        self.assertIn("captures contains member data", sql)
        self.assertIn("sys.foreign_keys", sql)
        self.assertIn("sys.sql_expression_dependencies", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)

    def test_verification_proves_two_owner_isolation_and_rolls_back(self):
        sql = self.verification.read_text(encoding="utf-8")

        self.assertIn("@SubjectA", sql)
        self.assertIn("@SubjectB", sql)
        self.assertIn("identity_record.provider", sql)
        self.assertNotIn("identity_record.auth_provider", sql)
        self.assertNotIn("INSERT @Created\n    EXEC dbo.usp_CreateCapture", sql)
        self.assertIn("Owner A capture isolation failed", sql)
        self.assertIn("Owner B capture isolation failed", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("CAST(1 AS bit) AS verified", sql)

    def test_runner_selects_capture_without_foundation_reapply(self):
        runner = load_runner()

        paths = runner.selected_optional_migrations(["PS-CAPTURE-001"])

        self.assertEqual(paths, [self.forward])
        self.assertNotIn(self.forward.name, runner.MIGRATION_FILENAMES)

    def test_foundation_validator_allows_later_migration_records(self):
        runner = load_runner()
        results = [
            [{"database_name": "test"}],
            [
                {"migration_id": item}
                for item in sorted(
                    runner.EXPECTED_MIGRATIONS | {"PS-CAPTURE-001"}
                )
            ],
            [
                {"object_name": item, "exists_flag": 1}
                for item in sorted(runner.EXPECTED_TABLES)
            ],
            [
                {"object_name": item, "exists_flag": 1}
                for item in sorted(runner.EXPECTED_PROGRAMMABLE_OBJECTS)
            ],
            [],
            [],
            [],
            [
                {
                    "user_count": 2,
                    "profile_count": 2,
                    "private_profile_count": 2,
                    "discovery_off_count": 2,
                    "account_key_count": 2,
                    "mapped_auth_count": 2,
                    "identity_count": 2,
                }
            ],
        ]

        self.assertEqual(runner.validate_verification_results(results), [])

    def test_lifecycle_forward_rollback_and_verification_exist(self):
        self.assertTrue(self.lifecycle_forward.exists())
        self.assertTrue(self.lifecycle_rollback.exists())
        self.assertTrue(self.lifecycle_verification.exists())

    def test_lifecycle_forward_is_revisioned_owner_scoped_and_concurrent(self):
        sql = self.lifecycle_forward.read_text(encoding="utf-8")

        self.assertIn("PS-AUTH-001", sql)
        self.assertIn("PS-CAPTURE-001", sql)
        self.assertIn("CREATE TABLE dbo.capture_revisions", sql)
        self.assertIn("UQ_capture_revisions_capture_number", sql)
        self.assertIn("INSERT dbo.capture_revisions", sql)
        self.assertNotIn("body = @CorrectedBody", sql)
        self.assertNotIn("SET body =", sql)
        self.assertIn("@UserKey nvarchar(300)", sql)
        self.assertIn("@CaptureKey uniqueidentifier", sql)
        self.assertGreaterEqual(sql.count("@ExpectedRowVersion binary(8)"), 4)
        self.assertIn("capture.owner_profile_id = @ProfileId", sql)
        self.assertIn("capture.row_version = @ExpectedRowVersion", sql)
        self.assertIn("not_found_or_changed", sql)
        self.assertIn("@Archived bit = 0", sql)
        self.assertIn("OUTER APPLY", sql)
        self.assertIn("capture.body AS original_body", sql)
        self.assertIn("DELETE dbo.capture_revisions", sql)
        self.assertIn("DELETE dbo.captures", sql)
        self.assertIn("usp_ExportCaptureForOwner", sql)
        self.assertNotIn("INSERT dbo.slate_entities", sql)
        self.assertNotIn("INSERT dbo.entity_publication_versions", sql)
        self.assertNotIn("UPDATE dbo.entity_publication_versions", sql)
        self.assertNotIn("@MetadataJson = @CorrectedBody", sql)
        self.assertNotIn("@MetadataJson = @CorrectionNote", sql)

    def test_lifecycle_dynamic_procedure_batches_are_well_formed(self):
        sql = self.lifecycle_forward.read_text(encoding="utf-8")
        dynamic_batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)

        self.assertEqual(len(dynamic_batches), 7)
        procedure_names = {
            match.group(1)
            for batch in dynamic_batches
            if (match := re.search(r"PROCEDURE dbo\.(usp_[A-Za-z0-9_]+)", batch))
        }
        self.assertEqual(
            procedure_names,
            {
                "usp_ListCapturesForOwner",
                "usp_GetCaptureForOwner",
                "usp_CorrectCapture",
                "usp_ArchiveCapture",
                "usp_RestoreCapture",
                "usp_DeleteCapture",
                "usp_ExportCaptureForOwner",
            },
        )
        self.assertIn("FOR JSON PATH", sql)

    def test_lifecycle_rollback_is_guarded_and_restores_capture_001_list(self):
        sql = self.lifecycle_rollback.read_text(encoding="utf-8")

        self.assertIn("capture_revisions contains member revisions", sql)
        self.assertIn("captures contains archived lifecycle state", sql)
        self.assertIn(
            "parent_object_id = OBJECT_ID(N'dbo.capture_revisions')",
            sql,
        )
        self.assertIn("CREATE OR ALTER PROCEDURE dbo.usp_ListCapturesForOwner", sql)
        self.assertIn("DROP PROCEDURE dbo.usp_CorrectCapture", sql)
        self.assertIn("DROP PROCEDURE dbo.usp_ArchiveCapture", sql)
        self.assertIn("DROP PROCEDURE dbo.usp_RestoreCapture", sql)
        self.assertIn("DROP PROCEDURE dbo.usp_DeleteCapture", sql)
        self.assertIn("DROP PROCEDURE dbo.usp_ExportCaptureForOwner", sql)
        self.assertIn("DROP TABLE dbo.capture_revisions", sql)
        self.assertIn("migration_id = N'PS-CAPTURE-002'", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertEqual(
            len(re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)),
            1,
        )

    def test_lifecycle_verification_proves_two_owner_and_no_auto_publish(self):
        sql = self.lifecycle_verification.read_text(encoding="utf-8")

        self.assertIn("@SubjectA", sql)
        self.assertIn("@SubjectB", sql)
        self.assertIn("usp_CorrectCapture", sql)
        self.assertIn("usp_ArchiveCapture", sql)
        self.assertIn("usp_RestoreCapture", sql)
        self.assertIn("usp_DeleteCapture", sql)
        self.assertIn("usp_ExportCaptureForOwner", sql)
        self.assertIn("Cross-owner", sql)
        self.assertIn("Stale row version", sql)
        self.assertIn("Original capture body was overwritten", sql)
        self.assertIn("visibility <> N'private'", sql)
        self.assertIn("status = N'placed'", sql)
        self.assertIn("Deleted capture text remained", sql)
        self.assertIn("Audit metadata contains private capture content", sql)
        self.assertNotIn("INSERT @CorrectionResult", sql)
        self.assertNotIn("INSERT @StateResult", sql)
        self.assertNotIn("INSERT @DeleteResult", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("CAST(1 AS bit) AS verified", sql)

    def test_runner_selects_and_verifies_capture_lifecycle_only(self):
        runner = load_runner()

        paths = runner.selected_optional_migrations(["PS-CAPTURE-002"])

        self.assertEqual(paths, [self.lifecycle_forward])
        self.assertEqual(
            runner.CAPTURE_LIFECYCLE_VERIFY_PATH,
            self.lifecycle_verification,
        )
        self.assertNotIn(self.lifecycle_forward.name, runner.MIGRATION_FILENAMES)


if __name__ == "__main__":
    unittest.main()
