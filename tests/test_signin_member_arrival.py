"""PS-SIGNIN-MEMBER-ARRIVAL-001: the sign-in return contract.

These tests exist because a member's destination was being silently discarded
in production and the suite could not see it.  Opportunity Slate's own tests
asserted the return target against a *stub* auth blueprint, so they verified
only the string the room emitted and never the half of the round trip that
decides where the member actually lands.  Every test here drives the real
validator.

The rule they enforce: a producer and the consumer must never disagree about
where a member may be returned to.
"""

import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import auth_routes
import community_routes
import opportunity_slate_v2_routes
import safe_return
import workshop_routes
from app import app
from safe_return import PROTECTED_DESTINATIONS, safe_return_path
from tests.test_auth import easy_auth_header


class SafeReturnContractTests(unittest.TestCase):
    """The validator itself, exercised directly."""

    def setUp(self):
        self.context = app.test_request_context("/")
        self.context.push()
        self.original = {
            key: app.config.get(key)
            for key in ("PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED",)
        }
        app.config["PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"] = True

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value
        self.context.pop()

    def test_every_registered_destination_round_trips(self):
        for destination in PROTECTED_DESTINATIONS:
            with self.subTest(prefix=destination.prefix):
                self.assertEqual(
                    destination.prefix, safe_return_path(destination.prefix)
                )
                nested = destination.prefix + "/nested/page"
                self.assertEqual(nested, safe_return_path(nested))

    def test_opportunity_slate_is_a_valid_destination_and_was_the_live_defect(self):
        # The exact value opportunity_slate_v2_routes builds for a signed-out
        # GET.  Before this package it resolved to "/app": the member signed in
        # and was dropped on their workspace with no explanation.  Proven live
        # 2026-08-16 with a real authenticated session.
        self.assertEqual("/opportunity-slate", safe_return_path("/opportunity-slate"))
        self.assertEqual(
            "/opportunity-slate?step=replace",
            safe_return_path("/opportunity-slate?step=replace"),
        )

    def test_flag_gated_destination_falls_back_when_its_route_would_not_exist(self):
        # Flag off means the legacy public room registers at this path instead,
        # so a stale return target must not land a member on a 404.
        app.config["PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"] = False
        self.assertEqual("/app", safe_return_path("/opportunity-slate"))
        self.assertNotIn("/opportunity-slate", safe_return.available_prefixes())

    def test_dot_segment_traversal_cannot_escape_an_allowlisted_prefix(self):
        # urlsplit does not remove RFC 3986 dot segments.  Each of these starts
        # with an allowlisted prefix and carries no scheme, host, fragment,
        # backslash or "//", so every other guard passes.
        for candidate in (
            "/app/../.auth/logout",
            "/app/../admin",
            "/app/../../etc/passwd",
            "/the-slate/../app/settings",
            "/interview-studio/../.auth/login/aad",
            "/opportunity-slate/../admin",
            "/app/nested/../../outside",
        ):
            with self.subTest(candidate=candidate):
                self.assertEqual("/app", safe_return_path(candidate))

    def test_app_prefix_confusion_is_rejected_like_the_other_prefixes(self):
        # /the-slate and /interview-studio already had these negatives; /app,
        # the default and most-used destination, did not.
        for candidate in ("/appx", "/app-x", "/apple", "/appsettings"):
            with self.subTest(candidate=candidate):
                self.assertEqual("/app", safe_return_path(candidate))

    def test_every_control_character_class_is_rejected(self):
        # The suite only ever supplied NUL.  DEL is a separately written and
        # separately deletable clause, and CRLF is the classic injection
        # payload for a value that ends up in a Location header.
        for candidate in (
            "/app\x00x",
            "/app\x7fx",
            "/app\tx",
            "/app\rx",
            "/app\nx",
            "/app\r\nSet-Cookie: x=y",
            "/app\x1fx",
        ):
            with self.subTest(candidate=repr(candidate)):
                self.assertEqual("/app", safe_return_path(candidate))

    def test_length_boundary_is_exact(self):
        limit = safe_return.MAX_RETURN_PATH_LENGTH
        at_limit = "/app/" + ("x" * (limit - len("/app/")))
        self.assertEqual(limit, len(at_limit))
        self.assertEqual(at_limit, safe_return_path(at_limit))

        over_limit = at_limit + "x"
        self.assertEqual(limit + 1, len(over_limit))
        self.assertEqual("/app", safe_return_path(over_limit))

    def test_auth_machinery_stays_unreachable_as_a_return_target(self):
        for candidate in (
            "/auth",
            "/auth/sign-in",
            "/auth/complete",
            "/.auth",
            "/.auth/login/aad",
            "/.auth/logout",
        ):
            with self.subTest(candidate=candidate):
                self.assertEqual("/app", safe_return_path(candidate))

    def test_off_site_and_malformed_targets_are_rejected(self):
        for candidate in (
            "https://attacker.example/app",
            "http://attacker.example/app",
            "//attacker.example/app",
            "/\\attacker.example",
            "/app\\outside",
            "/app//outside",
            "/app#fragment",
            "/petec/resume",
            "",
            None,
            12345,
        ):
            with self.subTest(candidate=repr(candidate)):
                self.assertEqual("/app", safe_return_path(candidate))

    def test_caller_supplied_default_is_honoured_on_rejection(self):
        self.assertEqual(
            "/app/workshop", safe_return_path("https://evil.example", "/app/workshop")
        )


