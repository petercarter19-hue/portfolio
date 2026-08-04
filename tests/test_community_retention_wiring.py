"""Regressions for the two P0s found by independent review, 2026-08-04.

The existing retention tests mocked the database and matched SQL text, so both
defects passed a fully green suite. These assert the wiring itself.

F1: the new procedures were missing from the database service allowlist.
    execute_procedure raises ValueError for an unknown name, ValueError is not
    a DatabaseServiceError, and the sweep runs from an app-wide before_request
    — so enabling the Community flag returned 500 on every route on the site,
    including "/".

F2: the purge set body to an empty string, which the pre-existing
    CK_community_*_body constraints forbid, so no content was ever erased
    while the public policy said it was.
"""

import re
import unittest
from pathlib import Path
from unittest import mock

from services.community_retention_service import CommunityRetentionService
from services.community_restore_service import CommunityRestoreService
from services.database_service import ALLOWED_PROCEDURES


ROOT = Path(__file__).resolve().parents[1]
RETENTION_SQL = (
    ROOT / "SQL FIles" / "Migrations" / "proposed"
    / "PS-COMMUNITY-RETENTION-001_retention.sql"
)
COMMUNITY_SQL = (
    ROOT / "SQL FIles" / "Migrations" / "proposed"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
)

RETENTION_PROCEDURES = (
    "usp_PurgeCommunityContent",
    "usp_PurgeCommunityAuditEvents",
    "usp_PurgeCommunityOutbox",
    "usp_SetCommunityLegalHold",
    "usp_ListRestorableCommunityForOwner",
    "usp_RestorePublicCommunityPost",
    "usp_RestorePublicCommunityContribution",
)


class ProcedureAllowlistTests(unittest.TestCase):
    def test_every_new_procedure_is_allowlisted(self):
        for name in RETENTION_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(
                    name,
                    ALLOWED_PROCEDURES,
                    f"{name} is unreachable and would raise ValueError at runtime",
                )

    def test_every_procedure_the_services_call_is_allowlisted(self):
        """Catch the next one automatically rather than by list maintenance."""
        sources = [
            (ROOT / "services" / "community_retention_service.py").read_text(
                encoding="utf-8"
            ),
            (ROOT / "services" / "community_restore_service.py").read_text(
                encoding="utf-8"
            ),
        ]
        called = set()
        for source in sources:
            called.update(re.findall(r'"(usp_[A-Za-z]+)"', source))
        missing = called - set(ALLOWED_PROCEDURES)
        self.assertEqual(
            missing, set(), f"these procedures are called but not allowlisted: {missing}"
        )


class SweepNeverBreaksARequestTests(unittest.TestCase):
    """The sweep runs from before_request. Nothing may escape it."""

    def setUp(self):
        self.database = mock.Mock()
        self.service = CommunityRetentionService(database=self.database)

    def test_a_valueerror_does_not_escape_the_content_sweep(self):
        # This is the exact failure: an unknown procedure name raises
        # ValueError, not DatabaseServiceError.
        self.database.first_row.side_effect = ValueError("Invalid stored procedure name.")
        self.assertEqual(self.service.sweep_content_best_effort(), {})

    def test_a_valueerror_does_not_escape_the_daily_sweep(self):
        self.database.first_row.side_effect = ValueError("Invalid stored procedure name.")
        self.assertEqual(
            self.service.sweep_daily_best_effort(), {"audit": {}, "outbox": {}}
        )

    def test_no_exception_type_escapes_either_sweep(self):
        for error in (
            RuntimeError("boom"),
            KeyError("missing"),
            TypeError("bad"),
            AttributeError("gone"),
        ):
            with self.subTest(error=type(error).__name__):
                self.database.first_row.side_effect = error
                self.assertEqual(self.service.sweep_content_best_effort(), {})
                self.assertEqual(
                    self.service.sweep_daily_best_effort(),
                    {"audit": {}, "outbox": {}},
                )

    def test_a_restore_failure_still_surfaces_to_its_caller(self):
        # The sweep swallows, but restore is a member action: it must NOT
        # silently report success when the database refused.
        database = mock.Mock()
        database.first_row.side_effect = ValueError("Invalid stored procedure name.")
        service = CommunityRestoreService(database=database)
        with self.assertRaises(Exception):
            service.restore_post("owner", "11111111-1111-1111-1111-111111111111")


class PurgeCanActuallyCommitTests(unittest.TestCase):
    def test_the_body_constraint_permits_a_purged_tombstone(self):
        # The original constraint required LEN(body) BETWEEN 1 AND N, so
        # emptying the body could never commit.
        retention = RETENTION_SQL.read_text(encoding="utf-8")
        self.assertIn("CK_community_posts_body_or_purged", retention)
        self.assertIn("CK_community_contributions_body_or_purged", retention)
        self.assertIn("purged_at_utc IS NOT NULL AND LEN(body) = 0", retention)

    def test_the_original_constraints_are_dropped_before_the_purge_can_run(self):
        retention = RETENTION_SQL.read_text(encoding="utf-8")
        for old in ("CK_community_posts_body", "CK_community_contributions_body"):
            with self.subTest(constraint=old):
                self.assertIn(f"DROP CONSTRAINT {old};", retention)

    def test_an_empty_body_is_still_impossible_outside_a_purge(self):
        # The replacement must not simply relax the lower bound.
        retention = RETENTION_SQL.read_text(encoding="utf-8")
        self.assertIn("purged_at_utc IS NULL AND LEN(body) BETWEEN 1 AND 4000", retention)
        self.assertIn("purged_at_utc IS NULL AND LEN(body) BETWEEN 1 AND 2000", retention)

    def test_the_original_constraint_text_still_exists_to_be_replaced(self):
        # If the base migration ever renames these, the drop above silently
        # stops working and F2 returns.
        community = COMMUNITY_SQL.read_text(encoding="utf-8")
        self.assertIn("CONSTRAINT CK_community_posts_body CHECK", community)
        self.assertIn("CONSTRAINT CK_community_contributions_body CHECK", community)


class AttachmentTruthTests(unittest.TestCase):
    """Restore returns words, not files. Both surfaces must say so."""

    def test_the_recovery_screen_states_files_are_not_restored(self):
        markup = (ROOT / "templates" / "community_recently_deleted.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Attached files are not restored", markup)

    def test_the_public_policy_states_files_are_not_recoverable(self):
        policy = (ROOT / "templates" / "community_pilot_policy.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Attached files are not recoverable", policy)

    def test_the_decision_records_that_a_hold_cannot_save_bytes(self):
        decision = (
            ROOT / "docs" / "initiatives" / "PS-COMMUNITY-PUBLIC-PILOT-001"
            / "APPROVED_RETENTION_AND_DELETION_DECISION.md"
        ).read_text(encoding="utf-8")
        self.assertIn("cannot save attachment bytes", decision)


if __name__ == "__main__":
    unittest.main()
