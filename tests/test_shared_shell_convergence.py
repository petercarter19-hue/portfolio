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


def _links(html, marker, end="</ul>"):
    parser = _AnchorParser()
    parser.feed(_element_chunk(html, marker, end))
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
        "PEERSLATE_RESUME_EDITOR_ENABLED",
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
                # Round 5 (PS-SITE-SHELL-ROUND5-001) has no header search field.
                self.assertEqual(html.count('id="nav-search-input"'), 0)
                self.assertEqual(html.count('id="nav-search-results"'), 0)
                self.assertEqual(html.count('site-header.css'), 1)
                self.assertEqual(html.count('<div class="ps-shell" id="site-header">'), 1)
                self.assertEqual(html.count('id="platform-mobile-menu"'), 1)
                self.assertEqual(html.count('id="platform-account-menu"'), 1)
                self.assertEqual(html.count('href="#main-content"'), 1)
                self.assertEqual(html.count('id="main-content"'), 1)

    def test_all_navigation_representations_share_destinations_and_current_state(self):
        # Round 5 (Pete, 2026-10-13): a signed-in member's bar opens only their
        # own resume; every other name is Soon text. The bar, the Menu sheet
        # and the no-script list are one server-derived list.
        app.config["PEERSLATE_RESUME_EDITOR_ENABLED"] = True
        _, html = self.render("/app/workshop")
        markers = (
            ('<nav class="ps-top__nav"', "</nav>"),
            ('<ul class="platform-menu__links"', "</ul>"),
            ('<ul class="platform-nojs-navigation__links"', "</ul>"),
        )
        representations = [_links(html, marker, end) for marker, end in markers]
        for links in representations:
            self.assertEqual([link["href"] for link in links], ["/app/resume"])
            self.assertEqual(
                [link["href"] for link in links if link["current"] == "page"],
                [],
            )
        _, resume = self.render("/app/resume")
        for marker, end in markers:
            self.assertEqual(
                [link["href"] for link in _links(resume, marker, end) if link["current"] == "page"],
                ["/app/resume"],
            )

        # The member search index (no longer drawn in the bar) is unchanged.
        records = _search_records(html)
        indexed = {record["href"]: record for record in records}
        for href in ("/app", "/the-slate", "/interview-studio", "/opportunity-slate"):
            self.assertIn(href, indexed)
            self.assertTrue(indexed[href]["title"])
            self.assertTrue(indexed[href]["sub"])

    def test_existing_availability_flags_remove_destinations_everywhere(self):
        flag_cases = (
            ("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED", "/the-slate"),
        )
        markers = (
            ('<nav class="ps-top__nav"', "</nav>"),
            ('<ul class="platform-menu__links"', "</ul>"),
            ('<ul class="platform-nojs-navigation__links"', "</ul>"),
        )
        for flag, href in flag_cases:
            with self.subTest(flag=flag):
                app.config[flag] = False
                _, html = self.render("/")
                for marker, end in markers:
                    self.assertNotIn(href, [link["href"] for link in _links(html, marker, end)])
                self.assertNotIn(href, [record["href"] for record in _search_records(html)])
                app.config[flag] = True
        app.config.update(
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=False,
            PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=False,
        )
        _, html = self.render("/")
        for marker, end in markers:
            self.assertNotIn(
                "/opportunity-slate", [link["href"] for link in _links(html, marker, end)]
            )
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        _, html = self.render("/")
        self.assertNotIn("/app/workshop", html.split("</header>", 1)[0])

    def test_protected_search_is_navigation_only_and_not_owner_capture(self):
        _, html = self.render("/app")
        titles = {record["title"] for record in _search_records(html)}
        self.assertTrue(
            {"My PeerSlate", "Settings", "My PeerSlate", "Interview Studio"}
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
        self.assertIn(".global-header .ps-top__right { display: none !important; }", html)
        fallback = _element_chunk(
            html, '<nav class="platform-nojs-navigation"', "</nav>"
        )
        # Round 5: the member's own resume (when its route is available) plus
        # the account actions; the Soon names are not destinations.
        for href in ("/app/settings",):
            self.assertIn(f'href="{href}"', fallback)
        for soon in ("/the-slate", "/interview-studio", "/opportunity-slate"):
            self.assertNotIn(f'href="{soon}"', fallback)
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

    def test_homepage_round_five_entry_copy_is_truthful(self):
        # PS-SITE-SHELL-ROUND5-001: Pete's approved round-5 home page. The
        # only actions are Pete's public demo resume and story.
        _, html = self.render("/")
        main = re.search(
            r'<main\b[^>]*\bid="main-content"[^>]*>(.*?)</main>',
            html,
            flags=re.DOTALL,
        ).group(1)
        self.assertIn("<span>Your Work.</span> <span>Your Story.</span> <span>Your Future.</span>", main)
        self.assertIn("A portfolio that tells your story and answers for you.", main)
        self.assertIn("Access is by invitation for now. See it working on Pete’s resume.", main)
        self.assertEqual(
            ["/petec/resume", "/petec/my-story"], re.findall(r'href="([^"]+)"', main)
        )
        for retired_copy in (
            "Sign in to open Interview Studio",
            "Sign in to practice in Interview Studio",
            "Try Interview AI",
            "The person behind the work",
            "Pete's Project Work",
            "Project Update",
            "A considered beginning",
        ):
            self.assertNotIn(retired_copy, main)

    def test_static_accessibility_contracts_are_explicit(self):
        HEADER_CSS = (ROOT / "static" / "css" / "site-header.css").read_text(
            encoding="utf-8"
        )
        for selector in (
            ".platform-account__trigger",
            ".platform-menu",
        ):
            self.assertIn(selector, NAV_CSS)
        # The round-5 bar's own focus, forced-colours and target contracts.
        for contract in (
            "#site-header :focus-visible",
            "outline: 2px solid #fff",
            "@media (forced-colors: active)",
            "#site-header .ps-top__menu",
            "height: 40px",
        ):
            self.assertIn(contract, HEADER_CSS)
        self.assertGreaterEqual(NAV_CSS.count("2.75rem"), 10)
        self.assertIn("outline: 3px solid var(--ps-shell-focus)", NAV_CSS)
        self.assertIn("@media (forced-colors: active)", NAV_CSS)
        self.assertIn("@media (prefers-reduced-motion: reduce)", NAV_CSS)
        # Round 5's Sign in (8px padding on 14.5px text, about 36px tall) and
        # the 40px Menu and account controls clear the WCAG 2.2 AA 24px
        # target minimum.
        sign_in_rule = HEADER_CSS.split("#site-header .ps-top__signin {", 1)[1].split("}", 1)[0]
        self.assertIn("padding: 8px 16px", sign_in_rule)
        self.assertIn("font: 600 14.5px", sign_in_rule)
        self.assertNotIn('aria-autocomplete="list"', BASE)
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
        self.assertIn("has-platform-menu-open", MOBILE_JS)
        self.assertIn("addEventListener('focusin'", MOBILE_JS)
        self.assertIn("setMenuOpen(false, false)", MOBILE_JS)
        self.assertNotIn("aria-modal", MOBILE_JS)

    def test_retired_scripts_are_deleted_and_unreferenced_by_the_shell(self):
        self.assertFalse((ROOT / "static" / "js" / "site-search.js").exists())
        self.assertFalse((ROOT / "static" / "js" / "mobile-nav.js").exists())
        self.assertNotIn("js/site-search.js", BASE)
        self.assertNotIn("js/mobile-nav.js", BASE)


if __name__ == "__main__":
    unittest.main()
