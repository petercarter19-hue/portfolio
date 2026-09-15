"""Behavior tests for the dark Resume media placement service.

Evidence level: local unit/contract with synthetic injected collaborators
(repository double, storage double, Photo Capture-shaped readiness double).
These tests prove the service contract - readiness gating, crop/slot rules,
owner isolation, idempotent private Add, review/publication, and
authorize-read-recheck media delivery. They do not prove SQL, real storage,
real malware scanning, live identity, or deployment behavior.
"""

import io
import json
import threading
import unittest
from dataclasses import replace

from services.resume_media_repository import (
    CATALOG_PAGE_SIZE_LIMIT,
    COMMAND_ADD_MEDIA,
    COMMAND_KEEP_WORDS_ONLY,
    COMMAND_PUBLISH,
    PLACEMENT_SLOTS,
    SLOT_EXPERIENCE_SUPPORT,
    SLOT_STORY_BANNER,
    CropRect,
    DraftMediaRecord,
    InMemoryMediaStorage,
    InMemoryResumeMediaRepository,
    MediaPlacement,
    PublicationRecord,
    RequestReceipt,
    canonical_json,
    sha256_hex,
)
from services.resume_media_service import (
    MAX_CATALOG_PAGE_SIZE,
    ResumeMediaConflict,
    ResumeMediaDenied,
    ResumeMediaError,
    ResumeMediaService,
    ResumePhotoReadinessAdapter,
    _review_payload,
    review_digest,
    resolve_placement_slot,
    validate_crop,
)


OWNER_A = "owner-aaaa1111"
OWNER_B = "owner-bbbb2222"
PRIVATE_FILENAME = "PRIVATE-MEMBER-FILENAME.jpg"
PHOTO_ALT_TEXT = "Member photo described for assistive technology"
ART_ALT_TEXT = "Illustrated scene described for assistive technology"

# Crops already shaped for each slot's bounded presentation aspect.
PHOTO_BANNER_CROP = {"x": 0.1, "y": 0.15, "width": 0.75, "height": 0.7}
PHOTO_EXPERIENCE_CROP = {"x": 0.3, "y": 0.1, "width": 0.4286, "height": 0.8}
ART_BANNER_CROP = {"x": 0.05, "y": 0.2, "width": 0.84375, "height": 0.5}
ART_EXPERIENCE_CROP = {"x": 0.2, "y": 0.2, "width": 0.50625, "height": 0.6}

# SQL rowversion values above JavaScript's exact-integer range must cross the
# browser boundary as canonical decimal text.
LARGE_PHOTO_VERSION = 289_360_691_352_306_692


class FakeCaptureError(RuntimeError):
    def __init__(self, code):
        self.code = str(code)
        super().__init__(self.code)


class FakePhotoCapture:
    """Synthetic Photo Capture double: upload -> scanning -> process -> ready.

    It mirrors the owner-scoped Photo Capture source surface the Resume adapter
    consumes. ``confirm_capture`` exists only to fail loudly if the Resume path
    ever calls the canonical Capture operation.
    """

    def __init__(self):
        self.calls = []
        self.sources = {}
        self.media = {}
        self.plans = {}
        self.dimensions = (1400, 500)
        self.raise_on_create = None
        self.on_open = None
        self.on_reconcile = None
        self.reconcile_result = None
        self.confirm_attempts = 0
        self._counter = 0

    def _row(self, owner_id, source_id):
        return self.sources[(owner_id, source_id)]

    def _bump(self, row):
        row["row_version"] = "%016x" % (int(row["row_version"], 16) + 1)

    def create_source(self, owner_id, upload):
        self.calls.append("create_source")
        if self.raise_on_create is not None:
            raise FakeCaptureError(self.raise_on_create)
        self._counter += 1
        source_id = "source-%04d" % self._counter
        self.sources[(owner_id, source_id)] = {
            "source_key": source_id,
            "state": "scanning",
            "row_version": "%016x" % 1,
            "derivative_blob_name": "photo/v1/aa/%s-preview.jpg" % source_id,
        }
        return dict(self._row(owner_id, source_id))

    def get_source(self, owner_id, source_key):
        self.calls.append("get_source")
        row = self.sources.get((owner_id, source_key))
        return dict(row) if row else None

    def reconcile_and_process(self, owner_id, source_key, expected_row_version):
        self.calls.append("reconcile_and_process")
        row = self.sources.get((owner_id, source_key))
        if row is None or str(expected_row_version) != str(row["row_version"]):
            raise FakeCaptureError("changed")
        if self.reconcile_result is not None:
            substituted = self.reconcile_result(owner_id, source_key)
            if substituted is not None:
                return dict(substituted)
        if self.on_reconcile is not None:
            self.on_reconcile(owner_id, source_key)
        plan = self.plans.get(source_key) or []
        state = plan.pop(0) if plan else "needs_review"
        row["state"] = state
        if state == "needs_review":
            payload = ("PRIVATE-IMAGE-%s" % source_key).encode("utf-8")
            self.media[(owner_id, source_key)] = payload
            width, height = self.dimensions
            row.update(
                {
                    "derivative_sha256_digest": sha256_hex(payload),
                    "pixel_width": width,
                    "pixel_height": height,
                    "derivative_content_type": "image/jpeg",
                    "derivative_byte_length": len(payload),
                }
            )
        elif state in ("rejected", "quarantined"):
            row["safe_error_code"] = "scan_error"
        self._bump(row)
        return dict(row)

    def open_media(self, owner_id, source_key, media_kind):
        self.calls.append("open_media")
        if self.on_open is not None:
            self.on_open(owner_id, source_key)
        payload = self.media.get((owner_id, source_key))
        if payload is None:
            return None
        return {
            "stream": io.BytesIO(payload),
            "content_type": "image/jpeg",
            "byte_length": len(payload),
        }

    def confirm_capture(self, *args, **kwargs):  # pragma: no cover - guard
        self.confirm_attempts += 1
        raise AssertionError("Resume media must never confirm a Capture")

    def finish_capture_deletion(self, *args, **kwargs):  # pragma: no cover
        self.confirm_attempts += 1
        raise AssertionError("Resume media must never finalize a Capture deletion")


class ResumeMediaServiceTest(unittest.TestCase):
    """Shared synthetic harness for the Resume media service contract."""

    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        self.storage = InMemoryMediaStorage()
        self.capture = FakePhotoCapture()
        self.readiness = ResumePhotoReadinessAdapter(self.capture)
        self.service = ResumeMediaService(
            repository=self.repository,
            storage=self.storage,
            photo_readiness=self.readiness,
        )

    # -- fixtures ----------------------------------------------------------

    def ingest_photo(self, owner_id=OWNER_A, *, plan=None, dimensions=None):
        if dimensions is not None:
            self.capture.dimensions = dimensions
        ingest = self.service.ingest_private_photo(
            owner_id=owner_id,
            upload={"data": b"\xff\xd8\xffsynthetic", "filename": PRIVATE_FILENAME},
        )
        if plan is not None:
            self.capture.plans[ingest["source_id"]] = list(plan)
        return ingest["source_id"]

    def ready_photo(self, owner_id=OWNER_A, **kwargs):
        source_id = self.ingest_photo(owner_id=owner_id, **kwargs)
        state = self.service.refresh_private_photo(
            owner_id=owner_id, source_id=source_id
        )
        self.assertEqual(state["state"], "ready")
        return self.repository.get_owner_photo(owner_id, source_id)

    def photo_source(self, record):
        source = {"kind": "owner_photo", "source_id": record.source_id}
        if record.version:
            source["expected_version"] = record.version
        if record.digest:
            source["expected_digest"] = record.digest
        return source

    def seed_large_photo(self, version=LARGE_PHOTO_VERSION):
        return self.repository.seed_owner_photo(
            owner_id=OWNER_A,
            source_id="source-large-version",
            state="ready",
            digest=sha256_hex(b"synthetic-large-version-photo"),
            width=1400,
            height=500,
            derivative_ref="photo/v1/source-large-version-preview.jpg",
            version=version,
            version_token="%016x" % version,
        )

    def art_asset(self, asset_id="art-1", *, label="Quiet Forest", category="Nature",
                  tags=("forest",), width=1600, height=900, version=1,
                  lifecycle="active", provenance=None, rights=None):
        banner_payload = ("ART-BANNER-%s" % asset_id).encode("utf-8")
        experience_payload = ("ART-EXPERIENCE-%s" % asset_id).encode("utf-8")
        banner_ref = "catalog/%s/v%d/story_banner.png" % (asset_id, version)
        experience_ref = "catalog/%s/v%d/experience_support.png" % (asset_id, version)
        self.storage.put(banner_ref, banner_payload, content_type="image/png")
        self.storage.put(experience_ref, experience_payload, content_type="image/png")
        digest = sha256_hex(canonical_json({"asset": asset_id, "version": version}))
        return self.repository.seed_catalog_asset(
            asset_id=asset_id,
            version=version,
            label=label,
            category=category,
            tags=tags,
            width=width,
            height=height,
            digest=digest,
            lifecycle=lifecycle,
            provenance=provenance or {"model": "synthetic-art-v1"},
            rights=rights or {"rights_id": "synthetic-rights", "approval_state": "approved"},
            derivatives=(
                {
                    "slot": SLOT_STORY_BANNER,
                    "ref": banner_ref,
                    "digest": self.storage.digest_for(banner_ref),
                    "content_type": "image/png",
                    "byte_length": len(banner_payload),
                },
                {
                    "slot": SLOT_EXPERIENCE_SUPPORT,
                    "ref": experience_ref,
                    "digest": self.storage.digest_for(experience_ref),
                    "content_type": "image/png",
                    "byte_length": len(experience_payload),
                },
            ),
        )

    def art_source(self, record):
        return {
            "kind": "generated_illustration",
            "asset_id": record.asset_id,
            "asset_version": record.version,
            "expected_digest": record.digest,
        }

    def stage_photo(self, slot, crop, owner_id=OWNER_A, record=None, *,
                    alt_text=PHOTO_ALT_TEXT, decorative=False, caption=None):
        record = record or self.ready_photo(owner_id=owner_id)
        return self.service.stage_placement(
            owner_id=owner_id,
            slot=slot,
            source=self.photo_source(record),
            crop=crop,
            alt_text=alt_text,
            decorative=decorative,
            caption=caption,
        )

    def photo_choice(self, record, slot, crop, *, alt_text=PHOTO_ALT_TEXT,
                     decorative=False, caption=None):
        return {
            "slot": slot,
            "source": self.photo_source(record),
            "crop": crop,
            "alt_text": alt_text,
            "decorative": decorative,
            "caption": caption,
        }

    def art_choice(self, record, slot, crop, *, alt_text=ART_ALT_TEXT,
                   decorative=True, caption=None):
        return {
            "slot": slot,
            "source": self.art_source(record),
            "crop": crop,
            "alt_text": alt_text,
            "decorative": decorative,
            "caption": caption,
        }


