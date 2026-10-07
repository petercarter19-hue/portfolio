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

    def test_public_resume_renders_published_overview_without_fixture_state(self):
        response = self.client.get("/petec/resume", base_url="http://localhost")
        self.assertEqual(response.status_code, 200)
        for current_marker in (
            b'class="lr-page resume-v2 resume-consolidated"',
            b'data-overview-root',
            b'data-publication-state="published"',
            b'data-publication-revision="1"',
            b'id="resume-overview"',
            b'id="impact"',
            b'id="skills"',
            b'id="experience"',
            b'id="credentials"',
            b'data-chat-open',
            b'data-sage-rail',
        ):
            self.assertIn(current_marker, response.data)
        for internal_marker in (
            b"Fixture review",
            b"data-fixture-id",
            b"overview_fixtures",
            b"Member Overview renderer review",
            b"Maya Chen",
            b"Illustrative renderer fixture",
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


class IPv6LoopbackCompatibilityTests(unittest.TestCase):
    def test_real_route_allows_only_exact_loopback_with_native_valid_ports(self):
        from flask import request
        client = app.test_client()
        for host in ("[::1]", "[::1]:5000", "[::1]:65535"):
            with self.subTest(host=host):
                response = client.get("/_internal/member-overview", headers={"Host": host})
                self.assertEqual(response.status_code, 200)
                with app.test_request_context("/", headers={"Host": host}):
                    self.assertEqual(request.host, host)
        for host in ("[::2]", "[::ffff:192.0.2.1]", "[2001:db8::1]",
                     "[::1]:0", "[::1]:65536", "[::1]:99999", "[::1]:00080",
                     "[::1]:-1", "[::1]:abc", "[::1].evil.example", "[::1]@evil.example",
                     "[::1] ", "[::1", "::1", "evil.example", "localhost:99999"):
            with self.subTest(host=host):
                response = client.get("/_internal/member-overview", headers={"Host": host})
                self.assertEqual(response.status_code, 400)

    def test_loopback_requires_explicit_entry_without_changing_native_unrestricted_semantics(self):
        from werkzeug.sansio import utils
        check = utils.host_is_trusted
        for refs in (["[::1]"], "[::1]", ("localhost", "[::1]")):
            with self.subTest(refs=refs):
                self.assertTrue(check("[::1]:5000", refs))
        for refs in (["localhost"], ["::1"], [".[::1]"], ["[::2]"]):
            with self.subTest(refs=refs):
                self.assertFalse(check("[::1]", refs))
        for refs in (None, []):
            with self.subTest(refs=refs):
                self.assertTrue(check("[::2]", refs))
                self.assertFalse(check("[::1]:65536", refs))
        client = app.test_client()
        with patch.dict(app.config, {"TRUSTED_HOSTS": ["localhost"]}):
            self.assertEqual(client.get("/_internal/member-overview", headers={"Host": "[::1]"}).status_code, 400)

    def test_installation_is_idempotent_and_inactive_for_other_versions(self):
        from app import _install_werkzeug_ipv6_loopback_compat
        from werkzeug.sansio import utils
        installed = utils.host_is_trusted
        _install_werkzeug_ipv6_loopback_compat()
        _install_werkzeug_ipv6_loopback_compat()
        self.assertIs(utils.host_is_trusted, installed)
        sentinel = lambda *_args, **_kwargs: False
        with patch.object(utils, "host_is_trusted", sentinel), patch("importlib.metadata.version", return_value="3.1.10"):
            _install_werkzeug_ipv6_loopback_compat()
            self.assertIs(utils.host_is_trusted, sentinel)

    def test_forwarded_host_cannot_enable_loopback_preview(self):
        client = app.test_client()
        self.assertEqual(client.get("/_internal/member-overview", headers={"Host": "evil.example", "X-Forwarded-Host": "[::1]"}).status_code, 400)
        self.assertEqual(client.get("/_internal/member-overview", headers={"Host": "peerslate.com", "X-Forwarded-Host": "[::1]"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
