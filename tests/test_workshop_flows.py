"""Contract tests for Workshop direct entry — PS-WORKSHOP-001, Slice W1.

Covers Add Information (composer -> review -> save), Edit, Archive, Restore,
and Delete, all mocked at the services/knowledge_service.py boundary so no
real database is required. Every behavioral test uses a generic fixture
member key, never a Pete-specific identifier
(tests/test_site_rules.py's OwnershipGuardrailTests enforces this separately
for reusable service/route code).
"""

import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import app, limiter
from identity import AuthenticationRequired
from services.database_service import DatabaseServiceError
from services.knowledge_service import KnowledgeItemListResult, KnowledgeServiceError


ITEM_KEY = "11111111-1111-1111-1111-111111111111"
VERSION_TOKEN = "0000000000000001"
FRESH_VERSION_TOKEN = "0000000000000002"
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


def member(name, user_key):
    return SimpleNamespace(display_name=name, user_key=user_key)


def service_get_row(**overrides):
    row = {
        "item_key": ITEM_KEY,
        "status": "confirmed",
        "classification": "work",
        "current_version": 1,
        "confirmed_version": 1,
        "confirmed_at": "2026-07-10T00:00:00Z",
        "archived_at": None,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-10T00:00:00Z",
        "version_token": VERSION_TOKEN,
        "version": 1,
        "title": "Systems Engineering Leadership",
        "approved_wording": "You led a system architecture effort end to end.",
        "original_member_wording": "You led a system architecture effort end to end.",
        "body_format": "plain",
        "authored_via": "typed",
        "saved_at": "2026-07-10T00:00:00Z",
        "history": [],
    }
    row.update(overrides)
    return row


def list_result(rows, *, total_count=None):
    """Wraps a plain row list the way the real
    ``list_knowledge_items_for_owner`` now does (BLOCKER 2 correction)."""
    return KnowledgeItemListResult(
        items=rows, total_count=len(rows) if total_count is None else total_count
    )


class WorkshopFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_fixture_flag = app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        self.identity_patch = patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        )
        self.identity_patch.start()
        # These functional tests repeatedly POST to the same rate-limited
        # routes (save/update/archive/restore/delete); the limiter's counter
        # is process-wide and would otherwise accumulate across unrelated
        # tests in this file and spuriously 429 them. Disabled here (mirrors
        # test_interview_studio.py's own pattern) — the dedicated
        # WorkshopRateLimitTests class below re-enables and resets it.
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        self.identity_patch.stop()
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag


