"""Application-layer contracts for the MVP1 D private Resume media chooser.

These tests bind the accepted Resume media service/repository contracts to the
increment B private Resume draft and drive them through the real
``PhotoCaptureService`` orchestration with injected, labelled lower boundaries:
a synthetic in-process stand-in for the owner-scoped Photo Capture procedures
and a synthetic private storage double. That proves the adapter consumes the
real service's response shapes (state, row-version token, derivative bytes) and
never calls ``confirm_capture``.

Honest limits: no SQL engine, transaction, Blob, malware-scanner, live identity
or deployment proof. The in-memory stores and the procedure stand-in are
synthetic fixtures and are labelled as such.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import threading
import time
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from PIL import Image

from services.photo_capture_service import PhotoCaptureService, normalize_photo
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
    ResumeDraftIdempotencyConflict,
    ResumeDraftVersionConflict,
    SqlResumeDraftRepository,
)
from services.resume_draft_service import (
    SHARED_MEDIA_STATE_ATTRIBUTE,
    ResumeDraftConflictError,
    ResumeDraftService,
    ResumeDraftUnavailableError,
)
from services.resume_media_application import (
    PhotoCaptureResumeReadinessPort,
    ResumeDraftBoundMediaRepository,
    ResumeMediaApplicationUnavailable,
    SqlResumeMediaDraftStore,
    build_resume_media_application,
    configured_resume_media_application,
)
from services.resume_media_repository import (
    InMemoryMediaStorage,
    InMemoryResumeMediaRepository,
    LIFECYCLE_RESTRICTED,
    LIFECYCLE_WITHDRAWN,
    READINESS_REJECTED,
    READINESS_READY,
    READINESS_SCANNING,
    ResumeMediaRepositoryError,
    SOURCE_KIND_GENERATED_ILLUSTRATION,
    SOURCE_KIND_OWNER_PHOTO,
)
from services.resume_media_service import (
    ResumeMediaConflict,
    ResumeMediaDenied,
    ResumeMediaError,
    ResumePhotoReadinessAdapter,
    centered_slot_crop,
    validate_crop,
)


OWNER_A = "owner-a"
OWNER_B = "owner-b"
SOURCE_KEY = "11111111-1111-4111-8111-111111111111"
ORIGINAL_REF = "photo/v1/ab/ab0123456789abcdef0123456789abcd.jpg"
PREVIEW_REF = "photo/v1/ab/ab0123456789abcdef0123456789abcd-preview.jpg"
SESSION = "01a09779-f4aa-7272-9c4f-89b9bb34af43"


def image_bytes(image_format="JPEG", size=(1200, 800)):
    """A synthetic source image whose EXIF-free derivative is deterministic."""

    payload = io.BytesIO()
    image = Image.new("RGB", size, (36, 78, 66))
    image.save(payload, format=image_format)
    return payload.getvalue()


class FakeUpload:
    """A labelled synthetic upload: the filename must never be used."""

    filename = "member-file-name-must-not-appear.jpg"

    def __init__(self, payload=None, mimetype="image/jpeg"):
        self.mimetype = mimetype
        self.stream = io.BytesIO(payload if payload is not None else image_bytes())


class SyntheticPhotoCaptureProcedures:
    """Labelled synthetic stand-in for the owner-scoped Photo Capture procedures."""

    def __init__(self):
        self.calls = []
        self._queued = {}
        self._sticky = {}

    def queue(self, procedure, *rows):
        self._queued.setdefault(procedure, []).extend(rows)

    def set_sticky(self, procedure, row):
        self._sticky[procedure] = row

    def procedures(self):
        return [name for name, _ in self.calls]

    def parameters(self, procedure):
        return [params for name, params in self.calls if name == procedure]

    def bound(self, procedure):
        """Every parameter set this procedure was called with."""

        return [dict(params) for name, params in self.calls if name == procedure]

    def first_row(self, procedure, parameters=None):
        self.calls.append((procedure, list(parameters or [])))
        queued = self._queued.get(procedure) or []
        if queued:
            return queued.pop(0)
        row = self._sticky.get(procedure)
        return row() if callable(row) else row


class SyntheticCaptureStorage:
    """Labelled synthetic private storage double for the Photo Capture boundary."""

    def __init__(self):
        self.objects = {}
        self.uploads = []
        self.downloads = []
        self.scans = {}

    def upload(self, ref, data, content_type):
        etag = '"etag-%d"' % (len(self.uploads) + 1)
        self.uploads.append({"ref": ref, "bytes": len(data), "content_type": content_type})
        self.objects[ref] = {
            "data": bytes(data),
            "content_type": str(content_type),
            "etag": etag,
        }
        return {"etag": etag}

    def download(self, ref):
        self.downloads.append(ref)
        record = self.objects[ref]
        return {
            "data": record["data"],
            "byte_length": len(record["data"]),
            "content_type": record["content_type"],
            "etag": record["etag"],
        }

    def get_scan_result(self, ref):
        if ref not in self.scans:
            self.scans[ref] = {
                "result": "clean",
                "scan_time_utc": datetime.now(timezone.utc),
            }
        return self.scans[ref]

    def exists(self, ref):
        return ref in self.objects

    def delete(self, ref):
        self.objects.pop(ref, None)


class RecordingDraftStore(InMemoryResumeDraftRepository):
    """Synthetic Resume draft store that can refuse one atomic command on demand.

    The refusal lands before anything is applied or persisted, so the prior
    snapshot must remain byte-identical.
    """

    def __init__(self):
        super().__init__()
        self.fail_next_save = False
        self.saves = 0

    def commit_owner_command(self, owner_user_key, *, expected_version, apply):
        self.saves += 1
        if self.fail_next_save:
            self.fail_next_save = False
            raise ResumeMediaRepositoryError("storage-unavailable")
        return super().commit_owner_command(
            owner_user_key, expected_version=expected_version, apply=apply
        )

    def save_owner(self, owner_user_key, snapshot):
        self.saves += 1
        if self.fail_next_save:
            self.fail_next_save = False
            raise ResumeMediaRepositoryError("storage-unavailable")
        super().save_owner(owner_user_key, snapshot)


class MediaApplicationTestCase(unittest.TestCase):
    def setUp(self):
        self.procedures = SyntheticPhotoCaptureProcedures()
        self.capture_storage = SyntheticCaptureStorage()
        self.capture = PhotoCaptureService(
            database=self.procedures, storage=self.capture_storage
        )
        self.sources = InMemoryResumeMediaRepository()
        self.storage = InMemoryMediaStorage()
        self.draft_store = RecordingDraftStore()
        self.draft_service = ResumeDraftService(
            repository=self.draft_store, catalog=InMemoryCanonicalCatalog()
        )
        self.application = build_resume_media_application(
            draft_store=self.draft_store,
            sources=self.sources,
            storage=self.storage,
            photo_readiness=ResumePhotoReadinessAdapter(
                capture=PhotoCaptureResumeReadinessPort(self.capture)
            ),
            persistence_label="in_memory_not_live_db",
            catalog_label="synthetic_test_catalog",
        )
        self.original_payload = image_bytes()
        self.derivative_payload = None

    # -- helpers -----------------------------------------------------------

    def install_photo_capture(self, *, original=None, derivative=None):
        """Queue the real service's procedure calls for one upload and refresh."""

        original = original or image_bytes()
        derivative = derivative or normalize_photo(original, "image/jpeg").data
        self.derivative_payload = derivative
        self.procedures.queue(
            "usp_CreatePhotoSource",
            {
                "outcome": "created",
                "source_key": SOURCE_KEY,
                "row_version": b"\x01" * 8,
            },
        )
        self.procedures.queue(
            "usp_MarkPhotoUploaded",
            {"outcome": "scanning", "row_version": b"\x02" * 8},
        )
        # The first owner-scoped read (inside create_source) sees the source
        # still scanning; later reads see the processed, ready row below.
        self.procedures.queue(
            "usp_GetPhotoSourceForOwner",
            {
                "source_key": SOURCE_KEY,
                "state": READINESS_SCANNING,
                "row_version": b"\x02" * 8,
                "pixel_width": 0,
                "pixel_height": 0,
            },
        )
        self.procedures.set_sticky("usp_CompletePhotoProcessing", {"outcome": "needs_review"})

        # These rows are derived from what the real Photo Capture service
        # actually uploaded, so the numbers the Resume adapter binds are the
        # service's own bytes and version tokens rather than a fake echo.
        def created_parameters():
            bound = self.procedures.bound("usp_CreatePhotoSource")
            self.assertIsNotNone(bound, "the real service must create a source first")
            return bound[0]

        def original_record():
            parameters = created_parameters()
            ref = parameters["@OriginalBlobName"]
            record = self.capture_storage.objects[ref]
            return parameters, ref, record

        def processing_row():
            parameters, ref, record = original_record()
            return {
                "source_key": SOURCE_KEY,
                "state": READINESS_SCANNING,
                "original_blob_name": ref,
                "derivative_blob_name": parameters["@DerivativeBlobName"],
                "original_content_type": parameters["@OriginalContentType"],
                "original_byte_length": len(record["data"]),
                "original_sha256_digest": hashlib.sha256(record["data"]).digest(),
                "original_blob_etag": record["etag"],
                "row_version": b"\x02" * 8,
            }

        def scan_result_row():
            parameters, ref, record = original_record()
            return {
                "outcome": "processing",
                "original_blob_name": ref,
                "original_content_type": parameters["@OriginalContentType"],
                "original_byte_length": len(record["data"]),
                "original_sha256_digest": hashlib.sha256(record["data"]).digest(),
                "original_blob_etag": record["etag"],
                "derivative_blob_name": parameters["@DerivativeBlobName"],
                "row_version": b"\x03" * 8,
            }

        def ready_row():
            parameters = created_parameters()
            derivative_record = self.capture_storage.objects[
                parameters["@DerivativeBlobName"]
            ]
            return {
                "source_key": SOURCE_KEY,
                "state": "needs_review",
                "row_version": b"\x04" * 8,
                "pixel_width": 1200,
                "pixel_height": 800,
                "derivative_content_type": derivative_record["content_type"],
                "derivative_byte_length": len(derivative_record["data"]),
                "derivative_blob_name": parameters["@DerivativeBlobName"],
                "scan_result": "clean",
            }

        def media_row():
            parameters = created_parameters()
            ref = parameters["@DerivativeBlobName"]
            record = self.capture_storage.objects[ref]
            return {
                "source_key": SOURCE_KEY,
                "blob_name": ref,
                "content_type": record["content_type"],
                "byte_length": len(record["data"]),
                "sha256_digest": hashlib.sha256(record["data"]).digest(),
            }

        self.procedures.set_sticky(
            "usp_GetPhotoProcessingSourceForOwner", processing_row
        )
        self.procedures.set_sticky("usp_RecordPhotoScanResult", scan_result_row)
        self.procedures.set_sticky("usp_GetPhotoSourceForOwner", ready_row)
        self.procedures.set_sticky("usp_GetPhotoMediaForOwner", media_row)

    def ready_source_row(self, state="rejected", row_version=b"\x03" * 8):
        """A terminal owner-scoped source row for refusal journeys."""

        return {
            "source_key": SOURCE_KEY,
            "state": state,
            "row_version": row_version,
            "pixel_width": 0,
            "pixel_height": 0,
        }

    def upload_ready_photo(self, *, owner_id=OWNER_A):
        self.install_photo_capture()
        uploaded = self.application.upload_photo(
            owner_id=owner_id, upload=FakeUpload(self.original_payload)
        )
        refreshed = self.application.refresh_photo(
            owner_id=owner_id, source_id=uploaded["source_id"]
        )
        self.assertEqual(refreshed["state"], READINESS_READY)
        return uploaded["source_id"]

    def stage_photo(self, source_id, slot, *, owner_id=OWNER_A, caption=None):
        crop = self.default_crop(slot, 1200, 800)
        return self.application.stage_placement(
            owner_id=owner_id,
            payload={
                "slot": slot,
                "source": {"kind": SOURCE_KIND_OWNER_PHOTO, "source_id": source_id},
                "crop": crop,
                "alt_text": "",
                "decorative": True,
                "caption": caption,
            },
        )

    @staticmethod
    def default_crop(slot, width, height):
        return centered_slot_crop(slot=slot, width=width, height=height).as_dict()

    def seed_art(self, asset_id="art-forest", *, version=1, digest="c" * 64):
        for slot in ("story_banner", "experience_support"):
            self.storage.put(
                f"catalog/{asset_id}/{version}/{slot}.png",
                b"catalog-bytes-" + slot.encode("ascii"),
                content_type="image/png",
            )
        return self.sources.seed_catalog_asset(
            asset_id=asset_id,
            label="Forest trail",
            category="Nature",
            tags=("calm", "outdoors"),
            width=1600,
            height=900,
            version=version,
            digest=digest,
            provenance={"model": "synthetic-test-model"},
            rights={"rights_id": "synthetic-rights", "approval_state": "approved"},
            derivatives=[
                {
                    "slot": slot,
                    "ref": f"catalog/{asset_id}/{version}/{slot}.png",
                    "digest": self.storage.digest_for(
                        f"catalog/{asset_id}/{version}/{slot}.png"
                    ),
                    "content_type": "image/png",
                    "byte_length": len(b"catalog-bytes-" + slot.encode("ascii")),
                }
                for slot in ("story_banner", "experience_support")
            ],
        )

    def add_choices(self, *entries, expected_draft_version, request_id=None):
        return self.application.add_media(
            owner_id=OWNER_A,
            payload={
                "type": "add_media",
                "request_id": request_id or str(uuid4()),
                "expected_draft_version": expected_draft_version,
                "choices": list(entries),
            },
        )

    def photo_choice(self, source_id, slot, *, caption=None):
        return {
            "slot": slot,
            "source": {"kind": SOURCE_KIND_OWNER_PHOTO, "source_id": source_id},
            "crop": self.default_crop(slot, 1200, 800),
            "alt_text": "",
            "decorative": True,
            "caption": caption,
        }


