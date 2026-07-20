import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from app import app
from identity import AuthenticationRequired, PeerSlateIdentity
from services.database_service import DatabaseServiceError
from services.photo_capture_service import PhotoCaptureError


IDENTITY = PeerSlateIdentity(
    user_key="owner-a",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-a",
    display_name="Owner A",
    email="owner-a@example.test",
)
IDENTITY_B = PeerSlateIdentity(
    user_key="owner-b",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-b",
    display_name="Owner B",
    email="owner-b@example.test",
)
IDENTITY_C = PeerSlateIdentity(
    user_key="owner-c",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-c",
    display_name="Owner C",
    email="owner-a@example.test",
)
SOURCE_KEY = "11111111-1111-1111-1111-111111111111"
CAPTURE_KEY = "22222222-2222-2222-2222-222222222222"
PROOF_CONFIG_NAMES = (
    "CAPTURE_PHOTO_ENABLED",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID",
)


def source(state="scanning"):
    return {
        "source_key": SOURCE_KEY,
        "state": state,
        "scan_result": "clean" if state in {"needs_review", "confirmed"} else "unknown",
        "safe_error_code": None,
        "original_content_type": "image/jpeg",
        "original_byte_length": 100,
        "derivative_content_type": "image/jpeg" if state in {"needs_review", "confirmed"} else None,
        "derivative_byte_length": 80 if state in {"needs_review", "confirmed"} else None,
        "pixel_width": 20 if state in {"needs_review", "confirmed"} else None,
        "pixel_height": 10 if state in {"needs_review", "confirmed"} else None,
        "row_version_token": "0101010101010101",
    }


class OwnerPhotoCaptureRouteTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            name: (name in app.config, app.config.get(name))
            for name in PROOF_CONFIG_NAMES
        }
        app.config.update(
            TESTING=True,
            CAPTURE_PHOTO_ENABLED=True,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS="",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC="",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID="",
        )
        self.client = app.test_client()
        self.identity_patch = patch(
            "owner_routes.get_current_identity", return_value=IDENTITY
        )
        self.identity = self.identity_patch.start()

    def tearDown(self):
        patch.stopall()
        for name, (existed, value) in self.original_config.items():
            if existed:
                app.config[name] = value
            else:
                app.config.pop(name, None)

    @staticmethod
    def same_origin_headers():
        return {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

    @staticmethod
    def enable_dark_launch():
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        app.config.update(
            CAPTURE_PHOTO_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=True,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS="owner-a,owner-b",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC=expiry.isoformat().replace(
                "+00:00", "Z"
            ),
            CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID=(
                "PS-CAPTURE-PHOTO-LIFECYCLE-001-test"
            ),
        )

    def test_photo_route_inventory_matches_the_server_gate(self):
        expected = {
            ("/app/capture/photo", "POST"),
            ("/app/capture/photo/<source_key>", "GET"),
            ("/app/capture/photo/<source_key>/reconcile", "POST"),
            ("/app/capture/photo/<source_key>/confirm", "POST"),
            ("/app/capture/photo/<source_key>/delete", "POST"),
            ("/app/capture/photo/<source_key>/preview", "GET"),
            ("/app/capture/photo/<source_key>/original", "GET"),
        }
        actual = {
            (rule.rule, method)
            for rule in app.url_map.iter_rules()
            if rule.rule.startswith("/app/capture/photo")
            for method in rule.methods
            if method in {"GET", "POST"}
        }

        self.assertEqual(actual, expected)

    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_dark_launch_page_admits_only_the_two_resolved_owners(
        self, _list_captures
    ):
        self.enable_dark_launch()

        for identity, expected in ((IDENTITY, True), (IDENTITY_B, True), (IDENTITY_C, False)):
            with self.subTest(user_key=identity.user_key):
                self.identity.return_value = identity
                response = self.client.get("/app/capture")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    b'data-capture-mode="photo"' in response.data,
                    expected,
                )

    @patch("owner_routes.photo_capture_service.get_source")
    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_noncohort_photo_query_is_neutral_before_photo_lookup(
        self, _list_captures, get_source
    ):
        self.enable_dark_launch()
        self.identity.return_value = IDENTITY_C

        response = self.client.get(f"/app/capture?photo={SOURCE_KEY}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Photo Capture is unavailable.")
        get_source.assert_not_called()

    @patch("owner_routes.photo_capture_service.create_source")
    def test_noncohort_cannot_forge_a_cohort_identity(self, create_source):
        self.enable_dark_launch()
        self.identity.return_value = IDENTITY_C

        response = self.client.post(
            "/app/capture/photo",
            data={
                "user_key": "owner-a",
                "email": "owner-a@example.test",
                "photo": (io.BytesIO(b"synthetic"), "private.jpg"),
            },
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Photo Capture is unavailable.")
        create_source.assert_not_called()

    def test_signed_out_dark_launch_request_is_neutral_not_a_sign_in_redirect(self):
        self.enable_dark_launch()
        self.identity.side_effect = AuthenticationRequired("Sign in is required.")

        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Location", response.headers)
        self.assertEqual(response.get_data(as_text=True), "Photo Capture is unavailable.")

    def test_identity_storage_failure_during_dark_launch_is_neutral(self):
        self.enable_dark_launch()
        self.identity.side_effect = DatabaseServiceError("unavailable")

        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Photo Capture is unavailable.")

    def test_signed_out_ordinary_release_keeps_existing_sign_in_redirect(self):
        self.identity.side_effect = AuthenticationRequired("Sign in is required.")

        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/sign-in", response.headers["Location"])

    def test_signed_out_ordinary_cross_site_write_keeps_existing_denial_order(self):
        self.identity.side_effect = AuthenticationRequired("Sign in is required.")

        response = self.client.post(
            "/app/capture/photo",
            headers={"Origin": "https://cross-site.example"},
        )

        self.assertEqual(response.status_code, 403)
        self.identity.assert_not_called()

    def test_signed_out_ordinary_invalid_source_keeps_existing_denial_order(self):
        self.identity.side_effect = AuthenticationRequired("Sign in is required.")

        response = self.client.get("/app/capture/photo/not-a-source-key")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Photo source not found.")
        self.identity.assert_not_called()

    @patch("owner_routes.photo_capture_service.create_source")
    def test_conflicting_flags_fail_closed_before_identity_or_service(self, create_source):
        self.enable_dark_launch()
        app.config["CAPTURE_PHOTO_ENABLED"] = True

        response = self.client.post(
            "/app/capture/photo", headers=self.same_origin_headers()
        )

        self.assertEqual(response.status_code, 404)
        self.identity.assert_not_called()
        create_source.assert_not_called()

    @patch("owner_routes.photo_capture_service.create_source")
    @patch("owner_routes.photo_capture_service.get_source")
    @patch("owner_routes.photo_capture_service.reconcile_and_process")
    @patch("owner_routes.photo_capture_service.confirm_capture")
    @patch("owner_routes.photo_capture_service.delete_draft")
    @patch("owner_routes.photo_capture_service.open_media")
    def test_noncohort_denial_matches_flag_off_for_every_direct_photo_route(
        self,
        open_media,
        delete_draft,
        confirm_capture,
        reconcile,
        get_source,
        create_source,
    ):
        routes = (
            ("post", "/app/capture/photo", {}),
            ("get", f"/app/capture/photo/{SOURCE_KEY}", {}),
            ("post", f"/app/capture/photo/{SOURCE_KEY}/reconcile", {}),
            ("post", f"/app/capture/photo/{SOURCE_KEY}/confirm", {}),
            ("post", f"/app/capture/photo/{SOURCE_KEY}/delete", {}),
            ("get", f"/app/capture/photo/{SOURCE_KEY}/preview", {}),
            ("get", f"/app/capture/photo/{SOURCE_KEY}/original", {}),
        )

        for method, path, data in routes:
            with self.subTest(method=method, path=path):
                app.config.update(
                    CAPTURE_PHOTO_ENABLED=False,
                    CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=False,
                )
                baseline = getattr(self.client, method)(
                    path, data=data, headers=self.same_origin_headers()
                )
                self.enable_dark_launch()
                self.identity.return_value = IDENTITY_C
                denied = getattr(self.client, method)(
                    path, data=data, headers=self.same_origin_headers()
                )
                self.assertEqual(denied.status_code, baseline.status_code)
                self.assertEqual(denied.data, baseline.data)

        for service_method in (
            open_media,
            delete_draft,
            confirm_capture,
            reconcile,
            get_source,
            create_source,
        ):
            service_method.assert_not_called()

    @patch("owner_routes.photo_capture_service.create_source")
    @patch("owner_routes.photo_capture_service.get_source", return_value=None)
    @patch("owner_routes.photo_capture_service.reconcile_and_process")
    @patch("owner_routes.photo_capture_service.confirm_capture")
    @patch("owner_routes.photo_capture_service.delete_draft")
    @patch("owner_routes.photo_capture_service.open_media", return_value=None)
    def test_second_cohort_owner_is_used_at_every_protected_photo_service_boundary(
        self,
        open_media,
        delete_draft,
        confirm_capture,
        reconcile,
        get_source,
        create_source,
    ):
        self.enable_dark_launch()
        self.identity.return_value = IDENTITY_B
        create_source.return_value = source("scanning")
        reconcile.side_effect = PhotoCaptureError("changed")
        confirm_capture.side_effect = PhotoCaptureError("changed")
        delete_draft.side_effect = PhotoCaptureError("changed")

        upload = self.client.post(
            "/app/capture/photo",
            data={"photo": (io.BytesIO(b"synthetic"), "private.jpg")},
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )
        status = self.client.get(f"/app/capture/photo/{SOURCE_KEY}")
        reconciliation = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/reconcile",
            data={"expected_row_version": "0101010101010101"},
            headers=self.same_origin_headers(),
        )
        confirmation = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/confirm",
            data={
                "approved_body": "Synthetic proof",
                "expected_row_version": "0101010101010101",
                "confirm_photo": "save-private-capture",
            },
            headers=self.same_origin_headers(),
        )
        deletion = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/delete",
            data={
                "confirm_delete": "delete",
                "expected_row_version": "0101010101010101",
            },
            headers=self.same_origin_headers(),
        )
        preview = self.client.get(f"/app/capture/photo/{SOURCE_KEY}/preview")
        original = self.client.get(f"/app/capture/photo/{SOURCE_KEY}/original")

        self.assertEqual(upload.status_code, 201)
        self.assertEqual(status.status_code, 404)
        self.assertEqual(reconciliation.status_code, 409)
        self.assertEqual(confirmation.status_code, 409)
        self.assertEqual(deletion.status_code, 409)
        self.assertEqual(preview.status_code, 404)
        self.assertEqual(original.status_code, 404)
        self.assertEqual(create_source.call_args.args[0], "owner-b")
        get_source.assert_called_once_with("owner-b", SOURCE_KEY)
        self.assertEqual(reconcile.call_args.args[0], "owner-b")
        self.assertEqual(confirm_capture.call_args.args[0], "owner-b")
        self.assertEqual(delete_draft.call_args.args[0], "owner-b")
        self.assertEqual(
            [call.args for call in open_media.call_args_list],
            [
                ("owner-b", SOURCE_KEY, "preview"),
                ("owner-b", SOURCE_KEY, "original"),
            ],
        )

    @patch("owner_routes.photo_capture_service.create_source")
    def test_feature_flag_is_fail_closed_before_service_call(self, create):
        app.config["CAPTURE_PHOTO_ENABLED"] = False

        response = self.client.post(
            "/app/capture/photo",
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 404)
        create.assert_not_called()

    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_capture_page_hides_photo_experience_when_flag_is_off(self, _list_captures):
        app.config["CAPTURE_PHOTO_ENABLED"] = False

        response = self.client.get("/app/capture")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'data-capture-mode="photo"', response.data)
        self.assertNotIn(b"owner-capture-photo.js", response.data)

    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_capture_page_exposes_accessible_photo_entry_when_flag_is_on(self, _list_captures):
        response = self.client.get("/app/capture")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-capture-mode="photo"', response.data)
        self.assertIn(b"Add a photo worth remembering", response.data)
        self.assertIn(b'id="photo-file-choice" type="file"', response.data)
        self.assertIn(b'accept="image/jpeg,image/png"', response.data)
        self.assertIn(b'capture="environment"', response.data)
        self.assertIn(b"Selected photo, not saved yet", response.data)
        self.assertIn(b"Save private Capture", response.data)
        self.assertIn(b"Nothing is shared or published", response.data)
        self.assertIn(b"owner-capture-photo.js", response.data)

    @patch("owner_routes.photo_capture_service.get_source")
    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_capture_page_hydrates_owner_scoped_photo_review(
        self, _list_captures, get_source
    ):
        get_source.return_value = source("needs_review")

        response = self.client.get(f"/app/capture?photo={SOURCE_KEY}")

        self.assertEqual(response.status_code, 200)
        get_source.assert_called_once_with("owner-a", SOURCE_KEY)
        self.assertIn(f'data-source-key="{SOURCE_KEY}"'.encode(), response.data)
        self.assertIn(b'data-source-state="needs_review"', response.data)
        self.assertIn(f"/app/capture/photo/{SOURCE_KEY}/preview".encode(), response.data)
        self.assertIn(b"Private photo awaiting your description", response.data)
        self.assertNotIn(b"blob.core.windows.net", response.data)

    @patch("owner_routes.photo_capture_service.get_source", return_value=None)
    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_capture_page_uses_neutral_not_found_for_other_owner_photo(
        self, _list_captures, _get_source
    ):
        response = self.client.get(f"/app/capture?photo={SOURCE_KEY}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Photo source not found.")

    @patch("owner_routes.database_service.first_result", return_value=[])
    def test_capture_page_rejects_two_private_drafts_at_once(self, _list_captures):
        response = self.client.get(
            f"/app/capture?voice={CAPTURE_KEY}&photo={SOURCE_KEY}"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Open one private Capture draft at a time", response.data)

    def test_photo_client_contract_has_private_state_and_accessibility_controls(self):
        root = Path(__file__).parents[1]
        script = (root / "static" / "js" / "owner-capture-photo.js").read_text(
            encoding="utf-8"
        )
        template = (root / "templates" / "owner_capture.html").read_text(
            encoding="utf-8"
        )

        for required in (
            "Selected photo, not saved yet",
            "Safe preview",
            "Embedded metadata removed",
            "Save private Capture",
        ):
            self.assertIn(required, template)
        for required in (
            "Upload cancelled in this browser",
            r"Scanning\u2026 Nothing is shared or published.",
            "save-private-capture",
            "confirm_delete",
            "aria-modal",
            "Escape",
            "URL.revokeObjectURL",
        ):
            self.assertIn(required, script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)
        self.assertNotIn("file.name", script)

    @patch("owner_routes.photo_capture_service.create_source")
    def test_upload_is_same_origin_owner_scoped_and_returns_no_storage_locator(self, create):
        create.return_value = source("scanning")

        response = self.client.post(
            "/app/capture/photo",
            data={"photo": (io.BytesIO(b"synthetic"), "private-name.jpg")},
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["state"], "scanning")
        self.assertEqual(create.call_args.args[0], "owner-a")
        serialized = json.dumps(response.get_json()).lower()
        self.assertNotIn("blob_name", serialized)
        self.assertNotIn("blob.core.windows.net", serialized)
        self.assertNotIn("private-name", serialized)

    @patch("owner_routes.photo_capture_service.create_source")
    def test_cross_site_upload_is_denied_before_service_call(self, create):
        response = self.client.post(
            "/app/capture/photo",
            data={"photo": (io.BytesIO(b"synthetic"), "private.jpg")},
            headers={"Origin": "https://attacker.example"},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    @patch("owner_routes.photo_capture_service.create_source")
    def test_upload_preserves_recovery_key_after_storage_uncertainty(self, create):
        create.side_effect = PhotoCaptureError("upload-recovery", SOURCE_KEY)

        response = self.client.post(
            "/app/capture/photo",
            data={"photo": (io.BytesIO(b"synthetic"), "private.jpg")},
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["source_key"], SOURCE_KEY)
        self.assertIn(SOURCE_KEY, response.get_json()["status_url"])
        self.assertNotIn("provider", json.dumps(response.get_json()).lower())

    @patch("owner_routes.photo_capture_service.get_source", return_value=None)
    def test_guessed_cross_owner_status_is_neutral_not_found(self, get_source):
        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}")

        self.assertEqual(response.status_code, 404)
        get_source.assert_called_once_with("owner-a", SOURCE_KEY)

    @patch("owner_routes.photo_capture_service.get_source")
    def test_status_is_private_no_store_and_contains_no_storage_locator(self, get_source):
        get_source.return_value = source("needs_review")

        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        payload = response.get_json()
        self.assertIn("preview_url", payload)
        self.assertNotIn("blob_name", json.dumps(payload))

    @patch("owner_routes.photo_capture_service.reconcile_and_process")
    def test_reconcile_uses_owner_and_row_version(self, reconcile):
        reconcile.return_value = source("needs_review")

        response = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/reconcile",
            data={"expected_row_version": "0101010101010101"},
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        reconcile.assert_called_once_with(
            "owner-a", SOURCE_KEY, "0101010101010101"
        )

    @patch("owner_routes.photo_capture_service.confirm_capture")
    def test_confirm_requires_explicit_save_private_action(self, confirm):
        response = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/confirm",
            data={
                "approved_body": "What this photo means.",
                "expected_row_version": "0101010101010101",
            },
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 400)
        confirm.assert_not_called()

    @patch("owner_routes.photo_capture_service.confirm_capture")
    def test_confirm_creates_private_capture_only_after_explicit_action(self, confirm):
        confirm.return_value = {"outcome": "created", "capture_key": CAPTURE_KEY}

        response = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/confirm",
            data={
                "approved_body": "What this photo means.",
                "expected_row_version": "0101010101010101",
                "confirm_photo": "save-private-capture",
            },
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["capture_key"], CAPTURE_KEY)
        confirm.assert_called_once_with(
            "owner-a", SOURCE_KEY, "0101010101010101", "What this photo means."
        )

    @patch("owner_routes.photo_capture_service.open_media")
    def test_preview_is_private_no_store_and_server_named(self, open_media):
        open_media.return_value = {
            "stream": io.BytesIO(b"synthetic-preview"),
            "content_type": "image/jpeg",
            "byte_length": 17,
        }

        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}/preview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("peerslate-private-photo-preview.jpg", response.headers["Content-Disposition"])
        self.assertNotIn("blob.core.windows.net", response.get_data(as_text=True))
        response.close()

    @patch("owner_routes.photo_capture_service.open_media")
    def test_original_is_always_an_attachment_even_without_query_flag(self, open_media):
        open_media.return_value = {
            "stream": io.BytesIO(b"synthetic-original"),
            "content_type": "image/jpeg",
            "byte_length": 18,
        }

        response = self.client.get(f"/app/capture/photo/{SOURCE_KEY}/original")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn("peerslate-private-photo-original.jpg", response.headers["Content-Disposition"])
        response.close()

    @patch("owner_routes.photo_capture_service.delete_draft")
    def test_draft_delete_requires_confirmation_and_same_origin(self, delete):
        response = self.client.post(
            f"/app/capture/photo/{SOURCE_KEY}/delete",
            data={
                "confirm_delete": "delete",
                "expected_row_version": "0101010101010101",
            },
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        delete.assert_called_once_with(
            "owner-a", SOURCE_KEY, "0101010101010101"
        )

    @patch("owner_routes.database_service.execute_procedure")
    def test_photo_export_is_schema_v3_and_never_exposes_blob_locator(self, execute):
        execute.return_value = [
            [
                {
                    "capture_key": CAPTURE_KEY,
                    "capture_type": "photo",
                    "body": "Current note.",
                    "original_body": "Original note.",
                    "visibility": "private",
                    "status": "captured",
                    "active": True,
                    "revision_number": 0,
                    "created_at_utc": "2026-07-19T12:00:00",
                    "updated_at_utc": "2026-07-19T12:00:00",
                    "revisions_json": "[]",
                }
            ],
            [
                {
                    "source_type": "photo",
                    "source_key": SOURCE_KEY,
                    "original_content_type": "image/jpeg",
                    "original_byte_length": 100,
                    "derivative_content_type": "image/jpeg",
                    "derivative_byte_length": 80,
                    "pixel_width": 20,
                    "pixel_height": 10,
                    "scan_result": "clean",
                    "scan_completed_at_utc": "2026-07-19T12:00:00",
                }
            ],
        ]

        response = self.client.get(f"/app/capture/{CAPTURE_KEY}/export")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["schema_version"], 3)
        self.assertTrue(
            payload["capture"]["photo_source"]["embedded_metadata_removed_from_preview"]
        )
        serialized = json.dumps(payload).lower()
        self.assertNotIn("blob_name", serialized)
        self.assertNotIn("blob.core.windows.net", serialized)
        self.assertNotIn("sha256", serialized)


if __name__ == "__main__":
    unittest.main()
