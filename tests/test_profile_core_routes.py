"""Unregistered D0 Profile HTML blueprint contract tests."""

from __future__ import annotations

import unittest

from pathlib import Path

from flask import Flask

from profile_routes import profile_routes
from services.profile_core_service import (
    InMemoryProfileCoreStore,
    ProfileAboutDraft,
    ProfileCoreService,
    ProfileCurrentChapterDraft,
    ProfileIdentityDraft,
    make_profile_draft,
)


OWNER = "ownerAlpha_123"


def _service():
    draft = make_profile_draft(
        owner_key=OWNER,
        slug="avery",
        identity=ProfileIdentityDraft(
            display_name="Avery Carter",
            headline="Systems engineer",
            location="Huntsville, Alabama",
            summary="A deliberate Profile foundation.",
        ),
        current_chapter=ProfileCurrentChapterDraft(
            label="Building with clarity", body="A quiet note about the current chapter."
        ),
        about=ProfileAboutDraft(
            heading="The person behind the work",
            body="A Profile-specific About introduction.",
            resume_path="/avery/resume",
            story_path="/avery/my-story",
            ask_path="/ask-avery",
        ),
    )
    store = InMemoryProfileCoreStore([draft])
    service = ProfileCoreService(store)
    context = service.owner_context(
        actor_key=OWNER, subject_owner_key=OWNER, slug="avery", purpose="test"
    )
    review = service.review_publication(
        context, expected_draft_version=draft.version, expected_public_revision=None
    )
    service.publish_publication(
        context,
        expected_draft_version=draft.version,
        expected_public_revision=None,
        candidate_digest=review["candidate_digest"],
        idempotency_key="publish-request-0001",
        confirmed=True,
    )
    return service


class ProfileRouteContractTests(unittest.TestCase):
    def setUp(self):
        root = Path.cwd()
        self.app = Flask(
            __name__,
            template_folder=str(root / "templates"),
            static_folder=str(root / "static"),
        )
        self.app.config.update(TESTING=True, PEERSLATE_PROFILE_CORE_SERVICE_PROVIDER=_service)
        self.app.register_blueprint(profile_routes)
        self.client = self.app.test_client()

    def test_blueprint_home_is_semantic_local_and_no_store(self):
        response = self.client.get("/avery/profile-home")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="profile-main"', body)
        self.assertIn('aria-label="Profile destinations"', body)
        self.assertIn("Avery Carter", body)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")
        self.assertNotIn("ownerAlpha_123", body)
        self.assertNotIn("draft_key", body)

    def test_unknown_profile_is_neutral_404(self):
        response = self.client.get("/missing/profile-home")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_unregistered_blueprint_does_not_change_current_app_routes(self):
        # This app registers the contract explicitly.  The source module must
        # not import app.py or perform registration as an import side effect.
        from pathlib import Path

        source = Path("profile_routes.py").read_text(encoding="utf-8")
        self.assertNotIn("from app import", source)
        self.assertNotIn("register_blueprint(profile_routes)", source)
