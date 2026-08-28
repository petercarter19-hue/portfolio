/* PS-WORKSHOP-004 disposable-database verification.

   Proves the dependency and protected definitions; unchanged procedure
   signature/result contract; exact owner/current-version predicates and
   locks; two successive edits retaining one byte-distinct stored source;
   prior-version stability; typed provenance; atomic parent/version/audit
   advancement; Workshop F history contents/count/order contract; neutral
   stale, archived, foreign, forged, and unknown behavior; and the
   transactionally failing missing-current-version invariant. All synthetic
   state is rolled back.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-003'
    )
        THROW 53540, 'PS-WORKSHOP-003 prerequisite is not registered.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-004'
    )
        THROW 53541, 'PS-WORKSHOP-004 is not registered.', 1;
    IF OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P') IS NULL
       OR OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P') IS NULL
        THROW 53542, 'The Workshop edit or history procedure is missing.', 1;

    DECLARE @UpdateObjectId int = OBJECT_ID(N'dbo.usp_UpdateKnowledgeItemForOwner', N'P');
    DECLARE @UpdateDefinition nvarchar(max) = OBJECT_DEFINITION(@UpdateObjectId);
    IF NOT EXISTS
    (
        SELECT 1
        FROM sys.extended_properties AS property
        WHERE property.class = 1
          AND property.major_id = @UpdateObjectId
          AND property.minor_id = 0
          AND property.name = N'PS_WORKSHOP_004_DEFINITION_HASH'
          AND CONVERT(nvarchar(64), property.value) = CONVERT
          (
              nvarchar(64), HASHBYTES('SHA2_256', @UpdateDefinition), 2
          )
    )
        THROW 53543, 'The Workshop edit procedure fingerprint is absent or drifted.', 1;

    DECLARE @HistoryObjectId int = OBJECT_ID(N'dbo.usp_ListKnowledgeItemVersionsForOwner', N'P');
    IF NOT EXISTS
    (
        SELECT 1
        FROM sys.extended_properties AS property
        WHERE property.class = 1
          AND property.major_id = @HistoryObjectId
          AND property.minor_id = 0
          AND property.name = N'PS_WORKSHOP_003_DEFINITION_HASH'
          AND CONVERT(nvarchar(64), property.value) = CONVERT
          (
              nvarchar(64), HASHBYTES('SHA2_256', OBJECT_DEFINITION(@HistoryObjectId)), 2
          )
    )
        THROW 53544, 'The Workshop F history procedure fingerprint is absent or drifted.', 1;

    IF @UpdateDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @UpdateDefinition NOT LIKE N'%@KnowledgeItemKey uniqueidentifier%'
       OR @UpdateDefinition NOT LIKE N'%@ExpectedRowVersion binary(8)%'
       OR @UpdateDefinition NOT LIKE N'%@ApprovedWording nvarchar(max)%'
       OR @UpdateDefinition NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
       OR @UpdateDefinition NOT LIKE N'%item.owner_profile_id = @ProfileId%'
       OR @UpdateDefinition NOT LIKE N'%item.visibility = N''private''%'
       OR @UpdateDefinition NOT LIKE N'%item.item_status <> N''archived''%'
       OR @UpdateDefinition NOT LIKE N'%item.row_version = @ExpectedRowVersion%'
       OR @UpdateDefinition NOT LIKE N'%version_record.knowledge_item_id = @KnowledgeItemId%'
       OR @UpdateDefinition NOT LIKE N'%version_record.owner_profile_id = @ProfileId%'
       OR @UpdateDefinition NOT LIKE N'%version_record.version_number = @CurrentVersionNumber%'
       OR @UpdateDefinition NOT LIKE N'%@ApprovedWording, @OriginalMemberWording%'
       OR @UpdateDefinition NOT LIKE N'%N''typed'', @UserId%'
       OR @UpdateDefinition NOT LIKE N'%IF @@ROWCOUNT <> 1%'
        THROW 53545, 'The Workshop edit definition lost its signature, owner/CAS fence, or stored-source contract.', 1;
    IF (SELECT COUNT(*) FROM sys.parameters WHERE object_id = @UpdateObjectId) <> 8
       OR EXISTS
       (
           SELECT 1 FROM sys.parameters
           WHERE object_id = @UpdateObjectId
             AND name IN (N'@OriginalWording', N'@OriginalMemberWording')
       )
        THROW 53564, 'The Workshop edit procedure exposes an original-wording input parameter.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:workshop-edit-provenance-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'workshop-edit-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'workshop-edit-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-edit-provenance-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Workshop edit verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-edit-provenance-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Workshop edit verification owner B';

    DECLARE @UserKeyA nvarchar(300), @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint, @ProfileIdB bigint;
    DECLARE @UserIdA int, @UserIdB int;
    SELECT @UserKeyA = app_user.user_key,
           @ProfileIdA = profile.profile_id,
           @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-edit-provenance-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;
    SELECT @UserKeyB = app_user.user_key,
           @ProfileIdB = profile.profile_id,
           @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-edit-provenance-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserIdA IS NULL OR @UserIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 53546, 'The two synthetic owners were not provisioned independently.', 1;

    DECLARE @ItemKeyA uniqueidentifier = NEWID();
    DECLARE @ItemKeyB uniqueidentifier = NEWID();
    DECLARE @ArchivedItemKey uniqueidentifier = NEWID();
    DECLARE @UnknownItemKey uniqueidentifier = NEWID();
    DECLARE @ItemIdA bigint, @ItemIdB bigint, @ArchivedItemId bigint;
    DECLARE @SourceCanary nvarchar(max) =
        N'  SOURCE <img src=x onerror=alert("source")> & Ω 漢字  ';
    DECLARE @ApprovedV1 nvarchar(max) =
        N'Approved v1 is deliberately byte-distinct from the source.';
    DECLARE @ApprovedV2 nvarchar(max) =
        N'Approved v2 keeps the exact stored source while changing this text.';
    DECLARE @ApprovedV3 nvarchar(max) =
        N'Approved v3 changes again and still keeps the first stored source.';

    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@ItemKeyA, @ProfileIdA, N'unfinished', N'work', 1);
    SET @ItemIdA = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, body_format,
         authored_via, saved_by_user_id, saved_at_utc)
    VALUES
        (@ItemIdA, @ProfileIdA, 1, N'Owner A version one',
         @ApprovedV1, @SourceCanary, N'plain', N'ai_assisted_approved',
         @UserIdA, '2026-03-01T00:00:00');

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
         N'typed', @UserIdB, '2026-03-02T00:00:00');

    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number, archived_at_utc, archived_by_user_id)
    VALUES
        (@ArchivedItemKey, @ProfileIdA, N'archived', N'personal', 1,
         '2026-03-03T00:00:00', @UserIdA);
    SET @ArchivedItemId = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, body_format,
         authored_via, saved_by_user_id, saved_at_utc)
    VALUES
        (@ArchivedItemId, @ProfileIdA, 1, N'Archived owner A version',
         N'ARCHIVED APPROVED', N'ARCHIVED SOURCE', N'plain', N'typed',
         @UserIdA, '2026-03-03T00:00:00');

    DECLARE @RowVersion1 binary(8), @RowVersion2 binary(8), @RowVersion3 binary(8);
    DECLARE @ArchivedRowVersion binary(8);
    SELECT @RowVersion1 = CONVERT(binary(8), row_version)
    FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdA;
    SELECT @ArchivedRowVersion = CONVERT(binary(8), row_version)
    FROM dbo.knowledge_items WHERE knowledge_item_id = @ArchivedItemId;

    DECLARE @V1ApprovedHash varbinary(32) = HASHBYTES
        ('SHA2_256', CONVERT(varbinary(max), @ApprovedV1));
    DECLARE @V1SourceHash varbinary(32) = HASHBYTES
        ('SHA2_256', CONVERT(varbinary(max), @SourceCanary));

    /* Success calls are deliberately bare EXEC: the procedure itself uses
       INSERT EXEC for its audit call, so capturing a successful mutation
       with another INSERT EXEC would be the forbidden nested form. */
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA,
        @ExpectedRowVersion = @RowVersion1,
        @Title = N'Owner A version two',
        @ApprovedWording = @ApprovedV2,
        @BodyFormat = N'plain',
        @Classification = N'both',
        @Confirm = 0;

    SELECT @RowVersion2 = CONVERT(binary(8), row_version)
    FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdA;
    IF @RowVersion2 IS NULL OR @RowVersion2 = @RowVersion1
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.knowledge_items
           WHERE knowledge_item_id = @ItemIdA
             AND owner_profile_id = @ProfileIdA
             AND current_version_number = 2
             AND item_status = N'unfinished'
             AND classification = N'both'
       )
        THROW 53547, 'The first edit did not advance exactly the owned parent.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @ItemIdA
          AND owner_profile_id = @ProfileIdA
          AND version_number = 2
          AND approved_wording = @ApprovedV2
          AND original_member_wording = @SourceCanary
          AND authored_via = N'typed'
          AND DATALENGTH(original_member_wording) = DATALENGTH(@SourceCanary)
          AND HASHBYTES('SHA2_256', CONVERT(varbinary(max), original_member_wording)) = @V1SourceHash
    )
        THROW 53548, 'Version 2 did not keep the exact stored source as typed edit provenance.', 1;

    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA,
        @ExpectedRowVersion = @RowVersion2,
        @Title = N'Owner A version three',
        @ApprovedWording = @ApprovedV3,
        @BodyFormat = N'plain',
        @Classification = N'work',
        @Confirm = 1;

    SELECT @RowVersion3 = CONVERT(binary(8), row_version)
    FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdA;
    IF @RowVersion3 IS NULL OR @RowVersion3 = @RowVersion2
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.knowledge_items
           WHERE knowledge_item_id = @ItemIdA
             AND owner_profile_id = @ProfileIdA
             AND current_version_number = 3
             AND item_status = N'confirmed'
             AND confirmed_version_number = 3
             AND confirmed_by_user_id = @UserIdA
             AND confirmed_at_utc IS NOT NULL
       )
        THROW 53549, 'The second edit did not advance and confirm exactly the owned parent.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @ItemIdA
          AND owner_profile_id = @ProfileIdA
          AND version_number = 3
          AND approved_wording = @ApprovedV3
          AND original_member_wording = @SourceCanary
          AND authored_via = N'typed'
          AND DATALENGTH(original_member_wording) = DATALENGTH(@SourceCanary)
          AND HASHBYTES('SHA2_256', CONVERT(varbinary(max), original_member_wording)) = @V1SourceHash
    )
        THROW 53550, 'Version 3 did not keep the exact stored source as typed edit provenance.', 1;

    IF (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @ItemIdA) <> 3
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.knowledge_item_versions
           WHERE knowledge_item_id = @ItemIdA
             AND owner_profile_id = @ProfileIdA
             AND version_number = 1
             AND HASHBYTES('SHA2_256', CONVERT(varbinary(max), approved_wording)) = @V1ApprovedHash
             AND HASHBYTES('SHA2_256', CONVERT(varbinary(max), original_member_wording)) = @V1SourceHash
             AND saved_at_utc = CONVERT(datetime2(7), '2026-03-01T00:00:00')
       )
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.knowledge_item_versions
           WHERE knowledge_item_id = @ItemIdA
             AND owner_profile_id = @ProfileIdA
             AND version_number = 2
             AND approved_wording = @ApprovedV2
             AND original_member_wording = @SourceCanary
             AND authored_via = N'typed'
       )
        THROW 53551, 'A prior version changed while later edit versions were appended.', 1;

    IF
    (
        SELECT COUNT(*) FROM dbo.audit_events
        WHERE action_type = N'knowledge_item.updated'
          AND entity_type = N'knowledge_item'
          AND entity_key = @ItemKeyA
          AND outcome = N'success'
    ) <> 2
        THROW 53552, 'The two successful edits did not produce exactly two update audits.', 1;

    DECLARE @History TABLE
    (
        version_number int NOT NULL,
        approved_wording nvarchar(max) NOT NULL,
        original_member_wording nvarchar(max) NOT NULL,
        saved_at_utc datetime2(7) NOT NULL
    );
    DECLARE @HistoryMetadata TABLE
    (
        total_count bigint NOT NULL,
        is_truncated bit NOT NULL
    );
    INSERT @History
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 1,
        @IncludeMetadata = 0;
    INSERT @HistoryMetadata
    EXEC dbo.usp_ListKnowledgeItemVersionsForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA,
        @IncludeVersions = 0,
        @IncludeMetadata = 1;
    IF (SELECT COUNT(*) FROM @History) <> 3
       OR (SELECT MIN(version_number) FROM @History) <> 1
       OR (SELECT MAX(version_number) FROM @History) <> 3
       OR NOT EXISTS
       (
           SELECT 1 FROM @History
           WHERE version_number = 3
             AND approved_wording = @ApprovedV3
             AND original_member_wording = @SourceCanary
       )
       OR NOT EXISTS
       (
           SELECT 1 FROM @HistoryMetadata
           WHERE total_count = 3 AND is_truncated = 0
       )
        THROW 53553, 'Workshop F history did not expose the appended approved wording and retained source truthfully.', 1;

    DECLARE @NeutralResult TABLE
    (
        outcome nvarchar(20) NOT NULL,
        version_number int NULL,
        row_version binary(8) NULL
    );
    DECLARE @ForeignItemRowVersion binary(8);
    SELECT @ForeignItemRowVersion = CONVERT(binary(8), row_version)
    FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdB;

    INSERT @NeutralResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyB, @KnowledgeItemKey = @ItemKeyA,
        @ExpectedRowVersion = @RowVersion3, @Title = N'Foreign owner',
        @ApprovedWording = N'Foreign owner edit', @BodyFormat = N'plain',
        @Classification = N'work', @Confirm = 0;
    IF NOT EXISTS (SELECT 1 FROM @NeutralResult WHERE outcome = N'changed' AND version_number IS NULL AND row_version IS NULL)
        THROW 53554, 'A foreign owner did not receive the neutral changed shape.', 1;

    DELETE @NeutralResult;
    INSERT @NeutralResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @ItemKeyB,
        @ExpectedRowVersion = @ForeignItemRowVersion, @Title = N'Foreign item',
        @ApprovedWording = N'Foreign item edit', @BodyFormat = N'plain',
        @Classification = N'work', @Confirm = 0;
    IF NOT EXISTS (SELECT 1 FROM @NeutralResult WHERE outcome = N'changed' AND version_number IS NULL AND row_version IS NULL)
        THROW 53555, 'A foreign item key did not receive the neutral changed shape.', 1;

    DELETE @NeutralResult;
    INSERT @NeutralResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = N'forged-workshop-edit-owner', @KnowledgeItemKey = @ItemKeyA,
        @ExpectedRowVersion = @RowVersion3, @Title = N'Forged owner',
        @ApprovedWording = N'Forged owner edit', @BodyFormat = N'plain',
        @Classification = N'work', @Confirm = 0;
    IF NOT EXISTS (SELECT 1 FROM @NeutralResult WHERE outcome = N'changed' AND version_number IS NULL AND row_version IS NULL)
        THROW 53556, 'A forged owner key did not receive the neutral changed shape.', 1;

    DELETE @NeutralResult;
    INSERT @NeutralResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @UnknownItemKey,
        @ExpectedRowVersion = @RowVersion3, @Title = N'Unknown item',
        @ApprovedWording = N'Unknown item edit', @BodyFormat = N'plain',
        @Classification = N'work', @Confirm = 0;
    IF NOT EXISTS (SELECT 1 FROM @NeutralResult WHERE outcome = N'changed' AND version_number IS NULL AND row_version IS NULL)
        THROW 53557, 'An unknown item key did not receive the neutral changed shape.', 1;

    DELETE @NeutralResult;
    INSERT @NeutralResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @ArchivedItemKey,
        @ExpectedRowVersion = @ArchivedRowVersion, @Title = N'Archived item',
        @ApprovedWording = N'Archived item edit', @BodyFormat = N'plain',
        @Classification = N'work', @Confirm = 0;
    IF NOT EXISTS (SELECT 1 FROM @NeutralResult WHERE outcome = N'changed' AND version_number IS NULL AND row_version IS NULL)
        THROW 53558, 'An archived item did not receive the neutral changed shape.', 1;

    DELETE @NeutralResult;
    INSERT @NeutralResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @ItemKeyA,
        @ExpectedRowVersion = @RowVersion1, @Title = N'Stale edit',
        @ApprovedWording = N'Stale edit wording', @BodyFormat = N'plain',
        @Classification = N'work', @Confirm = 0;
    IF NOT EXISTS (SELECT 1 FROM @NeutralResult WHERE outcome = N'changed' AND version_number IS NULL AND row_version IS NULL)
        THROW 53559, 'A stale rowversion did not receive the neutral changed shape.', 1;

    IF (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @ItemIdA) <> 3
       OR (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @ItemIdB) <> 1
       OR (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @ArchivedItemId) <> 1
       OR (SELECT COUNT(*) FROM dbo.audit_events
           WHERE action_type = N'knowledge_item.updated' AND entity_key = @ItemKeyA) <> 2
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.knowledge_items
           WHERE knowledge_item_id = @ItemIdA
             AND current_version_number = 3
             AND CONVERT(binary(8), row_version) = @RowVersion3
       )
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.knowledge_items
           WHERE knowledge_item_id = @ArchivedItemId
             AND item_status = N'archived'
             AND CONVERT(binary(8), row_version) = @ArchivedRowVersion
       )
        THROW 53560, 'A neutral edit path mutated a parent, version, or audit row.', 1;

    ROLLBACK TRANSACTION;

    /* A deliberately inconsistent parent proves the required current row
       fails with the migration-owned error and that the procedure's catch
       rolls back its entire attempted transaction. */
    DECLARE @MissingGuardVerified bit = 0;
    DECLARE @MissingSuffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @MissingSubject nvarchar(500) = CONCAT(N'workshop-edit-missing-', @MissingSuffix);
    BEGIN TRY
        BEGIN TRANSACTION;

        EXEC dbo.usp_UpsertAppUserFromAuth
            @AuthProvider = N'workshop-edit-provenance-verification',
            @AuthIssuer = @Issuer,
            @AuthSubject = @MissingSubject,
            @DisplayName = N'Workshop missing-current verification owner';

        DECLARE @MissingUserKey nvarchar(300), @MissingProfileId bigint, @MissingUserId int;
        SELECT @MissingUserKey = app_user.user_key,
               @MissingProfileId = profile.profile_id,
               @MissingUserId = app_user.id
        FROM dbo.app_users AS app_user
        JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
        JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
        WHERE identity_record.provider = N'workshop-edit-provenance-verification'
          AND identity_record.issuer = @Issuer
          AND identity_record.subject = @MissingSubject;

        DECLARE @MissingItemId bigint;
        DECLARE @MissingItemKey uniqueidentifier = NEWID();
        DECLARE @MissingRowVersion binary(8);
        INSERT dbo.knowledge_items
            (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
        VALUES (@MissingItemKey, @MissingProfileId, N'unfinished', N'work', 2);
        SET @MissingItemId = SCOPE_IDENTITY();
        INSERT dbo.knowledge_item_versions
            (knowledge_item_id, owner_profile_id, version_number, title,
             approved_wording, original_member_wording, body_format,
             authored_via, saved_by_user_id)
        VALUES
            (@MissingItemId, @MissingProfileId, 1, N'Only version one exists',
             N'Only approved one', N'Only source one', N'plain', N'typed', @MissingUserId);
        SELECT @MissingRowVersion = CONVERT(binary(8), row_version)
        FROM dbo.knowledge_items WHERE knowledge_item_id = @MissingItemId;

        EXEC dbo.usp_UpdateKnowledgeItemForOwner
            @UserKey = @MissingUserKey,
            @KnowledgeItemKey = @MissingItemKey,
            @ExpectedRowVersion = @MissingRowVersion,
            @Title = N'Must not append',
            @ApprovedWording = N'Must not append wording',
            @BodyFormat = N'plain',
            @Classification = N'work',
            @Confirm = 0;

        THROW 53561, 'The missing current version unexpectedly allowed an edit.', 1;
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() <> 53508
            THROW;
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        SET @MissingGuardVerified = 1;
    END CATCH;

    IF @MissingGuardVerified <> 1
        THROW 53562, 'The missing-current-version guard was not observed.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.user_identities
        WHERE provider = N'workshop-edit-provenance-verification'
          AND issuer = @Issuer
          AND subject = @MissingSubject
    )
        THROW 53563, 'The missing-current-version failure left synthetic state behind.', 1;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-WORKSHOP-004 owner-scoped edit provenance: dependencies and fingerprints present; no caller original parameter; exact owned current stored source retained byte-for-byte across v2/v3 while approved wording changes and authored_via is typed; parent/version/audit advancement atomic; prior versions stable; Workshop F history shows three versions and truthful metadata; stale, archived, foreign, forged, and unknown paths neutral; missing current version throws transactionally; synthetic state rolled back.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