class AddInformationComposerTests(WorkshopFlowTestCase):
    def test_get_composer_renders_empty_form_with_a_fresh_idempotency_key(self):
        response = self.client.get("/app/workshop/add")

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Add information", body)
        self.assertIn('name="idempotency_key"', body)
        # No AI concepts anywhere on the composer.
        self.assertNotIn("AI use", body)
        self.assertNotIn("Change permission", body)
        self.assertNotIn("Use as context", body)

    def test_flag_off_hides_the_composer(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        response = self.client.get("/app/workshop/add")
        self.assertEqual(response.status_code, 404)

    def test_signed_out_is_openable_in_preview_mode(self):
        """Owner decision 2026-08-02 (doc 20 section 6d): the composer no
        longer redirects a signed-out visitor to sign-in — it renders,
        openable, with the public preview banner. Supersedes the prior
        ``test_signed_out_is_redirected`` expectation."""
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        ):
            response = self.client.get("/app/workshop/add")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("wk-status-banner--preview", body)
        self.assertIn("Add information", body)

    def test_review_missing_origin_fails_closed(self):
        response = self.client.post(
            "/app/workshop/add/review",
            data={"title": "A title", "wording": "Some wording.", "classification": ""},
        )
        self.assertEqual(response.status_code, 403)

    def test_review_rejects_empty_fields_and_preserves_nothing_to_lose(self):
        response = self.client.post(
            "/app/workshop/add/review",
            data={"title": "", "wording": "", "classification": ""},
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Add information", body)
        self.assertIn("title and wording", body)

    def test_review_preserves_submitted_text_and_shows_source_line(self):
        response = self.client.post(
            "/app/workshop/add/review",
            data={
                "title": "Systems Engineering",
                "wording": "You led a system architecture effort.",
                "classification": "work",
                "idempotency_key": "test-idem-key-1",
            },
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Review what will be saved", body)
        self.assertIn("You led a system architecture effort.", body)
        self.assertIn("Your words, added directly", body)
        self.assertIn("test-idem-key-1", body)
        self.assertNotIn("AI use", body)
        self.assertNotIn("Change permission", body)
        self.assertNotIn("View original", body)

    def test_save_privately_calls_service_with_confirm_true_and_redirects_to_saved(self):
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            return_value={
                "item_key": ITEM_KEY,
                "status": "confirmed",
                "version_token": VERSION_TOKEN,
                "saved": True,
            },
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "Systems Engineering",
                    "wording": "You led a system architecture effort.",
                    "classification": "work",
                    "idempotency_key": "test-idem-key-1",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/app/workshop/items/{ITEM_KEY}/saved", response.headers["Location"])
        save_mock.assert_called_once()
        args, _ = save_mock.call_args
        self.assertEqual(args[0], "member-checkpoint-1")
        self.assertEqual(args[1], "test-idem-key-1")
        self.assertTrue(args[2]["confirm"])
        self.assertEqual(args[2]["authored_via"], "typed")
        self.assertEqual(args[2]["approved_wording"], args[2]["original_wording"])

    def test_save_unfinished_calls_service_with_confirm_false_and_redirects_to_library(self):
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            return_value={
                "item_key": ITEM_KEY,
                "status": "unfinished",
                "version_token": VERSION_TOKEN,
                "saved": True,
            },
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "Systems Engineering",
                    "wording": "You led a system architecture effort.",
                    "classification": "",
                    "idempotency_key": "test-idem-key-2",
                    "save_action": "unfinished",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/workshop", response.headers["Location"])
        self.assertIn("changed=unfinished", response.headers["Location"])
        _, kwargs = save_mock.call_args if save_mock.call_args.kwargs else (save_mock.call_args[0], {})
        args, _ = save_mock.call_args
        self.assertFalse(args[2]["confirm"])
        self.assertEqual(args[2]["classification"], "unclassified")

    def test_idempotency_key_from_composer_survives_keep_working_round_trip(self):
        first = self.client.post(
            "/app/workshop/add/review",
            data={
                "title": "A title",
                "wording": "Some wording.",
                "classification": "",
                "idempotency_key": "stable-key-123",
            },
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertIn("stable-key-123", first.data.decode("utf-8"))

        second = self.client.post(
            "/app/workshop/add",
            data={
                "title": "A title",
                "wording": "Some wording, revised.",
                "classification": "",
                "idempotency_key": "stable-key-123",
            },
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("stable-key-123", second.data.decode("utf-8"))
        self.assertIn("Some wording, revised.", second.data.decode("utf-8"))

    def test_save_missing_origin_fails_closed(self):
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "A title",
                    "wording": "Some wording.",
                    "classification": "",
                    "idempotency_key": "k",
                    "save_action": "confirm",
                },
            )
        self.assertEqual(response.status_code, 403)
        save_mock.assert_not_called()

    def test_save_service_unavailable_preserves_member_text_instead_of_the_bare_recovery_page(
        self,
    ):
        """Test gap 6 correction (code change): a database failure during
        Save must never lose the member's typed text — the review form
        re-renders with the submission intact and an unavailable message,
        not the bare payload-free unavailable page."""
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            side_effect=DatabaseServiceError("db down"),
        ):
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "My real title that must not be lost",
                    "wording": "My real wording that must not be lost either.",
                    "classification": "",
                    "idempotency_key": "k",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("My real title that must not be lost", body)
        self.assertIn("My real wording that must not be lost either.", body)
        self.assertIn("couldn&#39;t save this right now", body)
        self.assertNotIn("temporarily unavailable", body)


class MinorCorrectionsTests(WorkshopFlowTestCase):
    """MINORS 6-7: the "Work on Something" tab is an inert span (not a
    still-a-link <a>), and classification has an explicit fourth
    "Unclassified"/"Not set" option instead of an implicit all-unchecked
    state."""

    def test_work_on_something_is_an_inert_span_not_a_link(self):
        response = self.client.get("/app/workshop/add")
        body = response.data.decode("utf-8")

        self.assertIn("<span>Work on Something</span>", body)
        self.assertIn('<span class="wk-pill wk-pill--coming-later">Coming later</span>', body)
        # No <a href="#" ...>Work on Something</a> anywhere — it must not
        # be announced as a link at all, inert or otherwise.
        self.assertNotIn('role="link">Work on Something', body)
        self.assertNotIn('href="#" aria-disabled="true" role="link">Work on Something', body)

    def test_composer_offers_an_explicit_unclassified_radio(self):
        response = self.client.get("/app/workshop/add")
        body = response.data.decode("utf-8")

        self.assertIn('value="unclassified"', body)
        self.assertIn("Not set", body)

    def test_edit_prefills_the_explicit_unclassified_radio_as_checked(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(classification="unclassified"),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/edit")

        body = response.data.decode("utf-8")
        unclassified_index = body.index('value="unclassified"')
        tag_end = body.index(">", unclassified_index)
        following = body[unclassified_index:tag_end]
        self.assertIn("checked", following)


class EditInformationTests(WorkshopFlowTestCase):
    def test_get_edit_prefills_from_the_real_item(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ) as get_mock:
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/edit")

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Systems Engineering Leadership", body)
        self.assertIn(VERSION_TOKEN, body)
        get_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)

    def test_unknown_item_key_redirects_neutrally_to_the_library(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            side_effect=KnowledgeServiceError("not found", code="not_found"),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/edit")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/workshop")

    def test_update_confirm_redirects_to_saved(self):
        with patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
            return_value={"version": 2, "version_token": FRESH_VERSION_TOKEN, "updated": True},
        ) as update_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}",
                data={
                    "title": "Systems Engineering Leadership",
                    "wording": "Updated wording.",
                    "classification": "work",
                    "expected_row_version": VERSION_TOKEN,
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/app/workshop/items/{ITEM_KEY}/saved", response.headers["Location"])
        args, _ = update_mock.call_args
        self.assertEqual(args[0], "member-checkpoint-1")
        self.assertEqual(args[1], ITEM_KEY)
        self.assertEqual(args[2], VERSION_TOKEN)
        self.assertTrue(args[3]["confirm"])

    def test_stale_version_token_renders_conflict_message_with_text_preserved(self):
        with patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
            side_effect=KnowledgeServiceError("changed", code="changed"),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(version_token=FRESH_VERSION_TOKEN),
        ):
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}",
                data={
                    "title": "My edited title",
                    "wording": "My edited wording that must not be lost.",
                    "classification": "personal",
                    "expected_row_version": VERSION_TOKEN,
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("changed elsewhere", body)
        self.assertIn("My edited title", body)
        self.assertIn("My edited wording that must not be lost.", body)
        # A fresh token is threaded through so a retry can succeed.
        self.assertIn(FRESH_VERSION_TOKEN, body)

    def test_stale_version_token_when_refetch_also_fails_still_preserves_text(self):
        with patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
            side_effect=KnowledgeServiceError("changed", code="changed"),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            side_effect=DatabaseServiceError("down"),
        ):
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}",
                data={
                    "title": "My edited title",
                    "wording": "My edited wording that must not be lost.",
                    "classification": "",
                    "expected_row_version": VERSION_TOKEN,
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("My edited wording that must not be lost.", response.data.decode("utf-8"))

    def test_update_service_unavailable_preserves_member_text_instead_of_the_bare_recovery_page(
        self,
    ):
        """Test gap 6 correction (code change): same principle as Save's
        DatabaseServiceError path — the review form re-renders with the
        submission intact rather than the bare payload-free unavailable
        page."""
        with patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
            side_effect=DatabaseServiceError("db down"),
        ):
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}",
                data={
                    "title": "My edited title that must not be lost",
                    "wording": "My edited wording that must not be lost either.",
                    "classification": "",
                    "expected_row_version": VERSION_TOKEN,
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("My edited title that must not be lost", body)
        self.assertIn("My edited wording that must not be lost either.", body)
        self.assertIn("couldn&#39;t save this right now", body)
        self.assertNotIn("temporarily unavailable", body)


class ValidationErrorTextPreservationTests(WorkshopFlowTestCase):
    """Test gap 5: member prose survives a validation-error re-render at
    all four _rerender sites (review_add, save_item, review_edit,
    update_item), not just the "everything empty" case already covered by
    test_review_rejects_empty_fields_and_preserves_nothing_to_lose. Each
    test submits real, non-empty text plus one genuinely invalid field
    (a classification value outside the allowed set) and asserts the real
    text is still present in the re-rendered form."""

    REAL_TITLE = "A real title that must not be lost"
    REAL_WORDING = "Real wording text that must not be lost either."
    INVALID_CLASSIFICATION = "not-a-real-choice"

    def test_review_add_preserves_text_on_invalid_classification(self):
        response = self.client.post(
            "/app/workshop/add/review",
            data={
                "title": self.REAL_TITLE,
                "wording": self.REAL_WORDING,
                "classification": self.INVALID_CLASSIFICATION,
            },
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn(self.REAL_TITLE, body)
        self.assertIn(self.REAL_WORDING, body)
        self.assertIn("Choose Work, Personal, or Both", body)

    def test_save_item_rerender_preserves_text_on_invalid_classification(self):
        response = self.client.post(
            "/app/workshop/items",
            data={
                "title": self.REAL_TITLE,
                "wording": self.REAL_WORDING,
                "classification": self.INVALID_CLASSIFICATION,
                "idempotency_key": "k",
                "save_action": "confirm",
            },
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn(self.REAL_TITLE, body)
        self.assertIn(self.REAL_WORDING, body)
        self.assertIn("Choose Work, Personal, or Both", body)

    def test_review_edit_preserves_text_on_invalid_classification(self):
        response = self.client.post(
            f"/app/workshop/items/{ITEM_KEY}/edit/review",
            data={
                "title": self.REAL_TITLE,
                "wording": self.REAL_WORDING,
                "classification": self.INVALID_CLASSIFICATION,
                "expected_row_version": VERSION_TOKEN,
            },
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn(self.REAL_TITLE, body)
        self.assertIn(self.REAL_WORDING, body)
        self.assertIn("Choose Work, Personal, or Both", body)

    def test_update_item_rerender_preserves_text_on_invalid_classification(self):
        response = self.client.post(
            f"/app/workshop/items/{ITEM_KEY}",
            data={
                "title": self.REAL_TITLE,
                "wording": self.REAL_WORDING,
                "classification": self.INVALID_CLASSIFICATION,
                "expected_row_version": VERSION_TOKEN,
                "save_action": "confirm",
            },
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn(self.REAL_TITLE, body)
        self.assertIn(self.REAL_WORDING, body)
        self.assertIn("Choose Work, Personal, or Both", body)


class RouteLevelIdempotencyReplayTests(WorkshopFlowTestCase):
    """Test gap 9: posting the same idempotency_key twice at the route
    produces one consistent outcome (the same item, the same redirect) —
    not a duplicate. The route itself has no replay memory (the service's
    idempotency ledger is what actually dedupes, proven separately in
    test_knowledge_service.py); this proves the route threads the exact
    same key through both times and treats the identical outcome
    consistently."""

    def test_replaying_the_same_idempotency_key_produces_one_consistent_outcome(self):
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            return_value={
                "item_key": ITEM_KEY,
                "status": "confirmed",
                "version_token": VERSION_TOKEN,
                "saved": True,
            },
        ) as save_mock:
            payload = {
                "title": "Systems Engineering",
                "wording": "You led a system architecture effort.",
                "classification": "work",
                "idempotency_key": "replay-key-1",
                "save_action": "confirm",
            }
            first = self.client.post(
                "/app/workshop/items", data=payload, headers=SAME_ORIGIN_HEADERS
            )
            second = self.client.post(
                "/app/workshop/items", data=payload, headers=SAME_ORIGIN_HEADERS
            )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(first.headers["Location"], second.headers["Location"])
        self.assertIn(f"/app/workshop/items/{ITEM_KEY}/saved", first.headers["Location"])
        self.assertEqual(save_mock.call_count, 2)
        first_key = save_mock.call_args_list[0].args[1]
        second_key = save_mock.call_args_list[1].args[1]
        self.assertEqual(first_key, second_key)
        self.assertEqual(first_key, "replay-key-1")


class SavedConfirmationTests(WorkshopFlowTestCase):
    def test_confirmed_item_renders_saved_confirmation(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(status="confirmed"),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/saved")

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Saved privately", body)
        self.assertIn("Use this elsewhere", body)
        self.assertIn("Coming later", body)
        self.assertIn("View in My Information", body)
        self.assertIn("Add something else", body)
        self.assertIn("Close for now", body)
        self.assertNotIn("AI use", body)
        self.assertNotIn("Change permission", body)

    def test_non_confirmed_item_never_shows_saved_privately(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(status="unfinished"),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/saved")

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"item={ITEM_KEY}", response.headers["Location"])


class ArchiveRestoreDeleteTests(WorkshopFlowTestCase):
    def test_archive_missing_origin_fails_closed(self):
        with patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner"
        ) as archive_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/archive",
                data={"expected_row_version": VERSION_TOKEN},
            )
        self.assertEqual(response.status_code, 403)
        archive_mock.assert_not_called()

    def test_archive_success_redirects_with_status(self):
        with patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner",
            return_value={"version_token": FRESH_VERSION_TOKEN, "archived": True},
        ):
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/archive",
                data={"expected_row_version": VERSION_TOKEN},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("changed=archived", response.headers["Location"])

    def test_archive_changed_redirects_with_error(self):
        with patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner",
            side_effect=KnowledgeServiceError("changed", code="changed"),
        ):
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/archive",
                data={"expected_row_version": VERSION_TOKEN},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=changed", response.headers["Location"])

    def test_restore_success_redirects_with_status(self):
        with patch(
            "workshop_routes.knowledge_service.restore_knowledge_item_for_owner",
            return_value={"version_token": FRESH_VERSION_TOKEN, "restored": True},
        ):
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/restore",
                data={"expected_row_version": VERSION_TOKEN},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("changed=restored", response.headers["Location"])

    def test_delete_confirm_page_requires_no_write(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/delete")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("permanently deletes", body)
        self.assertIn(VERSION_TOKEN, body)

    def test_delete_without_confirmation_field_is_rejected(self):
        with patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner"
        ) as delete_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/delete",
                data={"expected_row_version": VERSION_TOKEN},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=confirm-delete", response.headers["Location"])
        delete_mock.assert_not_called()

    def test_delete_with_a_truthy_but_wrong_confirmation_value_is_rejected(self):
        """Test gap 15: confirm_delete must equal the exact string
        "delete" — any other truthy-looking value ("true", "yes", "on",
        "1") is refused exactly like a missing field, never accepted."""
        with patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner"
        ) as delete_mock:
            for wrong_value in ("true", "yes", "on", "1", "Delete", "DELETE"):
                with self.subTest(confirm_delete=wrong_value):
                    response = self.client.post(
                        f"/app/workshop/items/{ITEM_KEY}/delete",
                        data={
                            "expected_row_version": VERSION_TOKEN,
                            "confirm_delete": wrong_value,
                        },
                        headers=SAME_ORIGIN_HEADERS,
                    )
                    self.assertEqual(response.status_code, 302)
                    self.assertIn("error=confirm-delete", response.headers["Location"])
        delete_mock.assert_not_called()

    def test_delete_with_confirmation_succeeds(self):
        with patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner",
            return_value={"deleted_version_count": 1, "deleted": True},
        ) as delete_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/delete",
                data={"expected_row_version": VERSION_TOKEN, "confirm_delete": "delete"},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("changed=deleted", response.headers["Location"])
        delete_mock.assert_called_once_with(
            "member-checkpoint-1", ITEM_KEY, VERSION_TOKEN
        )

    def test_delete_missing_origin_fails_closed(self):
        with patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner"
        ) as delete_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/delete",
                data={"expected_row_version": VERSION_TOKEN, "confirm_delete": "delete"},
            )
        self.assertEqual(response.status_code, 403)
        delete_mock.assert_not_called()


