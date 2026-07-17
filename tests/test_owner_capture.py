import base64
import json
import unittest
from unittest.mock import call, patch

from app import app
from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError


USER_KEY = "45ab728a-44bc-4f80-a79f-d010e04d5453"


def easy_auth_header(subject="capture-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Capture Member"},
            {"typ": "email", "val": "capture@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


def identity_row():
    return {
        "account_key": USER_KEY,
        "user_key": USER_KEY,
        "display_name": "Capture Member",
        "email": "capture@example.com",
    }


class OwnerCaptureTests(unittest.TestCase):
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

    def test_capture_procedures_are_explicitly_allowed(self):
        self.assertIn("usp_CreateCapture", ALLOWED_PROCEDURES)
        self.assertIn("usp_ListCapturesForOwner", ALLOWED_PROCEDURES)

    def test_anonymous_capture_redirects_to_sign_in(self):
        response = self.client.get("/app/capture")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/auth/sign-in?return_to=/app/capture",
        )

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_signed_in_member_sees_composer_and_own_captures(
        self, first_row, first_result
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        first_result.return_value = [
            {
                "capture_key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "capture_type": "text",
                "body": "A private project note",
                "visibility": "private",
                "status": "captured",
                "created_at_utc": "2026-07-17T18:00:00",
                "updated_at_utc": "2026-07-17T18:00:00",
            }
        ]

        response = self.client.get("/app/capture", headers=easy_auth_header())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'id="main-content"'), 1)
        self.assertIn(b'form class="owner-app__capture-form"', response.data)
        self.assertIn(b'maxlength="8000"', response.data)
        self.assertIn(b"A private project note", response.data)
        self.assertIn(b"Private", response.data)
        first_result.assert_called_once_with(
            "usp_ListCapturesForOwner",
            [("@UserKey", USER_KEY), ("@Take", 50)],
        )

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_empty_capture_state_is_honest(self, first_row, first_result):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        first_result.return_value = []

        response = self.client.get("/app/capture", headers=easy_auth_header())

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nothing captured yet", response.data)
        self.assertNotIn(b"Place in Journal", response.data)

    @patch("identity.database_service.first_row")
    def test_signed_in_member_can_save_trimmed_private_text(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        created_capture = {
            "capture_key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "body": "Remember this result",
        }
        first_row.side_effect = [identity_row(), created_capture]

        response = self.client.post(
            "/app/capture",
            data={"body": "  Remember this result  "},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/capture?saved=1")
        self.assertEqual(
            first_row.call_args_list,
            [
                call(
                    "usp_UpsertAppUserFromAuth",
                    [
                        ("@AuthProvider", "aad"),
                        ("@AuthIssuer", "https://example.ciamlogin.com/example/v2.0"),
                        ("@AuthSubject", "capture-member"),
                        ("@Email", "capture@example.com"),
                        ("@DisplayName", "Capture Member"),
                        ("@ProfileImageUrl", None),
                        ("@TimezoneName", None),
                    ],
                ),
                call(
                    "usp_CreateCapture",
                    [
                        ("@UserKey", USER_KEY),
                        ("@CaptureType", "text"),
                        ("@Body", "Remember this result"),
                    ],
                ),
            ],
        )

    @patch("identity.database_service.first_row")
    def test_blank_body_never_calls_create(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        response = self.client.post(
            "/app/capture",
            data={"body": "   \n  "},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/capture?error=required")
        self.assertEqual(first_row.call_count, 1)

    @patch("identity.database_service.first_row")
    def test_overlong_body_never_calls_create(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        response = self.client.post(
            "/app/capture",
            data={"body": "x" * 8001},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/capture?error=too-long")
        self.assertEqual(first_row.call_count, 1)

    @patch("identity.database_service.first_row")
    def test_utf16_limit_matches_browser_and_sql_for_emoji(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        response = self.client.post(
            "/app/capture",
            data={"body": "\U0001f4a1" * 4001},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/capture?error=too-long")
        self.assertEqual(first_row.call_count, 1)

    @patch("identity.database_service.first_row")
    def test_cross_site_post_is_denied_before_identity_or_create(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.post(
            "/app/capture",
            data={"body": "A cross-site capture"},
            headers={
                **easy_auth_header(),
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Cross-site capture requests are not allowed", response.data)
        first_row.assert_not_called()

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_validation_and_success_messages_are_accessible(
        self, first_row, first_result
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        first_result.return_value = []

        error_response = self.client.get(
            "/app/capture?error=required", headers=easy_auth_header()
        )
        saved_response = self.client.get(
            "/app/capture?saved=1", headers=easy_auth_header()
        )

        self.assertIn(b'role="alert"', error_response.data)
        self.assertIn(b"Write something before saving", error_response.data)
        self.assertIn(b'role="status"', saved_response.data)
        self.assertIn(b"Saved privately", saved_response.data)

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_list_storage_failure_returns_503(self, first_row, first_result):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        first_result.side_effect = DatabaseServiceError("unavailable")

        response = self.client.get("/app/capture", headers=easy_auth_header())

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Sign in is not configured yet", response.data)

    @patch("identity.database_service.first_row")
    def test_create_storage_failure_returns_503(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            DatabaseServiceError("unavailable"),
        ]

        response = self.client.post(
            "/app/capture",
            data={"body": "A valid capture"},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Sign in is not configured yet", response.data)

    @patch("identity.database_service.first_row")
    def test_create_without_returned_record_never_reports_saved(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), None]

        response = self.client.post(
            "/app/capture",
            data={"body": "A valid capture"},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"Saved privately", response.data)


if __name__ == "__main__":
    unittest.main()
