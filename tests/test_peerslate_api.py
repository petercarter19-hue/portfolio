import base64
import json
import unittest
from unittest.mock import patch

from app import app
from services.database_service import DatabaseServiceError


class PeerSlateApiTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_ENABLE_DB_TEST_ROUTES": app.config.get("PEERSLATE_ENABLE_DB_TEST_ROUTES"),
            "PEERSLATE_DATABASE_UI_ENABLED": app.config.get("PEERSLATE_DATABASE_UI_ENABLED"),
            "PEERSLATE_LIVING_RESUME_DB_ENABLED": app.config.get("PEERSLATE_LIVING_RESUME_DB_ENABLED"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="test-user-1",
            PEERSLATE_ENABLE_DB_TEST_ROUTES=False,
            PEERSLATE_DATABASE_UI_ENABLED=False,
            PEERSLATE_LIVING_RESUME_DB_ENABLED=False,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    def test_dashboard_requires_identity(self):
        app.config.update(
            TESTING=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )

        response = self.client.get("/api/dashboard")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.get_json()["success"])

    @patch("peerslate_api.database_service.execute_procedure")
    def test_dashboard_uses_server_side_identity_and_named_sections(self, execute):
        execute.return_value = [[{"user_key": "test-user-1"}]] + [[] for _ in range(7)]

        response = self.client.get("/api/dashboard?user_key=someone-else")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["dashboard"]["user_summary"][0]["user_key"], "test-user-1")
        parameters = execute.call_args.args[1]
        self.assertIn(("@UserKey", "test-user-1"), parameters)
        self.assertNotIn(("@UserKey", "someone-else"), parameters)

    def test_write_routes_require_same_origin_header(self):
        response = self.client.post(
            "/api/slate-items",
            json={
                "space_name": "Career Slate",
                "space_type": "career",
                "item_type": "goal",
                "title": "Test item",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_write_routes_reject_cross_origin_requests(self):
        response = self.client.post(
            "/api/slate-items",
            headers={
                "X-PeerSlate-Request": "same-origin",
                "Origin": "https://attacker.example",
            },
            json={
                "space_name": "Career Slate",
                "space_type": "career",
                "item_type": "goal",
                "title": "Test item",
            },
        )

        self.assertEqual(response.status_code, 403)

    @patch("peerslate_api.database_service.last_result")
    def test_add_slate_item_validates_and_scopes_user(self, last_result):
        last_result.return_value = [{"id": 42, "title": "Study for PMP"}]

        response = self.client.post(
            "/api/slate-items",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "space_name": "Career Slate",
                "space_type": "career",
                "item_type": "goal",
                "title": "Study for PMP",
                "user_key": "someone-else",
            },
        )

        self.assertEqual(response.status_code, 201)
        parameters = last_result.call_args.args[1]
        self.assertIn(("@UserKey", "test-user-1"), parameters)
        self.assertNotIn(("@UserKey", "someone-else"), parameters)

    @patch("peerslate_api.database_service.first_result")
    def test_database_errors_do_not_expose_private_details(self, first_result):
        first_result.side_effect = DatabaseServiceError(
            "password=secret; internal SQL details"
        )

        with self.assertLogs(app.logger, level="ERROR") as captured_logs:
            response = self.client.get("/api/feed/break")

        self.assertEqual(response.status_code, 503)
        body = response.get_data(as_text=True)
        self.assertNotIn("secret", body)
        self.assertNotIn("internal SQL", body)
        logs = "\n".join(captured_logs.output)
        self.assertNotIn("secret", logs)
        self.assertNotIn("internal SQL", logs)

    def test_temporary_database_routes_are_disabled_by_default(self):
        self.assertEqual(self.client.get("/api/db-test").status_code, 404)
        self.assertEqual(self.client.get("/api/dashboard/test").status_code, 404)

    def test_database_ui_is_off_by_default_and_private_when_enabled(self):
        board_preview = self.client.get("/slate-board")
        self.assertIn(b'data-board-api="false"', board_preview.data)
        self.assertIn(b'stores changes only in this browser', board_preview.data)

        app.config["PEERSLATE_DATABASE_UI_ENABLED"] = True
        database_board = self.client.get("/slate-board")
        daily_slate = self.client.get("/the-slate/daily")

        self.assertIn(b'data-board-api="true"', database_board.data)
        self.assertIn(b'Saved privately', database_board.data)
        self.assertEqual(daily_slate.status_code, 302)
        self.assertTrue(daily_slate.location.endswith('/petec/slate-board#daily-check-in'))

    def test_living_resume_database_routes_are_feature_flagged_off(self):
        self.assertEqual(self.client.get("/api/living-resume/me").status_code, 404)
        self.assertEqual(
            self.client.get("/api/public/profiles/example/living-resume").status_code,
            404,
        )

    @patch("peerslate_api.database_service.execute_procedure")
    def test_owner_living_resume_uses_server_identity_and_named_contract(self, execute):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        execute.return_value = [[{"profile_slug": "example"}]] + [[] for _ in range(5)]

        response = self.client.get("/api/living-resume/me?user_key=someone-else")

        self.assertEqual(response.status_code, 200)
        parameters = execute.call_args.args[1]
        self.assertEqual(parameters, [("@UserKey", "test-user-1")])
        payload = response.get_json()["living_resume"]
        self.assertEqual(
            set(payload),
            {"profile", "chapters", "achievements", "skills", "skill_proofs", "timeline"},
        )

    @patch("peerslate_api.database_service.execute_procedure")
    def test_public_living_resume_passes_only_clean_slug(self, execute):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        execute.return_value = [[{"profile_slug": "sample-member"}]] + [[] for _ in range(5)]

        response = self.client.get("/api/public/profiles/Sample-Member/living-resume")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            execute.call_args.args[1],
            [("@ProfileSlug", "sample-member")],
        )

    @patch("identity.database_service.first_row")
    @patch("peerslate_api.database_service.execute_procedure")
    def test_easy_auth_subject_is_upserted_and_used_for_tenant_scope(
        self, execute, first_row
    ):
        principal = {
            "auth_typ": "aad",
            "claims": [
                {"typ": "oid", "val": "member-object-id"},
                {"typ": "email", "val": "member@example.com"},
                {"typ": "name", "val": "Example Member"},
            ],
        }
        encoded = base64.b64encode(json.dumps(principal).encode()).decode()
        first_row.return_value = {
            "user_key": "aad:member-object-id",
            "email": "member@example.com",
            "display_name": "Example Member",
        }
        execute.return_value = [[] for _ in range(8)]

        response = self.client.get(
            "/api/dashboard", headers={"X-MS-CLIENT-PRINCIPAL": encoded}
        )

        self.assertEqual(response.status_code, 200)
        upsert_parameters = first_row.call_args.args[1]
        self.assertIn(("@AuthSubject", "member-object-id"), upsert_parameters)
        dashboard_parameters = execute.call_args.args[1]
        self.assertIn(("@UserKey", "aad:member-object-id"), dashboard_parameters)


if __name__ == "__main__":
    unittest.main()
