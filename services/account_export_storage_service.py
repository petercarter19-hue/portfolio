"""Private Azure Blob adapter for the C2 account-export archive.

Job- and attempt-scoped staging, promotion only after an independent
readback recomputes SHA-256 and both byte-size facts, and content-free
idempotent cleanup of staging and final objects. Authenticates with
Microsoft Entra managed identity, matching
services/capture_media_storage_service.py and services/media_storage_service.py.

This adapter NEVER creates a SAS token, a public or direct container
URL, or a caller-selected object name. Every path is built only from
the server-issued ``job_key`` (a uniqueidentifier -- already opaque and
unguessable) and a bounded attempt ordinal; ``final_artifact_reference``
is a private, server-only locator for a future internal proxy download
(C3), never a value returned to a browser
(matches CK_account_export_jobs_artifact_not_url in
SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql).

C0 planning caps (docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
C0_ACCOUNT_EXPORT_ARCHITECTURE.md, "C2 private artifact and workload
design"): 100 MiB compressed, 250 MiB uncompressed. Both are enforced
here again, independent of services/account_export_assembly_service.py
already enforcing them during assembly -- this adapter never trusts a
caller's claim about what it is uploading.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile


MAX_COMPRESSED_BYTES = 100 * 1024 * 1024  # C0's approved compressed ZIP cap
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024  # C0's approved uncompressed cap

_UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
STAGING_BLOB_NAME = re.compile(
    r"^export/v1/staging/" + _UUID_PATTERN + r"/[1-3]\.zip\.part$"
)
FINAL_BLOB_NAME = re.compile(r"^export/v1/final/" + _UUID_PATTERN + r"\.zip$")


class AccountExportStorageError(RuntimeError):
    """A stable storage outcome. Never carries an object name, account
    URL, container name, or provider response body."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require_job_key(job_key):
    if not isinstance(job_key, str) or not re.fullmatch(_UUID_PATTERN, job_key):
        raise ValueError("Invalid opaque account export job key.")
    return job_key


def _require_attempt(attempt):
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 3:
        raise ValueError("Invalid account export attempt ordinal.")
    return attempt


def staging_blob_name(job_key, attempt):
    """Server-generated staging path scoped to one job_key and attempt.

    Staging objects are never downloadable: nothing in this module, or
    any caller of it, ever exposes this name outside the private
    container.
    """

    name = "export/v1/staging/%s/%d.zip.part" % (
        _require_job_key(job_key),
        _require_attempt(attempt),
    )
    assert STAGING_BLOB_NAME.fullmatch(name)
    return name


def final_blob_name(job_key):
    """Server-generated final object path. One per job, ever -- the
    object is created once (overwrite=False) and never replaced."""

    name = "export/v1/final/%s.zip" % _require_job_key(job_key)
    assert FINAL_BLOB_NAME.fullmatch(name)
    return name


