"""The public policy states the schedule that is actually implemented.

Required evidence item 6 of the approved retention decision: "Update the dated
public-pilot policy to state the implemented schedule plainly without promising
deletion from recipient copies or unexpired recovery backups."

The risk this guards is a policy that drifts from the code. A published
promise is the one artefact a member can rely on, so every number in it is
pinned to the constant the software actually uses.
"""

import unittest
from pathlib import Path

from services.community_retention_service import (
    AUDIT_RETENTION_DAYS,
    CONTENT_RETENTION_DAYS,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "templates" / "community_pilot_policy.html"


class PolicyStatesImplementedScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = POLICY.read_text(encoding="utf-8")

    def test_the_policy_is_dated(self):
        self.assertIn("Effective August 4, 2026", self.policy)

    def test_it_states_removal_is_immediate_not_delayed(self):
        # The single most important sentence: a member must not think their
        # removed post stays public for 30 days.
        self.assertIn("revokes its public availability immediately", self.policy)

    def test_it_states_the_content_window_the_code_uses(self):
        self.assertEqual(CONTENT_RETENTION_DAYS, 30)
        self.assertIn(f"<strong>{CONTENT_RETENTION_DAYS} days</strong>", self.policy)
        self.assertIn("permanently erased", self.policy)

    def test_it_states_the_audit_window_the_code_uses(self):
        self.assertEqual(AUDIT_RETENTION_DAYS, 90)
        self.assertIn("90 days", self.policy)

    def test_it_states_the_attachment_and_unattached_windows(self):
        self.assertIn("24 hours", self.policy)

    def test_it_does_not_promise_an_attachment_deadline_it_cannot_keep(self):
        """F9, independent review 2026-08-04.

        The policy promised deletion "within an hour", but the backstop is a
        best-effort worker that only runs when a request arrives. The ordinary
        path does delete synchronously inside the removal request, so the
        truthful claim is about the mechanism, not a clock PeerSlate does not
        control. The approved schedule is unchanged; only the wording is.
        """
        self.assertNotIn("within an hour", self.policy)
        self.assertIn("as part of removing the post", self.policy)
        self.assertIn("keeps retrying until it is gone", self.policy)
        self.assertIn("never held for the 30-day window", self.policy)

    def test_it_states_drafts_never_reach_peerslate(self):
        self.assertIn("only on your own device", self.policy)
        self.assertIn("never receives them", self.policy)

    def test_it_states_searches_are_not_stored(self):
        self.assertIn("searches are not stored", self.policy)

    def test_it_does_not_promise_deletion_from_backups(self):
        # The approved decision is explicit that a purged row may survive in
        # an access-restricted backup until it ages out. Claiming otherwise
        # would be the dishonest version of this page.
        self.assertIn("persist briefly in routine encrypted database backups", self.policy)
        self.assertIn("7 days", self.policy)

    def test_it_does_not_promise_deletion_from_recipient_copies(self):
        self.assertIn("cannot recall copies other people already made", self.policy)

    def test_it_makes_no_absolute_deletion_promise(self):
        lowered = self.policy.lower()
        for overclaim in (
            "deleted everywhere",
            "permanently deleted from all",
            "completely erased everywhere",
            "no copies remain",
        ):
            with self.subTest(claim=overclaim):
                self.assertNotIn(overclaim, lowered)


if __name__ == "__main__":
    unittest.main()
