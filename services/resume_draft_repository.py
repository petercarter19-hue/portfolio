"""Owner-scoped Resume draft persistence ports for MVP1 increment B.

In-memory stores are process-local and never a live database. The SQL adapter
names proposed procedures; schema application remains separately withheld.
Allowlisting a name is not engine proof.
"""

from __future__ import annotations

import copy
import json
import threading
from typing import Any, Protocol
from uuid import UUID

from services.database_service import DatabaseServiceError, database_service
from services.knowledge_service import KnowledgeService, KnowledgeServiceError
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
    return {"draft_version": 0, "base_publication_version": None, "story_entry_key": None, "items": {}, "receipts": {}}


class ResumeDraftStoreUnavailable(RuntimeError):
    """SQL draft port cannot run (unapplied schema, allowlist, or connection)."""


class ResumeDraftVersionConflict(RuntimeError):
    """The owner's draft changed before this command could apply.

    Raised by an atomic draft-store command when the stored version no longer
    matches the version the caller fenced. Nothing is written.
    """

    def __init__(self, current: int | None = None, expected: int | None = None):
        super().__init__("The draft changed before this command.")
        self.current = current
        self.expected = expected


class ResumeDraftIdempotencyConflict(RuntimeError):
    """One request id was already committed for different command semantics."""


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

    # Stores that carry more than one writer's state (the private editor text
    # commands and the Resume media commands share this draft) also expose
    # ``atomic_command_supported = True`` and
    # ``commit_owner_command(owner, expected_version=..., apply=...)``. The
    # store fences the exact expected version, runs ``apply(live)`` — which
    # returns False to make no change — and persists once. A store without that
    # contract may not carry shared media state; callers fail closed instead of
    # racing a whole-snapshot save.


class InMemoryResumeDraftRepository:
    """Process-local store. Never a live database and never shared across owners."""

    persistence_label = "in_memory_not_live_db"
    command_port = False
    # Single-process atomic command support: one lock per store instance, so
    # two services that share this store cannot both win the same version.
    # This is process-local only; it is not multi-process or durable safety.
    atomic_command_supported = True
    media_command_supported = True

    def __init__(self) -> None:
        self._owners: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        with self._lock:
            existing = self._owners.get(owner_user_key)
            if existing is None:
                return empty_draft_snapshot()
            return copy.deepcopy(existing)

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        with self._lock:
            stored = copy.deepcopy(snapshot)
            stored.pop("_pending_command", None)
            stored.pop("_base_version", None)
            self._owners[owner_user_key] = stored

    def commit_owner_command(
        self, owner_user_key: str, *, expected_version: int, apply: Any
    ) -> dict[str, Any]:
        """Atomically apply one fenced command to this owner's draft.

        The store owns the only lock, so every writer that shares this store —
        the editor's text commands and the Resume media commands — serializes
        here. The exact expected version is re-checked inside the lock, and the
        apply function runs before anything is persisted, so a conflict leaves
        the stored snapshot untouched.
        """

        with self._lock:
            existing = self._owners.get(owner_user_key)
            live = (
                copy.deepcopy(existing)
                if existing is not None
                else empty_draft_snapshot()
            )
            # The apply function checks for an exact confirmed replay first and
            # returns False for it, so an accepted command is never reported as
            # stale merely because the shared version moved on afterwards. Only
            # a real change must satisfy the version fence, and the caller's
            # mutations live on a private copy until the fence passes.
            current = int(live.get("draft_version") or 0)
            changed = apply(live)
            if changed is False:
                return copy.deepcopy(live)
            if current != int(expected_version):
                raise ResumeDraftVersionConflict(
                    current=current, expected=int(expected_version)
                )
            stored = copy.deepcopy(live)
            stored.pop("_pending_command", None)
            stored.pop("_base_version", None)
            self._owners[owner_user_key] = stored
            return copy.deepcopy(stored)


