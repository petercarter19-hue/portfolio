"""Dedicated private Resume originals; opaque paths and managed identity only.

The caller must resolve owner-qualified SQL metadata before every read/delete.
This adapter accepts no URL, account key, SAS or member filename. It performs
one operation without application retries and exposes only stable error codes.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit


MAX_ORIGINAL_BYTES = 50_000_000
MAX_CHUNK_BYTES = 4 * 1024 * 1024
OPAQUE_ORIGINAL_PATH = re.compile(r"^resume/v1/[0-9a-f]{2}/[0-9a-f]{32}$")
ORIGINAL_TYPES = frozenset({
    "application/pdf", "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})


class ResumeOriginalStorageError(RuntimeError):
    def __init__(self, code="original_storage_unavailable"):
        self.code = code
        super().__init__(code)


def require_path(path):
    if not isinstance(path, str) or not OPAQUE_ORIGINAL_PATH.fullmatch(path):
        raise ResumeOriginalStorageError("original_metadata_invalid")
    return path


def require_etag(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ResumeOriginalStorageError("original_metadata_invalid")
    return value


class ResumeOriginalStorageService:
    def __init__(self, *, account_url, container_name, credential=None, client=None):
        origin = urlsplit(account_url)
        if (origin.scheme != "https" or not (origin.hostname or "").endswith(".blob.core.windows.net")
                or origin.username or origin.password or origin.port not in (None, 443)
                or origin.path not in ("", "/") or origin.query or origin.fragment
                or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", container_name or "")):
            raise ResumeOriginalStorageError("original_storage_unconfigured")
        self.account_url = "https://" + origin.hostname
        self.container_name = container_name
        self._credential, self._container = credential, client

    def _client(self):
        if self._container is None:
            try:
                from azure.identity import ManagedIdentityCredential
                from azure.storage.blob import ContainerClient
                credential = self._credential or ManagedIdentityCredential()
                self._container = ContainerClient(
                    account_url=self.account_url, container_name=self.container_name,
                    credential=credential, retry_total=0, max_single_put_size=MAX_ORIGINAL_BYTES,
                )
            except Exception:
                raise ResumeOriginalStorageError() from None
        return self._container

    def upload(self, path, data, content_type):
        require_path(path)
        if (not isinstance(data, bytes) or not 1 <= len(data) <= MAX_ORIGINAL_BYTES
                or content_type not in ORIGINAL_TYPES):
            raise ResumeOriginalStorageError("original_metadata_invalid")
        try:
            from azure.storage.blob import ContentSettings
            result = self._client().upload_blob(
                name=path, data=data, overwrite=False, metadata=None,
                content_settings=ContentSettings(content_type="application/octet-stream"),
                max_concurrency=1,
            )
            etag = result.get("etag") if isinstance(result, dict) else getattr(result, "etag", None)
            return require_etag(etag)
        except ResumeOriginalStorageError:
            raise
        except Exception:
            raise ResumeOriginalStorageError("original_upload_unavailable") from None

    def read(self, path, *, etag, byte_length, sha256):
        """Bound chunk allocation and verify all bytes before the caller responds."""
        require_path(path)
        require_etag(etag)
        if (type(byte_length) is not int or not 1 <= byte_length <= MAX_ORIGINAL_BYTES
                or not isinstance(sha256, str) or not re.fullmatch("[0-9a-f]{64}", sha256)):
            raise ResumeOriginalStorageError("original_metadata_invalid")
        try:
            from azure.core import MatchConditions
            blob = self._client().get_blob_client(path)
            properties = blob.get_blob_properties()
            if getattr(properties, "size", None) != byte_length or getattr(properties, "etag", None) != etag:
                raise ResumeOriginalStorageError("original_integrity_unavailable")
            downloader = blob.download_blob(
                offset=0, length=byte_length + 1, etag=etag,
                match_condition=MatchConditions.IfNotModified, max_concurrency=1,
            )
            data = bytearray()
            digest = hashlib.sha256()
            for chunk in downloader.chunks():
                if (not isinstance(chunk, bytes) or len(chunk) > MAX_CHUNK_BYTES
                        or len(data) + len(chunk) > byte_length):
                    raise ResumeOriginalStorageError("original_integrity_unavailable")
                digest.update(chunk)
                data.extend(chunk)
            if len(data) != byte_length or digest.hexdigest() != sha256:
                raise ResumeOriginalStorageError("original_integrity_unavailable")
            return bytes(data)
        except ResumeOriginalStorageError:
            raise
        except Exception:
            raise ResumeOriginalStorageError("original_read_unavailable") from None

    def confirm_upload(self, path, *, byte_length, sha256):
        """Prove one create-only upload committed before closing deletion.

        Absence cannot prove an interrupted upload will not complete later.
        The durable pending intent/path must survive that uncertainty.
        """
        require_path(path)
        try:
            properties = self._client().get_blob_client(path).get_blob_properties()
            etag = require_etag(getattr(properties, "etag", None))
            self.read(path, etag=etag, byte_length=byte_length, sha256=sha256)
            return etag
        except ResumeOriginalStorageError:
            raise
        except Exception:
            raise ResumeOriginalStorageError("original_upload_unconfirmed") from None

    def delete(self, path, *, etag):
        """Conditional delete followed by an explicit absence observation.

        The upload must already be confirmed. An absent unconfirmed path is
        uncertain and cannot authorize forgetting durable deletion intent.
        """
        require_path(path)
        require_etag(etag)
        try:
            from azure.core import MatchConditions
            from azure.core.exceptions import ResourceNotFoundError
            blob = self._client().get_blob_client(path)
            options = {"delete_snapshots": "include"}
            if etag is not None:
                options.update(etag=etag, match_condition=MatchConditions.IfNotModified)
            try:
                blob.delete_blob(**options)
            except ResourceNotFoundError:
                pass
            if blob.exists():
                raise ResumeOriginalStorageError("original_delete_pending")
            return True
        except ResumeOriginalStorageError:
            raise
        except Exception:
            raise ResumeOriginalStorageError("original_delete_pending") from None
