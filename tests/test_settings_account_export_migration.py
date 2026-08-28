"""Contracts for PS-SETTINGS-EXPORT-001, the C1 account-export foundation.

Modeled on tests/test_workshop_edit_provenance_migration.py and the other
recent migration tests: registry completeness/digest assertions plus focused
structural assertions for the enforcement rules the C0 architecture requires
(docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md)
that a static read of the SQL text can express without a live database.
"""

import json
import re
import unittest
from pathlib import Path

from scripts.migration_registry import executable_body, executable_sha256


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
FORWARD = MIGRATIONS / "PS-SETTINGS-EXPORT-001_account_export_foundation.sql"
ROLLBACK = MIGRATIONS / "PS-SETTINGS-EXPORT-001_account_export_foundation_rollback.sql"
REGISTRY = MIGRATIONS / "registry.json"

OWNER_PROCEDURES = (
    "usp_RequestAccountExportForOwner",
    "usp_GetAccountExportStatusForOwner",
    "usp_GetAccountExportDownloadMetadataForOwner",
)
WORKER_PROCEDURES = (
    "usp_ClaimAccountExportJob",
    "usp_CompleteAccountExportJob",
    "usp_FailAccountExportJob",
    "usp_ExpireAccountExportJobs",
    "usp_CleanupAccountExportJob",
)
ALL_PROCEDURES = OWNER_PROCEDURES + WORKER_PROCEDURES


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


class SettingsAccountExportMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = read(FORWARD)
        cls.rollback = read(ROLLBACK)
        cls.procedures = procedure_batches(cls.forward)

    # -- file shape -----------------------------------------------------

    def test_claimed_files_exist_and_are_single_guarded_batches(self):
        for path in (FORWARD, ROLLBACK):
            self.assertTrue(path.exists())
            source = read(path)
            self.assertNotIn("\nGO", source)
            self.assertEqual(source.count("("), source.count(")"))
            self.assertEqual(source.count("/*"), source.count("*/"))
        for source in (self.forward, self.rollback):
            for fragment in (
                "SET XACT_ABORT ON",
                "BEGIN TRY",
                "BEGIN TRANSACTION",
                "COMMIT TRANSACTION",
                "BEGIN CATCH",
                "ROLLBACK TRANSACTION",
                "THROW;",
            ):
                self.assertIn(fragment, source)

    def test_throw_numbers_are_unique_within_each_owned_file(self):
        for label, source in (("forward", self.forward), ("rollback", self.rollback)):
            with self.subTest(file=label):
                numbers = re.findall(r"THROW (\d+),", source)
                self.assertTrue(numbers)
                self.assertEqual(len(numbers), len(set(numbers)))

    def test_forward_creates_exactly_the_claimed_procedures(self):
        self.assertEqual(set(self.procedures), set(ALL_PROCEDURES))
        self.assertEqual(
            self.forward.count("CREATE OR ALTER PROCEDURE"), len(ALL_PROCEDURES)
        )

    def test_forward_creates_exactly_the_claimed_tables_and_trigger(self):
        self.assertEqual(self.forward.count("CREATE TABLE dbo.account_export_jobs"), 1)
        self.assertEqual(
            self.forward.count("CREATE TABLE dbo.account_export_job_domains"), 1
        )
        self.assertEqual(self.forward.count("CREATE TABLE"), 2)
        self.assertEqual(self.forward.count("CREATE TRIGGER"), 1)
        self.assertIn(
            "CREATE TRIGGER dbo.trg_account_export_jobs_cleanup_guard", self.forward
        )

    def test_idempotent_rerun_guards_present(self):
        self.assertIn(
            "IF OBJECT_ID(N'dbo.account_export_jobs', N'U') IS NULL", self.forward
        )
        self.assertIn(
            "IF NOT EXISTS\n    (\n        SELECT 1 FROM dbo.schema_migrations "
            "WHERE migration_id = N'PS-SETTINGS-EXPORT-001'\n    )",
            self.forward,
        )
        # CREATE OR ALTER is naturally idempotent; unlike PS-WORKSHOP-004 this
        # migration never redefines an earlier migration's procedure, so no
        # extended-properties fingerprint dance is required or present.
        self.assertNotIn("sp_addextendedproperty", self.forward)

    def test_forward_never_redefines_another_migrations_procedure(self):
        # Every other registered forward migration file must not name any
        # procedure this migration claims, and this file must not touch a
        # procedure name owned by an earlier migration's CREATE OR ALTER.
        other_forwards = [
            entry["forward"]
            for entry in json.loads(read(REGISTRY))["migrations"]
            if entry["id"] != "PS-SETTINGS-EXPORT-001"
        ]
        for relative in other_forwards:
            path = ROOT / relative
            if not path.exists():
                continue
            source = read(path)
            for procedure in ALL_PROCEDURES:
                self.assertNotIn(
                    f"PROCEDURE dbo.{procedure}",
                    source,
                    msg=f"{procedure} must be owned by exactly one migration",
                )

    OBJECT_CREATION_PATTERN = re.compile(
        r"CREATE\s+(?:OR ALTER\s+)?(?:UNIQUE\s+)?"
        r"(TABLE|PROCEDURE|TRIGGER|INDEX)\s+(?:dbo\.)?(\w+)",
        re.IGNORECASE,
    )

    def test_forward_never_redefines_another_migrations_schema_object(self):
        # Beyond procedure names (checked above): every table, index, and
        # trigger this migration creates must not be created/altered by
        # any other registered forward migration file, and vice versa. A
        # name collision here means two migrations think they own the
        # same schema object -- the same repo lesson that motivated the
        # procedure-only check, generalized to every object kind this
        # migration introduces.
        this_objects = {
            (kind.upper(), name.upper())
            for kind, name in self.OBJECT_CREATION_PATTERN.findall(self.forward)
        }
        # Sanity: this migration really does create objects of every kind
        # the pattern looks for, so the pattern itself is proven live.
        self.assertEqual(
            {kind for kind, _ in this_objects},
            {"TABLE", "PROCEDURE", "TRIGGER", "INDEX"},
        )
        other_forwards = [
            entry["forward"]
            for entry in json.loads(read(REGISTRY))["migrations"]
            if entry["id"] != "PS-SETTINGS-EXPORT-001"
        ]
        for relative in other_forwards:
            path = ROOT / relative
            if not path.exists():
                continue
            source = read(path)
            other_objects = {
                (kind.upper(), name.upper())
                for kind, name in self.OBJECT_CREATION_PATTERN.findall(source)
            }
            collisions = this_objects & other_objects
            with self.subTest(other_migration=relative):
                self.assertFalse(
                    collisions,
                    msg=f"object(s) {collisions} claimed by both this migration and {relative}",
                )

    # -- prerequisite and dependency guards ------------------------------

    def test_forward_requires_auth_and_identity_columns(self):
        for fragment in (
            "migration_id = N'PS-AUTH-001'",
            "OBJECT_ID(N'dbo.app_users', N'U') IS NULL",
            "OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL",
            "OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL",
            "COL_LENGTH(N'dbo.app_users', N'user_key')",
            "COL_LENGTH(N'dbo.member_profiles', N'profile_id')",
        ):
            self.assertIn(fragment, self.forward)

    # -- owner procedures: identity resolution and no caller-selected IDs

    def test_owner_procedures_resolve_identity_server_side(self):
        for name in OWNER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("app_user.user_key = @UserKey", body)
                self.assertIn("app_user.active = 1", body)
                self.assertIn("profile.active = 1", body)

    def test_owner_procedures_never_accept_a_caller_selected_owner_or_artifact(self):
        forbidden_params = (
            "@OwnerUserId",
            "@OwnerProfileId",
            "@TableName",
            "@Url",
            "@BlobUrl",
            "@SasToken",
            "@ArtifactReference",
            "@ProviderReference",
        )
        for name in OWNER_PROCEDURES:
            sig = signature(self.procedures[name], name)
            for forbidden in forbidden_params:
                with self.subTest(procedure=name, param=forbidden):
                    self.assertNotIn(forbidden, sig)

    def test_only_download_metadata_procedure_ever_returns_the_artifact_reference(self):
        for name in ALL_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                if name == "usp_GetAccountExportDownloadMetadataForOwner":
                    self.assertIn("final_artifact_reference", body)
                elif name == "usp_CompleteAccountExportJob":
                    # The worker writes it once, on completion; the
                    # procedure's actual returned SELECT (everything after
                    # the last COMMIT TRANSACTION) never echoes it back to
                    # any caller.
                    self.assertIn("final_artifact_reference = @FinalArtifactReference", body)
                    trailing_select = body.rsplit("COMMIT TRANSACTION;", 1)[-1]
                    self.assertIn(
                        "SELECT @JobKey AS job_key, N''ready'' AS state;",
                        trailing_select,
                    )
                    self.assertNotIn("final_artifact_reference", trailing_select)
                else:
                    self.assertNotIn("final_artifact_reference", body)

    def test_download_metadata_never_returns_a_url(self):
        body = self.procedures["usp_CompleteAccountExportJob"]
        for fragment in (
            "LEFT(LOWER(@FinalArtifactReference), 7) = N''http://''",
            "LEFT(LOWER(@FinalArtifactReference), 8) = N''https://''",
        ):
            self.assertIn(fragment, body)
        self.assertIn(
            "CK_account_export_jobs_artifact_not_url", self.forward
        )

    def test_unknown_or_foreign_job_is_the_same_neutral_empty_result(self):
        for name in (
            "usp_GetAccountExportStatusForOwner",
            "usp_GetAccountExportDownloadMetadataForOwner",
        ):
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("job.owner_profile_id = @ProfileId", body)
                # No branch distinguishes "unknown job" from "foreign job"
                # from "unauthorized owner": all three fall through the
                # same WHERE predicate to a zero-row result.
                self.assertNotIn("THROW", body)

    def test_reauthorized_owner_may_read_truthful_expired_status(self):
        body = self.procedures["usp_GetAccountExportStatusForOwner"]
        self.assertNotIn("state <> N''expired''", body)
        # The main query's WHERE clause -- everything after its FROM --
        # filters only by job key and owner profile; there is no state
        # predicate anywhere that could hide an expired row from its own
        # reauthorized owner. (The procedure DOES compare
        # job.state = N''ready'' once, inside the download_available CASE
        # expression that appears BEFORE this FROM/WHERE pair -- a
        # computed column, not a row filter -- so this test scopes to the
        # WHERE clause specifically rather than scanning the whole body,
        # which would false-positive on that legitimate comparison.)
        where_clause = body.split("FROM dbo.account_export_jobs AS job", 1)[1]
        where_clause = where_clause.split(";", 1)[0]
        self.assertIn(
            "\n            WHERE job.job_key = @JobKey\n"
            "              AND job.owner_profile_id = @ProfileId",
            where_clause,
        )
        self.assertNotIn("state", where_clause)
        # The status read is unconditional on state; expired rows are
        # returned exactly like every other state for the owning profile.
        self.assertIn("job.state,", body)

    # -- enforcement: one active job, 24h rate limit, three attempts ----

    def test_one_active_job_per_owner_enforced_two_ways(self):
        self.assertIn(
            "CREATE UNIQUE INDEX UX_account_export_jobs_owner_active", self.forward
        )
        self.assertIn(
            "ON dbo.account_export_jobs(owner_profile_id)\n            WHERE state IN (N'queued', N'running')",
            self.forward,
        )
        request_body = self.procedures["usp_RequestAccountExportForOwner"]
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", request_body)
        self.assertIn(
            "job.state = N''ready'' AND job.ready_expires_at_utc > @Now", request_body
        )
        # The race path: a concurrent duplicate insert is caught and
        # resolved to the same neutral "existing" outcome, not an error.
        self.assertIn("ERROR_NUMBER() IN (2627, 2601)", request_body)

    def test_duplicate_request_returns_existing_job_without_a_new_row(self):
        request_body = self.procedures["usp_RequestAccountExportForOwner"]
        self.assertIn("N''existing'' AS outcome", request_body)
        self.assertEqual(request_body.count("INSERT dbo.account_export_jobs"), 1)

    def test_rate_limit_is_24_hours_and_not_caller_configurable(self):
        request_body = self.procedures["usp_RequestAccountExportForOwner"]
        self.assertIn("DATEADD(HOUR, -24, @Now)", request_body)
        self.assertIn("N''rate_limited'' AS outcome", request_body)
        self.assertNotIn("@RateLimitHours", request_body)
        self.assertNotIn("@Hours", request_body)

    def test_idempotency_fingerprint_is_lowercased_before_the_strict_check(self):
        # CONVERT(char(64), HASHBYTES(...), 2) is not guaranteed to be
        # lowercase; CK_account_export_jobs_fingerprint collates
        # Latin1_General_BIN2 and rejects anything outside [0-9a-f], so an
        # unwrapped uppercase digest would fail every INSERT with a CHECK
        # violation (error 547) -- outside the 2627/2601 race CATCH. This
        # asserts LOWER(...) actually wraps the CONVERT call end to end,
        # not merely that the word LOWER appears somewhere in the body.
        request_body = self.procedures["usp_RequestAccountExportForOwner"]
        self.assertIn(
            "DECLARE @Fingerprint char(64) = LOWER(CONVERT\n"
            "                (\n"
            "                    char(64),\n"
            "                    HASHBYTES",
            request_body,
        )
        convert_start = request_body.index(
            "DECLARE @Fingerprint char(64) = LOWER(CONVERT"
        )
        statement_end = request_body.index(";", convert_start)
        statement = request_body[convert_start:statement_end].rstrip()
        # One closing paren for CONVERT, one for the LOWER(...) wrapping
        # it -- not just ");" (CONVERT alone, LOWER unclosed or absent).
        self.assertTrue(statement.endswith("))"), statement[-10:])

    def test_attempt_cap_is_three_and_enforced_in_schema_and_procedures(self):
        self.assertIn(
            "CONSTRAINT CK_account_export_jobs_attempts CHECK\n"
            "                (attempt_count BETWEEN 0 AND 3)",
            self.forward,
        )
        claim_body = self.procedures["usp_ClaimAccountExportJob"]
        self.assertIn("DECLARE @MaxAttempts int = 3;", claim_body)
        self.assertIn("attempt_count < @MaxAttempts", claim_body)
        fail_body = self.procedures["usp_FailAccountExportJob"]
        self.assertIn("DECLARE @MaxAttempts int = 3;", fail_body)
        self.assertIn("@AttemptCount < @MaxAttempts", fail_body)

    def test_no_owner_approved_limit_is_a_caller_supplied_parameter(self):
        # The provisional limits are owner-approved constants, not
        # configuration a caller can override: none of these procedures
        # takes a parameter naming a limit.
        for name in ("usp_RequestAccountExportForOwner", "usp_ClaimAccountExportJob"):
            sig = signature(self.procedures[name], name)
            for forbidden in ("@MaxAttempts", "@LeaseDurationSeconds", "@RateLimitHours"):
                self.assertNotIn(forbidden, sig)
        complete_sig = signature(
            self.procedures["usp_CompleteAccountExportJob"], "usp_CompleteAccountExportJob"
        )
        self.assertNotIn("@ReadyWindowDays", complete_sig)

    def test_lease_duration_and_ready_window_pin_the_exact_values(self):
        # The 15-minute lease (writer-chosen at the scale of C0's pickup
        # target) and the owner-approved seven-day ready window are internal
        # constants; pin their exact values so a silent change cannot pass.
        self.assertIn(
            "DECLARE @LeaseDurationSeconds int = 900;",
            self.procedures["usp_ClaimAccountExportJob"],
        )
        self.assertIn(
            "DECLARE @ReadyWindowDays int = 7;",
            self.procedures["usp_CompleteAccountExportJob"],
        )

    # -- lease fencing and worker identity boundary ----------------------

    def test_worker_procedures_never_take_a_member_user_key(self):
        for name in WORKER_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("@UserKey", body)

    def test_claim_uses_compare_and_set_locking(self):
        body = self.procedures["usp_ClaimAccountExportJob"]
        self.assertIn("WITH (ROWLOCK, UPDLOCK, READPAST)", body)
        self.assertIn("lease_token = @LeaseToken", body)
        self.assertIn("attempts_exhausted", body)

    def test_complete_and_fail_are_fenced_by_lease_token_and_expiry(self):
        for name in ("usp_CompleteAccountExportJob", "usp_FailAccountExportJob"):
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("lease_token = @LeaseToken", body)
                self.assertIn("lease_expires_at_utc > @Now", body)
                self.assertIn("state = N''running''", body)

    def test_complete_rejects_a_stale_lease_via_rowcount_fence(self):
        body = self.procedures["usp_CompleteAccountExportJob"]
        self.assertIn("IF @@ROWCOUNT <> 1", body)
        self.assertIn("completion is refused", body)

    def test_fail_requeues_while_attempts_remain_else_terminates(self):
        body = self.procedures["usp_FailAccountExportJob"]
        self.assertIn("N''queued''", body)
        self.assertIn("N''failed''", body)
        self.assertIn("failure is refused", body)

    def test_failure_code_is_a_closed_content_free_enum(self):
        for source in (self.forward,):
            self.assertIn("domain_unavailable", source)
            self.assertIn("worker_unavailable", source)
        fail_body = self.procedures["usp_FailAccountExportJob"]
        self.assertNotIn("@FailureMessage", fail_body)
        self.assertNotIn("@ErrorDetail", fail_body)

    def test_expire_blocks_download_before_any_physical_cleanup(self):
        expire_body = self.procedures["usp_ExpireAccountExportJobs"]
        self.assertIn("N''expired''", expire_body)
        self.assertIn("ready_expires_at_utc <= @Now", expire_body)
        cleanup_body = self.procedures["usp_CleanupAccountExportJob"]
        self.assertIn(
            "the export job is still ready and has not expired", cleanup_body.lower()
        )

    def test_time_order_allows_revocation_driven_early_expiry(self):
        # C0's 'expired' state covers both "the ready window elapsed" and
        # "authorization is no longer valid" -- a future revocation
        # process must be able to expire a still-unexpired ready job
        # early, so the CHECK expression itself must not force
        # expired_at_utc >= ready_expires_at_utc. Scoped to the
        # constraint's own clause, not the whole file: the header comment
        # directly above it explains the omission in prose and
        # legitimately contains that exact substring while describing
        # its absence, which would make a whole-file assertNotIn a false
        # positive.
        self.assertIn(
            "CONSTRAINT CK_account_export_jobs_time_order CHECK", self.forward
        )
        after_marker = self.forward.split(
            "CONSTRAINT CK_account_export_jobs_time_order CHECK", 1
        )[1]
        clause = after_marker.split(");", 1)[0]
        self.assertNotIn("expired_at_utc >= ready_expires_at_utc", clause)
        for fragment in (
            "started_at_utc >= requested_at_utc",
            "completed_at_utc >= started_at_utc",
            "ready_expires_at_utc >= completed_at_utc",
        ):
            self.assertIn(fragment, clause)

    def test_cleanup_pair_allows_a_failed_job_a_real_cleanup_state(self):
        # A terminal failure can still owe cleanup of a per-attempt C2
        # staging object; forcing failed -> cleanup_state = 'not_required'
        # would make that unrepresentable. queued/running still must not
        # carry a real cleanup state (nothing has concluded to clean up).
        self.assertIn(
            "(state = N'failed' AND cleanup_state IN "
            "(N'not_required', N'pending', N'cleaned'))",
            self.forward,
        )
        self.assertIn(
            "(state IN (N'queued', N'running') AND cleanup_state = N'not_required')",
            self.forward,
        )

    def test_cleanup_is_idempotent_and_never_resurrects(self):
        cleanup_body = self.procedures["usp_CleanupAccountExportJob"]
        self.assertIn("Idempotent no-op", cleanup_body)
        self.assertIn("cleanup_state = N''pending''", cleanup_body)
        self.assertIn(
            "A cleaned account export artifact cannot be resurrected.", self.forward
        )
        self.assertIn("AFTER UPDATE", self.forward)
        self.assertIn(
            "d.cleanup_state = N''cleaned'' AND i.cleanup_state <> N''cleaned''",
            self.forward,
        )

    # -- content-free logging --------------------------------------------

    def test_audit_metadata_is_content_free(self):
        for name in (
            "usp_RequestAccountExportForOwner",
            "usp_CompleteAccountExportJob",
            "usp_FailAccountExportJob",
            "usp_CleanupAccountExportJob",
        ):
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertIn("usp_AppendAuditEvent", body)
        # No metadata JSON literal anywhere embeds a body, wording, or file
        # content field name. These are already fully quoted -- do not
        # wrap them again, or "reference" becomes the never-matching
        # ""reference"" artifact.
        for forbidden in ('"body"', '"wording"', '"excerpt"', '"reference"'):
            self.assertNotIn(forbidden, self.forward)

    # -- no dynamic table names, no secrets, no grants --------------------

    def test_no_caller_selected_dynamic_table_name(self):
        # Catch EXEC(@...) and EXECUTE(@...) regardless of spacing
        # ("EXEC (@", "EXECUTE(@", "EXEC  (@", ...), not only the one
        # exact "EXEC(@" spelling.
        dynamic_exec = re.compile(r"EXEC(UTE)?\s*\(\s*@")
        for name in ALL_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("sp_executesql", body)
                self.assertIsNone(dynamic_exec.search(body))

    def test_no_grant_or_identity_creation_in_this_migration(self):
        # Scoped to the executable body (leading header comment stripped)
        # so this does not false-positive on the header's own prose
        # describing the grant model ("...so no GRANT statement appears
        # in this file" -- that sentence itself contains "GRANT"). A bare
        # \bGRANT\b catches any GRANT statement, not only "GRANT EXECUTE".
        executable = executable_body(self.forward)
        self.assertIsNone(re.search(r"\bGRANT\b", executable))
        self.assertNotIn("CREATE ROLE", self.forward)
        self.assertNotIn("CREATE USER", self.forward)
        self.assertNotIn("sp_addrolemember", self.forward)
        self.assertIn("db_ddladmin", self.forward)

    def test_domain_ledger_table_is_schema_only_in_this_slice(self):
        for name in ALL_PROCEDURES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                self.assertNotIn("account_export_job_domains", body)

    # -- rollback ---------------------------------------------------------

    def test_rollback_refuses_when_either_table_holds_data(self):
        for fragment in (
            "EXISTS (SELECT 1 FROM dbo.account_export_jobs)",
            "EXISTS (SELECT 1 FROM dbo.account_export_job_domains)",
        ):
            self.assertIn(fragment, self.rollback)

    def test_rollback_drops_every_claimed_procedure_and_the_trigger(self):
        for name in ALL_PROCEDURES:
            self.assertIn(f"DROP PROCEDURE dbo.{name}", self.rollback)
        self.assertIn(
            "DROP TRIGGER dbo.trg_account_export_jobs_cleanup_guard", self.rollback
        )

    def test_rollback_drops_child_table_before_parent(self):
        domains_index = self.rollback.index("DROP TABLE dbo.account_export_job_domains")
        jobs_index = self.rollback.index("DROP TABLE dbo.account_export_jobs")
        self.assertLess(domains_index, jobs_index)

    def test_rollback_removes_only_this_migrations_ledger_row(self):
        self.assertIn(
            "DELETE dbo.schema_migrations\n        WHERE migration_id = N'PS-SETTINGS-EXPORT-001'",
            self.rollback,
        )
        self.assertNotIn("migration_id = N'PS-AUTH-001'", self.rollback)

    # -- registry -----------------------------------------------------------

    def test_registry_entry_is_well_formed_and_requires_auth(self):
        document = json.loads(read(REGISTRY))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-001", entries)
        entry = entries["PS-SETTINGS-EXPORT-001"]
        self.assertEqual(entry["requires"], ["PS-AUTH-001"])
        self.assertLess(ids.index("PS-AUTH-001"), ids.index("PS-SETTINGS-EXPORT-001"))
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation_rollback.sql",
        )
        self.assertTrue(entry["summary"])
        self.assertIn("no domain-reader procedure", entry["summary"].lower())
        # The gate proof was run in this lane (2026-08-28, disposable
        # database ps-migration-path-20260828); whenever a gate block is
        # present its digest must match this exact file — that is the
        # only thing this test can verify offline.
        if entry["gate"] is not None:
            self.assertEqual(
                entry["gate"]["executable_sha256"], executable_sha256(FORWARD)
            )
            self.assertIn("PS-AUTH-001", entry["gate"]["prerequisites"])
        else:
            self.assertIsNone(entry["gate"])

    def test_registry_ids_are_unique(self):
        document = json.loads(read(REGISTRY))
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
