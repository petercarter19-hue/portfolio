"""Disposable-database proof for the Interview telemetry schema (C3/C9/B4).

Runs ONLY against a throwaway database: the connection is taken from
INTERVIEW_TELEMETRY_SQL_PROOF_CONNECTIONSTRING (which must be an
Entra-authenticated administrator connection, Authentication=
ActiveDirectoryDefault, for the authority end-to-end case) and the tool refuses any
database whose name is not explicitly passed via --expect-database, or
whose name looks like production. Nothing here may connect to or alter
production SQL.

Executes, with named results:

  * the B4 hostile matrix (sql_case_1 .. sql_case_17): numeric boundary
    values on both sides of every bound, malformed source-count and
    exception-attribute JSON, canonical-identity form violations,
    resolution/parent-child relationship violations, and concurrent
    duplicate appends with different payloads proving first-row
    immutability;
  * the preserved C3 battery: permission separation both directions,
    silent duplicates, retention boundary (89/91 days), purge batch
    bound, rollback guard both branches, forward idempotency.

Output is one content-free JSON report of named checks.
"""

import argparse
import json
import os
import re
import sys
import threading
import uuid
from pathlib import Path

from mssql_python import connect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from configure_interview_telemetry_sql_authority import (  # noqa: E402
    apply as authority_apply,
    ensure_application_denies,
    ensure_roles_and_grants,
    verify as authority_verify,
)
CONNECTION_ENV = "INTERVIEW_TELEMETRY_SQL_PROOF_CONNECTIONSTRING"
_DATABASE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

FORWARD_SQL = (
    ROOT / "SQL FIles" / "Migrations" / "proposed"
    / "PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql"
)
ROLLBACK_SQL = (
    ROOT / "SQL FIles" / "Migrations" / "proposed"
    / "PS-INTERVIEW-AI-EXTRACT-001_telemetry_rollback.sql"
)

BASE_COUNTS = (
    '{"answer":1,"confirmed_context":0,"history_selection":0,'
    '"member_evidence":3,"question":1,"role_context":0}'
)
ZERO_COUNTS = (
    '{"answer":0,"confirmed_context":0,"history_selection":0,'
    '"member_evidence":0,"question":0,"role_context":0}'
)


def append_arguments(attempt_uuid, **overrides):
    values = {
        "@AttemptUuid": attempt_uuid,
        "@EventKind": "specialist_call",
        "@Outcome": "success",
        "@HttpStatus": 200,
        "@RetryOrdinal": 0,
        "@DurReceiveMs": 0,
        "@DurRetrievalMs": 1,
        "@DurManifestMs": 1,
        "@DurProviderMs": 5,
        "@DurValidateMs": 1,
        "@DurRespondMs": 1,
        "@DurTotalServerMs": 9,
        "@Specialist": "coach",
        "@BundleLabel": "1.0.0+00000000",
        "@BundleContentSha256": "0" * 64,
        "@Composition": None,
        "@ReleaseSetId": "1" * 64,
        "@ParentAttemptUuid": None,
        "@OperationId": None,
        "@FailureState": None,
        "@FailureReason": None,
        "@GuardianRejectionsJson": "[]",
        "@ValidationResult": "passed",
        "@SourceClassCountsJson": BASE_COUNTS,
        "@ProviderInputTokens": 700,
        "@ProviderOutputTokens": 300,
        "@CostMicrousd": 2200,
        "@PricingScheduleId": "2" * 64,
        "@ExceptionClass": None,
        "@ExceptionAttrsJson": None,
    }
    values.update(overrides)
    return values


def failed_arguments(attempt_uuid, exception_class, attrs_json, **overrides):
    values = append_arguments(
        attempt_uuid,
        **{
            "@Outcome": "failed",
            "@HttpStatus": 502,
            "@FailureState": "invalid_output",
            "@FailureReason": "no_json_object",
            "@ValidationResult": "rejected",
            "@ExceptionClass": exception_class,
            "@ExceptionAttrsJson": attrs_json,
        },
    )
    values.update(overrides)
    return values


def parent_arguments(attempt_uuid, **overrides):
    values = append_arguments(
        attempt_uuid,
        **{
            "@EventKind": "composition_parent",
            "@Specialist": None,
            "@Composition": "compare",
            "@BundleLabel": None,
            "@BundleContentSha256": None,
            "@ValidationResult": "not_applicable",
            "@SourceClassCountsJson": ZERO_COUNTS,
            "@ProviderInputTokens": None,
            "@ProviderOutputTokens": None,
            "@CostMicrousd": None,
            "@PricingScheduleId": None,
        },
    )
    values.update(overrides)
    return values


# Correction C3: every governed rejection this proof asserts, by exact
# SQL error number. 547 is a CHECK-constraint violation at INSERT; the
# 500xx numbers are the append procedure's own named THROWs. A case with
# no entry here fails rather than passing silently.
GOVERNED_ERROR_NUMBERS = frozenset({547, 2627, 2601}) | frozenset(
    range(50010, 50060)
)

