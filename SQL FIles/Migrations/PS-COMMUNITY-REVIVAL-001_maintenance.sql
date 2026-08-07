/* ============================================================
   PS-COMMUNITY-REVIVAL-001 - additive owner-scoped media cleanup

   Production already carries PS-COMMUNITY-PUBLIC-PILOT-001,
   PS-COMMUNITY-RETENTION-001, and PS-COMMUNITY-RESTORE-001. Those IDs are
   immutable and are never replayed. This migration adds one new procedure
   for targeted cleanup initiated by an authenticated owner. The existing
   unscoped procedure remains the janitor-only path.

   Rollback: PS-COMMUNITY-REVIVAL-001_maintenance_rollback.sql
   Verification: ../Verification/PS-COMMUNITY-REVIVAL-001_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53900, 'PS-COMMUNITY-REVIVAL-001 requires the migration ledger.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-COMMUNITY-PUBLIC-PILOT-001')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                      WHERE migration_id = N'PS-COMMUNITY-RETENTION-001')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                      WHERE migration_id = N'PS-COMMUNITY-RESTORE-001')
        THROW 53901, 'The complete Community production baseline is required.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.community_media', N'U') IS NULL
       OR OBJECT_ID(N'dbo.community_posts', N'U') IS NULL
       OR OBJECT_ID(N'dbo.community_contributions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_ClaimPublicCommunityMediaCleanup', N'P') IS NULL
        THROW 53902, 'The Community media-cleanup baseline is incomplete.', 1;

    IF COL_LENGTH(N'dbo.community_media', N'uploader_user_id') IS NULL
       OR COL_LENGTH(N'dbo.community_media', N'cleanup_claim_token') IS NULL
       OR COL_LENGTH(N'dbo.community_media', N'cleanup_claimed_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.community_media', N'blob_cleanup_completed_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.community_posts', N'legal_hold_reason') IS NULL
       OR COL_LENGTH(N'dbo.community_contributions', N'legal_hold_reason') IS NULL
        THROW 53903, 'The Community cleanup columns are incompatible.', 1;

    /* The applied baseline never accepted an uploader parameter. Finding
       F14 was incorrectly appended to that already-ledgered file. Refuse a
       database where that ungoverned signature is present rather than hiding
       a second source of truth behind this additive procedure. */
    IF EXISTS
    (
        SELECT 1
        FROM sys.parameters
        WHERE object_id = OBJECT_ID(N'dbo.usp_ClaimPublicCommunityMediaCleanup', N'P')
          AND name = N'@UploaderUserKey'
    )
        THROW 53904, 'The immutable Community cleanup baseline has drifted.', 1;

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanupForOwner
        @UserKey nvarchar(300),
        @Take int = 8,
        @MediaKey uniqueidentifier = NULL,
        @PostKey uniqueidentifier = NULL,
        @ContributionKey uniqueidentifier = NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        SET XACT_ABORT ON;

        SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
        IF @UserKey IS NULL OR @Take IS NULL OR @Take NOT BETWEEN 1 AND 20
           OR (CASE WHEN @MediaKey IS NULL THEN 0 ELSE 1 END
             + CASE WHEN @PostKey IS NULL THEN 0 ELSE 1 END
             + CASE WHEN @ContributionKey IS NULL THEN 0 ELSE 1 END) <> 1
            THROW 53910, ''Owner cleanup requires one bounded target.'', 1;

        DECLARE @UploaderUserId int =
        (
            SELECT id
            FROM dbo.app_users
            WHERE user_key = @UserKey
              AND active = 1
              AND account_status = N''active''
        );
        IF @UploaderUserId IS NULL
            THROW 53911, ''Cleanup owner is unavailable.'', 1;

        DECLARE @Now datetime2(7) = SYSUTCDATETIME();
        DECLARE @ClaimToken uniqueidentifier = NEWID();
        DECLARE @StartedTransaction bit = 0;
        DECLARE @Candidates TABLE
            (community_media_id bigint NOT NULL PRIMARY KEY);

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction = 1;
        END
        ELSE SAVE TRANSACTION CommunityOwnerMediaClaim;

        INSERT @Candidates (community_media_id)
        SELECT TOP (@Take) media.community_media_id
        FROM dbo.community_media AS media WITH (UPDLOCK, READPAST, READCOMMITTEDLOCK)
        LEFT JOIN dbo.community_posts AS direct_post
          ON direct_post.community_post_id = media.community_post_id
        LEFT JOIN dbo.community_contributions AS contribution
          ON contribution.community_contribution_id = media.community_contribution_id
        LEFT JOIN dbo.community_posts AS contribution_post
          ON contribution_post.community_post_id = contribution.community_post_id
        WHERE media.uploader_user_id = @UploaderUserId
          AND media.blob_cleanup_completed_at_utc IS NULL
          AND (@MediaKey IS NULL OR media.media_key = @MediaKey)
          AND (@PostKey IS NULL OR direct_post.post_key = @PostKey
               OR contribution_post.post_key = @PostKey)
          AND (@ContributionKey IS NULL
               OR contribution.contribution_key = @ContributionKey)
          AND (media.cleanup_claim_token IS NULL
               OR media.cleanup_claimed_at_utc < DATEADD(minute, -10, @Now))
          AND direct_post.legal_hold_reason IS NULL
          AND contribution.legal_hold_reason IS NULL
          AND contribution_post.legal_hold_reason IS NULL
          AND
          (
              media.media_state IN (N''rejected'', N''failed'', N''removed'')
              OR (media.community_post_id IS NULL
                  AND media.community_contribution_id IS NULL
                  AND media.expires_at_utc <= @Now)
              OR (direct_post.publication_state = N''deleted''
                  OR direct_post.moderation_state = N''removed'')
              OR (contribution.lifecycle_state = N''deleted''
                  OR contribution.moderation_state = N''removed''
                  OR contribution_post.publication_state = N''deleted''
                  OR contribution_post.moderation_state = N''removed'')
          )
        ORDER BY
          CASE WHEN media.media_state IN (N''rejected'', N''failed'', N''removed'')
               THEN 0 ELSE 1 END,
          media.expires_at_utc,
          media.community_media_id;

        UPDATE media
        SET cleanup_claim_token = @ClaimToken,
            cleanup_claimed_at_utc = @Now
        FROM dbo.community_media AS media
        JOIN @Candidates AS candidate
          ON candidate.community_media_id = media.community_media_id;

        IF @StartedTransaction = 1 COMMIT TRANSACTION;

        SELECT media.media_key,
               @ClaimToken AS cleanup_claim_token,
               media.original_blob_name,
               media.safe_blob_name
        FROM dbo.community_media AS media
        JOIN @Candidates AS candidate
          ON candidate.community_media_id = media.community_media_id
        WHERE media.cleanup_claim_token = @ClaimToken
        ORDER BY media.community_media_id;
    END');

    DECLARE @ProcedureName sysname = N'usp_ClaimPublicCommunityMediaCleanupForOwner';
    DECLARE @HashProperty sysname = N'PS_COMMUNITY_REVIVAL_001_DEFINITION_HASH';
    DECLARE @ProcedureHash nvarchar(64) = CONVERT(
        nvarchar(64),
        HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @ProcedureName, N'P'))),
        2
    );
    IF @ProcedureHash IS NULL
        THROW 53905, 'The owner-scoped cleanup procedure was not created.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.extended_properties
        WHERE class = 1
          AND major_id = OBJECT_ID(N'dbo.' + @ProcedureName, N'P')
          AND minor_id = 0
          AND name = @HashProperty
    )
        EXEC sys.sp_updateextendedproperty
            @name = @HashProperty, @value = @ProcedureHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = @ProcedureName;
    ELSE
        EXEC sys.sp_addextendedproperty
            @name = @HashProperty, @value = @ProcedureHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = @ProcedureName;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-REVIVAL-001')
    BEGIN
        INSERT dbo.schema_migrations
            (migration_id, description, application_version)
        VALUES
            (N'PS-COMMUNITY-REVIVAL-001',
             N'Additive owner-scoped targeted Community media cleanup; the existing unscoped procedure remains janitor-only.',
             N'PeerSlate Bible and Roadmap v3.0');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-COMMUNITY-REVIVAL-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
