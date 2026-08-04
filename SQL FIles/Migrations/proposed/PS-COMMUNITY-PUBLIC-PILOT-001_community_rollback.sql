/* Refuse destructive rollback after any Community member data exists. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'dbo.schema_migrations',N'U') IS NULL
        THROW 52489,'Community rollback refused: the migration ledger is missing.',1;

    DECLARE @CommunityTables TABLE(object_name sysname NOT NULL PRIMARY KEY);
    INSERT @CommunityTables(object_name) VALUES
        (N'community_posts'),(N'community_post_revisions'),
        (N'community_contributions'),(N'community_contribution_revisions'),
        (N'community_responses'),(N'community_saves'),
        (N'community_contribution_saves'),(N'community_media'),
        (N'community_audit_events'),(N'community_outbox');
    DECLARE @CommunityProcedures TABLE(object_name sysname NOT NULL PRIMARY KEY);
    INSERT @CommunityProcedures(object_name) VALUES
        (N'usp_ListPublicCommunityFeed'),(N'usp_ListPublicCommunityShelf'),
        (N'usp_GetPublicCommunityPost'),
        (N'usp_GetPublicCommunityContribution'),
        (N'usp_SearchPublicCommunity'),(N'usp_PublishPublicCommunityPost'),
        (N'usp_EditPublicCommunityPost'),(N'usp_DeletePublicCommunityPost'),
        (N'usp_AddPublicCommunityContribution'),
        (N'usp_EditPublicCommunityContribution'),
        (N'usp_DeletePublicCommunityContribution'),
        (N'usp_SetPublicCommunityResponse'),
        (N'usp_RemovePublicCommunityResponse'),(N'usp_SetPublicCommunitySave'),
        (N'usp_SetPublicCommunityContributionSave'),
        (N'usp_ReservePublicCommunityMedia'),
        (N'usp_MarkPublicCommunityMediaUploaded'),
        (N'usp_GetPublicCommunityMediaForOwner'),
        (N'usp_CompletePublicCommunityMedia'),
        (N'usp_CompensatePublicCommunityMediaCompletion'),
        (N'usp_RejectPublicCommunityMedia'),
        (N'usp_ClaimPublicCommunityMediaCleanup'),
        (N'usp_CompletePublicCommunityMediaCleanup'),
        (N'usp_GetPublicCommunityMedia'),(N'usp_DeletePublicCommunityMedia');

    DECLARE @CommunityAppliedAtUtc datetime2(7)=
        (SELECT applied_at_utc FROM dbo.schema_migrations WITH(UPDLOCK,HOLDLOCK) WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001');
    IF @CommunityAppliedAtUtc IS NULL
    BEGIN
        IF EXISTS(SELECT 1 FROM @CommunityTables AS expected JOIN sys.tables AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name)
           OR EXISTS(SELECT 1 FROM @CommunityProcedures AS expected JOIN sys.procedures AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name)
            THROW 52488,'Community rollback refused: artifacts exist without the migration ledger record.',1;
        COMMIT TRANSACTION;
        RETURN;
    END;
    IF EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc>@CommunityAppliedAtUtc)
        THROW 52487,'Community rollback refused: a later migration is present.',1;
    IF EXISTS
    (
        SELECT 1 FROM @CommunityTables AS expected
        LEFT JOIN sys.tables AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name
        WHERE actual.object_id IS NULL
    )
        THROW 52486,'Community rollback refused: an owned table is missing.',1;
    IF OBJECT_ID(N'dbo.community_posts',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.community_posts)
        THROW 52490,'Community contains posts. Disable the feature flag; do not destroy member content.',1;
    IF OBJECT_ID(N'dbo.community_contributions',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.community_contributions)
        THROW 52491,'Community contains contributions. Disable the feature flag; do not destroy member content.',1;
    IF OBJECT_ID(N'dbo.community_media',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.community_media)
        THROW 52492,'Community contains media reservations. Disable the feature flag; do not destroy member content.',1;
    IF OBJECT_ID(N'dbo.community_audit_events',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.community_audit_events)
        THROW 52496,'Community contains audit evidence. Disable the feature flag; do not destroy it.',1;
    IF OBJECT_ID(N'dbo.community_outbox',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.community_outbox)
        THROW 52497,'Community contains delivery evidence. Disable the feature flag; do not destroy it.',1;

    DECLARE @CommunityProcedureHashProperty sysname=N'PS_COMMUNITY_PUBLIC_PILOT_001_DEFINITION_HASH';
    IF EXISTS
    (
        SELECT 1
        FROM @CommunityProcedures AS expected
        LEFT JOIN sys.procedures AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name
        LEFT JOIN sys.extended_properties AS property ON property.class=1 AND property.major_id=actual.object_id AND property.minor_id=0 AND property.name=@CommunityProcedureHashProperty
        WHERE actual.object_id IS NULL OR property.major_id IS NULL
           OR OBJECT_DEFINITION(actual.object_id) IS NULL
           OR CONVERT(nvarchar(64),property.value)<>CONVERT(nvarchar(64),HASHBYTES('SHA2_256',OBJECT_DEFINITION(actual.object_id)),2)
    )
        THROW 52493,'Community rollback refused: a protected procedure changed.',1;

    DECLARE @CommunityTableIds TABLE(object_id int NOT NULL PRIMARY KEY);
    INSERT @CommunityTableIds(object_id)
    SELECT actual.object_id FROM sys.tables AS actual JOIN @CommunityTables AS expected ON expected.object_name=actual.name WHERE actual.schema_id=SCHEMA_ID(N'dbo');
    DECLARE @CommunityObjectIds TABLE(object_id int NOT NULL PRIMARY KEY);
    INSERT @CommunityObjectIds(object_id)
    SELECT object_id FROM @CommunityTableIds;
    INSERT @CommunityObjectIds(object_id)
    SELECT actual.object_id
    FROM sys.procedures AS actual
    JOIN @CommunityProcedures AS expected ON expected.object_name=actual.name
    WHERE actual.schema_id=SCHEMA_ID(N'dbo');
    IF EXISTS
    (
        SELECT 1 FROM sys.foreign_keys
        WHERE referenced_object_id IN(SELECT object_id FROM @CommunityTableIds)
          AND parent_object_id NOT IN(SELECT object_id FROM @CommunityTableIds)
    )
        THROW 52494,'Community rollback refused: a later table depends on Community objects.',1;
    IF EXISTS
    (
        SELECT 1 FROM sys.sql_expression_dependencies AS dependency
        WHERE dependency.referenced_id IN(SELECT object_id FROM @CommunityObjectIds)
          AND dependency.referencing_id NOT IN(SELECT object_id FROM @CommunityObjectIds)
          AND dependency.referencing_id NOT IN(SELECT object_id FROM sys.objects WHERE parent_object_id IN(SELECT object_id FROM @CommunityTableIds))
    )
        THROW 52495,'Community rollback refused: a later programmable object depends on Community objects.',1;

    DROP PROCEDURE IF EXISTS dbo.usp_DeletePublicCommunityMedia;
    DROP PROCEDURE IF EXISTS dbo.usp_GetPublicCommunityMedia;
    DROP PROCEDURE IF EXISTS dbo.usp_CompletePublicCommunityMediaCleanup;
    DROP PROCEDURE IF EXISTS dbo.usp_ClaimPublicCommunityMediaCleanup;
    DROP PROCEDURE IF EXISTS dbo.usp_RejectPublicCommunityMedia;
    DROP PROCEDURE IF EXISTS dbo.usp_CompensatePublicCommunityMediaCompletion;
    DROP PROCEDURE IF EXISTS dbo.usp_CompletePublicCommunityMedia;
    DROP PROCEDURE IF EXISTS dbo.usp_GetPublicCommunityMediaForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_MarkPublicCommunityMediaUploaded;
    DROP PROCEDURE IF EXISTS dbo.usp_ReservePublicCommunityMedia;
    DROP PROCEDURE IF EXISTS dbo.usp_SetPublicCommunitySave;
    DROP PROCEDURE IF EXISTS dbo.usp_SetPublicCommunityContributionSave;
    DROP PROCEDURE IF EXISTS dbo.usp_RemovePublicCommunityResponse;
    DROP PROCEDURE IF EXISTS dbo.usp_SetPublicCommunityResponse;
    DROP PROCEDURE IF EXISTS dbo.usp_DeletePublicCommunityContribution;
    DROP PROCEDURE IF EXISTS dbo.usp_EditPublicCommunityContribution;
    DROP PROCEDURE IF EXISTS dbo.usp_AddPublicCommunityContribution;
    DROP PROCEDURE IF EXISTS dbo.usp_DeletePublicCommunityPost;
    DROP PROCEDURE IF EXISTS dbo.usp_EditPublicCommunityPost;
    DROP PROCEDURE IF EXISTS dbo.usp_PublishPublicCommunityPost;
    DROP PROCEDURE IF EXISTS dbo.usp_SearchPublicCommunity;
    DROP PROCEDURE IF EXISTS dbo.usp_GetPublicCommunityContribution;
    DROP PROCEDURE IF EXISTS dbo.usp_GetPublicCommunityPost;
    DROP PROCEDURE IF EXISTS dbo.usp_ListPublicCommunityShelf;
    DROP PROCEDURE IF EXISTS dbo.usp_ListPublicCommunityFeed;
    DROP TABLE IF EXISTS dbo.community_outbox;
    DROP TABLE IF EXISTS dbo.community_audit_events;
    DROP TABLE IF EXISTS dbo.community_media;
    DROP TABLE IF EXISTS dbo.community_contribution_saves;
    DROP TABLE IF EXISTS dbo.community_saves;
    DROP TABLE IF EXISTS dbo.community_responses;
    DROP TABLE IF EXISTS dbo.community_contribution_revisions;
    DROP TABLE IF EXISTS dbo.community_contributions;
    DROP TABLE IF EXISTS dbo.community_post_revisions;
    DROP TABLE IF EXISTS dbo.community_posts;
    DELETE dbo.schema_migrations WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