EXPECTED_ERRORS = {
    # numeric bounds
    "sql_case_1_status_99": 50020,
    "sql_case_1_status_600": 50020,
    "sql_case_1_status_999": 50020,
    "sql_case_2_retry_minus1": 50021,
    "sql_case_2_retry_16": 50021,
    "sql_case_2_retry_999": 50021,
    "sql_case_3_duration_minus1": 50022,
    "sql_case_3_duration_over": 50022,
    "sql_case_3_total_below_stage": 50023,
    "sql_case_4_reply_chars_minus1": 50017,
    "sql_case_4_reply_chars_100001": 50017,
    "sql_case_5_exception_status_99": 50016,
    "sql_case_5_exception_status_600": 50016,
    "sql_case_5_exception_status_999": 50016,
    # per-class attribute allowlists
    "sql_case_6_timeout_with_status": 50032,
    "sql_case_6_rejected_with_reply_chars": 50015,
    "sql_case_6_validation_with_status": 50015,
    "sql_case_6_runtime_with_attrs": 50032,
    "sql_case_6_legacy_class_name": 50030,
    # source-count shape closure
    "sql_case_7_missing_plus_duplicate_key": 50012,
    "sql_case_7_unknown_key_six_entries": 50013,
    "sql_case_7_string_value": 50013,
    "sql_case_7_float_value": 50013,
    "sql_case_7_boolean_value": 50013,
    "sql_case_7_count_33": 50013,
    "sql_case_8_duplicate_exception_key": 50031,
    # canonical identities
    # case_9 corrupts @ReleaseSetId, so 50027 is its governed rejection.
    "sql_case_9_uppercase_sha": 50027,
    "sql_case_9_nonhex_sha": 50027,
    "sql_case_9_short_sha": 50027,
    "sql_case_9_long_sha": 50027,
    "sql_case_10_resolved_specialist_null_release": 50047,
    "sql_case_11_pre_resolution_with_release": 50047,
    # parent/child relational rules
    "sql_case_12_13_child_points_at_standalone": 50034,
    "sql_case_14_child_points_at_child": 50034,
    "sql_case_15_mismatched_parent_release": 50035,
    "sql_case_12_missing_parent_row": 50033,
    # composition-parent purity
    "sql_case_16_parent_nonzero_counts": 50029,
    "sql_case_16_parent_with_usage": 547,
    "sql_case_16_parent_with_cost": 547,
    "sql_case_16_parent_with_exception": 50049,
    # closed state matrix
    "sql_matrix_case_1_invalid_output_with_transport_reason": 50042,
    "sql_matrix_case_2_provider_failure_with_validation_reason": 50042,
    "sql_matrix_case_3_release_on_service_not_configured": 50047,
    "sql_matrix_case_4_invalid_output_with_provider_timeout_class": 50044,
    "sql_matrix_case_5_internal_error_with_validation_rejected": 50043,
    "sql_matrix_case_6_reserved_outcome_refused": 50040,
    "sql_matrix_case_7_reserved_reason_abandoned": 50041,
    "sql_matrix_case_8_provider_reason_class_pair_mismatch": 50044,
    "sql_matrix_case_9_validation_class_missing_required_attrs": 50049,
    "sql_matrix_case_10_exception_attrs_array": 50014,
    "sql_matrix_case_10b_exception_attrs_scalar": 50014,
    "sql_matrix_case_11_exception_on_service_not_configured": 50044,
    "sql_matrix_case_12_failed_invalid_output_without_exception": 50044,
    "sql_matrix_case_13_success_without_release_identity": 50047,
    "sql_matrix_case_14_usage_on_provider_failure_row": 50048,
    "sql_matrix_case_15_parent_with_passed_validation": 50043,
    "sql_matrix_case_16_internal_error_with_wrong_reason": 50042,
    # correction C2 (runtime-compatible): the bundle-label text channel.
    # The stored label is <semver>+<sha8>; specialist stays separate, so
    # the validated combined identity is specialist@bundle_label.
    "sql_label_case_1_arbitrary_text": 50053,
    "sql_label_case_2_legacy_specialist_prefixed": 50054,
    "sql_label_case_3_label_on_composition_parent": 50050,
    "sql_label_case_4_mismatched_hash_suffix": 50053,
    "sql_label_case_5_uppercase_hex_suffix": 50053,
    "sql_label_case_6_nonhex_suffix": 50053,
    "sql_label_case_7_nonnumeric_version": 50054,
    "sql_label_case_8_two_component_version": 50054,
    "sql_label_case_9_empty_version_component": 50054,
    "sql_label_case_10_overlong_label": 50051,
    "sql_label_case_11_label_without_hash": 50050,
    "sql_label_case_12_short_label": 50051,
}


def load_governed_messages():
    """number -> exact THROW message, derived from the migration bytes.

    The driver surfaces the THROW's message text but not its number, so
    the proof matches the exact governed message instead. Deriving the
    table from the migration itself keeps one source of truth: a THROW
    whose message drifts fails its case rather than silently passing.
    """
    text = FORWARD_SQL.read_text(encoding="utf-8")
    messages = {}
    for number, message in re.findall(
        r"THROW (\d{5}), N''([^']+)'', 1;", text
    ):
        # Several governed numbers carry more than one message (the same
        # rule stated for different branches); keep every variant.
        messages.setdefault(int(number), []).append(message)
    return messages


GOVERNED_MESSAGES = load_governed_messages()

# Constraint-violation cases (SQL error 547): matched by the exact
# violated constraint name instead of a THROW message.
CASE_CONSTRAINT_FRAGMENTS = {
    "sql_case_16_parent_with_usage": "CK_iasc_kind_shape",
    "sql_case_16_parent_with_cost": "CK_iasc_kind_shape",
}


def governed_match(check, expected_number, error):
    """True when the failure is exactly the governed rejection expected."""
    fragment = CASE_CONSTRAINT_FRAGMENTS.get(check)
    if fragment is not None:
        return fragment in str(error)
    text = str(error)
    return any(
        message in text
        for message in GOVERNED_MESSAGES.get(expected_number, ())
    )


def governed_error_numbers(error):
    """Governed numbers OR message-mapped numbers named by an exception.

    Only integers already known to this contract are returned, so no raw
    driver text, server name, or object detail can reach the evidence.
    """
    found = set()
    text = str(error)
    for token in re.findall(r"\d+", text):
        number = int(token)
        if number in GOVERNED_ERROR_NUMBERS:
            found.add(number)
    for number, variants in GOVERNED_MESSAGES.items():
        if any(message in text for message in variants):
            found.add(number)
    return found


