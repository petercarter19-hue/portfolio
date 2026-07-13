SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_evidence_links_item_owner') ALTER TABLE dbo.evidence_links DROP CONSTRAINT FK_evidence_links_item_owner;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_evidence_links_source_owner') ALTER TABLE dbo.evidence_links DROP CONSTRAINT FK_evidence_links_source_owner;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_evidence_links_profile') ALTER TABLE dbo.evidence_links DROP CONSTRAINT FK_evidence_links_profile;
    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'IX_evidence_links_owner' AND object_id=OBJECT_ID(N'dbo.evidence_links')) DROP INDEX IX_evidence_links_owner ON dbo.evidence_links;
    IF COL_LENGTH(N'dbo.evidence_links', N'owner_profile_id') IS NOT NULL ALTER TABLE dbo.evidence_links DROP COLUMN owner_profile_id;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_ai_proposals_target_owner') ALTER TABLE dbo.ai_proposals DROP CONSTRAINT FK_ai_proposals_target_owner;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_evidence_asset_owner') ALTER TABLE dbo.evidence_items DROP CONSTRAINT FK_evidence_asset_owner;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_evidence_entity_owner') ALTER TABLE dbo.evidence_items DROP CONSTRAINT FK_evidence_entity_owner;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_relations_to_owner') ALTER TABLE dbo.slate_entity_relations DROP CONSTRAINT FK_relations_to_owner;
    IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_relations_from_owner') ALTER TABLE dbo.slate_entity_relations DROP CONSTRAINT FK_relations_from_owner;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name=N'UQ_evidence_items_id_owner') ALTER TABLE dbo.evidence_items DROP CONSTRAINT UQ_evidence_items_id_owner;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name=N'UQ_file_assets_id_owner') ALTER TABLE dbo.file_assets DROP CONSTRAINT UQ_file_assets_id_owner;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name=N'UQ_slate_entities_id_owner') ALTER TABLE dbo.slate_entities DROP CONSTRAINT UQ_slate_entities_id_owner;
    DELETE dbo.schema_migrations WHERE migration_id=N'PS-PLAT-005';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
