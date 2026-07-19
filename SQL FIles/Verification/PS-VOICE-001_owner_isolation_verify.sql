/* PS-VOICE-001 production-safe database verification.
   Two synthetic owners exercise upload state, transcription attempts,
   review, idempotent confirmation, Capture lifecycle, export authority,
   retryable deletion, and cross-owner denials.  No real media is used and
   every row is rolled back by the outer transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-VOICE-001')
        THROW 52470, 'PS-VOICE-001 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:voice-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'voice-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'voice-b-', @Suffix);
    DECLARE @PrivateSentinel nvarchar(300) = CONCAT(N'provider-private-', @Suffix);
    DECLARE @ApprovedBody nvarchar(300) = CONCAT(N'member-approved-', @Suffix);
    DECLARE @BlobNameA nvarchar(160) = CONCAT(N'voice/v1/aa/', REPLACE(@Suffix, N'-', N''), N'.webm');
    DECLARE @BlobNameRetry nvarchar(160) = CONCAT(N'voice/v1/bb/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.webm');
    DECLARE @Digest binary(32) = HASHBYTES('SHA2_256', CONVERT(varbinary(max), @Suffix));

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'voice-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'Voice Owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'voice-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'Voice Owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'voice-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectA;
    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'voice-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectB;
    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @ProfileIdA = @ProfileIdB
        THROW 52471, 'Synthetic Voice owners were not provisioned.', 1;

    DECLARE @MomentCount int =
        (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @PlacementCount int =
        (SELECT COUNT(*) FROM dbo.moment_placements WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @EntityCount int =
        (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @AiProposalCount int =
        (SELECT COUNT(*) FROM dbo.ai_proposals WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));

    EXEC dbo.usp_CreateVoiceDraft
        @UserKey = @UserKeyA, @BlobName = @BlobNameA,
        @ContentType = N'audio/webm', @ByteLength = 4096,
        @Sha256Digest = @Digest, @Locale = N'en-US',
        @ClientDurationMilliseconds = 2400;
    DECLARE @SourceKeyA uniqueidentifier;
    DECLARE @SourceVersionA binary(8);
    SELECT @SourceKeyA = source_key, @SourceVersionA = row_version
    FROM dbo.voice_media_sources
    WHERE owner_profile_id = @ProfileIdA AND blob_name = @BlobNameA;
    IF @SourceKeyA IS NULL OR NOT EXISTS
       (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA AND state = N'uploading')
        THROW 52472, 'Owner A Voice source was not created in uploading state.', 1;

    /* Cross-owner upload failure denial. */
    EXEC dbo.usp_FailVoiceUpload
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceVersionA, @SafeErrorCode = N'storage_unavailable';
    IF NOT EXISTS
       (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA AND state = N'uploading')
        THROW 52473, 'Cross-owner upload failure changed a foreign source.', 1;

    /* Cross-owner queue denial. */
    EXEC dbo.usp_QueueVoiceTranscription
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceVersionA;
    IF EXISTS (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
        (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA))
        THROW 52474, 'Cross-owner queue created a foreign attempt.', 1;

    DECLARE @Queue TABLE
    (
        outcome nvarchar(30), source_key uniqueidentifier, blob_name nvarchar(160),
        content_type nvarchar(40), attempt_number int, row_version binary(8)
    );
    INSERT @Queue
    EXEC dbo.usp_QueueVoiceTranscription
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceVersionA;
    IF NOT EXISTS (SELECT 1 FROM @Queue WHERE outcome = N'queued' AND attempt_number = 1)
        THROW 52475, 'Owner A transcription was not queued.', 1;

    /* Cross-owner processing denial. */
    EXEC dbo.usp_MarkVoiceTranscriptionProcessing
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA, @AttemptNumber = 1;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
        (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA)
        AND attempt_number = 1 AND state = N'queued')
        THROW 52476, 'Cross-owner processing changed a foreign attempt.', 1;

    EXEC dbo.usp_MarkVoiceTranscriptionProcessing
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @AttemptNumber = 1;

    /* Cross-owner completion denial. */
    EXEC dbo.usp_CompleteVoiceTranscription
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA, @AttemptNumber = 1,
        @ProviderTranscript = N'cross-owner provider transcript',
        @ProviderRequestId = N'cross-owner-request',
        @VerifiedDurationMilliseconds = 2400;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
        (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA)
        AND attempt_number = 1 AND state = N'processing' AND provider_transcript IS NULL)
        THROW 52477, 'Cross-owner completion changed a foreign attempt.', 1;

    /* Cross-owner failure denial. */
    EXEC dbo.usp_FailVoiceTranscription
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @AttemptNumber = 1, @SafeErrorCode = N'speech_timeout';
    IF NOT EXISTS
       (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
        (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA)
        AND attempt_number = 1 AND state = N'processing')
        THROW 52478, 'Cross-owner failure changed a foreign attempt.', 1;

    EXEC dbo.usp_CompleteVoiceTranscription
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @AttemptNumber = 1,
        @ProviderTranscript = @PrivateSentinel,
        @ProviderRequestId = N'provider-request-a',
        @VerifiedDurationMilliseconds = 2400;
    SELECT @SourceVersionA = row_version
    FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA;

    /* A provider transcript changed after success is structurally blocked by the trigger.
       The isolated SQL proof separately executes the rejected update outside this outer
       verification transaction so XACT_ABORT cannot invalidate the remaining checks. */
    IF OBJECT_ID(N'dbo.trg_voice_transcription_attempts_immutable_result', N'TR') IS NULL
       OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.trg_voice_transcription_attempts_immutable_result', N'TR'))
          NOT LIKE N'%old_value.provider_transcript IS NOT NULL%'
        THROW 52479, 'Immutable provider transcript trigger is missing.', 1;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.voice_transcription_attempts WHERE provider_transcript = @PrivateSentinel)
        THROW 52480, 'Provider transcript provenance was not preserved.', 1;

    /* Cross-owner review/read denial. */
    DECLARE @ForeignDraft TABLE
    (
        source_key uniqueidentifier, state nvarchar(30), content_type nvarchar(40),
        byte_length bigint, locale nvarchar(10), client_duration_milliseconds int,
        verified_duration_milliseconds int, attempt_number int,
        provider_transcript nvarchar(max), safe_error_code nvarchar(60),
        capture_key uniqueidentifier, created_at_utc datetime2(7),
        updated_at_utc datetime2(7), row_version binary(8)
    );
    INSERT @ForeignDraft
    EXEC dbo.usp_GetVoiceDraftForOwner @UserKey = @UserKeyB, @SourceKey = @SourceKeyA;
    IF EXISTS (SELECT 1 FROM @ForeignDraft)
        THROW 52481, 'Cross-owner review exposed a foreign source.', 1;

    /* Cross-owner playback/media denial. */
    DECLARE @ForeignMedia TABLE
    (
        source_key uniqueidentifier, blob_name nvarchar(160), content_type nvarchar(40),
        byte_length bigint, sha256_digest binary(32)
    );
    INSERT @ForeignMedia
    EXEC dbo.usp_GetVoiceMediaForOwner @UserKey = @UserKeyB, @SourceKey = @SourceKeyA;
    IF EXISTS (SELECT 1 FROM @ForeignMedia)
        THROW 52482, 'Cross-owner playback exposed a private locator.', 1;

    /* Cross-owner confirmation denial. */
    EXEC dbo.usp_ConfirmVoiceCapture
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceVersionA, @ApprovedBody = N'cross-owner approved body';
    IF EXISTS (SELECT 1 FROM dbo.voice_capture_links WHERE source_id =
        (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA))
        THROW 52483, 'Cross-owner confirmation created a Capture link.', 1;

    EXEC dbo.usp_ConfirmVoiceCapture
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceVersionA, @ApprovedBody = @ApprovedBody;
    DECLARE @CaptureKeyA uniqueidentifier;
    DECLARE @CaptureIdA bigint;
    SELECT @CaptureIdA = link.capture_id, @CaptureKeyA = capture.capture_key
    FROM dbo.voice_capture_links AS link
    JOIN dbo.voice_media_sources AS source ON source.source_id = link.source_id
    JOIN dbo.captures AS capture ON capture.capture_id = link.capture_id
    WHERE link.owner_profile_id = @ProfileIdA AND source.source_key = @SourceKeyA;
    IF @CaptureIdA IS NULL
       OR NOT EXISTS
          (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA
           AND capture_type = N'voice' AND visibility = N'private' AND body = @ApprovedBody)
       OR NOT EXISTS
          (SELECT 1 FROM dbo.voice_transcription_attempts
           WHERE provider_transcript = @PrivateSentinel AND provider_transcript <> @ApprovedBody)
        THROW 52484, 'Approved Capture body and immutable provider transcript did not remain distinct.', 1;

    EXEC dbo.usp_ConfirmVoiceCapture
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceVersionA, @ApprovedBody = @ApprovedBody;
    IF (SELECT COUNT(*) FROM dbo.voice_capture_links WHERE capture_id = @CaptureIdA) <> 1
       OR (SELECT COUNT(*) FROM dbo.captures WHERE capture_key = @CaptureKeyA) <> 1
        THROW 52485, 'Voice confirmation was not idempotent.', 1;

    /* Cross-owner export denial. */
    DECLARE @ForeignExport TABLE
    (
        capture_key uniqueidentifier, capture_type nvarchar(30), body nvarchar(max),
        original_body nvarchar(max), visibility nvarchar(30), status nvarchar(30), active bit,
        revision_number int, created_at_utc datetime2(7), updated_at_utc datetime2(7),
        revisions_json nvarchar(max)
    );
    INSERT @ForeignExport
    EXEC dbo.usp_ExportCaptureForOwner @UserKey = @UserKeyB, @CaptureKey = @CaptureKeyA;
    IF EXISTS (SELECT 1 FROM @ForeignExport)
        THROW 52486, 'Cross-owner export exposed a voice Capture.', 1;

    DECLARE @CaptureVersion binary(8) =
        (SELECT row_version FROM dbo.captures WHERE capture_id = @CaptureIdA);
    /* Cross-owner archive denial. */
    EXEC dbo.usp_ArchiveCapture
        @UserKey = @UserKeyB, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA AND status = N'captured')
        THROW 52487, 'Cross-owner archive changed a voice Capture.', 1;
    EXEC dbo.usp_ArchiveCapture
        @UserKey = @UserKeyA, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    SELECT @CaptureVersion = row_version FROM dbo.captures WHERE capture_id = @CaptureIdA;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA AND status = N'archived')
        THROW 52488, 'Voice Capture did not archive.', 1;

    /* Cross-owner restore denial. */
    EXEC dbo.usp_RestoreCapture
        @UserKey = @UserKeyB, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA AND status = N'archived')
        THROW 52489, 'Cross-owner restore changed a voice Capture.', 1;
    EXEC dbo.usp_RestoreCapture
        @UserKey = @UserKeyA, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    SELECT @CaptureVersion = row_version FROM dbo.captures WHERE capture_id = @CaptureIdA;

    /* Retry creates attempt two and leaves attempt one immutable. */
    EXEC dbo.usp_CreateVoiceDraft
        @UserKey = @UserKeyA, @BlobName = @BlobNameRetry,
        @ContentType = N'audio/webm', @ByteLength = 2048,
        @Sha256Digest = @Digest, @Locale = N'en-US',
        @ClientDurationMilliseconds = 1000;
    DECLARE @RetrySourceKey uniqueidentifier;
    DECLARE @RetryVersion binary(8);
    SELECT @RetrySourceKey = source_key, @RetryVersion = row_version
    FROM dbo.voice_media_sources
    WHERE owner_profile_id = @ProfileIdA AND blob_name = @BlobNameRetry;
    DELETE @Queue;
    INSERT @Queue EXEC dbo.usp_QueueVoiceTranscription
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey, @ExpectedRowVersion = @RetryVersion;
    EXEC dbo.usp_MarkVoiceTranscriptionProcessing
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey, @AttemptNumber = 1;
    EXEC dbo.usp_FailVoiceTranscription
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey,
        @AttemptNumber = 1, @SafeErrorCode = N'speech_timeout';
    SELECT @RetryVersion = row_version FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey;
    DELETE @Queue;
    INSERT @Queue EXEC dbo.usp_QueueVoiceTranscription
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey, @ExpectedRowVersion = @RetryVersion;
    EXEC dbo.usp_MarkVoiceTranscriptionProcessing
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey, @AttemptNumber = 2;
    EXEC dbo.usp_CompleteVoiceTranscription
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey, @AttemptNumber = 2,
        @ProviderTranscript = N'synthetic retry transcript',
        @ProviderRequestId = N'provider-request-retry', @VerifiedDurationMilliseconds = 1000;
    IF (SELECT COUNT(*) FROM dbo.voice_transcription_attempts WHERE source_id =
        (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey)) <> 2
       OR NOT EXISTS
          (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
           (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey)
           AND attempt_number = 1 AND state = N'failed')
       OR NOT EXISTS
          (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
           (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey)
           AND attempt_number = 2 AND state = N'succeeded')
        THROW 52490, 'Retry did not preserve separate immutable attempts.', 1;

    SELECT @RetryVersion = row_version FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey;
    /* Cross-owner draft deletion denial. */
    EXEC dbo.usp_BeginVoiceDraftDeletion
        @UserKey = @UserKeyB, @SourceKey = @RetrySourceKey,
        @ExpectedRowVersion = @RetryVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey AND state = N'needs_review')
        THROW 52491, 'Cross-owner draft deletion changed a foreign source.', 1;
    EXEC dbo.usp_BeginVoiceDraftDeletion
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey,
        @ExpectedRowVersion = @RetryVersion;
    DECLARE @RetryDeletionVersion binary(8) =
        (SELECT row_version FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey);
    /* Cross-owner draft finalization denial. */
    EXEC dbo.usp_FinalizeVoiceDraftDeletion
        @UserKey = @UserKeyB, @SourceKey = @RetrySourceKey,
        @ExpectedDeletionRowVersion = @RetryDeletionVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey AND state = N'deletion_pending')
        THROW 52492, 'Cross-owner draft finalization changed a foreign source.', 1;
    EXEC dbo.usp_FinalizeVoiceDraftDeletion
        @UserKey = @UserKeyA, @SourceKey = @RetrySourceKey,
        @ExpectedDeletionRowVersion = @RetryDeletionVersion;
    IF NOT EXISTS
       (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey
        AND state = N'deleted' AND blob_name IS NULL AND sha256_digest IS NULL)
       OR EXISTS
          (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
           (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @RetrySourceKey))
        THROW 52493, 'Draft deletion did not leave only a body-free tombstone.', 1;

    /* Cross-owner confirmed-Capture deletion denial. */
    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyB, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
        THROW 52494, 'Cross-owner Capture deletion removed a foreign Capture.', 1;
    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyA, @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersion;
    DECLARE @SourceDeletionVersion binary(8) =
        (SELECT row_version FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA);
    IF NOT EXISTS (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA AND state = N'deletion_pending')
       OR NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
        THROW 52495, 'Voice Capture deletion did not persist pending before finalization.', 1;

    /* Cross-owner confirmed finalization denial. */
    EXEC dbo.usp_FinalizeVoiceCaptureDeletion
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedDeletionRowVersion = @SourceDeletionVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
        THROW 52496, 'Cross-owner finalization removed a foreign Capture.', 1;
    EXEC dbo.usp_FinalizeVoiceCaptureDeletion
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedDeletionRowVersion = @SourceDeletionVersion;
    IF EXISTS (SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdA)
       OR EXISTS (SELECT 1 FROM dbo.voice_capture_links WHERE capture_id = @CaptureIdA)
       OR EXISTS
          (SELECT 1 FROM dbo.voice_transcription_attempts WHERE source_id =
           (SELECT source_id FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA))
       OR NOT EXISTS
          (SELECT 1 FROM dbo.voice_media_sources WHERE source_key = @SourceKeyA
           AND state = N'deleted' AND blob_name IS NULL AND content_type IS NULL
           AND byte_length IS NULL AND sha256_digest IS NULL AND locale IS NULL)
        THROW 52497, 'Confirmed deletion did not remove all private content.', 1;

    IF EXISTS
       (
           SELECT 1 FROM dbo.audit_events
           WHERE metadata_json LIKE N'%' + @PrivateSentinel + N'%'
              OR metadata_json LIKE N'%' + @ApprovedBody + N'%'
              OR metadata_json LIKE N'%' + @BlobNameA + N'%'
       )
        THROW 52498, 'Private content or storage paths appeared in audit metadata.', 1;

    IF (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @MomentCount
       OR (SELECT COUNT(*) FROM dbo.moment_placements WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @PlacementCount
       OR (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @EntityCount
       OR (SELECT COUNT(*) FROM dbo.ai_proposals WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @AiProposalCount
        THROW 52499, 'Voice Capture created an automatic downstream record.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-VOICE-001 SQL owner, provenance, concurrency, retry, lifecycle, and downstream checks passed.' AS verification_result;

    ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
