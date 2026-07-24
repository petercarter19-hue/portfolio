"""Static DOM/CSS accessibility checks for the Slice 1 Studio shell."""

import unittest
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import patch

from app import app


ROUTE = "/app/studio/build-your-future"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": ""}
        self.nodes.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    def by_tag(self, tag):
        return [node for node in self.nodes if node["tag"] == tag]


class StudioSliceOneAccessibilityTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED")
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = True

    def tearDown(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = self.original_flag

    def render(self):
        identity = SimpleNamespace(display_name="Avery Member", user_key="owner-avery")
        with patch("auth_routes.get_current_identity", return_value=identity):
            response = self.client.get(ROUTE)
        html = response.get_data(as_text=True)
        parser = PageParser()
        parser.feed(html)
        return response, html, parser

    def test_has_one_main_one_h1_skip_link_and_named_navigation(self):
        response, html, parser = self.render()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(parser.by_tag("main")), 1)
        self.assertEqual(len(parser.by_tag("h1")), 1)
        self.assertIn('href="#main-content"', html)
        self.assertIn('aria-label="Studio global navigation"', html)
        self.assertIn('aria-label="Slate Studio sections"', html)
        self.assertIn('aria-labelledby="studio-stage-title"', html)

    def test_current_items_are_real_links_and_no_dead_or_fake_controls_exist(self):
        _, _, parser = self.render()

        current = [node for node in parser.by_tag("a") if node["attrs"].get("aria-current") == "page"]
        self.assertEqual(len(current), 2)
        self.assertTrue(all(node["attrs"].get("href") == ROUTE for node in current))
        for link in parser.by_tag("a"):
            self.assertTrue(link["attrs"].get("href"))
            self.assertNotEqual(link["attrs"].get("href"), "#")
            self.assertTrue(link["text"].strip() or link["attrs"].get("aria-label"))
        self.assertFalse(any("disabled" in button["attrs"] for button in parser.by_tag("button")))

    def test_state_and_trust_text_do_not_depend_on_color_or_javascript(self):
        _, html, _ = self.render()
        css_path = "static/css/owner-studio.css"
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("Your Build Your Future workspace is not connected yet.", html)
        self.assertIn("Nothing you try here changes what is live until you decide.", html)
        self.assertIn("Private by default.", html)
        self.assertIn(
            "Nothing is automatically saved, accepted, placed, or published.",
            html,
        )
        self.assertIn("@media (forced-colors: active)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("@media (max-width: 600px)", css)
        self.assertIn("outline: 3px solid var(--ss-focus)", css)
        theme_rules = css.rsplit(".ss-theme-toggle {", 1)[1].split("}", 1)[0]
        self.assertIn("gap: 6px;", theme_rules)

    def test_reflow_navigation_starts_at_first_item_and_mobile_global_nav_fits(self):
        _, _, parser = self.render()
        with open("static/css/owner-studio.css", encoding="utf-8") as css_file:
            css = css_file.read()

        reflow_rules = css.split("@media (max-width: 899px)", 1)[1].split(
            "@media (max-width: 600px)", 1
        )[0]
        mobile_rules = css.split("@media (max-width: 600px)", 1)[1].split(
            "@media (max-height: 500px)", 1
        )[0]

        self.assertIn(".ss-studio-nav { justify-content: flex-start; }", reflow_rules)
        self.assertIn(
            ".ss-account { grid-column: 1 / -1; grid-row: 3; }",
            reflow_rules,
        )
        self.assertIn(
            ".ss-studio-nav { min-height: 60px; justify-content: flex-start; }",
            mobile_rules,
        )
        self.assertIn(
            ".ss-account { width: 100%; grid-column: 1; grid-row: 3;",
            mobile_rules,
        )
        self.assertIn("grid-column: 1;\n        grid-row: 2;", mobile_rules)
        self.assertIn(
            "grid-template-columns: repeat(3, minmax(0, 1fr));",
            mobile_rules,
        )
        self.assertIn(".ss-studio-nav::-webkit-scrollbar { height: 4px; }", css)
        self.assertIn(
            ".ss-global-nav a,\n.ss-global-nav__unavailable {\n"
            "    min-height: 44px;",
            css,
        )

        focus_order = [
            node["attrs"].get("aria-label") or node["text"].strip()
            for node in parser.nodes
            if node["tag"] in {"a", "button"}
        ]
        expected_order = [
            "PeerSlate Workshop",
            "Slate Studio",
            "Avery Member",
            "Workshop",
        ]
        positions = [focus_order.index(label) for label in expected_order]
        self.assertEqual(positions, sorted(positions))

    def test_no_javascript_response_hides_the_inert_theme_control(self):
        _, html, parser = self.render()

        theme_controls = [
            button
            for button in parser.by_tag("button")
            if button["attrs"].get("id") == "theme-toggle"
        ]
        self.assertEqual(len(theme_controls), 1)
        self.assertIn("hidden", theme_controls[0]["attrs"])
        self.assertIn("data-theme-toggle-requires-js", theme_controls[0]["attrs"])
        self.assertIn(
            "Build Your Future works without JavaScript. "
            "The page remains in its default light theme.",
            html,
        )
        self.assertIn(
            'onload="document.getElementById(\'theme-toggle\').hidden = false"',
            html,
        )


if __name__ == "__main__":
    unittest.main()
