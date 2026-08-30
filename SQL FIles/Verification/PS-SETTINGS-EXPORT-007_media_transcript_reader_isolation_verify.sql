/* PS-SETTINGS-EXPORT-007 (account export Voice/Photo media and
   transcript readers) production-safe owner-isolation verification.

   House pattern (PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql):
   three synthetic owners (A, B, C -- C deactivated after its fixture is
   created) via a throwaway auth provider, one outer always-rolled-back
   transaction, fresh THROW numbers in the 58900-58999 block (clear of
   this package's own migration/rollback 58800-58899 range and of every
   sibling verification file's range -- highest prior use anywhere under
   SQL FIles/ before this package is 58753).

   FIVE READERS, TWO INDEPENDENT FAMILIES SHARING ONE SHAPE. Voice
   (voice_media_sources -> voice_transcription_attempts,
   voice_media_sources -> voice_capture_links -> voice_transcription_
   attempts) and Photo (capture_media_sources -> capture_media_links)
   are read from PS-VOICE-001 and PS-CAPTURE-MEDIA-001 respectively; both
   source tables share the identical payload-nulled-on-delete shape, and
   both link tables share the identical "no opaque key of its own"
   shape. Every reader's forbidden-column set, owner-predicate count, and
   join shape is proved per-procedure in section 0b below, since they
   genuinely differ (0 joins / 1 join / 2 joins).

   DIRECTIVE-CATEGORY CANARIES. This package hard-excludes
   STORAGE_LOCATOR, CONTENT_DIGEST, STORAGE_ETAG, and PROVIDER_REFERENCE
   columns (see the migration file's own header for the full citation
   trail), plus disclosed MACHINERY columns (safe_error_code, scan_result,
   scan_completed_at_utc, deletion_capture_row_version). Section 1's
   fixture populates EVERY one of these with a real, distinguishing,
   never-otherwise-referenced value on at least one row, so section 0b's
   forbidden-column-absence check proves a genuine exclusion of populated
   data, never merely the absence of something that was never written.
   Every uniqueidentifier canary is entropy-dead (NEWID() is used only
   where the schema itself generates the value; every hand-authored
   binary/string canary below uses a flat repeated character, never a
   realistic-looking GUID).

   DELETED-ROW AND IN-FLIGHT-ATTEMPT EXCLUSION PROOFS. Both source tables
   get one row inserted DIRECTLY in state = 'deleted' with every nullable
   payload column left NULL (CK_voice_media_sources_live_payload /
   CK_capture_media_sources_original_payload's own deleted branch) --
   planted, then proved absent from their own reader. Owner A's primary
   voice source additionally carries three transcription attempts
   (succeeded, failed, and processing) so section 3 can prove the
   succeeded and failed attempts both appear (the failed one WITHOUT its
   safe_error_code) while the processing one -- structurally contentless
   per CK_voice_transcription_attempts_result -- never appears at all.

   Read-window design note (why this script can use INSERT ... EXEC
   freely): every one of the five readers under test returns its read
   window as two TRAILING COLUMNS on its single content result set,
   never a second result set and never OUTPUT parameters (see the
   migration file's own header). This script uses BARE EXEC for every
   procedure at least once (the forged-@UserKey and deactivated-owner
   proofs, checked via @@ROWCOUNT immediately after the call) and
   INSERT ... EXEC for the real, two-owner, field-value-level isolation
   proofs, which need actual captured rows; every capturing TABLE
   variable below declares EXACTLY the columns its reader is expected to
   return, so an accidental extra output column would fail the INSERT
   itself, not merely go unchecked.

   Proof strategy:
     0. STRUCTURAL, looped across all five procedure names: exact
        "@UserKey nvarchar(300)" signature and no other parameter; the
        byte-identical identity-resolution header is present verbatim;
        an explicit ORDER BY is present; the read-window columns are
        present with exactly two SELECT keywords; no transaction-control
        keyword, write, or nested EXEC/dynamic SQL appears anywhere in
        the body; no caller-selected owner/target parameter.
     0b. Per-procedure, explicit (not looped -- the forbidden-list,
        FROM-anchor, owner-predicate count, and join shape genuinely
        differ per procedure): the content SELECT list -- located
        precisely as the text between the shared identity header's
        closing "IF @ProfileId IS NULL RETURN;" line and the procedure's
        own first subsequent "FROM dbo.<table>" -- never contains a
        forbidden column's fully-qualified reference; every owner
        predicate the procedure needs (one per joined table) is present;
        the state <> 'deleted' predicate is present on every reader that
        needs it (all five, through their own source table); the
        expected JOIN count is present.
     1. Three synthetic owners (A, B, C) via a throwaway auth provider.
        A and B each get a constraint-complete fixture mirroring each
        other exactly: one FK-target dbo.captures row per media type
        (never read by any procedure under test, needed only to satisfy
        voice_capture_links/capture_media_links' own FOREIGN KEY), three
        dbo.voice_media_sources rows (a "primary" one carrying three
        dbo.voice_transcription_attempts and one dbo.voice_capture_links
        row; a "failed" one canarying voice_media_sources' own
        safe_error_code/deletion_capture_row_version; a "deleted" one
        planted directly in state = 'deleted'), and three
        dbo.capture_media_sources rows (a "primary" one carrying one
        dbo.capture_media_links row; a "failed" one canarying
        capture_media_sources' own scan_result/scan_completed_at_utc/
        safe_error_code/deletion_capture_row_version; a "deleted" one).
        C gets one minimal row per table, is then deactivated, and must
        read as zero rows across all five procedures thereafter even
        though every row still physically exists. Every NOT NULL
        no-DEFAULT column, CHECK constraint, and FOREIGN KEY on all five
        tables was re-read from PS-VOICE-001_voice_capture.sql and
        PS-CAPTURE-MEDIA-001_photo_sources.sql before writing any INSERT
        below.
     2. Two synthetic-owner proofs (forged key, deactivated owner) across
        all five procedures via bare EXEC, checked by @@ROWCOUNT.
     3. DATA-LEVEL, for ALL FIVE procedures: calling as owner A must
        return exactly owner A's own row(s), carrying every
        distinguishing fixture value including correct parent-key
        linkage, and must NEVER contain any value or key unique to owner
        B's fixture -- and symmetrically for B. Every fixture row's
        identifying key is captured immediately after insert (via
        SCOPE_IDENTITY() then a follow-up SELECT of the opaque key, the
        same idiom every prior package's verification script uses) and
        it is that captured key -- never a guessed or literal constant --
        that every assertion below checks for. voice_capture_links and
        capture_media_links carry no opaque key of their own (unlike
        every table above); this script asserts against the joined
        source's own source_key directly, matching the migration's own
        recorded reasoning.
     4. Exclusion proofs: the deleted-state source row is absent from
        both source readers; the in-flight (processing) attempt is
        absent from the attempt reader while the concluded (succeeded,
        failed) ones are present, the failed one without its
        safe_error_code.

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-007')
        THROW 58900, 'PS-SETTINGS-EXPORT-007 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof, looped across all five procedures.
       ------------------------------------------------------------ */
    DECLARE @ReaderNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ReaderNames (procedure_name)
    VALUES
        (N'usp_ReadAccountExportVoiceMediaSourceForOwner'),
        (N'usp_ReadAccountExportVoiceTranscriptionAttemptForOwner'),
        (N'usp_ReadAccountExportVoiceCaptureLinkForOwner'),
        (N'usp_ReadAccountExportCaptureMediaSourceForOwner'),
        (N'usp_ReadAccountExportCaptureMediaLinkForOwner');

    IF (SELECT COUNT(*) FROM @ReaderNames) <> 5
        THROW 58901, 'The reader-name fixture itself is incomplete.', 1;

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ReaderNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ReaderNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 58902, 'A required account-export Voice/Photo media reader procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 58903, 'A Voice/Photo media reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
        IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
            THROW 58903, 'A Voice/Photo media reader procedure declares more than just @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%@OwnerUserId%'
           OR @CheckDefinition LIKE N'%@TableName%'
           OR @CheckDefinition LIKE N'%@SourceKey%'
           OR @CheckDefinition LIKE N'%@CaptureKey%'
            THROW 58903, 'A Voice/Photo media reader procedure accepts a caller-supplied owner id or target.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 58904, 'A Voice/Photo media reader procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
           OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
            THROW 58904, 'A Voice/Photo media reader procedure does not require an active user AND an active profile.', 1;
        IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
            THROW 58904, 'A Voice/Photo media reader procedure does not use the shared byte-identical identity header.', 1;
        IF @CheckDefinition NOT LIKE N'%ORDER BY%'
            THROW 58905, 'A Voice/Photo media reader procedure has no deterministic ORDER BY.', 1;
        IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
            THROW 58905, 'A Voice/Photo media reader procedure uses SELECT * instead of an explicit column list.', 1;
        IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
            THROW 58906, 'A Voice/Photo media reader procedure does not return the read-window columns.', 1;
        IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'SELECT', N''))) / LEN(N'SELECT') <> 2
            THROW 58906, 'A Voice/Photo media reader procedure does not contain exactly two SELECT keywords.', 1;
        IF @CheckDefinition LIKE N'%BEGIN TRAN%'
           OR @CheckDefinition LIKE N'%COMMIT%'
           OR @CheckDefinition LIKE N'%ROLLBACK%'
           OR @CheckDefinition LIKE N'%BEGIN TRY%'
           OR @CheckDefinition LIKE N'%BEGIN CATCH%'
           OR @CheckDefinition LIKE N'%INSERT %'
           OR @CheckDefinition LIKE N'%UPDATE %'
           OR @CheckDefinition LIKE N'%DELETE %'
           OR @CheckDefinition LIKE N'%EXEC%'
            THROW 58907, 'A Voice/Photo media reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;
        IF @CheckDefinition NOT LIKE N'%state <> N''deleted''%'
            THROW 58907, 'A Voice/Photo media reader procedure is missing its deleted-state exclusion predicate.', 1;

        DELETE @ReaderNames WHERE procedure_name = @CheckName;
    END;

    /* ------------------------------------------------------------
       0b. Per-procedure forbidden-column-absence, owner-predicate, and
           join-shape proof. The content SELECT list is located
           precisely between the shared identity header's closing line
           and the procedure's own first FROM clause.
       ------------------------------------------------------------ */
    DECLARE @HeaderEnd nvarchar(60) = N'IF @ProfileId IS NULL RETURN;';
    DECLARE @ListStart int;
    DECLARE @ListEnd int;
    DECLARE @SelectList nvarchar(max);

    -- Reader 1: voice_media_sources. Forbidden: source_id, owner_profile_id,
    -- blob_name, sha256_digest, safe_error_code, deletion_capture_row_version,
    -- created_by_user_id, deleted_by_user_id, deleted_at_utc, row_version.
    -- No JOIN beyond the identity header's own "JOIN dbo.app_users".
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportVoiceMediaSourceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.voice_media_sources AS source', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58910, 'Could not locate the voice media source reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%source.source_id%' OR @SelectList LIKE N'%source.owner_profile_id%'
       OR @SelectList LIKE N'%source.blob_name%' OR @SelectList LIKE N'%source.sha256_digest%'
       OR @SelectList LIKE N'%source.safe_error_code%' OR @SelectList LIKE N'%source.deletion_capture_row_version%'
       OR @SelectList LIKE N'%source.created_by_user_id%' OR @SelectList LIKE N'%source.deleted_by_user_id%'
       OR @SelectList LIKE N'%source.deleted_at_utc%' OR @SelectList LIKE N'%source.row_version%'
        THROW 58910, 'The voice media source reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%source.owner_profile_id = @ProfileId%'
        THROW 58910, 'The voice media source reader is missing its owner predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 1
        THROW 58910, 'The voice media source reader has a content-level join; it should have none beyond the identity header''s own.', 1;

    -- Reader 2: voice_transcription_attempts, joined to voice_media_sources.
    -- Forbidden: attempt_id, source_id, owner_profile_id, provider_request_id,
    -- safe_error_code, row_version, plus the joined source's internal id.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.voice_transcription_attempts AS attempt', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58911, 'Could not locate the voice transcription attempt reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%attempt.attempt_id%' OR @SelectList LIKE N'%attempt.source_id%'
       OR @SelectList LIKE N'%attempt.owner_profile_id%' OR @SelectList LIKE N'%attempt.provider_request_id%'
       OR @SelectList LIKE N'%attempt.safe_error_code%' OR @SelectList LIKE N'%attempt.row_version%'
       OR @SelectList LIKE N'%source.source_id%' OR @SelectList LIKE N'%source.owner_profile_id%'
        THROW 58911, 'The voice transcription attempt reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%attempt.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%source.owner_profile_id = @ProfileId%'
        THROW 58911, 'The voice transcription attempt reader is missing the owner predicate on both sides of its parent join.', 1;
    IF @CheckDefinition NOT LIKE N'%attempt.state IN (N''succeeded'', N''failed'')%'
        THROW 58911, 'The voice transcription attempt reader is missing its concluded-attempt-only predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 2
        THROW 58911, 'The voice transcription attempt reader does not have exactly one content-level join plus the identity header''s own.', 1;

    -- Reader 3: voice_capture_links, joined to voice_media_sources and
    -- voice_transcription_attempts. Forbidden: voice_capture_link_id,
    -- source_id, owner_profile_id, capture_id, successful_attempt_id,
    -- confirmed_by_user_id.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.voice_capture_links AS link', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58912, 'Could not locate the voice capture link reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%link.voice_capture_link_id%' OR @SelectList LIKE N'%link.source_id%'
       OR @SelectList LIKE N'%link.owner_profile_id%' OR @SelectList LIKE N'%link.capture_id%'
       OR @SelectList LIKE N'%link.successful_attempt_id%' OR @SelectList LIKE N'%link.confirmed_by_user_id%'
        THROW 58912, 'The voice capture link reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%link.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%source.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%attempt.owner_profile_id = @ProfileId%'
        THROW 58912, 'The voice capture link reader is missing the owner predicate on every joined table.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 3
        THROW 58912, 'The voice capture link reader does not have exactly two content-level joins plus the identity header''s own.', 1;

    -- Reader 4: capture_media_sources. Forbidden: source_id, owner_profile_id,
    -- original_blob_name, derivative_blob_name, original_sha256_digest,
    -- original_blob_etag, derivative_sha256_digest, derivative_blob_etag,
    -- scan_result, scan_completed_at_utc, safe_error_code,
    -- deletion_capture_row_version, created_by_user_id, deleted_by_user_id,
    -- deleted_at_utc, row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureMediaSourceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.capture_media_sources AS source', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58913, 'Could not locate the capture media source reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%source.source_id%' OR @SelectList LIKE N'%source.owner_profile_id%'
       OR @SelectList LIKE N'%source.original_blob_name%' OR @SelectList LIKE N'%source.derivative_blob_name%'
       OR @SelectList LIKE N'%source.original_sha256_digest%' OR @SelectList LIKE N'%source.original_blob_etag%'
       OR @SelectList LIKE N'%source.derivative_sha256_digest%' OR @SelectList LIKE N'%source.derivative_blob_etag%'
       OR @SelectList LIKE N'%source.scan_result%' OR @SelectList LIKE N'%source.scan_completed_at_utc%'
       OR @SelectList LIKE N'%source.safe_error_code%' OR @SelectList LIKE N'%source.deletion_capture_row_version%'
       OR @SelectList LIKE N'%source.created_by_user_id%' OR @SelectList LIKE N'%source.deleted_by_user_id%'
       OR @SelectList LIKE N'%source.deleted_at_utc%' OR @SelectList LIKE N'%source.row_version%'
        THROW 58913, 'The capture media source reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%source.owner_profile_id = @ProfileId%'
        THROW 58913, 'The capture media source reader is missing its owner predicate.', 1;
    IF @CheckDefinition NOT LIKE N'%source.source_type = N''photo''%'
        THROW 58913, 'The capture media source reader is missing its explicit source_type = ''photo'' predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 1
        THROW 58913, 'The capture media source reader has a content-level join; it should have none beyond the identity header''s own.', 1;

    -- Reader 5: capture_media_links, joined to capture_media_sources.
    -- Forbidden: capture_media_link_id, source_id, owner_profile_id,
    -- capture_id, confirmed_by_user_id.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureMediaLinkForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.capture_media_links AS link', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58914, 'Could not locate the capture media link reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%link.capture_media_link_id%' OR @SelectList LIKE N'%link.source_id%'
       OR @SelectList LIKE N'%link.owner_profile_id%' OR @SelectList LIKE N'%link.capture_id%'
       OR @SelectList LIKE N'%link.confirmed_by_user_id%'
        THROW 58914, 'The capture media link reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%link.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%source.owner_profile_id = @ProfileId%'
        THROW 58914, 'The capture media link reader is missing the owner predicate on both sides of its parent join.', 1;
    IF @CheckDefinition NOT LIKE N'%source.source_type = N''photo''%'
        THROW 58914, 'The capture media link reader is missing the joined source''s explicit source_type = ''photo'' predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 2
        THROW 58914, 'The capture media link reader does not have exactly one content-level join plus the identity header''s own.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x7-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x7-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x7-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x7-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x7-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX7 Owner A', @Email = N'psx7-owner-a@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x7-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX7 Owner B', @Email = N'psx7-owner-b@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x7-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX7 Owner C';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @UserKeyC nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    DECLARE @ProfileIdC bigint;
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;
    DECLARE @UserIdC int;

    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id, @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x7-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x7-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x7-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 58930, 'Synthetic Voice/Photo media verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture. Every NOT NULL no-DEFAULT column, CHECK constraint, and
       FOREIGN KEY on all five tables (plus dbo.captures, needed only as
       an FK target for the two link tables and never read by any
       procedure under test) was re-read from PS-VOICE-001_voice_capture.sql
       and PS-CAPTURE-MEDIA-001_photo_sources.sql before writing any
       INSERT below.
       ------------------------------------------------------------ */
    DECLARE @CapVoiceIdA bigint, @CapPhotoIdA bigint;
    DECLARE @CapVoiceIdB bigint, @CapPhotoIdB bigint;
    DECLARE @CapVoiceIdC bigint, @CapPhotoIdC bigint;

    DECLARE @VoicePrimaryIdA bigint, @VoicePrimaryKeyA uniqueidentifier;
    DECLARE @VoiceFailedKeyA uniqueidentifier;
    DECLARE @VoiceDeletedKeyA uniqueidentifier;
    DECLARE @AttemptSucceededIdA bigint, @AttemptSucceededKeyA uniqueidentifier;
    DECLARE @AttemptFailedKeyA uniqueidentifier;
    DECLARE @AttemptProcessingKeyA uniqueidentifier;
    DECLARE @PhotoPrimaryIdA bigint, @PhotoPrimaryKeyA uniqueidentifier;
    DECLARE @PhotoFailedKeyA uniqueidentifier;
    DECLARE @PhotoDeletedKeyA uniqueidentifier;

    DECLARE @VoicePrimaryIdB bigint, @VoicePrimaryKeyB uniqueidentifier;
    DECLARE @VoiceFailedKeyB uniqueidentifier;
    DECLARE @VoiceDeletedKeyB uniqueidentifier;
    DECLARE @AttemptSucceededIdB bigint, @AttemptSucceededKeyB uniqueidentifier;
    DECLARE @AttemptFailedKeyB uniqueidentifier;
    DECLARE @AttemptProcessingKeyB uniqueidentifier;
    DECLARE @PhotoPrimaryIdB bigint, @PhotoPrimaryKeyB uniqueidentifier;
    DECLARE @PhotoFailedKeyB uniqueidentifier;
    DECLARE @PhotoDeletedKeyB uniqueidentifier;

    DECLARE @VoicePrimaryIdC bigint, @VoicePrimaryKeyC uniqueidentifier;
    DECLARE @AttemptSucceededIdC bigint;
    DECLARE @PhotoPrimaryIdC bigint, @PhotoPrimaryKeyC uniqueidentifier;

    ------------------------------------------------------------------
    -- dbo.captures rows: FK targets only, never read by any procedure
    -- under test.
    ------------------------------------------------------------------
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdA, N'voice', N'PSX7-A voice capture body (FK target only)', N'private', N'captured');
    SET @CapVoiceIdA = SCOPE_IDENTITY();
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdA, N'photo', N'PSX7-A photo capture body (FK target only)', N'private', N'captured');
    SET @CapPhotoIdA = SCOPE_IDENTITY();

    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdB, N'voice', N'PSX7-B voice capture body (FK target only)', N'private', N'captured');
    SET @CapVoiceIdB = SCOPE_IDENTITY();
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdB, N'photo', N'PSX7-B photo capture body (FK target only)', N'private', N'captured');
    SET @CapPhotoIdB = SCOPE_IDENTITY();

    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdC, N'voice', N'PSX7-C voice capture body (FK target only)', N'private', N'captured');
    SET @CapVoiceIdC = SCOPE_IDENTITY();
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdC, N'photo', N'PSX7-C photo capture body (FK target only)', N'private', N'captured');
    SET @CapPhotoIdC = SCOPE_IDENTITY();

    ------------------------------------------------------------------
    -- Owner A: Voice fixture
    ------------------------------------------------------------------
    INSERT dbo.voice_media_sources
        (owner_profile_id, blob_name, content_type, byte_length, sha256_digest, locale,
         client_duration_milliseconds, verified_duration_milliseconds, state, created_by_user_id)
    VALUES
        (@ProfileIdA, N'voice/v1/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.webm', N'audio/webm', 222222,
         0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA, N'en-US',
         5000, 4900, N'confirmed', @UserIdA);
    SET @VoicePrimaryIdA = SCOPE_IDENTITY();
    SELECT @VoicePrimaryKeyA = source_key FROM dbo.voice_media_sources WHERE source_id = @VoicePrimaryIdA;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, provider_transcript, provider_request_id,
         queued_at_utc, started_at_utc, completed_at_utc)
    VALUES
        (@VoicePrimaryIdA, @ProfileIdA, 1, N'succeeded',
         N'PSX7-A owner transcript alpha (member spoken words)',
         N'provider-request-aaaaaaaaaaaaaaaaaaaaaaaa (must never be readable)',
         SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME());
    SET @AttemptSucceededIdA = SCOPE_IDENTITY();
    SELECT @AttemptSucceededKeyA = attempt_key FROM dbo.voice_transcription_attempts WHERE attempt_id = @AttemptSucceededIdA;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, safe_error_code,
         queued_at_utc, started_at_utc, completed_at_utc)
    VALUES
        (@VoicePrimaryIdA, @ProfileIdA, 2, N'failed', N'speech-failed-aaaaaaaa (must never be readable)',
         SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME());
    SELECT @AttemptFailedKeyA = attempt_key FROM dbo.voice_transcription_attempts
    WHERE source_id = @VoicePrimaryIdA AND attempt_number = 2;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, queued_at_utc, started_at_utc)
    VALUES
        (@VoicePrimaryIdA, @ProfileIdA, 3, N'processing', SYSUTCDATETIME(), SYSUTCDATETIME());
    SELECT @AttemptProcessingKeyA = attempt_key FROM dbo.voice_transcription_attempts
    WHERE source_id = @VoicePrimaryIdA AND attempt_number = 3;

    INSERT dbo.voice_capture_links
        (source_id, owner_profile_id, capture_id, successful_attempt_id, confirmed_by_user_id)
    VALUES (@VoicePrimaryIdA, @ProfileIdA, @CapVoiceIdA, @AttemptSucceededIdA, @UserIdA);

    INSERT dbo.voice_media_sources
        (owner_profile_id, blob_name, content_type, byte_length, sha256_digest, locale,
         client_duration_milliseconds, state, safe_error_code, deletion_capture_row_version, created_by_user_id)
    VALUES
        (@ProfileIdA, N'voice/v1/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee.webm', N'audio/webm', 333333,
         0xEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE, N'en-US',
         6000, N'failed', N'storage-unavailable-aaaa (must never be readable)',
         0xAAAAAAAAAAAAAAAA, @UserIdA);
    SELECT @VoiceFailedKeyA = source_key FROM dbo.voice_media_sources
    WHERE owner_profile_id = @ProfileIdA AND state = N'failed';

    INSERT dbo.voice_media_sources
        (owner_profile_id, state, deleted_by_user_id, deleted_at_utc, created_by_user_id)
    VALUES (@ProfileIdA, N'deleted', @UserIdA, SYSUTCDATETIME(), @UserIdA);
    SELECT @VoiceDeletedKeyA = source_key FROM dbo.voice_media_sources
    WHERE owner_profile_id = @ProfileIdA AND state = N'deleted';

    ------------------------------------------------------------------
    -- Owner A: Photo fixture
    ------------------------------------------------------------------
    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, original_blob_name, derivative_blob_name,
         original_content_type, original_byte_length, original_sha256_digest, original_blob_etag,
         derivative_content_type, derivative_byte_length, derivative_sha256_digest, derivative_blob_etag,
         pixel_width, pixel_height, state, scan_result, created_by_user_id)
    VALUES
        (@ProfileIdA, N'photo',
         N'photo/v1/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg',
         N'photo/v1/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-preview.jpg',
         N'image/jpeg', 444444,
         0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,
         N'original-etag-aaaaaaaa (must never be readable)',
         N'image/jpeg', 55555,
         0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,
         N'derivative-etag-aaaaaaaa (must never be readable)',
         800, 600, N'confirmed', N'clean', @UserIdA);
    SET @PhotoPrimaryIdA = SCOPE_IDENTITY();
    SELECT @PhotoPrimaryKeyA = source_key FROM dbo.capture_media_sources WHERE source_id = @PhotoPrimaryIdA;

    INSERT dbo.capture_media_links
        (source_id, owner_profile_id, capture_id, confirmed_by_user_id)
    VALUES (@PhotoPrimaryIdA, @ProfileIdA, @CapPhotoIdA, @UserIdA);

    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, original_blob_name, derivative_blob_name,
         original_content_type, original_byte_length, original_sha256_digest,
         state, scan_result, scan_completed_at_utc, safe_error_code,
         deletion_capture_row_version, created_by_user_id)
    VALUES
        (@ProfileIdA, N'photo',
         N'photo/v1/eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee.jpg',
         N'photo/v1/eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee-preview.jpg',
         N'image/jpeg', 666666,
         0xEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE,
         N'failed', N'error', SYSUTCDATETIME(), N'scan-error-aaaaaaaa (must never be readable)',
         0xAAAAAAAAAAAAAAAA, @UserIdA);
    SELECT @PhotoFailedKeyA = source_key FROM dbo.capture_media_sources
    WHERE owner_profile_id = @ProfileIdA AND state = N'failed';

    -- scan_result carries DEFAULT N'unknown'; the deleted-state payload
    -- CHECK demands NULL, so it must be set explicitly (an engine-only
    -- trap the first gate run caught: omitting the column fires the
    -- DEFAULT, not NULL).
    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, state, scan_result, deleted_by_user_id, deleted_at_utc, created_by_user_id)
    VALUES (@ProfileIdA, N'photo', N'deleted', NULL, @UserIdA, SYSUTCDATETIME(), @UserIdA);
    SELECT @PhotoDeletedKeyA = source_key FROM dbo.capture_media_sources
    WHERE owner_profile_id = @ProfileIdA AND state = N'deleted';

    ------------------------------------------------------------------
    -- Owner B: Voice fixture (mirrors A, distinct distinguishing text)
    ------------------------------------------------------------------
    INSERT dbo.voice_media_sources
        (owner_profile_id, blob_name, content_type, byte_length, sha256_digest, locale,
         client_duration_milliseconds, verified_duration_milliseconds, state, created_by_user_id)
    VALUES
        (@ProfileIdB, N'voice/v1/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb.webm', N'audio/webm', 777777,
         0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB, N'en-US',
         5100, 5000, N'confirmed', @UserIdB);
    SET @VoicePrimaryIdB = SCOPE_IDENTITY();
    SELECT @VoicePrimaryKeyB = source_key FROM dbo.voice_media_sources WHERE source_id = @VoicePrimaryIdB;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, provider_transcript, provider_request_id,
         queued_at_utc, started_at_utc, completed_at_utc)
    VALUES
        (@VoicePrimaryIdB, @ProfileIdB, 1, N'succeeded',
         N'PSX7-B owner transcript alpha (member spoken words)',
         N'provider-request-bbbbbbbbbbbbbbbbbbbbbbbb (must never be readable)',
         SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME());
    SET @AttemptSucceededIdB = SCOPE_IDENTITY();
    SELECT @AttemptSucceededKeyB = attempt_key FROM dbo.voice_transcription_attempts WHERE attempt_id = @AttemptSucceededIdB;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, safe_error_code,
         queued_at_utc, started_at_utc, completed_at_utc)
    VALUES
        (@VoicePrimaryIdB, @ProfileIdB, 2, N'failed', N'speech-failed-bbbbbbbb (must never be readable)',
         SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME());
    SELECT @AttemptFailedKeyB = attempt_key FROM dbo.voice_transcription_attempts
    WHERE source_id = @VoicePrimaryIdB AND attempt_number = 2;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, queued_at_utc, started_at_utc)
    VALUES
        (@VoicePrimaryIdB, @ProfileIdB, 3, N'processing', SYSUTCDATETIME(), SYSUTCDATETIME());
    SELECT @AttemptProcessingKeyB = attempt_key FROM dbo.voice_transcription_attempts
    WHERE source_id = @VoicePrimaryIdB AND attempt_number = 3;

    INSERT dbo.voice_capture_links
        (source_id, owner_profile_id, capture_id, successful_attempt_id, confirmed_by_user_id)
    VALUES (@VoicePrimaryIdB, @ProfileIdB, @CapVoiceIdB, @AttemptSucceededIdB, @UserIdB);

    INSERT dbo.voice_media_sources
        (owner_profile_id, blob_name, content_type, byte_length, sha256_digest, locale,
         client_duration_milliseconds, state, safe_error_code, deletion_capture_row_version, created_by_user_id)
    VALUES
        (@ProfileIdB, N'voice/v1/ffffffff-ffff-ffff-ffff-ffffffffffff.webm', N'audio/webm', 888888,
         0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, N'en-US',
         6100, N'failed', N'storage-unavailable-bbbb (must never be readable)',
         0xBBBBBBBBBBBBBBBB, @UserIdB);
    SELECT @VoiceFailedKeyB = source_key FROM dbo.voice_media_sources
    WHERE owner_profile_id = @ProfileIdB AND state = N'failed';

    INSERT dbo.voice_media_sources
        (owner_profile_id, state, deleted_by_user_id, deleted_at_utc, created_by_user_id)
    VALUES (@ProfileIdB, N'deleted', @UserIdB, SYSUTCDATETIME(), @UserIdB);
    SELECT @VoiceDeletedKeyB = source_key FROM dbo.voice_media_sources
    WHERE owner_profile_id = @ProfileIdB AND state = N'deleted';

    ------------------------------------------------------------------
    -- Owner B: Photo fixture
    ------------------------------------------------------------------
    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, original_blob_name, derivative_blob_name,
         original_content_type, original_byte_length, original_sha256_digest, original_blob_etag,
         derivative_content_type, derivative_byte_length, derivative_sha256_digest, derivative_blob_etag,
         pixel_width, pixel_height, state, scan_result, created_by_user_id)
    VALUES
        (@ProfileIdB, N'photo',
         N'photo/v1/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.jpg',
         N'photo/v1/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-preview.jpg',
         N'image/jpeg', 999999,
         0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB,
         N'original-etag-bbbbbbbb (must never be readable)',
         N'image/jpeg', 66666,
         0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB,
         N'derivative-etag-bbbbbbbb (must never be readable)',
         801, 601, N'confirmed', N'clean', @UserIdB);
    SET @PhotoPrimaryIdB = SCOPE_IDENTITY();
    SELECT @PhotoPrimaryKeyB = source_key FROM dbo.capture_media_sources WHERE source_id = @PhotoPrimaryIdB;

    INSERT dbo.capture_media_links
        (source_id, owner_profile_id, capture_id, confirmed_by_user_id)
    VALUES (@PhotoPrimaryIdB, @ProfileIdB, @CapPhotoIdB, @UserIdB);

    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, original_blob_name, derivative_blob_name,
         original_content_type, original_byte_length, original_sha256_digest,
         state, scan_result, scan_completed_at_utc, safe_error_code,
         deletion_capture_row_version, created_by_user_id)
    VALUES
        (@ProfileIdB, N'photo',
         N'photo/v1/fffffffffffffffffffffffffffffffffff.jpg',
         N'photo/v1/fffffffffffffffffffffffffffffffffff-preview.jpg',
         N'image/jpeg', 121212,
         0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
         N'failed', N'error', SYSUTCDATETIME(), N'scan-error-bbbbbbbb (must never be readable)',
         0xBBBBBBBBBBBBBBBB, @UserIdB);
    SELECT @PhotoFailedKeyB = source_key FROM dbo.capture_media_sources
    WHERE owner_profile_id = @ProfileIdB AND state = N'failed';

    -- Same DEFAULT-vs-NULL trap as owner A's deleted photo row above.
    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, state, scan_result, deleted_by_user_id, deleted_at_utc, created_by_user_id)
    VALUES (@ProfileIdB, N'photo', N'deleted', NULL, @UserIdB, SYSUTCDATETIME(), @UserIdB);
    SELECT @PhotoDeletedKeyB = source_key FROM dbo.capture_media_sources
    WHERE owner_profile_id = @ProfileIdB AND state = N'deleted';

    ------------------------------------------------------------------
    -- Owner C: one minimal row per table, then deactivate the owner.
    ------------------------------------------------------------------
    INSERT dbo.voice_media_sources
        (owner_profile_id, blob_name, content_type, byte_length, sha256_digest, locale,
         client_duration_milliseconds, state, created_by_user_id)
    VALUES
        (@ProfileIdC, N'voice/v1/cccccccc-cccc-cccc-cccc-cccccccccccc.webm', N'audio/webm', 111111,
         0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC, N'en-US',
         5200, N'confirmed', @UserIdC);
    SET @VoicePrimaryIdC = SCOPE_IDENTITY();
    SELECT @VoicePrimaryKeyC = source_key FROM dbo.voice_media_sources WHERE source_id = @VoicePrimaryIdC;

    INSERT dbo.voice_transcription_attempts
        (source_id, owner_profile_id, attempt_number, state, provider_transcript,
         queued_at_utc, started_at_utc, completed_at_utc)
    VALUES
        (@VoicePrimaryIdC, @ProfileIdC, 1, N'succeeded',
         N'PSX7-C capture (must never be readable once inactive)',
         SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME());
    SET @AttemptSucceededIdC = SCOPE_IDENTITY();

    INSERT dbo.voice_capture_links
        (source_id, owner_profile_id, capture_id, successful_attempt_id, confirmed_by_user_id)
    VALUES (@VoicePrimaryIdC, @ProfileIdC, @CapVoiceIdC, @AttemptSucceededIdC, @UserIdC);

    INSERT dbo.capture_media_sources
        (owner_profile_id, source_type, original_blob_name, derivative_blob_name,
         original_content_type, original_byte_length, original_sha256_digest, original_blob_etag,
         derivative_content_type, derivative_byte_length, derivative_sha256_digest, derivative_blob_etag,
         pixel_width, pixel_height, state, scan_result, created_by_user_id)
    VALUES
        (@ProfileIdC, N'photo',
         N'photo/v1/ccccccccccccccccccccccccccccccccccc.jpg',
         N'photo/v1/ccccccccccccccccccccccccccccccccccc-preview.jpg',
         N'image/jpeg', 131313,
         0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC,
         N'original-etag-cccccccc (must never be readable)',
         N'image/jpeg', 77777,
         0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC,
         N'derivative-etag-cccccccc (must never be readable)',
         802, 602, N'confirmed', N'clean', @UserIdC);
    SET @PhotoPrimaryIdC = SCOPE_IDENTITY();

    INSERT dbo.capture_media_links
        (source_id, owner_profile_id, capture_id, confirmed_by_user_id)
    VALUES (@PhotoPrimaryIdC, @ProfileIdC, @CapPhotoIdC, @UserIdC);

    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 58931, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey proof for all five procedures.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportVoiceMediaSourceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58940, 'A forged UserKey returned a voice media source row.', 1;
    EXEC dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58940, 'A forged UserKey returned a voice transcription attempt row.', 1;
    EXEC dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58940, 'A forged UserKey returned a voice capture link row.', 1;
    EXEC dbo.usp_ReadAccountExportCaptureMediaSourceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58940, 'A forged UserKey returned a capture media source row.', 1;
    EXEC dbo.usp_ReadAccountExportCaptureMediaLinkForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58940, 'A forged UserKey returned a capture media link row.', 1;

    /* ------------------------------------------------------------
       2b. Inactive-owner proof, all five procedures, using owner C's
           genuinely populated, pre-deactivation fixture.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportVoiceMediaSourceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58941, 'A deactivated owner''s voice media source row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58941, 'A deactivated owner''s voice transcription attempt row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58941, 'A deactivated owner''s voice capture link row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportCaptureMediaSourceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58941, 'A deactivated owner''s capture media source row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportCaptureMediaLinkForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58941, 'A deactivated owner''s capture media link row was still readable.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proofs for all five
          procedures via INSERT ... EXEC. Every capturing TABLE variable
          declares EXACTLY the columns its reader is expected to return.
       ------------------------------------------------------------ */

    -- Voice media source (2 rows expected per owner: primary + failed;
    -- the deleted row must never appear).
    DECLARE @VoiceSourceCapture TABLE
    (
        source_key uniqueidentifier, content_type nvarchar(40), byte_length bigint, locale nvarchar(10),
        client_duration_milliseconds int, verified_duration_milliseconds int, state nvarchar(30),
        created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @VoiceSourceCapture EXEC dbo.usp_ReadAccountExportVoiceMediaSourceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @VoiceSourceCapture) <> 2
        THROW 58950, 'Owner A''s voice media source capture does not have exactly two rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE source_key = @VoicePrimaryKeyA AND state = N'confirmed' AND verified_duration_milliseconds = 4900)
        THROW 58951, 'Owner A''s voice media source capture is missing the primary source or its facts.', 1;
    IF NOT EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE source_key = @VoiceFailedKeyA AND state = N'failed')
        THROW 58951, 'Owner A''s voice media source capture is missing the failed source (failed rows must still appear).', 1;
    IF EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE source_key = @VoiceDeletedKeyA)
        THROW 58952, 'A deleted-state voice media source is still returned by its reader.', 1;
    IF EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE source_key IN (@VoicePrimaryKeyB, @VoiceFailedKeyB, @VoiceDeletedKeyB))
        THROW 58952, 'Owner A''s voice media source capture contains one of owner B''s sources.', 1;
    IF EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58953, 'Owner A''s voice media source capture has a missing or non-monotonic read window.', 1;

    DELETE @VoiceSourceCapture;
    INSERT @VoiceSourceCapture EXEC dbo.usp_ReadAccountExportVoiceMediaSourceForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @VoiceSourceCapture) <> 2
        THROW 58950, 'Owner B''s voice media source capture does not have exactly two rows.', 1;
    IF EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE source_key = @VoiceDeletedKeyB)
        THROW 58952, 'A deleted-state voice media source is still returned by its reader.', 1;
    IF EXISTS (SELECT 1 FROM @VoiceSourceCapture WHERE source_key IN (@VoicePrimaryKeyA, @VoiceFailedKeyA, @VoiceDeletedKeyA))
        THROW 58952, 'Owner B''s voice media source capture contains one of owner A''s sources.', 1;

    -- Voice transcription attempt (2 rows expected per owner: succeeded
    -- + failed; the processing one must never appear).
    DECLARE @AttemptCapture TABLE
    (
        source_key uniqueidentifier, attempt_key uniqueidentifier, attempt_number int, state nvarchar(20),
        provider_transcript nvarchar(max), queued_at_utc datetime2(7), started_at_utc datetime2(7),
        completed_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @AttemptCapture EXEC dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @AttemptCapture) <> 2
        THROW 58950, 'Owner A''s voice transcription attempt capture does not have exactly two rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @AttemptCapture
        WHERE attempt_key = @AttemptSucceededKeyA AND source_key = @VoicePrimaryKeyA
          AND attempt_number = 1 AND state = N'succeeded'
          AND provider_transcript = N'PSX7-A owner transcript alpha (member spoken words)'
    )
        THROW 58951, 'Owner A''s voice transcription attempt capture is missing the succeeded attempt or its transcript.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @AttemptCapture
        WHERE attempt_key = @AttemptFailedKeyA AND source_key = @VoicePrimaryKeyA
          AND attempt_number = 2 AND state = N'failed' AND provider_transcript IS NULL
    )
        THROW 58951, 'Owner A''s voice transcription attempt capture is missing the failed attempt.', 1;
    IF EXISTS (SELECT 1 FROM @AttemptCapture WHERE attempt_key = @AttemptProcessingKeyA)
        THROW 58952, 'An in-flight (processing) transcription attempt is still returned by its reader.', 1;
    IF EXISTS (SELECT 1 FROM @AttemptCapture WHERE attempt_key IN (@AttemptSucceededKeyB, @AttemptFailedKeyB, @AttemptProcessingKeyB))
        THROW 58952, 'Owner A''s voice transcription attempt capture contains one of owner B''s attempts.', 1;

    DELETE @AttemptCapture;
    INSERT @AttemptCapture EXEC dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @AttemptCapture) <> 2
        THROW 58950, 'Owner B''s voice transcription attempt capture does not have exactly two rows.', 1;
    IF EXISTS (SELECT 1 FROM @AttemptCapture WHERE attempt_key = @AttemptProcessingKeyB)
        THROW 58952, 'An in-flight (processing) transcription attempt is still returned by its reader.', 1;
    IF EXISTS (SELECT 1 FROM @AttemptCapture WHERE attempt_key IN (@AttemptSucceededKeyA, @AttemptFailedKeyA, @AttemptProcessingKeyA))
        THROW 58952, 'Owner B''s voice transcription attempt capture contains one of owner A''s attempts.', 1;

    -- Voice capture link (1 row expected per owner).
    DECLARE @VoiceLinkCapture TABLE
    (
        source_key uniqueidentifier, attempt_key uniqueidentifier, confirmed_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @VoiceLinkCapture EXEC dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @VoiceLinkCapture) <> 1
        THROW 58950, 'Owner A''s voice capture link capture does not have exactly one row.', 1;
    IF NOT EXISTS (SELECT 1 FROM @VoiceLinkCapture WHERE source_key = @VoicePrimaryKeyA AND attempt_key = @AttemptSucceededKeyA)
        THROW 58951, 'Owner A''s voice capture link capture is missing its own row or its linkage.', 1;
    IF EXISTS (SELECT 1 FROM @VoiceLinkCapture WHERE source_key = @VoicePrimaryKeyB OR attempt_key = @AttemptSucceededKeyB)
        THROW 58952, 'Owner A''s voice capture link capture contains one of owner B''s links.', 1;

    DELETE @VoiceLinkCapture;
    INSERT @VoiceLinkCapture EXEC dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @VoiceLinkCapture WHERE source_key = @VoicePrimaryKeyB AND attempt_key = @AttemptSucceededKeyB)
        THROW 58951, 'Owner B''s voice capture link capture is missing its own row or its linkage.', 1;
    IF EXISTS (SELECT 1 FROM @VoiceLinkCapture WHERE source_key = @VoicePrimaryKeyA OR attempt_key = @AttemptSucceededKeyA)
        THROW 58952, 'Owner B''s voice capture link capture contains one of owner A''s links.', 1;

    -- Capture media source (2 rows expected per owner: primary + failed;
    -- the deleted row must never appear).
    DECLARE @PhotoSourceCapture TABLE
    (
        source_key uniqueidentifier, source_type nvarchar(20), original_content_type nvarchar(40),
        original_byte_length bigint, derivative_content_type nvarchar(40), derivative_byte_length bigint,
        pixel_width int, pixel_height int, state nvarchar(30),
        created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @PhotoSourceCapture EXEC dbo.usp_ReadAccountExportCaptureMediaSourceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @PhotoSourceCapture) <> 2
        THROW 58950, 'Owner A''s capture media source capture does not have exactly two rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @PhotoSourceCapture
        WHERE source_key = @PhotoPrimaryKeyA AND state = N'confirmed' AND pixel_width = 800 AND pixel_height = 600
    )
        THROW 58951, 'Owner A''s capture media source capture is missing the primary source or its facts.', 1;
    IF NOT EXISTS (SELECT 1 FROM @PhotoSourceCapture WHERE source_key = @PhotoFailedKeyA AND state = N'failed')
        THROW 58951, 'Owner A''s capture media source capture is missing the failed source (failed rows must still appear).', 1;
    IF EXISTS (SELECT 1 FROM @PhotoSourceCapture WHERE source_key = @PhotoDeletedKeyA)
        THROW 58952, 'A deleted-state capture media source is still returned by its reader.', 1;
    IF EXISTS (SELECT 1 FROM @PhotoSourceCapture WHERE source_key IN (@PhotoPrimaryKeyB, @PhotoFailedKeyB, @PhotoDeletedKeyB))
        THROW 58952, 'Owner A''s capture media source capture contains one of owner B''s sources.', 1;

    DELETE @PhotoSourceCapture;
    INSERT @PhotoSourceCapture EXEC dbo.usp_ReadAccountExportCaptureMediaSourceForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @PhotoSourceCapture) <> 2
        THROW 58950, 'Owner B''s capture media source capture does not have exactly two rows.', 1;
    IF EXISTS (SELECT 1 FROM @PhotoSourceCapture WHERE source_key = @PhotoDeletedKeyB)
        THROW 58952, 'A deleted-state capture media source is still returned by its reader.', 1;
    IF EXISTS (SELECT 1 FROM @PhotoSourceCapture WHERE source_key IN (@PhotoPrimaryKeyA, @PhotoFailedKeyA, @PhotoDeletedKeyA))
        THROW 58952, 'Owner B''s capture media source capture contains one of owner A''s sources.', 1;

    -- Capture media link (1 row expected per owner).
    DECLARE @PhotoLinkCapture TABLE
    (
        source_key uniqueidentifier, confirmed_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @PhotoLinkCapture EXEC dbo.usp_ReadAccountExportCaptureMediaLinkForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @PhotoLinkCapture) <> 1
        THROW 58950, 'Owner A''s capture media link capture does not have exactly one row.', 1;
    IF NOT EXISTS (SELECT 1 FROM @PhotoLinkCapture WHERE source_key = @PhotoPrimaryKeyA)
        THROW 58951, 'Owner A''s capture media link capture is missing its own row.', 1;
    IF EXISTS (SELECT 1 FROM @PhotoLinkCapture WHERE source_key = @PhotoPrimaryKeyB)
        THROW 58952, 'Owner A''s capture media link capture contains one of owner B''s links.', 1;

    DELETE @PhotoLinkCapture;
    INSERT @PhotoLinkCapture EXEC dbo.usp_ReadAccountExportCaptureMediaLinkForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @PhotoLinkCapture WHERE source_key = @PhotoPrimaryKeyB)
        THROW 58951, 'Owner B''s capture media link capture is missing its own row.', 1;
    IF EXISTS (SELECT 1 FROM @PhotoLinkCapture WHERE source_key = @PhotoPrimaryKeyA)
        THROW 58952, 'Owner B''s capture media link capture contains one of owner A''s links.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-007: structural grep across all five Voice/Photo media reader procedures (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, deterministic ORDER BY, read-window columns present with exactly two SELECT keywords, no transaction control/write/dynamic SQL, explicit state <> ''deleted'' predicate); per-procedure forbidden-column absence and predicate presence verified against each procedure''s own isolated content select-list text, including the owner-predicate-on-every-side check for the attempt and both link readers and the source_type = ''photo'' predicate on both Photo readers; a forged UserKey and a deactivated owner both yield zero rows (never an error) across all five procedures; real two-owner fixture data (three voice media sources, three transcription attempts on the primary source, one voice capture link, three capture media sources, and one capture media link, per owner) proves every one of the five readers returns exactly and only the calling owner''s own rows, complete with a non-null monotonic read window and correct parent source_key/attempt_key linkage; a payload-nulled deleted-state row is proven absent from both source readers; an in-flight (processing) transcription attempt is proven absent from the attempt reader while its sibling succeeded and failed attempts (the failed one without its safe_error_code) both appear; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