class AccountExportStorageService:
    """Stage, verify-and-promote, and idempotently clean up one export
    archive per job."""

    def __init__(
        self,
        account_url=None,
        container_name=None,
        credential=None,
        max_compressed_bytes=MAX_COMPRESSED_BYTES,
        max_uncompressed_bytes=MAX_UNCOMPRESSED_BYTES,
    ):
        self.account_url = account_url or os.getenv("EXPORT_BLOB_ACCOUNT_URL", "")
        self.container_name = container_name or os.getenv(
            "EXPORT_BLOB_CONTAINER", "peerslate-private-account-export"
        )
        self._credential = credential
        self._container_client = None
        self.max_compressed_bytes = max_compressed_bytes
        self.max_uncompressed_bytes = max_uncompressed_bytes

    def _client(self):
        if self._container_client is not None:
            return self._container_client
        if not self.account_url.startswith("https://") or not self.container_name:
            raise AccountExportStorageError("storage_unavailable")
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
            raise AccountExportStorageError("storage_unavailable") from error

    def assert_container_access(self):
        """Prove the active worker identity can reach only the
        configured container. No key, SAS, listing, or content is read
        or returned -- matches
        services/community_media_storage.py's own preflight.
        """

        try:
            self._client().get_container_properties()
            return True
        except AccountExportStorageError:
            raise
        except Exception as error:
            raise AccountExportStorageError("storage_access_denied") from error

    def stage(self, job_key, attempt, data):
        """Upload the complete archive once to a staging object.

        Create-only: a given job and attempt stage exactly once. The
        return value is ``None`` deliberately -- nothing about this
        call is authoritative. ``promote`` always re-derives the facts
        it commits from an independent readback, never from what a
        caller believes it just uploaded.
        """

        name = staging_blob_name(job_key, attempt)
        if not isinstance(data, bytes) or not data:
            raise ValueError("Invalid account export archive payload.")
        if len(data) > self.max_compressed_bytes:
            raise AccountExportStorageError("oversize_compressed")
        try:
            from azure.core.exceptions import ResourceExistsError
            from azure.storage.blob import ContentSettings

            try:
                self._client().upload_blob(
                    name=name,
                    data=data,
                    overwrite=False,
                    metadata=None,
                    content_settings=ContentSettings(content_type="application/zip"),
                )
            except ResourceExistsError as error:
                raise AccountExportStorageError("storage_conflict") from error
        except AccountExportStorageError:
            raise
        except Exception as error:
            raise AccountExportStorageError("storage_upload_failed") from error

    def promote(self, job_key, attempt):
        """Read the staged archive back, independently verify it, and
        promote only the verified bytes to the final object.

        Every value this method returns (``reference``, ``sha256``,
        ``compressed_size_bytes``, ``uncompressed_size_bytes``) is
        recomputed here from what is actually persisted in the staging
        object -- never taken on faith from the caller or from the
        pre-upload archive bytes. Promotion is therefore structurally
        impossible without a successful independent readback and
        recomputation: there is no parameter that lets a caller assert
        a hash or size and skip verification.
        """

        staging_name = staging_blob_name(job_key, attempt)
        final_name = final_blob_name(job_key)

        try:
            blob = self._client().get_blob_client(staging_name)
            properties = blob.get_blob_properties()
            reported_size = int(getattr(properties, "size", 0) or 0)
            data = blob.download_blob().readall()
        except AccountExportStorageError:
            raise
        except Exception as error:
            raise AccountExportStorageError("storage_read_failed") from error

        if not data or len(data) != reported_size:
            raise AccountExportStorageError("storage_invalid_properties")
        if len(data) > self.max_compressed_bytes:
            raise AccountExportStorageError("oversize_compressed")

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if "manifest.json" not in archive.namelist():
                    raise AccountExportStorageError("corrupt_archive")
                # Excludes manifest.json itself, matching the exact
                # definition services/account_export_assembly_service.py
                # uses for its own returned uncompressed_size_bytes, so
                # a happy-path value agrees exactly with what assembly
                # already checked against the same cap.
                uncompressed_size_bytes = sum(
                    info.file_size
                    for info in archive.infolist()
                    if info.filename != "manifest.json"
                )
        except zipfile.BadZipFile as error:
            raise AccountExportStorageError("corrupt_archive") from error

        if uncompressed_size_bytes > self.max_uncompressed_bytes:
            raise AccountExportStorageError("oversize_uncompressed")

        sha256 = hashlib.sha256(data).hexdigest()

        try:
            from azure.core.exceptions import ResourceExistsError
            from azure.storage.blob import ContentSettings

            try:
                self._client().upload_blob(
                    name=final_name,
                    data=data,
                    overwrite=False,
                    metadata=None,
                    content_settings=ContentSettings(content_type="application/zip"),
                )
            except ResourceExistsError as error:
                raise AccountExportStorageError("storage_conflict") from error
        except AccountExportStorageError:
            raise
        except Exception as error:
            raise AccountExportStorageError("storage_upload_failed") from error

        # Best-effort: the final object is already committed above, so
        # promotion has already succeeded. A transient staging-delete
        # failure here must never turn a successful promotion into a
        # reported failure -- that would make the worker fail an
        # already-`ready`-bound job and burn a retry attempt for
        # nothing, and every future retry of this same attempt would
        # then hit `storage_conflict` against the now-orphaned final
        # object (create-only, overwrite=False) until attempts run out.
        # Matches the worker's own best-effort cleanup-on-failure
        # treatment (run_account_export_worker.py).
        try:
            self.cleanup_staging(job_key, attempt)
        except AccountExportStorageError:
            pass

        return {
            "reference": final_name,
            "sha256": sha256,
            "compressed_size_bytes": len(data),
            "uncompressed_size_bytes": uncompressed_size_bytes,
        }

    def cleanup_staging(self, job_key, attempt):
        """Delete one attempt's staging object, or prove it is already
        absent. Idempotent: safe to call any number of times, including
        when nothing was ever staged for this attempt."""

        self._delete(staging_blob_name(job_key, attempt))

    def cleanup_final(self, job_key):
        """Delete the final object, or prove it is already absent.

        This adapter has no state-machine awareness of its own. The
        caller (the worker script) must only reach this after C1's
        ledger has already moved the job past ``ready`` -- exactly what
        usp_CleanupAccountExportJob's own refusal-while-ready guard
        enforces on the database side.
        """

        self._delete(final_blob_name(job_key))

    def _delete(self, name):
        try:
            from azure.core.exceptions import ResourceNotFoundError

            try:
                self._client().delete_blob(name, delete_snapshots="include")
            except ResourceNotFoundError:
                return
        except AccountExportStorageError:
            raise
        except Exception as error:
            raise AccountExportStorageError("storage_delete_failed") from error


account_export_storage_service = AccountExportStorageService()
