"""Owner-scoped Resume draft persistence ports for MVP1 increment B.

In-memory stores are process-local and never a live database. The SQL adapter
names proposed procedures; schema application remains separately withheld.
Allowlisting a name is not engine proof.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Protocol
from uuid import UUID

from services.database_service import DatabaseServiceError, database_service
from services.entry_policy_repository import (
    EntryPolicyStoreUnavailable,
    SqlEntryPolicyRepository,
)
from services.living_resume_editor_service import (
    LivingResumeEditorConflictError,
    LivingResumeEditorNotFoundError,
    LivingResumeEditorService,
    LivingResumeEditorUnavailableError,
    LivingResumeEditorValidationError,
    SECTION_RECORD_TYPES,
    living_resume_editor_service,
    save_mode_for_record,
)


RESUME_DRAFT_BROWSER_PROCEDURES = frozenset(
    {
        "usp_CommitResumeDraftCommandForOwner",
        "usp_GetResumeDraftForOwner",
    }
)
RESUME_DRAFT_WORKER_PROCEDURES = frozenset()

_META_FIELDS = {
    "record_key",
    "row_version",
    "editable",
    "blocked_reason",
    "save_mode",
    "parent_key",
    "profile_key",
}


def _as_key(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def empty_draft_snapshot() -> dict[str, Any]:
    return {"draft_version": 0, "base_publication_version": None, "items": {}, "receipts": {}}


class ResumeDraftStoreUnavailable(RuntimeError):
    """SQL draft port cannot run (unapplied schema, allowlist, or connection)."""


class CanonicalReadUnavailable(RuntimeError):
    """Canonical editor source could not be read. Not a success."""


class CanonicalConflictError(Exception):
    def __init__(self, error_code: str, current=None, message="The record changed."):
        super().__init__(message)
        self.error_code = error_code
        self.current = current


class CanonicalValidationError(ValueError):
    pass


class ResumeDraftRepository(Protocol):
    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        """Return a mutable owner draft snapshot."""

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        """Replace that owner's draft snapshot atomically."""


class InMemoryResumeDraftRepository:
    """Process-local store. Never a live database and never shared across owners."""

    persistence_label = "in_memory_not_live_db"
    command_port = False

    def __init__(self) -> None:
        self._owners: dict[str, dict[str, Any]] = {}

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        existing = self._owners.get(owner_user_key)
        if existing is None:
            return empty_draft_snapshot()
        return copy.deepcopy(existing)

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        stored = copy.deepcopy(snapshot)
        stored.pop("_pending_command", None)
        self._owners[owner_user_key] = stored


