/* PS-CAPTURE-MEDIA-001 production-safe database verification.
   Two synthetic owners exercise Photo source states, scan/derivative gates,
   idempotent private confirmation, media authority, deletion, and downstream
   isolation. No real media is used and the outer transaction rolls back all
   synthetic rows. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-MEDIA-001')
        THROW 52570, 'PS-CAPTURE-MEDIA-001 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @OpaqueA nvarchar(32) = REPLACE(@Suffix, N'-', N'');
    DECLARE @OpaqueB nvarchar(32) = REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N'');
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:photo-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'photo-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'photo-b-', @Suffix);
    DECLARE @ApprovedBody nvarchar(300) = CONCAT(N'private-photo-note-', @Suffix);
    DECLARE @OriginalA nvarchar(160) = CONCAT(N'photo/v1/aa/', @OpaqueA, N'.jpg');
    DECLARE @DerivativeA nvarchar(160) = CONCAT(N'photo/v1/aa/', @OpaqueA, N'-preview.jpg');
    DECLARE @OriginalB nvarchar(160) = CONCAT(N'photo/v1/bb/', @OpaqueB, N'.png');
    DECLARE @DerivativeB nvarchar(160) = CONCAT(N'photo/v1/bb/', @OpaqueB, N'-preview.png');
    DECLARE @OriginalDigest binary(32) = HASHBYTES('SHA2_256', CONVERT(varbinary(max), @Suffix));
    DECLARE @DerivativeDigest binary(32) = HASHBYTES('SHA2_256', CONVERT(varbinary(max), CONCAT(N'preview-', @Suffix)));

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'photo-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'Photo Owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'photo-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'Photo Owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'photo-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectA;
    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'photo-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectB;
    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @ProfileIdA = @ProfileIdB
        THROW 52571, 'Synthetic Photo owners were not provisioned.', 1;

    DECLARE @MomentCount int =
        (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @PlacementCount int =
        (SELECT COUNT(*) FROM dbo.moment_placements WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @EntityCount int =
        (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @AiProposalCount int =
        (SELECT COUNT(*) FROM dbo.ai_proposals WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));

    EXEC dbo.usp_CreatePhotoSource
        @UserKey = @UserKeyA, @OriginalBlobName = @OriginalA,
        @DerivativeBlobName = @DerivativeA, @OriginalContentType = N'image/jpeg',
        @OriginalByteLength = 4096, @OriginalSha256Digest = @OriginalDigest;
    DECLARE @SourceKeyA uniqueidentifier;
    DECLARE @VersionA binary(8);
    SELECT @SourceKeyA = source_key, @VersionA = row_version
    FROM dbo.capture_media_sources
    WHERE owner_profile_id = @ProfileIdA AND original_blob_name = @OriginalA;
    IF @SourceKeyA IS NULL OR NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA AND state = N'uploading')
        THROW 52572, 'Owner A Photo source was not created in uploading state.', 1;

    /* Cross-owner upload completion denial. */
    EXEC dbo.usp_MarkPhotoUploaded
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @OriginalBlobEtag = N'"etag-a"';
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA AND state = N'uploading')
        THROW 52573, 'Cross-owner upload completion changed a foreign source.', 1;

    EXEC dbo.usp_MarkPhotoUploaded
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @OriginalBlobEtag = N'"etag-a"';
    SELECT @VersionA = row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA
        AND state = N'scanning' AND scan_result = N'unknown')
        THROW 52574, 'Photo upload did not enter fail-closed scanning.', 1;

    /* Cross-owner Defender reconciliation denial. */
    EXEC dbo.usp_RecordPhotoScanResult
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @ScanResult = N'clean';
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA AND state = N'scanning')
        THROW 52575, 'Cross-owner scan reconciliation changed a foreign source.', 1;

    EXEC dbo.usp_RecordPhotoScanResult
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @ScanResult = N'clean';
    SELECT @VersionA = row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA
        AND state = N'processing' AND scan_result = N'clean')
        THROW 52576, 'Clean scan did not enter bounded derivative processing.', 1;

    /* Cross-owner derivative completion denial. */
    EXEC dbo.usp_CompletePhotoProcessing
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @DerivativeContentType = N'image/jpeg',
        @DerivativeByteLength = 2048, @DerivativeSha256Digest = @DerivativeDigest,
        @DerivativeBlobEtag = N'"preview-etag-a"', @PixelWidth = 1200, @PixelHeight = 800;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA AND state = N'processing')
        THROW 52577, 'Cross-owner derivative completion changed a foreign source.', 1;

    EXEC dbo.usp_CompletePhotoProcessing
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @DerivativeContentType = N'image/jpeg',
        @DerivativeByteLength = 2048, @DerivativeSha256Digest = @DerivativeDigest,
        @DerivativeBlobEtag = N'"preview-etag-a"', @PixelWidth = 1200, @PixelHeight = 800;
    SELECT @VersionA = row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA
        AND state = N'needs_review' AND derivative_sha256_digest = @DerivativeDigest)
        THROW 52578, 'Safe derivative did not enter needs_review.', 1;

    DECLARE @ForeignMedia TABLE
    (
        source_key uniqueidentifier, blob_name nvarchar(160), content_type nvarchar(40),
        byte_length bigint, sha256_digest binary(32)
    );
    INSERT @ForeignMedia EXEC dbo.usp_GetPhotoMediaForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA, @MediaKind = N'preview';
    IF EXISTS (SELECT 1 FROM @ForeignMedia)
        THROW 52579, 'Cross-owner media retrieval disclosed a private derivative.', 1;

    /* Cross-owner confirmation denial and explicit private confirmation. */
    EXEC dbo.usp_ConfirmPhotoCapture
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @ApprovedBody = @ApprovedBody;
    IF EXISTS
       (SELECT 1 FROM dbo.capture_media_links WHERE source_id =
        (SELECT source_id FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA))
        THROW 52580, 'Cross-owner confirmation created a foreign Capture.', 1;
    EXEC dbo.usp_ConfirmPhotoCapture
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @ApprovedBody = @ApprovedBody;

    DECLARE @CaptureIdA bigint;
    DECLARE @CaptureKeyA uniqueidentifier;
    DECLARE @CaptureVersion binary(8);
    SELECT @CaptureIdA = capture.capture_id, @CaptureKeyA = capture.capture_key,
           @CaptureVersion = capture.row_version
    FROM dbo.capture_media_links AS link
    JOIN dbo.captures AS capture ON capture.capture_id = link.capture_id
    WHERE link.source_id =
       (SELECT source_id FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA);
    IF @CaptureIdA IS NULL OR NOT EXISTS
       (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA
        AND owner_profile_id = @ProfileIdA AND capture_type = N'photo'
        AND visibility = N'private' AND body = @ApprovedBody)
        THROW 52581, 'Photo confirmation did not create exactly one private Capture.', 1;

    /* Idempotent confirmation must not duplicate the Capture. */
    EXEC dbo.usp_ConfirmPhotoCapture
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @VersionA, @ApprovedBody = @ApprovedBody;
    IF (SELECT COUNT(*) FROM dbo.capture_media_links WHERE source_id =
        (SELECT source_id FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA)) <> 1
        THROW 52582, 'Photo confirmation was not idempotent.', 1;

    /* A malicious result never creates a derivative or Capture. */
    EXEC dbo.usp_CreatePhotoSource
        @UserKey = @UserKeyA, @OriginalBlobName = @OriginalB,
        @DerivativeBlobName = @DerivativeB, @OriginalContentType = N'image/png',
        @OriginalByteLength = 1024, @OriginalSha256Digest = @OriginalDigest;
    DECLARE @SourceKeyB uniqueidentifier;
    DECLARE @VersionB binary(8);
    SELECT @SourceKeyB = source_key, @VersionB = row_version
    FROM dbo.capture_media_sources
    WHERE owner_profile_id = @ProfileIdA AND original_blob_name = @OriginalB;
    EXEC dbo.usp_MarkPhotoUploaded
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyB,
        @ExpectedRowVersion = @VersionB, @OriginalBlobEtag = N'"etag-b"';
    SELECT @VersionB = row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB;
    EXEC dbo.usp_RecordPhotoScanResult
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyB,
        @ExpectedRowVersion = @VersionB, @ScanResult = N'malicious';
    SELECT @VersionB = row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB
        AND state = N'rejected' AND scan_result = N'malicious'
        AND derivative_sha256_digest IS NULL)
        THROW 52583, 'Malicious Photo was not rejected before processing.', 1;

    /* Cross-owner draft deletion denial, then body-free tombstone. */
    EXEC dbo.usp_BeginPhotoDraftDeletion
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyB,
        @ExpectedRowVersion = @VersionB;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB AND state = N'rejected')
        THROW 52584, 'Cross-owner draft deletion changed a foreign source.', 1;
    EXEC dbo.usp_BeginPhotoDraftDeletion
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyB,
        @ExpectedRowVersion = @VersionB;
    DECLARE @DraftDeletionVersion binary(8) =
        (SELECT row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB);
    EXEC dbo.usp_FinalizePhotoDraftDeletion
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyB,
        @ExpectedDeletionRowVersion = @DraftDeletionVersion;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB AND state = N'deletion_pending')
        THROW 52585, 'Cross-owner draft finalization changed a foreign source.', 1;
    EXEC dbo.usp_FinalizePhotoDraftDeletion
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyB,
        @ExpectedDeletionRowVersion = @DraftDeletionVersion;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyB
        AND state = N'deleted' AND original_blob_name IS NULL
        AND derivative_blob_name IS NULL AND scan_result IS NULL)
        THROW 52586, 'Draft deletion did not leave a body-free Photo tombstone.', 1;

    /* Confirmed aggregate deletion remains pending until both Blobs are gone. */
    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyB, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
        THROW 52587, 'Cross-owner Capture deletion removed a foreign Capture.', 1;
    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyA, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    DECLARE @CaptureDeletionVersion binary(8) =
        (SELECT row_version FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA);
    IF NOT EXISTS
       (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA AND state = N'deletion_pending')
       OR NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
        THROW 52588, 'Photo Capture deletion did not persist pending before Blob cleanup.', 1;
    EXEC dbo.usp_FinalizePhotoCaptureDeletion
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedDeletionRowVersion = @CaptureDeletionVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
        THROW 52589, 'Cross-owner finalization removed a foreign Capture.', 1;
    EXEC dbo.usp_FinalizePhotoCaptureDeletion
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedDeletionRowVersion = @CaptureDeletionVersion;
    IF EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
       OR EXISTS (SELECT 1 FROM dbo.capture_media_links WHERE capture_id = @CaptureIdA)
       OR NOT EXISTS
          (SELECT 1 FROM dbo.capture_media_sources WHERE source_key = @SourceKeyA
           AND state = N'deleted' AND original_blob_name IS NULL
           AND derivative_blob_name IS NULL AND original_sha256_digest IS NULL
           AND derivative_sha256_digest IS NULL AND scan_result IS NULL)
        THROW 52590, 'Confirmed Photo deletion did not remove all private content.', 1;

    IF EXISTS
       (
           SELECT 1 FROM dbo.audit_events
           WHERE metadata_json LIKE N'%' + @ApprovedBody + N'%'
              OR metadata_json LIKE N'%' + @OriginalA + N'%'
              OR metadata_json LIKE N'%' + @DerivativeA + N'%'
       )
        THROW 52591, 'Private Photo content or storage paths appeared in audit metadata.', 1;

    IF (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @MomentCount
       OR (SELECT COUNT(*) FROM dbo.moment_placements WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @PlacementCount
       OR (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @EntityCount
       OR (SELECT COUNT(*) FROM dbo.ai_proposals WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @AiProposalCount
        THROW 52592, 'Photo Capture created an automatic downstream record.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-CAPTURE-MEDIA-001 SQL owner, scan, derivative, concurrency, private confirmation, lifecycle, and downstream checks passed.' AS verification_result;

    ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
