import unittest
from unittest.mock import Mock

from services.capture_lifecycle_service import (
    CaptureLifecycleError,
    CaptureLifecycleService,
)


class CaptureLifecycleServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.voice_storage = Mock()
        self.voice_storage.exists.return_value = False
        self.photo_service = Mock()
        self.service = CaptureLifecycleService(
            database=self.db,
            voice_storage=self.voice_storage,
            photo_service=self.photo_service,
        )

    def test_text_capture_finishes_in_sql_without_storage_dispatch(self):
        self.db.first_row.return_value = {"outcome": "success"}

        result = self.service.delete_capture("owner-a", "capture-a", b"12345678")

        self.assertEqual(result["kind"], "text")
        self.voice_storage.delete.assert_not_called()
        self.photo_service.finish_capture_deletion.assert_not_called()

    def test_voice_capture_preserves_existing_blob_then_finalize_order(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "pending",
                "source_type": "voice",
                "source_key": "source-a",
                "blob_name": "voice/v1/ab/opaque.webm",
                "deletion_token": b"12345678",
            },
            {"outcome": "success"},
        ]

        result = self.service.delete_capture("owner-a", "capture-a", b"abcdefgh")

        self.voice_storage.delete.assert_called_once_with("voice/v1/ab/opaque.webm")
        self.assertEqual(
            self.db.first_row.call_args_list[-1].args[0],
            "usp_FinalizeVoiceCaptureDeletion",
        )
        self.assertEqual(result["kind"], "voice")

    def test_photo_capture_dispatches_both_blob_cleanup_to_photo_service(self):
        pending = {
            "outcome": "pending",
            "source_type": "photo",
            "source_key": "source-a",
            "original_blob_name": "photo/v1/ab/original.jpg",
            "derivative_blob_name": "photo/v1/ab/preview.jpg",
            "deletion_token": b"12345678",
        }
        self.db.first_row.return_value = pending
        self.photo_service.finish_capture_deletion.return_value = {"outcome": "success"}

        result = self.service.delete_capture("owner-a", "capture-a", b"abcdefgh")

        self.photo_service.finish_capture_deletion.assert_called_once_with(
            "owner-a", pending
        )
        self.assertEqual(result["kind"], "photo")

    def test_unknown_media_type_fails_without_touching_storage(self):
        self.db.first_row.return_value = {
            "outcome": "pending",
            "source_type": "video",
        }

        with self.assertRaisesRegex(CaptureLifecycleError, "changed"):
            self.service.delete_capture("owner-a", "capture-a", b"abcdefgh")

        self.voice_storage.delete.assert_not_called()
        self.photo_service.finish_capture_deletion.assert_not_called()


if __name__ == "__main__":
    unittest.main()
