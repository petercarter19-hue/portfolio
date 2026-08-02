import os
import re
import unittest
from pathlib import Path

from mssql_python import connect


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
FORWARD = MIGRATIONS / "PS-WORKSHOP-001_knowledge_items.sql"
ROLLBACK = MIGRATIONS / "PS-WORKSHOP-001_knowledge_items_rollback.sql"
VERIFY = VERIFICATION / "PS-WORKSHOP-001_owner_isolation_verify.sql"

PROCEDURE_NAMES = (
    "usp_ListKnowledgeItemsForOwner",
    "usp_GetKnowledgeItemForOwner",
    "usp_SaveKnowledgeItemForOwner",
    "usp_UpdateKnowledgeItemForOwner",
    "usp_ArchiveKnowledgeItemForOwner",
    "usp_RestoreKnowledgeItemForOwner",
    "usp_DeleteKnowledgeItemForOwner",
)


def procedure_batches(sql):
    """Map each CREATE OR ALTER PROCEDURE dynamic-SQL batch to its name."""
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


class WorkshopMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_forward_rollback_and_verification_exist(self):
        self.assertTrue(FORWARD.exists())
        self.assertTrue(ROLLBACK.exists())
        self.assertTrue(VERIFY.exists())

    def test_all_seven_procedures_are_present_exactly_once(self):
        self.assertEqual(set(self.procedures), set(PROCEDURE_NAMES))
        self.assertEqual(
            self.forward.count("CREATE OR ALTER PROCEDURE"), len(PROCEDURE_NAMES)
        )

    def test_migration_is_one_guarded_transactional_batch(self):
        for value in (
            "SET NOCOUNT ON",
            "SET XACT_ABORT ON",
            "BEGIN TRY",
            "BEGIN TRANSACTION",
            "COMMIT TRANSACTION",
            "BEGIN CATCH",
            "ROLLBACK TRANSACTION",
            "THROW;",
        ):
            self.assertIn(value, self.forward)
        # A single batch: no GO separators anywhere in the forward file.
        self.assertNotIn("\nGO", self.forward)
        self.assertNotIn("\nGO", self.rollback)

    def test_migration_requires_its_dependency_guards(self):
        for value in (
            "PS-PLAT-001",
            "PS-PLAT-002",
            "PS-AUTH-001",
            "dbo.app_users",
            "dbo.member_profiles",
            "dbo.audit_events",
            "dbo.usp_AppendAuditEvent",
            "migration_id = N'PS-WORKSHOP-001'",
        ):
            self.assertIn(value, self.forward)

    def test_migration_creates_the_three_tables(self):
        for value in (
            "CREATE TABLE dbo.knowledge_items",
            "CREATE TABLE dbo.knowledge_item_versions",
            "CREATE TABLE dbo.knowledge_item_save_requests",
        ):
            self.assertIn(value, self.forward)

    def test_visibility_is_hard_locked_private(self):
        self.assertIn(
            "CONSTRAINT CK_knowledge_items_visibility CHECK (visibility = N'private')",
            self.forward,
        )

    def test_confirmation_and_archive_state_are_paired_checks(self):
        self.assertIn("CK_knowledge_items_confirmation_state", self.forward)
        self.assertIn("CK_knowledge_items_archive_pair", self.forward)

    def test_owner_and_version_uniqueness_constraints_exist(self):
        self.assertIn(
            "CONSTRAINT UQ_knowledge_items_id_owner UNIQUE (knowledge_item_id, owner_profile_id)",
            self.forward,
        )
        self.assertIn(
            "CONSTRAINT FK_knowledge_item_versions_item FOREIGN KEY (knowledge_item_id, owner_profile_id)",
            self.forward,
        )
        self.assertIn(
            "CONSTRAINT UQ_knowledge_item_versions_number UNIQUE (knowledge_item_id, version_number)",
            self.forward,
        )
        self.assertIn(
            "CONSTRAINT UQ_knowledge_item_save_requests_owner_key",
            self.forward,
        )
        self.assertIn(
            "UNIQUE (owner_profile_id, idempotency_key)",
            self.forward,
        )

    def test_utf16_length_checks_match_documented_bounds(self):
        self.assertIn(
            "CONSTRAINT CK_knowledge_item_versions_title_length CHECK\n"
            "                (DATALENGTH(title) / 2 BETWEEN 1 AND 160)",
            self.forward,
        )
        self.assertIn("DATALENGTH(approved_wording) / 2 BETWEEN 1 AND 8000", self.forward)
        self.assertIn(
            "DATALENGTH(original_member_wording) / 2 BETWEEN 1 AND 8000", self.forward
        )
        self.assertIn("title nvarchar(160)", self.forward)

    def test_no_ai_use_permission_concept_anywhere(self):
        """Owner decision, 2026-08-01 (doc 20 section 6a): AI use of confirmed
        information is always on. There is no per-item permission column,
        procedure, or predicate — checked here as a literal absence across
        all three SQL files, including comments, so the retired concept
        cannot silently reappear even as documentation."""
        forbidden = "ai_use" + "_permission"
        for sql, label in (
            (self.forward, "forward migration"),
            (self.rollback, "rollback"),
            (self.verification, "verifier"),
        ):
            self.assertNotIn(forbidden, sql, f"{label} contains the retired identifier")

    def test_every_procedure_resolves_user_key_and_never_accepts_owner_profile_id(self):
        for name, batch in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertIn("@UserKey nvarchar(300)", batch)
                self.assertNotIn("@OwnerProfileId", batch)
                self.assertIn("app_user.user_key = @UserKey", batch)
                self.assertIn("owner_profile_id = @ProfileId", batch)

    def test_list_procedure_is_bounded(self):
        self.assertIn("TOP (200)", self.procedures["usp_ListKnowledgeItemsForOwner"])

    def test_list_procedure_returns_a_true_total_count_second_result_set(self):
        """BLOCKER 2 correction: a caller must be able to render an honest
        "Showing 200 of <true total>" rather than silently implying 200 is
        everything. The count query mirrors the same owner/visibility/
        archived-scope predicate as the TOP (200) read, minus the cap."""
        batch = self.procedures["usp_ListKnowledgeItemsForOwner"]
        self.assertIn("SELECT COUNT(*) AS total_count", batch)
        # Two SELECTs against knowledge_items in this batch: the bounded
        # list read and the unbounded true-count read.
        self.assertEqual(batch.count("FROM dbo.knowledge_items AS item"), 2)

    def test_get_procedure_history_is_bounded(self):
        self.assertIn("TOP (50)", self.procedures["usp_GetKnowledgeItemForOwner"])

    def test_save_procedure_is_idempotent_via_the_ledger(self):
        save = self.procedures["usp_SaveKnowledgeItemForOwner"]
        self.assertIn("knowledge_item_save_requests", save)
        self.assertIn("UPDLOCK, HOLDLOCK", save)
        self.assertIn("N''existing''", save)
        self.assertIn("N''success''", save)

    def test_idempotency_key_parameter_is_wide_enough_for_its_own_guard(self):
        """MINOR 11 correction: the parameter must be wider than the 200-unit
        limit it enforces, or an over-length value is silently truncated to
        200 before the guard below ever runs — the guard could never fire.
        The column itself (the real, enforced limit) stays nvarchar(200)."""
        save = self.procedures["usp_SaveKnowledgeItemForOwner"]
        self.assertIn("@IdempotencyKey nvarchar(4000)", save)
        self.assertIn("DATALENGTH(@IdempotencyKey) / 2 > 200", save)
        self.assertIn(
            "idempotency_key nvarchar(200) NOT NULL", self.forward
        )

    def test_child_deletes_reassert_owner_profile_id(self):
        """MINOR 8 correction: every predicate in usp_DeleteKnowledgeItemForOwner
        re-asserts owner_profile_id, including both child-table deletes, not
        only the parent knowledge_items delete."""
        delete = self.procedures["usp_DeleteKnowledgeItemForOwner"]
        self.assertIn(
            "DELETE dbo.knowledge_item_save_requests\n"
            "                WHERE knowledge_item_id = @KnowledgeItemId AND owner_profile_id = @ProfileId;",
            delete,
        )
        self.assertIn(
            "DELETE dbo.knowledge_item_versions\n"
            "                WHERE knowledge_item_id = @KnowledgeItemId AND owner_profile_id = @ProfileId;",
            delete,
        )

    def test_update_procedure_is_version_fenced(self):
        update = self.procedures["usp_UpdateKnowledgeItemForOwner"]
        self.assertIn("@ExpectedRowVersion binary(8)", update)
        self.assertIn("N''changed''", update)
        self.assertIn("row_version = @ExpectedRowVersion", update)

    def test_archive_restore_delete_are_version_fenced_and_owner_scoped(self):
        for name in (
            "usp_ArchiveKnowledgeItemForOwner",
            "usp_RestoreKnowledgeItemForOwner",
            "usp_DeleteKnowledgeItemForOwner",
        ):
            with self.subTest(procedure=name):
                batch = self.procedures[name]
                self.assertIn("@ExpectedRowVersion binary(8)", batch)
                self.assertIn("row_version = @ExpectedRowVersion", batch)
                self.assertIn("N''changed''", batch)

    def test_migration_and_rollback_fingerprint_exact_procedures(self):
        for sql in (self.forward, self.rollback):
            self.assertIn("PS_WORKSHOP_001_DEFINITION_HASH", sql)
            self.assertIn("HASHBYTES", sql)
            self.assertIn("OBJECT_DEFINITION", sql)
            self.assertIn("SHA2_256", sql)

    def test_rollback_refuses_on_data_later_migration_and_definition_drift(self):
        for value in (
            "Rollback refused",
            "a migration later than PS-WORKSHOP-001 is present",
            "a protected Workshop procedure changed after PS-WORKSHOP-001",
            "contains member records",
            "UPDLOCK, HOLDLOCK",
        ):
            self.assertIn(value, self.rollback)

    def test_rollback_drops_procedures_then_child_tables_then_parent(self):
        procedure_index = self.rollback.index("DROP PROCEDURE dbo.usp_ListKnowledgeItemsForOwner")
        save_requests_index = self.rollback.index("DROP TABLE dbo.knowledge_item_save_requests")
        versions_index = self.rollback.index("DROP TABLE dbo.knowledge_item_versions")
        items_index = self.rollback.index("DROP TABLE dbo.knowledge_items")

        self.assertLess(procedure_index, save_requests_index)
        self.assertLess(save_requests_index, versions_index)
        self.assertLess(versions_index, items_index)

    def test_verifier_has_two_owners_canaries_forged_key_and_outer_rollback(self):
        for value in (
            "@SubjectA",
            "@SubjectB",
            "@ProfileIdA",
            "@ProfileIdB",
            "@UserKeyA",
            "@UserKeyB",
            "usp_UpsertAppUserFromAuth",
            "MUST NOT ENTER OWNER A RESULT",
            "forged-user-key-does-not-exist",
            "A forged UserKey returned rows from the list read",
            "A forged UserKey produced a truthful-looking Save outcome",
            "A forged UserKey produced a truthful-looking Update outcome",
            "A forged UserKey produced a truthful-looking Archive outcome",
            "A forged UserKey produced a truthful-looking Restore outcome",
            "A forged UserKey produced a truthful-looking Delete outcome",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_object_definition_greps_check_all_seven_procedures(self):
        self.assertIn("OBJECT_DEFINITION", self.verification)
        self.assertIn("@UserKey nvarchar(300)", self.verification)
        self.assertIn("@OwnerProfileId", self.verification)  # named as a forbidden pattern
        self.assertIn("owner_profile_id = @ProfileId", self.verification)
        for name in PROCEDURE_NAMES:
            self.assertIn(name, self.verification)

    def test_verifier_never_ends_in_a_committed_state(self):
        self.assertNotIn("COMMIT TRANSACTION", self.verification)

    def test_application_allowlist_registration(self):
        database_source = (ROOT / "services" / "database_service.py").read_text(
            encoding="utf-8"
        )
        for name in PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertEqual(database_source.count(f'"{name}"'), 1)

    def test_apply_sql_migrations_registers_workshop(self):
        script_source = (ROOT / "scripts" / "apply_sql_migrations.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"PS-WORKSHOP-001"', script_source)
        self.assertIn("def verify_workshop(", script_source)
        self.assertIn("PS-WORKSHOP-001_knowledge_items.sql", script_source)
        self.assertIn("PS-WORKSHOP-001_owner_isolation_verify.sql", script_source)
        self.assertIn('if "PS-WORKSHOP-001" in args.migration', script_source)


@unittest.skipUnless(
    os.getenv("PS_WORKSHOP_SQL_GATE") == "1",
    "requires the isolated PS-WORKSHOP-001 SQL gate database",
)
class WorkshopIsolatedSqlGateTests(unittest.TestCase):
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
                "WHERE migration_id = N'PS-WORKSHOP-001'"
            ),
            1,
        )

        self.execute_script(ROLLBACK)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-WORKSHOP-001'"
            ),
            0,
        )
        self.assertIsNone(
            self.scalar("SELECT OBJECT_ID(N'dbo.usp_ListKnowledgeItemsForOwner', N'P')")
        )

        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-WORKSHOP-001'"
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