class LargeVersionTransportTests(MediaApplicationTestCase):
    """Browser-facing saved/review responses keep large versions exact."""

    LARGE_VERSION = 289_360_691_352_306_692

    def seed_large_photo(self):
        return self.sources.seed_owner_photo(
            owner_id=OWNER_A,
            source_id="source-large-version",
            state=READINESS_READY,
            digest=hashlib.sha256(b"synthetic-large-version").hexdigest(),
            width=1200,
            height=800,
            version=self.LARGE_VERSION,
            version_token="%016x" % self.LARGE_VERSION,
        )

    def add_large_choice(self):
        record = self.seed_large_photo()
        return self.application.add_media(
            owner_id=OWNER_A,
            payload={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [
                    {
                        "slot": "story_banner",
                        "source": {
                            "kind": SOURCE_KIND_OWNER_PHOTO,
                            "source_id": record.source_id,
                            "expected_version": record.version,
                            "expected_digest": record.digest,
                        },
                        "crop": self.default_crop("story_banner", 1200, 800),
                        "alt_text": "",
                        "decorative": True,
                        "caption": None,
                    }
                ],
            },
        )

    def test_workspace_and_review_transport_large_version_as_exact_json_text(self):
        self.add_large_choice()
        workspace = self.application.workspace(owner_id=OWNER_A)
        review = self.application.review(
            owner_id=OWNER_A,
            payload={
                "expected_draft_version": workspace["draft_version"],
                "expected_publication_version": 0,
            },
        )
        for view in (workspace, review):
            transported = json.loads(json.dumps(view))
            value = transported["slots"]["story_banner"]["asset_version"]
            self.assertIsInstance(value, str)
            self.assertEqual(value, str(self.LARGE_VERSION))
            self.assertEqual(int(value), self.LARGE_VERSION)

    @unittest.skipUnless(
        shutil.which("node"), "node is required for the JavaScript roundtrip check"
    )
    def test_large_version_javascript_roundtrip_stays_exact_text(self):
        self.add_large_choice()
        workspace = self.application.workspace(owner_id=OWNER_A)
        serialized = json.dumps(workspace)
        script = (
            "const fs = require('fs');"
            "const payload = JSON.parse(fs.readFileSync(0, 'utf8'));"
            "const value = payload.slots.story_banner.asset_version;"
            "const numeric = JSON.parse('{\"value\":289360691352306692}').value;"
            "process.stdout.write(JSON.stringify(["
            "typeof value, value, String(BigInt(value)),"
            "typeof numeric, String(BigInt(numeric))]));"
        )
        completed = subprocess.run(
            [shutil.which("node"), "-e", script],
            input=serialized,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)
        self.assertEqual(
            observed[:3],
            ["string", str(self.LARGE_VERSION), str(self.LARGE_VERSION)],
        )
        # A raw JSON number above 2**53-1 is exactly what rounds in JavaScript;
        # canonical decimal text is the lossless browser transport.
        self.assertEqual(observed[3], "number")
        self.assertEqual(observed[4], str(self.LARGE_VERSION - 4))


