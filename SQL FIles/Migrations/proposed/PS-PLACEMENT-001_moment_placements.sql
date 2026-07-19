/* ============================================================
   PS-PLACEMENT-001 - private confirmed-Moment placement references

   Adds one body-free, lifecycle-aware reference from one exact
   confirmed Moment version to one existing owner-owned private,
   approved, unpublished Slate destination. No destination, audience,
   access, publication, or downstream content is created or changed.

   Rollback: PS-PLACEMENT-001_moment_placements_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52300, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002')
        THROW 52301, 'PS-PLAT-002 must be applied before PS-PLACEMENT-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-005')
        THROW 52302, 'PS-PLAT-005 must be applied before PS-PLACEMENT-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MOMENT-001')
        THROW 52303, 'PS-MOMENT-001 must be applied before PS-PLACEMENT-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moments', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.slate_entities', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 52304, 'The owner, Moment, destination, or audit foundation is missing.', 1;

    IF NOT EXISTS
       (
           SELECT 1 FROM sys.key_constraints
           WHERE parent_object_id = OBJECT_ID(N'dbo.moment_versions')
             AND name = N'UQ_moment_versions_number'
       )
        THROW 52305, 'The exact Moment-version key is missing.', 1;

    IF NOT EXISTS
       (
           SELECT 1 FROM sys.key_constraints
           WHERE parent_object_id = OBJECT_ID(N'dbo.slate_entities')
             AND name = N'UQ_slate_entities_id_owner'
       )
        THROW 52306, 'The tenant-safe Slate destination key is missing.', 1;

    IF NOT EXISTS
       (
           SELECT 1 FROM sys.key_constraints
           WHERE parent_object_id = OBJECT_ID(N'dbo.moments')
             AND name = N'UQ_moments_id_owner'
       )
        ALTER TABLE dbo.moments
            ADD CONSTRAINT UQ_moments_id_owner
                UNIQUE (moment_id, owner_profile_id);

    IF OBJECT_ID(N'dbo.moment_placements', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.moment_placements
        (
            placement_id bigint IDENTITY(1,1) NOT NULL,
            placement_key uniqueidentifier NOT NULL
                CONSTRAINT DF_moment_placements_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            moment_id bigint NOT NULL,
            moment_version_number int NOT NULL,
            target_entity_id bigint NOT NULL,
            placement_status nvarchar(20) NOT NULL
                CONSTRAINT DF_moment_placements_status DEFAULT N'active',
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moment_placements_created DEFAULT SYSUTCDATETIME(),
            reactivated_by_user_id int NULL,
            reactivated_at_utc datetime2(7) NULL,
            removed_by_user_id int NULL,
            removed_at_utc datetime2(7) NULL,
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_moment_placements_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_moment_placements PRIMARY KEY (placement_id),
            CONSTRAINT UQ_moment_placements_key UNIQUE (placement_key),
            CONSTRAINT UQ_moment_placements_logical UNIQUE
            (
                owner_profile_id,
                moment_id,
                moment_version_number,
                target_entity_id
            ),
            CONSTRAINT FK_moment_placements_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_moment_placements_moment_owner
                FOREIGN KEY (moment_id, owner_profile_id)
                REFERENCES dbo.moments(moment_id, owner_profile_id),
            CONSTRAINT FK_moment_placements_exact_version
                FOREIGN KEY (moment_id, moment_version_number)
                REFERENCES dbo.moment_versions(moment_id, version_number),
            CONSTRAINT FK_moment_placements_target_owner
                FOREIGN KEY (target_entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT FK_moment_placements_creator FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_moment_placements_reactivator FOREIGN KEY (reactivated_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_moment_placements_remover FOREIGN KEY (removed_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_moment_placements_version CHECK (moment_version_number > 0),
            CONSTRAINT CK_moment_placements_status
                CHECK (placement_status IN (N'active', N'removed')),
            CONSTRAINT CK_moment_placements_reactivation_pair CHECK
            (
                (reactivated_by_user_id IS NULL AND reactivated_at_utc IS NULL)
                OR
                (reactivated_by_user_id IS NOT NULL AND reactivated_at_utc IS NOT NULL)
            ),
            CONSTRAINT CK_moment_placements_removal_state CHECK
            (
                (placement_status = N'active'
                 AND removed_by_user_id IS NULL
                 AND removed_at_utc IS NULL)
                OR
                (placement_status = N'removed'
                 AND removed_by_user_id IS NOT NULL
                 AND removed_at_utc IS NOT NULL)
            )
        );

        CREATE INDEX IX_moment_placements_owner_status
            ON dbo.moment_placements
               (owner_profile_id, placement_status, updated_at_utc DESC, placement_id DESC)
            INCLUDE (placement_key, moment_id, moment_version_number, target_entity_id);
    END;

    IF COL_LENGTH(N'dbo.moment_placements', N'placement_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'moment_version_number') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'target_entity_id') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'placement_status') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'row_version') IS NULL
        THROW 52307, 'Existing Moment placement table is incompatible.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CreateOrReactivateMomentPlacement
            @UserKey nvarchar(300),
            @MomentKey uniqueidentifier,
            @TargetEntityKey uniqueidentifier,
            @ExpectedMomentRowVersion binary(8),
            @ExpectedPlacementRowVersion binary(8) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @MomentKey IS NULL
               OR @TargetEntityKey IS NULL OR @ExpectedMomentRowVersion IS NULL
                THROW 52310, ''Owner, Moment, destination, and expected Moment version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @MomentId bigint;
                DECLARE @MomentStatus nvarchar(30);
                DECLARE @MomentVisibility nvarchar(30);
                DECLARE @ConfirmedVersionNumber int;
                DECLARE @MomentRowVersion binary(8);
                DECLARE @TargetEntityId bigint;
                DECLARE @TargetVisibility nvarchar(30);
                DECLARE @TargetApprovalStatus nvarchar(30);
                DECLARE @TargetPublicationStatus nvarchar(30);
                DECLARE @TargetActive bit;
                DECLARE @TargetDeletedAtUtc datetime2(7);
                DECLARE @PlacementId bigint;
                DECLARE @PlacementKey uniqueidentifier;
                DECLARE @PlacementStatus nvarchar(20);
                DECLARE @PlacementRowVersion binary(8);

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
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           CAST(NULL AS uniqueidentifier) AS moment_key,
                           CAST(NULL AS int) AS moment_version_number,
                           CAST(NULL AS uniqueidentifier) AS target_entity_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                SELECT
                    @MomentId = moment.moment_id,
                    @MomentStatus = moment.status,
                    @MomentVisibility = moment.visibility,
                    @ConfirmedVersionNumber = moment.confirmed_version_number,
                    @MomentRowVersion = moment.row_version
                FROM dbo.moments AS moment WITH (UPDLOCK, HOLDLOCK)
                WHERE moment.owner_profile_id = @ProfileId
                  AND moment.moment_key = @MomentKey;

                IF @MomentId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           CAST(NULL AS uniqueidentifier) AS moment_key,
                           CAST(NULL AS int) AS moment_version_number,
                           CAST(NULL AS uniqueidentifier) AS target_entity_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF @MomentRowVersion <> @ExpectedMomentRowVersion
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''stale'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           @MomentKey AS moment_key,
                           @ConfirmedVersionNumber AS moment_version_number,
                           @TargetEntityKey AS target_entity_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF @MomentStatus <> N''confirmed''
                   OR @MomentVisibility <> N''private''
                   OR @ConfirmedVersionNumber IS NULL
                   OR NOT EXISTS
                      (
                          SELECT 1
                          FROM dbo.moment_versions AS version_record WITH (HOLDLOCK)
                          WHERE version_record.moment_id = @MomentId
                            AND version_record.version_number = @ConfirmedVersionNumber
                      )
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_confirmed'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           @MomentKey AS moment_key,
                           @ConfirmedVersionNumber AS moment_version_number,
                           @TargetEntityKey AS target_entity_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                SELECT
                    @TargetEntityId = target.entity_id,
                    @TargetVisibility = target.visibility,
                    @TargetApprovalStatus = target.approval_status,
                    @TargetPublicationStatus = target.publication_status,
                    @TargetActive = target.active,
                    @TargetDeletedAtUtc = target.deleted_at_utc
                FROM dbo.slate_entities AS target WITH (UPDLOCK, HOLDLOCK)
                WHERE target.owner_profile_id = @ProfileId
                  AND target.entity_key = @TargetEntityKey;

                IF @TargetEntityId IS NULL
                   OR @TargetVisibility <> N''private''
                   OR @TargetApprovalStatus <> N''approved''
                   OR @TargetPublicationStatus <> N''unpublished''
                   OR @TargetActive <> 1
                   OR @TargetDeletedAtUtc IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''target_unavailable'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           @MomentKey AS moment_key,
                           @ConfirmedVersionNumber AS moment_version_number,
                           @TargetEntityKey AS target_entity_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                SELECT
                    @PlacementId = placement.placement_id,
                    @PlacementKey = placement.placement_key,
                    @PlacementStatus = placement.placement_status,
                    @PlacementRowVersion = placement.row_version
                FROM dbo.moment_placements AS placement
                     WITH (UPDLOCK, HOLDLOCK, INDEX(UQ_moment_placements_logical))
                WHERE placement.owner_profile_id = @ProfileId
                  AND placement.moment_id = @MomentId
                  AND placement.moment_version_number = @ConfirmedVersionNumber
                  AND placement.target_entity_id = @TargetEntityId;

                IF @PlacementId IS NOT NULL AND @PlacementStatus = N''active''
                BEGIN
                    IF @ExpectedPlacementRowVersion IS NOT NULL
                       AND @ExpectedPlacementRowVersion <> @PlacementRowVersion
                    BEGIN
                        COMMIT TRANSACTION;
                        SELECT N''stale'' AS outcome,
                               @PlacementKey AS placement_key,
                               @MomentKey AS moment_key,
                               @ConfirmedVersionNumber AS moment_version_number,
                               @TargetEntityKey AS target_entity_key,
                               @PlacementStatus AS placement_status,
                               CAST(NULL AS binary(8)) AS row_version;
                        RETURN;
                    END;

                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome,
                           @PlacementKey AS placement_key,
                           @MomentKey AS moment_key,
                           @ConfirmedVersionNumber AS moment_version_number,
                           @TargetEntityKey AS target_entity_key,
                           @PlacementStatus AS placement_status,
                           @PlacementRowVersion AS row_version;
                    RETURN;
                END;

                IF @PlacementId IS NOT NULL AND @PlacementStatus = N''removed''
                BEGIN
                    IF @ExpectedPlacementRowVersion IS NULL
                       OR @ExpectedPlacementRowVersion <> @PlacementRowVersion
                    BEGIN
                        COMMIT TRANSACTION;
                        SELECT N''stale'' AS outcome,
                               @PlacementKey AS placement_key,
                               @MomentKey AS moment_key,
                               @ConfirmedVersionNumber AS moment_version_number,
                               @TargetEntityKey AS target_entity_key,
                               @PlacementStatus AS placement_status,
                               CAST(NULL AS binary(8)) AS row_version;
                        RETURN;
                    END;

                    UPDATE dbo.moment_placements
                    SET placement_status = N''active'',
                        reactivated_by_user_id = @UserId,
                        reactivated_at_utc = SYSUTCDATETIME(),
                        removed_by_user_id = NULL,
                        removed_at_utc = NULL,
                        updated_at_utc = SYSUTCDATETIME()
                    WHERE placement_id = @PlacementId
                      AND row_version = @ExpectedPlacementRowVersion;

                    IF @@ROWCOUNT <> 1
                        THROW 52311, ''Moment placement reactivation lost its concurrency boundary.'', 1;

                    DECLARE @ReactivationAuditResult TABLE
                    (
                        audit_event_id bigint, event_key uniqueidentifier,
                        occurred_at_utc datetime2(7), actor_user_id int,
                        actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                        entity_type nvarchar(100), entity_key uniqueidentifier,
                        outcome nvarchar(30), request_id nvarchar(100),
                        metadata_json nvarchar(max)
                    );
                    DECLARE @ReactivationMetadata nvarchar(max) = CONCAT
                    (
                        N''{"moment_version_number":'', @ConfirmedVersionNumber,
                        N'',"placement_status":"active"}''
                    );
                    INSERT @ReactivationAuditResult
                    EXEC dbo.usp_AppendAuditEvent
                        @ActorUserId = @UserId,
                        @ActorUserKeySnapshot = @UserKey,
                        @ActionType = N''moment.placement.reactivated'',
                        @EntityType = N''moment_placement'',
                        @EntityKey = @PlacementKey,
                        @Outcome = N''success'',
                        @MetadataJson = @ReactivationMetadata;

                    SELECT
                        @PlacementStatus = placement_status,
                        @PlacementRowVersion = row_version
                    FROM dbo.moment_placements
                    WHERE placement_id = @PlacementId;

                    COMMIT TRANSACTION;
                    SELECT N''reactivated'' AS outcome,
                           @PlacementKey AS placement_key,
                           @MomentKey AS moment_key,
                           @ConfirmedVersionNumber AS moment_version_number,
                           @TargetEntityKey AS target_entity_key,
                           @PlacementStatus AS placement_status,
                           @PlacementRowVersion AS row_version;
                    RETURN;
                END;

                IF @ExpectedPlacementRowVersion IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''stale'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           @MomentKey AS moment_key,
                           @ConfirmedVersionNumber AS moment_version_number,
                           @TargetEntityKey AS target_entity_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                INSERT dbo.moment_placements
                (
                    owner_profile_id, moment_id, moment_version_number,
                    target_entity_id, placement_status, created_by_user_id
                )
                VALUES
                (
                    @ProfileId, @MomentId, @ConfirmedVersionNumber,
                    @TargetEntityId, N''active'', @UserId
                );
                SET @PlacementId = CONVERT(bigint, SCOPE_IDENTITY());

                SELECT
                    @PlacementKey = placement_key,
                    @PlacementStatus = placement_status,
                    @PlacementRowVersion = row_version
                FROM dbo.moment_placements
                WHERE placement_id = @PlacementId;

                DECLARE @CreateAuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @CreateMetadata nvarchar(max) = CONCAT
                (
                    N''{"moment_version_number":'', @ConfirmedVersionNumber,
                    N'',"placement_status":"active"}''
                );
                INSERT @CreateAuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''moment.placement.created'',
                    @EntityType = N''moment_placement'',
                    @EntityKey = @PlacementKey,
                    @Outcome = N''success'',
                    @MetadataJson = @CreateMetadata;

                COMMIT TRANSACTION;
                SELECT N''created'' AS outcome,
                       @PlacementKey AS placement_key,
                       @MomentKey AS moment_key,
                       @ConfirmedVersionNumber AS moment_version_number,
                       @TargetEntityKey AS target_entity_key,
                       @PlacementStatus AS placement_status,
                       @PlacementRowVersion AS row_version;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListMomentPlacementsForOwner
            @UserKey nvarchar(300),
            @IncludeRemoved bit = 0,
            @Take int = 100
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;
            IF @Take IS NULL SET @Take = 100;
            IF @Take < 1 SET @Take = 1;
            IF @Take > 200 SET @Take = 200;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            SELECT TOP (@Take)
                placement.placement_key,
                moment.moment_key,
                placement.moment_version_number,
                target.entity_key AS target_entity_key,
                placement.placement_status,
                placement.created_at_utc,
                placement.reactivated_at_utc,
                placement.removed_at_utc,
                placement.updated_at_utc,
                placement.row_version,
                CAST
                (
                    CASE
                        WHEN target.active = 1
                         AND target.approval_status = N''approved''
                         AND target.visibility = N''private''
                         AND target.publication_status = N''unpublished''
                         AND target.deleted_at_utc IS NULL
                        THEN 1 ELSE 0
                    END AS bit
                ) AS target_available,
                target.active AS target_active,
                target.approval_status AS target_approval_status,
                target.visibility AS target_visibility,
                target.publication_status AS target_publication_status,
                CAST(CASE WHEN target.deleted_at_utc IS NULL THEN 0 ELSE 1 END AS bit)
                    AS target_deleted
            FROM dbo.moment_placements AS placement
            JOIN dbo.moments AS moment
              ON moment.moment_id = placement.moment_id
             AND moment.owner_profile_id = placement.owner_profile_id
            JOIN dbo.slate_entities AS target
              ON target.entity_id = placement.target_entity_id
             AND target.owner_profile_id = placement.owner_profile_id
            WHERE placement.owner_profile_id = @ProfileId
              AND (@IncludeRemoved = 1 OR placement.placement_status = N''active'')
            ORDER BY placement.updated_at_utc DESC, placement.placement_id DESC;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_RemoveMomentPlacement
            @UserKey nvarchar(300),
            @PlacementKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @PlacementKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52320, ''Owner, placement, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @PlacementId bigint;
                DECLARE @PlacementStatus nvarchar(20);
                DECLARE @PlacementRowVersion binary(8);
                DECLARE @MomentVersionNumber int;

                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                SELECT
                    @PlacementId = placement.placement_id,
                    @PlacementStatus = placement.placement_status,
                    @PlacementRowVersion = placement.row_version,
                    @MomentVersionNumber = placement.moment_version_number
                FROM dbo.moment_placements AS placement WITH (UPDLOCK, HOLDLOCK)
                WHERE placement.owner_profile_id = @ProfileId
                  AND placement.placement_key = @PlacementKey;

                IF @PlacementId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS placement_key,
                           CAST(NULL AS nvarchar(20)) AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF @PlacementRowVersion <> @ExpectedRowVersion
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''stale'' AS outcome,
                           @PlacementKey AS placement_key,
                           @PlacementStatus AS placement_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                IF @PlacementStatus = N''removed''
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''already_removed'' AS outcome,
                           @PlacementKey AS placement_key,
                           @PlacementStatus AS placement_status,
                           @PlacementRowVersion AS row_version;
                    RETURN;
                END;

                UPDATE dbo.moment_placements
                SET placement_status = N''removed'',
                    removed_by_user_id = @UserId,
                    removed_at_utc = SYSUTCDATETIME(),
                    updated_at_utc = SYSUTCDATETIME()
                WHERE placement_id = @PlacementId
                  AND row_version = @ExpectedRowVersion;

                IF @@ROWCOUNT <> 1
                    THROW 52321, ''Moment placement removal lost its concurrency boundary.'', 1;

                DECLARE @RemovalAuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @RemovalMetadata nvarchar(max) = CONCAT
                (
                    N''{"moment_version_number":'', @MomentVersionNumber,
                    N'',"placement_status":"removed"}''
                );
                INSERT @RemovalAuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''moment.placement.removed'',
                    @EntityType = N''moment_placement'',
                    @EntityKey = @PlacementKey,
                    @Outcome = N''success'',
                    @MetadataJson = @RemovalMetadata;

                SELECT
                    @PlacementStatus = placement_status,
                    @PlacementRowVersion = row_version
                FROM dbo.moment_placements
                WHERE placement_id = @PlacementId;

                COMMIT TRANSACTION;
                SELECT N''removed'' AS outcome,
                       @PlacementKey AS placement_key,
                       @PlacementStatus AS placement_status,
                       @PlacementRowVersion AS row_version;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_PLACEMENT_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreateOrReactivateMomentPlacement'),
        (N'usp_ListMomentPlacementsForOwner'),
        (N'usp_RemoveMomentPlacement');

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
        WHERE migration_id = N'PS-PLACEMENT-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-PLACEMENT-001',
            N'Private exact-version Moment placement references',
            N'PeerSlate Bible and Roadmap v2.3'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-PLACEMENT-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
