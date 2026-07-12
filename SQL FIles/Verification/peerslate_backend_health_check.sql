/*
PeerSlate backend health check
Read-only: this script does not insert, update, delete, or alter data.
*/

SET NOCOUNT ON;

SELECT
    DB_NAME() AS database_name,
    SYSUTCDATETIME() AS checked_at_utc;

SELECT
    s.name AS schema_name,
    o.name AS object_name,
    o.type_desc
FROM sys.objects AS o
JOIN sys.schemas AS s
    ON s.schema_id = o.schema_id
WHERE o.is_ms_shipped = 0
  AND o.type IN ('U', 'V', 'P')
ORDER BY o.type_desc, s.name, o.name;

SELECT 'app_users' AS object_name, COUNT_BIG(*) AS row_count FROM dbo.app_users
UNION ALL SELECT 'content_items', COUNT_BIG(*) FROM dbo.content_items
UNION ALL SELECT 'daily_feed_cards', COUNT_BIG(*) FROM dbo.daily_feed_cards
UNION ALL SELECT 'feed_interactions', COUNT_BIG(*) FROM dbo.feed_interactions
UNION ALL SELECT 'journal_responses', COUNT_BIG(*) FROM dbo.journal_responses
UNION ALL SELECT 'poll_votes', COUNT_BIG(*) FROM dbo.poll_votes
UNION ALL SELECT 'challenge_completions', COUNT_BIG(*) FROM dbo.challenge_completions
UNION ALL SELECT 'slate_spaces', COUNT_BIG(*) FROM dbo.slate_spaces
UNION ALL SELECT 'slate_items', COUNT_BIG(*) FROM dbo.slate_items
UNION ALL SELECT 'slate_item_links', COUNT_BIG(*) FROM dbo.slate_item_links
UNION ALL SELECT 'user_badges', COUNT_BIG(*) FROM dbo.user_badges
UNION ALL SELECT 'user_achievements', COUNT_BIG(*) FROM dbo.user_achievements;

SELECT
    name AS required_procedure,
    CASE WHEN OBJECT_ID(CONCAT('dbo.', name), 'P') IS NOT NULL THEN 1 ELSE 0 END AS exists_flag
FROM (VALUES
    ('usp_UpsertAppUserFromAuth'),
    ('usp_GetPeerSlateUserDashboard'),
    ('usp_GetTodayBreakFeedForUser'),
    ('usp_RecordFeedInteraction'),
    ('usp_SaveContentToBoard'),
    ('usp_UnsaveContentFromBoard'),
    ('usp_SubmitPollVote'),
    ('usp_CompleteChallenge'),
    ('usp_SaveJournalResponse'),
    ('usp_GetSlateSpaceForUser'),
    ('usp_AddSlateItem'),
    ('usp_UpdateSlateItem'),
    ('usp_LinkSlateItems'),
    ('usp_UnlinkSlateItems'),
    ('usp_ArchiveSlateItem'),
    ('usp_RestoreSlateItem'),
    ('usp_GetUserBadges'),
    ('usp_EvaluateUserFlatAchievements')
) AS required(name)
ORDER BY name;

SELECT
    publish_date,
    feed_name,
    COUNT(*) AS card_count,
    MIN(card_position) AS first_position,
    MAX(card_position) AS last_position
FROM dbo.daily_feed_cards
WHERE publish_date = CAST(GETDATE() AS DATE)
GROUP BY publish_date, feed_name
ORDER BY feed_name;
