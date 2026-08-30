"""Contracts for PS-SETTINGS-EXPORT-007, the account-export Voice/Photo
media and transcript readers.

Modeled directly on tests/test_settings_export_oppslate_reader.py
(replacement package 4, main 5a1b66b1, gate passed): registry
completeness/digest-pending assertions plus focused structural assertions
for the enforcement rules the writer brief and
docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
require that a static read of the SQL/Python text can express without a
live database. Also pins services/account_export_domain_readers.py's
DOMAINS registry against the actual SQL output column lists, and
exercises the adapter's row/read-window decoding with fake cursors.

Every DOMAINS-scoped assertion below is scoped to THIS package's own one
domain ("voice_photo"), never to "whatever the whole DOMAINS dict
currently contains" -- the lesson package 1's own test file needed
applied retroactively and every later package has followed since.

THE CENTRAL FINDINGS THIS TEST FILE PINS:
  1. Every reader filters state <> 'deleted' on its own source table (both
     dbo.voice_media_sources and dbo.capture_media_sources payload-null
     every content column once state = 'deleted'); a planted deleted-state
     row is proven absent in the paired verification script.
  2. dbo.voice_transcription_attempts is read ONLY where state IN
     ('succeeded', 'failed') -- every CONCLUDED attempt, never an
     in-flight (queued/processing) one, which carries no content column
     at all per CK_voice_transcription_attempts_result.
  3. capture_id on both link tables (dbo.voice_capture_links,
     dbo.capture_media_links) is excluded outright, never resolved to
     dbo.captures.capture_key: dbo.captures sits outside this package's
     five-table scope, the identical boundary PS-SETTINGS-EXPORT-004's own
     header drew for dbo.moment_placements.target_entity_id.
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
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-007_media_transcript_reader.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-007_media_transcript_reader_rollback.sql"
VERIFY = VERIFICATION / "PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql"
REGISTRY = MIGRATIONS / "registry.json"
ADAPTER_SOURCE_PATH = ROOT / "services" / "account_export_domain_readers.py"

READER_PROCEDURES = (
    "usp_ReadAccountExportVoiceMediaSourceForOwner",
    "usp_ReadAccountExportVoiceTranscriptionAttemptForOwner",
    "usp_ReadAccountExportVoiceCaptureLinkForOwner",
    "usp_ReadAccountExportCaptureMediaSourceForOwner",
    "usp_ReadAccountExportCaptureMediaLinkForOwner",
)

# Every owner predicate each procedure needs, one per joined table -- the
# leaf table first, then each ancestor in join order. All five tables
# under read independently carry their own owner_profile_id (confirmed by
# reading PS-VOICE-001's and PS-CAPTURE-MEDIA-001's own DDL), so the
# predicate COUNT itself is a load-bearing fact this package's join depth
# introduces.
OWNER_PREDICATES = {
    "usp_ReadAccountExportVoiceMediaSourceForOwner": (
        "source.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportVoiceTranscriptionAttemptForOwner": (
        "attempt.owner_profile_id = @ProfileId",
        "source.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportVoiceCaptureLinkForOwner": (
        "link.owner_profile_id = @ProfileId",
        "source.owner_profile_id = @ProfileId",
        "attempt.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportCaptureMediaSourceForOwner": (
        "source.owner_profile_id = @ProfileId",
    ),
    "usp_ReadAccountExportCaptureMediaLinkForOwner": (
        "link.owner_profile_id = @ProfileId",
        "source.owner_profile_id = @ProfileId",
    ),
}

# How many "JOIN dbo." occurrences each procedure body should contain,
# INCLUDING the shared identity header's own "JOIN dbo.app_users". Both
# top-level source readers have no content-level join at all (parity with
# PS-SETTINGS-EXPORT-006's opportunity_slates reader); each descendant
# reader joins one more table than the last.
EXPECTED_JOIN_COUNT = {
    "usp_ReadAccountExportVoiceMediaSourceForOwner": 1,
    "usp_ReadAccountExportVoiceTranscriptionAttemptForOwner": 2,
    "usp_ReadAccountExportVoiceCaptureLinkForOwner": 3,
    "usp_ReadAccountExportCaptureMediaSourceForOwner": 1,
    "usp_ReadAccountExportCaptureMediaLinkForOwner": 2,
}

# The two tables neither link reader joins even though its own DDL
# carries the FK: dbo.captures sits outside this package's declared
# five-table scope (see FORBIDDEN_FIELDS' capture_id entries below and the
# migration's own header, "OUT-OF-SCOPE LINKAGE").
OUT_OF_SCOPE_TABLE = "dbo.captures"

# Forbidden OUTPUT field names (unqualified, as they appear after
# aliasing/dot-stripping) per procedure. A full-name set, never a
# substring list -- PS-SETTINGS-EXPORT-003's own paused-predecessor design
# notes record a naive substring scan false-positiving on legitimate
# columns.
FORBIDDEN_FIELDS = {
    "usp_ReadAccountExportVoiceMediaSourceForOwner": {
        "source_id", "owner_profile_id", "blob_name", "sha256_digest",
        "safe_error_code", "deletion_capture_row_version",
        "created_by_user_id", "deleted_by_user_id", "deleted_at_utc", "row_version",
    },
    "usp_ReadAccountExportVoiceTranscriptionAttemptForOwner": {
        "attempt_id", "source_id", "owner_profile_id", "provider_request_id",
        "safe_error_code", "row_version",
    },
    "usp_ReadAccountExportVoiceCaptureLinkForOwner": {
        "voice_capture_link_id", "source_id", "owner_profile_id", "capture_id",
        "successful_attempt_id", "confirmed_by_user_id",
    },
    "usp_ReadAccountExportCaptureMediaSourceForOwner": {
        "source_id", "owner_profile_id", "original_blob_name", "derivative_blob_name",
        "original_sha256_digest", "original_blob_etag", "derivative_sha256_digest",
        "derivative_blob_etag", "scan_result", "scan_completed_at_utc", "safe_error_code",
        "deletion_capture_row_version", "created_by_user_id", "deleted_by_user_id",
        "deleted_at_utc", "row_version",
    },
    "usp_ReadAccountExportCaptureMediaLinkForOwner": {
        "capture_media_link_id", "source_id", "owner_profile_id", "capture_id",
        "confirmed_by_user_id",
    },
}

# The four directive-named hard-exclusion categories (STORAGE_LOCATOR,
# CONTENT_DIGEST, STORAGE_ETAG, PROVIDER_REFERENCE), each canary-proven in
# the paired verification script. Every one of these must appear in
# FORBIDDEN_FIELDS above (belt) and must never appear in any procedure's
# actual output (suspenders, checked directly against DOMAINS in
# test_every_directive_category_is_actually_absent_from_every_readers_output).
DIRECTIVE_CATEGORY_COLUMNS = {
    "storage_locator": {"blob_name", "original_blob_name", "derivative_blob_name"},
    "content_digest": {"sha256_digest", "original_sha256_digest", "derivative_sha256_digest"},
    "storage_etag": {"original_blob_etag", "derivative_blob_etag"},
    "provider_reference": {"provider_request_id"},
}

# Disclosed MACHINERY columns: not a directive-named category, but
# extending this program's existing idempotency-ledger/machinery
# precedent (PS-SETTINGS-EXPORT-006's idempotency_key) to a second and
# third package. Every one of these is also canary-proven (a real value
# written in the verify script's fixture) even though it is not part of
# the four directive categories.
MACHINERY_COLUMNS = {
    "safe_error_code", "scan_result", "scan_completed_at_utc",
    "deletion_capture_row_version",
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
# header stays byte-identical across the WHOLE program, not merely within
# this file.
ACCOUNT_EXPORT_FORWARD_FILES = (
    MIGRATIONS / "PS-SETTINGS-EXPORT-003_core_readers.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-004_capture_moment_readers.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-005_workshop_reader.sql",
    MIGRATIONS / "PS-SETTINGS-EXPORT-006_oppslate_reader.sql",
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


class SettingsExportMediaTranscriptReaderMigrationTests(unittest.TestCase):
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
            ("forward", self.forward, 58800, 58899),
            ("rollback", self.rollback, 58800, 58899),
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
        self.assertTrue(all(58900 <= n <= 58999 for n in numbers), numbers)

    def test_throw_ranges_are_fresh_against_every_sibling_sql_file(self):
        own_files = {FORWARD, ROLLBACK, VERIFY}
        sql_root = ROOT / "SQL FIles"
        for path in sql_root.rglob("*.sql"):
            if path in own_files:
                continue
            source = read(path)
            numbers = [int(n) for n in re.findall(r"THROW (\d+),", source)]
            colliding = [n for n in numbers if 58800 <= n <= 58999]
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
            if entry["id"] != "PS-SETTINGS-EXPORT-007"
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

    def test_no_reader_references_dbo_captures_outside_declared_scope(self):
        # capture_id (on both link tables) is excluded outright, never
        # resolved to dbo.captures.capture_key -- dbo.captures sits
        # outside this package's declared five-table scope. See the
        # migration's own header, "OUT-OF-SCOPE LINKAGE".
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertNotIn(OUT_OF_SCOPE_TABLE, self.procedures[name])

    # -- prerequisite guards match the registry's requires list ----------

    def test_forward_requires_exactly_the_media_transcript_chain(self):
        for fragment in (
            "migration_id = N'PS-VOICE-001'",
            "migration_id = N'PS-CAPTURE-MEDIA-001'",
        ):
            self.assertIn(fragment, self.forward)
        # PS-AUTH-001 is a registry-level requirement only (the paired
        # verification script's usp_UpsertAppUserFromAuth dependency); the
        # migration body itself never checks for it -- app_users/
        # member_profiles' identity-resolution columns predate
        # PS-AUTH-001, exactly every prior package's recorded reasoning
        # for the identical omission.
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.forward)
        # PS-VOICE-001's own upstream prerequisites (PS-CAPTURE-001/002,
        # PS-MOMENT-001, PS-PLACEMENT-001) and dbo.captures' own owning
        # migration are deliberately NOT dependencies here: this package
        # reads no column any of them created, and PS-VOICE-001's own
        # ledger row already attests its own prerequisites were satisfied.
        for fragment in (
            "migration_id = N'PS-CAPTURE-001'",
            "migration_id = N'PS-CAPTURE-002'",
            "migration_id = N'PS-MOMENT-001'",
            "migration_id = N'PS-PLACEMENT-001'",
            "migration_id = N'PS-SETTINGS-EXPORT-001'",
            "migration_id = N'PS-SETTINGS-EXPORT-003'",
            "migration_id = N'PS-SETTINGS-EXPORT-004'",
            "migration_id = N'PS-SETTINGS-EXPORT-005'",
            "migration_id = N'PS-SETTINGS-EXPORT-006'",
        ):
            self.assertNotIn(fragment, self.forward)
        for fragment in (
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NULL",
            "OBJECT_ID(N'dbo.voice_transcription_attempts', N'U') IS NULL",
            "OBJECT_ID(N'dbo.voice_capture_links', N'U') IS NULL",
            "OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NULL",
            "OBJECT_ID(N'dbo.capture_media_links', N'U') IS NULL",
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
        # This package's five additions must not introduce a second
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

    # -- owner predicate presence, every table in the chain -----------------

    def test_every_reader_filters_by_every_owner_predicate_its_chain_needs(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            for predicate in OWNER_PREDICATES[name]:
                with self.subTest(procedure=name, predicate=predicate):
                    self.assertIn(predicate, body)

    def test_every_reader_asserts_the_deleted_state_exclusion_predicate(self):
        # Every reader filters state <> 'deleted' on its own source table
        # (the two link readers and the attempt reader inherit it through
        # their own joined source), never deleted_at_utc directly -- see
        # the migration's own header for why deleted_at_utc itself is
        # excluded from output rather than used as the filter.
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn("state <> N''deleted''", self.procedures[name])

    def test_no_reader_references_the_deleted_at_utc_column_directly(self):
        for name in READER_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertNotIn("deleted_at_utc", self.procedures[name])

    def test_both_photo_readers_assert_the_explicit_source_type_predicate(self):
        # Never-trust-the-default discipline (PS-SETTINGS-EXPORT-006's own
        # opportunity_slates.visibility precedent): CK_capture_media_sources_type
        # hard-locks source_type to 'photo' today, but both Photo readers
        # assert it explicitly anyway.
        for name in (
            "usp_ReadAccountExportCaptureMediaSourceForOwner",
            "usp_ReadAccountExportCaptureMediaLinkForOwner",
        ):
            with self.subTest(procedure=name):
                self.assertIn("source.source_type = N''photo''", self.procedures[name])
        for name in (
            "usp_ReadAccountExportVoiceMediaSourceForOwner",
            "usp_ReadAccountExportVoiceTranscriptionAttemptForOwner",
            "usp_ReadAccountExportVoiceCaptureLinkForOwner",
        ):
            with self.subTest(procedure=name):
                self.assertNotIn("source_type", self.procedures[name])

    def test_transcription_attempt_reader_reads_only_concluded_attempts(self):
        body = self.procedures["usp_ReadAccountExportVoiceTranscriptionAttemptForOwner"]
        self.assertIn("attempt.state IN (N''succeeded'', N''failed'')", body)
        self.assertNotIn("N''queued''", body)
        self.assertNotIn("N''processing''", body)

    # -- join shape ----------------------------------------------------------

    def test_join_count_matches_the_chain_depth_per_procedure(self):
        for name in READER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertEqual(len(re.findall(r"\bJOIN dbo\.", body)), EXPECTED_JOIN_COUNT[name])
        for name in (
            "usp_ReadAccountExportVoiceMediaSourceForOwner",
            "usp_ReadAccountExportCaptureMediaSourceForOwner",
        ):
            self.assertIn("JOIN dbo.app_users AS app_user", self.procedures[name])

    def test_descendant_readers_join_every_ancestor_table_by_name(self):
        chain = {
            "usp_ReadAccountExportVoiceTranscriptionAttemptForOwner": (
                "dbo.voice_media_sources AS source",
            ),
            "usp_ReadAccountExportVoiceCaptureLinkForOwner": (
                "dbo.voice_media_sources AS source",
                "dbo.voice_transcription_attempts AS attempt",
            ),
            "usp_ReadAccountExportCaptureMediaLinkForOwner": (
                "dbo.capture_media_sources AS source",
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

    def test_attempt_reader_orders_parent_then_own_sequence(self):
        # attempt_number is unique only WITHIN one source
        # (UQ_voice_transcription_attempts_source_number), so a flat
        # reader over every owner's rows must order by the parent first.
        body = self.procedures["usp_ReadAccountExportVoiceTranscriptionAttemptForOwner"]
        order_by = body[body.index("ORDER BY"):]
        expected_order = ("source.created_at_utc", "source.source_key", "attempt.attempt_number")
        positions = [order_by.index(term) for term in expected_order]
        self.assertEqual(positions, sorted(positions), msg=order_by)

    def test_top_level_and_link_readers_order_by_own_or_source_timestamp_then_key(self):
        cases = {
            "usp_ReadAccountExportVoiceMediaSourceForOwner": ("source.created_at_utc", "source.source_key"),
            "usp_ReadAccountExportVoiceCaptureLinkForOwner": ("source.created_at_utc", "source.source_key"),
            "usp_ReadAccountExportCaptureMediaSourceForOwner": ("source.created_at_utc", "source.source_key"),
            "usp_ReadAccountExportCaptureMediaLinkForOwner": ("source.created_at_utc", "source.source_key"),
        }
        for name, expected_order in cases.items():
            body = self.procedures[name]
            order_by = body[body.index("ORDER BY"):]
            with self.subTest(procedure=name):
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

    def test_every_machinery_column_is_a_subset_of_forbidden_fields(self):
        all_forbidden = set()
        for fields in FORBIDDEN_FIELDS.values():
            all_forbidden |= fields
        self.assertTrue(MACHINERY_COLUMNS.issubset(all_forbidden), msg=MACHINERY_COLUMNS - all_forbidden)

    def test_every_machinery_column_is_actually_absent_from_every_readers_output(self):
        for name in READER_PROCEDURES:
            columns = set(content_select_columns(self.procedures[name]))
            with self.subTest(procedure=name):
                self.assertFalse(columns & MACHINERY_COLUMNS)

    def test_domains_field_allowlist_matches_the_actual_sql_output_exactly_in_order(self):
        # domain_field_map() walks the entire shared DOMAINS dict; this
        # test owns and checks only this package's own five, asserting
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
            "@SourceKey", "@AttemptKey", "@CaptureKey", "@Url", "@BlobUrl", "@BlobName",
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
        # gate round failed on a 779-character description. This
        # package's own description is kept at or under 450 characters
        # from the start, matching the writer brief's explicit budget.
        match = re.search(
            r"N'PS-SETTINGS-EXPORT-007',\s*\n\s*N'([^']*(?:''[^']*)*)',",
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
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-007'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-VOICE-001'", self.rollback)
        self.assertNotIn("migration_id = N'PS-CAPTURE-MEDIA-001'", self.rollback)

    # -- registry -------------------------------------------------------------

    def test_registry_entry_shape_and_requires(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-007", entries)
        entry = entries["PS-SETTINGS-EXPORT-007"]
        # PS-AUTH-001 is required because the paired verification script
        # provisions its synthetic owners through usp_UpsertAppUserFromAuth
        # -- named from the start, matching every package since
        # PS-SETTINGS-EXPORT-003's own gate round had to add this after
        # the fact. PS-VOICE-001 and PS-CAPTURE-MEDIA-001 are the two
        # migrations that create all five of this package's tables.
        self.assertEqual(
            entry["requires"],
            ["PS-AUTH-001", "PS-VOICE-001", "PS-CAPTURE-MEDIA-001"],
        )
        for prerequisite in entry["requires"]:
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(ids.index(prerequisite), ids.index("PS-SETTINGS-EXPORT-007"))
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-007_media_transcript_reader.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-007_media_transcript_reader_rollback.sql",
        )
        self.assertTrue(entry["summary"])
        self.assertLessEqual(len(entry["summary"]), 450)

    def test_registry_entry_pins_the_sealed_gate(self):
        """SEALED STATE (replaced in the same lockstep commit as the gate
        block and the report's Gate state section, per the placeholder's own
        instruction -- registry + test + REPORT). Literal pins the SEAL;
        recomputation pins the FILE. Gate run 1 was FAILED by the engine
        (the deleted-state photo fixture omitted scan_result, whose
        DEFAULT N'unknown' violates the deleted branch of
        CK_capture_media_sources_original_payload); run 2 sealed after
        the two-row fixture fix -- the catch is recorded in CR6's Gate
        state section."""
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        entry = entries["PS-SETTINGS-EXPORT-007"]
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual(
            gate["executable_sha256"],
            "14d21bd2f4e1d88829d75cedb76b3c39ad63d80e104468c159dff3e1222c35a5",
        )
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(len(gate["objects"]), 5)
        self.assertTrue(all(
            o.startswith("SQL_STORED_PROCEDURE:dbo.usp_ReadAccountExport")
            for o in gate["objects"]
        ))
        self.assertEqual(
            gate["verification"],
            "PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql returned verified = 1",
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
        # A genuine exclusion proof needs the excluded value to actually
        # exist in the fixture, not merely be absent because it was never
        # written. Every directive-category column must appear as a
        # fixture INSERT column list entry somewhere in the verify script.
        all_excluded = set()
        for columns in DIRECTIVE_CATEGORY_COLUMNS.values():
            all_excluded |= columns
        for column in all_excluded:
            with self.subTest(column=column):
                self.assertIn(column, self.verify)

    def test_verify_fixture_populates_every_machinery_column_with_a_real_value(self):
        for column in MACHINERY_COLUMNS:
            with self.subTest(column=column):
                self.assertIn(column, self.verify)

    def test_verify_proves_the_deleted_row_exclusion_for_both_source_tables(self):
        self.assertIn("deleted-state voice media source is still returned", self.verify)
        self.assertIn("deleted-state capture media source is still returned", self.verify)
        # The deleted rows are inserted directly in state = 'deleted',
        # never soft-deleted mid-script by an UPDATE.
        self.assertIn("N'deleted', @UserIdA, SYSUTCDATETIME(), @UserIdA", self.verify)

    def test_verify_proves_the_in_flight_attempt_exclusion(self):
        self.assertIn("N'processing'", self.verify)
        self.assertIn("in-flight (processing) transcription attempt is still returned", self.verify)
        self.assertIn("failed", self.verify.lower())

    def test_verify_never_references_unrelated_sibling_machinery_tables(self):
        # Sanity: this package's own fixture never accidentally reaches
        # into a sibling package's excluded machinery table or an
        # out-of-scope table.
        for name in (
            "knowledge_item_save_requests", "career_skill_links", "slate_entities",
            "opportunity_saved_results", "moment_placements",
        ):
            with self.subTest(table=name):
                self.assertNotIn(name, self.verify)


class AdapterModuleTests(unittest.TestCase):
    """Offline tests for services/account_export_domain_readers.py using
    fake cursors/connections only -- no database, no network. Fixture
    identifiers are entropy-dead, case-consistent placeholders
    ("aaaaaaaa-..." style), never a copied well-known example GUID."""

    _SOURCE_KEY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _ATTEMPT_KEY = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

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
        readers_module.read_voice_media_source,
        readers_module.read_voice_transcription_attempt,
        readers_module.read_voice_capture_link,
        readers_module.read_capture_media_source,
        readers_module.read_capture_media_link,
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

    def test_voice_media_source_content_row_uses_the_sql_embedded_read_window_not_the_fallback(self):
        description = [
            ("source_key",), ("content_type",), ("byte_length",), ("locale",),
            ("client_duration_milliseconds",), ("verified_duration_milliseconds",),
            ("state",), ("created_at_utc",), ("updated_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            self._SOURCE_KEY, "audio/webm", 12345, "en-US", 4200, 4100,
            "confirmed", "2020-01-01", "2020-01-02", "SQL-START", "SQL-END",
        )
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_voice_media_source(connection, "real-key")
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("read_started_at_utc", result["rows"][0])
        self.assertNotIn("read_ended_at_utc", result["rows"][0])
        self.assertEqual(result["rows"][0]["source_key"], self._SOURCE_KEY)
        self.assertEqual(result["read_started_at_utc"], "SQL-START")
        self.assertEqual(result["read_ended_at_utc"], "SQL-END")

    def test_voice_transcription_attempt_content_row_decodes_parent_linkage_key(self):
        description = [
            ("source_key",), ("attempt_key",), ("attempt_number",), ("state",),
            ("provider_transcript",), ("queued_at_utc",), ("started_at_utc",), ("completed_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            self._SOURCE_KEY, self._ATTEMPT_KEY, 1, "succeeded",
            "member spoken words", "2020-01-01", "2020-01-01", "2020-01-01",
            "SQL-START", "SQL-END",
        )
        plan = [("clock", "FALLBACK-S"), ("content", description, [row]), ("clock", "FALLBACK-E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_voice_transcription_attempt(connection, "real-key")
        self.assertEqual(result["rows"][0]["source_key"], self._SOURCE_KEY)
        self.assertEqual(result["rows"][0]["attempt_key"], self._ATTEMPT_KEY)
        self.assertEqual(result["rows"][0]["provider_transcript"], "member spoken words")

    def test_voice_capture_link_content_row_decodes_both_linkage_keys(self):
        description = [
            ("source_key",), ("attempt_key",), ("confirmed_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (self._SOURCE_KEY, self._ATTEMPT_KEY, "2020-01-01", "SQL-START", "SQL-END")
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_voice_capture_link(connection, "real-key")
        self.assertEqual(result["rows"][0]["source_key"], self._SOURCE_KEY)
        self.assertEqual(result["rows"][0]["attempt_key"], self._ATTEMPT_KEY)

    def test_capture_media_source_content_row_decodes_pixel_and_size_facts(self):
        description = [
            ("source_key",), ("source_type",), ("original_content_type",), ("original_byte_length",),
            ("derivative_content_type",), ("derivative_byte_length",), ("pixel_width",), ("pixel_height",),
            ("state",), ("created_at_utc",), ("updated_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (
            self._SOURCE_KEY, "photo", "image/jpeg", 44444, "image/jpeg", 5555, 800, 600,
            "confirmed", "2020-01-01", "2020-01-02", "SQL-START", "SQL-END",
        )
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_capture_media_source(connection, "real-key")
        self.assertEqual(result["rows"][0]["source_key"], self._SOURCE_KEY)
        self.assertEqual(result["rows"][0]["pixel_width"], 800)
        self.assertEqual(result["rows"][0]["pixel_height"], 600)

    def test_capture_media_link_content_row_decodes_source_linkage(self):
        description = [
            ("source_key",), ("confirmed_at_utc",),
            ("read_started_at_utc",), ("read_ended_at_utc",),
        ]
        row = (self._SOURCE_KEY, "2020-01-01", "SQL-START", "SQL-END")
        plan = [("clock", "S"), ("content", description, [row]), ("clock", "E")]
        connection = self._FakeConnection(plan)
        result = readers_module.read_capture_media_link(connection, "real-key")
        self.assertEqual(result["rows"][0]["source_key"], self._SOURCE_KEY)

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
    package's own domain ("voice_photo") -- never to "however many domains
    the shared dict currently totals," which would break the moment a
    future package legitimately adds another."""

    _THIS_PACKAGES_DOMAIN = "voice_photo"

    def test_voice_photo_is_included_with_exactly_five_readers_in_order(self):
        domain = DOMAINS[self._THIS_PACKAGES_DOMAIN]
        self.assertEqual(domain["disposition"], "included")
        self.assertIsNone(domain["reason"])
        self.assertEqual(
            [r["procedure"] for r in domain["readers"]],
            list(READER_PROCEDURES),
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