class PhotoReadinessTests(ResumeMediaServiceTest):
    def test_upload_then_processing_reaches_ready_without_confirm(self):
        ingest = self.service.ingest_private_photo(
            owner_id=OWNER_A, upload={"data": b"\xff\xd8\xff" + b"x" * 8}
        )
        self.assertEqual(ingest["state"], "scanning")
        self.assertNotIn("derivative_blob_name", ingest)
        refreshed = self.service.refresh_private_photo(
            owner_id=OWNER_A, source_id=ingest["source_id"]
        )
        self.assertEqual(refreshed["state"], "ready")
        self.assertTrue(refreshed["retryable"])
        stored = self.repository.get_owner_photo(OWNER_A, ingest["source_id"])
        # Placement versions retain the exact authoritative Photo Capture
        # rowversion; they are not a process-local refresh counter.
        self.assertEqual(stored.version, 2)
        again = self.service.refresh_private_photo(
            owner_id=OWNER_A, source_id=ingest["source_id"]
        )
        self.assertEqual(again["state"], "ready")
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, ingest["source_id"]).version, 3
        )
        self.assertEqual(self.capture.confirm_attempts, 0)

    def test_failed_source_can_retry_until_ready(self):
        source_id = self.ingest_photo(plan=["failed", "needs_review"])
        failed = self.service.refresh_private_photo(
            owner_id=OWNER_A, source_id=source_id
        )
        self.assertEqual(failed["state"], "failed")
        self.assertTrue(failed["retryable"])
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.stage_photo(
                SLOT_STORY_BANNER,
                PHOTO_BANNER_CROP,
                record=self.repository.get_owner_photo(OWNER_A, source_id),
            )
        self.assertEqual(caught.exception.code, "source-failed")
        recovered = self.service.refresh_private_photo(
            owner_id=OWNER_A, source_id=source_id
        )
        self.assertEqual(recovered["state"], "ready")
        preview = self.stage_photo(
            SLOT_STORY_BANNER,
            PHOTO_BANNER_CROP,
            record=self.repository.get_owner_photo(OWNER_A, source_id),
        )
        self.assertEqual(preview["slot"], SLOT_STORY_BANNER)

    def test_rejected_and_quarantined_sources_never_become_ready(self):
        for terminal in ("rejected", "quarantined"):
            with self.subTest(state=terminal):
                source_id = self.ingest_photo(plan=[terminal])
                result = self.service.refresh_private_photo(
                    owner_id=OWNER_A, source_id=source_id
                )
                self.assertEqual(result["state"], terminal)
                self.assertFalse(result["retryable"])
                calls_before = len(self.capture.calls)
                again = self.service.refresh_private_photo(
                    owner_id=OWNER_A, source_id=source_id
                )
                self.assertEqual(again["state"], terminal)
                self.assertEqual(len(self.capture.calls), calls_before)
                with self.assertRaises(ResumeMediaConflict) as caught:
                    self.stage_photo(
                        SLOT_STORY_BANNER,
                        PHOTO_BANNER_CROP,
                        record=self.repository.get_owner_photo(OWNER_A, source_id),
                    )
                self.assertEqual(caught.exception.code, "source-rejected")

    def test_not_ready_source_cannot_be_staged(self):
        source_id = self.ingest_photo()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source={"kind": "owner_photo", "source_id": source_id},
                crop=PHOTO_BANNER_CROP,
            )
        self.assertEqual(caught.exception.code, "source-not-ready")

    def test_resume_adapter_never_calls_photo_capture_confirm(self):
        self.assertFalse(hasattr(self.readiness, "confirm_capture"))
        for name in ResumePhotoReadinessAdapter.FORBIDDEN_METHODS:
            self.assertNotIn(name, dir(self.readiness))
        record = self.ready_photo()
        self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        opened = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="owner_preview"
        )
        self.assertIsNotNone(opened)
        self.assertEqual(self.capture.confirm_attempts, 0)
        self.assertEqual(
            sorted(set(self.capture.calls)),
            ["create_source", "get_source", "open_media", "reconcile_and_process"],
        )
        # The authoritative readiness recheck happens after the byte read.
        self.assertLess(
            self.capture.calls.index("open_media"),
            len(self.capture.calls) - 1 - self.capture.calls[::-1].index("get_source"),
        )

    def test_upload_guards_surface_stable_codes(self):
        for raw, expected in (
            ("unsupported", "unsupported-source"),
            ("too-large", "source-too-large"),
            ("dimensions", "source-dimensions"),
            ("unexpected-provider-detail", "upload-failed"),
        ):
            with self.subTest(raw=raw):
                self.capture.raise_on_create = raw
                with self.assertRaises(ResumeMediaError) as caught:
                    self.service.ingest_private_photo(
                        owner_id=OWNER_A, upload={"data": b"x"}
                    )
                self.assertEqual(caught.exception.code, expected)
        self.capture.raise_on_create = None

    def test_unmapped_or_malicious_source_state_is_refused(self):
        for raw_state in ("provider-internal", "malicious"):
            with self.subTest(raw_state=raw_state):
                source_id = self.ingest_photo(plan=[raw_state])
                with self.assertRaises(ResumeMediaError) as caught:
                    self.service.refresh_private_photo(
                        owner_id=OWNER_A, source_id=source_id
                    )
                self.assertEqual(caught.exception.code, "source-unavailable")


class SlotModelTests(ResumeMediaServiceTest):
    def test_only_two_decorative_slots_exist(self):
        self.assertEqual(PLACEMENT_SLOTS, ("story_banner", "experience_support"))

    def test_portrait_is_identity_presentation_not_a_placement_slot(self):
        with self.assertRaises(ResumeMediaConflict) as caught:
            resolve_placement_slot("portrait")
        self.assertEqual(caught.exception.code, "slot-not-allowed")
        with self.assertRaises(ResumeMediaError) as caught:
            resolve_placement_slot("hero_banner")
        self.assertEqual(caught.exception.code, "invalid-slot")
        with self.assertRaises(ResumeMediaError):
            resolve_placement_slot(None)
        record = self.ready_photo()
        with self.assertRaises(ResumeMediaConflict):
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot="portrait",
                source=self.photo_source(record),
                crop=PHOTO_BANNER_CROP,
            )


