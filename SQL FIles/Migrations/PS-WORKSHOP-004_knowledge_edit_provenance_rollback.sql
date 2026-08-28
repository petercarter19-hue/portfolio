/* ============================================================
   PS-WORKSHOP-004 ROLLBACK - guarded edit-provenance restoration

   Refuses unless PS-WORKSHOP-004 is the migration-ledger tip, no later
   migration exists, and the live edit procedure still matches its
   PS_WORKSHOP_004_DEFINITION_HASH. It then removes that fingerprint,
   restores the exact PS-WORKSHOP-001 procedure literal byte-for-byte,
   validates the restored live definition against the surviving
   PS_WORKSHOP_001_DEFINITION_HASH, and removes only the PS-WORKSHOP-004
   ledger row. It never executes a mutation against a knowledge item or
   version; already-appended member versions remain canonical history.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53520, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-WORKSHOP-004';

    IF @AppliedAtUtc IS NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.extended_properties AS property
           WHERE property.class = 1
             AND property.major_id = OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P')
             AND property.minor_id = 0
             AND property.name = N'PS_WORKSHOP_004_DEFINITION_HASH'
       )
        THROW 53521, 'Rollback refused: the PS-WORKSHOP-004 fingerprint exists without its migration record.', 1;
    IF @AppliedAtUtc IS NULL
        THROW 53522, 'Rollback refused: PS-WORKSHOP-004 is not recorded.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE applied_at_utc > @AppliedAtUtc
    )
        THROW 53523, 'Rollback refused: a migration later than PS-WORKSHOP-004 is present.', 1;

    DECLARE @LedgerTip nvarchar(200);
    SELECT TOP (1) @LedgerTip = migration.migration_id
    FROM dbo.schema_migrations AS migration
    ORDER BY migration.applied_at_utc DESC, migration.migration_id DESC;
    IF @LedgerTip <> N'PS-WORKSHOP-004'
        THROW 53524, 'Rollback refused: PS-WORKSHOP-004 is not the migration-ledger tip.', 1;

    DECLARE @ProcedureHashPropertyName sysname = N'PS_WORKSHOP_004_DEFINITION_HASH';
    DECLARE @OldHashPropertyName sysname = N'PS_WORKSHOP_001_DEFINITION_HASH';
    DECLARE @ProcedureObjectId int = OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P');
    IF @ProcedureObjectId IS NULL
       OR NOT EXISTS
       (
           SELECT 1
           FROM sys.extended_properties AS property
           WHERE property.class = 1
             AND property.major_id = @ProcedureObjectId
             AND property.minor_id = 0
             AND property.name = @ProcedureHashPropertyName
             AND CONVERT(nvarchar(64), property.value) = CONVERT
             (
                 nvarchar(64),
                 HASHBYTES('SHA2_256', OBJECT_DEFINITION(@ProcedureObjectId)),
                 2
             )
       )
        THROW 53525, 'Rollback refused: the protected PS-WORKSHOP-004 procedure changed after it applied.', 1;

    EXEC sys.sp_dropextendedproperty
        @name = @ProcedureHashPropertyName,
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'PROCEDURE', @level1name = N'usp_UpdateKnowledgeItemForOwner';

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_UpdateKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @Title nvarchar(160),
            @ApprovedWording nvarchar(max),
            @BodyFormat nvarchar(20),
            @Classification nvarchar(20),
            @Confirm bit
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @Title = NULLIF(LTRIM(RTRIM(@Title)), N'''');
            SET @ApprovedWording = NULLIF(LTRIM(RTRIM(@ApprovedWording)), N'''');
            SET @BodyFormat = NULLIF(LTRIM(RTRIM(@BodyFormat)), N'''');
            SET @Classification = NULLIF(LTRIM(RTRIM(@Classification)), N'''');
            IF @Confirm IS NULL SET @Confirm = 0;

            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53020, ''Owner, knowledge item, and expected version are required.'', 1;
            IF @Classification IS NULL OR @Classification NOT IN (N''work'', N''personal'', N''both'', N''unclassified'')
                THROW 53021, ''Classification is invalid.'', 1;
            IF @BodyFormat IS NULL OR @BodyFormat NOT IN (N''plain'', N''rich'')
                THROW 53022, ''Body format is invalid.'', 1;
            IF @Title IS NULL OR @ApprovedWording IS NULL
                THROW 53023, ''Title and approved wording are required.'', 1;
            IF DATALENGTH(@Title) / 2 > 160 OR DATALENGTH(@ApprovedWording) / 2 > 8000
                THROW 53024, ''One or more knowledge item fields exceeds its limit.'', 1;

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

                /* Editing an archived item is refused (surfaced as ''changed''
                   exactly like any other not-found/mismatch case): a member
                   restores it first. This keeps the archive/restore/edit
                   state machine deterministic without a separate error code. */
                DECLARE @KnowledgeItemId bigint;
                DECLARE @CurrentVersionNumber int;
                SELECT
                    @KnowledgeItemId = item.knowledge_item_id,
                    @CurrentVersionNumber = item.current_version_number
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status <> N''archived''
                  AND item.row_version = @ExpectedRowVersion;

                IF @KnowledgeItemId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome,
                           CAST(NULL AS int) AS version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                DECLARE @NextVersionNumber int = @CurrentVersionNumber + 1;

                /* original_member_wording of the NEW version is the new
                   approved wording itself: an edit made directly in My
                   Information is always the member''s own typed words (there
                   is no AI-assisted edit path in W1), so the member-typed
                   source and the canonical wording are identical for this
                   version, exactly as architecture doc 17 section 5.2/9.1
                   requires for a directly authored version. authored_via is
                   fixed to ''typed'' for the same reason. */
                INSERT dbo.knowledge_item_versions
                (
                    knowledge_item_id, owner_profile_id, version_number, title,
                    approved_wording, original_member_wording, body_format,
                    authored_via, saved_by_user_id
                )
                VALUES
                (
                    @KnowledgeItemId, @ProfileId, @NextVersionNumber, @Title,
                    @ApprovedWording, @ApprovedWording, @BodyFormat,
                    N''typed'', @UserId
                );

                UPDATE dbo.knowledge_items
                SET current_version_number = @NextVersionNumber,
                    classification = @Classification,
                    item_status = CASE WHEN @Confirm = 1 THEN N''confirmed'' ELSE N''unfinished'' END,
                    confirmed_version_number = CASE WHEN @Confirm = 1 THEN @NextVersionNumber ELSE NULL END,
                    confirmed_by_user_id = CASE WHEN @Confirm = 1 THEN @UserId ELSE NULL END,
                    confirmed_at_utc = CASE WHEN @Confirm = 1 THEN SYSUTCDATETIME() ELSE NULL END,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE knowledge_item_id = @KnowledgeItemId;

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
                    N''{"version_number":'', @NextVersionNumber,
                    N'',"classification":"'', @Classification,
                    N''","confirmed":'', CASE WHEN @Confirm = 1 THEN N''true'' ELSE N''false'' END,
                    N''}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''knowledge_item.updated'',
                    @EntityType = N''knowledge_item'',
                    @EntityKey = @KnowledgeItemKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       @NextVersionNumber AS version_number,
                       item.row_version
                FROM dbo.knowledge_items AS item
                WHERE item.knowledge_item_id = @KnowledgeItemId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    SET @ProcedureObjectId = OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P');
    IF @ProcedureObjectId IS NULL
       OR NOT EXISTS
       (
           SELECT 1
           FROM sys.extended_properties AS property
           WHERE property.class = 1
             AND property.major_id = @ProcedureObjectId
             AND property.minor_id = 0
             AND property.name = @OldHashPropertyName
             AND CONVERT(nvarchar(64), property.value) = CONVERT
             (
                 nvarchar(64),
                 HASHBYTES('SHA2_256', OBJECT_DEFINITION(@ProcedureObjectId)),
                 2
             )
       )
        THROW 53526, 'Rollback restored a procedure that does not match the PS-WORKSHOP-001 fingerprint.', 1;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-WORKSHOP-004';
    IF @@ROWCOUNT <> 1
        THROW 53527, 'Rollback did not remove exactly the PS-WORKSHOP-004 ledger row.', 1;

    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.rolled_back',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-WORKSHOP-004"}';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
