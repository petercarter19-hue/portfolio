import os
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-overview-renderer-key")

from app import app  # noqa: E402


class OverviewHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []
        self.h1_count = 0
        self.main_count = 0
        self.images = []
        self.overview_blocks = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "main":
            self.main_count += 1
        if tag == "img":
            self.images.append(attributes)
        classes = attributes.get("class", "").split()
        for class_name in classes:
            if class_name.startswith("overview-") and class_name in {
                "overview-story",
                "overview-career",
                "overview-impact",
                "overview-skills",
                "overview-credentials",
                "overview-chapters",
                "overview-quote",
                "overview-philosophy",
                "overview-future",
                "overview-resume-transition",
            }:
                self.overview_blocks.append(class_name)


class MemberOverviewRendererTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def render(self, fixture="experienced-leader", style="story-career", **params):
        query = {"fixture": fixture, "style": style, **params}
        return self.client.get(
            "/_internal/member-overview",
            query_string=query,
            base_url="http://localhost",
        )

    def test_all_five_fixtures_render_in_both_styles(self):
        fixtures = (
            "early-career",
            "career-changer",
            "experienced-leader",
            "independent-creative",
            "text-only",
        )
        for fixture in fixtures:
            for style, css_class in (
                ("story-career", "member-overview--story"),
                ("work-impact", "member-overview--work"),
            ):
                response = self.render(fixture, style)
                with self.subTest(fixture=fixture, style=style):
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(css_class.encode(), response.data)
                    self.assertIn(f'data-fixture-id="{fixture}"'.encode(), response.data)
                    self.assertIn(b"Illustrative renderer fixture", response.data)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_internal_route_is_loopback_only_by_default(self):
        for host in ("localhost", "127.0.0.1", "[::1]"):
            with self.subTest(host=host):
                response = self.client.get(
                    "/_internal/member-overview",
                    base_url=f"http://{host}",
                )
                self.assertEqual(response.status_code, 200)

        external = self.client.get(
            "/_internal/member-overview",
            base_url="https://peerslate.com",
        )
        self.assertEqual(external.status_code, 404)

        with patch.dict(os.environ, {"ENABLE_DESIGN_SYSTEM_PREVIEW": "1"}):
            enabled = self.client.get(
                "/_internal/member-overview",
                base_url="https://peerslate.com",
            )
        self.assertEqual(enabled.status_code, 200)

    def test_route_rejects_submitted_identity_and_unknown_options(self):
        for identity_key in (
            "member",
            "member_id",
            "owner",
            "owner_id",
            "profile",
            "profile_slug",
        ):
            response = self.client.get(
                "/_internal/member-overview",
                query_string={identity_key: "somebody-else"},
                base_url="http://localhost",
            )
            with self.subTest(identity_key=identity_key):
                self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.render("missing-fixture", "story-career").status_code,
            404,
        )
        self.assertEqual(
            self.render("early-career", "missing-style").status_code,
            404,
        )

    def test_public_resume_contract_has_no_internal_overview_state(self):
        response = self.client.get("/petec/resume", base_url="http://localhost")
        self.assertEqual(response.status_code, 200)
        for current_marker in (
            b'class="lr-page resume-v2 resume-consolidated"',
            b'id="resume-overview"',
            b'id="impact"',
            b'id="skills"',
            b'id="experience"',
            b'id="credentials"',
            b'data-chat-open',
            b'files/pete-carter-resume.pdf',
        ):
            self.assertIn(current_marker, response.data)
        for internal_marker in (
            b"Fixture review",
            b"data-overview-root",
            b"overview_fixtures",
            b"Member Overview renderer review",
        ):
            self.assertNotIn(internal_marker, response.data)

    def test_no_public_mutation_endpoint_was_added(self):
        overview_rules = [
            rule
            for rule in app.url_map.iter_rules()
            if "member-overview" in rule.rule
        ]
        self.assertEqual(len(overview_rules), 1)
        self.assertEqual(overview_rules[0].rule, "/_internal/member-overview")
        self.assertEqual(overview_rules[0].methods.intersection({"POST", "PUT", "PATCH", "DELETE"}), set())

    def test_rendered_fixture_contains_no_owner_or_source_identifiers(self):
        response = self.render("experienced-leader", "story-career")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"fixture-owner-", response.data)
        self.assertNotIn(b":role:", response.data)
        self.assertNotIn(b":media:", response.data)
        self.assertNotIn(b"provenance", response.data.lower())
        self.assertNotIn(b"verification", response.data.lower())

    def test_count_aware_and_missing_group_markup_has_no_empty_wrapper(self):
        early = self.render("early-career", "story-career")
        self.assertNotIn(b'class="overview-proof ', early.data)
        self.assertNotIn(b"overview-awards-heading", early.data)
        self.assertIn(b"Career Focus", early.data)
        self.assertEqual(early.data.count(b"overview-education-heading"), 2)

        text_only = self.render("text-only", "work-impact")
        self.assertIn(b'data-proof-count="2"', text_only.data)
        self.assertNotIn(b"<img", text_only.data)

        leader = self.render("experienced-leader", "work-impact")
        self.assertIn(b'data-proof-count="4"', leader.data)
        self.assertEqual(leader.data.count(b"class=\"overview-proof-item\""), 4)

    def test_preview_represents_pdf_and_public_ask_once(self):
        response = self.render("experienced-leader", "story-career", capture="1")
        self.assertEqual(response.data.count("Résumé PDF".encode()), 1)
        self.assertEqual(response.data.count(b"Ask Maya AI"), 1)
        self.assertNotIn(b"overview-review-toolbar", response.data)
        self.assertNotIn(b"member-overview-preview.js", response.data)

    def test_every_internal_anchor_has_a_rendered_destination(self):
        response = self.render("experienced-leader", "story-career")
        parser = OverviewHTMLParser()
        parser.feed(response.get_data(as_text=True))
        rendered_ids = set(parser.ids)
        for href in parser.hrefs:
            if href.startswith("#"):
                with self.subTest(href=href):
                    self.assertIn(href[1:], rendered_ids)
        self.assertEqual(parser.main_count, 1)
        self.assertEqual(parser.h1_count, 1)

    def test_server_rendered_meaning_survives_without_preview_javascript(self):
        response = self.render("career-changer", "work-impact", capture="1")
        for text in (
            "Jordan Blake",
            "Operations leader moving into service design",
            "Service Design Fellow",
            "Transferable strengths",
            "What I’m building toward",
            "Résumé begins here",
        ):
            self.assertIn(text, response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
