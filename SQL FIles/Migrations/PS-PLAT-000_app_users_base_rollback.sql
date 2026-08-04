SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id IN
        (
            N'PS-PLAT-001', N'PS-PLAT-002', N'PS-PLAT-003', N'PS-PLAT-004',
            N'PS-PLAT-005', N'PS-PLAT-006', N'PS-PLAT-007', N'PS-AUTH-001'
        )
    )
        THROW 51010, 'Rollback dependent platform migrations first.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NOT NULL
    BEGIN
        IF EXISTS (SELECT 1 FROM dbo.app_users)
            THROW 51011, 'app_users contains member rows; refusing rollback.', 1;
        DROP TABLE dbo.app_users;
    END;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
    BEGIN
        DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-000';
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations)
            DROP TABLE dbo.schema_migrations;
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
