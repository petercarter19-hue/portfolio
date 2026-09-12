"""Deterministic repository seam for private Resume media placement.

The Resume media backend is intentionally dark. This module declares the
storage-independent contracts the Resume media service depends on and ships one
deterministic in-memory implementation that is explicitly synthetic and
test-only. Nothing here registers a Flask route, talks to SQL, calls Azure Blob
Storage, reads live member data, or exposes a publishable media URL.

Vocabulary reused from the existing Photo Capture contracts
(``services/photo_capture_service.py`` and
``services/capture_media_storage_service.py``): owner-scoped source lookups,
opaque server-generated derivative references, row-version style optimistic
concurrency tokens, and the ``uploading -> scanning -> processing -> ready``
readiness ladder with terminal ``rejected``/``quarantined`` outcomes. This
module deliberately does not import those modules: the Resume adapter depends
on their shape by injection so tests never need live storage, SQL or identity.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import threading
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable


# --- placement and source vocabulary --------------------------------------

SLOT_STORY_BANNER = "story_banner"
SLOT_EXPERIENCE_SUPPORT = "experience_support"
PLACEMENT_SLOTS = (SLOT_STORY_BANNER, SLOT_EXPERIENCE_SUPPORT)

# Portrait is distinct identity presentation, never a decorative placement slot.
IDENTITY_PRESENTATION_PORTRAIT = "portrait"

SOURCE_KIND_OWNER_PHOTO = "owner_photo"
SOURCE_KIND_GENERATED_ILLUSTRATION = "generated_illustration"
SOURCE_KINDS = (SOURCE_KIND_OWNER_PHOTO, SOURCE_KIND_GENERATED_ILLUSTRATION)

LIFECYCLE_ACTIVE = "active"
LIFECYCLE_RESTRICTED = "restricted"
LIFECYCLE_WITHDRAWN = "withdrawn"
LIFECYCLE_DELETED = "deleted"
LIFECYCLE_STATES = (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_RESTRICTED,
    LIFECYCLE_WITHDRAWN,
    LIFECYCLE_DELETED,
)

READINESS_UPLOADING = "uploading"
READINESS_SCANNING = "scanning"
READINESS_PROCESSING = "processing"
READINESS_READY = "ready"
READINESS_FAILED = "failed"
READINESS_REJECTED = "rejected"
READINESS_QUARANTINED = "quarantined"
READINESS_STATES = (
    READINESS_UPLOADING,
    READINESS_SCANNING,
    READINESS_PROCESSING,
    READINESS_READY,
    READINESS_FAILED,
    READINESS_REJECTED,
    READINESS_QUARANTINED,
)
# Rejected and quarantined sources are terminal: they can never become ready.
TERMINAL_READINESS_STATES = (READINESS_REJECTED, READINESS_QUARANTINED)

ACCESSOR_PHOTO_READINESS = "photo_readiness"
ACCESSOR_STORAGE = "storage"

ORIENTATION_LANDSCAPE = "landscape"
ORIENTATION_PORTRAIT = "portrait"
ORIENTATION_SQUARE = "square"

# Closed command vocabulary for idempotent receipts. No other command type is
# accepted, so a caller cannot smuggle an unmodeled mutation through a receipt.
COMMAND_ADD_MEDIA = "add_media"
COMMAND_KEEP_WORDS_ONLY = "keep_words_only"
COMMAND_PUBLISH = "publish"
CLOSED_COMMAND_TYPES = (
    COMMAND_ADD_MEDIA,
    COMMAND_KEEP_WORDS_ONLY,
    COMMAND_PUBLISH,
)

# Catalog page bounds are service limits, not a production item count.
CATALOG_PAGE_SIZE_LIMIT = 24
CATALOG_PAGE_SIZE_DEFAULT = 12

CURSOR_VERSION = 1
CURSOR_CHECKSUM_CHARS = 16
CURSOR_TOKEN_MAX_LENGTH = 512


class ResumeMediaRepositoryError(RuntimeError):
    """Stable, content-free repository outcome code."""

    def __init__(self, code: str):
        self.code = str(code)
        super().__init__(self.code)


def _lifecycle_conflict_code(lifecycle: str) -> str:
    return {
        LIFECYCLE_DELETED: "source-deleted",
        LIFECYCLE_WITHDRAWN: "source-withdrawn",
        LIFECYCLE_RESTRICTED: "source-restricted",
    }.get(str(lifecycle), "source-unavailable")


def orientation_for(width: int, height: int) -> str:
    """Orientation label for already orientation-normalized dimensions."""

    if width > height:
        return ORIENTATION_LANDSCAPE
    if height > width:
        return ORIENTATION_PORTRAIT
    return ORIENTATION_SQUARE


def canonical_json(value: Any) -> str:
    """Deterministic JSON used for digests, cursors and rollback snapshots."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def sha256_hex(payload: bytes | str) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_search_text(value: Any) -> str:
    """NFKC + casefold + whitespace-collapsed search normalization."""

    if value is None:
        return ""
    if not isinstance(value, str):
        raise ResumeMediaRepositoryError("invalid-query")
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def normalize_catalog_query(query: Any) -> str:
    return normalize_search_text(query)


def catalog_query_fingerprint(
    *, query: Any = None, category: Any = None, tags: Iterable[Any] = ()
) -> str:
    """Semantic fingerprint a pagination cursor is bound to."""

    if isinstance(tags, (str, bytes)) or not isinstance(tags, Iterable):
        raise ResumeMediaRepositoryError("invalid-query")
    normalized_tags = sorted(
        {normalize_search_text(tag) for tag in tags if normalize_search_text(tag)}
    )
    payload = {
        "query": normalize_catalog_query(query),
        "category": normalize_search_text(category),
        "tags": normalized_tags,
    }
    return sha256_hex(canonical_json(payload))


def _cursor_fence(fingerprint: str, generation: int, last_key: Any) -> str:
    return sha256_hex(
        canonical_json(
            {"v": CURSOR_VERSION, "f": str(fingerprint), "g": int(generation),
             "k": last_key}
        )
    )[:CURSOR_CHECKSUM_CHARS]


