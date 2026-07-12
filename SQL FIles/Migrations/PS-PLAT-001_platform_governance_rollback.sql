SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id IN (N'PS-PLAT-002', N'PS-PLAT-003', N'PS-PLAT-004', N'PS-PLAT-005')
    )
        THROW 51101, 'Rollback dependent platform migrations first.', 1;

    IF OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_AppendAuditEvent;
    IF OBJECT_ID(N'dbo.trg_audit_events_immutable', N'TR') IS NOT NULL
        DROP TRIGGER dbo.trg_audit_events_immutable;
    IF OBJECT_ID(N'dbo.audit_events', N'U') IS NOT NULL
        DROP TABLE dbo.audit_events;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
    BEGIN
        DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-001';
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations)
            DROP TABLE dbo.schema_migrations;
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
