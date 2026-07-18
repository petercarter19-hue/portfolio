/* ============================================================
   PS-CAPTURE-002 - controlled private Capture lifecycle

   Adds immutable-original correction history, archive/restore,
   explicit aggregate deletion, optimistic concurrency, and
   owner-scoped per-capture export over PS-CAPTURE-001.

   Rollback: PS-CAPTURE-002_capture_lifecycle_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52100, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-AUTH-001'
    )
        THROW 52101, 'PS-AUTH-001 must be applied before PS-CAPTURE-002.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-001'
    )
        THROW 52102, 'PS-CAPTURE-001 must be applied before PS-CAPTURE-002.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NULL
       OR OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 52103, 'The Capture owner and audit foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.captures', N'body') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'active') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'deleted_at_utc') IS NULL
        THROW 52104, 'The PS-CAPTURE-001 table contract is incompatible.', 1;

    IF OBJECT_ID(N'dbo.capture_revisions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.capture_revisions
        (
            revision_id bigint IDENTITY(1,1) NOT NULL,
            revision_key uniqueidentifier NOT NULL
                CONSTRAINT DF_capture_revisions_key DEFAULT NEWSEQUENTIALID(),
            capture_id bigint NOT NULL,
            revision_number int NOT NULL,
            body nvarchar(max) NOT NULL,
            correction_note nvarchar(1000) NULL,
            corrected_by_user_id int NOT NULL,
            corrected_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_capture_revisions_corrected DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_capture_revisions PRIMARY KEY (revision_id),
            CONSTRAINT UQ_capture_revisions_key UNIQUE (revision_key),
            CONSTRAINT UQ_capture_revisions_capture_number
                UNIQUE (capture_id, revision_number),
            CONSTRAINT FK_capture_revisions_capture FOREIGN KEY (capture_id)
                REFERENCES dbo.captures(capture_id),
            CONSTRAINT FK_capture_revisions_actor FOREIGN KEY (corrected_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_capture_revisions_number CHECK (revision_number > 0),
            CONSTRAINT CK_capture_revisions_body_length CHECK
                (DATALENGTH(body) / 2 BETWEEN 1 AND 8000),
            CONSTRAINT CK_capture_revisions_note_length CHECK
                (correction_note IS NULL OR DATALENGTH(correction_note) / 2 <= 1000)
        );

        CREATE INDEX IX_capture_revisions_capture_latest
            ON dbo.capture_revisions(capture_id, revision_number DESC)
            INCLUDE (corrected_at_utc, corrected_by_user_id);
    END;

    IF COL_LENGTH(N'dbo.capture_revisions', N'capture_id') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'revision_number') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'body') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'corrected_by_user_id') IS NULL
        THROW 52105, 'Existing capture_revisions table is incompatible.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListCapturesForOwner
            @UserKey nvarchar(300),
            @Take int = 50,
            @Archived bit = 0
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL
                THROW 52106, ''Authenticated user key is required.'', 1;
            IF @Take IS NULL SET @Take = 50;
            IF @Take < 1 SET @Take = 1;
            IF @Take > 100 SET @Take = 100;
            IF @Archived IS NULL SET @Archived = 0;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52107, ''Authenticated owner profile not found.'', 1;

            SELECT TOP (@Take)
                capture.capture_key,
                capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body,
                capture.visibility,
                capture.status,
                capture.active,
                COALESCE(latest_revision.revision_number, 0) AS revision_number,
                revision_count.revision_count,
                capture.created_at_utc,
                capture.updated_at_utc,
                capture.row_version
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1)
                    revision.body,
                    revision.revision_number
                FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT COUNT(*) AS revision_count
                FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
            ) AS revision_count
            WHERE capture.owner_profile_id = @ProfileId
              AND capture.deleted_at_utc IS NULL
              AND
              (
                  (@Archived = 0 AND capture.active = 1 AND capture.status = N''captured'')
                  OR
                  (@Archived = 1 AND capture.active = 0 AND capture.status = N''archived'')
              )
            ORDER BY capture.updated_at_utc DESC, capture.capture_id DESC;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetCaptureForOwner
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            SELECT
                capture.capture_key,
                capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body,
                capture.visibility,
                capture.status,
                capture.active,
                COALESCE(latest_revision.revision_number, 0) AS revision_number,
                revision_count.revision_count,
                capture.created_at_utc,
                capture.updated_at_utc,
                capture.row_version
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT COUNT(*) AS revision_count
                FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
            ) AS revision_count
            WHERE capture.owner_profile_id = @ProfileId
              AND capture.capture_key = @CaptureKey
              AND capture.deleted_at_utc IS NULL
              AND
              (
                  (capture.active = 1 AND capture.status = N''captured'')
                  OR
                  (capture.active = 0 AND capture.status = N''archived'')
              );
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CorrectCapture
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @CorrectedBody nvarchar(max),
            @CorrectionNote nvarchar(1000) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @CorrectedBody = NULLIF(LTRIM(RTRIM(@CorrectedBody)), N'''');
            SET @CorrectionNote = NULLIF(LTRIM(RTRIM(@CorrectionNote)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52108, ''Owner, capture, and expected version are required.'', 1;
            IF @CorrectedBody IS NULL OR LEN
            (
                REPLACE(REPLACE(REPLACE(@CorrectedBody, NCHAR(9), N''''), NCHAR(10), N''''), NCHAR(13), N'''')
            ) = 0
                THROW 52109, ''Corrected capture body is required.'', 1;
            IF DATALENGTH(@CorrectedBody) / 2 > 8000
                THROW 52110, ''Corrected capture body exceeds 8000 characters.'', 1;
            IF @CorrectionNote IS NOT NULL AND DATALENGTH(@CorrectionNote) / 2 > 1000
                THROW 52111, ''Correction note exceeds 1000 characters.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT @CaptureId = capture.capture_id
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                WHERE capture.owner_profile_id = @ProfileId
                  AND capture.capture_key = @CaptureKey
                  AND capture.active = 1
                  AND capture.status = N''captured''
                  AND capture.deleted_at_utc IS NULL
                  AND capture.row_version = @ExpectedRowVersion;

                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''not_found_or_changed'' AS outcome,
                        CAST(NULL AS int) AS revision_number,
                        CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                DECLARE @RevisionNumber int;
                SELECT @RevisionNumber = COALESCE(MAX(revision.revision_number), 0) + 1
                FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = @CaptureId;

                INSERT dbo.capture_revisions
                (
                    capture_id, revision_number, body,
                    correction_note, corrected_by_user_id
                )
                VALUES
                (
                    @CaptureId, @RevisionNumber, @CorrectedBody,
                    @CorrectionNote, @UserId
                );

                UPDATE dbo.captures
                SET updated_at_utc = SYSUTCDATETIME()
                WHERE capture_id = @CaptureId;

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
                    N''{"revision_number":'', @RevisionNumber, N''}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.corrected'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    @RevisionNumber AS revision_number,
                    capture.row_version
                FROM dbo.captures AS capture
                WHERE capture.capture_id = @CaptureId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ArchiveCapture
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52112, ''Owner, capture, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT @CaptureId = capture.capture_id
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                WHERE capture.owner_profile_id = @ProfileId
                  AND capture.capture_key = @CaptureKey
                  AND capture.active = 1
                  AND capture.status = N''captured''
                  AND capture.deleted_at_utc IS NULL
                  AND capture.row_version = @ExpectedRowVersion;

                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''not_found_or_changed'' AS outcome,
                        CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                UPDATE dbo.captures
                SET
                    active = 0,
                    status = N''archived'',
                    updated_at_utc = SYSUTCDATETIME()
                WHERE capture_id = @CaptureId;

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
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.archived'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{"status":"archived"}'';

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, capture.row_version
                FROM dbo.captures AS capture
                WHERE capture.capture_id = @CaptureId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_RestoreCapture
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52113, ''Owner, capture, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT @CaptureId = capture.capture_id
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                WHERE capture.owner_profile_id = @ProfileId
                  AND capture.capture_key = @CaptureKey
                  AND capture.active = 0
                  AND capture.status = N''archived''
                  AND capture.deleted_at_utc IS NULL
                  AND capture.row_version = @ExpectedRowVersion;

                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''not_found_or_changed'' AS outcome,
                        CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                UPDATE dbo.captures
                SET
                    active = 1,
                    status = N''captured'',
                    updated_at_utc = SYSUTCDATETIME()
                WHERE capture_id = @CaptureId;

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
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.restored'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{"status":"captured"}'';

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, capture.row_version
                FROM dbo.captures AS capture
                WHERE capture.capture_id = @CaptureId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52114, ''Owner, capture, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                DECLARE @PreviousStatus nvarchar(30);
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT
                    @CaptureId = capture.capture_id,
                    @PreviousStatus = capture.status
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                WHERE capture.owner_profile_id = @ProfileId
                  AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL
                  AND capture.row_version = @ExpectedRowVersion
                  AND
                  (
                      (capture.active = 1 AND capture.status = N''captured'')
                      OR
                      (capture.active = 0 AND capture.status = N''archived'')
                  );

                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''not_found_or_changed'' AS outcome,
                        CAST(NULL AS int) AS deleted_revision_count;
                    RETURN;
                END;

                DECLARE @RevisionCount int =
                (
                    SELECT COUNT(*)
                    FROM dbo.capture_revisions AS revision
                    WHERE revision.capture_id = @CaptureId
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"previous_status":"'', @PreviousStatus,
                    N''","revision_count":'', @RevisionCount, N''}''
                );
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
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.deleted'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                DELETE dbo.capture_revisions
                WHERE capture_id = @CaptureId;

                DELETE dbo.captures
                WHERE capture_id = @CaptureId
                  AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT <> 1
                    THROW 52115, ''Capture delete did not complete atomically.'', 1;

                COMMIT TRANSACTION;

                SELECT
                    N''success'' AS outcome,
                    @RevisionCount AS deleted_revision_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ExportCaptureForOwner
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            DECLARE @ProfileId bigint;
            DECLARE @CaptureId bigint;
            IF @UserKey IS NOT NULL AND @CaptureKey IS NOT NULL
            BEGIN
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT @CaptureId = capture.capture_id
                FROM dbo.captures AS capture
                WHERE capture.owner_profile_id = @ProfileId
                  AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL
                  AND
                  (
                      (capture.active = 1 AND capture.status = N''captured'')
                      OR
                      (capture.active = 0 AND capture.status = N''archived'')
                  );
            END;

            SELECT
                capture.capture_key,
                capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body,
                capture.visibility,
                capture.status,
                capture.active,
                COALESCE(latest_revision.revision_number, 0) AS revision_number,
                capture.created_at_utc,
                capture.updated_at_utc,
                revisions.revisions_json
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT
                (
                    SELECT
                        revision.revision_number,
                        revision.body,
                        revision.correction_note,
                        revision.corrected_at_utc
                    FROM dbo.capture_revisions AS revision
                    WHERE revision.capture_id = capture.capture_id
                    ORDER BY revision.revision_number
                    FOR JSON PATH
                ) AS revisions_json
            ) AS revisions
            WHERE capture.capture_id = @CaptureId
              AND capture.owner_profile_id = @ProfileId;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-002'
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
            N'PS-CAPTURE-002',
            N'Owner-scoped Capture revisions, lifecycle, deletion, and export',
            N'PeerSlate Bible and Roadmap v2.3'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-CAPTURE-002"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
