"""Static contract tests for PS-OPPSLATE-004, the Opportunity Slate
REPLACEMENT R1 additive migration.

Mirrors tests/test_opportunity_slate_migration.py's own OS-4 additive-chain
class: these assert the shape of the proposed SQL without needing a
database, so the migration's guards, owner scoping, CHECK pins, takeover
hash-stamping, and rollback refusals are held in place by the ordinary test
run. PS-OPPSLATE-004 is additive on top of the applied PS-OPPSLATE-001/002/
003 baseline and is not wired into any apply script. The registry carries
the proof emitted by the 2026-08-12 disposable-database gate; the real
registry loader binds that proof to the exact executable migration digest.

This file is a lane-owned addition (docs/initiatives/PS-OPPORTUNITY-SLATE-002)
and does not modify tests/test_opportunity_slate_migration.py, which stays
exactly as PS-OPPSLATE-001/002/003 left it.
"""

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
REGISTRY_PATH = ROOT / "SQL FIles" / "Migrations" / "registry.json"
EVIDENCE = ROOT / "artifacts" / "2026-08-11-opportunity-slate-v2"

FORWARD = MIGRATIONS / "PS-OPPSLATE-004_opportunity_slate_replacement.sql"
ROLLBACK = MIGRATIONS / "PS-OPPSLATE-004_opportunity_slate_replacement_rollback.sql"
VERIFY = VERIFICATION / "PS-OPPSLATE-004_owner_isolation_verify.sql"

# The three new tables. Two of them (review events, member takes) are shape
# only in R1 — no R1 procedure writes them — per the forward file's own
# header and the delegation brief's "no requirement review" exclusion.
NEW_TABLE_NAMES = (
    "dbo.opportunity_source_identities",
    "dbo.opportunity_requirement_review_events",
    "dbo.opportunity_member_takes",
)

# The two procedures R1 application code actually calls.
NEW_PROCEDURE_NAMES = (
    "usp_SaveOpportunitySourceIdentityForOwner",
    "usp_GetOpportunitySourceIdentityForOwner",
)

# The two PS-OPPSLATE-001 procedures this migration takes over (CREATE OR
# ALTER, hash re-stamped), exactly as PS-OPPSLATE-002 took them over from
# PS-OPPSLATE-001 first.
TAKEOVER_PROCEDURE_NAMES = (
    "usp_PurgeExpiredOpportunityWorkingData",
    "usp_DeleteOpportunityWorkingSessionForOwner",
)

# Every procedure now in the accumulated Opportunity Slate store, R1 and
# earlier slices together — the full set the verifier's generic
# @UserKey/@OwnerProfileId grep must cover.
ALL_ACCUMULATED_PROCEDURE_NAMES = (
    "usp_PurgeExpiredOpportunityWorkingData",
    "usp_GetOpportunityWorkingSessionForOwner",
    "usp_SaveOpportunitySourceForOwner",
    "usp_CorrectOpportunitySourceForOwner",
    "usp_ConfirmOpportunitySourceForOwner",
    "usp_DeleteOpportunityWorkingSessionForOwner",
    "usp_GetOpportunitySourceReviewForOwner",
    "usp_SaveOpportunitySourceReviewForOwner",
    "usp_ResolveOpportunitySourceConcernForOwner",
    "usp_GetOpportunityRequirementsForOwner",
    "usp_SaveOpportunityRequirementProposalForOwner",
    "usp_CorrectOpportunityRequirementStatementForOwner",
    "usp_ConfirmOpportunityRequirementsForOwner",
    "usp_ListOpportunityEvidenceForOwner",
    "usp_GetOpportunityAnalysisForOwner",
    "usp_SaveOpportunityAnalysisForOwner",
    "usp_SaveOpportunityResponseForOwner",
    "usp_GetOpportunitySavedSlateForOwner",
    "usp_SaveOpportunitySlateForOwner",
    "usp_DeleteOpportunitySavedSlateForOwner",
    "usp_SaveOpportunitySourceIdentityForOwner",
    "usp_GetOpportunitySourceIdentityForOwner",
)

# The eight R2-scoped procedures the architecture's section 5.2 sketches
# that this migration deliberately does NOT create. Named here so a future
# accidental addition (or removal of the documented deferral) is caught by
# a change to this list, not silently.
DEFERRED_R2_PROCEDURE_NAMES = (
    "usp_SaveOpportunityRequirementReviewForOwner",
    "usp_ConfirmOpportunityRequirementsForOwnerR",
    "usp_ReviseOpportunityRequirementsForOwner",
    "usp_SaveOpportunityMemberTakeForOwner",
    "usp_ReviewOpportunityMemberResponseForOwner",
    "usp_ContinueOpportunityQualificationForOwner",
    "usp_SaveOpportunityAnalysisForOwnerR",
    "usp_GetOpportunityRoomForOwnerR",
)

_CREATE_PROCEDURE = re.compile(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)")

# Compound, column-name-shaped identifiers — never bare English words —
# exactly like tests/test_opportunity_slate_migration.py's own
# FORBIDDEN_VERDICT_IDENTIFIERS. A bare word check would false-positive on
# this migration's own "STILL NO SCORE. Not one column ... holds an
# aggregate, a percentage, a ranking, a recommendation" header prose, which
# discusses the retired concept in order to refuse it, not to reintroduce it.
_FORBIDDEN_VERDICT_IDENTIFIERS = (
    "overall_score",
    "match_score",
    "match_percentage",
    "fit_score",
    "fit_index",
    "confidence_score",
    "recommendation_score",
    "employer_prediction",
)


