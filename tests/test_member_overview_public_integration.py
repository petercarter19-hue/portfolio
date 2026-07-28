import os
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-overview-public-key")

import app as app_module  # noqa: E402
from overview_projection_service import OverviewProjectionError  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


class PublicResumeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.h1_count = 0
        self.resume_sections = []
        self.overview_attributes = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "h1":
            self.h1_count += 1
        if "data-resume-section" in attributes:
            self.resume_sections.append(attributes.get("id"))
        if "data-overview-root" in attributes:
            self.overview_attributes = attributes


class MemberOverviewPublicIntegrationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def render(self):
        return self.client.get("/petec/resume", base_url="http://localhost")

    def test_published_overview_replaces_summary_and_keeps_resume_below(self):
        response = self.render()
        html = response.get_data(as_text=True)
        parser = PublicResumeParser()
        parser.feed(html)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(parser.h1_count, 1)
        self.assertEqual(
            parser.resume_sections,
            ["overview", "impact", "skills", "experience", "credentials"],
        )
        self.assertEqual(
            {item: count for item, count in Counter(parser.ids).items() if count > 1},
            {},
        )
        self.assertIsNotNone(parser.overview_attributes)
        self.assertEqual(
            parser.overview_attributes["data-publication-state"],
            "published",
        )
        self.assertEqual(
            parser.overview_attributes["data-publication-revision"],
            "1",
        )
        self.assertNotIn('class="r2-summary', html)

        positions = [
            html.index(f'id="{section_id}"')
            for section_id in (
                "overview",
                "resume-start",
                "impact",
                "skills",
                "experience",
                "credentials",
            )
        ]
        constellation = html.index("<!-- shared-career-constellation:start -->")
        self.assertEqual(positions, sorted(positions))
        self.assertLess(positions[-1], constellation)

    def test_legacy_opening_anchors_resolve_inside_the_new_overview(self):
        html = self.render().get_data(as_text=True)
        overview_start = html.index('id="overview"')
        resume_start = html.index('id="resume-start"', overview_start)
        overview_html = html[overview_start:resume_start]

        self.assertIn('id="summary"', overview_html)
        self.assertIn('id="resume-overview"', overview_html)
        self.assertIn('href="#resume-start"', overview_html)
        self.assertIn('href="#skills"', overview_html)
        self.assertIn('href="#experience"', overview_html)
        self.assertIn('href="#credentials"', overview_html)

    def test_public_projection_uses_pete_data_and_never_fixture_content(self):
        html = self.render().get_data(as_text=True)

        for public_content in (
            "Pete Carter",
            "Systems Engineer · Technical Leader",
            "30+",
            "9 / $19.2M",
            "Purpose. People. Impact.",
            "Northrop Grumman",
            "L3Harris",
            "Department of Defense / U.S. Air Force",
        ):
            self.assertIn(public_content, html)
        for fixture_content in (
            "Maya Chen",
            "Lumen Harbor",
            "Illustrative renderer fixture",
            "data-fixture-id",
            "fixture-owner-",
        ):
            self.assertNotIn(fixture_content, html)

    def test_final_context_rails_and_primary_actions_are_distinct(self):
        html = self.render().get_data(as_text=True)
        page_start = html.index('id="living-resume-page"')
        page_end = html.index("</div>\n\n    </main>", page_start)
        page_html = html[page_start:page_end]
        overview_start = page_html.index("data-overview-root")
        resume_start = page_html.index('id="resume-start"', overview_start)
        overview_html = page_html[overview_start:resume_start]

        self.assertEqual(page_html.count("r2-overview-context-rail"), 1)
        self.assertEqual(page_html.count("r2-overview-ai-rail"), 1)
        self.assertEqual(page_html.count("data-hero-ai-search"), 1)
        self.assertNotIn("r2-context-ask-primary", page_html)
        self.assertEqual(
            page_html.count("/static/files/pete-carter-resume.pdf"),
            1,
        )
        self.assertEqual(overview_html.count(">Connect</a>"), 1)
        self.assertEqual(overview_html.count(">View résumé</a>"), 1)
        self.assertIn("Approved public context only", page_html)
        self.assertIn("data-r2-ai-context", page_html)
        self.assertEqual(page_html.count('class="overview-chapter-copy"'), 3)

        javascript = (
            ROOT / "static/js/living-resume-v2.js"
        ).read_text(encoding="utf-8")
        for section_id in ("overview", "impact", "skills", "experience", "credentials"):
            self.assertIn(f"{section_id}:", javascript)
        self.assertIn(
            "aiContextSection.textContent = sectionLabels[sectionId]",
            javascript,
        )

    def test_summary_fallback_remains_truthful_when_publication_is_absent(self):
        with patch.object(
            app_module,
            "build_public_overview_projection",
            return_value=None,
        ):
            response = self.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="r2-summary r2-summary--fallback"', response.data)
        self.assertIn(b'id="summary"', response.data)
        self.assertIn(b'data-r2-ai-context>Summary</strong>', response.data)
        self.assertNotIn(b"data-overview-root", response.data)

    def test_invalid_publication_fails_closed_to_summary(self):
        with patch.object(
            app_module,
            "build_public_overview_projection",
            side_effect=OverviewProjectionError(
                "unknown_metric",
                "invalid public selection",
            ),
        ):
            response = self.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="r2-summary r2-summary--fallback"', response.data)
        self.assertNotIn(b"data-publication-state", response.data)

    def test_center_stage_uses_normal_scale_and_constellation_stays_full_width(self):
        css = (ROOT / "static/css/resume2.css").read_text(encoding="utf-8")
        overview_css = (
            ROOT / "static/css/member-overview.css"
        ).read_text(encoding="utf-8")

        self.assertIn(
            ".resume-v2[data-public-overview] > .r2-page-grid {\n    zoom: 1;",
            css,
        )
        self.assertIn(
            ".resume-v2 .r2-page-grid {\n    width: min(98vw, 118rem);",
            css,
        )
        self.assertIn(
            "grid-template-columns: 11rem minmax(0, 90rem) 15rem;",
            css,
        )
        self.assertIn(
            ".resume-v2 .lr-constellation {\n    width: 100%;",
            css,
        )
        self.assertIn("zoom: 1;", overview_css)
        self.assertIn("transform: none;", overview_css)
        self.assertNotIn("\n* {\n  box-sizing: border-box;", overview_css)

    def test_public_integration_adds_no_mutation_or_public_preview_route(self):
        overview_rules = [
            rule
            for rule in app_module.app.url_map.iter_rules()
            if "overview" in rule.rule
        ]
        self.assertEqual(
            [rule.rule for rule in overview_rules if "member-overview" in rule.rule],
            ["/_internal/member-overview"],
        )
        for rule in overview_rules:
            self.assertEqual(
                rule.methods.intersection({"POST", "PUT", "PATCH", "DELETE"}),
                set(),
            )


if __name__ == "__main__":
    unittest.main()
