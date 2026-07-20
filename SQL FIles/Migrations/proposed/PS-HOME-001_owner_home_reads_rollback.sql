/* ============================================================
   PS-HOME-001 ROLLBACK - guarded read-procedure removal

   Removes only the exact unchanged Home procedure and its ledger
   entry. It refuses later migrations or definition drift.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 52530, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-HOME-001';

    IF @AppliedAtUtc IS NULL
       AND OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P') IS NOT NULL
        THROW 52531, 'Rollback refused: the Home procedure exists without its migration record.', 1;

    IF @AppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM dbo.schema_migrations AS migration
           WHERE migration.applied_at_utc > @AppliedAtUtc
       )
        THROW 52532, 'Rollback refused: a later migration is present.', 1;

    IF @AppliedAtUtc IS NOT NULL
       AND
       (
           OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P') IS NULL
           OR NOT EXISTS
           (
               SELECT 1
               FROM sys.extended_properties AS property
               WHERE property.class = 1
                 AND property.major_id = OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P')
                 AND property.minor_id = 0
                 AND property.name = N'PS_HOME_001_DEFINITION_HASH'
                 AND CONVERT(nvarchar(64), property.value) = CONVERT
                 (
                     nvarchar(64),
                     HASHBYTES
                     (
                         'SHA2_256',
                         OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P'))
                     ),
                     2
                 )
           )
       )
        THROW 52533, 'Rollback refused: the protected Home procedure has definition drift.', 1;

    IF OBJECT_ID(N'dbo.usp_GetOwnerHomeForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOwnerHomeForOwner;

    IF @AppliedAtUtc IS NOT NULL
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-HOME-001"}';

        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-HOME-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
