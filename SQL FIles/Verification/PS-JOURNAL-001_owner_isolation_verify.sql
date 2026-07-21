/* PS-JOURNAL-001 (Slice J1) production-safe verification.
   Uses two synthetic owners inside one outer transaction to prove:
   owner isolation on both the read and the write; idempotent Save
   Moment (a repeated key returns the SAME Moment, a new key creates
   a new one, and the idempotency namespace is scoped per owner, not
   global); derived Journal membership (only confirmed private
   Moments appear, an unconfirmed proposal never does); archived
   exclusion/inclusion; keyset pagination; and no automatic
   publication, placement, or downstream write. Every synthetic row
   is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-JOURNAL-001'
    )
        THROW 52750, 'PS-JOURNAL-001 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:journal-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'journal-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'journal-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'journal-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Journal verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'journal-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Journal verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;

    SELECT
        @UserKeyA = app_user.user_key,
        @UserIdA = app_user.id,
        @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record
      ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile
      ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'journal-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT
        @UserKeyB = app_user.user_key,
        @UserIdB = app_user.id,
        @ProfileIdB = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record
      ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile
      ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'journal-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 52751, 'Synthetic owner provisioning failed.', 1;

    DECLARE @SlateCountA int =
        (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id = @ProfileIdA);
    DECLARE @SlateCountB int =
        (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id = @ProfileIdB);
    DECLARE @PublicationCount int =
    (
        SELECT COUNT(*)
        FROM dbo.entity_publication_versions AS publication
        JOIN dbo.slate_entities AS entity ON entity.entity_id = publication.entity_id
        WHERE entity.owner_profile_id IN (@ProfileIdA, @ProfileIdB)
    );
    DECLARE @RelationCount int =
    (
        SELECT COUNT(*) FROM dbo.slate_entity_relations
        WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)
    );
    DECLARE @PlacementCount int =
    (
        SELECT COUNT(*) FROM dbo.moment_placements
        WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)
    );

    /* ------------------------------------------------------------
       1. Idempotent Save Moment: same key replays to the SAME
          Moment; a different key creates a new one; the same literal
          key string used by two different owners creates two
          independent Moments (per-owner idempotency namespace).
       ------------------------------------------------------------ */
    DECLARE @IdempotencyKeyShared nvarchar(200) = CONCAT(N'journal-key-shared-', @Suffix);
    DECLARE @IdempotencyKeyASecond nvarchar(200) = CONCAT(N'journal-key-a2-', @Suffix);

    DECLARE @TitleA1 nvarchar(160) = CONCAT(N'Owner A first Moment ', LEFT(@Suffix, 20));
    DECLARE @NarrativeA1 nvarchar(500) = CONCAT(N'Owner A first Moment narrative ', @Suffix);
    DECLARE @TitleA1Forged nvarchar(160) = N'Forged replay title must not persist';
    DECLARE @NarrativeA1Forged nvarchar(500) = N'Forged replay narrative must not persist';
    DECLARE @TitleA2 nvarchar(160) = CONCAT(N'Owner A second Moment ', LEFT(@Suffix, 20));
    DECLARE @NarrativeA2 nvarchar(500) = CONCAT(N'Owner A second Moment narrative ', @Suffix);
    DECLARE @TitleB1 nvarchar(160) = CONCAT(N'Owner B shared-key Moment ', LEFT(@Suffix, 20));
    DECLARE @NarrativeB1 nvarchar(500) = CONCAT(N'Owner B shared-key Moment narrative ', @Suffix);

    DECLARE @SaveResult TABLE
    (
        outcome nvarchar(30),
        moment_key uniqueidentifier,
        version_number int,
        row_version binary(8)
    );

    INSERT @SaveResult
    EXEC dbo.usp_SaveMomentForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyShared,
        @MomentKind = N'achievement',
        @Title = @TitleA1,
        @OccurredOn = '2026-07-10',
        @OccurredPrecision = N'exact',
        @Narrative = @NarrativeA1,
        @WhyItMatters = NULL;

    DECLARE @MomentKeyA1 uniqueidentifier;
    DECLARE @VersionA1 int;
    SELECT TOP (1) @MomentKeyA1 = moment_key, @VersionA1 = version_number
    FROM @SaveResult;

    IF @MomentKeyA1 IS NULL OR @VersionA1 <> 1
        THROW 52752, 'Owner A first Save Moment did not create a confirmed Moment.', 1;

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveMomentForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyShared,
        @MomentKind = N'lesson',
        @Title = @TitleA1Forged,
        @OccurredOn = '2020-01-01',
        @OccurredPrecision = N'exact',
        @Narrative = @NarrativeA1Forged,
        @WhyItMatters = N'Forged replay context';

    DECLARE @ReplayMomentKeyA1 uniqueidentifier;
    DECLARE @ReplayOutcome nvarchar(30);
    SELECT TOP (1) @ReplayMomentKeyA1 = moment_key, @ReplayOutcome = outcome
    FROM @SaveResult;

    IF @ReplayOutcome <> N'existing' OR @ReplayMomentKeyA1 <> @MomentKeyA1
        THROW 52753, 'A repeated idempotency key did not return the same Moment.', 1;

    DECLARE @MomentIdA1 bigint;
    SELECT @MomentIdA1 = moment_id FROM dbo.moments WHERE moment_key = @MomentKeyA1;

    IF (SELECT COUNT(*) FROM dbo.moments WHERE owner_profile_id = @ProfileIdA) <> 1
        THROW 52754, 'A replayed Save Moment created a second Moment.', 1;
    IF (SELECT COUNT(*) FROM dbo.moment_versions WHERE moment_id = @MomentIdA1) <> 1
        THROW 52755, 'A replayed Save Moment created an extra version.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.moment_versions
        WHERE moment_id = @MomentIdA1
          AND (title = @TitleA1Forged OR narrative = @NarrativeA1Forged)
    )
        THROW 52756, 'A replayed Save Moment overwrote the original canonical content.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_versions
        WHERE moment_id = @MomentIdA1
          AND title = @TitleA1
          AND narrative = @NarrativeA1
    )
        THROW 52757, 'The original Save Moment content did not persist.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.moment_save_requests
        WHERE owner_profile_id = @ProfileIdA AND idempotency_key = @IdempotencyKeyShared
    ) <> 1
        THROW 52758, 'The idempotency ledger recorded more than one replay row.', 1;

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveMomentForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyASecond,
        @MomentKind = N'progress',
        @Title = @TitleA2,
        @OccurredOn = '2026-06-15',
        @OccurredPrecision = N'month',
        @Narrative = @NarrativeA2,
        @WhyItMatters = NULL;

    DECLARE @MomentKeyA2 uniqueidentifier;
    SELECT TOP (1) @MomentKeyA2 = moment_key FROM @SaveResult;

    IF @MomentKeyA2 IS NULL OR @MomentKeyA2 = @MomentKeyA1
        THROW 52759, 'A distinct idempotency key did not create a distinct second Moment.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_versions
        WHERE moment_id = (SELECT moment_id FROM dbo.moments WHERE moment_key = @MomentKeyA2)
          AND occurred_on = '2026-06-01'
          AND occurred_precision = N'month'
    )
        THROW 52760, 'Month-precision Save Moment did not normalize to the first of the month.', 1;

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveMomentForOwner
        @UserKey = @UserKeyB,
        @IdempotencyKey = @IdempotencyKeyShared,
        @MomentKind = N'decision',
        @Title = @TitleB1,
        @OccurredOn = '2026-05-01',
        @OccurredPrecision = N'exact',
        @Narrative = @NarrativeB1,
        @WhyItMatters = NULL;

    DECLARE @MomentKeyB1 uniqueidentifier;
    SELECT TOP (1) @MomentKeyB1 = moment_key FROM @SaveResult;

    IF @MomentKeyB1 IS NULL OR @MomentKeyB1 = @MomentKeyA1 OR @MomentKeyB1 = @MomentKeyA2
        THROW 52761, 'The same idempotency-key literal collided across two different owners.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.moment_save_requests
        WHERE idempotency_key = @IdempotencyKeyShared
    ) <> 2
        THROW 52762, 'The per-owner idempotency ledger did not scope by owner.', 1;

    /* ------------------------------------------------------------
       2. Derived membership: an unconfirmed Capture-review proposal
          must never appear in the Journal read.
       ------------------------------------------------------------ */
    DECLARE @ProposalSource nvarchar(300) = CONCAT(N'Owner A unrelated capture ', @Suffix);
    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA, @CaptureType = N'text', @Body = @ProposalSource;

    DECLARE @ProposalCaptureKey uniqueidentifier;
    SELECT @ProposalCaptureKey = capture_key
    FROM dbo.captures
    WHERE owner_profile_id = @ProfileIdA AND body = @ProposalSource;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyA,
        @CaptureKey = @ProposalCaptureKey,
        @SourceRevisionNumber = 0;

    DECLARE @UnconfirmedMomentKey uniqueidentifier;
    SELECT @UnconfirmedMomentKey = moment.moment_key
    FROM dbo.moments AS moment
    JOIN dbo.moment_sources AS source_link ON source_link.moment_id = moment.moment_id
    WHERE moment.owner_profile_id = @ProfileIdA
      AND source_link.source_capture_key = @ProposalCaptureKey;

    IF @UnconfirmedMomentKey IS NULL
        THROW 52763, 'The unconfirmed proposal fixture was not created.', 1;

    /* ------------------------------------------------------------
       3. Archive lifecycle: excluded by default, included on request.
          (No archive-toggle procedure exists yet in Slice J1; this
          simulates the future action directly on the additive
          columns to prove the read filter's shape now.)
       ------------------------------------------------------------ */
    UPDATE dbo.moments
    SET archived_at_utc = SYSUTCDATETIME(), archived_by_user_id = @UserIdA
    WHERE moment_id = (SELECT moment_id FROM dbo.moments WHERE moment_key = @MomentKeyA2);

    /* ------------------------------------------------------------
       4. Owner-isolated derived read, default archived-excluded view.
       ------------------------------------------------------------ */
    DECLARE @JournalRead TABLE
    (
        moment_key uniqueidentifier,
        moment_kind nvarchar(30),
        title nvarchar(160),
        occurred_on date,
        occurred_precision nvarchar(20),
        visibility nvarchar(30),
        source_type nvarchar(30),
        lifecycle_state nvarchar(20),
        version_number int,
        cursor_token nvarchar(80)
    );

    INSERT @JournalRead
    EXEC dbo.usp_ListJournalMomentsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 0, @Limit = 50, @Cursor = NULL;

    IF (SELECT COUNT(*) FROM @JournalRead) <> 1
        THROW 52764, 'Default owner A Journal read did not exclude proposal and archived rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @JournalRead WHERE moment_key = @MomentKeyA1)
        THROW 52765, 'Owner A confirmed active Moment is missing from the default Journal read.', 1;
    IF EXISTS (SELECT 1 FROM @JournalRead WHERE moment_key = @MomentKeyA2)
        THROW 52766, 'An archived Moment leaked into the default Journal read.', 1;
    IF EXISTS (SELECT 1 FROM @JournalRead WHERE moment_key = @UnconfirmedMomentKey)
        THROW 52767, 'An unconfirmed proposal leaked into the Journal read.', 1;
    IF EXISTS (SELECT 1 FROM @JournalRead WHERE moment_key IN (@MomentKeyB1))
        THROW 52768, 'Cross-owner Moment leaked into the owner A Journal read.', 1;

    DELETE @JournalRead;
    INSERT @JournalRead
    EXEC dbo.usp_ListJournalMomentsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 1, @Limit = 50, @Cursor = NULL;

    IF (SELECT COUNT(*) FROM @JournalRead) <> 2
        THROW 52769, 'Including archived Moments did not return both owner A Moments.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @JournalRead
        WHERE moment_key = @MomentKeyA2 AND lifecycle_state = N'archived'
    )
        THROW 52770, 'The archived Moment was not reported with lifecycle_state = archived.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @JournalRead
        WHERE moment_key = @MomentKeyA1 AND lifecycle_state = N'active'
    )
        THROW 52771, 'The active Moment was not reported with lifecycle_state = active.', 1;
    IF EXISTS (SELECT 1 FROM @JournalRead WHERE source_type IS NULL OR source_type <> N'text')
        THROW 52772, 'The Journal read did not report the underlying Capture source type.', 1;

    /* ------------------------------------------------------------
       5. Keyset pagination: one row per page, no overlap, and the
          two pages together equal the unpaged archived-included set.
       ------------------------------------------------------------ */
    DECLARE @PageOne TABLE
    (
        moment_key uniqueidentifier, moment_kind nvarchar(30), title nvarchar(160),
        occurred_on date, occurred_precision nvarchar(20), visibility nvarchar(30),
        source_type nvarchar(30), lifecycle_state nvarchar(20), version_number int,
        cursor_token nvarchar(80)
    );
    INSERT @PageOne
    EXEC dbo.usp_ListJournalMomentsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 1, @Limit = 1, @Cursor = NULL;

    IF (SELECT COUNT(*) FROM @PageOne) <> 1
        THROW 52773, 'The first page of the Journal read did not honor @Limit = 1.', 1;

    DECLARE @PageOneMomentKey uniqueidentifier = (SELECT TOP (1) moment_key FROM @PageOne);
    DECLARE @PageOneCursor nvarchar(80) = (SELECT TOP (1) cursor_token FROM @PageOne);

    IF @PageOneMomentKey <> @MomentKeyA1
        THROW 52774, 'The Journal read page order is not deterministic by display time then key.', 1;

    DECLARE @PageTwo TABLE
    (
        moment_key uniqueidentifier, moment_kind nvarchar(30), title nvarchar(160),
        occurred_on date, occurred_precision nvarchar(20), visibility nvarchar(30),
        source_type nvarchar(30), lifecycle_state nvarchar(20), version_number int,
        cursor_token nvarchar(80)
    );
    INSERT @PageTwo
    EXEC dbo.usp_ListJournalMomentsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 1, @Limit = 1, @Cursor = @PageOneCursor;

    IF (SELECT COUNT(*) FROM @PageTwo) <> 1
        THROW 52775, 'The second Journal read page did not return the remaining Moment.', 1;
    IF (SELECT TOP (1) moment_key FROM @PageTwo) <> @MomentKeyA2
        THROW 52776, 'Keyset pagination did not advance past the first page cursor.', 1;

    /* ------------------------------------------------------------
       6. Reverse-direction owner isolation on the read.
       ------------------------------------------------------------ */
    DECLARE @JournalReadB TABLE
    (
        moment_key uniqueidentifier, moment_kind nvarchar(30), title nvarchar(160),
        occurred_on date, occurred_precision nvarchar(20), visibility nvarchar(30),
        source_type nvarchar(30), lifecycle_state nvarchar(20), version_number int,
        cursor_token nvarchar(80)
    );
    INSERT @JournalReadB
    EXEC dbo.usp_ListJournalMomentsForOwner
        @UserKey = @UserKeyB, @IncludeArchived = 1, @Limit = 50, @Cursor = NULL;

    IF (SELECT COUNT(*) FROM @JournalReadB) <> 1
        OR NOT EXISTS (SELECT 1 FROM @JournalReadB WHERE moment_key = @MomentKeyB1)
        THROW 52777, 'Owner B Journal read did not return exactly owner B''s own Moment.', 1;
    IF EXISTS
    (
        SELECT 1 FROM @JournalReadB
        WHERE moment_key IN (@MomentKeyA1, @MomentKeyA2, @UnconfirmedMomentKey)
    )
        THROW 52778, 'Cross-owner Moment leaked into the owner B Journal read.', 1;

    /* ------------------------------------------------------------
       7. A forged/unresolvable owner never resolves any row or Moment.
       ------------------------------------------------------------ */
    DECLARE @JournalReadForged TABLE
    (
        moment_key uniqueidentifier, moment_kind nvarchar(30), title nvarchar(160),
        occurred_on date, occurred_precision nvarchar(20), visibility nvarchar(30),
        source_type nvarchar(30), lifecycle_state nvarchar(20), version_number int,
        cursor_token nvarchar(80)
    );
    INSERT @JournalReadForged
    EXEC dbo.usp_ListJournalMomentsForOwner
        @UserKey = N'forged-user-key-does-not-exist',
        @IncludeArchived = 1, @Limit = 50, @Cursor = NULL;

    IF EXISTS (SELECT 1 FROM @JournalReadForged)
        THROW 52779, 'A forged UserKey returned rows from the Journal read.', 1;

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveMomentForOwner
        @UserKey = N'forged-user-key-does-not-exist',
        @IdempotencyKey = CONCAT(N'journal-key-forged-', @Suffix),
        @MomentKind = N'other',
        @Title = N'Forged owner Save Moment',
        @OccurredOn = NULL,
        @OccurredPrecision = N'unknown',
        @Narrative = N'Forged owner Save Moment must fail truthfully',
        @WhyItMatters = NULL;

    IF EXISTS (SELECT 1 FROM @SaveResult WHERE outcome <> N'not_found' OR moment_key IS NOT NULL)
        THROW 52780, 'A forged UserKey produced a truthful-looking Save Moment outcome.', 1;
    IF EXISTS (SELECT 1 FROM dbo.moments WHERE owner_profile_id NOT IN (@ProfileIdA, @ProfileIdB))
        THROW 52781, 'A forged-owner Save Moment call created an orphaned Moment.', 1;

    /* ------------------------------------------------------------
       8. No automatic publication, placement, or downstream write.
       ------------------------------------------------------------ */
    IF (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id = @ProfileIdA) <> @SlateCountA
       OR (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id = @ProfileIdB) <> @SlateCountB
       OR
       (
           SELECT COUNT(*)
           FROM dbo.entity_publication_versions AS publication
           JOIN dbo.slate_entities AS entity ON entity.entity_id = publication.entity_id
           WHERE entity.owner_profile_id IN (@ProfileIdA, @ProfileIdB)
       ) <> @PublicationCount
       OR
       (
           SELECT COUNT(*) FROM dbo.slate_entity_relations
           WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)
       ) <> @RelationCount
       OR
       (
           SELECT COUNT(*) FROM dbo.moment_placements
           WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)
       ) <> @PlacementCount
        THROW 52782, 'Save Moment or the Journal read automatically published or placed content.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE moment_key IN (@MomentKeyA1, @MomentKeyA2, @MomentKeyB1)
          AND (visibility <> N'private' OR status <> N'confirmed')
    )
        THROW 52783, 'A Save Moment result was not private and confirmed.', 1;

    /* ------------------------------------------------------------
       9. No private content in audit metadata, and no second body
          column anywhere in the new idempotency ledger.
       ------------------------------------------------------------ */
    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.action_type = N'journal.moment.saved'
          AND audit_event.entity_key IN (@MomentKeyA1, @MomentKeyA2, @MomentKeyB1)
          AND
          (
              audit_event.metadata_json LIKE N'%' + @TitleA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @NarrativeA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @TitleA2 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @NarrativeA2 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @TitleB1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @NarrativeB1 + N'%'
          )
    )
        THROW 52784, 'Audit metadata contains private Moment content.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.moment_save_requests')
          AND name IN (N'title', N'narrative', N'why_it_matters', N'body')
    )
        THROW 52785, 'The idempotency ledger contains a body/content column.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-JOURNAL-001 two-owner isolation, per-owner idempotent Save Moment, derived confirmed-only Journal membership, archive filter, keyset pagination, no automatic publication/placement, and synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
