/* PeerSlate platform foundation verification. Read-only. */
SET NOCOUNT ON;

SELECT DB_NAME() AS database_name, SYSUTCDATETIME() AS checked_at_utc;

SELECT migration_id, description, applied_at_utc, application_version
FROM dbo.schema_migrations
WHERE migration_id LIKE N'PS-PLAT-%'
ORDER BY migration_id;

SELECT expected.object_name,
       CASE WHEN OBJECT_ID(N'dbo.' + expected.object_name, N'U') IS NOT NULL THEN 1 ELSE 0 END AS exists_flag
FROM (VALUES
    (N'schema_migrations'), (N'audit_events'), (N'member_profiles'),
    (N'slate_entities'), (N'slate_entity_relations'), (N'entity_access_grants'),
    (N'entity_publication_versions'), (N'file_assets'), (N'evidence_items'),
    (N'evidence_links'), (N'ai_proposals'), (N'ai_proposal_changes'),
    (N'connection_preferences'), (N'connection_requests'), (N'member_connections'),
    (N'user_blocks'), (N'user_reports'), (N'notifications'),
    (N'notification_preferences'), (N'user_consents'),
    (N'career_chapters'), (N'career_experiences'), (N'career_education'),
    (N'career_credentials'), (N'career_projects'), (N'career_achievements'),
    (N'career_skills'), (N'career_skill_links'), (N'career_timeline_events'),
    (N'voice_drafts'), (N'content_approval_events')
) AS expected(object_name)
ORDER BY expected.object_name;

SELECT expected.object_name,
       CASE WHEN OBJECT_ID(N'dbo.' + expected.object_name) IS NOT NULL THEN 1 ELSE 0 END AS exists_flag
FROM (VALUES
    (N'usp_AppendAuditEvent'),
    (N'trg_audit_events_immutable'),
    (N'trg_content_approval_events_immutable')
) AS expected(object_name)
ORDER BY expected.object_name;

SELECT t.name AS table_name, SUM(CONVERT(bigint, p.rows)) AS row_count
FROM sys.tables AS t
JOIN sys.partitions AS p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE t.name IN
(
    N'audit_events', N'member_profiles', N'slate_entities', N'slate_entity_relations',
    N'entity_access_grants', N'entity_publication_versions', N'file_assets',
    N'evidence_items', N'evidence_links', N'ai_proposals', N'ai_proposal_changes',
    N'connection_preferences', N'connection_requests', N'member_connections',
    N'user_blocks', N'user_reports', N'notifications', N'notification_preferences', N'user_consents',
    N'career_chapters', N'career_experiences', N'career_education', N'career_credentials',
    N'career_projects', N'career_achievements', N'career_skills', N'career_skill_links',
    N'career_timeline_events', N'voice_drafts', N'content_approval_events'
)
GROUP BY t.name
ORDER BY t.name;

SELECT fk.name AS untrusted_foreign_key
FROM sys.foreign_keys AS fk
WHERE fk.is_not_trusted = 1
  AND OBJECT_SCHEMA_NAME(fk.parent_object_id) = N'dbo'
  AND OBJECT_NAME(fk.parent_object_id) IN
  (
      N'audit_events', N'member_profiles', N'slate_entities', N'slate_entity_relations',
      N'entity_access_grants', N'entity_publication_versions', N'file_assets',
      N'evidence_items', N'evidence_links', N'ai_proposals', N'ai_proposal_changes',
      N'connection_preferences', N'connection_requests', N'member_connections',
      N'user_blocks', N'user_reports', N'notifications', N'notification_preferences', N'user_consents',
      N'career_chapters', N'career_experiences', N'career_education', N'career_credentials',
      N'career_projects', N'career_achievements', N'career_skills', N'career_skill_links',
      N'career_timeline_events', N'voice_drafts', N'content_approval_events'
  );

SELECT cc.name AS disabled_or_untrusted_check,
       OBJECT_NAME(cc.parent_object_id) AS table_name
FROM sys.check_constraints AS cc
WHERE (cc.is_disabled = 1 OR cc.is_not_trusted = 1)
  AND OBJECT_SCHEMA_NAME(cc.parent_object_id) = N'dbo';

SELECT
    (SELECT COUNT(*) FROM dbo.app_users) AS user_count,
    (SELECT COUNT(*) FROM dbo.member_profiles) AS profile_count,
    (SELECT COUNT(*) FROM dbo.member_profiles WHERE visibility = N'private') AS private_profile_count,
    (SELECT COUNT(*) FROM dbo.connection_preferences WHERE discovery_opt_in = 0) AS discovery_off_count;
