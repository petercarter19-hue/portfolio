"""Owner-scoped persistence ports for MVP1 entry policy.

Canonical career and knowledge wording stays in those domains. This module
stores only the shared metadata/lifecycle/access contract plus an in-memory
adapter used by tests while proposed SQL remains unapplied.

Browser-facing procedure names are listed in ENTRY_POLICY_BROWSER_PROCEDURES
and are allowlisted by PS-MVP1-RESUME-EDITOR-001. Allowlisting is not schema
application: snapshot replace stays fail-closed. Command and list adapters
still raise unavailable when the proposed procedures are not present. The
expiry-sweep worker procedure is deliberately not allowlisted.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol
from uuid import UUID

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


def _as_bool(value: object) -> bool:
    return value in (True, 1, "1", b"\x01")


def _as_key(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return str(value)


def map_entry_policy_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Map SQL list/get columns onto the Python snapshot vocabulary.

    Proposed SQL uses parent_entry_key and recover_until_utc. The in-memory
    service snapshot uses parent_key and recover_until.
    """

    if not isinstance(row, Mapping):
        raise EntryPolicyStoreUnavailable("Entry policy storage is unavailable.")
    parent = row.get("parent_entry_key", row.get("parent_key"))
    recover = row.get("recover_until_utc", row.get("recover_until"))
    return {
        "entry_key": _as_key(row.get("entry_key")),
        "canonical_type": row.get("canonical_type"),
        "canonical_key": _as_key(row.get("canonical_key")),
        "category": row.get("category"),
        "parent_key": _as_key(parent) if parent is not None else None,
        "content_version": int(row["content_version"]) if row.get("content_version") is not None else 1,
        "access_revision": int(row["access_revision"]) if row.get("access_revision") is not None else 1,
        "resume_display": _as_bool(row.get("resume_display")),
        "visitor_ai": _as_bool(row.get("visitor_ai")),
        "private_assistance_excluded": _as_bool(row.get("private_assistance_excluded")),
        "lifecycle": row.get("lifecycle") or "active",
        "recover_until": recover,
        "values": dict(row.get("values") or {}),
    }


map_sql_entry_row = map_entry_policy_row


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
    """Owner-scoped procedure adapter. Procedures are proposed, not applied.

    Snapshot replace is not the SQL contract. Command-shaped writes go through
    ``commit_command``. List/get mapping lives on ``map_entry_policy_row``.
    """

    def __init__(self, database=None) -> None:
        self.database = database or database_service

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        raise EntryPolicyStoreUnavailable(
            "Entry policy SQL snapshot load is unused; command and list "
            "procedures require a separately applied schema."
        )

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        pending = snapshot.get("_pending_command") if isinstance(snapshot, dict) else None
        if isinstance(pending, dict) and pending.get("request_id") and pending.get("command_json"):
            self.commit_command(
                owner_user_key,
                pending["request_id"],
                pending["command_json"],
            )
            return
        raise EntryPolicyStoreUnavailable(
            "SQL entry-policy writes use usp_CommitEntryPolicyCommandForOwner; "
            "pass a closed command on the adapter."
        )

    def list_entries(self, owner_user_key: str) -> list[dict[str, Any]]:
        try:
            rows = self.database.first_result(
                "usp_ListEntryPolicyEntriesForOwner",
                [("@UserKey", owner_user_key)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise EntryPolicyStoreUnavailable("Entry policy storage is unavailable.") from error
        return [map_entry_policy_row(row) for row in rows or []]

    def get_entry(self, owner_user_key: str, entry_key: str) -> dict[str, Any] | None:
        try:
            row = self.database.first_row(
                "usp_GetEntryPolicyEntryForOwner",
                [("@UserKey", owner_user_key), ("@EntryKey", entry_key)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise EntryPolicyStoreUnavailable("Entry policy storage is unavailable.") from error
        if row is None:
            return None
        return map_entry_policy_row(row)

    def commit_command(
        self,
        owner_user_key: str,
        request_id: str,
        command_json: str | dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(command_json, dict):
            payload = json.dumps(command_json, ensure_ascii=False, separators=(",", ":"))
        else:
            payload = command_json
        try:
            row = self.database.last_row(
                "usp_CommitEntryPolicyCommandForOwner",
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", request_id),
                    ("@CommandJson", payload),
                ],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise EntryPolicyStoreUnavailable("Entry policy storage is unavailable.") from error
        if not row:
            raise EntryPolicyStoreUnavailable("Entry policy storage is unavailable.")
        return {
            "committed": bool(row.get("committed")),
            "replayed": bool(row.get("replayed")),
            "outcome": row.get("outcome"),
            "request_digest": row.get("request_digest"),
        }


class EntryPolicyStoreUnavailable(RuntimeError):
    """Raised when the SQL port cannot run (unapplied schema or missing objects)."""