def encode_catalog_cursor(
    *, fingerprint: str, generation: int, last_key: Sequence[Any] | None
) -> str:
    """Encode one stable, opaque, tamper-evident keyset pagination cursor.

    The cursor carries the normalized query fingerprint, the catalog generation
    snapshot fence, and the exact last sort key. It never carries a mutable
    offset, so an insertion or withdrawal cannot silently duplicate or skip an
    item: the generation fence refuses the page instead.
    """

    generation = int(generation)
    if generation < 0:
        raise ResumeMediaRepositoryError("invalid-cursor")
    key: list[Any] | None = None
    if last_key is not None:
        key = [str(last_key[0]), str(last_key[1]), int(last_key[2])]
    payload = {
        "v": CURSOR_VERSION,
        "g": generation,
        "f": str(fingerprint),
        "k": key,
        "c": _cursor_fence(str(fingerprint), generation, key),
    }
    raw = canonical_json(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_catalog_cursor(
    token: Any, *, fingerprint: str, generation: int
) -> tuple[str, str, int] | None:
    """Decode a keyset cursor, refusing tampering, query drift and stale pages."""

    if not isinstance(token, str) or not token:
        raise ResumeMediaRepositoryError("invalid-cursor")
    if len(token) > CURSOR_TOKEN_MAX_LENGTH:
        raise ResumeMediaRepositoryError("invalid-cursor")
    padded = token + "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError, UnicodeEncodeError) as error:
        raise ResumeMediaRepositoryError("invalid-cursor") from error
    if not isinstance(payload, dict) or payload.get("v") != CURSOR_VERSION:
        raise ResumeMediaRepositoryError("invalid-cursor")
    cursor_generation = payload.get("g")
    cursor_fingerprint = payload.get("f")
    key = payload.get("k")
    checksum = payload.get("c")
    if (
        isinstance(cursor_generation, bool)
        or not isinstance(cursor_generation, int)
        or cursor_generation < 0
    ):
        raise ResumeMediaRepositoryError("invalid-cursor")
    if not isinstance(cursor_fingerprint, str) or len(cursor_fingerprint) != 64:
        raise ResumeMediaRepositoryError("invalid-cursor")
    if key is not None:
        if (
            not isinstance(key, list)
            or len(key) != 3
            or not isinstance(key[0], str)
            or not isinstance(key[1], str)
            or isinstance(key[2], bool)
            or not isinstance(key[2], int)
        ):
            raise ResumeMediaRepositoryError("invalid-cursor")
    expected = _cursor_fence(cursor_fingerprint, cursor_generation, key)
    if not isinstance(checksum, str) or checksum != expected:
        raise ResumeMediaRepositoryError("invalid-cursor")
    if cursor_fingerprint != str(fingerprint):
        raise ResumeMediaRepositoryError("cursor-mismatch")
    if cursor_generation != int(generation):
        raise ResumeMediaRepositoryError("catalog-changed")
    if key is None:
        return None
    return (key[0], key[1], key[2])


# --- placement semantics and metadata safety -------------------------------

CROP_KEYS = ("x", "y", "width", "height")
CROP_EPSILON = 1e-9
CROP_PRECISION = 6

MAX_ALT_TEXT_LENGTH = 300
MAX_CAPTION_LENGTH = 500
MAX_PROVENANCE_LABEL_LENGTH = 120

PROVENANCE_LABEL_MEMBER_PHOTO = "Member photo"
PROVENANCE_LABEL_GENERATED = "Generated illustration"

# Explicit allowlists for public catalog metadata. Anything else, including
# storage keys, provider locators, prompts, and internal notes, is dropped.
ALLOWED_PROVENANCE_KEYS = ("model", "model_version", "generator", "created_utc")
ALLOWED_RIGHTS_KEYS = ("rights_id", "approval_state")
SCALAR_METADATA_TYPES = (str, int, float, bool)


def freeze_metadata(value: Any) -> Any:
    """Deep-freeze nested metadata into immutable tuples of scalars."""

    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (str(key), freeze_metadata(item)) for key, item in value.items()
            )
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(freeze_metadata(item) for item in value)
    if isinstance(value, SCALAR_METADATA_TYPES):
        return value
    return str(value)


def metadata_pairs(value: Any) -> dict[str, Any]:
    """Shallow dict view over a frozen metadata pair tuple."""

    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (tuple, list)):
        return {str(key): item for key, item in value}
    return {}


def _allowlisted_view(value: Any, allowed_keys: Sequence[str]) -> dict[str, Any]:
    """Return only allowlisted scalar metadata with no nested structures."""

    pairs = metadata_pairs(value)
    view: dict[str, Any] = {}
    for key in allowed_keys:
        item = pairs.get(key)
        if isinstance(item, bool) or isinstance(item, SCALAR_METADATA_TYPES):
            if isinstance(item, str) and len(item) > 200:
                item = item[:200]
            view[key] = item
    return view


def catalog_provenance_view(record: "CatalogAssetRecord") -> dict[str, Any]:
    return _allowlisted_view(record.provenance, ALLOWED_PROVENANCE_KEYS)


def catalog_rights_view(record: "CatalogAssetRecord") -> dict[str, Any]:
    return _allowlisted_view(record.rights, ALLOWED_RIGHTS_KEYS)


def provenance_label_for(
    *, source_kind: str, record: "CatalogAssetRecord | None" = None
) -> str:
    """Server-derived, safe provenance label for one placement source.

    The label is never a client value and never contains a provider locator,
    storage key or prompt: it is either the fixed member-photo label or the
    fixed generated-illustration label plus an allowlisted model name.
    """

    if source_kind == SOURCE_KIND_OWNER_PHOTO:
        return PROVENANCE_LABEL_MEMBER_PHOTO
    if source_kind != SOURCE_KIND_GENERATED_ILLUSTRATION:
        raise ResumeMediaRepositoryError("invalid-source")
    model: Any = None
    if record is not None:
        view = catalog_provenance_view(record)
        model = view.get("model") or view.get("model_version")
    if isinstance(model, str) and model.strip():
        return f"{PROVENANCE_LABEL_GENERATED} ({model.strip()[:60]})"
    return PROVENANCE_LABEL_GENERATED


def _bounded_text(value: Any, *, code: str, max_length: int, allow_empty: bool) -> str:
    if value is None:
        if allow_empty:
            return ""
        raise ResumeMediaRepositoryError(code)
    if not isinstance(value, str):
        raise ResumeMediaRepositoryError(code)
    text = value.strip()
    if not allow_empty and not text:
        raise ResumeMediaRepositoryError(code)
    if len(text) > max_length:
        raise ResumeMediaRepositoryError(code)
    if any(ord(character) < 32 and character not in "\t" for character in text):
        raise ResumeMediaRepositoryError(code)
    return text