def call_append(cursor, values):
    names = ", ".join("%s = ?" % name for name in values)
    cursor.execute(
        "EXEC dbo.usp_AppendInterviewAIServerCall " + names,
        tuple(values.values()),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-database", required=True)
    arguments = parser.parse_args()

    if not _DATABASE_NAME.fullmatch(arguments.expect_database):
        print(json.dumps({"result": "refused",
                          "reason": "invalid expected database name"}))
        return 2
    if "peerslate-database" in arguments.expect_database:
        print(json.dumps({"result": "refused",
                          "reason": "refusing a production-named database"}))
        return 2
    connection_string = os.environ.get(CONNECTION_ENV)
    if not connection_string:
        print(json.dumps({"result": "refused",
                          "reason": "%s is not configured" % CONNECTION_ENV}))
        return 2

    results = {}
    connection = connect(connection_string, timeout=60)
    connection.autocommit = True
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME();")
        database_name = cursor.fetchone()[0]
        if database_name != arguments.expect_database:
            print(json.dumps({"result": "refused",
                              "reason": "connected to an unexpected database"}))
            return 2

        # The forward file is idempotent; applying it here makes the proof
        # self-sufficient (idempotent-forward case).
        cursor.execute(FORWARD_SQL.read_text(encoding="utf-8"))
        cursor.execute(FORWARD_SQL.read_text(encoding="utf-8"))
        results["idempotent_forward_applies_twice"] = "pass"

        # The forward migration carries schema only. The two execute-only
        # roles and their grants come from the administrator-run authority
        # script (the governed apply identity holds db_ddladmin only and
        # cannot create roles or grant; run 1419 proved it). The gate runs
        # the very same function, twice, so it proves that path and its
        # idempotency as well.
        ensure_roles_and_grants(cursor)
        ensure_roles_and_grants(cursor)
        results["authority_roles_and_grants_idempotent"] = "pass"

        def expect_reject(check, values):
            """Correction C3: a hostile case passes ONLY when the boundary
            raises its exact governed error number. An unexpected syntax,
            connection, missing-object, or missing-procedure failure used
            to look identical to a real rejection; now it fails the proof.

            Only governed numbers are recorded — never raw error text —
            so the evidence stays content-free.
            """
            expected = EXPECTED_ERRORS.get(check)
            if expected is None:
                results[check] = "FAIL (no expected error number declared)"
                return
            try:
                call_append(cursor, values)
            except Exception as error:
                if governed_match(check, expected, error):
                    results[check] = "pass"
                else:
                    results[check] = (
                        "FAIL (expected %d, observed %s)"
                        % (expected,
                           sorted(governed_error_numbers(error)) or "none")
                    )
            else:
                results[check] = "FAIL (accepted)"

        def expect_accept(check, values):
            try:
                call_append(cursor, values)
            except Exception as error:
                results[check] = "FAIL (%s)" % type(error).__name__
            else:
                results[check] = "pass"

        # -- sql_case_1: http_status boundary sweep ----------------------
        expect_reject("sql_case_1_status_99",
                      append_arguments(str(uuid.uuid4()), **{"@HttpStatus": 99}))
        expect_accept("sql_case_1_status_100",
                      append_arguments(str(uuid.uuid4()), **{"@HttpStatus": 100}))
        expect_accept("sql_case_1_status_599",
                      append_arguments(str(uuid.uuid4()), **{"@HttpStatus": 599}))
        expect_reject("sql_case_1_status_600",
                      append_arguments(str(uuid.uuid4()), **{"@HttpStatus": 600}))
        expect_reject("sql_case_1_status_999",
                      append_arguments(str(uuid.uuid4()), **{"@HttpStatus": 999}))

        # -- sql_case_2: retry_ordinal sweep -----------------------------
        expect_reject("sql_case_2_retry_minus1",
                      append_arguments(str(uuid.uuid4()), **{"@RetryOrdinal": -1}))
        expect_accept("sql_case_2_retry_0",
                      append_arguments(str(uuid.uuid4()), **{"@RetryOrdinal": 0}))
        expect_accept("sql_case_2_retry_15",
                      append_arguments(str(uuid.uuid4()), **{"@RetryOrdinal": 15}))
        expect_reject("sql_case_2_retry_16",
                      append_arguments(str(uuid.uuid4()), **{"@RetryOrdinal": 16}))
        expect_reject("sql_case_2_retry_999",
                      append_arguments(str(uuid.uuid4()), **{"@RetryOrdinal": 999}))

        # -- sql_case_3: duration sweep ----------------------------------
        expect_reject("sql_case_3_duration_minus1",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@DurProviderMs": -1}))
        expect_accept("sql_case_3_duration_0",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@DurProviderMs": 0}))
        expect_accept("sql_case_3_duration_max",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@DurProviderMs": 86_400_000,
                                          "@DurTotalServerMs": 86_400_000}))
        expect_reject("sql_case_3_duration_over",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@DurProviderMs": 86_400_001,
                                          "@DurTotalServerMs": 86_400_001}))
        expect_reject("sql_case_3_total_below_stage",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@DurProviderMs": 50,
                                          "@DurTotalServerMs": 10}))

        # -- sql_case_4: reply_chars sweep (validation-class attrs) ------
        for label, value, ok in (("minus1", -1, False), ("0", 0, True),
                                 ("100000", 100_000, True),
                                 ("100001", 100_001, False)):
            values = failed_arguments(
                str(uuid.uuid4()), "validation_value",
                '{"provider_stop_reason":"end_turn","reply_chars":%d}' % value,
            )
            (expect_accept if ok else expect_reject)(
                "sql_case_4_reply_chars_%s" % label, values,
            )

        # -- sql_case_5: exception status sweep (provider_rejected) -----
        for label, value, ok in (("99", 99, False), ("100", 100, True),
                                 ("599", 599, True), ("600", 600, False),
                                 ("999", 999, False)):
            values = failed_arguments(
                str(uuid.uuid4()), "provider_rejected",
                '{"status_code":%d}' % value,
                **{"@FailureState": "provider_failure",
                   "@FailureReason": "rejected",
                   "@ValidationResult": "not_applicable",
                   # Consolidated B4 matrix: no usable response exists
                   # under provider_failure, so usage/cost must be null.
                   "@ProviderInputTokens": None,
                   "@ProviderOutputTokens": None,
                   "@CostMicrousd": None,
                   "@PricingScheduleId": None},
            )
            (expect_accept if ok else expect_reject)(
                "sql_case_5_exception_status_%s" % label, values,
            )

        # -- sql_case_6: wrong-class exception attributes ----------------
        expect_reject("sql_case_6_timeout_with_status",
                      failed_arguments(str(uuid.uuid4()), "provider_timeout",
                                       '{"status_code":500}',
                                       **{"@FailureState": "provider_failure",
                                          "@FailureReason": "timeout",
                                          "@ValidationResult":
                                              "not_applicable"}))
        expect_reject("sql_case_6_rejected_with_reply_chars",
                      failed_arguments(str(uuid.uuid4()), "provider_rejected",
                                       '{"reply_chars":10}',
                                       **{"@FailureState": "provider_failure",
                                          "@FailureReason": "rejected",
                                          "@ValidationResult":
                                              "not_applicable"}))
        expect_reject("sql_case_6_validation_with_status",
                      failed_arguments(str(uuid.uuid4()), "validation_value",
                                       '{"status_code":502}'))
        expect_reject("sql_case_6_runtime_with_attrs",
                      failed_arguments(str(uuid.uuid4()), "runtime_unexpected",
                                       '{"reply_chars":1}',
                                       **{"@FailureState": "internal_error",
                                          "@FailureReason":
                                              "unexpected_server_fault",
                                          "@ValidationResult":
                                              "not_applicable"}))
        expect_reject("sql_case_6_legacy_class_name",
                      failed_arguments(str(uuid.uuid4()), "value_error",
                                       None))

        # -- sql_case_7: missing + duplicated source key, six entries ----
        expect_reject("sql_case_7_missing_plus_duplicate_key",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                          '{"answer":1,"answer":2,'
                                          '"confirmed_context":0,'
                                          '"history_selection":0,'
                                          '"member_evidence":3,'
                                          '"role_context":0}'}))
        expect_reject("sql_case_7_unknown_key_six_entries",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                          BASE_COUNTS.replace(
                                              '"question":1',
                                              '"smuggled":1')}))
        expect_reject("sql_case_7_string_value",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                          BASE_COUNTS.replace(
                                              '"question":1',
                                              '"question":"1"')}))
        expect_reject("sql_case_7_float_value",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                          BASE_COUNTS.replace(
                                              '"question":1',
                                              '"question":1.5')}))
        expect_reject("sql_case_7_boolean_value",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                          BASE_COUNTS.replace(
                                              '"question":1',
                                              '"question":true')}))
        expect_reject("sql_case_7_count_33",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                          BASE_COUNTS.replace(
                                              '"member_evidence":3',
                                              '"member_evidence":33')}))

        # -- sql_case_8: duplicate exception key -------------------------
        expect_reject("sql_case_8_duplicate_exception_key",
                      failed_arguments(str(uuid.uuid4()), "validation_value",
                                       '{"reply_chars":1,"reply_chars":2}'))

        # -- sql_case_9: canonical identity form -------------------------
        expect_reject("sql_case_9_uppercase_sha",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@ReleaseSetId": "A" * 64}))
        expect_reject("sql_case_9_nonhex_sha",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@ReleaseSetId": "z" * 64}))
        expect_reject("sql_case_9_short_sha",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@ReleaseSetId": "1" * 63}))
        expect_reject("sql_case_9_long_sha",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@ReleaseSetId": "1" * 65}))

        # -- sql_case_10/11: resolution pairing --------------------------
        expect_reject("sql_case_10_resolved_specialist_null_release",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@ReleaseSetId": None,
                                          "@CostMicrousd": None,
                                          "@PricingScheduleId": None}))
        expect_reject("sql_case_11_pre_resolution_with_release",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@BundleLabel": None,
                                          "@BundleContentSha256": None,
                                          "@Outcome": "failed",
                                          "@FailureState":
                                              "service_not_configured",
                                          "@FailureReason":
                                              "active_release_unresolved",
                                          "@HttpStatus": 503,
                                          "@ValidationResult":
                                              "not_applicable",
                                          "@ProviderInputTokens": None,
                                          "@ProviderOutputTokens": None,
                                          "@CostMicrousd": None,
                                          "@PricingScheduleId": None}))

        # -- parent/child relational cases -------------------------------
        parent_uuid = str(uuid.uuid4())
        expect_accept("relational_control_parent_insert",
                      parent_arguments(parent_uuid))
        child_uuid = str(uuid.uuid4())
        expect_accept("relational_control_child_insert",
                      append_arguments(child_uuid,
                                       **{"@Specialist": "grounded_example",
                                          "@ParentAttemptUuid": parent_uuid}))

        standalone_uuid = str(uuid.uuid4())
        expect_accept("relational_control_standalone_insert",
                      append_arguments(standalone_uuid))
        expect_reject("sql_case_12_13_child_points_at_standalone",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@Specialist": "generic_example",
                                          "@ParentAttemptUuid":
                                              standalone_uuid}))
        expect_reject("sql_case_14_child_points_at_child",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@Specialist": "generic_example",
                                          "@ParentAttemptUuid": child_uuid}))
        expect_reject("sql_case_15_mismatched_parent_release",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@Specialist": "generic_example",
                                          "@ParentAttemptUuid": parent_uuid,
                                          "@ReleaseSetId": "3" * 64}))
        expect_reject("sql_case_12_missing_parent_row",
                      append_arguments(str(uuid.uuid4()),
                                       **{"@ParentAttemptUuid":
                                              str(uuid.uuid4())}))

        # -- sql_case_16: parent purity ----------------------------------
        expect_reject("sql_case_16_parent_nonzero_counts",
                      parent_arguments(str(uuid.uuid4()),
                                       **{"@SourceClassCountsJson":
                                              BASE_COUNTS}))
        expect_reject("sql_case_16_parent_with_usage",
                      parent_arguments(str(uuid.uuid4()),
                                       **{"@ProviderInputTokens": 1,
                                          "@ProviderOutputTokens": 1}))
        expect_reject("sql_case_16_parent_with_cost",
                      parent_arguments(str(uuid.uuid4()),
                                       **{"@CostMicrousd": 1,
                                          "@PricingScheduleId": "2" * 64}))
        expect_reject("sql_case_16_parent_with_exception",
                      parent_arguments(str(uuid.uuid4()),
                                       **{"@Outcome": "failed",
                                          "@HttpStatus": 502,
                                          "@FailureState": "invalid_output",
                                          "@FailureReason": "no_json_object",
                                          "@ExceptionClass":
                                              "validation_value",
                                          "@ExceptionAttrsJson": "{}"}))

        # -- correction C2 (runtime-compatible): label channel closed ---
        SHA = "0" * 64
        def _labelled(label, **extra):
            values = {"@BundleLabel": label, "@BundleContentSha256": SHA}
            values.update(extra)
            return append_arguments(str(uuid.uuid4()), **values)

        expect_reject("sql_label_case_1_arbitrary_text",
                      _labelled("DROP TABLE dbo.interview_ai_server_calls"))
        # The pre-correction <specialist>@... shape is itself rejected now.
        expect_reject("sql_label_case_2_legacy_specialist_prefixed",
                      _labelled("coach@1.0.0+00000000"))
        expect_reject("sql_label_case_3_label_on_composition_parent",
                      parent_arguments(str(uuid.uuid4()),
                                       **{"@BundleLabel": "1.0.0+00000000",
                                          "@BundleContentSha256": SHA}))
        expect_reject("sql_label_case_4_mismatched_hash_suffix",
                      _labelled("1.0.0+deadbeef"))
        expect_reject("sql_label_case_5_uppercase_hex_suffix",
                      _labelled("1.0.0+0000000A",
                                **{"@BundleContentSha256": "0" * 63 + "a"}))
        expect_reject("sql_label_case_6_nonhex_suffix",
                      _labelled("1.0.0+zzzzzzzz"))
        expect_reject("sql_label_case_7_nonnumeric_version",
                      _labelled("one.0.0+00000000"))
        expect_reject("sql_label_case_8_two_component_version",
                      _labelled("100.0+00000000"))
        expect_reject("sql_label_case_9_empty_version_component",
                      _labelled("1..00+00000000"))
        expect_reject("sql_label_case_10_overlong_label",
                      _labelled("1" * 40 + ".0.0+00000000"))
        expect_reject("sql_label_case_11_label_without_hash",
                      _labelled("1.0.0+00000000",
                                **{"@BundleContentSha256": None}))
        expect_reject("sql_label_case_12_short_label",
                      _labelled("1.0+0000000"))
        expect_accept("sql_label_control_runtime_format_is_accepted",
                      _labelled("1.0.0+00000000"))
        expect_accept("sql_label_control_multi_digit_version",
                      append_arguments(
                          str(uuid.uuid4()),
                          **{"@Specialist": "planning_hints",
                             "@BundleLabel": "2.11.3+00000000",
                             "@BundleContentSha256": SHA}))

        # -- sql_case_17: a GENUINE overlapping two-connection race -----
        # Correction C3: the previous version appended sequentially on two
        # connections, which proved duplicate handling but never a race.
        # Two independent connections now contend on the same attempt_uuid
        # with DIFFERENT payloads, released simultaneously by a barrier.
        raced_uuid = str(uuid.uuid4())
        winner_payload = {"@HttpStatus": 200,
                          "@ProviderInputTokens": 700,
                          "@ProviderOutputTokens": 300,
                          "@CostMicrousd": 2200,
                          "@PricingScheduleId": "2" * 64}
        rival_payload = {"@HttpStatus": 599,
                         "@ProviderInputTokens": 1,
                         "@ProviderOutputTokens": 1,
                         "@CostMicrousd": 6,
                         "@PricingScheduleId": "9" * 64}

        barrier = threading.Barrier(2, timeout=60)
        race_outcomes = {}

        def _racer(name, payload):
            try:
                racer_connection = connect(connection_string, timeout=60)
                racer_connection.autocommit = True
                try:
                    racer_cursor = racer_connection.cursor()
                    # Both threads arrive here, then are released together.
                    barrier.wait()
                    call_append(racer_cursor,
                                append_arguments(raced_uuid, **payload))
                    race_outcomes[name] = "completed"
                finally:
                    racer_connection.close()
            except Exception as error:
                # Only governed numbers are recorded; never raw text.
                race_outcomes[name] = "error:%s" % (
                    sorted(governed_error_numbers(error)) or "ungoverned"
                )

        threads = [
            threading.Thread(target=_racer, args=("winner", winner_payload)),
            threading.Thread(target=_racer, args=("rival", rival_payload)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=120)

        cursor.execute(
            "SELECT COUNT(*) FROM dbo.interview_ai_server_calls"
            " WHERE attempt_uuid = ?;",
            (raced_uuid,),
        )
        raced_row_count = cursor.fetchone()[0]
        results["sql_case_17_race_leaves_exactly_one_row"] = (
            "pass" if raced_row_count == 1
            else "FAIL (rows=%s)" % raced_row_count
        )

        # Whichever connection won, the stored row must be ENTIRELY that
        # payload — never a mixture, and never mutated by the loser.
        cursor.execute(
            "SELECT http_status, provider_input_tokens,"
            " provider_output_tokens, cost_microusd, pricing_schedule_id"
            " FROM dbo.interview_ai_server_calls WHERE attempt_uuid = ?;",
            (raced_uuid,),
        )
        stored = cursor.fetchone()
        if stored is None:
            results["sql_case_17_winning_row_is_internally_consistent"] = (
                "FAIL (no row)"
            )
        else:
            def _matches(payload):
                return (
                    stored[0] == payload["@HttpStatus"]
                    and stored[1] == payload["@ProviderInputTokens"]
                    and stored[2] == payload["@ProviderOutputTokens"]
                    and stored[3] == payload["@CostMicrousd"]
                    and stored[4] == payload["@PricingScheduleId"]
                )
            consistent = _matches(winner_payload) or _matches(rival_payload)
            results["sql_case_17_winning_row_is_internally_consistent"] = (
                "pass" if consistent else "FAIL (mixed payload)"
            )
            stored_before = tuple(stored)

        # The duplicate is an immutable no-op: neither racer surfaced an
        # ungoverned error, and re-reading the row shows identical bytes.
        results["sql_case_17_duplicate_is_a_silent_no_op"] = (
            "pass"
            if sorted(race_outcomes.values()) == ["completed", "completed"]
            else "FAIL (%s)" % sorted(race_outcomes.values())
        )

        cursor.execute(
            "SELECT http_status, provider_input_tokens,"
            " provider_output_tokens, cost_microusd, pricing_schedule_id"
            " FROM dbo.interview_ai_server_calls WHERE attempt_uuid = ?;",
            (raced_uuid,),
        )
        stored_after = cursor.fetchone()
        results["sql_case_17_winning_row_bytes_unchanged"] = (
            "pass"
            if stored is not None and stored_after is not None
            and tuple(stored_after) == stored_before
            else "FAIL (row changed after the race)"
        )

        # -- consolidated B4: the closed state matrix (sql_matrix_case_N
        #    mirrors py_matrix_case_N name for name) ----------------------
        NO_USAGE = {
            "@ProviderInputTokens": None, "@ProviderOutputTokens": None,
            "@CostMicrousd": None, "@PricingScheduleId": None,
        }
        expect_reject("sql_matrix_case_1_invalid_output_with_transport_reason",
                      failed_arguments(
                          str(uuid.uuid4()), "validation_value",
                          '{"provider_stop_reason":"end_turn","reply_chars":10}',
                          **{"@FailureReason": "transport"}))
        expect_reject("sql_matrix_case_2_provider_failure_with_validation_reason",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_transport", "{}",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "no_json_object",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        expect_reject("sql_matrix_case_3_release_on_service_not_configured",
                      append_arguments(
                          str(uuid.uuid4()),
                          **{"@Outcome": "failed", "@HttpStatus": 503,
                             "@FailureState": "service_not_configured",
                             "@FailureReason": "active_release_unresolved",
                             "@ValidationResult": "not_applicable",
                             "@BundleLabel": None,
                             "@BundleContentSha256": None, **NO_USAGE}))
        expect_reject("sql_matrix_case_4_invalid_output_with_provider_timeout_class",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_timeout", "{}"))
        expect_reject("sql_matrix_case_5_internal_error_with_validation_rejected",
                      failed_arguments(
                          str(uuid.uuid4()), "runtime_unexpected", "{}",
                          **{"@FailureState": "internal_error",
                             "@FailureReason": "unexpected_server_fault",
                             "@ValidationResult": "rejected"}))
        expect_reject("sql_matrix_case_6_reserved_outcome_refused",
                      append_arguments(
                          str(uuid.uuid4()),
                          **{"@Outcome": "refused", "@HttpStatus": 403,
                             "@FailureState": "internal_error",
                             "@FailureReason": None,
                             "@ValidationResult": "not_applicable"}))
        expect_reject("sql_matrix_case_7_reserved_reason_abandoned",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_transport", "{}",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "abandoned",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        expect_reject("sql_matrix_case_8_provider_reason_class_pair_mismatch",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_transport", "{}",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "timeout",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        expect_reject("sql_matrix_case_9_validation_class_missing_required_attrs",
                      failed_arguments(
                          str(uuid.uuid4()), "validation_value",
                          '{"reply_chars":10}'))
        expect_reject("sql_matrix_case_10_exception_attrs_array",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_rejected", "[]",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "rejected",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        expect_reject("sql_matrix_case_10b_exception_attrs_scalar",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_rejected", "7",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "rejected",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        expect_reject("sql_matrix_case_11_exception_on_service_not_configured",
                      append_arguments(
                          str(uuid.uuid4()),
                          **{"@Outcome": "failed", "@HttpStatus": 503,
                             "@FailureState": "service_not_configured",
                             "@FailureReason": "active_release_unresolved",
                             "@ValidationResult": "not_applicable",
                             "@BundleLabel": None,
                             "@BundleContentSha256": None,
                             "@ReleaseSetId": None,
                             "@ExceptionClass": "runtime_unexpected",
                             "@ExceptionAttrsJson": "{}", **NO_USAGE}))
        expect_reject("sql_matrix_case_12_failed_invalid_output_without_exception",
                      failed_arguments(str(uuid.uuid4()), None, None))
        expect_reject("sql_matrix_case_13_success_without_release_identity",
                      append_arguments(
                          str(uuid.uuid4()),
                          **{"@BundleLabel": None,
                             "@BundleContentSha256": None,
                             "@ReleaseSetId": None}))
        expect_reject("sql_matrix_case_14_usage_on_provider_failure_row",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_timeout", "{}",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "timeout",
                             "@ValidationResult": "not_applicable"}))
        expect_reject("sql_matrix_case_15_parent_with_passed_validation",
                      parent_arguments(
                          str(uuid.uuid4()),
                          **{"@ValidationResult": "passed"}))
        expect_reject("sql_matrix_case_16_internal_error_with_wrong_reason",
                      failed_arguments(
                          str(uuid.uuid4()), "runtime_unexpected", "{}",
                          **{"@FailureState": "internal_error",
                             "@FailureReason": "transport",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        # sql_matrix_case_17: lawful accept-controls for every failed state
        # (the matrix must not over-reject the real emission shapes).
        expect_accept("sql_matrix_case_17_accept_invalid_output_with_usage",
                      failed_arguments(
                          str(uuid.uuid4()), "validation_value",
                          '{"provider_stop_reason":"end_turn","reply_chars":9}'))
        expect_accept("sql_matrix_case_17_accept_provider_failure_no_usage",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_timeout", "{}",
                          **{"@FailureState": "provider_failure",
                             "@FailureReason": "timeout",
                             "@ValidationResult": "not_applicable", **NO_USAGE}))
        expect_accept("sql_matrix_case_17_accept_internal_error",
                      failed_arguments(
                          str(uuid.uuid4()), "provider_response_shape", "{}",
                          **{"@FailureState": "internal_error",
                             "@FailureReason": "unexpected_server_fault",
                             "@ValidationResult": "not_applicable"}))
        expect_accept("sql_matrix_case_17_accept_service_not_configured",
                      append_arguments(
                          str(uuid.uuid4()),
                          **{"@Outcome": "failed", "@HttpStatus": 503,
                             "@FailureState": "service_not_configured",
                             "@FailureReason": "active_release_unresolved",
                             "@ValidationResult": "not_applicable",
                             "@BundleLabel": None,
                             "@BundleContentSha256": None,
                             "@ReleaseSetId": None, **NO_USAGE}))

        # -- preserved battery: permissions ------------------------------
        for principal in ("proof_append", "proof_maintenance"):
            cursor.execute(
                "IF DATABASE_PRINCIPAL_ID(N'%s') IS NULL "
                "CREATE USER %s WITHOUT LOGIN;" % (principal, principal)
            )
        cursor.execute(
            "ALTER ROLE interview_telemetry_append ADD MEMBER proof_append;"
        )
        cursor.execute(
            "ALTER ROLE interview_telemetry_maintenance "
            "ADD MEMBER proof_maintenance;"
        )

        def expect_error_sql(check, statement):
            try:
                cursor.execute(statement)
                cursor.fetchall()
            except Exception:
                results[check] = "pass"
            else:
                results[check] = "FAIL (no error raised)"

        def expect_permission_denied(check, statement):
            """Round-2 correction: a DENY check passes ONLY on SQL's
            permission refusal (error 229), never on an unrelated failure
            such as a foreign-key violation. Only the number is recorded."""
            try:
                cursor.execute(statement)
                cursor.fetchall()
            except Exception as error:
                text = str(error)
                denied = (re.search(r"(?<![0-9])229(?![0-9])", text) is not None
                          or "permission was denied" in text.lower())
                results[check] = (
                    "pass" if denied else "FAIL (not a permission denial)"
                )
            else:
                results[check] = "FAIL (no error raised)"

        cursor.execute("EXECUTE AS USER = 'proof_append';")
        expect_error_sql("append_role_cannot_insert_directly",
                         "INSERT dbo.interview_ai_server_calls (attempt_uuid,"
                         "event_kind,outcome,http_status,retry_ordinal,"
                         "dur_receive_ms,dur_retrieval_ms,dur_manifest_ms,"
                         "dur_provider_ms,dur_validate_ms,dur_respond_ms,"
                         "dur_total_server_ms,specialist,guardian_rejections,"
                         "validation_result,source_class_counts) VALUES "
                         "(NEWID(),'specialist_call','failed',503,0,0,0,0,0,"
                         "0,0,0,'coach',N'[]','not_applicable',N'%s');"
                         % ZERO_COUNTS)
        expect_error_sql("append_role_cannot_select",
                         "SELECT TOP (1) attempt_uuid "
                         "FROM dbo.interview_ai_server_calls;")
        expect_error_sql("append_role_cannot_purge",
                         "EXEC dbo.usp_PurgeInterviewAIServerCalls "
                         "@BatchSize = 10, @MaxBatches = 1;")
        try:
            call_append(cursor, append_arguments(str(uuid.uuid4())))
            results["append_role_can_execute_append"] = "pass"
        except Exception:
            results["append_role_can_execute_append"] = "FAIL"
        cursor.execute("REVERT;")

        cursor.execute("EXECUTE AS USER = 'proof_maintenance';")
        try:
            call_append(cursor, append_arguments(str(uuid.uuid4())))
            results["maintenance_role_cannot_append"] = "FAIL (accepted)"
        except Exception:
            results["maintenance_role_cannot_append"] = "pass"
        expect_error_sql("maintenance_role_cannot_delete_directly",
                         "DELETE TOP (1) dbo.interview_ai_server_calls;")
        try:
            cursor.execute(
                "EXEC dbo.usp_PurgeInterviewAIServerCalls "
                "@BatchSize = 10, @MaxBatches = 1;"
            )
            cursor.fetchall()
            results["maintenance_role_can_execute_purge"] = "pass"
        except Exception:
            results["maintenance_role_can_execute_purge"] = "FAIL"
        cursor.execute("REVERT;")

        # -- production-shaped application identity ----------------------
        # The real application identity holds db_datareader, db_datawriter
        # and a database-wide EXECUTE grant. A stand-in with exactly those
        # grants plus the append role proves that the authority script's
        # DENYs close purge and direct table access while ownership
        # chaining keeps the append procedure working.
        cursor.execute(
            "IF DATABASE_PRINCIPAL_ID(N'proof_application') IS NULL "
            "CREATE USER proof_application WITHOUT LOGIN;"
        )
        cursor.execute("ALTER ROLE db_datareader ADD MEMBER proof_application;")
        cursor.execute("ALTER ROLE db_datawriter ADD MEMBER proof_application;")
        cursor.execute("GRANT EXECUTE TO proof_application;")
        cursor.execute(
            "ALTER ROLE interview_telemetry_append ADD MEMBER proof_application;"
        )
        cursor.execute("EXECUTE AS USER = 'proof_application';")
        try:
            cursor.execute(
                "EXEC dbo.usp_PurgeInterviewAIServerCalls "
                "@BatchSize = 10, @MaxBatches = 1;"
            )
            cursor.fetchall()
            broad_grants_reach_purge = True
        except Exception:
            broad_grants_reach_purge = False
        cursor.execute("REVERT;")
        results["broad_application_grants_reach_purge_without_deny"] = (
            "pass" if broad_grants_reach_purge else "FAIL (premise not reproduced)"
        )
        ensure_application_denies(cursor, "proof_application")
        ensure_application_denies(cursor, "proof_application")
        cursor.execute("EXECUTE AS USER = 'proof_application';")
        expect_permission_denied("denied_application_cannot_purge",
                                 "EXEC dbo.usp_PurgeInterviewAIServerCalls "
                                 "@BatchSize = 10, @MaxBatches = 1;")
        expect_permission_denied("denied_application_cannot_select",
                                 "SELECT TOP (1) attempt_uuid "
                                 "FROM dbo.interview_ai_server_calls;")
        # WHERE 1 = 0 touches no row, so only the permission check can fail.
        expect_permission_denied("denied_application_cannot_delete_directly",
                                 "DELETE dbo.interview_ai_server_calls "
                                 "WHERE 1 = 0;")
        expect_permission_denied("denied_application_cannot_insert_directly",
                                 "INSERT dbo.interview_ai_server_calls "
                                 "(attempt_uuid) SELECT NEWID() WHERE 1 = 0;")
        try:
            call_append(cursor, append_arguments(str(uuid.uuid4())))
            results["denied_application_can_still_append_via_procedure"] = "pass"
        except Exception:
            results["denied_application_can_still_append_via_procedure"] = "FAIL"
        cursor.execute("REVERT;")

        # -- authority script end to end -----------------------------------
        # Round-2 correction: production apply must not be the first
        # execution of any authority function. apply() and verify() run
        # here exactly as the administrator will run them, on stand-ins:
        # the broad-grant application stand-in above and a fresh
        # EXTERNAL_USER created from a synthetic SID (TYPE = E, so
        # EXECUTE AS on an external principal is exercised too).
        # This part REQUIRES an Entra-authenticated proof connection: a
        # SQL-authenticated one is refused by SQL Server when it tries to
        # impersonate an EXTERNAL_USER ("only active directory users can
        # impersonate other active directory users"), proven 2026-08-22.
        # The failure is therefore a NAMED check, never a traceback.
        synthetic_sid = uuid.uuid4().bytes_le
        try:
            authority_apply(
                cursor, synthetic_sid,
                application_principal="proof_application",
                maintenance_principal="proof_maintenance_external",
            )
            authority_apply(
                cursor, synthetic_sid,
                application_principal="proof_application",
                maintenance_principal="proof_maintenance_external",
            )
            authority_report = authority_verify(
                cursor, synthetic_sid,
                expected_database=arguments.expect_database,
                application_principal="proof_application",
                maintenance_principal="proof_maintenance_external",
            )
        except Exception as error:
            results["authority_apply_and_verify_end_to_end"] = (
                "FAIL (%s; an Entra-authenticated proof connection is required)"
                % type(error).__name__
            )
        else:
            for key in sorted(authority_report):
                value = authority_report[key]
                if isinstance(value, bool):
                    results["authority_verify_" + key] = (
                        "pass" if value else "FAIL"
                    )
            results["authority_apply_and_verify_end_to_end"] = (
                "pass" if authority_report["result"] == "pass" else "FAIL"
            )

        # -- preserved battery: retention boundary -----------------------
        old_uuid = str(uuid.uuid4())
        young_uuid = str(uuid.uuid4())
        call_append(cursor, append_arguments(old_uuid))
        call_append(cursor, append_arguments(young_uuid))
        cursor.execute(
            "UPDATE dbo.interview_ai_server_calls SET recorded_at = "
            "DATEADD(DAY, -91, SYSUTCDATETIME()) WHERE attempt_uuid = ?;",
            (old_uuid,),
        )
        cursor.execute(
            "UPDATE dbo.interview_ai_server_calls SET recorded_at = "
            "DATEADD(DAY, -89, SYSUTCDATETIME()) WHERE attempt_uuid = ?;",
            (young_uuid,),
        )
        cursor.execute("EXECUTE AS USER = 'proof_maintenance';")
        cursor.execute(
            "EXEC dbo.usp_PurgeInterviewAIServerCalls "
            "@BatchSize = 100, @MaxBatches = 5;"
        )
        cursor.fetchall()
        cursor.execute("REVERT;")
        cursor.execute(
            "SELECT "
            " (SELECT COUNT(*) FROM dbo.interview_ai_server_calls"
            "  WHERE attempt_uuid = ?),"
            " (SELECT COUNT(*) FROM dbo.interview_ai_server_calls"
            "  WHERE attempt_uuid = ?);",
            (old_uuid, young_uuid),
        )
        old_left, young_left = cursor.fetchone()
        results["purge_deletes_at_exactly_90_days"] = (
            "pass" if old_left == 0 and young_left == 1
            else "FAIL (old=%s young=%s)" % (old_left, young_left)
        )
        expect_error_sql("purge_rejects_oversize_batch",
                         "EXEC dbo.usp_PurgeInterviewAIServerCalls "
                         "@BatchSize = 5001, @MaxBatches = 1;")

        # -- preserved battery: rollback guard ---------------------------
        rollback_sql = ROLLBACK_SQL.read_text(encoding="utf-8")
        try:
            cursor.execute(rollback_sql)
            results["rollback_refuses_nonempty_table"] = (
                "FAIL (rollback ran against rows)"
            )
        except Exception:
            cursor.execute(
                "SELECT OBJECT_ID(N'dbo.interview_ai_server_calls', N'U');"
            )
            results["rollback_refuses_nonempty_table"] = (
                "pass" if cursor.fetchone()[0] is not None
                else "FAIL (table dropped despite refusal)"
            )
        cursor.execute("DELETE dbo.interview_ai_server_calls "
                       "WHERE parent_attempt_uuid IS NOT NULL;")
        cursor.execute("DELETE dbo.interview_ai_server_calls;")
        cursor.execute(rollback_sql)
        cursor.execute(
            "SELECT OBJECT_ID(N'dbo.interview_ai_server_calls', N'U');"
        )
        table_gone = cursor.fetchone()[0] is None
        cursor.execute(
            "SELECT COUNT(*) FROM dbo.schema_migrations "
            "WHERE migration_id = N'PS-INTERVIEW-AI-EXTRACT-001';"
        )
        ledger_gone = cursor.fetchone()[0] == 0
        results["rollback_completes_against_empty_table"] = (
            "pass" if table_gone and ledger_gone
            else "FAIL (table_gone=%s ledger_gone=%s)"
            % (table_gone, ledger_gone)
        )
        cursor.execute(FORWARD_SQL.read_text(encoding="utf-8"))
        cursor.execute(
            "SELECT OBJECT_ID(N'dbo.interview_ai_server_calls', N'U');"
        )
        results["forward_reapplies_after_rollback"] = (
            "pass" if cursor.fetchone()[0] is not None else "FAIL"
        )
        # Dropping the procedures dropped their execute grants; the roles
        # themselves survive the rollback (it never touches them). Re-running
        # the authority function must restore exactly one grant per role.
        ensure_roles_and_grants(cursor)
        cursor.execute(
            "SELECT COUNT(*) FROM sys.database_permissions AS permission_entry "
            "JOIN sys.database_principals AS role_principal "
            "  ON role_principal.principal_id = permission_entry.grantee_principal_id "
            "WHERE role_principal.name IN (N'interview_telemetry_append', "
            "      N'interview_telemetry_maintenance') "
            "  AND permission_entry.permission_name = N'EXECUTE';"
        )
        results["authority_regrants_after_forward_reapply"] = (
            "pass" if cursor.fetchone()[0] == 2 else "FAIL"
        )
    finally:
        connection.close()

    failed = [name for name, value in results.items() if value != "pass"]
    report = {
        "result": "pass" if not failed else "FAIL",
        "database": arguments.expect_database,
        "checks": results,
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
