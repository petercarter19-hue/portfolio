"""F14: a targeted media cleanup claim is scoped by uploader in SQL.

Independent review, 2026-08-04. A targeted claim names one member's record and
its safety rested entirely on its caller checking ownership first. Request
paths now only mark lifecycle state and never invoke cleanup. The additive
owner procedure remains the safe primitive for any explicit operational target
without mutating the already-applied Community migration.

This file previously also covered PS-PLAT-008, an owner-only endpoint reporting
whether production's migration ledger matched the repository. That was dropped
before merge: the governed schema migration path landed on `main` first and
reads applied-ness live from `dbo.schema_migrations`, so shipping a second
mechanism for the same fact would have created exactly the competing truth
store the repository's invariants forbid.
"""

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
COMMUNITY_SQL = (
    MIGRATIONS / "proposed" / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
)
REVIVAL_SQL = MIGRATIONS / "PS-COMMUNITY-REVIVAL-001_maintenance.sql"


class UploaderScopedCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.community = COMMUNITY_SQL.read_text(encoding="utf-8")
        cls.revival = REVIVAL_SQL.read_text(encoding="utf-8")
        cls.api = (ROOT / "community_api.py").read_text(encoding="utf-8")

    def test_the_applied_baseline_is_not_rewritten(self):
        self.assertNotIn("@UploaderUserKey", self.community)
        self.assertEqual(
            hashlib.sha256(COMMUNITY_SQL.read_bytes()).hexdigest(),
            "46293693212f3ea9b063d22af4712ac7f2a70485f2231c043812cb8e84d971e2",
        )

    def test_the_additive_owner_claim_accepts_a_server_key(self):
        self.assertIn(
            "CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanupForOwner",
            self.revival,
        )
        self.assertIn("@UserKey nvarchar(300)", self.revival)

    def test_the_uploader_is_resolved_server_side(self):
        # Never trust a caller-supplied id; resolve the key the way every other
        # Community procedure does.
        self.assertIn(
            "WHERE user_key = @UserKey",
            self.revival,
        )

    def test_an_unresolvable_uploader_is_refused(self):
        # Scoping to nothing would be a silent no-op; refuse instead.
        self.assertIn("THROW 53911", self.revival)

    def test_the_claim_is_scoped_by_uploader_when_one_is_given(self):
        self.assertIn(
            "WHERE media.uploader_user_id = @UploaderUserId",
            self.revival,
        )

    def test_server_initiated_sweeps_stay_unscoped(self):
        """The background janitor must still see every eligible row.

        The original procedure remains in the immutable base migration while
        the owner-scoped variant is a distinct additive procedure.
        """
        self.assertIn(
            "CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanup",
            self.community,
        )
        self.assertNotIn(
            "CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanupForOwner",
            self.community,
        )

    def test_member_reachable_routes_defer_cleanup_to_the_scheduler(self):
        self.assertNotIn("sweep_best_effort", self.api)
        self.assertNotIn("uploader_user_key=identity.user_key", self.api)


if __name__ == "__main__":
    unittest.main()
