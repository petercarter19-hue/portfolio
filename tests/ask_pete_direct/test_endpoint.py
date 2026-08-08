"""Contract tests for the POST /api/ask-pete/direct-question endpoint.

Everything here runs against the throwaway app in ``support.py``, which
registers the blueprint directly. The production application does not register
it, and ``test_darkness.py`` is the test that proves that separately.
"""

from __future__ import annotations

import unittest

import ask_pete_direct_routes
from ask_pete_direct_routes import (
    ALLOWED_QUESTION_FIELDS,
    DIRECT_QUESTION_ENDPOINT,
    DIRECT_QUESTION_PATH,
    HONEYPOT_FIELD,
    MAX_DIRECT_QUESTION_BYTES,
    PLANNED_RATE_LIMITS,
)
from services.ask_pete_direct_service import (
    CONSENT_VERSION,
    MAX_CONTACT_UNITS,
    MAX_IDEMPOTENCY_UNITS,
    MAX_QUESTION_UNITS,
)
from services.database_service import DatabaseServiceError

from tests.ask_pete_direct.support import (
    OWNER_USER_KEY,
    DirectRouteTestCase,
    json_headers,
    question_payload,
)


SUCCESS_ROW = {"outcome": "success"}
EXISTING_ROW = {"outcome": "existing"}


def _blueprint_rules():
    """The blueprint's rules, readable only once it is registered somewhere."""
    from flask import Flask

    probe = Flask("ask_pete_direct_rule_probe")
    probe.register_blueprint(ask_pete_direct_routes.ask_pete_direct)
    return {
        rule.endpoint: rule
        for rule in probe.url_map.iter_rules()
        if rule.endpoint.startswith("ask_pete_direct.")
    }


