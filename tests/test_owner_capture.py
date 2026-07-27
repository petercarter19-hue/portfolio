import base64
import json
import unittest
from unittest.mock import call, patch

from app import app
from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError


USER_KEY = "45ab728a-44bc-4f80-a79f-d010e04d5453"
CAPTURE_KEY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ROW_VERSION = bytes.fromhex("0000000000000007")
ROW_VERSION_TOKEN = "0000000000000007"


# A browser always sends at least one same-origin signal on a form post, and
# owner writes now require one. Model that here so the tests exercise the real
# request shape; the cross-site tests override these keys explicitly.
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


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
    return {"X-MS-CLIENT-PRINCIPAL": encoded, **SAME_ORIGIN_HEADERS}


def identity_row():
    return {
        "account_key": USER_KEY,
        "user_key": USER_KEY,
        "display_name": "Capture Member",
        "email": "capture@example.com",
    }


def capture_row(**overrides):
    row = {
        "capture_key": CAPTURE_KEY,
        "capture_type": "text",
        "body": "A corrected project note",
        "original_body": "A private project note",
        "visibility": "private",
        "status": "captured",
        "active": True,
        "revision_number": 1,
        "revision_count": 1,
        "created_at_utc": "2026-07-17T18:00:00Z",
        "updated_at_utc": "2026-07-18T18:00:00Z",
        "row_version": ROW_VERSION,
    }
    row.update(overrides)
    return row


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
        expected = {
            "usp_CreateCapture",
            "usp_ListCapturesForOwner",
            "usp_GetCaptureForOwner",
            "usp_CorrectCapture",
            "usp_ArchiveCapture",
            "usp_RestoreCapture",
            "usp_DeleteCapture",
            "usp_ExportCaptureForOwner",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))

    def test_anonymous_capture_redirects_to_sign_in(self):
        response = self.client.get("/app/capture")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/auth/sign-in?return_to=/app/capture",
        )

    @patch("owner_routes.database_service.execute_procedure")
    @patch("owner_routes.database_service.first_row")
    def test_anonymous_lifecycle_and_export_redirect_without_database_calls(
        self, first_row, execute_procedure
    ):
        write_response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/archive",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            # An anonymous visitor still arrives from a real browser, so the
            # same-origin signal is present and the sign-in redirect (not the
            # cross-site refusal) is the behaviour under test.
            headers=SAME_ORIGIN_HEADERS,
        )
        export_response = self.client.get(f"/app/capture/{CAPTURE_KEY}/export")

        self.assertEqual(write_response.status_code, 302)
        self.assertEqual(export_response.status_code, 302)
        self.assertEqual(
            write_response.headers["Location"],
            "/auth/sign-in?return_to=/app/capture",
        )
        self.assertEqual(
            export_response.headers["Location"],
            "/auth/sign-in?return_to=/app/capture",
        )
        first_row.assert_not_called()
        execute_procedure.assert_not_called()

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_signed_in_member_sees_composer_and_own_captures(
        self, first_row, first_result
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        first_result.return_value = [capture_row()]

        response = self.client.get("/app/capture", headers=easy_auth_header())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'id="main-content"'), 1)
        self.assertIn(b'form class="owner-app__capture-form"', response.data)
        self.assertIn(b'maxlength="8000"', response.data)
        self.assertIn(b"A corrected project note", response.data)
        self.assertIn(b"Original capture", response.data)
        self.assertIn(b"A private project note", response.data)
        self.assertIn(b"Private", response.data)
        self.assertIn(b"Correct this capture", response.data)
        self.assertIn(b"Review as a Moment", response.data)
        self.assertIn(b'name="source_revision_number"', response.data)
        self.assertIn(b"Current correction version 1", response.data)
        self.assertIn(b"Archive", response.data)
        self.assertIn(b"Export JSON", response.data)
        self.assertIn(b"Delete permanently", response.data)
        self.assertIn(b'name="confirm_delete"', response.data)
        self.assertIn(b'value="delete"', response.data)
        self.assertNotIn(b'name="user_key"', response.data)
        self.assertNotIn(b'name="owner_profile_id"', response.data)
        first_result.assert_called_once_with(
            "usp_ListCapturesForOwner",
            [("@UserKey", USER_KEY), ("@Take", 50), ("@Archived", False)],
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

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_archived_view_uses_explicit_owner_scoped_filter(
        self, first_row, first_result
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        first_result.return_value = [
            capture_row(status="archived", active=False, revision_count=0)
        ]

        response = self.client.get(
            "/app/capture?view=archived", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Archived captures", response.data)
        self.assertIn(b"Restore", response.data)
        self.assertNotIn(b">Archive<", response.data)
        first_result.assert_called_once_with(
            "usp_ListCapturesForOwner",
            [("@UserKey", USER_KEY), ("@Take", 50), ("@Archived", True)],
        )

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

    @patch("identity.database_service.first_row")
    def test_correction_inserts_revision_with_owner_and_row_version(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), {"outcome": "success"}]

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/correct",
            data={
                "body": "  A corrected project note  ",
                "correction_note": "  Clarified the outcome  ",
                "expected_row_version": ROW_VERSION_TOKEN,
            },
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"], "/app/capture?changed=corrected"
        )
        self.assertEqual(
            first_row.call_args_list[-1],
            call(
                "usp_CorrectCapture",
                [
                    ("@UserKey", USER_KEY),
                    ("@CaptureKey", CAPTURE_KEY),
                    ("@ExpectedRowVersion", ROW_VERSION),
                    ("@CorrectedBody", "A corrected project note"),
                    ("@CorrectionNote", "Clarified the outcome"),
                ],
            ),
        )

    @patch("identity.database_service.first_row")
    def test_blank_or_overlong_correction_never_calls_lifecycle_procedure(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        blank = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/correct",
            data={"body": "  ", "expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )
        overlong = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/correct",
            data={"body": "x" * 8001, "expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )

        self.assertEqual(blank.headers["Location"], "/app/capture?error=required")
        self.assertEqual(overlong.headers["Location"], "/app/capture?error=too-long")
        self.assertEqual(first_row.call_count, 2)

    @patch("identity.database_service.first_row")
    def test_stale_foreign_or_missing_write_uses_one_generic_result(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            {"outcome": "not_found_or_changed"},
        ]

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/archive",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/capture?error=changed")
        self.assertEqual(
            first_row.call_args_list[-1],
            call(
                "usp_ArchiveCapture",
                [
                    ("@UserKey", USER_KEY),
                    ("@CaptureKey", CAPTURE_KEY),
                    ("@ExpectedRowVersion", ROW_VERSION),
                ],
            ),
        )

    @patch("identity.database_service.first_row")
    def test_archive_and_restore_are_owner_derived_row_version_writes(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            {"outcome": "success"},
            identity_row(),
            {"outcome": "success"},
        ]

        archived = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/archive",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )
        restored = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/restore",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )

        self.assertEqual(
            archived.headers["Location"], "/app/capture?changed=archived"
        )
        self.assertEqual(
            restored.headers["Location"], "/app/capture?changed=restored"
        )
        procedure_calls = [item.args[0] for item in first_row.call_args_list]
        self.assertIn("usp_ArchiveCapture", procedure_calls)
        self.assertIn("usp_RestoreCapture", procedure_calls)
        self.assertNotIn("usp_CreateMoment", procedure_calls)
        self.assertNotIn("usp_PublishCapture", procedure_calls)

    @patch("identity.database_service.first_row")
    def test_delete_requires_explicit_confirmation_before_database_call(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/delete",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"], "/app/capture?error=confirm-delete"
        )
        self.assertEqual(first_row.call_count, 1)

    @patch("identity.database_service.first_row")
    def test_explicit_delete_is_owner_derived_and_uses_post(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), {"outcome": "success"}]

        get_response = self.client.get(f"/app/capture/{CAPTURE_KEY}/delete")
        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/delete",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "confirm_delete": "delete",
            },
            headers=easy_auth_header(),
        )

        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/capture?changed=deleted")
        self.assertEqual(first_row.call_args_list[-1].args[0], "usp_DeleteCapture")

    @patch("identity.database_service.first_row")
    def test_malformed_key_or_row_version_never_calls_lifecycle_procedure(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        bad_key = self.client.post(
            "/app/capture/not-a-key/archive",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )
        bad_version = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/archive",
            data={"expected_row_version": "not-a-row-version"},
            headers=easy_auth_header(),
        )

        self.assertEqual(bad_key.headers["Location"], "/app/capture?error=changed")
        self.assertEqual(bad_version.headers["Location"], "/app/capture?error=changed")
        self.assertEqual(first_row.call_count, 2)

    @patch("identity.database_service.first_row")
    def test_cross_site_lifecycle_post_fails_before_identity(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/archive",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers={
                **easy_auth_header(),
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )

        self.assertEqual(response.status_code, 403)
        first_row.assert_not_called()

    @patch("owner_routes.database_service.execute_procedure")
    @patch("identity.database_service.first_row")
    def test_versioned_json_export_is_private_deterministic_and_owner_scoped(
        self, first_row, execute_procedure
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        execute_procedure.return_value = [
            [capture_row()],
            [
                {
                    "revision_number": 1,
                    "body": "A corrected project note",
                    "correction_note": "Clarified the outcome",
                    "corrected_at_utc": "2026-07-18T18:00:00Z",
                }
            ],
        ]

        response = self.client.get(
            f"/app/capture/{CAPTURE_KEY}/export", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn(
            f'attachment; filename="peerslate-capture-{CAPTURE_KEY}-v1.json"',
            response.headers["Content-Disposition"],
        )
        payload = response.get_json()
        self.assertEqual(payload["schema"], "peerslate.capture.export")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["capture"]["key"], CAPTURE_KEY)
        self.assertEqual(payload["capture"]["original_text"], "A private project note")
        self.assertEqual(payload["capture"]["current_version"]["revision_number"], 1)
        self.assertEqual(len(payload["capture"]["revisions"]), 1)
        self.assertNotIn("capture_id", response.get_data(as_text=True))
        self.assertNotIn("owner_profile_id", response.get_data(as_text=True))
        self.assertNotIn("user_key", response.get_data(as_text=True))
        execute_procedure.assert_called_once_with(
            "usp_ExportCaptureForOwner",
            [("@UserKey", USER_KEY), ("@CaptureKey", CAPTURE_KEY)],
        )

    @patch("owner_routes.database_service.execute_procedure")
    @patch("identity.database_service.first_row")
    def test_export_reads_ordered_revision_json_from_sql_contract(
        self, first_row, execute_procedure
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        exported = capture_row()
        exported["revisions_json"] = json.dumps(
            [
                {
                    "revision_number": 1,
                    "body": "A corrected project note",
                    "correction_note": None,
                    "corrected_at_utc": "2026-07-18T18:00:00Z",
                }
            ]
        )
        execute_procedure.return_value = [[exported]]

        response = self.client.get(
            f"/app/capture/{CAPTURE_KEY}/export", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["capture"]["revisions"][0]["revision_number"],
            1,
        )

    @patch("owner_routes.database_service.execute_procedure")
    @patch("identity.database_service.first_row")
    def test_foreign_missing_or_deleted_export_is_one_generic_not_found(
        self, first_row, execute_procedure
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()
        execute_procedure.return_value = [[], []]

        response = self.client.get(
            f"/app/capture/{CAPTURE_KEY}/export", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Capture not found.")
        execute_procedure.assert_called_once_with(
            "usp_ExportCaptureForOwner",
            [("@UserKey", USER_KEY), ("@CaptureKey", CAPTURE_KEY)],
        )


if __name__ == "__main__":
    unittest.main()
