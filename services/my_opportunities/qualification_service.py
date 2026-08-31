"""Owner-scoped C5 qualification and evidence assessment for My Opportunities.

The service is intentionally route-free and provider-neutral.  AI may propose
evidence claims only through the bounded, fenced prompt seam below; this
module alone validates, evaluates, writes, and derives the qualification
gate.  Authorization always precedes retrieval and retrieval always precedes
AI: a member's evidence port is never called without a live grant admitting
its class, and the proposal provider is never called with nothing admitted.

Four assessment states and fifteen reason codes are closed and their pairing
is validated at construction.  ``purpose`` is fixed to
``qualification_verification`` everywhere; it is never a caller-supplied
parameter.  Evidence links carry only references (key, class, pinned
version) — never title or body text.  Practical fit is a structurally
separate member truth: the evaluator and the gate never read it.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Protocol, Sequence

from uuid import uuid4

from .evidence_port import (
    EVIDENCE_CLASSES,
    EVIDENCE_STRENGTHS,
    EvidencePort,
    EvidencePortError,
    EvidenceRecord,
    EvidenceReference,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_VERIFIED = "verified"
STATE_NOT_ESTABLISHED = "not_established"
STATE_APPEARS_UNMET = "appears_unmet"
STATE_REVIEW_UNAVAILABLE = "review_unavailable"
ASSESSMENT_STATES = frozenset(
    {STATE_VERIFIED, STATE_NOT_ESTABLISHED, STATE_APPEARS_UNMET, STATE_REVIEW_UNAVAILABLE}
)
# Canonical and closed: an outage label is not a fifth state.

REASONS_BY_STATE: Mapping[str, frozenset[str]] = {
    STATE_VERIFIED: frozenset({"direct_evidence", "corroborated", "alternative_path_met"}),
    STATE_NOT_ESTABLISHED: frozenset(
        {
            "no_evidence_in_scope",
            "ambiguous_evidence",
            "partial_evidence",
            "temporal_mismatch",
            "evidence_revoked",
            "classification_ambiguous",
            "candidate_evidence_only",
        }
    ),
    STATE_APPEARS_UNMET: frozenset({"affirmative_contradiction"}),
    STATE_REVIEW_UNAVAILABLE: frozenset(
        {"ai_unavailable", "evidence_source_unavailable", "timeout", "assessment_error"}
    ),
}

REQUIREMENT_CLASSES = frozenset({"required", "preferred"})
CLASSIFICATION_BASES = frozenset(
    {"stated_required", "stated_preferred", "ambiguous_default_required"}
)
GRANT_PURPOSE = "qualification_verification"  # fixed; the only value
GRANT_STATES = frozenset({"granted", "expired", "revoked"})  # derived
CLAIM_RELATIONS = frozenset({"supports", "partial", "contradicts"})
RECOMPUTE_CAUSES = frozenset(
    {"initial", "retry", "member_correction", "reading_flagged", "grant_revoked", "grant_expired"}
)
ACTORS = frozenset(
    {"system:search_worker/assessment", "system:recompute", "member", "correction"}
)
GATE_FULLY_VERIFIED = "fully_verified"
GATE_NOT_FULLY_VERIFIED = "not_fully_verified"
IDEMPOTENCY_TTL = timedelta(hours=24)  # C3 value
MONTH_DAYS = 30  # deterministic month unit for duration aggregation

MAX_USER_KEY_UTF16_UNITS = 300
MAX_IDEMPOTENCY_KEY_UTF16_UNITS = 200
MAX_CLAIMS = 256
MAX_MEMBER_CONTEXT_UTF16_UNITS = 4_000  # C3's request-text bound
MAX_NOTE_UTF16_UNITS = 2_000
MAX_CREDENTIAL_NAME_UNITS = 200
MAX_GRANT_RECORD_KEY_UNITS = 80
MAX_OPPORTUNITY_KEY_UTF16_UNITS = 200
MAX_OBSERVATION_KEY_UTF16_UNITS = 80

_STATE_PHRASES = {
    STATE_NOT_ESTABLISHED: "not established",
    STATE_APPEARS_UNMET: "appears unmet",
    STATE_REVIEW_UNAVAILABLE: "review unavailable",
}


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


def _bounded_string(
    value: object, label: str, maximum: int
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QualificationServiceError(f"{label}_required")
    normalized = value.strip()
    if _utf16_units(normalized) > maximum:
        raise QualificationServiceError(f"{label}_too_long")
    return normalized


def _require_user_key(value: object) -> str:
    return _bounded_string(value, "user_key", MAX_USER_KEY_UTF16_UNITS)


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
    raise QualificationServiceError("canonical_input_invalid")


def _canonical_hash(command: str, value: object) -> str:
    encoded = json.dumps(
        {"command": command, "input": _canonical_value(value)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_state_reason(state: str, reason_code: str) -> None:
    if state not in ASSESSMENT_STATES or reason_code not in REASONS_BY_STATE.get(state, frozenset()):
        raise ValueError("invalid_state_reason_pairing")


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


def _failure_message(code: str) -> str:
    return {
        "not_found": "That item is not available.",
        "user_key_required": "A member identity is required.",
        "user_key_too_long": "That member identity is too long.",
        "purpose_invalid": "That evidence grant's purpose is not supported.",
        "scope_invalid": "That evidence scope is not valid.",
        "expiry_invalid": "That grant's expiry is not valid.",
        "grant_terminal": "That grant can no longer be changed.",
        "idempotency_key_required": "A request key is required.",
        "idempotency_key_too_long": "That request key is too long.",
        "idempotency_mismatch": "That request key was already used for a different action.",
        "idempotency_result_invalid": "That request could not be replayed safely.",
        "spec_invalid": "That requirement version could not be assessed.",
        "note_required": "A note is required.",
        "note_too_long": "That note is too long.",
        "opportunity_key_required": "An opportunity is required.",
        "opportunity_key_too_long": "That opportunity reference is too long.",
        "observation_key_required": "An observation is required.",
        "observation_key_too_long": "That observation reference is too long.",
        "observation_archived": "That observation is already archived.",
        "cause_invalid": "That action is not available for this item.",
    }.get(code, "That request could not be completed.")


class QualificationServiceError(RuntimeError):
    """C3 pattern: ``.failure_code``, ``.recoverable``, ``.member_message``."""

    def __init__(self, failure_code: str, *, recoverable: bool | None = None) -> None:
        self.failure_code = failure_code
        self.recoverable = bool(recoverable) if recoverable is not None else False
        self.member_message = _failure_message(failure_code)
        super().__init__(failure_code)


class AssessmentPersistenceError(RuntimeError):
    """Raised when the repository write for an assessment row fails.

    NEVER converted into any assessment state; carries only content-free
    context (item key, requirement-version key). A future execution-outcome
    layer maps this to a ``partial`` outcome and excludes the entry — it is
    never fabricated here as a state.
    """

    def __init__(self, requirement_item_key: str, requirement_version_key: str) -> None:
        self.requirement_item_key = requirement_item_key
        self.requirement_version_key = requirement_version_key
        super().__init__("assessment_persistence_failed")


class RepositoryWriteError(RuntimeError):
    """Raised by a repository write when storage fails.

    Never becomes an assessment state; the service converts this into
    :class:`AssessmentPersistenceError` and fabricates no row.
    """


# ---------------------------------------------------------------------------
# Record shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequirementConstraints:
    minimum_duration_months: int | None = None  # > 0 when present
    credential_names: tuple[str, ...] = ()  # non-empty strings; a credential
    # requirement exists iff this tuple is non-empty
    recency_window_months: int | None = None  # ONLY when the posting
    # explicitly establishes a window (policy rule 6); None = any-time
    alternative_paths: tuple["RequirementConstraints", ...] = ()
    # genuine "or" alternatives (doc 07 §1); nesting depth 1 (a path may not
    # itself carry alternative_paths — validated during spec validation)


@dataclass(frozen=True)
class RequirementItemSpec:
    requirement_item_key: str
    ordinal: int  # > 0; evaluation order
    normalized_clause: str  # verbatim atomized reading
    requirement_class: str  # "required" | "preferred"
    classification_basis: str  # in CLASSIFICATION_BASES
    constraints: RequirementConstraints = RequirementConstraints()
    reading_flagged: bool = False  # doc 03 §6 `flagged`


@dataclass(frozen=True)
class RequirementVersionSpec:
    requirement_version_key: str
    opportunity_key: str
    items: tuple[RequirementItemSpec, ...]  # ordinal-unique, key-unique


@dataclass(frozen=True)
class GrantScope:
    evidence_classes: frozenset[str]  # subset of EVIDENCE_CLASSES, >= 1
    record_keys: frozenset[str] | None = None  # None => all records in the
    # classes; else exact allowlist


@dataclass(frozen=True)
class EvidenceGrant:
    grant_key: str
    user_key: str
    purpose: str  # always GRANT_PURPOSE
    scope: GrantScope
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None

    def __post_init__(self) -> None:
        if self.purpose != GRANT_PURPOSE:
            raise ValueError("purpose_invalid")

    def state(self, now: datetime) -> str:
        # revoked_at set -> "revoked"; now >= expires_at -> "expired"; else
        # "granted". revoked/expired are terminal; a new grant is a new
        # object (doc 03 §5).
        if self.revoked_at is not None:
            return "revoked"
        if now >= self.expires_at:
            return "expired"
        return "granted"


@dataclass(frozen=True)
class EvidenceLink:  # reference, never a copy
    reference: EvidenceReference
    admitting_grant_key: str  # grant live at write time
    relation: str  # in CLAIM_RELATIONS
    time_span: tuple[date, date] | None
    credential_name: str | None


@dataclass(frozen=True)
class AssessmentRevision:
    revision_number: int  # 1-based, contiguous
    state: str
    reason_code: str
    cause: str  # in RECOMPUTE_CAUSES
    actor: str  # in ACTORS
    evidence_links: tuple[EvidenceLink, ...]
    assessed_at: datetime

    def __post_init__(self) -> None:
        _validate_state_reason(self.state, self.reason_code)


@dataclass(frozen=True)
class Assessment:
    assessment_key: str
    user_key: str
    requirement_item_key: str
    requirement_version_key: str
    assessment_type: str  # "required" | "preferred" (doc 02 §1); ambiguous
    # placement stores "required"
    state: str
    reason_code: str
    current_revision_number: int
    evidence_links: tuple[EvidenceLink, ...]  # of the current revision
    assessed_at: datetime
    member_explanation: str  # derived member-language sentence (§2.10)

    def __post_init__(self) -> None:
        _validate_state_reason(self.state, self.reason_code)


@dataclass(frozen=True)
class PracticalFitObservation:
    observation_key: str
    user_key: str
    opportunity_key: str
    note_text: str  # <= 2000 units
    recorded_at: datetime
    archived_at: datetime | None


@dataclass(frozen=True)
class GateResult:
    requirement_version_key: str
    gate: str  # fully_verified | not_fully_verified
    required_total: int
    required_verified: int
    non_verified_required: tuple[tuple[str, str, str], ...]
    # (requirement_item_key, state, reason_code), ordinal order
    label: str  # e.g. "Fully verified" or
    # "5 of 6 required verified · 1 not established"


@dataclass(frozen=True)
class AssessmentRunResult:
    requirement_version_key: str
    assessments: tuple[Assessment, ...]  # ordinal order, all items
    gate: GateResult
    reused: tuple[str, ...]  # item keys whose existing current assessment
    # was reused (idempotent path)


# ---------------------------------------------------------------------------
# AI proposal seam (bounded, proposal-only — mirrors interpretation_service)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FencedEvidenceRecord:  # the ONLY place bodies may appear
    evidence_key: str
    evidence_class: str
    version: int
    title: str
    body: str


@dataclass(frozen=True)
class FencedAssessmentPrompt:
    requirement_version_key: str
    requirement_items: tuple[tuple[str, str], ...]  # (item_key, clause)
    evidence_records: tuple[FencedEvidenceRecord, ...]  # admitted ONLY
    member_context_text: str | None  # member's own words only

    def to_prompt_json(self) -> str:
        """Canonical JSON, sorted keys — the sole serialization path."""
        payload = {
            "requirement_version_key": self.requirement_version_key,
            "requirement_items": [
                {"requirement_item_key": item_key, "normalized_clause": clause}
                for item_key, clause in self.requirement_items
            ],
            "evidence_records": [
                {
                    "evidence_key": record.evidence_key,
                    "evidence_class": record.evidence_class,
                    "version": record.version,
                    "title": record.title,
                    "body": record.body,
                }
                for record in self.evidence_records
            ],
            "member_context_text": self.member_context_text,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_assessment_prompt(
    spec: RequirementVersionSpec,
    admitted: Sequence[EvidenceRecord],
    member_context_text: str | None,
) -> FencedAssessmentPrompt:
    """Pure allowlist serializer (doc 08 §2).

    May contain only the requirement clauses, the admitted records, and the
    member's own context text — nothing else. Takes no repository, no
    grants, no telemetry identifiers, and no user_key (the provider needs
    none): this is the fence asserted by the canary tests.
    """
    if member_context_text is None:
        normalized_context: str | None = None
    else:
        if not isinstance(member_context_text, str):
            raise QualificationServiceError("spec_invalid")
        stripped = member_context_text.strip()
        normalized_context = stripped or None
        if normalized_context is not None and _utf16_units(normalized_context) > MAX_MEMBER_CONTEXT_UTF16_UNITS:
            raise QualificationServiceError("spec_invalid")
    items = tuple((item.requirement_item_key, item.normalized_clause) for item in spec.items)
    records = tuple(
        FencedEvidenceRecord(
            evidence_key=record.evidence_key,
            evidence_class=record.evidence_class,
            version=record.version,
            title=record.title,
            body=record.body,
        )
        for record in admitted
    )
    return FencedAssessmentPrompt(
        requirement_version_key=spec.requirement_version_key,
        requirement_items=items,
        evidence_records=records,
        member_context_text=normalized_context,
    )


@dataclass(frozen=True)
class EvidenceClaim:
    requirement_item_key: str
    evidence_key: str
    evidence_class: str
    evidence_version: int
    relation: str  # supports|partial|contradicts
    time_span: tuple[date, date] | None = None  # proposed dated span read
    # from the record
    credential_name: str | None = None  # explicitly named credential


@dataclass(frozen=True)
class AssessmentProposalSet:
    claims: tuple[EvidenceClaim, ...]


class AssessmentProposalUnavailable(RuntimeError):
    """The bounded assessment proposal provider is unavailable."""


class AssessmentProposalTimeout(RuntimeError):
    """The bounded assessment proposal provider ran out of time."""


class ProposalContractError(ValueError):
    """A proposal violates the bounded fence contract."""


class AssessmentProposalProvider(Protocol):
    def propose(self, prompt: FencedAssessmentPrompt) -> AssessmentProposalSet: ...


class UnavailableAssessmentProvider:
    """Default provider: truthful unavailability, never an invented claim."""

    def propose(self, prompt: FencedAssessmentPrompt) -> AssessmentProposalSet:
        del prompt
        raise AssessmentProposalUnavailable("assessment_proposal_unavailable")


def _validate_proposal(
    proposal: object,
    spec: RequirementVersionSpec,
    admitted: Sequence[EvidenceRecord],
) -> tuple[EvidenceClaim, ...]:
    """Refuse a proposal that steps outside the bounded fence.

    A claim citing unadmitted or mis-versioned evidence invalidates the
    WHOLE proposal — nothing is silently dropped, because silent dropping
    would be silent gate weakening or strengthening.
    """
    if not isinstance(proposal, AssessmentProposalSet):
        raise ProposalContractError("proposal_invalid")
    claims = proposal.claims
    if isinstance(claims, (str, bytes)) or not isinstance(claims, Sequence):
        raise ProposalContractError("claims_invalid")
    if len(claims) > MAX_CLAIMS:
        raise ProposalContractError("too_many_claims")

    item_keys = {item.requirement_item_key for item in spec.items}
    admitted_by_triple = {
        (record.evidence_key, record.evidence_class, record.version): record for record in admitted
    }

    deduped: dict[tuple[str, tuple[str, str, int], str], EvidenceClaim] = {}
    for claim in claims:
        if not isinstance(claim, EvidenceClaim):
            raise ProposalContractError("claim_invalid")
        if claim.requirement_item_key not in item_keys:
            raise ProposalContractError("claim_item_unknown")
        triple = (claim.evidence_key, claim.evidence_class, claim.evidence_version)
        record = admitted_by_triple.get(triple)
        if record is None:
            raise ProposalContractError("claim_evidence_not_admitted")
        if record.strength not in EVIDENCE_STRENGTHS:
            # Important 7: an admitted record with an unrecognized strength
            # must refuse the whole proposal rather than silently vanishing
            # from evaluate_item's firm/candidate partition.
            raise ProposalContractError("claim_evidence_strength_invalid")
        if claim.relation not in CLAIM_RELATIONS:
            raise ProposalContractError("claim_relation_invalid")
        if claim.time_span is not None:
            span = claim.time_span
            if (
                not isinstance(span, tuple)
                or len(span) != 2
                or not all(isinstance(bound, date) for bound in span)
                or span[1] < span[0]
            ):
                raise ProposalContractError("claim_time_span_invalid")
            if record.time_span is not None:
                record_start, record_end = record.time_span
                claim_start, claim_end = span
                if claim_start < record_start or claim_end > record_end:
                    raise ProposalContractError("claim_time_span_exceeds_record")
        if claim.credential_name is not None:
            if not isinstance(claim.credential_name, str) or not (
                0 < len(claim.credential_name) <= MAX_CREDENTIAL_NAME_UNITS
            ):
                raise ProposalContractError("claim_credential_name_invalid")
        key = (claim.requirement_item_key, triple, claim.relation)
        # Duplicate claims (same item, same evidence triple, same relation)
        # collapse to one deterministically: first occurrence wins.
        deduped.setdefault(key, claim)
    return tuple(deduped.values())


# ---------------------------------------------------------------------------
# Audit sink (content-free; durable telemetry remains C9's)
# ---------------------------------------------------------------------------

_AUDIT_EVENT_KINDS = frozenset(
    {
        "grant_created",
        "grant_revoked",
        "assessment_written",
        "assessment_recomputed",
        "proposal_contract_violation",
        "persistence_failure",
    }
)


@dataclass(frozen=True)
class QualificationAuditEvent:
    event_kind: str
    user_key: str
    keys: tuple[str, ...]
    reason_code: str | None
    actor: str | None
    at: datetime


class AuditSink(Protocol):
    def emit(self, event: QualificationAuditEvent) -> None: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[QualificationAuditEvent] = []

    def emit(self, event: QualificationAuditEvent) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Repository Protocol + in-memory reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _IdempotencyRecord:
    command: str
    canonical_input_hash: str
    result: object
    expires_at: datetime


class QualificationRepository(Protocol):
    # grants
    def grant_for_owner(self, user_key: str, grant_key: str) -> EvidenceGrant | None: ...
    def grants_for_owner(self, user_key: str) -> tuple[EvidenceGrant, ...]: ...
    def save_grant(self, grant: EvidenceGrant) -> None: ...

    # assessments
    def assessment_for_owner(self, user_key: str, assessment_key: str) -> Assessment | None: ...
    def current_assessment_for_owner(
        self, user_key: str, requirement_item_key: str, requirement_version_key: str
    ) -> Assessment | None: ...
    def assessments_for_version(
        self, user_key: str, requirement_version_key: str
    ) -> tuple[Assessment, ...]: ...
    def assessments_linking_grant(self, user_key: str, grant_key: str) -> tuple[Assessment, ...]: ...
    def revisions_for_assessment(
        self, user_key: str, assessment_key: str
    ) -> tuple[AssessmentRevision, ...]: ...
    def append_assessment_revision(
        self, user_key: str, assessment: Assessment, revision: AssessmentRevision
    ) -> None: ...

    # practical fit
    def observation_for_owner(
        self, user_key: str, observation_key: str
    ) -> PracticalFitObservation | None: ...
    def observations_for_owner(
        self, user_key: str, opportunity_key: str | None = None
    ) -> tuple[PracticalFitObservation, ...]: ...
    def save_observation(self, observation: PracticalFitObservation) -> None: ...

    # idempotency (C3 shape)
    def _idempotency_record(self, user_key: str, key: str, now: datetime) -> _IdempotencyRecord | None: ...
    def _record_idempotency(
        self,
        user_key: str,
        key: str,
        command: str,
        digest: str,
        result: object,
        now: datetime,
    ) -> None: ...


class InMemoryQualificationRepository:
    """Fixture/P-1 persistence with the same owner boundary as the SQL model."""

    def __init__(self) -> None:
        self._grants: dict[str, EvidenceGrant] = {}
        self._assessments: dict[str, Assessment] = {}  # by assessment_key
        self._current_by_identity: dict[tuple[str, str, str], str] = {}
        # (user_key, requirement_item_key, requirement_version_key) -> assessment_key
        self._revisions: dict[str, list[AssessmentRevision]] = {}  # by assessment_key
        self._observations: dict[str, PracticalFitObservation] = {}
        self._idempotency: dict[tuple[str, str], _IdempotencyRecord] = {}
        self._lock = threading.RLock()

    # -- grants -------------------------------------------------------
    def grant_for_owner(self, user_key: str, grant_key: str) -> EvidenceGrant | None:
        grant = self._grants.get(grant_key)
        return grant if grant is not None and grant.user_key == user_key else None

    def grants_for_owner(self, user_key: str) -> tuple[EvidenceGrant, ...]:
        return tuple(grant for grant in self._grants.values() if grant.user_key == user_key)

    def save_grant(self, grant: EvidenceGrant) -> None:
        self._grants[grant.grant_key] = grant

    # -- assessments ----------------------------------------------------
    def assessment_for_owner(self, user_key: str, assessment_key: str) -> Assessment | None:
        assessment = self._assessments.get(assessment_key)
        return assessment if assessment is not None and assessment.user_key == user_key else None

    def current_assessment_for_owner(
        self, user_key: str, requirement_item_key: str, requirement_version_key: str
    ) -> Assessment | None:
        assessment_key = self._current_by_identity.get(
            (user_key, requirement_item_key, requirement_version_key)
        )
        return self._assessments.get(assessment_key) if assessment_key is not None else None

    def assessments_for_version(
        self, user_key: str, requirement_version_key: str
    ) -> tuple[Assessment, ...]:
        return tuple(
            assessment
            for assessment in self._assessments.values()
            if assessment.user_key == user_key
            and assessment.requirement_version_key == requirement_version_key
        )

    def assessments_linking_grant(self, user_key: str, grant_key: str) -> tuple[Assessment, ...]:
        return tuple(
            assessment
            for assessment in self._assessments.values()
            if assessment.user_key == user_key
            and any(link.admitting_grant_key == grant_key for link in assessment.evidence_links)
        )

    def revisions_for_assessment(
        self, user_key: str, assessment_key: str
    ) -> tuple[AssessmentRevision, ...]:
        if self.assessment_for_owner(user_key, assessment_key) is None:
            return ()
        return tuple(self._revisions.get(assessment_key, ()))

    def append_assessment_revision(
        self, user_key: str, assessment: Assessment, revision: AssessmentRevision
    ) -> None:
        """Atomically create the head on revision 1 / advance it on n+1.

        Enforces identity uniqueness (user x item x version) and
        ``revision_number == previous + 1``; raises :class:`RepositoryWriteError`
        on any storage failure.
        """
        identity = (user_key, assessment.requirement_item_key, assessment.requirement_version_key)
        if revision.revision_number == 1:
            if identity in self._current_by_identity:
                raise RepositoryWriteError("assessment_identity_exists")
            self._assessments[assessment.assessment_key] = assessment
            self._revisions[assessment.assessment_key] = [revision]
            self._current_by_identity[identity] = assessment.assessment_key
            return
        prior = self._assessments.get(assessment.assessment_key)
        if prior is None or prior.user_key != user_key:
            raise RepositoryWriteError("assessment_not_found")
        prior_revisions = self._revisions.get(assessment.assessment_key, [])
        if revision.revision_number != len(prior_revisions) + 1:
            raise RepositoryWriteError("revision_out_of_order")
        self._assessments[assessment.assessment_key] = assessment
        self._revisions[assessment.assessment_key].append(revision)

    # -- practical fit ----------------------------------------------------
    def observation_for_owner(
        self, user_key: str, observation_key: str
    ) -> PracticalFitObservation | None:
        observation = self._observations.get(observation_key)
        return observation if observation is not None and observation.user_key == user_key else None

    def observations_for_owner(
        self, user_key: str, opportunity_key: str | None = None
    ) -> tuple[PracticalFitObservation, ...]:
        return tuple(
            observation
            for observation in self._observations.values()
            if observation.user_key == user_key
            and (opportunity_key is None or observation.opportunity_key == opportunity_key)
        )

    def save_observation(self, observation: PracticalFitObservation) -> None:
        self._observations[observation.observation_key] = observation

    # -- idempotency (C3 shape) ----------------------------------------------
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
        result: object,
        now: datetime,
    ) -> None:
        self._idempotency[(user_key, idempotency_key)] = _IdempotencyRecord(
            command, canonical_input_hash, result, now + IDEMPOTENCY_TTL
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
                "grants": self._grants,
                "assessments": self._assessments,
                "revisions": {key: tuple(items) for key, items in self._revisions.items()},
                "observations": self._observations,
                "idempotency_keys": sorted(f"{owner}:{key}" for owner, key in self._idempotency),
            }
            return hashlib.sha256(
                json.dumps(_canonical_value(value), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()


class FailingQualificationRepository(InMemoryQualificationRepository):
    """Test double: raises :class:`RepositoryWriteError` from
    ``append_assessment_revision`` for the requirement items named in
    ``fail_on_revision_for`` — used by the persistence-failure tests.
    ``fail_from_revision_number`` (default 1, i.e. every write) restricts
    the failure to revisions at or above that number, so a test can let an
    item's initial write succeed and fail only a later recompute."""

    def __init__(
        self,
        *,
        fail_on_revision_for: set[str] | None = None,
        fail_from_revision_number: int = 1,
    ) -> None:
        super().__init__()
        self._fail_on_revision_for = set(fail_on_revision_for or ())
        self._fail_from_revision_number = fail_from_revision_number

    def append_assessment_revision(
        self, user_key: str, assessment: Assessment, revision: AssessmentRevision
    ) -> None:
        if (
            assessment.requirement_item_key in self._fail_on_revision_for
            and revision.revision_number >= self._fail_from_revision_number
        ):
            raise RepositoryWriteError("simulated_write_failure")
        super().append_assessment_revision(user_key, assessment, revision)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmittedRecord:
    record: EvidenceRecord
    admitting_grant_key: str


