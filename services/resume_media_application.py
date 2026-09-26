"""MVP1 D integration: private Resume media chooser application layer.

This module binds the accepted Resume media service and repository contracts
(``PS-MVP1-MEDIA-BACKEND-001``) to the private Resume draft that increment B
already owns, and exposes bounded route-facing use cases for one scoped chooser.

Two integration facts matter most here:

* One owner has exactly one Resume draft version. Media Add, Keep it words
  only, and the existing editor text commands advance that same version, and a
  media commit applies its placement change to the live snapshot it fences, so
  a pending text save and a pending media save cannot silently overwrite each
  other.
* Nothing here is durable by default. Production wiring must inject an explicit
  repository and storage pair; without it the application refuses to serve
  rather than quietly using a test store. Schema stays proposed and unapplied.

Honest limits: tests against these seams prove contracts, route wiring,
authorization order, and rollback behavior. They do not prove SQL engine
execution, live Blob storage, malware scanning, live identity, or deployment.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Mapping, Sequence
from uuid import UUID

from services.database_service import DatabaseServiceError, database_service
from services.resume_media_repository import (
    CATALOG_PAGE_SIZE_DEFAULT,
    CATALOG_PAGE_SIZE_LIMIT,
    IDENTITY_PRESENTATION_PORTRAIT,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_WITHDRAWN,
    PLACEMENT_SLOTS,
    READINESS_READY,
    SOURCE_KIND_OWNER_PHOTO,
    TERMINAL_READINESS_STATES,
    CropRect,
    DraftMediaRecord,
    MediaPlacement,
    RequestReceipt,
    ResumeMediaRepositoryError,
    canonical_json,
)
from services.resume_media_service import (
    MAX_CATALOG_PAGE_SIZE,
    ResumeMediaError,
    ResumeMediaService,
    resolve_placement_slot,
)
from services.resume_draft_service import SHARED_MEDIA_STATE_ATTRIBUTE
from services.resume_draft_repository import ResumeDraftVersionConflict


RESUME_MEDIA_BROWSER_PROCEDURES = frozenset(
    {
        "usp_GetResumeMediaDraftForOwner",
        "usp_CommitResumeMediaCommandForOwner",
    }
)
RESUME_MEDIA_WORKER_PROCEDURES = frozenset()

MEDIA_SNAPSHOT_KEY = "media"
MEDIA_RECEIPT_KEY = "media_receipts"
MAX_MEDIA_REQUEST_UUID_LENGTH = 128

FORBIDDEN_CLIENT_FIELDS = frozenset(
    {
        "owner_user_key",
        "owner_id",
        "user_key",
        "owner_profile_id",
        "profile_id",
        "visibility",
        "publication_status",
        "approval_status",
        "resume_display",
        "visitor_ai",
        "publish",
        "published",
    }
)


class ResumeMediaApplicationUnavailable(RuntimeError):
    """The configured media application cannot run. Never a fixture success."""

    code = "unavailable"


def _authority_free(payload: Any) -> dict[str, Any]:
    """Drop client-supplied owner/authority fields before anything else."""

    if not isinstance(payload, Mapping):
        return {}
    return {
        key: value for key, value in payload.items() if key not in FORBIDDEN_CLIENT_FIELDS
    }


def _request_uuid(payload: Mapping[str, Any]) -> str:
    """One bounded command identity. A non-UUID key is refused before use."""

    raw = payload.get("request_uuid") or payload.get("request_id")
    if not isinstance(raw, str) or not raw.strip():
        raise ResumeMediaError("required")
    try:
        return str(UUID(raw.strip()))
    except (TypeError, ValueError) as error:
        raise ResumeMediaError("invalid-request") from error


def _placement_payload(placement: MediaPlacement) -> dict[str, Any]:
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


def _placement_from_payload(payload: Any) -> MediaPlacement:
    if not isinstance(payload, Mapping):
        raise ResumeMediaRepositoryError("invalid-placement")
    try:
        slot = resolve_placement_slot(payload.get("slot"))
        crop = payload.get("crop") or {}
        return MediaPlacement(
            slot=slot,
            source_kind=str(payload["source_kind"]),
            asset_id=str(payload["asset_id"]),
            asset_version=int(payload["asset_version"]),
            asset_digest=str(payload.get("asset_digest") or ""),
            crop=CropRect(
                x=float(crop["x"]),
                y=float(crop["y"]),
                width=float(crop["width"]),
                height=float(crop["height"]),
            ),
            presentation_version=int(payload.get("presentation_version") or 1),
            alt_text=str(payload.get("alt_text") or ""),
            decorative=bool(payload.get("decorative")),
            provenance_label=str(payload.get("provenance_label") or ""),
            caption=payload.get("caption"),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ResumeMediaRepositoryError("invalid-placement") from error


def _receipt_payload(receipt: RequestReceipt) -> dict[str, Any]:
    return {
        "command_type": receipt.command_type,
        "request_uuid": receipt.request_uuid,
        "semantic_digest": receipt.semantic_digest,
        "outcome": receipt.outcome,
    }


def _receipt_from_payload(payload: Any) -> RequestReceipt:
    if not isinstance(payload, Mapping):
        raise ResumeMediaRepositoryError("invalid-receipt")
    try:
        return RequestReceipt.create(
            owner_id=str(payload["owner_id"]),
            command_type=str(payload["command_type"]),
            request_uuid=str(payload["request_uuid"]),
            semantic_digest=str(payload["semantic_digest"]),
            outcome=payload["outcome"],
        )
    except (KeyError, TypeError) as error:
        raise ResumeMediaRepositoryError("invalid-receipt") from error


def _receipt_key(command_type: str, request_uuid: str) -> str:
    return f"{command_type}:{request_uuid}"


class ResumeDraftBoundMediaRepository:
    """Bind media draft state to the owner's one canonical Resume draft.

    Draft placements and media receipts live inside the owner's private Resume
    draft snapshot, so ``draft_version`` is shared with the editor's text
    commands. A commit re-reads the live snapshot under one process lock,
    fences the exact expected version, applies only its own media change, and
    writes once. Source lifecycle, catalog, publication and media
    authorization stay in the injected source repository: only draft-bound
    state is shared, and a text command's snapshot can never author media
    state.
    """

    persistence_label = "shared_resume_draft"
    command_port = True

    def __init__(self, *, draft_store: Any, sources: Any, lock: Any = None) -> None:
        if draft_store is None or sources is None:
            raise ResumeMediaApplicationUnavailable("media-unavailable")
        if not callable(getattr(draft_store, "commit_owner_command", None)) or not (
            getattr(draft_store, "atomic_command_supported", False)
        ) or not getattr(draft_store, "media_command_supported", False):
            # Without the store's atomic command boundary two writers can read
            # the same version and both persist, losing one placement and one
            # receipt. Fail closed instead of racing.
            raise ResumeMediaApplicationUnavailable("media-unavailable")
        # A commit revalidates each placement's source and then writes the
        # draft. Without a real fence between those two steps a concurrent
        # restriction can land immediately after the source read and the commit
        # still persists the placement. Accept either an in-process source
        # lifecycle lock (held across revalidation and the write) or a durable
        # adapter that fences sources inside its own database transaction; a
        # repository offering neither is not an authoritative fence.
        self._source_guard = getattr(sources, "lifecycle_guard", None)
        self._durable_source_fence = bool(
            getattr(draft_store, "durable_source_fence", False)
        )
        if not self._durable_source_fence and not callable(
            getattr(self._source_guard, "__enter__", None)
        ):
            raise ResumeMediaApplicationUnavailable("media-unavailable")
        self._draft_store = draft_store
        self._sources = sources
        self._lock = lock if lock is not None else threading.RLock()
        # Test-only seam: invoked inside the commit boundary after the version
        # fence and before source revalidation, so a test can land a source
        # revocation at the exact moment of the write.
        self.on_commit_entry: Any = None
        # Test-only seam: invoked at the end of source revalidation, while the
        # source lifecycle guard is still held, so a test can prove a
        # concurrent mutation cannot land between the commit's source read and
        # its persisted write.
        self.on_after_source_read: Any = None
        # Tell the editor's text commands that this store also carries media
        # draft state, so a text save preserves media it did not author.
        try:
            setattr(draft_store, SHARED_MEDIA_STATE_ATTRIBUTE, True)
        except Exception:  # pragma: no cover - a store may refuse attribute writes
            pass

    # -- draft-bound half --------------------------------------------------

    def get_draft(self, owner_id: str) -> DraftMediaRecord:
        with self._lock:
            snapshot = self._load(owner_id)
        media = snapshot.get(MEDIA_SNAPSHOT_KEY) or {}
        placements = media.get("placements") or []
        return DraftMediaRecord(
            owner_id=str(owner_id),
            version=int(snapshot.get("draft_version") or 0),
            placements=tuple(_placement_from_payload(entry) for entry in placements),
        )

    def commit_draft(
        self,
        *,
        owner_id: str,
        expected_version: int,
        placements: Sequence[MediaPlacement],
        receipt: RequestReceipt,
    ) -> DraftMediaRecord:
        """Commit one media command through the shared draft's atomic boundary.

        The store fences the exact expected draft version, this method
        revalidates every placement's source lifecycle/version/digest, and only
        then is anything persisted — all inside one boundary, so a source that
        is revoked, restricted, withdrawn, deleted or replaced at the moment of
        the commit cannot be saved as placement media.
        """

        owner = str(owner_id)
        version = int(expected_version)
        ordered = tuple(
            sorted(placements, key=lambda item: PLACEMENT_SLOTS.index(item.slot))
        )
        serialized = [_placement_payload(placement) for placement in ordered]
        receipt_key = _receipt_key(receipt.command_type, receipt.request_uuid)
        replay: dict[str, Any] = {}

        def apply(live: dict[str, Any]) -> bool:
            receipts = dict(live.get(MEDIA_RECEIPT_KEY) or {})
            stored_receipt = receipts.get(receipt_key)
            if stored_receipt is not None:
                if str(stored_receipt.get("semantic_digest")) != receipt.semantic_digest:
                    raise ResumeMediaRepositoryError("idempotency-conflict")
                replay["outcome"] = stored_receipt.get("outcome")
                return False
            if self.on_commit_entry is not None:
                self.on_commit_entry()
            self.revalidate_sources(owner, ordered)
            if self.on_after_source_read is not None:
                self.on_after_source_read()
            media = dict(live.get(MEDIA_SNAPSHOT_KEY) or {})
            media["placements"] = serialized
            media["generation"] = int(media.get("generation") or 0) + 1
            live[MEDIA_SNAPSHOT_KEY] = media
            receipts[receipt_key] = _receipt_payload(receipt)
            live[MEDIA_RECEIPT_KEY] = receipts
            # Applied before the store's version fence; the store persists only
            # when the live version still matches, so this is always
            # expected+1 for a committed change.
            live["draft_version"] = int(live.get("draft_version") or version) + 1
            live["_pending_command"] = {
                "request_id": receipt.request_uuid,
                "command_json": canonical_json(
                    {
                        "command": receipt.command_type,
                        "expected_draft_version": version,
                        "draft_version": version + 1,
                        "placements": serialized,
                        "receipt": _receipt_payload(receipt),
                    }
                ),
            }
            return True

        try:
            # Stable lock order: source lifecycle first, then the draft store.
            # Every source mutation takes the same guard, so a restriction that
            # arrives after this commit's source read waits for the write to
            # finish, and a restriction that arrived before it is seen by the
            # revalidation inside the boundary.
            if self._source_guard is not None:
                with self._source_guard:
                    stored = self._draft_store.commit_owner_command(
                        owner, expected_version=version, apply=apply
                    )
            else:
                stored = self._draft_store.commit_owner_command(
                    owner, expected_version=version, apply=apply
                )
        except ResumeDraftVersionConflict as error:
            raise ResumeMediaRepositoryError("stale-draft") from error
        except ResumeMediaRepositoryError:
            raise
        except Exception as error:  # storage, SQL, or unknown failure: nothing lands
            raise ResumeMediaRepositoryError("storage-unavailable") from error
        if replay:
            return DraftMediaRecord(
                owner_id=owner,
                version=int(stored.get("draft_version") or version),
                placements=tuple(
                    _placement_from_payload(entry)
                    for entry in (stored.get(MEDIA_SNAPSHOT_KEY) or {}).get("placements")
                    or []
                ),
            )
        return DraftMediaRecord(
            owner_id=owner,
            version=int(stored.get("draft_version") or version + 1),
            placements=ordered,
        )

    def revalidate_sources(
        self, owner_id: str, placements: Sequence[MediaPlacement]
    ) -> None:
        """Refuse a commit whose source is no longer eligible right now.

        Runs inside the atomic commit boundary while the source lifecycle guard
        is held, so a concurrent restriction, withdrawal, deletion or
        replacement either happened before this check (and is refused) or waits
        until the commit has finished. Every placement must still have an
        active, ready, version- and digest-matching source; otherwise a stable
        conflict is raised and nothing is written.
        """

        owner = str(owner_id)
        for placement in placements:
            if placement.source_kind == SOURCE_KIND_OWNER_PHOTO:
                record = self._sources.get_owner_photo(owner, placement.asset_id)
                if record is None:
                    raise ResumeMediaRepositoryError("source-unavailable")
                lifecycle = str(getattr(record, "lifecycle", "") or "")
                if lifecycle and lifecycle != LIFECYCLE_ACTIVE:
                    raise ResumeMediaRepositoryError(f"source-{lifecycle}")
                state = str(getattr(record, "state", "") or "")
                if state in ("rejected", "quarantined"):
                    raise ResumeMediaRepositoryError("source-rejected")
                if state == "failed":
                    raise ResumeMediaRepositoryError("source-failed")
                if state != READINESS_READY:
                    raise ResumeMediaRepositoryError("source-not-ready")
                if int(getattr(record, "version", 0)) != int(placement.asset_version):
                    raise ResumeMediaRepositoryError("stale-version")
                if str(getattr(record, "digest", "")) != str(placement.asset_digest):
                    raise ResumeMediaRepositoryError("stale-digest")
                continue
            record = self._sources.get_catalog_asset(
                placement.asset_id, placement.asset_version
            )
            if record is None:
                raise ResumeMediaRepositoryError("asset-unavailable")
            lifecycle = str(getattr(record, "lifecycle", "") or "")
            if lifecycle == LIFECYCLE_WITHDRAWN:
                raise ResumeMediaRepositoryError("asset-withdrawn")
            if lifecycle != LIFECYCLE_ACTIVE:
                raise ResumeMediaRepositoryError("asset-unavailable")
            if str(getattr(record, "digest", "")) != str(placement.asset_digest):
                raise ResumeMediaRepositoryError("stale-digest")

    def get_receipt(
        self, *, owner_id: str, command_type: str, request_uuid: str
    ) -> RequestReceipt | None:
        with self._lock:
            snapshot = self._load(str(owner_id))
        stored = (snapshot.get(MEDIA_RECEIPT_KEY) or {}).get(
            _receipt_key(str(command_type), str(request_uuid))
        )
        if not stored:
            return None
        return RequestReceipt.create(
            owner_id=str(owner_id),
            command_type=str(stored["command_type"]),
            request_uuid=str(stored["request_uuid"]),
            semantic_digest=str(stored["semantic_digest"]),
            outcome=stored["outcome"],
        )

    def _load(self, owner_id: str) -> dict[str, Any]:
        snapshot = self._draft_store.load_owner(str(owner_id))
        if snapshot is None:
            return {}
        if not isinstance(snapshot, dict):  # pragma: no cover - defensive
            raise ResumeMediaRepositoryError("invalid-draft")
        return snapshot

    # -- delegated source half --------------------------------------------

    def get_publication(self, owner_id: str) -> Any:
        return self._sources.get_publication(str(owner_id))

    def commit_publication(self, **kwargs: Any) -> Any:
        return self._sources.commit_publication(**kwargs)

    def get_owner_photo(self, owner_id: str, source_id: str) -> Any:
        return self._sources.get_owner_photo(str(owner_id), str(source_id))

    def list_owner_photos(self, owner_id: str) -> tuple[Any, ...]:
        return tuple(self._sources.list_owner_photos(str(owner_id)))

    def create_owner_photo(self, record: Any) -> Any:
        return self._sources.create_owner_photo(record)

    def update_owner_photo_state(self, **kwargs: Any) -> Any:
        return self._sources.update_owner_photo_state(**kwargs)

    def get_catalog_asset(self, asset_id: str, version: int | None = None) -> Any:
        return self._sources.get_catalog_asset(str(asset_id), version)

    def list_catalog(self, **kwargs: Any) -> Any:
        return self._sources.list_catalog(**kwargs)

    def get_media_authorization(self, **kwargs: Any) -> Any:
        return self._sources.get_media_authorization(**kwargs)

    def get_source_authorization(self, **kwargs: Any) -> Any:
        return self._sources.get_source_authorization(**kwargs)

    def get_catalog_thumbnail_authorization(self, **kwargs: Any) -> Any:
        return self._sources.get_catalog_thumbnail_authorization(**kwargs)


class SqlResumeMediaDraftStore:
    """Proposed durable media-draft binding. Fail closed until schema is applied.

    The procedures are proposed only: PS-RESUME-MEDIA-001 is unapplied and its
    registry gate is null. A missing procedure, missing grant, unapplied
    schema, or unavailable engine surfaces as an unavailable media command, and
    no snapshot is ever reported as saved.
    """

    persistence_label = "sql_proposed_unapplied"
    command_port = True
    # Proposed durable atomic command support: the media command procedure
    # fences the shared Resume draft version and writes placements plus receipt
    # in one transaction. Unapplied and unproven; this flag states the contract
    # the procedure is written to satisfy.
    atomic_command_supported = True
    media_command_supported = True
    # The media command procedure itself refuses a placement whose source is no
    # longer eligible (owner photos are fenced against the authoritative Photo
    # Capture source row inside that transaction). That is the durable source
    # fence this adapter relies on instead of an in-process lock.
    durable_source_fence = True

    def __init__(self, database: Any = None) -> None:
        self.database = database or database_service

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        try:
            result_sets = self.database.execute_procedure(
                "usp_GetResumeMediaDraftForOwner",
                [("@UserKey", owner_user_key)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeMediaRepositoryError("storage-unavailable") from error
        header_rows = result_sets[0] if result_sets else []
        placement_rows = result_sets[1] if result_sets and len(result_sets) > 1 else []
        receipt_rows = result_sets[2] if result_sets and len(result_sets) > 2 else []
        snapshot: dict[str, Any] = {
            "draft_version": 0,
            "items": {},
            "receipts": {},
            MEDIA_SNAPSHOT_KEY: {"placements": [], "generation": 0},
            MEDIA_RECEIPT_KEY: {},
        }
        if header_rows:
            header = header_rows[0]
            snapshot["draft_version"] = int(header.get("draft_version") or 0)
            snapshot["base_publication_version"] = header.get("base_publication_version")
        placements = []
        for row in placement_rows or []:
            try:
                crop = {
                    "x": float(row["crop_x"]),
                    "y": float(row["crop_y"]),
                    "width": float(row["crop_width"]),
                    "height": float(row["crop_height"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
            placements.append(
                {
                    "slot": row.get("slot"),
                    "source_kind": row.get("source_kind"),
                    "asset_id": row.get("asset_id"),
                    "asset_version": int(row.get("asset_version") or 0),
                    "asset_digest": str(row.get("asset_digest") or ""),
                    "crop": crop,
                    "presentation_version": int(row.get("presentation_version") or 1),
                    "alt_text": str(row.get("alt_text") or ""),
                    "decorative": bool(row.get("decorative")),
                    "provenance_label": str(row.get("provenance_label") or ""),
                    "caption": row.get("caption"),
                }
            )
        snapshot[MEDIA_SNAPSHOT_KEY] = {
            "placements": placements,
            "generation": int(
                (header_rows[0].get("media_generation") if header_rows else 0) or 0
            ),
        }
        receipts = {}
        for row in receipt_rows or []:
            outcome = row.get("outcome_json") or row.get("outcome") or {}
            if isinstance(outcome, str):
                try:
                    import json as _json

                    outcome = _json.loads(outcome)
                except ValueError as error:
                    raise ResumeMediaRepositoryError("invalid-receipt") from error
            command_type = str(row.get("command_type") or "")
            request_uuid = str(row.get("request_uuid") or "")
            if not command_type or not request_uuid:
                continue
            receipts[_receipt_key(command_type, request_uuid)] = {
                "command_type": command_type,
                "request_uuid": request_uuid,
                "semantic_digest": str(row.get("semantic_digest") or ""),
                "outcome": outcome,
            }
        snapshot[MEDIA_RECEIPT_KEY] = receipts
        return snapshot

    def save_owner(self, owner_user_key: str, snapshot: dict[str, Any]) -> None:
        pending = snapshot.get("_pending_command") if isinstance(snapshot, dict) else None
        if not isinstance(pending, dict) or not pending.get("request_id"):
            raise ResumeMediaRepositoryError("storage-unavailable")
        try:
            result_sets = self.database.execute_procedure(
                "usp_CommitResumeMediaCommandForOwner",
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", str(pending["request_id"])),
                    ("@CommandJson", str(pending["command_json"])),
                ],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeMediaRepositoryError("storage-unavailable") from error
        rows = result_sets[0] if result_sets else []
        if not rows:
            raise ResumeMediaRepositoryError("storage-unavailable")
        outcome = str(rows[0].get("outcome") or "")
        if outcome == "stale_draft":
            raise ResumeMediaRepositoryError("stale-draft")
        if outcome == "idempotency_conflict":
            raise ResumeMediaRepositoryError("idempotency-conflict")
        if outcome == "source_changed":
            # The authoritative source lifecycle moved (restricted, withdrawn,
            # deleted, replaced or no longer ready) inside the transaction.
            raise ResumeMediaRepositoryError("source-changed")
        if outcome == "source_unavailable":
            # No authoritative fence is available for this placement's source.
            raise ResumeMediaRepositoryError("source-unavailable")
        if outcome not in {"committed", "replayed"}:
            raise ResumeMediaRepositoryError("storage-unavailable")

    def commit_owner_command(
        self, owner_user_key: str, *, expected_version: int, apply: Any
    ) -> dict[str, Any]:
        """Apply, then fence, then hand the exactly one command to the procedure.

        The apply function performs the exact-replay check first and returns
        False for a confirmed replay, so an accepted command that already
        committed is never reported as a stale draft just because the shared
        version moved on afterwards. Only a real change has to satisfy the
        version fence, and the procedure re-fences the same version and the
        authoritative source lifecycle inside its own transaction.
        """

        live = self.load_owner(owner_user_key)
        current = int(live.get("draft_version") or 0)
        changed = apply(live)
        if changed is False:
            return live
        if current != int(expected_version):
            raise ResumeDraftVersionConflict(
                current=current, expected=int(expected_version)
            )
        self.save_owner(owner_user_key, live)
        # A concurrent exact retry can be accepted by the procedure after this
        # adapter's initial read. Reload so the caller receives the actual
        # durable version and placements rather than its speculative callback
        # copy.
        return self.load_owner(owner_user_key)


class PhotoCaptureResumeReadinessPort:
    """Bind the real Photo Capture service to the Resume readiness seam.

    Photo Capture's own read shapes are preserved: state, row version, pixel
    dimensions and content type come from its owner-scoped source read. The
    derivative digest the Resume mirror binds is computed from the exact
    private preview bytes Photo Capture's own media reader returns, so a
    non-empty derivative is never assumed. ``confirm_capture`` and
    ``finish_capture_deletion`` are deliberately not part of this port.
    """

    FORBIDDEN_METHODS = ("confirm_capture", "finish_capture_deletion")
    READY_SOURCE_STATES = ("needs_review", "confirmed", "ready")

    def __init__(self, capture: Any) -> None:
        if capture is None:
            raise ResumeMediaApplicationUnavailable("readiness-unavailable")
        self._capture = capture

    def create_source(self, owner_id: str, upload: Any) -> Mapping[str, Any]:
        return self._capture.create_source(owner_id, upload)

    def get_source(
        self, owner_id: str, source_id: str
    ) -> Mapping[str, Any] | None:
        return self._with_derivative_digest(
            owner_id, self._capture.get_source(owner_id, source_id)
        )

    def reconcile_and_process(
        self, owner_id: str, source_id: str, expected_row_version: Any
    ) -> Mapping[str, Any]:
        return self._with_derivative_digest(
            owner_id,
            self._capture.reconcile_and_process(
                owner_id, source_id, expected_row_version
            ),
        )

    def open_media(
        self, owner_id: str, source_id: str, media_kind: str
    ) -> Mapping[str, Any] | None:
        if media_kind != "preview":
            raise ResumeMediaError("invalid-request")
        return self._capture.open_media(owner_id, source_id, media_kind)

    def _with_derivative_digest(
        self, owner_id: str, row: Any
    ) -> Mapping[str, Any] | None:
        if not row:
            return row
        state = str(row.get("state") or "").strip().lower()
        if state not in self.READY_SOURCE_STATES:
            return row
        if row.get("derivative_sha256_digest") and row.get("derivative_byte_length"):
            return row
        source_id = str(row.get("source_key") or row.get("source_id") or "")
        if not source_id:
            return row
        opened = self._capture.open_media(owner_id, source_id, "preview")
        if not opened:
            return row
        stream = opened.get("stream")
        if stream is not None and hasattr(stream, "read"):
            data = bytes(stream.read())
        else:
            data = bytes(opened.get("data") or b"")
        if not data:
            return row
        prepared = dict(row)
        prepared["derivative_sha256_digest"] = hashlib.sha256(data).hexdigest()
        prepared["derivative_byte_length"] = len(data)
        prepared["derivative_content_type"] = str(
            opened.get("content_type") or row.get("derivative_content_type") or ""
        )
        return prepared


class ResumeMediaApplicationService:
    """Route-facing use cases for the scoped private Resume media chooser."""

    def __init__(
        self,
        *,
        media: ResumeMediaService,
        persistence_label: str = "unconfigured",
        catalog_label: str = "unavailable",
    ) -> None:
        if media is None:
            raise ResumeMediaApplicationUnavailable("media-unavailable")
        self._media = media
        self.persistence_label = str(persistence_label)
        self.catalog_label = str(catalog_label)

    @property
    def publishes(self) -> bool:
        return False

    @property
    def media_repository(self) -> Any:
        """The media repository this application commands (wiring/diagnostic)."""

        return getattr(self._media, "repository", None)

    # -- read use cases ----------------------------------------------------

    def capabilities(self) -> dict[str, Any]:
        return {
            "commands": ["add_media", "keep_words_only", "review_media"],
            "slots": list(PLACEMENT_SLOTS),
            "portrait_is_identity_presentation": IDENTITY_PRESENTATION_PORTRAIT,
            "publishes": False,
            "review_publishes": False,
            "persistence": self.persistence_label,
            "persistence_is_live_database": False,
            "schema_applied": False,
            "catalog": self.catalog_label,
            "library_page_size": CATALOG_PAGE_SIZE_DEFAULT,
            "library_page_size_limit": min(
                CATALOG_PAGE_SIZE_LIMIT, MAX_CATALOG_PAGE_SIZE
            ),
        }

    def versions(self, *, owner_id: str) -> dict[str, int]:
        return self._media.media_versions(owner_id=owner_id)

    def workspace(self, *, owner_id: str) -> dict[str, Any]:
        draft = self._media.draft_media_view(owner_id=owner_id)
        staged = self._media.staged_placement_view(owner_id=owner_id)
        return {
            "draft_version": draft["draft_version"],
            "slots": draft["slots"],
            "staged": staged,
            "photos": list(self._media.owner_photo_view(owner_id=owner_id)),
            "capabilities": self.capabilities(),
        }

    def library(
        self,
        *,
        owner_id: str,
        query: Any = None,
        category: Any = None,
        tags: Any = (),
        limit: int = CATALOG_PAGE_SIZE_DEFAULT,
        cursor: Any = None,
    ) -> dict[str, Any]:
        page = self._media.list_library(
            query=query, category=category, tags=tags, limit=limit, cursor=cursor
        )
        page["catalog"] = self.catalog_label
        page["page_size"] = min(int(limit), MAX_CATALOG_PAGE_SIZE)
        return page

    def photo_state(self, *, owner_id: str) -> list[dict[str, Any]]:
        return list(self._media.owner_photo_view(owner_id=owner_id))

    # -- photo lifecycle ---------------------------------------------------

    def upload_photo(self, *, owner_id: str, upload: Any) -> dict[str, Any]:
        record = self._media.ingest_private_photo(owner_id=owner_id, upload=upload)
        return {
            "source_id": record["source_id"],
            "state": record["state"],
            "retryable": record["state"] not in TERMINAL_READINESS_STATES,
        }

    def refresh_photo(self, *, owner_id: str, source_id: str) -> dict[str, Any]:
        return self._media.refresh_private_photo(
            owner_id=owner_id, source_id=source_id
        )

    def open_photo_preview(self, *, owner_id: str, source_id: str) -> Any:
        return self._media.open_private_photo_preview(
            owner_id=owner_id, source_id=source_id
        )

    def open_library_thumbnail(
        self, *, owner_id: str, asset_id: str, asset_version: Any, slot: Any
    ) -> Any:
        return self._media.open_library_thumbnail(
            owner_id=owner_id,
            asset_id=asset_id,
            asset_version=asset_version,
            slot=slot,
        )

    # -- selection, preview and explicit Add --------------------------------

    def stage_placement(self, *, owner_id: str, payload: Any) -> dict[str, Any]:
        body = _authority_free(payload)
        return self._media.stage_placement(
            owner_id=owner_id,
            slot=body.get("slot"),
            source=body.get("source"),
            crop=body.get("crop"),
            alt_text=body.get("alt_text"),
            decorative=body.get("decorative"),
            caption=body.get("caption"),
        )

    def preview_placement(self, *, owner_id: str, slot: Any) -> dict[str, Any] | None:
        return self._media.preview_placement(owner_id=owner_id, slot=slot)

    def clear_placement(self, *, owner_id: str, slot: Any) -> bool:
        return self._media.clear_staged_placement(owner_id=owner_id, slot=slot)

    def swap_placements(self, *, owner_id: str) -> dict[str, Any]:
        return self._media.swap_staged_placements(owner_id=owner_id)

    def add_media(self, *, owner_id: str, payload: Any) -> dict[str, Any]:
        body = _authority_free(payload)
        return self._media.add_media_choices(
            owner_id=owner_id,
            request_uuid=_request_uuid(body),
            expected_draft_version=body.get("expected_draft_version"),
            choices=body.get("choices"),
        )

    def keep_words_only(self, *, owner_id: str, payload: Any) -> dict[str, Any]:
        body = _authority_free(payload)
        publication = getattr(self, "publication_service", None)
        if publication is not None:
            from services.resume_publication_repository import PublicationStoreUnavailable
            from services.resume_publication_service import PublicationUnavailableError

            try:
                snapshot = publication.repository.load_owner(str(owner_id))
            except (PublicationStoreUnavailable, PublicationUnavailableError) as error:
                raise ResumeMediaError("publication-unavailable") from error
            if not isinstance(snapshot, dict):
                raise ResumeMediaError("publication-unavailable")
            revision = snapshot.get("current_revision")
            sharing = bool(snapshot.get("sharing_enabled"))
            publications = snapshot.get("publications") or {}
            current = publications.get(revision)
            slot = body.get("slot")
            if sharing and revision is not None:
                if not isinstance(current, dict) or "media" not in current:
                    raise ResumeMediaError("publication-unavailable")
                media = current.get("media") or {}
                names = [slot] if slot else list(media)
                for name in names:
                    item = media.get(name)
                    if isinstance(item, dict) and item.get("active"):
                        raise ResumeMediaError("publication-restrict-required")
        return self._media.keep_words_only(
            owner_id=owner_id,
            request_uuid=_request_uuid(body),
            expected_draft_version=body.get("expected_draft_version"),
        )

    def review(self, *, owner_id: str, payload: Any) -> dict[str, Any]:
        body = _authority_free(payload)
        return self._media.review_draft(
            owner_id=owner_id,
            expected_draft_version=body.get("expected_draft_version"),
            expected_publication_version=body.get("expected_publication_version"),
        )

    def open_placement_media(self, *, owner_id: str, slot: Any) -> Any:
        return self._media.open_placement_media(
            owner_id=owner_id, slot=slot, scope="owner_preview"
        )

    def open_draft_placement_media(self, *, owner_id: str, slot: Any) -> Any:
        """Bytes for the placement already saved in this owner's private draft.

        Distinct from the staged preview read: this serves the persisted draft
        placement after an explicit Add and after a reload, with the same
        authorize-before-read and revalidate-after-read checks.
        """

        return self._media.open_placement_media(
            owner_id=owner_id, slot=slot, scope="owner_draft"
        )


def build_resume_media_application(
    *,
    draft_store: Any,
    sources: Any,
    storage: Any = None,
    photo_readiness: Any = None,
    persistence_label: str = "unknown",
    catalog_label: str = "synthetic_test_catalog",
    lock: Any = None,
    publication_service: Any = None,
) -> ResumeMediaApplicationService:
    """Explicitly wire the media application. Never an implicit test fallback."""

    if draft_store is None or sources is None:
        raise ResumeMediaApplicationUnavailable("media-unavailable")
    repository = ResumeDraftBoundMediaRepository(
        draft_store=draft_store, sources=sources, lock=lock
    )
    media = ResumeMediaService(
        repository=repository, storage=storage, photo_readiness=photo_readiness
    )
    application = ResumeMediaApplicationService(
        media=media,
        persistence_label=persistence_label,
        catalog_label=catalog_label,
    )
    application.publication_service = publication_service
    return application


def configured_resume_media_application(config_value: Any) -> ResumeMediaApplicationService:
    """Return the configured application or refuse to serve.

    Missing or malformed production configuration is a truthful unavailable
    state. It never falls back to an in-memory fixture catalog or reports a
    durable save.
    """

    if not isinstance(config_value, ResumeMediaApplicationService):
        raise ResumeMediaApplicationUnavailable("media-unavailable")
    return config_value


def recheck_catalog_for_publication(catalog, asset_id: str, version: int, digest: str):
    """Publication readers recheck the durable catalog before returning bytes."""

    if catalog is None:
        raise ResumeMediaApplicationUnavailable("media-unavailable")
    record = catalog.get_active(str(asset_id), int(version))
    if record.digest != str(digest) or record.lifecycle != "active":
        raise ResumeMediaApplicationUnavailable("media-unavailable")
    return record
