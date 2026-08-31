"""The doc 08 §2a owner-bound worker for My Opportunities C4.

Binding, rechecks, retrieval (both paths), the deterministic matcher,
per-entry C5 invocation, ordering chains, and snapshot assembly. The
worker's authorized writes are exhaustive: create/update its one
``search_execution``, write its one ``result_snapshot``, and create initial
``assessment`` rows only through ``qualification_service.assess_requirements``.
It holds no reference to grants, saves, links, drafts, imports, or canonical
write surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Callable, Mapping, Sequence

from .index_fence import fence_candidate
from .index_projection import DiscoveryIndex, IndexUnavailable
from .canonical_service import MyOpportunitiesCanonicalError
from .qualification_service import (
    AssessmentPersistenceError,
    GATE_FULLY_VERIFIED,
    GATE_NOT_FULLY_VERIFIED,
    QualificationService,
    RequirementConstraints,
    RequirementItemSpec,
    RequirementVersionSpec,
    STATE_APPEARS_UNMET,
    STATE_NOT_ESTABLISHED,
    STATE_REVIEW_UNAVAILABLE,
    STATE_VERIFIED,
)
from .retrieval_service import (
    AuditSink,
    FAILED_AUTHORIZATION_CHANGED,
    FAILED_INDEX_UNAVAILABLE,
    FAILED_SNAPSHOT_PERSISTENCE,
    InMemoryAuditSink,
    OrderingInputs,
    PARTIAL_ASSESSMENT_PERSISTENCE,
    PARTIAL_BUDGET_EXHAUSTED,
    PARTIAL_INDEX_FAILURE,
    PARTIAL_PROVIDER_FAILURE,
    PARTIAL_REASON_PRECEDENCE,
    PARTIAL_TIMEOUT,
    PARTITION_BROADER,
    PARTITION_QUALIFIED,
    PreferredSummary,
    RepositoryWriteError,
    RequiredSummary,
    RetrievalAuditEvent,
    RetrievalLimits,
    RetrievalRepository,
    RetrievalServiceError,
    ResultEntry,
    ResultSnapshot,
    STATE_ASSESSING,
    STATE_CANCELLED,
    STATE_COMPLETE,
    STATE_ORDERING,
    STATE_PARTIAL,
    STATE_RETRIEVING,
    STATE_SUBMITTED,
    SUPPORTED_FREE_TEXT_CRITERION_KINDS,
    SUPPORTED_STRUCTURED_CRITERION_KINDS,
    TERMINAL_STATES,
    _opaque_key,
    _posting_date,
    _tokenize,
)


# ---------------------------------------------------------------------------
# Display attribution (report note i)
# ---------------------------------------------------------------------------

# Every displayable field attributes to the SAME governing_source_version_key
# -- a result entry is pinned to one exact result-time basis (doc 04 §3), not
# to C2's live multi-source per-field attribution. References only, never
# facts.
_DISPLAY_FIELD_NAMES = ("employer", "title", "locations", "arrangement", "compensation")


def _display_attribution_refs(governing_source_version_key: str) -> Mapping[str, str]:
    return {field: governing_source_version_key for field in _DISPLAY_FIELD_NAMES}


# ---------------------------------------------------------------------------
# Structured criterion/filter kinds -- BLOCKER 3 moved the closed vocabulary
# itself into retrieval_service.py (register_execution now refuses an
# unsupported kind at registration); the local aliases below exist only so
# this module's matcher code reads unchanged. Interface-bookkeeping note
# (report note j) still applies: InMemoryDiscoveryIndex ignores `filters`,
# so this categorization has no effect on match correctness, only on what
# is passed to the index.
# ---------------------------------------------------------------------------

_STRUCTURED_CRITERION_KINDS = SUPPORTED_STRUCTURED_CRITERION_KINDS
_FREE_TEXT_CRITERION_KINDS = SUPPORTED_FREE_TEXT_CRITERION_KINDS


def _query_terms(snapshot: object) -> tuple[str, ...]:
    terms: set[str] = set()
    for criterion in snapshot.criteria:
        terms |= set(_tokenize(criterion.value))
    return tuple(sorted(terms))


def _structured_filters(snapshot: object) -> Mapping[str, str]:
    filters: dict[str, str] = {}
    for criterion in snapshot.criteria:
        if criterion.kind in _STRUCTURED_CRITERION_KINDS:
            filters[criterion.kind] = criterion.value
    filters.update(dict(snapshot.direct_filters))
    return filters


# ---------------------------------------------------------------------------
# §5.4 Deterministic criteria matcher
# ---------------------------------------------------------------------------


def _text_casefold(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _version_tokens(version: object) -> frozenset[str]:
    tokens: set[str] = set(_tokenize(getattr(version, "title", None) or ""))
    tokens |= set(_tokenize(getattr(version, "employer", None) or ""))
    tokens |= set(_tokenize(getattr(version, "description", None) or ""))
    for location in getattr(version, "locations", None) or ():
        tokens |= set(_tokenize(location))
    return frozenset(tokens)


def _tokens_subset(value: str, tokens: frozenset[str]) -> bool:
    needed = set(_tokenize(value))
    return needed.issubset(tokens)


def _casefold_eq(value: str, other: object) -> bool:
    if other is None:
        return False
    return _text_casefold(value) == _text_casefold(other)


def _casefold_in(value: str, collection: Sequence[str]) -> bool:
    target = _text_casefold(value)
    return any(_text_casefold(item) == target for item in collection)


def _compensation_meets_floor(version: object, value: str) -> bool:
    raw = (getattr(version, "fields", None) or {}).get("compensation_minimum")
    try:
        actual = int(raw)
        floor = int(value)
    except (TypeError, ValueError):
        return False
    if isinstance(raw, bool) or actual < 0:
        return False
    return actual >= floor


def _evaluate_structured(kind: str, value: str, version: object) -> bool:
    if kind == "arrangement":
        return _casefold_eq(value, getattr(version, "arrangement", None))
    if kind == "location":
        return _casefold_in(value, getattr(version, "locations", None) or ())
    if kind == "compensation_floor":
        return _compensation_meets_floor(version, value)
    # An unrecognized structured filter fails closed rather than being
    # silently ignored (report note c).
    return False


def matches_criteria(
    version: object, criteria: Sequence[object], direct_filters: Sequence[tuple[str, str]]
) -> bool:
    """Pure function over the governing ``SourceVersion`` + snapshot
    criteria + direct filters. Case-folded token matching; no clock, no
    randomness."""
    tokens = _version_tokens(version)
    structured_results: list[bool] = []
    free_text_hits: list[bool] = []
    for criterion in criteria:
        kind = criterion.kind
        value = criterion.value
        if kind in _FREE_TEXT_CRITERION_KINDS:
            free_text_hits.append(_tokens_subset(value, tokens))
        elif kind in _STRUCTURED_CRITERION_KINDS:
            structured_results.append(_evaluate_structured(kind, value, version))
        else:
            structured_results.append(False)
    for name, value in direct_filters:
        structured_results.append(_evaluate_structured(name, value, version))
    if not all(structured_results):
        return False
    if free_text_hits and not any(free_text_hits):
        return False
    return True


# ---------------------------------------------------------------------------
# §5.5 spec construction
# ---------------------------------------------------------------------------


def spec_from_requirement_version(version: object) -> RequirementVersionSpec:
    """C5 spec construction from C2 data. REC-06's accepted conservative
    default: every item is mapped ``requirement_class="required"``,
    ``classification_basis="ambiguous_default_required"`` -- C2 v1 stores no
    stated required/preferred classification, so this can only withhold
    ``Fully verified``, never overclaim (§11 note (d))."""
    if getattr(version, "content_withheld", False) or not version.items:
        raise RetrievalServiceError("not_found")
    items = []
    for item in version.items:
        if (
            item.content_withheld
            or not item.requirement_item_key
            or not item.normalized_clause
            or not isinstance(item.ordinal, int)
            or isinstance(item.ordinal, bool)
            or item.ordinal <= 0
        ):
            raise RetrievalServiceError("not_found")
        items.append(
            RequirementItemSpec(
                requirement_item_key=item.requirement_item_key,
                ordinal=item.ordinal,
                normalized_clause=item.normalized_clause,
                requirement_class="required",
                classification_basis="ambiguous_default_required",
                constraints=RequirementConstraints(),
                reading_flagged=False,
            )
        )
    return RequirementVersionSpec(
        requirement_version_key=version.requirement_version_key,
        opportunity_key=version.opportunity_key,
        items=tuple(items),
    )


# ---------------------------------------------------------------------------
# §5.3 Ordering chains
# ---------------------------------------------------------------------------


def _orderable(value: object) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, date):
        return float(value.toordinal())
    return float(value)


def _null_last_desc(value: object) -> tuple[int, float]:
    return (1, 0.0) if value is None else (0, -_orderable(value))


def _ts(value: datetime | None) -> datetime | None:
    return value


def _ord(value: date | None) -> date | None:
    return value


@dataclass(frozen=True)
class EntryEvaluation:
    """Worker-internal only (not part of the closed §4.1 vocabulary): every
    field the ordering chains and the final :class:`ResultEntry` assembly
    need, flattened so ``qualified_sort_key``/``broader_sort_key`` can read
    them directly (§5.3's pseudocode addresses ``e.preferred_verified`` etc.
    as direct attributes)."""

    opportunity_key: str
    requirement_version_key: str
    governing_source_version_key: str
    gate: str  # GATE_FULLY_VERIFIED | GATE_NOT_FULLY_VERIFIED
    required_summary: RequiredSummary
    preferred_summary: PreferredSummary
    preferred_verified: int
    retrieval_relevance: float | None
    last_successfully_verified_at: datetime | None
    posted_at: date | None


def qualified_sort_key(e: EntryEvaluation) -> tuple:
    return (
        -e.preferred_verified,  # 1. verified-preferred count desc; absent = 0
        *_null_last_desc(e.retrieval_relevance),  # 2. internal relevance desc; index path only
        *_null_last_desc(_ts(e.last_successfully_verified_at)),  # 3. REC-07 governing-head timestamp desc
        *_null_last_desc(_ord(e.posted_at)),  # 4. posting date desc; null oldest
        e.opportunity_key,  # 5. asc lexicographic -- total order, no ties
    )


def broader_sort_key(e: EntryEvaluation) -> tuple:
    return (
        *_null_last_desc(e.retrieval_relevance),
        *_null_last_desc(_ts(e.last_successfully_verified_at)),
        *_null_last_desc(_ord(e.posted_at)),
        e.opportunity_key,
    )


def _summarize_required(assessments: Sequence[object]) -> RequiredSummary:
    counts = {STATE_VERIFIED: 0, STATE_NOT_ESTABLISHED: 0, STATE_APPEARS_UNMET: 0, STATE_REVIEW_UNAVAILABLE: 0}
    for assessment in assessments:
        counts[assessment.state] += 1
    return RequiredSummary(
        verified=counts[STATE_VERIFIED],
        not_established=counts[STATE_NOT_ESTABLISHED],
        appears_unmet=counts[STATE_APPEARS_UNMET],
        review_unavailable=counts[STATE_REVIEW_UNAVAILABLE],
        total=len(assessments),
    )


def _summarize_preferred(assessments: Sequence[object]) -> PreferredSummary:
    verified = sum(1 for assessment in assessments if assessment.state == STATE_VERIFIED)
    return PreferredSummary(verified=verified, total=len(assessments))


def _build_entry(evaluation: EntryEvaluation, *, partition: str, ordinal: int) -> ResultEntry:
    return ResultEntry(
        entry_key=_opaque_key(),
        partition=partition,
        ordinal=ordinal,
        opportunity_key=evaluation.opportunity_key,
        requirement_version_key=evaluation.requirement_version_key,
        governing_source_version_key=evaluation.governing_source_version_key,
        display_attribution_refs=_display_attribution_refs(evaluation.governing_source_version_key),
        gate_outcome=evaluation.gate,
        required_summary=evaluation.required_summary,
        preferred_summary=evaluation.preferred_summary,
        ordering_inputs=OrderingInputs(
            preferred_verified=evaluation.preferred_verified,
            retrieval_relevance=evaluation.retrieval_relevance,
            last_successfully_verified_at=evaluation.last_successfully_verified_at,
            posted_at=evaluation.posted_at,
            opportunity_key=evaluation.opportunity_key,
        ),
    )


# ---------------------------------------------------------------------------
# Candidate basis (shared canonical admission rules; report note c)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CandidateBasis:
    opportunity_key: str
    requirement_version_key: str
    governing_source_version_key: str
    version: object
    requirement_version: object
    listing: object


class _PreAdmissionFailure(Exception):
    """Raised internally when a canonical-store read fails before any
    candidate has been admitted on the primary canonical path (§5.2 3b)."""


def _dedupe_fence_admitted(candidates: Sequence[tuple[str, float]]) -> list[tuple[str, float]]:
    """IMPORTANT 6: collapse duplicate opportunity_key slots from the index
    to one entry each -- keep the maximum relevance; a tie keeps whichever
    occurrence was seen first, for determinism."""
    best: dict[str, tuple[float, int]] = {}
    for position, (opportunity_key, relevance) in enumerate(candidates):
        prior = best.get(opportunity_key)
        if prior is None or relevance > prior[0]:
            best[opportunity_key] = (relevance, position)
    ordered_keys = sorted(best, key=lambda key: best[key][1])
    return [(key, best[key][0]) for key in ordered_keys]


# ---------------------------------------------------------------------------
# The worker
# ---------------------------------------------------------------------------


class SearchWorker:
    def __init__(
        self,
        *,
        retrieval_repository: RetrievalRepository,
        criteria_reader: object,
        canonical_service: object,
        canonical_repository: object,
        qualification_service: QualificationService,
        index: DiscoveryIndex | None = None,
        limits: RetrievalLimits = RetrievalLimits(),
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._repository = retrieval_repository
        self._criteria_reader = criteria_reader
        self._canonical_service = canonical_service
        self._canonical_repository = canonical_repository
        self._qualification_service = qualification_service
        self._index = index
        self._limits = limits
        self._audit_sink = audit_sink or InMemoryAuditSink()

    # -- audit ------------------------------------------------------------

    def _emit(
        self, event_kind: str, user_key: str, keys: Sequence[str], reason_code: str | None, at: datetime,
        count: int | None = None,
    ) -> None:
        self._audit_sink.emit(
            RetrievalAuditEvent(event_kind, user_key, tuple(keys), reason_code, "system:search_worker", count, at)
        )

    def _emit_counts(self, event_kind: str, user_key: str, counts: Mapping[str, int], at: datetime) -> None:
        for reason in sorted(counts):
            if counts[reason]:
                self._emit(event_kind, user_key, (), reason, at, count=counts[reason])

    # -- transitions --------------------------------------------------------

    def _transition_stage(self, execution: object, new_state: str, now: datetime) -> object:
        # BLOCKER 1 / IMPORTANT 5: re-read before writing. If the execution
        # already reached a terminal state through some other path (e.g. a
        # member cancel that landed between our own writes), never overwrite
        # it and never let the repository's transition guard raise -- return
        # the terminal record unchanged so the caller stops here.
        current = self._repository.execution(execution.execution_key)
        if current is not None and current.state in TERMINAL_STATES:
            return current
        # FINDING 7 (independent review, MINOR): build the update from the
        # freshly re-read record, not the caller's possibly-stale local
        # copy -- `current` is the true basis for what gets written.
        basis = current if current is not None else execution
        updated = replace(basis, state=new_state, stage_started_at={**basis.stage_started_at, new_state: now})
        self._repository.save_execution(updated)
        self._emit("stage_transition", execution.user_key, (execution.execution_key,), new_state, now)
        return updated

    def _terminal_failed(self, execution: object, failed_reason: str, now: datetime) -> object:
        # FINDING 2 (independent review, IMPORTANT): re-read first. Every
        # call site of this helper writes after work that can take
        # arbitrary time (a criteria-store read, a full _retrieve pass, a
        # persist_snapshot attempt) during which a routine member cancel
        # can land -- never overwrite an execution that already went
        # terminal, and never let the repository's transition guard raise.
        current = self._repository.execution(execution.execution_key)
        if current is not None and current.state in TERMINAL_STATES:
            return current
        basis = current if current is not None else execution
        updated = replace(basis, state="failed", failed_reason=failed_reason, terminal_at=now)
        self._repository.save_execution(updated)
        self._emit("execution_failed", execution.user_key, (execution.execution_key,), failed_reason, now)
        return updated

    def _terminal_authorization_changed(self, execution: object, now: datetime) -> object:
        current = self._repository.execution(execution.execution_key)
        if current is not None and current.state in TERMINAL_STATES:
            return current
        basis = current if current is not None else execution
        updated = replace(basis, state="failed", failed_reason=FAILED_AUTHORIZATION_CHANGED, terminal_at=now)
        self._repository.save_execution(updated)
        self._emit(
            "authorization_changed", execution.user_key, (execution.execution_key,), FAILED_AUTHORIZATION_CHANGED, now
        )
        return updated

    def _check_cancelled(self, execution_key: str) -> object | None:
        current = self._repository.execution(execution_key)
        return current if current is not None and current.state == STATE_CANCELLED else None

    # -- canonical admission (shared by both retrieval paths) -------------

    def _admission_basis(self, opportunity_key: str, data_class: str, now: datetime):
        try:
            opportunity = self._canonical_service.resolve_opportunity(opportunity_key)
        except MyOpportunitiesCanonicalError:
            # Expected absence (tombstone-unresolvable, truly unknown key):
            # a normal per-candidate drop, never a worker-level failure.
            # An unrelated exception type (e.g. a storage outage) is left
            # to propagate so the mid-enumeration provider_failure /
            # index_failure partial-cause paths can distinguish it (report
            # note l).
            return None, "governing_basis_missing"
        if opportunity.data_class != data_class:
            return None, "data_class_mismatch"
        gate = self._canonical_service.canonical_gate(opportunity_key, now=now)
        if not gate.passes:
            return None, "gate_ineligible"
        if not (
            opportunity.governing_listing_key
            and opportunity.governing_source_version_key
            and opportunity.requirement_version_key
        ):
            return None, "governing_basis_missing"
        requirement_version = self._canonical_repository.requirement_version(opportunity.requirement_version_key)
        if requirement_version is None or requirement_version.content_withheld or not requirement_version.items:
            return None, "requirement_unavailable"
        for item in requirement_version.items:
            if (
                item.content_withheld
                or not item.requirement_item_key
                or not item.normalized_clause
                or not isinstance(item.ordinal, int)
                or isinstance(item.ordinal, bool)
                or item.ordinal <= 0
            ):
                return None, "requirement_unavailable"
        version = self._canonical_repository.version(opportunity.governing_source_version_key)
        listing = self._canonical_repository.listing(opportunity.governing_listing_key)
        if version is None or listing is None:
            return None, "governing_basis_missing"
        return (
            _CandidateBasis(
                opportunity_key=opportunity.opportunity_key,
                requirement_version_key=requirement_version.requirement_version_key,
                governing_source_version_key=version.version_key,
                version=version,
                requirement_version=requirement_version,
                listing=listing,
            ),
            None,
        )

    def _canonical_candidates(self, data_class: str, now: datetime, *, partial_causes: set, drop_counts: dict):
        """Returns ``(basis, None)`` pairs: the primary/fallback canonical
        path resolves the full admission basis exactly once per
        candidate -- there is no separate index document to recheck
        against, so no second resolution pass is needed (unlike the index
        path; see the post-fence recheck in :meth:`_retrieve`)."""
        admitted: list[tuple[_CandidateBasis, None]] = []
        try:
            opportunities = tuple(self._canonical_repository.opportunities(data_class))
        except Exception:
            raise _PreAdmissionFailure() from None
        try:
            for opportunity in opportunities:
                basis, reason = self._admission_basis(opportunity.opportunity_key, data_class, now)
                if basis is not None:
                    admitted.append((basis, None))
                else:
                    drop_counts[reason] = drop_counts.get(reason, 0) + 1
        except Exception:
            if admitted:
                partial_causes.add(PARTIAL_PROVIDER_FAILURE)
                return admitted
            raise _PreAdmissionFailure() from None
        return admitted

    # -- retrieval (§5.2 step 3) -------------------------------------------

    def _retrieve(self, execution: object, snapshot: object, *, now: datetime):
        data_class = execution.data_class
        disclosures: list[str] = []
        partial_causes: set[str] = set()
        fence_drop_counts: dict[str, int] = {}
        entry_drop_counts: dict[str, int] = {}
        path: str
        coverage_override: str | None = None
        resolved: list[tuple[_CandidateBasis, float | None]] = []

        if self._index is not None:
            try:
                index_candidates = self._index.search(
                    data_class=data_class, terms=_query_terms(snapshot), filters=_structured_filters(snapshot)
                )
                path = "index"
                fence_admitted: list[tuple[str, float]] = []
                try:
                    for candidate in index_candidates:
                        decision = fence_candidate(
                            candidate,
                            data_class=data_class,
                            canonical_service=self._canonical_service,
                            canonical_repository=self._canonical_repository,
                            now=now,
                        )
                        if decision.admitted:
                            fence_admitted.append(
                                (candidate.document.opportunity_key, candidate.retrieval_relevance)
                            )
                        else:
                            fence_drop_counts[decision.reason] = fence_drop_counts.get(decision.reason, 0) + 1
                except Exception:
                    # BLOCKER 2 + IMPORTANT 4: fence_candidate now only ever
                    # swallows the expected "not found" canonical exception
                    # internally; anything else (a genuine storage outage
                    # mid-fence) propagates here. Nothing may strand the
                    # execution non-terminal -- record it exactly like the
                    # post-fence recheck's own mid-loop failure and stop
                    # admitting further, keeping whatever fenced so far.
                    partial_causes.add(PARTIAL_INDEX_FAILURE)
                    disclosures.append(
                        "search stopped early: the opportunity store became unavailable partway through"
                    )
                if fence_drop_counts:
                    self._emit_counts("fence_dropped", execution.user_key, fence_drop_counts, now)
                fence_admitted = _dedupe_fence_admitted(fence_admitted)

                # Post-fence canonical recheck (report note c): never trust
                # the projection document for anything beyond identity and
                # retrieval_relevance. The fence already proved the
                # document's governing/requirement keys equal canonical's
                # current ones; this additionally guards against a
                # requirement version that is malformed independent of its
                # key (empty/withheld items) and resolves the real
                # SourceVersion/RequirementVersion objects the matcher and
                # C5 spec construction need -- the worker never trusts a
                # candidate document's own copied fields for either.
                for opportunity_key, relevance in fence_admitted:
                    try:
                        basis, reason = self._admission_basis(opportunity_key, data_class, now)
                    except Exception:
                        # A canonical-store read failing partway through
                        # resolving already-fence-admitted index candidates
                        # is scoped to the index path specifically (report
                        # note k): keep whatever was resolved so far rather
                        # than discarding an already-substantially-retrieved
                        # index-path result.
                        partial_causes.add(PARTIAL_INDEX_FAILURE)
                        disclosures.append(
                            "search stopped early: the opportunity store became unavailable partway through"
                        )
                        break
                    if basis is None:
                        entry_drop_counts[reason] = entry_drop_counts.get(reason, 0) + 1
                        continue
                    resolved.append((basis, relevance))
                if entry_drop_counts:
                    self._emit_counts("entry_dropped", execution.user_key, entry_drop_counts, now)
            except IndexUnavailable:
                path = "canonical"
                coverage_override = "degraded"
                disclosures.append("reduced coverage: discovery index unavailable — reduced ordering richness")
                try:
                    resolved = self._canonical_candidates(
                        data_class, now, partial_causes=partial_causes, drop_counts=entry_drop_counts
                    )
                except _PreAdmissionFailure:
                    return "failed", FAILED_INDEX_UNAVAILABLE
                if entry_drop_counts:
                    self._emit_counts("entry_dropped", execution.user_key, entry_drop_counts, now)
        else:
            path = "canonical"
            try:
                resolved = self._canonical_candidates(
                    data_class, now, partial_causes=partial_causes, drop_counts=entry_drop_counts
                )
            except _PreAdmissionFailure:
                return "failed", FAILED_INDEX_UNAVAILABLE
            if entry_drop_counts:
                self._emit_counts("entry_dropped", execution.user_key, entry_drop_counts, now)

        matched = [
            (basis, relevance)
            for basis, relevance in resolved
            if matches_criteria(basis.version, snapshot.criteria, snapshot.direct_filters)
        ]
        matched.sort(key=lambda pair: pair[0].opportunity_key)

        if len(matched) > self._limits.retrieval_ceiling:
            matched = matched[: self._limits.retrieval_ceiling]
            partial_causes.add(PARTIAL_BUDGET_EXHAUSTED)
            disclosures.append(f"retrieval ceiling reached: first {self._limits.retrieval_ceiling} evaluated")

        return "ok", (matched, path, coverage_override, disclosures, partial_causes)

    # -- run (§5.2) ---------------------------------------------------------

    def run(
        self,
        execution_key: str,
        *,
        now: datetime,
        deadline: datetime | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> object:
        clock = clock or (lambda: now)

        # 0. LOAD
        execution = self._repository.execution(execution_key)
        if execution is None:
            raise RetrievalServiceError("not_found")
        if execution.state in TERMINAL_STATES:
            return execution  # idempotent re-run: the recorded outcome
        if execution.state != STATE_SUBMITTED:
            raise RetrievalServiceError("execution_not_pending")
        user_key, snapshot_key, data_class = execution.user_key, execution.snapshot_key, execution.data_class

        # 1. RECHECK AT EXECUTION
        snapshot = self._criteria_reader.snapshot_for_owner(user_key, snapshot_key)
        if snapshot is None or snapshot.snapshot_key != snapshot_key:
            return self._terminal_failed(execution, "stale_criteria", now)

        # 2. STAGE -> retrieving
        execution = self._transition_stage(execution, STATE_RETRIEVING, now)
        if execution.state in TERMINAL_STATES:
            return execution

        # 3. RETRIEVE
        kind, payload = self._retrieve(execution, snapshot, now=now)
        if kind == "failed":
            return self._terminal_failed(execution, payload, now)
        matched, path, coverage_override, disclosures, partial_causes = payload

        # BLOCKER 1 / IMPORTANT 5 (write window 1): re-read before this
        # direct write -- retrieval can take arbitrarily long, and the
        # execution may have become terminal (e.g. cancelled) while it ran.
        current = self._repository.execution(execution.execution_key)
        if current is not None and current.state in TERMINAL_STATES:
            return current
        execution = replace(execution, retrieval_path=path, coverage=(coverage_override or execution.coverage))
        self._repository.save_execution(execution)

        # 3f. CANCELLATION CHECK
        cancelled = self._check_cancelled(execution.execution_key)
        if cancelled is not None:
            return cancelled

        # 4. STAGE -> assessing
        execution = self._transition_stage(execution, STATE_ASSESSING, now)
        if execution.state in TERMINAL_STATES:
            return execution
        evaluations: list[EntryEvaluation] = []
        unavailable_checks: set[str] = set()
        for basis, relevance in matched:
            if deadline is not None and clock() > deadline:
                partial_causes.add(PARTIAL_TIMEOUT)
                disclosures.append(
                    "search stopped early: time limit reached before all matches could be checked"
                )
                break
            cancelled = self._check_cancelled(execution.execution_key)
            if cancelled is not None:
                return cancelled

            spec = spec_from_requirement_version(basis.requirement_version)
            try:
                run_result = self._qualification_service.assess_requirements(
                    user_key,
                    spec=spec,
                    member_context_text=None,
                    actor="system:search_worker/assessment",
                    now=now,
                )
            except AssessmentPersistenceError:
                if PARTIAL_ASSESSMENT_PERSISTENCE not in partial_causes:
                    # §11 note (c): every cause named in disclosures[], not
                    # only the highest-precedence one that ends up as the
                    # execution's headline partial_reason. One disclosure
                    # per cause, not per excluded entry.
                    disclosures.append("some matches could not be saved and were left out of these results")
                partial_causes.add(PARTIAL_ASSESSMENT_PERSISTENCE)
                self._emit(
                    "entry_excluded_persistence",
                    user_key,
                    (basis.opportunity_key,),
                    PARTIAL_ASSESSMENT_PERSISTENCE,
                    now,
                )
                continue

            gate = run_result.gate.gate
            review_unavailable_reasons = {
                assessment.reason_code
                for assessment in run_result.assessments
                if assessment.state == STATE_REVIEW_UNAVAILABLE
            }
            unavailable_checks |= review_unavailable_reasons
            required_assessments = [a for a in run_result.assessments if a.assessment_type == "required"]
            preferred_assessments = [a for a in run_result.assessments if a.assessment_type == "preferred"]
            required_summary = _summarize_required(required_assessments)
            preferred_summary = _summarize_preferred(preferred_assessments)

            if snapshot.verification_scope == "fully_verified" and gate != GATE_FULLY_VERIFIED:
                continue
            if snapshot.verification_scope == "not_fully_verified" and gate != GATE_NOT_FULLY_VERIFIED:
                continue

            evaluations.append(
                EntryEvaluation(
                    opportunity_key=basis.opportunity_key,
                    requirement_version_key=basis.requirement_version_key,
                    governing_source_version_key=basis.governing_source_version_key,
                    gate=gate,
                    required_summary=required_summary,
                    preferred_summary=preferred_summary,
                    preferred_verified=preferred_summary.verified,
                    retrieval_relevance=relevance,
                    last_successfully_verified_at=basis.listing.last_successfully_verified_at,
                    posted_at=_posting_date(basis.version),
                )
            )

        if unavailable_checks:
            disclosures.append(f"reduced coverage: {', '.join(sorted(unavailable_checks))} unavailable")

        # 5. STAGE -> ordering
        execution = self._transition_stage(execution, STATE_ORDERING, now)
        if execution.state in TERMINAL_STATES:
            return execution
        qualified = sorted((e for e in evaluations if e.gate == GATE_FULLY_VERIFIED), key=qualified_sort_key)
        broader = sorted((e for e in evaluations if e.gate == GATE_NOT_FULLY_VERIFIED), key=broader_sort_key)
        entries = tuple(
            _build_entry(e, partition=PARTITION_QUALIFIED, ordinal=index)
            for index, e in enumerate(qualified, start=1)
        ) + tuple(
            _build_entry(e, partition=PARTITION_BROADER, ordinal=index) for index, e in enumerate(broader, start=1)
        )

        # 6. FINAL RECHECK BEFORE PERSISTENCE
        final_snapshot = self._criteria_reader.snapshot_for_owner(user_key, snapshot_key)
        final_execution = self._repository.execution(execution.execution_key)
        if final_execution is not None and final_execution.state in TERMINAL_STATES:
            # BLOCKER 1 (write window 3, the probe-proven defect): a flip to
            # ANY terminal state -- not only cancelled -- between our own
            # writes must never be overwritten and must never have a
            # snapshot persisted on top of it. Return the actual re-read
            # terminal record unchanged; do not call
            # _terminal_authorization_changed, which would attempt a second
            # write on an already-terminal row.
            return final_execution
        if (
            final_snapshot is None
            or final_snapshot.snapshot_key != snapshot_key
            or final_execution is None
            or final_execution.user_key != user_key
            or final_execution.data_class != data_class
            or final_execution.snapshot_key != snapshot_key
        ):
            return self._terminal_authorization_changed(execution, now)

        # 7. SNAPSHOT -- ALWAYS LAST, IN ITS OWN TRANSACTION
        execution_coverage = (
            execution.coverage if execution.coverage == "degraded" else ("reduced" if unavailable_checks else "full")
        )
        snapshot_coverage = "reduced" if (unavailable_checks or execution.coverage == "degraded") else "full"
        completeness = "partial" if partial_causes else "complete"
        partial_reason = None
        if partial_causes:
            partial_reason = next(reason for reason in PARTIAL_REASON_PRECEDENCE if reason in partial_causes)

        result_snapshot = ResultSnapshot(
            result_key=_opaque_key(),
            user_key=user_key,
            data_class=data_class,
            execution_key=execution.execution_key,
            snapshot_key=snapshot_key,
            completeness=completeness,
            partial_reason=partial_reason,
            coverage=snapshot_coverage,
            disclosures=tuple(disclosures),
            total_qualified=len(qualified),
            total_broader=len(broader),
            totals_are_lower_bound=bool(partial_causes),
            entries=entries,
            created_at=now,
        )
        # FINDING 1(a) (independent review, BLOCKING): re-read immediately
        # before the persist attempt. A member cancel racing this exact
        # window must never see its own snapshot appear afterward -- do not
        # even attempt persist_snapshot if the execution already went
        # terminal.
        pre_persist = self._repository.execution(execution.execution_key)
        if pre_persist is not None and pre_persist.state in TERMINAL_STATES:
            return pre_persist
        try:
            self._repository.persist_snapshot(result_snapshot)
        except RepositoryWriteError:
            # FINDING 1(b): persist_snapshot's own state guard (mirroring
            # SQL THROW 55731) can still refuse here if the cancel landed in
            # the narrow gap between the re-read above and this call.
            # _terminal_failed re-reads internally (FINDING 2) and returns
            # the actual terminal record in that case rather than
            # fabricating a snapshot_persistence_failure on top of a
            # cancellation; a genuine storage failure (execution still
            # non-terminal) still becomes failed(snapshot_persistence_failure)
            # exactly as before.
            return self._terminal_failed(execution, FAILED_SNAPSHOT_PERSISTENCE, now)
        self._emit("snapshot_written", user_key, (result_snapshot.result_key,), None, now)

        # 8. TERMINAL
        # FINDING 1(a): guard this last write the same way -- a cancel could
        # still land in the (very narrow) gap between persist_snapshot
        # succeeding and this write.
        pre_terminal = self._repository.execution(execution.execution_key)
        if pre_terminal is not None and pre_terminal.state in TERMINAL_STATES:
            return pre_terminal
        terminal_state = STATE_PARTIAL if partial_causes else STATE_COMPLETE
        final = replace(
            pre_terminal if pre_terminal is not None else execution,
            state=terminal_state,
            partial_reason=partial_reason,
            coverage=execution_coverage,
            unavailable_checks=tuple(sorted(unavailable_checks)),
            terminal_at=now,
        )
        self._repository.save_execution(final)
        self._emit(
            "completeness_recorded",
            user_key,
            (execution.execution_key,),
            partial_reason,
            now,
            count=len(entries),
        )
        return final


__all__ = [
    "SearchWorker",
    "EntryEvaluation",
    "matches_criteria",
    "spec_from_requirement_version",
    "qualified_sort_key",
    "broader_sort_key",
]
