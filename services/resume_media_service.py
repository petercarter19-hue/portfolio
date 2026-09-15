"""Dark, dependency-injected service for private Resume media placement.

Scope: the bounded MVP1 D backend for two decorative Resume placement slots
(``story_banner``, ``experience_support``) with owner-private photo sources, a
curated generated-illustration catalog, crop validation, private Add, review and
immutable publication, and application-controlled media reads.

This module is deliberately dark and framework independent. It registers no
Flask route, edits no SQL or migration, enables no feature flag, and touches no
live identity, provider, storage, or member data. Every collaborator is
injected: a repository seam, an optional media storage seam, and a Photo
Capture-shaped readiness seam.

Photo Capture reuse: ``ResumePhotoReadinessAdapter`` consumes the existing
owner-scoped source lifecycle (``create_source`` -> scan -> process ->
``needs_review``) through the injected port and never calls Photo Capture's
``confirm_capture`` canonical operation. Readiness, digest, and dimension
reporting mirror ``services/photo_capture_service.py``; opaque derivative
references mirror ``services/capture_media_storage_service.py``.

Honest limits: tests against these seams prove contracts only. They do not
prove SQL, real storage, real malware scanning, live identity, or deployment.
"""

from __future__ import annotations

import io
import threading
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from services.resume_media_repository import (
    ACCESSOR_PHOTO_READINESS,
    ACCESSOR_STORAGE,
    CATALOG_PAGE_SIZE_DEFAULT,
    CATALOG_PAGE_SIZE_LIMIT,
    COMMAND_ADD_MEDIA,
    COMMAND_KEEP_WORDS_ONLY,
    COMMAND_PUBLISH,
    CROP_PRECISION,
    IDENTITY_PRESENTATION_PORTRAIT,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_DELETED,
    LIFECYCLE_RESTRICTED,
    LIFECYCLE_WITHDRAWN,
    PLACEMENT_SLOTS,
    READINESS_FAILED,
    READINESS_QUARANTINED,
    READINESS_READY,
    READINESS_REJECTED,
    SOURCE_KIND_GENERATED_ILLUSTRATION,
    SOURCE_KIND_OWNER_PHOTO,
    SOURCE_KINDS,
    SLOT_SPECS,
    TERMINAL_READINESS_STATES,
    CropRect,
    DraftMediaRecord,
    MediaAuthorization,
    MediaPlacement,
    OwnerPhotoRecord,
    PublicationRecord,
    RequestReceipt,
    ResumeMediaRepositoryError,
    SlotSpec,
    assert_no_catalog_claim,
    catalog_provenance_view,
    catalog_rights_view,
    crop_numbers,
    canonical_json,
    normalize_alt_text,
    normalize_caption,
    normalize_decorative,
    orientation_for,
    provenance_label_for,
    sha256_hex,
    validate_crop_geometry,
)


SCOPE_OWNER_PREVIEW = "owner_preview"
SCOPE_OWNER_DRAFT = "owner_draft"
SCOPE_PUBLISHED = "published"
MEDIA_SCOPES = (SCOPE_OWNER_PREVIEW, SCOPE_OWNER_DRAFT, SCOPE_PUBLISHED)

MAX_REQUEST_UUID_LENGTH = 128

# Repository codes that mean "the caller's own state conflicts", mapped to a
# stable conflict type so callers can branch without string matching.
CONFLICT_CODES = frozenset(
    {
        "asset-unavailable",
        "asset-withdrawn",
        "catalog-changed",
        "catalog-claim-not-allowed",
        "crop-slot-mismatch",
        "idempotency-conflict",
        "receipt-conflict",
        "source-changed",
        "source-deleted",
        "source-exists",
        "source-failed",
        "source-not-ready",
        "source-rejected",
        "source-restricted",
        "source-withdrawn",
        "stale-digest",
        "stale-draft",
        "stale-publication",
        "stale-version",
    }
)

DEFAULT_CATALOG_PAGE_SIZE = CATALOG_PAGE_SIZE_DEFAULT
MAX_CATALOG_PAGE_SIZE = CATALOG_PAGE_SIZE_LIMIT

# Photo Capture readiness vocabulary -> Resume readiness vocabulary. Photo
# Capture keeps a `confirmed` state for its canonical Capture operation; the
# Resume adapter intentionally treats only scan/processing completion as ready
# and never performs that canonical confirm.
PHOTO_CAPTURE_STATE_MAP = {
    "draft": "uploading",
    "uploading": "uploading",
    "scanning": "scanning",
    "processing": "processing",
    "needs_review": READINESS_READY,
    "confirmed": READINESS_READY,
    "ready": READINESS_READY,
    "failed": READINESS_FAILED,
    "rejected": READINESS_REJECTED,
    "quarantined": READINESS_QUARANTINED,
}

UPLOAD_ERROR_MAP = {
    "required": "required",
    "unsupported": "unsupported-source",
    "too-large": "source-too-large",
    "draft-limit": "source-limit",
    "dimensions": "source-dimensions",
    "invalid-image": "unsupported-source",
}


class ResumeMediaError(RuntimeError):
    """Stable, content-free Resume media outcome code."""

    def __init__(self, code: str):
        self.code = str(code)
        super().__init__(self.code)


class ResumeMediaDenied(ResumeMediaError):
    """Stable denial for any cross-owner, forged, or unknown reference.

    The same code and message are returned whether the reference does not exist
    or belongs to another owner, so a caller learns nothing about other members.
    """

    def __init__(self) -> None:
        super().__init__("not-authorized")


class ResumeMediaConflict(ResumeMediaError):
    """Stable conflict for stale, conflicting, or ineligible state."""


# --- crop and slot validation ---------------------------------------------


def resolve_placement_slot(slot: Any) -> str:
    """Return one allowed decorative slot, refusing the identity portrait."""

    if not isinstance(slot, str) or not slot.strip():
        raise ResumeMediaError("invalid-slot")
    name = slot.strip()
    if name == IDENTITY_PRESENTATION_PORTRAIT:
        raise ResumeMediaConflict("slot-not-allowed")
    if name not in PLACEMENT_SLOTS:
        raise ResumeMediaError("invalid-slot")
    return name


def validate_crop(
    crop: Any, *, slot: str, width: int, height: int
) -> CropRect:
    """Validate one crop rectangle, reusing the repository geometry contract.

    The same function is re-applied inside the repository's atomic commit so a
    service-side precheck and the persisted placement cannot disagree.
    """

    return _translate(
        validate_crop_geometry, crop, slot=slot, width=width, height=height
    )


def slot_spec(slot: Any) -> SlotSpec:
    """Return one slot's bounded presentation contract, refusing the portrait."""

    name = resolve_placement_slot(slot)
    spec = SLOT_SPECS.get(name)
    if spec is None:  # pragma: no cover - every allowed slot declares a spec
        raise ResumeMediaError("invalid-slot")
    return spec


def centered_slot_crop(*, slot: Any, width: Any, height: Any) -> CropRect:
    """Derive the largest centered crop that already carries the slot's shape.

    Used when a source moves between slots, where reusing the previous slot's
    crop geometry would present the wrong shape. The result is validated by the
    same geometry contract the repository re-applies at commit time.
    """

    name = resolve_placement_slot(slot)
    try:
        source_width = int(width)
        source_height = int(height)
    except (TypeError, ValueError) as error:
        raise ResumeMediaError("invalid-source") from error
    if source_width <= 0 or source_height <= 0:
        raise ResumeMediaError("invalid-source")
    spec = slot_spec(name)
    source_aspect = source_width / source_height
    if source_aspect >= spec.aspect:
        crop_height = 1.0
        crop_width = (spec.aspect * source_height) / source_width
    else:
        crop_width = 1.0
        crop_height = source_width / (spec.aspect * source_height)
    crop_width = min(crop_width, 1.0)
    crop_height = min(crop_height, 1.0)
    candidate = {
        "x": round((1.0 - crop_width) / 2.0, CROP_PRECISION),
        "y": round((1.0 - crop_height) / 2.0, CROP_PRECISION),
        "width": round(crop_width, CROP_PRECISION),
        "height": round(crop_height, CROP_PRECISION),
    }
    return validate_crop(
        candidate, slot=name, width=source_width, height=source_height
    )


