/* PS-PLACEMENT-001 production-safe verification.
   Uses two synthetic owners inside one outer transaction to prove exact
   confirmed-version pinning, deleted-source eligibility, owner isolation,
   destination-state enforcement, stale-token rejection, remove/reactivate,
   body-free persistence/audit, and no downstream side effects. Every
   synthetic row and content sentinel is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-PLACEMENT-001'
    )
        THROW 52350, 'PS-PLACEMENT-001 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:placement-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'placement-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'placement-b-', @Suffix);
    DECLARE @SourceSentinelA nvarchar(300) = CONCAT(N'PLACEMENT_SOURCE_SENTINEL_A_', @Suffix);
    DECLARE @SourceSentinelB nvarchar(300) = CONCAT(N'PLACEMENT_SOURCE_SENTINEL_B_', @Suffix);
    DECLARE @TitleSentinelA nvarchar(160) = CONCAT(N'PLACEMENT_TITLE_SENTINEL_A_', LEFT(@Suffix, 24));
    DECLARE @NarrativeSentinelA nvarchar(500) = CONCAT(N'PLACEMENT_NARRATIVE_SENTINEL_A_', @Suffix);
    DECLARE @NarrativeSentinelB nvarchar(500) = CONCAT(N'PLACEMENT_NARRATIVE_SENTINEL_B_', @Suffix);
    DECLARE @TargetSentinelA nvarchar(100) = CONCAT(N'PLACEMENT_TARGET_SENTINEL_A_', LEFT(@Suffix, 30));

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'placement-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Placement verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'placement-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Placement verification owner B';

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
    WHERE identity_record.provider = N'placement-verification'
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
    WHERE identity_record.provider = N'placement-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 52351, 'Synthetic owner provisioning failed.', 1;

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA, @CaptureType = N'text', @Body = @SourceSentinelA;
    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyB, @CaptureType = N'text', @Body = @SourceSentinelB;

    DECLARE @CaptureKeyA uniqueidentifier;
    DECLARE @CaptureKeyB uniqueidentifier;
    DECLARE @CaptureVersionA binary(8);
    DECLARE @CaptureVersionB binary(8);

    SELECT @CaptureKeyA = capture_key, @CaptureVersionA = row_version
    FROM dbo.captures
    WHERE owner_profile_id = @ProfileIdA AND body = @SourceSentinelA;

    SELECT @CaptureKeyB = capture_key, @CaptureVersionB = row_version
    FROM dbo.captures
    WHERE owner_profile_id = @ProfileIdB AND body = @SourceSentinelB;

    IF @CaptureKeyA IS NULL OR @CaptureKeyB IS NULL
        THROW 52352, 'Synthetic Capture provisioning failed.', 1;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @SourceRevisionNumber = 0;

    EXEC dbo.usp_CreateOrReopenMomentProposal
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @SourceRevisionNumber = 0;

    DECLARE @MomentIdA bigint;
    DECLARE @MomentIdB bigint;
    DECLARE @MomentKeyA uniqueidentifier;
    DECLARE @MomentKeyB uniqueidentifier;
    DECLARE @MomentVersionA binary(8);
    DECLARE @MomentVersionB binary(8);

    SELECT
        @MomentIdA = moment.moment_id,
        @MomentKeyA = moment.moment_key,
        @MomentVersionA = moment.row_version
    FROM dbo.moments AS moment
    JOIN dbo.moment_sources AS source_link ON source_link.moment_id = moment.moment_id
    WHERE moment.owner_profile_id = @ProfileIdA
      AND source_link.source_capture_key = @CaptureKeyA;

    SELECT
        @MomentIdB = moment.moment_id,
        @MomentKeyB = moment.moment_key,
        @MomentVersionB = moment.row_version
    FROM dbo.moments AS moment
    JOIN dbo.moment_sources AS source_link ON source_link.moment_id = moment.moment_id
    WHERE moment.owner_profile_id = @ProfileIdB
      AND source_link.source_capture_key = @CaptureKeyB;

    EXEC dbo.usp_SaveMomentProposal
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA,
        @MomentKind = N'achievement',
        @Title = @TitleSentinelA,
        @OccurredOn = '2026-07-18',
        @OccurredPrecision = N'exact',
        @Narrative = @NarrativeSentinelA,
        @WhyItMatters = NULL;

    EXEC dbo.usp_SaveMomentProposal
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyB,
        @ExpectedRowVersion = @MomentVersionB,
        @MomentKind = N'lesson',
        @Title = N'Owner B proposal title',
        @OccurredOn = NULL,
        @OccurredPrecision = N'unknown',
        @Narrative = @NarrativeSentinelB,
        @WhyItMatters = NULL;

    SET @MomentVersionA = (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdA);
    SET @MomentVersionB = (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdB);
    DECLARE @StaleMomentVersionA binary(8) = @MomentVersionA;

    EXEC dbo.usp_ConfirmMoment
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @ExpectedRowVersion = @MomentVersionA,
        @ExpectedProposalVersion = 2;

    SET @MomentVersionA = (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdA);

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moments
        WHERE moment_id = @MomentIdA
          AND status = N'confirmed'
          AND visibility = N'private'
          AND confirmed_version_number = 2
    )
        THROW 52353, 'Synthetic confirmed Moment was not created.', 1;

    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @CaptureVersionA;

    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @CaptureVersionB;

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.moment_sources AS source_link
        JOIN dbo.moments AS moment ON moment.moment_id = source_link.moment_id
        WHERE source_link.moment_id = @MomentIdA
          AND source_link.source_state = N'deleted'
          AND moment.status = N'confirmed'
    )
       OR NOT EXISTS
       (
           SELECT 1
           FROM dbo.moment_sources AS source_link
           JOIN dbo.moments AS moment ON moment.moment_id = source_link.moment_id
           WHERE source_link.moment_id = @MomentIdB
             AND source_link.source_state = N'deleted'
             AND moment.status = N'proposal'
       )
        THROW 52354, 'Synthetic source-deletion states were not established.', 1;

    DECLARE @EligibleTargetKeyA uniqueidentifier = NEWID();
    DECLARE @EligibleTargetKeyB uniqueidentifier = NEWID();
    DECLARE @DraftTargetKeyA uniqueidentifier = NEWID();
    DECLARE @SharedTargetKeyA uniqueidentifier = NEWID();
    DECLARE @PublishedTargetKeyA uniqueidentifier = NEWID();
    DECLARE @InactiveTargetKeyA uniqueidentifier = NEWID();
    DECLARE @DeletedTargetKeyA uniqueidentifier = NEWID();

    INSERT dbo.slate_entities
    (
        entity_key, owner_profile_id, entity_type, source_schema,
        source_table, source_record_id, visibility, approval_status,
        publication_status, active, deleted_at_utc
    )
    VALUES
        (@EligibleTargetKeyA, @ProfileIdA, N'placement_test', N'dbo', N'placement_fixture', @TargetSentinelA, N'private', N'approved', N'unpublished', 1, NULL),
        (@EligibleTargetKeyB, @ProfileIdB, N'placement_test', NULL, NULL, NULL, N'private', N'approved', N'unpublished', 1, NULL),
        (@DraftTargetKeyA, @ProfileIdA, N'placement_test', NULL, NULL, NULL, N'private', N'draft', N'unpublished', 1, NULL),
        (@SharedTargetKeyA, @ProfileIdA, N'placement_test', NULL, NULL, NULL, N'shared', N'approved', N'unpublished', 1, NULL),
        (@PublishedTargetKeyA, @ProfileIdA, N'placement_test', NULL, NULL, NULL, N'private', N'approved', N'published', 1, NULL),
        (@InactiveTargetKeyA, @ProfileIdA, N'placement_test', NULL, NULL, NULL, N'private', N'approved', N'unpublished', 0, NULL),
        (@DeletedTargetKeyA, @ProfileIdA, N'placement_test', NULL, NULL, NULL, N'private', N'approved', N'unpublished', 0, SYSUTCDATETIME());

    DECLARE @EligibleTargetIdA bigint;
    DECLARE @EligibleTargetVersionA binary(8);
    SELECT
        @EligibleTargetIdA = entity_id,
        @EligibleTargetVersionA = row_version
    FROM dbo.slate_entities
    WHERE owner_profile_id = @ProfileIdA
      AND entity_key = @EligibleTargetKeyA;

    DECLARE @SlateCount int =
        (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @RelationCount int =
        (SELECT COUNT(*) FROM dbo.slate_entity_relations WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB));
    DECLARE @GrantCount int =
    (
        SELECT COUNT(*)
        FROM dbo.entity_access_grants AS access_grant
        JOIN dbo.slate_entities AS entity ON entity.entity_id = access_grant.entity_id
        WHERE entity.owner_profile_id IN (@ProfileIdA, @ProfileIdB)
    );
    DECLARE @PublicationCount int =
    (
        SELECT COUNT(*)
        FROM dbo.entity_publication_versions AS publication
        JOIN dbo.slate_entities AS entity ON entity.entity_id = publication.entity_id
        WHERE entity.owner_profile_id IN (@ProfileIdA, @ProfileIdB)
    );
    DECLARE @MomentStatusA nvarchar(30) =
        (SELECT status FROM dbo.moments WHERE moment_id = @MomentIdA);
    DECLARE @MomentConfirmedVersionA int =
        (SELECT confirmed_version_number FROM dbo.moments WHERE moment_id = @MomentIdA);
    DECLARE @MomentStableVersionA binary(8) =
        (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdA);
    DECLARE @MomentSourceVersionA binary(8) =
        (SELECT row_version FROM dbo.moment_sources WHERE moment_id = @MomentIdA);

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @StaleMomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE owner_profile_id = @ProfileIdA
          AND moment_id = @MomentIdA
          AND target_entity_id = @EligibleTargetIdA
    )
        THROW 52355, 'A stale Moment token created a placement.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyB,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)
    )
        THROW 52356, 'A cross-owner Moment or destination created a placement.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyB,
        @MomentKey = @MomentKeyB,
        @TargetEntityKey = @EligibleTargetKeyB,
        @ExpectedMomentRowVersion = @MomentVersionB,
        @ExpectedPlacementRowVersion = NULL;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE owner_profile_id = @ProfileIdB
    )
        THROW 52357, 'A source-deleted proposal was placed.', 1;

    DECLARE @IneligibleTargets TABLE (target_key uniqueidentifier PRIMARY KEY);
    INSERT @IneligibleTargets (target_key)
    VALUES
        (@DraftTargetKeyA),
        (@SharedTargetKeyA),
        (@PublishedTargetKeyA),
        (@InactiveTargetKeyA),
        (@DeletedTargetKeyA),
        (NEWID());

    DECLARE @IneligibleTargetKey uniqueidentifier;
    WHILE EXISTS (SELECT 1 FROM @IneligibleTargets)
    BEGIN
        SELECT TOP (1) @IneligibleTargetKey = target_key
        FROM @IneligibleTargets ORDER BY target_key;

        EXEC dbo.usp_CreateOrReactivateMomentPlacement
            @UserKey = @UserKeyA,
            @MomentKey = @MomentKeyA,
            @TargetEntityKey = @IneligibleTargetKey,
            @ExpectedMomentRowVersion = @MomentVersionA,
            @ExpectedPlacementRowVersion = NULL;

        DELETE @IneligibleTargets WHERE target_key = @IneligibleTargetKey;
    END;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE owner_profile_id = @ProfileIdA
    )
        THROW 52358, 'An unavailable destination created a placement.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    DECLARE @PlacementId bigint;
    DECLARE @PlacementKey uniqueidentifier;
    DECLARE @PlacementVersion binary(8);
    SELECT
        @PlacementId = placement_id,
        @PlacementKey = placement_key,
        @PlacementVersion = row_version
    FROM dbo.moment_placements
    WHERE owner_profile_id = @ProfileIdA
      AND moment_id = @MomentIdA
      AND target_entity_id = @EligibleTargetIdA;

    IF @PlacementId IS NULL
       OR NOT EXISTS
          (
              SELECT 1
              FROM dbo.moment_placements AS placement
              JOIN dbo.moments AS moment ON moment.moment_id = placement.moment_id
              JOIN dbo.moment_versions AS version_record
                ON version_record.moment_id = placement.moment_id
               AND version_record.version_number = placement.moment_version_number
              WHERE placement.placement_id = @PlacementId
                AND placement.owner_profile_id = @ProfileIdA
                AND placement.moment_version_number = moment.confirmed_version_number
                AND placement.moment_version_number = 2
                AND placement.placement_status = N'active'
                AND moment.status = N'confirmed'
          )
        THROW 52359, 'The exact confirmed Moment version was not pinned.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    IF
    (
        SELECT COUNT(*) FROM dbo.moment_placements
        WHERE owner_profile_id = @ProfileIdA
          AND moment_id = @MomentIdA
          AND target_entity_id = @EligibleTargetIdA
    ) <> 1
       OR
       (
           SELECT COUNT(*) FROM dbo.audit_events
           WHERE entity_key = @PlacementKey
             AND action_type = N'moment.placement.created'
             AND outcome = N'success'
       ) <> 1
        THROW 52360, 'Idempotent placement creation duplicated a row or success audit.', 1;

    DECLARE @PlacementList TABLE
    (
        placement_key uniqueidentifier,
        moment_key uniqueidentifier,
        moment_version_number int,
        target_entity_key uniqueidentifier,
        placement_status nvarchar(20),
        created_at_utc datetime2(7),
        reactivated_at_utc datetime2(7),
        removed_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8),
        target_available bit,
        target_active bit,
        target_approval_status nvarchar(30),
        target_visibility nvarchar(30),
        target_publication_status nvarchar(30),
        target_deleted bit
    );

    INSERT @PlacementList
    EXEC dbo.usp_ListMomentPlacementsForOwner
        @UserKey = @UserKeyA, @IncludeRemoved = 1, @Take = 100;

    IF NOT EXISTS
    (
        SELECT 1 FROM @PlacementList
        WHERE placement_key = @PlacementKey
          AND moment_key = @MomentKeyA
          AND moment_version_number = 2
          AND target_entity_key = @EligibleTargetKeyA
          AND placement_status = N'active'
          AND target_available = 1
    )
        THROW 52361, 'Owner placement list omitted reference metadata.', 1;

    DELETE @PlacementList;
    INSERT @PlacementList
    EXEC dbo.usp_ListMomentPlacementsForOwner
        @UserKey = @UserKeyB, @IncludeRemoved = 1, @Take = 100;

    IF EXISTS (SELECT 1 FROM @PlacementList WHERE placement_key = @PlacementKey)
        THROW 52362, 'Cross-owner placement list exposed protected metadata.', 1;

    EXEC dbo.usp_RemoveMomentPlacement
        @UserKey = @UserKeyB,
        @PlacementKey = @PlacementKey,
        @ExpectedRowVersion = @PlacementVersion;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE placement_id = @PlacementId
          AND placement_status = N'active'
          AND row_version = @PlacementVersion
    )
        THROW 52363, 'Cross-owner placement removal changed owner A state.', 1;

    EXEC dbo.usp_RemoveMomentPlacement
        @UserKey = @UserKeyA,
        @PlacementKey = @PlacementKey,
        @ExpectedRowVersion = 0x0000000000000000;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE placement_id = @PlacementId
          AND placement_status = N'active'
          AND row_version = @PlacementVersion
    )
        THROW 52364, 'A stale placement token changed lifecycle state.', 1;

    EXEC dbo.usp_RemoveMomentPlacement
        @UserKey = @UserKeyA,
        @PlacementKey = @PlacementKey,
        @ExpectedRowVersion = @PlacementVersion;

    DECLARE @RemovedPlacementVersion binary(8) =
        (SELECT row_version FROM dbo.moment_placements WHERE placement_id = @PlacementId);

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE placement_id = @PlacementId
          AND placement_status = N'removed'
          AND removed_by_user_id = @UserIdA
          AND removed_at_utc IS NOT NULL
    )
        THROW 52365, 'Explicit placement removal failed.', 1;

    EXEC dbo.usp_RemoveMomentPlacement
        @UserKey = @UserKeyA,
        @PlacementKey = @PlacementKey,
        @ExpectedRowVersion = @RemovedPlacementVersion;

    IF
    (
        SELECT COUNT(*) FROM dbo.audit_events
        WHERE entity_key = @PlacementKey
          AND action_type = N'moment.placement.removed'
          AND outcome = N'success'
    ) <> 1
        THROW 52366, 'Already-removed replay duplicated a success audit.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE placement_id = @PlacementId
          AND placement_status = N'removed'
          AND row_version = @RemovedPlacementVersion
    )
        THROW 52367, 'Reactivation without the current placement token changed state.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = @RemovedPlacementVersion;

    SET @PlacementVersion =
        (SELECT row_version FROM dbo.moment_placements WHERE placement_id = @PlacementId);

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE placement_id = @PlacementId
          AND placement_status = N'active'
          AND reactivated_by_user_id = @UserIdA
          AND reactivated_at_utc IS NOT NULL
          AND removed_by_user_id IS NULL
          AND removed_at_utc IS NULL
    )
        THROW 52368, 'Explicit placement reactivation failed.', 1;

    EXEC dbo.usp_CreateOrReactivateMomentPlacement
        @UserKey = @UserKeyA,
        @MomentKey = @MomentKeyA,
        @TargetEntityKey = @EligibleTargetKeyA,
        @ExpectedMomentRowVersion = @MomentVersionA,
        @ExpectedPlacementRowVersion = NULL;

    IF
    (
        SELECT COUNT(*) FROM dbo.audit_events
        WHERE entity_key = @PlacementKey
          AND action_type = N'moment.placement.reactivated'
          AND outcome = N'success'
    ) <> 1
       OR
       (
           SELECT COUNT(*) FROM dbo.moment_placements
           WHERE owner_profile_id = @ProfileIdA
             AND moment_id = @MomentIdA
             AND moment_version_number = 2
             AND target_entity_id = @EligibleTargetIdA
       ) <> 1
        THROW 52369, 'Reactivation or retry duplicated lifecycle evidence.', 1;

    IF (SELECT status FROM dbo.moments WHERE moment_id = @MomentIdA) <> @MomentStatusA
       OR (SELECT confirmed_version_number FROM dbo.moments WHERE moment_id = @MomentIdA) <> @MomentConfirmedVersionA
       OR (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentIdA) <> @MomentStableVersionA
       OR (SELECT row_version FROM dbo.moment_sources WHERE moment_id = @MomentIdA) <> @MomentSourceVersionA
       OR (SELECT row_version FROM dbo.slate_entities WHERE entity_id = @EligibleTargetIdA) <> @EligibleTargetVersionA
        THROW 52370, 'Placement lifecycle changed its Moment, source, or destination.', 1;

    IF (SELECT COUNT(*) FROM dbo.slate_entities WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @SlateCount
       OR (SELECT COUNT(*) FROM dbo.slate_entity_relations WHERE owner_profile_id IN (@ProfileIdA, @ProfileIdB)) <> @RelationCount
       OR
       (
           SELECT COUNT(*)
           FROM dbo.entity_access_grants AS access_grant
           JOIN dbo.slate_entities AS entity ON entity.entity_id = access_grant.entity_id
           WHERE entity.owner_profile_id IN (@ProfileIdA, @ProfileIdB)
       ) <> @GrantCount
       OR
       (
           SELECT COUNT(*)
           FROM dbo.entity_publication_versions AS publication
           JOIN dbo.slate_entities AS entity ON entity.entity_id = publication.entity_id
           WHERE entity.owner_profile_id IN (@ProfileIdA, @ProfileIdB)
       ) <> @PublicationCount
        THROW 52371, 'Placement wrote entity, relation, grant, publication, or downstream rows.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.columns AS column_record
        JOIN sys.types AS type_record
          ON type_record.user_type_id = column_record.user_type_id
        WHERE column_record.object_id = OBJECT_ID(N'dbo.moment_placements')
          AND
          (
              type_record.name IN (N'text', N'ntext', N'xml')
              OR (type_record.name IN (N'nvarchar', N'varchar')
                  AND column_record.name <> N'placement_status')
              OR column_record.max_length = -1
              OR column_record.name LIKE N'%json%'
              OR column_record.name IN
                 (
                     N'body', N'title', N'narrative', N'why_it_matters',
                     N'content', N'label', N'audience', N'prompt', N'completion',
                     N'snapshot_json'
                 )
          )
    )
        THROW 52372, 'Placement persistence contains a text, JSON, or content field.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.parameters AS parameter_record
        JOIN sys.types AS type_record
          ON type_record.user_type_id = parameter_record.user_type_id
        WHERE parameter_record.object_id IN
              (
                  OBJECT_ID(N'dbo.usp_CreateOrReactivateMomentPlacement'),
                  OBJECT_ID(N'dbo.usp_ListMomentPlacementsForOwner'),
                  OBJECT_ID(N'dbo.usp_RemoveMomentPlacement')
              )
          AND
          (
              parameter_record.max_length = -1
              OR parameter_record.name LIKE N'%Body%'
              OR parameter_record.name LIKE N'%Title%'
              OR parameter_record.name LIKE N'%Narrative%'
              OR parameter_record.name LIKE N'%Content%'
              OR parameter_record.name LIKE N'%Json%'
              OR parameter_record.name LIKE N'%Audience%'
          )
    )
        THROW 52373, 'Placement procedure request fields accept content or audience payloads.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.moment_placements
        WHERE placement_id = @PlacementId
          AND
          (
              placement_status LIKE N'%' + @SourceSentinelA + N'%'
              OR placement_status LIKE N'%' + @TitleSentinelA + N'%'
              OR placement_status LIKE N'%' + @NarrativeSentinelA + N'%'
              OR placement_status LIKE N'%' + @TargetSentinelA + N'%'
          )
    )
       OR EXISTS
       (
           SELECT 1 FROM dbo.audit_events
           WHERE entity_key = @PlacementKey
             AND
             (
                 metadata_json LIKE N'%' + @SourceSentinelA + N'%'
                 OR metadata_json LIKE N'%' + @TitleSentinelA + N'%'
                 OR metadata_json LIKE N'%' + @NarrativeSentinelA + N'%'
                 OR metadata_json LIKE N'%' + @TargetSentinelA + N'%'
                 OR request_id LIKE N'%' + @SourceSentinelA + N'%'
                 OR request_id LIKE N'%' + @TitleSentinelA + N'%'
                 OR request_id LIKE N'%' + @NarrativeSentinelA + N'%'
                 OR request_id LIKE N'%' + @TargetSentinelA + N'%'
             )
       )
        THROW 52374, 'Placement or audit/request metadata contains a content sentinel.', 1;

    UPDATE dbo.slate_entities
    SET publication_status = N'published',
        updated_at_utc = SYSUTCDATETIME()
    WHERE entity_id = @EligibleTargetIdA;

    DELETE @PlacementList;
    INSERT @PlacementList
    EXEC dbo.usp_ListMomentPlacementsForOwner
        @UserKey = @UserKeyA, @IncludeRemoved = 1, @Take = 100;

    IF NOT EXISTS
    (
        SELECT 1 FROM @PlacementList
        WHERE placement_key = @PlacementKey
          AND placement_status = N'active'
          AND target_available = 0
          AND target_publication_status = N'published'
    )
        THROW 52375, 'Placement list did not report a later unavailable target honestly.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-PLACEMENT-001 exact confirmed-version pinning, deleted-source eligibility, two-owner isolation, destination-state enforcement, stale-token rejection, lifecycle reactivation/removal, zero content copy, no downstream writes, and synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
