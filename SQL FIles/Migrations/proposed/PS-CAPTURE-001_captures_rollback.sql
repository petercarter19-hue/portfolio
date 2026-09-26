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
           FROM sys.indexes
           WHERE object_id = OBJECT_ID(N'dbo.captures')
             AND index_id > 0
             AND name NOT IN
                 (N'PK_captures', N'UQ_captures_key', N'IX_captures_owner_created')
       )
        THROW 52022, 'Rollback blocked: a later object depends on captures.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.computed_columns
           WHERE object_id = OBJECT_ID(N'dbo.captures')
       )
        THROW 52022, 'Rollback blocked: a later object depends on captures.', 1;

    -- Standalone user statistics have no sys.indexes row. A later filtered
    -- statistic can create the same table-self dependency as the owned index.
    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.stats AS statistic
           WHERE statistic.object_id = OBJECT_ID(N'dbo.captures')
             AND statistic.user_created = 1
             AND NOT EXISTS
             (
                 SELECT 1
                 FROM sys.indexes AS capture_index
                 WHERE capture_index.object_id = statistic.object_id
                   AND capture_index.index_id = statistic.stats_id
             )
       )
        THROW 52022, 'Rollback blocked: a later object depends on captures.', 1;

    -- This migration's filtered index contributes a same-table dependency.
    -- Remove only that owned index; later indexes were checked above.
    IF EXISTS (SELECT 1 FROM sys.indexes
               WHERE object_id = OBJECT_ID(N'dbo.captures')
                 AND name = N'IX_captures_owner_created')
        DROP INDEX IX_captures_owner_created ON dbo.captures;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.sql_expression_dependencies AS dependency
           WHERE dependency.referenced_id = OBJECT_ID(N'dbo.captures')
             -- The owned filtered index can reference its own table. Later
             -- indexes, computed columns, and standalone statistics were
             -- checked above. The four CHECK constraints are owned here.
             AND dependency.referencing_id <> OBJECT_ID(N'dbo.captures')
             AND NOT EXISTS
             (
                 SELECT 1
                 FROM sys.check_constraints AS own_check
                 WHERE own_check.object_id = dependency.referencing_id
                   AND own_check.parent_object_id = OBJECT_ID(N'dbo.captures')
                   AND own_check.name IN
                       (N'CK_captures_type', N'CK_captures_visibility',
                        N'CK_captures_status', N'CK_captures_deleted_state')
             )
       )
        THROW 52022, 'Rollback blocked: a later object depends on captures.', 1;

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
