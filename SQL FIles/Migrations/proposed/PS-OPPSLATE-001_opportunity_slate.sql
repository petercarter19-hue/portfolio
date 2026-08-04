/* ============================================================
   PS-OPPSLATE-001 - Opportunity Slate working store (Slices OS-1, OS-2, OS-3)

   ------------------------------------------------------------------
   WHAT THIS REVISION ASSUMES, AND WHAT IT UPGRADES FROM. Read this first;
   the rest of the header is the accumulated record of earlier slices.

   THREE starting shapes are supported, and every block below is guarded so
   the file is idempotent over all of them:

     A. an EMPTY database with the prerequisites applied - creates all 12
        tables, 17 procedures and their constraints;
     B. the SLICE OS-1 revision - WHICH IS WHAT PRODUCTION CARRIES TODAY
        (3 tables, 6 procedures, applied 2026-08-04; see the record below).
        This path runs both OS-2 guarded upgrades
        (UQ_opportunity_source_versions_id_owner and the widened
        CK_opportunity_working_sessions_state) and then adds everything OS-2
        and OS-3 own;
     C. the SLICE OS-2 revision - gated on 2026-08-04 but NOT applied
        anywhere. This path adds only the four OS-3 tables and the four OS-3
        procedures, and re-deploys the four procedures OS-3 had to change.

   FOUR OS-2/OS-1 PROCEDURES CHANGED IN THIS REVISION, and only these four:
     usp_PurgeExpiredOpportunityWorkingData
     usp_DeleteOpportunityWorkingSessionForOwner
     usp_SaveOpportunityRequirementProposalForOwner
     usp_CorrectOpportunityRequirementStatementForOwner
   All four learned to remove the new analysis, citation and response rows.
   That was not optional: those rows reference the requirement statements, so
   without it a purge could not complete, a member''s explicit delete would
   fail on a foreign key while promising to be atomic, and re-reading the
   source would fail AFTER the confirmation had already been cleared. The
   fourth also deletes the analysis when a statement correction un-confirms
   the set, because an analysis of an un-confirmed reading describes
   requirements the member has since changed.

   ONE DELETE IN THIS REVISION DESTROYS MEMBER-AUTHORED TEXT, named here
   rather than buried: re-running AI step 2 replaces the whole statement set,
   so the member responses attached to the old statements go with them. See
   usp_SaveOpportunityRequirementProposalForOwner for why the alternative
   (orphaned rows the member can never see) is worse, and note that the
   Review Requirements screen warns before the member presses that control.

   THIS REVISION HAS NOT BEEN APPLIED TO PRODUCTION.
   ------------------------------------------------------------------

   Package: docs/initiatives/PS-OPPORTUNITY-SLATE-001
   Contract: 01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md section 8
             (data model), section 9 (route/service contract),
             section 11 (security), section 16 (slice scope).

   Slice OS-1 covered the ephemeral pre-save workbench a signed-in member
   needs to paste a role, review the captured source, correct its wording by
   hand, and confirm it (checkpoint 1 of 2):

     dbo.opportunity_working_sessions   the ephemeral workbench record
     dbo.opportunity_sources            one employer source per session
     dbo.opportunity_source_versions    append-only captured wording

   Slice OS-2 adds the AI-proposal store the room's first two AI steps write
   into, and checkpoint 2 of 2:

     dbo.opportunity_source_reviews          AI step 1 ran for this version
     dbo.opportunity_source_concerns         its proposed extraction concerns
     dbo.opportunity_requirement_sets        one per working session
     dbo.opportunity_requirement_set_versions   one AI step 2 run
     dbo.opportunity_requirement_statements  the statements it proposed

   Slice OS-3 adds the alignment analysis, its grounded citations, and the
   member's own responses to each qualification:

     dbo.opportunity_analyses                one analysis per requirement
                                             version
     dbo.opportunity_analysis_statements     its per-qualification result
     dbo.opportunity_analysis_citations      the evidence each result cites
     dbo.opportunity_responses               the member's own answers

   Deliberately NOT in this file (later slices, handoff section 16): the
   durable saved slate, saved results, and the save idempotency ledger
   (OS-4). No aggregate score, percentage, recommendation, or
   employer-prediction column exists anywhere in this file, and none may
   ever be added - handoff section 1 and section 8 make that a design rule,
   not an oversight. Slice OS-3 is where that rule stops being about a job
   advert and starts being about a person, so read the note above
   dbo.opportunity_analyses before adding a column to any table here.

   RE-APPLYING OVER THE SLICE OS-1 REVISION IS SUPPORTED. This file is
   idempotent in both directions: applied to an empty database it creates
   everything, and applied to a database already carrying the OS-1 revision
   it creates only what is missing AND upgrades the one constraint that
   changed. That upgrade is not optional and was missing until independent
   review finding F4 - see the "SLICE OS-2 CONSTRAINT UPGRADE" block below
   for what silently broke without it and why the compatibility THROW never
   caught it.

   SLICE OS-2 TOUCHED TWO SLICE OS-1 PROCEDURES, and only these two:
   usp_PurgeExpiredOpportunityWorkingData and
   usp_DeleteOpportunityWorkingSessionForOwner both learned to remove the
   new child rows. That was not optional. The proposal tables reference the
   source versions and the working session, so without it a purge could not
   complete (leaving expired employer wording on disk past its expiry) and a
   member's explicit delete would fail on a foreign key while promising to
   be atomic. No other OS-1 procedure changed.

   EPHEMERAL BY DESIGN. Nothing here is a saved, member-visible artifact.
   "Session private - nothing is saved yet" means exactly this: a working
   session is infrastructure. It is never listed, exported, projected, or
   shared, and it carries an expires_at_utc that every read enforces
   (handoff section 1). Physical destruction runs through
   dbo.usp_PurgeExpiredOpportunityWorkingData below, which the application
   invokes opportunistically at the start of a room request for that one
   owner; no background scheduler exists in this runtime and this
   migration does not add one.

   ONE ACTIVE SESSION PER MEMBER (owner decision, handoff section 17-Q2):
   UQ_opportunity_working_sessions_owner enforces it in the schema rather
   than trusting the application to remember.

   VERBATIM SOURCE PRESERVATION. opportunity_source_versions.original_text
   is written once, at INSERT, and is never updated by any procedure in
   this file - a member's manual correction is written to the separate,
   nullable member_corrected_text column on the same version row, so the
   employer's captured wording is always recoverable (handoff section 8:
   "member-corrected wording ... with the original always retained").
   Replacing the source appends a NEW version row rather than rewriting
   the current one. Confirmation is cleared whenever the confirmed text
   changes, so a confirmed source can never silently describe wording the
   member never confirmed.

   NO AI, NO AUDIT NOISE. Slice OS-1 makes no AI call, so no model,
   prompt-contract, or proposal column appears here (those arrive with
   OS-2/OS-3 on their own tables). No procedure in this file appends an
   audit event: a working session is ephemeral infrastructure whose
   content is private employer/member wording, and writing an audit row
   per keystroke-save would create log noise and a needless second place
   for that wording to leak. The durable, auditable artifact is the saved
   slate that OS-4 introduces.

   CAPTURE METHOD ENUM. capture_method is CHECK-pinned to the full
   architectural enum (pasted / dictated / uploaded / imported) because
   that is the contract; OS-1 itself only ever writes N'pasted'.
   Dictation lands with OS-5, upload and import with OS-6.

   THIS REVISION IS NOT APPLIED TO PRODUCTION. PRODUCTION CARRIES THE SLICE
   OS-1 REVISION OF THIS FILE.

   THE PRODUCTION-APPLY RECORD, STATED HERE RATHER THAN CITED. An operator
   reading this file needs the record in front of them, so it is written out
   below instead of being pointed at:

     What      the SLICE OS-1 revision of this file, exactly as it stood on
               origin/main at a55a4c5. Nothing executable was changed to
               apply it; the diff that accompanied the apply was confined to
               this leading header comment (executable SHA-256
               895f3b5eb86af13d50ef41523a0728b726f8950e5375cddf2ca6a9884ba38a83
               before and after).
     Where     peerslate-database, the production Azure SQL database.
     When      2026-08-04 UTC, under explicit owner authorization.
     How       one batch through mssql-python, using
               scripts/apply_sql_migrations.py's connection and execution
               method, inside the file's own transaction.
     Gate      the 2026-08-03 apply/verify/exercise/rollback/re-apply gate
               recorded further down this header, executed on the throwaway
               database ps-oppslate-001-gate-20260803 (identical tier,
               server and collation to production) and deleted afterwards.
     Pre-flight  no Opportunity Slate object of any kind existed, and every
               guarded prerequisite was present.
     Post-apply  3 tables, 3 indexes, 39 constraints, 6 procedures, 6
               definition-hash properties, 1 ledger row, 1 audit event, zero
               data rows; every new foreign key and CHECK enabled and
               trusted; all six procedure names already present in
               services/database_service.ALLOWED_PROCEDURES; the
               owner-isolation verifier returned verified = 1 and left no
               residue.

   PRODUCTION THEREFORE CARRIES 3 TABLES, 3 INDEXES, 39 CONSTRAINTS AND 6
   PROCEDURES - NOT the 8 tables and 13 procedures THIS file creates - with
   PEERSLATE_OPPORTUNITY_SLATE_ENABLED still unset, so the room is off.

   (The same record was also written into the OS-1 copy of this header by
   commit 2aac790ca698fa59ba52fff9b78ba7146361e06c. That is supplementary
   provenance only: at the time of writing that commit sits on
   work/2026-08-03-oppslate-prod-migration-record and is not on main, so do
   not rely on being able to follow it. Everything it says that matters to an
   operator of THIS file is stated above.)

   Applying THIS revision is a separate operational step needing its own
   authorization. On that path the file does not start from nothing: the
   guarded blocks below detect the OS-1 objects that already exist, skip
   their CREATEs, and run the one upgrade OS-1 cannot have had -
   UQ_opportunity_source_versions_id_owner, the candidate key the 2026-08-03
   gate found missing. That key is deliberately absent from production
   because nothing in OS-1 references opportunity_source_versions; without it
   FK_opportunity_source_reviews_version below cannot be created at all. The
   guarded ALTER therefore has to run BEFORE that table, and does. This exact
   populated-OS-1-to-OS-2 upgrade was exercised on the gate (see "upgrade"
   below and the 2026-08-04 gate further down); it has not been exercised
   against production data.

   RE-GATED ON THE UPGRADE PATH, 2026-08-04. The 2026-08-03 gate ran before
   the OS-1 revision reached production and before this file was ported onto
   the OS-2 branch. Because production now carries OS-1, the path that
   matters is the upgrade over a POPULATED OS-1 database, so the whole gate
   was run again on that shape.

     Database  ps-oppslate-002-gate-20260804, a throwaway Basic-tier Azure
               SQL database on server peerslate, collation
               SQL_Latin1_General_CP1_CI_AS - identical tier, server and
               collation to production. Created for this gate and deleted
               immediately afterwards.
     Driver    mssql-python, each file executed as ONE batch exactly as
               scripts/apply_sql_migrations.py does.
     Prereqs   PS-PLAT-000 through PS-PLAT-007, PS-AUTH-001 and
               PS-WORKSHOP-001, applied through
               scripts/apply_sql_migrations.py. PS-PLAT-000 removed the
               manual dbo.app_users bootstrap the 2026-08-03 gate needed;
               that is now confirmed by execution, not just expected.
     Baseline  the SLICE OS-1 revision as it stands on origin/main
               (executable SHA-256
               895f3b5eb86af13d50ef41523a0728b726f8950e5375cddf2ca6a9884ba38a83),
               i.e. byte-identical to what production carries, then
               POPULATED through the OS-1 procedures themselves: two
               distinct owners, each with a working session, a source,
               multiple appended source versions, a member correction
               overlay and a confirmed source. Nothing was hand-inserted
               where a procedure existed. 2 sessions, 2 sources, 5 versions.

   Results of the 2026-08-04 gate:
     upgrade    PASS - this file applied over that populated OS-1 database.
                Both guarded upgrades ran on tables that already held rows:
                UQ_opportunity_source_versions_id_owner was added to a
                five-row opportunity_source_versions, and
                CK_opportunity_working_sessions_state was rebuilt with the
                two checkpoint-2 states while validating the existing
                source_confirmed rows. Afterwards: 8 tables, 13 procedures,
                37 CHECK constraints, 31 key constraints, 14 foreign keys,
                all enabled and trusted, and 13 definition-hash properties
                each matching its deployed body.
     data       PASS - NO member content changed. A per-row SHA-256 of
                original_text, original_sha256 and member_corrected_text
                across all five version rows, plus the source/session state
                rows, was taken before and after and compared: every row
                identical, and the aggregate digest
                607C1D965836B4EFCC739CAB6C7F6E87D5E5EF22BA3ADC392A9F0DDDEBB53ECA
                before and after. Row counts unchanged.
     exercise   PASS - the seven OS-2 procedures were CALLED on that
                populated database: save a review and its concerns, resolve
                a concern both ways (applied and dismissed), save a
                requirement proposal, correct a statement's class and
                clarification, confirm the requirement set, and purge. The
                AI columns and the member-decision columns stayed apart -
                a statement carrying proposed_class = required_qualification
                and member_class = preferred_qualification held both.
     negative   PASS - stale row_version returned 'changed' and did not
                write; a forged @UserKey returned 'changed' or nothing from
                every procedure; cross-owner keys returned 'changed'; an
                unsupported class or resolution word returned 'invalid' or
                'changed'; malformed JSON returned 'invalid'.
     atomicity  PASS - two forced mid-procedure failures (a statement whose
                employer_text exceeds its CHECK, and a concern quote that
                exceeds its own) both rolled back whole: engine error 547,
                no partial rows, no orphan set version, no advanced version
                number, the member's confirmation and decisions intact, and
                @@TRANCOUNT back to 0.
     isolation  PASS - PS-OPPSLATE-001_owner_isolation_verify.sql returned
                verified = 1 while the two real gate owners' data was
                present, and left no residue.
     rollback   PASS - refused while OS-2 proposal rows existed
                ("opportunity_source_concerns contains member records"),
                refused again on a deliberately drifted procedure
                definition, then removed exactly what it owns once the data
                was cleared through the member-facing delete, leaving all
                ten prerequisite migrations intact.
     re-apply   PASS - clean re-apply, and a SECOND apply over itself was a
                genuine no-op: same ledger row, same audit-event count, same
                applied_at_utc, same object counts.
     harness    PASS - tests/test_opportunity_slate_migration.py run with
                PS_OPPSLATE_SQL_GATE=1 against the gate database: 49 tests,
                all passing, including
                OpportunitySlateIsolatedSqlGateTests.test_apply_verify_rollback_reapply.
                That count is the harness AS IT STOOD DURING THE GATE RUN. The
                two tests pinning the fixes below were written afterwards, so
                the suite reports 51 today; the extra two are static contract
                checks and need no engine.

   TWO MORE DEFECTS WERE FOUND AND FIXED, both only reachable by running it:
     1. usp_SaveOpportunitySourceReviewForOwner DESTROYED MEMBER DECISIONS ON
        A REJECTED PROPOSAL. Its "more than 20 concerns" guard sat AFTER the
        two DELETEs that clear the previous review, and then COMMITted. A
        21-concern payload therefore deleted the member's existing review,
        its concerns, and every applied/dismissed decision and per-concern
        corrected wording on them - and returned 'invalid', which tells the
        caller nothing happened. Observed on the gate: three resolved
        concerns went to zero. The count and its guard now run before the
        DELETEs, which is the order the sibling procedure
        usp_SaveOpportunityRequirementProposalForOwner already used. THIS
        CHANGES BEHAVIOUR ON THE 'invalid' PATH - from destroying the
        previous review to leaving it alone - and is the behaviour that
        return value already claimed. The success path is unchanged.
        Pinned by test_a_rejected_proposal_counts_before_it_deletes.
        The member's own document wording was never at risk: it lives on
        the source version row, which this procedure does not touch.
     2. THE LEDGER LIED AFTER THE UPGRADE. dbo.schema_migrations is how an
        operator answers "which revision does this database carry?", and the
        ledger write is INSERT-if-absent. On the upgrade path the row
        already exists, so the INSERT was skipped and the row kept saying
        "Slice OS-1: ... owner-scoped get/save/correct/confirm/delete
        procedures" on a database that now carried eight tables and thirteen
        procedures. A guarded UPDATE now corrects the description in place.
        applied_at_utc is deliberately NOT moved - the rollback's "a later
        migration is present" guard compares against it, and the second
        apply must stay a no-op, which was re-proved after the fix.
        Pinned by test_the_upgrade_path_corrects_the_migration_ledger_description.

   THE EXECUTABLE BYTES CHANGED, AND THE OS-2 REVIEW RECORD IS NOW STALE.
   OS-2's independent review certified the executable SQL (everything after
   this header comment) as SHA-256
   b8e881a130b528a108bf44ccd54a605a7998c0bdab2bd32ae9d2ab1140cccb0d. The two
   fixes above change it to
   c0984204f7d394d50cd30981c1be777332b921b274ef362fd758c8db073ea800. Defect 1
   changes procedure BEHAVIOUR on the 'invalid' path, so it is not a
   header-only or cosmetic edit and the certified-bytes claim must be
   re-established rather than carried forward.

   THE FIXES ARE PORTED, AND THE BYTES HERE ARE THE GATED BYTES. Both fixes
   and both pinning tests were carried onto the OS-2 delivery branch
   work/2026-08-03-opportunity-slate-os2. The executable body of THIS file -
   everything below this header comment, from the first session-setting
   statement to end of file, which is exactly what the hashes above measure -
   was recomputed on that branch and is
   c0984204f7d394d50cd30981c1be777332b921b274ef362fd758c8db073ea800, identical
   to the gate branch's. Nothing else was taken from the gate branch. The
   rollback script and PS-OPPSLATE-001_owner_isolation_verify.sql are
   unchanged by the fix; the verification script still hashes the same way at
   3ac86a103a751cf428aaa832a6b153d9edaa0a6fe2a74c9ecd87cf09d34e7026. The
   superseded record is corrected in the slice OS-2 completion report, section
   4 residual 3. Only this header changed after the port, and the header is
   outside the hashed region by construction.

   WHAT THE 2026-08-04 GATE STILL COULD NOT PROVE. It ran against a
   two-owner, five-version database, not against production's data volume,
   and it did not run on the production database. The post-commit
   result-set race below remains unreproduced for the same reason it was in
   August 3. Concurrency was single-threaded throughout, so no genuinely
   simultaneous two-writer contention was scheduled.

   EXECUTED AND GATED, 2026-08-03. This T-SQL has now run against a real
   engine. The apply/verify/exercise/rollback/re-apply gate was executed on a
   throwaway Azure SQL database, ps-oppslate-001-gate-20260803 (Basic tier,
   server peerslate, collation SQL_Latin1_General_CP1_CI_AS - identical to
   production), created for the gate and deleted immediately afterwards.
   Engine: Microsoft SQL Azure 12.0.2000.8. Driver: mssql-python, executing
   each file as ONE batch exactly as scripts/apply_sql_migrations.py does.

   Prerequisites applied first, in order: PS-PLAT-001 through PS-PLAT-007,
   PS-AUTH-001, PS-WORKSHOP-001. dbo.app_users had to be bootstrapped by hand
   before PS-PLAT-001 could add FK_audit_events_app_users, because at gate
   time it was a pre-migration table that no tracked migration created.

   THAT IS NO LONGER TRUE, as of PS-PLAT-000_app_users_base.sql (PR 263,
   2026-08-03). A from-empty database now gets the table from a real
   migration, so the manual step this gate needed is gone and a future rerun
   should apply PS-PLAT-000 first instead. Nothing about the gate's RESULTS
   changes - the same table, with the same columns the FK targets require,
   was present either way.

   Results:
     apply      PASS - 8 tables, 13 procedures, 13 definition-hash extended
                properties, 1 ledger row, 1 audit event.
     verify     PASS - PS-OPPSLATE-001_owner_isolation_verify.sql returned
                verified = 1. Two synthetic owners; every cross-owner read
                returned nothing; the forged-key canary on all thirteen
                procedures returned the truthful empty/changed outcome.
     exercise   PASS - the procedures were CALLED, not just parsed: save,
                idempotent replay, correct, confirm, replace, both AI
                proposal steps, both checkpoints, purge and delete.
     rollback   PASS - refused while member rows existed (each guard fired in
                turn), then removed exactly the 8 tables, 13 procedures, hash
                properties and ledger row it owns, leaving all nine
                prerequisite migrations intact.
     re-apply   PASS - clean re-apply, and a SECOND apply over itself was a
                genuine no-op (no duplicate ledger row, no audit event).
     upgrade    PASS - applied over a POPULATED slice OS-1 database: both
                guarded upgrades ran, member data and verbatim employer
                wording survived, and checkpoint 2 then worked end to end.

   The repository's own harness was run last and independently agrees:
   tests/test_opportunity_slate_migration.py
   OpportunitySlateIsolatedSqlGateTests.test_apply_verify_rollback_reapply,
   the named unmet condition, executed with PS_OPPSLATE_SQL_GATE=1 against
   the gate database and PASSED. It is skipped again by default because it
   mutates whatever AZURE_SQL_CONNECTIONSTRING points at.

   THREE DEFECTS WERE FOUND AND FIXED, all invisible to static assertion:
     1. This file (fatal, both paths). opportunity_source_versions had no
        UNIQUE (opportunity_source_version_id, owner_profile_id), so slice
        OS-2's FK_opportunity_source_reviews_version could not be created at
        all: "There are no primary or candidate keys in the referenced table
        ... that match the referencing column list". Fixed by adding the
        missing candidate key AND a guarded ALTER for the OS-1 upgrade path.
     2. The verification script asserted a requirement proposal succeeds on a
        source it had deliberately left unconfirmed. Fixed by re-confirming.
     3. The verification script backdated expires_at_utc alone, which
        CK_opportunity_working_sessions_expiry rejects. Fixed by ageing
        created_at_utc with it.
   None of the three changed any procedure's behaviour; see the completion
   record for the exact diff.

   KNOWN ISSUE - STALE row_version IN THE TRAILING RESULT SET (named
   "OS-1 post-commit result-set race"). Every mutating procedure below
   commits and THEN runs its result-set SELECT, so the row_version tokens
   it returns are read outside the transaction that produced them. A
   concurrent writer on the same owner's session can advance row_version
   between the COMMIT and that SELECT, and the caller then receives a
   token describing the other writer's later state. The optimistic-
   concurrency check itself is sound - a subsequent mutation still
   compares @ExpectedRowVersion against the live row and fails closed -
   so the failure mode is a wrongly ACCEPTED next write by the client
   that received the newer token, not a corrupted or unauthorized one.
   Owner isolation, verbatim-source preservation, and the confirmation-
   clearing rules are unaffected.

   This is PRE-EXISTING and DELIBERATELY NOT FIXED in slice OS-1. Closing
   it means reordering each procedure to SELECT ... INTO the result inside
   the transaction, COMMIT, then RETURN the captured values, and updating
   tests/test_opportunity_slate_migration.py's
   test_every_mutating_procedure_body_owns_a_transaction, which currently
   asserts the commit-then-select shape. The exposure requires two
   concurrent writers on one member's single working session, which the
   UQ_opportunity_working_sessions_owner constraint plus the one-room-tab
   client makes unlikely but not impossible.

   WHAT THE 2026-08-03 GATE ADDED TO THIS NOTE. The shape is confirmed on
   the real deployed objects, not merely in this source text: reading
   OBJECT_DEFINITION back from the gate database showed the last COMMIT
   preceding the trailing success SELECT in all NINE mutating procedures, so
   the window is genuinely present in every one of them.

   The gate also narrowed what is at risk. The fence itself was exercised
   under real contention and holds: a mutation presented with a stale
   row_version returned 'changed' and its write did NOT land, and a forced
   mid-procedure failure rolled back whole - no partial statement rows, no
   orphan set version, @@TRANCOUNT back to 0. So the damage a wrong token
   can do remains bounded to a wrongly ACCEPTED next write by the client
   holding it; it cannot corrupt a row, cross an owner boundary, or leave a
   torn transaction.

   The race WINDOW ITSELF WAS NOT REPRODUCED. Hitting it needs two writers
   interleaved inside the microseconds between COMMIT and the trailing
   SELECT, which single-threaded gate conditions cannot schedule
   deterministically. Treat it as present-but-unreproduced, not as
   disproven.

   THIS ISSUE IS ALREADY IN PRODUCTION AND REMAINS OPEN. The six OS-1
   procedures carrying the same shape shipped with the 2026-08-04 apply, as a
   known and accepted limitation rather than an oversight. It is not
   reachable: the room is flag-off, so no member can call them. The decision
   point is therefore no longer "before this file is applied" - applying this
   file adds seven more procedures with the same shape to a database that
   already has six - but BEFORE PEERSLATE_OPPORTUNITY_SLATE_ENABLED is turned
   on for anyone. That is the one open question left on this file.

   Rollback: PS-OPPSLATE-001_opportunity_slate_rollback.sql
   Verification: ../../Verification/PS-OPPSLATE-001_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53400, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-001')
        THROW 53401, 'PS-PLAT-001 must be applied before PS-OPPSLATE-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002')
        THROW 53402, 'PS-PLAT-002 must be applied before PS-OPPSLATE-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 53403, 'PS-AUTH-001 must be applied before PS-OPPSLATE-001.', 1;
    /* Handoff section 8: Opportunity Slate's evidence reads depend on the
       Workshop knowledge store. Slice OS-1 reads no evidence yet, but the
       dependency is part of this migration's contract and is guarded here
       so a later slice cannot discover it missing at runtime. */
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-WORKSHOP-001')
        THROW 53404, 'PS-WORKSHOP-001 must be applied before PS-OPPSLATE-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
       OR OBJECT_ID(N'dbo.knowledge_items', N'U') IS NULL
        THROW 53405, 'The owner, profile, audit, or Workshop knowledge foundation is missing.', 1;

    IF OBJECT_ID(N'dbo.opportunity_working_sessions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_working_sessions
        (
            working_session_id bigint IDENTITY(1,1) NOT NULL,
            working_session_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_working_sessions_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            /* Handoff section 2's state machine, narrowed to the states
               that can exist before requirement interpretation ships.
               role_intake is the schema default for a session that exists
               without a source; OS-1 never persists one, because a
               working session is created together with its first source
               and destroyed when that source is deleted. */
            workbench_state nvarchar(40) NOT NULL
                CONSTRAINT DF_opportunity_working_sessions_state DEFAULT N'role_intake',
            /* There is no audience model on this surface, by design
               (handoff section 8). Hard-locked by CHECK, not by a default
               that could silently change, exactly like
               knowledge_items.visibility. */
            visibility nvarchar(20) NOT NULL
                CONSTRAINT DF_opportunity_working_sessions_visibility DEFAULT N'private',
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_working_sessions_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_working_sessions_updated DEFAULT SYSUTCDATETIME(),
            expires_at_utc datetime2(7) NOT NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_working_sessions PRIMARY KEY (working_session_id),
            CONSTRAINT UQ_opportunity_working_sessions_key UNIQUE (working_session_key),
            /* One active Opportunity Slate per member in v1 (owner
               decision, handoff section 17-Q2). */
            CONSTRAINT UQ_opportunity_working_sessions_owner UNIQUE (owner_profile_id),
            CONSTRAINT UQ_opportunity_working_sessions_id_owner
                UNIQUE (working_session_id, owner_profile_id),
            CONSTRAINT FK_opportunity_working_sessions_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_opportunity_working_sessions_state CHECK
                (workbench_state IN (N'role_intake', N'review_source', N'source_confirmed',
                                     N'review_requirements', N'requirements_confirmed')),
            CONSTRAINT CK_opportunity_working_sessions_visibility CHECK (visibility = N'private'),
            CONSTRAINT CK_opportunity_working_sessions_expiry CHECK (expires_at_utc > created_at_utc)
        );

        CREATE INDEX IX_opportunity_working_sessions_expiry
            ON dbo.opportunity_working_sessions(expires_at_utc)
            INCLUDE (owner_profile_id, working_session_key);
    END;

    IF OBJECT_ID(N'dbo.opportunity_sources', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_sources
        (
            opportunity_source_id bigint IDENTITY(1,1) NOT NULL,
            source_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_sources_key DEFAULT NEWSEQUENTIALID(),
            working_session_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            current_version_number int NOT NULL
                CONSTRAINT DF_opportunity_sources_current_version DEFAULT 1,
            confirmed_version_number int NULL,
            confirmed_by_user_id int NULL,
            confirmed_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_sources_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_sources_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_sources PRIMARY KEY (opportunity_source_id),
            CONSTRAINT UQ_opportunity_sources_key UNIQUE (source_key),
            /* One employer source per working session in v1 - the member
               brings in one role at a time (handoff section 1). */
            CONSTRAINT UQ_opportunity_sources_session UNIQUE (working_session_id),
            CONSTRAINT UQ_opportunity_sources_id_owner
                UNIQUE (opportunity_source_id, owner_profile_id),
            CONSTRAINT FK_opportunity_sources_session FOREIGN KEY (working_session_id, owner_profile_id)
                REFERENCES dbo.opportunity_working_sessions(working_session_id, owner_profile_id),
            CONSTRAINT FK_opportunity_sources_confirmer FOREIGN KEY (confirmed_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_sources_current_version CHECK (current_version_number > 0),
            /* Either the source is unconfirmed (the whole confirmation
               triple is null) or it is confirmed at exactly the CURRENT
               version. Replacing or correcting the wording clears the
               triple, so a confirmed source can never describe wording
               the member never confirmed (handoff section 7's currency
               rule, applied at checkpoint 1). */
            CONSTRAINT CK_opportunity_sources_confirmation_state CHECK
            (
                (
                    confirmed_version_number IS NULL
                    AND confirmed_by_user_id IS NULL
                    AND confirmed_at_utc IS NULL
                )
                OR
                (
                    confirmed_version_number = current_version_number
                    AND confirmed_by_user_id IS NOT NULL
                    AND confirmed_at_utc IS NOT NULL
                )
            )
        );

        CREATE INDEX IX_opportunity_sources_owner
            ON dbo.opportunity_sources(owner_profile_id, opportunity_source_id)
            INCLUDE (source_key, working_session_id, current_version_number);
    END;

    IF OBJECT_ID(N'dbo.opportunity_source_versions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_source_versions
        (
            opportunity_source_version_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_source_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            version_number int NOT NULL,
            capture_method nvarchar(20) NOT NULL
                CONSTRAINT DF_opportunity_source_versions_capture DEFAULT N'pasted',
            /* Write-once. No procedure in this migration ever updates
               original_text or original_sha256; the owner-isolation
               verifier greps for that guarantee. */
            original_text nvarchar(max) NOT NULL,
            original_sha256 char(64) NOT NULL,
            /* The member's manual correction of the displayed wording.
               NULL means "the member has not changed anything", and the
               reader renders original_text. Never a replacement for the
               column above. */
            member_corrected_text nvarchar(max) NULL,
            corrected_by_user_id int NULL,
            corrected_at_utc datetime2(7) NULL,
            /* Replay key for a double-submitted intake POST. Stored on the
               version row itself rather than in a separate ledger table,
               because a version IS the created artifact here - there is no
               durable parent record for a ledger to point at until OS-4
               introduces the saved slate. */
            idempotency_key nvarchar(200) NOT NULL,
            captured_by_user_id int NOT NULL,
            captured_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_source_versions_captured DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_source_versions PRIMARY KEY (opportunity_source_version_id),
            CONSTRAINT UQ_opportunity_source_versions_number
                UNIQUE (opportunity_source_id, version_number),
            CONSTRAINT UQ_opportunity_source_versions_owner_key
                UNIQUE (owner_profile_id, idempotency_key),
            /* The owner-scoped candidate key every child of this table needs.
               Slice OS-2's opportunity_source_reviews carries a composite
               FOREIGN KEY (opportunity_source_version_id, owner_profile_id)
               so a review can never be attached across owners, and SQL Server
               requires a matching UNIQUE on the referenced side. Slice OS-1
               omitted it because nothing referenced this table yet; without
               it the whole migration fails at APPLY time with "no primary or
               candidate keys ... match the referencing column list". Every
               other table in this file already carries its _id_owner twin. */
            CONSTRAINT UQ_opportunity_source_versions_id_owner
                UNIQUE (opportunity_source_version_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_versions_source FOREIGN KEY (opportunity_source_id, owner_profile_id)
                REFERENCES dbo.opportunity_sources(opportunity_source_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_versions_capturer FOREIGN KEY (captured_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_opportunity_source_versions_corrector FOREIGN KEY (corrected_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_source_versions_number CHECK (version_number > 0),
            CONSTRAINT CK_opportunity_source_versions_capture_method CHECK
                (capture_method IN (N'pasted', N'dictated', N'uploaded', N'imported')),
            /* UTF-16 code-unit limits (DATALENGTH/2), the house idiom, and
               the exact bound services/opportunity_slate_service.py
               enforces before any round trip. 20000 units is the hard
               server-side cap that handoff section 18 safeguard 2
               requires on role text. */
            CONSTRAINT CK_opportunity_source_versions_original_length CHECK
                (DATALENGTH(original_text) / 2 BETWEEN 1 AND 20000),
            CONSTRAINT CK_opportunity_source_versions_corrected_length CHECK
                (member_corrected_text IS NULL
                 OR DATALENGTH(member_corrected_text) / 2 BETWEEN 1 AND 20000),
            CONSTRAINT CK_opportunity_source_versions_idempotency_length CHECK
                (DATALENGTH(idempotency_key) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_source_versions_correction_pair CHECK
            (
                (member_corrected_text IS NULL AND corrected_by_user_id IS NULL AND corrected_at_utc IS NULL)
                OR
                (member_corrected_text IS NOT NULL AND corrected_by_user_id IS NOT NULL AND corrected_at_utc IS NOT NULL)
            )
        );

        CREATE INDEX IX_opportunity_source_versions_current
            ON dbo.opportunity_source_versions(opportunity_source_id, version_number DESC)
            INCLUDE (capture_method, captured_at_utc, corrected_at_utc);
    END;

    /* ------------------------------------------------------------
       SLICE OS-2 CANDIDATE-KEY UPGRADE (isolated SQL gate, defect 1).

       The composite UNIQUE immediately above is new in slice OS-2, and it is
       a PRECONDITION for creating opportunity_source_reviews below rather
       than a refinement of it. A database already carrying the slice OS-1
       revision has opportunity_source_versions WITHOUT that key, and the
       CREATE TABLE that now declares it only runs when the table is absent -
       so on an OS-1 database this file would reach the reviews table and
       fail outright:

         There are no primary or candidate keys in the referenced table
         'dbo.opportunity_source_versions' that match the referencing column
         list in the foreign key 'FK_opportunity_source_reviews_version'.

       This block therefore has to run BEFORE the first table that references
       it, not with the state-CHECK repair further down. It is a no-op on a
       fresh apply because the constraint was created moments ago, and it can
       never fail validation on an OS-1 database: opportunity_source_version_id
       is already the primary key, so any pair containing it is unique too.
       ------------------------------------------------------------ */
    IF OBJECT_ID(N'dbo.opportunity_source_versions', N'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.key_constraints
            WHERE parent_object_id = OBJECT_ID(N'dbo.opportunity_source_versions')
              AND name = N'UQ_opportunity_source_versions_id_owner'
       )
        ALTER TABLE dbo.opportunity_source_versions
            ADD CONSTRAINT UQ_opportunity_source_versions_id_owner
                UNIQUE (opportunity_source_version_id, owner_profile_id);

    /* ------------------------------------------------------------
       SLICE OS-2 — AI proposals and the member's decisions on them.

       THE THIRD DATA CLASS. Handoff section 1 names three kinds of thing
       this room holds and forbids collapsing any of them into another: the
       employer's captured wording, the member's own input, and AI
       proposals. Slice OS-1 kept the first two apart (original_text is
       write-once; member_corrected_text is a separate nullable column on
       the same row). The tables below are the third class, and they are
       SEPARATE TABLES rather than columns on the source, so no proposal can
       ever be written into a field the member or the employer owns.

       Within them the same rule applies again: proposed_class and
       proposed_structure_json are the model's reading, member_class and
       member_clarification are the member's, and no procedure in this file
       writes one from the other. That is what makes "PeerSlate proposed X,
       the member says Y" a question the data can still answer.

       STILL NO SCORE. No aggregate score, percentage, recommendation,
       employer prediction, or traffic-light verdict column exists in any
       table here, and none may ever be added. The Review Requirements
       screen counts statements per class; that is the entire accounting.
       ------------------------------------------------------------ */

    IF OBJECT_ID(N'dbo.opportunity_source_reviews', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_source_reviews
        (
            opportunity_source_review_id bigint IDENTITY(1,1) NOT NULL,
            review_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_source_reviews_key DEFAULT NEWSEQUENTIALID(),
            opportunity_source_version_id bigint NOT NULL,
            /* Denormalized from the version row so every owner-scoped read
               and the superseded-version cleanup below can be expressed
               without a third join. Both are re-asserted against
               owner_profile_id regardless. */
            opportunity_source_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            source_version_number int NOT NULL,
            /* Provenance travels with the proposal (handoff section 10): the
               exact model and the exact prompt-contract version that
               produced the concerns below. */
            model_name nvarchar(200) NOT NULL,
            prompt_contract_version nvarchar(100) NOT NULL,
            concern_count int NOT NULL
                CONSTRAINT DF_opportunity_source_reviews_count DEFAULT 0,
            reviewed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_source_reviews_reviewed DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_source_reviews PRIMARY KEY (opportunity_source_review_id),
            CONSTRAINT UQ_opportunity_source_reviews_key UNIQUE (review_key),
            /* One review per captured version. Re-running the wording review
               replaces it rather than stacking a second opinion beside the
               first. */
            CONSTRAINT UQ_opportunity_source_reviews_version UNIQUE (opportunity_source_version_id),
            CONSTRAINT UQ_opportunity_source_reviews_id_owner
                UNIQUE (opportunity_source_review_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_reviews_version FOREIGN KEY (opportunity_source_version_id, owner_profile_id)
                REFERENCES dbo.opportunity_source_versions(opportunity_source_version_id, owner_profile_id),
            CONSTRAINT CK_opportunity_source_reviews_count CHECK (concern_count BETWEEN 0 AND 20),
            CONSTRAINT CK_opportunity_source_reviews_version_number CHECK (source_version_number > 0),
            CONSTRAINT CK_opportunity_source_reviews_model_length CHECK
                (DATALENGTH(model_name) / 2 BETWEEN 1 AND 100),
            CONSTRAINT CK_opportunity_source_reviews_contract_length CHECK
                (DATALENGTH(prompt_contract_version) / 2 BETWEEN 1 AND 60)
        );

        CREATE INDEX IX_opportunity_source_reviews_source
            ON dbo.opportunity_source_reviews(opportunity_source_id, owner_profile_id)
            INCLUDE (source_version_number, review_key);
    END;

    IF OBJECT_ID(N'dbo.opportunity_source_concerns', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_source_concerns
        (
            opportunity_source_concern_id bigint IDENTITY(1,1) NOT NULL,
            concern_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_source_concerns_key DEFAULT NEWSEQUENTIALID(),
            opportunity_source_review_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            ordinal int NOT NULL,
            /* The proposal: where the model pointed, what it quoted, and
               why. quoted_text holds the employer's characters at that span
               as they were stored, not as the model retyped them, so a
               concern can never become a back door for rewritten wording. */
            span_start int NOT NULL,
            span_length int NOT NULL,
            quoted_text nvarchar(1000) NOT NULL,
            concern_reason nvarchar(500) NOT NULL,
            /* The member's decision, in its own columns. "pending" is where
               every proposal starts and only the member moves it. */
            member_resolution nvarchar(20) NOT NULL
                CONSTRAINT DF_opportunity_source_concerns_resolution DEFAULT N'pending',
            member_corrected_text nvarchar(max) NULL,
            resolved_by_user_id int NULL,
            resolved_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_source_concerns PRIMARY KEY (opportunity_source_concern_id),
            CONSTRAINT UQ_opportunity_source_concerns_key UNIQUE (concern_key),
            CONSTRAINT UQ_opportunity_source_concerns_ordinal
                UNIQUE (opportunity_source_review_id, ordinal),
            CONSTRAINT UQ_opportunity_source_concerns_id_owner
                UNIQUE (opportunity_source_concern_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_concerns_review FOREIGN KEY (opportunity_source_review_id, owner_profile_id)
                REFERENCES dbo.opportunity_source_reviews(opportunity_source_review_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_concerns_resolver FOREIGN KEY (resolved_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_source_concerns_resolution CHECK
                (member_resolution IN (N'pending', N'applied', N'dismissed')),
            CONSTRAINT CK_opportunity_source_concerns_span CHECK
                (span_start >= 0 AND span_length > 0),
            CONSTRAINT CK_opportunity_source_concerns_quote_length CHECK
                (DATALENGTH(quoted_text) / 2 BETWEEN 1 AND 600),
            CONSTRAINT CK_opportunity_source_concerns_reason_length CHECK
                (DATALENGTH(concern_reason) / 2 BETWEEN 1 AND 240),
            CONSTRAINT CK_opportunity_source_concerns_corrected_length CHECK
                (member_corrected_text IS NULL
                 OR DATALENGTH(member_corrected_text) / 2 BETWEEN 1 AND 20000),
            /* A resolution and its provenance move together, and only an
               applied concern carries replacement wording. A dismissed one
               changed nothing, so it must not look like it did. */
            CONSTRAINT CK_opportunity_source_concerns_resolution_pair CHECK
            (
                (member_resolution = N'pending'
                 AND member_corrected_text IS NULL
                 AND resolved_by_user_id IS NULL
                 AND resolved_at_utc IS NULL)
                OR
                (member_resolution = N'dismissed'
                 AND member_corrected_text IS NULL
                 AND resolved_by_user_id IS NOT NULL
                 AND resolved_at_utc IS NOT NULL)
                OR
                (member_resolution = N'applied'
                 AND member_corrected_text IS NOT NULL
                 AND resolved_by_user_id IS NOT NULL
                 AND resolved_at_utc IS NOT NULL)
            )
        );

        CREATE INDEX IX_opportunity_source_concerns_review
            ON dbo.opportunity_source_concerns(opportunity_source_review_id, ordinal)
            INCLUDE (concern_key, member_resolution);
    END;

    IF OBJECT_ID(N'dbo.opportunity_requirement_sets', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_requirement_sets
        (
            opportunity_requirement_set_id bigint IDENTITY(1,1) NOT NULL,
            requirement_set_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_requirement_sets_key DEFAULT NEWSEQUENTIALID(),
            working_session_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            current_version_number int NOT NULL
                CONSTRAINT DF_opportunity_requirement_sets_current DEFAULT 1,
            confirmed_version_number int NULL,
            confirmed_by_user_id int NULL,
            confirmed_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_requirement_sets_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_requirement_sets_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_requirement_sets PRIMARY KEY (opportunity_requirement_set_id),
            CONSTRAINT UQ_opportunity_requirement_sets_key UNIQUE (requirement_set_key),
            /* One requirement set per working session, matching the
               one-slate-per-member rule (owner decision, handoff 17-Q2). */
            CONSTRAINT UQ_opportunity_requirement_sets_session UNIQUE (working_session_id),
            CONSTRAINT UQ_opportunity_requirement_sets_id_owner
                UNIQUE (opportunity_requirement_set_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_sets_session FOREIGN KEY (working_session_id, owner_profile_id)
                REFERENCES dbo.opportunity_working_sessions(working_session_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_sets_confirmer FOREIGN KEY (confirmed_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_requirement_sets_current CHECK (current_version_number > 0),
            /* Checkpoint 2's exact analogue of the source's confirmation
               CHECK: either nothing is confirmed, or the CURRENT version is,
               with its provenance. A correction or a re-read clears the
               triple, so a confirmed set can never describe a reading the
               member never confirmed. */
            CONSTRAINT CK_opportunity_requirement_sets_confirmation_state CHECK
            (
                (
                    confirmed_version_number IS NULL
                    AND confirmed_by_user_id IS NULL
                    AND confirmed_at_utc IS NULL
                )
                OR
                (
                    confirmed_version_number = current_version_number
                    AND confirmed_by_user_id IS NOT NULL
                    AND confirmed_at_utc IS NOT NULL
                )
            )
        );

        CREATE INDEX IX_opportunity_requirement_sets_owner
            ON dbo.opportunity_requirement_sets(owner_profile_id, opportunity_requirement_set_id)
            INCLUDE (requirement_set_key, working_session_id);
    END;

    IF OBJECT_ID(N'dbo.opportunity_requirement_set_versions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_requirement_set_versions
        (
            opportunity_requirement_set_version_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_requirement_set_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            version_number int NOT NULL,
            /* Which captured source version this reading was made from.
               A reading is only ever shown against the wording it was read
               out of. */
            source_version_number int NOT NULL,
            model_name nvarchar(200) NOT NULL,
            prompt_contract_version nvarchar(100) NOT NULL,
            statement_count int NOT NULL,
            proposed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_requirement_set_versions_proposed DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_requirement_set_versions PRIMARY KEY (opportunity_requirement_set_version_id),
            CONSTRAINT UQ_opportunity_requirement_set_versions_number
                UNIQUE (opportunity_requirement_set_id, version_number),
            CONSTRAINT UQ_opportunity_requirement_set_versions_id_owner
                UNIQUE (opportunity_requirement_set_version_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_set_versions_set FOREIGN KEY (opportunity_requirement_set_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_sets(opportunity_requirement_set_id, owner_profile_id),
            CONSTRAINT CK_opportunity_requirement_set_versions_number CHECK (version_number > 0),
            CONSTRAINT CK_opportunity_requirement_set_versions_source CHECK (source_version_number > 0),
            CONSTRAINT CK_opportunity_requirement_set_versions_count CHECK
                (statement_count BETWEEN 1 AND 60),
            CONSTRAINT CK_opportunity_requirement_set_versions_model_length CHECK
                (DATALENGTH(model_name) / 2 BETWEEN 1 AND 100),
            CONSTRAINT CK_opportunity_requirement_set_versions_contract_length CHECK
                (DATALENGTH(prompt_contract_version) / 2 BETWEEN 1 AND 60)
        );
    END;

    IF OBJECT_ID(N'dbo.opportunity_requirement_statements', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_requirement_statements
        (
            opportunity_requirement_statement_id bigint IDENTITY(1,1) NOT NULL,
            statement_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_requirement_statements_key DEFAULT NEWSEQUENTIALID(),
            opportunity_requirement_set_version_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            ordinal int NOT NULL,
            /* The employer's own wording for this statement, and where it
               sits in the confirmed source. Write-once: no procedure in this
               file ever updates employer_text. */
            span_start int NOT NULL,
            span_length int NOT NULL,
            employer_text nvarchar(2000) NOT NULL,
            /* The AI proposal. */
            proposed_class nvarchar(40) NOT NULL,
            proposed_explanation nvarchar(1000) NOT NULL,
            proposed_structure_json nvarchar(4000) NOT NULL,
            /* The member's decision, in its own columns, never written from
               the proposal and never overwriting it. */
            member_class nvarchar(40) NULL,
            member_clarification nvarchar(2000) NULL,
            member_updated_by_user_id int NULL,
            member_updated_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_requirement_statements PRIMARY KEY (opportunity_requirement_statement_id),
            CONSTRAINT UQ_opportunity_requirement_statements_key UNIQUE (statement_key),
            CONSTRAINT UQ_opportunity_requirement_statements_ordinal
                UNIQUE (opportunity_requirement_set_version_id, ordinal),
            CONSTRAINT UQ_opportunity_requirement_statements_id_owner
                UNIQUE (opportunity_requirement_statement_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_statements_version FOREIGN KEY (opportunity_requirement_set_version_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_set_versions(opportunity_requirement_set_version_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_statements_corrector FOREIGN KEY (member_updated_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_requirement_statements_ordinal CHECK (ordinal > 0),
            CONSTRAINT CK_opportunity_requirement_statements_span CHECK
                (span_start >= 0 AND span_length > 0),
            /* The four classes, CHECK-pinned in both columns. Required,
               Preferred, Responsibilities, and Informational statements are
               the whole vocabulary; there is no fifth value and no ordering
               among them. */
            CONSTRAINT CK_opportunity_requirement_statements_proposed_class CHECK
                (proposed_class IN (N'required_qualification', N'preferred_qualification',
                                    N'responsibility', N'informational_statement')),
            CONSTRAINT CK_opportunity_requirement_statements_member_class CHECK
                (member_class IS NULL
                 OR member_class IN (N'required_qualification', N'preferred_qualification',
                                     N'responsibility', N'informational_statement')),
            CONSTRAINT CK_opportunity_requirement_statements_text_length CHECK
                (DATALENGTH(employer_text) / 2 BETWEEN 1 AND 1200),
            CONSTRAINT CK_opportunity_requirement_statements_explanation_length CHECK
                (DATALENGTH(proposed_explanation) / 2 BETWEEN 1 AND 400),
            CONSTRAINT CK_opportunity_requirement_statements_structure_length CHECK
                (DATALENGTH(proposed_structure_json) / 2 BETWEEN 1 AND 4000),
            CONSTRAINT CK_opportunity_requirement_statements_clarification_length CHECK
                (member_clarification IS NULL
                 OR DATALENGTH(member_clarification) / 2 BETWEEN 1 AND 2000),
            /* Member input and its provenance move together. */
            CONSTRAINT CK_opportunity_requirement_statements_member_pair CHECK
            (
                (member_class IS NULL AND member_clarification IS NULL
                 AND member_updated_by_user_id IS NULL AND member_updated_at_utc IS NULL)
                OR
                (member_updated_by_user_id IS NOT NULL AND member_updated_at_utc IS NOT NULL)
            )
        );

        CREATE INDEX IX_opportunity_requirement_statements_version
            ON dbo.opportunity_requirement_statements(opportunity_requirement_set_version_id, ordinal)
            INCLUDE (statement_key, proposed_class, member_class);
    END;

    /* ------------------------------------------------------------
       SLICE OS-3 — the alignment analysis and the member''s responses.

       THE FOURTH DATA CLASS ARRIVES HERE. Slices OS-1 and OS-2 kept the
       employer''s captured wording, the member''s own input, and PeerSlate''s
       AI proposals in separate tables. Slice OS-3 adds the member''s
       AUTHORIZED EVIDENCE, and it is referenced rather than copied: an
       analysis citation stores the evidence''s key and its pinned version
       plus a bounded verbatim excerpt for identifiability, and nothing here
       writes a single Workshop or Moment row. The member''s library remains
       the one authoritative place their evidence lives.

       STILL NO SCORE, AND NOW IT MATTERS MOST. This is the first place in
       the schema that holds a result about a PERSON rather than about a job
       advert. No aggregate score, percentage, ranking, recommendation,
       employer prediction, or traffic-light verdict column exists in any
       table here, and none may ever be added.
       opportunity_analysis_statements.derived_status is per-statement and is
       exactly the accounting image 04 draws (three named states, counted per
       class); it is not an aggregate and it is not the model''s opinion. It
       is COMPUTED by the application from the citations below and the
       member-confirmed AND/OR structure — see the composition-boundary block
       in services/opportunity_analysis_service.py. There is deliberately no
       column anywhere in this file that a sentence about the member could be
       written into.
       ------------------------------------------------------------ */

    IF OBJECT_ID(N'dbo.opportunity_analyses', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_analyses
        (
            opportunity_analysis_id bigint IDENTITY(1,1) NOT NULL,
            analysis_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_analyses_key DEFAULT NEWSEQUENTIALID(),
            /* Pinned to the exact requirement-set version it was computed
               from. A reading of superseded requirements is never shown. */
            opportunity_requirement_set_version_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            source_version_number int NOT NULL,
            requirement_version_number int NOT NULL,
            /* Provenance travels with the analysis (handoff section 10). */
            model_name nvarchar(200) NOT NULL,
            prompt_contract_version nvarchar(100) NOT NULL,
            /* How many authorized evidence items were in the grounding
               allowlist. A count of the member''s own inputs, not a measure
               of them. */
            evidence_considered_count int NOT NULL
                CONSTRAINT DF_opportunity_analyses_evidence DEFAULT 0,
            qualification_count int NOT NULL,
            analyzed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_analyses_analyzed DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_analyses PRIMARY KEY (opportunity_analysis_id),
            CONSTRAINT UQ_opportunity_analyses_key UNIQUE (analysis_key),
            /* One current analysis per requirement-set version. Re-running
               replaces it rather than stacking a second opinion beside the
               first; the durable, versioned record is OS-4''s saved slate. */
            CONSTRAINT UQ_opportunity_analyses_version
                UNIQUE (opportunity_requirement_set_version_id),
            CONSTRAINT UQ_opportunity_analyses_id_owner
                UNIQUE (opportunity_analysis_id, owner_profile_id),
            CONSTRAINT FK_opportunity_analyses_version FOREIGN KEY (opportunity_requirement_set_version_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_set_versions(opportunity_requirement_set_version_id, owner_profile_id),
            CONSTRAINT CK_opportunity_analyses_source_version CHECK (source_version_number > 0),
            CONSTRAINT CK_opportunity_analyses_requirement_version CHECK (requirement_version_number > 0),
            CONSTRAINT CK_opportunity_analyses_evidence_count CHECK
                (evidence_considered_count BETWEEN 0 AND 24),
            CONSTRAINT CK_opportunity_analyses_qualification_count CHECK
                (qualification_count BETWEEN 1 AND 40),
            CONSTRAINT CK_opportunity_analyses_model_length CHECK
                (DATALENGTH(model_name) / 2 BETWEEN 1 AND 100),
            CONSTRAINT CK_opportunity_analyses_contract_length CHECK
                (DATALENGTH(prompt_contract_version) / 2 BETWEEN 1 AND 60)
        );

        CREATE INDEX IX_opportunity_analyses_owner
            ON dbo.opportunity_analyses(owner_profile_id, opportunity_analysis_id)
            INCLUDE (analysis_key, opportunity_requirement_set_version_id);
    END;

    IF OBJECT_ID(N'dbo.opportunity_analysis_statements', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_analysis_statements
        (
            opportunity_analysis_statement_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_analysis_id bigint NOT NULL,
            /* The qualification this result is about, referenced rather than
               copied: its employer wording, its proposed reading and the
               member''s own correction all stay on their own row. */
            opportunity_requirement_statement_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            ordinal int NOT NULL,
            /* Three named per-statement states, and nothing else. This column
               is the whole of the locked accounting. It is NOT a score: it
               carries no order, no weight, and no number, and the application
               derives it from the citations below rather than accepting it
               from a model. */
            derived_status nvarchar(30) NOT NULL,
            citation_count int NOT NULL
                CONSTRAINT DF_opportunity_analysis_statements_citations DEFAULT 0,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_analysis_statements PRIMARY KEY (opportunity_analysis_statement_id),
            CONSTRAINT UQ_opportunity_analysis_statements_statement
                UNIQUE (opportunity_analysis_id, opportunity_requirement_statement_id),
            CONSTRAINT UQ_opportunity_analysis_statements_ordinal
                UNIQUE (opportunity_analysis_id, ordinal),
            CONSTRAINT UQ_opportunity_analysis_statements_id_owner
                UNIQUE (opportunity_analysis_statement_id, owner_profile_id),
            CONSTRAINT FK_opportunity_analysis_statements_analysis FOREIGN KEY (opportunity_analysis_id, owner_profile_id)
                REFERENCES dbo.opportunity_analyses(opportunity_analysis_id, owner_profile_id),
            CONSTRAINT FK_opportunity_analysis_statements_statement FOREIGN KEY (opportunity_requirement_statement_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_statements(opportunity_requirement_statement_id, owner_profile_id),
            CONSTRAINT CK_opportunity_analysis_statements_ordinal CHECK (ordinal > 0),
            CONSTRAINT CK_opportunity_analysis_statements_status CHECK
                (derived_status IN (N'supported', N'partially_supported',
                                    N'not_enough_information')),
            CONSTRAINT CK_opportunity_analysis_statements_citation_count CHECK
                (citation_count BETWEEN 0 AND 24),
            /* A result with no citation can only be "not enough information",
               and one WITH a citation can never be. The screen''s three states
               therefore cannot drift away from the evidence behind them. */
            CONSTRAINT CK_opportunity_analysis_statements_citation_pair CHECK
            (
                (citation_count = 0 AND derived_status = N'not_enough_information')
                OR
                (citation_count > 0 AND derived_status <> N'not_enough_information')
            )
        );

        CREATE INDEX IX_opportunity_analysis_statements_analysis
            ON dbo.opportunity_analysis_statements(opportunity_analysis_id, ordinal)
            INCLUDE (opportunity_requirement_statement_id, derived_status);
    END;

    IF OBJECT_ID(N'dbo.opportunity_analysis_citations', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_analysis_citations
        (
            opportunity_analysis_citation_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_analysis_statement_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            ordinal int NOT NULL,
            /* Which clause of the member-confirmed AND/OR structure, and
               which of that clause''s own words the cited evidence covers.
               covered_text is a verbatim span of the EMPLOYER''s clause,
               validated before it reaches here; it is never model prose. */
            clause_ordinal int NOT NULL,
            covered_text nvarchar(400) NOT NULL,
            /* The evidence REFERENCE. The full enum is the architectural
               contract (handoff section 8); slice OS-3 only ever writes
               N''knowledge_item'', exactly as OS-1 pinned capture_method to
               the full enum while only ever writing N''pasted''. */
            evidence_kind nvarchar(30) NOT NULL,
            evidence_key uniqueidentifier NOT NULL,
            evidence_version int NOT NULL,
            /* A pinned copy of the title and a bounded verbatim excerpt, held
               only so the member can still identify WHAT the analysis read
               after they edit the item. The evidence itself is never copied
               and is never written by this room. */
            evidence_title nvarchar(200) NOT NULL,
            excerpt nvarchar(800) NOT NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_analysis_citations PRIMARY KEY (opportunity_analysis_citation_id),
            CONSTRAINT UQ_opportunity_analysis_citations_ordinal
                UNIQUE (opportunity_analysis_statement_id, ordinal),
            CONSTRAINT UQ_opportunity_analysis_citations_id_owner
                UNIQUE (opportunity_analysis_citation_id, owner_profile_id),
            CONSTRAINT FK_opportunity_analysis_citations_statement FOREIGN KEY (opportunity_analysis_statement_id, owner_profile_id)
                REFERENCES dbo.opportunity_analysis_statements(opportunity_analysis_statement_id, owner_profile_id),
            CONSTRAINT CK_opportunity_analysis_citations_ordinal CHECK (ordinal > 0),
            CONSTRAINT CK_opportunity_analysis_citations_clause CHECK (clause_ordinal > 0),
            CONSTRAINT CK_opportunity_analysis_citations_kind CHECK
                (evidence_kind IN (N'knowledge_item', N'moment')),
            CONSTRAINT CK_opportunity_analysis_citations_evidence_version CHECK
                (evidence_version > 0),
            CONSTRAINT CK_opportunity_analysis_citations_covered_length CHECK
                (DATALENGTH(covered_text) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_analysis_citations_title_length CHECK
                (DATALENGTH(evidence_title) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_analysis_citations_excerpt_length CHECK
                (DATALENGTH(excerpt) / 2 BETWEEN 1 AND 400)
        );

        CREATE INDEX IX_opportunity_analysis_citations_statement
            ON dbo.opportunity_analysis_citations(opportunity_analysis_statement_id, ordinal)
            INCLUDE (evidence_key, evidence_version, clause_ordinal);
    END;

    IF OBJECT_ID(N'dbo.opportunity_responses', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_responses
        (
            opportunity_response_id bigint IDENTITY(1,1) NOT NULL,
            response_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_responses_key DEFAULT NEWSEQUENTIALID(),
            /* Attached to the QUALIFICATION, not to an analysis run. A member
               response is member-authored context about the employer''s
               requirement; re-running the analysis must not discard it, so it
               deliberately does not reference dbo.opportunity_analyses. */
            opportunity_requirement_statement_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            response_kind nvarchar(30) NOT NULL,
            response_text nvarchar(max) NULL,
            /* The Workshop provenance enum. Dictation lands with OS-5, so
               slice OS-3 only ever writes N''typed''. */
            authored_via nvarchar(30) NOT NULL
                CONSTRAINT DF_opportunity_responses_authored DEFAULT N'typed',
            connected_evidence_kind nvarchar(30) NULL,
            connected_evidence_key uniqueidentifier NULL,
            connected_evidence_version int NULL,
            connected_evidence_title nvarchar(200) NULL,
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_responses_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_responses_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_responses PRIMARY KEY (opportunity_response_id),
            CONSTRAINT UQ_opportunity_responses_key UNIQUE (response_key),
            /* One current response per qualification. Changing it replaces
               it; the member is never shown two answers to one question. */
            CONSTRAINT UQ_opportunity_responses_statement
                UNIQUE (opportunity_requirement_statement_id),
            CONSTRAINT UQ_opportunity_responses_id_owner
                UNIQUE (opportunity_response_id, owner_profile_id),
            CONSTRAINT FK_opportunity_responses_statement FOREIGN KEY (opportunity_requirement_statement_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_statements(opportunity_requirement_statement_id, owner_profile_id),
            CONSTRAINT FK_opportunity_responses_author FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_responses_kind CHECK
                (response_kind IN (N'tell_more', N'connect_evidence', N'real_example',
                                   N'confirm_not_have', N'skip')),
            CONSTRAINT CK_opportunity_responses_authored_via CHECK
                (authored_via IN (N'typed', N'spoken')),
            CONSTRAINT CK_opportunity_responses_text_length CHECK
                (response_text IS NULL
                 OR DATALENGTH(response_text) / 2 BETWEEN 1 AND 4000),
            CONSTRAINT CK_opportunity_responses_title_length CHECK
                (connected_evidence_title IS NULL
                 OR DATALENGTH(connected_evidence_title) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_responses_connected_kind CHECK
                (connected_evidence_kind IS NULL
                 OR connected_evidence_kind IN (N'knowledge_item', N'moment')),
            /* Each response kind carries exactly what it means, and nothing
               else. "I do not have this experience" and "skip" carry no text
               and no evidence, so neither can be made to look like an answer
               the member did not give. */
            CONSTRAINT CK_opportunity_responses_shape CHECK
            (
                (
                    response_kind IN (N'tell_more', N'real_example')
                    AND response_text IS NOT NULL
                    AND connected_evidence_kind IS NULL
                    AND connected_evidence_key IS NULL
                    AND connected_evidence_version IS NULL
                    AND connected_evidence_title IS NULL
                )
                OR
                (
                    response_kind = N'connect_evidence'
                    AND response_text IS NULL
                    AND connected_evidence_kind IS NOT NULL
                    AND connected_evidence_key IS NOT NULL
                    AND connected_evidence_version IS NOT NULL
                    AND connected_evidence_title IS NOT NULL
                )
                OR
                (
                    response_kind IN (N'confirm_not_have', N'skip')
                    AND response_text IS NULL
                    AND connected_evidence_kind IS NULL
                    AND connected_evidence_key IS NULL
                    AND connected_evidence_version IS NULL
                    AND connected_evidence_title IS NULL
                )
            ),
            CONSTRAINT CK_opportunity_responses_connected_version CHECK
                (connected_evidence_version IS NULL OR connected_evidence_version > 0)
        );

        CREATE INDEX IX_opportunity_responses_owner
            ON dbo.opportunity_responses(owner_profile_id, opportunity_requirement_statement_id)
            INCLUDE (response_key, response_kind);
    END;

    /* ------------------------------------------------------------
       SLICE OS-2 CONSTRAINT UPGRADE (independent review, finding F4).

       Slice OS-2 widened CK_opportunity_working_sessions_state with the two
       checkpoint-2 states, review_requirements and requirements_confirmed.
       That widened CHECK is written inline in the CREATE TABLE above, which
       only runs when the table does not exist. A database already carrying
       the slice OS-1 revision therefore skipped it entirely: this file
       created the new proposal tables and the new procedures, reported
       success, and then failed at RUNTIME the first time a member reached
       checkpoint 2, because usp_SaveOpportunityRequirementsForOwner and
       usp_ConfirmOpportunityRequirementsForOwner write exactly those two
       values into a CHECK that still refuses them.

       The compatibility THROW immediately below does not catch it. Every
       column it probes is on a table this file has just created, so on a
       fresh apply they all exist, and on an OS-1 database the OS-1 columns
       exist too. Neither case inspects the constraint.

       This block closes it, and is a no-op on a fresh apply: the table was
       created moments ago with the full five-value CHECK, so the EXISTS
       matches and nothing is altered. It is also written to repair the case
       where the constraint is missing altogether. ALTER TABLE ... ADD
       CONSTRAINT validates existing rows by default, which is safe here
       because the new value set is a strict superset of the old one - no
       stored workbench_state can fail it.
       ------------------------------------------------------------ */
    IF OBJECT_ID(N'dbo.opportunity_working_sessions', N'U') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID(N'dbo.opportunity_working_sessions')
              AND name = N'CK_opportunity_working_sessions_state'
              AND definition LIKE N'%review\_requirements%' ESCAPE N'\'
              AND definition LIKE N'%requirements\_confirmed%' ESCAPE N'\'
       )
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID(N'dbo.opportunity_working_sessions')
              AND name = N'CK_opportunity_working_sessions_state'
        )
            ALTER TABLE dbo.opportunity_working_sessions
                DROP CONSTRAINT CK_opportunity_working_sessions_state;

        ALTER TABLE dbo.opportunity_working_sessions
            ADD CONSTRAINT CK_opportunity_working_sessions_state CHECK
                (workbench_state IN (N'role_intake', N'review_source', N'source_confirmed',
                                     N'review_requirements', N'requirements_confirmed'));
    END;

    IF COL_LENGTH(N'dbo.opportunity_working_sessions', N'expires_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_sources', N'confirmed_version_number') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_source_versions', N'member_corrected_text') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_source_concerns', N'member_resolution') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_requirement_statements', N'member_class') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_analysis_statements', N'derived_status') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_responses', N'response_kind') IS NULL
        THROW 53406, 'Existing Opportunity Slate tables are incompatible.', 1;

    /* ------------------------------------------------------------
       Stored procedures. Application access goes ONLY through these
       (services/database_service.py's allowlist pattern). Every
       procedure resolves @UserKey -> @ProfileId itself and returns
       empty / changed / not_found rather than accepting an owner id
       from the caller; every predicate re-asserts owner_profile_id;
       every read re-asserts the expiry bound so an expired working
       session is immediately inaccessible even before the purge
       procedure has physically removed it (handoff section 1).
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeExpiredOpportunityWorkingData
            @UserKey nvarchar(300),
            /* Opt-out for the internal caller below. Defaults to 1, the
               application''s behavior: the service reads the counts. The
               PS-WORKSHOP-001 @IncludeTotalCount idiom - an additive
               parameter defaulting to unchanged behavior - so that
               usp_SaveOpportunitySourceForOwner can invoke this cleanup
               without emitting a second result set ahead of its own. */
            @IncludeCounts bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Strictly owner-scoped. Handoff section 8 names this
               procedure as the physical-destruction mechanism, invoked
               opportunistically at the start of an Opportunity Slate
               request for that one owner. It deliberately has no
               all-owners branch: a cross-owner destructive sweep is not
               something an ordinary member request should be able to
               trigger, and no maintenance scheduler exists in this
               runtime. An operator sweep runs this per owner.

               It removes ONLY working data whose expires_at_utc has
               already passed - rows the reads below already refuse to
               return. It can never touch a saved artifact, because slice
               OS-1 has no saved artifact to touch. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @IncludeCounts IS NULL SET @IncludeCounts = 1;
            IF @UserKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @ExpiredSessions TABLE (working_session_id bigint NOT NULL PRIMARY KEY);
            DECLARE @PurgedVersionCount int = 0;
            DECLARE @PurgedSessionCount int = 0;

            /* The three deletes are ONE unit of work. Without an explicit
               transaction each statement autocommits on its own, so a
               failure between them could leave a source row whose versions
               were already destroyed - and the UPDLOCK, HOLDLOCK range lock
               below would release at statement end, serializing nothing.

               usp_SaveOpportunitySourceForOwner calls this procedure from
               inside its own transaction. Opening a second, nested one
               there would add nothing and would leave this procedure''s
               CATCH able to roll back its caller''s work, so the envelope
               is conditional on the entry @@TRANCOUNT: standalone this
               procedure owns the transaction; nested it enlists in the
               caller''s and lets the caller''s CATCH decide. That is
               precisely what makes Save atomic across the purge and the
               rows it then writes. */
            DECLARE @OuterTranCount int = @@TRANCOUNT;

            BEGIN TRY
                IF @OuterTranCount = 0 BEGIN TRANSACTION;

                INSERT @ExpiredSessions (working_session_id)
                SELECT working_session.working_session_id
                FROM dbo.opportunity_working_sessions AS working_session WITH (UPDLOCK, HOLDLOCK)
                WHERE working_session.owner_profile_id = @ProfileId
                  AND working_session.expires_at_utc <= @Now;

                /* SLICE OS-2 ADDITION. The AI-proposal tables hang off the
                   source versions and the working session, so they have to
                   go first or the deletes below violate their foreign keys.
                   This is the one place slice OS-2 had to reach into a
                   procedure slice OS-1 wrote, and it is not optional: a purge
                   that cannot complete leaves expired employer wording on
                   disk past its expiry, which is the exact thing this
                   procedure exists to prevent. */
                DELETE concern_record
                FROM dbo.opportunity_source_concerns AS concern_record
                JOIN dbo.opportunity_source_reviews AS review_record
                  ON review_record.opportunity_source_review_id = concern_record.opportunity_source_review_id
                 AND review_record.owner_profile_id = concern_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE concern_record.owner_profile_id = @ProfileId;

                DELETE review_record
                FROM dbo.opportunity_source_reviews AS review_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE review_record.owner_profile_id = @ProfileId;

                /* SLICE OS-3 ADDITION, for exactly the OS-2 reason one level
                   deeper: the analysis and the member''s responses hang off
                   the requirement statements, so they have to go before the
                   statements do. A purge that cannot complete leaves expired
                   employer wording AND an expired reading of a member''s own
                   evidence on disk past its expiry. */
                DELETE citation_record
                FROM dbo.opportunity_analysis_citations AS citation_record
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                 AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE citation_record.owner_profile_id = @ProfileId;

                DELETE analysis_statement
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE analysis_statement.owner_profile_id = @ProfileId;

                DELETE analysis_record
                FROM dbo.opportunity_analyses AS analysis_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE analysis_record.owner_profile_id = @ProfileId;

                DELETE response_record
                FROM dbo.opportunity_responses AS response_record
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = response_record.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = response_record.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE response_record.owner_profile_id = @ProfileId;

                DELETE statement_record
                FROM dbo.opportunity_requirement_statements AS statement_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE statement_record.owner_profile_id = @ProfileId;

                DELETE set_version
                FROM dbo.opportunity_requirement_set_versions AS set_version
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE set_version.owner_profile_id = @ProfileId;

                DELETE requirement_set
                FROM dbo.opportunity_requirement_sets AS requirement_set
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE requirement_set.owner_profile_id = @ProfileId;

                DELETE version_record
                FROM dbo.opportunity_source_versions AS version_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE version_record.owner_profile_id = @ProfileId;
                SET @PurgedVersionCount = @@ROWCOUNT;

                DELETE source_record
                FROM dbo.opportunity_sources AS source_record
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE source_record.owner_profile_id = @ProfileId;

                DELETE working_session
                FROM dbo.opportunity_working_sessions AS working_session
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = working_session.working_session_id
                WHERE working_session.owner_profile_id = @ProfileId;
                SET @PurgedSessionCount = @@ROWCOUNT;

                IF @OuterTranCount = 0 COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF @OuterTranCount = 0 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;

            IF @IncludeCounts = 1
                SELECT
                    @PurgedSessionCount AS purged_session_count,
                    @PurgedVersionCount AS purged_version_count;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunityWorkingSessionForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            /* An expired working session is inaccessible from this moment
               on, whether or not the purge procedure has physically
               removed it yet. Returning no row means the member starts
               fresh at role intake. */
            SELECT
                working_session.working_session_key,
                working_session.workbench_state,
                working_session.expires_at_utc,
                CONVERT(binary(8), working_session.row_version) AS session_row_version,
                source_record.source_key,
                source_record.current_version_number,
                source_record.confirmed_version_number,
                source_record.confirmed_at_utc,
                CONVERT(binary(8), source_record.row_version) AS source_row_version,
                version_record.capture_method,
                version_record.original_text,
                version_record.member_corrected_text,
                version_record.corrected_at_utc,
                version_record.captured_at_utc
            FROM dbo.opportunity_working_sessions AS working_session
            JOIN dbo.opportunity_sources AS source_record
              ON source_record.working_session_id = working_session.working_session_id
             AND source_record.owner_profile_id = working_session.owner_profile_id
            JOIN dbo.opportunity_source_versions AS version_record
              ON version_record.opportunity_source_id = source_record.opportunity_source_id
             AND version_record.owner_profile_id = source_record.owner_profile_id
             AND version_record.version_number = source_record.current_version_number
            WHERE working_session.owner_profile_id = @ProfileId
              AND working_session.visibility = N''private''
              AND working_session.expires_at_utc > SYSUTCDATETIME();
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunitySourceForOwner
            @UserKey nvarchar(300),
            /* Wider than the 200-unit limit it enforces, so an over-length
               value is not silently truncated before the guard can fire -
               the PS-WORKSHOP-001 MINOR 11 correction, applied here from
               the start. The column itself stays nvarchar(200). */
            @IdempotencyKey nvarchar(4000),
            @SourceText nvarchar(max),
            @CaptureMethod nvarchar(20) = N''pasted'',
            @ExpiresInHours int = 48
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL
            BEGIN
                SELECT
                    N''not_found'' AS outcome, CAST(NULL AS uniqueidentifier) AS working_session_key,
                    CAST(NULL AS uniqueidentifier) AS source_key, CAST(NULL AS int) AS version_number,
                    CAST(NULL AS nvarchar(40)) AS workbench_state,
                    CAST(NULL AS binary(8)) AS session_row_version,
                    CAST(NULL AS binary(8)) AS source_row_version;
                RETURN;
            END;

            IF @CaptureMethod IS NULL SET @CaptureMethod = N''pasted'';
            IF @ExpiresInHours IS NULL OR @ExpiresInHours < 1 OR @ExpiresInHours > 168
                SET @ExpiresInHours = 48;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT
                    N''not_found'' AS outcome, CAST(NULL AS uniqueidentifier) AS working_session_key,
                    CAST(NULL AS uniqueidentifier) AS source_key, CAST(NULL AS int) AS version_number,
                    CAST(NULL AS nvarchar(40)) AS workbench_state,
                    CAST(NULL AS binary(8)) AS session_row_version,
                    CAST(NULL AS binary(8)) AS source_row_version;
                RETURN;
            END;

            IF @SourceText IS NULL
               OR DATALENGTH(@SourceText) / 2 NOT BETWEEN 1 AND 20000
               OR @IdempotencyKey IS NULL
               OR DATALENGTH(@IdempotencyKey) / 2 NOT BETWEEN 1 AND 200
               OR @CaptureMethod NOT IN (N''pasted'', N''dictated'', N''uploaded'', N''imported'')
            BEGIN
                SELECT
                    N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS working_session_key,
                    CAST(NULL AS uniqueidentifier) AS source_key, CAST(NULL AS int) AS version_number,
                    CAST(NULL AS nvarchar(40)) AS workbench_state,
                    CAST(NULL AS binary(8)) AS session_row_version,
                    CAST(NULL AS binary(8)) AS source_row_version;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @Expiry datetime2(7) = DATEADD(hour, @ExpiresInHours, @Now);
            DECLARE @Digest char(64) =
                CONVERT(char(64), HASHBYTES(''SHA2_256'', @SourceText), 2);

            DECLARE @SessionId bigint;
            DECLARE @SourceId bigint;
            DECLARE @VersionNumber int;

            /* Everything below writes. It is one unit of work: the session,
               its source, the appended version row, and the confirmation
               state have to move together or not at all. In autocommit each
               statement would commit on its own, so a failure after the
               source insert but before the version insert would leave a
               source whose current_version_number points at a row that does
               not exist - the Get procedure inner-joins that version, so
               intake would render empty, and every retry would read
               @CurrentVersion = NULL and violate NOT NULL on NULL + 1. The
               working session would be unusable until its 48-hour expiry.
               The transaction is also what gives the UPDLOCK, HOLDLOCK
               guards below a lifetime long enough to serialize anything. */
            BEGIN TRY
                BEGIN TRANSACTION;

                /* Replay guard first: a double-submitted intake POST returns
                   the SAME version it already created rather than appending a
                   second one. */
                SELECT
                    @SourceId = version_record.opportunity_source_id,
                    @VersionNumber = version_record.version_number
                FROM dbo.opportunity_source_versions AS version_record WITH (UPDLOCK, HOLDLOCK)
                WHERE version_record.owner_profile_id = @ProfileId
                  AND version_record.idempotency_key = @IdempotencyKey;

                IF @SourceId IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''existing'' AS outcome,
                        working_session.working_session_key,
                        source_record.source_key,
                        @VersionNumber AS version_number,
                        working_session.workbench_state,
                        CONVERT(binary(8), working_session.row_version) AS session_row_version,
                        CONVERT(binary(8), source_record.row_version) AS source_row_version
                    FROM dbo.opportunity_sources AS source_record
                    JOIN dbo.opportunity_working_sessions AS working_session
                      ON working_session.working_session_id = source_record.working_session_id
                     AND working_session.owner_profile_id = source_record.owner_profile_id
                    WHERE source_record.opportunity_source_id = @SourceId
                      AND source_record.owner_profile_id = @ProfileId;
                    RETURN;
                END;

                /* Expired working data for this owner is destroyed before a new
                   session is created, so a stale expired row can never block
                   the one-session-per-member constraint. The purge enlists in
                   THIS transaction (it opens none of its own when called with
                   an open one), so its deletes and the inserts below commit or
                   roll back together. */
                EXEC dbo.usp_PurgeExpiredOpportunityWorkingData
                    @UserKey = @UserKey, @IncludeCounts = 0;

                SELECT
                    @SessionId = working_session.working_session_id,
                    @SourceId = source_record.opportunity_source_id
                FROM dbo.opportunity_working_sessions AS working_session WITH (UPDLOCK, HOLDLOCK)
                LEFT JOIN dbo.opportunity_sources AS source_record
                  ON source_record.working_session_id = working_session.working_session_id
                 AND source_record.owner_profile_id = working_session.owner_profile_id
                WHERE working_session.owner_profile_id = @ProfileId
                  AND working_session.expires_at_utc > @Now;

                IF @SessionId IS NULL
                BEGIN
                    INSERT dbo.opportunity_working_sessions
                        (owner_profile_id, workbench_state, created_at_utc, updated_at_utc, expires_at_utc)
                    VALUES
                        (@ProfileId, N''review_source'', @Now, @Now, @Expiry);
                    SET @SessionId = SCOPE_IDENTITY();
                END;

                IF @SourceId IS NULL
                BEGIN
                    INSERT dbo.opportunity_sources
                        (working_session_id, owner_profile_id, current_version_number, created_at_utc, updated_at_utc)
                    VALUES
                        (@SessionId, @ProfileId, 1, @Now, @Now);
                    SET @SourceId = SCOPE_IDENTITY();
                    SET @VersionNumber = 1;

                    INSERT dbo.opportunity_source_versions
                        (opportunity_source_id, owner_profile_id, version_number, capture_method,
                         original_text, original_sha256, idempotency_key, captured_by_user_id, captured_at_utc)
                    VALUES
                        (@SourceId, @ProfileId, 1, @CaptureMethod,
                         @SourceText, @Digest, @IdempotencyKey, @UserId, @Now);
                END
                ELSE
                BEGIN
                    DECLARE @CurrentVersion int;
                    DECLARE @CurrentDigest char(64);
                    SELECT
                        @CurrentVersion = source_record.current_version_number,
                        @CurrentDigest = version_record.original_sha256
                    FROM dbo.opportunity_sources AS source_record
                    JOIN dbo.opportunity_source_versions AS version_record
                      ON version_record.opportunity_source_id = source_record.opportunity_source_id
                     AND version_record.owner_profile_id = source_record.owner_profile_id
                     AND version_record.version_number = source_record.current_version_number
                    WHERE source_record.opportunity_source_id = @SourceId
                      AND source_record.owner_profile_id = @ProfileId;

                    IF @CurrentDigest = @Digest
                    BEGIN
                        /* Byte-identical resubmission of the same employer
                           wording: no new version, no version-number churn.
                           The member simply returns to Review Source. */
                        SET @VersionNumber = @CurrentVersion;

                        /* But a resubmission IS an explicit act of replacing
                           the displayed source, and a correction overlay
                           sitting on this version would mean the screen shows
                           wording the member did not just supply. Clear the
                           overlay so the displayed text is exactly what was
                           submitted, and clear the confirmation the changed
                           display invalidates - the same rule the correction
                           procedure applies. With no overlay there is nothing
                           stale: the confirmation still describes exactly this
                           wording and is left untouched, so re-pasting cannot
                           silently cost the member a completed checkpoint. */
                        DECLARE @ClearedCorrection bit = 0;

                        UPDATE dbo.opportunity_source_versions
                        SET member_corrected_text = NULL,
                            corrected_by_user_id = NULL,
                            corrected_at_utc = NULL
                        WHERE opportunity_source_id = @SourceId
                          AND owner_profile_id = @ProfileId
                          AND version_number = @VersionNumber
                          AND member_corrected_text IS NOT NULL;
                        IF @@ROWCOUNT > 0 SET @ClearedCorrection = 1;

                        IF @ClearedCorrection = 1
                        BEGIN
                            UPDATE dbo.opportunity_sources
                            SET confirmed_version_number = NULL,
                                confirmed_by_user_id = NULL,
                                confirmed_at_utc = NULL,
                                updated_at_utc = @Now
                            WHERE opportunity_source_id = @SourceId
                              AND owner_profile_id = @ProfileId;
                        END;

                        UPDATE dbo.opportunity_working_sessions
                        SET expires_at_utc = @Expiry,
                            updated_at_utc = @Now,
                            workbench_state = CASE
                                WHEN @ClearedCorrection = 1 THEN N''review_source''
                                ELSE workbench_state
                            END
                        WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                        COMMIT TRANSACTION;

                        SELECT
                            N''unchanged'' AS outcome,
                            working_session.working_session_key,
                            source_record.source_key,
                            @VersionNumber AS version_number,
                            working_session.workbench_state,
                            CONVERT(binary(8), working_session.row_version) AS session_row_version,
                            CONVERT(binary(8), source_record.row_version) AS source_row_version
                        FROM dbo.opportunity_sources AS source_record
                        JOIN dbo.opportunity_working_sessions AS working_session
                          ON working_session.working_session_id = source_record.working_session_id
                         AND working_session.owner_profile_id = source_record.owner_profile_id
                        WHERE source_record.opportunity_source_id = @SourceId
                          AND source_record.owner_profile_id = @ProfileId;
                        RETURN;
                    END;

                    SET @VersionNumber = @CurrentVersion + 1;

                    INSERT dbo.opportunity_source_versions
                        (opportunity_source_id, owner_profile_id, version_number, capture_method,
                         original_text, original_sha256, idempotency_key, captured_by_user_id, captured_at_utc)
                    VALUES
                        (@SourceId, @ProfileId, @VersionNumber, @CaptureMethod,
                         @SourceText, @Digest, @IdempotencyKey, @UserId, @Now);

                    /* New employer wording clears any confirmation: the member
                       has not confirmed THIS text. */
                    UPDATE dbo.opportunity_sources
                    SET current_version_number = @VersionNumber,
                        confirmed_version_number = NULL,
                        confirmed_by_user_id = NULL,
                        confirmed_at_utc = NULL,
                        updated_at_utc = @Now
                    WHERE opportunity_source_id = @SourceId AND owner_profile_id = @ProfileId;
                END;

                UPDATE dbo.opportunity_working_sessions
                SET workbench_state = N''review_source'',
                    expires_at_utc = @Expiry,
                    updated_at_utc = @Now
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    working_session.working_session_key,
                    source_record.source_key,
                    @VersionNumber AS version_number,
                    working_session.workbench_state,
                    CONVERT(binary(8), working_session.row_version) AS session_row_version,
                    CONVERT(binary(8), source_record.row_version) AS source_row_version
                FROM dbo.opportunity_sources AS source_record
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                WHERE source_record.opportunity_source_id = @SourceId
                  AND source_record.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CorrectOpportunitySourceForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @CorrectedText nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* A member''s manual correction of the DISPLAYED wording. It
               writes member_corrected_text only; original_text is never
               touched, so the employer''s captured wording stays
               recoverable. A correction that restores the original exactly
               clears the overlay instead of storing a duplicate. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS int) AS version_number;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS int) AS version_number;
                RETURN;
            END;

            IF @CorrectedText IS NULL OR DATALENGTH(@CorrectedText) / 2 NOT BETWEEN 1 AND 20000
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS int) AS version_number;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SourceId bigint;
            DECLARE @SessionId bigint;
            DECLARE @VersionNumber int;

            /* The correction and the confirmation it invalidates are one
               unit of work. In autocommit the member_corrected_text write
               could commit and the confirmation-clearing update then fail,
               leaving a source badged as confirmed against wording the
               member never confirmed. CK_opportunity_sources_confirmation_state
               would not catch it: current_version_number does not move on a
               correction, so the stale triple still satisfies the CHECK. */
            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @SourceId = source_record.opportunity_source_id,
                    @SessionId = source_record.working_session_id,
                    @VersionNumber = source_record.current_version_number
                FROM dbo.opportunity_sources AS source_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                WHERE source_record.source_key = @SourceKey
                  AND source_record.owner_profile_id = @ProfileId
                  AND source_record.row_version = @ExpectedRowVersion
                  AND working_session.expires_at_utc > @Now;

                /* A missing, foreign, expired, or stale-version source all
                   resolve to the same neutral ''changed'' outcome, so the
                   response can never confirm whether another member''s key
                   exists. */
                IF @SourceId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                           CAST(NULL AS int) AS version_number;
                    RETURN;
                END;

                DECLARE @IsRevert bit = 0;
                SELECT @IsRevert = CASE WHEN version_record.original_text = @CorrectedText THEN 1 ELSE 0 END
                FROM dbo.opportunity_source_versions AS version_record
                WHERE version_record.opportunity_source_id = @SourceId
                  AND version_record.owner_profile_id = @ProfileId
                  AND version_record.version_number = @VersionNumber;

                UPDATE dbo.opportunity_source_versions
                SET member_corrected_text = CASE WHEN @IsRevert = 1 THEN NULL ELSE @CorrectedText END,
                    corrected_by_user_id = CASE WHEN @IsRevert = 1 THEN NULL ELSE @UserId END,
                    corrected_at_utc = CASE WHEN @IsRevert = 1 THEN NULL ELSE @Now END
                WHERE opportunity_source_id = @SourceId
                  AND owner_profile_id = @ProfileId
                  AND version_number = @VersionNumber;

                /* Corrected wording is not the wording the member confirmed. */
                UPDATE dbo.opportunity_sources
                SET confirmed_version_number = NULL,
                    confirmed_by_user_id = NULL,
                    confirmed_at_utc = NULL,
                    updated_at_utc = @Now
                WHERE opportunity_source_id = @SourceId AND owner_profile_id = @ProfileId;

                UPDATE dbo.opportunity_working_sessions
                SET workbench_state = N''review_source'', updated_at_utc = @Now
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    CONVERT(binary(8), source_record.row_version) AS source_row_version,
                    @VersionNumber AS version_number
                FROM dbo.opportunity_sources AS source_record
                WHERE source_record.opportunity_source_id = @SourceId
                  AND source_record.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ConfirmOpportunitySourceForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Checkpoint 1 of 2 (handoff section 2). Confirming records
               which source version the member accepted. It saves no slate,
               produces no qualification result, and calls no AI. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS int) AS confirmed_version_number;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS int) AS confirmed_version_number;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SourceId bigint;
            DECLARE @SessionId bigint;
            DECLARE @VersionNumber int;

            /* The confirmation and the workbench state it advances are one
               unit of work: a committed confirmation with the session still
               sitting in review_source would describe a checkpoint the state
               machine never reached. */
            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @SourceId = source_record.opportunity_source_id,
                    @SessionId = source_record.working_session_id,
                    @VersionNumber = source_record.current_version_number
                FROM dbo.opportunity_sources AS source_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                WHERE source_record.source_key = @SourceKey
                  AND source_record.owner_profile_id = @ProfileId
                  AND source_record.row_version = @ExpectedRowVersion
                  AND working_session.expires_at_utc > @Now;

                IF @SourceId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                           CAST(NULL AS int) AS confirmed_version_number;
                    RETURN;
                END;

                UPDATE dbo.opportunity_sources
                SET confirmed_version_number = @VersionNumber,
                    confirmed_by_user_id = @UserId,
                    confirmed_at_utc = @Now,
                    updated_at_utc = @Now
                WHERE opportunity_source_id = @SourceId AND owner_profile_id = @ProfileId;

                UPDATE dbo.opportunity_working_sessions
                SET workbench_state = N''source_confirmed'', updated_at_utc = @Now
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    CONVERT(binary(8), source_record.row_version) AS source_row_version,
                    @VersionNumber AS confirmed_version_number
                FROM dbo.opportunity_sources AS source_record
                WHERE source_record.opportunity_source_id = @SourceId
                  AND source_record.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteOpportunityWorkingSessionForOwner
            @UserKey nvarchar(300),
            @WorkingSessionKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* The member''s explicit discard (image 02''s "Delete source").
               Atomic: source versions, then the source, then the working
               session, every predicate re-asserting owner_profile_id.
               Nothing durable exists to survive it in slice OS-1. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @WorkingSessionKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                RETURN;
            END;

            DECLARE @SessionId bigint;
            DECLARE @DeletedVersionCount int = 0;

            /* "Atomic" is a promise the member is shown (handoff section 7:
               a failed delete leaves the slate fully intact). Three
               autocommitted deletes are not atomic - a failure after the
               first would destroy the employer wording while leaving the
               session that claims to hold it. The transaction is what makes
               the promise true. */
            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT @SessionId = working_session.working_session_id
                FROM dbo.opportunity_working_sessions AS working_session WITH (UPDLOCK, HOLDLOCK)
                WHERE working_session.working_session_key = @WorkingSessionKey
                  AND working_session.owner_profile_id = @ProfileId
                  AND working_session.row_version = @ExpectedRowVersion;

                IF @SessionId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                    RETURN;
                END;

                /* SLICE OS-2 ADDITION, and the same reason as the purge: the
                   proposal tables reference these rows, so "atomic and
                   complete" now means them too. A member who deletes their
                   working session must not be left with PeerSlate''s readings
                   of a source that no longer exists. */
                DELETE concern_record
                FROM dbo.opportunity_source_concerns AS concern_record
                JOIN dbo.opportunity_source_reviews AS review_record
                  ON review_record.opportunity_source_review_id = concern_record.opportunity_source_review_id
                 AND review_record.owner_profile_id = concern_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND concern_record.owner_profile_id = @ProfileId;

                DELETE review_record
                FROM dbo.opportunity_source_reviews AS review_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND review_record.owner_profile_id = @ProfileId;

                /* SLICE OS-3 ADDITION. "Atomic and complete" now reaches the
                   analysis and the member''s responses too: a member who
                   deletes their working session must not be left with
                   PeerSlate''s reading of evidence against requirements that
                   no longer exist. */
                DELETE citation_record
                FROM dbo.opportunity_analysis_citations AS citation_record
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                 AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND citation_record.owner_profile_id = @ProfileId;

                DELETE analysis_statement
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND analysis_statement.owner_profile_id = @ProfileId;

                DELETE analysis_record
                FROM dbo.opportunity_analyses AS analysis_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND analysis_record.owner_profile_id = @ProfileId;

                DELETE response_record
                FROM dbo.opportunity_responses AS response_record
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = response_record.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = response_record.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND response_record.owner_profile_id = @ProfileId;

                DELETE statement_record
                FROM dbo.opportunity_requirement_statements AS statement_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND statement_record.owner_profile_id = @ProfileId;

                DELETE set_version
                FROM dbo.opportunity_requirement_set_versions AS set_version
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND set_version.owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_requirement_sets
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                DELETE version_record
                FROM dbo.opportunity_source_versions AS version_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND version_record.owner_profile_id = @ProfileId;
                SET @DeletedVersionCount = @@ROWCOUNT;

                DELETE dbo.opportunity_sources
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_working_sessions
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @DeletedVersionCount AS deleted_version_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* ============================================================
       SLICE OS-2 PROCEDURES

       Same discipline as every procedure above: @UserKey resolved here,
       owner_profile_id re-asserted in every predicate, rowversion fencing on
       every mutation, and one BEGIN TRY / BEGIN TRANSACTION / COMMIT /
       CATCH + XACT_STATE envelope around every write. No procedure below
       accepts an owner id from its caller, and none of them writes a
       proposal column from a member column or the reverse.
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunitySourceReviewForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Two result sets: the review, then its concerns. No rows at all
               means AI step 1 has not run for the CURRENT captured version —
               deliberately a different answer from a review with zero
               concerns, which means it ran and found nothing. The screen
               says those two things differently and this is what lets it. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @ReviewId bigint;
            SELECT @ReviewId = review_record.opportunity_source_review_id
            FROM dbo.opportunity_source_reviews AS review_record
            JOIN dbo.opportunity_sources AS source_record
              ON source_record.opportunity_source_id = review_record.opportunity_source_id
             AND source_record.owner_profile_id = review_record.owner_profile_id
            JOIN dbo.opportunity_working_sessions AS working_session
              ON working_session.working_session_id = source_record.working_session_id
             AND working_session.owner_profile_id = source_record.owner_profile_id
            WHERE source_record.source_key = @SourceKey
              AND review_record.owner_profile_id = @ProfileId
              AND review_record.source_version_number = source_record.current_version_number
              AND working_session.expires_at_utc > SYSUTCDATETIME();

            IF @ReviewId IS NULL RETURN;

            SELECT
                review_record.review_key,
                review_record.source_version_number,
                review_record.model_name,
                review_record.prompt_contract_version,
                review_record.concern_count,
                review_record.reviewed_at_utc
            FROM dbo.opportunity_source_reviews AS review_record
            WHERE review_record.opportunity_source_review_id = @ReviewId
              AND review_record.owner_profile_id = @ProfileId;

            SELECT
                concern_record.concern_key,
                concern_record.span_start,
                concern_record.span_length,
                concern_record.quoted_text,
                concern_record.concern_reason,
                concern_record.member_resolution,
                concern_record.member_corrected_text,
                concern_record.resolved_at_utc,
                CONVERT(binary(8), concern_record.row_version) AS concern_row_version
            FROM dbo.opportunity_source_concerns AS concern_record
            WHERE concern_record.opportunity_source_review_id = @ReviewId
              AND concern_record.owner_profile_id = @ProfileId
            ORDER BY concern_record.ordinal;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunitySourceReviewForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @ModelName nvarchar(4000),
            @PromptContractVersion nvarchar(4000),
            @ConcernsJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Records that AI step 1 ran against the current captured
               version, with the proposals it made. It writes ONLY proposal
               columns: not one statement here touches original_text,
               member_corrected_text on the version row, or the source
               confirmation. A proposal is not a change to the member''s
               wording and must not be able to become one. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS review_key,
                       CAST(NULL AS int) AS concern_count;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS review_key,
                       CAST(NULL AS int) AS concern_count;
                RETURN;
            END;

            IF @ModelName IS NULL OR DATALENGTH(@ModelName) / 2 NOT BETWEEN 1 AND 100
               OR @PromptContractVersion IS NULL
               OR DATALENGTH(@PromptContractVersion) / 2 NOT BETWEEN 1 AND 60
               OR @ConcernsJson IS NULL
               OR ISJSON(@ConcernsJson) <> 1
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS review_key,
                       CAST(NULL AS int) AS concern_count;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SourceId bigint;
            DECLARE @VersionId bigint;
            DECLARE @VersionNumber int;
            DECLARE @ReviewId bigint;
            DECLARE @ReviewKey uniqueidentifier;
            DECLARE @ConcernCount int = 0;

            /* The whole write is one unit of work: clearing the previous
               review, inserting this one, and inserting its concerns. In
               autocommit a failure between them could leave a review row
               claiming a concern_count it has no rows for. */
            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @SourceId = source_record.opportunity_source_id,
                    @VersionNumber = source_record.current_version_number,
                    @VersionId = version_record.opportunity_source_version_id
                FROM dbo.opportunity_sources AS source_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                JOIN dbo.opportunity_source_versions AS version_record
                  ON version_record.opportunity_source_id = source_record.opportunity_source_id
                 AND version_record.owner_profile_id = source_record.owner_profile_id
                 AND version_record.version_number = source_record.current_version_number
                WHERE source_record.source_key = @SourceKey
                  AND source_record.owner_profile_id = @ProfileId
                  AND source_record.row_version = @ExpectedRowVersion
                  AND working_session.expires_at_utc > @Now;

                IF @SourceId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS review_key,
                           CAST(NULL AS int) AS concern_count;
                    RETURN;
                END;

                /* COUNT AND REJECT BEFORE DELETING ANYTHING (isolated SQL
                   gate, 2026-08-04, defect 1). This guard used to sit AFTER
                   the two DELETEs below and then COMMIT, so an over-long
                   proposal destroyed the member''s existing review, its
                   concerns, and every decision they had already made on
                   them - and then returned ''invalid'', which tells the
                   caller nothing happened. The sibling procedure
                   usp_SaveOpportunityRequirementProposalForOwner already
                   counts before it deletes; this one now does too, so a
                   rejected proposal leaves the member''s work exactly where
                   it was. */
                SELECT @ConcernCount = COUNT(*)
                FROM OPENJSON(@ConcernsJson)
                WITH
                (
                    span_start int ''$.span_start'',
                    span_length int ''$.span_length'',
                    quoted_text nvarchar(1000) ''$.quoted_text'',
                    concern_reason nvarchar(500) ''$.concern_reason''
                ) AS proposal;

                IF @ConcernCount > 20
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS review_key,
                           CAST(NULL AS int) AS concern_count;
                    RETURN;
                END;

                /* Any earlier review of this source goes, including one for a
                   superseded version. A reading of wording the member has
                   since replaced is not history worth keeping in an ephemeral
                   store; it is a second copy of employer text with nothing to
                   show for it. */
                DELETE concern_record
                FROM dbo.opportunity_source_concerns AS concern_record
                JOIN dbo.opportunity_source_reviews AS review_record
                  ON review_record.opportunity_source_review_id = concern_record.opportunity_source_review_id
                 AND review_record.owner_profile_id = concern_record.owner_profile_id
                WHERE review_record.opportunity_source_id = @SourceId
                  AND concern_record.owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_source_reviews
                WHERE opportunity_source_id = @SourceId AND owner_profile_id = @ProfileId;

                INSERT dbo.opportunity_source_reviews
                    (opportunity_source_version_id, opportunity_source_id, owner_profile_id,
                     source_version_number, model_name, prompt_contract_version,
                     concern_count, reviewed_at_utc)
                VALUES
                    (@VersionId, @SourceId, @ProfileId, @VersionNumber, @ModelName,
                     @PromptContractVersion, @ConcernCount, @Now);
                SET @ReviewId = SCOPE_IDENTITY();

                INSERT dbo.opportunity_source_concerns
                    (opportunity_source_review_id, owner_profile_id, ordinal,
                     span_start, span_length, quoted_text, concern_reason)
                SELECT
                    @ReviewId,
                    @ProfileId,
                    ROW_NUMBER() OVER (ORDER BY proposal.span_start, proposal.span_length),
                    proposal.span_start,
                    proposal.span_length,
                    proposal.quoted_text,
                    proposal.concern_reason
                FROM OPENJSON(@ConcernsJson)
                WITH
                (
                    span_start int ''$.span_start'',
                    span_length int ''$.span_length'',
                    quoted_text nvarchar(1000) ''$.quoted_text'',
                    concern_reason nvarchar(500) ''$.concern_reason''
                ) AS proposal;

                SELECT @ReviewKey = review_record.review_key
                FROM dbo.opportunity_source_reviews AS review_record
                WHERE review_record.opportunity_source_review_id = @ReviewId
                  AND review_record.owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @ReviewKey AS review_key,
                       @ConcernCount AS concern_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ResolveOpportunitySourceConcernForOwner
            @UserKey nvarchar(300),
            @ConcernKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @Resolution nvarchar(20),
            @CorrectedSpanText nvarchar(max) = NULL,
            @DocumentText nvarchar(max) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* The member''s decision on one proposal.

               ''applied'' writes their replacement wording for the span AND
               the resulting whole document, then clears the source
               confirmation the changed wording invalidates — all in one
               transaction, because a committed document change with a stale
               confirmation would badge a source as confirmed against text
               the member never confirmed.

               ''dismissed'' records the decision and changes NO wording. The
               confirmation is deliberately left alone: nothing about the
               employer''s text moved, so there is nothing to re-confirm.

               original_text is untouched on both paths. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @ConcernKey IS NULL OR @ExpectedRowVersion IS NULL
               OR @Resolution NOT IN (N''applied'', N''dismissed'')
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS nvarchar(20)) AS member_resolution;
                RETURN;
            END;

            IF @Resolution = N''applied''
               AND (@CorrectedSpanText IS NULL
                    OR DATALENGTH(@CorrectedSpanText) / 2 NOT BETWEEN 1 AND 20000
                    OR @DocumentText IS NULL
                    OR DATALENGTH(@DocumentText) / 2 NOT BETWEEN 1 AND 20000)
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS nvarchar(20)) AS member_resolution;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                       CAST(NULL AS nvarchar(20)) AS member_resolution;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @ConcernId bigint;
            DECLARE @SourceId bigint;
            DECLARE @SessionId bigint;
            DECLARE @VersionNumber int;

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @ConcernId = concern_record.opportunity_source_concern_id,
                    @SourceId = source_record.opportunity_source_id,
                    @SessionId = source_record.working_session_id,
                    @VersionNumber = source_record.current_version_number
                FROM dbo.opportunity_source_concerns AS concern_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_source_reviews AS review_record
                  ON review_record.opportunity_source_review_id = concern_record.opportunity_source_review_id
                 AND review_record.owner_profile_id = concern_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                WHERE concern_record.concern_key = @ConcernKey
                  AND concern_record.owner_profile_id = @ProfileId
                  AND concern_record.row_version = @ExpectedRowVersion
                  AND concern_record.member_resolution = N''pending''
                  AND review_record.source_version_number = source_record.current_version_number
                  AND working_session.expires_at_utc > @Now;

                /* A missing, foreign, already-decided, superseded, expired,
                   or stale-version concern all resolve to the same neutral
                   ''changed'', so the response can never confirm whether
                   another member''s key exists. */
                IF @ConcernId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version,
                           CAST(NULL AS nvarchar(20)) AS member_resolution;
                    RETURN;
                END;

                UPDATE dbo.opportunity_source_concerns
                SET member_resolution = @Resolution,
                    member_corrected_text = CASE WHEN @Resolution = N''applied''
                                                 THEN @CorrectedSpanText ELSE NULL END,
                    resolved_by_user_id = @UserId,
                    resolved_at_utc = @Now
                WHERE opportunity_source_concern_id = @ConcernId
                  AND owner_profile_id = @ProfileId;

                IF @Resolution = N''applied''
                BEGIN
                    UPDATE dbo.opportunity_source_versions
                    SET member_corrected_text = @DocumentText,
                        corrected_by_user_id = @UserId,
                        corrected_at_utc = @Now
                    WHERE opportunity_source_id = @SourceId
                      AND owner_profile_id = @ProfileId
                      AND version_number = @VersionNumber;

                    UPDATE dbo.opportunity_sources
                    SET confirmed_version_number = NULL,
                        confirmed_by_user_id = NULL,
                        confirmed_at_utc = NULL,
                        updated_at_utc = @Now
                    WHERE opportunity_source_id = @SourceId AND owner_profile_id = @ProfileId;

                    UPDATE dbo.opportunity_working_sessions
                    SET workbench_state = N''review_source'', updated_at_utc = @Now
                    WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;
                END;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    CONVERT(binary(8), source_record.row_version) AS source_row_version,
                    @Resolution AS member_resolution
                FROM dbo.opportunity_sources AS source_record
                WHERE source_record.opportunity_source_id = @SourceId
                  AND source_record.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunityRequirementsForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Two result sets: the current requirement-set version, then its
               statements. A set pinned to a SUPERSEDED source version returns
               nothing at all, because it describes wording the member has
               since replaced and showing it would put words in the
               employer''s mouth. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @VersionId bigint;
            SELECT @VersionId = set_version.opportunity_requirement_set_version_id
            FROM dbo.opportunity_requirement_set_versions AS set_version
            JOIN dbo.opportunity_requirement_sets AS requirement_set
              ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
             AND requirement_set.owner_profile_id = set_version.owner_profile_id
            JOIN dbo.opportunity_working_sessions AS working_session
              ON working_session.working_session_id = requirement_set.working_session_id
             AND working_session.owner_profile_id = requirement_set.owner_profile_id
            JOIN dbo.opportunity_sources AS source_record
              ON source_record.working_session_id = working_session.working_session_id
             AND source_record.owner_profile_id = working_session.owner_profile_id
            WHERE requirement_set.owner_profile_id = @ProfileId
              AND set_version.version_number = requirement_set.current_version_number
              AND set_version.source_version_number = source_record.current_version_number
              AND working_session.expires_at_utc > SYSUTCDATETIME();

            IF @VersionId IS NULL RETURN;

            SELECT
                requirement_set.requirement_set_key,
                CONVERT(binary(8), requirement_set.row_version) AS set_row_version,
                set_version.version_number,
                set_version.source_version_number,
                set_version.model_name,
                set_version.prompt_contract_version,
                set_version.proposed_at_utc,
                requirement_set.confirmed_version_number,
                requirement_set.confirmed_at_utc
            FROM dbo.opportunity_requirement_set_versions AS set_version
            JOIN dbo.opportunity_requirement_sets AS requirement_set
              ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
             AND requirement_set.owner_profile_id = set_version.owner_profile_id
            WHERE set_version.opportunity_requirement_set_version_id = @VersionId
              AND set_version.owner_profile_id = @ProfileId;

            SELECT
                statement_record.statement_key,
                statement_record.ordinal,
                statement_record.span_start,
                statement_record.span_length,
                statement_record.employer_text,
                statement_record.proposed_class,
                statement_record.proposed_explanation,
                statement_record.proposed_structure_json,
                statement_record.member_class,
                statement_record.member_clarification,
                statement_record.member_updated_at_utc,
                CONVERT(binary(8), statement_record.row_version) AS statement_row_version
            FROM dbo.opportunity_requirement_statements AS statement_record
            WHERE statement_record.opportunity_requirement_set_version_id = @VersionId
              AND statement_record.owner_profile_id = @ProfileId
            ORDER BY statement_record.ordinal;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunityRequirementProposalForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @ModelName nvarchar(4000),
            @PromptContractVersion nvarchar(4000),
            @StatementsJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Records AI step 2''s validated proposals as ONE current
               requirement-set version for the working session, replacing any
               earlier one. The version number still increments, so which run
               produced the confirmed reading stays answerable; the superseded
               statements do not linger, because a working session is
               ephemeral infrastructure and not a member-visible history of
               PeerSlate''s opinions.

               Any existing confirmation is cleared: a member cannot have
               confirmed a reading that did not exist a moment ago. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS requirement_set_key,
                       CAST(NULL AS int) AS version_number, CAST(NULL AS int) AS statement_count;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS requirement_set_key,
                       CAST(NULL AS int) AS version_number, CAST(NULL AS int) AS statement_count;
                RETURN;
            END;

            IF @ModelName IS NULL OR DATALENGTH(@ModelName) / 2 NOT BETWEEN 1 AND 100
               OR @PromptContractVersion IS NULL
               OR DATALENGTH(@PromptContractVersion) / 2 NOT BETWEEN 1 AND 60
               OR @StatementsJson IS NULL
               OR ISJSON(@StatementsJson) <> 1
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS requirement_set_key,
                       CAST(NULL AS int) AS version_number, CAST(NULL AS int) AS statement_count;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SessionId bigint;
            DECLARE @SourceVersionNumber int;
            DECLARE @SetId bigint;
            DECLARE @SetKey uniqueidentifier;
            DECLARE @NextVersion int;
            DECLARE @VersionId bigint;
            DECLARE @StatementCount int = 0;

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @SessionId = source_record.working_session_id,
                    @SourceVersionNumber = source_record.current_version_number
                FROM dbo.opportunity_sources AS source_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                WHERE source_record.source_key = @SourceKey
                  AND source_record.owner_profile_id = @ProfileId
                  AND source_record.row_version = @ExpectedRowVersion
                  AND source_record.confirmed_version_number = source_record.current_version_number
                  AND working_session.expires_at_utc > @Now;

                IF @SessionId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS requirement_set_key,
                           CAST(NULL AS int) AS version_number, CAST(NULL AS int) AS statement_count;
                    RETURN;
                END;

                SELECT @StatementCount = COUNT(*)
                FROM OPENJSON(@StatementsJson)
                WITH
                (
                    ordinal int ''$.ordinal'',
                    span_start int ''$.span_start'',
                    span_length int ''$.span_length'',
                    employer_text nvarchar(2000) ''$.employer_text'',
                    proposed_class nvarchar(40) ''$.proposed_class'',
                    proposed_explanation nvarchar(1000) ''$.proposed_explanation'',
                    proposed_structure_json nvarchar(4000) ''$.proposed_structure_json''
                ) AS proposal;

                IF @StatementCount < 1 OR @StatementCount > 60
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS requirement_set_key,
                           CAST(NULL AS int) AS version_number, CAST(NULL AS int) AS statement_count;
                    RETURN;
                END;

                SELECT @SetId = requirement_set.opportunity_requirement_set_id,
                       @NextVersion = requirement_set.current_version_number + 1
                FROM dbo.opportunity_requirement_sets AS requirement_set WITH (UPDLOCK, HOLDLOCK)
                WHERE requirement_set.working_session_id = @SessionId
                  AND requirement_set.owner_profile_id = @ProfileId;

                IF @SetId IS NULL
                BEGIN
                    INSERT dbo.opportunity_requirement_sets
                        (working_session_id, owner_profile_id, current_version_number,
                         created_at_utc, updated_at_utc)
                    VALUES (@SessionId, @ProfileId, 1, @Now, @Now);
                    SET @SetId = SCOPE_IDENTITY();
                    SET @NextVersion = 1;
                END
                ELSE
                BEGIN
                    /* Clear the confirmation BEFORE the version moves, so the
                       paired CHECK never sees a confirmed_version_number that
                       no longer equals current_version_number. */
                    UPDATE dbo.opportunity_requirement_sets
                    SET confirmed_version_number = NULL,
                        confirmed_by_user_id = NULL,
                        confirmed_at_utc = NULL,
                        current_version_number = @NextVersion,
                        updated_at_utc = @Now
                    WHERE opportunity_requirement_set_id = @SetId
                      AND owner_profile_id = @ProfileId;

                    /* SLICE OS-3 ADDITION, and it is not optional: the
                       analysis and the member''s responses reference these
                       statements, so without it re-reading the source fails
                       on a foreign key after the confirmation has already
                       been cleared.

                       IT ALSO DESTROYS MEMBER-AUTHORED TEXT, and that is
                       named rather than hidden. Re-reading the employer''s
                       source produces a NEW set of statements, so a response
                       the member wrote against an old statement has no
                       question left to answer. The alternative — orphaned
                       response rows the member can never see — would be
                       retained private text with nothing to show for it,
                       which is worse. The Review Requirements screen warns
                       before the member presses the control that reaches
                       here. */
                    DELETE citation_record
                    FROM dbo.opportunity_analysis_citations AS citation_record
                    JOIN dbo.opportunity_analysis_statements AS analysis_statement
                      ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                     AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                    JOIN dbo.opportunity_analyses AS analysis_record
                      ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                     AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                    JOIN dbo.opportunity_requirement_set_versions AS set_version
                      ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                     AND set_version.owner_profile_id = analysis_record.owner_profile_id
                    WHERE set_version.opportunity_requirement_set_id = @SetId
                      AND citation_record.owner_profile_id = @ProfileId;

                    DELETE analysis_statement
                    FROM dbo.opportunity_analysis_statements AS analysis_statement
                    JOIN dbo.opportunity_analyses AS analysis_record
                      ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                     AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                    JOIN dbo.opportunity_requirement_set_versions AS set_version
                      ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                     AND set_version.owner_profile_id = analysis_record.owner_profile_id
                    WHERE set_version.opportunity_requirement_set_id = @SetId
                      AND analysis_statement.owner_profile_id = @ProfileId;

                    DELETE analysis_record
                    FROM dbo.opportunity_analyses AS analysis_record
                    JOIN dbo.opportunity_requirement_set_versions AS set_version
                      ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                     AND set_version.owner_profile_id = analysis_record.owner_profile_id
                    WHERE set_version.opportunity_requirement_set_id = @SetId
                      AND analysis_record.owner_profile_id = @ProfileId;

                    DELETE response_record
                    FROM dbo.opportunity_responses AS response_record
                    JOIN dbo.opportunity_requirement_statements AS statement_record
                      ON statement_record.opportunity_requirement_statement_id = response_record.opportunity_requirement_statement_id
                     AND statement_record.owner_profile_id = response_record.owner_profile_id
                    JOIN dbo.opportunity_requirement_set_versions AS set_version
                      ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                     AND set_version.owner_profile_id = statement_record.owner_profile_id
                    WHERE set_version.opportunity_requirement_set_id = @SetId
                      AND response_record.owner_profile_id = @ProfileId;

                    DELETE statement_record
                    FROM dbo.opportunity_requirement_statements AS statement_record
                    JOIN dbo.opportunity_requirement_set_versions AS set_version
                      ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                     AND set_version.owner_profile_id = statement_record.owner_profile_id
                    WHERE set_version.opportunity_requirement_set_id = @SetId
                      AND statement_record.owner_profile_id = @ProfileId;

                    DELETE dbo.opportunity_requirement_set_versions
                    WHERE opportunity_requirement_set_id = @SetId
                      AND owner_profile_id = @ProfileId;
                END;

                INSERT dbo.opportunity_requirement_set_versions
                    (opportunity_requirement_set_id, owner_profile_id, version_number,
                     source_version_number, model_name, prompt_contract_version,
                     statement_count, proposed_at_utc)
                VALUES
                    (@SetId, @ProfileId, @NextVersion, @SourceVersionNumber, @ModelName,
                     @PromptContractVersion, @StatementCount, @Now);
                SET @VersionId = SCOPE_IDENTITY();

                INSERT dbo.opportunity_requirement_statements
                    (opportunity_requirement_set_version_id, owner_profile_id, ordinal,
                     span_start, span_length, employer_text, proposed_class,
                     proposed_explanation, proposed_structure_json)
                SELECT
                    @VersionId,
                    @ProfileId,
                    proposal.ordinal,
                    proposal.span_start,
                    proposal.span_length,
                    proposal.employer_text,
                    proposal.proposed_class,
                    proposal.proposed_explanation,
                    proposal.proposed_structure_json
                FROM OPENJSON(@StatementsJson)
                WITH
                (
                    ordinal int ''$.ordinal'',
                    span_start int ''$.span_start'',
                    span_length int ''$.span_length'',
                    employer_text nvarchar(2000) ''$.employer_text'',
                    proposed_class nvarchar(40) ''$.proposed_class'',
                    proposed_explanation nvarchar(1000) ''$.proposed_explanation'',
                    proposed_structure_json nvarchar(4000) ''$.proposed_structure_json''
                ) AS proposal;

                UPDATE dbo.opportunity_working_sessions
                SET workbench_state = N''review_requirements'', updated_at_utc = @Now
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                SELECT @SetKey = requirement_set.requirement_set_key
                FROM dbo.opportunity_requirement_sets AS requirement_set
                WHERE requirement_set.opportunity_requirement_set_id = @SetId
                  AND requirement_set.owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @SetKey AS requirement_set_key,
                       @NextVersion AS version_number, @StatementCount AS statement_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CorrectOpportunityRequirementStatementForOwner
            @UserKey nvarchar(300),
            @StatementKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @MemberClass nvarchar(40) = NULL,
            @MemberClarification nvarchar(max) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* The member''s reading of one statement. It writes member_class
               and member_clarification ONLY: proposed_class,
               proposed_explanation, and proposed_structure_json are never
               touched by any procedure in this file, so "PeerSlate proposed
               X, the member says Y" stays answerable for the life of the
               session.

               A correction clears the requirement-set confirmation for the
               same reason a source correction clears the source''s: a
               confirmed set must never describe a reading the member has
               since changed. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @StatementKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS statement_row_version,
                       CAST(NULL AS nvarchar(40)) AS member_class;
                RETURN;
            END;

            SET @MemberClarification = NULLIF(LTRIM(RTRIM(@MemberClarification)), N'''');
            IF (@MemberClass IS NOT NULL
                AND @MemberClass NOT IN (N''required_qualification'', N''preferred_qualification'',
                                         N''responsibility'', N''informational_statement''))
               OR (@MemberClarification IS NOT NULL
                   AND DATALENGTH(@MemberClarification) / 2 NOT BETWEEN 1 AND 2000)
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS binary(8)) AS statement_row_version,
                       CAST(NULL AS nvarchar(40)) AS member_class;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS statement_row_version,
                       CAST(NULL AS nvarchar(40)) AS member_class;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @StatementId bigint;
            DECLARE @SetId bigint;
            DECLARE @ProposedClass nvarchar(40);

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @StatementId = statement_record.opportunity_requirement_statement_id,
                    @SetId = requirement_set.opportunity_requirement_set_id,
                    @ProposedClass = statement_record.proposed_class
                FROM dbo.opportunity_requirement_statements AS statement_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = requirement_set.working_session_id
                 AND working_session.owner_profile_id = requirement_set.owner_profile_id
                WHERE statement_record.statement_key = @StatementKey
                  AND statement_record.owner_profile_id = @ProfileId
                  AND statement_record.row_version = @ExpectedRowVersion
                  AND set_version.version_number = requirement_set.current_version_number
                  AND working_session.expires_at_utc > @Now;

                IF @StatementId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS statement_row_version,
                           CAST(NULL AS nvarchar(40)) AS member_class;
                    RETURN;
                END;

                /* A member who selects the proposed class and leaves the
                   clarification empty has told PeerSlate nothing new. Storing
                   that as a member decision would let the screen claim they
                   corrected something they did not. */
                IF @MemberClass = @ProposedClass AND @MemberClarification IS NULL
                    SET @MemberClass = NULL;

                UPDATE dbo.opportunity_requirement_statements
                SET member_class = @MemberClass,
                    member_clarification = @MemberClarification,
                    member_updated_by_user_id = CASE
                        WHEN @MemberClass IS NULL AND @MemberClarification IS NULL
                        THEN NULL ELSE @UserId END,
                    member_updated_at_utc = CASE
                        WHEN @MemberClass IS NULL AND @MemberClarification IS NULL
                        THEN NULL ELSE @Now END
                WHERE opportunity_requirement_statement_id = @StatementId
                  AND owner_profile_id = @ProfileId;

                UPDATE dbo.opportunity_requirement_sets
                SET confirmed_version_number = NULL,
                    confirmed_by_user_id = NULL,
                    confirmed_at_utc = NULL,
                    updated_at_utc = @Now
                WHERE opportunity_requirement_set_id = @SetId
                  AND owner_profile_id = @ProfileId;

                /* SLICE OS-3 ADDITION. Correcting a statement un-confirms the
                   requirement set, and an analysis of an un-confirmed reading
                   is a result the member never asked for: it describes
                   requirements they have since changed. It goes with the
                   confirmation, in the same transaction.

                   The member''s RESPONSES deliberately survive. They are
                   member-authored context about the employer''s requirement,
                   not part of PeerSlate''s reading of it, and the statement
                   they are attached to still exists. */
                DELETE citation_record
                FROM dbo.opportunity_analysis_citations AS citation_record
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                 AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                WHERE set_version.opportunity_requirement_set_id = @SetId
                  AND citation_record.owner_profile_id = @ProfileId;

                DELETE analysis_statement
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                WHERE set_version.opportunity_requirement_set_id = @SetId
                  AND analysis_statement.owner_profile_id = @ProfileId;

                DELETE analysis_record
                FROM dbo.opportunity_analyses AS analysis_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                WHERE set_version.opportunity_requirement_set_id = @SetId
                  AND analysis_record.owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    CONVERT(binary(8), statement_record.row_version) AS statement_row_version,
                    statement_record.member_class
                FROM dbo.opportunity_requirement_statements AS statement_record
                WHERE statement_record.opportunity_requirement_statement_id = @StatementId
                  AND statement_record.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ConfirmOpportunityRequirementsForOwner
            @UserKey nvarchar(300),
            @RequirementSetKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Checkpoint 2 of 2 (handoff section 2). Confirming records which
               requirement-set version the member accepted. It saves no slate,
               produces no alignment result, and calls no AI — the analysis it
               precedes is slice OS-3 and does not exist. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @RequirementSetKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS set_row_version,
                       CAST(NULL AS int) AS confirmed_version_number;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS set_row_version,
                       CAST(NULL AS int) AS confirmed_version_number;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SetId bigint;
            DECLARE @SessionId bigint;
            DECLARE @VersionNumber int;

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @SetId = requirement_set.opportunity_requirement_set_id,
                    @SessionId = requirement_set.working_session_id,
                    @VersionNumber = requirement_set.current_version_number
                FROM dbo.opportunity_requirement_sets AS requirement_set WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = requirement_set.working_session_id
                 AND working_session.owner_profile_id = requirement_set.owner_profile_id
                WHERE requirement_set.requirement_set_key = @RequirementSetKey
                  AND requirement_set.owner_profile_id = @ProfileId
                  AND requirement_set.row_version = @ExpectedRowVersion
                  AND working_session.expires_at_utc > @Now;

                IF @SetId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS set_row_version,
                           CAST(NULL AS int) AS confirmed_version_number;
                    RETURN;
                END;

                UPDATE dbo.opportunity_requirement_sets
                SET confirmed_version_number = @VersionNumber,
                    confirmed_by_user_id = @UserId,
                    confirmed_at_utc = @Now,
                    updated_at_utc = @Now
                WHERE opportunity_requirement_set_id = @SetId
                  AND owner_profile_id = @ProfileId;

                UPDATE dbo.opportunity_working_sessions
                SET workbench_state = N''requirements_confirmed'', updated_at_utc = @Now
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    CONVERT(binary(8), requirement_set.row_version) AS set_row_version,
                    @VersionNumber AS confirmed_version_number
                FROM dbo.opportunity_requirement_sets AS requirement_set
                WHERE requirement_set.opportunity_requirement_set_id = @SetId
                  AND requirement_set.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* ============================================================
       SLICE OS-3 PROCEDURES

       Same discipline as every procedure above, plus one rule this slice
       learned the hard way from the 2026-08-04 gate: EVERY rejection return
       inside a transaction happens BEFORE any mutation. A procedure that
       deletes first and validates afterwards destroys member data and then
       tells its caller nothing happened.

       None of these accepts an owner id. None writes a Workshop or Moment
       row - the evidence read below is strictly read-only. And none of them
       has anywhere to put a score: there is no such column.
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListOpportunityEvidenceForOwner
            @UserKey nvarchar(300),
            @MaxItems int = 24
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* The grounding allowlist (handoff sections 8 and 10). READ ONLY,
               and deliberately narrow: this returns the member''s CONFIRMED
               Workshop knowledge items at their confirmed version, and
               nothing else. A draft, a suggestion, or an archived item is not
               something the member has authorized as evidence about
               themselves, so it never reaches a prompt.

               Evidence is referenced, never copied: this procedure reads the
               Workshop tables and writes none of them. Moments are part of
               the architectural contract (handoff section 17-Q2) and are NOT
               read here - slice OS-3 grounds on knowledge items only, and the
               screen says so. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;
            IF @MaxItems IS NULL OR @MaxItems < 1 OR @MaxItems > 24 SET @MaxItems = 24;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT TOP (@MaxItems)
                item.knowledge_item_key AS evidence_key,
                item.confirmed_version_number AS evidence_version,
                item_version.title AS evidence_title,
                item_version.approved_wording AS evidence_body,
                item.updated_at_utc AS evidence_updated_at_utc
            FROM dbo.knowledge_items AS item
            JOIN dbo.knowledge_item_versions AS item_version
              ON item_version.knowledge_item_id = item.knowledge_item_id
             AND item_version.owner_profile_id = item.owner_profile_id
             AND item_version.version_number = item.confirmed_version_number
            WHERE item.owner_profile_id = @ProfileId
              AND item.item_status = N''confirmed''
              AND item.archived_at_utc IS NULL
            ORDER BY item.updated_at_utc DESC, item.knowledge_item_id DESC;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunityAnalysisForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Four result sets: the analysis, its per-qualification results,
               their citations, and the member''s own responses.

               An analysis pinned to a SUPERSEDED requirement-set version
               returns nothing at all, for the same reason the requirement
               read refuses a superseded set: it describes requirements the
               member has since changed, and showing it would put a reading in
               their mouth. The responses are returned regardless, because
               they are the member''s own words and belong to the statement,
               not to any one analysis run. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @VersionId bigint;
            SELECT @VersionId = set_version.opportunity_requirement_set_version_id
            FROM dbo.opportunity_requirement_set_versions AS set_version
            JOIN dbo.opportunity_requirement_sets AS requirement_set
              ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
             AND requirement_set.owner_profile_id = set_version.owner_profile_id
            JOIN dbo.opportunity_working_sessions AS working_session
              ON working_session.working_session_id = requirement_set.working_session_id
             AND working_session.owner_profile_id = requirement_set.owner_profile_id
            JOIN dbo.opportunity_sources AS source_record
              ON source_record.working_session_id = working_session.working_session_id
             AND source_record.owner_profile_id = working_session.owner_profile_id
            WHERE requirement_set.owner_profile_id = @ProfileId
              AND set_version.version_number = requirement_set.current_version_number
              AND set_version.source_version_number = source_record.current_version_number
              AND working_session.expires_at_utc > SYSUTCDATETIME();

            IF @VersionId IS NULL RETURN;

            DECLARE @AnalysisId bigint;
            SELECT @AnalysisId = analysis_record.opportunity_analysis_id
            FROM dbo.opportunity_analyses AS analysis_record
            WHERE analysis_record.opportunity_requirement_set_version_id = @VersionId
              AND analysis_record.owner_profile_id = @ProfileId;

            SELECT
                analysis_record.analysis_key,
                CONVERT(binary(8), analysis_record.row_version) AS analysis_row_version,
                analysis_record.source_version_number,
                analysis_record.requirement_version_number,
                analysis_record.model_name,
                analysis_record.prompt_contract_version,
                analysis_record.evidence_considered_count,
                analysis_record.qualification_count,
                analysis_record.analyzed_at_utc
            FROM dbo.opportunity_analyses AS analysis_record
            WHERE analysis_record.opportunity_analysis_id = @AnalysisId
              AND analysis_record.owner_profile_id = @ProfileId;

            SELECT
                statement_record.statement_key,
                analysis_statement.ordinal,
                analysis_statement.derived_status,
                analysis_statement.citation_count
            FROM dbo.opportunity_analysis_statements AS analysis_statement
            JOIN dbo.opportunity_requirement_statements AS statement_record
              ON statement_record.opportunity_requirement_statement_id = analysis_statement.opportunity_requirement_statement_id
             AND statement_record.owner_profile_id = analysis_statement.owner_profile_id
            WHERE analysis_statement.opportunity_analysis_id = @AnalysisId
              AND analysis_statement.owner_profile_id = @ProfileId
            ORDER BY analysis_statement.ordinal;

            SELECT
                statement_record.statement_key,
                citation_record.ordinal,
                citation_record.clause_ordinal,
                citation_record.covered_text,
                citation_record.evidence_kind,
                citation_record.evidence_key,
                citation_record.evidence_version,
                citation_record.evidence_title,
                citation_record.excerpt
            FROM dbo.opportunity_analysis_citations AS citation_record
            JOIN dbo.opportunity_analysis_statements AS analysis_statement
              ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
             AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
            JOIN dbo.opportunity_requirement_statements AS statement_record
              ON statement_record.opportunity_requirement_statement_id = analysis_statement.opportunity_requirement_statement_id
             AND statement_record.owner_profile_id = analysis_statement.owner_profile_id
            WHERE analysis_statement.opportunity_analysis_id = @AnalysisId
              AND citation_record.owner_profile_id = @ProfileId
            ORDER BY analysis_statement.ordinal, citation_record.ordinal;

            SELECT
                statement_record.statement_key,
                response_record.response_key,
                CONVERT(binary(8), response_record.row_version) AS response_row_version,
                response_record.response_kind,
                response_record.response_text,
                response_record.authored_via,
                response_record.connected_evidence_kind,
                response_record.connected_evidence_key,
                response_record.connected_evidence_version,
                response_record.connected_evidence_title,
                response_record.updated_at_utc
            FROM dbo.opportunity_responses AS response_record
            JOIN dbo.opportunity_requirement_statements AS statement_record
              ON statement_record.opportunity_requirement_statement_id = response_record.opportunity_requirement_statement_id
             AND statement_record.owner_profile_id = response_record.owner_profile_id
            WHERE statement_record.opportunity_requirement_set_version_id = @VersionId
              AND response_record.owner_profile_id = @ProfileId
            ORDER BY statement_record.ordinal;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunityAnalysisForOwner
            @UserKey nvarchar(300),
            @RequirementSetKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @ModelName nvarchar(4000),
            @PromptContractVersion nvarchar(4000),
            @EvidenceConsideredCount int,
            @ResultsJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Records one validated alignment analysis for the CONFIRMED
               requirement set, replacing any earlier one for that version.
               The status values it stores are derived by the application from
               the citations, never returned by a model - see the
               composition-boundary block in
               services/opportunity_analysis_service.py.

               ORDER OF OPERATIONS IS LOAD-BEARING (2026-08-04 gate, defect
               1). Every guard below runs, and every rejection returns, BEFORE
               the first DELETE. A procedure that clears the previous analysis
               and then discovers the payload is invalid destroys a result the
               member was reading and returns ''invalid'', which tells its
               caller nothing happened.

               2026-08-04 INDEPENDENT REVIEW, FINDING F8. That claim used to
               be false for the CITATIONS: only the per-qualification rows
               were checked up here, and the eight citation constraints could
               not fire until the INSERT, which is after all three DELETEs.
               XACT_ABORT plus the CATCH rollback meant no member data was
               ever at risk, but the caller got a 503 where it should have got
               ''invalid''. The citations are now shredded and validated in
               this same guard phase, so the sentence above is true of the
               whole payload.

               2026-08-04 INDEPENDENT REVIEW, FINDING F7. The evidence
               IDENTITY is re-derived here and is no longer taken from the
               payload. usp_SaveOpportunityResponseForOwner already worked
               this way: it accepts a key and reads the version, the title and
               the kind out of the member''s own confirmed items. This
               procedure accepted evidence_key, evidence_version,
               evidence_title and evidence_kind verbatim, with no lookup at
               all - so nothing checked that a cited key was the member''s own,
               that the item was confirmed and unarchived, or that the version
               pinned beside it was the confirmed one.

               `excerpt` and `covered_text` are still taken from the payload,
               and that is correct: they are verbatim spans the analysis
               service already resolved against the stored evidence and the
               employer''s confirmed clause. What could not be taken on trust
               was WHOSE record they came from. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @RequirementSetKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS analysis_key,
                       CAST(NULL AS int) AS qualification_count;
                RETURN;
            END;

            IF @ModelName IS NULL OR DATALENGTH(@ModelName) / 2 NOT BETWEEN 1 AND 100
               OR @PromptContractVersion IS NULL
               OR DATALENGTH(@PromptContractVersion) / 2 NOT BETWEEN 1 AND 60
               OR @EvidenceConsideredCount IS NULL
               OR @EvidenceConsideredCount NOT BETWEEN 0 AND 24
               OR @ResultsJson IS NULL
               OR ISJSON(@ResultsJson) <> 1
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS analysis_key,
                       CAST(NULL AS int) AS qualification_count;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS analysis_key,
                       CAST(NULL AS int) AS qualification_count;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SetId bigint;
            DECLARE @VersionId bigint;
            DECLARE @VersionNumber int;
            DECLARE @SourceVersionNumber int;
            DECLARE @AnalysisId bigint;
            DECLARE @AnalysisKey uniqueidentifier;
            DECLARE @QualificationCount int = 0;
            DECLARE @MatchedCount int = 0;
            DECLARE @Results TABLE
            (
                statement_key uniqueidentifier NOT NULL PRIMARY KEY,
                derived_status nvarchar(30) NOT NULL,
                citation_count int NOT NULL
            );
            /* Finding F8. Every text column here is nvarchar(max) even though
               the columns they land in are narrower. That is the idiom this
               file already documents for @IdempotencyKey: a NARROW OPENJSON
               declaration silently TRUNCATES an over-length value, so the
               guard measures a string the caller never sent and the real
               length is discovered later by a CHECK constraint - as a 500,
               after the DELETEs. Read wide, measure the truth, refuse
               honestly.

               evidence_version and evidence_title carry no payload value.
               They are filled in below from the member''s own confirmed
               Workshop item (finding F7). */
            DECLARE @Citations TABLE
            (
                statement_key uniqueidentifier NOT NULL,
                ordinal int NULL,
                clause_ordinal int NULL,
                covered_text nvarchar(max) NULL,
                evidence_key uniqueidentifier NULL,
                excerpt nvarchar(max) NULL,
                evidence_version int NULL,
                evidence_title nvarchar(200) NULL
            );

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT
                    @SetId = requirement_set.opportunity_requirement_set_id,
                    @VersionId = set_version.opportunity_requirement_set_version_id,
                    @VersionNumber = set_version.version_number,
                    @SourceVersionNumber = set_version.source_version_number
                FROM dbo.opportunity_requirement_sets AS requirement_set WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_id = requirement_set.opportunity_requirement_set_id
                 AND set_version.owner_profile_id = requirement_set.owner_profile_id
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = requirement_set.working_session_id
                 AND working_session.owner_profile_id = requirement_set.owner_profile_id
                WHERE requirement_set.requirement_set_key = @RequirementSetKey
                  AND requirement_set.owner_profile_id = @ProfileId
                  AND requirement_set.row_version = @ExpectedRowVersion
                  AND set_version.version_number = requirement_set.current_version_number
                  AND requirement_set.confirmed_version_number = requirement_set.current_version_number
                  AND working_session.expires_at_utc > @Now;

                IF @VersionId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS analysis_key,
                           CAST(NULL AS int) AS qualification_count;
                    RETURN;
                END;

                INSERT @Results (statement_key, derived_status, citation_count)
                SELECT result.statement_key, result.derived_status, result.citation_count
                FROM OPENJSON(@ResultsJson)
                WITH
                (
                    statement_key uniqueidentifier ''$.statement_key'',
                    derived_status nvarchar(30) ''$.derived_status'',
                    citation_count int ''$.citation_count''
                ) AS result;

                SELECT @QualificationCount = COUNT(*) FROM @Results;

                /* Every qualification named has to be a statement of THIS
                   requirement-set version and THIS owner. Counting the join
                   is what stops a caller attaching an analysis to somebody
                   else''s statement, and it runs before anything is written. */
                SELECT @MatchedCount = COUNT(*)
                FROM @Results AS result
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.statement_key = result.statement_key
                 AND statement_record.owner_profile_id = @ProfileId
                 AND statement_record.opportunity_requirement_set_version_id = @VersionId;

                IF @QualificationCount < 1
                   OR @QualificationCount > 40
                   OR @MatchedCount <> @QualificationCount
                   OR EXISTS
                   (
                       SELECT 1 FROM @Results
                       WHERE derived_status NOT IN (N''supported'', N''partially_supported'',
                                                    N''not_enough_information'')
                          OR citation_count < 0
                          OR citation_count > 24
                          OR (citation_count = 0 AND derived_status <> N''not_enough_information'')
                          OR (citation_count > 0 AND derived_status = N''not_enough_information'')
                   )
                BEGIN
                    /* BEFORE any mutation. The member''s previous analysis and
                       every response they wrote are untouched. */
                    COMMIT TRANSACTION;
                    SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS analysis_key,
                           CAST(NULL AS int) AS qualification_count;
                    RETURN;
                END;

                /* ----------------------------------------------------------
                   CITATIONS: shredded, resolved and validated HERE, before
                   the first DELETE (findings F7 and F8).
                   ---------------------------------------------------------- */
                INSERT @Citations
                    (statement_key, ordinal, clause_ordinal, covered_text,
                     evidence_key, excerpt)
                SELECT
                    result.statement_key,
                    citation.ordinal,
                    citation.clause_ordinal,
                    citation.covered_text,
                    citation.evidence_key,
                    citation.excerpt
                FROM OPENJSON(@ResultsJson)
                WITH
                (
                    statement_key uniqueidentifier ''$.statement_key'',
                    citations nvarchar(max) ''$.citations'' AS JSON
                ) AS result
                CROSS APPLY OPENJSON(result.citations)
                WITH
                (
                    ordinal int ''$.ordinal'',
                    clause_ordinal int ''$.clause_ordinal'',
                    covered_text nvarchar(max) ''$.covered_text'',
                    evidence_key uniqueidentifier ''$.evidence_key'',
                    excerpt nvarchar(max) ''$.excerpt''
                ) AS citation;

                /* THE EVIDENCE IDENTITY IS READ, NOT ACCEPTED (finding F7).
                   Exactly the sibling procedure''s lookup: the caller supplies
                   a key, and the version, the title and the kind come from
                   the member''s OWN confirmed, unarchived Workshop item. A key
                   belonging to somebody else, to a draft, to an archived item,
                   or to nothing at all resolves to NULL and is refused below.
                   evidence_kind is likewise set by this procedure, not sent:
                   slice OS-3 grounds on knowledge items only. */
                UPDATE citation
                SET evidence_version = item.confirmed_version_number,
                    evidence_title = item_version.title
                FROM @Citations AS citation
                JOIN dbo.knowledge_items AS item
                  ON item.knowledge_item_key = citation.evidence_key
                 AND item.owner_profile_id = @ProfileId
                 AND item.item_status = N''confirmed''
                 AND item.archived_at_utc IS NULL
                JOIN dbo.knowledge_item_versions AS item_version
                  ON item_version.knowledge_item_id = item.knowledge_item_id
                 AND item_version.owner_profile_id = item.owner_profile_id
                 AND item_version.version_number = item.confirmed_version_number;

                IF EXISTS
                (
                    SELECT 1 FROM @Citations AS citation
                    WHERE citation.ordinal IS NULL OR citation.ordinal < 1
                       OR citation.clause_ordinal IS NULL OR citation.clause_ordinal < 1
                       OR citation.covered_text IS NULL
                       OR DATALENGTH(citation.covered_text) / 2 NOT BETWEEN 1 AND 200
                       OR citation.excerpt IS NULL
                       OR DATALENGTH(citation.excerpt) / 2 NOT BETWEEN 1 AND 400
                       OR citation.evidence_key IS NULL
                       /* Not the member''s own confirmed, unarchived item. */
                       OR citation.evidence_version IS NULL
                       OR citation.evidence_title IS NULL
                       OR DATALENGTH(citation.evidence_title) / 2 NOT BETWEEN 1 AND 200
                       OR citation.evidence_version < 1
                       /* A citation hanging off a qualification the payload
                          did not declare a result for. */
                       OR NOT EXISTS
                          (
                              SELECT 1 FROM @Results AS result
                              WHERE result.statement_key = citation.statement_key
                          )
                )
                   OR EXISTS
                   (
                       /* UQ_opportunity_analysis_citations_ordinal, checked
                          here rather than met as a 2627 after the DELETEs. */
                       SELECT 1 FROM @Citations
                       GROUP BY statement_key, ordinal
                       HAVING COUNT(*) > 1
                   )
                   OR EXISTS
                   (
                       /* Finding F8, last part. citation_count is STORED, and
                          CK_opportunity_analysis_statements_citation_pair
                          pairs it with the derived status - so the comment on
                          that constraint claims the screen''s three states
                          "cannot drift away from the evidence behind them".
                          That claim needs the stored count to be the number
                          of citation ROWS actually written, which nothing
                          checked: the count came from the payload and the
                          rows came from a different part of the same payload.
                          They are reconciled here. */
                       SELECT 1 FROM @Results AS result
                       WHERE result.citation_count <>
                             (
                                 SELECT COUNT(*) FROM @Citations AS citation
                                 WHERE citation.statement_key = result.statement_key
                             )
                   )
                BEGIN
                    /* Still BEFORE any mutation. */
                    COMMIT TRANSACTION;
                    SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS analysis_key,
                           CAST(NULL AS int) AS qualification_count;
                    RETURN;
                END;

                DELETE citation_record
                FROM dbo.opportunity_analysis_citations AS citation_record
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                 AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                WHERE analysis_record.opportunity_requirement_set_version_id = @VersionId
                  AND citation_record.owner_profile_id = @ProfileId;

                DELETE analysis_statement
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                WHERE analysis_record.opportunity_requirement_set_version_id = @VersionId
                  AND analysis_statement.owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_analyses
                WHERE opportunity_requirement_set_version_id = @VersionId
                  AND owner_profile_id = @ProfileId;

                INSERT dbo.opportunity_analyses
                    (opportunity_requirement_set_version_id, owner_profile_id,
                     source_version_number, requirement_version_number, model_name,
                     prompt_contract_version, evidence_considered_count,
                     qualification_count, analyzed_at_utc)
                VALUES
                    (@VersionId, @ProfileId, @SourceVersionNumber, @VersionNumber,
                     @ModelName, @PromptContractVersion, @EvidenceConsideredCount,
                     @QualificationCount, @Now);
                SET @AnalysisId = SCOPE_IDENTITY();

                INSERT dbo.opportunity_analysis_statements
                    (opportunity_analysis_id, opportunity_requirement_statement_id,
                     owner_profile_id, ordinal, derived_status, citation_count)
                SELECT
                    @AnalysisId,
                    statement_record.opportunity_requirement_statement_id,
                    @ProfileId,
                    statement_record.ordinal,
                    result.derived_status,
                    result.citation_count
                FROM @Results AS result
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.statement_key = result.statement_key
                 AND statement_record.owner_profile_id = @ProfileId
                 AND statement_record.opportunity_requirement_set_version_id = @VersionId;

                INSERT dbo.opportunity_analysis_citations
                    (opportunity_analysis_statement_id, owner_profile_id, ordinal,
                     clause_ordinal, covered_text, evidence_kind, evidence_key,
                     evidence_version, evidence_title, excerpt)
                /* Read from the validated, RESOLVED table variable rather
                   than re-shredding the payload: the identity written here is
                   the one this procedure derived from the member''s own
                   confirmed item, and evidence_kind is a literal. */
                SELECT
                    analysis_statement.opportunity_analysis_statement_id,
                    @ProfileId,
                    citation.ordinal,
                    citation.clause_ordinal,
                    citation.covered_text,
                    N''knowledge_item'',
                    citation.evidence_key,
                    citation.evidence_version,
                    citation.evidence_title,
                    citation.excerpt
                FROM @Citations AS citation
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.statement_key = citation.statement_key
                 AND statement_record.owner_profile_id = @ProfileId
                 AND statement_record.opportunity_requirement_set_version_id = @VersionId
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_id = @AnalysisId
                 AND analysis_statement.opportunity_requirement_statement_id = statement_record.opportunity_requirement_statement_id
                 AND analysis_statement.owner_profile_id = @ProfileId;

                SELECT @AnalysisKey = analysis_record.analysis_key
                FROM dbo.opportunity_analyses AS analysis_record
                WHERE analysis_record.opportunity_analysis_id = @AnalysisId
                  AND analysis_record.owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @AnalysisKey AS analysis_key,
                       @QualificationCount AS qualification_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunityResponseForOwner
            @UserKey nvarchar(300),
            @StatementKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @ResponseKind nvarchar(30),
            @ResponseText nvarchar(max) = NULL,
            @AuthoredVia nvarchar(30) = N''typed'',
            @ConnectedEvidenceKey uniqueidentifier = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* One member response per qualification (image 04''s response
               rail). This is MEMBER-ATTRIBUTED CONTEXT and is stored apart
               from both the AI proposal and the authorized evidence: it never
               becomes a citation, it never changes a derived status, and it
               never edits the member''s evidence library.

               The connected-evidence path takes only a KEY. Its title and
               version are read here from the member''s own confirmed items,
               so a caller cannot label somebody else''s record or pin a
               version that does not exist - and an item that is not the
               member''s own confirmed evidence is refused BEFORE anything is
               written. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @ResponseText = NULLIF(LTRIM(RTRIM(@ResponseText)), N'''');
            IF @AuthoredVia IS NULL SET @AuthoredVia = N''typed'';

            IF @UserKey IS NULL OR @StatementKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS response_key,
                       CAST(NULL AS nvarchar(30)) AS response_kind;
                RETURN;
            END;

            IF @ResponseKind NOT IN (N''tell_more'', N''connect_evidence'', N''real_example'',
                                     N''confirm_not_have'', N''skip'')
               OR @AuthoredVia NOT IN (N''typed'', N''spoken'')
               OR (@ResponseKind IN (N''tell_more'', N''real_example'')
                   AND (@ResponseText IS NULL
                        OR DATALENGTH(@ResponseText) / 2 NOT BETWEEN 1 AND 4000
                        OR @ConnectedEvidenceKey IS NOT NULL))
               OR (@ResponseKind = N''connect_evidence''
                   AND (@ConnectedEvidenceKey IS NULL OR @ResponseText IS NOT NULL))
               OR (@ResponseKind IN (N''confirm_not_have'', N''skip'')
                   AND (@ResponseText IS NOT NULL OR @ConnectedEvidenceKey IS NOT NULL))
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS response_key,
                       CAST(NULL AS nvarchar(30)) AS response_kind;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS response_key,
                       CAST(NULL AS nvarchar(30)) AS response_kind;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @StatementId bigint;
            DECLARE @ResponseKey uniqueidentifier;
            DECLARE @EvidenceVersion int;
            DECLARE @EvidenceTitle nvarchar(200);
            DECLARE @EvidenceKind nvarchar(30);

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT @StatementId = statement_record.opportunity_requirement_statement_id
                FROM dbo.opportunity_requirement_statements AS statement_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = requirement_set.working_session_id
                 AND working_session.owner_profile_id = requirement_set.owner_profile_id
                WHERE statement_record.statement_key = @StatementKey
                  AND statement_record.owner_profile_id = @ProfileId
                  AND statement_record.row_version = @ExpectedRowVersion
                  AND set_version.version_number = requirement_set.current_version_number
                  AND working_session.expires_at_utc > @Now;

                IF @StatementId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS response_key,
                           CAST(NULL AS nvarchar(30)) AS response_kind;
                    RETURN;
                END;

                IF @ResponseKind = N''connect_evidence''
                BEGIN
                    SELECT
                        @EvidenceVersion = item.confirmed_version_number,
                        @EvidenceTitle = item_version.title
                    FROM dbo.knowledge_items AS item
                    JOIN dbo.knowledge_item_versions AS item_version
                      ON item_version.knowledge_item_id = item.knowledge_item_id
                     AND item_version.owner_profile_id = item.owner_profile_id
                     AND item_version.version_number = item.confirmed_version_number
                    WHERE item.knowledge_item_key = @ConnectedEvidenceKey
                      AND item.owner_profile_id = @ProfileId
                      AND item.item_status = N''confirmed''
                      AND item.archived_at_utc IS NULL;

                    IF @EvidenceVersion IS NULL
                    BEGIN
                        /* Not the member''s own confirmed evidence. Refused
                           BEFORE any mutation, and told apart from a
                           concurrency conflict so the screen can say which
                           it was. */
                        COMMIT TRANSACTION;
                        SELECT N''invalid'' AS outcome, CAST(NULL AS uniqueidentifier) AS response_key,
                               CAST(NULL AS nvarchar(30)) AS response_kind;
                        RETURN;
                    END;
                    SET @EvidenceKind = N''knowledge_item'';
                END;

                UPDATE dbo.opportunity_responses
                SET response_kind = @ResponseKind,
                    response_text = @ResponseText,
                    authored_via = @AuthoredVia,
                    connected_evidence_kind = @EvidenceKind,
                    connected_evidence_key = CASE WHEN @ResponseKind = N''connect_evidence''
                        THEN @ConnectedEvidenceKey ELSE NULL END,
                    connected_evidence_version = @EvidenceVersion,
                    connected_evidence_title = @EvidenceTitle,
                    updated_at_utc = @Now
                WHERE opportunity_requirement_statement_id = @StatementId
                  AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT = 0
                    INSERT dbo.opportunity_responses
                        (opportunity_requirement_statement_id, owner_profile_id,
                         response_kind, response_text, authored_via,
                         connected_evidence_kind, connected_evidence_key,
                         connected_evidence_version, connected_evidence_title,
                         created_by_user_id, created_at_utc, updated_at_utc)
                    VALUES
                        (@StatementId, @ProfileId, @ResponseKind, @ResponseText,
                         @AuthoredVia, @EvidenceKind,
                         CASE WHEN @ResponseKind = N''connect_evidence''
                             THEN @ConnectedEvidenceKey ELSE NULL END,
                         @EvidenceVersion, @EvidenceTitle, @UserId, @Now, @Now);

                SELECT @ResponseKey = response_key
                FROM dbo.opportunity_responses
                WHERE opportunity_requirement_statement_id = @StatementId
                  AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @ResponseKey AS response_key,
                       @ResponseKind AS response_kind;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* ------------------------------------------------------------
       Fingerprint every procedure this migration owns, so the rollback
       can refuse to drop one that changed afterwards (the
       PS-WORKSHOP-001 idiom).
       ------------------------------------------------------------ */
    DECLARE @ProcedureHashPropertyName sysname = N'PS_OPPSLATE_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_GetOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunitySourceForOwner'),
        (N'usp_CorrectOpportunitySourceForOwner'),
        (N'usp_ConfirmOpportunitySourceForOwner'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_GetOpportunitySourceReviewForOwner'),
        (N'usp_SaveOpportunitySourceReviewForOwner'),
        (N'usp_ResolveOpportunitySourceConcernForOwner'),
        (N'usp_GetOpportunityRequirementsForOwner'),
        (N'usp_SaveOpportunityRequirementProposalForOwner'),
        (N'usp_CorrectOpportunityRequirementStatementForOwner'),
        (N'usp_ConfirmOpportunityRequirementsForOwner'),
        (N'usp_ListOpportunityEvidenceForOwner'),
        (N'usp_GetOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityResponseForOwner');

    DECLARE @ProtectedProcedureName sysname;
    DECLARE @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures
        ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P') IS NULL
            THROW 53407, 'A required Opportunity Slate procedure was not created.', 1;

        SELECT @ProtectedProcedureHash = CONVERT
        (
            nvarchar(64),
            HASHBYTES
            (
                'SHA2_256',
                OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P'))
            ),
            2
        );

        IF EXISTS
        (
            SELECT 1
            FROM sys.extended_properties AS property
            WHERE property.class = 1
              AND property.major_id = OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
              AND property.minor_id = 0
              AND property.name = @ProcedureHashPropertyName
        )
            EXEC sys.sp_updateextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;

        DELETE @ProtectedProcedures
        WHERE procedure_name = @ProtectedProcedureName;
    END;

    /* The ledger is how an operator answers "which revision does this
       database carry?", so it has to describe what is actually here. */
    /* dbo.schema_migrations.description is nvarchar(500). Keep this string
       inside that bound: the ledger write is what an operator reads to answer
       "which revision does this database carry?", and an over-long value
       aborts the whole migration on the final statement. */
    DECLARE @OppSlateDescription nvarchar(500) =
        N'Slices OS-1/OS-2/OS-3: Opportunity Slate ephemeral working session (working_sessions / sources / source_versions), its AI-proposal store (source_reviews / source_concerns / requirement_sets / requirement_set_versions / requirement_statements), the grounded alignment analysis and member responses (analyses / analysis_statements / analysis_citations / responses), seventeen owner-scoped procedures, and the expired-working-data purge. No score, percentage, ranking or verdict column exists.';

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-OPPSLATE-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-OPPSLATE-001',
            @OppSlateDescription,
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-OPPSLATE-001"}';
    END;
    ELSE
    BEGIN
        /* UPGRADE OVER THE SLICE OS-1 REVISION (isolated SQL gate,
           2026-08-04, defect 2). The row already exists, so the INSERT above
           is skipped and the ledger kept describing a three-table, six-
           procedure migration on a database that now carries eight tables
           and thirteen procedures. Correct the description in place.

           applied_at_utc is deliberately NOT moved. It records when
           PS-OPPSLATE-001 first landed, the rollback's "a later migration is
           present" guard compares against it, and re-running this file must
           stay a genuine no-op. Once the description is already correct the
           UPDATE matches nothing, so a second apply still changes nothing
           and still appends no audit event. */
        UPDATE dbo.schema_migrations
        SET description = @OppSlateDescription
        WHERE migration_id = N'PS-OPPSLATE-001'
          AND description <> @OppSlateDescription;
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
