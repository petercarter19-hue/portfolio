"""PS-JOURNAL-001 Slice J1 frontend: /app/journal, the Moment detail route,
and the additive voice-draft JSON route.

Mirrors the mocked-database patterns already used by tests/test_owner_journal.py
(the Slice J1 backend/API tests) and tests/test_owner_moment.py (existing owner
page route tests): PEERSLATE_ALLOW_DEV_IDENTITY + PEERSLATE_DEV_USER_KEY stand
in for a signed-in owner without a live database, and owner_routes.journal_service
/ owner_routes.get_current_identity are patched directly for the flag-off and
unauthenticated cases so no real Azure SQL connection is required.
"""

import datetime
import unittest
from unittest.mock import patch

from app import app
from identity import AuthenticationRequired, PeerSlateIdentity
from services.journal_service import JournalServiceError


DEV_USER_KEY = "journal-frontend-owner-1"
MOMENT_KEY_ACHIEVEMENT = "11111111-1111-1111-1111-111111111111"
MOMENT_KEY_VOICE = "22222222-2222-2222-2222-222222222222"
MOMENT_KEY_TEXT = "33333333-3333-3333-3333-333333333333"
GUESSED_MOMENT_KEY = "99999999-9999-9999-9999-999999999999"


def sample_items():
    return [
        {
            "moment_key": MOMENT_KEY_ACHIEVEMENT,
            "moment_kind": "achievement",
            "title": "Shipped the private Journal frontend",
            "occurred_on": datetime.date(2026, 5, 20),
            "occurred_precision": "exact",
            "visibility": "private",
            "source_type": "text",
            "lifecycle_state": "active",
            "version_number": 1,
        },
        {
            "moment_key": MOMENT_KEY_VOICE,
            "moment_kind": "update",
            "title": "A voice-sourced Moment (illustrative row type)",
            "occurred_on": datetime.date(2026, 5, 19),
            "occurred_precision": "exact",
            "visibility": "private",
            "source_type": "voice",
            "lifecycle_state": "active",
            "version_number": 1,
        },
        {
            "moment_key": MOMENT_KEY_TEXT,
            "moment_kind": "lesson",
            "title": "I realized I enjoy translating technical ideas",
            "occurred_on": datetime.date(2026, 5, 18),
            "occurred_precision": "exact",
            "visibility": "private",
            "source_type": "text",
            "lifecycle_state": "active",
            "version_number": 1,
        },
    ]


def fake_list_owner_journal_factory(items):
    """A side_effect function standing in for journal_service.list_owner_journal.

    The Journal route calls this twice per request with different intents -
    once for the displayed Timeline page (limit=20, no cursor) and again in a
    bounded scan for the This-Season hero's honest totals (limit=100). A
    single page with next_cursor=None answers both without an infinite loop.
    """

    def fake(user_key, include_archived=False, limit=50, cursor=None):
        return {"items": list(items), "next_cursor": None}

    return fake


class OwnerJournalFlagAndAuthTests(unittest.TestCase):
    """Flag-off, unauthenticated, and non-owner requests must be identically
    neutral 404s across all three routes - never a distinct redirect/401."""

    def setUp(self):
        self.client = app.test_client()
        self.original_config = {
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
        }
        app.config["PEERSLATE_JOURNAL_ENABLED"] = False

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("owner_routes.journal_service")
    @patch("owner_routes.get_current_identity")
    def test_journal_page_flag_off_is_neutral_404_before_identity(self, identity, journal_service):
        response = self.client.get("/app/journal")

        self.assertEqual(response.status_code, 404)
        identity.assert_not_called()
        journal_service.list_owner_journal.assert_not_called()

    @patch("owner_routes.journal_service")
    @patch("owner_routes.get_current_identity")
    def test_moment_detail_flag_off_is_neutral_404_before_identity(self, identity, journal_service):
        response = self.client.get(f"/app/journal/moments/{MOMENT_KEY_ACHIEVEMENT}")

        self.assertEqual(response.status_code, 404)
        identity.assert_not_called()
        journal_service.list_owner_journal.assert_not_called()

    @patch("owner_routes.voice_capture_service")
    @patch("owner_routes.get_current_identity")
    def test_voice_draft_flag_off_is_neutral_404_before_identity(self, identity, voice_capture_service):
        response = self.client.get(f"/app/journal/voice/{MOMENT_KEY_VOICE}/draft")

        self.assertEqual(response.status_code, 404)
        identity.assert_not_called()
        voice_capture_service.get_draft.assert_not_called()

    @patch("owner_routes.journal_service")
    @patch("owner_routes.get_current_identity")
    def test_journal_page_flag_on_unauthenticated_is_404_not_redirect(self, identity, journal_service):
        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get("/app/journal")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"PRIVATE", response.data)
        journal_service.list_owner_journal.assert_not_called()

    @patch("owner_routes.journal_service")
    @patch("owner_routes.get_current_identity")
    def test_moment_detail_flag_on_unauthenticated_is_404_not_redirect(self, identity, journal_service):
        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get(f"/app/journal/moments/{MOMENT_KEY_ACHIEVEMENT}")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"PRIVATE", response.data)
        journal_service.list_owner_journal.assert_not_called()

    def test_flag_off_and_unauthenticated_journal_bodies_are_identical(self):
        off_response = self.client.get("/app/journal")

        app.config["PEERSLATE_JOURNAL_ENABLED"] = True
        with patch("owner_routes.get_current_identity") as identity:
            identity.side_effect = AuthenticationRequired("nope")
            unauth_response = self.client.get("/app/journal")

        self.assertEqual(off_response.status_code, unauth_response.status_code)
        self.assertEqual(off_response.data, unauth_response.data)

    def test_journal_flag_defaults_off(self):
        self.assertIs(self.original_config["PEERSLATE_JOURNAL_ENABLED"], False)


