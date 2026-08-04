"""Device-local drafts expire after 30 idle days.

Required evidence item 3 of the approved retention decision. A draft is never
transmitted to PeerSlate, so no server-side sweep can reach it — the rule can
only be enforced on the device holding it, which makes this the one retention
row with no database behind it.
"""

import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "static" / "js" / "community-v1.js"
DECISION = (
    ROOT
    / "docs"
    / "initiatives"
    / "PS-COMMUNITY-PUBLIC-PILOT-001"
    / "APPROVED_RETENTION_AND_DELETION_DECISION.md"
)


class DraftExpiryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_the_window_matches_the_approved_thirty_days(self):
        self.assertIn(
            "var DRAFT_IDLE_LIMIT_MS = 30 * 24 * 60 * 60 * 1000;", self.script
        )

    def test_the_approved_decision_still_says_thirty_days(self):
        # If the decision is ever revised, this fails and forces the code to
        # be revisited rather than quietly diverging from what Pete approved.
        self.assertIn("30 days without an edit", DECISION.read_text(encoding="utf-8"))

    def test_saving_a_draft_records_when_it_was_last_edited(self):
        # Without a timestamp there is nothing to expire against.
        self.assertIn("value.saved_at = Date.now();", self.script)
        self.assertIn("saved_at: Date.now()", self.script)

    def test_all_three_draft_surfaces_check_expiry_before_restoring(self):
        # The composer, the per-post comment box, and the reply box each
        # persist separately; an expiry applied to only some of them leaks the
        # rest. This test asserted two surfaces and shipped with the reply box
        # unbounded — independent review, 2026-08-04, F6.
        self.assertIn("if (draftHasExpired(value)) {", self.script)
        self.assertIn("function readPrimaryCommentDraft(postKey)", self.script)
        self.assertIn("input.value = readPrimaryCommentDraft(post.key);", self.script)
        self.assertIn("function readReplyDraft(targetKey)", self.script)
        self.assertIn("input.value = readReplyDraft(targetKey);", self.script)

    def test_no_draft_surface_reads_storage_without_an_expiry_check(self):
        """Catch the next missed surface automatically rather than by list.

        Every read of a draft key must go through a reader that consults
        draftHasExpired. A bare getItem on a draft key is the exact shape of
        the defect this replaces.
        """
        readers = ("restoreDraft", "readPrimaryCommentDraft", "readReplyDraft")
        for name in readers:
            with self.subTest(reader=name):
                start = self.script.index("function %s(" % name)
                body = self.script[start : start + 1400]
                self.assertIn(
                    "draftHasExpired", body, "%s restores without expiring" % name
                )
        # Attribute every draft read to the function that performs it, and
        # require that function to consult the expiry. Matching per line would
        # wrongly flag a reader whose check sits on the following line.
        lines = self.script.splitlines()
        starts = [
            (index, line.strip().split("(")[0][len("function ") :])
            for index, line in enumerate(lines)
            if line.startswith("  function ")
        ]
        unguarded = []
        for index, line in enumerate(lines):
            if "localStorage.getItem(" not in line or "draft" not in line.lower():
                continue
            enclosing = [start for start in starts if start[0] < index]
            if not enclosing:
                continue
            name = enclosing[-1][1]
            end = next(
                (start[0] for start in starts if start[0] > index), len(lines)
            )
            body = "\n".join(lines[enclosing[-1][0] : end])
            if "draftHasExpired" not in body:
                unguarded.append(name)
        self.assertEqual(
            unguarded,
            [],
            "these functions read a draft without expiring it: %s" % unguarded,
        )

    def test_a_reply_draft_is_stored_with_its_timestamp(self):
        start = self.script.index("function saveReplyDraft()")
        body = self.script[start : self.script.index("function readReplyDraft(")]
        self.assertIn("saved_at: Date.now()", body)

    def test_an_expired_draft_is_removed_not_merely_hidden(self):
        expiry_block = self.script[self.script.index("function restoreDraft()"):]
        expiry_block = expiry_block[: expiry_block.index("function updateCount")]
        self.assertIn("localStorage.removeItem(draftKey);", expiry_block)

    def test_an_expired_draft_also_clears_its_pending_command(self):
        # A stale pending command would otherwise replay content whose draft
        # has already been expired away.
        expiry_block = self.script[self.script.index("function restoreDraft()"):]
        expiry_block = expiry_block[: expiry_block.index("function updateCount")]
        self.assertIn("localStorage.removeItem(postCommandStorageKey);", expiry_block)


class DraftExpiryBehaviourTests(unittest.TestCase):
    def test_draft_expiry_behavior_harness_passes(self):
        node = shutil.which("node")
        app_node = "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node"
        if not node and os.path.isfile(app_node):
            node = app_node
        if not node:
            self.skipTest(
                "Node runtime unavailable for the dependency-free draft expiry harness"
            )
        result = subprocess.run(
            [node, str(ROOT / "tests" / "community_draft_expiry.test.js")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("behavioral checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
