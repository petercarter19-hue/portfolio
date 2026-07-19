/* ============================================================
   PS-PLACEMENT-001 ROLLBACK - guarded placement-reference removal

   Refuses to discard placement lifecycle data, reverse a later
   migration/dependency, or remove drifted protected procedures.
   Normal rollback removes only PS-PLACEMENT-001 artifacts.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52330, 'Rollback blocked: the migration ledger is missing.', 1;

    DECLARE @PlacementAppliedAtUtc datetime2(7);
    SELECT @PlacementAppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-PLACEMENT-001';

    IF @PlacementAppliedAtUtc IS NULL
       AND
       (
           OBJECT_ID(N'dbo.moment_placements', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.usp_CreateOrReactivateMomentPlacement', N'P') IS NOT NULL
           OR OBJECT_ID(N'dbo.usp_ListMomentPlacementsForOwner', N'P') IS NOT NULL
           OR OBJECT_ID(N'dbo.usp_RemoveMomentPlacement', N'P') IS NOT NULL
       )
        THROW 52331, 'Rollback blocked: Placement artifacts exist without a migration record.', 1;

    IF @PlacementAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM dbo.schema_migrations AS migration
           WHERE migration.applied_at_utc > @PlacementAppliedAtUtc
       )
        THROW 52332, 'Rollback blocked: a migration later than PS-PLACEMENT-001 is present.', 1;

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

    IF @PlacementAppliedAtUtc IS NOT NULL
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
        THROW 52333, 'Rollback blocked: a protected Placement procedure changed after PS-PLACEMENT-001.', 1;

    IF OBJECT_ID(N'dbo.moment_placements', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.moment_placements)
        THROW 52334, 'Rollback blocked: moment_placements contains lifecycle records.', 1;

    DECLARE @PlacementTableId int = OBJECT_ID(N'dbo.moment_placements', N'U');

    IF @PlacementTableId IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.foreign_keys AS foreign_key
           WHERE foreign_key.referenced_object_id = @PlacementTableId
             AND foreign_key.parent_object_id <> @PlacementTableId
       )
        THROW 52335, 'Rollback blocked: a later table depends on PS-PLACEMENT-001.', 1;

    IF @PlacementTableId IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.sql_expression_dependencies AS dependency
           WHERE dependency.referenced_id = @PlacementTableId
             AND dependency.referencing_id NOT IN
                 (
                     OBJECT_ID(N'dbo.usp_CreateOrReactivateMomentPlacement'),
                     OBJECT_ID(N'dbo.usp_ListMomentPlacementsForOwner'),
                     OBJECT_ID(N'dbo.usp_RemoveMomentPlacement')
                 )
             AND dependency.referencing_id <> @PlacementTableId
             AND dependency.referencing_id NOT IN
                 (
                     SELECT object_id
                     FROM sys.objects
                     WHERE parent_object_id = @PlacementTableId
                 )
       )
        THROW 52336, 'Rollback blocked: a later programmable object depends on PS-PLACEMENT-001.', 1;

    DECLARE @MomentOwnerUniqueIndexId int;
    SELECT @MomentOwnerUniqueIndexId = constraint_record.unique_index_id
    FROM sys.key_constraints AS constraint_record
    WHERE constraint_record.parent_object_id = OBJECT_ID(N'dbo.moments')
      AND constraint_record.name = N'UQ_moments_id_owner';

    IF @PlacementAppliedAtUtc IS NOT NULL
       AND @MomentOwnerUniqueIndexId IS NULL
        THROW 52337, 'Rollback blocked: the Placement Moment-owner key is missing.', 1;

    IF @MomentOwnerUniqueIndexId IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.foreign_keys AS foreign_key
           WHERE foreign_key.referenced_object_id = OBJECT_ID(N'dbo.moments')
             AND foreign_key.key_index_id = @MomentOwnerUniqueIndexId
             AND foreign_key.parent_object_id <> COALESCE(@PlacementTableId, -1)
       )
        THROW 52338, 'Rollback blocked: a later table uses the Placement Moment-owner key.', 1;

    /* All refusal guards above this line run before destructive statements. */
    IF OBJECT_ID(N'dbo.usp_CreateOrReactivateMomentPlacement', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CreateOrReactivateMomentPlacement;
    IF OBJECT_ID(N'dbo.usp_ListMomentPlacementsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListMomentPlacementsForOwner;
    IF OBJECT_ID(N'dbo.usp_RemoveMomentPlacement', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_RemoveMomentPlacement;

    IF OBJECT_ID(N'dbo.moment_placements', N'U') IS NOT NULL
        DROP TABLE dbo.moment_placements;

    IF EXISTS
       (
           SELECT 1 FROM sys.key_constraints
           WHERE parent_object_id = OBJECT_ID(N'dbo.moments')
             AND name = N'UQ_moments_id_owner'
       )
        ALTER TABLE dbo.moments DROP CONSTRAINT UQ_moments_id_owner;

    IF @PlacementAppliedAtUtc IS NOT NULL
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-PLACEMENT-001"}';

        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-PLACEMENT-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
