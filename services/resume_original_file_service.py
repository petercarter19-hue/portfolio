"""Recoverable owner-only original-file retention and deletion."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from services.resume_original_file_repository import (
    OriginalFileConflict, OriginalFileNotFound, OriginalFileUnavailable,
)
from services.resume_original_storage_service import ResumeOriginalStorageError


def present_original(row):
    # Paths, digests, provider identifiers and metadata ownership never become
    # member-visible references. Download uses the opaque SQL record key only.
    return {name: row.get(name) for name in (
        "original_key", "source_key", "version", "source_version", "content_type",
        "byte_length", "state", "downloadable", "created_at",
    )}


class ResumeOriginalFileService:
    def __init__(self, *, repository, storage):
        self.repository, self.storage = repository, storage

    def retain(self, owner, source, data):
        original = uuid4()
        path = "resume/v1/" + original.hex[:2] + "/" + original.hex
        digest = hashlib.sha256(data).hexdigest()
        if digest != source.get("sha256"):
            raise OriginalFileUnavailable()
        row = self.repository.command(owner, {
            "type": "reserve", "original_key": str(original),
            "source_key": source["source_key"], "source_version": source["version"],
            "blob_name": path, "sha256": digest, "byte_length": len(data),
            "content_type": source["content_type"],
        })
        # Ownership and immutable file integrity live in this dedicated row.
        # Once upload is confirmed, the member keeps access independently of
        # source parsing/commit/expiry/purge. Staged reservations stay visible
        # and member-deletable; no automatic cleanup implies deletion consent.
        try:
            etag = self.storage.upload(path, data, source["content_type"])
        except ResumeOriginalStorageError:
            raise OriginalFileUnavailable() from None
        try:
            current = self.repository.get(owner, row["original_key"])
            confirmed = self.repository.command(owner, {
                "type": "uploaded", "original_key": row["original_key"],
                "expected_version": current["version"], "blob_etag": etag,
            })
            if confirmed["state"] == "delete_pending":
                self._complete_member_delete(owner, confirmed)
        except (OriginalFileConflict, OriginalFileNotFound):
            # No upload replay. A concurrent delete keeps its durable path and
            # can confirm this completed create-only Blob through reconciliation.
            raise OriginalFileUnavailable() from None

    def list(self, owner):
        return [present_original(row) for row in self.repository.list(owner)]

    def download(self, owner, original_key):
        row = self.repository.get(owner, original_key)
        if not row["downloadable"] or row["state"] != "uploaded":
            raise OriginalFileNotFound()
        try:
            data = self.storage.read(
                row["blob_name"], etag=row["blob_etag"],
                byte_length=row["byte_length"], sha256=row["sha256"],
            )
        except ResumeOriginalStorageError:
            raise OriginalFileUnavailable() from None
        # Fence member file deletion or metadata change during the Blob read.
        # Parsed-source lifecycle never revokes retained original ownership.
        current = self.repository.get(owner, original_key)
        if (not current["downloadable"] or current["state"] != "uploaded"
                or current["version"] != row["version"]
                or current["source_version"] != row["source_version"]):
            raise OriginalFileNotFound()
        return data, row["content_type"]

    def delete(self, owner, original_key, *, expected_version, request_id):
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError("The current original file version is required.")
        try:
            request_id = str(UUID(str(request_id)))
            original_key = str(UUID(str(original_key)))
        except ValueError:
            raise ValueError("Invalid original file request.") from None
        row = self.repository.command(owner, {
            "type": "delete", "original_key": original_key,
            "expected_version": expected_version, "request_id": request_id,
        })
        if row["state"] == "deleted":
            return {"success": True, "outcome": "deleted", "original": present_original(row)}
        return self._complete_member_delete(owner, row)

    def _complete_member_delete(self, owner, row):
        try:
            if row.get("blob_etag") is None:
                etag = self.storage.confirm_upload(row["blob_name"],
                    byte_length=row["byte_length"], sha256=row["sha256"])
                row = self.repository.command(owner, {
                    "type": "uploaded", "original_key": row["original_key"],
                    "expected_version": row["version"], "blob_etag": etag,
                })
            self.storage.delete(row["blob_name"], etag=row["blob_etag"])
            row = self.repository.command(owner, {
                "type": "deleted", "original_key": row["original_key"],
                "expected_version": row["version"],
            })
        except (ResumeOriginalStorageError, OriginalFileUnavailable, OriginalFileConflict):
            return {
                "success": True, "outcome": "delete_pending",
                "original": present_original(row),
                "message": "The original is unavailable while deletion finishes. You can retry.",
            }
        return {"success": True, "outcome": "deleted", "original": present_original(row)}

    def reconcile(self, *, limit=25):
        # SQL admits only pending rows carrying durable explicit member-delete
        # intent. Draft expiry, source purge/absence, and reservation age never
        # create permission to delete an original or unconfirmed staged upload.
        completed, pending = 0, 0
        for row in self.repository.claim_cleanup(limit):
            try:
                etag = row.get("blob_etag") or self.storage.confirm_upload(
                    row["blob_name"], byte_length=row["byte_length"], sha256=row["sha256"])
                self.storage.delete(row["blob_name"], etag=etag)
                self.repository.complete_cleanup(row, etag)
                completed += 1
            except (ResumeOriginalStorageError, OriginalFileUnavailable):
                pending += 1
        return {"completed": completed, "pending": pending}
