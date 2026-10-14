"""Closed owner-scoped entry policy and canonical coordination commands.

MVP1 increment A. Identity is always the server-derived user key. Clients send
opaque keys and expected versions only. New entries and new children default to
Resume display off, visitor AI off, and private assistance on unless excluded.
Direct corrections do not call an AI provider.

Proposed SQL stores one owner-composite canonical_key plus metadata, lifecycle,
and access revisions. It is not a second fact table. The in-memory repository
keeps adapter-owned values on the snapshot so commands can be exercised without
calling unclaimed career/knowledge modules. Schema application remains separate.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from services.entry_policy_repository import (
    EntryPolicyStoreUnavailable,
    SqlEntryPolicyRepository,
)
from services.living_resume_editor_service import utf16_length


COMMAND_TYPES = frozenset(
    {
        "create",
        "edit",
        "recategorize",
        "change_permissions",
        "delete",
        "restore",
        "permanently_delete",
        "resolve_match",
    }
)
CANONICAL_TYPES = frozenset(
    {
        "role",
        "education",
        "credential",
        "skill",
        "achievement",
        "project",
        "knowledge",
    }
)
CATEGORIES = frozenset(
    {
        "experience",
        "education",
        "credential",
        "skill",
        "achievement",
        "project",
        "personal",
    }
)
TYPE_CATEGORY = {
    "role": "experience",
    "education": "education",
    "credential": "credential",
    "skill": "skill",
    "achievement": "achievement",
    "project": "project",
    "knowledge": "personal",
}
PARENT_TYPES = frozenset({"role", "education", "credential", "project"})
CHILD_TYPES = frozenset({"achievement"})
MATCH_DECISIONS = frozenset(
    {"equivalent", "additional_detail", "contradiction", "distinct"}
)
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_DELETED = "deleted"
LIFECYCLE_PERMANENT = "permanently_deleted"
RECOVERY_DAYS = 30
MAX_TEXT = 8000
_UUID = re.compile(
    # SQL uniqueidentifier and the intake's stable SHA-derived identifiers use
    # all 128 bits. Preserve those existing keys; version/variant bits are not
    # owner authority. Keep the exact dashed hexadecimal representation.
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_FIELD_SETS = {
    "role": frozenset(
        {
            "role_title",
            "employer_name",
            "location_text",
            "summary",
            "start_date",
            "end_date",
            "date_precision",
            "employment_type",
            "current_role",
        }
    ),
    "education": frozenset(
        {
            "title",
            "institution_name",
            "degree_name",
            "field_of_study",
            "education_status",
            "grade_text",
            "location_text",
            "summary",
            "start_date",
            "end_date",
            "date_precision",
        }
    ),
    "credential": frozenset(
        {
            "credential_name",
            "issuer_name",
            "credential_identifier",
            "issue_date",
            "expiration_date",
            "issue_date_precision",
            "expiration_date_precision",
            "completion_status",
            "verification_url",
            "qualification_kind",
        }
    ),
    "skill": frozenset({"skill_name", "skill_summary"}),
    "achievement": frozenset({"wording", "metric_value", "metric_label"}),
    "project": frozenset(
        {
            "project_name",
            "project_role",
            "project_status",
            "project_url",
            "additional_project_urls",
            "project_category",
            "organization_name",
            "location_text",
            "summary",
            "start_date",
            "end_date",
            "date_precision",
        }
    ),
    "knowledge": frozenset({"title", "wording", "classification"}),
}
_REQUIRED_CREATE = {
    "role": ("role_title", "employer_name"),
    "education": ("title", "institution_name"),
    "credential": ("credential_name", "issuer_name"),
    "skill": ("skill_name",),
    "achievement": ("wording",),
    "project": ("project_name",),
    "knowledge": ("title", "wording"),
}


class EntryPolicyValidationError(ValueError):
    """Malformed closed-vocabulary input."""


class EntryPolicyConflictError(Exception):
    def __init__(self, error_code: str, conflicts=None, message="The record changed."):
        super().__init__(message)
        self.error_code = error_code
        self.conflicts = list(conflicts or [])


class EntryPolicyNotFoundError(Exception):
    """Neutral missing-or-foreign result. Never distinguishes another member."""


class EntryPolicyUnavailableError(Exception):
    """Storage or identity dependency is unavailable."""


def _as_uuid(value, *, field: str) -> str:
    if not isinstance(value, str) or not _UUID.fullmatch(value):
        raise EntryPolicyValidationError(f"Invalid {field}.")
    return str(UUID(value))


def _optional_uuid(value, *, field: str):
    if value is None:
        return None
    return _as_uuid(value, field=field)


def _json_digest(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require_int(value, *, field: str, allow_none=False):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EntryPolicyValidationError(f"Invalid {field}.")
    return value


def _require_bool(value, *, field: str):
    if not isinstance(value, bool):
        raise EntryPolicyValidationError(f"Invalid {field}.")
    return value


def _clean_text(value, *, field: str, required=False, maximum=MAX_TEXT):
    if value is None:
        if required:
            raise EntryPolicyValidationError(f"Invalid {field}.")
        return None
    if not isinstance(value, str):
        raise EntryPolicyValidationError(f"Invalid {field}.")
    text = value.strip()
    if required and not text:
        raise EntryPolicyValidationError(f"Invalid {field}.")
    if utf16_length(text) > maximum:
        raise EntryPolicyValidationError(f"Invalid {field}.")
    return text or None


def _normalize_values(canonical_type: str, values: object, *, required: bool, guide_review=False, section=None) -> dict:
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise EntryPolicyValidationError("Invalid values.")
    allowed = _FIELD_SETS[canonical_type]
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise EntryPolicyValidationError("Unknown value fields are not allowed.")
    forbidden = {
        "owner_user_key",
        "owner_profile_id",
        "visibility",
        "approval_status",
        "publication_status",
        "resume_display",
        "visitor_ai",
        "table",
    }
    if set(values) & forbidden:
        raise EntryPolicyValidationError("Authority fields cannot be client-supplied.")
    if guide_review and canonical_type in {"role", "knowledge"}:
        from services.living_resume_editor_service import normalize_guide_values, LivingResumeEditorValidationError
        try:
            return normalize_guide_values(canonical_type, values, section=section)
        except LivingResumeEditorValidationError as error:
            raise EntryPolicyValidationError(str(error)) from error
    local_project_fields = {"project_category", "organization_name", "additional_project_urls"}
    if (canonical_type == "credential" and "qualification_kind" in values) or (
            canonical_type == "project" and local_project_fields & set(values)):
        from services.living_resume_editor_service import (
            LivingResumeEditorValidationError, normalize_editor_intent, normalize_editor_values)
        aliases = {"credential_name": "name", "issuer_name": "issuer", "credential_identifier": "identifier"}
        supplied = {aliases.get(name, name) if canonical_type == "credential" else name: value
                    for name, value in values.items()}
        try:
            normalizer = normalize_editor_values if required else normalize_editor_intent
            result = normalizer(canonical_type, supplied)
        except LivingResumeEditorValidationError as error:
            raise EntryPolicyValidationError(str(error)) from error
        reverse = {value: name for name, value in aliases.items()} if canonical_type == "credential" else {}
        return {reverse.get(name, name): value for name, value in result.items()}
    required_fields = _REQUIRED_CREATE[canonical_type]
    if canonical_type == "education" and not str(values.get("title") or "").strip():
        # The local Guide's institution/year path carries no invented degree
        # or title. Existing titled education keeps its legacy validation.
        required_fields = ("institution_name", "end_date")
    normalized = {}
    for name in sorted(allowed):
        if name not in values:
            if required and name in required_fields:
                raise EntryPolicyValidationError(f"Invalid {name}.")
            continue
        raw = values[name]
        if name in {"current_role"}:
            normalized[name] = _require_bool(raw, field=name)
        elif name in {'issue_date_precision', 'expiration_date_precision'}:
            if raw is not None and (not isinstance(raw, str) or raw not in {'year', 'month', 'day'}):
                raise EntryPolicyValidationError('Invalid credential date detail.')
            if raw in {'year', 'month'}: normalized[name] = raw
        elif canonical_type == 'credential' and name == 'completion_status':
            if raw is not None and (not isinstance(raw, str) or raw not in {'planned', 'in_progress', 'completed'}):
                raise EntryPolicyValidationError('Invalid credential status.')
            if raw is not None: normalized[name] = raw
        else:
            need = required and name in required_fields
            normalized[name] = _clean_text(raw, field=name, required=need)
    if canonical_type == 'credential':
        from services.living_resume_editor_service import credential_date_text, LivingResumeEditorValidationError
        try:
            for name in ('issue_date', 'expiration_date'):
                precision = normalized.get(name + '_precision')
                if precision and not normalized.get(name):
                    raise EntryPolicyValidationError('Credential date detail needs its date.')
                if precision: credential_date_text(normalized.get(name), precision)
        except LivingResumeEditorValidationError as error:
            raise EntryPolicyValidationError(str(error)) from error
    if required:
        for name in required_fields:
            if not normalized.get(name):
                raise EntryPolicyValidationError(f"Invalid {name}.")
    if canonical_type == 'knowledge':
        from services.living_resume_editor_service import validate_guide_text_limits, LivingResumeEditorValidationError
        try:
            validate_guide_text_limits(normalized)
        except LivingResumeEditorValidationError as error:
            raise EntryPolicyValidationError(str(error)) from error
    return normalized


def _moment_text(now: datetime) -> str:
    """Render a snapshot timestamp as a JSON-safe UTC ISO string.

    Stored as text (not datetime) so owner snapshots survive JSON
    round-trips such as the SQL command log without custom encoders.
    """
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def _present_moment(value):
    """Render an optional lifecycle timestamp as a JSON-safe UTC ISO string.

    Snapshots built before a stamp existed carry None; datetimes render
    like recover_until; already-text values pass through untouched.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return moment.isoformat().replace("+00:00", "Z")
    text = str(value)
    return text or None


