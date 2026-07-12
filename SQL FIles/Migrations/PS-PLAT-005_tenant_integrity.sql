/* Enforce same-profile ownership across entity, evidence, and AI relationships. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-004')
        THROW 51500, 'PS-PLAT-004 must be applied first.', 1;

    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_slate_entities_id_owner')
        ALTER TABLE dbo.slate_entities ADD CONSTRAINT UQ_slate_entities_id_owner UNIQUE (entity_id, owner_profile_id);
    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_file_assets_id_owner')
        ALTER TABLE dbo.file_assets ADD CONSTRAINT UQ_file_assets_id_owner UNIQUE (asset_id, owner_profile_id);
    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_evidence_items_id_owner')
        ALTER TABLE dbo.evidence_items ADD CONSTRAINT UQ_evidence_items_id_owner UNIQUE (evidence_item_id, owner_profile_id);

    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_relations_from_owner')
        ALTER TABLE dbo.slate_entity_relations WITH CHECK ADD CONSTRAINT FK_relations_from_owner
            FOREIGN KEY (from_entity_id, owner_profile_id) REFERENCES dbo.slate_entities(entity_id, owner_profile_id);
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_relations_to_owner')
        ALTER TABLE dbo.slate_entity_relations WITH CHECK ADD CONSTRAINT FK_relations_to_owner
            FOREIGN KEY (to_entity_id, owner_profile_id) REFERENCES dbo.slate_entities(entity_id, owner_profile_id);
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_evidence_entity_owner')
        ALTER TABLE dbo.evidence_items WITH CHECK ADD CONSTRAINT FK_evidence_entity_owner
            FOREIGN KEY (entity_id, owner_profile_id) REFERENCES dbo.slate_entities(entity_id, owner_profile_id);
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_evidence_asset_owner')
        ALTER TABLE dbo.evidence_items WITH CHECK ADD CONSTRAINT FK_evidence_asset_owner
            FOREIGN KEY (asset_id, owner_profile_id) REFERENCES dbo.file_assets(asset_id, owner_profile_id);
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ai_proposals_target_owner')
        ALTER TABLE dbo.ai_proposals WITH CHECK ADD CONSTRAINT FK_ai_proposals_target_owner
            FOREIGN KEY (target_entity_id, owner_profile_id) REFERENCES dbo.slate_entities(entity_id, owner_profile_id);

    IF COL_LENGTH(N'dbo.evidence_links', N'owner_profile_id') IS NULL
        EXEC(N'ALTER TABLE dbo.evidence_links ADD owner_profile_id bigint NULL;');

    EXEC(N'
        UPDATE link
        SET owner_profile_id = entity.owner_profile_id
        FROM dbo.evidence_links AS link
        JOIN dbo.slate_entities AS entity ON entity.entity_id = link.source_entity_id
        WHERE link.owner_profile_id IS NULL;
    ');

    EXEC(N'
        IF EXISTS (SELECT 1 FROM dbo.evidence_links WHERE owner_profile_id IS NULL)
            THROW 51501, ''Evidence links could not be assigned to an owning profile.'', 1;
    ');

    EXEC(N'ALTER TABLE dbo.evidence_links ALTER COLUMN owner_profile_id bigint NOT NULL;');

    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_evidence_links_profile')
        EXEC(N'ALTER TABLE dbo.evidence_links WITH CHECK ADD CONSTRAINT FK_evidence_links_profile
            FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id);');
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_evidence_links_source_owner')
        EXEC(N'ALTER TABLE dbo.evidence_links WITH CHECK ADD CONSTRAINT FK_evidence_links_source_owner
            FOREIGN KEY (source_entity_id, owner_profile_id) REFERENCES dbo.slate_entities(entity_id, owner_profile_id);');
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_evidence_links_item_owner')
        EXEC(N'ALTER TABLE dbo.evidence_links WITH CHECK ADD CONSTRAINT FK_evidence_links_item_owner
            FOREIGN KEY (evidence_item_id, owner_profile_id) REFERENCES dbo.evidence_items(evidence_item_id, owner_profile_id);');

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_evidence_links_owner')
        EXEC(N'CREATE INDEX IX_evidence_links_owner ON dbo.evidence_links(owner_profile_id, approval_status);');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-005')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-PLAT-005', N'Composite tenant-integrity constraints for platform relationships', N'PeerSlate SQL Foundation v0.1');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied', @EntityType=N'database_migration', @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-PLAT-005"}';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
