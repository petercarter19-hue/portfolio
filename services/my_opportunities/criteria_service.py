"""Owner-scoped C3 criteria state machine for My Opportunities.

The service is intentionally route-free and provider-neutral.  AI may propose
only through ``InterpretationService``; this module alone validates and writes
drafts, rotates tokens, freezes applied snapshots, and emits terminal receipts.
It allocates an execution key on Apply but performs no retrieval or execution.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence
from uuid import uuid4

from .interpretation_service import (
    InterpretationContractError,
    InterpretationService,
    ProposedCriterion,
)


CONTRACT_VERSION = "1.0"
IDEMPOTENCY_TTL = timedelta(hours=24)
MAX_IDEMPOTENCY_KEY_UTF16_UNITS = 200
MAX_USER_KEY_UTF16_UNITS = 300
MAX_OPERATIONS = 64
MAX_CRITERIA = 64
MAX_DIRECT_FILTERS = 32

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")
_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SCOPES = frozenset({"fully_verified", "not_fully_verified", "both"})


def _utc(value: datetime | None = None) -> datetime:
    resolved = value or datetime.now(timezone.utc)
    if resolved.tzinfo is None:
        raise ValueError("now_requires_timezone")
    return resolved.astimezone(timezone.utc)


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _opaque_key() -> str:
    return uuid4().hex


def _version_token() -> str:
    return secrets.token_urlsafe(24)


def _bounded_string(
    value: object,
    label: str,
    maximum: int,
    *,
    pattern: re.Pattern[str] | None = None,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CriteriaServiceError(f"{label}_required")
    normalized = value.strip()
    if _utf16_units(normalized) > maximum:
        raise CriteriaServiceError(f"{label}_too_long")
    if pattern is not None and not pattern.fullmatch(normalized):
        raise CriteriaServiceError(f"{label}_invalid")
    return normalized


def _require_user_key(value: object) -> str:
    return _bounded_string(value, "user_key", MAX_USER_KEY_UTF16_UNITS)


def _canonical_value(value: object) -> object:
    if is_dataclass(value):
        return _canonical_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise CriteriaServiceError("canonical_input_invalid")


def _canonical_hash(command: str, value: object) -> str:
    encoded = json.dumps(
        {"command": command, "input": _canonical_value(value)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Criterion:
    criterion_key: str
    kind: str
    display_label: str
    value: str
    source: str


@dataclass(frozen=True)
class ClarificationOption:
    option_key: str
    display_label: str
    criteria: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class Clarification:
    clarification_key: str
    question: str
    options: tuple[ClarificationOption, ...]
    scope: str


@dataclass(frozen=True)
class CriteriaDraft:
    draft_key: str
    user_key: str
    draft_version_token: str | None
    version_number: int
    state: str
    criteria: tuple[Criterion, ...]
    verification_scope: str
    direct_filters: tuple[tuple[str, str], ...]
    request_text: str | None
    interpretation_provenance: str
    interpretation_status: str
    parent_snapshot_key: str | None
    clarification: Clarification | None
    created_at: datetime
    updated_at: datetime

    @property
    def contract_version(self) -> str:
        return CONTRACT_VERSION


@dataclass(frozen=True)
class AppliedCriteriaSnapshot:
    snapshot_key: str
    user_key: str
    source_draft_key: str
    previous_snapshot_key: str | None
    criteria: tuple[Criterion, ...]
    verification_scope: str
    direct_filters: tuple[tuple[str, str], ...]
    interpretation_provenance: str
    applied_at: datetime

    @property
    def contract_version(self) -> str:
        return CONTRACT_VERSION


@dataclass(frozen=True)
class TerminalReceipt:
    draft_key: str
    outcome: str
    receipt_at: datetime
    snapshot_key: str | None = None
    execution_key: str | None = None

    @property
    def contract_version(self) -> str:
        return CONTRACT_VERSION


@dataclass(frozen=True)
class _IdempotencyRecord:
    command: str
    canonical_input_hash: str
    result: CriteriaDraft | TerminalReceipt
    expires_at: datetime


class CriteriaServiceError(RuntimeError):
    def __init__(
        self,
        failure_code: str,
        *,
        current_state: CriteriaDraft | None = None,
        terminal_receipt: TerminalReceipt | None = None,
        recoverable: bool | None = None,
    ) -> None:
        self.failure_code = failure_code
        self.current_state = current_state
        self.terminal_receipt = terminal_receipt
        self.recoverable = (
            failure_code in {"stale_draft", "interpretation_unavailable"}
            if recoverable is None
            else recoverable
        )
        self.member_message = _failure_message(failure_code)
        super().__init__(failure_code)


def _failure_message(code: str) -> str:
    return {
        "not_found": "That criteria draft is not available.",
        "stale_draft": "This draft changed. Review the current criteria and try again.",
        "terminal_draft": "This draft is already complete.",
        "idempotency_mismatch": "That request key was already used for a different action.",
        "clarification_required": "Choose or dismiss the open clarification before applying.",
        "unknown_clarification": "That clarification is no longer available.",
        "unknown_clarification_option": "That clarification choice is not available.",
    }.get(code, "The criteria change could not be completed.")


class InMemoryCriteriaRepository:
    """Fixture/P-1 persistence with the same owner boundary as the SQL model."""

    def __init__(self) -> None:
        self._drafts: dict[str, CriteriaDraft] = {}
        self._snapshots: dict[str, AppliedCriteriaSnapshot] = {}
        self._snapshot_order: dict[str, list[str]] = {}
        self._terminal_receipts: dict[str, TerminalReceipt] = {}
        self._idempotency: dict[tuple[str, str], _IdempotencyRecord] = {}
        self._lock = threading.RLock()

    def draft_for_owner(self, user_key: str, draft_key: str) -> CriteriaDraft | None:
        draft = self._drafts.get(draft_key)
        return draft if draft is not None and draft.user_key == user_key else None

    def snapshot_for_owner(
        self, user_key: str, snapshot_key: str
    ) -> AppliedCriteriaSnapshot | None:
        snapshot = self._snapshots.get(snapshot_key)
        return snapshot if snapshot is not None and snapshot.user_key == user_key else None

    def snapshots_for_owner(self, user_key: str) -> tuple[AppliedCriteriaSnapshot, ...]:
        return tuple(
            self._snapshots[key] for key in self._snapshot_order.get(user_key, ())
        )

    def latest_snapshot_for_owner(self, user_key: str) -> AppliedCriteriaSnapshot | None:
        keys = self._snapshot_order.get(user_key, ())
        return self._snapshots[keys[-1]] if keys else None

    def terminal_receipt_for_owner(
        self, user_key: str, draft_key: str
    ) -> TerminalReceipt | None:
        if self.draft_for_owner(user_key, draft_key) is None:
            return None
        return self._terminal_receipts.get(draft_key)

    def _idempotency_record(
        self, user_key: str, idempotency_key: str, now: datetime
    ) -> _IdempotencyRecord | None:
        record = self._idempotency.get((user_key, idempotency_key))
        if record is not None and record.expires_at <= now:
            del self._idempotency[(user_key, idempotency_key)]
            return None
        return record

    def _record_idempotency(
        self,
        user_key: str,
        idempotency_key: str,
        command: str,
        canonical_input_hash: str,
        result: CriteriaDraft | TerminalReceipt,
        now: datetime,
    ) -> None:
        self._idempotency[(user_key, idempotency_key)] = _IdempotencyRecord(
            command,
            canonical_input_hash,
            result,
            now + IDEMPOTENCY_TTL,
        )

    def purge_expired_idempotency(self, *, now: datetime) -> int:
        with self._lock:
            expired = [key for key, row in self._idempotency.items() if row.expires_at <= now]
            for key in expired:
                del self._idempotency[key]
            return len(expired)

    def state_digest(self) -> str:
        """Content-safe test aid proving refusals did not mutate repository state."""
        with self._lock:
            value = {
                "drafts": self._drafts,
                "snapshots": self._snapshots,
                "receipts": self._terminal_receipts,
                "idempotency_keys": sorted(f"{owner}:{key}" for owner, key in self._idempotency),
            }
            return hashlib.sha256(
                json.dumps(_canonical_value(value), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()


class CriteriaService:
    def __init__(
        self,
        repository: InMemoryCriteriaRepository,
        interpretation: InterpretationService | None = None,
    ) -> None:
        self.repository = repository
        self.interpretation = interpretation or InterpretationService()
        self._lock = repository._lock

    def get_draft(self, user_key: str, draft_key: str) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        with self._lock:
            draft = self.repository.draft_for_owner(user_key, draft_key)
            if draft is None:
                raise CriteriaServiceError("not_found", recoverable=False)
            return draft

    def get_snapshot(self, user_key: str, snapshot_key: str) -> AppliedCriteriaSnapshot:
        user_key = _require_user_key(user_key)
        with self._lock:
            snapshot = self.repository.snapshot_for_owner(user_key, snapshot_key)
            if snapshot is None:
                raise CriteriaServiceError("not_found", recoverable=False)
            return snapshot

    def create_draft(
        self,
        user_key: str,
        *,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        command = "create_draft"
        canonical = {"idempotency_key": idempotency_key}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_draft(replay)
            draft = CriteriaDraft(
                draft_key=_opaque_key(),
                user_key=user_key,
                draft_version_token=_version_token(),
                version_number=1,
                state="live",
                criteria=(),
                verification_scope="both",
                direct_filters=(),
                request_text=None,
                interpretation_provenance="manual",
                interpretation_status="manual",
                parent_snapshot_key=None,
                clarification=None,
                created_at=now,
                updated_at=now,
            )
            self.repository._drafts[draft.draft_key] = draft
            self._finish(user_key, key, command, digest, draft, now)
            return draft

    def interpret(
        self,
        user_key: str,
        *,
        request_text: str,
        locale: str,
        timezone_name: str,
        idempotency_key: str,
        existing_draft_key: str | None = None,
        existing_draft_version_token: str | None = None,
        parent_snapshot_key: str | None = None,
        now: datetime | None = None,
    ) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if existing_draft_key is None and existing_draft_version_token is not None:
            raise CriteriaServiceError("draft_key_required")
        if existing_draft_key is not None and parent_snapshot_key is not None:
            raise CriteriaServiceError("interpret_target_invalid")
        command = "interpret"
        canonical = {
            "request_text": request_text,
            "locale": locale,
            "timezone": timezone_name,
            "existing_draft_key": existing_draft_key,
            "existing_draft_version_token": existing_draft_version_token,
            "parent_snapshot_key": parent_snapshot_key,
        }
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_draft(replay)
            existing: CriteriaDraft | None = None
            parent: AppliedCriteriaSnapshot | None = None
            if existing_draft_key is not None:
                existing = self._live_draft(
                    user_key, existing_draft_key, existing_draft_version_token
                )
            elif parent_snapshot_key is not None:
                parent = self.repository.snapshot_for_owner(user_key, parent_snapshot_key)
                if parent is None:
                    raise CriteriaServiceError("not_found", recoverable=False)
            try:
                interpreted = self.interpretation.propose(
                    request_text,
                    locale=locale,
                    timezone=timezone_name,
                )
            except InterpretationContractError as error:
                raise CriteriaServiceError(str(error), recoverable=False) from error

            seed_criteria = existing.criteria if existing else (parent.criteria if parent else ())
            proposal_criteria = tuple(
                _criterion_from_proposal(item, source="ai")
                for item in interpreted.proposal.criteria
            )
            criteria = (
                _merge_criteria(seed_criteria, proposal_criteria)
                if seed_criteria
                else proposal_criteria
            )
            seed_filters = dict(
                existing.direct_filters if existing else (parent.direct_filters if parent else ())
            )
            seed_filters.update(dict(interpreted.proposal.direct_filters))
            scope = interpreted.proposal.verification_scope
            if interpreted.interpretation_provenance == "manual_required":
                scope = existing.verification_scope if existing else (
                    parent.verification_scope if parent else "both"
                )
            clarification = _clarification_from_proposal(interpreted.proposal.clarification)
            if existing is None:
                draft = CriteriaDraft(
                    draft_key=_opaque_key(),
                    user_key=user_key,
                    draft_version_token=_version_token(),
                    version_number=1,
                    state="live",
                    criteria=criteria,
                    verification_scope=scope,
                    direct_filters=tuple(sorted(seed_filters.items())),
                    request_text=request_text.strip(),
                    interpretation_provenance=(
                        "manual"
                        if interpreted.interpretation_provenance == "manual_required"
                        else "ai_interpreted"
                    ),
                    interpretation_status=interpreted.interpretation_provenance,
                    parent_snapshot_key=parent_snapshot_key,
                    clarification=clarification,
                    created_at=now,
                    updated_at=now,
                )
            else:
                draft = replace(
                    existing,
                    draft_version_token=_version_token(),
                    version_number=existing.version_number + 1,
                    criteria=criteria,
                    verification_scope=scope,
                    direct_filters=tuple(sorted(seed_filters.items())),
                    request_text=request_text.strip(),
                    interpretation_provenance=(
                        existing.interpretation_provenance
                        if interpreted.interpretation_provenance == "manual_required"
                        else "ai_interpreted"
                    ),
                    interpretation_status=interpreted.interpretation_provenance,
                    clarification=clarification,
                    updated_at=now,
                )
            self.repository._drafts[draft.draft_key] = draft
            self._finish(user_key, key, command, digest, draft, now)
            return draft

    def edit_draft(
        self,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        operations: Sequence[Mapping[str, object]],
        idempotency_key: str,
        now: datetime | None = None,
    ) -> CriteriaDraft:
        return self._edit_command(
            "edit_draft",
            user_key,
            draft_key=draft_key,
            draft_version_token=draft_version_token,
            operations=operations,
            idempotency_key=idempotency_key,
            now=now,
        )

    def refine_from_results(
        self,
        user_key: str,
        *,
        snapshot_key: str,
        operations: Sequence[Mapping[str, object]],
        idempotency_key: str,
        now: datetime | None = None,
    ) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        command = "refine_from_results"
        canonical = {"snapshot_key": snapshot_key, "operations": operations}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_draft(replay)
            snapshot = self.repository.snapshot_for_owner(user_key, snapshot_key)
            if snapshot is None:
                raise CriteriaServiceError("not_found", recoverable=False)
            seed = CriteriaDraft(
                draft_key=_opaque_key(),
                user_key=user_key,
                draft_version_token=_version_token(),
                version_number=1,
                state="live",
                criteria=snapshot.criteria,
                verification_scope=snapshot.verification_scope,
                direct_filters=snapshot.direct_filters,
                request_text=None,
                interpretation_provenance="member_edited",
                interpretation_status="manual",
                parent_snapshot_key=snapshot.snapshot_key,
                clarification=None,
                created_at=now,
                updated_at=now,
            )
            changed = _apply_operations(seed, operations, now=now, rotate=False)
            self.repository._drafts[changed.draft_key] = changed
            self._finish(user_key, key, command, digest, changed, now)
            return changed

    def answer_clarification(
        self,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        clarification_key: str,
        selected_option_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        command = "answer_clarification"
        canonical = {
            "draft_key": draft_key,
            "draft_version_token": draft_version_token,
            "clarification_key": clarification_key,
            "selected_option_key": selected_option_key,
        }
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_draft(replay)
            draft = self._live_draft(user_key, draft_key, draft_version_token)
            if draft.clarification is None or draft.clarification.clarification_key != clarification_key:
                raise CriteriaServiceError("unknown_clarification", recoverable=False)
            option = next(
                (item for item in draft.clarification.options if item.option_key == selected_option_key),
                None,
            )
            if option is None:
                raise CriteriaServiceError("unknown_clarification_option", recoverable=False)
            proposed = tuple(
                Criterion(_opaque_key(), kind, label, value, "member")
                for kind, label, value in option.criteria
            )
            updated = self._rotated(
                draft,
                now=now,
                criteria=_merge_criteria(draft.criteria, proposed),
                clarification=None,
                interpretation_provenance="member_edited",
            )
            self.repository._drafts[draft_key] = updated
            self._finish(user_key, key, command, digest, updated, now)
            return updated

    def dismiss_clarification(
        self,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        clarification_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        command = "dismiss_clarification"
        canonical = {
            "draft_key": draft_key,
            "draft_version_token": draft_version_token,
            "clarification_key": clarification_key,
        }
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_draft(replay)
            draft = self._live_draft(user_key, draft_key, draft_version_token)
            if draft.clarification is None or draft.clarification.clarification_key != clarification_key:
                raise CriteriaServiceError("unknown_clarification", recoverable=False)
            updated = self._rotated(draft, now=now, clarification=None)
            self.repository._drafts[draft_key] = updated
            self._finish(user_key, key, command, digest, updated, now)
            return updated

    def apply(
        self,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> TerminalReceipt:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        command = "apply"
        canonical = {"draft_key": draft_key, "draft_version_token": draft_version_token}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_receipt(replay)
            draft = self._live_draft(user_key, draft_key, draft_version_token)
            if draft.clarification is not None:
                raise CriteriaServiceError("clarification_required", current_state=draft)
            previous = draft.parent_snapshot_key
            if previous is None:
                latest = self.repository.latest_snapshot_for_owner(user_key)
                previous = latest.snapshot_key if latest is not None else None
            snapshot = AppliedCriteriaSnapshot(
                snapshot_key=_opaque_key(),
                user_key=user_key,
                source_draft_key=draft.draft_key,
                previous_snapshot_key=previous,
                criteria=draft.criteria,
                verification_scope=draft.verification_scope,
                direct_filters=draft.direct_filters,
                interpretation_provenance=draft.interpretation_provenance,
                applied_at=now,
            )
            receipt = TerminalReceipt(
                draft_key=draft.draft_key,
                outcome="applied",
                snapshot_key=snapshot.snapshot_key,
                execution_key=_opaque_key(),
                receipt_at=now,
            )
            terminal = replace(
                draft,
                draft_version_token=None,
                state="applied",
                clarification=None,
                updated_at=now,
            )
            self.repository._snapshots[snapshot.snapshot_key] = snapshot
            self.repository._snapshot_order.setdefault(user_key, []).append(snapshot.snapshot_key)
            self.repository._drafts[draft.draft_key] = terminal
            self.repository._terminal_receipts[draft.draft_key] = receipt
            self._finish(user_key, key, command, digest, receipt, now)
            return receipt

    def keep_current_criteria(
        self,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> TerminalReceipt:
        return self._discard(
            "keep_current_criteria",
            user_key,
            draft_key=draft_key,
            draft_version_token=draft_version_token,
            idempotency_key=idempotency_key,
            require_parent=True,
            now=now,
        )

    def discard_draft(
        self,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> TerminalReceipt:
        return self._discard(
            "discard_draft",
            user_key,
            draft_key=draft_key,
            draft_version_token=draft_version_token,
            idempotency_key=idempotency_key,
            require_parent=False,
            now=now,
        )

    def _edit_command(
        self,
        command: str,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        operations: Sequence[Mapping[str, object]],
        idempotency_key: str,
        now: datetime | None,
    ) -> CriteriaDraft:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        canonical = {
            "draft_key": draft_key,
            "draft_version_token": draft_version_token,
            "operations": operations,
        }
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_draft(replay)
            draft = self._live_draft(user_key, draft_key, draft_version_token)
            updated = _apply_operations(draft, operations, now=now, rotate=True)
            self.repository._drafts[draft_key] = updated
            self._finish(user_key, key, command, digest, updated, now)
            return updated

    def _discard(
        self,
        command: str,
        user_key: str,
        *,
        draft_key: str,
        draft_version_token: str,
        idempotency_key: str,
        require_parent: bool,
        now: datetime | None,
    ) -> TerminalReceipt:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        canonical = {"draft_key": draft_key, "draft_version_token": draft_version_token}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect_receipt(replay)
            draft = self._live_draft(user_key, draft_key, draft_version_token)
            if require_parent and draft.parent_snapshot_key is None:
                raise CriteriaServiceError("keep_current_not_available", current_state=draft)
            receipt = TerminalReceipt(draft.draft_key, "discarded", now)
            self.repository._drafts[draft.draft_key] = replace(
                draft,
                draft_version_token=None,
                state="discarded",
                clarification=None,
                updated_at=now,
            )
            self.repository._terminal_receipts[draft.draft_key] = receipt
            self._finish(user_key, key, command, digest, receipt, now)
            return receipt

    def _rotated(self, draft: CriteriaDraft, *, now: datetime, **changes: object) -> CriteriaDraft:
        return replace(
            draft,
            draft_version_token=_version_token(),
            version_number=draft.version_number + 1,
            updated_at=now,
            **changes,
        )

    def _live_draft(
        self, user_key: str, draft_key: str, draft_version_token: str | None
    ) -> CriteriaDraft:
        draft = self.repository.draft_for_owner(user_key, draft_key)
        if draft is None:
            raise CriteriaServiceError("not_found", recoverable=False)
        if draft.state != "live":
            raise CriteriaServiceError(
                "terminal_draft",
                terminal_receipt=self.repository.terminal_receipt_for_owner(user_key, draft_key),
                recoverable=False,
            )
        if not isinstance(draft_version_token, str) or draft.draft_version_token != draft_version_token:
            raise CriteriaServiceError("stale_draft", current_state=draft)
        return draft

    def _begin(
        self,
        user_key: str,
        idempotency_key: str,
        command: str,
        canonical: object,
        now: datetime,
    ) -> tuple[CriteriaDraft | TerminalReceipt | None, str, str]:
        key = _bounded_string(
            idempotency_key,
            "idempotency_key",
            MAX_IDEMPOTENCY_KEY_UTF16_UNITS,
        )
        digest = _canonical_hash(command, canonical)
        record = self.repository._idempotency_record(user_key, key, now)
        if record is not None:
            if record.command == command and record.canonical_input_hash == digest:
                return record.result, key, digest
            raise CriteriaServiceError("idempotency_mismatch", recoverable=False)
        return None, key, digest

    def _finish(
        self,
        user_key: str,
        idempotency_key: str,
        command: str,
        digest: str,
        result: CriteriaDraft | TerminalReceipt,
        now: datetime,
    ) -> None:
        self.repository._record_idempotency(
            user_key, idempotency_key, command, digest, result, now
        )


def _expect_draft(value: CriteriaDraft | TerminalReceipt) -> CriteriaDraft:
    if not isinstance(value, CriteriaDraft):
        raise CriteriaServiceError("idempotency_result_invalid", recoverable=False)
    return value


def _expect_receipt(value: CriteriaDraft | TerminalReceipt) -> TerminalReceipt:
    if not isinstance(value, TerminalReceipt):
        raise CriteriaServiceError("idempotency_result_invalid", recoverable=False)
    return value


def _criterion_from_proposal(value: ProposedCriterion, *, source: str) -> Criterion:
    return Criterion(_opaque_key(), value.kind, value.display_label, value.value, source)


def _clarification_from_proposal(value: object) -> Clarification | None:
    if value is None:
        return None
    return Clarification(
        clarification_key=value.clarification_key,
        question=value.question,
        options=tuple(
            ClarificationOption(
                option.option_key,
                option.display_label,
                tuple((item.kind, item.display_label, item.value) for item in option.criteria),
            )
            for option in value.options
        ),
        scope=value.scope,
    )


def _merge_criteria(
    existing: Sequence[Criterion], proposed: Sequence[Criterion]
) -> tuple[Criterion, ...]:
    replaced_kinds = {item.kind for item in proposed}
    merged = [item for item in existing if item.kind not in replaced_kinds]
    merged.extend(proposed)
    if len(merged) > MAX_CRITERIA:
        raise CriteriaServiceError("too_many_criteria")
    return tuple(merged)


def _apply_operations(
    draft: CriteriaDraft,
    operations: Sequence[Mapping[str, object]],
    *,
    now: datetime,
    rotate: bool,
) -> CriteriaDraft:
    if isinstance(operations, (str, bytes)) or not isinstance(operations, Sequence):
        raise CriteriaServiceError("operations_invalid")
    if not operations or len(operations) > MAX_OPERATIONS:
        raise CriteriaServiceError("operations_invalid")
    criteria = list(draft.criteria)
    scope = draft.verification_scope
    filters = dict(draft.direct_filters)
    for operation in operations:
        if not isinstance(operation, Mapping):
            raise CriteriaServiceError("operation_invalid")
        action = operation.get("op")
        if action == "set_criterion":
            kind = _bounded_string(operation.get("kind"), "criterion_kind", 64, pattern=_KIND_PATTERN)
            label = _bounded_string(operation.get("display_label"), "criterion_display_label", 200)
            value = _bounded_string(operation.get("value"), "criterion_value", 1_000)
            requested_key = operation.get("criterion_key")
            if requested_key is None:
                criterion = Criterion(_opaque_key(), kind, label, value, "manual")
                criteria.append(criterion)
            else:
                requested_key = _bounded_string(requested_key, "criterion_key", 80)
                index = next(
                    (position for position, item in enumerate(criteria) if item.criterion_key == requested_key),
                    None,
                )
                if index is None:
                    raise CriteriaServiceError("criterion_not_found")
                criteria[index] = Criterion(requested_key, kind, label, value, "member")
        elif action == "remove_criterion":
            requested_key = _bounded_string(operation.get("criterion_key"), "criterion_key", 80)
            before = len(criteria)
            criteria = [item for item in criteria if item.criterion_key != requested_key]
            if len(criteria) == before:
                raise CriteriaServiceError("criterion_not_found")
        elif action == "set_verification_scope":
            requested_scope = operation.get("verification_scope")
            if requested_scope not in _SCOPES:
                raise CriteriaServiceError("verification_scope_invalid")
            scope = str(requested_scope)
        elif action == "set_direct_filter":
            filter_key = _bounded_string(
                operation.get("filter_key"), "direct_filter_key", 80, pattern=_KEY_PATTERN
            )
            filters[filter_key] = _bounded_string(
                operation.get("value"), "direct_filter_value", 500
            )
        elif action == "clear_direct_filter":
            filter_key = _bounded_string(
                operation.get("filter_key"), "direct_filter_key", 80, pattern=_KEY_PATTERN
            )
            filters.pop(filter_key, None)
        else:
            raise CriteriaServiceError("operation_invalid")
        if len(criteria) > MAX_CRITERIA or len(filters) > MAX_DIRECT_FILTERS:
            raise CriteriaServiceError("draft_limit_exceeded")
    changes = {
        "criteria": tuple(criteria),
        "verification_scope": scope,
        "direct_filters": tuple(sorted(filters.items())),
        "interpretation_provenance": "member_edited",
        "interpretation_status": "manual",
        "updated_at": now,
    }
    if rotate:
        changes.update(
            draft_version_token=_version_token(),
            version_number=draft.version_number + 1,
        )
    return replace(draft, **changes)


__all__ = [
    "AppliedCriteriaSnapshot",
    "Clarification",
    "ClarificationOption",
    "CriteriaDraft",
    "CriteriaService",
    "CriteriaServiceError",
    "Criterion",
    "InMemoryCriteriaRepository",
    "TerminalReceipt",
]
