"""PS-PUBLIC-NAV-ROUTE-TRUTH-002 bounded navigation and route truth."""

import ast
import hashlib
import json
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from app import app
from safe_return import navigation_destinations, safe_return_path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_PATHS = (
    "/career-search",
    "/my-network",
    "/explore-profiles",
    "/for-recruiters",
)


def _search_records(html):
    block = html.split(
        '<script id="nav-search-data" type="application/json">', 1
    )[1].split("</script>", 1)[0]
    return json.loads(block)


def _decorated_function_source(source, node):
    """Return a portable exact slice containing decorators and function body."""
    lines = source.splitlines(keepends=True)
    start_line = min(
        [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
    )
    return "".join(lines[start_line - 1 : node.end_lineno])


class PublicNavigationRouteTruthTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            key: app.config.get(key)
            for key in (
                "TESTING",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",
                "PEERSLATE_WORKSHOP_ENABLED",
                "PEERSLATE_WORKSHOP_SESSION_ENABLED",
                "PEERSLATE_OPPORTUNITY_SLATE_ENABLED",
                "PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED",
            )
        }
        endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
        self.v2_registered = "opportunity_slate_v2.room" in endpoints
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="synthetic-navigation-member",
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_WORKSHOP_ENABLED=True,
            PEERSLATE_WORKSHOP_SESSION_ENABLED=True,
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=not self.v2_registered,
            PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=self.v2_registered,
        )
        self.client = app.test_client()

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def render(self, path):
        response = self.client.get(path, base_url="http://localhost")
        self.assertEqual(200, response.status_code, path)
        return response.get_data(as_text=True)

    def test_every_shell_representation_uses_the_same_promoted_routes(self):
        expected = ("/app", "/interview-studio")
        for path in ("/", "/petec/resume", "/interview-studio"):
            with self.subTest(path=path):
                html = self.render(path)
                for marker in (
                    '<ul class="platform-nav__links"',
                    '<ul class="platform-roomswitcher__list"',
                    '<ul class="platform-menu__links"',
                    '<ul class="platform-nojs-navigation__links"',
                ):
                    with self.subTest(marker=marker):
                        block = html.split(marker, 1)[1].split("</ul>", 1)[0]
                        self.assertEqual(
                            expected, tuple(re.findall(r'href="([^"]+)"', block))
                        )
                for removed in ("Workshop", "Capture", "Slate Board"):
                    self.assertNotIn(removed, html.split("</header>", 1)[0])

    def test_public_footer_keeps_privacy_and_copyright_without_old_marketing_links(self):
        for path in ("/", "/petec/resume"):
            with self.subTest(path=path):
                html = self.render(path)
                footer = html.split('<footer class="footer">', 1)[1].split(
                    "</footer>", 1
                )[0]
                self.assertIn("Your data is private. You control what you share.", footer)
                self.assertIn("&copy; 2026", footer)
                self.assertNotIn('href="/peerslate"', footer)
                self.assertNotIn('class="footer-brand"', footer)
                self.assertNotIn('class="footer-why-link"', footer)
                self.assertIn('class="platform-brand__logo" href="/"', html)

    def test_member_launchpad_is_neutral_and_uses_available_destinations(self):
        html = self.render("/app")
        titles = re.findall(r'owner-app__destination-title">([^<]+)', html)
        self.assertEqual(
            ["Opportunity Slate", "Interview Studio", "Community", "Settings"],
            titles,
        )
        for removed in ("My Opportunities", "Workshop", "Capture", "Profile"):
            self.assertNotIn(removed, titles)
        self.assertIn("private starting point, not your Profile", html)
        launchpad = html.split('<section class="owner-app', 1)[1].split(
            "</section>", 1
        )[0]
        self.assertNotIn("Pete Carter", launchpad)

    def test_public_profile_tabs_keep_story_and_resume_only(self):
        html = self.render("/petec/resume")
        block = html.split('class="profile-tabs__list"', 1)[1].split("</div>", 1)[0]
        self.assertEqual(
            ["/petec/my-story", "/petec/resume#resume-start"],
            re.findall(r'href="([^"]+)"', block),
        )
        self.assertNotIn("Slate Board", block)
        self.assertEqual(200, self.client.get("/petec/slate-board").status_code)

    def test_search_indexes_use_declared_routes_without_retired_promotions(self):
        public_titles = {
            item["title"] for item in _search_records(self.render("/"))
        }
        member_titles = {
            item["title"] for item in _search_records(self.render("/app"))
        }
        self.assertIn("My Story", public_titles)
        self.assertIn("My PeerSlate", member_titles)
        self.assertIn("Settings", member_titles)
        self.assertIn("Interview Studio", public_titles)
        self.assertTrue({"Community", "Opportunity Slate"}.isdisjoint(public_titles))
        self.assertTrue({"Interview Studio", "Community", "Opportunity Slate"} <= member_titles)
        for titles in (public_titles, member_titles):
            self.assertTrue({"Capture", "Workshop", "Slate Board"}.isdisjoint(titles))

    def test_opportunity_promotion_follows_the_registered_blueprint_flag(self):
        app.config.update(
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=self.v2_registered,
            PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=not self.v2_registered,
        )
        with app.test_request_context("/"):
            self.assertNotIn(
                "opportunity",
                {item["key"] for item in navigation_destinations("shell")},
            )

        app.config.update(
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=not self.v2_registered,
            PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=self.v2_registered,
        )
        with app.test_request_context("/"):
            self.assertIn(
                "opportunity",
                {item["key"] for item in navigation_destinations("shell")},
            )

    def test_quiet_preview_sitemap_advertises_no_public_route(self):
        response = self.client.get("/sitemap.xml", base_url="https://peerslate.com")
        self.assertEqual(response.status_code, 200)
        root = ET.fromstring(response.get_data(as_text=True))
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        paths = [node.text.removeprefix("https://peerslate.com") for node in root.findall("s:url/s:loc", namespace)]
        self.assertEqual(paths, [])

    def test_declared_safe_returns_are_exact_and_route_aware(self):
        exact = (
            "/app",
            "/app/settings",
            "/app/capture",
            "/app/workshop",
            "/app/workshop/add",
            "/app/workshop/work",
            "/app/workshop/work/session",
            "/the-slate",
            "/the-slate/recently-deleted",
            "/the-slate/policy",
            "/interview-studio",
            "/interview-studio/history",
        )
        with app.test_request_context("/"), patch.dict(
            os.environ,
            {"INTERVIEW_VIDEO_STUDIO": "preview", "INTERVIEW_PROGRESS_HISTORY": "preview"},
        ):
            for path in exact:
                with self.subTest(path=path):
                    self.assertEqual(path, safe_return_path(path))
            for query in ("mode=me", "mode=ai", "mode=video"):
                self.assertEqual(
                    f"/interview-studio?{query}",
                    safe_return_path(f"/interview-studio?{query}"),
                )
            if self.v2_registered:
                self.assertEqual(
                    "/opportunity-slate?step=replace",
                    safe_return_path("/opportunity-slate?step=replace"),
                )
            else:
                self.assertEqual("/app", safe_return_path("/opportunity-slate"))

        with app.test_request_context("/"), patch.dict(
            os.environ,
            {"INTERVIEW_VIDEO_STUDIO": "false", "INTERVIEW_PROGRESS_HISTORY": "false"},
        ):
            self.assertEqual("/app", safe_return_path("/interview-studio?mode=video"))
            self.assertEqual("/app", safe_return_path("/interview-studio/history"))
            self.assertEqual(
                "/interview-studio?mode=me",
                safe_return_path("/interview-studio?mode=me"),
            )

        with app.test_request_context("/"):
            for flag in (
                "PEERSLATE_WORKSHOP_ENABLED",
                "PEERSLATE_WORKSHOP_SESSION_ENABLED",
            ):
                with self.subTest(disabled_flag=flag):
                    app.config[flag] = False
                    self.assertEqual("/app", safe_return_path("/app/workshop/work"))
                    self.assertEqual(
                        "/app", safe_return_path("/app/workshop/work/session")
                    )
                    app.config[flag] = True

    def test_opaque_and_action_routes_collapse_without_reflecting_keys(self):
        cases = {
            "/app/settings/export/private-job/download": "/app/settings",
            "/app/capture/voice/private-source/audio": "/app/capture",
            "/app/capture/photo/private-source/preview": "/app/capture",
            "/app/workshop/items/private-item/edit": "/app/workshop",
            "/app/workshop/work/session/review": "/app/workshop/work/session",
            "/app/workshop/preview/reset": "/app/workshop",
            "/the-slate/posts/private-post": "/the-slate",
        }
        if self.v2_registered:
            cases["/opportunity-slate/source"] = "/opportunity-slate"
        with app.test_request_context("/"):
            for candidate, expected in cases.items():
                with self.subTest(candidate=candidate):
                    resolved = safe_return_path(candidate)
                    self.assertEqual(expected, resolved)
                    self.assertNotIn("private-", resolved)

    def test_unsafe_unknown_and_undeclared_queries_fail_closed(self):
        candidates = (
            "/app/unknown",
            "/interview-studio/unknown",
            "/the-slate/unknown",
            "/app/settings?tab=account",
            "/interview-studio?mode=unknown",
            "/interview-studio?mode=me&mode=ai",
            "/opportunity-slate?step=delete",
            "/app/../.auth/logout",
            "/app/%2e%2e/.auth/logout",
            "/app/%252e%252e/.auth/logout",
            "/app%2fsettings",
            "/app%252fsettings",
            "/app%5csettings",
            "/app%255csettings",
            "/app%ZZ",
            "/app#fragment",
            "//attacker.example/app",
            "https://attacker.example/app",
            "/app\x00outside",
            "/app" + ("x" * 2049),
        )
        with app.test_request_context("/"):
            for candidate in candidates:
                with self.subTest(candidate=repr(candidate)):
                    self.assertEqual("/app", safe_return_path(candidate))
            self.assertEqual(
                "/app",
                safe_return_path("https://attacker.example", "//bad.example"),
            )
            app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
            self.assertEqual(
                "/app",
                safe_return_path("https://attacker.example", "/app/workshop"),
            )


