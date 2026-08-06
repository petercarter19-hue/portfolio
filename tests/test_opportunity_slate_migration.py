"""Static contract tests for the Opportunity Slate migrations —
PS-OPPSLATE-001 (OS-1/OS-2) plus additive PS-OPPSLATE-002 (OS-3).

Mirrors tests/test_workshop_migration.py: these assert the shape of the
proposed SQL without needing a database, so the migration's guards, owner
scoping, CHECK pins, and rollback refusals are held in place by the ordinary
test run. OS-3's schema and procedure allowlist deliberately release before
the OS-3 route/service code, so production can be upgraded before a live route
can call a procedure that does not exist yet.
"""

import json
import os
import re
import unittest
from pathlib import Path

from mssql_python import connect


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
BASE_FORWARD = MIGRATIONS / "PS-OPPSLATE-001_opportunity_slate.sql"
BASE_ROLLBACK = MIGRATIONS / "PS-OPPSLATE-001_opportunity_slate_rollback.sql"
BASE_VERIFY = VERIFICATION / "PS-OPPSLATE-001_owner_isolation_verify.sql"
FORWARD = MIGRATIONS / "PS-OPPSLATE-002_opportunity_slate_os3.sql"
ROLLBACK = MIGRATIONS / "PS-OPPSLATE-002_opportunity_slate_os3_rollback.sql"
VERIFY = VERIFICATION / "PS-OPPSLATE-002_owner_isolation_verify.sql"

# PS-OPPSLATE-003 (OS-4): the save-lifecycle delta, re-cut as its own
# additive migration over the 001+002 baseline exactly like OS-3 became
# PS-OPPSLATE-002 rather than an in-place edit of PS-OPPSLATE-001.
FORWARD_003 = MIGRATIONS / "PS-OPPSLATE-003_opportunity_slate_os4.sql"
ROLLBACK_003 = MIGRATIONS / "PS-OPPSLATE-003_opportunity_slate_os4_rollback.sql"
VERIFY_003 = VERIFICATION / "PS-OPPSLATE-003_owner_isolation_verify.sql"
REGISTRY_PATH = ROOT / "SQL FIles" / "Migrations" / "registry.json"

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

# Slice OS-3: the grounded alignment analysis, the member's responses, and the
# READ-ONLY evidence allowlist the analysis is grounded in.
OS3_PROCEDURE_NAMES = (
    "usp_ListOpportunityEvidenceForOwner",
    "usp_GetOpportunityAnalysisForOwner",
    "usp_SaveOpportunityAnalysisForOwner",
    "usp_SaveOpportunityResponseForOwner",
)

# Slice OS-4: the durable saved slate and its save lifecycle. Unlike every
# earlier slice, OS-4 revises no existing procedure - see PS-OPPSLATE-003's
# own header - so this tuple is purely additive.
OS4_PROCEDURE_NAMES = (
    "usp_GetOpportunitySavedSlateForOwner",
    "usp_SaveOpportunitySlateForOwner",
    "usp_DeleteOpportunitySavedSlateForOwner",
)

OS4_TABLE_NAMES = (
    "dbo.opportunity_slates",
    "dbo.opportunity_saved_results",
    "dbo.opportunity_saved_qualifications",
    "dbo.opportunity_saved_evidence",
)

PROCEDURE_NAMES = OS1_PROCEDURE_NAMES + OS2_PROCEDURE_NAMES + OS3_PROCEDURE_NAMES

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
    "usp_SaveOpportunityAnalysisForOwner",
    "usp_SaveOpportunityResponseForOwner",
)

