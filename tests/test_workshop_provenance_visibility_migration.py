"""Static and registry contracts for PS-WORKSHOP-003 wording history."""

import json
import re
import unittest
from pathlib import Path

from scripts.migration_registry import executable_sha256


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
REGISTRY = MIGRATIONS / "registry.json"
FORWARD = MIGRATIONS / "PS-WORKSHOP-003_knowledge_version_history_read.sql"
ROLLBACK = MIGRATIONS / "PS-WORKSHOP-003_knowledge_version_history_read_rollback.sql"
VERIFY = VERIFICATION / "PS-WORKSHOP-003_owner_isolation_verify.sql"
PROCEDURE = "usp_ListKnowledgeItemVersionsForOwner"


def read(path):
    return path.read_text(encoding="utf-8")


class WorkshopProvenanceVisibilityMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = read(FORWARD)
        cls.rollback = read(ROLLBACK)
        cls.verification = read(VERIFY)

    def test_registry_requires_workshop_002_and_uses_claimed_paths(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        entry = entries["PS-WORKSHOP-003"]
        ids = [item["id"] for item in document["migrations"]]

        self.assertEqual(entry["requires"], ["PS-WORKSHOP-002"])
        self.assertLess(ids.index("PS-WORKSHOP-002"), ids.index("PS-WORKSHOP-003"))
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-WORKSHOP-003_knowledge_version_history_read.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-WORKSHOP-003_knowledge_version_history_read_rollback.sql",
        )
        if entry["gate"] is not None:
            self.assertEqual(
                entry["gate"]["executable_sha256"], executable_sha256(FORWARD)
            )
            self.assertIn("PS-WORKSHOP-002", entry["gate"]["prerequisites"])
            self.assertIn("verified = 1", entry["gate"]["verification"])

    def test_forward_is_additive_read_only_and_owner_scoped(self):
        self.assertIn(f"CREATE OR ALTER PROCEDURE dbo.{PROCEDURE}", self.forward)
        self.assertIn("@UserKey nvarchar(300)", self.forward)
        self.assertIn("@KnowledgeItemKey uniqueidentifier", self.forward)
        self.assertNotIn("@OwnerProfileId", self.forward)
        self.assertIn("app_user.user_key = @UserKey", self.forward)
        self.assertIn("item.owner_profile_id = @ProfileId", self.forward)
        self.assertIn("item.visibility = N''private''", self.forward)
        self.assertIn("version_record.owner_profile_id = @ProfileId", self.forward)

        procedure_match = re.search(
            rf"CREATE OR ALTER PROCEDURE dbo\.{PROCEDURE}(.*?)\n\s*END;\n\s*'\);",
            self.forward,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(procedure_match)
        procedure_body = re.sub(
            r"/\*.*?\*/", "", procedure_match.group(1), flags=re.DOTALL
        ).upper()
        self.assertEqual(procedure_body.count("INSERT @VERSIONSNAPSHOT"), 1)
        for mutation in ("INSERT DBO.", "UPDATE ", "DELETE ", "MERGE "):
            self.assertNotIn(mutation, procedure_body)

    def test_exact_wording_timestamp_bound_and_metadata_are_selected(self):
        for field in (
            "version_record.version_number",
            "version_record.approved_wording",
            "version_record.original_member_wording",
            "version_record.saved_at_utc",
        ):
            self.assertIn(field, self.forward)
        self.assertIn("SELECT TOP (50)", self.forward)
        self.assertIn("ORDER BY version_record.version_number DESC", self.forward)
        self.assertIn("COUNT_BIG(*) OVER ()", self.forward)
        self.assertIn("INSERT @VersionSnapshot", self.forward)
        self.assertIn("@TotalCount AS total_count", self.forward)
        self.assertIn("AS is_truncated", self.forward)
        self.assertNotIn("COALESCE(version_record.original_member_wording", self.forward)
        self.assertNotIn("ISNULL(version_record.original_member_wording", self.forward)

    def test_rows_and_metadata_derive_from_one_materialized_source_statement(self):
        procedure_literal = self.forward.split("EXEC(N'", 1)[1].split(
            "\n    ');", 1
        )[0]
        self.assertEqual(
            procedure_literal.count(
                "FROM dbo.knowledge_item_versions AS version_record"
            ),
            1,
        )
        self.assertIn("COUNT_BIG(*) OVER () AS total_count", procedure_literal)
        self.assertIn("INSERT @VersionSnapshot", procedure_literal)
        self.assertIn("FROM @VersionSnapshot AS snapshot", procedure_literal)
        self.assertGreaterEqual(
            procedure_literal.count("FROM @VersionSnapshot AS snapshot"), 2
        )

    def test_w4_production_tip_and_prior_ledger_selects_w3_for_rollback(self):
        registry_document = json.loads(read(REGISTRY))
        registry_ids = [entry["id"] for entry in registry_document["migrations"]]
        state_text = read(ROOT / "docs" / "governance" / "PRODUCTION_SCHEMA_STATE.md")
        state_document = json.loads(
            state_text.split("```json", 1)[1].split("```", 1)[0]
        )
        current_ledger = {entry["id"] for entry in state_document["applied"]}

        production_in_registry_order = [
            migration_id
            for migration_id in registry_ids
            if migration_id in current_ledger
        ]
        # This pin is the production tip in registry order and moves with
        # each authorized production apply batch -- that is its purpose: any
        # movement of what production carries must be an explicit, reviewed
        # decision here. 2026-09-01: the owner-authorized eight-migration
        # account-export batch (PS-SETTINGS-EXPORT-001, 003-009) moved the
        # tip from PS-WORKSHOP-004.
        self.assertEqual(production_in_registry_order[-1], "PS-SETTINGS-EXPORT-009")

        # The selector property this test exists for, now stated
        # tip-relative so it can never silently go stale: removing the
        # current tip selects exactly its registry-order predecessor
        # within the applied set.
        tip = production_in_registry_order[-1]
        prior_ledger = current_ledger - {tip}
        applied_in_registry_order = [
            migration_id
            for migration_id in registry_ids
            if migration_id in prior_ledger
        ]
        self.assertEqual(
            applied_in_registry_order[-1], production_in_registry_order[-2]
        )

        # And the original migration-specific guarantee, preserved within
        # the Workshop family: with W4 rolled back to W3, W3 is the
        # workshop tip.
        workshop_prior = (current_ledger - {"PS-WORKSHOP-004"}) | {"PS-WORKSHOP-003"}
        workshop_in_registry_order = [
            migration_id
            for migration_id in registry_ids
            if migration_id in workshop_prior and migration_id.startswith("PS-WORKSHOP-")
        ]
        self.assertEqual(workshop_in_registry_order[-1], "PS-WORKSHOP-003")

    def test_unknown_foreign_and_forged_inputs_share_neutral_query_shape(self):
        procedure_literal = self.forward.split("EXEC(N'", 1)[1].split(
            "\n    ');", 1
        )[0]
        self.assertNotIn("THROW 53", procedure_literal)
        self.assertIn("DECLARE @TotalCount bigint = 0", self.forward)
        self.assertIn("WHERE version_record.knowledge_item_id = @KnowledgeItemId", self.forward)
        self.assertIn("CASE WHEN @TotalCount > 50 THEN 1 ELSE 0 END", self.forward)

    def test_definition_fingerprint_guards_noop_and_rollback(self):
        for sql in (self.forward, self.rollback):
            self.assertIn("PS_WORKSHOP_003_DEFINITION_HASH", sql)
            self.assertIn("OBJECT_DEFINITION", sql)
            self.assertIn("HASHBYTES", sql)
        self.assertIn("@MigrationAlreadyApplied", self.forward)
        self.assertIn("CREATE OR ALTER PROCEDURE", self.forward)
        self.assertIn(f"DROP PROCEDURE dbo.{PROCEDURE}", self.rollback)
        self.assertIn(
            "a migration later than PS-WORKSHOP-003 is present", self.rollback
        )
        self.assertNotIn("UPDATE dbo.knowledge_items", self.rollback)
        self.assertNotIn("DELETE dbo.knowledge_items", self.rollback)
        self.assertNotIn("UPDATE dbo.knowledge_item_versions", self.rollback)
        self.assertNotIn("DELETE dbo.knowledge_item_versions", self.rollback)

    def test_verifier_proves_required_owner_and_byte_boundaries(self):
        required_fragments = (
            "@Version <= 55",
            "<> 50",
            "total_count = 55 AND is_truncated = 1",
            "DATALENGTH(approved_wording)",
            "DATALENGTH(original_member_wording)",
            "HASHBYTES('SHA2_256'",
            "forged-workshop-history-owner",
            "A foreign owner",
            "A foreign item key",
            "An unknown item key",
            "OWNER B APPROVED SECRET",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, self.verification)
        self.assertNotIn("LAG(version_number)", self.verification)
        self.assertIn("COUNT(DISTINCT version_number)", self.verification)

    def test_files_are_single_batch_and_error_numbers_do_not_collide(self):
        for label, sql in (
            ("forward", self.forward),
            ("rollback", self.rollback),
            ("verification", self.verification),
        ):
            with self.subTest(file=label):
                self.assertFalse(
                    any(line.strip().upper() == "GO" for line in sql.splitlines())
                )
                numbers = re.findall(r"THROW (\d+),", sql)
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)))


if __name__ == "__main__":
    unittest.main()
