/* Guarded rollback of the additive durable composer boundary.
   Meaningful drafts and identifier-only consumption history prevent rollback. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'dbo.resume_intake_composer_state',N'U') IS NOT NULL
        AND EXISTS(SELECT 1 FROM dbo.resume_intake_composer_state WITH (UPDLOCK,HOLDLOCK)
            CROSS APPLY OPENJSON(drafts_json))
        THROW 52310,'RESUME_INTAKE_DURABLE_ROLLBACK_HAS_DRAFTS',1;
    IF OBJECT_ID(N'dbo.resume_intake_extracted_actions',N'U') IS NOT NULL
        AND EXISTS(SELECT 1 FROM dbo.resume_intake_extracted_actions WITH (UPDLOCK,HOLDLOCK))
        THROW 52311,'RESUME_INTAKE_DURABLE_ROLLBACK_HAS_HISTORY',1;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeIntakeExtractedSourceForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_ReplaceResumeIntakeDraftsForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetResumeIntakeDurableWorkspaceForOwner;
    DROP TABLE IF EXISTS dbo.resume_intake_extracted_actions;
    DROP TABLE IF EXISTS dbo.resume_intake_composer_state;
    DELETE dbo.schema_migrations WHERE migration_id=N'PS-RESUME-INTAKE-002';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