class SqlResumeDraftRepository:
    """Owner-scoped procedure adapter. Procedures are proposed, not applied."""

    persistence_label = "sql_proposed_unapplied"
    command_port = True

    def __init__(self, database=None) -> None:
        self.database = database or database_service

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        try:
            result_sets = self.database.execute_procedure(
                "usp_GetResumeDraftForOwner",
                [("@UserKey", owner_user_key)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.") from error
        header_rows = result_sets[0] if result_sets else []
        item_rows = result_sets[1] if result_sets and len(result_sets) > 1 else []
        snapshot = empty_draft_snapshot()
        if header_rows:
            header = header_rows[0]
            snapshot["draft_version"] = int(header.get("draft_version") or 0)
            snapshot["base_publication_version"] = header.get("base_publication_version")
        for row in item_rows or []:
            key = _as_key(row.get("record_key"))
            if not key:
                continue
            proposed = row.get("proposed_values_json") or row.get("proposed_values") or {}
            if isinstance(proposed, str):
                proposed = json.loads(proposed)
            intended = row.get("intended_permission_expansions_json") or row.get(
                "intended_permission_expansions"
            )
            if isinstance(intended, str):
                intended = json.loads(intended)
            snapshot["items"][key] = {
                "record_key": key,
                "record_type": row.get("record_type"),
                "base_content_token": str(row.get("base_content_token") or ""),
                "base_access_revision": int(row.get("base_access_revision") or 1),
                "proposed_values": proposed,
                "intended_permission_expansions": intended,
                "is_new": bool(row.get("is_new")),
            }
        return snapshot

    def commit_command(
        self,
        owner_user_key: str,
        request_id: str,
        command_json: str | dict[str, Any],
    ) -> list:
        if isinstance(command_json, dict):
            payload = json.dumps(command_json, ensure_ascii=False, separators=(",", ":"))
        else:
            payload = command_json
        try:
            return self.database.execute_procedure(
                "usp_CommitResumeDraftCommandForOwner",
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", request_id),
                    ("@CommandJson", payload),
                ],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.") from error

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        pending = snapshot.get("_pending_command") if isinstance(snapshot, dict) else None
        if isinstance(pending, dict) and pending.get("request_id") and pending.get("command_json"):
            self.commit_command(
                owner_user_key,
                pending["request_id"],
                pending["command_json"],
            )
            return
        raise ResumeDraftStoreUnavailable(
            "SQL resume-draft writes use usp_CommitResumeDraftCommandForOwner."
        )


class InMemoryCanonicalCatalog:
    """Test catalog. Never a live database. Owners are isolated."""

    persistence_label = "in_memory_not_live_db"

    def __init__(self) -> None:
        self._owners: dict[str, dict[str, dict[str, Any]]] = {}

    def list_items(self, owner_user_key: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(item) for item in self._owners.get(owner_user_key, {}).values()]

    def get_item(self, owner_user_key: str, record_key: str) -> dict[str, Any] | None:
        item = self._owners.get(owner_user_key, {}).get(record_key)
        return copy.deepcopy(item) if item else None

    def put_item(self, owner_user_key: str, item: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(item)
        self._owners.setdefault(owner_user_key, {})[stored["record_key"]] = stored
        return copy.deepcopy(stored)

    def bump_content(self, owner_user_key: str, record_key: str) -> dict[str, Any]:
        item = self._owners[owner_user_key][record_key]
        token = item["content_token"]
        if token.isdigit():
            item["content_token"] = str(int(token) + 1)
        else:
            item["content_token"] = token[:-1] + ("b" if token.endswith("a") else "a")
        return copy.deepcopy(item)

    def bump_access(self, owner_user_key: str, record_key: str) -> dict[str, Any]:
        item = self._owners[owner_user_key][record_key]
        item["access_revision"] = int(item["access_revision"]) + 1
        item["resume_display"] = False
        item["visitor_ai"] = False
        return copy.deepcopy(item)

    def create_private(self, owner_user_key: str, item: dict[str, Any]) -> dict[str, Any]:
        key = item["record_key"]
        if key in self._owners.get(owner_user_key, {}):
            raise CanonicalConflictError("changed", current=self.get_item(owner_user_key, key))
        stored = {
            "record_key": key,
            "record_type": item["record_type"],
            "content_token": "1",
            "access_revision": 1,
            "editable": True,
            "blocked_reason": None,
            "save_mode": "canonical",
            "values": copy.deepcopy(item["values"]),
            "resume_display": False,
            "visitor_ai": False,
            "private_assistance_excluded": False,
        }
        return self.put_item(owner_user_key, stored)


def _row_values(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in _META_FIELDS}


class LivingResumeCanonicalCatalog:
    """Reads the existing private editor. Fail-closed when that source is down.

    This is not engine proof for proposed draft SQL. Access revisions come from
    the entry-policy adapter when that read succeeds; otherwise they default to 1.
    """

    persistence_label = "living_resume_editor_sql"

    def __init__(self, editor=None, policy_repository=None) -> None:
        self._editor: LivingResumeEditorService = editor or living_resume_editor_service
        self._policy = policy_repository

    def _policy_index(self, owner_user_key: str) -> dict[str, dict[str, Any]]:
        if self._policy is None:
            self._policy = SqlEntryPolicyRepository()
        try:
            snapshot = self._policy.load_owner(owner_user_key)
        except EntryPolicyStoreUnavailable:
            return {}
        return snapshot.get("entries") or {}

    def _editor_items(self, owner_user_key: str) -> list[dict[str, Any]]:
        try:
            editor = self._editor.get_editor(owner_user_key)
        except LivingResumeEditorNotFoundError:
            return []
        except LivingResumeEditorUnavailableError as error:
            raise CanonicalReadUnavailable("Canonical Resume records are unavailable.") from error
        policy = self._policy_index(owner_user_key)
        items = []
        for section, record_type in SECTION_RECORD_TYPES.items():
            rows = editor.get(section) or []
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = str(row["record_key"])
                access = policy.get(key) or {}
                items.append(
                    {
                        "record_key": key,
                        "record_type": record_type,
                        "content_token": str(row.get("row_version") or ""),
                        "access_revision": int(access.get("access_revision") or 1),
                        "editable": bool(row.get("editable")),
                        "blocked_reason": row.get("blocked_reason"),
                        "save_mode": save_mode_for_record(row),
                        "values": _row_values(row),
                        "resume_display": bool(access.get("resume_display", False)),
                        "visitor_ai": bool(access.get("visitor_ai", False)),
                        "private_assistance_excluded": bool(
                            access.get("private_assistance_excluded", False)
                        ),
                    }
                )
        return items

    def list_items(self, owner_user_key: str) -> list[dict[str, Any]]:
        return self._editor_items(owner_user_key)

    def get_item(self, owner_user_key: str, record_key: str) -> dict[str, Any] | None:
        for item in self._editor_items(owner_user_key):
            if item["record_key"] == record_key:
                return item
        return None

    def create_private(self, owner_user_key: str, item: dict[str, Any]) -> dict[str, Any]:
        type_map = {
            "role": "create_role",
            "education": "create_education",
            "credential": "create_credential",
            "skill": "create_skill",
            "accomplishment": "create_accomplishment",
        }
        command_type = type_map.get(item["record_type"])
        if command_type is None:
            raise CanonicalValidationError("This entry type cannot be created here.")
        payload = {
            "command_id": item["command_id"],
            "type": command_type,
            "record_key": item["record_key"],
            "parent_key": item.get("parent_key"),
            "expected_version": None,
            "values": item["values"],
        }
        try:
            result = self._editor.commit(owner_user_key, payload)
        except LivingResumeEditorValidationError as error:
            raise CanonicalValidationError(str(error)) from error
        except LivingResumeEditorConflictError as error:
            raise CanonicalConflictError(error.code, current=error.current) from error
        except (LivingResumeEditorUnavailableError, LivingResumeEditorNotFoundError) as error:
            raise CanonicalReadUnavailable("Canonical Resume records are unavailable.") from error
        created = self.get_item(owner_user_key, item["record_key"])
        if created is None and isinstance(result, dict) and result.get("current"):
            current = result["current"]
            created = {
                "record_key": item["record_key"],
                "record_type": item["record_type"],
                "content_token": str(current.get("row_version") or "1"),
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": _row_values(current) if isinstance(current, dict) else item["values"],
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            }
        if created is None:
            raise CanonicalReadUnavailable("Canonical Resume records are unavailable.")
        created["resume_display"] = False
        created["visitor_ai"] = False
        return created
