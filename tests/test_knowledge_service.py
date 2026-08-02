import unittest
from unittest.mock import Mock

from services.knowledge_service import KnowledgeService, KnowledgeServiceError


ITEM_KEY = "11111111-1111-1111-1111-111111111111"
OTHER_ITEM_KEY = "22222222-2222-2222-2222-222222222222"
ROW_VERSION_BYTES = b"\x00\x00\x00\x00\x00\x00\x00\x01"
ROW_VERSION_TOKEN = "0000000000000001"


def list_row(**overrides):
    row = {
        "knowledge_item_key": ITEM_KEY,
        "item_status": "confirmed",
        "classification": "work",
        "current_version_number": 1,
        "confirmed_version_number": 1,
        "confirmed_at_utc": "2026-07-10T00:00:00+00:00",
        "archived_at_utc": None,
        "created_at_utc": "2026-07-01T00:00:00+00:00",
        "updated_at_utc": "2026-07-10T00:00:00+00:00",
        "row_version": ROW_VERSION_BYTES,
        "title": "A confirmed knowledge item",
        "body_format": "plain",
        "authored_via": "typed",
    }
    row.update(overrides)
    return row


def get_row(**overrides):
    row = {
        "knowledge_item_key": ITEM_KEY,
        "item_status": "confirmed",
        "classification": "work",
        "current_version_number": 1,
        "confirmed_version_number": 1,
        "confirmed_at_utc": "2026-07-10T00:00:00+00:00",
        "archived_at_utc": None,
        "created_at_utc": "2026-07-01T00:00:00+00:00",
        "updated_at_utc": "2026-07-10T00:00:00+00:00",
        "row_version": ROW_VERSION_BYTES,
        "version_number": 1,
        "title": "A confirmed knowledge item",
        "approved_wording": "The approved canonical wording.",
        "original_member_wording": "The approved canonical wording.",
        "body_format": "plain",
        "authored_via": "typed",
        "saved_at_utc": "2026-07-10T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def history_row(**overrides):
    row = {
        "version_number": 1,
        "title": "A confirmed knowledge item",
        "body_format": "plain",
        "authored_via": "typed",
        "saved_at_utc": "2026-07-10T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def valid_fields(**overrides):
    fields = {
        "title": "Systems Engineering",
        "approved_wording": "You led a system architecture effort.",
        "original_wording": "You led a system architecture effort.",
        "body_format": "plain",
        "classification": "work",
        "authored_via": "typed",
        "confirm": False,
    }
    fields.update(overrides)
    return fields


def count_result(total_count):
    return [{"total_count": total_count}]


class KnowledgeServiceListTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = KnowledgeService(database=self.database)

    def test_list_shapes_items_with_exact_fields(self):
        self.database.execute_procedure.return_value = [[list_row()], count_result(1)]

        result = self.service.list_knowledge_items_for_owner("member-a")

        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(
            set(item),
            {
                "item_key",
                "status",
                "classification",
                "current_version",
                "confirmed_version",
                "confirmed_at",
                "archived_at",
                "created_at",
                "updated_at",
                "version_token",
                "title",
                "body_format",
                "authored_via",
            },
        )
        self.assertEqual(item["item_key"], ITEM_KEY)
        self.assertEqual(item["version_token"], ROW_VERSION_TOKEN)
        self.assertEqual(result.total_count, 1)

    def test_list_threads_the_exact_user_key_and_include_archived(self):
        self.database.execute_procedure.return_value = [[], count_result(0)]

        self.service.list_knowledge_items_for_owner("member-a", include_archived=True)

        procedure_name = self.database.execute_procedure.call_args.args[0]
        parameters = self.database.execute_procedure.call_args.args[1]
        self.assertEqual(procedure_name, "usp_ListKnowledgeItemsForOwner")
        self.assertEqual(
            parameters, [("@UserKey", "member-a"), ("@IncludeArchived", 1)]
        )

    def test_list_default_excludes_archived(self):
        self.database.execute_procedure.return_value = [[], count_result(0)]

        self.service.list_knowledge_items_for_owner("member-a")

        parameters = self.database.execute_procedure.call_args.args[1]
        self.assertIn(("@IncludeArchived", 0), parameters)

    def test_list_empty_result_is_tolerated(self):
        self.database.execute_procedure.return_value = [[], count_result(0)]

        result = self.service.list_knowledge_items_for_owner("member-a")

        self.assertEqual(result.items, [])
        self.assertEqual(result.total_count, 0)

    def test_list_superset_row_is_rejected(self):
        """Exact-shape discipline (owner_home_service's _require_exact_fields):
        a row carrying one extra, unrecognized column is rejected outright,
        not silently passed through with the extra field dropped."""
        self.database.execute_procedure.return_value = [
            [list_row(unexpected_extra_column="should not be here")],
            count_result(1),
        ]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(context.exception.code, "invalid")

    def test_list_row_missing_a_field_is_rejected(self):
        row = list_row()
        del row["title"]
        self.database.execute_procedure.return_value = [[row], count_result(1)]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(context.exception.code, "invalid")

    def test_list_bound_of_200_items_is_enforced(self):
        rows = [
            list_row(knowledge_item_key=f"{index:08x}-0000-0000-0000-000000000000")
            for index in range(201)
        ]
        self.database.execute_procedure.return_value = [rows, count_result(201)]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(context.exception.code, "invalid")

    def test_list_exactly_200_items_is_accepted(self):
        rows = [
            list_row(knowledge_item_key=f"{index:08x}-0000-0000-0000-000000000000")
            for index in range(200)
        ]
        self.database.execute_procedure.return_value = [rows, count_result(200)]

        result = self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(len(result.items), 200)
        self.assertEqual(result.total_count, 200)

    def test_total_count_can_exceed_the_200_item_cap(self):
        """BLOCKER 2 correction: the true total is independent of the TOP
        (200) bound on the returned rows themselves."""
        rows = [
            list_row(knowledge_item_key=f"{index:08x}-0000-0000-0000-000000000000")
            for index in range(200)
        ]
        self.database.execute_procedure.return_value = [rows, count_result(543)]

        result = self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(len(result.items), 200)
        self.assertEqual(result.total_count, 543)

    def test_missing_count_result_set_defaults_total_count_to_zero(self):
        """Mirrors the database's own no-profile-resolved case (the
        procedure RETURNs before either SELECT): zero result sets, zero
        items, zero true total — never a guess."""
        self.database.execute_procedure.return_value = []

        result = self.service.list_knowledge_items_for_owner("member-a")

        self.assertEqual(result.items, [])
        self.assertEqual(result.total_count, 0)

    def test_count_result_superset_row_is_rejected(self):
        self.database.execute_procedure.return_value = [
            [],
            [{"total_count": 3, "unexpected_extra_column": "nope"}],
        ]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(context.exception.code, "invalid")

    def test_count_result_with_more_than_one_row_is_rejected(self):
        self.database.execute_procedure.return_value = [
            [],
            [{"total_count": 1}, {"total_count": 2}],
        ]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(context.exception.code, "invalid")

    def test_negative_total_count_is_rejected(self):
        self.database.execute_procedure.return_value = [[], count_result(-1)]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("member-a")
        self.assertEqual(context.exception.code, "invalid")

    def test_missing_user_key_raises_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.list_knowledge_items_for_owner("")
        self.assertEqual(context.exception.code, "no_identity")
        self.database.execute_procedure.assert_not_called()

    def test_non_string_user_key_raises_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError):
            self.service.list_knowledge_items_for_owner(None)
        self.database.execute_procedure.assert_not_called()

    def test_forged_user_key_style_input_is_passed_through_unchanged(self):
        """The service never substitutes, derives, or drops the given
        user_key — whatever string is passed (real or forged/unresolvable)
        reaches the procedure call exactly once, verbatim. Authorization is
        the procedure's job, proven separately by the SQL verifier."""
        self.database.execute_procedure.return_value = [[], count_result(0)]

        self.service.list_knowledge_items_for_owner("forged-user-key-does-not-exist")

        parameters = dict(self.database.execute_procedure.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "forged-user-key-does-not-exist")


class KnowledgeServiceGetTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = KnowledgeService(database=self.database)

    def test_get_shapes_item_and_history_with_exact_fields(self):
        self.database.execute_procedure.return_value = [
            [get_row()],
            [history_row()],
        ]

        result = self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)

        self.assertEqual(
            set(result),
            {
                "item_key",
                "status",
                "classification",
                "current_version",
                "confirmed_version",
                "confirmed_at",
                "archived_at",
                "created_at",
                "updated_at",
                "version_token",
                "version",
                "title",
                "approved_wording",
                "original_member_wording",
                "body_format",
                "authored_via",
                "saved_at",
                "history",
            },
        )
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(
            set(result["history"][0]),
            {"version", "title", "body_format", "authored_via", "saved_at"},
        )

    def test_get_threads_the_exact_user_key_and_item_key(self):
        self.database.execute_procedure.return_value = [[get_row()], []]

        self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)

        procedure_name = self.database.execute_procedure.call_args.args[0]
        parameters = dict(self.database.execute_procedure.call_args.args[1])
        self.assertEqual(procedure_name, "usp_GetKnowledgeItemForOwner")
        self.assertEqual(parameters["@UserKey"], "member-a")
        self.assertEqual(parameters["@KnowledgeItemKey"], ITEM_KEY)

    def test_get_empty_item_result_raises_not_found(self):
        self.database.execute_procedure.return_value = [[], []]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)
        self.assertEqual(context.exception.code, "not_found")

    def test_get_wrong_result_set_count_is_rejected(self):
        self.database.execute_procedure.return_value = [[get_row()]]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)
        self.assertEqual(context.exception.code, "invalid")

    def test_get_superset_row_is_rejected(self):
        self.database.execute_procedure.return_value = [
            [get_row(unexpected_extra_column="nope")],
            [],
        ]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)
        self.assertEqual(context.exception.code, "invalid")

    def test_get_history_superset_row_is_rejected(self):
        self.database.execute_procedure.return_value = [
            [get_row()],
            [history_row(unexpected_extra_column="nope")],
        ]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)
        self.assertEqual(context.exception.code, "invalid")

    def test_get_history_bound_of_50_versions_is_enforced(self):
        self.database.execute_procedure.return_value = [
            [get_row()],
            [history_row(version_number=index + 1) for index in range(51)],
        ]

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)
        self.assertEqual(context.exception.code, "invalid")

    def test_get_history_exactly_50_versions_is_accepted(self):
        """Test gap 14: the boundary itself (exactly 50, matching the
        procedure's TOP (50)) must be accepted — only 51+ is a contract
        violation."""
        self.database.execute_procedure.return_value = [
            [get_row()],
            [history_row(version_number=index + 1) for index in range(50)],
        ]

        result = self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)
        self.assertEqual(len(result["history"]), 50)

    def test_invalid_item_key_raises_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("member-a", "not-a-uuid")
        self.assertEqual(context.exception.code, "invalid")
        self.database.execute_procedure.assert_not_called()

    def test_missing_user_key_raises_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.get_knowledge_item_for_owner("", ITEM_KEY)
        self.assertEqual(context.exception.code, "no_identity")
        self.database.execute_procedure.assert_not_called()


class KnowledgeServiceSaveTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = KnowledgeService(database=self.database)

    def test_valid_save_returns_item_key_status_and_saved_true(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
        }

        result = self.service.save_knowledge_item_for_owner(
            "member-a", "idem-key-1", valid_fields()
        )

        self.assertEqual(
            result,
            {
                "item_key": ITEM_KEY,
                "status": "unfinished",
                "version_token": ROW_VERSION_TOKEN,
                "saved": True,
            },
        )
        procedure_name = self.database.first_row.call_args.args[0]
        self.assertEqual(procedure_name, "usp_SaveKnowledgeItemForOwner")

    def test_save_threads_the_exact_user_key_idempotency_key_and_fields(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
        }
        fields = valid_fields()

        self.service.save_knowledge_item_for_owner("member-a", "idem-key-2", fields)

        parameters = dict(self.database.first_row.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "member-a")
        self.assertEqual(parameters["@IdempotencyKey"], "idem-key-2")
        self.assertEqual(parameters["@Title"], fields["title"])
        self.assertEqual(parameters["@ApprovedWording"], fields["approved_wording"])
        self.assertEqual(parameters["@OriginalWording"], fields["original_wording"])
        self.assertEqual(parameters["@BodyFormat"], fields["body_format"])
        self.assertEqual(parameters["@Classification"], fields["classification"])
        self.assertEqual(parameters["@AuthoredVia"], fields["authored_via"])
        self.assertEqual(parameters["@Confirm"], 0)

    def test_repeated_idempotency_key_existing_outcome_is_treated_as_saved(self):
        self.database.first_row.return_value = {
            "outcome": "existing",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
        }

        first = self.service.save_knowledge_item_for_owner(
            "member-a", "idem-key-3", valid_fields()
        )
        second = self.service.save_knowledge_item_for_owner(
            "member-a", "idem-key-3", valid_fields()
        )

        self.assertTrue(first["saved"])
        self.assertTrue(second["saved"])
        self.assertEqual(first["item_key"], second["item_key"])

    def test_false_save_guard_missing_item_key_raises_not_found(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": None,
            "item_status": None,
            "row_version": None,
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-4", valid_fields()
            )
        self.assertEqual(context.exception.code, "not_found")

    def test_false_save_guard_unrecognized_outcome_raises_not_found(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "knowledge_item_key": None,
            "item_status": None,
            "row_version": None,
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-5", valid_fields()
            )
        self.assertEqual(context.exception.code, "not_found")

    def test_forged_owner_not_found_outcome_never_reports_saved_true(self):
        """Mirrors the database's own not_found outcome for a forged/
        unresolvable @UserKey: the service never reports saved: True."""
        self.database.first_row.return_value = {
            "outcome": "not_found",
            "knowledge_item_key": None,
            "item_status": None,
            "row_version": None,
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "forged-user-key-does-not-exist", "idem-key-6", valid_fields()
            )
        self.assertEqual(context.exception.code, "not_found")

    def test_save_result_superset_row_is_rejected(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
            "unexpected_extra_column": "nope",
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-7", valid_fields()
            )
        self.assertEqual(context.exception.code, "invalid")

    def test_missing_title_raises_required_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-8", valid_fields(title="")
            )
        self.assertEqual(context.exception.code, "required")
        self.database.first_row.assert_not_called()

    def test_missing_approved_wording_raises_required(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-9", valid_fields(approved_wording="")
            )
        self.assertEqual(context.exception.code, "required")
        self.database.first_row.assert_not_called()

    def test_missing_original_wording_raises_required(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-10", valid_fields(original_wording="")
            )
        self.assertEqual(context.exception.code, "required")
        self.database.first_row.assert_not_called()

    def test_title_over_utf16_length_cap_raises_too_long(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-11", valid_fields(title="x" * 161)
            )
        self.assertEqual(context.exception.code, "too_long")
        self.database.first_row.assert_not_called()

    def test_title_at_utf16_length_cap_is_accepted(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
        }

        self.service.save_knowledge_item_for_owner(
            "member-a", "idem-key-12", valid_fields(title="x" * 160)
        )
        self.database.first_row.assert_called_once()

    def test_wording_over_utf16_length_cap_raises_too_long(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a",
                "idem-key-13",
                valid_fields(approved_wording="x" * 8001),
            )
        self.assertEqual(context.exception.code, "too_long")
        self.database.first_row.assert_not_called()

    def test_utf16_surrogate_pair_counts_as_two_units(self):
        """An astral character (e.g. an emoji) is one Python code point but
        two UTF-16 code units — the same boundary SQL Server's
        nvarchar/DATALENGTH and the browser's maxlength use. 80 emoji is 160
        UTF-16 units, exactly at the title cap; 81 exceeds it."""
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
        }
        self.service.save_knowledge_item_for_owner(
            "member-a", "idem-key-14", valid_fields(title="\U0001F600" * 80)
        )
        self.database.first_row.assert_called_once()

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-15", valid_fields(title="\U0001F600" * 81)
            )
        self.assertEqual(context.exception.code, "too_long")

    def test_invalid_classification_raises_invalid_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-16", valid_fields(classification="secret")
            )
        self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_invalid_body_format_raises_invalid_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-17", valid_fields(body_format="markdown")
            )
        self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_invalid_authored_via_raises_invalid_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "idem-key-18", valid_fields(authored_via="dictated")
            )
        self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_missing_idempotency_key_raises_required_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner("member-a", "", valid_fields())
        self.assertEqual(context.exception.code, "required")
        self.database.first_row.assert_not_called()

    def test_idempotency_key_over_200_chars_raises_too_long(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "x" * 201, valid_fields()
            )
        self.assertEqual(context.exception.code, "too_long")
        self.database.first_row.assert_not_called()

    def test_idempotency_key_utf16_surrogate_pair_counts_as_two_units(self):
        """MINOR 11 correction: the bound is UTF-16 code units (matching the
        migration's DATALENGTH(@IdempotencyKey)/2 guard), not Python's
        len() — 100 emoji is 200 UTF-16 units, exactly at the cap; 101
        exceeds it, even though len() would report only 101/101.5 code
        points either way."""
        self.database.first_row.return_value = {
            "outcome": "success",
            "knowledge_item_key": ITEM_KEY,
            "item_status": "unfinished",
            "row_version": ROW_VERSION_BYTES,
        }
        self.service.save_knowledge_item_for_owner(
            "member-a", "\U0001F600" * 100, valid_fields()
        )
        self.database.first_row.assert_called_once()

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner(
                "member-a", "\U0001F600" * 101, valid_fields()
            )
        self.assertEqual(context.exception.code, "too_long")

    def test_missing_user_key_raises_no_identity_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner("", "idem-key-19", valid_fields())
        self.assertEqual(context.exception.code, "no_identity")
        self.database.first_row.assert_not_called()

    def test_non_dict_fields_raises_required(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.save_knowledge_item_for_owner("member-a", "idem-key-20", None)
        self.assertEqual(context.exception.code, "required")
        self.database.first_row.assert_not_called()

    def test_forged_user_key_style_input_is_passed_through_unchanged(self):
        self.database.first_row.return_value = {
            "outcome": "not_found",
            "knowledge_item_key": None,
            "item_status": None,
            "row_version": None,
        }

        with self.assertRaises(KnowledgeServiceError):
            self.service.save_knowledge_item_for_owner(
                "forged-user-key-does-not-exist", "idem-key-21", valid_fields()
            )

        parameters = dict(self.database.first_row.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "forged-user-key-does-not-exist")


class KnowledgeServiceUpdateTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = KnowledgeService(database=self.database)

    def test_valid_update_returns_version_and_updated_true(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "version_number": 2,
            "row_version": ROW_VERSION_BYTES,
        }

        result = self.service.update_knowledge_item_for_owner(
            "member-a", ITEM_KEY, ROW_VERSION_TOKEN, valid_fields()
        )

        self.assertEqual(
            result,
            {"version": 2, "version_token": ROW_VERSION_TOKEN, "updated": True},
        )
        procedure_name = self.database.first_row.call_args.args[0]
        self.assertEqual(procedure_name, "usp_UpdateKnowledgeItemForOwner")

    def test_update_threads_the_exact_parameters(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "version_number": 2,
            "row_version": ROW_VERSION_BYTES,
        }
        fields = valid_fields()

        self.service.update_knowledge_item_for_owner(
            "member-a", ITEM_KEY, ROW_VERSION_TOKEN, fields
        )

        parameters = dict(self.database.first_row.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "member-a")
        self.assertEqual(parameters["@KnowledgeItemKey"], ITEM_KEY)
        self.assertEqual(parameters["@ExpectedRowVersion"], ROW_VERSION_BYTES)
        self.assertEqual(parameters["@Title"], fields["title"])
        self.assertEqual(parameters["@ApprovedWording"], fields["approved_wording"])
        self.assertEqual(parameters["@BodyFormat"], fields["body_format"])
        self.assertEqual(parameters["@Classification"], fields["classification"])
        self.assertEqual(parameters["@Confirm"], 0)
        self.assertNotIn("@AuthoredVia", parameters)
        self.assertNotIn("@OriginalWording", parameters)

    def test_stale_row_version_raises_changed(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "version_number": None,
            "row_version": None,
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN, valid_fields()
            )
        self.assertEqual(context.exception.code, "changed")

    def test_forged_user_key_changed_outcome_is_never_reported_as_updated(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "version_number": None,
            "row_version": None,
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "forged-user-key-does-not-exist",
                ITEM_KEY,
                ROW_VERSION_TOKEN,
                valid_fields(),
            )
        self.assertEqual(context.exception.code, "changed")

        parameters = dict(self.database.first_row.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "forged-user-key-does-not-exist")

    def test_update_result_superset_row_is_rejected(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "version_number": 2,
            "row_version": ROW_VERSION_BYTES,
            "unexpected_extra_column": "nope",
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN, valid_fields()
            )
        self.assertEqual(context.exception.code, "invalid")

    def test_invalid_expected_version_token_raises_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "member-a", ITEM_KEY, "not-a-version-token", valid_fields()
            )
        self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_invalid_item_key_raises_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "member-a", "not-a-uuid", ROW_VERSION_TOKEN, valid_fields()
            )
        self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_title_over_length_cap_raises_too_long_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN, valid_fields(title="x" * 161)
            )
        self.assertEqual(context.exception.code, "too_long")
        self.database.first_row.assert_not_called()

    def test_wording_over_length_cap_raises_too_long_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "member-a",
                ITEM_KEY,
                ROW_VERSION_TOKEN,
                valid_fields(approved_wording="x" * 8001),
            )
        self.assertEqual(context.exception.code, "too_long")
        self.database.first_row.assert_not_called()

    def test_missing_user_key_raises_no_identity_without_calling_database(self):
        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.update_knowledge_item_for_owner(
                "", ITEM_KEY, ROW_VERSION_TOKEN, valid_fields()
            )
        self.assertEqual(context.exception.code, "no_identity")
        self.database.first_row.assert_not_called()


