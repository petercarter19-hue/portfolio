/* ============================================================
   PS-OPPSLATE-002 ROLLBACK - guarded OS-3 additive reversal

   Refuses to discard any OS-3 analysis, citation, or member-response row,
   any later migration, or a drifted owned procedure. Drops the four OS-3
   procedures, restores the four revised procedures to their gated OS-2
   definitions, drops the four OS-3 tables, and removes only the
   PS-OPPSLATE-002 ledger row. PS-OPPSLATE-001 and OS-1/OS-2 data remain.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53630, 'Rollback refused: the migration ledger is missing.', 1;
    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc=applied_at_utc FROM dbo.schema_migrations WITH (UPDLOCK,HOLDLOCK)
    WHERE migration_id=N'PS-OPPSLATE-002';
    IF @AppliedAtUtc IS NULL
        THROW 53631, 'Rollback refused: PS-OPPSLATE-002 is not recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc>@AppliedAtUtc)
        THROW 53632, 'Rollback refused: a migration later than PS-OPPSLATE-002 is present.', 1;

    DECLARE @ProcedureHashPropertyName sysname=N'PS_OPPSLATE_002_DEFINITION_HASH';
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
    IF EXISTS
    (
        SELECT 1 FROM @ProtectedProcedures p
        LEFT JOIN sys.procedures o ON o.schema_id=SCHEMA_ID(N'dbo') AND o.name=p.procedure_name
        LEFT JOIN sys.extended_properties x ON x.class=1 AND x.major_id=o.object_id
             AND x.minor_id=0 AND x.name=@ProcedureHashPropertyName
        WHERE o.object_id IS NULL OR x.major_id IS NULL
           OR CONVERT(nvarchar(64),x.value)<>CONVERT(nvarchar(64),
              HASHBYTES('SHA2_256',OBJECT_DEFINITION(o.object_id)),2)
    )
        THROW 53633, 'Rollback refused: a protected OS-3 procedure changed after PS-OPPSLATE-002.', 1;

    IF OBJECT_ID(N'dbo.opportunity_responses',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_responses)
        THROW 53634, 'Rollback refused: opportunity_responses contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_analysis_citations',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_analysis_citations)
        THROW 53635, 'Rollback refused: opportunity_analysis_citations contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_analysis_statements',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_analysis_statements)
        THROW 53636, 'Rollback refused: opportunity_analysis_statements contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_analyses',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_analyses)
        THROW 53637, 'Rollback refused: opportunity_analyses contains member records.', 1;

    IF OBJECT_ID(N'dbo.usp_SaveOpportunityResponseForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunityResponseForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunityAnalysisForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunityAnalysisForOwner;
    IF OBJECT_ID(N'dbo.usp_GetOpportunityAnalysisForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunityAnalysisForOwner;
    IF OBJECT_ID(N'dbo.usp_ListOpportunityEvidenceForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListOpportunityEvidenceForOwner;

    DECLARE @RevisedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @RevisedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunityRequirementProposalForOwner'),
        (N'usp_CorrectOpportunityRequirementStatementForOwner');
    DECLARE @RevisedProcedureName sysname;
    WHILE EXISTS (SELECT 1 FROM @RevisedProcedures)
    BEGIN
        SELECT TOP (1) @RevisedProcedureName=procedure_name FROM @RevisedProcedures ORDER BY procedure_name;
        IF EXISTS (SELECT 1 FROM sys.extended_properties WHERE class=1
                   AND major_id=OBJECT_ID(N'dbo.'+@RevisedProcedureName,N'P')
                   AND minor_id=0 AND name=@ProcedureHashPropertyName)
            EXEC sys.sp_dropextendedproperty @name=@ProcedureHashPropertyName,
                @level0type=N'SCHEMA',@level0name=N'dbo',
                @level1type=N'PROCEDURE',@level1name=@RevisedProcedureName;
        DELETE @RevisedProcedures WHERE procedure_name=@RevisedProcedureName;
    END;

    /* Restore the four OS-2 definitions changed by OS-3. */
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

    IF OBJECT_ID(N'dbo.opportunity_responses',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_responses;
    IF OBJECT_ID(N'dbo.opportunity_analysis_citations',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_analysis_citations;
    IF OBJECT_ID(N'dbo.opportunity_analysis_statements',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_analysis_statements;
    IF OBJECT_ID(N'dbo.opportunity_analyses',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_analyses;

    DELETE dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-002';
    IF OBJECT_ID(N'dbo.usp_AppendAuditEvent',N'P') IS NOT NULL
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.rolled_back',
            @EntityType=N'database_migration',@Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-OPPSLATE-002"}';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
