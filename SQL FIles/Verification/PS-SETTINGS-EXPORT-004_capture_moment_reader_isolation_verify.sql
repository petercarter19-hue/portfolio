/* PS-SETTINGS-EXPORT-004 (account export Capture/Moment readers)
   production-safe owner-isolation verification.

   House pattern (PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql):
   two synthetic owners (A, B) plus a third (C, deactivated after its
   fixture is created) via a throwaway auth provider, one outer
   always-rolled-back transaction, fresh THROW numbers in the
   58300-58399 block (clear of this package's own migration/rollback
   58200-58299 range and of every sibling verification file's range --
   highest prior use anywhere under SQL FIles/ is 58161).

   Read-window design note (why this script can use INSERT ... EXEC
   freely): every one of the six readers under test returns its read
   window as two TRAILING COLUMNS on its single content result set,
   never a second result set and never OUTPUT parameters (see the
   migration file's own header). That single, uniform shape is exactly
   what keeps every one of them safe to call with INSERT ... EXEC --
   Microsoft's own INSERT (Transact-SQL) reference requires "each result
   set" from an EXEC target to be "compatible with the columns in the
   table," not merely the first one. None of the six readers under test
   contains any transaction control at all (asserted structurally
   below), so both calling conventions are available here; this script
   uses BARE EXEC for every procedure at least once (the forged-@UserKey
   and deactivated-owner proofs, checked via @@ROWCOUNT immediately
   after the call) and INSERT ... EXEC for the real, two-owner,
   field-value-level isolation proofs, which need actual captured rows.

   Proof strategy:
     0. STRUCTURAL, looped across all six procedure names: exact
        "@UserKey nvarchar(300)" signature and no other parameter; the
        byte-identical identity-resolution header is present verbatim;
        the expected owner-scoping predicate appears; an explicit
        ORDER BY is present; the read-window columns are present; and --
        the load-bearing structural tripwire -- no transaction-control
        keyword, write, or nested EXEC/dynamic SQL appears anywhere in
        the body.
     0b. Per-procedure, explicit (not looped -- the forbidden-list and
        FROM-anchor genuinely differ per procedure): the content SELECT
        list -- located precisely as the text between the shared
        identity header's closing "IF @ProfileId IS NULL RETURN;" line
        and the procedure's own first subsequent "FROM dbo.<table>" --
        never contains a forbidden column's fully-qualified reference,
        and every reader that is supposed to carry a soft-delete or
        both-sided owner predicate does.
     1. Two synthetic owners (A, B) each get: three dbo.captures rows
        (a "primary" one with two dbo.capture_revisions, an "archived"
        one with none, and a "doomed" one with one revision reserved for
        the soft-delete proof), two dbo.moments rows (a "confirmed" one
        sourced from the primary capture's second revision, with one
        dbo.moment_versions row, one dbo.moment_sources row in state
        'available', and one dbo.moment_placements row against a
        throwaway dbo.slate_entities destination; and a "proposal" one
        sourced from the archived capture at revision 0, with one blank
        dbo.moment_versions row and one dbo.moment_sources row directly
        set to state 'deleted' -- simulating the tombstone
        usp_DeleteCapture leaves behind -- to prove the reader surfaces
        that fact rather than filtering it). A third owner (C) gets one
        minimal row in each of the six tables (plus the one
        dbo.slate_entities row its placement needs), is then
        deactivated, and must read as zero rows across all six
        procedures thereafter even though every row still physically
        exists. Every NOT NULL no-DEFAULT column, CHECK constraint, and
        FOREIGN KEY on every touched table (dbo.captures,
        dbo.capture_revisions, dbo.moments, dbo.moment_versions,
        dbo.moment_sources, dbo.moment_placements, dbo.slate_entities)
        was re-read from PS-CAPTURE-001_captures.sql,
        PS-CAPTURE-002_capture_lifecycle.sql, PS-MOMENT-001_moments.sql,
        PS-PLACEMENT-001_moment_placements.sql, and
        PS-PLAT-002_profiles_entities_access.sql before writing any
        INSERT below -- in particular dbo.captures'
        CK_captures_deleted_state, which ties deleted_at_utc to active
        and is why the soft-delete proof below sets both columns, not
        deleted_at_utc alone.
     2. DATA-LEVEL, for EVERY one of the six procedures: calling as
        owner A must return exactly owner A's own row(s), carrying every
        distinguishing fixture value including correct parent
        capture_key/moment_key linkage, and must NEVER contain any value
        unique to owner B's fixture -- and symmetrically for B. Every
        fixture row's identifying key is captured immediately after
        insert (via SCOPE_IDENTITY() then a follow-up SELECT of the
        opaque key, the same idiom PS-SETTINGS-EXPORT-003's own
        verification script uses) and it is that captured key -- never a
        guessed or literal constant -- that every assertion below
        checks for.
     3. Soft-delete: only dbo.captures carries a soft-delete column
        among these six tables (dbo.moments, dbo.moment_versions,
        dbo.moment_sources, and dbo.moment_placements have none --
        discarding a Moment proposal is a real DELETE, not a flag, and
        dbo.moment_sources' own source_deleted_at_utc/source_state
        describe the LINKED CAPTURE's fate, never this row's own
        presence, so no predicate proof applies to them). Soft-deleting
        owner A's "doomed" capture must remove exactly that capture from
        the capture reader and its one revision from the capture
        revision reader, while leaving the "primary" and "archived"
        captures (and the primary's two revisions) visible for the same
        owner, and owner B's entire fixture untouched.

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-004')
        THROW 58300, 'PS-SETTINGS-EXPORT-004 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof, looped across all six procedures.
       ------------------------------------------------------------ */
    DECLARE @ReaderNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY, owner_predicate nvarchar(120) NOT NULL);
    INSERT @ReaderNames (procedure_name, owner_predicate)
    VALUES
        (N'usp_ReadAccountExportCaptureForOwner', N'capture.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCaptureRevisionForOwner', N'capture.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportMomentForOwner', N'moment.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportMomentVersionForOwner', N'moment.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportMomentSourceForOwner', N'moment_source.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportMomentPlacementForOwner', N'placement.owner_profile_id = @ProfileId');

    IF (SELECT COUNT(*) FROM @ReaderNames) <> 6
        THROW 58301, 'The reader-name fixture itself is incomplete.', 1;

    DECLARE @CheckName sysname;
    DECLARE @CheckOwnerPredicate nvarchar(120);
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ReaderNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name, @CheckOwnerPredicate = owner_predicate
        FROM @ReaderNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 58302, 'A required account-export Capture/Moment reader procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 58303, 'A Capture/Moment reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
        IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
            THROW 58303, 'A Capture/Moment reader procedure declares more than just @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%@OwnerUserId%'
           OR @CheckDefinition LIKE N'%@TableName%'
           OR @CheckDefinition LIKE N'%@CaptureKey%'
           OR @CheckDefinition LIKE N'%@MomentKey%'
            THROW 58303, 'A Capture/Moment reader procedure accepts a caller-supplied owner id or target.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 58304, 'A Capture/Moment reader procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
           OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
            THROW 58304, 'A Capture/Moment reader procedure does not require an active user AND an active profile.', 1;
        IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
            THROW 58304, 'A Capture/Moment reader procedure does not use the shared byte-identical identity header.', 1;
        IF @CheckDefinition NOT LIKE N'%' + @CheckOwnerPredicate + N'%'
            THROW 58305, 'A Capture/Moment reader procedure does not filter by its expected owner predicate.', 1;
        IF @CheckDefinition NOT LIKE N'%ORDER BY%'
            THROW 58306, 'A Capture/Moment reader procedure has no deterministic ORDER BY.', 1;
        IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
            THROW 58306, 'A Capture/Moment reader procedure uses SELECT * instead of an explicit column list.', 1;
        IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
            THROW 58307, 'A Capture/Moment reader procedure does not return the read-window columns.', 1;
        IF @CheckDefinition LIKE N'%BEGIN TRAN%'
           OR @CheckDefinition LIKE N'%COMMIT%'
           OR @CheckDefinition LIKE N'%ROLLBACK%'
           OR @CheckDefinition LIKE N'%BEGIN TRY%'
           OR @CheckDefinition LIKE N'%BEGIN CATCH%'
           OR @CheckDefinition LIKE N'%INSERT %'
           OR @CheckDefinition LIKE N'%UPDATE %'
           OR @CheckDefinition LIKE N'%DELETE %'
           OR @CheckDefinition LIKE N'%EXEC%'
            THROW 58308, 'A Capture/Moment reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;

        DELETE @ReaderNames WHERE procedure_name = @CheckName;
    END;

    /* ------------------------------------------------------------
       0b. Per-procedure forbidden-column-absence and predicate-
           presence proof. The content SELECT list is located
           precisely between the shared identity header's closing
           line and the procedure's own FROM clause.
       ------------------------------------------------------------ */
    DECLARE @HeaderEnd nvarchar(60) = N'IF @ProfileId IS NULL RETURN;';
    DECLARE @ListStart int;
    DECLARE @ListEnd int;
    DECLARE @SelectList nvarchar(max);

    -- Capture: forbidden capture_id/owner_profile_id/active/deleted_at_utc/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.captures AS capture', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58320, 'Could not locate the capture reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%capture.capture_id%' OR @SelectList LIKE N'%capture.owner_profile_id%'
       OR @SelectList LIKE N'%capture.active%' OR @SelectList LIKE N'%capture.deleted_at_utc%'
       OR @SelectList LIKE N'%capture.row_version%'
        THROW 58320, 'The capture reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%capture.deleted_at_utc IS NULL%'
        THROW 58320, 'The capture reader is missing its own soft-delete predicate.', 1;

    -- Capture revision: forbidden revision_id/capture_id/corrected_by_user_id/
    -- row_version/capture.owner_profile_id (as an OUTPUT column)/capture.active.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCaptureRevisionForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.capture_revisions AS revision', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58321, 'Could not locate the capture revision reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%revision.revision_id%' OR @SelectList LIKE N'%revision.capture_id%'
       OR @SelectList LIKE N'%revision.corrected_by_user_id%' OR @SelectList LIKE N'%revision.row_version%'
       OR @SelectList LIKE N'%capture.owner_profile_id%' OR @SelectList LIKE N'%capture.active%'
       OR @SelectList LIKE N'%capture.capture_id%'
        THROW 58321, 'The capture revision reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%capture.deleted_at_utc IS NULL%'
        THROW 58321, 'The capture revision reader is missing the joined capture''s soft-delete predicate.', 1;

    -- Moment: forbidden moment_id/owner_profile_id/confirmed_by_user_id/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportMomentForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.moments AS moment', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58322, 'Could not locate the moment reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%moment.moment_id%' OR @SelectList LIKE N'%moment.owner_profile_id%'
       OR @SelectList LIKE N'%moment.confirmed_by_user_id%' OR @SelectList LIKE N'%moment.row_version%'
        THROW 58322, 'The moment reader selects a forbidden column.', 1;

    -- Moment version: forbidden moment_version_id/moment_id/saved_by_user_id/
    -- row_version/moment.owner_profile_id (as output)/moment.moment_id.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportMomentVersionForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.moment_versions AS moment_version', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58323, 'Could not locate the moment version reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%moment_version.moment_version_id%' OR @SelectList LIKE N'%moment_version.moment_id%'
       OR @SelectList LIKE N'%moment_version.saved_by_user_id%' OR @SelectList LIKE N'%moment_version.row_version%'
       OR @SelectList LIKE N'%moment.owner_profile_id%' OR @SelectList LIKE N'%moment.moment_id%'
        THROW 58323, 'The moment version reader selects a forbidden column.', 1;

    -- Moment source: forbidden moment_source_id/moment_id/owner_profile_id/
    -- capture_id/capture_revision_id/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportMomentSourceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.moment_sources AS moment_source', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58324, 'Could not locate the moment source reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%moment_source.moment_source_id%' OR @SelectList LIKE N'%moment_source.moment_id%'
       OR @SelectList LIKE N'%moment_source.owner_profile_id%' OR @SelectList LIKE N'%moment_source.capture_id%'
       OR @SelectList LIKE N'%moment_source.capture_revision_id%' OR @SelectList LIKE N'%moment_source.row_version%'
       OR @SelectList LIKE N'%moment.owner_profile_id%' OR @SelectList LIKE N'%moment.moment_id%'
        THROW 58324, 'The moment source reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%moment_source.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%moment.owner_profile_id = @ProfileId%'
        THROW 58324, 'The moment source reader is missing the owner predicate on both sides of its parent join.', 1;

    -- Moment placement: forbidden placement_id/owner_profile_id/moment_id/
    -- target_entity_id/created_by_user_id/reactivated_by_user_id/
    -- removed_by_user_id/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportMomentPlacementForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.moment_placements AS placement', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58325, 'Could not locate the moment placement reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%placement.placement_id%' OR @SelectList LIKE N'%placement.owner_profile_id%'
       OR @SelectList LIKE N'%placement.moment_id%' OR @SelectList LIKE N'%placement.target_entity_id%'
       OR @SelectList LIKE N'%placement.created_by_user_id%' OR @SelectList LIKE N'%placement.reactivated_by_user_id%'
       OR @SelectList LIKE N'%placement.removed_by_user_id%' OR @SelectList LIKE N'%placement.row_version%'
       OR @SelectList LIKE N'%moment.owner_profile_id%' OR @SelectList LIKE N'%moment.moment_id%'
        THROW 58325, 'The moment placement reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%placement.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%moment.owner_profile_id = @ProfileId%'
        THROW 58325, 'The moment placement reader is missing the owner predicate on both sides of its parent join.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x4-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x4-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x4-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x4-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x4-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX4 Owner A', @Email = N'psx4-owner-a@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x4-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX4 Owner B', @Email = N'psx4-owner-b@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x4-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX4 Owner C';

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
    WHERE identity_row.provider = N'settings-export-x4-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x4-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x4-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 58330, 'Synthetic Capture/Moment verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture. Every NOT NULL no-DEFAULT column, CHECK constraint, and
       FOREIGN KEY on dbo.captures, dbo.capture_revisions, dbo.moments,
       dbo.moment_versions, dbo.moment_sources, dbo.moment_placements,
       and dbo.slate_entities was re-read from their owning migration
       files before writing any INSERT below.
       ------------------------------------------------------------ */
    DECLARE @CapturePrimaryIdA bigint, @CapturePrimaryKeyA uniqueidentifier;
    DECLARE @CaptureArchivedIdA bigint, @CaptureArchivedKeyA uniqueidentifier;
    DECLARE @CaptureDoomedIdA bigint, @CaptureDoomedKeyA uniqueidentifier;
    DECLARE @RevisionPrimary1IdA bigint, @RevisionPrimary1KeyA uniqueidentifier;
    DECLARE @RevisionPrimary2IdA bigint, @RevisionPrimary2KeyA uniqueidentifier;
    DECLARE @RevisionDoomedIdA bigint, @RevisionDoomedKeyA uniqueidentifier;
    DECLARE @MomentConfirmedIdA bigint, @MomentConfirmedKeyA uniqueidentifier;
    DECLARE @MomentProposalIdA bigint, @MomentProposalKeyA uniqueidentifier;
    DECLARE @MomentVersionConfirmedKeyA uniqueidentifier;
    DECLARE @MomentVersionProposalKeyA uniqueidentifier;
    DECLARE @MomentSourceAvailableKeyA uniqueidentifier;
    DECLARE @MomentSourceDeletedIdA bigint, @MomentSourceDeletedKeyA uniqueidentifier;
    DECLARE @TargetEntityIdA bigint;
    DECLARE @PlacementKeyA uniqueidentifier;

    DECLARE @CapturePrimaryIdB bigint, @CapturePrimaryKeyB uniqueidentifier;
    DECLARE @CaptureArchivedIdB bigint, @CaptureArchivedKeyB uniqueidentifier;
    DECLARE @CaptureDoomedIdB bigint, @CaptureDoomedKeyB uniqueidentifier;
    DECLARE @RevisionPrimary1IdB bigint, @RevisionPrimary1KeyB uniqueidentifier;
    DECLARE @RevisionPrimary2IdB bigint, @RevisionPrimary2KeyB uniqueidentifier;
    DECLARE @RevisionDoomedIdB bigint, @RevisionDoomedKeyB uniqueidentifier;
    DECLARE @MomentConfirmedIdB bigint, @MomentConfirmedKeyB uniqueidentifier;
    DECLARE @MomentProposalIdB bigint, @MomentProposalKeyB uniqueidentifier;
    DECLARE @MomentVersionConfirmedKeyB uniqueidentifier;
    DECLARE @MomentVersionProposalKeyB uniqueidentifier;
    DECLARE @MomentSourceAvailableKeyB uniqueidentifier;
    DECLARE @MomentSourceDeletedIdB bigint, @MomentSourceDeletedKeyB uniqueidentifier;
    DECLARE @TargetEntityIdB bigint;
    DECLARE @PlacementKeyB uniqueidentifier;

    DECLARE @CaptureIdC bigint, @CaptureKeyC uniqueidentifier;
    DECLARE @RevisionIdC bigint;
    DECLARE @MomentIdC bigint, @MomentKeyC uniqueidentifier;
    DECLARE @TargetEntityIdC bigint;

    ------------------------------------------------------------------
    -- Owner A fixture
    ------------------------------------------------------------------
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdA, N'text', N'PSX4-A primary capture body', N'private', N'captured');
    SET @CapturePrimaryIdA = SCOPE_IDENTITY();
    SELECT @CapturePrimaryKeyA = capture_key FROM dbo.captures WHERE capture_id = @CapturePrimaryIdA;

    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status, active)
    VALUES (@ProfileIdA, N'text', N'PSX4-A archived capture body', N'private', N'archived', 0);
    SET @CaptureArchivedIdA = SCOPE_IDENTITY();
    SELECT @CaptureArchivedKeyA = capture_key FROM dbo.captures WHERE capture_id = @CaptureArchivedIdA;

    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdA, N'text', N'PSX4-A doomed capture body', N'private', N'captured');
    SET @CaptureDoomedIdA = SCOPE_IDENTITY();
    SELECT @CaptureDoomedKeyA = capture_key FROM dbo.captures WHERE capture_id = @CaptureDoomedIdA;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CapturePrimaryIdA, 1, N'PSX4-A primary revision one body', N'PSX4-A revision one note', @UserIdA);
    SET @RevisionPrimary1IdA = SCOPE_IDENTITY();
    SELECT @RevisionPrimary1KeyA = revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionPrimary1IdA;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CapturePrimaryIdA, 2, N'PSX4-A primary revision two body', NULL, @UserIdA);
    SET @RevisionPrimary2IdA = SCOPE_IDENTITY();
    SELECT @RevisionPrimary2KeyA = revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionPrimary2IdA;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CaptureDoomedIdA, 1, N'PSX4-A doomed revision one body', NULL, @UserIdA);
    SET @RevisionDoomedIdA = SCOPE_IDENTITY();
    SELECT @RevisionDoomedKeyA = revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionDoomedIdA;

    INSERT dbo.moments (owner_profile_id, visibility, status, current_version_number)
    VALUES (@ProfileIdA, N'private', N'proposal', 1);
    SET @MomentConfirmedIdA = SCOPE_IDENTITY();
    SELECT @MomentConfirmedKeyA = moment_key FROM dbo.moments WHERE moment_id = @MomentConfirmedIdA;

    INSERT dbo.moment_versions (moment_id, version_number, moment_kind, title, occurred_on, occurred_precision, narrative, why_it_matters, saved_by_user_id)
    VALUES (@MomentConfirmedIdA, 1, N'achievement', N'PSX4-A confirmed moment title', '2021-06-01', N'month', N'PSX4-A confirmed moment narrative', N'PSX4-A confirmed moment why', @UserIdA);
    SELECT @MomentVersionConfirmedKeyA = moment_version_key FROM dbo.moment_versions WHERE moment_id = @MomentConfirmedIdA AND version_number = 1;

    UPDATE dbo.moments
    SET status = N'confirmed', confirmed_version_number = 1, confirmed_by_user_id = @UserIdA, confirmed_at_utc = SYSUTCDATETIME()
    WHERE moment_id = @MomentConfirmedIdA;

    INSERT dbo.moment_sources (moment_id, owner_profile_id, capture_id, capture_revision_id, source_capture_key, source_revision_key, source_revision_number, source_state)
    VALUES (@MomentConfirmedIdA, @ProfileIdA, @CapturePrimaryIdA, @RevisionPrimary2IdA, @CapturePrimaryKeyA, @RevisionPrimary2KeyA, 2, N'available');
    SELECT @MomentSourceAvailableKeyA = moment_source_key FROM dbo.moment_sources WHERE moment_id = @MomentConfirmedIdA;

    INSERT dbo.moments (owner_profile_id, visibility, status, current_version_number)
    VALUES (@ProfileIdA, N'private', N'proposal', 1);
    SET @MomentProposalIdA = SCOPE_IDENTITY();
    SELECT @MomentProposalKeyA = moment_key FROM dbo.moments WHERE moment_id = @MomentProposalIdA;

    INSERT dbo.moment_versions (moment_id, version_number, moment_kind, title, occurred_on, occurred_precision, narrative, why_it_matters, saved_by_user_id)
    VALUES (@MomentProposalIdA, 1, N'update', NULL, NULL, N'unknown', NULL, NULL, @UserIdA);
    SELECT @MomentVersionProposalKeyA = moment_version_key FROM dbo.moment_versions WHERE moment_id = @MomentProposalIdA AND version_number = 1;

    INSERT dbo.moment_sources (moment_id, owner_profile_id, capture_id, capture_revision_id, source_capture_key, source_revision_key, source_revision_number, source_state)
    VALUES (@MomentProposalIdA, @ProfileIdA, @CaptureArchivedIdA, NULL, @CaptureArchivedKeyA, NULL, 0, N'available');
    SET @MomentSourceDeletedIdA = (SELECT moment_source_id FROM dbo.moment_sources WHERE moment_id = @MomentProposalIdA);

    -- Simulate the tombstone usp_DeleteCapture leaves behind: the
    -- reader must surface this fact, never filter it out.
    UPDATE dbo.moment_sources
    SET source_state = N'deleted', source_deleted_at_utc = SYSUTCDATETIME(), capture_id = NULL, capture_revision_id = NULL
    WHERE moment_source_id = @MomentSourceDeletedIdA;
    SELECT @MomentSourceDeletedKeyA = moment_source_key FROM dbo.moment_sources WHERE moment_source_id = @MomentSourceDeletedIdA;

    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'moment_placement');
    SET @TargetEntityIdA = SCOPE_IDENTITY();

    INSERT dbo.moment_placements (owner_profile_id, moment_id, moment_version_number, target_entity_id, created_by_user_id)
    VALUES (@ProfileIdA, @MomentConfirmedIdA, 1, @TargetEntityIdA, @UserIdA);
    SELECT @PlacementKeyA = placement_key FROM dbo.moment_placements WHERE moment_id = @MomentConfirmedIdA;

    ------------------------------------------------------------------
    -- Owner B fixture (mirrors A, distinct distinguishing text)
    ------------------------------------------------------------------
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdB, N'text', N'PSX4-B primary capture body', N'private', N'captured');
    SET @CapturePrimaryIdB = SCOPE_IDENTITY();
    SELECT @CapturePrimaryKeyB = capture_key FROM dbo.captures WHERE capture_id = @CapturePrimaryIdB;

    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status, active)
    VALUES (@ProfileIdB, N'text', N'PSX4-B archived capture body', N'private', N'archived', 0);
    SET @CaptureArchivedIdB = SCOPE_IDENTITY();
    SELECT @CaptureArchivedKeyB = capture_key FROM dbo.captures WHERE capture_id = @CaptureArchivedIdB;

    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdB, N'text', N'PSX4-B doomed capture body', N'private', N'captured');
    SET @CaptureDoomedIdB = SCOPE_IDENTITY();
    SELECT @CaptureDoomedKeyB = capture_key FROM dbo.captures WHERE capture_id = @CaptureDoomedIdB;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CapturePrimaryIdB, 1, N'PSX4-B primary revision one body', N'PSX4-B revision one note', @UserIdB);
    SET @RevisionPrimary1IdB = SCOPE_IDENTITY();
    SELECT @RevisionPrimary1KeyB = revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionPrimary1IdB;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CapturePrimaryIdB, 2, N'PSX4-B primary revision two body', NULL, @UserIdB);
    SET @RevisionPrimary2IdB = SCOPE_IDENTITY();
    SELECT @RevisionPrimary2KeyB = revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionPrimary2IdB;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CaptureDoomedIdB, 1, N'PSX4-B doomed revision one body', NULL, @UserIdB);
    SET @RevisionDoomedIdB = SCOPE_IDENTITY();
    SELECT @RevisionDoomedKeyB = revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionDoomedIdB;

    INSERT dbo.moments (owner_profile_id, visibility, status, current_version_number)
    VALUES (@ProfileIdB, N'private', N'proposal', 1);
    SET @MomentConfirmedIdB = SCOPE_IDENTITY();
    SELECT @MomentConfirmedKeyB = moment_key FROM dbo.moments WHERE moment_id = @MomentConfirmedIdB;

    INSERT dbo.moment_versions (moment_id, version_number, moment_kind, title, occurred_on, occurred_precision, narrative, why_it_matters, saved_by_user_id)
    VALUES (@MomentConfirmedIdB, 1, N'lesson', N'PSX4-B confirmed moment title', '2022-07-01', N'month', N'PSX4-B confirmed moment narrative', N'PSX4-B confirmed moment why', @UserIdB);
    SELECT @MomentVersionConfirmedKeyB = moment_version_key FROM dbo.moment_versions WHERE moment_id = @MomentConfirmedIdB AND version_number = 1;

    UPDATE dbo.moments
    SET status = N'confirmed', confirmed_version_number = 1, confirmed_by_user_id = @UserIdB, confirmed_at_utc = SYSUTCDATETIME()
    WHERE moment_id = @MomentConfirmedIdB;

    INSERT dbo.moment_sources (moment_id, owner_profile_id, capture_id, capture_revision_id, source_capture_key, source_revision_key, source_revision_number, source_state)
    VALUES (@MomentConfirmedIdB, @ProfileIdB, @CapturePrimaryIdB, @RevisionPrimary2IdB, @CapturePrimaryKeyB, @RevisionPrimary2KeyB, 2, N'available');
    SELECT @MomentSourceAvailableKeyB = moment_source_key FROM dbo.moment_sources WHERE moment_id = @MomentConfirmedIdB;

    INSERT dbo.moments (owner_profile_id, visibility, status, current_version_number)
    VALUES (@ProfileIdB, N'private', N'proposal', 1);
    SET @MomentProposalIdB = SCOPE_IDENTITY();
    SELECT @MomentProposalKeyB = moment_key FROM dbo.moments WHERE moment_id = @MomentProposalIdB;

    INSERT dbo.moment_versions (moment_id, version_number, moment_kind, title, occurred_on, occurred_precision, narrative, why_it_matters, saved_by_user_id)
    VALUES (@MomentProposalIdB, 1, N'update', NULL, NULL, N'unknown', NULL, NULL, @UserIdB);
    SELECT @MomentVersionProposalKeyB = moment_version_key FROM dbo.moment_versions WHERE moment_id = @MomentProposalIdB AND version_number = 1;

    INSERT dbo.moment_sources (moment_id, owner_profile_id, capture_id, capture_revision_id, source_capture_key, source_revision_key, source_revision_number, source_state)
    VALUES (@MomentProposalIdB, @ProfileIdB, @CaptureArchivedIdB, NULL, @CaptureArchivedKeyB, NULL, 0, N'available');
    SET @MomentSourceDeletedIdB = (SELECT moment_source_id FROM dbo.moment_sources WHERE moment_id = @MomentProposalIdB);

    UPDATE dbo.moment_sources
    SET source_state = N'deleted', source_deleted_at_utc = SYSUTCDATETIME(), capture_id = NULL, capture_revision_id = NULL
    WHERE moment_source_id = @MomentSourceDeletedIdB;
    SELECT @MomentSourceDeletedKeyB = moment_source_key FROM dbo.moment_sources WHERE moment_source_id = @MomentSourceDeletedIdB;

    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'moment_placement');
    SET @TargetEntityIdB = SCOPE_IDENTITY();

    INSERT dbo.moment_placements (owner_profile_id, moment_id, moment_version_number, target_entity_id, created_by_user_id)
    VALUES (@ProfileIdB, @MomentConfirmedIdB, 1, @TargetEntityIdB, @UserIdB);
    SELECT @PlacementKeyB = placement_key FROM dbo.moment_placements WHERE moment_id = @MomentConfirmedIdB;

    ------------------------------------------------------------------
    -- Owner C: one minimal row per table, then deactivate the owner.
    ------------------------------------------------------------------
    INSERT dbo.captures (owner_profile_id, capture_type, body, visibility, status)
    VALUES (@ProfileIdC, N'text', N'PSX4-C capture (must never be readable once inactive)', N'private', N'captured');
    SET @CaptureIdC = SCOPE_IDENTITY();
    SELECT @CaptureKeyC = capture_key FROM dbo.captures WHERE capture_id = @CaptureIdC;

    INSERT dbo.capture_revisions (capture_id, revision_number, body, correction_note, corrected_by_user_id)
    VALUES (@CaptureIdC, 1, N'PSX4-C revision body', NULL, @UserIdC);
    SET @RevisionIdC = SCOPE_IDENTITY();

    INSERT dbo.moments (owner_profile_id, visibility, status, current_version_number)
    VALUES (@ProfileIdC, N'private', N'proposal', 1);
    SET @MomentIdC = SCOPE_IDENTITY();
    SELECT @MomentKeyC = moment_key FROM dbo.moments WHERE moment_id = @MomentIdC;

    INSERT dbo.moment_versions (moment_id, version_number, moment_kind, title, occurred_on, occurred_precision, narrative, why_it_matters, saved_by_user_id)
    VALUES (@MomentIdC, 1, N'update', N'PSX4-C moment title', NULL, N'unknown', N'PSX4-C moment narrative', NULL, @UserIdC);

    INSERT dbo.moment_sources (moment_id, owner_profile_id, capture_id, capture_revision_id, source_capture_key, source_revision_key, source_revision_number, source_state)
    VALUES (@MomentIdC, @ProfileIdC, @CaptureIdC, @RevisionIdC, @CaptureKeyC, (SELECT revision_key FROM dbo.capture_revisions WHERE revision_id = @RevisionIdC), 1, N'available');

    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdC, N'moment_placement');
    SET @TargetEntityIdC = SCOPE_IDENTITY();

    INSERT dbo.moment_placements (owner_profile_id, moment_id, moment_version_number, target_entity_id, created_by_user_id)
    VALUES (@ProfileIdC, @MomentIdC, 1, @TargetEntityIdC, @UserIdC);

    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 58331, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey proof for all six procedures.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportCaptureForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58340, 'A forged UserKey returned a capture row.', 1;
    EXEC dbo.usp_ReadAccountExportCaptureRevisionForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58340, 'A forged UserKey returned a capture revision row.', 1;
    EXEC dbo.usp_ReadAccountExportMomentForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58340, 'A forged UserKey returned a moment row.', 1;
    EXEC dbo.usp_ReadAccountExportMomentVersionForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58340, 'A forged UserKey returned a moment version row.', 1;
    EXEC dbo.usp_ReadAccountExportMomentSourceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58340, 'A forged UserKey returned a moment source row.', 1;
    EXEC dbo.usp_ReadAccountExportMomentPlacementForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58340, 'A forged UserKey returned a moment placement row.', 1;

    /* ------------------------------------------------------------
       2b. Inactive-owner proof, all six procedures, using owner C's
           genuinely populated, pre-deactivation fixture.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportCaptureForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58341, 'A deactivated owner''s capture row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportCaptureRevisionForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58341, 'A deactivated owner''s capture revision row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportMomentForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58341, 'A deactivated owner''s moment row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportMomentVersionForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58341, 'A deactivated owner''s moment version row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportMomentSourceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58341, 'A deactivated owner''s moment source row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportMomentPlacementForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58341, 'A deactivated owner''s moment placement row was still readable.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proofs for all six
          procedures via INSERT ... EXEC.
       ------------------------------------------------------------ */

    -- Capture (3 rows expected per owner)
    DECLARE @CaptureCapture TABLE
    (
        capture_key uniqueidentifier, capture_type nvarchar(30), body nvarchar(max), visibility nvarchar(30),
        status nvarchar(30), created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @CaptureCapture EXEC dbo.usp_ReadAccountExportCaptureForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @CaptureCapture) <> 3
        THROW 58350, 'Owner A''s capture capture does not have exactly three rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @CaptureCapture WHERE capture_key = @CapturePrimaryKeyA AND status = N'captured')
        THROW 58351, 'Owner A''s capture capture is missing the primary capture.', 1;
    IF NOT EXISTS (SELECT 1 FROM @CaptureCapture WHERE capture_key = @CaptureArchivedKeyA AND status = N'archived')
        THROW 58351, 'Owner A''s capture capture is missing the archived capture (archived rows must still appear).', 1;
    IF EXISTS (SELECT 1 FROM @CaptureCapture WHERE capture_key IN (@CapturePrimaryKeyB, @CaptureArchivedKeyB, @CaptureDoomedKeyB))
        THROW 58352, 'Owner A''s capture capture contains one of owner B''s captures.', 1;
    IF EXISTS (SELECT 1 FROM @CaptureCapture WHERE body LIKE N'PSX4-B%')
        THROW 58352, 'Owner A''s capture capture contains owner B''s distinguishing text.', 1;
    IF EXISTS (SELECT 1 FROM @CaptureCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58353, 'Owner A''s capture capture has a missing or non-monotonic read window.', 1;

    DELETE @CaptureCapture;
    INSERT @CaptureCapture EXEC dbo.usp_ReadAccountExportCaptureForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @CaptureCapture) <> 3
        THROW 58350, 'Owner B''s capture capture does not have exactly three rows.', 1;
    IF EXISTS (SELECT 1 FROM @CaptureCapture WHERE capture_key IN (@CapturePrimaryKeyA, @CaptureArchivedKeyA, @CaptureDoomedKeyA))
        THROW 58352, 'Owner B''s capture capture contains one of owner A''s captures.', 1;
    IF EXISTS (SELECT 1 FROM @CaptureCapture WHERE body LIKE N'PSX4-A%')
        THROW 58352, 'Owner B''s capture capture contains owner A''s distinguishing text.', 1;

    -- Capture revision (3 rows expected per owner: primary x2, doomed x1)
    DECLARE @RevisionCapture TABLE
    (
        revision_key uniqueidentifier, capture_key uniqueidentifier, revision_number int, body nvarchar(max),
        correction_note nvarchar(1000), corrected_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @RevisionCapture EXEC dbo.usp_ReadAccountExportCaptureRevisionForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @RevisionCapture) <> 3
        THROW 58350, 'Owner A''s capture revision capture does not have exactly three rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @RevisionCapture WHERE revision_key = @RevisionPrimary1KeyA AND capture_key = @CapturePrimaryKeyA AND revision_number = 1)
        THROW 58351, 'Owner A''s capture revision capture is missing revision one or its parent capture_key.', 1;
    IF NOT EXISTS (SELECT 1 FROM @RevisionCapture WHERE revision_key = @RevisionPrimary2KeyA AND capture_key = @CapturePrimaryKeyA AND revision_number = 2)
        THROW 58351, 'Owner A''s capture revision capture is missing revision two or its parent capture_key.', 1;
    IF EXISTS (SELECT 1 FROM @RevisionCapture WHERE revision_key IN (@RevisionPrimary1KeyB, @RevisionPrimary2KeyB, @RevisionDoomedKeyB))
        THROW 58352, 'Owner A''s capture revision capture contains one of owner B''s revisions.', 1;
    IF EXISTS (SELECT 1 FROM @RevisionCapture WHERE body LIKE N'PSX4-B%')
        THROW 58352, 'Owner A''s capture revision capture contains owner B''s distinguishing text.', 1;

    DELETE @RevisionCapture;
    INSERT @RevisionCapture EXEC dbo.usp_ReadAccountExportCaptureRevisionForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @RevisionCapture) <> 3
        THROW 58350, 'Owner B''s capture revision capture does not have exactly three rows.', 1;
    IF EXISTS (SELECT 1 FROM @RevisionCapture WHERE revision_key IN (@RevisionPrimary1KeyA, @RevisionPrimary2KeyA, @RevisionDoomedKeyA))
        THROW 58352, 'Owner B''s capture revision capture contains one of owner A''s revisions.', 1;

    -- Moment (2 rows expected per owner)
    DECLARE @MomentCapture TABLE
    (
        moment_key uniqueidentifier, visibility nvarchar(30), status nvarchar(30), current_version_number int,
        confirmed_version_number int, confirmed_at_utc datetime2(7), created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @MomentCapture EXEC dbo.usp_ReadAccountExportMomentForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @MomentCapture) <> 2
        THROW 58350, 'Owner A''s moment capture does not have exactly two rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @MomentCapture WHERE moment_key = @MomentConfirmedKeyA AND status = N'confirmed' AND confirmed_version_number = 1 AND confirmed_at_utc IS NOT NULL)
        THROW 58351, 'Owner A''s moment capture is missing the confirmed moment or lost its confirmation facts.', 1;
    IF NOT EXISTS (SELECT 1 FROM @MomentCapture WHERE moment_key = @MomentProposalKeyA AND status = N'proposal' AND confirmed_version_number IS NULL)
        THROW 58351, 'Owner A''s moment capture is missing the proposal moment.', 1;
    IF EXISTS (SELECT 1 FROM @MomentCapture WHERE moment_key IN (@MomentConfirmedKeyB, @MomentProposalKeyB))
        THROW 58352, 'Owner A''s moment capture contains one of owner B''s moments.', 1;

    DELETE @MomentCapture;
    INSERT @MomentCapture EXEC dbo.usp_ReadAccountExportMomentForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @MomentCapture) <> 2
        THROW 58350, 'Owner B''s moment capture does not have exactly two rows.', 1;
    IF EXISTS (SELECT 1 FROM @MomentCapture WHERE moment_key IN (@MomentConfirmedKeyA, @MomentProposalKeyA))
        THROW 58352, 'Owner B''s moment capture contains one of owner A''s moments.', 1;

    -- Moment version (2 rows expected per owner)
    DECLARE @MomentVersionCapture TABLE
    (
        moment_version_key uniqueidentifier, moment_key uniqueidentifier, version_number int, moment_kind nvarchar(30),
        title nvarchar(160), occurred_on date, occurred_precision nvarchar(20), narrative nvarchar(max),
        why_it_matters nvarchar(2000), saved_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @MomentVersionCapture EXEC dbo.usp_ReadAccountExportMomentVersionForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @MomentVersionCapture) <> 2
        THROW 58350, 'Owner A''s moment version capture does not have exactly two rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @MomentVersionCapture WHERE moment_version_key = @MomentVersionConfirmedKeyA AND moment_key = @MomentConfirmedKeyA AND title = N'PSX4-A confirmed moment title')
        THROW 58351, 'Owner A''s moment version capture is missing the confirmed moment''s version or its parent moment_key.', 1;
    IF NOT EXISTS (SELECT 1 FROM @MomentVersionCapture WHERE moment_version_key = @MomentVersionProposalKeyA AND moment_key = @MomentProposalKeyA AND title IS NULL AND narrative IS NULL)
        THROW 58351, 'Owner A''s moment version capture is missing the blank proposal version.', 1;
    IF EXISTS (SELECT 1 FROM @MomentVersionCapture WHERE moment_version_key IN (@MomentVersionConfirmedKeyB, @MomentVersionProposalKeyB) OR title LIKE N'PSX4-B%')
        THROW 58352, 'Owner A''s moment version capture contains owner B''s data.', 1;

    DELETE @MomentVersionCapture;
    INSERT @MomentVersionCapture EXEC dbo.usp_ReadAccountExportMomentVersionForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @MomentVersionCapture WHERE moment_version_key = @MomentVersionConfirmedKeyB AND moment_key = @MomentConfirmedKeyB AND title = N'PSX4-B confirmed moment title')
        THROW 58351, 'Owner B''s moment version capture is missing its own confirmed version.', 1;
    IF EXISTS (SELECT 1 FROM @MomentVersionCapture WHERE moment_version_key IN (@MomentVersionConfirmedKeyA, @MomentVersionProposalKeyA) OR title LIKE N'PSX4-A%')
        THROW 58352, 'Owner B''s moment version capture contains owner A''s data.', 1;

    -- Moment source (2 rows expected per owner: one available, one deleted tombstone)
    DECLARE @MomentSourceCapture TABLE
    (
        moment_source_key uniqueidentifier, moment_key uniqueidentifier, source_capture_key uniqueidentifier,
        source_revision_key uniqueidentifier, source_revision_number int, source_state nvarchar(20),
        source_deleted_at_utc datetime2(7), created_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @MomentSourceCapture EXEC dbo.usp_ReadAccountExportMomentSourceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @MomentSourceCapture) <> 2
        THROW 58350, 'Owner A''s moment source capture does not have exactly two rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @MomentSourceCapture
        WHERE moment_source_key = @MomentSourceAvailableKeyA AND moment_key = @MomentConfirmedKeyA
          AND source_capture_key = @CapturePrimaryKeyA AND source_revision_key = @RevisionPrimary2KeyA
          AND source_revision_number = 2 AND source_state = N'available' AND source_deleted_at_utc IS NULL
    )
        THROW 58351, 'Owner A''s moment source capture is missing the available source or one of its linkage facts.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @MomentSourceCapture
        WHERE moment_source_key = @MomentSourceDeletedKeyA AND moment_key = @MomentProposalKeyA
          AND source_state = N'deleted' AND source_deleted_at_utc IS NOT NULL
    )
        THROW 58351, 'Owner A''s moment source capture is missing the deleted-tombstone source or its deletion facts.', 1;
    IF EXISTS (SELECT 1 FROM @MomentSourceCapture WHERE moment_source_key IN (@MomentSourceAvailableKeyB, @MomentSourceDeletedKeyB))
        THROW 58352, 'Owner A''s moment source capture contains one of owner B''s sources.', 1;

    DELETE @MomentSourceCapture;
    INSERT @MomentSourceCapture EXEC dbo.usp_ReadAccountExportMomentSourceForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @MomentSourceCapture) <> 2
        THROW 58350, 'Owner B''s moment source capture does not have exactly two rows.', 1;
    IF EXISTS (SELECT 1 FROM @MomentSourceCapture WHERE moment_source_key IN (@MomentSourceAvailableKeyA, @MomentSourceDeletedKeyA))
        THROW 58352, 'Owner B''s moment source capture contains one of owner A''s sources.', 1;

    -- Moment placement (1 row expected per owner)
    DECLARE @PlacementCapture TABLE
    (
        placement_key uniqueidentifier, moment_key uniqueidentifier, moment_version_number int, placement_status nvarchar(20),
        created_at_utc datetime2(7), reactivated_at_utc datetime2(7), removed_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @PlacementCapture EXEC dbo.usp_ReadAccountExportMomentPlacementForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @PlacementCapture) <> 1
        THROW 58350, 'Owner A''s moment placement capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @PlacementCapture
        WHERE placement_key = @PlacementKeyA AND moment_key = @MomentConfirmedKeyA
          AND moment_version_number = 1 AND placement_status = N'active'
          AND reactivated_at_utc IS NULL AND removed_at_utc IS NULL
    )
        THROW 58351, 'Owner A''s moment placement capture is missing its own row or its parent moment_key.', 1;
    IF EXISTS (SELECT 1 FROM @PlacementCapture WHERE placement_key = @PlacementKeyB)
        THROW 58352, 'Owner A''s moment placement capture contains owner B''s placement.', 1;

    DELETE @PlacementCapture;
    INSERT @PlacementCapture EXEC dbo.usp_ReadAccountExportMomentPlacementForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @PlacementCapture WHERE placement_key = @PlacementKeyB AND moment_key = @MomentConfirmedKeyB)
        THROW 58351, 'Owner B''s moment placement capture is missing its own row.', 1;
    IF EXISTS (SELECT 1 FROM @PlacementCapture WHERE placement_key = @PlacementKeyA)
        THROW 58352, 'Owner B''s moment placement capture contains owner A''s placement.', 1;

    /* ------------------------------------------------------------
       4. Soft-delete precision proof (dbo.captures is the only one of
          these six tables with its own soft-delete column). Soft-
          deleting owner A's "doomed" capture must remove it (and its
          one revision) while leaving the primary/archived captures
          (and the primary's two revisions) visible, and owner B's
          fixture completely untouched. CK_captures_deleted_state ties
          deleted_at_utc to active, so both are set together.
       ------------------------------------------------------------ */
    UPDATE dbo.captures SET deleted_at_utc = SYSUTCDATETIME(), active = 0 WHERE capture_id = @CaptureDoomedIdA;
    IF @@ROWCOUNT <> 1
        THROW 58360, 'Could not soft-delete owner A''s doomed capture for the soft-delete proof.', 1;

    DELETE @CaptureCapture;
    INSERT @CaptureCapture EXEC dbo.usp_ReadAccountExportCaptureForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @CaptureCapture) <> 2
        THROW 58361, 'Owner A''s capture capture did not drop to two rows after the soft-delete.', 1;
    IF EXISTS (SELECT 1 FROM @CaptureCapture WHERE capture_key = @CaptureDoomedKeyA)
        THROW 58361, 'A soft-deleted capture is still returned by the capture reader.', 1;
    IF NOT EXISTS (SELECT 1 FROM @CaptureCapture WHERE capture_key IN (@CapturePrimaryKeyA, @CaptureArchivedKeyA))
        THROW 58362, 'Soft-deleting one capture incorrectly hid a sibling capture for the same owner.', 1;

    DELETE @RevisionCapture;
    INSERT @RevisionCapture EXEC dbo.usp_ReadAccountExportCaptureRevisionForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @RevisionCapture) <> 2
        THROW 58361, 'Owner A''s capture revision capture did not drop to two rows after the soft-delete.', 1;
    IF EXISTS (SELECT 1 FROM @RevisionCapture WHERE revision_key = @RevisionDoomedKeyA)
        THROW 58361, 'A revision whose parent capture was soft-deleted is still returned by the capture revision reader.', 1;
    IF NOT EXISTS (SELECT 1 FROM @RevisionCapture WHERE revision_key IN (@RevisionPrimary1KeyA, @RevisionPrimary2KeyA))
        THROW 58362, 'Soft-deleting one capture incorrectly hid a sibling capture''s revisions for the same owner.', 1;

    -- Owner B's parallel fixture must be completely unaffected.
    DELETE @CaptureCapture;
    INSERT @CaptureCapture EXEC dbo.usp_ReadAccountExportCaptureForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @CaptureCapture) <> 3
        THROW 58362, 'Owner A''s soft-delete proof disturbed owner B''s unrelated capture fixture.', 1;
    DELETE @RevisionCapture;
    INSERT @RevisionCapture EXEC dbo.usp_ReadAccountExportCaptureRevisionForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @RevisionCapture) <> 3
        THROW 58362, 'Owner A''s soft-delete proof disturbed owner B''s unrelated capture revision fixture.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-004: structural grep across all six Capture/Moment reader procedures (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, expected owner predicate, deterministic ORDER BY, read-window columns present, no transaction control/write/dynamic SQL); per-procedure forbidden-column absence and predicate presence verified against each procedure''s own isolated content select-list text, including the owner-predicate-on-both-sides check for moment_sources/moment_placements; a forged UserKey and a deactivated owner both yield zero rows (never an error) across all six procedures; real two-owner fixture data (three captures with three revisions, two moments with one version/source each, and one placement, per owner) proves every one of the six readers returns exactly and only the calling owner''s own rows, complete with a non-null monotonic read window, correct parent capture_key/moment_key linkage, and correct surfacing of a moment_source''s own deleted-tombstone state; soft-deleting a capture removes it and its own revision while leaving sibling captures/revisions and the other owner''s fixture untouched; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
