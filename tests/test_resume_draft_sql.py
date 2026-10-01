"""Static contract checks for proposed PS-RESUME-DRAFT-001 SQL.

These tests do not claim SQL Server execution, transaction, concurrency,
rollback, or driver serialization proof. The registry gate stays null until a
separately authorized disposable-database proof is completed.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from services.database_service import ALLOWED_PROCEDURES
from services.entry_policy_repository import ENTRY_POLICY_WORKER_PROCEDURES
from services.resume_draft_repository import (
    RESUME_DRAFT_BROWSER_PROCEDURES,
    RESUME_DRAFT_WORKER_PROCEDURES,
    ResumeDraftStoreUnavailable,
    SqlResumeDraftRepository,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
FORWARD = MIGRATIONS / "PS-RESUME-DRAFT-001_resume_drafts.sql"
ROLLBACK = MIGRATIONS / "PS-RESUME-DRAFT-001_resume_drafts_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-RESUME-DRAFT-001_resume_drafts_verify.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"


class ResumeDraftSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registry_entry_requires_honest_null_or_matching_gate(self):
        entry = next(item for item in self.registry["migrations"] if item["id"] == "PS-RESUME-DRAFT-001")
        if entry["gate"] is not None:
            from scripts.migration_registry import load_registry, gate_status
            migration = load_registry(REGISTRY, ROOT).get(entry["id"])
            self.assertTrue(gate_status(migration, ROOT)[0])
        self.assertEqual(entry["requires"], ["PS-ENTRY-POLICY-001"])
        self.assertEqual(entry["forward"], "SQL FIles/Migrations/proposed/PS-RESUME-DRAFT-001_resume_drafts.sql")
        self.assertEqual(entry["rollback"], "SQL FIles/Migrations/proposed/PS-RESUME-DRAFT-001_resume_drafts_rollback.sql")

    def test_forward_sql_is_owner_keyed_serializable_and_closed(self):
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.forward)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", self.forward)
        self.assertIn("@UserKey", self.forward)
        self.assertNotIn("@OwnerProfileId", self.forward)
        self.assertIn("usp_CommitResumeDraftCommandForOwner", self.forward)
        self.assertIn("usp_GetResumeDraftForOwner", self.forward)
        self.assertIn("N'save_item'", self.forward)
        self.assertIn("N'review_candidate'", self.forward)
        self.assertIn("RESUME_DRAFT_IDEMPOTENCY_CONFLICT", self.forward)
        self.assertIn("RESUME_DRAFT_CHANGED", self.forward)
        self.assertIn("entry_policy_records", self.forward)
        self.assertIn("publishes", self.forward)
        self.assertIn("PROPOSED ONLY", self.forward)
        self.assertNotIn("usp_Publish", self.forward)
        self.assertNotIn("resume_display = 1", self.forward)
        self.assertIsNone(re.search(r"(?mi)^[ \t]*GO[ \t]*$", self.forward))

    def test_rollback_and_verify_are_structural_only(self):
        self.assertIn("DELETE dbo.schema_migrations", self.rollback)
        self.assertIn("PS-RESUME-DRAFT-001", self.rollback)
        self.assertIn("verified", self.verify)
        self.assertIn("runtime proof remains outstanding", self.verify)

    def test_reader_orders_receipts_by_the_recorded_commit_time(self):
        receipt_table = self.forward.split(
            "CREATE TABLE dbo.resume_draft_command_receipts", 1
        )[1].split("EXEC(N'", 1)[0]
        reader = self.forward.split(
            "CREATE OR ALTER PROCEDURE dbo.usp_GetResumeDraftForOwner", 1
        )[1].split("CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeDraftCommandForOwner", 1)[0]
        self.assertIn("committed_at_utc datetime2(7) NOT NULL", receipt_table)
        self.assertIn("ORDER BY receipt.committed_at_utc, receipt.request_id", reader)
        self.assertNotIn("receipt.created_at_utc", reader)

    def test_browser_procedures_are_allowlisted_and_workers_are_absent(self):
        for name in RESUME_DRAFT_BROWSER_PROCEDURES:
            self.assertIn(name, self.forward)
            self.assertIn(name, ALLOWED_PROCEDURES)
        self.assertFalse(RESUME_DRAFT_WORKER_PROCEDURES)
        for name in ENTRY_POLICY_WORKER_PROCEDURES:
            self.assertNotIn(name, ALLOWED_PROCEDURES)

    def test_sql_adapter_binds_owner_and_fail_closes_without_engine_proof(self):
        database = MagicMock()
        database.execute_procedure.return_value = [
            [{"draft_version": 2, "base_publication_version": None}],
            [],
        ]
        repository = SqlResumeDraftRepository(database)
        snapshot = repository.load_owner("owner-a")
        self.assertEqual(snapshot["draft_version"], 2)
        database.execute_procedure.assert_called_with(
            "usp_GetResumeDraftForOwner",
            [("@UserKey", "owner-a")],
        )
        database.execute_procedure.side_effect = ValueError("unapplied")
        with self.assertRaises(ResumeDraftStoreUnavailable):
            repository.load_owner("owner-a")


if __name__ == "__main__":
    unittest.main()
