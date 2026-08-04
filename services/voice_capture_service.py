"""Owner-scoped orchestration for the first private Voice Capture slice."""

import hashlib
import io
import math
import os
from dataclasses import dataclass
from uuid import UUID, uuid4

from services.database_service import DatabaseServiceError, database_service
from services.media_storage_service import MediaStorageError, media_storage_service
from services.speech_transcription_service import (
    SpeechTranscriptionError,
    speech_transcription_service,
)


MAX_VOICE_BYTES = int(os.getenv("VOICE_MAX_BYTES", str(20 * 1024 * 1024)))
MAX_VOICE_DURATION_SECONDS = int(
    os.getenv("VOICE_MAX_DURATION_SECONDS", "180")
)
MAX_CAPTURE_BODY_LENGTH = 8000
VOICE_LOCALE = "en-US"

SUPPORTED_AUDIO = {
    "audio/webm": ("webm", lambda data: data.startswith(b"\x1aE\xdf\xa3")),
    "audio/ogg": ("ogg", lambda data: data.startswith(b"OggS")),
    "audio/wav": (
        "wav",
        lambda data: len(data) >= 12
        and data.startswith(b"RIFF")
        and data[8:12] == b"WAVE",
    ),
    "audio/x-wav": (
        "wav",
        lambda data: len(data) >= 12
        and data.startswith(b"RIFF")
        and data[8:12] == b"WAVE",
    ),
    "audio/mp4": ("mp4", lambda data: len(data) >= 12 and data[4:8] == b"ftyp"),
    "audio/mpeg": (
        "mp3",
        lambda data: data.startswith(b"ID3")
        or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0),
    ),
    "audio/aac": (
        "aac",
        lambda data: len(data) >= 2
        and data[0] == 0xFF
        and data[1] & 0xF6 in {0xF0, 0xF4},
    ),
}


class VoiceCaptureError(RuntimeError):
    """A stable, owner-safe Voice Capture outcome code."""

    def __init__(self, code, source_key=None):
        self.code = code
        self.source_key = source_key
        super().__init__(code)


@dataclass(frozen=True)
class ValidatedAudio:
    data: bytes
    content_type: str
    extension: str
    byte_length: int
    duration_seconds: float
    locale: str
    sha256_digest: bytes


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
    raise VoiceCaptureError("changed")


def _source_key(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise VoiceCaptureError("changed") from error


def validate_audio(upload, duration_seconds, max_bytes=None, max_duration_seconds=None):
    """Validate duration, size, MIME, and media-container signature.

    ``max_bytes`` and ``max_duration_seconds`` default to this module's
    owner-Capture bounds, so every existing caller behaves exactly as
    before. They exist so a second surface can reuse this validation under
    its OWN, tighter bounds instead of copying the container-signature
    table: PS-WORKSHOP-001 W2d's short Workshop dictation passes much
    smaller numbers (services/workshop_voice_service.py). Only the bounds
    are per-caller — which containers are accepted, and the requirement
    that the bytes actually match the declared MIME type, stay one shared
    contract.
    """
    if upload is None or not getattr(upload, "stream", None):
        raise VoiceCaptureError("required")
    byte_ceiling = MAX_VOICE_BYTES if max_bytes is None else int(max_bytes)
    duration_ceiling = (
        MAX_VOICE_DURATION_SECONDS
        if max_duration_seconds is None
        else float(max_duration_seconds)
    )
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError) as error:
        raise VoiceCaptureError("invalid-duration") from error
    if not math.isfinite(duration) or duration <= 0:
        raise VoiceCaptureError("invalid-duration")
    if duration > duration_ceiling:
        raise VoiceCaptureError("too-long")

    content_type = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0]
    media_contract = SUPPORTED_AUDIO.get(content_type)
    if not media_contract:
        raise VoiceCaptureError("unsupported")
    data = upload.stream.read(byte_ceiling + 1)
    if len(data) > byte_ceiling:
        raise VoiceCaptureError("too-large")
    if not data or not media_contract[1](data):
        raise VoiceCaptureError("unsupported")
    return ValidatedAudio(
        data=data,
        content_type="audio/wav" if content_type == "audio/x-wav" else content_type,
        extension=media_contract[0],
        byte_length=len(data),
        duration_seconds=duration,
        locale=VOICE_LOCALE,
        sha256_digest=hashlib.sha256(data).digest(),
    )