def _procedure_body(text, name):
    """The dynamic-SQL body of exactly one ``CREATE OR ALTER PROCEDURE``,
    from its header to the closing ``    ');`` of the EXEC(N'...') block
    that carries it — the exact boundary every procedure in this file
    (and in PS-OPPSLATE-001/002/003) is written with."""
    start_match = re.search(
        r"CREATE OR ALTER PROCEDURE dbo\." + re.escape(name) + r"\b", text
    )
    if start_match is None:
        raise AssertionError(f"{name} is not defined in this file.")
    end = text.index("\n    ');", start_match.start())
    return text[start_match.start() : end]


class OpportunitySlateV2MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.registry_entry = next(
            item
            for item in cls.registry["migrations"]
            if item["id"] == "PS-OPPSLATE-004"
        )

    # ------------------------------------------------------------
    # Files and registration
    # ------------------------------------------------------------

    def test_forward_rollback_and_verification_exist(self):
        for path in (FORWARD, ROLLBACK, VERIFY):
            with self.subTest(path=path):
                self.assertTrue(path.exists())

    def test_registered_after_003_and_requires_all_three_priors(self):
        ids = [entry["id"] for entry in self.registry["migrations"]]
        self.assertIn("PS-OPPSLATE-003", ids)
        self.assertIn("PS-OPPSLATE-004", ids)
        self.assertLess(ids.index("PS-OPPSLATE-003"), ids.index("PS-OPPSLATE-004"))
        self.assertEqual(
            set(self.registry_entry["requires"]),
            {"PS-OPPSLATE-001", "PS-OPPSLATE-002", "PS-OPPSLATE-003"},
        )
        self.assertEqual(
            self.registry_entry["forward"],
            "SQL FIles/Migrations/proposed/PS-OPPSLATE-004_opportunity_slate_replacement.sql",
        )
        self.assertEqual(
            self.registry_entry["rollback"],
            "SQL FIles/Migrations/proposed/PS-OPPSLATE-004_opportunity_slate_replacement_rollback.sql",
        )

    def test_registry_entry_records_the_real_disposable_database_gate(self):
        proof = self.registry_entry["gate"]
        self.assertEqual(
            proof["executable_sha256"],
            "f4752c0e9cf176d26bd4239a5cf13bbc99e7614fa1da7fae6087705d79acb73a",
        )
        self.assertEqual(proof["gate_database"], "ps-oppslate-004-perm-202608121325")
        self.assertEqual(proof["gate_server"], "peerslate")
        self.assertEqual(
            proof["verification"],
            "PS-OPPSLATE-004_owner_isolation_verify.sql returned verified = 1",
        )
        self.assertNotIn(proof["gate_database"], {"peerslate-database", "peerslate-staging"})

    def test_supplemental_rollback_evidence_matches_the_exact_files_and_gate_inventory(self):
        gate = json.loads((EVIDENCE / "PS-OPPSLATE-004-gate.json").read_text(encoding="utf-8"))
        rollback_proof = json.loads(
            (EVIDENCE / "PS-OPPSLATE-004-rollback-proof.json").read_text(encoding="utf-8")
        )
        post_rollback = json.loads(
            (EVIDENCE / "PS-OPPSLATE-004-post-rollback-state.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            set(gate["proof"]["objects"]),
            set(rollback_proof["objects_removed"]),
        )
        self.assertEqual(len(gate["proof"]["objects"]), 42)
        self.assertEqual(len(rollback_proof["objects_removed"]), 42)
        for key in (
            "removed_exactly_matches_gate_objects",
            "ledger_absent",
            "additive_columns_absent",
            "new_procedures_absent",
            "ps_oppslate_004_definition_stamps_absent",
            "restored_ps_oppslate_002_definition_hashes_match",
        ):
            with self.subTest(key=key):
                self.assertIs(post_rollback[key], True)

        self.assertEqual(
            hashlib.sha256(VERIFY.read_bytes()).hexdigest(),
            post_rollback["verifier_sha256_at_gate"],
        )
        self.assertEqual(
            hashlib.sha256(ROLLBACK.read_bytes()).hexdigest(),
            post_rollback["rollback_sha256_at_supplemental_proof"],
        )

    def test_registry_loads_through_the_real_loader(self):
        """End-to-end validation via the actual governance module, not just
        raw JSON — catches a shape the hand-authored JSON checks above
        would miss (e.g. a key load_registry requires that these tests do
        not separately assert)."""
        from scripts.migration_registry import load_registry

        registry = load_registry()
        migration = registry.get("PS-OPPSLATE-004")
        self.assertTrue(migration.is_gated)
        self.assertEqual(
            registry.ids.index(migration.migration_id), migration.position
        )
        self.assertEqual(
            migration.migration_id, registry.ids[migration.position]
        )
        self.assertTrue(
            set(migration.requires).issubset(set(registry.ids[:migration.position]))
        )

    def test_the_migration_is_proposed_and_not_wired_into_the_apply_script(self):
        self.assertIn("proposed", str(FORWARD))
        script_source = (ROOT / "scripts" / "apply_sql_migrations.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("PS-OPPSLATE-004", script_source)

    def test_original_001_002_003_files_are_untouched_by_this_migration(self):
        """Applied migrations are immutable. This suite must never assert
        anything that requires editing PS-OPPSLATE-001/002/003, so their
        own byte-for-byte content stays exactly what was gated before."""
        for prior in ("PS-OPPSLATE-001", "PS-OPPSLATE-002", "PS-OPPSLATE-003"):
            prior_forward = MIGRATIONS / (
                "PS-OPPSLATE-001_opportunity_slate.sql"
                if prior == "PS-OPPSLATE-001"
                else "PS-OPPSLATE-002_opportunity_slate_os3.sql"
                if prior == "PS-OPPSLATE-002"
                else "PS-OPPSLATE-003_opportunity_slate_os4.sql"
            )
            with self.subTest(prior=prior):
                self.assertNotIn(
                    "PS-OPPSLATE-004", prior_forward.read_text(encoding="utf-8")
                )

    # ------------------------------------------------------------
    # Forward: transactional shape and dependency guards
    # ------------------------------------------------------------

    def test_migration_is_one_guarded_transactional_batch(self):
        self.assertIn("SET NOCOUNT ON", self.forward)
        self.assertIn("SET XACT_ABORT ON", self.forward)
        self.assertIn("BEGIN TRY", self.forward)
        self.assertIn("BEGIN TRANSACTION", self.forward)
        self.assertIn("COMMIT TRANSACTION", self.forward)
        self.assertIn("BEGIN CATCH", self.forward)
        self.assertIn("ROLLBACK TRANSACTION", self.forward)
        self.assertIn("THROW;", self.forward)

    def test_migration_requires_its_dependency_guards(self):
        self.assertIn("PS-OPPSLATE-001", self.forward)
        self.assertIn("PS-OPPSLATE-002", self.forward)
        self.assertIn("PS-OPPSLATE-003", self.forward)
        self.assertIn("must be applied before PS-OPPSLATE-004", self.forward)

    def test_unapplied_partial_shape_guard_adopts_no_existing_surface(self):
        self.assertIn("@ExistingOs5ObjectCount", self.forward)
        self.assertIn("@OwnedColumnCount", self.forward)
        self.assertIn("@MigrationAlreadyApplied = 0", self.forward)
        self.assertIn("@ExistingOs5ObjectCount > 0", self.forward)
        self.assertIn("@OwnedColumnCount > 0", self.forward)
        self.assertIn("@OwnedConstraintCount > 0", self.forward)
        self.assertIn("no existing object or column will be adopted", self.forward)
        # Five objects: three tables, two procedures.
        os5_block_match = re.search(
            r"INSERT @Os5Objects.*?;", self.forward, re.DOTALL
        )
        self.assertIsNotNone(os5_block_match)
        block = os5_block_match.group(0)
        for table in NEW_TABLE_NAMES:
            with self.subTest(table=table):
                self.assertIn(table, block)
        for procedure in NEW_PROCEDURE_NAMES:
            with self.subTest(procedure=procedure):
                self.assertIn(procedure, block)

    def test_reapply_and_rollback_require_owned_surface_stamps(self):
        self.assertIn("PS_OPPSLATE_004_OWNED", self.forward)
        self.assertIn("PS_OPPSLATE_004_OWNED", self.rollback)
        for table in NEW_TABLE_NAMES:
            with self.subTest(table=table):
                self.assertIn(table.split(".", 1)[1], self.forward)
        for column in (
            "evidence_snapshot_sha256",
            "confirmed_requirements_ordinal",
            "member_confirmed_ordinal",
        ):
            with self.subTest(column=column):
                self.assertIn(column, self.rollback)
        self.assertIn("table ownership stamp is missing", self.rollback)
        self.assertIn("column ownership stamp is missing", self.rollback)

    # ------------------------------------------------------------
    # New tables
    # ------------------------------------------------------------

    def test_migration_creates_every_new_table_it_owns(self):
        for table in NEW_TABLE_NAMES:
            unqualified = table.split(".", 1)[1]
            with self.subTest(table=table):
                self.assertIn(f"CREATE TABLE dbo.{unqualified}", self.forward)

    def test_every_new_table_declares_its_composite_candidate_key_up_front(self):
        """The 2026-08-03-class gate failure this comment chain warns
        about: a child table referencing (id, owner_profile_id) needs the
        matching UNIQUE on the PARENT declared, and every new table here
        needs its OWN (id, owner_profile_id) unique for whatever the next
        migration references."""
        for name, prefix in (
            ("opportunity_source_identities", "osi"),
            ("opportunity_requirement_review_events", "orre"),
            ("opportunity_member_takes", "omt"),
        ):
            with self.subTest(table=name):
                self.assertIn(
                    f"UQ_opportunity_{name.split('opportunity_', 1)[-1]}_id_owner"
                    if False
                    else f"UQ_{name}_id_owner",
                    self.forward,
                )

    def test_identity_table_is_one_row_per_source_version(self):
        self.assertIn(
            "CONSTRAINT UQ_opportunity_source_identities_version\n"
            "                UNIQUE (opportunity_source_version_id)",
            self.forward,
        )

    def test_identity_fields_are_optional_and_length_bounded(self):
        self.assertIn("employer_name nvarchar(200) NULL", self.forward)
        self.assertIn("role_title nvarchar(200) NULL", self.forward)
        self.assertIn("CK_opportunity_source_identities_employer_length", self.forward)
        self.assertIn("CK_opportunity_source_identities_role_length", self.forward)
        self.assertIn("BETWEEN 1 AND 200", self.forward)

    def test_identity_source_type_is_hard_pinned(self):
        self.assertIn(
            "CK_opportunity_source_identities_type CHECK\n"
            "                (source_type IN (N'job_posting'))",
            self.forward,
        )

    def test_review_events_are_append_only(self):
        body = _procedure_body(self.forward, "usp_SaveOpportunitySourceIdentityForOwner")
        # Sanity check the extraction helper itself before trusting the
        # negative assertions below.
        self.assertIn("opportunity_source_identities", body)
        self.assertNotRegex(
            self.forward,
            r"UPDATE\s+dbo\.opportunity_requirement_review_events",
        )
        self.assertIn(
            "CONSTRAINT UQ_opportunity_requirement_review_events_ordinal\n"
            "                UNIQUE (opportunity_requirement_statement_id, event_ordinal)",
            self.forward,
        )

    def test_review_events_correction_payload_travels_only_with_needs_correction(self):
        self.assertIn(
            "CK_opportunity_requirement_review_events_payload CHECK",
            self.forward,
        )
        self.assertIn(
            "(review_decision = N'needs_correction')\n"
            "                OR (corrected_organized_text IS NULL AND corrected_class IS NULL)",
            self.forward,
        )

    def test_review_events_decision_vocabulary_matches_the_architecture(self):
        self.assertIn(
            "review_decision IN (N'accurate', N'needs_correction', N'not_a_requirement')",
            self.forward,
        )

    def test_member_takes_take_vocabulary_matches_the_architecture(self):
        self.assertIn(
            "take IS NULL OR take IN (N'done_this', N'done_related', N'not_yet')",
            self.forward,
        )

    def test_member_takes_response_length_matches_the_architecture_bound(self):
        self.assertIn(
            "CONSTRAINT CK_opportunity_member_takes_response_length CHECK\n"
            "                (response_text IS NULL OR DATALENGTH(response_text) / 2 BETWEEN 1 AND 4000)",
            self.forward,
        )

    def test_member_takes_reviewed_stamp_requires_response_text(self):
        """A response cannot be marked 'reviewed' while empty — the R2
        commit control (section 6.4) can never certify a blank draft."""
        self.assertIn(
            "CK_opportunity_member_takes_reviewed_pair CHECK\n"
            "                (response_reviewed_at_utc IS NULL OR response_text IS NOT NULL)",
            self.forward,
        )

    def test_member_takes_one_current_row_per_qualification(self):
        self.assertIn(
            "CONSTRAINT UQ_opportunity_member_takes_statement\n"
            "                UNIQUE (opportunity_requirement_statement_id)",
            self.forward,
        )

    # ------------------------------------------------------------
    # New nullable currency columns (additive-safe)
    # ------------------------------------------------------------

    def test_analyses_gets_two_new_nullable_currency_columns(self):
        self.assertIn(
            "IF COL_LENGTH(N'dbo.opportunity_analyses', N'evidence_snapshot_sha256') IS NULL",
            self.forward,
        )
        self.assertIn(
            "ALTER TABLE dbo.opportunity_analyses ADD evidence_snapshot_sha256 char(64) NULL",
            self.forward,
        )
        self.assertIn(
            "IF COL_LENGTH(N'dbo.opportunity_analyses', N'confirmed_requirements_ordinal') IS NULL",
            self.forward,
        )
        self.assertIn(
            "ALTER TABLE dbo.opportunity_analyses ADD confirmed_requirements_ordinal int NULL",
            self.forward,
        )

    def test_requirement_sets_gets_one_new_nullable_ordinal_column(self):
        self.assertIn(
            "IF COL_LENGTH(N'dbo.opportunity_requirement_sets', N'member_confirmed_ordinal') IS NULL",
            self.forward,
        )
        self.assertIn(
            "ALTER TABLE dbo.opportunity_requirement_sets ADD member_confirmed_ordinal int NULL",
            self.forward,
        )

    def test_new_columns_are_all_nullable_never_not_null(self):
        """Additive safety: a NOT NULL column added to a table that already
        carries rows fails at apply time unless every existing row is
        backfilled. Every column this migration adds must stay NULL so no
        backfill is required and no 001-003 row is touched."""
        for column_fragment in (
            "ADD evidence_snapshot_sha256 char(64) NULL",
            "ADD confirmed_requirements_ordinal int NULL",
            "ADD member_confirmed_ordinal int NULL",
        ):
            with self.subTest(column=column_fragment):
                self.assertIn(column_fragment, self.forward)
                self.assertNotIn(
                    column_fragment.replace(" NULL", " NOT NULL"), self.forward
                )

    def test_evidence_snapshot_hash_check_matches_the_established_fingerprint_pattern(self):
        self.assertIn(
            "CK_opportunity_analyses_evidence_snapshot_hash CHECK",
            self.forward,
        )
        self.assertIn(
            "evidence_snapshot_sha256 IS NULL OR evidence_snapshot_sha256 NOT LIKE N''%[^0-9a-f]%''",
            self.forward,
        )

    def test_new_ordinal_columns_are_check_pinned_positive(self):
        self.assertIn(
            "CK_opportunity_analyses_confirmed_ordinal CHECK\n"
            "                  (confirmed_requirements_ordinal IS NULL OR confirmed_requirements_ordinal > 0)",
            self.forward,
        )
        self.assertIn(
            "CK_opportunity_requirement_sets_member_confirmed_ordinal CHECK\n"
            "                  (member_confirmed_ordinal IS NULL OR member_confirmed_ordinal > 0)",
            self.forward,
        )

    def test_existing_table_checks_skip_only_the_historical_row_scan(self):
        """Production's schema identity may alter these protected tables but
        may not read their member rows. WITH NOCHECK avoids that historical
        scan; SQL Server leaves the new constraints enabled for future DML."""
        expected = (
            (
                "opportunity_analyses",
                "CK_opportunity_analyses_evidence_snapshot_hash",
            ),
            (
                "opportunity_analyses",
                "CK_opportunity_analyses_confirmed_ordinal",
            ),
            (
                "opportunity_requirement_sets",
                "CK_opportunity_requirement_sets_member_confirmed_ordinal",
            ),
        )
        for table, constraint in expected:
            with self.subTest(constraint=constraint):
                self.assertIn(
                    f"ALTER TABLE dbo.{table} WITH NOCHECK ADD\n"
                    f"                  CONSTRAINT {constraint} CHECK",
                    self.forward,
                )
                self.assertNotIn(
                    f"ALTER TABLE dbo.{table} WITH CHECK ADD\n"
                    f"                  CONSTRAINT {constraint} CHECK",
                    self.forward,
                )
        self.assertEqual(3, self.forward.count(" WITH NOCHECK ADD\n"))
        self.assertIn(
            "columns are created nullable in this same transaction",
            self.forward.lower(),
        )
        self.assertIn("every historical\n   value is already null", self.forward.lower())

    def test_verifier_pins_enabled_intentionally_untrusted_constraints(self):
        for constraint in (
            "CK_opportunity_analyses_evidence_snapshot_hash",
            "CK_opportunity_analyses_confirmed_ordinal",
            "CK_opportunity_requirement_sets_member_confirmed_ordinal",
        ):
            with self.subTest(constraint=constraint):
                self.assertIn(constraint, self.verify)
        self.assertIn("actual_check.is_disabled <> 0", self.verify)
        self.assertIn("actual_check.is_not_trusted <> 1", self.verify)
        self.assertIn("THROW 53944", self.verify)

    # ------------------------------------------------------------
    # New procedures: exactly four CREATE OR ALTER, nothing else touched
    # ------------------------------------------------------------

    def test_exactly_four_procedures_are_created_or_altered(self):
        """The only CREATE OR ALTER PROCEDURE statements in this file are
        the two brand-new procedures and the two takeovers — proof that no
        OTHER PS-OPPSLATE-001/002/003 procedure is silently redefined."""
        defined = set(_CREATE_PROCEDURE.findall(self.forward))
        expected = set(NEW_PROCEDURE_NAMES) | set(TAKEOVER_PROCEDURE_NAMES)
        self.assertEqual(defined, expected)

    def test_deferred_r2_procedures_are_named_nowhere_as_created(self):
        for name in DEFERRED_R2_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertNotIn(f"PROCEDURE dbo.{name}", self.forward)

    def test_migration_header_states_the_deferred_r2_procedures_and_why(self):
        for name in DEFERRED_R2_PROCEDURE_NAMES:
            with self.subTest(procedure=name):
                self.assertIn(name, self.forward)
        self.assertIn("DEFERRED PROCEDURES, DELIBERATELY", self.forward)

    def test_identity_save_is_fenced_by_the_existing_source_row_version_token(self):
        body = _procedure_body(self.forward, "usp_SaveOpportunitySourceIdentityForOwner")
        self.assertIn("@ExpectedRowVersion binary(8)", body)
        self.assertIn("source_record.row_version = @ExpectedRowVersion", body)
        # No second, source-identity-specific concurrency token is invented.
        self.assertNotIn("@ExpectedIdentityRowVersion", body)

    def test_identity_save_advances_the_shared_token_without_touching_wording_or_confirmation(self):
        body = _procedure_body(self.forward, "usp_SaveOpportunitySourceIdentityForOwner")
        self.assertNotRegex(body, r"UPDATE\s+dbo\.opportunity_source_versions")
        self.assertRegex(body, r"UPDATE\s+dbo\.opportunity_sources\b")
        self.assertIn("SET updated_at_utc = @Now", body)
        self.assertNotIn("original_text", body)
        self.assertNotIn("confirmed_version_number =", body)

    def test_identity_save_resolves_the_current_version_not_a_caller_supplied_one(self):
        body = _procedure_body(self.forward, "usp_SaveOpportunitySourceIdentityForOwner")
        self.assertIn("version_record.version_number = source_record.current_version_number", body)
        self.assertNotIn("@VersionNumber uniqueidentifier", body)

    def test_identity_save_upserts_rather_than_always_inserting(self):
        body = _procedure_body(self.forward, "usp_SaveOpportunitySourceIdentityForOwner")
        self.assertIn("UPDATE dbo.opportunity_source_identities", body)
        self.assertIn("IF @@ROWCOUNT = 0", body)
        self.assertIn("INSERT dbo.opportunity_source_identities", body)

    def test_identity_get_returns_nothing_for_a_forged_or_absent_owner(self):
        body = _procedure_body(self.forward, "usp_GetOpportunitySourceIdentityForOwner")
        self.assertIn("IF @ProfileId IS NULL RETURN", body)

    # ------------------------------------------------------------
    # Takeover: purge and delete learn all three new tables
    # ------------------------------------------------------------

    def test_takeover_procedures_reach_all_three_new_tables(self):
        for procedure in TAKEOVER_PROCEDURE_NAMES:
            body = _procedure_body(self.forward, procedure)
            for table in NEW_TABLE_NAMES:
                unqualified = table.split(".", 1)[1]
                with self.subTest(procedure=procedure, table=table):
                    self.assertIn(unqualified, body)

    def test_takeover_deletes_child_tables_before_their_shared_parent(self):
        """opportunity_source_identities FKs to opportunity_source_versions;
        opportunity_requirement_review_events and opportunity_member_takes
        FK to opportunity_requirement_statements. Each child delete must
        appear before the parent delete in BOTH takeover procedures, or the
        FK refuses the parent delete at apply time."""
        for procedure in TAKEOVER_PROCEDURE_NAMES:
            body = _procedure_body(self.forward, procedure)
            with self.subTest(procedure=procedure):
                identity_pos = body.index("opportunity_source_identities")
                version_delete_pos = body.index(
                    "DELETE version_record\n                FROM dbo.opportunity_source_versions"
                )
                self.assertLess(identity_pos, version_delete_pos)

                takes_pos = body.index("opportunity_member_takes")
                review_events_pos = body.index("opportunity_requirement_review_events")
                statement_delete_pos = body.index(
                    "DELETE statement_record\n                FROM dbo.opportunity_requirement_statements"
                )
                self.assertLess(takes_pos, statement_delete_pos)
                self.assertLess(review_events_pos, statement_delete_pos)

    def test_takeover_procedures_are_hash_stamped_with_a_004_specific_property(self):
        self.assertIn("PS_OPPSLATE_004_DEFINITION_HASH", self.forward)
        stamped_block = self.forward[self.forward.index("@ProtectedProcedures TABLE") :]
        for procedure in TAKEOVER_PROCEDURE_NAMES + NEW_PROCEDURE_NAMES:
            with self.subTest(procedure=procedure):
                self.assertIn(procedure, stamped_block)

    def test_prior_002_hash_stamp_is_not_removed_by_this_migration(self):
        """The forward file never drops PS_OPPSLATE_002_DEFINITION_HASH —
        it is left in place (now describing a superseded body) so the
        rollback can restore it. Only the ROLLBACK removes this migration's
        own stamp."""
        self.assertNotIn("sp_dropextendedproperty", self.forward)
        self.assertIn("sp_dropextendedproperty", self.rollback)

    def test_no_aggregate_verdict_concept_anywhere(self):
        for sql, label in (
            (self.forward, "forward"),
            (self.rollback, "rollback"),
            (self.verify, "verifier"),
        ):
            for identifier in _FORBIDDEN_VERDICT_IDENTIFIERS:
                with self.subTest(file=label, identifier=identifier):
                    self.assertNotIn(identifier, sql.lower())

    def test_every_new_or_taken_over_procedure_resolves_user_key_itself(self):
        for name in NEW_PROCEDURE_NAMES + TAKEOVER_PROCEDURE_NAMES:
            body = _procedure_body(self.forward, name)
            with self.subTest(procedure=name):
                self.assertIn("@UserKey nvarchar(300)", body)
                self.assertIn("app_user.user_key = @UserKey", body)
                self.assertNotIn("@OwnerProfileId", body)
                self.assertIn("owner_profile_id = @ProfileId", body)

    def test_ledger_only_ever_inserted(self):
        self.assertNotRegex(self.forward, r"UPDATE\s+dbo\.schema_migrations")
        self.assertIn(
            "IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-004')",
            self.forward,
        )

    def test_the_ledger_description_fits_the_column_it_is_written_into(self):
        """dbo.schema_migrations.description is nvarchar(500) — the same
        bound PS-OPPSLATE-003's own equivalent test names."""
        match = re.search(
            r"VALUES \(N'PS-OPPSLATE-004', N'(.*?)', N'PeerSlate Bible",
            self.forward,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match.group(1)), 500)

    # ------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------

    def test_rollback_is_one_guarded_transactional_batch(self):
        self.assertIn("SET NOCOUNT ON", self.rollback)
        self.assertIn("SET XACT_ABORT ON", self.rollback)
        self.assertIn("BEGIN TRY", self.rollback)
        self.assertIn("BEGIN TRANSACTION", self.rollback)
        self.assertIn("COMMIT TRANSACTION", self.rollback)
        self.assertIn("ROLLBACK TRANSACTION", self.rollback)

    def test_rollback_refuses_on_missing_ledger_or_unrecorded_migration(self):
        self.assertIn("Rollback refused: the migration ledger is missing.", self.rollback)
        self.assertIn("Rollback refused: PS-OPPSLATE-004 is not recorded.", self.rollback)

    def test_rollback_refuses_when_a_later_migration_is_present(self):
        self.assertIn(
            "Rollback refused: a migration later than PS-OPPSLATE-004 is present.",
            self.rollback,
        )
        self.assertIn("applied_at_utc>@AppliedAtUtc", self.rollback)

    def test_rollback_refuses_on_protected_procedure_drift(self):
        self.assertIn(
            "Rollback refused: a protected PS-OPPSLATE-004 procedure changed after apply.",
            self.rollback,
        )
        self.assertIn("HASHBYTES('SHA2_256',OBJECT_DEFINITION(o.object_id))", self.rollback)

    def test_rollback_checks_all_three_new_tables_for_member_records(self):
        for table in NEW_TABLE_NAMES:
            unqualified = table.split(".", 1)[1]
            with self.subTest(table=table):
                self.assertIn(
                    f"Rollback refused: {unqualified} contains member records.",
                    self.rollback,
                )

    def test_rollback_drops_only_the_two_new_procedures_directly(self):
        drop_statements = re.findall(r"DROP PROCEDURE dbo\.(\w+);", self.rollback)
        # The two takeovers are RESTORED (CREATE OR ALTER), never DROPped —
        # only the two brand-new procedures are dropped outright.
        self.assertEqual(set(drop_statements), set(NEW_PROCEDURE_NAMES))

    def test_rollback_restores_both_takeover_procedures_to_their_002_bodies(self):
        for procedure in TAKEOVER_PROCEDURE_NAMES:
            with self.subTest(procedure=procedure):
                self.assertIn(f"CREATE OR ALTER PROCEDURE dbo.{procedure}", self.rollback)
        # The restored bodies must NOT reference any of the three new v2
        # tables — that is precisely what makes them the PRE-004 bodies.
        purge_body = _procedure_body(self.rollback, "usp_PurgeExpiredOpportunityWorkingData")
        delete_body = _procedure_body(self.rollback, "usp_DeleteOpportunityWorkingSessionForOwner")
        for table in NEW_TABLE_NAMES:
            unqualified = table.split(".", 1)[1]
            with self.subTest(table=table):
                self.assertNotIn(unqualified, purge_body)
                self.assertNotIn(unqualified, delete_body)

    def test_rollback_re_stamps_the_002_hash_after_restoring(self):
        self.assertIn("PS_OPPSLATE_002_DEFINITION_HASH", self.rollback)
        restore_block = self.rollback[
            self.rollback.index("@RestoredProcedureHashPropertyName") :
        ]
        for procedure in TAKEOVER_PROCEDURE_NAMES:
            with self.subTest(procedure=procedure):
                self.assertIn(procedure, restore_block)

    def test_rollback_drops_the_004_hash_stamp_before_restoring_bodies(self):
        drop_stamp_pos = self.rollback.index("sp_dropextendedproperty")
        restore_pos = self.rollback.index(
            "CREATE OR ALTER PROCEDURE dbo.usp_PurgeExpiredOpportunityWorkingData"
        )
        self.assertLess(drop_stamp_pos, restore_pos)

    def test_rollback_drops_only_the_three_new_tables(self):
        drop_statements = re.findall(r"DROP TABLE dbo\.(\w+);", self.rollback)
        expected = {table.split(".", 1)[1] for table in NEW_TABLE_NAMES}
        self.assertEqual(set(drop_statements), expected)

    def test_rollback_drops_children_before_parents(self):
        member_takes_pos = self.rollback.index("DROP TABLE dbo.opportunity_member_takes;")
        review_events_pos = self.rollback.index(
            "DROP TABLE dbo.opportunity_requirement_review_events;"
        )
        identities_pos = self.rollback.index(
            "DROP TABLE dbo.opportunity_source_identities;"
        )
        # All three are independent leaves off shared 001/002 parents, so
        # there is no ordering requirement AMONG them — only that all three
        # drop before the migration's ledger row is removed.
        ledger_delete_pos = self.rollback.index(
            "DELETE dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-004'"
        )
        for pos in (member_takes_pos, review_events_pos, identities_pos):
            self.assertLess(pos, ledger_delete_pos)

    def test_rollback_drops_the_new_columns_and_their_check_constraints(self):
        for column, table in (
            ("evidence_snapshot_sha256", "opportunity_analyses"),
            ("confirmed_requirements_ordinal", "opportunity_analyses"),
            ("member_confirmed_ordinal", "opportunity_requirement_sets"),
        ):
            with self.subTest(column=column):
                self.assertIn(
                    f"ALTER TABLE dbo.{table} DROP COLUMN {column}", self.rollback
                )

    def test_rollback_deletes_only_its_own_ledger_row(self):
        self.assertIn(
            "DELETE dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-004'",
            self.rollback,
        )
        self.assertNotIn("migration_id=N'PS-OPPSLATE-001'", self.rollback)
        self.assertNotIn("migration_id=N'PS-OPPSLATE-002'", self.rollback)
        self.assertNotIn("migration_id=N'PS-OPPSLATE-003'", self.rollback)

    def test_rollback_never_ends_in_a_committed_state_on_refusal(self):
        """Every THROW happens before the single COMMIT TRANSACTION, so a
        refusal always leaves the outer transaction to the CATCH block's
        ROLLBACK rather than a partially-applied rollback."""
        commit_pos = self.rollback.index("COMMIT TRANSACTION")
        throw_positions = [
            match.start() for match in re.finditer(r"THROW \d+,", self.rollback)
        ]
        self.assertTrue(throw_positions)
        for position in throw_positions:
            self.assertLess(position, commit_pos)

    # ------------------------------------------------------------
    # Error number hygiene
    # ------------------------------------------------------------

    def test_error_numbers_are_unique_within_forward_and_rollback(self):
        forward_numbers = re.findall(r"THROW (\d+),", self.forward)
        rollback_numbers = re.findall(r"THROW (\d+),", self.rollback)
        self.assertEqual(len(forward_numbers), len(set(forward_numbers)))
        self.assertEqual(len(rollback_numbers), len(set(rollback_numbers)))
        self.assertEqual(set(), set(forward_numbers) & set(rollback_numbers))

    def test_error_numbers_do_not_collide_with_any_other_migration(self):
        forward_numbers = set(re.findall(r"THROW (\d+)", self.forward))
        rollback_numbers = set(re.findall(r"THROW (\d+)", self.rollback))
        mine = forward_numbers | rollback_numbers
        for path in MIGRATIONS.glob("*.sql"):
            if path in (FORWARD, ROLLBACK):
                continue
            with self.subTest(path=path.name):
                other_numbers = set(
                    re.findall(r"THROW (\d+)", path.read_text(encoding="utf-8"))
                )
                self.assertEqual(set(), mine & other_numbers)

    # ------------------------------------------------------------
    # Verification script
    # ------------------------------------------------------------

    def test_verifier_registration_check_targets_004(self):
        self.assertIn("migration_id = N'PS-OPPSLATE-004'", self.verify)
        self.assertIn("PS-OPPSLATE-004 is not registered.", self.verify)

    def test_verifier_covers_every_accumulated_procedure(self):
        block_match = re.search(
            r"INSERT @ProcedureNames \(procedure_name\)\s*VALUES(.*?);",
            self.verify,
            re.DOTALL,
        )
        self.assertIsNotNone(block_match)
        listed = set(re.findall(r"N'(\w+)'", block_match.group(1)))
        self.assertEqual(listed, set(ALL_ACCUMULATED_PROCEDURE_NAMES))

    def test_verifier_generic_grep_checks_the_same_four_invariants(self):
        for phrase in (
            "@UserKey nvarchar(300)%",
            "@OwnerProfileId%",
            "app_user.user_key = @UserKey%",
            "owner_profile_id = @ProfileId%",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.verify)

    def test_verifier_proves_the_takeover_textually_reaches_all_three_tables(self):
        for table in NEW_TABLE_NAMES:
            unqualified = table.split(".", 1)[1]
            with self.subTest(table=table):
                self.assertIn(unqualified, self.verify)
        self.assertIn(
            "The purge takeover does not reach all three new v2 tables.",
            self.verify,
        )
        self.assertIn(
            "The delete takeover does not reach all three new v2 tables.",
            self.verify,
        )

    def test_verifier_exercises_cross_owner_identity_isolation(self):
        for phrase in (
            "A forged UserKey produced a truthful-looking identity save outcome.",
            "Owner B saved identity against owner A''s source.",
            "Identity save is not fenced by @ExpectedRowVersion.",
            "Owner B''s read returned owner A''s source identity.",
            "A forged UserKey returned a source identity row.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.verify)

    def test_verifier_exercises_the_takeover_cascade_for_both_owners(self):
        self.assertIn("usp_PurgeExpiredOpportunityWorkingData", self.verify)
        self.assertIn("usp_DeleteOpportunityWorkingSessionForOwner", self.verify)
        self.assertIn(
            "The purge takeover left a source identity row behind for its own owner.",
            self.verify,
        )
        self.assertIn(
            "Owner A''s purge removed owner B''s unexpired v2 rows.",
            self.verify,
        )
        self.assertIn("The delete takeover left a member take behind.", self.verify)
        self.assertIn(
            "Owner B''s explicit delete removed owner A''s undeleted v2 rows.",
            self.verify,
        )

    def test_verifier_proves_delete_survivor_and_refuses_stale_delete(self):
        purge_assertion = self.verify.index(
            "Owner A''s purge removed owner B''s unexpired v2 rows."
        )
        survivor_setup = self.verify.index(
            "Owner A explicit-delete survivor rows were not fully established.",
            purge_assertion,
        )
        stale_refusal = self.verify.index(
            "A stale row version was not refused before explicit delete.",
            survivor_setup,
        )
        real_delete = self.verify.index(
            "Owner B could not delete their own working session.",
            stale_refusal,
        )
        survivor_assertion = self.verify.index(
            "Owner B''s explicit delete removed owner A''s undeleted v2 rows.",
            real_delete,
        )
        self.assertLess(purge_assertion, survivor_setup)
        self.assertLess(survivor_setup, stale_refusal)
        self.assertLess(stale_refusal, real_delete)
        self.assertLess(real_delete, survivor_assertion)

    def test_verifier_no_aggregate_guard_matches_the_concept_not_four_names(self):
        self.assertIn("verdict", self.verify)
        self.assertIn("recommend", self.verify)

    def test_verifier_never_ends_in_a_committed_state(self):
        self.assertIn("ROLLBACK TRANSACTION;", self.verify)
        rollback_pos = self.verify.index("ROLLBACK TRANSACTION;")
        # No unconditional COMMIT TRANSACTION exists anywhere in this
        # production-safe verification script; every synthetic row must be
        # undone before the script returns.
        self.assertNotIn("\n    COMMIT TRANSACTION;\n", self.verify)
        self.assertGreater(len(self.verify), rollback_pos)

    def test_verifier_materializes_function_results_before_exec_arguments(self):
        """SQL Server EXEC arguments accept variables, not inline functions."""
        exec_blocks = re.findall(
            r"\bEXEC\s+dbo\.\w+(.*?);",
            self.verify,
            re.IGNORECASE | re.DOTALL,
        )
        self.assertTrue(exec_blocks)
        inline_function = re.compile(
            r"@\w+\s*=\s*[A-Za-z_]\w*\s*\(",
            re.IGNORECASE,
        )
        for block in exec_blocks:
            with self.subTest(block=block[:80]):
                self.assertIsNone(inline_function.search(block))

    def test_verifier_carries_the_latest_identity_rowversion_into_confirmation(self):
        identity_update = self.verify.index(
            "Owner A could not update their own source identity with the fresh token."
        )
        token_refresh = self.verify.index(
            "SELECT TOP (1) @SourceRowVersionA = source_row_version",
            identity_update,
        )
        confirmation = self.verify.index(
            "EXEC dbo.usp_ConfirmOpportunitySourceForOwner",
            token_refresh,
        )
        self.assertLess(identity_update, token_refresh)
        self.assertLess(token_refresh, confirmation)

    def test_verifier_ages_the_session_without_breaking_the_expiry_constraint(self):
        ageing = re.search(
            r"UPDATE dbo\.opportunity_working_sessions\s+"
            r"SET created_at_utc = DATEADD\(HOUR, -3, SYSUTCDATETIME\(\)\),\s+"
            r"expires_at_utc = DATEADD\(HOUR, -1, SYSUTCDATETIME\(\)\)",
            self.verify,
            re.IGNORECASE,
        )
        self.assertIsNotNone(ageing)

    def test_verifier_creates_every_owner_b_child_before_isolation_checks(self):
        own_identity = self.verify.index(
            "Owner B could not create the identity row required by the isolation checks."
        )
        token_refresh = self.verify.index(
            "SELECT TOP (1) @SourceRowVersionB = source_row_version",
            own_identity,
        )
        confirmation = self.verify.index(
            "EXEC dbo.usp_ConfirmOpportunitySourceForOwner",
            token_refresh,
        )
        purge_assertion = self.verify.index(
            "Owner A''s purge removed owner B''s unexpired v2 rows.",
            confirmation,
        )
        self.assertLess(own_identity, token_refresh)
        self.assertLess(token_refresh, confirmation)
        self.assertLess(confirmation, purge_assertion)

    def test_verifier_uses_a_distinct_synthetic_auth_provider(self):
        """A distinct provider string (oppslate-v2-verification) keeps this
        script's synthetic owners from ever colliding with
        PS-OPPSLATE-003's own verifier (oppslate-verification) if both ran
        against the same throwaway database in one session."""
        self.assertIn("oppslate-v2-verification", self.verify)
        self.assertNotIn("N'oppslate-verification'", self.verify)


if __name__ == "__main__":
    unittest.main()
