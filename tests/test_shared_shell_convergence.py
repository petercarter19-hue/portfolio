"""PS-SHARED-SHELL-CONVERGENCE-001 shared server and static contracts."""

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app


ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
NAV_CSS = (ROOT / "static" / "css" / "public-navigation.css").read_text(
    encoding="utf-8"
)
SEARCH_JS = (ROOT / "static" / "js" / "public-site-search.js").read_text(
    encoding="utf-8"
)
MOBILE_JS = (ROOT / "static" / "js" / "public-mobile-nav.js").read_text(
    encoding="utf-8"
)


class _AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attributes = dict(attrs)
            self.current = {
                "href": attributes.get("href"),
                "current": attributes.get("aria-current"),
                "text": "",
            }

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.current["text"] = " ".join(self.current["text"].split())
            self.links.append(self.current)
            self.current = None


def _element_chunk(html, marker, end="</ul>"):
    return html.split(marker, 1)[1].split(end, 1)[0]


def _links(html, marker):
    parser = _AnchorParser()
    parser.feed(_element_chunk(html, marker))
    return parser.links


def _search_records(html):
    block = _element_chunk(
        html,
        '<script id="nav-search-data" type="application/json">',
        "</script>",
    )
    return json.loads(block)


class SharedShellConvergenceTests(unittest.TestCase):
    MISSING = object()
    CONFIG_KEYS = (
        "TESTING",
        "PEERSLATE_ALLOW_DEV_IDENTITY",
        "PEERSLATE_DEV_USER_KEY",
        "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",
        "PEERSLATE_WORKSHOP_ENABLED",
        "PEERSLATE_OPPORTUNITY_SLATE_ENABLED",
        "PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED",
        "PEERSLATE_AUTH_CLIENT_ID",
    )

    def setUp(self):
        self.original = {
            key: app.config[key] if key in app.config else self.MISSING
            for key in self.CONFIG_KEYS
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="shared-shell-convergence-member",
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_WORKSHOP_ENABLED=True,
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=True,
            PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=True,
            PEERSLATE_AUTH_CLIENT_ID="shared-shell-test-client",
        )
        self.client = app.test_client()

    def tearDown(self):
        for key, value in self.original.items():
            if value is self.MISSING:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def render(self, path):
        response = self.client.get(
            path, base_url="http://localhost", follow_redirects=False
        )
        return response, response.get_data(as_text=True)

    def test_authenticated_route_matrix_uses_one_shared_shell(self):
        expected_statuses = {
            "/": {200},
            "/petec/resume": {200},
            "/petec/about": {200},
            "/petec/hobbies": {200},
            "/petec/skills": {200},
            "/petec/contact": {200},
            "/app": {200},
            "/app/settings": {200, 503},
            "/app/capture": {200, 503},
            "/app/workshop": {200, 503},
            "/interview-studio": {200},
            "/the-slate": {200, 503},
            "/opportunity-slate": {200, 503},
        }
        for path, statuses in expected_statuses.items():
            with self.subTest(path=path):
                response, html = self.render(path)
                self.assertIn(response.status_code, statuses)
                self.assertEqual(html.count("public-navigation.css"), 1)
                self.assertEqual(html.count("js/public-site-search.js"), 1)
                self.assertEqual(html.count("js/public-mobile-nav.js"), 1)
                self.assertNotIn("js/site-search.js", html)
                self.assertNotIn("js/mobile-nav.js", html)
                self.assertEqual(html.count('id="nav-search-input"'), 1)
                self.assertEqual(html.count('id="nav-search-results"'), 1)
                self.assertEqual(html.count('id="platform-mobile-menu"'), 1)
                self.assertEqual(html.count('id="platform-account-menu"'), 1)
                self.assertEqual(html.count('href="#main-content"'), 1)
                self.assertEqual(html.count('id="main-content"'), 1)

    def test_all_navigation_representations_share_destinations_and_current_state(self):
        _, html = self.render("/app/workshop")
        markers = (
            '<ul class="platform-nav__links"',
            '<ul class="platform-roomswitcher__list"',
            '<ul class="platform-menu__links"',
            '<ul class="platform-nojs-navigation__links"',
        )
        representations = [_links(html, marker) for marker in markers]
        expected_hrefs = [
            "/petec/resume#overview",
            "/the-slate",
            "/interview-studio",
            "/opportunity-slate",
        ]
        for links in representations:
            self.assertEqual([link["href"] for link in links], expected_hrefs)
            self.assertEqual(
                [link["href"] for link in links if link["current"] == "page"],
                [],
            )

        records = _search_records(html)
        indexed = {record["href"]: record for record in records}
        for href in expected_hrefs:
            self.assertIn(href, indexed)
            self.assertTrue(indexed[href]["title"])
            self.assertTrue(indexed[href]["sub"])

    def test_existing_availability_flags_remove_destinations_everywhere(self):
        flag_cases = (
            ("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED", "/the-slate"),
        )
        markers = (
            '<ul class="platform-nav__links"',
            '<ul class="platform-roomswitcher__list"',
            '<ul class="platform-menu__links"',
            '<ul class="platform-nojs-navigation__links"',
        )
        for flag, href in flag_cases:
            with self.subTest(flag=flag):
                app.config[flag] = False
                _, html = self.render("/")
                for marker in markers:
                    self.assertNotIn(href, [link["href"] for link in _links(html, marker)])
                self.assertNotIn(href, [record["href"] for record in _search_records(html)])
                app.config[flag] = True
        app.config.update(
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=False,
            PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=False,
        )
        _, html = self.render("/")
        for marker in markers:
            self.assertNotIn(
                "/opportunity-slate", [link["href"] for link in _links(html, marker)]
            )
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        _, html = self.render("/")
        self.assertNotIn("/app/workshop", html.split("</header>", 1)[0])

    def test_protected_search_is_navigation_only_and_not_owner_capture(self):
        _, html = self.render("/app")
        titles = {record["title"] for record in _search_records(html)}
        self.assertTrue(
            {"My PeerSlate", "Settings", "Pete's Slate", "Interview Studio"}
            <= titles
        )
        for absent in ("Capture", "Ask Pete", "Profile", "Help", "Notification"):
            self.assertNotIn(absent, titles)

    def test_signed_out_access_and_privacy_boundaries_are_unchanged(self):
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        app.config["PEERSLATE_DEV_USER_KEY"] = None
        for path in ("/app", "/app/settings", "/app/capture"):
            with self.subTest(path=path):
                response, _ = self.render(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.headers["Location"],
                    f"/auth/sign-in?return_to={path}",
                )

        preview, html = self.render("/app/workshop")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.headers["Cache-Control"], "private, no-store")
        self.assertIn("Preview — this is", html)
        self.assertIn("preview is temporary.", html)
        self.assertNotIn('data-global-tabsource', html)

    def test_script_off_fallback_has_native_destinations_and_account_actions(self):
        _, html = self.render("/app")
        self.assertIn("PeerSlate navigation without JavaScript", html)
        self.assertIn(".global-header .platform-actions { display: none !important; }", html)
        fallback = _element_chunk(
            html, '<nav class="platform-nojs-navigation"', "</nav>"
        )
        for href in (
            "/petec/resume#overview",
            "/the-slate",
            "/interview-studio",
            "/opportunity-slate",
            "/app",
            "/app/settings",
        ):
            self.assertIn(f'href="{href}"', fallback)
        self.assertIn('method="post" action="/auth/sign-out"', fallback)
        self.assertIn(">Sign out</button>", fallback)

    def test_profile_pages_have_one_content_owned_heading(self):
        for path, identity_tag in (
            ("/petec/about", "<h1>Pete Carter</h1>"),
            ("/petec/hobbies", "<h1>Pete Carter</h1>"),
            ("/petec/skills", '<p class="profile-identity__name">Pete Carter</p>'),
            ("/petec/contact", '<p class="profile-identity__name">Pete Carter</p>'),
        ):
            with self.subTest(path=path):
                _, html = self.render(path)
                self.assertEqual(len(re.findall(r"<h1(?:\s|>)", html)), 1)
                self.assertIn(identity_tag, html)

    def test_homepage_destination_copy_is_truthful(self):
        _, html = self.render("/")
        self.assertIn("Sign in to open Interview Studio", html)
        self.assertIn("Sign in to practice in Interview Studio", html)
        self.assertNotIn("public Interview Studio", html)
        self.assertIn("My Story", html)
        self.assertIn("The person behind the work", html)
        self.assertNotIn("Pete's Project Work", html)
        self.assertNotIn("Project Update", html)

    def test_static_accessibility_contracts_are_explicit(self):
        for selector in (
            ".platform-brand__logo",
            ".platform-roomswitcher__trigger",
            ".platform-account__trigger",
            ".platform-menu-toggle",
            ".nav-search__input",
        ):
            self.assertIn(selector, NAV_CSS)
        self.assertGreaterEqual(NAV_CSS.count("2.75rem"), 10)
        self.assertIn("outline: 3px solid var(--ps-shell-focus)", NAV_CSS)
        self.assertIn("@media (forced-colors: active)", NAV_CSS)
        self.assertIn("@media (prefers-reduced-motion: reduce)", NAV_CSS)
        sign_in_rule = NAV_CSS.split(
            ".global-header .sign-in-btn,", 1
        )[1].split("}", 1)[0]
        self.assertIn("min-height: 2.75rem", sign_in_rule)
        self.assertIn('aria-autocomplete="list"', BASE)
        for semantic in (
            "aria-activedescendant",
            "aria-selected",
            "nav-search-option-",
        ):
            self.assertIn(semantic, SEARCH_JS)
        self.assertNotIn("input.blur()", SEARCH_JS)
        self.assertIn("restoreSafeFocus", MOBILE_JS)
        self.assertIn("disclosureClosers", MOBILE_JS)
        self.assertIn("menu.contains(document.activeElement)", MOBILE_JS)
        self.assertIn("panel.contains(document.activeElement)", MOBILE_JS)
        self.assertGreaterEqual(MOBILE_JS.count("window.addEventListener('resize'"), 2)

    def test_retired_scripts_are_deleted_and_unreferenced_by_the_shell(self):
        self.assertFalse((ROOT / "static" / "js" / "site-search.js").exists())
        self.assertFalse((ROOT / "static" / "js" / "mobile-nav.js").exists())
        self.assertNotIn("js/site-search.js", BASE)
        self.assertNotIn("js/mobile-nav.js", BASE)


if __name__ == "__main__":
    unittest.main()
