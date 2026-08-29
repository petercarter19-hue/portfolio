"""Contracts for PS-SETTINGS-EXPORT-006, the account-export Opportunity
Slate readers (replacement package 4, the FINAL content reader of the
2026-08-29 reader topology).

Modeled directly on tests/test_settings_export_workshop_reader.py
(replacement package 3, main 7d6b0ea1, gate passed on the first run):
registry completeness/digest-pending assertions plus focused structural
assertions for the enforcement rules the lane claim and
docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
require that a static read of the SQL/Python text can express without a live
database. Also pins services/account_export_domain_readers.py's DOMAINS
registry against the actual SQL output column lists, and exercises the
adapter's row/read-window decoding with fake cursors.

Every DOMAINS-scoped assertion below is scoped to THIS package's own one
domain ("opportunity_slate"), never to "whatever the whole DOMAINS dict
currently contains" -- the lesson package 1's own test file needed applied
retroactively and every later package has followed since.

THE CENTRAL FINDING THIS TEST FILE PINS: of the fifteen tables created
across PS-OPPSLATE-001/002/004 (eight OS-1/OS-2 tables, four OS-3 tables,
three "replacement" R1 tables), NONE is read by this package. Every one of
them is ephemeral working-session state, cascade-deleted by
usp_PurgeExpiredOpportunityWorkingData/usp_DeleteOpportunityWorkingSessionForOwner
-- confirmed by reading PS-OPPSLATE-004's own DELETE statements against its
own three new tables, not assumed from the "replacement" migration's name.
Only PS-OPPSLATE-003's four tables (opportunity_slates,
opportunity_saved_results, opportunity_saved_qualifications,
opportunity_saved_evidence) are durable, and only those four are read here.
Several tests below assert the NEGATIVE space explicitly (no reader
references any of the fifteen excluded table names) precisely because this
finding overturned the writer brief's own "expect" framing at write time.
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
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-006_oppslate_reader.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-006_oppslate_reader_rollback.sql"
VERIFY = VERIFICATION / "PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
ADAPTER_SOURCE_PATH = ROOT / "services" / "account_export_domain_readers.py"

READER_PROCEDURES = (
    "usp_ReadAccountExportOpportunitySlateForOwner",
    "usp_ReadAccountExportOpportunitySavedResultForOwner",
    "usp_ReadAccountExportOpportunitySavedQualificationForOwner",
    "usp_ReadAccountExportOpportunitySavedEvidenceForOwner",
)

# Every owner predicate each procedure needs, one per joined table -- the
# leaf table first, then each ancestor in join order. All four tables under
# read independently carry their own owner_profile_id (confirmed by reading
# PS-OPPSLATE-003's own DDL), so the predicate COUNT itself is a load-bearing
# fact this package's chain depth introduces that no sibling package needed.
OWNER_PREDICATES = {
    "usp_ReadAccountExportOpportunitySlateForOwner": (
        "slate.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportOpportunitySavedResultForOwner": (
        "saved_result.owner_profile_id = @ProfileId",
        "slate.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportOpportunitySavedQualificationForOwner": (
        "qualification.owner_profile_id = @ProfileId",
        "saved_result.owner_profile_id = @ProfileId",
        "slate.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportOpportunitySavedEvidenceForOwner": (
        "evidence.owner_profile_id = @ProfileId",
        "qualification.owner_profile_id = @ProfileId",
        "saved_result.owner_profile_id = @ProfileId",
        "slate.owner_profile_id = @ProfileId",
    ),
}

# How many "JOIN dbo." occurrences each procedure body should contain,
# INCLUDING the shared identity header's own "JOIN dbo.app_users". The
# slate reader has no content-level join at all (parity with
# PS-SETTINGS-EXPORT-005's knowledge_items reader); each descendant reader
# joins one more ancestor than the last.
EXPECTED_JOIN_COUNT = {
    "usp_ReadAccountExportOpportunitySlateForOwner": 1,
    "usp_ReadAccountExportOpportunitySavedResultForOwner": 2,
    "usp_ReadAccountExportOpportunitySavedQualificationForOwner": 3,
    "usp_ReadAccountExportOpportunitySavedEvidenceForOwner": 4,
}

# Forbidden OUTPUT field names (unqualified, as they appear after
# aliasing/dot-stripping) per procedure. A full-name set, never a substring
# list -- PS-SETTINGS-EXPORT-003's own paused-predecessor design notes
# record a naive substring scan false-positiving on legitimate columns.
FORBIDDEN_FIELDS = {
    "usp_ReadAccountExportOpportunitySlateForOwner": {
        "opportunity_slate_id", "owner_profile_id", "row_version",
    },
    "usp_ReadAccountExportOpportunitySavedResultForOwner": {
        "opportunity_saved_result_id", "opportunity_slate_id", "owner_profile_id",
        "source_text", "saved_analysis_key", "model_name", "prompt_contract_version",
        "idempotency_key", "saved_by_user_id", "row_version",
    },
    "usp_ReadAccountExportOpportunitySavedQualificationForOwner": {
        "opportunity_saved_qualification_id", "opportunity_saved_result_id", "owner_profile_id",
        "employer_text", "response_kind", "response_text", "authored_via",
        "connected_evidence_title", "connected_evidence_version", "row_version",
    },
    "usp_ReadAccountExportOpportunitySavedEvidenceForOwner": {
        "opportunity_saved_evidence_id", "opportunity_saved_qualification_id", "owner_profile_id",
        "covered_text", "evidence_kind", "evidence_key", "evidence_version",
        "evidence_title", "excerpt", "row_version",
    },
}

# The owner's 2026-08-29 directive's four hard-exclusion categories, each
# named with the exact columns this package found carrying that category's
# content. Every one of these must appear in FORBIDDEN_FIELDS above (belt)
# and must never appear in any procedure's actual output (suspenders,
# checked directly against DOMAINS in
# test_every_directive_category_is_actually_absent_from_every_readers_output).
DIRECTIVE_CATEGORY_COLUMNS = {
    "third_party_posting_text": {"source_text", "employer_text", "covered_text"},
    "evidence_links": {
        "evidence_kind", "evidence_key", "evidence_version", "evidence_title", "excerpt",
        "connected_evidence_title", "connected_evidence_version",
    },
    "responses": {
        "response_kind", "response_text", "authored_via",
        "connected_evidence_title", "connected_evidence_version",
    },
    # saved_analysis_key joined this category in the independent-review
    # correction round: it is a generation-run identifier ("Model
    # names/ids"), reversing the writer's original keep, whose stated
    # premise ("neither is a name, id, ...") was factually wrong.
    "ai_model_provenance": {"model_name", "prompt_contract_version", "saved_analysis_key"},
}

# Every table created across PS-OPPSLATE-001 (OS-1/OS-2), PS-OPPSLATE-002
# (OS-3), and PS-OPPSLATE-004 ("the replacement" R1 shell) -- all fifteen
# confirmed ephemeral (cascade-purged with the working session) and
# therefore read by NONE of this package's four procedures. See this
# module's own docstring and the migration file's own header for the proof.
EPHEMERAL_TABLES = (
    "opportunity_working_sessions", "opportunity_sources", "opportunity_source_versions",
    "opportunity_source_reviews", "opportunity_source_concerns",
    "opportunity_requirement_sets", "opportunity_requirement_set_versions",
    "opportunity_requirement_statements",
    "opportunity_analyses", "opportunity_analysis_statements",
    "opportunity_analysis_citations", "opportunity_responses",
    "opportunity_source_identities", "opportunity_requirement_review_events",
    "opportunity_member_takes",
)

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
    order. Located precisely between the shared identity header's closing
    "IF @ProfileId IS NULL RETURN;" line and the procedure's own first
    subsequent FROM clause -- every ancestor beyond the driving table is
    joined via "JOIN dbo....", never a second "FROM dbo....", so this
    generic anchor (identical to every prior package's own helper) locates
    the correct boundary regardless of how many tables a given procedure
    joins."""

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