def normalize_alt_text(value: Any) -> str:
    return _bounded_text(
        value, code="invalid-alt-text", max_length=MAX_ALT_TEXT_LENGTH,
        allow_empty=True,
    )


def normalize_caption(value: Any) -> str | None:
    if value is None:
        return None
    text = _bounded_text(
        value, code="invalid-caption", max_length=MAX_CAPTION_LENGTH,
        allow_empty=False,
    )
    return text


def normalize_decorative(value: Any) -> bool:
    """Decorative status is explicit; the source kind never sets it."""

    if isinstance(value, bool):
        return value
    raise ResumeMediaRepositoryError("invalid-decorative")


def assert_no_catalog_claim(
    *, alt_text: str, caption: str | None, record: "CatalogAssetRecord"
) -> None:
    """Refuse catalog labels/tags promoted into member-facing text."""

    claims = {
        normalize_search_text(record.label),
        *(normalize_search_text(tag) for tag in record.tags),
    }
    claims.discard("")
    for candidate in (alt_text, caption):
        if candidate and normalize_search_text(candidate) in claims:
            raise ResumeMediaRepositoryError("catalog-claim-not-allowed")


def crop_numbers(crop: Any) -> dict[str, float]:
    """Finite-number check for one crop payload."""

    if not isinstance(crop, Mapping):
        raise ResumeMediaRepositoryError("invalid-crop")
    if set(crop) != set(CROP_KEYS):
        raise ResumeMediaRepositoryError("invalid-crop")
    numbers: dict[str, float] = {}
    for key in CROP_KEYS:
        value = crop[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ResumeMediaRepositoryError("invalid-crop")
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            raise ResumeMediaRepositoryError("crop-not-finite")
        numbers[key] = number
    return numbers


def validate_crop_geometry(
    crop: Any, *, slot: str, width: int, height: int
) -> CropRect:
    """Bounds, positivity, area and slot-aspect contract for one crop."""

    numbers = crop_numbers(crop)
    if numbers["width"] <= 0 or numbers["height"] <= 0:
        raise ResumeMediaRepositoryError("invalid-crop")
    if numbers["x"] < -CROP_EPSILON or numbers["y"] < -CROP_EPSILON:
        raise ResumeMediaRepositoryError("crop-out-of-bounds")
    if numbers["x"] + numbers["width"] > 1.0 + CROP_EPSILON:
        raise ResumeMediaRepositoryError("crop-out-of-bounds")
    if numbers["y"] + numbers["height"] > 1.0 + CROP_EPSILON:
        raise ResumeMediaRepositoryError("crop-out-of-bounds")
    spec = SLOT_SPECS.get(slot)
    if spec is None:
        raise ResumeMediaRepositoryError("invalid-slot")
    if numbers["width"] * numbers["height"] < spec.min_area:
        raise ResumeMediaRepositoryError("invalid-crop")
    if width <= 0 or height <= 0:
        raise ResumeMediaRepositoryError("invalid-source")
    crop_aspect = (numbers["width"] * width) / (numbers["height"] * height)
    lower = spec.aspect * (1.0 - spec.aspect_tolerance)
    upper = spec.aspect * (1.0 + spec.aspect_tolerance)
    if not lower <= crop_aspect <= upper:
        raise ResumeMediaRepositoryError("crop-slot-mismatch")
    return CropRect(
        x=round(numbers["x"], CROP_PRECISION),
        y=round(numbers["y"], CROP_PRECISION),
        width=round(numbers["width"], CROP_PRECISION),
        height=round(numbers["height"], CROP_PRECISION),
    )


# --- persisted records (immutable snapshots) -------------------------------


@dataclass(frozen=True)
class SlotSpec:
    """Bounded presentation contract for one decorative placement slot."""

    slot: str
    aspect: float
    aspect_tolerance: float
    min_area: float


# The crop selects the region of the source that is presented in the slot. It
# must already carry the slot's presentation shape so preview and published
# derivative share one calculation; these are bounded contract constants, not
# approved production artwork dimensions.
SLOT_SPECS: Mapping[str, SlotSpec] = {
    SLOT_STORY_BANNER: SlotSpec(
        slot=SLOT_STORY_BANNER, aspect=3.0, aspect_tolerance=0.25, min_area=0.02
    ),
    SLOT_EXPERIENCE_SUPPORT: SlotSpec(
        slot=SLOT_EXPERIENCE_SUPPORT,
        aspect=1.5,
        aspect_tolerance=0.25,
        min_area=0.01,
    ),
}


@dataclass(frozen=True)
class CropRect:
    """Normalized (0..1) crop rectangle over orientation-normalized pixels."""

    x: float
    y: float
    width: float
    height: float

    def as_dict(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class MediaPlacement:
    """One slot -> source reference with its own independently persisted crop.

    Placement semantics are typed and immutable: an explicit decorative flag,
    semantic alt text, a server-derived safe provenance label, a separately
    governed member caption, and a server-derived presentation version. The
    decorative flag is never derived from the source kind alone.
    """

    slot: str
    source_kind: str
    asset_id: str
    asset_version: int
    asset_digest: str
    crop: CropRect
    presentation_version: int = 1
    alt_text: str = ""
    decorative: bool = False
    provenance_label: str = ""
    caption: str | None = None

    def presentation_fields(self) -> tuple[Any, ...]:
        """Fields that decide whether the presentation version must advance."""

        return (
            self.source_kind,
            self.asset_id,
            self.asset_version,
            self.asset_digest,
            self.crop.as_dict(),
            self.alt_text,
            self.decorative,
            self.provenance_label,
            self.caption,
        )


@dataclass(frozen=True)
class DraftMediaRecord:
    """Immutable snapshot of the owner's private Resume media draft."""

    owner_id: str
    version: int
    placements: tuple[MediaPlacement, ...] = ()
    updated_sequence: int = 0

    def placement_for(self, slot: str) -> MediaPlacement | None:
        for placement in self.placements:
            if placement.slot == slot:
                return placement
        return None


@dataclass(frozen=True)
class PublicationRecord:
    """Immutable published Resume media revision."""

    owner_id: str
    version: int
    placements: tuple[MediaPlacement, ...] = ()
    digest: str = ""
    published_sequence: int = 0

    @property
    def published(self) -> bool:
        return self.version > 0

    def placement_for(self, slot: str) -> MediaPlacement | None:
        for placement in self.placements:
            if placement.slot == slot:
                return placement
        return None


@dataclass(frozen=True)
class RequestReceipt:
    """Idempotency receipt for one closed command from one owner."""

    owner_id: str
    command_type: str
    request_uuid: str
    semantic_digest: str
    outcome_json: str
    recorded_sequence: int = 0

    @property
    def outcome(self) -> dict[str, Any]:
        return json.loads(self.outcome_json)

    @staticmethod
    def create(
        *,
        owner_id: str,
        command_type: str,
        request_uuid: str,
        semantic_digest: str,
        outcome: Mapping[str, Any],
        recorded_sequence: int = 0,
    ) -> "RequestReceipt":
        if command_type not in CLOSED_COMMAND_TYPES:
            raise ResumeMediaRepositoryError("invalid-command")
        return RequestReceipt(
            owner_id=str(owner_id),
            command_type=str(command_type),
            request_uuid=str(request_uuid),
            semantic_digest=str(semantic_digest),
            outcome_json=canonical_json(dict(outcome)),
            recorded_sequence=int(recorded_sequence),
        )


@dataclass(frozen=True)
class OwnerPhotoRecord:
    """Owner-scoped private photo source mirrored from Photo Capture."""

    owner_id: str
    source_id: str
    state: str
    version_token: str
    digest: str
    width: int
    height: int
    content_type: str
    byte_length: int
    derivative_ref: str | None = None
    lifecycle: str = LIFECYCLE_ACTIVE
    version: int = 0
    reason_code: str | None = None

    @property
    def orientation(self) -> str:
        return orientation_for(self.width, self.height)


@dataclass(frozen=True)
class CatalogDerivative:
    """Private derivative reference kept behind the repository boundary."""

    slot: str
    ref: str
    digest: str
    content_type: str
    byte_length: int


@dataclass(frozen=True)
class CatalogAssetRecord:
    """One immutable curated generated-illustration catalog revision."""

    asset_id: str
    version: int
    digest: str
    label: str
    category: str
    tags: tuple[str, ...]
    width: int
    height: int
    origin: str = SOURCE_KIND_GENERATED_ILLUSTRATION
    provenance: Any = field(default_factory=tuple)
    rights: Any = field(default_factory=tuple)
    derivatives: tuple[CatalogDerivative, ...] = ()
    lifecycle: str = LIFECYCLE_ACTIVE

    @property
    def orientation(self) -> str:
        return orientation_for(self.width, self.height)

    def derivative_for(self, slot: str) -> CatalogDerivative | None:
        for derivative in self.derivatives:
            if derivative.slot == slot:
                return derivative
        return None


@dataclass(frozen=True)
class MediaAuthorization:
    """Authorized (but not yet read) media access snapshot."""

    slot: str
    accessor: str
    asset_version: int
    asset_digest: str
    expected_digest: str
    byte_length: int
    content_type: str
    ref: str | None = None
    source_id: str | None = None
    source_version_token: str | None = None
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class CatalogPage:
    items: tuple[CatalogAssetRecord, ...]
    next_cursor: str | None
    total_matches: int


# --- ports -----------------------------------------------------------------


@runtime_checkable
class MediaStoragePort(Protocol):
    """Injected storage seam. The service only ever asks for authorized refs."""

    def open(self, ref: str) -> Mapping[str, Any]:
        """Return ``data``/``byte_length``/``content_type`` for one opaque ref."""


@runtime_checkable
class ResumeMediaRepository(Protocol):
    """Repository seam the Resume media service depends on."""

    def get_draft(self, owner_id: str) -> DraftMediaRecord: ...

    def commit_draft(
        self,
        *,
        owner_id: str,
        expected_version: int,
        placements: Sequence[MediaPlacement],
        receipt: RequestReceipt,
    ) -> DraftMediaRecord: ...

    def get_publication(self, owner_id: str) -> PublicationRecord: ...

    def commit_publication(
        self,
        *,
        owner_id: str,
        expected_draft_version: int,
        expected_publication_version: int,
        placements: Sequence[MediaPlacement],
        digest: str,
        receipt: RequestReceipt,
    ) -> PublicationRecord: ...

    def get_receipt(
        self, *, owner_id: str, command_type: str, request_uuid: str
    ) -> RequestReceipt | None: ...

    def get_owner_photo(
        self, owner_id: str, source_id: str
    ) -> OwnerPhotoRecord | None: ...

    def create_owner_photo(self, record: OwnerPhotoRecord) -> OwnerPhotoRecord: ...

    def update_owner_photo_state(
        self,
        *,
        owner_id: str,
        source_id: str,
        record: OwnerPhotoRecord,
        expected_lifecycle: str,
        expected_version: int,
        expected_version_token: str,
    ) -> OwnerPhotoRecord: ...

    def get_catalog_asset(
        self, asset_id: str, version: int | None = None
    ) -> CatalogAssetRecord | None: ...

    def list_catalog(
        self,
        *,
        query: str | None,
        category: str | None,
        tags: Sequence[str],
        limit: int,
        cursor: str | None,
    ) -> CatalogPage: ...

    def get_media_authorization(
        self, *, owner_id: str, placement: MediaPlacement
    ) -> MediaAuthorization | None: ...


# --- synthetic in-memory doubles (test-only) -------------------------------


class InMemoryMediaStorage:
    """Synthetic, deterministic, test-only storage double.

    It stores bytes under opaque refs and supports injected read failures and a
    read-time callback so a test can mutate authorization state inside the read
    barrier. It is not a production store and proves no real storage behavior.
    """

    def __init__(self) -> None:
        self._objects: dict[str, dict[str, Any]] = {}
        self._failures: dict[str, str] = {}
        self.on_open: Any = None
        self.opens: list[str] = []

    def put(
        self,
        ref: str,
        data: bytes,
        *,
        content_type: str = "image/jpeg",
        digest: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "data": bytes(data),
            "content_type": str(content_type),
            "digest": str(digest) if digest else sha256_hex(data),
            "byte_length": len(data),
        }
        self._objects[str(ref)] = record
        return record

    def digest_for(self, ref: str) -> str:
        return self._objects[str(ref)]["digest"]

    def fail_open(self, ref: str, code: str = "storage-unavailable") -> None:
        self._failures[str(ref)] = str(code)

    def open(self, ref: str) -> Mapping[str, Any]:
        key = str(ref)
        self.opens.append(key)
        if self.on_open is not None:
            self.on_open(key)
        if key in self._failures:
            raise ResumeMediaRepositoryError(self._failures[key])
        record = self._objects.get(key)
        if record is None:
            raise ResumeMediaRepositoryError("storage-unavailable")
        return dict(record)

    def refs(self) -> tuple[str, ...]:
        return tuple(sorted(self._objects))


class InMemoryResumeMediaRepository:
    """Synthetic, deterministic, test-only repository implementation.

    Every write is applied under one lock and either fully lands or is rolled
    back to the previous immutable snapshot, so tests can prove rollback and
    failure behavior through the declared seam. It proves contracts only: no
    SQL, storage, identity, or deployment behavior is exercised.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._drafts: dict[str, DraftMediaRecord] = {}
        self._publications: dict[str, PublicationRecord] = {}
        self._receipts: dict[tuple[str, str, str], RequestReceipt] = {}
        self._owner_photos: dict[tuple[str, str], OwnerPhotoRecord] = {}
        self._catalog: dict[tuple[str, int], CatalogAssetRecord] = {}
        self._sequence = 0
        self._catalog_generation = 0
        self._mutations: list[str] = []
        self._failures: dict[tuple[str, str], list[str]] = {}
        # Test-only seam: invoked inside the lock at the top of a committing
        # write so a test can inject a restriction/deletion/version race
        # between service validation and the atomic repository write.
        self.on_commit_entry: Any = None

    # -- deterministic bookkeeping used by tests ---------------------------

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _note(self, name: str) -> None:
        self._mutations.append(str(name))

    @property
    def mutation_log(self) -> tuple[str, ...]:
        return tuple(self._mutations)

    def inject_failure(
        self, operation: str, *, step: str | None = None, code: str = "injected-failure"
    ) -> None:
        """Queue one injected failure for the next matching repository step."""

        self._failures.setdefault((str(operation), str(step or "")), []).append(
            str(code)
        )

    def _maybe_fail(self, operation: str, step: str) -> None:
        queued = self._failures.get((operation, step))
        if queued:
            raise ResumeMediaRepositoryError(queued.pop(0))

    def snapshot(self) -> str:
        """Canonical JSON of every persisted record, for rollback proofs."""

        with self._lock:
            return canonical_json(
                {
                    "drafts": [
                        {
                            "owner_id": record.owner_id,
                            "version": record.version,
                            "placements": [self._placement_json(p) for p in record.placements],
                        }
                        for record in sorted(
                            self._drafts.values(), key=lambda item: item.owner_id
                        )
                    ],
                    "publications": [
                        {
                            "owner_id": record.owner_id,
                            "version": record.version,
                            "digest": record.digest,
                            "placements": [self._placement_json(p) for p in record.placements],
                        }
                        for record in sorted(
                            self._publications.values(), key=lambda item: item.owner_id
                        )
                    ],
                    "receipts": [
                        {
                            "owner_id": receipt.owner_id,
                            "command_type": receipt.command_type,
                            "request_uuid": receipt.request_uuid,
                            "semantic_digest": receipt.semantic_digest,
                            "outcome": receipt.outcome,
                        }
                        for receipt in sorted(
                            self._receipts.values(),
                            key=lambda item: (
                                item.owner_id,
                                item.command_type,
                                item.request_uuid,
                            ),
                        )
                    ],
                    "owner_photos": [
                        {
                            "owner_id": record.owner_id,
                            "source_id": record.source_id,
                            "state": record.state,
                            "version": record.version,
                            "version_token": record.version_token,
                            "digest": record.digest,
                            "lifecycle": record.lifecycle,
                            "derivative_ref": record.derivative_ref,
                        }
                        for record in sorted(
                            self._owner_photos.values(),
                            key=lambda item: (item.owner_id, item.source_id),
                        )
                    ],
                    "catalog": [
                        {
                            "asset_id": record.asset_id,
                            "version": record.version,
                            "digest": record.digest,
                            "lifecycle": record.lifecycle,
                            "provenance": record.provenance,
                            "rights": record.rights,
                            "derivatives": [
                                {
                                    "slot": derivative.slot,
                                    "ref": derivative.ref,
                                    "digest": derivative.digest,
                                }
                                for derivative in record.derivatives
                            ],
                        }
                        for record in sorted(
                            self._catalog.values(),
                            key=lambda item: (item.asset_id, item.version),
                        )
                    ],
                    "catalog_generation": self._catalog_generation,
                }
            )

    @staticmethod
    def _placement_json(placement: MediaPlacement) -> dict[str, Any]:
        return {
            "slot": placement.slot,
            "source_kind": placement.source_kind,
            "asset_id": placement.asset_id,
            "asset_version": placement.asset_version,
            "asset_digest": placement.asset_digest,
            "crop": placement.crop.as_dict(),
            "presentation_version": placement.presentation_version,
            "alt_text": placement.alt_text,
            "decorative": placement.decorative,
            "provenance_label": placement.provenance_label,
            "caption": placement.caption,
        }

    # -- seeding helpers used by tests -------------------------------------

    def seed_owner_photo(
        self,
        *,
        owner_id: str,
        source_id: str,
        state: str = READINESS_READY,
        digest: str = "",
        width: int = 1200,
        height: int = 800,
        content_type: str = "image/jpeg",
        byte_length: int = 0,
        derivative_ref: str | None = None,
        lifecycle: str = LIFECYCLE_ACTIVE,
        version: int = 1,
        version_token: str = "0000000000000001",
        reason_code: str | None = None,
    ) -> OwnerPhotoRecord:
        if state not in READINESS_STATES:
            raise ResumeMediaRepositoryError("invalid-readiness")
        if lifecycle not in LIFECYCLE_STATES:
            raise ResumeMediaRepositoryError("invalid-lifecycle")
        record = OwnerPhotoRecord(
            owner_id=str(owner_id),
            source_id=str(source_id),
            state=state,
            version_token=str(version_token),
            digest=str(digest),
            width=int(width),
            height=int(height),
            content_type=str(content_type),
            byte_length=int(byte_length),
            derivative_ref=derivative_ref,
            lifecycle=lifecycle,
            version=int(version),
            reason_code=reason_code,
        )
        with self._lock:
            self._owner_photos[(record.owner_id, record.source_id)] = record
        return record

    def update_owner_photo(
        self, *, owner_id: str, source_id: str, **changes: Any
    ) -> OwnerPhotoRecord:
        with self._lock:
            record = self._owner_photos.get((str(owner_id), str(source_id)))
            if record is None:
                raise ResumeMediaRepositoryError("unknown-source")
            updated = OwnerPhotoRecord(
                **{
                    **{
                        "owner_id": record.owner_id,
                        "source_id": record.source_id,
                        "state": record.state,
                        "version_token": record.version_token,
                        "digest": record.digest,
                        "width": record.width,
                        "height": record.height,
                        "content_type": record.content_type,
                        "byte_length": record.byte_length,
                        "derivative_ref": record.derivative_ref,
                        "lifecycle": record.lifecycle,
                        "version": record.version,
                        "reason_code": record.reason_code,
                    },
                    **changes,
                }
            )
            self._owner_photos[(updated.owner_id, updated.source_id)] = updated
            return updated

    def seed_catalog_asset(
        self,
        *,
        asset_id: str,
        label: str,
        category: str,
        tags: Iterable[str] = (),
        width: int = 1600,
        height: int = 900,
        version: int = 1,
        digest: str = "",
        origin: str = SOURCE_KIND_GENERATED_ILLUSTRATION,
        provenance: Mapping[str, Any] | None = None,
        rights: Mapping[str, Any] | None = None,
        derivatives: Iterable[Mapping[str, Any]] = (),
        lifecycle: str = LIFECYCLE_ACTIVE,
    ) -> CatalogAssetRecord:
        if origin not in SOURCE_KINDS:
            raise ResumeMediaRepositoryError("invalid-source-kind")
        if lifecycle not in LIFECYCLE_STATES:
            raise ResumeMediaRepositoryError("invalid-lifecycle")
        record = CatalogAssetRecord(
            asset_id=str(asset_id),
            version=int(version),
            digest=str(digest),
            label=str(label),
            category=str(category),
            tags=tuple(str(tag) for tag in tags),
            width=int(width),
            height=int(height),
            origin=origin,
            provenance=freeze_metadata(provenance or {}),
            rights=freeze_metadata(rights or {}),
            derivatives=tuple(
                CatalogDerivative(
                    slot=str(entry["slot"]),
                    ref=str(entry["ref"]),
                    digest=str(entry["digest"]),
                    content_type=str(entry.get("content_type", "image/png")),
                    byte_length=int(entry.get("byte_length", 0)),
                )
                for entry in derivatives
            ),
            lifecycle=lifecycle,
        )
        with self._lock:
            self._catalog[(record.asset_id, record.version)] = record
            self._catalog_generation += 1
        return record

    def set_catalog_lifecycle(
        self, *, asset_id: str, version: int, lifecycle: str
    ) -> CatalogAssetRecord:
        if lifecycle not in LIFECYCLE_STATES:
            raise ResumeMediaRepositoryError("invalid-lifecycle")
        with self._lock:
            key = (str(asset_id), int(version))
            record = self._catalog.get(key)
            if record is None:
                raise ResumeMediaRepositoryError("unknown-asset")
            updated = CatalogAssetRecord(
                asset_id=record.asset_id,
                version=record.version,
                digest=record.digest,
                label=record.label,
                category=record.category,
                tags=record.tags,
                width=record.width,
                height=record.height,
                origin=record.origin,
                provenance=record.provenance,
                rights=record.rights,
                derivatives=record.derivatives,
                lifecycle=lifecycle,
            )
            self._catalog[key] = updated
            self._catalog_generation += 1
            return updated

    # -- read paths ---------------------------------------------------------

    def get_draft(self, owner_id: str) -> DraftMediaRecord:
        with self._lock:
            record = self._drafts.get(str(owner_id))
        if record is not None:
            return record
        return DraftMediaRecord(owner_id=str(owner_id), version=0, placements=())

    def get_publication(self, owner_id: str) -> PublicationRecord:
        with self._lock:
            record = self._publications.get(str(owner_id))
        if record is not None:
            return record
        return PublicationRecord(owner_id=str(owner_id), version=0, placements=())

    def get_receipt(
        self, *, owner_id: str, command_type: str, request_uuid: str
    ) -> RequestReceipt | None:
        if command_type not in CLOSED_COMMAND_TYPES:
            raise ResumeMediaRepositoryError("invalid-command")
        with self._lock:
            return self._receipts.get(
                (str(owner_id), str(command_type), str(request_uuid))
            )

    def get_owner_photo(
        self, owner_id: str, source_id: str
    ) -> OwnerPhotoRecord | None:
        with self._lock:
            return self._owner_photos.get((str(owner_id), str(source_id)))

    def get_catalog_asset(
        self, asset_id: str, version: int | None = None
    ) -> CatalogAssetRecord | None:
        with self._lock:
            if version is not None:
                return self._catalog.get((str(asset_id), int(version)))
            candidates = [
                record
                for (candidate_id, _), record in self._catalog.items()
                if candidate_id == str(asset_id)
            ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.version)

    def list_catalog(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        tags: Sequence[str] = (),
        limit: int = CATALOG_PAGE_SIZE_DEFAULT,
        cursor: str | None = None,
    ) -> CatalogPage:
        fingerprint = catalog_query_fingerprint(
            query=query, category=category, tags=tags
        )
        normalized_query = normalize_catalog_query(query)
        normalized_category = normalize_search_text(category)
        normalized_tags = sorted(
            {normalize_search_text(tag) for tag in tags if normalize_search_text(tag)}
        )
        page_limit = max(1, min(int(limit), CATALOG_PAGE_SIZE_LIMIT))
        with self._lock:
            generation = self._catalog_generation
            last_key = (
                decode_catalog_cursor(
                    cursor, fingerprint=fingerprint, generation=generation
                )
                if cursor
                else None
            )
            latest: dict[str, CatalogAssetRecord] = {}
            for (asset_id, version), record in self._catalog.items():
                if record.lifecycle != LIFECYCLE_ACTIVE:
                    continue
                current = latest.get(asset_id)
                if current is None or version > current.version:
                    latest[asset_id] = record
            matches = [
                record
                for record in latest.values()
                if self._catalog_matches(
                    record,
                    query=normalized_query,
                    category=normalized_category,
                    tags=normalized_tags,
                )
            ]
        matches.sort(key=self._catalog_sort_key)
        total_matches = len(matches)
        if last_key is not None:
            matches = [
                record for record in matches if self._catalog_sort_key(record) > last_key
            ]
        page = tuple(matches[:page_limit])
        next_cursor = (
            encode_catalog_cursor(
                fingerprint=fingerprint,
                generation=generation,
                last_key=self._catalog_sort_key(page[-1]),
            )
            if len(matches) > len(page)
            else None
        )
        return CatalogPage(
            items=page, next_cursor=next_cursor, total_matches=total_matches
        )

    @staticmethod
    def _catalog_sort_key(record: CatalogAssetRecord) -> tuple[str, str, int]:
        """Deterministic keyset key: label, stable asset id, immutable version."""

        return (record.label.casefold(), record.asset_id, record.version)

    @staticmethod
    def _catalog_matches(
        record: CatalogAssetRecord,
        *,
        query: str,
        category: str,
        tags: Sequence[str],
    ) -> bool:
        if category and normalize_search_text(record.category) != category:
            return False
        record_tags = {normalize_search_text(tag) for tag in record.tags}
        if tags and not set(tags).issubset(record_tags):
            return False
        if not query:
            return True
        haystack = " ".join(
            [normalize_search_text(record.label), normalize_search_text(record.category)]
            + sorted(record_tags)
        )
        return query in haystack

    def get_media_authorization(
        self, *, owner_id: str, placement: MediaPlacement
    ) -> MediaAuthorization | None:
        if placement.slot not in SLOT_SPECS:
            return None
        if placement.source_kind == SOURCE_KIND_OWNER_PHOTO:
            record = self.get_owner_photo(owner_id, placement.asset_id)
            if record is None or record.lifecycle != LIFECYCLE_ACTIVE:
                return None
            if record.state != READINESS_READY:
                return None
            if record.version != placement.asset_version:
                return None
            if record.digest != placement.asset_digest:
                return None
            return MediaAuthorization(
                slot=placement.slot,
                accessor=ACCESSOR_PHOTO_READINESS,
                asset_version=record.version,
                asset_digest=record.digest,
                expected_digest=record.digest,
                byte_length=record.byte_length,
                content_type=record.content_type,
                source_id=record.source_id,
                source_version_token=record.version_token,
                width=record.width,
                height=record.height,
            )
        if placement.source_kind == SOURCE_KIND_GENERATED_ILLUSTRATION:
            record = self.get_catalog_asset(placement.asset_id, placement.asset_version)
            if record is None or record.lifecycle != LIFECYCLE_ACTIVE:
                return None
            if record.digest != placement.asset_digest:
                return None
            derivative = record.derivative_for(placement.slot)
            if derivative is None:
                return None
            return MediaAuthorization(
                slot=placement.slot,
                accessor=ACCESSOR_STORAGE,
                asset_version=record.version,
                asset_digest=record.digest,
                expected_digest=derivative.digest,
                byte_length=derivative.byte_length,
                content_type=derivative.content_type,
                ref=derivative.ref,
                width=record.width,
                height=record.height,
            )
        return None

    # -- write paths (atomic with rollback) --------------------------------

    def create_owner_photo(self, record: OwnerPhotoRecord) -> OwnerPhotoRecord:
        """Insert one new mirrored source; never overwrite an existing row."""

        with self._lock:
            self._maybe_fail("create_owner_photo", "write")
            if record.lifecycle != LIFECYCLE_ACTIVE:
                raise ResumeMediaRepositoryError(
                    _lifecycle_conflict_code(record.lifecycle)
                )
            key = (record.owner_id, record.source_id)
            if key in self._owner_photos:
                raise ResumeMediaRepositoryError("source-exists")
            self._owner_photos[key] = record
            self._note("create_owner_photo")
            try:
                self._maybe_fail("create_owner_photo", "after_write")
            except ResumeMediaRepositoryError:
                self._owner_photos.pop(key, None)
                self._note("rollback:create_owner_photo")
                raise
            return record

    def update_owner_photo_state(
        self,
        *,
        owner_id: str,
        source_id: str,
        record: OwnerPhotoRecord,
        expected_lifecycle: str,
        expected_version: int,
        expected_version_token: str,
    ) -> OwnerPhotoRecord:
        """Compare-and-set one mirrored source under the repository lock.

        The row is addressed by the requested owner/source identity, never by a
        provider-returned record identity, and the stored
        lifecycle/version/version token must match exactly while the stored
        lifecycle is still active: a restriction, deletion, withdrawal, or
        version change that lands after a service precheck can never be
        overwritten by a stale readiness result.
        """

        with self._lock:
            key = (str(owner_id), str(source_id))
            if record.owner_id != key[0] or record.source_id != key[1]:
                raise ResumeMediaRepositoryError("source-changed")
            current = self._owner_photos.get(key)
            if current is None:
                raise ResumeMediaRepositoryError("not-authorized")
            if current.lifecycle != LIFECYCLE_ACTIVE:
                raise ResumeMediaRepositoryError(
                    _lifecycle_conflict_code(current.lifecycle)
                )
            if (
                current.lifecycle != str(expected_lifecycle)
                or current.version != int(expected_version)
                or current.version_token != str(expected_version_token)
            ):
                raise ResumeMediaRepositoryError("source-changed")
            self._maybe_fail("update_owner_photo_state", "write")
            previous = current
            self._owner_photos[key] = record
            self._note("update_owner_photo_state")
            try:
                self._maybe_fail("update_owner_photo_state", "after_write")
            except ResumeMediaRepositoryError:
                self._owner_photos[key] = previous
                self._note("rollback:update_owner_photo_state")
                raise
            return record

    def commit_draft(
        self,
        *,
        owner_id: str,
        expected_version: int,
        placements: Sequence[MediaPlacement],
        receipt: RequestReceipt,
    ) -> DraftMediaRecord:
        owner_id = str(owner_id)
        with self._lock:
            if self.on_commit_entry is not None:
                self.on_commit_entry("commit_draft")
            self._maybe_fail("commit_draft", "before")
            previous = self._drafts.get(owner_id)
            current_version = previous.version if previous else 0
            if int(expected_version) != current_version:
                raise ResumeMediaRepositoryError("stale-draft")
            # Authorization is derived from - and bound to - the exact
            # placements persisted by this transaction, under the same
            # repository lock. There is no independently supplied list and no
            # default that can bypass the fence, so a restriction, deletion,
            # withdrawal, swap or version change that lands after the service
            # precheck cannot be committed.
            planned = tuple(placements)
            self._revalidate_placements(owner_id=owner_id, placements=planned)
            record = DraftMediaRecord(
                owner_id=owner_id,
                version=current_version + 1,
                placements=planned,
                updated_sequence=self._next_sequence(),
            )
            self._drafts[owner_id] = record
            self._note("commit_draft")
            try:
                self._maybe_fail("commit_draft", "after_draft")
                self._store_receipt(receipt)
            except ResumeMediaRepositoryError:
                if previous is None:
                    self._drafts.pop(owner_id, None)
                else:
                    self._drafts[owner_id] = previous
                self._note("rollback:commit_draft")
                raise
            return record

    def commit_publication(
        self,
        *,
        owner_id: str,
        expected_draft_version: int,
        expected_publication_version: int,
        placements: Sequence[MediaPlacement],
        digest: str,
        receipt: RequestReceipt,
    ) -> PublicationRecord:
        owner_id = str(owner_id)
        with self._lock:
            if self.on_commit_entry is not None:
                self.on_commit_entry("commit_publication")
            self._maybe_fail("commit_publication", "before")
            draft = self._drafts.get(owner_id)
            draft_version = draft.version if draft else 0
            if int(expected_draft_version) != draft_version:
                raise ResumeMediaRepositoryError("stale-draft")
            previous = self._publications.get(owner_id)
            current_version = previous.version if previous else 0
            if int(expected_publication_version) != current_version:
                raise ResumeMediaRepositoryError("stale-publication")
            planned = tuple(placements)
            self._revalidate_placements(owner_id=owner_id, placements=planned)
            record = PublicationRecord(
                owner_id=owner_id,
                version=current_version + 1,
                placements=planned,
                digest=str(digest),
                published_sequence=self._next_sequence(),
            )
            self._publications[owner_id] = record
            self._note("commit_publication")
            try:
                self._maybe_fail("commit_publication", "after_publication")
                self._store_receipt(receipt)
            except ResumeMediaRepositoryError:
                if previous is None:
                    self._publications.pop(owner_id, None)
                else:
                    self._publications[owner_id] = previous
                self._note("rollback:commit_publication")
                raise
            return record

    def _revalidate_placements(
        self, *, owner_id: str, placements: Sequence[MediaPlacement]
    ) -> None:
        """Validate the exact placements this transaction is about to persist.

        Requirements are derived from the persisted placements rather than
        supplied independently, so a call cannot validate one source and store
        another. Slots are unique, and every persisted source, crop and
        presentation/provenance semantic is bound under the same lock as the
        write.
        """

        planned = tuple(placements)
        if len(planned) > len(PLACEMENT_SLOTS):
            raise ResumeMediaRepositoryError("duplicate-slot")
        seen: set[str] = set()
        for placement in planned:
            slot = str(placement.slot)
            if slot not in SLOT_SPECS:
                raise ResumeMediaRepositoryError("invalid-slot")
            if slot in seen:
                raise ResumeMediaRepositoryError("duplicate-slot")
            seen.add(slot)
            self._validate_persisted_placement(owner_id=owner_id, placement=placement)

    def _validate_persisted_placement(
        self, *, owner_id: str, placement: MediaPlacement
    ) -> None:
        slot = str(placement.slot)
        if placement.source_kind == SOURCE_KIND_OWNER_PHOTO:
            record = self._owner_photos.get((owner_id, str(placement.asset_id)))
            if record is None:
                raise ResumeMediaRepositoryError("not-authorized")
            if record.lifecycle != LIFECYCLE_ACTIVE:
                raise ResumeMediaRepositoryError(
                    _lifecycle_conflict_code(record.lifecycle)
                )
            if record.state in (READINESS_REJECTED, READINESS_QUARANTINED):
                raise ResumeMediaRepositoryError("source-rejected")
            if record.state == READINESS_FAILED:
                raise ResumeMediaRepositoryError("source-failed")
            if record.state != READINESS_READY:
                raise ResumeMediaRepositoryError("source-not-ready")
            width, height = record.width, record.height
            derived_label = provenance_label_for(
                source_kind=SOURCE_KIND_OWNER_PHOTO
            )
        elif placement.source_kind == SOURCE_KIND_GENERATED_ILLUSTRATION:
            record = self._catalog.get(
                (str(placement.asset_id), int(placement.asset_version))
            )
            if record is None or record.lifecycle != LIFECYCLE_ACTIVE:
                if record is not None and record.lifecycle == LIFECYCLE_WITHDRAWN:
                    raise ResumeMediaRepositoryError("asset-withdrawn")
                raise ResumeMediaRepositoryError("asset-unavailable")
            if record.derivative_for(slot) is None:
                raise ResumeMediaRepositoryError("asset-unavailable")
            width, height = record.width, record.height
            derived_label = provenance_label_for(
                source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION, record=record
            )
        else:
            raise ResumeMediaRepositoryError("invalid-source")
        if record.version != int(placement.asset_version):
            raise ResumeMediaRepositoryError("stale-version")
        if record.digest != str(placement.asset_digest):
            raise ResumeMediaRepositoryError("stale-digest")
        if not isinstance(placement.presentation_version, int) or isinstance(
            placement.presentation_version, bool
        ):
            raise ResumeMediaRepositoryError("invalid-presentation-version")
        if placement.presentation_version < 1:
            raise ResumeMediaRepositoryError("invalid-presentation-version")
        if width <= 0 or height <= 0:
            raise ResumeMediaRepositoryError("source-unavailable")
        validate_crop_geometry(
            placement.crop.as_dict(), slot=slot, width=width, height=height
        )
        alt_text = normalize_alt_text(placement.alt_text)
        decorative = normalize_decorative(placement.decorative)
        caption = normalize_caption(placement.caption)
        if not decorative and not alt_text:
            raise ResumeMediaRepositoryError("required")
        label = _bounded_text(
            placement.provenance_label,
            code="invalid-provenance",
            max_length=MAX_PROVENANCE_LABEL_LENGTH,
            allow_empty=False,
        )
        if label != derived_label:
            raise ResumeMediaRepositoryError("invalid-provenance")
        if placement.source_kind == SOURCE_KIND_GENERATED_ILLUSTRATION:
            assert_no_catalog_claim(alt_text=alt_text, caption=caption, record=record)

    def _store_receipt(self, receipt: RequestReceipt) -> RequestReceipt:
        key = (receipt.owner_id, receipt.command_type, receipt.request_uuid)
        existing = self._receipts.get(key)
        if existing is not None:
            if existing.semantic_digest != receipt.semantic_digest:
                raise ResumeMediaRepositoryError("receipt-conflict")
            return existing
        stored = receipt
        if not stored.recorded_sequence:
            stored = RequestReceipt(
                owner_id=receipt.owner_id,
                command_type=receipt.command_type,
                request_uuid=receipt.request_uuid,
                semantic_digest=receipt.semantic_digest,
                outcome_json=receipt.outcome_json,
                recorded_sequence=self._next_sequence(),
            )
        self._receipts[key] = stored
        self._note("store_receipt:" + receipt.command_type)
        return stored
