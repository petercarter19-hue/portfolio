"""Owner recovery of removed Community posts and contributions.

Pete, 2026-08-03: members should be able to come back later and see what they
did. The approved retention schedule keeps a removed body for 30 days before
purging it; this reads and acts on that window so a mistaken removal is
recoverable rather than merely delayed.

Authorization is server-derived: every procedure resolves the author from the
caller's own user key and will not act on anyone else's record. This module
adds no new authority — it cannot restore something the retention rules have
already purged, something under legal hold, or something past the window.
"""

from __future__ import annotations

from services.community_contracts import (
    CommunityNotFoundError,
    CommunityUnavailableError,
    CommunityValidationError,
    opaque_key,
)
from services.community_retention_service import CONTENT_RETENTION_DAYS
from services.database_service import DatabaseServiceError, database_service


RESTORE_OUTCOMES = frozenset(
    {
        "restored",
        "existing",
        "not_found",
        "purged",
        "held",
        "expired",
        "parent_unavailable",
        # Moderation is not bypassed by a restore. Reporting "restored" for a
        # moderated record would be a lie the member could not see through:
        # every read filters moderation_state=clear, so nothing would appear.
        # Independent review, 2026-08-04, F11.
        "moderated",
    }
)


class CommunityRestoreService:
    def __init__(self, database=None):
        self.database = database or database_service

    def list_restorable(self, user_key):
        """Everything this author removed that can still be recovered."""
        try:
            rows = self.database.first_result(
                "usp_ListRestorableCommunityForOwner",
                [
                    ("@UserKey", user_key),
                    ("@RetentionDays", CONTENT_RETENTION_DAYS),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError(
                "Recently deleted is unavailable."
            ) from error
        return [self._present(row) for row in rows or []]

    def restore_post(self, user_key, post_key):
        return self._restore(
            "usp_RestorePublicCommunityPost",
            user_key,
            ("@PostKey", opaque_key(post_key, field="post key")),
        )

    def restore_contribution(self, user_key, contribution_key):
        return self._restore(
            "usp_RestorePublicCommunityContribution",
            user_key,
            (
                "@ContributionKey",
                opaque_key(contribution_key, field="contribution key"),
            ),
        )

    def _restore(self, procedure, user_key, key_parameter):
        try:
            row = self.database.first_row(
                procedure,
                [
                    ("@UserKey", user_key),
                    key_parameter,
                    ("@RetentionDays", CONTENT_RETENTION_DAYS),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Restore is unavailable.") from error
        outcome = (row or {}).get("outcome")
        if outcome not in RESTORE_OUTCOMES:
            raise CommunityUnavailableError("Restore is unavailable.")
        if outcome == "not_found":
            # Never distinguish "someone else's record" from "no such record".
            raise CommunityNotFoundError("That item is no longer available.")
        return outcome

    @staticmethod
    def _present(row):
        """Shape one row for the page. No identifiers beyond the opaque key."""
        body = (row.get("body") or "").strip()
        return {
            "record_key": str(row.get("record_key")),
            "record_kind": row.get("record_kind"),
            "excerpt": body[:280],
            "truncated": len(body) > 280,
            "deleted_on": _readable_date(row.get("deleted_at_utc")),
            "recoverable_until": _readable_date(row.get("restorable_until_utc")),
        }


def _readable_date(value):
    """Format a date for the page without platform-specific directives.

    strftime('%-d') is POSIX-only and raises on Windows, so the day is
    interpolated directly rather than via a format code.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return f"{value:%B} {value.day}, {value.year}"
    except (TypeError, ValueError):
        return ""


community_restore_service = CommunityRestoreService()