class PhotoCaptureBoundaryTests(MediaApplicationTestCase):
    def test_upload_reaches_ready_through_the_real_service_without_confirm(self):
        source_id = self.upload_ready_photo()

        procedures = self.procedures.procedures()
        self.assertIn("usp_CreatePhotoSource", procedures)
        self.assertIn("usp_MarkPhotoUploaded", procedures)
        self.assertIn("usp_RecordPhotoScanResult", procedures)
        self.assertIn("usp_CompletePhotoProcessing", procedures)
        self.assertIn("usp_GetPhotoMediaForOwner", procedures)
        self.assertNotIn("usp_ConfirmPhotoCapture", procedures)

        # The real service uploads the synthetic original to private storage and
        # uploads a separate metadata-free derivative; the member's filename is
        # never used as a storage reference.
        refs = [entry["ref"] for entry in self.capture_storage.uploads]
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(ref.startswith("photo/v1/") for ref in refs))
        self.assertNotIn("member-file-name", " ".join(refs))

        view = self.application.photo_state(owner_id=OWNER_A)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]["source_id"], source_id)
        self.assertEqual(view[0]["state"], READINESS_READY)
        self.assertTrue(view[0]["selectable"])
        self.assertEqual(view[0]["width"], 1200)
        self.assertEqual(view[0]["height"], 800)
        # The placement version is the exact unsigned Photo Capture rowversion,
        # not a process-local counter. The durable SQL fence compares this value
        # with the locked authoritative source row.
        self.assertEqual(
            self.sources.get_owner_photo(OWNER_A, source_id).version,
            int.from_bytes(b"\x04" * 8, byteorder="big", signed=False),
        )
        for forbidden in ("blob", "storage", "filename", "digest", "scan", "exif"):
            self.assertNotIn(forbidden, repr(view[0]).lower())

    def test_private_preview_returns_the_exact_derivative_bytes(self):
        source_id = self.upload_ready_photo()
        opened = self.application.open_photo_preview(
            owner_id=OWNER_A, source_id=source_id
        )
        self.assertIsNotNone(opened)
        self.assertEqual(opened["stream"].read(), self.derivative_payload)
        self.assertEqual(opened["byte_length"], len(self.derivative_payload))
        self.assertEqual(opened["content_type"], "image/jpeg")

    def test_refused_scan_never_becomes_selectable_and_preview_denies(self):
        self.install_photo_capture()
        self.procedures._queued["usp_RecordPhotoScanResult"] = [
            {"outcome": "rejected"}
        ]
        self.procedures.set_sticky(
            "usp_GetPhotoSourceForOwner", self.ready_source_row("rejected")
        )
        uploaded = self.application.upload_photo(
            owner_id=OWNER_A, upload=FakeUpload(self.original_payload)
        )
        refreshed = self.application.refresh_photo(
            owner_id=OWNER_A, source_id=uploaded["source_id"]
        )
        self.assertEqual(refreshed["state"], READINESS_REJECTED)
        self.assertFalse(refreshed["retryable"])
        view = self.application.photo_state(owner_id=OWNER_A)[0]
        self.assertFalse(view["selectable"])
        self.assertFalse(view["retryable"])
        with self.assertRaises(ResumeMediaConflict):
            self.stage_photo(uploaded["source_id"], "story_banner")
        with self.assertRaises(ResumeMediaConflict):
            self.application.open_photo_preview(
                owner_id=OWNER_A, source_id=uploaded["source_id"]
            )

    def test_foreign_owner_source_reference_is_denied_identically(self):
        source_id = self.upload_ready_photo()
        with self.assertRaises(ResumeMediaDenied):
            self.application.open_photo_preview(owner_id=OWNER_B, source_id=source_id)
        with self.assertRaises(ResumeMediaDenied):
            self.application.open_photo_preview(
                owner_id=OWNER_B, source_id="unknown-source"
            )


