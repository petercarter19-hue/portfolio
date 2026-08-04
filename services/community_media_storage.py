"""Private managed-identity Blob storage for Community attachments."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import re

from services.community_contracts import XLSX_CONTENT_TYPE


OPAQUE_BLOB_NAME = re.compile(
    r"^community/v1/[0-9a-f]{2}/[0-9a-f]{32}(?:-safe)?\.(?:jpg|png|pdf|xlsx)$"
)
SCAN_RESULT_TAG = "Malware scanning scan result"
SCAN_TIME_TAG = "Malware scanning scan time"
SCAN_TIME_UTC_TAG = "Malware Scanning scan time UTC"
MAX_BLOB_BYTES = 10 * 1024 * 1024


class CommunityMediaStorageError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require_blob_name(blob_name):
    if not isinstance(blob_name, str) or not OPAQUE_BLOB_NAME.fullmatch(blob_name):
        raise ValueError("Invalid opaque Community attachment path.")
    return blob_name


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


class CommunityMediaStorage:
    def __init__(self, account_url=None, container_name=None, credential=None):
        self.account_url = account_url or os.getenv("CAPTURE_MEDIA_BLOB_ACCOUNT_URL", "")
        self.container_name = container_name or os.getenv(
            "CAPTURE_MEDIA_BLOB_CONTAINER", "peerslate-private-capture-media"
        )
        self._credential = credential
        self._container_client = None

    def _client(self):
        if self._container_client is not None:
            return self._container_client
        if not self.account_url.startswith("https://") or not self.container_name:
            raise CommunityMediaStorageError("storage_unavailable")
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import ContainerClient

            self._container_client = ContainerClient(
                account_url=self.account_url,
                container_name=self.container_name,
                credential=self._credential or DefaultAzureCredential(),
            )
            return self._container_client
        except Exception as error:
            raise CommunityMediaStorageError("storage_unavailable") from error

    def upload(self, blob_name, data, content_type):
        _require_blob_name(blob_name)
        if content_type not in {
            "image/jpeg",
            "image/png",
            "application/pdf",
            XLSX_CONTENT_TYPE,
        }:
            raise ValueError("Invalid Community attachment type.")
        if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_BLOB_BYTES:
            raise ValueError("Invalid Community attachment size.")
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
                raise CommunityMediaStorageError("storage_conflict") from error
            return {"etag": str(getattr(result, "etag", "") or "")[:128] or None}
        except CommunityMediaStorageError:
            raise
        except Exception as error:
            raise CommunityMediaStorageError("storage_upload_failed") from error

    def download(self, blob_name):
        _require_blob_name(blob_name)
        try:
            blob = self._client().get_blob_client(blob_name)
            properties = blob.get_blob_properties()
            size = int(getattr(properties, "size", 0) or 0)
            if not 1 <= size <= MAX_BLOB_BYTES:
                raise CommunityMediaStorageError("storage_invalid")
            data = blob.download_blob().readall()
            if len(data) != size:
                raise CommunityMediaStorageError("storage_invalid")
            settings = getattr(properties, "content_settings", None)
            return {
                "data": data,
                "byte_length": size,
                "content_type": getattr(settings, "content_type", None),
            }
        except CommunityMediaStorageError:
            raise
        except Exception as error:
            raise CommunityMediaStorageError("storage_read_failed") from error

    def scan_result(self, blob_name):
        _require_blob_name(blob_name)
        try:
            tags = self._client().get_blob_client(blob_name).get_blob_tags() or {}
        except Exception as error:
            raise CommunityMediaStorageError("scan_unavailable") from error
        tags = {str(key).casefold(): value for key, value in dict(tags).items()}
        raw = str(tags.get(SCAN_RESULT_TAG.casefold(), "")).strip().casefold()
        return {
            "result": {
                "no threats found": "clean",
                "malicious": "malicious",
                "error": "error",
                "not scanned": "not_scanned",
            }.get(raw),
            "scan_time_utc": _parse_scan_time(
                tags.get(SCAN_TIME_TAG.casefold())
                or tags.get(SCAN_TIME_UTC_TAG.casefold())
            ),
        }

    def delete(self, blob_name):
        if not blob_name:
            return
        _require_blob_name(blob_name)
        try:
            from azure.core.exceptions import ResourceNotFoundError

            try:
                self._client().delete_blob(blob_name, delete_snapshots="include")
            except ResourceNotFoundError:
                return
        except CommunityMediaStorageError:
            raise
        except Exception as error:
            raise CommunityMediaStorageError("storage_delete_failed") from error


community_media_storage = CommunityMediaStorage()
