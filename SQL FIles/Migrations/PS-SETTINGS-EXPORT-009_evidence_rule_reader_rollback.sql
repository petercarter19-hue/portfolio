/* ============================================================
   PS-SETTINGS-EXPORT-009 ROLLBACK - account export evidence-rule
   reader (career_skill_links)

   This migration creates no table, trigger, or index -- only one
   read-only procedure over an existing, already-applied table (the
   same data-safety reasoning every prior package in this program has
   recorded: nothing here ever held a row, and no later object can
   depend on a plain SELECT-only procedure the way it can depend on a
   table or another migration's procedure). Rollback is a straight
   guarded DROP of the procedure this migration created, followed by
   removing this migration's registry ledger row.

   THROW range: 59207 (continuing inside this package's reserved
   59200-59299 block; the forward file uses 59200-59206).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 59207, 'PS-SETTINGS-EXPORT-009 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerSkillLinkForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerSkillLinkForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-009';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
