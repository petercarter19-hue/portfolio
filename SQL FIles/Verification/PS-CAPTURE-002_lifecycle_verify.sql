/* PS-CAPTURE-002 production-safe verification.
   Creates two synthetic owners inside one outer transaction, exercises
   revision, concurrency, archive/restore, delete, export, and isolation,
   proves no automatic publication, then rolls every synthetic row back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-002'
    )
        THROW 52150, 'PS-CAPTURE-002 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:capture-lifecycle-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'capture-lifecycle-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'capture-lifecycle-b-', @Suffix);
    DECLARE @OriginalA nvarchar(200) = CONCAT(N'Owner A private original ', @Suffix);
    DECLARE @CorrectedA nvarchar(200) = CONCAT(N'Owner A private correction ', @Suffix);
    DECLARE @OriginalB nvarchar(200) = CONCAT(N'Owner B private original ', @Suffix);
    DECLARE @CorrectedB nvarchar(200) = CONCAT(N'Owner B private correction ', @Suffix);
    DECLARE @CorrectionNote nvarchar(200) = CONCAT(N'Private correction note ', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'capture-lifecycle-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Capture lifecycle verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'capture-lifecycle-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Capture lifecycle verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;
    SELECT
        @UserKeyA = app_user.user_key,
        @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record
      ON identity_record.user_id = app_user.id
    WHERE identity_record.provider = N'capture-lifecycle-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT
        @UserKeyB = app_user.user_key,
        @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record
      ON identity_record.user_id = app_user.id
    WHERE identity_record.provider = N'capture-lifecycle-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyA = @UserKeyB
        THROW 52151, 'Synthetic owner provisioning failed.', 1;

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA,
        @CaptureType = N'text',
        @Body = @OriginalA;

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyB,
        @CaptureType = N'text',
        @Body = @OriginalB;

    DECLARE @CaptureIdA bigint;
    DECLARE @CaptureIdB bigint;
    DECLARE @CaptureKeyA uniqueidentifier;
    DECLARE @CaptureKeyB uniqueidentifier;
    DECLARE @OriginalVersionA binary(8);
    DECLARE @OriginalVersionB binary(8);

    SELECT
        @CaptureIdA = capture.capture_id,
        @CaptureKeyA = capture.capture_key,
        @OriginalVersionA = capture.row_version
    FROM dbo.captures AS capture
    JOIN dbo.member_profiles AS profile
      ON profile.profile_id = capture.owner_profile_id
    JOIN dbo.app_users AS app_user
      ON app_user.id = profile.user_id
    WHERE app_user.user_key = @UserKeyA
      AND capture.body = @OriginalA;

    SELECT
        @CaptureIdB = capture.capture_id,
        @CaptureKeyB = capture.capture_key,
        @OriginalVersionB = capture.row_version
    FROM dbo.captures AS capture
    JOIN dbo.member_profiles AS profile
      ON profile.profile_id = capture.owner_profile_id
    JOIN dbo.app_users AS app_user
      ON app_user.id = profile.user_id
    WHERE app_user.user_key = @UserKeyB
      AND capture.body = @OriginalB;

    IF @CaptureIdA IS NULL OR @CaptureIdB IS NULL
        THROW 52152, 'Synthetic captures were not created.', 1;

    DECLARE @CaptureRead TABLE
    (
        capture_key uniqueidentifier,
        capture_type nvarchar(30),
        body nvarchar(max),
        original_body nvarchar(max),
        visibility nvarchar(30),
        status nvarchar(30),
        active bit,
        revision_number int,
        revision_count int,
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        row_version binary(8)
    );

    INSERT @CaptureRead
    EXEC dbo.usp_GetCaptureForOwner
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyB;

    IF EXISTS (SELECT 1 FROM @CaptureRead)
        THROW 52153, 'Cross-owner get exposed a foreign capture.', 1;

    DECLARE @CaptureExport TABLE
    (
        capture_key uniqueidentifier,
        capture_type nvarchar(30),
        body nvarchar(max),
        original_body nvarchar(max),
        visibility nvarchar(30),
        status nvarchar(30),
        active bit,
        revision_number int,
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7),
        revisions_json nvarchar(max)
    );

    INSERT @CaptureExport
    EXEC dbo.usp_ExportCaptureForOwner
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyB;

    IF EXISTS (SELECT 1 FROM @CaptureExport)
        THROW 52154, 'Cross-owner export exposed a foreign capture.', 1;

    EXEC dbo.usp_CorrectCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @OriginalVersionB,
        @CorrectedBody = N'Cross-owner correction must not persist',
        @CorrectionNote = NULL;

    IF EXISTS
       (
           SELECT 1 FROM dbo.capture_revisions
           WHERE capture_id = @CaptureIdB
       )
       OR NOT EXISTS
       (
           SELECT 1 FROM dbo.captures
           WHERE capture_id = @CaptureIdB
             AND row_version = @OriginalVersionB
             AND active = 1
             AND status = N'captured'
       )
        THROW 52155, 'Cross-owner correction was not denied generically.', 1;

    EXEC dbo.usp_CorrectCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @OriginalVersionA,
        @CorrectedBody = @CorrectedA,
        @CorrectionNote = @CorrectionNote;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.capture_revisions
        WHERE capture_id = @CaptureIdA
          AND revision_number = 1
    )
        THROW 52156, 'Owner correction did not create revision 1.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_id = @CaptureIdA AND body = @OriginalA
    )
        THROW 52157, 'Original capture body was overwritten.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.capture_revisions
        WHERE capture_id = @CaptureIdA
          AND revision_number = 1
          AND body = @CorrectedA
          AND correction_note = @CorrectionNote
          AND corrected_by_user_id = @UserIdA
    )
        THROW 52158, 'Correction revision provenance is incomplete.', 1;

    EXEC dbo.usp_CorrectCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyA,
        @ExpectedRowVersion = @OriginalVersionA,
        @CorrectedBody = N'Stale row version must not persist',
        @CorrectionNote = NULL;

    IF (SELECT COUNT(*) FROM dbo.capture_revisions WHERE capture_id = @CaptureIdA) <> 1
        THROW 52159, 'Stale row version changed the capture.', 1;

    DELETE @CaptureRead;
    INSERT @CaptureRead
    EXEC dbo.usp_ListCapturesForOwner
        @UserKey = @UserKeyA,
        @Take = 50,
        @Archived = 0;

    IF NOT EXISTS
    (
        SELECT 1 FROM @CaptureRead
        WHERE capture_key = @CaptureKeyA
          AND body = @CorrectedA
          AND original_body = @OriginalA
          AND revision_number = 1
          AND revision_count = 1
          AND visibility = N'private'
          AND status = N'captured'
    )
        THROW 52160, 'Current-body selection or private state is incorrect.', 1;

    EXEC dbo.usp_ArchiveCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @OriginalVersionB;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_id = @CaptureIdB
          AND row_version = @OriginalVersionB
          AND active = 1
          AND status = N'captured'
    )
        THROW 52161, 'Cross-owner archive was not denied generically.', 1;

    EXEC dbo.usp_ArchiveCapture
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @OriginalVersionB;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_id = @CaptureIdB
          AND active = 0
          AND status = N'archived'
          AND row_version <> @OriginalVersionB
    )
        THROW 52162, 'Owner archive failed.', 1;

    DECLARE @ArchivedVersionB binary(8) =
    (
        SELECT row_version FROM dbo.captures WHERE capture_id = @CaptureIdB
    );

    DELETE @CaptureRead;
    INSERT @CaptureRead
    EXEC dbo.usp_ListCapturesForOwner
        @UserKey = @UserKeyB,
        @Take = 50,
        @Archived = 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM @CaptureRead
        WHERE capture_key = @CaptureKeyB
          AND active = 0
          AND status = N'archived'
          AND visibility = N'private'
    )
        THROW 52163, 'Archived capture was not owner-visible in the archived filter.', 1;

    EXEC dbo.usp_RestoreCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @ArchivedVersionB;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_id = @CaptureIdB
          AND row_version = @ArchivedVersionB
          AND active = 0
          AND status = N'archived'
    )
        THROW 52164, 'Cross-owner restore was not denied generically.', 1;

    EXEC dbo.usp_RestoreCapture
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @ArchivedVersionB;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_id = @CaptureIdB
          AND active = 1
          AND status = N'captured'
          AND row_version <> @ArchivedVersionB
    )
        THROW 52165, 'Owner restore failed.', 1;

    DECLARE @RestoredVersionB binary(8) =
    (
        SELECT row_version FROM dbo.captures WHERE capture_id = @CaptureIdB
    );

    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyA,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @RestoredVersionB;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_id = @CaptureIdB
          AND row_version = @RestoredVersionB
    )
        THROW 52166, 'Cross-owner delete was not denied generically.', 1;

    EXEC dbo.usp_CorrectCapture
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @RestoredVersionB,
        @CorrectedBody = @CorrectedB,
        @CorrectionNote = @CorrectionNote;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.capture_revisions
        WHERE capture_id = @CaptureIdB
          AND revision_number = 1
          AND body = @CorrectedB
    )
        THROW 52167, 'Owner B correction failed before delete verification.', 1;

    DECLARE @CorrectedVersionB binary(8) =
    (
        SELECT row_version FROM dbo.captures WHERE capture_id = @CaptureIdB
    );

    IF (SELECT COUNT(*) FROM dbo.capture_revisions WHERE capture_id = @CaptureIdB) <> 1
        THROW 52168, 'Delete verification did not begin with one revision.', 1;

    EXEC dbo.usp_DeleteCapture
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB,
        @ExpectedRowVersion = @CorrectedVersionB;

    IF EXISTS
    (
        SELECT 1 FROM dbo.captures WHERE capture_id = @CaptureIdB
        UNION ALL
        SELECT 1 FROM dbo.capture_revisions WHERE capture_id = @CaptureIdB
    )
        THROW 52169, 'Deleted capture text remained in the Capture aggregate.', 1;

    DELETE @CaptureRead;
    INSERT @CaptureRead
    EXEC dbo.usp_GetCaptureForOwner
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB;

    DELETE @CaptureExport;
    INSERT @CaptureExport
    EXEC dbo.usp_ExportCaptureForOwner
        @UserKey = @UserKeyB,
        @CaptureKey = @CaptureKeyB;

    IF EXISTS (SELECT 1 FROM @CaptureRead)
       OR EXISTS (SELECT 1 FROM @CaptureExport)
        THROW 52170, 'Deleted capture remained readable or exportable.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.entity_type = N'capture'
          AND audit_event.entity_key IN (@CaptureKeyA, @CaptureKeyB)
          AND
          (
              audit_event.metadata_json LIKE N'%' + @OriginalA + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CorrectedA + N'%'
              OR audit_event.metadata_json LIKE N'%' + @OriginalB + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CorrectedB + N'%'
              OR audit_event.metadata_json LIKE N'%' + @CorrectionNote + N'%'
          )
    )
        THROW 52171, 'Audit metadata contains private capture content.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.captures
        WHERE capture_key IN (@CaptureKeyA, @CaptureKeyB)
          AND (visibility <> N'private' OR status = N'placed')
    )
        THROW 52172, 'Lifecycle actions changed visibility or auto-published/placed.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-CAPTURE-002 lifecycle, two-owner isolation, no automatic publication, and synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
