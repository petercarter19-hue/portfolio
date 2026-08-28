/* ============================================================
   PS-WORKSHOP-003 - owner-scoped knowledge wording history read

   Adds one read-only procedure. It returns at most the newest 50 retained
   versions of one private knowledge item owned by the server-resolved
   member. Each row contains only the version number, the exact stored
   approved wording, the exact stored original-member wording, and its save
   timestamp. A second result set reports the true retained-version count
   and whether the 50-row window is truncated.

   No wording is inferred, repaired, backfilled, or rewritten. In
   particular, older ai_assisted_approved rows may contain refined wording
   in original_member_wording because the original wording was not retained
   when those rows were created; this migration exposes the stored fact and
   does not manufacture greater certainty.

   The optional result-set switches exist only so the disposable verifier
   can capture the differently-shaped sets independently with INSERT EXEC.
   Application callers omit them and receive both sets.

   Requires PS-WORKSHOP-002. No production apply is authorized by this file.
   Rollback: PS-WORKSHOP-003_knowledge_version_history_read_rollback.sql
   Verification: ../Verification/PS-WORKSHOP-003_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53400, 'PS-WORKSHOP-003 requires the migration ledger.', 1;
    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-WORKSHOP-002'
    )
        THROW 53401, 'PS-WORKSHOP-002 must be applied before PS-WORKSHOP-003.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.knowledge_items', N'U') IS NULL
       OR OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 53402, 'The Workshop owner or knowledge-version baseline is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'knowledge_item_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'knowledge_item_key') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'knowledge_item_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'approved_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'original_member_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'saved_at_utc') IS NULL
        THROW 53403, 'The Workshop knowledge-version columns are incompatible.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_items')
          AND name = N'CK_knowledge_items_visibility'
    )
       OR NOT EXISTS
       (
           SELECT 1 FROM sys.foreign_keys
           WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_item_versions')
             AND name = N'FK_knowledge_item_versions_item'
       )
       OR NOT EXISTS
       (
           SELECT 1 FROM sys.key_constraints
           WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_item_versions')
             AND name = N'UQ_knowledge_item_versions_number'
       )
        THROW 53404, 'The Workshop owner-isolation constraint baseline is missing or renamed.', 1;

    DECLARE @ProcedureHashPropertyName sysname = N'PS_WORKSHOP_003_DEFINITION_HASH';
    DECLARE @MigrationAlreadyApplied bit = CASE WHEN EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-003'
    ) THEN 1 ELSE 0 END;

    IF @MigrationAlreadyApplied = 1
    BEGIN
        IF OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P') IS NULL
            THROW 53405, 'PS-WORKSHOP-003 is recorded but its procedure is missing.', 1;
        IF NOT EXISTS
        (
            SELECT 1
            FROM sys.extended_properties AS property
            WHERE property.class = 1
              AND property.major_id = OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P')
              AND property.minor_id = 0
              AND property.name = @ProcedureHashPropertyName
              AND CONVERT(nvarchar(64), property.value) = CONVERT
              (
                  nvarchar(64),
                  HASHBYTES
                  (
                      'SHA2_256',
                      OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P'))
                  ),
                  2
              )
        )
            THROW 53406, 'The protected PS-WORKSHOP-003 procedure changed after it applied.', 1;
    END;
    ELSE IF OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P') IS NOT NULL
        THROW 53407, 'The PS-WORKSHOP-003 procedure exists without its migration record.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListKnowledgeItemVersionsForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @IncludeVersions bit = 1,
            @IncludeMetadata bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @IncludeVersions IS NULL SET @IncludeVersions = 1;
            IF @IncludeMetadata IS NULL SET @IncludeMetadata = 1;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            DECLARE @KnowledgeItemId bigint;
            SELECT @KnowledgeItemId = item.knowledge_item_id
            FROM dbo.knowledge_items AS item
            WHERE item.owner_profile_id = @ProfileId
              AND item.knowledge_item_key = @KnowledgeItemKey
              AND item.visibility = N''private'';

            /* Materialize rows and their full-set count from ONE source
               statement. This is the concurrency boundary: under ordinary
               READ COMMITTED, a standalone COUNT followed by a standalone
               TOP (50) can observe two different committed states when an
               update appends a version between them. COUNT_BIG OVER is
               evaluated over the same qualifying statement that supplies
               the TOP window, and every outward result is then derived only
               from this table variable. Rows and metadata therefore cannot
               disagree even when a concurrent append commits. */
            DECLARE @VersionSnapshot TABLE
            (
                version_number int NOT NULL PRIMARY KEY,
                approved_wording nvarchar(max) NOT NULL,
                original_member_wording nvarchar(max) NOT NULL,
                saved_at_utc datetime2(7) NOT NULL,
                total_count bigint NOT NULL
            );
            INSERT @VersionSnapshot
                (version_number, approved_wording, original_member_wording,
                 saved_at_utc, total_count)
            SELECT TOP (50)
                version_record.version_number,
                version_record.approved_wording,
                version_record.original_member_wording,
                version_record.saved_at_utc,
                COUNT_BIG(*) OVER () AS total_count
            FROM dbo.knowledge_item_versions AS version_record
            WHERE version_record.knowledge_item_id = @KnowledgeItemId
              AND version_record.owner_profile_id = @ProfileId
            ORDER BY version_record.version_number DESC;

            DECLARE @TotalCount bigint = 0;
            SELECT @TotalCount = COALESCE(MAX(snapshot.total_count), 0)
            FROM @VersionSnapshot AS snapshot;

            IF @IncludeVersions = 1
            BEGIN
                SELECT
                    snapshot.version_number,
                    snapshot.approved_wording,
                    snapshot.original_member_wording,
                    snapshot.saved_at_utc
                FROM @VersionSnapshot AS snapshot
                ORDER BY snapshot.version_number DESC;
            END;

            IF @IncludeMetadata = 1
            BEGIN
                SELECT
                    @TotalCount AS total_count,
                    CONVERT(bit, CASE WHEN @TotalCount > 50 THEN 1 ELSE 0 END) AS is_truncated;
            END;
        END;
    ');

    DECLARE @ProcedureHash nvarchar(64) = CONVERT
    (
        nvarchar(64),
        HASHBYTES
        (
            'SHA2_256',
            OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P'))
        ),
        2
    );
    IF @ProcedureHash IS NULL
        THROW 53408, 'The PS-WORKSHOP-003 procedure was not created.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.extended_properties
        WHERE class = 1
          AND major_id = OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P')
          AND minor_id = 0
          AND name = @ProcedureHashPropertyName
    )
        EXEC sys.sp_updateextendedproperty
            @name = @ProcedureHashPropertyName,
            @value = @ProcedureHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_ListKnowledgeItemVersionsForOwner';
    ELSE
        EXEC sys.sp_addextendedproperty
            @name = @ProcedureHashPropertyName,
            @value = @ProcedureHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_ListKnowledgeItemVersionsForOwner';

    IF @MigrationAlreadyApplied = 0
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-WORKSHOP-003',
            N'Owner-scoped read-only Workshop wording history: newest 50 retained versions with exact approved and stored original-member wording, save timestamp, true total count, and truncation metadata. Requires PS-WORKSHOP-002.',
            N'PeerSlate Bible and Roadmap v3.0'
        );
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-WORKSHOP-003"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