def _present(entry: dict, *, now: datetime) -> dict:
    recover_until = entry.get("recover_until")
    return {
        "entry_key": entry["entry_key"],
        "canonical_type": entry["canonical_type"],
        "category": entry["category"],
        "parent_key": entry.get("parent_key"),
        "content_version": entry["content_version"],
        "access_revision": entry["access_revision"],
        "resume_display": entry["resume_display"],
        "visitor_ai": entry["visitor_ai"],
        "private_assistance_excluded": entry["private_assistance_excluded"],
        "lifecycle": entry["lifecycle"],
        "created_at": entry.get("created_at"),
        "updated_at": entry.get("updated_at"),
        "deleted_at": _present_moment(entry.get("deleted_at")),
        "recover_until": recover_until.isoformat().replace("+00:00", "Z") if recover_until else None,
        "expired": bool(
            entry["lifecycle"] == LIFECYCLE_DELETED
            and recover_until is not None
            and now >= recover_until
        ),
        "values": dict(entry.get("values") or {}),
        "standalone": entry["canonical_type"] == "achievement" and entry.get("parent_key") is None,
    }


def _dependents(snapshot: dict, parent_key: str) -> list[str]:
    return sorted(
        key
        for key, entry in snapshot["entries"].items()
        if entry.get("parent_key") == parent_key
        and entry["lifecycle"] != LIFECYCLE_PERMANENT
    )


