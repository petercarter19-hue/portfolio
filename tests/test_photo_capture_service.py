import io
import unittest
from unittest.mock import Mock

from PIL import Image

from services.capture_media_storage_service import CaptureMediaStorageError
from services.photo_capture_service import (
    PhotoCaptureError,
    PhotoCaptureService,
    normalize_photo,
    validate_photo_upload,
)


SOURCE_KEY = "11111111-1111-1111-1111-111111111111"
ORIGINAL = "photo/v1/ab/ab0123456789abcdef0123456789abcd.jpg"
PREVIEW = "photo/v1/ab/ab0123456789abcdef0123456789abcd-preview.jpg"


def image_bytes(image_format="JPEG", size=(32, 24), exif=None):
    payload = io.BytesIO()
    image = Image.new("RGB", size, (25, 50, 75))
    kwargs = {"format": image_format}
    if exif is not None:
        kwargs["exif"] = exif
    image.save(payload, **kwargs)
    return payload.getvalue()


class FakeUpload:
    filename = "member-filename-must-not-be-used.jpg"

    def __init__(self, payload=None, mimetype="image/jpeg"):
        self.mimetype = mimetype
        self.stream = io.BytesIO(payload or image_bytes())


class PhotoValidationTests(unittest.TestCase):
    def test_accepts_complete_jpeg_and_png_without_using_filename(self):
        jpeg = validate_photo_upload(FakeUpload())
        png = validate_photo_upload(
            FakeUpload(image_bytes("PNG"), "image/png")
        )

        self.assertEqual(jpeg.extension, "jpg")
        self.assertEqual(png.extension, "png")
        self.assertEqual(jpeg.content_type, "image/jpeg")

    def test_rejects_mime_magic_mismatch_and_trailing_container_data(self):
        cases = (
            FakeUpload(image_bytes("PNG"), "image/jpeg"),
            FakeUpload(image_bytes("JPEG") + b"trailing", "image/jpeg"),
            FakeUpload(b"not-an-image", "image/png"),
        )
        for upload in cases:
            with self.subTest(mimetype=upload.mimetype), self.assertRaisesRegex(
                PhotoCaptureError, "unsupported"
            ):
                validate_photo_upload(upload)

    def test_normalization_applies_orientation_and_removes_exif(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = "PRIVATE MEMBER DESCRIPTION"
        original = image_bytes(size=(40, 20), exif=exif)

        normalized = normalize_photo(original, "image/jpeg")

        with Image.open(io.BytesIO(normalized.data)) as result:
            self.assertEqual(result.size, (20, 40))
            self.assertEqual(len(result.getexif()), 0)
            self.assertNotIn(b"PRIVATE MEMBER DESCRIPTION", normalized.data)


class PhotoOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.storage = Mock()
        self.storage.exists.return_value = False
        self.service = PhotoCaptureService(database=self.db, storage=self.storage)
        self.user_key = "owner-a"

    def test_create_uploads_private_original_then_enters_scanning(self):
        self.db.first_row.side_effect = [
            {"outcome": "created", "source_key": SOURCE_KEY, "row_version": b"\x01" * 8},
            {"outcome": "scanning", "row_version": b"\x02" * 8},
            {
                "source_key": SOURCE_KEY,
                "state": "scanning",
                "row_version": b"\x02" * 8,
            },
        ]
        self.storage.upload.return_value = {"etag": '"opaque-etag"'}

        result = self.service.create_source(self.user_key, FakeUpload())

        self.assertEqual(result["state"], "scanning")
        upload_name = self.storage.upload.call_args.args[0]
        self.assertRegex(upload_name, r"^photo/v1/[0-9a-f]{2}/[0-9a-f]{32}\.jpg$")
        self.assertNotIn("member-filename", upload_name)
        mark_params = self.db.first_row.call_args_list[1].args[1]
        self.assertIn(("@OriginalBlobEtag", '"opaque-etag"'), mark_params)

    def test_draft_limit_stops_before_blob_upload(self):
        self.db.first_row.return_value = {
            "outcome": "draft_limit",
            "source_key": None,
            "row_version": None,
        }

        with self.assertRaisesRegex(PhotoCaptureError, "draft-limit"):
            self.service.create_source(self.user_key, FakeUpload())

        self.storage.upload.assert_not_called()

    def test_storage_failure_records_only_safe_code(self):
        self.db.first_row.side_effect = [
            {"outcome": "created", "source_key": SOURCE_KEY, "row_version": b"\x01" * 8},
            {"outcome": "failed"},
        ]
        self.storage.upload.side_effect = RuntimeError("PRIVATE PROVIDER PAYLOAD")

        with self.assertRaisesRegex(PhotoCaptureError, "upload-failed") as raised:
            self.service.create_source(self.user_key, FakeUpload())

        self.assertNotIn("PRIVATE", str(raised.exception))
        failure_params = self.db.first_row.call_args_list[-1].args[1]
        self.assertIn(("@SafeErrorCode", "storage_unavailable"), failure_params)

    def test_clean_scan_precedes_download_decode_and_derivative_upload(self):
        original = image_bytes()
        digest = __import__("hashlib").sha256(original).digest()
        self.db.first_row.side_effect = [
            {
                "source_key": SOURCE_KEY,
                "state": "scanning",
                "original_blob_name": ORIGINAL,
                "derivative_blob_name": PREVIEW,
                "original_content_type": "image/jpeg",
                "original_byte_length": len(original),
                "original_sha256_digest": digest,
                "original_blob_etag": '"original-etag"',
                "row_version": b"\x01" * 8,
            },
            {
                "outcome": "processing",
                "original_blob_name": ORIGINAL,
                "derivative_blob_name": PREVIEW,
                "original_content_type": "image/jpeg",
                "original_byte_length": len(original),
                "original_sha256_digest": digest,
                "original_blob_etag": '"original-etag"',
                "row_version": b"\x02" * 8,
            },
            {"outcome": "needs_review", "source_key": SOURCE_KEY, "row_version": b"\x03" * 8},
            {"source_key": SOURCE_KEY, "state": "needs_review", "row_version": b"\x03" * 8},
        ]
        self.storage.get_scan_result.return_value = {
            "result": "clean",
            "scan_time_utc": None,
        }
        self.storage.download.return_value = {
            "data": original,
            "byte_length": len(original),
            "etag": '"original-etag"',
            "content_type": "image/jpeg",
        }
        self.storage.upload.return_value = {"etag": '"preview-etag"'}

        result = self.service.reconcile_and_process(
            self.user_key, SOURCE_KEY, "0101010101010101"
        )

        self.assertEqual(result["state"], "needs_review")
        self.assertEqual(self.storage.method_calls[0].args[0], ORIGINAL)
        self.storage.download.assert_called_once_with(ORIGINAL)
        derivative_call = self.storage.upload.call_args
        self.assertEqual(derivative_call.args[0], PREVIEW)
        self.assertNotEqual(derivative_call.args[1], original)
        self.assertEqual(
            self.db.first_row.call_args_list[1].args[0],
            "usp_RecordPhotoScanResult",
        )

    def test_malicious_scan_never_downloads_or_decodes(self):
        self.db.first_row.side_effect = [
            {
                "source_key": SOURCE_KEY,
                "state": "scanning",
                "original_blob_name": ORIGINAL,
                "row_version": b"\x01" * 8,
            },
            {"outcome": "rejected", "row_version": b"\x02" * 8},
            {"source_key": SOURCE_KEY, "state": "rejected", "row_version": b"\x02" * 8},
        ]
        self.storage.get_scan_result.return_value = {
            "result": "malicious",
            "scan_time_utc": None,
        }

        result = self.service.reconcile_and_process(
            self.user_key, SOURCE_KEY, "0101010101010101"
        )

        self.assertEqual(result["state"], "rejected")
        self.storage.download.assert_not_called()
        self.storage.upload.assert_not_called()

    def test_integrity_failure_is_terminal_and_never_uploads_preview(self):
        self.db.first_row.side_effect = [
            {
                "source_key": SOURCE_KEY,
                "state": "scanning",
                "original_blob_name": ORIGINAL,
                "row_version": b"\x01" * 8,
            },
            {
                "outcome": "processing",
                "original_blob_name": ORIGINAL,
                "derivative_blob_name": PREVIEW,
                "original_content_type": "image/jpeg",
                "original_byte_length": 99,
                "original_sha256_digest": b"x" * 32,
                "original_blob_etag": '"expected"',
                "row_version": b"\x02" * 8,
            },
            {"outcome": "rejected"},
        ]
        self.storage.get_scan_result.return_value = {"result": "clean", "scan_time_utc": None}
        self.storage.download.return_value = {
            "data": b"different",
            "byte_length": 9,
            "etag": '"actual"',
        }

        with self.assertRaisesRegex(PhotoCaptureError, "integrity-failed"):
            self.service.reconcile_and_process(
                self.user_key, SOURCE_KEY, "0101010101010101"
            )

        self.storage.upload.assert_not_called()
        failure_params = self.db.first_row.call_args_list[-1].args[1]
        self.assertIn(("@SafeErrorCode", "integrity_failed"), failure_params)
        self.assertIn(("@Terminal", True), failure_params)

    def test_confirm_requires_member_note_and_preserves_utf16_limit(self):
        with self.assertRaisesRegex(PhotoCaptureError, "required"):
            self.service.confirm_capture(
                self.user_key, SOURCE_KEY, "0101010101010101", "  "
            )
        with self.assertRaisesRegex(PhotoCaptureError, "too-long"):
            self.service.confirm_capture(
                self.user_key, SOURCE_KEY, "0101010101010101", "😀" * 4001
            )

    def test_delete_removes_preview_then_original_before_sql_finalization(self):
        self.db.first_row.side_effect = [
            {
                "outcome": "pending",
                "source_key": SOURCE_KEY,
                "original_blob_name": ORIGINAL,
                "derivative_blob_name": PREVIEW,
                "deletion_token": b"\x02" * 8,
            },
            {"outcome": "success"},
        ]

        result = self.service.delete_draft(
            self.user_key, SOURCE_KEY, "0101010101010101"
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            [call.args[0] for call in self.storage.delete.call_args_list],
            [PREVIEW, ORIGINAL],
        )
        self.assertEqual(
            self.db.first_row.call_args_list[-1].args[0],
            "usp_FinalizePhotoDraftDeletion",
        )

    def test_delete_failure_remains_pending_and_retryable(self):
        self.db.first_row.return_value = {
            "outcome": "pending",
            "source_key": SOURCE_KEY,
            "original_blob_name": ORIGINAL,
            "derivative_blob_name": PREVIEW,
            "deletion_token": b"\x02" * 8,
        }
        self.storage.delete.side_effect = CaptureMediaStorageError(
            "private-storage-delete-failed"
        )

        with self.assertRaisesRegex(PhotoCaptureError, "delete-retry"):
            self.service.delete_draft(
                self.user_key, SOURCE_KEY, "0101010101010101"
            )

        self.assertEqual(self.db.first_row.call_count, 1)


if __name__ == "__main__":
    unittest.main()
