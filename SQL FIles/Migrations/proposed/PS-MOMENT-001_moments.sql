/* ============================================================
   PS-MOMENT-001 - private Capture review and Moment promotion

   Adds a member-reviewed canonical Moment layer while preserving
   one exact owner-scoped Capture source version. Confirmation is
   explicit and private. Capture deletion produces body-free source
   tombstones and never silently rewrites canonical Moment content.

   Rollback: PS-MOMENT-001_moments_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52200, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 52201, 'PS-AUTH-001 must be applied before PS-MOMENT-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-001')
        THROW 52202, 'PS-CAPTURE-001 must be applied before PS-MOMENT-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-002')
        THROW 52203, 'PS-CAPTURE-002 must be applied before PS-MOMENT-001.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NULL
       OR OBJECT_ID(N'dbo.capture_revisions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
       OR OBJECT_ID(N'dbo.usp_DeleteCapture', N'P') IS NULL
        THROW 52204, 'The Capture lifecycle, owner, or audit foundation is missing.', 1;

    IF OBJECT_ID(N'dbo.moments', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.moments
        (
            moment_id bigint IDENTITY(1,1) NOT NULL,
            moment_key uniqueidentifier NOT NULL
                CONSTRAINT DF_moments_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            visibility nvarchar(30) NOT NULL
                CONSTRAINT DF_moments_visibility DEFAULT N'private',
            status nvarchar(30) NOT NULL
                CONSTRAINT DF_moments_status DEFAULT N'proposal',
            current_version_number int NOT NULL
                CONSTRAINT DF_moments_current_version DEFAULT 1,
            confirmed_version_number int NULL,
            confirmed_by_user_id int NULL,
            confirmed_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moments_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moments_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_moments PRIMARY KEY (moment_id),
            CONSTRAINT UQ_moments_key UNIQUE (moment_key),
            CONSTRAINT FK_moments_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_moments_confirmer FOREIGN KEY (confirmed_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_moments_visibility CHECK (visibility = N'private'),
            CONSTRAINT CK_moments_status CHECK (status IN (N'proposal', N'confirmed')),
            CONSTRAINT CK_moments_current_version CHECK (current_version_number > 0),
            CONSTRAINT CK_moments_confirmation_state CHECK
            (
                (status = N'proposal'
                 AND confirmed_version_number IS NULL
                 AND confirmed_by_user_id IS NULL
                 AND confirmed_at_utc IS NULL)
                OR
                (status = N'confirmed'
                 AND confirmed_version_number = current_version_number
                 AND confirmed_by_user_id IS NOT NULL
                 AND confirmed_at_utc IS NOT NULL)
            )
        );

        CREATE INDEX IX_moments_owner_updated
            ON dbo.moments(owner_profile_id, updated_at_utc DESC, moment_id DESC)
            INCLUDE (moment_key, status, visibility, current_version_number);
    END;

    IF OBJECT_ID(N'dbo.moment_versions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.moment_versions
        (
            moment_version_id bigint IDENTITY(1,1) NOT NULL,
            moment_version_key uniqueidentifier NOT NULL
                CONSTRAINT DF_moment_versions_key DEFAULT NEWSEQUENTIALID(),
            moment_id bigint NOT NULL,
            version_number int NOT NULL,
            moment_kind nvarchar(30) NOT NULL
                CONSTRAINT DF_moment_versions_kind DEFAULT N'update',
            title nvarchar(160) NULL,
            occurred_on date NULL,
            occurred_precision nvarchar(20) NOT NULL
                CONSTRAINT DF_moment_versions_precision DEFAULT N'unknown',
            narrative nvarchar(max) NULL,
            why_it_matters nvarchar(2000) NULL,
            saved_by_user_id int NOT NULL,
            saved_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moment_versions_saved DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_moment_versions PRIMARY KEY (moment_version_id),
            CONSTRAINT UQ_moment_versions_key UNIQUE (moment_version_key),
            CONSTRAINT UQ_moment_versions_number UNIQUE (moment_id, version_number),
            CONSTRAINT FK_moment_versions_moment FOREIGN KEY (moment_id)
                REFERENCES dbo.moments(moment_id),
            CONSTRAINT FK_moment_versions_actor FOREIGN KEY (saved_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_moment_versions_number CHECK (version_number > 0),
            CONSTRAINT CK_moment_versions_kind CHECK
            (
                moment_kind IN
                (
                    N'achievement', N'decision', N'lesson', N'progress',
                    N'challenge', N'question', N'update', N'other'
                )
            ),
            CONSTRAINT CK_moment_versions_precision CHECK
                (occurred_precision IN (N'exact', N'month', N'year', N'unknown')),
            CONSTRAINT CK_moment_versions_date_state CHECK
            (
                (occurred_precision = N'unknown' AND occurred_on IS NULL)
                OR
                (occurred_precision <> N'unknown' AND occurred_on IS NOT NULL)
            ),
            CONSTRAINT CK_moment_versions_title_length CHECK
                (title IS NULL OR DATALENGTH(title) / 2 BETWEEN 1 AND 160),
            CONSTRAINT CK_moment_versions_narrative_length CHECK
                (narrative IS NULL OR DATALENGTH(narrative) / 2 BETWEEN 1 AND 8000),
            CONSTRAINT CK_moment_versions_why_length CHECK
                (why_it_matters IS NULL OR DATALENGTH(why_it_matters) / 2 <= 2000)
        );

        CREATE INDEX IX_moment_versions_current
            ON dbo.moment_versions(moment_id, version_number DESC)
            INCLUDE (moment_kind, occurred_on, occurred_precision, saved_at_utc);
    END;

    IF OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.moment_sources
        (
            moment_source_id bigint IDENTITY(1,1) NOT NULL,
            moment_source_key uniqueidentifier NOT NULL
                CONSTRAINT DF_moment_sources_key DEFAULT NEWSEQUENTIALID(),
            moment_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            capture_id bigint NULL,
            capture_revision_id bigint NULL,
            source_capture_key uniqueidentifier NOT NULL,
            source_revision_key uniqueidentifier NULL,
            source_revision_number int NOT NULL,
            source_state nvarchar(20) NOT NULL
                CONSTRAINT DF_moment_sources_state DEFAULT N'available',
            source_deleted_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moment_sources_created DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_moment_sources PRIMARY KEY (moment_source_id),
            CONSTRAINT UQ_moment_sources_key UNIQUE (moment_source_key),
            CONSTRAINT UQ_moment_sources_moment UNIQUE (moment_id),
            CONSTRAINT UQ_moment_sources_owner_version
                UNIQUE (owner_profile_id, source_capture_key, source_revision_number),
            CONSTRAINT FK_moment_sources_moment FOREIGN KEY (moment_id)
                REFERENCES dbo.moments(moment_id),
            CONSTRAINT FK_moment_sources_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_moment_sources_capture FOREIGN KEY (capture_id)
                REFERENCES dbo.captures(capture_id),
            CONSTRAINT FK_moment_sources_revision FOREIGN KEY (capture_revision_id)
                REFERENCES dbo.capture_revisions(revision_id),
            CONSTRAINT CK_moment_sources_revision_number CHECK (source_revision_number >= 0),
            CONSTRAINT CK_moment_sources_state CHECK
                (source_state IN (N'available', N'deleted')),
            CONSTRAINT CK_moment_sources_reference_state CHECK
            (
                (
                    source_state = N'available'
                    AND source_deleted_at_utc IS NULL
                    AND capture_id IS NOT NULL
                    AND
                    (
                        (source_revision_number = 0
                         AND capture_revision_id IS NULL
                         AND source_revision_key IS NULL)
                        OR
                        (source_revision_number > 0
                         AND capture_revision_id IS NOT NULL
                         AND source_revision_key IS NOT NULL)
                    )
                )
                OR
                (
                    source_state = N'deleted'
                    AND source_deleted_at_utc IS NOT NULL
                    AND capture_id IS NULL
                    AND capture_revision_id IS NULL
                )
            )
        );

        CREATE INDEX IX_moment_sources_capture
            ON dbo.moment_sources(capture_id, owner_profile_id, source_state)
            INCLUDE (moment_id, source_revision_number);
    END;

    IF COL_LENGTH(N'dbo.moments', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'narrative') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_state') IS NULL
        THROW 52205, 'Existing Moment tables are incompatible.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CreateOrReopenMomentProposal
            @UserKey nvarchar(300),
            @CaptureKey uniqueidentifier,
            @SourceRevisionNumber int
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL
               OR @SourceRevisionNumber IS NULL OR @SourceRevisionNumber < 0
                THROW 52206, ''Owner, Capture, and source version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                DECLARE @CaptureRevisionId bigint;
                DECLARE @CaptureRevisionKey uniqueidentifier;
                DECLARE @MomentId bigint;
                DECLARE @MomentKey uniqueidentifier;
                DECLARE @MomentStatus nvarchar(30);

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
                  AND capture.deleted_at_utc IS NULL;

                IF @SourceRevisionNumber > 0 AND @CaptureId IS NOT NULL
                BEGIN
                    SELECT
                        @CaptureRevisionId = revision.revision_id,
                        @CaptureRevisionKey = revision.revision_key
                    FROM dbo.capture_revisions AS revision
                    WHERE revision.capture_id = @CaptureId
                      AND revision.revision_number = @SourceRevisionNumber;
                END;

                IF @ProfileId IS NULL OR @UserId IS NULL OR @CaptureId IS NULL
                   OR (@SourceRevisionNumber > 0 AND @CaptureRevisionId IS NULL)
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''not_found_or_changed'' AS outcome,
                        CAST(NULL AS uniqueidentifier) AS moment_key,
                        CAST(NULL AS nvarchar(30)) AS status,
                        CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                SELECT
                    @MomentId = moment.moment_id,
                    @MomentKey = moment.moment_key,
                    @MomentStatus = moment.status
                FROM dbo.moment_sources AS source_link WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.moments AS moment ON moment.moment_id = source_link.moment_id
                WHERE source_link.owner_profile_id = @ProfileId
                  AND source_link.source_capture_key = @CaptureKey
                  AND source_link.source_revision_number = @SourceRevisionNumber;

                IF @MomentId IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''existing'' AS outcome,
                        moment.moment_key,
                        moment.status,
                        moment.row_version
                    FROM dbo.moments AS moment
                    WHERE moment.moment_id = @MomentId;
                    RETURN;
                END;

                INSERT dbo.moments (owner_profile_id, visibility, status)
                VALUES (@ProfileId, N''private'', N''proposal'');
                SET @MomentId = CONVERT(bigint, SCOPE_IDENTITY());

                INSERT dbo.moment_versions
                (
                    moment_id, version_number, moment_kind, title,
                    occurred_on, occurred_precision, narrative,
                    why_it_matters, saved_by_user_id
                )
                VALUES
                (
                    @MomentId, 1, N''update'', NULL,
                    NULL, N''unknown'', NULL, NULL, @UserId
                );

                INSERT dbo.moment_sources
                (
                    moment_id, owner_profile_id, capture_id, capture_revision_id,
                    source_capture_key, source_revision_key,
                    source_revision_number, source_state
                )
                VALUES
                (
                    @MomentId, @ProfileId, @CaptureId, @CaptureRevisionId,
                    @CaptureKey, @CaptureRevisionKey,
                    @SourceRevisionNumber, N''available''
                );

                SELECT @MomentKey = moment_key
                FROM dbo.moments WHERE moment_id = @MomentId;

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
                    N''{"source_revision_number":'', @SourceRevisionNumber,
                    N'',"visibility":"private"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''moment.proposal.created'',
                    @EntityType = N''moment'',
                    @EntityKey = @MomentKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT
                    N''created'' AS outcome,
                    moment.moment_key,
                    moment.status,
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

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetMomentForOwner
            @UserKey nvarchar(300),
            @MomentKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @MomentKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            SELECT
                moment.moment_key,
                moment.visibility,
                moment.status,
                moment.current_version_number,
                moment.confirmed_version_number,
                moment.confirmed_at_utc,
                moment.created_at_utc,
                moment.updated_at_utc,
                moment.row_version,
                version_record.moment_kind,
                version_record.title,
                version_record.occurred_on,
                version_record.occurred_precision,
                version_record.narrative,
                version_record.why_it_matters,
                source_link.moment_source_key,
                source_link.source_capture_key,
                source_link.source_revision_key,
                source_link.source_revision_number,
                source_link.source_state,
                source_link.source_deleted_at_utc,
                CASE
                    WHEN source_link.source_state = N''deleted'' THEN NULL
                    WHEN source_link.source_revision_number = 0 THEN capture.body
                    ELSE revision.body
                END AS source_body,
                COALESCE(latest_revision.latest_revision_number, 0)
                    AS latest_source_revision_number,
                CAST
                (
                    CASE
                        WHEN source_link.source_state = N''available''
                         AND COALESCE(latest_revision.latest_revision_number, 0)
                             > source_link.source_revision_number
                        THEN 1 ELSE 0
                    END AS bit
                ) AS newer_source_available,
                CAST
                (
                    CASE
                        WHEN moment.status = N''proposal''
                         AND source_link.source_state = N''available''
                         AND NULLIF(LTRIM(RTRIM(version_record.title)), N'''') IS NOT NULL
                         AND NULLIF(LTRIM(RTRIM(version_record.narrative)), N'''') IS NOT NULL
                        THEN 1 ELSE 0
                    END AS bit
                ) AS can_confirm
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
            LEFT JOIN dbo.capture_revisions AS revision
              ON revision.revision_id = source_link.capture_revision_id
             AND revision.capture_id = source_link.capture_id
            OUTER APPLY
            (
                SELECT MAX(all_revisions.revision_number) AS latest_revision_number
                FROM dbo.capture_revisions AS all_revisions
                WHERE all_revisions.capture_id = source_link.capture_id
            ) AS latest_revision
            WHERE moment.owner_profile_id = @ProfileId
              AND moment.moment_key = @MomentKey
              AND moment.visibility = N''private'';
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveMomentProposal
            @UserKey nvarchar(300),
            @MomentKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
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
            SET @MomentKind = NULLIF(LTRIM(RTRIM(@MomentKind)), N'''');
            SET @Title = NULLIF(LTRIM(RTRIM(@Title)), N'''');
            SET @OccurredPrecision = NULLIF(LTRIM(RTRIM(@OccurredPrecision)), N'''');
            SET @Narrative = NULLIF(LTRIM(RTRIM(@Narrative)), N'''');
            SET @WhyItMatters = NULLIF(LTRIM(RTRIM(@WhyItMatters)), N'''');

            IF @UserKey IS NULL OR @MomentKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52207, ''Owner, Moment, and expected version are required.'', 1;
            IF @MomentKind NOT IN
               (
                   N''achievement'', N''decision'', N''lesson'', N''progress'',
                   N''challenge'', N''question'', N''update'', N''other''
               )
                THROW 52208, ''Moment type is invalid.'', 1;
            IF @Title IS NULL OR @Narrative IS NULL
                THROW 52209, ''Moment title and narrative are required.'', 1;
            IF DATALENGTH(@Title) / 2 > 160
               OR DATALENGTH(@Narrative) / 2 > 8000
               OR (@WhyItMatters IS NOT NULL AND DATALENGTH(@WhyItMatters) / 2 > 2000)
                THROW 52210, ''One or more Moment fields exceeds its limit.'', 1;
            IF @OccurredPrecision NOT IN (N''exact'', N''month'', N''year'', N''unknown'')
                THROW 52211, ''Moment date precision is invalid.'', 1;
            IF @OccurredPrecision = N''unknown''
                SET @OccurredOn = NULL;
            ELSE IF @OccurredOn IS NULL
                THROW 52212, ''Moment date is required for the selected precision.'', 1;
            ELSE IF @OccurredPrecision = N''month''
                SET @OccurredOn = DATEFROMPARTS(YEAR(@OccurredOn), MONTH(@OccurredOn), 1);
            ELSE IF @OccurredPrecision = N''year''
                SET @OccurredOn = DATEFROMPARTS(YEAR(@OccurredOn), 1, 1);

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @MomentId bigint;
                DECLARE @CurrentVersionNumber int;
                DECLARE @SourceState nvarchar(20);
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT
                    @MomentId = moment.moment_id,
                    @CurrentVersionNumber = moment.current_version_number,
                    @SourceState = source_link.source_state
                FROM dbo.moments AS moment WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.moment_sources AS source_link WITH (UPDLOCK, HOLDLOCK)
                  ON source_link.moment_id = moment.moment_id
                 AND source_link.owner_profile_id = moment.owner_profile_id
                WHERE moment.owner_profile_id = @ProfileId
                  AND moment.moment_key = @MomentKey
                  AND moment.visibility = N''private''
                  AND moment.status = N''proposal''
                  AND moment.row_version = @ExpectedRowVersion;

                IF @MomentId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS int) AS version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF @SourceState = N''deleted''
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''source_deleted'' AS outcome,
                           @CurrentVersionNumber AS version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                DECLARE @NextVersionNumber int = @CurrentVersionNumber + 1;
                INSERT dbo.moment_versions
                (
                    moment_id, version_number, moment_kind, title,
                    occurred_on, occurred_precision, narrative,
                    why_it_matters, saved_by_user_id
                )
                VALUES
                (
                    @MomentId, @NextVersionNumber, @MomentKind, @Title,
                    @OccurredOn, @OccurredPrecision, @Narrative,
                    @WhyItMatters, @UserId
                );

                UPDATE dbo.moments
                SET current_version_number = @NextVersionNumber,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE moment_id = @MomentId;

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
                    N''{"proposal_version":'', @NextVersionNumber,
                    N'',"kind":"'', @MomentKind,
                    N''","occurred_precision":"'', @OccurredPrecision, N''"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''moment.proposal.saved'',
                    @EntityType = N''moment'',
                    @EntityKey = @MomentKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       @NextVersionNumber AS version_number,
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

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ConfirmMoment
            @UserKey nvarchar(300),
            @MomentKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @ExpectedProposalVersion int
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @MomentKey IS NULL
               OR @ExpectedRowVersion IS NULL
               OR @ExpectedProposalVersion IS NULL OR @ExpectedProposalVersion < 1
                THROW 52213, ''Owner, Moment, row version, and proposal version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @MomentId bigint;
                DECLARE @SourceState nvarchar(20);
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT
                    @MomentId = moment.moment_id,
                    @SourceState = source_link.source_state
                FROM dbo.moments AS moment WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.moment_sources AS source_link WITH (UPDLOCK, HOLDLOCK)
                  ON source_link.moment_id = moment.moment_id
                 AND source_link.owner_profile_id = moment.owner_profile_id
                WHERE moment.owner_profile_id = @ProfileId
                  AND moment.moment_key = @MomentKey
                  AND moment.visibility = N''private''
                  AND moment.status = N''proposal''
                  AND moment.current_version_number = @ExpectedProposalVersion
                  AND moment.row_version = @ExpectedRowVersion;

                IF @MomentId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS int) AS confirmed_version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF @SourceState = N''deleted''
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''source_deleted'' AS outcome,
                           CAST(NULL AS int) AS confirmed_version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF NOT EXISTS
                (
                    SELECT 1
                    FROM dbo.moment_versions AS version_record
                    WHERE version_record.moment_id = @MomentId
                      AND version_record.version_number = @ExpectedProposalVersion
                      AND NULLIF(LTRIM(RTRIM(version_record.title)), N'''') IS NOT NULL
                      AND NULLIF(LTRIM(RTRIM(version_record.narrative)), N'''') IS NOT NULL
                )
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS int) AS confirmed_version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                UPDATE dbo.moments
                SET status = N''confirmed'',
                    confirmed_version_number = @ExpectedProposalVersion,
                    confirmed_by_user_id = @UserId,
                    confirmed_at_utc = SYSUTCDATETIME(),
                    updated_at_utc = SYSUTCDATETIME()
                WHERE moment_id = @MomentId;

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
                    N''{"confirmed_proposal_version":'', @ExpectedProposalVersion,
                    N'',"visibility":"private"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''moment.confirmed'',
                    @EntityType = N''moment'',
                    @EntityKey = @MomentKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       @ExpectedProposalVersion AS confirmed_version_number,
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

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DiscardMomentProposal
            @UserKey nvarchar(300),
            @MomentKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @MomentKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52214, ''Owner, Moment, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @MomentId bigint;
                DECLARE @VersionCount int;
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT @MomentId = moment.moment_id
                FROM dbo.moments AS moment WITH (UPDLOCK, HOLDLOCK)
                WHERE moment.owner_profile_id = @ProfileId
                  AND moment.moment_key = @MomentKey
                  AND moment.visibility = N''private''
                  AND moment.status = N''proposal''
                  AND moment.row_version = @ExpectedRowVersion;

                IF @MomentId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS int) AS deleted_version_count;
                    RETURN;
                END;

                SELECT @VersionCount = COUNT(*)
                FROM dbo.moment_versions WHERE moment_id = @MomentId;

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
                    N''{"discarded_proposal_versions":'', @VersionCount, N''}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''moment.proposal.discarded'',
                    @EntityType = N''moment'',
                    @EntityKey = @MomentKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                DELETE dbo.moment_sources WHERE moment_id = @MomentId;
                DELETE dbo.moment_versions WHERE moment_id = @MomentId;
                DELETE dbo.moments
                WHERE moment_id = @MomentId AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT <> 1
                    THROW 52215, ''Moment proposal discard did not complete atomically.'', 1;

                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome,
                       @VersionCount AS deleted_version_count;
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
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count;
                    RETURN;
                END;

                DECLARE @RevisionCount int =
                (
                    SELECT COUNT(*) FROM dbo.capture_revisions
                    WHERE capture_id = @CaptureId
                );
                DECLARE @MomentSourceCount int =
                (
                    SELECT COUNT(*) FROM dbo.moment_sources
                    WHERE owner_profile_id = @ProfileId
                      AND capture_id = @CaptureId
                      AND source_state = N''available''
                );

                UPDATE dbo.moment_sources
                SET source_state = N''deleted'',
                    source_deleted_at_utc = SYSUTCDATETIME(),
                    capture_revision_id = NULL,
                    capture_id = NULL
                WHERE owner_profile_id = @ProfileId
                  AND capture_id = @CaptureId
                  AND source_state = N''available'';

                IF @@ROWCOUNT <> @MomentSourceCount
                    THROW 52216, ''Capture source tombstones were not updated atomically.'', 1;

                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"previous_status":"'', @PreviousStatus,
                    N''","revision_count":'', @RevisionCount,
                    N'',"moment_source_tombstone_count":'', @MomentSourceCount, N''}''
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
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.deleted'',
                    @EntityType = N''capture'',
                    @EntityKey = @CaptureKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                DELETE dbo.capture_revisions WHERE capture_id = @CaptureId;
                DELETE dbo.captures
                WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT <> 1
                    THROW 52115, ''Capture delete did not complete atomically.'', 1;

                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome,
                       @RevisionCount AS deleted_revision_count,
                       @MomentSourceCount AS tombstoned_moment_source_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_MOMENT_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreateOrReopenMomentProposal'),
        (N'usp_GetMomentForOwner'),
        (N'usp_SaveMomentProposal'),
        (N'usp_ConfirmMoment'),
        (N'usp_DiscardMomentProposal'),
        (N'usp_DeleteCapture');

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
        WHERE migration_id = N'PS-MOMENT-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-MOMENT-001',
            N'Private source-pinned Moment proposals and explicit confirmation',
            N'PeerSlate Bible and Roadmap v2.3'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-MOMENT-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
