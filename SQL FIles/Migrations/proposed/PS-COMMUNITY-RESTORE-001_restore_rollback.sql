/* PS-COMMUNITY-RESTORE-001 rollback. Removes the restore path only; no
   content, deletion record, or retention state is touched. */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.usp_RestorePublicCommunityPost', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_RestorePublicCommunityPost;
    IF OBJECT_ID(N'dbo.usp_RestorePublicCommunityContribution', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_RestorePublicCommunityContribution;
    IF OBJECT_ID(N'dbo.usp_ListRestorableCommunityForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListRestorableCommunityForOwner;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-RESTORE-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
