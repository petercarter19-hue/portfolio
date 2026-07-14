/* ============================================================
   PS-PLAT-008 ROLLBACK — People & Interests feed domain

   *** PROPOSED — NOT APPLIED. DO NOT RUN WITHOUT PETE'S APPROVAL. ***

   Removes everything PS-PLAT-008 created, children first.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.usp_ToggleFeedPostSave', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_ToggleFeedPostSave;
    IF OBJECT_ID(N'dbo.usp_RemoveFeedPostReaction', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_RemoveFeedPostReaction;
    IF OBJECT_ID(N'dbo.usp_AddFeedPostReaction', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_AddFeedPostReaction;
    IF OBJECT_ID(N'dbo.usp_AddFeedPostComment', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_AddFeedPostComment;
    IF OBJECT_ID(N'dbo.usp_GetFeedPostDetail', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetFeedPostDetail;
    IF OBJECT_ID(N'dbo.usp_CreateFeedPost', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_CreateFeedPost;
    IF OBJECT_ID(N'dbo.usp_GetPeopleInterestsFeedPage', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetPeopleInterestsFeedPage;

    IF OBJECT_ID(N'dbo.feed_post_saves', N'U') IS NOT NULL DROP TABLE dbo.feed_post_saves;
    IF OBJECT_ID(N'dbo.feed_post_reactions', N'U') IS NOT NULL DROP TABLE dbo.feed_post_reactions;
    IF OBJECT_ID(N'dbo.feed_post_comments', N'U') IS NOT NULL DROP TABLE dbo.feed_post_comments;
    IF OBJECT_ID(N'dbo.feed_posts', N'U') IS NOT NULL DROP TABLE dbo.feed_posts;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-008';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
