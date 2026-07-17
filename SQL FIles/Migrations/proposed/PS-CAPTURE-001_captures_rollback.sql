/* ============================================================
   PS-CAPTURE-001 ROLLBACK - private Universal Capture text intake

   Data-safe by default: this rollback refuses to remove member data
   or objects that later migrations depend on. Export/review retention
   before deliberately clearing capture rows for a destructive rollback.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.captures)
        THROW 52020, 'Rollback blocked: captures contains member data.', 1;

    IF OBJECT_ID(N'dbo.usp_CreateCapture', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CreateCapture;
    IF OBJECT_ID(N'dbo.usp_ListCapturesForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListCapturesForOwner;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.foreign_keys
           WHERE referenced_object_id = OBJECT_ID(N'dbo.captures')
       )
        THROW 52021, 'Rollback blocked: a later table depends on captures.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.sql_expression_dependencies
           WHERE referenced_id = OBJECT_ID(N'dbo.captures')
       )
        THROW 52022, 'Rollback blocked: a later programmable object depends on captures.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
        DROP TABLE dbo.captures;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
