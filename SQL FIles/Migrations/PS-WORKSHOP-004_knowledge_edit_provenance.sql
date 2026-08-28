/* ============================================================
   PS-WORKSHOP-004 - retain source wording across owner edits

   Replaces only dbo.usp_UpdateKnowledgeItemForOwner. The procedure's
   parameters and result shape are unchanged. After the existing
   server-derived owner, private/non-archived item, expected-rowversion,
   UPDLOCK/HOLDLOCK fence succeeds, the procedure reads the owned current
   version by knowledge_item_id, owner_profile_id, and version_number. The
   new appended version copies that exact stored original_member_wording;
   approved_wording remains the member's edited input and authored_via
   remains N'typed'. Nothing accepts a browser-supplied original, infers or
   backfills wording, updates an old version, or changes application code.

   Requires PS-WORKSHOP-003. A first apply takes ownership only when the
   live procedure still matches its PS_WORKSHOP_001_DEFINITION_HASH. An
   applied re-run is a true no-op after validating the live
   PS_WORKSHOP_004_DEFINITION_HASH. No production apply is authorized by
   this file.

   Rollback: PS-WORKSHOP-004_knowledge_edit_provenance_rollback.sql
   Verification: ../Verification/PS-WORKSHOP-004_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53500, 'PS-WORKSHOP-004 requires the migration ledger.', 1;
    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-WORKSHOP-003'
    )
        THROW 53501, 'PS-WORKSHOP-003 must be applied before PS-WORKSHOP-004.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.knowledge_items', N'U') IS NULL
       OR OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
       OR OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P') IS NULL
        THROW 53502, 'The Workshop owner, audit, or knowledge-version baseline is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'knowledge_item_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'knowledge_item_key') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'current_version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'item_status') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'knowledge_item_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'approved_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'original_member_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'authored_via') IS NULL
        THROW 53503, 'The Workshop edit-provenance columns are incompatible.', 1;

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
        THROW 53504, 'The Workshop owner/version isolation baseline is missing or renamed.', 1;

    DECLARE @OldHashPropertyName sysname = N'PS_WORKSHOP_001_DEFINITION_HASH';
    DECLARE @ProcedureHashPropertyName sysname = N'PS_WORKSHOP_004_DEFINITION_HASH';
    DECLARE @ProcedureObjectId int = OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P');
    DECLARE @MigrationAlreadyApplied bit = CASE WHEN EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-004'
    ) THEN 1 ELSE 0 END;

    IF @MigrationAlreadyApplied = 1
    BEGIN
        IF NOT EXISTS
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
            THROW 53505, 'The protected PS-WORKSHOP-004 procedure changed after it applied.', 1;

        COMMIT TRANSACTION;
        RETURN;
    END;

    IF NOT EXISTS
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
        THROW 53506, 'The live Workshop edit procedure does not match its PS-WORKSHOP-001 fingerprint.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.extended_properties AS property
        WHERE property.class = 1
          AND property.major_id = @ProcedureObjectId
          AND property.minor_id = 0
          AND property.name = @ProcedureHashPropertyName
    )
        THROW 53507, 'The PS-WORKSHOP-004 fingerprint exists without its migration record.', 1;

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

                /* The existing owner/CAS fence remains the only admission
                   path. Unknown, foreign, forged, archived, and stale inputs
                   all retain the same neutral changed result. */
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

                /* Source provenance comes only from the already-stored,
                   owned current version. No caller parameter, fallback,
                   inference, or prior-row mutation is possible here. */
                DECLARE @OriginalMemberWording nvarchar(max);
                SELECT @OriginalMemberWording = version_record.original_member_wording
                FROM dbo.knowledge_item_versions AS version_record WITH (UPDLOCK, HOLDLOCK)
                WHERE version_record.knowledge_item_id = @KnowledgeItemId
                  AND version_record.owner_profile_id = @ProfileId
                  AND version_record.version_number = @CurrentVersionNumber;

                IF @OriginalMemberWording IS NULL
                    THROW 53508, ''The owned current knowledge version is missing.'', 1;

                DECLARE @NextVersionNumber int = @CurrentVersionNumber + 1;

                INSERT dbo.knowledge_item_versions
                (
                    knowledge_item_id, owner_profile_id, version_number, title,
                    approved_wording, original_member_wording, body_format,
                    authored_via, saved_by_user_id
                )
                VALUES
                (
                    @KnowledgeItemId, @ProfileId, @NextVersionNumber, @Title,
                    @ApprovedWording, @OriginalMemberWording, @BodyFormat,
                    N''typed'', @UserId
                );

                /* Reassert the complete admitted parent scope. The row-count
                   fence makes the version append and parent advance atomic
                   even if this procedure is changed incorrectly later. */
                UPDATE item
                SET item.current_version_number = @NextVersionNumber,
                    item.classification = @Classification,
                    item.item_status = CASE WHEN @Confirm = 1 THEN N''confirmed'' ELSE N''unfinished'' END,
                    item.confirmed_version_number = CASE WHEN @Confirm = 1 THEN @NextVersionNumber ELSE NULL END,
                    item.confirmed_by_user_id = CASE WHEN @Confirm = 1 THEN @UserId ELSE NULL END,
                    item.confirmed_at_utc = CASE WHEN @Confirm = 1 THEN SYSUTCDATETIME() ELSE NULL END,
                    item.updated_at_utc = SYSUTCDATETIME()
                FROM dbo.knowledge_items AS item
                WHERE item.knowledge_item_id = @KnowledgeItemId
                  AND item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status <> N''archived''
                  AND item.current_version_number = @CurrentVersionNumber
                  AND item.row_version = @ExpectedRowVersion;

                IF @@ROWCOUNT <> 1
                    THROW 53509, ''The knowledge item changed before its version advance completed.'', 1;

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
    DECLARE @ProcedureHash nvarchar(64) = CONVERT
    (
        nvarchar(64),
        HASHBYTES('SHA2_256', OBJECT_DEFINITION(@ProcedureObjectId)),
        2
    );
    IF @ProcedureHash IS NULL
        THROW 53510, 'The PS-WORKSHOP-004 procedure was not created.', 1;

    EXEC sys.sp_addextendedproperty
        @name = @ProcedureHashPropertyName,
        @value = @ProcedureHash,
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'PROCEDURE', @level1name = N'usp_UpdateKnowledgeItemForOwner';

    INSERT dbo.schema_migrations (migration_id, description, application_version)
    VALUES
    (
        N'PS-WORKSHOP-004',
        N'Workshop owner edits retain the exact stored original-member wording from the owned current version while appending the edited approved wording as a typed version. Replaces only usp_UpdateKnowledgeItemForOwner; no input/output change, inference, backfill, old-version mutation, or application change. Requires PS-WORKSHOP-003.',
        N'PeerSlate Bible and Roadmap v3.0'
    );
    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.applied',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-WORKSHOP-004"}';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
