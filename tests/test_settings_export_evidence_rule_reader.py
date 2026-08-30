"""Contracts for PS-SETTINGS-EXPORT-009, the account-export
evidence-rule reader (dbo.career_skill_links).

Modeled directly on tests/test_settings_export_preferences_consent_reader.py
(PS-SETTINGS-EXPORT-008, gate sealed): registry completeness/gate-null
assertions plus focused structural assertions for the enforcement rules
the writer brief and
docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
require that a static read of the SQL/Python text can express without a
live database. Also pins services/account_export_domain_readers.py's
DOMAINS registry against the actual SQL output column list, exercises
the adapter's row/read-window decoding with fake cursors, and pins the
four ruling-record reason strings this package updated as durable owner
decisions (so a future package changing one of them fails a test, not
merely a documentation drift).

THE CENTRAL FINDINGS THIS TEST FILE PINS:
  1. This is the first ONE-reader package in this program (every prior
     package built two or more procedures in its own migration); its
     structural checks are written directly against the one procedure
     rather than through the generic reader-name-loop machinery every
     multi-reader sibling file uses.
  2. The reader's join count is 2 (the identity header's own join to
     dbo.app_users plus this reader's own join to dbo.career_skills for
     skill_key resolution) -- the first content-level join a
     "flip a domain from excluded to included" package in this program
     has needed.
  3. Two references are excluded outright and never resolved, never
     joined: source_entity_id (a dbo.slate_entities reference -- the
     same boundary this program has drawn for every entity_id reference
     since PS-SETTINGS-EXPORT-003's own header) and evidence_item_id (a
     dbo.evidence_items reference -- dbo.evidence_items is not one of
     this package's claimed tables, so resolving it to anything, even an
     opaque key, is out of scope). A derived evidence_linked bit is
     disclosed instead, computed entirely from career_skill_links' own
     nullable column -- no join, no evidence_items content.
  4. dbo.career_skill_links has no deleted_at_utc or row_version of its
     own; the joined dbo.career_skills row does, and the reader filters
     skill.deleted_at_utc IS NULL so a soft-deleted skill's link cannot
     surface through this back door -- proven in the verification
     script by actually soft-deleting a skill mid-script and re-invoking
     the reader, not merely asserted from the DDL.
  5. Four durable owner rulings, alongside the safe-references-only
     evidence rule itself, are recorded as updated DOMAINS reason
     strings this file also pins: ai_proposals, both publication-adjacent
     domains (profile_publication_foundation, own_publication_versions),
     community_authored_content, and file_evidence_metadata.
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
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-009_evidence_rule_reader.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-009_evidence_rule_reader_rollback.sql"
VERIFY = VERIFICATION / "PS-SETTINGS-EXPORT-009_evidence_rule_reader_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
ADAPTER_SOURCE_PATH = ROOT / "services" / "account_export_domain_readers.py"

READER_PROCEDURES = ("usp_ReadAccountExportCareerSkillLinkForOwner",)

# dbo.career_skill_links carries its own owner_profile_id directly; the
# joined dbo.career_skills row is independently owner-predicated too
# (defense in depth beyond the composite FK that already ties them to
# the same owner) -- both predicates are required, not merely one.
OWNER_PREDICATES = {
    "usp_ReadAccountExportCareerSkillLinkForOwner": (
        "link.owner_profile_id = @ProfileId",
        "skill.owner_profile_id = @ProfileId",
    ),
}

# The identity header's own join to dbo.app_users, plus this reader's
# own join to dbo.career_skills for skill_key resolution -- the first
# content-level join a "flip a domain to included" package in this
# program has needed.
EXPECTED_JOIN_COUNT = {
    "usp_ReadAccountExportCareerSkillLinkForOwner": 2,
}

# Forbidden OUTPUT field names (unqualified, as they appear after
# aliasing/dot-stripping). A full-name set, never a substring list --
# PS-SETTINGS-EXPORT-003's own paused-predecessor design notes record a
# naive substring scan false-positiving on legitimate columns.
FORBIDDEN_FIELDS = {
    "usp_ReadAccountExportCareerSkillLinkForOwner": {
        "skill_link_id", "owner_profile_id", "skill_id", "source_entity_id",
        "evidence_item_id", "created_by_user_id",
    },
}

# The one column this package's own safe-references-only evidence rule
# forbids resolving: evidence_item_id is a dbo.evidence_items reference,
# and dbo.evidence_items is not a claimed table of this package, so even
# an opaque-key resolution is out of scope. Named separately from the
# other forbidden fields (which are plain internal ids, the same
# "standard" exclusion category every prior package uses) because this
# one column is the actual subject of the owner's 2026-08-30 ruling this
# package adopts, the same "directive category, named for the rule that
# forbids it" treatment PS-SETTINGS-EXPORT-008 gave evidence_json under
# UNCONSTRAINED_EVIDENCE. source_entity_id is NOT in this category: its
# exclusion is the older, separate, program-wide "never resolve an
# entity_id reference" convention (PS-SETTINGS-EXPORT-003's own header),
# predating and independent of this package's own evidence rule --  it
# is a plain FORBIDDEN_FIELDS member instead, the identical treatment
# PS-SETTINGS-EXPORT-004 gave target_entity_id.
SAFE_REFERENCES_RULE = {
    "evidence_reference": {"evidence_item_id"},
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
    MIGRATIONS / "PS-SETTINGS-EXPORT-008_preferences_consent_reader.sql",
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
    """Extract the OUTPUT field names of the reader's content SELECT, in
    order. Located precisely between the shared identity header's
    closing "IF @ProfileId IS NULL RETURN;" line and the procedure's own
    first subsequent FROM clause -- identical anchor to every prior
    package's own helper. The multi-line CAST(CASE WHEN ... END AS bit)
    AS evidence_linked expression contains no top-level comma, so it
    survives the plain comma-split as one segment, and rsplit(" AS ", 1)
    correctly takes its LAST " AS " (the outer alias), not the inner
    "END AS bit" cast target."""

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


class SettingsExportEvidenceRuleReaderMigrationTests(unittest.TestCase):
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
            ("forward", self.forward, 59200, 59299),
            ("rollback", self.rollback, 59200, 59299),
        ):
            with self.subTest(file=label):
                numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)), "THROW numbers must be unique in this file")
                self.assertTrue(all(low <= n <= high for n in numbers), numbers)

    def test_verify_throw_numbers_are_in_its_own_reserved_range(self):
        # Several sections deliberately reuse a number across several
        # THROW statements sharing one meaning (e.g. every "contains one
        # of the other owner's rows" cross-contamination check) --
        # uniqueness is not asserted here, matching every prior
        # package's own verify-file test.
        numbers = [int(n) for n in re.findall(r"THROW (\d+),", self.verify)]
        self.assertTrue(numbers)
        self.assertTrue(all(59300 <= n <= 59399 for n in numbers), numbers)

    def test_throw_ranges_are_fresh_against_every_sibling_sql_file(self):
        own_files = {FORWARD, ROLLBACK, VERIFY}
        sql_root = ROOT / "SQL FIles"
        for path in sql_root.rglob("*.sql"):
            if path in own_files:
                continue
            source = read(path)
            numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
            colliding = [n for n in numbers if 59200 <= n <= 59399]
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertFalse(colliding, msg=f"{path} reuses reserved number(s) {colliding}")

    def test_forward_creates_exactly_the_claimed_procedure_and_nothing_else(self):
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
            if entry["id"] != "PS-SETTINGS-EXPORT-009"
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

    def test_forward_requires_exactly_the_evidence_rule_chain(self):
        self.assertIn("migration_id = N'PS-PLAT-006'", self.forward)
        # PS-AUTH-001 and PS-PLAT-003 are registry-level requirements
        # only (see this file's own header: PS-AUTH-001's
        # usp_UpsertAppUserFromAuth is the paired verification script's
        # own owner-provisioning dependency, and PS-PLAT-003 is already
        # a transitive ancestor of PS-PLAT-006 but is named directly and
        # conservatively because the verification script inserts real
        # rows into dbo.evidence_items) -- the migration body itself
        # never checks for either.
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.forward)
        self.assertNotIn("migration_id = N'PS-PLAT-003'", self.forward)
        for fragment in (
            "migration_id = N'PS-SETTINGS-EXPORT-001'",
            "migration_id = N'PS-SETTINGS-EXPORT-003'",
            "migration_id = N'PS-SETTINGS-EXPORT-004'",
            "migration_id = N'PS-SETTINGS-EXPORT-005'",
            "migration_id = N'PS-SETTINGS-EXPORT-006'",
            "migration_id = N'PS-SETTINGS-EXPORT-007'",
            "migration_id = N'PS-SETTINGS-EXPORT-008'",
        ):
            self.assertNotIn(fragment, self.forward)
        for fragment in (
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_skills', N'U') IS NULL",
            "OBJECT_ID(N'dbo.career_skill_links', N'U') IS NULL",
        ):
            self.assertIn(fragment, self.forward)

    def test_no_reader_references_recruiter_questions(self):
        # No third-party content is read by this package either.
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertNotIn("recruiter_questions", self.procedures[name])

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
        # This package's one addition must not introduce a second
        # distinct identity-header variant anywhere in the whole
        # account-export reader program (PS-SETTINGS-EXPORT-003 through
        # this package -- 31 readers total).
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
                self.assertIn("JOIN dbo.career_skills AS skill ON skill.skill_id = link.skill_id", body)

    # -- ORDER BY presence and shape ----------------------------------------------------

    def test_every_reader_has_a_deterministic_order_by(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("ORDER BY", body)
                self.assertNotIn("SELECT *", body)
                self.assertNotIn("SELECT*", body)

    def test_reader_orders_by_created_at_then_the_excluded_surrogate_tiebreak(self):
        # dbo.career_skill_links has no opaque *_key column and no
        # display_order of its own, so the trailing, excluded-from-output
        # internal id is the deterministic tiebreak -- the same "order by
        # an excluded internal id" idiom usp_ReadAccountExportAccountForOwner
        # and usp_ReadAccountExportConnectionPreferenceForOwner already use.
        body = self.procedures["usp_ReadAccountExportCareerSkillLinkForOwner"]
        order_by = body[body.index("ORDER BY"):]
        expected_order = ("link.created_at_utc", "link.skill_link_id")
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

    def test_every_safe_references_rule_column_is_a_subset_of_forbidden_fields(self):
        all_forbidden = set()
        for fields in FORBIDDEN_FIELDS.values():
            all_forbidden |= fields
        for category, columns in SAFE_REFERENCES_RULE.items():
            with self.subTest(category=category):
                self.assertTrue(columns.issubset(all_forbidden), msg=columns - all_forbidden)

    def test_every_safe_references_rule_column_is_actually_absent_from_every_readers_output(self):
        all_forbidden = set()
        for columns in SAFE_REFERENCES_RULE.values():
            all_forbidden |= columns
        for name in READER_PROCEDURES:
            columns = set(content_select_columns(self.procedures[name]))
            with self.subTest(procedure=name):
                self.assertFalse(columns & all_forbidden)

    def test_resolved_skill_key_linkage_is_present_and_skill_content_is_not_double_exported(self):
        # career_skills is already included via "living_resume" and
        # already exports skill_name/skill_summary/visibility/etc.; this
        # reader must resolve skill_id to career_skills' own skill_key
        # for intra-export linkage and never re-select any of that
        # content itself.
        for name in READER_PROCEDURES:
            columns = content_select_columns(self.procedures[name])
            with self.subTest(procedure=name):
                self.assertIn("skill_key", columns)
                for forbidden in ("skill_name", "skill_summary", "visibility", "featured", "display_order"):
                    self.assertNotIn(forbidden, columns)

    def test_evidence_linked_flag_is_present_and_computed_from_the_links_own_column(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            columns = content_select_columns(body)
            with self.subTest(procedure=name):
                self.assertIn("evidence_linked", columns)
                self.assertIn("CASE WHEN link.evidence_item_id IS NOT NULL THEN 1 ELSE 0", body)
                self.assertIn("AS bit", body)

    def test_no_reader_references_slate_entities_or_evidence_items_anywhere_in_its_body(self):
        # A stronger check than a column-name grep: proves no JOIN to
        # either excluded table exists at all, not merely that one
        # column is missing from the SELECT list.
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("slate_entities", body)
                self.assertNotIn("evidence_items", body)

    def test_domains_field_allowlist_matches_the_actual_sql_output_exactly_in_order(self):
        # domain_field_map() walks the entire shared DOMAINS dict; this
        # test owns and checks only this package's own one, asserting it
        # is present (a subset) and exactly matches in order -- never
        # that nothing else (e.g. the sibling packages') has been added.
        expected_by_procedure = domain_field_map()
        self.assertTrue(set(READER_PROCEDURES).issubset(set(expected_by_procedure)))
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                actual = content_select_columns(self.procedures[name])
                expected = list(expected_by_procedure[name])
                self.assertEqual(actual, expected)

    # -- soft-delete back-door predicate -------------------------------------

    def test_link_has_no_own_soft_delete_predicate(self):
        # dbo.career_skill_links has neither deleted_at_utc nor
        # row_version of its own.
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("link.deleted_at_utc", body)
                self.assertNotIn("link.row_version", body)

    def test_joined_skill_soft_delete_predicate_is_present_and_load_bearing(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("skill.deleted_at_utc IS NULL", body)

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
            "@SkillId", "@EvidenceItemId", "@SourceEntityId", "@Url",
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
            r"N'PS-SETTINGS-EXPORT-009',\s*\n\s*N'([^']*(?:''[^']*)*)',",
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
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-009'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-PLAT-006'", self.rollback)
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.rollback)
        self.assertNotIn("migration_id = N'PS-PLAT-003'", self.rollback)

    # -- registry -------------------------------------------------------------

    def test_registry_entry_shape_and_requires(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-009", entries)
        entry = entries["PS-SETTINGS-EXPORT-009"]
        # PS-AUTH-001 covers the verification script's own
        # usp_UpsertAppUserFromAuth dependency; PS-PLAT-006 creates both
        # tables this package reads; PS-PLAT-003 is named conservatively
        # (already a transitive ancestor of PS-PLAT-006) because the
        # verification script inserts real rows into dbo.evidence_items
        # -- see this package's own migration header for the full
        # reasoning.
        self.assertEqual(
            entry["requires"],
            ["PS-AUTH-001", "PS-PLAT-003", "PS-PLAT-006"],
        )
        for prerequisite in entry["requires"]:
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(ids.index(prerequisite), ids.index("PS-SETTINGS-EXPORT-009"))
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-009_evidence_rule_reader.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-009_evidence_rule_reader_rollback.sql",
        )
        self.assertTrue(entry["summary"])
        self.assertLessEqual(len(entry["summary"]), 450)

    def test_registry_entry_pins_the_sealed_gate(self):
        """SEALED STATE (replaced in the same lockstep commit as the gate
        block and the report's Gate state section, per the placeholder's own
        instruction -- registry + test + REPORT). Literal pins the SEAL;
        recomputation pins the FILE. Gate run 1 was REFUSED by the verify
        script's own forbidden-column scan, which as first written
        contradicted the reader's own disclosed evidence_linked design
        (the derivation MENTIONS link.evidence_item_id to test IS NOT
        NULL; the value never leaves). The fix sanctioned exactly that
        one expression in the scan -- asserting it present exactly once,
        neutralizing it, then scanning strictly. Run 2 sealed; the
        forward migration never changed, so the digest equals the
        writer's authoring-time computation."""
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        entry = entries["PS-SETTINGS-EXPORT-009"]
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual(
            gate["executable_sha256"],
            "09c900119191c2379007aae85eeee06523675351437fca868d35b880bdbdd678",
        )
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(len(gate["objects"]), 1)
        self.assertEqual(
            gate["objects"],
            ["SQL_STORED_PROCEDURE:dbo.usp_ReadAccountExportCareerSkillLinkForOwner"],
        )
        self.assertEqual(
            gate["verification"],
            "PS-SETTINGS-EXPORT-009_evidence_rule_reader_isolation_verify.sql returned verified = 1",
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

    def test_verify_uses_bare_exec_for_the_reader(self):
        bare_calls = set(re.findall(r"^\s*EXEC dbo\.(\w+)", self.verify, re.MULTILINE))
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(name, bare_calls)

    def test_verify_also_uses_insert_exec_for_the_reader_for_value_level_proof(self):
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

    def test_verify_fixture_populates_the_safe_references_rule_column_with_a_real_value(self):
        # evidence_item_id (the safe-references-only rule's own excluded
        # column) is genuinely non-null for three of five fixture rows
        # (owners A's first/third links, owner B's link), captured into
        # real Transact-SQL variables -- never merely absent because it
        # was never written.
        for column in SAFE_REFERENCES_RULE["evidence_reference"]:
            with self.subTest(column=column):
                self.assertIn(column, self.verify)
        self.assertIn("@EvidenceItemIdA1", self.verify)
        self.assertIn("@EvidenceItemIdA3", self.verify)
        self.assertIn("@EvidenceItemIdB1", self.verify)

    def test_verify_marks_every_evidence_item_canary_as_must_never_be_readable(self):
        self.assertGreaterEqual(self.verify.count("must never be readable"), 3)

    def test_verify_proves_the_evidence_linked_true_false_contrast(self):
        # The central evidence_linked proof: owner A's second link (no
        # evidence_item_id) must decode as evidence_linked = 0, contrasted
        # against owner A's first and third links (evidence_linked = 1) --
        # a genuine 0/1 contrast against a real engine, not merely a
        # value present in the procedure text.
        self.assertIn("evidence_linked = 1", self.verify)
        self.assertIn("evidence_linked = 0", self.verify)
        self.assertIn(
            "this is the central evidence_linked = 0 proof",
            self.verify.lower(),
        )

    def test_verify_proves_the_soft_delete_back_door_is_closed(self):
        self.assertIn("UPDATE dbo.career_skills SET deleted_at_utc = SYSUTCDATETIME() WHERE skill_id = @SkillIdA3", self.verify)
        self.assertIn("back door", self.verify.lower())
        self.assertIn("back door is open", self.verify.lower())
        # The drop from three rows to two, and the specific missing
        # skill_key, are both asserted -- not merely that SOME row went
        # missing.
        self.assertIn("did not drop to two rows after the joined skill''s soft-delete", self.verify)
        self.assertIn("WHERE skill_key = @SkillKeyA3", self.verify)

    def test_verify_never_references_recruiter_questions(self):
        self.assertNotIn("recruiter_questions", executable_body(self.verify))

    def test_verify_never_references_unrelated_sibling_machinery_tables(self):
        # Sanity: this package's own fixture never accidentally reaches
        # into a sibling package's excluded machinery table or an
        # out-of-scope table. dbo.file_assets is deliberately absent too
        # -- evidence_items.asset_id is left NULL by this fixture, since
        # file_assets is out of scope for this package (the mission
        # brief's own explicit steer: no locator-bearing file_asset is
        # ever planted).
        for name in (
            "knowledge_item_save_requests", "opportunity_saved_results",
            "moment_placements", "voice_media_sources", "file_assets",
        ):
            with self.subTest(table=name):
                self.assertNotIn(name, self.verify)


class AdapterModuleTests(unittest.TestCase):
    """Offline tests for services/account_export_domain_readers.py using
    fake cursors/connections only -- no database, no network. Fixture
    identifiers are entropy-dead, case-consistent placeholders
    ("aaaaaaaa-..." style), never a copied well-known example GUID."""

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

    THIS_PACKAGES_READERS = (readers_module.read_career_skill_link,)

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

    def test_career_skill_link_legitimately_empty_result_is_not_an_error(self):
        # dbo.career_skill_links is practically empty today (no writer
        # populates dbo.evidence_items anywhere in this codebase, and a
        # member may simply have no skill-evidence links at all) -- a
        # REAL owner (a resolved identity, not merely a forged key) can
        # legitimately have zero rows here. Modeled on the F1 lesson from
        # PS-SETTINGS-EXPORT-008's own independent-review round: a
        # resolved owner with an empty table produces a result set WITH a
        # real column description and zero rows -- not the
        # description-less shape an unresolved identity produces (that
        # path is the test above).
        description = [
            ("skill_key",), ("relationship_type",), ("approval_status",),
            ("strength_rank",), ("evidence_linked",), ("created_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        plan = [("clock", "FALLBACK-S"), ("content", description, []), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_career_skill_link(connection, "a-real-resolved-key")
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["read_started_at_utc"], "FALLBACK-S")
        self.assertEqual(result["read_ended_at_utc"], "FALLBACK-E")

    def test_career_skill_link_content_rows_decode_every_field_including_both_evidence_linked_states(self):
        description = [
            ("skill_key",), ("relationship_type",), ("approval_status",),
            ("strength_rank",), ("evidence_linked",), ("created_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        rows = [
            ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "learned_in", "proposed", None, False, "2020-01-01", "SQL-START", "SQL-END"),
            ("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "demonstrated_in", "approved", 85, True, "2020-01-02", "SQL-START", "SQL-END"),
        ]
        plan = [("clock", "FALLBACK-S"), ("content", description, rows), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_career_skill_link(connection, "real-key")
        self.assertEqual(len(result["rows"]), 2)
        for row in result["rows"]:
            self.assertNotIn("read_started_at_utc", row)
            self.assertNotIn("read_ended_at_utc", row)
        no_evidence_row, evidence_row = result["rows"]
        self.assertEqual(no_evidence_row["relationship_type"], "learned_in")
        self.assertIsNone(no_evidence_row["strength_rank"])
        self.assertEqual(no_evidence_row["evidence_linked"], False)
        self.assertEqual(evidence_row["relationship_type"], "demonstrated_in")
        self.assertEqual(evidence_row["strength_rank"], 85)
        self.assertEqual(evidence_row["evidence_linked"], True)
        self.assertEqual(result["read_started_at_utc"], "SQL-START")
        self.assertEqual(result["read_ended_at_utc"], "SQL-END")

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
        # Cheap regression net: this package's edits to the shared
        # DOMAINS dict must not disturb any sibling package's own
        # readers.
        for domain_code, reader_entry in iter_included_readers():
            plan = [("clock", "S"), ("none",), ("clock", "E")]
            connection = self._FakeConnection(plan)
            with self.subTest(domain=domain_code, procedure=reader_entry["procedure"]):
                result = reader_entry["function"](connection, "some-user-key")
                self.assertEqual(result["rows"], [])


class DomainsRegistryTests(unittest.TestCase):
    """Offline shape tests for the DOMAINS registry itself, scoped to
    this package's own one domain and its four updated ruling-record
    reasons -- never to "however many domains the shared dict currently
    totals," which would break the moment a future package legitimately
    adds another."""

    def test_career_skill_links_domain_is_included_with_exactly_one_reader(self):
        domain = DOMAINS["career_skill_links"]
        self.assertEqual(domain["disposition"], "included")
        self.assertIsNone(domain["reason"])
        self.assertEqual(len(domain["readers"]), 1)
        self.assertEqual(
            domain["readers"][0]["procedure"],
            "usp_ReadAccountExportCareerSkillLinkForOwner",
        )
        self.assertEqual(
            domain["readers"][0]["schema_id"],
            "peerslate.account_export.career_skill_links.career_skill_link.v1",
        )

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
        forbidden_terms = (
            "user_key", "auth_subject", "row_version", "profile_key",
            "evidence_json", "skill_link_id", "source_entity_id",
        )
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

    # -- the four (five-entry) ruling-record reason pins ---------------------
    #
    # These pin the OWNER'S RULINGS as durable text, not merely today's
    # prose: a future package that touches one of these five reasons
    # without an explicit new owner ruling fails a test here, exactly as
    # the writer brief intends ("the reasons are now owner rulings, not
    # prose").

    def test_ai_proposals_reason_pins_the_2026_08_30_ruling(self):
        reason = DOMAINS["ai_proposals"]["reason"]
        self.assertIn("2026-08-30", reason)
        self.assertIn("nothing additional to export today", reason)
        self.assertIn("live, member-facing AI proposal feature ships", reason)

    def test_profile_publication_foundation_reason_pins_the_2026_08_30_ruling(self):
        reason = DOMAINS["profile_publication_foundation"]["reason"]
        self.assertIn("2026-08-30", reason)
        self.assertIn("nothing exists to export", reason)
        self.assertIn("PS-PROFILE-002", reason)
        self.assertIn("must ship its own export reader", reason)

    def test_own_publication_versions_reason_pins_the_2026_08_30_ruling(self):
        reason = DOMAINS["own_publication_versions"]["reason"]
        self.assertIn("2026-08-30", reason)
        self.assertIn("nothing exists to export", reason)
        self.assertIn("entity_publication_versions", reason)
        self.assertIn("entity_access_grants", reason)
        self.assertIn("must ship its own export reader", reason)

    def test_community_authored_content_reason_pins_the_2026_08_30_ruling(self):
        reason = DOMAINS["community_authored_content"]["reason"]
        self.assertIn("2026-08-30", reason)
        self.assertIn("honestly omitted from v1", reason)
        self.assertIn("own words only", reason)

    def test_file_evidence_metadata_reason_pins_the_safe_references_rule(self):
        reason = DOMAINS["file_evidence_metadata"]["reason"]
        self.assertIn("2026-08-30", reason)
        self.assertIn("safe-references-only", reason)
        self.assertIn("PS-SETTINGS-EXPORT-009", reason)
        self.assertIn("never storage locators", reason)

if __name__ == "__main__":
    unittest.main()
