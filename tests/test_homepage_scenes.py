"""PS-MVP1-MINIMAL-HOMEPAGE-001 — minimal public homepage contract."""

import unittest
from pathlib import Path
import re

from app import app


class HomepageMinimalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.response = cls.client.get("/")
        cls.html = cls.response.get_data(as_text=True)
        cls.main = re.search(
            r'<main\b[^>]*\bid="main-content"[^>]*>(.*?)</main>',
            cls.html,
            flags=re.DOTALL,
        ).group(1)
        cls.css = Path("static/css/homepage-minimal.css").read_text(
            encoding="utf-8"
        )

    def test_homepage_renders_in_the_shared_shell(self):
        self.assertEqual(self.response.status_code, 200)
        for expected in (
            'class="global-header"',
            'href="#main-content"',
            'id="main-content"',
            'class="footer"',
            'Sign In',
        ):
            self.assertIn(expected, self.html)

    def test_document_identity_and_quiet_preview_policy_are_preserved(self):
        self.assertIn(
            "<title>PeerSlate — Your Work. Your Story. Your Future.</title>",
            self.html,
        )
        body_tag = re.search(r"<body\b[^>]*>", self.html).group(0)
        self.assertIn("home-v3-page", body_tag)
        self.assertIn("homepage-minimal-page", body_tag)
        self.assertIn(
            '<meta name="robots" content="noindex, nofollow, noarchive, noimageindex">',
            self.html,
        )

    def test_body_has_one_headline_and_one_expressive_visual(self):
        self.assertEqual(len(re.findall(r"<h1\b", self.main)), 1)
        self.assertEqual(
            re.search(r"<h1\b[^>]*>(.*?)</h1>", self.main, re.DOTALL)
            .group(1)
            .strip(),
            "Your Work. Your Story. Your Future.",
        )
        images = re.findall(r"<img\b[^>]*>", self.main, re.DOTALL)
        self.assertEqual(len(images), 1)
        self.assertRegex(
            images[0],
            r'src="/static/images/cinematic/hero-aurora\.jpg(?:\?[^\"]+)?"',
        )

    def test_body_has_the_owner_requested_progress_note(self):
        self.assertIn(
            (
                "A considered beginning. PeerSlate is taking shape. "
                "Access is by invitation as we prepare for what’s next."
            ),
            self.main,
        )
        self.assertEqual(
            len(re.findall(r'class="homepage-minimal__status"', self.main)),
            1,
        )

    def test_visual_is_decorative_and_layout_stable(self):
        image = re.search(r"<img\b[^>]*>", self.main, re.DOTALL).group(0)
        for attribute in (
            'alt=""',
            'width="3840"',
            'height="2160"',
            'decoding="async"',
            'fetchpriority="high"',
        ):
            self.assertIn(attribute, image)
        self.assertIn(
            'class="homepage-minimal__visual" aria-hidden="true"',
            self.main,
        )
        self.assertIn("background: var(--ps-primary-soft", self.css)

    def test_homepage_loads_only_its_minimal_page_asset(self):
        self.assertIn('/static/css/homepage-minimal.css', self.html)
        self.assertNotIn('/static/css/homepage-scenes.css', self.html)
        self.assertNotIn("/static/js/homepage-interview-demo.js", self.html)

    def test_body_has_no_entry_action_or_form(self):
        for tag_name in ("a", "button", "form", "input", "textarea", "select"):
            self.assertEqual(
                len(re.findall(rf"<{tag_name}\b", self.main)),
                0,
                f"homepage body unexpectedly contains <{tag_name}>",
            )

    def test_body_does_not_advertise_superseded_product_scenes(self):
        for banned in (
            "Say what happened",
            "Keep a private career record",
            "Public example",
            "Capture",
            "Journal",
            "Projects",
            "Workshop",
            "Interview Studio",
            "Create My Slate",
            "Get Started",
        ):
            self.assertNotIn(banned, self.main)

    def test_layout_is_natural_flow_without_motion(self):
        normalized_css = " ".join(self.css.lower().split())
        self.assertNotIn("position: fixed", normalized_css)
        self.assertNotIn("position: absolute", normalized_css)
        self.assertNotIn("height: 100vh", normalized_css)
        self.assertNotIn(
            "overflow: hidden",
            normalized_css.split(".homepage-minimal__visual", 1)[0],
        )
        self.assertNotIn("animation:", normalized_css)
        self.assertNotIn("transition:", normalized_css)
        for token in ("--ps-canvas", "--ps-ink", "--ps-primary-soft"):
            self.assertIn(token, self.css)


if __name__ == "__main__":
    unittest.main()