def domain_field_map():
    """procedure_name -> fields tuple, from DOMAINS (every domain, not only
    included ones, though only included domains carry readers)."""

    mapping = {}
    for domain in DOMAINS.values():
        for reader_entry in domain["readers"]:
            mapping[reader_entry["procedure"]] = reader_entry["fields"]
    return mapping


class SettingsExportOppslateReaderMigrationTests(unittest.TestCase):
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
            ("forward", self.forward, 58600, 58699),
            ("rollback", self.rollback, 58600, 58699),
        ):
            with self.subTest(file=label):
                numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)), "THROW numbers must be unique in this file")
                self.assertTrue(all(low <= n <= high for n in numbers), numbers)

    def test_verify_throw_numbers_are_in_its_own_reserved_range(self):
        # Unlike the forward/rollback files, the structural loop in section
        # 0 deliberately reuses a handful of numbers once per procedure
        # iteration -- uniqueness is not asserted here, matching every
        # prior package's own verify-file test.
        numbers = [int(n) for n in re.findall(r"THROW (\d+),", self.verify)]
        self.assertTrue(numbers)
        self.assertTrue(all(58700 <= n <= 58799 for n in numbers), numbers)

    def test_throw_ranges_are_fresh_against_every_sibling_sql_file(self):
        own_files = {FORWARD, ROLLBACK, VERIFY}
        sql_root = ROOT / "SQL FIles"
        for path in sql_root.rglob("*.sql"):
            if path in own_files:
                continue
            source = read(path)
            numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
            colliding = [n for n in numbers if 58600 <= n <= 58799]
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
            if entry["id"] != "PS-SETTINGS-EXPORT-006"
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

    # -- prerequisite guards match the registry's requires list ----------

    def test_forward_requires_exactly_the_oppslate_chain(self):
        for fragment in (
            "migration_id = N'PS-OPPSLATE-001'",
            "migration_id = N'PS-OPPSLATE-002'",
            "migration_id = N'PS-OPPSLATE-003'",
        ):
            self.assertIn(fragment, self.forward)
        # PS-AUTH-001 is a registry-level requirement only (the paired
        # verification script's usp_UpsertAppUserFromAuth dependency); the
        # migration body itself never checks for it -- app_users/
        # member_profiles' identity-resolution columns predate PS-AUTH-001,
        # exactly every prior package's recorded reasoning for the
        # identical omission.
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.forward)
        # PS-OPPSLATE-004 ("the replacement") is deliberately NOT a
        # dependency: none of its objects (opportunity_source_identities,
        # opportunity_requirement_review_events, opportunity_member_takes,
        # or the three additive columns on opportunity_analyses/
        # opportunity_requirement_sets) are read by this package.
        self.assertNotIn("migration_id = N'PS-OPPSLATE-004'", self.forward)
        for fragment in (
            "migration_id = N'PS-WORKSHOP-001'",
            "migration_id = N'PS-WORKSHOP-002'",
            "migration_id = N'PS-SETTINGS-EXPORT-001'",
            "migration_id = N'PS-SETTINGS-EXPORT-003'",
            "migration_id = N'PS-SETTINGS-EXPORT-004'",
            "migration_id = N'PS-SETTINGS-EXPORT-005'",
        ):
            self.assertNotIn(fragment, self.forward)
        for fragment in (
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.opportunity_slates', N'U') IS NULL",
            "OBJECT_ID(N'dbo.opportunity_saved_results', N'U') IS NULL",
            "OBJECT_ID(N'dbo.opportunity_saved_qualifications', N'U') IS NULL",
            "OBJECT_ID(N'dbo.opportunity_saved_evidence', N'U') IS NULL",
        ):
            self.assertIn(fragment, self.forward)

    def test_no_reader_references_any_ephemeral_working_session_table(self):
        # The central finding this test file exists to pin: all fifteen
        # tables PS-OPPSLATE-001/002/004 create are ephemeral, and none of
        # them is referenced by any of this package's four reader bodies
        # (never mind selected from -- not even joined or mentioned).
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            for table in EPHEMERAL_TABLES:
                with self.subTest(procedure=name, table=table):
                    self.assertNotIn(f"dbo.{table}", body)

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

    def test_identity_resolution_matches_c1_owner_procedures(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("app_user.user_key = @UserKey", body)
                self.assertIn("app_user.active = 1", body)
                self.assertIn("profile.active = 1", body)

    # -- owner predicate presence, every table in the chain -----------------

    def test_every_reader_filters_by_every_owner_predicate_its_chain_needs(self):
        # All four tables independently carry their own owner_profile_id;
        # every reader must assert the predicate on every table it joins,
        # not merely the leaf -- the "owner predicate on every side"
        # defense in depth PS-SETTINGS-EXPORT-004/005 introduced, extended
        # here across a four-level chain.
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            for predicate in OWNER_PREDICATES[name]:
                with self.subTest(procedure=name, predicate=predicate):
                    self.assertIn(predicate, body)

    def test_every_reader_asserts_the_joined_slates_visibility_predicate(self):
        # Every descendant reader joins all the way up to
        # dbo.opportunity_slates for exactly this predicate -- the
        # "never trust the default" discipline PS-SETTINGS-EXPORT-005
        # applied to dbo.knowledge_items even though the column is
        # CHECK-locked today.
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn("slate.visibility = N''private''", self.procedures[name])

    def test_join_count_matches_the_chain_depth_per_procedure(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertEqual(len(re.findall(r"\bJOIN dbo\.", body)), EXPECTED_JOIN_COUNT[name])
        # The slate reader's one join is the identity header's own.
        self.assertIn(
            "JOIN dbo.app_users AS app_user",
            self.procedures["usp_ReadAccountExportOpportunitySlateForOwner"],
        )

    def test_descendant_readers_join_every_ancestor_table_by_name(self):
        chain = {
            "usp_ReadAccountExportOpportunitySavedResultForOwner": ("dbo.opportunity_slates AS slate",),
            "usp_ReadAccountExportOpportunitySavedQualificationForOwner": (
                "dbo.opportunity_saved_results AS saved_result",
                "dbo.opportunity_slates AS slate",
            ),
            "usp_ReadAccountExportOpportunitySavedEvidenceForOwner": (
                "dbo.opportunity_saved_qualifications AS qualification",
                "dbo.opportunity_saved_results AS saved_result",
                "dbo.opportunity_slates AS slate",
            ),
        }
        for name, ancestors in chain.items():
            body = self.procedures[name]
            for ancestor in ancestors:
                with self.subTest(procedure=name, ancestor=ancestor):
                    self.assertIn(f"JOIN {ancestor}", body)

    # -- ORDER BY presence ----------------------------------------------------

    def test_every_reader_has_a_deterministic_order_by(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("ORDER BY", body)
                self.assertNotIn("SELECT *", body)
                self.assertNotIn("SELECT*", body)

    def test_descendant_readers_order_parent_then_own_sequence(self):
        # save_version_number/ordinal are only unique WITHIN one parent, so
        # a flat reader over every owner's rows must order by every
        # ancestor's own key first.
        cases = {
            "usp_ReadAccountExportOpportunitySavedResultForOwner": (
                "slate.created_at_utc", "slate.slate_key", "saved_result.save_version_number",
            ),
            "usp_ReadAccountExportOpportunitySavedQualificationForOwner": (
                "slate.created_at_utc", "slate.slate_key", "saved_result.save_version_number",
                "qualification.ordinal",
            ),
            "usp_ReadAccountExportOpportunitySavedEvidenceForOwner": (
                "slate.created_at_utc", "slate.slate_key", "saved_result.save_version_number",
                "qualification.ordinal", "evidence.ordinal",
            ),
        }
        for name, expected_order in cases.items():
            body = self.procedures[name]
            order_by = body[body.index("ORDER BY"):]
            with self.subTest(procedure=name):
                positions = [order_by.index(term) for term in expected_order]
                self.assertEqual(positions, sorted(positions), msg=order_by)

    # -- no soft-delete column exists on any claimed table ---------------

    def test_no_reader_references_a_soft_delete_column(self):
        # None of the four tables under test has a deleted_at_utc column of
        # any kind; usp_DeleteOpportunitySavedSlateForOwner is a
        # member-triggered hard delete of the whole slate.
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("deleted_at_utc", body)

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

    def test_domains_field_allowlist_matches_the_actual_sql_output_exactly_in_order(self):
        # domain_field_map() walks the entire shared DOMAINS dict; this
        # test owns and checks only this package's own four, asserting
        # they are present (a subset) and exactly match in order -- never
        # that nothing else (e.g. the sibling packages') has been added.
        expected_by_procedure = domain_field_map()
        self.assertTrue(set(READER_PROCEDURES).issubset(set(expected_by_procedure)))
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                actual = content_select_columns(self.procedures[name])
                expected = list(expected_by_procedure[name])
                self.assertEqual(actual, expected)

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
            "@SlateKey", "@SavedResultKey", "@Url", "@BlobUrl",
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
        # The ledger column is nvarchar(500); PS-SETTINGS-EXPORT-003's own
        # gate round failed on a 779-character description. This package's
        # own description is kept at or under 450 characters from the
        # start, matching the writer brief's explicit budget.
        match = re.search(
            r"N'PS-SETTINGS-EXPORT-006',\s*\n\s*N'([^']*(?:''[^']*)*)',",
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
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-006'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-OPPSLATE-001'", self.rollback)
        self.assertNotIn("migration_id = N'PS-OPPSLATE-002'", self.rollback)
        self.assertNotIn("migration_id = N'PS-OPPSLATE-003'", self.rollback)

    # -- registry -------------------------------------------------------------

    def test_registry_entry_shape_and_requires(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-006", entries)
        entry = entries["PS-SETTINGS-EXPORT-006"]
        # PS-AUTH-001 is required because the paired verification script
        # provisions its synthetic owners through usp_UpsertAppUserFromAuth
        # -- named from the start, matching every package since
        # PS-SETTINGS-EXPORT-003's own gate round had to add this after the
        # fact. PS-OPPSLATE-001/002/003 are the FULL direct chain, matching
        # the in-family precedent PS-OPPSLATE-003/004 themselves already
        # set (each names its own full ancestor chain in `requires`, never
        # relying on transitivity alone), even though this migration's own
        # tables (all four read here) are created solely by PS-OPPSLATE-003.
        self.assertEqual(
            entry["requires"],
            ["PS-AUTH-001", "PS-OPPSLATE-001", "PS-OPPSLATE-002", "PS-OPPSLATE-003"],
        )
        for prerequisite in entry["requires"]:
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(ids.index(prerequisite), ids.index("PS-SETTINGS-EXPORT-006"))
        self.assertEqual(
            entry["forward"], "SQL FIles/Migrations/PS-SETTINGS-EXPORT-006_oppslate_reader.sql"
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-006_oppslate_reader_rollback.sql",
        )
        self.assertTrue(entry["summary"])

    def test_registry_entry_pins_the_sealed_gate(self):
        """SEALED STATE (replaced in the same lockstep commit as the gate
        block and the report's Gate state section, per the placeholder's own
        instruction — registry + test + REPORT). Literal pins the SEAL;
        computed form pins the FILE; four objects; the exact verification
        string the gate run recorded."""
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        entry = entries["PS-SETTINGS-EXPORT-006"]
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual(
            gate["executable_sha256"],
            "3db5eff29654109f35e3c5a8ef1df0d442a316258d82b41fe1fff1868be2ed80",
        )
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(len(gate["objects"]), 4)
        self.assertTrue(all(
            o.startswith("SQL_STORED_PROCEDURE:dbo.usp_ReadAccountExportOpportunity")
            for o in gate["objects"]
        ))
        self.assertEqual(
            gate["verification"],
            "PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql returned verified = 1",
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

    def test_verify_structural_loop_checks_for_the_soft_delete_column_that_does_not_exist(self):
        self.assertIn("LIKE N'%deleted_at_utc%'", self.verify)

    def test_verify_fixture_populates_every_directive_excluded_column_with_a_real_value(self):
        # A genuine exclusion proof needs the excluded value to actually
        # exist in the fixture, not merely be absent because it was never
        # written. Every directive-category column must appear as a
        # fixture INSERT column list entry somewhere in the verify script.
        all_excluded = set()
        for columns in DIRECTIVE_CATEGORY_COLUMNS.items():
            all_excluded |= columns[1]
        for column in all_excluded:
            with self.subTest(column=column):
                self.assertIn(column, self.verify)

    def test_verify_never_references_knowledge_item_save_requests_or_other_sibling_machinery(self):
        # Sanity: this package's own fixture never accidentally reaches
        # into a sibling package's excluded machinery table.
        for name in ("knowledge_item_save_requests", "career_skill_links", "slate_entities"):
            with self.subTest(table=name):
                self.assertNotIn(name, self.verify)


class AdapterModuleTests(unittest.TestCase):
    """Offline tests for services/account_export_domain_readers.py using
    fake cursors/connections only -- no database, no network. Fixture
    identifiers are entropy-dead, case-consistent placeholders
    ("aaaaaaaa-..." style), never a copied well-known example GUID."""

    _SLATE_KEY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _RESULT_KEY = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

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
        readers_module.read_opportunity_slate,
        readers_module.read_opportunity_saved_result,
        readers_module.read_opportunity_saved_qualification,
        readers_module.read_opportunity_saved_evidence,
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

    def test_opportunity_slate_content_rows_use_the_sql_embedded_read_window_not_the_fallback(self):
        description = [
            ("slate_key",), ("visibility",), ("current_save_version_number",),
            ("created_at_utc",), ("updated_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (self._SLATE_KEY, "private", 2, "2020-01-01", "2020-01-02", "SQL-START", "SQL-END")
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_opportunity_slate(connection, "real-key")
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("read_started_at_utc", result["rows"][0])
        self.assertNotIn("read_ended_at_utc", result["rows"][0])
        self.assertEqual(result["rows"][0]["slate_key"], self._SLATE_KEY)
        self.assertEqual(result["read_started_at_utc"], "SQL-START")
        self.assertEqual(result["read_ended_at_utc"], "SQL-END")

    def test_opportunity_saved_result_content_row_decodes_parent_linkage_key(self):
        description = [
            ("slate_key",), ("saved_result_key",), ("save_version_number",),
            ("source_version_number",), ("requirement_version_number",),
            ("evidence_considered_count",), ("qualification_count",), ("input_fingerprint",),
            ("saved_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            self._SLATE_KEY, self._RESULT_KEY, 2, 2, 2,
            5, 3, "b" * 64, "2020-01-01", "SQL-START", "SQL-END",
        )
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_opportunity_saved_result(connection, "real-key")
        self.assertEqual(result["rows"][0]["slate_key"], self._SLATE_KEY)
        self.assertEqual(result["rows"][0]["saved_result_key"], self._RESULT_KEY)
        self.assertEqual(result["rows"][0]["save_version_number"], 2)

    def test_opportunity_saved_qualification_content_row_decodes_ordinal_and_class(self):
        description = [
            ("saved_result_key",), ("ordinal",), ("statement_class",), ("derived_status",),
            ("citation_count",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (self._RESULT_KEY, 1, "required_qualification", "supported", 2, "SQL-START", "SQL-END")
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_opportunity_saved_qualification(connection, "real-key")
        self.assertEqual(result["rows"][0]["saved_result_key"], self._RESULT_KEY)
        self.assertEqual(result["rows"][0]["statement_class"], "required_qualification")

    def test_opportunity_saved_evidence_content_row_decodes_full_linkage_chain(self):
        description = [
            ("saved_result_key",), ("saved_qualification_ordinal",), ("ordinal",), ("clause_ordinal",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (self._RESULT_KEY, 1, 2, 1, "SQL-START", "SQL-END")
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_opportunity_saved_evidence(connection, "real-key")
        self.assertEqual(result["rows"][0]["saved_result_key"], self._RESULT_KEY)
        self.assertEqual(result["rows"][0]["saved_qualification_ordinal"], 1)
        self.assertEqual(result["rows"][0]["ordinal"], 2)

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
    package's own domain ("opportunity_slate") -- never to "however many
    domains the shared dict currently totals," which would break the
    moment a future package legitimately adds another."""

    _THIS_PACKAGES_DOMAIN = "opportunity_slate"

    def test_opportunity_slate_is_included_with_exactly_four_readers_in_order(self):
        domain = DOMAINS[self._THIS_PACKAGES_DOMAIN]
        self.assertEqual(domain["disposition"], "included")
        self.assertIsNone(domain["reason"])
        self.assertEqual(
            [r["procedure"] for r in domain["readers"]],
            list(READER_PROCEDURES),
        )

    def test_my_opportunities_is_still_unavailable_with_a_factual_reason(self):
        # This package flips opportunity_slate to included but explicitly
        # leaves my_opportunities alone -- re-verified, not merely
        # untouched: PS-MYOPP-001 is confirmed shared-side-only with no
        # member-owned table.
        entry = DOMAINS["my_opportunities"]
        self.assertEqual(entry["disposition"], "unavailable")
        self.assertEqual(entry["readers"], ())
        self.assertIn("Opportunity Slate", entry["reason"])
        self.assertIn("PS-MYOPP-001", entry["reason"])

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
        forbidden_terms = ("user_key", "auth_subject", "row_version", "profile_key")
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
