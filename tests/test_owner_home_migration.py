import os
import re
import unittest
from pathlib import Path

from mssql_python import connect


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
FORWARD = MIGRATIONS / "PS-HOME-001_owner_home_reads.sql"
ROLLBACK = MIGRATIONS / "PS-HOME-001_owner_home_reads_rollback.sql"
VERIFY = VERIFICATION / "PS-HOME-001_owner_isolation_verify.sql"


def procedure_batch(sql):
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    matches = [batch for batch in batches if "usp_GetOwnerHomeForOwner" in batch]
    if len(matches) != 1:
        raise AssertionError("Expected one Owner Home procedure batch.")
    return matches[0]


class OwnerHomeMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.procedure = procedure_batch(cls.forward)

    def test_forward_rollback_and_verification_exist(self):
        self.assertTrue(FORWARD.exists())
        self.assertTrue(ROLLBACK.exists())
        self.assertTrue(VERIFY.exists())

    def test_migration_requires_released_owner_workflow_foundations(self):
        for value in (
            "PS-AUTH-001",
            "PS-CAPTURE-001",
            "PS-MOMENT-001",
            "PS-VOICE-001",
            "dbo.member_profiles",
            "dbo.voice_media_sources",
            "dbo.moments",
            "dbo.moment_versions",
            "dbo.moment_sources",
            "SET XACT_ABORT ON",
            "BEGIN TRANSACTION",
            "COMMIT TRANSACTION",
            "ROLLBACK TRANSACTION",
            "migration_id = N'PS-HOME-001'",
        ):
            self.assertIn(value, self.forward)

    def test_one_owner_resolving_transactionally_consistent_read_procedure(self):
        self.assertIn("@UserKey nvarchar(300)", self.procedure)
        self.assertNotIn("@OwnerProfileId", self.procedure)
        self.assertNotIn("@ProfileId bigint,", self.procedure.split("AS", 1)[0])
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.procedure)
        self.assertIn("app_user.user_key = @UserKey", self.procedure)
        self.assertIn("source.owner_profile_id = @ProfileId", self.procedure)
        self.assertIn("moment.owner_profile_id = @ProfileId", self.procedure)
        self.assertIn("TOP (3)", self.procedure)
        self.assertIn("TOP (1)", self.procedure)
        self.assertEqual(self.forward.count("CREATE OR ALTER PROCEDURE"), 1)

    def test_review_priority_determinism_and_deleted_state_exclusions(self):
        failed = self.procedure.index("voice_draft_failed")
        proposal = self.procedure.index("moment_proposal_pending")
        ready = self.procedure.index("voice_draft_ready")
        self.assertLess(failed, proposal)
        self.assertLess(proposal, ready)
        self.assertIn("candidate.urgency_priority", self.procedure)
        self.assertIn("candidate.updated_at_utc", self.procedure)
        self.assertIn("candidate.item_key", self.procedure)
        self.assertIn("source.state = N''failed''", self.procedure)
        self.assertIn("source.state = N''needs_review''", self.procedure)
        self.assertIn("source.deleted_at_utc IS NULL", self.procedure)
        self.assertIn("source_link.source_state = N''available''", self.procedure)

    def test_read_contract_never_selects_prohibited_private_content(self):
        lowered = self.procedure.lower()
        for forbidden in (
            "capture.body",
            "provider_transcript",
            "blob_name",
            "sha256_digest",
            "email",
            "narrative",
            "why_it_matters",
            "owner_profile_id as",
            "profile_id as",
            "moment_id as",
            "source_id as",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn("usp_GetPeerSlateUserDashboard", self.procedure)

    def test_migration_and_rollback_fingerprint_exact_procedure(self):
        for sql in (self.forward, self.rollback):
            self.assertIn("PS_HOME_001_DEFINITION_HASH", sql)
            self.assertIn("HASHBYTES", sql)
            self.assertIn("OBJECT_DEFINITION", sql)
        self.assertIn("a later migration is present", self.rollback)
        self.assertIn("definition drift", self.rollback)
        self.assertIn("DROP PROCEDURE dbo.usp_GetOwnerHomeForOwner", self.rollback)
        self.assertLess(
            self.rollback.index("definition drift"),
            self.rollback.index("DROP PROCEDURE"),
        )

    def test_verifier_has_two_owners_canaries_and_outer_rollback(self):
        for value in (
            "@SubjectA",
            "@SubjectB",
            "@ProfileIdA",
            "@ProfileIdB",
            "@FailedKeyA",
            "@FailedKeyB",
            "@RecentMomentA",
            "@RecentMomentB",
            "MUST NOT ENTER HOME PAYLOAD",
            "usp_GetOwnerHomeForOwner @UserKey = @UserKeyA",
            "usp_GetOwnerHomeForOwner @UserKey = @UserKeyB",
            "The Owner Home read changed canonical owner records",
            "The Owner Home read includes prohibited private content",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        ):
            self.assertIn(value, self.verification)

    def test_application_allowlist_and_flag_route_changes_are_narrow(self):
        database_source = (ROOT / "services" / "database_service.py").read_text(
            encoding="utf-8"
        )
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        route_source = (ROOT / "owner_routes.py").read_text(encoding="utf-8")
        auth_source = (ROOT / "auth_routes.py").read_text(encoding="utf-8")

        self.assertEqual(database_source.count('"usp_GetOwnerHomeForOwner"'), 1)
        self.assertIn("PEERSLATE_OWNER_HOME_ENABLED", app_source)
        self.assertIn('@owner.get("/api/v1/owner/home")', route_source)
        self.assertNotIn("PEERSLATE_OWNER_HOME_ENABLED", auth_source)
        self.assertNotIn("owner_home.html", auth_source)


@unittest.skipUnless(
    os.getenv("PS_HOME_SQL_GATE") == "1",
    "requires the isolated PS-HOME-001 SQL gate database",
)
class OwnerHomeIsolatedSqlGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]

    def execute_script(self, path):
        with connect(self.connection_string, timeout=60) as connection:
            connection.setautocommit(True)
            cursor = connection.cursor()
            cursor.execute(path.read_text(encoding="utf-8"))
            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()

    def scalar(self, statement):
        with connect(self.connection_string, timeout=60) as connection:
            connection.setautocommit(True)
            cursor = connection.cursor()
            cursor.execute(statement)
            return cursor.fetchone()[0]

    def test_apply_verify_rollback_reapply(self):
        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-HOME-001'"
            ),
            1,
        )

        self.execute_script(ROLLBACK)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-HOME-001'"
            ),
            0,
        )
        self.assertIsNone(
            self.scalar("SELECT OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P')")
        )

        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-HOME-001'"
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
