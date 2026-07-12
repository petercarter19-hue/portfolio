/* PeerSlate evidence, protected asset metadata, and reviewable AI proposals. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002')
        THROW 51300, 'PS-PLAT-002 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.file_assets', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.file_assets
        (
            asset_id bigint IDENTITY(1,1) NOT NULL,
            asset_key uniqueidentifier NOT NULL CONSTRAINT DF_file_assets_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            storage_provider nvarchar(50) NOT NULL,
            container_name nvarchar(200) NOT NULL,
            object_key nvarchar(1000) NOT NULL,
            original_file_name nvarchar(500) NOT NULL,
            content_type nvarchar(200) NULL,
            byte_size bigint NULL,
            sha256_hash char(64) NULL,
            scan_status nvarchar(30) NOT NULL CONSTRAINT DF_file_assets_scan DEFAULT N'pending',
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_file_assets_visibility DEFAULT N'private',
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_file_assets_created DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            CONSTRAINT PK_file_assets PRIMARY KEY (asset_id),
            CONSTRAINT UQ_file_assets_key UNIQUE (asset_key),
            CONSTRAINT UQ_file_assets_storage UNIQUE (storage_provider, container_name, object_key),
            CONSTRAINT FK_file_assets_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_file_assets_size CHECK (byte_size IS NULL OR byte_size >= 0),
            CONSTRAINT CK_file_assets_scan CHECK (scan_status IN (N'pending', N'clean', N'quarantined', N'failed')),
            CONSTRAINT CK_file_assets_visibility CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public'))
        );
        CREATE INDEX IX_file_assets_owner ON dbo.file_assets(owner_profile_id, deleted_at_utc, created_at_utc DESC);
    END;

    IF OBJECT_ID(N'dbo.evidence_items', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.evidence_items
        (
            evidence_item_id bigint IDENTITY(1,1) NOT NULL,
            evidence_key uniqueidentifier NOT NULL CONSTRAINT DF_evidence_items_key DEFAULT NEWSEQUENTIALID(),
            entity_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            asset_id bigint NULL,
            title nvarchar(500) NOT NULL,
            summary nvarchar(max) NULL,
            evidence_type nvarchar(100) NOT NULL,
            source_kind nvarchar(50) NOT NULL,
            source_url nvarchar(1000) NULL,
            provenance_json nvarchar(max) NULL,
            evidence_state nvarchar(50) NOT NULL,
            verification_status nvarchar(30) NOT NULL CONSTRAINT DF_evidence_items_verification DEFAULT N'unreviewed',
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_evidence_items_visibility DEFAULT N'private',
            verified_by_user_id int NULL,
            verified_at_utc datetime2(7) NULL,
            expires_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_evidence_items_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_evidence_items_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_evidence_items PRIMARY KEY (evidence_item_id),
            CONSTRAINT UQ_evidence_items_key UNIQUE (evidence_key),
            CONSTRAINT UQ_evidence_items_entity UNIQUE (entity_id),
            CONSTRAINT FK_evidence_items_entity FOREIGN KEY (entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_evidence_items_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_evidence_items_asset FOREIGN KEY (asset_id) REFERENCES dbo.file_assets(asset_id),
            CONSTRAINT FK_evidence_items_verifier FOREIGN KEY (verified_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_evidence_items_source CHECK (source_kind IN (N'member', N'document', N'public_artifact', N'reference', N'credential', N'employer')),
            CONSTRAINT CK_evidence_items_state CHECK (evidence_state IN (N'self_reported', N'document_supported', N'public_artifact', N'reference_confirmed', N'verified_credential', N'employer_verified')),
            CONSTRAINT CK_evidence_items_verification CHECK (verification_status IN (N'unreviewed', N'pending', N'verified', N'rejected', N'expired')),
            CONSTRAINT CK_evidence_items_visibility CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_evidence_items_provenance CHECK (provenance_json IS NULL OR ISJSON(provenance_json) = 1)
        );
        CREATE INDEX IX_evidence_items_owner_state ON dbo.evidence_items(owner_profile_id, verification_status, visibility);
        CREATE INDEX IX_evidence_items_asset ON dbo.evidence_items(asset_id) WHERE asset_id IS NOT NULL;
    END;

    IF OBJECT_ID(N'dbo.evidence_links', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.evidence_links
        (
            evidence_link_id bigint IDENTITY(1,1) NOT NULL,
            source_entity_id bigint NOT NULL,
            evidence_item_id bigint NOT NULL,
            relationship_type nvarchar(50) NOT NULL,
            approval_status nvarchar(30) NOT NULL CONSTRAINT DF_evidence_links_approval DEFAULT N'proposed',
            strength_rank tinyint NULL,
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_evidence_links_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_evidence_links PRIMARY KEY (evidence_link_id),
            CONSTRAINT UQ_evidence_links UNIQUE (source_entity_id, evidence_item_id, relationship_type),
            CONSTRAINT FK_evidence_links_source FOREIGN KEY (source_entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_evidence_links_evidence FOREIGN KEY (evidence_item_id) REFERENCES dbo.evidence_items(evidence_item_id),
            CONSTRAINT FK_evidence_links_creator FOREIGN KEY (created_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_evidence_links_type CHECK (relationship_type IN (N'supports', N'proves', N'illustrates', N'contradicts', N'context')),
            CONSTRAINT CK_evidence_links_approval CHECK (approval_status IN (N'proposed', N'approved', N'rejected')),
            CONSTRAINT CK_evidence_links_rank CHECK (strength_rank IS NULL OR strength_rank BETWEEN 1 AND 100)
        );
        CREATE INDEX IX_evidence_links_item ON dbo.evidence_links(evidence_item_id, approval_status);
    END;

    IF OBJECT_ID(N'dbo.ai_proposals', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.ai_proposals
        (
            proposal_id bigint IDENTITY(1,1) NOT NULL,
            proposal_key uniqueidentifier NOT NULL CONSTRAINT DF_ai_proposals_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            requested_by_user_id int NOT NULL,
            target_entity_id bigint NULL,
            proposal_type nvarchar(100) NOT NULL,
            transcript_text nvarchar(max) NULL,
            interpreted_intent_json nvarchar(max) NULL,
            source_context_json nvarchar(max) NULL,
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_ai_proposals_visibility DEFAULT N'private',
            proposal_status nvarchar(30) NOT NULL CONSTRAINT DF_ai_proposals_status DEFAULT N'proposed',
            model_identifier nvarchar(200) NULL,
            prompt_version nvarchar(100) NULL,
            reviewed_by_user_id int NULL,
            reviewed_at_utc datetime2(7) NULL,
            retention_until_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_ai_proposals_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_ai_proposals_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_ai_proposals PRIMARY KEY (proposal_id),
            CONSTRAINT UQ_ai_proposals_key UNIQUE (proposal_key),
            CONSTRAINT FK_ai_proposals_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_ai_proposals_requester FOREIGN KEY (requested_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_ai_proposals_target FOREIGN KEY (target_entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_ai_proposals_reviewer FOREIGN KEY (reviewed_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_ai_proposals_visibility CHECK (visibility = N'private'),
            CONSTRAINT CK_ai_proposals_status CHECK (proposal_status IN (N'proposed', N'clarification_needed', N'approved', N'rejected', N'cancelled', N'applied')),
            CONSTRAINT CK_ai_proposals_intent CHECK (interpreted_intent_json IS NULL OR ISJSON(interpreted_intent_json) = 1),
            CONSTRAINT CK_ai_proposals_context CHECK (source_context_json IS NULL OR ISJSON(source_context_json) = 1)
        );
        CREATE INDEX IX_ai_proposals_owner_status ON dbo.ai_proposals(owner_profile_id, proposal_status, created_at_utc DESC);
    END;

    IF OBJECT_ID(N'dbo.ai_proposal_changes', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.ai_proposal_changes
        (
            proposal_change_id bigint IDENTITY(1,1) NOT NULL,
            proposal_id bigint NOT NULL,
            change_order int NOT NULL,
            target_entity_id bigint NULL,
            source_entity_id bigint NULL,
            field_path nvarchar(500) NOT NULL,
            original_value nvarchar(max) NULL,
            proposed_value nvarchar(max) NULL,
            proposed_visibility nvarchar(30) NOT NULL CONSTRAINT DF_ai_proposal_changes_visibility DEFAULT N'private',
            decision_status nvarchar(30) NOT NULL CONSTRAINT DF_ai_proposal_changes_decision DEFAULT N'pending',
            member_edited_value nvarchar(max) NULL,
            CONSTRAINT PK_ai_proposal_changes PRIMARY KEY (proposal_change_id),
            CONSTRAINT UQ_ai_proposal_changes_order UNIQUE (proposal_id, change_order),
            CONSTRAINT FK_ai_proposal_changes_proposal FOREIGN KEY (proposal_id) REFERENCES dbo.ai_proposals(proposal_id),
            CONSTRAINT FK_ai_proposal_changes_target FOREIGN KEY (target_entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_ai_proposal_changes_source FOREIGN KEY (source_entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT CK_ai_proposal_changes_order CHECK (change_order > 0),
            CONSTRAINT CK_ai_proposal_changes_visibility CHECK (proposed_visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_ai_proposal_changes_decision CHECK (decision_status IN (N'pending', N'accepted', N'edited', N'rejected'))
        );
        CREATE INDEX IX_ai_proposal_changes_target ON dbo.ai_proposal_changes(target_entity_id) WHERE target_entity_id IS NOT NULL;
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-003')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-PLAT-003', N'Evidence provenance, protected file metadata, and reviewable AI proposals', N'PeerSlate SQL Foundation v0.1');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied', @EntityType=N'database_migration', @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-PLAT-003"}';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
