SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id IN (N'PS-PLAT-004', N'PS-PLAT-005'))
        THROW 51390, 'Rollback dependent platform migrations first.', 1;
    IF OBJECT_ID(N'dbo.ai_proposal_changes', N'U') IS NOT NULL DROP TABLE dbo.ai_proposal_changes;
    IF OBJECT_ID(N'dbo.ai_proposals', N'U') IS NOT NULL DROP TABLE dbo.ai_proposals;
    IF OBJECT_ID(N'dbo.evidence_links', N'U') IS NOT NULL DROP TABLE dbo.evidence_links;
    IF OBJECT_ID(N'dbo.evidence_items', N'U') IS NOT NULL DROP TABLE dbo.evidence_items;
    IF OBJECT_ID(N'dbo.file_assets', N'U') IS NOT NULL DROP TABLE dbo.file_assets;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-003';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
