"""Typed, immutable, reference-only evidence reads for My Opportunities C5.

The port owns no persistence, no provider, no network, and no grant
knowledge.  Grants are applied by ``qualification_service`` after
authorization resolves; grant objects never travel through this module.  A
port implementation returns the owner's own confirmed records, newest
first, bounded — nothing more.  It never raises for "no rows" and never
returns another member's record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Mapping, Protocol, Sequence
from uuid import UUID


CONTRACT_VERSION = "1.0"
EVIDENCE_CLASS_WORKSHOP = "workshop_knowledge"
EVIDENCE_CLASSES = frozenset({EVIDENCE_CLASS_WORKSHOP})  # closed, v1
EVIDENCE_STRENGTHS = frozenset({"firm", "candidate"})  # closed
MAX_EVIDENCE_ITEMS = 24  # the governed procedure's own window
MAX_EVIDENCE_TITLE_UNITS = 200  # mirror opportunity_slate_service
MAX_EVIDENCE_BODY_UNITS = 8_000  # mirror opportunity_slate_service
MAX_USER_KEY_UTF16_UNITS = 300
MAX_EVIDENCE_KEY_UNITS = 80

_EVIDENCE_ROW_FIELDS = frozenset(
    {
        "evidence_key",
        "evidence_version",
        "evidence_title",
        "evidence_body",
        "evidence_updated_at_utc",
    }
)


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


class EvidencePortError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require_user_key(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidencePortError("user_key_required")
    normalized = value.strip()
    if _utf16_units(normalized) > MAX_USER_KEY_UTF16_UNITS:
        raise EvidencePortError("user_key_too_long")
    return normalized


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_key: str  # opaque key (uuid hex/str) of the source record
    evidence_class: str  # in EVIDENCE_CLASSES
    version: int  # pinned confirmed version, > 0
    title: str  # bounded, <= 200 UTF-16 units
    body: str  # bounded, <= 8000 UTF-16 units
    updated_at: datetime  # tz-aware UTC
    strength: str  # "firm" | "candidate"
    time_span: tuple[date, date] | None = None
    # (start, end); None for the Workshop port (no structured dates on
    # knowledge items)

    @property
    def contract_version(self) -> str:
        return CONTRACT_VERSION


@dataclass(frozen=True)
class EvidenceReference:
    """Reference-only identity used everywhere outside prompt assembly —
    never carries title/body."""

    evidence_key: str
    evidence_class: str
    version: int


class EvidencePort(Protocol):
    evidence_class: str

    def list_records_for_owner(
        self, user_key: str, *, max_items: int = MAX_EVIDENCE_ITEMS
    ) -> tuple[EvidenceRecord, ...]: ...


def _record_from_row(row: object) -> EvidenceRecord:
    """Strict, set-equality row validation (mirror ``_require_exact_fields``).

    A missing OR extra field refuses the whole call — never a truncation or
    pass-through — because an untrustworthy row is an unavailable source,
    never a guessed record.
    """
    if not isinstance(row, Mapping) or set(row) != _EVIDENCE_ROW_FIELDS:
        raise EvidencePortError("evidence_row_invalid")

    raw_key = row["evidence_key"]
    if isinstance(raw_key, str):
        evidence_key = raw_key
    elif isinstance(raw_key, UUID):
        evidence_key = str(raw_key)
    else:
        raise EvidencePortError("evidence_row_invalid")
    if not evidence_key or _utf16_units(evidence_key) > MAX_EVIDENCE_KEY_UNITS:
        raise EvidencePortError("evidence_row_invalid")

    version = row["evidence_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise EvidencePortError("evidence_row_invalid")

    title = row["evidence_title"]
    if (
        not isinstance(title, str)
        or not title
        or _utf16_units(title) > MAX_EVIDENCE_TITLE_UNITS
    ):
        raise EvidencePortError("evidence_row_invalid")

    body = row["evidence_body"]
    if (
        not isinstance(body, str)
        or not body
        or _utf16_units(body) > MAX_EVIDENCE_BODY_UNITS
    ):
        raise EvidencePortError("evidence_row_invalid")

    updated_at = row["evidence_updated_at_utc"]
    if not isinstance(updated_at, datetime) or updated_at.tzinfo is None:
        # Naive values are refused: the service layer always passes
        # tz-aware UTC, so a naive timestamp means the source is untrusted.
        raise EvidencePortError("evidence_row_invalid")

    return EvidenceRecord(
        evidence_key=evidence_key,
        evidence_class=EVIDENCE_CLASS_WORKSHOP,
        version=version,
        title=title,
        body=body,
        updated_at=updated_at.astimezone(timezone.utc),
        strength="firm",
        time_span=None,
    )


class WorkshopEvidencePort:
    """The governed adapter over the already-allowlisted, already-applied
    ``usp_ListOpportunityEvidenceForOwner`` procedure (PS-OPPSLATE-002).

    Mirrors ``OpportunitySlateService.list_evidence_for_owner`` exactly: read
    only the member's confirmed, unarchived Workshop knowledge records
    (policy rule 7). Every record this adapter produces carries
    ``strength="firm"`` — member-confirmed, source-linked evidence is firm
    by policy rule 1 — and ``time_span=None`` (no structured dates on
    Workshop knowledge items). The adapter performs zero writes and defines
    no SQL of its own.
    """

    evidence_class = EVIDENCE_CLASS_WORKSHOP

    def __init__(self, database) -> None:
        self._database = database

    def list_records_for_owner(
        self, user_key: str, *, max_items: int = MAX_EVIDENCE_ITEMS
    ) -> tuple[EvidenceRecord, ...]:
        user_key = _require_user_key(user_key)
        bounded = max(1, min(int(max_items or MAX_EVIDENCE_ITEMS), MAX_EVIDENCE_ITEMS))
        try:
            result_sets = self._database.execute_procedure(
                "usp_ListOpportunityEvidenceForOwner",
                [("@UserKey", user_key), ("@MaxItems", bounded)],
            )
        except Exception as error:
            # The port never invents rows and never partially returns: any
            # transport/database failure is a source outage, not evidence.
            raise EvidencePortError("evidence_source_unavailable") from error
        rows = result_sets[0] if result_sets else []
        return tuple(_record_from_row(row) for row in rows)


class InMemoryEvidencePort:
    """P-1 reference port: synthetic per-owner evidence, no database."""

    def __init__(
        self,
        records_by_owner: Mapping[str, Sequence[EvidenceRecord]],
        *,
        evidence_class: str = EVIDENCE_CLASS_WORKSHOP,
        fail_with: str | None = None,
    ) -> None:
        self._records_by_owner = {
            owner: tuple(records) for owner, records in records_by_owner.items()
        }
        for records in self._records_by_owner.values():
            for record in records:
                # Important 7: an unknown strength must never silently
                # vanish from evaluate_item's firm/candidate partition --
                # refuse it here, at the source, the same way a malformed
                # database row is refused.
                if record.strength not in EVIDENCE_STRENGTHS:
                    raise EvidencePortError("evidence_row_invalid")
        self.evidence_class = evidence_class
        self._fail_with = fail_with

    def list_records_for_owner(
        self, user_key: str, *, max_items: int = MAX_EVIDENCE_ITEMS
    ) -> tuple[EvidenceRecord, ...]:
        user_key = _require_user_key(user_key)
        if self._fail_with is not None:
            raise EvidencePortError(self._fail_with)
        bounded = max(1, min(int(max_items or MAX_EVIDENCE_ITEMS), MAX_EVIDENCE_ITEMS))
        # A key miss returns (): cross-owner isolation is structural, not a
        # lookup that could leak another member's presence/absence.
        records = self._records_by_owner.get(user_key, ())
        ordered = sorted(records, key=lambda record: record.updated_at, reverse=True)
        return tuple(ordered[:bounded])


__all__ = [
    "CONTRACT_VERSION",
    "EVIDENCE_CLASS_WORKSHOP",
    "EVIDENCE_CLASSES",
    "EVIDENCE_STRENGTHS",
    "EvidencePort",
    "EvidencePortError",
    "EvidenceRecord",
    "EvidenceReference",
    "InMemoryEvidencePort",
    "MAX_EVIDENCE_ITEMS",
    "MAX_EVIDENCE_TITLE_UNITS",
    "MAX_EVIDENCE_BODY_UNITS",
    "MAX_USER_KEY_UTF16_UNITS",
    "WorkshopEvidencePort",
]