class SaveItemDevFixtureGuardTests(WorkshopFlowTestCase):
    """MAJOR 3 correction: the fixture save-preview seam requires BOTH
    PEERSLATE_WORKSHOP_DEV_FIXTURE and the pre-existing local-preview-only
    PEERSLATE_ALLOW_DEV_IDENTITY flag. Either one absent means the
    production path — the real save_knowledge_item_for_owner call — runs."""

    def setUp(self):
        super().setUp()
        self.original_allow_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")

    def tearDown(self):
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = self.original_allow_dev_identity
        super().tearDown()

    def _save_payload(self):
        return {
            "title": "Systems Engineering",
            "wording": "You led a system architecture effort.",
            "classification": "work",
            "idempotency_key": "test-idem-key-guard",
            "save_action": "confirm",
        }

    def test_dev_fixture_flag_alone_still_calls_the_real_save(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            return_value={
                "item_key": ITEM_KEY,
                "status": "confirmed",
                "version_token": VERSION_TOKEN,
                "saved": True,
            },
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items", data=self._save_payload(), headers=SAME_ORIGIN_HEADERS
            )

        save_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/app/workshop/items/{ITEM_KEY}/saved", response.headers["Location"])

    def test_dev_identity_flag_alone_still_calls_the_real_save(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            return_value={
                "item_key": ITEM_KEY,
                "status": "confirmed",
                "version_token": VERSION_TOKEN,
                "saved": True,
            },
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items", data=self._save_payload(), headers=SAME_ORIGIN_HEADERS
            )

        save_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)

    def test_both_flags_together_take_the_fixture_branch_and_skip_the_real_save(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items", data=self._save_payload(), headers=SAME_ORIGIN_HEADERS
            )

        save_mock.assert_not_called()
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Dev preview", body)
        self.assertIn("nothing was stored", body)


