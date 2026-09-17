"""Inactive E contract v1. Objects are data, never publication credentials.

Only a future trusted application adapter may issue a use context after its
own authentication/authorization. The private constructor seal prevents an
accidental client-dictionary/boolean API, not malicious in-process Python.
No adapter, persistence, route or provider is installed by this module.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Protocol

from services.ai_foundation.contracts import SourceVersion
from services.resume_media_repository import (
    CatalogAssetRecord, CropRect, MediaPlacement, PLACEMENT_SLOTS, SOURCE_KINDS,
)


class ContractError(ValueError):
    """Malformed or unsupported component input; never recover with defaults."""


def text(value: object, *, empty: bool = False) -> None:
    if type(value) is not str or (not empty and not value.strip()):
        raise ContractError("required text")


def revision(value: object) -> None:
    if type(value) is not int or value < 0:
        raise ContractError("explicit nonnegative revision required")


def digest(value: object) -> None:
    if type(value) is not str or len(value) != 64 or any(
        ch not in "0123456789abcdef" for ch in value
    ):
        raise ContractError("canonical SHA-256 required")


def members(values: object, cls: type) -> None:
    if type(values) is not tuple or any(type(item) is not cls for item in values):
        raise ContractError("immutable typed tuple required")


def unique(values: tuple, key) -> None:
    keys = [key(value) for value in values]
    if len(keys) != len(set(keys)):
        raise ContractError("duplicate reference or field")


class UseAudience(str, Enum):
    GUEST = "guest"
    OWNER_PREVIEW = "owner_preview"


class UsePurpose(str, Enum):
    PUBLICATION_REVIEW = "publication_review"
    PUBLIC_DISPLAY = "public_display"
    OWNER_PREVIEW = "owner_preview"


_CONTEXT_SEAL = object()


@dataclass(frozen=True)
class TrustedUseContext:
    subject_key: str
    resume_key: str
    audience: UseAudience
    purpose: UsePurpose
    authenticated_owner_key: str | None
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self):
        if self._seal is not _CONTEXT_SEAL:
            raise ContractError("context requires trusted server construction")
        text(self.subject_key)
        text(self.resume_key)
        if type(self.audience) is not UseAudience or type(self.purpose) is not UsePurpose:
            raise ContractError("closed audience and purpose required")
        if self.audience is UseAudience.GUEST:
            if self.purpose is not UsePurpose.PUBLIC_DISPLAY or self.authenticated_owner_key is not None:
                raise ContractError("guest context cannot attest owner preview")
        elif self.authenticated_owner_key != self.subject_key or self.purpose not in {
            UsePurpose.OWNER_PREVIEW, UsePurpose.PUBLICATION_REVIEW,
        }:
            raise ContractError("authenticated owner and owner purpose required")


def _context_from_authorized_server(*, subject_key: str, resume_key: str,
                                    audience: UseAudience, purpose: UsePurpose,
                                    authenticated_owner_key: str | None) -> TrustedUseContext:
    """Trusted-code seam, NOT authentication. No current application calls it.

    A later adapter must derive all arguments from authorized server state,
    never unpack request JSON here. Tests supply synthetic identities only.
    """
    return TrustedUseContext(subject_key, resume_key, audience, purpose,
                             authenticated_owner_key, _CONTEXT_SEAL)


@dataclass(frozen=True, order=True)
class EntryRef:
    subject_key: str
    entry_key: str
    content_revision: str
    access_revision: int

    def __post_init__(self):
        for value in (self.subject_key, self.entry_key, self.content_revision):
            text(value)
        revision(self.access_revision)

    @property
    def identity(self):
        return self.subject_key, self.entry_key


@dataclass(frozen=True, order=True)
class SourceRef:
    entry: EntryRef
    source_key: str
    source_version_key: str
    version: int
    content_sha256: str

    def __post_init__(self):
        if type(self.entry) is not EntryRef:
            raise ContractError("owner-composite entry required")
        text(self.source_key)
        text(self.source_version_key)
        revision(self.version)
        if self.version == 0:
            raise ContractError("source version must be positive")
        digest(self.content_sha256)


@dataclass(frozen=True, order=True)
class MediaVersion:
    subject_key: str
    slot: str
    placement_version: int
    source_kind: str
    source_key: str
    source_revision: str
    asset_version: int
    catalog_revision: str | None
    content_sha256: str
    readiness_sha256: str

    def __post_init__(self):
        for value in (self.subject_key, self.source_key, self.source_revision):
            text(value)
        if self.slot not in PLACEMENT_SLOTS or self.source_kind not in SOURCE_KINDS:
            raise ContractError("unsupported media reference")
        revision(self.placement_version)
        if self.placement_version < 1:
            raise ContractError("placement version must be positive")
        revision(self.asset_version)
        if self.source_kind == "generated_illustration":
            text(self.catalog_revision)
        elif self.catalog_revision is not None:
            raise ContractError("owner photo has no catalog revision")
        digest(self.content_sha256)
        digest(self.readiness_sha256)


@dataclass(frozen=True)
class VersionTuple:
    subject_key: str
    resume_key: str
    draft_revision: int | None
    publication_revision: int
    sharing_epoch: int
    entries: tuple[EntryRef, ...]
    sources: tuple[SourceRef, ...]
    media: tuple[MediaVersion, ...]
    schema_version: int = 1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ContractError("unsupported schema version")
        text(self.subject_key)
        text(self.resume_key)
        if self.draft_revision is not None:
            revision(self.draft_revision)
        revision(self.publication_revision)
        revision(self.sharing_epoch)
        members(self.entries, EntryRef)
        members(self.sources, SourceRef)
        members(self.media, MediaVersion)
        unique(self.entries, lambda x: x.identity)
        unique(self.sources, lambda x: x.source_version_key)
        unique(self.sources, lambda x: x.source_key)
        unique(self.media, lambda x: x.slot)
        if any(x.subject_key != self.subject_key for x in self.entries + self.media):
            raise ContractError("foreign subject")
        if any(x.entry not in self.entries for x in self.sources):
            raise ContractError("source entry missing from version tuple")
        for name in ("entries", "sources", "media"):
            object.__setattr__(self, name, tuple(sorted(getattr(self, name))))


@dataclass(frozen=True, order=True)
class Wording:
    field: str
    value: str | None

    def __post_init__(self):
        text(self.field)
        if self.value is not None:
            text(self.value, empty=True)


@dataclass(frozen=True, order=True)
class EditorialDelta:
    field: str
    before: str | None
    after: str | None

    def __post_init__(self):
        text(self.field)
        for value in (self.before, self.after):
            if value is not None:
                text(value, empty=True)
        if self.before == self.after:
            raise ContractError("unchanged wording is not an editorial delta")


@dataclass(frozen=True)
class EntrySelection:
    entry: EntryRef
    display: bool
    visitor_ai: bool
    expand_display: bool
    expand_visitor_ai: bool
    deltas: tuple[EditorialDelta, ...] = ()

    def __post_init__(self):
        if type(self.entry) is not EntryRef:
            raise ContractError("entry reference required")
        for value in (self.display, self.visitor_ai, self.expand_display, self.expand_visitor_ai):
            if type(value) is not bool:
                raise ContractError("explicit permission boolean required")
        members(self.deltas, EditorialDelta)
        unique(self.deltas, lambda x: x.field)
        object.__setattr__(self, "deltas", tuple(sorted(self.deltas)))


def check_placement(item: MediaPlacement) -> None:
    if type(item) is not MediaPlacement or type(item.crop) is not CropRect:
        raise ContractError("immutable media placement required")
    if item.slot not in PLACEMENT_SLOTS or item.source_kind not in SOURCE_KINDS:
        raise ContractError("unsupported placement")
    text(item.asset_id)
    revision(item.asset_version)
    revision(item.presentation_version)
    if item.presentation_version < 1:
        raise ContractError("presentation version must be positive")
    digest(item.asset_digest)
    for value in (item.alt_text, item.provenance_label):
        text(value, empty=True)
    if item.caption is not None:
        text(item.caption, empty=True)
    if type(item.decorative) is not bool:
        raise ContractError("decorative must be boolean")
    for value in (item.crop.x, item.crop.y, item.crop.width, item.crop.height):
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ContractError("finite crop coordinates required")


@dataclass(frozen=True)
class CandidateInput:
    context: TrustedUseContext
    prior: VersionTuple
    selections: tuple[EntrySelection, ...]
    placements: tuple[MediaPlacement, ...]
    schema_version: int = 1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ContractError("unsupported schema version")
        if type(self.context) is not TrustedUseContext or type(self.prior) is not VersionTuple:
            raise ContractError("typed context and versions required")
        members(self.selections, EntrySelection)
        members(self.placements, MediaPlacement)
        unique(self.selections, lambda x: x.entry.identity)
        unique(self.placements, lambda x: x.slot)
        for placement in self.placements:
            check_placement(placement)
        object.__setattr__(self, "selections", tuple(sorted(self.selections, key=lambda x: x.entry)))
        object.__setattr__(self, "placements", tuple(sorted(self.placements, key=lambda x: x.slot)))


class ReadState(str, Enum):
    CURRENT = "current"
    DENIED = "denied"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class EntryState:
    ref: EntryRef
    wording: tuple[Wording, ...]
    display_allowed: bool
    visitor_ai_allowed: bool
    active: bool
    identity_resolved: bool

    def __post_init__(self):
        if type(self.ref) is not EntryRef:
            raise ContractError("typed entry required")
        members(self.wording, Wording)
        unique(self.wording, lambda x: x.field)
        for value in (self.display_allowed, self.visitor_ai_allowed, self.active, self.identity_resolved):
            if type(value) is not bool:
                raise ContractError("typed policy required")
        object.__setattr__(self, "wording", tuple(sorted(self.wording)))


@dataclass(frozen=True)
class SourceState:
    ref: SourceRef
    source: SourceVersion
    saved: bool
    approved: bool
    active: bool
    canonical_evidence: bool

    def __post_init__(self):
        if type(self.ref) is not SourceRef or type(self.source) is not SourceVersion:
            raise ContractError("typed source required")
        for value in (self.saved, self.approved, self.active, self.canonical_evidence):
            if type(value) is not bool:
                raise ContractError("typed source eligibility required")


@dataclass(frozen=True)
class PolicySnapshot:
    state: ReadState
    versions: VersionTuple | None = None
    sharing_enabled: bool | None = None
    entries: tuple[EntryState, ...] = ()
    sources: tuple[SourceState, ...] = ()


@dataclass(frozen=True)
class MediaState:
    ref: MediaVersion
    width: int
    height: int
    ready: bool
    active: bool
    # Authoritative catalog evidence, never a client-supplied provenance label.
    # Owner photos use the existing fixed member-photo provenance instead.
    catalog: CatalogAssetRecord | None = None


@dataclass(frozen=True)
class MediaSnapshot:
    state: ReadState
    versions: VersionTuple | None = None
    media: tuple[MediaState, ...] = ()


class PolicyReadPort(Protocol):
    def read_current(self, context: TrustedUseContext,
                     refs: tuple[EntryRef, ...]) -> PolicySnapshot: ...


class MediaReadPort(Protocol):
    def read_current(self, context: TrustedUseContext,
                     placements: tuple[MediaPlacement, ...]) -> MediaSnapshot: ...


@dataclass(frozen=True)
class ManifestEntry:
    ref: EntryRef
    wording: tuple[Wording, ...]
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class DisplayManifest:
    entries: tuple[ManifestEntry, ...]
    placements: tuple[MediaPlacement, ...]


@dataclass(frozen=True)
class VisitorAIManifest:
    entries: tuple[ManifestEntry, ...]


@dataclass(frozen=True)
class ReviewedCandidate:
    """Validation output only; never a publish receipt or guest-usable token."""
    candidate: CandidateInput
    versions: VersionTuple
    display: DisplayManifest
    visitor_ai: VisitorAIManifest
    digest: str
    validation: ReadState = ReadState.CURRENT
    schema_version: int = 1


@dataclass(frozen=True)
class ValidationResult:
    state: ReadState
    reason: str
    reviewed: ReviewedCandidate | None = None
