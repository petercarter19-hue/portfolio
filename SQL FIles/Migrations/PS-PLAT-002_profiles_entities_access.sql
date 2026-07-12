/* PeerSlate profiles, entity registry, access, and publication foundation. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 51200, 'PS-PLAT-001 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.member_profiles
        (
            profile_id bigint IDENTITY(1,1) NOT NULL,
            profile_key uniqueidentifier NOT NULL
                CONSTRAINT DF_member_profiles_key DEFAULT NEWSEQUENTIALID(),
            user_id int NOT NULL,
            profile_slug nvarchar(100) NULL,
            display_name nvarchar(300) NOT NULL,
            headline nvarchar(500) NULL,
            bio nvarchar(max) NULL,
            location_text nvarchar(300) NULL,
            visibility nvarchar(30) NOT NULL
                CONSTRAINT DF_member_profiles_visibility DEFAULT N'private',
            active bit NOT NULL CONSTRAINT DF_member_profiles_active DEFAULT 1,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_member_profiles_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_member_profiles_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_member_profiles PRIMARY KEY (profile_id),
            CONSTRAINT UQ_member_profiles_key UNIQUE (profile_key),
            CONSTRAINT UQ_member_profiles_user UNIQUE (user_id),
            CONSTRAINT FK_member_profiles_app_users FOREIGN KEY (user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_member_profiles_visibility
                CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public'))
        );
        CREATE UNIQUE INDEX UX_member_profiles_slug
            ON dbo.member_profiles(profile_slug) WHERE profile_slug IS NOT NULL;
    END;

    INSERT dbo.member_profiles(user_id, display_name, visibility)
    SELECT u.id, COALESCE(NULLIF(u.display_name, N''), N'PeerSlate member'), N'private'
    FROM dbo.app_users AS u
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.member_profiles AS p WHERE p.user_id = u.id
    );

    IF OBJECT_ID(N'dbo.slate_entities', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.slate_entities
        (
            entity_id bigint IDENTITY(1,1) NOT NULL,
            entity_key uniqueidentifier NOT NULL
                CONSTRAINT DF_slate_entities_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            entity_type nvarchar(100) NOT NULL,
            source_schema nvarchar(128) NULL,
            source_table nvarchar(128) NULL,
            source_record_id nvarchar(100) NULL,
            visibility nvarchar(30) NOT NULL
                CONSTRAINT DF_slate_entities_visibility DEFAULT N'private',
            approval_status nvarchar(30) NOT NULL
                CONSTRAINT DF_slate_entities_approval DEFAULT N'draft',
            publication_status nvarchar(30) NOT NULL
                CONSTRAINT DF_slate_entities_publication DEFAULT N'unpublished',
            active bit NOT NULL CONSTRAINT DF_slate_entities_active DEFAULT 1,
            deleted_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_slate_entities_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_slate_entities_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_slate_entities PRIMARY KEY (entity_id),
            CONSTRAINT UQ_slate_entities_key UNIQUE (entity_key),
            CONSTRAINT FK_slate_entities_profile FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_slate_entities_visibility
                CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_slate_entities_approval
                CHECK (approval_status IN (N'draft', N'proposed', N'approved', N'rejected')),
            CONSTRAINT CK_slate_entities_publication
                CHECK (publication_status IN (N'unpublished', N'scheduled', N'published', N'withdrawn')),
            CONSTRAINT CK_slate_entities_source_pair
                CHECK
                (
                    (source_table IS NULL AND source_record_id IS NULL)
                    OR (source_table IS NOT NULL AND source_record_id IS NOT NULL)
                )
        );
        CREATE INDEX IX_slate_entities_owner_type
            ON dbo.slate_entities(owner_profile_id, entity_type, active);
        CREATE INDEX IX_slate_entities_audience
            ON dbo.slate_entities(visibility, publication_status, active);
        CREATE UNIQUE INDEX UX_slate_entities_source
            ON dbo.slate_entities(owner_profile_id, source_schema, source_table, source_record_id)
            WHERE source_table IS NOT NULL AND source_record_id IS NOT NULL;
    END;

    IF OBJECT_ID(N'dbo.slate_entity_relations', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.slate_entity_relations
        (
            relation_id bigint IDENTITY(1,1) NOT NULL,
            relation_key uniqueidentifier NOT NULL
                CONSTRAINT DF_slate_entity_relations_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            from_entity_id bigint NOT NULL,
            to_entity_id bigint NOT NULL,
            relation_type nvarchar(100) NOT NULL,
            label nvarchar(300) NULL,
            provenance_type nvarchar(50) NOT NULL
                CONSTRAINT DF_slate_entity_relations_provenance DEFAULT N'member',
            confidence decimal(5,4) NULL,
            approval_status nvarchar(30) NOT NULL
                CONSTRAINT DF_slate_entity_relations_approval DEFAULT N'approved',
            visibility nvarchar(30) NOT NULL
                CONSTRAINT DF_slate_entity_relations_visibility DEFAULT N'private',
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_slate_entity_relations_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_slate_entity_relations PRIMARY KEY (relation_id),
            CONSTRAINT UQ_slate_entity_relations_key UNIQUE (relation_key),
            CONSTRAINT UQ_slate_entity_relations_path
                UNIQUE (from_entity_id, to_entity_id, relation_type),
            CONSTRAINT FK_slate_entity_relations_profile FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_slate_entity_relations_from FOREIGN KEY (from_entity_id)
                REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_slate_entity_relations_to FOREIGN KEY (to_entity_id)
                REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_slate_entity_relations_creator FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_slate_entity_relations_distinct CHECK (from_entity_id <> to_entity_id),
            CONSTRAINT CK_slate_entity_relations_provenance
                CHECK (provenance_type IN (N'member', N'imported', N'ai_proposed', N'system')),
            CONSTRAINT CK_slate_entity_relations_confidence
                CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
            CONSTRAINT CK_slate_entity_relations_approval
                CHECK (approval_status IN (N'proposed', N'approved', N'rejected')),
            CONSTRAINT CK_slate_entity_relations_visibility
                CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public'))
        );
        CREATE INDEX IX_slate_entity_relations_owner
            ON dbo.slate_entity_relations(owner_profile_id, relation_type);
        CREATE INDEX IX_slate_entity_relations_to
            ON dbo.slate_entity_relations(to_entity_id, relation_type);
    END;

    IF OBJECT_ID(N'dbo.entity_access_grants', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.entity_access_grants
        (
            grant_id bigint IDENTITY(1,1) NOT NULL,
            entity_id bigint NOT NULL,
            grantee_user_id int NOT NULL,
            access_level nvarchar(30) NOT NULL,
            granted_by_user_id int NOT NULL,
            granted_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_entity_access_grants_granted DEFAULT SYSUTCDATETIME(),
            expires_at_utc datetime2(7) NULL,
            revoked_at_utc datetime2(7) NULL,
            CONSTRAINT PK_entity_access_grants PRIMARY KEY (grant_id),
            CONSTRAINT FK_entity_access_grants_entity FOREIGN KEY (entity_id)
                REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_entity_access_grants_grantee FOREIGN KEY (grantee_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_entity_access_grants_grantor FOREIGN KEY (granted_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_entity_access_grants_level
                CHECK (access_level IN (N'view', N'comment', N'edit')),
            CONSTRAINT CK_entity_access_grants_expiry
                CHECK (expires_at_utc IS NULL OR expires_at_utc > granted_at_utc)
        );
        CREATE UNIQUE INDEX UX_entity_access_grants_active
            ON dbo.entity_access_grants(entity_id, grantee_user_id)
            WHERE revoked_at_utc IS NULL;
        CREATE INDEX IX_entity_access_grants_grantee
            ON dbo.entity_access_grants(grantee_user_id, revoked_at_utc, expires_at_utc);
    END;

    IF OBJECT_ID(N'dbo.entity_publication_versions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.entity_publication_versions
        (
            publication_version_id bigint IDENTITY(1,1) NOT NULL,
            entity_id bigint NOT NULL,
            version_number int NOT NULL,
            audience nvarchar(30) NOT NULL,
            publication_status nvarchar(30) NOT NULL,
            snapshot_json nvarchar(max) NOT NULL,
            source_hash_sha256 char(64) NULL,
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_entity_publications_created DEFAULT SYSUTCDATETIME(),
            scheduled_at_utc datetime2(7) NULL,
            published_at_utc datetime2(7) NULL,
            withdrawn_at_utc datetime2(7) NULL,
            CONSTRAINT PK_entity_publication_versions PRIMARY KEY (publication_version_id),
            CONSTRAINT UQ_entity_publication_versions UNIQUE (entity_id, version_number),
            CONSTRAINT FK_entity_publications_entity FOREIGN KEY (entity_id)
                REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_entity_publications_creator FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_entity_publications_version CHECK (version_number > 0),
            CONSTRAINT CK_entity_publications_audience
                CHECK (audience IN (N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_entity_publications_status
                CHECK (publication_status IN (N'draft', N'scheduled', N'published', N'withdrawn')),
            CONSTRAINT CK_entity_publications_snapshot CHECK (ISJSON(snapshot_json) = 1)
        );
        CREATE INDEX IX_entity_publications_status
            ON dbo.entity_publication_versions(entity_id, publication_status, created_at_utc DESC);
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-PLAT-002', N'Profiles, entity relationships, access grants, and publication versions', N'PeerSlate SQL Foundation v0.1');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-PLAT-002"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
