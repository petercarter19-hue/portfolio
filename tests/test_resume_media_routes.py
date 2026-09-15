"""Real Flask HTTP journeys for the MVP1 D private Resume media chooser.

These issue actual requests through Flask's test client, including real
multipart uploads whose bytes reach the real Photo Capture orchestration with
injected lower boundaries. They are not browser proof, SQL engine proof or live
storage/identity proof, and the injected in-memory stores are labelled
synthetic.
"""

from __future__ import annotations

import hashlib
import io
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from PIL import Image

from app import app, limiter
from services.photo_capture_service import PhotoCaptureService, normalize_photo
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_media_application import (
    PhotoCaptureResumeReadinessPort,
    ResumeMediaApplicationService,
    build_resume_media_application,
)
from services.resume_media_repository import (
    InMemoryMediaStorage,
    InMemoryResumeMediaRepository,
    LIFECYCLE_WITHDRAWN,
    READINESS_READY,
    ResumeMediaRepositoryError,
)
from services.resume_media_service import (
    ResumeMediaError,
    ResumeMediaService,
    ResumePhotoReadinessAdapter,
)


OWNER_A = "media-routes-member-a"
OWNER_B = "media-routes-member-b"
SOURCE_KEY = "11111111-1111-4111-8111-111111111111"

CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_RESUME_MEDIA_ENABLED",
    "RESUME_MEDIA_SERVICE",
)


def image_bytes(image_format="JPEG", size=(1200, 800)):
    payload = io.BytesIO()
    Image.new("RGB", size, (36, 78, 66)).save(payload, format=image_format)
    return payload.getvalue()


class FailingCatalogRepository(InMemoryResumeMediaRepository):
    """Synthetic catalogue outage used to prove honest error states."""

    FAILING_QUERY = "__catalog-unavailable__"

    def list_catalog(self, **kwargs):
        if kwargs.get("query") == self.FAILING_QUERY:
            raise ResumeMediaRepositoryError("catalog-unavailable")
        return super().list_catalog(**kwargs)


class SyntheticPhotoProcedures:
    def __init__(self, storage):
        self.storage = storage
        self.calls = []

    def bound(self, procedure):
        return [dict(params) for name, params in self.calls if name == procedure]

    def first_row(self, procedure, parameters=None):
        self.calls.append((procedure, list(parameters or [])))
        if procedure == "usp_CreatePhotoSource":
            return {"outcome": "created", "source_key": SOURCE_KEY, "row_version": b"\x01" * 8}
        if procedure == "usp_MarkPhotoUploaded":
            return {"outcome": "scanning", "row_version": b"\x02" * 8}
        if procedure == "usp_GetPhotoSourceForOwner":
            if any(name == "usp_CompletePhotoProcessing" for name, _ in self.calls):
                return self._ready_row()
            return {
                "source_key": SOURCE_KEY,
                "state": "scanning",
                "row_version": b"\x02" * 8,
                "pixel_width": 0,
                "pixel_height": 0,
            }
        if procedure == "usp_GetPhotoProcessingSourceForOwner":
            parameters = self.bound("usp_CreatePhotoSource")[0]
            record = self.storage.objects[parameters["@OriginalBlobName"]]
            return {
                "source_key": SOURCE_KEY,
                "state": "scanning",
                "original_blob_name": parameters["@OriginalBlobName"],
                "derivative_blob_name": parameters["@DerivativeBlobName"],
                "original_content_type": parameters["@OriginalContentType"],
                "original_byte_length": len(record["data"]),
                "original_sha256_digest": hashlib.sha256(record["data"]).digest(),
                "original_blob_etag": record["etag"],
                "row_version": b"\x02" * 8,
            }
        if procedure == "usp_RecordPhotoScanResult":
            parameters = self.bound("usp_CreatePhotoSource")[0]
            record = self.storage.objects[parameters["@OriginalBlobName"]]
            return {
                "outcome": "processing",
                "original_blob_name": parameters["@OriginalBlobName"],
                "original_content_type": parameters["@OriginalContentType"],
                "original_byte_length": len(record["data"]),
                "original_sha256_digest": hashlib.sha256(record["data"]).digest(),
                "original_blob_etag": record["etag"],
                "derivative_blob_name": parameters["@DerivativeBlobName"],
                "row_version": b"\x03" * 8,
            }
        if procedure == "usp_CompletePhotoProcessing":
            return {"outcome": "needs_review"}
        if procedure == "usp_GetPhotoMediaForOwner":
            return self._media_row()
        return None

    def _ready_row(self):
        parameters = self.bound("usp_CreatePhotoSource")[0]
        record = self.storage.objects[parameters["@DerivativeBlobName"]]
        return {
            "source_key": SOURCE_KEY,
            "state": "needs_review",
            "row_version": b"\x04" * 8,
            "pixel_width": 1200,
            "pixel_height": 800,
            "derivative_content_type": record["content_type"],
            "derivative_byte_length": len(record["data"]),
            "derivative_blob_name": parameters["@DerivativeBlobName"],
            "scan_result": "clean",
        }

    def _media_row(self):
        parameters = self.bound("usp_CreatePhotoSource")[0]
        ref = parameters["@DerivativeBlobName"]
        record = self.storage.objects[ref]
        return {
            "source_key": SOURCE_KEY,
            "blob_name": ref,
            "content_type": record["content_type"],
            "byte_length": len(record["data"]),
            "sha256_digest": hashlib.sha256(record["data"]).digest(),
        }


