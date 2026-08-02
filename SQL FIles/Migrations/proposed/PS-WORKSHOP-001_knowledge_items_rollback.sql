/* ============================================================
   PS-WORKSHOP-001 ROLLBACK - guarded private knowledge store removal

   Refuses to discard any member knowledge_items, knowledge_item_versions,
   or knowledge_item_save_requests record, any later migration, or any
   protected procedure that changed after this migration was applied.
   Removes only the seven usp_*KnowledgeItem*ForOwner procedures and the
   three tables this migration added.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53100, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @WorkshopAppliedAtUtc datetime2(7);
    SELECT @WorkshopAppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-WORKSHOP-001';

    IF @WorkshopAppliedAtUtc IS NULL
       AND
       (
           OBJECT_ID(N'dbo.knowledge_items', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.knowledge_item_save_requests', N'U') IS NOT NULL
       )
        THROW 53101, 'Rollback refused: Knowledge objects exist without their migration record.', 1;

    IF @WorkshopAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM dbo.schema_migrations AS migration
           WHERE migration.applied_at_utc > @WorkshopAppliedAtUtc
       )
        THROW 53102, 'Rollback refused: a migration later than PS-WORKSHOP-001 is present.', 1;

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_WORKSHOP_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_ListKnowledgeItemsForOwner'),
        (N'usp_GetKnowledgeItemForOwner'),
        (N'usp_SaveKnowledgeItemForOwner'),
        (N'usp_UpdateKnowledgeItemForOwner'),
        (N'usp_ArchiveKnowledgeItemForOwner'),
        (N'usp_RestoreKnowledgeItemForOwner'),
        (N'usp_DeleteKnowledgeItemForOwner');

    IF @WorkshopAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM @ProtectedProcedures AS protected_procedure
           LEFT JOIN sys.procedures AS procedure_object
             ON procedure_object.schema_id = SCHEMA_ID(N'dbo')
            AND procedure_object.name = protected_procedure.procedure_name
           LEFT JOIN sys.extended_properties AS property
             ON property.class = 1
            AND property.major_id = procedure_object.object_id
            AND property.minor_id = 0
            AND property.name = @ProcedureHashPropertyName
           WHERE procedure_object.object_id IS NULL
              OR property.major_id IS NULL
              OR CONVERT(nvarchar(64), property.value) <>
                 CONVERT
                 (
                     nvarchar(64),
                     HASHBYTES
                     (
                         'SHA2_256',
                         OBJECT_DEFINITION(procedure_object.object_id)
                     ),
                     2
                 )
       )
        THROW 53103, 'Rollback refused: a protected Workshop procedure changed after PS-WORKSHOP-001.', 1;

    IF OBJECT_ID(N'dbo.knowledge_items', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.knowledge_items)
        THROW 53104, 'Rollback refused: knowledge_items contains member records.', 1;
    IF OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.knowledge_item_versions)
        THROW 53105, 'Rollback refused: knowledge_item_versions contains member content.', 1;
    IF OBJECT_ID(N'dbo.knowledge_item_save_requests', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.knowledge_item_save_requests)
        THROW 53106, 'Rollback refused: knowledge_item_save_requests contains member replay records.', 1;

    DECLARE @WorkshopTableIds TABLE (object_id int PRIMARY KEY);
    INSERT @WorkshopTableIds (object_id)
    SELECT object_id
    FROM sys.tables
    WHERE object_id IN
    (
        OBJECT_ID(N'dbo.knowledge_items'),
        OBJECT_ID(N'dbo.knowledge_item_versions'),
        OBJECT_ID(N'dbo.knowledge_item_save_requests')
    );

    IF EXISTS
    (
        SELECT 1
        FROM sys.foreign_keys AS foreign_key
        WHERE foreign_key.referenced_object_id IN
              (SELECT object_id FROM @WorkshopTableIds)
          AND foreign_key.parent_object_id NOT IN
              (SELECT object_id FROM @WorkshopTableIds)
    )
        THROW 53107, 'Rollback refused: a later table depends on PS-WORKSHOP-001.', 1;

    /* Joined to sys.objects and filtered to genuine programmable object
       types (procedure/view/trigger/function) - caught by the first live
       staging rehearsal: every CHECK constraint on knowledge_items and
       knowledge_item_versions (CK_knowledge_items_status and its siblings)
       also appears in sys.sql_expression_dependencies referencing its own
       table, because it is a scalar expression evaluated against that
       table's columns. Those constraints are part of PS-WORKSHOP-001's own
       CREATE TABLE statements, not a later dependent object, so without
       this filter this guard refused rollback unconditionally on every
       freshly applied, untouched migration. */
    IF EXISTS
    (
        SELECT 1
        FROM sys.sql_expression_dependencies AS dependency
        JOIN sys.objects AS referencing_object
          ON referencing_object.object_id = dependency.referencing_id
        WHERE dependency.referenced_id IN (SELECT object_id FROM @WorkshopTableIds)
          AND referencing_object.type IN (N'P', N'V', N'TR', N'FN', N'IF', N'TF')
          AND dependency.referencing_id NOT IN
          (
              OBJECT_ID(N'dbo.usp_ListKnowledgeItemsForOwner'),
              OBJECT_ID(N'dbo.usp_GetKnowledgeItemForOwner'),
              OBJECT_ID(N'dbo.usp_SaveKnowledgeItemForOwner'),
              OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner'),
              OBJECT_ID(N'dbo.usp_ArchiveKnowledgeItemForOwner'),
              OBJECT_ID(N'dbo.usp_RestoreKnowledgeItemForOwner'),
              OBJECT_ID(N'dbo.usp_DeleteKnowledgeItemForOwner')
          )
          AND dependency.referencing_id NOT IN (SELECT object_id FROM @WorkshopTableIds)
    )
        THROW 53108, 'Rollback refused: a later programmable object depends on PS-WORKSHOP-001.', 1;

    IF OBJECT_ID(N'dbo.usp_ListKnowledgeItemsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListKnowledgeItemsForOwner;
    IF OBJECT_ID(N'dbo.usp_GetKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetKnowledgeItemForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveKnowledgeItemForOwner;
    IF OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_UpdateKnowledgeItemForOwner;
    IF OBJECT_ID(N'dbo.usp_ArchiveKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ArchiveKnowledgeItemForOwner;
    IF OBJECT_ID(N'dbo.usp_RestoreKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_RestoreKnowledgeItemForOwner;
    IF OBJECT_ID(N'dbo.usp_DeleteKnowledgeItemForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_DeleteKnowledgeItemForOwner;

    IF OBJECT_ID(N'dbo.knowledge_item_save_requests', N'U') IS NOT NULL
        DROP TABLE dbo.knowledge_item_save_requests;
    IF OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NOT NULL
        DROP TABLE dbo.knowledge_item_versions;
    IF OBJECT_ID(N'dbo.knowledge_items', N'U') IS NOT NULL
        DROP TABLE dbo.knowledge_items;

    IF @WorkshopAppliedAtUtc IS NOT NULL
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-WORKSHOP-001"}';

        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
