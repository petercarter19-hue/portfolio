"""Contracts and optional two-connection proof for PS-WORKSHOP-004."""

import json
import os
import re
import unittest
import uuid
from pathlib import Path

from scripts.migration_registry import executable_sha256


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
BASE_FORWARD = MIGRATIONS / "proposed" / "PS-WORKSHOP-001_knowledge_items.sql"
FORWARD = MIGRATIONS / "PS-WORKSHOP-004_knowledge_edit_provenance.sql"
ROLLBACK = MIGRATIONS / "PS-WORKSHOP-004_knowledge_edit_provenance_rollback.sql"
VERIFY = VERIFICATION / "PS-WORKSHOP-004_owner_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
PROCEDURE = "usp_UpdateKnowledgeItemForOwner"


def read(path):
    return path.read_text(encoding="utf-8")


def procedure_batches(sql):
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


def migration_wrapper(sql):
    return re.sub(r"EXEC\(N'(?:''|[^'])*'\);", "", sql, flags=re.DOTALL)


def signature(batch):
    match = re.search(
        rf"CREATE OR ALTER PROCEDURE dbo\.{PROCEDURE}(.*?)\n\s*AS\n",
        batch,
        flags=re.DOTALL,
    )
    if not match:
        raise AssertionError("procedure signature not found")
    return match.group(1)


class WorkshopEditProvenanceMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_forward = read(BASE_FORWARD)
        cls.forward = read(FORWARD)
        cls.rollback = read(ROLLBACK)
        cls.verification = read(VERIFY)
        cls.base_procedure = procedure_batches(cls.base_forward)[PROCEDURE]
        cls.forward_procedure = procedure_batches(cls.forward)[PROCEDURE]
        cls.rollback_procedure = procedure_batches(cls.rollback)[PROCEDURE]

    def test_claimed_files_exist_and_are_single_guarded_batches(self):
        for path in (FORWARD, ROLLBACK, VERIFY):
            self.assertTrue(path.exists())
            source = read(path)
            self.assertNotIn("\nGO", source)
            self.assertEqual(source.count("/*"), source.count("*/"))
        for source in (self.forward, self.rollback):
            for fragment in (
                "SET XACT_ABORT ON",
                "BEGIN TRY",
                "BEGIN TRANSACTION",
                "COMMIT TRANSACTION",
                "BEGIN CATCH",
                "ROLLBACK TRANSACTION",
                "THROW;",
            ):
                self.assertIn(fragment, source)

    def test_forward_replaces_only_the_edit_procedure(self):
        self.assertEqual(set(procedure_batches(self.forward)), {PROCEDURE})
        self.assertEqual(self.forward.count("CREATE OR ALTER PROCEDURE"), 1)

    def test_input_signature_is_byte_identical_and_has_no_original_parameter(self):
        self.assertEqual(
            signature(self.forward_procedure), signature(self.base_procedure)
        )
        self.assertNotIn("@OriginalWording", signature(self.forward_procedure))
        self.assertNotIn(
            "@OriginalMemberWording", signature(self.forward_procedure)
        )

    def test_result_shapes_remain_the_existing_changed_and_success_shapes(self):
        for fragment in (
            "SELECT N''changed'' AS outcome,",
            "CAST(NULL AS int) AS version_number,",
            "CAST(NULL AS binary(8)) AS row_version;",
            "SELECT N''success'' AS outcome,",
            "@NextVersionNumber AS version_number,",
            "item.row_version",
        ):
            self.assertIn(fragment, self.base_procedure)
            self.assertIn(fragment, self.forward_procedure)

    def test_first_apply_requires_workshop_003_and_live_workshop_001_hash(self):
        wrapper = migration_wrapper(self.forward)
        for fragment in (
            "migration_id = N'PS-WORKSHOP-003'",
            "PS_WORKSHOP_001_DEFINITION_HASH",
            "OBJECT_DEFINITION",
            "HASHBYTES('SHA2_256'",
            "live Workshop edit procedure does not match",
        ):
            self.assertIn(fragment, wrapper)

    def test_reapply_is_hash_validated_and_returns_without_ddl(self):
        wrapper = migration_wrapper(self.forward)
        self.assertIn("@MigrationAlreadyApplied", wrapper)
        self.assertIn("PS_WORKSHOP_004_DEFINITION_HASH", wrapper)
        applied_branch = wrapper.split("IF @MigrationAlreadyApplied = 1", 1)[1].split(
            "IF NOT EXISTS\n    (\n        SELECT 1\n        FROM sys.extended_properties", 1
        )[0]
        self.assertIn("COMMIT TRANSACTION", applied_branch)
        self.assertIn("RETURN", applied_branch)

    def test_current_source_read_is_exact_owned_locked_and_has_no_fallback(self):
        body = self.forward_procedure
        source_read = re.search(
            r"SELECT @OriginalMemberWording = version_record\.original_member_wording"
            r"(.*?)IF @OriginalMemberWording IS NULL",
            body,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(source_read)
        source = source_read.group(1)
        for fragment in (
            "WITH (UPDLOCK, HOLDLOCK)",
            "version_record.knowledge_item_id = @KnowledgeItemId",
            "version_record.owner_profile_id = @ProfileId",
            "version_record.version_number = @CurrentVersionNumber",
        ):
            self.assertIn(fragment, source)
        for forbidden in ("COALESCE", "ISNULL", "@ApprovedWording"):
            self.assertNotIn(forbidden, source)
        self.assertIn("THROW 53508", body)

    def test_new_version_copies_stored_source_and_is_typed(self):
        self.assertIn(
            "@ApprovedWording, @OriginalMemberWording, @BodyFormat,\n"
            "                    N''typed'', @UserId",
            self.forward_procedure,
        )
        self.assertNotIn(
            "@ApprovedWording, @ApprovedWording, @BodyFormat",
            self.forward_procedure,
        )
        self.assertEqual(
            self.forward_procedure.count("INSERT dbo.knowledge_item_versions"), 1
        )
        self.assertNotIn("UPDATE dbo.knowledge_item_versions", self.forward_procedure)
        self.assertNotIn("DELETE dbo.knowledge_item_versions", self.forward_procedure)

    def test_parent_advance_reasserts_every_admission_predicate_and_rowcount(self):
        update = re.search(
            r"UPDATE item\s+SET(.*?)IF @@ROWCOUNT <> 1",
            self.forward_procedure,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(update)
        statement = update.group(1)
        for fragment in (
            "item.knowledge_item_id = @KnowledgeItemId",
            "item.owner_profile_id = @ProfileId",
            "item.knowledge_item_key = @KnowledgeItemKey",
            "item.visibility = N''private''",
            "item.item_status <> N''archived''",
            "item.current_version_number = @CurrentVersionNumber",
            "item.row_version = @ExpectedRowVersion",
        ):
            self.assertIn(fragment, statement)
        self.assertIn("THROW 53509", self.forward_procedure)

    def test_rollback_is_tip_guarded_and_restores_exact_workshop_001_literal(self):
        for fragment in (
            "a migration later than PS-WORKSHOP-004 is present",
            "PS-WORKSHOP-004 is not the migration-ledger tip",
            "PS_WORKSHOP_004_DEFINITION_HASH",
            "PS_WORKSHOP_001_DEFINITION_HASH",
            "OBJECT_DEFINITION",
            "HASHBYTES('SHA2_256'",
        ):
            self.assertIn(fragment, self.rollback)
        self.assertEqual(self.rollback_procedure, self.base_procedure)

    def test_rollback_control_flow_never_mutates_member_rows(self):
        wrapper = migration_wrapper(self.rollback)
        for forbidden in (
            "UPDATE dbo.knowledge_items",
            "DELETE dbo.knowledge_items",
            "UPDATE dbo.knowledge_item_versions",
            "DELETE dbo.knowledge_item_versions",
        ):
            self.assertNotIn(forbidden, wrapper)
        self.assertIn(
            "DELETE dbo.schema_migrations\n    WHERE migration_id = N'PS-WORKSHOP-004'",
            wrapper,
        )
        self.assertNotIn("migration_id = N'PS-WORKSHOP-003'", wrapper)

    def test_verifier_covers_bytes_neutrality_history_and_transactional_invariant(self):
        for fragment in (
            "PS_WORKSHOP_004_DEFINITION_HASH",
            "PS_WORKSHOP_003_DEFINITION_HASH",
            "FROM sys.parameters",
            "name IN (N'@OriginalWording', N'@OriginalMemberWording')",
            "DATALENGTH(original_member_wording)",
            "HASHBYTES('SHA2_256'",
            "version_number = 2",
            "version_number = 3",
            "authored_via = N'typed'",
            "usp_ListKnowledgeItemVersionsForOwner",
            "total_count = 3 AND is_truncated = 0",
            "foreign owner",
            "foreign item key",
            "forged owner key",
            "unknown item key",
            "archived item",
            "stale rowversion",
            "ERROR_NUMBER() <> 53508",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        ):
            self.assertIn(fragment, self.verification)

    def test_registry_appends_workshop_004_after_003_without_global_tip_assumption(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        entry = entries["PS-WORKSHOP-004"]
        self.assertEqual(entry["requires"], ["PS-WORKSHOP-003"])
        self.assertLess(ids.index("PS-WORKSHOP-003"), ids.index("PS-WORKSHOP-004"))
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-WORKSHOP-004_knowledge_edit_provenance.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-WORKSHOP-004_knowledge_edit_provenance_rollback.sql",
        )
        if entry["gate"] is not None:
            self.assertEqual(
                entry["gate"]["executable_sha256"], executable_sha256(FORWARD)
            )
            self.assertIn("PS-WORKSHOP-003", entry["gate"]["prerequisites"])
            self.assertIn("verified = 1", entry["gate"]["verification"])

    def test_throw_numbers_are_unique_within_each_owned_file(self):
        for label, source in (
            ("forward", self.forward),
            ("rollback", self.rollback),
            ("verification", self.verification),
        ):
            with self.subTest(file=label):
                numbers = re.findall(r"THROW (\d+),", source)
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)))


