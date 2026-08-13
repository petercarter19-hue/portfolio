"""Static accessibility checks for the isolated Profile D0 template."""

from __future__ import annotations

from pathlib import Path
import unittest


class ProfileCoreAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = Path("templates/profile/profile_destination.html").read_text(encoding="utf-8")
        cls.css = Path("static/css/profile-experience.css").read_text(encoding="utf-8")
        cls.script = Path("static/js/profile-experience.js").read_text(encoding="utf-8")

    def test_template_has_landmarks_skip_link_and_current_page_state(self):
        for contract in (
            'href="#profile-main"',
            'id="profile-main"',
            '<main',
            'aria-label="Profile identity"',
            'aria-label="Profile destinations"',
            'aria-current="page"',
            '<time datetime=',
            'meta name="viewport"',
            'aria-label="Current chapter"',
            'aria-labelledby="profile-principles-title"',
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.template)

    def test_css_covers_focus_mobile_reflow_and_reduced_motion(self):
        for contract in (
            ':focus-visible',
            '@media (max-width: 30rem)',
            '@media (prefers-reduced-motion: reduce)',
            '@media (forced-colors: active)',
            'overflow-x: auto',
            '--profile-measure',
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.css)

    def test_script_has_no_storage_network_or_autoplay_behavior(self):
        lower = self.script.lower()
        for forbidden in ("localstorage", "sessionstorage", "fetch(", "xmlhttprequest", "autoplay", "navigator.media"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lower)
