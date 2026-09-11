"""Real Flask HTTP journeys for the private Resume editor.

These tests issue actual requests through Flask's test client. They are not
browser-interception stubs. They also are not SQL engine proof, live identity
proof, or process-restart proof: injected in-memory stores are labeled as such.
"""

from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from app import app
from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService


ROLE_KEY = str(UUID(int=31, version=4))
EDU_KEY = str(UUID(int=32, version=4))


def published_role(summary="Canonical wording"):
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
            "summary": summary,
            "start_date": "2026-09-01",
            "end_date": None,
            "date_precision": "month",
            "employment_type": "full_time",
            "current_role": True,
        },
        "resume_display": True,
        "visitor_ai": True,
        "private_assistance_excluded": False,
    }


class ResumeEditorHttpTests(unittest.TestCase):
    def setUp(self):
        self.catalog = InMemoryCanonicalCatalog()
        self.repository = InMemoryResumeDraftRepository()
        self.catalog.put_item("member-a", published_role())
        self.catalog.put_item("member-b", published_role("B canonical"))
        self.service = ResumeDraftService(repository=self.repository, catalog=self.catalog)
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
            PEERSLATE_DEV_USER_KEY="member-a",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_EDITOR_ENABLED=True,
            RESUME_DRAFT_SERVICE=self.service,
        )

    def tearDown(self):
        app.config.update(self.original)

    def _client(self):
        return app.test_client()

    def _save(self, client, summary, request_id=None):
        return client.post(
            "/api/resume-drafts/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": request_id or str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": summary},
            },
        )

    def test_create_save_reopen_fresh_client_edit(self):
        first = self._client()
        page = first.get("/app/resume")
        self.assertEqual(page.status_code, 200)
        created = first.post(
            "/api/resume-drafts/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "type": "create_private_item",
                "record_key": EDU_KEY,
                "record_type": "education",
                "values": {
                    "title": "Certificate",
                    "institution_name": "Example University",
                    "degree_name": None,
                    "field_of_study": None,
                    "education_status": "completed",
                    "grade_text": None,
                    "location_text": None,
                    "summary": None,
                    "start_date": None,
                    "end_date": "2020-06-01",
                    "date_precision": "month",
                },
            },
        )
        self.assertEqual(created.status_code, 200)
        self.assertFalse(created.get_json()["item"]["resume_display"])
        saved = self._save(first, "Draft after create")
        self.assertEqual(saved.status_code, 200)
        reopened = first.get("/api/resume-drafts/me")
        self.assertEqual(reopened.status_code, 200)
        overlay = next(item for item in reopened.get_json()["items"] if item["record_key"] == ROLE_KEY)
        self.assertEqual(overlay["proposed_values"]["summary"], "Draft after create")

        fresh = self._client()
        again = fresh.get("/api/resume-drafts/me")
        self.assertEqual(again.status_code, 200)
        overlay = next(item for item in again.get_json()["items"] if item["record_key"] == ROLE_KEY)
        self.assertEqual(overlay["proposed_values"]["summary"], "Draft after create")
        edited = self._save(fresh, "Edited from a fresh client")
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.get_json()["item"]["proposed_values"]["summary"], "Edited from a fresh client")
        self.assertTrue(self.catalog.get_item("member-a", ROLE_KEY)["resume_display"])

    def test_lost_response_same_request_replays(self):
        client = self._client()
        request_id = str(uuid4())
        first = self._save(client, "Recover me", request_id=request_id)
        lost = self._save(client, "Recover me", request_id=request_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(lost.status_code, 200)
        self.assertTrue(lost.get_json()["replayed"])
        conflict = self._save(client, "Different body", request_id=request_id)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["proposed_values"]["summary"], "Different body")
        self.assertTrue(conflict.get_json()["input_preserved"])

    def test_stale_correction_and_restriction_do_not_clobber_input(self):
        client = self._client()
        self.catalog.bump_content("member-a", ROLE_KEY)
        stale = self._save(client, "Keep the member wording")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["proposed_values"]["summary"], "Keep the member wording")
        self.catalog.put_item("member-a", {**self.catalog.get_item("member-a", ROLE_KEY), "content_token": "1"})
        self.catalog.bump_access("member-a", ROLE_KEY)
        restricted = self._save(client, "Still keep this")
        self.assertEqual(restricted.status_code, 409)
        self.assertFalse(restricted.get_json()["conflicts"][0]["permissions_restored"])
        self.assertFalse(self.catalog.get_item("member-a", ROLE_KEY)["resume_display"])

    def test_two_members_and_unavailable_provider_preserve_input(self):
        client_a = self._client()
        self._save(client_a, "A only")
        app.config["PEERSLATE_DEV_USER_KEY"] = "member-b"
        client_b = self._client()
        listed = client_b.get("/api/resume-drafts/me")
        item = next(row for row in listed.get_json()["items"] if row["record_key"] == ROLE_KEY)
        self.assertEqual(item["values"]["summary"], "B canonical")
        self.assertFalse(item["has_draft"])

        class DownRepo:
            persistence_label = "sql_proposed_unapplied"

            def load_owner(self, owner):
                from services.resume_draft_repository import ResumeDraftStoreUnavailable

                raise ResumeDraftStoreUnavailable()

            def save_owner(self, owner, snapshot):
                from services.resume_draft_repository import ResumeDraftStoreUnavailable

                raise ResumeDraftStoreUnavailable()

        app.config["PEERSLATE_DEV_USER_KEY"] = "member-a"
        app.config["RESUME_DRAFT_SERVICE"] = ResumeDraftService(
            repository=DownRepo(),
            catalog=self.catalog,
        )
        down = self._client()
        failed = self._save(down, "Do not lose this")
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.get_json()["proposed_values"]["summary"], "Do not lose this")
        self.assertTrue(failed.get_json()["input_preserved"])
        self.assertNotIn("SQL", failed.get_data(as_text=True))

    def test_http_proof_is_labeled_and_not_engine_proof(self):
        client = self._client()
        workspace = client.get("/api/resume-drafts/me").get_json()
        self.assertEqual(workspace["capabilities"]["persistence"], "in_memory_not_live_db")
        self.assertFalse(workspace["capabilities"]["persistence_is_live_database"])
        self.assertFalse(workspace["capabilities"]["schema_applied"])
        self.assertFalse(workspace["capabilities"]["publishes"])


if __name__ == "__main__":
    unittest.main()
