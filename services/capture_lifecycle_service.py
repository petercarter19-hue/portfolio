"""Generic Capture aggregate deletion dispatch for text, Voice, and Photo."""

from services.database_service import database_service
from services.media_storage_service import MediaStorageError, media_storage_service
from services.photo_capture_service import PhotoCaptureError, photo_capture_service


class CaptureLifecycleError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class CaptureLifecycleService:
    def __init__(self, database=None, voice_storage=None, photo_service=None):
        self.database = database or database_service
        self.voice_storage = voice_storage or media_storage_service
        self.photo_service = photo_service or photo_capture_service

    @staticmethod
    def _outcome(row, allowed):
        if not row or row.get("outcome") not in allowed:
            raise CaptureLifecycleError("changed")
        return row

    def _finish_voice(self, user_key, pending):
        try:
            self.voice_storage.delete(pending["blob_name"])
            if self.voice_storage.exists(pending["blob_name"]):
                raise MediaStorageError("private-storage-delete-failed")
        except (MediaStorageError, Exception) as error:
            raise CaptureLifecycleError("delete-retry") from error
        return self._outcome(
            self.database.first_row(
                "usp_FinalizeVoiceCaptureDeletion",
                [
                    ("@UserKey", user_key),
                    ("@SourceKey", pending["source_key"]),
                    ("@ExpectedDeletionRowVersion", pending["deletion_token"]),
                ],
            ),
            {"success"},
        )

    def delete_capture(self, user_key, capture_key, expected_row_version):
        pending = self._outcome(
            self.database.first_row(
                "usp_DeleteCapture",
                [
                    ("@UserKey", user_key),
                    ("@CaptureKey", capture_key),
                    ("@ExpectedRowVersion", expected_row_version),
                ],
            ),
            {"success", "pending"},
        )
        if pending["outcome"] == "success":
            pending["kind"] = "text"
            return pending
        source_type = pending.get("source_type")
        try:
            if source_type == "voice":
                result = self._finish_voice(user_key, pending)
            elif source_type == "photo":
                result = self.photo_service.finish_capture_deletion(
                    user_key, pending
                )
            else:
                raise CaptureLifecycleError("changed")
        except PhotoCaptureError as error:
            code = getattr(error, "code", "delete-retry")
            raise CaptureLifecycleError(code) from error
        result["kind"] = source_type
        return result


capture_lifecycle_service = CaptureLifecycleService()
