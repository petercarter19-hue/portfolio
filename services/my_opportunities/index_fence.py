"""Doc 04 §10 local fence for My Opportunities C4.

Before any index-derived entry is admitted, re-validate against canonical
truth. Fence failures drop the entry and emit a content-free event; they
never surface index-only data. Display facts are never taken from the
candidate document: the snapshot stores references only, and reads resolve
display fields from canonical (retrieval_service §4.4), so even an
admitted-but-tampered index field can never render.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from datetime import date, datetime

from .canonical_service import MyOpportunitiesCanonicalError
from .index_projection import PROJECTION_FIELDS, IndexCandidate, ProjectionDocument
from .retrieval_service import DATA_CLASSES


FENCE_DROP_REASONS = frozenset(
    {
        "opportunity_missing",  # canonical row gone / tombstone unresolvable
        "not_current",  # no rights-permitted current head passes the gate
        "governing_version_mismatch",  # index doc's governing version != canonical's
        "data_class_mismatch",  # fixture/production context mismatch
        "shape_invalid",  # schema/enum shape not exactly expected
    }
)


@dataclass(frozen=True)
class FenceDecision:
    admitted: bool
    reason: str | None  # in FENCE_DROP_REASONS when not admitted

    def __post_init__(self) -> None:
        if self.admitted and self.reason is not None:
            raise ValueError("fence_decision_invalid")
        if not self.admitted and self.reason not in FENCE_DROP_REASONS:
            raise ValueError("fence_decision_invalid")


def _shape_valid(document: object) -> bool:
    """Strict set-equality shape check first, mirroring
    ``evidence_port._record_from_row``: types and non-empty keys."""
    if not isinstance(document, ProjectionDocument):
        return False
    field_names = {item.name for item in fields(document)}
    if field_names != PROJECTION_FIELDS:
        return False
    for key_field in (
        "opportunity_key",
        "governing_listing_key",
        "governing_source_version_key",
        "requirement_version_key",
    ):
        value = getattr(document, key_field)
        if not isinstance(value, str) or not value:
            return False
    if document.data_class not in DATA_CLASSES:
        return False
    if not isinstance(document.employer, str) or not isinstance(document.title, str):
        return False
    if not isinstance(document.locations, tuple) or any(
        not isinstance(item, str) for item in document.locations
    ):
        return False
    if document.arrangement is not None and not isinstance(document.arrangement, str):
        return False
    if not isinstance(document.description_terms, tuple) or any(
        not isinstance(item, str) for item in document.description_terms
    ):
        return False
    if document.last_successfully_verified_at is not None and not isinstance(
        document.last_successfully_verified_at, datetime
    ):
        return False
    if document.posted_at is not None and not isinstance(document.posted_at, date):
        return False
    return True


def _relevance_valid(value: object) -> bool:
    """IMPORTANT 7: a candidate's ``retrieval_relevance`` must be a finite,
    non-negative number. ``bool`` is rejected even though it is technically
    an ``int`` subtype -- a boolean was never a relevance score."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return value >= 0


def fence_candidate(
    candidate: IndexCandidate,
    *,
    data_class: str,
    canonical_service: object,
    canonical_repository: object,
    now: datetime,
) -> FenceDecision:
    """Checks, in order (first failure wins)."""
    del canonical_repository  # canonical_service.resolve_opportunity is the sole read path (tombstone-following)
    document = candidate.document

    # 1. shape (document fields, and the candidate's own retrieval_relevance:
    #    int/float, finite, non-negative -- a NaN/inf/negative/non-numeric
    #    relevance is never trustworthy enough to admit or order by).
    if not _shape_valid(document) or not _relevance_valid(candidate.retrieval_relevance):
        return FenceDecision(False, "shape_invalid")

    # 2. data_class
    if document.data_class != data_class:
        return FenceDecision(False, "data_class_mismatch")

    # 3. opportunity resolves (tombstone-following) and its data_class matches
    try:
        opportunity = canonical_service.resolve_opportunity(document.opportunity_key)
    except MyOpportunitiesCanonicalError:
        # Expected absence (tombstone-unresolvable, truly unknown key): a
        # normal fence drop. An unrelated exception type (e.g. a storage
        # outage) is left to propagate -- the worker's fence loop converts
        # it to a truthful partial(index_failure) rather than this silently
        # becoming an ordinary "opportunity_missing" drop (BLOCKER 2).
        return FenceDecision(False, "opportunity_missing")
    if opportunity.data_class != data_class:
        return FenceDecision(False, "opportunity_missing")

    # 4. canonical gate passes
    gate = canonical_service.canonical_gate(document.opportunity_key, now=now)
    if not gate.passes:
        return FenceDecision(False, "not_current")

    # 5. canonical governing_source_version_key and requirement_version_key
    #    equal the document's -- a stale index doc never supplies the basis.
    if (
        opportunity.governing_source_version_key != document.governing_source_version_key
        or opportunity.requirement_version_key != document.requirement_version_key
    ):
        return FenceDecision(False, "governing_version_mismatch")

    return FenceDecision(True, None)


__all__ = ["FENCE_DROP_REASONS", "FenceDecision", "fence_candidate"]
