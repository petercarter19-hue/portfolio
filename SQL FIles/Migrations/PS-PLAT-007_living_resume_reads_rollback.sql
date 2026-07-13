SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'dbo.usp_GetPublicLivingResumeBySlug', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetPublicLivingResumeBySlug;
    IF OBJECT_ID(N'dbo.usp_GetOwnerLivingResume', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOwnerLivingResume;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-007';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