class CatalogServiceTests(ResumeMediaServiceTest):
    def test_zero_results_are_honest(self):
        page = self.service.list_library(query="nothing here")
        self.assertEqual(page["items"], [])
        self.assertIsNone(page["next_cursor"])
        self.assertEqual(page["total"], 0)

    def test_search_and_pagination_are_bounded_and_complete(self):
        for index in range(5):
            self.art_asset(
                asset_id="art-%02d" % index,
                label="page leaf %02d" % index,
                category="Nature",
                tags=("leaf",),
            )
        seen, cursor, pages = [], None, 0
        while True:
            page = self.service.list_library(query="  LEAF ", limit=2, cursor=cursor)
            self.assertLessEqual(len(page["items"]), 2)
            self.assertEqual(page["total"], 5)
            seen.extend(item["asset_id"] for item in page["items"])
            pages += 1
            cursor = page["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(len(seen), 5)
        self.assertEqual(sorted(seen), sorted(set(seen)))
        self.assertEqual(pages, 3)
        clamped = self.service.list_library(query="leaf", limit=1000)
        self.assertLessEqual(len(clamped["items"]), MAX_CATALOG_PAGE_SIZE)
        self.assertEqual(MAX_CATALOG_PAGE_SIZE, CATALOG_PAGE_SIZE_LIMIT)

    def test_cursor_reused_with_different_query_conflicts(self):
        for index in range(3):
            self.art_asset(asset_id="art-%02d" % index, label="alpha %02d" % index)
        cursor = self.service.list_library(query="alpha", limit=1)["next_cursor"]
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.list_library(query="different", limit=1, cursor=cursor)
        self.assertEqual(caught.exception.code, "cursor-mismatch")

    def test_invalid_limit_and_malformed_cursor_are_refused(self):
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.list_library(limit=0)
        self.assertEqual(caught.exception.code, "invalid-limit")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.list_library(limit=4, cursor="!!!not-a-cursor")
        self.assertEqual(caught.exception.code, "invalid-cursor")

    def test_catalog_item_exposes_no_private_locator_or_digest(self):
        self.art_asset()
        item = self.service.list_library()["items"][0]
        self.assertEqual(
            set(item),
            {
                "asset_id",
                "asset_version",
                "label",
                "category",
                "tags",
                "origin",
                "orientation",
                "width",
                "height",
                "provenance",
                "rights",
            },
        )
        self.assertNotIn("catalog/", canonical_json(item))
        self.assertNotIn("png", canonical_json(item))


class CropAndPreviewTests(ResumeMediaServiceTest):
    def test_crop_validation_matrix(self):
        cases = (
            ({"x": 0.1, "y": 0.1, "width": float("nan"), "height": 0.5},
             "crop-not-finite"),
            ({"x": 0.1, "y": 0.1, "width": float("inf"), "height": 0.5},
             "crop-not-finite"),
            ({"x": 0.1, "y": 0.1, "width": 0.5, "height": float("-inf")},
             "crop-not-finite"),
            ({"x": 0.1, "y": 0.1, "width": -0.5, "height": 0.5},
             "invalid-crop"),
            ({"x": 0.1, "y": 0.1, "width": 0.0, "height": 0.5},
             "invalid-crop"),
            ({"x": 0.6, "y": 0.1, "width": 0.6, "height": 0.7},
             "crop-out-of-bounds"),
            ({"x": -0.2, "y": 0.1, "width": 0.5, "height": 0.5},
             "crop-out-of-bounds"),
            ({"x": 0.1, "y": 0.7, "width": 0.5, "height": 0.5},
             "crop-out-of-bounds"),
            ({"x": "0.1", "y": 0.1, "width": 0.5, "height": 0.5},
             "invalid-crop"),
            ({"x": True, "y": 0.1, "width": 0.5, "height": 0.5},
             "invalid-crop"),
            ({"y": 0.1, "width": 0.5, "height": 0.5}, "invalid-crop"),
            ({"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5, "zoom": 1.2},
             "invalid-crop"),
            ({"x": 0.1, "y": 0.1, "width": 0.02, "height": 0.02},
             "invalid-crop"),
            ("not-a-crop", "invalid-crop"),
        )
        for crop, expected in cases:
            with self.subTest(crop=crop):
                with self.assertRaises(ResumeMediaError) as caught:
                    validate_crop(
                        crop, slot=SLOT_STORY_BANNER, width=1400, height=500
                    )
                self.assertEqual(caught.exception.code, expected)

    def test_valid_crop_is_normalized_and_rounded(self):
        crop = validate_crop(
            {"x": 0.0, "y": 0.0, "width": 0.75, "height": 0.7},
            slot=SLOT_STORY_BANNER,
            width=1400,
            height=500,
        )
        self.assertEqual(crop.as_dict(),
                         {"x": 0.0, "y": 0.0, "width": 0.75, "height": 0.7})
        photo = validate_crop(
            {"x": 0, "y": 0, "width": 1, "height": 1},
            slot=SLOT_EXPERIENCE_SUPPORT,
            width=150,
            height=100,
        )
        self.assertEqual(photo.width, 1.0)

    def test_preview_payload_exposes_only_safe_presentation_metadata(self):
        record = self.ready_photo()
        preview = self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        self.assertEqual(
            set(preview),
            {
                "slot",
                "source_kind",
                # PS-MVP1-MEDIA-INTEGRATION-001: the owner may name the exact
                # reviewed source again when a slot is adjusted, so the stable
                # asset identity is part of the safe preview. The raw digest,
                # storage key and provider locator stay private (asserted below).
                "asset_id",
                "asset_version",
                "decorative",
                "biographical_evidence",
                "orientation",
                "width",
                "height",
                "crop",
                "alt_text",
                "caption",
                "provenance_label",
                "presentation_version",
            },
        )
        self.assertFalse(preview["decorative"])
        self.assertFalse(preview["biographical_evidence"])
        self.assertEqual(preview["orientation"], "landscape")
        self.assertEqual(preview["alt_text"], PHOTO_ALT_TEXT)
        self.assertIsNone(preview["caption"])
        self.assertEqual(preview["provenance_label"], "Member photo")
        self.assertEqual(preview["presentation_version"], 1)
        serialized = canonical_json(preview)
        for forbidden in (
            PRIVATE_FILENAME,
            "photo/v1/",
            record.digest,
            OWNER_A,
            "scan",
            "exif",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_large_owner_photo_version_is_canonical_text_in_saved_and_review(self):
        record = self.seed_large_photo()
        preview = self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        self.assertEqual(preview["asset_version"], str(LARGE_PHOTO_VERSION))

        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-large-version",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)
            ],
        )
        # Persistence keeps the exact Python/SQL integer; only browser-facing
        # projections serialize it as canonical decimal text.
        stored_placement = self.repository.get_draft(OWNER_A).placement_for(
            SLOT_STORY_BANNER
        )
        self.assertIsNotNone(stored_placement)
        self.assertEqual(stored_placement.asset_version, LARGE_PHOTO_VERSION)

        saved = self.service.draft_media_view(owner_id=OWNER_A)
        self.assertEqual(
            saved["slots"][SLOT_STORY_BANNER]["asset_version"],
            str(LARGE_PHOTO_VERSION),
        )
        review = self.service.review_draft(
            owner_id=OWNER_A,
            expected_draft_version=saved["draft_version"],
            expected_publication_version=0,
        )
        self.assertEqual(
            review["slots"][SLOT_STORY_BANNER]["asset_version"],
            str(LARGE_PHOTO_VERSION),
        )

        for view in (preview, saved, review):
            transported = json.loads(canonical_json(view))
            if "slots" in transported:
                value = transported["slots"][SLOT_STORY_BANNER]["asset_version"]
            else:
                value = transported["asset_version"]
            self.assertIsInstance(value, str)
            self.assertEqual(int(value), LARGE_PHOTO_VERSION)

    def test_source_version_validation_keeps_canonical_text_and_rejects_unsafe(self):
        maximum = 0x7FFF_FFFF_FFFF_FFFF
        record = self.art_asset(asset_id="art-max", version=maximum)
        preview = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_STORY_BANNER,
            source={
                "kind": "generated_illustration",
                "asset_id": record.asset_id,
                "asset_version": str(maximum),
            },
            crop=ART_BANNER_CROP,
            alt_text=ART_ALT_TEXT,
            decorative=True,
        )
        # The canonical text normalizes to the exact bigint and comes back out
        # as text because it is above the JavaScript safe-integer range.
        self.assertEqual(preview["asset_version"], str(maximum))

        for value in ("01", "+1", "1.0", "not-a-number", True, 1.5, 2**63, -1):
            with self.assertRaises(ResumeMediaError) as caught:
                self.service.stage_placement(
                    owner_id=OWNER_A,
                    slot=SLOT_STORY_BANNER,
                    source={
                        "kind": "generated_illustration",
                        "asset_id": record.asset_id,
                        "asset_version": value,
                    },
                    crop=ART_BANNER_CROP,
                    alt_text=ART_ALT_TEXT,
                    decorative=True,
                )
            self.assertEqual(caught.exception.code, "invalid-source")

    def test_crops_persist_separately_per_slot_for_one_asset(self):
        record = self.ready_photo()
        banner = self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        experience = self.stage_photo(
            SLOT_EXPERIENCE_SUPPORT, PHOTO_EXPERIENCE_CROP, record=record
        )
        self.assertEqual(banner["crop"], PHOTO_BANNER_CROP)
        self.assertEqual(experience["crop"], PHOTO_EXPERIENCE_CROP)
        self.assertNotEqual(banner["crop"], experience["crop"])
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP),
                self.photo_choice(
                    record, SLOT_EXPERIENCE_SUPPORT, PHOTO_EXPERIENCE_CROP
                ),
            ],
        )
        draft = self.repository.get_draft(OWNER_A)
        self.assertEqual(
            draft.placement_for(SLOT_STORY_BANNER).crop.as_dict(), PHOTO_BANNER_CROP
        )
        self.assertEqual(
            draft.placement_for(SLOT_EXPERIENCE_SUPPORT).crop.as_dict(),
            PHOTO_EXPERIENCE_CROP,
        )

    def test_slot_swap_requires_each_crop_to_validate(self):
        record = self.ready_photo()
        self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_EXPERIENCE_SUPPORT,
                source=self.photo_source(record),
                crop=PHOTO_BANNER_CROP,
            )
        self.assertEqual(caught.exception.code, "crop-slot-mismatch")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source=self.photo_source(record),
                crop=PHOTO_EXPERIENCE_CROP,
            )
        self.assertEqual(caught.exception.code, "crop-slot-mismatch")
        swapped = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_EXPERIENCE_SUPPORT,
            source=self.photo_source(record),
            crop=PHOTO_EXPERIENCE_CROP,
            alt_text=PHOTO_ALT_TEXT,
            decorative=False,
        )
        self.assertEqual(swapped["slot"], SLOT_EXPERIENCE_SUPPORT)

    def test_staging_is_owner_scoped_and_denies_foreign_sources(self):
        record = self.ready_photo(owner_id=OWNER_A)
        foreign = self.service.stage_placement
        with self.assertRaises(ResumeMediaDenied) as caught:
            foreign(
                owner_id=OWNER_B,
                slot=SLOT_STORY_BANNER,
                source=self.photo_source(record),
                crop=PHOTO_BANNER_CROP,
            )
        with self.assertRaises(ResumeMediaDenied) as unknown:
            foreign(
                owner_id=OWNER_B,
                slot=SLOT_STORY_BANNER,
                source={"kind": "owner_photo", "source_id": "does-not-exist"},
                crop=PHOTO_BANNER_CROP,
            )
        self.assertEqual(str(caught.exception), str(unknown.exception))
        self.assertEqual(str(caught.exception), "not-authorized")
        self.assertIsNone(
            self.service.preview_placement(owner_id=OWNER_B, slot=SLOT_STORY_BANNER)
        )
        self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        self.assertIsNone(
            self.service.preview_placement(owner_id=OWNER_B, slot=SLOT_STORY_BANNER)
        )
        self.assertIsNotNone(
            self.service.preview_placement(owner_id=OWNER_A, slot=SLOT_STORY_BANNER)
        )

    def test_forged_catalog_version_and_digest_conflict(self):
        asset = self.art_asset()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source={
                    "kind": "generated_illustration",
                    "asset_id": asset.asset_id,
                    "asset_version": 99,
                },
                crop=ART_BANNER_CROP,
            )
        self.assertEqual(caught.exception.code, "asset-unavailable")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source={
                    "kind": "generated_illustration",
                    "asset_id": asset.asset_id,
                    "asset_version": asset.version,
                    "expected_digest": "0" * 64,
                },
                crop=ART_BANNER_CROP,
            )
        self.assertEqual(caught.exception.code, "stale-digest")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source={
                    "kind": "owner_photo",
                    "source_id": self.ready_photo().source_id,
                    "expected_version": 7,
                },
                crop=PHOTO_BANNER_CROP,
            )
        self.assertEqual(caught.exception.code, "stale-version")