class SqlResumeDraftRepository:
    """Owner-scoped procedure adapter. Procedures are proposed, not applied."""

    persistence_label = "sql_proposed_unapplied"
    command_port = True
    # The proposed command procedure owns its transaction and re-fences the
    # exact expected draft version against the same resume_drafts row used by
    # the media procedure. The proposal remains unapplied/unproven, but this
    # adapter now truthfully implements the fenced callback contract.
    atomic_command_supported = True
    # This adapter persists text commands only. Media commands use
    # SqlResumeMediaDraftStore, whose procedure also fences authoritative media
    # sources; do not accept this store as the media command port merely because
    # both procedures coordinate through the shared draft row.
    media_command_supported = False

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
            selected_story = header.get("story_entry_key")
            normalized_story = _as_key(selected_story)
            if selected_story is not None and normalized_story is None:
                raise ResumeDraftStoreUnavailable("Resume Story reference is unavailable.")
            snapshot["story_entry_key"] = normalized_story
            receipts = header.get("command_receipts_json") or []
            if isinstance(receipts, str):
                try:
                    receipts = json.loads(receipts)
                except ValueError as error:
                    raise ResumeDraftStoreUnavailable(
                        "Resume drafts are unavailable."
                    ) from error
            if not isinstance(receipts, list):
                raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
            for receipt in receipts:
                if not isinstance(receipt, dict):
                    raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
                request_id = _as_key(receipt.get("request_id"))
                request_digest = str(receipt.get("request_digest") or "")
                if not request_id or len(request_digest) != 64:
                    raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
                snapshot["receipts"][request_id] = {
                    "request_digest": request_digest,
                    "outcome": str(receipt.get("outcome") or ""),
                }
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
            result_sets = self.commit_command(
                owner_user_key,
                pending["request_id"],
                pending["command_json"],
            )
            rows = result_sets[0] if result_sets else []
            if not rows:
                raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
            row = rows[0]
            outcome = str(row.get("outcome") or "")
            if outcome == "stale_draft":
                raise ResumeDraftVersionConflict(
                    current=row.get("current_draft_version"),
                    expected=row.get("expected_draft_version"),
                )
            if outcome == "idempotency_conflict":
                raise ResumeDraftIdempotencyConflict()
            if not bool(row.get("committed")):
                raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
            return
        raise ResumeDraftStoreUnavailable(
            "SQL resume-draft writes use usp_CommitResumeDraftCommandForOwner."
        )

    def commit_owner_command(
        self, owner_user_key: str, *, expected_version: int, apply: Any
    ) -> dict[str, Any]:
        """Apply locally, then let the procedure arbitrate replay/version.

        The Python callback only prepares the closed command. The procedure
        runs exact-replay arbitration before its locked version fence and owns
        the transaction, so the autocommit connection cannot split receipt,
        item, and shared-version changes. A fresh read supplies the committed
        result instead of reporting the speculative local copy as durable.
        """

        live = self.load_owner(owner_user_key)
        changed = apply(live)
        if changed is False:
            return live
        pending = live.get("_pending_command")
        if not isinstance(pending, dict):
            raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
        try:
            body = json.loads(str(pending.get("command_json") or ""))
        except (TypeError, ValueError) as error:
            raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.") from error
        if body.get("expected_draft_version") != int(expected_version):
            raise ResumeDraftStoreUnavailable("Resume drafts are unavailable.")
        self.save_owner(owner_user_key, live)
        return self.load_owner(owner_user_key)

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
    the entry-policy adapter when that read succeeds. Missing policy rows or an
    unavailable snapshot cannot authorize publication or review.
    """

    persistence_label = "living_resume_editor_sql"

    def __init__(self, editor=None, policy_repository=None, knowledge=None) -> None:
        self._editor: LivingResumeEditorService = editor or living_resume_editor_service
        self._policy = policy_repository
        self._knowledge = knowledge or KnowledgeService()

    def _policy_index(self, owner_user_key: str) -> dict[str, dict[str, Any]]:
        if self._policy is None:
            self._policy = SqlEntryPolicyRepository()
        rows: list[dict[str, Any]] = []
        if hasattr(self._policy, "list_entries"):
            try:
                payload = self._policy.list_entries(owner_user_key)
            except EntryPolicyStoreUnavailable:
                payload = []
            if isinstance(payload, dict):
                rows = list(payload.get("entries") or [])
            else:
                rows = list(payload or [])
        else:
            try:
                snapshot = self._policy.load_owner(owner_user_key)
            except EntryPolicyStoreUnavailable:
                snapshot = {}
            rows = list((snapshot.get("entries") or {}).values())
        index = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("entry_key") or "")
            if key:
                index[key] = row
        return index

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
                access = policy.get(key)
                access_revision = None
                content_version = None
                if isinstance(access, dict):
                    if access.get("access_revision") is not None:
                        try:
                            access_revision = int(access["access_revision"])
                        except (TypeError, ValueError):
                            access_revision = None
                    if access.get("content_version") is not None:
                        try:
                            content_version = int(access["content_version"])
                        except (TypeError, ValueError):
                            content_version = None
                items.append(
                    {
                        "record_key": key,
                        "record_type": record_type,
                        "content_token": str(row.get("row_version") or ""),
                        "access_revision": access_revision,
                        "content_version": content_version,
                        "editable": bool(row.get("editable")),
                        "blocked_reason": row.get("blocked_reason"),
                        "save_mode": save_mode_for_record(row),
                        "values": _row_values(row),
                        "resume_display": bool(access.get("resume_display")) if access else False,
                        "visitor_ai": bool(access.get("visitor_ai")) if access else False,
                        "private_assistance_excluded": bool(
                            access.get("private_assistance_excluded")
                        )
                        if access
                        else False,
                        "publication_eligible": access_revision is not None
                        and content_version is not None,
                    }
                )
        return items

    def list_items(self, owner_user_key: str) -> list[dict[str, Any]]:
        items = self._editor_items(owner_user_key)
        policy = self._policy_index(owner_user_key)
        try:
            listed = self._knowledge.list_knowledge_items_for_owner(owner_user_key)
            # Refuse an incomplete source snapshot; do not silently publish a
            # subset when the existing knowledge list reaches its bounded cap.
            if listed.total_count != len(listed.items):
                raise CanonicalReadUnavailable("Personal entries are unavailable.")
            for summary in listed.items:
                if summary["classification"] != "personal" or summary["status"] != "confirmed":
                    continue
                row = self._knowledge.get_knowledge_item_for_owner(owner_user_key, summary["item_key"])
                if (row["classification"] != "personal" or row["status"] != "confirmed"
                        or row["confirmed_version"] != row["current_version"]):
                    continue
                access = policy.get(row["item_key"])
                if access and (access.get("lifecycle") != "active" or access.get("canonical_type") != "knowledge"):
                    continue
                items.append({
                    "record_key": row["item_key"], "record_type": "knowledge",
                    "content_token": row["version_token"],
                    "content_version": access.get("content_version") if access else None,
                    "access_revision": access["access_revision"] if access else 0,
                    "editable": bool(access), "blocked_reason": None if access else "select_story_first",
                    "save_mode": "draft_overlay",
                    "values": {"title": row["title"], "wording": row["approved_wording"], "classification": "personal"},
                    "resume_display": bool(access and access.get("resume_display")),
                    "visitor_ai": bool(access and access.get("visitor_ai")),
                    "private_assistance_excluded": bool(access and access.get("private_assistance_excluded")),
                    # An unregistered record can be explicitly selected. Only
                    # the locked bind command may create its private policy row.
                    "publication_eligible": True,
                })
        except (KnowledgeServiceError, DatabaseServiceError, ValueError) as error:
            raise CanonicalReadUnavailable("Personal entries are unavailable.") from error
        return items

    def get_item(self, owner_user_key: str, record_key: str) -> dict[str, Any] | None:
        for item in self.list_items(owner_user_key):
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
