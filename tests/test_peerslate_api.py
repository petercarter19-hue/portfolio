import base64
import json
import os
import unittest
from unittest.mock import patch

from app import app
from services.database_service import DatabaseServiceError
from services.living_resume_editor_service import (
    LivingResumeEditorConflictError,
    LivingResumeEditorUnavailableError,
    LivingResumeEditorValidationError,
)


class PeerSlateApiTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_ENABLE_DB_TEST_ROUTES": app.config.get("PEERSLATE_ENABLE_DB_TEST_ROUTES"),
            "PEERSLATE_DATABASE_UI_ENABLED": app.config.get("PEERSLATE_DATABASE_UI_ENABLED"),
            "PEERSLATE_LIVING_RESUME_DB_ENABLED": app.config.get("PEERSLATE_LIVING_RESUME_DB_ENABLED"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS"),
            "PEERSLATE_RESUME_EDITOR_ENABLED": app.config.get("PEERSLATE_RESUME_EDITOR_ENABLED"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="test-user-1",
            PEERSLATE_ENABLE_DB_TEST_ROUTES=False,
            PEERSLATE_DATABASE_UI_ENABLED=False,
            PEERSLATE_LIVING_RESUME_DB_ENABLED=False,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_EDITOR_ENABLED=False,
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
        break_feed = self.client.get("/the-slate/break")

        self.assertIn(b'data-board-api="true"', database_board.data)
        self.assertIn(b'Saved privately', database_board.data)
        # PS-COMMUNITY-AUTH-WALL-001: the Daily Slate and Break pages are
        # retired — their addresses forward to the one real Community and
        # serve no database-UI or break-API markup in any flag state.
        self.assertEqual(daily_slate.status_code, 302)
        self.assertTrue(daily_slate.headers["Location"].endswith("/the-slate"))
        self.assertNotIn(b'data-database-ui=', daily_slate.data)
        self.assertEqual(break_feed.status_code, 302)
        self.assertNotIn(b'data-break-api=', break_feed.data)

    def test_living_resume_database_routes_are_feature_flagged_off(self):
        owner = self.client.get("/api/living-resume/me")
        command = self.client.post(
            "/api/living-resume/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={},
        )
        self.assertEqual(owner.status_code, 404)
        self.assertEqual(command.status_code, 404)
        self.assertEqual(owner.headers["Cache-Control"], "private, no-store")
        self.assertEqual(command.headers["Cache-Control"], "private, no-store")
        self.assertEqual(
            self.client.get("/api/public/profiles/example/living-resume").status_code,
            404,
        )

    @patch("identity.database_service.first_row")
    def test_azure_hosting_does_not_automatically_trust_identity_headers(
        self, first_row
    ):
        app.config.update(
            TESTING=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
        )
        principal = {
            "auth_typ": "aad",
            "claims": [{"typ": "oid", "val": "untrusted-member"}],
        }
        encoded = base64.b64encode(json.dumps(principal).encode()).decode()

        with patch.dict(os.environ, {"WEBSITE_INSTANCE_ID": "hosted-instance"}):
            response = self.client.get(
                "/api/dashboard", headers={"X-MS-CLIENT-PRINCIPAL": encoded}
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["message"], "Sign in is required.")
        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_testing_mode_does_not_automatically_trust_identity_headers(
        self, first_row
    ):
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
        )
        principal = {
            "auth_typ": "aad",
            "claims": [{"typ": "oid", "val": "untrusted-test-member"}],
        }
        encoded = base64.b64encode(json.dumps(principal).encode()).decode()

        response = self.client.get(
            "/api/dashboard", headers={"X-MS-CLIENT-PRINCIPAL": encoded}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["message"], "Sign in is required.")
        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_truthy_string_does_not_enable_identity_header_trust(self, first_row):
        app.config.update(
            TESTING=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS="true",
        )
        principal = {
            "auth_typ": "aad",
            "claims": [{"typ": "oid", "val": "untrusted-string-member"}],
        }
        encoded = base64.b64encode(json.dumps(principal).encode()).decode()

        response = self.client.get(
            "/api/dashboard", headers={"X-MS-CLIENT-PRINCIPAL": encoded}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["message"], "Sign in is required.")
        first_row.assert_not_called()

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
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("peerslate_api.living_resume_editor_service.get_editor")
    def test_owner_editor_view_uses_server_identity_and_is_never_cached(self, get_editor):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        get_editor.return_value = {"profile": {"profile_key": "private"}, "roles": []}

        response = self.client.get(
            "/api/living-resume/me?view=editor&user_key=someone-else"
        )

        self.assertEqual(response.status_code, 200)
        get_editor.assert_called_once_with("test-user-1")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    @patch("peerslate_api.living_resume_editor_service.get_editor")
    def test_owner_editor_view_advertises_draft_overlay_only_when_flag_on(self, get_editor):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        get_editor.return_value = {
            "profile": {"profile_key": "private"},
            "roles": [],
            "capabilities": {"commands": ["create_role"]},
        }

        off = self.client.get("/api/living-resume/me?view=editor")
        self.assertEqual(off.status_code, 200)
        self.assertNotIn("draft_overlay_path", off.get_json()["editor"].get("capabilities", {}))

        app.config["PEERSLATE_RESUME_EDITOR_ENABLED"] = True
        on = self.client.get("/api/living-resume/me?view=editor")
        capabilities = on.get_json()["editor"]["capabilities"]
        self.assertTrue(capabilities["draft_overlay"])
        self.assertEqual(capabilities["draft_overlay_path"], "/api/resume-drafts/me")
        self.assertEqual(capabilities["draft_editor_path"], "/app/resume")

    @patch("peerslate_api.living_resume_editor_service.commit")
    def test_owner_command_uses_server_identity_and_same_origin(self, commit):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        commit.return_value = {
            "receipt": {"outcome": "created", "replayed": False},
            "current": {"record_key": "private"},
        }
        body = {"command_id": "browser-value", "user_key": "someone-else"}

        response = self.client.post(
            "/api/living-resume/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json=body,
        )

        self.assertEqual(response.status_code, 201)
        commit.assert_called_once_with("test-user-1", body)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("peerslate_api.living_resume_editor_service.commit")
    def test_owner_command_replay_is_200(self, commit):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        commit.return_value = {
            "receipt": {"outcome": "created", "replayed": True},
            "current": {"record_key": "private"},
        }
        response = self.client.post(
            "/api/living-resume/me/commands",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={},
        )
        self.assertEqual(response.status_code, 200)

    @patch("peerslate_api.living_resume_editor_service.commit")
    def test_owner_command_returns_typed_safe_errors_and_current_conflict(self, commit):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        cases = (
            (LivingResumeEditorValidationError("Bad command."), 400, "invalid"),
            (
                LivingResumeEditorConflictError(
                    "Changed.", code="changed", current={"row_version": "next"}
                ),
                409,
                "changed",
            ),
            (LivingResumeEditorUnavailableError(), 503, "unavailable"),
        )
        for error, status, code in cases:
            with self.subTest(code=code):
                commit.side_effect = error
                response = self.client.post(
                    "/api/living-resume/me/commands",
                    headers={"X-PeerSlate-Request": "same-origin"},
                    json={},
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.get_json()["code"], code)
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                self.assertNotIn("SQL", response.get_data(as_text=True))
        self.assertEqual(response.get_json().get("current"), None)

    def test_owner_command_without_same_origin_is_rejected_and_never_cached(self):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        response = self.client.post("/api/living-resume/me/commands", json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_owner_command_malformed_types_unicode_and_urls_return_typed_400(self):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        base = {
            "command_id": "00000000-0000-4000-8000-000000000001",
            "type": "create_role",
            "record_key": "00000000-0000-4000-8000-000000000002",
            "parent_key": None,
            "expected_version": None,
            "values": {
                "role_title": "Engineer",
                "employer_name": "PeerSlate",
                "location_text": None,
                "summary": None,
                "start_date": None,
                "end_date": None,
                "date_precision": "unknown",
                "employment_type": None,
                "current_role": False,
            },
        }
        credential = {
            **base,
            "type": "create_credential",
            "values": {
                "name": "Azure Fundamentals",
                "issuer": "Microsoft",
                "identifier": None,
                "issue_date": "2026-01-02",
                "expiration_date": None,
                "verification_url": "http://[",
                "completion_status": "completed",
            },
        }
        cases = (
            {**base, "type": []},
            {**base, "values": {**base["values"], "summary": "bad\ud800text"}},
            credential,
        )
        for body in cases:
            with self.subTest(command_type=body["type"]):
                response = self.client.post(
                    "/api/living-resume/me/commands",
                    headers={"X-PeerSlate-Request": "same-origin"},
                    json=body,
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["code"], "invalid")
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("peerslate_api.database_service.execute_procedure")
    def test_public_living_resume_passes_only_clean_slug(self, execute):
        app.config["PEERSLATE_LIVING_RESUME_DB_ENABLED"] = True
        execute.return_value = [[{"profile_slug": "petec"}]] + [[] for _ in range(5)]

        response = self.client.get("/api/public/profiles/Petec/living-resume")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            execute.call_args.args[1],
            [("@ProfileSlug", "petec")],
        )

    @patch("identity.database_service.first_row")
    @patch("peerslate_api.database_service.execute_procedure")
    def test_easy_auth_subject_is_upserted_and_used_for_tenant_scope(
        self, execute, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        principal = {
            "auth_typ": "aad",
            "claims": [
                {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0"},
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
        self.assertIn(
            ("@AuthIssuer", "https://example.ciamlogin.com/example/v2.0"),
            upsert_parameters,
        )
        self.assertIn(("@AuthSubject", "member-object-id"), upsert_parameters)
        dashboard_parameters = execute.call_args.args[1]
        self.assertIn(("@UserKey", "aad:member-object-id"), dashboard_parameters)


if __name__ == "__main__":
    unittest.main()