class PrivateAddTests(ResumeMediaServiceTest):
    def choices_for(self, record, *, slots=(SLOT_STORY_BANNER,)):
        crops = {
            SLOT_STORY_BANNER: PHOTO_BANNER_CROP,
            SLOT_EXPERIENCE_SUPPORT: PHOTO_EXPERIENCE_CROP,
        }
        return [
            self.photo_choice(record, slot, crops[slot])
            for slot in slots
        ]

    def test_add_is_idempotent_for_same_key_and_body(self):
        record = self.ready_photo()
        choices = self.choices_for(record)
        first = self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=choices,
        )
        second = self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=choices,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["draft_version"], 1)
        self.assertEqual(
            len([call for call in self.repository.mutation_log if call == "commit_draft"]),
            1,
        )

    def test_same_key_with_different_body_conflicts(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=self.choices_for(record),
        )
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=self.choices_for(record, slots=(SLOT_EXPERIENCE_SUPPORT,)),
            )
        self.assertEqual(caught.exception.code, "idempotency-conflict")
        self.assertEqual(self.repository.snapshot(), before)

    def test_add_failure_preserves_draft_and_publication(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=self.choices_for(record),
        )
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=self.service.review_draft(
                owner_id=OWNER_A,
                expected_draft_version=1,
                expected_publication_version=0,
            )["reviewed_digest"],
        )
        before = self.repository.snapshot()
        self.repository.inject_failure("commit_draft", step="after_draft")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-2",
                expected_draft_version=1,
                choices=self.choices_for(record, slots=(SLOT_EXPERIENCE_SUPPORT,)),
            )
        self.assertEqual(caught.exception.code, "injected-failure")
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 1)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 1)

    def test_add_stale_draft_conflicts_without_writing(self):
        record = self.ready_photo()
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=5,
                choices=self.choices_for(record),
            )
        self.assertEqual(caught.exception.code, "stale-draft")
        self.assertEqual(self.repository.snapshot(), before)

    def test_deleted_photo_and_withdrawn_art_conflict_without_partial_change(self):
        record = self.ready_photo()
        self.repository.update_owner_photo(
            owner_id=OWNER_A, source_id=record.source_id, state="ready",
            lifecycle="deleted",
        )
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=self.choices_for(record),
            )
        self.assertEqual(caught.exception.code, "source-deleted")
        self.assertEqual(self.repository.snapshot(), before)
        asset = self.art_asset()
        self.repository.set_catalog_lifecycle(
            asset_id=asset.asset_id, version=asset.version, lifecycle="withdrawn"
        )
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-2",
                expected_draft_version=0,
                choices=[
                    self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP)
                ],
            )
        self.assertEqual(caught.exception.code, "asset-withdrawn")
        self.assertEqual(self.repository.snapshot(), before)

    def test_cross_owner_add_is_denied_with_stable_message(self):
        record = self.ready_photo(owner_id=OWNER_A)
        with self.assertRaises(ResumeMediaDenied) as foreign:
            self.service.add_media_choices(
                owner_id=OWNER_B,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=self.choices_for(record),
            )
        with self.assertRaises(ResumeMediaDenied) as unknown:
            self.service.add_media_choices(
                owner_id=OWNER_B,
                request_uuid="add-2",
                expected_draft_version=0,
                choices=[
                    {
                        "slot": SLOT_STORY_BANNER,
                        "source": {"kind": "owner_photo", "source_id": "nope"},
                        "crop": PHOTO_BANNER_CROP,
                        "alt_text": PHOTO_ALT_TEXT,
                        "decorative": False,
                    }
                ],
            )
        self.assertEqual(str(foreign.exception), str(unknown.exception))
        self.assertEqual(self.repository.get_draft(OWNER_B).version, 0)

    def test_add_requires_a_non_empty_unique_slot_body(self):
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=[],
            )
        self.assertEqual(caught.exception.code, "required")
        record = self.ready_photo()
        duplicated = self.choices_for(record) * 2
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-2",
                expected_draft_version=0,
                choices=duplicated,
            )
        self.assertEqual(caught.exception.code, "invalid-request")

    def test_request_receipts_are_owner_scoped(self):
        record_a = self.ready_photo(owner_id=OWNER_A)
        record_b = self.ready_photo(owner_id=OWNER_B)
        first = self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="shared-request-key",
            expected_draft_version=0,
            choices=self.choices_for(record_a),
        )
        second = self.service.add_media_choices(
            owner_id=OWNER_B,
            request_uuid="shared-request-key",
            expected_draft_version=0,
            choices=self.choices_for(record_b),
        )
        self.assertEqual(first["draft_version"], 1)
        self.assertEqual(second["draft_version"], 1)
        self.assertNotEqual(
            self.repository.get_draft(OWNER_A).placement_for(
                SLOT_STORY_BANNER
            ).asset_id,
            self.repository.get_draft(OWNER_B).placement_for(
                SLOT_STORY_BANNER
            ).asset_id,
        )
        self.assertNotEqual(
            self.repository.get_receipt(
                owner_id=OWNER_A,
                command_type=COMMAND_ADD_MEDIA,
                request_uuid="shared-request-key",
            ).semantic_digest,
            self.repository.get_receipt(
                owner_id=OWNER_B,
                command_type=COMMAND_ADD_MEDIA,
                request_uuid="shared-request-key",
            ).semantic_digest,
        )

    def test_mixed_personal_and_library_selections_publish_together(self):
        record = self.ready_photo()
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_EXPERIENCE_SUPPORT, PHOTO_EXPERIENCE_CROP),
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP),
            ],
        )
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=digest,
        )
        current = self.service.current_publication(owner_id=OWNER_A)
        self.assertEqual(
            current["slots"][SLOT_EXPERIENCE_SUPPORT]["source_kind"], "owner_photo"
        )
        self.assertFalse(current["slots"][SLOT_EXPERIENCE_SUPPORT]["decorative"])
        self.assertEqual(
            current["slots"][SLOT_STORY_BANNER]["source_kind"],
            "generated_illustration",
        )
        self.assertTrue(current["slots"][SLOT_STORY_BANNER]["decorative"])
        photo_read = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_EXPERIENCE_SUPPORT, scope="published"
        )
        art_read = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
        )
        self.assertEqual(sha256_hex(photo_read["stream"].read()), record.digest)
        self.assertEqual(
            art_read["stream"].read(),
            ("ART-BANNER-%s" % asset.asset_id).encode("utf-8"),
        )

    def test_words_only_keeps_existing_published_media(self):
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP)
            ],
        )
        review = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=review["reviewed_digest"],
        )
        published_before = self.repository.snapshot()
        publication_before = self.repository.get_publication(OWNER_A)
        outcome = self.service.keep_words_only(
            owner_id=OWNER_A, request_uuid="words-1", expected_draft_version=1
        )
        self.assertEqual(outcome["command"], COMMAND_KEEP_WORDS_ONLY)
        self.assertEqual(outcome["draft_version"], 2)
        self.assertEqual(outcome["publication_version"], 1)
        self.assertEqual(
            self.repository.get_publication(OWNER_A).version, 1
        )
        self.assertNotEqual(published_before, self.repository.snapshot())
        self.assertEqual(self.repository.get_publication(OWNER_A), publication_before)
        read = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
        )
        self.assertIsNotNone(read)
        self.assertEqual(
            self.repository.get_draft(OWNER_A).placement_for(SLOT_STORY_BANNER)
            .asset_id,
            asset.asset_id,
        )
        replay = self.service.keep_words_only(
            owner_id=OWNER_A, request_uuid="words-1", expected_draft_version=1
        )
        self.assertEqual(replay, outcome)

    def test_removing_story_does_not_affect_experience_support(self):
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP),
                self.art_choice(asset, SLOT_EXPERIENCE_SUPPORT, ART_EXPERIENCE_CROP),
            ],
        )
        review = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=review["reviewed_digest"],
        )
        publication_before = self.repository.get_publication(OWNER_A)
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-2",
            expected_draft_version=1,
            choices=[{"slot": SLOT_STORY_BANNER, "source": None, "crop": None}],
        )
        draft = self.repository.get_draft(OWNER_A)
        self.assertIsNone(draft.placement_for(SLOT_STORY_BANNER))
        self.assertIsNotNone(draft.placement_for(SLOT_EXPERIENCE_SUPPORT))
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 1)
        self.assertEqual(self.repository.get_publication(OWNER_A), publication_before)
        review = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=2, expected_publication_version=1
        )
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-2",
            expected_draft_version=2,
            expected_publication_version=1,
            reviewed_digest=review["reviewed_digest"],
        )
        current = self.service.current_publication(owner_id=OWNER_A)
        self.assertIsNone(current["slots"][SLOT_STORY_BANNER])
        self.assertIsNotNone(current["slots"][SLOT_EXPERIENCE_SUPPORT])
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
            )
        )
        self.assertIsNotNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_EXPERIENCE_SUPPORT, scope="published"
            )
        )


