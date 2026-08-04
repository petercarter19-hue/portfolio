"""Static contract tests for the Opportunity Slate migration —
PS-OPPSLATE-001, slices OS-1 and OS-2.

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

OS1_PROCEDURE_NAMES = (
    "usp_PurgeExpiredOpportunityWorkingData",
    "usp_GetOpportunityWorkingSessionForOwner",
    "usp_SaveOpportunitySourceForOwner",
    "usp_CorrectOpportunitySourceForOwner",
    "usp_ConfirmOpportunitySourceForOwner",
    "usp_DeleteOpportunityWorkingSessionForOwner",
)

# Slice OS-2: the AI-proposal store and checkpoint 2 of 2.
OS2_PROCEDURE_NAMES = (
    "usp_GetOpportunitySourceReviewForOwner",
    "usp_SaveOpportunitySourceReviewForOwner",
    "usp_ResolveOpportunitySourceConcernForOwner",
    "usp_GetOpportunityRequirementsForOwner",
    "usp_SaveOpportunityRequirementProposalForOwner",
    "usp_CorrectOpportunityRequirementStatementForOwner",
    "usp_ConfirmOpportunityRequirementsForOwner",
)

PROCEDURE_NAMES = OS1_PROCEDURE_NAMES + OS2_PROCEDURE_NAMES

# Every procedure that writes. The two read procedures are deliberately
# absent: each is a single read and owns no transaction.
MUTATING_PROCEDURE_NAMES = (
    "usp_PurgeExpiredOpportunityWorkingData",
    "usp_SaveOpportunitySourceForOwner",
    "usp_CorrectOpportunitySourceForOwner",
    "usp_ConfirmOpportunitySourceForOwner",
    "usp_DeleteOpportunityWorkingSessionForOwner",
    "usp_SaveOpportunitySourceReviewForOwner",
    "usp_ResolveOpportunitySourceConcernForOwner",
    "usp_SaveOpportunityRequirementProposalForOwner",
    "usp_CorrectOpportunityRequirementStatementForOwner",
    "usp_ConfirmOpportunityRequirementsForOwner",
)

READ_PROCEDURE_NAMES = (
    "usp_GetOpportunityWorkingSessionForOwner",
    "usp_GetOpportunitySourceReviewForOwner",
    "usp_GetOpportunityRequirementsForOwner",
)

TABLE_NAMES = (
    "dbo.opportunity_working_sessions",
    "dbo.opportunity_sources",
    "dbo.opportunity_source_versions",
    "dbo.opportunity_source_reviews",
    "dbo.opportunity_source_concerns",
    "dbo.opportunity_requirement_sets",
    "dbo.opportunity_requirement_set_versions",
    "dbo.opportunity_requirement_statements",
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

    def test_all_thirteen_procedures_are_present_exactly_once(self):
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
            "workbench_state IN (N'role_intake', N'review_source', N'source_confirmed',\n"
            "                                     N'review_requirements', N'requirements_confirmed')",
            self.forward,
        )
        self.assertIn(
            "capture_method IN (N'pasted', N'dictated', N'uploaded', N'imported')",
            self.forward,
        )

    def test_the_widened_state_check_is_migrated_not_only_declared(self):
        """Slice OS-2 independent review, finding F4.

        The two checkpoint-2 states are declared inline in CREATE TABLE, and
        that CREATE TABLE sits inside `IF OBJECT_ID(...) IS NULL`. On a
        database already at the slice OS-1 revision the whole block is
        skipped: this file would create the new proposal tables and
        procedures, report success, and then fail at runtime the first time a
        member reached checkpoint 2, because the CHECK still refused the
        value the confirm procedure writes. The compatibility THROW below it
        probes columns on tables this file just created, so it cannot see the
        constraint at all.

        The fix is an ALTER path, and the test asserts three things about it:
        that it exists, that it is guarded so a fresh apply is unaffected,
        and that it reinstates the constraint rather than merely dropping it.
        """
        alter_index = self.forward.find(
            "ALTER TABLE dbo.opportunity_working_sessions\n"
            "                DROP CONSTRAINT CK_opportunity_working_sessions_state;"
        )
        self.assertNotEqual(alter_index, -1, "no ALTER path for the widened CHECK")

        add_index = self.forward.find(
            "ALTER TABLE dbo.opportunity_working_sessions\n"
            "            ADD CONSTRAINT CK_opportunity_working_sessions_state CHECK"
        )
        self.assertNotEqual(add_index, -1, "the CHECK is dropped and never restored")
        self.assertGreater(
            add_index,
            alter_index,
            "ADD CONSTRAINT appears before DROP CONSTRAINT, so the widened "
            "CHECK is overwritten by the narrow one it was meant to replace",
        )

        # Guarded: the drop/add only runs when the live constraint does not
        # already carry both new values, so applying this file to an empty
        # database changes nothing.
        guard = self.forward[:alter_index]
        self.assertIn("FROM sys.check_constraints", guard)
        self.assertIn(r"definition LIKE N'%review\_requirements%' ESCAPE N'\'", guard)
        self.assertIn(r"definition LIKE N'%requirements\_confirmed%' ESCAPE N'\'", guard)

        # The restored constraint carries the full five-value vocabulary, not
        # a subset that would break some other state.
        restored = self.forward[add_index : add_index + 400]
        for state in (
            "role_intake",
            "review_source",
            "source_confirmed",
            "review_requirements",
            "requirements_confirmed",
        ):
            self.assertIn(f"N'{state}'", restored)

        # And it stays inside the file's single guarded transaction — the
        # envelope this slice's review verified is not reopened.
        #
        # Both anchors name the OUTER envelope explicitly. The file contains
        # 20-odd nested COMMIT TRANSACTION statements inside procedure bodies,
        # the first of them well before this ALTER path, so a bare
        # index("COMMIT TRANSACTION") would bind to a procedure's commit and
        # assert nothing about the envelope at all.
        envelope_begin = "\n    BEGIN TRANSACTION;"
        envelope_commit = "\n    COMMIT TRANSACTION;\nEND TRY"
        self.assertEqual(
            self.forward.count(envelope_commit), 1, "envelope COMMIT is not unique"
        )
        self.assertLess(self.forward.index(envelope_begin), alter_index)
        self.assertGreater(self.forward.index(envelope_commit), add_index)

    def test_the_migration_header_states_it_is_safe_over_the_os1_revision(self):
        """Finding F4's other half: an operator deciding whether to re-run
        this file against an existing database must not have to read 2,500
        lines of T-SQL to find out."""
        header = self.forward[: self.forward.index("SET NOCOUNT ON;")]
        self.assertIn("RE-APPLYING OVER THE SLICE OS-1 REVISION IS SUPPORTED", header)
        self.assertIn("SLICE OS-2 CONSTRAINT UPGRADE", self.forward)

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
        # trigger a cross-owner destructive sweep. Slice OS-2 added five more
        # deletes (the proposal tables), each carrying the same predicate.
        self.assertEqual(purge.count("owner_profile_id = @ProfileId"), 9)
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

    # ------------------------------------------------------------------
    # Slice OS-2
    # ------------------------------------------------------------------

    def test_the_proposal_tables_keep_ai_and_member_columns_apart(self):
        """Handoff section 1's third data class, enforced in the schema.

        A statement carries the model's reading in proposed_* columns and the
        member's in member_* columns. If a future edit ever merged them,
        "PeerSlate proposed X, the member says Y" stops being a question the
        data can answer.
        """
        for column in (
            "proposed_class nvarchar(40) NOT NULL",
            "proposed_explanation nvarchar(1000) NOT NULL",
            "proposed_structure_json nvarchar(4000) NOT NULL",
            "member_class nvarchar(40) NULL",
            "member_clarification nvarchar(2000) NULL",
        ):
            self.assertIn(column, self.forward)

    def test_no_procedure_ever_writes_a_proposal_column(self):
        """The AI's reading is written once, when the proposal is recorded,
        and never edited afterwards — least of all from a member column."""
        correct = self.procedures[
            "usp_CorrectOpportunityRequirementStatementForOwner"
        ]
        for forbidden in (
            "SET proposed_class",
            "proposed_class =",
            "proposed_explanation =",
            "proposed_structure_json =",
        ):
            self.assertNotIn(forbidden, correct)
        resolve = self.procedures["usp_ResolveOpportunitySourceConcernForOwner"]
        for forbidden in ("original_text =", "SET original_text", "quoted_text ="):
            self.assertNotIn(forbidden, resolve)

    def test_resolving_a_concern_never_touches_the_verbatim_original(self):
        """Applying a member's per-concern correction writes the correction
        columns and the whole-document overlay. original_text is write-once
        and stays that way."""
        resolve = self.procedures["usp_ResolveOpportunitySourceConcernForOwner"]
        self.assertIn("member_corrected_text = @DocumentText", resolve)
        self.assertIn("member_corrected_text = CASE WHEN @Resolution", resolve)
        # Applying invalidates the confirmation; dismissing changes no
        # wording, so it must not.
        applied = resolve.split("IF @Resolution = N''applied''", 2)[-1]
        self.assertIn("confirmed_version_number = NULL", applied)
        self.assertEqual(resolve.count("confirmed_version_number = NULL"), 1)

    def test_a_statement_correction_clears_the_requirement_confirmation(self):
        correct = self.procedures[
            "usp_CorrectOpportunityRequirementStatementForOwner"
        ]
        self.assertIn("confirmed_version_number = NULL", correct)
        proposal = self.procedures[
            "usp_SaveOpportunityRequirementProposalForOwner"
        ]
        self.assertIn("confirmed_version_number = NULL", proposal)

    def test_requirement_confirmation_is_a_paired_check_on_the_current_version(self):
        self.assertIn(
            "CK_opportunity_requirement_sets_confirmation_state", self.forward
        )
        self.assertIn(
            "confirmed_version_number = current_version_number", self.forward
        )

    def test_the_four_statement_classes_are_check_pinned_in_both_columns(self):
        for constraint in (
            "CK_opportunity_requirement_statements_proposed_class",
            "CK_opportunity_requirement_statements_member_class",
        ):
            self.assertIn(constraint, self.forward)
        self.assertEqual(
            self.forward.count(
                "N'required_qualification', N'preferred_qualification'"
            ),
            2,
        )

    def test_the_concern_resolution_pair_is_all_or_nothing(self):
        """A dismissed concern changed no wording, so it must not be able to
        carry replacement wording; a pending one must not look decided."""
        self.assertIn(
            "CK_opportunity_source_concerns_resolution_pair", self.forward
        )
        for clause in (
            "member_resolution = N'pending'",
            "member_resolution = N'dismissed'",
            "member_resolution = N'applied'",
        ):
            self.assertIn(clause, self.forward)

    def test_purge_and_delete_remove_every_proposal_row_they_own(self):
        """The two slice OS-1 procedures slice OS-2 had to touch. Without
        this a purge cannot complete (expired employer wording survives its
        expiry) and an explicit delete fails on a foreign key while promising
        to be atomic."""
        for name in (
            "usp_PurgeExpiredOpportunityWorkingData",
            "usp_DeleteOpportunityWorkingSessionForOwner",
        ):
            with self.subTest(procedure=name):
                body = self.procedures[name]
                for table in (
                    "dbo.opportunity_source_concerns",
                    "dbo.opportunity_source_reviews",
                    "dbo.opportunity_requirement_statements",
                    "dbo.opportunity_requirement_set_versions",
                    "dbo.opportunity_requirement_sets",
                ):
                    self.assertIn(table, body)

    def test_the_two_read_procedures_own_no_transaction(self):
        for name in READ_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertNotIn("BEGIN TRANSACTION", self.procedures[name])

    def test_a_rejected_proposal_counts_before_it_deletes(self):
        """Isolated SQL gate, 2026-08-04, defect 1.

        Both Save-proposal procedures clear the previous proposal before
        writing the new one, and both can still reject the payload after
        that point on a count they have not yet taken. If the count guard
        runs after the DELETE and then COMMITs, an over-long proposal
        destroys the member's existing review or set - and every decision
        they had already made on it - while returning 'invalid', which tells
        the caller nothing happened.

        This was live in usp_SaveOpportunitySourceReviewForOwner: a
        21-concern payload deleted the member's review and all three
        resolved concerns, committed the delete, and reported 'invalid'.
        The order below is the fix, and its sibling already had it right.
        """
        checks = (
            (
                "usp_SaveOpportunitySourceReviewForOwner",
                "@ConcernCount > 20",
                "DELETE dbo.opportunity_source_reviews",
            ),
            (
                "usp_SaveOpportunityRequirementProposalForOwner",
                "@StatementCount < 1 OR @StatementCount > 60",
                "DELETE dbo.opportunity_requirement_set_versions",
            ),
        )
        for name, guard, delete_statement in checks:
            with self.subTest(procedure=name):
                body = self.procedures[name]
                self.assertIn(guard, body)
                self.assertIn(delete_statement, body)
                self.assertLess(
                    body.index(guard),
                    body.index(delete_statement),
                    f"{name} rejects the payload only after it has already "
                    "deleted the member's previous proposal",
                )

    def test_the_upgrade_path_corrects_the_migration_ledger_description(self):
        """Isolated SQL gate, 2026-08-04, defect 2.

        The ledger row is how an operator answers "which revision does this
        database carry?". On the upgrade over the slice OS-1 revision the
        INSERT is skipped, so without this the ledger keeps describing a
        three-table, six-procedure migration on a database that now has
        eight tables and thirteen procedures.

        applied_at_utc must NOT move: the rollback's "a later migration is
        present" guard compares against it, and re-running the file has to
        stay a no-op.
        """
        wrapper = migration_wrapper(self.forward)
        self.assertIn("UPDATE dbo.schema_migrations", wrapper)
        self.assertIn("SET description = @OppSlateDescription", wrapper)
        self.assertIn("description <> @OppSlateDescription", wrapper)
        self.assertNotIn("SET applied_at_utc", wrapper)
        self.assertIn("Slices OS-1 and OS-2:", wrapper)

    def test_json_parameters_are_validated_before_use(self):
        """A malformed JSON payload is refused by name rather than thrown as
        a raw engine error out of OPENJSON."""
        for name in (
            "usp_SaveOpportunitySourceReviewForOwner",
            "usp_SaveOpportunityRequirementProposalForOwner",
        ):
            with self.subTest(procedure=name):
                body = self.procedures[name]
                self.assertIn("ISJSON(", body)
                self.assertIn("OPENJSON(", body)
                self.assertIn("N''invalid''", body)

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

    Skipped by default and never run against production. Still skipped
    without an isolated gate database, because it mutates whatever
    AZURE_SQL_CONNECTIONSTRING points at.

    EXECUTED 2026-08-03 and PASSED, against the throwaway Azure SQL database
    ps-oppslate-001-gate-20260803 (Basic tier, deleted afterwards). It found
    three defects the static assertions above cannot reach: a missing
    candidate key that made the forward migration fail outright, and two
    verification-script errors. See the migration header for the full record.
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
