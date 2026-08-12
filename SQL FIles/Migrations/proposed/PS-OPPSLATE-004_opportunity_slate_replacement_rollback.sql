/* ============================================================
   PS-OPPSLATE-004 ROLLBACK - guarded replacement-R1 additive reversal

   Refuses to discard any source identity, requirement review event, or
   member take row, any later migration, or a drifted owned procedure.
   Drops the two new procedures (usp_SaveOpportunitySourceIdentityForOwner,
   usp_GetOpportunitySourceIdentityForOwner), restores
   usp_PurgeExpiredOpportunityWorkingData and
   usp_DeleteOpportunityWorkingSessionForOwner to bodies functionally
   identical to their PS-OPPSLATE-002 (OS-3) originals -- every statement
   matches exactly; this restore's own block comments do not reproduce
   OS-3's, so the live body after rollback is not a byte-for-byte copy of
   the OS-3 migration file's text, only of its behavior -- re-stamping
   PS_OPPSLATE_002_DEFINITION_HASH from that restored (comment-stripped)
   body so the chain stays reversible in sequence -- drops the two additive
   opportunity_analyses columns and the one additive
   opportunity_requirement_sets column, drops the three new tables (children
   before parents), and removes only the PS-OPPSLATE-004 ledger row.
   PS-OPPSLATE-001/002/003 objects and data remain untouched.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53820, 'Rollback refused: the migration ledger is missing.', 1;
    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc=applied_at_utc FROM dbo.schema_migrations WITH (UPDLOCK,HOLDLOCK)
    WHERE migration_id=N'PS-OPPSLATE-004';
    IF @AppliedAtUtc IS NULL
        THROW 53821, 'Rollback refused: PS-OPPSLATE-004 is not recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc>@AppliedAtUtc)
        THROW 53822, 'Rollback refused: a migration later than PS-OPPSLATE-004 is present.', 1;

    /* Every procedure PS-OPPSLATE-004 owns (created new, or took over) must
       still carry the exact body it was fingerprinted with at apply time.
       A drifted body means an operator hand-patched or otherwise changed a
       procedure this rollback is about to drop or rewrite. */
    DECLARE @ProcedureHashPropertyName sysname=N'PS_OPPSLATE_004_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunitySourceIdentityForOwner'),
        (N'usp_GetOpportunitySourceIdentityForOwner');
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
        THROW 53823, 'Rollback refused: a protected PS-OPPSLATE-004 procedure changed after apply.', 1;

    /* Refuse while a member record exists in any table this migration owns.
       Children before parents, so an operator hears about the innermost
       record first -- the same ordering PS-OPPSLATE-002/003's rollbacks use. */
    IF OBJECT_ID(N'dbo.opportunity_member_takes',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_member_takes)
        THROW 53824, 'Rollback refused: opportunity_member_takes contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_requirement_review_events',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events)
        THROW 53825, 'Rollback refused: opportunity_requirement_review_events contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_source_identities',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_source_identities)
        THROW 53826, 'Rollback refused: opportunity_source_identities contains member records.', 1;

    /* Names alone are not ownership. Forward apply stamps every independently
       droppable table and additive column after proving it was absent. Refuse
       rollback if any stamp is missing so an unknown pre-existing surface is
       never removed merely because its name matches this package. */
    DECLARE @OwnershipPropertyName sysname = N'PS_OPPSLATE_004_OWNED';
    IF EXISTS
    (
        SELECT 1
        FROM (VALUES
            (N'opportunity_source_identities'),
            (N'opportunity_requirement_review_events'),
            (N'opportunity_member_takes')
        ) AS owned(table_name)
        LEFT JOIN sys.tables AS table_record
          ON table_record.schema_id = SCHEMA_ID(N'dbo')
         AND table_record.name = owned.table_name
        LEFT JOIN sys.extended_properties AS property_record
          ON property_record.class = 1
         AND property_record.major_id = table_record.object_id
         AND property_record.minor_id = 0
         AND property_record.name = @OwnershipPropertyName
        WHERE property_record.major_id IS NULL
    )
        THROW 53827, 'Rollback refused: a PS-OPPSLATE-004 table ownership stamp is missing.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM (VALUES
            (N'opportunity_analyses', N'evidence_snapshot_sha256'),
            (N'opportunity_analyses', N'confirmed_requirements_ordinal'),
            (N'opportunity_requirement_sets', N'member_confirmed_ordinal')
        ) AS owned(table_name, column_name)
        LEFT JOIN sys.tables AS table_record
          ON table_record.schema_id = SCHEMA_ID(N'dbo')
         AND table_record.name = owned.table_name
        LEFT JOIN sys.columns AS column_record
          ON column_record.object_id = table_record.object_id
         AND column_record.name = owned.column_name
        LEFT JOIN sys.extended_properties AS property_record
          ON property_record.class = 1
         AND property_record.major_id = table_record.object_id
         AND property_record.minor_id = column_record.column_id
         AND property_record.name = @OwnershipPropertyName
        WHERE property_record.major_id IS NULL
    )
        THROW 53828, 'Rollback refused: a PS-OPPSLATE-004 column ownership stamp is missing.', 1;

    IF OBJECT_ID(N'dbo.usp_SaveOpportunitySourceIdentityForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunitySourceIdentityForOwner;
    IF OBJECT_ID(N'dbo.usp_GetOpportunitySourceIdentityForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunitySourceIdentityForOwner;

    /* Drop this migration's stamp from the two taken-over procedures before
       restoring their bodies. The PS_OPPSLATE_002_DEFINITION_HASH property
       from PS-OPPSLATE-002's own takeover was never removed by this
       migration's forward script, so it is still attached and will again
       describe the live body the moment the restore below runs. */
    DECLARE @RevisedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @RevisedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner');
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

    /* Restore the two PS-OPPSLATE-002 (OS-3) definitions PS-OPPSLATE-004
       revised: every statement below matches the OS-3 originals exactly
       (mechanically diffed; independent review finding), but OS-3's own
       block comments are not reproduced here, so this is a functional
       restore, not a byte-for-byte one -- the hash re-stamp below is
       computed from this exact (comment-stripped) body, so every guard in
       the chain stays self-consistent regardless. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeExpiredOpportunityWorkingData
            @UserKey nvarchar(300),
            @IncludeCounts bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

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
            DECLARE @OuterTranCount int = @@TRANCOUNT;

            BEGIN TRY
                IF @OuterTranCount = 0 BEGIN TRANSACTION;

                INSERT @ExpiredSessions (working_session_id)
                SELECT working_session.working_session_id
                FROM dbo.opportunity_working_sessions AS working_session WITH (UPDLOCK, HOLDLOCK)
                WHERE working_session.owner_profile_id = @ProfileId
                  AND working_session.expires_at_utc <= @Now;

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

    DECLARE @RestoredProcedureHashPropertyName sysname = N'PS_OPPSLATE_002_DEFINITION_HASH';
    DECLARE @RestoredProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @RestoredProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner');
    DECLARE @RestoredProcedureName sysname, @RestoredProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @RestoredProcedures)
    BEGIN
        SELECT TOP (1) @RestoredProcedureName = procedure_name
        FROM @RestoredProcedures ORDER BY procedure_name;
        SELECT @RestoredProcedureHash = CONVERT(nvarchar(64),
            HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @RestoredProcedureName, N'P'))), 2);
        IF EXISTS (SELECT 1 FROM sys.extended_properties
                   WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @RestoredProcedureName, N'P')
                     AND minor_id = 0 AND name = @RestoredProcedureHashPropertyName)
            EXEC sys.sp_updateextendedproperty @name=@RestoredProcedureHashPropertyName,
                @value=@RestoredProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@RestoredProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty @name=@RestoredProcedureHashPropertyName,
                @value=@RestoredProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@RestoredProcedureName;
        DELETE @RestoredProcedures WHERE procedure_name = @RestoredProcedureName;
    END;

    /* Children before parents, so no drop ever runs against an object a
       foreign key still points at. */
    IF OBJECT_ID(N'dbo.opportunity_member_takes',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_member_takes;
    IF OBJECT_ID(N'dbo.opportunity_requirement_review_events',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_requirement_review_events;
    IF OBJECT_ID(N'dbo.opportunity_source_identities',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_source_identities;

    IF EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE name = N'CK_opportunity_requirement_sets_member_confirmed_ordinal')
        ALTER TABLE dbo.opportunity_requirement_sets
            DROP CONSTRAINT CK_opportunity_requirement_sets_member_confirmed_ordinal;
    IF COL_LENGTH(N'dbo.opportunity_requirement_sets', N'member_confirmed_ordinal') IS NOT NULL
        ALTER TABLE dbo.opportunity_requirement_sets DROP COLUMN member_confirmed_ordinal;

    IF EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE name = N'CK_opportunity_analyses_confirmed_ordinal')
        ALTER TABLE dbo.opportunity_analyses DROP CONSTRAINT CK_opportunity_analyses_confirmed_ordinal;
    IF EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE name = N'CK_opportunity_analyses_evidence_snapshot_hash')
        ALTER TABLE dbo.opportunity_analyses DROP CONSTRAINT CK_opportunity_analyses_evidence_snapshot_hash;
    IF COL_LENGTH(N'dbo.opportunity_analyses', N'confirmed_requirements_ordinal') IS NOT NULL
        ALTER TABLE dbo.opportunity_analyses DROP COLUMN confirmed_requirements_ordinal;
    IF COL_LENGTH(N'dbo.opportunity_analyses', N'evidence_snapshot_sha256') IS NOT NULL
        ALTER TABLE dbo.opportunity_analyses DROP COLUMN evidence_snapshot_sha256;

    DELETE dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-004';
    IF OBJECT_ID(N'dbo.usp_AppendAuditEvent',N'P') IS NOT NULL
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.rolled_back',
            @EntityType=N'database_migration',@Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-OPPSLATE-004"}';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
