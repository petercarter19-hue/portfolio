"""Contracts for PS-SETTINGS-EXPORT-003, the account-export core readers
(replacement package 1 of the 2026-08-29 reader topology, after
PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-READERS-001 failed independent
pre-activation review).

Modeled on tests/test_settings_account_export_migration.py: registry
completeness/digest assertions plus focused structural assertions for
the enforcement rules the lane claim and
docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
require that a static read of the SQL/Python text can express without a
live database. Also pins services/account_export_domain_readers.py's
DOMAINS registry against the actual SQL output column lists, and
exercises the adapter's row/read-window decoding with fake cursors.
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
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-003_core_readers.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-003_core_readers_rollback.sql"
VERIFY = VERIFICATION / "PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
ADAPTER_SOURCE_PATH = ROOT / "services" / "account_export_domain_readers.py"

READER_PROCEDURES = (
    "usp_ReadAccountExportAccountForOwner",
    "usp_ReadAccountExportProfileForOwner",
    "usp_ReadAccountExportCareerChapterForOwner",
    "usp_ReadAccountExportCareerExperienceForOwner",
    "usp_ReadAccountExportCareerEducationForOwner",
    "usp_ReadAccountExportCareerCredentialForOwner",
    "usp_ReadAccountExportCareerProjectForOwner",
    "usp_ReadAccountExportCareerAchievementForOwner",
    "usp_ReadAccountExportCareerSkillForOwner",
    "usp_ReadAccountExportCareerTimelineEventForOwner",
)

# Expected owner-scoping predicate substring per procedure (used both as
# a presence check and, for the non-account readers, to confirm the
# joined chapter's own predicate where applicable).
OWNER_PREDICATE = {
    "usp_ReadAccountExportAccountForOwner": "app_user.id = @UserId",
    "usp_ReadAccountExportProfileForOwner": "profile.profile_id = @ProfileId",
    "usp_ReadAccountExportCareerChapterForOwner": "chapter.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerExperienceForOwner": "experience.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerEducationForOwner": "education.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerCredentialForOwner": "credential.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerProjectForOwner": "project.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerAchievementForOwner": "achievement.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerSkillForOwner": "skill.owner_profile_id = @ProfileId",
    "usp_ReadAccountExportCareerTimelineEventForOwner": "timeline_event.owner_profile_id = @ProfileId",
}

# Readers that join dbo.career_chapters for parent chapter_key linkage
# and therefore must ALSO carry the joined chapter's soft-delete
# predicate (see the migration's own header for why this is a
# deliberate widening beyond "every table that has the column").
CHAPTER_JOINED_READERS = (
    "usp_ReadAccountExportCareerExperienceForOwner",
    "usp_ReadAccountExportCareerEducationForOwner",
    "usp_ReadAccountExportCareerCredentialForOwner",
    "usp_ReadAccountExportCareerProjectForOwner",
    "usp_ReadAccountExportCareerAchievementForOwner",
    "usp_ReadAccountExportCareerTimelineEventForOwner",
)

# Readers with their own deleted_at_utc column/predicate.
OWN_SOFT_DELETE_READERS = (
    "usp_ReadAccountExportCareerChapterForOwner",
    "usp_ReadAccountExportCareerAchievementForOwner",
    "usp_ReadAccountExportCareerSkillForOwner",
)

# Forbidden OUTPUT field names (unqualified, as they appear after
# aliasing/dot-stripping) per procedure. A full-name set, never a
# substring list -- the paused DOMAIN-READERS-001 package's own design
# notes record a naive substring scan false-positiving on legitimate
# columns (e.g. "credential" inside career_credentials' own
# credential_name/credential_issuer_name/credential_identifier).
FORBIDDEN_FIELDS = {
    "usp_ReadAccountExportAccountForOwner": {"id", "user_key", "auth_subject", "active"},
    "usp_ReadAccountExportProfileForOwner": {
        "profile_id", "profile_key", "user_id", "active", "row_version",
    },
    "usp_ReadAccountExportCareerChapterForOwner": {
        "chapter_id", "entity_id", "owner_profile_id", "created_by_user_id",
        "approved_by_user_id", "deleted_at_utc", "row_version",
    },
    "usp_ReadAccountExportCareerExperienceForOwner": {
        "chapter_id", "owner_profile_id", "entity_id", "row_version",
    },
    "usp_ReadAccountExportCareerEducationForOwner": {
        "chapter_id", "owner_profile_id", "entity_id", "row_version",
    },
    "usp_ReadAccountExportCareerCredentialForOwner": {
        "chapter_id", "owner_profile_id", "entity_id", "row_version",
    },
    "usp_ReadAccountExportCareerProjectForOwner": {
        "chapter_id", "owner_profile_id", "entity_id", "row_version",
    },
    "usp_ReadAccountExportCareerAchievementForOwner": {
        "achievement_id", "entity_id", "owner_profile_id", "chapter_id",
        "created_by_user_id", "approved_by_user_id", "deleted_at_utc", "row_version",
    },
    "usp_ReadAccountExportCareerSkillForOwner": {
        "skill_id", "entity_id", "owner_profile_id", "deleted_at_utc", "row_version",
    },
    "usp_ReadAccountExportCareerTimelineEventForOwner": {
        "timeline_event_id", "entity_id", "owner_profile_id", "chapter_id", "row_version",
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
    """Extract the OUTPUT field names of a core-reader's content SELECT,
    in order, matching exactly what a caller decoding the result set
    would see. Located precisely between the shared identity header's
    closing "IF @ProfileId IS NULL RETURN;" line and the procedure's own
    first subsequent FROM clause, so a WHERE/JOIN/ORDER BY reference to
    owner_profile_id/chapter_id/deleted_at_utc (all legitimate there)
    can never be mistaken for a selected column."""

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
    """procedure_name -> fields tuple, from DOMAINS (every domain, not
    only included ones, though only included domains carry readers)."""

    mapping = {}
    for domain in DOMAINS.values():
        for reader_entry in domain["readers"]:
            mapping[reader_entry["procedure"]] = reader_entry["fields"]
    return mapping


class SettingsExportCoreReadersMigrationTests(unittest.TestCase):
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
            ("forward", self.forward, 58000, 58099),
            ("rollback", self.rollback, 58000, 58099),
        ):
            with self.subTest(file=label):
                numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)), "THROW numbers must be unique in this file")
                self.assertTrue(all(low <= n <= high for n in numbers), numbers)

    def test_verify_throw_numbers_are_in_its_own_reserved_range(self):
        numbers = [int(n) for n in re.findall(r"THROW (\d+),", self.verify)]
        self.assertTrue(numbers)
        self.assertTrue(all(58100 <= n <= 58199 for n in numbers), numbers)

    def test_throw_ranges_are_fresh_against_every_sibling_sql_file(self):
        # "Fresh" means no sibling file anywhere under SQL FIles/ (other
        # than this package's own three) uses a number inside either of
        # this package's reserved ranges.
        own_files = {FORWARD, ROLLBACK, VERIFY}
        sql_root = ROOT / "SQL FIles"
        for path in sql_root.rglob("*.sql"):
            if path in own_files:
                continue
            source = read(path)
            numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
            colliding = [n for n in numbers if 58000 <= n <= 58199]
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
            if entry["id"] != "PS-SETTINGS-EXPORT-003"
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

    def test_forward_requires_exactly_plat_006_and_the_schema_it_needs(self):
        self.assertIn("migration_id = N'PS-PLAT-006'", self.forward)
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.forward)
        self.assertNotIn("migration_id = N'PS-SETTINGS-EXPORT-001'", self.forward)
        for fragment in (
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_chapters', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_experiences', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_education', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_credentials', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_projects', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_achievements', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_skills', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_timeline_events', N'U') IS NULL",
        ):
            self.assertIn(fragment, self.forward)
        # career_skill_links is deliberately never one of the ten created
        # procedures' source tables (the migration's own ledger
        # description and header comment both name it in prose while
        # explaining the deliberate exclusion, so a whole-body substring
        # check would false-positive on that; the real guarantee --
        # exactly ten procedures, none reading career_skill_links -- is
        # covered by test_forward_creates_exactly_the_claimed_procedures_and_nothing_else
        # and DomainsRegistryTests.test_career_skill_links_is_excluded_with_the_evidence_item_reason).
        for name in READER_PROCEDURES:
            self.assertNotIn("career_skill_links", self.procedures[name])

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

    # -- owner predicate presence -------------------------------------------

    def test_every_reader_filters_by_its_expected_owner_predicate(self):
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(OWNER_PREDICATE[name], self.procedures[name])

    # -- ORDER BY presence ----------------------------------------------------

    def test_every_reader_has_a_deterministic_order_by(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("ORDER BY", body)
                self.assertNotIn("SELECT *", body)
                self.assertNotIn("SELECT*", body)

    # -- soft-delete predicate presence ----------------------------------------

    def test_own_soft_delete_predicate_present_where_the_table_has_the_column(self):
        for name in OWN_SOFT_DELETE_READERS:
            body = self.procedures[name]
            alias = {
                "usp_ReadAccountExportCareerChapterForOwner": "chapter",
                "usp_ReadAccountExportCareerAchievementForOwner": "achievement",
                "usp_ReadAccountExportCareerSkillForOwner": "skill",
            }[name]
            with self.subTest(procedure=name):
                self.assertIn(f"{alias}.deleted_at_utc IS NULL", body)

    def test_joined_chapter_soft_delete_predicate_present_on_every_chapter_joined_reader(self):
        for name in CHAPTER_JOINED_READERS:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("chapter.deleted_at_utc IS NULL", body)
                self.assertIn("JOIN dbo.career_chapters AS chapter", body)
                # Defense in depth: the composite FK already guarantees
                # same-owner, but the join must still carry the parent's own
                # owner predicate so a schema relaxation cannot silently turn
                # the linkage into a leak (independent-review finding).
                self.assertIn("chapter.owner_profile_id = @ProfileId", body)

    def test_readers_without_a_deleted_at_utc_column_never_reference_one_of_their_own(self):
        # career_experiences/_education/_credentials/_projects/
        # _timeline_events have no deleted_at_utc column of their own;
        # only the joined chapter's is legitimate.
        no_own_column_readers = (
            "usp_ReadAccountExportCareerExperienceForOwner",
            "usp_ReadAccountExportCareerEducationForOwner",
            "usp_ReadAccountExportCareerCredentialForOwner",
            "usp_ReadAccountExportCareerProjectForOwner",
            "usp_ReadAccountExportCareerTimelineEventForOwner",
        )
        aliases = {
            "usp_ReadAccountExportCareerExperienceForOwner": "experience",
            "usp_ReadAccountExportCareerEducationForOwner": "education",
            "usp_ReadAccountExportCareerCredentialForOwner": "credential",
            "usp_ReadAccountExportCareerProjectForOwner": "project",
            "usp_ReadAccountExportCareerTimelineEventForOwner": "timeline_event",
        }
        for name in no_own_column_readers:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn(f"{aliases[name]}.deleted_at_utc", body)

    # -- read-window columns ----------------------------------------------------

    def test_every_reader_returns_the_read_window_as_trailing_columns(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("@ReadStartedAtUtc AS read_started_at_utc", body)
                self.assertIn("SYSUTCDATETIME() AS read_ended_at_utc", body)
                # Exactly one content SELECT plus the identity-resolution
                # SELECT -- never a second content-shaped result set.
                self.assertEqual(body.count("SELECT"), 2)

    # -- forbidden-field canary, exact allowlist pinning -------------------------

    def test_forbidden_fields_are_absent_from_every_readers_output(self):
        for name in READER_PROCEDURES:
            columns = set(content_select_columns(self.procedures[name]))
            with self.subTest(procedure=name):
                overlap = columns & FORBIDDEN_FIELDS[name]
                self.assertFalse(overlap, msg=f"{name} selects forbidden column(s) {overlap}")

    def test_domains_field_allowlist_matches_the_actual_sql_output_exactly_in_order(self):
        # domain_field_map() walks the entire (shared, module-global) DOMAINS
        # dict, not merely this package's own ten procedures -- a later
        # package (PS-SETTINGS-EXPORT-004 added "capture"/"moment") legitimately
        # extends the same dict with its own included readers. This test only
        # owns and checks this package's own ten; it asserts they are present
        # (a subset), never that nothing else has been added since.
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
            "@Url", "@BlobUrl",
        )
        for name in READER_PROCEDURES:
            sig = signature(self.procedures[name], name)
            for forbidden in forbidden_params:
                with self.subTest(procedure=name, param=forbidden):
                    self.assertNotIn(forbidden, sig)

    def test_no_grant_or_identity_creation_in_this_migration(self):
        # Scoped to the executable body (leading header comment stripped)
        # so this does not false-positive on the header's own prose
        # describing the grant model, which names these statements while
        # explaining their absence.
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

    # -- rollback -----------------------------------------------------------

    def test_rollback_drops_every_claimed_procedure_and_nothing_else(self):
        for name in READER_PROCEDURES:
            self.assertIn(f"DROP PROCEDURE dbo.{name}", self.rollback)
        self.assertNotIn("DROP TABLE", self.rollback)
        self.assertNotIn("DROP TRIGGER", self.rollback)

    def test_rollback_removes_only_this_migrations_ledger_row(self):
        self.assertIn(
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-003'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-PLAT-006'", self.rollback)

    # -- registry -------------------------------------------------------------

    def test_registry_entry_shape_sealed_gate_and_requires(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-003", entries)
        entry = entries["PS-SETTINGS-EXPORT-003"]
        # PS-PLAT-006 covers every schema the READERS guard for; PS-AUTH-001 is
        # required additionally because the paired verification script
        # provisions its synthetic owners through usp_UpsertAppUserFromAuth and
        # the governed gate replays `requires` before running verification.
        self.assertEqual(entry["requires"], ["PS-PLAT-006", "PS-AUTH-001"])
        self.assertLess(ids.index("PS-PLAT-006"), ids.index("PS-SETTINGS-EXPORT-003"))
        self.assertLess(ids.index("PS-AUTH-001"), ids.index("PS-SETTINGS-EXPORT-003"))
        self.assertEqual(
            entry["forward"], "SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers.sql"
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers_rollback.sql",
        )
        self.assertTrue(entry["summary"])
        # The manager's governed gate run sealed the proof; pin its identity so
        # neither the digest nor the verified isolation result can silently
        # drift from the file this suite also reads. (The digest hashes
        # normalized executable content, so comment-only edits keep it valid.)
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual(
            gate["executable_sha256"],
            "28678016f02b4a0abb072504e7f1fe6f3ed16f11ac7d1de3ad758fbc9f326b2e",
        )
        # The literal pins the seal; the computed form pins the FILE, so an
        # un-regated executable edit cannot slip past (house sibling idiom;
        # independent-review finding proved the literal alone misses it).
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(len(gate["objects"]), 10)
        self.assertTrue(
            all(o.startswith("SQL_STORED_PROCEDURE:dbo.usp_ReadAccountExport") for o in gate["objects"])
        )
        self.assertEqual(
            gate["verification"],
            "PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql returned verified = 1",
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
        # The deliberate rollback must precede the final report SELECT,
        # not merely exist somewhere (e.g. only inside the CATCH block).
        deliberate_rollback = self.verify.index("ROLLBACK TRANSACTION;\n\n    SELECT")
        self.assertGreater(deliberate_rollback, self.verify.index("INSERT dbo.slate_entities"))

    def test_verify_uses_bare_exec_for_every_reader(self):
        # "grep-tripwire that": every reader must be invoked at least
        # once via a genuinely bare EXEC (line starts with EXEC, not
        # preceded by INSERT), matching the migration's own claim that
        # every reader is safe to call that way because it carries no
        # ROLLBACK.
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
        """Raises if the adapter ever tries to manage the connection's
        lifetime or transaction state -- it must only ever call
        .cursor()."""

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

    # -- module holds no configuration/connection factory of its own -----

    def test_module_holds_no_configuration_or_connection_factory(self):
        source = ADAPTER_SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "ALLOWED_PROCEDURES", "get_connection", "import pyodbc",
            "DATABASE_", "CONNECTION_STRING",
        ):
            self.assertNotIn(forbidden, source)

    def test_every_domain_function_is_independently_callable(self):
        for domain_code, reader_entry in iter_included_readers():
            function = reader_entry["function"]
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(domain=domain_code, procedure=reader_entry["procedure"]):
                result = function(connection, "some-user-key")
                self.assertEqual(result["rows"], [])
                self.assertEqual(result["read_started_at_utc"], "S")
                self.assertEqual(result["read_ended_at_utc"], "E")

    def test_unresolved_identity_returns_empty_rows_not_an_error(self):
        plan = [("clock", "S"), ("none",), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_account(connection, "forged-key")
        self.assertEqual(result, {"rows": [], "read_started_at_utc": "S", "read_ended_at_utc": "E"})

    def test_content_rows_use_the_sql_embedded_read_window_not_the_fallback(self):
        description = [
            ("display_name",), ("email",), ("auth_provider",), ("profile_image_url",),
            ("timezone_name",), ("user_role",), ("created_at_utc",), ("last_seen_at_utc",),
            ("updated_at_utc",), ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            "Alice", "alice@example.com", "google", "https://example.invalid/a.png",
            "America/Chicago", "user", "2020-01-01", None, "2020-01-02",
            "SQL-START", "SQL-END",
        )
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_account(connection, "real-key")
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("read_started_at_utc", result["rows"][0])
        self.assertNotIn("read_ended_at_utc", result["rows"][0])
        self.assertEqual(result["rows"][0]["display_name"], "Alice")
        self.assertEqual(result["read_started_at_utc"], "SQL-START")
        self.assertEqual(result["read_ended_at_utc"], "SQL-END")

    def test_adapter_never_manages_connection_lifetime(self):
        plan = [("clock", "S"), ("none",), ("clock", "E")]
        connection = self._FakeConnection(plan)
        readers_module.read_career_skill(connection, "some-user-key")
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

        for domain_code, reader_entry in iter_included_readers():
            captured = {}
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = CapturingConnection(plan, captured)
            function = reader_entry["function"]
            with self.subTest(domain=domain_code, procedure=reader_entry["procedure"]):
                function(connection, "a-real-looking-user-key")
                self.assertIn(
                    f"EXEC dbo.{reader_entry['procedure']} @UserKey = ?;", captured["sql"]
                )
                self.assertEqual(captured["params"], ("a-real-looking-user-key",))
                self.assertNotIn("a-real-looking-user-key", captured["sql"])


class DomainsRegistryTests(unittest.TestCase):
    """Offline shape tests for the DOMAINS registry itself."""

    def test_exactly_three_domains_are_included_with_ten_total_readers(self):
        # Scoped to this package's own three named domains, not "whatever the
        # whole DOMAINS dict's included set happens to be" -- a later package
        # (PS-SETTINGS-EXPORT-004) legitimately adds its own included domains
        # ("capture", "moment") to the same shared dict. Restricting the
        # dict comprehension to this package's three names preserves the
        # original guarantee (exactly ten readers across exactly these three
        # domains, matching exactly this package's ten procedures) without
        # being disturbed by growth elsewhere.
        this_packages_domains = {"account", "profile", "living_resume"}
        included = {code: d for code, d in DOMAINS.items() if code in this_packages_domains}
        self.assertEqual(set(included), this_packages_domains)
        for code, domain in included.items():
            with self.subTest(domain=code):
                self.assertEqual(domain["disposition"], "included")
        total_readers = sum(len(d["readers"]) for d in included.values())
        self.assertEqual(total_readers, 10)
        procedures = {r["procedure"] for d in included.values() for r in d["readers"]}
        self.assertEqual(procedures, set(READER_PROCEDURES))

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

    def test_career_skill_links_is_excluded_with_the_evidence_item_reason(self):
        self.assertIn("career_skill_links", DOMAINS)
        entry = DOMAINS["career_skill_links"]
        self.assertEqual(entry["disposition"], "excluded")
        self.assertIn("evidence_item_id", entry["reason"])
        self.assertEqual(entry["readers"], ())

    def test_no_domain_reason_leaks_a_forbidden_field_name(self):
        # Reasons are safe architecture-level prose; none should ever
        # need to mention a forbidden internal identifier by name.
        forbidden_terms = ("user_key", "auth_subject", "row_version", "profile_key")
        for code, domain in DOMAINS.items():
            reason = domain["reason"] or ""
            for term in forbidden_terms:
                with self.subTest(domain=code, term=term):
                    self.assertNotIn(term, reason)

    def test_reader_entries_have_unique_procedures_and_schema_ids(self):
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
