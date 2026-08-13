/* PS-PROFILE-002 destructive rollback candidate. Exact release authority is required. */
SET NOCOUNT ON; SET XACT_ABORT ON;
BEGIN TRY
  BEGIN TRANSACTION;
  IF EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-PROFILE-002')
  BEGIN
    DROP PROCEDURE IF EXISTS dbo.usp_GetCurrentProfileEligibleCommunityRevisionForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetProfileEligibleCommunityPostForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitProfilePublicationForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_SaveProfileDraftForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetProfilePublicationCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetCurrentProfilePublicationForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetProfileDraftForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetProfileOwnerBySlug;
    IF OBJECT_ID(N'dbo.profile_publications',N'U') IS NOT NULL
      ALTER TABLE dbo.profile_publications DROP CONSTRAINT FK_profile_publications_current_revision;
    DROP TABLE IF EXISTS dbo.profile_publication_commands;
    DROP TABLE IF EXISTS dbo.profile_publication_revision_items;
    DROP TABLE IF EXISTS dbo.profile_publication_revisions;
    DROP TABLE IF EXISTS dbo.profile_draft_placements;
    DROP TABLE IF EXISTS dbo.profile_drafts;
    DROP TABLE IF EXISTS dbo.profile_projection_versions;
    DROP TABLE IF EXISTS dbo.profile_content_versions;
    DROP TABLE IF EXISTS dbo.profile_content_items;
    DROP TABLE IF EXISTS dbo.profile_slug_history;
    DROP TABLE IF EXISTS dbo.profile_publications;
    DELETE dbo.schema_migrations WHERE migration_id=N'PS-PROFILE-002';
  END;
  COMMIT;
END TRY
BEGIN CATCH
  IF XACT_STATE()<>0 ROLLBACK;
  THROW;
END CATCH;
