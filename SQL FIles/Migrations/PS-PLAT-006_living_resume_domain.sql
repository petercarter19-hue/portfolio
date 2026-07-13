/* PS-FEAT-001 structured career domain. Additive; no current page is switched by this migration. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-005')
        THROW 51600, 'PS-PLAT-005 must be applied first.', 1;

    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_ai_proposals_id_owner')
        ALTER TABLE dbo.ai_proposals ADD CONSTRAINT UQ_ai_proposals_id_owner
            UNIQUE (proposal_id, owner_profile_id);

    IF OBJECT_ID(N'dbo.career_chapters', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_chapters
        (
            chapter_id bigint IDENTITY(1,1) NOT NULL,
            chapter_key uniqueidentifier NOT NULL CONSTRAINT DF_career_chapters_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            entity_id bigint NOT NULL,
            chapter_type nvarchar(30) NOT NULL,
            title nvarchar(300) NOT NULL,
            organization_name nvarchar(300) NULL,
            location_text nvarchar(300) NULL,
            summary nvarchar(max) NULL,
            original_member_wording nvarchar(max) NULL,
            approved_wording nvarchar(max) NULL,
            start_date date NULL,
            end_date date NULL,
            date_precision nvarchar(20) NOT NULL CONSTRAINT DF_career_chapters_precision DEFAULT N'month',
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_career_chapters_visibility DEFAULT N'private',
            approval_status nvarchar(30) NOT NULL CONSTRAINT DF_career_chapters_approval DEFAULT N'draft',
            publication_status nvarchar(30) NOT NULL CONSTRAINT DF_career_chapters_publication DEFAULT N'unpublished',
            featured bit NOT NULL CONSTRAINT DF_career_chapters_featured DEFAULT 0,
            display_order int NOT NULL CONSTRAINT DF_career_chapters_order DEFAULT 0,
            created_by_user_id int NOT NULL,
            approved_by_user_id int NULL,
            approved_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_chapters_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_chapters_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_career_chapters PRIMARY KEY (chapter_id),
            CONSTRAINT UQ_career_chapters_key UNIQUE (chapter_key),
            CONSTRAINT UQ_career_chapters_entity UNIQUE (entity_id),
            CONSTRAINT UQ_career_chapters_id_owner UNIQUE (chapter_id, owner_profile_id),
            CONSTRAINT FK_career_chapters_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_career_chapters_entity_owner FOREIGN KEY (entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT FK_career_chapters_creator FOREIGN KEY (created_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_career_chapters_approver FOREIGN KEY (approved_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_career_chapters_type CHECK (chapter_type IN (N'experience', N'education', N'credential', N'project', N'future')),
            CONSTRAINT CK_career_chapters_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
            CONSTRAINT CK_career_chapters_precision CHECK (date_precision IN (N'day', N'month', N'year', N'approximate', N'unknown')),
            CONSTRAINT CK_career_chapters_visibility CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_career_chapters_approval CHECK (approval_status IN (N'draft', N'proposed', N'approved', N'rejected')),
            CONSTRAINT CK_career_chapters_publication CHECK (publication_status IN (N'unpublished', N'scheduled', N'published', N'withdrawn')),
            CONSTRAINT CK_career_chapters_approval_actor CHECK
                ((approval_status = N'approved' AND approved_by_user_id IS NOT NULL AND approved_at_utc IS NOT NULL)
                 OR approval_status <> N'approved')
        );
        CREATE INDEX IX_career_chapters_owner_type_order
            ON dbo.career_chapters(owner_profile_id, chapter_type, deleted_at_utc, display_order);
        CREATE INDEX IX_career_chapters_public
            ON dbo.career_chapters(owner_profile_id, publication_status, visibility, featured)
            WHERE deleted_at_utc IS NULL;
    END;

    IF OBJECT_ID(N'dbo.career_experiences', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_experiences
        (
            chapter_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            role_title nvarchar(300) NOT NULL,
            employer_name nvarchar(300) NOT NULL,
            employment_type nvarchar(30) NULL,
            current_role bit NOT NULL CONSTRAINT DF_career_experiences_current DEFAULT 0,
            CONSTRAINT PK_career_experiences PRIMARY KEY (chapter_id),
            CONSTRAINT FK_career_experiences_chapter_owner FOREIGN KEY (chapter_id, owner_profile_id)
                REFERENCES dbo.career_chapters(chapter_id, owner_profile_id),
            CONSTRAINT CK_career_experiences_type CHECK
                (employment_type IS NULL OR employment_type IN (N'full_time', N'part_time', N'contract', N'freelance', N'internship', N'volunteer', N'military', N'other'))
        );
        CREATE INDEX IX_career_experiences_owner ON dbo.career_experiences(owner_profile_id, current_role);
    END;

    IF OBJECT_ID(N'dbo.career_education', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_education
        (
            chapter_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            institution_name nvarchar(300) NOT NULL,
            degree_name nvarchar(300) NULL,
            field_of_study nvarchar(300) NULL,
            education_status nvarchar(30) NOT NULL CONSTRAINT DF_career_education_status DEFAULT N'completed',
            grade_text nvarchar(100) NULL,
            CONSTRAINT PK_career_education PRIMARY KEY (chapter_id),
            CONSTRAINT FK_career_education_chapter_owner FOREIGN KEY (chapter_id, owner_profile_id)
                REFERENCES dbo.career_chapters(chapter_id, owner_profile_id),
            CONSTRAINT CK_career_education_status CHECK (education_status IN (N'planned', N'admitted', N'in_progress', N'completed', N'paused', N'withdrawn'))
        );
        CREATE INDEX IX_career_education_owner ON dbo.career_education(owner_profile_id, education_status);
    END;

    IF OBJECT_ID(N'dbo.career_credentials', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_credentials
        (
            chapter_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            credential_name nvarchar(300) NOT NULL,
            issuer_name nvarchar(300) NOT NULL,
            credential_identifier nvarchar(300) NULL,
            issue_date date NULL,
            expiration_date date NULL,
            verification_url nvarchar(1000) NULL,
            CONSTRAINT PK_career_credentials PRIMARY KEY (chapter_id),
            CONSTRAINT FK_career_credentials_chapter_owner FOREIGN KEY (chapter_id, owner_profile_id)
                REFERENCES dbo.career_chapters(chapter_id, owner_profile_id),
            CONSTRAINT CK_career_credentials_dates CHECK (expiration_date IS NULL OR issue_date IS NULL OR expiration_date >= issue_date)
        );
        CREATE INDEX IX_career_credentials_owner ON dbo.career_credentials(owner_profile_id, issuer_name);
    END;

    IF OBJECT_ID(N'dbo.career_projects', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_projects
        (
            chapter_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            project_name nvarchar(300) NOT NULL,
            project_role nvarchar(300) NULL,
            project_status nvarchar(30) NOT NULL CONSTRAINT DF_career_projects_status DEFAULT N'in_progress',
            project_url nvarchar(1000) NULL,
            CONSTRAINT PK_career_projects PRIMARY KEY (chapter_id),
            CONSTRAINT FK_career_projects_chapter_owner FOREIGN KEY (chapter_id, owner_profile_id)
                REFERENCES dbo.career_chapters(chapter_id, owner_profile_id),
            CONSTRAINT CK_career_projects_status CHECK (project_status IN (N'planned', N'in_progress', N'completed', N'paused', N'cancelled'))
        );
        CREATE INDEX IX_career_projects_owner ON dbo.career_projects(owner_profile_id, project_status);
    END;

    IF OBJECT_ID(N'dbo.career_achievements', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_achievements
        (
            achievement_id bigint IDENTITY(1,1) NOT NULL,
            achievement_key uniqueidentifier NOT NULL CONSTRAINT DF_career_achievements_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            entity_id bigint NOT NULL,
            chapter_id bigint NOT NULL,
            original_member_wording nvarchar(max) NOT NULL,
            approved_wording nvarchar(max) NULL,
            metric_value nvarchar(100) NULL,
            metric_label nvarchar(300) NULL,
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_career_achievements_visibility DEFAULT N'private',
            approval_status nvarchar(30) NOT NULL CONSTRAINT DF_career_achievements_approval DEFAULT N'draft',
            featured bit NOT NULL CONSTRAINT DF_career_achievements_featured DEFAULT 0,
            display_order int NOT NULL CONSTRAINT DF_career_achievements_order DEFAULT 0,
            created_by_user_id int NOT NULL,
            approved_by_user_id int NULL,
            approved_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_achievements_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_achievements_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_career_achievements PRIMARY KEY (achievement_id),
            CONSTRAINT UQ_career_achievements_key UNIQUE (achievement_key),
            CONSTRAINT UQ_career_achievements_entity UNIQUE (entity_id),
            CONSTRAINT FK_career_achievements_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_career_achievements_entity_owner FOREIGN KEY (entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT FK_career_achievements_chapter_owner FOREIGN KEY (chapter_id, owner_profile_id)
                REFERENCES dbo.career_chapters(chapter_id, owner_profile_id),
            CONSTRAINT FK_career_achievements_creator FOREIGN KEY (created_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_career_achievements_approver FOREIGN KEY (approved_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_career_achievements_visibility CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_career_achievements_approval CHECK (approval_status IN (N'draft', N'proposed', N'approved', N'rejected'))
        );
        CREATE INDEX IX_career_achievements_chapter
            ON dbo.career_achievements(owner_profile_id, chapter_id, featured, display_order)
            WHERE deleted_at_utc IS NULL;
    END;

    IF OBJECT_ID(N'dbo.career_skills', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_skills
        (
            skill_id bigint IDENTITY(1,1) NOT NULL,
            skill_key uniqueidentifier NOT NULL CONSTRAINT DF_career_skills_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            entity_id bigint NOT NULL,
            skill_name nvarchar(200) NOT NULL,
            skill_summary nvarchar(max) NULL,
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_career_skills_visibility DEFAULT N'private',
            approval_status nvarchar(30) NOT NULL CONSTRAINT DF_career_skills_approval DEFAULT N'draft',
            featured bit NOT NULL CONSTRAINT DF_career_skills_featured DEFAULT 0,
            display_order int NOT NULL CONSTRAINT DF_career_skills_order DEFAULT 0,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_skills_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_skills_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_career_skills PRIMARY KEY (skill_id),
            CONSTRAINT UQ_career_skills_key UNIQUE (skill_key),
            CONSTRAINT UQ_career_skills_entity UNIQUE (entity_id),
            CONSTRAINT UQ_career_skills_id_owner UNIQUE (skill_id, owner_profile_id),
            CONSTRAINT FK_career_skills_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_career_skills_entity_owner FOREIGN KEY (entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT CK_career_skills_visibility CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_career_skills_approval CHECK (approval_status IN (N'draft', N'proposed', N'approved', N'rejected'))
        );
        CREATE UNIQUE INDEX UX_career_skills_owner_name
            ON dbo.career_skills(owner_profile_id, skill_name) WHERE deleted_at_utc IS NULL;
        CREATE INDEX IX_career_skills_owner_state
            ON dbo.career_skills(owner_profile_id, approval_status, visibility, featured);
    END;

    IF OBJECT_ID(N'dbo.career_skill_links', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_skill_links
        (
            skill_link_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            skill_id bigint NOT NULL,
            source_entity_id bigint NOT NULL,
            evidence_item_id bigint NULL,
            relationship_type nvarchar(30) NOT NULL,
            approval_status nvarchar(30) NOT NULL CONSTRAINT DF_career_skill_links_approval DEFAULT N'proposed',
            strength_rank tinyint NULL,
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_skill_links_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_career_skill_links PRIMARY KEY (skill_link_id),
            CONSTRAINT UQ_career_skill_links UNIQUE (skill_id, source_entity_id, evidence_item_id, relationship_type),
            CONSTRAINT FK_career_skill_links_skill_owner FOREIGN KEY (skill_id, owner_profile_id)
                REFERENCES dbo.career_skills(skill_id, owner_profile_id),
            CONSTRAINT FK_career_skill_links_source_owner FOREIGN KEY (source_entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT FK_career_skill_links_evidence_owner FOREIGN KEY (evidence_item_id, owner_profile_id)
                REFERENCES dbo.evidence_items(evidence_item_id, owner_profile_id),
            CONSTRAINT FK_career_skill_links_creator FOREIGN KEY (created_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_career_skill_links_type CHECK (relationship_type IN (N'demonstrated_in', N'supported_by', N'learned_in', N'applied_in')),
            CONSTRAINT CK_career_skill_links_approval CHECK (approval_status IN (N'proposed', N'approved', N'rejected')),
            CONSTRAINT CK_career_skill_links_rank CHECK (strength_rank IS NULL OR strength_rank BETWEEN 1 AND 100)
        );
        CREATE INDEX IX_career_skill_links_owner_skill
            ON dbo.career_skill_links(owner_profile_id, skill_id, approval_status, strength_rank);
    END;

    IF OBJECT_ID(N'dbo.career_timeline_events', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.career_timeline_events
        (
            timeline_event_id bigint IDENTITY(1,1) NOT NULL,
            timeline_event_key uniqueidentifier NOT NULL CONSTRAINT DF_career_timeline_events_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            entity_id bigint NOT NULL,
            chapter_id bigint NOT NULL,
            event_label nvarchar(300) NOT NULL,
            event_type nvarchar(30) NOT NULL,
            start_date date NULL,
            end_date date NULL,
            date_precision nvarchar(20) NOT NULL CONSTRAINT DF_career_timeline_events_precision DEFAULT N'month',
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_career_timeline_events_visibility DEFAULT N'private',
            approval_status nvarchar(30) NOT NULL CONSTRAINT DF_career_timeline_events_approval DEFAULT N'draft',
            constellation_featured bit NOT NULL CONSTRAINT DF_career_timeline_events_featured DEFAULT 0,
            display_order int NOT NULL CONSTRAINT DF_career_timeline_events_order DEFAULT 0,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_timeline_events_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_career_timeline_events_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_career_timeline_events PRIMARY KEY (timeline_event_id),
            CONSTRAINT UQ_career_timeline_events_key UNIQUE (timeline_event_key),
            CONSTRAINT UQ_career_timeline_events_entity UNIQUE (entity_id),
            CONSTRAINT FK_career_timeline_events_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_career_timeline_events_entity_owner FOREIGN KEY (entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT FK_career_timeline_events_chapter_owner FOREIGN KEY (chapter_id, owner_profile_id)
                REFERENCES dbo.career_chapters(chapter_id, owner_profile_id),
            CONSTRAINT CK_career_timeline_events_type CHECK (event_type IN (N'experience', N'education', N'credential', N'project', N'evidence', N'future', N'transition')),
            CONSTRAINT CK_career_timeline_events_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
            CONSTRAINT CK_career_timeline_events_precision CHECK (date_precision IN (N'day', N'month', N'year', N'approximate', N'unknown')),
            CONSTRAINT CK_career_timeline_events_visibility CHECK (visibility IN (N'private', N'shared', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_career_timeline_events_approval CHECK (approval_status IN (N'draft', N'proposed', N'approved', N'rejected'))
        );
        CREATE INDEX IX_career_timeline_owner_order
            ON dbo.career_timeline_events(owner_profile_id, constellation_featured, display_order);
    END;

    IF OBJECT_ID(N'dbo.voice_drafts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.voice_drafts
        (
            voice_draft_id bigint IDENTITY(1,1) NOT NULL,
            voice_draft_key uniqueidentifier NOT NULL CONSTRAINT DF_voice_drafts_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            requested_by_user_id int NOT NULL,
            ai_proposal_id bigint NULL,
            raw_audio_asset_id bigint NULL,
            transcript_text nvarchar(max) NULL,
            draft_status nvarchar(30) NOT NULL CONSTRAINT DF_voice_drafts_status DEFAULT N'captured',
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_voice_drafts_visibility DEFAULT N'private',
            retention_until_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_voice_drafts_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_voice_drafts_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_voice_drafts PRIMARY KEY (voice_draft_id),
            CONSTRAINT UQ_voice_drafts_key UNIQUE (voice_draft_key),
            CONSTRAINT FK_voice_drafts_profile FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_voice_drafts_requester FOREIGN KEY (requested_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_voice_drafts_proposal_owner FOREIGN KEY (ai_proposal_id, owner_profile_id)
                REFERENCES dbo.ai_proposals(proposal_id, owner_profile_id),
            CONSTRAINT FK_voice_drafts_asset_owner FOREIGN KEY (raw_audio_asset_id, owner_profile_id)
                REFERENCES dbo.file_assets(asset_id, owner_profile_id),
            CONSTRAINT CK_voice_drafts_status CHECK (draft_status IN (N'captured', N'transcribed', N'interpreted', N'clarification_needed', N'previewed', N'approved', N'committed', N'cancelled', N'failed')),
            CONSTRAINT CK_voice_drafts_private CHECK (visibility = N'private')
        );
        CREATE INDEX IX_voice_drafts_owner_status
            ON dbo.voice_drafts(owner_profile_id, draft_status, created_at_utc DESC);
        CREATE UNIQUE INDEX UX_voice_drafts_proposal
            ON dbo.voice_drafts(ai_proposal_id) WHERE ai_proposal_id IS NOT NULL;
        CREATE INDEX IX_voice_drafts_retention
            ON dbo.voice_drafts(retention_until_utc) WHERE retention_until_utc IS NOT NULL;
    END;

    IF OBJECT_ID(N'dbo.content_approval_events', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.content_approval_events
        (
            approval_event_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            entity_id bigint NOT NULL,
            actor_user_id int NOT NULL,
            action_type nvarchar(30) NOT NULL,
            prior_status nvarchar(30) NULL,
            new_status nvarchar(30) NOT NULL,
            notes nvarchar(1000) NULL,
            occurred_at_utc datetime2(7) NOT NULL CONSTRAINT DF_content_approval_events_time DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_content_approval_events PRIMARY KEY (approval_event_id),
            CONSTRAINT FK_content_approval_events_entity_owner FOREIGN KEY (entity_id, owner_profile_id)
                REFERENCES dbo.slate_entities(entity_id, owner_profile_id),
            CONSTRAINT FK_content_approval_events_actor FOREIGN KEY (actor_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_content_approval_events_action CHECK (action_type IN (N'proposed', N'approved', N'rejected', N'applied', N'scheduled', N'published', N'withdrawn', N'cancelled')),
            CONSTRAINT CK_content_approval_events_status CHECK (new_status IN (N'draft', N'proposed', N'approved', N'rejected', N'applied', N'scheduled', N'published', N'withdrawn', N'cancelled'))
        );
        CREATE INDEX IX_content_approval_events_entity_time
            ON dbo.content_approval_events(owner_profile_id, entity_id, occurred_at_utc DESC);
    END;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_content_approval_events_immutable
        ON dbo.content_approval_events
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 51602, ''Content approval events are immutable.'', 1;
        END;
    ');

    IF COL_LENGTH(N'dbo.career_chapters', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'original_member_wording') IS NULL
       OR COL_LENGTH(N'dbo.voice_drafts', N'visibility') IS NULL
        THROW 51601, 'Existing PS-FEAT-001 tables are incompatible.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-006')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-PLAT-006', N'PS-FEAT-001 structured career chapters, skills, timeline, voice drafts, and approval history', N'PeerSlate SQL Foundation v0.2');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-PLAT-006"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
