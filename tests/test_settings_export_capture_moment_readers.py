"""Contracts for PS-SETTINGS-EXPORT-004, the account-export Capture/Moment
readers (replacement package 2 of the 2026-08-29 reader topology).

Modeled directly on tests/test_settings_export_core_readers.py (replacement
package 1, main cc5174da, independently reviewed and merged): registry
completeness/digest assertions plus focused structural assertions for the
enforcement rules the lane claim and
docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
require that a static read of the SQL/Python text can express without a live
database. Also pins services/account_export_domain_readers.py's DOMAINS
registry against the actual SQL output column lists, and exercises the
adapter's row/read-window decoding with fake cursors.

Every DOMAINS-scoped assertion below is scoped to THIS package's own two
domains ("capture", "moment"), never to "whatever the whole DOMAINS dict
currently contains" -- the same lesson package 1's own test file needed
applied retroactively when this package extended the same shared dict (see
this package's edits to test_settings_export_core_readers.py, noted in
CR2_OWNER_TECHNICAL_COMPLETION_REPORT.md), applied here from the start so a
future package 3 does not have to repeat the correction a second time.
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
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-004_capture_moment_readers.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-004_capture_moment_readers_rollback.sql"
VERIFY = VERIFICATION / "PS-SETTINGS-EXPORT-004_capture_moment_reader_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
ADAPTER_SOURCE_PATH = ROOT / "services" / "account_export_domain_readers.py"

READER_PROCEDURES = (
    "usp_ReadAccountExportCaptureForOwner",
    "usp_ReadAccountExportCaptureRevisionForOwner",
    "usp_ReadAccountExportMomentForOwner",
    "usp_ReadAccountExportMomentVersionForOwner",
    "usp_ReadAccountExportMomentSourceForOwner",
    "usp_ReadAccountExportMomentPlacementForOwner",
)

# Expected primary owner-scoping predicate substring per procedure (used
# both as a presence check and, for the parent-joined readers, to confirm
# the joined parent's own predicate where applicable).
OWNER_PREDICATE = {
    "usp_ReadAccountExportCaptureForOwner": "capture.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCaptureRevisionForOwner": "capture.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportMomentForOwner": "moment.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportMomentVersionForOwner": "moment.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportMomentSourceForOwner": "moment_source.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportMomentPlacementForOwner": "placement.owner_profile_id = @ProfileId",
}

# Readers whose own table carries owner_profile_id AND whose join to
# dbo.moments must therefore also assert the PARENT's owner_profile_id
# against @ProfileId independently -- the "owner predicate on both sides"
# defense in depth PS-SETTINGS-EXPORT-003's own independent review added
# (its correction round, finding 3), applied here from the start.
BOTH_SIDED_OWNER_READERS = (
    "usp_ReadAccountExportMomentSourceForOwner",
    "usp_ReadAccountExportMomentPlacementForOwner",
)
BOTH_SIDED_PARENT_PREDICATE = "moment.owner_profile_id = @ProfileId"

# Readers whose own table carries NO owner_profile_id column at all --
# ownership is asserted exactly once, through the joined parent, because
# that parent predicate is the only column that exists to check.
PARENT_ONLY_OWNER_READERS = (
    "usp_ReadAccountExportCaptureRevisionForOwner",
    "usp_ReadAccountExportMomentVersionForOwner",
)

# The one reader with its own deleted_at_utc column and predicate.
OWN_SOFT_DELETE_READERS = ("usp_ReadAccountExportCaptureForOwner",)

# The one reader that joins dbo.captures for parent capture_key linkage and
# must therefore also carry the joined capture's own soft-delete predicate.
CAPTURE_JOINED_READERS = ("usp_ReadAccountExportCaptureRevisionForOwner",)

# Readers whose own table has no deleted_at_utc column at all (discarding a
# Moment proposal is a real DELETE, not a soft-delete flag; moment_sources'
# own source_deleted_at_utc is a different fact -- see FORBIDDEN_FIELDS and
# the migration's own header).
NO_DELETED_AT_UTC_READERS = (
    "usp_ReadAccountExportMomentForOwner",
    "usp_ReadAccountExportMomentVersionForOwner",
    "usp_ReadAccountExportMomentPlacementForOwner",
)

# Forbidden OUTPUT field names (unqualified, as they appear after
# aliasing/dot-stripping) per procedure. A full-name set, never a substring
# list -- PS-SETTINGS-EXPORT-003's own paused-predecessor design notes
# record a naive substring scan false-positiving on legitimate columns.
FORBIDDEN_FIELDS = {
    "usp_ReadAccountExportCaptureForOwner": {
        "capture_id", "owner_profile_id", "active", "deleted_at_utc", "row_version",
    },
    "usp_ReadAccountExportCaptureRevisionForOwner": {
        "revision_id", "capture_id", "corrected_by_user_id", "row_version",
        "owner_profile_id", "active",
    },
    "usp_ReadAccountExportMomentForOwner": {
        "moment_id", "owner_profile_id", "confirmed_by_user_id", "row_version",
    },
    "usp_ReadAccountExportMomentVersionForOwner": {
        "moment_version_id", "moment_id", "saved_by_user_id", "row_version",
        "owner_profile_id",
    },
    "usp_ReadAccountExportMomentSourceForOwner": {
        "moment_source_id", "moment_id", "owner_profile_id", "capture_id",
        "capture_revision_id", "row_version",
    },
    "usp_ReadAccountExportMomentPlacementForOwner": {
        "placement_id", "owner_profile_id", "moment_id", "target_entity_id",
        "created_by_user_id", "reactivated_by_user_id", "removed_by_user_id",
        "row_version",
    },
}

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
    order, matching exactly what a caller decoding the result set would
    see. Located precisely between the shared identity header's closing
    "IF @ProfileId IS NULL RETURN;" line and the procedure's own first
    subsequent FROM clause, so a WHERE/JOIN/ORDER BY reference to
    owner_profile_id/capture_id/moment_id/deleted_at_utc (all legitimate
    there) can never be mistaken for a selected column."""

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


