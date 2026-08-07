/* PS-COMMUNITY-REVIVAL-001 production-safe owner-isolation verifier.
   Every synthetic row is enclosed in one outer transaction and rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-REVIVAL-001')
        THROW 53940, 'PS-COMMUNITY-REVIVAL-001 is not registered.', 1;

    DECLARE @Definition nvarchar(max) = OBJECT_DEFINITION(
        OBJECT_ID(N'dbo.usp_ClaimPublicCommunityMediaCleanupForOwner', N'P')
    );
    IF @Definition IS NULL
       OR @Definition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @Definition NOT LIKE N'%media.uploader_user_id = @UploaderUserId%'
       OR EXISTS
          (SELECT 1 FROM sys.parameters
           WHERE object_id = OBJECT_ID(
               N'dbo.usp_ClaimPublicCommunityMediaCleanupForOwner', N'P'
           ) AND name = N'@UploaderUserId')
        THROW 53941, 'The cleanup procedure does not enforce server-key owner resolution.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:community-revival-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'community-revival-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'community-revival-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'community-revival-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectA,
        @DisplayName = N'Community revival owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'community-revival-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectB,
        @DisplayName = N'Community revival owner B';

    DECLARE @UserIdA int, @UserIdB int;
    DECLARE @UserKeyA nvarchar(300), @UserKeyB nvarchar(300);
    SELECT @UserIdA = app_user.id, @UserKeyA = app_user.user_key
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    WHERE identity_record.provider = N'community-revival-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectA;
    SELECT @UserIdB = app_user.id, @UserKeyB = app_user.user_key
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    WHERE identity_record.provider = N'community-revival-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectB;
    IF @UserIdA IS NULL OR @UserIdB IS NULL OR @UserIdA = @UserIdB
        THROW 53942, 'Synthetic cleanup owners were not created.', 1;

    DECLARE @MediaKeyA uniqueidentifier = NEWID();
    DECLARE @MediaKeyB uniqueidentifier = NEWID();
    DECLARE @Digest binary(32) = HASHBYTES('SHA2_256', N'community-revival');
    INSERT dbo.community_media
        (media_key, uploader_user_id, display_name, content_type, byte_length,
         sha256, original_blob_name, safe_blob_name, media_state, removed_at_utc)
    VALUES
        (@MediaKeyA, @UserIdA, N'owner-a.pdf', N'application/pdf', 1, @Digest,
         CONCAT(N'community/v1/aa/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.pdf'),
         CONCAT(N'community/v1/aa/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.pdf'),
         N'removed', SYSUTCDATETIME()),
        (@MediaKeyB, @UserIdB, N'owner-b.pdf', N'application/pdf', 1, @Digest,
         CONCAT(N'community/v1/bb/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.pdf'),
         CONCAT(N'community/v1/bb/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.pdf'),
         N'removed', SYSUTCDATETIME());

    DECLARE @Claims TABLE
    (
        media_key uniqueidentifier,
        cleanup_claim_token uniqueidentifier,
        original_blob_name nvarchar(220),
        safe_blob_name nvarchar(220)
    );

    INSERT @Claims
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanupForOwner
        @UserKey = @UserKeyA, @Take = 1, @MediaKey = @MediaKeyB;
    IF EXISTS (SELECT 1 FROM @Claims)
       OR EXISTS (SELECT 1 FROM dbo.community_media
                  WHERE media_key = @MediaKeyB AND cleanup_claim_token IS NOT NULL)
        THROW 53943, 'Owner A claimed owner B cleanup work.', 1;

    INSERT @Claims
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanupForOwner
        @UserKey = @UserKeyA, @Take = 1, @MediaKey = @MediaKeyA;
    IF (SELECT COUNT(*) FROM @Claims WHERE media_key = @MediaKeyA) <> 1
       OR NOT EXISTS (SELECT 1 FROM dbo.community_media
                      WHERE media_key = @MediaKeyA AND uploader_user_id = @UserIdA
                        AND cleanup_claim_token IS NOT NULL)
        THROW 53944, 'Owner A could not claim its own cleanup work.', 1;

    DELETE @Claims;
    INSERT @Claims
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanupForOwner
        @UserKey = N'forged-user-key', @Take = 1, @MediaKey = @MediaKeyB;
    THROW 53945, 'A forged owner key did not fail closed.', 1;
END TRY
BEGIN CATCH
    DECLARE @ErrorNumber int = ERROR_NUMBER();
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    IF @ErrorNumber = 53911
    BEGIN
        SELECT CAST(1 AS bit) AS verified;
        RETURN;
    END;
    THROW;
END CATCH;