@dataclass(frozen=True)
class RevocationOutcome:
    grant: EvidenceGrant
    recomputed: tuple[Assessment, ...]


def _link_still_admitted(link: EvidenceLink, live_grants: Sequence[EvidenceGrant]) -> bool:
    """Is this link's referenced evidence still within scope of some live
    grant (not necessarily the one that originally admitted it)?"""
    for grant in live_grants:
        if link.reference.evidence_class not in grant.scope.evidence_classes:
            continue
        if grant.scope.record_keys is not None and link.reference.evidence_key not in grant.scope.record_keys:
            continue
        return True
    return False


def _validate_scope(scope: object) -> GrantScope:
    if not isinstance(scope, GrantScope):
        raise QualificationServiceError("scope_invalid")
    classes = scope.evidence_classes
    if not isinstance(classes, frozenset) or not classes or not classes <= EVIDENCE_CLASSES:
        raise QualificationServiceError("scope_invalid")
    record_keys = scope.record_keys
    if record_keys is not None:
        if not isinstance(record_keys, frozenset) or not record_keys:
            raise QualificationServiceError("scope_invalid")
        for item in record_keys:
            if (
                not isinstance(item, str)
                or not item
                or _utf16_units(item) > MAX_GRANT_RECORD_KEY_UNITS
            ):
                raise QualificationServiceError("scope_invalid")
    return GrantScope(evidence_classes=frozenset(classes), record_keys=record_keys)


