/* PS-HOME-001 production-safe verification.
   Two synthetic owners exercise the bounded Home read. No production member
   content is read, copied, or logged; every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-HOME-001')
        THROW 52560, 'PS-HOME-001 is not registered.', 1;
    IF OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P') IS NULL
        THROW 52561, 'The Owner Home procedure is missing.', 1;

    DECLARE @Definition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P'));
    IF @Definition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @Definition LIKE N'%@OwnerProfileId%'
       OR @Definition LIKE N'%usp_GetPeerSlateUserDashboard%'
       OR @Definition NOT LIKE N'%source.owner_profile_id = @ProfileId%'
       OR @Definition NOT LIKE N'%moment.owner_profile_id = @ProfileId%'
       OR @Definition NOT LIKE N'%TOP (3)%'
       OR @Definition NOT LIKE N'%TOP (1)%'
        THROW 52562, 'The Owner Home procedure is not owner-resolving and bounded.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:home-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'home-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'home-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'home-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'Home Owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'home-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'Home Owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;
    SELECT
        @UserKeyA = app_user.user_key,
        @ProfileIdA = profile.profile_id,
        @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'home-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;
    SELECT
        @UserKeyB = app_user.user_key,
        @ProfileIdB = profile.profile_id,
        @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'home-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @ProfileIdA = @ProfileIdB
        THROW 52563, 'Synthetic Home owners were not provisioned.', 1;

    DECLARE @Digest binary(32) =
        HASHBYTES('SHA2_256', CONVERT(varbinary(max), @Suffix));
    DECLARE @FailedKeyA uniqueidentifier = NEWID();
    DECLARE @ReadyKeyA uniqueidentifier = NEWID();
    DECLARE @FailedKeyB uniqueidentifier = NEWID();

    INSERT dbo.voice_media_sources
    (
        source_key, owner_profile_id, blob_name, content_type, byte_length,
        sha256_digest, locale, client_duration_milliseconds, state,
        safe_error_code, created_by_user_id, created_at_utc, updated_at_utc
    )
    VALUES
        (
            @FailedKeyA, @ProfileIdA,
            CONCAT(N'voice/v1/aa/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.webm'),
            N'audio/webm', 1024, @Digest, N'en-US', 1000, N'failed',
            N'speech_unavailable', @UserIdA,
            DATEADD(minute, -30, SYSUTCDATETIME()),
            DATEADD(minute, -20, SYSUTCDATETIME())
        ),
        (
            @ReadyKeyA, @ProfileIdA,
            CONCAT(N'voice/v1/bb/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.webm'),
            N'audio/webm', 1024, @Digest, N'en-US', 1000, N'needs_review',
            NULL, @UserIdA,
            DATEADD(minute, -18, SYSUTCDATETIME()),
            DATEADD(minute, -10, SYSUTCDATETIME())
        ),
        (
            @FailedKeyB, @ProfileIdB,
            CONCAT(N'voice/v1/cc/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.webm'),
            N'audio/webm', 1024, @Digest, N'en-US', 1000, N'failed',
            N'speech_unavailable', @UserIdB,
            DATEADD(minute, -25, SYSUTCDATETIME()),
            DATEADD(minute, -15, SYSUTCDATETIME())
        );

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA, @CaptureType = N'text',
        @Body = N'SYNTHETIC HOME A CAPTURE - MUST NOT ENTER HOME PAYLOAD';
    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyB, @CaptureType = N'text',
        @Body = N'SYNTHETIC HOME B CAPTURE - MUST NOT ENTER HOME PAYLOAD';

    DECLARE @CaptureKeyA uniqueidentifier =
        (SELECT TOP (1) capture_key FROM dbo.captures
         WHERE owner_profile_id = @ProfileIdA ORDER BY capture_id DESC);
    DECLARE @CaptureKeyB uniqueidentifier =
        (SELECT TOP (1) capture_key FROM dbo.captures
         WHERE owner_profile_id = @ProfileIdB ORDER BY capture_id DESC);
    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyA, @CaptureKey = @CaptureKeyA,
        @SourceRevisionNumber = 0;
    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyB, @CaptureKey = @CaptureKeyB,
        @SourceRevisionNumber = 0;

    DECLARE @RecentMomentA uniqueidentifier = NEWID();
    DECLARE @RecentMomentB uniqueidentifier = NEWID();
    INSERT dbo.moments
    (
        moment_key, owner_profile_id, visibility, status,
        current_version_number, confirmed_version_number,
        confirmed_by_user_id, confirmed_at_utc
    )
    VALUES
        (
            @RecentMomentA, @ProfileIdA, N'private', N'confirmed',
            1, 1, @UserIdA, DATEADD(minute, -5, SYSUTCDATETIME())
        ),
        (
            @RecentMomentB, @ProfileIdB, N'private', N'confirmed',
            1, 1, @UserIdB, DATEADD(minute, -4, SYSUTCDATETIME())
        );
    INSERT dbo.moment_versions
    (
        moment_id, version_number, moment_kind, title, occurred_on,
        occurred_precision, narrative, why_it_matters, saved_by_user_id
    )
    SELECT
        moment.moment_id, 1, N'achievement',
        CASE WHEN moment.owner_profile_id = @ProfileIdA
             THEN N'Synthetic Home A Moment' ELSE N'Synthetic Home B Moment' END,
        CAST(SYSUTCDATETIME() AS date), N'exact',
        N'Synthetic verifier narrative that must not enter the Home payload.',
        N'Synthetic verifier why text that must not enter the Home payload.',
        CASE WHEN moment.owner_profile_id = @ProfileIdA THEN @UserIdA ELSE @UserIdB END
    FROM dbo.moments AS moment
    WHERE moment.moment_key IN (@RecentMomentA, @RecentMomentB);

    DECLARE @CaptureCountBefore int =
        (SELECT COUNT(*) FROM dbo.captures WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @MomentCountBefore int =
        (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @VoiceCountBefore int =
        (SELECT COUNT(*) FROM dbo.voice_media_sources WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));

    /* The six bounded result grids below are the two-owner byte/canary evidence.
       They must contain only each requested owner's opaque keys, fixed review
       summaries supplied later by Python, and the one bounded Moment title. */
    EXEC dbo.usp_GetOwnerHomeForOwner @UserKey = @UserKeyA;
    EXEC dbo.usp_GetOwnerHomeForOwner @UserKey = @UserKeyB;

    IF (SELECT COUNT(*) FROM dbo.captures WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @CaptureCountBefore
       OR (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @MomentCountBefore
       OR (SELECT COUNT(*) FROM dbo.voice_media_sources WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @VoiceCountBefore
        THROW 52564, 'The Owner Home read changed canonical owner records.', 1;

    IF @Definition LIKE N'%capture.body%'
       OR @Definition LIKE N'%provider_transcript%'
       OR @Definition LIKE N'%blob_name%'
       OR @Definition LIKE N'%email%'
       OR @Definition LIKE N'%narrative%'
       OR @Definition LIKE N'%why_it_matters%'
        THROW 52565, 'The Owner Home read includes prohibited private content.', 1;

    ROLLBACK TRANSACTION;
    SELECT CAST(1 AS bit) AS verified,
           N'PS-HOME-001 two-owner bounded read passed' AS result;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
