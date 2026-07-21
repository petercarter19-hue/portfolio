"""Derived private Journal reads and idempotent Save Moment writes.

Slice J1 (image-independent backend). The Journal has no separate content
table: it is a derived read over the existing private confirmed Moment and
Capture-source tables (see PS-MOMENT-001 / PS-CAPTURE-001). Save Moment is a
single idempotent commit of one Capture source and one confirmed canonical
Moment first version; it never publishes, places, or broadens audience, and
new Moments always default to private/Only Me.
"""

from __future__ import annotations

from services.database_service import database_service


DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100
_SAVE_OUTCOMES = {"success", "existing"}


class JournalServiceError(RuntimeError):
    """Raised when the Journal read/write contract cannot be honored."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class JournalService:
    def __init__(self, database=None):
        self.database = database or database_service

    def list_owner_journal(
        self, user_key, *, include_archived=False, limit=DEFAULT_LIST_LIMIT, cursor=None
    ):
        if not user_key:
            raise JournalServiceError("changed")

        bounded_limit = limit if isinstance(limit, int) and not isinstance(limit, bool) else DEFAULT_LIST_LIMIT
        bounded_limit = max(1, min(bounded_limit, MAX_LIST_LIMIT))
        clean_cursor = cursor.strip() if isinstance(cursor, str) and cursor.strip() else None

        rows = self.database.first_result(
            "usp_ListJournalMomentsForOwner",
            [
                ("@UserKey", user_key),
                ("@IncludeArchived", 1 if include_archived else 0),
                ("@Limit", bounded_limit),
                ("@Cursor", clean_cursor),
            ],
        )

        items = []
        next_cursor = None
        for row in rows or []:
            if not row:
                continue
            entry = dict(row)
            cursor_token = entry.get("cursor_token")
            moment_key = entry.get("moment_key")
            items.append(
                {
                    "moment_key": str(moment_key) if moment_key is not None else None,
                    "moment_kind": entry.get("moment_kind"),
                    "title": entry.get("title"),
                    "occurred_on": entry.get("occurred_on"),
                    "occurred_precision": entry.get("occurred_precision"),
                    "visibility": entry.get("visibility"),
                    "source_type": entry.get("source_type"),
                    "lifecycle_state": entry.get("lifecycle_state"),
                    "version_number": entry.get("version_number"),
                }
            )
            next_cursor = cursor_token

        # Only offer a next page when this page was fully populated; a
        # short page always means the owner's Journal is exhausted.
        if len(items) < bounded_limit:
            next_cursor = None

        return {"items": items, "next_cursor": next_cursor}

    def save_moment(self, user_key, idempotency_key, proposal):
        if not user_key or not idempotency_key:
            raise JournalServiceError("changed")
        if not isinstance(proposal, dict):
            raise JournalServiceError("changed")

        row = self.database.first_row(
            "usp_SaveMomentForOwner",
            [
                ("@UserKey", user_key),
                ("@IdempotencyKey", idempotency_key),
                ("@MomentKind", proposal.get("moment_kind")),
                ("@Title", proposal.get("title")),
                ("@OccurredOn", proposal.get("occurred_on")),
                ("@OccurredPrecision", proposal.get("occurred_precision")),
                ("@Narrative", proposal.get("narrative")),
                ("@WhyItMatters", proposal.get("why_it_matters")),
            ],
        )

        # Never report success without an exact Moment key: a missing or
        # unrecognized outcome, or a falsy key, is always a false-save guard.
        if (
            not row
            or row.get("outcome") not in _SAVE_OUTCOMES
            or not row.get("moment_key")
            or not row.get("version_number")
        ):
            raise JournalServiceError("changed")

        return {
            "moment_key": str(row["moment_key"]),
            "version": int(row["version_number"]),
            "saved": True,
        }


journal_service = JournalService()
