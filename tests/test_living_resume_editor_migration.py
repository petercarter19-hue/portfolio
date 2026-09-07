"""Static contract checks for the proposed PS-RESUME-EDIT-001 SQL.

These tests deliberately do not claim SQL Server execution, transaction,
concurrency, rollback, or driver serialization proof. The registry gate stays
null until a separately authorized disposable-database proof is completed.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
FORWARD = MIGRATIONS / "PS-RESUME-EDIT-001_private_commands.sql"
ROLLBACK = MIGRATIONS / "PS-RESUME-EDIT-001_private_commands_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-RESUME-EDIT-001_private_commands_verify.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"


def procedure_batches(sql: str) -> dict[str, str]:
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


def assert_balanced_sql_delimiters(testcase: unittest.TestCase, encoded_sql: str) -> None:
    """Check delimiters after decoding the outer EXEC(N'...') SQL literal.

    This is deliberately a lexical static check. It catches stray parentheses
    without claiming that SQL Server compiled or executed the batch.
    """
    sql = encoded_sql.replace("''", "'")
    depth = 0
    index = 0
    state = "code"
    while index < len(sql):
        char = sql[index]
        following = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "code":
            if char == "'":
                state = "string"
            elif char == "-" and following == "-":
                state = "line_comment"
                index += 1
            elif char == "/" and following == "*":
                state = "block_comment"
                index += 1
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                testcase.assertGreaterEqual(depth, 0, "dynamic SQL has an unmatched closing parenthesis")
        elif state == "string":
            if char == "'" and following == "'":
                index += 1
            elif char == "'":
                state = "code"
        elif state == "line_comment":
            if char in "\r\n":
                state = "code"
        elif state == "block_comment" and char == "*" and following == "/":
            state = "code"
            index += 1
        index += 1
    testcase.assertEqual(state, "code", f"dynamic SQL ended in lexical state {state}")
    testcase.assertEqual(depth, 0, "dynamic SQL has unmatched opening parentheses")


class LivingResumeEditorMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)
        cls.command = cls.procedures["usp_CommitLivingResumeCommandForOwner"]
        cls.reader = cls.procedures["usp_GetOwnerLivingResumeEditor"]

    def test_forward_rollback_and_verification_are_bom_free(self):
        for path in (FORWARD, ROLLBACK, VERIFY):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertNotEqual(path.read_bytes()[:3], b"\xef\xbb\xbf")

    def test_exact_procedure_vocabulary_is_parseable(self):
        self.assertEqual(
            set(self.procedures),
            {"usp_GetOwnerLivingResumeEditor", "usp_CommitLivingResumeCommandForOwner"},
        )
        self.assertEqual(self.forward.count("CREATE OR ALTER PROCEDURE"), 2)

    def test_extracted_dynamic_procedure_sql_has_balanced_delimiters(self):
        for name, body in self.procedures.items():
            with self.subTest(procedure=name):
                assert_balanced_sql_delimiters(self, body)

    def test_static_delimiter_check_rejects_the_reviewed_extra_closing_shape(self):
        with self.assertRaisesRegex(AssertionError, "unmatched closing parenthesis"):
            assert_balanced_sql_delimiters(self, "IF EXISTS (SELECT 1));")

    def test_registry_is_proposed_and_requires_canonical_resume_domain(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["migrations"]
        entry = next(item for item in registry if item["id"] == "PS-RESUME-EDIT-001")
        self.assertEqual(entry["requires"], ["PS-PLAT-007"])
        self.assertIsNone(entry["gate"])
        self.assertIn("Repository candidate only", entry["summary"])

    def test_migration_and_command_are_transactional(self):
        for body in (self.forward, self.command):
            with self.subTest(scope="command" if body is self.command else "migration"):
                for token in (
                    "SET XACT_ABORT ON",
                    "BEGIN TRY",
                    "BEGIN TRANSACTION",
                    "COMMIT TRANSACTION",
                    "IF XACT_STATE() <> 0 ROLLBACK TRANSACTION",
                ):
                    self.assertIn(token, body)
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.command)

    def test_identity_is_derived_from_user_key_in_both_procedures(self):
        for name, body in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertIn("@UserKey nvarchar(300)", body)
                self.assertIn("JOIN dbo.app_users AS app_user", body)
                self.assertIn("app_user.active = 1", body)
                self.assertIn("profile.active = 1", body)
                self.assertNotIn("@OwnerProfileId", body)

    def test_command_surface_is_closed_and_owner_scoped(self):
        for command_type in (
            "create_role", "update_role", "remove_role",
            "create_accomplishment", "update_accomplishment", "remove_accomplishment",
            "create_skill", "update_skill", "remove_skill",
            "create_credential", "update_credential", "remove_credential",
        ):
            self.assertIn(command_type, self.command)
        for forbidden in ("owner_profile_id'', N''visibility", "source_table'', N''publication_status"):
            self.assertNotIn(forbidden, self.command)
        self.assertIn("WHERE receipt.owner_profile_id = @ProfileId", self.command)

    def test_idempotency_receipt_is_locked_and_written_after_mutations(self):
        self.assertIn("UQ_living_resume_command_receipts_owner_command", self.forward)
        self.assertIn("HASHBYTES(''SHA2_256''", self.command)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", self.command)
        self.assertIn("RESUME_EDITOR_IDEMPOTENCY_CONFLICT", self.command)
        receipt_insert = self.command.rindex("INSERT dbo.living_resume_command_receipts")
        self.assertGreater(receipt_insert, self.command.index("UPDATE dbo.career_chapters"))
        self.assertGreater(receipt_insert, self.command.index("UPDATE dbo.career_achievements"))
        self.assertGreater(receipt_insert, self.command.index("UPDATE dbo.career_skills"))

    def test_subtype_writes_are_fenced_by_parent_versions(self):
        self.assertIn("chapter.row_version", self.command)
        self.assertIn("career_experiences", self.command)
        self.assertIn("career_credentials", self.command)
        self.assertGreaterEqual(self.command.count("row_version=@ExpectedVersion"), 6)
        self.assertIn("N''changed'' AS error_code", self.command)
        self.assertIn("JOIN dbo.career_experiences AS experience WITH (UPDLOCK, HOLDLOCK)", self.command)
        self.assertIn("JOIN dbo.career_credentials AS credential WITH (UPDLOCK, HOLDLOCK)", self.command)
        self.assertGreaterEqual(self.command.count("IF @@ROWCOUNT <> 1 THROW 52003"), 6)

    def test_long_editor_text_uses_nvarchar_max_extraction_and_8000_bounds(self):
        self.assertNotIn("JSON_VALUE(@CommandJson, ''$.values.summary'')", self.command)
        self.assertNotIn("JSON_VALUE(@CommandJson, ''$.values.wording'')", self.command)
        self.assertEqual(self.command.count("WITH (summary nvarchar(max) N''$.summary'')"), 4)
        self.assertEqual(self.command.count("WITH (wording nvarchar(max) N''$.wording'')"), 2)
        for value in (
            "@RoleSummary",
            "@Wording",
            "@SkillSummary",
            "@UpdateRoleSummary",
            "@UpdateWording",
            "@UpdateSkillSummary",
        ):
            self.assertIn(f"LEN({value}) > 8000", self.command)

    def test_accomplishment_mutation_relocks_private_experience_parent(self):
        discovery = "FROM dbo.career_achievements AS achievement WITH (READUNCOMMITTED)"
        parent_lock = "FROM dbo.career_chapters AS parent_chapter WITH (UPDLOCK, HOLDLOCK)"
        child_lock = "FROM dbo.career_achievements AS achievement WITH (UPDLOCK, HOLDLOCK)"
        self.assertIn(discovery, self.command)
        self.assertIn("@ExperienceParentValid bit", self.command)
        self.assertIn(parent_lock, self.command)
        self.assertIn("FROM dbo.career_experiences AS parent_experience WITH (UPDLOCK, HOLDLOCK)", self.command)
        self.assertIn("JOIN dbo.slate_entities AS parent_entity WITH (UPDLOCK, HOLDLOCK)", self.command)
        self.assertIn("parent_chapter.owner_profile_id = @ProfileId", self.command)
        self.assertIn("parent_chapter.chapter_type = N''experience''", self.command)
        self.assertIn("parent_chapter.visibility = N''private''", self.command)
        self.assertIn("parent_chapter.publication_status = N''unpublished''", self.command)
        self.assertIn("achievement.chapter_id = @CandidateChapterId", self.command)
        self.assertLess(self.command.index(discovery), self.command.index(parent_lock))
        self.assertLess(self.command.index(parent_lock), self.command.index(child_lock))
        self.assertIn("IF @EntityId IS NOT NULL AND @ExperienceParentValid IS NULL", self.command)

    def test_publication_history_and_relations_block_mutation(self):
        for token in (
            "entity_publication_versions",
            "entity_access_grants",
            "content_approval_events",
            "slate_entity_relations",
            "career_skill_links",
            "evidence_links",
            "ai_proposals",
            "RESUME_EDITOR_PROTECTED",
        ):
            self.assertIn(token, self.command)
        self.assertIn("counterpart.visibility <> N''private''", self.command)
        self.assertIn("link.approval_status <> N''proposed''", self.command)

    def test_private_remove_covers_chapter_children_and_relation_rows(self):
        for token in (
            "DELETE FROM dbo.career_timeline_events",
            "UPDATE dbo.career_achievements",
            "UPDATE dbo.career_chapters",
            "UPDATE dbo.career_skills",
            "DELETE relation FROM dbo.slate_entity_relations",
            "DELETE link FROM dbo.career_skill_links",
            "DELETE evidence_link FROM dbo.evidence_links",
            "UPDATE entity",
        ):
            self.assertIn(token, self.command)
        self.assertIn("JOIN @AffectedEntities", self.command)

    def test_credential_status_is_nullable_only_for_legacy_rows(self):
        self.assertIn("credential_completion_status nvarchar(30) NULL", self.forward)
        self.assertIn("credential_completion_status IS NULL OR", self.forward)
        self.assertIn("N''planned'',N''in_progress'',N''completed''", self.command)
        self.assertIn("@CompletionStatus = N''completed'' AND @IssueDate IS NULL", self.command)

    def test_editor_read_returns_row_versions_and_block_reasons(self):
        self.assertEqual(self.reader.count("row_version"), 4)
        self.assertEqual(self.reader.count("AS editable"), 4)
        self.assertEqual(self.reader.count("AS blocked_reason"), 4)
        self.assertIn("credential_completion_status AS completion_status", self.reader)

    def test_rollback_removes_only_this_additive_contract(self):
        for token in (
            "DROP PROCEDURE IF EXISTS dbo.usp_CommitLivingResumeCommandForOwner",
            "DROP PROCEDURE IF EXISTS dbo.usp_GetOwnerLivingResumeEditor",
            "DROP TABLE IF EXISTS dbo.living_resume_command_receipts",
            "DROP COLUMN credential_completion_status",
            "migration_id = N'PS-RESUME-EDIT-001'",
        ):
            self.assertIn(token, self.rollback)
        self.assertNotIn("DROP TABLE IF EXISTS dbo.career_", self.rollback)
        self.assertIn("Rollback refused: Living Resume command receipts are stored.", self.rollback)
        self.assertIn("Rollback refused: explicit credential completion states are stored.", self.rollback)

    def test_verifier_truthfully_keeps_runtime_proof_outstanding(self):
        self.assertIn("runtime proof remains outstanding", self.verification)
        self.assertIn("structural object contract only", self.verification)
        self.assertNotIn("gate_database", self.verification)


if __name__ == "__main__":
    unittest.main()