class ReviewAndPublicationTests(ResumeMediaServiceTest):
    def publish_photo(self, record=None, slots=(SLOT_STORY_BANNER,), slug="1"):
        record = record or self.ready_photo()
        crops = {
            SLOT_STORY_BANNER: PHOTO_BANNER_CROP,
            SLOT_EXPERIENCE_SUPPORT: PHOTO_EXPERIENCE_CROP,
        }
        choices = [
            self.photo_choice(record, slot, crops[slot])
            for slot in slots
        ]
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-%s" % slug,
            expected_draft_version=self.repository.get_draft(OWNER_A).version,
            choices=choices,
        )
        draft_version = self.repository.get_draft(OWNER_A).version
        publication_version = self.repository.get_publication(OWNER_A).version
        review = self.service.review_draft(
            owner_id=OWNER_A,
            expected_draft_version=draft_version,
            expected_publication_version=publication_version,
        )
        outcome = self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-%s" % slug,
            expected_draft_version=draft_version,
            expected_publication_version=publication_version,
            reviewed_digest=review["reviewed_digest"],
        )
        return outcome, review

    def test_review_has_no_side_effects(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)
            ],
        )
        before = self.repository.snapshot()
        mutations = self.repository.mutation_log
        review = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )
        self.assertEqual(len(review["reviewed_digest"]), 64)
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.mutation_log, mutations)
        for command in (COMMAND_ADD_MEDIA, COMMAND_KEEP_WORDS_ONLY, COMMAND_PUBLISH):
            self.assertIsNone(
                self.repository.get_receipt(
                    owner_id=OWNER_A, command_type=command, request_uuid="review-1"
                )
            )
        self.assertIsNotNone(
            self.repository.get_receipt(
                owner_id=OWNER_A,
                command_type=COMMAND_ADD_MEDIA,
                request_uuid="add-1",
            )
        )
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 0)

    def test_review_digest_binds_versions_crops_and_assets(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)
            ],
        )
        first = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )
        shifted = dict(PHOTO_BANNER_CROP)
        shifted["x"] = 0.05
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-2",
            expected_draft_version=1,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, shifted)
            ],
        )
        second = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=2, expected_publication_version=0
        )
        self.assertNotEqual(first["reviewed_digest"], second["reviewed_digest"])
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.review_draft(
                owner_id=OWNER_A,
                expected_draft_version=2,
                expected_publication_version=9,
            )
        self.assertEqual(caught.exception.code, "stale-publication")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.review_draft(
                owner_id=OWNER_A,
                expected_draft_version=7,
                expected_publication_version=0,
            )
        self.assertEqual(caught.exception.code, "stale-draft")

    def test_publish_requires_the_matching_review_digest(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)
            ],
        )
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-1",
                expected_draft_version=1,
                expected_publication_version=0,
                reviewed_digest="f" * 64,
            )
        self.assertEqual(caught.exception.code, "review-mismatch")
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 0)

    def test_publish_stale_versions_conflict(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)
            ],
        )
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-1",
                expected_draft_version=3,
                expected_publication_version=0,
                reviewed_digest=digest,
            )
        self.assertEqual(caught.exception.code, "stale-draft")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-2",
                expected_draft_version=1,
                expected_publication_version=4,
                reviewed_digest=digest,
            )
        self.assertEqual(caught.exception.code, "stale-publication")
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 0)

    def test_publish_rollback_preserves_existing_publication(self):
        outcome, _ = self.publish_photo(slug="1")
        self.assertEqual(outcome["publication_version"], 1)
        record = self.repository.get_owner_photo(
            OWNER_A, self.repository.get_draft(OWNER_A).placement_for(
                SLOT_STORY_BANNER
            ).asset_id
        )
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-2",
            expected_draft_version=1,
            choices=[
                {
                    "slot": SLOT_STORY_BANNER,
                    "source": self.photo_source(record),
                    "crop": dict(PHOTO_BANNER_CROP, x=0.2),
                    "alt_text": PHOTO_ALT_TEXT,
                    "decorative": False,
                }
            ],
        )
        before = self.repository.snapshot()
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=2, expected_publication_version=1
        )["reviewed_digest"]
        self.repository.inject_failure("commit_publication", step="after_publication")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-2",
                expected_draft_version=2,
                expected_publication_version=1,
                reviewed_digest=digest,
            )
        self.assertEqual(caught.exception.code, "injected-failure")
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 1)
        current = self.service.current_publication(owner_id=OWNER_A)
        self.assertEqual(
            current["slots"][SLOT_STORY_BANNER]["crop"], PHOTO_BANNER_CROP
        )
        read = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
        )
        self.assertIsNotNone(read)
        self.assertEqual(sha256_hex(read["stream"].read()), record.digest)

    def test_lost_response_replay_creates_one_publication(self):
        outcome, review = self.publish_photo(slug="1")
        replay = self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=review["reviewed_digest"],
        )
        self.assertEqual(replay, outcome)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 1)
        self.assertEqual(
            len(
                [
                    call
                    for call in self.repository.mutation_log
                    if call == "commit_publication"
                ]
            ),
            1,
        )

    def test_publish_revalidates_assets_before_commit(self):
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP)
            ],
        )
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]
        self.repository.set_catalog_lifecycle(
            asset_id=asset.asset_id, version=asset.version, lifecycle="withdrawn"
        )
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-1",
                expected_draft_version=1,
                expected_publication_version=0,
                reviewed_digest=digest,
            )
        self.assertEqual(caught.exception.code, "asset-withdrawn")
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 0)

    def test_published_metadata_and_facts_never_use_catalog_claims(self):
        sentinel = "PETE-WAS-A-PROFESSIONAL-GARDENER"
        asset = self.art_asset(label=sentinel, tags=("gardening", sentinel))
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP),
                self.art_choice(asset, SLOT_EXPERIENCE_SUPPORT, ART_EXPERIENCE_CROP),
            ],
        )
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=digest,
        )
        self.assertIn(
            sentinel, canonical_json(self.service.list_library()["items"])
        )
        self.assertEqual(self.service.placement_fact_projection(owner_id=OWNER_A), ())
        current = self.service.current_publication(owner_id=OWNER_A)
        self.assertNotIn(sentinel, canonical_json(current))
        self.assertTrue(current["slots"][SLOT_STORY_BANNER]["decorative"])
        preview = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_STORY_BANNER,
            source=self.art_source(asset),
            crop=ART_BANNER_CROP,
            alt_text=ART_ALT_TEXT,
            decorative=True,
        )
        self.assertNotIn(sentinel, canonical_json(preview))
        self.assertFalse(preview["biographical_evidence"])


