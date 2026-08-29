/* ============================================================
   PS-SETTINGS-EXPORT-004 ROLLBACK - account export capture/moment
   readers

   This migration creates no table, trigger, or index -- only six
   read-only procedures over existing, already-applied tables (matching
   the data-safety reasoning already recorded for PS-SETTINGS-EXPORT-001
   and PS-SETTINGS-EXPORT-003: nothing here ever held a row, and no
   later object can depend on a plain SELECT-only procedure the way it
   can depend on a table or another migration's procedure). Rollback is
   a straight guarded DROP of every procedure this migration created,
   followed by removing this migration's registry ledger row.

   THROW range: 58214 (continuing inside this package's reserved
   58200-58299 block; the forward file uses 58200-58213).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58214, 'PS-SETTINGS-EXPORT-004 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCaptureForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureRevisionForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCaptureRevisionForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportMomentForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportMomentForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportMomentVersionForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportMomentVersionForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportMomentSourceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportMomentSourceForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportMomentPlacementForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportMomentPlacementForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-004';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