class FlagGateTests(DirectRouteTestCase):
    def test_the_flag_is_off_by_default_for_a_plain_flask_app(self):
        """Nothing sets this key unless a deployment deliberately does."""
        client, database = self.make_app(enabled=True)
        self.app.config.pop("PEERSLATE_ASK_PETE_DIRECT_ENABLED")
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(database.calls, [])

    def test_flag_off_answers_a_neutral_404_with_nothing_stored(self):
        client, database = self.make_app(enabled=False)
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"success": False, "message": "Not found."})
        self.assertEqual(database.calls, [])

    def test_a_non_boolean_flag_value_fails_closed(self):
        """A "true" string in an environment file must not enable the path."""
        for value in ("true", "True", 1, "1", "yes", [1]):
            with self.subTest(value=value):
                client, database = self.make_app(enabled=value)
                response = client.post(
                    DIRECT_QUESTION_PATH,
                    json=question_payload(),
                    headers=json_headers(),
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(database.calls, [])

    def test_flag_off_refuses_before_the_same_origin_check_can_disclose_anything(self):
        """A cross-site caller and a same-origin caller get the same answer."""
        client, _ = self.make_app(enabled=False)
        cross_site = client.post(
            DIRECT_QUESTION_PATH,
            json=question_payload(),
            headers=json_headers(Sec_Fetch_Site="cross-site"),
        )
        same_origin = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(cross_site.status_code, same_origin.status_code)
        self.assertEqual(cross_site.get_json(), same_origin.get_json())


class SameOriginTests(DirectRouteTestCase):
    def post(self, headers, database_rows=(SUCCESS_ROW,)):
        client, database = self.make_app(rows=list(database_rows))
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=headers
        )
        return response, database

    def test_a_missing_custom_header_is_refused(self):
        response, database = self.post(json_headers(X_PeerSlate_Request=None))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(database.calls, [])

    def test_a_wrong_custom_header_is_refused(self):
        response, database = self.post(json_headers(X_PeerSlate_Request="anything"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(database.calls, [])

    def test_a_foreign_origin_is_refused(self):
        response, database = self.post(json_headers(Origin="https://evil.example"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(database.calls, [])

    def test_a_cross_site_fetch_is_refused(self):
        for fetch_site in ("cross-site", "same-site"):
            with self.subTest(fetch_site=fetch_site):
                response, database = self.post(json_headers(Sec_Fetch_Site=fetch_site))
                self.assertEqual(response.status_code, 403)
                self.assertEqual(database.calls, [])

    def test_a_non_json_body_is_refused_with_415(self):
        client, database = self.make_app(rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH,
            data="question=hello",
            headers=json_headers(Content_Type="application/x-www-form-urlencoded"),
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(database.calls, [])

    def test_absent_optional_headers_are_still_accepted_when_the_custom_one_proves_it(self):
        """Origin and Sec-Fetch-Site are advisory on a fetch() write; the
        X-PeerSlate-Request header a cross-origin form cannot set is the
        control. This mirrors community_api exactly."""
        response, database = self.post(json_headers(Origin=None, Sec_Fetch_Site=None))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(database.procedures, ["usp_SubmitRecruiterQuestion"])


class ValidationLadderTests(DirectRouteTestCase):
    def post(self, payload, *, headers=None, rows=(SUCCESS_ROW,)):
        client, database = self.make_app(rows=list(rows))
        response = client.post(
            DIRECT_QUESTION_PATH, json=payload, headers=headers or json_headers()
        )
        return response, database

    def assert_refused(self, payload, *, headers=None, code=None):
        response, database = self.post(payload, headers=headers)
        self.assertEqual(response.status_code, 422)
        body = response.get_json()
        self.assertFalse(body["success"])
        if code:
            self.assertEqual(body["code"], code)
        self.assertEqual(database.calls, [], "nothing may be stored")
        return body

    def test_a_missing_idempotency_key_is_refused(self):
        self.assert_refused(
            question_payload(), headers=json_headers(idempotency_key=None), code="required"
        )

    def test_a_blank_idempotency_key_is_refused(self):
        self.assert_refused(
            question_payload(), headers=json_headers(idempotency_key="   "), code="required"
        )

    def test_an_over_length_idempotency_key_is_refused(self):
        self.assert_refused(
            question_payload(),
            headers=json_headers(idempotency_key="k" * (MAX_IDEMPOTENCY_UNITS + 1)),
            code="too_long",
        )

    def test_a_non_object_body_is_refused(self):
        for body in ([], "text", 12, None, True):
            with self.subTest(body=body):
                self.assert_refused(body, code="invalid")

    def test_an_unexpected_field_is_refused_rather_than_ignored(self):
        self.assert_refused(
            question_payload(recipient="somebody-else"), code="invalid"
        )
        self.assert_refused(question_payload(consent_version="forged"), code="invalid")
        self.assert_refused(question_payload(status="read"), code="invalid")

    def test_a_filled_honeypot_is_refused_and_never_faked_as_sent(self):
        body = self.assert_refused(
            question_payload(**{HONEYPOT_FIELD: "https://spam.example"}), code="invalid"
        )
        self.assertNotIn("sent", body["message"].lower())

    def test_an_empty_honeypot_is_accepted(self):
        response, database = self.post(question_payload(**{HONEYPOT_FIELD: ""}))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(database.procedures, ["usp_SubmitRecruiterQuestion"])

    def test_a_missing_empty_or_mistyped_question_is_refused(self):
        for question in (None, "", "   ", 5, ["a"], {"text": "x"}):
            with self.subTest(question=question):
                payload = question_payload()
                if question is None:
                    payload.pop("question")
                else:
                    payload["question"] = question
                self.assert_refused(payload)

    def test_an_over_length_question_is_refused(self):
        self.assert_refused(
            question_payload(question="q" * (MAX_QUESTION_UNITS + 1)), code="too_long"
        )

    def test_an_over_length_contact_is_refused(self):
        self.assert_refused(
            question_payload(contact="c" * (MAX_CONTACT_UNITS + 1)), code="too_long"
        )

    def test_a_mistyped_contact_is_refused(self):
        self.assert_refused(question_payload(contact=42), code="invalid")

    def test_consent_must_be_exactly_true_and_nothing_is_stored_otherwise(self):
        for consent in (False, None, 1, "true", "on", "yes", [], {}):
            with self.subTest(consent=consent):
                self.assert_refused(
                    question_payload(consent=consent), code="consent_required"
                )

    def test_a_missing_consent_field_is_refused(self):
        payload = question_payload()
        payload.pop("consent")
        self.assert_refused(payload, code="consent_required")

    def test_the_exact_bounds_are_accepted(self):
        response, database = self.post(
            question_payload(
                question="q" * MAX_QUESTION_UNITS, contact="c" * MAX_CONTACT_UNITS
            )
        )
        self.assertEqual(response.status_code, 201)
        parameters = database.parameters()
        self.assertEqual(len(parameters["@QuestionText"]), MAX_QUESTION_UNITS)
        self.assertEqual(len(parameters["@ContactText"]), MAX_CONTACT_UNITS)

    def test_an_oversized_body_is_bounded_before_it_is_parsed(self):
        client, database = self.make_app(rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH,
            data=b'{"question":"' + b"x" * (MAX_DIRECT_QUESTION_BYTES * 2) + b'"}',
            headers=json_headers(),
        )
        self.assertIn(response.status_code, {413, 422})
        self.assertEqual(database.calls, [])


class StorageContractTests(DirectRouteTestCase):
    def test_a_valid_question_reaches_exactly_one_allowlisted_procedure(self):
        client, database = self.make_app(rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH,
            json=question_payload(),
            headers=json_headers(idempotency_key="idem-abc"),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(database.procedures, ["usp_SubmitRecruiterQuestion"])
        self.assertEqual(
            database.parameters(),
            {
                "@OwnerUserKey": OWNER_USER_KEY,
                "@IdempotencyKey": "idem-abc",
                "@QuestionText": question_payload()["question"],
                "@ContactText": question_payload()["contact"],
                "@ConsentVersion": CONSENT_VERSION,
                "@ConsentGiven": 1,
            },
        )

    def test_the_recipient_can_never_come_from_the_request(self):
        """Even a payload that names one is refused outright, and the key the
        procedure receives is always the configured one."""
        client, database = self.make_app(rows=[SUCCESS_ROW], owner_user_keys="the-owner")
        refused = client.post(
            DIRECT_QUESTION_PATH,
            json=question_payload(recipient="victim-user-key"),
            headers=json_headers(),
        )
        self.assertEqual(refused.status_code, 422)

        accepted = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(database.parameters()["@OwnerUserKey"], "the-owner")

    def test_a_double_submit_with_one_key_reports_already_sent(self):
        client, database = self.make_app(rows=[SUCCESS_ROW, EXISTING_ROW])
        first = client.post(
            DIRECT_QUESTION_PATH,
            json=question_payload(),
            headers=json_headers(idempotency_key="same-key"),
        )
        second = client.post(
            DIRECT_QUESTION_PATH,
            json=question_payload(),
            headers=json_headers(idempotency_key="same-key"),
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.get_json()["state"], "sent")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()["state"], "already_sent")
        self.assertEqual(
            [parameters["@IdempotencyKey"] for parameters in map(dict, (call[1] for call in database.calls))],
            ["same-key", "same-key"],
        )

    def test_the_response_never_carries_a_stored_question_identifier(self):
        client, _ = self.make_app(rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(
            set(response.get_json()), {"success", "state", "consent_version", "message"}
        )

    def test_the_response_states_the_consent_version_that_was_recorded(self):
        client, _ = self.make_app(rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.get_json()["consent_version"], CONSENT_VERSION)

    def test_the_sent_message_promises_nothing_automatic(self):
        client, _ = self.make_app(rows=[SUCCESS_ROW])
        message = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        ).get_json()["message"]
        self.assertIn("own schedule", message)
        for overclaim in ("reply shortly", "we will get back", "confirmation email"):
            with self.subTest(overclaim=overclaim):
                self.assertNotIn(overclaim, message.lower())


class UnavailableTests(DirectRouteTestCase):
    def test_no_configured_recipient_is_unavailable_not_a_silent_success(self):
        client, database = self.make_app(owner_user_keys="", rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "unavailable")
        self.assertEqual(database.calls, [])

    def test_an_ambiguous_recipient_is_refused_rather_than_guessed(self):
        client, database = self.make_app(
            owner_user_keys="owner-one owner-two", rows=[SUCCESS_ROW]
        )
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(database.calls, [])

    def test_an_email_only_owner_allowlist_is_unavailable(self):
        client, database = self.make_app(
            owner_user_keys="", owner_emails="owner@example.com", rows=[SUCCESS_ROW]
        )
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(database.calls, [])

    def test_a_storage_failure_is_unavailable_and_leaks_nothing(self):
        client, _ = self.make_app(
            error=DatabaseServiceError(
                "Database procedure usp_SubmitRecruiterQuestion failed."
            )
        )
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["code"], "unavailable")
        self.assertNotIn("usp_", body["message"])

    def test_an_unresolvable_recipient_is_never_reported_as_sent(self):
        client, _ = self.make_app(rows=[{"outcome": "not_found"}])
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "unavailable")


class ResponseHardeningTests(DirectRouteTestCase):
    def test_every_response_is_private_and_unindexed(self):
        client, _ = self.make_app(rows=[SUCCESS_ROW])
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")

    def test_the_refusals_are_hardened_too(self):
        client, _ = self.make_app(enabled=False)
        response = client.post(
            DIRECT_QUESTION_PATH, json=question_payload(), headers=json_headers()
        )
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")


class MethodSurfaceTests(DirectRouteTestCase):
    def test_the_endpoint_accepts_only_post(self):
        client, database = self.make_app(rows=[SUCCESS_ROW])
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(client, method)(
                    DIRECT_QUESTION_PATH, headers=json_headers()
                )
                self.assertEqual(response.status_code, 405)
        self.assertEqual(database.calls, [])


class RateLimitPlanTests(unittest.TestCase):
    """The one control this blueprint cannot apply itself, declared honestly."""

    def test_the_plan_names_every_state_changing_endpoint_in_this_blueprint(self):
        """A route added later without a budget fails here, not in production."""
        state_changing = {
            endpoint
            for endpoint, rule in _blueprint_rules().items()
            if {"POST", "PUT", "PATCH", "DELETE"} & rule.methods
        }
        self.assertTrue(state_changing)
        self.assertEqual(state_changing, set(PLANNED_RATE_LIMITS))

    def test_the_planned_write_budget_is_the_house_floor(self):
        self.assertEqual(PLANNED_RATE_LIMITS[DIRECT_QUESTION_ENDPOINT], "30 per hour")

    def test_the_module_documents_that_it_cannot_wire_the_limit_itself(self):
        docstring = ask_pete_direct_routes.__doc__
        self.assertIn("PLANNED_RATE_LIMITS", docstring)
        self.assertIn("Rate limiting cannot be wired from here", docstring)
        self.assertIn("after", docstring.lower())

    def test_no_parallel_limiter_was_invented_in_this_module(self):
        source = (
            ask_pete_direct_routes.__file__
        )
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        for forbidden in ("Limiter(", "get_remote_address", "time.time()", "_hit_count"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)


class FieldContractTests(unittest.TestCase):
    def test_the_accepted_field_set_is_exactly_four_names(self):
        self.assertEqual(
            ALLOWED_QUESTION_FIELDS,
            frozenset({"question", "contact", "consent", HONEYPOT_FIELD}),
        )

    def test_the_path_constant_matches_the_registered_rule(self):
        rules = _blueprint_rules()
        self.assertEqual(str(rules[DIRECT_QUESTION_ENDPOINT]), DIRECT_QUESTION_PATH)


if __name__ == "__main__":
    unittest.main()
