SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id IN (N'PS-PLAT-003', N'PS-PLAT-004', N'PS-PLAT-005'))
        THROW 51290, 'Rollback dependent platform migrations first.', 1;
    IF OBJECT_ID(N'dbo.entity_publication_versions', N'U') IS NOT NULL DROP TABLE dbo.entity_publication_versions;
    IF OBJECT_ID(N'dbo.entity_access_grants', N'U') IS NOT NULL DROP TABLE dbo.entity_access_grants;
    IF OBJECT_ID(N'dbo.slate_entity_relations', N'U') IS NOT NULL DROP TABLE dbo.slate_entity_relations;
    IF OBJECT_ID(N'dbo.slate_entities', N'U') IS NOT NULL DROP TABLE dbo.slate_entities;
    IF OBJECT_ID(N'dbo.member_profiles', N'U') IS NOT NULL DROP TABLE dbo.member_profiles;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
