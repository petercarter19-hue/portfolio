/* ============================================================
   PS-HOME-001 - finite, owner-resolving Home read contract

   Adds one bounded read-only procedure. It creates no Home table,
   copies no canonical content, and accepts no profile selector.

   Rollback: PS-HOME-001_owner_home_reads_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52500, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-001')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MOMENT-001')
       OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-VOICE-001')
        THROW 52501, 'The owner, Capture, Moment, and Voice foundations must precede PS-HOME-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moments', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 52502, 'The finite Owner Home read foundation is incomplete.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOwnerHomeForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL
                THROW 52503, ''Authenticated owner key is required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                IF @ProfileId IS NULL
                    THROW 52504, ''Authenticated owner profile not found.'', 1;

                DECLARE @ReviewItems TABLE
                (
                    item_key uniqueidentifier NOT NULL,
                    review_kind nvarchar(30) NOT NULL,
                    created_at_utc datetime2(7) NOT NULL,
                    updated_at_utc datetime2(7) NOT NULL,
                    version_token binary(8) NOT NULL,
                    status nvarchar(30) NOT NULL,
                    urgency_priority tinyint NOT NULL,
                    PRIMARY KEY (review_kind, item_key)
                );

                ;WITH ReviewCandidates AS
                (
                    SELECT
                        source.source_key AS item_key,
                        CAST(N''voice_draft_failed'' AS nvarchar(30)) AS review_kind,
                        source.created_at_utc,
                        source.updated_at_utc,
                        CONVERT(binary(8), source.row_version) AS version_token,
                        source.state AS status,
                        CAST(1 AS tinyint) AS urgency_priority
                    FROM dbo.voice_media_sources AS source
                    WHERE source.owner_profile_id = @ProfileId
                      AND source.state = N''failed''
                      AND source.deleted_at_utc IS NULL

                    UNION ALL

                    SELECT
                        moment.moment_key,
                        CAST(N''moment_proposal_pending'' AS nvarchar(30)),
                        moment.created_at_utc,
                        moment.updated_at_utc,
                        CONVERT(binary(8), moment.row_version),
                        moment.status,
                        CAST(2 AS tinyint)
                    FROM dbo.moments AS moment
                    WHERE moment.owner_profile_id = @ProfileId
                      AND moment.visibility = N''private''
                      AND moment.status = N''proposal''
                      AND EXISTS
                      (
                          SELECT 1
                          FROM dbo.moment_sources AS source_link
                          WHERE source_link.moment_id = moment.moment_id
                            AND source_link.owner_profile_id = @ProfileId
                            AND source_link.source_state = N''available''
                      )

                    UNION ALL

                    SELECT
                        source.source_key,
                        CAST(N''voice_draft_ready'' AS nvarchar(30)),
                        source.created_at_utc,
                        source.updated_at_utc,
                        CONVERT(binary(8), source.row_version),
                        source.state,
                        CAST(3 AS tinyint)
                    FROM dbo.voice_media_sources AS source
                    WHERE source.owner_profile_id = @ProfileId
                      AND source.state = N''needs_review''
                      AND source.deleted_at_utc IS NULL
                )
                INSERT @ReviewItems
                (
                    item_key, review_kind, created_at_utc, updated_at_utc,
                    version_token, status, urgency_priority
                )
                SELECT TOP (3)
                    candidate.item_key,
                    candidate.review_kind,
                    candidate.created_at_utc,
                    candidate.updated_at_utc,
                    candidate.version_token,
                    candidate.status,
                    candidate.urgency_priority
                FROM ReviewCandidates AS candidate
                ORDER BY
                    candidate.urgency_priority,
                    candidate.updated_at_utc,
                    candidate.item_key;

                DECLARE @RecentMoment TABLE
                (
                    moment_key uniqueidentifier NOT NULL PRIMARY KEY,
                    confirmed_version int NOT NULL,
                    title nvarchar(160) NOT NULL,
                    occurred_on date NULL,
                    updated_at_utc datetime2(7) NOT NULL,
                    version_token binary(8) NOT NULL,
                    status nvarchar(30) NOT NULL
                );

                INSERT @RecentMoment
                (
                    moment_key, confirmed_version, title, occurred_on,
                    updated_at_utc, version_token, status
                )
                SELECT TOP (1)
                    moment.moment_key,
                    moment.confirmed_version_number,
                    version_record.title,
                    version_record.occurred_on,
                    moment.updated_at_utc,
                    CONVERT(binary(8), moment.row_version),
                    moment.status
                FROM dbo.moments AS moment
                JOIN dbo.moment_versions AS version_record
                  ON version_record.moment_id = moment.moment_id
                 AND version_record.version_number = moment.confirmed_version_number
                WHERE moment.owner_profile_id = @ProfileId
                  AND moment.visibility = N''private''
                  AND moment.status = N''confirmed''
                  AND moment.confirmed_version_number IS NOT NULL
                  AND NULLIF(LTRIM(RTRIM(version_record.title)), N'''') IS NOT NULL
                  AND NOT EXISTS
                  (
                      SELECT 1
                      FROM @ReviewItems AS review
                      WHERE review.review_kind = N''moment_proposal_pending''
                        AND review.item_key = moment.moment_key
                  )
                ORDER BY
                    moment.confirmed_at_utc DESC,
                    moment.updated_at_utc DESC,
                    moment.moment_key;

                SELECT
                    profile.profile_key,
                    profile.display_name,
                    CONVERT(binary(8), profile.row_version) AS profile_row_version
                FROM dbo.member_profiles AS profile
                WHERE profile.profile_id = @ProfileId;

                SELECT
                    review.item_key,
                    review.review_kind,
                    review.created_at_utc,
                    review.updated_at_utc,
                    review.version_token,
                    review.status
                FROM @ReviewItems AS review
                ORDER BY
                    review.urgency_priority,
                    review.updated_at_utc,
                    review.item_key;

                SELECT
                    recent.moment_key,
                    recent.confirmed_version,
                    recent.title,
                    recent.occurred_on,
                    recent.updated_at_utc,
                    recent.version_token,
                    recent.status
                FROM @RecentMoment AS recent;

                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_HOME_001_DEFINITION_HASH';
    DECLARE @ProcedureHash nvarchar(64) = CONVERT
    (
        nvarchar(64),
        HASHBYTES
        (
            'SHA2_256',
            OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P'))
        ),
        2
    );

    IF EXISTS
    (
        SELECT 1
        FROM sys.extended_properties AS property
        WHERE property.class = 1
          AND property.major_id = OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P')
          AND property.minor_id = 0
          AND property.name = @ProcedureHashPropertyName
    )
        EXEC sys.sp_updateextendedproperty
            @name = @ProcedureHashPropertyName,
            @value = @ProcedureHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_GetOwnerHomeForOwner';
    ELSE
        EXEC sys.sp_addextendedproperty
            @name = @ProcedureHashPropertyName,
            @value = @ProcedureHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_GetOwnerHomeForOwner';

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-HOME-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-HOME-001',
            N'Finite owner-resolving Home read contract',
            N'PeerSlate Bible v2.6 / Roadmap v2.5'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-HOME-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
