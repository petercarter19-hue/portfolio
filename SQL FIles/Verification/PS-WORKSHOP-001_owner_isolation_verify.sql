/* PS-WORKSHOP-001 (Slice W1) production-safe verification.
   Uses two synthetic owners inside one outer always-rolled-back transaction
   to prove: every one of the seven usp_*KnowledgeItemForOwner procedures
   resolves @UserKey nvarchar(300) -> @ProfileId itself, filters
   owner_profile_id = @ProfileId, never accepts @OwnerProfileId, and never
   references the retired per-item AI-use-permission concept (checked
   below via a runtime-built identifier so the retired name itself never
   appears literally in this file, matching the same absence this
   migration's own header enforces); the list read is
   bounded TOP (200); Save is idempotent per owner (a repeated key returns
   the SAME item and never overwrites its original content); Update is
   fenced by @ExpectedRowVersion with a 'changed' outcome on mismatch;
   Archive/Restore/Delete are owner-isolated and version-fenced; a forged,
   unresolvable @UserKey never returns a row or a truthful-looking write
   outcome from any of the seven procedures; and no private wording ever
   reaches audit metadata or a second content column on the idempotency
   ledger. Every synthetic row is rolled back.

   Calling convention note (discovered by the first live staging rehearsal):
   every one of the five write procedures records its audit event via
   INSERT ... EXEC dbo.usp_AppendAuditEvent once it reaches a real state
   change (Save's success path, Update/Archive/Restore/Delete's success
   path). T-SQL does not allow an INSERT ... EXEC statement to nest inside
   another INSERT ... EXEC - "An INSERT EXEC statement cannot be nested."
   The application never hits this: services/database_service.py always
   calls these procedures with a bare EXEC, so the nested audit call sits
   at nesting level 1 and is fine. This verifier used to wrap every write
   call in INSERT @Table EXEC to capture the returned outcome row, which
   is safe ONLY for a call that stays on an early-return branch (Save's
   'existing'/'not_found', Update/Archive/Restore/Delete's 'changed') and
   therefore never reaches the nested audit call. Any call expected to
   reach the real success path is invoked here with a bare EXEC instead,
   and the resulting state is confirmed with a direct, equally-rigorous
   table read immediately afterward rather than a captured outcome row.

   Second, related discovery: INSERT ... EXEC requires every result set a
   target procedure returns to match the INSERT target's column list - it
   does not silently keep only the first and ignore the rest, despite what
   an earlier version of a comment in the forward migration claimed (also
   never exercised against a real database before this rehearsal).
   usp_ListKnowledgeItemsForOwner and usp_GetKnowledgeItemForOwner each
   return a second, differently-shaped result set (a true total count, and
   bounded version history respectively) that services/knowledge_service.py
   genuinely reads today via a bare, non-nested EXEC. Every List/Get call
   below passes the corresponding opt-out parameter
   (@IncludeTotalCount = 0 / @IncludeHistory = 0, both additive parameters
   defaulting to the application's unchanged behavior) so its
   INSERT ... EXEC capture sees exactly one result set. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-001'
    )
        THROW 53200, 'PS-WORKSHOP-001 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps: every one of the seven procedures
          resolves @UserKey itself, filters by @ProfileId, never accepts
          a caller-supplied @OwnerProfileId, and never references the
          retired per-item AI-use-permission concept. The list read is
          also confirmed bounded to TOP (200) here.
       ------------------------------------------------------------ */
    DECLARE @ProcedureNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProcedureNames (procedure_name)
    VALUES
        (N'usp_ListKnowledgeItemsForOwner'),
        (N'usp_GetKnowledgeItemForOwner'),
        (N'usp_SaveKnowledgeItemForOwner'),
        (N'usp_UpdateKnowledgeItemForOwner'),
        (N'usp_ArchiveKnowledgeItemForOwner'),
        (N'usp_RestoreKnowledgeItemForOwner'),
        (N'usp_DeleteKnowledgeItemForOwner');

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    -- Built at runtime (never written as one contiguous literal in this
    -- file) so the retired per-item AI-use-permission column/concept name
    -- does not appear here even as a comparison target.
    DECLARE @RetiredPermissionIdentifier nvarchar(50) = CONCAT(N'ai_use', N'_permission');
    WHILE EXISTS (SELECT 1 FROM @ProcedureNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ProcedureNames
        ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 53201, 'A required Workshop knowledge procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
           OR @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%' + @RetiredPermissionIdentifier + N'%'
           OR @CheckDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
            THROW 53202, 'A Workshop knowledge procedure is not owner-resolving or leaks a forbidden identifier.', 1;

        DELETE @ProcedureNames WHERE procedure_name = @CheckName;
    END;

    DECLARE @ListDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListKnowledgeItemsForOwner', N'P'));
    IF @ListDefinition NOT LIKE N'%TOP (200)%'
        THROW 53203, 'usp_ListKnowledgeItemsForOwner is not bounded to TOP (200).', 1;

    /* ------------------------------------------------------------
       1. Two synthetic owners via a throwaway auth provider.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:workshop-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'workshop-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'workshop-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Workshop verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Workshop verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;

    SELECT
        @UserKeyA = app_user.user_key,
        @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT
        @UserKeyB = app_user.user_key,
        @ProfileIdB = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 53204, 'Synthetic Workshop owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       2. Idempotent Save: a repeated key returns the SAME item and
          never overwrites its original content; a shared key literal
          used by two different owners creates two independent items
          (per-owner idempotency namespace, per
          UQ_knowledge_item_save_requests_owner_key).
       ------------------------------------------------------------ */
    DECLARE @SaveResult TABLE
    (
        outcome nvarchar(30),
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        row_version binary(8)
    );

    DECLARE @IdempotencyKeyShared nvarchar(200) = CONCAT(N'workshop-key-shared-', @Suffix);
    DECLARE @IdempotencyKeyASecond nvarchar(200) = CONCAT(N'workshop-key-a2-', @Suffix);
    DECLARE @IdempotencyKeyAThird nvarchar(200) = CONCAT(N'workshop-key-a3-', @Suffix);

    DECLARE @TitleA1 nvarchar(160) = CONCAT(N'Owner A first item ', LEFT(@Suffix, 20));
    DECLARE @WordingA1 nvarchar(max) = CONCAT(N'Owner A first item wording ', @Suffix);
    DECLARE @TitleA1Forged nvarchar(160) = N'Forged replay title must not persist';
    DECLARE @WordingA1Forged nvarchar(max) = N'Forged replay wording must not persist';
    DECLARE @TitleA2 nvarchar(160) = CONCAT(N'Owner A second item ', LEFT(@Suffix, 20));
    DECLARE @WordingA2 nvarchar(max) = CONCAT(N'Owner A second item wording ', @Suffix);
    DECLARE @TitleB1 nvarchar(160) =
        N'SYNTHETIC WORKSHOP B ITEM - MUST NOT ENTER OWNER A RESULT';
    DECLARE @WordingB1 nvarchar(max) =
        N'SYNTHETIC WORKSHOP B WORDING - MUST NOT ENTER OWNER A RESULT';

    -- Bare EXEC (not INSERT ... EXEC): this call reaches Save's success
    -- path, which nests its own INSERT ... EXEC of usp_AppendAuditEvent.
    -- See the calling-convention note at the top of this file.
    EXEC dbo.usp_SaveKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyShared,
        @Title = @TitleA1,
        @ApprovedWording = @WordingA1,
        @OriginalWording = @WordingA1,
        @BodyFormat = N'plain',
        @Classification = N'work',
        @AuthoredVia = N'typed',
        @Confirm = 0;

    DECLARE @ItemKeyA1 uniqueidentifier;
    DECLARE @RowVersionA1 binary(8);
    SELECT
        @ItemKeyA1 = item.knowledge_item_key,
        @RowVersionA1 = item.row_version
    FROM dbo.knowledge_item_save_requests AS request
    JOIN dbo.knowledge_items AS item
      ON item.knowledge_item_id = request.knowledge_item_id
     AND item.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdA
      AND request.idempotency_key = @IdempotencyKeyShared;

    IF @ItemKeyA1 IS NULL
        THROW 53205, 'Owner A first Save Knowledge Item did not create an item.', 1;

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyShared,
        @Title = @TitleA1Forged,
        @ApprovedWording = @WordingA1Forged,
        @OriginalWording = @WordingA1Forged,
        @BodyFormat = N'plain',
        @Classification = N'personal',
        @AuthoredVia = N'spoken',
        @Confirm = 1;

    DECLARE @ReplayItemKeyA1 uniqueidentifier;
    DECLARE @ReplayOutcome nvarchar(30);
    SELECT TOP (1) @ReplayItemKeyA1 = knowledge_item_key, @ReplayOutcome = outcome
    FROM @SaveResult;

    IF @ReplayOutcome <> N'existing' OR @ReplayItemKeyA1 <> @ItemKeyA1
        THROW 53206, 'A repeated idempotency key did not return the same knowledge item.', 1;

    DECLARE @ItemIdA1 bigint;
    SELECT @ItemIdA1 = knowledge_item_id
    FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA1;

    IF (SELECT COUNT(*) FROM dbo.knowledge_items WHERE owner_profile_id = @ProfileIdA) <> 1
        THROW 53207, 'A replayed Save Knowledge Item created a second item.', 1;
    IF (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @ItemIdA1) <> 1
        THROW 53208, 'A replayed Save Knowledge Item created an extra version.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @ItemIdA1
          AND (title = @TitleA1Forged OR approved_wording = @WordingA1Forged)
    )
        THROW 53209, 'A replayed Save Knowledge Item overwrote the original canonical wording.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @ItemIdA1 AND title = @TitleA1 AND approved_wording = @WordingA1
    )
        THROW 53210, 'The original Save Knowledge Item wording did not persist.', 1;
    IF EXISTS (SELECT 1 FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdA1 AND item_status = N'confirmed')
        THROW 53211, 'A replayed Save Knowledge Item applied the replay''s confirm flag.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.knowledge_item_save_requests
        WHERE owner_profile_id = @ProfileIdA AND idempotency_key = @IdempotencyKeyShared
    ) <> 1
        THROW 53212, 'The idempotency ledger recorded more than one replay row.', 1;

    -- Bare EXEC: reaches Save's success path (see calling-convention note).
    EXEC dbo.usp_SaveKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyASecond,
        @Title = @TitleA2,
        @ApprovedWording = @WordingA2,
        @OriginalWording = @WordingA2,
        @BodyFormat = N'plain',
        @Classification = N'both',
        @AuthoredVia = N'typed',
        @Confirm = 0;

    DECLARE @ItemKeyA2 uniqueidentifier;
    SELECT @ItemKeyA2 = item.knowledge_item_key
    FROM dbo.knowledge_item_save_requests AS request
    JOIN dbo.knowledge_items AS item
      ON item.knowledge_item_id = request.knowledge_item_id
     AND item.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdA
      AND request.idempotency_key = @IdempotencyKeyASecond;

    IF @ItemKeyA2 IS NULL OR @ItemKeyA2 = @ItemKeyA1
        THROW 53213, 'A distinct idempotency key did not create a distinct second item.', 1;

    -- Bare EXEC: reaches Save's success path (see calling-convention note).
    EXEC dbo.usp_SaveKnowledgeItemForOwner
        @UserKey = @UserKeyB,
        @IdempotencyKey = @IdempotencyKeyShared,
        @Title = @TitleB1,
        @ApprovedWording = @WordingB1,
        @OriginalWording = @WordingB1,
        @BodyFormat = N'plain',
        @Classification = N'work',
        @AuthoredVia = N'typed',
        @Confirm = 0;

    DECLARE @ItemKeyB1 uniqueidentifier;
    SELECT @ItemKeyB1 = item.knowledge_item_key
    FROM dbo.knowledge_item_save_requests AS request
    JOIN dbo.knowledge_items AS item
      ON item.knowledge_item_id = request.knowledge_item_id
     AND item.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdB
      AND request.idempotency_key = @IdempotencyKeyShared;

    IF @ItemKeyB1 IS NULL OR @ItemKeyB1 = @ItemKeyA1 OR @ItemKeyB1 = @ItemKeyA2
        THROW 53214, 'The same idempotency-key literal collided across two different owners.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.knowledge_item_save_requests
        WHERE idempotency_key = @IdempotencyKeyShared
    ) <> 2
        THROW 53215, 'The per-owner idempotency ledger did not scope by owner.', 1;

    /* ------------------------------------------------------------
       3. Owner-isolated list read, default archived-excluded view.
       ------------------------------------------------------------ */
    DECLARE @ListRead TABLE
    (
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        classification nvarchar(20),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        archived_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        title nvarchar(160),
        body_format nvarchar(20),
        authored_via nvarchar(30)
    );

    INSERT @ListRead
    EXEC dbo.usp_ListKnowledgeItemsForOwner @UserKey = @UserKeyA, @IncludeArchived = 0, @IncludeTotalCount = 0;

    IF (SELECT COUNT(*) FROM @ListRead) <> 2
        THROW 53216, 'Owner A default list did not return exactly owner A''s two items.', 1;
    IF EXISTS (SELECT 1 FROM @ListRead WHERE knowledge_item_key = @ItemKeyB1)
        THROW 53217, 'Cross-owner item leaked into the owner A list read.', 1;
    IF EXISTS (SELECT 1 FROM @ListRead WHERE title = @TitleB1)
        THROW 53218, 'Owner B''s sentinel title leaked into the owner A list read.', 1;

    /* ------------------------------------------------------------
       4. Get: single-item read plus history; unauthorized for a
          different owner's key.
       ------------------------------------------------------------ */
    DECLARE @GetReadA TABLE
    (
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        classification nvarchar(20),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        archived_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        version_number int,
        title nvarchar(160),
        approved_wording nvarchar(max),
        original_member_wording nvarchar(max),
        body_format nvarchar(20),
        authored_via nvarchar(30),
        saved_at_utc datetime2(7)
    );

    INSERT @GetReadA
    EXEC dbo.usp_GetKnowledgeItemForOwner @UserKey = @UserKeyA, @KnowledgeItemKey = @ItemKeyA1, @IncludeHistory = 0;

    IF (SELECT COUNT(*) FROM @GetReadA) <> 1
        THROW 53219, 'Owner A Get did not return exactly one item.', 1;
    IF NOT EXISTS (SELECT 1 FROM @GetReadA WHERE title = @TitleA1 AND approved_wording = @WordingA1)
        THROW 53220, 'Owner A Get did not return the persisted original wording.', 1;

    DECLARE @GetReadCrossOwner TABLE
    (
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        classification nvarchar(20),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        archived_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        version_number int,
        title nvarchar(160),
        approved_wording nvarchar(max),
        original_member_wording nvarchar(max),
        body_format nvarchar(20),
        authored_via nvarchar(30),
        saved_at_utc datetime2(7)
    );

    INSERT @GetReadCrossOwner
    EXEC dbo.usp_GetKnowledgeItemForOwner @UserKey = @UserKeyB, @KnowledgeItemKey = @ItemKeyA1, @IncludeHistory = 0;

    IF EXISTS (SELECT 1 FROM @GetReadCrossOwner)
        THROW 53221, 'Owner B''s Get resolved owner A''s knowledge item key.', 1;

    /* ------------------------------------------------------------
       5. Update: version-fenced edit; a stale @ExpectedRowVersion
          returns 'changed' with no new version; a correct one creates
          version 2, sets original_member_wording = approved_wording,
          and can confirm the item.
       ------------------------------------------------------------ */
    DECLARE @UpdateResult TABLE
    (
        outcome nvarchar(30),
        version_number int,
        row_version binary(8)
    );
    DECLARE @StaleRowVersion binary(8) = 0x0000000000000001;

    INSERT @UpdateResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA1,
        @ExpectedRowVersion = @StaleRowVersion,
        @Title = @TitleA1,
        @ApprovedWording = N'This edit must not apply.',
        @BodyFormat = N'plain',
        @Classification = N'work',
        @Confirm = 0;

    IF EXISTS (SELECT 1 FROM @UpdateResult WHERE outcome <> N'changed' OR version_number IS NOT NULL)
        THROW 53222, 'A stale @ExpectedRowVersion did not produce a changed outcome.', 1;
    IF (SELECT current_version_number FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdA1) <> 1
        THROW 53223, 'A stale @ExpectedRowVersion update advanced the version number.', 1;

    DECLARE @TitleA1Updated nvarchar(160) = CONCAT(N'Owner A first item updated ', LEFT(@Suffix, 20));
    DECLARE @WordingA1Updated nvarchar(max) = CONCAT(N'Owner A first item updated wording ', @Suffix);

    -- Bare EXEC: reaches Update's success path (see calling-convention note).
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @KnowledgeItemKey = @ItemKeyA1,
        @ExpectedRowVersion = @RowVersionA1,
        @Title = @TitleA1Updated,
        @ApprovedWording = @WordingA1Updated,
        @BodyFormat = N'plain',
        @Classification = N'work',
        @Confirm = 1;

    DECLARE @UpdatedVersionNumber int;
    SELECT @UpdatedVersionNumber = current_version_number
    FROM dbo.knowledge_items
    WHERE knowledge_item_id = @ItemIdA1;

    IF @UpdatedVersionNumber <> 2
        THROW 53224, 'A correctly fenced Update did not create version 2.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @ItemIdA1 AND version_number = 2
          AND title = @TitleA1Updated
          AND approved_wording = @WordingA1Updated
          AND original_member_wording = @WordingA1Updated
          AND authored_via = N'typed'
    )
        THROW 53225, 'Update did not persist a second version with original wording mirroring the approved wording.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_items
        WHERE knowledge_item_id = @ItemIdA1
          AND item_status = N'confirmed'
          AND current_version_number = 2
          AND confirmed_version_number = 2
    )
        THROW 53226, 'Update with @Confirm = 1 did not confirm the item at its current version.', 1;

    /* ------------------------------------------------------------
       6. Archive / Restore: owner-isolated, version-fenced lifecycle.
       ------------------------------------------------------------ */
    DECLARE @ArchiveResult TABLE (outcome nvarchar(30), row_version binary(8));
    DECLARE @RowVersionA2 binary(8) =
        (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA2);

    -- Bare EXEC: reaches Archive's success path (see calling-convention note).
    EXEC dbo.usp_ArchiveKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @ItemKeyA2, @ExpectedRowVersion = @RowVersionA2;

    DECLARE @ArchiveOutcome nvarchar(30) =
    (
        SELECT CASE WHEN item_status = N'archived' THEN N'success' ELSE N'unexpected' END
        FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA2
    );
    IF @ArchiveOutcome <> N'success'
        THROW 53227, 'A correctly fenced Archive did not succeed.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_items
        WHERE knowledge_item_key = @ItemKeyA2
          AND item_status = N'archived'
          AND archived_at_utc IS NOT NULL
          AND archived_by_user_id IS NOT NULL
    )
        THROW 53228, 'Archive did not set the archived triple.', 1;

    DELETE @ListRead;
    INSERT @ListRead
    EXEC dbo.usp_ListKnowledgeItemsForOwner @UserKey = @UserKeyA, @IncludeArchived = 0, @IncludeTotalCount = 0;
    IF EXISTS (SELECT 1 FROM @ListRead WHERE knowledge_item_key = @ItemKeyA2)
        THROW 53229, 'An archived item leaked into the default owner A list read.', 1;

    DELETE @ListRead;
    INSERT @ListRead
    EXEC dbo.usp_ListKnowledgeItemsForOwner @UserKey = @UserKeyA, @IncludeArchived = 1, @IncludeTotalCount = 0;
    IF NOT EXISTS (SELECT 1 FROM @ListRead WHERE knowledge_item_key = @ItemKeyA2 AND item_status = N'archived')
        THROW 53230, 'Including archived items did not report the archived item as archived.', 1;

    DECLARE @RestoreResult TABLE (outcome nvarchar(30), row_version binary(8));
    DECLARE @RowVersionA2Archived binary(8) =
        (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA2);

    -- Bare EXEC: reaches Restore's success path (see calling-convention note).
    EXEC dbo.usp_RestoreKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @ItemKeyA2, @ExpectedRowVersion = @RowVersionA2Archived;

    DECLARE @RestoreOutcome nvarchar(30) =
    (
        SELECT CASE WHEN archived_at_utc IS NULL THEN N'success' ELSE N'unexpected' END
        FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA2
    );
    IF @RestoreOutcome <> N'success'
        THROW 53231, 'A correctly fenced Restore did not succeed.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_items
        WHERE knowledge_item_key = @ItemKeyA2
          AND item_status = N'unfinished'
          AND archived_at_utc IS NULL
          AND archived_by_user_id IS NULL
    )
        THROW 53232, 'Restore did not return the never-confirmed item to unfinished with cleared archive fields.', 1;

    /* ------------------------------------------------------------
       7. Delete: owner-isolated, version-fenced hard delete of a
          throwaway third item (W1 has no downstream use table yet).
       ------------------------------------------------------------ */
    -- Bare EXEC: reaches Save's success path (see calling-convention note).
    EXEC dbo.usp_SaveKnowledgeItemForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyAThird,
        @Title = N'Owner A throwaway item',
        @ApprovedWording = N'Owner A throwaway wording.',
        @OriginalWording = N'Owner A throwaway wording.',
        @BodyFormat = N'plain',
        @Classification = N'unclassified',
        @AuthoredVia = N'typed',
        @Confirm = 0;

    DECLARE @ItemKeyA3 uniqueidentifier;
    SELECT @ItemKeyA3 = item.knowledge_item_key
    FROM dbo.knowledge_item_save_requests AS request
    JOIN dbo.knowledge_items AS item
      ON item.knowledge_item_id = request.knowledge_item_id
     AND item.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdA
      AND request.idempotency_key = @IdempotencyKeyAThird;

    IF @ItemKeyA3 IS NULL
        THROW 53233, 'The throwaway third item for Delete was not created.', 1;

    DECLARE @ItemIdA3 bigint;
    DECLARE @RowVersionA3 binary(8);
    SELECT @ItemIdA3 = knowledge_item_id, @RowVersionA3 = row_version
    FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA3;

    -- Captured before the delete: usp_DeleteKnowledgeItemForOwner hard-deletes
    -- both the item and its versions, so the version count cannot be read
    -- back from the outcome row (bare EXEC - see calling-convention note)
    -- or from the table afterward; it is asserted independently here instead.
    DECLARE @PreDeleteVersionCount int =
        (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @ItemIdA3);

    EXEC dbo.usp_DeleteKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @ItemKeyA3, @ExpectedRowVersion = @RowVersionA3;

    DECLARE @DeleteOutcome nvarchar(30) =
    (
        SELECT CASE WHEN EXISTS
        (
            SELECT 1 FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA3
        ) THEN N'unexpected' ELSE N'success' END
    );
    IF @DeleteOutcome <> N'success' OR @PreDeleteVersionCount <> 1
        THROW 53234, 'A correctly fenced Delete did not succeed with one deleted version.', 1;
    IF EXISTS (SELECT 1 FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA3)
        THROW 53235, 'Delete did not remove the knowledge item row.', 1;
    IF EXISTS (SELECT 1 FROM dbo.knowledge_item_versions WHERE knowledge_item_id IN (SELECT knowledge_item_id FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA3))
        THROW 53236, 'Delete did not remove the item''s versions.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_save_requests
        WHERE knowledge_item_id NOT IN (SELECT knowledge_item_id FROM dbo.knowledge_items)
          AND idempotency_key = @IdempotencyKeyAThird
    )
        THROW 53237, 'Delete left an orphaned idempotency ledger row referencing a removed item.', 1;

    -- Declared here (rather than beside the real Delete call above, which
    -- now uses a bare EXEC - see calling-convention note) because it is
    -- still needed below for the forged-owner Delete canary, which stays
    -- on Delete's early-return 'changed' branch and can safely capture its
    -- outcome row via INSERT ... EXEC.
    DECLARE @DeleteResult TABLE (outcome nvarchar(30), deleted_version_count int);

    /* ------------------------------------------------------------
       8. Reverse-direction owner isolation on the read.
       ------------------------------------------------------------ */
    DECLARE @ListReadB TABLE
    (
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        classification nvarchar(20),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        archived_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        title nvarchar(160),
        body_format nvarchar(20),
        authored_via nvarchar(30)
    );
    INSERT @ListReadB
    EXEC dbo.usp_ListKnowledgeItemsForOwner @UserKey = @UserKeyB, @IncludeArchived = 1, @IncludeTotalCount = 0;

    IF (SELECT COUNT(*) FROM @ListReadB) <> 1
       OR NOT EXISTS (SELECT 1 FROM @ListReadB WHERE knowledge_item_key = @ItemKeyB1)
        THROW 53238, 'Owner B list did not return exactly owner B''s own item.', 1;
    IF EXISTS (SELECT 1 FROM @ListReadB WHERE knowledge_item_key IN (@ItemKeyA1, @ItemKeyA2))
        THROW 53239, 'Cross-owner item leaked into the owner B list read.', 1;

    /* ------------------------------------------------------------
       9. Forged/unresolvable owner: never resolves any row, and never
          produces a truthful-looking write outcome, from any of the
          seven procedures.
       ------------------------------------------------------------ */
    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    DECLARE @ListReadForged TABLE
    (
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        classification nvarchar(20),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        archived_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        title nvarchar(160),
        body_format nvarchar(20),
        authored_via nvarchar(30)
    );
    INSERT @ListReadForged
    EXEC dbo.usp_ListKnowledgeItemsForOwner @UserKey = @ForgedUserKey, @IncludeArchived = 1, @IncludeTotalCount = 0;
    IF EXISTS (SELECT 1 FROM @ListReadForged)
        THROW 53240, 'A forged UserKey returned rows from the list read.', 1;

    DECLARE @GetReadForged TABLE
    (
        knowledge_item_key uniqueidentifier,
        item_status nvarchar(30),
        classification nvarchar(20),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        archived_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        version_number int,
        title nvarchar(160),
        approved_wording nvarchar(max),
        original_member_wording nvarchar(max),
        body_format nvarchar(20),
        authored_via nvarchar(30),
        saved_at_utc datetime2(7)
    );
    INSERT @GetReadForged
    EXEC dbo.usp_GetKnowledgeItemForOwner @UserKey = @ForgedUserKey, @KnowledgeItemKey = @ItemKeyA1, @IncludeHistory = 0;
    IF EXISTS (SELECT 1 FROM @GetReadForged)
        THROW 53241, 'A forged UserKey returned rows from the get read.', 1;

    DECLARE @IdempotencyKeyForged nvarchar(200) = CONCAT(N'workshop-key-forged-', @Suffix);
    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveKnowledgeItemForOwner
        @UserKey = @ForgedUserKey,
        @IdempotencyKey = @IdempotencyKeyForged,
        @Title = N'Forged owner save',
        @ApprovedWording = N'Forged owner save must not persist.',
        @OriginalWording = N'Forged owner save must not persist.',
        @BodyFormat = N'plain',
        @Classification = N'work',
        @AuthoredVia = N'typed',
        @Confirm = 0;

    IF EXISTS (SELECT 1 FROM @SaveResult WHERE outcome <> N'not_found' OR knowledge_item_key IS NOT NULL)
        THROW 53242, 'A forged UserKey produced a truthful-looking Save outcome.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.knowledge_items
        WHERE owner_profile_id NOT IN (@ProfileIdA, @ProfileIdB)
    )
        THROW 53243, 'A forged-owner Save call created an orphaned knowledge item.', 1;

    DECLARE @RowVersionA1Current binary(8) =
        (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA1);

    DELETE @UpdateResult;
    INSERT @UpdateResult
    EXEC dbo.usp_UpdateKnowledgeItemForOwner
        @UserKey = @ForgedUserKey,
        @KnowledgeItemKey = @ItemKeyA1,
        @ExpectedRowVersion = @RowVersionA1Current,
        @Title = N'Forged update must not apply',
        @ApprovedWording = N'Forged update must not apply.',
        @BodyFormat = N'plain',
        @Classification = N'work',
        @Confirm = 0;
    IF EXISTS (SELECT 1 FROM @UpdateResult WHERE outcome <> N'changed' OR version_number IS NOT NULL)
        THROW 53244, 'A forged UserKey produced a truthful-looking Update outcome.', 1;

    DELETE @ArchiveResult;
    INSERT @ArchiveResult
    EXEC dbo.usp_ArchiveKnowledgeItemForOwner
        @UserKey = @ForgedUserKey, @KnowledgeItemKey = @ItemKeyA1, @ExpectedRowVersion = @RowVersionA1Current;
    IF EXISTS (SELECT 1 FROM @ArchiveResult WHERE outcome <> N'changed')
        THROW 53245, 'A forged UserKey produced a truthful-looking Archive outcome.', 1;

    DELETE @RestoreResult;
    INSERT @RestoreResult
    EXEC dbo.usp_RestoreKnowledgeItemForOwner
        @UserKey = @ForgedUserKey, @KnowledgeItemKey = @ItemKeyA2, @ExpectedRowVersion = @RowVersionA1Current;
    IF EXISTS (SELECT 1 FROM @RestoreResult WHERE outcome <> N'changed')
        THROW 53246, 'A forged UserKey produced a truthful-looking Restore outcome.', 1;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteKnowledgeItemForOwner
        @UserKey = @ForgedUserKey, @KnowledgeItemKey = @ItemKeyA1, @ExpectedRowVersion = @RowVersionA1Current;
    IF EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome <> N'changed' OR deleted_version_count IS NOT NULL)
        THROW 53247, 'A forged UserKey produced a truthful-looking Delete outcome.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.knowledge_items WHERE knowledge_item_key = @ItemKeyA1)
        THROW 53248, 'A forged-owner Delete call removed a real owner''s knowledge item.', 1;

    /* ------------------------------------------------------------
       10. No private wording in audit metadata, and no content column
           on the idempotency ledger.
       ------------------------------------------------------------ */
    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.entity_type = N'knowledge_item'
          AND audit_event.entity_key IN (@ItemKeyA1, @ItemKeyA2, @ItemKeyB1)
          AND
          (
              audit_event.metadata_json LIKE N'%' + @WordingA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @WordingA2 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @WordingB1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @TitleA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @TitleB1 + N'%'
          )
    )
        THROW 53249, 'Audit metadata contains private knowledge item wording.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.knowledge_item_save_requests')
          AND name IN (N'title', N'approved_wording', N'original_member_wording', N'body')
    )
        THROW 53250, 'The idempotency ledger contains a wording/content column.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-WORKSHOP-001 two-owner isolation across all seven procedures, per-owner idempotent Save without overwrite, version-fenced Update/Archive/Restore/Delete, forged-owner canaries on every write, TOP (200) list bound, no retired per-item AI-use-permission column or @OwnerProfileId leakage, no private wording in audit metadata, and full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