class MediaReadTests(ResumeMediaServiceTest):
    def staged_photo(self, *, owner_id=OWNER_A):
        record = self.ready_photo(owner_id=owner_id)
        self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, owner_id=owner_id,
                         record=record)
        return record

    def publish_art(self, asset=None, *, owner_id=OWNER_A, slug="1"):
        asset = asset or self.art_asset()
        self.service.add_media_choices(
            owner_id=owner_id,
            request_uuid="add-%s" % slug,
            expected_draft_version=self.repository.get_draft(owner_id).version,
            choices=[
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP)
            ],
        )
        draft_version = self.repository.get_draft(owner_id).version
        digest = self.service.review_draft(
            owner_id=owner_id,
            expected_draft_version=draft_version,
            expected_publication_version=0,
        )["reviewed_digest"]
        self.service.publish(
            owner_id=owner_id,
            request_uuid="publish-%s" % slug,
            expected_draft_version=draft_version,
            expected_publication_version=0,
            reviewed_digest=digest,
        )
        return asset

    def test_owner_preview_read_returns_bytes_without_locators(self):
        record = self.staged_photo()
        result = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="owner_preview"
        )
        self.assertEqual(set(result), {"stream", "content_type", "byte_length"})
        payload = result["stream"].read()
        self.assertEqual(sha256_hex(payload), record.digest)
        self.assertEqual(result["byte_length"], len(payload))
        self.assertNotIn(b"photo/v1", payload)

    def test_cross_owner_preview_denies_before_opening_storage(self):
        self.staged_photo()
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_B, slot=SLOT_STORY_BANNER, scope="owner_preview"
            )
        )
        self.assertEqual(self.capture.calls.count("open_media"), 0)
        self.publish_art()
        self.storage.opens.clear()
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_EXPERIENCE_SUPPORT,
                scope="owner_preview",
            )
        )
        self.assertEqual(self.storage.opens, [])
        self.assertEqual(self.capture.calls.count("open_media"), 0)

    def test_published_read_requires_the_current_publication(self):
        self.staged_photo()
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
            )
        )
        asset = self.publish_art()
        result = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
        )
        self.assertIsNotNone(result)
        payload = result["stream"].read()
        self.assertEqual(payload, ("ART-BANNER-%s" % asset.asset_id).encode("utf-8"))

    def test_read_discards_bytes_when_source_is_withdrawn_during_barrier(self):
        asset = self.publish_art()
        self.storage.on_open = lambda ref: self.repository.set_catalog_lifecycle(
            asset_id=asset.asset_id, version=asset.version, lifecycle="withdrawn"
        )
        result = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
        )
        self.assertIsNone(result)
        self.assertEqual(len(self.storage.opens), 1)

    def test_read_discards_bytes_on_version_change_during_barrier(self):
        record = self.staged_photo()

        def mutate(owner_id, source_id):
            self.repository.update_owner_photo(
                owner_id=owner_id,
                source_id=source_id,
                version=record.version + 1,
                digest=sha256_hex(b"replacement"),
            )

        self.capture.on_open = mutate
        result = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="owner_preview"
        )
        self.assertIsNone(result)
        self.assertEqual(self.capture.calls.count("open_media"), 1)

    def test_read_discards_bytes_when_placement_is_swapped_during_barrier(self):
        asset = self.publish_art()
        asset_record = self.art_asset(asset_id="art-2", label="Second Scene")
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-2",
            expected_draft_version=1,
            choices=[
                self.art_choice(asset_record, SLOT_STORY_BANNER, ART_BANNER_CROP)
            ],
        )
        new_digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=2, expected_publication_version=1
        )["reviewed_digest"]

        def swap(ref):
            self.repository.commit_publication(
                owner_id=OWNER_A,
                expected_draft_version=2,
                expected_publication_version=1,
                placements=(),
                digest=new_digest,
                receipt=RequestReceipt.create(
                    owner_id=OWNER_A,
                    command_type=COMMAND_PUBLISH,
                    request_uuid="publish-swap",
                    semantic_digest=new_digest,
                    outcome={"command": COMMAND_PUBLISH, "outcome": "published"},
                ),
            )

        self.storage.on_open = swap
        result = self.service.open_placement_media(
            owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
        )
        self.assertIsNone(result)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 2)
        self.assertEqual(asset.asset_id, "art-1")

    def test_read_refuses_bytes_that_do_not_match_the_authorized_digest(self):
        asset = self.publish_art()
        ref = "catalog/%s/v1/story_banner.png" % asset.asset_id
        self.storage.put(ref, b"tampered-payload", content_type="image/png")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
            )
        self.assertEqual(caught.exception.code, "media-unavailable")

    def test_storage_failure_returns_no_bytes_and_no_provider_detail(self):
        asset = self.publish_art()
        ref = "catalog/%s/v1/story_banner.png" % asset.asset_id
        self.storage.fail_open(ref, "private-storage-read-failed")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
            )
        self.assertEqual(caught.exception.code, "media-unavailable")
        self.assertNotIn("private-storage-read-failed", str(caught.exception))

    def test_withdrawal_makes_placements_ineligible_for_later_reads(self):
        asset = self.publish_art()
        self.repository.set_catalog_lifecycle(
            asset_id=asset.asset_id, version=asset.version, lifecycle="withdrawn"
        )
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="published"
            )
        )
        current = self.service.current_publication(owner_id=OWNER_A)
        self.assertFalse(current["slots"][SLOT_STORY_BANNER]["media_available"])
        self.assertEqual(current["publication_version"], 1)

    def test_restricted_or_deleted_private_photo_is_never_served(self):
        record = self.staged_photo()
        for lifecycle in ("restricted", "deleted"):
            with self.subTest(lifecycle=lifecycle):
                self.repository.update_owner_photo(
                    owner_id=OWNER_A,
                    source_id=record.source_id,
                    lifecycle=lifecycle,
                )
                self.assertIsNone(
                    self.service.open_placement_media(
                        owner_id=OWNER_A,
                        slot=SLOT_STORY_BANNER,
                        scope="owner_preview",
                    )
                )
                self.assertIsNone(
                    self.service.preview_placement(
                        owner_id=OWNER_A, slot=SLOT_STORY_BANNER
                    )
                )

    def test_invalid_scope_and_slot_are_refused(self):
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="public-raw"
            )
        self.assertEqual(caught.exception.code, "invalid-request")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.open_placement_media(
                owner_id=OWNER_A, slot="portrait", scope="published"
            )
        self.assertEqual(caught.exception.code, "slot-not-allowed")


class ResurrectionGuardTests(ResumeMediaServiceTest):
    """Finding 1: a non-active mirrored source can never be refreshed to active."""

    def test_deleted_restricted_or_withdrawn_source_cannot_refresh_to_active(self):
        for lifecycle, code in (
            ("deleted", "source-deleted"),
            ("restricted", "source-restricted"),
            ("withdrawn", "source-withdrawn"),
        ):
            with self.subTest(lifecycle=lifecycle):
                record = self.ready_photo()
                self.repository.update_owner_photo(
                    owner_id=OWNER_A,
                    source_id=record.source_id,
                    lifecycle=lifecycle,
                )
                before = self.repository.snapshot()
                with self.assertRaises(ResumeMediaConflict) as caught:
                    self.service.refresh_private_photo(
                        owner_id=OWNER_A, source_id=record.source_id
                    )
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(self.repository.snapshot(), before)
                stored = self.repository.get_owner_photo(OWNER_A, record.source_id)
                self.assertEqual(stored.lifecycle, lifecycle)

    def test_restriction_race_during_reconcile_cannot_resurrect_the_source(self):
        source_id = self.ingest_photo(plan=["needs_review"])

        def restrict(owner_id, key):
            self.repository.update_owner_photo(
                owner_id=owner_id, source_id=key, lifecycle="restricted"
            )

        self.capture.on_reconcile = restrict
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.refresh_private_photo(
                owner_id=OWNER_A, source_id=source_id
            )
        self.assertEqual(caught.exception.code, "source-restricted")
        stored = self.repository.get_owner_photo(OWNER_A, source_id)
        self.assertEqual(stored.lifecycle, "restricted")
        self.assertNotEqual(stored.state, "ready")
        self.assertEqual(stored.digest, "")


class AuthoritativeReadinessRecheckTests(ResumeMediaServiceTest):
    """Finding 2: the authoritative source is rechecked after the byte read."""

    def staged_photo(self):
        record = self.ready_photo()
        self.stage_photo(SLOT_STORY_BANNER, PHOTO_BANNER_CROP, record=record)
        return record

    def assert_get_source_after_open(self):
        self.assertIn("get_source", self.capture.calls)
        self.assertLess(
            self.capture.calls.index("open_media"),
            len(self.capture.calls) - 1 - self.capture.calls[::-1].index("get_source"),
        )

    def test_read_discards_bytes_when_the_authoritative_source_disappears(self):
        record = self.staged_photo()
        mirror = self.repository.get_owner_photo(OWNER_A, record.source_id)

        def revoke(owner_id, source_id):
            del self.capture.sources[(owner_id, source_id)]

        self.capture.on_open = revoke
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="owner_preview"
            )
        )
        # The mirror alone would not have caught this: it is unchanged.
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, record.source_id), mirror
        )
        self.assert_get_source_after_open()

    def test_read_discards_bytes_when_the_authoritative_version_changes(self):
        record = self.staged_photo()
        mirror = self.repository.get_owner_photo(OWNER_A, record.source_id)

        def replace_derivative(owner_id, source_id):
            self.capture.sources[(owner_id, source_id)][
                "derivative_sha256_digest"
            ] = "f" * 64

        self.capture.on_open = replace_derivative
        self.assertIsNone(
            self.service.open_placement_media(
                owner_id=OWNER_A, slot=SLOT_STORY_BANNER, scope="owner_preview"
            )
        )
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, record.source_id), mirror
        )
        self.assert_get_source_after_open()