# MAJOR 4 correction (independent review): the complete same-origin test
# matrix over all nine Workshop POST routes. Each entry is
# (path, form data, optional service method name to assert uncalled).
POST_ROUTES = (
    ("/app/workshop/add", {}, None),
    (
        "/app/workshop/add/review",
        {"title": "A title", "wording": "Some wording.", "classification": ""},
        None,
    ),
    (
        "/app/workshop/items",
        {
            "title": "A title",
            "wording": "Some wording.",
            "classification": "",
            "idempotency_key": "k",
            "save_action": "confirm",
        },
        "save_knowledge_item_for_owner",
    ),
    (f"/app/workshop/items/{ITEM_KEY}/edit", {}, None),
    (
        f"/app/workshop/items/{ITEM_KEY}/edit/review",
        {
            "title": "A title",
            "wording": "Some wording.",
            "classification": "",
            "expected_row_version": VERSION_TOKEN,
        },
        None,
    ),
    (
        f"/app/workshop/items/{ITEM_KEY}",
        {
            "title": "A title",
            "wording": "Some wording.",
            "classification": "",
            "expected_row_version": VERSION_TOKEN,
            "save_action": "confirm",
        },
        "update_knowledge_item_for_owner",
    ),
    (
        f"/app/workshop/items/{ITEM_KEY}/archive",
        {"expected_row_version": VERSION_TOKEN},
        "archive_knowledge_item_for_owner",
    ),
    (
        f"/app/workshop/items/{ITEM_KEY}/restore",
        {"expected_row_version": VERSION_TOKEN},
        "restore_knowledge_item_for_owner",
    ),
    (
        f"/app/workshop/items/{ITEM_KEY}/delete",
        {"expected_row_version": VERSION_TOKEN, "confirm_delete": "delete"},
        "delete_knowledge_item_for_owner",
    ),
)

