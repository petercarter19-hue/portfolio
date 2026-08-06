"""Static contract tests for PS-WORKSHOP-002 (leg 9: gated in-place
knowledge backlog confirmation).

Mirrors tests/test_opportunity_slate_migration.py's idiom: these assert the
shape of the proposed SQL without needing a database, so the migration's
guards, the structural exclusion of suggested/archived rows, the byte-exact
rollback restoration, and the registry's recorded gate proof are held in place by
the ordinary test run. PS-WORKSHOP-002 carries the recorded owner proof from
its disposable-database gate and still ships nowhere until the separately
governed production schema apply.
"""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"

BASE_FORWARD = MIGRATIONS / "PS-WORKSHOP-001_knowledge_items.sql"
BASE_ROLLBACK = MIGRATIONS / "PS-WORKSHOP-001_knowledge_items_rollback.sql"
FORWARD = MIGRATIONS / "PS-WORKSHOP-002_knowledge_confirmation.sql"
ROLLBACK = MIGRATIONS / "PS-WORKSHOP-002_knowledge_confirmation_rollback.sql"
VERIFY = VERIFICATION / "PS-WORKSHOP-002_owner_isolation_verify.sql"
REGISTRY_PATH = ROOT / "SQL FIles" / "Migrations" / "registry.json"

NEW_PROCEDURE = "usp_ConfirmAuthoredKnowledgeBacklogForOwner"
REVISED_PROCEDURE = "usp_ArchiveKnowledgeItemForOwner"
UNCHANGED_W1_PROCEDURES = (
    "usp_ListKnowledgeItemsForOwner",
    "usp_GetKnowledgeItemForOwner",
    "usp_SaveKnowledgeItemForOwner",
    "usp_UpdateKnowledgeItemForOwner",
    "usp_RestoreKnowledgeItemForOwner",
    "usp_DeleteKnowledgeItemForOwner",
)


def procedure_batches(sql):
    """Map each CREATE OR ALTER PROCEDURE dynamic-SQL batch to its name.

    Same idiom as tests/test_workshop_migration.py and
    tests/test_opportunity_slate_migration.py.
    """
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


def migration_wrapper(sql):
    """The migration's own guard/fingerprint batch, procedure bodies removed."""
    return re.sub(r"EXEC\(N'(?:''|[^'])*'\);", "", sql, flags=re.DOTALL)


class WorkshopConfirmationMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_forward = BASE_FORWARD.read_text(encoding="utf-8")
        cls.base_rollback = BASE_ROLLBACK.read_text(encoding="utf-8")
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.base_procedures = procedure_batches(cls.base_forward)
        cls.procedures = procedure_batches(cls.forward)
        cls.rollback_procedures = procedure_batches(cls.rollback)

    # ------------------------------------------------------------------
    # File presence and batch shape.
    # ------------------------------------------------------------------

    def test_forward_rollback_and_verification_exist(self):
        self.assertTrue(FORWARD.exists())
        self.assertTrue(ROLLBACK.exists())
        self.assertTrue(VERIFY.exists())

    def test_sql_block_comment_delimiters_are_balanced(self):
        """A glob-like ``/*`` inside a SQL block comment is still nested SQL.

        The first disposable gate caught this in the migration header before
        any PS-WORKSHOP-002 SQL executed. Pin the raw delimiter balance so a
        prose-only header edit cannot make the migration unparsable again.
        """
        for label, source in (
            ("forward", self.forward),
            ("rollback", self.rollback),
            ("verification", self.verification),
        ):
            with self.subTest(file=label):
                self.assertEqual(source.count("/*"), source.count("*/"))

    def test_forward_creates_exactly_one_new_procedure_and_revises_exactly_one(self):
        self.assertEqual(set(self.procedures), {NEW_PROCEDURE, REVISED_PROCEDURE})
        self.assertEqual(self.forward.count("CREATE OR ALTER PROCEDURE"), 2)

    def test_forward_never_touches_the_five_unrevised_procedures(self):
        for name in UNCHANGED_W1_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertNotIn(f"CREATE OR ALTER PROCEDURE dbo.{name}", self.forward)

    def test_migration_is_one_guarded_transactional_batch(self):
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
            self.assertIn(value, self.forward)
        self.assertNotIn("\nGO", self.forward)
        self.assertNotIn("\nGO", self.rollback)

    def test_no_applied_ps_workshop_001_bytes_were_touched(self):
        """CONSTRAINT: an applied migration's bytes never change. This file
        must not itself edit PS-WORKSHOP-001's forward or rollback file."""
        # This test's own existence guards the constraint procedurally: it
        # only reads PS-WORKSHOP-001's files, and every other test in this
        # module reads only the PS-WORKSHOP-002 files. Recorded as an
        # explicit assertion of the base file's exact procedure count, so a
        # future accidental edit to PS-WORKSHOP-001 that changed its shape
        # would also be caught here.
        self.assertEqual(len(self.base_procedures), 7)
        self.assertEqual(
            set(self.base_procedures),
            set(UNCHANGED_W1_PROCEDURES) | {REVISED_PROCEDURE},
        )

    # ------------------------------------------------------------------
    # Guards: missing, older, and drifted baseline.
    # ------------------------------------------------------------------

    def test_migration_requires_the_ps_workshop_001_baseline(self):
        for value in (
            "dbo.schema_migrations",
            "migration_id = N'PS-WORKSHOP-001'",
            "dbo.knowledge_items",
            "dbo.knowledge_item_versions",
            "dbo.knowledge_item_save_requests",
        ):
            self.assertIn(value, self.forward)
        for name in UNCHANGED_W1_PROCEDURES + (REVISED_PROCEDURE,):
            with self.subTest(procedure=name):
                self.assertIn(f"N'dbo.{name}', N'P'", self.forward)

    def test_migration_requires_the_confirmation_and_archive_constraints(self):
        for value in (
            "CK_knowledge_items_confirmation_state",
            "CK_knowledge_items_archive_pair",
            "CK_knowledge_items_status",
        ):
            self.assertIn(value, self.forward)

    def test_migration_refuses_a_drifted_baseline_by_hash(self):
        wrapper = migration_wrapper(self.forward)
        for value in (
            "PS_WORKSHOP_001_DEFINITION_HASH",
            "HASHBYTES",
            "OBJECT_DEFINITION",
            "SHA2_256",
            "sys.extended_properties",
        ):
            self.assertIn(value, wrapper)

    def _baseline_procedure_names(self):
        """The exact membership of @BaselineProcedures (the W1 drift-guard
        set), extracted precisely rather than merely grepped for -- the
        revised procedure's name appears elsewhere in the file too (the
        required-object check, the fingerprint block), so a plain
        ``assertIn`` cannot tell "checked for drift" from "mentioned"."""
        match = re.search(
            r"INSERT @BaselineProcedures \(procedure_name\)\s*VALUES\s*"
            r"(?P<values>(?:\s*\(N'\w+'\),?)+);",
            self.forward,
        )
        self.assertIsNotNone(match, "could not locate @BaselineProcedures VALUES list")
        return set(re.findall(r"N'(\w+)'", match.group("values")))

    def test_the_w1_drift_guard_checks_exactly_the_six_unrevised_procedures(self):
        """BLOCKER 1 fix (Opus review, 2026-08-06): the drift guard must
        check the six W1 procedures this migration does not touch, and must
        deliberately EXCLUDE usp_ArchiveKnowledgeItemForOwner -- the one
        procedure this migration itself revises. Including it would compare
        its live (post-revision) definition against the pre-revision
        PS_WORKSHOP_001_DEFINITION_HASH property on every apply after the
        first, throwing THROW 53305 on the governed gate's own no-op
        reapply proof (scripts/govern_sql_migrations.py `gate`, which
        applies the forward script twice)."""
        baseline_names = self._baseline_procedure_names()
        self.assertEqual(baseline_names, set(UNCHANGED_W1_PROCEDURES))
        self.assertNotIn(REVISED_PROCEDURE, baseline_names)

    def test_the_reapply_idempotency_reasoning_is_documented(self):
        for value in (
            "deliberately EXCLUDED",
            "running the forward script",
            "TWICE",
            "is success, not drift",
        ):
            self.assertIn(value, self.forward)

    def test_dependency_guard_error_numbers_precede_any_ddl(self):
        """Every guard THROWs before the first CREATE OR ALTER PROCEDURE."""
        first_procedure_index = self.forward.index("CREATE OR ALTER PROCEDURE")
        for code in ("53300", "53301", "53302", "53303", "53304", "53305"):
            with self.subTest(code=code):
                index = self.forward.index(f"THROW {code},")
                self.assertLess(index, first_procedure_index)

    # ------------------------------------------------------------------
    # The new procedure's contract.
    # ------------------------------------------------------------------

    def test_new_procedure_resolves_user_key_and_never_accepts_owner_profile_id(self):
        batch = self.procedures[NEW_PROCEDURE]
        self.assertIn("@UserKey nvarchar(300)", batch)
        self.assertNotIn("@OwnerProfileId", batch)
        self.assertIn("owner_profile_id = @ProfileId", batch)

    def test_new_procedure_never_assigns_updated_at_utc(self):
        batch = self.procedures[NEW_PROCEDURE]
        self.assertNotIn("updated_at_utc =", batch)
        self.assertNotIn("SET item.updated_at_utc", batch)

    def test_new_procedure_never_touches_versions_wording_or_provenance(self):
        batch = self.procedures[NEW_PROCEDURE]
        for forbidden in (
            "INSERT dbo.knowledge_item_versions",
            "UPDATE dbo.knowledge_item_versions",
            "approved_wording =",
            "original_member_wording =",
            "authored_via =",
            "title =",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, batch)

    def test_new_procedure_set_list_is_exactly_the_confirmation_triple_and_status(self):
        batch = self.procedures[NEW_PROCEDURE]
        set_match = re.search(r"UPDATE item\s+SET(.*?)FROM dbo\.knowledge_items", batch, re.DOTALL)
        self.assertIsNotNone(set_match)
        set_clause = set_match.group(1)
        assigned_columns = set(re.findall(r"item\.(\w+)\s*=", set_clause))
        self.assertEqual(
            assigned_columns,
            {
                "item_status",
                "confirmed_version_number",
                "confirmed_by_user_id",
                "confirmed_at_utc",
            },
        )

    def test_new_procedure_where_clause_structurally_excludes_suggested_and_archived(self):
        batch = self.procedures[NEW_PROCEDURE]
        # The candidate read, the UPDATE itself, and the remaining-count
        # query all assert the same scope; item_status = N'unfinished'
        # alone already excludes N'suggested' and N'archived'
        # (CK_knowledge_items_status / CK_knowledge_items_archive_pair),
        # and archived_at_utc IS NULL (plus visibility = N'private',
        # checked separately below) is present as defense in depth.
        self.assertEqual(
            batch.count("item.item_status = N''unfinished''"), 3,
            "expected exactly three owner-scoped item_status = 'unfinished' "
            "predicates (the candidate read, the UPDATE, and the "
            "remaining-count query)",
        )
        self.assertEqual(batch.count("item.archived_at_utc IS NULL"), 3)
        # No comparison against 'suggested' or the old exclusionary
        # predicate shape anywhere in the executable code (a documentation
        # comment mentioning 'suggested' by name is fine and expected).
        self.assertNotIn("item_status = N''suggested''", batch)
        self.assertNotIn("item_status <> N''archived''", batch)
        self.assertNotIn("IN (N''suggested''", batch)

    def test_new_procedure_asserts_visibility_private_in_every_scope_query(self):
        """Fix 4 (Opus review, 2026-08-06): knowledge_items.visibility is
        hard-locked to 'private' by CK_knowledge_items_visibility today, but
        this procedure asserts it explicitly rather than trusting the
        default -- the same never-trust-the-invariant discipline
        usp_ListKnowledgeItemsForOwner and usp_GetKnowledgeItemForOwner
        already apply to this exact table. Present in the candidate read,
        the UPDATE, and the remaining-count query."""
        batch = self.procedures[NEW_PROCEDURE]
        self.assertEqual(batch.count("AND item.visibility = N''private''"), 3)

    def test_forward_guards_the_visibility_constraint_that_makes_the_predicate_safe(self):
        wrapper = migration_wrapper(self.forward)
        self.assertIn("CK_knowledge_items_visibility", wrapper)

    def test_confirmed_count_is_captured_immediately_after_the_update(self):
        """BLOCKER 3 fix (Opus review, 2026-08-06): DECLARE ... = <value>
        executes as its own assignment and resets @@ROWCOUNT, so
        @ConfirmedCount must be declared WITHOUT an initializer, and
        SET @ConfirmedCount = @@ROWCOUNT must be the very next statement
        after the UPDATE -- no DECLARE-with-initializer (or any other
        statement) may sit between them, or the UPDATE's own row count is
        lost. Matches the repo's own idiom (PS-OPPSLATE-001,
        PS-OPPSLATE-002: declare the counter first, assign @@ROWCOUNT as
        the statement immediately after the row-affecting one)."""
        batch = self.procedures[NEW_PROCEDURE]
        self.assertIn("DECLARE @ConfirmedCount int;", batch)
        self.assertNotIn("DECLARE @ConfirmedCount int = 0;", batch)
        self.assertNotIn("DECLARE @ConfirmedCount int =", batch)

        update_index = batch.index("UPDATE item")
        rowcount_index = batch.index("SET @ConfirmedCount = @@ROWCOUNT;")
        self.assertGreater(rowcount_index, update_index)

        between = batch[update_index:rowcount_index]
        # The UPDATE statement itself is terminated by its own semicolon;
        # nothing may follow it before the @@ROWCOUNT capture.
        after_update_semicolon = between[between.index(";") + 1:]
        self.assertEqual(after_update_semicolon.strip(), "")

    def test_new_procedure_is_bounded_and_deterministic(self):
        batch = self.procedures[NEW_PROCEDURE]
        self.assertIn("@MaxItems int = 200", batch)
        self.assertIn("SET @MaxItems = 200", batch)
        self.assertIn("TOP (@MaxItems)", batch)
        self.assertIn("ORDER BY item.created_at_utc ASC, item.knowledge_item_id ASC", batch)
        self.assertIn("UPDLOCK, HOLDLOCK", batch)

    def test_new_procedure_writes_exactly_one_audit_row_per_item_with_the_distinct_action(self):
        batch = self.procedures[NEW_PROCEDURE]
        self.assertIn("knowledge_item.backlog_confirmed", batch)
        # Never the member-edit action names a defect this migration exists
        # to prevent would have used.
        self.assertNotIn("knowledge_item.updated", batch)
        self.assertNotIn("knowledge_item.saved", batch)
        self.assertIn("WHILE EXISTS (SELECT 1 FROM @Candidates)", batch)
        self.assertEqual(batch.count("EXEC dbo.usp_AppendAuditEvent"), 1)

    def test_new_procedure_materializes_audit_json_before_the_exec_call(self):
        """SQL Server procedure arguments accept a variable here, not a
        CONCAT expression.  The disposable gate caught the direct-expression
        form as a syntax error before this migration ever reached production."""
        batch = self.procedures[NEW_PROCEDURE]
        self.assertIn("DECLARE @AuditMetadataJson nvarchar(max);", batch)
        self.assertIn("SET @AuditMetadataJson = CONCAT(", batch)
        self.assertIn("@MetadataJson = @AuditMetadataJson;", batch)
        self.assertNotIn("@MetadataJson = CONCAT(", batch)

    def test_new_procedure_returns_confirmed_and_remaining_counts(self):
        batch = self.procedures[NEW_PROCEDURE]
        self.assertIn("confirmed_count", batch)
        self.assertIn("remaining_count", batch)
        self.assertIn("SELECT @ConfirmedCount AS confirmed_count, @RemainingCount AS remaining_count;", batch)

    def test_new_procedure_owns_a_transaction(self):
        batch = self.procedures[NEW_PROCEDURE]
        for value in ("BEGIN TRY", "BEGIN TRANSACTION", "COMMIT TRANSACTION", "BEGIN CATCH", "ROLLBACK TRANSACTION", "THROW;"):
            self.assertIn(value, batch)

    # ------------------------------------------------------------------
    # The revised archive procedure.
    # ------------------------------------------------------------------

    def test_archive_revision_refuses_a_suggested_row(self):
        batch = self.procedures[REVISED_PROCEDURE]
        self.assertIn("item.item_status IN (N''unfinished'', N''confirmed'')", batch)
        self.assertNotIn("item.item_status <> N''archived''", batch)

    def test_archive_revision_is_otherwise_byte_identical_to_ps_workshop_001(self):
        """With block comments and blank lines stripped from both, the
        revised body's executable code is identical to the original
        PS-WORKSHOP-001 definition's, line for line, except the one
        deliberately changed WHERE predicate."""

        def code_lines(batch):
            without_comments = re.sub(r"/\*.*?\*/", "", batch, flags=re.DOTALL)
            return [line.strip() for line in without_comments.splitlines() if line.strip()]

        original_code = code_lines(self.base_procedures[REVISED_PROCEDURE])
        revised_code = code_lines(self.procedures[REVISED_PROCEDURE])
        self.assertEqual(len(original_code), len(revised_code))

        differing = [
            index
            for index, (before, after) in enumerate(zip(original_code, revised_code))
            if before != after
        ]
        self.assertEqual(differing, [
            original_code.index("AND item.item_status <> N''archived''")
        ])
        (changed_index,) = differing
        self.assertEqual(
            original_code[changed_index], "AND item.item_status <> N''archived''"
        )
        self.assertEqual(
            revised_code[changed_index],
            "AND item.item_status IN (N''unfinished'', N''confirmed'')",
        )

    # ------------------------------------------------------------------
    # Fingerprinting.
    # ------------------------------------------------------------------

    def test_migration_and_rollback_fingerprint_the_owned_procedures(self):
        for sql in (self.forward, self.rollback):
            self.assertIn("PS_WORKSHOP_002_DEFINITION_HASH", sql)
            self.assertIn("HASHBYTES", sql)
            self.assertIn("OBJECT_DEFINITION", sql)
            self.assertIn("SHA2_256", sql)
        for name in (NEW_PROCEDURE, REVISED_PROCEDURE):
            with self.subTest(procedure=name):
                self.assertIn(f"N'{name}'", self.forward)
                self.assertIn(f"N'{name}'", self.rollback)

    # ------------------------------------------------------------------
    # Rollback.
    # ------------------------------------------------------------------

    def test_rollback_refuses_on_missing_ledger_later_migration_and_drift(self):
        for value in (
            "Rollback refused",
            "the migration ledger is missing",
            "a migration later than PS-WORKSHOP-002 is present",
            "a protected PS-WORKSHOP-002 procedure changed after it applied",
            "UPDLOCK, HOLDLOCK",
        ):
            self.assertIn(value, self.rollback)

    def test_rollback_drops_the_new_procedure_and_restores_the_revised_one(self):
        self.assertIn(f"DROP PROCEDURE dbo.{NEW_PROCEDURE}", self.rollback)
        self.assertEqual(set(self.rollback_procedures), {REVISED_PROCEDURE})
        self.assertEqual(self.rollback.count("CREATE OR ALTER PROCEDURE"), 1)

    def test_rollback_removes_only_its_own_extended_property_before_restoring(self):
        self.assertIn("sys.sp_dropextendedproperty", self.rollback)
        self.assertIn("PS_WORKSHOP_002_DEFINITION_HASH", self.rollback)

    def test_rollback_restores_the_exact_ps_workshop_001_archive_definition(self):
        """Byte-exact proof: the rollback's restored CREATE OR ALTER batch
        is character-for-character identical to PS-WORKSHOP-001's original
        definition of usp_ArchiveKnowledgeItemForOwner."""
        original = self.base_procedures[REVISED_PROCEDURE]
        restored = self.rollback_procedures[REVISED_PROCEDURE]
        self.assertEqual(original, restored)

    def test_rollback_never_touches_knowledge_items_or_versions_data(self):
        """CONSTRAINT: rollback must never un-confirm a legitimately
        confirmed row. Proven structurally: no UPDATE or DELETE against
        dbo.knowledge_items or dbo.knowledge_item_versions appears anywhere
        in this file (the restored procedure body's own UPDATE, used only
        when a MEMBER later calls Archive again, does not count -- it is
        inside a CREATE OR ALTER PROCEDURE definition string, never
        executed by the rollback script itself)."""
        outside_procedure_bodies = migration_wrapper(self.rollback)
        for forbidden in (
            "UPDATE dbo.knowledge_items",
            "DELETE dbo.knowledge_items",
            "UPDATE dbo.knowledge_item_versions",
            "DELETE dbo.knowledge_item_versions",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, outside_procedure_bodies)

    def test_rollback_documents_that_confirmations_are_not_reverted(self):
        for value in (
            "DOES NOT UN-CONFIRM",
            "LEGITIMATE confirmation",
            "standing rule",
        ):
            self.assertIn(value, self.rollback)

    def test_rollback_deletes_only_its_own_ledger_row(self):
        self.assertIn("DELETE dbo.schema_migrations WHERE migration_id = N'PS-WORKSHOP-002'", self.rollback)
        self.assertNotIn("migration_id = N'PS-WORKSHOP-001'", self.rollback)

    # ------------------------------------------------------------------
    # Verifier.
    # ------------------------------------------------------------------

    def test_verifier_has_two_owners_forged_key_canaries_and_outer_rollback(self):
        for value in (
            "@SubjectA",
            "@SubjectB",
            "@ProfileIdA",
            "@ProfileIdB",
            "@UserKeyA",
            "@UserKeyB",
            "usp_UpsertAppUserFromAuth",
            "forged-user-key-does-not-exist",
            "A forged UserKey produced a truthful-looking backlog confirmation result",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_never_ends_in_a_committed_state(self):
        self.assertNotIn("COMMIT TRANSACTION", self.verification)

    def test_verifier_proves_byte_stability_of_content_version_and_updated_at(self):
        for value in (
            "updated_at_utc = @BackdatedAt",
            "current_version_number = 1",
            "approved_wording = N'You led a systems integration effort end to end.'",
            "original_member_wording = N'You led a systems integration effort end to end.'",
            "authored_via = N'typed'",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_proves_byte_stability_for_both_authored_via_values(self):
        """Item 6 (Opus review, 2026-08-06): the original refusal named
        provenance surviving across BOTH authored_via values this migration
        exercises (item1 is N'typed', item2 is N'spoken') -- proving it only
        for item1 leaves the other exactly half-tested."""
        for value in (
            "@Item2BackdatedAt",
            "updated_at_utc = @Item2BackdatedAt",
            "created_at_utc = @Item2BackdatedAt",
            "title = N'Owner A backlog item two'",
            "approved_wording = N'You train and race long distances.'",
            "original_member_wording = N'You train and race long distances.'",
            "authored_via = N'spoken'",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_proves_suggested_confirmed_and_archived_rows_are_untouched(self):
        for value in (
            "@SuggestedRowVersionBefore",
            "@ConfirmedRowVersionBefore",
            "@ArchivedRowVersionBefore",
            "A suggested item was touched by the backlog confirmation",
            "An already-confirmed item was touched by the backlog confirmation",
            "An already-archived item was touched by the backlog confirmation",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_proves_bounded_and_deterministic_order(self):
        for value in (
            "@MaxItems = 1",
            "did not confirm the older eligible item first",
            "confirmed more than @MaxItems items",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_covers_the_archive_restore_fix(self):
        for value in (
            "usp_ArchiveKnowledgeItemForOwner accepted a suggested row",
            "usp_ArchiveKnowledgeItemForOwner refused a genuine unfinished row",
            "usp_RestoreKnowledgeItemForOwner refused a legitimately archived unfinished row",
            "The restored genuine unfinished item was not swept by the next backlog call",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_checks_audit_rows_carry_the_distinct_action(self):
        for value in (
            "action_type = N'knowledge_item.backlog_confirmed'",
            "did not write exactly one distinct-action audit row per confirmed item",
            "was recorded under a member-edit audit action",
            "contains private knowledge item wording",
        ):
            self.assertIn(value, self.verification)

    def test_verifier_states_the_bare_exec_calling_convention(self):
        for value in (
            "cannot be nested",
            "early-return branch",
            "bare EXEC",
        ):
            self.assertIn(value, self.verification)

    # ------------------------------------------------------------------
    # Registry, allowlist, and error-number hygiene.
    # ------------------------------------------------------------------

    def test_registry_entry_records_the_owner_gate_proof(self):
        from scripts.migration_registry import executable_sha256

        document = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        self.assertIn("PS-WORKSHOP-002", entries)
        entry = entries["PS-WORKSHOP-002"]
        self.assertEqual(entry["requires"], ["PS-WORKSHOP-001"])
        gate = entry["gate"]
        self.assertIsNotNone(gate)
        self.assertEqual("Pete", gate["operator"])
        self.assertRegex(
            gate["gate_database"], r"^ps-workshop-002-gate-\d{12}$"
        )
        self.assertEqual("peerslate", gate["gate_server"])
        self.assertEqual(executable_sha256(FORWARD), gate["executable_sha256"])
        self.assertIn("verified = 1", gate["verification"])
        for required in entry["requires"]:
            self.assertIn(required, gate["prerequisites"])
        self.assertEqual("PS-WORKSHOP-001", gate["prerequisites"][-1])
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/proposed/PS-WORKSHOP-002_knowledge_confirmation.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/proposed/PS-WORKSHOP-002_knowledge_confirmation_rollback.sql",
        )

    def test_registry_entries_are_ordered_before_the_ledger_description_limit(self):
        document = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        entries = {entry["id"]: entry for entry in document["migrations"]}
        ids = [entry["id"] for entry in document["migrations"]]
        self.assertLess(ids.index("PS-WORKSHOP-001"), ids.index("PS-WORKSHOP-002"))
        # The description column this ledger row is written into is
        # nvarchar(max) (see PS-PLAT-001), but every existing migration's
        # description stays well under a generous sanity bound so an
        # operator reading dbo.schema_migrations in a query tool never
        # meets a wall of text.
        match = re.search(
            r"N'PS-WORKSHOP-002', N'((?:''|[^'])*)'", self.forward
        )
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match.group(1).replace("''", "'")), 800)

    def test_application_allowlist_registration(self):
        database_source = (ROOT / "services" / "database_service.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(database_source.count(f'"{NEW_PROCEDURE}"'), 1)

    def test_the_knowledge_service_calls_only_the_new_procedure_name(self):
        service_source = (ROOT / "services" / "knowledge_service.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'"{NEW_PROCEDURE}"', service_source)
        self.assertEqual(service_source.count(f'"{NEW_PROCEDURE}"'), 1)

    def test_the_migration_is_proposed_and_not_wired_into_the_apply_script(self):
        self.assertIn("proposed", str(FORWARD))
        script_source = (ROOT / "scripts" / "apply_sql_migrations.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("PS-WORKSHOP-002", script_source)

    def test_error_numbers_are_unique_within_each_file(self):
        def numbers(sql):
            return re.findall(r"THROW (\d+),", sql)

        for label, sql in (
            ("forward", self.forward),
            ("rollback", self.rollback),
            ("verification", self.verification),
        ):
            with self.subTest(file=label):
                file_numbers = numbers(sql)
                self.assertTrue(file_numbers)
                self.assertEqual(len(file_numbers), len(set(file_numbers)))

    def test_migration_owned_guard_numbers_do_not_collide_across_the_three_files(self):
        """Scoped to each file's own wrapper-level guards (procedure bodies
        stripped): usp_ArchiveKnowledgeItemForOwner's revised body is
        byte-identical to PS-WORKSHOP-001's except the one predicate line,
        so it legitimately carries forward the SAME internal THROW 53030
        the original procedure already used for its own required-parameter
        guard, in every file that carries that procedure body. That is not
        a collision between two different guards; it is one unchanged
        guard appearing in the (also unchanged) code that copies it."""

        def numbers(sql):
            return set(re.findall(r"THROW (\d+),", migration_wrapper(sql)))

        forward_numbers = numbers(self.forward)
        rollback_numbers = numbers(self.rollback)
        verify_numbers = numbers(self.verification)
        self.assertEqual(forward_numbers & rollback_numbers, set())
        self.assertEqual(forward_numbers & verify_numbers, set())
        self.assertEqual(rollback_numbers & verify_numbers, set())

    def test_migration_owned_guard_numbers_do_not_collide_with_ps_workshop_001(self):
        def numbers(sql):
            return set(re.findall(r"THROW (\d+),", migration_wrapper(sql)))

        base_numbers = numbers(self.base_forward) | numbers(self.base_rollback)
        new_numbers = numbers(self.forward) | numbers(self.rollback)
        self.assertEqual(base_numbers & new_numbers, set())

    def test_the_carried_procedure_throw_code_is_the_only_repeated_number(self):
        """The one THROW number that DOES legitimately repeat across
        PS-WORKSHOP-001 and PS-WORKSHOP-002 is 53030 -- the unchanged
        required-parameter guard inside the byte-copied
        usp_ArchiveKnowledgeItemForOwner body -- and nothing else."""

        def numbers(sql):
            return set(re.findall(r"THROW (\d+),", sql))

        base_numbers = numbers(self.base_forward) | numbers(self.base_rollback)
        new_numbers = numbers(self.forward) | numbers(self.rollback)
        self.assertEqual(base_numbers & new_numbers, {"53030"})

    def test_the_ordering_of_gate_apply_and_merge_is_stated_in_the_header(self):
        for value in (
            "ORDERING",
            "passed the owner's disposable-",
            "proof branch merges",
            "production apply is",
            "queued on that exact merged SHA",
        ):
            self.assertIn(value, self.forward)

    def test_gate_script_exists_and_targets_this_migration(self):
        gate_script = ROOT / "scripts" / "gate_workshop_002.ps1"
        self.assertTrue(gate_script.exists())
        source = gate_script.read_text(encoding="utf-8")
        self.assertIn("PS-WORKSHOP-002", source)
        self.assertIn("work/workshop-002-gate-proof", source)


# ----------------------------------------------------------------------
# Item 5 (Opus review, 2026-08-06), BLOCKER 2 regression guard: no verifier
# anywhere may capture one of these Workshop write procedures via
# INSERT ... EXEC and then assert it reached a real, audit-writing success
# outcome -- T-SQL cannot nest an INSERT ... EXEC inside the nested
# usp_AppendAuditEvent call those procedures make on their success path
# (Msg 8164). A call captured this way must only ever be asserted against
# an early-return signal (outcome <> 'changed', a zero count, and so on);
# proving a real success requires the bare-EXEC-plus-direct-read idiom
# instead. This scans every file under SQL FIles/Verification/, not only
# this migration's own, so the same regression anywhere else is caught too.
# ----------------------------------------------------------------------

_NESTED_AUDIT_WORKSHOP_PROCEDURES = frozenset(
    {
        "usp_SaveKnowledgeItemForOwner",
        "usp_UpdateKnowledgeItemForOwner",
        "usp_ArchiveKnowledgeItemForOwner",
        "usp_RestoreKnowledgeItemForOwner",
        "usp_DeleteKnowledgeItemForOwner",
        "usp_ConfirmAuthoredKnowledgeBacklogForOwner",
    }
)

_CAPTURED_WORKSHOP_CALL = re.compile(
    r"INSERT\s+@(?P<var>\w+)\s*\n\s*EXEC\s+dbo\.(?P<proc>usp_\w+)\b[^;]*;",
    re.DOTALL,
)


def _forbidden_success_signal(procedure_name, var_name):
    """The fingerprint of blocker 2's exact defect: an INSERT ... EXEC
    capture asserted to have reached a real, mutating success outcome.
    Confirm has no outcome column (it returns confirmed_count/
    remaining_count instead), so a positive confirmed_count is its own
    success signal; every other Workshop write procedure here returns
    outcome, and 'success' is the only value its nested audit call is
    reachable from."""
    if procedure_name == "usp_ConfirmAuthoredKnowledgeBacklogForOwner":
        return re.compile(rf"@{re.escape(var_name)}\b[^;]*confirmed_count\s*=\s*1")
    return re.compile(rf"@{re.escape(var_name)}\b[^;]*outcome\s*=\s*N'success'")


class VerifierBareExecConventionTests(unittest.TestCase):
    """Scans every SQL FIles/Verification/*.sql file, not only
    PS-WORKSHOP-002's own, so this exact class of bug can never silently
    recur anywhere in the suite."""

    def test_no_verifier_captures_a_nested_audit_success_via_insert_exec(self):
        verifier_paths = sorted(VERIFICATION.glob("*.sql"))
        self.assertTrue(verifier_paths, "no verifier files found to scan")
        checked_any = False
        for path in verifier_paths:
            source = path.read_text(encoding="utf-8")
            for match in _CAPTURED_WORKSHOP_CALL.finditer(source):
                var_name, procedure_name = match.group("var"), match.group("proc")
                if procedure_name not in _NESTED_AUDIT_WORKSHOP_PROCEDURES:
                    continue
                checked_any = True
                window = source[match.end() : match.end() + 600]
                forbidden = _forbidden_success_signal(procedure_name, var_name)
                with self.subTest(file=path.name, procedure=procedure_name, var=var_name):
                    self.assertIsNone(
                        forbidden.search(window),
                        f"{path.name} captures {procedure_name} via "
                        f"INSERT @{var_name} ... EXEC and then appears to assert "
                        "it reached a real success/mutation outcome -- T-SQL "
                        "cannot nest INSERT ... EXEC under that procedure's own "
                        "nested usp_AppendAuditEvent call on its success path; "
                        "use a bare EXEC with a direct table read instead.",
                    )
        self.assertTrue(
            checked_any,
            "expected at least one INSERT ... EXEC call to a Workshop write "
            "procedure across the verifier suite (the safe early-return "
            "canaries); found none, which means this test is not exercising "
            "anything",
        )

    def test_this_migrations_verifier_still_exercises_the_safe_capture_pattern(self):
        """A regression test that removed every INSERT ... EXEC entirely
        (over-correcting) would make the test above vacuous for this file.
        Confirms the three early-return captures this file's own header
        documents are still present and still safe."""
        source = VERIFY.read_text(encoding="utf-8")
        matches = list(_CAPTURED_WORKSHOP_CALL.finditer(source))
        procedures_captured = {match.group("proc") for match in matches}
        self.assertEqual(
            procedures_captured,
            {"usp_ConfirmAuthoredKnowledgeBacklogForOwner", "usp_ArchiveKnowledgeItemForOwner"},
        )
        self.assertEqual(len(matches), 4)


if __name__ == "__main__":
    unittest.main()
