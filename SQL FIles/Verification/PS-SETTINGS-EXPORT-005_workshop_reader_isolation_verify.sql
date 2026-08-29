/* PS-SETTINGS-EXPORT-005 (account export Workshop / My Knowledge readers)
   production-safe owner-isolation verification.

   House pattern (PS-SETTINGS-EXPORT-004_capture_moment_reader_isolation_verify.sql):
   two synthetic owners (A, B) plus a third (C, deactivated after its
   fixture is created) via a throwaway auth provider, one outer
   always-rolled-back transaction, fresh THROW numbers in the
   58500-58599 block (clear of this package's own migration/rollback
   58400-58499 range and of every sibling verification file's range --
   highest prior use anywhere under SQL FIles/ is 58362).

   No soft-delete section exists in this script, unlike the capture/
   moment verifier. Neither dbo.knowledge_items nor
   dbo.knowledge_item_versions has a deleted_at_utc column of any kind
   (PS-WORKSHOP-001's own header: deletion is a plain hard DELETE, W4's
   future problem, not this package's); dbo.knowledge_items' own
   archived_at_utc/archived_by_user_id record a REAL, undeleted state
   (like dbo.captures.status = 'archived') and are proved as CONTENT
   below, never as a presence predicate.

   Read-window design note (why this script can use INSERT ... EXEC
   freely): both readers under test return their read window as two
   TRAILING COLUMNS on their single content result set, never a second
   result set and never OUTPUT parameters (see the migration file's own
   header). This script uses BARE EXEC for both procedures at least
   once (the forged-@UserKey and deactivated-owner proofs, checked via
   @@ROWCOUNT immediately after the call) and INSERT ... EXEC for the
   real, two-owner, field-value-level isolation proofs, which need
   actual captured rows.

   Proof strategy:
     0. STRUCTURAL, looped across both procedure names: exact
        "@UserKey nvarchar(300)" signature and no other parameter; the
        byte-identical identity-resolution header is present verbatim;
        the reader's primary owner-scoping predicate appears; an
        explicit ORDER BY is present; the read-window columns are
        present; and -- the load-bearing structural tripwire -- no
        transaction-control keyword, write, or nested EXEC/dynamic SQL
        appears anywhere in the body.
     0b. Per-procedure, explicit (not looped -- the forbidden-list,
        FROM-anchor, and owner-predicate shape genuinely differ per
        procedure): the content SELECT list -- located precisely as the
        text between the shared identity header's closing
        "IF @ProfileId IS NULL RETURN;" line and the procedure's own
        first subsequent "FROM dbo.<table>" -- never contains a
        forbidden column's fully-qualified reference; the
        knowledge_item reader's own visibility predicate is present;
        and the knowledge_item_version reader carries the owner
        predicate on BOTH sides of its parent join (it independently
        carries its own owner_profile_id column, unlike
        dbo.capture_revisions/dbo.moment_versions in the sibling
        packages -- confirmed by reading PS-WORKSHOP-001's own DDL
        before writing this script, not assumed).
     1. Two synthetic owners (A, B) each get three dbo.knowledge_items
        rows -- a "confirmed" one with one version, an "unfinished" one
        with two versions (proving the parent-then-sequence ORDER BY
        and non-default body_format/authored_via decoding), and an
        "archived, never confirmed" one with one version -- four
        dbo.knowledge_item_versions rows per owner in total. A third
        owner (C) gets one minimal item and version, is then
        deactivated, and must read as zero rows across both procedures
        thereafter even though every row still physically exists.
        Every NOT NULL no-DEFAULT column, CHECK constraint, and FOREIGN
        KEY on dbo.knowledge_items and dbo.knowledge_item_versions was
        re-read from PS-WORKSHOP-001_knowledge_items.sql before writing
        any INSERT below -- in particular
        CK_knowledge_items_confirmation_state (which ties
        confirmed_version_number/confirmed_by_user_id/confirmed_at_utc
        to item_status as a strict tri-state, not three independent
        nullable columns) and CK_knowledge_items_archive_pair (which
        ties archived_at_utc/archived_by_user_id together), and the
        composite FK_knowledge_item_versions_item foreign key
        (knowledge_item_id, owner_profile_id) -> dbo.knowledge_items
        (knowledge_item_id, owner_profile_id), which is exactly why
        dbo.knowledge_item_versions carries its own owner_profile_id at
        all and why every version INSERT below supplies the SAME
        owner_profile_id as its parent item.
     2. DATA-LEVEL, for BOTH procedures: calling as owner A must return
        exactly owner A's own row(s), carrying every distinguishing
        fixture value including correct parent knowledge_item_key
        linkage, and must NEVER contain any value or key unique to
        owner B's fixture -- and symmetrically for B. Every fixture
        row's identifying key is captured immediately after insert (via
        SCOPE_IDENTITY() then a follow-up SELECT of the opaque key, the
        same idiom every prior package's verification script uses) and
        it is that captured key -- never a guessed or literal constant
        -- that every assertion below checks for.
        dbo.knowledge_item_versions carries no opaque key column of its
        own (unlike dbo.capture_revisions.revision_key or
        dbo.moment_versions.moment_version_key); its exported
        identifying tuple is (knowledge_item_key, version_number),
        already unique per UQ_knowledge_item_versions_number, so this
        script asserts against that tuple directly rather than a
        manufactured key that does not exist in the schema.

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-005')
        THROW 58500, 'PS-SETTINGS-EXPORT-005 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof, looped across both procedures.
       ------------------------------------------------------------ */
    DECLARE @ReaderNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY, owner_predicate nvarchar(120) NOT NULL);
    INSERT @ReaderNames (procedure_name, owner_predicate)
    VALUES
        (N'usp_ReadAccountExportKnowledgeItemForOwner', N'item.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportKnowledgeItemVersionForOwner', N'version_record.owner_profile_id = @ProfileId');

    IF (SELECT COUNT(*) FROM @ReaderNames) <> 2
        THROW 58501, 'The reader-name fixture itself is incomplete.', 1;

    DECLARE @CheckName sysname;
    DECLARE @CheckOwnerPredicate nvarchar(120);
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ReaderNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name, @CheckOwnerPredicate = owner_predicate
        FROM @ReaderNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 58502, 'A required account-export Workshop reader procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 58503, 'A Workshop reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
        IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
            THROW 58503, 'A Workshop reader procedure declares more than just @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%@OwnerUserId%'
           OR @CheckDefinition LIKE N'%@TableName%'
           OR @CheckDefinition LIKE N'%@KnowledgeItemKey%'
            THROW 58503, 'A Workshop reader procedure accepts a caller-supplied owner id or target.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 58504, 'A Workshop reader procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
           OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
            THROW 58504, 'A Workshop reader procedure does not require an active user AND an active profile.', 1;
        IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
            THROW 58504, 'A Workshop reader procedure does not use the shared byte-identical identity header.', 1;
        IF @CheckDefinition NOT LIKE N'%' + @CheckOwnerPredicate + N'%'
            THROW 58505, 'A Workshop reader procedure does not filter by its expected owner predicate.', 1;
        IF @CheckDefinition NOT LIKE N'%ORDER BY%'
            THROW 58506, 'A Workshop reader procedure has no deterministic ORDER BY.', 1;
        IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
            THROW 58506, 'A Workshop reader procedure uses SELECT * instead of an explicit column list.', 1;
        IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
            THROW 58507, 'A Workshop reader procedure does not return the read-window columns.', 1;
        IF @CheckDefinition LIKE N'%BEGIN TRAN%'
           OR @CheckDefinition LIKE N'%COMMIT%'
           OR @CheckDefinition LIKE N'%ROLLBACK%'
           OR @CheckDefinition LIKE N'%BEGIN TRY%'
           OR @CheckDefinition LIKE N'%BEGIN CATCH%'
           OR @CheckDefinition LIKE N'%INSERT %'
           OR @CheckDefinition LIKE N'%UPDATE %'
           OR @CheckDefinition LIKE N'%DELETE %'
           OR @CheckDefinition LIKE N'%EXEC%'
            THROW 58508, 'A Workshop reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;
        IF @CheckDefinition LIKE N'%deleted_at_utc%'
            THROW 58508, 'A Workshop reader procedure references a soft-delete column that does not exist on either claimed table.', 1;

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

    -- Knowledge item: forbidden knowledge_item_id/owner_profile_id/
    -- confirmed_by_user_id/archived_by_user_id/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportKnowledgeItemForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.knowledge_items AS item', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58520, 'Could not locate the knowledge item reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%item.knowledge_item_id%' OR @SelectList LIKE N'%item.owner_profile_id%'
       OR @SelectList LIKE N'%item.confirmed_by_user_id%' OR @SelectList LIKE N'%item.archived_by_user_id%'
       OR @SelectList LIKE N'%item.row_version%'
        THROW 58520, 'The knowledge item reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%item.visibility = N''private''%'
        THROW 58520, 'The knowledge item reader is missing its explicit visibility = ''private'' predicate.', 1;

    -- Knowledge item version: forbidden knowledge_item_version_id/
    -- knowledge_item_id/version_record.owner_profile_id (as output)/
    -- saved_by_user_id/row_version/item.knowledge_item_id (as output)/
    -- item.owner_profile_id (as output).
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.knowledge_item_versions AS version_record', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58521, 'Could not locate the knowledge item version reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%version_record.knowledge_item_version_id%'
       OR @SelectList LIKE N'%version_record.knowledge_item_id%'
       OR @SelectList LIKE N'%version_record.owner_profile_id%'
       OR @SelectList LIKE N'%version_record.saved_by_user_id%'
       OR @SelectList LIKE N'%version_record.row_version%'
       OR @SelectList LIKE N'%item.owner_profile_id%'
       OR @SelectList LIKE N'%item.knowledge_item_id%'
        THROW 58521, 'The knowledge item version reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%JOIN dbo.knowledge_items AS item%'
        THROW 58521, 'The knowledge item version reader does not join its parent for linkage.', 1;
    IF @CheckDefinition NOT LIKE N'%version_record.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%item.owner_profile_id = @ProfileId%'
        THROW 58521, 'The knowledge item version reader is missing the owner predicate on both sides of its parent join.', 1;
    IF @CheckDefinition NOT LIKE N'%item.visibility = N''private''%'
        THROW 58521, 'The knowledge item version reader is missing the joined item''s explicit visibility = ''private'' predicate.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x5-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x5-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x5-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x5-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x5-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX5 Owner A', @Email = N'psx5-owner-a@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x5-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX5 Owner B', @Email = N'psx5-owner-b@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x5-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX5 Owner C';

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
    WHERE identity_row.provider = N'settings-export-x5-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x5-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x5-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 58530, 'Synthetic Workshop verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture. Every NOT NULL no-DEFAULT column, CHECK constraint, and
       FOREIGN KEY on dbo.knowledge_items and dbo.knowledge_item_versions
       was re-read from PS-WORKSHOP-001_knowledge_items.sql before
       writing any INSERT below.
       ------------------------------------------------------------ */
    DECLARE @ItemConfirmedIdA bigint, @ItemConfirmedKeyA uniqueidentifier;
    DECLARE @ItemMultiIdA bigint, @ItemMultiKeyA uniqueidentifier;
    DECLARE @ItemArchivedIdA bigint, @ItemArchivedKeyA uniqueidentifier;

    DECLARE @ItemConfirmedIdB bigint, @ItemConfirmedKeyB uniqueidentifier;
    DECLARE @ItemMultiIdB bigint, @ItemMultiKeyB uniqueidentifier;
    DECLARE @ItemArchivedIdB bigint, @ItemArchivedKeyB uniqueidentifier;

    DECLARE @ItemIdC bigint, @ItemKeyC uniqueidentifier;

    ------------------------------------------------------------------
    -- Owner A fixture
    ------------------------------------------------------------------
    INSERT dbo.knowledge_items (owner_profile_id, classification)
    VALUES (@ProfileIdA, N'work');
    SET @ItemConfirmedIdA = SCOPE_IDENTITY();
    SELECT @ItemConfirmedKeyA = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemConfirmedIdA;
    UPDATE dbo.knowledge_items
    SET item_status = N'confirmed', confirmed_version_number = 1, confirmed_by_user_id = @UserIdA, confirmed_at_utc = SYSUTCDATETIME()
    WHERE knowledge_item_id = @ItemConfirmedIdA;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemConfirmedIdA, @ProfileIdA, 1, N'PSX5-A confirmed item title', N'PSX5-A confirmed item approved wording', N'PSX5-A confirmed item original wording', N'plain', N'typed', @UserIdA);

    INSERT dbo.knowledge_items (owner_profile_id, classification)
    VALUES (@ProfileIdA, N'personal');
    SET @ItemMultiIdA = SCOPE_IDENTITY();
    SELECT @ItemMultiKeyA = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemMultiIdA;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemMultiIdA, @ProfileIdA, 1, N'PSX5-A multi item v1 title', N'PSX5-A multi item v1 approved wording', N'PSX5-A multi item v1 original wording', N'plain', N'typed', @UserIdA);
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemMultiIdA, @ProfileIdA, 2, N'PSX5-A multi item v2 title', N'PSX5-A multi item v2 approved wording', N'PSX5-A multi item v2 original wording', N'rich', N'spoken', @UserIdA);
    UPDATE dbo.knowledge_items SET current_version_number = 2 WHERE knowledge_item_id = @ItemMultiIdA;

    INSERT dbo.knowledge_items (owner_profile_id, classification)
    VALUES (@ProfileIdA, N'both');
    SET @ItemArchivedIdA = SCOPE_IDENTITY();
    SELECT @ItemArchivedKeyA = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemArchivedIdA;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemArchivedIdA, @ProfileIdA, 1, N'PSX5-A archived item title', N'PSX5-A archived item approved wording', N'PSX5-A archived item original wording', N'plain', N'typed', @UserIdA);
    UPDATE dbo.knowledge_items
    SET item_status = N'archived', archived_at_utc = SYSUTCDATETIME(), archived_by_user_id = @UserIdA
    WHERE knowledge_item_id = @ItemArchivedIdA;

    ------------------------------------------------------------------
    -- Owner B fixture (mirrors A, distinct distinguishing text)
    ------------------------------------------------------------------
    INSERT dbo.knowledge_items (owner_profile_id, classification)
    VALUES (@ProfileIdB, N'work');
    SET @ItemConfirmedIdB = SCOPE_IDENTITY();
    SELECT @ItemConfirmedKeyB = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemConfirmedIdB;
    UPDATE dbo.knowledge_items
    SET item_status = N'confirmed', confirmed_version_number = 1, confirmed_by_user_id = @UserIdB, confirmed_at_utc = SYSUTCDATETIME()
    WHERE knowledge_item_id = @ItemConfirmedIdB;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemConfirmedIdB, @ProfileIdB, 1, N'PSX5-B confirmed item title', N'PSX5-B confirmed item approved wording', N'PSX5-B confirmed item original wording', N'plain', N'typed', @UserIdB);

    INSERT dbo.knowledge_items (owner_profile_id, classification)
    VALUES (@ProfileIdB, N'personal');
    SET @ItemMultiIdB = SCOPE_IDENTITY();
    SELECT @ItemMultiKeyB = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemMultiIdB;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemMultiIdB, @ProfileIdB, 1, N'PSX5-B multi item v1 title', N'PSX5-B multi item v1 approved wording', N'PSX5-B multi item v1 original wording', N'plain', N'typed', @UserIdB);
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemMultiIdB, @ProfileIdB, 2, N'PSX5-B multi item v2 title', N'PSX5-B multi item v2 approved wording', N'PSX5-B multi item v2 original wording', N'rich', N'spoken', @UserIdB);
    UPDATE dbo.knowledge_items SET current_version_number = 2 WHERE knowledge_item_id = @ItemMultiIdB;

    INSERT dbo.knowledge_items (owner_profile_id, classification)
    VALUES (@ProfileIdB, N'both');
    SET @ItemArchivedIdB = SCOPE_IDENTITY();
    SELECT @ItemArchivedKeyB = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemArchivedIdB;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemArchivedIdB, @ProfileIdB, 1, N'PSX5-B archived item title', N'PSX5-B archived item approved wording', N'PSX5-B archived item original wording', N'plain', N'typed', @UserIdB);
    UPDATE dbo.knowledge_items
    SET item_status = N'archived', archived_at_utc = SYSUTCDATETIME(), archived_by_user_id = @UserIdB
    WHERE knowledge_item_id = @ItemArchivedIdB;

    ------------------------------------------------------------------
    -- Owner C: one minimal item and version, then deactivate the owner.
    ------------------------------------------------------------------
    INSERT dbo.knowledge_items (owner_profile_id)
    VALUES (@ProfileIdC);
    SET @ItemIdC = SCOPE_IDENTITY();
    SELECT @ItemKeyC = knowledge_item_key FROM dbo.knowledge_items WHERE knowledge_item_id = @ItemIdC;
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title, approved_wording, original_member_wording, body_format, authored_via, saved_by_user_id)
    VALUES
        (@ItemIdC, @ProfileIdC, 1, N'PSX5-C item (must never be readable once inactive)', N'PSX5-C approved wording', N'PSX5-C original wording', N'plain', N'typed', @UserIdC);

    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 58531, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey proof for both procedures.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportKnowledgeItemForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58540, 'A forged UserKey returned a knowledge item row.', 1;
    EXEC dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58540, 'A forged UserKey returned a knowledge item version row.', 1;

    /* ------------------------------------------------------------
       2b. Inactive-owner proof, both procedures, using owner C's
           genuinely populated, pre-deactivation fixture.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportKnowledgeItemForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58541, 'A deactivated owner''s knowledge item row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58541, 'A deactivated owner''s knowledge item version row was still readable.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proofs for both
          procedures via INSERT ... EXEC.
       ------------------------------------------------------------ */

    -- Knowledge item (3 rows expected per owner)
    DECLARE @ItemCapture TABLE
    (
        knowledge_item_key uniqueidentifier, item_status nvarchar(30), classification nvarchar(20),
        visibility nvarchar(20), current_version_number int, confirmed_version_number int,
        confirmed_at_utc datetime2(7), archived_at_utc datetime2(7),
        created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ItemCapture EXEC dbo.usp_ReadAccountExportKnowledgeItemForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ItemCapture) <> 3
        THROW 58550, 'Owner A''s knowledge item capture does not have exactly three rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ItemCapture
        WHERE knowledge_item_key = @ItemConfirmedKeyA AND item_status = N'confirmed'
          AND classification = N'work' AND current_version_number = 1
          AND confirmed_version_number = 1 AND confirmed_at_utc IS NOT NULL
          AND archived_at_utc IS NULL
    )
        THROW 58551, 'Owner A''s knowledge item capture is missing the confirmed item or lost its confirmation facts.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ItemCapture
        WHERE knowledge_item_key = @ItemMultiKeyA AND item_status = N'unfinished'
          AND classification = N'personal' AND current_version_number = 2
          AND confirmed_version_number IS NULL
    )
        THROW 58551, 'Owner A''s knowledge item capture is missing the multi-version unfinished item.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ItemCapture
        WHERE knowledge_item_key = @ItemArchivedKeyA AND item_status = N'archived'
          AND classification = N'both' AND archived_at_utc IS NOT NULL
          AND confirmed_version_number IS NULL
    )
        THROW 58551, 'Owner A''s knowledge item capture is missing the archived item or its archive facts.', 1;
    IF EXISTS (SELECT 1 FROM @ItemCapture WHERE knowledge_item_key IN (@ItemConfirmedKeyB, @ItemMultiKeyB, @ItemArchivedKeyB))
        THROW 58552, 'Owner A''s knowledge item capture contains one of owner B''s items.', 1;
    IF EXISTS (SELECT 1 FROM @ItemCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58553, 'Owner A''s knowledge item capture has a missing or non-monotonic read window.', 1;

    DELETE @ItemCapture;
    INSERT @ItemCapture EXEC dbo.usp_ReadAccountExportKnowledgeItemForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @ItemCapture) <> 3
        THROW 58550, 'Owner B''s knowledge item capture does not have exactly three rows.', 1;
    IF EXISTS (SELECT 1 FROM @ItemCapture WHERE knowledge_item_key IN (@ItemConfirmedKeyA, @ItemMultiKeyA, @ItemArchivedKeyA))
        THROW 58552, 'Owner B''s knowledge item capture contains one of owner A''s items.', 1;

    -- Knowledge item version (4 rows expected per owner: confirmed x1, multi x2, archived x1)
    DECLARE @VersionCapture TABLE
    (
        knowledge_item_key uniqueidentifier, version_number int, title nvarchar(160),
        approved_wording nvarchar(max), original_member_wording nvarchar(max),
        body_format nvarchar(20), authored_via nvarchar(30), saved_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @VersionCapture EXEC dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @VersionCapture) <> 4
        THROW 58550, 'Owner A''s knowledge item version capture does not have exactly four rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @VersionCapture
        WHERE knowledge_item_key = @ItemConfirmedKeyA AND version_number = 1
          AND title = N'PSX5-A confirmed item title' AND approved_wording = N'PSX5-A confirmed item approved wording'
          AND original_member_wording = N'PSX5-A confirmed item original wording'
          AND body_format = N'plain' AND authored_via = N'typed'
    )
        THROW 58551, 'Owner A''s knowledge item version capture is missing the confirmed item''s version or its content.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @VersionCapture
        WHERE knowledge_item_key = @ItemMultiKeyA AND version_number = 1
          AND title = N'PSX5-A multi item v1 title' AND body_format = N'plain' AND authored_via = N'typed'
    )
        THROW 58551, 'Owner A''s knowledge item version capture is missing the multi item''s first version.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @VersionCapture
        WHERE knowledge_item_key = @ItemMultiKeyA AND version_number = 2
          AND title = N'PSX5-A multi item v2 title' AND body_format = N'rich' AND authored_via = N'spoken'
    )
        THROW 58551, 'Owner A''s knowledge item version capture is missing the multi item''s second version or its non-default body_format/authored_via.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @VersionCapture
        WHERE knowledge_item_key = @ItemArchivedKeyA AND version_number = 1
          AND title = N'PSX5-A archived item title'
    )
        THROW 58551, 'Owner A''s knowledge item version capture is missing the archived item''s version.', 1;
    IF EXISTS (SELECT 1 FROM @VersionCapture WHERE knowledge_item_key IN (@ItemConfirmedKeyB, @ItemMultiKeyB, @ItemArchivedKeyB))
        THROW 58552, 'Owner A''s knowledge item version capture contains one of owner B''s parent keys.', 1;
    IF EXISTS (SELECT 1 FROM @VersionCapture WHERE title LIKE N'PSX5-B%' OR approved_wording LIKE N'PSX5-B%' OR original_member_wording LIKE N'PSX5-B%')
        THROW 58552, 'Owner A''s knowledge item version capture contains owner B''s distinguishing text.', 1;
    IF EXISTS (SELECT 1 FROM @VersionCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58553, 'Owner A''s knowledge item version capture has a missing or non-monotonic read window.', 1;

    DELETE @VersionCapture;
    INSERT @VersionCapture EXEC dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @VersionCapture) <> 4
        THROW 58550, 'Owner B''s knowledge item version capture does not have exactly four rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @VersionCapture WHERE knowledge_item_key = @ItemConfirmedKeyB AND version_number = 1 AND title = N'PSX5-B confirmed item title')
        THROW 58551, 'Owner B''s knowledge item version capture is missing its own confirmed item''s version.', 1;
    IF EXISTS (SELECT 1 FROM @VersionCapture WHERE knowledge_item_key IN (@ItemConfirmedKeyA, @ItemMultiKeyA, @ItemArchivedKeyA))
        THROW 58552, 'Owner B''s knowledge item version capture contains one of owner A''s parent keys.', 1;
    IF EXISTS (SELECT 1 FROM @VersionCapture WHERE title LIKE N'PSX5-A%' OR approved_wording LIKE N'PSX5-A%' OR original_member_wording LIKE N'PSX5-A%')
        THROW 58552, 'Owner B''s knowledge item version capture contains owner A''s distinguishing text.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-005: structural grep across both Workshop reader procedures (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, expected owner predicate, deterministic ORDER BY, read-window columns present, no transaction control/write/dynamic SQL, no deleted_at_utc reference on either table); per-procedure forbidden-column absence and predicate presence verified against each procedure''s own isolated content select-list text, including the owner-predicate-on-both-sides check for the knowledge item version reader (which independently carries its own owner_profile_id, unlike the sibling packages'' version-history tables) and the explicit visibility = ''private'' predicate on both; a forged UserKey and a deactivated owner both yield zero rows (never an error) across both procedures; real two-owner fixture data (three knowledge items -- confirmed/multi-version-unfinished/archived-never-confirmed -- with four versions total per owner) proves both readers return exactly and only the calling owner''s own rows, complete with a non-null monotonic read window, correct parent knowledge_item_key linkage, correct confirmation/archive fact surfacing, and correct non-default body_format/authored_via decoding; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