def _validate_constraints(constraints: object) -> None:
    """Reject a malformed :class:`RequirementConstraints` before it can ever
    reach the evaluator.  Blocker fix: ``minimum_duration_months=0`` (or
    negative) previously sailed through unvalidated and produced a
    ``Verified`` result off zero claims/links -- a threshold of "at least
    zero" is not a genuine requirement."""
    if not isinstance(constraints, RequirementConstraints):
        raise QualificationServiceError("spec_invalid")
    duration = constraints.minimum_duration_months
    if duration is not None and (isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0):
        raise QualificationServiceError("spec_invalid")
    window = constraints.recency_window_months
    if window is not None and (isinstance(window, bool) or not isinstance(window, int) or window <= 0):
        raise QualificationServiceError("spec_invalid")
    if isinstance(constraints.credential_names, (str, bytes)) or not isinstance(
        constraints.credential_names, tuple
    ):
        raise QualificationServiceError("spec_invalid")
    for name in constraints.credential_names:
        if not isinstance(name, str) or not name.strip():
            raise QualificationServiceError("spec_invalid")


def _validate_spec(spec: object) -> RequirementVersionSpec:
    if not isinstance(spec, RequirementVersionSpec):
        raise QualificationServiceError("spec_invalid")
    if not spec.requirement_version_key or not spec.opportunity_key:
        raise QualificationServiceError("spec_invalid")
    if not spec.items:
        raise QualificationServiceError("spec_invalid")
    seen_keys: set[str] = set()
    seen_ordinals: set[int] = set()
    for item in spec.items:
        if not isinstance(item, RequirementItemSpec):
            raise QualificationServiceError("spec_invalid")
        if (
            not item.requirement_item_key
            or item.requirement_item_key in seen_keys
            or not isinstance(item.ordinal, int)
            or isinstance(item.ordinal, bool)
            or item.ordinal <= 0
            or item.ordinal in seen_ordinals
        ):
            raise QualificationServiceError("spec_invalid")
        seen_keys.add(item.requirement_item_key)
        seen_ordinals.add(item.ordinal)
        if item.requirement_class not in REQUIREMENT_CLASSES:
            raise QualificationServiceError("spec_invalid")
        if item.classification_basis not in CLASSIFICATION_BASES:
            raise QualificationServiceError("spec_invalid")
        _validate_constraints(item.constraints)
        for path in item.constraints.alternative_paths:
            if path.alternative_paths:
                raise QualificationServiceError("spec_invalid")
            _validate_constraints(path)
    return replace(spec, items=tuple(sorted(spec.items, key=lambda item: item.ordinal)))


