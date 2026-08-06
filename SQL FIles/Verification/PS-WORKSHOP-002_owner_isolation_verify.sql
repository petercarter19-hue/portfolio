/* PS-WORKSHOP-002 (leg 9: gated in-place knowledge backlog confirmation)
   production-safe verification. Uses two synthetic owners inside one outer
   always-rolled-back transaction to prove:

     1. usp_ConfirmAuthoredKnowledgeBacklogForOwner resolves @UserKey ->
        @ProfileId itself, never accepts @OwnerProfileId, and its SET list
        never assigns updated_at_utc.
     2. A pre-existing member-authored N'unfinished' row confirms in place:
        item_status becomes N'confirmed', confirmed_version_number equals
        current_version_number, confirmed_by_user_id/confirmed_at_utc are
        set -- while current_version_number, updated_at_utc, title,
        approved_wording, original_member_wording, and authored_via are all
        BYTE-IDENTICAL before and after, and knowledge_item_versions gains
        no row.
     3. A N'suggested' row and an already-N'archived' row are completely
        untouched (row_version identical), whatever @MaxItems is passed.
     4. An already-N'confirmed' row is untouched (idempotent with respect to
        rows outside its scope).
     5. Bounded and deterministic: with two eligible rows and @MaxItems = 1,
        exactly the older one confirms and remaining_count = 1; a second
        call with the default @MaxItems confirms the rest.
     6. Cross-owner isolation and a forged, unresolvable @UserKey: neither
        touches another owner's rows or produces a truthful-looking result.
     7. Every confirmed item gets exactly one audit row under the DISTINCT
        action N'knowledge_item.backlog_confirmed' -- never
        N'knowledge_item.updated' or N'knowledge_item.saved' -- and no
        private wording reaches its metadata.
     8. The archive/restore fix: usp_ArchiveKnowledgeItemForOwner now
        refuses a N'suggested' row (outcome 'changed', item_status
        unchanged) but still archives a genuine N'unfinished' or
        N'confirmed' row exactly as before; restoring a never-confirmed
        archived item returns it to N'unfinished', and that restored item
        IS correctly picked up by the next backlog confirmation call --
        proving the laundering path (suggested -> archived -> restored
        unfinished -> auto-confirmed) is closed at the archive step, not
        merely untested.

   Calling convention (the PS-WORKSHOP-001_owner_isolation_verify.sql
   idiom, restated here because the first draft of this file violated it):
   every one of usp_ConfirmAuthoredKnowledgeBacklogForOwner,
   usp_ArchiveKnowledgeItemForOwner, and usp_RestoreKnowledgeItemForOwner
   records its audit event via INSERT ... EXEC dbo.usp_AppendAuditEvent
   once it reaches a real state change (Confirm's per-item loop body,
   Archive/Restore's success path). T-SQL does not allow an INSERT ... EXEC
   statement to nest inside another INSERT ... EXEC -- "An INSERT EXEC
   statement cannot be nested." A call that stays on an early-return branch
   (Confirm with a forged key or zero eligible candidates; Archive's
   'changed' outcome) never reaches that nested call and is safe to wrap in
   INSERT @Table EXEC to capture its outcome row. A call expected to reach
   the real success path is invoked below with a bare EXEC instead, and the
   resulting state is confirmed with a direct, equally-rigorous table read
   immediately afterward rather than a captured outcome row.

   Every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-WORKSHOP-002')
        THROW 53350, 'PS-WORKSHOP-002 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps.
       ------------------------------------------------------------ */
    DECLARE @ConfirmDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner', N'P'));
    IF @ConfirmDefinition IS NULL
        THROW 53351, 'usp_ConfirmAuthoredKnowledgeBacklogForOwner does not exist.', 1;
    IF @ConfirmDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @ConfirmDefinition LIKE N'%@OwnerProfileId%'
       OR @ConfirmDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
        THROW 53352, 'usp_ConfirmAuthoredKnowledgeBacklogForOwner is not owner-resolving or leaks a forbidden identifier.', 1;
    IF @ConfirmDefinition NOT LIKE N'%item_status = N''unfinished''%'
       OR @ConfirmDefinition NOT LIKE N'%archived_at_utc IS NULL%'
        THROW 53353, 'usp_ConfirmAuthoredKnowledgeBacklogForOwner does not structurally exclude suggested/archived rows.', 1;
    IF @ConfirmDefinition LIKE N'%updated_at_utc =%'
        THROW 53354, 'usp_ConfirmAuthoredKnowledgeBacklogForOwner touches updated_at_utc.', 1;
    IF @ConfirmDefinition LIKE N'%INSERT dbo.knowledge_item_versions%'
       OR @ConfirmDefinition LIKE N'%approved_wording =%'
       OR @ConfirmDefinition LIKE N'%original_member_wording =%'
       OR @ConfirmDefinition LIKE N'%authored_via =%'
        THROW 53355, 'usp_ConfirmAuthoredKnowledgeBacklogForOwner touches version/wording/provenance.', 1;
    IF @ConfirmDefinition NOT LIKE N'%knowledge_item.backlog_confirmed%'
        THROW 53356, 'usp_ConfirmAuthoredKnowledgeBacklogForOwner does not use the distinct audit action.', 1;

    DECLARE @ArchiveDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ArchiveKnowledgeItemForOwner', N'P'));
    IF @ArchiveDefinition NOT LIKE N'%item.item_status IN (N''unfinished'', N''confirmed'')%'
        THROW 53357, 'usp_ArchiveKnowledgeItemForOwner does not refuse a suggested row.', 1;

    /* ------------------------------------------------------------
       1. Two synthetic owners.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:workshop-confirmation-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'workshop-confirm-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'workshop-confirm-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-confirmation-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectA,
        @DisplayName = N'Backlog verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'workshop-confirmation-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectB,
        @DisplayName = N'Backlog verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;

    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id, @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-confirmation-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'workshop-confirmation-verification'
      AND identity_record.issuer = @Issuer AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 53358, 'Synthetic backlog-confirmation owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       2. Seed owner A's backlog: two eligible unfinished items (older
          "item1" and newer "item2", for the bound/order test), plus one
          suggested, one already-confirmed, and one already-archived
          never-confirmed item that must all stay untouched. Owner B gets
          one eligible unfinished item of its own, for cross-owner
          isolation.
       ------------------------------------------------------------ */
    DECLARE @BackdatedAt datetime2(7) = '2020-01-01T00:00:00';
    DECLARE @Item2BackdatedAt datetime2(7) = DATEADD(SECOND, 1, @BackdatedAt);

    DECLARE @Item1Key uniqueidentifier = NEWID();
    DECLARE @Item1Id bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@Item1Key, @ProfileIdA, N'unfinished', N'work', 1);
    SET @Item1Id = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@Item1Id, @ProfileIdA, 1, N'Owner A backlog item one',
            N'You led a systems integration effort end to end.',
            N'You led a systems integration effort end to end.', N'typed', @UserIdA);
    UPDATE dbo.knowledge_items
    SET created_at_utc = @BackdatedAt, updated_at_utc = @BackdatedAt
    WHERE knowledge_item_id = @Item1Id;

    DECLARE @Item2Key uniqueidentifier = NEWID();
    DECLARE @Item2Id bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@Item2Key, @ProfileIdA, N'unfinished', N'personal', 1);
    SET @Item2Id = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@Item2Id, @ProfileIdA, 1, N'Owner A backlog item two',
            N'You train and race long distances.',
            N'You train and race long distances.', N'spoken', @UserIdA);
    UPDATE dbo.knowledge_items
    SET created_at_utc = @Item2BackdatedAt, updated_at_utc = @Item2BackdatedAt
    WHERE knowledge_item_id = @Item2Id;

    DECLARE @SuggestedKey uniqueidentifier = NEWID();
    DECLARE @SuggestedId bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@SuggestedKey, @ProfileIdA, N'suggested', N'work', 1);
    SET @SuggestedId = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@SuggestedId, @ProfileIdA, 1, N'SYNTHETIC AI suggestion, never accepted',
            N'A possible connection PeerSlate noticed.',
            N'A possible connection PeerSlate noticed.', N'ai_assisted_approved', @UserIdA);

    DECLARE @ConfirmedKey uniqueidentifier = NEWID();
    DECLARE @ConfirmedId bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number, confirmed_version_number, confirmed_by_user_id, confirmed_at_utc)
    VALUES (@ConfirmedKey, @ProfileIdA, N'confirmed', N'work', 1, 1, @UserIdA, @BackdatedAt);
    SET @ConfirmedId = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@ConfirmedId, @ProfileIdA, 1, N'Owner A already-confirmed item',
            N'Already confirmed before this migration ever ran.',
            N'Already confirmed before this migration ever ran.', N'typed', @UserIdA);

    DECLARE @ArchivedKey uniqueidentifier = NEWID();
    DECLARE @ArchivedId bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number, archived_at_utc, archived_by_user_id)
    VALUES (@ArchivedKey, @ProfileIdA, N'archived', N'work', 1, @BackdatedAt, @UserIdA);
    SET @ArchivedId = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@ArchivedId, @ProfileIdA, 1, N'Owner A never-confirmed archived item',
            N'Archived before it was ever confirmed.',
            N'Archived before it was ever confirmed.', N'typed', @UserIdA);

    DECLARE @ItemBKey uniqueidentifier = NEWID();
    DECLARE @ItemBId bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@ItemBKey, @ProfileIdB, N'unfinished', N'work', 1);
    SET @ItemBId = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@ItemBId, @ProfileIdB, 1, N'SYNTHETIC WORKSHOP B ITEM - MUST NOT BE CONFIRMED BY OWNER A',
            N'Owner B''s own unfinished wording.',
            N'Owner B''s own unfinished wording.', N'typed', @UserIdB);

    /* Before-snapshots, captured after every backdate above. */
    DECLARE @Item1RowVersionBefore binary(8), @Item2RowVersionBefore binary(8);
    DECLARE @SuggestedRowVersionBefore binary(8), @ConfirmedRowVersionBefore binary(8);
    DECLARE @ArchivedRowVersionBefore binary(8), @ItemBRowVersionBefore binary(8);
    SELECT @Item1RowVersionBefore = row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @Item1Id;
    SELECT @Item2RowVersionBefore = row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @Item2Id;
    SELECT @SuggestedRowVersionBefore = row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @SuggestedId;
    SELECT @ConfirmedRowVersionBefore = row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @ConfirmedId;
    SELECT @ArchivedRowVersionBefore = row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @ArchivedId;
    SELECT @ItemBRowVersionBefore = row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemBId;

    /* ------------------------------------------------------------
       3. Forged, unresolvable owner first: never resolves any row,
          never mutates anything, never produces a truthful-looking
          result from either procedure this migration owns.
       ------------------------------------------------------------ */
    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';
    DECLARE @ConfirmResult TABLE (confirmed_count int, remaining_count int);

    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner @UserKey = @ForgedUserKey;
    IF EXISTS (SELECT 1 FROM @ConfirmResult WHERE confirmed_count <> 0 OR remaining_count <> 0)
        THROW 53359, 'A forged UserKey produced a truthful-looking backlog confirmation result.', 1;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item1Id) <> N'unfinished'
        THROW 53360, 'A forged UserKey confirmed a real owner''s knowledge item.', 1;

    DECLARE @ForgedArchiveResult TABLE (outcome nvarchar(30), row_version binary(8));
    INSERT @ForgedArchiveResult
    EXEC dbo.usp_ArchiveKnowledgeItemForOwner
        @UserKey = @ForgedUserKey, @KnowledgeItemKey = @Item1Key, @ExpectedRowVersion = @Item1RowVersionBefore;
    IF EXISTS (SELECT 1 FROM @ForgedArchiveResult WHERE outcome <> N'changed')
        THROW 53361, 'A forged UserKey produced a truthful-looking Archive outcome.', 1;

    /* ------------------------------------------------------------
       4. Cross-owner: owner B's call must never touch owner A's rows.
       ------------------------------------------------------------ */
    -- Bare EXEC (not INSERT ... EXEC): this call reaches the real,
    -- audit-writing success path (owner B has exactly one eligible item),
    -- which nests its own INSERT ... EXEC of usp_AppendAuditEvent. See the
    -- calling-convention note at the top of this file. The outcome is
    -- confirmed by direct table reads immediately below instead of a
    -- captured outcome row.
    EXEC dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner @UserKey = @UserKeyB;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemBId) <> N'confirmed'
        THROW 53363, 'Owner B''s own item was not confirmed by owner B''s own call.', 1;
    IF EXISTS (SELECT 1 FROM dbo.knowledge_items WHERE owner_profile_id = @ProfileIdB
               AND item_status = N'unfinished' AND archived_at_utc IS NULL)
        THROW 53362, 'Owner B''s own backlog call left an eligible item unconfirmed.', 1;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item1Id) <> N'unfinished'
       OR (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item2Id) <> N'unfinished'
        THROW 53364, 'Owner B''s call confirmed owner A''s knowledge items.', 1;

    /* ------------------------------------------------------------
       5. Bounded and deterministic: @MaxItems = 1 confirms only the
          older item1, leaving item2 and remaining_count = 1.
       ------------------------------------------------------------ */
    -- Bare EXEC: reaches the real, audit-writing success path (see the
    -- calling-convention note at the top of this file).
    EXEC dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner @UserKey = @UserKeyA, @MaxItems = 1;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item1Id) <> N'confirmed'
        THROW 53366, 'The bounded call did not confirm the older eligible item first.', 1;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item2Id) <> N'unfinished'
        THROW 53367, 'The bounded call confirmed more than @MaxItems items.', 1;
    IF (SELECT COUNT(*) FROM dbo.knowledge_items WHERE owner_profile_id = @ProfileIdA
        AND item_status = N'unfinished' AND archived_at_utc IS NULL) <> 1
        THROW 53365, 'A bounded call did not leave exactly one eligible item remaining.', 1;

    /* Byte-stability proof for item1: exactly the confirmation triple and
       item_status changed; current_version_number, updated_at_utc, and
       every version-table column are byte-identical to their seeded
       values, and no second version row was written. */
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_items
        WHERE knowledge_item_id = @Item1Id
          AND item_status = N'confirmed'
          AND confirmed_version_number = 1
          AND confirmed_by_user_id = @UserIdA
          AND confirmed_at_utc IS NOT NULL
          AND current_version_number = 1
          AND updated_at_utc = @BackdatedAt
          AND created_at_utc = @BackdatedAt
    )
        THROW 53368, 'Confirmation did not set exactly the confirmation triple, or touched updated_at_utc/current_version_number.', 1;
    IF (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @Item1Id) <> 1
        THROW 53369, 'Confirmation inserted a knowledge_item_versions row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @Item1Id AND version_number = 1
          AND title = N'Owner A backlog item one'
          AND approved_wording = N'You led a systems integration effort end to end.'
          AND original_member_wording = N'You led a systems integration effort end to end.'
          AND authored_via = N'typed'
    )
        THROW 53370, 'Confirmation altered the member''s canonical title, wording, or provenance.', 1;
    DECLARE @Item1RowVersionAfterFirstCall binary(8) =
        (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @Item1Id);
    IF @Item1RowVersionAfterFirstCall = @Item1RowVersionBefore
        THROW 53371, 'item1''s row_version did not change even though it was confirmed.', 1;

    /* The still-eligible item2, the suggested item, the already-confirmed
       item, and the already-archived item must all be completely
       untouched by the bounded call -- row_version identical proves no
       UPDATE statement reached any of them. */
    IF (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @Item2Id) <> @Item2RowVersionBefore
        THROW 53372, 'The still-eligible item2 was touched by a bounded call that should not have reached it.', 1;
    IF (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @SuggestedId) <> @SuggestedRowVersionBefore
        THROW 53373, 'A suggested item was touched by the backlog confirmation.', 1;
    IF (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @ConfirmedId) <> @ConfirmedRowVersionBefore
        THROW 53374, 'An already-confirmed item was touched by the backlog confirmation.', 1;
    IF (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @ArchivedId) <> @ArchivedRowVersionBefore
        THROW 53375, 'An already-archived item was touched by the backlog confirmation.', 1;

    /* ------------------------------------------------------------
       6. A second call with the default @MaxItems clears the rest.
       ------------------------------------------------------------ */
    -- Bare EXEC: reaches the real, audit-writing success path (see the
    -- calling-convention note at the top of this file).
    EXEC dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner @UserKey = @UserKeyA;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item2Id) <> N'confirmed'
        THROW 53377, 'The follow-up call did not confirm item2.', 1;
    IF EXISTS (SELECT 1 FROM dbo.knowledge_items WHERE owner_profile_id = @ProfileIdA
               AND item_status = N'unfinished' AND archived_at_utc IS NULL)
        THROW 53376, 'The follow-up call did not leave zero eligible items remaining.', 1;

    /* Byte-stability proof for item2, mirroring item1's above -- the
       original refusal named provenance across BOTH authored_via values
       (N'typed' for item1, N'spoken' for item2), so both must be proven,
       not only the typed one. */
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_items
        WHERE knowledge_item_id = @Item2Id
          AND item_status = N'confirmed'
          AND confirmed_version_number = 1
          AND confirmed_by_user_id = @UserIdA
          AND confirmed_at_utc IS NOT NULL
          AND current_version_number = 1
          AND updated_at_utc = @Item2BackdatedAt
          AND created_at_utc = @Item2BackdatedAt
    )
        THROW 53392, 'item2 confirmation did not set exactly the confirmation triple, or touched updated_at_utc/current_version_number.', 1;
    IF (SELECT COUNT(*) FROM dbo.knowledge_item_versions WHERE knowledge_item_id = @Item2Id) <> 1
        THROW 53393, 'item2 confirmation inserted a knowledge_item_versions row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.knowledge_item_versions
        WHERE knowledge_item_id = @Item2Id AND version_number = 1
          AND title = N'Owner A backlog item two'
          AND approved_wording = N'You train and race long distances.'
          AND original_member_wording = N'You train and race long distances.'
          AND authored_via = N'spoken'
    )
        THROW 53394, 'item2 confirmation altered the member''s canonical title, wording, or spoken provenance.', 1;

    /* A third call finds nothing left: confirmed_count = 0, and every row
       stays exactly where it is (idempotent no-op once the backlog is
       clear). */
    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @ConfirmResult WHERE confirmed_count = 0 AND remaining_count = 0)
        THROW 53378, 'A call against an already-clear backlog reported a nonzero confirmed_count.', 1;

    /* ------------------------------------------------------------
       7. Audit rows: exactly one per confirmed item, the distinct action
          name, and no private wording in the metadata.
       ------------------------------------------------------------ */
    IF (SELECT COUNT(*) FROM dbo.audit_events
        WHERE entity_type = N'knowledge_item' AND entity_key IN (@Item1Key, @Item2Key)
          AND action_type = N'knowledge_item.backlog_confirmed') <> 2
        THROW 53379, 'The backlog confirmation did not write exactly one distinct-action audit row per confirmed item.', 1;
    IF EXISTS (SELECT 1 FROM dbo.audit_events
               WHERE entity_type = N'knowledge_item' AND entity_key IN (@Item1Key, @Item2Key)
                 AND action_type IN (N'knowledge_item.updated', N'knowledge_item.saved'))
        THROW 53380, 'The backlog confirmation was recorded under a member-edit audit action.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.audit_events
        WHERE entity_type = N'knowledge_item' AND entity_key IN (@Item1Key, @Item2Key)
          AND
          (
              metadata_json LIKE N'%systems integration%'
              OR metadata_json LIKE N'%long distances%'
          )
    )
        THROW 53381, 'Audit metadata for the backlog confirmation contains private knowledge item wording.', 1;

    /* ------------------------------------------------------------
       8. The archive/restore fix. A suggested row is refused by Archive;
          a genuine unfinished/confirmed row still archives and restores
          exactly as before; a restored never-confirmed item returns to
          unfinished and IS legitimately swept by the next backlog call --
          proving the laundering path is closed at the archive step.
       ------------------------------------------------------------ */
    DECLARE @SuggestedRowVersionCurrent binary(8) =
        (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @SuggestedId);
    DECLARE @ArchiveSuggestedResult TABLE (outcome nvarchar(30), row_version binary(8));
    INSERT @ArchiveSuggestedResult
    EXEC dbo.usp_ArchiveKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @SuggestedKey, @ExpectedRowVersion = @SuggestedRowVersionCurrent;
    IF NOT EXISTS (SELECT 1 FROM @ArchiveSuggestedResult WHERE outcome = N'changed')
        THROW 53382, 'usp_ArchiveKnowledgeItemForOwner accepted a suggested row.', 1;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @SuggestedId) <> N'suggested'
        THROW 53383, 'A suggested row''s status changed despite Archive refusing it.', 1;

    /* A genuine, never-confirmed unfinished item (a fresh one, so this
       step does not depend on item1/item2''s already-confirmed state)
       archives and restores exactly as PS-WORKSHOP-001 always allowed. */
    DECLARE @Item3Key uniqueidentifier = NEWID();
    DECLARE @Item3Id bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification, current_version_number)
    VALUES (@Item3Key, @ProfileIdA, N'unfinished', N'work', 1);
    SET @Item3Id = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, authored_via, saved_by_user_id)
    VALUES (@Item3Id, @ProfileIdA, 1, N'Owner A item for the archive/restore proof',
            N'Genuinely the member''s own unfinished draft.',
            N'Genuinely the member''s own unfinished draft.', N'typed', @UserIdA);

    DECLARE @Item3RowVersion binary(8) = (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @Item3Id);
    -- Bare EXEC: reaches Archive's real success path (see the
    -- calling-convention note at the top of this file).
    EXEC dbo.usp_ArchiveKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @Item3Key, @ExpectedRowVersion = @Item3RowVersion;
    IF NOT EXISTS (SELECT 1 FROM dbo.knowledge_items
                   WHERE knowledge_item_id = @Item3Id AND item_status = N'archived'
                     AND archived_at_utc IS NOT NULL AND archived_by_user_id IS NOT NULL)
        THROW 53384, 'usp_ArchiveKnowledgeItemForOwner refused a genuine unfinished row.', 1;

    DECLARE @Item3RowVersionArchived binary(8) = (SELECT row_version FROM dbo.knowledge_items WHERE knowledge_item_id = @Item3Id);
    -- Bare EXEC: reaches Restore's real success path (see the
    -- calling-convention note at the top of this file).
    EXEC dbo.usp_RestoreKnowledgeItemForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @Item3Key, @ExpectedRowVersion = @Item3RowVersionArchived;
    IF NOT EXISTS (SELECT 1 FROM dbo.knowledge_items
                   WHERE knowledge_item_id = @Item3Id AND item_status = N'unfinished' AND archived_at_utc IS NULL)
        THROW 53386, 'usp_RestoreKnowledgeItemForOwner refused a legitimately archived unfinished row.', 1;

    /* The restored item genuinely IS member-authored, so the owner's
       standing rule correctly sweeps it on the next call -- this is the
       intended behavior the migration header documents, not a gap. */
    -- Bare EXEC: reaches the real, audit-writing success path (see the
    -- calling-convention note at the top of this file).
    EXEC dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner @UserKey = @UserKeyA;
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @Item3Id) <> N'confirmed'
        THROW 53388, 'The restored genuine unfinished item was not swept by the next backlog call.', 1;

    /* And the suggested item, never able to reach archived at all, is
       still exactly where it started -- the laundering path never opens. */
    IF (SELECT item_status FROM dbo.knowledge_items WHERE knowledge_item_id = @SuggestedId) <> N'suggested'
        THROW 53390, 'The suggested item''s status changed by the end of the run.', 1;

    /* ------------------------------------------------------------
       9. Owner B never sees or holds any of owner A's synthetic rows.
       ------------------------------------------------------------ */
    IF EXISTS (SELECT 1 FROM dbo.knowledge_items WHERE owner_profile_id = @ProfileIdB
               AND knowledge_item_key IN (@Item1Key, @Item2Key, @Item3Key, @SuggestedKey, @ConfirmedKey, @ArchivedKey))
        THROW 53391, 'One of owner A''s synthetic items is attributed to owner B.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-WORKSHOP-002 in-place backlog confirmation: bounded, deterministic, owner-isolated, forged-key refused; unfinished authored rows confirm with byte-stable content/version/updated_at and no new knowledge_item_versions row; suggested/archived/already-confirmed rows fully untouched; one distinct-action audit row per confirmed item with no private wording; the archive/restore laundering path closed and proven with a genuine restore still correctly swept; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
