"""Contract tests for the default-off Workshop / My Information page.

PS-WORKSHOP-001, Slice W1: the owner checkpoint gate passed (doc 20 section
6b) and implementation continued through real data wiring. These tests
follow the conventions in tests/test_owner_studio_slice1.py. Every
behavioral test uses a generic fixture member key, never a Pete-specific
identifier (tests/test_site_rules.py's OwnershipGuardrailTests enforces this
separately for reusable service/route code).
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import app, limiter
from identity import AuthenticationRequired
from services import workshop_demo_library
from services.database_service import DatabaseServiceError
from services.knowledge_service import KnowledgeItemListResult, KnowledgeServiceError


ROUTE = "/app/workshop"
ITEM_KEY = "11111111-1111-1111-1111-111111111111"
OTHER_ITEM_KEY = "22222222-2222-2222-2222-222222222222"
FOREIGN_ITEM_KEY = "99999999-9999-9999-9999-999999999999"
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


def member(name, user_key):
    return SimpleNamespace(display_name=name, user_key=user_key)


def service_list_row(**overrides):
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
        "version_token": "0000000000000001",
        "title": "Systems Engineering Leadership",
        "body_format": "plain",
        "authored_via": "typed",
    }
    row.update(overrides)
    return row


def list_result(rows, *, total_count=None):
    """Wraps a plain row list the way the real
    ``list_knowledge_items_for_owner`` now does (BLOCKER 2 correction:
    KnowledgeItemListResult carries the owner's true total_count alongside
    the bounded item list)."""
    return KnowledgeItemListResult(
        items=rows, total_count=len(rows) if total_count is None else total_count
    )


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
        "version_token": "0000000000000001",
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


def _demo_item_key(title):
    """The stable, deterministic item_key for one Jordan Ellis demo-library
    base item, looked up by its exact title (owner instruction 2026-08-02,
    doc 20 section 6e)."""
    return next(
        item["item_key"]
        for item in workshop_demo_library.BASE_ITEMS
        if item["title"] == title
    )


def _library_item_title_count(body):
    """How many library rows a My Information render actually shows —
    counts the per-row title span, not workshop.total_item_count (which
    intentionally stays the unfiltered owner total; see _library.html)."""
    return body.count('class="wk-list__item-title"')


class WorkshopCheckpointRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_fixture_flag = app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag

    def test_flag_off_is_neutral_and_resolves_no_identity_or_asset(self):
        with patch("workshop_routes.get_current_identity") as identity:
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"workshop.css", response.data)
        self.assertNotIn(b"Workshop", response.data)
        identity.assert_not_called()

    def test_signed_out_visitor_gets_the_public_preview_not_a_redirect(self):
        """Owner decision 2026-08-02 (doc 20 section 6d): Workshop must not
        be behind a login wall right now. A signed-out visitor gets the
        real page rendered over honestly-labeled sample content instead of
        the sign-in redirect this route used to return — supersedes the
        prior ``test_signed_out_member_is_redirected_with_the_exact_return_
        path`` expectation."""
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        body = response.data.decode("utf-8")
        self.assertIn("wk-status-banner--preview", body)
        self.assertIn("example information", body)

    def test_identity_failure_returns_a_payload_free_recovery_state(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=DatabaseServiceError("identity storage unavailable"),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertIn(b"temporarily unavailable", response.data)

    def test_library_read_failure_returns_a_payload_free_recovery_state(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            side_effect=DatabaseServiceError("db unavailable"),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"Systems Engineering", response.data)

    def test_signed_in_member_gets_the_real_populated_library(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ) as list_mock, patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ) as get_mock:
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        body = response.data.decode("utf-8")
        self.assertIn("<h1", body)
        self.assertEqual(body.count("<h1"), 1)
        self.assertIn(">Workshop<", body)
        self.assertIn("Systems Engineering Leadership", body)

        list_mock.assert_called_once_with("member-checkpoint-1", include_archived=True)
        get_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)

        # Doc 20 section 6a (owner decision, 2026-08-01): AI use of confirmed
        # information is always on with no member-facing permission control
        # anywhere on the page.
        self.assertNotIn("AI use", body)
        self.assertNotIn("Change permission", body)
        self.assertNotIn("Use as context", body)
        self.assertNotIn("ai_use", body.lower().replace(" ", ""))

    def test_first_run_empty_state_is_honest_and_has_no_suggestion_card(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("New Member", "member-new-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([]),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Nothing saved here yet", body)
        self.assertIn("Add information", body)
        # No suggestion mechanism exists yet in W1 (Spark is slice W3) — a
        # real member never sees a fabricated suggestion, empty or not.
        self.assertNotIn("Suggested by PeerSlate", body)
        # No dead search/filter controls on an empty library.
        self.assertNotIn("wk-search", body)
        self.assertNotIn("wk-filters", body)

    def test_foreign_or_unknown_item_key_renders_the_list_with_no_detail(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner"
        ) as get_mock:
            response = self.client.get(ROUTE + f"?item={FOREIGN_ITEM_KEY}")

        self.assertEqual(response.status_code, 200)
        # Never confirms or denies whether that key belongs to someone else:
        # no detail is fetched or rendered, and no error is shown.
        get_mock.assert_not_called()
        self.assertNotIn(FOREIGN_ITEM_KEY.encode(), response.data)
        self.assertNotIn(b'wk-detail"', response.data)

    def test_malformed_item_key_falls_back_neutrally_to_the_first_item(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ) as get_mock:
            response = self.client.get(ROUTE + "?item=not-a-uuid")

        self.assertEqual(response.status_code, 200)
        get_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)

    def test_user_key_query_parameter_is_ignored(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ) as identity, patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ) as list_mock, patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(ROUTE + "?user_key=someone-else")

        self.assertEqual(response.status_code, 200)
        # The service is called with the server-resolved identity object only
        # — never anything derived from the query string.
        identity.assert_called_once_with()
        list_mock.assert_called_once_with("member-checkpoint-1", include_archived=True)
        self.assertNotIn(b"someone-else", response.data)

    def test_two_owners_never_share_library_bytes(self):
        """Two different signed-in members never see each other's items."""
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Avery Member", "member-avery"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row(title="Avery's item")]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(title="Avery's item"),
        ):
            avery = self.client.get(ROUTE)
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Morgan Member", "member-morgan"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row(title="Morgan's item")]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(title="Morgan's item"),
        ):
            morgan = self.client.get(ROUTE)

        self.assertEqual(avery.status_code, 200)
        self.assertEqual(morgan.status_code, 200)
        self.assertNotIn(b"member-avery", avery.data)
        self.assertNotIn(b"member-morgan", morgan.data)
        self.assertIn(b"Avery&#39;s item", avery.data)
        self.assertNotIn(b"Morgan&#39;s item", avery.data)
        self.assertIn(b"Morgan&#39;s item", morgan.data)
        self.assertNotIn(b"Avery&#39;s item", morgan.data)

    def test_route_is_read_only(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        rule = next(r for r in app.url_map.iter_rules() if r.rule == ROUTE)
        self.assertEqual(rule.methods - {"HEAD", "OPTIONS"}, {"GET"})


class WorkshopBacklogConfirmationWiringTests(unittest.TestCase):
    """Leg 9 (PS-WORKSHOP-002): the standing-rule backlog confirmation runs
    once per real (non-fixture) library read for a signed-in member, and a
    failure there degrades to skip-not-fail rather than denying the member
    their page — the same discipline the Opportunity Slate room applies to
    its own opportunistic working-data purge."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_fixture_flag = app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag

    def test_a_signed_in_real_library_read_triggers_the_backlog_confirmation_once(self):
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.confirm_authored_knowledge_backlog_for_owner",
            return_value={"confirmed_count": 0, "remaining_count": 0},
        ) as confirm_mock, patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([]),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        confirm_mock.assert_called_once_with("member-checkpoint-1")

    def test_a_backlog_confirmation_database_failure_never_denies_the_page(self):
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.confirm_authored_knowledge_backlog_for_owner",
            side_effect=DatabaseServiceError("procedure not applied yet"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Systems Engineering Leadership", body)

    def test_a_backlog_confirmation_knowledge_service_failure_never_denies_the_page(self):
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.confirm_authored_knowledge_backlog_for_owner",
            side_effect=KnowledgeServiceError("no identity", code="no_identity"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([]),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)

    def test_the_backlog_confirmation_never_runs_for_a_signed_out_visitor(self):
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("anonymous"),
        ), patch(
            "workshop_routes.knowledge_service.confirm_authored_knowledge_backlog_for_owner"
        ) as confirm_mock:
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        confirm_mock.assert_not_called()

    def test_the_backlog_confirmation_never_runs_in_dev_fixture_preview(self):
        original_allow_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        try:
            with patch(
                "workshop_routes.get_current_identity",
                return_value=member("Checkpoint Member", "member-checkpoint-1"),
            ), patch(
                "workshop_routes.knowledge_service.confirm_authored_knowledge_backlog_for_owner"
            ) as confirm_mock:
                # get_my_information_checkpoint runs for real here (a pure
                # fixture builder, no database call), exercising the genuine
                # dev-preview branch; only the backlog-confirmation call is
                # asserted.
                response = self.client.get(ROUTE)
        finally:
            app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = original_allow_dev_identity

        self.assertEqual(response.status_code, 200)
        confirm_mock.assert_not_called()


class WorkshopEnabledConfigDefaultTests(unittest.TestCase):
    """Test gap 12: PEERSLATE_WORKSHOP_ENABLED is off by default — no
    setUp/tearDown override here, so this reads the app's actual startup
    configuration rather than a test-injected value."""

    def test_workshop_enabled_is_off_by_default(self):
        self.assertIsNot(app.config.get("PEERSLATE_WORKSHOP_ENABLED"), True)


class WorkshopDevFixtureSeamTests(unittest.TestCase):
    """PEERSLATE_WORKSHOP_DEV_FIXTURE: local-preview-only, off by default.

    MAJOR 3 correction (independent review): the fixture seam is gated on
    TWO independent flags — PEERSLATE_WORKSHOP_DEV_FIXTURE AND the
    pre-existing PEERSLATE_ALLOW_DEV_IDENTITY (identity.py's own
    local-preview-only dev-identity flag; production never sets it). Either
    one alone must leave the seam unreachable.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_fixture_flag = app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE")
        self.original_allow_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = self.original_allow_dev_identity

    def test_dev_fixture_is_off_by_default(self):
        self.assertIsNot(app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE"), True)

    def test_dev_fixture_off_never_consults_the_checkpoint_fixture(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.get_my_information_checkpoint"
        ) as checkpoint_mock, patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([]),
        ):
            self.client.get(ROUTE)

        checkpoint_mock.assert_not_called()

    def test_dev_fixture_flag_alone_is_unreachable_without_dev_identity(self):
        """PEERSLATE_WORKSHOP_DEV_FIXTURE=True by itself (the pre-correction
        guard) must not be enough — the real, populated store still renders."""
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.get_my_information_checkpoint"
        ) as checkpoint_mock, patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(ROUTE)

        checkpoint_mock.assert_not_called()
        self.assertIn("Systems Engineering Leadership", response.data.decode("utf-8"))
        self.assertNotIn("Dev preview", response.data.decode("utf-8"))

    def test_dev_identity_flag_alone_is_unreachable_without_dev_fixture(self):
        """PEERSLATE_ALLOW_DEV_IDENTITY=True by itself must not enable the
        fixture seam either — both flags are independently required."""
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.get_my_information_checkpoint"
        ) as checkpoint_mock, patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(ROUTE)

        checkpoint_mock.assert_not_called()
        self.assertIn("Systems Engineering Leadership", response.data.decode("utf-8"))
        self.assertNotIn("Dev preview", response.data.decode("utf-8"))

    def test_dev_fixture_on_renders_the_populated_preview(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner"
        ) as list_mock:
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Systems Engineering", body)
        # The dev-fixture path never touches the real store.
        list_mock.assert_not_called()
        # Both flags together produce an unmistakable dev-preview banner.
        self.assertIn("Dev preview", body)
        self.assertIn("nothing was stored", body)
        # The fabricated suggestion card is tagged so it can't be mistaken
        # for a live W3 capability.
        self.assertIn("Preview example", body)

    def test_dev_fixture_empty_state_seam_is_gated_on_the_flag(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            # _dev_state is ignored entirely when the fixture flag is off —
            # the real (populated) store still renders.
            response = self.client.get(ROUTE + "?_dev_state=empty")

        self.assertIn("Systems Engineering Leadership", response.data.decode("utf-8"))

    def test_dev_fixture_empty_state_renders_the_honest_empty_page(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            response = self.client.get(ROUTE + "?_dev_state=empty")

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Nothing saved here yet", body)
        self.assertNotIn("Systems Engineering", body)
        self.assertIn("Dev preview", body)

    def test_real_path_never_shows_the_dev_preview_banner(self):
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(ROUTE)

        self.assertNotIn("Dev preview", response.data.decode("utf-8"))


class WorkshopChromeScopeTests(unittest.TestCase):
    """The approved mockups (06/09) draw no profile-tabs sub-strip and no
    floating Ask AI button on /app/workshop. base.html's shared
    is_owner_app_path chrome is excluded for the workshop blueprint
    specifically (is_workshop_path), so this is confirmed both ways: absent
    on Workshop, still present on a sibling /app-family page whose approved
    authority does draw it.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag

    def test_workshop_excludes_profile_tabs_and_floating_ask_ai(self):
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([]),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertNotIn("profile-tabs", body)
        self.assertNotIn("chat-toggle", body)
        self.assertNotIn("chat-panel", body)

    def test_app_still_shows_profile_tabs_and_floating_ask_ai(self):
        with patch(
            "auth_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("profile-tabs", body)
        self.assertIn("chat-toggle", body)


class WorkshopNavigationTests(unittest.TestCase):
    """The global nav shows Workshop whenever the flag is on.

    Owner decision 2026-08-02: the entry is discoverable to every visitor so
    people can find Workshop; that same decision also removed the sign-in
    wall from the route itself (doc 20 section 6d) — a signed-out visitor
    now gets the real page over honestly-labeled sample content, not a
    sign-in redirect.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag

    def _nav_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        return body.split('platform-nav__links')[1].split("</ul>")[0]

    def _search_data(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        return body.split('id="nav-search-data"')[1].split("</script>")[0]

    def test_workshop_absent_when_flag_off_even_if_signed_in(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        with patch(
            "auth_routes.get_optional_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            nav = self._nav_html()

        self.assertNotIn(">Workshop<", nav)

    def test_workshop_present_after_interview_studio_when_signed_out(self):
        # Owner decision 2026-08-02: discoverable to everyone, so a visitor
        # can find it and sign in. The route stays protected regardless.
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch("auth_routes.get_optional_identity", return_value=None):
            nav = self._nav_html()

        self.assertIn(">Workshop<", nav)
        self.assertLess(nav.index(">Interview Studio<"), nav.index(">Workshop<"))

    def test_workshop_present_after_interview_studio_when_signed_in_and_flag_on(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "auth_routes.get_optional_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            nav = self._nav_html()

        self.assertIn(">Workshop<", nav)
        self.assertLess(nav.index(">Interview Studio<"), nav.index(">Workshop<"))

    def test_nav_entry_signed_out_visitor_gets_preview_never_another_owners_data(self):
        # Owner decision 2026-08-02 (doc 20 section 6d) supersedes the prior
        # "still gets the sign-in redirect" expectation: the link being
        # visible now matches real signed-out access to the public preview
        # — sample content only, never a real owner's library.
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        self.assertIn("wk-status-banner--preview", response.data.decode("utf-8"))

    def test_search_data_includes_workshop_whenever_the_flag_is_on(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch("auth_routes.get_optional_identity", return_value=None):
            signed_out = self._search_data()
        with patch(
            "auth_routes.get_optional_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            signed_in = self._search_data()

        self.assertIn('"title": "Workshop"', signed_out)
        self.assertIn('"title": "Workshop"', signed_in)

    def test_search_data_excludes_workshop_when_flag_off_even_if_signed_in(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        with patch(
            "auth_routes.get_optional_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            search_data = self._search_data()

        self.assertNotIn('"title": "Workshop"', search_data)


class WorkshopLibraryFilterAndSearchTests(unittest.TestCase):
    """BLOCKER 1 correction: the search form and Area/Status chips are real,
    server-side controls over the already-materialized, owner-scoped row
    list — not decorative dead controls."""

    WORK_KEY = ITEM_KEY
    PERSONAL_KEY = OTHER_ITEM_KEY
    ARCHIVED_KEY = "33333333-3333-3333-3333-333333333333"

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
        self.rows = [
            service_list_row(
                item_key=self.WORK_KEY,
                title="Systems Engineering Leadership",
                classification="work",
                status="confirmed",
            ),
            service_list_row(
                item_key=self.PERSONAL_KEY,
                title="Long-distance running",
                classification="personal",
                status="unfinished",
            ),
            service_list_row(
                item_key=self.ARCHIVED_KEY,
                title="A retired accomplishment",
                classification="both",
                status="archived",
            ),
        ]
        self.list_patch = patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result(self.rows),
        )
        self.list_patch.start()
        self._detail_by_key = {
            self.WORK_KEY: service_get_row(
                item_key=self.WORK_KEY,
                title="Systems Engineering Leadership",
                classification="work",
                status="confirmed",
            ),
            self.PERSONAL_KEY: service_get_row(
                item_key=self.PERSONAL_KEY,
                title="Long-distance running",
                classification="personal",
                status="unfinished",
            ),
            self.ARCHIVED_KEY: service_get_row(
                item_key=self.ARCHIVED_KEY,
                title="A retired accomplishment",
                classification="both",
                status="archived",
            ),
        }
        self.get_patch = patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            side_effect=lambda user_key, item_key: self._detail_by_key[item_key],
        )
        self.get_patch.start()

    def tearDown(self):
        self.get_patch.stop()
        self.list_patch.stop()
        self.identity_patch.stop()
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag

    def test_default_all_statuses_excludes_archived(self):
        response = self.client.get(ROUTE)
        body = response.data.decode("utf-8")

        self.assertIn("Systems Engineering Leadership", body)
        self.assertIn("Long-distance running", body)
        self.assertNotIn("A retired accomplishment", body)

    def test_archived_status_shows_only_archived(self):
        response = self.client.get(ROUTE + "?status=archived")
        body = response.data.decode("utf-8")

        self.assertIn("A retired accomplishment", body)
        self.assertNotIn("Systems Engineering Leadership", body)
        self.assertNotIn("Long-distance running", body)

    def test_area_filter_narrows_to_the_selected_classification(self):
        response = self.client.get(ROUTE + "?area=personal")
        body = response.data.decode("utf-8")

        self.assertIn("Long-distance running", body)
        self.assertNotIn("Systems Engineering Leadership", body)

    def test_search_matches_title_case_insensitively(self):
        response = self.client.get(ROUTE + "?q=SYSTEMS")
        body = response.data.decode("utf-8")

        self.assertIn("Systems Engineering Leadership", body)
        self.assertNotIn("Long-distance running", body)

    def test_search_query_is_preserved_in_the_input_value(self):
        response = self.client.get(ROUTE + "?q=running")
        body = response.data.decode("utf-8")

        self.assertIn('value="running"', body)

    def test_zero_matches_renders_honest_no_match_state_with_clear_link(self):
        response = self.client.get(ROUTE + "?q=nothing-will-match-this")
        body = response.data.decode("utf-8")

        self.assertIn("No items match", body)
        self.assertIn("Clear filters", body)
        self.assertIn('href="/app/workshop"', body)
        # Distinct from the true first-run empty state's copy.
        self.assertNotIn("Nothing saved here yet", body)
        self.assertNotIn("Systems Engineering Leadership", body)

    def test_garbage_area_and_status_params_fall_back_to_all(self):
        response = self.client.get(ROUTE + "?area=bogus&status=whatever")
        body = response.data.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        # Falls back to all/all: default (non-archived) behavior holds.
        self.assertIn("Systems Engineering Leadership", body)
        self.assertIn("Long-distance running", body)
        self.assertNotIn("A retired accomplishment", body)

    def test_selected_chips_carry_aria_current_not_aria_pressed(self):
        response = self.client.get(ROUTE + "?area=work&status=confirmed")
        body = response.data.decode("utf-8")

        self.assertNotIn("aria-pressed", body)
        self.assertIn('aria-current="true"', body)

    def test_chips_are_real_links_preserving_the_other_parameter(self):
        response = self.client.get(ROUTE + "?area=work&status=confirmed")
        body = response.data.decode("utf-8")

        # Clicking the "Personal" area chip must keep status=confirmed.
        self.assertIn("/app/workshop?area=personal&amp;status=confirmed", body)
        # Clicking the "Archived" status chip must keep area=work.
        self.assertIn("/app/workshop?area=work&amp;status=archived", body)

    def test_filters_preserved_across_area_and_status_combinations(self):
        for area_key in ("all", "work", "personal", "both"):
            for status_key in ("all", "confirmed", "suggested", "unfinished", "archived"):
                with self.subTest(area=area_key, status=status_key):
                    response = self.client.get(
                        ROUTE + f"?area={area_key}&status={status_key}"
                    )
                    body = response.data.decode("utf-8")
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(f"area={area_key}&amp;status={status_key}", body)

    def test_search_hidden_fields_preserve_area_and_status_on_submit(self):
        response = self.client.get(ROUTE + "?area=personal&status=unfinished")
        body = response.data.decode("utf-8")

        self.assertIn('name="area" value="personal"', body)
        self.assertIn('name="status" value="unfinished"', body)


class WorkshopLibraryTruncationTests(unittest.TestCase):
    """BLOCKER 2 correction: an owner with more than 200 items sees an
    honest "Showing 200 of <true total>" footer rather than a footer that
    silently implies 200 is everything."""

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
        self.rows = [
            service_list_row(
                item_key=f"{index:08x}-0000-0000-0000-000000000000",
                title=f"Item {index}",
            )
            for index in range(200)
        ]
        self.list_patch = patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result(self.rows, total_count=543),
        )
        self.list_patch.start()
        self.get_patch = patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(item_key=self.rows[0]["item_key"]),
        )
        self.get_patch.start()

    def tearDown(self):
        self.get_patch.stop()
        self.list_patch.stop()
        self.identity_patch.stop()
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag

    def test_truncated_list_renders_the_honest_footer(self):
        response = self.client.get(ROUTE)
        body = response.data.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Showing 200 of 543", body)
        # Recheck: the footer states the real window scope instead of
        # promising that search can reach items it cannot see.
        self.assertIn(
            "Filters and search cover your 200 most recently updated items", body
        )
        self.assertNotIn("use search to narrow", body)
        # The old, misleading "Showing 200 of 200" phrasing never renders.
        self.assertNotIn("Showing 200 of 200", body)

    def test_truncated_filtered_view_shows_the_real_rendered_count(self):
        # Recheck REQUIRED fix: the shown count must be the number of rows
        # actually rendered, never a hardcoded 200. 60 of the 200 window
        # rows are personal; ?area=personal renders exactly those 60.
        rows = list(self.rows)
        for index in range(60):
            rows[index] = dict(rows[index], classification="personal")
        with patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result(rows, total_count=543),
        ):
            response = self.client.get(ROUTE + "?area=personal")
        body = response.data.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Showing 60 of 543", body)
        self.assertNotIn("Showing 200 of 543", body)
        self.assertIn(
            "Filters and search cover your 200 most recently updated items", body
        )

    def test_truncated_zero_match_never_asserts_that_nothing_exists(self):
        # Recheck REQUIRED fix: with 343 items beyond the window, a
        # zero-match filter result may not claim "No items match" — the
        # code cannot know that. The truncation-aware copy renders instead.
        response = self.client.get(ROUTE + "?q=zz-cannot-match-anything-zz")
        body = response.data.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("No matches in your recent items", body)
        self.assertIn("Older items are not searched yet", body)
        self.assertNotIn("No items match</h2>", body)

    def test_untruncated_list_at_exactly_200_shows_the_normal_footer(self):
        with patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result(self.rows, total_count=200),
        ):
            response = self.client.get(ROUTE)
        body = response.data.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Showing 200 of 200 items", body)
        self.assertNotIn("use search to narrow", body)


# Test gap 7: every route on the workshop blueprint (5 GET + 9 POST = 14),
# used for the flag-off identity-spy neutrality matrix below.
ALL_WORKSHOP_ROUTES = (
    ("get", ROUTE, {}),
    ("get", "/app/workshop/add", {}),
    ("get", f"/app/workshop/items/{ITEM_KEY}/edit", {}),
    ("get", f"/app/workshop/items/{ITEM_KEY}/saved", {}),
    ("get", f"/app/workshop/items/{ITEM_KEY}/delete", {}),
    ("post", "/app/workshop/add", {}),
    (
        "post",
        "/app/workshop/add/review",
        {"title": "t", "wording": "w", "classification": ""},
    ),
    (
        "post",
        "/app/workshop/items",
        {
            "title": "t",
            "wording": "w",
            "classification": "",
            "idempotency_key": "k",
            "save_action": "confirm",
        },
    ),
    ("post", f"/app/workshop/items/{ITEM_KEY}/edit", {}),
    (
        "post",
        f"/app/workshop/items/{ITEM_KEY}/edit/review",
        {
            "title": "t",
            "wording": "w",
            "classification": "",
            "expected_row_version": "0000000000000001",
        },
    ),
    (
        "post",
        f"/app/workshop/items/{ITEM_KEY}",
        {
            "title": "t",
            "wording": "w",
            "classification": "",
            "expected_row_version": "0000000000000001",
            "save_action": "confirm",
        },
    ),
    (
        "post",
        f"/app/workshop/items/{ITEM_KEY}/archive",
        {"expected_row_version": "0000000000000001"},
    ),
    (
        "post",
        f"/app/workshop/items/{ITEM_KEY}/restore",
        {"expected_row_version": "0000000000000001"},
    ),
    (
        "post",
        f"/app/workshop/items/{ITEM_KEY}/delete",
        {"expected_row_version": "0000000000000001", "confirm_delete": "delete"},
    ),
)


class WorkshopFlagOffNeutralityMatrixTests(unittest.TestCase):
    """Test gap 7: flag-off identity-spy neutrality across ALL fourteen
    routes on the workshop blueprint, not only the main library route."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False

    def tearDown(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag

    def test_flag_off_is_neutral_and_resolves_no_identity_on_every_route(self):
        for method, path, data in ALL_WORKSHOP_ROUTES:
            with self.subTest(method=method, path=path):
                with patch("workshop_routes.get_current_identity") as identity_mock:
                    response = getattr(self.client, method)(path, data=data)

                self.assertEqual(response.status_code, 404)
                identity_mock.assert_not_called()


class WorkshopPublicPreviewTests(unittest.TestCase):
    """PS-WORKSHOP-001 public preview mode (owner decision 2026-08-02, doc 20
    section 6d): "Workshop must not be behind a login wall right now."
    Signed-out visitors get the full experience over honestly-labeled sample
    content (the library) or their own typed text (add/review/save) instead
    of the sign-in redirect these routes used to return, while every
    real-data guarantee stays exactly as it is: no owner-scoped service
    method is ever reachable anonymously, and no confirming save ever writes
    or claims a save happened.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_fixture_flag = app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        self.identity_patch = patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        )
        self.identity_mock = self.identity_patch.start()
        # Owner instruction 2026-08-02 (doc 20 section 6e) tests repeatedly
        # POST to the rate-limited save/update/archive/restore/delete
        # routes; the limiter's counter is process-wide and would otherwise
        # accumulate across unrelated tests and spuriously 429 them.
        # Disabled here — mirrors test_workshop_flows.py's own established
        # pattern for the same reason.
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        self.identity_patch.stop()
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag

    # 1. Signed-out GET /app/workshop returns 200, not 302, with the
    #    preview banner present.
    def test_signed_out_library_returns_200_with_preview_banner(self):
        response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("wk-status-banner--preview", body)
        self.assertIn("example information", body)

    # 2. Signed-out requests never call any owner-scoped service method.
    def test_signed_out_library_never_calls_owner_scoped_service_methods(self):
        with patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner"
        ) as list_mock, patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner"
        ) as get_mock, patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock, patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner"
        ) as update_mock:
            response = self.client.get(ROUTE + "?area=work&status=confirmed&q=eng")

        self.assertEqual(response.status_code, 200)
        list_mock.assert_not_called()
        get_mock.assert_not_called()
        save_mock.assert_not_called()
        update_mock.assert_not_called()

    # 3. Signed-out POST /app/workshop/items does not call
    #    save_knowledge_item_for_owner, and the response never contains
    #    "Saved privately" — for either save_action value, since neither
    #    writes anything for a signed-out visitor.
    def test_signed_out_confirm_save_never_writes_or_claims_saved(self):
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "My real preview title",
                    "wording": "My real preview wording that must stay visible.",
                    "classification": "work",
                    "idempotency_key": "anon-key-1",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        save_mock.assert_not_called()
        body = response.data.decode("utf-8")
        self.assertNotIn("Saved privately", body)
        # The confirming save's own template only ever surfaces wording (not
        # title) on this screen — true for the real path too, see
        # test_workshop_flows.py's SavedConfirmationTests, which asserts no
        # title either. The member's wording stays visible; nothing is lost.
        self.assertIn("My real preview wording that must stay visible.", body)
        self.assertIn("Sign in to save", body)

    def test_signed_out_add_saves_the_demo_item_as_confirmed(self):
        """Owner-ordered knowledge confirmation rule (2026-08-06): a
        member-authored save confirms immediately, and that rule applies to
        the anonymous preview library exactly as it applies to the real
        store. Independent review carried this as a missing guard: nothing
        asserted that workshop_routes.py's anonymous add_item call actually
        passes status="confirmed" rather than the retired "unfinished"
        outcome, so a regression there would pass silently."""
        with patch(
            "workshop_routes.workshop_demo_library.add_item",
            return_value=("11111111-1111-1111-1111-111111111111", None),
        ) as add_mock:
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "My real preview title",
                    "wording": "My real preview wording.",
                    "classification": "work",
                    "idempotency_key": "anon-key-status-guard",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        add_mock.assert_called_once()
        _, kwargs = add_mock.call_args
        self.assertEqual(kwargs["status"], "confirmed")

    def test_signed_out_edit_saves_the_demo_item_as_confirmed(self):
        """The edit-confirm sibling of the add guard immediately above:
        workshop_routes.py's anonymous edit_item call must also pass
        status="confirmed", never "unfinished"."""
        item_key = "22222222-2222-2222-2222-222222222222"
        with patch(
            "workshop_routes.workshop_demo_library.edit_item",
            return_value=(True, None),
        ) as edit_mock:
            response = self.client.post(
                f"/app/workshop/items/{item_key}",
                data={
                    "title": "My real preview title",
                    "wording": "My real preview wording.",
                    "classification": "work",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 302)
        edit_mock.assert_called_once()
        _, kwargs = edit_mock.call_args
        self.assertEqual(kwargs["status"], "confirmed")

    def test_signed_out_stale_unfinished_action_still_only_previews(self):
        # Owner-ordered knowledge confirmation rule (2026-08-06): every save
        # confirms now, member-authored or anonymous alike — there is no
        # "unfinished" save outcome left. A stale posted
        # save_action="unfinished" (from a cached pre-2026-08-06 page)
        # produces exactly the same confirmed preview-session save "confirm"
        # would — added to this visitor's own session only, never the real
        # database, never save_knowledge_item_for_owner, never "Saved
        # privately" (that phrase describes a real, permanent save, which
        # this is not).
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "Another preview title",
                    "wording": "Another preview wording.",
                    "classification": "",
                    "idempotency_key": "anon-key-2",
                    "save_action": "unfinished",
                },
                headers=SAME_ORIGIN_HEADERS,
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        save_mock.assert_not_called()
        body = response.data.decode("utf-8")
        self.assertNotIn("Saved privately", body)
        # The confirming save's own template only ever surfaces wording (not
        # title) on this screen — see this class's earlier assertion of the
        # same fact for the "confirm" case.
        self.assertIn("Added to this preview session", body)
        self.assertIn("Another preview wording.", body)

    # 4. The signed-out response never contains another member's data —
    #    sample content only, even if the real store somehow held data.
    def test_signed_out_response_never_contains_another_members_data(self):
        with patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result(
                [service_list_row(title="Someone Else's Real Confidential Item")]
            ),
        ) as list_mock:
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        list_mock.assert_not_called()
        self.assertNotIn(b"Someone Else&#39;s Real Confidential Item", response.data)
        self.assertNotIn(b"Someone Else's Real Confidential Item", response.data)
        # Sample content only (the demo library's own item titles — owner
        # instruction 2026-08-02, doc 20 section 6e: the Jordan Ellis demo
        # library replaced the four-item checkpoint fixture here).
        self.assertIn(b"Rebuilt patient intake from 40 minutes to 9", response.data)

    # 5. Signed-in behavior is completely unchanged.
    def test_signed_in_behavior_is_unchanged(self):
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=list_result([service_list_row()]),
        ) as list_mock, patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertNotIn("wk-status-banner--preview", body)
        self.assertIn("Systems Engineering Leadership", body)
        list_mock.assert_called_once_with("member-checkpoint-1", include_archived=True)

    # 6. Flag-off still returns a neutral 404 before anything else,
    #    signed-out included.
    def test_flag_off_returns_404_before_anything_else_signed_out_included(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False

        response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 404)
        self.identity_mock.assert_not_called()

    # 7. Cache-Control: private, no-store still set on preview responses.
    def test_preview_responses_still_carry_private_no_store(self):
        library_response = self.client.get(ROUTE)
        self.assertEqual(
            library_response.headers.get("Cache-Control"), "private, no-store"
        )

        with patch("workshop_routes.knowledge_service.save_knowledge_item_for_owner"):
            saved_response = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "Cache header check",
                    "wording": "Checking the header on the preview-complete render.",
                    "classification": "",
                    "idempotency_key": "anon-key-3",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(
            saved_response.headers.get("Cache-Control"), "private, no-store"
        )

    # ------------------------------------------------------------------
    # Owner instruction 2026-08-02 (doc 20 section 6e): the public demo
    # library (17-item Jordan Ellis persona) and session-backed play.
    # ------------------------------------------------------------------

    # 8. Every Area and Status filter returns the expected non-empty subset
    #    of the demo library — real counts, not just 200s.
    def test_anonymous_library_shows_demo_items_with_real_filter_counts(self):
        response = self.client.get(ROUTE)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Rebuilt patient intake from 40 minutes to 9",
            response.data.decode("utf-8"),
        )

        # Status filters: exact counts matching the content spec exactly
        # (11 confirmed, 2 suggested, 2 unfinished, 2 archived = 17 total).
        expected_status_counts = {
            "confirmed": 11,
            "suggested": 2,
            "unfinished": 2,
            "archived": 2,
        }
        for status, expected_count in expected_status_counts.items():
            resp = self.client.get(ROUTE, query_string={"status": status})
            self.assertEqual(resp.status_code, 200)
            count = _library_item_title_count(resp.data.decode("utf-8"))
            self.assertEqual(count, expected_count, f"status={status}")

        # Area filters, with status=all (which excludes the 2 archived
        # items, the same "hidden unless asked for" convention the real
        # signed-in library also uses) — real, non-trivial counts.
        expected_area_counts = {"work": 8, "personal": 3, "both": 4}
        for area, expected_count in expected_area_counts.items():
            resp = self.client.get(ROUTE, query_string={"area": area, "status": "all"})
            self.assertEqual(resp.status_code, 200)
            count = _library_item_title_count(resp.data.decode("utf-8"))
            self.assertEqual(count, expected_count, f"area={area}")

    # 9. Search matches a known demo title and misses a nonsense query.
    def test_anonymous_search_matches_known_title_and_misses_nonsense(self):
        match = self.client.get(ROUTE, query_string={"q": "patient intake"})
        self.assertEqual(match.status_code, 200)
        self.assertIn(
            "Rebuilt patient intake from 40 minutes to 9", match.data.decode("utf-8")
        )

        miss = self.client.get(ROUTE, query_string={"q": "zzz-nonsense-query-xyz"})
        self.assertEqual(miss.status_code, 200)
        body = miss.data.decode("utf-8")
        self.assertNotIn("Rebuilt patient intake", body)
        self.assertIn("No items match", body)

    # 10. Add -> review -> confirm as an anonymous visitor: the item appears
    #     in the library on the NEXT request (session persistence).
    def test_anonymous_add_review_confirm_persists_across_requests(self):
        review = self.client.post(
            "/app/workshop/add/review",
            data={
                "title": "My anonymous accomplishment",
                "wording": "A realistic sentence about something I did.",
                "classification": "work",
                "idempotency_key": "anon-add-1",
            },
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(review.status_code, 200)

        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            saved = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "My anonymous accomplishment",
                    "wording": "A realistic sentence about something I did.",
                    "classification": "work",
                    "idempotency_key": "anon-add-1",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(saved.status_code, 200)
        save_mock.assert_not_called()
        saved_body = saved.data.decode("utf-8")
        self.assertNotIn("Saved privately", saved_body)
        # This confirming-save screen only ever surfaces wording, not title
        # (true for the real signed-in path too; see workshop_saved.html).
        self.assertIn(
            "A realistic sentence about something I did.", saved_body
        )

        # The NEXT request (a fresh GET) shows the TITLE in the library —
        # proves this lives in the session, not just the immediate response.
        library = self.client.get(ROUTE)
        self.assertIn(
            "My anonymous accomplishment", library.data.decode("utf-8")
        )

    # 11. Edit takes effect in the session copy on the following request.
    def test_anonymous_edit_persists_across_requests(self):
        item_key = _demo_item_key(
            "Led the move from three scheduling systems to one"
        )
        review = self.client.post(
            f"/app/workshop/items/{item_key}/edit/review",
            data={
                "title": "Edited scheduling systems title",
                "wording": "Edited wording describing the same accomplishment.",
                "classification": "personal",
                "expected_row_version": "0000000000000000",
            },
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(review.status_code, 200)

        with patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner"
        ) as update_mock:
            confirm = self.client.post(
                f"/app/workshop/items/{item_key}",
                data={
                    "title": "Edited scheduling systems title",
                    "wording": "Edited wording describing the same accomplishment.",
                    "classification": "personal",
                    "expected_row_version": "0000000000000000",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(confirm.status_code, 302)
        update_mock.assert_not_called()

        library = self.client.get(ROUTE, query_string={"item": item_key})
        body = library.data.decode("utf-8")
        self.assertIn("Edited scheduling systems title", body)
        self.assertIn(
            "Edited wording describing the same accomplishment.", body
        )

    # 11 (cont.). Archive then Restore take effect in the session copy on
    #     the following request.
    def test_anonymous_archive_and_restore_persist_across_requests(self):
        item_key = _demo_item_key(
            "Requirements gathering with people who hate meetings"
        )

        with patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner"
        ) as archive_mock:
            archived = self.client.post(
                f"/app/workshop/items/{item_key}/archive",
                data={"expected_row_version": "0000000000000000"},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(archived.status_code, 302)
        archive_mock.assert_not_called()

        archived_view = self.client.get(ROUTE, query_string={"status": "archived"})
        self.assertIn(
            "Requirements gathering with people who hate meetings",
            archived_view.data.decode("utf-8"),
        )
        confirmed_view = self.client.get(ROUTE, query_string={"status": "confirmed"})
        self.assertNotIn(
            "Requirements gathering with people who hate meetings",
            confirmed_view.data.decode("utf-8"),
        )

        with patch(
            "workshop_routes.knowledge_service.restore_knowledge_item_for_owner"
        ) as restore_mock:
            restored = self.client.post(
                f"/app/workshop/items/{item_key}/restore",
                data={"expected_row_version": "0000000000000000"},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(restored.status_code, 302)
        restore_mock.assert_not_called()

        confirmed_after_restore = self.client.get(
            ROUTE, query_string={"status": "confirmed"}
        )
        self.assertIn(
            "Requirements gathering with people who hate meetings",
            confirmed_after_restore.data.decode("utf-8"),
        )

    # 11 (cont.). Delete takes effect in the session copy on the following
    #     request.
    def test_anonymous_delete_persists_across_requests(self):
        item_key = _demo_item_key("Grant reporting and outcome measurement")

        confirm_page = self.client.get(f"/app/workshop/items/{item_key}/delete")
        self.assertEqual(confirm_page.status_code, 200)
        self.assertIn(
            "Grant reporting and outcome measurement",
            confirm_page.data.decode("utf-8"),
        )

        with patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner"
        ) as delete_mock:
            deleted = self.client.post(
                f"/app/workshop/items/{item_key}/delete",
                data={
                    "confirm_delete": "delete",
                    "expected_row_version": "0000000000000000",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(deleted.status_code, 302)
        delete_mock.assert_not_called()

        library = self.client.get(ROUTE)
        self.assertNotIn(
            "Grant reporting and outcome measurement", library.data.decode("utf-8")
        )

    # 12. Caps enforced: the 5th added item is refused with the honest
    #     message, and the visitor's typed text is never silently dropped.
    def test_anonymous_add_cap_refuses_fifth_item_with_honest_message(self):
        with patch("workshop_routes.knowledge_service.save_knowledge_item_for_owner"):
            for i in range(workshop_demo_library.MAX_ADDED_ITEMS):
                resp = self.client.post(
                    "/app/workshop/items",
                    data={
                        "title": f"Cap item {i}",
                        "wording": "Some reasonable wording.",
                        "classification": "work",
                        "idempotency_key": f"cap-key-{i}",
                        "save_action": "confirm",
                    },
                    headers=SAME_ORIGIN_HEADERS,
                )
                self.assertEqual(resp.status_code, 200)

        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            fifth = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "Fifth item",
                    "wording": "Should be refused, not silently dropped.",
                    "classification": "work",
                    "idempotency_key": "cap-key-5",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(fifth.status_code, 200)
        save_mock.assert_not_called()
        body = fifth.data.decode("utf-8")
        self.assertIn(workshop_demo_library.CAP_ITEMS_MESSAGE, body)
        # The visitor's own typed text is preserved on the form, not lost.
        self.assertIn("Fifth item", body)

        library = self.client.get(ROUTE)
        self.assertNotIn("Fifth item", library.data.decode("utf-8"))

    # 12 (cont.). Over-long wording is rejected with an honest message
    #     (this implementation's chosen rule: reject, never silently
    #     truncate, so the visitor's exact text is never altered without
    #     telling them).
    def test_anonymous_add_wording_cap_refuses_oversized_wording(self):
        with patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock:
            resp = self.client.post(
                "/app/workshop/items",
                data={
                    "title": "Long wording item",
                    "wording": "x" * (workshop_demo_library.MAX_PREVIEW_WORDING_UNITS + 1),
                    "classification": "work",
                    "idempotency_key": "long-wording-key",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(resp.status_code, 200)
        save_mock.assert_not_called()
        body = resp.data.decode("utf-8")
        self.assertIn(workshop_demo_library.CAP_WORDING_MESSAGE, body)

        library = self.client.get(ROUTE)
        self.assertNotIn("Long wording item", library.data.decode("utf-8"))

    # 13. No anonymous request across the FULL add/edit/archive/restore/
    #     delete flow ever calls any *_for_owner service method or reaches
    #     the database, and no response ever contains "Saved privately".
    def test_anonymous_full_mutation_flow_never_touches_owner_scoped_service(self):
        item_key = _demo_item_key("Data migration without losing history")
        with patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner"
        ) as list_mock, patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner"
        ) as get_mock, patch(
            "workshop_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as save_mock, patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner"
        ) as update_mock, patch(
            "workshop_routes.knowledge_service.archive_knowledge_item_for_owner"
        ) as archive_mock, patch(
            "workshop_routes.knowledge_service.restore_knowledge_item_for_owner"
        ) as restore_mock, patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner"
        ) as delete_mock:
            responses = [
                self.client.get(ROUTE),
                self.client.get(f"/app/workshop/items/{item_key}/edit"),
                self.client.post(
                    f"/app/workshop/items/{item_key}/edit/review",
                    data={
                        "title": "New title",
                        "wording": "New wording.",
                        "classification": "work",
                        "expected_row_version": "0000000000000000",
                    },
                    headers=SAME_ORIGIN_HEADERS,
                ),
                self.client.post(
                    f"/app/workshop/items/{item_key}",
                    data={
                        "title": "New title",
                        "wording": "New wording.",
                        "classification": "work",
                        "expected_row_version": "0000000000000000",
                        "save_action": "confirm",
                    },
                    headers=SAME_ORIGIN_HEADERS,
                ),
                self.client.post(
                    f"/app/workshop/items/{item_key}/archive",
                    data={"expected_row_version": "0000000000000000"},
                    headers=SAME_ORIGIN_HEADERS,
                ),
                self.client.post(
                    f"/app/workshop/items/{item_key}/restore",
                    data={"expected_row_version": "0000000000000000"},
                    headers=SAME_ORIGIN_HEADERS,
                ),
                self.client.get(f"/app/workshop/items/{item_key}/delete"),
                self.client.post(
                    f"/app/workshop/items/{item_key}/delete",
                    data={
                        "confirm_delete": "delete",
                        "expected_row_version": "0000000000000000",
                    },
                    headers=SAME_ORIGIN_HEADERS,
                ),
            ]

        list_mock.assert_not_called()
        get_mock.assert_not_called()
        save_mock.assert_not_called()
        update_mock.assert_not_called()
        archive_mock.assert_not_called()
        restore_mock.assert_not_called()
        delete_mock.assert_not_called()
        for response in responses:
            self.assertNotIn(b"Saved privately", response.data)

    # 14. Two different sessions do not see each other's additions.
    def test_two_different_sessions_do_not_share_additions(self):
        client_a = app.test_client()
        client_b = app.test_client()

        with patch("workshop_routes.knowledge_service.save_knowledge_item_for_owner"):
            client_a.post(
                "/app/workshop/items",
                data={
                    "title": "Visitor A own distinctive item",
                    "wording": "Only visitor A should see this.",
                    "classification": "work",
                    "idempotency_key": "session-a-key",
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        library_b = client_b.get(ROUTE)
        self.assertNotIn(
            "Visitor A own distinctive item", library_b.data.decode("utf-8")
        )

        library_a = client_a.get(ROUTE)
        self.assertIn("Visitor A own distinctive item", library_a.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