CROSS_SITE_SCENARIOS = (
    ("no_signals", {}),
    ("cross_site_origin", {"Origin": "http://evil.example"}),
    ("cross_site_fetch_site", {"Sec-Fetch-Site": "cross-site"}),
)

ACCEPTED_SOLO_SIGNAL_SCENARIOS = (
    ("origin_alone", {"Origin": "http://localhost"}),
    ("fetch_site_alone", {"Sec-Fetch-Site": "same-origin"}),
)


class WorkshopSameOriginMatrixTests(WorkshopFlowTestCase):
    """MAJOR 4 correction: the complete same-origin test matrix over all
    nine state-changing Workshop POST routes, not just a sample."""

    def test_every_route_rejects_every_cross_site_scenario(self):
        for path, data, service_attr in POST_ROUTES:
            for scenario_name, headers in CROSS_SITE_SCENARIOS:
                with self.subTest(path=path, scenario=scenario_name):
                    with contextlib.ExitStack() as stack:
                        identity_mock = stack.enter_context(
                            patch("workshop_routes.get_current_identity")
                        )
                        service_mock = (
                            stack.enter_context(
                                patch(f"workshop_routes.knowledge_service.{service_attr}")
                            )
                            if service_attr
                            else None
                        )
                        response = self.client.post(path, data=data, headers=headers)

                    self.assertEqual(response.status_code, 403)
                    identity_mock.assert_not_called()
                    if service_mock is not None:
                        service_mock.assert_not_called()

    def test_every_route_accepts_either_signal_alone(self):
        """The no-JS path: a real form post carries only Origin OR only
        Sec-Fetch-Site (never neither, per browser behavior), and either
        one alone must be enough to pass the same-origin check."""
        for path, data, service_attr in POST_ROUTES:
            for scenario_name, headers in ACCEPTED_SOLO_SIGNAL_SCENARIOS:
                with self.subTest(path=path, scenario=scenario_name):
                    with patch(
                        "workshop_routes.get_current_identity",
                        return_value=member("Checkpoint Member", "member-checkpoint-1"),
                    ), patch(
                        "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
                        return_value=service_get_row(),
                    ), patch(
                        "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
                        return_value={
                            "item_key": ITEM_KEY,
                            "status": "confirmed",
                            "version_token": VERSION_TOKEN,
                            "saved": True,
                        },
                    ), patch(
                        "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
                        return_value={
                            "version": 2,
                            "version_token": FRESH_VERSION_TOKEN,
                            "updated": True,
                        },
                    ), patch(
                        "workshop_routes.knowledge_service.archive_knowledge_item_for_owner",
                        return_value={"version_token": FRESH_VERSION_TOKEN, "archived": True},
                    ), patch(
                        "workshop_routes.knowledge_service.restore_knowledge_item_for_owner",
                        return_value={"version_token": FRESH_VERSION_TOKEN, "restored": True},
                    ), patch(
                        "workshop_routes.knowledge_service.delete_knowledge_item_for_owner",
                        return_value={"deleted_version_count": 1, "deleted": True},
                    ):
                        response = self.client.post(path, data=data, headers=headers)

                    self.assertNotEqual(response.status_code, 403)


