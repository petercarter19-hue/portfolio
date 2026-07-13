/* Stable, side-effect-free owner and public Living Resume read contracts. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-006')
        THROW 51700, 'PS-PLAT-006 must be applied first.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOwnerLivingResume
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 51701, ''Living Resume owner profile not found.'', 1;

            SELECT
                profile.profile_key, profile.profile_slug, profile.display_name,
                profile.headline, profile.bio, profile.location_text,
                profile.visibility, profile.updated_at_utc, profile.row_version
            FROM dbo.member_profiles AS profile
            WHERE profile.profile_id = @ProfileId;

            SELECT
                chapter.chapter_key, chapter.chapter_type, chapter.title,
                chapter.organization_name, chapter.location_text, chapter.summary,
                chapter.original_member_wording, chapter.approved_wording,
                chapter.start_date, chapter.end_date, chapter.date_precision,
                chapter.visibility, chapter.approval_status, chapter.publication_status,
                chapter.featured, chapter.display_order, chapter.updated_at_utc,
                experience.role_title, experience.employer_name, experience.employment_type,
                experience.current_role, education.institution_name, education.degree_name,
                education.field_of_study, education.education_status, education.grade_text,
                credential.credential_name, credential.issuer_name,
                credential.credential_identifier, credential.issue_date,
                credential.expiration_date, credential.verification_url,
                project.project_name, project.project_role, project.project_status,
                project.project_url
            FROM dbo.career_chapters AS chapter
            LEFT JOIN dbo.career_experiences AS experience ON experience.chapter_id = chapter.chapter_id
            LEFT JOIN dbo.career_education AS education ON education.chapter_id = chapter.chapter_id
            LEFT JOIN dbo.career_credentials AS credential ON credential.chapter_id = chapter.chapter_id
            LEFT JOIN dbo.career_projects AS project ON project.chapter_id = chapter.chapter_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.start_date, chapter.chapter_id;

            SELECT
                achievement.achievement_key, chapter.chapter_key,
                achievement.original_member_wording, achievement.approved_wording,
                achievement.metric_value, achievement.metric_label,
                achievement.visibility, achievement.approval_status,
                achievement.featured, achievement.display_order,
                achievement.updated_at_utc
            FROM dbo.career_achievements AS achievement
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = achievement.chapter_id
            WHERE achievement.owner_profile_id = @ProfileId
              AND achievement.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, achievement.display_order, achievement.achievement_id;

            SELECT
                skill.skill_key, skill.skill_name, skill.skill_summary,
                skill.visibility, skill.approval_status, skill.featured,
                skill.display_order, skill.updated_at_utc,
                SUM(CASE WHEN link.approval_status = N''approved'' THEN 1 ELSE 0 END) AS approved_proof_count
            FROM dbo.career_skills AS skill
            LEFT JOIN dbo.career_skill_links AS link ON link.skill_id = skill.skill_id
            WHERE skill.owner_profile_id = @ProfileId
              AND skill.deleted_at_utc IS NULL
            GROUP BY
                skill.skill_id, skill.skill_key, skill.skill_name, skill.skill_summary,
                skill.visibility, skill.approval_status, skill.featured,
                skill.display_order, skill.updated_at_utc
            ORDER BY skill.featured DESC, skill.display_order, skill.skill_name;

            SELECT
                skill.skill_key, source_entity.entity_key AS source_entity_key,
                evidence.evidence_key, link.relationship_type,
                link.approval_status, link.strength_rank,
                evidence.title AS evidence_title, evidence.evidence_state,
                evidence.verification_status, evidence.visibility AS evidence_visibility
            FROM dbo.career_skill_links AS link
            JOIN dbo.career_skills AS skill ON skill.skill_id = link.skill_id
            JOIN dbo.slate_entities AS source_entity ON source_entity.entity_id = link.source_entity_id
            LEFT JOIN dbo.evidence_items AS evidence ON evidence.evidence_item_id = link.evidence_item_id
            WHERE link.owner_profile_id = @ProfileId
            ORDER BY skill.display_order, link.strength_rank, link.skill_link_id;

            SELECT
                timeline.timeline_event_key, chapter.chapter_key,
                timeline.event_label, timeline.event_type,
                timeline.start_date, timeline.end_date, timeline.date_precision,
                timeline.visibility, timeline.approval_status,
                timeline.constellation_featured, timeline.display_order,
                timeline.updated_at_utc
            FROM dbo.career_timeline_events AS timeline
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = timeline.chapter_id
            WHERE timeline.owner_profile_id = @ProfileId
            ORDER BY timeline.display_order, timeline.start_date, timeline.timeline_event_id;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetPublicLivingResumeBySlug
            @ProfileSlug nvarchar(100)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            WHERE profile.profile_slug = @ProfileSlug
              AND profile.active = 1
              AND profile.visibility = N''public'';

            IF @ProfileId IS NULL
                THROW 51702, ''Public Living Resume not found.'', 1;

            SELECT
                profile.profile_key, profile.profile_slug, profile.display_name,
                profile.headline, profile.bio, profile.location_text,
                profile.updated_at_utc
            FROM dbo.member_profiles AS profile
            WHERE profile.profile_id = @ProfileId;

            SELECT
                chapter.chapter_key, chapter.chapter_type, chapter.title,
                chapter.organization_name, chapter.location_text,
                COALESCE(chapter.approved_wording, chapter.summary) AS summary,
                chapter.start_date, chapter.end_date, chapter.date_precision,
                chapter.featured, chapter.display_order,
                experience.role_title, experience.employer_name, experience.employment_type,
                experience.current_role, education.institution_name, education.degree_name,
                education.field_of_study, education.education_status, education.grade_text,
                credential.credential_name, credential.issuer_name,
                credential.issue_date, credential.expiration_date, credential.verification_url,
                project.project_name, project.project_role, project.project_status,
                project.project_url
            FROM dbo.career_chapters AS chapter
            LEFT JOIN dbo.career_experiences AS experience ON experience.chapter_id = chapter.chapter_id
            LEFT JOIN dbo.career_education AS education ON education.chapter_id = chapter.chapter_id
            LEFT JOIN dbo.career_credentials AS credential ON credential.chapter_id = chapter.chapter_id
            LEFT JOIN dbo.career_projects AS project ON project.chapter_id = chapter.chapter_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
              AND chapter.visibility = N''public''
              AND chapter.approval_status = N''approved''
              AND chapter.publication_status = N''published''
            ORDER BY chapter.display_order, chapter.start_date, chapter.chapter_id;

            SELECT
                achievement.achievement_key, chapter.chapter_key,
                achievement.approved_wording, achievement.metric_value,
                achievement.metric_label, achievement.featured,
                achievement.display_order
            FROM dbo.career_achievements AS achievement
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = achievement.chapter_id
            WHERE achievement.owner_profile_id = @ProfileId
              AND achievement.deleted_at_utc IS NULL
              AND achievement.visibility = N''public''
              AND achievement.approval_status = N''approved''
              AND chapter.visibility = N''public''
              AND chapter.approval_status = N''approved''
              AND chapter.publication_status = N''published''
            ORDER BY chapter.display_order, achievement.display_order, achievement.achievement_id;

            SELECT
                skill.skill_key, skill.skill_name, skill.skill_summary,
                skill.featured, skill.display_order,
                COUNT_BIG(link.skill_link_id) AS approved_proof_count
            FROM dbo.career_skills AS skill
            JOIN dbo.career_skill_links AS link
              ON link.skill_id = skill.skill_id
             AND link.approval_status = N''approved''
            JOIN dbo.slate_entities AS source_entity
              ON source_entity.entity_id = link.source_entity_id
             AND source_entity.visibility = N''public''
             AND source_entity.approval_status = N''approved''
             AND source_entity.publication_status = N''published''
            WHERE skill.owner_profile_id = @ProfileId
              AND skill.deleted_at_utc IS NULL
              AND skill.visibility = N''public''
              AND skill.approval_status = N''approved''
            GROUP BY skill.skill_id, skill.skill_key, skill.skill_name,
                     skill.skill_summary, skill.featured, skill.display_order
            ORDER BY skill.featured DESC, skill.display_order, skill.skill_name;

            SELECT
                skill.skill_key, source_entity.entity_key AS source_entity_key,
                evidence.evidence_key, link.relationship_type, link.strength_rank,
                evidence.title AS evidence_title, evidence.summary AS evidence_summary,
                evidence.evidence_state, evidence.verification_status
            FROM dbo.career_skill_links AS link
            JOIN dbo.career_skills AS skill ON skill.skill_id = link.skill_id
            JOIN dbo.slate_entities AS source_entity ON source_entity.entity_id = link.source_entity_id
            LEFT JOIN dbo.evidence_items AS evidence ON evidence.evidence_item_id = link.evidence_item_id
            WHERE link.owner_profile_id = @ProfileId
              AND link.approval_status = N''approved''
              AND skill.visibility = N''public''
              AND skill.approval_status = N''approved''
              AND source_entity.visibility = N''public''
              AND source_entity.approval_status = N''approved''
              AND source_entity.publication_status = N''published''
              AND (evidence.evidence_item_id IS NULL OR evidence.visibility = N''public'')
            ORDER BY skill.display_order, link.strength_rank, link.skill_link_id;

            SELECT
                timeline.timeline_event_key, chapter.chapter_key,
                timeline.event_label, timeline.event_type,
                timeline.start_date, timeline.end_date, timeline.date_precision,
                timeline.constellation_featured, timeline.display_order
            FROM dbo.career_timeline_events AS timeline
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = timeline.chapter_id
            WHERE timeline.owner_profile_id = @ProfileId
              AND timeline.visibility = N''public''
              AND timeline.approval_status = N''approved''
              AND chapter.visibility = N''public''
              AND chapter.approval_status = N''approved''
              AND chapter.publication_status = N''published''
              AND chapter.deleted_at_utc IS NULL
            ORDER BY timeline.display_order, timeline.start_date, timeline.timeline_event_id;
        END;
    ');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-007')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-PLAT-007', N'Side-effect-free owner and public Living Resume read contracts', N'PeerSlate SQL Foundation v0.2');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-PLAT-007"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
