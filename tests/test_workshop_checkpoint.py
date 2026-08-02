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

from app import app
from identity import AuthenticationRequired
from services.database_service import DatabaseServiceError
from services.knowledge_service import KnowledgeItemListResult, KnowledgeServiceError


ROUTE = "/app/workshop"
ITEM_KEY = "11111111-1111-1111-1111-111111111111"
OTHER_ITEM_KEY = "22222222-2222-2222-2222-222222222222"
FOREIGN_ITEM_KEY = "99999999-9999-9999-9999-999999999999"


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

    def test_signed_out_member_is_redirected_with_the_exact_return_path(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        ):
            response = self.client.get(ROUTE)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/auth/sign-in?return_to=/app/workshop",
        )

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
    """The global nav shows Workshop only when signed in AND flag-on."""

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

    def test_workshop_absent_when_signed_out_even_if_flag_on(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch("auth_routes.get_optional_identity", return_value=None):
            nav = self._nav_html()

        self.assertNotIn(">Workshop<", nav)

    def test_workshop_present_after_interview_studio_when_signed_in_and_flag_on(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch(
            "auth_routes.get_optional_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            nav = self._nav_html()

        self.assertIn(">Workshop<", nav)
        self.assertLess(nav.index(">Interview Studio<"), nav.index(">Workshop<"))

    def test_search_data_includes_workshop_only_when_signed_in_and_flag_on(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        with patch("auth_routes.get_optional_identity", return_value=None):
            signed_out = self._search_data()
        with patch(
            "auth_routes.get_optional_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        ):
            signed_in = self._search_data()

        self.assertNotIn('"title": "Workshop"', signed_out)
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


if __name__ == "__main__":
    unittest.main()
