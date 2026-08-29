/* ============================================================
   PS-SETTINGS-EXPORT-006 ROLLBACK - account export Opportunity Slate
   reader

   This migration creates no table, trigger, or index -- only four
   read-only procedures over existing, already-applied tables (matching
   the data-safety reasoning already recorded for every prior package in
   this program: nothing here ever held a row, and no later object can
   depend on a plain SELECT-only procedure the way it can depend on a
   table or another migration's procedure). Rollback is a straight
   guarded DROP of every procedure this migration created, followed by
   removing this migration's registry ledger row.

   THROW range: 58611 (continuing inside this package's reserved
   58600-58699 block; the forward file uses 58600-58610).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58611, 'PS-SETTINGS-EXPORT-006 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySlateForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportOpportunitySlateForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySavedResultForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportOpportunitySavedResultForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-006';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