def _translate(function: Any, *args: Any, **kwargs: Any) -> Any:
    """Map repository seam codes onto stable service outcomes."""

    try:
        return function(*args, **kwargs)
    except ResumeMediaRepositoryError as error:
        raise _service_error(error.code) from error


def _service_error(code: str) -> ResumeMediaError:
    if code == "not-authorized":
        return ResumeMediaDenied()
    if code in CONFLICT_CODES:
        return ResumeMediaConflict(code)
    return ResumeMediaError(code)


def _lifecycle_conflict(lifecycle: str) -> ResumeMediaConflict:
    return ResumeMediaConflict(
        {
            LIFECYCLE_DELETED: "source-deleted",
            LIFECYCLE_RESTRICTED: "source-restricted",
            LIFECYCLE_WITHDRAWN: "source-withdrawn",
        }.get(str(lifecycle), "source-unavailable")
    )


def _photo_state_error(record: Any) -> ResumeMediaError:
    """Stable conflict for a source that exists but cannot be served."""

    lifecycle = str(getattr(record, "lifecycle", "") or "")
    if lifecycle and lifecycle != LIFECYCLE_ACTIVE:
        return _lifecycle_conflict(lifecycle)
    state = str(getattr(record, "state", "") or "")
    if state in (READINESS_REJECTED, READINESS_QUARANTINED):
        return ResumeMediaConflict("source-rejected")
    if state == READINESS_FAILED:
        return ResumeMediaConflict("source-failed")
    if state != READINESS_READY:
        return ResumeMediaConflict("source-not-ready")
    return ResumeMediaError("source-unavailable")


# --- Photo Capture readiness seam ------------------------------------------


@runtime_checkable
class PhotoCaptureSourcePort(Protocol):
    """The Photo Capture surface the Resume adapter reuses.

    Deliberately excludes ``confirm_capture`` and ``finish_capture_deletion``:
    a Resume adapter must never turn a scanned source into a canonical Capture.
    """

    def create_source(self, owner_id: str, upload: Any) -> Mapping[str, Any]: ...

    def get_source(
        self, owner_id: str, source_key: str
    ) -> Mapping[str, Any] | None: ...

    def reconcile_and_process(
        self, owner_id: str, source_key: str, expected_row_version: Any
    ) -> Mapping[str, Any]: ...

    def open_media(
        self, owner_id: str, source_key: str, media_kind: str
    ) -> Mapping[str, Any] | None: ...


def _hex_digest(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return raw.hex() if len(raw) != 32 else raw.hex()
    text = str(value).strip()
    return text.lower()


def _row_version_number(value: Any) -> int:
    """Return an exact SQL-bigint Photo Capture row-version value.

    Resume placements use a numeric asset version for both source kinds. Photo
    Capture's authoritative version is SQL ``rowversion``; retain all eight
    bytes as one non-negative Python integer so the proposed SQL fence can
    compare the reviewed placement with the locked source row.
    """

    token = _hex_digest(value)
    if len(token) != 16 or any(character not in "0123456789abcdef" for character in token):
        raise ResumeMediaError("source-unavailable")
    version = int(token, 16)
    # The proposed placement schema uses bigint. Refuse values whose high bit
    # cannot be represented by SQL Server bigint instead of wrapping or losing
    # source-version identity at the durable fence.
    if version > 0x7FFF_FFFF_FFFF_FFFF:
        raise ResumeMediaError("source-unavailable")
    return version


class ResumePhotoReadinessAdapter:
    """Map Photo Capture's source lifecycle onto Resume readiness.

    Preserves ``uploading -> scanning -> processing -> ready`` and refuses to
    invoke Photo Capture's canonical confirm-to-Capture operation. The adapter
    never exposes original filenames, blob names, or scan metadata upward.
    """

    FORBIDDEN_METHODS = ("confirm_capture", "finish_capture_deletion")

    def __init__(self, capture: PhotoCaptureSourcePort):
        if capture is None:
            raise ResumeMediaError("readiness-unavailable")
        self._capture = capture

    def _normalize(self, row: Any) -> dict[str, Any] | None:
        if not row:
            return None
        state = PHOTO_CAPTURE_STATE_MAP.get(str(row.get("state") or "").strip().lower())
        if state is None:
            raise ResumeMediaError("source-unavailable")
        source_id = str(row.get("source_key") or row.get("source_id") or "")
        if not source_id:
            raise ResumeMediaError("source-unavailable")
        raw_version = row.get("row_version") or row.get("version_token")
        record = {
            "source_id": source_id,
            "state": state,
            "version_token": _hex_digest(raw_version),
            "source_version": _row_version_number(raw_version),
            "digest": "",
            "width": 0,
            "height": 0,
            "content_type": "",
            "byte_length": 0,
            "derivative_ref": row.get("derivative_blob_name"),
            "reason_code": row.get("safe_error_code") or None,
        }
        if state == READINESS_READY:
            digest = _hex_digest(
                row.get("derivative_sha256_digest") or row.get("derivative_digest")
            )
            width = int(row.get("pixel_width") or 0)
            height = int(row.get("pixel_height") or 0)
            if not digest or width <= 0 or height <= 0:
                # Never invent readiness from an incomplete source record.
                raise ResumeMediaError("source-unavailable")
            record.update(
                {
                    "digest": digest,
                    "width": width,
                    "height": height,
                    "content_type": str(
                        row.get("derivative_content_type") or "image/jpeg"
                    ),
                    "byte_length": int(row.get("derivative_byte_length") or 0),
                }
            )
        return record

    def create_source(self, owner_id: str, upload: Any) -> dict[str, Any]:
        try:
            row = self._capture.create_source(owner_id, upload)
        except ResumeMediaError:
            raise
        except Exception as error:
            code = str(getattr(error, "code", "") or "")
            raise ResumeMediaError(UPLOAD_ERROR_MAP.get(code, "upload-failed")) from error
        record = self._normalize(row)
        if record is None:
            raise ResumeMediaError("upload-failed")
        return record

    def get_source(self, owner_id: str, source_id: str) -> dict[str, Any] | None:
        try:
            row = self._capture.get_source(owner_id, source_id)
        except Exception as error:
            raise ResumeMediaError("source-unavailable") from error
        return self._normalize(row)

    def reconcile_source(
        self, owner_id: str, source_id: str, version_token: Any
    ) -> dict[str, Any]:
        try:
            row = self._capture.reconcile_and_process(owner_id, source_id, version_token)
        except ResumeMediaError:
            raise
        except Exception as error:
            code = str(getattr(error, "code", "") or "")
            if code == "changed":
                raise ResumeMediaConflict("stale-version") from error
            raise ResumeMediaError("source-processing-failed") from error
        record = self._normalize(row)
        if record is None:
            raise ResumeMediaError("source-unavailable")
        return record

    def open_source_media(
        self, owner_id: str, source_id: str, media_kind: str = "preview"
    ) -> Mapping[str, Any] | None:
        if media_kind != "preview":
            raise ResumeMediaError("invalid-request")
        try:
            opened = self._capture.open_media(owner_id, source_id, media_kind)
        except ResumeMediaError:
            raise
        except Exception as error:
            raise ResumeMediaError("media-unavailable") from error
        if not opened:
            return None
        return opened


# --- service ---------------------------------------------------------------


@dataclass(frozen=True)
class _ResolvedSource:
    kind: str
    asset_id: str
    asset_version: int
    asset_digest: str
    width: int
    height: int
    provenance_label: str = ""

    @property
    def orientation(self) -> str:
        return orientation_for(self.width, self.height)


def _require_text(value: Any, code: str, *, max_length: int = 0) -> str:
    if not isinstance(value, str):
        raise ResumeMediaError(code)
    text = value.strip()
    if not text:
        raise ResumeMediaError(code)
    if max_length and len(text) > max_length:
        raise ResumeMediaError(code)
    return text


def _require_version(value: Any, code: str = "invalid-request") -> int:
    # SQL rowversion values can exceed JavaScript's exact-integer range. The
    # browser therefore round-trips large versions as canonical decimal text;
    # normalize that one lossless representation at the API boundary.
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        if value != "0" and value.startswith("0"):
            raise ResumeMediaError(code)
        value = int(value)
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > 0x7FFF_FFFF_FFFF_FFFF
    ):
        raise ResumeMediaError(code)
    return int(value)


