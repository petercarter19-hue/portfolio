"""Owner-scoped Resume publication persistence.

The SQL adapter names one complete command procedure. In-memory storage is
test-only and never a live database. Schema application remains withheld.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any


PUBLICATION_BROWSER_PROCEDURES = frozenset(
    {
        "usp_CommitResumePublicationCommandForOwner",
        "usp_GetResumePublicationForOwner",
        "usp_GetResumePublicationReceiptForOwner",
        "usp_GetPublicResumePublicationBySlug",
        "usp_GetResumePublicationMediaAuthorization",
        "usp_ListResumePublicationPolicyForOwner",
        "usp_GetResumeCatalogAsset",
        "usp_CommitResumeCatalogCommandForOwner",
    }
)
PUBLICATION_INTERNAL_PROCEDURES = frozenset(
    {
        "usp_ResumePublicationApplyCanonicalInternal",
        "usp_ResumePublicationRefreshProjectionInternal",
        "usp_ResumePublicationEncodeSourceInternal",
        "usp_ResumePublicationLockOwnerInternal",
        "usp_ResumePublicationBuildManifestsInternal",
        "usp_ResumePublicationGuardLegacyMutator",
        "usp_ResumePublicationApplyAfterPolicyInternal",
    }
)


class PublicationStoreUnavailable(RuntimeError):
    """Raised when publication storage cannot run."""


class PublicationConflictError(RuntimeError):
    def __init__(self, code: str, message: str = "The publication changed.") -> None:
        super().__init__(message)
        self.code = code


def _is_sql_adapter_error(error: BaseException) -> bool:
    if isinstance(error, ValueError):
        return True
    if type(error).__name__ == "DatabaseServiceError":
        return True
    try:
        from services.database_service import DatabaseServiceError
    except Exception:
        return False
    return isinstance(error, DatabaseServiceError)


def _sql_error_texts(error: BaseException):
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts = [str(current)]
        parts.extend(str(item) for item in getattr(current, "args", ()) if item is not None)
        for name in ("sqlstate", "code", "number"):
            value = getattr(current, name, None)
            if value is not None:
                parts.append(str(value))
        yield " ".join(parts)
        current = current.__cause__ or getattr(current, "__context__", None)


def _is_stale_publication(error: BaseException) -> bool:
    return any("54023" in text or "the publication changed" in text.lower() for text in _sql_error_texts(error))


def _is_invalid_correction_target(error: BaseException) -> bool:
    correction_codes = {"54026", "54027", "54028", "54029"}
    texts = tuple(_sql_error_texts(error))
    reported_codes = {
        match.group(0)
        for text in texts
        for match in re.finditer(r"(?<!\d)54\d{3}(?!\d)", text)
    }
    if reported_codes:
        return reported_codes <= correction_codes
    server_messages = (
        "entry is unavailable.",
        "expected content and access versions are required.",
        "entry is not active.",
        "canonical source did not change.",
    )
    for text in texts:
        # mssql-python may expose the SQL Server THROW message without its
        # number. Match only these exact server-originated correction messages.
        for fragment in text.lower().split("[sql server]")[1:]:
            if any(fragment.lstrip().startswith(message) for message in server_messages):
                return True
    return False


def _raise_commit_error(error: BaseException) -> None:
    if any("54302" in text or "profile identity changed" in text.lower() for text in _sql_error_texts(error)):
        raise PublicationConflictError("stale_identity", "Profile identity changed. Review it again.") from error
    if _is_receipt_conflict(error):
        raise PublicationConflictError(
            "request_conflict",
            "That request already used a different payload.",
        ) from error
    if _is_stale_publication(error):
        raise PublicationConflictError("stale_publish", "The publication changed.") from error
    if _is_invalid_correction_target(error):
        raise PublicationDenied("denied", "Correction target is unavailable.") from error
    raise PublicationStoreUnavailable("Publication storage is unavailable.") from error


def _is_receipt_conflict(error: BaseException) -> bool:
    """True when SQL THROW 54022 is wrapped, including DatabaseServiceError.__cause__."""

    for text in _sql_error_texts(error):
        lowered = text.lower()
        if "54022" in text or "already used a different payload" in lowered:
            return True
    return False


class PublicationDenied(RuntimeError):
    def __init__(self, code: str, message: str = "Publication is unavailable.") -> None:
        super().__init__(message)
        self.code = code


def empty_publication_snapshot() -> dict[str, Any]:
    return {
        "sharing_enabled": False,
        "sharing_epoch": 0,
        "publication_revision": 0,
        "current_revision": None,
        "slug": None,
        "publications": {},
        "receipts": {},
        "revoked_media": set(),
        "read_epoch": 0,
    }


def _media_from_owner_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if "media_json" not in row:
        return None
    raw = row.get("media_json")
    if raw is None:
        return None
    if isinstance(raw, dict):
        media = raw
    elif isinstance(raw, str):
        if not raw.strip():
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        media = parsed
    else:
        return None
    normalized = {}
    for slot, item in media.items():
        if not isinstance(item, dict):
            continue
        slot_state = dict(item)
        active = slot_state.get("active")
        if active in (1, "1", True, "true"):
            slot_state["active"] = True
        elif active in (0, "0", False, "false"):
            slot_state["active"] = False
        normalized[str(slot)] = slot_state
    return normalized


class InMemoryResumePublicationRepository:
    def __init__(self) -> None:
        self._owners: dict[str, dict[str, Any]] = {}

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        existing = self._owners.get(owner_user_key)
        if existing is None:
            return empty_publication_snapshot()
        return copy.deepcopy(existing)

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        self._owners[owner_user_key] = copy.deepcopy(snapshot)


class SqlResumePublicationRepository:
    def __init__(self, database=None) -> None:
        if database is None:
            from services.database_service import database_service as default_database

            database = default_database
        self.database = database

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        row = self.get_owner_publication(owner_user_key)
        if not row:
            return empty_publication_snapshot()
        revision = row.get("current_revision")
        if revision is not None:
            revision = int(revision)
        media = _media_from_owner_row(row)
        publications = {}
        if revision is not None and media is not None:
            publications[revision] = {
                "media": media,
                "digest": row.get("reviewed_digest"),
                "profile_identity": self._identity_reference(row.get("profile_identity_json")),
            }
        return {
            "sharing_enabled": bool(row.get("sharing_enabled")),
            "sharing_epoch": int(row.get("sharing_epoch") or 0),
            "publication_revision": int(row.get("publication_revision") or 0),
            "current_revision": revision,
            "slug": row.get("public_slug"),
            "publications": publications,
            "receipts": {},
            "revoked_media": set(),
            "read_epoch": int(row.get("sharing_epoch") or 0),
        }

    @staticmethod
    def _identity_reference(raw):
        if raw is None:
            return None
        from services.mvp1_profile_binding import identity_reference
        try:
            parsed = json.loads(raw) if type(raw) is str else raw
            ref = identity_reference(parsed)
            return ref.to_payload() if ref else None
        except (TypeError, ValueError):
            # A corrupt optional identity never supplies a public name.
            return None

    def get_receipt(self, owner_user_key: str, request_id: str) -> dict[str, Any] | None:
        try:
            row = self.database.first_row(
                "usp_GetResumePublicationReceiptForOwner",
                [("@UserKey", owner_user_key), ("@RequestId", request_id)],
            )
        except Exception as error:
            if not _is_sql_adapter_error(error):
                raise
            raise PublicationStoreUnavailable("Publication storage is unavailable.") from error
        if not row or not isinstance(row, dict):
            return None
        return {
            "request_digest": row.get("request_digest"),
            "receipt": {
                "request_id": str(row.get("request_id") or request_id),
                "request_digest": row.get("request_digest"),
                "type": row.get("command_type"),
                "outcome": row.get("outcome"),
                "publication_revision": row.get("publication_revision"),
            },
        }

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        raise PublicationStoreUnavailable(
            "SQL publication writes use usp_CommitResumePublicationCommandForOwner; "
            "snapshot replace is test-only."
        )

    def commit_command(
        self,
        owner_user_key: str,
        request_id: str,
        command_json: dict[str, Any] | str,
    ) -> dict[str, Any]:
        try:
            row = self.database.last_row(
                "usp_CommitResumePublicationCommandForOwner",
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", request_id),
                    ("@CommandJson", command_json),
                ],
            )
        except Exception as error:
            if not _is_sql_adapter_error(error):
                raise
            _raise_commit_error(error)
            raise PublicationStoreUnavailable("Publication storage is unavailable.") from error
        if not row:
            raise PublicationStoreUnavailable("Publication storage is unavailable.")
        return {
            "committed": bool(row.get("committed")),
            "replayed": bool(row.get("replayed")),
            "outcome": row.get("outcome"),
            "request_digest": row.get("request_digest"),
            "read_state": row.get("read_state"),
            "publication_revision": row.get("publication_revision"),
        }

    def get_owner_publication(self, owner_user_key: str) -> dict[str, Any] | None:
        try:
            row = self.database.first_row(
                "usp_GetResumePublicationForOwner",
                [("@UserKey", owner_user_key)],
            )
        except Exception as error:
            if not _is_sql_adapter_error(error):
                raise
            raise PublicationStoreUnavailable("Publication storage is unavailable.") from error
        return dict(row) if row else None

    def get_public_by_slug(self, slug: str) -> dict[str, Any] | None:
        try:
            row = self.database.first_row(
                "usp_GetPublicResumePublicationBySlug",
                [("@ProfileSlug", slug)],
            )
        except Exception as error:
            if not _is_sql_adapter_error(error):
                raise
            if any("54030" in text or "publication is unavailable" in text.lower()
                   for text in _sql_error_texts(error)):
                raise PublicationDenied("denied", "Publication is unavailable.") from error
            raise PublicationStoreUnavailable("Publication storage is unavailable.") from error
        return dict(row) if row else None

    def authorize_media(self, slug: str, slot: str, revision: int | None) -> dict[str, Any]:
        try:
            row = self.database.first_row(
                "usp_GetResumePublicationMediaAuthorization",
                [
                    ("@ProfileSlug", slug),
                    ("@Slot", slot),
                    ("@PublicationRevision", revision),
                ],
            )
        except Exception as error:
            if not _is_sql_adapter_error(error):
                raise
            if any(any(code in text for code in ("54031", "54032", "54033", "54034"))
                   or "media is unavailable" in text.lower()
                   for text in _sql_error_texts(error)):
                raise PublicationDenied("denied", "Media is unavailable.") from error
            raise PublicationStoreUnavailable("Publication storage is unavailable.") from error
        if not row or not row.get("authorized"):
            raise PublicationDenied("denied", "Media is unavailable.")
        return dict(row)
