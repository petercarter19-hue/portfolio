"""F14: a targeted media cleanup claim is scoped by uploader in SQL.

Independent review, 2026-08-04. A targeted claim names one member's record and
its safety rested entirely on the route checking ownership first — one
deployment mistake away from a member claiming cleanup of another member's
attachment. Not exploitable while the site owner is the only writer, which is
why the review filed it as defence-in-depth to be closed before the pilot
admits a second member.

This file previously also covered PS-PLAT-008, an owner-only endpoint reporting
whether production's migration ledger matched the repository. That was dropped
before merge: the governed schema migration path landed on `main` first and
reads applied-ness live from `dbo.schema_migrations`, so shipping a second
mechanism for the same fact would have created exactly the competing truth
store the repository's invariants forbid.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
COMMUNITY_SQL = MIGRATIONS / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"


class UploaderScopedCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.community = COMMUNITY_SQL.read_text(encoding="utf-8")
        cls.api = (ROOT / "community_api.py").read_text(encoding="utf-8")

    def test_the_claim_accepts_an_uploader(self):
        self.assertIn("@UploaderUserKey nvarchar(300) = NULL", self.community)

    def test_the_uploader_is_resolved_server_side(self):
        # Never trust a caller-supplied id; resolve the key the way every other
        # Community procedure does.
        self.assertIn(
            "WHERE user_key=@UploaderUserKey AND active=1 AND account_status=N''active''",
            self.community,
        )

    def test_an_unresolvable_uploader_is_refused(self):
        # Scoping to nothing would be a silent no-op; refuse instead.
        self.assertIn("THROW 52453", self.community)

    def test_the_claim_is_scoped_by_uploader_when_one_is_given(self):
        self.assertIn(
            "AND (@UploaderUserId IS NULL OR media.uploader_user_id=@UploaderUserId)",
            self.community,
        )

    def test_server_initiated_sweeps_stay_unscoped(self):
        """The background janitor must still see every eligible row.

        The predicate is written so a NULL uploader disables the scope rather
        than matching nothing, which is what keeps the lifecycle sweeps working.
        """
        self.assertIn("@UploaderUserId IS NULL OR", self.community)

    def test_member_reachable_routes_pass_their_identity(self):
        # Both delete routes sweep media synchronously; each must scope it.
        self.assertEqual(
            self.api.count("uploader_user_key=identity.user_key"),
            2,
            "every member-reachable cleanup sweep must name its uploader",
        )


if __name__ == "__main__":
    unittest.main()
