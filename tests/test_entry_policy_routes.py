"""Flask wiring tests for the entry-policy API. No live database or identity."""

import unittest
from uuid import UUID, uuid4

from app import app
from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService


def key(n: int) -> str:
    return str(UUID(int=n, version=4))


class EntryPolicyRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        self.original = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS"),
            "PEERSLATE_ENTRY_POLICY_ENABLED": app.config.get("PEERSLATE_ENTRY_POLICY_ENABLED"),
            "ENTRY_POLICY_SERVICE": app.config.get("ENTRY_POLICY_SERVICE"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="owner-api",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_ENTRY_POLICY_ENABLED=True,
            ENTRY_POLICY_SERVICE=self.service,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original)

    def test_flag_off_is_neutral_not_found(self):
        app.config["PEERSLATE_ENTRY_POLICY_ENABLED"] = False
        response = self.client.get("/api/entry-policy/me/entries")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers.get("Cache-Control"), "private, no-store")

    def test_list_and_create_use_server_identity_and_same_origin(self):
        create = {
            "request_id": str(uuid4()),
            "type": "create",
            "entry_key": key(1),
            "canonical_type": "role",
            "values": {"role_title": "Engineer", "employer_name": "PeerSlate"},
        }
        denied = self.client.post(
            "/api/entry-policy/me/commands?user_key=foreign",
            json=create,
        )
        self.assertEqual(denied.status_code, 403)
        created = self.client.post(
            "/api/entry-policy/me/commands?user_key=foreign",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={**create, "owner_user_key": "someone-else"},
        )
        self.assertEqual(created.status_code, 200)
        payload = created.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["entries"][0]["entry_key"], key(1))
        self.assertFalse(payload["entries"][0]["resume_display"])
        self.assertEqual(created.headers.get("Cache-Control"), "private, no-store")
        listed = self.client.get("/api/entry-policy/me/entries")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()["entries"]), 1)
        self.assertFalse(listed.get_json()["capabilities"]["ai_provider_required"])
        stale = self.client.post(
            "/api/entry-policy/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "type": "edit",
                "entry_key": key(1),
                "expected_content_version": 9,
                "values": {"role_title": "Stale", "employer_name": "PeerSlate"},
            },
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["error_code"], "changed")
        fetched = self.client.get(f"/api/entry-policy/me/entries/{key(1)}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["entry"]["values"]["role_title"], "Engineer")

    def test_unauthenticated_is_not_found(self):
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=False, PEERSLATE_DEV_USER_KEY=None)
        response = self.client.get("/api/entry-policy/me/entries")
        self.assertEqual(response.status_code, 404)

    def test_planned_rate_limits_cover_every_entry_policy_endpoint(self):
        from entry_policy_routes import PLANNED_RATE_LIMITS

        endpoints = {
            rule.endpoint
            for rule in app.url_map.iter_rules()
            if rule.endpoint.startswith("entry_policy.")
        }
        self.assertEqual(set(PLANNED_RATE_LIMITS), endpoints)


if __name__ == "__main__":
    unittest.main()
