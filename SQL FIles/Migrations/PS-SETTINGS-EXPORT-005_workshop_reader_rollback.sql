/* ============================================================
   PS-SETTINGS-EXPORT-005 ROLLBACK - account export Workshop / My
   Knowledge readers

   This migration creates no table, trigger, or index -- only two
   read-only procedures over existing, already-applied tables (matching
   the data-safety reasoning already recorded for PS-SETTINGS-EXPORT-001,
   PS-SETTINGS-EXPORT-003, and PS-SETTINGS-EXPORT-004: nothing here ever
   held a row, and no later object can depend on a plain SELECT-only
   procedure the way it can depend on a table or another migration's
   procedure). Rollback is a straight guarded DROP of every procedure
   this migration created, followed by removing this migration's
   registry ledger row.

   THROW range: 58408 (continuing inside this package's reserved
   58400-58499 block; the forward file uses 58400-58407).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58408, 'PS-SETTINGS-EXPORT-005 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportKnowledgeItemForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-005';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
