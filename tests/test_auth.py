import base64
import json
import threading
import time
import unittest
from unittest.mock import patch

import auth_routes
from app import app
from services.database_service import DatabaseServiceError


def easy_auth_header(subject, display_name="Example Member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": display_name},
            {"typ": "email", "val": f"{subject}@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


class AuthenticationFlowTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_AUTH_ISSUER": app.config.get("PEERSLATE_AUTH_ISSUER"),
            "PEERSLATE_AUTH_PROVIDER_NAME": app.config.get(
                "PEERSLATE_AUTH_PROVIDER_NAME"
            ),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_AUTH_ISSUER=None,
            PEERSLATE_AUTH_PROVIDER_NAME="aad",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    def test_anonymous_owner_workspace_redirects_to_sign_in(self):
        response = self.client.get("/app")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/sign-in?return_to=/app")

    def test_sign_in_is_honest_until_easy_auth_is_configured(self):
        response = self.client.get("/auth/sign-in")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Sign in is not configured yet", response.data)
        # The asset is versioned automatically by content hash now, so match
        # the stable path-plus-?v= prefix rather than a hand-typed token.
        callback_script = b"/static/js/easy-auth-callback.js?v="
        self.assertIn(callback_script, response.data)
        self.assertLess(
            response.data.index(callback_script),
            response.data.index(b"REAL TABLETS GET THE DESKTOP LAYOUT"),
        )

    def test_sign_in_uses_easy_auth_and_rejects_external_return_urls(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.get(
            "/auth/sign-in?return_to=https://attacker.example/steal"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/.auth/login/aad?post_login_redirect_uri=%2Fapp",
        )

    def test_signed_out_session_response_is_private_no_store(self):
        response = self.client.get("/auth/session")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["signed_in"], False)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("identity.database_service.first_row")
    def test_signed_in_session_response_is_private_no_store(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Pete Example",
            "email": "pete@example.com",
        }

        response = self.client.get(
            "/auth/session", headers=easy_auth_header("pete-id")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["signed_in"], True)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("identity.database_service.first_row")
    def test_signed_in_member_can_open_private_owner_workspace(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = {
            "account_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "user_key": "45ab728a-44bc-4f80-a79f-d010e04d5453",
            "display_name": "Pete Example",
            "email": "pete@example.com",
        }

        response = self.client.get("/app", headers=easy_auth_header("pete-id"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Private owner workspace", response.data)
        self.assertIn(b"Welcome, Pete Example", response.data)
        self.assertIn(b"Default audience", response.data)
        parameters = first_row.call_args.args[1]
        self.assertIn(
            ("@AuthIssuer", "https://example.ciamlogin.com/example/v2.0"),
            parameters,
        )

    @patch("identity.database_service.first_row")
    def test_signed_in_member_sees_truthful_workspace_wakeup_state(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = DatabaseServiceError("identity storage unavailable")

        response = self.client.get("/app", headers=easy_auth_header("pete-id"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"Your private workspace is waking up", response.data)
        self.assertIn(b"You are signed in", response.data)
        self.assertIn(b'href="/app">Check now</a>', response.data)
        self.assertIn(b">Workspace waking</a>", response.data)
        self.assertNotIn(b"Sign in is not configured", response.data)
        self.assertNotIn(b">Sign In</a>", response.data)
        first_row.assert_called_once()

    @patch("identity.database_service.first_row")
    def test_identity_waking_page_auto_retries_within_a_bounded_window(
        self, first_row
    ):
        """PS-SIGNIN-EXPERIENCE-001 item 2.2.

        The copy was already honest, but recovery was manual: a member had to
        keep pressing a link through the whole 30-60 second serverless resume.
        """
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = DatabaseServiceError("identity storage unavailable")

        body = self.client.get("/app", headers=easy_auth_header("pete-id")).data

        self.assertIn(b'data-ps-waking-retry-url="/app"', body)
        self.assertIn(b'data-ps-waking-budget-seconds="90"', body)
        self.assertIn(b"js/workspace-waking.js", body)
        # Polite announcement, a real stop control, and a server-rendered
        # manual route so the page still works with JavaScript disabled.
        self.assertIn(b'role="status" aria-live="polite"', body)
        self.assertIn(b"data-ps-waking-stop", body)
        self.assertIn(b"Stop checking automatically", body)
        self.assertIn(b'href="/">Return home</a>', body)
        # Honest about member content and about how long this normally takes.
        self.assertIn(b"under a minute", body)
        self.assertIn(b"Nothing was published, shared, deleted, or changed.", body)

    def _drain_prewarm(self):
        """Reset both module-level pre-warm guards and outwait any thread.

        Every pre-warm test must call this first and last. unittest orders
        these tests alphabetically (the pipeline runs them that way), so the
        rate-limit test's worker thread can still be marked in flight when the
        next test starts; pipeline 330 failed exactly there, and an escaped
        thread that outlives its patch would also hit the real connector.
        """
        deadline = time.monotonic() + 10
        while auth_routes._prewarm_in_flight and time.monotonic() < deadline:
            time.sleep(0.02)
        with auth_routes._prewarm_lock:
            auth_routes._prewarm_in_flight = False
            auth_routes._prewarm_last_started = None

    def test_sign_in_prewarm_never_blocks_or_fails_the_redirect(self):
        """PS-SIGNIN-EXPERIENCE-001 item 2.3.

        The pre-warm exists only to start a paused Azure SQL serverless
        database resuming while the member is on the Microsoft page. A failure
        inside it must be invisible to sign-in.
        """
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        app.config["PEERSLATE_SIGN_IN_PREWARM_ENABLED"] = True
        self._drain_prewarm()
        finished = threading.Event()

        def exploding_connection():
            try:
                raise RuntimeError("connection refused")
            finally:
                finished.set()

        try:
            with patch("auth_routes.get_connection", side_effect=exploding_connection):
                response = self.client.get("/auth/sign-in")
                self.assertTrue(
                    finished.wait(timeout=10), "pre-warm thread never ran"
                )
                self._drain_prewarm()
        finally:
            app.config.pop("PEERSLATE_SIGN_IN_PREWARM_ENABLED", None)
            self._drain_prewarm()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/.auth/login/aad?post_login_redirect_uri=%2Fapp",
        )

    def test_sign_in_prewarm_is_rate_limited_and_runs_off_the_request_thread(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        app.config["PEERSLATE_SIGN_IN_PREWARM_ENABLED"] = True
        self._drain_prewarm()
        release = threading.Event()
        started = threading.Event()
        opened = []

        def slow_connection():
            opened.append(1)
            started.set()
            # Blocking here would hang the response if the pre-warm were
            # running on the request thread.
            release.wait(timeout=10)
            raise RuntimeError("still unreachable")

        try:
            with patch("auth_routes.get_connection", side_effect=slow_connection):
                first = self.client.get("/auth/sign-in")
                self.assertTrue(started.wait(timeout=10))
                second = self.client.get("/auth/sign-in")
                third = self.client.get("/auth/sign-in")
                release.set()
                # The worker must finish while its patched connector is still
                # in place; leaving the context with the thread alive is how
                # it escapes to the real connector.
                self._drain_prewarm()
        finally:
            release.set()
            app.config.pop("PEERSLATE_SIGN_IN_PREWARM_ENABLED", None)
            self._drain_prewarm()

        # A public unauthenticated endpoint may not let a caller open a
        # database connection per request.
        self.assertEqual(len(opened), 1)
        for response in (first, second, third):
            self.assertEqual(response.status_code, 302)

    def test_sign_in_prewarm_does_not_run_when_authentication_is_disabled(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = False
        app.config["PEERSLATE_SIGN_IN_PREWARM_ENABLED"] = True
        self._drain_prewarm()
        opened = []

        try:
            with patch(
                "auth_routes.get_connection", side_effect=lambda: opened.append(1)
            ):
                response = self.client.get("/auth/sign-in")
        finally:
            app.config.pop("PEERSLATE_SIGN_IN_PREWARM_ENABLED", None)
            self._drain_prewarm()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(opened, [])

    def test_sign_in_prewarm_is_off_under_testing_unless_a_test_opts_in(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        self._drain_prewarm()
        opened = []

        try:
            with patch(
                "auth_routes.get_connection", side_effect=lambda: opened.append(1)
            ):
                response = self.client.get("/auth/sign-in")
        finally:
            self._drain_prewarm()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(opened, [])

    @patch("identity.database_service.first_row")
    def test_session_reports_authenticated_workspace_unavailable(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = DatabaseServiceError("identity storage unavailable")

        response = self.client.get(
            "/auth/session", headers=easy_auth_header("pete-id")
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(
            response.get_json(),
            {
                "signed_in": True,
                "available": False,
                "state": "workspace_unavailable",
            },
        )
        first_row.assert_called_once()

    @patch("identity.database_service.first_row")
    def test_two_provider_subjects_resolve_to_two_internal_accounts(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        def user_for_subject(_procedure_name, parameters):
            subject = dict(parameters)["@AuthSubject"]
            return {
                "account_key": f"account-{subject}",
                "user_key": f"user-{subject}",
                "display_name": subject,
                "email": f"{subject}@example.com",
            }

        first_row.side_effect = user_for_subject

        pete = self.client.get(
            "/auth/session", headers=easy_auth_header("pete", "Pete")
        ).get_json()
        danielle = self.client.get(
            "/auth/session", headers=easy_auth_header("danielle", "Danielle")
        ).get_json()

        self.assertTrue(pete["signed_in"])
        self.assertTrue(danielle["signed_in"])
        self.assertEqual(pete["display_name"], "pete")
        self.assertEqual(danielle["display_name"], "danielle")
        subjects = [dict(call.args[1])["@AuthSubject"] for call in first_row.call_args_list]
        self.assertEqual(subjects, ["pete", "danielle"])

    def test_malformed_trusted_principal_is_rejected(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.get(
            "/api/dashboard", headers={"X-MS-CLIENT-PRINCIPAL": "not-base64!"}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.get_json()["message"], "The authentication identity is invalid."
        )

    def test_sign_out_rejects_cross_site_posts(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        denied = self.client.post(
            "/auth/sign-out", headers={"Origin": "https://attacker.example"}
        )
        allowed = self.client.post(
            "/auth/sign-out", headers={"Origin": "http://localhost"}
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 302)
        self.assertEqual(
            allowed.headers["Location"],
            "/.auth/logout?post_logout_redirect_uri=%2F",
        )

    def test_security_headers_and_trusted_hosts_are_active(self):
        response = self.client.get("/", base_url="https://peerslate.com")
        rejected_host = self.client.get("/", base_url="https://attacker.example")

        self.assertNotIn(b"easy-auth-callback.js", response.data)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])
        self.assertEqual(rejected_host.status_code, 400)


if __name__ == "__main__":
    unittest.main()
