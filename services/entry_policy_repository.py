"""Owner-scoped persistence ports for MVP1 entry policy.

Canonical career and knowledge wording stays in those domains. This module
stores only the shared metadata/lifecycle/access contract plus an in-memory
adapter used by tests while proposed SQL remains unapplied.

Browser-facing procedure names are listed in ENTRY_POLICY_BROWSER_PROCEDURES.
They are not merged into services.database_service.ALLOWED_PROCEDURES in this
package: that exact-set lock lives in tests/test_database_service.py, which
this claim does not own. The SQL adapter therefore stays fail-closed against
the live allowlist. Schema application remains separately authorized.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Protocol

from services.database_service import DatabaseServiceError, database_service


ENTRY_POLICY_BROWSER_PROCEDURES = frozenset(
    {
        "usp_CommitEntryPolicyCommandForOwner",
        "usp_GetEntryPolicyEntryForOwner",
        "usp_ListEntryPolicyEntriesForOwner",
    }
)
ENTRY_POLICY_WORKER_PROCEDURES = frozenset(
    {
        "usp_SweepExpiredEntryPolicyForOwner",
    }
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EntryPolicyRepository(Protocol):
    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        """Return a mutable owner snapshot: entries, receipts, match_decisions."""

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        """Replace that owner's snapshot atomically."""


class InMemoryEntryPolicyRepository:
    """Process-local store. Never a live database and never shared across owners."""

    def __init__(self) -> None:
        self._owners: dict[str, dict[str, Any]] = {}

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        existing = self._owners.get(owner_user_key)
        if existing is None:
            return {"entries": {}, "receipts": {}, "match_decisions": {}}
        return copy.deepcopy(existing)

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        self._owners[owner_user_key] = copy.deepcopy(snapshot)


class SqlEntryPolicyRepository:
    """Owner-scoped procedure adapter. Procedures are proposed, not applied."""

    def __init__(self, database=None) -> None:
        self.database = database or database_service

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        try:
            rows = self.database.first_result(
                "usp_ListEntryPolicyEntriesForOwner",
                [("@UserKey", owner_user_key)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise EntryPolicyStoreUnavailable("Entry policy storage is unavailable.") from error
        entries = {}
        for row in rows or []:
            key = str(row["entry_key"])
            entries[key] = row
        return {"entries": entries, "receipts": {}, "match_decisions": {}}

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        raise EntryPolicyStoreUnavailable(
            "Entry policy SQL writes require a separately applied schema."
        )


class EntryPolicyStoreUnavailable(RuntimeError):
    """Raised when the SQL port cannot run (unapplied schema or allowlist)."""
