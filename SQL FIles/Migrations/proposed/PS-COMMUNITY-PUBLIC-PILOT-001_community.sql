/* PS-COMMUNITY-PUBLIC-PILOT-001 canonical owner-authored public conversations. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
       OR OBJECT_ID(N'dbo.app_users', N'U') IS NULL
        THROW 52400, 'PeerSlate identity foundation is required.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 52401, 'PS-AUTH-001 must be applied first.', 1;

    DECLARE @CommunityTables TABLE(object_name sysname NOT NULL PRIMARY KEY);
    INSERT @CommunityTables(object_name) VALUES
        (N'community_posts'),(N'community_post_revisions'),
        (N'community_contributions'),(N'community_contribution_revisions'),
        (N'community_responses'),(N'community_saves'),
        (N'community_contribution_saves'),(N'community_media'),
        (N'community_audit_events'),(N'community_outbox');
    DECLARE @CommunityProcedures TABLE(object_name sysname NOT NULL PRIMARY KEY);
    INSERT @CommunityProcedures(object_name) VALUES
        (N'usp_ListPublicCommunityFeed'),(N'usp_ListPublicCommunityShelf'),
        (N'usp_GetPublicCommunityPost'),
        (N'usp_GetPublicCommunityContribution'),
        (N'usp_SearchPublicCommunity'),(N'usp_PublishPublicCommunityPost'),
        (N'usp_EditPublicCommunityPost'),(N'usp_DeletePublicCommunityPost'),
        (N'usp_AddPublicCommunityContribution'),
        (N'usp_EditPublicCommunityContribution'),
        (N'usp_DeletePublicCommunityContribution'),
        (N'usp_SetPublicCommunityResponse'),
        (N'usp_RemovePublicCommunityResponse'),(N'usp_SetPublicCommunitySave'),
        (N'usp_SetPublicCommunityContributionSave'),
        (N'usp_ReservePublicCommunityMedia'),
        (N'usp_MarkPublicCommunityMediaUploaded'),
        (N'usp_GetPublicCommunityMediaForOwner'),
        (N'usp_CompletePublicCommunityMedia'),
        (N'usp_CompensatePublicCommunityMediaCompletion'),
        (N'usp_RejectPublicCommunityMedia'),
        (N'usp_ClaimPublicCommunityMediaCleanup'),
        (N'usp_CompletePublicCommunityMediaCleanup'),
        (N'usp_GetPublicCommunityMedia'),(N'usp_DeletePublicCommunityMedia');
    DECLARE @CommunityProcedureHashProperty sysname=N'PS_COMMUNITY_PUBLIC_PILOT_001_DEFINITION_HASH';
    DECLARE @CommunityConstraintHashProperty sysname=N'PS_COMMUNITY_PUBLIC_PILOT_001_CONSTRAINT_HASH';
    DECLARE @CommunityIndexHashProperty sysname=N'PS_COMMUNITY_PUBLIC_PILOT_001_INDEX_HASH';
    DECLARE @CommunityIndexes TABLE(object_name sysname NOT NULL,index_name sysname NOT NULL,is_unique bit NOT NULL,PRIMARY KEY(object_name,index_name));
    INSERT @CommunityIndexes(object_name,index_name,is_unique) VALUES
        (N'community_posts',N'UX_community_posts_author_idempotency',1),
        (N'community_posts',N'IX_community_posts_public_feed',0),
        (N'community_contributions',N'UX_community_contributions_author_idempotency',1),
        (N'community_contributions',N'IX_community_contributions_post',0),
        (N'community_media',N'IX_community_media_expiry',0),
        (N'community_media',N'IX_community_media_cleanup',0);
    DECLARE @CommunityChecks TABLE(object_name sysname NOT NULL,constraint_name sysname NOT NULL,PRIMARY KEY(object_name,constraint_name));
    INSERT @CommunityChecks(object_name,constraint_name) VALUES
        (N'community_posts',N'CK_community_posts_audience'),
        (N'community_posts',N'CK_community_posts_deletion'),
        (N'community_contributions',N'CK_community_contributions_shape'),
        (N'community_contributions',N'CK_community_contributions_deletion'),
        (N'community_media',N'CK_community_media_binding'),
        (N'community_media',N'CK_community_media_type'),
        (N'community_media',N'CK_community_media_size'),
        (N'community_media',N'CK_community_media_clean_ready'),
        (N'community_media',N'CK_community_media_cleanup_claim');
    DECLARE @CommunityAppliedAtUtc datetime2(7)=
        (SELECT applied_at_utc FROM dbo.schema_migrations WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001');

    IF @CommunityAppliedAtUtc IS NOT NULL
    BEGIN
        IF EXISTS
        (
            SELECT 1 FROM @CommunityTables AS expected
            LEFT JOIN sys.tables AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name
            WHERE actual.object_id IS NULL
        )
            THROW 52402, 'Community migration drift: an owned table is missing.', 1;
        IF EXISTS
        (
            SELECT 1 FROM @CommunityProcedures AS expected
            LEFT JOIN sys.procedures AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name
            LEFT JOIN sys.extended_properties AS property ON property.class=1 AND property.major_id=actual.object_id AND property.minor_id=0 AND property.name=@CommunityProcedureHashProperty
            WHERE actual.object_id IS NULL OR property.major_id IS NULL
               OR OBJECT_DEFINITION(actual.object_id) IS NULL
               OR CONVERT(nvarchar(64),property.value)<>CONVERT(nvarchar(64),HASHBYTES('SHA2_256',OBJECT_DEFINITION(actual.object_id)),2)
        )
            THROW 52403, 'Community migration drift: a protected procedure changed.', 1;
        IF EXISTS
        (
            SELECT 1
            FROM @CommunityIndexes AS expected
            LEFT JOIN sys.indexes AS actual
              ON actual.object_id=OBJECT_ID(N'dbo.'+expected.object_name,N'U')
             AND actual.name=expected.index_name
            LEFT JOIN sys.extended_properties AS property
              ON property.class=7 AND property.major_id=actual.object_id
             AND property.minor_id=actual.index_id AND property.name=@CommunityIndexHashProperty
            OUTER APPLY
            (
                SELECT CONCAT(
                    CONVERT(nvarchar(1),actual.is_unique),N'|',
                    CONVERT(nvarchar(10),actual.type),N'|',
                    COALESCE(actual.filter_definition,N'<none>'),N'|',
                    (
                        SELECT STRING_AGG(
                            CONCAT(CONVERT(nvarchar(10),column_record.index_column_id),N':',
                                   CONVERT(nvarchar(10),column_record.key_ordinal),N':',
                                   column_definition.name,N':',
                                   CONVERT(nvarchar(1),column_record.is_descending_key),N':',
                                   CONVERT(nvarchar(1),column_record.is_included_column)),N'|'
                        ) WITHIN GROUP (ORDER BY column_record.index_column_id)
                        FROM sys.index_columns AS column_record
                        JOIN sys.columns AS column_definition
                          ON column_definition.object_id=column_record.object_id
                         AND column_definition.column_id=column_record.column_id
                        WHERE column_record.object_id=actual.object_id
                          AND column_record.index_id=actual.index_id
                    )
                ) AS definition_signature
            ) AS signature
            WHERE actual.index_id IS NULL OR actual.is_disabled=1
               OR actual.is_hypothetical=1 OR actual.is_unique<>expected.is_unique
               OR property.major_id IS NULL OR signature.definition_signature IS NULL
               OR CONVERT(nvarchar(64),property.value)<>CONVERT(nvarchar(64),HASHBYTES('SHA2_256',signature.definition_signature),2)
        )
            THROW 52404, 'Community migration drift: a required index changed, moved, or was disabled.', 1;
        IF EXISTS
        (
            SELECT 1
            FROM @CommunityChecks AS expected
            LEFT JOIN sys.check_constraints AS actual
              ON actual.parent_object_id=OBJECT_ID(N'dbo.'+expected.object_name,N'U')
             AND actual.name=expected.constraint_name
            LEFT JOIN sys.extended_properties AS property
              ON property.class=1 AND property.major_id=actual.object_id
             AND property.minor_id=0 AND property.name=@CommunityConstraintHashProperty
            WHERE actual.object_id IS NULL OR actual.is_disabled=1 OR actual.is_not_trusted=1
               OR OBJECT_DEFINITION(actual.object_id) IS NULL OR property.major_id IS NULL
               OR CONVERT(nvarchar(64),property.value)<>CONVERT(nvarchar(64),HASHBYTES('SHA2_256',OBJECT_DEFINITION(actual.object_id)),2)
        ) OR COL_LENGTH(N'dbo.community_posts',N'idempotency_hash') IS NULL
          OR COL_LENGTH(N'dbo.community_contributions',N'idempotency_hash') IS NULL
          OR COL_LENGTH(N'dbo.community_media',N'scan_result') IS NULL
          OR COL_LENGTH(N'dbo.community_media',N'safe_byte_length') IS NULL
          OR COL_LENGTH(N'dbo.community_media',N'safe_sha256') IS NULL
          OR COL_LENGTH(N'dbo.community_media',N'blob_cleanup_completed_at_utc') IS NULL
          OR NOT EXISTS
          (
              SELECT 1
              FROM sys.columns
              WHERE object_id=OBJECT_ID(N'dbo.community_media')
                AND name=N'content_type'
                AND system_type_id=TYPE_ID(N'nvarchar')
                AND max_length=200
                AND is_nullable=0
          )
          OR NOT EXISTS
          (
              SELECT 1 FROM sys.foreign_keys AS foreign_key
              WHERE foreign_key.name=N'FK_community_media_post_owner'
                AND foreign_key.parent_object_id=OBJECT_ID(N'dbo.community_media')
                AND foreign_key.referenced_object_id=OBJECT_ID(N'dbo.community_posts')
                AND foreign_key.is_disabled=0 AND foreign_key.is_not_trusted=0
                AND foreign_key.delete_referential_action=0 AND foreign_key.update_referential_action=0
                AND (SELECT COUNT(*) FROM sys.foreign_key_columns WHERE constraint_object_id=foreign_key.object_id)=2
                AND EXISTS(SELECT 1 FROM sys.foreign_key_columns AS column_map WHERE column_map.constraint_object_id=foreign_key.object_id AND column_map.constraint_column_id=1 AND COL_NAME(column_map.parent_object_id,column_map.parent_column_id)=N'community_post_id' AND COL_NAME(column_map.referenced_object_id,column_map.referenced_column_id)=N'community_post_id')
                AND EXISTS(SELECT 1 FROM sys.foreign_key_columns AS column_map WHERE column_map.constraint_object_id=foreign_key.object_id AND column_map.constraint_column_id=2 AND COL_NAME(column_map.parent_object_id,column_map.parent_column_id)=N'uploader_user_id' AND COL_NAME(column_map.referenced_object_id,column_map.referenced_column_id)=N'author_user_id')
          )
          OR NOT EXISTS
          (
              SELECT 1 FROM sys.foreign_keys AS foreign_key
              WHERE foreign_key.name=N'FK_community_media_contribution_owner'
                AND foreign_key.parent_object_id=OBJECT_ID(N'dbo.community_media')
                AND foreign_key.referenced_object_id=OBJECT_ID(N'dbo.community_contributions')
                AND foreign_key.is_disabled=0 AND foreign_key.is_not_trusted=0
                AND foreign_key.delete_referential_action=0 AND foreign_key.update_referential_action=0
                AND (SELECT COUNT(*) FROM sys.foreign_key_columns WHERE constraint_object_id=foreign_key.object_id)=2
                AND EXISTS(SELECT 1 FROM sys.foreign_key_columns AS column_map WHERE column_map.constraint_object_id=foreign_key.object_id AND column_map.constraint_column_id=1 AND COL_NAME(column_map.parent_object_id,column_map.parent_column_id)=N'community_contribution_id' AND COL_NAME(column_map.referenced_object_id,column_map.referenced_column_id)=N'community_contribution_id')
                AND EXISTS(SELECT 1 FROM sys.foreign_key_columns AS column_map WHERE column_map.constraint_object_id=foreign_key.object_id AND column_map.constraint_column_id=2 AND COL_NAME(column_map.parent_object_id,column_map.parent_column_id)=N'uploader_user_id' AND COL_NAME(column_map.referenced_object_id,column_map.referenced_column_id)=N'author_user_id')
          )
            THROW 52405, 'Community migration drift: a protected constraint or column changed.', 1;
        COMMIT TRANSACTION;
        RETURN;
    END;

    IF EXISTS
    (
        SELECT 1 FROM @CommunityTables AS expected
        JOIN sys.tables AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name
    ) OR EXISTS
    (
        SELECT 1 FROM @CommunityProcedures AS expected
        JOIN sys.procedures AS actual ON actual.schema_id=SCHEMA_ID(N'dbo') AND actual.name=expected.object_name
    )
        THROW 52406, 'Community artifacts exist without the migration ledger record.', 1;

    IF OBJECT_ID(N'dbo.community_posts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_posts
        (
            community_post_id bigint IDENTITY(1,1) NOT NULL,
            post_key uniqueidentifier NOT NULL CONSTRAINT DF_community_posts_key DEFAULT NEWSEQUENTIALID(),
            author_user_id int NOT NULL,
            body nvarchar(4000) NOT NULL,
            intent nvarchar(30) NOT NULL,
            response_posture nvarchar(40) NOT NULL,
            audience nvarchar(20) NOT NULL,
            publication_state nvarchar(20) NOT NULL,
            moderation_state nvarchar(20) NOT NULL CONSTRAINT DF_community_posts_moderation DEFAULT N'clear',
            revision_number int NOT NULL CONSTRAINT DF_community_posts_revision DEFAULT 1,
            idempotency_key varchar(128) NOT NULL,
            idempotency_hash binary(32) NOT NULL,
            published_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_posts_published DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_posts_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            /* A legal hold lives here rather than in the retention migration
               because dbo.usp_ClaimPublicCommunityMediaCleanup below must be
               able to skip held records, and SQL Server resolves a column
               reference against an existing table at CREATE PROCEDURE time.
               Defining the columns in a later migration forced that procedure
               to be restated there, which trips this file's own definition
               hash guard. Independent review, 2026-08-04, F5.
               The hold marker is body-free: a short reason code, who set it,
               when, and a review date. PS-COMMUNITY-RETENTION-001 owns the
               procedure that writes these and the purge that honours them. */
            legal_hold_reason nvarchar(60) NULL,
            legal_hold_set_at_utc datetime2(7) NULL,
            legal_hold_set_by_user_id int NULL,
            legal_hold_review_on date NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_community_posts PRIMARY KEY (community_post_id),
            CONSTRAINT UQ_community_posts_key UNIQUE (post_key),
            CONSTRAINT UQ_community_posts_id_author UNIQUE (community_post_id, author_user_id),
            CONSTRAINT FK_community_posts_author FOREIGN KEY (author_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_community_posts_body CHECK (LEN(body) BETWEEN 1 AND 4000),
            CONSTRAINT CK_community_posts_intent CHECK (intent IN (N'post', N'question', N'small_win')),
            CONSTRAINT CK_community_posts_posture CHECK (response_posture IN (N'open_feedback', N'questions_welcome', N'sharing_only', N'help_welcome')),
            CONSTRAINT CK_community_posts_audience CHECK (audience = N'public'),
            CONSTRAINT CK_community_posts_publication CHECK (publication_state IN (N'published', N'deleted')),
            CONSTRAINT CK_community_posts_moderation CHECK (moderation_state IN (N'clear', N'held', N'removed')),
            CONSTRAINT CK_community_posts_deletion CHECK ((publication_state = N'deleted' AND deleted_at_utc IS NOT NULL) OR (publication_state = N'published' AND deleted_at_utc IS NULL)),
            /* A hold must be complete or absent; a partial hold is unreviewable. */
            CONSTRAINT CK_community_posts_legal_hold CHECK ((legal_hold_reason IS NULL AND legal_hold_set_at_utc IS NULL AND legal_hold_set_by_user_id IS NULL AND legal_hold_review_on IS NULL) OR (legal_hold_reason IS NOT NULL AND legal_hold_set_at_utc IS NOT NULL AND legal_hold_set_by_user_id IS NOT NULL AND legal_hold_review_on IS NOT NULL))
        );
        CREATE UNIQUE INDEX UX_community_posts_author_idempotency ON dbo.community_posts(author_user_id, idempotency_key);
        CREATE INDEX IX_community_posts_public_feed ON dbo.community_posts(publication_state, moderation_state, audience, published_at_utc DESC, post_key DESC);
    END;

    IF OBJECT_ID(N'dbo.community_post_revisions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_post_revisions
        (
            post_revision_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_community_post_revisions PRIMARY KEY,
            community_post_id bigint NOT NULL,
            revision_number int NOT NULL,
            body nvarchar(4000) NOT NULL,
            intent nvarchar(30) NOT NULL,
            response_posture nvarchar(40) NOT NULL,
            changed_by_user_id int NOT NULL,
            changed_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_post_revisions_changed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_community_post_revisions_post FOREIGN KEY (community_post_id) REFERENCES dbo.community_posts(community_post_id),
            CONSTRAINT FK_community_post_revisions_user FOREIGN KEY (changed_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT UQ_community_post_revisions UNIQUE (community_post_id, revision_number)
        );
    END;

    IF OBJECT_ID(N'dbo.community_contributions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_contributions
        (
            community_contribution_id bigint IDENTITY(1,1) NOT NULL,
            contribution_key uniqueidentifier NOT NULL CONSTRAINT DF_community_contributions_key DEFAULT NEWSEQUENTIALID(),
            community_post_id bigint NOT NULL,
            parent_contribution_id bigint NULL,
            author_user_id int NOT NULL,
            contribution_kind nvarchar(30) NOT NULL,
            body nvarchar(2000) NOT NULL,
            depth tinyint NOT NULL,
            revision_number int NOT NULL CONSTRAINT DF_community_contributions_revision DEFAULT 1,
            lifecycle_state nvarchar(20) NOT NULL CONSTRAINT DF_community_contributions_state DEFAULT N'active',
            moderation_state nvarchar(20) NOT NULL CONSTRAINT DF_community_contributions_moderation DEFAULT N'clear',
            idempotency_key varchar(128) NOT NULL,
            idempotency_hash binary(32) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_contributions_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_contributions_updated DEFAULT SYSUTCDATETIME(),
            deleted_at_utc datetime2(7) NULL,
            /* Same reasoning as community_posts above: the media cleanup claim
               must be able to skip held records, so the hold columns live with
               the table the procedure reads. Independent review, F5. */
            legal_hold_reason nvarchar(60) NULL,
            legal_hold_set_at_utc datetime2(7) NULL,
            legal_hold_set_by_user_id int NULL,
            legal_hold_review_on date NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_community_contributions PRIMARY KEY (community_contribution_id),
            CONSTRAINT UQ_community_contributions_key UNIQUE (contribution_key),
            CONSTRAINT UQ_community_contributions_id_author UNIQUE (community_contribution_id, author_user_id),
            CONSTRAINT FK_community_contributions_post FOREIGN KEY (community_post_id) REFERENCES dbo.community_posts(community_post_id),
            CONSTRAINT FK_community_contributions_parent FOREIGN KEY (parent_contribution_id) REFERENCES dbo.community_contributions(community_contribution_id),
            CONSTRAINT FK_community_contributions_author FOREIGN KEY (author_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_community_contributions_kind CHECK (contribution_kind IN (N'comment', N'reply', N'author_update')),
            CONSTRAINT CK_community_contributions_body CHECK (LEN(body) BETWEEN 1 AND 2000),
            CONSTRAINT CK_community_contributions_depth CHECK (depth BETWEEN 0 AND 8),
            CONSTRAINT CK_community_contributions_shape CHECK (
                (parent_contribution_id IS NULL AND depth = 0 AND contribution_kind IN (N'comment', N'author_update'))
                OR (parent_contribution_id IS NOT NULL AND depth BETWEEN 1 AND 8 AND contribution_kind = N'reply')
            ),
            CONSTRAINT CK_community_contributions_state CHECK (lifecycle_state IN (N'active', N'deleted')),
            CONSTRAINT CK_community_contributions_moderation CHECK (moderation_state IN (N'clear', N'held', N'removed')),
            CONSTRAINT CK_community_contributions_deletion CHECK ((lifecycle_state = N'deleted' AND deleted_at_utc IS NOT NULL) OR (lifecycle_state = N'active' AND deleted_at_utc IS NULL)),
            CONSTRAINT CK_community_contributions_legal_hold CHECK ((legal_hold_reason IS NULL AND legal_hold_set_at_utc IS NULL AND legal_hold_set_by_user_id IS NULL AND legal_hold_review_on IS NULL) OR (legal_hold_reason IS NOT NULL AND legal_hold_set_at_utc IS NOT NULL AND legal_hold_set_by_user_id IS NOT NULL AND legal_hold_review_on IS NOT NULL))
        );
        CREATE UNIQUE INDEX UX_community_contributions_author_idempotency ON dbo.community_contributions(author_user_id, idempotency_key);
        CREATE INDEX IX_community_contributions_post ON dbo.community_contributions(community_post_id, created_at_utc, community_contribution_id);
    END;

    IF OBJECT_ID(N'dbo.community_contribution_revisions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_contribution_revisions
        (
            contribution_revision_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_community_contribution_revisions PRIMARY KEY,
            community_contribution_id bigint NOT NULL,
            revision_number int NOT NULL,
            body nvarchar(2000) NOT NULL,
            changed_by_user_id int NOT NULL,
            changed_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_contribution_revisions_changed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_community_contribution_revisions_contribution FOREIGN KEY (community_contribution_id) REFERENCES dbo.community_contributions(community_contribution_id),
            CONSTRAINT FK_community_contribution_revisions_user FOREIGN KEY (changed_by_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT UQ_community_contribution_revisions UNIQUE (community_contribution_id, revision_number)
        );
    END;

    IF OBJECT_ID(N'dbo.community_responses', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_responses
        (
            community_post_id bigint NOT NULL,
            user_id int NOT NULL,
            response_intention nvarchar(30) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_responses_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_responses_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_community_responses PRIMARY KEY (community_post_id, user_id),
            CONSTRAINT FK_community_responses_post FOREIGN KEY (community_post_id) REFERENCES dbo.community_posts(community_post_id),
            CONSTRAINT FK_community_responses_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_community_responses_intention CHECK (response_intention IN (N'celebrate', N'support', N'i_relate', N'ask', N'offer_help'))
        );
    END;

    IF OBJECT_ID(N'dbo.community_saves', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_saves
        (
            community_post_id bigint NOT NULL,
            user_id int NOT NULL,
            saved_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_saves_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_community_saves PRIMARY KEY (community_post_id, user_id),
            CONSTRAINT FK_community_saves_post FOREIGN KEY (community_post_id) REFERENCES dbo.community_posts(community_post_id),
            CONSTRAINT FK_community_saves_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id)
        );
    END;

    IF OBJECT_ID(N'dbo.community_contribution_saves', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_contribution_saves
        (
            community_contribution_id bigint NOT NULL,
            user_id int NOT NULL,
            saved_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_contribution_saves_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_community_contribution_saves PRIMARY KEY (community_contribution_id, user_id),
            CONSTRAINT FK_community_contribution_saves_contribution FOREIGN KEY (community_contribution_id) REFERENCES dbo.community_contributions(community_contribution_id),
            CONSTRAINT FK_community_contribution_saves_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id)
        );
    END;

    IF OBJECT_ID(N'dbo.community_media', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_media
        (
            community_media_id bigint IDENTITY(1,1) NOT NULL,
            media_key uniqueidentifier NOT NULL CONSTRAINT DF_community_media_key DEFAULT NEWSEQUENTIALID(),
            uploader_user_id int NOT NULL,
            community_post_id bigint NULL,
            community_contribution_id bigint NULL,
            display_name nvarchar(180) NOT NULL,
            content_type nvarchar(100) NOT NULL,
            byte_length bigint NOT NULL,
            sha256 binary(32) NOT NULL,
            original_blob_name nvarchar(220) NOT NULL,
            safe_blob_name nvarchar(220) NOT NULL,
            media_state nvarchar(30) NOT NULL CONSTRAINT DF_community_media_state DEFAULT N'reserved',
            pixel_width int NULL,
            pixel_height int NULL,
            safe_byte_length bigint NULL,
            safe_sha256 binary(32) NULL,
            scan_result nvarchar(30) NULL,
            scan_time_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_media_created DEFAULT SYSUTCDATETIME(),
            expires_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_media_expires DEFAULT DATEADD(hour, 24, SYSUTCDATETIME()),
            attached_at_utc datetime2(7) NULL,
            removed_at_utc datetime2(7) NULL,
            cleanup_claim_token uniqueidentifier NULL,
            cleanup_claimed_at_utc datetime2(7) NULL,
            blob_cleanup_completed_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_community_media PRIMARY KEY (community_media_id),
            CONSTRAINT UQ_community_media_key UNIQUE (media_key),
            CONSTRAINT UQ_community_media_original_blob UNIQUE (original_blob_name),
            CONSTRAINT UQ_community_media_safe_blob UNIQUE (safe_blob_name),
            CONSTRAINT FK_community_media_uploader FOREIGN KEY (uploader_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_community_media_post FOREIGN KEY (community_post_id) REFERENCES dbo.community_posts(community_post_id),
            CONSTRAINT FK_community_media_contribution FOREIGN KEY (community_contribution_id) REFERENCES dbo.community_contributions(community_contribution_id),
            CONSTRAINT FK_community_media_post_owner FOREIGN KEY (community_post_id, uploader_user_id) REFERENCES dbo.community_posts(community_post_id, author_user_id),
            CONSTRAINT FK_community_media_contribution_owner FOREIGN KEY (community_contribution_id, uploader_user_id) REFERENCES dbo.community_contributions(community_contribution_id, author_user_id),
            CONSTRAINT CK_community_media_type CHECK (content_type IN (N'image/jpeg', N'image/png', N'application/pdf', N'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
            CONSTRAINT CK_community_media_size CHECK (byte_length BETWEEN 1 AND 10485760),
            CONSTRAINT CK_community_media_state CHECK (media_state IN (N'reserved', N'uploaded', N'ready', N'rejected', N'failed', N'removed')),
            CONSTRAINT CK_community_media_clean_ready CHECK ((media_state = N'ready' AND scan_result IS NOT NULL AND scan_result = N'clean' AND scan_time_utc IS NOT NULL AND safe_byte_length IS NOT NULL AND safe_byte_length BETWEEN 1 AND 10485760 AND safe_sha256 IS NOT NULL AND DATALENGTH(safe_sha256)=32) OR media_state <> N'ready'),
            CONSTRAINT CK_community_media_cleanup_claim CHECK ((cleanup_claim_token IS NULL AND cleanup_claimed_at_utc IS NULL) OR (cleanup_claim_token IS NOT NULL AND cleanup_claimed_at_utc IS NOT NULL)),
            CONSTRAINT CK_community_media_binding CHECK (NOT (community_post_id IS NOT NULL AND community_contribution_id IS NOT NULL))
        );
        CREATE INDEX IX_community_media_expiry ON dbo.community_media(media_state, expires_at_utc) WHERE community_post_id IS NULL AND community_contribution_id IS NULL;
        CREATE INDEX IX_community_media_cleanup ON dbo.community_media(blob_cleanup_completed_at_utc, cleanup_claimed_at_utc, expires_at_utc);
    END;

    IF OBJECT_ID(N'dbo.community_audit_events', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_audit_events
        (
            community_audit_event_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_community_audit_events PRIMARY KEY,
            actor_user_id int NOT NULL,
            entity_type nvarchar(40) NOT NULL,
            entity_key uniqueidentifier NOT NULL,
            action_type nvarchar(50) NOT NULL,
            occurred_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_audit_events_occurred DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_community_audit_events_user FOREIGN KEY (actor_user_id) REFERENCES dbo.app_users(id)
        );
    END;

    IF OBJECT_ID(N'dbo.community_outbox', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.community_outbox
        (
            community_outbox_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_community_outbox PRIMARY KEY,
            event_key uniqueidentifier NOT NULL CONSTRAINT DF_community_outbox_key DEFAULT NEWSEQUENTIALID(),
            event_type nvarchar(80) NOT NULL,
            entity_key uniqueidentifier NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_community_outbox_created DEFAULT SYSUTCDATETIME(),
            processed_at_utc datetime2(7) NULL,
            CONSTRAINT UQ_community_outbox_key UNIQUE (event_key)
        );
    END;

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ListPublicCommunityFeed
        @AsOfUtc datetime2(7),
        @AfterPublishedAtUtc datetime2(7) = NULL,
        @AfterPostKey uniqueidentifier = NULL,
        @PageLimit int = 12,
        @ViewerUserKey nvarchar(300) = NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        IF @AsOfUtc IS NULL OR @PageLimit NOT BETWEEN 1 AND 20
           OR ((@AfterPublishedAtUtc IS NULL AND @AfterPostKey IS NOT NULL) OR (@AfterPublishedAtUtc IS NOT NULL AND @AfterPostKey IS NULL))
            THROW 52410, ''Invalid Feed window.'', 1;
        DECLARE @ViewerId int=(SELECT id FROM dbo.app_users WHERE user_key=@ViewerUserKey AND active=1 AND account_status=N''active'');

        DECLARE @Page TABLE
        (
            community_post_id bigint PRIMARY KEY,
            published_at_utc datetime2(7) NOT NULL,
            post_key uniqueidentifier NOT NULL,
            page_rank int NOT NULL UNIQUE
        );
        INSERT @Page(community_post_id,published_at_utc,post_key,page_rank)
        SELECT candidate.community_post_id,candidate.published_at_utc,candidate.post_key,
               ROW_NUMBER() OVER(ORDER BY candidate.published_at_utc DESC,candidate.post_key DESC)
        FROM
        (
            SELECT TOP (@PageLimit + 1) post.community_post_id,post.published_at_utc,post.post_key
            FROM dbo.community_posts AS post
            WHERE post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public'' AND post.published_at_utc<=@AsOfUtc
              AND EXISTS(SELECT 1 FROM dbo.app_users AS author WHERE author.id=post.author_user_id AND author.active=1 AND author.account_status=N''active'')
              AND (@AfterPublishedAtUtc IS NULL OR post.published_at_utc<@AfterPublishedAtUtc OR (post.published_at_utc=@AfterPublishedAtUtc AND post.post_key<@AfterPostKey))
            ORDER BY post.published_at_utc DESC,post.post_key DESC
        ) AS candidate;

        SELECT
            post.post_key, app_user.display_name AS author_name,
            app_user.profile_image_url AS author_avatar_url,
            post.body, post.intent, post.response_posture,
            post.published_at_utc,
            CASE WHEN post.revision_number > 1 THEN post.updated_at_utc END AS edited_at_utc,
            post.revision_number,
            CAST(CASE WHEN viewer_save.user_id IS NULL THEN 0 ELSE 1 END AS bit) AS viewer_saved,
            viewer_response.response_intention AS viewer_response_intention,
            (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS contribution
             WHERE contribution.community_post_id = post.community_post_id
               AND contribution.lifecycle_state = N''active'' AND contribution.moderation_state = N''clear''
               AND EXISTS(SELECT 1 FROM dbo.app_users AS contributor WHERE contributor.id=contribution.author_user_id AND contributor.active=1 AND contributor.account_status=N''active'')) AS contribution_count
        FROM dbo.community_posts AS post
        JOIN @Page AS page_record ON page_record.community_post_id=post.community_post_id
        JOIN dbo.app_users AS app_user ON app_user.id = post.author_user_id
        LEFT JOIN dbo.community_saves AS viewer_save ON viewer_save.community_post_id=post.community_post_id AND viewer_save.user_id=@ViewerId
        LEFT JOIN dbo.community_responses AS viewer_response ON viewer_response.community_post_id=post.community_post_id AND viewer_response.user_id=@ViewerId
        WHERE page_record.page_rank<=@PageLimit
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND app_user.active=1 AND app_user.account_status=N''active''
        ORDER BY page_record.page_rank;

        SELECT media.media_key, media.community_post_id, post.post_key,
               media.display_name, media.content_type, media.byte_length,
               media.pixel_width, media.pixel_height
        FROM dbo.community_media AS media
        JOIN dbo.community_posts AS post ON post.community_post_id = media.community_post_id
        JOIN @Page AS page_record ON page_record.community_post_id=post.community_post_id
        JOIN dbo.app_users AS app_user ON app_user.id=post.author_user_id
        WHERE page_record.page_rank<=@PageLimit
          AND media.media_state = N''ready'' AND media.uploader_user_id=post.author_user_id
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND app_user.active=1 AND app_user.account_status=N''active'';

        DECLARE @Preview TABLE
        (
            community_contribution_id bigint NOT NULL PRIMARY KEY,
            community_post_id bigint NOT NULL,
            created_at_utc datetime2(7) NOT NULL,
            contribution_key uniqueidentifier NOT NULL,
            preview_rank int NOT NULL,
            UNIQUE(community_post_id,preview_rank)
        );
        INSERT @Preview(community_contribution_id,community_post_id,created_at_utc,contribution_key,preview_rank)
        SELECT preview.community_contribution_id,preview.community_post_id,preview.created_at_utc,preview.contribution_key,preview.preview_rank
        FROM @Page AS page_record
        CROSS APPLY
        (
            SELECT candidate.community_contribution_id,candidate.community_post_id,
                   candidate.created_at_utc,candidate.contribution_key,
                   ROW_NUMBER() OVER(ORDER BY candidate.created_at_utc DESC,candidate.contribution_key DESC) AS preview_rank
            FROM
            (
                SELECT TOP(5) contribution.community_contribution_id,contribution.community_post_id,
                       contribution.created_at_utc,contribution.contribution_key
                FROM dbo.community_contributions AS contribution
                JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
                WHERE contribution.community_post_id=page_record.community_post_id
                  AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
                  AND contributor.active=1 AND contributor.account_status=N''active''
                  AND contribution.created_at_utc<=@AsOfUtc
                ORDER BY contribution.created_at_utc DESC,contribution.contribution_key DESC
            ) AS candidate
        ) AS preview
        WHERE page_record.page_rank<=@PageLimit;

        SELECT contribution.contribution_key,post.post_key,
               parent.contribution_key AS parent_contribution_key,
               contribution.contribution_kind,contributor.display_name AS author_name,
               contributor.profile_image_url AS author_avatar_url,contribution.body,
               contribution.created_at_utc,
               CASE WHEN contribution.revision_number>1 THEN contribution.updated_at_utc END AS edited_at_utc,
               contribution.revision_number,contribution.depth,N''active'' AS projection_state,
               CAST(CASE WHEN viewer_save.user_id IS NULL THEN 0 ELSE 1 END AS bit) AS viewer_saved,
               (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS child
                WHERE child.parent_contribution_id=contribution.community_contribution_id
                  AND child.lifecycle_state=N''active'' AND child.moderation_state=N''clear''
                  AND EXISTS(SELECT 1 FROM dbo.app_users AS child_author WHERE child_author.id=child.author_user_id AND child_author.active=1 AND child_author.account_status=N''active'')) AS child_reply_count
        FROM @Preview AS preview
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=preview.community_contribution_id
        JOIN @Page AS page_record ON page_record.community_post_id=preview.community_post_id
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        LEFT JOIN dbo.community_contributions AS parent ON parent.community_contribution_id=contribution.parent_contribution_id
        LEFT JOIN dbo.community_contribution_saves AS viewer_save ON viewer_save.community_contribution_id=contribution.community_contribution_id AND viewer_save.user_id=@ViewerId
        WHERE preview.preview_rank<=4
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active''
        ORDER BY page_record.page_rank,preview.preview_rank;

        SELECT media.media_key,post.post_key,contribution.contribution_key,
               media.display_name,media.content_type,media.byte_length,
               media.pixel_width,media.pixel_height
        FROM dbo.community_media AS media
        JOIN @Preview AS preview ON preview.community_contribution_id=media.community_contribution_id
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=media.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE preview.preview_rank<=4
          AND media.media_state=N''ready'' AND media.uploader_user_id=contribution.author_user_id
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        SELECT post.post_key,
               COUNT(preview.community_contribution_id) AS selected_candidate_count,
               CAST(CASE WHEN COUNT(preview.community_contribution_id)>4 THEN 1 ELSE 0 END AS bit) AS has_more,
               boundary.created_at_utc AS boundary_created_at_utc,
               boundary.contribution_key AS boundary_contribution_key
        FROM @Page AS page_record
        JOIN dbo.community_posts AS post ON post.community_post_id=page_record.community_post_id
        LEFT JOIN @Preview AS preview ON preview.community_post_id=page_record.community_post_id
        OUTER APPLY
        (
            SELECT boundary_preview.created_at_utc,boundary_preview.contribution_key
            FROM @Preview AS boundary_preview
            WHERE boundary_preview.community_post_id=page_record.community_post_id
              AND boundary_preview.preview_rank=4
        ) AS boundary
        WHERE page_record.page_rank<=@PageLimit
        GROUP BY page_record.page_rank,post.post_key,boundary.created_at_utc,boundary.contribution_key
        ORDER BY page_record.page_rank;

        DECLARE @SelectedCandidateCount int=(SELECT COUNT(*) FROM @Page);
        DECLARE @EmittedCandidateCount int=CASE WHEN @SelectedCandidateCount>@PageLimit THEN @PageLimit ELSE @SelectedCandidateCount END;
        SELECT @EmittedCandidateCount AS selected_candidate_count,
               CAST(CASE WHEN @SelectedCandidateCount>@PageLimit THEN 1 ELSE 0 END AS bit) AS has_more,
               (SELECT published_at_utc FROM @Page WHERE page_rank=@EmittedCandidateCount) AS boundary_published_at_utc,
               (SELECT post_key FROM @Page WHERE page_rank=@EmittedCandidateCount) AS boundary_post_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_GetPublicCommunityPost
        @PostKey uniqueidentifier,
        @ViewerUserKey nvarchar(300) = NULL,
        @AsOfUtc datetime2(7) = NULL,
        @BeforeCreatedAtUtc datetime2(7) = NULL,
        @BeforeContributionKey uniqueidentifier = NULL,
        @PageSize int = 20
    AS
    BEGIN
        SET NOCOUNT ON;
        SET @AsOfUtc=COALESCE(@AsOfUtc,SYSUTCDATETIME());
        IF @PageSize NOT BETWEEN 1 AND 20
           OR ((@BeforeCreatedAtUtc IS NULL AND @BeforeContributionKey IS NOT NULL) OR (@BeforeCreatedAtUtc IS NOT NULL AND @BeforeContributionKey IS NULL))
            THROW 52412,''Invalid conversation window.'',1;
        DECLARE @PostId bigint = (
            SELECT post.community_post_id FROM dbo.community_posts AS post
            WHERE post.post_key = @PostKey AND post.publication_state = N''published''
              AND post.moderation_state = N''clear'' AND post.audience = N''public''
              AND EXISTS(SELECT 1 FROM dbo.app_users AS author WHERE author.id=post.author_user_id AND author.active=1 AND author.account_status=N''active'')
        );
        DECLARE @ViewerId int = (SELECT id FROM dbo.app_users WHERE user_key = @ViewerUserKey AND active = 1 AND account_status=N''active'');
        IF @PostId IS NULL RETURN;
        DECLARE @ContributionCandidates TABLE
        (
            community_contribution_id bigint NOT NULL PRIMARY KEY,
            created_at_utc datetime2(7) NOT NULL,
            contribution_key uniqueidentifier NOT NULL,
            page_rank int NOT NULL UNIQUE
        );
        INSERT @ContributionCandidates(community_contribution_id,created_at_utc,contribution_key,page_rank)
        SELECT candidate.community_contribution_id,candidate.created_at_utc,candidate.contribution_key,
               ROW_NUMBER() OVER(ORDER BY candidate.created_at_utc DESC,candidate.contribution_key DESC)
        FROM
        (
            SELECT TOP(@PageSize+1) contribution.community_contribution_id,contribution.created_at_utc,contribution.contribution_key
            FROM dbo.community_contributions AS contribution
            JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
            WHERE contribution.community_post_id=@PostId
              AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
              AND contributor.active=1 AND contributor.account_status=N''active''
              AND contribution.created_at_utc<=@AsOfUtc
              AND (@BeforeCreatedAtUtc IS NULL OR contribution.created_at_utc<@BeforeCreatedAtUtc
                   OR (contribution.created_at_utc=@BeforeCreatedAtUtc AND contribution.contribution_key<@BeforeContributionKey))
            ORDER BY contribution.created_at_utc DESC,contribution.contribution_key DESC
        ) AS candidate;

        DECLARE @ContributionPage TABLE
        (
            community_contribution_id bigint NOT NULL PRIMARY KEY
        );
        ;WITH ProjectionTree AS
        (
            SELECT contribution.community_contribution_id,contribution.parent_contribution_id
            FROM @ContributionCandidates AS candidate
            JOIN dbo.community_contributions AS contribution
              ON contribution.community_contribution_id=candidate.community_contribution_id
            WHERE candidate.page_rank<=@PageSize
            UNION ALL
            SELECT parent.community_contribution_id,parent.parent_contribution_id
            FROM dbo.community_contributions AS parent
            JOIN ProjectionTree AS child
              ON child.parent_contribution_id=parent.community_contribution_id
            WHERE parent.community_post_id=@PostId
        )
        INSERT @ContributionPage(community_contribution_id)
        SELECT DISTINCT community_contribution_id FROM ProjectionTree
        OPTION(MAXRECURSION 9);

        SELECT post.post_key, app_user.display_name AS author_name,
               app_user.profile_image_url AS author_avatar_url,
               post.body, post.intent, post.response_posture, post.published_at_utc,
               CASE WHEN post.revision_number > 1 THEN post.updated_at_utc END AS edited_at_utc,
               post.revision_number,
               (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS c WHERE c.community_post_id = post.community_post_id AND c.lifecycle_state = N''active'' AND c.moderation_state = N''clear'' AND EXISTS(SELECT 1 FROM dbo.app_users AS contributor WHERE contributor.id=c.author_user_id AND contributor.active=1 AND contributor.account_status=N''active'')) AS contribution_count
        FROM dbo.community_posts AS post JOIN dbo.app_users AS app_user ON app_user.id = post.author_user_id
        WHERE post.community_post_id = @PostId AND post.publication_state=N''published''
          AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND app_user.active=1 AND app_user.account_status=N''active'';

        DECLARE @CurrentProjectionIds TABLE(community_contribution_id bigint NOT NULL PRIMARY KEY);
        ;WITH AuthorizedContribution AS
        (
            SELECT contribution.community_contribution_id,contribution.parent_contribution_id
            FROM dbo.community_contributions AS contribution
            JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
            WHERE contribution.community_post_id=@PostId
              AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
              AND contributor.active=1 AND contributor.account_status=N''active''
              AND contribution.created_at_utc<=@AsOfUtc
        ),
        ProjectionTree AS
        (
            SELECT community_contribution_id,parent_contribution_id
            FROM AuthorizedContribution
            UNION ALL
            SELECT parent.community_contribution_id,parent.parent_contribution_id
            FROM dbo.community_contributions AS parent
            JOIN ProjectionTree AS child ON child.parent_contribution_id=parent.community_contribution_id
            WHERE parent.community_post_id=@PostId
        )
        INSERT @CurrentProjectionIds(community_contribution_id)
        SELECT DISTINCT community_contribution_id FROM ProjectionTree
        OPTION(MAXRECURSION 9);

        SELECT contribution.contribution_key, post.post_key,
               parent.contribution_key AS parent_contribution_key,
               CASE WHEN contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear'' AND app_user.active=1 AND app_user.account_status=N''active'' THEN contribution.contribution_kind END AS contribution_kind,
               CASE WHEN contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear'' AND app_user.active=1 AND app_user.account_status=N''active'' THEN app_user.display_name END AS author_name,
               CASE WHEN contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear'' AND app_user.active=1 AND app_user.account_status=N''active'' THEN app_user.profile_image_url END AS author_avatar_url,
               CASE WHEN contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear'' AND app_user.active=1 AND app_user.account_status=N''active'' THEN contribution.body END AS body,
               contribution.created_at_utc,
               CASE WHEN contribution.revision_number > 1 THEN contribution.updated_at_utc END AS edited_at_utc,
               contribution.revision_number, contribution.depth,
               CASE
                   WHEN contribution.lifecycle_state<>N''active'' OR contribution.moderation_state<>N''clear'' OR app_user.active<>1 OR app_user.account_status<>N''active'' THEN N''unavailable''
                   ELSE N''active''
               END AS projection_state,
               CAST(CASE WHEN contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear'' AND app_user.active=1 AND app_user.account_status=N''active'' AND viewer_save.user_id IS NOT NULL THEN 1 ELSE 0 END AS bit) AS viewer_saved,
               (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS child
                JOIN dbo.app_users AS child_author ON child_author.id=child.author_user_id
                WHERE child.parent_contribution_id=contribution.community_contribution_id
                  AND child.lifecycle_state=N''active'' AND child.moderation_state=N''clear''
                  AND child_author.active=1 AND child_author.account_status=N''active'') AS child_reply_count
        FROM dbo.community_contributions AS contribution
        JOIN @ContributionPage AS contribution_page ON contribution_page.community_contribution_id=contribution.community_contribution_id
        JOIN @CurrentProjectionIds AS current_projection ON current_projection.community_contribution_id=contribution.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id = contribution.community_post_id
        JOIN dbo.app_users AS app_user ON app_user.id = contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        LEFT JOIN dbo.community_contributions AS parent ON parent.community_contribution_id = contribution.parent_contribution_id
        LEFT JOIN dbo.community_contribution_saves AS viewer_save ON viewer_save.community_contribution_id=contribution.community_contribution_id AND viewer_save.user_id=@ViewerId
        WHERE contribution.community_post_id = @PostId
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active''
        ORDER BY contribution.created_at_utc DESC,contribution.contribution_key DESC;

        SELECT media.media_key, post.post_key, media.display_name, media.content_type,
               media.byte_length, media.pixel_width, media.pixel_height
        FROM dbo.community_media AS media JOIN dbo.community_posts AS post ON post.community_post_id = media.community_post_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE media.community_post_id = @PostId AND media.media_state = N''ready''
          AND media.uploader_user_id=post.author_user_id
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        SELECT media.media_key, contribution.contribution_key, media.display_name,
               media.content_type, media.byte_length, media.pixel_width, media.pixel_height
        FROM dbo.community_media AS media
        JOIN @ContributionPage AS contribution_page ON contribution_page.community_contribution_id=media.community_contribution_id
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id = media.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE contribution.community_post_id = @PostId AND contribution.lifecycle_state = N''active''
          AND contribution.moderation_state = N''clear'' AND media.media_state = N''ready''
          AND media.uploader_user_id=contribution.author_user_id
          AND EXISTS(SELECT 1 FROM dbo.app_users AS author WHERE author.id=contribution.author_user_id AND author.active=1 AND author.account_status=N''active'')
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        SELECT CAST(CASE WHEN save_record.user_id IS NULL THEN 0 ELSE 1 END AS bit) AS saved,
               response_record.response_intention
        FROM (VALUES (1)) AS seed(seed_value)
        LEFT JOIN dbo.community_saves AS save_record ON save_record.community_post_id = @PostId AND save_record.user_id = @ViewerId
        LEFT JOIN dbo.community_responses AS response_record ON response_record.community_post_id = @PostId AND response_record.user_id = @ViewerId
        WHERE EXISTS(SELECT 1 FROM dbo.community_posts AS eligible_post JOIN dbo.app_users AS eligible_author ON eligible_author.id=eligible_post.author_user_id WHERE eligible_post.community_post_id=@PostId AND eligible_post.publication_state=N''published'' AND eligible_post.moderation_state=N''clear'' AND eligible_post.audience=N''public'' AND eligible_author.active=1 AND eligible_author.account_status=N''active'');

        DECLARE @SelectedContributionCount int=(SELECT COUNT(*) FROM @ContributionCandidates);
        DECLARE @BoundaryRank int=CASE WHEN @SelectedContributionCount>@PageSize THEN @PageSize ELSE @SelectedContributionCount END;
        SELECT @SelectedContributionCount AS selected_candidate_count,
               CAST(CASE WHEN @SelectedContributionCount>@PageSize THEN 1 ELSE 0 END AS bit) AS has_more,
               (SELECT created_at_utc FROM @ContributionCandidates WHERE page_rank=@BoundaryRank) AS boundary_created_at_utc,
               (SELECT contribution_key FROM @ContributionCandidates WHERE page_rank=@BoundaryRank) AS boundary_contribution_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ListPublicCommunityShelf
        @PostKey uniqueidentifier,
        @AsOfUtc datetime2(7),
        @BeforeCreatedAtUtc datetime2(7)=NULL,
        @BeforeContributionKey uniqueidentifier=NULL,
        @PageSize int=20,
        @ViewerUserKey nvarchar(300)=NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        IF @AsOfUtc IS NULL OR @PageSize NOT BETWEEN 1 AND 20
           OR ((@BeforeCreatedAtUtc IS NULL AND @BeforeContributionKey IS NOT NULL) OR (@BeforeCreatedAtUtc IS NOT NULL AND @BeforeContributionKey IS NULL))
            THROW 52413,''Invalid Replies and updates window.'',1;
        DECLARE @PostId bigint=(
            SELECT post.community_post_id
            FROM dbo.community_posts AS post
            JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
            WHERE post.post_key=@PostKey
              AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
              AND post_author.active=1 AND post_author.account_status=N''active''
        );
        DECLARE @ViewerId int=(SELECT id FROM dbo.app_users WHERE user_key=@ViewerUserKey AND active=1 AND account_status=N''active'');
        DECLARE @ShelfPage TABLE
        (
            community_contribution_id bigint NOT NULL PRIMARY KEY,
            created_at_utc datetime2(7) NOT NULL,
            contribution_key uniqueidentifier NOT NULL,
            page_rank int NOT NULL UNIQUE
        );
        IF @PostId IS NOT NULL
        BEGIN
            INSERT @ShelfPage(community_contribution_id,created_at_utc,contribution_key,page_rank)
            SELECT candidate.community_contribution_id,candidate.created_at_utc,candidate.contribution_key,
                   ROW_NUMBER() OVER(ORDER BY candidate.created_at_utc DESC,candidate.contribution_key DESC)
            FROM
            (
                SELECT TOP(@PageSize+1) contribution.community_contribution_id,
                       contribution.created_at_utc,contribution.contribution_key
                FROM dbo.community_contributions AS contribution
                JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
                WHERE contribution.community_post_id=@PostId
                  AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
                  AND contributor.active=1 AND contributor.account_status=N''active''
                  AND contribution.created_at_utc<=@AsOfUtc
                  AND (@BeforeCreatedAtUtc IS NULL OR contribution.created_at_utc<@BeforeCreatedAtUtc
                       OR (contribution.created_at_utc=@BeforeCreatedAtUtc AND contribution.contribution_key<@BeforeContributionKey))
                ORDER BY contribution.created_at_utc DESC,contribution.contribution_key DESC
            ) AS candidate;
        END;

        SELECT post.post_key
        FROM dbo.community_posts AS post
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE post.community_post_id=@PostId
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        SELECT contribution.contribution_key,post.post_key,
               parent.contribution_key AS parent_contribution_key,
               contribution.contribution_kind,contributor.display_name AS author_name,
               contributor.profile_image_url AS author_avatar_url,contribution.body,
               contribution.created_at_utc,
               CASE WHEN contribution.revision_number>1 THEN contribution.updated_at_utc END AS edited_at_utc,
               contribution.revision_number,contribution.depth,N''active'' AS projection_state,
               CAST(CASE WHEN viewer_save.user_id IS NULL THEN 0 ELSE 1 END AS bit) AS viewer_saved,
               (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS child
                JOIN dbo.app_users AS child_author ON child_author.id=child.author_user_id
                WHERE child.parent_contribution_id=contribution.community_contribution_id
                  AND child.lifecycle_state=N''active'' AND child.moderation_state=N''clear''
                  AND child_author.active=1 AND child_author.account_status=N''active'') AS child_reply_count
        FROM @ShelfPage AS shelf_page
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=shelf_page.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        LEFT JOIN dbo.community_contributions AS parent ON parent.community_contribution_id=contribution.parent_contribution_id
        LEFT JOIN dbo.community_contribution_saves AS viewer_save ON viewer_save.community_contribution_id=contribution.community_contribution_id AND viewer_save.user_id=@ViewerId
        WHERE shelf_page.page_rank<=@PageSize
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active''
        ORDER BY shelf_page.page_rank;

        SELECT media.media_key,contribution.contribution_key,media.display_name,
               media.content_type,media.byte_length,media.pixel_width,media.pixel_height
        FROM @ShelfPage AS shelf_page
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=shelf_page.community_contribution_id
        JOIN dbo.community_media AS media ON media.community_contribution_id=contribution.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE shelf_page.page_rank<=@PageSize
          AND media.media_state=N''ready'' AND media.uploader_user_id=contribution.author_user_id
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        DECLARE @ShelfCandidateCount int=(SELECT COUNT(*) FROM @ShelfPage);
        DECLARE @ShelfBoundaryRank int=CASE WHEN @ShelfCandidateCount>@PageSize THEN @PageSize ELSE @ShelfCandidateCount END;
        SELECT @ShelfCandidateCount AS selected_candidate_count,
               CAST(CASE WHEN @ShelfCandidateCount>@PageSize THEN 1 ELSE 0 END AS bit) AS has_more,
               (SELECT created_at_utc FROM @ShelfPage WHERE page_rank=@ShelfBoundaryRank) AS boundary_created_at_utc,
               (SELECT contribution_key FROM @ShelfPage WHERE page_rank=@ShelfBoundaryRank) AS boundary_contribution_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_GetPublicCommunityContribution
        @PostKey uniqueidentifier,@ContributionKey uniqueidentifier,
        @ViewerUserKey nvarchar(300)=NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @SelectedId bigint=(
            SELECT contribution.community_contribution_id
            FROM dbo.community_contributions AS contribution
            JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
            JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
            JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
            WHERE post.post_key=@PostKey AND contribution.contribution_key=@ContributionKey
              AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
              AND contributor.active=1 AND contributor.account_status=N''active''
              AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
              AND post_author.active=1 AND post_author.account_status=N''active''
        );
        DECLARE @ViewerId int=(SELECT id FROM dbo.app_users WHERE user_key=@ViewerUserKey AND active=1 AND account_status=N''active'');
        DECLARE @Ancestors TABLE
        (
            community_contribution_id bigint NOT NULL PRIMARY KEY,
            relation_distance int NOT NULL UNIQUE
        );
        ;WITH AncestorTree AS
        (
            SELECT parent.community_contribution_id,parent.parent_contribution_id,1 AS relation_distance
            FROM dbo.community_contributions AS selected_contribution
            JOIN dbo.community_contributions AS parent ON parent.community_contribution_id=selected_contribution.parent_contribution_id
            WHERE selected_contribution.community_contribution_id=@SelectedId
            UNION ALL
            SELECT parent.community_contribution_id,parent.parent_contribution_id,child.relation_distance+1
            FROM AncestorTree AS child
            JOIN dbo.community_contributions AS current_ancestor ON current_ancestor.community_contribution_id=child.community_contribution_id
            JOIN dbo.community_contributions AS parent ON parent.community_contribution_id=current_ancestor.parent_contribution_id
        )
        INSERT @Ancestors(community_contribution_id,relation_distance)
        SELECT community_contribution_id,relation_distance FROM AncestorTree
        OPTION(MAXRECURSION 9);

        SELECT contribution.contribution_key,post.post_key,
               parent.contribution_key AS parent_contribution_key,
               contribution.contribution_kind,contributor.display_name AS author_name,
               contributor.profile_image_url AS author_avatar_url,contribution.body,
               contribution.created_at_utc,
               CASE WHEN contribution.revision_number>1 THEN contribution.updated_at_utc END AS edited_at_utc,
               contribution.revision_number,contribution.depth,N''active'' AS projection_state,
               CAST(CASE WHEN viewer_save.user_id IS NULL THEN 0 ELSE 1 END AS bit) AS viewer_saved,
               (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS child
                JOIN dbo.app_users AS child_author ON child_author.id=child.author_user_id
                WHERE child.parent_contribution_id=contribution.community_contribution_id
                  AND child.lifecycle_state=N''active'' AND child.moderation_state=N''clear''
                  AND child_author.active=1 AND child_author.account_status=N''active'') AS child_reply_count
        FROM dbo.community_contributions AS contribution
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        LEFT JOIN dbo.community_contributions AS parent ON parent.community_contribution_id=contribution.parent_contribution_id
        LEFT JOIN dbo.community_contribution_saves AS viewer_save ON viewer_save.community_contribution_id=contribution.community_contribution_id AND viewer_save.user_id=@ViewerId
        WHERE contribution.community_contribution_id=@SelectedId
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.post_key=@PostKey AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        SELECT media.media_key,contribution.contribution_key,media.display_name,
               media.content_type,media.byte_length,media.pixel_width,media.pixel_height
        FROM dbo.community_media AS media
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=media.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE contribution.community_contribution_id=@SelectedId
          AND media.media_state=N''ready'' AND media.uploader_user_id=contribution.author_user_id
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.post_key=@PostKey AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';

        SELECT ancestor_contribution.contribution_key,post.post_key,
               parent.contribution_key AS parent_contribution_key,
               CASE WHEN ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear'' AND ancestor_author.active=1 AND ancestor_author.account_status=N''active'' THEN ancestor_contribution.contribution_kind END AS contribution_kind,
               CASE WHEN ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear'' AND ancestor_author.active=1 AND ancestor_author.account_status=N''active'' THEN ancestor_author.display_name END AS author_name,
               CASE WHEN ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear'' AND ancestor_author.active=1 AND ancestor_author.account_status=N''active'' THEN ancestor_author.profile_image_url END AS author_avatar_url,
               CASE WHEN ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear'' AND ancestor_author.active=1 AND ancestor_author.account_status=N''active'' THEN ancestor_contribution.body END AS body,
               ancestor_contribution.created_at_utc,
               CASE WHEN ancestor_contribution.revision_number>1 THEN ancestor_contribution.updated_at_utc END AS edited_at_utc,
               ancestor_contribution.revision_number,ancestor_contribution.depth,
               CASE WHEN ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear'' AND ancestor_author.active=1 AND ancestor_author.account_status=N''active'' THEN N''active'' ELSE N''unavailable'' END AS projection_state,
               CAST(CASE WHEN ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear'' AND ancestor_author.active=1 AND ancestor_author.account_status=N''active'' AND viewer_save.user_id IS NOT NULL THEN 1 ELSE 0 END AS bit) AS viewer_saved,
               (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS child
                JOIN dbo.app_users AS child_author ON child_author.id=child.author_user_id
                WHERE child.parent_contribution_id=ancestor_contribution.community_contribution_id
                  AND child.lifecycle_state=N''active'' AND child.moderation_state=N''clear''
                  AND child_author.active=1 AND child_author.account_status=N''active'') AS child_reply_count
        FROM @Ancestors AS ancestor
        JOIN dbo.community_contributions AS ancestor_contribution ON ancestor_contribution.community_contribution_id=ancestor.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=ancestor_contribution.community_post_id
        JOIN dbo.app_users AS ancestor_author ON ancestor_author.id=ancestor_contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        LEFT JOIN dbo.community_contributions AS parent ON parent.community_contribution_id=ancestor_contribution.parent_contribution_id
        LEFT JOIN dbo.community_contribution_saves AS viewer_save ON viewer_save.community_contribution_id=ancestor_contribution.community_contribution_id AND viewer_save.user_id=@ViewerId
        WHERE post.post_key=@PostKey
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active''
          AND EXISTS
          (
              SELECT 1 FROM dbo.community_contributions AS selected_now
              JOIN dbo.app_users AS selected_author ON selected_author.id=selected_now.author_user_id
              WHERE selected_now.community_contribution_id=@SelectedId
                AND selected_now.lifecycle_state=N''active'' AND selected_now.moderation_state=N''clear''
                AND selected_author.active=1 AND selected_author.account_status=N''active''
          )
        ORDER BY ancestor.relation_distance DESC;

        SELECT media.media_key,ancestor_contribution.contribution_key,
               media.display_name,media.content_type,media.byte_length,
               media.pixel_width,media.pixel_height
        FROM @Ancestors AS ancestor
        JOIN dbo.community_contributions AS ancestor_contribution ON ancestor_contribution.community_contribution_id=ancestor.community_contribution_id
        JOIN dbo.community_media AS media ON media.community_contribution_id=ancestor_contribution.community_contribution_id
        JOIN dbo.community_posts AS post ON post.community_post_id=ancestor_contribution.community_post_id
        JOIN dbo.app_users AS ancestor_author ON ancestor_author.id=ancestor_contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE media.media_state=N''ready'' AND media.uploader_user_id=ancestor_contribution.author_user_id
          AND ancestor_contribution.lifecycle_state=N''active'' AND ancestor_contribution.moderation_state=N''clear''
          AND ancestor_author.active=1 AND ancestor_author.account_status=N''active''
          AND post.post_key=@PostKey AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active''
          AND EXISTS
          (
              SELECT 1 FROM dbo.community_contributions AS selected_now
              JOIN dbo.app_users AS selected_author ON selected_author.id=selected_now.author_user_id
              WHERE selected_now.community_contribution_id=@SelectedId
                AND selected_now.lifecycle_state=N''active'' AND selected_now.moderation_state=N''clear''
                AND selected_author.active=1 AND selected_author.account_status=N''active''
          );
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_SearchPublicCommunity
        @Query nvarchar(120),
        @ResultLimit int = 20,
        @ViewerUserKey nvarchar(300) = NULL
    AS
    BEGIN
        SET NOCOUNT ON;
        SET @Query = NULLIF(LTRIM(RTRIM(@Query)), N'''');
        IF @Query IS NULL OR LEN(@Query) < 2 OR @ResultLimit NOT BETWEEN 1 AND 20 THROW 52411, ''Invalid search.'', 1;
        DECLARE @ViewerId int=(SELECT id FROM dbo.app_users WHERE user_key=@ViewerUserKey AND active=1 AND account_status=N''active'');
        DECLARE @Pattern nvarchar(250) = N''%'' + REPLACE(REPLACE(REPLACE(@Query, N''['', N''[[]''), N''%'', N''[%]''), N''_'', N''[_]'') + N''%'';
        DECLARE @Matches TABLE(community_post_id bigint PRIMARY KEY,published_at_utc datetime2(7),post_key uniqueidentifier);
        INSERT @Matches(community_post_id,published_at_utc,post_key)
        SELECT TOP (@ResultLimit) post.community_post_id,post.published_at_utc,post.post_key
        FROM dbo.community_posts AS post
        WHERE post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND EXISTS(SELECT 1 FROM dbo.app_users AS author WHERE author.id=post.author_user_id AND author.active=1 AND author.account_status=N''active'')
          AND (post.body LIKE @Pattern OR EXISTS(SELECT 1 FROM dbo.community_contributions AS c WHERE c.community_post_id=post.community_post_id AND c.lifecycle_state=N''active'' AND c.moderation_state=N''clear'' AND c.body LIKE @Pattern AND EXISTS(SELECT 1 FROM dbo.app_users AS contributor WHERE contributor.id=c.author_user_id AND contributor.active=1 AND contributor.account_status=N''active'')))
        ORDER BY post.published_at_utc DESC,post.post_key DESC;

        SELECT
            post.post_key, app_user.display_name AS author_name,
            app_user.profile_image_url AS author_avatar_url,
            post.body, post.intent, post.response_posture, post.published_at_utc,
            CASE WHEN post.revision_number > 1 THEN post.updated_at_utc END AS edited_at_utc,
            post.revision_number,
            CAST(CASE WHEN viewer_save.user_id IS NULL THEN 0 ELSE 1 END AS bit) AS viewer_saved,
            viewer_response.response_intention AS viewer_response_intention,
            (SELECT COUNT_BIG(*) FROM dbo.community_contributions AS c WHERE c.community_post_id = post.community_post_id AND c.lifecycle_state = N''active'' AND c.moderation_state = N''clear'' AND EXISTS(SELECT 1 FROM dbo.app_users AS contributor WHERE contributor.id=c.author_user_id AND contributor.active=1 AND contributor.account_status=N''active'')) AS contribution_count
        FROM dbo.community_posts AS post JOIN @Matches AS match_record ON match_record.community_post_id=post.community_post_id JOIN dbo.app_users AS app_user ON app_user.id = post.author_user_id
        LEFT JOIN dbo.community_saves AS viewer_save ON viewer_save.community_post_id=post.community_post_id AND viewer_save.user_id=@ViewerId
        LEFT JOIN dbo.community_responses AS viewer_response ON viewer_response.community_post_id=post.community_post_id AND viewer_response.user_id=@ViewerId
        WHERE post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND app_user.active=1 AND app_user.account_status=N''active''
        ORDER BY post.published_at_utc DESC, post.post_key DESC;

        SELECT media.media_key, post.post_key, media.display_name, media.content_type,
               media.byte_length, media.pixel_width, media.pixel_height
        FROM dbo.community_media AS media JOIN dbo.community_posts AS post ON post.community_post_id = media.community_post_id JOIN @Matches AS match_record ON match_record.community_post_id=post.community_post_id
        JOIN dbo.app_users AS app_user ON app_user.id=post.author_user_id
        WHERE media.media_state = N''ready'' AND media.uploader_user_id=post.author_user_id
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND app_user.active=1 AND app_user.account_status=N''active'';
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_PublishPublicCommunityPost
        @UserKey nvarchar(300), @IdempotencyKey varchar(128), @Body nvarchar(4000),
        @Intent nvarchar(30), @ResponsePosture nvarchar(40), @Audience nvarchar(20),
        @AttachmentKeysJson nvarchar(max) = N''[]''
    AS
    BEGIN
        SET NOCOUNT ON; SET XACT_ABORT ON;
        DECLARE @UserId int = (SELECT id FROM dbo.app_users WHERE user_key = @UserKey AND active = 1 AND account_status = N''active'');
        IF @UserId IS NULL THROW 52420, ''Member unavailable.'', 1;
        IF @Audience IS NULL OR @Audience <> N''public'' OR @Intent IS NULL OR @Intent NOT IN (N''post'',N''question'',N''small_win'') OR @ResponsePosture IS NULL OR @ResponsePosture NOT IN (N''open_feedback'',N''questions_welcome'',N''sharing_only'',N''help_welcome'') OR @IdempotencyKey IS NULL OR LEN(@IdempotencyKey) NOT BETWEEN 16 AND 128 OR NULLIF(LTRIM(RTRIM(@Body)),N'''') IS NULL OR LEN(@Body) > 4000 OR @AttachmentKeysJson IS NULL OR ISJSON(@AttachmentKeysJson) <> 1
            THROW 52421, ''Invalid publication.'', 1;
        DECLARE @AttachmentCount int = (SELECT COUNT(*) FROM OPENJSON(@AttachmentKeysJson));
        IF @AttachmentCount > 4 OR EXISTS (SELECT 1 FROM OPENJSON(@AttachmentKeysJson) WHERE TRY_CONVERT(uniqueidentifier,[value]) IS NULL)
            THROW 52422, ''Invalid attachment set.'', 1;

        DECLARE @CommandHash binary(32)=HASHBYTES(''SHA2_256'',CONCAT(@Body,N''|'',@Intent,N''|'',@ResponsePosture,N''|'',@Audience,N''|'',@AttachmentKeysJson));
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityPublish;
        DECLARE @ExistingId bigint, @ExistingKey uniqueidentifier, @ExistingHash binary(32);
        SELECT @ExistingId = community_post_id, @ExistingKey = post_key, @ExistingHash=idempotency_hash
        FROM dbo.community_posts WITH (UPDLOCK,HOLDLOCK)
        WHERE author_user_id = @UserId AND idempotency_key = @IdempotencyKey;
        IF @ExistingId IS NOT NULL
        BEGIN
            IF @ExistingHash=@CommandHash
            BEGIN IF @StartedTransaction=1 COMMIT; SELECT N''existing'' AS outcome, @ExistingKey AS post_key; RETURN; END;
            IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPublish;
            SELECT N''idempotency_conflict'' AS outcome; RETURN;
        END;
        IF @AttachmentCount <> (
            SELECT COUNT(*) FROM dbo.community_media AS media WITH (UPDLOCK,HOLDLOCK)
            JOIN OPENJSON(@AttachmentKeysJson) AS requested ON media.media_key = TRY_CONVERT(uniqueidentifier,requested.[value])
            WHERE media.uploader_user_id=@UserId AND media.media_state=N''ready'' AND media.community_post_id IS NULL AND media.community_contribution_id IS NULL AND media.expires_at_utc>SYSUTCDATETIME()
        )
        BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPublish; THROW 52423, ''One or more attachments are not ready.'', 1; END;

        DECLARE @PostId bigint, @PostKey uniqueidentifier;
        INSERT dbo.community_posts(author_user_id,body,intent,response_posture,audience,publication_state,idempotency_key,idempotency_hash)
        VALUES(@UserId,LTRIM(RTRIM(@Body)),@Intent,@ResponsePosture,N''public'',N''published'',@IdempotencyKey,@CommandHash);
        SET @PostId=SCOPE_IDENTITY(); SELECT @PostKey=post_key FROM dbo.community_posts WHERE community_post_id=@PostId;
        INSERT dbo.community_post_revisions(community_post_id,revision_number,body,intent,response_posture,changed_by_user_id)
        VALUES(@PostId,1,LTRIM(RTRIM(@Body)),@Intent,@ResponsePosture,@UserId);
        UPDATE media SET community_post_id=@PostId, attached_at_utc=SYSUTCDATETIME()
        FROM dbo.community_media AS media JOIN OPENJSON(@AttachmentKeysJson) AS requested ON media.media_key=TRY_CONVERT(uniqueidentifier,requested.[value]);
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''post'',@PostKey,N''published'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.post.published'',@PostKey);
        IF @StartedTransaction=1 COMMIT;
        SELECT N''created'' AS outcome,@PostKey AS post_key,1 AS revision_number;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_EditPublicCommunityPost
        @UserKey nvarchar(300), @PostKey uniqueidentifier, @ExpectedRevision int,
        @Body nvarchar(4000), @Intent nvarchar(30), @ResponsePosture nvarchar(40)
    AS
    BEGIN
        SET NOCOUNT ON; SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52424, ''Member unavailable.'', 1;
        IF @ExpectedRevision IS NULL OR @ExpectedRevision<1 OR @Intent IS NULL OR @Intent NOT IN (N''post'',N''question'',N''small_win'') OR @ResponsePosture IS NULL OR @ResponsePosture NOT IN (N''open_feedback'',N''questions_welcome'',N''sharing_only'',N''help_welcome'') OR NULLIF(LTRIM(RTRIM(@Body)),N'''') IS NULL OR LEN(@Body)>4000 THROW 52425, ''Invalid edit.'', 1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityPostEdit;
        DECLARE @PostId bigint,@Revision int;
        SELECT @PostId=community_post_id,@Revision=revision_number FROM dbo.community_posts WITH(UPDLOCK,HOLDLOCK)
        WHERE post_key=@PostKey AND author_user_id=@UserId AND publication_state=N''published'';
        IF @PostId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostEdit; SELECT N''not_found'' AS outcome; RETURN; END;
        IF @Revision<>@ExpectedRevision BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostEdit; SELECT N''stale'' AS outcome; RETURN; END;
        SET @Revision=@Revision+1;
        UPDATE dbo.community_posts SET body=LTRIM(RTRIM(@Body)),intent=@Intent,response_posture=@ResponsePosture,revision_number=@Revision,updated_at_utc=SYSUTCDATETIME() WHERE community_post_id=@PostId;
        INSERT dbo.community_post_revisions(community_post_id,revision_number,body,intent,response_posture,changed_by_user_id) VALUES(@PostId,@Revision,LTRIM(RTRIM(@Body)),@Intent,@ResponsePosture,@UserId);
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''post'',@PostKey,N''edited'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.post.edited'',@PostKey);
        IF @StartedTransaction=1 COMMIT; SELECT N''updated'' AS outcome,@PostKey AS post_key,@Revision AS revision_number;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_DeletePublicCommunityPost
        @UserKey nvarchar(300), @PostKey uniqueidentifier, @ExpectedRevision int
    AS
    BEGIN
        SET NOCOUNT ON; SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52426, ''Member unavailable.'', 1;
        IF @ExpectedRevision IS NULL OR @ExpectedRevision<1 THROW 52427, ''Invalid revision precondition.'', 1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityPostDelete;
        DECLARE @PostId bigint,@Revision int,@State nvarchar(20);
        SELECT @PostId=community_post_id,@Revision=revision_number,@State=publication_state FROM dbo.community_posts WITH(UPDLOCK,HOLDLOCK) WHERE post_key=@PostKey AND author_user_id=@UserId;
        IF @PostId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostDelete; SELECT N''not_found'' AS outcome; RETURN; END;
        IF @State=N''deleted'' BEGIN IF @StartedTransaction=1 COMMIT; SELECT N''existing'' AS outcome,@PostKey AS post_key; RETURN; END;
        IF @Revision<>@ExpectedRevision BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityPostDelete; SELECT N''stale'' AS outcome; RETURN; END;
        UPDATE dbo.community_posts SET publication_state=N''deleted'',deleted_at_utc=SYSUTCDATETIME(),updated_at_utc=SYSUTCDATETIME(),revision_number=revision_number+1 WHERE community_post_id=@PostId;
        DELETE contribution_save FROM dbo.community_contribution_saves AS contribution_save
        JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=contribution_save.community_contribution_id
        WHERE contribution.community_post_id=@PostId;
        DELETE dbo.community_responses WHERE community_post_id=@PostId; DELETE dbo.community_saves WHERE community_post_id=@PostId;
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''post'',@PostKey,N''deleted'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.post.deleted'',@PostKey);
        IF @StartedTransaction=1 COMMIT; SELECT N''deleted'' AS outcome,@PostKey AS post_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_AddPublicCommunityContribution
        @UserKey nvarchar(300), @PostKey uniqueidentifier, @ParentContributionKey uniqueidentifier=NULL,
        @Body nvarchar(2000), @IdempotencyKey varchar(128), @AttachmentKeysJson nvarchar(max)=N''[]''
    AS
    BEGIN
        SET NOCOUNT ON; SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52430, ''Member unavailable.'',1;
        IF @IdempotencyKey IS NULL OR LEN(@IdempotencyKey) NOT BETWEEN 16 AND 128 OR NULLIF(LTRIM(RTRIM(@Body)),N'''') IS NULL OR LEN(@Body)>2000 OR @AttachmentKeysJson IS NULL OR ISJSON(@AttachmentKeysJson)<>1 THROW 52431,''Invalid contribution.'',1;
        DECLARE @AttachmentCount int=(SELECT COUNT(*) FROM OPENJSON(@AttachmentKeysJson));
        IF @AttachmentCount>4 OR EXISTS(SELECT 1 FROM OPENJSON(@AttachmentKeysJson) WHERE TRY_CONVERT(uniqueidentifier,[value]) IS NULL) THROW 52432,''Invalid attachment set.'',1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityContributionAdd;
        DECLARE @PostId bigint,@PostAuthorId int,@ParentId bigint,@Depth int=0,@ExistingId bigint,@ExistingKey uniqueidentifier,@ExistingHash binary(32),@ContributionKind nvarchar(30);
        SELECT @PostId=post.community_post_id,@PostAuthorId=post.author_user_id
        FROM dbo.community_posts AS post WITH(UPDLOCK,HOLDLOCK)
        JOIN dbo.app_users AS post_author WITH(UPDLOCK,HOLDLOCK) ON post_author.id=post.author_user_id
        WHERE post.post_key=@PostKey AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';
        IF @PostId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionAdd; SELECT N''not_found'' AS outcome; RETURN; END;
        IF @ParentContributionKey IS NOT NULL
        BEGIN
            SELECT @ParentId=parent.community_contribution_id,@Depth=parent.depth+1
            FROM dbo.community_contributions AS parent WITH(UPDLOCK,HOLDLOCK)
            JOIN dbo.app_users AS parent_author WITH(UPDLOCK,HOLDLOCK) ON parent_author.id=parent.author_user_id
            WHERE parent.contribution_key=@ParentContributionKey AND parent.community_post_id=@PostId
              AND parent.lifecycle_state=N''active'' AND parent.moderation_state=N''clear''
              AND parent_author.active=1 AND parent_author.account_status=N''active'';
            IF @ParentId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionAdd; SELECT N''not_found'' AS outcome; RETURN; END;
            IF @Depth>8 BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionAdd; SELECT N''depth_limit'' AS outcome; RETURN; END;
        END;
        SET @ContributionKind=CASE WHEN @ParentId IS NOT NULL THEN N''reply'' WHEN @PostAuthorId=@UserId THEN N''author_update'' ELSE N''comment'' END;
        DECLARE @CommandHash binary(32)=HASHBYTES(''SHA2_256'',CONCAT(CONVERT(nvarchar(36),@PostKey),N''|'',COALESCE(CONVERT(nvarchar(36),@ParentContributionKey),N''''),N''|'',@ContributionKind,N''|'',@Body,N''|'',@AttachmentKeysJson));
        SELECT @ExistingId=community_contribution_id,@ExistingKey=contribution_key,@ExistingHash=idempotency_hash FROM dbo.community_contributions WITH(UPDLOCK,HOLDLOCK) WHERE author_user_id=@UserId AND idempotency_key=@IdempotencyKey;
        IF @ExistingId IS NOT NULL BEGIN IF @ExistingHash=@CommandHash BEGIN IF @StartedTransaction=1 COMMIT; SELECT N''existing'' AS outcome,@ExistingKey AS contribution_key; RETURN; END; IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionAdd; SELECT N''idempotency_conflict'' AS outcome; RETURN; END;
        IF @AttachmentCount<>(SELECT COUNT(*) FROM dbo.community_media AS media WITH(UPDLOCK,HOLDLOCK) JOIN OPENJSON(@AttachmentKeysJson) AS requested ON media.media_key=TRY_CONVERT(uniqueidentifier,requested.[value]) WHERE media.uploader_user_id=@UserId AND media.media_state=N''ready'' AND media.community_post_id IS NULL AND media.community_contribution_id IS NULL AND media.expires_at_utc>SYSUTCDATETIME()) BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionAdd; THROW 52434,''One or more attachments are not ready.'',1; END;
        DECLARE @ContributionId bigint,@ContributionKey uniqueidentifier;
        INSERT dbo.community_contributions(community_post_id,parent_contribution_id,author_user_id,contribution_kind,body,depth,idempotency_key,idempotency_hash) VALUES(@PostId,@ParentId,@UserId,@ContributionKind,LTRIM(RTRIM(@Body)),@Depth,@IdempotencyKey,@CommandHash);
        SET @ContributionId=SCOPE_IDENTITY(); SELECT @ContributionKey=contribution_key FROM dbo.community_contributions WHERE community_contribution_id=@ContributionId;
        INSERT dbo.community_contribution_revisions(community_contribution_id,revision_number,body,changed_by_user_id) VALUES(@ContributionId,1,LTRIM(RTRIM(@Body)),@UserId);
        UPDATE media SET community_contribution_id=@ContributionId,attached_at_utc=SYSUTCDATETIME() FROM dbo.community_media AS media JOIN OPENJSON(@AttachmentKeysJson) AS requested ON media.media_key=TRY_CONVERT(uniqueidentifier,requested.[value]);
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''contribution'',@ContributionKey,N''published'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.contribution.published'',@ContributionKey);
        IF @StartedTransaction=1 COMMIT; SELECT N''created'' AS outcome,@ContributionKey AS contribution_key,1 AS revision_number;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_EditPublicCommunityContribution
        @UserKey nvarchar(300),@ContributionKey uniqueidentifier,@ExpectedRevision int,@Body nvarchar(2000)
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL OR @ExpectedRevision IS NULL OR @ExpectedRevision<1 OR NULLIF(LTRIM(RTRIM(@Body)),N'''') IS NULL OR LEN(@Body)>2000 THROW 52435,''Invalid contribution edit.'',1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityContributionEdit;
        DECLARE @Id bigint,@Revision int;
        SELECT @Id=community_contribution_id,@Revision=revision_number FROM dbo.community_contributions WITH(UPDLOCK,HOLDLOCK) WHERE contribution_key=@ContributionKey AND author_user_id=@UserId AND lifecycle_state=N''active'';
        IF @Id IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionEdit;SELECT N''not_found'' AS outcome;RETURN;END;
        IF @Revision<>@ExpectedRevision BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionEdit;SELECT N''stale'' AS outcome;RETURN;END;
        SET @Revision=@Revision+1; UPDATE dbo.community_contributions SET body=LTRIM(RTRIM(@Body)),revision_number=@Revision,updated_at_utc=SYSUTCDATETIME() WHERE community_contribution_id=@Id;
        INSERT dbo.community_contribution_revisions(community_contribution_id,revision_number,body,changed_by_user_id) VALUES(@Id,@Revision,LTRIM(RTRIM(@Body)),@UserId);
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''contribution'',@ContributionKey,N''edited'');
        IF @StartedTransaction=1 COMMIT;SELECT N''updated'' AS outcome,@ContributionKey AS contribution_key,@Revision AS revision_number;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_DeletePublicCommunityContribution
        @UserKey nvarchar(300),@ContributionKey uniqueidentifier,@ExpectedRevision int
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52436,''Member unavailable.'',1;
        IF @ExpectedRevision IS NULL OR @ExpectedRevision<1 THROW 52437,''Invalid revision precondition.'',1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityContributionDelete;
        DECLARE @Id bigint,@Revision int,@State nvarchar(20);
        SELECT @Id=community_contribution_id,@Revision=revision_number,@State=lifecycle_state FROM dbo.community_contributions WITH(UPDLOCK,HOLDLOCK) WHERE contribution_key=@ContributionKey AND author_user_id=@UserId;
        IF @Id IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionDelete;SELECT N''not_found'' AS outcome;RETURN;END;
        IF @State=N''deleted'' BEGIN IF @StartedTransaction=1 COMMIT;SELECT N''existing'' AS outcome,@ContributionKey AS contribution_key;RETURN;END;
        IF @Revision<>@ExpectedRevision BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionDelete;SELECT N''stale'' AS outcome;RETURN;END;
        UPDATE dbo.community_contributions SET lifecycle_state=N''deleted'',deleted_at_utc=SYSUTCDATETIME(),updated_at_utc=SYSUTCDATETIME(),revision_number=revision_number+1 WHERE community_contribution_id=@Id;
        DELETE dbo.community_contribution_saves WHERE community_contribution_id=@Id;
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''contribution'',@ContributionKey,N''deleted'');
        INSERT dbo.community_outbox(event_type,entity_key) VALUES(N''community.contribution.deleted'',@ContributionKey);
        IF @StartedTransaction=1 COMMIT;SELECT N''deleted'' AS outcome,@ContributionKey AS contribution_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_SetPublicCommunityResponse
        @UserKey nvarchar(300),@PostKey uniqueidentifier,@Intention nvarchar(30)
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52440,''Member unavailable.'',1;
        IF @Intention IS NULL OR @Intention NOT IN(N''celebrate'',N''support'',N''i_relate'',N''ask'',N''offer_help'') THROW 52441,''Invalid response.'',1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityResponseSet;
        DECLARE @PostId bigint;
        SELECT @PostId=post.community_post_id
        FROM dbo.community_posts AS post WITH(UPDLOCK,HOLDLOCK)
        JOIN dbo.app_users AS post_author WITH(UPDLOCK,HOLDLOCK) ON post_author.id=post.author_user_id
        WHERE post.post_key=@PostKey AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';
        IF @PostId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityResponseSet; SELECT N''not_found'' AS outcome;RETURN;END;
        MERGE dbo.community_responses WITH(HOLDLOCK) AS target
        USING(SELECT @PostId AS community_post_id,@UserId AS user_id) AS source
        ON target.community_post_id=source.community_post_id AND target.user_id=source.user_id
        WHEN MATCHED THEN UPDATE SET response_intention=@Intention,updated_at_utc=SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT(community_post_id,user_id,response_intention) VALUES(source.community_post_id,source.user_id,@Intention);
        INSERT dbo.community_audit_events(actor_user_id,entity_type,entity_key,action_type) VALUES(@UserId,N''response'',@PostKey,N''set'');
        IF @StartedTransaction=1 COMMIT;
        SELECT N''saved'' AS outcome,@Intention AS response_intention;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_RemovePublicCommunityResponse
        @UserKey nvarchar(300),@PostKey uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        DECLARE @PostId bigint=(SELECT community_post_id FROM dbo.community_posts WHERE post_key=@PostKey);
        IF @UserId IS NULL THROW 52442,''Member unavailable.'',1;
        IF @PostId IS NULL BEGIN SELECT N''not_found'' AS outcome;RETURN;END;
        DELETE dbo.community_responses WHERE community_post_id=@PostId AND user_id=@UserId;
        SELECT CASE WHEN @@ROWCOUNT=1 THEN N''removed'' ELSE N''existing'' END AS outcome;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_SetPublicCommunitySave
        @UserKey nvarchar(300),@PostKey uniqueidentifier,@Saved bit
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52443,''Member unavailable.'',1;
        IF @Saved IS NULL THROW 52444,''Invalid save state.'',1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunitySaveSet;
        DECLARE @PostId bigint;
        SELECT @PostId=post.community_post_id
        FROM dbo.community_posts AS post WITH(UPDLOCK,HOLDLOCK)
        JOIN dbo.app_users AS post_author WITH(UPDLOCK,HOLDLOCK) ON post_author.id=post.author_user_id
        WHERE post.post_key=@PostKey AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';
        IF @PostId IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunitySaveSet; SELECT N''not_found'' AS outcome;RETURN;END;
        IF @Saved=1
        BEGIN
            IF NOT EXISTS(SELECT 1 FROM dbo.community_saves WITH(UPDLOCK,HOLDLOCK) WHERE community_post_id=@PostId AND user_id=@UserId) INSERT dbo.community_saves(community_post_id,user_id) VALUES(@PostId,@UserId);
            IF @StartedTransaction=1 COMMIT;
            SELECT N''saved'' AS outcome;
        END
        ELSE
        BEGIN
            DELETE dbo.community_saves WHERE community_post_id=@PostId AND user_id=@UserId;
            DECLARE @Removed bit=CASE WHEN @@ROWCOUNT=1 THEN 1 ELSE 0 END;
            IF @StartedTransaction=1 COMMIT;
            SELECT CASE WHEN @Removed=1 THEN N''removed'' ELSE N''existing'' END AS outcome;
        END;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_SetPublicCommunityContributionSave
        @UserKey nvarchar(300),@ContributionKey uniqueidentifier,@Saved bit
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL THROW 52445,''Member unavailable.'',1;
        IF @Saved IS NULL THROW 52446,''Invalid save state.'',1;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityContributionSaveSet;
        DECLARE @ContributionId bigint;
        SELECT @ContributionId=contribution.community_contribution_id
        FROM dbo.community_contributions AS contribution WITH(UPDLOCK,HOLDLOCK)
        JOIN dbo.community_posts AS post ON post.community_post_id=contribution.community_post_id
        JOIN dbo.app_users AS contributor ON contributor.id=contribution.author_user_id
        JOIN dbo.app_users AS post_author ON post_author.id=post.author_user_id
        WHERE contribution.contribution_key=@ContributionKey
          AND contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
          AND contributor.active=1 AND contributor.account_status=N''active''
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
          AND post_author.active=1 AND post_author.account_status=N''active'';
        IF @ContributionId IS NULL
        BEGIN
            IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityContributionSaveSet;
            SELECT N''not_found'' AS outcome;RETURN;
        END;
        IF @Saved=1
        BEGIN
            IF NOT EXISTS(SELECT 1 FROM dbo.community_contribution_saves WITH(UPDLOCK,HOLDLOCK) WHERE community_contribution_id=@ContributionId AND user_id=@UserId)
                INSERT dbo.community_contribution_saves(community_contribution_id,user_id) VALUES(@ContributionId,@UserId);
            IF @StartedTransaction=1 COMMIT;
            SELECT N''saved'' AS outcome;
        END
        ELSE
        BEGIN
            DELETE dbo.community_contribution_saves WHERE community_contribution_id=@ContributionId AND user_id=@UserId;
            DECLARE @Removed bit=CASE WHEN @@ROWCOUNT=1 THEN 1 ELSE 0 END;
            IF @StartedTransaction=1 COMMIT;
            SELECT CASE WHEN @Removed=1 THEN N''removed'' ELSE N''existing'' END AS outcome;
        END;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ReservePublicCommunityMedia
        @UserKey nvarchar(300),@DisplayName nvarchar(180),@ContentType nvarchar(100),@ByteLength bigint,
        @Sha256 binary(32),@OriginalBlobName nvarchar(220),@SafeBlobName nvarchar(220)
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL OR @ContentType NOT IN(N''image/jpeg'',N''image/png'',N''application/pdf'',N''application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'') OR @ByteLength NOT BETWEEN 1 AND 10485760 OR DATALENGTH(@Sha256)<>32 OR NULLIF(LTRIM(RTRIM(@DisplayName)),N'''') IS NULL THROW 52450,''Invalid attachment reservation.'',1;
        INSERT dbo.community_media(uploader_user_id,display_name,content_type,byte_length,sha256,original_blob_name,safe_blob_name) VALUES(@UserId,@DisplayName,@ContentType,@ByteLength,@Sha256,@OriginalBlobName,@SafeBlobName);
        SELECT N''reserved'' AS outcome,media_key FROM dbo.community_media WHERE community_media_id=SCOPE_IDENTITY();
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_MarkPublicCommunityMediaUploaded
        @UserKey nvarchar(300),@MediaKey uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        UPDATE dbo.community_media SET media_state=N''uploaded'' WHERE media_key=@MediaKey AND uploader_user_id=@UserId AND media_state=N''reserved'' AND expires_at_utc>SYSUTCDATETIME();
        IF @@ROWCOUNT<>1 BEGIN SELECT N''not_found'' AS outcome;RETURN;END;
        SELECT N''uploaded'' AS outcome,@MediaKey AS media_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_GetPublicCommunityMediaForOwner
        @UserKey nvarchar(300),@MediaKey uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        SELECT media_key,display_name,content_type,byte_length,sha256,media_state,original_blob_name,safe_blob_name,pixel_width,pixel_height,safe_byte_length,safe_sha256,scan_result,scan_time_utc
        FROM dbo.community_media WHERE media_key=@MediaKey AND uploader_user_id=@UserId AND removed_at_utc IS NULL;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_CompletePublicCommunityMedia
        @UserKey nvarchar(300),@MediaKey uniqueidentifier,@SafeByteLength bigint,@SafeSha256 binary(32),
        @PixelWidth int=NULL,@PixelHeight int=NULL,@ScanTimeUtc datetime2(7)=NULL
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        UPDATE dbo.community_media SET media_state=N''ready'',pixel_width=@PixelWidth,pixel_height=@PixelHeight,
            safe_byte_length=@SafeByteLength,safe_sha256=@SafeSha256,scan_result=N''clean'',scan_time_utc=@ScanTimeUtc
        WHERE media_key=@MediaKey AND uploader_user_id=@UserId AND media_state=N''uploaded'' AND expires_at_utc>SYSUTCDATETIME()
          AND @ScanTimeUtc IS NOT NULL AND @SafeByteLength BETWEEN 1 AND 10485760 AND DATALENGTH(@SafeSha256)=32
          AND ((content_type IN(N''application/pdf'',N''application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'') AND @PixelWidth IS NULL AND @PixelHeight IS NULL AND @SafeByteLength=byte_length AND @SafeSha256=sha256)
            OR (content_type IN(N''image/jpeg'',N''image/png'') AND @PixelWidth>0 AND @PixelHeight>0));
        IF @@ROWCOUNT<>1 BEGIN SELECT N''not_found'' AS outcome;RETURN;END;
        SELECT N''ready'' AS outcome,media_key,display_name,content_type,media_state FROM dbo.community_media WHERE media_key=@MediaKey;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_CompensatePublicCommunityMediaCompletion
        @UserKey nvarchar(300),@MediaKey uniqueidentifier,@SafeByteLength bigint,@SafeSha256 binary(32),
        @PixelWidth int,@PixelHeight int
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL BEGIN SELECT N''not_found'' AS outcome;RETURN;END;
        IF @SafeByteLength IS NULL OR @SafeByteLength NOT BETWEEN 1 AND 10485760 OR @SafeSha256 IS NULL
           OR DATALENGTH(@SafeSha256)<>32 OR @PixelWidth IS NULL OR @PixelWidth<1 OR @PixelHeight IS NULL OR @PixelHeight<1
            THROW 52454,''Invalid attachment completion compensation.'',1;

        DECLARE @StartedTransaction bit=0,@Now datetime2(7)=SYSUTCDATETIME();
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityMediaCompleteComp;

        DECLARE @Found bit=0,@State nvarchar(30),@ExpiresAtUtc datetime2(7),
                @CurrentSafeByteLength bigint,@CurrentSafeSha256 binary(32),
                @CurrentPixelWidth int,@CurrentPixelHeight int,
                @DisplayName nvarchar(180),@ContentType nvarchar(100);
        SELECT @Found=1,@State=media_state,@ExpiresAtUtc=expires_at_utc,
               @CurrentSafeByteLength=safe_byte_length,@CurrentSafeSha256=safe_sha256,
               @CurrentPixelWidth=pixel_width,@CurrentPixelHeight=pixel_height,
               @DisplayName=display_name,@ContentType=content_type
        FROM dbo.community_media WITH(UPDLOCK,HOLDLOCK)
        WHERE media_key=@MediaKey AND uploader_user_id=@UserId;

        IF @Found=0
        BEGIN
            IF @StartedTransaction=1 COMMIT TRANSACTION;
            SELECT N''not_found'' AS outcome;
            RETURN;
        END;

        IF @State=N''ready''
        BEGIN
            IF @ContentType IN(N''image/jpeg'',N''image/png'')
               AND @CurrentSafeByteLength=@SafeByteLength AND @CurrentSafeSha256=@SafeSha256
               AND @CurrentPixelWidth=@PixelWidth AND @CurrentPixelHeight=@PixelHeight
            BEGIN
                IF @StartedTransaction=1 COMMIT TRANSACTION;
                SELECT N''ready'' AS outcome,@MediaKey AS media_key,@DisplayName AS display_name,
                       @ContentType AS content_type,N''ready'' AS media_state;
                RETURN;
            END;
            IF @StartedTransaction=1 COMMIT TRANSACTION;
            SELECT N''conflict'' AS outcome;
            RETURN;
        END;

        IF @State IN(N''rejected'',N''failed'',N''removed'') OR @ExpiresAtUtc<=@Now
        BEGIN
            UPDATE dbo.community_media
            SET media_state=N''removed'',removed_at_utc=COALESCE(removed_at_utc,@Now),
                cleanup_claim_token=NULL,cleanup_claimed_at_utc=NULL,
                blob_cleanup_completed_at_utc=NULL
            WHERE media_key=@MediaKey AND uploader_user_id=@UserId;
            IF @StartedTransaction=1 COMMIT TRANSACTION;
            SELECT N''cleanup_reopened'' AS outcome,N''removed'' AS media_state;
            RETURN;
        END;

        IF @StartedTransaction=1 COMMIT TRANSACTION;
        SELECT N''retryable'' AS outcome,@State AS media_state;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_RejectPublicCommunityMedia
        @UserKey nvarchar(300),@MediaKey uniqueidentifier,@TerminalState nvarchar(30)
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @TerminalState IS NULL OR @TerminalState NOT IN(N''rejected'',N''failed'') THROW 52451,''Invalid attachment state.'',1;
        UPDATE dbo.community_media SET media_state=@TerminalState,scan_result=CASE WHEN @TerminalState=N''rejected'' THEN N''malicious'' ELSE N''error'' END
        WHERE media_key=@MediaKey AND uploader_user_id=@UserId AND media_state IN(N''reserved'',N''uploaded'') AND community_post_id IS NULL AND community_contribution_id IS NULL;
        IF @@ROWCOUNT=1 BEGIN SELECT @TerminalState AS outcome,@TerminalState AS media_state;RETURN;END;
        SELECT N''existing'' AS outcome,media_state FROM dbo.community_media WHERE media_key=@MediaKey AND uploader_user_id=@UserId AND media_state IN(N''rejected'',N''failed'');
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanup
        @Take int = 8,@MediaKey uniqueidentifier = NULL,
        @PostKey uniqueidentifier = NULL,@ContributionKey uniqueidentifier = NULL
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        IF @Take IS NULL OR @Take NOT BETWEEN 1 AND 20
           OR (CASE WHEN @MediaKey IS NULL THEN 0 ELSE 1 END
             + CASE WHEN @PostKey IS NULL THEN 0 ELSE 1 END
             + CASE WHEN @ContributionKey IS NULL THEN 0 ELSE 1 END)>1
            THROW 52452,''Invalid cleanup batch.'',1;
        DECLARE @Now datetime2(7)=SYSUTCDATETIME(),@ClaimToken uniqueidentifier=NEWID(),@StartedTransaction bit=0;
        DECLARE @Candidates TABLE(community_media_id bigint NOT NULL PRIMARY KEY);
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityMediaCleanupClaim;

        INSERT @Candidates(community_media_id)
        SELECT TOP (@Take) media.community_media_id
        FROM dbo.community_media AS media WITH(UPDLOCK,READPAST,READCOMMITTEDLOCK)
        LEFT JOIN dbo.community_posts AS direct_post ON direct_post.community_post_id=media.community_post_id
        LEFT JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=media.community_contribution_id
        LEFT JOIN dbo.community_posts AS contribution_post ON contribution_post.community_post_id=contribution.community_post_id
        WHERE media.blob_cleanup_completed_at_utc IS NULL
          AND (@MediaKey IS NULL OR media.media_key=@MediaKey)
          AND (@PostKey IS NULL OR direct_post.post_key=@PostKey OR contribution_post.post_key=@PostKey)
          AND (@ContributionKey IS NULL OR contribution.contribution_key=@ContributionKey)
          AND (media.cleanup_claim_token IS NULL OR media.cleanup_claimed_at_utc<DATEADD(minute,-10,@Now))
          /* A hold anywhere on the chain that owns these bytes stops cleanup.
             Without this a feature named "legal hold" destroys exactly the
             attachments it exists to preserve. Independent review, F5.
             Scope limit: this suspends cleanup that has not yet run. Cleanup is
             claimed inside the removal request, so a hold applied afterwards
             still preserves the words and not the files -- preserving files
             requires the hold to precede the removal. */
          AND direct_post.legal_hold_reason IS NULL
          AND contribution.legal_hold_reason IS NULL
          AND contribution_post.legal_hold_reason IS NULL
          AND
          (
              media.media_state IN(N''rejected'',N''failed'',N''removed'')
              OR (media.community_post_id IS NULL AND media.community_contribution_id IS NULL AND media.expires_at_utc<=@Now)
              OR (direct_post.publication_state=N''deleted'' OR direct_post.moderation_state=N''removed'')
              OR (contribution.lifecycle_state=N''deleted'' OR contribution.moderation_state=N''removed''
                  OR contribution_post.publication_state=N''deleted'' OR contribution_post.moderation_state=N''removed'')
          )
        ORDER BY CASE WHEN media.media_state IN(N''rejected'',N''failed'',N''removed'') THEN 0 ELSE 1 END,
                 media.expires_at_utc,media.community_media_id;

        UPDATE media
        SET cleanup_claim_token=@ClaimToken,cleanup_claimed_at_utc=@Now
        FROM dbo.community_media AS media
        JOIN @Candidates AS candidate ON candidate.community_media_id=media.community_media_id;

        IF @StartedTransaction=1 COMMIT TRANSACTION;
        SELECT media.media_key,@ClaimToken AS cleanup_claim_token,
               media.original_blob_name,media.safe_blob_name
        FROM dbo.community_media AS media
        JOIN @Candidates AS candidate ON candidate.community_media_id=media.community_media_id
        WHERE media.cleanup_claim_token=@ClaimToken
        ORDER BY media.community_media_id;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_CompletePublicCommunityMediaCleanup
        @MediaKey uniqueidentifier,@ClaimToken uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;
        IF @MediaKey IS NULL OR @ClaimToken IS NULL THROW 52453,''Invalid cleanup completion.'',1;
        DECLARE @Now datetime2(7)=SYSUTCDATETIME();
        UPDATE dbo.community_media
        SET media_state=N''removed'',removed_at_utc=COALESCE(removed_at_utc,@Now),
            cleanup_claim_token=NULL,cleanup_claimed_at_utc=NULL,
            blob_cleanup_completed_at_utc=@Now
        WHERE media_key=@MediaKey AND cleanup_claim_token=@ClaimToken
          AND blob_cleanup_completed_at_utc IS NULL;
        IF @@ROWCOUNT<>1 BEGIN SELECT N''not_found'' AS outcome;RETURN;END;
        SELECT N''completed'' AS outcome,@MediaKey AS media_key;
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_GetPublicCommunityMedia @MediaKey uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;
        SELECT TOP(1) media.media_key,media.display_name,media.content_type,media.byte_length,media.sha256,
               media.safe_byte_length,media.safe_sha256,media.original_blob_name,media.safe_blob_name
        FROM dbo.community_media AS media
        LEFT JOIN dbo.community_posts AS direct_post ON direct_post.community_post_id=media.community_post_id
        LEFT JOIN dbo.app_users AS direct_author ON direct_author.id=direct_post.author_user_id
        LEFT JOIN dbo.community_contributions AS contribution ON contribution.community_contribution_id=media.community_contribution_id
        LEFT JOIN dbo.app_users AS contribution_author ON contribution_author.id=contribution.author_user_id
        LEFT JOIN dbo.community_posts AS contribution_post ON contribution_post.community_post_id=contribution.community_post_id
        LEFT JOIN dbo.app_users AS contribution_post_author ON contribution_post_author.id=contribution_post.author_user_id
        WHERE media.media_key=@MediaKey AND media.media_state=N''ready'' AND media.removed_at_utc IS NULL
          AND ((direct_post.publication_state=N''published'' AND direct_post.moderation_state=N''clear'' AND direct_post.audience=N''public''
                AND media.uploader_user_id=direct_post.author_user_id AND direct_author.active=1 AND direct_author.account_status=N''active'')
            OR (contribution.lifecycle_state=N''active'' AND contribution.moderation_state=N''clear''
                AND media.uploader_user_id=contribution.author_user_id AND contribution_author.active=1 AND contribution_author.account_status=N''active''
                AND contribution_post.publication_state=N''published'' AND contribution_post.moderation_state=N''clear'' AND contribution_post.audience=N''public''
                AND contribution_post_author.active=1 AND contribution_post_author.account_status=N''active''));
    END');

    EXEC(N'
    CREATE OR ALTER PROCEDURE dbo.usp_DeletePublicCommunityMedia @UserKey nvarchar(300),@MediaKey uniqueidentifier
    AS
    BEGIN
        SET NOCOUNT ON;SET XACT_ABORT ON;DECLARE @UserId int=(SELECT id FROM dbo.app_users WHERE user_key=@UserKey AND active=1 AND account_status=N''active'');
        IF @UserId IS NULL BEGIN SELECT N''not_found'' AS outcome;RETURN;END;
        DECLARE @StartedTransaction bit=0;
        IF @@TRANCOUNT=0
        BEGIN
            BEGIN TRANSACTION;
            SET @StartedTransaction=1;
        END
        ELSE SAVE TRANSACTION CommunityMediaDelete;
        DECLARE @State nvarchar(30),@Original nvarchar(220),@Safe nvarchar(220),@PostId bigint,@ContributionId bigint;
        SELECT @State=media_state,@Original=original_blob_name,@Safe=safe_blob_name,@PostId=community_post_id,@ContributionId=community_contribution_id FROM dbo.community_media WITH(UPDLOCK,HOLDLOCK) WHERE media_key=@MediaKey AND uploader_user_id=@UserId;
        IF @State IS NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityMediaDelete; SELECT N''not_found'' AS outcome;RETURN;END;
        IF @PostId IS NOT NULL OR @ContributionId IS NOT NULL BEGIN IF @StartedTransaction=1 ROLLBACK; ELSE ROLLBACK TRANSACTION CommunityMediaDelete; SELECT N''not_found'' AS outcome;RETURN;END;
        IF @State<>N''removed'' UPDATE dbo.community_media SET media_state=N''removed'',removed_at_utc=SYSUTCDATETIME() WHERE media_key=@MediaKey;
        IF @StartedTransaction=1 COMMIT;
        SELECT CASE WHEN @State=N''removed'' THEN N''existing'' ELSE N''removed'' END AS outcome,@Original AS original_blob_name,@Safe AS safe_blob_name;
    END');

    DECLARE @CommunityIndexTable sysname,@CommunityIndexName sysname,
            @CommunityIndexObjectId int,@CommunityIndexId int,
            @CommunityIndexSignature nvarchar(max),@CommunityIndexDefinitionHash nvarchar(64);
    DECLARE CommunityIndexCursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT object_name,index_name FROM @CommunityIndexes ORDER BY object_name,index_name;
    OPEN CommunityIndexCursor;
    FETCH NEXT FROM CommunityIndexCursor INTO @CommunityIndexTable,@CommunityIndexName;
    WHILE @@FETCH_STATUS=0
    BEGIN
        SET @CommunityIndexObjectId=OBJECT_ID(N'dbo.'+@CommunityIndexTable,N'U');
        SET @CommunityIndexId=(SELECT index_id FROM sys.indexes WHERE object_id=@CommunityIndexObjectId AND name=@CommunityIndexName);
        SET @CommunityIndexSignature=(
            SELECT CONCAT(
                CONVERT(nvarchar(1),index_record.is_unique),N'|',
                CONVERT(nvarchar(10),index_record.type),N'|',
                COALESCE(index_record.filter_definition,N'<none>'),N'|',
                (
                    SELECT STRING_AGG(
                        CONCAT(CONVERT(nvarchar(10),column_record.index_column_id),N':',
                               CONVERT(nvarchar(10),column_record.key_ordinal),N':',
                               column_definition.name,N':',
                               CONVERT(nvarchar(1),column_record.is_descending_key),N':',
                               CONVERT(nvarchar(1),column_record.is_included_column)),N'|'
                    ) WITHIN GROUP (ORDER BY column_record.index_column_id)
                    FROM sys.index_columns AS column_record
                    JOIN sys.columns AS column_definition
                      ON column_definition.object_id=column_record.object_id
                     AND column_definition.column_id=column_record.column_id
                    WHERE column_record.object_id=index_record.object_id
                      AND column_record.index_id=index_record.index_id
                )
            )
            FROM sys.indexes AS index_record
            WHERE index_record.object_id=@CommunityIndexObjectId
              AND index_record.index_id=@CommunityIndexId
        );
        IF @CommunityIndexObjectId IS NULL OR @CommunityIndexId IS NULL OR @CommunityIndexSignature IS NULL
            THROW 52404,'Community migration could not protect an owned index.',1;
        SET @CommunityIndexDefinitionHash=CONVERT(nvarchar(64),HASHBYTES('SHA2_256',@CommunityIndexSignature),2);
        EXEC sys.sp_addextendedproperty
            @name=@CommunityIndexHashProperty,@value=@CommunityIndexDefinitionHash,
            @level0type=N'SCHEMA',@level0name=N'dbo',
            @level1type=N'TABLE',@level1name=@CommunityIndexTable,
            @level2type=N'INDEX',@level2name=@CommunityIndexName;
        FETCH NEXT FROM CommunityIndexCursor INTO @CommunityIndexTable,@CommunityIndexName;
    END;
    CLOSE CommunityIndexCursor;
    DEALLOCATE CommunityIndexCursor;

    DECLARE @CommunityConstraintTable sysname,@CommunityConstraintName sysname,
            @CommunityConstraintObjectId int,@CommunityConstraintDefinition nvarchar(max),
            @CommunityConstraintDefinitionHash nvarchar(64);
    DECLARE CommunityConstraintCursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT object_name,constraint_name FROM @CommunityChecks ORDER BY object_name,constraint_name;
    OPEN CommunityConstraintCursor;
    FETCH NEXT FROM CommunityConstraintCursor INTO @CommunityConstraintTable,@CommunityConstraintName;
    WHILE @@FETCH_STATUS=0
    BEGIN
        SET @CommunityConstraintObjectId=(
            SELECT object_id FROM sys.check_constraints
            WHERE parent_object_id=OBJECT_ID(N'dbo.'+@CommunityConstraintTable,N'U')
              AND name=@CommunityConstraintName
        );
        SET @CommunityConstraintDefinition=OBJECT_DEFINITION(@CommunityConstraintObjectId);
        IF @CommunityConstraintObjectId IS NULL OR @CommunityConstraintDefinition IS NULL
            THROW 52405,'Community migration could not protect an owned check constraint.',1;
        SET @CommunityConstraintDefinitionHash=CONVERT(nvarchar(64),HASHBYTES('SHA2_256',@CommunityConstraintDefinition),2);
        EXEC sys.sp_addextendedproperty
            @name=@CommunityConstraintHashProperty,@value=@CommunityConstraintDefinitionHash,
            @level0type=N'SCHEMA',@level0name=N'dbo',
            @level1type=N'TABLE',@level1name=@CommunityConstraintTable,
            @level2type=N'CONSTRAINT',@level2name=@CommunityConstraintName;
        FETCH NEXT FROM CommunityConstraintCursor INTO @CommunityConstraintTable,@CommunityConstraintName;
    END;
    CLOSE CommunityConstraintCursor;
    DEALLOCATE CommunityConstraintCursor;

    DECLARE @CommunityProcedureName sysname,@CommunityProcedureObjectId int,
            @CommunityProcedureDefinition nvarchar(max),@CommunityDefinitionHash nvarchar(64);
    DECLARE CommunityProcedureCursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT object_name FROM @CommunityProcedures ORDER BY object_name;
    OPEN CommunityProcedureCursor;
    FETCH NEXT FROM CommunityProcedureCursor INTO @CommunityProcedureName;
    WHILE @@FETCH_STATUS=0
    BEGIN
        SET @CommunityProcedureObjectId=OBJECT_ID(N'dbo.'+@CommunityProcedureName,N'P');
        SET @CommunityProcedureDefinition=OBJECT_DEFINITION(@CommunityProcedureObjectId);
        IF @CommunityProcedureObjectId IS NULL OR @CommunityProcedureDefinition IS NULL
            THROW 52403,'Community migration could not protect an owned procedure.',1;
        SET @CommunityDefinitionHash=CONVERT(nvarchar(64),HASHBYTES('SHA2_256',@CommunityProcedureDefinition),2);
        EXEC sys.sp_addextendedproperty
            @name=@CommunityProcedureHashProperty,@value=@CommunityDefinitionHash,
            @level0type=N'SCHEMA',@level0name=N'dbo',
            @level1type=N'PROCEDURE',@level1name=@CommunityProcedureName;
        FETCH NEXT FROM CommunityProcedureCursor INTO @CommunityProcedureName;
    END;
    CLOSE CommunityProcedureCursor;
    DEALLOCATE CommunityProcedureCursor;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001')
        INSERT dbo.schema_migrations(migration_id,description,application_version)
        VALUES(N'PS-COMMUNITY-PUBLIC-PILOT-001',N'Owner-authored public Community pilot','1.0');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
