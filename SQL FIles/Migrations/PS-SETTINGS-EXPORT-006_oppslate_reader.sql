/* ============================================================
   PS-SETTINGS-EXPORT-006 - account export Opportunity Slate reader
   (replacement package 4, the FINAL content reader of the accepted
   2026-08-29 reader topology)

   Read-only, owner-scoped SQL reader procedures for EXACTLY the member's
   own DURABLE saved Opportunity Slate records, directive-trimmed. This
   migration creates ONLY procedures. It creates no table, no trigger, no
   index, and writes nothing anywhere except its own ledger row.

   WHAT "DURABLE" MEANS HERE, DERIVED FROM THE SCHEMA, NOT ASSUMED. The
   writer brief for this package named an expectation ("saved-slate/
   results/qualifications/evidence-class tables from 001-003 and the 004
   replacement''s durable member tables: opportunity_source_identities,
   opportunity_requirement_review_events, opportunity_member_takes") and
   explicitly instructed judging each table against the real schema rather
   than trusting that expectation. All four PS-OPPSLATE-001..004 migration
   files under SQL FIles/Migrations/proposed/ were read in full before any
   allowlist decision below was made. The result contradicts the "expect"
   framing on one material point, recorded here because it changes this
   migration''s entire table list:

     PS-OPPSLATE-001 (OS-1/OS-2, 8 tables: opportunity_working_sessions,
     opportunity_sources, opportunity_source_versions,
     opportunity_source_reviews, opportunity_source_concerns,
     opportunity_requirement_sets, opportunity_requirement_set_versions,
     opportunity_requirement_statements) is EPHEMERAL BY DESIGN, per its
     own header: "a working session is infrastructure. It is never listed,
     exported, projected, or shared." Physically destroyed by
     usp_PurgeExpiredOpportunityWorkingData / cascade-deleted by
     usp_DeleteOpportunityWorkingSessionForOwner.

     PS-OPPSLATE-002 (OS-3, 4 tables: opportunity_analyses,
     opportunity_analysis_statements, opportunity_analysis_citations,
     opportunity_responses) is EQUALLY EPHEMERAL, confirmed not by
     inference but by reading the actual DELETE statements
     PS-OPPSLATE-004''s takeover of usp_PurgeExpiredOpportunityWorkingData
     issues against all four of these tables, joined back to
     @ExpiredSessions on every call. PS-OPPSLATE-002''s own header states
     "the durable, versioned record is OS-4''s saved slate" -- i.e. OS-3
     itself, in its own words, is not that record.

     PS-OPPSLATE-003 (OS-4, 4 tables: opportunity_slates,
     opportunity_saved_results, opportunity_saved_qualifications,
     opportunity_saved_evidence) is the ONLY durable table group in this
     entire schema. Its own header states this in terms that leave no
     ambiguity: "EVERYTHING ABOVE THIS LINE IS EPHEMERAL... This is the
     first table group in this file that survives expiry, survives the
     member deleting their working session, and survives the source being
     replaced." None of these four tables carries a foreign key into any
     OS-1/OS-2/OS-3 table; a saved result COPIES what it shows rather than
     referencing the ephemeral rows it was computed from, precisely so the
     working tables can be purged with no conditional retention logic.

     PS-OPPSLATE-004 ("the replacement" -- a separate, parallel R1 shell
     architecture, owner decision 2026-08-11: replace, not evolve -- ships
     BESIDE 001-003, which stay production truth for the legacy room
     forever) adds three new tables:
     opportunity_source_identities, opportunity_requirement_review_events,
     opportunity_member_takes. THESE ARE EPHEMERAL TOO, not durable, DESPITE
     living in the migration titled "replacement" and despite two of them
     never having been written by any procedure at all
     (opportunity_requirement_review_events and opportunity_member_takes
     are SHAPE ONLY in PS-OPPSLATE-004 -- "Their PROCEDURES are
     deliberately NOT created by this migration... No R1 route or service
     touches either table," per that file''s own header -- so as of this
     writing no row can exist in either one under any real database).
     Proof, read directly from PS-OPPSLATE-004''s own takeover of
     usp_PurgeExpiredOpportunityWorkingData: "opportunity_member_takes and
     opportunity_requirement_review_events both hang off
     opportunity_requirement_statements, so both have to go before it
     does" and "opportunity_source_identities hangs off
     opportunity_source_versions, so it has to go before the version
     delete below" -- followed by actual DELETE...JOIN...@ExpiredSessions
     statements against all three, at the same purge call every OS-1/OS-2
     table above already goes through. A table cascade-deleted by the same
     procedure that purges expired working-session infrastructure IS
     working-session infrastructure, regardless of which migration file
     created it or what that file is named. The replacement architecture
     has not yet shipped its own durable save mechanism at all (R1''s own
     delegation brief: "Build NOTHING beyond R1: ... no requirement
     review, no alignment, no save/history"), so today there is exactly
     one durable Opportunity Slate save path in this schema: OS-4.

   THEREFORE this migration builds four readers, one per PS-OPPSLATE-003
   table, and none over any PS-OPPSLATE-001/002/004 table. Every table this
   migration does NOT read is recorded in
   services/account_export_domain_readers.py as its own excluded entry with
   this exact reasoning, matching this program''s standing precedent for a
   deliberate whole-table omission (PS-SETTINGS-EXPORT-005''s
   knowledge_item_save_requests, PS-SETTINGS-EXPORT-004''s
   target_entity_id/dbo.slate_entities, PS-SETTINGS-EXPORT-003''s
   career_skill_links) -- never silently folded into "opportunity_slate" or
   omitted.

   PS-OPPSLATE-USE-001 (SQL FIles/Migrations/, not proposed/ -- outside
   this package''s declared PS-OPPSLATE-001..004 reading baseline, and
   therefore not a dependency) was also re-read for safety: it adds one
   index and one new procedure (usp_GetOpportunitySlateUseForOwner) over
   dbo.opportunity_saved_evidence and holds no ALTER TABLE of any kind. It
   changes no column this migration reads and requires no guard here.

   HARD EXCLUSIONS PER THE OWNER''S 2026-08-29 DIRECTIVE, SUPERSEDING C0.
   C0''s V1 domain matrix (docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
   C0_ACCOUNT_EXPORT_ARCHITECTURE.md) marked this row "Included with
   provenance: Durable member records plus provenance and
   proposed/noncanonical status where applicable." The owner''s later
   2026-08-29 directive TRIMS that: AI/model provenance is now excluded
   pending separate review. Where C0 said "with provenance," the directive
   controls and this migration ships WITHOUT provenance. Four categories are
   HARD-EXCLUDED, canaried by the paired verification script, from every
   table below:
     (a) THIRD-PARTY POSTING/JOB TEXT -- any column carrying source-document
         content authored by someone other than the member. Found on
         opportunity_saved_results.source_text ("the confirmed employer
         wording as the member accepted it, copied verbatim," per
         PS-OPPSLATE-003''s own header) and on
         opportunity_saved_qualifications.employer_text ("the employer''s
         own wording for this statement"), and on
         opportunity_saved_evidence.covered_text ("a verbatim span of the
         EMPLOYER''s clause," per PS-OPPSLATE-002''s identical column on
         opportunity_analysis_citations).
     (b) EVIDENCE LINKS -- evidence_item_id and any evidence linkage,
         excluded even where the referenced evidence is the member''s own
         Workshop record (PS-OPPSLATE-003''s own header: "evidence_key and
         evidence_version identify the member''s own Workshop record").
         Found on opportunity_saved_evidence.evidence_kind/evidence_key/
         evidence_version/evidence_title/excerpt in full, and on
         opportunity_saved_qualifications.connected_evidence_title/
         connected_evidence_version.
     (c) RESPONSES -- the member''s own response context to a qualification
         prompt, hard-excluded as its own directive category regardless of
         authorship, pending the same separate review. Found on
         opportunity_saved_qualifications.response_kind/response_text/
         authored_via/connected_evidence_title/connected_evidence_version
         (the last two doubly excluded, also matching category (b)).
     (d) EVERY AI/MODEL PROVENANCE FIELD -- model names/ids, prompts,
         scores, confidence values, generation metadata. Found on
         opportunity_saved_results.model_name/prompt_contract_version.
   Plus the standard set every reader in this program already applies:
   every internal integer id, every actor/owner user id, row_version, and
   any soft-delete predicate (none of these four tables has a
   deleted_at_utc column of any kind; they are hard-deleted only by
   usp_DeleteOpportunitySavedSlateForOwner, a member''s own explicit
   action, never soft-flagged).

   NOT EVERY BORDERLINE COLUMN WAS EXCLUDED. Two judgment calls are
   recorded in full in CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md and
   summarized here because they touch this migration''s own output shape:
     - opportunity_saved_results.evidence_considered_count and
       .qualification_count are INCLUDED. Both are plain counts, not a
       name/id/prompt/score/confidence value, and the schema''s own comment
       on evidence_considered_count states it directly: "A count of the
       member''s own inputs, not a measure of them." (In context the
       antecedent is the member''s inputs; PS-OPPSLATE-002 separately
       states derived_status "is not the model''s opinion. It is COMPUTED
       by the application.") Excluding a
       count of the member''s own things because an AI process happened to
       run alongside it would over-read the directive''s named categories.
     - opportunity_saved_qualifications.derived_status and .citation_count
       are INCLUDED. PS-OPPSLATE-002''s own header is explicit that
       derived_status "is COMPUTED by the application from the citations...
       and the member-confirmed AND/OR structure... There is deliberately
       no column anywhere in this file that a sentence about the member
       could be written into" -- i.e. by the schema author''s own design
       intent, this is application accounting, not a model opinion.
       citation_count is included alongside it because
       CK_opportunity_saved_qualifications_citation_pair ties the two
       together (citation_count = 0 iff derived_status =
       ''not_enough_information''); excluding one half of a CHECK-enforced
       pair while keeping the other would be an arbitrary split.
   opportunity_saved_results.input_fingerprint is also INCLUDED: a
   one-way SHA-256 digest the member''s own currency check depends on
   (equal means "Current," different means "Reanalysis required") -- not
   a name, id, prompt, score, or evidence reference, and it cannot be
   reversed to reveal excluded content.
   opportunity_saved_results.saved_analysis_key is EXCLUDED
   (AI_MODEL_PROVENANCE) -- a reversal recorded by the independent
   review round, which corrected this package''s original keep: it IS an
   id (a uniqueidentifier naming which generation run produced the save,
   squarely inside the directive category''s "Model names/ids"
   definition), and its member-readable export value is nil because the
   run it names is ephemeral and already purged.
   opportunity_saved_results.idempotency_key is EXCLUDED (not by any of
   the four hard-exclusion categories, which do not name it, but by
   extending this program''s own established machinery-not-content
   precedent to a column rather than a whole table): it is a client-
   supplied nvarchar(200) replay/dedupe token the migration''s own header
   calls "the idempotency ledger," never member-authored content, never
   read back by any member-facing surface -- the same class of decision
   already applied whole-table to knowledge_item_save_requests,
   recruiter_question_save_requests, and moment_save_requests.

   A HALF-GUTTED TABLE, DISCLOSED RATHER THAN QUIETLY DROPPED.
   dbo.opportunity_saved_evidence loses every column that carries meaning
   to categories (a) and (b) above -- covered_text, evidence_kind,
   evidence_key, evidence_version, evidence_title, excerpt are ALL
   excluded, leaving only ordinal and clause_ordinal (structural position
   facts, not content) plus the parent linkage. This migration still
   builds its reader, per the writer brief''s explicit instruction ("When a
   table is half member-fact half third-party..., include ONLY the
   member-fact columns and record each excluded column with its directive
   category") rather than silently reclassifying the whole domain as
   excluded because most of one table''s payload happens to be barred
   today. The resulting reader is honestly near-content-free until a
   future, separately reviewed package revisits evidence-linkage policy;
   recorded as a limitation, not hidden.

   Every procedure, identical in shape and discipline to every prior
   package in this program (most recently
   PS-SETTINGS-EXPORT-005_workshop_reader.sql):
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, no table name,
       no dynamic SQL built from any argument;
     - resolves identity internally, BYTE-IDENTICALLY across all four,
       exactly like every prior package''s readers: @UserKey -> an ACTIVE
       dbo.app_users row -> its ACTIVE dbo.member_profiles row. An
       unresolved identity RETURNs before any SELECT (no result set at
       all) -- the caller-side adapter treats that as zero rows, never an
       error;
     - filters every row by the resolved owner profile on EVERY joined
       table, never only the leaf: all four of opportunity_slates,
       opportunity_saved_results, opportunity_saved_qualifications, and
       opportunity_saved_evidence independently carry their OWN
       owner_profile_id column (confirmed by reading PS-OPPSLATE-003''s own
       DDL, not assumed), so every reader below asserts
       owner_profile_id = @ProfileId on every table it touches -- the
       "owner predicate on both/every side" defense in depth
       PS-SETTINGS-EXPORT-004 introduced for dbo.moment_sources/
       dbo.moment_placements and PS-SETTINGS-EXPORT-005 applied to
       dbo.knowledge_item_versions, extended here across a four-level
       chain (slate -> saved_result -> saved_qualification -> saved_evidence);
     - also asserts the top-level slate.visibility = N''private'' explicitly
       on every reader, including the three descendant readers (joined all
       the way up to opportunity_slates for exactly this predicate) --
       the identical "never trust the default" discipline
       PS-SETTINGS-EXPORT-005 applied to dbo.knowledge_items even though
       CK_opportunity_slates_visibility hard-locks the column today;
     - replaces every internal integer id with the row''s own opaque
       *_key uniqueidentifier where the table has one
       (opportunity_slates.slate_key, opportunity_saved_results.
       saved_result_key), plus the nearest ancestor''s opaque key for
       intra-export linkage where the table has none of its own.
       opportunity_saved_qualifications and opportunity_saved_evidence
       have NO opaque key column of their own (unlike every ancestor) --
       their identifying tuples are (saved_result_key, ordinal) and
       (saved_result_key, saved_qualification_ordinal, ordinal)
       respectively, both already unique per
       UQ_opportunity_saved_qualifications_ordinal and
       UQ_opportunity_saved_evidence_ordinal, so no surrogate key is
       manufactured for a column the schema does not have -- the identical
       treatment PS-SETTINGS-EXPORT-005 gave dbo.knowledge_item_versions;
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *), matching this package''s directive-trimmed allowlist
       exactly;
     - orders its result set deterministically, parent-then-sequence at
       every level: opportunity_slates orders by its own created_at_utc
       then its own opaque key (the "own timestamp, own key" idiom every
       top-level reader in this program uses); each descendant orders by
       every ancestor''s own ordering key first, then its own sequence
       column (save_version_number, then ordinal, then ordinal again) --
       required because save_version_number/ordinal are only unique WITHIN
       one parent, the identical reasoning PS-SETTINGS-EXPORT-004/005
       already applied to their own version-history tables;
     - returns a read window (SYSUTCDATETIME() captured at the top of the
       procedure as @ReadStartedAtUtc, and again inline in the content
       SELECT as read_ended_at_utc) as two TRAILING COLUMNS on the single
       content result set -- identical mechanism and rationale to every
       prior package;
     - contains NO transaction control of any kind -- no BEGIN
       TRANSACTION, COMMIT, ROLLBACK, or TRY/CATCH, and no nested EXEC or
       dynamic SQL of its own. Every procedure here is a single read-only
       SELECT, safe to call with a bare EXEC.

   Requires PS-OPPSLATE-001, PS-OPPSLATE-002, and PS-OPPSLATE-003 -- the
   FULL direct chain, not merely PS-OPPSLATE-003 (whose own tables are the
   only ones this migration reads). This follows the in-family precedent
   PS-OPPSLATE-003 and PS-OPPSLATE-004 both already set: PS-OPPSLATE-003''s
   own guard checks for BOTH PS-OPPSLATE-001 AND PS-OPPSLATE-002 by ledger
   row explicitly (never relying on transitivity alone), and
   PS-OPPSLATE-004''s own `requires` names all three ancestors directly.
   None of the four tables this migration reads carries a foreign key into
   any OS-1/OS-2 table, so this is a disclosed, conservative,
   family-consistent choice, not a discovered technical necessity -- the
   identical class of choice PS-SETTINGS-EXPORT-005''s own header recorded
   for including PS-WORKSHOP-002 in its own requires. PS-AUTH-001 is named
   in the registry''s own requires list too, for the paired verification
   script''s usp_UpsertAppUserFromAuth dependency -- named here from the
   start, matching every package since PS-SETTINGS-EXPORT-003''s own gate
   round had to correct the identical omission after the fact. This
   migration''s own guards do not check for PS-AUTH-001 directly: every
   column they touch on dbo.app_users/dbo.member_profiles already exists as
   of PS-PLAT-000/PS-PLAT-002, predating PS-AUTH-001, identically to every
   prior package''s recorded reasoning for the same omission.

   Grant model: identical to every prior package in this program. The
   governed apply identity holds db_ddladmin only and cannot GRANT EXECUTE;
   no GRANT, CREATE ROLE, CREATE USER, or sp_addrolemember statement
   appears anywhere in this file. The intended production grant -- EXECUTE
   on these four procedures for the existing web-app principal role -- is a
   separate, later, administrator-run authority operation, not created here
   and not authorized by a repository merge of this file.

   THROW range: 58600-58699 (this migration; the rollback file continues
   within the same block at 58611). Verified clear of every sibling
   migration/rollback/verification file''s range: the highest prior THROW
   number anywhere under SQL FIles/ is 58553
   (PS-SETTINGS-EXPORT-005_workshop_reader_isolation_verify.sql).

   No production apply is authorized by this file. No container, worker,
   schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-006_oppslate_reader_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58600, 'PS-SETTINGS-EXPORT-006 requires the migration ledger.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-OPPSLATE-001')
        THROW 58601, 'PS-OPPSLATE-001 must be applied before PS-SETTINGS-EXPORT-006.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-OPPSLATE-002')
        THROW 58602, 'PS-OPPSLATE-002 must be applied before PS-SETTINGS-EXPORT-006.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-OPPSLATE-003')
        THROW 58603, 'PS-OPPSLATE-003 must be applied before PS-SETTINGS-EXPORT-006.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 58604, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 58605, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.opportunity_slates', N'U') IS NULL
       OR OBJECT_ID(N'dbo.opportunity_saved_results', N'U') IS NULL
       OR OBJECT_ID(N'dbo.opportunity_saved_qualifications', N'U') IS NULL
       OR OBJECT_ID(N'dbo.opportunity_saved_evidence', N'U') IS NULL
        THROW 58606, 'The Opportunity Slate durable saved-slate schema is missing.', 1;

    IF COL_LENGTH(N'dbo.opportunity_slates', N'slate_key') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_slates', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_slates', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_slates', N'current_save_version_number') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_slates', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_slates', N'updated_at_utc') IS NULL
        THROW 58607, 'The opportunity_slates columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.opportunity_saved_results', N'opportunity_slate_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'saved_result_key') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'save_version_number') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'source_version_number') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'requirement_version_number') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'saved_analysis_key') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'evidence_considered_count') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'qualification_count') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'input_fingerprint') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_results', N'saved_at_utc') IS NULL
        THROW 58608, 'The opportunity_saved_results columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.opportunity_saved_qualifications', N'opportunity_saved_result_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_qualifications', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_qualifications', N'ordinal') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_qualifications', N'statement_class') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_qualifications', N'derived_status') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_qualifications', N'citation_count') IS NULL
        THROW 58609, 'The opportunity_saved_qualifications columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.opportunity_saved_evidence', N'opportunity_saved_qualification_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_evidence', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_evidence', N'ordinal') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_saved_evidence', N'clause_ordinal') IS NULL
        THROW 58610, 'The opportunity_saved_evidence columns are incompatible.', 1;

    /* ============================================================
       READER 1: dbo.opportunity_slates (5 content columns; no parent)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportOpportunitySlateForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                slate.slate_key,
                slate.visibility,
                slate.current_save_version_number,
                slate.created_at_utc,
                slate.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.opportunity_slates AS slate
            WHERE slate.owner_profile_id = @ProfileId
              AND slate.visibility = N''private''
            ORDER BY slate.created_at_utc, slate.slate_key;
        END;
    ');

    /* ============================================================
       READER 2: dbo.opportunity_saved_results (8 content columns, plus
       the joined parent''s slate_key for linkage; owner predicate on
       both tables; third-party posting text (source_text) and AI
       provenance (saved_analysis_key, model_name,
       prompt_contract_version) hard-excluded; idempotency_key excluded
       as replay machinery.)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportOpportunitySavedResultForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                slate.slate_key,
                saved_result.saved_result_key,
                saved_result.save_version_number,
                saved_result.source_version_number,
                saved_result.requirement_version_number,
                saved_result.evidence_considered_count,
                saved_result.qualification_count,
                saved_result.input_fingerprint,
                saved_result.saved_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.opportunity_saved_results AS saved_result
            JOIN dbo.opportunity_slates AS slate
              ON slate.opportunity_slate_id = saved_result.opportunity_slate_id
            WHERE saved_result.owner_profile_id = @ProfileId
              AND slate.owner_profile_id = @ProfileId
              AND slate.visibility = N''private''
            ORDER BY slate.created_at_utc, slate.slate_key, saved_result.save_version_number;
        END;
    ');

    /* ============================================================
       READER 3: dbo.opportunity_saved_qualifications (4 content columns,
       plus the joined grandparent saved_result_key for linkage; owner
       predicate on all three tables; third-party posting text
       (employer_text) and every response/evidence-link column
       hard-excluded.)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                saved_result.saved_result_key,
                qualification.ordinal,
                qualification.statement_class,
                qualification.derived_status,
                qualification.citation_count,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.opportunity_saved_qualifications AS qualification
            JOIN dbo.opportunity_saved_results AS saved_result
              ON saved_result.opportunity_saved_result_id = qualification.opportunity_saved_result_id
            JOIN dbo.opportunity_slates AS slate
              ON slate.opportunity_slate_id = saved_result.opportunity_slate_id
            WHERE qualification.owner_profile_id = @ProfileId
              AND saved_result.owner_profile_id = @ProfileId
              AND slate.owner_profile_id = @ProfileId
              AND slate.visibility = N''private''
            ORDER BY slate.created_at_utc, slate.slate_key, saved_result.save_version_number, qualification.ordinal;
        END;
    ');

    /* ============================================================
       READER 4: dbo.opportunity_saved_evidence -- 2 content columns
       (ordinal, clause_ordinal) plus the joined ancestors'' linkage;
       owner predicate on all four tables. Every other column on this
       table is either third-party posting text (covered_text) or
       evidence linkage (evidence_kind/evidence_key/evidence_version/
       evidence_title/excerpt) and is hard-excluded; see this file''s own
       header for why a reader is still built rather than the domain
       reclassified as excluded.
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                saved_result.saved_result_key,
                qualification.ordinal AS saved_qualification_ordinal,
                evidence.ordinal,
                evidence.clause_ordinal,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.opportunity_saved_evidence AS evidence
            JOIN dbo.opportunity_saved_qualifications AS qualification
              ON qualification.opportunity_saved_qualification_id = evidence.opportunity_saved_qualification_id
            JOIN dbo.opportunity_saved_results AS saved_result
              ON saved_result.opportunity_saved_result_id = qualification.opportunity_saved_result_id
            JOIN dbo.opportunity_slates AS slate
              ON slate.opportunity_slate_id = saved_result.opportunity_slate_id
            WHERE evidence.owner_profile_id = @ProfileId
              AND qualification.owner_profile_id = @ProfileId
              AND saved_result.owner_profile_id = @ProfileId
              AND slate.owner_profile_id = @ProfileId
              AND slate.visibility = N''private''
            ORDER BY slate.created_at_utc, slate.slate_key, saved_result.save_version_number, qualification.ordinal, evidence.ordinal;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-006'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-006',
            N'Read-only owner-scoped account-export Opportunity Slate readers (replacement package 4, FINAL reader): four @UserKey-only procedures over the durable saved slate only (opportunity_slates/saved_results/saved_qualifications/saved_evidence). Directive-trimmed: excludes third-party posting text, evidence links, responses, and AI/model provenance. Every OS-1/OS-2/OS-3 working table and all three PS-OPPSLATE-004 tables are ephemeral, excluded.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-006"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
