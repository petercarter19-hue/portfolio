/* Roll back PS-FEAT-001 only before application code stores member career data. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS
    (
        SELECT 1
        FROM
        (
            SELECT COUNT_BIG(*) AS row_count FROM dbo.content_approval_events
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.voice_drafts
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_timeline_events
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_skill_links
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_skills
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_achievements
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_projects
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_credentials
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_education
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_experiences
            UNION ALL SELECT COUNT_BIG(*) FROM dbo.career_chapters
        ) AS counts
        WHERE counts.row_count > 0
    )
        THROW 51690, 'PS-PLAT-006 contains member data. Export and complete a retention review before rollback.', 1;

    IF OBJECT_ID(N'dbo.content_approval_events', N'U') IS NOT NULL DROP TABLE dbo.content_approval_events;
    IF OBJECT_ID(N'dbo.voice_drafts', N'U') IS NOT NULL DROP TABLE dbo.voice_drafts;
    IF OBJECT_ID(N'dbo.career_timeline_events', N'U') IS NOT NULL DROP TABLE dbo.career_timeline_events;
    IF OBJECT_ID(N'dbo.career_skill_links', N'U') IS NOT NULL DROP TABLE dbo.career_skill_links;
    IF OBJECT_ID(N'dbo.career_skills', N'U') IS NOT NULL DROP TABLE dbo.career_skills;
    IF OBJECT_ID(N'dbo.career_achievements', N'U') IS NOT NULL DROP TABLE dbo.career_achievements;
    IF OBJECT_ID(N'dbo.career_projects', N'U') IS NOT NULL DROP TABLE dbo.career_projects;
    IF OBJECT_ID(N'dbo.career_credentials', N'U') IS NOT NULL DROP TABLE dbo.career_credentials;
    IF OBJECT_ID(N'dbo.career_education', N'U') IS NOT NULL DROP TABLE dbo.career_education;
    IF OBJECT_ID(N'dbo.career_experiences', N'U') IS NOT NULL DROP TABLE dbo.career_experiences;
    IF OBJECT_ID(N'dbo.career_chapters', N'U') IS NOT NULL DROP TABLE dbo.career_chapters;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_ai_proposals_id_owner')
        ALTER TABLE dbo.ai_proposals DROP CONSTRAINT UQ_ai_proposals_id_owner;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-PLAT-006';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