class SettingsExportCaptureMomentReadersMigrationTests(unittest.TestCase):
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
            ("forward", self.forward, 58200, 58299),
            ("rollback", self.rollback, 58200, 58299),
        ):
            with self.subTest(file=label):
                numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)), "THROW numbers must be unique in this file")
                self.assertTrue(all(low <= n <= high for n in numbers), numbers)

    def test_verify_throw_numbers_are_in_its_own_reserved_range(self):
        numbers = [int(n) for n in re.findall(r"THROW (\d+),", self.verify)]
        self.assertTrue(numbers)
        self.assertTrue(all(58300 <= n <= 58399 for n in numbers), numbers)

    def test_throw_ranges_are_fresh_against_every_sibling_sql_file(self):
        own_files = {FORWARD, ROLLBACK, VERIFY}
        sql_root = ROOT / "SQL FIles"
        for path in sql_root.rglob("*.sql"):
            if path in own_files:
                continue
            source = read(path)
            numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
            colliding = [n for n in numbers if 58200 <= n <= 58399]
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
            if entry["id"] != "PS-SETTINGS-EXPORT-004"
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

    def test_forward_requires_exactly_the_capture_moment_chain(self):
        for fragment in (
            "migration_id = N'PS-CAPTURE-001'",
            "migration_id = N'PS-CAPTURE-002'",
            "migration_id = N'PS-MOMENT-001'",
            "migration_id = N'PS-PLACEMENT-001'",
        ):
            self.assertIn(fragment, self.forward)
        # PS-AUTH-001 is a registry-level requirement only (the paired
        # verification script's usp_UpsertAppUserFromAuth dependency); the
        # migration body itself never checks for it -- app_users/
        # member_profiles' identity-resolution columns predate PS-AUTH-001,
        # exactly PS-SETTINGS-EXPORT-003's own recorded reasoning for the
        # identical omission.
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.forward)
        self.assertNotIn("migration_id = N'PS-SETTINGS-EXPORT-001'", self.forward)
        self.assertNotIn("migration_id = N'PS-SETTINGS-EXPORT-003'", self.forward)
        # PS-PLAT-002/PS-PLAT-005 create dbo.slate_entities, which this
        # migration never reads (see the target_entity_id exclusion). The
        # header and several per-reader prose comments both name
        # "slate_entities" while explaining that exclusion, so a whole-body
        # substring check here would false-positive on that prose exactly
        # the class of mistake PS-SETTINGS-EXPORT-003's own design notes
        # record catching for a different substring
        # ("career_skill_links") -- the real invariant (no READER BODY
        # references it) is checked precisely, per procedure, by
        # test_no_reader_references_slate_entities_or_target_entity_id
        # below.
        self.assertNotIn("migration_id = N'PS-PLAT-002'", self.forward)
        self.assertNotIn("migration_id = N'PS-PLAT-005'", self.forward)
        for fragment in (
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.captures', N'U') IS NULL",
            "OBJECT_ID(N'dbo.capture_revisions', N'U') IS NULL",
            "OBJECT_ID(N'dbo.moments', N'U') IS NULL",
            "OBJECT_ID(N'dbo.moment_versions', N'U') IS NULL",
            "OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL",
            "OBJECT_ID(N'dbo.moment_placements', N'U') IS NULL",
        ):
            self.assertIn(fragment, self.forward)

    def test_no_reader_references_slate_entities_or_target_entity_id(self):
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertNotIn("slate_entities", self.procedures[name])
                self.assertNotIn("target_entity_id", self.procedures[name])
                self.assertNotIn("TargetEntityKey", self.procedures[name])

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

    # -- owner predicate presence, including "both sides" ------------------

    def test_every_reader_filters_by_its_expected_owner_predicate(self):
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(OWNER_PREDICATE[name], self.procedures[name])

    def test_both_sided_owner_predicate_present_where_the_table_carries_its_own_owner_profile_id(self):
        # moment_sources and moment_placements each carry their own
        # owner_profile_id column, so the join to dbo.moments must ALSO
        # independently assert the parent's owner_profile_id against
        # @ProfileId -- defense in depth beyond the foreign key that
        # already ties them to the same owner (the pattern
        # PS-SETTINGS-EXPORT-003's own independent review added).
        for name in BOTH_SIDED_OWNER_READERS:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn(OWNER_PREDICATE[name], body)
                self.assertIn(BOTH_SIDED_PARENT_PREDICATE, body)
                self.assertIn("JOIN dbo.moments AS moment", body)

    def test_parent_only_owner_predicate_where_the_table_has_no_owner_profile_id_of_its_own(self):
        # dbo.capture_revisions and dbo.moment_versions carry no
        # owner_profile_id column at all; ownership can only be asserted
        # once, through the joined parent. Confirmed two ways: the parent
        # predicate is present, and the child's own alias never carries an
        # owner_profile_id reference (which would be a schema error if it
        # somehow did -- FORBIDDEN_FIELDS covers the output-column half of
        # this; here we additionally confirm no such predicate exists to
        # find in the WHERE/JOIN text either).
        aliases = {
            "usp_ReadAccountExportCaptureRevisionForOwner": "revision",
            "usp_ReadAccountExportMomentVersionForOwner": "moment_version",
        }
        for name in PARENT_ONLY_OWNER_READERS:
            body = self.procedures[name]
            alias = aliases[name]
            with self.subTest(procedure=name):
                self.assertIn(OWNER_PREDICATE[name], body)
                self.assertNotIn(f"{alias}.owner_profile_id", body)

    # -- ORDER BY presence ----------------------------------------------------

    def test_every_reader_has_a_deterministic_order_by(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("ORDER BY", body)
                self.assertNotIn("SELECT *", body)
                self.assertNotIn("SELECT*", body)

    # -- soft-delete predicate presence/absence ----------------------------------

    def test_own_soft_delete_predicate_present_where_the_table_has_the_column(self):
        for name in OWN_SOFT_DELETE_READERS:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("capture.deleted_at_utc IS NULL", body)

    def test_joined_capture_soft_delete_predicate_present_on_capture_revision_reader(self):
        for name in CAPTURE_JOINED_READERS:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("capture.deleted_at_utc IS NULL", body)
                self.assertIn("JOIN dbo.captures AS capture", body)
                self.assertIn("capture.owner_profile_id = @ProfileId", body)

    def test_readers_without_a_deleted_at_utc_column_never_reference_one(self):
        # dbo.moments/moment_versions/moment_placements have no
        # deleted_at_utc column at all -- discarding a Moment proposal is a
        # real DELETE, not a soft-delete flag. moment_sources is checked
        # separately below: it DOES have a deleted_at_utc-named column
        # (source_deleted_at_utc), but that describes the linked capture's
        # fate, never this row's own presence.
        aliases = {
            "usp_ReadAccountExportMomentForOwner": "moment",
            "usp_ReadAccountExportMomentVersionForOwner": "moment_version",
            "usp_ReadAccountExportMomentPlacementForOwner": "placement",
        }
        for name in NO_DELETED_AT_UTC_READERS:
            body = self.procedures[name]
            alias = aliases[name]
            with self.subTest(procedure=name):
                self.assertNotIn(f"{alias}.deleted_at_utc", body)

    def test_moment_source_never_uses_its_own_deleted_at_utc_style_column_as_a_presence_predicate(self):
        body = self.procedures["usp_ReadAccountExportMomentSourceForOwner"]
        # source_deleted_at_utc/source_state are content (selected), never
        # a WHERE-clause presence gate -- the row is 1:1 with its Moment
        # and is never itself soft-deleted.
        self.assertNotIn("source_deleted_at_utc IS NULL", body)
        self.assertNotIn("source_state = N'available'", body)
        self.assertNotIn("source_state <> N'deleted'", body)

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

    def test_domains_field_allowlist_matches_the_actual_sql_output_exactly_in_order(self):
        # domain_field_map() walks the entire shared DOMAINS dict; this
        # test owns and checks only this package's own six, asserting they
        # are present (a subset) and exactly match in order -- never that
        # nothing else (e.g. PS-SETTINGS-EXPORT-003's ten) has been added.
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
            "@CaptureKey", "@MomentKey", "@TargetEntityId", "@TargetEntityKey",
            "@Url", "@BlobUrl",
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
            r"N'PS-SETTINGS-EXPORT-004',\s*\n\s*N'([^']*(?:''[^']*)*)',",
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
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-004'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-CAPTURE-001'", self.rollback)
        self.assertNotIn("migration_id = N'PS-MOMENT-001'", self.rollback)

    # -- registry -------------------------------------------------------------

    def test_registry_entry_shape_and_requires(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-004", entries)
        entry = entries["PS-SETTINGS-EXPORT-004"]
        # PS-AUTH-001 is required because the paired verification script
        # provisions its synthetic owners through usp_UpsertAppUserFromAuth
        # -- named from the start (PS-SETTINGS-EXPORT-003's own gate round
        # had to add this after the fact; this package does not repeat
        # that omission). PS-CAPTURE-001/002, PS-MOMENT-001, and
        # PS-PLACEMENT-001 are the migrations that create this package's
        # six tables.
        self.assertEqual(
            entry["requires"],
            ["PS-AUTH-001", "PS-CAPTURE-001", "PS-CAPTURE-002", "PS-MOMENT-001", "PS-PLACEMENT-001"],
        )
        for prerequisite in entry["requires"]:
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(ids.index(prerequisite), ids.index("PS-SETTINGS-EXPORT-004"))
        self.assertEqual(
            entry["forward"], "SQL FIles/Migrations/PS-SETTINGS-EXPORT-004_capture_moment_readers.sql"
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-004_capture_moment_readers_rollback.sql",
        )
        self.assertTrue(entry["summary"])

    def test_registry_entry_pins_the_sealed_gate(self):
        """SEALED STATE (replaced in the same commit as the gate block, per
        the pre-gate placeholder's own five-step instruction). The literal
        pins the SEAL; the computed form pins the FILE; six objects, not
        package 1's ten; and the exact verification string the gate run
        recorded."""
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        entry = entries["PS-SETTINGS-EXPORT-004"]
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual(
            gate["executable_sha256"],
            "679af4674478db72933ffea49311d000d95b1a9113791cb461dc9671dfb721c3",
        )
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(len(gate["objects"]), 6)
        self.assertTrue(all(
            o.startswith("SQL_STORED_PROCEDURE:dbo.usp_ReadAccountExport")
            for o in gate["objects"]
        ))
        self.assertEqual(
            gate["verification"],
            "PS-SETTINGS-EXPORT-004_capture_moment_reader_isolation_verify.sql returned verified = 1",
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
        self.assertGreater(deliberate_rollback, self.verify.index("INSERT dbo.slate_entities"))

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

    def test_verify_never_writes_to_slate_entities_beyond_the_minimal_placement_fixture(self):
        # slate_entities rows exist only to satisfy moment_placements'
        # foreign key; the verify script must never select target_entity_id
        # back out of any reader.
        self.assertNotIn("target_entity_key", self.verify.lower())
        self.assertIn("INSERT dbo.slate_entities (owner_profile_id, entity_type)", self.verify)


class AdapterModuleTests(unittest.TestCase):
    """Offline tests for services/account_export_domain_readers.py using
    fake cursors/connections only -- no database, no network. Fixture
    identifiers are entropy-dead, case-consistent placeholders
    ("aaaaaaaa-..." style), never a copied well-known example GUID."""

    _CAPTURE_KEY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _REVISION_KEY = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    _MOMENT_KEY = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    _MOMENT_VERSION_KEY = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    _MOMENT_SOURCE_KEY = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    _PLACEMENT_KEY = "ffffffff-ffff-ffff-ffff-ffffffffffff"

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
        readers_module.read_capture,
        readers_module.read_capture_revision,
        readers_module.read_moment,
        readers_module.read_moment_version,
        readers_module.read_moment_source,
        readers_module.read_moment_placement,
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

    def test_capture_content_rows_use_the_sql_embedded_read_window_not_the_fallback(self):
        description = [
            ("capture_key",), ("capture_type",), ("body",), ("visibility",), ("status",),
            ("created_at_utc",), ("updated_at_utc",), ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            self._CAPTURE_KEY, "text", "PSX4 capture body", "private", "captured",
            "2020-01-01", "2020-01-02", "SQL-START", "SQL-END",
        )
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_capture(connection, "real-key")
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("read_started_at_utc", result["rows"][0])
        self.assertNotIn("read_ended_at_utc", result["rows"][0])
        self.assertEqual(result["rows"][0]["capture_key"], self._CAPTURE_KEY)
        self.assertEqual(result["read_started_at_utc"], "SQL-START")
        self.assertEqual(result["read_ended_at_utc"], "SQL-END")

    def test_moment_source_content_row_decodes_parent_and_capture_linkage_keys(self):
        description = [
            ("moment_source_key",), ("moment_key",), ("source_capture_key",),
            ("source_revision_key",), ("source_revision_number",), ("source_state",),
            ("source_deleted_at_utc",), ("created_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            self._MOMENT_SOURCE_KEY, self._MOMENT_KEY, self._CAPTURE_KEY,
            self._REVISION_KEY, 1, "available",
            None, "2020-01-01",
            "SQL-START", "SQL-END",
        )
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_moment_source(connection, "real-key")
        self.assertEqual(result["rows"][0]["moment_key"], self._MOMENT_KEY)
        self.assertEqual(result["rows"][0]["source_capture_key"], self._CAPTURE_KEY)
        self.assertEqual(result["rows"][0]["source_revision_key"], self._REVISION_KEY)
        self.assertIsNone(result["rows"][0]["source_deleted_at_utc"])

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

    def test_every_included_reader_across_both_packages_is_still_callable(self):
        # Cheap regression net: this package's edits to the shared DOMAINS
        # dict must not disturb PS-SETTINGS-EXPORT-003's own ten readers.
        for domain_code, reader_entry in iter_included_readers():
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(domain=domain_code, procedure=reader_entry["procedure"]):
                result = reader_entry["function"](connection, "some-user-key")
                self.assertEqual(result["rows"], [])


class DomainsRegistryTests(unittest.TestCase):
    """Offline shape tests for the DOMAINS registry itself, scoped to this
    package's own two domains ("capture", "moment") -- never to "however
    many domains the shared dict currently totals," which would break the
    moment a future package legitimately adds a third."""

    _THIS_PACKAGES_DOMAINS = {"capture", "moment"}

    def test_exactly_two_new_domains_are_included_with_six_total_readers(self):
        included = {code: d for code, d in DOMAINS.items() if code in self._THIS_PACKAGES_DOMAINS}
        self.assertEqual(set(included), self._THIS_PACKAGES_DOMAINS)
        for code, domain in included.items():
            with self.subTest(domain=code):
                self.assertEqual(domain["disposition"], "included")
                self.assertIsNone(domain["reason"])
        total_readers = sum(len(d["readers"]) for d in included.values())
        self.assertEqual(total_readers, 6)
        procedures = {r["procedure"] for d in included.values() for r in d["readers"]}
        self.assertEqual(procedures, set(READER_PROCEDURES))

    def test_capture_domain_has_two_readers_in_source_order(self):
        readers = DOMAINS["capture"]["readers"]
        self.assertEqual(
            [r["procedure"] for r in readers],
            ["usp_ReadAccountExportCaptureForOwner", "usp_ReadAccountExportCaptureRevisionForOwner"],
        )

    def test_moment_domain_has_four_readers_in_source_order(self):
        readers = DOMAINS["moment"]["readers"]
        self.assertEqual(
            [r["procedure"] for r in readers],
            [
                "usp_ReadAccountExportMomentForOwner",
                "usp_ReadAccountExportMomentVersionForOwner",
                "usp_ReadAccountExportMomentSourceForOwner",
                "usp_ReadAccountExportMomentPlacementForOwner",
            ],
        )

    def test_voice_photo_is_excluded_with_a_stable_corrected_reason(self):
        # Corrected by this package from "unavailable" to "excluded": the
        # prior reason claimed the underlying schema was not applied, which
        # docs/governance/PRODUCTION_SCHEMA_STATE.md contradicts (PS-VOICE-001/
        # PS-CAPTURE-MEDIA-001 are both applied, exactly like this
        # package's own dbo.captures/dbo.moments).
        entry = DOMAINS["voice_photo"]
        self.assertEqual(entry["disposition"], "excluded")
        self.assertEqual(entry["readers"], ())
        self.assertIsInstance(entry["reason"], str)
        self.assertTrue(entry["reason"].strip())
        self.assertNotIn("not gated/applied", entry["reason"])

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
