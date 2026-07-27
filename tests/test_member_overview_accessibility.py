import os
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-overview-accessibility-key")

from app import app  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static/css/member-overview.css").read_text(encoding="utf-8")
JAVASCRIPT = (
    ROOT / "static/js/member-overview-preview.js"
).read_text(encoding="utf-8")


class AccessibilityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []
        self._heading = None
        self.images = []
        self.main_count = 0
        self.landmarks = []
        self.labels = 0
        self.selects = 0
        self.buttons = []
        self.current_locations = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = {"level": int(tag[1]), "text": ""}
        if tag == "img":
            self.images.append(attributes)
        if tag == "main":
            self.main_count += 1
        if tag in {"header", "main", "nav", "aside", "footer"}:
            self.landmarks.append((tag, attributes))
        if tag == "label":
            self.labels += 1
        if tag == "select":
            self.selects += 1
        if tag == "button":
            self.buttons.append(attributes)
        if attributes.get("aria-current") == "location":
            self.current_locations += 1

    def handle_data(self, data):
        if self._heading is not None:
            self._heading["text"] += data

    def handle_endtag(self, tag):
        if self._heading is not None and tag == f"h{self._heading['level']}":
            self._heading["text"] = " ".join(self._heading["text"].split())
            self.headings.append(self._heading)
            self._heading = None


class MemberOverviewAccessibilityTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def render(self, style="story-career", fixture="experienced-leader", **params):
        return self.client.get(
            "/_internal/member-overview",
            query_string={"style": style, "fixture": fixture, **params},
            base_url="http://localhost",
        )

    def parse(self, response):
        parser = AccessibilityParser()
        parser.feed(response.get_data(as_text=True))
        return parser

    def test_one_h1_logical_headings_and_landmarks_in_both_styles(self):
        for style in ("story-career", "work-impact"):
            parser = self.parse(self.render(style))
            levels = [heading["level"] for heading in parser.headings]
            with self.subTest(style=style):
                self.assertEqual(levels.count(1), 1)
                self.assertEqual(parser.main_count, 1)
                self.assertTrue(any(tag == "header" for tag, _ in parser.landmarks))
                self.assertTrue(any(tag == "nav" for tag, _ in parser.landmarks))
                self.assertTrue(any(tag == "aside" for tag, _ in parser.landmarks))
                self.assertTrue(any(tag == "footer" for tag, _ in parser.landmarks))
                for previous, current in zip(levels, levels[1:]):
                    self.assertLessEqual(current - previous, 1)

    def test_style_change_preserves_semantic_section_order(self):
        expected_ids = (
            'id="overview"',
            'id="story"',
            'id="experience"',
            'id="impact"',
            'id="skills"',
            'id="credentials"',
            'id="connect"',
            'id="resume-start"',
        )
        order_by_style = []
        for style in ("story-career", "work-impact"):
            html = self.render(style).get_data(as_text=True)
            positions = [html.index(marker) for marker in expected_ids]
            self.assertEqual(positions, sorted(positions))
            order_by_style.append(
                [
                    marker
                    for _, marker in sorted(zip(positions, expected_ids))
                ]
            )
        self.assertEqual(order_by_style[0], order_by_style[1])

    def test_images_have_meaningful_alt_and_truth_labels(self):
        response = self.render("story-career", "experienced-leader")
        parser = self.parse(response)
        self.assertGreaterEqual(len(parser.images), 4)
        for image in parser.images:
            self.assertIn("alt", image)
            self.assertTrue(image["alt"].strip())
        self.assertEqual(
            response.data.count(b"Illustrative fixture image"),
            len(parser.images),
        )

        text_only = self.parse(self.render("work-impact", "text-only"))
        self.assertEqual(text_only.images, [])

    def test_review_controls_are_labeled_keyboard_native_and_server_backed(self):
        response = self.render("story-career", "experienced-leader")
        parser = self.parse(response)
        html = response.get_data(as_text=True)
        self.assertGreaterEqual(parser.labels, 3)
        self.assertEqual(parser.selects, 2)
        self.assertTrue(parser.buttons)
        self.assertIn('method="get"', html)
        self.assertIn('type="submit"', html)
        self.assertIn(":focus-visible", CSS)
        self.assertIn("outline: 3px solid", CSS)
        self.assertIn('controls.requestSubmit()', JAVASCRIPT)

    def test_exactly_one_current_section_and_descriptive_actions(self):
        response = self.render("story-career", "experienced-leader")
        parser = self.parse(response)
        # The desktop rail and mobile context each own one current marker;
        # responsive CSS makes exactly one of those navigation surfaces visible.
        self.assertEqual(parser.current_locations, 2)
        self.assertIn(".overview-mobile-context {\n  display: none;", CSS)
        self.assertIn(".overview-context-rail {\n    display: none;", CSS)
        html = response.get_data(as_text=True)
        for action in (
            "Connect",
            "View résumé",
            "View detailed experience",
            "View all skills",
            "View education",
            "View certifications",
            "View awards",
        ):
            self.assertIn(action, html)
        self.assertNotRegex(html, r">\s*More\s*<")

    def test_reflow_reduced_motion_and_geometry_contracts_are_explicit(self):
        required_css = (
            ".overview-center-stage {\n  width: 100%;",
            "zoom: 1;",
            "transform: none;",
            "@media (max-width: 64rem)",
            "grid-template-columns: 1fr;",
            "@media (prefers-reduced-motion: reduce)",
            "overflow-x: hidden;",
            "font-size: 1rem;",
            "max-width: 64ch;",
        )
        for marker in required_css:
            with self.subTest(marker=marker):
                self.assertIn(marker, CSS)
        self.assertNotIn("column-count:", CSS)
        self.assertNotIn("line-clamp", CSS)
        self.assertNotIn("text-overflow: ellipsis", CSS)
        self.assertNotRegex(
            CSS,
            r"\.member-overview[^{]*\{[^}]*overflow:\s*auto",
        )

    def test_large_text_and_capture_are_truthful_server_rendered_states(self):
        large = self.render(
            "story-career",
            "experienced-leader",
            largeText="1",
        )
        self.assertIn(b'class="overview-preview large-text"', large.data)
        self.assertIn(b"Maya Chen", large.data)
        self.assertIn(b"R\xc3\xa9sum\xc3\xa9 begins here", large.data)

        capture = self.render(
            "work-impact",
            "experienced-leader",
            capture="1",
        )
        self.assertIn(b'class="overview-preview capture-mode"', capture.data)
        self.assertNotIn(b"Fixture review controls", capture.data)
        self.assertIn(b"data-overview-root", capture.data)

    def test_primary_copy_uses_rem_not_sub_16_pixel_values(self):
        primary_rules = re.findall(
            r"(\.member-overview (?:p|li)[^{]*\{[^}]*\})",
            CSS,
            flags=re.MULTILINE,
        )
        self.assertTrue(primary_rules)
        self.assertTrue(any("font-size: 1rem" in rule for rule in primary_rules))
        self.assertNotRegex(
            "\n".join(primary_rules),
            r"font-size:\s*(?:0\.[0-9]+rem|[0-9]|1[0-5])px",
        )


if __name__ == "__main__":
    unittest.main()