class AtomicCommitRevalidationTests(ResumeMediaServiceTest):
    """Finding 3: source authorization is revalidated inside the atomic write."""

    def test_add_detects_a_deletion_injected_at_commit_entry(self):
        record = self.ready_photo()
        choices = [self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)]

        def race(operation):
            if operation == "commit_draft":
                self.repository.update_owner_photo(
                    owner_id=OWNER_A, source_id=record.source_id, lifecycle="deleted"
                )

        self.repository.on_commit_entry = race
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=choices,
            )
        self.assertEqual(caught.exception.code, "source-deleted")
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)
        self.assertIsNone(
            self.repository.get_receipt(
                owner_id=OWNER_A, command_type=COMMAND_ADD_MEDIA, request_uuid="add-1"
            )
        )
        # The injected race really landed; only the commit was refused.
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, record.source_id).lifecycle,
            "deleted",
        )

    def test_publish_detects_a_withdrawal_injected_at_commit_entry(self):
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP)],
        )
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]

        def race(operation):
            if operation == "commit_publication":
                self.repository.set_catalog_lifecycle(
                    asset_id=asset.asset_id,
                    version=asset.version,
                    lifecycle="withdrawn",
                )

        self.repository.on_commit_entry = race
        publication_before = self.repository.get_publication(OWNER_A)
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-1",
                expected_draft_version=1,
                expected_publication_version=0,
                reviewed_digest=digest,
            )
        self.assertEqual(caught.exception.code, "asset-withdrawn")
        self.assertEqual(self.repository.get_publication(OWNER_A), publication_before)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 0)
        self.assertIsNone(
            self.repository.get_receipt(
                owner_id=OWNER_A, command_type=COMMAND_PUBLISH, request_uuid="publish-1"
            )
        )


class PlacementSemanticsTests(ResumeMediaServiceTest):
    """Finding 4: typed placement semantics are persisted and projected safely."""

    def test_semantics_persist_and_project_safely(self):
        record = self.ready_photo()
        preview = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_STORY_BANNER,
            source=self.photo_source(record),
            crop=PHOTO_BANNER_CROP,
            alt_text="A friendly portrait",
            decorative=False,
            caption="Member written caption",
        )
        self.assertEqual(preview["alt_text"], "A friendly portrait")
        self.assertEqual(preview["caption"], "Member written caption")
        self.assertFalse(preview["decorative"])
        self.assertEqual(preview["provenance_label"], "Member photo")
        self.assertEqual(preview["presentation_version"], 1)
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(
                    record,
                    SLOT_STORY_BANNER,
                    PHOTO_BANNER_CROP,
                    alt_text="A friendly portrait",
                    caption="Member written caption",
                )
            ],
        )
        stored = self.repository.get_draft(OWNER_A).placement_for(SLOT_STORY_BANNER)
        self.assertEqual(stored.alt_text, "A friendly portrait")
        self.assertEqual(stored.caption, "Member written caption")
        self.assertFalse(stored.decorative)
        self.assertEqual(stored.provenance_label, "Member photo")
        self.assertIn("Member written caption", self.repository.snapshot())
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]
        self.service.publish(
            owner_id=OWNER_A,
            request_uuid="publish-1",
            expected_draft_version=1,
            expected_publication_version=0,
            reviewed_digest=digest,
        )
        published = self.service.current_publication(owner_id=OWNER_A)["slots"][
            SLOT_STORY_BANNER
        ]
        self.assertEqual(published["alt_text"], "A friendly portrait")
        self.assertEqual(published["caption"], "Member written caption")
        self.assertEqual(published["provenance_label"], "Member photo")
        self.assertEqual(published["presentation_version"], 1)
        self.assertFalse(published["decorative"])

    def test_presentation_version_advances_only_when_presentation_changes(self):
        record = self.ready_photo()
        for index, crop in enumerate(
            (PHOTO_BANNER_CROP, PHOTO_BANNER_CROP, dict(PHOTO_BANNER_CROP, x=0.05))
        ):
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-%d" % index,
                expected_draft_version=index,
                choices=[self.photo_choice(record, SLOT_STORY_BANNER, crop)],
            )
            placement = self.repository.get_draft(OWNER_A).placement_for(
                SLOT_STORY_BANNER
            )
            expected = 1 if index < 2 else 2
            self.assertEqual(placement.presentation_version, expected)

    def test_decorative_is_explicit_and_never_derived_from_source_kind(self):
        asset = self.art_asset()
        informative = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_STORY_BANNER,
            source=self.art_source(asset),
            crop=ART_BANNER_CROP,
            alt_text=ART_ALT_TEXT,
            decorative=False,
        )
        self.assertFalse(informative["decorative"])
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source=self.art_source(asset),
                crop=ART_BANNER_CROP,
                alt_text=ART_ALT_TEXT,
                decorative="yes",
            )
        self.assertEqual(caught.exception.code, "invalid-decorative")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=[
                    {
                        "slot": SLOT_STORY_BANNER,
                        "source": self.art_source(asset),
                        "crop": ART_BANNER_CROP,
                        "alt_text": ART_ALT_TEXT,
                    }
                ],
            )
        self.assertEqual(caught.exception.code, "invalid-decorative")

    def test_informative_placement_requires_alt_text(self):
        record = self.ready_photo()
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source=self.photo_source(record),
                crop=PHOTO_BANNER_CROP,
                alt_text="",
                decorative=False,
            )
        self.assertEqual(caught.exception.code, "required")
        decorative = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_STORY_BANNER,
            source=self.photo_source(record),
            crop=PHOTO_BANNER_CROP,
            alt_text="",
            decorative=True,
        )
        self.assertTrue(decorative["decorative"])
        self.assertEqual(decorative["alt_text"], "")

    def test_caption_is_bounded_and_kept_separate(self):
        record = self.ready_photo()
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source=self.photo_source(record),
                crop=PHOTO_BANNER_CROP,
                alt_text=PHOTO_ALT_TEXT,
                decorative=False,
                caption="x" * 501,
            )
        self.assertEqual(caught.exception.code, "invalid-caption")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source=self.photo_source(record),
                crop=PHOTO_BANNER_CROP,
                alt_text=PHOTO_ALT_TEXT,
                decorative=False,
                caption=17,
            )
        self.assertEqual(caught.exception.code, "invalid-caption")
        staged = self.service.stage_placement(
            owner_id=OWNER_A,
            slot=SLOT_STORY_BANNER,
            source=self.photo_source(record),
            crop=PHOTO_BANNER_CROP,
            alt_text=PHOTO_ALT_TEXT,
            decorative=False,
            caption="  Separate member caption  ",
        )
        self.assertEqual(staged["caption"], "Separate member caption")
        self.assertNotEqual(staged["caption"], staged["alt_text"])
        self.assertEqual(staged["provenance_label"], "Member photo")

    def test_catalog_label_or_tag_cannot_become_member_text(self):
        asset = self.art_asset(label="Quiet Forest", tags=("forest",))
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.stage_placement(
                owner_id=OWNER_A,
                slot=SLOT_STORY_BANNER,
                source=self.art_source(asset),
                crop=ART_BANNER_CROP,
                alt_text="Quiet Forest",
                decorative=False,
            )
        self.assertEqual(caught.exception.code, "catalog-claim-not-allowed")
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=[
                    self.art_choice(
                        asset,
                        SLOT_STORY_BANNER,
                        ART_BANNER_CROP,
                        alt_text=ART_ALT_TEXT,
                        caption="forest",
                    )
                ],
            )
        self.assertEqual(caught.exception.code, "catalog-claim-not-allowed")
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)

    def test_review_digest_binds_the_new_placement_semantics(self):
        crop = CropRect(x=0.1, y=0.2, width=0.6, height=0.3)
        base = MediaPlacement(
            slot=SLOT_STORY_BANNER,
            source_kind="generated_illustration",
            asset_id="art-1",
            asset_version=1,
            asset_digest="a" * 64,
            crop=crop,
            presentation_version=1,
            alt_text="First description",
            decorative=True,
        )
        changed_alt = replace(base, alt_text="Second description")
        changed_decorative = replace(base, decorative=False)
        changed_version = replace(base, presentation_version=2)
        changed_caption = replace(base, caption="Member caption")
        publication = PublicationRecord(owner_id=OWNER_A, version=0)
        digests = {
            review_digest(
                DraftMediaRecord(
                    owner_id=OWNER_A, version=1, placements=(candidate,)
                ),
                publication,
            )
            for candidate in (
                base,
                changed_alt,
                changed_decorative,
                changed_version,
                changed_caption,
            )
        }
        self.assertEqual(len(digests), 5)


