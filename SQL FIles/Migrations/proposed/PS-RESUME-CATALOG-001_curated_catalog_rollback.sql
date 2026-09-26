/*
Rollback for proposed PS-RESUME-CATALOG-001. Refuses if catalog rows exist.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.resume_catalog_command_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_catalog_command_receipts WITH (UPDLOCK, HOLDLOCK))
        THROW 53131, 'Rollback refused: catalog command receipts are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_catalog_assets', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_catalog_assets WITH (UPDLOCK, HOLDLOCK))
        THROW 53132, 'Rollback refused: catalog assets are stored.', 1;

    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeCatalogCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetResumeCatalogAsset;
    DROP PROCEDURE IF EXISTS dbo.usp_ResumeCatalogApplyInternal;
    DROP TABLE IF EXISTS dbo.resume_catalog_command_receipts;
    DROP TABLE IF EXISTS dbo.resume_catalog_assets;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-RESUME-CATALOG-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
