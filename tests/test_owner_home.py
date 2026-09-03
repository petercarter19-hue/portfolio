"""Regression proof for PS-OWNER-HOME-RETIREMENT-001."""

import unittest
from pathlib import Path

from app import app


ROOT = Path(__file__).resolve().parents[1]


class OwnerHomeRetirementTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_WORKSHOP_ENABLED": app.config.get(
                "PEERSLATE_WORKSHOP_ENABLED"
            ),
            "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": app.config.get(
                "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"
            ),
            "PEERSLATE_OPPORTUNITY_SLATE_ENABLED": app.config.get(
                "PEERSLATE_OPPORTUNITY_SLATE_ENABLED"
            ),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="owner-home-retirement-test",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_WORKSHOP_ENABLED=False,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=True,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original)

    def test_app_is_one_neutral_private_launchpad(self):
        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        body = response.get_data(as_text=True)
        self.assertIn("My PeerSlate", body)
        self.assertIn("private starting point, not your Profile", body)
        self.assertIn('aria-label="Your PeerSlate destinations"', body)
        self.assertIn('href="/app/capture"', body)
        self.assertIn('href="/app/settings"', body)
        self.assertIn('href="/interview-studio"', body)
        self.assertIn('href="/the-slate"', body)
        self.assertIn("My Opportunities", body)
        self.assertNotIn("Owner Home", body)
        self.assertNotIn("Capture a Moment", body)
        self.assertNotIn("/app/profile", body)
        self.assertNotIn('class="profile-tabs', body)
        self.assertEqual(body.count("<main"), 1)

    def test_capture_is_an_equal_destination_not_the_home(self):
        body = self.client.get("/app").get_data(as_text=True)
        self.assertEqual(body.count('class="owner-app__destination"'), 5)
        self.assertEqual(body.count('href="/app/capture"'), 1)
        self.assertNotIn("owner-app__primary", body)

    def test_workshop_is_rendered_only_when_its_real_route_is_enabled(self):
        hidden = self.client.get("/app").get_data(as_text=True)
        self.assertNotIn('href="/app/workshop"', hidden)

        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        visible = self.client.get("/app").get_data(as_text=True)
        self.assertIn('href="/app/workshop"', visible)
        self.assertIn(">Workshop<", visible)

    def test_gated_destinations_are_absent_when_off_and_real_when_on(self):
        app.config.update(
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=False,
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=False,
        )
        hidden = self.client.get("/app").get_data(as_text=True)
        self.assertNotIn('href="/the-slate"', hidden)
        self.assertNotIn('href="/opportunity-slate"', hidden)
        self.assertNotIn('"title": "Community"', hidden)
        self.assertNotIn('"title": "Opportunity Slate"', hidden)

        app.config.update(
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=True,
        )
        visible = self.client.get("/app").get_data(as_text=True)
        self.assertIn('href="/the-slate"', visible)
        self.assertIn('href="/opportunity-slate"', visible)
        self.assertNotEqual(self.client.get("/the-slate").status_code, 404)
        self.assertNotEqual(self.client.get("/opportunity-slate").status_code, 404)

    def test_retired_api_and_stale_flag_cannot_revive_owner_home(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        try:
            self.assertEqual(self.client.get("/api/v1/owner/home").status_code, 404)
            body = self.client.get("/app").get_data(as_text=True)
        finally:
            app.config.pop("PEERSLATE_OWNER_HOME_ENABLED", None)
        self.assertIn("My PeerSlate", body)
        self.assertNotIn("Owner Home", body)

    def test_executable_owner_home_files_and_references_are_gone(self):
        retired = (
            "services/owner_home_service.py",
            "templates/owner_home.html",
            "static/css/owner-home.css",
            "static/js/owner-home.js",
            "static/img/owner-home/atmosphere.png",
            "scripts/capture_ps_owner_home_evidence.py",
        )
        for relative in retired:
            with self.subTest(relative=relative):
                self.assertFalse((ROOT / relative).exists())

        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        auth_source = (ROOT / "auth_routes.py").read_text(encoding="utf-8")
        owner_source = (ROOT / "owner_routes.py").read_text(encoding="utf-8")
        base_source = (ROOT / "templates/base.html").read_text(encoding="utf-8")
        for source in (app_source, auth_source, owner_source, base_source):
            self.assertNotIn("PEERSLATE_OWNER_HOME_ENABLED", source)
            self.assertNotIn("standalone_owner_shell", source)
        self.assertNotIn("owner_home_service", auth_source)
        self.assertNotIn("owner_home_service", owner_source)
        self.assertNotIn('/api/v1/owner/home', owner_source)

    def test_account_navigation_uses_truthful_temporary_name(self):
        body = self.client.get("/app").get_data(as_text=True)
        self.assertIn('href="/app">My PeerSlate</a>', body)
        self.assertNotIn('href="/app">My Slate</a>', body)


if __name__ == "__main__":
    unittest.main()
