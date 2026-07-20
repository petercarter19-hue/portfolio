/* Disposable-only PS-HOME-001 founding-alpha performance proof.
   Run only after the complete foundation and PS-HOME-001 are present in an
   isolated database. All values are synthetic; the resource is deleted after
   evidence capture. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

DECLARE @Issuer nvarchar(500) = N'urn:peerslate:home-performance';
DECLARE @Subject nvarchar(500) = N'home-performance-owner';
EXEC dbo.usp_UpsertAppUserFromAuth
    @AuthProvider = N'home-performance',
    @AuthIssuer = @Issuer,
    @AuthSubject = @Subject,
    @DisplayName = N'Synthetic Home Performance Owner';

DECLARE @UserKey nvarchar(300);
DECLARE @ProfileId bigint;
DECLARE @UserId int;
SELECT
    @UserKey = app_user.user_key,
    @ProfileId = profile.profile_id,
    @UserId = app_user.id
FROM dbo.app_users AS app_user
JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
WHERE identity_record.provider = N'home-performance'
  AND identity_record.issuer = @Issuer
  AND identity_record.subject = @Subject;

IF @UserKey IS NULL OR @ProfileId IS NULL OR @UserId IS NULL
    THROW 52580, 'The synthetic performance owner was not provisioned.', 1;

DECLARE @Digest binary(32) = HASHBYTES('SHA2_256', CONVERT(varbinary(max), @Subject));
DECLARE @Counter int = 0;
WHILE @Counter < 100
BEGIN
    INSERT dbo.voice_media_sources
    (
        source_key, owner_profile_id, blob_name, content_type, byte_length,
        sha256_digest, locale, client_duration_milliseconds, state,
        safe_error_code, created_by_user_id, created_at_utc, updated_at_utc
    )
    VALUES
    (
        NEWID(), @ProfileId,
        CONCAT(N'voice/v1/perf/', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''), N'.webm'),
        N'audio/webm', 1024, @Digest, N'en-US', 1000,
        CASE WHEN @Counter % 2 = 0 THEN N'failed' ELSE N'needs_review' END,
        CASE WHEN @Counter % 2 = 0 THEN N'synthetic_failure' ELSE NULL END,
        @UserId,
        DATEADD(minute, -200 - @Counter, SYSUTCDATETIME()),
        DATEADD(minute, -100 - @Counter, SYSUTCDATETIME())
    );
    SET @Counter += 1;
END;

SET @Counter = 0;
WHILE @Counter < 1000
BEGIN
    INSERT dbo.moments
    (
        moment_key, owner_profile_id, visibility, status,
        current_version_number, confirmed_version_number,
        confirmed_by_user_id, confirmed_at_utc,
        created_at_utc, updated_at_utc
    )
    VALUES
    (
        NEWID(), @ProfileId, N'private', N'confirmed', 1, 1, @UserId,
        DATEADD(second, -@Counter, SYSUTCDATETIME()),
        DATEADD(day, -30, SYSUTCDATETIME()),
        DATEADD(second, -@Counter, SYSUTCDATETIME())
    );
    DECLARE @MomentId bigint = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.moment_versions
    (
        moment_id, version_number, moment_kind, title, occurred_on,
        occurred_precision, narrative, why_it_matters, saved_by_user_id
    )
    VALUES
    (
        @MomentId, 1, N'progress',
        CONCAT(N'Synthetic performance Moment ', @Counter),
        CAST(SYSUTCDATETIME() AS date), N'exact',
        N'Synthetic performance narrative.',
        N'Synthetic performance reason.',
        @UserId
    );
    SET @Counter += 1;
END;

COMMIT TRANSACTION;

IF (SELECT COUNT(*) FROM dbo.voice_media_sources WHERE owner_profile_id = @ProfileId) < 100
   OR (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id = @ProfileId AND status = N'confirmed') < 1000
    THROW 52581, 'The founding-alpha performance profile is incomplete.', 1;

EXEC sys.sp_recompile N'dbo.usp_GetOwnerHomeForOwner';
SET @Counter = 0;
WHILE @Counter < 50
BEGIN
    EXEC dbo.usp_GetOwnerHomeForOwner @UserKey = @UserKey;
    SET @Counter += 1;
END;
