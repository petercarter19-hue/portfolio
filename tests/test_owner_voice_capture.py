import io
import unittest
from unittest.mock import patch

from app import app
from identity import PeerSlateIdentity
from services.voice_capture_service import VoiceCaptureError


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


class OwnerVoiceCaptureRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.identity = patch("owner_routes.get_current_identity", return_value=IDENTITY)
        self.identity.start()

    def tearDown(self):
        patch.stopall()

    @staticmethod
    def same_origin_headers():
        return {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

    @patch("owner_routes.voice_capture_service.create_and_transcribe")
    def test_upload_is_owner_scoped_same_origin_and_returns_review_location(self, create):
        create.return_value = {"source_key": SOURCE_KEY, "state": "needs_review"}

        response = self.client.post(
            "/app/capture/voice",
            data={
                "audio": (io.BytesIO(b"\x1aE\xdf\xa3data"), "ignored.webm"),
                "duration_seconds": "1.2",
            },
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["state"], "needs_review")
        self.assertIn(f"voice={SOURCE_KEY}", response.get_json()["review_url"])
        self.assertEqual(create.call_args.args[0], "owner-a")

    @patch("owner_routes.voice_capture_service.create_and_transcribe")
    def test_cross_site_upload_is_denied_before_service_call(self, create):
        response = self.client.post(
            "/app/capture/voice",
            data={"audio": (io.BytesIO(b"x"), "ignored.webm")},
            headers={"Origin": "https://attacker.example"},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    @patch("owner_routes.voice_capture_service.create_and_transcribe")
    def test_recoverable_provider_failure_returns_private_review_location(self, create):
        create.side_effect = VoiceCaptureError("transcription-failed", SOURCE_KEY)

        response = self.client.post(
            "/app/capture/voice",
            data={
                "audio": (io.BytesIO(b"\x1aE\xdf\xa3data"), "ignored.webm"),
                "duration_seconds": "1.2",
            },
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn(f"voice={SOURCE_KEY}", response.get_json()["review_url"])

    @patch("owner_routes.voice_capture_service.create_and_transcribe")
    def test_queue_failure_after_upload_returns_recoverable_review_location(self, create):
        create.side_effect = VoiceCaptureError("queue-failed", SOURCE_KEY)

        response = self.client.post(
            "/app/capture/voice",
            data={
                "audio": (io.BytesIO(b"\x1aE\xdf\xa3data"), "ignored.webm"),
                "duration_seconds": "1.2",
            },
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "queue-failed")
        self.assertEqual(response.get_json()["source_key"], SOURCE_KEY)
        self.assertNotIn("state", response.get_json())
        self.assertIn(f"voice={SOURCE_KEY}", response.get_json()["review_url"])

    @patch("owner_routes.voice_capture_service.create_and_transcribe")
    def test_post_upload_database_uncertainty_returns_stable_recovery_location(self, create):
        create.side_effect = VoiceCaptureError("transcription-recovery", SOURCE_KEY)

        response = self.client.post(
            "/app/capture/voice",
            data={
                "audio": (io.BytesIO(b"\x1aE\xdf\xa3data"), "ignored.webm"),
                "duration_seconds": "1.2",
            },
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(payload["error"], "transcription-recovery")
        self.assertEqual(payload["source_key"], SOURCE_KEY)
        self.assertIn(f"voice={SOURCE_KEY}", payload["review_url"])
        self.assertNotIn("state", payload)
        self.assertNotIn("provider", str(payload).lower())
        self.assertNotIn("database", str(payload).lower())

    @patch("owner_routes.voice_capture_service.get_draft")
    def test_uploaded_but_unqueued_review_page_offers_retry_and_delete(self, get_draft):
        get_draft.return_value = {
            "source_key": SOURCE_KEY,
            "state": "uploading",
            "row_version_token": "0000000000000001",
        }

        with patch("owner_routes.database_service.first_result", return_value=[]):
            response = self.client.get(f"/app/capture?voice={SOURCE_KEY}")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("transcription has not started", page)
        self.assertIn("Retry transcription", page)
        self.assertIn("Delete private voice draft", page)
        self.assertNotIn("PRIVATE DATABASE DETAIL", page)

    def _render_voice_draft(self, state, attempt_number=None):
        draft = {
            "source_key": SOURCE_KEY,
            "state": state,
            "attempt_number": attempt_number,
            "row_version_token": "0000000000000001",
        }
        with patch(
            "owner_routes.voice_capture_service.get_draft",
            return_value=draft,
        ), patch("owner_routes.database_service.first_result", return_value=[]):
            return self.client.get(f"/app/capture?voice={SOURCE_KEY}")

    def test_failed_draft_with_attempt_offers_retry_and_delete(self):
        response = self._render_voice_draft("failed", attempt_number=2)

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Retry transcription", page)
        self.assertIn("Delete private voice draft", page)
        self.assertNotIn("cannot be retried", page)

    def test_failed_upload_without_attempt_offers_rerecord_type_and_delete_only(self):
        response = self._render_voice_draft("failed", attempt_number=None)

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertNotIn("Retry transcription", page)
        self.assertIn("cannot be retried", page)
        self.assertIn("Record again", page)
        self.assertIn("Switch to Type", page)
        self.assertIn("Delete private voice draft", page)

    def test_stranded_queued_and_processing_drafts_offer_retry_and_delete(self):
        for state in ("queued", "processing"):
            with self.subTest(state=state):
                response = self._render_voice_draft(state, attempt_number=1)
                self.assertEqual(response.status_code, 200)
                page = response.get_data(as_text=True)
                self.assertIn("Retry transcription", page)
                self.assertIn("Delete private voice draft", page)
                self.assertIn("No Capture or downstream item was created", page)
                self.assertNotIn("Saved private Capture", page)

    @patch("owner_routes.voice_capture_service.create_and_transcribe")
    def test_voice_route_can_receive_more_than_global_two_megabyte_limit(self, create):
        create.return_value = {"source_key": SOURCE_KEY, "state": "needs_review"}

        response = self.client.post(
            "/app/capture/voice",
            data={
                "audio": (io.BytesIO(b"\x1aE\xdf\xa3" + b"x" * (3 * 1024 * 1024)), "ignored.webm"),
                "duration_seconds": "2",
            },
            headers=self.same_origin_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        create.assert_called_once()

    @patch("owner_routes.voice_capture_service.get_draft", return_value=None)
    def test_guessed_cross_owner_review_is_neutral_not_found(self, get_draft):
        with patch("owner_routes.database_service.first_result", return_value=[]):
            response = self.client.get(f"/app/capture?voice={SOURCE_KEY}")

        self.assertEqual(response.status_code, 404)
        get_draft.assert_called_once_with("owner-a", SOURCE_KEY)

    @patch("owner_routes.voice_capture_service.open_audio", return_value=None)
    def test_guessed_cross_owner_audio_is_neutral_not_found(self, open_audio):
        response = self.client.get(f"/app/capture/voice/{SOURCE_KEY}/audio")

        self.assertEqual(response.status_code, 404)

    @patch("owner_routes.voice_capture_service.open_audio")
    def test_playback_is_private_no_store_and_never_exposes_blob_url(self, open_audio):
        open_audio.return_value = {
            "stream": io.BytesIO(b"synthetic"),
            "content_type": "audio/webm",
            "byte_length": 9,
        }

        response = self.client.get(f"/app/capture/voice/{SOURCE_KEY}/audio")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("inline", response.headers["Content-Disposition"])
        self.assertNotIn("blob.core.windows.net", response.get_data(as_text=True))

    @patch("owner_routes.voice_capture_service.confirm_capture")
    def test_save_private_capture_requires_meaningful_reviewed_text(self, confirm):
        response = self.client.post(
            f"/app/capture/voice/{SOURCE_KEY}/confirm",
            data={
                "expected_row_version": "0000000000000001",
                "approved_body": "   ",
            },
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("error=required", response.location)
        confirm.assert_not_called()

    @patch("owner_routes.voice_capture_service.confirm_capture")
    def test_save_private_capture_is_explicit_owner_scoped(self, confirm):
        confirm.return_value = {"outcome": "created", "capture_key": CAPTURE_KEY}

        response = self.client.post(
            f"/app/capture/voice/{SOURCE_KEY}/confirm",
            data={
                "expected_row_version": "0000000000000001",
                "approved_body": "Member approved transcript.",
                "confirm_voice": "save-private-capture",
            },
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("saved=1", response.location)
        self.assertEqual(confirm.call_args.args[0], "owner-a")

    @patch("owner_routes.voice_capture_service.retry_transcription")
    def test_retry_maps_stale_or_cross_owner_to_neutral_changed_state(self, retry):
        retry.side_effect = VoiceCaptureError("changed")

        response = self.client.post(
            f"/app/capture/voice/{SOURCE_KEY}/retry",
            data={"expected_row_version": "0000000000000001"},
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("error=voice-changed", response.location)

    @patch("owner_routes.voice_capture_service.delete_capture")
    def test_voice_capture_delete_uses_distributed_service(self, delete):
        delete.return_value = {"outcome": "success", "kind": "voice"}

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/delete",
            data={
                "expected_row_version": "0000000000000001",
                "confirm_delete": "delete",
            },
            headers=self.same_origin_headers(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("changed=deleted", response.location)
        delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
