import unittest
from unittest.mock import patch

from app import app
from identity import AuthenticationRequired
from services.journal_service import JournalServiceError


SAME_ORIGIN_HEADERS = {"X-PeerSlate-Request": "same-origin"}

VALID_MOMENT_BODY = {
    "idempotency_key": "client-generated-key-1",
    "moment_kind": "achievement",
    "title": "Shipped the private Journal backend",
    "narrative": "Wrote and reviewed the Slice J1 backend end to end.",
    "occurred_precision": "unknown",
}


class OwnerJournalFlagAndAuthTests(unittest.TestCase):
    """Flag-off and unauthenticated/unresolved requests must be identically
    neutral 404s that never distinguish "not signed in" from "not found"."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_JOURNAL_ENABLED")
        app.config["PEERSLATE_JOURNAL_ENABLED"] = False

    def tearDown(self):
        app.config["PEERSLATE_JOURNAL_ENABLED"] = self.original_flag

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_get_flag_off_is_neutral_404_before_identity_or_retrieval(
        self, identity, journal_service
    ):
        response = self.client.get("/api/journal/moments")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        identity.assert_not_called()
        journal_service.list_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_post_flag_off_is_neutral_404_before_identity_or_save(
        self, identity, journal_service
    ):
        response = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=VALID_MOMENT_BODY
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        identity.assert_not_called()
        journal_service.save_moment.assert_not_called()

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_get_flag_on_unauthenticated_is_neutral_404_not_401(
        self, identity, journal_service
    ):
        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get("/api/journal/moments")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        self.assertNotIn(b"PRIVATE", response.data)
        journal_service.list_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_post_flag_on_unauthenticated_is_neutral_404_not_401(
        self, identity, journal_service
    ):
        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=VALID_MOMENT_BODY
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        self.assertNotIn(b"PRIVATE", response.data)
        journal_service.save_moment.assert_not_called()

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_non_owner_unresolved_identity_is_also_neutral_404(
        self, identity, journal_service
    ):
        """A caller whose identity cannot be resolved to an owner gets the
        same neutral 404 as an unauthenticated caller - no distinct signal."""
        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("no owner profile resolved")

        response = self.client.get("/api/journal/moments?include_archived=true")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("count", response.get_data(as_text=True))
        self.assertNotIn(b"items", response.data)

    def test_journal_flag_defaults_off(self):
        self.assertIs(self.original_flag, False)

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_get_with_q_flag_off_is_neutral_404_before_identity_or_retrieval(
        self, identity, journal_service
    ):
        """The additive ?q= search path must honor the exact same flag gate
        as the list path - a query string never bypasses it."""
        response = self.client.get("/api/journal/moments?q=shipped")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        identity.assert_not_called()
        journal_service.search_owner_journal.assert_not_called()
        journal_service.list_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    @patch("peerslate_api.get_current_identity")
    def test_get_with_q_flag_on_unauthenticated_is_neutral_404_not_401(
        self, identity, journal_service
    ):
        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get("/api/journal/moments?q=shipped")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        self.assertNotIn(b"PRIVATE", response.data)
        journal_service.search_owner_journal.assert_not_called()


class OwnerJournalRouteTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="journal-owner-1",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("peerslate_api.journal_service")
    def test_get_returns_items_and_next_cursor_scoped_to_caller(self, journal_service):
        journal_service.list_owner_journal.return_value = {
            "items": [{"moment_key": "11111111-1111-1111-1111-111111111111"}],
            "next_cursor": "opaque-cursor-token",
        }

        response = self.client.get("/api/journal/moments")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["next_cursor"], "opaque-cursor-token")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        journal_service.list_owner_journal.assert_called_once_with(
            "journal-owner-1", include_archived=False, limit=50, cursor=None
        )

    @patch("peerslate_api.journal_service")
    def test_get_parses_include_archived_limit_and_cursor(self, journal_service):
        journal_service.list_owner_journal.return_value = {"items": [], "next_cursor": None}

        self.client.get(
            "/api/journal/moments?include_archived=true&limit=5&cursor=abc"
        )

        journal_service.list_owner_journal.assert_called_once_with(
            "journal-owner-1", include_archived=True, limit=5, cursor="abc"
        )

    @patch("peerslate_api.journal_service")
    def test_get_rejects_non_numeric_limit(self, journal_service):
        response = self.client.get("/api/journal/moments?limit=not-a-number")

        self.assertEqual(response.status_code, 400)
        journal_service.list_owner_journal.assert_not_called()

    def test_post_requires_same_origin_header(self):
        response = self.client.post("/api/journal/moments", json=VALID_MOMENT_BODY)

        self.assertEqual(response.status_code, 403)

    def test_post_rejects_cross_origin_requests(self):
        response = self.client.post(
            "/api/journal/moments",
            headers={**SAME_ORIGIN_HEADERS, "Origin": "https://attacker.example"},
            json=VALID_MOMENT_BODY,
        )

        self.assertEqual(response.status_code, 403)

    @patch("peerslate_api.journal_service")
    def test_post_saves_and_scopes_to_caller_with_idempotency_key(self, journal_service):
        journal_service.save_moment.return_value = {
            "moment_key": "22222222-2222-2222-2222-222222222222",
            "version": 1,
            "saved": True,
        }

        response = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=VALID_MOMENT_BODY
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertTrue(payload["saved"])
        self.assertEqual(payload["moment_key"], "22222222-2222-2222-2222-222222222222")
        self.assertEqual(payload["version"], 1)

        args, kwargs = journal_service.save_moment.call_args
        self.assertEqual(args[0], "journal-owner-1")
        self.assertEqual(args[1], "client-generated-key-1")
        self.assertEqual(args[2]["title"], VALID_MOMENT_BODY["title"])
        self.assertEqual(args[2]["narrative"], VALID_MOMENT_BODY["narrative"])

    @patch("peerslate_api.journal_service")
    def test_post_repeated_idempotency_key_never_reports_two_different_moments(
        self, journal_service
    ):
        journal_service.save_moment.return_value = {
            "moment_key": "33333333-3333-3333-3333-333333333333",
            "version": 1,
            "saved": True,
        }

        first = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=VALID_MOMENT_BODY
        )
        second = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=VALID_MOMENT_BODY
        )

        self.assertEqual(first.get_json()["moment_key"], second.get_json()["moment_key"])
        self.assertEqual(journal_service.save_moment.call_count, 2)

    @patch("peerslate_api.journal_service")
    def test_post_missing_required_fields_is_rejected_before_save(self, journal_service):
        response = self.client.post(
            "/api/journal/moments",
            headers=SAME_ORIGIN_HEADERS,
            json={"idempotency_key": "client-generated-key-2"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])
        journal_service.save_moment.assert_not_called()

    def test_post_missing_idempotency_key_is_rejected_before_save(self):
        body = {key: value for key, value in VALID_MOMENT_BODY.items() if key != "idempotency_key"}

        response = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=body
        )

        self.assertEqual(response.status_code, 400)

    @patch("peerslate_api.journal_service")
    def test_post_false_save_guard_never_reports_success(self, journal_service):
        journal_service.save_moment.side_effect = JournalServiceError("changed")

        response = self.client.post(
            "/api/journal/moments", headers=SAME_ORIGIN_HEADERS, json=VALID_MOMENT_BODY
        )

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertNotIn("moment_key", payload)
        self.assertNotIn("saved", payload)

    @patch("peerslate_api.journal_service")
    def test_get_never_leaks_another_owners_scope_when_forced(self, journal_service):
        """Even if a caller supplies a user_key-shaped query parameter, the
        service is always called with the server-resolved identity only."""
        journal_service.list_owner_journal.return_value = {"items": [], "next_cursor": None}

        self.client.get("/api/journal/moments?user_key=someone-else")

        journal_service.list_owner_journal.assert_called_once_with(
            "journal-owner-1", include_archived=False, limit=50, cursor=None
        )


class OwnerJournalSearchRouteTests(unittest.TestCase):
    """Slice J1.1: the additive ?q= parameter on GET /api/journal/moments."""

    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="journal-owner-1",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("peerslate_api.journal_service")
    def test_get_without_q_calls_list_not_search_byte_identical_to_before(self, journal_service):
        """The no-q path must remain exactly the pre-J1.1 list behavior."""
        journal_service.list_owner_journal.return_value = {
            "items": [{"moment_key": "11111111-1111-1111-1111-111111111111"}],
            "next_cursor": "opaque-cursor-token",
        }

        response = self.client.get("/api/journal/moments")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["next_cursor"], "opaque-cursor-token")
        journal_service.list_owner_journal.assert_called_once_with(
            "journal-owner-1", include_archived=False, limit=50, cursor=None
        )
        journal_service.search_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    def test_get_with_q_calls_search_not_list_and_scopes_to_caller(self, journal_service):
        journal_service.search_owner_journal.return_value = {
            "items": [{"moment_key": "22222222-2222-2222-2222-222222222222"}],
            "next_cursor": "opaque-cursor-token-2",
        }

        response = self.client.get("/api/journal/moments?q=shipped")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["next_cursor"], "opaque-cursor-token-2")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        journal_service.search_owner_journal.assert_called_once_with(
            "journal-owner-1", "shipped", include_archived=False, limit=50, cursor=None
        )
        journal_service.list_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    def test_get_with_q_parses_include_archived_limit_and_cursor(self, journal_service):
        journal_service.search_owner_journal.return_value = {"items": [], "next_cursor": None}

        self.client.get(
            "/api/journal/moments?q=shipped&include_archived=true&limit=5&cursor=abc"
        )

        journal_service.search_owner_journal.assert_called_once_with(
            "journal-owner-1", "shipped", include_archived=True, limit=5, cursor="abc"
        )

    @patch("peerslate_api.journal_service")
    def test_get_with_empty_q_is_rejected_with_400(self, journal_service):
        journal_service.search_owner_journal.side_effect = JournalServiceError("required")

        response = self.client.get("/api/journal/moments?q=")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    @patch("peerslate_api.journal_service")
    def test_get_with_whitespace_only_q_is_rejected_with_400(self, journal_service):
        journal_service.search_owner_journal.side_effect = JournalServiceError("required")

        response = self.client.get("/api/journal/moments?q=%20%20")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    @patch("peerslate_api.journal_service")
    def test_get_with_overlength_q_is_rejected_with_400_before_calling_service(
        self, journal_service
    ):
        response = self.client.get("/api/journal/moments?q=" + "x" * 201)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])
        journal_service.search_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    def test_get_with_q_at_max_length_is_accepted(self, journal_service):
        journal_service.search_owner_journal.return_value = {"items": [], "next_cursor": None}

        response = self.client.get("/api/journal/moments?q=" + "x" * 200)

        self.assertEqual(response.status_code, 200)
        journal_service.search_owner_journal.assert_called_once()

    @patch("peerslate_api.journal_service")
    def test_get_with_q_rejects_non_numeric_limit_before_calling_service(self, journal_service):
        response = self.client.get("/api/journal/moments?q=shipped&limit=not-a-number")

        self.assertEqual(response.status_code, 400)
        journal_service.search_owner_journal.assert_not_called()

    @patch("peerslate_api.journal_service")
    def test_get_with_q_never_leaks_another_owners_scope_when_forced(self, journal_service):
        """Even if a caller supplies a user_key-shaped query parameter, the
        service is always called with the server-resolved identity only."""
        journal_service.search_owner_journal.return_value = {"items": [], "next_cursor": None}

        self.client.get("/api/journal/moments?q=shipped&user_key=someone-else")

        journal_service.search_owner_journal.assert_called_once_with(
            "journal-owner-1", "shipped", include_archived=False, limit=50, cursor=None
        )


if __name__ == "__main__":
    unittest.main()
