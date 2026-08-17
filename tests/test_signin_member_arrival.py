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

import unittest
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
