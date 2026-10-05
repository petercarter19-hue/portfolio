"""Private Resume draft overlay and new-fact commands for MVP1 increment B.

Editor saves of existing records persist proposed values against the current
canonical content token and access revision. They never change already-shared
facts or restore revoked permissions. New unambiguous facts are created as
private canonical records (display off, visitor AI off). Review and preview
compute a digest and do not publish.

In-memory persistence is test-only. SQL adapters are fail-closed until a
separately authorized schema application. This service does not enable
production flags.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any
from uuid import UUID

from services.resume_publication_projection import resume_presentation_key

from services.living_resume_editor_service import (
    LivingResumeEditorValidationError,
    normalize_editor_values,
    utf16_length,
)
from services.resume_draft_repository import (
    CanonicalConflictError,
    CanonicalReadUnavailable,
    CanonicalValidationError,
    LivingResumeCanonicalCatalog,
    ResumeDraftStoreUnavailable,
    ResumeDraftIdempotencyConflict,
    ResumeDraftVersionConflict,
    SqlResumeDraftRepository,
    empty_draft_snapshot,
)


COMMAND_TYPES = frozenset(
    {"save_item", "discard_item", "create_private_item", "review_candidate", "bind_story", "clear_story"}
)
RECORD_TYPES = frozenset(
    {"role", "education", "credential", "skill", "accomplishment", "knowledge"}
)
FORBIDDEN_CLIENT_FIELDS = frozenset(
    {
        "owner_user_key",
        "owner_profile_id",
        "user_key",
        "table",
        "bypass",
        "visibility",
        "approval_status",
        "publication_status",
        "resume_display",
        "visitor_ai",
    }
)
MAX_TEXT = 8000


# PS-MVP1-INTAKE-GUIDE-001: an additive, best-effort commit observer. The
# composer registers one so a manual editor save/discard fences that record's
# still-pending intake references. Observers never change the editor command's
# own outcome, and an editor command never depends on them.
_COMMIT_OBSERVERS: list = []

# PS-MVP1-MEDIA-INTEGRATION-001: when Resume media placements are stored inside
# this same private draft snapshot, the store is marked here so a text command
# preserves the media state it did not author. A media command applies its own
# placement change to the live snapshot it fences, so neither surface can
# silently overwrite the other. Durable SQL keeps placements in dedicated
# tables fenced by this same draft version and does not set this marker.
SHARED_MEDIA_STATE_ATTRIBUTE = "resume_media_state_present"


def register_commit_observer(observer) -> None:
    if callable(observer) and observer not in _COMMIT_OBSERVERS:
        _COMMIT_OBSERVERS.append(observer)


def _notify_commit_observers(owner, command_type, record_key, result) -> None:
    for observer in list(_COMMIT_OBSERVERS):
        try:
            observer(owner, command_type, record_key, result)
        except Exception:  # noqa: BLE001 - an observer must never break a command
            continue


class ResumeDraftValidationError(ValueError):
    code = "invalid"


class ResumeDraftConflictError(Exception):
    def __init__(
        self,
        error_code: str,
        conflicts=None,
        message="The record changed.",
        proposed=None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.conflicts = list(conflicts or [])
        self.proposed = proposed
        self.code = error_code


class ResumeDraftNotFoundError(Exception):
    """Neutral missing-or-foreign result. Never distinguishes another member."""

    code = "not_found"


class ResumeDraftUnavailableError(Exception):
    def __init__(self, message="Resume drafts are unavailable.", proposed=None):
        super().__init__(message)
        self.proposed = proposed
        self.code = "unavailable"


def _json_digest(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _as_uuid(value, *, field: str) -> str:
    if not isinstance(value, str):
        raise ResumeDraftValidationError(f"Invalid {field}.")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as error:
        raise ResumeDraftValidationError(f"Invalid {field}.") from error
    return str(parsed)


def _require_int(value, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResumeDraftValidationError(f"Invalid {field}.")
    if value < 0:
        raise ResumeDraftValidationError(f"Invalid {field}.")
    return value


def _command_json(command: dict) -> str:
    body = {key: command[key] for key in command if key != "digest"}
    # The SQL command receipt must use the same normalized semantic digest as
    # the service's in-memory receipt. Hashing this transport JSON would be a
    # different contract (and would make every durable retry look changed).
    body["request_digest"] = command["digest"]
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _normalize_draft_values(record_type, values):
    if record_type != "knowledge":
        return normalize_editor_values(record_type, values)
    from services.knowledge_service import KnowledgeServiceError, validate_knowledge_item_input
    if not isinstance(values, dict) or set(values) - {"title", "wording", "classification"}:
        raise LivingResumeEditorValidationError("Check the personal entry fields.")
    try:
        title, wording, classification = validate_knowledge_item_input(
            values.get("title"), values.get("wording"), values.get("classification", "personal"))
    except KnowledgeServiceError as error:
        raise LivingResumeEditorValidationError(str(error)) from error
    return {"title": title, "wording": wording, "classification": classification}


class ResumeDraftService:
    def __init__(self, repository=None, catalog=None) -> None:
        self.repository = repository or SqlResumeDraftRepository()
        self.catalog = catalog or LivingResumeCanonicalCatalog()

    def _load(self, owner: str) -> dict:
        try:
            snapshot = self.repository.load_owner(owner)
        except ResumeDraftStoreUnavailable as error:
            raise ResumeDraftUnavailableError() from error
        if not snapshot:
            return empty_draft_snapshot()
        snapshot.setdefault("draft_version", 0)
        snapshot.setdefault("items", {})
        snapshot.setdefault("receipts", {})
        snapshot.setdefault("base_publication_version", None)
        snapshot.setdefault("story_entry_key", None)
        # Version this command is fenced against. The shared-draft atomic
        # command boundary re-checks it inside the store, so a text save and a
        # media save cannot both win the same version.
        snapshot["_base_version"] = int(snapshot["draft_version"])
        return snapshot

    def _save(self, owner: str, snapshot: dict, command: dict | None = None) -> bool:
        if command is not None:
            transport = dict(command)
            if transport.get("expected_draft_version") is None:
                transport["expected_draft_version"] = snapshot.get("_base_version", 0)
            if command.get("record_type") == "knowledge":
                if command["type"] == "create_private_item":
                    transport["values"] = _normalize_draft_values("knowledge", command["values"])
                elif command["type"] == "save_item":
                    transport["values"] = snapshot["items"][command["record_key"]]["proposed_values"]
            snapshot["_pending_command"] = {
                "request_id": command["request_id"],
                "command_json": _command_json(transport),
            }
        shares_media_state = getattr(self.repository, SHARED_MEDIA_STATE_ATTRIBUTE, False)
        if shares_media_state:
            # Media placements share this draft but are authored only by media
            # commands, so a text command may not save a whole snapshot: it
            # must apply only its own record/receipt change through the
            # store's atomic command boundary and leave media state (and every
            # other concurrent change) exactly as stored.
            return self._save_shared_draft(owner, snapshot, command)
        try:
            self.repository.save_owner(owner, snapshot)
        except ResumeDraftVersionConflict as error:
            raise ResumeDraftConflictError(
                "changed",
                [
                    {
                        "field": "draft_version",
                        "current": error.current,
                        "expected": error.expected,
                    }
                ],
                "The draft changed before this command.",
                proposed=(command or {}).get("values"),
            ) from error
        except ResumeDraftIdempotencyConflict as error:
            raise ResumeDraftConflictError(
                "idempotency_conflict",
                [{"request_id": (command or {}).get("request_id")}],
                "That request was already used for different content.",
                proposed=(command or {}).get("values"),
            ) from error
        except ResumeDraftStoreUnavailable as error:
            raise ResumeDraftUnavailableError(
                proposed=(command or {}).get("values")
            ) from error
        return False

    def _save_shared_draft(
        self, owner: str, snapshot: dict, command: dict | None
    ) -> bool:
        """Apply one text command through the shared draft's atomic boundary.

        Returns True only when the store proved this exact command was already
        committed and therefore wrote nothing new.
        """

        commit = getattr(self.repository, "commit_owner_command", None)
        if not callable(commit) or not getattr(
            self.repository, "atomic_command_supported", False
        ):
            # A store that carries shared media state but cannot fence and
            # apply one command atomically would let two writers overwrite each
            # other. Refuse rather than race.
            raise ResumeDraftUnavailableError(
                proposed=(command or {}).get("values")
            )
        expected_version = snapshot.get("_base_version")
        if expected_version is None:
            raise ResumeDraftUnavailableError(
                proposed=(command or {}).get("values")
            )
        record_key = command.get("record_key") if command else None
        pending = snapshot.get("_pending_command")
        receipt_keys = set((snapshot.get("receipts") or {}).keys())
        request_id = command.get("request_id") if command else None
        request_digest = command.get("digest") if command else None
        base_publication_version = snapshot.get("base_publication_version")
        # Preserve this command's own version behaviour exactly: some commands
        # (a private-record creation) deliberately do not advance the draft
        # version, so the store applies the observed delta rather than always
        # bumping by one.
        version_delta = int(snapshot.get("draft_version") or 0) - int(expected_version)
        replayed = False

        def apply(live: dict) -> bool:
            nonlocal replayed
            live_receipts = dict(live.get("receipts") or {})
            stored_receipt = (
                live_receipts.get(request_id) if request_id is not None else None
            )
            if stored_receipt is not None:
                # The receipt read that preceded this command ran before the
                # store's lock. Another writer can commit the same request in
                # that window: an exact replay must converge on the stored
                # success without another write, while the same request id
                # carrying different content is an idempotency conflict.
                if str(stored_receipt.get("request_digest") or "") != str(
                    request_digest or ""
                ):
                    raise ResumeDraftIdempotencyConflict()
                replayed = True
                return False
            live_items = dict(live.get("items") or {})
            if record_key:
                if record_key in (snapshot.get("items") or {}):
                    live_items[record_key] = copy.deepcopy(snapshot["items"][record_key])
                else:
                    live_items.pop(record_key, None)
            live["items"] = live_items
            if (command or {}).get("type") in {"bind_story", "clear_story"}:
                live["story_entry_key"] = snapshot.get("story_entry_key")
            for key in receipt_keys:
                live_receipts[key] = copy.deepcopy(snapshot["receipts"][key])
            live["receipts"] = live_receipts
            live["base_publication_version"] = base_publication_version
            live["draft_version"] = int(live.get("draft_version") or 0) + version_delta
            if isinstance(pending, dict):
                live["_pending_command"] = copy.deepcopy(pending)
            return True

        try:
            commit(
                owner,
                expected_version=int(expected_version),
                apply=apply,
            )
        except ResumeDraftVersionConflict as error:
            raise ResumeDraftConflictError(
                "changed",
                [
                    {
                        "field": "draft_version",
                        "current": error.current,
                        "expected": error.expected,
                    }
                ],
                "The draft changed before this command.",
                proposed=(command or {}).get("values"),
            ) from error
        except ResumeDraftIdempotencyConflict as error:
            raise ResumeDraftConflictError(
                "idempotency_conflict",
                [{"request_id": (command or {}).get("request_id")}],
                "That request was already used for different content.",
                proposed=(command or {}).get("values"),
            ) from error
        except ResumeDraftStoreUnavailable as error:
            raise ResumeDraftUnavailableError(
                proposed=(command or {}).get("values")
            ) from error
        return replayed

    def _catalog_list(self, owner: str) -> tuple[list[dict], str]:
        try:
            return self.catalog.list_items(owner), "ok"
        except CanonicalReadUnavailable:
            return [], "unavailable"

    def _catalog_get(self, owner: str, record_key: str) -> dict | None:
        try:
            return self.catalog.get_item(owner, record_key)
        except CanonicalReadUnavailable as error:
            raise ResumeDraftUnavailableError() from error

    def get_workspace(self, owner: str) -> dict:
        snapshot = self._load(owner)
        canonical_items, canonical_read = self._catalog_list(owner)
        overlays = snapshot["items"]
        merged = []
        seen = set()
        for item in canonical_items:
            key = item["record_key"]
            overlay = overlays.get(key)
            merged.append(self._present_item(item, overlay))
            seen.add(key)
        for key, overlay in overlays.items():
            if key in seen:
                continue
            merged.append(
                {
                    "record_key": key,
                    "record_type": overlay.get("record_type"),
                    "content_token": overlay.get("base_content_token"),
                    "access_revision": overlay.get("base_access_revision"),
                    "editable": False,
                    "save_mode": "draft_overlay",
                    "has_draft": True,
                    "orphaned": True,
                    "values": overlay.get("proposed_values") or {},
                    "proposed_values": overlay.get("proposed_values"),
                    "intended_permission_expansions": overlay.get(
                        "intended_permission_expansions"
                    ),
                    "resume_display": False,
                    "visitor_ai": False,
                    "draft_does_not_change_sharing": True,
                }
            )
        persistence = getattr(self.repository, "persistence_label", "unknown")
        return {
            "draft_version": snapshot["draft_version"],
            "base_publication_version": snapshot.get("base_publication_version"),
            "story_entry_key": snapshot.get("story_entry_key"),
            "items": sorted(merged, key=lambda item: resume_presentation_key(
                item.get("record_type"), {**(item.get("values") or {}), **(item.get("proposed_values") or {})})),
            "capabilities": {
                "commands": sorted(COMMAND_TYPES),
                "record_types": sorted(RECORD_TYPES),
                "publishes": False,
                "review_publishes": False,
                "preview_publishes": False,
                "canonical_read": canonical_read,
                "persistence": persistence,
                "persistence_is_live_database": False,
                "schema_applied": False,
            },
        }

    def command_digest(self, payload: object) -> str:
        """The canonical semantic digest for one draft command payload.

        The intake boundary stages a command the SQL callee replays by this
        digest, so it must equal the digest every other path computes from the
        same normalized command semantics (including the expected draft
        version and request id).
        """

        return self._normalize_command(payload)["digest"]

    def _present_item(self, item: dict, overlay: dict | None) -> dict:
        presented = {
            "record_key": item["record_key"],
            "record_type": item["record_type"],
            "content_token": item["content_token"],
            "access_revision": item["access_revision"],
            "editable": bool(item.get("editable")),
            "blocked_reason": item.get("blocked_reason"),
            "save_mode": item.get("save_mode")
            or ("canonical" if item.get("editable") else "draft_overlay"),
            "has_draft": overlay is not None,
            "orphaned": False,
            "values": item.get("values") or {},
            "proposed_values": (overlay or {}).get("proposed_values"),
            "intended_permission_expansions": (overlay or {}).get(
                "intended_permission_expansions"
            ),
            "resume_display": bool(item.get("resume_display")),
            "visitor_ai": bool(item.get("visitor_ai")),
            "private_assistance_excluded": bool(item.get("private_assistance_excluded")),
            "draft_does_not_change_sharing": True,
        }
        if overlay:
            presented["draft_base_content_token"] = overlay.get("base_content_token")
            presented["draft_base_access_revision"] = overlay.get("base_access_revision")
            stale = (
                overlay.get("base_content_token") != item["content_token"]
                or int(overlay.get("base_access_revision") or 1) != int(item["access_revision"])
            )
            presented["draft_is_stale"] = stale
        else:
            presented["draft_is_stale"] = False
        return presented

    def commit(self, owner: str, payload: object) -> dict:
        command = self._normalize_command(payload)
        if (command.get('record_type') == 'credential' and isinstance(self.repository, SqlResumeDraftRepository)
                and {'issue_date_precision', 'expiration_date_precision'} & set(command.get('values') or {})):
            from services.living_resume_editor_service import CREDENTIAL_PRECISION_UNAVAILABLE
            raise ResumeDraftValidationError(CREDENTIAL_PRECISION_UNAVAILABLE)
        try:
            snapshot = self._load(owner)
        except ResumeDraftUnavailableError as error:
            raise ResumeDraftUnavailableError(proposed=command.get("values")) from error
        existing = snapshot["receipts"].get(command["request_id"])
        if existing:
            if existing["request_digest"] != command["digest"]:
                raise ResumeDraftConflictError(
                    "idempotency_conflict",
                    [{"request_id": command["request_id"]}],
                    "That request was already used for different content.",
                    proposed=command.get("values"),
                )
            workspace = self.get_workspace(owner)
            return {
                "outcome": existing["outcome"],
                "replayed": True,
                "publishes": False,
                "request_digest": existing["request_digest"],
                "workspace": workspace,
                "item": existing.get("item"),
                "review_digest": existing.get("review_digest"),
                "proposed_values": command.get("values"),
            }
        if (
            command.get("expected_draft_version") is not None
            and command["expected_draft_version"] != snapshot["draft_version"]
        ):
            raise ResumeDraftConflictError(
                "changed",
                [
                    {
                        "field": "draft_version",
                        "current": snapshot["draft_version"],
                        "expected": command["expected_draft_version"],
                    }
                ],
                "The draft changed before this command.",
                proposed=command.get("values"),
            )
        handler = {
            "save_item": self._save_item,
            "discard_item": self._discard_item,
            "create_private_item": self._create_private_item,
            "review_candidate": self._review_candidate,
            "bind_story": self._bind_story,
            "clear_story": self._bind_story,
        }[command["type"]]
        result = handler(owner, snapshot, command)
        snapshot["receipts"][command["request_id"]] = {
            "request_digest": command["digest"],
            "outcome": result["outcome"],
            "item": result.get("item"),
            "review_digest": result.get("review_digest"),
        }
        replayed = False
        if command["type"] != "review_candidate":
            replayed = bool(self._save(owner, snapshot, command))
            _notify_commit_observers(owner, command["type"], command.get("record_key"), result)
        result["replayed"] = replayed
        result["publishes"] = False
        result["request_digest"] = command["digest"]
        result["workspace"] = self.get_workspace(owner)
        result.setdefault("proposed_values", command.get("values"))
        return result

    def _bind_story(self, owner: str, snapshot: dict, command: dict) -> dict:
        selected = None
        if command["type"] == "bind_story":
            canonical = self._catalog_get(owner, command["record_key"])
            if canonical is None or canonical.get("record_type") != "knowledge":
                raise ResumeDraftNotFoundError()
            effective = {**(canonical.get("values") or {}),
                         **((snapshot["items"].get(command["record_key"]) or {}).get("proposed_values") or {})}
            if effective.get("classification") != "personal":
                raise ResumeDraftValidationError("Choose a personal entry for My Story.")
            if (canonical.get("content_token") != command["expected_content_token"]
                    or canonical.get("access_revision") != command["expected_access_revision"]
                    or canonical.get("publication_eligible") is not True):
                raise ResumeDraftConflictError("changed", [], "That personal entry changed. Review it again.")
            selected = canonical["record_key"]
        snapshot["story_entry_key"] = selected
        snapshot["draft_version"] += 1
        return {"outcome": "story_selected" if selected else "story_removed", "item": None}

    def _save_item(self, owner: str, snapshot: dict, command: dict) -> dict:
        canonical = self._catalog_get(owner, command["record_key"])
        if canonical is None or canonical.get("record_type") != command["record_type"]:
            raise ResumeDraftNotFoundError()
        if canonical.get("record_type") == "knowledge" and not canonical.get("access_revision"):
            raise ResumeDraftValidationError("Select this personal entry for My Story before editing its Resume draft.")
        conflicts = []
        if str(canonical["content_token"]) != str(command["expected_content_token"]):
            conflicts.append(
                {
                    "record_key": command["record_key"],
                    "field": "content_token",
                    "current": canonical["content_token"],
                }
            )
        if int(canonical["access_revision"]) != int(command["expected_access_revision"]):
            conflicts.append(
                {
                    "record_key": command["record_key"],
                    "field": "access_revision",
                    "current": canonical["access_revision"],
                    "permissions_restored": False,
                }
            )
        if conflicts:
            raise ResumeDraftConflictError(
                "changed",
                conflicts,
                "That record changed before this save. Your wording is still here.",
                proposed=command["values"],
            )
        try:
            previous = snapshot['items'].get(command['record_key']) or {}
            previous_values = (previous.get('proposed_values') or {}) if (
                previous.get('base_content_token') == str(canonical['content_token'])
                and previous.get('base_access_revision') == int(canonical['access_revision'])) else {}
            merged = {**(canonical.get("values") or {}), **previous_values, **command["values"]}
            proposed = _normalize_draft_values(command["record_type"], merged)
        except LivingResumeEditorValidationError as error:
            raise ResumeDraftValidationError(str(error)) from error
        snapshot["items"][command["record_key"]] = {
            "record_key": command["record_key"],
            "record_type": command["record_type"],
            "base_content_token": str(canonical["content_token"]),
            "base_access_revision": int(canonical["access_revision"]),
            "proposed_values": proposed,
            "intended_permission_expansions": command.get("intended_permission_expansions"),
            "is_new": False,
        }
        snapshot["draft_version"] = int(snapshot["draft_version"]) + 1
        return {
            "outcome": "saved",
            "item": self._present_item(
                canonical, snapshot["items"][command["record_key"]]
            ),
        }

    def _discard_item(self, owner: str, snapshot: dict, command: dict) -> dict:
        overlay = snapshot["items"].pop(command["record_key"], None)
        if overlay is not None:
            snapshot["draft_version"] = int(snapshot["draft_version"]) + 1
        return {"outcome": "discarded", "item": None}

    def _create_private_item(self, owner: str, snapshot: dict, command: dict) -> dict:
        if command.get("parent_key") is not None:
            if self._catalog_get(owner, command["parent_key"]) is None:
                raise ResumeDraftNotFoundError()
        try:
            values = _normalize_draft_values(command["record_type"], command["values"])
        except LivingResumeEditorValidationError as error:
            raise ResumeDraftValidationError(str(error)) from error
        if command["record_type"] == "knowledge" and getattr(self.repository, "command_port", False):
            # The SQL command creates the existing versioned knowledge record,
            # private policy and receipt in one transaction. This is only a
            # proposed result until _save succeeds and the workspace is reread.
            return {"outcome": "created", "item": None}
        try:
            created = self.catalog.create_private(
                owner,
                {
                    "command_id": command["request_id"],
                    "record_key": command["record_key"],
                    "record_type": command["record_type"],
                    "parent_key": command.get("parent_key"),
                    "values": values,
                },
            )
        except CanonicalValidationError as error:
            raise ResumeDraftValidationError(str(error)) from error
        except CanonicalConflictError as error:
            raise ResumeDraftConflictError(
                error.error_code,
                [{"record_key": command["record_key"]}],
                str(error),
                proposed=command["values"],
            ) from error
        except CanonicalReadUnavailable as error:
            raise ResumeDraftUnavailableError(proposed=command["values"]) from error
        created["resume_display"] = False
        created["visitor_ai"] = False
        return {"outcome": "created", "item": self._present_item(created, None)}

    def _review_candidate(self, owner: str, snapshot: dict, command: dict) -> dict:
        conflicts = []
        for key, overlay in snapshot["items"].items():
            canonical = self._catalog_get(owner, key)
            if canonical is None:
                continue
            if str(overlay.get("base_content_token")) != str(canonical["content_token"]) or int(
                overlay.get("base_access_revision") or 1
            ) != int(canonical["access_revision"]):
                conflicts.append(
                    {
                        "record_key": key,
                        "field": "stale_draft",
                        "current": {
                            "content_token": canonical["content_token"],
                            "access_revision": canonical["access_revision"],
                            "resume_display": canonical.get("resume_display"),
                            "visitor_ai": canonical.get("visitor_ai"),
                        },
                        "proposed": overlay.get("proposed_values"),
                        "permissions_restored": False,
                    }
                )
        if conflicts:
            raise ResumeDraftConflictError(
                "changed",
                conflicts,
                "Review is blocked until stale drafts are reconciled. Proposed text is kept.",
                proposed=conflicts[0].get("proposed"),
            )
        workspace = {
            "draft_version": snapshot["draft_version"],
            "story_entry_key": snapshot.get("story_entry_key"),
            "items": snapshot["items"],
        }
        digest = _json_digest(workspace)
        return {
            "outcome": "reviewed",
            "review_digest": digest,
            "item": None,
            "message": "Review does not publish or change sharing.",
        }

    def _normalize_command(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            raise ResumeDraftValidationError("Invalid command.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeDraftValidationError("Owner or authority fields cannot be client-supplied.")
        command_type = payload.get("type")
        if command_type not in COMMAND_TYPES:
            raise ResumeDraftValidationError("Unknown command.")
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        record_type = payload.get("record_type")
        if command_type in {"save_item", "create_private_item"}:
            if record_type not in RECORD_TYPES:
                raise ResumeDraftValidationError("Invalid record type.")
        elif record_type not in {None, *RECORD_TYPES}:
            raise ResumeDraftValidationError("Invalid record type.")
        record_key = None
        if command_type not in {"review_candidate", "clear_story"}:
            record_key = _as_uuid(payload.get("record_key"), field="record key")
        values = payload.get("values") if payload.get("values") is not None else {}
        if values is not None and not isinstance(values, dict):
            raise ResumeDraftValidationError("Invalid values.")
        if isinstance(values, dict) and set(values) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeDraftValidationError("Authority fields cannot be client-supplied.")
        intended = payload.get("intended_permission_expansions")
        if intended is not None:
            if not isinstance(intended, dict) or not intended:
                raise ResumeDraftValidationError("Invalid intended permission expansions.")
            allowed = {"resume_display", "visitor_ai", "private_assistance_excluded"}
            if set(intended) - allowed:
                raise ResumeDraftValidationError("Unknown permission fields are not allowed.")
            for name, flag in intended.items():
                if flag is not True and flag is not False:
                    raise ResumeDraftValidationError("Invalid intended permission expansions.")
        parent_key = payload.get("parent_key")
        if parent_key is not None:
            parent_key = _as_uuid(parent_key, field="parent key")
        expected_draft_version = payload.get("expected_draft_version")
        if expected_draft_version is not None:
            expected_draft_version = _require_int(
                expected_draft_version, field="expected draft version"
            )
        expected_content_token = payload.get("expected_content_token")
        expected_access_revision = payload.get("expected_access_revision")
        if command_type in {"bind_story", "clear_story"} and expected_draft_version is None:
            raise ResumeDraftValidationError("The current draft version is required.")
        if command_type in {"save_item", "bind_story"}:
            if not isinstance(expected_content_token, str) or not expected_content_token:
                raise ResumeDraftValidationError("Invalid expected content token.")
            if utf16_length(expected_content_token) > 64:
                raise ResumeDraftValidationError("Invalid expected content token.")
            expected_access_revision = _require_int(
                expected_access_revision, field="expected access revision"
            )
        command = {
            "request_id": request_id,
            "type": command_type,
            "record_key": record_key,
            "record_type": record_type,
            "parent_key": parent_key,
            "values": values or {},
            "intended_permission_expansions": intended,
            "expected_draft_version": expected_draft_version,
            "expected_content_token": expected_content_token,
            "expected_access_revision": expected_access_revision,
        }
        command["digest"] = _json_digest(
            {key: command[key] for key in command if key != "digest"}
        )
        return command


resume_draft_service = ResumeDraftService()
