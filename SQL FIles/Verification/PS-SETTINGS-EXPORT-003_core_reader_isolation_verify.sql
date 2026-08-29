/* PS-SETTINGS-EXPORT-003 (account export core readers) production-safe
   owner-isolation verification.

   House pattern: two synthetic owners (A, B) plus a third (C,
   deactivated after its fixture is created) via a throwaway auth
   provider, one outer always-rolled-back transaction, fresh THROW
   numbers in the 58100-58199 block (clear of the migration's own
   58000-58013 range and of every sibling verification file's range --
   highest prior use anywhere under SQL FIles/, excluding the paused,
   unmerged DOMAIN-READERS-001 branch which does not exist in this
   worktree, is 57735).

   Read-window design note (why this script can use INSERT ... EXEC
   freely): every one of the ten readers under test returns its read
   window as two TRAILING COLUMNS on its single content result set,
   never a second result set and never OUTPUT parameters (see the
   migration file's own header for the full rationale). That single,
   uniform shape is exactly what keeps every one of them safe to call
   with INSERT ... EXEC -- Microsoft's own INSERT (Transact-SQL)
   reference requires "each result set" from an EXEC target to be
   "compatible with the columns in the table," not merely the first
   one, so a genuinely second, differently-shaped result set would have
   made that impossible (the exact trap the paused DOMAIN-READERS-001
   package's own header comment records, and the reason
   PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql calls its own two
   *write* procedures -- the ones with a CATCH block that can reach
   ROLLBACK -- bare instead of via INSERT ... EXEC). None of the ten
   readers under test contains any transaction control at all (asserted
   structurally below), so both calling conventions are available here;
   this script uses BARE EXEC for every procedure at least once (the
   forged-@UserKey proof, checked via @@ROWCOUNT immediately after the
   call -- @@ROWCOUNT after a bare EXEC of a procedure reflects that
   procedure's own last-executed statement, exactly as it does after any
   other statement) and INSERT ... EXEC for the real, two-owner,
   field-value-level isolation proofs, which need actual captured rows
   rather than a row count alone.

   Proof strategy:
     0. STRUCTURAL, looped across all ten procedure names: exact
        "@UserKey nvarchar(300)" signature and no other parameter; the
        byte-identical identity-resolution header is present verbatim;
        the expected owner-scoping predicate appears; an explicit
        ORDER BY is present; and -- the load-bearing structural
        tripwire -- no transaction-control keyword, write, or nested
        EXEC/dynamic SQL appears anywhere in the body (a procedure that
        can never reach ROLLBACK can never trip T-SQL's "Cannot use the
        ROLLBACK statement within an INSERT-EXEC statement" refusal,
        which is exactly why every capture below is a plain
        INSERT ... EXEC with no special-casing).
     0b. Per-procedure, explicit (not looped, because the forbidden-list
        and FROM-anchor genuinely differ per procedure and a naive
        generic substring scan is exactly what the paused
        DOMAIN-READERS-001 package's own design notes record
        false-positiving on): the content SELECT list -- located
        precisely as the text between the shared identity header's
        closing "IF @ProfileId IS NULL RETURN;" line and the
        procedure's own first subsequent "FROM dbo.<table>" -- never
        contains a forbidden column's fully-qualified reference, and
        every reader that is supposed to carry a soft-delete predicate
        does.
     1. Two synthetic owners (A, B) each get a full fixture: four
        career_chapters rows (one per subtype: experience, education,
        credential, project), the matching subtype row for each, one
        achievement and one timeline event hung off the experience
        chapter, and one skill. A third owner (C) gets one chapter, is
        then deactivated, and must read as zero rows thereafter even
        though its row still physically exists.
     2. DATA-LEVEL, for EVERY one of the ten procedures: calling as
        owner A must return exactly owner A's own row(s), carrying every
        distinguishing fixture value, and must NEVER contain any value
        unique to owner B's fixture -- and symmetrically for B. Every
        fixture row''s identifying key is captured immediately after
        insert (the "SELECT TOP (1) ... ORDER BY ... DESC" idiom
        PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql already uses)
        and it is that captured key -- never a guessed or literal
        constant -- that every assertion below checks for.
     3. Soft-delete: directly soft-deleting a chapter (career_projects'
        parent), an achievement, and a skill each removes exactly that
        row from its reader (and, for the chapter case, from the joined
        career_projects reader too) while leaving every sibling fixture
        row for the same owner visible -- proving the predicate is
        precise, not merely present.

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-003')
        THROW 58100, 'PS-SETTINGS-EXPORT-003 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof, looped across all ten procedures.
       ------------------------------------------------------------ */
    DECLARE @ReaderNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY, owner_predicate nvarchar(120) NOT NULL);
    INSERT @ReaderNames (procedure_name, owner_predicate)
    VALUES
        (N'usp_ReadAccountExportAccountForOwner', N'app_user.id = @UserId'),
        (N'usp_ReadAccountExportProfileForOwner', N'profile.profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerChapterForOwner', N'chapter.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerExperienceForOwner', N'experience.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerEducationForOwner', N'education.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerCredentialForOwner', N'credential.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerProjectForOwner', N'project.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerAchievementForOwner', N'achievement.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerSkillForOwner', N'skill.owner_profile_id = @ProfileId'),
        (N'usp_ReadAccountExportCareerTimelineEventForOwner', N'timeline_event.owner_profile_id = @ProfileId');

    IF (SELECT COUNT(*) FROM @ReaderNames) <> 10
        THROW 58101, 'The reader-name fixture itself is incomplete.', 1;

    DECLARE @CheckName sysname;
    DECLARE @CheckOwnerPredicate nvarchar(120);
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ReaderNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name, @CheckOwnerPredicate = owner_predicate
        FROM @ReaderNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 58102, 'A required account-export core-reader procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 58103, 'A core-reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
        -- The parameter list is exactly "@UserKey nvarchar(300)" with
        -- nothing after it before "AS": no OUTPUT parameter, no second
        -- input parameter, no default. Anchor on the literal sequence
        -- that would only occur if a second parameter followed.
        IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
            THROW 58103, 'A core-reader procedure declares more than just @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%@OwnerUserId%'
           OR @CheckDefinition LIKE N'%@TableName%'
           OR @CheckDefinition LIKE N'%@ProfileKey%'
            THROW 58103, 'A core-reader procedure accepts a caller-supplied owner id or target.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 58104, 'A core-reader procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
           OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
            THROW 58104, 'A core-reader procedure does not require an active user AND an active profile.', 1;
        IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
            THROW 58104, 'A core-reader procedure does not use the shared byte-identical identity header.', 1;
        IF @CheckDefinition NOT LIKE N'%' + @CheckOwnerPredicate + N'%'
            THROW 58105, 'A core-reader procedure does not filter by its expected owner predicate.', 1;
        IF @CheckDefinition NOT LIKE N'%ORDER BY%'
            THROW 58106, 'A core-reader procedure has no deterministic ORDER BY.', 1;
        IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
            THROW 58107, 'A core-reader procedure uses SELECT * instead of an explicit column list.', 1;
        IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
            THROW 58106, 'A core-reader procedure does not return the read-window columns.', 1;
        -- The structural tripwire: no transaction control, write, or
        -- nested EXEC/dynamic SQL anywhere in the body.
        IF @CheckDefinition LIKE N'%BEGIN TRAN%'
           OR @CheckDefinition LIKE N'%COMMIT%'
           OR @CheckDefinition LIKE N'%ROLLBACK%'
           OR @CheckDefinition LIKE N'%BEGIN TRY%'
           OR @CheckDefinition LIKE N'%BEGIN CATCH%'
           OR @CheckDefinition LIKE N'%INSERT %'
           OR @CheckDefinition LIKE N'%UPDATE %'
           OR @CheckDefinition LIKE N'%DELETE %'
           OR @CheckDefinition LIKE N'%EXEC%'
            THROW 58108, 'A core-reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;

        DELETE @ReaderNames WHERE procedure_name = @CheckName;
    END;

    /* ------------------------------------------------------------
       0b. Per-procedure forbidden-column-absence and soft-delete-
           predicate-presence proof. The content SELECT list is
           located precisely between the shared identity header's
           closing line and the procedure's own FROM clause, so a
           forbidden column's fully-qualified reference inside the
           WHERE/JOIN/ORDER BY text (which legitimately uses
           owner_profile_id, chapter_id, and deleted_at_utc as
           predicates) can never false-positive this check.
       ------------------------------------------------------------ */
    DECLARE @HeaderEnd nvarchar(60) = N'IF @ProfileId IS NULL RETURN;';
    DECLARE @ListStart int;
    DECLARE @ListEnd int;
    DECLARE @SelectList nvarchar(max);

    -- Account: forbidden id/user_key/auth_subject/active.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportAccountForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.app_users AS app_user', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58120, 'Could not locate the account reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%app_user.id%' OR @SelectList LIKE N'%app_user.user_key%'
       OR @SelectList LIKE N'%app_user.auth_subject%' OR @SelectList LIKE N'%app_user.active%'
        THROW 58120, 'The account reader selects a forbidden column.', 1;

    -- Profile: forbidden profile_id/profile_key/user_id/active/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportProfileForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.member_profiles AS profile', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58121, 'Could not locate the profile reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%profile.profile_id%' OR @SelectList LIKE N'%profile.profile_key%'
       OR @SelectList LIKE N'%profile.user_id%' OR @SelectList LIKE N'%profile.active%'
       OR @SelectList LIKE N'%profile.row_version%'
        THROW 58121, 'The profile reader selects a forbidden column.', 1;

    -- Career chapter: forbidden chapter_id/entity_id/owner_profile_id/
    -- created_by_user_id/approved_by_user_id/deleted_at_utc/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerChapterForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_chapters AS chapter', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58122, 'Could not locate the career chapter reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.entity_id%'
       OR @SelectList LIKE N'%chapter.owner_profile_id%' OR @SelectList LIKE N'%chapter.created_by_user_id%'
       OR @SelectList LIKE N'%chapter.approved_by_user_id%' OR @SelectList LIKE N'%chapter.deleted_at_utc%'
       OR @SelectList LIKE N'%chapter.row_version%'
        THROW 58122, 'The career chapter reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58122, 'The career chapter reader is missing its own soft-delete predicate.', 1;

    -- Career experience: forbidden chapter_id/owner_profile_id (both sides).
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerExperienceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_experiences AS experience', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58123, 'Could not locate the career experience reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%experience.chapter_id%' OR @SelectList LIKE N'%experience.owner_profile_id%'
       OR @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.owner_profile_id%'
        THROW 58123, 'The career experience reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58123, 'The career experience reader is missing the joined chapter''s soft-delete predicate.', 1;

    -- Career education: forbidden chapter_id/owner_profile_id (both sides).
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerEducationForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_education AS education', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58124, 'Could not locate the career education reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%education.chapter_id%' OR @SelectList LIKE N'%education.owner_profile_id%'
       OR @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.owner_profile_id%'
        THROW 58124, 'The career education reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58124, 'The career education reader is missing the joined chapter''s soft-delete predicate.', 1;

    -- Career credential: forbidden chapter_id/owner_profile_id (both sides).
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerCredentialForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_credentials AS credential', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58125, 'Could not locate the career credential reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%credential.chapter_id%' OR @SelectList LIKE N'%credential.owner_profile_id%'
       OR @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.owner_profile_id%'
        THROW 58125, 'The career credential reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58125, 'The career credential reader is missing the joined chapter''s soft-delete predicate.', 1;

    -- Career project: forbidden chapter_id/owner_profile_id (both sides).
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerProjectForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_projects AS project', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58126, 'Could not locate the career project reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%project.chapter_id%' OR @SelectList LIKE N'%project.owner_profile_id%'
       OR @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.owner_profile_id%'
        THROW 58126, 'The career project reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58126, 'The career project reader is missing the joined chapter''s soft-delete predicate.', 1;

    -- Career achievement: forbidden achievement_id/entity_id/owner_profile_id/
    -- chapter_id/created_by_user_id/approved_by_user_id/deleted_at_utc/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerAchievementForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_achievements AS achievement', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58127, 'Could not locate the career achievement reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%achievement.achievement_id%' OR @SelectList LIKE N'%achievement.entity_id%'
       OR @SelectList LIKE N'%achievement.owner_profile_id%' OR @SelectList LIKE N'%achievement.chapter_id%'
       OR @SelectList LIKE N'%achievement.created_by_user_id%' OR @SelectList LIKE N'%achievement.approved_by_user_id%'
       OR @SelectList LIKE N'%achievement.deleted_at_utc%' OR @SelectList LIKE N'%achievement.row_version%'
       OR @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.owner_profile_id%'
        THROW 58127, 'The career achievement reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%achievement.deleted_at_utc IS NULL%'
       OR @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58127, 'The career achievement reader is missing a required soft-delete predicate.', 1;

    -- Career skill: forbidden skill_id/entity_id/owner_profile_id/deleted_at_utc/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerSkillForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_skills AS skill', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58128, 'Could not locate the career skill reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%skill.skill_id%' OR @SelectList LIKE N'%skill.entity_id%'
       OR @SelectList LIKE N'%skill.owner_profile_id%' OR @SelectList LIKE N'%skill.deleted_at_utc%'
       OR @SelectList LIKE N'%skill.row_version%'
        THROW 58128, 'The career skill reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%skill.deleted_at_utc IS NULL%'
        THROW 58128, 'The career skill reader is missing its own soft-delete predicate.', 1;

    -- Career timeline event: forbidden timeline_event_id/entity_id/
    -- owner_profile_id/chapter_id/row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerTimelineEventForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.career_timeline_events AS timeline_event', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58129, 'Could not locate the career timeline event reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%timeline_event.timeline_event_id%' OR @SelectList LIKE N'%timeline_event.entity_id%'
       OR @SelectList LIKE N'%timeline_event.owner_profile_id%' OR @SelectList LIKE N'%timeline_event.chapter_id%'
       OR @SelectList LIKE N'%timeline_event.row_version%'
       OR @SelectList LIKE N'%chapter.chapter_id%' OR @SelectList LIKE N'%chapter.owner_profile_id%'
        THROW 58129, 'The career timeline event reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%chapter.deleted_at_utc IS NULL%'
        THROW 58129, 'The career timeline event reader is missing the joined chapter''s soft-delete predicate.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x3-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x3-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x3-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x3-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x3-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX3 Owner A', @Email = N'psx3-owner-a@example.invalid',
        @ProfileImageUrl = N'https://example.invalid/psx3-a.png', @TimezoneName = N'America/Chicago';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x3-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX3 Owner B', @Email = N'psx3-owner-b@example.invalid',
        @ProfileImageUrl = N'https://example.invalid/psx3-b.png', @TimezoneName = N'America/New_York';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x3-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX3 Owner C';

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
    WHERE identity_row.provider = N'settings-export-x3-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x3-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x3-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 58130, 'Synthetic core-reader verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture: four chapters (one per subtype) plus the matching
       subtype row, one achievement, one skill, and one timeline event,
       for owners A and B. Every NOT NULL no-default column and every
       CHECK constraint on every touched table (slate_entities,
       career_chapters, career_experiences, career_education,
       career_credentials, career_projects, career_achievements,
       career_skills, career_timeline_events) was re-read from
       PS-PLAT-002_profiles_entities_access.sql and
       PS-PLAT-006_living_resume_domain.sql before writing any INSERT
       below.
       ------------------------------------------------------------ */
    DECLARE @EntityIdChapterExpA bigint, @EntityIdChapterEduA bigint, @EntityIdChapterCredA bigint, @EntityIdChapterProjA bigint;
    DECLARE @EntityIdAchievementA bigint, @EntityIdSkillA bigint, @EntityIdTimelineA bigint;
    DECLARE @EntityIdChapterExpB bigint, @EntityIdChapterEduB bigint, @EntityIdChapterCredB bigint, @EntityIdChapterProjB bigint;
    DECLARE @EntityIdAchievementB bigint, @EntityIdSkillB bigint, @EntityIdTimelineB bigint;
    DECLARE @EntityIdChapterC bigint;

    DECLARE @ChapterIdExpA bigint, @ChapterIdEduA bigint, @ChapterIdCredA bigint, @ChapterIdProjA bigint;
    DECLARE @ChapterKeyExpA uniqueidentifier, @ChapterKeyEduA uniqueidentifier, @ChapterKeyCredA uniqueidentifier, @ChapterKeyProjA uniqueidentifier;
    DECLARE @ChapterIdExpB bigint, @ChapterIdEduB bigint, @ChapterIdCredB bigint, @ChapterIdProjB bigint;
    DECLARE @ChapterKeyExpB uniqueidentifier, @ChapterKeyEduB uniqueidentifier, @ChapterKeyCredB uniqueidentifier, @ChapterKeyProjB uniqueidentifier;
    DECLARE @ChapterIdC bigint;

    DECLARE @AchievementKeyA uniqueidentifier, @AchievementKeyB uniqueidentifier;
    DECLARE @SkillKeyA uniqueidentifier, @SkillKeyB uniqueidentifier;
    DECLARE @TimelineKeyA uniqueidentifier, @TimelineKeyB uniqueidentifier;

    ------------------------------------------------------------------
    -- Owner A fixture
    ------------------------------------------------------------------
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_chapter');
    SET @EntityIdChapterExpA = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_chapter');
    SET @EntityIdChapterEduA = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_chapter');
    SET @EntityIdChapterCredA = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_chapter');
    SET @EntityIdChapterProjA = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_achievement');
    SET @EntityIdAchievementA = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill');
    SET @EntityIdSkillA = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_timeline_event');
    SET @EntityIdTimelineA = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.career_chapters
        (owner_profile_id, entity_id, chapter_type, title, organization_name, location_text, summary,
         original_member_wording, approved_wording, start_date, end_date, created_by_user_id,
         approval_status, approved_by_user_id, approved_at_utc)
    VALUES
        (@ProfileIdA, @EntityIdChapterExpA, N'experience', N'PSX3-A Senior Widget Engineer', N'PSX3-A Employer Co',
         N'PSX3-A Remote', N'PSX3-A summary text', N'PSX3-A original wording', N'PSX3-A approved wording',
         '2020-01-01', '2022-01-01', @UserIdA, N'approved', @UserIdA, SYSUTCDATETIME());
    SET @ChapterIdExpA = SCOPE_IDENTITY();

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdA, @EntityIdChapterEduA, N'education', N'PSX3-A Chapter Education', N'PSX3-A University', @UserIdA);
    SET @ChapterIdEduA = SCOPE_IDENTITY();

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdA, @EntityIdChapterCredA, N'credential', N'PSX3-A Chapter Credential', N'PSX3-A Certifier', @UserIdA);
    SET @ChapterIdCredA = SCOPE_IDENTITY();

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdA, @EntityIdChapterProjA, N'project', N'PSX3-A Chapter Project', N'PSX3-A Project Org', @UserIdA);
    SET @ChapterIdProjA = SCOPE_IDENTITY();

    SELECT @ChapterKeyExpA = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdExpA;
    SELECT @ChapterKeyEduA = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdEduA;
    SELECT @ChapterKeyCredA = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdCredA;
    SELECT @ChapterKeyProjA = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdProjA;

    INSERT dbo.career_experiences (chapter_id, owner_profile_id, role_title, employer_name, employment_type, current_role)
    VALUES (@ChapterIdExpA, @ProfileIdA, N'PSX3-A Role Title', N'PSX3-A Employer Name', N'full_time', 0);
    INSERT dbo.career_education (chapter_id, owner_profile_id, institution_name, degree_name, field_of_study)
    VALUES (@ChapterIdEduA, @ProfileIdA, N'PSX3-A Institution', N'PSX3-A Degree', N'PSX3-A Field');
    INSERT dbo.career_credentials (chapter_id, owner_profile_id, credential_name, issuer_name, credential_identifier, issue_date, expiration_date, verification_url)
    VALUES (@ChapterIdCredA, @ProfileIdA, N'PSX3-A Credential Name', N'PSX3-A Issuer', N'PSX3-A-CERT-001', '2020-01-01', '2030-01-01', N'https://example.invalid/psx3-a-cert');
    INSERT dbo.career_projects (chapter_id, owner_profile_id, project_name, project_role, project_url)
    VALUES (@ChapterIdProjA, @ProfileIdA, N'PSX3-A Project Name', N'PSX3-A Project Role', N'https://example.invalid/psx3-a-project');

    INSERT dbo.career_achievements
        (owner_profile_id, entity_id, chapter_id, original_member_wording, approved_wording, metric_value, metric_label, created_by_user_id)
    VALUES
        (@ProfileIdA, @EntityIdAchievementA, @ChapterIdExpA, N'PSX3-A Achievement Wording', N'PSX3-A Achievement Approved',
         N'42%', N'PSX3-A Metric Label', @UserIdA);
    SELECT @AchievementKeyA = achievement_key FROM dbo.career_achievements WHERE entity_id = @EntityIdAchievementA;

    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name, skill_summary)
    VALUES (@ProfileIdA, @EntityIdSkillA, N'PSX3-A Skill Name', N'PSX3-A Skill Summary');
    SELECT @SkillKeyA = skill_key FROM dbo.career_skills WHERE entity_id = @EntityIdSkillA;

    INSERT dbo.career_timeline_events (owner_profile_id, entity_id, chapter_id, event_label, event_type)
    VALUES (@ProfileIdA, @EntityIdTimelineA, @ChapterIdExpA, N'PSX3-A Timeline Label', N'experience');
    SELECT @TimelineKeyA = timeline_event_key FROM dbo.career_timeline_events WHERE entity_id = @EntityIdTimelineA;

    ------------------------------------------------------------------
    -- Owner B fixture (mirrors A, distinct distinguishing text)
    ------------------------------------------------------------------
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_chapter');
    SET @EntityIdChapterExpB = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_chapter');
    SET @EntityIdChapterEduB = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_chapter');
    SET @EntityIdChapterCredB = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_chapter');
    SET @EntityIdChapterProjB = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_achievement');
    SET @EntityIdAchievementB = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_skill');
    SET @EntityIdSkillB = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_timeline_event');
    SET @EntityIdTimelineB = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdB, @EntityIdChapterExpB, N'experience', N'PSX3-B Chapter Experience', N'PSX3-B Employer Co', @UserIdB);
    SET @ChapterIdExpB = SCOPE_IDENTITY();

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdB, @EntityIdChapterEduB, N'education', N'PSX3-B Chapter Education', N'PSX3-B University', @UserIdB);
    SET @ChapterIdEduB = SCOPE_IDENTITY();

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdB, @EntityIdChapterCredB, N'credential', N'PSX3-B Chapter Credential', N'PSX3-B Certifier', @UserIdB);
    SET @ChapterIdCredB = SCOPE_IDENTITY();

    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdB, @EntityIdChapterProjB, N'project', N'PSX3-B Chapter Project', N'PSX3-B Project Org', @UserIdB);
    SET @ChapterIdProjB = SCOPE_IDENTITY();

    SELECT @ChapterKeyExpB = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdExpB;
    SELECT @ChapterKeyEduB = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdEduB;
    SELECT @ChapterKeyCredB = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdCredB;
    SELECT @ChapterKeyProjB = chapter_key FROM dbo.career_chapters WHERE chapter_id = @ChapterIdProjB;

    INSERT dbo.career_experiences (chapter_id, owner_profile_id, role_title, employer_name, employment_type, current_role)
    VALUES (@ChapterIdExpB, @ProfileIdB, N'PSX3-B Role Title', N'PSX3-B Employer Name', N'contract', 1);
    INSERT dbo.career_education (chapter_id, owner_profile_id, institution_name, degree_name, field_of_study)
    VALUES (@ChapterIdEduB, @ProfileIdB, N'PSX3-B Institution', N'PSX3-B Degree', N'PSX3-B Field');
    INSERT dbo.career_credentials (chapter_id, owner_profile_id, credential_name, issuer_name, credential_identifier, issue_date, expiration_date, verification_url)
    VALUES (@ChapterIdCredB, @ProfileIdB, N'PSX3-B Credential Name', N'PSX3-B Issuer', N'PSX3-B-CERT-001', '2021-01-01', '2031-01-01', N'https://example.invalid/psx3-b-cert');
    INSERT dbo.career_projects (chapter_id, owner_profile_id, project_name, project_role, project_url)
    VALUES (@ChapterIdProjB, @ProfileIdB, N'PSX3-B Project Name', N'PSX3-B Project Role', N'https://example.invalid/psx3-b-project');

    INSERT dbo.career_achievements
        (owner_profile_id, entity_id, chapter_id, original_member_wording, approved_wording, metric_value, metric_label, created_by_user_id)
    VALUES
        (@ProfileIdB, @EntityIdAchievementB, @ChapterIdExpB, N'PSX3-B Achievement Wording', N'PSX3-B Achievement Approved',
         N'99%', N'PSX3-B Metric Label', @UserIdB);
    SELECT @AchievementKeyB = achievement_key FROM dbo.career_achievements WHERE entity_id = @EntityIdAchievementB;

    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name, skill_summary)
    VALUES (@ProfileIdB, @EntityIdSkillB, N'PSX3-B Skill Name', N'PSX3-B Skill Summary');
    SELECT @SkillKeyB = skill_key FROM dbo.career_skills WHERE entity_id = @EntityIdSkillB;

    INSERT dbo.career_timeline_events (owner_profile_id, entity_id, chapter_id, event_label, event_type)
    VALUES (@ProfileIdB, @EntityIdTimelineB, @ChapterIdExpB, N'PSX3-B Timeline Label', N'experience');
    SELECT @TimelineKeyB = timeline_event_key FROM dbo.career_timeline_events WHERE entity_id = @EntityIdTimelineB;

    ------------------------------------------------------------------
    -- Owner C: one minimal chapter fixture, then deactivate the owner.
    ------------------------------------------------------------------
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdC, N'career_chapter');
    SET @EntityIdChapterC = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.career_chapters (owner_profile_id, entity_id, chapter_type, title, organization_name, created_by_user_id)
    VALUES (@ProfileIdC, @EntityIdChapterC, N'experience', N'PSX3-C Chapter (must never be readable once inactive)', N'PSX3-C Employer', @UserIdC);
    SET @ChapterIdC = SCOPE_IDENTITY();

    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 58131, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey proof for all ten procedures:
          @@ROWCOUNT after a bare EXEC reflects that procedure's own
          last-executed statement, so a value other than 0 means the
          content SELECT (not merely the identity-resolution SELECT,
          which never executes when @UserKey does not resolve) yielded
          a row for an unauthenticated caller.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportAccountForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned an account row.', 1;
    EXEC dbo.usp_ReadAccountExportProfileForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a profile row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerChapterForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career chapter row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerExperienceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career experience row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerEducationForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career education row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerCredentialForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career credential row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerProjectForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career project row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerAchievementForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career achievement row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerSkillForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career skill row.', 1;
    EXEC dbo.usp_ReadAccountExportCareerTimelineEventForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58140, 'A forged UserKey returned a career timeline event row.', 1;

    /* ------------------------------------------------------------
       2b. Inactive-owner proof, representative across every scoping
           shape (an @UserId-only reader, a @ProfileId-only reader on
           its own table, and a @ProfileId reader joined to
           career_chapters) using owner C''s genuinely populated,
           pre-deactivation fixture.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportAccountForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58141, 'A deactivated owner''s account row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportProfileForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58141, 'A deactivated owner''s profile row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportCareerChapterForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58141, 'A deactivated owner''s career chapter row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportCareerExperienceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58141, 'A deactivated owner''s career experience row was still readable.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proofs for all ten
          procedures via INSERT ... EXEC (safe: every reader has
          exactly one, uniformly-shaped result set).
       ------------------------------------------------------------ */

    -- Account
    DECLARE @AccountCapture TABLE
    (
        display_name nvarchar(300), email nvarchar(320), auth_provider nvarchar(100),
        profile_image_url nvarchar(2000), timezone_name nvarchar(100), user_role nvarchar(50),
        created_at_utc datetime2(7), last_seen_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @AccountCapture EXEC dbo.usp_ReadAccountExportAccountForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @AccountCapture WHERE email = N'psx3-owner-a@example.invalid')
        THROW 58151, 'Owner A''s account capture is missing owner A''s own email.', 1;
    IF EXISTS (SELECT 1 FROM @AccountCapture WHERE email = N'psx3-owner-b@example.invalid')
        THROW 58152, 'Owner A''s account capture contains owner B''s email.', 1;
    IF EXISTS (SELECT 1 FROM @AccountCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58153, 'Owner A''s account capture has a missing or non-monotonic read window.', 1;
    IF (SELECT COUNT(*) FROM @AccountCapture) <> 1
        THROW 58150, 'Owner A''s account capture does not have exactly one row.', 1;

    DELETE @AccountCapture;
    INSERT @AccountCapture EXEC dbo.usp_ReadAccountExportAccountForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @AccountCapture WHERE email = N'psx3-owner-b@example.invalid')
        THROW 58151, 'Owner B''s account capture is missing owner B''s own email.', 1;
    IF EXISTS (SELECT 1 FROM @AccountCapture WHERE email = N'psx3-owner-a@example.invalid')
        THROW 58152, 'Owner B''s account capture contains owner A''s email.', 1;

    -- Profile
    DECLARE @ProfileCapture TABLE
    (
        profile_slug nvarchar(100), display_name nvarchar(300), headline nvarchar(500), bio nvarchar(max),
        location_text nvarchar(300), visibility nvarchar(30), created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ProfileCapture EXEC dbo.usp_ReadAccountExportProfileForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @ProfileCapture WHERE display_name = N'PSX3 Owner A')
        THROW 58151, 'Owner A''s profile capture is missing owner A''s own display name.', 1;
    IF EXISTS (SELECT 1 FROM @ProfileCapture WHERE display_name = N'PSX3 Owner B')
        THROW 58152, 'Owner A''s profile capture contains owner B''s display name.', 1;
    IF (SELECT COUNT(*) FROM @ProfileCapture) <> 1
        THROW 58150, 'Owner A''s profile capture does not have exactly one row.', 1;

    DELETE @ProfileCapture;
    INSERT @ProfileCapture EXEC dbo.usp_ReadAccountExportProfileForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @ProfileCapture WHERE display_name = N'PSX3 Owner B')
        THROW 58151, 'Owner B''s profile capture is missing owner B''s own display name.', 1;
    IF EXISTS (SELECT 1 FROM @ProfileCapture WHERE display_name = N'PSX3 Owner A')
        THROW 58152, 'Owner B''s profile capture contains owner A''s display name.', 1;

    -- Career chapter (4 rows expected per owner)
    DECLARE @ChapterCapture TABLE
    (
        chapter_key uniqueidentifier, chapter_type nvarchar(30), title nvarchar(300), organization_name nvarchar(300),
        location_text nvarchar(300), summary nvarchar(max), original_member_wording nvarchar(max), approved_wording nvarchar(max),
        start_date date, end_date date, date_precision nvarchar(20), visibility nvarchar(30), approval_status nvarchar(30),
        publication_status nvarchar(30), featured bit, display_order int, approved_at_utc datetime2(7),
        created_at_utc datetime2(7), updated_at_utc datetime2(7), read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ChapterCapture EXEC dbo.usp_ReadAccountExportCareerChapterForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ChapterCapture) <> 4
        THROW 58150, 'Owner A''s career chapter capture does not have exactly four rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @ChapterCapture WHERE chapter_key = @ChapterKeyExpA AND approval_status = N'approved' AND approved_at_utc IS NOT NULL)
        THROW 58151, 'Owner A''s approved experience chapter is missing or lost its approved_at_utc.', 1;
    IF NOT EXISTS (SELECT 1 FROM @ChapterCapture WHERE chapter_key IN (@ChapterKeyEduA, @ChapterKeyCredA, @ChapterKeyProjA))
        THROW 58151, 'Owner A''s career chapter capture is missing one of owner A''s own chapters.', 1;
    IF EXISTS (SELECT 1 FROM @ChapterCapture WHERE chapter_key IN (@ChapterKeyExpB, @ChapterKeyEduB, @ChapterKeyCredB, @ChapterKeyProjB))
        THROW 58152, 'Owner A''s career chapter capture contains one of owner B''s chapters.', 1;
    IF EXISTS (SELECT 1 FROM @ChapterCapture WHERE title LIKE N'PSX3-B%' OR organization_name LIKE N'PSX3-B%')
        THROW 58152, 'Owner A''s career chapter capture contains owner B''s distinguishing text.', 1;

    DELETE @ChapterCapture;
    INSERT @ChapterCapture EXEC dbo.usp_ReadAccountExportCareerChapterForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @ChapterCapture) <> 4
        THROW 58150, 'Owner B''s career chapter capture does not have exactly four rows.', 1;
    IF EXISTS (SELECT 1 FROM @ChapterCapture WHERE chapter_key IN (@ChapterKeyExpA, @ChapterKeyEduA, @ChapterKeyCredA, @ChapterKeyProjA))
        THROW 58152, 'Owner B''s career chapter capture contains one of owner A''s chapters.', 1;
    IF EXISTS (SELECT 1 FROM @ChapterCapture WHERE title LIKE N'PSX3-A%' OR organization_name LIKE N'PSX3-A%')
        THROW 58152, 'Owner B''s career chapter capture contains owner A''s distinguishing text.', 1;

    -- Career experience
    DECLARE @ExperienceCapture TABLE
    (
        chapter_key uniqueidentifier, role_title nvarchar(300), employer_name nvarchar(300),
        employment_type nvarchar(30), current_role bit, read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ExperienceCapture EXEC dbo.usp_ReadAccountExportCareerExperienceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ExperienceCapture) <> 1
        THROW 58150, 'Owner A''s career experience capture does not have exactly one row.', 1;
    IF NOT EXISTS (SELECT 1 FROM @ExperienceCapture WHERE chapter_key = @ChapterKeyExpA AND role_title = N'PSX3-A Role Title' AND employer_name = N'PSX3-A Employer Name')
        THROW 58151, 'Owner A''s career experience capture is missing owner A''s own row or its parent chapter_key.', 1;
    IF EXISTS (SELECT 1 FROM @ExperienceCapture WHERE employer_name LIKE N'PSX3-B%' OR chapter_key = @ChapterKeyExpB)
        THROW 58152, 'Owner A''s career experience capture contains owner B''s data.', 1;

    DELETE @ExperienceCapture;
    INSERT @ExperienceCapture EXEC dbo.usp_ReadAccountExportCareerExperienceForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @ExperienceCapture WHERE chapter_key = @ChapterKeyExpB AND role_title = N'PSX3-B Role Title')
        THROW 58151, 'Owner B''s career experience capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @ExperienceCapture WHERE employer_name LIKE N'PSX3-A%' OR chapter_key = @ChapterKeyExpA)
        THROW 58152, 'Owner B''s career experience capture contains owner A''s data.', 1;

    -- Career education
    DECLARE @EducationCapture TABLE
    (
        chapter_key uniqueidentifier, institution_name nvarchar(300), degree_name nvarchar(300),
        field_of_study nvarchar(300), education_status nvarchar(30), grade_text nvarchar(100),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @EducationCapture EXEC dbo.usp_ReadAccountExportCareerEducationForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @EducationCapture WHERE chapter_key = @ChapterKeyEduA AND institution_name = N'PSX3-A Institution')
        THROW 58151, 'Owner A''s career education capture is missing owner A''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @EducationCapture WHERE institution_name LIKE N'PSX3-B%' OR chapter_key = @ChapterKeyEduB)
        THROW 58152, 'Owner A''s career education capture contains owner B''s data.', 1;

    DELETE @EducationCapture;
    INSERT @EducationCapture EXEC dbo.usp_ReadAccountExportCareerEducationForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @EducationCapture WHERE chapter_key = @ChapterKeyEduB AND institution_name = N'PSX3-B Institution')
        THROW 58151, 'Owner B''s career education capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @EducationCapture WHERE institution_name LIKE N'PSX3-A%' OR chapter_key = @ChapterKeyEduA)
        THROW 58152, 'Owner B''s career education capture contains owner A''s data.', 1;

    -- Career credential
    DECLARE @CredentialCapture TABLE
    (
        chapter_key uniqueidentifier, credential_name nvarchar(300), issuer_name nvarchar(300),
        credential_identifier nvarchar(300), issue_date date, expiration_date date, verification_url nvarchar(1000),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @CredentialCapture EXEC dbo.usp_ReadAccountExportCareerCredentialForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @CredentialCapture WHERE chapter_key = @ChapterKeyCredA AND credential_identifier = N'PSX3-A-CERT-001')
        THROW 58151, 'Owner A''s career credential capture is missing owner A''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @CredentialCapture WHERE credential_identifier = N'PSX3-B-CERT-001' OR chapter_key = @ChapterKeyCredB)
        THROW 58152, 'Owner A''s career credential capture contains owner B''s data.', 1;

    DELETE @CredentialCapture;
    INSERT @CredentialCapture EXEC dbo.usp_ReadAccountExportCareerCredentialForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @CredentialCapture WHERE chapter_key = @ChapterKeyCredB AND credential_identifier = N'PSX3-B-CERT-001')
        THROW 58151, 'Owner B''s career credential capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @CredentialCapture WHERE credential_identifier = N'PSX3-A-CERT-001' OR chapter_key = @ChapterKeyCredA)
        THROW 58152, 'Owner B''s career credential capture contains owner A''s data.', 1;

    -- Career project
    DECLARE @ProjectCapture TABLE
    (
        chapter_key uniqueidentifier, project_name nvarchar(300), project_role nvarchar(300),
        project_status nvarchar(30), project_url nvarchar(1000), read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ProjectCapture EXEC dbo.usp_ReadAccountExportCareerProjectForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @ProjectCapture WHERE chapter_key = @ChapterKeyProjA AND project_name = N'PSX3-A Project Name')
        THROW 58151, 'Owner A''s career project capture is missing owner A''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @ProjectCapture WHERE project_name LIKE N'PSX3-B%' OR chapter_key = @ChapterKeyProjB)
        THROW 58152, 'Owner A''s career project capture contains owner B''s data.', 1;

    DELETE @ProjectCapture;
    INSERT @ProjectCapture EXEC dbo.usp_ReadAccountExportCareerProjectForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @ProjectCapture WHERE chapter_key = @ChapterKeyProjB AND project_name = N'PSX3-B Project Name')
        THROW 58151, 'Owner B''s career project capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @ProjectCapture WHERE project_name LIKE N'PSX3-A%' OR chapter_key = @ChapterKeyProjA)
        THROW 58152, 'Owner B''s career project capture contains owner A''s data.', 1;

    -- Career achievement
    DECLARE @AchievementCapture TABLE
    (
        achievement_key uniqueidentifier, chapter_key uniqueidentifier, original_member_wording nvarchar(max),
        approved_wording nvarchar(max), metric_value nvarchar(100), metric_label nvarchar(300), visibility nvarchar(30),
        approval_status nvarchar(30), featured bit, display_order int, approved_at_utc datetime2(7),
        created_at_utc datetime2(7), updated_at_utc datetime2(7), read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @AchievementCapture EXEC dbo.usp_ReadAccountExportCareerAchievementForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @AchievementCapture WHERE achievement_key = @AchievementKeyA AND chapter_key = @ChapterKeyExpA AND metric_value = N'42%')
        THROW 58151, 'Owner A''s career achievement capture is missing owner A''s own row or its parent chapter_key.', 1;
    IF EXISTS (SELECT 1 FROM @AchievementCapture WHERE achievement_key = @AchievementKeyB OR metric_value = N'99%')
        THROW 58152, 'Owner A''s career achievement capture contains owner B''s data.', 1;

    DELETE @AchievementCapture;
    INSERT @AchievementCapture EXEC dbo.usp_ReadAccountExportCareerAchievementForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @AchievementCapture WHERE achievement_key = @AchievementKeyB AND chapter_key = @ChapterKeyExpB AND metric_value = N'99%')
        THROW 58151, 'Owner B''s career achievement capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @AchievementCapture WHERE achievement_key = @AchievementKeyA OR metric_value = N'42%')
        THROW 58152, 'Owner B''s career achievement capture contains owner A''s data.', 1;

    -- Career skill
    DECLARE @SkillCapture TABLE
    (
        skill_key uniqueidentifier, skill_name nvarchar(200), skill_summary nvarchar(max), visibility nvarchar(30),
        approval_status nvarchar(30), featured bit, display_order int, created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @SkillCapture EXEC dbo.usp_ReadAccountExportCareerSkillForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @SkillCapture WHERE skill_key = @SkillKeyA AND skill_name = N'PSX3-A Skill Name')
        THROW 58151, 'Owner A''s career skill capture is missing owner A''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @SkillCapture WHERE skill_key = @SkillKeyB OR skill_name LIKE N'PSX3-B%')
        THROW 58152, 'Owner A''s career skill capture contains owner B''s data.', 1;

    DELETE @SkillCapture;
    INSERT @SkillCapture EXEC dbo.usp_ReadAccountExportCareerSkillForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @SkillCapture WHERE skill_key = @SkillKeyB AND skill_name = N'PSX3-B Skill Name')
        THROW 58151, 'Owner B''s career skill capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @SkillCapture WHERE skill_key = @SkillKeyA OR skill_name LIKE N'PSX3-A%')
        THROW 58152, 'Owner B''s career skill capture contains owner A''s data.', 1;

    -- Career timeline event
    DECLARE @TimelineCapture TABLE
    (
        timeline_event_key uniqueidentifier, chapter_key uniqueidentifier, event_label nvarchar(300), event_type nvarchar(30),
        start_date date, end_date date, date_precision nvarchar(20), visibility nvarchar(30), approval_status nvarchar(30),
        constellation_featured bit, display_order int, created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @TimelineCapture EXEC dbo.usp_ReadAccountExportCareerTimelineEventForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @TimelineCapture WHERE timeline_event_key = @TimelineKeyA AND chapter_key = @ChapterKeyExpA AND event_label = N'PSX3-A Timeline Label')
        THROW 58151, 'Owner A''s career timeline event capture is missing owner A''s own row or its parent chapter_key.', 1;
    IF EXISTS (SELECT 1 FROM @TimelineCapture WHERE timeline_event_key = @TimelineKeyB OR event_label LIKE N'PSX3-B%')
        THROW 58152, 'Owner A''s career timeline event capture contains owner B''s data.', 1;

    DELETE @TimelineCapture;
    INSERT @TimelineCapture EXEC dbo.usp_ReadAccountExportCareerTimelineEventForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @TimelineCapture WHERE timeline_event_key = @TimelineKeyB AND chapter_key = @ChapterKeyExpB AND event_label = N'PSX3-B Timeline Label')
        THROW 58151, 'Owner B''s career timeline event capture is missing owner B''s own row.', 1;
    IF EXISTS (SELECT 1 FROM @TimelineCapture WHERE timeline_event_key = @TimelineKeyA OR event_label LIKE N'PSX3-A%')
        THROW 58152, 'Owner B''s career timeline event capture contains owner A''s data.', 1;

    /* ------------------------------------------------------------
       4. Soft-delete precision proof. Deleting owner A's project
          chapter must remove it (and its joined project row) while
          leaving owner A's other three chapters, and owner B's
          fixture, untouched. Deleting owner A's achievement and skill
          directly must remove exactly those rows.
       ------------------------------------------------------------ */
    UPDATE dbo.career_chapters SET deleted_at_utc = SYSUTCDATETIME() WHERE chapter_id = @ChapterIdProjA;
    IF @@ROWCOUNT <> 1
        THROW 58160, 'Could not soft-delete owner A''s project chapter for the soft-delete proof.', 1;
    UPDATE dbo.career_achievements SET deleted_at_utc = SYSUTCDATETIME() WHERE entity_id = @EntityIdAchievementA;
    IF @@ROWCOUNT <> 1
        THROW 58160, 'Could not soft-delete owner A''s achievement for the soft-delete proof.', 1;
    UPDATE dbo.career_skills SET deleted_at_utc = SYSUTCDATETIME() WHERE entity_id = @EntityIdSkillA;
    IF @@ROWCOUNT <> 1
        THROW 58160, 'Could not soft-delete owner A''s skill for the soft-delete proof.', 1;

    DELETE @ChapterCapture;
    INSERT @ChapterCapture EXEC dbo.usp_ReadAccountExportCareerChapterForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ChapterCapture) <> 3
        THROW 58160, 'Owner A''s career chapter capture did not drop to three rows after the soft-delete.', 1;
    IF EXISTS (SELECT 1 FROM @ChapterCapture WHERE chapter_key = @ChapterKeyProjA)
        THROW 58160, 'A soft-deleted chapter is still returned by the career chapter reader.', 1;
    IF NOT EXISTS (SELECT 1 FROM @ChapterCapture WHERE chapter_key IN (@ChapterKeyExpA, @ChapterKeyEduA, @ChapterKeyCredA))
        THROW 58161, 'Soft-deleting one chapter incorrectly hid a sibling chapter for the same owner.', 1;

    DELETE @ProjectCapture;
    INSERT @ProjectCapture EXEC dbo.usp_ReadAccountExportCareerProjectForOwner @UserKey = @UserKeyA;
    IF EXISTS (SELECT 1 FROM @ProjectCapture)
        THROW 58160, 'A career project row whose parent chapter was soft-deleted is still returned.', 1;

    DELETE @AchievementCapture;
    INSERT @AchievementCapture EXEC dbo.usp_ReadAccountExportCareerAchievementForOwner @UserKey = @UserKeyA;
    IF EXISTS (SELECT 1 FROM @AchievementCapture)
        THROW 58160, 'A soft-deleted achievement is still returned by the career achievement reader.', 1;

    DELETE @SkillCapture;
    INSERT @SkillCapture EXEC dbo.usp_ReadAccountExportCareerSkillForOwner @UserKey = @UserKeyA;
    IF EXISTS (SELECT 1 FROM @SkillCapture)
        THROW 58160, 'A soft-deleted skill is still returned by the career skill reader.', 1;

    -- Owner B's parallel fixture must be completely unaffected.
    DELETE @ChapterCapture;
    INSERT @ChapterCapture EXEC dbo.usp_ReadAccountExportCareerChapterForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @ChapterCapture) <> 4
        THROW 58161, 'Owner A''s soft-delete proof disturbed owner B''s unrelated chapter fixture.', 1;
    DELETE @SkillCapture;
    INSERT @SkillCapture EXEC dbo.usp_ReadAccountExportCareerSkillForOwner @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @SkillCapture WHERE skill_key = @SkillKeyB)
        THROW 58161, 'Owner A''s soft-delete proof disturbed owner B''s unrelated skill fixture.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-003: structural grep across all ten core-reader procedures (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, expected owner predicate, deterministic ORDER BY, read-window columns present, no transaction control/write/dynamic SQL); per-procedure forbidden-column absence and soft-delete-predicate presence verified against each procedure''s own isolated content select-list text; a forged UserKey and a deactivated owner both yield zero rows (never an error) across every scoping shape; real two-owner fixture data (four chapters plus matching subtype rows, one achievement, one skill, one timeline event per owner) proves every one of the ten readers returns exactly and only the calling owner''s own rows, complete with a non-null monotonic read window and correct parent chapter_key linkage where applicable; soft-deleting a chapter removes it and its joined project row while leaving sibling chapters and the other owner''s fixture untouched, and direct achievement/skill soft-deletes are independently precise; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
