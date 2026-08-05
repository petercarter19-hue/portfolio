/* ============================================================
   PS-OPPSLATE-003 - Opportunity Slate OS-4 additive schema

   Immutable follow-on to the production-ledgered PS-OPPSLATE-001 (OS-1/OS-2)
   and PS-OPPSLATE-002 (OS-3) baseline. Adds the durable saved slate - the
   first thing in this store that outlives a member's ephemeral working
   session - and the currency fingerprint that keeps "saved" and "still
   accurate" two separate truths (locked rule; handoff section 7):

     dbo.opportunity_slates                one per member, created by the
                                           first save and by nothing else
     dbo.opportunity_saved_results         append-only saved versions, each
                                           with its input_fingerprint and
                                           its (owner, idempotency_key)
     dbo.opportunity_saved_qualifications  the per-qualification snapshot,
                                           including the member's response
     dbo.opportunity_saved_evidence        evidence references pinned to
                                           item + version with excerpts

   and three new owner-scoped procedures:
     usp_GetOpportunitySavedSlateForOwner
     usp_SaveOpportunitySlateForOwner
     usp_DeleteOpportunitySavedSlateForOwner

   THIS IS A RE-CUT, NOT A NEW DESIGN. A prior branch
   (work/2026-08-04-opportunity-slate-os4, checkpoint de8735ce) implemented
   this exact OS-4 delta by extending PS-OPPSLATE-001 in place - the same
   defect PS-OPPSLATE-002 already corrected once for OS-3. Production's
   ledger makes PS-OPPSLATE-001 and PS-OPPSLATE-002 immutable: an applied
   migration's bytes may never change. This file carries the identical OS-4
   schema delta - every table, column, index, constraint and procedure body
   below is lifted unchanged from that checkpoint - re-cut as its own
   additive migration on top of the applied baseline, exactly like the OS-3
   delta became PS-OPPSLATE-002 rather than an edit to PS-OPPSLATE-001.

   NO EXISTING PROCEDURE CHANGES. Not one, and not by omission: the
   checkpoint's own header records this as a deliberate design outcome
   rather than an oversight. A saved result COPIES what it shows instead of
   pinning the ephemeral rows it was computed from, so the purge and the
   member's working-session delete need no conditional retention logic and
   their bodies are untouched by this migration. usp_DeleteOpportunitySaved-
   SlateForOwner removes only the saved slate the member explicitly deletes
   and touches no working data; deleting the working session likewise never
   removes a saved slate, because the two lifetimes are separate by
   construction. This migration is therefore purely additive: four new
   tables and three new procedures, with no ALTER of any table PS-OPPSLATE-
   001 or PS-OPPSLATE-002 created.

   STILL NO SCORE. Not one column below holds an aggregate, a percentage, a
   ranking, a recommendation or an employer prediction, and none may ever be
   added. opportunity_saved_qualifications.derived_status is the same
   per-statement accounting OS-3 stores (handoff section 1 and section 8),
   copied unchanged.

   A missing or partial PS-OPPSLATE-001/PS-OPPSLATE-002 baseline fails before
   the first mutation. It never updates or reuses the PS-OPPSLATE-001 or
   PS-OPPSLATE-002 ledger rows, and inserts only its own.

   Rollback: PS-OPPSLATE-003_opportunity_slate_os4_rollback.sql
   Verification: ../../Verification/PS-OPPSLATE-003_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53720, 'PS-OPPSLATE-003 requires the migration ledger.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-OPPSLATE-001')
        THROW 53721, 'PS-OPPSLATE-001 must be applied before PS-OPPSLATE-003.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-OPPSLATE-002')
        THROW 53722, 'PS-OPPSLATE-002 must be applied before PS-OPPSLATE-003.', 1;

    DECLARE @RequiredBaselineObjects TABLE
        (object_name nvarchar(300) NOT NULL, object_type char(1) NOT NULL);
    INSERT @RequiredBaselineObjects (object_name, object_type)
    VALUES
        (N'dbo.opportunity_working_sessions', N'U'),
        (N'dbo.opportunity_sources', N'U'),
        (N'dbo.opportunity_source_versions', N'U'),
        (N'dbo.opportunity_source_reviews', N'U'),
        (N'dbo.opportunity_source_concerns', N'U'),
        (N'dbo.opportunity_requirement_sets', N'U'),
        (N'dbo.opportunity_requirement_set_versions', N'U'),
        (N'dbo.opportunity_requirement_statements', N'U'),
        (N'dbo.opportunity_analyses', N'U'),
        (N'dbo.opportunity_analysis_statements', N'U'),
        (N'dbo.opportunity_analysis_citations', N'U'),
        (N'dbo.opportunity_responses', N'U'),
        (N'dbo.usp_PurgeExpiredOpportunityWorkingData', N'P'),
        (N'dbo.usp_GetOpportunityWorkingSessionForOwner', N'P'),
        (N'dbo.usp_SaveOpportunitySourceForOwner', N'P'),
        (N'dbo.usp_CorrectOpportunitySourceForOwner', N'P'),
        (N'dbo.usp_ConfirmOpportunitySourceForOwner', N'P'),
        (N'dbo.usp_DeleteOpportunityWorkingSessionForOwner', N'P'),
        (N'dbo.usp_GetOpportunitySourceReviewForOwner', N'P'),
        (N'dbo.usp_SaveOpportunitySourceReviewForOwner', N'P'),
        (N'dbo.usp_ResolveOpportunitySourceConcernForOwner', N'P'),
        (N'dbo.usp_GetOpportunityRequirementsForOwner', N'P'),
        (N'dbo.usp_SaveOpportunityRequirementProposalForOwner', N'P'),
        (N'dbo.usp_CorrectOpportunityRequirementStatementForOwner', N'P'),
        (N'dbo.usp_ConfirmOpportunityRequirementsForOwner', N'P'),
        (N'dbo.usp_ListOpportunityEvidenceForOwner', N'P'),
        (N'dbo.usp_GetOpportunityAnalysisForOwner', N'P'),
        (N'dbo.usp_SaveOpportunityAnalysisForOwner', N'P'),
        (N'dbo.usp_SaveOpportunityResponseForOwner', N'P');
    IF EXISTS (SELECT 1 FROM @RequiredBaselineObjects
               WHERE OBJECT_ID(object_name, object_type) IS NULL)
        THROW 53723, 'PS-OPPSLATE-001/PS-OPPSLATE-002 does not match the required OS-3 object baseline.', 1;

    DECLARE @Os4Objects TABLE
        (object_name nvarchar(300) NOT NULL, object_type char(1) NOT NULL);
    INSERT @Os4Objects (object_name, object_type)
    VALUES
        (N'dbo.opportunity_slates', N'U'),
        (N'dbo.opportunity_saved_results', N'U'),
        (N'dbo.opportunity_saved_qualifications', N'U'),
        (N'dbo.opportunity_saved_evidence', N'U'),
        (N'dbo.usp_GetOpportunitySavedSlateForOwner', N'P'),
        (N'dbo.usp_SaveOpportunitySlateForOwner', N'P'),
        (N'dbo.usp_DeleteOpportunitySavedSlateForOwner', N'P');
    DECLARE @ExistingOs4ObjectCount int =
        (SELECT COUNT(*) FROM @Os4Objects WHERE OBJECT_ID(object_name, object_type) IS NOT NULL);
    IF @ExistingOs4ObjectCount NOT IN (0, 7)
        THROW 53724, 'A partial OS-4 schema exists without a complete additive migration.', 1;

    /* ------------------------------------------------------------
       SLICE OS-4 — the durable saved slate.

       EVERYTHING ABOVE THIS LINE IS EPHEMERAL. The working session, its
       source, its readings, its analysis and the member''s responses all
       expire, and the member is told so on every screen. This is the first
       table group in this file that survives expiry, survives the member
       deleting their working session, and survives the source being
       replaced — because the member explicitly asked for it to.

       IT IS A COPY, NOT A REFERENCE, AND THAT IS THE WHOLE DESIGN. Handoff
       section 8 proposed retaining the pre-save version rows "pinned by a
       saved result" when the working data is purged. That entangles two
       lifetimes: every purge and every delete would have to know which rows
       a saved result still needs, and the day one of them forgets is the day
       a member opens a saved slate and finds the employer wording gone. A
       saved result here instead OWNS its own immutable copy of everything it
       shows — the confirmed source wording, each qualification''s employer
       text and derived status, each citation with its pinned evidence
       key/version/title/excerpt, and the member''s own response context. The
       working tables can then be purged with no conditional logic at all,
       which is why NO EXISTING PROCEDURE IN THIS FILE CHANGES IN THIS
       REVISION. Documented as a section 14-M13-class adaptation: same
       contract (an immutable snapshot pinned to exact versions), one fewer
       coupling.

       WHAT IS STILL A REFERENCE. evidence_key and evidence_version identify
       the member''s own Workshop record; the excerpt is a bounded verbatim
       span retained only so the member can see WHAT the analysis read. This
       room writes no Workshop row, here or anywhere else.

       AND STILL NO SCORE. Not one column below holds an aggregate, a
       percentage, a ranking, a recommendation or an employer prediction, and
       none may ever be added. opportunity_saved_qualifications.derived_status
       is the same per-statement accounting OS-3 stores, copied unchanged.

       CURRENCY IS A SEPARATE TRUTH FROM SAVEDNESS (locked rule; handoff
       section 7). input_fingerprint below is what makes that mechanical: it
       is a digest over the inputs this result was computed from — the pinned
       source version, the pinned requirement-set version, and every cited
       evidence record at the version it was cited at. The application
       recomputes the same digest from the CURRENT inputs and the CURRENT
       version of each of those evidence records; equal means "Current for
       these inputs", different means "Inputs changed - Reanalysis required".
       Nothing is ever silently reanalyzed and nothing is ever overwritten:
       saving again appends a new save_version_number.
       ------------------------------------------------------------ */

    IF OBJECT_ID(N'dbo.opportunity_slates', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_slates
        (
            opportunity_slate_id bigint IDENTITY(1,1) NOT NULL,
            slate_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_slates_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            /* There is no audience model on this surface, by design (handoff
               section 8). Hard-locked by CHECK exactly like
               knowledge_items.visibility, not by a default that could
               silently change. */
            visibility nvarchar(20) NOT NULL
                CONSTRAINT DF_opportunity_slates_visibility DEFAULT N'private',
            current_save_version_number int NOT NULL
                CONSTRAINT DF_opportunity_slates_current DEFAULT 0,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_slates_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_slates_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_slates PRIMARY KEY (opportunity_slate_id),
            CONSTRAINT UQ_opportunity_slates_key UNIQUE (slate_key),
            /* One active slate per member (owner decision, handoff section
               17-Q2), enforced in the schema rather than trusted to the
               application. */
            CONSTRAINT UQ_opportunity_slates_owner UNIQUE (owner_profile_id),
            /* The composite candidate key every child below references.
               Declared UP FRONT: the 2026-08-03 gate lost a whole migration
               on its first statement because opportunity_source_versions did
               not have one. */
            CONSTRAINT UQ_opportunity_slates_id_owner
                UNIQUE (opportunity_slate_id, owner_profile_id),
            CONSTRAINT FK_opportunity_slates_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_opportunity_slates_visibility CHECK (visibility = N'private'),
            CONSTRAINT CK_opportunity_slates_current CHECK (current_save_version_number >= 0)
        );
    END;

    IF OBJECT_ID(N'dbo.opportunity_saved_results', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_saved_results
        (
            opportunity_saved_result_id bigint IDENTITY(1,1) NOT NULL,
            saved_result_key uniqueidentifier NOT NULL
                CONSTRAINT DF_opportunity_saved_results_key DEFAULT NEWSEQUENTIALID(),
            opportunity_slate_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            /* Append-only. Saving again writes save_version_number + 1;
               nothing is ever overwritten and every earlier version stays
               identifiable by its source version and its save time (locked
               rule; handoff section 7). */
            save_version_number int NOT NULL,
            source_version_number int NOT NULL,
            requirement_version_number int NOT NULL,
            /* Which analysis RUN was saved. A value, not a foreign key: the
               analysis it names is ephemeral and this row must outlive it.
               The application compares it with the current run''s key to tell
               "the result on screen is the saved one" from "a newer, unsaved
               result is on screen". */
            saved_analysis_key uniqueidentifier NOT NULL,
            /* The confirmed employer wording as the member accepted it,
               copied verbatim. This is what makes the snapshot readable after
               the working session is gone. */
            source_text nvarchar(max) NOT NULL,
            model_name nvarchar(200) NOT NULL,
            prompt_contract_version nvarchar(100) NOT NULL,
            evidence_considered_count int NOT NULL,
            qualification_count int NOT NULL,
            /* SHA-256 hex of the canonical input digest (see the block
               above). char(64) because the application always writes 64 hex
               characters and a shorter value means the caller is wrong. */
            input_fingerprint char(64) NOT NULL,
            /* The idempotency ledger, keyed exactly as handoff section 8
               specifies — (owner_profile_id, idempotency_key) — and carried
               on the row it protects rather than in a separate
               opportunity_save_requests table. A separate ledger can outlive
               or point past the row it describes; this one cannot. Same key,
               same guarantee, one fewer thing to drift. */
            idempotency_key nvarchar(200) NOT NULL,
            saved_by_user_id int NOT NULL,
            saved_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_saved_results_saved DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_saved_results PRIMARY KEY (opportunity_saved_result_id),
            CONSTRAINT UQ_opportunity_saved_results_key UNIQUE (saved_result_key),
            CONSTRAINT UQ_opportunity_saved_results_version
                UNIQUE (opportunity_slate_id, save_version_number),
            CONSTRAINT UQ_opportunity_saved_results_idempotency
                UNIQUE (owner_profile_id, idempotency_key),
            CONSTRAINT UQ_opportunity_saved_results_id_owner
                UNIQUE (opportunity_saved_result_id, owner_profile_id),
            CONSTRAINT FK_opportunity_saved_results_slate FOREIGN KEY (opportunity_slate_id, owner_profile_id)
                REFERENCES dbo.opportunity_slates(opportunity_slate_id, owner_profile_id),
            CONSTRAINT FK_opportunity_saved_results_author FOREIGN KEY (saved_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_saved_results_save_version CHECK (save_version_number > 0),
            CONSTRAINT CK_opportunity_saved_results_source_version CHECK (source_version_number > 0),
            CONSTRAINT CK_opportunity_saved_results_requirement_version CHECK (requirement_version_number > 0),
            CONSTRAINT CK_opportunity_saved_results_source_length CHECK
                (DATALENGTH(source_text) / 2 BETWEEN 1 AND 20000),
            CONSTRAINT CK_opportunity_saved_results_model_length CHECK
                (DATALENGTH(model_name) / 2 BETWEEN 1 AND 100),
            CONSTRAINT CK_opportunity_saved_results_contract_length CHECK
                (DATALENGTH(prompt_contract_version) / 2 BETWEEN 1 AND 60),
            CONSTRAINT CK_opportunity_saved_results_evidence_count CHECK
                (evidence_considered_count BETWEEN 0 AND 24),
            CONSTRAINT CK_opportunity_saved_results_qualification_count CHECK
                (qualification_count BETWEEN 1 AND 40),
            CONSTRAINT CK_opportunity_saved_results_fingerprint CHECK
                (input_fingerprint NOT LIKE N'%[^0-9a-f]%'),
            CONSTRAINT CK_opportunity_saved_results_idempotency_length CHECK
                (DATALENGTH(idempotency_key) / 2 BETWEEN 1 AND 200)
        );

        CREATE INDEX IX_opportunity_saved_results_owner
            ON dbo.opportunity_saved_results(owner_profile_id, opportunity_slate_id, save_version_number DESC)
            INCLUDE (saved_result_key, saved_at_utc, source_version_number);
    END;

    IF OBJECT_ID(N'dbo.opportunity_saved_qualifications', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_saved_qualifications
        (
            opportunity_saved_qualification_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_saved_result_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            ordinal int NOT NULL,
            statement_class nvarchar(40) NOT NULL,
            employer_text nvarchar(2000) NOT NULL,
            /* Copied from opportunity_analysis_statements.derived_status,
               which the APPLICATION derived from the citations. Not a score,
               not a model opinion, and not an aggregate — the same three
               named states image 04 draws, per statement. */
            derived_status nvarchar(30) NOT NULL,
            citation_count int NOT NULL,
            /* The member''s response context (handoff section 7: the saved
               result retains "the member''s response context"). Nullable
               because most qualifications have no response, and shaped by the
               same CHECK the live table uses so a saved response can never
               look like an answer the member did not give. */
            response_kind nvarchar(30) NULL,
            response_text nvarchar(max) NULL,
            authored_via nvarchar(30) NULL,
            connected_evidence_title nvarchar(200) NULL,
            connected_evidence_version int NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_saved_qualifications PRIMARY KEY (opportunity_saved_qualification_id),
            CONSTRAINT UQ_opportunity_saved_qualifications_ordinal
                UNIQUE (opportunity_saved_result_id, ordinal),
            CONSTRAINT UQ_opportunity_saved_qualifications_id_owner
                UNIQUE (opportunity_saved_qualification_id, owner_profile_id),
            CONSTRAINT FK_opportunity_saved_qualifications_result FOREIGN KEY (opportunity_saved_result_id, owner_profile_id)
                REFERENCES dbo.opportunity_saved_results(opportunity_saved_result_id, owner_profile_id),
            CONSTRAINT CK_opportunity_saved_qualifications_ordinal CHECK (ordinal > 0),
            /* THE FULL FOUR-CLASS ENUM, and the 2026-08-04 gate is why.
               This started as the narrow pair, on the reasoning that only a
               qualification is ever analysed. The gate refused a legitimate
               save with a raw CHECK violation: usp_SaveOpportunityAnalysis-
               ForOwner records a result for whatever statement the caller
               names, and a member who reclassifies a statement BEFORE the
               analysis runs can leave a stored result whose effective class
               is a responsibility. Narrowing here bought no safety - this
               column is a copy of the member''s own decision, not a rule the
               room enforces - and cost a save that fails with nothing the
               member could act on. The snapshot records what the analysis
               actually held. */
            CONSTRAINT CK_opportunity_saved_qualifications_class CHECK
                (statement_class IN (N'required_qualification', N'preferred_qualification',
                                     N'responsibility', N'informational_statement')),
            CONSTRAINT CK_opportunity_saved_qualifications_status CHECK
                (derived_status IN (N'supported', N'partially_supported',
                                    N'not_enough_information')),
            CONSTRAINT CK_opportunity_saved_qualifications_text_length CHECK
                (DATALENGTH(employer_text) / 2 BETWEEN 1 AND 1200),
            CONSTRAINT CK_opportunity_saved_qualifications_citation_count CHECK
                (citation_count BETWEEN 0 AND 24),
            /* The same pairing OS-3 locks on the live table: a result with no
               citation can only be "not enough information", and one with a
               citation can never be. */
            CONSTRAINT CK_opportunity_saved_qualifications_citation_pair CHECK
            (
                (citation_count = 0 AND derived_status = N'not_enough_information')
                OR
                (citation_count > 0 AND derived_status <> N'not_enough_information')
            ),
            CONSTRAINT CK_opportunity_saved_qualifications_response_kind CHECK
                (response_kind IS NULL
                 OR response_kind IN (N'tell_more', N'connect_evidence', N'real_example',
                                      N'confirm_not_have', N'skip')),
            CONSTRAINT CK_opportunity_saved_qualifications_authored_via CHECK
                (authored_via IS NULL OR authored_via IN (N'typed', N'spoken')),
            CONSTRAINT CK_opportunity_saved_qualifications_response_shape CHECK
            (
                (
                    response_kind IS NULL
                    AND response_text IS NULL
                    AND authored_via IS NULL
                    AND connected_evidence_title IS NULL
                    AND connected_evidence_version IS NULL
                )
                OR
                (
                    response_kind IN (N'tell_more', N'real_example')
                    AND response_text IS NOT NULL
                    AND authored_via IS NOT NULL
                    AND connected_evidence_title IS NULL
                    AND connected_evidence_version IS NULL
                )
                OR
                (
                    response_kind = N'connect_evidence'
                    AND response_text IS NULL
                    AND authored_via IS NOT NULL
                    AND connected_evidence_title IS NOT NULL
                    AND connected_evidence_version IS NOT NULL
                )
                OR
                (
                    response_kind IN (N'confirm_not_have', N'skip')
                    AND response_text IS NULL
                    AND authored_via IS NOT NULL
                    AND connected_evidence_title IS NULL
                    AND connected_evidence_version IS NULL
                )
            ),
            CONSTRAINT CK_opportunity_saved_qualifications_response_length CHECK
                (response_text IS NULL
                 OR DATALENGTH(response_text) / 2 BETWEEN 1 AND 4000),
            CONSTRAINT CK_opportunity_saved_qualifications_connected_title CHECK
                (connected_evidence_title IS NULL
                 OR DATALENGTH(connected_evidence_title) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_saved_qualifications_connected_version CHECK
                (connected_evidence_version IS NULL OR connected_evidence_version > 0)
        );

        CREATE INDEX IX_opportunity_saved_qualifications_result
            ON dbo.opportunity_saved_qualifications(opportunity_saved_result_id, ordinal)
            INCLUDE (statement_class, derived_status, citation_count);
    END;

    IF OBJECT_ID(N'dbo.opportunity_saved_evidence', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_saved_evidence
        (
            opportunity_saved_evidence_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_saved_qualification_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            ordinal int NOT NULL,
            clause_ordinal int NOT NULL,
            covered_text nvarchar(400) NOT NULL,
            /* The evidence REFERENCE, pinned to item + version, with the
               bounded verbatim excerpt the analysis actually read. Handoff
               section 8: evidence is referenced, never copied; the excerpt is
               the one exception and exists so the member can still identify
               what was read after they edit the item. */
            evidence_kind nvarchar(30) NOT NULL,
            evidence_key uniqueidentifier NOT NULL,
            evidence_version int NOT NULL,
            evidence_title nvarchar(200) NOT NULL,
            excerpt nvarchar(800) NOT NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_saved_evidence PRIMARY KEY (opportunity_saved_evidence_id),
            CONSTRAINT UQ_opportunity_saved_evidence_ordinal
                UNIQUE (opportunity_saved_qualification_id, ordinal),
            CONSTRAINT UQ_opportunity_saved_evidence_id_owner
                UNIQUE (opportunity_saved_evidence_id, owner_profile_id),
            CONSTRAINT FK_opportunity_saved_evidence_qualification FOREIGN KEY (opportunity_saved_qualification_id, owner_profile_id)
                REFERENCES dbo.opportunity_saved_qualifications(opportunity_saved_qualification_id, owner_profile_id),
            CONSTRAINT CK_opportunity_saved_evidence_ordinal CHECK (ordinal > 0),
            CONSTRAINT CK_opportunity_saved_evidence_clause CHECK (clause_ordinal > 0),
            CONSTRAINT CK_opportunity_saved_evidence_kind CHECK
                (evidence_kind IN (N'knowledge_item', N'moment')),
            CONSTRAINT CK_opportunity_saved_evidence_version CHECK (evidence_version > 0),
            CONSTRAINT CK_opportunity_saved_evidence_covered_length CHECK
                (DATALENGTH(covered_text) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_saved_evidence_title_length CHECK
                (DATALENGTH(evidence_title) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_saved_evidence_excerpt_length CHECK
                (DATALENGTH(excerpt) / 2 BETWEEN 1 AND 400)
        );

        CREATE INDEX IX_opportunity_saved_evidence_qualification
            ON dbo.opportunity_saved_evidence(opportunity_saved_qualification_id, ordinal)
            INCLUDE (evidence_key, evidence_version);
    END;

    /* ============================================================
       SLICE OS-4 PROCEDURES — the save lifecycle.

       Same discipline as every procedure above, plus one rule this slice
       needs more than any earlier one: THE SNAPSHOT IS BUILT SERVER-SIDE.
       usp_SaveOpportunitySlateForOwner accepts no content payload at all. It
       reads the confirmed source, the confirmed requirement set, its
       analysis, that analysis'' citations and the member''s own responses out
       of this owner''s OWN rows and copies them. A caller cannot choose what
       a saved result says about the member, which is the strongest form of
       the finding-F7 lesson: do not accept identity, and where you can, do
       not accept content either.
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunitySavedSlateForOwner
            @UserKey nvarchar(300),
            /* NULL reads the latest saved version. A key opens an earlier one
               from the versions list (handoff section 4, os-saved-details). */
            @SavedResultKey uniqueidentifier = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Five result sets: the slate, every saved version (the versions
               list), the opened version''s qualifications, their pinned
               evidence, and — the one that makes currency mechanical — each
               distinct cited evidence record with its CURRENT confirmed
               version read live from the member''s own library.

               A record the member has since archived, un-confirmed, or
               deleted resolves to NULL there. NULL is not an error: it is a
               change, and a changed input is exactly what "Inputs changed -
               Reanalysis required" describes. */
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

            DECLARE @SlateId bigint;
            SELECT @SlateId = slate.opportunity_slate_id
            FROM dbo.opportunity_slates AS slate
            WHERE slate.owner_profile_id = @ProfileId;

            IF @SlateId IS NULL RETURN;

            DECLARE @ResultId bigint;
            IF @SavedResultKey IS NULL
                SELECT TOP (1) @ResultId = saved_result.opportunity_saved_result_id
                FROM dbo.opportunity_saved_results AS saved_result
                WHERE saved_result.opportunity_slate_id = @SlateId
                  AND saved_result.owner_profile_id = @ProfileId
                ORDER BY saved_result.save_version_number DESC;
            ELSE
                SELECT @ResultId = saved_result.opportunity_saved_result_id
                FROM dbo.opportunity_saved_results AS saved_result
                WHERE saved_result.opportunity_slate_id = @SlateId
                  AND saved_result.owner_profile_id = @ProfileId
                  AND saved_result.saved_result_key = @SavedResultKey;

            /* A slate with no saved result cannot exist - the slate row is
               created inside the same transaction as its first save - but a
               requested key that is not this member''s resolves to NULL, and
               that must read as "not found" rather than silently opening
               somebody else''s idea of the latest. */
            IF @ResultId IS NULL RETURN;

            SELECT
                slate.slate_key,
                CONVERT(binary(8), slate.row_version) AS slate_row_version,
                slate.current_save_version_number,
                slate.created_at_utc AS slate_created_at_utc,
                saved_result.saved_result_key,
                saved_result.save_version_number,
                saved_result.source_version_number,
                saved_result.requirement_version_number,
                saved_result.saved_analysis_key,
                saved_result.source_text,
                saved_result.model_name,
                saved_result.prompt_contract_version,
                saved_result.evidence_considered_count,
                saved_result.qualification_count,
                saved_result.input_fingerprint,
                saved_result.saved_at_utc
            FROM dbo.opportunity_slates AS slate
            JOIN dbo.opportunity_saved_results AS saved_result
              ON saved_result.opportunity_slate_id = slate.opportunity_slate_id
             AND saved_result.owner_profile_id = slate.owner_profile_id
            WHERE slate.opportunity_slate_id = @SlateId
              AND slate.owner_profile_id = @ProfileId
              AND saved_result.opportunity_saved_result_id = @ResultId;

            SELECT
                saved_result.saved_result_key,
                saved_result.save_version_number,
                saved_result.source_version_number,
                saved_result.requirement_version_number,
                saved_result.qualification_count,
                saved_result.saved_at_utc
            FROM dbo.opportunity_saved_results AS saved_result
            WHERE saved_result.opportunity_slate_id = @SlateId
              AND saved_result.owner_profile_id = @ProfileId
            ORDER BY saved_result.save_version_number DESC;

            SELECT
                saved_qualification.opportunity_saved_qualification_id AS qualification_id,
                saved_qualification.ordinal,
                saved_qualification.statement_class,
                saved_qualification.employer_text,
                saved_qualification.derived_status,
                saved_qualification.citation_count,
                saved_qualification.response_kind,
                saved_qualification.response_text,
                saved_qualification.authored_via,
                saved_qualification.connected_evidence_title,
                saved_qualification.connected_evidence_version
            FROM dbo.opportunity_saved_qualifications AS saved_qualification
            WHERE saved_qualification.opportunity_saved_result_id = @ResultId
              AND saved_qualification.owner_profile_id = @ProfileId
            ORDER BY saved_qualification.ordinal;

            SELECT
                saved_evidence.opportunity_saved_qualification_id AS qualification_id,
                saved_evidence.ordinal,
                saved_evidence.clause_ordinal,
                saved_evidence.covered_text,
                saved_evidence.evidence_kind,
                saved_evidence.evidence_key,
                saved_evidence.evidence_version,
                saved_evidence.evidence_title,
                saved_evidence.excerpt
            FROM dbo.opportunity_saved_evidence AS saved_evidence
            JOIN dbo.opportunity_saved_qualifications AS saved_qualification
              ON saved_qualification.opportunity_saved_qualification_id = saved_evidence.opportunity_saved_qualification_id
             AND saved_qualification.owner_profile_id = saved_evidence.owner_profile_id
            WHERE saved_qualification.opportunity_saved_result_id = @ResultId
              AND saved_evidence.owner_profile_id = @ProfileId
            ORDER BY saved_qualification.ordinal, saved_evidence.ordinal;

            /* CURRENCY. One row per distinct cited record: the KIND it was
               cited as, the version it was cited at, and the version the
               member''s library carries NOW. Owner-scoped on both sides; a key
               that is not this member''s simply fails the join and reports
               current_version = NULL.

               2026-08-04 INDEPENDENT REVIEW, FINDING F6. The kind is emitted
               and the join is now explicitly predicated on it. This query can
               price exactly ONE kind - knowledge_item - because that is the
               only library it reads. opportunity_saved_evidence''s CHECK also
               permits ''moment'' (handoff section 17-Q2), and without the
               predicate a Moment key would silently fail the knowledge_items
               join and report current_version = NULL forever: a saved slate
               reading "Inputs changed" permanently, with no member action able
               to clear it. Unreachable today - AI step 3 writes the literal
               N''knowledge_item'' - and the application now REFUSES any other
               kind on read rather than showing that permanent staleness. A
               slice that grounds on Moments must add its branch here AND widen
               SAVED_EVIDENCE_CURRENCY_KINDS in
               services/opportunity_slate_service.py; neither works alone. */
            SELECT
                pinned.evidence_kind,
                pinned.evidence_key,
                pinned.evidence_version AS pinned_version,
                item.confirmed_version_number AS current_version
            FROM
            (
                SELECT DISTINCT
                    saved_evidence.evidence_kind,
                    saved_evidence.evidence_key,
                    saved_evidence.evidence_version
                FROM dbo.opportunity_saved_evidence AS saved_evidence
                JOIN dbo.opportunity_saved_qualifications AS saved_qualification
                  ON saved_qualification.opportunity_saved_qualification_id = saved_evidence.opportunity_saved_qualification_id
                 AND saved_qualification.owner_profile_id = saved_evidence.owner_profile_id
                WHERE saved_qualification.opportunity_saved_result_id = @ResultId
                  AND saved_evidence.owner_profile_id = @ProfileId
            ) AS pinned
            LEFT JOIN dbo.knowledge_items AS item
              ON pinned.evidence_kind = N''knowledge_item''
             AND item.knowledge_item_key = pinned.evidence_key
             AND item.owner_profile_id = @ProfileId
             AND item.item_status = N''confirmed''
             AND item.archived_at_utc IS NULL
            ORDER BY pinned.evidence_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunitySlateForOwner
            @UserKey nvarchar(300),
            @IdempotencyKey nvarchar(4000),
            @RequirementSetKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @InputFingerprint nvarchar(4000)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* `Save privately`. Creates one IMMUTABLE saved result from this
               owner''s own confirmed inputs and current analysis.

               ORDER OF OPERATIONS IS LOAD-BEARING, and this procedure has an
               easier job than its siblings because it DELETES NOTHING. There
               is no previous row to destroy: saving again appends a new
               save_version_number. Every rejection below therefore returns
               before any INSERT as well, and the member''s existing saved
               versions, working session, analysis and responses are untouched
               on every non-success path.

               IDEMPOTENT. A repeated (owner, idempotency_key) returns the
               result it already created (outcome ''existing'') instead of
               appending a second identical version — the OS-1 save idiom,
               same key shape, checked inside the transaction under the same
               lock that would otherwise create the duplicate.

               @IdempotencyKey and @InputFingerprint are declared WIDE and
               measured here (the @IdempotencyKey idiom this file already
               documents): a narrow declaration truncates silently, so the
               guard would measure a string the caller never sent. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @RequirementSetKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome,
                       CAST(NULL AS uniqueidentifier) AS slate_key,
                       CAST(NULL AS uniqueidentifier) AS saved_result_key,
                       CAST(NULL AS int) AS save_version_number,
                       CAST(NULL AS int) AS qualification_count;
                RETURN;
            END;

            IF @IdempotencyKey IS NULL
               OR DATALENGTH(@IdempotencyKey) / 2 NOT BETWEEN 1 AND 200
               OR @InputFingerprint IS NULL
               OR DATALENGTH(@InputFingerprint) / 2 <> 64
               OR @InputFingerprint LIKE N''%[^0-9a-f]%''
            BEGIN
                SELECT N''invalid'' AS outcome,
                       CAST(NULL AS uniqueidentifier) AS slate_key,
                       CAST(NULL AS uniqueidentifier) AS saved_result_key,
                       CAST(NULL AS int) AS save_version_number,
                       CAST(NULL AS int) AS qualification_count;
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
                SELECT N''changed'' AS outcome,
                       CAST(NULL AS uniqueidentifier) AS slate_key,
                       CAST(NULL AS uniqueidentifier) AS saved_result_key,
                       CAST(NULL AS int) AS save_version_number,
                       CAST(NULL AS int) AS qualification_count;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @VersionId bigint;
            DECLARE @VersionNumber int;
            DECLARE @SourceVersionNumber int;
            DECLARE @SourceText nvarchar(max);
            DECLARE @AnalysisId bigint;
            DECLARE @AnalysisKey uniqueidentifier;
            DECLARE @ModelName nvarchar(200);
            DECLARE @PromptContract nvarchar(100);
            DECLARE @EvidenceCount int;
            DECLARE @QualificationCount int;
            DECLARE @SlateId bigint;
            DECLARE @SlateKey uniqueidentifier;
            DECLARE @ResultId bigint;
            DECLARE @SavedResultKey uniqueidentifier;
            DECLARE @SaveVersionNumber int;

            BEGIN TRY
                BEGIN TRANSACTION;

                /* THE IDEMPOTENT REPLAY, FIRST. Checked before anything is
                   read or written, so a double-submitted footer cannot append
                   a second saved version.

                   2026-08-04 INDEPENDENT REVIEW, FINDING F7. The probe HOLDS
                   ITS RANGE. Without a lock hint this read took no lock at
                   all, so two simultaneous requests carrying the same key
                   could both miss it, both proceed, and the loser would hit
                   UQ_opportunity_saved_results_idempotency and surface
                   as a 503 - telling the member their save failed when it had
                   in fact succeeded. UPDLOCK + HOLDLOCK over
                   (owner_profile_id, idempotency_key) takes a range lock on
                   the key that is NOT there, so the second request waits and
                   then reads the row the first one wrote, returning
                   ''existing'' exactly as a sequential replay would. The hint
                   sits on the saved_results side only; the slate join is a
                   lookup. The CATCH below still handles the violation, for the
                   same reason every guard in this file is doubled: a promise
                   the member is shown should not rest on one mechanism. */
                SELECT
                    @ResultId = saved_result.opportunity_saved_result_id,
                    @SavedResultKey = saved_result.saved_result_key,
                    @SaveVersionNumber = saved_result.save_version_number,
                    @QualificationCount = saved_result.qualification_count,
                    @SlateKey = slate.slate_key
                FROM dbo.opportunity_saved_results AS saved_result WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_slates AS slate
                  ON slate.opportunity_slate_id = saved_result.opportunity_slate_id
                 AND slate.owner_profile_id = saved_result.owner_profile_id
                WHERE saved_result.owner_profile_id = @ProfileId
                  AND saved_result.idempotency_key = @IdempotencyKey;

                IF @ResultId IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome, @SlateKey AS slate_key,
                           @SavedResultKey AS saved_result_key,
                           @SaveVersionNumber AS save_version_number,
                           @QualificationCount AS qualification_count;
                    RETURN;
                END;

                /* The confirmed requirement set, fenced on its row_version,
                   inside a live working session — the same predicate
                   usp_SaveOpportunityAnalysisForOwner uses, so a member
                   cannot save a reading they have since changed. */
                SELECT
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
                    SELECT N''changed'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS slate_key,
                           CAST(NULL AS uniqueidentifier) AS saved_result_key,
                           CAST(NULL AS int) AS save_version_number,
                           CAST(NULL AS int) AS qualification_count;
                    RETURN;
                END;

                /* The employer wording the member confirmed, copied verbatim:
                   the correction overlay when there is one, otherwise the
                   captured original. Read through the source''s own confirmed
                   version number so a later appended version cannot be saved
                   as though it had been confirmed. */
                SELECT @SourceText = COALESCE(version_record.member_corrected_text,
                                              version_record.original_text)
                FROM dbo.opportunity_source_versions AS version_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.working_session_id = source_record.working_session_id
                 AND requirement_set.owner_profile_id = source_record.owner_profile_id
                WHERE requirement_set.requirement_set_key = @RequirementSetKey
                  AND version_record.owner_profile_id = @ProfileId
                  AND version_record.version_number = source_record.confirmed_version_number
                  AND source_record.confirmed_version_number = @SourceVersionNumber;

                SELECT
                    @AnalysisId = analysis_record.opportunity_analysis_id,
                    @AnalysisKey = analysis_record.analysis_key,
                    @ModelName = analysis_record.model_name,
                    @PromptContract = analysis_record.prompt_contract_version,
                    @EvidenceCount = analysis_record.evidence_considered_count,
                    @QualificationCount = analysis_record.qualification_count
                FROM dbo.opportunity_analyses AS analysis_record
                WHERE analysis_record.opportunity_requirement_set_version_id = @VersionId
                  AND analysis_record.owner_profile_id = @ProfileId;

                /* Nothing to save is not a failure of this procedure and not a
                   conflict either: there is simply no analysis yet, or the
                   confirmed source went missing under it. Both return
                   ''invalid'' BEFORE any write. */
                IF @AnalysisId IS NULL OR @SourceText IS NULL
                   OR DATALENGTH(@SourceText) / 2 NOT BETWEEN 1 AND 20000
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''invalid'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS slate_key,
                           CAST(NULL AS uniqueidentifier) AS saved_result_key,
                           CAST(NULL AS int) AS save_version_number,
                           CAST(NULL AS int) AS qualification_count;
                    RETURN;
                END;

                /* One slate per member. Created together with its first save,
                   never on its own, so an empty slate cannot exist. */
                SELECT @SlateId = slate.opportunity_slate_id,
                       @SlateKey = slate.slate_key
                FROM dbo.opportunity_slates AS slate WITH (UPDLOCK, HOLDLOCK)
                WHERE slate.owner_profile_id = @ProfileId;

                IF @SlateId IS NULL
                BEGIN
                    INSERT dbo.opportunity_slates
                        (owner_profile_id, created_at_utc, updated_at_utc)
                    VALUES (@ProfileId, @Now, @Now);
                    SET @SlateId = SCOPE_IDENTITY();
                    SELECT @SlateKey = slate.slate_key
                    FROM dbo.opportunity_slates AS slate
                    WHERE slate.opportunity_slate_id = @SlateId
                      AND slate.owner_profile_id = @ProfileId;
                END;

                SELECT @SaveVersionNumber = COALESCE(MAX(saved_result.save_version_number), 0) + 1
                FROM dbo.opportunity_saved_results AS saved_result
                WHERE saved_result.opportunity_slate_id = @SlateId
                  AND saved_result.owner_profile_id = @ProfileId;

                INSERT dbo.opportunity_saved_results
                    (opportunity_slate_id, owner_profile_id, save_version_number,
                     source_version_number, requirement_version_number,
                     saved_analysis_key, source_text, model_name,
                     prompt_contract_version, evidence_considered_count,
                     qualification_count, input_fingerprint, idempotency_key,
                     saved_by_user_id, saved_at_utc)
                VALUES
                    (@SlateId, @ProfileId, @SaveVersionNumber,
                     @SourceVersionNumber, @VersionNumber,
                     @AnalysisKey, @SourceText, @ModelName,
                     @PromptContract, @EvidenceCount,
                     @QualificationCount, LOWER(@InputFingerprint), @IdempotencyKey,
                     @UserId, @Now);
                SET @ResultId = SCOPE_IDENTITY();

                /* THE SNAPSHOT, COPIED FROM THIS OWNER''S OWN ROWS. Not one
                   value here comes from the caller. The member''s response is
                   carried across on the same row as the qualification it
                   answers, which is what handoff section 7 means by "the
                   member''s response context". */
                INSERT dbo.opportunity_saved_qualifications
                    (opportunity_saved_result_id, owner_profile_id, ordinal,
                     statement_class, employer_text, derived_status, citation_count,
                     response_kind, response_text, authored_via,
                     connected_evidence_title, connected_evidence_version)
                SELECT
                    @ResultId,
                    @ProfileId,
                    analysis_statement.ordinal,
                    COALESCE(statement_record.member_class, statement_record.proposed_class),
                    statement_record.employer_text,
                    analysis_statement.derived_status,
                    analysis_statement.citation_count,
                    response_record.response_kind,
                    response_record.response_text,
                    response_record.authored_via,
                    response_record.connected_evidence_title,
                    response_record.connected_evidence_version
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = analysis_statement.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = analysis_statement.owner_profile_id
                LEFT JOIN dbo.opportunity_responses AS response_record
                  ON response_record.opportunity_requirement_statement_id = statement_record.opportunity_requirement_statement_id
                 AND response_record.owner_profile_id = statement_record.owner_profile_id
                WHERE analysis_statement.opportunity_analysis_id = @AnalysisId
                  AND analysis_statement.owner_profile_id = @ProfileId
                ORDER BY analysis_statement.ordinal;

                INSERT dbo.opportunity_saved_evidence
                    (opportunity_saved_qualification_id, owner_profile_id, ordinal,
                     clause_ordinal, covered_text, evidence_kind, evidence_key,
                     evidence_version, evidence_title, excerpt)
                SELECT
                    saved_qualification.opportunity_saved_qualification_id,
                    @ProfileId,
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
                JOIN dbo.opportunity_saved_qualifications AS saved_qualification
                  ON saved_qualification.opportunity_saved_result_id = @ResultId
                 AND saved_qualification.ordinal = analysis_statement.ordinal
                 AND saved_qualification.owner_profile_id = analysis_statement.owner_profile_id
                WHERE analysis_statement.opportunity_analysis_id = @AnalysisId
                  AND citation_record.owner_profile_id = @ProfileId;

                UPDATE dbo.opportunity_slates
                SET current_save_version_number = @SaveVersionNumber,
                    updated_at_utc = @Now
                WHERE opportunity_slate_id = @SlateId
                  AND owner_profile_id = @ProfileId;

                SELECT @SavedResultKey = saved_result.saved_result_key
                FROM dbo.opportunity_saved_results AS saved_result
                WHERE saved_result.opportunity_saved_result_id = @ResultId
                  AND saved_result.owner_profile_id = @ProfileId;

                /* NO AUDIT EVENT, and this is the slice where that decision
                   had to be made deliberately rather than inherited. The OS-1
                   header called the saved slate "the durable, auditable
                   artifact", so appending one here is the obvious move. Two
                   facts about the platform''s audit-append procedure make it
                   the wrong one: it ends in SELECT *, so calling it would
                   emit a result set AHEAD of this procedure''s own outcome
                   row and break every caller that reads the first row; and
                   dbo.audit_events carries an immutability trigger, so the
                   row would outlive the member''s explicit delete - an
                   undeletable trace of a private action they asked to remove.
                   Neither is worth trading for a log line nobody currently
                   reads. The member-facing record IS the saved slate, and the
                   operator-facing record is the migration''s own applied
                   event. */
                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @SlateKey AS slate_key,
                       @SavedResultKey AS saved_result_key,
                       @SaveVersionNumber AS save_version_number,
                       @QualificationCount AS qualification_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;

                /* FINDING F7, second mechanism. If the range lock above is
                   ever defeated - a rebuilt index, a future isolation change,
                   a snapshot-read plan - the loser of a same-key race lands
                   on the unique index instead. That is a SUCCEEDED save from
                   the member''s point of view: the winner committed the row
                   they asked for. Re-read it AFTER the rollback and report
                   ''existing'', which is exactly what a sequential replay
                   returns. Any other error still THROWs untouched. */
                IF ERROR_NUMBER() IN (2601, 2627)
                BEGIN
                    SELECT
                        @ResultId = saved_result.opportunity_saved_result_id,
                        @SavedResultKey = saved_result.saved_result_key,
                        @SaveVersionNumber = saved_result.save_version_number,
                        @QualificationCount = saved_result.qualification_count,
                        @SlateKey = slate.slate_key
                    FROM dbo.opportunity_saved_results AS saved_result
                    JOIN dbo.opportunity_slates AS slate
                      ON slate.opportunity_slate_id = saved_result.opportunity_slate_id
                     AND slate.owner_profile_id = saved_result.owner_profile_id
                    WHERE saved_result.owner_profile_id = @ProfileId
                      AND saved_result.idempotency_key = @IdempotencyKey;

                    IF @ResultId IS NOT NULL
                    BEGIN
                        SELECT N''existing'' AS outcome, @SlateKey AS slate_key,
                               @SavedResultKey AS saved_result_key,
                               @SaveVersionNumber AS save_version_number,
                               @QualificationCount AS qualification_count;
                        RETURN;
                    END;
                END;

                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteOpportunitySavedSlateForOwner
            @UserKey nvarchar(300),
            @SlateKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* The member''s explicit deletion of their saved slate, and every
               saved version in it.

               ATOMIC IS A PROMISE THE MEMBER IS SHOWN (image 09-d: "It
               remains saved privately. Nothing was removed."). One
               transaction, children before parents, every predicate
               re-asserting owner_profile_id. A failure anywhere leaves the
               slate whole — not partly deleted, and not deleted-but-reported-
               as-failed.

               It touches NO working data. The working session, its source and
               its analysis are separate, ephemeral, and the member may still
               be using them. */
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SlateKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_result_count;
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
                SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_result_count;
                RETURN;
            END;

            DECLARE @SlateId bigint;
            DECLARE @DeletedResultCount int = 0;

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT @SlateId = slate.opportunity_slate_id
                FROM dbo.opportunity_slates AS slate WITH (UPDLOCK, HOLDLOCK)
                WHERE slate.slate_key = @SlateKey
                  AND slate.owner_profile_id = @ProfileId
                  AND slate.row_version = @ExpectedRowVersion;

                IF @SlateId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_result_count;
                    RETURN;
                END;

                DELETE saved_evidence
                FROM dbo.opportunity_saved_evidence AS saved_evidence
                JOIN dbo.opportunity_saved_qualifications AS saved_qualification
                  ON saved_qualification.opportunity_saved_qualification_id = saved_evidence.opportunity_saved_qualification_id
                 AND saved_qualification.owner_profile_id = saved_evidence.owner_profile_id
                JOIN dbo.opportunity_saved_results AS saved_result
                  ON saved_result.opportunity_saved_result_id = saved_qualification.opportunity_saved_result_id
                 AND saved_result.owner_profile_id = saved_qualification.owner_profile_id
                WHERE saved_result.opportunity_slate_id = @SlateId
                  AND saved_evidence.owner_profile_id = @ProfileId;

                DELETE saved_qualification
                FROM dbo.opportunity_saved_qualifications AS saved_qualification
                JOIN dbo.opportunity_saved_results AS saved_result
                  ON saved_result.opportunity_saved_result_id = saved_qualification.opportunity_saved_result_id
                 AND saved_result.owner_profile_id = saved_qualification.owner_profile_id
                WHERE saved_result.opportunity_slate_id = @SlateId
                  AND saved_qualification.owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_saved_results
                WHERE opportunity_slate_id = @SlateId AND owner_profile_id = @ProfileId;
                SET @DeletedResultCount = @@ROWCOUNT;

                DELETE dbo.opportunity_slates
                WHERE opportunity_slate_id = @SlateId AND owner_profile_id = @ProfileId;

                /* No audit event, for the reasons stated in the save
                   procedure above — and here the second of them is the whole
                   point: a member deleting their saved slate must not leave
                   an immutable row behind saying they had one. */
                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @DeletedResultCount AS deleted_result_count;
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
       PS_OPPSLATE_003_DEFINITION_HASH idiom PS-OPPSLATE-002 introduced for
       PS-OPPSLATE-001's OS-3 delta). This migration revises no existing
       procedure - see the header - so only the three it creates are
       fingerprinted.
       ------------------------------------------------------------ */
    DECLARE @ProcedureHashPropertyName sysname = N'PS_OPPSLATE_003_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_GetOpportunitySavedSlateForOwner'),
        (N'usp_SaveOpportunitySlateForOwner'),
        (N'usp_DeleteOpportunitySavedSlateForOwner');
    DECLARE @ProtectedProcedureName sysname, @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures ORDER BY procedure_name;
        IF OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P') IS NULL
            THROW 53725, 'A required OS-4 procedure was not created.', 1;
        SELECT @ProtectedProcedureHash = CONVERT(nvarchar(64),
            HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P'))), 2);
        IF EXISTS (SELECT 1 FROM sys.extended_properties
                   WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
                     AND minor_id = 0 AND name = @ProcedureHashPropertyName)
            EXEC sys.sp_updateextendedproperty @name=@ProcedureHashPropertyName,
                @value=@ProtectedProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty @name=@ProcedureHashPropertyName,
                @value=@ProtectedProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@ProtectedProcedureName;
        DELETE @ProtectedProcedures WHERE procedure_name = @ProtectedProcedureName;
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-003')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-OPPSLATE-003', N'Slice OS-4 additive: the durable saved slate (slates / saved_results / saved_qualifications / saved_evidence), three new owner-scoped save-lifecycle procedures, and the currency fingerprint that keeps saved and still-accurate two separate truths. Requires the PS-OPPSLATE-001 OS-2 and PS-OPPSLATE-002 OS-3 baseline. No existing procedure is revised. No aggregate score, percentage, ranking, recommendation, or verdict.', N'PeerSlate Bible and Roadmap v3.0');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied',
            @EntityType=N'database_migration', @Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-OPPSLATE-003"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
