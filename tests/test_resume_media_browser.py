"""Real browser -> Flask -> service journeys for the MVP1 D media chooser.

Playwright drives a real headless Chrome against a locally served Flask app.
The Photo Capture procedure boundary and the private storage/catalog boundary
are in-process deterministic stubs that record the exact bytes and calls they
received, so the browser evidence is real
(page -> event -> request -> view -> service -> boundary -> response -> DOM)
while the provider/storage boundary stays synthetic. The application's own HTTP
responses are never intercepted.

Ordinary unittest discovery may skip when Playwright or Chrome is unavailable.
This is not SQL engine proof, live storage proof or live identity proof.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.serving import make_server

from app import app, limiter
from services.photo_capture_service import PhotoCaptureService, normalize_photo
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_media_application import (
    PhotoCaptureResumeReadinessPort,
    build_resume_media_application,
)
from services.resume_media_repository import (
    InMemoryMediaStorage,
    InMemoryResumeMediaRepository,
    ResumeMediaRepositoryError,
)
from services.resume_media_service import ResumePhotoReadinessAdapter
from services.resume_guide_service import ResumeGuideService
from services.resume_intake_repository import InMemoryResumeIntakeRepository

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - environment capability gate
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - optional local browser helper
    CHROME_EXECUTABLE = None


OWNER_A = "media-browser-member"
OWNER_B = "media-browser-other-member"
SOURCE_KEY = "11111111-1111-4111-8111-111111111111"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "resume_media"
MEMBER_PHOTO = FIXTURES / "member-photo-1200x800.jpg"
LIBRARY_ILLUSTRATION = FIXTURES / "library-illustration-1600x900.png"
PLACEMENT_PREVIEW_LABEL = "Placement preview \u00b7 Not added yet"
SAVED_LABEL = "Saved in your private draft"

CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_RESUME_EDITOR_ENABLED",
    "PEERSLATE_RESUME_MEDIA_ENABLED",
    "RESUME_DRAFT_SERVICE",
    "RESUME_MEDIA_SERVICE",
    "RESUME_GUIDE_SERVICE",
    "RESUME_INTAKE_SERVICE",
)


class SyntheticPhotoProcedures:
    """Labelled synthetic stand-in for the owner-scoped Photo Capture procedures."""

    def __init__(self, storage):
        self.storage = storage
        self.calls = []
        self.media_reads = []
        self.created = {}
        self.completed = set()
        self.rejected = False
        self._counter = 0
        # The threaded test server can run two procedures at once; a real
        # database serializes them, so this stand-in does too.
        self._lock = threading.RLock()

    def reset(self):
        with self._lock:
            self.calls.clear()
            self.media_reads.clear()
            self.created.clear()
            self.completed.clear()
            self.rejected = False
            self._counter = 0

    @staticmethod
    def _params(parameters):
        return {name: value for name, value in (parameters or [])}

    @staticmethod
    def _row_version(stage):
        return bytes([stage]) * 8

    def bound(self, procedure):
        with self._lock:
            return [dict(params) for name, params in self.calls if name == procedure]

    def first_row(self, procedure, parameters=None):
        with self._lock:
            return self._first_row(procedure, parameters)

    def _first_row(self, procedure, parameters):
        bound = self._params(parameters)
        self.calls.append((procedure, list(parameters or [])))
        if procedure == "usp_CreatePhotoSource":
            self._counter += 1
            source_key = "11111111-1111-4111-8111-%012d" % self._counter
            self.created[source_key] = bound
            return {
                "outcome": "created",
                "source_key": source_key,
                "row_version": self._row_version(1),
            }
        if procedure == "usp_MarkPhotoUploaded":
            return {"outcome": "scanning", "row_version": self._row_version(2)}
        if procedure == "usp_GetPhotoSourceForOwner":
            return self._source_row(str(bound["@SourceKey"]))
        if procedure == "usp_GetPhotoProcessingSourceForOwner":
            return self._processing_row(str(bound["@SourceKey"]))
        if procedure == "usp_RecordPhotoScanResult":
            if self.rejected:
                return {"outcome": "rejected"}
            return self._scan_row(str(bound["@SourceKey"]))
        if procedure == "usp_CompletePhotoProcessing":
            self.completed.add(str(bound["@SourceKey"]))
            return {"outcome": "needs_review"}
        if procedure == "usp_GetPhotoMediaForOwner":
            return self._media_row(str(bound["@SourceKey"]))
        return None

    def _created(self, source_key):
        return self.created[source_key]

    def _source_row(self, source_key):
        if source_key not in self.completed:
            return {
                "source_key": source_key,
                "state": "scanning",
                "row_version": self._row_version(2),
                "pixel_width": 0,
                "pixel_height": 0,
            }
        if self.rejected:
            return {
                "source_key": source_key,
                "state": "rejected",
                "row_version": self._row_version(3),
                "pixel_width": 0,
                "pixel_height": 0,
            }
        parameters = self._created(source_key)
        record = self.storage.objects[parameters["@DerivativeBlobName"]]
        return {
            "source_key": source_key,
            "state": "needs_review",
            "row_version": self._row_version(4),
            "pixel_width": 1200,
            "pixel_height": 800,
            "derivative_content_type": record["content_type"],
            "derivative_byte_length": len(record["data"]),
            "derivative_blob_name": parameters["@DerivativeBlobName"],
            "scan_result": "clean",
        }

    def _processing_row(self, source_key):
        parameters = self._created(source_key)
        record = self.storage.objects[parameters["@OriginalBlobName"]]
        return {
            "source_key": source_key,
            "state": "scanning",
            "original_blob_name": parameters["@OriginalBlobName"],
            "derivative_blob_name": parameters["@DerivativeBlobName"],
            "original_content_type": parameters["@OriginalContentType"],
            "original_byte_length": len(record["data"]),
            "original_sha256_digest": hashlib.sha256(record["data"]).digest(),
            "original_blob_etag": record["etag"],
            "row_version": self._row_version(2),
        }

    def _scan_row(self, source_key):
        parameters = self._created(source_key)
        record = self.storage.objects[parameters["@OriginalBlobName"]]
        return {
            "outcome": "processing",
            "original_blob_name": parameters["@OriginalBlobName"],
            "original_content_type": parameters["@OriginalContentType"],
            "original_byte_length": len(record["data"]),
            "original_sha256_digest": hashlib.sha256(record["data"]).digest(),
            "original_blob_etag": record["etag"],
            "derivative_blob_name": parameters["@DerivativeBlobName"],
            "row_version": self._row_version(3),
        }

    def _media_row(self, source_key):
        parameters = self._created(source_key)
        ref = parameters["@DerivativeBlobName"]
        record = self.storage.objects[ref]
        self.media_reads.append(
            {"ref": ref, "bytes": len(record["data"]), "sha256": hashlib.sha256(record["data"]).hexdigest()}
        )
        return {
            "source_key": source_key,
            "blob_name": ref,
            "content_type": record["content_type"],
            "byte_length": len(record["data"]),
            "sha256_digest": hashlib.sha256(record["data"]).digest(),
        }


class SyntheticBoundaryStorage:
    """Synthetic private storage double for Photo Capture and catalog refs."""

    def __init__(self):
        self.objects = {}
        self.uploads = []
        self._lock = threading.Lock()

    def upload(self, ref, data, content_type):
        with self._lock:
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


class CatalogOutageRepository(InMemoryResumeMediaRepository):
    """Synthetic catalogue outage used to prove the honest error state."""

    FAILING_QUERY = "__catalog-unavailable__"
    SLOW_QUERY = "slow-trail"

    def __init__(self):
        super().__init__()
        self.slow_query_delay = 0.0

    def list_catalog(self, **kwargs):
        if kwargs.get("query") == self.FAILING_QUERY:
            raise ResumeMediaRepositoryError("catalog-unavailable")
        if kwargs.get("query") == self.SLOW_QUERY and self.slow_query_delay:
            time.sleep(self.slow_query_delay)
        return super().list_catalog(**kwargs)


class SyntheticDraftStore(InMemoryResumeDraftRepository):
    """Synthetic Resume draft store with a one-shot slow read hook."""

    def __init__(self):
        super().__init__()
        self.slow_next_load_seconds = 0.0
        self.block_next_commit = False
        self.commit_entered = threading.Event()
        self.release_commit = threading.Event()
        self.command_calls = 0
        # One-shot hooks are taken under a lock so that, on the threaded test
        # server, exactly one concurrent request consumes each of them.
        self._hook_lock = threading.Lock()

    def load_owner(self, owner_user_key):
        with self._hook_lock:
            delay = self.slow_next_load_seconds
            self.slow_next_load_seconds = 0.0
        if delay:
            time.sleep(delay)
        return super().load_owner(owner_user_key)

    def commit_owner_command(self, owner_user_key, *, expected_version, apply):
        with self._hook_lock:
            self.command_calls += 1
            block = self.block_next_commit
            self.block_next_commit = False
        if block:
            self.commit_entered.set()
            if not self.release_commit.wait(timeout=10):
                raise AssertionError("Timed out waiting to release blocked command.")
        return super().commit_owner_command(
            owner_user_key, expected_version=expected_version, apply=apply
        )


def _stop_playwright(runtime):
    runtime.stop()


def _close_browser(browser):
    browser.close()


def _shutdown_server(server, thread):
    try:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
    finally:
        server.server_close()


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for the Resume media browser proof",
)
class ResumeMediaBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_config = {key: app.config.get(key) for key in CONFIG_KEYS}
        cls.limiter_was_enabled = limiter.enabled
        cls.werkzeug_logger = logging.getLogger("werkzeug")
        cls.werkzeug_log_level = cls.werkzeug_logger.level

        def restore():
            app.config.update(cls.original_config)
            limiter.enabled = cls.limiter_was_enabled
            cls.werkzeug_logger.setLevel(cls.werkzeug_log_level)

        cls.addClassCleanup(restore)

        cls.capture_storage = SyntheticBoundaryStorage()
        cls.procedures = SyntheticPhotoProcedures(cls.capture_storage)
        cls.capture = PhotoCaptureService(
            database=cls.procedures, storage=cls.capture_storage
        )
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=OWNER_A,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_EDITOR_ENABLED=True,
            PEERSLATE_RESUME_MEDIA_ENABLED=True,
            RESUME_GUIDE_SERVICE=ResumeGuideService(
                repository=InMemoryResumeIntakeRepository()
            ),
            RESUME_INTAKE_SERVICE=None,
        )
        limiter.enabled = False
        cls.werkzeug_logger.setLevel(logging.ERROR)

        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        cls.addClassCleanup(_shutdown_server, server, thread)
        thread.start()
        cls.server = server
        cls.base_url = f"http://127.0.0.1:{server.server_port}"

        runtime = sync_playwright().start()
        cls.addClassCleanup(_stop_playwright, runtime)
        cls.playwright = runtime
        browser = runtime.chromium.launch(
            executable_path=CHROME_EXECUTABLE, headless=True
        )
        cls.addClassCleanup(_close_browser, browser)
        cls.browser = browser
        cls.evidence_dir = None
        evidence_value = os.environ.get("PEERSLATE_RESUME_MEDIA_EVIDENCE_DIR", "").strip()
        if evidence_value:
            cls.evidence_dir = Path(evidence_value).expanduser().resolve()
            cls.evidence_dir.mkdir(parents=True, exist_ok=True)
        cls.capture_manifest = []

    def setUp(self):
        """Fresh synthetic boundaries for every journey; the browser is reused."""

        self.procedures.reset()
        self.capture_storage.objects.clear()
        self.capture_storage.uploads.clear()
        self.sources = CatalogOutageRepository()
        self.storage = InMemoryMediaStorage()
        self.draft_store = SyntheticDraftStore()
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
        self.seed_catalog()
        app.config.update(
            PEERSLATE_DEV_USER_KEY=OWNER_A,
            RESUME_DRAFT_SERVICE=self.draft_service,
            RESUME_MEDIA_SERVICE=self.application,
        )

    def seed_catalog(self, asset_id="art-forest", *, label="Forest trail", version=1):
        derivatives = []
        for slot in ("story_banner", "experience_support"):
            payload = LIBRARY_ILLUSTRATION.read_bytes()
            ref = f"catalog/{asset_id}/{version}/{slot}.png"
            record = self.storage.put(
                ref,
                payload,
                content_type="image/png",
            )
            derivatives.append(
                {
                    "slot": slot,
                    "ref": ref,
                    "digest": record["digest"],
                    "content_type": "image/png",
                    "byte_length": record["byte_length"],
                }
            )
        return self.sources.seed_catalog_asset(
            asset_id=asset_id,
            label=label,
            category="Nature",
            tags=("calm", "trail"),
            version=version,
            digest=("%064d" % version),
            provenance={"model": "synthetic-test-model"},
            rights={"rights_id": "synthetic-rights", "approval_state": "approved"},
            derivatives=derivatives,
        )

    # -- helpers -----------------------------------------------------------

    def page_for(self, width=1440, height=1000, **context_kwargs):
        context = self.browser.new_context(
            viewport={"width": width, "height": height}, **context_kwargs
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        return page

    def open_chooser(self, page, *, owner=OWNER_A):
        app.config["PEERSLATE_DEV_USER_KEY"] = owner
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-media").wait_for(state="visible")
        return page

    def draft_version(self, page):
        response = page.context.request.get(f"{self.base_url}/api/resume-media/me/workspace")
        return response.json()["draft_version"]

    def upload_and_confirm_scan(self, page):
        self.procedures.rejected = False
        page.locator("#resume-media-upload").set_input_files(str(MEMBER_PHOTO))
        card = page.locator("#resume-media-photos li").first
        card.wait_for(timeout=15000)
        card.get_by_role("button", name="Check scan").click()
        card.get_by_role("button", name="Use for My Story banner").wait_for(timeout=15000)
        return card

    def stage_photo_into(self, page, slot):
        card = self.upload_and_confirm_scan(page)
        card.get_by_role("button", name=f"Use for {'My Story banner' if slot == 'story_banner' else 'Experience photo'}").click()
        page.locator(f"#resume-media-slot-{slot}-value").get_by_text("Your photo").wait_for(
            timeout=15000
        )

    def stage_library_into(self, page, slot):
        page.locator("#resume-media-tab-library").click()
        panel = page.locator("#resume-media-panel-library")
        card = panel.locator("li").first
        card.wait_for(timeout=15000)
        label = "My Story banner" if slot == "story_banner" else "Experience photo"
        card.get_by_role("button", name=f"Use for {label}").click()
        page.locator(f"#resume-media-slot-{slot}-value").get_by_text("Forest trail").wait_for(
            timeout=15000
        )
        page.locator("#resume-media-tab-photos").click()

    def capture_evidence(self, page, name):
        if self.evidence_dir is None:
            return
        target = self.evidence_dir / f"{name}.png"
        page.screenshot(path=str(target), full_page=True)
        self.capture_manifest.append({"name": name, "file": target.name})

    # -- journeys ----------------------------------------------------------

    def test_upload_scan_ready_and_personal_selection(self):
        page = self.open_chooser(self.page_for())
        card = self.upload_and_confirm_scan(page)
        state = card.locator(".resume-media__card-state").inner_text().lower()
        self.assertIn("ready to use", state)
        card.get_by_role("button", name="Use for My Story banner").click()
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "Your photo"
        ).wait_for(timeout=15000)
        self.assertEqual(self.draft_version(page), 0)

        # The real private preview bytes came back through the Flask route.
        media = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/placements/story_banner/media"
        )
        expected = normalize_photo(MEMBER_PHOTO.read_bytes(), "image/jpeg").data
        self.assertEqual(media.status, 200)
        self.assertEqual(media.body(), expected)
        self.assertEqual(media.headers["cache-control"], "private, no-store")
        # The Photo Capture seam read exactly that derivative.
        self.assertTrue(self.procedures.media_reads)
        self.assertEqual(
            self.procedures.media_reads[-1]["sha256"],
            hashlib.sha256(expected).hexdigest(),
        )
        self.capture_evidence(page, "d04-my-photos-desktop")

    def test_library_search_places_an_illustration_and_shows_attribution(self):
        page = self.open_chooser(self.page_for())
        page.locator("#resume-media-tab-library").click()
        page.locator("#resume-media-library-search").fill("forest")
        card = page.locator("#resume-media-panel-library li").first
        card.wait_for(timeout=15000)
        self.assertIn("Forest trail", card.inner_text())
        self.assertIn("AI generated illustration", card.inner_text())
        card.get_by_role("button", name="Use for My Story banner").click()
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "Forest trail"
        ).wait_for(timeout=15000)

        attribution = page.locator(
            "#resume-media-placement-attribution-story_banner"
        )
        self.assertTrue(attribution.is_visible())
        self.assertIn("library illustration", attribution.inner_text().lower())
        self.assertIn(
            "ai generated illustrations",
            page.locator("#resume-media-preview-provenance").inner_text().lower(),
        )
        # Catalogue bytes really rendered through the production handler.
        thumbnail = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/library/art-forest/1/thumbnail"
        )
        self.assertEqual(thumbnail.status, 200)
        self.assertEqual(thumbnail.body(), LIBRARY_ILLUSTRATION.read_bytes())
        self.assertIn("catalog/art-forest/1/story_banner.png", self.storage.opens)
        self.capture_evidence(page, "d05-library-desktop")

    def test_mixed_selection_swap_and_per_slot_crops(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        self.stage_library_into(page, "experience_support")

        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")
        self.assertIn("2 photos", page.locator("#resume-media-preview-count").inner_text())
        page.locator("#resume-media-crop-story_banner").click()
        story_crop_before = page.locator("#resume-media-crop-story_banner-height").input_value()
        page.locator("#resume-media-crop-experience_support").click()
        experience_crop_before = page.locator(
            "#resume-media-crop-experience_support-width"
        ).input_value()

        page.locator("#resume-media-swap").click()
        page.locator("#resume-media-preview-slot-story_banner").get_by_text(
            "No photo"
        ).count()
        page.locator("#resume-media-crop-story_banner").click()
        story_crop_after = page.locator("#resume-media-crop-story_banner-height").input_value()
        page.locator("#resume-media-crop-experience_support").click()
        experience_crop_after = page.locator(
            "#resume-media-crop-experience_support-width"
        ).input_value()
        # Swapping recomputes each slot's own shape instead of reusing the
        # other slot's geometry.
        self.assertNotEqual(story_crop_before, story_crop_after)
        self.assertNotEqual(experience_crop_before, experience_crop_after)
        self.assertEqual(self.draft_version(page), 0)
        self.capture_evidence(page, "d06-placement-desktop")

    def test_tab_switch_and_hide_reopen_keep_pending_state(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        caption = "Photos from a project I led."
        page.locator("#resume-media-caption").fill(caption)
        page.locator("#resume-media-tab-library").click()
        page.locator("#resume-media-tab-photos").click()
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "Your photo"
        ).wait_for(timeout=15000)
        self.assertEqual(page.locator("#resume-media-caption").input_value(), caption)

        page.locator("#resume-media-hide").click()
        self.assertFalse(page.locator("#resume-media-guide").is_visible())
        self.assertTrue(page.locator("#resume-media-reopen").is_visible())
        # The placement preview stays on the page with its honest badge.
        self.assertTrue(
            page.locator("#resume-media-placement-badge-story_banner").is_visible()
        )
        self.assertEqual(
            page.locator("#resume-media-placement-badge-story_banner").inner_text(),
            PLACEMENT_PREVIEW_LABEL,
        )
        page.locator("#resume-media-reopen").click()
        self.assertTrue(page.locator("#resume-media-guide").is_visible())
        self.assertEqual(page.locator("#resume-media-caption").input_value(), caption)
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "Your photo"
        ).wait_for(timeout=15000)
        self.assertEqual(self.draft_version(page), 0)

    def test_preview_does_not_change_the_private_draft(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        self.stage_library_into(page, "experience_support")
        before = self.draft_version(page)
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")
        self.assertTrue(page.locator("#resume-media-preview-image-story_banner").is_visible())
        self.assertTrue(
            page.locator("#resume-media-preview-image-experience_support").is_visible()
        )
        self.assertEqual(
            page.locator("#resume-media-preview-count").inner_text().strip(),
            "2 photos \u00b7 Not added yet",
        )
        page.locator("#resume-media-preview-back").click()
        page.locator("#resume-media-guide").wait_for(state="visible")
        self.assertEqual(self.draft_version(page), before)
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertIsNone(workspace["slots"]["story_banner"])
        self.assertEqual(workspace["draft_version"], 0)

    def test_add_saves_one_private_draft_version_and_reload_returns_crops(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")
        page.locator("#resume-media-crop-story_banner").click()
        page.locator("#resume-media-crop-story_banner-x").fill("0")
        page.locator("#resume-media-crop-story_banner-y").fill("0.25")
        page.locator("#resume-media-crop-story_banner-width").fill("1")
        page.locator("#resume-media-crop-story_banner-height").fill("0.5")
        page.locator("#resume-media-crop-apply-story_banner").click()
        page.locator("#resume-media-status").get_by_text("Crop updated").wait_for(
            timeout=15000
        )
        # The reviewed crop really drives the preview view: a half-height crop
        # on the story banner shows the source at 200% height.
        self.assertAlmostEqual(
            page.locator("#resume-media-placement-image-story_banner").evaluate(
                "node => parseFloat(node.style.height)"
            ),
            200.0,
        )

        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text(
            "Added 1 photo to your private r\u00e9sum\u00e9. Nothing was published."
        ).wait_for(timeout=20000)
        self.assertEqual(self.draft_version(page), 1)
        self.assertEqual(
            page.locator("#resume-media-placement-badge-story_banner").inner_text(),
            SAVED_LABEL,
        )

        page.reload(wait_until="load")
        page.locator("#resume-media").wait_for(state="visible")
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "saved privately"
        ).wait_for(timeout=15000)
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertEqual(workspace["slots"]["story_banner"]["crop"], {
            "x": 0.0,
            "y": 0.25,
            "width": 1.0,
            "height": 0.5,
        })
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-crop-story_banner").click()
        self.assertEqual(
            page.locator("#resume-media-crop-story_banner-height").input_value(), "0.5"
        )
        self.capture_evidence(page, "d06-placement-saved-desktop")

    def test_saved_placement_bytes_render_after_add_and_after_reload(self):
        page = self.open_chooser(self.page_for())
        card = self.upload_and_confirm_scan(page)
        card.get_by_role("button", name="Use for My Story banner").click()
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "Your photo"
        ).wait_for(timeout=15000)
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )

        expected = normalize_photo(MEMBER_PHOTO.read_bytes(), "image/jpeg").data
        # After Add the source image is the persisted draft placement: the
        # browser really decoded bytes through the private draft media route.
        page.locator("#resume-media-placement-image-story_banner").wait_for(
            state="visible", timeout=15000
        )
        page.wait_for_function(
            "() => { const img = document.getElementById('resume-media-placement-image-story_banner');"
            " return img && img.complete && img.naturalWidth > 0; }",
            timeout=15000,
        )
        rendered = page.locator("#resume-media-placement-image-story_banner").evaluate(
            "node => ({width: node.naturalWidth, src: node.currentSrc || node.src})"
        )
        self.assertGreater(rendered["width"], 0)
        self.assertIn("/draft/placements/story_banner/media", rendered["src"])
        saved = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/draft/placements/story_banner/media"
        )
        self.assertEqual(saved.status, 200)
        self.assertEqual(saved.body(), expected)
        self.assertEqual(
            page.context.request.get(
                f"{self.base_url}/api/resume-media/me/placements/story_banner/media"
            ).status,
            404,
        )

        # A reload still renders the saved placement bytes, not a broken image.
        page.reload(wait_until="load")
        page.locator("#resume-media").wait_for(state="visible")
        page.wait_for_function(
            "() => { const img = document.getElementById('resume-media-placement-image-story_banner');"
            " return img && !img.hidden && img.complete && img.naturalWidth > 0; }",
            timeout=15000,
        )
        after_reload = page.locator(
            "#resume-media-placement-image-story_banner"
        ).evaluate("node => ({width: node.naturalWidth, src: node.currentSrc || node.src})")
        self.assertGreater(after_reload["width"], 0)
        self.assertIn("/draft/placements/story_banner/media", after_reload["src"])
        reloaded = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/draft/placements/story_banner/media"
        )
        self.assertEqual(reloaded.body(), expected)
        self.capture_evidence(page, "corrected-saved-placement-desktop")

    def test_index_marks_exactly_one_hide_guide_in_placement_review(self):
        for width, height, name in (
            (1440, 900, "corrected-placement-header-desktop"),
            (390, 844, "corrected-placement-header-mobile"),
        ):
            with self.subTest(width=width):
                page = self.open_chooser(
                    self.page_for(
                        width=width, height=height,
                        is_mobile=width < 768, has_touch=width < 768,
                    )
                )
                self.stage_library_into(page, "story_banner")
                page.locator("#resume-media-preview-placement").click()
                page.locator("#resume-media-preview").wait_for(state="visible")
                visible_hide = page.locator(
                    'button:visible:text-is("Hide guide")'
                ).count()
                self.assertEqual(visible_hide, 1)
                self.assertFalse(
                    page.locator("#resume-media > .resume-media__header").is_visible()
                )
                self.assertTrue(page.locator("#resume-media-preview-back").is_visible())
                self.capture_evidence(page, name)
                page.context.close()

    def test_lost_command_response_is_retried_with_the_same_request(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")

        seen_request_ids = []
        aborted = {"count": 0}
        commands_pattern = "**/api/resume-media/me/commands"

        def lose_the_response(route):
            request_id = None
            try:
                body = json.loads(route.request.post_data or "{}")
                request_id = body.get("request_id")
            except (TypeError, ValueError):
                request_id = None
            seen_request_ids.append(request_id)
            if aborted["count"] >= 1:
                # The retry is the same request; let it reach the application.
                route.continue_()
                return
            # The real request reaches Flask and really commits; only the
            # response is dropped, so the client cannot know the outcome.
            route.fetch()
            aborted["count"] += 1
            route.abort()

        page.route(commands_pattern, lose_the_response)
        page.locator("#resume-media-add").click()

        page.locator("#resume-media-status").get_by_text(
            "outcome is unknown"
        ).wait_for(timeout=20000)
        self.assertEqual(aborted["count"], 1)
        # The command really committed even though the response was lost.
        self.assertEqual(self.draft_version(page), 1)

        page.locator("#resume-media-retry").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        page.unroute(commands_pattern, lose_the_response)
        self.assertEqual(aborted["count"], 1)
        self.assertNotIn(None, seen_request_ids)
        self.assertEqual(len(seen_request_ids), 2)
        self.assertEqual(seen_request_ids[0], seen_request_ids[1])
        # One commit, one receipt: the retry replayed the original outcome.
        self.assertEqual(self.draft_version(page), 1)
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertEqual(workspace["draft_version"], 1)
        stored = self.draft_store.load_owner(OWNER_A)
        self.assertEqual(len(stored["media_receipts"]), 1)

    def test_stale_library_response_does_not_replace_newer_search(self):
        page = self.open_chooser(self.page_for())
        self.sources.slow_query_delay = 1.5
        page.locator("#resume-media-tab-library").click()
        page.locator("#resume-media-panel-library li").first.wait_for(timeout=15000)
        search = page.locator("#resume-media-library-search")
        search.fill(CatalogOutageRepository.SLOW_QUERY)
        # The slow query is in flight; a newer query supersedes it before the
        # slow response can arrive.
        time.sleep(0.35)
        search.fill("no-such-illustration")
        page.locator("#resume-media-library-empty").wait_for(state="visible", timeout=15000)
        time.sleep(1.8)
        self.assertTrue(page.locator("#resume-media-library-empty").is_visible())
        self.assertEqual(page.locator("#resume-media-panel-library li").count(), 0)
        self.assertEqual(search.input_value(), "no-such-illustration")

    def test_caption_cleared_before_add_clears_the_saved_caption(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        caption = page.locator("#resume-media-caption")
        caption.fill("A caption I later removed.")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")
        page.locator("#resume-media-preview-back").click()
        page.locator("#resume-media-guide").wait_for(state="visible")
        caption.fill("")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertIsNone(workspace["slots"]["story_banner"]["caption"])

    def test_later_workspace_refresh_is_not_overwritten_by_an_earlier_request(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        # The next workspace read is slow and returns the pre-Add snapshot: it
        # is the read the upload triggers. Its response arrives after the Add's
        # own refresh, so an unguarded client would repaint the older state.
        self.draft_store.slow_next_load_seconds = 1.2
        page.locator("#resume-media-upload").set_input_files(str(MEMBER_PHOTO))
        page.locator("#resume-media-status").get_by_text(
            "Uploaded privately"
        ).wait_for(timeout=15000)
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        # The slow earlier snapshot must not repaint the chooser back to
        # "Not added yet" after the Add's own refresh landed.
        time.sleep(1.6)
        self.assertEqual(
            page.locator("#resume-media-placement-badge-story_banner").inner_text(),
            SAVED_LABEL,
        )
        self.assertEqual(self.draft_version(page), 1)

    def test_unresolved_command_blocks_every_other_committing_action(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")

        seen_request_ids = []
        dropped = {"count": 0}
        commands_pattern = "**/api/resume-media/me/commands"

        def drop_first_response(route):
            try:
                body = json.loads(route.request.post_data or "{}")
                seen_request_ids.append(body.get("request_id"))
            except (TypeError, ValueError):
                seen_request_ids.append(None)
            if dropped["count"] >= 1:
                route.continue_()
                return
            route.fetch()
            dropped["count"] += 1
            route.abort()

        page.route(commands_pattern, drop_first_response)
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text(
            "outcome is unknown"
        ).wait_for(timeout=20000)
        self.assertEqual(dropped["count"], 1)
        self.assertEqual(self.draft_version(page), 1)

        # Every other committing control is gated while the outcome is unknown.
        keep = page.locator("#resume-media-keep-words")
        self.assertTrue(keep.is_disabled())
        self.assertEqual(keep.get_attribute("aria-disabled"), "true")
        self.assertTrue(
            page.locator("#resume-media-slot-story_banner-remove").is_disabled()
        )
        # Even a synthetic dispatch cannot start a second command.
        page.evaluate(
            "() => document.getElementById('resume-media-keep-words')"
            ".dispatchEvent(new MouseEvent('click', {bubbles: true}))"
        )
        page.locator("#resume-media-status").get_by_text(
            "still unresolved"
        ).wait_for(timeout=10000)
        page.evaluate(
            "() => document.getElementById('resume-media-slot-story_banner-remove')"
            ".dispatchEvent(new MouseEvent('click', {bubbles: true}))"
        )
        page.wait_for_timeout(400)
        self.assertEqual(len(seen_request_ids), 1)

        # Only the exact retry resolves it: same request, one commit, one receipt.
        page.locator("#resume-media-retry").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        page.unroute(commands_pattern, drop_first_response)
        self.assertEqual(len(seen_request_ids), 2)
        self.assertEqual(seen_request_ids[0], seen_request_ids[1])
        self.assertEqual(self.draft_version(page), 1)
        stored = self.draft_store.load_owner(OWNER_A)
        self.assertEqual(len(stored["media_receipts"]), 1)
        self.assertTrue(keep.is_enabled())

    def test_in_flight_command_gates_cross_actions_before_the_response(self):
        page = self.open_chooser(self.page_for())
        # Persist one slot first so the test exercises the saved-removal command
        # path, then stage a different slot for the blocked Add.
        self.stage_library_into(page, "experience_support")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        page.locator("#resume-media-preview-back").click()
        page.locator("#resume-media-guide").wait_for(state="visible")
        self.stage_photo_into(page, "story_banner")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")

        baseline_calls = self.draft_store.command_calls
        self.draft_store.block_next_commit = True
        try:
            # DOM click returns immediately while fetch and the real Flask
            # command continue on the server thread.
            page.evaluate("() => document.getElementById('resume-media-add').click()")
            self.assertTrue(self.draft_store.commit_entered.wait(timeout=10))

            keep = page.locator("#resume-media-keep-words")
            saved_remove = page.locator(
                "#resume-media-slot-experience_support-remove"
            )
            self.assertTrue(keep.is_disabled())
            self.assertTrue(saved_remove.is_disabled())
            self.assertEqual(keep.get_attribute("aria-disabled"), "true")
            # Programmatic events cannot bypass the handlers while the first
            # command has no authoritative response.
            page.evaluate(
                "() => document.getElementById('resume-media-keep-words')"
                ".dispatchEvent(new MouseEvent('click', {bubbles: true}))"
            )
            page.evaluate(
                "() => document.getElementById('resume-media-slot-experience_support-remove')"
                ".dispatchEvent(new MouseEvent('click', {bubbles: true}))"
            )
            self.assertEqual(self.draft_store.command_calls, baseline_calls + 1)
        finally:
            self.draft_store.release_commit.set()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        self.assertEqual(self.draft_store.command_calls, baseline_calls + 1)
        self.assertEqual(self.draft_version(page), 2)
        self.assertEqual(len(self.draft_store.load_owner(OWNER_A)["media_receipts"]), 2)

    def test_unresolved_remove_cannot_be_displaced_by_another_slot_removal(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        self.stage_library_into(page, "experience_support")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 2 photos").wait_for(
            timeout=20000
        )
        page.locator("#resume-media-preview-back").click()
        page.locator("#resume-media-guide").wait_for(state="visible")

        seen_request_ids = []
        dropped = {"count": 0}
        commands_pattern = "**/api/resume-media/me/commands"

        def drop_first_response(route):
            body = json.loads(route.request.post_data or "{}")
            seen_request_ids.append(body.get("request_id"))
            if dropped["count"]:
                route.continue_()
                return
            route.fetch()
            dropped["count"] += 1
            route.abort()

        page.route(commands_pattern, drop_first_response)
        page.locator("#resume-media-slot-story_banner-remove").click()
        page.locator("#resume-media-status").get_by_text("outcome is unknown").wait_for(
            timeout=20000
        )
        self.assertEqual(self.draft_version(page), 2)

        # A second remove_slot event is not an exact retry: it targets another
        # slot and therefore must not displace the retained request identity.
        page.evaluate(
            "() => document.getElementById('resume-media-slot-experience_support-remove')"
            ".dispatchEvent(new MouseEvent('click', {bubbles: true}))"
        )
        page.locator("#resume-media-status").get_by_text("still unresolved").wait_for(
            timeout=10000
        )
        self.assertEqual(len(seen_request_ids), 1)

        page.locator("#resume-media-retry").click()
        page.locator("#resume-media-status").get_by_text(
            "My Story banner removed"
        ).wait_for(timeout=20000)
        page.unroute(commands_pattern, drop_first_response)
        self.assertEqual(seen_request_ids, [seen_request_ids[0], seen_request_ids[0]])
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertIsNone(workspace["slots"]["story_banner"])
        self.assertIsNotNone(workspace["slots"]["experience_support"])
        self.assertEqual(workspace["draft_version"], 2)
        self.assertEqual(len(self.draft_store.load_owner(OWNER_A)["media_receipts"]), 2)

    def test_old_workspace_refresh_cannot_overwrite_new_local_intent(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        # A slow refresh starts with only the first choice staged, then the
        # member stages a second choice while that snapshot is in flight.
        self.draft_store.slow_next_load_seconds = 1.2
        page.locator("#resume-media-upload").set_input_files(str(MEMBER_PHOTO))
        page.locator("#resume-media-status").get_by_text(
            "Uploaded privately"
        ).wait_for(timeout=15000)
        self.stage_library_into(page, "experience_support")
        self.assertIn(
            "Forest trail",
            page.locator("#resume-media-slot-experience_support-value").inner_text(),
        )
        # Let the older snapshot arrive: it must not repaint over the new intent.
        time.sleep(1.8)
        self.assertIn(
            "Forest trail",
            page.locator("#resume-media-slot-experience_support-value").inner_text(),
        )
        self.assertIn(
            "Your photo",
            page.locator("#resume-media-slot-story_banner-value").inner_text(),
        )
        self.assertEqual(self.draft_version(page), 0)

    def test_removal_is_slot_local_and_keeps_the_other_photo(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        self.stage_library_into(page, "experience_support")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 2 photos").wait_for(
            timeout=20000
        )
        self.assertEqual(self.draft_version(page), 1)

        # Back to the chooser, where the saved slots are listed for change or
        # removal.
        page.locator("#resume-media-preview-back").click()
        page.locator("#resume-media-guide").wait_for(state="visible")
        page.locator("#resume-media-slot-story_banner-remove").click()
        page.locator("#resume-media-status").get_by_text(
            "removed from your private"
        ).wait_for(timeout=20000)
        self.assertEqual(self.draft_version(page), 2)
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertIsNone(workspace["slots"]["story_banner"])
        self.assertEqual(
            workspace["slots"]["experience_support"]["asset_id"], "art-forest"
        )
        self.assertFalse(page.locator("#resume-media-placement-image-story_banner").is_visible())
        self.assertTrue(
            page.locator("#resume-media-placement-image-experience_support").is_visible()
        )

    def test_library_empty_and_error_states_are_honest(self):
        page = self.open_chooser(self.page_for())
        page.locator("#resume-media-tab-library").click()
        page.locator("#resume-media-panel-library li").first.wait_for(timeout=15000)
        page.locator("#resume-media-library-search").fill("no-such-illustration")
        page.locator("#resume-media-library-empty").wait_for(state="visible", timeout=15000)
        self.assertIn(
            "no library images",
            page.locator("#resume-media-library-empty").inner_text().lower(),
        )

        page.locator("#resume-media-library-search").fill(
            CatalogOutageRepository.FAILING_QUERY
        )
        page.locator("#resume-media-library-error").wait_for(state="visible", timeout=15000)
        self.assertIn(
            "unavailable",
            page.locator("#resume-media-library-error").inner_text().lower(),
        )
        # The member's own photos remain usable while the library is down.
        page.locator("#resume-media-tab-photos").click()
        self.assertTrue(page.locator("#resume-media-upload").is_visible())

    def test_no_photo_choice_keeps_the_editor_usable(self):
        page = self.open_chooser(self.page_for())
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-status").get_by_text(
            "Choose at least one photo"
        ).wait_for(timeout=15000)
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text(
            "Choose at least one photo before adding"
        ).wait_for(timeout=15000)
        self.assertEqual(self.draft_version(page), 0)
        page.locator("#resume-media-preview-back").click()
        page.locator("#resume-media-guide").wait_for(state="visible")
        # The private editor itself still works.
        page.locator("#resume-editor-reload").click()
        self.assertTrue(page.locator("#resume-editor-status").inner_text())

    def test_keep_words_only_discards_pending_and_keeps_saved_media(self):
        page = self.open_chooser(self.page_for())
        self.stage_photo_into(page, "story_banner")
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-add").click()
        page.locator("#resume-media-status").get_by_text("Added 1 photo").wait_for(
            timeout=20000
        )
        page.locator("#resume-media-preview-back").click()
        self.stage_library_into(page, "experience_support")

        page.locator("#resume-media-keep-words").click()
        page.locator("#resume-media-status").get_by_text("Kept your words").wait_for(
            timeout=20000
        )
        workspace = page.context.request.get(
            f"{self.base_url}/api/resume-media/me/workspace"
        ).json()
        self.assertEqual(workspace["draft_version"], 2)
        self.assertEqual(workspace["staged"], {})
        self.assertTrue(workspace["slots"]["story_banner"])
        self.assertIsNone(workspace["slots"]["experience_support"])

    def test_mobile_layout_stacks_and_has_no_horizontal_overflow(self):
        page = self.open_chooser(
            self.page_for(width=390, height=844, is_mobile=True, has_touch=True)
        )
        self.stage_library_into(page, "story_banner")
        story = page.locator(".resume-media__frame--story").bounding_box()
        experience = page.locator(".resume-media__frame--experience").bounding_box()
        self.assertGreaterEqual(experience["y"], story["y"] + story["height"] - 1)
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        self.assertLessEqual(overflow, 1)
        page.locator("#resume-media-preview-placement").click()
        page.locator("#resume-media-preview").wait_for(state="visible")
        self.assertTrue(page.locator("#resume-media-add").is_visible())
        self.capture_evidence(page, "m06-placement-mobile")

    def test_keyboard_tabs_and_focus_are_operable(self):
        page = self.open_chooser(self.page_for())
        page.locator("#resume-media-tab-photos").focus()
        page.keyboard.press("ArrowRight")
        self.assertEqual(
            page.evaluate("() => document.activeElement.id"),
            "resume-media-tab-library",
        )
        self.assertEqual(
            page.locator("#resume-media-tab-library").get_attribute("aria-selected"),
            "true",
        )
        self.assertTrue(page.locator("#resume-media-panel-library").is_visible())
        page.keyboard.press("ArrowLeft")
        self.assertEqual(
            page.evaluate("() => document.activeElement.id"),
            "resume-media-tab-photos",
        )
        page.locator("#resume-media-tab-library").click()
        page.locator("#resume-media-panel-library li").first.wait_for(timeout=15000)
        page.locator("#resume-media-panel-library li").first.get_by_role(
            "button", name="Use for My Story banner"
        ).focus()
        page.keyboard.press("Enter")
        page.locator("#resume-media-slot-story_banner-value").get_by_text(
            "Forest trail"
        ).wait_for(timeout=15000)


if __name__ == "__main__":
    unittest.main()