class SyntheticRouteStorage:
    """Synthetic private storage double for both Photo Capture and catalog reads."""

    def __init__(self):
        self.objects = {}
        self.uploads = []

    def upload(self, ref, data, content_type):
        etag = '"etag-%d"' % (len(self.uploads) + 1)
        self.uploads.append(ref)
        self.objects[ref] = {
            "data": bytes(data),
            "content_type": str(content_type),
            "etag": etag,
        }
        return {"etag": etag}

    def download(self, ref):
        record = self.objects[ref]
        return {
            "data": record["data"],
            "byte_length": len(record["data"]),
            "content_type": record["content_type"],
            "etag": record["etag"],
        }

    def get_scan_result(self, ref):
        return {"result": "clean", "scan_time_utc": datetime.now(timezone.utc)}

    def exists(self, ref):
        return ref in self.objects

    def delete(self, ref):
        self.objects.pop(ref, None)


class ResumeMediaRoutesTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {key: app.config.get(key) for key in CONFIG_KEYS}
        self.limiter_was_enabled = limiter.enabled
        limiter.enabled = False
        self.addCleanup(self._restore)

        self.capture_storage = SyntheticRouteStorage()
        self.procedures = SyntheticPhotoProcedures(self.capture_storage)
        self.capture = PhotoCaptureService(
            database=self.procedures, storage=self.capture_storage
        )
        self.sources = FailingCatalogRepository()
        self.storage = InMemoryMediaStorage()
        self.draft_store = InMemoryResumeDraftRepository()
        self.draft_service = ResumeDraftService(
            repository=self.draft_store, catalog=InMemoryCanonicalCatalog()
        )
        self.readiness = ResumePhotoReadinessAdapter(
            capture=PhotoCaptureResumeReadinessPort(self.capture)
        )
        self.application = build_resume_media_application(
            draft_store=self.draft_store,
            sources=self.sources,
            storage=self.storage,
            photo_readiness=self.readiness,
            persistence_label="in_memory_not_live_db",
            catalog_label="synthetic_test_catalog",
        )
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=OWNER_A,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_MEDIA_ENABLED=True,
            RESUME_MEDIA_SERVICE=self.application,
        )
        self.client = app.test_client()

    def _restore(self):
        app.config.update(self.original_config)
        limiter.enabled = self.limiter_was_enabled

    # -- helpers -----------------------------------------------------------

    def headers(self, origin=None):
        result = {"X-PeerSlate-Request": "same-origin"}
        if origin:
            result["Origin"] = origin
        return result

    def use_owner(self, owner):
        app.config["PEERSLATE_DEV_USER_KEY"] = owner

    def upload(self, *, owner=OWNER_A, payload=None, mimetype="image/jpeg"):
        self.use_owner(owner)
        return self.client.post(
            "/api/resume-media/me/photos",
            data={"photo": (io.BytesIO(payload or image_bytes()), "member-photo.jpg", mimetype)},
            headers=self.headers(),
            content_type="multipart/form-data",
        )

    def ready_photo(self, *, owner=OWNER_A, payload=None):
        source_payload = payload or image_bytes()
        uploaded = self.upload(owner=owner, payload=source_payload)
        self.assertEqual(uploaded.status_code, 200, uploaded.get_data(as_text=True))
        source_id = uploaded.get_json()["source_id"]
        refreshed = self.client.post(
            f"/api/resume-media/me/photos/{source_id}/refresh",
            json={},
            headers=self.headers(),
        )
        self.assertEqual(refreshed.status_code, 200, refreshed.get_data(as_text=True))
        self.assertEqual(refreshed.get_json()["state"], READINESS_READY)
        return source_id, normalize_photo(source_payload, "image/jpeg").data

    def seed_art(self, asset_id="art-forest", *, version=1, label="Forest trail"):
        for slot in ("story_banner", "experience_support"):
            self.storage.put(
                f"catalog/{asset_id}/{version}/{slot}.png",
                b"catalog-bytes-" + slot.encode("ascii"),
                content_type="image/png",
            )
        return self.sources.seed_catalog_asset(
            asset_id=asset_id,
            label=label,
            category="Nature",
            tags=("calm",),
            version=version,
            digest=("%064d" % version),
            provenance={"model": "synthetic-test-model"},
            rights={"rights_id": "synthetic-rights", "approval_state": "approved"},
            derivatives=[
                {
                    "slot": slot,
                    "ref": f"catalog/{asset_id}/{version}/{slot}.png",
                    "digest": self.storage.digest_for(f"catalog/{asset_id}/{version}/{slot}.png"),
                    "content_type": "image/png",
                    "byte_length": len(b"catalog-bytes-" + slot.encode("ascii")),
                }
                for slot in ("story_banner", "experience_support")
            ],
        )

    def stage(self, body, *, owner=OWNER_A):
        self.use_owner(owner)
        return self.client.post(
            "/api/resume-media/me/placements", json=body, headers=self.headers()
        )

    def photo_choice(self, source_id, slot, *, caption=None):
        from services.resume_media_service import centered_slot_crop

        return {
            "slot": slot,
            "source": {"kind": "owner_photo", "source_id": source_id},
            "crop": centered_slot_crop(slot=slot, width=1200, height=800).as_dict(),
            "alt_text": "",
            "decorative": True,
            "caption": caption,
        }

    # -- gating ------------------------------------------------------------

    def test_flag_off_returns_a_neutral_404_for_every_route(self):
        app.config["PEERSLATE_RESUME_MEDIA_ENABLED"] = False
        for method, path in (
            ("get", "/api/resume-media/me/workspace"),
            ("get", "/api/resume-media/me/library"),
            ("get", "/api/resume-media/me/photos/x/preview"),
            ("get", "/api/resume-media/me/placements/story_banner/media"),
            ("get", "/api/resume-media/me/library/art-1/1/thumbnail"),
        ):
            with self.subTest(path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.get_json()["success"], False)
        response = self.client.post(
            "/api/resume-media/me/photos", data={}, headers=self.headers()
        )
        self.assertEqual(response.status_code, 404)

    def test_flag_on_without_configured_service_is_unavailable(self):
        app.config["RESUME_MEDIA_SERVICE"] = None
        response = self.client.get("/api/resume-media/me/workspace")
        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], "unavailable")
        self.assertNotIn("items", payload)

    def test_same_origin_write_guard_and_cross_origin_refusal(self):
        missing = self.client.post("/api/resume-media/me/photos", data={})
        self.assertEqual(missing.status_code, 403)
        cross = self.client.post(
            "/api/resume-media/me/photos",
            data={},
            headers=self.headers(origin="https://example.invalid"),
        )
        self.assertEqual(cross.status_code, 403)
        allowed = self.upload()
        self.assertEqual(allowed.status_code, 200)

    # -- upload / readiness / bytes ---------------------------------------

    def test_upload_reaches_ready_and_preview_returns_the_derivative_bytes(self):
        source_id, derivative = self.ready_photo()

        preview = self.client.get(f"/api/resume-media/me/photos/{source_id}/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.get_data(), derivative)
        self.assertEqual(preview.headers["Content-Type"], "image/jpeg")
        self.assertEqual(preview.headers["Cache-Control"], "private, no-store")
        self.assertEqual(preview.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(preview.headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertNotIn("member-photo", str(preview.headers))

        workspace = self.client.get("/api/resume-media/me/workspace").get_json()
        self.assertEqual(len(workspace["photos"]), 1)
        self.assertTrue(workspace["photos"][0]["selectable"])
        self.assertFalse(workspace["capabilities"]["publishes"])
        self.assertFalse(workspace["capabilities"]["schema_applied"])
        self.assertEqual(workspace["capabilities"]["persistence"], "in_memory_not_live_db")

    def test_procedures_never_confirm_photo_capture(self):
        self.ready_photo()
        called = [name for name, _ in self.procedures.calls]
        self.assertIn("usp_CompletePhotoProcessing", called)
        self.assertNotIn("usp_ConfirmPhotoCapture", called)

    def test_preview_and_unready_source_are_refused_honestly(self):
        self.use_owner(OWNER_A)
        uploaded = self.upload()
        source_id = uploaded.get_json()["source_id"]
        staged = self.stage(
            {
                "slot": "story_banner",
                "source": {"kind": "owner_photo", "source_id": source_id},
                "crop": {"x": 0, "y": 0.25, "width": 1, "height": 0.5},
                "alt_text": "",
                "decorative": True,
            }
        )
        self.assertEqual(staged.status_code, 409)
        self.assertEqual(staged.get_json()["code"], "source-not-ready")
        preview = self.client.get(f"/api/resume-media/me/photos/{source_id}/preview")
        self.assertEqual(preview.status_code, 409)
        self.assertEqual(preview.get_json()["code"], "source-not-ready")

    def test_unsupported_upload_is_refused_without_a_stored_source(self):
        self.use_owner(OWNER_A)
        response = self.upload(payload=b"not-an-image", mimetype="image/png")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "unsupported-source")
        self.assertEqual(self.capture_storage.uploads, [])

    # -- owner isolation and authority ------------------------------------

    def test_owner_isolation_across_real_requests(self):
        source_id, _ = self.ready_photo(owner=OWNER_A)
        self.use_owner(OWNER_B)
        self.assertEqual(
            self.client.get(
                f"/api/resume-media/me/photos/{source_id}/preview"
            ).status_code,
            404,
        )
        foreign_stage = self.stage(
            {
                "slot": "story_banner",
                "source": {"kind": "owner_photo", "source_id": source_id},
                "crop": {"x": 0, "y": 0.25, "width": 1, "height": 0.5},
                "alt_text": "",
                "decorative": True,
            },
            owner=OWNER_B,
        )
        self.assertEqual(foreign_stage.status_code, 404)
        self.use_owner(OWNER_B)
        workspace = self.client.get("/api/resume-media/me/workspace").get_json()
        self.assertEqual(workspace["photos"], [])
        self.assertEqual(workspace["slots"]["story_banner"], None)

    def test_client_authority_fields_never_change_owner_or_visibility(self):
        source_id, _ = self.ready_photo(owner=OWNER_A)
        response = self.stage(
            {
                "owner_user_key": OWNER_B,
                "owner_profile_id": 4242,
                "publication_status": "published",
                "publish": True,
                "slot": "story_banner",
                "source": {"kind": "owner_photo", "source_id": source_id},
                "crop": {"x": 0, "y": 0.25, "width": 1, "height": 0.5},
                "alt_text": "",
                "decorative": True,
            }
        )
        self.assertEqual(response.status_code, 200)
        preview = response.get_json()["preview"]
        self.assertEqual(preview["asset_id"], source_id)
        self.assertNotIn("visibility", preview)
        self.assertFalse(response.get_json()["publishes"])
        # Owner B still sees nothing.
        self.use_owner(OWNER_B)
        self.assertEqual(
            self.client.get("/api/resume-media/me/workspace").get_json()["slots"][
                "story_banner"
            ],
            None,
        )

    # -- library -----------------------------------------------------------

    def test_library_search_empty_error_and_thumbnail_bytes(self):
        self.seed_art()
        page = self.client.get("/api/resume-media/me/library?query=forest").get_json()
        self.assertEqual(len(page["items"]), 1)
        item = page["items"][0]
        self.assertEqual(item["label"], "Forest trail")
        self.assertEqual(item["origin"], "generated_illustration")
        self.assertNotIn("ref", item)
        self.assertNotIn("digest", item)
        self.assertIn("thumbnail_url", item)

        thumbnail = self.client.get(
            f"/api/resume-media/me/library/{item['asset_id']}/{item['asset_version']}/thumbnail"
        )
        self.assertEqual(thumbnail.status_code, 200)
        self.assertEqual(thumbnail.get_data(), b"catalog-bytes-story_banner")
        self.assertEqual(thumbnail.headers["Cache-Control"], "private, no-store")

        empty = self.client.get(
            "/api/resume-media/me/library?query=no-such-illustration"
        ).get_json()
        self.assertEqual(empty["items"], [])
        self.assertEqual(empty["total"], 0)
        self.assertIsNone(empty["next_cursor"])

        unavailable = self.client.get(
            "/api/resume-media/me/library?query="
            + FailingCatalogRepository.FAILING_QUERY
        )
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.get_json()["code"], "catalog-unavailable")

    def test_library_cursor_and_withdrawal_states(self):
        for index in range(4):
            self.seed_art(asset_id=f"art-{index}", label=f"Trail {index}")
        first = self.client.get("/api/resume-media/me/library?limit=2").get_json()
        self.assertEqual(len(first["items"]), 2)
        cursor = first["next_cursor"]
        self.assertIsNotNone(cursor)
        second = self.client.get(
            f"/api/resume-media/me/library?limit=2&cursor={cursor}"
        ).get_json()
        self.assertEqual(len(second["items"]), 2)

        recycled = self.client.get(
            f"/api/resume-media/me/library?limit=2&query=trail&cursor={cursor}"
        )
        self.assertEqual(recycled.status_code, 409)
        malformed = self.client.get("/api/resume-media/me/library?cursor=not-a-cursor")
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.get_json()["code"], "invalid-cursor")

        self.sources.set_catalog_lifecycle(
            asset_id="art-0", version=1, lifecycle=LIFECYCLE_WITHDRAWN
        )
        after = self.client.get("/api/resume-media/me/library").get_json()
        self.assertNotIn("art-0", [item["asset_id"] for item in after["items"]])
        withdrawn = self.client.get("/api/resume-media/me/library/art-0/1/thumbnail")
        self.assertEqual(withdrawn.status_code, 404)

    # -- selection, preview, explicit Add ----------------------------------

    def test_stage_preview_swap_and_slot_local_removal(self):
        source_id, derivative = self.ready_photo()
        self.seed_art()
        staged_photo = self.stage(self.photo_choice(source_id, "story_banner"))
        self.assertEqual(staged_photo.status_code, 200)
        preview = staged_photo.get_json()["preview"]
        self.assertEqual(preview["slot"], "story_banner")
        self.assertEqual(preview["source_kind"], "owner_photo")
        self.assertEqual(
            staged_photo.get_json()["placement_preview_label"],
            "Placement preview · Not added yet",
        )

        staged_art = self.stage(
            {
                "slot": "experience_support",
                "source": {
                    "kind": "generated_illustration",
                    "asset_id": "art-forest",
                    "asset_version": 1,
                },
                "crop": self.photo_choice(source_id, "experience_support")["crop"],
                "alt_text": "",
                "decorative": True,
            }
        )
        self.assertEqual(staged_art.status_code, 200, staged_art.get_data(as_text=True))

        media = self.client.get("/api/resume-media/me/placements/story_banner/media")
        self.assertEqual(media.status_code, 200)
        self.assertEqual(media.get_data(), derivative)
        art_media = self.client.get(
            "/api/resume-media/me/placements/experience_support/media"
        )
        self.assertEqual(art_media.get_data(), b"catalog-bytes-experience_support")

        swapped = self.client.post(
            "/api/resume-media/me/placement-swap", json={}, headers=self.headers()
        )
        self.assertEqual(swapped.status_code, 200)
        slots = swapped.get_json()["slots"]
        self.assertEqual(slots["story_banner"]["source_kind"], "generated_illustration")
        self.assertEqual(slots["experience_support"]["source_kind"], "owner_photo")
        self.assertEqual(
            self.client.get("/api/resume-media/me/workspace").get_json()["draft_version"],
            0,
        )

        removed = self.client.delete(
            "/api/resume-media/me/placements/story_banner", headers=self.headers()
        )
        self.assertEqual(removed.status_code, 200)
        self.assertTrue(removed.get_json()["removed"])
        self.assertIsNone(
            self.client.get(
                "/api/resume-media/me/placements/story_banner"
            ).get_json()["preview"]
        )
        remaining = self.client.get(
            "/api/resume-media/me/placements/experience_support"
        ).get_json()["preview"]
        self.assertEqual(remaining["source_kind"], "owner_photo")

    def test_portrait_can_never_be_a_placement_slot(self):
        source_id, _ = self.ready_photo()
        response = self.stage(
            {
                "slot": "portrait",
                "source": {"kind": "owner_photo", "source_id": source_id},
                "crop": {"x": 0, "y": 0.25, "width": 1, "height": 0.5},
                "alt_text": "",
                "decorative": True,
            }
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "slot-not-allowed")
        self.assertIn("identity presentation", response.get_json()["message"])

    def test_invalid_crop_geometry_is_refused_without_staging(self):
        source_id, _ = self.ready_photo()
        cases = (
            {"x": 0, "y": 0, "width": 0.4, "height": 0.5},
            {"x": 0.9, "y": 0, "width": 0.5, "height": 0.5},
            {"x": 0, "y": 0, "width": float("nan"), "height": 1},
            {"x": 0, "y": 0, "width": 1, "height": 1},
        )
        for crop in cases:
            with self.subTest(crop=crop):
                response = self.stage(
                    {
                        "slot": "story_banner",
                        "source": {"kind": "owner_photo", "source_id": source_id},
                        "crop": crop,
                        "alt_text": "",
                        "decorative": True,
                    }
                )
                self.assertIn(response.status_code, (400, 409))
        self.assertIsNone(
            self.client.get(
                "/api/resume-media/me/placements/story_banner"
            ).get_json()["preview"]
        )

    def test_explicit_add_is_idempotent_and_conflicts_on_a_changed_payload(self):
        source_id, _ = self.ready_photo()
        request_id = str(uuid4())
        body = {
            "type": "add_media",
            "request_id": request_id,
            "expected_draft_version": 0,
            "choices": [self.photo_choice(source_id, "story_banner", caption="My caption")],
        }
        first = self.client.post(
            "/api/resume-media/me/commands", json=body, headers=self.headers()
        )
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))
        payload = first.get_json()
        self.assertEqual(payload["draft_version"], 1)
        self.assertFalse(payload["publishes"])
        self.assertEqual(payload["workspace"]["draft_version"], 1)
        self.assertEqual(
            payload["workspace"]["slots"]["story_banner"]["caption"], "My caption"
        )

        replay = self.client.post(
            "/api/resume-media/me/commands", json=body, headers=self.headers()
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.get_json()["draft_version"], 1)
        self.assertEqual(
            self.client.get("/api/resume-media/me/workspace").get_json()["draft_version"],
            1,
        )

        changed = dict(body)
        changed["choices"] = [
            self.photo_choice(source_id, "experience_support", caption="Different")
        ]
        conflict = self.client.post(
            "/api/resume-media/me/commands", json=changed, headers=self.headers()
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["code"], "idempotency-conflict")

    def test_stale_draft_and_missing_request_id_are_refused(self):
        source_id, _ = self.ready_photo()
        stale = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 7,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["error_code"], "stale-draft")
        self.assertEqual(
            self.client.get("/api/resume-media/me/workspace").get_json()["draft_version"],
            0,
        )

        invalid = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": "not-a-uuid",
                "expected_draft_version": 0,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()["code"], "invalid-request")

        unknown = self.client.post(
            "/api/resume-media/me/commands",
            json={"type": "publish_media"},
            headers=self.headers(),
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.get_json()["code"], "invalid-command")

    def test_keep_words_only_discards_pending_choices_and_keeps_saved_media(self):
        source_id, _ = self.ready_photo()
        self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        self.stage(self.photo_choice(source_id, "experience_support"))
        kept = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "keep_words_only",
                "request_id": str(uuid4()),
                "expected_draft_version": 1,
            },
            headers=self.headers(),
        )
        self.assertEqual(kept.status_code, 200, kept.get_data(as_text=True))
        workspace = kept.get_json()["workspace"]
        self.assertEqual(workspace["draft_version"], 2)
        self.assertEqual(workspace["staged"], {})
        self.assertTrue(workspace["slots"]["story_banner"])
        self.assertIsNone(workspace["slots"]["experience_support"])

    def test_review_command_reports_a_digest_and_never_publishes(self):
        source_id, _ = self.ready_photo()
        self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        reviewed = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "review_media",
                "expected_draft_version": 1,
                "expected_publication_version": 0,
            },
            headers=self.headers(),
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.get_data(as_text=True))
        payload = reviewed.get_json()
        self.assertFalse(payload["publishes"])
        self.assertEqual(payload["draft_version"], 1)
        self.assertEqual(payload["publication_version"], 0)
        self.assertTrue(payload["reviewed_digest"])
        self.assertNotIn("digest", payload["slots"]["story_banner"])
        self.assertNotIn("asset_digest", payload["slots"]["story_banner"])
        self.assertEqual(
            self.client.get("/api/resume-media/me/workspace").get_json()["draft_version"],
            1,
        )

    def test_removing_a_saved_slot_leaves_the_other_slot_and_never_publishes(self):
        source_id, _ = self.ready_photo()
        self.seed_art()
        self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [
                    self.photo_choice(source_id, "story_banner"),
                    {
                        "slot": "experience_support",
                        "source": {
                            "kind": "generated_illustration",
                            "asset_id": "art-forest",
                            "asset_version": 1,
                        },
                        "crop": self.photo_choice(source_id, "experience_support")["crop"],
                        "alt_text": "",
                        "decorative": True,
                    },
                ],
            },
            headers=self.headers(),
        )
        removed = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 1,
                "choices": [{"slot": "story_banner", "source": None}],
            },
            headers=self.headers(),
        )
        self.assertEqual(removed.status_code, 200, removed.get_data(as_text=True))
        workspace = removed.get_json()["workspace"]
        self.assertIsNone(workspace["slots"]["story_banner"])
        self.assertEqual(
            workspace["slots"]["experience_support"]["asset_id"], "art-forest"
        )
        self.assertEqual(
            self.client.get("/api/resume-media/me/workspace").get_json()["draft_version"],
            2,
        )

    def test_no_publication_route_and_every_response_stays_private(self):
        paths = sorted(str(rule) for rule in app.url_map.iter_rules())
        media_paths = [path for path in paths if "resume-media" in path]
        self.assertTrue(media_paths)
        for path in media_paths:
            self.assertNotIn("publish", path)
            self.assertNotIn("public", path)
        response = self.client.get("/api/resume-media/me/workspace")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertFalse(response.get_json()["publishes"])

    def test_unauthenticated_requests_get_a_neutral_404(self):
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        app.config["PEERSLATE_DEV_USER_KEY"] = None
        for path in (
            "/api/resume-media/me/workspace",
            "/api/resume-media/me/library",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.get_json()["message"], "Not found.")

    def test_draft_media_route_serves_persisted_bytes_after_add(self):
        source_id, derivative = self.ready_photo()
        # While the choice is still pending, only the staged preview exists.
        self.stage(self.photo_choice(source_id, "story_banner"))
        staged = self.client.get("/api/resume-media/me/placements/story_banner/media")
        self.assertEqual(staged.status_code, 200)
        self.assertEqual(staged.get_data(), derivative)
        self.assertEqual(
            self.client.get("/api/resume-media/me/draft/placements/story_banner/media").status_code,
            404,
        )

        added = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        self.assertEqual(added.status_code, 200, added.get_data(as_text=True))

        # Add clears the pending preview; the persisted draft placement still
        # serves its exact bytes through its own owner-authorized route.
        self.assertEqual(
            self.client.get("/api/resume-media/me/placements/story_banner/media").status_code,
            404,
        )
        saved = self.client.get("/api/resume-media/me/draft/placements/story_banner/media")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.get_data(), derivative)
        self.assertEqual(saved.headers["Content-Type"], "image/jpeg")
        self.assertEqual(saved.headers["Cache-Control"], "private, no-store")
        self.assertEqual(saved.headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("member-photo", str(saved.headers))

    def test_draft_media_route_denies_another_owner_and_a_revoked_source(self):
        source_id, derivative = self.ready_photo()
        self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        self.use_owner(OWNER_B)
        self.assertEqual(
            self.client.get(
                "/api/resume-media/me/draft/placements/story_banner/media"
            ).status_code,
            404,
        )
        self.use_owner(OWNER_A)
        self.sources.update_owner_photo(
            owner_id=OWNER_A, source_id=source_id, lifecycle=LIFECYCLE_WITHDRAWN
        )
        self.assertEqual(
            self.client.get(
                "/api/resume-media/me/draft/placements/story_banner/media"
            ).status_code,
            404,
        )

    def test_extra_multipart_authority_fields_are_ignored_not_mutated(self):
        self.use_owner(OWNER_A)
        response = self.client.post(
            "/api/resume-media/me/photos",
            data={
                "owner_user_key": OWNER_B,
                "user_key": OWNER_B,
                "owner_profile_id": "4242",
                "publish": "true",
                "photo": (io.BytesIO(image_bytes()), "member-photo.jpg", "image/jpeg"),
            },
            headers=self.headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload["source_id"])
        self.assertEqual(payload["state"], "scanning")
        self.assertFalse(payload["added_to_resume"])
        # The source is mirrored for the server-derived owner only.
        self.assertIsNotNone(
            self.sources.get_owner_photo(OWNER_A, payload["source_id"])
        )
        self.assertIsNone(self.sources.get_owner_photo(OWNER_B, payload["source_id"]))

    def test_missing_service_config_on_the_command_route_is_unavailable(self):
        app.config["RESUME_MEDIA_SERVICE"] = None
        response = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "keep_words_only",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
            },
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "unavailable")

    def test_post_commit_workspace_failure_keeps_the_committed_outcome(self):
        source_id, _ = self.ready_photo()

        class WorkspaceFailingApplication(ResumeMediaApplicationService):
            def workspace(self, *, owner_id):
                raise ResumeMediaError("storage-unavailable")

        failing = WorkspaceFailingApplication(
            media=ResumeMediaService(
                repository=self.application.media_repository,
                storage=self.storage,
                photo_readiness=self.readiness,
            ),
            persistence_label="in_memory_not_live_db",
            catalog_label="synthetic_test_catalog",
        )
        app.config["RESUME_MEDIA_SERVICE"] = failing
        response = self.client.post(
            "/api/resume-media/me/commands",
            json={
                "type": "add_media",
                "request_id": str(uuid4()),
                "expected_draft_version": 0,
                "choices": [self.photo_choice(source_id, "story_banner")],
            },
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertEqual(payload["outcome"], "committed")
        self.assertEqual(payload["draft_version"], 1)
        self.assertIsNone(payload["workspace"])
        self.assertTrue(payload["workspace_unavailable"])
        # The command really committed: the original wiring sees it.
        app.config["RESUME_MEDIA_SERVICE"] = self.application
        workspace = self.application.workspace(owner_id=OWNER_A)
        self.assertEqual(workspace["draft_version"], 1)
        self.assertTrue(workspace["slots"]["story_banner"])

    def test_application_errors_surface_as_unavailable_not_fixture_success(self):
        class BrokenApplication:
            pass

        app.config["RESUME_MEDIA_SERVICE"] = BrokenApplication()
        response = self.client.get("/api/resume-media/me/workspace")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "unavailable")


if __name__ == "__main__":
    unittest.main()