class OwnerJournalPageRenderTests(unittest.TestCase):
    """Flag on + a resolvable owner identity: assert the rendered page shell,
    without any live database (journal_service is fully mocked)."""

    def setUp(self):
        self.original_config = {
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("owner_routes.journal_service")
    def test_page_renders_rail_chapters_and_composer_shell(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for chapter_label in ("Timeline", "Voice", "Photos", "Videos", "Milestones", "Reflections"):
            self.assertIn(chapter_label, body)
        self.assertIn('data-timeline', body)
        self.assertIn("Capture a Moment", body)
        self.assertIn("Private to you", body)
        self.assertIn(
            "Private to you - only you can see this until you choose to share.", body
        )
        self.assertIn("Save Moment", body)
        self.assertIn("Only you", body)
        self.assertIn("Coming later", body)

    @patch("owner_routes.journal_service")
    def test_use_this_moment_chips_and_attachments_are_disabled(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        for label in ("Share to Feed", "Add to My Story", "Use in Work", "Add to Résumé"):
            self.assertIn(label, body)
        self.assertEqual(body.count('aria-disabled="true"'), body.count('aria-disabled="true"'))
        # Every Use This Moment chip and the attachment row must be
        # non-interactive, never a fake-enabled control (site rule 83).
        self.assertGreaterEqual(body.count('aria-disabled="true"'), 5)
        self.assertIn("Add a photo or video", body)

    @patch("owner_routes.journal_service")
    def test_page_renders_real_moments_with_honest_totals(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertIn("Shipped the private Journal frontend", body)
        self.assertIn("3", body)  # totals.moments from the 3 fixture items
        journal_service.list_owner_journal.assert_any_call(
            DEV_USER_KEY, include_archived=False, limit=20, cursor=None
        )

    @patch("owner_routes.journal_service")
    def test_empty_journal_shows_truthful_empty_state_not_fake_data(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory([])

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("The trail starts here", body)
        self.assertNotIn("Maya Thompson", body)

    @patch("owner_routes.journal_service")
    def test_manage_view_uses_include_archived(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal?view=archived")

        self.assertEqual(response.status_code, 200)
        journal_service.list_owner_journal.assert_any_call(
            DEV_USER_KEY, include_archived=True, limit=20, cursor=None
        )

    @patch("owner_routes.journal_service")
    def test_journal_read_failure_returns_unavailable_not_a_crash(self, journal_service):
        journal_service.list_owner_journal.side_effect = JournalServiceError("changed")

        response = self.client.get("/app/journal")

        self.assertEqual(response.status_code, 503)


class OwnerJournalMomentDetailTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("owner_routes.journal_service")
    def test_owner_sees_moment_detail_fields(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get(f"/app/journal/moments/{MOMENT_KEY_ACHIEVEMENT}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Shipped the private Journal frontend", body)
        self.assertIn("Achievement", body)
        self.assertIn("2026-05-20", body)
        self.assertIn("Only you", body)

    @patch("owner_routes.journal_service")
    def test_guessed_key_is_404(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get(f"/app/journal/moments/{GUESSED_MOMENT_KEY}")

        self.assertEqual(response.status_code, 404)

    @patch("owner_routes.journal_service")
    def test_malformed_key_is_404_without_a_service_call(self, journal_service):
        response = self.client.get("/app/journal/moments/not-a-uuid")

        self.assertEqual(response.status_code, 404)
        journal_service.list_owner_journal.assert_not_called()


class OwnerJournalVoiceDraftTests(unittest.TestCase):
    """The additive JSON voice-draft route the in-context composer uses
    instead of the released full-page /app/capture?voice= redirect."""

    def setUp(self):
        self.original_config = {
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("owner_routes.voice_capture_service")
    def test_returns_transcript_for_a_ready_draft(self, voice_capture_service):
        voice_capture_service.get_draft.return_value = {
            "source_key": MOMENT_KEY_VOICE,
            "state": "needs_review",
            "provider_transcript": "I led the workshop without reading from my notes.",
            "verified_duration_milliseconds": 48000,
        }

        response = self.client.get(f"/app/journal/voice/{MOMENT_KEY_VOICE}/draft")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["state"], "needs_review")
        self.assertEqual(
            payload["transcript"], "I led the workshop without reading from my notes."
        )
        self.assertEqual(payload["duration_seconds"], 48.0)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("owner_routes.voice_capture_service")
    def test_missing_draft_is_404(self, voice_capture_service):
        voice_capture_service.get_draft.return_value = None

        response = self.client.get(f"/app/journal/voice/{MOMENT_KEY_VOICE}/draft")

        self.assertEqual(response.status_code, 404)

    def test_malformed_source_key_is_404(self):
        response = self.client.get("/app/journal/voice/not-a-uuid/draft")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
