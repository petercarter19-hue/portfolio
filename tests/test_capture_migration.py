import importlib.util
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


if __name__ == "__main__":
    unittest.main()
