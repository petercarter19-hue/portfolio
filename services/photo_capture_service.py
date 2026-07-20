"""Owner-scoped orchestration for private Photo Capture sources."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import os
import warnings
from uuid import UUID, uuid4

from services.capture_media_storage_service import (
    CaptureMediaStorageError,
    capture_media_storage_service,
)
from services.database_service import DatabaseServiceError, database_service


MAX_PHOTO_BYTES = int(os.getenv("CAPTURE_PHOTO_MAX_BYTES", str(10 * 1024 * 1024)))
MAX_PHOTO_PIXELS = int(os.getenv("CAPTURE_PHOTO_MAX_PIXELS", "20000000"))
MAX_PHOTO_EDGE = int(os.getenv("CAPTURE_PHOTO_MAX_EDGE", "8192"))
MAX_PHOTO_DERIVATIVE_EDGE = int(
    os.getenv("CAPTURE_PHOTO_DERIVATIVE_MAX_EDGE", "2400")
)
MAX_CAPTURE_BODY_LENGTH = 8000


class PhotoCaptureError(RuntimeError):
    """A stable, owner-safe Photo Capture outcome code."""

    def __init__(self, code, source_key=None):
        self.code = code
        self.source_key = source_key
        super().__init__(code)


@dataclass(frozen=True)
class ValidatedPhoto:
    data: bytes
    content_type: str
    extension: str
    byte_length: int
    sha256_digest: bytes


@dataclass(frozen=True)
class NormalizedPhoto:
    data: bytes
    content_type: str
    byte_length: int
    sha256_digest: bytes
    width: int
    height: int


def utf16_length(value):
    return len(value.encode("utf-16-le")) // 2


def _row_version(value):
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes) and len(value) == 8:
        return value
    if isinstance(value, str) and len(value) == 16:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass
    raise PhotoCaptureError("changed")


def _source_key(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise PhotoCaptureError("changed") from error


def validate_photo_upload(upload):
    """Validate bounded bytes, declared type, and complete container markers."""
    if upload is None or not getattr(upload, "stream", None):
        raise PhotoCaptureError("required")
    content_type = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0]
    if content_type not in {"image/jpeg", "image/png"}:
        raise PhotoCaptureError("unsupported")
    data = upload.stream.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise PhotoCaptureError("too-large")
    if not data:
        raise PhotoCaptureError("required")
    if content_type == "image/jpeg":
        if not data.startswith(b"\xff\xd8\xff") or not data.endswith(b"\xff\xd9"):
            raise PhotoCaptureError("unsupported")
        extension = "jpg"
    else:
        png_end = b"\x00\x00\x00\x00IEND\xaeB\x60\x82"
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or not data.endswith(png_end):
            raise PhotoCaptureError("unsupported")
        extension = "png"
    return ValidatedPhoto(
        data=data,
        content_type=content_type,
        extension=extension,
        byte_length=len(data),
        sha256_digest=hashlib.sha256(data).digest(),
    )


def normalize_photo(data, expected_content_type):
    """Decode an already-scanned image and create a metadata-free derivative."""
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise PhotoCaptureError("processing-unavailable") from error

    expected_format = "JPEG" if expected_content_type == "image/jpeg" else "PNG"
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PHOTO_PIXELS
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=[expected_format]) as probe:
                if probe.format != expected_format or getattr(probe, "n_frames", 1) != 1:
                    raise PhotoCaptureError("unsupported")
                width, height = probe.size
                if (
                    width < 1
                    or height < 1
                    or width > MAX_PHOTO_EDGE
                    or height > MAX_PHOTO_EDGE
                    or width * height > MAX_PHOTO_PIXELS
                ):
                    raise PhotoCaptureError("dimensions")
                probe.verify()

            with Image.open(io.BytesIO(data), formats=[expected_format]) as decoded:
                if getattr(decoded, "n_frames", 1) != 1:
                    raise PhotoCaptureError("unsupported")
                decoded.load()
                oriented = ImageOps.exif_transpose(decoded)
                width, height = oriented.size
                if (
                    width < 1
                    or height < 1
                    or width > MAX_PHOTO_EDGE
                    or height > MAX_PHOTO_EDGE
                    or width * height > MAX_PHOTO_PIXELS
                ):
                    raise PhotoCaptureError("dimensions")
                has_alpha = oriented.mode in {"RGBA", "LA"} or (
                    oriented.mode == "P" and "transparency" in oriented.info
                )
                mode = "RGBA" if expected_format == "PNG" and has_alpha else "RGB"
                pixels = oriented.convert(mode)
                if max(pixels.size) > MAX_PHOTO_DERIVATIVE_EDGE:
                    pixels.thumbnail(
                        (MAX_PHOTO_DERIVATIVE_EDGE, MAX_PHOTO_DERIVATIVE_EDGE),
                        Image.Resampling.LANCZOS,
                    )
                clean = Image.new(mode, pixels.size)
                clean.paste(pixels)
                output = io.BytesIO()
                if expected_format == "JPEG":
                    clean.save(
                        output,
                        format="JPEG",
                        quality=90,
                        optimize=True,
                        progressive=True,
                        exif=b"",
                    )
                    content_type = "image/jpeg"
                else:
                    clean.save(output, format="PNG", optimize=True)
                    content_type = "image/png"
                payload = output.getvalue()
                return NormalizedPhoto(
                    data=payload,
                    content_type=content_type,
                    byte_length=len(payload),
                    sha256_digest=hashlib.sha256(payload).digest(),
                    width=clean.width,
                    height=clean.height,
                )
    except PhotoCaptureError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise PhotoCaptureError("dimensions") from error
    except Exception as error:
        raise PhotoCaptureError("invalid-image") from error


class PhotoCaptureService:
    """Coordinate SQL, private Blob scanning, and safe image normalization."""

    def __init__(self, database=None, storage=None):
        self.database = database or database_service
        self.storage = storage or capture_media_storage_service

    @staticmethod
    def _blob_names(extension):
        opaque = uuid4().hex
        prefix = f"photo/v1/{opaque[:2]}/{opaque}"
        return f"{prefix}.{extension}", f"{prefix}-preview.{extension}"

    @staticmethod
    def _outcome(row, allowed):
        if not row or row.get("outcome") not in allowed:
            raise PhotoCaptureError("changed")
        return row

    @staticmethod
    def _prepare(row):
        if not row:
            return None
        prepared = dict(row)
        if "row_version" in prepared:
            prepared["row_version_token"] = _row_version(
                prepared["row_version"]
            ).hex()
        return prepared

    def _record_failure(self, user_key, source_key, row_version, code, terminal=False):
        safe_code = code if code in {
            "storage_unavailable",
            "scan_unavailable",
            "scan_error",
            "not_scanned",
            "integrity_failed",
            "invalid_image",
            "dimensions",
            "processing_failed",
        } else "processing_failed"
        try:
            self.database.first_row(
                "usp_FailPhotoSource",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", _source_key(source_key)),
                    ("@ExpectedRowVersion", _row_version(row_version)),
                    ("@SafeErrorCode", safe_code),
                    ("@Terminal", bool(terminal)),
                ],
            )
        except (DatabaseServiceError, PhotoCaptureError):
            pass

    def create_source(self, user_key, upload):
        photo = validate_photo_upload(upload)
        original_name, derivative_name = self._blob_names(photo.extension)
        created = self._outcome(
            self.database.first_row(
                "usp_CreatePhotoSource",
                [
                    ("@UserKey", user_key),
                    ("@OriginalBlobName", original_name),
                    ("@DerivativeBlobName", derivative_name),
                    ("@OriginalContentType", photo.content_type),
                    ("@OriginalByteLength", photo.byte_length),
                    ("@OriginalSha256Digest", photo.sha256_digest),
                ],
            ),
            {"created", "draft_limit"},
        )
        if created["outcome"] == "draft_limit":
            raise PhotoCaptureError("draft-limit")
        source_key = _source_key(created["source_key"])
        try:
            uploaded = self.storage.upload(
                original_name, photo.data, photo.content_type
            )
        except (CaptureMediaStorageError, Exception) as error:
            self._record_failure(
                user_key,
                source_key,
                created["row_version"],
                "storage_unavailable",
            )
            raise PhotoCaptureError("upload-failed", source_key) from error
        try:
            self._outcome(
                self.database.first_row(
                    "usp_MarkPhotoUploaded",
                    [
                        ("@UserKey", user_key),
                        ("@SourceKey", source_key),
                        ("@ExpectedRowVersion", _row_version(created["row_version"])),
                        ("@OriginalBlobEtag", uploaded.get("etag")),
                    ],
                ),
                {"scanning"},
            )
            draft = self.get_source(user_key, source_key)
        except (DatabaseServiceError, PhotoCaptureError) as error:
            raise PhotoCaptureError("upload-recovery", source_key) from error
        if not draft:
            raise PhotoCaptureError("upload-recovery", source_key)
        return draft

    def get_source(self, user_key, source_key):
        row = self.database.first_row(
            "usp_GetPhotoSourceForOwner",
            [("@UserKey", user_key), ("@SourceKey", _source_key(source_key))],
        )
        return self._prepare(row)

    def reconcile_and_process(self, user_key, source_key, expected_row_version):
        source_key = _source_key(source_key)
        processing_source = self.database.first_row(
            "usp_GetPhotoProcessingSourceForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", source_key),
                ("@ExpectedRowVersion", _row_version(expected_row_version)),
            ],
        )
        if not processing_source:
            raise PhotoCaptureError("changed")
        state = processing_source.get("state")
        if state == "needs_review" or state == "confirmed":
            return self.get_source(user_key, source_key)
        if state not in {"scanning", "failed"}:
            raise PhotoCaptureError("changed")

        try:
            scan = self.storage.get_scan_result(
                processing_source["original_blob_name"]
            )
        except CaptureMediaStorageError as error:
            self._record_failure(
                user_key,
                source_key,
                processing_source["row_version"],
                "scan_unavailable",
            )
            raise PhotoCaptureError("scan-unavailable", source_key) from error
        if not scan.get("result"):
            return self.get_source(user_key, source_key)

        result = scan["result"]
        safe_code = {
            "malicious": "malicious",
            "error": "scan_error",
            "not_scanned": "not_scanned",
        }.get(result)
        transition = self._outcome(
            self.database.first_row(
                "usp_RecordPhotoScanResult",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    (
                        "@ExpectedRowVersion",
                        _row_version(processing_source["row_version"]),
                    ),
                    ("@ScanResult", result),
                    ("@ScanCompletedAtUtc", scan.get("scan_time_utc")),
                    ("@SafeErrorCode", safe_code),
                ],
            ),
            {"processing", "failed", "rejected"},
        )
        if transition["outcome"] != "processing":
            return self.get_source(user_key, source_key)

        try:
            original = self.storage.download(transition["original_blob_name"])
            payload = original["data"]
            if (
                len(payload) != int(transition["original_byte_length"])
                or int(original["byte_length"]) != len(payload)
                or hashlib.sha256(payload).digest()
                != bytes(transition["original_sha256_digest"])
            ):
                raise PhotoCaptureError("integrity-failed")
            expected_etag = str(transition.get("original_blob_etag") or "")
            actual_etag = str(original.get("etag") or "")
            if expected_etag and actual_etag and expected_etag != actual_etag:
                raise PhotoCaptureError("integrity-failed")
            derivative = normalize_photo(payload, transition["original_content_type"])
            try:
                uploaded = self.storage.upload(
                    transition["derivative_blob_name"],
                    derivative.data,
                    derivative.content_type,
                )
            except CaptureMediaStorageError as error:
                if error.code != "private-storage-conflict":
                    raise
                existing = self.storage.download(transition["derivative_blob_name"])
                if hashlib.sha256(existing["data"]).digest() != derivative.sha256_digest:
                    raise PhotoCaptureError("integrity-failed") from error
                uploaded = {"etag": existing.get("etag")}
            completed = self._outcome(
                self.database.first_row(
                    "usp_CompletePhotoProcessing",
                    [
                        ("@UserKey", user_key),
                        ("@SourceKey", source_key),
                        ("@ExpectedRowVersion", _row_version(transition["row_version"])),
                        ("@DerivativeContentType", derivative.content_type),
                        ("@DerivativeByteLength", derivative.byte_length),
                        ("@DerivativeSha256Digest", derivative.sha256_digest),
                        ("@DerivativeBlobEtag", uploaded.get("etag")),
                        ("@PixelWidth", derivative.width),
                        ("@PixelHeight", derivative.height),
                    ],
                ),
                {"needs_review"},
            )
        except PhotoCaptureError as error:
            terminal = error.code in {"integrity-failed", "invalid-image", "dimensions", "unsupported"}
            safe_code = "integrity_failed" if error.code == "integrity-failed" else error.code.replace("-", "_")
            self._record_failure(
                user_key,
                source_key,
                transition["row_version"],
                safe_code,
                terminal=terminal,
            )
            raise PhotoCaptureError(error.code, source_key) from error
        except (CaptureMediaStorageError, DatabaseServiceError, Exception) as error:
            self._record_failure(
                user_key,
                source_key,
                transition["row_version"],
                "processing_failed",
            )
            raise PhotoCaptureError("processing-failed", source_key) from error
        return self.get_source(user_key, source_key) or self._prepare(completed)

    def confirm_capture(self, user_key, source_key, expected_row_version, body):
        source_key = _source_key(source_key)
        body = str(body or "").strip()
        if not body:
            raise PhotoCaptureError("required")
        if utf16_length(body) > MAX_CAPTURE_BODY_LENGTH:
            raise PhotoCaptureError("too-long")
        return self._outcome(
            self.database.first_row(
                "usp_ConfirmPhotoCapture",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@ExpectedRowVersion", _row_version(expected_row_version)),
                    ("@ApprovedBody", body),
                ],
            ),
            {"created", "existing"},
        )

    def open_media(self, user_key, source_key, media_kind):
        if media_kind not in {"preview", "original"}:
            raise PhotoCaptureError("changed")
        row = self.database.first_row(
            "usp_GetPhotoMediaForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", _source_key(source_key)),
                ("@MediaKind", media_kind),
            ],
        )
        if not row:
            return None
        try:
            stored = self.storage.download(row["blob_name"])
        except CaptureMediaStorageError as error:
            raise PhotoCaptureError("media-unavailable") from error
        digest = hashlib.sha256(stored["data"]).digest()
        if len(stored["data"]) != int(row["byte_length"]) or digest != bytes(
            row["sha256_digest"]
        ):
            raise PhotoCaptureError("media-unavailable")
        return {
            "stream": io.BytesIO(stored["data"]),
            "content_type": row["content_type"],
            "byte_length": len(stored["data"]),
        }

    def _finish_deletion(self, user_key, pending, finalize_procedure):
        names = [pending.get("derivative_blob_name"), pending.get("original_blob_name")]
        try:
            for blob_name in names:
                if blob_name:
                    self.storage.delete(blob_name)
            for blob_name in names:
                if blob_name and self.storage.exists(blob_name):
                    raise CaptureMediaStorageError("private-storage-delete-failed")
        except (CaptureMediaStorageError, Exception) as error:
            raise PhotoCaptureError("delete-retry") from error
        return self._outcome(
            self.database.first_row(
                finalize_procedure,
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", _source_key(pending["source_key"])),
                    (
                        "@ExpectedDeletionRowVersion",
                        _row_version(pending["deletion_token"]),
                    ),
                ],
            ),
            {"success"},
        )

    def delete_draft(self, user_key, source_key, expected_row_version):
        pending = self._outcome(
            self.database.first_row(
                "usp_BeginPhotoDraftDeletion",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", _source_key(source_key)),
                    ("@ExpectedRowVersion", _row_version(expected_row_version)),
                ],
            ),
            {"pending"},
        )
        return self._finish_deletion(
            user_key, pending, "usp_FinalizePhotoDraftDeletion"
        )

    def finish_capture_deletion(self, user_key, pending):
        return self._finish_deletion(
            user_key, pending, "usp_FinalizePhotoCaptureDeletion"
        )


photo_capture_service = PhotoCaptureService()
