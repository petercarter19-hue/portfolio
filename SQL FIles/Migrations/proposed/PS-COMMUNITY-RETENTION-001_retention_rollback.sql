/*
PS-COMMUNITY-RETENTION-001 rollback.

Refuses while any record is under legal hold: dropping the hold columns would
silently release a hold and expose held records to the next purge run.
Purged tombstones are preserved; this rollback removes enforcement, never
content or its deletion record.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    /* PS-COMMUNITY-RESTORE-001 reads purged_at_utc, which this rollback drops.
       Running out of order would leave the restore procedures referencing a
       dropped column, and would strip the purge marker so a body-emptied
       tombstone became "restorable" again — republishing an empty post, the
       exact case the restore header says it prevents. Mirrors the forward
       migration's dependency guard. Independent review, 2026-08-04, F10. */
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-RESTORE-001')
        THROW 52514, 'Community rollback refused: roll back PS-COMMUNITY-RESTORE-001 first.', 1;

    IF OBJECT_ID(N'dbo.community_posts', N'U') IS NOT NULL
       AND COL_LENGTH(N'dbo.community_posts', N'legal_hold_reason') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.community_posts WHERE legal_hold_reason IS NOT NULL)
        THROW 52510, 'Community rollback refused: posts are under legal hold.', 1;

    IF OBJECT_ID(N'dbo.community_contributions', N'U') IS NOT NULL
       AND COL_LENGTH(N'dbo.community_contributions', N'legal_hold_reason') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.community_contributions WHERE legal_hold_reason IS NOT NULL)
        THROW 52511, 'Community rollback refused: contributions are under legal hold.', 1;

    IF OBJECT_ID(N'dbo.usp_PurgeCommunityContent', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_PurgeCommunityContent;
    IF OBJECT_ID(N'dbo.usp_PurgeCommunityAuditEvents', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_PurgeCommunityAuditEvents;
    IF OBJECT_ID(N'dbo.usp_PurgeCommunityOutbox', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_PurgeCommunityOutbox;
    IF OBJECT_ID(N'dbo.usp_SetCommunityLegalHold', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SetCommunityLegalHold;

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_posts') AND name = N'IX_community_posts_purge_due')
        DROP INDEX IX_community_posts_purge_due ON dbo.community_posts;
    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_contributions') AND name = N'IX_community_contributions_purge_due')
        DROP INDEX IX_community_contributions_purge_due ON dbo.community_contributions;
    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_audit_events') AND name = N'IX_community_audit_events_occurred')
        DROP INDEX IX_community_audit_events_occurred ON dbo.community_audit_events;
    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_outbox') AND name = N'IX_community_outbox_retention')
        DROP INDEX IX_community_outbox_retention ON dbo.community_outbox;

    /* Restore the original body constraints. A purged tombstone has an empty
       body, which the original constraint forbids, so refuse rather than
       leave the table in a state its own constraint rejects. */
    IF COL_LENGTH(N'dbo.community_posts', N'purged_at_utc') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.community_posts WHERE purged_at_utc IS NOT NULL)
        THROW 52512, 'Community rollback refused: purged tombstones exist.', 1;
    IF COL_LENGTH(N'dbo.community_contributions', N'purged_at_utc') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.community_contributions WHERE purged_at_utc IS NOT NULL)
        THROW 52513, 'Community rollback refused: purged tombstones exist.', 1;

    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_posts_body_or_purged')
        ALTER TABLE dbo.community_posts DROP CONSTRAINT CK_community_posts_body_or_purged;
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_posts_body')
        EXEC(N'ALTER TABLE dbo.community_posts WITH CHECK ADD CONSTRAINT CK_community_posts_body CHECK (LEN(body) BETWEEN 1 AND 4000);');
    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_contributions_body_or_purged')
        ALTER TABLE dbo.community_contributions DROP CONSTRAINT CK_community_contributions_body_or_purged;
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_contributions_body')
        EXEC(N'ALTER TABLE dbo.community_contributions WITH CHECK ADD CONSTRAINT CK_community_contributions_body CHECK (LEN(body) BETWEEN 1 AND 2000);');

    /* The legal_hold_* columns and their completeness constraints belong to
       PS-COMMUNITY-PUBLIC-PILOT-001 and are removed by its own rollback. This
       rollback removes only what this migration added: the purge marker, the
       purge jobs, the hold-setting procedure, and the retention indexes.
       Independent review, 2026-08-04, F5. */
    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_posts_purge')
        ALTER TABLE dbo.community_posts DROP CONSTRAINT CK_community_posts_purge;
    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_contributions_purge')
        ALTER TABLE dbo.community_contributions DROP CONSTRAINT CK_community_contributions_purge;

    IF COL_LENGTH(N'dbo.community_posts', N'purged_at_utc') IS NOT NULL
        EXEC(N'ALTER TABLE dbo.community_posts DROP COLUMN purged_at_utc;');
    IF COL_LENGTH(N'dbo.community_contributions', N'purged_at_utc') IS NOT NULL
        EXEC(N'ALTER TABLE dbo.community_contributions DROP COLUMN purged_at_utc;');

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-RETENTION-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
