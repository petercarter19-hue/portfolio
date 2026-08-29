/* ============================================================
   PS-SETTINGS-EXPORT-003 ROLLBACK - account export core readers

   This migration creates no table, trigger, or index -- only ten
   read-only procedures over existing tables (matching the data-safety
   reasoning already recorded for PS-SETTINGS-EXPORT-001 and the paused
   DOMAIN-READERS-001 package's own rollback: nothing here ever held a
   row, and no later object can depend on a plain SELECT-only
   procedure the way it can depend on a table or another migration's
   procedure). Rollback is a straight guarded DROP of every procedure
   this migration created, followed by removing this migration's
   registry ledger row.

   THROW range: 58013 (inside this migration's reserved 58000-58099
   block; the forward file uses 58000-58012).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58013, 'PS-SETTINGS-EXPORT-003 rollback requires the migration ledger.', 1;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportAccountForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportAccountForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportProfileForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportProfileForOwner;

    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerChapterForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerChapterForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerExperienceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerExperienceForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerEducationForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerEducationForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerCredentialForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerCredentialForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerProjectForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerProjectForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerAchievementForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerAchievementForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerSkillForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerSkillForOwner;
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerTimelineEventForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ReadAccountExportCareerTimelineEventForOwner;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-003';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
