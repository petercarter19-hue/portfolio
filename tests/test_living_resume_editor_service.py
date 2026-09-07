import hashlib
import json
import unittest
from datetime import date
from unittest.mock import MagicMock

from services.database_service import DatabaseServiceError
from services.living_resume_editor_service import (
    LivingResumeEditorConflictError,
    LivingResumeEditorService,
    LivingResumeEditorUnavailableError,
    LivingResumeEditorValidationError,
    normalize_command,
    utf16_length,
)


COMMAND_ID = "00000000-0000-4000-8000-000000000001"
RECORD_KEY = "00000000-0000-4000-8000-000000000002"
PARENT_KEY = "00000000-0000-4000-8000-000000000003"
VERSION = "000000000000002a"


def role_payload(**overrides):
    payload = {
        "command_id": COMMAND_ID,
        "type": "create_role",
        "record_key": RECORD_KEY,
        "parent_key": None,
        "expected_version": None,
        "values": {
            "role_title": "Engineer",
            "employer_name": "PeerSlate",
            "location_text": None,
            "summary": "Built private tools",
            "start_date": "2026-09-06",
            "end_date": None,
            "date_precision": "month",
            "employment_type": "full_time",
            "current_role": True,
        },
    }
    payload.update(overrides)
    return payload


def editor_sets(*, role=True):
    return [
        [{"profile_key": PARENT_KEY, "profile_slug": "pete", "display_name": "Pete"}],
        ([{
            "record_key": RECORD_KEY,
            "role_title": "Engineer",
            "employer_name": "PeerSlate",
            "location_text": None,
            "summary": "Built private tools",
            "start_date": date(2026, 9, 1),
            "end_date": None,
            "date_precision": "month",
            "employment_type": "full_time",
            "current_role": 1,
            "row_version": bytes.fromhex(VERSION),
            "editable": 1,
            "blocked_reason": None,
        }] if role else []),
        [],
        [],
        [],
    ]


