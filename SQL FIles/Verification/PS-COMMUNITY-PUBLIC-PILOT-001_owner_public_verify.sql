/* Production-safe Community verification. Synthetic rows stay in one outer transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001')
        THROW 52590,'Community migration is not registered.',1;
    IF (SELECT COUNT(*) FROM sys.foreign_keys
        WHERE parent_object_id=OBJECT_ID(N'dbo.community_media')
          AND referenced_object_id IN(OBJECT_ID(N'dbo.community_posts'),OBJECT_ID(N'dbo.community_contributions'))
          AND name IN(N'FK_community_media_post_owner',N'FK_community_media_contribution_owner')
          AND is_disabled=0 AND is_not_trusted=0)<>2
       OR NOT EXISTS
       (
           SELECT 1 FROM sys.foreign_keys AS foreign_key
           WHERE foreign_key.name=N'FK_community_media_post_owner'
             AND foreign_key.parent_object_id=OBJECT_ID(N'dbo.community_media')
             AND foreign_key.referenced_object_id=OBJECT_ID(N'dbo.community_posts')
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
             AND foreign_key.delete_referential_action=0 AND foreign_key.update_referential_action=0
             AND (SELECT COUNT(*) FROM sys.foreign_key_columns WHERE constraint_object_id=foreign_key.object_id)=2
             AND EXISTS(SELECT 1 FROM sys.foreign_key_columns AS column_map WHERE column_map.constraint_object_id=foreign_key.object_id AND column_map.constraint_column_id=1 AND COL_NAME(column_map.parent_object_id,column_map.parent_column_id)=N'community_contribution_id' AND COL_NAME(column_map.referenced_object_id,column_map.referenced_column_id)=N'community_contribution_id')
             AND EXISTS(SELECT 1 FROM sys.foreign_key_columns AS column_map WHERE column_map.constraint_object_id=foreign_key.object_id AND column_map.constraint_column_id=2 AND COL_NAME(column_map.parent_object_id,column_map.parent_column_id)=N'uploader_user_id' AND COL_NAME(column_map.referenced_object_id,column_map.referenced_column_id)=N'author_user_id')
       )
        THROW 52590,'Community media ownership constraints are missing, disabled, untrusted, or mis-scoped.',1;
    DECLARE @ConstraintHashProperty sysname=N'PS_COMMUNITY_PUBLIC_PILOT_001_CONSTRAINT_HASH';
    DECLARE @ExpectedChecks TABLE(object_name sysname NOT NULL,constraint_name sysname NOT NULL,PRIMARY KEY(object_name,constraint_name));
    INSERT @ExpectedChecks(object_name,constraint_name) VALUES
        (N'community_posts',N'CK_community_posts_audience'),
        (N'community_posts',N'CK_community_posts_deletion'),
        (N'community_contributions',N'CK_community_contributions_shape'),
        (N'community_contributions',N'CK_community_contributions_deletion'),
        (N'community_media',N'CK_community_media_binding'),
        (N'community_media',N'CK_community_media_type'),
        (N'community_media',N'CK_community_media_size'),
        (N'community_media',N'CK_community_media_clean_ready'),
        (N'community_media',N'CK_community_media_cleanup_claim');
    IF EXISTS
    (
        SELECT 1
        FROM @ExpectedChecks AS expected
        LEFT JOIN sys.check_constraints AS actual
          ON actual.parent_object_id=OBJECT_ID(N'dbo.'+expected.object_name,N'U')
         AND actual.name=expected.constraint_name
        LEFT JOIN sys.extended_properties AS property
          ON property.class=1 AND property.major_id=actual.object_id
         AND property.minor_id=0 AND property.name=@ConstraintHashProperty
        WHERE actual.object_id IS NULL OR actual.is_disabled=1 OR actual.is_not_trusted=1
           OR OBJECT_DEFINITION(actual.object_id) IS NULL OR property.major_id IS NULL
           OR CONVERT(nvarchar(64),property.value)<>CONVERT(nvarchar(64),HASHBYTES('SHA2_256',OBJECT_DEFINITION(actual.object_id)),2)
    )
        THROW 52590,'Community protected constraints are missing, changed, disabled, untrusted, or mis-scoped.',1;
    DECLARE @IndexHashProperty sysname=N'PS_COMMUNITY_PUBLIC_PILOT_001_INDEX_HASH';
    DECLARE @ExpectedIndexes TABLE(object_name sysname NOT NULL,index_name sysname NOT NULL,is_unique bit NOT NULL,PRIMARY KEY(object_name,index_name));
    INSERT @ExpectedIndexes(object_name,index_name,is_unique) VALUES
        (N'community_posts',N'UX_community_posts_author_idempotency',1),
        (N'community_posts',N'IX_community_posts_public_feed',0),
        (N'community_contributions',N'UX_community_contributions_author_idempotency',1),
        (N'community_contributions',N'IX_community_contributions_post',0),
        (N'community_media',N'IX_community_media_expiry',0),
        (N'community_media',N'IX_community_media_cleanup',0);
    IF EXISTS
    (
        SELECT 1
        FROM @ExpectedIndexes AS expected
        LEFT JOIN sys.indexes AS actual
          ON actual.object_id=OBJECT_ID(N'dbo.'+expected.object_name,N'U')
         AND actual.name=expected.index_name
        LEFT JOIN sys.extended_properties AS property
          ON property.class=7 AND property.major_id=actual.object_id
         AND property.minor_id=actual.index_id AND property.name=@IndexHashProperty
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
        WHERE actual.index_id IS NULL OR actual.is_disabled=1 OR actual.is_hypothetical=1
           OR actual.is_unique<>expected.is_unique OR property.major_id IS NULL
           OR signature.definition_signature IS NULL
           OR CONVERT(nvarchar(64),property.value)<>CONVERT(nvarchar(64),HASHBYTES('SHA2_256',signature.definition_signature),2)
    )
        THROW 52590,'Community protected indexes are missing, changed, moved, or disabled.',1;

    DECLARE @FeedProcedureDefinition nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListPublicCommunityFeed',N'P'));
    IF @FeedProcedureDefinition IS NULL
       OR CHARINDEX(N'DECLARE @SelectedCandidateCount int=(SELECT COUNT(*) FROM @Page)',@FeedProcedureDefinition)=0
       OR CHARINDEX(N'SELECT TOP (@PageLimit + 1)',@FeedProcedureDefinition)=0
       OR CHARINDEX(N'DECLARE @EmittedCandidateCount int=CASE WHEN @SelectedCandidateCount>@PageLimit THEN @PageLimit ELSE @SelectedCandidateCount END',@FeedProcedureDefinition)=0
       OR CHARINDEX(N'SELECT @EmittedCandidateCount AS selected_candidate_count',@FeedProcedureDefinition)=0
       OR CHARINDEX(N'CAST(CASE WHEN @SelectedCandidateCount>@PageLimit THEN 1 ELSE 0 END AS bit) AS has_more',@FeedProcedureDefinition)=0
       OR CHARINDEX(N'(SELECT published_at_utc FROM @Page WHERE page_rank=@EmittedCandidateCount) AS boundary_published_at_utc',@FeedProcedureDefinition)=0
       OR CHARINDEX(N'(SELECT post_key FROM @Page WHERE page_rank=@EmittedCandidateCount) AS boundary_post_key',@FeedProcedureDefinition)=0
       OR (LEN(@FeedProcedureDefinition)-LEN(REPLACE(@FeedProcedureDefinition,N'page_record.page_rank<=@PageLimit',N'')))/LEN(N'page_record.page_rank<=@PageLimit')<4
       OR CHARINDEX(N'app_user.active=1 AND app_user.account_status=N''active''',@FeedProcedureDefinition)=0
        THROW 52590,'Community Feed does not expose a content-free selected-candidate boundary.',1;
    DECLARE @ContributionProcedureDefinition nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_AddPublicCommunityContribution',N'P'));
    IF @ContributionProcedureDefinition IS NULL
       OR CHARINDEX(N'SELECT N''depth_limit'' AS outcome',@ContributionProcedureDefinition)=0
       OR CHARINDEX(N'SET @ContributionKind=CASE WHEN @ParentId IS NOT NULL THEN N''reply'' WHEN @PostAuthorId=@UserId THEN N''author_update'' ELSE N''comment'' END',@ContributionProcedureDefinition)=0
       OR EXISTS(SELECT 1 FROM sys.parameters WHERE object_id=OBJECT_ID(N'dbo.usp_AddPublicCommunityContribution',N'P') AND name=N'@ContributionKind')
        THROW 52590,'Community contribution writes do not expose the maximum-depth domain outcome.',1;
    IF OBJECT_ID(N'dbo.usp_ListPublicCommunityShelf',N'P') IS NULL
       OR OBJECT_ID(N'dbo.usp_GetPublicCommunityContribution',N'P') IS NULL
        THROW 52590,'Community shelf or selected-contribution reads are missing.',1;
    DECLARE @ConversationProcedureDefinition nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetPublicCommunityPost',N'P'));
    IF @ConversationProcedureDefinition IS NULL
       OR CHARINDEX(N'DECLARE @ContributionCandidates TABLE',@ConversationProcedureDefinition)=0
       OR CHARINDEX(N'WHERE candidate.page_rank<=@PageSize',@ConversationProcedureDefinition)=0
       OR CHARINDEX(N'INSERT @ContributionPage(community_contribution_id)',@ConversationProcedureDefinition)=0
       OR CHARINDEX(N'SELECT DISTINCT community_contribution_id FROM ProjectionTree',@ConversationProcedureDefinition)=0
       OR CHARINDEX(N'SELECT COUNT(*) FROM @ContributionCandidates',@ConversationProcedureDefinition)=0
        THROW 52590,'Community conversation paging does not preserve ancestor closure.',1;

    DECLARE @Suffix nvarchar(36)=CONVERT(nvarchar(36),NEWID());
    DECLARE @Issuer nvarchar(500)=N'urn:peerslate:community-verification';
    DECLARE @SubjectA nvarchar(500)=CONCAT(N'community-a-',@Suffix);
    DECLARE @SubjectB nvarchar(500)=CONCAT(N'community-b-',@Suffix);
    EXEC dbo.usp_UpsertAppUserFromAuth @AuthProvider=N'community-verification',@AuthIssuer=@Issuer,@AuthSubject=@SubjectA,@DisplayName=N'Community verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth @AuthProvider=N'community-verification',@AuthIssuer=@Issuer,@AuthSubject=@SubjectB,@DisplayName=N'Community verification owner B';

    DECLARE @UserKeyA nvarchar(300),@UserKeyB nvarchar(300),@UserIdA int,@UserIdB int;
    SELECT @UserKeyA=app_user.user_key,@UserIdA=app_user.id FROM dbo.app_users AS app_user JOIN dbo.user_identities AS identity_record ON identity_record.user_id=app_user.id WHERE identity_record.provider=N'community-verification' AND identity_record.issuer=@Issuer AND identity_record.subject=@SubjectA;
    SELECT @UserKeyB=app_user.user_key,@UserIdB=app_user.id FROM dbo.app_users AS app_user JOIN dbo.user_identities AS identity_record ON identity_record.user_id=app_user.id WHERE identity_record.provider=N'community-verification' AND identity_record.issuer=@Issuer AND identity_record.subject=@SubjectB;
    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserIdA=@UserIdB THROW 52591,'Synthetic Community owners were not provisioned.',1;

    /* Exercise exact XLSX reserve -> uploaded -> clean/ready metadata lifecycle. */
    DECLARE @XlsxContentType nvarchar(100)=N'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    DECLARE @XlsxDigest binary(32)=HASHBYTES('SHA2_256',N'community-xlsx-verification');
    DECLARE @XlsxBlobToken nvarchar(32)=REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N'');
    DECLARE @XlsxOriginalBlob nvarchar(220)=CONCAT(N'community/v1/aa/',@XlsxBlobToken,N'.xlsx');
    DECLARE @XlsxSafeBlob nvarchar(220)=CONCAT(N'community/v1/aa/',@XlsxBlobToken,N'-safe.xlsx');
    DECLARE @XlsxReserve TABLE(outcome nvarchar(30),media_key uniqueidentifier);
    INSERT @XlsxReserve(outcome,media_key)
    EXEC dbo.usp_ReservePublicCommunityMedia @UserKey=@UserKeyA,@DisplayName=N'Community gate tracker.xlsx',@ContentType=@XlsxContentType,@ByteLength=128,@Sha256=@XlsxDigest,@OriginalBlobName=@XlsxOriginalBlob,@SafeBlobName=@XlsxSafeBlob;
    DECLARE @XlsxMediaKey uniqueidentifier=(SELECT media_key FROM @XlsxReserve WHERE outcome=N'reserved');
    IF @XlsxMediaKey IS NULL THROW 52591,'Community XLSX reservation failed.',1;
    DECLARE @XlsxUploaded TABLE(outcome nvarchar(30),media_key uniqueidentifier);
    INSERT @XlsxUploaded(outcome,media_key)
    EXEC dbo.usp_MarkPublicCommunityMediaUploaded @UserKey=@UserKeyA,@MediaKey=@XlsxMediaKey;
    IF NOT EXISTS(SELECT 1 FROM @XlsxUploaded WHERE outcome=N'uploaded' AND media_key=@XlsxMediaKey)
        THROW 52591,'Community XLSX upload transition failed.',1;
    DECLARE @XlsxReady TABLE(outcome nvarchar(30),media_key uniqueidentifier,display_name nvarchar(180),content_type nvarchar(100),media_state nvarchar(30));
    DECLARE @XlsxScanTimeUtc datetime2(7)=SYSUTCDATETIME();
    INSERT @XlsxReady(outcome,media_key,display_name,content_type,media_state)
    EXEC dbo.usp_CompletePublicCommunityMedia @UserKey=@UserKeyA,@MediaKey=@XlsxMediaKey,@SafeByteLength=128,@SafeSha256=@XlsxDigest,@PixelWidth=NULL,@PixelHeight=NULL,@ScanTimeUtc=@XlsxScanTimeUtc;
    IF NOT EXISTS(SELECT 1 FROM @XlsxReady WHERE outcome=N'ready' AND media_key=@XlsxMediaKey AND content_type=@XlsxContentType AND media_state=N'ready')
       OR NOT EXISTS(SELECT 1 FROM dbo.community_media WHERE media_key=@XlsxMediaKey AND content_type=@XlsxContentType AND byte_length=128 AND safe_byte_length=128 AND sha256=@XlsxDigest AND safe_sha256=@XlsxDigest AND pixel_width IS NULL AND pixel_height IS NULL AND scan_result=N'clean' AND scan_time_utc=@XlsxScanTimeUtc)
        THROW 52591,'Community XLSX clean completion failed.',1;
    DELETE dbo.community_media WHERE media_key=@XlsxMediaKey;
    IF @@ROWCOUNT<>1 THROW 52591,'Community XLSX verification cleanup failed.',1;

    DECLARE @IdempotencyA varchar(128)=CONCAT('community-post-a-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@IdempotencyA,@Body=N'Community verification public post A',@Intent=N'question',@ResponsePosture=N'questions_welcome',@Audience=N'public',@AttachmentKeysJson=N'[]';
    DECLARE @PostKey uniqueidentifier,@PostId bigint;
    SELECT @PostKey=post_key,@PostId=community_post_id FROM dbo.community_posts WHERE author_user_id=@UserIdA AND idempotency_key=@IdempotencyA;
    IF @PostKey IS NULL OR NOT EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@PostId AND audience=N'public' AND publication_state=N'published' AND revision_number=1) THROW 52592,'Explicit public publication failed.',1;

    /* Same command is idempotent and cannot create a second post. */
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@IdempotencyA,@Body=N'Community verification public post A',@Intent=N'question',@ResponsePosture=N'questions_welcome',@Audience=N'public',@AttachmentKeysJson=N'[]';
    IF (SELECT COUNT(*) FROM dbo.community_posts WHERE author_user_id=@UserIdA AND idempotency_key=@IdempotencyA)<>1 THROW 52593,'Publication idempotency failed.',1;
    SELECT N'publish_conflict' AS verification_marker;
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@IdempotencyA,@Body=N'Changed replay must be rejected',@Intent=N'question',@ResponsePosture=N'questions_welcome',@Audience=N'public',@AttachmentKeysJson=N'[]';
    IF EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@PostId AND body=N'Changed replay must be rejected') OR @@TRANCOUNT<>1 THROW 52593,'Publication idempotency conflict or outer transaction preservation failed.',1;

    /* A different authenticated owner cannot edit the source. */
    SELECT N'cross_owner_post_edit' AS verification_marker;
    EXEC dbo.usp_EditPublicCommunityPost @UserKey=@UserKeyB,@PostKey=@PostKey,@ExpectedRevision=1,@Body=N'Cross-owner edit must not persist',@Intent=N'post',@ResponsePosture=N'open_feedback';
    IF EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@PostId AND body=N'Cross-owner edit must not persist') OR @@TRANCOUNT<>1 THROW 52594,'Cross-owner post edit or outer transaction preservation failed.',1;

    DECLARE @SearchQuery nvarchar(120)=CONCAT(N'verification-',@Suffix);
    DECLARE @EditedPostBody nvarchar(2000)=CONCAT(N'Community ',@SearchQuery,N' public post A');
    EXEC dbo.usp_EditPublicCommunityPost @UserKey=@UserKeyA,@PostKey=@PostKey,@ExpectedRevision=1,@Body=@EditedPostBody,@Intent=N'small_win',@ResponsePosture=N'open_feedback';
    IF NOT EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@PostId AND revision_number=2 AND body=@EditedPostBody) OR (SELECT COUNT(*) FROM dbo.community_post_revisions WHERE community_post_id=@PostId)<>2 THROW 52595,'Revision history failed.',1;

    DECLARE @ContributionIdempotency varchar(128)=CONCAT('community-reply-a-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyA,@PostKey=@PostKey,@Body=N'Community verification author update',@IdempotencyKey=@ContributionIdempotency,@AttachmentKeysJson=N'[]';
    DECLARE @ContributionKey uniqueidentifier,@ContributionId bigint;
    SELECT @ContributionKey=contribution_key,@ContributionId=community_contribution_id FROM dbo.community_contributions WHERE author_user_id=@UserIdA AND idempotency_key=@ContributionIdempotency;
    IF @ContributionKey IS NULL OR NOT EXISTS(SELECT 1 FROM dbo.community_contributions WHERE community_contribution_id=@ContributionId AND contribution_kind=N'author_update') THROW 52596,'Server-derived author update was not created.',1;
    SELECT N'contribution_conflict' AS verification_marker;
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyA,@PostKey=@PostKey,@Body=N'Changed contribution replay must be rejected',@IdempotencyKey=@ContributionIdempotency,@AttachmentKeysJson=N'[]';
    IF EXISTS(SELECT 1 FROM dbo.community_contributions WHERE community_contribution_id=@ContributionId AND body=N'Changed contribution replay must be rejected') OR @@TRANCOUNT<>1 THROW 52596,'Contribution idempotency conflict or outer transaction preservation failed.',1;
    SELECT N'cross_owner_contribution_edit' AS verification_marker;
    EXEC dbo.usp_EditPublicCommunityContribution @UserKey=@UserKeyB,@ContributionKey=@ContributionKey,@ExpectedRevision=1,@Body=N'Cross-owner reply edit';
    IF EXISTS(SELECT 1 FROM dbo.community_contributions WHERE community_contribution_id=@ContributionId AND body=N'Cross-owner reply edit') OR @@TRANCOUNT<>1 THROW 52597,'Cross-owner contribution edit or outer transaction preservation failed.',1;

    EXEC dbo.usp_SetPublicCommunityResponse @UserKey=@UserKeyA,@PostKey=@PostKey,@Intention=N'celebrate';
    EXEC dbo.usp_SetPublicCommunityResponse @UserKey=@UserKeyA,@PostKey=@PostKey,@Intention=N'offer_help';
    IF (SELECT COUNT(*) FROM dbo.community_responses WHERE community_post_id=@PostId AND user_id=@UserIdA)<>1 OR NOT EXISTS(SELECT 1 FROM dbo.community_responses WHERE community_post_id=@PostId AND user_id=@UserIdA AND response_intention=N'offer_help') THROW 52598,'Deterministic response replacement failed.',1;
    EXEC dbo.usp_SetPublicCommunitySave @UserKey=@UserKeyA,@PostKey=@PostKey,@Saved=1;
    EXEC dbo.usp_SetPublicCommunitySave @UserKey=@UserKeyA,@PostKey=@PostKey,@Saved=1;
    IF (SELECT COUNT(*) FROM dbo.community_saves WHERE community_post_id=@PostId AND user_id=@UserIdA)<>1 THROW 52599,'Deterministic private save failed.',1;

    /* Exercise every public read model and one synthetic ready attachment. */
    DECLARE @MediaKey uniqueidentifier=NEWID(),@BlobToken nvarchar(32)=REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N'');
    DECLARE @BlobName nvarchar(220)=CONCAT(N'community/v1/aa/',@BlobToken,N'.pdf');
    DECLARE @VerificationDigest binary(32)=HASHBYTES('SHA2_256',N'community-verify');
    DECLARE @PublicPostPublishedAtUtc datetime2(7)=DATETIME2FROMPARTS(2,1,1,0,0,0,0,7);
    DECLARE @PublicReadAsOfUtc datetime2(7)=DATETIME2FROMPARTS(2,1,2,0,0,0,0,7);
    UPDATE dbo.community_posts SET published_at_utc=@PublicPostPublishedAtUtc WHERE community_post_id=@PostId;
    INSERT dbo.community_media(media_key,uploader_user_id,community_post_id,display_name,content_type,byte_length,sha256,original_blob_name,safe_blob_name,media_state,safe_byte_length,safe_sha256,scan_result,scan_time_utc,attached_at_utc)
    VALUES(@MediaKey,@UserIdA,@PostId,N'Community verification.pdf',N'application/pdf',16,@VerificationDigest,@BlobName,@BlobName,N'ready',16,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME());

    /* Build one active -> deleted -> active branch plus a deleted leaf. */
    DECLARE @RootIdempotency varchar(128)=CONCAT('community-root-',REPLACE(@Suffix,'-',''));
    DECLARE @MiddleIdempotency varchar(128)=CONCAT('community-middle-',REPLACE(@Suffix,'-',''));
    DECLARE @SelectedIdempotency varchar(128)=CONCAT('community-selected-',REPLACE(@Suffix,'-',''));
    DECLARE @DeletedLeafIdempotency varchar(128)=CONCAT('community-deleted-leaf-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyB,@PostKey=@PostKey,@Body=N'Community verification active root',@IdempotencyKey=@RootIdempotency,@AttachmentKeysJson=N'[]';
    DECLARE @RootContributionKey uniqueidentifier,@RootContributionId bigint;
    SELECT @RootContributionKey=contribution_key,@RootContributionId=community_contribution_id FROM dbo.community_contributions WHERE author_user_id=@UserIdB AND idempotency_key=@RootIdempotency;
    IF NOT EXISTS(SELECT 1 FROM dbo.community_contributions WHERE community_contribution_id=@RootContributionId AND contribution_kind=N'comment') THROW 52605,'Server-derived top-level comment was not created.',1;
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyB,@PostKey=@PostKey,@ParentContributionKey=@RootContributionKey,@Body=N'Community verification hidden middle',@IdempotencyKey=@MiddleIdempotency,@AttachmentKeysJson=N'[]';
    DECLARE @MiddleContributionKey uniqueidentifier,@MiddleContributionId bigint;
    SELECT @MiddleContributionKey=contribution_key,@MiddleContributionId=community_contribution_id FROM dbo.community_contributions WHERE author_user_id=@UserIdB AND idempotency_key=@MiddleIdempotency;
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyB,@PostKey=@PostKey,@ParentContributionKey=@MiddleContributionKey,@Body=N'Community verification selected leaf',@IdempotencyKey=@SelectedIdempotency,@AttachmentKeysJson=N'[]';
    DECLARE @SelectedContributionKey uniqueidentifier,@SelectedContributionId bigint;
    SELECT @SelectedContributionKey=contribution_key,@SelectedContributionId=community_contribution_id FROM dbo.community_contributions WHERE author_user_id=@UserIdB AND idempotency_key=@SelectedIdempotency;
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyB,@PostKey=@PostKey,@ParentContributionKey=@RootContributionKey,@Body=N'Community verification deleted leaf',@IdempotencyKey=@DeletedLeafIdempotency,@AttachmentKeysJson=N'[]';
    DECLARE @DeletedLeafContributionKey uniqueidentifier,@DeletedLeafContributionId bigint;
    SELECT @DeletedLeafContributionKey=contribution_key,@DeletedLeafContributionId=community_contribution_id FROM dbo.community_contributions WHERE author_user_id=@UserIdB AND idempotency_key=@DeletedLeafIdempotency;
    IF @RootContributionKey IS NULL OR @MiddleContributionKey IS NULL OR @SelectedContributionKey IS NULL OR @DeletedLeafContributionKey IS NULL
        THROW 52605,'Synthetic Community conversation was not created.',1;

    DECLARE @RootMediaKey uniqueidentifier=NEWID(),@HiddenMediaKey uniqueidentifier=NEWID(),@SelectedMediaKey uniqueidentifier=NEWID();
    DECLARE @RootBlobName nvarchar(220)=CONCAT(N'community/v1/aa/',REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N''),N'.pdf');
    DECLARE @HiddenBlobName nvarchar(220)=CONCAT(N'community/v1/aa/',REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N''),N'.pdf');
    DECLARE @SelectedBlobName nvarchar(220)=CONCAT(N'community/v1/aa/',REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N''),N'.pdf');
    INSERT dbo.community_media(media_key,uploader_user_id,community_contribution_id,display_name,content_type,byte_length,sha256,original_blob_name,safe_blob_name,media_state,safe_byte_length,safe_sha256,scan_result,scan_time_utc,attached_at_utc)
    VALUES
        (@RootMediaKey,@UserIdB,@RootContributionId,N'Community root verification.pdf',N'application/pdf',17,@VerificationDigest,@RootBlobName,@RootBlobName,N'ready',17,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME()),
        (@HiddenMediaKey,@UserIdB,@MiddleContributionId,N'Community hidden verification.pdf',N'application/pdf',18,@VerificationDigest,@HiddenBlobName,@HiddenBlobName,N'ready',18,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME()),
        (@SelectedMediaKey,@UserIdB,@SelectedContributionId,N'Community selected verification.pdf',N'application/pdf',19,@VerificationDigest,@SelectedBlobName,@SelectedBlobName,N'ready',19,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME());

    EXEC dbo.usp_DeletePublicCommunityContribution @UserKey=@UserKeyB,@ContributionKey=@MiddleContributionKey,@ExpectedRevision=1;
    EXEC dbo.usp_DeletePublicCommunityContribution @UserKey=@UserKeyB,@ContributionKey=@DeletedLeafContributionKey,@ExpectedRevision=1;
    IF NOT EXISTS(SELECT 1 FROM dbo.community_contributions WHERE community_contribution_id=@MiddleContributionId AND lifecycle_state=N'deleted')
       OR NOT EXISTS(SELECT 1 FROM dbo.community_contributions WHERE community_contribution_id=@DeletedLeafContributionId AND lifecycle_state=N'deleted')
        THROW 52606,'Synthetic Community tombstones were not created.',1;
    EXEC dbo.usp_SetPublicCommunityContributionSave @UserKey=@UserKeyA,@ContributionKey=@SelectedContributionKey,@Saved=1;

    DECLARE @WrongPostIdempotency varchar(128)=CONCAT('community-wrong-post-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyB,@IdempotencyKey=@WrongPostIdempotency,@Body=N'Community verification wrong binding post',@Intent=N'post',@ResponsePosture=N'open_feedback',@Audience=N'public',@AttachmentKeysJson=N'[]';
    DECLARE @WrongPostKey uniqueidentifier;
    SELECT @WrongPostKey=post_key FROM dbo.community_posts WHERE author_user_id=@UserIdB AND idempotency_key=@WrongPostIdempotency;
    IF @WrongPostKey IS NULL THROW 52607,'Synthetic wrong-binding post was not created.',1;

    DECLARE @ConversationAsOfUtc datetime2(7)=DATEADD(second,1,SYSUTCDATETIME());
    SELECT N'structural_conversation' AS verification_marker,
           CONVERT(nvarchar(36),@PostKey) AS expected_post_key,
           CONVERT(nvarchar(36),@RootContributionKey) AS expected_root_key,
           CONVERT(nvarchar(36),@MiddleContributionKey) AS expected_hidden_key,
           CONVERT(nvarchar(36),@SelectedContributionKey) AS expected_selected_key,
           CONVERT(nvarchar(36),@DeletedLeafContributionKey) AS expected_omitted_leaf_key,
           CONVERT(nvarchar(36),@MediaKey) AS expected_post_media_key,
           CONVERT(nvarchar(36),@RootMediaKey) AS expected_root_media_key,
           CONVERT(nvarchar(36),@HiddenMediaKey) AS expected_hidden_media_key,
           CONVERT(nvarchar(36),@SelectedMediaKey) AS expected_selected_media_key;
    EXEC dbo.usp_GetPublicCommunityPost @PostKey=@PostKey,@ViewerUserKey=@UserKeyA,@AsOfUtc=@ConversationAsOfUtc,@PageSize=20;
    SELECT N'structural_conversation_end' AS verification_marker;

    SELECT N'selected_contribution' AS verification_marker,
           CONVERT(nvarchar(36),@PostKey) AS expected_post_key,
           CONVERT(nvarchar(36),@RootContributionKey) AS expected_root_key,
           CONVERT(nvarchar(36),@MiddleContributionKey) AS expected_hidden_key,
           CONVERT(nvarchar(36),@SelectedContributionKey) AS expected_selected_key,
           CONVERT(nvarchar(36),@RootMediaKey) AS expected_root_media_key,
           CONVERT(nvarchar(36),@HiddenMediaKey) AS expected_hidden_media_key,
           CONVERT(nvarchar(36),@SelectedMediaKey) AS expected_selected_media_key;
    EXEC dbo.usp_GetPublicCommunityContribution @PostKey=@PostKey,@ContributionKey=@SelectedContributionKey,@ViewerUserKey=@UserKeyA;
    SELECT N'selected_contribution_end' AS verification_marker;

    SELECT N'selected_wrong_post' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityContribution @PostKey=@WrongPostKey,@ContributionKey=@SelectedContributionKey,@ViewerUserKey=@UserKeyA;
    SELECT N'selected_wrong_post_end' AS verification_marker;

    UPDATE dbo.app_users SET active=0 WHERE id=@UserIdB;
    SELECT N'selected_revoked_author' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityContribution @PostKey=@PostKey,@ContributionKey=@SelectedContributionKey,@ViewerUserKey=@UserKeyA;
    SELECT N'selected_revoked_author_end' AS verification_marker;
    UPDATE dbo.app_users SET active=1 WHERE id=@UserIdB;
    IF NOT EXISTS(SELECT 1 FROM dbo.app_users WHERE id=@UserIdB AND active=1 AND account_status=N'active')
        THROW 52608,'Synthetic contributor authorization was not restored.',1;

    UPDATE dbo.app_users SET active=0 WHERE id=@UserIdA;
    SELECT N'selected_revoked_post_author' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityContribution @PostKey=@PostKey,@ContributionKey=@SelectedContributionKey,@ViewerUserKey=@UserKeyA;
    SELECT N'selected_revoked_post_author_end' AS verification_marker;
    UPDATE dbo.app_users SET active=1 WHERE id=@UserIdA;
    IF NOT EXISTS(SELECT 1 FROM dbo.app_users WHERE id=@UserIdA AND active=1 AND account_status=N'active')
        THROW 52608,'Synthetic post-author authorization was not restored.',1;

    /* Put a child in the newest 20 while its older parent is candidate 21. */
    DECLARE @ClosureBaseUtc datetime2(7)=DATETIME2FROMPARTS(9998,1,1,0,0,0,0,7);
    DECLARE @ClosureParentId bigint,@ClosureParentKey uniqueidentifier;
    DECLARE @ClosureParentIdempotency varchar(128)=CONCAT('community-closure-parent-',REPLACE(@Suffix,'-',''));
    INSERT dbo.community_contributions(community_post_id,author_user_id,contribution_kind,body,depth,idempotency_key,idempotency_hash,created_at_utc,updated_at_utc)
    VALUES(@PostId,@UserIdB,N'comment',N'Community closure parent',0,@ClosureParentIdempotency,HASHBYTES('SHA2_256',@ClosureParentIdempotency),@ClosureBaseUtc,@ClosureBaseUtc);
    SET @ClosureParentId=SCOPE_IDENTITY();
    SELECT @ClosureParentKey=contribution_key FROM dbo.community_contributions WHERE community_contribution_id=@ClosureParentId;
    INSERT dbo.community_contribution_revisions(community_contribution_id,revision_number,body,changed_by_user_id,changed_at_utc)
    VALUES(@ClosureParentId,1,N'Community closure parent',@UserIdB,@ClosureBaseUtc);

    DECLARE @ClosureOrdinal int=1,@ClosureFillerId bigint,@ClosureFillerKey uniqueidentifier,@ClosureFillerUtc datetime2(7),@ClosureFillerIdempotency varchar(128),@ClosureBoundaryKey uniqueidentifier;
    WHILE @ClosureOrdinal<=19
    BEGIN
        SET @ClosureFillerUtc=DATEADD(second,@ClosureOrdinal,@ClosureBaseUtc);
        SET @ClosureFillerIdempotency=CONCAT('community-closure-filler-',REPLACE(@Suffix,'-',''),'-',CONVERT(varchar(2),@ClosureOrdinal));
        INSERT dbo.community_contributions(community_post_id,author_user_id,contribution_kind,body,depth,idempotency_key,idempotency_hash,created_at_utc,updated_at_utc)
        VALUES(@PostId,@UserIdB,N'comment',CONCAT(N'Community closure filler ',@ClosureOrdinal),0,@ClosureFillerIdempotency,HASHBYTES('SHA2_256',@ClosureFillerIdempotency),@ClosureFillerUtc,@ClosureFillerUtc);
        SET @ClosureFillerId=SCOPE_IDENTITY();
        SELECT @ClosureFillerKey=contribution_key FROM dbo.community_contributions WHERE community_contribution_id=@ClosureFillerId;
        INSERT dbo.community_contribution_revisions(community_contribution_id,revision_number,body,changed_by_user_id,changed_at_utc)
        VALUES(@ClosureFillerId,1,CONCAT(N'Community closure filler ',@ClosureOrdinal),@UserIdB,@ClosureFillerUtc);
        IF @ClosureOrdinal=1 SET @ClosureBoundaryKey=@ClosureFillerKey;
        SET @ClosureOrdinal=@ClosureOrdinal+1;
    END;

    DECLARE @ClosureChildId bigint,@ClosureChildKey uniqueidentifier,@ClosureChildUtc datetime2(7)=DATEADD(second,20,@ClosureBaseUtc);
    DECLARE @ClosureChildIdempotency varchar(128)=CONCAT('community-closure-child-',REPLACE(@Suffix,'-',''));
    INSERT dbo.community_contributions(community_post_id,author_user_id,parent_contribution_id,contribution_kind,body,depth,idempotency_key,idempotency_hash,created_at_utc,updated_at_utc)
    VALUES(@PostId,@UserIdB,@ClosureParentId,N'reply',N'Community closure child',1,@ClosureChildIdempotency,HASHBYTES('SHA2_256',@ClosureChildIdempotency),@ClosureChildUtc,@ClosureChildUtc);
    SET @ClosureChildId=SCOPE_IDENTITY();
    SELECT @ClosureChildKey=contribution_key FROM dbo.community_contributions WHERE community_contribution_id=@ClosureChildId;
    INSERT dbo.community_contribution_revisions(community_contribution_id,revision_number,body,changed_by_user_id,changed_at_utc)
    VALUES(@ClosureChildId,1,N'Community closure child',@UserIdB,@ClosureChildUtc);

    DECLARE @ClosureAsOfUtc datetime2(7)=DATEADD(second,21,@ClosureBaseUtc);
    SELECT N'conversation_page_closure' AS verification_marker,
           CONVERT(nvarchar(36),@PostKey) AS expected_post_key,
           CONVERT(nvarchar(36),@ClosureParentKey) AS expected_parent_key,
           CONVERT(nvarchar(36),@ClosureChildKey) AS expected_child_key,
           CONVERT(nvarchar(36),@ClosureBoundaryKey) AS expected_boundary_key;
    EXEC dbo.usp_GetPublicCommunityPost @PostKey=@PostKey,@ViewerUserKey=@UserKeyA,@AsOfUtc=@ClosureAsOfUtc,@PageSize=20;
    SELECT N'conversation_page_closure_end' AS verification_marker;

    /* Page all 22 newest shelf records through a post-bound keyset boundary. */
    DECLARE @ShelfBaseUtc datetime2(7)=DATETIME2FROMPARTS(9997,1,1,0,0,0,0,7);
    DECLARE @ShelfAsOfUtc datetime2(7)=DATETIME2FROMPARTS(9997,1,2,0,0,0,0,7);
    DECLARE @ShelfExpected TABLE(ordinal int NOT NULL PRIMARY KEY,contribution_key uniqueidentifier NOT NULL UNIQUE,created_at_utc datetime2(7) NOT NULL);
    DECLARE @ShelfOrdinal int=1,@ShelfContributionId bigint,@ShelfContributionKey uniqueidentifier,@ShelfCreatedAtUtc datetime2(7),@ShelfIdempotency varchar(128);
    WHILE @ShelfOrdinal<=22
    BEGIN
        SET @ShelfCreatedAtUtc=DATEADD(second,@ShelfOrdinal,@ShelfBaseUtc);
        SET @ShelfIdempotency=CONCAT('community-shelf-',REPLACE(@Suffix,'-',''),'-',CONVERT(varchar(2),@ShelfOrdinal));
        INSERT dbo.community_contributions(community_post_id,author_user_id,contribution_kind,body,depth,idempotency_key,idempotency_hash,created_at_utc,updated_at_utc)
        VALUES(@PostId,@UserIdA,N'comment',CONCAT(N'Community shelf page ',@ShelfOrdinal),0,@ShelfIdempotency,HASHBYTES('SHA2_256',@ShelfIdempotency),@ShelfCreatedAtUtc,@ShelfCreatedAtUtc);
        SET @ShelfContributionId=SCOPE_IDENTITY();
        SELECT @ShelfContributionKey=contribution_key FROM dbo.community_contributions WHERE community_contribution_id=@ShelfContributionId;
        INSERT dbo.community_contribution_revisions(community_contribution_id,revision_number,body,changed_by_user_id,changed_at_utc)
        VALUES(@ShelfContributionId,1,CONCAT(N'Community shelf page ',@ShelfOrdinal),@UserIdA,@ShelfCreatedAtUtc);
        INSERT @ShelfExpected(ordinal,contribution_key,created_at_utc) VALUES(@ShelfOrdinal,@ShelfContributionKey,@ShelfCreatedAtUtc);
        SET @ShelfOrdinal=@ShelfOrdinal+1;
    END;
    DECLARE @ShelfBoundaryCreatedAtUtc datetime2(7),@ShelfBoundaryContributionKey uniqueidentifier;
    SELECT @ShelfBoundaryCreatedAtUtc=created_at_utc,@ShelfBoundaryContributionKey=contribution_key FROM @ShelfExpected WHERE ordinal=3;

    SELECT N'shelf_page_one' AS verification_marker,
           CONVERT(nvarchar(36),@PostKey) AS expected_post_key,
           CONVERT(nvarchar(36),@ShelfBoundaryContributionKey) AS expected_boundary_key;
    EXEC dbo.usp_ListPublicCommunityShelf @PostKey=@PostKey,@AsOfUtc=@ShelfAsOfUtc,@PageSize=20,@ViewerUserKey=@UserKeyA;
    SELECT N'shelf_page_one_end' AS verification_marker;
    SELECT N'shelf_page_two' AS verification_marker,CONVERT(nvarchar(36),@PostKey) AS expected_post_key;
    EXEC dbo.usp_ListPublicCommunityShelf @PostKey=@PostKey,@AsOfUtc=@ShelfAsOfUtc,@BeforeCreatedAtUtc=@ShelfBoundaryCreatedAtUtc,@BeforeContributionKey=@ShelfBoundaryContributionKey,@PageSize=20,@ViewerUserKey=@UserKeyA;
    SELECT N'shelf_page_two_end' AS verification_marker;

    /* Revoke page one after capturing its boundary, then continue from it. */
    DECLARE @FeedTopIdempotency varchar(128)=CONCAT('community-feed-top-',REPLACE(@Suffix,'-',''));
    DECLARE @FeedNextIdempotency varchar(128)=CONCAT('community-feed-next-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@FeedTopIdempotency,@Body=N'Community verification Feed top',@Intent=N'post',@ResponsePosture=N'open_feedback',@Audience=N'public',@AttachmentKeysJson=N'[]';
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@FeedNextIdempotency,@Body=N'Community verification Feed next',@Intent=N'post',@ResponsePosture=N'open_feedback',@Audience=N'public',@AttachmentKeysJson=N'[]';
    DECLARE @FeedTopKey uniqueidentifier,@FeedNextKey uniqueidentifier,@FeedTopId bigint;
    SELECT @FeedTopKey=post_key,@FeedTopId=community_post_id FROM dbo.community_posts WHERE author_user_id=@UserIdA AND idempotency_key=@FeedTopIdempotency;
    SELECT @FeedNextKey=post_key FROM dbo.community_posts WHERE author_user_id=@UserIdA AND idempotency_key=@FeedNextIdempotency;
    DECLARE @FeedNextPublishedAtUtc datetime2(7)=DATETIME2FROMPARTS(1,1,1,0,0,0,0,7);
    DECLARE @FeedTopPublishedAtUtc datetime2(7)=DATEADD(second,1,@FeedNextPublishedAtUtc);
    DECLARE @FeedAsOfUtc datetime2(7)=DATEADD(second,1,@FeedTopPublishedAtUtc);
    UPDATE dbo.community_posts SET published_at_utc=@FeedTopPublishedAtUtc,updated_at_utc=@FeedTopPublishedAtUtc WHERE post_key=@FeedTopKey;
    UPDATE dbo.community_posts SET published_at_utc=@FeedNextPublishedAtUtc,updated_at_utc=@FeedNextPublishedAtUtc WHERE post_key=@FeedNextKey;

    SELECT N'feed_boundary_page_one' AS verification_marker,
           CONVERT(nvarchar(36),@FeedTopKey) AS expected_post_key,
           1 AS expected_selected_candidate_count,CAST(1 AS bit) AS expected_has_more;
    EXEC dbo.usp_ListPublicCommunityFeed @AsOfUtc=@FeedAsOfUtc,@PageLimit=1,@ViewerUserKey=@UserKeyA;
    SELECT N'feed_boundary_page_one_end' AS verification_marker;
    EXEC dbo.usp_DeletePublicCommunityPost @UserKey=@UserKeyA,@PostKey=@FeedTopKey,@ExpectedRevision=1;
    IF EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@FeedTopId AND publication_state=N'published')
        THROW 52609,'Synthetic Feed page-one revocation failed.',1;
    SELECT N'feed_boundary_page_two_after_revoke' AS verification_marker,
           CONVERT(nvarchar(36),@FeedNextKey) AS expected_post_key,
           CONVERT(nvarchar(36),@FeedTopKey) AS revoked_post_key,
           1 AS expected_selected_candidate_count,CAST(0 AS bit) AS expected_has_more;
    EXEC dbo.usp_ListPublicCommunityFeed @AsOfUtc=@FeedAsOfUtc,@AfterPublishedAtUtc=@FeedTopPublishedAtUtc,@AfterPostKey=@FeedTopKey,@PageLimit=1,@ViewerUserKey=@UserKeyA;
    SELECT N'feed_boundary_page_two_after_revoke_end' AS verification_marker;

    /* Exercise the contribution-delete cleanup selector against its exact media. */
    DECLARE @ContributionSelectorClaims TABLE(media_key uniqueidentifier,cleanup_claim_token uniqueidentifier,original_blob_name nvarchar(220),safe_blob_name nvarchar(220));
    INSERT @ContributionSelectorClaims(media_key,cleanup_claim_token,original_blob_name,safe_blob_name)
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanup @Take=4,@ContributionKey=@MiddleContributionKey;
    IF (SELECT COUNT(*) FROM @ContributionSelectorClaims)<>1
       OR NOT EXISTS(SELECT 1 FROM @ContributionSelectorClaims WHERE media_key=@HiddenMediaKey)
        THROW 52610,'Contribution-key cleanup selector did not isolate deleted-contribution media.',1;
    DECLARE @ContributionSelectorToken uniqueidentifier=(SELECT cleanup_claim_token FROM @ContributionSelectorClaims WHERE media_key=@HiddenMediaKey);
    DECLARE @ContributionSelectorCompletion TABLE(outcome nvarchar(30),media_key uniqueidentifier);
    INSERT @ContributionSelectorCompletion(outcome,media_key)
    EXEC dbo.usp_CompletePublicCommunityMediaCleanup @MediaKey=@HiddenMediaKey,@ClaimToken=@ContributionSelectorToken;
    IF NOT EXISTS(SELECT 1 FROM @ContributionSelectorCompletion WHERE outcome=N'completed' AND media_key=@HiddenMediaKey)
        THROW 52610,'Contribution-key cleanup selector claim did not complete.',1;
    SELECT N'cleanup_contribution_selector' AS verification_marker,
           CONVERT(nvarchar(36),@MiddleContributionKey) AS expected_contribution_key,
           CONVERT(nvarchar(36),@HiddenMediaKey) AS expected_media_key;
    SELECT CONVERT(nvarchar(36),media_key) AS media_key,CONVERT(nvarchar(36),cleanup_claim_token) AS cleanup_claim_token FROM @ContributionSelectorClaims;

    /* Exercise both direct and contribution-owned branches of the post selector. */
    DECLARE @CleanupPostIdempotency varchar(128)=CONCAT('community-cleanup-post-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@CleanupPostIdempotency,@Body=N'Community post cleanup selector verification',@Intent=N'post',@ResponsePosture=N'open_feedback',@Audience=N'public',@AttachmentKeysJson=N'[]';
    DECLARE @CleanupPostKey uniqueidentifier,@CleanupPostId bigint;
    SELECT @CleanupPostKey=post_key,@CleanupPostId=community_post_id FROM dbo.community_posts WHERE author_user_id=@UserIdA AND idempotency_key=@CleanupPostIdempotency;
    DECLARE @CleanupContributionIdempotency varchar(128)=CONCAT('community-cleanup-contribution-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_AddPublicCommunityContribution @UserKey=@UserKeyA,@PostKey=@CleanupPostKey,@Body=N'Community post selector contribution',@IdempotencyKey=@CleanupContributionIdempotency,@AttachmentKeysJson=N'[]';
    DECLARE @CleanupContributionKey uniqueidentifier,@CleanupContributionId bigint;
    SELECT @CleanupContributionKey=contribution_key,@CleanupContributionId=community_contribution_id FROM dbo.community_contributions WHERE author_user_id=@UserIdA AND idempotency_key=@CleanupContributionIdempotency;
    IF @CleanupPostKey IS NULL OR @CleanupContributionKey IS NULL
        THROW 52611,'Synthetic post cleanup sources were not created.',1;
    DECLARE @PostSelectorMediaKey uniqueidentifier=NEWID(),@PostSelectorContributionMediaKey uniqueidentifier=NEWID();
    DECLARE @PostSelectorBlobName nvarchar(220)=CONCAT(N'community/v1/aa/',REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N''),N'.pdf');
    DECLARE @PostSelectorContributionBlobName nvarchar(220)=CONCAT(N'community/v1/aa/',REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N''),N'.pdf');
    INSERT dbo.community_media(media_key,uploader_user_id,community_post_id,display_name,content_type,byte_length,sha256,original_blob_name,safe_blob_name,media_state,safe_byte_length,safe_sha256,scan_result,scan_time_utc,attached_at_utc)
    VALUES(@PostSelectorMediaKey,@UserIdA,@CleanupPostId,N'Community post selector verification.pdf',N'application/pdf',20,@VerificationDigest,@PostSelectorBlobName,@PostSelectorBlobName,N'ready',20,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME());
    INSERT dbo.community_media(media_key,uploader_user_id,community_contribution_id,display_name,content_type,byte_length,sha256,original_blob_name,safe_blob_name,media_state,safe_byte_length,safe_sha256,scan_result,scan_time_utc,attached_at_utc)
    VALUES(@PostSelectorContributionMediaKey,@UserIdA,@CleanupContributionId,N'Community post contribution selector verification.pdf',N'application/pdf',21,@VerificationDigest,@PostSelectorContributionBlobName,@PostSelectorContributionBlobName,N'ready',21,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME());
    EXEC dbo.usp_DeletePublicCommunityPost @UserKey=@UserKeyA,@PostKey=@CleanupPostKey,@ExpectedRevision=1;
    IF NOT EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@CleanupPostId AND publication_state=N'deleted')
        THROW 52611,'Synthetic post cleanup source was not deleted.',1;
    DECLARE @PostDirectSelectorClaims TABLE(media_key uniqueidentifier,cleanup_claim_token uniqueidentifier,original_blob_name nvarchar(220),safe_blob_name nvarchar(220));
    INSERT @PostDirectSelectorClaims(media_key,cleanup_claim_token,original_blob_name,safe_blob_name)
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanup @Take=1,@PostKey=@CleanupPostKey;
    IF (SELECT COUNT(*) FROM @PostDirectSelectorClaims)<>1
       OR NOT EXISTS(SELECT 1 FROM @PostDirectSelectorClaims WHERE media_key=@PostSelectorMediaKey)
        THROW 52611,'Post-key cleanup selector did not isolate direct post media first.',1;
    DECLARE @PostDirectSelectorToken uniqueidentifier=(SELECT cleanup_claim_token FROM @PostDirectSelectorClaims WHERE media_key=@PostSelectorMediaKey);
    DECLARE @PostDirectSelectorCompletion TABLE(outcome nvarchar(30),media_key uniqueidentifier);
    INSERT @PostDirectSelectorCompletion(outcome,media_key)
    EXEC dbo.usp_CompletePublicCommunityMediaCleanup @MediaKey=@PostSelectorMediaKey,@ClaimToken=@PostDirectSelectorToken;
    IF NOT EXISTS(SELECT 1 FROM @PostDirectSelectorCompletion WHERE outcome=N'completed' AND media_key=@PostSelectorMediaKey)
        THROW 52611,'Direct post-key cleanup selector claim did not complete.',1;
    DECLARE @PostSelectorClaims TABLE(media_key uniqueidentifier,cleanup_claim_token uniqueidentifier,original_blob_name nvarchar(220),safe_blob_name nvarchar(220));
    INSERT @PostSelectorClaims(media_key,cleanup_claim_token,original_blob_name,safe_blob_name)
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanup @Take=20,@PostKey=@CleanupPostKey;
    IF (SELECT COUNT(*) FROM @PostSelectorClaims)<>1
       OR NOT EXISTS(SELECT 1 FROM @PostSelectorClaims WHERE media_key=@PostSelectorContributionMediaKey)
        THROW 52611,'Post-key cleanup selector did not isolate contribution-owned media.',1;
    DECLARE @PostSelectorToken uniqueidentifier=(SELECT cleanup_claim_token FROM @PostSelectorClaims WHERE media_key=@PostSelectorContributionMediaKey);
    DECLARE @PostSelectorCompletion TABLE(outcome nvarchar(30),media_key uniqueidentifier);
    INSERT @PostSelectorCompletion(outcome,media_key)
    EXEC dbo.usp_CompletePublicCommunityMediaCleanup @MediaKey=@PostSelectorContributionMediaKey,@ClaimToken=@PostSelectorToken;
    IF NOT EXISTS(SELECT 1 FROM @PostSelectorCompletion WHERE outcome=N'completed' AND media_key=@PostSelectorContributionMediaKey)
        THROW 52611,'Contribution-owned post-key cleanup selector claim did not complete.',1;
    SELECT N'cleanup_post_selector' AS verification_marker,
           CONVERT(nvarchar(36),@CleanupPostKey) AS expected_post_key,
           CONVERT(nvarchar(36),@PostSelectorContributionMediaKey) AS expected_media_key;
    SELECT CONVERT(nvarchar(36),media_key) AS media_key,CONVERT(nvarchar(36),cleanup_claim_token) AS cleanup_claim_token FROM @PostSelectorClaims;

    /* A still-published source must never become a cleanup candidate. */
    DECLARE @ActiveCleanupPostIdempotency varchar(128)=CONCAT('community-active-cleanup-post-',REPLACE(@Suffix,'-',''));
    EXEC dbo.usp_PublishPublicCommunityPost @UserKey=@UserKeyA,@IdempotencyKey=@ActiveCleanupPostIdempotency,@Body=N'Community active cleanup negative verification',@Intent=N'post',@ResponsePosture=N'open_feedback',@Audience=N'public',@AttachmentKeysJson=N'[]';
    DECLARE @ActiveCleanupPostKey uniqueidentifier,@ActiveCleanupPostId bigint;
    SELECT @ActiveCleanupPostKey=post_key,@ActiveCleanupPostId=community_post_id FROM dbo.community_posts WHERE author_user_id=@UserIdA AND idempotency_key=@ActiveCleanupPostIdempotency;
    DECLARE @ActiveCleanupMediaKey uniqueidentifier=NEWID(),@ActiveCleanupBlobName nvarchar(220)=CONCAT(N'community/v1/aa/',REPLACE(CONVERT(nvarchar(36),NEWID()),N'-',N''),N'.pdf');
    INSERT dbo.community_media(media_key,uploader_user_id,community_post_id,display_name,content_type,byte_length,sha256,original_blob_name,safe_blob_name,media_state,safe_byte_length,safe_sha256,scan_result,scan_time_utc,attached_at_utc)
    VALUES(@ActiveCleanupMediaKey,@UserIdA,@ActiveCleanupPostId,N'Community active cleanup negative verification.pdf',N'application/pdf',22,@VerificationDigest,@ActiveCleanupBlobName,@ActiveCleanupBlobName,N'ready',22,@VerificationDigest,N'clean',SYSUTCDATETIME(),SYSUTCDATETIME());
    DECLARE @ActivePostSelectorClaims TABLE(media_key uniqueidentifier,cleanup_claim_token uniqueidentifier,original_blob_name nvarchar(220),safe_blob_name nvarchar(220));
    INSERT @ActivePostSelectorClaims(media_key,cleanup_claim_token,original_blob_name,safe_blob_name)
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanup @Take=20,@PostKey=@ActiveCleanupPostKey;
    IF EXISTS(SELECT 1 FROM @ActivePostSelectorClaims)
        THROW 52611,'Post-key cleanup selector claimed media from an active source.',1;

    SELECT N'public_feed_before_delete' AS verification_marker,CONVERT(nvarchar(36),@PostKey) AS expected_post_key,CONVERT(nvarchar(36),@MediaKey) AS expected_media_key;
    EXEC dbo.usp_ListPublicCommunityFeed @AsOfUtc=@PublicReadAsOfUtc,@PageLimit=1;
    SELECT N'public_detail_before_delete' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityPost @PostKey=@PostKey,@ViewerUserKey=@UserKeyA;
    SELECT N'public_search_before_delete' AS verification_marker;
    EXEC dbo.usp_SearchPublicCommunity @Query=@SearchQuery,@ResultLimit=20;
    SELECT N'public_media_before_delete' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityMedia @MediaKey=@MediaKey;

    /* Soft deletion revokes public eligibility and clears interaction references. */
    EXEC dbo.usp_DeletePublicCommunityPost @UserKey=@UserKeyA,@PostKey=@PostKey,@ExpectedRevision=2;
    IF EXISTS(SELECT 1 FROM dbo.community_posts WHERE community_post_id=@PostId AND publication_state=N'published') OR EXISTS(SELECT 1 FROM dbo.community_saves WHERE community_post_id=@PostId) OR EXISTS(SELECT 1 FROM dbo.community_responses WHERE community_post_id=@PostId) THROW 52600,'Public revocation failed.',1;
    IF NOT EXISTS(SELECT 1 FROM dbo.community_audit_events WHERE entity_key=@PostKey AND action_type=N'deleted') OR NOT EXISTS(SELECT 1 FROM dbo.community_outbox WHERE entity_key=@PostKey AND event_type=N'community.post.deleted') THROW 52601,'Content-free audit/outbox evidence is missing.',1;

    SELECT N'public_feed_after_delete' AS verification_marker;
    EXEC dbo.usp_ListPublicCommunityFeed @AsOfUtc=@PublicReadAsOfUtc,@PageLimit=1;
    SELECT N'public_detail_after_delete' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityPost @PostKey=@PostKey,@ViewerUserKey=@UserKeyA;
    SELECT N'public_detail_after_delete_end' AS verification_marker;
    SELECT N'public_search_after_delete' AS verification_marker;
    EXEC dbo.usp_SearchPublicCommunity @Query=@SearchQuery,@ResultLimit=20;
    SELECT N'public_media_after_delete' AS verification_marker;
    EXEC dbo.usp_GetPublicCommunityMedia @MediaKey=@MediaKey;
    SELECT N'public_media_after_delete_end' AS verification_marker;

    DECLARE @CleanupClaims TABLE(media_key uniqueidentifier,cleanup_claim_token uniqueidentifier,original_blob_name nvarchar(220),safe_blob_name nvarchar(220));
    INSERT @CleanupClaims(media_key,cleanup_claim_token,original_blob_name,safe_blob_name)
    EXEC dbo.usp_ClaimPublicCommunityMediaCleanup @Take=1,@MediaKey=@MediaKey;
    IF NOT EXISTS(SELECT 1 FROM @CleanupClaims WHERE media_key=@MediaKey) THROW 52603,'Deleted attachment was not claimable for physical cleanup.',1;
    SELECT N'cleanup_claim' AS verification_marker;
    SELECT CONVERT(nvarchar(36),media_key) AS media_key,CONVERT(nvarchar(36),cleanup_claim_token) AS cleanup_claim_token FROM @CleanupClaims;
    DECLARE @CleanupClaimToken uniqueidentifier=(SELECT cleanup_claim_token FROM @CleanupClaims WHERE media_key=@MediaKey);
    SELECT N'cleanup_wrong_token' AS verification_marker;
    EXEC dbo.usp_CompletePublicCommunityMediaCleanup @MediaKey=@MediaKey,@ClaimToken='00000000-0000-0000-0000-000000000001';
    IF @@TRANCOUNT<>1 OR NOT EXISTS(SELECT 1 FROM dbo.community_media WHERE media_key=@MediaKey AND cleanup_claim_token=@CleanupClaimToken AND blob_cleanup_completed_at_utc IS NULL) THROW 52604,'Wrong cleanup lease token changed attachment state.',1;
    SELECT N'cleanup_complete' AS verification_marker;
    EXEC dbo.usp_CompletePublicCommunityMediaCleanup @MediaKey=@MediaKey,@ClaimToken=@CleanupClaimToken;
    IF NOT EXISTS(SELECT 1 FROM dbo.community_media WHERE media_key=@MediaKey AND media_state=N'removed' AND blob_cleanup_completed_at_utc IS NOT NULL AND cleanup_claim_token IS NULL) THROW 52604,'Deleted attachment cleanup did not complete.',1;
    SELECT N'cleanup_second_complete' AS verification_marker;
    EXEC dbo.usp_CompletePublicCommunityMediaCleanup @MediaKey=@MediaKey,@ClaimToken=@CleanupClaimToken;
    IF @@TRANCOUNT<>1 THROW 52604,'Repeated cleanup completion changed the caller transaction.',1;

    IF EXISTS(SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID(N'dbo.community_audit_events') AND name IN(N'body',N'query',N'email')) OR EXISTS(SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID(N'dbo.community_outbox') AND name IN(N'body',N'query',N'email',N'payload')) THROW 52602,'Audit or outbox contains content fields.',1;

    ROLLBACK TRANSACTION;
    SELECT CAST(1 AS bit) AS verified;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
