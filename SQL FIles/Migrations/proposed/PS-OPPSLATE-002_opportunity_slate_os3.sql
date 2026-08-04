/* ============================================================
   PS-OPPSLATE-002 - Opportunity Slate OS-3 additive schema

   Immutable follow-on to the production-ledgered PS-OPPSLATE-001 OS-1/OS-2
   baseline. Adds four OS-3 tables and four procedures, and revises the four
   existing delete paths that must account for the new rows. It never updates
   or reuses the PS-OPPSLATE-001 ledger row. A missing or partial OS-2 baseline
   fails before the first mutation.

   No aggregate score, percentage, ranking, recommendation, employer
   prediction, or traffic-light verdict is introduced.
   Rollback: PS-OPPSLATE-002_opportunity_slate_os3_rollback.sql
   Verification: ../../Verification/PS-OPPSLATE-002_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53620, 'PS-OPPSLATE-002 requires the migration ledger.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-OPPSLATE-001')
        THROW 53621, 'PS-OPPSLATE-001 must be applied before PS-OPPSLATE-002.', 1;

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
        (N'dbo.usp_ConfirmOpportunityRequirementsForOwner', N'P');
    IF EXISTS (SELECT 1 FROM @RequiredBaselineObjects
               WHERE OBJECT_ID(object_name, object_type) IS NULL)
        THROW 53622, 'PS-OPPSLATE-001 does not match the required OS-2 object baseline.', 1;
    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints
                   WHERE parent_object_id = OBJECT_ID(N'dbo.opportunity_source_versions')
                     AND name = N'UQ_opportunity_source_versions_id_owner')
       OR NOT EXISTS (SELECT 1 FROM sys.check_constraints
                      WHERE parent_object_id = OBJECT_ID(N'dbo.opportunity_working_sessions')
                        AND name = N'CK_opportunity_working_sessions_state'
                        AND definition LIKE N'%review\_requirements%' ESCAPE N'\'
                        AND definition LIKE N'%requirements\_confirmed%' ESCAPE N'\')
        THROW 53623, 'The PS-OPPSLATE-001 baseline is older than OS-2.', 1;

    DECLARE @Os3Objects TABLE
        (object_name nvarchar(300) NOT NULL, object_type char(1) NOT NULL);
    INSERT @Os3Objects (object_name, object_type)
    VALUES
        (N'dbo.opportunity_analyses', N'U'),
        (N'dbo.opportunity_analysis_statements', N'U'),
        (N'dbo.opportunity_analysis_citations', N'U'),
        (N'dbo.opportunity_responses', N'U'),
        (N'dbo.usp_ListOpportunityEvidenceForOwner', N'P'),
        (N'dbo.usp_GetOpportunityAnalysisForOwner', N'P'),
        (N'dbo.usp_SaveOpportunityAnalysisForOwner', N'P'),
        (N'dbo.usp_SaveOpportunityResponseForOwner', N'P');
    DECLARE @ExistingOs3ObjectCount int =
        (SELECT COUNT(*) FROM @Os3Objects WHERE OBJECT_ID(object_name, object_type) IS NOT NULL);
    IF @ExistingOs3ObjectCount NOT IN (0, 8)
        THROW 53624, 'A partial OS-3 schema exists without a complete additive migration.', 1;

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

    DECLARE @ProcedureHashPropertyName sysname = N'PS_OPPSLATE_002_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunityRequirementProposalForOwner'),
        (N'usp_CorrectOpportunityRequirementStatementForOwner'),
        (N'usp_ListOpportunityEvidenceForOwner'),
        (N'usp_GetOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityResponseForOwner');
    DECLARE @ProtectedProcedureName sysname, @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures ORDER BY procedure_name;
        IF OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P') IS NULL
            THROW 53625, 'A required OS-3 procedure was not created.', 1;
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

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-002')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-OPPSLATE-002', N'Slice OS-3 additive: four grounded analysis/response tables, four new owner-scoped procedures, and OS-3 revisions to purge, delete, requirement replacement, and statement correction. Requires the PS-OPPSLATE-001 OS-2 baseline. No aggregate score, percentage, ranking, recommendation, or verdict.', N'PeerSlate Bible and Roadmap v3.0');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied',
            @EntityType=N'database_migration', @Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-OPPSLATE-002"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
