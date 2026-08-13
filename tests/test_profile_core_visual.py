"""D0 visual-authority and scope static checks.

The real 33-board visual comparison belongs to D4, after the Profile has all
six destinations and the shared global shell may be integrated.  D0 protects
the adopted visual language without pretending to complete that comparison.
"""

from __future__ import annotations

from pathlib import Path
import unittest


class ProfileCoreVisualContractTests(unittest.TestCase):
    def test_d0_documents_its_visual_scope_and_deferred_boards(self):
        package = Path("docs/initiatives/PS-PROFILE-CORE-FOUNDATION-001/README.md").read_text(encoding="utf-8")
        self.assertIn("D0", package)
        self.assertIn("01-04", package)
        self.assertIn("09", package)
        self.assertIn("D4", package)
        self.assertIn("not a complete Profile", package)

        traceability = Path(
            "docs/initiatives/PS-PROFILE-CORE-FOUNDATION-001/TRACEABILITY.md"
        ).read_text(encoding="utf-8")
        for board in ("01_HOME_PUBLIC.png", "03_POSTS_PUBLIC.png", "09_ABOUT_PUBLIC.png"):
            with self.subTest(board=board):
                self.assertIn(board, traceability)

    def test_local_css_preserves_locked_non_blue_visual_language(self):
        css = Path("static/css/profile-experience.css").read_text(encoding="utf-8")
        for token in ("--profile-forest", "--profile-bronze", "--profile-plum", "--profile-canvas"):
            with self.subTest(token=token):
                self.assertIn(token, css)
        self.assertNotIn("#0057ff", css.lower())

    def test_current_application_registration_remains_untouched(self):
        app_source = Path("app.py").read_text(encoding="utf-8")
        self.assertNotIn("profile_routes", app_source)
        self.assertNotIn("profile_api", app_source)
