"""Source contracts for PS-INTERVIEW-RECOVERY-MOBILE-NAV-001 F2/F3 repairs."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "interview-recovery-mobile-nav-test-key")

from app import app

ROOT = Path(__file__).resolve().parents[1]
STUDIO_JS = (ROOT / "static" / "js" / "interview-studio.js").read_text(encoding="utf-8")
STUDIO_CSS = (ROOT / "static" / "css" / "interview-studio.css").read_text(
    encoding="utf-8"
)
MOBILE_JS = (ROOT / "static" / "js" / "public-mobile-nav.js").read_text(
    encoding="utf-8"
)
STUDIO_HTML = (ROOT / "templates" / "interview_studio.html").read_text(
    encoding="utf-8"
)


class InterviewRecoveryMobileNavContractTests(unittest.TestCase):
    def test_public_markup_keeps_one_retry_pair_and_ordinary_review(self):
        self.assertIn("data-is-review", STUDIO_HTML)
        self.assertIn("data-is-retry-coaching", STUDIO_HTML)
        self.assertIn("data-is-keep-editing", STUDIO_HTML)
        self.assertIn("Retry coaching", STUDIO_HTML)
        self.assertIn("Keep editing", STUDIO_HTML)

    def test_failed_coaching_uses_one_request_capable_recovery_path(self):
        self.assertIn("var coachingRecoveryVisible = false;", STUDIO_JS)
        self.assertIn("function setCoachingRecoveryVisible(visible)", STUDIO_JS)
        self.assertIn("all('[data-is-review]').forEach", STUDIO_JS)
        self.assertIn("setHidden(button, coachingRecoveryVisible);", STUDIO_JS)
        form_submit = STUDIO_JS.split(
            "answerForm.addEventListener('submit'", 1
        )[1].split("authenticated && modelAnswersEnabled", 1)[0]
        self.assertIn("if (coachingRecoveryVisible) return;", form_submit)
        keep_editing = STUDIO_JS.split(
            "keepEditingButton.addEventListener('click'", 1
        )[1].split("retryCoachingButton.addEventListener('click'", 1)[0]
        self.assertIn("setCoachingRecoveryVisible(false);", keep_editing)
        self.assertNotIn("submitReview()", keep_editing)
        retry = STUDIO_JS.split(
            "retryCoachingButton.addEventListener('click'", 1
        )[1].split("one('[data-is-retry]').addEventListener('click'", 1)[0]
        self.assertIn("submitReview();", retry)
        self.assertIn("if (reviewController) return;", STUDIO_JS)

    def test_menu_open_hides_interview_fixed_dock_without_making_a_modal(self):
        hide_rule = STUDIO_CSS.split(
            "body.has-platform-menu-open.interview-studio-page .is__composer-actions",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("visibility: hidden;", hide_rule)
        self.assertIn("pointer-events: none;", hide_rule)
        self.assertIn("has-platform-menu-open", MOBILE_JS)
        self.assertIn("addEventListener('focusin'", MOBILE_JS)
        focusin = MOBILE_JS.split("addEventListener('focusin'", 1)[1].split(
            "/* ---- Disclosure controls", 1
        )[0]
        self.assertIn("setMenuOpen(false, false);", focusin)
        self.assertNotIn("aria-modal", MOBILE_JS)
        self.assertNotIn("aria-modal", STUDIO_HTML)

    def test_public_studio_route_still_renders_recovery_controls(self):
        app.config["TESTING"] = True
        client = app.test_client()
        previous = app.config.get("PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED")
        app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = False
        try:
            response = client.get("/interview-studio", base_url="http://localhost")
        finally:
            app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = previous
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("data-is-review", html)
        self.assertIn("data-is-retry-coaching", html)
        self.assertIn("data-platform-menu-toggle", html)
        self.assertIn("interview-studio-page", html)


if __name__ == "__main__":
    unittest.main()