def _browser_safe_version(value: int) -> int | str:
    """Keep exact versions across JSON/JavaScript without numeric rounding."""

    version = int(value)
    return version if version <= 9_007_199_254_740_991 else str(version)


def _normalize_source_ref(source: Any) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        raise ResumeMediaError("invalid-source")
    kind = source.get("kind")
    if kind not in SOURCE_KINDS:
        raise ResumeMediaError("invalid-source")
    normalized: dict[str, Any] = {"kind": kind}
    if kind == SOURCE_KIND_OWNER_PHOTO:
        normalized["source_id"] = _require_text(source.get("source_id"), "invalid-source")
    else:
        normalized["asset_id"] = _require_text(source.get("asset_id"), "invalid-source")
        normalized["asset_version"] = _require_version(
            source.get("asset_version"), "invalid-source"
        )
    if source.get("expected_version") is not None:
        normalized["expected_version"] = _require_version(
            source.get("expected_version"), "invalid-source"
        )
    if source.get("expected_digest") is not None:
        normalized["expected_digest"] = _require_text(
            source.get("expected_digest"), "invalid-source"
        )
    return normalized


CHOICE_KEYS = {"slot", "source", "crop", "alt_text", "decorative", "caption"}


def _normalize_placement_semantics(choice: Mapping[str, Any]) -> dict[str, Any]:
    """Explicit, bounded placement semantics: alt text, decorativeness, caption."""

    alt_text = _translate(normalize_alt_text, choice.get("alt_text"))
    decorative = _translate(normalize_decorative, choice.get("decorative"))
    caption = _translate(normalize_caption, choice.get("caption"))
    if not decorative and not alt_text:
        # An informative image without alt text is unusable and unlabeled.
        raise ResumeMediaError("required")
    return {"alt_text": alt_text, "decorative": decorative, "caption": caption}


def _normalize_add_body(
    expected_draft_version: Any, choices: Any
) -> dict[str, Any]:
    version = _require_version(expected_draft_version)
    if isinstance(choices, (str, bytes)) or not isinstance(choices, Iterable):
        raise ResumeMediaError("required")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for choice in choices:
        if not isinstance(choice, Mapping):
            raise ResumeMediaError("invalid-request")
        if set(choice) - CHOICE_KEYS:
            raise ResumeMediaError("invalid-request")
        slot = resolve_placement_slot(choice.get("slot"))
        if slot in seen:
            raise ResumeMediaError("invalid-request")
        seen.add(slot)
        source = choice.get("source")
        if source is None:
            if any(
                choice.get(key) is not None
                for key in ("crop", "alt_text", "decorative", "caption")
            ):
                raise ResumeMediaError("invalid-request")
            entries.append({"slot": slot, "source": None, "crop": None})
            continue
        crop = choice.get("crop")
        if crop is None:
            raise ResumeMediaError("required")
        numbers = _translate(crop_numbers, crop)
        semantics = _normalize_placement_semantics(choice)
        entries.append(
            {
                "slot": slot,
                "source": _normalize_source_ref(source),
                "crop": {
                    key: round(numbers[key], CROP_PRECISION)
                    for key in ("x", "y", "width", "height")
                },
                **semantics,
            }
        )
    if not entries:
        raise ResumeMediaError("required")
    entries.sort(key=lambda entry: PLACEMENT_SLOTS.index(entry["slot"]))
    return {"expected_draft_version": version, "choices": entries}


def review_placement_view(placement: MediaPlacement) -> dict[str, Any]:
    """Safe, allowlisted projection of one digest-bound placement.

    This is the single projection used both to compute the review digest and to
    answer the owner's review request, so the owner can observe exactly the
    presentation semantics that will be published. Private storage/provider
    metadata is never part of it; the raw asset digest is bound by the digest
    but is not exposed.
    """

    return {
        "asset_kind": placement.source_kind,
        "asset_id": placement.asset_id,
        # SQL rowversion values can exceed JavaScript's exact-integer range.
        # Every browser-facing saved/review projection uses the same canonical
        # decimal text as the staged preview; the internal Python/SQL value
        # stays an exact integer.
        "asset_version": _browser_safe_version(placement.asset_version),
        "crop": placement.crop.as_dict(),
        "presentation_version": placement.presentation_version,
        "alt_text": placement.alt_text,
        "decorative": placement.decorative,
        "provenance_label": placement.provenance_label,
        "caption": placement.caption,
    }


def review_slots(draft: DraftMediaRecord) -> dict[str, dict[str, Any]]:
    """Slot-keyed safe review projection for the owner's current draft."""

    return {
        placement.slot: review_placement_view(placement)
        for placement in sorted(draft.placements, key=lambda item: item.slot)
    }


def _review_payload(
    draft: DraftMediaRecord, publication: PublicationRecord
) -> dict[str, Any]:
    return {
        "draft_version": draft.version,
        "publication_version": publication.version,
        "slots": {
            placement.slot: {
                **review_placement_view(placement),
                "asset_digest": placement.asset_digest,
            }
            for placement in sorted(draft.placements, key=lambda item: item.slot)
        },
    }


def review_digest(draft: DraftMediaRecord, publication: PublicationRecord) -> str:
    """Digest binding a review to exact draft/publication/asset versions."""

    return sha256_hex(canonical_json(_review_payload(draft, publication)))


