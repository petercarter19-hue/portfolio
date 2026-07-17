import base64
import json
import unittest
from unittest.mock import patch

from app import app


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
    def test_signed_in_member_sees_account_information(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Danielle Example",
            "email": "danielle@example.com",
        }

        response = self.client.get(
            "/app/settings",
            headers=easy_auth_header("danielle-id", "Danielle Example"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Danielle Example", response.data)
        self.assertIn(b"danielle@example.com", response.data)
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


if __name__ == "__main__":
    unittest.main()
