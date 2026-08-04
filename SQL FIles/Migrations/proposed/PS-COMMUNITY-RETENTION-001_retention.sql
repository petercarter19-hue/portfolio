/*
PS-COMMUNITY-RETENTION-001 — retention and deletion enforcement.

Implements the schedule Pete approved on 2026-08-03 in
docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/APPROVED_RETENTION_AND_DELETION_DECISION.md

Design notes that matter for review:

- Purge nulls the body and presentation fields and stamps purged_at_utc,
  leaving a body-free tombstone. The row itself must survive so a purged post
  cannot reappear as "not found and therefore creatable again", and so
  referencing rows keep their foreign keys.
- Every job is idempotent, bounded by @BatchSize, and safe to run
  concurrently: rows are claimed with UPDLOCK/READPAST so two workers never
  fight over the same row and a crashed worker leaves nothing locked.
- A legal hold suspends permanent purge for specifically identified records
  only. The hold marker is body-free: a short reason code, who set it, when,
  and a review date. A hold changes nothing about who can see the record: it
  exempts that record from the retention purge and from attachment cleanup,
  and nothing else. An earlier version of this comment claimed a hold revokes
  public access, which was untrue for a hold placed on a live post
  (independent review, 2026-08-04, F8). Holding a live post is permitted and
  useful, because it survives a later author deletion.
- Attachment bytes are handled by the existing media cleanup worker. This file
  only purges media metadata once the Blob deletion has completed, so metadata
  never disappears while bytes still exist.
- Audit rows never contain bodies, so their purge is a plain delete.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-PUBLIC-PILOT-001')
        THROW 52500, 'PS-COMMUNITY-PUBLIC-PILOT-001 must be applied first.', 1;

    /* ---- Purge tombstone and legal-hold state (body-free) ---- */

    IF COL_LENGTH(N'dbo.community_posts', N'purged_at_utc') IS NULL
        EXEC(N'ALTER TABLE dbo.community_posts ADD purged_at_utc datetime2(7) NULL;');
    IF COL_LENGTH(N'dbo.community_contributions', N'purged_at_utc') IS NULL
        EXEC(N'ALTER TABLE dbo.community_contributions ADD purged_at_utc datetime2(7) NULL;');

    /* The legal_hold_* columns and their completeness constraints belong to
       PS-COMMUNITY-PUBLIC-PILOT-001, not to this migration. They were defined
       here originally, which meant the media cleanup claim could not reference
       them without being restated in this file -- and that tripped the base
       migration's procedure definition hash guard on re-application. This
       migration owns the purge marker, the jobs that honour a hold, and the
       procedure that sets one. Independent review, 2026-08-04, F5. */
    IF COL_LENGTH(N'dbo.community_posts', N'legal_hold_reason') IS NULL
        THROW 52515, 'PS-COMMUNITY-PUBLIC-PILOT-001 must supply the legal hold columns.', 1;
    IF COL_LENGTH(N'dbo.community_contributions', N'legal_hold_reason') IS NULL
        THROW 52515, 'PS-COMMUNITY-PUBLIC-PILOT-001 must supply the legal hold columns.', 1;

    /* The original body constraints require LEN(body) BETWEEN 1 AND N, so a
       purge that empties the body could never commit — it failed silently and
       no content was ever erased, while the public policy said it was
       (independent review 2026-08-04, F2). Replace them with constraints that
       permit an empty body ONLY on a purged tombstone. This is strictly
       tighter than relaxing the lower bound: an empty body outside a purge
       remains impossible. */
    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_posts_body')
        ALTER TABLE dbo.community_posts DROP CONSTRAINT CK_community_posts_body;
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_posts_body_or_purged')
        EXEC(N'ALTER TABLE dbo.community_posts WITH CHECK ADD CONSTRAINT CK_community_posts_body_or_purged CHECK ((purged_at_utc IS NULL AND LEN(body) BETWEEN 1 AND 4000) OR (purged_at_utc IS NOT NULL AND LEN(body) = 0));');

    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_contributions_body')
        ALTER TABLE dbo.community_contributions DROP CONSTRAINT CK_community_contributions_body;
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_contributions_body_or_purged')
        EXEC(N'ALTER TABLE dbo.community_contributions WITH CHECK ADD CONSTRAINT CK_community_contributions_body_or_purged CHECK ((purged_at_utc IS NULL AND LEN(body) BETWEEN 1 AND 2000) OR (purged_at_utc IS NOT NULL AND LEN(body) = 0));');

    /* Only a removed row may be purged, and a purged row must stay removed. */
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_posts_purge')
        EXEC(N'ALTER TABLE dbo.community_posts WITH CHECK ADD CONSTRAINT CK_community_posts_purge CHECK (purged_at_utc IS NULL OR (publication_state = N''deleted'' AND deleted_at_utc IS NOT NULL));');
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_community_contributions_purge')
        EXEC(N'ALTER TABLE dbo.community_contributions WITH CHECK ADD CONSTRAINT CK_community_contributions_purge CHECK (purged_at_utc IS NULL OR (lifecycle_state = N''deleted'' AND deleted_at_utc IS NOT NULL));');

    /* Selective indexes so each job scans only its own candidates. */
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_posts') AND name = N'IX_community_posts_purge_due')
        EXEC(N'CREATE INDEX IX_community_posts_purge_due ON dbo.community_posts(deleted_at_utc) WHERE purged_at_utc IS NULL AND deleted_at_utc IS NOT NULL;');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_contributions') AND name = N'IX_community_contributions_purge_due')
        EXEC(N'CREATE INDEX IX_community_contributions_purge_due ON dbo.community_contributions(deleted_at_utc) WHERE purged_at_utc IS NULL AND deleted_at_utc IS NOT NULL;');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_audit_events') AND name = N'IX_community_audit_events_occurred')
        EXEC(N'CREATE INDEX IX_community_audit_events_occurred ON dbo.community_audit_events(occurred_at_utc);');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.community_outbox') AND name = N'IX_community_outbox_retention')
        EXEC(N'CREATE INDEX IX_community_outbox_retention ON dbo.community_outbox(created_at_utc, processed_at_utc);');

    /* ---- 30-day content purge ---- */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeCommunityContent
            @RetentionDays int = 30,
            @BatchSize int = 200,
            @UtcNow datetime2(7) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @RetentionDays < 1 OR @RetentionDays > 3650 THROW 52501, ''Retention days out of range.'', 1;
            IF @BatchSize < 1 OR @BatchSize > 5000 THROW 52502, ''Batch size out of range.'', 1;
            SET @UtcNow = COALESCE(@UtcNow, SYSUTCDATETIME());
            DECLARE @Cutoff datetime2(7) = DATEADD(day, -@RetentionDays, @UtcNow);
            DECLARE @PostsPurged int = 0, @ContributionsPurged int = 0;

            /* The revision deletes below are scoped to exactly the rows this
               batch purged. Joining on purged_at_utc IS NOT NULL instead would
               rescan every tombstone ever created and delete an unbounded
               number of revisions in one transaction, on a sweep that runs
               inline on a member request. Independent review, 2026-08-04, F7. */
            DECLARE @PurgedPosts TABLE (community_post_id bigint PRIMARY KEY);
            DECLARE @PurgedContributions TABLE (community_contribution_id bigint PRIMARY KEY);

            BEGIN TRANSACTION;

            /* Posts: null the body and presentation fields, keep the tombstone. */
            ;WITH due AS
            (
                SELECT TOP (@BatchSize) community_post_id
                FROM dbo.community_posts WITH (UPDLOCK, READPAST)
                WHERE purged_at_utc IS NULL
                  AND deleted_at_utc IS NOT NULL
                  AND deleted_at_utc <= @Cutoff
                  AND legal_hold_reason IS NULL
                ORDER BY deleted_at_utc
            )
            UPDATE post
            SET body = N'''',
                intent = N''post'',
                response_posture = N''sharing_only'',
                purged_at_utc = @UtcNow,
                updated_at_utc = @UtcNow
            OUTPUT inserted.community_post_id INTO @PurgedPosts(community_post_id)
            FROM dbo.community_posts AS post
            JOIN due ON due.community_post_id = post.community_post_id;
            SET @PostsPurged = @@ROWCOUNT;

            /* Revisions carry the same bodies and go with their source. */
            DELETE revision
            FROM dbo.community_post_revisions AS revision
            JOIN @PurgedPosts AS purged
              ON purged.community_post_id = revision.community_post_id;

            ;WITH due AS
            (
                SELECT TOP (@BatchSize) community_contribution_id
                FROM dbo.community_contributions WITH (UPDLOCK, READPAST)
                WHERE purged_at_utc IS NULL
                  AND deleted_at_utc IS NOT NULL
                  AND deleted_at_utc <= @Cutoff
                  AND legal_hold_reason IS NULL
                ORDER BY deleted_at_utc
            )
            UPDATE contribution
            SET body = N'''',
                purged_at_utc = @UtcNow,
                updated_at_utc = @UtcNow
            OUTPUT inserted.community_contribution_id INTO @PurgedContributions(community_contribution_id)
            FROM dbo.community_contributions AS contribution
            JOIN due ON due.community_contribution_id = contribution.community_contribution_id;
            SET @ContributionsPurged = @@ROWCOUNT;

            DELETE revision
            FROM dbo.community_contribution_revisions AS revision
            JOIN @PurgedContributions AS purged
              ON purged.community_contribution_id = revision.community_contribution_id;

            /* Media metadata goes only once its bytes are confirmed gone. */
            DECLARE @MediaPurged int = 0;
            DELETE TOP (@BatchSize) media
            FROM dbo.community_media AS media
            LEFT JOIN dbo.community_posts AS post
              ON post.community_post_id = media.community_post_id
            LEFT JOIN dbo.community_contributions AS contribution
              ON contribution.community_contribution_id = media.community_contribution_id
            WHERE media.blob_cleanup_completed_at_utc IS NOT NULL
              AND media.removed_at_utc IS NOT NULL
              AND media.removed_at_utc <= @Cutoff
              AND (post.community_post_id IS NULL OR post.purged_at_utc IS NOT NULL)
              AND (contribution.community_contribution_id IS NULL OR contribution.purged_at_utc IS NOT NULL);
            SET @MediaPurged = @@ROWCOUNT;

            COMMIT TRANSACTION;

            SELECT @PostsPurged AS posts_purged,
                   @ContributionsPurged AS contributions_purged,
                   @MediaPurged AS media_metadata_purged;
        END;
    ');

    /* ---- 90-day body-free audit purge ---- */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeCommunityAuditEvents
            @RetentionDays int = 90,
            @BatchSize int = 1000,
            @UtcNow datetime2(7) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @RetentionDays < 1 OR @RetentionDays > 3650 THROW 52501, ''Retention days out of range.'', 1;
            IF @BatchSize < 1 OR @BatchSize > 5000 THROW 52502, ''Batch size out of range.'', 1;
            SET @UtcNow = COALESCE(@UtcNow, SYSUTCDATETIME());
            DELETE TOP (@BatchSize) FROM dbo.community_audit_events
            WHERE occurred_at_utc <= DATEADD(day, -@RetentionDays, @UtcNow);
            SELECT @@ROWCOUNT AS audit_events_purged;
        END;
    ');

    /* ---- Outbox: 30 days processed, 90 days abandoned ---- */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeCommunityOutbox
            @ProcessedRetentionDays int = 30,
            @AbandonedRetentionDays int = 90,
            @BatchSize int = 1000,
            @UtcNow datetime2(7) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF @ProcessedRetentionDays < 1 OR @ProcessedRetentionDays > 3650 THROW 52501, ''Retention days out of range.'', 1;
            IF @AbandonedRetentionDays < @ProcessedRetentionDays OR @AbandonedRetentionDays > 3650 THROW 52501, ''Retention days out of range.'', 1;
            IF @BatchSize < 1 OR @BatchSize > 5000 THROW 52502, ''Batch size out of range.'', 1;
            SET @UtcNow = COALESCE(@UtcNow, SYSUTCDATETIME());
            DECLARE @Processed int = 0, @Abandoned int = 0;

            DELETE TOP (@BatchSize) FROM dbo.community_outbox
            WHERE processed_at_utc IS NOT NULL
              AND processed_at_utc <= DATEADD(day, -@ProcessedRetentionDays, @UtcNow);
            SET @Processed = @@ROWCOUNT;

            DELETE TOP (@BatchSize) FROM dbo.community_outbox
            WHERE processed_at_utc IS NULL
              AND created_at_utc <= DATEADD(day, -@AbandonedRetentionDays, @UtcNow);
            SET @Abandoned = @@ROWCOUNT;

            SELECT @Processed AS processed_purged, @Abandoned AS abandoned_purged;
        END;
    ');

    /* ---- Scoped legal hold ---- */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SetCommunityLegalHold
            @PostKey uniqueidentifier = NULL,
            @ContributionKey uniqueidentifier = NULL,
            @OperatorUserId int,
            @ReasonCode nvarchar(60) = NULL,
            @ReviewOn date = NULL,
            @Release bit = 0
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF (@PostKey IS NULL AND @ContributionKey IS NULL) OR (@PostKey IS NOT NULL AND @ContributionKey IS NOT NULL)
                THROW 52503, ''Name exactly one record to hold.'', 1;
            IF @Release = 0 AND (@ReasonCode IS NULL OR LTRIM(RTRIM(@ReasonCode)) = N'''' OR @ReviewOn IS NULL)
                THROW 52504, ''A hold requires a reason code and a review date.'', 1;
            IF @Release = 0 AND @ReviewOn <= CONVERT(date, SYSUTCDATETIME())
                THROW 52505, ''The hold review date must be in the future.'', 1;
            /* An audit record attributing a hold to a user id that does not
               exist is worse than no record at all: it looks authoritative and
               cannot be resolved to a person. Independent review, F8. */
            IF @Release = 0 AND NOT EXISTS (SELECT 1 FROM dbo.app_users WHERE id = @OperatorUserId)
                THROW 52507, ''The hold operator is not a known user.'', 1;

            IF @PostKey IS NOT NULL
                UPDATE dbo.community_posts
                SET legal_hold_reason = CASE WHEN @Release = 1 THEN NULL ELSE @ReasonCode END,
                    legal_hold_set_at_utc = CASE WHEN @Release = 1 THEN NULL ELSE SYSUTCDATETIME() END,
                    legal_hold_set_by_user_id = CASE WHEN @Release = 1 THEN NULL ELSE @OperatorUserId END,
                    legal_hold_review_on = CASE WHEN @Release = 1 THEN NULL ELSE @ReviewOn END
                WHERE post_key = @PostKey;
            ELSE
                UPDATE dbo.community_contributions
                SET legal_hold_reason = CASE WHEN @Release = 1 THEN NULL ELSE @ReasonCode END,
                    legal_hold_set_at_utc = CASE WHEN @Release = 1 THEN NULL ELSE SYSUTCDATETIME() END,
                    legal_hold_set_by_user_id = CASE WHEN @Release = 1 THEN NULL ELSE @OperatorUserId END,
                    legal_hold_review_on = CASE WHEN @Release = 1 THEN NULL ELSE @ReviewOn END
                WHERE contribution_key = @ContributionKey;

            IF @@ROWCOUNT = 0 THROW 52506, ''No such Community record.'', 1;
            SELECT CASE WHEN @Release = 1 THEN N''released'' ELSE N''held'' END AS outcome;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-RETENTION-001'
    )
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
        (
            N'PS-COMMUNITY-RETENTION-001',
            N'Community retention purge jobs and scoped legal hold',
            N'PeerSlate SQL Foundation v0.1'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