READ_PROCEDURE_NAMES = (
    "usp_GetOpportunityWorkingSessionForOwner",
    "usp_GetOpportunitySourceReviewForOwner",
    "usp_GetOpportunityRequirementsForOwner",
    "usp_GetOpportunityAnalysisForOwner",
    "usp_ListOpportunityEvidenceForOwner",
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
    "dbo.opportunity_analyses",
    "dbo.opportunity_analysis_statements",
    "dbo.opportunity_analysis_citations",
    "dbo.opportunity_responses",
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
        cls.base_forward = BASE_FORWARD.read_text(encoding="utf-8")
        cls.os3_forward = FORWARD.read_text(encoding="utf-8")
        cls.forward = cls.base_forward + "\n" + cls.os3_forward
        cls.base_rollback = BASE_ROLLBACK.read_text(encoding="utf-8")
        cls.os3_rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.rollback = cls.base_rollback + "\n" + cls.os3_rollback
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_forward_rollback_and_verification_exist(self):
        for path in (
            BASE_FORWARD, BASE_ROLLBACK, BASE_VERIFY, FORWARD, ROLLBACK, VERIFY
        ):
            self.assertTrue(path.exists())

    def test_every_procedure_is_present_exactly_once(self):
        self.assertEqual(set(self.procedures), set(PROCEDURE_NAMES))
        self.assertEqual(
            self.base_forward.count("CREATE OR ALTER PROCEDURE"),
            len(OS1_PROCEDURE_NAMES + OS2_PROCEDURE_NAMES),
        )
        self.assertEqual(self.os3_forward.count("CREATE OR ALTER PROCEDURE"), 8)

    def test_migration_is_one_guarded_transactional_batch(self):
        """The wrapper itself — asserted against the migration batch with the
        procedure bodies stripped out, so this can no longer be satisfied by
        a transaction that lives inside some procedure."""
        for sql in (self.base_forward, self.os3_forward):
            wrapper = migration_wrapper(sql)
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

    def test_migration_creates_every_table_it_owns(self):
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
        alter_index = self.base_forward.find(
            "ALTER TABLE dbo.opportunity_working_sessions\n"
            "                DROP CONSTRAINT CK_opportunity_working_sessions_state;"
        )
        self.assertNotEqual(alter_index, -1, "no ALTER path for the widened CHECK")

        add_index = self.base_forward.find(
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
        guard = self.base_forward[:alter_index]
        self.assertIn("FROM sys.check_constraints", guard)
        self.assertIn(r"definition LIKE N'%review\_requirements%' ESCAPE N'\'", guard)
        self.assertIn(r"definition LIKE N'%requirements\_confirmed%' ESCAPE N'\'", guard)

        # The restored constraint carries the full five-value vocabulary, not
        # a subset that would break some other state.
        restored = self.base_forward[add_index : add_index + 400]
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
        wrapper = self.base_forward
        envelope_begin = "\n    BEGIN TRANSACTION;"
        envelope_commit = "\n    COMMIT TRANSACTION;\nEND TRY"
        self.assertEqual(
            wrapper.count(envelope_commit), 1, "envelope COMMIT is not unique"
        )
        self.assertLess(wrapper.index(envelope_begin), alter_index)
        self.assertGreater(wrapper.index(envelope_commit), add_index)

    def test_the_migration_header_states_it_is_safe_over_the_os1_revision(self):
        """Finding F4's other half: an operator deciding whether to re-run
        this file against an existing database must not have to read 2,500
        lines of T-SQL to find out."""
        header = self.base_forward[: self.base_forward.index("SET NOCOUNT ON;")]
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
        # Slice OS-3 added four more (the analysis, its statements, its
        # citations, and the member's responses), each carrying the same
        # predicate.
        self.assertEqual(purge.count("owner_profile_id = @ProfileId"), 13)
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

    def test_verifier_names_every_procedure_the_migration_owns(self):
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
        # OS-4's three procedures are called by the service and allowlisted
        # in services/database_service.py. PS-OPPSLATE-003's SQL is now
        # merged into main, so this file can assert against it directly —
        # but it is neither gated nor applied (registry.json gate is null;
        # see test_registry_entry_has_no_gate_proof_yet). This branch does
        # not go live until PS-OPPSLATE-003 is gated and applied.
        self.assertEqual(called, set(PROCEDURE_NAMES) | set(OS4_PROCEDURE_NAMES))

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
        base_wrapper = migration_wrapper(self.base_forward)
        self.assertIn("UPDATE dbo.schema_migrations", base_wrapper)
        self.assertIn("SET description = @OppSlateDescription", base_wrapper)
        self.assertIn("description <> @OppSlateDescription", base_wrapper)
        self.assertNotIn("SET applied_at_utc", base_wrapper)
        self.assertIn("Slices OS-1 and OS-2:", base_wrapper)

        os3_wrapper = migration_wrapper(self.os3_forward)
        self.assertIn("N'PS-OPPSLATE-002'", os3_wrapper)
        self.assertNotIn("UPDATE dbo.schema_migrations", os3_wrapper)

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

    # ------------------------------------------------------------------
    # Slice OS-3
    # ------------------------------------------------------------------

    def test_the_analysis_tables_hold_no_field_a_verdict_could_live_in(self):
        """The schema-level half of the composition boundary.

        There is no free-text column on any OS-3 table that a model's sentence
        could reach. Every string column holds either a verbatim span of the
        employer's clause, a verbatim excerpt of the member's own evidence, a
        pinned title, or the member's own words.
        """
        analysis_block = self.forward.split("CREATE TABLE dbo.opportunity_analyses")[1]
        analysis_block = analysis_block.split("CREATE TABLE dbo.opportunity_responses")[0]
        for banned in (
            "explanation",
            "rationale",
            "summary",
            "narrative",
            "commentary",
            "reason",
        ):
            with self.subTest(column=banned):
                self.assertNotIn(f"{banned} nvarchar", analysis_block)

    def test_the_derived_status_is_the_three_named_states_and_nothing_else(self):
        self.assertIn(
            "derived_status IN (N'supported', N'partially_supported',\n"
            "                                    N'not_enough_information')",
            self.forward,
        )

    def test_a_status_cannot_disagree_with_its_own_citation_count(self):
        """A "supported" row with nothing behind it, or a cited row that calls
        itself "not enough information", is refused by the database as well as
        by the application."""
        self.assertIn("CK_opportunity_analysis_statements_citation_pair", self.forward)
        self.assertIn(
            "(citation_count = 0 AND derived_status = N'not_enough_information')",
            self.forward,
        )
        self.assertIn(
            "(citation_count > 0 AND derived_status <> N'not_enough_information')",
            self.forward,
        )

    def test_evidence_is_referenced_and_never_written(self):
        """Opportunity Slate reads the member's Workshop library and writes
        none of it."""
        for name in PROCEDURE_NAMES:
            body = self.procedures[name]
            with self.subTest(procedure=name):
                for write in (
                    "INSERT dbo.knowledge_item",
                    "UPDATE dbo.knowledge_item",
                    "DELETE dbo.knowledge_item",
                    "INSERT dbo.moment",
                    "UPDATE dbo.moment",
                    "DELETE dbo.moment",
                ):
                    self.assertNotIn(write, body)
        allowlist = self.procedures["usp_ListOpportunityEvidenceForOwner"]
        self.assertIn("FROM dbo.knowledge_items AS item", allowlist)
        self.assertIn("item.item_status = N''confirmed''", allowlist)
        self.assertIn("item.archived_at_utc IS NULL", allowlist)

    def test_the_response_shape_check_is_all_or_nothing_per_kind(self):
        """"I do not have this experience" and "skip" carry no text and no
        evidence, so neither can be made to look like an answer the member did
        not give."""
        self.assertIn("CONSTRAINT CK_opportunity_responses_shape CHECK", self.forward)
        for kind in (
            "N'tell_more', N'real_example'",
            "response_kind = N'connect_evidence'",
            "N'confirm_not_have', N'skip'",
        ):
            self.assertIn(kind, self.forward)

    def test_every_rejection_returns_before_any_mutation(self):
        """The 2026-08-04 gate's defect 1, applied to the two new writers: a
        procedure that deletes first and validates afterwards destroys member
        data and then reports that nothing happened."""
        for name in (
            "usp_SaveOpportunityAnalysisForOwner",
            "usp_SaveOpportunityResponseForOwner",
        ):
            body = self.procedures[name]
            with self.subTest(procedure=name):
                first_mutation = min(
                    (
                        position
                        for position in (
                            body.find("DELETE dbo."),
                            body.find("DELETE citation_record"),
                            body.find("DELETE analysis_statement"),
                            body.find("INSERT dbo."),
                            body.find("UPDATE dbo."),
                        )
                        if position != -1
                    ),
                    default=len(body),
                )
                last_rejection = max(
                    body.rfind("SELECT N''invalid''"),
                    body.rfind("SELECT N''changed''"),
                )
                self.assertNotEqual(last_rejection, -1)
                self.assertLess(
                    last_rejection,
                    first_mutation,
                    f"{name} mutates before its final rejection returns",
                )

    def test_the_analysis_writer_re_derives_the_cited_evidence_identity(self):
        """Independent review finding F7.

        usp_SaveOpportunityAnalysisForOwner used to take evidence_key,
        evidence_version, evidence_title AND evidence_kind straight out of the
        payload and write them, with no lookup against dbo.knowledge_items at
        all — so nothing checked that a cited key was the member's own, that
        the item was confirmed and unarchived, or that the pinned version was
        the confirmed one. Its sibling usp_SaveOpportunityResponseForOwner
        already did this correctly. It now does the same lookup.
        """
        body = self.procedures["usp_SaveOpportunityAnalysisForOwner"]
        self.assertIn("FROM @Citations AS citation", body)
        self.assertIn("JOIN dbo.knowledge_items AS item", body)
        self.assertIn("item.knowledge_item_key = citation.evidence_key", body)
        self.assertIn("item.owner_profile_id = @ProfileId", body)
        self.assertIn("item.item_status = N''confirmed''", body)
        self.assertIn("item.archived_at_utc IS NULL", body)
        self.assertIn(
            "item_version.version_number = item.confirmed_version_number", body
        )
        # And the identity is no longer read out of the payload anywhere.
        self.assertNotIn("evidence_version int ''$.evidence_version''", body)
        self.assertNotIn("evidence_title nvarchar(200) ''$.evidence_title''", body)
        self.assertNotIn("evidence_kind nvarchar(30) ''$.evidence_kind''", body)
        # The one kind slice OS-3 grounds on is a literal, not a parameter.
        self.assertIn("N''knowledge_item'',", body)

    def test_the_service_stops_sending_the_identity_the_database_derives(self):
        """The other half of F7. Leaving three fields in the payload that
        nothing reads is how a caller comes to believe it controls them."""
        source = (ROOT / "services" / "opportunity_slate_service.py").read_text(
            encoding="utf-8"
        )
        payload = source.split("def save_analysis_for_owner")[1].split(
            "row = self.database.first_row"
        )[0]
        for retired in (
            '"evidence_kind":',
            '"evidence_version":',
            '"evidence_title":',
        ):
            with self.subTest(field=retired):
                self.assertNotIn(retired, payload)
        for kept in ('"evidence_key":', '"excerpt":', '"covered_text":'):
            with self.subTest(field=kept):
                self.assertIn(kept, payload)

    def test_the_citations_are_validated_before_the_first_delete(self):
        """Independent review finding F8.

        The header claimed every rejection returned before the first DELETE.
        That was true of the per-qualification rows and false of the
        CITATIONS: eight constraints on dbo.opportunity_analysis_citations
        could not fire until the INSERT, which is after all three DELETEs, so
        the caller got a 503 where it should have got 'invalid'. Member data
        was never at risk — XACT_ABORT and the CATCH rollback restore
        everything — but a claim in a header is either true or it is removed.
        """
        body = self.procedures["usp_SaveOpportunityAnalysisForOwner"]
        shred = body.find("INSERT @Citations")
        guard = body.find("SELECT 1 FROM @Citations AS citation")
        first_delete = body.find("DELETE citation_record")
        self.assertNotEqual(shred, -1)
        self.assertNotEqual(guard, -1)
        self.assertNotEqual(first_delete, -1)
        self.assertLess(shred, first_delete)
        self.assertLess(guard, first_delete)

    def test_the_citation_guard_reads_wider_than_the_columns_it_writes(self):
        """F8, second part. A narrow OPENJSON declaration TRUNCATES an
        over-length value, so the guard measures a string the caller never
        sent and the real length is discovered later by a CHECK constraint.
        The file already documents the wider-parameter idiom for
        @IdempotencyKey; the citation shred now follows it."""
        body = self.procedures["usp_SaveOpportunityAnalysisForOwner"]
        self.assertIn("covered_text nvarchar(max) ''$.covered_text''", body)
        self.assertIn("excerpt nvarchar(max) ''$.excerpt''", body)
        self.assertNotIn("covered_text nvarchar(400)", body)
        self.assertNotIn("excerpt nvarchar(800)", body)
        # And the lengths the columns really enforce are what the guard tests.
        self.assertIn(
            "DATALENGTH(citation.covered_text) / 2 NOT BETWEEN 1 AND 200", body
        )
        self.assertIn("DATALENGTH(citation.excerpt) / 2 NOT BETWEEN 1 AND 400", body)

    def test_the_stored_citation_count_is_reconciled_with_the_rows_written(self):
        """F8, third part. CK_opportunity_analysis_statements_citation_pair
        carries a comment promising the screen's three states "cannot drift
        away from the evidence behind them". That needs the stored count to be
        the number of citation ROWS actually written — and the count came from
        one part of the payload while the rows came from another."""
        body = self.procedures["usp_SaveOpportunityAnalysisForOwner"]
        self.assertIn("WHERE result.citation_count <>", body)
        self.assertIn("SELECT COUNT(*) FROM @Citations AS citation", body)

    def test_the_rollback_header_counts_what_the_rollback_removes(self):
        """Independent review finding F12. The lists were right throughout;
        the summary still said thirteen procedures and eight tables after four
        of each had been added."""
        base_header = self.base_rollback.split("SET NOCOUNT ON;")[0]
        os3_header = self.os3_rollback.split("SET NOCOUNT ON;")[0]
        self.assertIn("thirteen Opportunity", base_header)
        self.assertIn("Slate procedures", base_header)
        self.assertIn("eight tables", base_header)
        normalized_os3_header = " ".join(os3_header.split())
        self.assertIn("four OS-3 procedures", normalized_os3_header)
        self.assertIn("four OS-3 tables", normalized_os3_header)
        procedures = set(re.findall(r"N'(usp_\w+)'", self.rollback))
        tables = set(re.findall(r"N'(dbo\.opportunity_\w+)'", self.rollback))
        self.assertEqual(len(procedures), 17)
        self.assertEqual(len(tables), 12)

    def test_the_verifier_no_aggregate_guard_matches_the_concept_not_four_names(self):
        """Independent review finding F13. The guard matched `overall_score`,
        `match_score`, `match_percentage` and `recommendation` exactly, so
        `alignment_rating`, `fit_index` or `confidence` would have passed the
        one check whose entire subject is "no aggregate verdict about a
        person"."""
        verify = VERIFY.read_text(encoding="utf-8")
        for concept in (
            "%score%",
            "%rating%",
            "%ranking%",
            "%percentile%",
            "%fit_index%",
            "%confidence%",
            "%likelihood%",
            "%probability%",
            "%verdict%",
        ):
            with self.subTest(concept=concept):
                self.assertIn(f"LIKE N'{concept}'", verify)
        # And no procedure body trips it, which is what makes it usable.
        for name in PROCEDURE_NAMES:
            lowered = self.procedures[name].lower()
            for word in (
                "score",
                "rating",
                "ranking",
                "percentile",
                "fit_index",
                "confidence",
                "likelihood",
                "probability",
                "verdict",
            ):
                with self.subTest(procedure=name, word=word):
                    self.assertNotIn(word, lowered)

    def test_the_verifier_does_not_capture_a_four_result_set_procedure(self):
        """Independent review finding F13. `INSERT @Table EXEC` of
        usp_GetOpportunityAnalysisForOwner into one nine-column table variable
        can only succeed when the procedure returns NO result set — which is
        what happens for an owner with no requirement set. It proved nothing,
        and it became error 213 the moment the fixture changed."""
        verify = VERIFY.read_text(encoding="utf-8")
        self.assertNotIn(
            "INSERT @AnalysisReadResult\n    EXEC dbo.usp_GetOpportunityAnalysisForOwner",
            verify,
        )
        # Isolation is asserted on the tables, which no fixture shape can make
        # vacuous, and the read procedure gains a positive path.
        self.assertIn("Owner B owns alignment rows they never created.", verify)
        self.assertIn(
            "EXEC dbo.usp_GetOpportunityAnalysisForOwner @UserKey = @UserKeyA;", verify
        )
        self.assertIn(
            "Owner A has no readable alignment analysis at its current version.",
            verify,
        )

    def test_every_new_table_declares_its_composite_candidate_key_up_front(self):
        """The 2026-08-04 gate's defect 1 from the round before: a table
        another table will reference needs UNIQUE (id, owner_profile_id)
        DECLARED, or the referencing foreign key cannot be created at all."""
        for table, key in (
            ("opportunity_analyses", "UQ_opportunity_analyses_id_owner"),
            (
                "opportunity_analysis_statements",
                "UQ_opportunity_analysis_statements_id_owner",
            ),
            (
                "opportunity_analysis_citations",
                "UQ_opportunity_analysis_citations_id_owner",
            ),
            ("opportunity_responses", "UQ_opportunity_responses_id_owner"),
        ):
            with self.subTest(table=table):
                self.assertIn(f"CONSTRAINT {key}", self.forward)

    def test_the_new_child_rows_are_removed_by_purge_delete_and_re_read(self):
        """Four procedures had to learn about them, and all four must have."""
        for name in (
            "usp_PurgeExpiredOpportunityWorkingData",
            "usp_DeleteOpportunityWorkingSessionForOwner",
            "usp_SaveOpportunityRequirementProposalForOwner",
        ):
            body = self.procedures[name]
            with self.subTest(procedure=name):
                for table in (
                    "dbo.opportunity_analysis_citations",
                    "dbo.opportunity_analysis_statements",
                    "dbo.opportunity_analyses",
                    "dbo.opportunity_responses",
                ):
                    self.assertIn(table, body)
        # A statement correction takes the stale analysis and spares the
        # member's own response.
        correction = self.procedures[
            "usp_CorrectOpportunityRequirementStatementForOwner"
        ]
        self.assertIn("dbo.opportunity_analyses", correction)
        self.assertNotIn("DELETE response_record", correction)

    def test_the_migration_header_states_what_it_assumes_and_upgrades_from(self):
        header = self.os3_forward.split("SET NOCOUNT ON;")[0]
        self.assertIn("Immutable follow-on", header)
        self.assertIn("PS-OPPSLATE-001 OS-1/OS-2", header)
        self.assertIn("fails before the first mutation", header)
        self.assertIn("never updates", header)

    def test_the_ledger_description_fits_the_column_it_is_written_into(self):
        """dbo.schema_migrations.description is nvarchar(500), and an
        over-long value aborts the whole migration on its final statement."""
        match = re.search(
            r"VALUES \(N'PS-OPPSLATE-002', N'((?:''|[^'])*)'",
            self.os3_forward,
        )
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match.group(1).replace("''", "'")), 500)

    def test_the_migration_is_proposed_and_not_wired_into_the_apply_script(self):
        """Slice OS-1 ships the migration as proposed/ and applies it
        nowhere. Registering it with the apply script is a separate,
        explicitly authorized operational step."""
        self.assertIn("proposed", str(FORWARD))
        script_source = (ROOT / "scripts" / "apply_sql_migrations.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("PS-OPPSLATE-001", script_source)


class OpportunitySlateOs4AdditiveChainTests(unittest.TestCase):
    """PS-OPPSLATE-003 (OS-4) as a NEW additive migration over the applied
    001+002 baseline - exactly how the OS-3 delta became PS-OPPSLATE-002
    rather than an in-place edit of PS-OPPSLATE-001. A prior branch
    (work/2026-08-04-opportunity-slate-os4) repeated the in-place-edit
    defect for OS-4; these tests hold the additive re-cut in place, the same
    way this file already holds PS-OPPSLATE-002's additive shape in place,
    without needing a database.
    """

    @classmethod
    def setUpClass(cls):
        cls.forward_003 = FORWARD_003.read_text(encoding="utf-8")
        cls.rollback_003 = ROLLBACK_003.read_text(encoding="utf-8")
        cls.verification_003 = VERIFY_003.read_text(encoding="utf-8")
        cls.base_forward = BASE_FORWARD.read_text(encoding="utf-8")
        cls.base_rollback = BASE_ROLLBACK.read_text(encoding="utf-8")
        cls.forward_002 = FORWARD.read_text(encoding="utf-8")
        cls.rollback_002 = ROLLBACK.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_forward_rollback_and_verification_exist(self):
        for path in (FORWARD_003, ROLLBACK_003, VERIFY_003):
            with self.subTest(path=path):
                self.assertTrue(path.exists())

    def test_registered_after_002_and_requires_both(self):
        ids = [entry["id"] for entry in self.registry["migrations"]]
        self.assertIn("PS-OPPSLATE-002", ids)
        self.assertIn("PS-OPPSLATE-003", ids)
        self.assertLess(
            ids.index("PS-OPPSLATE-002"), ids.index("PS-OPPSLATE-003")
        )
        entry = next(
            item
            for item in self.registry["migrations"]
            if item["id"] == "PS-OPPSLATE-003"
        )
        self.assertEqual(
            set(entry["requires"]), {"PS-OPPSLATE-001", "PS-OPPSLATE-002"}
        )
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/proposed/PS-OPPSLATE-003_opportunity_slate_os4.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/proposed/PS-OPPSLATE-003_opportunity_slate_os4_rollback.sql",
        )

    def test_registry_entry_records_the_owner_gate_proof(self):
        """PS-OPPSLATE-003 carries the owner's disposable-database gate
        proof: run against a throwaway ps-oppslate-os4-gate-* database,
        never a real one, with the digest matching the forward file on
        disk so a later edit to the gated bytes fails here as well as in
        the registry check."""
        from scripts.govern_sql_migrations import executable_sha256

        entry = next(
            item
            for item in self.registry["migrations"]
            if item["id"] == "PS-OPPSLATE-003"
        )
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual("Pete", gate["operator"])
        self.assertRegex(
            gate["gate_database"], r"^ps-oppslate-os4-gate-\d{12}$"
        )
        self.assertEqual("peerslate", gate["gate_server"])
        self.assertEqual(
            executable_sha256(FORWARD_003), gate["executable_sha256"]
        )
        self.assertIn("verified = 1", gate["verification"])
        # The gate rehearsed the full transitive chain, ending on the
        # direct prerequisite, so every declared requirement was present.
        for required in entry["requires"]:
            self.assertIn(required, gate["prerequisites"])
        self.assertEqual("PS-OPPSLATE-002", gate["prerequisites"][-1])

    def test_no_aggregate_verdict_concept_anywhere(self):
        for sql, label in (
            (self.forward_003, "forward migration"),
            (self.rollback_003, "rollback"),
            (self.verification_003, "verifier"),
        ):
            for forbidden in FORBIDDEN_VERDICT_IDENTIFIERS:
                with self.subTest(file=label, identifier=forbidden):
                    if label == "verifier" and forbidden in (
                        "overall_score",
                        "match_score",
                        "match_percentage",
                    ):
                        # Section 0's procedure-body concept grep and the
                        # forbidden-column check both name these
                        # deliberately, as the patterns they refuse to find
                        # in a definition - exactly like PS-OPPSLATE-002's
                        # own verifier.
                        continue
                    self.assertNotIn(forbidden, sql)

    def test_creates_every_os4_table_and_procedure(self):
        for table in OS4_TABLE_NAMES:
            with self.subTest(table=table):
                self.assertIn(
                    f"IF OBJECT_ID(N'{table}', N'U') IS NULL", self.forward_003
                )
        for name in OS4_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertIn(
                    f"CREATE OR ALTER PROCEDURE dbo.{name}", self.forward_003
                )

    def test_the_currency_read_prices_only_the_kind_it_can_resolve(self):
        """Independent review finding F6 (OS-4 checkpoint,
        work/2026-08-04-opportunity-slate-os4, carried into this additive
        re-cut). opportunity_saved_evidence permits `moment` for handoff
        section 17-Q2, but the currency read that decides "Inputs changed"
        prices knowledge_items only. Without an explicit kind predicate a
        Moment citation would resolve to current_version = NULL forever, with
        no member action able to clear it.

        Both halves of the guard are asserted together so they cannot drift
        apart: the SQL predicate that actually restricts the join, and the
        application-side constant the service layer reads the same fact
        from.
        """
        procedures = procedure_batches(self.forward_003)
        read = procedures["usp_GetOpportunitySavedSlateForOwner"]
        self.assertIn("pinned.evidence_kind = N''knowledge_item''", read)
        self.assertIn("pinned.evidence_kind,", read)
        from services.opportunity_slate_service import (
            SAVED_EVIDENCE_CURRENCY_KINDS,
        )

        self.assertEqual(SAVED_EVIDENCE_CURRENCY_KINDS, frozenset({"knowledge_item"}))

    def test_revises_no_existing_procedure(self):
        """Unlike PS-OPPSLATE-002 (which had to revise four OS-2 procedures
        to remove the new child rows it added), the OS-4 delta touches none
        of them - a saved slate is a COPY of the owner's own rows rather
        than a pin on the ephemeral ones, so no purge or delete needs
        conditional retention logic. See the forward file's own header."""
        for name in OS1_PROCEDURE_NAMES + OS2_PROCEDURE_NAMES + OS3_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertNotIn(
                    f"CREATE OR ALTER PROCEDURE dbo.{name}", self.forward_003
                )

    def test_migration_requires_its_dependency_guards(self):
        self.assertIn("dbo.schema_migrations', N'U') IS NULL", self.forward_003)
        self.assertIn("migration_id = N'PS-OPPSLATE-001'", self.forward_003)
        self.assertIn("migration_id = N'PS-OPPSLATE-002'", self.forward_003)
        self.assertIn(
            "does not match the required OS-3 object baseline", self.forward_003
        )
        self.assertIn("partial OS-4 schema exists", self.forward_003)

    def test_partial_shape_guard_admits_only_zero_or_all_new_objects(self):
        match = re.search(
            r"IF @ExistingOs4ObjectCount NOT IN \((\d+), (\d+)\)",
            self.forward_003,
        )
        self.assertIsNotNone(match)
        self.assertEqual((match.group(1), match.group(2)), ("0", "7"))

    def test_ledger_only_ever_inserted(self):
        """No UPDATE against dbo.schema_migrations anywhere in the file, so
        the 001 and 002 ledger rows this migration reads (UPDLOCK/HOLDLOCK,
        to prove they are applied) can never be the target of a write here
        - only its own row is ever inserted."""
        self.assertNotIn("UPDATE dbo.schema_migrations", self.forward_003)
        self.assertEqual(
            self.forward_003.count("INSERT dbo.schema_migrations"), 1
        )
        self.assertIn("N'PS-OPPSLATE-003'", self.forward_003)

    def test_procedures_are_labeled_with_a_definition_hash(self):
        self.assertIn("PS_OPPSLATE_003_DEFINITION_HASH", self.forward_003)
        for name in OS4_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertIn(f"(N'{name}')", self.forward_003)

    def test_every_procedure_resolves_user_key_and_never_accepts_owner_profile_id(
        self,
    ):
        procedures = procedure_batches(self.forward_003)
        self.assertEqual(set(procedures), set(OS4_PROCEDURE_NAMES))
        for name, body in procedures.items():
            with self.subTest(procedure=name):
                self.assertIn("@UserKey nvarchar(300)", body)
                self.assertNotIn("@OwnerProfileId", body)
                self.assertIn("app_user.user_key = @UserKey", body)
                self.assertIn("owner_profile_id = @ProfileId", body)

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def test_rollback_refuses_on_data_later_migration_and_drift(self):
        for phrase in (
            "opportunity_slates contains member records",
            "opportunity_saved_results contains member records",
            "opportunity_saved_qualifications contains member records",
            "opportunity_saved_evidence contains member records",
            "a migration later than PS-OPPSLATE-003 is present",
            "a protected OS-4 procedure changed after PS-OPPSLATE-003",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.rollback_003)

    def test_rollback_checks_data_children_before_parents(self):
        """Same ordering discipline PS-OPPSLATE-002's rollback uses: an
        operator hears about the innermost record first."""
        ordered = (
            "opportunity_saved_evidence contains member records",
            "opportunity_saved_qualifications contains member records",
            "opportunity_saved_results contains member records",
            "opportunity_slates contains member records",
        )
        positions = [self.rollback_003.index(phrase) for phrase in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_rollback_deletes_only_its_own_ledger_row(self):
        self.assertEqual(
            self.rollback_003.count("DELETE dbo.schema_migrations"), 1
        )
        self.assertIn(
            "DELETE dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-003'",
            self.rollback_003,
        )
        self.assertNotIn("UPDATE dbo.schema_migrations", self.rollback_003)
        # The only ledger row this file ever names as a DELETE/UPDATE target
        # is its own; PS-OPPSLATE-001/002 are named only in prose (the
        # header, and the drift/ordering comments) or inside a read-only
        # UPDLOCK/HOLDLOCK guard in the forward file, never here as a target.
        self.assertNotIn("migration_id=N'PS-OPPSLATE-001'", self.rollback_003)
        self.assertNotIn("migration_id=N'PS-OPPSLATE-002'", self.rollback_003)

    def test_rollback_drops_only_what_003_created(self):
        for table in OS4_TABLE_NAMES:
            with self.subTest(table=table):
                self.assertIn(f"DROP TABLE {table};", self.rollback_003)
        for name in OS4_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertIn(f"DROP PROCEDURE dbo.{name};", self.rollback_003)
        # Never a DROP against a 001/002-owned object.
        for name in OS1_PROCEDURE_NAMES + OS2_PROCEDURE_NAMES + OS3_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertNotIn(f"DROP PROCEDURE dbo.{name};", self.rollback_003)
        for table in TABLE_NAMES:
            with self.subTest(table=table):
                self.assertNotIn(f"DROP TABLE {table};", self.rollback_003)

    def test_rollback_restores_no_prior_procedure_definition(self):
        """PS-OPPSLATE-002's rollback has to reinstate four OS-2 procedure
        bodies OS-3 changed. PS-OPPSLATE-003's forward file revises none, so
        its rollback has nothing to restore - only DROPs."""
        for name in OS1_PROCEDURE_NAMES + OS2_PROCEDURE_NAMES + OS3_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertNotIn(
                    f"CREATE OR ALTER PROCEDURE dbo.{name}", self.rollback_003
                )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def test_verifier_registration_check_targets_003(self):
        self.assertIn("migration_id = N'PS-OPPSLATE-003'", self.verification_003)
        self.assertIn("is not registered", self.verification_003)

    def test_verifier_covers_all_twenty_procedures(self):
        for name in (
            OS1_PROCEDURE_NAMES
            + OS2_PROCEDURE_NAMES
            + OS3_PROCEDURE_NAMES
            + OS4_PROCEDURE_NAMES
        ):
            with self.subTest(procedure=name):
                self.assertIn(f"(N'{name}')", self.verification_003)

    def test_verifier_forbidden_column_check_covers_every_table(self):
        """Recorded review finding against PS-OPPSLATE-002's own verifier:
        its structural column check covered only the eight OS-1/OS-2
        tables, missing every OS-3 table entirely. PS-OPPSLATE-003 extends
        coverage to all twelve OS-1/OS-2/OS-3 tables plus its own four."""
        for table in TABLE_NAMES + OS4_TABLE_NAMES:
            with self.subTest(table=table):
                self.assertIn(f"OBJECT_ID(N'{table}')", self.verification_003)

    def test_verifier_forbidden_column_check_is_pattern_based(self):
        """Same finding, second half: PS-OPPSLATE-002's own verifier used a
        FIXED four-name list for the column check (unlike its own
        concept-based procedure-body check, fixed under finding F13).
        PS-OPPSLATE-003 uses a LIKE pattern instead, so it cannot be walked
        around by an unlisted prefix or suffix."""
        self.assertNotIn(
            "name IN (N'overall_score', N'match_score', N'match_percentage', "
            "N'recommendation')",
            self.verification_003,
        )
        self.assertIn("name LIKE N'%score%'", self.verification_003)
        self.assertIn("name LIKE N'%verdict%'", self.verification_003)

    def test_verifier_is_two_owners_forged_key_single_outer_rollback(self):
        self.assertEqual(
            self.verification_003.count("BEGIN TRANSACTION"), 1
        )
        self.assertEqual(
            self.verification_003.count("ROLLBACK TRANSACTION"), 2
        )
        self.assertNotIn("COMMIT TRANSACTION", self.verification_003)
        self.assertIn("@ForgedUserKey", self.verification_003)
        self.assertIn("@ProfileIdA", self.verification_003)
        self.assertIn("@ProfileIdB", self.verification_003)

    def test_verifier_exercises_save_lifecycle_isolation_and_idempotency(self):
        for phrase in (
            "usp_SaveOpportunitySlateForOwner",
            "usp_GetOpportunitySavedSlateForOwner",
            "usp_DeleteOpportunitySavedSlateForOwner",
            "outcome = N'existing'",
            "A malformed input fingerprint was not refused",
            "A refused slate delete removed part of the slate",
            "The purge destroyed a saved slate it does not own",
            "A statement correction destroyed the member''s saved slate",
            "Deleting a saved slate left rows behind",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.verification_003)

    def test_verifier_never_ends_in_a_committed_state(self):
        tail = self.verification_003[
            self.verification_003.rindex("ROLLBACK TRANSACTION;") :
        ]
        self.assertNotIn("COMMIT TRANSACTION", tail)

    # ------------------------------------------------------------------
    # Cross-file discipline
    # ------------------------------------------------------------------

    def test_error_numbers_are_unique_across_all_three_migrations(self):
        """Preflight/rollback THROW numbers for PS-OPPSLATE-001,
        PS-OPPSLATE-002 and PS-OPPSLATE-003 must never collide, so an
        operator reading a raised error number can trace it to exactly one
        migration file."""

        def numbers(sql):
            return re.findall(r"THROW (\d+),", sql)

        files = {
            "PS-OPPSLATE-001 forward": self.base_forward,
            "PS-OPPSLATE-001 rollback": self.base_rollback,
            "PS-OPPSLATE-002 forward": self.forward_002,
            "PS-OPPSLATE-002 rollback": self.rollback_002,
            "PS-OPPSLATE-003 forward": self.forward_003,
            "PS-OPPSLATE-003 rollback": self.rollback_003,
        }
        seen = {}
        for label, sql in files.items():
            file_numbers = numbers(sql)
            self.assertEqual(
                len(file_numbers),
                len(set(file_numbers)),
                f"{label} reuses one of its own error numbers",
            )
            for number in file_numbers:
                self.assertNotIn(
                    number,
                    seen,
                    f"error number {number} used by both {seen.get(number)!r} "
                    f"and {label!r}",
                )
                seen[number] = label

    def test_the_migration_header_credits_the_source_checkpoint(self):
        header = self.forward_003.split("SET NOCOUNT ON;")[0]
        self.assertIn("Immutable follow-on", header)
        self.assertIn("PS-OPPSLATE-001", header)
        self.assertIn("PS-OPPSLATE-002", header)
        self.assertIn("additive", header)

    def test_the_ledger_description_fits_the_column_it_is_written_into(self):
        """dbo.schema_migrations.description is nvarchar(500), and an
        over-long value aborts the whole migration on its final
        statement."""
        match = re.search(
            r"VALUES \(N'PS-OPPSLATE-003', N'((?:''|[^'])*)'",
            self.forward_003,
        )
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match.group(1).replace("''", "'")), 500)

    def test_the_migration_is_proposed_and_not_wired_into_the_apply_script(self):
        self.assertIn("proposed", str(FORWARD_003))
        script_source = (ROOT / "scripts" / "apply_sql_migrations.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("PS-OPPSLATE-003", script_source)

    def test_original_001_and_002_files_are_untouched_by_this_chain(self):
        """Applied migrations are immutable. This suite must never assert
        anything that requires editing PS-OPPSLATE-001 or PS-OPPSLATE-002,
        so their own byte-for-byte content stays exactly what production
        applied."""
        self.assertNotIn("PS-OPPSLATE-003", self.base_forward)
        self.assertNotIn("PS-OPPSLATE-003", self.base_rollback)
        self.assertNotIn("PS-OPPSLATE-003", self.forward_002)
        self.assertNotIn("PS-OPPSLATE-003", self.rollback_002)


@unittest.skipUnless(
    os.getenv("PS_OPPSLATE_SQL_GATE") == "1",
    "requires the isolated PS-OPPSLATE-002 SQL gate database",
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
        self.execute_script(BASE_FORWARD)
        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-OPPSLATE-002'"
            ),
            1,
        )

        self.execute_script(ROLLBACK)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-OPPSLATE-002'"
            ),
            0,
        )
        self.assertIsNotNone(
            self.scalar(
                "SELECT OBJECT_ID(N'dbo.usp_GetOpportunityWorkingSessionForOwner', N'P')"
            )
        )

        self.execute_script(FORWARD)
        self.execute_script(VERIFY)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM dbo.schema_migrations "
                "WHERE migration_id = N'PS-OPPSLATE-002'"
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
