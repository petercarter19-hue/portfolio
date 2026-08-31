"""Owner-scoped C4 search execution and result persistence for My Opportunities.

Shared vocabulary module: every closed enum, record shape, repository
Protocol, audit event kind, and the fenced result serializer live here.
``search_worker.py``, ``index_projection.py`` and ``index_fence.py`` import
constants from this module rather than re-typing any string literal, so the
lifecycle/reason vocabulary has exactly one authoritative definition.

Route-free and provider-neutral, mirroring C3/C5's style: no Flask, no
identity, no provider credentials. A member's ``user_key`` is always the
first, server-derived argument on every member-facing method.
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass, fields, is_dataclass, asdict, replace
from datetime import date, datetime, time, timedelta, timezone
from typing import Mapping, Protocol, Sequence

from uuid import uuid4

from .canonical_service import DATA_CLASSES
from .qualification_service import GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED


CONTRACT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# doc 03 §4 execution lifecycle
# ---------------------------------------------------------------------------

STATE_SUBMITTED = "submitted"
STATE_RETRIEVING = "retrieving"
STATE_ASSESSING = "assessing"
STATE_ORDERING = "ordering"
STATE_COMPLETE = "complete"
STATE_PARTIAL = "partial"
STATE_FAILED = "failed"
STATE_CANCELLED = "cancelled"
EXECUTION_STATES = frozenset(
    {
        STATE_SUBMITTED,
        STATE_RETRIEVING,
        STATE_ASSESSING,
        STATE_ORDERING,
        STATE_COMPLETE,
        STATE_PARTIAL,
        STATE_FAILED,
        STATE_CANCELLED,
    }
)
TERMINAL_STATES = frozenset({STATE_COMPLETE, STATE_PARTIAL, STATE_FAILED, STATE_CANCELLED})
STAGE_ORDER = (STATE_SUBMITTED, STATE_RETRIEVING, STATE_ASSESSING, STATE_ORDERING)

# doc 03 §4 + doc 08 §2a failed reasons (closed)
FAILED_STALE_CRITERIA = "stale_criteria"
FAILED_INDEX_UNAVAILABLE = "index_unavailable"
FAILED_AUTHORIZATION_CHANGED = "authorization_changed"
FAILED_SNAPSHOT_PERSISTENCE = "snapshot_persistence_failure"  # §11 note (b)
FAILED_REASONS = frozenset(
    {FAILED_STALE_CRITERIA, FAILED_INDEX_UNAVAILABLE, FAILED_AUTHORIZATION_CHANGED, FAILED_SNAPSHOT_PERSISTENCE}
)

# doc 04 §11 partial reasons (closed, verbatim)
PARTIAL_TIMEOUT = "timeout"
PARTIAL_PROVIDER_FAILURE = "provider_failure"
PARTIAL_INDEX_FAILURE = "index_failure"
PARTIAL_BUDGET_EXHAUSTED = "budget_exhausted"
PARTIAL_ASSESSMENT_PERSISTENCE = "assessment_persistence_failure"
PARTIAL_REASONS = frozenset(
    {
        PARTIAL_TIMEOUT,
        PARTIAL_PROVIDER_FAILURE,
        PARTIAL_INDEX_FAILURE,
        PARTIAL_BUDGET_EXHAUSTED,
        PARTIAL_ASSESSMENT_PERSISTENCE,
    }
)
# Deterministic precedence when several causes occur in one run (§11 note (c)):
PARTIAL_REASON_PRECEDENCE = (
    PARTIAL_ASSESSMENT_PERSISTENCE,
    PARTIAL_INDEX_FAILURE,
    PARTIAL_PROVIDER_FAILURE,
    PARTIAL_TIMEOUT,
    PARTIAL_BUDGET_EXHAUSTED,
)

# doc 04 §3: status coverage vs snapshot coverage
STATUS_COVERAGE = frozenset({"full", "reduced", "degraded"})
SNAPSHOT_COVERAGE = frozenset({"full", "reduced"})
COMPLETENESS = frozenset({"complete", "partial"})

# doc 04 §4 partitions
PARTITION_QUALIFIED = "qualified"  # gate fully_verified
PARTITION_BROADER = "broader"  # gate not_fully_verified
PARTITIONS = frozenset({PARTITION_QUALIFIED, PARTITION_BROADER})

RETRIEVAL_PATHS = frozenset({"index", "canonical"})

# doc 04 §9 named unavailable checks == C5 review_unavailable reason codes, verbatim
UNAVAILABLE_CHECKS = frozenset(
    {"ai_unavailable", "evidence_source_unavailable", "timeout", "assessment_error"}
)

CANCEL_REASONS = frozenset({"member_cancelled", "superseded"})  # doc 04 §5 cancel-and-replace

# canonical-path admission drop reasons (fence analog; closed)
ENTRY_DROP_REASONS = frozenset(
    {"governing_basis_missing", "requirement_unavailable", "data_class_mismatch", "gate_ineligible"}
)

# BLOCKER 3: C3's criterion-kind vocabulary is open by design (any string
# matching interpretation_service's pattern is a legal Criterion.kind); C4
# v1 supports only this enumerated subset for matching. Shared here (rather
# than owned solely by search_worker.py) so register_execution can refuse
# an unsupported kind at registration time -- the matcher's own fail-closed
# handling of an unrecognized kind stays as unreachable defense-in-depth
# once registration validates.
SUPPORTED_STRUCTURED_CRITERION_KINDS = frozenset({"arrangement", "location", "compensation_floor"})
SUPPORTED_FREE_TEXT_CRITERION_KINDS = frozenset({"free_text_term", "role_family", "domain"})
SUPPORTED_CRITERION_KINDS = SUPPORTED_STRUCTURED_CRITERION_KINDS | SUPPORTED_FREE_TEXT_CRITERION_KINDS

# defaults (constructor-injected RetrievalLimits, all explicit -- no hidden values)
DEFAULT_PAGE_SIZE = 20  # doc 04 §5
MAX_PAGE_SIZE = 50  # doc 04 §5
DEFAULT_RETRIEVAL_CEILING = 200
DEFAULT_DAILY_EXECUTION_BUDGET = 100
DEFAULT_STALENESS_HORIZON = timedelta(hours=24)  # doc 04 §8 default; final threshold = owner freshness decision
DEFAULT_ABANDONED_TTL = timedelta(hours=6)  # doc 03 §4 TTL abandonment
DEFAULT_RESULT_RETENTION = timedelta(days=90)  # PROPOSED -- owner decision at C4, §11 (a)

MAX_USER_KEY_UTF16_UNITS = 300  # C3/C5 convention
POSTING_DATE_FIELD = "posted_at"

# ---------------------------------------------------------------------------
# Loading-copy truth binding (doc 16 §4; REC-07)
# ---------------------------------------------------------------------------

LOADING_COPY = {
    ("index", "retrieving"): "Searching stored listings…",
    ("canonical", "retrieving"): "Searching the opportunity store…",
    ("index", "assessing"): "Checking requirements against your evidence…",
    ("canonical", "assessing"): "Checking requirements against your evidence…",
    ("index", "ordering"): "Ordering your results…",
    ("canonical", "ordering"): "Ordering your results…",
}
# Asserted by test: no value may imply a live employer/source check at query time.
FORBIDDEN_LOADING_PHRASES = (
    "employer site",
    "checking sources",
    "contacting",
    "live check",
    "verifying with the employer",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(value: datetime | None = None) -> datetime:
    resolved = value or datetime.now(timezone.utc)
    if resolved.tzinfo is None:
        raise ValueError("now_requires_timezone")
    return resolved.astimezone(timezone.utc)


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _opaque_key() -> str:
    return uuid4().hex


def _bounded_string(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RetrievalServiceError(f"{label}_required")
    normalized = value.strip()
    if _utf16_units(normalized) > maximum:
        # MINOR 14: an over-length value is a distinct failure from a
        # missing one (C5's own _bounded_string precedent) -- this makes
        # user_key_too_long reachable, which was dead code before.
        raise RetrievalServiceError(f"{label}_too_long")
    return normalized


def _require_user_key(value: object) -> str:
    return _bounded_string(value, "user_key", MAX_USER_KEY_UTF16_UNITS)


def _require_nonempty(value: object, label: str) -> str:
    """Presence/type-only check (conservative resolution -- see report note
    e: the closed failure-code list has no ``*_too_long`` code for
    ``snapshot_key``/``execution_key``, so no length ceiling is enforced
    here; a pathologically long opaque key still fails safely downstream as
    ``not_found``)."""
    if not isinstance(value, str) or not value.strip():
        raise RetrievalServiceError(f"{label}_required")
    return value.strip()


_TOKEN_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"


def _tokenize(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    folded = text.casefold()
    tokens: list[str] = []
    current: list[str] = []
    for char in folded:
        if char in _TOKEN_CHARS:
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def _posting_date(version: object) -> date | None:
    raw = (getattr(version, "fields", None) or {}).get(POSTING_DATE_FIELD)
    if not isinstance(raw, str) or len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _canonical_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (frozenset, set)):
        items = [_canonical_value(item) for item in value]
        items.sort(key=lambda item: json.dumps(item, sort_keys=True, default=str))
        return items
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise RetrievalServiceError("canonical_input_invalid")


def _seconds_to_utc_midnight(now: datetime) -> int:
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime.combine(tomorrow, time.min, tzinfo=timezone.utc)
    return int((midnight - now).total_seconds())


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


def _failure_message(code: str) -> str:
    return {
        "not_found": "That item is not available.",
        "user_key_required": "A member identity is required.",
        "user_key_too_long": "That member identity is too long.",
        "snapshot_key_required": "A criteria snapshot is required.",
        "execution_key_required": "A search execution is required.",
        "execution_key_conflict": "That request key was already used for a different search.",
        "execution_not_pending": "That search is already running or finished.",
        "daily_budget_exhausted": "You've reached today's search limit. Try again after midnight UTC.",
        "page_size_invalid": "That page size is not valid.",
        "cursor_invalid": "That results page could not be found; start from the first page.",
        "data_class_invalid": "That data class is not valid.",
        # BLOCKER 3
        "criterion_unsupported": "The search could not run because it contains a filter this version cannot apply.",
        # MINOR 15: deliberately generic and member-facing-identical to
        # `not_found` in tone, but its OWN distinct code -- ops can
        # distinguish "the read genuinely has no data" from "this
        # RetrievalService instance was never wired with a display
        # resolver," which is an integration defect, not a member fact.
        "display_resolver_unavailable": "That request could not be completed right now.",
    }.get(code, "That request could not be completed.")


class RetrievalServiceError(RuntimeError):
    """C3/C5 pattern: ``.failure_code``, ``.recoverable``, ``.member_message``,
    plus ``.retry_after`` and ``.current_state`` for 409-shaped refusals
    (doc 09 §4)."""

    def __init__(
        self,
        failure_code: str,
        *,
        recoverable: bool | None = None,
        retry_after: int | None = None,
        current_state: object | None = None,
    ) -> None:
        self.failure_code = failure_code
        self.recoverable = bool(recoverable) if recoverable is not None else False
        self.retry_after = retry_after
        self.current_state = current_state
        self.member_message = _failure_message(failure_code)
        super().__init__(failure_code)


class RepositoryWriteError(RuntimeError):
    """Raised by a repository write when storage fails. Never becomes an
    execution/snapshot state; the service converts this into a truthful
    terminal ``failed`` outcome and fabricates no member result."""


# ---------------------------------------------------------------------------
# 4.1 Record shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalLimits:
    retrieval_ceiling: int = DEFAULT_RETRIEVAL_CEILING
    daily_execution_budget: int = DEFAULT_DAILY_EXECUTION_BUDGET
    page_size_default: int = DEFAULT_PAGE_SIZE
    page_size_max: int = MAX_PAGE_SIZE
    staleness_horizon: timedelta = DEFAULT_STALENESS_HORIZON
    abandoned_ttl: timedelta = DEFAULT_ABANDONED_TTL

    def __post_init__(self) -> None:
        if (
            not isinstance(self.retrieval_ceiling, int)
            or isinstance(self.retrieval_ceiling, bool)
            or self.retrieval_ceiling <= 0
            or not isinstance(self.daily_execution_budget, int)
            or isinstance(self.daily_execution_budget, bool)
            or self.daily_execution_budget <= 0
            or not isinstance(self.page_size_default, int)
            or isinstance(self.page_size_default, bool)
            or self.page_size_default <= 0
            or not isinstance(self.page_size_max, int)
            or isinstance(self.page_size_max, bool)
            or self.page_size_max <= 0
        ):
            raise ValueError("retrieval_limits_invalid")
        # Mechanical consequence, not a policy choice: a default page size
        # above the max page size could never be honored.
        if self.page_size_default > self.page_size_max:
            raise ValueError("retrieval_limits_invalid")
        if self.staleness_horizon <= timedelta(0) or self.abandoned_ttl <= timedelta(0):
            raise ValueError("retrieval_limits_invalid")


def _validate_state_reason_pairing(
    state: str, failed_reason: str | None, partial_reason: str | None, cancel_reason: str | None
) -> None:
    if state == STATE_FAILED:
        ok = failed_reason in FAILED_REASONS and partial_reason is None and cancel_reason is None
    elif state == STATE_PARTIAL:
        ok = partial_reason in PARTIAL_REASONS and failed_reason is None and cancel_reason is None
    elif state == STATE_CANCELLED:
        ok = cancel_reason in CANCEL_REASONS and failed_reason is None and partial_reason is None
    else:
        ok = failed_reason is None and partial_reason is None and cancel_reason is None
    if not ok:
        raise ValueError("invalid_state_reason_pairing")


@dataclass(frozen=True)
class SearchExecution:
    execution_key: str
    user_key: str
    data_class: str  # fixture | production
    snapshot_key: str  # the C3 applied_criteria_snapshot binding
    state: str  # EXECUTION_STATES
    retrieval_path: str | None  # RETRIEVAL_PATHS once retrieving starts
    coverage: str  # STATUS_COVERAGE
    unavailable_checks: tuple[str, ...]  # subset of UNAVAILABLE_CHECKS, sorted
    failed_reason: str | None  # paired: only when state == failed
    partial_reason: str | None  # paired: only when state == partial
    cancel_reason: str | None  # paired: only when state == cancelled
    submitted_at: datetime
    stage_started_at: Mapping[str, datetime]  # stage -> entered-at (UTC)
    terminal_at: datetime | None

    def __post_init__(self) -> None:
        if self.state not in EXECUTION_STATES:
            raise ValueError("invalid_state")
        if self.data_class not in DATA_CLASSES:
            raise ValueError("invalid_data_class")
        if self.retrieval_path is not None and self.retrieval_path not in RETRIEVAL_PATHS:
            raise ValueError("invalid_retrieval_path")
        if self.coverage not in STATUS_COVERAGE:
            raise ValueError("invalid_coverage")
        checks = tuple(self.unavailable_checks)
        if not set(checks).issubset(UNAVAILABLE_CHECKS) or list(checks) != sorted(checks) or len(set(checks)) != len(checks):
            raise ValueError("invalid_unavailable_checks")
        object.__setattr__(self, "unavailable_checks", checks)
        object.__setattr__(self, "stage_started_at", dict(self.stage_started_at))
        _validate_state_reason_pairing(self.state, self.failed_reason, self.partial_reason, self.cancel_reason)
        if (self.terminal_at is not None) != (self.state in TERMINAL_STATES):
            raise ValueError("invalid_terminal_at")


@dataclass(frozen=True)
class OrderingInputs:  # internal; excluded from serialization
    preferred_verified: int
    retrieval_relevance: float | None  # index-path executions only (doc 04 §4)
    last_successfully_verified_at: datetime | None
    posted_at: date | None
    opportunity_key: str


@dataclass(frozen=True)
class RequiredSummary:
    verified: int
    not_established: int
    appears_unmet: int
    review_unavailable: int
    total: int

    def __post_init__(self) -> None:
        parts = (self.verified, self.not_established, self.appears_unmet, self.review_unavailable, self.total)
        if any(part < 0 for part in parts):
            raise ValueError("invalid_required_summary")
        if self.verified + self.not_established + self.appears_unmet + self.review_unavailable != self.total:
            raise ValueError("invalid_required_summary")


@dataclass(frozen=True)
class PreferredSummary:
    verified: int
    total: int

    def __post_init__(self) -> None:
        if self.verified < 0 or self.total < 0 or self.verified > self.total:
            raise ValueError("invalid_preferred_summary")


@dataclass(frozen=True)
class ResultEntry:
    entry_key: str
    partition: str  # PARTITIONS; pairs with gate_outcome
    ordinal: int  # 1-based within partition, frozen order
    opportunity_key: str
    requirement_version_key: str
    governing_source_version_key: str  # exact result-time basis (doc 04 §3)
    display_attribution_refs: Mapping[str, str]  # field -> source_version_key (references, never facts)
    gate_outcome: str  # C5 GATE_* strings
    required_summary: RequiredSummary
    preferred_summary: PreferredSummary
    ordering_inputs: OrderingInputs

    def __post_init__(self) -> None:
        if self.partition not in PARTITIONS:
            raise ValueError("invalid_partition")
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool) or self.ordinal <= 0:
            raise ValueError("invalid_ordinal")
        if self.gate_outcome not in (GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED):
            raise ValueError("invalid_gate_outcome")
        if (self.partition == PARTITION_QUALIFIED) != (self.gate_outcome == GATE_FULLY_VERIFIED):
            raise ValueError("partition_gate_mismatch")
        object.__setattr__(self, "display_attribution_refs", dict(self.display_attribution_refs))


@dataclass(frozen=True)
class ResultSnapshot:
    result_key: str
    user_key: str
    data_class: str
    execution_key: str
    snapshot_key: str
    completeness: str  # COMPLETENESS
    partial_reason: str | None  # paired with completeness == partial
    coverage: str  # SNAPSHOT_COVERAGE
    disclosures: tuple[str, ...]  # verbatim member-renderable coverage truth
    total_qualified: int
    total_broader: int
    totals_are_lower_bound: bool  # True only when partial ("at least N")
    entries: tuple[ResultEntry, ...]  # qualified partition first, then broader
    created_at: datetime

    def __post_init__(self) -> None:
        if self.data_class not in DATA_CLASSES:
            raise ValueError("invalid_data_class")
        if self.completeness not in COMPLETENESS:
            raise ValueError("invalid_completeness")
        if self.coverage not in SNAPSHOT_COVERAGE:
            raise ValueError("invalid_coverage")
        if self.completeness == "partial":
            if self.partial_reason not in PARTIAL_REASONS:
                raise ValueError("invalid_partial_reason")
        else:
            if self.partial_reason is not None:
                raise ValueError("invalid_partial_reason")
            if self.totals_are_lower_bound:
                raise ValueError("invalid_lower_bound")
        if self.total_qualified < 0 or self.total_broader < 0:
            raise ValueError("invalid_totals")
        entries = tuple(self.entries)
        qualified = tuple(entry for entry in entries if entry.partition == PARTITION_QUALIFIED)
        broader = tuple(entry for entry in entries if entry.partition == PARTITION_BROADER)
        if entries != qualified + broader:
            raise ValueError("invalid_entry_order")
        if self.total_qualified != len(qualified) or self.total_broader != len(broader):
            raise ValueError("invalid_totals")
        for group in (qualified, broader):
            for index, entry in enumerate(group, start=1):
                if entry.ordinal != index:
                    raise ValueError("invalid_ordinal_sequence")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "disclosures", tuple(self.disclosures))


@dataclass(frozen=True)
class ExecutionStatus:
    """Not part of the closed §4.1 vocabulary; a mechanical read-model
    assembled by :meth:`RetrievalService.status` (report note f)."""

    execution_key: str
    state: str
    stages: tuple[tuple[str, datetime], ...]
    coverage: str
    unavailable_checks: tuple[str, ...]
    cancellable: bool
    failed_reason: str | None
    partial_reason: str | None
    loading_copy: str | None


@dataclass(frozen=True)
class ResultsPage:
    """Not part of the closed §4.1 vocabulary; the envelope
    :meth:`RetrievalService.results` returns, wrapping the fenced
    serializer's dict (§4.4) with the staleness metadata described in §4.3
    (report note f). ``entries`` are plain JSON-safe dicts, never the
    internal :class:`ResultEntry` records."""

    result_key: str
    snapshot_key: str
    coverage: str
    completeness: str
    disclosures: tuple[str, ...]
    total_qualified: int
    total_broader: int
    totals_are_lower_bound: bool
    entries: tuple[Mapping[str, object], ...]
    next_cursor: str | None
    previous_cursor: str | None
    contract_version: str
    snapshot_age_seconds: int
    stale: bool


__all__ = [
    "CONTRACT_VERSION",
    "STATE_SUBMITTED",
    "STATE_RETRIEVING",
    "STATE_ASSESSING",
    "STATE_ORDERING",
    "STATE_COMPLETE",
    "STATE_PARTIAL",
    "STATE_FAILED",
    "STATE_CANCELLED",
    "EXECUTION_STATES",
    "TERMINAL_STATES",
    "STAGE_ORDER",
    "FAILED_STALE_CRITERIA",
    "FAILED_INDEX_UNAVAILABLE",
    "FAILED_AUTHORIZATION_CHANGED",
    "FAILED_SNAPSHOT_PERSISTENCE",
    "FAILED_REASONS",
    "PARTIAL_TIMEOUT",
    "PARTIAL_PROVIDER_FAILURE",
    "PARTIAL_INDEX_FAILURE",
    "PARTIAL_BUDGET_EXHAUSTED",
    "PARTIAL_ASSESSMENT_PERSISTENCE",
    "PARTIAL_REASONS",
    "PARTIAL_REASON_PRECEDENCE",
    "STATUS_COVERAGE",
    "SNAPSHOT_COVERAGE",
    "COMPLETENESS",
    "PARTITION_QUALIFIED",
    "PARTITION_BROADER",
    "PARTITIONS",
    "RETRIEVAL_PATHS",
    "UNAVAILABLE_CHECKS",
    "CANCEL_REASONS",
    "ENTRY_DROP_REASONS",
    "SUPPORTED_STRUCTURED_CRITERION_KINDS",
    "SUPPORTED_FREE_TEXT_CRITERION_KINDS",
    "SUPPORTED_CRITERION_KINDS",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "DEFAULT_RETRIEVAL_CEILING",
    "DEFAULT_DAILY_EXECUTION_BUDGET",
    "DEFAULT_STALENESS_HORIZON",
    "DEFAULT_ABANDONED_TTL",
    "DEFAULT_RESULT_RETENTION",
    "MAX_USER_KEY_UTF16_UNITS",
    "POSTING_DATE_FIELD",
    "LOADING_COPY",
    "FORBIDDEN_LOADING_PHRASES",
    "DATA_CLASSES",
    "GATE_FULLY_VERIFIED",
    "GATE_NOT_FULLY_VERIFIED",
    "RetrievalServiceError",
    "RepositoryWriteError",
    "RetrievalLimits",
    "SearchExecution",
    "OrderingInputs",
    "RequiredSummary",
    "PreferredSummary",
    "ResultEntry",
    "ResultSnapshot",
    "ExecutionStatus",
    "ResultsPage",
]


# ---------------------------------------------------------------------------
# 4.2 Repository Protocol + in-memory reference
# ---------------------------------------------------------------------------


class RetrievalRepository(Protocol):
    def execution_for_owner(self, user_key: str, execution_key: str) -> SearchExecution | None: ...
    def execution(self, execution_key: str) -> SearchExecution | None: ...  # worker binding read only
    def active_executions_for_owner(self, user_key: str) -> tuple[SearchExecution, ...]: ...
    def executions_registered_on(self, user_key: str, day: date) -> int: ...
    def save_execution(self, execution: SearchExecution) -> None: ...  # state-machine-guarded
    def snapshot_for_owner(self, user_key: str, result_key: str) -> ResultSnapshot | None: ...
    def snapshot_for_execution(self, user_key: str, execution_key: str) -> ResultSnapshot | None: ...
    def persist_snapshot(self, snapshot: ResultSnapshot) -> None: ...  # atomic, once, LAST write
    def purge_abandoned_executions(self, *, now: datetime, ttl: timedelta) -> int: ...


_LEGAL_FORWARD: Mapping[str, frozenset[str]] = {
    STATE_SUBMITTED: frozenset({STATE_RETRIEVING}),
    STATE_RETRIEVING: frozenset({STATE_ASSESSING}),
    STATE_ASSESSING: frozenset({STATE_ORDERING}),
    STATE_ORDERING: frozenset({STATE_COMPLETE}),
}
_PARTIAL_FROM = frozenset({STATE_RETRIEVING, STATE_ASSESSING, STATE_ORDERING})
_IDENTITY_FIELDS = ("execution_key", "user_key", "data_class", "snapshot_key", "submitted_at")


def _validate_transition(prior: SearchExecution, new: SearchExecution) -> None:
    if prior.state in TERMINAL_STATES:
        raise RepositoryWriteError("execution_terminal")
    for field_name in _IDENTITY_FIELDS:
        if getattr(prior, field_name) != getattr(new, field_name):
            raise RepositoryWriteError("execution_identity_changed")
    if new.state != prior.state:
        if new.state in (STATE_CANCELLED, STATE_FAILED):
            pass  # any non-terminal state may go to cancelled or failed
        elif new.state == STATE_PARTIAL:
            if prior.state not in _PARTIAL_FROM:
                raise RepositoryWriteError("illegal_transition")
        elif new.state not in _LEGAL_FORWARD.get(prior.state, frozenset()):
            raise RepositoryWriteError("illegal_transition")
    for stage, started_at in prior.stage_started_at.items():
        if new.stage_started_at.get(stage) != started_at:
            raise RepositoryWriteError("stage_timestamp_changed")
    if prior.terminal_at is not None and new.terminal_at != prior.terminal_at:
        raise RepositoryWriteError("terminal_timestamp_changed")


class InMemoryRetrievalRepository:
    """C3/C5 idiom: dicts keyed by opaque key, owner filter on every
    ``*_for_owner`` read, a reentrant lock, a content-safe ``state_digest()``
    hash, and a transition guard inside :meth:`save_execution`."""

    def __init__(self) -> None:
        self._executions: dict[str, SearchExecution] = {}
        self._snapshots_by_result_key: dict[str, ResultSnapshot] = {}
        self._result_key_by_execution: dict[str, str] = {}
        self._lock = threading.RLock()

    def execution_for_owner(self, user_key: str, execution_key: str) -> SearchExecution | None:
        execution = self._executions.get(execution_key)
        return execution if execution is not None and execution.user_key == user_key else None

    def execution(self, execution_key: str) -> SearchExecution | None:
        return self._executions.get(execution_key)

    def active_executions_for_owner(self, user_key: str) -> tuple[SearchExecution, ...]:
        return tuple(
            execution
            for execution in self._executions.values()
            if execution.user_key == user_key and execution.state not in TERMINAL_STATES
        )

    def executions_registered_on(self, user_key: str, day: date) -> int:
        return sum(
            1
            for execution in self._executions.values()
            if execution.user_key == user_key and execution.submitted_at.date() == day
        )

    def save_execution(self, execution: SearchExecution) -> None:
        with self._lock:
            prior = self._executions.get(execution.execution_key)
            if prior is not None:
                _validate_transition(prior, execution)
            self._executions[execution.execution_key] = execution

    def snapshot_for_owner(self, user_key: str, result_key: str) -> ResultSnapshot | None:
        snapshot = self._snapshots_by_result_key.get(result_key)
        return snapshot if snapshot is not None and snapshot.user_key == user_key else None

    def snapshot_for_execution(self, user_key: str, execution_key: str) -> ResultSnapshot | None:
        result_key = self._result_key_by_execution.get(execution_key)
        return None if result_key is None else self.snapshot_for_owner(user_key, result_key)

    def persist_snapshot(self, snapshot: ResultSnapshot) -> None:
        with self._lock:
            if snapshot.execution_key in self._result_key_by_execution:
                raise RepositoryWriteError("snapshot_exists")
            execution = self._executions.get(snapshot.execution_key)
            if execution is None or execution.user_key != snapshot.user_key:
                raise RepositoryWriteError("execution_owner_mismatch")
            if execution.state not in (STATE_ORDERING, STATE_COMPLETE, STATE_PARTIAL):
                # Mirrors SQL THROW 55731 on trg_myopp_result_snapshots_immutable
                # (independent-review FINDING 1(b)): a snapshot may only ever
                # be inserted against an execution already in
                # ordering/complete/partial. Catches a cancel that raced in
                # between the worker's own pre-persist re-read and this call
                # -- the worker's persist site turns this into "return the
                # re-read terminal record", never a fabricated
                # snapshot_persistence_failure on top of a cancellation.
                raise RepositoryWriteError("execution_not_ready_for_snapshot")
            self._snapshots_by_result_key[snapshot.result_key] = snapshot
            self._result_key_by_execution[snapshot.execution_key] = snapshot.result_key

    def purge_abandoned_executions(self, *, now: datetime, ttl: timedelta) -> int:
        """Content-blind TTL primitive (doc 03 §4 / doc 08 §2a): deletes by
        key + age only, never reads criteria/results/any content, and never
        writes a snapshot."""
        with self._lock:
            doomed = [
                key
                for key, execution in self._executions.items()
                if execution.state not in TERMINAL_STATES
                and key not in self._result_key_by_execution
                and (now - execution.submitted_at) > ttl
            ]
            for key in doomed:
                del self._executions[key]
            return len(doomed)

    def state_digest(self) -> str:
        """Content-safe test aid proving refusals did not mutate repository state."""
        with self._lock:
            value = {
                "executions": self._executions,
                "snapshots": self._snapshots_by_result_key,
                "snapshot_by_execution": self._result_key_by_execution,
            }
            return hashlib.sha256(
                json.dumps(_canonical_value(value), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()


class FailingRetrievalRepository(InMemoryRetrievalRepository):
    """Test double: raises :class:`RepositoryWriteError` from
    :meth:`persist_snapshot` when ``fail_on_persist_snapshot`` is set --
    used by the snapshot-persistence-failure path tests."""

    def __init__(self, *, fail_on_persist_snapshot: bool = False) -> None:
        super().__init__()
        self._fail_on_persist_snapshot = fail_on_persist_snapshot

    def persist_snapshot(self, snapshot: ResultSnapshot) -> None:
        if self._fail_on_persist_snapshot:
            raise RepositoryWriteError("simulated_write_failure")
        super().persist_snapshot(snapshot)


# ---------------------------------------------------------------------------
# 4.5 Audit sink (content-free; doc 12 Search family)
# ---------------------------------------------------------------------------

_AUDIT_EVENT_KINDS = frozenset(
    {
        "execution_registered",
        "execution_superseded",
        "stage_transition",
        "execution_cancelled",
        "execution_failed",
        "completeness_recorded",
        "fence_dropped",
        "entry_dropped",
        "entry_excluded_persistence",
        "snapshot_written",
        "authorization_changed",
    }
)


@dataclass(frozen=True)
class RetrievalAuditEvent:
    event_kind: str
    user_key: str
    keys: tuple[str, ...]
    reason_code: str | None
    actor: str
    count: int | None
    at: datetime

    def __post_init__(self) -> None:
        if self.event_kind not in _AUDIT_EVENT_KINDS:
            raise ValueError("invalid_event_kind")
        object.__setattr__(self, "keys", tuple(self.keys))


class AuditSink(Protocol):
    def emit(self, event: RetrievalAuditEvent) -> None: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[RetrievalAuditEvent] = []

    def emit(self, event: RetrievalAuditEvent) -> None:
        self.events.append(event)


class CriteriaReader(Protocol):
    def snapshot_for_owner(self, user_key: str, snapshot_key: str) -> object | None: ...


class DisplayResolver(Protocol):
    """Read-only C2 seam (§4.4): satisfied directly by a
    ``CanonicalRepository``-shaped object (its ``version``/``listing``
    methods already match this signature -- no adapter required)."""

    def version(self, key: str) -> object | None: ...
    def listing(self, key: str) -> object | None: ...


# ---------------------------------------------------------------------------
# Cursor encoding (§4.3 results)
# ---------------------------------------------------------------------------


def _encode_cursor(result_key: str, offset: int) -> str:
    payload = json.dumps({"result_key": result_key, "offset": offset}, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str, result_key: str, total_entries: int) -> int:
    try:
        if not isinstance(cursor, str) or not cursor:
            raise ValueError("empty_cursor")
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
        if not isinstance(data, dict) or set(data) != {"result_key", "offset"}:
            raise ValueError("cursor_shape_invalid")
        if data["result_key"] != result_key:
            raise ValueError("cursor_result_key_mismatch")
        offset = data["offset"]
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0 or offset > total_entries:
            raise ValueError("cursor_offset_invalid")
    except RetrievalServiceError:
        raise
    except Exception as error:
        raise RetrievalServiceError("cursor_invalid") from error
    return offset


# ---------------------------------------------------------------------------
# 4.4 Fenced serializer (Search 3F pattern; doc 04 §3)
# ---------------------------------------------------------------------------

PUBLIC_ENTRY_FIELDS = frozenset(
    {
        "entry_key",
        "opportunity_key",
        "requirement_version_key",
        "governing_source_version_key",
        "display_attribution_refs",
        "gate_outcome",
        "required_summary",
        "preferred_summary",
        "display_projection",
    }
)

# doc 16 §4 no-score rule: asserted by test on the full JSON dump of the
# serialized payload -- no key anywhere in it may match these substrings.
FORBIDDEN_SERIALIZATION_TOKENS = (
    "score",
    "probab",
    "percent",
    "rank",
    "predict",
    "confidence",
    "match_rate",
    "relevance",
    "ordering",
)


def _resolve_display_projection(entry: ResultEntry, *, display_resolver: object) -> dict:
    version = display_resolver.version(entry.governing_source_version_key)
    if version is None or getattr(version, "content_withheld", False):
        # Rights-removed or otherwise gone: never substituted with newer
        # facts (doc 04 §8) -- the whole projection collapses to one flag.
        return {"unavailable_under_rights": True}
    listing = display_resolver.listing(getattr(version, "listing_key", None))
    last_verified = getattr(listing, "last_successfully_verified_at", None) if listing is not None else None
    last_attempted = getattr(listing, "last_attempted_at", None) if listing is not None else None
    locations = getattr(version, "locations", None) or ()
    fields = getattr(version, "fields", None) or {}
    return {
        "employer": getattr(version, "employer", None),
        "title": getattr(version, "title", None),
        "locations": list(locations),
        "arrangement": getattr(version, "arrangement", None),
        # "As stated" compensation text (report note g): C2 has no named
        # display-compensation field, so this reads the same free-text
        # ``fields`` bag the matcher's numeric floor reads a different key
        # from -- absent renders null, per the missing-fields rule below.
        "compensation": fields.get("compensation"),
        "last_successfully_verified_at": last_verified.isoformat() if last_verified else None,
        "last_attempted_at": last_attempted.isoformat() if last_attempted else None,
    }


def _serialize_entry(entry: ResultEntry, *, display_resolver: object) -> dict:
    return {
        "entry_key": entry.entry_key,
        "opportunity_key": entry.opportunity_key,
        "requirement_version_key": entry.requirement_version_key,
        "governing_source_version_key": entry.governing_source_version_key,
        "display_attribution_refs": dict(entry.display_attribution_refs),
        "gate_outcome": entry.gate_outcome,
        "required_summary": {
            "verified": entry.required_summary.verified,
            "not_established": entry.required_summary.not_established,
            "appears_unmet": entry.required_summary.appears_unmet,
            "review_unavailable": entry.required_summary.review_unavailable,
            "total": entry.required_summary.total,
        },
        "preferred_summary": {
            "verified": entry.preferred_summary.verified,
            "total": entry.preferred_summary.total,
        },
        "display_projection": _resolve_display_projection(entry, display_resolver=display_resolver),
    }


def serialize_results_page(
    snapshot: ResultSnapshot, page_entries: Sequence[ResultEntry], *, display_resolver: object, now: datetime
) -> dict:
    """Explicit, field-by-field construction (§4.4). Never ``asdict()``s an
    entry and never copies the internal records -- ``ordering_inputs`` (and
    any relevance value) never appears anywhere in the output."""
    del now  # reserved for a future freshness-at-read computation; unused here
    return {
        "result_key": snapshot.result_key,
        "snapshot_key": snapshot.snapshot_key,
        "coverage": snapshot.coverage,
        "completeness": snapshot.completeness,
        "disclosures": list(snapshot.disclosures),
        "total_qualified": snapshot.total_qualified,
        "total_broader": snapshot.total_broader,
        "totals_are_lower_bound": snapshot.totals_are_lower_bound,
        "entries": tuple(_serialize_entry(entry, display_resolver=display_resolver) for entry in page_entries),
        "contract_version": CONTRACT_VERSION,
    }


def _require_supported_criterion_vocabulary(snapshot: object) -> None:
    """BLOCKER 3: refuse at registration when the applied snapshot names a
    criterion kind or direct-filter key C4 v1 does not support. C3's own
    vocabulary is intentionally open (any pattern-valid kind string is a
    legal ``Criterion.kind``); this is where C4 draws its own closed line,
    with a single failure code and message that gives no vocabulary oracle
    beyond "supported" vs "unsupported" -- every unsupported kind refuses
    identically."""
    for criterion in snapshot.criteria:
        if criterion.kind not in SUPPORTED_CRITERION_KINDS:
            raise RetrievalServiceError("criterion_unsupported")
    for filter_key, _value in snapshot.direct_filters:
        if filter_key not in SUPPORTED_STRUCTURED_CRITERION_KINDS:
            raise RetrievalServiceError("criterion_unsupported")


# ---------------------------------------------------------------------------
# 4.3 RetrievalService
# ---------------------------------------------------------------------------


class RetrievalService:
    def __init__(
        self,
        repository: RetrievalRepository,
        *,
        criteria_reader: CriteriaReader,
        limits: RetrievalLimits = RetrievalLimits(),
        audit_sink: AuditSink | None = None,
        display_resolver: DisplayResolver | None = None,
    ) -> None:
        self.repository = repository
        self._criteria_reader = criteria_reader
        self.limits = limits
        self._audit_sink = audit_sink or InMemoryAuditSink()
        # display_resolver is a structural addition (report note d): §4.4
        # requires one to resolve display_projection at read time, but the
        # §4.3 constructor snippet omits a canonical-read seam entirely.
        # Any object exposing ``version(key)``/``listing(key)`` -- e.g. a
        # CanonicalRepository passed directly -- satisfies it.
        self._display_resolver = display_resolver
        self._lock = getattr(repository, "_lock", None) or threading.RLock()

    def _emit(
        self, event_kind: str, user_key: str, keys: Sequence[str], reason_code: str | None, actor: str, at: datetime
    ) -> None:
        self._audit_sink.emit(
            RetrievalAuditEvent(event_kind, user_key, tuple(keys), reason_code, actor, None, at)
        )

    def register_execution(
        self,
        user_key: str,
        *,
        snapshot_key: str,
        execution_key: str,
        data_class: str,
        now: datetime | None = None,
    ) -> SearchExecution:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if data_class not in DATA_CLASSES:
            raise RetrievalServiceError("data_class_invalid")
        snapshot_key = _require_nonempty(snapshot_key, "snapshot_key")
        execution_key = _require_nonempty(execution_key, "execution_key")
        with self._lock:
            snapshot = self._criteria_reader.snapshot_for_owner(user_key, snapshot_key)
            if snapshot is None:
                raise RetrievalServiceError("not_found")
            _require_supported_criterion_vocabulary(snapshot)
            existing = self.repository.execution(execution_key)
            if existing is not None:
                if (existing.user_key, existing.snapshot_key, existing.data_class) == (
                    user_key,
                    snapshot_key,
                    data_class,
                ):
                    return existing  # doc 04 §11 idempotency: never a silent re-run
                raise RetrievalServiceError("execution_key_conflict")
            registered_today = self.repository.executions_registered_on(user_key, now.date())
            if registered_today >= self.limits.daily_execution_budget:
                raise RetrievalServiceError(
                    "daily_budget_exhausted", recoverable=True, retry_after=_seconds_to_utc_midnight(now)
                )
            for active in self.repository.active_executions_for_owner(user_key):
                superseded = replace(active, state=STATE_CANCELLED, cancel_reason="superseded", terminal_at=now)
                self.repository.save_execution(superseded)
                self._emit("execution_superseded", user_key, (active.execution_key,), "superseded", "member", now)
            execution = SearchExecution(
                execution_key=execution_key,
                user_key=user_key,
                data_class=data_class,
                snapshot_key=snapshot_key,
                state=STATE_SUBMITTED,
                retrieval_path=None,
                coverage="full",
                unavailable_checks=(),
                failed_reason=None,
                partial_reason=None,
                cancel_reason=None,
                submitted_at=now,
                stage_started_at={STATE_SUBMITTED: now},
                terminal_at=None,
            )
            self.repository.save_execution(execution)
            self._emit("execution_registered", user_key, (execution_key,), None, "member", now)
            return execution

    def status(self, user_key: str, execution_key: str, *, now: datetime | None = None) -> ExecutionStatus:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        with self._lock:
            execution = self.repository.execution_for_owner(user_key, execution_key)
            if execution is None:
                raise RetrievalServiceError("not_found")
            stages = tuple(
                (stage, execution.stage_started_at[stage]) for stage in STAGE_ORDER if stage in execution.stage_started_at
            )
            loading_copy = LOADING_COPY.get((execution.retrieval_path or "canonical", execution.state))
            return ExecutionStatus(
                execution_key=execution.execution_key,
                state=execution.state,
                stages=stages,
                coverage=execution.coverage,
                unavailable_checks=execution.unavailable_checks,
                cancellable=execution.state not in TERMINAL_STATES,
                failed_reason=execution.failed_reason,
                partial_reason=execution.partial_reason,
                loading_copy=loading_copy,
            )

    def cancel(self, user_key: str, *, execution_key: str, now: datetime | None = None) -> SearchExecution:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        with self._lock:
            execution = self.repository.execution_for_owner(user_key, execution_key)
            if execution is None:
                raise RetrievalServiceError("not_found")
            if execution.state in TERMINAL_STATES:
                return execution  # idempotent: already-terminal cancel is a no-op, not an error
            updated = replace(execution, state=STATE_CANCELLED, cancel_reason="member_cancelled", terminal_at=now)
            self.repository.save_execution(updated)
            self._emit("execution_cancelled", user_key, (execution_key,), "member_cancelled", "member", now)
            return updated

    def results(
        self,
        user_key: str,
        *,
        result_key: str | None = None,
        execution_key: str | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
        now: datetime | None = None,
    ) -> ResultsPage:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if (result_key is None) == (execution_key is None):
            # Exactly one is required; ambiguous/absent input is withheld as
            # not_found rather than a distinct failure code (report note e).
            raise RetrievalServiceError("not_found")
        with self._lock:
            if result_key is not None:
                snapshot = self.repository.snapshot_for_owner(user_key, result_key)
            else:
                snapshot = self.repository.snapshot_for_execution(user_key, execution_key)
            if snapshot is None:
                raise RetrievalServiceError("not_found")
            size = self.limits.page_size_default if page_size is None else page_size
            if isinstance(size, bool) or not isinstance(size, int) or size <= 0 or size > self.limits.page_size_max:
                raise RetrievalServiceError("page_size_invalid")
            offset = 0
            if cursor is not None:
                offset = _decode_cursor(cursor, snapshot.result_key, len(snapshot.entries))
            page_entries = snapshot.entries[offset : offset + size]
            next_offset = offset + size
            next_cursor = (
                _encode_cursor(snapshot.result_key, next_offset) if next_offset < len(snapshot.entries) else None
            )
            previous_cursor = (
                _encode_cursor(snapshot.result_key, max(0, offset - size)) if offset > 0 else None
            )
            if self._display_resolver is None:
                # MINOR 15: an integration defect (this service instance was
                # never wired with a display resolver), not a member fact --
                # a distinct, non-member-identifying code for ops, with a
                # generic member-facing message.
                raise RetrievalServiceError("display_resolver_unavailable")
            payload = serialize_results_page(snapshot, page_entries, display_resolver=self._display_resolver, now=now)
            age = now - snapshot.created_at
            return ResultsPage(
                result_key=payload["result_key"],
                snapshot_key=payload["snapshot_key"],
                coverage=payload["coverage"],
                completeness=payload["completeness"],
                disclosures=tuple(payload["disclosures"]),
                total_qualified=payload["total_qualified"],
                total_broader=payload["total_broader"],
                totals_are_lower_bound=payload["totals_are_lower_bound"],
                entries=payload["entries"],
                next_cursor=next_cursor,
                previous_cursor=previous_cursor,
                contract_version=payload["contract_version"],
                snapshot_age_seconds=int(age.total_seconds()),
                stale=age > self.limits.staleness_horizon,
            )

    def purge_abandoned(self, *, now: datetime) -> int:
        now = _utc(now)
        return self.repository.purge_abandoned_executions(now=now, ttl=self.limits.abandoned_ttl)


__all__ += [
    "RetrievalRepository",
    "InMemoryRetrievalRepository",
    "FailingRetrievalRepository",
    "RetrievalAuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "CriteriaReader",
    "DisplayResolver",
    "PUBLIC_ENTRY_FIELDS",
    "FORBIDDEN_SERIALIZATION_TOKENS",
    "serialize_results_page",
    "RetrievalService",
    "_require_supported_criterion_vocabulary",
]

