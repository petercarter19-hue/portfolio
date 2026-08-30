"""Contracts for PS-SETTINGS-EXPORT-008, the account-export preferences
and consent readers.

Modeled directly on tests/test_settings_export_media_transcript_reader.py
(PS-SETTINGS-EXPORT-007, gate sealed): registry completeness/gate-null
assertions plus focused structural assertions for the enforcement rules
the writer brief and
docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
require that a static read of the SQL/Python text can express without a
live database. Also pins services/account_export_domain_readers.py's
DOMAINS registry against the actual SQL output column lists, and
exercises the adapter's row/read-window decoding with fake cursors.

Every DOMAINS-scoped assertion below is scoped to THIS package's own
three domains ("connection_preferences", "notification_preferences",
"consent_history"), never to "however many domains the shared dict
currently totals" -- the lesson package 1's own test file needed applied
retroactively and every later package has followed since.

THE CENTRAL FINDINGS THIS TEST FILE PINS:
  1. All three tables key on dbo.app_users.id (user_id), not
     owner_profile_id -- the second, third, and fourth readers in this
     program to do so (usp_ReadAccountExportAccountForOwner was the
     first). Every reader still resolves the full, byte-identical
     identity header (including the otherwise-unused @ProfileId) before
     filtering on user_id = @UserId.
  2. Both preference readers (connection_preferences,
     notification_preferences) emit an explicit constant disclosure
     column, feature_status = 'dormant_not_yet_enforced', on every row
     (Paper 2's truthful-labeling requirement); the consent reader
     carries NO such column (Paper 3: consent records are real, live
     facts, never an unenforced switch).
  3. dbo.user_consents.evidence_json is excluded whole
     (UNCONSTRAINED_EVIDENCE); dbo.user_consents.source_context is also
     excluded, for a distinct, disclosed, non-directive reason (no
     procedure anywhere writes this table today, so its real-world
     population cannot be verified against any actual procedure body).
     consent_status includes 'withdrawn' and every status is returned,
     so a member's export shows their full consent history.
  4. No third-party consent is read: dbo.recruiter_questions never
     appears in the migration, either reader body, or the paired
     verification script.
"""

import json
import re
import unittest
from pathlib import Path

from scripts.migration_registry import executable_body, executable_sha256

import services.account_export_domain_readers as readers_module
from services.account_export_domain_readers import DOMAINS, iter_included_readers


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-008_preferences_consent_reader.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-008_preferences_consent_reader_rollback.sql"
VERIFY = VERIFICATION / "PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
ADAPTER_SOURCE_PATH = ROOT / "services" / "account_export_domain_readers.py"

READER_PROCEDURES = (
    "usp_ReadAccountExportConnectionPreferenceForOwner",
    "usp_ReadAccountExportNotificationPreferenceForOwner",
    "usp_ReadAccountExportUserConsentForOwner",
)

# All three tables independently carry only user_id (never
# owner_profile_id -- see the migration file's own "IDENTITY" header
# section), so every reader's own owner predicate is a single-item
# tuple. No reader in this package joins to a second table.
OWNER_PREDICATES = {
    "usp_ReadAccountExportConnectionPreferenceForOwner": (
        "preference.user_id = @UserId",
    ),
    "usp_ReadAccountExportNotificationPreferenceForOwner": (
        "preference.user_id = @UserId",
    ),
    "usp_ReadAccountExportUserConsentForOwner": (
        "consent.user_id = @UserId",
    ),
}

# How many "JOIN dbo." occurrences each procedure body should contain,
# INCLUDING the shared identity header's own "JOIN dbo.app_users". All
# three readers are top-level, single-table reads with no content-level
# join of their own.
EXPECTED_JOIN_COUNT = {
    "usp_ReadAccountExportConnectionPreferenceForOwner": 1,
    "usp_ReadAccountExportNotificationPreferenceForOwner": 1,
    "usp_ReadAccountExportUserConsentForOwner": 1,
}

# Forbidden OUTPUT field names (unqualified, as they appear after
# aliasing/dot-stripping) per procedure. A full-name set, never a
# substring list -- PS-SETTINGS-EXPORT-003's own paused-predecessor
# design notes record a naive substring scan false-positiving on
# legitimate columns.
FORBIDDEN_FIELDS = {
    "usp_ReadAccountExportConnectionPreferenceForOwner": {"user_id"},
    "usp_ReadAccountExportNotificationPreferenceForOwner": {"user_id"},
    "usp_ReadAccountExportUserConsentForOwner": {
        "user_id", "user_consent_id", "source_context", "evidence_json",
    },
}

# The one directive-named hard-exclusion category this package touches
# (Paper 3's own ruling: a schema-free field that could hold network
# addresses or device details), canary-proven in the paired verification
# script. Every one of these must appear in FORBIDDEN_FIELDS above
# (belt) and must never appear in any procedure's actual output
# (suspenders, checked directly against DOMAINS in
# test_every_directive_category_is_actually_absent_from_every_readers_output).
DIRECTIVE_CATEGORY_COLUMNS = {
    "unconstrained_evidence": {"evidence_json"},
}

