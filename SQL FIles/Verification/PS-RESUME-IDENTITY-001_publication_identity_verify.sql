/* Read-only structural verification. Not engine acceptance or authority to execute. */
SET NOCOUNT ON;
IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-IDENTITY-001')
    THROW 54320, 'Pinned identity migration is absent.', 1;
IF COL_LENGTH(N'dbo.resume_publication_revisions',N'profile_identity_json') IS NULL
    THROW 54321, 'Pinned identity storage is absent.', 1;
IF ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumePublicationCommandForOwner')),N'') NOT LIKE N'%Profile identity changed. Review it again.%'
    THROW 54322, 'Atomic Profile identity validation is absent.', 1;
IF ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ResumePublicationRefreshProjectionInternal')),N'') NOT LIKE N'%@ReplaceProfileIdentity%'
    THROW 54323, 'Pinned identity inheritance is absent.', 1;
IF COL_LENGTH(N'dbo.resume_drafts',N'story_entry_key') IS NULL
    THROW 54324, 'Explicit Story binding is absent.', 1;
IF ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner')),N'') NOT LIKE N'%bind_story%'
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner')),N'') NOT LIKE N'%knowledge_item_versions%'
    THROW 54325, 'Versioned personal draft commands are absent.', 1;
IF ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumePublicationCommandForOwner')),N'') NOT LIKE N'%canonical_token%'
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumePublicationCommandForOwner')),N'') NOT LIKE N'%proposed_values_json%'
    THROW 54326, 'Integrated raw-source and saved-draft validation is absent.', 1;
IF ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_MemberVisitorAiSnapshotInternal')),N'') NOT LIKE N'%knowledge_item_versions%'
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetPublicResumePublicationBySlug')),N'') NOT LIKE N'%$.canonical_revision%'
    THROW 54327, 'Current personal evidence fences are absent.', 1;
IF COL_LENGTH(N'dbo.resume_media_command_receipts',N'catalog_source_bound') IS NULL
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwner')),N'') NOT LIKE N'%resume_catalog_assets AS asset WITH (UPDLOCK,HOLDLOCK)%'
    THROW 54328, 'Durable catalog media binding is absent.', 1;
IF ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwner')),N'') NOT LIKE N'%usp_ResumePublicationGuardLegacyMutator%'
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner')),N'') NOT LIKE N'%usp_ResumePublicationGuardLegacyMutator%'
    THROW 54329, 'Existing publication mutator guards are absent.', 1;
SELECT migration_id=N'PS-RESUME-IDENTITY-001', verification=N'structural_only',CAST(1 AS bit) AS verified;