class CacheControlHeaderMatrixTests(WorkshopFlowTestCase):
    """Test gap 10: every Workshop route response carries
    Cache-Control: private, no-store, not only the main library route —
    this is a signed-in member's own private library on every one of
    these routes and must never be stored by a shared cache or replayed
    from the back/forward cache after sign-out."""

    def test_every_route_response_is_private_no_store(self):
        get_routes = (
            "/app/workshop",
            "/app/workshop/add",
            f"/app/workshop/items/{ITEM_KEY}/edit",
            f"/app/workshop/items/{ITEM_KEY}/saved",
            f"/app/workshop/items/{ITEM_KEY}/delete",
        )
        with patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(status="confirmed"),
        ), patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner",
            return_value={
                "item_key": ITEM_KEY,
                "status": "confirmed",
                "version_token": VERSION_TOKEN,
                "saved": True,
            },
        ), patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
            return_value={
                "version": 2,
                "version_token": FRESH_VERSION_TOKEN,
                "updated": True,
            },
        ), patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner",
            return_value={"version_token": FRESH_VERSION_TOKEN, "archived": True},
        ), patch(
            "workshop_routes.knowledge_service.restore_knowledge_item_for_owner",
            return_value={"version_token": FRESH_VERSION_TOKEN, "restored": True},
        ), patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner",
            return_value={"deleted_version_count": 1, "deleted": True},
        ):
            for path in get_routes:
                with self.subTest(method="get", path=path):
                    response = self.client.get(path)
                    self.assertEqual(
                        response.headers.get("Cache-Control"), "private, no-store"
                    )

            for path, data, _service_attr in POST_ROUTES:
                with self.subTest(method="post", path=path):
                    response = self.client.post(
                        path, data=data, headers=SAME_ORIGIN_HEADERS
                    )
                    self.assertEqual(
                        response.headers.get("Cache-Control"), "private, no-store"
                    )


