import unittest
from unittest.mock import Mock

from services.journal_service import JournalService, JournalServiceError


def moment_row(
    moment_key="11111111-1111-1111-1111-111111111111",
    title="A confirmed Moment",
    cursor_token="2026-07-10T00:00:00.0000000|101",
):
    return {
        "moment_key": moment_key,
        "moment_kind": "achievement",
        "title": title,
        "occurred_on": "2026-07-10",
        "occurred_precision": "exact",
        "visibility": "private",
        "source_type": "text",
        "lifecycle_state": "active",
        "version_number": 1,
        "cursor_token": cursor_token,
    }


def valid_proposal():
    return {
        "moment_kind": "achievement",
        "title": "Shipped the thing",
        "occurred_on": None,
        "occurred_precision": "unknown",
        "narrative": "Wrote the narrative for the Moment.",
        "why_it_matters": None,
    }


class JournalServiceListTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = JournalService(database=self.database)

    def test_list_shapes_items_and_omits_internal_fields(self):
        self.database.first_result.return_value = [moment_row()]

        result = self.service.list_owner_journal("owner-a")

        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(
            set(item),
            {
                "moment_key",
                "moment_kind",
                "title",
                "occurred_on",
                "occurred_precision",
                "visibility",
                "source_type",
                "lifecycle_state",
                "version_number",
            },
        )
        self.assertNotIn("cursor_token", item)
        self.assertNotIn("display_at_utc", item)

    def test_list_threads_owner_key_include_archived_limit_and_cursor(self):
        self.database.first_result.return_value = []

        self.service.list_owner_journal(
            "owner-a", include_archived=True, limit=10, cursor="some-cursor"
        )

        parameters = self.database.first_result.call_args.args[1]
        self.assertEqual(
            parameters,
            [
                ("@UserKey", "owner-a"),
                ("@IncludeArchived", 1),
                ("@Limit", 10),
                ("@Cursor", "some-cursor"),
            ],
        )

    def test_list_default_excludes_archived(self):
        self.database.first_result.return_value = []

        self.service.list_owner_journal("owner-a")

        parameters = self.database.first_result.call_args.args[1]
        self.assertIn(("@IncludeArchived", 0), parameters)

    def test_list_clamps_limit_to_bounds(self):
        self.database.first_result.return_value = []

        self.service.list_owner_journal("owner-a", limit=0)
        self.assertIn(("@Limit", 1), self.database.first_result.call_args.args[1])

        self.service.list_owner_journal("owner-a", limit=9000)
        self.assertIn(("@Limit", 100), self.database.first_result.call_args.args[1])

        self.service.list_owner_journal("owner-a", limit="not-a-number")
        self.assertIn(("@Limit", 50), self.database.first_result.call_args.args[1])

    def test_full_page_returns_next_cursor_short_page_does_not(self):
        self.database.first_result.return_value = [
            moment_row(moment_key="1" * 8 + "-1111-1111-1111-111111111111", cursor_token="cursor-1"),
            moment_row(moment_key="2" * 8 + "-2222-2222-2222-222222222222", cursor_token="cursor-2"),
        ]

        full_page = self.service.list_owner_journal("owner-a", limit=2)
        self.assertEqual(full_page["next_cursor"], "cursor-2")

        self.database.first_result.return_value = [moment_row(cursor_token="cursor-only")]
        short_page = self.service.list_owner_journal("owner-a", limit=2)
        self.assertIsNone(short_page["next_cursor"])

    def test_empty_result_set_is_tolerated(self):
        self.database.first_result.return_value = []

        result = self.service.list_owner_journal("owner-a")

        self.assertEqual(result, {"items": [], "next_cursor": None})

    def test_none_and_falsy_rows_are_skipped_without_error(self):
        self.database.first_result.return_value = [None, {}, moment_row()]

        result = self.service.list_owner_journal("owner-a")

        self.assertEqual(len(result["items"]), 1)

    def test_missing_user_key_raises_without_calling_database(self):
        with self.assertRaises(JournalServiceError):
            self.service.list_owner_journal("")

        self.database.first_result.assert_not_called()


class JournalServiceSaveTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = JournalService(database=self.database)

    def test_valid_save_returns_moment_key_version_and_saved_true(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "moment_key": "22222222-2222-2222-2222-222222222222",
            "version_number": 1,
            "row_version": b"\x00" * 8,
        }

        result = self.service.save_moment("owner-a", "idem-key-1", valid_proposal())

        self.assertEqual(
            result,
            {
                "moment_key": "22222222-2222-2222-2222-222222222222",
                "version": 1,
                "saved": True,
            },
        )
        self.database.first_row.assert_called_once()
        procedure_name = self.database.first_row.call_args.args[0]
        self.assertEqual(procedure_name, "usp_SaveMomentForOwner")

    def test_save_threads_owner_key_idempotency_key_and_proposal_fields(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "moment_key": "33333333-3333-3333-3333-333333333333",
            "version_number": 1,
        }
        proposal = valid_proposal()

        self.service.save_moment("owner-a", "idem-key-2", proposal)

        parameters = dict(self.database.first_row.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "owner-a")
        self.assertEqual(parameters["@IdempotencyKey"], "idem-key-2")
        self.assertEqual(parameters["@MomentKind"], proposal["moment_kind"])
        self.assertEqual(parameters["@Title"], proposal["title"])
        self.assertEqual(parameters["@Narrative"], proposal["narrative"])
        self.assertEqual(parameters["@OccurredPrecision"], proposal["occurred_precision"])

    def test_repeated_idempotency_key_existing_outcome_is_treated_as_saved(self):
        self.database.first_row.return_value = {
            "outcome": "existing",
            "moment_key": "44444444-4444-4444-4444-444444444444",
            "version_number": 1,
        }

        first = self.service.save_moment("owner-a", "idem-key-3", valid_proposal())
        second = self.service.save_moment("owner-a", "idem-key-3", valid_proposal())

        self.assertTrue(first["saved"])
        self.assertTrue(second["saved"])
        self.assertEqual(first["moment_key"], second["moment_key"])
        self.assertEqual(self.database.first_row.call_count, 2)

    def test_false_save_guard_no_row_raises(self):
        self.database.first_row.return_value = None

        with self.assertRaises(JournalServiceError):
            self.service.save_moment("owner-a", "idem-key-4", valid_proposal())

    def test_false_save_guard_missing_moment_key_raises(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "moment_key": None,
            "version_number": 1,
        }

        with self.assertRaises(JournalServiceError):
            self.service.save_moment("owner-a", "idem-key-5", valid_proposal())

    def test_false_save_guard_unrecognized_outcome_raises(self):
        self.database.first_row.return_value = {
            "outcome": "not_found",
            "moment_key": None,
            "version_number": None,
        }

        with self.assertRaises(JournalServiceError):
            self.service.save_moment("owner-a", "idem-key-6", valid_proposal())

    def test_false_save_guard_never_reports_saved_true_on_error(self):
        self.database.first_row.return_value = {"outcome": "changed"}

        try:
            self.service.save_moment("owner-a", "idem-key-7", valid_proposal())
            self.fail("Expected JournalServiceError")
        except JournalServiceError as error:
            self.assertEqual(error.code, "changed")

    def test_missing_user_key_or_idempotency_key_raises_without_db_call(self):
        with self.assertRaises(JournalServiceError):
            self.service.save_moment("", "idem-key", valid_proposal())
        with self.assertRaises(JournalServiceError):
            self.service.save_moment("owner-a", "", valid_proposal())

        self.database.first_row.assert_not_called()

    def test_save_never_writes_to_a_second_content_table(self):
        """Save Moment is exactly one call to one stored procedure - no
        second body/content table write happens at the service layer."""
        self.database.first_row.return_value = {
            "outcome": "success",
            "moment_key": "55555555-5555-5555-5555-555555555555",
            "version_number": 1,
        }

        self.service.save_moment("owner-a", "idem-key-8", valid_proposal())

        self.assertEqual(len(self.database.method_calls), 1)
        self.assertEqual(self.database.method_calls[0][0], "first_row")
        self.database.execute_procedure.assert_not_called()
        self.database.last_row.assert_not_called()
        self.database.last_result.assert_not_called()
        self.database.first_result.assert_not_called()


class JournalServiceDefaultDatabaseTests(unittest.TestCase):
    def test_default_database_is_the_module_singleton(self):
        from services.database_service import database_service

        service = JournalService()
        self.assertIs(service.database, database_service)


if __name__ == "__main__":
    unittest.main()
