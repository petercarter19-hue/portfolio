"""HTTP-edge security controls.

These cover the boundary between the public internet and the application:
who a request is attributed to for rate limiting, whether an off-site caller
can reach a paid AI endpoint or a member's private write, and whether a
private response may be stored by a cache. The data layer has its own
allowlist and isolation tests; this file is only about the edge.
"""

import base64
import gzip
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from flask import Response, session

from app import (
    _STATIC_GZIP_CACHE,
    _STATIC_VERSION_CACHE,
    app,
    _address_without_port,
    _canonical_static_file,
    _client_rate_limit_key,
    _compress_public_text_response,
    _static_file_version,
)


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
    def test_missing_or_blank_issuer_is_refused_before_any_account_upsert(
        self, first_row
    ):
        app.config["PEERSLATE_AUTH_ISSUER"] = "https://example.ciamlogin.com/example/v2.0"

        for issuer in (None, "   "):
            with self.subTest(issuer=issuer):
                response = self.client.get(
                    "/auth/session",
                    headers=self._principal(issuer),
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
        # Covers a deployment that leaves the expected issuer unset.
        #
        # Do not read this as a statement about production. The peerslate-pete
        # App Service DOES define PEERSLATE_AUTH_ISSUER, so the enforcement
        # above is live there, not inert. Until this change, a wrong value was
        # undetectable, because the setting was only a fallback used when the
        # principal carried no issuer claim. Enforcement makes it load-bearing:
        # if the configured value does not equal the iss claim Easy Auth
        # presents (compared case-insensitively, ignoring a trailing slash),
        # every member is refused sign-in. Confirm the two match before
        # relying on this path in production.
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
        claims = [
            {"typ": "oid", "val": "edge-member"},
            {"typ": "name", "val": "Edge Member"},
            {"typ": "email", "val": "edge@example.com"},
        ]
        if issuer is not None:
            claims.insert(0, {"typ": "iss", "val": issuer})
        principal = {
            "auth_typ": "aad",
            "claims": claims,
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
            "PEERSLATE_DATABASE_UI_ENABLED": app.config.get(
                "PEERSLATE_DATABASE_UI_ENABLED"
            ),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="edge-owner",
            PEERSLATE_OWNER_HOME_ENABLED=False,
            PEERSLATE_DATABASE_UI_ENABLED=False,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(**self.original_config)

    def test_flag_off_workspace_is_private_and_not_stored(self):
        response = self.client.get(
            "/app",
            headers={"Accept-Encoding": "gzip"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertIsNone(response.headers.get("Content-Encoding"))

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

    @patch("peerslate_api.database_service.name_result_sets")
    @patch("peerslate_api.database_service.execute_procedure")
    def test_authenticated_api_responses_default_to_private_no_store(
        self, execute_procedure, name_result_sets
    ):
        execute_procedure.return_value = []
        name_result_sets.return_value = {
            "user_summary": [{"display_name": "Edge Member"}]
        }

        response = self.client.get("/api/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("people_interests_api.people_interests_feed.get_page")
    def test_personalized_public_feed_response_is_private_no_store(self, get_page):
        get_page.return_value = {"items": [], "next_cursor": None}

        response = self.client.get("/api/feed/people-interests")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(get_page.call_args.kwargs["user_key"], "edge-owner")

    def test_identity_personalized_app_page_is_private_no_store(self):
        app.config["PEERSLATE_DATABASE_UI_ENABLED"] = True

        response = self.client.get("/slate-board")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-board-storage-scope="member-', response.data)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_public_pages_keep_the_ordinary_revalidation_policy(self):
        app.config.update(
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Cache-Control"], "no-cache, must-revalidate"
        )


class FeatureFlagConsistencyTests(unittest.TestCase):
    """Two blueprints read the Owner Home flag through their own helper.

    auth_routes gates the /app render and owner_routes gates the
    /api/v1/owner/home contract. The helpers are separate but must agree:
    changing the semantics in one and not the other would split the page
    from its data source, showing a shell with no API behind it or the
    reverse. Assert they stay in lockstep rather than coupling the modules.
    """

    def setUp(self):
        self.original = app.config.get("PEERSLATE_OWNER_HOME_ENABLED")

    def tearDown(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = self.original

    def test_both_owner_home_flag_readers_agree(self):
        import auth_routes
        import owner_routes

        for value in (True, False, None, "true", 1):
            with self.subTest(value=value):
                app.config["PEERSLATE_OWNER_HOME_ENABLED"] = value
                with app.test_request_context("/app"):
                    self.assertEqual(
                        auth_routes._owner_home_enabled(),
                        owner_routes._owner_home_enabled(),
                        f"the two Owner Home flag readers disagree for {value!r}",
                    )


class StaticVersioningTests(unittest.TestCase):
    """Public static assets use exact content URLs and bounded fallback caching."""

    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(TESTING=self.original_testing)

    def test_templates_carry_no_hand_typed_version_tokens(self):
        # The whole point is to remove the manual scheme that had drifted.
        template_root = Path(app.root_path, app.template_folder)
        for path in template_root.rglob("*.html"):
            with self.subTest(template=path.relative_to(template_root)):
                self.assertNotRegex(
                    path.read_text(encoding="utf-8"),
                    r"\}\}\s*\?v=",
                    "url_for static output must not receive a second manual token",
                )

        html = self.client.get("/").get_data(as_text=True)
        for token in re.findall(r"\?v=([^\"'&,\s]+)", html):
            with self.subTest(token=token):
                self.assertRegex(
                    token, r"^[0-9a-f]{12}$",
                    f"non-hash version token {token!r} leaked into a page")

    def test_current_version_is_cached_immutably(self):
        version = _static_file_version("css/style.css")
        response = self.client.get(f"/static/css/style.css?v={version}")

        self.assertEqual(
            response.headers["Cache-Control"],
            "public, max-age=31536000, immutable",
        )
        response.close()

    def test_a_stale_or_wrong_token_is_never_cached_long(self):
        # A visitor must never be pinned to old bytes: only a token that
        # matches the live content hash earns the long cache.
        for token in ("signout-1", "deadbeef0000", ""):
            with self.subTest(token=token):
                url = "/static/css/style.css"
                if token:
                    url += f"?v={token}"
                response = self.client.get(url)
                self.assertNotIn(
                    "immutable", response.headers.get("Cache-Control", ""))
                self.assertEqual(
                    response.headers.get("Cache-Control"),
                    "public, max-age=3600, stale-while-revalidate=86400",
                )
                response.close()

    def test_template_images_are_content_versioned(self):
        version = _static_file_version("images/peerslate-mark.png")
        self.assertRegex(version, r"^[0-9a-f]{12}$")

        html = self.client.get("/").get_data(as_text=True)
        self.assertIn(
            f"/static/images/peerslate-mark.png?v={version}",
            html,
        )

    def test_editing_a_file_changes_its_token(self):
        # Different bytes must produce a different URL, or a cache could serve
        # stale content. Prove the hash actually depends on content.
        a = _static_file_version("css/style.css")
        b = _static_file_version("js/chatbot.js")
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^[0-9a-f]{12}$")

    def test_canonical_equivalent_paths_share_one_static_cache_key(self):
        _STATIC_VERSION_CACHE.clear()
        _STATIC_GZIP_CACHE.clear()
        version = _static_file_version("css/style.css")
        expected = Path(app.static_folder, "css", "style.css").read_bytes()
        aliases = (
            "/static/css/style.css",
            "/static/css/./style.css",
            "/static/css//style.css",
            "/static/css/sub/../style.css",
            "/static/css/%2e/style.css",
            "/static/css/sub/%2e%2e/style.css",
        )

        for alias in aliases:
            with self.subTest(alias=alias):
                response = self.client.get(
                    alias,
                    query_string={"v": version},
                    headers={"Accept-Encoding": "gzip"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers.get("Content-Encoding"),
                    "gzip",
                )
                self.assertEqual(gzip.decompress(response.data), expected)
                response.close()

        self.assertEqual(set(_STATIC_VERSION_CACHE), {"css/style.css"})
        self.assertEqual(set(_STATIC_GZIP_CACHE), {"css/style.css"})
        canonical = {
            _canonical_static_file(alias)[0]
            for alias in (
                "css/style.css",
                "css/./style.css",
                "css//style.css",
                "css/sub/../style.css",
            )
        }
        self.assertEqual(canonical, {"css/style.css"})
        self.assertIsNone(_canonical_static_file("../requirements.txt"))


class PublicResponseCompressionTests(unittest.TestCase):
    """Gzip reduces public text bytes without crossing private boundaries."""

    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(TESTING=self.original_testing)

    def test_public_html_gzip_round_trips_and_meets_budget(self):
        identity = self.client.get("/")
        compressed = self.client.get(
            "/",
            headers={"Accept-Encoding": "gzip"},
        )

        self.assertEqual(compressed.headers.get("Content-Encoding"), "gzip")
        self.assertIn(
            "Accept-Encoding",
            compressed.headers.get("Vary", ""),
        )
        self.assertEqual(gzip.decompress(compressed.data), identity.data)
        self.assertLessEqual(len(compressed.data), len(identity.data) * 0.35)
        identity.close()
        compressed.close()

    def test_exact_version_css_gzip_round_trips_and_is_immutable(self):
        version = _static_file_version("css/style.css")
        url = f"/static/css/style.css?v={version}"
        identity = self.client.get(url)
        compressed = self.client.get(
            url,
            headers={"Accept-Encoding": "gzip"},
        )

        self.assertEqual(compressed.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(gzip.decompress(compressed.data), identity.data)
        self.assertLessEqual(len(compressed.data), len(identity.data) * 0.35)
        self.assertEqual(
            compressed.headers.get("Cache-Control"),
            "public, max-age=31536000, immutable",
        )
        self.assertIsNone(compressed.headers.get("ETag"))
        identity.close()
        compressed.close()

    def test_gzip_rejection_and_head_are_not_compressed(self):
        rejected = self.client.get(
            "/",
            headers={"Accept-Encoding": "gzip;q=0, identity;q=1"},
        )
        head = self.client.head(
            "/",
            headers={"Accept-Encoding": "gzip"},
        )

        self.assertIsNone(rejected.headers.get("Content-Encoding"))
        self.assertIn("Accept-Encoding", rejected.headers.get("Vary", ""))
        self.assertIsNone(head.headers.get("Content-Encoding"))

    def test_private_no_store_response_is_not_compressed(self):
        with app.test_request_context(
            "/private-test",
            headers={"Accept-Encoding": "gzip"},
        ):
            response = Response(
                "private member text " * 500,
                mimetype="text/html",
            )
            response.headers["Cache-Control"] = "private, no-store"

            result = _compress_public_text_response(response)

        self.assertIsNone(result.headers.get("Content-Encoding"))
        self.assertEqual(result.headers["Cache-Control"], "private, no-store")

    def test_response_that_will_set_session_cookie_is_not_compressed(self):
        original_secret = app.secret_key
        app.secret_key = "test-cookie-key"
        try:
            with app.test_request_context(
                "/cookie-test",
                headers={"Accept-Encoding": "gzip"},
            ):
                session["compression_probe"] = "member-specific-value"
                response = Response(
                    "otherwise public text " * 500,
                    mimetype="text/html",
                )
                response.headers["Cache-Control"] = "no-cache, must-revalidate"

                result = _compress_public_text_response(response)
                app.session_interface.save_session(app, session, result)
        finally:
            app.secret_key = original_secret

        self.assertIsNone(result.headers.get("Content-Encoding"))
        self.assertTrue(result.headers.getlist("Set-Cookie"))

    def test_small_no_store_health_and_range_responses_are_not_compressed(self):
        health = self.client.get(
            "/healthz",
            headers={"Accept-Encoding": "gzip"},
        )
        version = _static_file_version("css/style.css")
        partial = self.client.get(
            f"/static/css/style.css?v={version}",
            headers={"Accept-Encoding": "gzip", "Range": "bytes=0-99"},
        )

        self.assertIsNone(health.headers.get("Content-Encoding"))
        self.assertEqual(health.headers.get("Cache-Control"), "no-store")
        self.assertEqual(partial.status_code, 206)
        self.assertIsNone(partial.headers.get("Content-Encoding"))
        self.assertEqual(len(partial.data), 100)
        partial.close()


if __name__ == "__main__":
    unittest.main()
