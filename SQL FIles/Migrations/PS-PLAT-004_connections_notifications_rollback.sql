SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-005')
        THROW 51490, 'Rollback PS-PLAT-005 first.', 1;
    IF OBJECT_ID(N'dbo.user_consents', N'U') IS NOT NULL DROP TABLE dbo.user_consents;
    IF OBJECT_ID(N'dbo.notification_preferences', N'U') IS NOT NULL DROP TABLE dbo.notification_preferences;
    IF OBJECT_ID(N'dbo.notifications', N'U') IS NOT NULL DROP TABLE dbo.notifications;
    IF OBJECT_ID(N'dbo.user_reports', N'U') IS NOT NULL DROP TABLE dbo.user_reports;
    IF OBJECT_ID(N'dbo.user_blocks', N'U') IS NOT NULL DROP TABLE dbo.user_blocks;
    IF OBJECT_ID(N'dbo.member_connections', N'U') IS NOT NULL DROP TABLE dbo.member_connections;
    IF OBJECT_ID(N'dbo.connection_requests', N'U') IS NOT NULL DROP TABLE dbo.connection_requests;
    IF OBJECT_ID(N'dbo.connection_preferences', N'U') IS NOT NULL DROP TABLE dbo.connection_preferences;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-004';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
