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
import os
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from identity import AuthenticationRequired, PeerSlateIdentity
from playwright.sync_api import sync_playwright
from services.journal_service import JournalServiceError
from werkzeug.serving import make_server


DEV_USER_KEY = "journal-frontend-owner-1"
MOMENT_KEY_ACHIEVEMENT = "11111111-1111-1111-1111-111111111111"
MOMENT_KEY_VOICE = "22222222-2222-2222-2222-222222222222"
MOMENT_KEY_TEXT = "33333333-3333-3333-3333-333333333333"
GUESSED_MOMENT_KEY = "99999999-9999-9999-9999-999999999999"
CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


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

    def test_journal_shell_exception_does_not_change_a_public_shell(self):
        response = self.client.get("/peerslate")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="profile-tabs', body)
        self.assertIn('data-open-chat', body)
        self.assertIn('id="chat-toggle"', body)


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
        self.assertIn("Only you can see this until you choose to share.", body)
        self.assertIn("Save Moment", body)
        self.assertIn("Only you", body)
        self.assertIn("Coming later", body)
        # The private Journal must not inherit a public-profile tab strip or
        # Ask Pete assistant launcher from the broad site shell.
        self.assertNotIn('data-open-chat', body)
        self.assertNotIn('id="chat-toggle"', body)
        self.assertNotIn('class="profile-tabs"', body)

    @patch("owner_routes.journal_service")
    def test_use_this_moment_chips_and_attachments_are_disabled(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        for label in ("Share to Feed", "Add to My Story", "Use in Work", "Add to Résumé"):
            self.assertIn(label, body)
        # Opus review N5 fix: this used to assert
        # body.count(...) == body.count(...) - always true regardless of the
        # actual count, so it could never catch a fake-enabled control. The
        # The real, precise count for this fixture is the four Use This
        # Moment chips, the visibly locked audience selector, and one disabled
        # voice-play control per voice-sourced row. This catches a fake-enabled
        # future destination or playback control.
        voice_row_count = sum(1 for item in sample_items() if item["source_type"] == "voice")
        expected_disabled_count = 5 + voice_row_count
        self.assertEqual(body.count('aria-disabled="true"'), expected_disabled_count)
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
        # Doc 15 item 37 supersedes doc 13: quote attribution is dynamic to
        # the authenticated member, never fixed to the accepted fixture.
        self.assertIn("Your story starts here.", body)
        self.assertIn("The pages are yours.", body)
        self.assertNotIn("&mdash; Pete", body)
        self.assertIn("&mdash; Local", body)
        self.assertNotIn("Maya Thompson", body)
        # S2: the zero-count This-Season hero is fully suppressed on a
        # genuinely empty first visit, not just visually deemphasized.
        self.assertNotIn("This season", body)
        self.assertNotIn("Moments captured", body)
        journal_css = (Path(__file__).resolve().parent.parent / "static" / "css" / "journal.css").read_text(encoding="utf-8")
        # Generic chapter-empty messages stay hidden until a rail filter
        # selects them; this guards against base CSS exposing empty bars.
        self.assertIn(".ps-journal__empty[hidden]", journal_css)
        self.assertIn("display: none !important;", journal_css)
        self.assertIn(".ps-journal__manage-ghost", journal_css)

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
    def test_manage_view_uses_the_compact_control_structure(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal?view=manage")
        body = response.get_data(as_text=True)
        journal_css = (Path(__file__).resolve().parent.parent / "static" / "css" / "journal.css").read_text(encoding="utf-8")

        self.assertEqual(response.status_code, 200)
        for class_name in (
            "ps-journal__book--manage",
            "ps-journal__manage-controls",
            "ps-journal__manage-select",
            "ps-journal__manage-pill",
            "ps-journal__manage-icon-btn",
        ):
            self.assertIn(class_name, body)
            self.assertIn(f".{class_name}", journal_css)
        self.assertIn("appearance: none;", journal_css)
        self.assertIn("grid-template-columns: minmax(12rem, 1.45fr)", journal_css)

    @patch("owner_routes.journal_service")
    def test_journal_read_failure_returns_unavailable_not_a_crash(self, journal_service):
        journal_service.list_owner_journal.side_effect = JournalServiceError("changed")

        response = self.client.get("/app/journal")

        self.assertEqual(response.status_code, 503)
        body = response.get_data(as_text=True)
        self.assertIn("Your Journal is temporarily unavailable.", body)
        self.assertIn("Your private Moments are not shown here", body)
        self.assertNotIn("Sign in is not configured", body)


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
        # Doc 15 visual-finish pass: the accepted screen B meta row is
        # "<time>路 <source label> 路 Private" only (verified against the
        # accepted PNG) - it never prints the moment_kind word ("Achievement"
        # etc). That word was a pre-doc-15 styling detail, not a behavioral
        # or security assertion, so this rewritten check confirms the real
        # accepted-mockup meta shape instead of asserting removed copy.
        self.assertIn("Text Note", body)
        self.assertNotIn(">Achievement<", body)
        # B2 rewrite (Opus review): the debug dt/dd grid that used to print
        # a single "2026-05-20" ISO string is gone - the accepted-screen-B
        # date numeral renders day/month/year as separate elements instead.
        self.assertIn(">20<", body)
        self.assertIn(">MAY<", body)
        self.assertIn(">2026<", body)
        self.assertIn("Only you", body)
        self.assertIn("Back to timeline", body)
        self.assertNotIn("Back to Journal", body)
        self.assertIn("Journal sections", body)
        for chapter_label in ("Timeline", "Voice", "Photos", "Videos", "Milestones", "Reflections"):
            self.assertIn(chapter_label, body)
        # B2: no internal jargon or stored-procedure names leak into
        # member-facing copy.
        self.assertNotIn("usp_", body)
        self.assertNotIn("J1.1", body)

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


class JournalEvidenceFixtureIsolationTests(unittest.TestCase):
    """Doc 15 fixture richness must be possible for visual evidence without
    allowing production records to collide with fixture presentation data."""

    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_JOURNAL_EVIDENCE_FIXTURES": app.config.get(
                "PEERSLATE_JOURNAL_EVIDENCE_FIXTURES"
            ),
            "PEERSLATE_JOURNAL_EVIDENCE_STATE": app.config.get(
                "PEERSLATE_JOURNAL_EVIDENCE_STATE"
            ),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_JOURNAL_EVIDENCE_FIXTURES=True,
            PEERSLATE_JOURNAL_EVIDENCE_STATE="timeline",
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    @patch("owner_routes.journal_service")
    def test_test_only_timeline_fixture_is_exact_and_never_calls_member_read(self, journal_service):
        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        journal_service.list_owner_journal.assert_not_called()
        self.assertIn('data-journal-evidence-fixture="true"', body)
        for day in ("20", "19", "18", "13"):
            self.assertIn(f">{day}<", body)
        self.assertNotIn(">17<", body)
        self.assertNotIn(">16<", body)
        self.assertNotIn(">15<", body)
        self.assertIn("9:41 AM", body)
        self.assertIn("Attached to this Moment", body)
        self.assertIn("images/journal/maya-fixture-hero-v1.png", body)
        self.assertIn("images/journal/mountain-lake-fixture-v3.png", body)
        self.assertIn("images/journal/workshop-stage-fixture-v3.png", body)
        self.assertNotIn('aria-controls="journal-panel-timeline"', body)

    @patch("owner_routes.journal_service")
    def test_test_only_detail_fixture_is_rich_without_a_member_read(self, journal_service):
        response = self.client.get(
            "/app/journal/moments/e1111111-1111-1111-1111-111111111111"
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        journal_service.list_owner_journal.assert_not_called()
        self.assertIn("Felt prepared, present, and confident.", body)
        self.assertIn("1 version", body)
        self.assertIn("Created May 20, 2024", body)
        self.assertIn("Back to timeline", body)

    @patch("owner_routes.journal_service")
    def test_test_only_manage_fixture_is_exact_and_never_calls_member_read(self, journal_service):
        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "manage"

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        journal_service.list_owner_journal.assert_not_called()
        self.assertIn("68 Moments", body)
        for label in ("Voice", "Text", "Photo", "Video"):
            self.assertIn(label, body)
        for day in ("20", "19", "18", "17", "16", "15"):
            self.assertIn(f">{day}<", body)
        self.assertNotIn(">13<", body)
        # Duration is metadata on the voice Moment, not a video-only field:
        # May 20 is voice-backed but deliberately has no video thumbnail.
        self.assertIn('class="ps-journal__manage-duration">00:48</span>', body)

    @patch("owner_routes.journal_service")
    def test_test_only_saved_fixture_is_visible_without_a_write_or_member_read(self, journal_service):
        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "saved"

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        journal_service.list_owner_journal.assert_not_called()
        self.assertIn('data-evidence-saved="true"', body)
        self.assertIn('data-composer-view="compose" hidden', body)
        self.assertIn('data-composer-view="saved">', body)
        self.assertIn("Moment saved privately", body)

    @patch("owner_routes.journal_service")
    def test_fixture_mode_cannot_be_requested_by_url(self, journal_service):
        app.config["PEERSLATE_JOURNAL_EVIDENCE_FIXTURES"] = False
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal?evidence=manage")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        # The query cannot opt an identity into the test provider.  With the
        # explicit server switch off, the normal authorized read is required.
        self.assertTrue(journal_service.list_owner_journal.called)
        self.assertNotIn('data-journal-evidence-fixture="true"', body)
        self.assertNotIn("68 Moments", body)

    @patch("owner_routes.journal_service")
    @patch("owner_routes.get_current_identity")
    def test_same_title_never_enriches_two_real_members(self, identity, journal_service):
        # The config key is deliberately left true. TESTING=false is the
        # production gate: neither owner can ever enter fixture presentation.
        app.config["TESTING"] = False
        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "saved"
        fixture_title = "I led the first client workshop without reading from my notes."
        real_item = {
            "moment_key": MOMENT_KEY_TEXT,
            "moment_kind": "update",
            "title": fixture_title,
            "occurred_on": datetime.date(2026, 5, 20),
            "occurred_precision": "exact",
            "visibility": "private",
            "source_type": "text",
            "lifecycle_state": "active",
            "version_number": 1,
        }
        identity.side_effect = (
            PeerSlateIdentity("real-owner-one", "test", "issuer", "one", display_name="Avery"),
            PeerSlateIdentity("real-owner-two", "test", "issuer", "two", display_name="Blair"),
        )
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory([real_item])

        first = self.client.get("/app/journal").get_data(as_text=True)
        second = self.client.get("/app/journal").get_data(as_text=True)

        for body in (first, second):
            self.assertIn(fixture_title, body)
            self.assertNotIn("9:41 AM", body)
            self.assertNotIn("Felt prepared, present, and confident.", body)
            self.assertNotIn("thumbnail_kind", body)
            self.assertNotIn('data-journal-evidence-fixture="true"', body)
            self.assertNotIn("data-fixture-attached", body)
            self.assertNotIn("images/cinematic/story-sunset-bg.jpg", body)
        owner_keys = [call.args[0] for call in journal_service.list_owner_journal.call_args_list]
        self.assertIn("real-owner-one", owner_keys)
        self.assertIn("real-owner-two", owner_keys)

    def test_client_draft_never_uses_persistent_browser_storage(self):
        js_path = Path(__file__).resolve().parent.parent / "static" / "js" / "journal.js"
        js_source = js_path.read_text(encoding="utf-8")

        self.assertNotIn("localStorage", js_source)
        self.assertNotIn("sessionStorage", js_source)
        self.assertIn("let recoverableDraft", js_source)

    def test_composer_close_and_mobile_footer_have_explicit_visual_guards(self):
        css_path = Path(__file__).resolve().parent.parent / "static" / "css" / "journal.css"
        journal_css = css_path.read_text(encoding="utf-8")

        self.assertIn(".ps-composer__close", journal_css)
        self.assertIn("position: absolute;", journal_css)
        self.assertIn("width: 2.35rem;", journal_css)
        self.assertIn(".ps-composer__footer", journal_css)
        self.assertIn("bottom: 0.8rem;", journal_css)


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
        # Opus review N5 fix: assert ownership threading - the route must
        # call get_draft with THIS caller's own user_key (never a client-
        # supplied value), so a draft can never be read across owners.
        voice_capture_service.get_draft.assert_called_once_with(
            DEV_USER_KEY, MOMENT_KEY_VOICE
        )

    @patch("owner_routes.voice_capture_service")
    def test_missing_draft_is_404(self, voice_capture_service):
        voice_capture_service.get_draft.return_value = None

        response = self.client.get(f"/app/journal/voice/{MOMENT_KEY_VOICE}/draft")

        self.assertEqual(response.status_code, 404)

    def test_malformed_source_key_is_404(self):
        response = self.client.get("/app/journal/voice/not-a-uuid/draft")

        self.assertEqual(response.status_code, 404)

    @patch("owner_routes.voice_capture_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_on_unauthenticated_is_404_not_redirect(
        self, identity, voice_capture_service
    ):
        """Opus review N5: the three flag-off/unauthenticated matrix cells
        already covered the Journal page and Moment detail routes but not
        this third owner-only route - flag on + no resolvable identity must
        still be the same neutral 404, never a distinct 401/redirect that
        would leak "not signed in" versus "not found"."""
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get(f"/app/journal/voice/{MOMENT_KEY_VOICE}/draft")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"PRIVATE", response.data)
        voice_capture_service.get_draft.assert_not_called()


class JournalMomentsApiDateFormatTests(unittest.TestCase):
    """Opus review N5: static/js/journal.js's client-side date parsing
    (formatOccurred, formatOccurredIso) depends on a documented assumption -
    that Flask's jsonify serializes a Python date as an RFC 822/1123 string
    with a "GMT" suffix, not a bare ISO "YYYY-MM-DD" string. There is no
    JS test runner in this repository (no package.json/jest/node harness),
    so this is the automated, server-side half of that contract: it proves
    exactly what shape date /api/journal/moments actually sends the browser.
    The client-side parsing logic itself (Date/getUTCDate/toLocaleString)
    is covered by manual/documented evidence - the desktop timeline
    screenshots in artifacts/ps-journal-001-j1-frontend/ show real dates
    ("20 MAY") rendered correctly from this exact response shape."""

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

    @patch("peerslate_api.journal_service")
    def test_occurred_on_serializes_as_rfc822_not_bare_iso(self, journal_service):
        journal_service.list_owner_journal.return_value = {
            "items": [
                {
                    "moment_key": MOMENT_KEY_TEXT,
                    "moment_kind": "update",
                    "title": "Date-format contract fixture",
                    "occurred_on": datetime.date(2026, 7, 20),
                    "occurred_precision": "exact",
                    "visibility": "private",
                    "source_type": "text",
                    "lifecycle_state": "active",
                    "version_number": 1,
                }
            ],
            "next_cursor": None,
        }

        response = self.client.get("/api/journal/moments")
        raw_body = response.get_data(as_text=True)
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        occurred_on = payload["items"][0]["occurred_on"]
        # Exactly what journal.js's formatOccurred/formatOccurredIso comment
        # documents: "Mon, 20 Jul 2026 00:00:00 GMT", not "2026-07-20".
        self.assertRegex(
            occurred_on, r"^[A-Za-z]{3}, 20 Jul 2026 \d{2}:\d{2}:\d{2} GMT$"
        )
        self.assertNotEqual(occurred_on, "2026-07-20")
        self.assertNotIn("2026-07-20", raw_body)


class OwnerJournalManageSearchWiringTests(unittest.TestCase):
    """Opus review N5: the Manage search input (B3) wired to the now-merged
    GET /api/journal/moments?q=. Deeper interactive JS behavior (debounce,
    live fetch, honest result states) has no JS test runner available in
    this repository and is disclosed as manual/screenshot evidence in the
    completion report; these tests cover what is mechanically checkable
    here - the server renders the real input, and the shipped JS file
    genuinely references the ?q= parameter it claims to use."""

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
    def test_manage_view_renders_real_search_input(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal?view=archived")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="journal-manage-search"', body)
        self.assertIn('type="search"', body)
        self.assertIn("data-manage-search", body)
        self.assertIn("Manage", body)
        self.assertIn("View and organize all of your Moments.", body)

    @patch("owner_routes.journal_service")
    def test_timeline_view_does_not_render_manage_search(self, journal_service):
        journal_service.list_owner_journal.side_effect = fake_list_owner_journal_factory(
            sample_items()
        )

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertNotIn("data-manage-search", body)

    def test_journal_js_references_the_q_search_parameter(self):
        js_path = Path(__file__).resolve().parent.parent / "static" / "js" / "journal.js"
        js_source = js_path.read_text(encoding="utf-8")

        self.assertIn('url.searchParams.set("q", query)', js_source)
        self.assertIn("data-manage-search", js_source)
        self.assertIn("CONFIG.apiUrl", js_source)


@unittest.skipUnless(os.path.exists(CHROME_EXECUTABLE), "Google Chrome is required for Journal browser coverage")
class JournalBrowserBehaviorTests(unittest.TestCase):
    """Run the shipped Journal JavaScript in Chrome against a local Flask app.

    These checks deliberately intercept only the already-existing Journal API
    boundary. The server-owned evidence fixture renders the page, while the
    intercepts give the UI deterministic read/write outcomes without creating
    a database record. This covers the DOM builders and recovery paths that
    server-render tests cannot execute.
    """

    @classmethod
    def setUpClass(cls):
        cls.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
            "PEERSLATE_JOURNAL_EVIDENCE_FIXTURES": app.config.get("PEERSLATE_JOURNAL_EVIDENCE_FIXTURES"),
            "PEERSLATE_JOURNAL_EVIDENCE_STATE": app.config.get("PEERSLATE_JOURNAL_EVIDENCE_STATE"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_JOURNAL_EVIDENCE_FIXTURES=True,
            PEERSLATE_JOURNAL_EVIDENCE_STATE="timeline",
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
        )
        cls.server = make_server("127.0.0.1", 0, app)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=CHROME_EXECUTABLE,
            headless=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
        app.config.update(cls.original_config)

    def setUp(self):
        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "timeline"

    def _page(self, width=1280, height=900):
        context = self.browser.new_context(viewport={"width": width, "height": height})
        self.addCleanup(context.close)
        return context.new_page()

    @staticmethod
    def _api_payload(item, next_cursor=None):
        return {"success": True, "items": [item], "next_cursor": next_cursor}

    def test_load_more_creates_the_same_timeline_structure_as_server_rows(self):
        page = self._page()

        def api(route):
            if "cursor=" not in route.request.url:
                return route.continue_()
            route.fulfill(
                status=200,
                content_type="application/json",
                json=self._api_payload(
                    {
                        "moment_key": "e8888888-8888-8888-8888-888888888888",
                        "moment_kind": "achievement",
                        "title": "A loaded voice Moment keeps the full Journal card structure.",
                        "occurred_on": "2024-05-12",
                        "display_time": "10:22 AM",
                        "source_type": "voice",
                        "voice_duration_label": "00:19",
                        "thumbnail_kind": "lake",
                        "thumbnail_is_video": False,
                        "lifecycle_state": "active",
                    }
                ),
            )

        page.route("**/api/journal/moments**", api)
        page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")
        page.locator("#journal-load-more").click()
        loaded = page.locator("#journal-moment-e8888888-8888-8888-8888-888888888888")
        loaded.wait_for()
        self.assertEqual(loaded.locator(".ps-journal__date-node").count(), 1)
        self.assertEqual(loaded.locator(".ps-journal__card").count(), 1)
        self.assertIn("10:22 AM", loaded.locator(".ps-journal__meta").inner_text())
        self.assertEqual(loaded.locator(".ps-journal__voice-row").count(), 1)
        self.assertEqual(loaded.locator(".ps-journal__thumb img").count(), 1)

    def test_manage_search_rebuilds_all_six_columns_and_rich_media(self):
        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "manage"
        page = self._page()

        def api(route):
            if "q=workshop" not in route.request.url:
                return route.continue_()
            route.fulfill(
                status=200,
                content_type="application/json",
                json=self._api_payload(
                    {
                        "moment_key": "e9999999-9999-9999-9999-999999999999",
                        "moment_kind": "achievement",
                        "display_kind_label": "Voice",
                        "title": "Workshop recap from the loaded Manage search.",
                        "occurred_on": "2024-05-12",
                        "display_time": "10:22 AM",
                        "source_type": "voice",
                        "voice_duration_label": "00:19",
                        "thumbnail_kind": "stage",
                        "thumbnail_is_video": True,
                        "lifecycle_state": "active",
                    }
                ),
            )

        page.route("**/api/journal/moments**", api)
        page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")
        page.locator("[data-manage-search]").fill("workshop")
        page.wait_for_function("document.querySelectorAll('[data-manage-row]').length === 1")
        self.assertEqual(page.locator(".ps-journal__manage-head > span").count(), 6)
        row = page.locator("[data-manage-row]")
        for selector in (
            ".ps-journal__manage-date-block",
            ".ps-journal__manage-kind svg",
            ".ps-journal__manage-title .ps-journal__thumb img",
            ".ps-journal__manage-duration",
            ".ps-journal__manage-status",
            ".ps-journal__manage-menu",
        ):
            self.assertEqual(row.locator(selector).count(), 1)
        self.assertEqual(row.locator(".ps-journal__manage-duration").inner_text(), "00:19")

    def test_context_rail_has_honest_timeline_manage_empty_and_detail_behavior(self):
        page = self._page()
        page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")
        page.locator("#journal-rail-voice").click()
        self.assertEqual(page.locator("[data-journal-row]:not([hidden])").count(), 2)
        self.assertEqual(page.locator("#journal-rail-voice").get_attribute("aria-current"), "true")
        self.assertEqual(page.locator("[data-rail-mobile] [data-chapter='voice']").get_attribute("aria-current"), "true")

        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "manage"
        manage_page = self._page()
        manage_page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")
        manage_page.locator("#journal-rail-photos").click()
        self.assertEqual(manage_page.locator("[data-manage-row]:not([hidden])").count(), 1)

        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "empty"
        empty_page = self._page()
        empty_page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")
        empty_page.locator("#journal-rail-voice").click()
        self.assertIn("No voice Moments", empty_page.locator("#journal-live-region").inner_text())

        app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = "detail"
        detail_page = self._page()
        detail_page.goto(
            f"{self.base_url}/app/journal/moments/e1111111-1111-1111-1111-111111111111",
            wait_until="networkidle",
        )
        self.assertEqual(detail_page.locator("[data-rail-entry]").count(), 0)
        self.assertEqual(detail_page.locator(".ps-rail__entry--static").count(), 6)
        self.assertEqual(detail_page.locator("[aria-controls^='journal-panel-']").count(), 0)

    def test_desktop_rail_anchors_reflections_and_flourish_to_the_final_rows(self):
        page = self._page(width=1440, height=1040)
        page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")

        def top(selector):
            box = page.locator(selector).bounding_box()
            self.assertIsNotNone(box)
            return box["y"]

        # Binding doc-15 anchors: the final rail chapter starts beside May 19,
        # and the flourish begins beside May 13 after the final hero geometry.
        self.assertLessEqual(abs(top("#journal-rail-reflections") - top("#journal-moment-e2222222-2222-2222-2222-222222222222")), 2)
        self.assertLessEqual(abs(top(".ps-journal__rail-flourish-line") - top("#journal-moment-e4444444-4444-4444-4444-444444444444")), 2)

    def test_mobile_composer_keeps_save_and_voice_failures_visible_and_recoverable(self):
        page = self._page(width=390, height=844)

        def api(route):
            if route.request.method == "POST":
                return route.fulfill(status=200, content_type="application/json", json={"success": True})
            return route.fulfill(status=503, content_type="application/json", json={"success": False})

        page.route("**/api/journal/moments**", api)
        page.goto(f"{self.base_url}/app/journal", wait_until="networkidle")
        trigger = page.locator("#journal-open-composer")
        trigger.click()
        page.locator("[data-composer-save]").click()
        save_status = page.locator("[data-composer-status]")
        self.assertTrue(save_status.is_visible())
        self.assertIn("Add a Moment", save_status.inner_text())

        page.locator("[data-composer-narrative]").fill("A real retry path stays visible on a phone.")
        page.locator("[data-composer-save]").click()
        page.locator("#journal-saved-title").wait_for()
        recovery = page.locator("[data-saved-refresh-status]")
        self.assertTrue(recovery.is_visible())
        self.assertIn("could not refresh", recovery.inner_text())
        box = recovery.bounding_box()
        self.assertIsNotNone(box)
        self.assertLess(box["y"], 844)

        page.locator("[data-composer-back]").click()
        page.wait_for_url("**/app/journal")

        page.locator("#journal-open-composer").click()
        page.locator("[data-composer-tab='speak']").click()
        page.evaluate(
            """() => Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
                configurable: true,
                value: async () => { throw new DOMException('Denied', 'NotAllowedError'); }
            })"""
        )
        voice_start = page.locator("[data-voice-action='start']")
        self.assertFalse(voice_start.is_disabled())
        voice_start.click()
        page.locator("[data-voice-state-title]").wait_for()
        self.assertIn("denied or unavailable", page.locator("[data-voice-state-title]").inner_text())
        self.assertTrue(page.locator("[data-voice-state-help]").is_visible())


if __name__ == "__main__":
    unittest.main()
