/* PS-MOMENT-001 production-safe verification.
   Uses two synthetic owners inside one outer transaction to prove owner
   isolation, proposal versioning, explicit confirmation, source pinning,
   deterministic body-free deletion propagation, and no automatic
   publication or placement. Every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-MOMENT-001'
    )
        THROW 52250, 'PS-MOMENT-001 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:moment-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'moment-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'moment-b-', @Suffix);
    DECLARE @OriginalA nvarchar(300) = CONCAT(N'Owner A original source ', @Suffix);
    DECLARE @CorrectionA1 nvarchar(300) = CONCAT(N'Owner A correction one ', @Suffix);
    DECLARE @CorrectionA2 nvarchar(300) = CONCAT(N'Owner A correction two ', @Suffix);
    DECLARE @OriginalB nvarchar(300) = CONCAT(N'Owner B original source ', @Suffix);
    DECLARE @DiscardSource nvarchar(300) = CONCAT(N'Owner A discard source ', @Suffix);
    DECLARE @CanonicalTitleA nvarchar(160) = CONCAT(N'Owner A approved title ', LEFT(@Suffix, 20));
    DECLARE @CanonicalNarrativeA nvarchar(500) = CONCAT(N'Owner A approved canonical narrative ', @Suffix);
    DECLARE @CanonicalNarrativeB nvarchar(500) = CONCAT(N'Owner B unconfirmed canonical narrative ', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'moment-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Moment verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'moment-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Moment verification owner B';

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
    WHERE identity_record.provider = N'moment-verification'
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
    WHERE identity_record.provider = N'moment-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 52251, 'Synthetic owner provisioning failed.', 1;

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

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA, @CaptureType = N'text', @Body = @OriginalA;
    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyB, @CaptureType = N'text', @Body = @OriginalB;
    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA, @CaptureType = N'text', @Body = @DiscardSource;

    DECLARE @CaptureIdA bigint;
    DECLARE @CaptureIdB bigint;
    DECLARE @CaptureIdDiscard bigint;
    DECLARE @CaptureKeyA uniqueidentifier;
    DECLARE @CaptureKeyB uniqueidentifier;
    DECLARE @CaptureKeyDiscard uniqueidentifier;
    DECLARE @CaptureVersionA binary(8);
    DECLARE @CaptureVersionB binary(8);

    SELECT
        @CaptureIdA = capture.capture_id,
        @CaptureKeyA = capture.capture_key,
        @CaptureVersionA = capture.row_version
    FROM dbo.captures AS capture
    WHERE capture.owner_profile_id = @ProfileIdA AND capture.body = @OriginalA;

    SELECT
        @CaptureIdB = capture.capture_id,
        @CaptureKeyB = capture.capture_key,
        @CaptureVersionB = capture.row_version
    FROM dbo.captures AS capture
    WHERE capture.owner_profile_id = @ProfileIdB AND capture.body = @OriginalB;

    SELECT
        @CaptureIdDiscard = capture.capture_id,
        @CaptureKeyDiscard = capture.capture_key
    FROM dbo.captures AS capture
    WHERE capture.owner_profile_id = @ProfileIdA AND capture.body = @DiscardSource;

    IF @CaptureIdA IS NULL OR @CaptureIdB IS NULL OR @CaptureIdDiscard IS NULL
        THROW 52252, 'Synthetic Captures were not created.', 1;

    EXEC dbo.usp_CorrectCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersionA,
        @CorrectedBody = @CorrectionA1,
        @CorrectionNote = NULL;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.capture_revisions
        WHERE capture_id = @CaptureIdA
          AND revision_number = 1
          AND body = @CorrectionA1
    )
        THROW 52253, 'Pinned correction source was not created.', 1;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @SourceRevisionNumber = 1;

    DECLARE @MomentIdA bigint;
    DECLARE @MomentKeyA uniqueidentifier;
    DECLARE @MomentVersionA binary(8);
    SELECT
        @MomentIdA = moment.moment_id,
        @MomentKeyA = moment.moment_key,
        @MomentVersionA = moment.row_version
    FROM dbo.moments AS moment
    JOIN dbo.moment_sources AS source_link ON source_link.moment_id = moment.moment_id
    WHERE moment.owner_profile_id = @ProfileIdA
      AND source_link.source_capture_key = @CaptureKeyA
      AND source_link.source_revision_number = 1;

    IF @MomentIdA IS NULL OR @MomentKeyA IS NULL
        THROW 52254, 'Owner A Moment proposal was not created.', 1;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @SourceRevisionNumber = 1;

    IF
    (
        SELECT COUNT(*)
        FROM dbo.moment_sources
        WHERE owner_profile_id = @ProfileIdA
          AND source_capture_key = @CaptureKeyA
          AND source_revision_number = 1
    ) <> 1
        THROW 52255, 'Proposal creation was not idempotent for the pinned source.', 1;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyA,
        @SourceRevisionNumber = 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.moment_sources
        WHERE owner_profile_id = @ProfileIdB
          AND source_capture_key = @CaptureKeyA
    )
        THROW 52256, 'Cross-owner source selection created a foreign proposal.', 1;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @SourceRevisionNumber = 0;

    DECLARE @MomentIdB bigint;
    DECLARE @MomentKeyB uniqueidentifier;
    DECLARE @MomentVersionB binary(8);
    SELECT
        @MomentIdB = moment.moment_id,
        @MomentKeyB = moment.moment_key,
        @MomentVersionB = moment.row_version
    FROM dbo.moments AS moment
    JOIN dbo.moment_sources AS source_link ON source_link.moment_id = moment.moment_id
    WHERE moment.owner_profile_id = @ProfileIdB
      AND source_link.source_capture_key = @CaptureKeyB
      AND source_link.source_revision_number = 0;

    IF @MomentIdB IS NULL OR @MomentKeyB IS NULL OR @MomentIdB = @MomentIdA
        THROW 52257, 'Two-owner Moment creation failed.', 1;

    DECLARE @MomentRead TABLE
    (
        moment_key uniqueidentifier,
        visibility nvarchar(30),
        status nvarchar(30),
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        moment_kind nvarchar(30),
        title nvarchar(160),
        occurred_on date,
        occurred_precision nvarchar(20),
        narrative nvarchar(max),
        why_it_matters nvarchar(2000),
        moment_source_key uniqueidentifier,
        source_capture_key uniqueidentifier,
        source_revision_key uniqueidentifier,
        source_revision_number int,
        source_state nvarchar(20),
        source_deleted_at_utc datetime2(7),
        source_body nvarchar(max),
        latest_source_revision_number int,
        newer_source_available bit,
        can_confirm bit
    );

    INSERT @MomentRead
    EXEC dbo.usp_GetMomentForOwner
        @UserKey = @UserKeyB, @MomentKey = @MomentKeyA;

    IF EXISTS (SELECT 1 FROM @MomentRead)
        THROW 52258, 'Cross-owner Moment read exposed private content.', 1;

    INSERT @MomentRead
    EXEC dbo.usp_GetMomentForOwner
        @UserKey = @UserKeyA, @MomentKey = @MomentKeyB;

    IF EXISTS (SELECT 1 FROM @MomentRead)
        THROW 52259, 'Reverse cross-owner Moment read exposed private content.', 1;

    EXEC dbo.usp_SaveMomentProposal
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA,
        @MomentKind = N'achievement',
        @Title = N'Forged cross-owner title',
        @OccurredOn = '2026-07-18',
        @OccurredPrecision = N'exact',
        @Narrative = N'Forged cross-owner narrative',
        @WhyItMatters = NULL;

    IF (SELECT COUNT(*) FROM dbo.moment_versions WHERE moment_id = @MomentIdA) <> 1
        THROW 52260, 'Cross-owner proposal edit was not denied.', 1;

    EXEC dbo.usp_ConfirmMoment
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA,
        @ExpectedProposalVersion = 1;

    EXEC dbo.usp_DiscardMomentProposal
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE moment_id = @MomentIdA
          AND status = N'proposal'
          AND row_version = @MomentVersionA
    )
        THROW 52261, 'Cross-owner confirm or discard changed owner A Moment.', 1;

    EXEC dbo.usp_SaveMomentProposal
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA,
        @MomentKind = N'achievement',
        @Title = @CanonicalTitleA,
        @OccurredOn = '2026-07-18',
        @OccurredPrecision = N'exact',
        @Narrative = @CanonicalNarrativeA,
        @WhyItMatters = N'Member-approved context';

    DECLARE @SavedMomentVersionA binary(8) =
        (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdA);

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.moments AS moment
        JOIN dbo.moment_versions AS version_record
          ON version_record.moment_id = moment.moment_id
         AND version_record.version_number = moment.current_version_number
        WHERE moment.moment_id = @MomentIdA
          AND moment.current_version_number = 2
          AND moment.visibility = N'private'
          AND moment.status = N'proposal'
          AND version_record.title = @CanonicalTitleA
          AND version_record.narrative = @CanonicalNarrativeA
    )
        THROW 52262, 'Owner proposal save/versioning failed.', 1;

    EXEC dbo.usp_SaveMomentProposal
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA,
        @MomentKind = N'lesson',
        @Title = N'Stale title',
        @OccurredOn = NULL,
        @OccurredPrecision = N'unknown',
        @Narrative = N'Stale narrative must not persist',
        @WhyItMatters = NULL;

    IF (SELECT COUNT(*) FROM dbo.moment_versions WHERE moment_id = @MomentIdA) <> 2
        THROW 52263, 'Stale row version created a proposal version.', 1;

    EXEC dbo.usp_ConfirmMoment
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @SavedMomentVersionA,
        @ExpectedProposalVersion = 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE moment_id = @MomentIdA AND status = N'confirmed'
    )
        THROW 52264, 'Stale proposal version was confirmed.', 1;

    EXEC dbo.usp_ConfirmMoment
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @SavedMomentVersionA,
        @ExpectedProposalVersion = 2;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE moment_id = @MomentIdA
          AND status = N'confirmed'
          AND visibility = N'private'
          AND confirmed_version_number = 2
          AND confirmed_by_user_id = @UserIdA
          AND confirmed_at_utc IS NOT NULL
    )
        THROW 52265, 'Explicit confirmation did not create a private canonical Moment.', 1;

    SET @CaptureVersionA =
        (SELECT row_version FROM dbo.captures WHERE capture_id = @CaptureIdA);
    EXEC dbo.usp_CorrectCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersionA,
        @CorrectedBody = @CorrectionA2,
        @CorrectionNote = NULL;

    DELETE @MomentRead;
    INSERT @MomentRead
    EXEC dbo.usp_GetMomentForOwner
        @UserKey = @UserKeyA, @MomentKey = @MomentKeyA;

    IF NOT EXISTS
    (
        SELECT 1 FROM @MomentRead
        WHERE source_revision_number = 1
          AND source_body = @CorrectionA1
          AND latest_source_revision_number = 2
          AND newer_source_available = 1
          AND narrative = @CanonicalNarrativeA
          AND status = N'confirmed'
    )
        THROW 52266, 'Later Capture correction silently changed or obscured the pinned Moment.', 1;

    EXEC dbo.usp_SaveMomentProposal
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyB,
        @ExpectedRowVersion = @MomentVersionB,
        @MomentKind = N'lesson',
        @Title = N'Owner B private proposal',
        @OccurredOn = NULL,
        @OccurredPrecision = N'unknown',
        @Narrative = @CanonicalNarrativeB,
        @WhyItMatters = NULL;

    SET @MomentVersionB =
        (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdB);

    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @CaptureVersionB;

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.moment_sources AS source_link
        JOIN dbo.moments AS moment ON moment.moment_id = source_link.moment_id
        WHERE source_link.moment_id = @MomentIdB
          AND source_link.owner_profile_id = @ProfileIdB
          AND source_link.source_state = N'deleted'
          AND source_link.source_deleted_at_utc IS NOT NULL
          AND source_link.capture_id IS NULL
          AND source_link.capture_revision_id IS NULL
          AND source_link.source_capture_key = @CaptureKeyB
          AND moment.status = N'proposal'
    )
        THROW 52267, 'Unconfirmed source deletion did not create a body-free tombstone.', 1;

    EXEC dbo.usp_ConfirmMoment
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyB,
        @ExpectedRowVersion = @MomentVersionB,
        @ExpectedProposalVersion = 2;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE moment_id = @MomentIdB AND status = N'confirmed'
    )
        THROW 52268, 'A source-deleted unconfirmed proposal was confirmed.', 1;

    SET @CaptureVersionA =
        (SELECT row_version FROM dbo.captures WHERE capture_id = @CaptureIdA);
    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersionA;

    DELETE @MomentRead;
    INSERT @MomentRead
    EXEC dbo.usp_GetMomentForOwner
        @UserKey = @UserKeyA, @MomentKey = @MomentKeyA;

    IF NOT EXISTS
    (
        SELECT 1 FROM @MomentRead
        WHERE status = N'confirmed'
          AND visibility = N'private'
          AND narrative = @CanonicalNarrativeA
          AND title = @CanonicalTitleA
          AND source_state = N'deleted'
          AND source_body IS NULL
          AND source_deleted_at_utc IS NOT NULL
    )
        THROW 52269, 'Confirmed canonical content or source-deleted reporting is incorrect.', 1;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyDiscard,
        @SourceRevisionNumber = 0;

    DECLARE @DiscardMomentId bigint;
    DECLARE @DiscardMomentKey uniqueidentifier;
    DECLARE @DiscardMomentVersion binary(8);
    SELECT
        @DiscardMomentId = moment.moment_id,
        @DiscardMomentKey = moment.moment_key,
        @DiscardMomentVersion = moment.row_version
    FROM dbo.moments AS moment
    JOIN dbo.moment_sources AS source_link ON source_link.moment_id = moment.moment_id
    WHERE source_link.source_capture_key = @CaptureKeyDiscard
      AND source_link.owner_profile_id = @ProfileIdA;

    EXEC dbo.usp_DiscardMomentProposal
        @UserKey = @UserKeyA,
        @MomentKey = @DiscardMomentKey,
        @ExpectedRowVersion = @DiscardMomentVersion;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moments WHERE moment_id = @DiscardMomentId
        UNION ALL
        SELECT 1 FROM dbo.moment_versions WHERE moment_id = @DiscardMomentId
        UNION ALL
        SELECT 1 FROM dbo.moment_sources WHERE moment_id = @DiscardMomentId
    )
        THROW 52270, 'Discarded proposal content or source relationship remained.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.moment_sources')
          AND name IN (N'body', N'source_body', N'narrative', N'correction_note')
    )
        THROW 52271, 'Moment source tombstones contain a body/content column.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.entity_key IN
              (@CaptureKeyA, @CaptureKeyB, @MomentKeyA, @MomentKeyB, @DiscardMomentKey)
          AND
          (
              audit_event.metadata_json LIKE N'%' + @OriginalA + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CorrectionA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CorrectionA2 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @OriginalB + N'%'
              OR audit_event.metadata_json LIKE N'%' + @DiscardSource + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CanonicalTitleA + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CanonicalNarrativeA + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CanonicalNarrativeB + N'%'
          )
    )
        THROW 52272, 'Audit metadata contains private Capture or Moment content.', 1;

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
        THROW 52273, 'Moment review automatically published, placed, or wrote downstream.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)
          AND visibility <> N'private'
    )
        THROW 52274, 'Moment proposal or confirmation changed private visibility.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-MOMENT-001 two-owner isolation, source pinning, concurrency, deletion tombstones, explicit private confirmation, no automatic publication/placement, and synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