class ResumeMediaService:
    """Coordinate private Resume media placement against injected seams."""

    def __init__(
        self,
        *,
        repository: Any,
        storage: Any = None,
        photo_readiness: Any = None,
    ):
        self._repository = repository
        self._storage = storage
        self._photo_readiness = photo_readiness
        self._staged: dict[tuple[str, str], MediaPlacement] = {}
        self._lock = threading.RLock()

    @property
    def repository(self) -> Any:
        """The repository this service commands (wiring and diagnostic access)."""

        return self._repository

    # -- shared helpers ----------------------------------------------------

    def _repository_call(self, function: Any, **kwargs: Any) -> Any:
        try:
            return function(**kwargs)
        except ResumeMediaRepositoryError as error:
            raise _service_error(error.code) from error

    def _receipt_after_conflict(
        self, owner_id: str, command_type: str, request_uuid: str, digest: str
    ) -> dict[str, Any] | None:
        """Re-arbitrate one optimistic conflict against the exact receipt.

        Two callers racing the same owner + command + request UUID + semantic
        digest must converge on one structural outcome. The loser of the
        optimistic write re-reads its receipt and returns the winner's outcome.
        """

        receipt = self._repository_call(
            self._repository.get_receipt,
            owner_id=owner_id,
            command_type=command_type,
            request_uuid=request_uuid,
        )
        if receipt is None or receipt.semantic_digest != digest:
            return None
        return receipt.outcome

    def _commit_with_convergence(
        self,
        *,
        owner_id: str,
        command_type: str,
        request_uuid: str,
        digest: str,
        commit: Any,
    ) -> Any:
        """Run one atomic commit, converging same-key racers on one outcome."""

        try:
            return commit()
        except ResumeMediaError as error:
            if not isinstance(error, ResumeMediaConflict):
                raise
            receipt = self._repository_call(
                self._repository.get_receipt,
                owner_id=owner_id,
                command_type=command_type,
                request_uuid=request_uuid,
            )
            if receipt is None:
                raise
            if receipt.semantic_digest == digest:
                # A same-key, same-body racer already committed this command.
                return receipt.outcome
            # Same key with a different body is a stable conflict, whichever
            # write lost the race.
            raise ResumeMediaConflict("idempotency-conflict") from error

    def _receipt_outcome(
        self, owner_id: str, command_type: str, request_uuid: str, digest: str
    ) -> dict[str, Any] | None:
        receipt = self._repository_call(
            self._repository.get_receipt,
            owner_id=owner_id,
            command_type=command_type,
            request_uuid=request_uuid,
        )
        if receipt is None:
            return None
        if receipt.semantic_digest != digest:
            raise ResumeMediaConflict("idempotency-conflict")
        return receipt.outcome

    def _commit_receipt(
        self, owner_id: str, command_type: str, request_uuid: str, digest: str,
        outcome: Mapping[str, Any],
    ) -> RequestReceipt:
        return RequestReceipt.create(
            owner_id=owner_id,
            command_type=command_type,
            request_uuid=request_uuid,
            semantic_digest=digest,
            outcome=outcome,
        )

    def _resolve_source(self, owner_id: str, source: Any) -> _ResolvedSource:
        normalized = _normalize_source_ref(source)
        if normalized["kind"] == SOURCE_KIND_OWNER_PHOTO:
            record = self._repository_call(
                self._repository.get_owner_photo,
                owner_id=owner_id,
                source_id=normalized["source_id"],
            )
            if record is None:
                raise ResumeMediaDenied()
            if record.lifecycle == LIFECYCLE_DELETED:
                raise ResumeMediaConflict("source-deleted")
            if record.lifecycle == LIFECYCLE_WITHDRAWN:
                raise ResumeMediaConflict("source-withdrawn")
            if record.lifecycle == LIFECYCLE_RESTRICTED:
                raise ResumeMediaConflict("source-restricted")
            if record.lifecycle != LIFECYCLE_ACTIVE:
                raise ResumeMediaConflict("source-unavailable")
            if record.state in (READINESS_REJECTED, READINESS_QUARANTINED):
                raise ResumeMediaConflict("source-rejected")
            if record.state == READINESS_FAILED:
                raise ResumeMediaConflict("source-failed")
            if record.state != READINESS_READY:
                raise ResumeMediaConflict("source-not-ready")
            if not record.digest or record.width <= 0 or record.height <= 0:
                raise ResumeMediaError("source-unavailable")
            self._check_expected(normalized, record.version, record.digest)
            return _ResolvedSource(
                kind=SOURCE_KIND_OWNER_PHOTO,
                asset_id=record.source_id,
                asset_version=record.version,
                asset_digest=record.digest,
                width=record.width,
                height=record.height,
                provenance_label=provenance_label_for(
                    source_kind=SOURCE_KIND_OWNER_PHOTO
                ),
            )
        record = self._repository_call(
            self._repository.get_catalog_asset,
            asset_id=normalized["asset_id"],
            version=normalized["asset_version"],
        )
        if record is None:
            raise ResumeMediaConflict("asset-unavailable")
        if record.origin != SOURCE_KIND_GENERATED_ILLUSTRATION:
            raise ResumeMediaError("invalid-source")
        if record.lifecycle == LIFECYCLE_WITHDRAWN:
            raise ResumeMediaConflict("asset-withdrawn")
        if record.lifecycle != LIFECYCLE_ACTIVE:
            raise ResumeMediaConflict("asset-unavailable")
        self._check_expected(normalized, record.version, record.digest)
        return _ResolvedSource(
            kind=SOURCE_KIND_GENERATED_ILLUSTRATION,
            asset_id=record.asset_id,
            asset_version=record.version,
            asset_digest=record.digest,
            width=record.width,
            height=record.height,
            provenance_label=provenance_label_for(
                source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION, record=record
            ),
        )

    @staticmethod
    def _check_expected(
        normalized: Mapping[str, Any], version: int, digest: str
    ) -> None:
        expected_version = normalized.get("expected_version")
        if expected_version is not None and int(expected_version) != int(version):
            raise ResumeMediaConflict("stale-version")
        expected_digest = normalized.get("expected_digest")
        if expected_digest is not None and str(expected_digest) != str(digest):
            raise ResumeMediaConflict("stale-digest")

    @staticmethod
    def _source_ref_for_placement(placement: MediaPlacement) -> dict[str, Any]:
        if placement.source_kind == SOURCE_KIND_OWNER_PHOTO:
            return {
                "kind": SOURCE_KIND_OWNER_PHOTO,
                "source_id": placement.asset_id,
                "expected_version": placement.asset_version,
                "expected_digest": placement.asset_digest,
            }
        return {
            "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
            "asset_id": placement.asset_id,
            "asset_version": placement.asset_version,
            "expected_digest": placement.asset_digest,
        }

    def _placement(
        self,
        slot: str,
        resolved: _ResolvedSource,
        crop: CropRect,
        *,
        alt_text: str,
        decorative: bool,
        caption: str | None,
        presentation_version: int,
    ) -> MediaPlacement:
        return MediaPlacement(
            slot=slot,
            source_kind=resolved.kind,
            asset_id=resolved.asset_id,
            asset_version=resolved.asset_version,
            asset_digest=resolved.asset_digest,
            crop=crop,
            presentation_version=presentation_version,
            alt_text=alt_text,
            decorative=decorative,
            provenance_label=resolved.provenance_label,
            caption=caption,
        )

    @staticmethod
    def _next_presentation_version(
        current: MediaPlacement | None, candidate: MediaPlacement
    ) -> int:
        """Server-derived presentation revision for one slot."""

        if current is None:
            return 1
        if current.presentation_fields() == candidate.presentation_fields():
            return current.presentation_version
        return current.presentation_version + 1

    def _semantic_placement(
        self,
        draft: DraftMediaRecord,
        slot: str,
        resolved: _ResolvedSource,
        crop: CropRect,
        semantics: Mapping[str, Any],
    ) -> MediaPlacement:
        """Build one placement with its server-derived presentation version."""

        candidate = self._placement(
            slot,
            resolved,
            crop,
            alt_text=str(semantics["alt_text"]),
            decorative=bool(semantics["decorative"]),
            caption=semantics["caption"],
            presentation_version=1,
        )
        return replace(
            candidate,
            presentation_version=self._next_presentation_version(
                draft.placement_for(slot), candidate
            ),
        )

    @staticmethod
    def _preview_payload(
        placement: MediaPlacement, resolved: _ResolvedSource
    ) -> dict[str, Any]:
        # Safe presentation metadata only: no filename, storage key, provider
        # locator, scan metadata, EXIF, owner id, raw digest or label claim.
        return {
            "slot": placement.slot,
            "source_kind": placement.source_kind,
            # Enough for the owner to name the exact reviewed source again.
            # The raw digest, storage key and provider locator stay private.
            "asset_id": placement.asset_id,
            "asset_version": _browser_safe_version(placement.asset_version),
            "decorative": placement.decorative,
            "biographical_evidence": False,
            "orientation": resolved.orientation,
            "width": resolved.width,
            "height": resolved.height,
            "crop": placement.crop.as_dict(),
            "alt_text": placement.alt_text,
            "caption": placement.caption,
            "provenance_label": placement.provenance_label,
            "presentation_version": placement.presentation_version,
        }

    def _staged_placement(self, owner_id: str, slot: str) -> MediaPlacement | None:
        with self._lock:
            return self._staged.get((owner_id, slot))

    def _clear_staged(self, owner_id: str) -> None:
        with self._lock:
            for key in [key for key in self._staged if key[0] == owner_id]:
                self._staged.pop(key, None)

    # -- private photo readiness -------------------------------------------

    def media_versions(self, *, owner_id: str) -> dict[str, int]:
        """The owner's current private draft and publication versions."""

        owner = _require_text(owner_id, "required")
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        publication = self._repository_call(
            self._repository.get_publication, owner_id=owner
        )
        return {
            "draft_version": int(draft.version),
            "publication_version": int(publication.version),
        }

    def owner_photo_view(self, *, owner_id: str) -> tuple[dict[str, Any], ...]:
        """Safe owner view of the mirrored private photo sources.

        Never exposes original filenames, storage keys, provider locators, scan
        metadata or digests. A source that is not ready is reported as
        ineligible, and a rejected or quarantined source is honestly terminal.
        """

        owner = _require_text(owner_id, "required")
        records = self._repository_call(
            self._repository.list_owner_photos, owner_id=owner
        )
        entries: list[dict[str, Any]] = []
        for record in records:
            selectable = (
                record.lifecycle == LIFECYCLE_ACTIVE
                and record.state == READINESS_READY
                and bool(record.digest)
                and int(record.width) > 0
                and int(record.height) > 0
            )
            entries.append(
                {
                    "source_id": record.source_id,
                    "state": record.state,
                    "lifecycle": record.lifecycle,
                    "orientation": record.orientation,
                    "width": int(record.width),
                    "height": int(record.height),
                    "content_type": str(record.content_type),
                    "selectable": selectable,
                    "preview_available": selectable,
                    "retryable": (
                        record.lifecycle == LIFECYCLE_ACTIVE
                        and record.state not in TERMINAL_READINESS_STATES
                    ),
                    "reason_code": record.reason_code,
                }
            )
        entries.sort(key=lambda entry: entry["source_id"])
        return tuple(entries)

    def ingest_private_photo(self, *, owner_id: str, upload: Any) -> dict[str, Any]:
        """Start one owner-private photo upload through the readiness seam."""

        owner = _require_text(owner_id, "required")
        if self._photo_readiness is None:
            raise ResumeMediaError("readiness-unavailable")
        record = self._photo_readiness.create_source(owner, upload)
        stored = self._repository_call(
            self._repository.create_owner_photo,
            record=self._photo_repository_record(owner, record),
        )
        return {"source_id": stored.source_id, "state": stored.state}

    def refresh_private_photo(
        self, *, owner_id: str, source_id: str
    ) -> dict[str, Any]:
        """Advance or retry one private photo source, returning its state."""

        owner = _require_text(owner_id, "required")
        source = _require_text(source_id, "required")
        previous = self._repository_call(
            self._repository.get_owner_photo, owner_id=owner, source_id=source
        )
        if previous is None:
            raise ResumeMediaDenied()
        if previous.lifecycle != LIFECYCLE_ACTIVE:
            # Fail closed: a deleted, restricted, or withdrawn source must
            # never be refreshed back into an active mirrored row.
            raise _lifecycle_conflict(previous.lifecycle)
        if self._photo_readiness is None:
            raise ResumeMediaError("readiness-unavailable")
        if previous.state in (READINESS_REJECTED, READINESS_QUARANTINED):
            return {
                "source_id": previous.source_id,
                "state": previous.state,
                "retryable": False,
            }
        record = self._photo_readiness.reconcile_source(
            owner, source, previous.version_token
        )
        if str(record.get("source_id") or "") != source:
            # The provider answered for a different source than the one that
            # was requested: fail closed and write nothing.
            raise ResumeMediaConflict("source-changed")
        # Compare-and-set against the exact prior lifecycle/version/token under
        # the repository lock, addressed by the requested owner/source identity
        # rather than a provider-returned row identity: a restriction, deletion,
        # or version change that landed after the precheck wins and no source is
        # resurrected or written to the wrong row.
        stored = self._repository_call(
            self._repository.update_owner_photo_state,
            owner_id=owner,
            source_id=source,
            record=self._photo_repository_record(owner, {**record, "source_id": source}),
            expected_lifecycle=previous.lifecycle,
            expected_version=previous.version,
            expected_version_token=previous.version_token,
        )
        return {
            "source_id": stored.source_id,
            "state": stored.state,
            "retryable": stored.state
            not in (READINESS_REJECTED, READINESS_QUARANTINED),
        }

    def _photo_repository_record(
        self, owner_id: str, record: Mapping[str, Any]
    ) -> OwnerPhotoRecord:
        return OwnerPhotoRecord(
            owner_id=owner_id,
            source_id=str(record["source_id"]),
            state=str(record["state"]),
            version_token=str(record.get("version_token") or ""),
            digest=str(record.get("digest") or ""),
            width=int(record.get("width") or 0),
            height=int(record.get("height") or 0),
            content_type=str(record.get("content_type") or ""),
            byte_length=int(record.get("byte_length") or 0),
            derivative_ref=record.get("derivative_ref"),
            version=int(record["source_version"]),
            reason_code=record.get("reason_code"),
        )

    # -- catalog -----------------------------------------------------------

    def list_library(
        self,
        *,
        query: Any = None,
        category: Any = None,
        tags: Any = (),
        limit: int = DEFAULT_CATALOG_PAGE_SIZE,
        cursor: Any = None,
    ) -> dict[str, Any]:
        """Search the curated generated-illustration catalog honestly."""

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ResumeMediaError("invalid-limit")
        if tags is None:
            tags = ()
        if isinstance(tags, (str, bytes)) or not isinstance(tags, Iterable):
            raise ResumeMediaError("invalid-request")
        page = self._repository_call(
            self._repository.list_catalog,
            query=query,
            category=category,
            tags=tuple(tags),
            limit=min(limit, MAX_CATALOG_PAGE_SIZE),
            cursor=cursor,
        )
        return {
            "items": [self._catalog_summary(asset) for asset in page.items],
            "next_cursor": page.next_cursor,
            "total": page.total_matches,
        }

    @staticmethod
    def _catalog_summary(asset: Any) -> dict[str, Any]:
        return {
            "asset_id": asset.asset_id,
            "asset_version": asset.version,
            "label": asset.label,
            "category": asset.category,
            "tags": list(asset.tags),
            "origin": asset.origin,
            "orientation": asset.orientation,
            "width": asset.width,
            "height": asset.height,
            # Explicit allowlists only: provider locators, storage keys, prompts
            # and any other internal metadata can never reach a caller.
            "provenance": catalog_provenance_view(asset),
            "rights": catalog_rights_view(asset),
        }

    # -- staging and preview ----------------------------------------------

    def stage_placement(
        self,
        *,
        owner_id: str,
        slot: Any,
        source: Any,
        crop: Any,
        alt_text: Any = None,
        decorative: Any = None,
        caption: Any = None,
    ) -> dict[str, Any]:
        """Stage one slot choice privately. This never touches the draft."""

        owner = _require_text(owner_id, "required")
        slot_name = resolve_placement_slot(slot)
        resolved = self._resolve_source(owner, source)
        rect = validate_crop(
            crop, slot=slot_name, width=resolved.width, height=resolved.height
        )
        semantics = _normalize_placement_semantics(
            {"alt_text": alt_text, "decorative": decorative, "caption": caption}
        )
        self._assert_catalog_claim(owner, resolved, semantics)
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        placement = self._semantic_placement(
            draft, slot_name, resolved, rect, semantics
        )
        with self._lock:
            self._staged[(owner, slot_name)] = placement
        return self._preview_payload(placement, resolved)

    def _assert_catalog_claim(
        self, owner_id: str, resolved: _ResolvedSource, semantics: Mapping[str, Any]
    ) -> None:
        """Refuse catalog labels/tags promoted into member-facing text."""

        if resolved.kind != SOURCE_KIND_GENERATED_ILLUSTRATION:
            return
        record = self._repository_call(
            self._repository.get_catalog_asset,
            asset_id=resolved.asset_id,
            version=resolved.asset_version,
        )
        if record is None:
            raise ResumeMediaConflict("asset-unavailable")
        _translate(
            assert_no_catalog_claim,
            alt_text=str(semantics.get("alt_text") or ""),
            caption=semantics.get("caption"),
            record=record,
        )

    def preview_placement(self, *, owner_id: str, slot: Any) -> dict[str, Any] | None:
        """Preview one staged slot, or None when nothing is stage-eligible."""

        owner = _require_text(owner_id, "required")
        slot_name = resolve_placement_slot(slot)
        placement = self._staged_placement(owner, slot_name)
        if placement is None:
            return None
        try:
            resolved = self._resolve_source(
                owner, self._source_ref_for_placement(placement)
            )
        except ResumeMediaError:
            # Deleted, restricted, withdrawn, or stale sources are ineligible.
            return None
        return self._preview_payload(placement, resolved)

    def clear_staged_placement(self, *, owner_id: str, slot: Any) -> bool:
        owner = _require_text(owner_id, "required")
        slot_name = resolve_placement_slot(slot)
        with self._lock:
            return self._staged.pop((owner, slot_name), None) is not None

    def staged_placement_view(self, *, owner_id: str) -> dict[str, Any]:
        """Owner-scoped view of pending slot choices. Never a draft write."""

        owner = _require_text(owner_id, "required")
        staged: dict[str, Any] = {}
        for slot in PLACEMENT_SLOTS:
            placement = self._staged_placement(owner, slot)
            if placement is None:
                continue
            preview = self.preview_placement(owner_id=owner, slot=slot)
            if preview is not None:
                staged[slot] = preview
        return staged

    def draft_media_view(self, *, owner_id: str) -> dict[str, Any]:
        """Safe owner view of the saved private draft media state.

        This is the draft, not the publication: nothing here is shared, and an
        unavailable or revoked source is reported honestly rather than served.
        """

        owner = _require_text(owner_id, "required")
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        slots: dict[str, Any] = {}
        for slot in PLACEMENT_SLOTS:
            placement = draft.placement_for(slot)
            if placement is None:
                slots[slot] = None
                continue
            entry: dict[str, Any] = {
                "slot": slot,
                "source_kind": placement.source_kind,
                **review_placement_view(placement),
            }
            try:
                resolved = self._resolve_source(
                    owner, self._source_ref_for_placement(placement)
                )
            except ResumeMediaError:
                entry["media_available"] = False
            else:
                entry.update(
                    {
                        "media_available": True,
                        "orientation": resolved.orientation,
                        "width": resolved.width,
                        "height": resolved.height,
                    }
                )
            slots[slot] = entry
        return {"draft_version": draft.version, "slots": slots}

    def swap_staged_placements(self, *, owner_id: str) -> dict[str, Any]:
        """Swap two staged sources and give each one its new slot's shape.

        The previous slot's crop geometry is never reused for the other shape:
        each swapped source is resolved again and receives a crop that already
        carries the target slot's presentation aspect.
        """

        owner = _require_text(owner_id, "required")
        current = {slot: self._staged_placement(owner, slot) for slot in PLACEMENT_SLOTS}
        if any(placement is None for placement in current.values()):
            raise ResumeMediaConflict("required")
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        moved = {
            PLACEMENT_SLOTS[0]: current[PLACEMENT_SLOTS[1]],
            PLACEMENT_SLOTS[1]: current[PLACEMENT_SLOTS[0]],
        }
        previews: dict[str, Any] = {}
        with self._lock:
            for slot, source_placement in moved.items():
                resolved = self._resolve_source(
                    owner, self._source_ref_for_placement(source_placement)
                )
                rect = centered_slot_crop(
                    slot=slot, width=resolved.width, height=resolved.height
                )
                semantics = {
                    "alt_text": source_placement.alt_text,
                    "decorative": source_placement.decorative,
                    "caption": source_placement.caption,
                }
                self._assert_catalog_claim(owner, resolved, semantics)
                placement = self._semantic_placement(
                    draft, slot, resolved, rect, semantics
                )
                self._staged[(owner, slot)] = placement
                previews[slot] = self._preview_payload(placement, resolved)
        return {"slots": previews}

    # -- private Add -------------------------------------------------------

    def add_media_choices(
        self,
        *,
        owner_id: str,
        request_uuid: str,
        expected_draft_version: Any,
        choices: Any,
    ) -> dict[str, Any]:
        """Commit explicit staged media choices atomically against the draft."""

        owner = _require_text(owner_id, "required")
        request = _require_text(
            request_uuid, "required", max_length=MAX_REQUEST_UUID_LENGTH
        )
        body = _normalize_add_body(expected_draft_version, choices)
        digest = sha256_hex(
            canonical_json({"command": COMMAND_ADD_MEDIA, **body})
        )
        replay = self._receipt_outcome(owner, COMMAND_ADD_MEDIA, request, digest)
        if replay is not None:
            return replay
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        if draft.version != body["expected_draft_version"]:
            raise ResumeMediaConflict("stale-draft")
        placements = list(draft.placements)
        committed: list[str] = []
        removed: list[str] = []
        for entry in body["choices"]:
            slot = entry["slot"]
            placements = [item for item in placements if item.slot != slot]
            if entry["source"] is None:
                removed.append(slot)
                continue
            resolved = self._resolve_source(owner, entry["source"])
            rect = validate_crop(
                entry["crop"], slot=slot, width=resolved.width, height=resolved.height
            )
            semantics = {
                "alt_text": entry["alt_text"],
                "decorative": entry["decorative"],
                "caption": entry["caption"],
            }
            self._assert_catalog_claim(owner, resolved, semantics)
            placements.append(
                self._semantic_placement(draft, slot, resolved, rect, semantics)
            )
            committed.append(slot)
        placements.sort(key=lambda item: PLACEMENT_SLOTS.index(item.slot))
        outcome = {
            "command": COMMAND_ADD_MEDIA,
            "outcome": "committed",
            "draft_version": draft.version + 1,
            "slots": sorted(committed, key=PLACEMENT_SLOTS.index),
            "removed_slots": sorted(removed, key=PLACEMENT_SLOTS.index),
        }
        receipt = self._commit_receipt(
            owner, COMMAND_ADD_MEDIA, request, digest, outcome
        )
        stored = self._commit_with_convergence(
            owner_id=owner,
            command_type=COMMAND_ADD_MEDIA,
            request_uuid=request,
            digest=digest,
            commit=lambda: self._repository_call(
                self._repository.commit_draft,
                owner_id=owner,
                expected_version=draft.version,
                placements=tuple(placements),
                receipt=receipt,
            ),
        )
        if isinstance(stored, dict):
            # A concurrent same-key racer already committed this exact command.
            return stored
        self._clear_staged(owner)
        return {
            "command": outcome["command"],
            "outcome": outcome["outcome"],
            "draft_version": stored.version,
            "slots": outcome["slots"],
            "removed_slots": outcome["removed_slots"],
        }

    def keep_words_only(
        self,
        *,
        owner_id: str,
        request_uuid: str,
        expected_draft_version: Any,
    ) -> dict[str, Any]:
        """Skip pending media choices without removing published media."""

        owner = _require_text(owner_id, "required")
        request = _require_text(
            request_uuid, "required", max_length=MAX_REQUEST_UUID_LENGTH
        )
        version = _require_version(expected_draft_version)
        body = {"expected_draft_version": version}
        digest = sha256_hex(
            canonical_json({"command": COMMAND_KEEP_WORDS_ONLY, **body})
        )
        replay = self._receipt_outcome(owner, COMMAND_KEEP_WORDS_ONLY, request, digest)
        if replay is not None:
            return replay
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        if draft.version != version:
            raise ResumeMediaConflict("stale-draft")
        publication = self._repository_call(
            self._repository.get_publication, owner_id=owner
        )
        outcome = {
            "command": COMMAND_KEEP_WORDS_ONLY,
            "outcome": "committed",
            "draft_version": draft.version + 1,
            "slots": [],
            "removed_slots": [],
            "publication_version": publication.version,
        }
        receipt = self._commit_receipt(
            owner, COMMAND_KEEP_WORDS_ONLY, request, digest, outcome
        )
        converged = self._commit_with_convergence(
            owner_id=owner,
            command_type=COMMAND_KEEP_WORDS_ONLY,
            request_uuid=request,
            digest=digest,
            commit=lambda: self._repository_call(
                self._repository.commit_draft,
                owner_id=owner,
                expected_version=draft.version,
                placements=draft.placements,
                receipt=receipt,
            ),
        )
        if isinstance(converged, dict):
            return converged
        self._clear_staged(owner)
        return outcome

    # -- review and publication -------------------------------------------

    def review_draft(
        self,
        *,
        owner_id: str,
        expected_draft_version: Any,
        expected_publication_version: Any,
    ) -> dict[str, Any]:
        """Produce the reviewed digest. This has no publish side effect."""

        owner = _require_text(owner_id, "required")
        draft_version = _require_version(expected_draft_version)
        publication_version = _require_version(expected_publication_version)
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        if draft.version != draft_version:
            raise ResumeMediaConflict("stale-draft")
        publication = self._repository_call(
            self._repository.get_publication, owner_id=owner
        )
        if publication.version != publication_version:
            raise ResumeMediaConflict("stale-publication")
        return {
            "reviewed_digest": review_digest(draft, publication),
            "draft_version": draft.version,
            "publication_version": publication.version,
            # The same safe projection the digest is computed over, so the
            # owner can observe exactly what publication will use.
            "slots": review_slots(draft),
        }

    def publish(
        self,
        *,
        owner_id: str,
        request_uuid: str,
        expected_draft_version: Any,
        expected_publication_version: Any,
        reviewed_digest: Any,
    ) -> dict[str, Any]:
        """Publish the reviewed draft placements as one immutable revision."""

        owner = _require_text(owner_id, "required")
        request = _require_text(
            request_uuid, "required", max_length=MAX_REQUEST_UUID_LENGTH
        )
        draft_version = _require_version(expected_draft_version)
        publication_version = _require_version(expected_publication_version)
        reviewed = _require_text(reviewed_digest, "required")
        body = {
            "expected_draft_version": draft_version,
            "expected_publication_version": publication_version,
            "reviewed_digest": reviewed,
        }
        digest = sha256_hex(canonical_json({"command": COMMAND_PUBLISH, **body}))
        replay = self._receipt_outcome(owner, COMMAND_PUBLISH, request, digest)
        if replay is not None:
            return replay
        draft = self._repository_call(self._repository.get_draft, owner_id=owner)
        if draft.version != draft_version:
            raise ResumeMediaConflict("stale-draft")
        publication = self._repository_call(
            self._repository.get_publication, owner_id=owner
        )
        if publication.version != publication_version:
            raise ResumeMediaConflict("stale-publication")
        current_digest = review_digest(draft, publication)
        if current_digest != reviewed:
            raise ResumeMediaConflict("review-mismatch")
        for placement in draft.placements:
            resolved = self._resolve_source(
                owner, self._source_ref_for_placement(placement)
            )
            validate_crop(
                placement.crop.as_dict(),
                slot=placement.slot,
                width=resolved.width,
                height=resolved.height,
            )
        outcome = {
            "command": COMMAND_PUBLISH,
            "outcome": "published",
            "publication_version": publication.version + 1,
            "draft_version": draft.version,
            "slots": sorted(
                (placement.slot for placement in draft.placements),
                key=PLACEMENT_SLOTS.index,
            ),
        }
        receipt = self._commit_receipt(owner, COMMAND_PUBLISH, request, digest, outcome)
        stored = self._commit_with_convergence(
            owner_id=owner,
            command_type=COMMAND_PUBLISH,
            request_uuid=request,
            digest=digest,
            commit=lambda: self._repository_call(
                self._repository.commit_publication,
                owner_id=owner,
                expected_draft_version=draft.version,
                expected_publication_version=publication.version,
                placements=draft.placements,
                digest=current_digest,
                receipt=receipt,
            ),
        )
        if isinstance(stored, dict):
            # A concurrent same-key racer already published this exact command.
            return stored
        return {
            "command": outcome["command"],
            "outcome": outcome["outcome"],
            "publication_version": stored.version,
            "draft_version": outcome["draft_version"],
            "slots": outcome["slots"],
        }

    def current_publication(self, *, owner_id: str) -> dict[str, Any]:
        """Safe presentation metadata for the current published revision."""

        owner = _require_text(owner_id, "required")
        publication = self._repository_call(
            self._repository.get_publication, owner_id=owner
        )
        slots: dict[str, Any] = {}
        for slot in PLACEMENT_SLOTS:
            placement = publication.placement_for(slot)
            if placement is None:
                slots[slot] = None
                continue
            entry: dict[str, Any] = {
                "slot": slot,
                "source_kind": placement.source_kind,
                "decorative": placement.decorative,
                "crop": placement.crop.as_dict(),
                "alt_text": placement.alt_text,
                "caption": placement.caption,
                "provenance_label": placement.provenance_label,
                "presentation_version": placement.presentation_version,
            }
            try:
                resolved = self._resolve_source(
                    owner, self._source_ref_for_placement(placement)
                )
            except ResumeMediaError:
                entry["media_available"] = False
            else:
                entry.update(
                    {
                        "media_available": True,
                        "orientation": resolved.orientation,
                        "width": resolved.width,
                        "height": resolved.height,
                    }
                )
            slots[slot] = entry
        return {"publication_version": publication.version, "slots": slots}

    # -- media reads -------------------------------------------------------

    def open_placement_media(
        self, *, owner_id: str, slot: Any, scope: str = SCOPE_OWNER_PREVIEW
    ) -> dict[str, Any] | None:
        """Authorize, read, recheck, and only then return private bytes."""

        owner = _require_text(owner_id, "required")
        slot_name = resolve_placement_slot(slot)
        if scope not in MEDIA_SCOPES:
            raise ResumeMediaError("invalid-request")
        if scope == SCOPE_OWNER_PREVIEW:
            placement = self._staged_placement(owner, slot_name)
        elif scope == SCOPE_OWNER_DRAFT:
            # The saved private draft placement: this is what the member sees
            # after an explicit Add, including after a reload, and it is a
            # different state from the pending staged preview.
            draft = self._repository_call(self._repository.get_draft, owner_id=owner)
            placement = draft.placement_for(slot_name)
        else:
            publication = self._repository_call(
                self._repository.get_publication, owner_id=owner
            )
            placement = publication.placement_for(slot_name)
        if placement is None:
            return None
        authorization = self._repository_call(
            self._repository.get_media_authorization,
            owner_id=owner,
            placement=placement,
        )
        if authorization is None:
            return None
        data = self._read_bytes(owner, authorization)
        if (
            len(data) != authorization.byte_length
            or sha256_hex(data) != authorization.expected_digest
        ):
            raise ResumeMediaError("media-unavailable")
        if not self._still_authorized(owner, placement, authorization, scope):
            # Revoked, restricted, withdrawn, replaced, or version-changed
            # during the read: discard the bytes.
            return None
        if authorization.accessor == ACCESSOR_PHOTO_READINESS:
            # The mirrored repository row can be unchanged while the
            # authoritative Photo Capture source was revoked, restricted, or
            # replaced, so re-query the readiness port after the read.
            if not self._readiness_unchanged(owner, authorization):
                return None
        return {
            "stream": io.BytesIO(data),
            "content_type": authorization.content_type,
            "byte_length": len(data),
        }

    def open_private_photo_preview(
        self, *, owner_id: str, source_id: Any
    ) -> dict[str, Any] | None:
        """Authorize, read, recheck, and only then return one private preview.

        The My photos chooser shows an owner's own uploaded source before that
        source is staged for a placement slot. The read path is the same
        contract a placement read uses: deny before reading storage, verify the
        exact bytes, then re-query the authoritative readiness source so a
        restriction, deletion, replacement or version change that lands during
        the read discards the bytes instead of serving them.
        """

        owner = _require_text(owner_id, "required")
        source = _require_text(source_id, "required")
        authorization = self._repository_call(
            self._repository.get_source_authorization,
            owner_id=owner,
            source_id=source,
        )
        if authorization is None:
            record = self._repository_call(
                self._repository.get_owner_photo, owner_id=owner, source_id=source
            )
            if record is None:
                raise ResumeMediaDenied()
            raise _photo_state_error(record)
        data = self._read_bytes(owner, authorization)
        if (
            len(data) != authorization.byte_length
            or sha256_hex(data) != authorization.expected_digest
        ):
            raise ResumeMediaError("media-unavailable")
        current = self._repository_call(
            self._repository.get_source_authorization,
            owner_id=owner,
            source_id=source,
        )
        if current != authorization:
            return None
        if not self._readiness_unchanged(owner, authorization):
            return None
        return {
            "stream": io.BytesIO(data),
            "content_type": authorization.content_type,
            "byte_length": len(data),
        }

    def open_library_thumbnail(
        self, *, owner_id: str, asset_id: Any, asset_version: Any, slot: Any
    ) -> dict[str, Any] | None:
        """Authorize, read, recheck, and only then return one catalog derivative."""

        owner = _require_text(owner_id, "required")
        asset = _require_text(asset_id, "required")
        version = _require_version(asset_version)
        slot_name = resolve_placement_slot(slot)
        authorization = self._repository_call(
            self._repository.get_catalog_thumbnail_authorization,
            asset_id=asset,
            version=version,
            slot=slot_name,
        )
        if authorization is None:
            return None
        data = self._read_bytes(owner, authorization)
        if (
            len(data) != authorization.byte_length
            or sha256_hex(data) != authorization.expected_digest
        ):
            raise ResumeMediaError("media-unavailable")
        current = self._repository_call(
            self._repository.get_catalog_thumbnail_authorization,
            asset_id=asset,
            version=version,
            slot=slot_name,
        )
        if current != authorization:
            # Withdrawn, replaced or re-versioned during the read: drop bytes.
            return None
        return {
            "stream": io.BytesIO(data),
            "content_type": authorization.content_type,
            "byte_length": len(data),
        }

    def _readiness_unchanged(
        self, owner_id: str, authorization: MediaAuthorization
    ) -> bool:
        """Authoritative post-read recheck of one Photo Capture source."""

        if self._photo_readiness is None:
            return False
        try:
            snapshot = self._photo_readiness.get_source(
                owner_id, authorization.source_id
            )
        except ResumeMediaError:
            return False
        if not snapshot or snapshot.get("state") != READINESS_READY:
            return False
        return (
            str(snapshot.get("source_id") or "") == str(authorization.source_id)
            and str(snapshot.get("version_token") or "")
            == str(authorization.source_version_token or "")
            and str(snapshot.get("digest") or "")
            == str(authorization.expected_digest)
            and int(snapshot.get("width") or 0) == int(authorization.width)
            and int(snapshot.get("height") or 0) == int(authorization.height)
            and str(snapshot.get("content_type") or "")
            == str(authorization.content_type)
        )

    def _still_authorized(
        self,
        owner_id: str,
        placement: MediaPlacement,
        authorization: MediaAuthorization,
        scope: str,
    ) -> bool:
        if scope == SCOPE_OWNER_PREVIEW:
            current_placement = self._staged_placement(owner_id, placement.slot)
        elif scope == SCOPE_OWNER_DRAFT:
            draft = self._repository_call(self._repository.get_draft, owner_id=owner_id)
            current_placement = draft.placement_for(placement.slot)
        else:
            publication = self._repository_call(
                self._repository.get_publication, owner_id=owner_id
            )
            current_placement = publication.placement_for(placement.slot)
        if current_placement != placement:
            return False
        current = self._repository_call(
            self._repository.get_media_authorization,
            owner_id=owner_id,
            placement=placement,
        )
        return current == authorization

    def _read_bytes(self, owner_id: str, authorization: MediaAuthorization) -> bytes:
        if authorization.accessor == ACCESSOR_STORAGE:
            if self._storage is None:
                raise ResumeMediaError("storage-unavailable")
            try:
                record = self._storage.open(authorization.ref)
            except Exception as error:
                raise ResumeMediaError("media-unavailable") from error
            return bytes(record.get("data") or b"")
        if authorization.accessor == ACCESSOR_PHOTO_READINESS:
            if self._photo_readiness is None:
                raise ResumeMediaError("readiness-unavailable")
            opened = self._photo_readiness.open_source_media(
                owner_id, authorization.source_id, "preview"
            )
            if not opened:
                raise ResumeMediaError("media-unavailable")
            stream = opened.get("stream")
            if stream is not None and hasattr(stream, "read"):
                return bytes(stream.read())
            return bytes(opened.get("data") or b"")
        raise ResumeMediaError("media-unavailable")

    # -- biographical boundary --------------------------------------------

    def placement_fact_projection(self, *, owner_id: str) -> tuple[Any, ...]:
        """Biographical evidence contributed by Resume media: none.

        A generated illustration never proves member biography, and a private
        photo does not assert what the member did. Catalog labels, tags,
        prompts, and provenance are selection metadata only and are never
        returned as Resume evidence or member captions.
        """

        _require_text(owner_id, "required")
        return ()
