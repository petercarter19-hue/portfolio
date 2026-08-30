/* ============================================================
   PS-SETTINGS-EXPORT-008 ROLLBACK - account export preferences and
   consent readers

   This migration creates no table, trigger, or index -- only three
   read-only procedures over existing, already-applied tables (the same
   data-safety reasoning every prior package in this program has
   recorded: nothing here ever held a row, and no later object can
   depend on a plain SELECT-only procedure the way it can depend on a
   table or another migration's procedure). Rollback is a straight
   guarded DROP of every procedure this migration created, followed by
   removing this migration's registry ledger row.

   THROW range: 59008 (continuing inside this package's reserved
   59000-59099 block; the forward file uses 59000-59007).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 59008, 'PS-SETTINGS-EXPORT-008 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportConnectionPreferenceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportConnectionPreferenceForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportNotificationPreferenceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportNotificationPreferenceForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportUserConsentForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportUserConsentForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-008';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
