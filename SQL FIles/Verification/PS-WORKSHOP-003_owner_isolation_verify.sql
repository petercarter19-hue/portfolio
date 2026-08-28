/* PS-WORKSHOP-003 disposable-database verification.

   Proves the exact dependency and definition are present; two-owner,
   foreign-item, unknown-item, and forged-owner neutrality; exact stored
   approved/original wording bytes; the deterministic newest-50 contents
   over 55 retained versions; and truthful total and truncation metadata.
   Delivery order is pinned by the procedure definition's outward ORDER BY,
   not falsely inferred from INSERT EXEC insertion order into a table
   variable (which SQL Server does not guarantee). All synthetic state is
   rolled back.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-002'
    )
        THROW 53440, 'PS-WORKSHOP-002 prerequisite is not registered.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-003'
    )
        THROW 53441, 'PS-WORKSHOP-003 is not registered.', 1;
    IF OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P') IS NULL
        THROW 53442, 'The knowledge wording-history procedure is missing.', 1;

    DECLARE @Definition nvarchar(max) = OBJECT_DEFINITION
    (
        OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P')
    );
    IF @Definition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @Definition LIKE N'%@OwnerProfileId%'
       OR @Definition NOT LIKE N'%owner_profile_id = @ProfileId%'
       OR @Definition NOT LIKE N'%item.visibility = N''private''%'
       OR @Definition NOT LIKE N'%TOP (50)%'
       OR @Definition NOT LIKE N'%ORDER BY snapshot.version_number DESC%'
       OR @Definition NOT LIKE N'%version_record.approved_wording%'
       OR @Definition NOT LIKE N'%version_record.original_member_wording%'
       OR @Definition NOT LIKE N'%COUNT_BIG(*) OVER ()%'
       OR @Definition NOT LIKE N'%INSERT @VersionSnapshot%'
        THROW 53443, 'The knowledge wording-history definition is not bounded and owner-scoped.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:workshop-provenance-visibility-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'workshop-history-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'workshop-history-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-provenance-visibility-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Workshop history verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-provenance-visibility-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Workshop history verification owner B';

    DECLARE @UserKeyA nvarchar(300), @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint, @ProfileIdB bigint;
    DECLARE @UserIdA int, @UserIdB int;
    SELECT @UserKeyA = app_user.user_key,
           @ProfileIdA = profile.profile_id,
           @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-provenance-visibility-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;
    SELECT @UserKeyB = app_user.user_key,
           @ProfileIdB = profile.profile_id,
           @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-provenance-visibility-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserIdA IS NULL OR @UserIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 53444, 'The two synthetic owners were not provisioned independently.', 1;

    DECLARE @ItemKeyA uniqueidentifier = NEWID();
    DECLARE @ItemKeyB uniqueidentifier = NEWID();
    DECLARE @UnknownItemKey uniqueidentifier = NEWID();
    DECLARE @ItemIdA bigint, @ItemIdB bigint;

    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@ItemKeyA, @ProfileIdA, N'unfinished', N'work', 55);
    SET @ItemIdA = SCOPE_IDENTITY();

    DECLARE @ApprovedCanary nvarchar(max) =
        N'  approved <script>alert("approved")</script> & Ω  ';
    DECLARE @OriginalCanary nvarchar(max) =
        N'  source <img src=x onerror=alert("source")> & 漢字  ';
    DECLARE @Version int = 1;
    WHILE @Version <= 55
    BEGIN
        INSERT dbo.knowledge_item_versions
            (knowledge_item_id, owner_profile_id, version_number, title,
             approved_wording, original_member_wording, body_format,
             authored_via, saved_by_user_id, saved_at_utc)
        VALUES
        (
            @ItemIdA,
            @ProfileIdA,
            @Version,
            CONCAT(N'Owner A version ', @Version),
            CASE WHEN @Version = 55 THEN @ApprovedCanary
                 ELSE CONCAT(N'Owner A approved version ', @Version) END,
            CASE WHEN @Version = 55 THEN @OriginalCanary
                 ELSE CONCAT(N'Owner A source version ', @Version) END,
            N'plain',
            CASE WHEN @Version = 55 THEN N'ai_assisted_approved' ELSE N'typed' END,
            @UserIdA,
            DATEADD(MINUTE, @Version, CONVERT(datetime2(7), '2026-01-01T00:00:00'))
        );
        SET @Version += 1;
    END;

    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@ItemKeyB, @ProfileIdB, N'unfinished', N'personal', 1);
    SET @ItemIdB = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, body_format,
         authored_via, saved_by_user_id, saved_at_utc)
    VALUES
        (@ItemIdB, @ProfileIdB, 1, N'Owner B private version',
         N'OWNER B APPROVED SECRET', N'OWNER B SOURCE SECRET', N'plain',
         N'typed', @UserIdB, '2026-02-01T00:00:00');

    DECLARE @Versions TABLE
    (
        version_number int NOT NULL,
        approved_wording nvarchar(max) NOT NULL,
        original_member_wording nvarchar(max) NOT NULL,
        saved_at_utc datetime2(7) NOT NULL
    );
    DECLARE @Metadata TABLE
    (
        total_count bigint NOT NULL,
        is_truncated bit NOT NULL
    );

    INSERT @Versions
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 1,
        @IncludeMetadata = 0;

    IF (SELECT COUNT(*) FROM @Versions) <> 50
        THROW 53445, 'The 55-version item did not return exactly the newest 50 versions.', 1;
    IF (SELECT MAX(version_number) FROM @Versions) <> 55
       OR (SELECT MIN(version_number) FROM @Versions) <> 6
       OR (SELECT COUNT(DISTINCT version_number) FROM @Versions) <> 50
       OR EXISTS
       (
           SELECT 1 FROM @Versions
           WHERE version_number NOT BETWEEN 6 AND 55
       )
        THROW 53446, 'The bounded version window does not contain exactly the newest 50 versions.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM @Versions
        WHERE version_number = 55
          AND approved_wording = @ApprovedCanary
          AND original_member_wording = @OriginalCanary
          AND DATALENGTH(approved_wording) = DATALENGTH(@ApprovedCanary)
          AND DATALENGTH(original_member_wording) = DATALENGTH(@OriginalCanary)
          AND HASHBYTES('SHA2_256', CONVERT(varbinary(max), approved_wording)) =
              HASHBYTES('SHA2_256', CONVERT(varbinary(max), @ApprovedCanary))
          AND HASHBYTES('SHA2_256', CONVERT(varbinary(max), original_member_wording)) =
              HASHBYTES('SHA2_256', CONVERT(varbinary(max), @OriginalCanary))
          AND saved_at_utc = CONVERT(datetime2(7), '2026-01-01T00:55:00')
    )
        THROW 53447, 'Exact approved/source wording bytes or timestamp were not preserved.', 1;
    IF EXISTS
    (
        SELECT 1 FROM @Versions
        WHERE approved_wording LIKE N'%OWNER B%'
           OR original_member_wording LIKE N'%OWNER B%'
    )
        THROW 53448, 'Owner B wording entered owner A history.', 1;

    INSERT @Metadata
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 0,
        @IncludeMetadata = 1;
    IF (SELECT COUNT(*) FROM @Metadata) <> 1
       OR NOT EXISTS
       (
           SELECT 1 FROM @Metadata
           WHERE total_count = 55 AND is_truncated = 1
       )
        THROW 53449, 'The 55-version total/truncation metadata is not truthful.', 1;

    DELETE @Versions;
    DELETE @Metadata;
    INSERT @Versions
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyB,
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 1,
        @IncludeMetadata = 0;
    INSERT @Metadata
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyB,
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 0,
        @IncludeMetadata = 1;
    IF EXISTS (SELECT 1 FROM @Versions)
       OR NOT EXISTS (SELECT 1 FROM @Metadata WHERE total_count = 0 AND is_truncated = 0)
        THROW 53450, 'A foreign owner did not receive the neutral empty result.', 1;

    DELETE @Versions;
    DELETE @Metadata;
    INSERT @Versions
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyB,
        @IncludeVersions = 1,
        @IncludeMetadata = 0;
    INSERT @Metadata
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyB,
        @IncludeVersions = 0,
        @IncludeMetadata = 1;
    IF EXISTS (SELECT 1 FROM @Versions)
       OR NOT EXISTS (SELECT 1 FROM @Metadata WHERE total_count = 0 AND is_truncated = 0)
        THROW 53451, 'A foreign item key did not receive the neutral empty result.', 1;

    DELETE @Versions;
    DELETE @Metadata;
    INSERT @Versions
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = N'forged-workshop-history-owner',
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 1,
        @IncludeMetadata = 0;
    INSERT @Metadata
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = N'forged-workshop-history-owner',
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 0,
        @IncludeMetadata = 1;
    IF EXISTS (SELECT 1 FROM @Versions)
       OR NOT EXISTS (SELECT 1 FROM @Metadata WHERE total_count = 0 AND is_truncated = 0)
        THROW 53452, 'A forged owner key did not receive the neutral empty result.', 1;

    DELETE @Versions;
    DELETE @Metadata;
    INSERT @Versions
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @UnknownItemKey,
        @IncludeVersions = 1,
        @IncludeMetadata = 0;
    INSERT @Metadata
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @UnknownItemKey,
        @IncludeVersions = 0,
        @IncludeMetadata = 1;
    IF EXISTS (SELECT 1 FROM @Versions)
       OR NOT EXISTS (SELECT 1 FROM @Metadata WHERE total_count = 0 AND is_truncated = 0)
        THROW 53453, 'An unknown item key did not receive the neutral empty result.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-WORKSHOP-003 owner-scoped exact wording history: dependency and protected definition present; one materialized source statement binds newest-50 contents to true total/truncation metadata; approved/source byte canaries and timestamp preserved; two-owner, foreign, forged, and unknown requests remain neutral; synthetic state rolled back.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