class NoProducerDisagreesWithTheConsumerTests(unittest.TestCase):
    """The structural guarantee that stops this defect class recurring.

    Four modules used to hold four different implementations, two of them
    carrying docstrings claiming they mirrored a sibling "exactly" when they
    did not.  If any of these ever stops delegating, the drift is back.
    """

    def test_every_producer_delegates_to_the_shared_validator(self):
        with app.test_request_context("/"):
            app.config["PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"] = True
            # A value only the canonical validator rejects: the weak copies
            # this replaced had no allowlist, no dot-segment rule and no
            # /.auth exclusion, so each would have returned it unchanged.
            hostile = "/app/../.auth/logout"
            self.assertEqual("/app", auth_routes._safe_return_path(hostile))
            self.assertEqual(
                "/app/workshop", workshop_routes._safe_return_path(hostile)
            )
            self.assertEqual(
                "/opportunity-slate",
                opportunity_slate_v2_routes._safe_return_path(hostile),
            )

    def test_the_validator_is_defined_in_exactly_one_place(self):
        source = (
            "safe_return.py",
            "auth_routes.py",
            "workshop_routes.py",
            "opportunity_slate_v2_routes.py",
            "community_routes.py",
        )
        from pathlib import Path

        implementations = []
        for name in source:
            text = Path(name).read_text(encoding="utf-8")
            # The allowlist match is the load-bearing line; only the shared
            # module may contain it.
            if "PROTECTED_DESTINATIONS = (" in text:
                implementations.append(name)
        self.assertEqual(["safe_return.py"], implementations)


