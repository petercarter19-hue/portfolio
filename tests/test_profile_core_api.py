"""Unregistered D0 Profile JSON blueprint contracts."""

from __future__ import annotations

import unittest

from flask import Flask

from profile_api import profile_api
from services.profile_core_service import (
    InMemoryProfileCoreStore,
    ProfileAboutDraft,
    ProfileCoreService,
    ProfileCurrentChapterDraft,
    ProfileIdentityDraft,
    make_profile_draft,
)


OWNER = "ownerAlpha_123"
OTHER = "ownerBravo_456"


class ProfileApiContractTests(unittest.TestCase):
    def setUp(self):
        draft = make_profile_draft(
            owner_key=OWNER,
            slug="avery",
            identity=ProfileIdentityDraft(
                display_name="Avery Carter",
                headline="Systems engineer",
                location=None,
                summary="A deliberate Profile foundation.",
            ),
            current_chapter=ProfileCurrentChapterDraft("Building", "Current chapter."),
            about=ProfileAboutDraft("About Avery", "A Profile-specific introduction."),
        )
        self.store = InMemoryProfileCoreStore([draft])
        self.service = ProfileCoreService(self.store)
        self.context = self.service.owner_context(
            actor_key=OWNER, subject_owner_key=OWNER, slug="avery", purpose="api"
        )
        self.app = Flask(__name__, template_folder="templates", static_folder="static")
        self.app.config.update(
            TESTING=True,
            PEERSLATE_PROFILE_CORE_SERVICE_PROVIDER=lambda: self.service,
            PEERSLATE_PROFILE_CORE_OWNER_CONTEXT_PROVIDER=lambda: self.context,
        )
        self.app.register_blueprint(profile_api)
        self.client = self.app.test_client()

    def _headers(self, key="publish-request-0001"):
        return {"X-PeerSlate-Request": "same-origin", "Idempotency-Key": key}

    def _publish(self):
        review = self.client.post(
            "/api/v1/profile-foundation/owner/publication/review",
            json={
                "expected_draft_version": self.store.draft_for_owner(OWNER).version,
                "expected_public_revision": None,
            },
            headers=self._headers(),
        )
        self.assertEqual(review.status_code, 200)
        return self.client.post(
            "/api/v1/profile-foundation/owner/publication/publish",
            json={
                "expected_draft_version": self.store.draft_for_owner(OWNER).version,
                "expected_public_revision": None,
                "candidate_digest": review.get_json()["review"]["candidate_digest"],
                "confirmed": True,
            },
            headers=self._headers(),
        )

    def test_public_unpublished_payload_is_neutral_not_found(self):
        response = self.client.get("/api/v1/profile-foundation/public/avery/home")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "code": "not_found"})
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_public_payload_has_no_owner_or_draft_data(self):
        self.assertEqual(self._publish().status_code, 200)
        response = self.client.get("/api/v1/profile-foundation/public/avery/home")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["profile"]["mode"], "public")
        encoded = response.get_data(as_text=True)
        self.assertNotIn(OWNER, encoded)
        self.assertNotIn("draft_key", encoded)
        self.assertNotIn("source_key", encoded)

    def test_write_rejects_cross_origin_and_browser_supplied_identity(self):
        denied = self.client.patch(
            "/api/v1/profile-foundation/owner/draft",
            json={},
        )
        self.assertEqual(denied.status_code, 403)
        forged = self.client.patch(
            "/api/v1/profile-foundation/owner/draft",
            json={"actor_key": OTHER},
            headers=self._headers(),
        )
        self.assertEqual(forged.status_code, 400)
        self.assertEqual(forged.get_json()["code"], "invalid_request")

    def test_preview_uses_same_public_payload_and_owner_is_server_derived(self):
        self.assertEqual(self._publish().status_code, 200)
        public = self.client.get("/api/v1/profile-foundation/public/avery/home").get_json()["profile"]
        preview = self.client.get(
            "/api/v1/profile-foundation/owner/preview/public/home"
        ).get_json()["profile"]
        self.assertEqual(preview, public)

    def test_source_does_not_register_with_main_application(self):
        from pathlib import Path

        for filename, blueprint in (("profile_api.py", "profile_api"), ("profile_routes.py", "profile_routes")):
            source = Path(filename).read_text(encoding="utf-8")
            self.assertNotIn("from app import", source)
            self.assertNotIn(f"register_blueprint({blueprint})", source)
