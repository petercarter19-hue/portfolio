/* ============================================================
   PS-SETTINGS-EXPORT-007 ROLLBACK - account export Voice/Photo media and
   transcript reader

   This migration creates no table, trigger, or index -- only five
   read-only procedures over existing, already-applied tables (matching
   the data-safety reasoning already recorded for every prior package in
   this program: nothing here ever held a row, and no later object can
   depend on a plain SELECT-only procedure the way it can depend on a
   table or another migration's procedure). Rollback is a straight
   guarded DROP of every procedure this migration created, followed by
   removing this migration's registry ledger row.

   THROW range: 58812 (continuing inside this package's reserved
   58800-58899 block; the forward file uses 58800-58811).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58812, 'PS-SETTINGS-EXPORT-007 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportVoiceMediaSourceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportVoiceMediaSourceForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureMediaSourceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCaptureMediaSourceForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureMediaLinkForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCaptureMediaLinkForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-007';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
