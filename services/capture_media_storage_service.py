"""Private Azure Blob adapter for quarantined Capture Media sources.

The adapter accepts only server-generated Photo v1 blob names and authenticates
with Microsoft Entra managed identity. It never creates a SAS URL, accepts a
client path, writes member metadata, or falls back to an account key.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import re


OPAQUE_PHOTO_BLOB_NAME = re.compile(
    r"^photo/v1/[0-9a-f]{2}/[0-9a-f]{32}(?:-preview)?\.(?:jpg|png)$"
)
SCAN_RESULT_TAG = "Malware scanning scan result"
SCAN_TIME_TAG = "Malware scanning scan time"
MAX_CAPTURE_MEDIA_BLOB_BYTES = 10 * 1024 * 1024


class CaptureMediaStorageError(RuntimeError):
    """A stable storage outcome that contains no provider or blob detail."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require_blob_name(blob_name):
    if not isinstance(blob_name, str) or not OPAQUE_PHOTO_BLOB_NAME.fullmatch(
        blob_name
    ):
        raise ValueError("Invalid opaque Capture Media blob name.")
    return blob_name


def _etag_value(value):
    value = str(value or "").strip()
    if len(value) > 128:
        raise CaptureMediaStorageError("private-storage-invalid-properties")
    return value or None


def _parse_scan_time(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


class CaptureMediaStorageService:
    """Upload, inspect, read, and delete private Photo v1 blobs."""

    def __init__(self, account_url=None, container_name=None, credential=None):
        self.account_url = account_url or os.getenv(
            "CAPTURE_MEDIA_BLOB_ACCOUNT_URL", ""
        )
        self.container_name = container_name or os.getenv(
            "CAPTURE_MEDIA_BLOB_CONTAINER", "peerslate-private-capture-media"
        )
        self._credential = credential
        self._container_client = None

    def _client(self):
        if self._container_client is not None:
            return self._container_client
        if not self.account_url.startswith("https://") or not self.container_name:
            raise CaptureMediaStorageError("private-storage-unavailable")
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import ContainerClient

            credential = self._credential or DefaultAzureCredential()
            self._container_client = ContainerClient(
                account_url=self.account_url,
                container_name=self.container_name,
                credential=credential,
            )
            return self._container_client
        except Exception as error:
            raise CaptureMediaStorageError("private-storage-unavailable") from error

    def upload(self, blob_name, data, content_type):
        """Create one private block Blob without overwrite or member metadata."""
        _require_blob_name(blob_name)
        if content_type not in {"image/jpeg", "image/png"}:
            raise ValueError("Invalid Capture Media content type.")
        if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_CAPTURE_MEDIA_BLOB_BYTES:
            raise ValueError("Invalid Capture Media payload size.")
        try:
            from azure.core.exceptions import ResourceExistsError
            from azure.storage.blob import ContentSettings

            try:
                result = self._client().upload_blob(
                    name=blob_name,
                    data=data,
                    overwrite=False,
                    metadata=None,
                    content_settings=ContentSettings(content_type=content_type),
                )
            except ResourceExistsError as error:
                raise CaptureMediaStorageError("private-storage-conflict") from error
            return {"etag": _etag_value(getattr(result, "etag", None))}
        except CaptureMediaStorageError:
            raise
        except Exception as error:
            raise CaptureMediaStorageError("private-storage-upload-failed") from error

    def download(self, blob_name):
        """Return bytes and bounded object properties after caller authorization."""
        _require_blob_name(blob_name)
        try:
            blob = self._client().get_blob_client(blob_name)
            properties = blob.get_blob_properties()
            size = getattr(properties, "size", None)
            if size is None or not 1 <= int(size) <= MAX_CAPTURE_MEDIA_BLOB_BYTES:
                raise CaptureMediaStorageError("private-storage-invalid-properties")
            payload = blob.download_blob().readall()
            if len(payload) != int(size):
                raise CaptureMediaStorageError("private-storage-invalid-properties")
            content_settings = getattr(properties, "content_settings", None)
            return {
                "data": payload,
                "byte_length": int(size),
                "etag": _etag_value(getattr(properties, "etag", None)),
                "content_type": getattr(content_settings, "content_type", None),
            }
        except CaptureMediaStorageError:
            raise
        except Exception as error:
            raise CaptureMediaStorageError("private-storage-read-failed") from error

    def get_scan_result(self, blob_name):
        """Read Defender-owned result tags; this adapter never writes Blob tags."""
        _require_blob_name(blob_name)
        try:
            tags = self._client().get_blob_client(blob_name).get_blob_tags() or {}
        except CaptureMediaStorageError:
            raise
        except Exception as error:
            raise CaptureMediaStorageError("private-storage-tags-unavailable") from error

        normalized = {str(key).casefold(): value for key, value in dict(tags).items()}
        raw_result = str(normalized.get(SCAN_RESULT_TAG.casefold(), "")).strip()
        result_map = {
            "no threats found": "clean",
            "malicious": "malicious",
            "error": "error",
            "not scanned": "not_scanned",
        }
        return {
            "result": result_map.get(raw_result.casefold()),
            "scan_time_utc": _parse_scan_time(
                normalized.get(SCAN_TIME_TAG.casefold())
            ),
        }

    def delete(self, blob_name):
        """Delete a blob or prove it is already absent."""
        if not blob_name:
            return
        _require_blob_name(blob_name)
        try:
            from azure.core.exceptions import ResourceNotFoundError

            try:
                self._client().delete_blob(blob_name, delete_snapshots="include")
            except ResourceNotFoundError:
                return
        except CaptureMediaStorageError:
            raise
        except Exception as error:
            raise CaptureMediaStorageError("private-storage-delete-failed") from error

    def exists(self, blob_name):
        if not blob_name:
            return False
        _require_blob_name(blob_name)
        try:
            return bool(self._client().get_blob_client(blob_name).exists())
        except CaptureMediaStorageError:
            raise
        except Exception as error:
            raise CaptureMediaStorageError("private-storage-read-failed") from error


capture_media_storage_service = CaptureMediaStorageService()