class DraftAtomicityTests(MediaApplicationTestCase):
    def test_media_add_advances_the_shared_draft_version_once(self):
        source_id = self.upload_ready_photo()
        self.assertEqual(
            self.application.versions(owner_id=OWNER_A)["draft_version"], 0
        )
        first = self.add_choices(
            self.photo_choice(source_id, "story_banner", caption="My caption"),
            expected_draft_version=0,
        )
        self.assertEqual(first["outcome"], "committed")
        self.assertEqual(first["draft_version"], 1)
        self.assertEqual(
            self.application.versions(owner_id=OWNER_A)["draft_version"], 1
        )

        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertEqual(workspace["draft_version"], 1)
        saved = workspace["slots"]["story_banner"]
        self.assertEqual(saved["caption"], "My caption")
        self.assertEqual(saved["asset_id"], source_id)
        self.assertTrue(saved["media_available"])
        self.assertIsNone(workspace["slots"]["experience_support"])
        self.assertEqual(workspace["capabilities"]["persistence"], "in_memory_not_live_db")
        self.assertFalse(workspace["capabilities"]["publishes"])
        self.assertFalse(workspace["capabilities"]["schema_applied"])

    def test_text_save_and_media_add_do_not_clobber_each_other(self):
        source_id = self.upload_ready_photo()
        self.seed_art()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        record_key = str(uuid4())
        saved = self.draft_service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "create_private_item",
                "record_key": record_key,
                "record_type": "skill",
                "values": {"name": "Systems engineering"},
            },
        )
        self.assertEqual(saved["outcome"], "created")
        workspace_after_text = self.application.workspace(owner_id=OWNER_A)
        self.assertIn("story_banner", workspace_after_text["slots"])
        self.assertTrue(workspace_after_text["slots"]["story_banner"])

        # The canonical private record is still there after the media command.
        second = self.add_choices(
            {
                "slot": "experience_support",
                "source": {
                    "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
                    "asset_id": "art-forest",
                    "asset_version": 1,
                },
                "crop": self.default_crop("experience_support", 1600, 900),
                "alt_text": "",
                "decorative": True,
                "caption": None,
            },
            expected_draft_version=1,
        )
        self.assertEqual(second["draft_version"], 2)
        final = self.application.workspace(owner_id=OWNER_A)
        self.assertTrue(final["slots"]["story_banner"])
        self.assertTrue(final["slots"]["experience_support"])
        canonical = self.draft_service.get_workspace(OWNER_A)
        self.assertEqual(
            [item["record_key"] for item in canonical["items"]], [record_key]
        )

    def test_stale_draft_media_command_changes_nothing(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        before = self.sources.snapshot(), self.draft_store.load_owner(OWNER_A)
        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(
                {
                    "slot": "experience_support",
                    "source": {
                        "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
                        "asset_id": "art-forest",
                        "asset_version": 1,
                    },
                    "crop": self.default_crop("experience_support", 1600, 900),
                    "alt_text": "",
                    "decorative": True,
                },
                expected_draft_version=0,
            )
        self.assertEqual(raised.exception.code, "stale-draft")
        self.assertEqual(before, (self.sources.snapshot(), self.draft_store.load_owner(OWNER_A)))

    def test_same_request_uuid_replays_and_changed_payload_conflicts(self):
        source_id = self.upload_ready_photo()
        request_id = str(uuid4())
        first = self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
            request_id=request_id,
        )
        replay = self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
            request_id=request_id,
        )
        self.assertEqual(replay["draft_version"], first["draft_version"])
        self.assertEqual(self.application.versions(owner_id=OWNER_A)["draft_version"], 1)

        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(
                self.photo_choice(source_id, "experience_support"),
                expected_draft_version=0,
                request_id=request_id,
            )
        self.assertEqual(raised.exception.code, "idempotency-conflict")
        self.assertEqual(self.application.versions(owner_id=OWNER_A)["draft_version"], 1)

    def test_injected_write_failure_leaves_the_prior_draft_unchanged(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        before = self.draft_store.load_owner(OWNER_A)
        self.draft_store.fail_next_save = True
        with self.assertRaises(ResumeMediaError) as raised:
            self.add_choices(
                self.photo_choice(source_id, "experience_support", caption="Two"),
                expected_draft_version=1,
            )
        self.assertEqual(raised.exception.code, "storage-unavailable")
        self.assertEqual(self.draft_store.load_owner(OWNER_A), before)
        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertTrue(workspace["slots"]["story_banner"])
        self.assertIsNone(workspace["slots"]["experience_support"])

    def test_removal_is_slot_local_and_never_touches_the_publication(self):
        source_id = self.upload_ready_photo()
        self.seed_art()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            {
                "slot": "experience_support",
                "source": {
                    "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
                    "asset_id": "art-forest",
                    "asset_version": 1,
                },
                "crop": self.default_crop("experience_support", 1600, 900),
                "alt_text": "",
                "decorative": True,
            },
            expected_draft_version=0,
        )
        removed = self.add_choices(
            {"slot": "story_banner", "source": None},
            expected_draft_version=1,
        )
        self.assertEqual(removed["draft_version"], 2)
        self.assertEqual(removed["removed_slots"], ["story_banner"])
        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertIsNone(workspace["slots"]["story_banner"])
        self.assertEqual(
            workspace["slots"]["experience_support"]["asset_id"], "art-forest"
        )
        self.assertEqual(
            self.application.versions(owner_id=OWNER_A)["publication_version"], 0
        )

    def test_keep_words_only_discards_pending_choices_and_keeps_saved_media(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        self.stage_photo(source_id, "experience_support")
        outcome = self.application.keep_words_only(
            owner_id=OWNER_A,
            payload={
                "type": "keep_words_only",
                "request_id": str(uuid4()),
                "expected_draft_version": 1,
            },
        )
        self.assertEqual(outcome["draft_version"], 2)
        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertEqual(workspace["staged"], {})
        self.assertTrue(workspace["slots"]["story_banner"])

    def test_swap_recomputes_a_valid_crop_for_each_target_slot(self):
        source_id = self.upload_ready_photo()
        self.seed_art()
        self.stage_photo(source_id, "story_banner")
        self.application.stage_placement(
            owner_id=OWNER_A,
            payload={
                "slot": "experience_support",
                "source": {
                    "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
                    "asset_id": "art-forest",
                    "asset_version": 1,
                },
                "crop": self.default_crop("experience_support", 1600, 900),
                "alt_text": "",
                "decorative": True,
            },
        )
        before = self.sources.snapshot()
        swapped = self.application.swap_placements(owner_id=OWNER_A)
        self.assertEqual(set(swapped["slots"]), {"story_banner", "experience_support"})
        self.assertEqual(swapped["slots"]["story_banner"]["source_kind"], SOURCE_KIND_GENERATED_ILLUSTRATION)
        self.assertEqual(swapped["slots"]["experience_support"]["source_kind"], SOURCE_KIND_OWNER_PHOTO)
        for slot, preview in swapped["slots"].items():
            validate_crop(
                preview["crop"],
                slot=slot,
                width=preview["width"],
                height=preview["height"],
            )
        # Swapping is a preview-only action: no private draft state changed.
        self.assertEqual(self.sources.snapshot(), before)
        self.assertEqual(
            self.application.versions(owner_id=OWNER_A)["draft_version"], 0
        )

    def test_withdrawn_source_is_unavailable_in_the_saved_draft_view(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        self.sources.update_owner_photo(
            owner_id=OWNER_A, source_id=source_id, lifecycle=LIFECYCLE_WITHDRAWN
        )
        entry = self.application.workspace(owner_id=OWNER_A)["slots"]["story_banner"]
        self.assertFalse(entry["media_available"])
        self.assertIsNone(
            self.application.open_placement_media(owner_id=OWNER_A, slot="story_banner")
        )

    def test_restricted_source_is_refused_by_add_without_writes(self):
        source_id = self.upload_ready_photo()
        self.sources.update_owner_photo(
            owner_id=OWNER_A, source_id=source_id, lifecycle=LIFECYCLE_RESTRICTED
        )
        before = self.draft_store.load_owner(OWNER_A)
        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(
                self.photo_choice(source_id, "story_banner"),
                expected_draft_version=0,
            )
        self.assertEqual(raised.exception.code, "source-restricted")
        self.assertEqual(self.draft_store.load_owner(OWNER_A), before)

    def test_add_binds_the_reviewed_source_version(self):
        source_id = self.upload_ready_photo()
        preview = self.stage_photo(source_id, "story_banner")
        reviewed_version = preview["asset_version"]
        self.assertIsInstance(reviewed_version, str)
        # The source is replaced while the member is still reviewing it.
        self.sources.update_owner_photo(
            owner_id=OWNER_A,
            source_id=source_id,
            version=int(reviewed_version) + 1,
            digest="f" * 64,
        )
        before = self.draft_store.load_owner(OWNER_A)
        choice = self.photo_choice(source_id, "story_banner")
        choice["source"]["expected_version"] = reviewed_version
        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(choice, expected_draft_version=0)
        self.assertEqual(raised.exception.code, "stale-version")
        self.assertEqual(self.draft_store.load_owner(OWNER_A), before)


class CatalogIntegrationTests(MediaApplicationTestCase):
    def test_library_page_is_bounded_and_honest_when_empty(self):
        page = self.application.library(owner_id=OWNER_A)
        self.assertEqual(page["items"], [])
        self.assertEqual(page["total"], 0)
        self.assertIsNone(page["next_cursor"])
        self.assertEqual(page["catalog"], "synthetic_test_catalog")

    def test_library_thumbnail_returns_real_bytes_and_disappears_when_withdrawn(self):
        self.seed_art()
        page = self.application.library(owner_id=OWNER_A, query="forest")
        self.assertEqual(len(page["items"]), 1)
        item = page["items"][0]
        for forbidden in ("ref", "digest", "blob", "storage", "prompt"):
            self.assertNotIn(forbidden, {key.lower() for key in item})
        opened = self.application.open_library_thumbnail(
            owner_id=OWNER_A,
            asset_id=item["asset_id"],
            asset_version=item["asset_version"],
            slot="story_banner",
        )
        self.assertEqual(opened["stream"].read(), b"catalog-bytes-story_banner")
        self.assertEqual(opened["content_type"], "image/png")

        self.sources.set_catalog_lifecycle(
            asset_id="art-forest", version=1, lifecycle=LIFECYCLE_WITHDRAWN
        )
        self.assertIsNone(
            self.application.open_library_thumbnail(
                owner_id=OWNER_A,
                asset_id="art-forest",
                asset_version=1,
                slot="story_banner",
            )
        )
        self.assertEqual(self.application.library(owner_id=OWNER_A)["items"], [])

    def test_library_search_paginates_with_a_stable_cursor(self):
        for index in range(5):
            self.seed_art(asset_id=f"art-{index}", digest=("%064d" % index))
        first = self.application.library(owner_id=OWNER_A, limit=2)
        self.assertEqual(len(first["items"]), 2)
        self.assertIsNotNone(first["next_cursor"])
        second = self.application.library(
            owner_id=OWNER_A, limit=2, cursor=first["next_cursor"]
        )
        self.assertEqual(len(second["items"]), 2)
        overlap = {item["asset_id"] for item in first["items"]} & {
            item["asset_id"] for item in second["items"]
        }
        self.assertFalse(overlap)
        with self.assertRaises(ResumeMediaError):
            self.application.library(
                owner_id=OWNER_A, query="different", limit=2, cursor=first["next_cursor"]
            )

    def test_catalog_bytes_are_rechecked_after_the_read(self):
        self.seed_art()
        ref = "catalog/art-forest/1/story_banner.png"

        def withdraw(_ref):
            self.sources.set_catalog_lifecycle(
                asset_id="art-forest", version=1, lifecycle=LIFECYCLE_WITHDRAWN
            )

        self.storage.on_open = withdraw
        self.assertIsNone(
            self.application.open_library_thumbnail(
                owner_id=OWNER_A,
                asset_id="art-forest",
                asset_version=1,
                slot="story_banner",
            )
        )
        self.assertIn(ref, self.storage.opens)


class WiringTests(MediaApplicationTestCase):
    def test_missing_configuration_is_unavailable_rather_than_a_fixture_store(self):
        for value in (None, {}, "media"):
            with self.subTest(value=value), self.assertRaises(
                ResumeMediaApplicationUnavailable
            ):
                configured_resume_media_application(value)
        with self.assertRaises(ResumeMediaApplicationUnavailable):
            build_resume_media_application(draft_store=None, sources=None)

    def test_capabilities_never_claim_publication_or_applied_schema(self):
        capabilities = self.application.capabilities()
        self.assertFalse(capabilities["publishes"])
        self.assertFalse(capabilities["review_publishes"])
        self.assertFalse(capabilities["persistence_is_live_database"])
        self.assertFalse(capabilities["schema_applied"])
        self.assertEqual(
            capabilities["slots"], ["story_banner", "experience_support"]
        )
        self.assertEqual(capabilities["portrait_is_identity_presentation"], "portrait")
        self.assertNotIn("portrait", capabilities["slots"])

    def test_client_authority_fields_are_ignored(self):
        source_id = self.upload_ready_photo()
        staged = self.application.stage_placement(
            owner_id=OWNER_A,
            payload={
                "owner_user_key": OWNER_B,
                "owner_profile_id": 99,
                "visibility": "public",
                "publish": True,
                "slot": "story_banner",
                "source": {"kind": SOURCE_KIND_OWNER_PHOTO, "source_id": source_id},
                "crop": self.default_crop("story_banner", 1200, 800),
                "alt_text": "",
                "decorative": True,
            },
        )
        self.assertEqual(staged["asset_id"], source_id)
        self.assertNotIn("visibility", staged)
        self.assertNotIn("publish", staged)

    def test_sql_media_draft_store_fails_closed_and_maps_outcomes(self):
        class FakeDatabase:
            def __init__(self, result=None, error=None):
                self.result = result
                self.error = error
                self.calls = []

            def execute_procedure(self, procedure, parameters=None):
                self.calls.append((procedure, list(parameters or [])))
                if self.error is not None:
                    raise self.error
                return self.result

        store = SqlResumeMediaDraftStore(FakeDatabase(error=ValueError("unapplied")))
        with self.assertRaises(ResumeMediaRepositoryError) as raised:
            store.load_owner(OWNER_A)
        self.assertEqual(raised.exception.code, "storage-unavailable")

        committed = SqlResumeMediaDraftStore(
            FakeDatabase(result=[[{"outcome": "committed", "committed": True, "replayed": False}]])
        )
        committed.save_owner(
            OWNER_A,
            {
                "_pending_command": {
                    "request_id": str(uuid4()),
                    "command_json": "{}",
                }
            },
        )

        stale = SqlResumeMediaDraftStore(
            FakeDatabase(result=[[{"outcome": "stale_draft"}]])
        )
        with self.assertRaises(ResumeMediaRepositoryError) as stale_error:
            stale.save_owner(
                OWNER_A,
                {"_pending_command": {"request_id": str(uuid4()), "command_json": "{}"}},
            )
        self.assertEqual(stale_error.exception.code, "stale-draft")

        conflict = SqlResumeMediaDraftStore(
            FakeDatabase(result=[[{"outcome": "idempotency_conflict"}]])
        )
        with self.assertRaises(ResumeMediaRepositoryError) as conflict_error:
            conflict.save_owner(
                OWNER_A,
                {"_pending_command": {"request_id": str(uuid4()), "command_json": "{}"}},
            )
        self.assertEqual(conflict_error.exception.code, "idempotency-conflict")

    def test_sql_adapter_reads_owner_scoped_placements(self):
        class FakeDatabase:
            def execute_procedure(self, procedure, parameters=None):
                self.procedure = procedure
                self.parameters = parameters
                return [
                    [{"draft_version": 3, "base_publication_version": None, "media_generation": 2}],
                    [
                        {
                            "slot": "story_banner",
                            "source_kind": SOURCE_KIND_OWNER_PHOTO,
                            "asset_id": SOURCE_KEY,
                            "asset_version": 2,
                            "asset_digest": "d" * 64,
                            "crop_x": 0,
                            "crop_y": 0.2,
                            "crop_width": 1,
                            "crop_height": 0.59,
                            "presentation_version": 1,
                            "alt_text": "",
                            "decorative": True,
                            "provenance_label": "Member photo",
                            "caption": None,
                        }
                    ],
                    [
                        {
                            "command_type": "add_media",
                            "request_uuid": "22222222-2222-4222-8222-222222222222",
                            "semantic_digest": "e" * 64,
                            "outcome_json": '{"outcome": "committed", "draft_version": 3}',
                        }
                    ],
                ]

        database = FakeDatabase()
        store = SqlResumeMediaDraftStore(database)
        snapshot = store.load_owner(OWNER_A)
        self.assertEqual(snapshot["draft_version"], 3)
        self.assertEqual(len(snapshot["media"]["placements"]), 1)
        self.assertIn("add_media:22222222-2222-4222-8222-222222222222", snapshot["media_receipts"])
        self.assertEqual(database.parameters, [("@UserKey", OWNER_A)])


class RepositoryBindingTests(unittest.TestCase):
    def test_binding_refuses_a_missing_store_or_source_repository(self):
        sources = InMemoryResumeMediaRepository()
        with self.assertRaises(ResumeMediaApplicationUnavailable):
            ResumeDraftBoundMediaRepository(draft_store=None, sources=sources)
        with self.assertRaises(ResumeMediaApplicationUnavailable):
            ResumeDraftBoundMediaRepository(
                draft_store=InMemoryResumeDraftRepository(), sources=None
            )


class SqlMediaAdapterContractTests(unittest.TestCase):
    """The durable adapter's replay and refusal contract, without an engine."""

    OWNER = OWNER_A
    REQUEST = "22222222-2222-4222-8222-222222222222"
    DIGEST = "c" * 64

    def database(self, *, version, receipts):
        class FakeDatabase:
            def __init__(self):
                self.calls = []
                self.result = None

            def execute_procedure(self, procedure, parameters=None):
                self.calls.append((procedure, list(parameters or [])))
                if procedure == "usp_GetResumeMediaDraftForOwner":
                    return [
                        [
                            {
                                "draft_version": version,
                                "base_publication_version": None,
                                "media_generation": len(receipts),
                            }
                        ],
                        [],
                        receipts,
                    ]
                return self.result

        return FakeDatabase()

    def receipt_row(self, *, digest, command_type="add_media", outcome=None):
        return {
            "command_type": command_type,
            "request_uuid": self.REQUEST,
            "semantic_digest": digest,
            "outcome_json": outcome
            or '{"command": "add_media", "outcome": "committed", "draft_version": 2}',
        }

    def test_exact_replay_resolves_after_the_version_moved_on(self):
        database = self.database(
            version=3, receipts=[self.receipt_row(digest=self.DIGEST)]
        )
        store = SqlResumeMediaDraftStore(database)
        applied = {"ran": False}

        def apply(live):
            stored = (live.get("media_receipts") or {}).get(
                f"add_media:{self.REQUEST}"
            )
            self.assertIsNotNone(stored)
            self.assertEqual(stored["semantic_digest"], self.DIGEST)
            applied["ran"] = True
            return False

        snapshot = store.commit_owner_command(
            self.OWNER, expected_version=1, apply=apply
        )
        # The version fence (1 vs stored 3) must not turn a confirmed replay
        # into a stale-draft conflict, and nothing is written again.
        self.assertTrue(applied["ran"])
        self.assertEqual(snapshot["draft_version"], 3)
        procedures = [name for name, _ in database.calls]
        self.assertNotIn("usp_CommitResumeMediaCommandForOwner", procedures)

    def test_same_key_with_a_different_digest_is_refused(self):
        database = self.database(
            version=3, receipts=[self.receipt_row(digest="d" * 64)]
        )
        store = SqlResumeMediaDraftStore(database)

        def apply(live):
            stored = (live.get("media_receipts") or {}).get(
                f"add_media:{self.REQUEST}"
            )
            if stored["semantic_digest"] != self.DIGEST:
                raise ResumeMediaRepositoryError("idempotency-conflict")
            return False

        with self.assertRaises(ResumeMediaRepositoryError) as raised:
            store.commit_owner_command(self.OWNER, expected_version=1, apply=apply)
        self.assertEqual(raised.exception.code, "idempotency-conflict")

    def test_stale_new_command_still_conflicts(self):
        database = self.database(version=3, receipts=[])
        store = SqlResumeMediaDraftStore(database)

        def apply(live):
            return True

        with self.assertRaises(ResumeDraftVersionConflict):
            store.commit_owner_command(self.OWNER, expected_version=1, apply=apply)
        self.assertNotIn(
            "usp_CommitResumeMediaCommandForOwner",
            [name for name, _ in database.calls],
        )

    def test_procedure_refusals_map_to_stable_conflicts(self):
        for outcome, expected_code in (
            ("stale_draft", "stale-draft"),
            ("idempotency_conflict", "idempotency-conflict"),
            ("source_changed", "source-changed"),
            ("source_unavailable", "source-unavailable"),
            ("something_else", "storage-unavailable"),
        ):
            with self.subTest(outcome=outcome):
                database = self.database(version=0, receipts=[])
                database.result = [[{"outcome": outcome}]]
                store = SqlResumeMediaDraftStore(database)
                with self.assertRaises(ResumeMediaRepositoryError) as raised:
                    store.save_owner(
                        self.OWNER,
                        {
                            "_pending_command": {
                                "request_id": self.REQUEST,
                                "command_json": "{}",
                            }
                        },
                    )
                self.assertEqual(raised.exception.code, expected_code)

    def test_procedure_accepts_committed_and_replayed_outcomes(self):
        for outcome in ("committed", "replayed"):
            with self.subTest(outcome=outcome):
                database = self.database(version=0, receipts=[])
                database.result = [[{"outcome": outcome}]]
                store = SqlResumeMediaDraftStore(database)
                store.save_owner(
                    self.OWNER,
                    {
                        "_pending_command": {
                            "request_id": self.REQUEST,
                            "command_json": "{}",
                        }
                    },
                )


class SqlDraftAdapterContractTests(unittest.TestCase):
    """The text adapter delegates final replay/version arbitration to SQL."""

    OWNER = OWNER_A
    REQUEST = "33333333-3333-4333-8333-333333333333"

    class FakeDatabase:
        def __init__(self, *, version, commit_row, receipts=None):
            self.version = version
            self.commit_row = commit_row
            self.receipts = list(receipts or [])
            self.calls = []

        def execute_procedure(self, procedure, parameters=None):
            self.calls.append((procedure, list(parameters or [])))
            if procedure == "usp_GetResumeDraftForOwner":
                return [[{
                    "draft_version": self.version,
                    "command_receipts_json": json.dumps(self.receipts),
                }], []]
            return [[dict(self.commit_row)]]

    def prepared_apply(self, live):
        live["_pending_command"] = {
            "request_id": self.REQUEST,
            "command_json": (
                '{"expected_draft_version":1,"record_key":'
                '"44444444-4444-4444-8444-444444444444",'
                '"type":"discard_item"}'
            ),
        }
        return True

    def test_exact_replay_reaches_the_procedure_before_a_local_stale_refusal(self):
        database = self.FakeDatabase(
            version=3,
            commit_row={"committed": True, "replayed": True, "outcome": "discarded"},
        )
        store = SqlResumeDraftRepository(database)
        snapshot = store.commit_owner_command(
            self.OWNER, expected_version=1, apply=self.prepared_apply
        )
        self.assertEqual(snapshot["draft_version"], 3)
        self.assertIn(
            "usp_CommitResumeDraftCommandForOwner",
            [name for name, _ in database.calls],
        )

    def test_two_result_reader_restores_durable_receipts_for_service_replay(self):
        digest = "a" * 64
        database = self.FakeDatabase(
            version=3,
            commit_row={"committed": True, "outcome": "discarded"},
            receipts=[{
                "request_id": self.REQUEST,
                "request_digest": digest,
                "outcome": "discarded",
            }],
        )
        snapshot = SqlResumeDraftRepository(database).load_owner(self.OWNER)
        self.assertEqual(snapshot["draft_version"], 3)
        self.assertEqual(
            snapshot["receipts"][self.REQUEST],
            {"request_digest": digest, "outcome": "discarded"},
        )

    def test_stale_and_changed_replays_map_to_stable_adapter_conflicts(self):
        cases = (
            (
                {
                    "committed": False,
                    "outcome": "stale_draft",
                    "current_draft_version": 3,
                    "expected_draft_version": 1,
                },
                ResumeDraftVersionConflict,
            ),
            (
                {"committed": False, "outcome": "idempotency_conflict"},
                ResumeDraftIdempotencyConflict,
            ),
        )
        for row, expected in cases:
            with self.subTest(outcome=row["outcome"]):
                store = SqlResumeDraftRepository(
                    self.FakeDatabase(version=3, commit_row=row)
                )
                with self.assertRaises(expected):
                    store.commit_owner_command(
                        self.OWNER, expected_version=1, apply=self.prepared_apply
                    )


class AtomicCommandBoundaryTests(MediaApplicationTestCase):
    """The source-eligibility and version fences live inside one atomic write."""

    def second_service_over_the_same_store(self):
        """A second, independent writer sharing only the draft store."""

        return build_resume_media_application(
            draft_store=self.draft_store,
            sources=self.sources,
            storage=self.storage,
            photo_readiness=ResumePhotoReadinessAdapter(
                capture=PhotoCaptureResumeReadinessPort(self.capture)
            ),
            persistence_label="in_memory_not_live_db",
            catalog_label="synthetic_test_catalog",
        )

    def test_source_revoked_inside_the_commit_boundary_rolls_back(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        before = self.draft_store.load_owner(OWNER_A)
        binding = self.application.media_repository

        def revoke_at_the_write():
            # Lands after the service's own validation and after the version
            # fence, at the exact moment of the atomic write.
            self.sources.update_owner_photo(
                owner_id=OWNER_A,
                source_id=source_id,
                lifecycle=LIFECYCLE_RESTRICTED,
            )

        binding.on_commit_entry = revoke_at_the_write
        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(
                self.photo_choice(source_id, "experience_support"),
                expected_draft_version=1,
            )
        self.assertEqual(raised.exception.code, "source-restricted")
        self.assertEqual(self.draft_store.load_owner(OWNER_A), before)
        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertIsNone(workspace["slots"]["experience_support"])
        self.assertEqual(workspace["draft_version"], 1)

    def test_source_replaced_inside_the_commit_boundary_rolls_back(self):
        source_id = self.upload_ready_photo()
        before = self.draft_store.load_owner(OWNER_A)
        binding = self.application.media_repository

        def replace_at_the_write():
            record = self.sources.get_owner_photo(OWNER_A, source_id)
            self.sources.update_owner_photo(
                owner_id=OWNER_A,
                source_id=source_id,
                version=int(record.version) + 1,
                digest="a" * 64,
            )

        binding.on_commit_entry = replace_at_the_write
        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(
                self.photo_choice(source_id, "story_banner"),
                expected_draft_version=0,
            )
        self.assertEqual(raised.exception.code, "stale-version")
        self.assertEqual(self.draft_store.load_owner(OWNER_A), before)

    def test_withdrawn_catalog_asset_inside_the_commit_boundary_rolls_back(self):
        self.seed_art()
        before = self.draft_store.load_owner(OWNER_A)
        self.application.media_repository.on_commit_entry = lambda: (
            self.sources.set_catalog_lifecycle(
                asset_id="art-forest", version=1, lifecycle=LIFECYCLE_WITHDRAWN
            )
        )
        with self.assertRaises(ResumeMediaConflict) as raised:
            self.add_choices(
                {
                    "slot": "experience_support",
                    "source": {
                        "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
                        "asset_id": "art-forest",
                        "asset_version": 1,
                    },
                    "crop": self.default_crop("experience_support", 1600, 900),
                    "alt_text": "",
                    "decorative": True,
                },
                expected_draft_version=0,
            )
        self.assertEqual(raised.exception.code, "asset-withdrawn")
        self.assertEqual(self.draft_store.load_owner(OWNER_A), before)

    def test_two_repository_instances_cannot_both_commit_one_version(self):
        source_id = self.upload_ready_photo()
        second = self.second_service_over_the_same_store()
        self.assertIsNot(self.application.media_repository, second.media_repository)

        choice = self.photo_choice(source_id, "story_banner")
        other = self.photo_choice(source_id, "experience_support")
        barrier = threading.Barrier(2)
        outcomes = []

        def attempt(application, payload):
            barrier.wait(timeout=5)
            try:
                outcomes.append(
                    ("ok", application.add_media(owner_id=OWNER_A, payload=payload))
                )
            except ResumeMediaConflict as error:
                outcomes.append(("conflict", error.code))

        threads = [
            threading.Thread(
                target=attempt,
                args=(
                    self.application,
                    {
                        "type": "add_media",
                        "request_id": str(uuid4()),
                        "expected_draft_version": 0,
                        "choices": [choice],
                    },
                ),
            ),
            threading.Thread(
                target=attempt,
                args=(
                    second,
                    {
                        "type": "add_media",
                        "request_id": str(uuid4()),
                        "expected_draft_version": 0,
                        "choices": [other],
                    },
                ),
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        winners = [entry for entry in outcomes if entry[0] == "ok"]
        losers = [entry for entry in outcomes if entry[0] == "conflict"]
        self.assertEqual(len(winners), 1, outcomes)
        self.assertEqual(len(losers), 1, outcomes)
        self.assertEqual(losers[0][1], "stale-draft")
        stored = self.draft_store.load_owner(OWNER_A)
        self.assertEqual(stored["draft_version"], 1)
        # Exactly one winner's placement and exactly one receipt survived: no
        # successful outcome pointed at a write that disappeared.
        self.assertEqual(len(stored["media"]["placements"]), 1)
        self.assertEqual(len(stored["media_receipts"]), 1)

    def test_text_save_and_media_add_race_leaves_exactly_one_winner(self):
        source_id = self.upload_ready_photo()
        record_key = str(uuid4())
        canonical = InMemoryCanonicalCatalog()
        canonical.put_item(
            OWNER_A,
            {
                "record_key": record_key,
                "record_type": "skill",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": {"name": "Systems engineering"},
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )
        text_service = ResumeDraftService(
            repository=self.draft_store, catalog=canonical
        )
        barrier = threading.Barrier(2)
        outcomes = []

        def media_attempt():
            barrier.wait(timeout=5)
            try:
                outcomes.append(
                    (
                        "media",
                        self.application.add_media(
                            owner_id=OWNER_A,
                            payload={
                                "type": "add_media",
                                "request_id": str(uuid4()),
                                "expected_draft_version": 0,
                                "choices": [self.photo_choice(source_id, "story_banner")],
                            },
                        ),
                    )
                )
            except (ResumeMediaConflict, ResumeDraftConflictError) as error:
                outcomes.append(("media-conflict", getattr(error, "code", "changed")))

        def text_attempt():
            barrier.wait(timeout=5)
            try:
                outcomes.append(
                    (
                        "text",
                        text_service.commit(
                            OWNER_A,
                            {
                                "request_id": str(uuid4()),
                                "type": "save_item",
                                "record_key": record_key,
                                "record_type": "skill",
                                "expected_content_token": "1",
                                "expected_access_revision": 1,
                                "expected_draft_version": 0,
                                "values": {"name": "Requirements management"},
                            },
                        ),
                    )
                )
            except ResumeDraftConflictError as error:
                outcomes.append(("text-conflict", error.error_code))

        threads = [threading.Thread(target=media_attempt), threading.Thread(target=text_attempt)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        winners = [entry for entry in outcomes if entry[0] in {"media", "text"}]
        self.assertEqual(len(winners), 1, outcomes)
        stored = self.draft_store.load_owner(OWNER_A)
        placed = bool((stored.get("media") or {}).get("placements"))
        recorded = record_key in (stored.get("items") or {})
        if winners[0][0] == "media":
            self.assertTrue(placed)
            self.assertFalse(recorded)
            self.assertEqual(stored["draft_version"], 1)
        else:
            self.assertTrue(recorded)
            self.assertFalse(placed)
            self.assertEqual(stored["draft_version"], 1)

    def test_text_save_conflict_is_reported_not_silently_merged(self):
        source_id = self.upload_ready_photo()
        stale_text_snapshot = self.draft_service._load(OWNER_A)
        self.assertEqual(stale_text_snapshot["draft_version"], 0)
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        # The text command loaded version 0 before the media Add landed; its
        # atomic apply must refuse rather than overwrite the media placement.
        with self.assertRaises(ResumeDraftConflictError) as raised:
            self.draft_service._save_shared_draft(
                OWNER_A,
                {
                    **stale_text_snapshot,
                    "items": {},
                    "draft_version": 1,
                    "receipts": {},
                    "_base_version": 0,
                },
                {"record_key": None, "request_id": str(uuid4()), "values": None},
            )
        self.assertEqual(raised.exception.error_code, "changed")
        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertTrue(workspace["slots"]["story_banner"])
        self.assertEqual(workspace["draft_version"], 1)

    def test_store_without_the_atomic_contract_fails_closed(self):
        class LegacyStore(InMemoryResumeDraftRepository):
            atomic_command_supported = False

        with self.assertRaises(ResumeMediaApplicationUnavailable):
            ResumeDraftBoundMediaRepository(
                draft_store=LegacyStore(), sources=self.sources
            )

    def test_source_mutation_after_the_source_read_waits_for_the_commit(self):
        """A restriction cannot land between the commit's read and its write."""

        source_id = self.upload_ready_photo()
        binding = self.application.media_repository
        read_complete = threading.Event()
        mutation_attempted = threading.Event()
        mutation_done = threading.Event()
        observed = {}

        def after_source_read():
            read_complete.set()
            mutation_attempted.wait(timeout=5)
            # If the mutation is really serialized it is still blocked on the
            # source lifecycle guard while this window is open.
            time.sleep(0.3)
            observed["completed_during_commit"] = mutation_done.is_set()

        binding.on_after_source_read = after_source_read
        timings = {}

        def mutate():
            read_complete.wait(timeout=5)
            mutation_attempted.set()
            started = time.monotonic()
            self.sources.update_owner_photo(
                owner_id=OWNER_A,
                source_id=source_id,
                lifecycle=LIFECYCLE_RESTRICTED,
            )
            timings["elapsed"] = time.monotonic() - started
            mutation_done.set()

        mutation_thread = threading.Thread(target=mutate)
        mutation_thread.start()
        result = self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        mutation_thread.join(timeout=10)
        self.assertFalse(mutation_thread.is_alive())

        # The restriction landed only after the commit released the guard, so
        # the commit's own source read was true at commit time...
        self.assertFalse(observed.get("completed_during_commit", True))
        self.assertGreaterEqual(timings.get("elapsed", 0.0), 0.2)
        self.assertEqual(result["outcome"], "committed")
        # ...and the restriction that arrived afterwards takes effect at once:
        # the persisted placement is not servable any more.
        record = self.sources.get_owner_photo(OWNER_A, source_id)
        self.assertEqual(record.lifecycle, LIFECYCLE_RESTRICTED)
        self.assertIsNone(
            self.application.open_draft_placement_media(
                owner_id=OWNER_A, slot="story_banner"
            )
        )
        entry = self.application.workspace(owner_id=OWNER_A)["slots"]["story_banner"]
        self.assertTrue(entry)
        self.assertFalse(entry["media_available"])

    def test_source_repository_without_a_lifecycle_guard_fails_closed(self):
        # A repository that cannot offer a real source-lifecycle fence is not
        # accepted as the authoritative fence for a shared-draft commit.
        with self.assertRaises(ResumeMediaApplicationUnavailable):
            ResumeDraftBoundMediaRepository(
                draft_store=InMemoryResumeDraftRepository(), sources=object()
            )

    def test_shared_marker_on_an_unsupported_store_refuses_a_text_save(self):
        class LegacyStore(InMemoryResumeDraftRepository):
            atomic_command_supported = False

        store = LegacyStore()
        service = ResumeDraftService(
            repository=store, catalog=InMemoryCanonicalCatalog()
        )
        setattr(store, SHARED_MEDIA_STATE_ATTRIBUTE, True)
        with self.assertRaises(ResumeDraftUnavailableError):
            service.commit(
                OWNER_A,
                {
                    "request_id": str(uuid4()),
                    "type": "create_private_item",
                    "record_key": str(uuid4()),
                    "record_type": "skill",
                    "values": {"name": "Systems engineering"},
                },
            )


class PersistedDraftMediaReadTests(MediaApplicationTestCase):
    """Owner-authorized bytes for a placement already saved in the draft."""

    def test_draft_media_read_serves_saved_bytes_and_uses_the_persisted_draft(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        # The pending preview is gone after Add; the persisted draft still
        # serves the exact bytes.
        self.assertIsNone(
            self.application.open_placement_media(owner_id=OWNER_A, slot="story_banner")
        )
        opened = self.application.open_draft_placement_media(
            owner_id=OWNER_A, slot="story_banner"
        )
        self.assertIsNotNone(opened)
        self.assertEqual(opened["stream"].read(), self.derivative_payload)
        self.assertEqual(
            opened["byte_length"], len(self.derivative_payload)
        )

    def test_draft_media_read_denies_after_revocation_and_for_another_owner(self):
        source_id = self.upload_ready_photo()
        self.add_choices(
            self.photo_choice(source_id, "story_banner"),
            expected_draft_version=0,
        )
        self.assertIsNone(
            self.application.open_draft_placement_media(
                owner_id=OWNER_B, slot="story_banner"
            )
        )
        self.sources.update_owner_photo(
            owner_id=OWNER_A, source_id=source_id, lifecycle=LIFECYCLE_WITHDRAWN
        )
        self.assertIsNone(
            self.application.open_draft_placement_media(
                owner_id=OWNER_A, slot="story_banner"
            )
        )

    def test_draft_media_read_for_a_catalog_placement_serves_catalog_bytes(self):
        self.seed_art()
        self.add_choices(
            {
                "slot": "experience_support",
                "source": {
                    "kind": SOURCE_KIND_GENERATED_ILLUSTRATION,
                    "asset_id": "art-forest",
                    "asset_version": 1,
                },
                "crop": self.default_crop("experience_support", 1600, 900),
                "alt_text": "",
                "decorative": True,
            },
            expected_draft_version=0,
        )
        opened = self.application.open_draft_placement_media(
            owner_id=OWNER_A, slot="experience_support"
        )
        self.assertEqual(opened["stream"].read(), b"catalog-bytes-experience_support")


if __name__ == "__main__":
    unittest.main()
