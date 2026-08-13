/* PS-CONNECT-002 rollback is deliberately limited to its additive objects.
   It never changes PS-PLAT-004 request, connection, or block history. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CONNECT-002')
        THROW 53370, 'PS-CONNECT-002 is not applied.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id NOT IN (N'PS-PLAT-000', N'PS-PLAT-001', N'PS-PLAT-002', N'PS-PLAT-003', N'PS-PLAT-004', N'PS-PLAT-005', N'PS-PLAT-006', N'PS-PLAT-007', N'PS-AUTH-001', N'PS-CONNECT-002')
    )
        THROW 53371, 'PS-CONNECT-002 rollback refused because a later or unrelated migration is present.', 1;
    IF EXISTS (SELECT 1 FROM dbo.connection_relationship_commands)
       OR EXISTS (SELECT 1 FROM dbo.connection_relationship_events)
       OR EXISTS (SELECT 1 FROM dbo.connection_relationship_states)
        THROW 53372, 'PS-CONNECT-002 rollback refused because relationship data exists.', 1;

    IF OBJECT_ID(N'dbo.usp_GetConnectionRelationshipCommandForActor', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetConnectionRelationshipCommandForActor;
    IF OBJECT_ID(N'dbo.usp_GetConnectionRelationshipSnapshotForActor', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetConnectionRelationshipSnapshotForActor;
    IF OBJECT_ID(N'dbo.usp_CommitConnectionRelationshipCommandForActor', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CommitConnectionRelationshipCommandForActor;
    IF OBJECT_ID(N'dbo.connection_relationship_commands', N'U') IS NOT NULL
        DROP TABLE dbo.connection_relationship_commands;
    IF OBJECT_ID(N'dbo.connection_relationship_events', N'U') IS NOT NULL
        DROP TABLE dbo.connection_relationship_events;
    IF OBJECT_ID(N'dbo.connection_relationship_states', N'U') IS NOT NULL
        DROP TABLE dbo.connection_relationship_states;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-CONNECT-002';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
