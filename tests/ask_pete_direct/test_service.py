"""Contract tests for services/ask_pete_direct_service.py.

The database is mocked at the ``database_service`` seam - the service is given
a double whose ``first_row`` / ``execute_procedure`` record the procedure name
and the exact bound parameters. That is deliberately the ONLY seam these tests
touch: everything above it (validation, bounds, consent, false-success guards,
serialization) is what this module is responsible for, and everything below it
is proven by the migration's own verifier against a real server.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from services.ask_pete_direct_service import (
    CONSENT_VERSION,
    MAX_CONTACT_UNITS,
    MAX_IDEMPOTENCY_UNITS,
    MAX_QUESTION_UNITS,
    AskPeteDirectError,
    AskPeteDirectService,
    utf16_length,
    validate_question_input,
)
from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError


RECIPIENT = "owner-user-key"
QUESTION_FIXTURE = "6f1b7e3a-8a4a-4a1e-9f0e-2b6c9f7d1a55"
VERSION_STAMP = "00000000000004d2"


def _list_row(**overrides):
    row = {
        "recruiter_question_key": QUESTION_FIXTURE,
        "question_status": "new",
        "question_text": "Does Pete have hands-on MBSE tooling experience?",
        "contact_text": "Dana at Northwind, dana@example.com",
        "consent_version": CONSENT_VERSION,
        "created_at_utc": datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
        "status_changed_at_utc": None,
        "row_version": bytes.fromhex(VERSION_STAMP),
    }
    row.update(overrides)
    return row


class FakeDatabase:
    """Records every call; returns whatever the test queued."""

    def __init__(self, rows=None, result_sets=None, error=None):
        self.rows = rows if rows is not None else []
        self.result_sets = result_sets
        self.error = error
        self.calls = []

    def first_row(self, procedure_name, parameters=None):
        self.calls.append((procedure_name, list(parameters or [])))
        if self.error:
            raise self.error
        return self.rows.pop(0) if self.rows else None

    def execute_procedure(self, procedure_name, parameters=None):
        self.calls.append((procedure_name, list(parameters or [])))
        if self.error:
            raise self.error
        return self.result_sets if self.result_sets is not None else []

    def parameters(self, index=0):
        return dict(self.calls[index][1])


def service_with(**kwargs):
    database = FakeDatabase(**kwargs)
    return AskPeteDirectService(database=database), database


class AllowlistTests(unittest.TestCase):
    def test_every_procedure_this_service_calls_is_allowlisted(self):
        for name in (
            "usp_SubmitRecruiterQuestion",
            "usp_ListRecruiterQuestionsForOwner",
            "usp_SetRecruiterQuestionStatusForOwner",
        ):
            with self.subTest(procedure=name):
                self.assertIn(name, ALLOWED_PROCEDURES)

    def test_no_recruiter_question_delete_or_purge_is_allowlisted(self):
        for name in sorted(ALLOWED_PROCEDURES):
            if "RecruiterQuestion" not in name:
                continue
            with self.subTest(procedure=name):
                self.assertNotIn("Delete", name)
                self.assertNotIn("Purge", name)


class SubmitValidationTests(unittest.TestCase):
    """Every rung of the ladder refuses BEFORE the database is touched."""

    def submit(self, **overrides):
        payload = {
            "recipient_user_key": RECIPIENT,
            "idempotency_key": "idem-1",
            "question": "How much of the recovery effort did Pete lead himself?",
            "contact": None,
            "consent": True,
        }
        payload.update(overrides)
        service, database = service_with(rows=[{"outcome": "success"}])
        return service, database, payload

    def assert_refused(self, code, **overrides):
        service, database, payload = self.submit(**overrides)
        with self.assertRaises(AskPeteDirectError) as raised:
            service.submit_question(**payload)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(database.calls, [], "nothing may reach the database")

    def test_a_missing_recipient_is_refused(self):
        self.assert_refused("no_identity", recipient_user_key=None)
        self.assert_refused("no_identity", recipient_user_key="   ")
        self.assert_refused("no_identity", recipient_user_key=42)

    def test_a_missing_idempotency_key_is_refused(self):
        self.assert_refused("required", idempotency_key=None)
        self.assert_refused("required", idempotency_key="")
        self.assert_refused("required", idempotency_key="  ")

    def test_an_over_length_idempotency_key_is_refused(self):
        self.assert_refused(
            "too_long", idempotency_key="k" * (MAX_IDEMPOTENCY_UNITS + 1)
        )

    def test_an_empty_or_non_string_question_is_refused(self):
        for question in (None, "", "   ", 7, ["a"]):
            with self.subTest(question=question):
                self.assert_refused("required", question=question)

    def test_an_over_length_question_is_refused(self):
        self.assert_refused("too_long", question="q" * (MAX_QUESTION_UNITS + 1))

    def test_an_over_length_contact_is_refused(self):
        self.assert_refused("too_long", contact="c" * (MAX_CONTACT_UNITS + 1))

    def test_a_non_string_contact_is_refused(self):
        self.assert_refused("invalid", contact=17)

    def test_consent_must_be_exactly_true(self):
        for consent in (None, False, 0, 1, "true", "on", "yes", [1], object()):
            with self.subTest(consent=consent):
                self.assert_refused("consent_required", consent=consent)

    def test_bounds_are_counted_in_utf16_code_units_not_python_characters(self):
        """An astral character costs two units in SQL Server and one in Python.

        Counting with len() would let a question through that the CHECK
        constraint then rejects as a raw constraint violation.
        """
        emoji = "\U0001f600"
        self.assertEqual(len(emoji), 1)
        self.assertEqual(utf16_length(emoji), 2)
        question = emoji * (MAX_QUESTION_UNITS // 2 + 1)
        self.assertLessEqual(len(question), MAX_QUESTION_UNITS)
        self.assert_refused("too_long", question=question)

    def test_the_exact_limit_is_accepted(self):
        service, database, payload = self.submit(
            question="q" * MAX_QUESTION_UNITS, contact="c" * MAX_CONTACT_UNITS
        )
        result = service.submit_question(**payload)
        self.assertTrue(result["stored"])
        self.assertEqual(len(database.calls), 1)


class SubmitStorageTests(unittest.TestCase):
    def test_the_submit_calls_exactly_one_procedure_with_bound_parameters(self):
        service, database = service_with(rows=[{"outcome": "success"}])
        result = service.submit_question(
            RECIPIENT, "  idem-42  ", "  Where did he do that?  ", "  Dana  ", True
        )

        self.assertEqual(len(database.calls), 1)
        name, _ = database.calls[0]
        self.assertEqual(name, "usp_SubmitRecruiterQuestion")
        self.assertEqual(
            database.parameters(),
            {
                "@OwnerUserKey": RECIPIENT,
                "@IdempotencyKey": "idem-42",
                "@QuestionText": "Where did he do that?",
                "@ContactText": "Dana",
                "@ConsentVersion": CONSENT_VERSION,
                "@ConsentGiven": 1,
            },
        )
        self.assertEqual(
            result,
            {"stored": True, "state": "sent", "consent_version": CONSENT_VERSION},
        )

    def test_the_recipient_key_is_passed_through_unchanged(self):
        """The service resolves nothing. Whatever key it is handed is exactly
        what @OwnerUserKey receives, so a forged one fails at the database."""
        service, database = service_with(rows=[{"outcome": "not_found"}])
        with self.assertRaises(AskPeteDirectError):
            service.submit_question("forged-key", "idem", "Q?", None, True)
        self.assertEqual(database.parameters()["@OwnerUserKey"], "forged-key")

    def test_an_empty_contact_is_stored_as_null_not_as_an_empty_string(self):
        service, database = service_with(rows=[{"outcome": "success"}])
        service.submit_question(RECIPIENT, "idem", "Q?", "   ", True)
        self.assertIsNone(database.parameters()["@ContactText"])

    def test_a_replayed_key_reports_already_sent_rather_than_a_second_send(self):
        service, _ = service_with(rows=[{"outcome": "existing"}])
        result = service.submit_question(RECIPIENT, "idem", "Q?", None, True)
        self.assertEqual(result["state"], "already_sent")
        self.assertTrue(result["stored"])

    def test_the_submit_never_returns_the_stored_question_key(self):
        service, _ = service_with(rows=[{"outcome": "success"}])
        result = service.submit_question(RECIPIENT, "idem", "Q?", None, True)
        self.assertEqual(set(result), {"stored", "state", "consent_version"})

    def test_an_unrecognised_or_missing_outcome_is_never_a_false_send(self):
        for row in (
            {"outcome": "not_found"},
            {"outcome": "queued"},
            {"outcome": None},
            None,
            {},
            {"outcome": "success", "recruiter_question_key": QUESTION_FIXTURE},
        ):
            with self.subTest(row=row):
                service, _ = service_with(rows=[row])
                with self.assertRaises(AskPeteDirectError):
                    service.submit_question(RECIPIENT, "idem", "Q?", None, True)

    def test_a_database_failure_never_surfaces_the_drivers_words(self):
        service, _ = service_with(
            error=DatabaseServiceError(
                "Database procedure usp_SubmitRecruiterQuestion failed."
            )
        )
        with self.assertRaises(AskPeteDirectError) as raised:
            service.submit_question(RECIPIENT, "idem", "Q?", None, True)
        self.assertEqual(raised.exception.code, "unavailable")
        self.assertNotIn("usp_", str(raised.exception))


class ListTests(unittest.TestCase):
    def test_the_list_read_serializes_rows_and_true_counts(self):
        service, database = service_with(
            result_sets=[[_list_row()], [{"total_count": 4, "new_count": 2}]]
        )
        result = service.list_questions_for_owner("owner-key")

        self.assertEqual(database.calls[0][0], "usp_ListRecruiterQuestionsForOwner")
        self.assertEqual(
            database.parameters(), {"@UserKey": "owner-key", "@IncludeArchived": 0}
        )
        self.assertEqual(result.total_count, 4)
        self.assertEqual(result.new_count, 2)
        item = result.items[0]
        self.assertEqual(item["question_key"], QUESTION_FIXTURE)
        self.assertEqual(item["status"], "new")
        self.assertEqual(item["version_token"], VERSION_STAMP)
        self.assertEqual(item["created_at"], "2026-08-08T12:00:00Z")
        self.assertIsNone(item["status_changed_at"])

    def test_include_archived_is_passed_through(self):
        service, database = service_with(result_sets=[[], []])
        service.list_questions_for_owner("owner-key", include_archived=True)
        self.assertEqual(database.parameters()["@IncludeArchived"], 1)

    def test_an_owner_with_no_questions_reads_as_zero_not_as_unknown(self):
        service, _ = service_with(result_sets=[[], [{"total_count": 0, "new_count": 0}]])
        result = service.list_questions_for_owner("owner-key")
        self.assertEqual((result.items, result.total_count, result.new_count), ([], 0, 0))

    def test_a_row_with_an_unexpected_shape_is_rejected_not_partly_trusted(self):
        for row in (
            {**_list_row(), "extra": 1},
            {key: value for key, value in _list_row().items() if key != "consent_version"},
        ):
            with self.subTest(row=sorted(row)):
                service, _ = service_with(result_sets=[[row], []])
                with self.assertRaises(AskPeteDirectError):
                    service.list_questions_for_owner("owner-key")

    def test_an_unknown_status_is_rejected(self):
        service, _ = service_with(result_sets=[[_list_row(question_status="deleted")], []])
        with self.assertRaises(AskPeteDirectError):
            service.list_questions_for_owner("owner-key")

    def test_a_result_larger_than_the_procedure_bound_is_rejected(self):
        service, _ = service_with(result_sets=[[_list_row()] * 201, []])
        with self.assertRaises(AskPeteDirectError):
            service.list_questions_for_owner("owner-key")

    def test_a_missing_owner_key_never_reaches_the_database(self):
        service, database = service_with(result_sets=[[], []])
        with self.assertRaises(AskPeteDirectError) as raised:
            service.list_questions_for_owner("")
        self.assertEqual(raised.exception.code, "no_identity")
        self.assertEqual(database.calls, [])


class StatusChangeTests(unittest.TestCase):
    def test_a_status_change_calls_one_version_fenced_procedure(self):
        service, database = service_with(
            rows=[
                {
                    "outcome": "success",
                    "question_status": "read",
                    "row_version": bytes.fromhex("00000000000004d3"),
                }
            ]
        )
        result = service.set_question_status_for_owner(
            "owner-key", QUESTION_FIXTURE, "read", VERSION_STAMP
        )

        self.assertEqual(
            database.calls[0][0], "usp_SetRecruiterQuestionStatusForOwner"
        )
        self.assertEqual(
            database.parameters(),
            {
                "@UserKey": "owner-key",
                "@RecruiterQuestionKey": QUESTION_FIXTURE,
                "@Status": "read",
                "@ExpectedRowVersion": bytes.fromhex(VERSION_STAMP),
            },
        )
        self.assertEqual(result["status"], "read")
        self.assertEqual(result["version_token"], "00000000000004d3")

    def test_only_the_three_real_statuses_are_settable(self):
        for status in ("deleted", "purged", "spam", "", None, "READ"):
            with self.subTest(status=status):
                service, database = service_with(rows=[])
                with self.assertRaises(AskPeteDirectError) as raised:
                    service.set_question_status_for_owner(
                        "owner-key", QUESTION_FIXTURE, status, VERSION_STAMP
                    )
                self.assertEqual(raised.exception.code, "invalid")
                self.assertEqual(database.calls, [])

    def test_a_changed_outcome_is_raised_rather_than_reported_as_success(self):
        service, _ = service_with(
            rows=[{"outcome": "changed", "question_status": None, "row_version": None}]
        )
        with self.assertRaises(AskPeteDirectError) as raised:
            service.set_question_status_for_owner(
                "owner-key", QUESTION_FIXTURE, "archived", VERSION_STAMP
            )
        self.assertEqual(raised.exception.code, "changed")

    def test_a_malformed_question_key_or_version_never_reaches_the_database(self):
        service, database = service_with(rows=[])
        for question_key, token in (
            ("not-a-uuid", VERSION_STAMP),
            (None, VERSION_STAMP),
            (QUESTION_FIXTURE, "zz"),
            (QUESTION_FIXTURE, None),
            (QUESTION_FIXTURE, b"\x00" * 4),
        ):
            with self.subTest(question_key=question_key, token=token):
                with self.assertRaises(AskPeteDirectError):
                    service.set_question_status_for_owner(
                        "owner-key", question_key, "read", token
                    )
        self.assertEqual(database.calls, [])

    def test_there_is_no_delete_method_on_the_service(self):
        for forbidden in ("delete_question_for_owner", "purge_questions", "delete"):
            with self.subTest(forbidden=forbidden):
                self.assertFalse(hasattr(AskPeteDirectService, forbidden))


class ValidateHelperTests(unittest.TestCase):
    def test_the_shared_validator_returns_the_cleaned_pair(self):
        self.assertEqual(
            validate_question_input("  Why?  ", "  Dana  ", True), ("Why?", "Dana")
        )

    def test_the_shared_validator_normalises_an_absent_contact(self):
        self.assertEqual(validate_question_input("Why?", "", True), ("Why?", None))
        self.assertEqual(validate_question_input("Why?", None, True), ("Why?", None))


if __name__ == "__main__":
    unittest.main()