class ConcurrentReplayTests(ResumeMediaServiceTest):
    """Finding 5: same-key racers converge on one structural outcome."""

    def gate(self, name):
        """Deterministically let both racers finish their prechecks first."""

        original = getattr(self.repository, name)
        barrier = threading.Barrier(2)

        def gated(*args, **kwargs):
            barrier.wait(timeout=30)
            return original(*args, **kwargs)

        setattr(self.repository, name, gated)

    def run_pair(self, first, second=None):
        second = second or first
        barrier = threading.Barrier(2)
        results: list = []
        errors: list = []
        lock = threading.Lock()

        def worker(call):
            barrier.wait()
            try:
                outcome = call()
            except Exception as error:  # noqa: BLE001 - captured for assertions
                with lock:
                    errors.append(error)
                return
            with lock:
                results.append(outcome)

        threads = [
            threading.Thread(target=worker, args=(first,)),
            threading.Thread(target=worker, args=(second,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        return results, errors

    def test_concurrent_same_key_add_converges_on_one_outcome(self):
        record = self.ready_photo()
        choices = [self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)]

        def call():
            return self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=choices,
            )

        self.gate("commit_draft")
        results, errors = self.run_pair(call)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["draft_version"], 1)
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 1)
        self.assertEqual(self.repository.mutation_log.count("commit_draft"), 1)

    def test_concurrent_same_key_words_only_converges_on_one_outcome(self):
        def call():
            return self.service.keep_words_only(
                owner_id=OWNER_A, request_uuid="words-1", expected_draft_version=0
            )

        self.gate("commit_draft")
        results, errors = self.run_pair(call)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 1)
        self.assertEqual(self.repository.mutation_log.count("commit_draft"), 1)

    def test_concurrent_same_key_publish_converges_on_one_outcome(self):
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP)],
        )
        digest = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )["reviewed_digest"]

        def call():
            return self.service.publish(
                owner_id=OWNER_A,
                request_uuid="publish-1",
                expected_draft_version=1,
                expected_publication_version=0,
                reviewed_digest=digest,
            )

        self.gate("commit_publication")
        results, errors = self.run_pair(call)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["publication_version"], 1)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 1)
        self.assertEqual(self.repository.mutation_log.count("commit_publication"), 1)

    def test_concurrent_same_key_different_body_conflicts(self):
        record = self.ready_photo()

        def first():
            return self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=[
                    self.photo_choice(record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP)
                ],
            )

        def second():
            return self.service.add_media_choices(
                owner_id=OWNER_A,
                request_uuid="add-1",
                expected_draft_version=0,
                choices=[
                    self.photo_choice(
                        record, SLOT_STORY_BANNER, dict(PHOTO_BANNER_CROP, x=0.05)
                    )
                ],
            )

        self.gate("commit_draft")
        results, errors = self.run_pair(first, second)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ResumeMediaConflict)
        self.assertEqual(errors[0].code, "idempotency-conflict")
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 1)
        self.assertEqual(self.repository.mutation_log.count("commit_draft"), 1)


class CatalogCursorAndMetadataTests(ResumeMediaServiceTest):
    """Findings 6 and 7: snapshot-fenced cursors and allowlisted metadata."""

    def test_cursor_after_a_catalog_change_requires_a_restart(self):
        for index in range(3):
            self.art_asset(asset_id="art-%02d" % index, label="leaf %02d" % index)
        first = self.service.list_library(query="leaf", limit=1)
        self.assertIsNotNone(first["next_cursor"])
        self.art_asset(asset_id="art-new", label="leaf new")
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.list_library(
                query="leaf", limit=1, cursor=first["next_cursor"]
            )
        self.assertEqual(caught.exception.code, "catalog-changed")
        self.repository.set_catalog_lifecycle(
            asset_id="art-00", version=1, lifecycle="withdrawn"
        )
        with self.assertRaises(ResumeMediaError) as caught:
            self.service.list_library(
                query="leaf", limit=1, cursor=first["next_cursor"]
            )
        self.assertEqual(caught.exception.code, "catalog-changed")

    def test_catalog_output_excludes_private_metadata(self):
        self.art_asset(
            provenance={
                "model": "synthetic-art-v1",
                "provider_locator": "https://private.example/asset/1",
                "storage_key": "secret-storage-key",
                "prompt": "internal generation prompt",
                "nested": {"locator": "deep-private-locator"},
            },
            rights={
                "rights_id": "synthetic-rights",
                "approval_state": "approved",
                "internal_notes": "private reviewer note",
            },
        )
        item = self.service.list_library()["items"][0]
        self.assertEqual(item["provenance"], {"model": "synthetic-art-v1"})
        self.assertEqual(
            item["rights"],
            {"rights_id": "synthetic-rights", "approval_state": "approved"},
        )
        # Mutating a retrieved projection cannot change repository state.
        item["provenance"]["model"] = "tampered"
        item["rights"]["rights_id"] = "tampered"
        fresh = self.service.list_library()["items"][0]
        self.assertEqual(fresh["provenance"], {"model": "synthetic-art-v1"})
        self.assertEqual(fresh["rights"]["rights_id"], "synthetic-rights")
        serialized = canonical_json(self.service.list_library()["items"])
        for private in (
            "private.example",
            "secret-storage-key",
            "internal generation prompt",
            "internal_notes",
            "deep-private-locator",
            "private reviewer note",
        ):
            self.assertNotIn(private, serialized)


class ProviderIdentityBindingTests(ResumeMediaServiceTest):
    """Finding 2: a provider result is bound to the requested source id."""

    def test_reconcile_result_for_a_different_source_is_refused(self):
        requested = self.ingest_photo(plan=["needs_review"])
        other = self.ready_photo()
        before_requested = self.repository.get_owner_photo(OWNER_A, requested)
        before_other = self.repository.get_owner_photo(OWNER_A, other.source_id)
        self.capture.reconcile_result = lambda owner_id, source_key: dict(
            self.capture.sources[(owner_id, other.source_id)]
        )
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.refresh_private_photo(
                owner_id=OWNER_A, source_id=requested
            )
        self.assertEqual(caught.exception.code, "source-changed")
        # Fail closed: neither the requested nor the substituted row changed.
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, requested), before_requested
        )
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, other.source_id), before_other
        )

    def test_matching_owner_and_token_but_wrong_source_is_still_refused(self):
        requested = self.ingest_photo(plan=["needs_review"])
        other = self.ingest_photo(plan=["needs_review"])
        self.capture.reconcile_result = lambda owner_id, source_key: dict(
            self.capture.sources[(owner_id, other)]
        )
        with self.assertRaises(ResumeMediaConflict) as caught:
            self.service.refresh_private_photo(
                owner_id=OWNER_A, source_id=requested
            )
        self.assertEqual(caught.exception.code, "source-changed")
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, requested).state, "scanning"
        )
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, other).state, "scanning"
        )


class ReviewProjectionTests(ResumeMediaServiceTest):
    """Finding 3: review shows exactly the presentation semantics it binds."""

    def build_reviewable_draft(self):
        record = self.ready_photo()
        asset = self.art_asset()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(
                    record,
                    SLOT_EXPERIENCE_SUPPORT,
                    PHOTO_EXPERIENCE_CROP,
                    alt_text="A described member photo",
                    caption="Member written caption",
                ),
                self.art_choice(asset, SLOT_STORY_BANNER, ART_BANNER_CROP),
            ],
        )
        return record, asset

    def test_review_exposes_every_digest_bound_presentation_field(self):
        record, asset = self.build_reviewable_draft()
        draft = self.repository.get_draft(OWNER_A)
        publication = self.repository.get_publication(OWNER_A)
        review = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )
        self.assertEqual(review["reviewed_digest"], review_digest(draft, publication))
        digest_input = _review_payload(draft, publication)
        self.assertEqual(sorted(review["slots"]), sorted(PLACEMENT_SLOTS))
        for slot, visible in review["slots"].items():
            bound = digest_input["slots"][slot]
            self.assertEqual(set(visible), set(bound) - {"asset_digest"})
            self.assertEqual(
                visible, {k: v for k, v in bound.items() if k != "asset_digest"}
            )
        published_view = review["slots"][SLOT_EXPERIENCE_SUPPORT]
        self.assertEqual(published_view["asset_kind"], "owner_photo")
        self.assertEqual(published_view["alt_text"], "A described member photo")
        self.assertEqual(published_view["caption"], "Member written caption")
        self.assertFalse(published_view["decorative"])
        self.assertEqual(published_view["provenance_label"], "Member photo")
        self.assertEqual(published_view["presentation_version"], 1)
        art_view = review["slots"][SLOT_STORY_BANNER]
        self.assertEqual(art_view["asset_id"], asset.asset_id)
        self.assertTrue(art_view["decorative"])
        self.assertEqual(art_view["provenance_label"], "Generated illustration (synthetic-art-v1)")
        serialized = canonical_json(review["slots"])
        for forbidden in (
            "asset_digest",
            record.digest,
            "photo/v1",
            "catalog/",
            "storage_key",
            "provider_locator",
            OWNER_A,
        ):
            self.assertNotIn(forbidden, serialized)

    def test_review_reflects_a_changed_presentation_semantic(self):
        record = self.ready_photo()
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-1",
            expected_draft_version=0,
            choices=[
                self.photo_choice(
                    record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP,
                    alt_text="First description",
                )
            ],
        )
        first = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=1, expected_publication_version=0
        )
        self.assertEqual(
            first["slots"][SLOT_STORY_BANNER]["alt_text"], "First description"
        )
        self.service.add_media_choices(
            owner_id=OWNER_A,
            request_uuid="add-2",
            expected_draft_version=1,
            choices=[
                self.photo_choice(
                    record, SLOT_STORY_BANNER, PHOTO_BANNER_CROP,
                    alt_text="Second description",
                )
            ],
        )
        second = self.service.review_draft(
            owner_id=OWNER_A, expected_draft_version=2, expected_publication_version=0
        )
        self.assertEqual(
            second["slots"][SLOT_STORY_BANNER]["alt_text"], "Second description"
        )
        self.assertNotEqual(first["reviewed_digest"], second["reviewed_digest"])


if __name__ == "__main__":
    unittest.main()
