/* ============================================================
   PS-JOURNAL-001 (Slice J1) - derived private Journal read and
   one-step Save Moment

   Adds no journal_entry table and copies no Moment body. The Journal
   is a derived read over the existing private confirmed Moment/source
   tables (PS-MOMENT-001). Save Moment is a single idempotent commit
   that creates exactly one Capture source and one confirmed canonical
   Moment first version in one transaction - no separate Add to
   Journal step, no publish, no placement, no audience broadening.
   New Moments default to private/Only Me, matching the existing
   CK_moments_visibility constraint.

   REVIEW-FIRST MIGRATION. Proposed only; not applied by this task.
   The feature stays behind PEERSLATE_JOURNAL_ENABLED (default false)
   until this script and its rollback/verification pass an explicit
   migration gate.

   Rollback: PS-JOURNAL-001_journal_reads_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52700, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 52701, 'PS-AUTH-001 must be applied before PS-JOURNAL-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-001')
        THROW 52702, 'PS-CAPTURE-001 must be applied before PS-JOURNAL-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MOMENT-001')
        THROW 52703, 'PS-MOMENT-001 must be applied before PS-JOURNAL-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.captures', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moments', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 52704, 'The owner, Capture, Moment, or audit foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.moments', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'narrative') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_state') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'capture_type') IS NULL
        THROW 52705, 'Existing Capture or Moment tables are incompatible.', 1;

    /* ------------------------------------------------------------
       Additive, guarded lifecycle columns on the existing private
       moments table only. No visibility, status, or content column
       is touched; existing rows resolve to lifecycle_state = active.
       ------------------------------------------------------------ */
    IF COL_LENGTH(N'dbo.moments', N'archived_at_utc') IS NULL
        ALTER TABLE dbo.moments ADD archived_at_utc datetime2(7) NULL;

    IF COL_LENGTH(N'dbo.moments', N'archived_by_user_id') IS NULL
        ALTER TABLE dbo.moments ADD archived_by_user_id int NULL;

    IF NOT EXISTS
       (
           SELECT 1 FROM sys.foreign_keys
           WHERE name = N'FK_moments_archived_by'
             AND parent_object_id = OBJECT_ID(N'dbo.moments')
       )
        ALTER TABLE dbo.moments
            ADD CONSTRAINT FK_moments_archived_by FOREIGN KEY (archived_by_user_id)
                REFERENCES dbo.app_users(id);

    IF NOT EXISTS
       (
           SELECT 1 FROM sys.check_constraints
           WHERE name = N'CK_moments_archive_pair'
             AND parent_object_id = OBJECT_ID(N'dbo.moments')
       )
        ALTER TABLE dbo.moments
            ADD CONSTRAINT CK_moments_archive_pair CHECK
            (
                (archived_at_utc IS NULL AND archived_by_user_id IS NULL)
                OR
                (archived_at_utc IS NOT NULL AND archived_by_user_id IS NOT NULL)
            );

    /* ------------------------------------------------------------
       Idempotency ledger for one-step Save Moment. Holds only an
       owner-scoped replay key and the resulting Moment reference -
       no title, narrative, or other content. Not a second body
       table: it stores no Moment/Capture content of its own.
       ------------------------------------------------------------ */
    IF OBJECT_ID(N'dbo.moment_save_requests', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.moment_save_requests
        (
            moment_save_request_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            idempotency_key nvarchar(200) NOT NULL,
            moment_id bigint NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moment_save_requests_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_moment_save_requests PRIMARY KEY (moment_save_request_id),
            CONSTRAINT UQ_moment_save_requests_owner_key
                UNIQUE (owner_profile_id, idempotency_key),
            CONSTRAINT FK_moment_save_requests_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_moment_save_requests_moment FOREIGN KEY (moment_id)
                REFERENCES dbo.moments(moment_id)
        );

        CREATE INDEX IX_moment_save_requests_moment
            ON dbo.moment_save_requests(moment_id);
    END;

    IF COL_LENGTH(N'dbo.moment_save_requests', N'idempotency_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_save_requests', N'moment_id') IS NULL
        THROW 52706, 'Existing Moment save-request ledger is incompatible.', 1;

    /* ------------------------------------------------------------
       Stored procedures. Application access goes ONLY through these
       (services/database_service.py's allowlist pattern).
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListJournalMomentsForOwner
            @UserKey nvarchar(300),
            @IncludeArchived bit = 0,
            @Limit int = 50,
            @Cursor nvarchar(400) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;
            IF @IncludeArchived IS NULL SET @IncludeArchived = 0;
            IF @Limit IS NULL SET @Limit = 50;
            IF @Limit < 1 SET @Limit = 1;
            IF @Limit > 100 SET @Limit = 100;
            SET @Cursor = NULLIF(LTRIM(RTRIM(@Cursor)), N'''');

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @CursorDisplayAtUtc datetime2(7) = NULL;
            DECLARE @CursorMomentId bigint = NULL;
            IF @Cursor IS NOT NULL
            BEGIN
                DECLARE @DelimiterPos int = CHARINDEX(N''|'', @Cursor);
                IF @DelimiterPos > 1
                BEGIN
                    DECLARE @CursorDisplayPart nvarchar(40) = LEFT(@Cursor, @DelimiterPos - 1);
                    DECLARE @CursorIdPart nvarchar(40) =
                        SUBSTRING(@Cursor, @DelimiterPos + 1, 40);
                    SET @CursorDisplayAtUtc =
                        TRY_CONVERT(datetime2(7), @CursorDisplayPart, 126);
                    SET @CursorMomentId = TRY_CONVERT(bigint, @CursorIdPart);
                END;
                /* An unparsable cursor is treated as an owner-visible input
                   error, not a silent full re-list: return nothing rather
                   than guess a position. */
                IF @CursorDisplayAtUtc IS NULL OR @CursorMomentId IS NULL RETURN;
            END;

            SELECT TOP (@Limit)
                moment.moment_key,
                version_record.moment_kind,
                version_record.title,
                version_record.occurred_on,
                version_record.occurred_precision,
                moment.visibility,
                capture.capture_type AS source_type,
                CASE
                    WHEN moment.archived_at_utc IS NOT NULL THEN N''archived''
                    ELSE N''active''
                END AS lifecycle_state,
                moment.current_version_number AS version_number,
                CONCAT
                (
                    CONVERT(nvarchar(33), display.display_at_utc, 126),
                    N''|'', moment.moment_id
                ) AS cursor_token
            FROM dbo.moments AS moment
            JOIN dbo.moment_versions AS version_record
              ON version_record.moment_id = moment.moment_id
             AND version_record.version_number = moment.current_version_number
            JOIN dbo.moment_sources AS source_link
              ON source_link.moment_id = moment.moment_id
             AND source_link.owner_profile_id = moment.owner_profile_id
            LEFT JOIN dbo.captures AS capture
              ON capture.capture_id = source_link.capture_id
             AND capture.owner_profile_id = moment.owner_profile_id
            CROSS APPLY
            (
                SELECT CASE
                    WHEN version_record.occurred_precision = N''unknown''
                         OR version_record.occurred_on IS NULL
                        THEN moment.confirmed_at_utc
                    ELSE CAST(version_record.occurred_on AS datetime2(7))
                END AS display_at_utc
            ) AS display
            WHERE moment.owner_profile_id = @ProfileId
              AND moment.visibility = N''private''
              AND moment.status = N''confirmed''
              AND (@IncludeArchived = 1 OR moment.archived_at_utc IS NULL)
              AND
              (
                  @CursorDisplayAtUtc IS NULL
                  OR display.display_at_utc < @CursorDisplayAtUtc
                  OR
                  (
                      display.display_at_utc = @CursorDisplayAtUtc
                      AND moment.moment_id < @CursorMomentId
                  )
              )
            ORDER BY display.display_at_utc DESC, moment.moment_id DESC;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveMomentForOwner
            @UserKey nvarchar(300),
            @IdempotencyKey nvarchar(200),
            @MomentKind nvarchar(30),
            @Title nvarchar(160),
            @OccurredOn date = NULL,
            @OccurredPrecision nvarchar(20),
            @Narrative nvarchar(max),
            @WhyItMatters nvarchar(2000) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @IdempotencyKey = NULLIF(LTRIM(RTRIM(@IdempotencyKey)), N'''');
            SET @MomentKind = NULLIF(LTRIM(RTRIM(@MomentKind)), N'''');
            SET @Title = NULLIF(LTRIM(RTRIM(@Title)), N'''');
            SET @OccurredPrecision = NULLIF(LTRIM(RTRIM(@OccurredPrecision)), N'''');
            SET @Narrative = NULLIF(LTRIM(RTRIM(@Narrative)), N'''');
            SET @WhyItMatters = NULLIF(LTRIM(RTRIM(@WhyItMatters)), N'''');

            IF @UserKey IS NULL OR @IdempotencyKey IS NULL
                THROW 52707, ''Owner and idempotency key are required.'', 1;
            IF LEN(@IdempotencyKey) > 200
                THROW 52708, ''Idempotency key exceeds its limit.'', 1;
            IF @MomentKind NOT IN
               (
                   N''achievement'', N''decision'', N''lesson'', N''progress'',
                   N''challenge'', N''question'', N''update'', N''other''
               )
                THROW 52709, ''Moment type is invalid.'', 1;
            IF @Title IS NULL OR @Narrative IS NULL
                THROW 52710, ''Moment title and narrative are required.'', 1;
            IF DATALENGTH(@Title) / 2 > 160
               OR DATALENGTH(@Narrative) / 2 > 8000
               OR (@WhyItMatters IS NOT NULL AND DATALENGTH(@WhyItMatters) / 2 > 2000)
                THROW 52711, ''One or more Moment fields exceeds its limit.'', 1;
            IF @OccurredPrecision NOT IN (N''exact'', N''month'', N''year'', N''unknown'')
                THROW 52712, ''Moment date precision is invalid.'', 1;
            IF @OccurredPrecision = N''unknown''
                SET @OccurredOn = NULL;
            ELSE IF @OccurredOn IS NULL
                THROW 52713, ''Moment date is required for the selected precision.'', 1;
            ELSE IF @OccurredPrecision = N''month''
                SET @OccurredOn = DATEFROMPARTS(YEAR(@OccurredOn), MONTH(@OccurredOn), 1);
            ELSE IF @OccurredPrecision = N''year''
                SET @OccurredOn = DATEFROMPARTS(YEAR(@OccurredOn), 1, 1);

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
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS moment_key,
                           CAST(NULL AS int) AS version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                /* Idempotent replay: a repeated key for this owner always
                   returns the SAME Moment, never a second one. The range
                   lock on the unique (owner, key) index serializes any
                   concurrent replay of the same key. */
                DECLARE @ExistingMomentId bigint;
                SELECT @ExistingMomentId = request.moment_id
                FROM dbo.moment_save_requests AS request
                     WITH (UPDLOCK, HOLDLOCK, INDEX(UQ_moment_save_requests_owner_key))
                WHERE request.owner_profile_id = @ProfileId
                  AND request.idempotency_key = @IdempotencyKey;

                IF @ExistingMomentId IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome,
                           moment.moment_key,
                           moment.current_version_number AS version_number,
                           moment.row_version
                    FROM dbo.moments AS moment
                    WHERE moment.moment_id = @ExistingMomentId
                      AND moment.owner_profile_id = @ProfileId;
                    RETURN;
                END;

                /* One Capture source, reusing the existing private Capture
                   table exactly as usp_CreateCapture would - no parallel
                   content store. */
                INSERT dbo.captures
                (
                    owner_profile_id, capture_type, body,
                    visibility, status, active
                )
                VALUES
                (
                    @ProfileId, N''text'', @Narrative,
                    N''private'', N''captured'', 1
                );
                DECLARE @CaptureId bigint = CONVERT(bigint, SCOPE_IDENTITY());
                DECLARE @CaptureKey uniqueidentifier;
                SELECT @CaptureKey = capture_key
                FROM dbo.captures
                WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId;

                /* One confirmed canonical Moment, first version, created and
                   confirmed together - there is no separate proposal step
                   for a direct Save Moment. Visibility stays private and
                   nothing is placed or published. */
                INSERT dbo.moments
                (
                    owner_profile_id, visibility, status,
                    current_version_number, confirmed_version_number,
                    confirmed_by_user_id, confirmed_at_utc
                )
                VALUES
                (
                    @ProfileId, N''private'', N''confirmed'',
                    1, 1,
                    @UserId, SYSUTCDATETIME()
                );
                DECLARE @MomentId bigint = CONVERT(bigint, SCOPE_IDENTITY());
                DECLARE @MomentKey uniqueidentifier;
                SELECT @MomentKey = moment_key
                FROM dbo.moments WHERE moment_id = @MomentId;

                INSERT dbo.moment_versions
                (
                    moment_id, version_number, moment_kind, title,
                    occurred_on, occurred_precision, narrative,
                    why_it_matters, saved_by_user_id
                )
                VALUES
                (
                    @MomentId, 1, @MomentKind, @Title,
                    @OccurredOn, @OccurredPrecision, @Narrative,
                    @WhyItMatters, @UserId
                );

                INSERT dbo.moment_sources
                (
                    moment_id, owner_profile_id, capture_id, capture_revision_id,
                    source_capture_key, source_revision_key,
                    source_revision_number, source_state
                )
                VALUES
                (
                    @MomentId, @ProfileId, @CaptureId, NULL,
                    @CaptureKey, NULL,
                    0, N''available''
                );

                INSERT dbo.moment_save_requests
                (
                    owner_profile_id, idempotency_key, moment_id
                )
                VALUES
                (
                    @ProfileId, @IdempotencyKey, @MomentId
                );

                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"kind":"'', @MomentKind,
                    N''","occurred_precision":"'', @OccurredPrecision,
                    N''","visibility":"private"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''journal.moment.saved'',
                    @EntityType = N''moment'',
                    @EntityKey = @MomentKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       @MomentKey AS moment_key,
                       1 AS version_number,
                       moment.row_version
                FROM dbo.moments AS moment
                WHERE moment.moment_id = @MomentId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_JOURNAL_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_ListJournalMomentsForOwner'),
        (N'usp_SaveMomentForOwner');

    DECLARE @ProtectedProcedureName sysname;
    DECLARE @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures
        ORDER BY procedure_name;

        SELECT @ProtectedProcedureHash = CONVERT
        (
            nvarchar(64),
            HASHBYTES
            (
                'SHA2_256',
                OBJECT_DEFINITION
                (
                    OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
                )
            ),
            2
        );

        IF EXISTS
        (
            SELECT 1
            FROM sys.extended_properties AS property
            WHERE property.class = 1
              AND property.major_id =
                  OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
              AND property.minor_id = 0
              AND property.name = @ProcedureHashPropertyName
        )
            EXEC sys.sp_updateextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;

        DELETE @ProtectedProcedures
        WHERE procedure_name = @ProtectedProcedureName;
    END;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-JOURNAL-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-JOURNAL-001',
            N'Slice J1: derived private Journal read and one-step idempotent Save Moment',
            N'PeerSlate Bible and Roadmap v2.7'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-JOURNAL-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
