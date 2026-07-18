/* ============================================================
   PS-CAPTURE-002 ROLLBACK - controlled private Capture lifecycle

   Guarded by default. The rollback refuses to remove correction
   history or archived state and restores the PS-CAPTURE-001 list
   procedure only when doing so cannot silently discard lifecycle data.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.capture_revisions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.capture_revisions)
        THROW 52130, 'Rollback blocked: capture_revisions contains member revisions.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.captures
           WHERE status = N'archived' OR active = 0
       )
        THROW 52131, 'Rollback blocked: captures contains archived lifecycle state.', 1;

    IF OBJECT_ID(N'dbo.capture_revisions', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.foreign_keys
           WHERE referenced_object_id = OBJECT_ID(N'dbo.capture_revisions')
       )
        THROW 52132, 'Rollback blocked: a later table depends on capture_revisions.', 1;

    IF OBJECT_ID(N'dbo.capture_revisions', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.sql_expression_dependencies
           WHERE referenced_id = OBJECT_ID(N'dbo.capture_revisions')
             AND referencing_id NOT IN
             (
                 SELECT object_id
                 FROM sys.objects
                 WHERE parent_object_id = OBJECT_ID(N'dbo.capture_revisions')
             )
             AND referencing_id NOT IN
             (
                 OBJECT_ID(N'dbo.usp_ListCapturesForOwner'),
                 OBJECT_ID(N'dbo.usp_GetCaptureForOwner'),
                 OBJECT_ID(N'dbo.usp_CorrectCapture'),
                 OBJECT_ID(N'dbo.usp_DeleteCapture'),
                 OBJECT_ID(N'dbo.usp_ExportCaptureForOwner')
             )
       )
        THROW 52133, 'Rollback blocked: a later programmable object depends on capture_revisions.', 1;

    IF OBJECT_ID(N'dbo.usp_GetCaptureForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetCaptureForOwner;
    IF OBJECT_ID(N'dbo.usp_CorrectCapture', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CorrectCapture;
    IF OBJECT_ID(N'dbo.usp_ArchiveCapture', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ArchiveCapture;
    IF OBJECT_ID(N'dbo.usp_RestoreCapture', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_RestoreCapture;
    IF OBJECT_ID(N'dbo.usp_DeleteCapture', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_DeleteCapture;
    IF OBJECT_ID(N'dbo.usp_ExportCaptureForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ExportCaptureForOwner;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListCapturesForOwner
            @UserKey nvarchar(300),
            @Take int = 50
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL
                THROW 52008, ''Authenticated user key is required.'', 1;
            IF @Take IS NULL SET @Take = 50;
            IF @Take < 1 SET @Take = 1;
            IF @Take > 100 SET @Take = 100;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52009, ''Authenticated owner profile not found.'', 1;

            SELECT TOP (@Take)
                capture.capture_key,
                capture.capture_type,
                capture.body,
                capture.visibility,
                capture.status,
                capture.created_at_utc,
                capture.updated_at_utc
            FROM dbo.captures AS capture
            WHERE capture.owner_profile_id = @ProfileId
              AND capture.active = 1
              AND capture.deleted_at_utc IS NULL
            ORDER BY capture.created_at_utc DESC, capture.capture_id DESC;
        END;
    ');

    IF OBJECT_ID(N'dbo.capture_revisions', N'U') IS NOT NULL
        DROP TABLE dbo.capture_revisions;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.schema_migrations
           WHERE migration_id = N'PS-CAPTURE-002'
       )
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-CAPTURE-002"}';

        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-002';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
