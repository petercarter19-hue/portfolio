/* ============================================================
   PS-VOICE-001 - private Voice Capture, first slice

   REVIEW-FIRST MIGRATION. Apply only after explicit manager approval.
   The application stores original audio in private Blob Storage and
   stores immutable provider transcript provenance here.  A Capture is
   created only after explicit member confirmation.

   Rollback: PS-VOICE-001_voice_capture_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52400, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-002')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MOMENT-001')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLACEMENT-001')
        THROW 52401, 'The current Capture, Moment, and Placement baseline must be applied first.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NULL
       OR OBJECT_ID(N'dbo.capture_revisions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 52402, 'The owner, Capture, Moment, or audit contract is missing.', 1;

    IF OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.voice_media_sources
        (
            source_id bigint IDENTITY(1,1) NOT NULL,
            source_key uniqueidentifier NOT NULL
                CONSTRAINT DF_voice_media_sources_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            blob_name nvarchar(160) NULL,
            content_type nvarchar(40) NULL,
            byte_length bigint NULL,
            sha256_digest binary(32) NULL,
            locale nvarchar(10) NULL,
            client_duration_milliseconds int NULL,
            verified_duration_milliseconds int NULL,
            state nvarchar(30) NOT NULL
                CONSTRAINT DF_voice_media_sources_state DEFAULT N'uploading',
            safe_error_code nvarchar(60) NULL,
            deletion_capture_row_version binary(8) NULL,
            created_by_user_id int NOT NULL,
            deleted_by_user_id int NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_voice_media_sources_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_voice_media_sources_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_voice_media_sources PRIMARY KEY (source_id),
            CONSTRAINT UQ_voice_media_sources_key UNIQUE (source_key),
            CONSTRAINT FK_voice_media_sources_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_voice_media_sources_creator FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_voice_media_sources_deleter FOREIGN KEY (deleted_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_voice_media_sources_state CHECK
            (
                state IN
                (
                    N'uploading', N'queued', N'processing', N'needs_review',
                    N'confirmed', N'failed', N'deletion_pending', N'deleted'
                )
            ),
            CONSTRAINT CK_voice_media_sources_live_payload CHECK
            (
                (
                    state <> N'deleted'
                    AND blob_name IS NOT NULL
                    AND blob_name LIKE N'voice/v1/%'
                    AND content_type IN
                    (
                        N'audio/webm', N'audio/ogg', N'audio/wav',
                        N'audio/mp4', N'audio/mpeg', N'audio/aac'
                    )
                    AND byte_length BETWEEN 1 AND 20971520
                    AND sha256_digest IS NOT NULL
                    AND locale = N'en-US'
                    AND client_duration_milliseconds BETWEEN 1 AND 180000
                    AND deleted_at_utc IS NULL
                )
                OR
                (
                    state = N'deleted'
                    AND blob_name IS NULL
                    AND content_type IS NULL
                    AND byte_length IS NULL
                    AND sha256_digest IS NULL
                    AND locale IS NULL
                    AND client_duration_milliseconds IS NULL
                    AND verified_duration_milliseconds IS NULL
                    AND safe_error_code IS NULL
                    AND deletion_capture_row_version IS NULL
                    AND deleted_at_utc IS NOT NULL
                )
            ),
            CONSTRAINT CK_voice_media_sources_verified_duration CHECK
            (
                verified_duration_milliseconds IS NULL
                OR verified_duration_milliseconds BETWEEN 1 AND 180000
            )
        );

        CREATE INDEX IX_voice_media_sources_owner_state
            ON dbo.voice_media_sources(owner_profile_id, state, updated_at_utc DESC)
            INCLUDE (source_key, content_type, byte_length, locale);
    END;

    IF EXISTS
    (
        SELECT 1 FROM sys.key_constraints
        WHERE parent_object_id = OBJECT_ID(N'dbo.voice_media_sources')
          AND name = N'UQ_voice_media_sources_blob'
    )
        ALTER TABLE dbo.voice_media_sources DROP CONSTRAINT UQ_voice_media_sources_blob;
    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.voice_media_sources')
          AND name = N'UX_voice_media_sources_live_blob'
    )
        CREATE UNIQUE INDEX UX_voice_media_sources_live_blob
            ON dbo.voice_media_sources(blob_name)
            WHERE blob_name IS NOT NULL;

    IF OBJECT_ID(N'dbo.voice_transcription_attempts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.voice_transcription_attempts
        (
            attempt_id bigint IDENTITY(1,1) NOT NULL,
            attempt_key uniqueidentifier NOT NULL
                CONSTRAINT DF_voice_transcription_attempts_key DEFAULT NEWSEQUENTIALID(),
            source_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            attempt_number int NOT NULL,
            state nvarchar(20) NOT NULL,
            provider_request_id nvarchar(100) NULL,
            provider_transcript nvarchar(max) NULL,
            safe_error_code nvarchar(60) NULL,
            queued_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_voice_transcription_attempts_queued DEFAULT SYSUTCDATETIME(),
            started_at_utc datetime2(7) NULL,
            completed_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_voice_transcription_attempts PRIMARY KEY (attempt_id),
            CONSTRAINT UQ_voice_transcription_attempts_key UNIQUE (attempt_key),
            CONSTRAINT UQ_voice_transcription_attempts_source_number
                UNIQUE (source_id, attempt_number),
            CONSTRAINT FK_voice_transcription_attempts_source FOREIGN KEY (source_id)
                REFERENCES dbo.voice_media_sources(source_id),
            CONSTRAINT FK_voice_transcription_attempts_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_voice_transcription_attempts_number CHECK (attempt_number > 0),
            CONSTRAINT CK_voice_transcription_attempts_state CHECK
                (state IN (N'queued', N'processing', N'succeeded', N'failed')),
            CONSTRAINT CK_voice_transcription_attempts_result CHECK
            (
                (
                    state = N'succeeded'
                    AND provider_transcript IS NOT NULL
                    AND DATALENGTH(provider_transcript) / 2 BETWEEN 1 AND 8000
                    AND safe_error_code IS NULL
                    AND completed_at_utc IS NOT NULL
                )
                OR
                (
                    state = N'failed'
                    AND provider_transcript IS NULL
                    AND safe_error_code IS NOT NULL
                    AND completed_at_utc IS NOT NULL
                )
                OR
                (
                    state IN (N'queued', N'processing')
                    AND provider_transcript IS NULL
                    AND safe_error_code IS NULL
                    AND completed_at_utc IS NULL
                )
            )
        );

        CREATE INDEX IX_voice_transcription_attempts_source_latest
            ON dbo.voice_transcription_attempts(source_id, attempt_number DESC)
            INCLUDE (state, completed_at_utc);
    END;

    IF OBJECT_ID(N'dbo.voice_capture_links', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.voice_capture_links
        (
            voice_capture_link_id bigint IDENTITY(1,1) NOT NULL,
            source_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            capture_id bigint NOT NULL,
            successful_attempt_id bigint NOT NULL,
            confirmed_by_user_id int NOT NULL,
            confirmed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_voice_capture_links_confirmed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_voice_capture_links PRIMARY KEY (voice_capture_link_id),
            CONSTRAINT UQ_voice_capture_links_source UNIQUE (source_id),
            CONSTRAINT UQ_voice_capture_links_capture UNIQUE (capture_id),
            CONSTRAINT UQ_voice_capture_links_attempt UNIQUE (successful_attempt_id),
            CONSTRAINT FK_voice_capture_links_source FOREIGN KEY (source_id)
                REFERENCES dbo.voice_media_sources(source_id),
            CONSTRAINT FK_voice_capture_links_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_voice_capture_links_capture FOREIGN KEY (capture_id)
                REFERENCES dbo.captures(capture_id),
            CONSTRAINT FK_voice_capture_links_attempt FOREIGN KEY (successful_attempt_id)
                REFERENCES dbo.voice_transcription_attempts(attempt_id),
            CONSTRAINT FK_voice_capture_links_actor FOREIGN KEY (confirmed_by_user_id)
                REFERENCES dbo.app_users(id)
        );
    END;

    IF COL_LENGTH(N'dbo.voice_media_sources', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'provider_transcript') IS NULL
       OR COL_LENGTH(N'dbo.voice_capture_links', N'successful_attempt_id') IS NULL
        THROW 52403, 'Existing Voice Capture tables are incompatible.', 1;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_voice_transcription_attempts_immutable_result
        ON dbo.voice_transcription_attempts
        AFTER UPDATE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS
            (
                SELECT 1
                FROM inserted AS new_value
                JOIN deleted AS old_value ON old_value.attempt_id = new_value.attempt_id
                WHERE old_value.provider_transcript IS NOT NULL
                  AND
                  (
                      ISNULL(new_value.provider_transcript, NCHAR(0)) <>
                          ISNULL(old_value.provider_transcript, NCHAR(0))
                      OR ISNULL(new_value.provider_request_id, NCHAR(0)) <>
                          ISNULL(old_value.provider_request_id, NCHAR(0))
                  )
            )
                THROW 52404, ''Provider transcript provenance is immutable.'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CreateVoiceDraft
            @UserKey nvarchar(300),
            @BlobName nvarchar(160),
            @ContentType nvarchar(40),
            @ByteLength bigint,
            @Sha256Digest binary(32),
            @Locale nvarchar(10),
            @ClientDurationMilliseconds int
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @BlobName = NULLIF(LTRIM(RTRIM(@BlobName)), N'''');
            IF @UserKey IS NULL OR @BlobName IS NULL OR @Sha256Digest IS NULL
                THROW 52405, ''Voice owner and validated media are required.'', 1;
            IF @BlobName NOT LIKE N''voice/v1/%'' OR LEN(@BlobName) > 160
                THROW 52406, ''Voice media locator is invalid.'', 1;
            IF @ContentType NOT IN
               (N''audio/webm'', N''audio/ogg'', N''audio/wav'', N''audio/mp4'', N''audio/mpeg'', N''audio/aac'')
               OR @ByteLength NOT BETWEEN 1 AND 20971520
               OR @Locale <> N''en-US''
               OR @ClientDurationMilliseconds NOT BETWEEN 1 AND 180000
                THROW 52407, ''Voice media contract is invalid.'', 1;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL OR @UserId IS NULL
                THROW 52408, ''Authenticated owner profile not found.'', 1;

            INSERT dbo.voice_media_sources
            (
                owner_profile_id, blob_name, content_type, byte_length,
                sha256_digest, locale, client_duration_milliseconds,
                state, created_by_user_id
            )
            VALUES
            (
                @ProfileId, @BlobName, @ContentType, @ByteLength,
                @Sha256Digest, @Locale, @ClientDurationMilliseconds,
                N''uploading'', @UserId
            );
            DECLARE @SourceId bigint = CONVERT(bigint, SCOPE_IDENTITY());
            DECLARE @SourceKey uniqueidentifier;
            SELECT @SourceKey = source_key FROM dbo.voice_media_sources WHERE source_id = @SourceId;

            DECLARE @AuditMetadata nvarchar(max) = CONCAT
            (
                N''{"state":"uploading","byte_count":'', @ByteLength,
                N'',"duration_ms":'', @ClientDurationMilliseconds,
                N'',"locale":"en-US"}''
            );
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
                @ActorUserId = @UserId,
                @ActorUserKeySnapshot = @UserKey,
                @ActionType = N''voice.draft.created'',
                @EntityType = N''voice_source'',
                @EntityKey = @SourceKey,
                @Outcome = N''success'',
                @MetadataJson = @AuditMetadata;

            SELECT N''created'' AS outcome, source_key, blob_name, row_version
            FROM dbo.voice_media_sources
            WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FailVoiceUpload
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @SafeErrorCode nvarchar(60)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52409, ''Owner, source, and expected version are required.'', 1;
            IF @SafeErrorCode NOT IN (N''storage_unavailable'', N''storage_rejected'')
                SET @SafeErrorCode = N''storage_unavailable'';
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            UPDATE dbo.voice_media_sources
            SET state = N''failed'', safe_error_code = @SafeErrorCode,
                updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey
              AND state = N''uploading'' AND row_version = @ExpectedRowVersion;
            IF @@ROWCOUNT <> 1
            BEGIN
                SELECT N''not_found_or_changed'' AS outcome;
                RETURN;
            END;
            SELECT N''failed'' AS outcome, row_version
            FROM dbo.voice_media_sources
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_QueueVoiceTranscription
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52410, ''Owner, source, and expected version are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @SourceId bigint;
                DECLARE @SourceState nvarchar(30);
                DECLARE @AttemptNumber int;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id, @SourceState = source.state
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId
                  AND source.source_key = @SourceKey
                  AND source.row_version = @ExpectedRowVersion
                  AND
                  (
                      source.state = N''uploading''
                      OR source.state IN (N''queued'', N''processing'')
                      OR
                      (
                          source.state = N''failed''
                          AND EXISTS
                          (
                              SELECT 1 FROM dbo.voice_transcription_attempts AS prior_attempt
                              WHERE prior_attempt.source_id = source.source_id
                          )
                      )
                  );
                IF @SourceId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome;
                    RETURN;
                END;
                IF @SourceState IN (N''queued'', N''processing'')
                BEGIN
                    UPDATE dbo.voice_transcription_attempts
                    SET state = N''failed'', safe_error_code = N''recovery_retry'',
                        started_at_utc = COALESCE(started_at_utc, SYSUTCDATETIME()),
                        completed_at_utc = SYSUTCDATETIME()
                    WHERE source_id = @SourceId AND owner_profile_id = @ProfileId
                      AND state IN (N''queued'', N''processing'');
                END;
                SELECT @AttemptNumber = ISNULL(MAX(attempt_number), 0) + 1
                FROM dbo.voice_transcription_attempts WITH (UPDLOCK, HOLDLOCK)
                WHERE source_id = @SourceId;
                INSERT dbo.voice_transcription_attempts
                    (source_id, owner_profile_id, attempt_number, state)
                VALUES (@SourceId, @ProfileId, @AttemptNumber, N''queued'');
                UPDATE dbo.voice_media_sources
                SET state = N''queued'', safe_error_code = NULL,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                COMMIT TRANSACTION;
                SELECT N''queued'' AS outcome, source.source_key, source.blob_name,
                       source.content_type, @AttemptNumber AS attempt_number,
                       source.row_version
                FROM dbo.voice_media_sources AS source
                WHERE source.source_id = @SourceId AND source.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_MarkVoiceTranscriptionProcessing
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @AttemptNumber int,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF NULLIF(LTRIM(RTRIM(@UserKey)), N'''') IS NULL
               OR @SourceKey IS NULL OR @AttemptNumber IS NULL
               OR @ExpectedRowVersion IS NULL
                THROW 52417, ''Owner, source, attempt, and expected version are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @SourceId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.state = N''queued''
                  AND source.row_version = @ExpectedRowVersion;
                UPDATE dbo.voice_transcription_attempts
                SET state = N''processing'', started_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId
                  AND attempt_number = @AttemptNumber AND state = N''queued'';
                IF @@ROWCOUNT <> 1
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome;
                    RETURN;
                END;
                UPDATE dbo.voice_media_sources
                SET state = N''processing'', updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                COMMIT TRANSACTION;
                SELECT N''processing'' AS outcome, row_version
                FROM dbo.voice_media_sources
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CompleteVoiceTranscription
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @AttemptNumber int,
            @ExpectedRowVersion binary(8),
            @ProviderTranscript nvarchar(max),
            @ProviderRequestId nvarchar(100) = NULL,
            @VerifiedDurationMilliseconds int = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @ProviderTranscript = NULLIF(LTRIM(RTRIM(@ProviderTranscript)), N'''');
            SET @ProviderRequestId = NULLIF(LTRIM(RTRIM(@ProviderRequestId)), N'''');
            IF @ProviderTranscript IS NULL OR DATALENGTH(@ProviderTranscript) / 2 > 8000
                THROW 52411, ''Provider transcript is required and must fit the Capture limit.'', 1;
            IF @ProviderRequestId IS NOT NULL AND LEN(@ProviderRequestId) > 100
                THROW 52412, ''Provider request identifier is invalid.'', 1;
            IF @VerifiedDurationMilliseconds IS NULL
               OR @VerifiedDurationMilliseconds NOT BETWEEN 1 AND 180000
                THROW 52413, ''Verified duration exceeds the Voice limit.'', 1;
            IF NULLIF(LTRIM(RTRIM(@UserKey)), N'''') IS NULL
               OR @SourceKey IS NULL OR @AttemptNumber IS NULL
               OR @ExpectedRowVersion IS NULL
                THROW 52418, ''Owner, source, attempt, and expected version are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @SourceId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.state = N''processing''
                  AND source.row_version = @ExpectedRowVersion;
                UPDATE dbo.voice_transcription_attempts
                SET state = N''succeeded'', provider_request_id = @ProviderRequestId,
                    provider_transcript = @ProviderTranscript,
                    completed_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId
                  AND attempt_number = @AttemptNumber AND state = N''processing'';
                IF @@ROWCOUNT <> 1
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome;
                    RETURN;
                END;
                UPDATE dbo.voice_media_sources
                SET state = N''needs_review'', safe_error_code = NULL,
                    verified_duration_milliseconds = @VerifiedDurationMilliseconds,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                COMMIT TRANSACTION;
                SELECT N''needs_review'' AS outcome, source_key, row_version
                FROM dbo.voice_media_sources
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FailVoiceTranscription
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @AttemptNumber int,
            @SafeErrorCode nvarchar(60)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @SafeErrorCode NOT IN
               (N''speech_timeout'', N''speech_unavailable'', N''speech_auth_failed'',
                N''speech_busy'', N''speech_failed'', N''speech_malformed'',
                N''speech_empty'', N''speech_too_long'', N''speech_duration_exceeded'')
                SET @SafeErrorCode = N''speech_failed'';
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @SourceId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.state IN (N''queued'', N''processing'');
                UPDATE dbo.voice_transcription_attempts
                SET state = N''failed'', safe_error_code = @SafeErrorCode,
                    started_at_utc = COALESCE(started_at_utc, SYSUTCDATETIME()),
                    completed_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId
                  AND attempt_number = @AttemptNumber AND state IN (N''queued'', N''processing'');
                IF @@ROWCOUNT <> 1
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome;
                    RETURN;
                END;
                UPDATE dbo.voice_media_sources
                SET state = N''failed'', safe_error_code = @SafeErrorCode,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                COMMIT TRANSACTION;
                SELECT N''failed'' AS outcome, row_version
                FROM dbo.voice_media_sources
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetVoiceDraftForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier
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
            SELECT source.source_key, source.state, source.content_type,
                   source.byte_length, source.locale,
                   source.client_duration_milliseconds,
                   source.verified_duration_milliseconds,
                   latest_attempt.attempt_number,
                   latest_attempt.provider_transcript,
                   source.safe_error_code, capture.capture_key,
                   source.created_at_utc, source.updated_at_utc,
                   source.row_version
            FROM dbo.voice_media_sources AS source
            OUTER APPLY
            (
                SELECT TOP (1) attempt.attempt_number, attempt.provider_transcript
                FROM dbo.voice_transcription_attempts AS attempt
                WHERE attempt.source_id = source.source_id
                ORDER BY attempt.attempt_number DESC
            ) AS latest_attempt
            LEFT JOIN dbo.voice_capture_links AS link ON link.source_id = source.source_id
            LEFT JOIN dbo.captures AS capture ON capture.capture_id = link.capture_id
            WHERE source.owner_profile_id = @ProfileId
              AND source.source_key = @SourceKey
              AND source.state <> N''deleted'';
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetVoiceMediaForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier
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
            SELECT source.source_key, source.blob_name, source.content_type,
                   source.byte_length, source.sha256_digest
            FROM dbo.voice_media_sources AS source
            WHERE source.owner_profile_id = @ProfileId
              AND source.source_key = @SourceKey
              AND source.state IN (N''needs_review'', N''confirmed'', N''failed'');
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ConfirmVoiceCapture
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @ApprovedBody nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @ApprovedBody = NULLIF(LTRIM(RTRIM(@ApprovedBody)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
               OR @ApprovedBody IS NULL OR DATALENGTH(@ApprovedBody) / 2 > 8000
                THROW 52414, ''Owner, source version, and approved body are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @SourceId bigint;
                DECLARE @AttemptId bigint;
                DECLARE @CaptureId bigint;
                DECLARE @CaptureKey uniqueidentifier;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;

                SELECT @CaptureId = link.capture_id, @SourceId = link.source_id
                FROM dbo.voice_capture_links AS link WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.voice_media_sources AS source ON source.source_id = link.source_id
                WHERE link.owner_profile_id = @ProfileId AND source.source_key = @SourceKey;
                IF @CaptureId IS NOT NULL
                BEGIN
                    SELECT @CaptureKey = capture_key FROM dbo.captures WHERE capture_id = @CaptureId;
                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome, @CaptureKey AS capture_key;
                    RETURN;
                END;

                SELECT @SourceId = source.source_id
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.state = N''needs_review'' AND source.row_version = @ExpectedRowVersion;
                SELECT TOP (1) @AttemptId = attempt.attempt_id
                FROM dbo.voice_transcription_attempts AS attempt
                WHERE attempt.source_id = @SourceId AND attempt.owner_profile_id = @ProfileId
                  AND attempt.state = N''succeeded'' AND attempt.provider_transcript IS NOT NULL
                ORDER BY attempt.attempt_number DESC;
                IF @SourceId IS NULL OR @AttemptId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome, CAST(NULL AS uniqueidentifier) AS capture_key;
                    RETURN;
                END;

                INSERT dbo.captures
                    (owner_profile_id, capture_type, body, visibility, status, active)
                VALUES (@ProfileId, N''voice'', @ApprovedBody, N''private'', N''captured'', 1);
                SET @CaptureId = CONVERT(bigint, SCOPE_IDENTITY());
                SELECT @CaptureKey = capture_key FROM dbo.captures WHERE capture_id = @CaptureId;
                INSERT dbo.voice_capture_links
                    (source_id, owner_profile_id, capture_id, successful_attempt_id, confirmed_by_user_id)
                VALUES (@SourceId, @ProfileId, @CaptureId, @AttemptId, @UserId);
                UPDATE dbo.voice_media_sources
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
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''voice.capture.confirmed'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{"capture_type":"voice","visibility":"private"}'';
                COMMIT TRANSACTION;
                SELECT N''created'' AS outcome, @CaptureKey AS capture_key;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                IF ERROR_NUMBER() IN (2601, 2627)
                BEGIN
                    SELECT @CaptureKey = capture.capture_key
                    FROM dbo.voice_capture_links AS link
                    JOIN dbo.voice_media_sources AS source ON source.source_id = link.source_id
                    JOIN dbo.captures AS capture ON capture.capture_id = link.capture_id
                    WHERE link.owner_profile_id = @ProfileId AND source.source_key = @SourceKey;
                    IF @CaptureKey IS NOT NULL
                    BEGIN
                        SELECT N''existing'' AS outcome, @CaptureKey AS capture_key;
                        RETURN;
                    END;
                END;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_BeginVoiceDraftDeletion
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
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
            FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
            WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
              AND source.state <> N''confirmed'' AND source.state <> N''deleted''
              AND source.row_version = @ExpectedRowVersion
              AND NOT EXISTS
                  (SELECT 1 FROM dbo.voice_capture_links AS link WHERE link.source_id = source.source_id);
            IF @SourceId IS NULL OR @UserId IS NULL
            BEGIN
                SELECT N''not_found_or_changed'' AS outcome;
                RETURN;
            END;
            UPDATE dbo.voice_media_sources
            SET state = N''deletion_pending'', safe_error_code = NULL,
                deleted_by_user_id = @UserId, updated_at_utc = SYSUTCDATETIME()
            WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
            SELECT N''pending'' AS outcome, source_key, blob_name,
                   row_version AS deletion_token
            FROM dbo.voice_media_sources
            WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FinalizeVoiceDraftDeletion
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
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
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.state = N''deletion_pending''
                  AND source.row_version = @ExpectedDeletionRowVersion
                  AND NOT EXISTS
                      (SELECT 1 FROM dbo.voice_capture_links AS link WHERE link.source_id = source.source_id);
                IF @SourceId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome;
                    RETURN;
                END;
                DELETE dbo.voice_transcription_attempts
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                UPDATE dbo.voice_media_sources
                SET blob_name = NULL, content_type = NULL, byte_length = NULL,
                    sha256_digest = NULL, locale = NULL,
                    client_duration_milliseconds = NULL,
                    verified_duration_milliseconds = NULL,
                    state = N''deleted'', safe_error_code = NULL,
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
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''voice.draft.deleted'',
                    @EntityType = N''voice_source'',
                    @EntityKey = @SourceKey,
                    @Outcome = N''success'',
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

    /* Voice-aware list/get preserve the PS-CAPTURE-002 result contract and add source state. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListCapturesForOwner
            @UserKey nvarchar(300), @Take int = 50, @Archived bit = 0
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL THROW 52106, ''Authenticated user key is required.'', 1;
            IF @Take IS NULL SET @Take = 50;
            IF @Take < 1 SET @Take = 1;
            IF @Take > 100 SET @Take = 100;
            IF @Archived IS NULL SET @Archived = 0;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52107, ''Authenticated owner profile not found.'', 1;
            SELECT TOP (@Take)
                capture.capture_key, capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body, capture.visibility, capture.status,
                capture.active, COALESCE(latest_revision.revision_number, 0) AS revision_number,
                revision_count.revision_count, capture.created_at_utc, capture.updated_at_utc,
                capture.row_version
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT COUNT(*) AS revision_count FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
            ) AS revision_count
            WHERE capture.owner_profile_id = @ProfileId AND capture.deleted_at_utc IS NULL
              AND ((@Archived = 0 AND capture.active = 1 AND capture.status = N''captured'')
                OR (@Archived = 1 AND capture.active = 0 AND capture.status = N''archived''))
            ORDER BY capture.updated_at_utc DESC, capture.capture_id DESC;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetCaptureForOwner
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT capture.capture_key, capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body, capture.visibility, capture.status,
                capture.active, COALESCE(latest_revision.revision_number, 0) AS revision_number,
                revision_count.revision_count, capture.created_at_utc, capture.updated_at_utc,
                capture.row_version
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT COUNT(*) AS revision_count FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
            ) AS revision_count
            WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
              AND capture.deleted_at_utc IS NULL
              AND ((capture.active = 1 AND capture.status = N''captured'')
                OR (capture.active = 0 AND capture.status = N''archived''));
        END;
    ');

    /* Text Captures finish immediately; Voice Captures enter deletion_pending first. */
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
                DECLARE @SourceId bigint;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @CaptureId = capture.capture_id, @PreviousStatus = capture.status,
                       @SourceId = voice_link.source_id
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                LEFT JOIN dbo.voice_capture_links AS voice_link ON voice_link.capture_id = capture.capture_id
                WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL AND capture.row_version = @ExpectedRowVersion
                  AND ((capture.active = 1 AND capture.status = N''captured'')
                    OR (capture.active = 0 AND capture.status = N''archived''));
                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS source_key,
                           CAST(NULL AS nvarchar(160)) AS blob_name,
                           CAST(NULL AS binary(8)) AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count;
                    RETURN;
                END;
                IF @SourceId IS NOT NULL
                BEGIN
                    UPDATE dbo.voice_media_sources
                    SET state = N''deletion_pending'', safe_error_code = NULL,
                        deletion_capture_row_version = @ExpectedRowVersion,
                        deleted_by_user_id = @UserId, updated_at_utc = SYSUTCDATETIME()
                    WHERE source_id = @SourceId AND owner_profile_id = @ProfileId
                      AND state IN (N''confirmed'', N''deletion_pending'');
                    IF @@ROWCOUNT <> 1 THROW 52415, ''Voice deletion state is invalid.'', 1;
                    COMMIT TRANSACTION;
                    SELECT N''pending'' AS outcome, source_key, blob_name,
                           row_version AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count
                    FROM dbo.voice_media_sources
                    WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
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
                       CAST(NULL AS uniqueidentifier) AS source_key,
                       CAST(NULL AS nvarchar(160)) AS blob_name,
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
        CREATE OR ALTER PROCEDURE dbo.usp_FinalizeVoiceCaptureDeletion
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
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
                FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @SourceId = source.source_id, @CaptureId = link.capture_id,
                       @CaptureKey = capture.capture_key
                FROM dbo.voice_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.voice_capture_links AS link ON link.source_id = source.source_id
                JOIN dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK) ON capture.capture_id = link.capture_id
                WHERE source.owner_profile_id = @ProfileId AND source.source_key = @SourceKey
                  AND source.state = N''deletion_pending''
                  AND source.row_version = @ExpectedDeletionRowVersion
                  AND link.owner_profile_id = @ProfileId
                  AND capture.owner_profile_id = @ProfileId
                  AND capture.row_version = source.deletion_capture_row_version;
                IF @SourceId IS NULL OR @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome;
                    RETURN;
                END;
                SELECT @RevisionCount = COUNT(*) FROM dbo.capture_revisions WHERE capture_id = @CaptureId;
                SELECT @MomentSourceCount = COUNT(*) FROM dbo.moment_sources
                WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId AND source_state = N''available'';
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
                    @MetadataJson = N''{"capture_type":"voice","source_state":"deleted"}'';
                DELETE dbo.capture_revisions WHERE capture_id = @CaptureId;
                DELETE dbo.voice_capture_links
                WHERE source_id = @SourceId AND capture_id = @CaptureId AND owner_profile_id = @ProfileId;
                DELETE dbo.captures WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId;
                IF @@ROWCOUNT <> 1 THROW 52416, ''Voice Capture deletion did not complete atomically.'', 1;
                DELETE dbo.voice_transcription_attempts
                WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
                UPDATE dbo.voice_media_sources
                SET blob_name = NULL, content_type = NULL, byte_length = NULL,
                    sha256_digest = NULL, locale = NULL,
                    client_duration_milliseconds = NULL,
                    verified_duration_milliseconds = NULL,
                    state = N''deleted'', safe_error_code = NULL,
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
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT @CaptureId = capture.capture_id
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

            IF EXISTS
            (
                SELECT 1 FROM dbo.voice_capture_links
                WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId
            )
            BEGIN
                SELECT source.source_key, source.content_type, source.byte_length,
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
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname = N'PS_VOICE_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreateVoiceDraft'), (N'usp_FailVoiceUpload'),
        (N'usp_QueueVoiceTranscription'), (N'usp_MarkVoiceTranscriptionProcessing'),
        (N'usp_CompleteVoiceTranscription'), (N'usp_FailVoiceTranscription'),
        (N'usp_GetVoiceDraftForOwner'), (N'usp_GetVoiceMediaForOwner'),
        (N'usp_ConfirmVoiceCapture'), (N'usp_BeginVoiceDraftDeletion'),
        (N'usp_FinalizeVoiceDraftDeletion'), (N'usp_FinalizeVoiceCaptureDeletion'),
        (N'usp_ListCapturesForOwner'), (N'usp_GetCaptureForOwner'),
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

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-VOICE-001')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-VOICE-001',
            N'Private Voice source, immutable transcription review, Capture confirmation, and deletion lifecycle',
            N'PeerSlate Bible and Roadmap v2.3'
        );
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-VOICE-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
