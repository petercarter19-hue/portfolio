"""HTTP-edge security controls.

These cover the boundary between the public internet and the application:
who a request is attributed to for rate limiting, whether an off-site caller
can reach a paid AI endpoint or a member's private write, and whether a
private response may be stored by a cache. The data layer has its own
allowlist and isolation tests; this file is only about the edge.
"""

import base64
import json
import unittest
from unittest.mock import patch

from app import app, _address_without_port, _client_rate_limit_key


CAPTURE_KEY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ROW_VERSION_TOKEN = "0000000000000007"
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


def easy_auth_header(subject="edge-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Edge Member"},
            {"typ": "email", "val": "edge@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


class RateLimitClientKeyTests(unittest.TestCase):
    """The AI limits must apply per visitor, not to the Azure edge address."""

    def _key_for(self, forwarded_for):
        headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
        with app.test_request_context("/api/chat", headers=headers):
            return _client_rate_limit_key()

    def test_azure_appends_the_caller_with_a_port_which_is_dropped(self):
        # Keying on address:port would make every request a new client and
        # silently disable the limit, because the source port always changes.
        self.assertEqual(self._key_for("203.0.113.5:39876"), "203.0.113.5")

    def test_a_forged_leading_entry_cannot_displace_the_appended_caller(self):
        # A client may send its own X-Forwarded-For; Azure appends the real
        # address after it, so the rightmost entry is the trustworthy one.
        self.assertEqual(
            self._key_for("198.51.100.9, 203.0.113.5:39876"), "203.0.113.5"
        )

    def test_two_visitors_behind_the_same_edge_get_different_keys(self):
        first = self._key_for("203.0.113.5:1111")
        second = self._key_for("203.0.113.6:2222")
        self.assertNotEqual(first, second)

    def test_ipv6_forms_are_handled(self):
        self.assertEqual(self._key_for("[2001:db8::1]:443"), "2001:db8::1")
        self.assertEqual(self._key_for("2001:db8::1"), "2001:db8::1")

    def test_missing_or_unusable_header_falls_back_to_the_socket_address(self):
        for value in ("", "not-an-address", "  ,  "):
            with self.subTest(value=value):
                self.assertEqual(self._key_for(value), "127.0.0.1")

    def test_address_without_port_leaves_a_bare_ipv6_address_intact(self):
        self.assertEqual(_address_without_port("2001:db8::1"), "2001:db8::1")
        self.assertEqual(_address_without_port("203.0.113.5"), "203.0.113.5")


class ChatOriginTests(unittest.TestCase):
    """/api/chat is public, but must not be callable from another origin."""

    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(TESTING=self.original_testing)

    @patch("app.client.messages.create")
    def test_cross_site_fetch_is_refused_before_any_model_call(self, create):
        response = self.client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    @patch("app.client.messages.create")
    def test_foreign_origin_is_refused_before_any_model_call(self, create):
        response = self.client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Origin": "https://attacker.example"},
        )

        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    @patch("app.client.messages.create")
    def test_same_origin_request_still_reaches_the_model(self, create):
        create.return_value.content = [type("Block", (), {"text": "An answer."})()]

        response = self.client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"},
        )

        self.assertEqual(response.status_code, 200)
        create.assert_called_once()


class OwnerWriteOriginTests(unittest.TestCase):
    """Owner writes must prove same origin, including no-JS form posts."""

    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_AUTH_ISSUER": app.config.get("PEERSLATE_AUTH_ISSUER"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_AUTH_ISSUER=None,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(**self.original_config)

    @patch("identity.database_service.first_row")
    def test_write_without_any_same_origin_signal_is_refused(self, first_row):
        # A browser always sends Origin and/or Sec-Fetch-Site on a form post.
        # A caller that supplies neither is not treated as trusted: allowing it
        # let a cross-site post reach POST /app/capture, which needs no
        # unguessable token.
        response = self.client.post(
            "/app/capture",
            data={"body": "Written from nowhere"},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 403)
        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_lifecycle_write_without_a_signal_is_refused_before_identity(
        self, first_row
    ):
        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/archive",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 403)
        first_row.assert_not_called()

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_either_signal_alone_is_accepted_for_the_no_js_form_path(
        self, first_row, first_result
    ):
        # Firefox historically omitted Origin on a same-origin form post, and
        # older browsers omit Sec-Fetch-Site, so either signal alone must stay
        # sufficient or the documented no-JavaScript form path would break.
        # Reaching identity resolution proves the origin gate was passed.
        first_row.return_value = {
            "account_key": "edge-owner",
            "user_key": "edge-owner",
            "display_name": "Edge Member",
            "email": "edge@example.com",
        }
        first_result.return_value = []

        for signal in ({"Sec-Fetch-Site": "same-origin"}, {"Origin": "http://localhost"}):
            with self.subTest(signal=sorted(signal)):
                first_row.reset_mock()

                response = self.client.post(
                    "/app/capture",
                    data={"body": "From a real form"},
                    headers={**easy_auth_header(), **signal},
                )

                self.assertNotEqual(response.status_code, 403)
                self.assertTrue(first_row.called)

    def test_read_only_get_is_unaffected_by_the_write_gate(self):
        # The gate guards state changes only; a read must not be refused for
        # lacking a write signal.
        response = self.client.get("/app/capture")

        self.assertNotEqual(response.status_code, 403)


