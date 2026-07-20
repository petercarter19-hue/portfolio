import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from app import app
from identity import PeerSlateIdentity
from services.photo_capture_service import PhotoCaptureError


IDENTITY = PeerSlateIdentity(
    user_key="owner-a",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-a",
    display_name="Owner A",
    email="owner-a@example.test",
)
SOURCE_KEY = "11111111-1111-1111-1111-111111111111"
CAPTURE_KEY = "22222222-2222-2222-2222-222222222222"


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
        app.config.update(TESTING=True, CAPTURE_PHOTO_ENABLED=True)
        self.client = app.test_client()
        self.identity = patch("owner_routes.get_current_identity", return_value=IDENTITY)
        self.identity.start()

    def tearDown(self):
        app.config["CAPTURE_PHOTO_ENABLED"] = False
        patch.stopall()

    @staticmethod
    def same_origin_headers():
        return {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

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