class SignInRoundTripTests(unittest.TestCase):
    """Both halves of the journey, through the real endpoints.

    ``/auth/complete`` is the endpoint that turns a caller-supplied value into
    a raw Location header — it is the actual open-redirect sink, and the
    hostile matrix was previously applied only to ``/auth/sign-in``.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original = {
            key: app.config.get(key)
            for key in (
                "TESTING",
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED",
            )
        }
        app.config["TESTING"] = True
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        app.config["PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"] = True

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def _return_to_of(self, location):
        """The return_to the provider URL will hand back to /auth/complete."""
        redirect_uri = parse_qs(urlsplit(location).query)["post_login_redirect_uri"][0]
        return parse_qs(urlsplit(redirect_uri).query)["return_to"][0]

    def test_sign_in_preserves_every_registered_destination(self):
        for destination in PROTECTED_DESTINATIONS:
            with self.subTest(prefix=destination.prefix):
                response = self.client.get(
                    "/auth/sign-in", query_string={"return_to": destination.prefix}
                )
                self.assertEqual(302, response.status_code)
                self.assertEqual(
                    destination.prefix,
                    self._return_to_of(response.headers["Location"]),
                )

    def test_complete_lands_a_signed_in_member_on_every_registered_destination(self):
        # This is the assertion whose absence hid the defect: the half of the
        # round trip that actually decides where the member ends up.
        for destination in PROTECTED_DESTINATIONS:
            with self.subTest(prefix=destination.prefix):
                response = self.client.get(
                    "/auth/complete",
                    query_string={"return_to": destination.prefix},
                    headers=easy_auth_header("member-round-trip"),
                )
                self.assertEqual(302, response.status_code)
                self.assertEqual(destination.prefix, response.headers["Location"])

    def test_complete_rejects_the_full_hostile_matrix(self):
        for candidate in (
            "https://attacker.example/app",
            "//attacker.example/app",
            "/app/../.auth/logout",
            "/app/../admin",
            "/appx",
            "/app-x",
            "/app\\outside",
            "/app//outside",
            "/app#fragment",
            "/app\x00x",
            "/app\x7fx",
            "/app\r\nSet-Cookie: x=y",
            "/auth/sign-in",
            "/.auth/login/aad",
            "/petec/resume",
            "/app" + ("x" * 2049),
        ):
            with self.subTest(candidate=repr(candidate)):
                response = self.client.get(
                    "/auth/complete",
                    query_string={"return_to": candidate},
                    headers=easy_auth_header("member-hostile"),
                )
                self.assertEqual(302, response.status_code)
                self.assertEqual("/app", response.headers["Location"])

    def test_opportunity_slate_round_trip_end_to_end(self):
        """The exact journey that was broken, producer through consumer.

        The room's blueprint is chosen at import time (``app.py`` registers
        either the v2 room or the legacy public one depending on the flag), so
        a test client cannot drive the v2 gate itself.  This drives the gate's
        own return-target builder instead, which is the half that was
        disagreeing with the consumer.
        """
        with app.test_request_context("/opportunity-slate?step=replace"):
            from flask import request

            requested = opportunity_slate_v2_routes._safe_return_path(
                request.full_path.rstrip("?")
            )
        self.assertEqual("/opportunity-slate?step=replace", requested)

        landed = self.client.get(
            "/auth/complete",
            query_string={"return_to": requested},
            headers=easy_auth_header("member-oppslate"),
        )
        self.assertEqual(302, landed.status_code)
        # Before this package: "/app".
        self.assertEqual("/opportunity-slate?step=replace", landed.headers["Location"])

    def test_post_only_endpoints_still_return_to_the_room_not_the_action(self):
        # Pre-existing correct behaviour that must survive the refactor: a
        # member signing in after an expired-session POST lands on the room,
        # not on a path that only accepts POST.
        with app.test_request_context("/opportunity-slate/source", method="POST"):
            self.assertEqual(
                "/opportunity-slate",
                opportunity_slate_v2_routes._safe_return_path(
                    opportunity_slate_v2_routes.ROOM_PATH
                ),
            )


class HeaderReturnsMemberToTheirPageTests(unittest.TestCase):
    """The most-clicked sign-in control on the site used to discard context."""

    def setUp(self):
        self.client = app.test_client()
        self.original = {
            key: app.config.get(key)
            for key in (
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",
            )
        }
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def test_public_pages_still_default_to_the_workspace(self):
        response = self.client.get("/", base_url="http://localhost")
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn('href="/auth/sign-in?return_to=/app"', body)

    def test_a_protected_page_offers_to_return_the_member_to_it(self):
        # A signed-out reader on a protected page is redirected to sign-in with
        # that page as the target; the header control must agree rather than
        # overriding it with /app.
        with app.test_request_context("/the-slate"):
            self.assertEqual("/the-slate", auth_routes._current_return_target())
        with app.test_request_context("/interview-studio/history"):
            self.assertEqual(
                "/interview-studio/history", auth_routes._current_return_target()
            )

    def test_hostile_and_unknown_paths_still_resolve_to_the_workspace(self):
        with app.test_request_context("/petec/resume"):
            self.assertEqual("/app", auth_routes._current_return_target())
        with app.test_request_context("/app/../.auth/logout"):
            self.assertEqual("/app", auth_routes._current_return_target())

    def test_outside_a_request_there_is_no_page_to_return_to(self):
        with app.app_context():
            self.assertEqual("/app", auth_routes._current_return_target())

    def test_recovery_retry_keeps_the_destination_the_member_asked_for(self):
        # The recovery surface renders at /auth/complete, which the validator
        # correctly refuses as a destination. Taking the current path there
        # would send a member who deep-linked to Community back to /app —
        # losing their destination on the one surface where something has
        # already gone wrong for them. The requested destination is in the
        # query string, and is validated by the same rules.
        with app.test_request_context("/auth/complete?return_to=/the-slate"):
            self.assertEqual("/the-slate", auth_routes._current_return_target())
        with app.test_request_context(
            "/auth/complete?return_to=/opportunity-slate"
        ):
            app.config["PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"] = True
            self.assertEqual(
                "/opportunity-slate", auth_routes._current_return_target()
            )

    def test_auth_surfaces_never_reflect_a_hostile_return_to(self):
        for hostile in (
            "https://attacker.example/app",
            "//attacker.example",
            "/app/../.auth/logout",
            "/petec/resume",
        ):
            with self.subTest(hostile=hostile):
                with app.test_request_context(
                    "/auth/complete", query_string={"return_to": hostile}
                ):
                    self.assertEqual("/app", auth_routes._current_return_target())

    def test_auth_surface_without_a_return_to_falls_back(self):
        with app.test_request_context("/auth/complete"):
            self.assertEqual("/app", auth_routes._current_return_target())


class PrivateNamespaceParityTests(unittest.TestCase):
    """The server's registered destinations and the browser's private-path
    lists must never disagree.

    ``safe_return.py`` decides where a member may be *returned* to.  Two
    browser scripts decide what counts as a *private document*:
    ``auth-state.js`` reloads one whose session has ended in another tab, and
    ``easy-auth-callback.js`` reloads one restored from bfcache.  A namespace
    that is private on the server but unknown to a script is the same
    producer/consumer mismatch that silently dropped Opportunity Slate members
    on ``/app`` — this time across the Python/JavaScript boundary, where
    nothing was watching.

    Registering a destination in ``safe_return.py`` and forgetting a script
    now fails here instead of in a member's browser.
    """

    SCRIPTS = ("auth-state.js", "easy-auth-callback.js")

    def declared_prefixes(self, filename):
        source = (Path("static") / "js" / filename).read_text(encoding="utf-8")
        match = re.search(r"PRIVATE_PREFIXES = \[(.*?)\]", source, re.S)
        self.assertIsNotNone(
            match, f"{filename} must declare a PRIVATE_PREFIXES list"
        )
        return sorted(re.findall(r"'([^']+)'", match.group(1)))

    def test_browser_private_paths_match_the_registered_destinations(self):
        registered = sorted(
            destination.prefix for destination in PROTECTED_DESTINATIONS
        )
        # Sorted, because agreement is about membership; the order a script
        # happens to list them in carries no meaning.
        for filename in self.SCRIPTS:
            with self.subTest(script=filename):
                self.assertEqual(registered, self.declared_prefixes(filename))

    def test_the_registered_set_is_not_accidentally_empty(self):
        # A regex that stopped matching would otherwise make the test above
        # pass by comparing two empty lists.
        self.assertTrue(PROTECTED_DESTINATIONS)
        for filename in self.SCRIPTS:
            with self.subTest(script=filename):
                self.assertTrue(self.declared_prefixes(filename))


class PrivateWorkspaceReconciliationTests(unittest.TestCase):
    """The shell must load the reconciliation script on private documents.

    Before this round it was excluded from ``/app`` and ``/auth/``.  The
    ``/auth/`` exclusion is deliberate and stays: reloading a sign-in page on
    a signed-out session is a loop.  The ``/app`` exclusion was the bug. Shared
    Shell convergence now also gives the workspace truthful account controls,
    so the script owns both their reconciliation and the private-page reload.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original = {
            key: app.config.get(key)
            for key in (
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
            )
        }
        app.config["PEERSLATE_DEV_USER_KEY"] = "existing-owner"
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True

    def tearDown(self):
        for key, value in self.original.items():
            app.config[key] = value

    def test_the_private_workspace_loads_the_reconciliation_script(self):
        response = self.client.get("/app")

        self.assertEqual(200, response.status_code)
        self.assertIn(b"/static/js/auth-state.js?v=", response.data)
        self.assertIn(
            b'data-ps-auth-controls data-ps-auth-state="authenticated"',
            response.data,
        )
        self.assertIn(b'data-ps-auth-control="authenticated"', response.data)
        self.assertIn(b'method="post" action="/auth/sign-out"', response.data)

    def test_a_flag_gated_namespace_can_render_public_and_says_so(self):
        """Why the client cannot treat a private prefix as always private.

        Three of the four registered namespaces are reachable only behind
        sign-in in production, but their gate is configuration. With the gate
        off, the same path serves an ordinary public page to a signed-out
        visitor — and that render is truthful, not stale: it already carries
        ``data-ps-auth-state="signed_out"``.

        ``auth-state.js`` must therefore reload a private document only when
        the server rendered it for a signed-IN member. Without that check a
        signed-out visitor on a public Interview Studio would be reloaded every
        time they returned to the tab.
        """
        original = {
            key: app.config.get(key)
            for key in (
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
            )
        }
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        app.config["PEERSLATE_DEV_USER_KEY"] = None
        try:
            response = app.test_client().get(
                "/interview-studio", follow_redirects=False
            )
            if response.status_code != 200:
                self.skipTest(
                    "Interview Studio is behind its sign-in gate in this "
                    "configuration, which is production's setting; the public "
                    "render this guards against is not reachable here."
                )
            self.assertIn(
                b'data-ps-auth-state="signed_out"',
                response.data,
                "a public render must declare the signed-out state it is in",
            )
            self.assertIn(b"/static/js/auth-state.js?v=", response.data)
        finally:
            for key, value in original.items():
                app.config[key] = value

    def test_the_public_workshop_preview_declares_signed_out_and_is_left_alone(self):
        """A public preview remains public after its account shell converges.

        ``/app/workshop`` is a deliberately public preview — owner decision
        2026-08-02 — and returns 200 to a signed-out visitor in production
        today. It now renders the shared shell's signed-out account controls;
        the server-declared state still tells reconciliation not to mistake
        the public document for a stale signed-in private page and reload it.

        The shell must therefore declare what it rendered, on every branch.
        """
        original = {
            key: app.config.get(key)
            for key in (
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_WORKSHOP_ENABLED",
            )
        }
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        app.config["PEERSLATE_DEV_USER_KEY"] = None
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        try:
            response = app.test_client().get(
                "/app/workshop", follow_redirects=False
            )
            self.assertEqual(
                200,
                response.status_code,
                "the Workshop preview is public by owner decision",
            )
            self.assertIn(b"/static/js/auth-state.js?v=", response.data)
            self.assertIn(
                b'data-ps-auth-state="signed_out"',
                response.data,
                "a public owner-shell render must declare the state it is in, "
                "or the client cannot tell it from a stale private page",
            )
            self.assertIn(
                b'data-ps-auth-control="signed_out"', response.data
            )
            self.assertIn(
                b'href="/auth/sign-in?return_to=/app/workshop"',
                response.data,
            )
        finally:
            for key, value in original.items():
                app.config[key] = value

    def test_the_signed_in_owner_shell_declares_authenticated(self):
        """The counterpart: a real private render must be reloadable."""
        original = {
            key: app.config.get(key)
            for key in ("PEERSLATE_WORKSHOP_ENABLED",)
        }
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        try:
            for path in ("/app", "/app/workshop"):
                with self.subTest(path=path):
                    response = self.client.get(path, follow_redirects=False)
                    # Status is not the invariant here: without a database the
                    # Workshop library answers its truthful 503 surface. Both
                    # renders go through the owner shell, and both must declare
                    # the signed-in state, because that declaration is the only
                    # thing telling the client this document is private.
                    self.assertIn(
                        response.status_code,
                        (200, 503),
                        "the owner shell must render, not redirect",
                    )
                    self.assertIn(
                        b'data-ps-auth-state="authenticated"', response.data
                    )
                    self.assertIn(b"/static/js/auth-state.js?v=", response.data)
        finally:
            for key, value in original.items():
                app.config[key] = value

    def test_the_single_owner_shell_declares_its_state(self):
        response = self.client.get("/app", follow_redirects=False)
        self.assertIn(response.status_code, (200, 503))
        self.assertIn(b"/static/js/auth-state.js?v=", response.data)
        self.assertIn(b'data-ps-auth-state="authenticated"', response.data)
        self.assertNotIn(b"owner-home-shell", response.data)

    def test_the_auth_surfaces_still_exclude_it(self):
        for path in ("/auth/sign-in", "/auth/complete"):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=False)
                self.assertNotIn(b"auth-state.js", response.data)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