class LivingResumeEditorValidationTests(unittest.TestCase):
    def test_utf16_limits_count_non_bmp_text_as_two_units(self):
        self.assertEqual(utf16_length("a😀"), 3)

    def test_normalizes_full_role_and_hashes_exact_utf16_json(self):
        normalized, command_json, digest = normalize_command(role_payload())

        self.assertEqual(normalized["values"]["start_date"], "2026-09-01")
        self.assertEqual(json.loads(command_json), normalized)
        self.assertEqual(digest, hashlib.sha256(command_json.encode("utf-16-le")).hexdigest())

    def test_rejects_browser_control_of_any_unknown_envelope_or_value_field(self):
        cases = (
            role_payload(owner_profile_id=12),
            role_payload(values={**role_payload()["values"], "visibility": "public"}),
            role_payload(values={**role_payload()["values"], "approved_text": "unsafe"}),
        )
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(payload)

    def test_non_text_command_type_and_invalid_unicode_are_typed_validation_errors(self):
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_command(role_payload(type=[]))
        values = {**role_payload()["values"], "summary": "bad\ud800text"}
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_command(role_payload(values=values))

    def test_command_id_must_be_canonical_uuid_v4(self):
        for value in ("ABC", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA", "00000000-0000-1000-8000-000000000000"):
            with self.subTest(value=value):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(role_payload(command_id=value))

    def test_update_and_remove_require_parent_version_and_cannot_reparent(self):
        for payload in (
            role_payload(type="update_role", expected_version=None),
            role_payload(type="update_role", expected_version=VERSION, parent_key=PARENT_KEY),
            role_payload(type="remove_role", expected_version=VERSION, values={"role_title": "x"}),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(payload)

    def test_only_create_accomplishment_accepts_parent_key(self):
        payload = {
            "command_id": COMMAND_ID,
            "type": "create_accomplishment",
            "record_key": RECORD_KEY,
            "parent_key": PARENT_KEY,
            "expected_version": None,
            "values": {"wording": "Shipped it", "metric_value": "2x", "metric_label": None},
        }
        normalized, _, _ = normalize_command(payload)
        self.assertEqual(normalized["parent_key"], PARENT_KEY)

    def test_role_dates_and_current_role_are_consistent(self):
        cases = (
            {"start_date": None, "end_date": "2026-01-01", "current_role": False},
            {"start_date": "2026-02-01", "end_date": "2026-01-01", "current_role": False},
            {"start_date": "2026-01-01", "end_date": "2026-02-01", "current_role": True},
        )
        for changes in cases:
            values = {**role_payload()["values"], **changes}
            with self.subTest(changes=changes):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(role_payload(values=values))

    def test_credential_status_is_explicit_and_legacy_unknown_is_not_a_write_value(self):
        base = {
            "name": "Azure Fundamentals",
            "issuer": "Microsoft",
            "identifier": None,
            "issue_date": None,
            "expiration_date": None,
            "verification_url": None,
        }
        for status in (None, "unknown"):
            values = {**base, "completion_status": status}
            with self.subTest(status=status):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(role_payload(type="create_credential", values=values))

    def test_credential_completion_controls_dates_and_url(self):
        base = {
            "name": "Azure Fundamentals",
            "issuer": "Microsoft",
            "identifier": None,
            "issue_date": "2026-01-02",
            "expiration_date": None,
            "verification_url": "https://example.test/proof",
            "completion_status": "completed",
        }
        normalized, _, _ = normalize_command(role_payload(type="create_credential", values=base))
        self.assertEqual(normalized["values"]["completion_status"], "completed")
        for changes in (
            {"completion_status": "planned"},
            {"issue_date": None},
            {"verification_url": "javascript:alert(1)"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(
                        role_payload(type="create_credential", values={**base, **changes})
                    )

    def test_malformed_bracketed_verification_url_is_a_typed_validation_error(self):
        values = {
            "name": "Azure Fundamentals",
            "issuer": "Microsoft",
            "identifier": None,
            "issue_date": "2026-01-02",
            "expiration_date": None,
            "verification_url": "http://[",
            "completion_status": "completed",
        }
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_command(role_payload(type="create_credential", values=values))

    def test_eight_thousand_unit_long_fields_survive_create_and_update_normalization(self):
        long_text = "x" * 8000
        cases = (
            role_payload(values={**role_payload()["values"], "summary": long_text}),
            role_payload(
                type="update_role",
                expected_version=VERSION,
                values={**role_payload()["values"], "summary": long_text},
            ),
            role_payload(
                type="create_accomplishment",
                parent_key=PARENT_KEY,
                values={"wording": long_text, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="update_accomplishment",
                expected_version=VERSION,
                values={"wording": long_text, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="create_skill", values={"name": "SQL", "summary": long_text}
            ),
            role_payload(
                type="update_skill",
                expected_version=VERSION,
                values={"name": "SQL", "summary": long_text},
            ),
        )
        for payload in cases:
            with self.subTest(command_type=payload["type"]):
                normalized, command_json, _ = normalize_command(payload)
                field = "wording" if "accomplishment" in payload["type"] else "summary"
                self.assertEqual(normalized["values"][field], long_text)
                self.assertEqual(json.loads(command_json)["values"][field], long_text)

    def test_long_editor_text_rejects_over_eight_thousand_units_for_create_and_update(self):
        too_long = "x" * 8001
        cases = (
            role_payload(values={**role_payload()["values"], "summary": too_long}),
            role_payload(
                type="update_role",
                expected_version=VERSION,
                values={**role_payload()["values"], "summary": too_long},
            ),
            role_payload(
                type="create_accomplishment",
                parent_key=PARENT_KEY,
                values={"wording": too_long, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="update_accomplishment",
                expected_version=VERSION,
                values={"wording": too_long, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="create_skill", values={"name": "SQL", "summary": too_long}
            ),
            role_payload(
                type="update_skill",
                expected_version=VERSION,
                values={"name": "SQL", "summary": too_long},
            ),
        )
        for payload in cases:
            with self.subTest(command_type=payload["type"]):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(payload)


class LivingResumeEditorServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = MagicMock()
        self.service = LivingResumeEditorService(self.database)

    def test_owner_read_has_five_strict_sections_and_explicit_capabilities(self):
        self.database.execute_procedure.return_value = editor_sets()
        editor = self.service.get_editor("owner-1")

        self.assertEqual(editor["roles"][0]["row_version"], VERSION)
        self.assertEqual(editor["roles"][0]["start_date"], "2026-09-01")
        self.assertIs(editor["roles"][0]["editable"], True)
        self.assertEqual(editor["credentials"], [])
        self.assertIn("create_credential", editor["capabilities"]["commands"])
        self.database.execute_procedure.assert_called_once_with(
            "usp_GetOwnerLivingResumeEditor", (("@UserKey", "owner-1"),)
        )

    def test_commit_binds_only_server_identity_uuid_and_canonical_json(self):
        _, command_json, digest = normalize_command(role_payload())
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": 1,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "create_role",
                "record_key": RECORD_KEY,
                "outcome": "created",
                "record_version": bytes.fromhex(VERSION),
                "replayed": 0,
            }]],
            editor_sets(),
        ]

        result = self.service.commit("owner-1", role_payload())

        self.assertEqual(result["receipt"]["outcome"], "created")
        self.assertEqual(result["current"]["record_key"], RECORD_KEY)
        self.database.execute_procedure.assert_any_call(
            "usp_CommitLivingResumeCommandForOwner",
            (
                ("@UserKey", "owner-1"),
                ("@CommandId", COMMAND_ID),
                ("@CommandJson", command_json),
            ),
        )

    def test_replay_returns_original_receipt_and_current_record(self):
        _, _, digest = normalize_command(role_payload())
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": True,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "create_role",
                "record_key": RECORD_KEY,
                "outcome": "created",
                "record_version": VERSION,
                "replayed": 1,
            }]],
            editor_sets(),
        ]
        result = self.service.commit("owner-1", role_payload())
        self.assertTrue(result["receipt"]["replayed"])
        self.assertEqual(result["current"]["row_version"], VERSION)

    def test_replayed_create_keeps_original_receipt_when_record_was_later_removed(self):
        _, _, digest = normalize_command(role_payload())
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": True,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "create_role",
                "record_key": RECORD_KEY,
                "outcome": "created",
                "record_version": VERSION,
                "replayed": 1,
            }]],
            editor_sets(role=False),
        ]
        result = self.service.commit("owner-1", role_payload())
        self.assertEqual(result["receipt"]["outcome"], "created")
        self.assertIsNone(result["current"])

    def test_changed_conflict_refreshes_only_authorized_current_state(self):
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": 0,
                "error_code": "changed",
                "command_id": None,
                "request_digest": None,
                "command_type": None,
                "record_key": None,
                "outcome": None,
                "record_version": None,
                "replayed": 0,
            }]],
            editor_sets(),
        ]
        payload = role_payload(type="update_role", expected_version="0000000000000001")
        with self.assertRaises(LivingResumeEditorConflictError) as raised:
            self.service.commit("owner-1", payload)
        self.assertEqual(raised.exception.code, "changed")
        self.assertEqual(raised.exception.current["record_key"], RECORD_KEY)

    def test_removed_record_must_be_absent_after_commit(self):
        payload = role_payload(type="remove_role", expected_version=VERSION, values={})
        _, _, digest = normalize_command(payload)
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": 1,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "remove_role",
                "record_key": RECORD_KEY,
                "outcome": "removed",
                "record_version": None,
                "replayed": 0,
            }]],
            editor_sets(role=False),
        ]
        result = self.service.commit("owner-1", payload)
        self.assertIsNone(result["current"])

    def test_database_error_markers_map_without_exposing_sql_text(self):
        cases = {
            "RESUME_EDITOR_NOT_FOUND diagnostic": "not_found",
            "RESUME_EDITOR_PROTECTED diagnostic": "protected",
            "RESUME_EDITOR_IDEMPOTENCY_CONFLICT diagnostic": "idempotency_conflict",
            "something internal": "unavailable",
        }
        for detail, code in cases.items():
            with self.subTest(detail=detail):
                cause = RuntimeError(detail)
                error = DatabaseServiceError("procedure failed")
                error.__cause__ = cause
                self.database.execute_procedure.side_effect = error
                with self.assertRaises(Exception) as raised:
                    self.service.commit("owner-1", role_payload())
                self.assertEqual(raised.exception.code, code)
                self.assertNotIn("diagnostic", str(raised.exception))
                self.database.reset_mock()

    def test_unknown_or_extra_database_shapes_fail_closed(self):
        self.database.execute_procedure.return_value = editor_sets() + [[]]
        with self.assertRaises(LivingResumeEditorUnavailableError):
            self.service.get_editor("owner-1")

    def test_malformed_database_identifiers_and_visibility_state_fail_closed(self):
        malformed_key = editor_sets()
        malformed_key[1][0]["record_key"] = "not-a-uuid"
        self.database.execute_procedure.return_value = malformed_key
        with self.assertRaises(LivingResumeEditorUnavailableError):
            self.service.get_editor("owner-1")

        contradictory_state = editor_sets()
        contradictory_state[1][0]["editable"] = 0
        self.database.execute_procedure.return_value = contradictory_state
        with self.assertRaises(LivingResumeEditorUnavailableError):
            self.service.get_editor("owner-1")


if __name__ == "__main__":
    unittest.main()
