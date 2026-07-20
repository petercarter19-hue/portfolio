/* ============================================================
   PS-CAPTURE-MEDIA-001 - private Photo Capture backend

   REVIEW-FIRST MIGRATION. Apply only after manager acceptance.
   Original bytes stay private and unavailable until Defender reports
   clean and the application creates a bounded metadata-free derivative.
   A private Capture is created only after explicit member confirmation.

   Rollback: PS-CAPTURE-MEDIA-001_photo_sources_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52500, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-VOICE-001')
        THROW 52501, 'PS-VOICE-001 must be applied before Photo Capture.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NULL
       OR OBJECT_ID(N'dbo.capture_revisions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.voice_capture_links', N'U') IS NULL
       OR OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 52502, 'The owner, Capture, Voice, Moment, or audit contract is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.captures')
          AND name = N'UX_captures_id_owner_for_media'
    )
        CREATE UNIQUE INDEX UX_captures_id_owner_for_media
            ON dbo.captures(capture_id, owner_profile_id);

    IF OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.capture_media_sources
        (
            source_id bigint IDENTITY(1,1) NOT NULL,
            source_key uniqueidentifier NOT NULL
                CONSTRAINT DF_capture_media_sources_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            source_type nvarchar(20) NOT NULL
                CONSTRAINT DF_capture_media_sources_type DEFAULT N'photo',
            original_blob_name nvarchar(160) NULL,
            derivative_blob_name nvarchar(160) NULL,
            original_content_type nvarchar(40) NULL,
            original_byte_length bigint NULL,
            original_sha256_digest binary(32) NULL,
            original_blob_etag nvarchar(128) NULL,
            derivative_content_type nvarchar(40) NULL,
            derivative_byte_length bigint NULL,
            derivative_sha256_digest binary(32) NULL,
            derivative_blob_etag nvarchar(128) NULL,
            pixel_width int NULL,
            pixel_height int NULL,
            state nvarchar(30) NOT NULL
                CONSTRAINT DF_capture_media_sources_state DEFAULT N'uploading',
            scan_result nvarchar(20) NULL
                CONSTRAINT DF_capture_media_sources_scan DEFAULT N'unknown',
            scan_completed_at_utc datetime2(7) NULL,
            safe_error_code nvarchar(60) NULL,
            deletion_capture_row_version binary(8) NULL,
            created_by_user_id int NOT NULL,
            deleted_by_user_id int NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_capture_media_sources_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_capture_media_sources_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_capture_media_sources PRIMARY KEY (source_id),
            CONSTRAINT UQ_capture_media_sources_key UNIQUE (source_key),
            CONSTRAINT UQ_capture_media_sources_id_owner UNIQUE
                (source_id, owner_profile_id),
            CONSTRAINT FK_capture_media_sources_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_capture_media_sources_creator FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_capture_media_sources_deleter FOREIGN KEY (deleted_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_capture_media_sources_type CHECK (source_type = N'photo'),
            CONSTRAINT CK_capture_media_sources_state CHECK
            (
                state IN
                (
                    N'uploading', N'scanning', N'processing', N'needs_review',
                    N'confirmed', N'failed', N'rejected',
                    N'deletion_pending', N'deleted'
                )
            ),
            CONSTRAINT CK_capture_media_sources_scan CHECK
            (
                scan_result IN
                    (N'unknown', N'clean', N'malicious', N'error', N'not_scanned')
                OR scan_result IS NULL
            ),
            CONSTRAINT CK_capture_media_sources_original_payload CHECK
            (
                (
                    state <> N'deleted'
                    AND original_blob_name LIKE N'photo/v1/%'
                    AND derivative_blob_name LIKE N'photo/v1/%-preview.%'
                    AND original_blob_name <> derivative_blob_name
                    AND LEN(original_blob_name) = 48
                    AND LEN(derivative_blob_name) = 56
                    AND derivative_blob_name =
                        LEFT(original_blob_name, 44) + N'-preview' + RIGHT(original_blob_name, 4)
                    AND original_content_type IN (N'image/jpeg', N'image/png')
                    AND
                    (
                        (original_content_type = N'image/jpeg' AND RIGHT(original_blob_name, 4) = N'.jpg')
                        OR (original_content_type = N'image/png' AND RIGHT(original_blob_name, 4) = N'.png')
                    )
                    AND original_byte_length BETWEEN 1 AND 10485760
                    AND original_sha256_digest IS NOT NULL
                    AND scan_result IS NOT NULL
                    AND deleted_at_utc IS NULL
                )
                OR
                (
                    state = N'deleted'
                    AND original_blob_name IS NULL
                    AND derivative_blob_name IS NULL
                    AND original_content_type IS NULL
                    AND original_byte_length IS NULL
                    AND original_sha256_digest IS NULL
                    AND original_blob_etag IS NULL
                    AND derivative_content_type IS NULL
                    AND derivative_byte_length IS NULL
                    AND derivative_sha256_digest IS NULL
                    AND derivative_blob_etag IS NULL
                    AND pixel_width IS NULL
                    AND pixel_height IS NULL
                    AND scan_result IS NULL
                    AND scan_completed_at_utc IS NULL
                    AND safe_error_code IS NULL
                    AND deletion_capture_row_version IS NULL
                    AND deleted_at_utc IS NOT NULL
                )
            ),
            CONSTRAINT CK_capture_media_sources_derivative_payload CHECK
            (
                (
                    derivative_content_type IS NULL
                    AND derivative_byte_length IS NULL
                    AND derivative_sha256_digest IS NULL
                    AND derivative_blob_etag IS NULL
                    AND pixel_width IS NULL
                    AND pixel_height IS NULL
                )
                OR
                (
                    derivative_content_type IN (N'image/jpeg', N'image/png')
                    AND derivative_content_type = original_content_type
                    AND derivative_byte_length BETWEEN 1 AND 10485760
                    AND derivative_sha256_digest IS NOT NULL
                    AND derivative_blob_etag IS NOT NULL
                    AND pixel_width BETWEEN 1 AND 2400
                    AND pixel_height BETWEEN 1 AND 2400
                )
            ),
            CONSTRAINT CK_capture_media_sources_state_payload CHECK
            (
                state IN (N'uploading', N'scanning', N'failed', N'rejected', N'deletion_pending', N'deleted')
                OR
                (
                    state = N'processing'
                    AND scan_result = N'clean'
                    AND original_blob_etag IS NOT NULL
                )
                OR
                (
                    state IN (N'needs_review', N'confirmed')
                    AND scan_result = N'clean'
                    AND original_blob_etag IS NOT NULL
                    AND derivative_content_type IS NOT NULL
                )
            )
        );

        CREATE UNIQUE INDEX UX_capture_media_sources_live_original_blob
            ON dbo.capture_media_sources(original_blob_name)
            WHERE original_blob_name IS NOT NULL;
        CREATE UNIQUE INDEX UX_capture_media_sources_live_derivative_blob
            ON dbo.capture_media_sources(derivative_blob_name)
            WHERE derivative_blob_name IS NOT NULL;
        CREATE INDEX IX_capture_media_sources_owner_state
            ON dbo.capture_media_sources(owner_profile_id, state, updated_at_utc DESC)
            INCLUDE (source_key, source_type, scan_result, original_content_type,
                     original_byte_length, pixel_width, pixel_height);
    END;

    IF OBJECT_ID(N'dbo.capture_media_links', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.capture_media_links
        (
            capture_media_link_id bigint IDENTITY(1,1) NOT NULL,
            source_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            capture_id bigint NOT NULL,
            confirmed_by_user_id int NOT NULL,
            confirmed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_capture_media_links_confirmed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_capture_media_links PRIMARY KEY (capture_media_link_id),
            CONSTRAINT UQ_capture_media_links_source UNIQUE (source_id),
            CONSTRAINT UQ_capture_media_links_capture UNIQUE (capture_id),
            CONSTRAINT FK_capture_media_links_source_owner
                FOREIGN KEY (source_id, owner_profile_id)
                REFERENCES dbo.capture_media_sources(source_id, owner_profile_id),
            CONSTRAINT FK_capture_media_links_capture_owner
                FOREIGN KEY (capture_id, owner_profile_id)
                REFERENCES dbo.captures(capture_id, owner_profile_id),
            CONSTRAINT FK_capture_media_links_actor FOREIGN KEY (confirmed_by_user_id)
                REFERENCES dbo.app_users(id)
        );
    END;

    IF COL_LENGTH(N'dbo.capture_media_sources', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'derivative_sha256_digest') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_links', N'owner_profile_id') IS NULL
        THROW 52503, 'Existing Capture Media tables are incompatible.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CreatePhotoSource
            @UserKey nvarchar(300),
            @OriginalBlobName nvarchar(160),
            @DerivativeBlobName nvarchar(160),
            @OriginalContentType nvarchar(40),
            @OriginalByteLength bigint,
            @OriginalSha256Digest binary(32)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @OriginalBlobName = NULLIF(LTRIM(RTRIM(@OriginalBlobName)), N'''');
            SET @DerivativeBlobName = NULLIF(LTRIM(RTRIM(@DerivativeBlobName)), N'''');
            IF @UserKey IS NULL OR @OriginalBlobName IS NULL OR @DerivativeBlobName IS NULL
               OR @OriginalSha256Digest IS NULL
                THROW 52504, ''Photo owner and validated media are required.'', 1;
            IF @OriginalBlobName NOT LIKE N''photo/v1/%''
               OR @DerivativeBlobName NOT LIKE N''photo/v1/%-preview.%''
               OR @OriginalBlobName = @DerivativeBlobName
               OR LEN(@OriginalBlobName) <> 48 OR LEN(@DerivativeBlobName) <> 56
               OR @DerivativeBlobName <>
                  LEFT(@OriginalBlobName, 44) + N''-preview'' + RIGHT(@OriginalBlobName, 4)
               OR @OriginalContentType NOT IN (N''image/jpeg'', N''image/png'')
               OR (@OriginalContentType = N''image/jpeg'' AND RIGHT(@OriginalBlobName, 4) <> N''.jpg'')
               OR (@OriginalContentType = N''image/png'' AND RIGHT(@OriginalBlobName, 4) <> N''.png'')
               OR @OriginalByteLength NOT BETWEEN 1 AND 10485760
                THROW 52505, ''Photo media contract is invalid.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1 AND profile.active = 1;
                IF @ProfileId IS NULL OR @UserId IS NULL
                    THROW 52506, ''Authenticated owner profile not found.'', 1;
                IF
                (
                    SELECT COUNT(*)
                    FROM dbo.capture_media_sources WITH (UPDLOCK, HOLDLOCK)
                    WHERE owner_profile_id = @ProfileId AND source_type = N''photo''
                      AND state NOT IN (N''confirmed'', N''deleted'')
                ) >= 10
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''draft_limit'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS source_key,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;
                INSERT dbo.capture_media_sources
                (
                    owner_profile_id, source_type, original_blob_name,
                    derivative_blob_name, original_content_type,
                    original_byte_length, original_sha256_digest,
                    state, scan_result, created_by_user_id
                )
                VALUES
                (
                    @ProfileId, N''photo'', @OriginalBlobName,
                    @DerivativeBlobName, @OriginalContentType,
                    @OriginalByteLength, @OriginalSha256Digest,
                    N''uploading'', N''unknown'', @UserId
                );
                DECLARE @SourceId bigint = CONVERT(bigint, SCOPE_IDENTITY());
                DECLARE @SourceKey uniqueidentifier;
                SELECT @SourceKey = source_key
                FROM dbo.capture_media_sources WHERE source_id = @SourceId;
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100), metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId, @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''photo.draft.created'', @EntityType = N''photo_source'',
                    @EntityKey = @SourceKey, @Outcome = N''success'',
                    @MetadataJson = N''{"state":"uploading","source_type":"photo"}'';
                COMMIT TRANSACTION;
                SELECT N''created'' AS outcome, source_key, row_version
                FROM dbo.capture_media_sources
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_MarkPhotoUploaded
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8), @OriginalBlobEtag nvarchar(128)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @OriginalBlobEtag = NULLIF(LTRIM(RTRIM(@OriginalBlobEtag)), N'''');
            IF NULLIF(LTRIM(RTRIM(@UserKey)), N'''') IS NULL
               OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
               OR @OriginalBlobEtag IS NULL OR LEN(@OriginalBlobEtag) > 128
                THROW 52507, ''Owner, source, version, and Blob ETag are required.'', 1;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            UPDATE dbo.capture_media_sources
            SET original_blob_etag = @OriginalBlobEtag, state = N''scanning'',
                scan_result = N''unknown'', safe_error_code = NULL,
                updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey
              AND source_type = N''photo'' AND state = N''uploading''
              AND row_version = @ExpectedRowVersion;
            IF @@ROWCOUNT <> 1
            BEGIN
                SELECT N''not_found_or_changed'' AS outcome;
                RETURN;
            END;
            SELECT N''scanning'' AS outcome, row_version
            FROM dbo.capture_media_sources
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FailPhotoSource
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8), @SafeErrorCode nvarchar(60),
            @Terminal bit = 0
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @SafeErrorCode NOT IN
            (
                N''storage_unavailable'', N''scan_unavailable'', N''scan_error'',
                N''not_scanned'', N''integrity_failed'', N''invalid_image'',
                N''dimensions'', N''processing_failed''
            ) SET @SafeErrorCode = N''processing_failed'';
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            UPDATE dbo.capture_media_sources
            SET state = CASE WHEN ISNULL(@Terminal, 0) = 1 THEN N''rejected'' ELSE N''failed'' END,
                safe_error_code = @SafeErrorCode, updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey
              AND source_type = N''photo''
              AND state IN (N''uploading'', N''scanning'', N''processing'', N''failed'')
              AND row_version = @ExpectedRowVersion;
            IF @@ROWCOUNT <> 1
            BEGIN SELECT N''not_found_or_changed'' AS outcome; RETURN; END;
            SELECT CASE WHEN ISNULL(@Terminal, 0) = 1 THEN N''rejected'' ELSE N''failed'' END AS outcome,
                   row_version
            FROM dbo.capture_media_sources
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetPhotoSourceForOwner
            @UserKey nvarchar(300), @SourceKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT source.source_key, source.source_type, source.state,
                   source.scan_result, source.scan_completed_at_utc,
                   source.safe_error_code, source.original_content_type,
                   source.original_byte_length, source.derivative_content_type,
                   source.derivative_byte_length, source.pixel_width,
                   source.pixel_height, capture.capture_key,
                   source.created_at_utc, source.updated_at_utc, source.row_version
            FROM dbo.capture_media_sources AS source
            LEFT JOIN dbo.capture_media_links AS link ON link.source_id = source.source_id
            LEFT JOIN dbo.captures AS capture ON capture.capture_id = link.capture_id
            WHERE source.owner_profile_id = @ProfileId
              AND source.source_key = @SourceKey
              AND source.source_type = N''photo'' AND source.state <> N''deleted'';
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetPhotoProcessingSourceForOwner
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT source.source_key, source.state, source.scan_result,
                   source.original_blob_name, source.derivative_blob_name,
                   source.original_content_type, source.original_byte_length,
                   source.original_sha256_digest, source.original_blob_etag,
                   source.row_version
            FROM dbo.capture_media_sources AS source
            WHERE source.owner_profile_id = @ProfileId
              AND source.source_key = @SourceKey
              AND source.source_type = N''photo''
              AND source.state IN (N''scanning'', N''failed'', N''needs_review'', N''confirmed'')
              AND source.row_version = @ExpectedRowVersion;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_RecordPhotoScanResult
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8), @ScanResult nvarchar(20),
            @ScanCompletedAtUtc datetime2(7) = NULL,
            @SafeErrorCode nvarchar(60) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @ScanResult NOT IN (N''clean'', N''malicious'', N''error'', N''not_scanned'')
                THROW 52508, ''A recognized Defender scan result is required.'', 1;
            IF @ScanResult = N''malicious'' SET @SafeErrorCode = N''malicious'';
            IF @ScanResult = N''error'' SET @SafeErrorCode = N''scan_error'';
            IF @ScanResult = N''not_scanned'' SET @SafeErrorCode = N''not_scanned'';
            IF @ScanResult = N''clean'' SET @SafeErrorCode = NULL;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            UPDATE dbo.capture_media_sources
            SET scan_result = @ScanResult,
                scan_completed_at_utc = COALESCE(@ScanCompletedAtUtc, SYSUTCDATETIME()),
                state = CASE @ScanResult
                    WHEN N''clean'' THEN N''processing''
                    WHEN N''malicious'' THEN N''rejected'' ELSE N''failed'' END,
                safe_error_code = @SafeErrorCode,
                updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey
              AND source_type = N''photo'' AND state IN (N''scanning'', N''failed'')
              AND row_version = @ExpectedRowVersion;
            IF @@ROWCOUNT <> 1
            BEGIN SELECT N''not_found_or_changed'' AS outcome; RETURN; END;
            SELECT state AS outcome, original_blob_name, derivative_blob_name,
                   original_content_type, original_byte_length,
                   original_sha256_digest, original_blob_etag, row_version
            FROM dbo.capture_media_sources
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CompletePhotoProcessing
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @DerivativeContentType nvarchar(40), @DerivativeByteLength bigint,
            @DerivativeSha256Digest binary(32), @DerivativeBlobEtag nvarchar(128),
            @PixelWidth int, @PixelHeight int
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @DerivativeBlobEtag = NULLIF(LTRIM(RTRIM(@DerivativeBlobEtag)), N'''');
            IF @DerivativeContentType NOT IN (N''image/jpeg'', N''image/png'')
               OR @DerivativeByteLength NOT BETWEEN 1 AND 10485760
               OR @DerivativeSha256Digest IS NULL OR @DerivativeBlobEtag IS NULL
               OR LEN(@DerivativeBlobEtag) > 128
               OR @PixelWidth NOT BETWEEN 1 AND 2400
               OR @PixelHeight NOT BETWEEN 1 AND 2400
                THROW 52509, ''The safe Photo derivative contract is invalid.'', 1;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            UPDATE dbo.capture_media_sources
            SET derivative_content_type = @DerivativeContentType,
                derivative_byte_length = @DerivativeByteLength,
                derivative_sha256_digest = @DerivativeSha256Digest,
                derivative_blob_etag = @DerivativeBlobEtag,
                pixel_width = @PixelWidth, pixel_height = @PixelHeight,
                state = N''needs_review'', safe_error_code = NULL,
                updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey
              AND source_type = N''photo'' AND state = N''processing''
              AND scan_result = N''clean''
              AND original_content_type = @DerivativeContentType
              AND row_version = @ExpectedRowVersion;
            IF @@ROWCOUNT <> 1
            BEGIN SELECT N''not_found_or_changed'' AS outcome; RETURN; END;
            SELECT N''needs_review'' AS outcome, source_key, row_version
            FROM dbo.capture_media_sources
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ConfirmPhotoCapture
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8), @ApprovedBody nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @ApprovedBody = NULLIF(LTRIM(RTRIM(@ApprovedBody)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
               OR @ApprovedBody IS NULL OR DATALENGTH(@ApprovedBody) / 2 > 8000
               OR LEN
                  (
                      REPLACE
                      (
                          REPLACE(REPLACE(@ApprovedBody, NCHAR(9), N''''), NCHAR(10), N''''),
                          NCHAR(13), N''''
                      )
                  ) = 0
                THROW 52510, ''Owner, source version, and approved note are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @SourceId bigint;
                DECLARE @CaptureId bigint;
                DECLARE @CaptureKey uniqueidentifier;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @CaptureId = link.capture_id, @SourceId = link.source_id
                FROM dbo.capture_media_links AS link WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.capture_media_sources AS source ON source.source_id = link.source_id
                WHERE link.owner_profile_id = @ProfileId AND source.source_key = @SourceKey;
                IF @CaptureId IS NOT NULL
                BEGIN
                    SELECT @CaptureKey = capture_key FROM dbo.captures WHERE capture_id = @CaptureId;
                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome, @CaptureKey AS capture_key;
                    RETURN;
                END;
                SELECT @SourceId = source.source_id
                FROM dbo.capture_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.source_type = N''photo'' AND source.state = N''needs_review''
                  AND source.scan_result = N''clean''
                  AND source.derivative_sha256_digest IS NOT NULL
                  AND source.row_version = @ExpectedRowVersion;
                IF @SourceId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS capture_key;
                    RETURN;
                END;
                INSERT dbo.captures
                    (owner_profile_id, capture_type, body, visibility, status, active)
                VALUES (@ProfileId, N''photo'', @ApprovedBody, N''private'', N''captured'', 1);
                SET @CaptureId = CONVERT(bigint, SCOPE_IDENTITY());
                SELECT @CaptureKey = capture_key FROM dbo.captures WHERE capture_id = @CaptureId;
                INSERT dbo.capture_media_links
                    (source_id, owner_profile_id, capture_id, confirmed_by_user_id)
                VALUES (@SourceId, @ProfileId, @CaptureId, @UserId);
                UPDATE dbo.capture_media_sources
                SET state = N''confirmed'', updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100), metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId, @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''photo.capture.confirmed'', @EntityType = N''capture'',
                    @EntityKey = @CaptureKey, @Outcome = N''success'',
                    @MetadataJson = N''{"capture_type":"photo","visibility":"private"}'';
                COMMIT TRANSACTION;
                SELECT N''created'' AS outcome, @CaptureKey AS capture_key;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                IF ERROR_NUMBER() IN (2601, 2627)
                BEGIN
                    SELECT @CaptureKey = capture.capture_key
                    FROM dbo.capture_media_links AS link
                    JOIN dbo.capture_media_sources AS source ON source.source_id = link.source_id
                    JOIN dbo.captures AS capture ON capture.capture_id = link.capture_id
                    WHERE link.owner_profile_id = @ProfileId AND source.source_key = @SourceKey;
                    IF @CaptureKey IS NOT NULL
                    BEGIN SELECT N''existing'' AS outcome, @CaptureKey AS capture_key; RETURN; END;
                END;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetPhotoMediaForOwner
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @MediaKind nvarchar(20)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @MediaKind NOT IN (N''preview'', N''original'')
                THROW 52511, ''A supported Photo media kind is required.'', 1;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT source.source_key,
                   CASE WHEN @MediaKind = N''preview'' THEN source.derivative_blob_name
                        ELSE source.original_blob_name END AS blob_name,
                   CASE WHEN @MediaKind = N''preview'' THEN source.derivative_content_type
                        ELSE source.original_content_type END AS content_type,
                   CASE WHEN @MediaKind = N''preview'' THEN source.derivative_byte_length
                        ELSE source.original_byte_length END AS byte_length,
                   CASE WHEN @MediaKind = N''preview'' THEN source.derivative_sha256_digest
                        ELSE source.original_sha256_digest END AS sha256_digest
            FROM dbo.capture_media_sources AS source
            WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
              AND source.source_type = N''photo'' AND source.scan_result = N''clean''
              AND source.state IN (N''needs_review'', N''confirmed'')
              AND source.derivative_sha256_digest IS NOT NULL;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_BeginPhotoDraftDeletion
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            DECLARE @SourceId bigint;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT @SourceId = source.source_id
            FROM dbo.capture_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
            WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
              AND source.source_type = N''photo''
              AND source.state NOT IN (N''confirmed'', N''deleted'')
              AND source.row_version = @ExpectedRowVersion
              AND NOT EXISTS
                  (SELECT 1 FROM dbo.capture_media_links AS link WHERE link.source_id = source.source_id);
            IF @SourceId IS NULL OR @UserId IS NULL
            BEGIN SELECT N''not_found_or_changed'' AS outcome; RETURN; END;
            UPDATE dbo.capture_media_sources
            SET state = N''deletion_pending'', safe_error_code = NULL,
                deleted_by_user_id = @UserId, updated_at_utc = SYSUTCDATETIME()
            WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
            SELECT N''pending'' AS outcome, source_key,
                   original_blob_name, derivative_blob_name,
                   row_version AS deletion_token
            FROM dbo.capture_media_sources
            WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FinalizePhotoDraftDeletion
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedDeletionRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @SourceId bigint;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id
                FROM dbo.capture_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.source_type = N''photo'' AND source.state = N''deletion_pending''
                  AND source.row_version = @ExpectedDeletionRowVersion
                  AND NOT EXISTS
                      (SELECT 1 FROM dbo.capture_media_links AS link WHERE link.source_id = source.source_id);
                IF @SourceId IS NULL OR @UserId IS NULL
                BEGIN COMMIT TRANSACTION; SELECT N''not_found_or_changed'' AS outcome; RETURN; END;
                UPDATE dbo.capture_media_sources
                SET original_blob_name = NULL, derivative_blob_name = NULL,
                    original_content_type = NULL, original_byte_length = NULL,
                    original_sha256_digest = NULL, original_blob_etag = NULL,
                    derivative_content_type = NULL, derivative_byte_length = NULL,
                    derivative_sha256_digest = NULL, derivative_blob_etag = NULL,
                    pixel_width = NULL, pixel_height = NULL,
                    state = N''deleted'', scan_result = NULL,
                    scan_completed_at_utc = NULL, safe_error_code = NULL,
                    deletion_capture_row_version = NULL,
                    deleted_at_utc = SYSUTCDATETIME(), updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100), metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId, @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''photo.draft.deleted'', @EntityType = N''photo_source'',
                    @EntityKey = @SourceKey, @Outcome = N''success'',
                    @MetadataJson = N''{"state":"deleted"}'';
                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* Text finishes immediately; Voice and Photo return opaque server cleanup locators. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier, @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF NULLIF(LTRIM(RTRIM(@UserKey)), N'''') IS NULL
               OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52114, ''Owner, capture, and expected version are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                DECLARE @PreviousStatus nvarchar(30);
                DECLARE @VoiceSourceId bigint;
                DECLARE @PhotoSourceId bigint;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @CaptureId = capture.capture_id, @PreviousStatus = capture.status,
                       @VoiceSourceId = voice_link.source_id,
                       @PhotoSourceId = photo_link.source_id
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                LEFT JOIN dbo.voice_capture_links AS voice_link ON voice_link.capture_id = capture.capture_id
                LEFT JOIN dbo.capture_media_links AS photo_link ON photo_link.capture_id = capture.capture_id
                WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL AND capture.row_version = @ExpectedRowVersion
                  AND ((capture.active = 1 AND capture.status = N''captured'')
                    OR (capture.active = 0 AND capture.status = N''archived''));
                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS nvarchar(20)) AS source_type,
                           CAST(NULL AS uniqueidentifier) AS source_key,
                           CAST(NULL AS nvarchar(160)) AS blob_name,
                           CAST(NULL AS nvarchar(160)) AS original_blob_name,
                           CAST(NULL AS nvarchar(160)) AS derivative_blob_name,
                           CAST(NULL AS binary(8)) AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count;
                    RETURN;
                END;
                IF @VoiceSourceId IS NOT NULL
                BEGIN
                    UPDATE dbo.voice_media_sources
                    SET state = N''deletion_pending'', safe_error_code = NULL,
                        deletion_capture_row_version = @ExpectedRowVersion,
                        deleted_by_user_id = @UserId, updated_at_utc = SYSUTCDATETIME()
                    WHERE source_id = @VoiceSourceId AND owner_profile_id = @ProfileId
                      AND state IN (N''confirmed'', N''deletion_pending'');
                    IF @@ROWCOUNT <> 1 THROW 52415, ''Voice deletion state is invalid.'', 1;
                    COMMIT TRANSACTION;
                    SELECT N''pending'' AS outcome, N''voice'' AS source_type,
                           source_key, blob_name,
                           CAST(NULL AS nvarchar(160)) AS original_blob_name,
                           CAST(NULL AS nvarchar(160)) AS derivative_blob_name,
                           row_version AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count
                    FROM dbo.voice_media_sources
                    WHERE source_id = @VoiceSourceId AND owner_profile_id = @ProfileId;
                    RETURN;
                END;
                IF @PhotoSourceId IS NOT NULL
                BEGIN
                    UPDATE dbo.capture_media_sources
                    SET state = N''deletion_pending'', safe_error_code = NULL,
                        deletion_capture_row_version = @ExpectedRowVersion,
                        deleted_by_user_id = @UserId, updated_at_utc = SYSUTCDATETIME()
                    WHERE source_id = @PhotoSourceId AND owner_profile_id = @ProfileId
                      AND source_type = N''photo''
                      AND state IN (N''confirmed'', N''deletion_pending'');
                    IF @@ROWCOUNT <> 1 THROW 52512, ''Photo deletion state is invalid.'', 1;
                    COMMIT TRANSACTION;
                    SELECT N''pending'' AS outcome, N''photo'' AS source_type,
                           source_key, CAST(NULL AS nvarchar(160)) AS blob_name,
                           original_blob_name, derivative_blob_name,
                           row_version AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count
                    FROM dbo.capture_media_sources
                    WHERE source_id = @PhotoSourceId AND owner_profile_id = @ProfileId;
                    RETURN;
                END;
                DECLARE @RevisionCount int =
                    (SELECT COUNT(*) FROM dbo.capture_revisions WHERE capture_id = @CaptureId);
                DECLARE @MomentSourceCount int =
                    (SELECT COUNT(*) FROM dbo.moment_sources
                     WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId
                       AND source_state = N''available'');
                UPDATE dbo.moment_sources
                SET source_state = N''deleted'', source_deleted_at_utc = SYSUTCDATETIME(),
                    capture_revision_id = NULL, capture_id = NULL
                WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId
                  AND source_state = N''available'';
                IF @@ROWCOUNT <> @MomentSourceCount
                    THROW 52216, ''Capture source tombstones were not updated atomically.'', 1;
                DECLARE @AuditMetadata nvarchar(max) = CONCAT
                    (N''{"previous_status":"'', @PreviousStatus, N''","revision_count":'',
                     @RevisionCount, N'',"moment_source_tombstone_count":'', @MomentSourceCount, N''}'');
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100), metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId, @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.deleted'', @EntityType = N''capture'',
                    @EntityKey = @CaptureKey, @Outcome = N''success'', @MetadataJson = @AuditMetadata;
                DELETE dbo.capture_revisions WHERE capture_id = @CaptureId;
                DELETE dbo.captures WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId;
                IF @@ROWCOUNT <> 1 THROW 52115, ''Capture delete did not complete atomically.'', 1;
                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome,
                       CAST(NULL AS nvarchar(20)) AS source_type,
                       CAST(NULL AS uniqueidentifier) AS source_key,
                       CAST(NULL AS nvarchar(160)) AS blob_name,
                       CAST(NULL AS nvarchar(160)) AS original_blob_name,
                       CAST(NULL AS nvarchar(160)) AS derivative_blob_name,
                       CAST(NULL AS binary(8)) AS deletion_token,
                       @RevisionCount AS deleted_revision_count,
                       @MomentSourceCount AS tombstoned_moment_source_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FinalizePhotoCaptureDeletion
            @UserKey nvarchar(300), @SourceKey uniqueidentifier,
            @ExpectedDeletionRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @SourceId bigint;
                DECLARE @CaptureId bigint;
                DECLARE @CaptureKey uniqueidentifier;
                DECLARE @RevisionCount int;
                DECLARE @MomentSourceCount int;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id, @CaptureId = link.capture_id,
                       @CaptureKey = capture.capture_key
                FROM dbo.capture_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.capture_media_links AS link ON link.source_id = source.source_id
                JOIN dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK) ON capture.capture_id = link.capture_id
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.source_type = N''photo'' AND source.state = N''deletion_pending''
                  AND source.row_version = @ExpectedDeletionRowVersion
                  AND link.owner_profile_id = @ProfileId
                  AND capture.owner_profile_id = @ProfileId
                  AND capture.row_version = source.deletion_capture_row_version;
                IF @SourceId IS NULL OR @CaptureId IS NULL OR @UserId IS NULL
                BEGIN COMMIT TRANSACTION; SELECT N''not_found_or_changed'' AS outcome; RETURN; END;
                SELECT @RevisionCount = COUNT(*) FROM dbo.capture_revisions WHERE capture_id = @CaptureId;
                SELECT @MomentSourceCount = COUNT(*) FROM dbo.moment_sources
                WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId
                  AND source_state = N''available'';
                UPDATE dbo.moment_sources
                SET source_state = N''deleted'', source_deleted_at_utc = SYSUTCDATETIME(),
                    capture_revision_id = NULL, capture_id = NULL
                WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId
                  AND source_state = N''available'';
                IF @@ROWCOUNT <> @MomentSourceCount
                    THROW 52216, ''Capture source tombstones were not updated atomically.'', 1;
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100), metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId, @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.deleted'', @EntityType = N''capture'',
                    @EntityKey = @CaptureKey, @Outcome = N''success'',
                    @MetadataJson = N''{"capture_type":"photo","source_state":"deleted"}'';
                DELETE dbo.capture_revisions WHERE capture_id = @CaptureId;
                DELETE dbo.capture_media_links
                WHERE source_id = @SourceId AND capture_id = @CaptureId
                  AND owner_profile_id = @ProfileId;
                DELETE dbo.captures WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId;
                IF @@ROWCOUNT <> 1 THROW 52513, ''Photo Capture deletion did not complete atomically.'', 1;
                UPDATE dbo.capture_media_sources
                SET original_blob_name = NULL, derivative_blob_name = NULL,
                    original_content_type = NULL, original_byte_length = NULL,
                    original_sha256_digest = NULL, original_blob_etag = NULL,
                    derivative_content_type = NULL, derivative_byte_length = NULL,
                    derivative_sha256_digest = NULL, derivative_blob_etag = NULL,
                    pixel_width = NULL, pixel_height = NULL,
                    state = N''deleted'', scan_result = NULL,
                    scan_completed_at_utc = NULL, safe_error_code = NULL,
                    deletion_capture_row_version = NULL,
                    deleted_at_utc = SYSUTCDATETIME(), updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome, @RevisionCount AS deleted_revision_count,
                       @MomentSourceCount AS tombstoned_moment_source_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ExportCaptureForOwner
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            DECLARE @CaptureId bigint;
            DECLARE @CaptureType nvarchar(30);
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT @CaptureId = capture.capture_id, @CaptureType = capture.capture_type
            FROM dbo.captures AS capture
            WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
              AND capture.deleted_at_utc IS NULL
              AND ((capture.active = 1 AND capture.status = N''captured'')
                OR (capture.active = 0 AND capture.status = N''archived''));
            SELECT capture.capture_key, capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body, capture.visibility, capture.status,
                capture.active, COALESCE(latest_revision.revision_number, 0) AS revision_number,
                capture.created_at_utc, capture.updated_at_utc, revisions.revisions_json
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT
                (
                    SELECT revision.revision_number, revision.body, revision.correction_note,
                           revision.corrected_at_utc
                    FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                    ORDER BY revision.revision_number FOR JSON PATH
                ) AS revisions_json
            ) AS revisions
            WHERE capture.capture_id = @CaptureId AND capture.owner_profile_id = @ProfileId;
            IF @CaptureType = N''voice''
            BEGIN
                SELECT N''voice'' AS source_type,
                       source.source_key, source.content_type, source.byte_length,
                       source.locale, source.client_duration_milliseconds,
                       source.verified_duration_milliseconds,
                       attempt.provider_transcript
                FROM dbo.voice_capture_links AS link
                JOIN dbo.voice_media_sources AS source ON source.source_id = link.source_id
                JOIN dbo.voice_transcription_attempts AS attempt
                  ON attempt.attempt_id = link.successful_attempt_id
                WHERE link.capture_id = @CaptureId AND link.owner_profile_id = @ProfileId
                  AND source.owner_profile_id = @ProfileId AND attempt.owner_profile_id = @ProfileId
                  AND source.state IN (N''confirmed'', N''deletion_pending'')
                  AND attempt.state = N''succeeded'';
            END;
            ELSE IF @CaptureType = N''photo''
            BEGIN
                SELECT N''photo'' AS source_type, source.source_key,
                       source.original_content_type, source.original_byte_length,
                       source.derivative_content_type, source.derivative_byte_length,
                       source.pixel_width, source.pixel_height,
                       source.scan_result, source.scan_completed_at_utc
                FROM dbo.capture_media_links AS link
                JOIN dbo.capture_media_sources AS source ON source.source_id = link.source_id
                WHERE link.capture_id = @CaptureId AND link.owner_profile_id = @ProfileId
                  AND source.owner_profile_id = @ProfileId AND source.source_type = N''photo''
                  AND source.state IN (N''confirmed'', N''deletion_pending'')
                  AND source.scan_result = N''clean'';
            END;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname = N'PS_CAPTURE_MEDIA_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreatePhotoSource'), (N'usp_MarkPhotoUploaded'),
        (N'usp_FailPhotoSource'), (N'usp_GetPhotoSourceForOwner'),
        (N'usp_GetPhotoProcessingSourceForOwner'), (N'usp_RecordPhotoScanResult'),
        (N'usp_CompletePhotoProcessing'), (N'usp_ConfirmPhotoCapture'),
        (N'usp_GetPhotoMediaForOwner'), (N'usp_BeginPhotoDraftDeletion'),
        (N'usp_FinalizePhotoDraftDeletion'), (N'usp_FinalizePhotoCaptureDeletion'),
        (N'usp_DeleteCapture'), (N'usp_ExportCaptureForOwner');
    DECLARE @ProtectedProcedureName sysname;
    DECLARE @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures ORDER BY procedure_name;
        SELECT @ProtectedProcedureHash = CONVERT
        (
            nvarchar(64),
            HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P'))),
            2
        );
        IF EXISTS
        (
            SELECT 1 FROM sys.extended_properties
            WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
              AND minor_id = 0 AND name = @ProcedureHashPropertyName
        )
            EXEC sys.sp_updateextendedproperty
                @name = @ProcedureHashPropertyName, @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = @ProcedureHashPropertyName, @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;
        DELETE @ProtectedProcedures WHERE procedure_name = @ProtectedProcedureName;
    END;

    IF NOT EXISTS
       (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-MEDIA-001')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-CAPTURE-MEDIA-001',
            N'Private Photo source scanning, safe derivative, explicit Capture confirmation, export, and deletion',
            N'PeerSlate Bible v2.6 and Roadmap v2.5'
        );
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration', @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-CAPTURE-MEDIA-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
