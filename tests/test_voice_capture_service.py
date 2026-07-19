import io
import unittest
from unittest.mock import Mock

from services.database_service import DatabaseServiceError
from services.media_storage_service import MediaStorageError
from services.voice_capture_service import (
    MAX_VOICE_BYTES,
    MAX_VOICE_DURATION_SECONDS,
    VoiceCaptureError,
    VoiceCaptureService,
    validate_audio,
)


WEBM_HEADER = b"\x1aE\xdf\xa3" + (b"\x00" * 32)


class FakeUpload:
    filename = "member-name-must-not-be-used.webm"
    mimetype = "audio/webm"

    def __init__(self, payload=WEBM_HEADER):
        self.stream = io.BytesIO(payload)


class VoiceCaptureValidationTests(unittest.TestCase):
    def test_accepts_supported_webm_magic_and_en_us(self):
        validated = validate_audio(FakeUpload(), "1.25")

        self.assertEqual(validated.content_type, "audio/webm")
        self.assertEqual(validated.locale, "en-US")
        self.assertEqual(validated.duration_seconds, 1.25)
        self.assertEqual(validated.byte_length, len(WEBM_HEADER))

    def test_rejects_oversize_without_silent_truncation(self):
        upload = FakeUpload(WEBM_HEADER + b"x" * MAX_VOICE_BYTES)

        with self.assertRaisesRegex(VoiceCaptureError, "too-large"):
            validate_audio(upload, "1")

    def test_rejects_duration_over_three_minutes(self):
        with self.assertRaisesRegex(VoiceCaptureError, "too-long"):
            validate_audio(FakeUpload(), str(MAX_VOICE_DURATION_SECONDS + 0.01))

    def test_rejects_mime_and_magic_mismatch(self):
        upload = FakeUpload(b"not-a-media-container")

        with self.assertRaisesRegex(VoiceCaptureError, "unsupported"):
            validate_audio(upload, "1")


class VoiceCaptureOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.storage = Mock()
        self.storage.exists.return_value = False
        self.speech = Mock()
        self.service = VoiceCaptureService(
            database=self.db,
            storage=self.storage,
            speech=self.speech,
        )
        self.user_key = "owner-a"
        self.source_key = "11111111-1111-1111-1111-111111111111"

    def test_upload_transcribe_preserves_provider_text_for_review(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "created",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "row_version": b"\x00" * 7 + b"\x01",
            },
            {"outcome": "queued", "attempt_number": 1},
            {"outcome": "processing"},
            {"outcome": "needs_review", "source_key": self.source_key},
            {
                "source_key": self.source_key,
                "state": "needs_review",
                "provider_transcript": "Synthetic provider draft.",
            },
        ]
        self.speech.transcribe.return_value = {
            "provider_transcript": "Synthetic provider draft.",
            "provider_request_id": "request-opaque",
            "duration_seconds": 2.5,
        }

        result = self.service.create_and_transcribe(
            self.user_key, FakeUpload(), "2.4"
        )

        self.storage.upload.assert_called_once()
        self.speech.transcribe.assert_called_once()
        self.assertEqual(result["state"], "needs_review")
        completion = self.db.first_row.call_args_list[3]
        self.assertIn(("@ProviderTranscript", "Synthetic provider draft."), completion.args[1])

    def test_storage_failure_records_safe_code_without_payload(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "created",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "row_version": b"\x00" * 8,
            },
            {"outcome": "failed"},
        ]
        self.storage.upload.side_effect = RuntimeError("PRIVATE AUDIO SHOULD NOT LEAK")

        with self.assertRaisesRegex(VoiceCaptureError, "upload-failed") as raised:
            self.service.create_and_transcribe(self.user_key, FakeUpload(), "1")

        self.assertNotIn("PRIVATE AUDIO", str(raised.exception))
        self.assertEqual(raised.exception.source_key, self.source_key)
        failure_params = self.db.first_row.call_args_list[-1].args[1]
        self.assertIn(("@SafeErrorCode", "storage_unavailable"), failure_params)

    def test_database_failure_after_blob_upload_returns_recoverable_source(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "created",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "row_version": b"\x00" * 7 + b"\x01",
            },
            DatabaseServiceError("PRIVATE DATABASE DETAIL"),
        ]

        with self.assertRaisesRegex(VoiceCaptureError, "queue-failed") as raised:
            self.service.create_and_transcribe(self.user_key, FakeUpload(), "1")

        self.assertEqual(raised.exception.source_key, self.source_key)
        self.assertNotIn("PRIVATE", str(raised.exception))
        self.storage.upload.assert_called_once()
        self.speech.transcribe.assert_not_called()

    def test_changed_queue_outcome_after_blob_upload_returns_recoverable_source(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "created",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "row_version": b"\x00" * 7 + b"\x01",
            },
            {"outcome": "not_found_or_changed"},
        ]

        with self.assertRaisesRegex(VoiceCaptureError, "queue-failed") as raised:
            self.service.create_and_transcribe(self.user_key, FakeUpload(), "1")

        self.assertEqual(raised.exception.source_key, self.source_key)
        self.storage.upload.assert_called_once()
        self.speech.transcribe.assert_not_called()

    def test_retry_creates_new_attempt_and_never_overwrites_old_result(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "queued",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "content_type": "audio/webm",
                "attempt_number": 2,
            },
            {"outcome": "processing"},
            {"outcome": "needs_review"},
            {"source_key": self.source_key, "state": "needs_review"},
        ]
        self.storage.download.return_value = WEBM_HEADER
        self.speech.transcribe.return_value = {
            "provider_transcript": "Second immutable result.",
            "provider_request_id": "request-2",
            "duration_seconds": 1.0,
        }

        self.service.retry_transcription(
            self.user_key, self.source_key, "0000000000000001"
        )

        first_call = self.db.first_row.call_args_list[0]
        self.assertEqual(first_call.args[0], "usp_QueueVoiceTranscription")
        completion_params = self.db.first_row.call_args_list[2].args[1]
        self.assertIn(("@AttemptNumber", 2), completion_params)

    def test_retry_storage_failure_marks_attempt_failed_with_safe_code(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "queued",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "content_type": "audio/webm",
                "attempt_number": 2,
            },
            {"outcome": "failed"},
        ]
        self.storage.download.side_effect = MediaStorageError(
            "PRIVATE PROVIDER DETAIL"
        )

        with self.assertRaisesRegex(
            VoiceCaptureError, "transcription-failed"
        ) as raised:
            self.service.retry_transcription(
                self.user_key, self.source_key, "0000000000000001"
            )

        self.assertNotIn("PRIVATE", str(raised.exception))
        failure_call = self.db.first_row.call_args_list[1]
        self.assertEqual(failure_call.args[0], "usp_FailVoiceTranscription")
        self.assertIn(("@AttemptNumber", 2), failure_call.args[1])
        self.assertIn(("@SafeErrorCode", "storage_unavailable"), failure_call.args[1])

    def test_confirm_is_explicit_idempotent_and_member_body_is_separate(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "created",
                "capture_key": "22222222-2222-2222-2222-222222222222",
            },
            {
                "outcome": "existing",
                "capture_key": "22222222-2222-2222-2222-222222222222",
            },
        ]

        first = self.service.confirm_capture(
            self.user_key,
            self.source_key,
            "0000000000000001",
            "Member-corrected body.",
        )
        second = self.service.confirm_capture(
            self.user_key,
            self.source_key,
            "0000000000000001",
            "Member-corrected body.",
        )

        self.assertEqual(first["capture_key"], second["capture_key"])
        params = self.db.first_row.call_args_list[0].args[1]
        self.assertIn(("@ApprovedBody", "Member-corrected body."), params)
        self.assertNotIn("provider_transcript", dict(params))

    def test_delete_marks_pending_before_blob_then_finalizes(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "pending",
                "source_key": self.source_key,
                "blob_name": "voice/v1/ab/opaque.webm",
                "deletion_token": b"\x00" * 7 + b"\x02",
            },
            {"outcome": "success"},
        ]

        result = self.service.delete_draft(
            self.user_key, self.source_key, "0000000000000001"
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            self.db.first_row.call_args_list[0].args[0],
            "usp_BeginVoiceDraftDeletion",
        )
        self.storage.delete.assert_called_once_with("voice/v1/ab/opaque.webm")
        self.assertEqual(
            self.db.first_row.call_args_list[1].args[0],
            "usp_FinalizeVoiceDraftDeletion",
        )

    def test_blob_delete_failure_remains_retryable_and_does_not_finalize(self):
        self.db.first_row.return_value = {
            "outcome": "pending",
            "source_key": self.source_key,
            "blob_name": "voice/v1/ab/opaque.webm",
            "deletion_token": b"\x00" * 8,
        }
        self.storage.delete.side_effect = RuntimeError("provider payload")

        with self.assertRaisesRegex(VoiceCaptureError, "delete-retry"):
            self.service.delete_draft(
                self.user_key, self.source_key, "0000000000000001"
            )

        self.assertEqual(self.db.first_row.call_count, 1)


if __name__ == "__main__":
    unittest.main()
