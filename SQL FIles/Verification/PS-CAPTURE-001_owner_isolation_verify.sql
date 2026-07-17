/* PS-CAPTURE-001 production verification.
   Creates two synthetic owners inside one outer transaction, proves each
   list procedure sees only its own capture, then rolls everything back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-CAPTURE-001'
    )
        THROW 52030, 'PS-CAPTURE-001 is not registered.', 1;

    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:capture-owner-isolation';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'capture-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'capture-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'capture-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Capture verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'capture-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Capture verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);

    SELECT @UserKeyA = app_user.user_key
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record
      ON identity_record.user_id = app_user.id
    WHERE identity_record.provider = N'capture-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record
      ON identity_record.user_id = app_user.id
    WHERE identity_record.provider = N'capture-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyA = @UserKeyB
        THROW 52031, 'Synthetic owner provisioning failed.', 1;

    DECLARE @Created TABLE
    (
        capture_key uniqueidentifier,
        capture_type nvarchar(30),
        body nvarchar(max),
        visibility nvarchar(30),
        status nvarchar(30),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7)
    );

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyA,
        @CaptureType = N'text',
        @Body = N'Owner A private verification capture';

    EXEC dbo.usp_CreateCapture
        @UserKey = @UserKeyB,
        @CaptureType = N'text',
        @Body = N'Owner B private verification capture';

    INSERT @Created
    SELECT
        capture.capture_key,
        capture.capture_type,
        capture.body,
        capture.visibility,
        capture.status,
        capture.created_at_utc,
        capture.updated_at_utc
    FROM dbo.captures AS capture
    JOIN dbo.member_profiles AS profile
      ON profile.profile_id = capture.owner_profile_id
    JOIN dbo.app_users AS app_user
      ON app_user.id = profile.user_id
    WHERE app_user.user_key IN (@UserKeyA, @UserKeyB)
      AND capture.body IN
      (
          N'Owner A private verification capture',
          N'Owner B private verification capture'
      );

    IF (SELECT COUNT(*) FROM @Created) <> 2
        THROW 52032, 'CreateCapture did not persist both synthetic captures.', 1;

    IF EXISTS
    (
        SELECT 1 FROM @Created
        WHERE visibility <> N'private' OR status <> N'captured'
    )
        THROW 52035, 'CreateCapture did not enforce private captured state.', 1;

    DECLARE @OwnerA TABLE
    (
        capture_key uniqueidentifier,
        capture_type nvarchar(30),
        body nvarchar(max),
        visibility nvarchar(30),
        status nvarchar(30),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7)
    );
    DECLARE @OwnerB TABLE
    (
        capture_key uniqueidentifier,
        capture_type nvarchar(30),
        body nvarchar(max),
        visibility nvarchar(30),
        status nvarchar(30),
        created_at_utc datetime2(7),
        updated_at_utc datetime2(7)
    );

    INSERT @OwnerA
    EXEC dbo.usp_ListCapturesForOwner @UserKey = @UserKeyA, @Take = 50;

    INSERT @OwnerB
    EXEC dbo.usp_ListCapturesForOwner @UserKey = @UserKeyB, @Take = 50;

    IF (SELECT COUNT(*) FROM @OwnerA) <> 1
       OR NOT EXISTS
       (
           SELECT 1 FROM @OwnerA
           WHERE body = N'Owner A private verification capture'
       )
       OR EXISTS
       (
           SELECT 1 FROM @OwnerA
           WHERE body = N'Owner B private verification capture'
       )
        THROW 52033, 'Owner A capture isolation failed.', 1;

    IF (SELECT COUNT(*) FROM @OwnerB) <> 1
       OR NOT EXISTS
       (
           SELECT 1 FROM @OwnerB
           WHERE body = N'Owner B private verification capture'
       )
       OR EXISTS
       (
           SELECT 1 FROM @OwnerB
           WHERE body = N'Owner A private verification capture'
       )
        THROW 52034, 'Owner B capture isolation failed.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-CAPTURE-001 owner isolation verified; synthetic data rolled back.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
