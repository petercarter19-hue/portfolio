/*
PS-COMMUNITY-RESTORE-001 — restore a removed post or contribution.

Pete, 2026-08-03: members should be able to come back later and see what they
did. Deletion was one-way, so a mistaken removal was unrecoverable. The
retention window already keeps the text for 30 days before purging it; this
turns that window into a recovery window rather than only a delay.

Boundaries this file keeps:

- Only the author may restore, and only their own record. Authorization is
  server-derived from @UserKey exactly as the delete path is.
- A purged record can never be restored: its body is already gone, so
  "restore" would silently republish an empty post.
- A record under legal hold can never be restored. A hold means public access
  stays revoked; restoring would defeat it.
- Restoring a contribution whose parent post is still deleted is refused,
  because it would otherwise be unreachable and invisible.
- Responses and saves are NOT resurrected. They were deleted outright on
  removal and other members' reactions are not the author's to reinstate.
- Restore is idempotent: restoring a live record reports `existing`.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-RETENTION-001')
        THROW 52520, 'PS-COMMUNITY-RETENTION-001 must be applied first.', 1;

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ListRestorableCommunityForOwner
        @UserKey nvarchar(300), @RetentionDays int = 30
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52521, ''Member unavailable.'', 1;
        IF @RetentionDays<1 OR @RetentionDays>3650 THROW 52522, ''Retention days out of range.'', 1;
        DECLARE @Cutoff datetime2(7)=DATEADD(day,-@RetentionDays,SYSUTCDATETIME());

        SELECT post_key AS record_key, N''post'' AS record_kind, body,
               deleted_at_utc, revision_number,
               DATEADD(day,@RetentionDays,deleted_at_utc) AS restorable_until_utc
        FROM dbo.community_posts
        WHERE author_user_id=@UserId AND publication_state=N''deleted''
          AND purged_at_utc IS NULL AND legal_hold_reason IS NULL
          AND deleted_at_utc IS NOT NULL AND deleted_at_utc>@Cutoff
          /* Every read procedure filters moderation_state=clear, so restoring a
             moderated record reports success and shows nothing. Do not offer a
             control that cannot work. Independent review, 2026-08-04, F11. */
          AND moderation_state=N''clear''
        UNION ALL
        SELECT contribution_key, N''contribution'', body,
               deleted_at_utc, revision_number,
               DATEADD(day,@RetentionDays,deleted_at_utc)
        FROM dbo.community_contributions AS contribution
        WHERE author_user_id=@UserId AND lifecycle_state=N''deleted''
          AND purged_at_utc IS NULL AND legal_hold_reason IS NULL
          AND deleted_at_utc IS NOT NULL AND deleted_at_utc>@Cutoff
          AND moderation_state=N''clear''
          /* A reply cannot come back under a post that is still gone: the
             restore refuses with parent_unavailable. Independent review, F12. */
          AND EXISTS
          (
              SELECT 1 FROM dbo.community_posts AS parent
              WHERE parent.community_post_id=contribution.community_post_id
                AND parent.publication_state=N''published''
          )
        ORDER BY deleted_at_utc DESC;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_RestorePublicCommunityPost
        @UserKey nvarchar(300), @PostKey uniqueidentifier, @RetentionDays int = 30
    AS
    BEGIN
        SET NOCOUNT ON; SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52521, ''Member unavailable.'', 1;
        IF @RetentionDays<1 OR @RetentionDays>3650 THROW 52522, ''Retention days out of range.'', 1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityPostRestore;
        DECLARE @PostId bigint,@State nvarchar(20),@DeletedAt datetime2(7),@Purged datetime2(7),@Hold nvarchar(60),@Moderation nvarchar(20);
        SELECT @PostId=community_post_id,@State=publication_state,@DeletedAt=deleted_at_utc,
               @Purged=purged_at_utc,@Hold=legal_hold_reason,@Moderation=moderation_state
        FROM dbo.community_posts WITH(UPDLOCK,HOLDLOCK)
        WHERE post_key=@PostKey AND author_user_id=@UserId;
        IF @PostId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostRestore; SELECT N''not_found'' AS outcome; RETURN; END;
        IF @State=N''published'' BEGIN IF @StartedTransaction=1 COMMIT; SELECT N''existing'' AS outcome,@PostKey AS post_key; RETURN; END;
        IF @Purged IS NOT NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostRestore; SELECT N''purged'' AS outcome; RETURN; END;
        IF @Hold IS NOT NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostRestore; SELECT N''held'' AS outcome; RETURN; END;
        /* Moderation is deliberately not bypassed. Say so rather than report a
           restore that no reader will ever see. Independent review, F11. */
        IF @Moderation<>N''clear'' BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostRestore; SELECT N''moderated'' AS outcome; RETURN; END;
        IF @DeletedAt IS NULL OR @DeletedAt<=DATEADD(day,-@RetentionDays,SYSUTCDATETIME())
        BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostRestore; SELECT N''expired'' AS outcome; RETURN; END;
        UPDATE dbo.community_posts
        SET publication_state=N''published'',deleted_at_utc=NULL,
            updated_at_utc=SYSUTCDATETIME(),revision_number=revision_number+1
        WHERE community_post_id=@PostId;
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''post'',@PostKey,N''restored'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.post.restored'',@PostKey);
        IF @StartedTransaction=1 COMMIT; SELECT N''restored'' AS outcome,@PostKey AS post_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_RestorePublicCommunityContribution
        @UserKey nvarchar(300), @ContributionKey uniqueidentifier, @RetentionDays int = 30
    AS
    BEGIN
        SET NOCOUNT ON; SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52521, ''Member unavailable.'', 1;
        IF @RetentionDays<1 OR @RetentionDays>3650 THROW 52522, ''Retention days out of range.'', 1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityContribRestore;
        DECLARE @Id bigint,@State nvarchar(20),@DeletedAt datetime2(7),@Purged datetime2(7),@Hold nvarchar(60),@PostId bigint,@Moderation nvarchar(20);
        SELECT @Id=community_contribution_id,@State=lifecycle_state,@DeletedAt=deleted_at_utc,
               @Purged=purged_at_utc,@Hold=legal_hold_reason,@PostId=community_post_id,@Moderation=moderation_state
        FROM dbo.community_contributions WITH(UPDLOCK,HOLDLOCK)
        WHERE contribution_key=@ContributionKey AND author_user_id=@UserId;
        IF @Id IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContribRestore; SELECT N''not_found'' AS outcome; RETURN; END;
        IF @State=N''active'' BEGIN IF @StartedTransaction=1 COMMIT; SELECT N''existing'' AS outcome,@ContributionKey AS contribution_key; RETURN; END;
        IF @Purged IS NOT NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContribRestore; SELECT N''purged'' AS outcome; RETURN; END;
        IF @Hold IS NOT NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContribRestore; SELECT N''held'' AS outcome; RETURN; END;
        IF @Moderation<>N''clear'' BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContribRestore; SELECT N''moderated'' AS outcome; RETURN; END;
        IF @DeletedAt IS NULL OR @DeletedAt<=DATEADD(day,-@RetentionDays,SYSUTCDATETIME())
        BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContribRestore; SELECT N''expired'' AS outcome; RETURN; END;
        IF EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@PostId AND publication_state<>N''published'')
        BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContribRestore; SELECT N''parent_unavailable'' AS outcome; RETURN; END;
        UPDATE dbo.community_contributions
        SET lifecycle_state=N''active'',deleted_at_utc=NULL,
            updated_at_utc=SYSUTCDATETIME(),revision_number=revision_number+1
        WHERE community_contribution_id=@Id;
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''contribution'',@ContributionKey,N''restored'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.contribution.restored'',@ContributionKey);
        IF @StartedTransaction=1 COMMIT; SELECT N''restored'' AS outcome,@ContributionKey AS contribution_key;
    END');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-COMMUNITY-RESTORE-001'
    )
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
        (
            N'PS-COMMUNITY-RESTORE-001',
            N'Owner restore of a removed Community post or contribution within the retention window',
            N'PeerSlate SQL Foundation v0.1'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