def _get_own(snapshot: dict, entry_key: str) -> dict:
    entry = snapshot["entries"].get(entry_key)
    if entry is None or entry["lifecycle"] == LIFECYCLE_PERMANENT:
        raise EntryPolicyNotFoundError("That item is no longer available.")
    return entry


class EntryPolicyService:
    def __init__(self, repository=None, clock=None, publication_service=None):
        self.repository = repository or SqlEntryPolicyRepository()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.publication_service = publication_service

    def list_entries(self, user_key: object) -> dict:
        return self._list_entries(user_key, persist_expiry=True)

    def read_entries(self, user_key: object) -> dict:
        """Project current policy without persisting expiry or modifying loaded state."""
        return self._list_entries(user_key, persist_expiry=False)

    def _list_entries(self, user_key: object, *, persist_expiry: bool) -> dict:
        owner = self._owner(user_key)
        now = self._now()
        if self._sql_command_port():
            visible = [
                _present(entry, now=now)
                for entry in self._list_sql(owner)
                if entry.get("lifecycle") != LIFECYCLE_PERMANENT
            ]
        else:
            from services.resume_intake_repository import resume_owner_guard
            with resume_owner_guard(owner):
                snapshot = self._load(owner)
                if not persist_expiry:
                    snapshot = copy.deepcopy(snapshot)
                if self._expire_snapshot(snapshot, now) and persist_expiry:
                    self._save(owner, snapshot)
            visible = [
                _present(entry, now=now)
                for entry in snapshot["entries"].values()
                if entry["lifecycle"] != LIFECYCLE_PERMANENT
            ]
        visible.sort(key=lambda item: item["entry_key"])
        return {
            "entries": visible,
            "capabilities": {
                "commands": sorted(COMMAND_TYPES),
                "canonical_types": sorted(CANONICAL_TYPES),
                "recovery_days": RECOVERY_DAYS,
                "ai_provider_required": False,
            },
        }

    def read_publication_entries(self, user_key: object) -> dict:
        """Use the existing publication SQL read or a non-persisting snapshot projection."""
        if not self._sql_command_port():
            return self.read_entries(user_key)
        return self.list_publication_entries(user_key)

    def list_publication_entries(self, user_key: object) -> dict:
        """Use the E canonical read when the SQL publication boundary is active."""

        if not self._sql_command_port():
            return self.list_entries(user_key)
        owner = self._owner(user_key)
        now = self._now()
        try:
            rows = self.repository.list_publication_entries(owner)
        except EntryPolicyStoreUnavailable as error:
            raise EntryPolicyUnavailableError("Entry policy is unavailable.") from error
        visible = [
            _present(entry, now=now)
            for entry in rows
            if entry.get("lifecycle") != LIFECYCLE_PERMANENT
        ]
        visible.sort(key=lambda item: item["entry_key"])
        return {"entries": visible}

    def get_entry(self, user_key: object, entry_key: object) -> dict:
        owner = self._owner(user_key)
        key = _as_uuid(entry_key, field="entry key")
        now = self._now()
        if self._sql_command_port():
            try:
                item = self.repository.get_entry(owner, key)
            except EntryPolicyStoreUnavailable as error:
                raise EntryPolicyUnavailableError("Entry policy is unavailable.") from error
            if item is None or item.get("lifecycle") == LIFECYCLE_PERMANENT:
                raise EntryPolicyNotFoundError("That item is no longer available.")
            return {"entry": _present(item, now=now)}
        from services.resume_intake_repository import resume_owner_guard
        with resume_owner_guard(owner):
            snapshot = self._load(owner)
            if self._expire_snapshot(snapshot, now):
                self._save(owner, snapshot)
        return {"entry": _present(_get_own(snapshot, key), now=now)}

    def commit(self, user_key: object, payload: object) -> dict:
        from services.resume_intake_repository import resume_owner_guard
        owner = self._owner(user_key)
        with resume_owner_guard(owner):
            return self._commit_guarded(owner, payload)

    def _commit_guarded(self, user_key: object, payload: object) -> dict:
        owner = self._owner(user_key)
        command = self._normalize_command(payload)
        now = self._now()
        if self._sql_command_port():
            values = command.get("values") or {}
            local_fields = {"qualification_kind", "project_category", "organization_name", "additional_project_urls"}
            title = values.get("title")
            title_missing = title is None or isinstance(title, str) and not title.strip()
            untitled = (command.get("canonical_type") == "education" and command["type"] == "create"
                        and title_missing) or (command["type"] == "edit" and "title" in values
                            and command.get("canonical_type") in {None, "education"} and title_missing)
            if command.get("guide_review") or local_fields & set(values) or untitled:
                raise EntryPolicyValidationError("This storage does not support these local Resume fields yet. Your input is kept.")
            if {'issue_date_precision', 'expiration_date_precision', 'completion_status'} & set(command.get('values') or {}):
                from services.living_resume_editor_service import CREDENTIAL_PRECISION_UNAVAILABLE
                raise EntryPolicyValidationError(CREDENTIAL_PRECISION_UNAVAILABLE)
            return self._commit_sql(owner, command, now)
        snapshot = self._load(owner)
        self._expire_snapshot(snapshot, now)
        existing = snapshot["receipts"].get(command["request_id"])
        if existing is not None:
            if existing["request_digest"] != command["digest"]:
                raise EntryPolicyConflictError(
                    "request_conflict",
                    [{"request_id": command["request_id"]}],
                    "That request already used a different payload.",
                )
            return {
                "receipt": dict(existing["receipt"]),
                "replayed": True,
                "entries": [_present(snapshot["entries"][key], now=now) for key in existing["affected"] if key in snapshot["entries"]],
            }
        before = copy.deepcopy(snapshot)
        try:
            affected, presented = self._apply(snapshot, command, now)
        except Exception:
            raise
        receipt = {
            "request_id": command["request_id"],
            "request_digest": command["digest"],
            "type": command["type"],
            "outcome": presented.get("outcome"),
        }
        snapshot["receipts"][command["request_id"]] = {
            "request_digest": command["digest"],
            "receipt": receipt,
            "affected": affected,
        }
        if self.publication_service is not None:
            from services.resume_publication_service import (
                PublicationConflictError as PublicationBoundaryConflict,
                PublicationDenied,
                PublicationValidationError,
            )
            try:
                self.publication_service.commit_linked_write(
                    owner, self.repository, before, snapshot, command
                )
            except PublicationBoundaryConflict as error:
                raise EntryPolicyConflictError(error.code) from error
            except PublicationDenied as error:
                raise EntryPolicyConflictError(getattr(error, "code", "denied")) from error
            except PublicationValidationError as error:
                raise EntryPolicyValidationError(str(error)) from error
        else:
            self._save(owner, snapshot)
        result = {"receipt": receipt, "replayed": False, "entries": presented["entries"]}
        if "match" in presented:
            result["match"] = presented["match"]
        return result

    def _sql_command_port(self) -> bool:
        return callable(getattr(self.repository, "commit_command", None))

    def _list_sql(self, owner: str) -> list:
        try:
            return list(self.repository.list_entries(owner) or [])
        except EntryPolicyStoreUnavailable as error:
            raise EntryPolicyUnavailableError("Entry policy is unavailable.") from error

    def _commit_sql(self, owner: str, command: dict, now: datetime) -> dict:
        try:
            result = self.repository.commit_command(owner, command["request_id"], command)
        except EntryPolicyStoreUnavailable as error:
            raise EntryPolicyUnavailableError("Entry policy is unavailable.") from error
        replayed = bool(result.get("replayed"))
        entries = []
        try:
            entries = [
                _present(item, now=now)
                for item in self._list_sql(owner)
                if item.get("lifecycle") != LIFECYCLE_PERMANENT
            ]
        except EntryPolicyUnavailableError:
            entries = []
        receipt = {
            "request_id": command["request_id"],
            "request_digest": result.get("request_digest") or command.get("digest"),
            "type": command["type"],
            "outcome": result.get("outcome"),
        }
        return {"receipt": receipt, "replayed": replayed, "entries": entries}

    def sweep_expired(self, user_key: object) -> dict:
        owner = self._owner(user_key)
        now = self._now()
        from services.resume_intake_repository import resume_owner_guard
        with resume_owner_guard(owner):
            snapshot = self._load(owner)
            expired = self._expire_snapshot(snapshot, now)
            self._save(owner, snapshot)
        return {"expired_count": expired}

    def _load(self, owner: str) -> dict:
        try:
            return self.repository.load_owner(owner)
        except EntryPolicyStoreUnavailable as error:
            raise EntryPolicyUnavailableError("Entry policy is unavailable.") from error

    def _save(self, owner: str, snapshot: dict) -> None:
        try:
            self.repository.save_owner(owner, snapshot)
        except EntryPolicyStoreUnavailable as error:
            raise EntryPolicyUnavailableError("Entry policy is unavailable.") from error

    def _apply(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        handler = {
            "create": self._create,
            "edit": self._edit,
            "recategorize": self._recategorize,
            "change_permissions": self._change_permissions,
            "delete": self._delete,
            "restore": self._restore,
            "permanently_delete": self._permanently_delete,
            "resolve_match": self._resolve_match,
        }[command["type"]]
        return handler(snapshot, command, now)

    def _create(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        canonical_type = command["canonical_type"]
        entry_key = command["entry_key"]
        if entry_key in snapshot["entries"]:
            raise EntryPolicyConflictError(
                "changed",
                [{"entry_key": entry_key}],
                "That entry already exists.",
            )
        parent_key = command["parent_key"]
        if canonical_type in CHILD_TYPES:
            if parent_key is not None:
                parent = snapshot["entries"].get(parent_key)
                if (
                    parent is None
                    or parent["lifecycle"] != LIFECYCLE_ACTIVE
                    or parent["canonical_type"] not in PARENT_TYPES
                ):
                    raise EntryPolicyNotFoundError("That item is no longer available.")
        elif parent_key is not None:
            raise EntryPolicyValidationError("This entry type cannot have a parent.")
        values = _normalize_values(canonical_type, command["values"], required=True,
            guide_review=command.get("guide_review", False), section=command.get("guide_section"))
        entry = {
            "entry_key": entry_key,
            "canonical_type": canonical_type,
            "category": command["category"] or TYPE_CATEGORY[canonical_type],
            "parent_key": parent_key,
            "content_version": 1,
            "access_revision": 1,
            "resume_display": False,
            "visitor_ai": False,
            "private_assistance_excluded": False,
            "lifecycle": LIFECYCLE_ACTIVE,
            "created_at": _moment_text(now),
            "updated_at": _moment_text(now),
            "deleted_at": None,
            "recover_until": None,
            "values": values,
        }
        snapshot["entries"][entry_key] = entry
        return [entry_key], {
            "outcome": "created",
            "entries": [_present(entry, now=now)],
        }

    def _edit(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        entry = _get_own(snapshot, command["entry_key"])
        if entry["lifecycle"] != LIFECYCLE_ACTIVE:
            raise EntryPolicyNotFoundError("That item is no longer available.")
        self._require_content_version(entry, command)
        section = command.get("guide_section")
        if command.get("guide_review") and entry["canonical_type"] == "knowledge":
            from services.resume_publication_projection import resume_section_for
            current = entry.get("values") or {}
            existing_section = resume_section_for("knowledge", current)
            if current.get("title") == "My Story":
                existing_section = "story"
            if existing_section in {"impact_statement", "story", "looking_ahead", "contact"}:
                section = existing_section
        values = _normalize_values(entry["canonical_type"], command["values"], required=True,
            guide_review=command.get("guide_review", False), section=section)
        entry["values"] = values
        entry["content_version"] += 1
        entry["updated_at"] = _moment_text(now)
        return [entry["entry_key"]], {
            "outcome": "updated",
            "entries": [_present(entry, now=now)],
        }

    def _recategorize(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        entry = _get_own(snapshot, command["entry_key"])
        if entry["lifecycle"] != LIFECYCLE_ACTIVE:
            raise EntryPolicyNotFoundError("That item is no longer available.")
        self._require_content_version(entry, command)
        category = command["category"]
        if category not in CATEGORIES:
            raise EntryPolicyValidationError("Invalid category.")
        entry["category"] = category
        entry["content_version"] += 1
        entry["updated_at"] = _moment_text(now)
        return [entry["entry_key"]], {
            "outcome": "recategorized",
            "entries": [_present(entry, now=now)],
        }

    def _change_permissions(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        targets = command["targets"]
        conflicts = []
        planned = []
        for item in targets:
            try:
                entry = _get_own(snapshot, item["entry_key"])
            except EntryPolicyNotFoundError:
                conflicts.append({"entry_key": item["entry_key"], "reason": "not_found"})
                continue
            if entry["lifecycle"] != LIFECYCLE_ACTIVE:
                conflicts.append({"entry_key": item["entry_key"], "reason": "not_found"})
                continue
            if entry["access_revision"] != item["expected_access_revision"]:
                conflicts.append(
                    {
                        "entry_key": item["entry_key"],
                        "reason": "changed",
                        "access_revision": entry["access_revision"],
                    }
                )
                continue
            planned.append((entry, item["permissions"]))
        if conflicts:
            raise EntryPolicyConflictError("changed", conflicts)
        affected = []
        presented = []
        for entry, permissions in planned:
            if "resume_display" in permissions:
                entry["resume_display"] = permissions["resume_display"]
            if "visitor_ai" in permissions:
                entry["visitor_ai"] = permissions["visitor_ai"]
            if "private_assistance_excluded" in permissions:
                entry["private_assistance_excluded"] = permissions[
                    "private_assistance_excluded"
                ]
            entry["access_revision"] += 1
            affected.append(entry["entry_key"])
            presented.append(_present(entry, now=now))
        return affected, {"outcome": "permissions_changed", "entries": presented}

    def _delete(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        entry = _get_own(snapshot, command["entry_key"])
        if entry["lifecycle"] != LIFECYCLE_ACTIVE:
            raise EntryPolicyNotFoundError("That item is no longer available.")
        self._require_content_version(entry, command)
        self._require_access_revision(entry, command)
        expected_dependents = command["dependent_keys"]
        actual = _dependents(snapshot, entry["entry_key"])
        expected = [] if expected_dependents is None else sorted(expected_dependents)
        if expected != actual:
            raise EntryPolicyConflictError(
                "scope_changed",
                [{"entry_key": entry["entry_key"], "dependents": actual}],
                "The dependent group changed.",
            )
        group = [entry["entry_key"], *actual]
        recover_until = now + timedelta(days=RECOVERY_DAYS)
        presented = []
        for key in group:
            member = snapshot["entries"][key]
            member["lifecycle"] = LIFECYCLE_DELETED
            member["deleted_at"] = now
            member["recover_until"] = recover_until
            member["resume_display"] = False
            member["visitor_ai"] = False
            member["access_revision"] += 1
            presented.append(_present(member, now=now))
        return group, {"outcome": "deleted", "entries": presented}

    def _restore(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        anchor = _get_own(snapshot, command["entry_key"])
        if command["group_keys"]:
            keys = command["group_keys"]
        else:
            recover_until = anchor.get("recover_until")
            keys = [
                key
                for key, member in snapshot["entries"].items()
                if member["lifecycle"] == LIFECYCLE_DELETED
                and member.get("recover_until") == recover_until
            ] or [command["entry_key"]]
        presented = []
        affected = []
        for key in keys:
            entry = snapshot["entries"].get(key)
            if entry is None or entry["lifecycle"] == LIFECYCLE_PERMANENT:
                raise EntryPolicyNotFoundError("That item is no longer available.")
            if entry["lifecycle"] != LIFECYCLE_DELETED:
                raise EntryPolicyValidationError("Only recently deleted entries can be restored.")
            if entry.get("recover_until") is not None and now >= entry["recover_until"]:
                self._erase(entry)
                raise EntryPolicyNotFoundError("That item is no longer available.")
            if key == command["entry_key"]:
                self._require_access_revision(entry, command)
            exclusion = entry["private_assistance_excluded"]
            entry["lifecycle"] = LIFECYCLE_ACTIVE
            entry["deleted_at"] = None
            entry["recover_until"] = None
            entry["resume_display"] = False
            entry["visitor_ai"] = False
            entry["private_assistance_excluded"] = exclusion
            entry["access_revision"] += 1
            affected.append(key)
            presented.append(_present(entry, now=now))
        return affected, {"outcome": "restored", "entries": presented}

    def _permanently_delete(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        entry = _get_own(snapshot, command["entry_key"])
        if entry["lifecycle"] != LIFECYCLE_DELETED:
            raise EntryPolicyValidationError("Permanent deletion requires a deleted entry.")
        self._require_access_revision(entry, command)
        keys = [entry["entry_key"], *_dependents(snapshot, entry["entry_key"])]
        for key in keys:
            self._erase(snapshot["entries"][key])
        return keys, {"outcome": "permanently_deleted", "entries": []}

    def _resolve_match(self, snapshot: dict, command: dict, now: datetime) -> tuple[list[str], dict]:
        entry = _get_own(snapshot, command["entry_key"])
        candidate = snapshot["entries"].get(command["candidate_key"])
        if (
            candidate is None
            or candidate["lifecycle"] != LIFECYCLE_ACTIVE
            or entry["lifecycle"] != LIFECYCLE_ACTIVE
        ):
            raise EntryPolicyNotFoundError("That item is no longer available.")
        self._require_content_version(entry, command)
        decision = command["match_decision"]
        if decision == "equivalent":
            adopted = dict(candidate.get("values") or {})
            # A truly identical duplicate stays quiet: the canonical values
            # are still adopted and the version still moves (established
            # contract), but updated_at only moves when the member's
            # resolution actually changes content. Otherwise Activity
            # would report a correction that never happened.
            if adopted != dict(entry.get("values") or {}):
                entry["updated_at"] = _moment_text(now)
            entry["values"] = adopted
            entry["content_version"] += 1
        elif decision == "additional_detail":
            merged = dict(entry.get("values") or {})
            merged.update(
                {
                    key: value
                    for key, value in (candidate.get("values") or {}).items()
                    if value not in (None, "")
                }
            )
            entry["values"] = merged
            entry["content_version"] += 1
            entry["updated_at"] = _moment_text(now)
        snapshot["match_decisions"][command["request_id"]] = {
            "entry_key": entry["entry_key"],
            "candidate_key": candidate["entry_key"],
            "decision": decision,
            "content_version": entry["content_version"],
        }
        return [entry["entry_key"]], {
            "outcome": "match_resolved",
            "entries": [_present(entry, now=now)],
            "match": {
                "candidate_key": candidate["entry_key"],
                "decision": decision,
            },
        }

    @staticmethod
    def _erase(entry: dict) -> None:
        entry["lifecycle"] = LIFECYCLE_PERMANENT
        entry["values"] = {}
        entry["resume_display"] = False
        entry["visitor_ai"] = False
        entry["deleted_at"] = None
        entry["recover_until"] = None
        entry["access_revision"] += 1

    def _expire_snapshot(self, snapshot: dict, now: datetime) -> int:
        expired = 0
        for entry in snapshot["entries"].values():
            if (
                entry["lifecycle"] == LIFECYCLE_DELETED
                and entry.get("recover_until") is not None
                and now >= entry["recover_until"]
            ):
                self._erase(entry)
                expired += 1
        return expired

    @staticmethod
    def _require_content_version(entry: dict, command: dict) -> None:
        expected = command["expected_content_version"]
        if expected is None or entry["content_version"] != expected:
            raise EntryPolicyConflictError(
                "changed",
                [
                    {
                        "entry_key": entry["entry_key"],
                        "content_version": entry["content_version"],
                    }
                ],
            )

    @staticmethod
    def _require_access_revision(entry: dict, command: dict) -> None:
        expected = command["expected_access_revision"]
        if expected is None or entry["access_revision"] != expected:
            raise EntryPolicyConflictError(
                "changed",
                [
                    {
                        "entry_key": entry["entry_key"],
                        "access_revision": entry["access_revision"],
                    }
                ],
            )

    def _normalize_command(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            raise EntryPolicyValidationError("Invalid command.")
        forbidden = {
            "owner_user_key",
            "owner_profile_id",
            "user_key",
            "table",
            "bypass",
        }
        if set(payload) & forbidden:
            raise EntryPolicyValidationError("Owner or table fields cannot be client-supplied.")
        guide_review = payload.get("guide_review", False)
        if type(guide_review) is not bool:
            raise EntryPolicyValidationError("Invalid Guide review choice.")
        if guide_review:
            from services.resume_publication_projection import RESUME_SECTION_LABELS
            if payload.get("type") not in {"create", "edit"} or (
                    payload.get("guide_section") is not None and payload["guide_section"] not in RESUME_SECTION_LABELS):
                raise EntryPolicyValidationError("Invalid Guide save.")
        command_type = payload.get("type")
        if command_type not in COMMAND_TYPES:
            raise EntryPolicyValidationError("Unknown command.")
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        entry_key = payload.get("entry_key")
        if command_type == "create":
            entry_key = _as_uuid(entry_key, field="entry key")
        else:
            entry_key = _as_uuid(entry_key, field="entry key")
        canonical_type = payload.get("canonical_type")
        if command_type == "create":
            if canonical_type not in CANONICAL_TYPES:
                raise EntryPolicyValidationError("Invalid canonical type.")
        elif canonical_type not in {None, *CANONICAL_TYPES}:
            raise EntryPolicyValidationError("Invalid canonical type.")
        category = payload.get("category")
        if category is not None and category not in CATEGORIES:
            raise EntryPolicyValidationError("Invalid category.")
        parent_key = _optional_uuid(payload.get("parent_key"), field="parent key")
        values = payload.get("values") if payload.get("values") is not None else {}
        if values is not None and not isinstance(values, dict):
            raise EntryPolicyValidationError("Invalid values.")
        permissions = payload.get("permissions")
        targets = payload.get("entries")
        if command_type == "change_permissions":
            if targets is None:
                if not isinstance(permissions, dict):
                    raise EntryPolicyValidationError("Invalid permissions.")
                targets = [
                    {
                        "entry_key": entry_key,
                        "expected_access_revision": payload.get("expected_access_revision"),
                        "permissions": permissions,
                    }
                ]
            if not isinstance(targets, list) or not targets:
                raise EntryPolicyValidationError("Invalid permission targets.")
            normalized_targets = []
            for item in targets:
                if not isinstance(item, dict):
                    raise EntryPolicyValidationError("Invalid permission targets.")
                perms = item.get("permissions")
                if not isinstance(perms, dict) or not perms:
                    raise EntryPolicyValidationError("Invalid permissions.")
                allowed = {"resume_display", "visitor_ai", "private_assistance_excluded"}
                if set(perms) - allowed:
                    raise EntryPolicyValidationError("Unknown permission fields are not allowed.")
                normalized_targets.append(
                    {
                        "entry_key": _as_uuid(item.get("entry_key"), field="entry key"),
                        "expected_access_revision": _require_int(
                            item.get("expected_access_revision"),
                            field="expected access revision",
                        ),
                        "permissions": {
                            name: _require_bool(perms[name], field=name) for name in perms
                        },
                    }
                )
        else:
            normalized_targets = []
        dependent_keys = payload.get("dependent_keys")
        if dependent_keys is not None:
            if not isinstance(dependent_keys, list):
                raise EntryPolicyValidationError("Invalid dependent keys.")
            dependent_keys = [_as_uuid(item, field="dependent key") for item in dependent_keys]
        group_keys = payload.get("group_keys")
        if group_keys is not None:
            if not isinstance(group_keys, list):
                raise EntryPolicyValidationError("Invalid group keys.")
            group_keys = [_as_uuid(item, field="group key") for item in group_keys]
        candidate_key = payload.get("candidate_key")
        match_decision = payload.get("match_decision")
        if command_type == "resolve_match":
            candidate_key = _as_uuid(candidate_key, field="candidate key")
            if match_decision not in MATCH_DECISIONS:
                raise EntryPolicyValidationError("Invalid match decision.")
        normalized = {
            "request_id": request_id,
            "type": command_type,
            "entry_key": entry_key,
            "canonical_type": canonical_type,
            "category": category,
            "parent_key": parent_key,
            "values": values,
            "expected_content_version": _require_int(
                payload.get("expected_content_version"),
                field="expected content version",
                allow_none=True,
            ),
            "expected_access_revision": _require_int(
                payload.get("expected_access_revision"),
                field="expected access revision",
                allow_none=True,
            ),
            "targets": normalized_targets,
            "dependent_keys": dependent_keys,
            "group_keys": group_keys,
            "candidate_key": candidate_key,
            "match_decision": match_decision,
        }
        if command_type in {"edit", "recategorize", "delete", "resolve_match"} and normalized["expected_content_version"] is None:
            raise EntryPolicyValidationError("Invalid expected content version.")
        if command_type in {"delete", "restore", "permanently_delete"} and normalized["expected_access_revision"] is None:
            raise EntryPolicyValidationError("Invalid expected access revision.")
        if command_type == "create":
            if normalized["expected_content_version"] is not None or normalized["expected_access_revision"] is not None:
                raise EntryPolicyValidationError("Create cannot include expected versions.")
        digest_body = {
            key: normalized[key]
            for key in (
                "request_id",
                "type",
                "entry_key",
                "canonical_type",
                "category",
                "parent_key",
                "values",
                "expected_content_version",
                "expected_access_revision",
                "targets",
                "dependent_keys",
                "group_keys",
                "candidate_key",
                "match_decision",
            )
        }
        if guide_review:
            guide_options = {"guide_review": True}
            if payload.get("guide_section") is not None:
                guide_options["guide_section"] = payload["guide_section"]
            normalized.update(guide_options)
            digest_body.update(guide_options)
        normalized["digest"] = _json_digest(digest_body)
        return normalized

    @staticmethod
    def _owner(user_key: object) -> str:
        if not isinstance(user_key, str) or not user_key.strip() or len(user_key) > 300:
            raise EntryPolicyUnavailableError("Owner identity is unavailable.")
        return user_key.strip()

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


entry_policy_service = EntryPolicyService()