def _expect(value: object, expected_type: type) -> object:
    if not isinstance(value, expected_type):
        raise QualificationServiceError("idempotency_result_invalid")
    return value


class QualificationService:
    def __init__(
        self,
        repository: QualificationRepository,
        *,
        evidence_ports: Mapping[str, EvidencePort] | None = None,
        provider: AssessmentProposalProvider | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.repository = repository
        self._evidence_ports: dict[str, EvidencePort] = dict(evidence_ports) if evidence_ports else {}
        self._provider = provider or UnavailableAssessmentProvider()
        self._audit_sink = audit_sink or InMemoryAuditSink()
        # Minor a: a conforming repository need not expose a private
        # ``_lock`` attribute; fall back to owning our own reentrant lock
        # rather than requiring that implementation detail.
        self._lock = getattr(repository, "_lock", None) or threading.RLock()

    # -- idempotency plumbing (C3 pattern) -----------------------------

    def _begin(
        self, user_key: str, idempotency_key: str, command: str, canonical: object, now: datetime
    ) -> tuple[object | None, str, str]:
        key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        digest = _canonical_hash(command, canonical)
        record = self.repository._idempotency_record(user_key, key, now)
        if record is not None:
            if record.command == command and record.canonical_input_hash == digest:
                return record.result, key, digest
            raise QualificationServiceError("idempotency_mismatch")
        return None, key, digest

    def _finish(
        self, user_key: str, idempotency_key: str, command: str, digest: str, result: object, now: datetime
    ) -> None:
        self.repository._record_idempotency(user_key, idempotency_key, command, digest, result, now)

    def _emit(
        self,
        event_kind: str,
        user_key: str,
        keys: Sequence[str],
        reason_code: str | None,
        actor: str | None,
        at: datetime,
    ) -> None:
        self._audit_sink.emit(
            QualificationAuditEvent(
                event_kind=event_kind,
                user_key=user_key,
                keys=tuple(keys),
                reason_code=reason_code,
                actor=actor,
                at=at,
            )
        )

    # -- grants ---------------------------------------------------------

    def create_grant(
        self,
        user_key: str,
        *,
        scope: GrantScope,
        expires_at: datetime,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> EvidenceGrant:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        scope = _validate_scope(scope)
        if not isinstance(expires_at, datetime) or expires_at.tzinfo is None:
            raise QualificationServiceError("expiry_invalid")
        expires_at = expires_at.astimezone(timezone.utc)
        if expires_at <= now:
            raise QualificationServiceError("expiry_invalid")
        command = "create_grant"
        canonical = {
            "scope_classes": sorted(scope.evidence_classes),
            "scope_record_keys": sorted(scope.record_keys) if scope.record_keys is not None else None,
            "expires_at": expires_at,
        }
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, EvidenceGrant)
            grant = EvidenceGrant(
                grant_key=_opaque_key(),
                user_key=user_key,
                purpose=GRANT_PURPOSE,
                scope=scope,
                granted_at=now,
                expires_at=expires_at,
                revoked_at=None,
            )
            self.repository.save_grant(grant)
            self._finish(user_key, key, command, digest, grant, now)
            self._emit("grant_created", user_key, (grant.grant_key,), None, None, now)
            return grant

    def get_grant(self, user_key: str, grant_key: str) -> EvidenceGrant:
        user_key = _require_user_key(user_key)
        with self._lock:
            grant = self.repository.grant_for_owner(user_key, grant_key)
            if grant is None:
                raise QualificationServiceError("not_found")
            return grant

    def list_grants(self, user_key: str, *, now: datetime | None = None) -> tuple[EvidenceGrant, ...]:
        # `now` is accepted, not consumed here: each returned EvidenceGrant's
        # derived state is read via `.state(now)` by the caller, so there is
        # nothing for this method itself to filter or compute from it.
        user_key = _require_user_key(user_key)
        with self._lock:
            return tuple(
                sorted(
                    self.repository.grants_for_owner(user_key),
                    key=lambda grant: (grant.granted_at, grant.grant_key),
                )
            )

    def revoke_grant(
        self,
        user_key: str,
        *,
        grant_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> RevocationOutcome:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        command = "revoke_grant"
        canonical = {"grant_key": grant_key}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, RevocationOutcome)
            grant = self.repository.grant_for_owner(user_key, grant_key)
            if grant is None:
                raise QualificationServiceError("not_found")
            if grant.state(now) != "granted":
                raise QualificationServiceError("grant_terminal")
            revoked = replace(grant, revoked_at=now)
            self.repository.save_grant(revoked)
            self._emit("grant_revoked", user_key, (grant_key,), None, None, now)
            # Blocker 2: a link's admitting_grant_key is only rewritten when
            # that exact assessment changes, so it can go stale -- pointing
            # at an earlier-revoked grant -- once a *different* grant is
            # revoked. Scanning only assessments_linking_grant(grant_key)
            # would then miss it. Build the candidate set from assessments
            # linked to ANY of the owner's grants instead (deduped by item x
            # version); _recompute_after_authorization_loss already no-ops
            # when nothing actually died, so the wider scan is safe.
            candidates: dict[tuple[str, str], Assessment] = {}
            for owned_grant in self.repository.grants_for_owner(user_key):
                for assessment in self.repository.assessments_linking_grant(user_key, owned_grant.grant_key):
                    candidates[
                        (assessment.requirement_item_key, assessment.requirement_version_key)
                    ] = assessment
            recomputed: list[Assessment] = []
            try:
                for (item_key, version_key), assessment in candidates.items():
                    updated = self._recompute_after_authorization_loss(
                        user_key,
                        item_key,
                        version_key,
                        cause="grant_revoked",
                        actor="system:recompute",
                        now=now,
                    )
                    if updated.current_revision_number != assessment.current_revision_number:
                        recomputed.append(updated)
            except AssessmentPersistenceError:
                # Important 9: the grant is already durably revoked by this
                # point. Without a receipt, a retry of this same
                # idempotency_key would see grant_terminal instead of
                # replaying the (partial) outcome already produced -- record
                # the partial outcome before re-raising so replay stays safe.
                partial_outcome = RevocationOutcome(grant=revoked, recomputed=tuple(recomputed))
                self._finish(user_key, key, command, digest, partial_outcome, now)
                raise
            outcome = RevocationOutcome(grant=revoked, recomputed=tuple(recomputed))
            self._finish(user_key, key, command, digest, outcome, now)
            return outcome

    def recompute_for_expired_grants(
        self,
        user_key: str,
        *,
        spec_by_version: Mapping[str, RequirementVersionSpec],
        now: datetime | None = None,
    ) -> tuple[Assessment, ...]:
        """Named expiry recompute path (doc 03 §5).

        Finds current assessments linked to any of the owner's grants where
        at least one live grant has since expired, and recomputes affected
        assessments with ``cause="grant_expired"``, ``actor="system:recompute"``.
        Content-blind about evidence it can no longer read: it never
        re-reads evidence content and never calls the proposal provider
        again, it only checks whether previously-linked evidence references
        remain authorized under a still-live grant.

        ``spec_by_version`` is currently unused by this structural
        recompute (the no-op guard in ``_recompute_after_authorization_loss``
        makes scoping by spec unnecessary); it is retained only for
        signature compatibility with future callers (e.g. a job that wants
        to hint which versions are in play) and is advisory, not a filter.
        """
        user_key = _require_user_key(user_key)
        now = _utc(now)
        del spec_by_version
        with self._lock:
            expired_grants = tuple(
                grant for grant in self.repository.grants_for_owner(user_key) if grant.state(now) == "expired"
            )
            if not expired_grants:
                return ()
            # Blocker 2 (mirrors revoke_grant): build the candidate set from
            # assessments linked to ANY of the owner's grants, not just the
            # currently-expired ones -- a link's admitting_grant_key can go
            # stale, pointing at an earlier-revoked/expired grant that is no
            # longer itself in `expired_grants`. The recompute is a safe
            # no-op for any candidate that has not actually lost
            # authorization.
            candidates: dict[tuple[str, str], Assessment] = {}
            for owned_grant in self.repository.grants_for_owner(user_key):
                for assessment in self.repository.assessments_linking_grant(user_key, owned_grant.grant_key):
                    candidates[
                        (assessment.requirement_item_key, assessment.requirement_version_key)
                    ] = assessment
            recomputed: list[Assessment] = []
            for (item_key, version_key), assessment in candidates.items():
                updated = self._recompute_after_authorization_loss(
                    user_key,
                    item_key,
                    version_key,
                    cause="grant_expired",
                    actor="system:recompute",
                    now=now,
                )
                if updated.current_revision_number != assessment.current_revision_number:
                    recomputed.append(updated)
            return tuple(recomputed)

    def _recompute_after_authorization_loss(
        self,
        user_key: str,
        requirement_item_key: str,
        requirement_version_key: str,
        *,
        cause: str,
        actor: str,
        now: datetime,
    ) -> Assessment:
        assessment = self.repository.current_assessment_for_owner(
            user_key, requirement_item_key, requirement_version_key
        )
        if assessment is None:
            raise QualificationServiceError("not_found")
        live_grants = tuple(
            grant for grant in self.repository.grants_for_owner(user_key) if grant.state(now) == "granted"
        )
        surviving_links = tuple(
            link for link in assessment.evidence_links if _link_still_admitted(link, live_grants)
        )
        if surviving_links == assessment.evidence_links:
            return assessment  # nothing died; no new revision (no no-ops)

        surviving_contradicts = any(link.relation == "contradicts" for link in surviving_links)
        if assessment.state == STATE_VERIFIED:
            # Doc 03 §5's named override: lost evidence behind a verified
            # conclusion collapses to a truthful not_established/evidence_revoked.
            new_state, new_reason = STATE_NOT_ESTABLISHED, "evidence_revoked"
        elif assessment.state == STATE_APPEARS_UNMET and not surviving_contradicts:
            # Blocker 3: an appears_unmet conclusion is entirely load-bearing
            # on its contradiction link(s). If the contradicting evidence
            # itself lost authorization, the "requirement isn't met" signal
            # no longer stands and must not silently survive with zero (or
            # non-contradicting) links -- collapse the same way verified does.
            new_state, new_reason = STATE_NOT_ESTABLISHED, "evidence_revoked"
        elif assessment.state != STATE_REVIEW_UNAVAILABLE and not surviving_links:
            # Any other non-outage state whose entire evidentiary basis just
            # disappeared is likewise no longer a live conclusion.
            new_state, new_reason = STATE_NOT_ESTABLISHED, "evidence_revoked"
        else:
            # Otherwise: keep this assessment's own state and reason, only
            # dropping the dead references from its links.
            new_state, new_reason = assessment.state, assessment.reason_code

        next_number = assessment.current_revision_number + 1
        revision = AssessmentRevision(
            revision_number=next_number,
            state=new_state,
            reason_code=new_reason,
            cause=cause,
            actor=actor,
            evidence_links=surviving_links,
            assessed_at=now,
        )
        updated = replace(
            assessment,
            state=new_state,
            reason_code=new_reason,
            current_revision_number=next_number,
            evidence_links=surviving_links,
            assessed_at=now,
            member_explanation=_member_explanation(new_state, new_reason),
        )
        try:
            self.repository.append_assessment_revision(user_key, updated, revision)
        except RepositoryWriteError as error:
            self._emit(
                "persistence_failure",
                user_key,
                (requirement_item_key, requirement_version_key),
                None,
                actor,
                now,
            )
            raise AssessmentPersistenceError(requirement_item_key, requirement_version_key) from error
        self._emit("assessment_recomputed", user_key, (updated.assessment_key,), new_reason, actor, now)
        return updated

    # -- admitted-evidence pipeline (§1.8, §2.6) -------------------------

    def _admitted_evidence(self, user_key: str, now: datetime) -> tuple[AdmittedRecord, ...]:
        live_grants = tuple(
            sorted(
                (grant for grant in self.repository.grants_for_owner(user_key) if grant.state(now) == "granted"),
                key=lambda grant: (grant.granted_at, grant.grant_key),
            )
        )
        if not live_grants:
            return ()
        classes_needed: set[str] = set()
        for grant in live_grants:
            classes_needed |= grant.scope.evidence_classes

        admitted: list[AdmittedRecord] = []
        seen_keys: set[tuple[str, str]] = set()
        for evidence_class in sorted(classes_needed):
            port = self._evidence_ports.get(evidence_class)
            if port is None:
                continue  # no port registered for this class: nothing to call
            records = port.list_records_for_owner(user_key)  # may raise EvidencePortError
            for record in records:
                if record.evidence_class != evidence_class:
                    continue
                identity = (record.evidence_key, record.evidence_class)
                if identity in seen_keys:
                    continue
                for grant in live_grants:
                    if evidence_class not in grant.scope.evidence_classes:
                        continue
                    if grant.scope.record_keys is not None and record.evidence_key not in grant.scope.record_keys:
                        continue
                    # First live grant (by determinism order) admitting it.
                    admitted.append(AdmittedRecord(record=record, admitting_grant_key=grant.grant_key))
                    seen_keys.add(identity)
                    break
        return tuple(admitted)

    # -- initial assessment (§2.8) ---------------------------------------

    def assess_requirements(
        self,
        user_key: str,
        *,
        spec: RequirementVersionSpec,
        member_context_text: str | None = None,
        actor: str = "system:search_worker/assessment",
        now: datetime | None = None,
    ) -> AssessmentRunResult:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        spec = _validate_spec(spec)
        if actor not in ACTORS:
            raise QualificationServiceError("spec_invalid")
        with self._lock:
            assessments: dict[str, Assessment] = {}
            reused: list[str] = []
            work_items: list[RequirementItemSpec] = []
            for item in spec.items:
                current = self.repository.current_assessment_for_owner(
                    user_key, item.requirement_item_key, spec.requirement_version_key
                )
                if current is not None:
                    assessments[item.requirement_item_key] = current
                    reused.append(item.requirement_item_key)
                else:
                    work_items.append(item)

            if work_items:
                self._run_initial_work_set(
                    user_key, spec, work_items, member_context_text, actor, now, assessments
                )

            ordered = tuple(assessments[item.requirement_item_key] for item in spec.items)
            gate = _derive_gate(spec, ordered)
            return AssessmentRunResult(
                requirement_version_key=spec.requirement_version_key,
                assessments=ordered,
                gate=gate,
                reused=tuple(reused),
            )

    def _run_initial_work_set(
        self,
        user_key: str,
        spec: RequirementVersionSpec,
        work_items: Sequence[RequirementItemSpec],
        member_context_text: str | None,
        actor: str,
        now: datetime,
        assessments: dict[str, Assessment],
    ) -> None:
        # Important 8: a flagged reading is a deterministic answer
        # (classification_ambiguous) and must never trigger an evidence
        # read or an AI call -- split those items out before any
        # grant/port/provider step. evaluate_item's own reading_flagged
        # check (§2.8a step 0) is kept as defense-in-depth beneath this.
        flagged_items = [item for item in work_items if item.reading_flagged]
        unflagged_items = [item for item in work_items if not item.reading_flagged]
        if flagged_items:
            self._write_uniform_outcome(
                user_key,
                spec,
                flagged_items,
                STATE_NOT_ESTABLISHED,
                "classification_ambiguous",
                "initial",
                actor,
                now,
                assessments,
            )
        if not unflagged_items:
            return
        work_items = unflagged_items

        live_grants = tuple(
            grant for grant in self.repository.grants_for_owner(user_key) if grant.state(now) == "granted"
        )
        if not live_grants:
            # No live grant admits anything: no port call, no AI call
            # (authorization before retrieval/AI).
            self._write_uniform_outcome(
                user_key, spec, work_items, STATE_NOT_ESTABLISHED, "no_evidence_in_scope", "initial", actor, now, assessments
            )
            return

        try:
            admitted = self._admitted_evidence(user_key, now)
        except EvidencePortError:
            self._write_uniform_outcome(
                user_key,
                spec,
                work_items,
                STATE_REVIEW_UNAVAILABLE,
                "evidence_source_unavailable",
                "initial",
                actor,
                now,
                assessments,
            )
            return

        if not admitted:
            # Grants live but nothing in scope: still nothing authorized to
            # send, so still no AI call.
            self._write_uniform_outcome(
                user_key, spec, work_items, STATE_NOT_ESTABLISHED, "no_evidence_in_scope", "initial", actor, now, assessments
            )
            return

        admitted_records = tuple(entry.record for entry in admitted)
        prompt = build_assessment_prompt(spec, admitted_records, member_context_text)
        try:
            proposal = self._provider.propose(prompt)
            claims = _validate_proposal(proposal, spec, admitted_records)
        except AssessmentProposalUnavailable:
            self._write_uniform_outcome(
                user_key, spec, work_items, STATE_REVIEW_UNAVAILABLE, "ai_unavailable", "initial", actor, now, assessments
            )
            return
        except AssessmentProposalTimeout:
            self._write_uniform_outcome(
                user_key, spec, work_items, STATE_REVIEW_UNAVAILABLE, "timeout", "initial", actor, now, assessments
            )
            return
        except ProposalContractError:
            self._emit(
                "proposal_contract_violation",
                user_key,
                tuple(item.requirement_item_key for item in work_items),
                None,
                actor,
                now,
            )
            self._write_uniform_outcome(
                user_key, spec, work_items, STATE_REVIEW_UNAVAILABLE, "assessment_error", "initial", actor, now, assessments
            )
            return
        except Exception:
            self._write_uniform_outcome(
                user_key, spec, work_items, STATE_REVIEW_UNAVAILABLE, "assessment_error", "initial", actor, now, assessments
            )
            return

        claims_by_item: dict[str, list[EvidenceClaim]] = {}
        for claim in claims:
            claims_by_item.setdefault(claim.requirement_item_key, []).append(claim)
        admitted_by_triple = {
            (entry.record.evidence_key, entry.record.evidence_class, entry.record.version): entry
            for entry in admitted
        }

        for item in work_items:  # already in ordinal order
            item_claims = tuple(claims_by_item.get(item.requirement_item_key, ()))
            state, reason, links = evaluate_item(item, item_claims, admitted_by_triple, evaluation_time=now)

            # Per-write grant recheck (§2.8 step 8a): re-verify each link's
            # admitting grant is STILL live at write time.
            live_now = tuple(
                grant for grant in self.repository.grants_for_owner(user_key) if grant.state(now) == "granted"
            )
            live_keys = {grant.grant_key for grant in live_now}
            if any(link.admitting_grant_key not in live_keys for link in links):
                reduced_claims = tuple(
                    claim
                    for claim in item_claims
                    if admitted_by_triple[
                        (claim.evidence_key, claim.evidence_class, claim.evidence_version)
                    ].admitting_grant_key
                    in live_keys
                )
                state, reason, links = evaluate_item(
                    item, reduced_claims, admitted_by_triple, evaluation_time=now
                )

            assessment = Assessment(
                assessment_key=_opaque_key(),
                user_key=user_key,
                requirement_item_key=item.requirement_item_key,
                requirement_version_key=spec.requirement_version_key,
                assessment_type=item.requirement_class,
                state=state,
                reason_code=reason,
                current_revision_number=1,
                evidence_links=links,
                assessed_at=now,
                member_explanation=_member_explanation(state, reason),
            )
            revision = AssessmentRevision(
                revision_number=1,
                state=state,
                reason_code=reason,
                cause="initial",
                actor=actor,
                evidence_links=links,
                assessed_at=now,
            )
            try:
                self.repository.append_assessment_revision(user_key, assessment, revision)
            except RepositoryWriteError as error:
                self._emit(
                    "persistence_failure",
                    user_key,
                    (item.requirement_item_key, spec.requirement_version_key),
                    None,
                    actor,
                    now,
                )
                raise AssessmentPersistenceError(item.requirement_item_key, spec.requirement_version_key) from error
            self._emit("assessment_written", user_key, (assessment.assessment_key,), reason, actor, now)
            assessments[item.requirement_item_key] = assessment

    def _write_uniform_outcome(
        self,
        user_key: str,
        spec: RequirementVersionSpec,
        items: Sequence[RequirementItemSpec],
        state: str,
        reason: str,
        cause: str,
        actor: str,
        now: datetime,
        assessments: dict[str, Assessment],
    ) -> None:
        for item in items:
            assessment = Assessment(
                assessment_key=_opaque_key(),
                user_key=user_key,
                requirement_item_key=item.requirement_item_key,
                requirement_version_key=spec.requirement_version_key,
                assessment_type=item.requirement_class,
                state=state,
                reason_code=reason,
                current_revision_number=1,
                evidence_links=(),
                assessed_at=now,
                member_explanation=_member_explanation(state, reason),
            )
            revision = AssessmentRevision(
                revision_number=1,
                state=state,
                reason_code=reason,
                cause=cause,
                actor=actor,
                evidence_links=(),
                assessed_at=now,
            )
            try:
                self.repository.append_assessment_revision(user_key, assessment, revision)
            except RepositoryWriteError as error:
                self._emit(
                    "persistence_failure",
                    user_key,
                    (item.requirement_item_key, spec.requirement_version_key),
                    None,
                    actor,
                    now,
                )
                raise AssessmentPersistenceError(item.requirement_item_key, spec.requirement_version_key) from error
            self._emit("assessment_written", user_key, (assessment.assessment_key,), reason, actor, now)
            assessments[item.requirement_item_key] = assessment

    # -- recompute (retry / correction / reading-flagged) ----------------

    def retry_assessment(
        self,
        user_key: str,
        *,
        spec: RequirementVersionSpec,
        requirement_item_key: str,
        now: datetime | None = None,
    ) -> Assessment:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        spec = _validate_spec(spec)
        with self._lock:
            current = self.repository.current_assessment_for_owner(
                user_key, requirement_item_key, spec.requirement_version_key
            )
            if current is None:
                raise QualificationServiceError("not_found")
            if current.state != STATE_REVIEW_UNAVAILABLE:
                raise QualificationServiceError("cause_invalid")
            return self._recompute_item(
                user_key, spec, requirement_item_key, cause="retry", actor="member", now=now
            )

    def reassess_after_correction(
        self,
        user_key: str,
        *,
        spec: RequirementVersionSpec,
        requirement_item_key: str,
        cause: str,
        member_context_text: str | None = None,
        now: datetime | None = None,
    ) -> Assessment:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        spec = _validate_spec(spec)
        if cause not in ("member_correction", "reading_flagged"):
            raise QualificationServiceError("cause_invalid")
        actor = "member" if cause == "member_correction" else "correction"
        with self._lock:
            current = self.repository.current_assessment_for_owner(
                user_key, requirement_item_key, spec.requirement_version_key
            )
            if current is None:
                raise QualificationServiceError("not_found")
            return self._recompute_item(
                user_key,
                spec,
                requirement_item_key,
                cause=cause,
                actor=actor,
                now=now,
                member_context_text=member_context_text,
            )

    def _recompute_item(
        self,
        user_key: str,
        spec: RequirementVersionSpec,
        requirement_item_key: str,
        *,
        cause: str,
        actor: str,
        now: datetime,
        member_context_text: str | None = None,
    ) -> Assessment:
        item = next((i for i in spec.items if i.requirement_item_key == requirement_item_key), None)
        if item is None:
            raise QualificationServiceError("not_found")
        current = self.repository.current_assessment_for_owner(
            user_key, requirement_item_key, spec.requirement_version_key
        )
        if current is None:
            raise QualificationServiceError("not_found")

        # Important 8: same short-circuit as _run_initial_work_set -- a
        # flagged reading is deterministic and must never trigger an
        # evidence read or an AI call, even on recompute.
        if item.reading_flagged:
            return self._append_recompute_revision(
                user_key, current, STATE_NOT_ESTABLISHED, "classification_ambiguous", (), cause, actor, now
            )

        live_grants = tuple(
            grant for grant in self.repository.grants_for_owner(user_key) if grant.state(now) == "granted"
        )
        if not live_grants:
            return self._append_recompute_revision(
                user_key, current, STATE_NOT_ESTABLISHED, "no_evidence_in_scope", (), cause, actor, now
            )
        try:
            admitted = self._admitted_evidence(user_key, now)
        except EvidencePortError:
            return self._append_recompute_revision(
                user_key, current, STATE_REVIEW_UNAVAILABLE, "evidence_source_unavailable", (), cause, actor, now
            )
        if not admitted:
            return self._append_recompute_revision(
                user_key, current, STATE_NOT_ESTABLISHED, "no_evidence_in_scope", (), cause, actor, now
            )

        admitted_records = tuple(entry.record for entry in admitted)
        prompt = build_assessment_prompt(spec, admitted_records, member_context_text)
        try:
            proposal = self._provider.propose(prompt)
            claims = _validate_proposal(proposal, spec, admitted_records)
        except AssessmentProposalUnavailable:
            return self._append_recompute_revision(
                user_key, current, STATE_REVIEW_UNAVAILABLE, "ai_unavailable", (), cause, actor, now
            )
        except AssessmentProposalTimeout:
            return self._append_recompute_revision(
                user_key, current, STATE_REVIEW_UNAVAILABLE, "timeout", (), cause, actor, now
            )
        except ProposalContractError:
            self._emit("proposal_contract_violation", user_key, (requirement_item_key,), None, actor, now)
            return self._append_recompute_revision(
                user_key, current, STATE_REVIEW_UNAVAILABLE, "assessment_error", (), cause, actor, now
            )
        except Exception:
            return self._append_recompute_revision(
                user_key, current, STATE_REVIEW_UNAVAILABLE, "assessment_error", (), cause, actor, now
            )

        admitted_by_triple = {
            (entry.record.evidence_key, entry.record.evidence_class, entry.record.version): entry
            for entry in admitted
        }
        item_claims = tuple(claim for claim in claims if claim.requirement_item_key == requirement_item_key)
        state, reason, links = evaluate_item(item, item_claims, admitted_by_triple, evaluation_time=now)

        live_keys = {grant.grant_key for grant in live_grants}
        if any(link.admitting_grant_key not in live_keys for link in links):
            reduced_claims = tuple(
                claim
                for claim in item_claims
                if admitted_by_triple[
                    (claim.evidence_key, claim.evidence_class, claim.evidence_version)
                ].admitting_grant_key
                in live_keys
            )
            state, reason, links = evaluate_item(item, reduced_claims, admitted_by_triple, evaluation_time=now)

        return self._append_recompute_revision(user_key, current, state, reason, links, cause, actor, now)

    def _append_recompute_revision(
        self,
        user_key: str,
        current: Assessment,
        state: str,
        reason: str,
        links: tuple[EvidenceLink, ...],
        cause: str,
        actor: str,
        now: datetime,
    ) -> Assessment:
        if state == current.state and reason == current.reason_code and links == current.evidence_links:
            return current  # unchanged outcome: history never accretes no-ops

        next_number = current.current_revision_number + 1
        updated = replace(
            current,
            state=state,
            reason_code=reason,
            current_revision_number=next_number,
            evidence_links=links,
            assessed_at=now,
            member_explanation=_member_explanation(state, reason),
        )
        revision = AssessmentRevision(
            revision_number=next_number,
            state=state,
            reason_code=reason,
            cause=cause,
            actor=actor,
            evidence_links=links,
            assessed_at=now,
        )
        try:
            self.repository.append_assessment_revision(user_key, updated, revision)
        except RepositoryWriteError as error:
            self._emit(
                "persistence_failure",
                user_key,
                (current.requirement_item_key, current.requirement_version_key),
                None,
                actor,
                now,
            )
            raise AssessmentPersistenceError(
                current.requirement_item_key, current.requirement_version_key
            ) from error
        self._emit("assessment_recomputed", user_key, (updated.assessment_key,), reason, actor, now)
        return updated

    # -- reads ------------------------------------------------------------

    def get_assessment(self, user_key: str, assessment_key: str) -> Assessment:
        user_key = _require_user_key(user_key)
        with self._lock:
            assessment = self.repository.assessment_for_owner(user_key, assessment_key)
            if assessment is None:
                raise QualificationServiceError("not_found")
            return assessment

    def list_assessments(self, user_key: str, requirement_version_key: str) -> tuple[Assessment, ...]:
        user_key = _require_user_key(user_key)
        with self._lock:
            return tuple(
                sorted(
                    self.repository.assessments_for_version(user_key, requirement_version_key),
                    key=lambda assessment: assessment.requirement_item_key,
                )
            )

    def assessment_history(self, user_key: str, assessment_key: str) -> tuple[AssessmentRevision, ...]:
        user_key = _require_user_key(user_key)
        with self._lock:
            assessment = self.repository.assessment_for_owner(user_key, assessment_key)
            if assessment is None:
                raise QualificationServiceError("not_found")
            return tuple(
                sorted(
                    self.repository.revisions_for_assessment(user_key, assessment_key),
                    key=lambda revision: revision.revision_number,
                )
            )

    def derive_gate(self, user_key: str, *, spec: RequirementVersionSpec) -> GateResult:
        """Pure over current assessments. Never reads preferred states,
        practical fit, or grants."""
        user_key = _require_user_key(user_key)
        spec = _validate_spec(spec)
        with self._lock:
            current = tuple(
                self.repository.current_assessment_for_owner(
                    user_key, item.requirement_item_key, spec.requirement_version_key
                )
                for item in spec.items
            )
            return _derive_gate(spec, current)

    # -- practical fit (separate truth) ------------------------------------

    def record_practical_fit(
        self,
        user_key: str,
        *,
        opportunity_key: str,
        note_text: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> PracticalFitObservation:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        opportunity_key = _bounded_string(
            opportunity_key, "opportunity_key", MAX_OPPORTUNITY_KEY_UTF16_UNITS
        )
        if not isinstance(note_text, str) or not note_text.strip():
            raise QualificationServiceError("note_required")
        normalized_note = note_text.strip()
        if _utf16_units(normalized_note) > MAX_NOTE_UTF16_UNITS:
            raise QualificationServiceError("note_too_long")
        command = "record_practical_fit"
        canonical = {"opportunity_key": opportunity_key, "note_text": normalized_note}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, PracticalFitObservation)
            observation = PracticalFitObservation(
                observation_key=_opaque_key(),
                user_key=user_key,
                opportunity_key=opportunity_key,
                note_text=normalized_note,
                recorded_at=now,
                archived_at=None,
            )
            self.repository.save_observation(observation)
            self._finish(user_key, key, command, digest, observation, now)
            return observation

    def list_practical_fit(
        self, user_key: str, *, opportunity_key: str | None = None
    ) -> tuple[PracticalFitObservation, ...]:
        user_key = _require_user_key(user_key)
        with self._lock:
            return tuple(
                sorted(
                    self.repository.observations_for_owner(user_key, opportunity_key),
                    key=lambda observation: observation.recorded_at,
                )
            )

    def archive_practical_fit(
        self,
        user_key: str,
        *,
        observation_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> PracticalFitObservation:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        observation_key = _bounded_string(
            observation_key, "observation_key", MAX_OBSERVATION_KEY_UTF16_UNITS
        )
        command = "archive_practical_fit"
        canonical = {"observation_key": observation_key}
        with self._lock:
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, PracticalFitObservation)
            observation = self.repository.observation_for_owner(user_key, observation_key)
            if observation is None:
                raise QualificationServiceError("not_found")
            if observation.archived_at is not None:
                raise QualificationServiceError("observation_archived")
            archived = replace(observation, archived_at=now)
            self.repository.save_observation(archived)
            self._finish(user_key, key, command, digest, archived, now)
            return archived


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _merge_and_sum(spans: Sequence[tuple[tuple[date, date], str]]) -> tuple[int, set[str]]:
    """Merge overlapping/adjacent date spans and sum total days.

    Returns ``(total_days, contributing_evidence_keys)``. ``contributing``
    is every evidence key whose span was folded into the merge — a simple,
    deterministic, order-independent proxy for "necessary", not an attempt
    at a minimal covering subset.
    """
    if not spans:
        return 0, set()
    ordered = sorted(spans, key=lambda entry: (entry[0][0], entry[0][1]))
    merged: list[tuple[date, date]] = []
    contributing: set[str] = set()
    current_start, current_end = ordered[0][0]
    contributing.add(ordered[0][1])
    for (start, end), key in ordered[1:]:
        if start <= current_end + timedelta(days=1):
            if end > current_end:
                current_end = end
            contributing.add(key)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
            contributing.add(key)
    merged.append((current_start, current_end))
    total_days = sum((end - start).days for start, end in merged)
    return total_days, contributing


def evaluate_item(
    item: RequirementItemSpec,
    claims: Sequence[EvidenceClaim],
    admitted_by_triple: Mapping[tuple[str, str, int], AdmittedRecord],
    *,
    evaluation_time: datetime,
) -> tuple[str, str, tuple[EvidenceLink, ...]]:
    """Deterministic per-item evaluation (§2.8a). Pure: no repository, no
    clock, no randomness — only the passed ``evaluation_time``."""

    if item.reading_flagged:
        return STATE_NOT_ESTABLISHED, "classification_ambiguous", ()

    def _record(claim: EvidenceClaim) -> EvidenceRecord:
        triple = (claim.evidence_key, claim.evidence_class, claim.evidence_version)
        return admitted_by_triple[triple].record

    def _link(claim: EvidenceClaim) -> EvidenceLink:
        triple = (claim.evidence_key, claim.evidence_class, claim.evidence_version)
        entry = admitted_by_triple[triple]
        return EvidenceLink(
            reference=EvidenceReference(
                entry.record.evidence_key, entry.record.evidence_class, entry.record.version
            ),
            admitting_grant_key=entry.admitting_grant_key,
            relation=claim.relation,
            time_span=claim.time_span,
            credential_name=claim.credential_name,
        )

    ordered_claims = tuple(
        sorted(
            claims,
            key=lambda claim: (claim.evidence_key, claim.relation, claim.time_span or (date.min, date.min)),
        )
    )

    firm_supports = [c for c in ordered_claims if _record(c).strength == "firm" and c.relation == "supports"]
    firm_partials = [c for c in ordered_claims if _record(c).strength == "firm" and c.relation == "partial"]
    firm_contradictions = [
        c for c in ordered_claims if _record(c).strength == "firm" and c.relation == "contradicts"
    ]
    candidate_any = [c for c in ordered_claims if _record(c).strength == "candidate"]

    window: tuple[date, date] | None = None
    if item.constraints.recency_window_months is not None:
        window_start = evaluation_time.date() - timedelta(
            days=item.constraints.recency_window_months * MONTH_DAYS
        )
        window = (window_start, evaluation_time.date())

    def _effective_span(claim: EvidenceClaim) -> tuple[date, date] | None | str:
        span = claim.time_span or _record(claim).time_span
        if span is None:
            return None
        if window is None:
            return span
        start, end = span
        clipped_start = max(start, window[0])
        clipped_end = min(end, window[1])
        if clipped_start > clipped_end:
            return "out_of_window"
        return (clipped_start, clipped_end)

    def _in_window(claim: EvidenceClaim) -> bool:
        if window is None:
            return True
        span = _effective_span(claim)
        # An undated claim cannot satisfy a windowed requirement.
        return span is not None and span != "out_of_window"

    def _satisfies(
        constraints: RequirementConstraints,
        supports: Sequence[EvidenceClaim],
        partials: Sequence[EvidenceClaim],
    ) -> tuple[bool, set[str]]:
        necessary_keys: set[str] = set()

        if constraints.credential_names:
            normalized_names = {" ".join(name.split()).casefold() for name in constraints.credential_names}
            credential_ok = False
            for claim in supports:
                if not _in_window(claim):
                    continue
                if claim.credential_name is None:
                    continue
                normalized_claim_name = " ".join(claim.credential_name.split()).casefold()
                if normalized_claim_name in normalized_names:
                    credential_ok = True
                    necessary_keys.add(claim.evidence_key)
            if not credential_ok:
                return False, necessary_keys

        if constraints.minimum_duration_months is not None:
            spans: list[tuple[tuple[date, date], str]] = []
            for claim in list(supports) + list(partials):
                span = _effective_span(claim)
                if span == "out_of_window" or span is None:
                    continue
                spans.append((span, claim.evidence_key))
            total_days, contributing = _merge_and_sum(spans)
            required_days = constraints.minimum_duration_months * MONTH_DAYS
            # Defense-in-depth (Blocker 1): a threshold can never be met by
            # zero contributing evidence, even if a malformed constraint
            # somehow reached here with required_days <= 0.
            if not contributing or total_days < required_days:
                return False, necessary_keys
            necessary_keys |= contributing

        if not constraints.credential_names and constraints.minimum_duration_months is None:
            plain_ok = False
            for claim in supports:
                if not _in_window(claim):
                    continue
                plain_ok = True
                necessary_keys.add(claim.evidence_key)
                break
            if not plain_ok:
                return False, necessary_keys

        return True, necessary_keys

    base_ok, base_necessary = _satisfies(item.constraints, firm_supports, firm_partials)
    satisfied_via_alt = False
    if not base_ok:
        for alt in item.constraints.alternative_paths:
            alt_ok, alt_necessary = _satisfies(alt, firm_supports, firm_partials)
            if alt_ok:
                base_ok, base_necessary, satisfied_via_alt = True, alt_necessary, True
                break

    if base_ok:
        contributing_claims = [
            c for c in firm_supports + firm_partials if c.evidence_key in base_necessary
        ]
        if firm_contradictions:
            links = tuple(_link(c) for c in contributing_claims) + tuple(_link(c) for c in firm_contradictions)
            return STATE_NOT_ESTABLISHED, "ambiguous_evidence", links
        if satisfied_via_alt:
            reason = "alternative_path_met"
        elif len(base_necessary) >= 2:
            reason = "corroborated"
        else:
            reason = "direct_evidence"
        links = tuple(_link(c) for c in contributing_claims)
        return STATE_VERIFIED, reason, links

    if firm_contradictions:
        return STATE_APPEARS_UNMET, "affirmative_contradiction", tuple(_link(c) for c in firm_contradictions)

    # Not established (reason precedence, first match wins).
    if not ordered_claims:
        return STATE_NOT_ESTABLISHED, "no_evidence_in_scope", ()
    if not firm_supports and not firm_partials and not firm_contradictions and candidate_any:
        return STATE_NOT_ESTABLISHED, "candidate_evidence_only", tuple(_link(c) for c in candidate_any)
    relevant_firm = firm_supports + firm_partials
    all_out_of_window = bool(window) and bool(relevant_firm) and not any(_in_window(c) for c in relevant_firm)
    if all_out_of_window:
        return STATE_NOT_ESTABLISHED, "temporal_mismatch", tuple(_link(c) for c in relevant_firm)
    if firm_supports or firm_partials:
        return STATE_NOT_ESTABLISHED, "partial_evidence", tuple(_link(c) for c in relevant_firm)
    return STATE_NOT_ESTABLISHED, "ambiguous_evidence", tuple(_link(c) for c in ordered_claims)


def _derive_gate(
    spec: RequirementVersionSpec, assessments: Sequence[Assessment | None]
) -> GateResult:
    by_item = {
        item.requirement_item_key: assessment for item, assessment in zip(spec.items, assessments)
    }
    required_items = [item for item in spec.items if item.requirement_class == "required"]
    required_total = len(required_items)
    required_verified = 0
    non_verified: list[tuple[str, str, str]] = []
    for item in required_items:
        assessment = by_item.get(item.requirement_item_key)
        if assessment is None:
            # Defensive: should not occur (assess_requirements always writes
            # a row per item), but a required item with literally no
            # assessment must not silently drop out of the gate arithmetic
            # -- report it as an unavailable review so the gate stays
            # truthfully not_fully_verified with a well-formed label.
            non_verified.append((item.requirement_item_key, STATE_REVIEW_UNAVAILABLE, "assessment_error"))
            continue
        if assessment.state == STATE_VERIFIED:
            required_verified += 1
        else:
            non_verified.append((item.requirement_item_key, assessment.state, assessment.reason_code))
    gate = (
        GATE_FULLY_VERIFIED
        if required_verified == required_total and not non_verified
        else GATE_NOT_FULLY_VERIFIED
    )
    label = _gate_label(required_verified, required_total, non_verified)
    return GateResult(
        requirement_version_key=spec.requirement_version_key,
        gate=gate,
        required_total=required_total,
        required_verified=required_verified,
        non_verified_required=tuple(non_verified),
        label=label,
    )


def _gate_label(required_verified: int, required_total: int, non_verified: Sequence[tuple[str, str, str]]) -> str:
    if required_verified == required_total and not non_verified:
        return "Fully verified"
    counts: dict[str, int] = {}
    for _, state, _reason in non_verified:
        counts[state] = counts.get(state, 0) + 1
    parts = [
        f"{counts[state]} {_STATE_PHRASES[state]}"
        for state in (STATE_NOT_ESTABLISHED, STATE_APPEARS_UNMET, STATE_REVIEW_UNAVAILABLE)
        if state in counts
    ]
    detail = " · ".join(parts)
    if not detail:
        # Defensive: every non_verified entry is required to carry one of
        # the three phrase-mapped states, so this should not occur -- but a
        # dangling "· " with nothing after it must never render.
        return f"{required_verified} of {required_total} required verified"
    return f"{required_verified} of {required_total} required verified · {detail}"


_EXPLANATIONS: Mapping[tuple[str, str], str] = {
    (STATE_VERIFIED, "direct_evidence"): "Confirmed by your own evidence, linked to its source.",
    (STATE_VERIFIED, "corroborated"): "Confirmed by more than one of your evidence records.",
    (STATE_VERIFIED, "alternative_path_met"): (
        "Confirmed through an accepted alternative to the stated qualification."
    ),
    (STATE_NOT_ESTABLISHED, "no_evidence_in_scope"): (
        "None of the evidence you've authorized covers this. This does not mean you lack the experience."
    ),
    (STATE_NOT_ESTABLISHED, "ambiguous_evidence"): (
        "Your authorized evidence is unclear on this. This does not mean you lack the experience."
    ),
    (STATE_NOT_ESTABLISHED, "partial_evidence"): (
        "Your authorized evidence covers part of this, but not firmly all of it. "
        "This does not mean you lack the experience."
    ),
    (STATE_NOT_ESTABLISHED, "temporal_mismatch"): (
        "Your evidence falls outside the time window this posting asks for. "
        "This does not mean you lack the experience."
    ),
    (STATE_NOT_ESTABLISHED, "evidence_revoked"): (
        "Evidence that previously confirmed this is no longer authorized. "
        "This does not mean you lack the experience."
    ),
    (STATE_NOT_ESTABLISHED, "classification_ambiguous"): (
        "The requirement's wording is ambiguous, so it can't be firmly confirmed yet. "
        "This does not mean you lack the experience."
    ),
    (STATE_NOT_ESTABLISHED, "candidate_evidence_only"): (
        "Only unconfirmed evidence touches this; confirm it to allow verification. "
        "This does not mean you lack the experience."
    ),
    (STATE_APPEARS_UNMET, "affirmative_contradiction"): (
        "Your authorized evidence indicates this stated requirement isn't met. "
        "You can correct or add evidence."
    ),
    (STATE_REVIEW_UNAVAILABLE, "ai_unavailable"): (
        "The check itself couldn't run right now. This does not mean you lack the experience."
    ),
    (STATE_REVIEW_UNAVAILABLE, "evidence_source_unavailable"): (
        "Your evidence source couldn't be read right now. This does not mean you lack the experience."
    ),
    (STATE_REVIEW_UNAVAILABLE, "timeout"): (
        "The check ran out of time. This does not mean you lack the experience."
    ),
    (STATE_REVIEW_UNAVAILABLE, "assessment_error"): (
        "Something went wrong running this check. This does not mean you lack the experience."
    ),
}


def _member_explanation(state: str, reason_code: str) -> str:
    return _EXPLANATIONS[(state, reason_code)]


__all__ = [
    "ACTORS",
    "ASSESSMENT_STATES",
    "AdmittedRecord",
    "Assessment",
    "AssessmentPersistenceError",
    "AssessmentProposalProvider",
    "AssessmentProposalSet",
    "AssessmentProposalTimeout",
    "AssessmentProposalUnavailable",
    "AssessmentRevision",
    "AssessmentRunResult",
    "AuditSink",
    "CLAIM_RELATIONS",
    "CLASSIFICATION_BASES",
    "EvidenceClaim",
    "EvidenceGrant",
    "EvidenceLink",
    "FailingQualificationRepository",
    "FencedAssessmentPrompt",
    "FencedEvidenceRecord",
    "GATE_FULLY_VERIFIED",
    "GATE_NOT_FULLY_VERIFIED",
    "GRANT_PURPOSE",
    "GRANT_STATES",
    "GateResult",
    "IDEMPOTENCY_TTL",
    "InMemoryAuditSink",
    "InMemoryQualificationRepository",
    "MONTH_DAYS",
    "PracticalFitObservation",
    "ProposalContractError",
    "QualificationAuditEvent",
    "QualificationRepository",
    "QualificationService",
    "QualificationServiceError",
    "REASONS_BY_STATE",
    "RECOMPUTE_CAUSES",
    "REQUIREMENT_CLASSES",
    "RepositoryWriteError",
    "RequirementConstraints",
    "RequirementItemSpec",
    "RequirementVersionSpec",
    "RevocationOutcome",
    "GrantScope",
    "STATE_APPEARS_UNMET",
    "STATE_NOT_ESTABLISHED",
    "STATE_REVIEW_UNAVAILABLE",
    "STATE_VERIFIED",
    "UnavailableAssessmentProvider",
    "build_assessment_prompt",
    "evaluate_item",
]
