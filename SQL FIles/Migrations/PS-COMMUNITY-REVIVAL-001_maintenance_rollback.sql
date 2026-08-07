/* PS-COMMUNITY-REVIVAL-001 rollback. Drops only the additive owner-scoped
   cleanup procedure after verifying it has not drifted. It never touches
   Community content or the existing janitor procedure. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53920, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-COMMUNITY-REVIVAL-001'
    );
    IF @AppliedAtUtc IS NULL
        THROW 53921, 'Rollback refused: PS-COMMUNITY-REVIVAL-001 is not recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc > @AppliedAtUtc)
        THROW 53922, 'Rollback refused: a later migration is present.', 1;

    DECLARE @ProcedureName sysname = N'usp_ClaimPublicCommunityMediaCleanupForOwner';
    DECLARE @HashProperty sysname = N'PS_COMMUNITY_REVIVAL_001_DEFINITION_HASH';
    DECLARE @ObjectId int = OBJECT_ID(N'dbo.' + @ProcedureName, N'P');
    DECLARE @RecordedHash nvarchar(64) =
    (
        SELECT CONVERT(nvarchar(64), value)
        FROM sys.extended_properties
        WHERE class = 1 AND major_id = @ObjectId AND minor_id = 0
          AND name = @HashProperty
    );
    DECLARE @CurrentHash nvarchar(64) = CONVERT(
        nvarchar(64), HASHBYTES('SHA2_256', OBJECT_DEFINITION(@ObjectId)), 2
    );
    IF @ObjectId IS NULL OR @RecordedHash IS NULL OR @RecordedHash <> @CurrentHash
        THROW 53923, 'Rollback refused: the owner-scoped cleanup procedure drifted.', 1;

    DROP PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanupForOwner;

    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.rolled_back',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-COMMUNITY-REVIVAL-001"}';
    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-COMMUNITY-REVIVAL-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