class VoiceCaptureService:
    """Coordinate SQL, private Blob, and Speech state transitions."""

    def __init__(self, database=None, storage=None, speech=None):
        self.database = database or database_service
        self.storage = storage or media_storage_service
        self.speech = speech or speech_transcription_service

    @staticmethod
    def _blob_name(extension):
        opaque = uuid4().hex
        return f"voice/v1/{opaque[:2]}/{opaque}.{extension}"

    @staticmethod
    def _outcome(row, allowed):
        if not row or row.get("outcome") not in allowed:
            raise VoiceCaptureError("changed")
        return row

    def _record_failure(self, procedure, parameters):
        try:
            self.database.first_row(procedure, parameters)
        except DatabaseServiceError:
            pass

    def _transcribe_attempt(self, user_key, queued, audio_bytes, content_type):
        source_key = _source_key(queued["source_key"])
        attempt_number = int(queued["attempt_number"])
        try:
            processing = self._outcome(
                self.database.first_row(
                    "usp_MarkVoiceTranscriptionProcessing",
                    [
                        ("@UserKey", user_key),
                        ("@SourceKey", source_key),
                        ("@AttemptNumber", attempt_number),
                        (
                            "@ExpectedRowVersion",
                            _row_version(queued["row_version"]),
                        ),
                    ],
                ),
                {"processing"},
            )
            completed_row_version = processing["row_version"]
        except (DatabaseServiceError, VoiceCaptureError) as error:
            # The source and private Blob already exist. Preserve their opaque
            # key even when the database outcome is uncertain so the owner can
            # return to the stable review URL and retry or delete explicitly.
            raise VoiceCaptureError(
                "transcription-recovery", source_key
            ) from error
        try:
            result = self.speech.transcribe(audio_bytes, content_type, VOICE_LOCALE)
            transcript = str(result.get("provider_transcript") or "").strip()
            if not transcript:
                raise SpeechTranscriptionError("speech_empty")
            if utf16_length(transcript) > MAX_CAPTURE_BODY_LENGTH:
                raise SpeechTranscriptionError("speech_too_long")
            provider_duration = result.get("duration_seconds")
            if provider_duration is None:
                raise SpeechTranscriptionError("speech_malformed")
            if float(provider_duration) > MAX_VOICE_DURATION_SECONDS:
                raise SpeechTranscriptionError("speech_duration_exceeded")
        except SpeechTranscriptionError as error:
            self._record_failure(
                "usp_FailVoiceTranscription",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@AttemptNumber", attempt_number),
                    ("@SafeErrorCode", error.code),
                ],
            )
            raise VoiceCaptureError("transcription-failed", source_key) from error

        try:
            completed = self.database.first_row(
                "usp_CompleteVoiceTranscription",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@AttemptNumber", attempt_number),
                    (
                        "@ExpectedRowVersion",
                        _row_version(completed_row_version),
                    ),
                    ("@ProviderTranscript", transcript),
                    ("@ProviderRequestId", result.get("provider_request_id")),
                    (
                        "@VerifiedDurationMilliseconds",
                        int(round(float(provider_duration) * 1000)),
                    ),
                ],
            )
            self._outcome(completed, {"needs_review"})
        except (DatabaseServiceError, VoiceCaptureError) as error:
            raise VoiceCaptureError(
                "transcription-recovery", source_key
            ) from error
        return completed

    def create_and_transcribe(self, user_key, upload, duration_seconds):
        audio = validate_audio(upload, duration_seconds)
        blob_name = self._blob_name(audio.extension)
        created = self._outcome(
            self.database.first_row(
                "usp_CreateVoiceDraft",
                [
                    ("@UserKey", user_key),
                    ("@BlobName", blob_name),
                    ("@ContentType", audio.content_type),
                    ("@ByteLength", audio.byte_length),
                    ("@Sha256Digest", audio.sha256_digest),
                    ("@Locale", audio.locale),
                    (
                        "@ClientDurationMilliseconds",
                        int(round(audio.duration_seconds * 1000)),
                    ),
                ],
            ),
            {"created"},
        )
        source_key = _source_key(created["source_key"])
        try:
            self.storage.upload(blob_name, audio.data, audio.content_type)
        except (MediaStorageError, Exception) as error:
            self._record_failure(
                "usp_FailVoiceUpload",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@ExpectedRowVersion", _row_version(created["row_version"])),
                    ("@SafeErrorCode", "storage_unavailable"),
                ],
            )
            raise VoiceCaptureError("upload-failed", source_key) from error

        try:
            queued = self._outcome(
                self.database.first_row(
                    "usp_QueueVoiceTranscription",
                    [
                        ("@UserKey", user_key),
                        ("@SourceKey", source_key),
                        (
                            "@ExpectedRowVersion",
                            _row_version(created["row_version"]),
                        ),
                    ],
                ),
                {"queued"},
            )
        except (DatabaseServiceError, VoiceCaptureError) as error:
            # The Blob upload succeeded, so preserve the opaque source key. Once
            # the database is available the owner can retry or explicitly delete
            # this still-private, uploading draft from its stable review URL.
            raise VoiceCaptureError("queue-failed", source_key) from error
        queued.setdefault("source_key", source_key)
        try:
            self._transcribe_attempt(
                user_key, queued, audio.data, audio.content_type
            )
            draft = self.get_draft(user_key, source_key)
        except VoiceCaptureError as error:
            if error.source_key:
                raise
            raise VoiceCaptureError(
                "transcription-recovery", source_key
            ) from error
        except DatabaseServiceError as error:
            raise VoiceCaptureError(
                "transcription-recovery", source_key
            ) from error
        if not draft:
            raise VoiceCaptureError("transcription-recovery", source_key)
        return draft

    def get_draft(self, user_key, source_key):
        source_key = _source_key(source_key)
        row = self.database.first_row(
            "usp_GetVoiceDraftForOwner",
            [("@UserKey", user_key), ("@SourceKey", source_key)],
        )
        if row:
            row = dict(row)
            if "row_version" in row:
                row["row_version_token"] = _row_version(row["row_version"]).hex()
        return row

    def retry_transcription(self, user_key, source_key, expected_row_version):
        source_key = _source_key(source_key)
        queued = self._outcome(
            self.database.first_row(
                "usp_QueueVoiceTranscription",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@ExpectedRowVersion", _row_version(expected_row_version)),
                ],
            ),
            {"queued"},
        )
        try:
            audio_bytes = self.storage.download(queued["blob_name"])
        except MediaStorageError as error:
            self._record_failure(
                "usp_FailVoiceTranscription",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@AttemptNumber", int(queued["attempt_number"])),
                    ("@SafeErrorCode", "storage_unavailable"),
                ],
            )
            raise VoiceCaptureError("transcription-failed", source_key) from error
        self._transcribe_attempt(
            user_key, queued, audio_bytes, queued["content_type"]
        )
        try:
            draft = self.get_draft(user_key, source_key)
        except (DatabaseServiceError, VoiceCaptureError) as error:
            raise VoiceCaptureError(
                "transcription-recovery", source_key
            ) from error
        if not draft:
            raise VoiceCaptureError("transcription-recovery", source_key)
        return draft

    def confirm_capture(
        self, user_key, source_key, expected_row_version, approved_body
    ):
        source_key = _source_key(source_key)
        body = str(approved_body or "").strip()
        if not body:
            raise VoiceCaptureError("required")
        if utf16_length(body) > MAX_CAPTURE_BODY_LENGTH:
            raise VoiceCaptureError("too-long")
        return self._outcome(
            self.database.first_row(
                "usp_ConfirmVoiceCapture",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", source_key),
                    ("@ExpectedRowVersion", _row_version(expected_row_version)),
                    ("@ApprovedBody", body),
                ],
            ),
            {"created", "existing"},
        )

    def open_audio(self, user_key, source_key):
        source_key = _source_key(source_key)
        row = self.database.first_row(
            "usp_GetVoiceMediaForOwner",
            [("@UserKey", user_key), ("@SourceKey", source_key)],
        )
        if not row:
            return None
        try:
            payload = self.storage.download(row["blob_name"])
        except MediaStorageError as error:
            raise VoiceCaptureError("playback-unavailable") from error
        return {
            "stream": io.BytesIO(payload),
            "content_type": row["content_type"],
            "byte_length": len(payload),
        }

    def _finish_deletion(self, user_key, pending, finalize_procedure):
        try:
            self.storage.delete(pending["blob_name"])
            if self.storage.exists(pending["blob_name"]):
                raise MediaStorageError("private-storage-delete-failed")
        except (MediaStorageError, Exception) as error:
            raise VoiceCaptureError("delete-retry") from error
        return self._outcome(
            self.database.first_row(
                finalize_procedure,
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", _source_key(pending["source_key"])),
                    ("@ExpectedDeletionRowVersion", _row_version(pending["deletion_token"])),
                ],
            ),
            {"success"},
        )

    def delete_draft(self, user_key, source_key, expected_row_version):
        pending = self._outcome(
            self.database.first_row(
                "usp_BeginVoiceDraftDeletion",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", _source_key(source_key)),
                    ("@ExpectedRowVersion", _row_version(expected_row_version)),
                ],
            ),
            {"pending"},
        )
        return self._finish_deletion(
            user_key, pending, "usp_FinalizeVoiceDraftDeletion"
        )

    def delete_capture(self, user_key, capture_key, expected_row_version):
        pending = self._outcome(
            self.database.first_row(
                "usp_DeleteCapture",
                [
                    ("@UserKey", user_key),
                    ("@CaptureKey", _source_key(capture_key)),
                    ("@ExpectedRowVersion", _row_version(expected_row_version)),
                ],
            ),
            {"success", "pending"},
        )
        if pending["outcome"] == "success":
            pending["kind"] = "text"
            return pending
        result = self._finish_deletion(
            user_key, pending, "usp_FinalizeVoiceCaptureDeletion"
        )
        result["kind"] = "voice"
        return result


voice_capture_service = VoiceCaptureService()
