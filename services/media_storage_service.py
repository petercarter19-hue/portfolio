"""Private Azure Blob adapter for Voice Capture source audio.

The adapter accepts only opaque server-generated blob names and authenticates with
Microsoft Entra through ``DefaultAzureCredential``.  It never creates a URL,
SAS token, metadata entry, or storage-key fallback.
"""

import os
import re


OPAQUE_VOICE_BLOB_NAME = re.compile(
    r"^voice/v1/[0-9a-f]{2}/[0-9a-f]{32}\.(?:webm|ogg|wav|mp4|mp3|aac)$"
)


class MediaStorageError(RuntimeError):
    """A safe storage failure that contains no provider response or blob name."""


def _require_blob_name(blob_name):
    if not isinstance(blob_name, str) or not OPAQUE_VOICE_BLOB_NAME.fullmatch(
        blob_name
    ):
        raise ValueError("Invalid opaque Voice blob name.")
    return blob_name


class MediaStorageService:
    """Upload, read, and delete private Voice blobs using managed identity."""

    def __init__(self, account_url=None, container_name=None, credential=None):
        self.account_url = account_url or os.getenv("VOICE_BLOB_ACCOUNT_URL", "")
        self.container_name = container_name or os.getenv(
            "VOICE_BLOB_CONTAINER", "peerslate-private-voice"
        )
        self._credential = credential
        self._container_client = None

    def _client(self):
        if self._container_client is not None:
            return self._container_client
        if not self.account_url.startswith("https://") or not self.container_name:
            raise MediaStorageError("private-storage-unavailable")
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
            raise MediaStorageError("private-storage-unavailable") from error

    def upload(self, blob_name, data, content_type):
        """Create one non-public blob without metadata or overwrite behavior."""
        _require_blob_name(blob_name)
        try:
            from azure.storage.blob import ContentSettings

            self._client().upload_blob(
                name=blob_name,
                data=data,
                overwrite=False,
                metadata=None,
                content_settings=ContentSettings(content_type=content_type),
            )
        except MediaStorageError:
            raise
        except Exception as error:
            raise MediaStorageError("private-storage-upload-failed") from error

    def download(self, blob_name):
        """Return private bytes only after the caller has resolved ownership."""
        _require_blob_name(blob_name)
        try:
            return self._client().download_blob(blob_name).readall()
        except MediaStorageError:
            raise
        except Exception as error:
            raise MediaStorageError("private-storage-read-failed") from error

    def delete(self, blob_name):
        """Delete a blob or prove it is already absent."""
        _require_blob_name(blob_name)
        try:
            from azure.core.exceptions import ResourceNotFoundError

            try:
                self._client().delete_blob(blob_name, delete_snapshots="include")
            except ResourceNotFoundError:
                return
        except MediaStorageError:
            raise
        except Exception as error:
            raise MediaStorageError("private-storage-delete-failed") from error

    def exists(self, blob_name):
        """Check presence without returning provider metadata."""
        _require_blob_name(blob_name)
        try:
            return bool(self._client().get_blob_client(blob_name).exists())
        except MediaStorageError:
            raise
        except Exception as error:
            raise MediaStorageError("private-storage-read-failed") from error


media_storage_service = MediaStorageService()