class FrozenPreviewContractTests(unittest.TestCase):
    """Freeze preview handlers, referring cards/templates, and discovery."""

    TEMPLATE_HASHES = {
        "templates/peerslate.html": "5be0be9c4440ca3b9a5286b83395e150533489e563490f80e38d29de35bf0fb9",
        "templates/platform_page.html": "2c887c30dbb0bf4b2532a055f0ef1d84def4f38daea37363456d2da3d6a3b928",
    }
    HANDLER_HASHES = {
        "career_search": "27486ecb9c9be10dd5dc72373dc48e1e3e4c66ab1e738cfde5c5789e23d8a72d",
        "my_network": "011c9d47954d4857974c2bdb38a8da7fc6a81dd810da9cf8204099423ff5f9a7",
        "explore_profiles": "4bf21abd0b19d72155564303d3937c1601312adb31529dfa435b0e51a5af6059",
        "for_recruiters": "93a77f27d9317c9325df300f4adf4075cce754b17e22a9c39d977d8451c6c60c",
    }

    def test_referring_card_and_page_template_bytes_match_activated_main(self):
        for relative_path, expected in self.TEMPLATE_HASHES.items():
            with self.subTest(path=relative_path):
                actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
                self.assertEqual(expected, actual)

    def test_preview_handler_source_matches_activated_main(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name, expected in self.HANDLER_HASHES.items():
            with self.subTest(handler=name):
                # Bind the route decorator and exact handler body to the
                # accepted activation source. ``ast.dump`` is not portable
                # across Python versions because its fields follow the
                # interpreter's AST schema.
                payload = _decorated_function_source(
                    source, functions[name]
                ).encode()
                self.assertEqual(expected, hashlib.sha256(payload).hexdigest())

    def test_preview_handler_freeze_detects_route_decorator_changes(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "career_search"
        )
        original = _decorated_function_source(source, function)

        changed_source = source.replace(
            "@app.route('/career-search')",
            "@app.route('/career-search-changed')",
            1,
        )
        changed_tree = ast.parse(changed_source)
        changed_function = next(
            node
            for node in changed_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "career_search"
        )
        changed = _decorated_function_source(changed_source, changed_function)

        self.assertNotEqual(original, changed)
        self.assertNotEqual(
            hashlib.sha256(original.encode()).hexdigest(),
            hashlib.sha256(changed.encode()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
