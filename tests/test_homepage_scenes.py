"""Public homepage contract: Pete's approved round-5 home page "The Fan"
(PS-SITE-SHELL-ROUND5-001; it replaces PS-MVP1-MINIMAL-HOMEPAGE-001's body)."""

import unittest
from pathlib import Path
import re

from app import app


class HomepageRound5Tests(unittest.TestCase):
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
        cls.css = Path("static/css/home.css").read_text(encoding="utf-8")

    def test_homepage_renders_in_the_shared_shell(self):
        self.assertEqual(self.response.status_code, 200)
        for expected in (
            '<div class="ps-shell" id="site-header">',
            'href="#main-content"',
            'id="main-content"',
            'class="ps-home-foot"',
            '>Sign in</a>',
        ):
            self.assertIn(expected, self.html)

    def test_document_identity_and_quiet_preview_policy_are_preserved(self):
        self.assertIn(
            "<title>PeerSlate — Your Work. Your Story. Your Future.</title>",
            self.html,
        )
        body_tag = re.search(r"<body\b[^>]*>", self.html).group(0)
        # home-v3-page stays: scripts/verify_deployment_smoke.py asserts it.
        self.assertIn("home-v3-page", body_tag)
        self.assertIn("ps-home-page", body_tag)
        self.assertNotIn("homepage-minimal-page", body_tag)
        self.assertIn(
            '<meta name="robots" content="noindex, nofollow, noarchive, noimageindex">',
            self.html,
        )

    def test_body_has_one_headline_the_lede_and_the_invitation_note(self):
        self.assertEqual(len(re.findall(r"<h1\b", self.main)), 1)
        headline = re.search(r"<h1\b[^>]*>(.*?)</h1>", self.main, re.DOTALL).group(1)
        self.assertEqual(
            "Your Work. Your Story. Your Future.",
            re.sub(r"<[^>]+>", "", headline).strip(),
        )
        self.assertIn(
            '<p class="ps-home__lede">A portfolio that tells your story and answers for you.</p>',
            self.main,
        )
        self.assertIn(
            '<p class="ps-home__inv">Access is by invitation for now. See it working on Pete’s resume.</p>',
            self.main,
        )

    def test_the_only_actions_are_petes_resume_and_story(self):
        self.assertEqual(
            [("ps-home__gold", "/petec/resume", "See Pete’s resume"),
             ("ps-home__textlink", "/petec/my-story", "See Pete’s story")],
            re.findall(r'<a class="([\w-]+)" href="([^"]+)">([^<]+)</a>', self.main),
        )
        for tag_name in ("button", "form", "input", "textarea", "select"):
            self.assertEqual(
                len(re.findall(rf"<{tag_name}\b", self.main)),
                0,
                f"homepage body unexpectedly contains <{tag_name}>",
            )

    def test_the_fan_is_layout_stable_and_described(self):
        images = re.findall(r"<img\b[^>]*>", self.main, re.DOTALL)
        self.assertEqual(len(images), 2)
        for image, width, height in zip(images, ("1396", "714"), ("600", "580")):
            self.assertIn(f'width="{width}"', image)
            self.assertIn(f'height="{height}"', image)
            self.assertIn('decoding="async"', image)
            self.assertRegex(image, r'alt="[^"]{20,}"')
        self.assertIn('fetchpriority="high"', images[0])
        # The decorative stones and the hero Cairn stay out of the
        # accessibility tree.
        self.assertIn('<div class="ps-home-bg" aria-hidden="true">', self.main)
        self.assertRegex(self.main, r'<svg class="ps-home__cairn"[^>]*aria-hidden="true"')

    def test_homepage_loads_only_its_own_page_asset(self):
        self.assertIn("/static/css/home.css", self.html)
        for retired in ("/static/css/homepage-minimal.css", "/static/css/homepage-scenes.css",
                        "/static/js/homepage-interview-demo.js", "hero-aurora.jpg"):
            self.assertNotIn(retired, self.html)

    def test_body_does_not_advertise_superseded_product_scenes(self):
        # The fan's alt text names Interview Studio and Opportunity Slate as
        # coming soon, exactly as round 5 shows them; no other copy may.
        visible = re.sub(r'alt="[^"]*"', "", self.main)
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
            "Try Interview AI",
        ):
            self.assertNotIn(banned, visible)

    def test_layout_is_light_and_motion_free(self):
        normalized_css = " ".join(self.css.lower().split())
        self.assertNotIn("animation:", normalized_css)
        self.assertNotIn("transition:", normalized_css)
        self.assertNotIn("prefers-color-scheme: dark", normalized_css)
        self.assertIn("color-scheme: light", normalized_css)
        self.assertIn("--home-green: #3f6a51", normalized_css)


if __name__ == "__main__":
    unittest.main()