@unittest.skipUnless(
    os.getenv("PS_WORKSHOP_004_SQL_GATE") == "1"
    and bool(os.getenv("PS_WORKSHOP_004_GATE_DATABASE")),
    "requires the disposable PS-WORKSHOP-004 SQL gate database",
)
class WorkshopEditProvenanceTwoConnectionGateTests(unittest.TestCase):
    """Real lock/old-token proof, run inside the one disposable gate lifecycle."""

    @classmethod
    def setUpClass(cls):
        cls.database = os.environ["PS_WORKSHOP_004_GATE_DATABASE"]
        env_path = os.getenv("PS_WORKSHOP_004_ENV_FILE")
        cls.env_file = Path(env_path) if env_path else None

    def connect(self):
        from scripts.govern_sql_migrations import open_connection

        return open_connection(self.env_file, database=self.database)

    @staticmethod
    def result_rows(cursor):
        rows = []
        while True:
            if cursor.description is not None:
                columns = [column[0] for column in cursor.description]
                rows.extend(dict(zip(columns, row)) for row in cursor.fetchall())
            if not cursor.nextset():
                return rows

    def test_a_holds_lock_b_times_out_then_old_token_is_neutral(self):
        suffix = str(uuid.uuid4())
        provider = "workshop-edit-provenance-concurrency"
        issuer = "urn:peerslate:workshop-edit-provenance-concurrency"
        subject = f"workshop-edit-concurrency-{suffix}"
        item_key = str(uuid.uuid4())
        source = "  CONCURRENCY SOURCE Ω 漢字  "
        approved_one = "Concurrency approved version one"
        approved_two = "Concurrency approved version two"

        with self.connect() as setup:
            setup.setautocommit(True)
            cursor = setup.cursor()
            cursor.execute(
                "EXEC dbo.usp_UpsertAppUserFromAuth "
                "@AuthProvider=?, @AuthIssuer=?, @AuthSubject=?, @DisplayName=?",
                provider,
                issuer,
                subject,
                "Workshop edit concurrency owner",
            )
            self.result_rows(cursor)
            cursor.execute(
                "SELECT app_user.user_key, profile.profile_id, app_user.id "
                "FROM dbo.app_users AS app_user "
                "JOIN dbo.user_identities AS identity_record "
                "ON identity_record.user_id=app_user.id "
                "JOIN dbo.member_profiles AS profile ON profile.user_id=app_user.id "
                "WHERE identity_record.provider=? AND identity_record.issuer=? "
                "AND identity_record.subject=?",
                provider,
                issuer,
                subject,
            )
            user_key, profile_id, user_id = cursor.fetchone()
            cursor.execute(
                "INSERT dbo.knowledge_items "
                "(knowledge_item_key,owner_profile_id,item_status,classification,current_version_number) "
                "OUTPUT INSERTED.knowledge_item_id,CONVERT(binary(8),INSERTED.row_version) "
                "VALUES (CONVERT(uniqueidentifier,?),?,N'unfinished',N'work',1)",
                item_key,
                profile_id,
            )
            item_id, old_token = cursor.fetchone()
            cursor.execute(
                "INSERT dbo.knowledge_item_versions "
                "(knowledge_item_id,owner_profile_id,version_number,title,approved_wording,"
                "original_member_wording,body_format,authored_via,saved_by_user_id) "
                "VALUES (?,?,1,N'Concurrency v1',?,?,N'plain',N'typed',?)",
                item_id,
                profile_id,
                approved_one,
                source,
                user_id,
            )
            cursor.execute(
                "SELECT COUNT(*) FROM dbo.audit_events "
                "WHERE action_type=N'knowledge_item.updated' "
                "AND entity_key=CONVERT(uniqueidentifier,?)",
                item_key,
            )
            audit_before = cursor.fetchone()[0]

        connection_a = self.connect()
        connection_b = self.connect()
        try:
            # Autocommit plus one explicit transaction keeps @@TRANCOUNT
            # exact: the procedure's nested BEGIN/COMMIT returns it to one,
            # and the explicit COMMIT below releases A's retained lock.
            connection_a.setautocommit(True)
            connection_b.setautocommit(True)
            cursor_a = connection_a.cursor()
            cursor_b = connection_b.cursor()

            cursor_a.execute(
                "SET LOCK_TIMEOUT 5000; BEGIN TRANSACTION; "
                "SELECT knowledge_item_id FROM dbo.knowledge_items WITH (UPDLOCK,HOLDLOCK) "
                "WHERE knowledge_item_id=? AND owner_profile_id=?",
                item_id,
                profile_id,
            )
            self.assertEqual(cursor_a.fetchone()[0], item_id)
            cursor_a.execute(
                "EXEC dbo.usp_UpdateKnowledgeItemForOwner "
                "@UserKey=?, @KnowledgeItemKey=?, "
                "@ExpectedRowVersion=?, @Title=N'Concurrency v2', "
                "@ApprovedWording=?, @BodyFormat=N'plain', "
                "@Classification=N'work', @Confirm=0",
                user_key,
                item_key,
                bytes(old_token),
                approved_two,
            )
            result_a = self.result_rows(cursor_a)
            self.assertTrue(any(row.get("outcome") == "success" for row in result_a))

            with self.assertRaises(Exception) as blocked:
                cursor_b.execute(
                    "SET LOCK_TIMEOUT 1500; EXEC dbo.usp_UpdateKnowledgeItemForOwner "
                    "@UserKey=?, @KnowledgeItemKey=?, "
                    "@ExpectedRowVersion=?, @Title=N'Blocked v2', "
                    "@ApprovedWording=N'Blocked wording', @BodyFormat=N'plain', "
                    "@Classification=N'work', @Confirm=0",
                    user_key,
                    item_key,
                    bytes(old_token),
                )
                self.result_rows(cursor_b)
            self.assertTrue(
                "1222" in str(blocked.exception)
                or "Lock request time out" in str(blocked.exception)
            )

            cursor_a.execute("COMMIT TRANSACTION")
            # mssql-python deliberately treats the server-side lock-timeout
            # rollback as a broken communication context. Reconnect the same
            # logical B actor before proving its old token is now neutral.
            connection_b.close()
            connection_b = self.connect()
            connection_b.setautocommit(True)
            cursor_b = connection_b.cursor()
            cursor_b.execute("SET LOCK_TIMEOUT -1")
            cursor_b.execute(
                "EXEC dbo.usp_UpdateKnowledgeItemForOwner "
                "@UserKey=?, @KnowledgeItemKey=?, "
                "@ExpectedRowVersion=?, @Title=N'Old token retry', "
                "@ApprovedWording=N'Old token retry wording', @BodyFormat=N'plain', "
                "@Classification=N'work', @Confirm=0",
                user_key,
                item_key,
                bytes(old_token),
            )
            retry = self.result_rows(cursor_b)
            self.assertEqual(
                [
                    (
                        row.get("outcome"),
                        row.get("version_number"),
                        row.get("row_version"),
                    )
                    for row in retry
                ],
                [("changed", None, None)],
            )

            cursor_b.execute(
                "SELECT current_version_number FROM dbo.knowledge_items "
                "WHERE knowledge_item_id=? AND owner_profile_id=?",
                item_id,
                profile_id,
            )
            self.assertEqual(cursor_b.fetchone()[0], 2)
            cursor_b.execute(
                "SELECT approved_wording,original_member_wording,authored_via "
                "FROM dbo.knowledge_item_versions "
                "WHERE knowledge_item_id=? AND owner_profile_id=? AND version_number=2",
                item_id,
                profile_id,
            )
            self.assertEqual(tuple(cursor_b.fetchone()), (approved_two, source, "typed"))
            cursor_b.execute(
                "SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id=?",
                item_id,
            )
            self.assertEqual(cursor_b.fetchone()[0], 2)
            cursor_b.execute(
                "SELECT COUNT(*) FROM dbo.audit_events "
                "WHERE action_type=N'knowledge_item.updated' "
                "AND entity_key=CONVERT(uniqueidentifier,?)",
                item_key,
            )
            self.assertEqual(cursor_b.fetchone()[0], audit_before + 1)
        finally:
            try:
                connection_a.rollback()
            except Exception:
                pass
            connection_a.close()
            connection_b.close()


if __name__ == "__main__":
    unittest.main()