class AuthIssuerTests(unittest.TestCase):
    """A configured expected issuer must be enforced, not merely defaulted."""

    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_AUTH_ISSUER": app.config.get("PEERSLATE_AUTH_ISSUER"),
        }
        app.config.update(TESTING=True, PEERSLATE_TRUST_EASYAUTH_HEADERS=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(**self.original_config)

    @patch("identity.database_service.first_row")
    def test_foreign_issuer_is_refused_before_any_account_upsert(self, first_row):
        app.config["PEERSLATE_AUTH_ISSUER"] = "https://example.ciamlogin.com/example/v2.0"

        response = self.client.get(
            "/auth/session",
            # A principal minted by a different issuer entirely.
            headers=self._principal("https://attacker.example/v2.0"),
        )

        self.assertEqual(response.get_json()["signed_in"], False)
        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_matching_issuer_is_accepted_ignoring_a_trailing_slash(self, first_row):
        app.config["PEERSLATE_AUTH_ISSUER"] = "https://example.ciamlogin.com/example/v2.0"
        first_row.return_value = {
            "account_key": "issuer-owner",
            "user_key": "issuer-owner",
            "display_name": "Edge Member",
            "email": "edge@example.com",
        }

        response = self.client.get(
            "/auth/session",
            headers=self._principal("https://example.ciamlogin.com/example/v2.0/"),
        )

        self.assertEqual(response.get_json()["signed_in"], True)
        first_row.assert_called_once()

    @patch("identity.database_service.first_row")
    def test_unset_expected_issuer_preserves_existing_behaviour(self, first_row):
        # Production currently leaves this unset; the change must be inert then.
        app.config["PEERSLATE_AUTH_ISSUER"] = None
        first_row.return_value = {
            "account_key": "issuer-owner",
            "user_key": "issuer-owner",
            "display_name": "Edge Member",
            "email": "edge@example.com",
        }

        response = self.client.get(
            "/auth/session", headers=self._principal("https://anything.example/v2.0")
        )

        self.assertEqual(response.get_json()["signed_in"], True)
        first_row.assert_called_once()

    @staticmethod
    def _principal(issuer):
        principal = {
            "auth_typ": "aad",
            "claims": [
                {"typ": "iss", "val": issuer},
                {"typ": "oid", "val": "edge-member"},
                {"typ": "name", "val": "Edge Member"},
                {"typ": "email", "val": "edge@example.com"},
            ],
        }
        encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode(
            "ascii"
        )
        return {"X-MS-CLIENT-PRINCIPAL": encoded}


class CrawlerExclusionTests(unittest.TestCase):
    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(TESTING=self.original_testing)

    def test_private_surfaces_are_excluded_from_crawling(self):
        body = self.client.get("/robots.txt").get_data(as_text=True)

        for path in ("Disallow: /app", "Disallow: /api/"):
            with self.subTest(path=path):
                self.assertIn(path, body)
        # The public site must still be crawlable.
        self.assertIn("Allow: /", body)
        self.assertIn("Sitemap:", body)

    def test_sitemap_lists_no_private_path(self):
        body = self.client.get("/sitemap.xml").get_data(as_text=True)

        for private in ("/app", "/api/", "/owner"):
            with self.subTest(private=private):
                self.assertNotIn(f"<loc>{private}", body)


class ContentSecurityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(TESTING=self.original_testing)

    def test_injection_escalation_directives_are_enforced(self):
        policy = self.client.get("/").headers["Content-Security-Policy"]

        for directive in (
            "base-uri 'self'",
            "object-src 'none'",
            "form-action 'self'",
            "frame-ancestors 'self'",
        ):
            with self.subTest(directive=directive):
                self.assertIn(directive, policy)

    def test_script_and_style_are_not_restricted_yet(self):
        # Enforcing these needs nonces threaded through the templates. Pin the
        # deliberate omission so it is a decision, not an oversight, and so a
        # future change to add them is made knowingly.
        policy = self.client.get("/").headers["Content-Security-Policy"]

        self.assertNotIn("script-src", policy)
        self.assertNotIn("style-src", policy)

    def test_the_policy_is_present_on_a_private_surface_too(self):
        response = self.client.get("/app")

        self.assertIn("Content-Security-Policy", response.headers)


class PrivateResponseCacheTests(unittest.TestCase):
    """Private member responses must not be stored by any cache."""

    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_OWNER_HOME_ENABLED": app.config.get(
                "PEERSLATE_OWNER_HOME_ENABLED"
            ),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="edge-owner",
            PEERSLATE_OWNER_HOME_ENABLED=False,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(**self.original_config)

    def test_flag_off_workspace_is_private_and_not_stored(self):
        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("owner_routes.database_service.first_result")
    @patch("identity.database_service.first_row")
    def test_owner_blueprint_responses_default_to_private_no_store(
        self, first_row, first_result
    ):
        first_row.return_value = {
            "account_key": "edge-owner",
            "user_key": "edge-owner",
            "display_name": "Edge Member",
            "email": "edge@example.com",
        }
        first_result.return_value = []

        response = self.client.get("/app/capture")

        self.assertEqual(
            response.headers["Cache-Control"],
            "private, no-store",
            "an owner surface must never be left on the shared HTML default",
        )

    def test_public_pages_keep_the_ordinary_revalidation_policy(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Cache-Control"], "no-cache, must-revalidate"
        )


if __name__ == "__main__":
    unittest.main()
