"""REC-05 shared discovery-index projection for My Opportunities C4.

REC-05 (accepted): member data never enters the shared discovery index.
Asserted structurally (closed field set, allowlist builder signature with
no member/owner input) and by test (canary scans).

Owns no persistence beyond the deterministic in-memory fake below; a real
provisioned index adapter is a separate, later, owner-authorized package
(§0 -- P-1 ships contracts and fakes only, no provisioning or spend
authority).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from typing import Mapping, Protocol

from .retrieval_service import DATA_CLASSES, _posting_date, _tokenize


PROJECTION_FIELDS = frozenset(
    {
        "opportunity_key",
        "data_class",
        "governing_listing_key",
        "governing_source_version_key",
        "requirement_version_key",
        "employer",
        "title",
        "locations",
        "arrangement",
        "description_terms",  # case-folded token tuple, shared content only
        "last_successfully_verified_at",  # governing head, REC-07 semantics
        "posted_at",  # deterministic read, §5.3
    }
)

FORBIDDEN_PROJECTION_TOKENS = (
    "user",
    "member",
    "grant",
    "assessment",
    "criteria",
    "draft",
    "snapshot",
    "evidence",
    "save",
    "slate",
    "import",
    "score",
)


class ProjectionContractError(ValueError):
    """A projection input violates the governing-basis-only fence."""


@dataclass(frozen=True)
class ProjectionDocument:
    opportunity_key: str
    data_class: str  # fixture | production; never mixed
    governing_listing_key: str
    governing_source_version_key: str
    requirement_version_key: str
    employer: str
    title: str
    locations: tuple[str, ...]
    arrangement: str | None
    description_terms: tuple[str, ...]
    last_successfully_verified_at: datetime | None
    posted_at: date | None

    def __post_init__(self) -> None:
        field_names = {item.name for item in fields(self)}
        if field_names != PROJECTION_FIELDS:
            raise ProjectionContractError("projection_fields_invalid")
        for name in field_names:
            lowered = name.lower()
            if any(token in lowered for token in FORBIDDEN_PROJECTION_TOKENS):
                raise ProjectionContractError("projection_field_forbidden")
        object.__setattr__(self, "locations", tuple(self.locations))
        object.__setattr__(self, "description_terms", tuple(self.description_terms))


def build_projection_document(
    opportunity: object, listing: object, version: object, requirement_version: object
) -> ProjectionDocument:
    """Pure allowlist builder (the C5 ``build_assessment_prompt`` fence
    pattern). Signature takes only C2 shared-side objects: no ``user_key``,
    repository, grant, criteria, or telemetry parameter. A projection is
    only ever built from the governing basis."""
    data_classes = {
        getattr(opportunity, "data_class", None),
        getattr(listing, "data_class", None),
        getattr(version, "data_class", None),
        getattr(requirement_version, "data_class", None),
    }
    if len(data_classes) != 1 or None in data_classes:
        raise ProjectionContractError("data_class_mismatch")
    data_class = data_classes.pop()
    if data_class not in DATA_CLASSES:
        raise ProjectionContractError("data_class_mismatch")
    if getattr(listing, "listing_key", None) != getattr(opportunity, "governing_listing_key", None):
        raise ProjectionContractError("not_governing_listing")
    if getattr(version, "version_key", None) != getattr(opportunity, "governing_source_version_key", None):
        raise ProjectionContractError("not_governing_version")
    if getattr(requirement_version, "requirement_version_key", None) != getattr(
        opportunity, "requirement_version_key", None
    ):
        raise ProjectionContractError("not_governing_requirement_version")

    return ProjectionDocument(
        opportunity_key=opportunity.opportunity_key,
        data_class=data_class,
        governing_listing_key=listing.listing_key,
        governing_source_version_key=version.version_key,
        requirement_version_key=requirement_version.requirement_version_key,
        employer=version.employer or "",
        title=version.title or "",
        locations=tuple(version.locations or ()),
        arrangement=version.arrangement,
        description_terms=_tokenize(version.description or ""),
        last_successfully_verified_at=listing.last_successfully_verified_at,
        posted_at=_posting_date(version),
    )


@dataclass(frozen=True)
class RebuildIndexResult:
    """MINOR 17: distinguishes a genuinely-ineligible opportunity (gate
    correctly evaluated and failed -- not counted at all, an ordinary
    outcome) from one whose eligibility could not even be *evaluated*
    (``canonical_gate`` itself raised -- a truncation C9 must be able to
    see, not a silent gap in the index)."""

    indexed: int
    skipped_gate_failures: int


def rebuild_index(
    index: "InMemoryDiscoveryIndex",
    canonical_repository: object,
    data_class: str,
    *,
    canonical_service: object,
    now: datetime,
) -> RebuildIndexResult:
    """Full rebuild from canonical truth (doc 02 §4 "rebuildable
    projection"): clears and re-adds one document per gate-eligible
    opportunity. Deterministic; used by tests and, later, by C9
    operations.

    ``canonical_service``/``now`` are a structural addition (report note
    d): gate-eligibility cannot be evaluated without them, and the
    blueprint's 3-argument signature omits a seam for either.
    """
    index.clear()
    count = 0
    skipped_gate_failures = 0
    for opportunity in sorted(
        canonical_repository.opportunities(data_class), key=lambda item: item.opportunity_key
    ):
        if getattr(opportunity, "tombstone_target_key", None) is not None:
            continue
        governing_listing_key = getattr(opportunity, "governing_listing_key", None)
        governing_source_version_key = getattr(opportunity, "governing_source_version_key", None)
        requirement_version_key = getattr(opportunity, "requirement_version_key", None)
        if not (governing_listing_key and governing_source_version_key and requirement_version_key):
            continue
        try:
            gate = canonical_service.canonical_gate(opportunity.opportunity_key, now=now)
        except Exception:
            # MINOR 17: no longer a silent `continue` -- counted so a
            # caller (C9) can see the rebuild was truncated rather than
            # mistaking a storage hiccup for genuine non-eligibility. One
            # opportunity's gate failure still does not abort the whole
            # rebuild; every other opportunity is still attempted.
            skipped_gate_failures += 1
            continue
        if not gate.passes:
            continue
        listing = canonical_repository.listing(governing_listing_key)
        version = canonical_repository.version(governing_source_version_key)
        requirement_version = canonical_repository.requirement_version(requirement_version_key)
        if listing is None or version is None or requirement_version is None:
            continue
        try:
            document = build_projection_document(opportunity, listing, version, requirement_version)
        except ProjectionContractError:
            continue
        index.add_document(document)
        count += 1
    return RebuildIndexResult(indexed=count, skipped_gate_failures=skipped_gate_failures)


class IndexUnavailable(RuntimeError):
    """The discovery index could not be reached; the worker falls back to
    the bounded canonical path (doc 04 §9)."""


class DiscoveryIndex(Protocol):
    def search(
        self, *, data_class: str, terms: tuple[str, ...], filters: Mapping[str, str]
    ) -> tuple["IndexCandidate", ...]: ...


@dataclass(frozen=True)
class IndexCandidate:
    document: ProjectionDocument
    retrieval_relevance: float  # internal only; NEVER serialized (doc 04 §§3-4)


class InMemoryDiscoveryIndex:
    """P-1 fake. Deterministic relevance: ``retrieval_relevance`` = float
    (number of query terms present in title/employer/description_terms/
    locations, case-folded exact token match). No randomness, no clock.
    Candidates are returned sorted (opportunity_key asc) -- the WORKER, not
    the index, owns ordering. Constructor flag ``fail_with=IndexUnavailable``
    for degraded tests; mutation hooks (``overwrite_document``) for fence
    tests.

    ``filters`` is accepted for interface compatibility with a future
    provisioned index but is not consulted by this fake (report note h):
    correctness never depends on it -- every candidate this fake returns is
    re-validated by the worker's own ``matches_criteria`` regardless of
    path, so an unfiltered-but-fenced-and-rematched candidate set is exactly
    as correct as a pre-filtered one.
    """

    def __init__(self, *, fail_with: type[BaseException] | None = None) -> None:
        self._documents: dict[str, ProjectionDocument] = {}
        self._fail_with = fail_with

    def add_document(self, document: ProjectionDocument) -> None:
        self._documents[document.opportunity_key] = document

    def overwrite_document(self, opportunity_key: str, document: ProjectionDocument) -> None:
        """Mutation hook for fence tests: forces a document into the index
        under a given key regardless of the document's own identity, so a
        test can simulate staleness/tampering."""
        self._documents[opportunity_key] = document

    def remove_document(self, opportunity_key: str) -> None:
        self._documents.pop(opportunity_key, None)

    def clear(self) -> None:
        self._documents.clear()

    def documents(self) -> tuple[ProjectionDocument, ...]:
        return tuple(self._documents.values())

    def search(
        self, *, data_class: str, terms: tuple[str, ...], filters: Mapping[str, str]
    ) -> tuple[IndexCandidate, ...]:
        del filters
        if self._fail_with is not None:
            raise self._fail_with("index_unavailable")
        term_set = frozenset(terms)
        candidates = []
        for document in self._documents.values():
            if document.data_class != data_class:
                continue
            haystack = set(_tokenize(document.title)) | set(_tokenize(document.employer))
            haystack |= set(document.description_terms)
            for location in document.locations:
                haystack |= set(_tokenize(location))
            relevance = float(len(term_set & haystack))
            candidates.append(IndexCandidate(document=document, retrieval_relevance=relevance))
        return tuple(sorted(candidates, key=lambda candidate: candidate.document.opportunity_key))


__all__ = [
    "PROJECTION_FIELDS",
    "FORBIDDEN_PROJECTION_TOKENS",
    "ProjectionContractError",
    "ProjectionDocument",
    "build_projection_document",
    "rebuild_index",
    "RebuildIndexResult",
    "IndexUnavailable",
    "DiscoveryIndex",
    "IndexCandidate",
    "InMemoryDiscoveryIndex",
]
