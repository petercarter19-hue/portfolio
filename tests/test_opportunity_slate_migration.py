"""Static contract tests for the Opportunity Slate migration —
PS-OPPSLATE-001, slice OS-1.

Mirrors tests/test_workshop_migration.py: these assert the shape of the
proposed SQL without needing a database, so the migration's guards, owner
scoping, CHECK pins, and rollback refusals are held in place by the ordinary
test run. The migration ships as proposed/ and is NOT applied by this slice.
"""

import os
import re
import unittest
from pathlib import Path

from mssql_python import connect


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
FORWARD = MIGRATIONS / "PS-OPPSLATE-001_opportunity_slate.sql"
ROLLBACK = MIGRATIONS / "PS-OPPSLATE-001_opportunity_slate_rollback.sql"
VERIFY = VERIFICATION / "PS-OPPSLATE-001_owner_isolation_verify.sql"

PROCEDURE_NAMES = (
    "usp_PurgeExpiredOpportunityWorkingData",
    "usp_GetOpportunityWorkingSessionForOwner",
    "usp_SaveOpportunitySourceForOwner",
    "usp_CorrectOpportunitySourceForOwner",
    "usp_ConfirmOpportunitySourceForOwner",
    "usp_DeleteOpportunityWorkingSessionForOwner",
)

# Every procedure that writes. usp_GetOpportunityWorkingSessionForOwner is
# deliberately absent: it is a single read and owns no transaction.
MUTATING_PROCEDURE_NAMES = (
    "usp_PurgeExpiredOpportunityWorkingData",
    "usp_SaveOpportunitySourceForOwner",
    "usp_CorrectOpportunitySourceForOwner",
    "usp_ConfirmOpportunitySourceForOwner",
    "usp_DeleteOpportunityWorkingSessionForOwner",
)

TABLE_NAMES = (
    "dbo.opportunity_working_sessions",
    "dbo.opportunity_sources",
    "dbo.opportunity_source_versions",
)

# Handoff section 1 and section 8: no overall score, percentage,
# recommendation, employer prediction, or traffic-light verdict at any
# layer, including the database. Checked as a literal absence across all
# three SQL files (comments included) so the retired concept cannot creep
# back in even as documentation.
FORBIDDEN_VERDICT_IDENTIFIERS = (
    "overall_score",
    "match_score",
    "match_percentage",
    "fit_score",
    "traffic_light",
)


def procedure_batches(sql):
    """Map each CREATE OR ALTER PROCEDURE dynamic-SQL batch to its name."""
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


def migration_wrapper(sql):
    """The migration's own batch, with every procedure body removed.

    Asserting transaction keywords against the whole file proves only that
    *somewhere* in it a transaction is opened — which the wrapper below
    satisfies on its own, whatever the procedure bodies do. Separating the
    two is what lets the wrapper test and the per-procedure test each mean
    something.
    """
    return re.sub(r"EXEC\(N'(?:''|[^'])*'\);", "", sql, flags=re.DOTALL)


class OpportunitySlateMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_forward_rollback_and_verification_exist(self):
        self.assertTrue(FORWARD.exists())
        self.assertTrue(ROLLBACK.exists())
        self.assertTrue(VERIFY.exists())

    def test_all_six_procedures_are_present_exactly_once(self):
        self.assertEqual(set(self.procedures), set(PROCEDURE_NAMES))
        self.assertEqual(
            self.forward.count("CREATE OR ALTER PROCEDURE"), len(PROCEDURE_NAMES)
        )

    def test_migration_is_one_guarded_transactional_batch(self):
        """The wrapper itself — asserted against the migration batch with the
        procedure bodies stripped out, so this can no longer be satisfied by
        a transaction that lives inside some procedure."""
        wrapper = migration_wrapper(self.forward)
        for value in (
            "SET NOCOUNT ON",
            "SET XACT_ABORT ON",
            "BEGIN TRY",
            "BEGIN TRANSACTION",
            "COMMIT TRANSACTION",
            "BEGIN CATCH",
            "ROLLBACK TRANSACTION",
            "THROW;",
        ):
            self.assertIn(value, wrapper)
        self.assertNotIn("\nGO", self.forward)
        self.assertNotIn("\nGO", self.rollback)

    def test_every_mutating_procedure_body_owns_a_transaction(self):
        """Independent review, MAJOR 1: all five write procedures set
        XACT_ABORT ON and opened no transaction.

        XACT_ABORT governs what happens to a transaction that is already
        open; it does not open one. In autocommit each statement committed
        separately, so a mid-procedure failure could commit a correction
        without clearing the confirmation it invalidates, commit a session
        and source without the version row they point at, or destroy source
        versions and leave the session claiming to hold them — and the
        UPDLOCK, HOLDLOCK guards released at statement end, serializing
        nothing. Each body is asserted individually here: the whole-file
        check above can never catch this.
        """
        for name in MUTATING_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                body = self.procedures[name]
                for value in (
                    "BEGIN TRY",
                    "BEGIN TRANSACTION;",
                    "COMMIT TRANSACTION;",
                    "END TRY",
                    "BEGIN CATCH",
                    "ROLLBACK TRANSACTION;",
                    "THROW;",
                    "END CATCH;",
                ):
                    self.assertIn(value, body)

                # Every early exit taken after the transaction opens commits
                # first. A RETURN with the transaction still open would
                # abandon it and trip the connection's next statement.
                inside = body.split("BEGIN TRANSACTION", 1)[1]
                for segment in inside.split("RETURN;")[:-1]:
                    self.assertIn("COMMIT TRANSACTION;", segment)

    def test_the_purge_enlists_in_its_callers_transaction(self):
        """usp_SaveOpportunitySourceForOwner EXECs the purge from inside its
        own transaction, so the purge opens one only when it is the
        outermost caller. Nested it enlists, which is what makes the purge's
        deletes and the rows Save then writes commit or roll back together —
        and keeps the purge's CATCH from rolling back its caller's work."""
        purge = self.procedures["usp_PurgeExpiredOpportunityWorkingData"]
        for value in (
            "DECLARE @OuterTranCount int = @@TRANCOUNT;",
            "IF @OuterTranCount = 0 BEGIN TRANSACTION;",
            "IF @OuterTranCount = 0 COMMIT TRANSACTION;",
            "IF @OuterTranCount = 0 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;",
        ):
            self.assertIn(value, purge)

        save = self.procedures["usp_SaveOpportunitySourceForOwner"]
        purge_call = save.index("EXEC dbo.usp_PurgeExpiredOpportunityWorkingData")
        self.assertLess(save.index("BEGIN TRANSACTION;"), purge_call)
        self.assertLess(purge_call, save.rindex("COMMIT TRANSACTION;"))

    def test_migration_requires_its_dependency_guards(self):
        for value in (
            "PS-PLAT-001",
            "PS-PLAT-002",
            "PS-AUTH-001",
            "PS-WORKSHOP-001",
            "dbo.app_users",
            "dbo.member_profiles",
            "dbo.audit_events",
            "dbo.usp_AppendAuditEvent",
            "dbo.knowledge_items",
            "migration_id = N'PS-OPPSLATE-001'",
        ):
            self.assertIn(value, self.forward)
        # Each prerequisite is a THROW, not a warning.
        self.assertEqual(self.forward.count("must be applied before PS-OPPSLATE-001"), 4)

    def test_migration_creates_the_three_tables(self):
        for table in TABLE_NAMES:
            self.assertIn(f"CREATE TABLE {table}", self.forward)

    def test_visibility_is_hard_locked_private(self):
        self.assertIn(
            "CONSTRAINT CK_opportunity_working_sessions_visibility CHECK (visibility = N'private')",
            self.forward,
        )

    def test_one_active_working_session_per_member(self):
        """Owner decision, handoff section 17-Q2 — enforced in the schema
        rather than trusted to the application."""
        self.assertIn(
            "CONSTRAINT UQ_opportunity_working_sessions_owner UNIQUE (owner_profile_id)",
            self.forward,
        )

    def test_workbench_state_and_capture_method_are_check_pinned(self):
        self.assertIn(
            "workbench_state IN (N'role_intake', N'review_source', N'source_confirmed')",
            self.forward,
        )
        self.assertIn(
            "capture_method IN (N'pasted', N'dictated', N'uploaded', N'imported')",
            self.forward,
        )

    def test_confirmation_state_is_a_paired_check_pinned_to_the_current_version(self):
        self.assertIn("CK_opportunity_sources_confirmation_state", self.forward)
        self.assertIn("confirmed_version_number = current_version_number", self.forward)

    def test_correction_pair_is_all_or_nothing(self):
        self.assertIn("CK_opportunity_source_versions_correction_pair", self.forward)
        self.assertIn(
            "(member_corrected_text IS NULL AND corrected_by_user_id IS NULL AND corrected_at_utc IS NULL)",
            self.forward,
        )

    def test_owner_and_version_uniqueness_constraints_exist(self):
        for constraint in (
            "CONSTRAINT UQ_opportunity_working_sessions_id_owner\n"
            "                UNIQUE (working_session_id, owner_profile_id)",
            "CONSTRAINT UQ_opportunity_sources_id_owner\n"
            "                UNIQUE (opportunity_source_id, owner_profile_id)",
            "CONSTRAINT UQ_opportunity_source_versions_number\n"
            "                UNIQUE (opportunity_source_id, version_number)",
            "CONSTRAINT UQ_opportunity_source_versions_owner_key\n"
            "                UNIQUE (owner_profile_id, idempotency_key)",
        ):
            self.assertIn(constraint, self.forward)
        # Child rows are foreign-keyed on the (id, owner) composite so a row
        # can never be reparented across owners.
        self.assertIn(
            "FOREIGN KEY (working_session_id, owner_profile_id)", self.forward
        )
        self.assertIn(
            "FOREIGN KEY (opportunity_source_id, owner_profile_id)", self.forward
        )

    def test_utf16_length_checks_match_the_service_bound(self):
        """The migration's CHECK and
        services/opportunity_slate_service.MAX_SOURCE_TEXT_UNITS must state
        the same number, or the server-side cap the public boundary relies
        on is enforced in only one of the two places."""
        from services.opportunity_slate_service import MAX_SOURCE_TEXT_UNITS

        self.assertEqual(MAX_SOURCE_TEXT_UNITS, 20000)
        self.assertIn(
            "DATALENGTH(original_text) / 2 BETWEEN 1 AND 20000", self.forward
        )
        self.assertIn(
            "DATALENGTH(member_corrected_text) / 2 BETWEEN 1 AND 20000", self.forward
        )
        self.assertIn(
            "DATALENGTH(idempotency_key) / 2 BETWEEN 1 AND 200", self.forward
        )
        self.assertIn("idempotency_key nvarchar(200) NOT NULL", self.forward)

    def test_idempotency_key_parameter_is_wider_than_the_limit_it_enforces(self):
        """A parameter narrower than its own guard silently truncates an
        over-length value, so the guard could never fire (the
        PS-WORKSHOP-001 MINOR 11 correction, applied here from the start)."""
        save = self.procedures["usp_SaveOpportunitySourceForOwner"]
        self.assertIn("@IdempotencyKey nvarchar(4000)", save)
        self.assertIn("DATALENGTH(@IdempotencyKey) / 2 NOT BETWEEN 1 AND 200", save)

    def test_no_aggregate_verdict_concept_anywhere(self):
        for sql, label in (
            (self.forward, "forward migration"),
            (self.rollback, "rollback"),
            (self.verification, "verifier"),
        ):
            for forbidden in FORBIDDEN_VERDICT_IDENTIFIERS:
                with self.subTest(file=label, identifier=forbidden):
                    if label == "verifier" and forbidden in (
                        "overall_score",
                        "match_score",
                        "match_percentage",
                    ):
                        # The verifier names these deliberately, as the
                        # patterns it refuses to find in a definition.
                        continue
                    self.assertNotIn(forbidden, sql)

    def test_every_procedure_resolves_user_key_and_never_accepts_owner_profile_id(self):
        for name, batch in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertIn("@UserKey nvarchar(300)", batch)
                self.assertNotIn("@OwnerProfileId", batch)
                self.assertIn("app_user.user_key = @UserKey", batch)
                self.assertIn("owner_profile_id = @ProfileId", batch)

    def test_the_read_enforces_expiry(self):
        """Handoff section 1: an expired working session is immediately
        inaccessible, whether or not it has been physically purged yet."""
        read = self.procedures["usp_GetOpportunityWorkingSessionForOwner"]
        self.assertIn("expires_at_utc > SYSUTCDATETIME()", read)

    def test_the_purge_only_removes_already_expired_working_data(self):
        purge = self.procedures["usp_PurgeExpiredOpportunityWorkingData"]
        self.assertIn("expires_at_utc <= @Now", purge)
        self.assertIn("UPDLOCK, HOLDLOCK", purge)
        # Owner-scoped with no all-owners branch: a member request can never
        # trigger a cross-owner destructive sweep.
        self.assertEqual(purge.count("owner_profile_id = @ProfileId"), 4)
        self.assertNotIn("@AllOwners", purge)
        # Counts are opt-out so the internal caller does not emit a second
        # result set ahead of its own.
        self.assertIn("@IncludeCounts bit = 1", purge)

    def test_save_is_idempotent_and_suppresses_an_unchanged_resubmission(self):
        save = self.procedures["usp_SaveOpportunitySourceForOwner"]
        self.assertIn("UPDLOCK, HOLDLOCK", save)
        self.assertIn("N''existing''", save)
        self.assertIn("N''unchanged''", save)
        self.assertIn("N''success''", save)
        self.assertIn("HASHBYTES(''SHA2_256'', @SourceText)", save)
        self.assertIn(
            "EXEC dbo.usp_PurgeExpiredOpportunityWorkingData\n"
            "                    @UserKey = @UserKey, @IncludeCounts = 0;",
            save,
        )

    def test_an_unchanged_resubmission_clears_a_stale_correction_overlay(self):
        """Independent review, MINOR 1: the byte-identical branch compared
        only original_sha256 and returned, leaving the member's older
        corrected wording on screen — possibly still badged confirmed — even
        though they had just supplied the original text as the source.

        A resubmission is an explicit replace, so an overlay that
        contradicts it is cleared inside the same transaction and the
        confirmation the changed display invalidates goes with it. With no
        overlay nothing is stale: the confirmation still describes exactly
        this wording, so it is preserved rather than costing the member a
        completed checkpoint.
        """
        save = self.procedures["usp_SaveOpportunitySourceForOwner"]
        branch = save.split("N''unchanged'' AS outcome", 1)[0].split(
            "IF @CurrentDigest = @Digest", 1
        )[1]

        self.assertIn("member_corrected_text = NULL", branch)
        self.assertIn("AND member_corrected_text IS NOT NULL", branch)
        self.assertIn("IF @@ROWCOUNT > 0 SET @ClearedCorrection = 1;", branch)
        self.assertIn("IF @ClearedCorrection = 1", branch)
        self.assertIn("confirmed_version_number = NULL", branch)
        # Back to Review Source only when the confirmation was actually
        # cleared, so workbench_state and the confirmation stay consistent.
        self.assertIn("WHEN @ClearedCorrection = 1 THEN N''review_source''", branch)
        # The employer's captured wording is never rewritten to match.
        self.assertNotIn("original_text =", branch)
        # And the branch closes its transaction before returning.
        self.assertIn("COMMIT TRANSACTION;", branch)

    def test_replacing_the_source_clears_the_confirmation(self):
        save = self.procedures["usp_SaveOpportunitySourceForOwner"]
        self.assertIn("confirmed_version_number = NULL", save)
        correct = self.procedures["usp_CorrectOpportunitySourceForOwner"]
        self.assertIn("confirmed_version_number = NULL", correct)

    def test_the_correction_never_touches_the_verbatim_original(self):
        """The employer's captured wording is write-once. The correction
        procedure updates member_corrected_text and its provenance pair
        only."""
        correct = self.procedures["usp_CorrectOpportunitySourceForOwner"]
        update = correct.split("UPDATE dbo.opportunity_source_versions", 1)[1].split(
            "UPDATE dbo.opportunity_sources", 1
        )[0]
        self.assertIn("member_corrected_text =", update)
        self.assertNotIn("original_text =", update)
        self.assertNotIn("original_sha256 =", update)
        for batch in self.procedures.values():
            self.assertNotIn("SET original_text", batch)

    def test_correct_confirm_and_delete_are_version_fenced(self):
        for name in (
            "usp_CorrectOpportunitySourceForOwner",
            "usp_ConfirmOpportunitySourceForOwner",
            "usp_DeleteOpportunityWorkingSessionForOwner",
        ):
            with self.subTest(procedure=name):
                batch = self.procedures[name]
                self.assertIn("@ExpectedRowVersion binary(8)", batch)
                self.assertIn("row_version = @ExpectedRowVersion", batch)
                self.assertIn("N''changed''", batch)

    def test_delete_reasserts_owner_on_every_child_predicate(self):
        delete = self.procedures["usp_DeleteOpportunityWorkingSessionForOwner"]
        self.assertIn(
            "DELETE dbo.opportunity_sources\n"
            "                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;",
            delete,
        )
        self.assertIn(
            "DELETE dbo.opportunity_working_sessions\n"
            "                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;",
            delete,
        )
        self.assertIn("version_record.owner_profile_id = @ProfileId", delete)

    def test_no_procedure_writes_an_audit_event(self):
        """A working session is ephemeral infrastructure holding private
        employer/member wording. Writing an audit row per keystroke-save
        would be noise and a second place for that wording to leak."""
        for name, batch in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertNotIn("usp_AppendAuditEvent", batch)

    def test_migration_and_rollback_fingerprint_exact_procedures(self):
        for sql in (self.forward, self.rollback):
            self.assertIn("PS_OPPSLATE_001_DEFINITION_HASH", sql)
            self.assertIn("HASHBYTES", sql)
            self.assertIn("OBJECT_DEFINITION", sql)
            self.assertIn("SHA2_256", sql)

    def test_rollback_refuses_on_data_later_migration_and_definition_drift(self):
        for value in (
            "Rollback refused",
            "a migration later than PS-OPPSLATE-001 is present",
            "a protected Opportunity Slate procedure changed after PS-OPPSLATE-001",
            "contains member records",
            "UPDLOCK, HOLDLOCK",
        ):
            self.assertIn(value, self.rollback)

    def test_rollback_drops_procedures_then_child_tables_then_parent(self):
        procedure_index = self.rollback.index(
            "DROP PROCEDURE dbo.usp_PurgeExpiredOpportunityWorkingData"
        )
        versions_index = self.rollback.index("DROP TABLE dbo.opportunity_source_versions")
        sources_index = self.rollback.index("DROP TABLE dbo.opportunity_sources")
        sessions_index = self.rollback.index("DROP TABLE dbo.opportunity_working_sessions")

        self.assertLess(procedure_index, versions_index)
        self.assertLess(versions_index, sources_index)
        self.assertLess(sources_index, sessions_index)
        for name in PROCEDURE_NAMES:
            self.assertIn(f"DROP PROCEDURE dbo.{name}", self.rollback)

    def test_verifier_has_two_owners_forged_key_canaries_and_outer_rollback(self):
        for value in (
            "@SubjectA",
            "@SubjectB",
            "@ProfileIdA",
            "@ProfileIdB",
            "@UserKeyA",
            "@UserKeyB",
            "usp_UpsertAppUserFromAuth",
            "MUST NOT ENTER OWNER A RESULT",
            "forged-user-key-does-not-exist",
            "A forged UserKey returned rows from the working-session read",
            "A forged UserKey produced a truthful-looking Correct outcome",
            "A forged UserKey produced a truthful-looking Confirm outcome",
            "A forged UserKey produced a truthful-looking Delete outcome",
            "A forged UserKey produced a truthful-looking purge outcome",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_proves_the_verbatim_original_survives_correction(self):
        for value in (
            "did not preserve the verbatim original employer wording",
            "Replacing the source destroyed the previous verbatim version",
            "Replacing the source left a stale confirmation",
            "An expired working session was still readable before purge",
            # T-SQL literals escape the apostrophe, so this is
            # "Owner B's purge destroyed owner A's working session."
            "purge destroyed owner A''s working session",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_object_definition_greps_check_all_six_procedures(self):
        self.assertIn("OBJECT_DEFINITION", self.verification)
        self.assertIn("@UserKey nvarchar(300)", self.verification)
        self.assertIn("@OwnerProfileId", self.verification)  # named as forbidden
        self.assertIn("owner_profile_id = @ProfileId", self.verification)
        for name in PROCEDURE_NAMES:
            self.assertIn(name, self.verification)

    def test_verifier_never_ends_in_a_committed_state(self):
        self.assertNotIn("COMMIT TRANSACTION", self.verification)

    def test_application_allowlist_registration(self):
        database_source = (ROOT / "services" / "database_service.py").read_text(
            encoding="utf-8"
        )
        for name in PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertEqual(database_source.count(f'"{name}"'), 1)

    def test_the_service_calls_only_allowlisted_procedure_names(self):
        service_source = (
            ROOT / "services" / "opportunity_slate_service.py"
        ).read_text(encoding="utf-8")
        called = set(re.findall(r'"(usp_[A-Za-z0-9_]+)"', service_source))
        self.assertEqual(called, set(PROCEDURE_NAMES))

    def test_the_migration_is_proposed_and_not_wired_into_the_apply_script(self):
        """Slice OS-1 ships the migration as proposed/ and applies it
        nowhere. Registering it with the apply script is a separate,
        explicitly authorized operational step."""
        self.assertIn("proposed", str(FORWARD))
        script_source = (ROOT / "scripts" / "apply_sql_migrations.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("PS-OPPSLATE-001", script_source)


@unittest.skipUnless(
    os.getenv("PS_OPPSLATE_SQL_GATE") == "1",
    "requires the isolated PS-OPPSLATE-001 SQL gate database",
)
class OpportunitySlateIsolatedSqlGateTests(unittest.TestCase):
    """Apply / verify / rollback / re-apply against a throwaway database.

    Skipped by default and never run against production. Slice OS-1 has not
    executed this gate — no isolated gate database exists on this machine —
    so the migration's runtime behaviour is asserted statically above and
    the live rehearsal remains an explicit operational step.
    """

    @classmethod
    def setUpClass(cls):
        cls.connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]

    def execute_script(self, path):
        with connect(self.connection_string, timeout=60) as connection:
            connection.setautocommit(True)
            cursor = connection.cursor()
            cursor.execute(path.read_text(encoding="utf-8"))
            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()

    def scalar(self, statement):
        with connect(self.connection_string, timeout=60) as connection:
            connection.setautocommit(True)
            cursor = connection.cursor()
            cursor.execute(statement)
            return cursor.fetchone()[0]

    def test_apply_verify_rollback_reapply(self):
        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-OPPSLATE-001'"
            ),
            1,
        )

        self.execute_script(ROLLBACK)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-OPPSLATE-001'"
            ),
            0,
        )
        self.assertIsNone(
            self.scalar(
                "SELECT OBJECT_ID(N'dbo.usp_GetOpportunityWorkingSessionForOwner', N'P')"
            )
        )

        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-OPPSLATE-001'"
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
