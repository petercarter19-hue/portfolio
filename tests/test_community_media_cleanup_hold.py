"""Retention corrections from the 2026-08-04 independent review.

F5 (a legal hold did not suspend attachment cleanup), F7 (unbounded revision
deletes), F8 (unvalidated hold operator and a false header claim), and F10
(rollback ordering).

F5 is worth the long note, because the first attempt was wrong in an
instructive way. `usp_ClaimPublicCommunityMediaCleanup` belongs to the base
community migration, but the `legal_hold_*` columns were created by the
retention migration, and SQL Server resolves column references against an
already-existing table at CREATE PROCEDURE time — so the predicate could not be
added where the procedure lives. Restating the procedure in the retention
migration looked like the only route, and proof run 457 rejected it: the base
migration stamps a SHA-256 of every procedure it owns into an extended property
and refuses re-application when a definition no longer matches.

The guard was right. The fix is ownership, not duplication: the hold columns now
live with the tables in the base migration, so one procedure carries the
predicate. Retention keeps what it actually owns — the purge marker, the jobs
that honour a hold, and the procedure that sets one.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
BASE = MIGRATIONS / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
RETENTION = MIGRATIONS / "PS-COMMUNITY-RETENTION-001_retention.sql"
ROLLBACK = MIGRATIONS / "PS-COMMUNITY-RETENTION-001_retention_rollback.sql"

CLEANUP_PROCEDURE = "CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanup"
HOLD_COLUMNS = (
    "legal_hold_reason nvarchar(60) NULL",
    "legal_hold_set_at_utc datetime2(7) NULL",
    "legal_hold_set_by_user_id int NULL",
    "legal_hold_review_on date NULL",
)


class OnlyTheOwningMigrationDefinesItsProceduresTests(unittest.TestCase):
    """The rule proof run 457 taught us, kept enforceable."""

    def test_the_cleanup_claim_is_defined_exactly_once(self):
        owners = [
            path.name
            for path in (BASE, RETENTION, ROLLBACK)
            if CLEANUP_PROCEDURE in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            owners,
            [BASE.name],
            "a migration is redefining another migration's protected procedure; "
            "the base migration's definition hash guard will reject it on "
            "re-application",
        )


class AHoldSuspendsAttachmentCleanupTests(unittest.TestCase):
    """F5: the feature that exists to preserve evidence must preserve it."""

    @classmethod
    def setUpClass(cls):
        cls.base = BASE.read_text(encoding="utf-8")

    def test_every_ownership_chain_is_covered(self):
        """Media hangs off a post, a contribution, or a contribution's post.

        A hold on any of them owns those bytes. Missing one leaves a hold that
        preserves the words and loses the files for that shape of record.
        """
        for alias in ("direct_post", "contribution", "contribution_post"):
            with self.subTest(chain=alias):
                self.assertIn("AND %s.legal_hold_reason IS NULL" % alias, self.base)

    def test_the_predicates_sit_inside_the_cleanup_claim(self):
        start = self.base.index(CLEANUP_PROCEDURE)
        end = self.base.index("    END');", start)
        claim = self.base[start:end]
        self.assertIn("direct_post.legal_hold_reason IS NULL", claim)
        self.assertIn("contribution_post.legal_hold_reason IS NULL", claim)

    def test_the_scope_limit_is_recorded_where_someone_will_read_it(self):
        # A hold applied after removal is still too late for the bytes. That
        # is a real limitation and must not be quietly forgotten.
        self.assertIn("requires the hold to precede the removal", self.base)


class HoldColumnsBelongToTheMigrationThatReadsThemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = BASE.read_text(encoding="utf-8")
        cls.retention = RETENTION.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")

    def test_the_base_migration_declares_the_columns(self):
        for column in HOLD_COLUMNS:
            with self.subTest(column=column):
                self.assertIn(column, self.base)

    def test_the_base_migration_declares_the_completeness_constraints(self):
        self.assertIn("CONSTRAINT CK_community_posts_legal_hold CHECK", self.base)
        self.assertIn(
            "CONSTRAINT CK_community_contributions_legal_hold CHECK", self.base
        )

    def test_retention_no_longer_creates_them(self):
        self.assertNotIn("ADD legal_hold_reason", self.retention)
        self.assertNotIn(
            "ADD CONSTRAINT CK_community_posts_legal_hold", self.retention
        )

    def test_retention_refuses_rather_than_assuming_they_exist(self):
        # If the base migration ever stops supplying them, fail loudly here
        # instead of failing to compile a procedure much later.
        self.assertIn("THROW 52515", self.retention)
        self.assertIn(
            "IF COL_LENGTH(N'dbo.community_posts', N'legal_hold_reason') IS NULL",
            self.retention,
        )

    def test_the_retention_rollback_does_not_drop_columns_it_does_not_own(self):
        self.assertNotIn("DROP COLUMN legal_hold_reason", self.rollback)

    def test_the_retention_rollback_still_removes_its_own_purge_marker(self):
        self.assertIn("DROP COLUMN purged_at_utc", self.rollback)


class HoldOperatorIsValidatedTests(unittest.TestCase):
    """F8: a hold attributed to a user id that does not exist is unusable."""

    @classmethod
    def setUpClass(cls):
        cls.retention = RETENTION.read_text(encoding="utf-8")

    def test_the_operator_is_checked_against_app_users(self):
        self.assertIn(
            "IF @Release = 0 AND NOT EXISTS (SELECT 1 FROM dbo.app_users WHERE id = @OperatorUserId)",
            self.retention,
        )
        self.assertIn("THROW 52507", self.retention)

    def test_the_header_no_longer_claims_a_hold_revokes_public_access(self):
        self.assertNotIn("Public access stays revoked while held", self.retention)
        self.assertIn(
            "A hold changes nothing about who can see the record", self.retention
        )


class RevisionDeletesAreBoundedTests(unittest.TestCase):
    """F7: the revision deletes ran over every tombstone, not just the batch."""

    @classmethod
    def setUpClass(cls):
        cls.retention = RETENTION.read_text(encoding="utf-8")

    def test_the_purged_batch_is_captured(self):
        self.assertIn(
            "OUTPUT inserted.community_post_id INTO @PurgedPosts(community_post_id)",
            self.retention,
        )
        self.assertIn(
            "OUTPUT inserted.community_contribution_id INTO @PurgedContributions(community_contribution_id)",
            self.retention,
        )

    def test_revisions_are_deleted_by_batch_not_by_tombstone_scan(self):
        self.assertIn("JOIN @PurgedPosts AS purged", self.retention)
        self.assertIn("JOIN @PurgedContributions AS purged", self.retention)
        self.assertNotIn("WHERE post.purged_at_utc IS NOT NULL;", self.retention)
        self.assertNotIn(
            "WHERE contribution.purged_at_utc IS NOT NULL;", self.retention
        )


class RollbackOrderingIsEnforcedTests(unittest.TestCase):
    """F10: rolling retention back under restore breaks restore."""

    def test_the_rollback_refuses_while_restore_is_applied(self):
        rollback = ROLLBACK.read_text(encoding="utf-8")
        self.assertIn("PS-COMMUNITY-RESTORE-001", rollback)
        self.assertIn("THROW 52514", rollback)


if __name__ == "__main__":
    unittest.main()
