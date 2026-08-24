import base64
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from services.database_service import DatabaseServiceError


def easy_auth_header(subject, display_name="Example Member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": display_name},
            {"typ": "email", "val": f"{subject}@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


class OwnerSettingsTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_AUTH_ISSUER": app.config.get("PEERSLATE_AUTH_ISSUER"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_AUTH_ISSUER=None,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    def test_anonymous_settings_redirect_to_sign_in(self):
        response = self.client.get("/app/settings")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/auth/sign-in?return_to=/app/settings",
        )

    @patch("identity.database_service.first_row")
    def test_arbitrary_signed_in_members_see_their_account_information(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        members = (
            (
                "danielle-id",
                "45ab728a-44bc-4f80-a79f-d010e04d5453",
                "Danielle Example",
                "danielle@example.com",
            ),
            (
                "riley-id",
                "0fa7a288-63b7-4298-b165-540095494eaa",
                "Riley Member",
                "riley@example.com",
            ),
        )

        for subject, user_key, display_name, email in members:
            with self.subTest(subject=subject):
                first_row.return_value = {
                    "account_key": user_key,
                    "user_key": user_key,
                    "display_name": display_name,
                    "email": email,
                }

                response = self.client.get(
                    "/app/settings",
                    headers=easy_auth_header(subject, display_name),
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(display_name.encode(), response.data)
                self.assertIn(email.encode(), response.data)
                self.assertIn(b"Account status", response.data)

    @patch("identity.database_service.first_row")
    def test_settings_page_renders_the_sign_out_form(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Example Member",
            "email": "example@example.com",
        }

        response = self.client.get(
            "/app/settings",
            headers=easy_auth_header("example-id"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<form method="post" action="/auth/sign-out">', response.data)
        self.assertIn(b'<button class="owner-app__sign-out" type="submit">', response.data)

    def test_sign_out_endpoint_keeps_same_origin_post_behavior(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        response = self.client.post(
            "/auth/sign-out",
            headers={"Origin": "http://localhost"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/.auth/logout?post_logout_redirect_uri=%2F",
        )

    @patch("identity.database_service.first_row")
    def test_settings_has_one_main_landmark_and_one_skip_target(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Example Member",
            "email": "example@example.com",
        }

        response = self.client.get(
            "/app/settings",
            headers=easy_auth_header("example-id"),
        )
        html = response.get_data(as_text=True)

        self.assertEqual(len(re.findall(r"<main\b", html)), 1)
        self.assertEqual(html.count('id="main-content"'), 1)
        self.assertEqual(html.count('href="#main-content"'), 1)

    @patch("identity.database_service.first_row")
    def test_settings_uses_member_wording_and_states_private_as_a_rule(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Example Member",
            "email": "example@example.com",
        }

        response = self.client.get(
            "/app/settings",
            headers=easy_auth_header("example-id"),
        )
        html = response.get_data(as_text=True)

        self.assertIn("Signed-in member settings", html)
        self.assertNotIn("Private member workspace", html)
        self.assertIn('aria-label="Member settings actions"', html)
        self.assertNotIn("Private owner workspace", html)
        self.assertNotIn('aria-label="Owner settings actions"', html)
        self.assertIn("Private by default", html)
        self.assertIn("current product rule", html)
        self.assertIn("not a saved member preference", html)

    @patch("identity.database_service.first_row")
    def test_my_data_reports_every_truth_state_without_controls(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Example Member",
            "email": "example@example.com",
        }

        response = self.client.get(
            "/app/settings",
            headers=easy_auth_header("example-id"),
        )
        html = response.get_data(as_text=True)
        section_start = html.index('<section class="owner-app__section"')
        section_end = html.index("</section>", section_start)
        my_data = html[section_start:section_end]
        my_data_text = " ".join(my_data.split())

        for expected in (
            "Account and identity",
            "Member-created records",
            "Preferences and consents",
            "Account-wide export, deletion, and closure",
            "Retention, backups, and provider processing",
            "Current.",
            "Upcoming.",
            "Not available today.",
            "Not yet resolved.",
            "item-level actions already available",
            "no consolidated retention schedule",
            "complete-erasure promise",
        ):
            self.assertIn(expected, my_data_text)
        for interactive_tag in ("<a ", "<button", "<form", "<input", "<select", "<textarea"):
            self.assertNotIn(interactive_tag, my_data)

    @patch("identity.database_service.first_row")
    def test_identity_database_failure_returns_unavailable_without_member_data(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = DatabaseServiceError("database unavailable")

        response = self.client.get(
            "/app/settings",
            headers=easy_auth_header("example-id"),
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Sign in is not configured yet", response.data)
        self.assertNotIn(b"example-id@example.com", response.data)
        self.assertNotIn(b"My Data", response.data)

    def test_settings_template_adds_no_javascript_or_fake_field(self):
        template = Path("templates/owner_settings.html").read_text(encoding="utf-8")

        self.assertNotIn("<script", template.lower())
        for field_tag in ("<input", "<select", "<textarea"):
            self.assertNotIn(field_tag, template.lower())

    def test_template_local_css_supports_mobile_reflow_and_long_values(self):
        template = Path("templates/owner_settings.html").read_text(encoding="utf-8")
        shared_css = Path("static/css/owner-app.css").read_text(encoding="utf-8")
        settings_rules = template.split("<style>", 1)[1].split("</style>", 1)[0]
        mobile_rules = settings_rules.split("@media (max-width: 540px)", 1)[1]

        self.assertIn("overflow-wrap: anywhere", settings_rules)
        self.assertIn(".owner-app__status--data", settings_rules)
        self.assertIn("grid-template-columns: 1fr", mobile_rules)
        self.assertIn(".owner-app__panel--settings", mobile_rules)
        self.assertIn("width: 100%", mobile_rules)
        self.assertNotIn(".owner-app__panel--settings", shared_css)


if __name__ == "__main__":
    unittest.main()
