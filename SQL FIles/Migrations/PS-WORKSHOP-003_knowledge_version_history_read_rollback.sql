/* ============================================================
   PS-WORKSHOP-003 ROLLBACK - guarded wording-history read removal

   Drops only dbo.usp_ListKnowledgeItemVersionsForOwner and removes only
   the PS-WORKSHOP-003 ledger row. It refuses a missing record, later
   migration, missing procedure, or drifted protected definition. It does
   not update, delete, infer, or backfill any knowledge item or version.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53420, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-WORKSHOP-003';

    IF @AppliedAtUtc IS NULL
       AND OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P') IS NOT NULL
        THROW 53421, 'Rollback refused: the procedure exists without its migration record.', 1;
    IF @AppliedAtUtc IS NULL
        THROW 53422, 'Rollback refused: PS-WORKSHOP-003 is not recorded.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE applied_at_utc > @AppliedAtUtc
    )
        THROW 53423, 'Rollback refused: a migration later than PS-WORKSHOP-003 is present.', 1;

    DECLARE @ProcedureHashPropertyName sysname = N'PS_WORKSHOP_003_DEFINITION_HASH';
    IF OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P') IS NULL
       OR NOT EXISTS
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
        THROW 53424, 'Rollback refused: the protected PS-WORKSHOP-003 procedure changed after it applied.', 1;

    DROP PROCEDURE dbo.usp_ListKnowledgeItemVersionsForOwner;

    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.rolled_back',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-WORKSHOP-003"}';

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-WORKSHOP-003';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
