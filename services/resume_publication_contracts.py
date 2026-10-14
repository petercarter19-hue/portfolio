"""Resume publication contracts. Objects are data, never publication credentials.

Only a trusted application adapter may issue a use context after its own
authentication/authorization. The private constructor seal prevents an
accidental client-dictionary/boolean API, not malicious in-process Python.
Review never grants permission or constructs a foundation SourceVersion.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
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


CANONICAL_SOURCE_CODEC = "resume-canonical-source.v1"
REVIEW_PAYLOAD_SCHEMA = "resume-publication-review.v4"
CANONICAL_SOURCE_FIELDS = (
    "canonical_type",
    "role_title",
    "employer_name",
    "location_text",
    "summary",
    "start_date",
    "end_date",
    "date_precision",
    "employment_type",
    "current_role",
    "title",
    "institution_name",
    "degree_name",
    "field_of_study",
    "education_status",
    "grade_text",
    "credential_name",
    "issuer_name",
    "credential_identifier",
    "issue_date",
    "expiration_date",
    "name",
    "skill_summary",
    "wording",
    "metric_value",
    "metric_label",
    "accomplishment_to_achievement",
    "parent_canonical_type",
)
_BOOLEAN_SOURCE_FIELDS = frozenset({"current_role", "accomplishment_to_achievement"})


def _utf8(value: str) -> bytes:
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ContractError("invalid UTF-8") from error
    if encoded.decode("utf-8") != value:
        raise ContractError("invalid UTF-8 round trip")
    return encoded


def encode_canonical_source(fields: dict[str, object]) -> bytes:
    """Closed length-prefixed codec. No trim, normalize, or str() coercion."""
    if type(fields) is not dict:
        raise ContractError("typed codec fields required")
    unknown = set(fields) - set(CANONICAL_SOURCE_FIELDS)
    if unknown:
        raise ContractError("unknown codec field")
    parts = [_utf8(CANONICAL_SOURCE_CODEC)]
    for name in CANONICAL_SOURCE_FIELDS:
        name_bytes = _utf8(name)
        parts.append(f"{len(name_bytes):d}:".encode("ascii") + name_bytes)
        if name not in fields or fields[name] is None:
            parts.append(b"N")
            continue
        value = fields[name]
        if name in _BOOLEAN_SOURCE_FIELDS:
            if type(value) is not bool:
                raise ContractError("boolean codec field required")
            parts.append(b"B1" if value else b"B0")
            continue
        if type(value) is not str:
            raise ContractError("string codec field required")
        raw = _utf8(value)
        parts.append(b"S" + f"{len(raw):d}:".encode("ascii") + raw)
    return b"".join(parts)


def decode_canonical_source(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes:
        raise ContractError("codec bytes required")
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError("invalid UTF-8") from error

    cursor = 0

    def take_tag() -> str:
        nonlocal cursor
        if cursor >= len(payload):
            raise ContractError("truncated codec")
        tag = payload[cursor:cursor + 1]
        cursor += 1
        if tag not in (b"N", b"B", b"S"):
            raise ContractError("unsupported codec tag")
        return tag.decode("ascii")

    def take_len_prefixed() -> bytes:
        nonlocal cursor
        start = cursor
        while cursor < len(payload) and 48 <= payload[cursor] <= 57:
            cursor += 1
        if start == cursor or cursor >= len(payload) or payload[cursor:cursor + 1] != b":":
            raise ContractError("malformed codec length")
        length = int(payload[start:cursor].decode("ascii"))
        cursor += 1
        end = cursor + length
        if length < 0 or end > len(payload):
            raise ContractError("truncated codec")
        chunk = payload[cursor:end]
        cursor = end
        return chunk

    prefix = _utf8(CANONICAL_SOURCE_CODEC)
    if payload[:len(prefix)] != prefix:
        raise ContractError("unsupported codec")
    cursor = len(prefix)
    decoded: dict[str, object] = {}
    for expected in CANONICAL_SOURCE_FIELDS:
        name = take_len_prefixed().decode("utf-8")
        if name != expected:
            raise ContractError("codec field order")
        kind = take_tag()
        if kind == "N":
            decoded[name] = None
        elif kind == "B":
            if cursor >= len(payload) or payload[cursor:cursor + 1] not in (b"0", b"1"):
                raise ContractError("malformed boolean")
            decoded[name] = payload[cursor:cursor + 1] == b"1"
            cursor += 1
            if expected not in _BOOLEAN_SOURCE_FIELDS:
                raise ContractError("boolean codec field required")
        else:
            decoded[name] = take_len_prefixed().decode("utf-8")
            if expected in _BOOLEAN_SOURCE_FIELDS:
                raise ContractError("boolean codec field required")
    if cursor != len(payload):
        raise ContractError("trailing codec bytes")
    return decoded


def hash_canonical_source(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("codec bytes required")
    decode_canonical_source(payload)
    return hashlib.sha256(payload).hexdigest()


class UseAudience(str, Enum):
    GUEST = "guest"
    OWNER_PREVIEW = "owner_preview"


class UsePurpose(str, Enum):
    PUBLICATION_REVIEW = "publication_review"
    PUBLIC_DISPLAY = "public_display"
    OWNER_PREVIEW = "owner_preview"
    VISITOR_AI = "visitor_ai"
    OWNER_VISITOR_AI_PREVIEW = "owner_visitor_ai_preview"


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
            if self.purpose not in {UsePurpose.PUBLIC_DISPLAY, UsePurpose.VISITOR_AI} or self.authenticated_owner_key is not None:
                raise ContractError("guest context cannot attest owner preview")
        elif self.authenticated_owner_key != self.subject_key or self.purpose not in {
            UsePurpose.OWNER_PREVIEW, UsePurpose.PUBLICATION_REVIEW, UsePurpose.OWNER_VISITOR_AI_PREVIEW,
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
    value: str | bool | None

    def __post_init__(self):
        text(self.field)
        if type(self.value) is bool and self.field in _BOOLEAN_SOURCE_FIELDS:
            return
        if self.value is not None:
            text(self.value, empty=True)


@dataclass(frozen=True, order=True)
class EditorialDelta:
    field: str
    before: str | bool | None
    after: str | bool | None

    def __post_init__(self):
        text(self.field)
        for value in (self.before, self.after):
            if type(value) is bool and self.field in _BOOLEAN_SOURCE_FIELDS:
                continue
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


@dataclass(frozen=True, order=True)
class NeutralReviewEvidence:
    """Saved canonical review evidence. Zero AI uses are valid. Not a grant."""
    entry: EntryRef
    evidence_key: str
    evidence_version_key: str
    version: int
    content_sha256: str
    codec: str
    canonical_token: str
    policy_content_version: int
    access_revision: int
    lifecycle: str
    owner_key: str
    saved: bool
    approved: bool
    active: bool
    canonical_evidence: bool
    ai_use_count: int
    content: str
    dependency_versions: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.entry) is not EntryRef:
            raise ContractError("owner-composite entry required")
        for value in (self.evidence_key, self.evidence_version_key, self.codec, self.canonical_token, self.owner_key, self.lifecycle):
            text(value)
        if self.codec != CANONICAL_SOURCE_CODEC:
            raise ContractError("unsupported evidence codec")
        revision(self.version)
        if self.version == 0:
            raise ContractError("evidence version must be positive")
        digest(self.content_sha256)
        revision(self.policy_content_version)
        if self.policy_content_version == 0:
            raise ContractError("policy content version must be positive")
        revision(self.access_revision)
        if type(self.ai_use_count) is not int or self.ai_use_count < 0:
            raise ContractError("explicit nonnegative AI-use count required")
        for value in (self.saved, self.approved, self.active, self.canonical_evidence):
            if type(value) is not bool:
                raise ContractError("typed evidence eligibility required")
        if type(self.content) is not str:
            raise ContractError("exact saved canonical wording required")
        members(self.dependency_versions, str)
        unique(self.dependency_versions, lambda x: x)
        object.__setattr__(self, "dependency_versions", tuple(sorted(self.dependency_versions)))


@dataclass(frozen=True, order=True)
class PublicationEvidenceVersion:
    """Immutable committed source evidence produced after a write, never a review proposal."""
    owner_key: str
    entry_key: str
    evidence_key: str
    evidence_version_key: str
    version: int
    codec: str
    canonical_token: str
    policy_content_version: int
    access_revision: int
    content: bytes
    content_sha256: str
    display_eligible: bool
    visitor_ai_eligible: bool
    dependency_versions: tuple[str, ...] = ()

    def __post_init__(self):
        for value in (self.owner_key, self.entry_key, self.evidence_key, self.evidence_version_key, self.codec, self.canonical_token):
            text(value)
        if self.codec != CANONICAL_SOURCE_CODEC:
            raise ContractError("unsupported evidence codec")
        revision(self.version)
        if self.version == 0:
            raise ContractError("evidence version must be positive")
        revision(self.policy_content_version)
        if self.policy_content_version == 0:
            raise ContractError("policy content version must be positive")
        revision(self.access_revision)
        if type(self.content) is not bytes:
            raise ContractError("committed codec bytes required")
        digest(self.content_sha256)
        if hashlib.sha256(self.content).hexdigest() != self.content_sha256:
            raise ContractError("evidence digest mismatch")
        for value in (self.display_eligible, self.visitor_ai_eligible):
            if type(value) is not bool:
                raise ContractError("typed eligibility required")
        members(self.dependency_versions, str)
        unique(self.dependency_versions, lambda x: x)
        object.__setattr__(self, "dependency_versions", tuple(sorted(self.dependency_versions)))


@dataclass(frozen=True)
class ProfileIdentityReference:
    """Selected immutable Profile publication, never a second identity record."""

    owner_key: str
    profile_slug: str
    revision_key: str
    revision_number: int
    publication_digest: str
    schema_version: int = 1

    def __post_init__(self):
        for value in (self.owner_key, self.profile_slug, self.revision_key):
            text(value)
        if (len(self.owner_key) > 300 or len(self.profile_slug) > 64
                or len(self.revision_key) > 128):
            raise ContractError("invalid Profile identity reference")
        revision(self.revision_number)
        if self.revision_number < 1:
            raise ContractError("positive Profile publication revision required")
        digest(self.publication_digest)
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ContractError("unsupported Profile identity reference")

    def to_payload(self):
        return {
            "schema_version": self.schema_version,
            "owner_key": self.owner_key,
            "profile_slug": self.profile_slug,
            "revision_key": self.revision_key,
            "revision_number": self.revision_number,
            "publication_digest": self.publication_digest,
        }

    @classmethod
    def from_payload(cls, value):
        if type(value) is not dict or set(value) != {
            "schema_version", "owner_key", "profile_slug", "revision_key",
            "revision_number", "publication_digest",
        }:
            raise ContractError("closed Profile identity reference required")
        return cls(**value)


@dataclass(frozen=True)
class DraftEntryBase:
    """Canonical editor token is distinct from the policy content counter."""

    entry: EntryRef
    canonical_token: str

    def __post_init__(self):
        if type(self.entry) is not EntryRef:
            raise ContractError("typed draft entry base required")
        text(self.canonical_token)
        if len(self.canonical_token) > 128:
            raise ContractError("invalid canonical editor token")


@dataclass(frozen=True)
class CandidateInput:
    context: TrustedUseContext
    prior: VersionTuple
    selections: tuple[EntrySelection, ...]
    placements: tuple[MediaPlacement, ...]
    schema_version: int = 1
    review_evidence: tuple[NeutralReviewEvidence, ...] = ()
    profile_identity: ProfileIdentityReference | None = None
    draft_bases: tuple[DraftEntryBase, ...] = ()
    story_entry_key: str | None = None

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ContractError("unsupported schema version")
        if type(self.context) is not TrustedUseContext or type(self.prior) is not VersionTuple:
            raise ContractError("typed context and versions required")
        if self.profile_identity is not None:
            if (type(self.profile_identity) is not ProfileIdentityReference
                    or self.profile_identity.owner_key != self.context.subject_key):
                raise ContractError("same-owner Profile identity reference required")
        members(self.selections, EntrySelection)
        if self.story_entry_key is not None:
            text(self.story_entry_key)
            if self.story_entry_key not in {item.entry.entry_key for item in self.selections}:
                raise ContractError("Story must reference an entry in this candidate")
        members(self.draft_bases, DraftEntryBase)
        unique(self.draft_bases, lambda value: value.entry.identity)
        if any(base.entry not in self.prior.entries for base in self.draft_bases):
            raise ContractError("draft base must belong to this candidate")
        object.__setattr__(self, "draft_bases", tuple(sorted(self.draft_bases, key=lambda value: value.entry)))
        members(self.placements, MediaPlacement)
        members(self.review_evidence, NeutralReviewEvidence)
        unique(self.selections, lambda x: x.entry.identity)
        unique(self.placements, lambda x: x.slot)
        unique(self.review_evidence, lambda x: x.evidence_version_key)
        for placement in self.placements:
            check_placement(placement)
        object.__setattr__(self, "selections", tuple(sorted(self.selections, key=lambda x: x.entry)))
        object.__setattr__(self, "placements", tuple(sorted(self.placements, key=lambda x: x.slot)))
        object.__setattr__(self, "review_evidence", tuple(sorted(self.review_evidence)))


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
    private_assistance_excluded: bool = False

    def __post_init__(self):
        if type(self.ref) is not EntryRef:
            raise ContractError("typed entry required")
        members(self.wording, Wording)
        unique(self.wording, lambda x: x.field)
        for value in (
            self.display_allowed, self.visitor_ai_allowed, self.active,
            self.identity_resolved, self.private_assistance_excluded,
        ):
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
    owner_entries: tuple[ManifestEntry, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    state: ReadState
    reason: str
    reviewed: ReviewedCandidate | None = None
    # Named items behind an UNAVAILABLE codec refusal, so the owner can see
    # which entry blocks the whole review. Never content, only refs/reasons.
    blocked_items: tuple[tuple[str, str], ...] = ()
