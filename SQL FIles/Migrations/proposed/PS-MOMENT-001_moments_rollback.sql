/* ============================================================
   PS-MOMENT-001 ROLLBACK - guarded private Moment removal

   Refuses to discard any Moment, proposal/version/source data or
   later dependency. Restores the exact PS-CAPTURE-002 delete
   behavior before removing only PS-MOMENT-001 objects.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @MomentAppliedAtUtc datetime2(7);
    SELECT @MomentAppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-MOMENT-001';

    IF @MomentAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM dbo.schema_migrations AS migration
           WHERE migration.applied_at_utc > @MomentAppliedAtUtc
       )
        THROW 52235, 'Rollback blocked: a migration later than PS-MOMENT-001 is present.', 1;

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_MOMENT_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreateOrReopenMomentProposal'),
        (N'usp_GetMomentForOwner'),
        (N'usp_SaveMomentProposal'),
        (N'usp_ConfirmMoment'),
        (N'usp_DiscardMomentProposal'),
        (N'usp_DeleteCapture');

    IF @MomentAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM @ProtectedProcedures AS protected_procedure
           LEFT JOIN sys.procedures AS procedure_object
             ON procedure_object.schema_id = SCHEMA_ID(N'dbo')
            AND procedure_object.name = protected_procedure.procedure_name
           LEFT JOIN sys.extended_properties AS property
             ON property.class = 1
            AND property.major_id = procedure_object.object_id
            AND property.minor_id = 0
            AND property.name = @ProcedureHashPropertyName
           WHERE procedure_object.object_id IS NULL
              OR property.major_id IS NULL
              OR CONVERT(nvarchar(64), property.value) <>
                 CONVERT
                 (
                     nvarchar(64),
                     HASHBYTES
                     (
                         'SHA2_256',
                         OBJECT_DEFINITION(procedure_object.object_id)
                     ),
                     2
                 )
       )
        THROW 52236, 'Rollback blocked: a protected procedure changed after PS-MOMENT-001.', 1;

    IF OBJECT_ID(N'dbo.moments', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.moments)
        THROW 52230, 'Rollback blocked: moments contains member records.', 1;
    IF OBJECT_ID(N'dbo.moment_versions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.moment_versions)
        THROW 52231, 'Rollback blocked: moment_versions contains member proposals.', 1;
    IF OBJECT_ID(N'dbo.moment_sources', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.moment_sources)
        THROW 52232, 'Rollback blocked: moment_sources contains source relationships.', 1;

    DECLARE @MomentTableIds TABLE (object_id int PRIMARY KEY);
    INSERT @MomentTableIds (object_id)
    SELECT object_id
    FROM sys.tables
    WHERE object_id IN
    (
        OBJECT_ID(N'dbo.moments'),
        OBJECT_ID(N'dbo.moment_versions'),
        OBJECT_ID(N'dbo.moment_sources')
    );

    IF EXISTS
    (
        SELECT 1
        FROM sys.foreign_keys AS foreign_key
        WHERE foreign_key.referenced_object_id IN
              (SELECT object_id FROM @MomentTableIds)
          AND foreign_key.parent_object_id NOT IN
              (SELECT object_id FROM @MomentTableIds)
    )
        THROW 52233, 'Rollback blocked: a later table depends on PS-MOMENT-001.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.sql_expression_dependencies AS dependency
        WHERE dependency.referenced_id IN (SELECT object_id FROM @MomentTableIds)
          AND dependency.referencing_id NOT IN
          (
              OBJECT_ID(N'dbo.usp_CreateOrReopenMomentProposal'),
              OBJECT_ID(N'dbo.usp_GetMomentForOwner'),
              OBJECT_ID(N'dbo.usp_SaveMomentProposal'),
              OBJECT_ID(N'dbo.usp_ConfirmMoment'),
              OBJECT_ID(N'dbo.usp_DiscardMomentProposal'),
              OBJECT_ID(N'dbo.usp_DeleteCapture')
          )
          AND dependency.referencing_id NOT IN (SELECT object_id FROM @MomentTableIds)
          AND dependency.referencing_id NOT IN
          (
              SELECT object_id FROM sys.objects
              WHERE parent_object_id IN (SELECT object_id FROM @MomentTableIds)
          )
    )
        THROW 52234, 'Rollback blocked: a later programmable object depends on PS-MOMENT-001.', 1;

    IF OBJECT_ID(N'dbo.usp_CreateOrReopenMomentProposal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CreateOrReopenMomentProposal;
    IF OBJECT_ID(N'dbo.usp_GetMomentForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetMomentForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveMomentProposal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveMomentProposal;
    IF OBJECT_ID(N'dbo.usp_ConfirmMoment', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ConfirmMoment;
    IF OBJECT_ID(N'dbo.usp_DiscardMomentProposal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_DiscardMomentProposal;

    IF EXISTS
    (
        SELECT 1
        FROM sys.extended_properties AS property
        WHERE property.class = 1
          AND property.major_id = OBJECT_ID(N'dbo.usp_DeleteCapture', N'P')
          AND property.minor_id = 0
          AND property.name = @ProcedureHashPropertyName
    )
        EXEC sys.sp_dropextendedproperty
            @name = @ProcedureHashPropertyName,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_DeleteCapture';

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52114, ''Owner, capture, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                DECLARE @PreviousStatus nvarchar(30);
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT
                    @CaptureId = capture.capture_id,
                    @PreviousStatus = capture.status
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                WHERE capture.owner_profile_id = @ProfileId
                  AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL
                  AND capture.row_version = @ExpectedRowVersion
                  AND
                  (
                      (capture.active = 1 AND capture.status = N''captured'')
                      OR
                      (capture.active = 0 AND capture.status = N''archived'')
                  );

                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''not_found_or_changed'' AS outcome,
                        CAST(NULL AS int) AS deleted_revision_count;
                    RETURN;
                END;

                DECLARE @RevisionCount int =
                (
                    SELECT COUNT(*)
                    FROM dbo.capture_revisions AS revision
                    WHERE revision.capture_id = @CaptureId
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"previous_status":"'', @PreviousStatus,
                    N''","revision_count":'', @RevisionCount, N''}''
                );
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint,
                    event_key uniqueidentifier,
                    occurred_at_utc datetime2(7),
                    actor_user_id int,
                    actor_user_key_snapshot nvarchar(300),
                    action_type nvarchar(200),
                    entity_type nvarchar(100),
                    entity_key uniqueidentifier,
                    outcome nvarchar(30),
                    request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.deleted'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                DELETE dbo.capture_revisions
                WHERE capture_id = @CaptureId;

                DELETE dbo.captures
                WHERE capture_id = @CaptureId
                  AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT <> 1
                    THROW 52115, ''Capture delete did not complete atomically.'', 1;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    @RevisionCount AS deleted_revision_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF OBJECT_ID(N'dbo.moment_sources', N'U') IS NOT NULL
        DROP TABLE dbo.moment_sources;
    IF OBJECT_ID(N'dbo.moment_versions', N'U') IS NOT NULL
        DROP TABLE dbo.moment_versions;
    IF OBJECT_ID(N'dbo.moments', N'U') IS NOT NULL
        DROP TABLE dbo.moments;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.schema_migrations
           WHERE migration_id = N'PS-MOMENT-001'
       )
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-MOMENT-001"}';

        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-MOMENT-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
