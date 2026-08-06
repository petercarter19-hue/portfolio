/* ============================================================
   PS-WORKSHOP-002 ROLLBACK - guarded backlog-confirmation reversal

   Refuses to run if a later migration is present or if either procedure
   this migration owns has drifted since it was applied. Drops
   dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner and restores
   dbo.usp_ArchiveKnowledgeItemForOwner to its exact PS-WORKSHOP-001
   definition (byte-identical T-SQL; tests/test_workshop_confirmation_
   migration.py compares the two literal CREATE OR ALTER batches and
   asserts they are equal). Removes only the PS-WORKSHOP-002 ledger row.

   THIS ROLLBACK DOES NOT UN-CONFIRM ANY ROW, AND THAT IS DELIBERATE. Every
   knowledge_items row that usp_ConfirmAuthoredKnowledgeBacklogForOwner ever
   confirmed is a LEGITIMATE confirmation under the owner's standing rule
   ("anything in your knowledge database is confirmed. You put it there"),
   not a side effect of this migration's schema existing. Rolling that rule
   back is a product decision for the owner to make explicitly and
   separately, never an automatic consequence of undoing the procedure that
   happened to apply it -- exactly as PS-OPPSLATE-002's rollback leaves
   every already-applied Opportunity Slate analysis untouched rather than
   reversing member decisions along with the schema that recorded them.
   Structurally: this rollback script EXECUTES no UPDATE and no DELETE
   against dbo.knowledge_items or dbo.knowledge_item_versions anywhere in
   its own control flow, so it is not merely policy that the confirmations
   survive -- no statement this script runs could touch them. (The
   restored usp_ArchiveKnowledgeItemForOwner procedure body below
   necessarily contains, as program TEXT, its own UPDATE targeting
   knowledge_items -- that is what the procedure does when a member later
   calls it -- but submitting that stored-procedure definition is not the
   same thing as this rollback executing an UPDATE; the rollback never
   runs one.)
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53320, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-WORKSHOP-002';

    IF @AppliedAtUtc IS NULL
       AND OBJECT_ID(N'dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner', N'P') IS NOT NULL
        THROW 53321, 'Rollback refused: the backlog-confirmation procedure exists without its migration record.', 1;

    IF @AppliedAtUtc IS NULL
        THROW 53322, 'Rollback refused: PS-WORKSHOP-002 is not recorded.', 1;

    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc > @AppliedAtUtc)
        THROW 53323, 'Rollback refused: a migration later than PS-WORKSHOP-002 is present.', 1;

    /* Drift guard on the two procedures this migration owns. If either
       changed after this migration applied -- by any path other than this
       migration's own forward script -- rolling back would silently
       discard an ungoverned edit no proof here can vouch for. */
    DECLARE @ProcedureHashPropertyName sysname = N'PS_WORKSHOP_002_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_ConfirmAuthoredKnowledgeBacklogForOwner'),
        (N'usp_ArchiveKnowledgeItemForOwner');
    IF EXISTS
    (
        SELECT 1 FROM @ProtectedProcedures p
        LEFT JOIN sys.procedures o ON o.schema_id = SCHEMA_ID(N'dbo') AND o.name = p.procedure_name
        LEFT JOIN sys.extended_properties x ON x.class = 1 AND x.major_id = o.object_id
             AND x.minor_id = 0 AND x.name = @ProcedureHashPropertyName
        WHERE o.object_id IS NULL OR x.major_id IS NULL
           OR CONVERT(nvarchar(64), x.value) <> CONVERT(nvarchar(64),
              HASHBYTES('SHA2_256', OBJECT_DEFINITION(o.object_id)), 2)
    )
        THROW 53324, 'Rollback refused: a protected PS-WORKSHOP-002 procedure changed after it applied.', 1;

    /* Drop the procedure this migration added outright. */
    IF OBJECT_ID(N'dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner;

    /* Restore usp_ArchiveKnowledgeItemForOwner to its exact PS-WORKSHOP-001
       definition. First remove the PS-WORKSHOP-002 fingerprint so the next
       forward apply of this same migration (or a later one) does not find
       a stale property left behind by a procedure it no longer owns. */
    IF EXISTS (SELECT 1 FROM sys.extended_properties WHERE class = 1
               AND major_id = OBJECT_ID(N'dbo.usp_ArchiveKnowledgeItemForOwner', N'P')
               AND minor_id = 0 AND name = @ProcedureHashPropertyName)
        EXEC sys.sp_dropextendedproperty @name = @ProcedureHashPropertyName,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_ArchiveKnowledgeItemForOwner';

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ArchiveKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53030, ''Owner, knowledge item, and expected version are required.'', 1;

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

                DECLARE @KnowledgeItemId bigint;
                SELECT @KnowledgeItemId = item.knowledge_item_id
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status <> N''archived''
                  AND item.row_version = @ExpectedRowVersion;

                IF @KnowledgeItemId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                UPDATE dbo.knowledge_items
                SET item_status = N''archived'',
                    archived_at_utc = SYSUTCDATETIME(),
                    archived_by_user_id = @UserId,
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
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''knowledge_item.archived'',
                    @EntityType = N''knowledge_item'',
                    @EntityKey = @KnowledgeItemKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{}'';

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, item.row_version
                FROM dbo.knowledge_items AS item
                WHERE item.knowledge_item_id = @KnowledgeItemId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF @AppliedAtUtc IS NOT NULL
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-WORKSHOP-002"}';

        DELETE dbo.schema_migrations WHERE migration_id = N'PS-WORKSHOP-002';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