# Disclosed but NOT a directive category: source_context is excluded
# because no procedure anywhere writes dbo.user_consents today, so its
# real-world population cannot be traced against any actual procedure
# body -- the same "not a directive category, a precedent extension"
# treatment PS-SETTINGS-EXPORT-006 gave idempotency_key. Also
# canary-proven in the verification script.
UNVERIFIED_FIELD_COLUMNS = {"source_context"}

# Both preference readers disclose the dormant-feature label; the
# consent reader must never carry it (consent records are real, live
# facts, never an unenforced switch).
DORMANT_LABEL_READERS = (
    "usp_ReadAccountExportConnectionPreferenceForOwner",
    "usp_ReadAccountExportNotificationPreferenceForOwner",
)
NO_DORMANT_LABEL_READERS = ("usp_ReadAccountExportUserConsentForOwner",)
DORMANT_LABEL_VALUE = "dormant_not_yet_enforced"

IDENTITY_HEADER = (
    "SET NOCOUNT ON;\n\n"
    "            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();\n\n"
    "            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');\n\n"
    "            DECLARE @ProfileId bigint;\n"
    "            DECLARE @UserId int;\n"
    "            IF @UserKey IS NOT NULL\n"
    "                SELECT\n"
    "                    @ProfileId = profile.profile_id,\n"
    "                    @UserId = app_user.id\n"
    "                FROM dbo.member_profiles AS profile\n"
    "                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id\n"
    "                WHERE app_user.user_key = @UserKey\n"
    "                  AND app_user.active = 1\n"
    "                  AND profile.active = 1;\n\n"
    "            IF @ProfileId IS NULL RETURN;"
)

# Every account-export forward migration in the program, oldest first,
# ending with this package's own file -- used only to prove the identity
# header stays byte-identical across the WHOLE program, not merely
# within this file.
ACCOUNT_EXPORT_FORWARD_FILES = (
    MIGRATIONS / "PS-SETTINGS-EXPORT-003_core_readers.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-004_capture_moment_readers.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-005_workshop_reader.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-006_oppslate_reader.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-007_media_transcript_reader.sql",
    FORWARD,
)


def read(path):
    return path.read_text(encoding="utf-8")


def procedure_batches(sql):
    """Map procedure name -> its raw (still quote-doubled) EXEC(N'...') body."""

    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


def signature(batch, procedure_name):
    match = re.search(
        rf"CREATE OR ALTER PROCEDURE dbo\.{procedure_name}(.*?)\n\s*AS\n",
        batch,
        flags=re.DOTALL,
    )
    if not match:
        raise AssertionError(f"signature not found for {procedure_name}")
    return match.group(1)


def content_select_columns(body):
    """Extract the OUTPUT field names of a reader's content SELECT, in
    order. Located precisely between the shared identity header's
    closing "IF @ProfileId IS NULL RETURN;" line and the procedure's own
    first subsequent FROM clause -- every reader in this package is a
    single-table read with no ancestor join, so this generic anchor
    (identical to every prior package's own helper) locates the correct
    boundary directly."""

    marker = "IF @ProfileId IS NULL RETURN;"
    header_end = body.index(marker) + len(marker)
    remainder = body[header_end:]
    select_start = remainder.index("SELECT") + len("SELECT")
    from_pos = remainder.index("FROM dbo.")
    column_text = remainder[select_start:from_pos]
    names = []
    for segment in column_text.split(","):
        segment = segment.strip()
        if not segment:
            continue
        if " AS " in segment:
            name = segment.rsplit(" AS ", 1)[1].strip()
        elif "." in segment:
            name = segment.rsplit(".", 1)[1].strip()
        else:
            name = segment
        names.append(name)
    return names


def extract_identity_header(body):
    start = body.index("SET NOCOUNT ON;")
    end = body.index("IF @ProfileId IS NULL RETURN;") + len("IF @ProfileId IS NULL RETURN;")
    return body[start:end]


def domain_field_map():
    """procedure_name -> fields tuple, from DOMAINS (every domain, not only
    included ones, though only included domains carry readers)."""

    mapping = {}
    for domain in DOMAINS.values():
        for reader_entry in domain["readers"]:
            mapping[reader_entry["procedure"]] = reader_entry["fields"]
    return mapping


class SettingsExportPreferencesConsentReaderMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = read(FORWARD)
        cls.rollback = read(ROLLBACK)
        cls.verify = read(VERIFY)
        cls.procedures = procedure_batches(cls.forward)

    # -- file shape -----------------------------------------------------

    def test_claimed_files_exist_and_are_single_guarded_batches(self):
        for path in (FORWARD, ROLLBACK, VERIFY):
            self.assertTrue(path.exists(), msg=str(path))
            source = read(path)
            self.assertNotIn("\nGO", source)
            self.assertEqual(source.count("("), source.count(")"))
            self.assertEqual(source.count("/*"), source.count("*/"))
        for source in (self.forward, self.rollback, self.verify):
            for fragment in ("SET XACT_ABORT ON", "BEGIN TRY", "BEGIN TRANSACTION", "BEGIN CATCH", "THROW;"):
                self.assertIn(fragment, source)

    def test_forward_and_rollback_throw_numbers_are_unique_and_in_range(self):
        for label, source, low, high in (
            ("forward", self.forward, 59000, 59099),
            ("rollback", self.rollback, 59000, 59099),
        ):
            with self.subTest(file=label):
                numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)), "THROW numbers must be unique in this file")
                self.assertTrue(all(low <= n <= high for n in numbers), numbers)

    def test_verify_throw_numbers_are_in_its_own_reserved_range(self):
        # Unlike the forward/rollback files, several sections of the
        # verify script deliberately reuse a number across several THROW
        # statements sharing one meaning (e.g. every "contains one of the
        # other owner's rows" cross-contamination check) -- uniqueness is
        # not asserted here, matching every prior package's own verify-
        # file test.
        numbers = [int(n) for n in re.findall(r"THROW (\d+),", self.verify)]
        self.assertTrue(numbers)
        self.assertTrue(all(59100 <= n <= 59199 for n in numbers), numbers)

    def test_throw_ranges_are_fresh_against_every_sibling_sql_file(self):
        own_files = {FORWARD, ROLLBACK, VERIFY}
        sql_root = ROOT / "SQL FIles"
        for path in sql_root.rglob("*.sql"):
            if path in own_files:
                continue
            source = read(path)
            numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
            colliding = [n for n in numbers if 59000 <= n <= 59199]
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertFalse(colliding, msg=f"{path} reuses reserved number(s) {colliding}")

    def test_forward_creates_exactly_the_claimed_procedures_and_nothing_else(self):
        self.assertEqual(set(self.procedures), set(READER_PROCEDURES))
        self.assertEqual(self.forward.count("CREATE OR ALTER PROCEDURE"), len(READER_PROCEDURES))
        self.assertNotIn("CREATE TABLE", self.forward)
        self.assertNotIn("CREATE TRIGGER", self.forward)
        self.assertNotIn("CREATE INDEX", self.forward)
        self.assertNotIn("CREATE UNIQUE INDEX", self.forward)

    def test_forward_never_redefines_another_migrations_procedure(self):
        other_forwards = [
            entry["forward"]
            for entry in json.loads(read(REGISTRY))["migrations"]
            if entry["id"] != "PS-SETTINGS-EXPORT-008"
        ]
        for relative in other_forwards:
            path = ROOT / relative
            if not path.exists():
                continue
            source = read(path)
            for procedure in READER_PROCEDURES:
                self.assertNotIn(
                    f"PROCEDURE dbo.{procedure}",
                    source,
                    msg=f"{procedure} must be owned by exactly one migration",
                )

    def test_no_reader_references_recruiter_questions(self):
        # No third-party consent is read: dbo.recruiter_questions never
        # appears in any reader procedure's own body. (The migration's
        # own header comment and ledger description literal both name
        # dbo.recruiter_questions explicitly, by design, to document
        # this exact boundary -- the same "name the excluded table in
        # the summary" precedent PS-SETTINGS-EXPORT-004's own registry
        # entry set for target_entity_id/dbo.slate_entities -- so this
        # check is scoped to the procedure bodies, not the whole file.)
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertNotIn("recruiter_questions", self.procedures[name])

    # -- prerequisite guards match the registry's requires list ----------

    def test_forward_requires_exactly_the_preferences_consent_chain(self):
        self.assertIn("migration_id = N'PS-PLAT-004'", self.forward)
        # PS-AUTH-001 is a registry-level requirement only (the paired
        # verification script's usp_UpsertAppUserFromAuth dependency);
        # the migration body itself never checks for it -- app_users/
        # member_profiles' identity-resolution columns predate
        # PS-AUTH-001, exactly every prior package's recorded reasoning
        # for the identical omission.
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.forward)
        for fragment in (
            "migration_id = N'PS-SETTINGS-EXPORT-001'",
            "migration_id = N'PS-SETTINGS-EXPORT-003'",
            "migration_id = N'PS-SETTINGS-EXPORT-004'",
            "migration_id = N'PS-SETTINGS-EXPORT-005'",
            "migration_id = N'PS-SETTINGS-EXPORT-006'",
            "migration_id = N'PS-SETTINGS-EXPORT-007'",
        ):
            self.assertNotIn(fragment, self.forward)
        for fragment in (
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.connection_preferences', N'U') IS NULL",
            "OBJECT_ID(N'dbo.notification_preferences', N'U') IS NULL",
            "OBJECT_ID(N'dbo.user_consents', N'U') IS NULL",
        ):
            self.assertIn(fragment, self.forward)

    # -- @UserKey-only signature ------------------------------------------

    def test_every_reader_signature_is_exactly_user_key_and_nothing_else(self):
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                sig = signature(self.procedures[name], name)
                self.assertEqual(sig.strip(), "@UserKey nvarchar(300)")

    # -- byte-identical identity header ------------------------------------

    def test_every_reader_shares_the_byte_identical_identity_header(self):
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(IDENTITY_HEADER, self.procedures[name])

    def test_identity_header_is_byte_identical_across_every_account_export_reader_in_the_program(self):
        # This package's three additions must not introduce a second
        # distinct identity-header variant anywhere in the whole
        # account-export reader program (PS-SETTINGS-EXPORT-003 through
        # this package).
        headers = set()
        procedure_count = 0
        for path in ACCOUNT_EXPORT_FORWARD_FILES:
            if not path.exists():
                continue
            sql = read(path)
            for procedure_name, body in procedure_batches(sql).items():
                if not procedure_name.startswith("usp_ReadAccountExport"):
                    continue
                procedure_count += 1
                headers.add(extract_identity_header(body))
        self.assertGreaterEqual(procedure_count, len(READER_PROCEDURES) + 1)
        self.assertEqual(
            len(headers), 1,
            msg=f"found {len(headers)} distinct identity-header variants across the program",
        )
        self.assertEqual(headers.pop(), IDENTITY_HEADER)

    def test_identity_resolution_matches_c1_owner_procedures(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("app_user.user_key = @UserKey", body)
                self.assertIn("app_user.active = 1", body)
                self.assertIn("profile.active = 1", body)

    # -- owner predicate presence -----------------------------------------

    def test_every_reader_filters_by_every_owner_predicate_its_chain_needs(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            for predicate in OWNER_PREDICATES[name]:
                with self.subTest(procedure=name, predicate=predicate):
                    self.assertIn(predicate, body)

    # -- join shape ----------------------------------------------------------

    def test_join_count_matches_the_chain_depth_per_procedure(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertEqual(len(re.findall(r"\bJOIN dbo\.", body)), EXPECTED_JOIN_COUNT[name])
                self.assertIn("JOIN dbo.app_users AS app_user", body)

    # -- ORDER BY presence and shape ----------------------------------------------------

    def test_every_reader_has_a_deterministic_order_by(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("ORDER BY", body)
                self.assertNotIn("SELECT *", body)
                self.assertNotIn("SELECT*", body)

    def test_connection_preference_reader_orders_by_its_own_excluded_user_id(self):
        # Mirrors usp_ReadAccountExportAccountForOwner's own "ORDER BY
        # app_user.id" idiom of ordering by an excluded internal column
        # -- at most one row can exist per owner (PK_connection_preferences
        # (user_id) alone), so this is already fully deterministic.
        body = self.procedures["usp_ReadAccountExportConnectionPreferenceForOwner"]
        order_by = body[body.index("ORDER BY"):]
        self.assertIn("preference.user_id", order_by)

    def test_notification_preference_reader_orders_by_notification_type(self):
        # PK_notification_preferences (user_id, notification_type) --
        # notification_type alone is unique once user_id is fixed by the
        # WHERE predicate.
        body = self.procedures["usp_ReadAccountExportNotificationPreferenceForOwner"]
        order_by = body[body.index("ORDER BY"):]
        self.assertIn("preference.notification_type", order_by)

    def test_user_consent_reader_orders_by_code_then_time_then_surrogate_tiebreak(self):
        # IX_user_consents_history (user_id, consent_code, recorded_at_utc
        # DESC) is NOT a unique index, so consent_code + recorded_at_utc
        # alone cannot be proven collision-free; the trailing
        # user_consent_id tiebreak (excluded from output) makes the order
        # fully deterministic even in a same-timestamp tie.
        body = self.procedures["usp_ReadAccountExportUserConsentForOwner"]
        order_by = body[body.index("ORDER BY"):]
        expected_order = ("consent.consent_code", "consent.recorded_at_utc", "consent.user_consent_id")
        positions = [order_by.index(term) for term in expected_order]
        self.assertEqual(positions, sorted(positions), msg=order_by)

    # -- read-window columns ----------------------------------------------------

    def test_every_reader_returns_the_read_window_as_trailing_columns(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("@ReadStartedAtUtc AS read_started_at_utc", body)
                self.assertIn("SYSUTCDATETIME() AS read_ended_at_utc", body)
                self.assertEqual(body.count("SELECT"), 2)

    # -- forbidden-field canary, exact allowlist pinning -------------------------

    def test_forbidden_fields_are_absent_from_every_readers_output(self):
        for name in READER_PROCEDURES:
            columns = set(content_select_columns(self.procedures[name]))
            with self.subTest(procedure=name):
                overlap = columns & FORBIDDEN_FIELDS[name]
                self.assertFalse(overlap, msg=f"{name} selects forbidden column(s) {overlap}")

    def test_every_directive_category_column_is_a_subset_of_forbidden_fields(self):
        all_forbidden = set()
        for fields in FORBIDDEN_FIELDS.values():
            all_forbidden |= fields
        for category, columns in DIRECTIVE_CATEGORY_COLUMNS.items():
            with self.subTest(category=category):
                self.assertTrue(columns.issubset(all_forbidden), msg=columns - all_forbidden)

    def test_every_directive_category_is_actually_absent_from_every_readers_output(self):
        all_forbidden = set()
        for columns in DIRECTIVE_CATEGORY_COLUMNS.values():
            all_forbidden |= columns
        for name in READER_PROCEDURES:
            columns = set(content_select_columns(self.procedures[name]))
            with self.subTest(procedure=name):
                self.assertFalse(columns & all_forbidden)

    def test_unverified_field_column_is_a_subset_of_forbidden_fields(self):
        all_forbidden = set()
        for fields in FORBIDDEN_FIELDS.values():
            all_forbidden |= fields
        self.assertTrue(UNVERIFIED_FIELD_COLUMNS.issubset(all_forbidden), msg=UNVERIFIED_FIELD_COLUMNS - all_forbidden)

    def test_unverified_field_column_is_actually_absent_from_every_readers_output(self):
        for name in READER_PROCEDURES:
            columns = set(content_select_columns(self.procedures[name]))
            with self.subTest(procedure=name):
                self.assertFalse(columns & UNVERIFIED_FIELD_COLUMNS)

    def test_domains_field_allowlist_matches_the_actual_sql_output_exactly_in_order(self):
        # domain_field_map() walks the entire shared DOMAINS dict; this
        # test owns and checks only this package's own three, asserting
        # they are present (a subset) and exactly match in order -- never
        # that nothing else (e.g. the sibling packages') has been added.
        expected_by_procedure = domain_field_map()
        self.assertTrue(set(READER_PROCEDURES).issubset(set(expected_by_procedure)))
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                actual = content_select_columns(self.procedures[name])
                expected = list(expected_by_procedure[name])
                self.assertEqual(actual, expected)

    # -- dormant-feature disclosure label -----------------------------------

    def test_both_preference_readers_emit_the_dormant_feature_label(self):
        for name in DORMANT_LABEL_READERS:
            with self.subTest(procedure=name):
                columns = content_select_columns(self.procedures[name])
                self.assertIn("feature_status", columns)
                self.assertIn(f"N''{DORMANT_LABEL_VALUE}''", self.procedures[name])

    def test_consent_reader_does_not_emit_any_dormant_feature_label(self):
        for name in NO_DORMANT_LABEL_READERS:
            with self.subTest(procedure=name):
                columns = content_select_columns(self.procedures[name])
                self.assertNotIn("feature_status", columns)
                self.assertNotIn(DORMANT_LABEL_VALUE, self.procedures[name])

    # -- structural safety: no transaction control, no write, no dynamic SQL ----

    def test_no_reader_contains_transaction_control_a_write_or_dynamic_sql(self):
        forbidden_fragments = (
            "BEGIN TRAN", "COMMIT", "ROLLBACK", "BEGIN TRY", "BEGIN CATCH",
            "INSERT ", "UPDATE ", "DELETE ", "EXEC",
        )
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            for fragment in forbidden_fragments:
                with self.subTest(procedure=name, fragment=fragment):
                    self.assertNotIn(fragment, body)

    def test_no_reader_accepts_a_caller_selected_owner_or_target(self):
        forbidden_params = (
            "@OwnerUserId", "@OwnerProfileId", "@TableName", "@ProfileKey",
            "@ConsentCode", "@NotificationType", "@Url",
        )
        for name in READER_PROCEDURES:
            sig = signature(self.procedures[name], name)
            for forbidden in forbidden_params:
                with self.subTest(procedure=name, param=forbidden):
                    self.assertNotIn(forbidden, sig)

    def test_no_grant_or_identity_creation_in_this_migration(self):
        executable = executable_body(self.forward)
        self.assertIsNone(re.search(r"\bGRANT\b", executable))
        self.assertNotIn("CREATE ROLE", executable)
        self.assertNotIn("CREATE USER", executable)
        self.assertNotIn("sp_addrolemember", executable)

    def test_no_caller_selected_dynamic_table_name(self):
        dynamic_exec = re.compile(r"EXEC(UTE)?\s*\(\s*@")
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("sp_executesql", body)
                self.assertIsNone(dynamic_exec.search(body))

    # -- ledger self-description budget ------------------------------------------

    def test_ledger_description_fits_the_nvarchar_500_column_with_margin(self):
        match = re.search(
            r"N'PS-SETTINGS-EXPORT-008',\s*\n\s*N'([^']*(?:''[^']*)*)',",
            self.forward,
        )
        self.assertIsNotNone(match, "could not locate the ledger description literal")
        description = match.group(1).replace("''", "'")
        self.assertLessEqual(len(description), 450, msg=description)

    # -- rollback -----------------------------------------------------------

    def test_rollback_drops_every_claimed_procedure_and_nothing_else(self):
        for name in READER_PROCEDURES:
            self.assertIn(f"DROP PROCEDURE dbo.{name}", self.rollback)
        self.assertNotIn("DROP TABLE", self.rollback)
        self.assertNotIn("DROP TRIGGER", self.rollback)

    def test_rollback_removes_only_this_migrations_ledger_row(self):
        self.assertIn(
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-008'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-PLAT-004'", self.rollback)
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.rollback)

    # -- registry -------------------------------------------------------------

    def test_registry_entry_shape_and_requires(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-008", entries)
        entry = entries["PS-SETTINGS-EXPORT-008"]
        # PS-AUTH-001 is required because the paired verification script
        # provisions its synthetic owners through usp_UpsertAppUserFromAuth
        # -- named from the start, matching every package since
        # PS-SETTINGS-EXPORT-003's own gate round had to add this after
        # the fact. PS-PLAT-004 is the one migration that creates all
        # three of this package's tables.
        self.assertEqual(
            entry["requires"],
            ["PS-AUTH-001", "PS-PLAT-004"],
        )
        for prerequisite in entry["requires"]:
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(ids.index(prerequisite), ids.index("PS-SETTINGS-EXPORT-008"))
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-008_preferences_consent_reader.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-008_preferences_consent_reader_rollback.sql",
        )
        self.assertTrue(entry["summary"])
        self.assertLessEqual(len(entry["summary"]), 450)

    def test_registry_entry_pins_the_sealed_gate(self):
        """SEALED STATE (replaced in the same lockstep commit as the gate
        block and the report's Gate state section, per the placeholder's own
        instruction -- registry + test + REPORT). Literal pins the SEAL;
        recomputation pins the FILE. First-run full pass on disposable
        ps-migration-path-20260830-pc -- the first INSERT exercise of
        notification_preferences' and user_consents' constraint sets
        anywhere in this reader program."""
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        entry = entries["PS-SETTINGS-EXPORT-008"]
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual(
            gate["executable_sha256"],
            "b92a301e0d3616b3baedb1236eedea4d45a74430c84ad5e2e9b3adfde5eccd94",
        )
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(len(gate["objects"]), 3)
        self.assertTrue(all(
            o.startswith("SQL_STORED_PROCEDURE:dbo.usp_ReadAccountExport")
            for o in gate["objects"]
        ))
        self.assertEqual(
            gate["verification"],
            "PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql returned verified = 1",
        )

    def test_registry_ids_are_unique(self):
        document = json.loads(read(REGISTRY))
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertEqual(len(ids), len(set(ids)))

    # -- verification script structural properties -----------------------------

    def test_verify_provisions_synthetic_owners_and_never_commits(self):
        self.assertIn("usp_UpsertAppUserFromAuth", self.verify)
        self.assertNotIn("COMMIT TRANSACTION", self.verify)
        self.assertIn("ROLLBACK TRANSACTION;", self.verify)
        deliberate_rollback = self.verify.index("ROLLBACK TRANSACTION;\n\n    SELECT")
        self.assertGreater(deliberate_rollback, self.verify.index("UPDATE dbo.app_users SET active = 0"))

    def test_verify_uses_bare_exec_for_every_reader(self):
        bare_calls = set(re.findall(r"^\s*EXEC dbo\.(\w+)", self.verify, re.MULTILINE))
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(name, bare_calls)

    def test_verify_also_uses_insert_exec_for_every_reader_for_value_level_proof(self):
        insert_exec_calls = set(re.findall(r"INSERT @\w+ EXEC dbo\.(\w+)", self.verify))
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(name, insert_exec_calls)

    def test_verify_provisions_three_owners_including_a_deactivated_one(self):
        self.assertIn("@SubjectA", self.verify)
        self.assertIn("@SubjectB", self.verify)
        self.assertIn("@SubjectC", self.verify)
        self.assertIn("SET active = 0 WHERE id = @UserIdC", self.verify)

    def test_verify_asserts_read_window_presence_and_monotonicity(self):
        self.assertIn("read_started_at_utc IS NULL OR read_ended_at_utc IS NULL", self.verify)
        self.assertIn("read_ended_at_utc < read_started_at_utc", self.verify)

    def test_verify_fixture_populates_every_directive_excluded_column_with_a_real_value(self):
        all_excluded = set()
        for columns in DIRECTIVE_CATEGORY_COLUMNS.values():
            all_excluded |= columns
        for column in all_excluded:
            with self.subTest(column=column):
                self.assertIn(column, self.verify)

    def test_verify_fixture_populates_the_unverified_field_column_with_a_real_value(self):
        for column in UNVERIFIED_FIELD_COLUMNS:
            with self.subTest(column=column):
                self.assertIn(column, self.verify)

    def test_verify_marks_every_consent_evidence_canary_as_must_never_be_readable(self):
        self.assertGreaterEqual(self.verify.count("must never be readable"), 4)

    def test_verify_proves_the_connection_preferences_auto_seed_precondition(self):
        # An INSERT into connection_preferences for a synthetic owner
        # would violate PK_connection_preferences (user_id) if the
        # auto-seed did not already run via usp_UpsertAppUserFromAuth;
        # this script updates the pre-existing row instead and proves it
        # via @@ROWCOUNT.
        self.assertNotIn("INSERT dbo.connection_preferences", self.verify)
        self.assertIn("UPDATE dbo.connection_preferences", self.verify)
        self.assertIn("auto-seeded connection_preferences row was not found to update", self.verify)

    def test_verify_proves_the_withdrawn_after_accepted_consent_history(self):
        self.assertIn("N'withdrawn'", self.verify)
        self.assertIn("Paper 3 requires the full history, including withdrawal", self.verify)
        # The two events for owner A's shared consent code are recorded
        # against the SAME captured variable (@ConsentRecordedAtUtcA12),
        # a deliberately identical recorded_at_utc, proving the reader's
        # own surrogate-id tiebreak handles a genuine same-timestamp
        # collision rather than merely arguing it from the DDL.
        self.assertGreaterEqual(self.verify.count("@ConsentRecordedAtUtcA12"), 3)
        self.assertIn("deliberately-identical recorded_at_utc", self.verify)

    def test_verify_never_references_recruiter_questions(self):
        # The header comment names dbo.recruiter_questions explicitly, by
        # design, to document that this script never touches it (see
        # this file's own header, "NO THIRD-PARTY CONSENT"); the
        # executable body -- every fixture, capture, and assertion -- must
        # not.
        self.assertNotIn("recruiter_questions", executable_body(self.verify))

    def test_verify_never_references_unrelated_sibling_machinery_tables(self):
        # Sanity: this package's own fixture never accidentally reaches
        # into a sibling package's excluded machinery table or an
        # out-of-scope table.
        for name in (
            "knowledge_item_save_requests", "career_skill_links", "slate_entities",
            "opportunity_saved_results", "moment_placements", "voice_media_sources",
        ):
            with self.subTest(table=name):
                self.assertNotIn(name, self.verify)


class AdapterModuleTests(unittest.TestCase):
    """Offline tests for services/account_export_domain_readers.py using
    fake cursors/connections only -- no database, no network."""

    class _FakeCursor:
        def __init__(self, plan):
            self.plan = list(plan)
            self.description = None
            self._rows = []
            self.executed = []

        def execute(self, sql, params=None):
            self.executed.append((sql, params))
            step = self.plan.pop(0)
            kind = step[0]
            if kind == "clock":
                self.description = [("now_utc",)]
                self._rows = [(step[1],)]
            elif kind == "content":
                self.description = step[1]
                self._rows = step[2]
            elif kind == "none":
                self.description = None
                self._rows = []
            else:
                raise AssertionError(f"unknown fake step {kind}")

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return list(self._rows)

    class _FakeConnection:
        def __init__(self, plan):
            self._plan = plan
            self.cursor_calls = 0

        def cursor(self):
            self.cursor_calls += 1
            return AdapterModuleTests._FakeCursor(self._plan)

        def commit(self):
            raise AssertionError("adapter must never commit the caller's connection")

        def rollback(self):
            raise AssertionError("adapter must never roll back the caller's connection")

        def close(self):
            raise AssertionError("adapter must never close the caller's connection")

    THIS_PACKAGES_READERS = (
        readers_module.read_connection_preference,
        readers_module.read_notification_preference,
        readers_module.read_user_consent,
    )

    def test_every_new_domain_function_is_independently_callable(self):
        for function in self.THIS_PACKAGES_READERS:
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(procedure=function.procedure_name):
                result = function(connection, "some-user-key")
                self.assertEqual(result["rows"], [])
                self.assertEqual(result["read_started_at_utc"], "S")
                self.assertEqual(result["read_ended_at_utc"], "E")

    def test_unresolved_identity_returns_empty_rows_not_an_error(self):
        for function in self.THIS_PACKAGES_READERS:
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(procedure=function.procedure_name):
                result = function(connection, "forged-key")
                self.assertEqual(result, {"rows": [], "read_started_at_utc": "S", "read_ended_at_utc": "E"})

    def test_notification_preference_legitimately_empty_result_is_not_an_error(self):
        # dbo.notification_preferences has no writer anywhere in this
        # codebase -- a REAL owner (a resolved identity, not merely a
        # forged key) can legitimately have zero rows here today. The
        # adapter must report a clean empty read, using the fallback
        # clock window, never raise. Corrected in the independent-review
        # round: a resolved owner with an empty table produces a result
        # set WITH a column description and zero rows -- not the
        # description-less shape an unresolved identity produces (that
        # path is the test above) -- so this plan models the real cursor
        # shape.
        description = [
            ("notification_type",), ("in_app_enabled",), ("email_enabled",),
            ("quiet_hours_start",), ("quiet_hours_end",), ("updated_at_utc",),
            ("feature_status",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        plan = [("clock", "FALLBACK-S"), ("content", description, []), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_notification_preference(connection, "a-real-resolved-key")
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["read_started_at_utc"], "FALLBACK-S")
        self.assertEqual(result["read_ended_at_utc"], "FALLBACK-E")

    def test_connection_preference_content_row_decodes_every_field_and_the_dormant_label(self):
        description = [
            ("discovery_opt_in",), ("goal_matching_opt_in",), ("recruiter_discovery_opt_in",),
            ("discoverable_audience",), ("updated_at_utc",), ("feature_status",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (True, False, False, "private", "2020-01-01", "dormant_not_yet_enforced", "SQL-START", "SQL-END")
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_connection_preference(connection, "real-key")
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("read_started_at_utc", result["rows"][0])
        self.assertNotIn("read_ended_at_utc", result["rows"][0])
        self.assertEqual(result["rows"][0]["discoverable_audience"], "private")
        self.assertEqual(result["rows"][0]["feature_status"], "dormant_not_yet_enforced")
        self.assertEqual(result["read_started_at_utc"], "SQL-START")
        self.assertEqual(result["read_ended_at_utc"], "SQL-END")

    def test_notification_preference_content_row_decodes_quiet_hours_and_the_dormant_label(self):
        description = [
            ("notification_type",), ("in_app_enabled",), ("email_enabled",),
            ("quiet_hours_start",), ("quiet_hours_end",), ("updated_at_utc",), ("feature_status",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = ("capture_ready", True, True, "22:00:00", "07:00:00", "2020-01-01", "dormant_not_yet_enforced", "S", "E")
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_notification_preference(connection, "real-key")
        self.assertEqual(result["rows"][0]["notification_type"], "capture_ready")
        self.assertEqual(result["rows"][0]["quiet_hours_start"], "22:00:00")
        self.assertEqual(result["rows"][0]["feature_status"], "dormant_not_yet_enforced")

    def test_user_consent_content_row_decodes_every_field_and_carries_no_dormant_label(self):
        description = [
            ("consent_code",), ("policy_version",), ("consent_status",), ("recorded_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = ("settings.marketing_email", "2026-08-01.v1", "withdrawn", "2020-01-02", "S", "E")
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_user_consent(connection, "real-key")
        self.assertEqual(result["rows"][0]["consent_code"], "settings.marketing_email")
        self.assertEqual(result["rows"][0]["consent_status"], "withdrawn")
        self.assertNotIn("feature_status", result["rows"][0])

    def test_adapter_never_manages_connection_lifetime(self):
        for function in self.THIS_PACKAGES_READERS:
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(procedure=function.procedure_name):
                function(connection, "some-user-key")
                self.assertEqual(connection.cursor_calls, 1)

    def test_call_reader_binds_user_key_as_a_parameter_never_string_formatted_in(self):
        class CapturingCursor(AdapterModuleTests._FakeCursor):
            def __init__(self, plan, sink):
                super().__init__(plan)
                self._sink = sink

            def execute(self, sql, params=None):
                if "EXEC dbo." in sql:
                    self._sink["sql"] = sql
                    self._sink["params"] = params
                super().execute(sql, params)

        class CapturingConnection:
            def __init__(self, plan, sink):
                self._plan = plan
                self._sink = sink

            def cursor(self):
                return CapturingCursor(self._plan, self._sink)

        for function in self.THIS_PACKAGES_READERS:
            captured = {}
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = CapturingConnection(plan, captured)
            with self.subTest(procedure=function.procedure_name):
                function(connection, "a-real-looking-user-key")
                self.assertIn(f"EXEC dbo.{function.procedure_name} @UserKey = ?;", captured["sql"])
                self.assertEqual(captured["params"], ("a-real-looking-user-key",))
                self.assertNotIn("a-real-looking-user-key", captured["sql"])

    def test_every_included_reader_across_the_program_is_still_callable(self):
        # Cheap regression net: this package's edits to the shared DOMAINS
        # dict must not disturb any sibling package's own readers.
        for domain_code, reader_entry in iter_included_readers():
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(domain=domain_code, procedure=reader_entry["procedure"]):
                result = reader_entry["function"](connection, "some-user-key")
                self.assertEqual(result["rows"], [])


class DomainsRegistryTests(unittest.TestCase):
    """Offline shape tests for the DOMAINS registry itself, scoped to this
    package's own three domains -- never to "however many domains the
    shared dict currently totals," which would break the moment a future
    package legitimately adds another."""

    _THIS_PACKAGES_DOMAINS = (
        "connection_preferences", "notification_preferences", "consent_history",
    )

    def test_all_three_domains_are_included_with_exactly_one_reader_each(self):
        expected_procedures = {
            "connection_preferences": "usp_ReadAccountExportConnectionPreferenceForOwner",
            "notification_preferences": "usp_ReadAccountExportNotificationPreferenceForOwner",
            "consent_history": "usp_ReadAccountExportUserConsentForOwner",
        }
        for code in self._THIS_PACKAGES_DOMAINS:
            domain = DOMAINS[code]
            with self.subTest(domain=code):
                self.assertEqual(domain["disposition"], "included")
                self.assertIsNone(domain["reason"])
                self.assertEqual(len(domain["readers"]), 1)
                self.assertEqual(domain["readers"][0]["procedure"], expected_procedures[code])

    def test_included_domains_have_no_reason_others_have_a_stable_reason(self):
        for code, domain in DOMAINS.items():
            with self.subTest(domain=code):
                if domain["disposition"] == "included":
                    self.assertIsNone(domain["reason"])
                    self.assertTrue(domain["readers"])
                else:
                    self.assertIn(domain["disposition"], ("excluded", "unavailable"))
                    self.assertIsInstance(domain["reason"], str)
                    self.assertTrue(domain["reason"].strip())
                    self.assertEqual(domain["readers"], ())

    def test_no_domain_reason_leaks_a_forbidden_field_name(self):
        forbidden_terms = ("user_key", "auth_subject", "row_version", "profile_key", "evidence_json")
        for code, domain in DOMAINS.items():
            reason = domain["reason"] or ""
            for term in forbidden_terms:
                with self.subTest(domain=code, term=term):
                    self.assertNotIn(term, reason)

    def test_reader_entries_have_unique_procedures_and_schema_ids_across_the_whole_dict(self):
        procedures = []
        schema_ids = []
        for domain in DOMAINS.values():
            for reader_entry in domain["readers"]:
                procedures.append(reader_entry["procedure"])
                schema_ids.append(reader_entry["schema_id"])
        self.assertEqual(len(procedures), len(set(procedures)))
        self.assertEqual(len(schema_ids), len(set(schema_ids)))
        for schema_id in schema_ids:
            self.assertRegex(schema_id, r"^peerslate\.account_export\.[a-z_]+\.[a-z_]+\.v1$")


if __name__ == "__main__":
    unittest.main()
