import json
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app import app
from identity import AuthenticationRequired
from services.database_service import DatabaseServiceError
from services.owner_home_service import (
    MAX_PAYLOAD_BYTES,
    OwnerHomeContractError,
    OwnerHomeService,
    OwnerHomeViewModel,
)


OWNER_A_PROFILE = "11111111-1111-1111-1111-111111111111"
OWNER_B_PROFILE = "22222222-2222-2222-2222-222222222222"
FAILED_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROPOSAL_A = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
READY_A = "cccccccc-cccc-cccc-cccc-cccccccccccc"
MOMENT_A = "dddddddd-dddd-dddd-dddd-dddddddddddd"
FAILED_B = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


def owner_row(profile_key=OWNER_A_PROFILE, display_name="Owner A", token="01" * 8):
    return {
        "profile_key": profile_key,
        "display_name": display_name,
        "profile_row_version": token,
    }


def review_row(item_key, kind, status, minute, token):
    return {
        "item_key": item_key,
        "review_kind": kind,
        "created_at_utc": f"2026-07-20T10:{minute:02d}:00",
        "updated_at_utc": f"2026-07-20T10:{minute + 1:02d}:00",
        "version_token": token * 8,
        "status": status,
    }


def moment_row(moment_key=MOMENT_A, title="A real confirmed Moment"):
    return {
        "moment_key": moment_key,
        "confirmed_version": 2,
        "title": title,
        "occurred_on": "2026-07-19",
        "updated_at_utc": "2026-07-20T10:40:00",
        "version_token": "05" * 8,
        "status": "confirmed",
    }


def complete_result_sets():
    return [
        [owner_row()],
        [
            review_row(FAILED_A, "voice_draft_failed", "failed", 1, "02"),
            review_row(
                PROPOSAL_A, "moment_proposal_pending", "proposal", 2, "03"
            ),
            review_row(READY_A, "voice_draft_ready", "needs_review", 3, "04"),
        ],
        [moment_row()],
    ]


class OwnerHomeServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.database.execute_procedure.return_value = complete_result_sets()
        self.clock = lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc)
        self.service = OwnerHomeService(database=self.database, clock=self.clock)
        self.identity = SimpleNamespace(user_key="owner-a")

    def payload(self):
        return self.service.get_home(self.identity).to_dict()

    def test_schema_shape_limits_and_server_owned_availability(self):
        payload = self.payload()

        self.assertEqual(payload["schema_version"], "owner-home.v1")
        self.assertEqual(payload["owner"]["profile_key"], OWNER_A_PROFILE)
        self.assertEqual(len(payload["review_items"]), 3)
        self.assertEqual(payload["recent_moment"]["moment_key"], MOMENT_A)
        self.assertIsNone(payload["resurfaced_moment"])
        self.assertIsNone(payload["noticed_item"])
        self.assertIsNone(payload["connection_item"])
        self.assertEqual(
            payload["availability"],
            {
                "resurfaced_moment": {"state": "coming_later"},
                "noticed_item": {"state": "coming_later"},
                "connection_item": {"state": "coming_later"},
            },
        )
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.assertLessEqual(len(encoded), MAX_PAYLOAD_BYTES)

    def test_one_core_query_and_no_optional_member_data_adapters(self):
        self.payload()

        self.database.execute_procedure.assert_called_once_with(
            "usp_GetOwnerHomeForOwner", [("@UserKey", "owner-a")]
        )

    def test_review_order_destinations_and_fixed_owner_safe_summaries(self):
        reviews = self.payload()["review_items"]

        self.assertEqual(
            [item["review_kind"] for item in reviews],
            [
                "voice_draft_failed",
                "moment_proposal_pending",
                "voice_draft_ready",
            ],
        )
        self.assertEqual(reviews[0]["destination"], f"/app/capture?voice={FAILED_A}")
        self.assertEqual(
            reviews[1]["destination"], f"/app/moments/{PROPOSAL_A}/review"
        )
        self.assertNotIn("transcript", json.dumps(reviews).lower())
        self.assertNotIn("blob", json.dumps(reviews).lower())

    def test_state_version_is_stable_and_changes_with_selected_state(self):
        first = self.payload()["state_version"]
        second = self.payload()["state_version"]
        self.assertEqual(first, second)

        changed = complete_result_sets()
        changed[1][0]["version_token"] = "99" * 8
        self.database.execute_procedure.return_value = changed
        self.assertNotEqual(first, self.payload()["state_version"])

    def test_next_step_uses_review_then_recent_then_capture(self):
        self.assertEqual(self.payload()["next_step"]["destination"], f"/app/capture?voice={FAILED_A}")

        no_reviews = complete_result_sets()
        no_reviews[1] = []
        self.database.execute_procedure.return_value = no_reviews
        self.assertEqual(
            self.payload()["next_step"]["destination"],
            f"/app/moments/{MOMENT_A}/review",
        )

        empty = complete_result_sets()
        empty[1] = []
        empty[2] = []
        self.database.execute_procedure.return_value = empty
        self.assertEqual(self.payload()["next_step"]["destination"], "/app/capture")

    def test_unknown_columns_kinds_statuses_and_extra_rows_fail_closed(self):
        cases = []

        extra_owner = complete_result_sets()
        extra_owner[0][0]["email"] = "private@example.invalid"
        cases.append(extra_owner)

        extra_review = complete_result_sets()
        extra_review[1][0]["transcript"] = "PRIVATE TRANSCRIPT"
        cases.append(extra_review)

        bad_kind = complete_result_sets()
        bad_kind[1][0]["review_kind"] = "unreleased_workflow"
        cases.append(bad_kind)

        bad_status = complete_result_sets()
        bad_status[1][0]["status"] = "confirmed"
        cases.append(bad_status)

        too_many = complete_result_sets()
        too_many[1].append(
            review_row(
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "voice_draft_ready",
                "needs_review",
                4,
                "06",
            )
        )
        cases.append(too_many)

        extra_moment = complete_result_sets()
        extra_moment[2].append(
            moment_row("99999999-9999-9999-9999-999999999999", "Another")
        )
        cases.append(extra_moment)

        for result_sets in cases:
            with self.subTest(case=cases.index(result_sets)):
                self.database.execute_procedure.return_value = result_sets
                with self.assertRaises(OwnerHomeContractError):
                    self.payload()

    def test_payload_cap_rejects_oversized_view_model(self):
        view_model = OwnerHomeViewModel(
            owner={"profile_key": OWNER_A_PROFILE, "display_name": "X" * 70000},
            generated_at="2026-07-20T11:00:00Z",
            state_version="a" * 64,
            capture_action={
                "action_kind": "capture",
                "destination": "/app/capture",
                "availability": {"state": "available"},
                "label": "Capture something",
            },
            review_items=(),
            recent_moment=None,
            next_step={
                "action_kind": "start_text_capture",
                "label": "Start a new Capture",
                "reason": "Capture something you want to remember.",
                "destination": "/app/capture",
                "availability": {"state": "available"},
            },
        )
        with self.assertRaisesRegex(OwnerHomeContractError, "payload limit"):
            view_model.to_dict()

    def test_serializer_rejects_unknown_internal_action_fields(self):
        view_model = self.service.get_home(self.identity)
        object.__setattr__(
            view_model,
            "capture_action",
            {**view_model.capture_action, "private_count": 17},
        )
        with self.assertRaisesRegex(OwnerHomeContractError, "Capture action shape"):
            view_model.to_dict()

    def test_two_owner_serialized_byte_canaries_do_not_bleed(self):
        payload_a = self.payload()
        bytes_a = json.dumps(payload_a, sort_keys=True).encode()

        owner_b = [
            [owner_row(OWNER_B_PROFILE, "Owner B", "10" * 8)],
            [review_row(FAILED_B, "voice_draft_failed", "failed", 5, "11")],
            [],
        ]
        self.database.execute_procedure.return_value = owner_b
        payload_b = self.service.get_home(
            SimpleNamespace(user_key="owner-b")
        ).to_dict()
        bytes_b = json.dumps(payload_b, sort_keys=True).encode()

        self.assertIn(OWNER_A_PROFILE.encode(), bytes_a)
        self.assertNotIn(OWNER_B_PROFILE.encode(), bytes_a)
        self.assertIn(OWNER_B_PROFILE.encode(), bytes_b)
        self.assertNotIn(OWNER_A_PROFILE.encode(), bytes_b)
        self.assertNotIn(FAILED_A.encode(), bytes_b)

    def test_missing_identity_or_result_set_shape_fails_closed(self):
        with self.assertRaises(OwnerHomeContractError):
            self.service.get_home(SimpleNamespace(user_key=""))

        for result_sets in ([], [[]], [[], [], []], [[owner_row()], []]):
            with self.subTest(result_sets=result_sets):
                self.database.execute_procedure.return_value = result_sets
                with self.assertRaises(OwnerHomeContractError):
                    self.service.get_home(self.identity)


class OwnerHomeRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_OWNER_HOME_ENABLED")
        self.original_dev_user_key = app.config.get("PEERSLATE_DEV_USER_KEY")
        self.original_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = False

    def tearDown(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = self.original_flag
        app.config["PEERSLATE_DEV_USER_KEY"] = self.original_dev_user_key
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = self.original_dev_identity

    def view_model(self):
        database = Mock()
        database.execute_procedure.return_value = complete_result_sets()
        return OwnerHomeService(
            database=database,
            clock=lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc),
        ).get_home(SimpleNamespace(user_key="owner-a"))

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_off_is_neutral_404_before_identity_or_retrieval(
        self, identity, home_service
    ):
        response = self.client.get("/api/v1/owner/home")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "not_found"})
        identity.assert_not_called()
        home_service.get_home.assert_not_called()

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_on_anonymous_is_json_401_before_home_read(
        self, identity, home_service
    ):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get("/api/v1/owner/home")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "authentication_required"})
        self.assertNotIn(b"PRIVATE", response.data)
        home_service.get_home.assert_not_called()

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_on_owner_gets_bounded_no_store_json(self, identity, home_service):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        resolved = SimpleNamespace(user_key="owner-a")
        identity.return_value = resolved
        home_service.get_home.return_value = self.view_model()

        response = self.client.get("/api/v1/owner/home")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["schema_version"], "owner-home.v1")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertLessEqual(len(response.data), MAX_PAYLOAD_BYTES)
        home_service.get_home.assert_called_once_with(resolved)

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_contract_or_database_failure_is_content_free_503(
        self, identity, home_service
    ):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        identity.return_value = SimpleNamespace(user_key="owner-a")
        for error in (
            OwnerHomeContractError("PRIVATE BODY"),
            DatabaseServiceError("PRIVATE SQL DETAIL"),
        ):
            with self.subTest(error=type(error).__name__):
                home_service.get_home.side_effect = error
                response = self.client.get("/api/v1/owner/home")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json(), {"error": "unavailable"})
                self.assertNotIn(b"PRIVATE", response.data)

    def test_backend_slice_does_not_change_existing_app_render(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        app.config["PEERSLATE_DEV_USER_KEY"] = "existing-owner"
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True

        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"My PeerSlate", response.data)
        self.assertNotIn(b"owner-home.v1", response.data)

    def test_owner_home_flag_defaults_off(self):
        self.assertIs(app.config.get("PEERSLATE_OWNER_HOME_ENABLED"), False)


if __name__ == "__main__":
    unittest.main()