class ExistenceOracleNeutralityTests(WorkshopFlowTestCase):
    """Test gap 11: a not_found item key on GET saved/delete-confirm must
    never confirm or deny whether that key belongs to someone else — the
    redirect carries no item reference back to the caller, matching
    edit_information's existing neutral-redirect behavior for the same
    not_found case."""

    def test_saved_not_found_redirects_neutrally(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            side_effect=KnowledgeServiceError("not found", code="not_found"),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/saved")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/workshop")
        self.assertNotIn(ITEM_KEY.encode(), response.data)

    def test_delete_confirm_not_found_redirects_neutrally(self):
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            side_effect=KnowledgeServiceError("not found", code="not_found"),
        ):
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/delete")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app/workshop")
        self.assertNotIn(ITEM_KEY.encode(), response.data)


class WorkshopRateLimitTests(unittest.TestCase):
    """MAJOR 5 correction: the five state-changing Workshop routes are rate
    limited the same way the app's other state-changing/AI-cost routes are.
    Uses one representative route (archive) rather than re-proving the
    limiter mechanism itself for all five."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        self.identity_patch = patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        )
        self.identity_patch.start()
        self._limiter_enabled = limiter.enabled
        limiter.enabled = True
        limiter.reset()

    def tearDown(self):
        limiter.reset()
        limiter.enabled = self._limiter_enabled
        self.identity_patch.stop()
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag

    def test_archive_returns_429_after_the_per_minute_limit_is_exceeded(self):
        with patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner",
            return_value={"version_token": VERSION_TOKEN, "archived": True},
        ):
            statuses = [
                self.client.post(
                    f"/app/workshop/items/{ITEM_KEY}/archive",
                    data={"expected_row_version": VERSION_TOKEN},
                    headers=SAME_ORIGIN_HEADERS,
                ).status_code
                for _ in range(9)
            ]

        self.assertIn(429, statuses)
        self.assertEqual(statuses[-1], 429)


if __name__ == "__main__":
    unittest.main()
