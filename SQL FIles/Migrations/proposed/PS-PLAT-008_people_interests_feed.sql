/* ============================================================
   PS-PLAT-008 — People & Interests feed domain (PS-FEAT-002)

   *** PROPOSED — NOT APPLIED. DO NOT RUN WITHOUT PETE'S APPROVAL. ***

   Why each object exists:
   - feed_posts: one row per board object. Carries the content type,
     the STORED presentation variant (layout/paper/rotation/attachment
     — deterministic collage, never re-randomized at render), the
     tenant owner, visibility (drafts default private per AGENTS.md),
     and optional links to a goal/project/slate item.
   - feed_post_comments: comments on a post.
   - feed_post_reactions: positive-only reactions; the primary key
     makes duplicate reactions impossible (idempotent by design).
   - feed_post_saves: a member's saved posts.
   - media_asset_url on feed_posts is a REFERENCE to Azure Blob
     Storage (never base64 in SQL). The upload pipeline itself is
     separate future work — see PS-FEAT-002 doc, "Media uploads".

   Rollback: PS-PLAT-008_people_interests_feed_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-005')
        THROW 51800, 'PS-PLAT-005 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.feed_posts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.feed_posts
        (
            feed_post_id bigint IDENTITY(1,1) NOT NULL,
            post_key uniqueidentifier NOT NULL CONSTRAINT DF_feed_posts_key DEFAULT NEWSEQUENTIALID(),
            author_user_id int NOT NULL,
            content_type nvarchar(30) NOT NULL,
            body nvarchar(200) NOT NULL,
            title nvarchar(120) NULL,
            quote_attribution nvarchar(120) NULL,
            media_asset_url nvarchar(500) NULL,           -- Azure Blob reference only
            media_alt_text nvarchar(300) NULL,
            layout_variant nvarchar(20) NOT NULL CONSTRAINT DF_feed_posts_layout DEFAULT N'standard',
            paper_kind nvarchar(20) NOT NULL CONSTRAINT DF_feed_posts_paper DEFAULT N'sticky',
            paper_color nvarchar(20) NOT NULL CONSTRAINT DF_feed_posts_color DEFAULT N'yellow',
            rotation_degrees decimal(4,2) NOT NULL CONSTRAINT DF_feed_posts_rotation DEFAULT 0,
            attachment_kind nvarchar(20) NOT NULL CONSTRAINT DF_feed_posts_attachment DEFAULT N'pin',
            visibility nvarchar(30) NOT NULL CONSTRAINT DF_feed_posts_visibility DEFAULT N'private',
            linked_entity_type nvarchar(30) NULL,          -- goal | project | slate_item
            linked_entity_id bigint NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_feed_posts_created DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            CONSTRAINT PK_feed_posts PRIMARY KEY (feed_post_id),
            CONSTRAINT UQ_feed_posts_key UNIQUE (post_key),
            CONSTRAINT FK_feed_posts_author FOREIGN KEY (author_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_feed_posts_content_type CHECK (content_type IN (N'note', N'win', N'question', N'goal', N'project', N'idea', N'photo', N'quote', N'moment')),
            CONSTRAINT CK_feed_posts_layout CHECK (layout_variant IN (N'small', N'standard', N'tall', N'wide', N'photo', N'featured')),
            CONSTRAINT CK_feed_posts_visibility CHECK (visibility IN (N'private', N'connections', N'public')),
            CONSTRAINT CK_feed_posts_linked CHECK (
                (linked_entity_type IS NULL AND linked_entity_id IS NULL)
                OR (linked_entity_type IN (N'goal', N'project', N'slate_item') AND linked_entity_id IS NOT NULL)
            )
        );

        /* Keyset pagination path: newest-first scans over public posts. */
        CREATE INDEX IX_feed_posts_feed_scan
            ON dbo.feed_posts (created_at_utc DESC, feed_post_id DESC)
            INCLUDE (author_user_id, content_type, visibility)
            WHERE deleted_at_utc IS NULL;
    END;

    IF OBJECT_ID(N'dbo.feed_post_comments', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.feed_post_comments
        (
            feed_post_comment_id bigint IDENTITY(1,1) NOT NULL,
            feed_post_id bigint NOT NULL,
            author_user_id int NOT NULL,
            body nvarchar(300) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_feed_post_comments_created DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            CONSTRAINT PK_feed_post_comments PRIMARY KEY (feed_post_comment_id),
            CONSTRAINT FK_feed_post_comments_post FOREIGN KEY (feed_post_id) REFERENCES dbo.feed_posts(feed_post_id),
            CONSTRAINT FK_feed_post_comments_author FOREIGN KEY (author_user_id) REFERENCES dbo.app_users(id)
        );

        CREATE INDEX IX_feed_post_comments_post
            ON dbo.feed_post_comments (feed_post_id, created_at_utc);
    END;

    IF OBJECT_ID(N'dbo.feed_post_reactions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.feed_post_reactions
        (
            feed_post_id bigint NOT NULL,
            user_id int NOT NULL,
            reaction_type nvarchar(30) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_feed_post_reactions_created DEFAULT SYSUTCDATETIME(),
            /* One row per member per reaction per post — duplicate
               submissions cannot create duplicate records. */
            CONSTRAINT PK_feed_post_reactions PRIMARY KEY (feed_post_id, user_id, reaction_type),
            CONSTRAINT FK_feed_post_reactions_post FOREIGN KEY (feed_post_id) REFERENCES dbo.feed_posts(feed_post_id),
            CONSTRAINT FK_feed_post_reactions_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id),
            /* Positive-only vocabulary, shared with the application config. */
            CONSTRAINT CK_feed_post_reactions_type CHECK (reaction_type IN (N'applaud', N'celebrate', N'inspired', N'rooting', N'im_in'))
        );
    END;

    IF OBJECT_ID(N'dbo.feed_post_saves', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.feed_post_saves
        (
            feed_post_id bigint NOT NULL,
            user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_feed_post_saves_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_feed_post_saves PRIMARY KEY (feed_post_id, user_id),
            CONSTRAINT FK_feed_post_saves_post FOREIGN KEY (feed_post_id) REFERENCES dbo.feed_posts(feed_post_id),
            CONSTRAINT FK_feed_post_saves_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id)
        );
    END;

    /* ------------------------------------------------------------
       Stored procedures (application access goes ONLY through these,
       matching services/database_service.py's allowlist pattern).
       ------------------------------------------------------------ */

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_GetPeopleInterestsFeedPage
        @ViewerKey nvarchar(100) = NULL,
        @CursorCreatedAtUtc datetime2(7) = NULL,
        @CursorPostId bigint = NULL,
        @PageLimit int = 16
    AS
    BEGIN
        SET NOCOUNT ON;
        IF @PageLimit < 1 SET @PageLimit = 1;
        IF @PageLimit > 32 SET @PageLimit = 32;

        SELECT TOP (@PageLimit)
            p.feed_post_id, p.post_key, p.content_type, p.body, p.title,
            p.quote_attribution, p.media_asset_url, p.media_alt_text,
            p.layout_variant, p.paper_kind, p.paper_color, p.rotation_degrees,
            p.attachment_kind, p.created_at_utc,
            u.user_key AS author_key, u.display_name AS author_name,
            (SELECT COUNT(*) FROM dbo.feed_post_comments c
              WHERE c.feed_post_id = p.feed_post_id AND c.deleted_at_utc IS NULL) AS comment_count
        FROM dbo.feed_posts AS p
        JOIN dbo.app_users AS u ON u.id = p.author_user_id
        WHERE p.deleted_at_utc IS NULL
          AND p.visibility = N''public''
          AND (
                @CursorCreatedAtUtc IS NULL
                OR p.created_at_utc < @CursorCreatedAtUtc
                OR (p.created_at_utc = @CursorCreatedAtUtc AND p.feed_post_id < @CursorPostId)
              )
        ORDER BY p.created_at_utc DESC, p.feed_post_id DESC;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_CreateFeedPost
        @UserKey nvarchar(100),
        @ContentType nvarchar(30),
        @Body nvarchar(200),
        @Title nvarchar(120) = NULL,
        @MediaAssetUrl nvarchar(500) = NULL,
        @MediaAltText nvarchar(300) = NULL,
        @LayoutVariant nvarchar(20) = N''standard'',
        @PaperKind nvarchar(20) = N''sticky'',
        @PaperColor nvarchar(20) = N''yellow'',
        @RotationDegrees decimal(4,2) = 0,
        @AttachmentKind nvarchar(20) = N''pin'',
        @Visibility nvarchar(30) = N''private'',
        @LinkedEntityType nvarchar(30) = NULL,
        @LinkedEntityId bigint = NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @AuthorId int = (SELECT id FROM dbo.app_users WHERE user_key = @UserKey);
        IF @AuthorId IS NULL THROW 51801, ''Member not found for feed post.'', 1;

        /* Linked goal/project/slate item must belong to the author
           (tenant-safe: never trust a browser-supplied entity id). */
        IF @LinkedEntityType = N''slate_item''
           AND NOT EXISTS (
               SELECT 1 FROM dbo.slate_items si
               WHERE si.slate_item_id = @LinkedEntityId
                 AND si.owner_user_id = @AuthorId)
            THROW 51802, ''Linked item does not belong to this member.'', 1;

        INSERT dbo.feed_posts (
            author_user_id, content_type, body, title, media_asset_url,
            media_alt_text, layout_variant, paper_kind, paper_color,
            rotation_degrees, attachment_kind, visibility,
            linked_entity_type, linked_entity_id)
        VALUES (
            @AuthorId, @ContentType, @Body, @Title, @MediaAssetUrl,
            @MediaAltText, @LayoutVariant, @PaperKind, @PaperColor,
            @RotationDegrees, @AttachmentKind, @Visibility,
            @LinkedEntityType, @LinkedEntityId);

        SELECT p.feed_post_id, p.post_key, p.created_at_utc
        FROM dbo.feed_posts AS p
        WHERE p.feed_post_id = SCOPE_IDENTITY();
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_GetFeedPostDetail
        @PostKey uniqueidentifier,
        @ViewerKey nvarchar(100) = NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @PostId bigint = (
            SELECT feed_post_id FROM dbo.feed_posts
            WHERE post_key = @PostKey AND deleted_at_utc IS NULL);
        IF @PostId IS NULL THROW 51803, ''Feed post not found.'', 1;

        SELECT p.feed_post_id, p.post_key, p.content_type, p.body, p.title,
               p.quote_attribution, p.media_asset_url, p.media_alt_text,
               p.layout_variant, p.paper_kind, p.paper_color,
               p.rotation_degrees, p.attachment_kind, p.created_at_utc,
               u.user_key AS author_key, u.display_name AS author_name
        FROM dbo.feed_posts AS p
        JOIN dbo.app_users AS u ON u.id = p.author_user_id
        WHERE p.feed_post_id = @PostId;

        SELECT c.feed_post_comment_id, c.body, c.created_at_utc,
               u.user_key AS author_key, u.display_name AS author_name
        FROM dbo.feed_post_comments AS c
        JOIN dbo.app_users AS u ON u.id = c.author_user_id
        WHERE c.feed_post_id = @PostId AND c.deleted_at_utc IS NULL
        ORDER BY c.created_at_utc;

        SELECT r.reaction_type, COUNT(*) AS reaction_count
        FROM dbo.feed_post_reactions AS r
        WHERE r.feed_post_id = @PostId
        GROUP BY r.reaction_type;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_AddFeedPostComment
        @UserKey nvarchar(100),
        @PostKey uniqueidentifier,
        @Body nvarchar(300)
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @AuthorId int = (SELECT id FROM dbo.app_users WHERE user_key = @UserKey);
        DECLARE @PostId bigint = (
            SELECT feed_post_id FROM dbo.feed_posts
            WHERE post_key = @PostKey AND deleted_at_utc IS NULL);
        IF @AuthorId IS NULL OR @PostId IS NULL
            THROW 51804, ''Comment target not found.'', 1;

        INSERT dbo.feed_post_comments (feed_post_id, author_user_id, body)
        VALUES (@PostId, @AuthorId, @Body);

        SELECT c.feed_post_comment_id, c.body, c.created_at_utc
        FROM dbo.feed_post_comments AS c
        WHERE c.feed_post_comment_id = SCOPE_IDENTITY();
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_AddFeedPostReaction
        @UserKey nvarchar(100),
        @PostKey uniqueidentifier,
        @ReactionType nvarchar(30)
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @UserId int = (SELECT id FROM dbo.app_users WHERE user_key = @UserKey);
        DECLARE @PostId bigint = (
            SELECT feed_post_id FROM dbo.feed_posts
            WHERE post_key = @PostKey AND deleted_at_utc IS NULL);
        IF @UserId IS NULL OR @PostId IS NULL
            THROW 51805, ''Reaction target not found.'', 1;

        /* Idempotent: the PK swallows duplicates without erroring. */
        IF NOT EXISTS (
            SELECT 1 FROM dbo.feed_post_reactions
            WHERE feed_post_id = @PostId AND user_id = @UserId
              AND reaction_type = @ReactionType)
            INSERT dbo.feed_post_reactions (feed_post_id, user_id, reaction_type)
            VALUES (@PostId, @UserId, @ReactionType);

        SELECT r.reaction_type, COUNT(*) AS reaction_count
        FROM dbo.feed_post_reactions AS r
        WHERE r.feed_post_id = @PostId
        GROUP BY r.reaction_type;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_RemoveFeedPostReaction
        @UserKey nvarchar(100),
        @PostKey uniqueidentifier,
        @ReactionType nvarchar(30)
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @UserId int = (SELECT id FROM dbo.app_users WHERE user_key = @UserKey);
        DECLARE @PostId bigint = (
            SELECT feed_post_id FROM dbo.feed_posts
            WHERE post_key = @PostKey AND deleted_at_utc IS NULL);
        IF @UserId IS NULL OR @PostId IS NULL
            THROW 51806, ''Reaction target not found.'', 1;

        DELETE dbo.feed_post_reactions
        WHERE feed_post_id = @PostId AND user_id = @UserId
          AND reaction_type = @ReactionType;

        SELECT r.reaction_type, COUNT(*) AS reaction_count
        FROM dbo.feed_post_reactions AS r
        WHERE r.feed_post_id = @PostId
        GROUP BY r.reaction_type;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ToggleFeedPostSave
        @UserKey nvarchar(100),
        @PostKey uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @UserId int = (SELECT id FROM dbo.app_users WHERE user_key = @UserKey);
        DECLARE @PostId bigint = (
            SELECT feed_post_id FROM dbo.feed_posts
            WHERE post_key = @PostKey AND deleted_at_utc IS NULL);
        IF @UserId IS NULL OR @PostId IS NULL
            THROW 51807, ''Save target not found.'', 1;

        IF EXISTS (SELECT 1 FROM dbo.feed_post_saves
                   WHERE feed_post_id = @PostId AND user_id = @UserId)
        BEGIN
            DELETE dbo.feed_post_saves
            WHERE feed_post_id = @PostId AND user_id = @UserId;
            SELECT CAST(0 AS bit) AS saved;
        END
        ELSE
        BEGIN
            INSERT dbo.feed_post_saves (feed_post_id, user_id)
            VALUES (@PostId, @UserId);
            SELECT CAST(1 AS bit) AS saved;
        END
    END');

    INSERT dbo.schema_migrations (migration_id, description)
    SELECT N'PS-PLAT-008', N'People & Interests feed domain (PS-FEAT-002)'
    WHERE NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-008');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