class KnowledgeServiceArchiveRestoreDeleteTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.service = KnowledgeService(database=self.database)

    def test_archive_success_returns_version_token_and_archived_true(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "row_version": ROW_VERSION_BYTES,
        }

        result = self.service.archive_knowledge_item_for_owner(
            "member-a", ITEM_KEY, ROW_VERSION_TOKEN
        )

        self.assertEqual(
            result, {"version_token": ROW_VERSION_TOKEN, "archived": True}
        )
        procedure_name = self.database.first_row.call_args.args[0]
        self.assertEqual(procedure_name, "usp_ArchiveKnowledgeItemForOwner")

    def test_archive_changed_outcome_raises_changed(self):
        self.database.first_row.return_value = {"outcome": "changed", "row_version": None}

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.archive_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN
            )
        self.assertEqual(context.exception.code, "changed")

    def test_archive_result_superset_row_is_rejected(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "row_version": ROW_VERSION_BYTES,
            "unexpected_extra_column": "nope",
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.archive_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN
            )
        self.assertEqual(context.exception.code, "invalid")

    def test_restore_success_returns_version_token_and_restored_true(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "row_version": ROW_VERSION_BYTES,
        }

        result = self.service.restore_knowledge_item_for_owner(
            "member-a", ITEM_KEY, ROW_VERSION_TOKEN
        )

        self.assertEqual(
            result, {"version_token": ROW_VERSION_TOKEN, "restored": True}
        )
        procedure_name = self.database.first_row.call_args.args[0]
        self.assertEqual(procedure_name, "usp_RestoreKnowledgeItemForOwner")

    def test_restore_changed_outcome_raises_changed(self):
        self.database.first_row.return_value = {"outcome": "changed", "row_version": None}

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.restore_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN
            )
        self.assertEqual(context.exception.code, "changed")

    def test_delete_success_returns_deleted_version_count_and_deleted_true(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "deleted_version_count": 3,
        }

        result = self.service.delete_knowledge_item_for_owner(
            "member-a", ITEM_KEY, ROW_VERSION_TOKEN
        )

        self.assertEqual(
            result, {"deleted_version_count": 3, "deleted": True}
        )
        procedure_name = self.database.first_row.call_args.args[0]
        self.assertEqual(procedure_name, "usp_DeleteKnowledgeItemForOwner")

    def test_delete_changed_outcome_raises_changed(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "deleted_version_count": None,
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.delete_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN
            )
        self.assertEqual(context.exception.code, "changed")

    def test_delete_result_superset_row_is_rejected(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "deleted_version_count": 1,
            "unexpected_extra_column": "nope",
        }

        with self.assertRaises(KnowledgeServiceError) as context:
            self.service.delete_knowledge_item_for_owner(
                "member-a", ITEM_KEY, ROW_VERSION_TOKEN
            )
        self.assertEqual(context.exception.code, "invalid")

    def test_forged_user_key_never_bypasses_the_passed_key_on_any_fenced_write(self):
        self.database.first_row.return_value = {"outcome": "changed", "row_version": None}

        for method_name in (
            "archive_knowledge_item_for_owner",
            "restore_knowledge_item_for_owner",
        ):
            with self.subTest(method=method_name):
                method = getattr(self.service, method_name)
                with self.assertRaises(KnowledgeServiceError):
                    method(
                        "forged-user-key-does-not-exist", ITEM_KEY, ROW_VERSION_TOKEN
                    )
                parameters = dict(self.database.first_row.call_args.args[1])
                self.assertEqual(
                    parameters["@UserKey"], "forged-user-key-does-not-exist"
                )

        self.database.first_row.return_value = {
            "outcome": "changed",
            "deleted_version_count": None,
        }
        with self.assertRaises(KnowledgeServiceError):
            self.service.delete_knowledge_item_for_owner(
                "forged-user-key-does-not-exist", ITEM_KEY, ROW_VERSION_TOKEN
            )
        parameters = dict(self.database.first_row.call_args.args[1])
        self.assertEqual(parameters["@UserKey"], "forged-user-key-does-not-exist")

    def test_invalid_expected_version_token_raises_without_calling_database(self):
        for method_name in (
            "archive_knowledge_item_for_owner",
            "restore_knowledge_item_for_owner",
            "delete_knowledge_item_for_owner",
        ):
            with self.subTest(method=method_name):
                method = getattr(self.service, method_name)
                with self.assertRaises(KnowledgeServiceError) as context:
                    method("member-a", ITEM_KEY, "not-a-version-token")
                self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_invalid_item_key_raises_without_calling_database(self):
        for method_name in (
            "archive_knowledge_item_for_owner",
            "restore_knowledge_item_for_owner",
            "delete_knowledge_item_for_owner",
        ):
            with self.subTest(method=method_name):
                method = getattr(self.service, method_name)
                with self.assertRaises(KnowledgeServiceError) as context:
                    method("member-a", "not-a-uuid", ROW_VERSION_TOKEN)
                self.assertEqual(context.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_missing_user_key_raises_no_identity_without_calling_database(self):
        for method_name in (
            "archive_knowledge_item_for_owner",
            "restore_knowledge_item_for_owner",
            "delete_knowledge_item_for_owner",
        ):
            with self.subTest(method=method_name):
                method = getattr(self.service, method_name)
                with self.assertRaises(KnowledgeServiceError) as context:
                    method("", ITEM_KEY, ROW_VERSION_TOKEN)
                self.assertEqual(context.exception.code, "no_identity")
        self.database.first_row.assert_not_called()


class KnowledgeServiceCheckpointFixtureStillWorksTests(unittest.TestCase):
    """The existing checkpoint fixture (used by workshop_routes.py behind
    PEERSLATE_WORKSHOP_ENABLED) is untouched by the real-method wiring
    above; this is a narrow smoke check that it still behaves as before."""

    def test_checkpoint_still_returns_a_fixture_without_touching_the_database(self):
        from types import SimpleNamespace

        database = Mock()
        service = KnowledgeService(database=database)

        checkpoint = service.get_my_information_checkpoint(
            SimpleNamespace(display_name="A Member", user_key="member-a")
        )

        self.assertEqual(checkpoint.owner_display_name, "A Member")
        self.assertGreater(len(checkpoint.items), 0)
        database.first_result.assert_not_called()
        database.first_row.assert_not_called()
        database.execute_procedure.assert_not_called()


class KnowledgeServiceDefaultDatabaseTests(unittest.TestCase):
    def test_default_database_is_the_module_singleton(self):
        from services.database_service import database_service

        service = KnowledgeService()
        self.assertIs(service.database, database_service)


class KnowledgeServiceTwoOwnerByteCanaryTests(unittest.TestCase):
    """Test gap 8: two mocked row payloads through the SAME service
    instance, back to back, prove there is no shared/cached state at the
    serialization layer that could bleed one owner's bytes into another's
    result."""

    def setUp(self):
        self.database = Mock()
        self.service = KnowledgeService(database=self.database)

    def test_list_serialization_does_not_leak_between_two_owners(self):
        self.database.execute_procedure.return_value = [
            [list_row(knowledge_item_key=ITEM_KEY, title="Owner A's private title")],
            count_result(1),
        ]
        result_a = self.service.list_knowledge_items_for_owner("member-a")

        self.database.execute_procedure.return_value = [
            [list_row(knowledge_item_key=OTHER_ITEM_KEY, title="Owner B's private title")],
            count_result(1),
        ]
        result_b = self.service.list_knowledge_items_for_owner("member-b")

        self.assertEqual(result_a.items[0]["title"], "Owner A's private title")
        self.assertEqual(result_b.items[0]["title"], "Owner B's private title")
        a_titles = [item["title"] for item in result_a.items]
        b_titles = [item["title"] for item in result_b.items]
        self.assertNotIn("Owner B's private title", a_titles)
        self.assertNotIn("Owner A's private title", b_titles)
        self.assertNotEqual(result_a.items[0]["item_key"], result_b.items[0]["item_key"])

    def test_get_serialization_does_not_leak_between_two_owners(self):
        self.database.execute_procedure.return_value = [
            [
                get_row(
                    knowledge_item_key=ITEM_KEY,
                    title="Owner A get title",
                    approved_wording="Owner A's confidential wording.",
                )
            ],
            [],
        ]
        result_a = self.service.get_knowledge_item_for_owner("member-a", ITEM_KEY)

        self.database.execute_procedure.return_value = [
            [
                get_row(
                    knowledge_item_key=OTHER_ITEM_KEY,
                    title="Owner B get title",
                    approved_wording="Owner B's confidential wording.",
                )
            ],
            [],
        ]
        result_b = self.service.get_knowledge_item_for_owner("member-b", OTHER_ITEM_KEY)

        self.assertEqual(result_a["title"], "Owner A get title")
        self.assertEqual(result_b["title"], "Owner B get title")
        self.assertEqual(result_a["approved_wording"], "Owner A's confidential wording.")
        self.assertEqual(result_b["approved_wording"], "Owner B's confidential wording.")
        self.assertNotEqual(result_a["title"], result_b["title"])
        self.assertNotEqual(result_a["approved_wording"], result_b["approved_wording"])
        self.assertNotEqual(result_a["item_key"], result_b["item_key"])


if __name__ == "__main__":
    unittest.main()
