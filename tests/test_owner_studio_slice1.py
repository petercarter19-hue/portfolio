"""Contract tests for the default-off protected Studio Slice 1 frame."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import render_template

from app import app
from identity import AuthenticationRequired
from services.database_service import DatabaseServiceError


ROUTE = "/app/studio/build-your-future"


def member(name, user_key):
    return SimpleNamespace(display_name=name, user_key=user_key)


class StudioSliceOneRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED")
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = False

    def tearDown(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = self.original_flag

    def test_flag_off_is_neutral_and_resolves_no_identity_or_studio_asset(self):
        with patch("auth_routes.get_current_identity") as identity:
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"owner-studio.css", response.data)
        self.assertNotIn(b"Build Your Future", response.data)
        identity.assert_not_called()

    def test_signed_out_member_gets_the_exact_safe_return_path(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = True
        with patch(
            "auth_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/auth/sign-in?return_to=/app/studio/build-your-future",
        )

    def test_ready_frame_is_private_no_store_and_contains_only_its_owner(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = True
        with patch(
            "auth_routes.get_current_identity",
            return_value=member("Avery Member", "owner-avery"),
        ):
            avery = self.client.get(ROUTE)
        with patch(
            "auth_routes.get_current_identity",
            return_value=member("Morgan Member", "owner-morgan"),
        ):
            morgan = self.client.get(ROUTE)

        self.assertEqual(avery.status_code, 200)
        self.assertEqual(avery.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"Avery Member", avery.data)
        self.assertNotIn(b"Morgan Member", avery.data)
        self.assertIn(b"Morgan Member", morgan.data)
        self.assertNotIn(b"Avery Member", morgan.data)
        self.assertNotIn(b"owner-avery", avery.data)
        self.assertNotIn(b"owner-morgan", morgan.data)

    def test_frame_does_not_invent_a_published_slate_or_accept_a_browser_url(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = True
        with patch(
            "auth_routes.get_current_identity",
            return_value=member("Avery Member", "owner-avery"),
        ):
            response = self.client.get(
                ROUTE + "?published_slate_url=https://attacker.example/member"
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your published Slate is not connected yet.", response.data)
        self.assertNotIn(b"View published Slate", response.data)
        self.assertNotIn(b"attacker.example", response.data)
        self.assertNotIn(b"/petec/resume", response.data)

    def test_identity_failure_returns_a_payload_free_recovery_frame(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = True
        with patch(
            "auth_routes.get_current_identity",
            side_effect=DatabaseServiceError("identity storage unavailable"),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertIn(b"Build Your Future is temporarily unavailable.", response.data)
        self.assertIn(b'href="/app/studio/build-your-future">Try again</a>', response.data)
        self.assertNotIn(b"Avery Member", response.data)
        self.assertNotIn(b"Pete", response.data)

    def test_route_is_read_only(self):
        app.config["PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED"] = True
        rule = next(rule for rule in app.url_map.iter_rules() if rule.rule == ROUTE)

        self.assertEqual(rule.methods - {"HEAD", "OPTIONS"}, {"GET"})

    def test_denied_template_state_omits_member_identity(self):
        from auth_routes import _studio_frame_view_model

        with app.test_request_context(ROUTE):
            frame = _studio_frame_view_model(
                member("Avery Member", "owner-avery"), access_state="denied"
            )
            html = render_template(
                "owner_studio_build_your_future.html",
                page_title="Build Your Future",
                frame=frame,
            )

        self.assertIn("This protected workspace isn't available to your current session.", html)
        self.assertIn("Nothing private has been shown.", html)
        self.assertNotIn("Avery Member", html)
        self.assertNotIn("owner-avery", html)


class StudioFrameWorkshopUrlFallbackTests(unittest.TestCase):
    """MINOR 9 correction: the studio shell's navigation.workshop_url must
    not 404 in a flag-off deployment."""

    def setUp(self):
        self.original_workshop_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_workshop_flag

    def test_workshop_url_points_at_workshop_when_flag_is_on(self):
        from auth_routes import _studio_frame_view_model

        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with app.test_request_context("/app/studio/build-your-future"):
            frame = _studio_frame_view_model(member("Avery Member", "owner-avery"))

        self.assertEqual(frame["navigation"]["workshop_url"], "/app/workshop")

    def test_workshop_url_falls_back_to_owner_workspace_when_flag_is_off(self):
        from auth_routes import _studio_frame_view_model

        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        with app.test_request_context("/app/studio/build-your-future"):
            frame = _studio_frame_view_model(member("Avery Member", "owner-avery"))

        self.assertEqual(frame["navigation"]["workshop_url"], "/app")
        self.assertNotEqual(frame["navigation"]["workshop_url"], "/app/workshop")


if __name__ == "__main__":
    unittest.main()
