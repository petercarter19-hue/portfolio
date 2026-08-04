"""The secret-scan allowlist must survive a squash merge.

2026-08-04: the Community pull request was squash-merged. Three allowlists in
`.gitleaks.toml` were pinned to branch commit SHAs, and a squash rewrites every
branch commit into one new SHA, so all three stopped matching simultaneously.
The two false positives they covered reappeared as leaks and the deploy for the
merge commit failed. Production was unaffected — it kept serving the previous
build — but `main` could not deploy until the pins were removed.

Squash merge is this repository's required merge strategy, so a commit-pinned
allowlist is not merely fragile: it guarantees a failed deploy on the very merge
that carries the allowlisted line. This test makes that mistake fail here,
before it reaches the pipeline.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".gitleaks.toml"


class AllowlistSurvivesSquashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = CONFIG.read_text(encoding="utf-8")

    def test_no_allowlist_is_pinned_to_a_commit(self):
        pinned = [
            line.strip()
            for line in self.config.splitlines()
            if re.match(r"^\s*commits\s*=", line)
        ]
        self.assertEqual(
            pinned,
            [],
            "a commit-pinned allowlist cannot survive a squash merge and will "
            "fail the deploy for the merge that carries its line: %s" % pinned,
        )

    def test_the_known_false_positives_are_still_covered(self):
        # If these disappear, the two leaks come back on the next merge.
        self.assertIn("services/community_cursor", self.config)
        self.assertIn("max_age=CURSOR_MAX_AGE_SECONDS", self.config)
        self.assertIn("PRIMARY_FEED_ARCHITECTURE_AMENDMENT_2026-08-01", self.config)

    def test_every_allowlisted_line_still_exists_where_it_is_claimed(self):
        """An allowlist for a line that no longer exists is dead weight.

        Worse, it reads as though a real finding is being suppressed. If the
        code moves or the prose is rewritten, this fails and the entry should
        be deleted rather than left behind.
        """
        claims = (
            (
                "services/community_cursor.py",
                "max_age=CURSOR_MAX_AGE_SECONDS",
            ),
            (
                "docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001"
                "/PRIMARY_FEED_ARCHITECTURE_AMENDMENT_2026-08-01.md",
                "server audio, no content-bearing logs, owner-only access",
            ),
        )
        for relative_path, needle in claims:
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.exists(), "%s is gone" % relative_path)
                self.assertIn(
                    needle,
                    path.read_text(encoding="utf-8"),
                    "%s no longer contains the allowlisted line" % relative_path,
                )

    def test_allowlists_are_scoped_rather_than_blanket(self):
        """A path allowlist with no line regex would hide real secrets."""
        blocks = self.config.split("[[allowlists]]")[1:]
        for index, block in enumerate(blocks, start=1):
            with self.subTest(allowlist=index):
                self.assertIn("regexes", block, "allowlist %d has no regex" % index)
                if "paths" in block:
                    self.assertIn(
                        'regexTarget = "line"',
                        block,
                        "a path-scoped allowlist must also pin the exact line",
                    )


if __name__ == "__main__":
    unittest.main()
