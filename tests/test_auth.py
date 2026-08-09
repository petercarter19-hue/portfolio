import base64
import json
import os
import threading
import time
import unittest
from unittest.mock import patch

import auth_routes
from app import _configured_trusted_hosts, app
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
            "PEERSLATE_WORKSHOP_ENABLED": app.config.get(
                "PEERSLATE_WORKSHOP_ENABLED"
            ),
            "PEERSLATE_OWNER_HOME_ENABLED": app.config.get(
                "PEERSLATE_OWNER_HOME_ENABLED"
            ),
            "PEERSLATE_ENFORCE_CANONICAL_HOST": app.config.get(
                "PEERSLATE_ENFORCE_CANONICAL_HOST"
            ),
            "PEERSLATE_CANONICAL_HOST": app.config.get(
                "PEERSLATE_CANONICAL_HOST"
            ),
            "PEERSLATE_AZURE_HOSTNAME": app.config.get(
                "PEERSLATE_AZURE_HOSTNAME"
            ),
            "TRUSTED_HOSTS": app.config.get("TRUSTED_HOSTS"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_AUTH_ISSUER=None,
            PEERSLATE_AUTH_PROVIDER_NAME="aad",
            PEERSLATE_WORKSHOP_ENABLED=False,
            PEERSLATE_OWNER_HOME_ENABLED=False,
            PEERSLATE_ENFORCE_CANONICAL_HOST=False,
            PEERSLATE_CANONICAL_HOST="peerslate.com",
            PEERSLATE_AZURE_HOSTNAME="",
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
        self.assertNotIn(b"auth-state.js", response.data)
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
            "/.auth/login/aad?post_login_redirect_uri=%2Fauth%2Fcomplete%3Freturn_to%3D%2Fapp",
        )

    def test_signed_out_session_response_is_private_no_store(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        response = self.client.get("/auth/session")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"state": "signed_out"})
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
        self.assertEqual(response.get_json(), {"state": "authenticated"})
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        first_row.assert_not_called()

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
            "/.auth/login/aad?post_login_redirect_uri=%2Fauth%2Fcomplete%3Freturn_to%3D%2Fapp",
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
    def test_session_remains_principal_only_when_identity_storage_would_fail(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = DatabaseServiceError("identity storage unavailable")

        response = self.client.get(
            "/auth/session", headers=easy_auth_header("pete-id")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.get_json(), {"state": "authenticated"})
        first_row.assert_not_called()

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

        pete = self.client.get("/app", headers=easy_auth_header("pete", "Pete"))
        danielle = self.client.get(
            "/app", headers=easy_auth_header("danielle", "Danielle")
        )

        self.assertEqual(pete.status_code, 200)
        self.assertEqual(danielle.status_code, 200)
        subjects = [dict(call.args[1])["@AuthSubject"] for call in first_row.call_args_list]
        self.assertEqual(subjects, ["pete", "danielle"])

    def test_malformed_trusted_principal_is_rejected(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.get(
            "/api/dashboard", headers={"X-MS-CLIENT-PRINCIPAL": "not-base64!"}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "invalid_session"})

    def test_session_reports_only_safe_principal_states(self):
        unavailable = self.client.get("/auth/session")
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.get_json(), {"state": "auth_unavailable"})

        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        invalid = self.client.get(
            "/auth/session", headers={"X-MS-CLIENT-PRINCIPAL": "bad"}
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.get_json(), {"state": "invalid_session"})

    @patch("identity.database_service.first_row")
    def test_sign_in_existing_principal_skips_provider_and_database(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.get(
            "/auth/sign-in?return_to=/app/settings",
            headers=easy_auth_header("pete-id"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/complete?return_to=/app/settings")
        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_completion_is_principal_only_and_non_looping_when_missing(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        completed = self.client.get(
            "/auth/complete?return_to=/app/settings",
            headers=easy_auth_header("pete-id"),
        )
        missing = self.client.get("/auth/complete")

        self.assertEqual(completed.status_code, 302)
        self.assertEqual(completed.headers["Location"], "/app/settings")
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"We need to check your account session", missing.data)
        self.assertNotIn(b"/.auth/login", missing.data)
        first_row.assert_not_called()

    def test_return_to_is_restricted_to_bounded_private_app_paths(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        rejected_values = (
            "https://attacker.example/app",
            "//attacker.example/app",
            "/auth/sign-in",
            "/.auth/login/aad",
            "/app#fragment",
            "/app\\outside",
            "/app//outside",
            "/petec/resume",
            "/app\x00outside",
            "/app" + ("x" * 2049),
            # PS-COMMUNITY-AUTH-WALL-001: the Community prefix is bounded the
            # same way the private-app prefix is — hostile shapes stay out.
            "https://attacker.example/the-slate",
            "//attacker.example/the-slate",
            "/the-slate#fragment",
            "/the-slate\\outside",
            "/the-slate//outside",
            "/the-slatex",
            "/the-slate-x",
            "/the-slate\x00posts",
            "/the-slate" + ("x" * 2049),
        )
        default_location = (
            "/.auth/login/aad?post_login_redirect_uri="
            "%2Fauth%2Fcomplete%3Freturn_to%3D%2Fapp"
        )

        for return_to in rejected_values:
            with self.subTest(return_to=return_to):
                response = self.client.get(
                    "/auth/sign-in", query_string={"return_to": return_to}
                )
                self.assertEqual(response.headers["Location"], default_location)

        accepted_values = {
            "/app/settings?tab=account": (
                "/.auth/login/aad?post_login_redirect_uri="
                "%2Fauth%2Fcomplete%3Freturn_to%3D%2Fapp%2Fsettings%3Ftab%253Daccount"
            ),
            # PS-COMMUNITY-AUTH-WALL-001: authenticated Community destinations
            # return the member to the exact Feed, post, or contribution.
            "/the-slate": (
                "/.auth/login/aad?post_login_redirect_uri="
                "%2Fauth%2Fcomplete%3Freturn_to%3D%2Fthe-slate"
            ),
            "/the-slate/posts/0f5b2c1a2e3d4c5b6a798877665544332211aabb": (
                "/.auth/login/aad?post_login_redirect_uri="
                "%2Fauth%2Fcomplete%3Freturn_to%3D%2Fthe-slate%2Fposts"
                "%2F0f5b2c1a2e3d4c5b6a798877665544332211aabb"
            ),
        }
        for return_to, expected_location in accepted_values.items():
            with self.subTest(return_to=return_to):
                accepted = self.client.get(
                    "/auth/sign-in", query_string={"return_to": return_to}
                )
                self.assertEqual(accepted.headers["Location"], expected_location)

    @patch("identity.database_service.first_row", return_value=None)
    def test_mapping_failure_uses_generic_private_recovery(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.get("/app", headers=easy_auth_header("pete-id"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"We need to check your account session", response.data)
        self.assertNotIn(b"pete-id", response.data)
        self.assertNotIn(b"/.auth/login", response.data)
        self.assertEqual(response.data.lower().count(b"<main"), 1)
        self.assertEqual(response.data.count(b'id="main-content"'), 1)
        first_row.assert_called_once()

    def test_invalid_principal_never_redirects_to_provider_across_private_routes(self):
        app.config.update(
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_WORKSHOP_ENABLED=True,
            PEERSLATE_OWNER_HOME_ENABLED=True,
        )
        bad_header = {"X-MS-CLIENT-PRINCIPAL": "not-base64"}
        routes = (
            ("/app", False),
            ("/app/settings", False),
            ("/app/workshop", False),
            ("/auth/sign-in", False),
            ("/auth/complete", False),
            ("/api/dashboard", True),
            ("/api/v1/owner/home", True),
        )

        for path, is_json in routes:
            with self.subTest(path=path):
                response = self.client.get(path, headers=bad_header)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                self.assertNotIn("/.auth/login", response.headers.get("Location", ""))
                if is_json:
                    self.assertEqual(response.get_json(), {"error": "invalid_session"})
                else:
                    self.assertIn(b"We need to check your account session", response.data)

    @patch("identity.database_service.first_row")
    def test_public_header_uses_principal_without_database_mapping(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

        response = self.client.get("/", headers=easy_auth_header("pete-id"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-ps-auth-state="authenticated"', response.data)
        first_row.assert_not_called()

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

        self.assertIn(b"easy-auth-callback.js", response.data)
        self.assertIn(b"auth-state.js", response.data)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])
        self.assertEqual(rejected_host.status_code, 400)

    def test_configured_canonical_host_is_also_trusted_at_startup(self):
        with patch.dict(
            os.environ,
            {"PEERSLATE_CANONICAL_HOST": "app.example.test"},
            clear=False,
        ):
            trusted_hosts = _configured_trusted_hosts()

        self.assertIn("app.example.test", trusted_hosts)
        self.assertIn("www.app.example.test", trusted_hosts)

    def test_opt_in_canonical_host_enforcement_is_fixed_target_and_body_safe(self):
        azure_host = "peerslate-prod.azurewebsites.net"
        app.config.update(
            PEERSLATE_ENFORCE_CANONICAL_HOST=True,
            PEERSLATE_CANONICAL_HOST="peerslate.com",
            PEERSLATE_AZURE_HOSTNAME=azure_host,
            TRUSTED_HOSTS=[*self.original_config["TRUSTED_HOSTS"], azure_host],
        )

        www = self.client.get("/app?next=one", base_url="https://www.peerslate.com")
        azure = self.client.get(
            "/auth/sign-in?return_to=/app", base_url=f"https://{azure_host}"
        )
        pete_private = self.client.get(
            "/app/settings?tab=account", base_url="https://pete.peerslate.com"
        )
        health = self.client.get("/healthz", base_url=f"https://{azure_host}")
        unsafe = self.client.post("/auth/sign-out", base_url="https://www.peerslate.com")
        forged_forwarded_host = self.client.get(
            "/app", base_url=f"https://{azure_host}",
            headers={"X-Forwarded-Host": "peerslate.com"},
        )
        unknown = self.client.get("/", base_url="https://evil.peerslate.com")

        self.assertEqual(www.status_code, 308)
        self.assertEqual(www.headers["Location"], "https://peerslate.com/app?next=one")
        self.assertEqual(azure.status_code, 308)
        self.assertEqual(
            azure.headers["Location"],
            "https://peerslate.com/auth/sign-in?return_to=/app",
        )
        self.assertEqual(pete_private.status_code, 308)
        self.assertEqual(
            pete_private.headers["Location"],
            "https://peerslate.com/app/settings?tab=account",
        )
        self.assertEqual(health.status_code, 200)
        self.assertEqual(unsafe.status_code, 400)
        self.assertNotIn("Location", unsafe.headers)
        self.assertEqual(forged_forwarded_host.status_code, 308)
        self.assertEqual(forged_forwarded_host.headers["Location"], "https://peerslate.com/app")
        self.assertEqual(unknown.status_code, 400)


if __name__ == "__main__":
    unittest.main()
