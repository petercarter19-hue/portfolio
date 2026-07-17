/* ============================================================
   PS-CAPTURE-001 - Universal Capture, slice 1 (private text)

   REVIEW-FIRST MIGRATION. Apply only after explicit owner approval.

   A capture is the canonical private intake draft. Future Journal,
   Project, Story, Work, Resume, or Feed placement must reference the
   same capture/source record rather than copy its authoritative body.

   Rollback: PS-CAPTURE-001_captures_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52000, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id = N'PS-AUTH-001'
    )
        THROW 52001, 'PS-AUTH-001 must be applied before PS-CAPTURE-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 52002, 'The PeerSlate owner identity foundation is missing.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.captures
        (
            capture_id bigint IDENTITY(1,1) NOT NULL,
            capture_key uniqueidentifier NOT NULL
                CONSTRAINT DF_captures_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            capture_type nvarchar(30) NOT NULL
                CONSTRAINT DF_captures_type DEFAULT N'text',
            body nvarchar(max) NOT NULL,
            visibility nvarchar(30) NOT NULL
                CONSTRAINT DF_captures_visibility DEFAULT N'private',
            status nvarchar(30) NOT NULL
                CONSTRAINT DF_captures_status DEFAULT N'captured',
            active bit NOT NULL
                CONSTRAINT DF_captures_active DEFAULT 1,
            deleted_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_captures_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_captures_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_captures PRIMARY KEY (capture_id),
            CONSTRAINT UQ_captures_key UNIQUE (capture_key),
            CONSTRAINT FK_captures_owner_profile FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_captures_type CHECK
                (capture_type IN (N'text', N'voice', N'photo', N'video', N'document')),
            CONSTRAINT CK_captures_visibility CHECK
                (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_captures_status CHECK
                (status IN (N'captured', N'placed', N'archived')),
            CONSTRAINT CK_captures_deleted_state CHECK
                (deleted_at_utc IS NULL OR active = 0)
        );

        CREATE INDEX IX_captures_owner_created
            ON dbo.captures(owner_profile_id, created_at_utc DESC, capture_id DESC)
            INCLUDE (capture_key, capture_type, visibility, status, active)
            WHERE deleted_at_utc IS NULL;
    END;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CreateCapture
            @UserKey nvarchar(300),
            @CaptureType nvarchar(30),
            @Body nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @CaptureType = NULLIF(LTRIM(RTRIM(@CaptureType)), N'''');
            SET @Body = NULLIF(LTRIM(RTRIM(@Body)), N'''');

            IF @UserKey IS NULL
                THROW 52003, ''Authenticated user key is required.'', 1;
            IF @CaptureType NOT IN (N''text'', N''voice'', N''photo'', N''video'', N''document'')
                THROW 52004, ''Unsupported capture type.'', 1;
            IF @Body IS NULL OR LEN
            (
                REPLACE
                (
                    REPLACE(REPLACE(@Body, NCHAR(9), N''''), NCHAR(10), N''''),
                    NCHAR(13),
                    N''''
                )
            ) = 0
                THROW 52005, ''Capture body is required.'', 1;
            IF DATALENGTH(@Body) / 2 > 8000
                THROW 52006, ''Capture body exceeds 8000 characters.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                IF @ProfileId IS NULL OR @UserId IS NULL
                    THROW 52007, ''Authenticated owner profile not found.'', 1;

                INSERT dbo.captures
                (
                    owner_profile_id, capture_type, body,
                    visibility, status, active
                )
                VALUES
                (
                    @ProfileId, @CaptureType, @Body,
                    N''private'', N''captured'', 1
                );

                DECLARE @CaptureId bigint = CONVERT(bigint, SCOPE_IDENTITY());
                DECLARE @CaptureKey uniqueidentifier;
                SELECT @CaptureKey = capture_key
                FROM dbo.captures
                WHERE capture_id = @CaptureId
                  AND owner_profile_id = @ProfileId;

                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint,
                    event_key uniqueidentifier,
                    occurred_at_utc datetime2(7),
                    actor_user_id int,
                    actor_user_key_snapshot nvarchar(300),
                    action_type nvarchar(200),
                    entity_type nvarchar(100),
                    entity_key uniqueidentifier,
                    outcome nvarchar(30),
                    request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"capture_type":"'', @CaptureType,
                    N''","visibility":"private"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.created'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT
                    capture.capture_key,
                    capture.capture_type,
                    capture.body,
                    capture.visibility,
                    capture.status,
                    capture.created_at_utc,
                    capture.updated_at_utc
                FROM dbo.captures AS capture
                WHERE capture.capture_id = @CaptureId
                  AND capture.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListCapturesForOwner
            @UserKey nvarchar(300),
            @Take int = 50
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL
                THROW 52008, ''Authenticated user key is required.'', 1;
            IF @Take IS NULL SET @Take = 50;
            IF @Take < 1 SET @Take = 1;
            IF @Take > 100 SET @Take = 100;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52009, ''Authenticated owner profile not found.'', 1;

            SELECT TOP (@Take)
                capture.capture_key,
                capture.capture_type,
                capture.body,
                capture.visibility,
                capture.status,
                capture.created_at_utc,
                capture.updated_at_utc
            FROM dbo.captures AS capture
            WHERE capture.owner_profile_id = @ProfileId
              AND capture.active = 1
              AND capture.deleted_at_utc IS NULL
            ORDER BY capture.created_at_utc DESC, capture.capture_id DESC;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id,
            description,
            application_version
        )
        VALUES
        (
            N'PS-CAPTURE-001',
            N'Owner-isolated private Universal Capture text intake',
            N'PeerSlate Company and Product Bible v1.4'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-CAPTURE-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
