"""Flask wiring tests for the Resume draft editor. No live database or identity."""

import unittest
from uuid import UUID, uuid4

from app import app
from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService


ROLE_KEY = str(UUID(int=21, version=4))


def role_item():
    return {
        "record_key": ROLE_KEY,
        "record_type": "role",
        "content_token": "1",
        "access_revision": 1,
        "editable": False,
        "blocked_reason": "published_or_history_bearing",
        "save_mode": "draft_overlay",
        "values": {
            "role_title": "Engineer",
            "employer_name": "PeerSlate",
            "location_text": None,
            "summary": "Live wording",
            "start_date": "2026-09-01",
            "end_date": None,
            "date_precision": "month",
            "employment_type": "full_time",
            "current_role": True,
        },
        "resume_display": True,
        "visitor_ai": False,
        "private_assistance_excluded": False,
    }


class ResumeDraftRouteTests(unittest.TestCase):
    def setUp(self):
        self.catalog = InMemoryCanonicalCatalog()
        self.catalog.put_item("owner-api", role_item())
        self.catalog.put_item("owner-b", role_item())
        self.service = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(),
            catalog=self.catalog,
        )
        self.original = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS"),
            "PEERSLATE_RESUME_EDITOR_ENABLED": app.config.get("PEERSLATE_RESUME_EDITOR_ENABLED"),
            "RESUME_DRAFT_SERVICE": app.config.get("RESUME_DRAFT_SERVICE"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="owner-api",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_EDITOR_ENABLED=True,
            RESUME_DRAFT_SERVICE=self.service,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original)

    def test_flag_off_is_neutral_not_found(self):
        app.config["PEERSLATE_RESUME_EDITOR_ENABLED"] = False
        api = self.client.get("/api/resume-drafts/me")
        page = self.client.get("/app/resume")
        self.assertEqual(api.status_code, 404)
        self.assertEqual(page.status_code, 404)
        self.assertEqual(api.headers.get("Cache-Control"), "private, no-store")
        self.assertEqual(page.headers.get("Cache-Control"), "private, no-store")

    def test_unauthenticated_is_neutral_not_found(self):
        app.config.update(
            TESTING=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )
        api = self.client.get("/api/resume-drafts/me")
        page = self.client.get("/app/resume")
        self.assertEqual(api.status_code, 404)
        self.assertEqual(page.status_code, 302)
        self.assertIn("/auth/sign-in", page.headers.get("Location", ""))

    def test_writes_require_same_origin_and_ignore_client_owner(self):
        denied = self.client.post(
            "/api/resume-drafts/me/commands?user_key=foreign",
            json={
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "Mine"},
            },
        )
        self.assertEqual(denied.status_code, 403)
        saved = self.client.post(
            "/api/resume-drafts/me/commands?user_key=foreign",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "owner_user_key": "someone-else",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "Mine"},
            },
        )
        self.assertEqual(saved.status_code, 200)
        payload = saved.get_json()
        self.assertTrue(payload["success"])
        self.assertFalse(payload["publishes"])
        self.assertEqual(payload["item"]["proposed_values"]["summary"], "Mine")
        self.assertEqual(saved.headers.get("Cache-Control"), "private, no-store")

    def test_two_members_are_isolated(self):
        self.client.post(
            "/api/resume-drafts/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "Owner API overlay"},
            },
        )
        app.config["PEERSLATE_DEV_USER_KEY"] = "owner-b"
        other = self.client.get("/api/resume-drafts/me")
        self.assertEqual(other.status_code, 200)
        item = other.get_json()["items"][0]
        self.assertEqual(item["values"]["summary"], "Live wording")
        self.assertFalse(item["has_draft"])

    def test_editor_page_is_private_and_does_not_use_pete_fixture(self):
        page = self.client.get("/app/resume")
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        self.assertIn("Edit your Resume", html)
        self.assertIn("does not publish", html.lower())
        self.assertIn("Welcome, Local PeerSlate Test User.", html)
        self.assertNotIn("Welcome, Pete Carter", html)
        self.assertNotIn("resume2.css", html)
        self.assertIn('rel="stylesheet"', html)

    def test_review_route_does_not_publish(self):
        reviewed = self.client.post(
            "/api/resume-drafts/me/review",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4())},
        )
        self.assertEqual(reviewed.status_code, 200)
        payload = reviewed.get_json()
        self.assertFalse(payload["publishes"])
        self.assertEqual(payload["outcome"], "reviewed")

    def test_planned_rate_limits_cover_every_resume_draft_endpoint(self):
        from resume_draft_routes import PLANNED_RATE_LIMITS

        endpoints = {
            rule.endpoint
            for rule in app.url_map.iter_rules()
            if rule.endpoint.startswith("resume_draft.")
        }
        self.assertEqual(endpoints, set(PLANNED_RATE_LIMITS))


if __name__ == "__main__":
    unittest.main()
