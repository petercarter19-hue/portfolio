"""Closed owner-qualified metadata commands for private Resume originals."""

from __future__ import annotations

import json
from uuid import UUID

from services.database_service import DatabaseService, DatabaseServiceError, database_service
from db import get_connection, fetch_all_result_sets
from services.resume_original_storage_service import require_etag, require_path, ORIGINAL_TYPES, MAX_ORIGINAL_BYTES


class OriginalFileUnavailable(RuntimeError):
    pass


class OriginalFileNotFound(RuntimeError):
    pass


class OriginalFileConflict(RuntimeError):
    pass


def map_original(row):
    try:
        result = dict(row)
        result["original_key"] = str(UUID(str(row["original_key"])))
        result["source_key"] = str(UUID(str(row["source_key"])))
        for field in ("version", "source_version", "byte_length"):
            if type(row[field]) is not int or row[field] < 1:
                raise ValueError()
        if row["byte_length"] > MAX_ORIGINAL_BYTES or row["content_type"] not in ORIGINAL_TYPES:
            raise ValueError()
        if row["state"] not in {"reserved", "uploaded", "delete_pending", "deleted"}:
            raise ValueError()
        digest = row["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(x not in "0123456789abcdef" for x in digest):
            raise ValueError()
        if row["state"] != "deleted":
            require_path(row["blob_name"])
        if row.get("blob_etag") is not None:
            require_etag(row["blob_etag"])
        if row.get("downloadable") not in (None, False, True, 0, 1):
            raise ValueError()
        result["downloadable"] = bool(row.get("downloadable"))
        return result
    except Exception:
        raise OriginalFileUnavailable("Original file metadata is unavailable.") from None


class SqlResumeOriginalCleanupAdapter:
    """Server composition only: two fixed commands, no procedure-name port.

    Reuse the application's connection and proved cursor timeout. Browser
    DatabaseService stays closed; member routes cannot select these commands.
    The caller confirms upload integrity and conditional deletion/absence
    before completing metadata CAS; unconfirmed absence keeps intent pending.
    """
    def __init__(self, *, connection_factory=None):
        self._connection_factory=connection_factory or get_connection

    def _execute(self, statement, values):
        if statement not in {
            "EXEC dbo.usp_ClaimResumeOriginalCleanup @Limit = ?",
            "EXEC dbo.usp_CompleteResumeOriginalCleanup @OriginalKey = ?, @ExpectedVersion = ?, @ConfirmedEtag = ?",
        }:raise ValueError("Invalid original cleanup command.")
        try:
            with self._connection_factory() as connection:
                cursor=DatabaseService._cursor(connection)
                try:
                    cursor.execute(statement,values)
                    sets=fetch_all_result_sets(cursor)
                    return sets[0] if sets else []
                finally:cursor.close()
        except Exception:
            raise OriginalFileUnavailable("Original deletion recovery is unavailable.") from None

    def claim(self, limit):
        if type(limit) is not int or not 1<=limit<=100:raise ValueError("Invalid cleanup bound.")
        return self._execute("EXEC dbo.usp_ClaimResumeOriginalCleanup @Limit = ?",(limit,))

    def complete(self, original_key, version, confirmed_etag):
        try:original_key=str(UUID(str(original_key)))
        except (ValueError,TypeError,AttributeError):raise ValueError("Invalid original key.") from None
        if type(version) is not int or version<1:raise ValueError("Invalid original version.")
        require_etag(confirmed_etag)
        return self._execute("EXEC dbo.usp_CompleteResumeOriginalCleanup @OriginalKey = ?, @ExpectedVersion = ?, @ConfirmedEtag = ?",
            (original_key,version,confirmed_etag))


class SqlResumeOriginalFileRepository:
    def __init__(self, database=None, *, cleanup=None):
        self.database = database or database_service
        self._cleanup = cleanup or SqlResumeOriginalCleanupAdapter()

    def list(self, owner, original_key=None):
        try:
            rows = self.database.first_result("usp_GetResumeOriginalFilesForOwner", [
                ("@UserKey", owner), ("@OriginalKey", original_key),
            ])
            if not isinstance(rows, list):
                raise ValueError()
            return [map_original(row) for row in rows]
        except (DatabaseServiceError, ValueError):
            raise OriginalFileUnavailable("Original file metadata is unavailable.") from None

    def get(self, owner, original_key):
        rows = self.list(owner, original_key)
        if not rows:
            raise OriginalFileNotFound()
        if len(rows) != 1:
            raise OriginalFileUnavailable()
        return rows[0]

    def command(self, owner, payload):
        try:
            sets = self.database.execute_procedure("usp_CommitResumeOriginalFileForOwner", [
                ("@UserKey", owner), ("@CommandJson", json.dumps(payload, separators=(",", ":"))),
            ])
            nonempty = [rows for rows in sets if rows]
            if not nonempty or len(nonempty[-1]) != 1:
                raise ValueError()
            row = nonempty[-1][0]
            if row.get("outcome") == "not_found":
                raise OriginalFileNotFound()
            if row.get("outcome") == "conflict":
                raise OriginalFileConflict()
            if row.get("outcome") != "ok":
                raise ValueError()
            return map_original(row)
        except (DatabaseServiceError, ValueError):
            raise OriginalFileUnavailable("Original file metadata is unavailable.") from None

    def claim_cleanup(self, limit=25):
        try:
            rows = self._cleanup.claim(limit)
            if not isinstance(rows, list) or len(rows) > limit:
                raise ValueError()
            return [map_original(row) for row in rows]
        except (DatabaseServiceError, ValueError):
            raise OriginalFileUnavailable() from None

    def complete_cleanup(self, row, confirmed_etag):
        try:
            rows = self._cleanup.complete(row["original_key"],row["version"],confirmed_etag)
            result = rows[0] if isinstance(rows,list) and len(rows)==1 else None
            if not isinstance(result, dict) or result.get("completed") not in (True, 1):
                raise ValueError()
        except (DatabaseServiceError, ValueError):
            raise OriginalFileUnavailable() from None
