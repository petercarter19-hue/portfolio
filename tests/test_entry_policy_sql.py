"""Static contract checks for proposed PS-ENTRY-POLICY-001 SQL.

These tests do not claim SQL Server execution, transaction, concurrency,
rollback, or driver serialization proof. The registry gate stays null until a
separately authorized disposable-database proof is completed.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from services.database_service import ALLOWED_PROCEDURES
from services.entry_policy_repository import (
    ENTRY_POLICY_BROWSER_PROCEDURES,
    ENTRY_POLICY_WORKER_PROCEDURES,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
FORWARD = MIGRATIONS / "PS-ENTRY-POLICY-001_entry_metadata.sql"
ROLLBACK = MIGRATIONS / "PS-ENTRY-POLICY-001_entry_metadata_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-ENTRY-POLICY-001_entry_metadata_verify.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"


class EntryPolicySqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registry_entry_is_proposed_with_null_gate(self):
        entry = next(item for item in self.registry["migrations"] if item["id"] == "PS-ENTRY-POLICY-001")
        self.assertIsNone(entry["gate"])
        self.assertEqual(entry["requires"], ["PS-RESUME-EDIT-002"])
        self.assertEqual(entry["forward"], "SQL FIles/Migrations/proposed/PS-ENTRY-POLICY-001_entry_metadata.sql")
        self.assertEqual(entry["rollback"], "SQL FIles/Migrations/proposed/PS-ENTRY-POLICY-001_entry_metadata_rollback.sql")

    def test_forward_sql_is_owner_keyed_serializable_and_closed(self):
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.forward)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", self.forward)
        self.assertIn("@UserKey", self.forward)
        self.assertNotIn("@OwnerProfileId", self.forward)
        self.assertIn("usp_CommitEntryPolicyCommandForOwner", self.forward)
        self.assertIn("ALTER COLUMN chapter_id bigint NULL", self.forward)
        self.assertIn("N'create'", self.forward)
        self.assertIn("N'resolve_match'", self.forward)
        self.assertIn("resume_display", self.forward)
        self.assertIn("visitor_ai", self.forward)
        self.assertIn("private_assistance_excluded", self.forward)
        self.assertIn("DATEADD(day, 30, @Now)", self.forward)
        self.assertIn("ENTRY_POLICY_SCOPE_CHANGED", self.forward)
        self.assertIn("SET category = @Category", self.forward)
        self.assertIn("lifecycle = N''deleted''", self.forward)
        self.assertIn("PROPOSED ONLY", self.forward)
        self.assertIsNone(re.search(r"(?mi)^[ \t]*GO[ \t]*$", self.forward))

    def test_rollback_and_verify_are_structural_only(self):
        self.assertIn("DELETE dbo.schema_migrations", self.rollback)
        self.assertIn("PS-ENTRY-POLICY-001", self.rollback)
        self.assertIn("verified", self.verify)
        self.assertIn("runtime proof remains outstanding", self.verify)

    def test_browser_procedures_are_allowlisted_and_workers_are_not(self):
        for name in ENTRY_POLICY_BROWSER_PROCEDURES:
            self.assertIn(name, self.forward)
            self.assertIn(name, ALLOWED_PROCEDURES)
        self.assertTrue(ENTRY_POLICY_WORKER_PROCEDURES)
        self.assertTrue(ENTRY_POLICY_WORKER_PROCEDURES.isdisjoint(ENTRY_POLICY_BROWSER_PROCEDURES))
        for name in ENTRY_POLICY_WORKER_PROCEDURES:
            self.assertNotIn(name, ALLOWED_PROCEDURES)

    def test_sql_row_mapping_renames_parent_and_recovery_columns(self):
        from services.entry_policy_repository import map_entry_policy_row

        mapped = map_entry_policy_row(
            {
                "entry_key": "00000000-0000-4000-8000-000000000001",
                "canonical_type": "role",
                "canonical_key": "00000000-0000-4000-8000-000000000001",
                "category": "experience",
                "parent_entry_key": None,
                "content_version": 7,
                "access_revision": 3,
                "resume_display": 1,
                "visitor_ai": 0,
                "private_assistance_excluded": 0,
                "lifecycle": "active",
                "recover_until_utc": None,
            }
        )
        self.assertEqual(mapped["parent_key"], None)
        self.assertEqual(mapped["recover_until"], None)
        self.assertTrue(mapped["resume_display"])
        self.assertFalse(mapped["visitor_ai"])
        self.assertEqual(mapped["content_version"], 7)

    def test_command_adapter_binds_owner_request_and_json(self):
        from unittest.mock import MagicMock

        from services.entry_policy_repository import SqlEntryPolicyRepository

        database = MagicMock()
        database.last_row.return_value = {
            "committed": 1,
            "replayed": 0,
            "outcome": "updated",
            "request_digest": "abc",
        }
        result = SqlEntryPolicyRepository(database).commit_command(
            "owner-a",
            "00000000-0000-4000-8000-000000000009",
            '{"type":"edit"}',
        )
        self.assertTrue(result["committed"])
        database.last_row.assert_called_once()
        args = database.last_row.call_args[0]
        self.assertEqual(args[0], "usp_CommitEntryPolicyCommandForOwner")
        self.assertEqual(args[1][0], ("@UserKey", "owner-a"))


if __name__ == "__main__":
    unittest.main()
