"""Real Flask HTTP journeys for Resume publication. Not SQL engine proof."""

from __future__ import annotations

import unittest
from uuid import uuid4

from app import app
from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_publication_service import memory_resume_publication_service


def _create_displayed_role(policy, owner, summary="Led team 0."):
    entry_key = str(uuid4())
    policy.commit(
        owner,
        {
            "type": "create",
            "request_id": str(uuid4()),
            "entry_key": entry_key,
            "canonical_type": "role",
            "values": {
                "role_title": "Lead",
                "employer_name": "PeerSlate",
                "summary": summary,
            },
        },
    )
    listed = policy.list_entries(owner)["entries"]
    created = next(item for item in listed if item["entry_key"] == entry_key)
    policy.commit(
        owner,
        {
            "type": "change_permissions",
            "request_id": str(uuid4()),
            "entry_key": entry_key,
            "expected_access_revision": created["access_revision"],
            "permissions": {"resume_display": True, "visitor_ai": False},
        },
    )
    return entry_key


class ResumePublicationRouteTests(unittest.TestCase):
    def setUp(self):
        self.policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        self.service = memory_resume_publication_service()
        self.policy.publication_service = self.service
        self.service.policy_service = self.policy
        self.service.bind_slug("member-a", "alice")
        self.entry_key = _create_displayed_role(self.policy, "member-a")
        self.original = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS"),
            "PEERSLATE_RESUME_PUBLICATION_ENABLED": app.config.get("PEERSLATE_RESUME_PUBLICATION_ENABLED"),
            "RESUME_PUBLICATION_SERVICE": app.config.get("RESUME_PUBLICATION_SERVICE"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="member-a",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_PUBLICATION_ENABLED=True,
            RESUME_PUBLICATION_SERVICE=self.service,
        )

    def tearDown(self):
        app.config.update(self.original)

    def _client(self):
        return app.test_client()

    def _headers(self):
        return {"X-PeerSlate-Request": "same-origin"}

    def test_flag_off_is_not_found(self):
        app.config["PEERSLATE_RESUME_PUBLICATION_ENABLED"] = False
        client = self._client()
        self.assertEqual(client.get("/app/resume/publication").status_code, 404)
        self.assertEqual(client.get("/api/resume-publication/me/preview").status_code, 404)

    def test_review_does_not_publish(self):
        client = self._client()
        response = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["digest"])
        guest = client.get("/alice/resume")
        self.assertEqual(guest.status_code, 404)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_publish_guest_sees_result_and_private_cache(self):
        client = self._client()
        reviewed = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()
        published = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": reviewed["digest"],
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(published.status_code, 200)
        guest = client.get("/alice/resume")
        self.assertEqual(guest.status_code, 200)
        self.assertIn("private, no-store", guest.headers["Cache-Control"])
        self.assertIn("noindex", guest.headers.get("X-Robots-Tag", ""))
        self.assertIn("not the labeled Pete example", guest.get_data(as_text=True))
        self.assertIn("Led team 0.", guest.get_data(as_text=True))
        api = client.get("/api/public/profiles/alice/living-resume")
        self.assertEqual(api.status_code, 200)
        body = api.get_json()
        self.assertEqual(body["classification"], "member_publication")
        self.assertNotIn("visitor_ai", body["living_resume"])
        etag = api.headers["ETag"]
        cached = client.get(
            "/api/public/profiles/alice/living-resume",
            headers={"If-None-Match": etag},
        )
        self.assertEqual(cached.status_code, 304)
        head = client.head("/alice/resume")
        self.assertEqual(head.status_code, 200)

    def test_unknown_slug_does_not_fallback_to_pete_and_old_alias_redirects(self):
        client = self._client()
        self.assertEqual(client.get("/unknown-member/resume").status_code, 404)
        self.assertEqual(client.get("/unknown-member/resume2").status_code, 404)
        self.assertEqual(client.get("/alice/resume2").status_code, 404)
        reviewed = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()
        published = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": reviewed["digest"],
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(published.status_code, 200)
        redirect = client.get("/alice/resume2")
        self.assertEqual(redirect.status_code, 302)
        self.assertIn("/alice/resume", redirect.headers["Location"])
        media_alias = client.get("/alice/resume2/media/story_banner")
        self.assertEqual(media_alias.status_code, 302)

    def test_stale_publish_conflict_and_replay(self):
        client = self._client()
        digest = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()["digest"]
        request_id = str(uuid4())
        first = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": request_id,
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(first.status_code, 200)
        replay = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": request_id,
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertTrue(replay.get_json()["replayed"])
        conflict = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": request_id,
                "reviewed_digest": digest,
                "slug": "changed",
            },
            headers=self._headers(),
        )
        self.assertEqual(conflict.status_code, 409)

    def test_sharing_off_denies_guest_and_owner_preview_stays_private(self):
        client = self._client()
        digest = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()["digest"]
        client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        client.post(
            "/api/resume-publication/me/commands",
            json={"type": "sharing_off", "request_id": str(uuid4())},
            headers=self._headers(),
        )
        self.assertEqual(client.get("/alice/resume").status_code, 404)
        preview = client.get("/api/resume-publication/me/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertFalse(preview.get_json()["sharing_enabled"])

    def test_owner_page_uses_accepted_editor_visuals(self):
        client = self._client()
        page = client.get("/app/resume/publication")
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn("Review without publishing", body)
        self.assertIn("Publish reviewed Resume", body)
        self.assertIn("resume-publication.css", body)

    def test_media_reader_is_gated_and_supports_head(self):
        client = self._client()
        missing = client.get("/alice/resume/media/story_banner")
        self.assertEqual(missing.status_code, 404)
        head = client.head("/alice/resume/media/story_banner")
        self.assertEqual(head.status_code, 404)
        digest = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()["digest"]
        client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        after_publish = client.get("/alice/resume/media/story_banner")
        self.assertEqual(after_publish.status_code, 404)
        alias = client.get("/alice/resume2/media/story_banner")
        self.assertEqual(alias.status_code, 302)

    def test_sql_adapter_wrapped_54022_maps_to_http_409(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        class WrappedConflictDatabase:
            def first_row(self, name, params=None):
                return {
                    "request_digest": "a" * 64,
                    "request_id": "00000000-0000-4000-8000-000000000099",
                    "command_type": "publish",
                    "outcome": "published",
                    "publication_revision": 1,
                }

            def last_row(self, name, params=None):
                cause = RuntimeError(
                    "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
                    "That request already used a different payload. (54022)"
                )
                raise DatabaseServiceError(
                    "Database procedure usp_CommitResumePublicationCommandForOwner failed."
                ) from cause

        self.service.sql_repository = SqlResumePublicationRepository(
            database=WrappedConflictDatabase()
        )
        app.config["RESUME_PUBLICATION_SERVICE"] = self.service
        response = self._client().post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": "00000000-0000-4000-8000-000000000099",
                "reviewed_digest": "a" * 64,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "request_conflict")

    def test_sql_adapter_unrelated_failure_maps_to_http_503(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        class UnrelatedFailureDatabase:
            def first_row(self, name, params=None):
                return {
                    "request_digest": "a" * 64,
                    "request_id": "00000000-0000-4000-8000-000000000099",
                    "command_type": "publish",
                    "outcome": "published",
                    "publication_revision": 1,
                }

            def last_row(self, name, params=None):
                raise DatabaseServiceError(
                    "Database procedure usp_CommitResumePublicationCommandForOwner failed."
                ) from RuntimeError("login failed for user 'sa'")

        self.service.sql_repository = SqlResumePublicationRepository(
            database=UnrelatedFailureDatabase()
        )
        app.config["RESUME_PUBLICATION_SERVICE"] = self.service
        response = self._client().post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": "00000000-0000-4000-8000-000000000099",
                "reviewed_digest": "a" * 64,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "unavailable")

    def test_sql_manifest_failure_stays_http_503_with_or_without_number(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        for suffix in ("", " (54015)"):
            class ManifestFailureDatabase:
                def first_row(self, name, params=None):
                    return {"request_digest": "a" * 64, "request_id": "existing",
                            "command_type": "publish", "outcome": "published",
                            "publication_revision": 1}

                def last_row(self, name, params=None):
                    raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                        "Driver Error: [Microsoft][SQL Server]Canonical source is unavailable."
                        + suffix
                    )

            self.service.sql_repository = SqlResumePublicationRepository(ManifestFailureDatabase())
            app.config["RESUME_PUBLICATION_SERVICE"] = self.service
            response = self._client().post(
                "/api/resume-publication/me/commands",
                json={"type": "publish", "request_id": str(uuid4()),
                      "reviewed_digest": "a" * 64, "slug": "alice"},
                headers=self._headers(),
            )
            with self.subTest(suffix=suffix):
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json()["code"], "unavailable")

    def test_sql_numberless_correction_denial_maps_to_http_409(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        class CorrectionFailureDatabase:
            def first_row(self, name, params=None):
                return None

            def last_row(self, name, params=None):
                raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                    "Driver Error: [Microsoft][SQL Server]Entry is unavailable."
                )

        self.service.sql_repository = SqlResumePublicationRepository(CorrectionFailureDatabase())
        app.config["RESUME_PUBLICATION_SERVICE"] = self.service
        response = self._client().post(
            "/api/resume-publication/me/commands",
            json={"type": "correct", "request_id": str(uuid4()),
                  "entry_key": self.entry_key, "expected_content_version": 1,
                  "expected_access_revision": 1,
                  "values": {"summary": "Attempted correction."}},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "denied")


if __name__ == "__main__":
    unittest.main()
