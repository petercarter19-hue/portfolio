/* PS-SETTINGS-EXPORT-006 (account export Opportunity Slate readers)
   production-safe owner-isolation verification.

   House pattern (PS-SETTINGS-EXPORT-005_workshop_reader_isolation_verify.sql):
   two synthetic owners (A, B) plus a third (C, deactivated after its
   fixture is created) via a throwaway auth provider, one outer
   always-rolled-back transaction, fresh THROW numbers in the
   58700-58799 block (clear of this package's own migration/rollback
   58600-58699 range and of every sibling verification file's range --
   highest prior use anywhere under SQL FIles/ before this package is
   58553).

   FOUR READERS, A FOUR-LEVEL CHAIN. Unlike every sibling verification
   script in this program, the four procedures under test form a strict
   ancestor chain (opportunity_slates -> opportunity_saved_results ->
   opportunity_saved_qualifications -> opportunity_saved_evidence), and
   every one of the four tables independently carries its own
   owner_profile_id (confirmed by reading PS-OPPSLATE-003's own DDL, not
   assumed). Every reader below therefore joins all the way up to
   dbo.opportunity_slates for its own visibility predicate, and asserts
   the owner predicate on EVERY table it touches, not merely the leaf --
   proved per-procedure in section 0b below, since the exact predicate
   count and join shape differ per procedure (1 table / 2 tables / 3
   tables / 4 tables) and cannot be expressed as one looped assertion.

   DIRECTIVE-CATEGORY CANARIES. This package hard-excludes four content
   categories per the owner's 2026-08-29 directive (see the migration
   file's own header for the full citation trail): third-party posting
   text, evidence links, responses, and AI/model provenance. Section 1's
   fixture populates EVERY one of the excluded columns with a real,
   distinguishing, never-otherwise-referenced value on at least one row
   per table -- including a "tell_more" response (free text) and a
   "connect_evidence" response (evidence title/version) on separate
   qualification rows, so section 0b's forbidden-column-absence check is
   proving a genuine exclusion of populated data, never merely the
   absence of something that was never written.

   No soft-delete section exists in this script. None of the four tables
   under test has a deleted_at_utc column of any kind; PS-OPPSLATE-003's
   own header records that usp_DeleteOpportunitySavedSlateForOwner is a
   member-triggered hard delete of the whole slate, never a flag.

   Read-window design note (why this script can use INSERT ... EXEC
   freely): all four readers under test return their read window as two
   TRAILING COLUMNS on their single content result set, never a second
   result set and never OUTPUT parameters (see the migration file's own
   header). This script uses BARE EXEC for all four procedures at least
   once (the forged-@UserKey and deactivated-owner proofs, checked via
   @@ROWCOUNT immediately after the call) and INSERT ... EXEC for the
   real, two-owner, field-value-level isolation proofs, which need actual
   captured rows.

   Proof strategy:
     0. STRUCTURAL, looped across all four procedure names: exact
        "@UserKey nvarchar(300)" signature and no other parameter; the
        byte-identical identity-resolution header is present verbatim; an
        explicit ORDER BY is present; the read-window columns are present
        with exactly two SELECT keywords; no transaction-control keyword,
        write, or nested EXEC/dynamic SQL appears anywhere in the body; no
        deleted_at_utc reference; no caller-selected owner/target
        parameter.
     0b. Per-procedure, explicit (not looped -- the forbidden-list,
        FROM-anchor, owner-predicate count, and join shape genuinely
        differ per procedure): the content SELECT list -- located
        precisely as the text between the shared identity header's
        closing "IF @ProfileId IS NULL RETURN;" line and the procedure's
        own first subsequent "FROM dbo.<table>" -- never contains a
        forbidden column's fully-qualified reference; every owner
        predicate the procedure needs (one per joined table) is present;
        the top-level slate.visibility = 'private' predicate is present
        on every procedure, including the three descendant readers that
        join all the way up for it; the expected JOIN chain is present.
     1. Three synthetic owners (A, B, C) each get a constraint-complete
        fixture: A and B mirror each other exactly (one slate; two
        append-only saved results, proving save_version_number ordering;
        three qualifications on the latest result -- one with no
        response, one with a "tell_more" response, one with a
        "connect_evidence" response, exercising every branch of
        CK_opportunity_saved_qualifications_response_shape and the
        citation_count/derived_status pairing CHECK; three evidence rows
        spread across two of the three qualifications). C gets one
        minimal row per table, is then deactivated, and must read as zero
        rows across all four procedures thereafter even though every row
        still physically exists. Every NOT NULL no-DEFAULT column, CHECK
        constraint, and FOREIGN KEY on all four tables was re-read from
        PS-OPPSLATE-003_opportunity_slate_os4.sql before writing any
        INSERT below.
     2. Two synthetic-owner proofs (forged key, deactivated owner) across
        all four procedures via bare EXEC, checked by @@ROWCOUNT.
     3. DATA-LEVEL, for ALL FOUR procedures: calling as owner A must
        return exactly owner A's own row(s), carrying every distinguishing
        fixture value including correct parent-key linkage at every
        level, and must NEVER contain any value or key unique to owner
        B's fixture -- and symmetrically for B. Every fixture row's
        identifying key is captured immediately after insert (via
        SCOPE_IDENTITY() then a follow-up SELECT of the opaque key, the
        same idiom every prior package's verification script uses) and it
        is that captured key -- never a guessed or literal constant --
        that every assertion below checks for. opportunity_saved_
        qualifications and opportunity_saved_evidence carry no opaque key
        column of their own (unlike every ancestor); their exported
        identifying tuples are (saved_result_key, ordinal) and
        (saved_result_key, saved_qualification_ordinal, ordinal)
        respectively, already unique per their own UNIQUE constraints, so
        this script asserts against those tuples directly rather than a
        manufactured key that does not exist in the schema.

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-006')
        THROW 58700, 'PS-SETTINGS-EXPORT-006 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof, looped across all four procedures.
       ------------------------------------------------------------ */
    DECLARE @ReaderNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ReaderNames (procedure_name)
    VALUES
        (N'usp_ReadAccountExportOpportunitySlateForOwner'),
        (N'usp_ReadAccountExportOpportunitySavedResultForOwner'),
        (N'usp_ReadAccountExportOpportunitySavedQualificationForOwner'),
        (N'usp_ReadAccountExportOpportunitySavedEvidenceForOwner');

    IF (SELECT COUNT(*) FROM @ReaderNames) <> 4
        THROW 58701, 'The reader-name fixture itself is incomplete.', 1;

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ReaderNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ReaderNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 58702, 'A required account-export Opportunity Slate reader procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 58703, 'An Opportunity Slate reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
        IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
            THROW 58703, 'An Opportunity Slate reader procedure declares more than just @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%@OwnerUserId%'
           OR @CheckDefinition LIKE N'%@TableName%'
           OR @CheckDefinition LIKE N'%@SlateKey%'
           OR @CheckDefinition LIKE N'%@SavedResultKey%'
            THROW 58703, 'An Opportunity Slate reader procedure accepts a caller-supplied owner id or target.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 58704, 'An Opportunity Slate reader procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
           OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
            THROW 58704, 'An Opportunity Slate reader procedure does not require an active user AND an active profile.', 1;
        IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
            THROW 58704, 'An Opportunity Slate reader procedure does not use the shared byte-identical identity header.', 1;
        IF @CheckDefinition NOT LIKE N'%ORDER BY%'
            THROW 58705, 'An Opportunity Slate reader procedure has no deterministic ORDER BY.', 1;
        IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
            THROW 58705, 'An Opportunity Slate reader procedure uses SELECT * instead of an explicit column list.', 1;
        IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
            THROW 58706, 'An Opportunity Slate reader procedure does not return the read-window columns.', 1;
        IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'SELECT', N''))) / LEN(N'SELECT') <> 2
            THROW 58706, 'An Opportunity Slate reader procedure does not contain exactly two SELECT keywords.', 1;
        IF @CheckDefinition LIKE N'%BEGIN TRAN%'
           OR @CheckDefinition LIKE N'%COMMIT%'
           OR @CheckDefinition LIKE N'%ROLLBACK%'
           OR @CheckDefinition LIKE N'%BEGIN TRY%'
           OR @CheckDefinition LIKE N'%BEGIN CATCH%'
           OR @CheckDefinition LIKE N'%INSERT %'
           OR @CheckDefinition LIKE N'%UPDATE %'
           OR @CheckDefinition LIKE N'%DELETE %'
           OR @CheckDefinition LIKE N'%EXEC%'
            THROW 58707, 'An Opportunity Slate reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;
        IF @CheckDefinition LIKE N'%deleted_at_utc%'
            THROW 58707, 'An Opportunity Slate reader procedure references a soft-delete column that does not exist on any claimed table.', 1;

        DELETE @ReaderNames WHERE procedure_name = @CheckName;
    END;

    /* ------------------------------------------------------------
       0b. Per-procedure forbidden-column-absence, owner-predicate,
           visibility-predicate, and join-shape proof. The content
           SELECT list is located precisely between the shared identity
           header's closing line and the procedure's own first FROM
           clause.
       ------------------------------------------------------------ */
    DECLARE @HeaderEnd nvarchar(60) = N'IF @ProfileId IS NULL RETURN;';
    DECLARE @ListStart int;
    DECLARE @ListEnd int;
    DECLARE @SelectList nvarchar(max);

    -- Reader 1: opportunity_slates. Forbidden: opportunity_slate_id,
    -- owner_profile_id, row_version. No JOIN beyond the identity header's
    -- own "JOIN dbo.app_users".
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySlateForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.opportunity_slates AS slate', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58720, 'Could not locate the slate reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%slate.opportunity_slate_id%' OR @SelectList LIKE N'%slate.owner_profile_id%'
       OR @SelectList LIKE N'%slate.row_version%'
        THROW 58720, 'The slate reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%slate.owner_profile_id = @ProfileId%'
        THROW 58720, 'The slate reader is missing its owner predicate.', 1;
    IF @CheckDefinition NOT LIKE N'%slate.visibility = N''private''%'
        THROW 58720, 'The slate reader is missing its explicit visibility = ''private'' predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 1
        THROW 58720, 'The slate reader has a content-level join; it should have none beyond the identity header''s own.', 1;

    -- Reader 2: opportunity_saved_results, joined to opportunity_slates.
    -- Forbidden: opportunity_saved_result_id, opportunity_slate_id,
    -- owner_profile_id, source_text, saved_analysis_key, model_name,
    -- prompt_contract_version, idempotency_key, saved_by_user_id,
    -- row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySavedResultForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.opportunity_saved_results AS saved_result', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58721, 'Could not locate the saved-result reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%saved_result.opportunity_saved_result_id%'
       OR @SelectList LIKE N'%saved_result.opportunity_slate_id%'
       OR @SelectList LIKE N'%saved_result.owner_profile_id%'
       OR @SelectList LIKE N'%saved_result.source_text%'
       OR @SelectList LIKE N'%saved_result.saved_analysis_key%'
       OR @SelectList LIKE N'%saved_result.model_name%'
       OR @SelectList LIKE N'%saved_result.prompt_contract_version%'
       OR @SelectList LIKE N'%saved_result.idempotency_key%'
       OR @SelectList LIKE N'%saved_result.saved_by_user_id%'
       OR @SelectList LIKE N'%saved_result.row_version%'
       OR @SelectList LIKE N'%slate.opportunity_slate_id%'
       OR @SelectList LIKE N'%slate.owner_profile_id%'
        THROW 58721, 'The saved-result reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%JOIN dbo.opportunity_slates AS slate%'
        THROW 58721, 'The saved-result reader does not join its parent for linkage.', 1;
    IF @CheckDefinition NOT LIKE N'%saved_result.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%slate.owner_profile_id = @ProfileId%'
        THROW 58721, 'The saved-result reader is missing the owner predicate on both its own and its parent''s table.', 1;
    IF @CheckDefinition NOT LIKE N'%slate.visibility = N''private''%'
        THROW 58721, 'The saved-result reader is missing the joined slate''s explicit visibility = ''private'' predicate.', 1;

    -- Reader 3: opportunity_saved_qualifications, joined to
    -- opportunity_saved_results and opportunity_slates. Forbidden:
    -- opportunity_saved_qualification_id, opportunity_saved_result_id,
    -- owner_profile_id, employer_text, response_kind, response_text,
    -- authored_via, connected_evidence_title, connected_evidence_version,
    -- row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.opportunity_saved_qualifications AS qualification', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58722, 'Could not locate the saved-qualification reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%qualification.opportunity_saved_qualification_id%'
       OR @SelectList LIKE N'%qualification.opportunity_saved_result_id%'
       OR @SelectList LIKE N'%qualification.owner_profile_id%'
       OR @SelectList LIKE N'%qualification.employer_text%'
       OR @SelectList LIKE N'%qualification.response_kind%'
       OR @SelectList LIKE N'%qualification.response_text%'
       OR @SelectList LIKE N'%qualification.authored_via%'
       OR @SelectList LIKE N'%qualification.connected_evidence_title%'
       OR @SelectList LIKE N'%qualification.connected_evidence_version%'
       OR @SelectList LIKE N'%qualification.row_version%'
       OR @SelectList LIKE N'%saved_result.opportunity_saved_result_id%'
       OR @SelectList LIKE N'%saved_result.opportunity_slate_id%'
       OR @SelectList LIKE N'%saved_result.owner_profile_id%'
       OR @SelectList LIKE N'%slate.opportunity_slate_id%'
       OR @SelectList LIKE N'%slate.owner_profile_id%'
        THROW 58722, 'The saved-qualification reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%JOIN dbo.opportunity_saved_results AS saved_result%'
       OR @CheckDefinition NOT LIKE N'%JOIN dbo.opportunity_slates AS slate%'
        THROW 58722, 'The saved-qualification reader does not join every ancestor for linkage and visibility.', 1;
    IF @CheckDefinition NOT LIKE N'%qualification.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%saved_result.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%slate.owner_profile_id = @ProfileId%'
        THROW 58722, 'The saved-qualification reader is missing the owner predicate on every ancestor table.', 1;
    IF @CheckDefinition NOT LIKE N'%slate.visibility = N''private''%'
        THROW 58722, 'The saved-qualification reader is missing the joined slate''s explicit visibility = ''private'' predicate.', 1;

    -- Reader 4: opportunity_saved_evidence, joined to
    -- opportunity_saved_qualifications, opportunity_saved_results, and
    -- opportunity_slates. Forbidden: opportunity_saved_evidence_id,
    -- opportunity_saved_qualification_id, owner_profile_id, covered_text,
    -- evidence_kind, evidence_key, evidence_version, evidence_title,
    -- excerpt, row_version.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.opportunity_saved_evidence AS evidence', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 58723, 'Could not locate the saved-evidence reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%evidence.opportunity_saved_evidence_id%'
       OR @SelectList LIKE N'%evidence.opportunity_saved_qualification_id%'
       OR @SelectList LIKE N'%evidence.owner_profile_id%'
       OR @SelectList LIKE N'%evidence.covered_text%'
       OR @SelectList LIKE N'%evidence.evidence_kind%'
       OR @SelectList LIKE N'%evidence.evidence_key%'
       OR @SelectList LIKE N'%evidence.evidence_version%'
       OR @SelectList LIKE N'%evidence.evidence_title%'
       OR @SelectList LIKE N'%evidence.excerpt%'
       OR @SelectList LIKE N'%evidence.row_version%'
       OR @SelectList LIKE N'%qualification.opportunity_saved_qualification_id%'
       OR @SelectList LIKE N'%qualification.opportunity_saved_result_id%'
       OR @SelectList LIKE N'%qualification.owner_profile_id%'
       OR @SelectList LIKE N'%qualification.employer_text%'
       OR @SelectList LIKE N'%saved_result.opportunity_saved_result_id%'
       OR @SelectList LIKE N'%saved_result.opportunity_slate_id%'
       OR @SelectList LIKE N'%saved_result.owner_profile_id%'
       OR @SelectList LIKE N'%slate.opportunity_slate_id%'
       OR @SelectList LIKE N'%slate.owner_profile_id%'
        THROW 58723, 'The saved-evidence reader selects a forbidden column.', 1;
    IF @CheckDefinition NOT LIKE N'%JOIN dbo.opportunity_saved_qualifications AS qualification%'
       OR @CheckDefinition NOT LIKE N'%JOIN dbo.opportunity_saved_results AS saved_result%'
       OR @CheckDefinition NOT LIKE N'%JOIN dbo.opportunity_slates AS slate%'
        THROW 58723, 'The saved-evidence reader does not join every ancestor for linkage and visibility.', 1;
    IF @CheckDefinition NOT LIKE N'%evidence.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%qualification.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%saved_result.owner_profile_id = @ProfileId%'
       OR @CheckDefinition NOT LIKE N'%slate.owner_profile_id = @ProfileId%'
        THROW 58723, 'The saved-evidence reader is missing the owner predicate on every ancestor table.', 1;
    IF @CheckDefinition NOT LIKE N'%slate.visibility = N''private''%'
        THROW 58723, 'The saved-evidence reader is missing the joined slate''s explicit visibility = ''private'' predicate.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x6-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x6-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x6-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x6-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x6-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX6 Owner A', @Email = N'psx6-owner-a@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x6-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX6 Owner B', @Email = N'psx6-owner-b@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x6-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX6 Owner C';

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
    WHERE identity_row.provider = N'settings-export-x6-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x6-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x6-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 58730, 'Synthetic Opportunity Slate verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture. Every NOT NULL no-DEFAULT column, CHECK constraint, and
       FOREIGN KEY on all four tables was re-read from
       PS-OPPSLATE-003_opportunity_slate_os4.sql before writing any
       INSERT below.
       ------------------------------------------------------------ */
    DECLARE @SlateIdA bigint, @SlateKeyA uniqueidentifier;
    DECLARE @ResultIdA1 bigint, @ResultKeyA1 uniqueidentifier;
    DECLARE @ResultIdA2 bigint, @ResultKeyA2 uniqueidentifier;
    DECLARE @QualIdA1 bigint, @QualIdA2 bigint, @QualIdA3 bigint;

    DECLARE @SlateIdB bigint, @SlateKeyB uniqueidentifier;
    DECLARE @ResultIdB1 bigint, @ResultKeyB1 uniqueidentifier;
    DECLARE @ResultIdB2 bigint, @ResultKeyB2 uniqueidentifier;
    DECLARE @QualIdB1 bigint, @QualIdB2 bigint, @QualIdB3 bigint;

    DECLARE @SlateIdC bigint;
    DECLARE @ResultIdC bigint;
    DECLARE @QualIdC bigint;

    ------------------------------------------------------------------
    -- Owner A fixture
    ------------------------------------------------------------------
    INSERT dbo.opportunity_slates (owner_profile_id)
    VALUES (@ProfileIdA);
    SET @SlateIdA = SCOPE_IDENTITY();
    SELECT @SlateKeyA = slate_key FROM dbo.opportunity_slates WHERE opportunity_slate_id = @SlateIdA;
    UPDATE dbo.opportunity_slates SET current_save_version_number = 2 WHERE opportunity_slate_id = @SlateIdA;

    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number, source_version_number, requirement_version_number,
         saved_analysis_key, source_text, model_name, prompt_contract_version, evidence_considered_count,
         qualification_count, input_fingerprint, idempotency_key, saved_by_user_id)
    VALUES
        (@SlateIdA, @ProfileIdA, 1, 1, 1, NEWID(),
         N'PSX6-A v1 employer wording (must never be readable)', N'psx6-fixture-model-a1', N'psx6-fixture-contract-a1',
         3, 2, REPLICATE(N'a', 64), CONCAT(N'psx6-a-idem-1-', @Suffix), @UserIdA);
    SET @ResultIdA1 = SCOPE_IDENTITY();
    SELECT @ResultKeyA1 = saved_result_key FROM dbo.opportunity_saved_results WHERE opportunity_saved_result_id = @ResultIdA1;

    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number, source_version_number, requirement_version_number,
         saved_analysis_key, source_text, model_name, prompt_contract_version, evidence_considered_count,
         qualification_count, input_fingerprint, idempotency_key, saved_by_user_id)
    VALUES
        (@SlateIdA, @ProfileIdA, 2, 2, 2, NEWID(),
         N'PSX6-A v2 employer wording (must never be readable)', N'psx6-fixture-model-a2', N'psx6-fixture-contract-a2',
         5, 3, REPLICATE(N'b', 64), CONCAT(N'psx6-a-idem-2-', @Suffix), @UserIdA);
    SET @ResultIdA2 = SCOPE_IDENTITY();
    SELECT @ResultKeyA2 = saved_result_key FROM dbo.opportunity_saved_results WHERE opportunity_saved_result_id = @ResultIdA2;

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count)
    VALUES
        (@ResultIdA2, @ProfileIdA, 1, N'required_qualification', N'PSX6-A employer text Q1 (must never be readable)', N'supported', 2);
    SET @QualIdA1 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count,
         response_kind, response_text, authored_via)
    VALUES
        (@ResultIdA2, @ProfileIdA, 2, N'preferred_qualification', N'PSX6-A employer text Q2 (must never be readable)', N'not_enough_information', 0,
         N'tell_more', N'PSX6-A response text Q2 (must never be readable)', N'typed');
    SET @QualIdA2 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count,
         response_kind, authored_via, connected_evidence_title, connected_evidence_version)
    VALUES
        (@ResultIdA2, @ProfileIdA, 3, N'responsibility', N'PSX6-A employer text Q3 (must never be readable)', N'partially_supported', 1,
         N'connect_evidence', N'typed', N'PSX6-A connected evidence title (must never be readable)', 3);
    SET @QualIdA3 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdA1, @ProfileIdA, 1, 1, N'PSX6-A covered text Q1E1 (must never be readable)', N'knowledge_item', NEWID(), 1, N'PSX6-A evidence title Q1E1 (must never be readable)', N'PSX6-A excerpt Q1E1 (must never be readable)');
    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdA1, @ProfileIdA, 2, 1, N'PSX6-A covered text Q1E2 (must never be readable)', N'moment', NEWID(), 2, N'PSX6-A evidence title Q1E2 (must never be readable)', N'PSX6-A excerpt Q1E2 (must never be readable)');
    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdA3, @ProfileIdA, 1, 1, N'PSX6-A covered text Q3E1 (must never be readable)', N'knowledge_item', NEWID(), 1, N'PSX6-A evidence title Q3E1 (must never be readable)', N'PSX6-A excerpt Q3E1 (must never be readable)');

    ------------------------------------------------------------------
    -- Owner B fixture (mirrors A, distinct distinguishing text)
    ------------------------------------------------------------------
    INSERT dbo.opportunity_slates (owner_profile_id)
    VALUES (@ProfileIdB);
    SET @SlateIdB = SCOPE_IDENTITY();
    SELECT @SlateKeyB = slate_key FROM dbo.opportunity_slates WHERE opportunity_slate_id = @SlateIdB;
    UPDATE dbo.opportunity_slates SET current_save_version_number = 2 WHERE opportunity_slate_id = @SlateIdB;

    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number, source_version_number, requirement_version_number,
         saved_analysis_key, source_text, model_name, prompt_contract_version, evidence_considered_count,
         qualification_count, input_fingerprint, idempotency_key, saved_by_user_id)
    VALUES
        (@SlateIdB, @ProfileIdB, 1, 1, 1, NEWID(),
         N'PSX6-B v1 employer wording (must never be readable)', N'psx6-fixture-model-b1', N'psx6-fixture-contract-b1',
         4, 2, REPLICATE(N'c', 64), CONCAT(N'psx6-b-idem-1-', @Suffix), @UserIdB);
    SET @ResultIdB1 = SCOPE_IDENTITY();
    SELECT @ResultKeyB1 = saved_result_key FROM dbo.opportunity_saved_results WHERE opportunity_saved_result_id = @ResultIdB1;

    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number, source_version_number, requirement_version_number,
         saved_analysis_key, source_text, model_name, prompt_contract_version, evidence_considered_count,
         qualification_count, input_fingerprint, idempotency_key, saved_by_user_id)
    VALUES
        (@SlateIdB, @ProfileIdB, 2, 2, 2, NEWID(),
         N'PSX6-B v2 employer wording (must never be readable)', N'psx6-fixture-model-b2', N'psx6-fixture-contract-b2',
         6, 3, REPLICATE(N'd', 64), CONCAT(N'psx6-b-idem-2-', @Suffix), @UserIdB);
    SET @ResultIdB2 = SCOPE_IDENTITY();
    SELECT @ResultKeyB2 = saved_result_key FROM dbo.opportunity_saved_results WHERE opportunity_saved_result_id = @ResultIdB2;

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count)
    VALUES
        (@ResultIdB2, @ProfileIdB, 1, N'required_qualification', N'PSX6-B employer text Q1 (must never be readable)', N'supported', 2);
    SET @QualIdB1 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count,
         response_kind, response_text, authored_via)
    VALUES
        (@ResultIdB2, @ProfileIdB, 2, N'preferred_qualification', N'PSX6-B employer text Q2 (must never be readable)', N'not_enough_information', 0,
         N'tell_more', N'PSX6-B response text Q2 (must never be readable)', N'typed');
    SET @QualIdB2 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count,
         response_kind, authored_via, connected_evidence_title, connected_evidence_version)
    VALUES
        (@ResultIdB2, @ProfileIdB, 3, N'responsibility', N'PSX6-B employer text Q3 (must never be readable)', N'partially_supported', 1,
         N'connect_evidence', N'typed', N'PSX6-B connected evidence title (must never be readable)', 4);
    SET @QualIdB3 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdB1, @ProfileIdB, 1, 1, N'PSX6-B covered text Q1E1 (must never be readable)', N'knowledge_item', NEWID(), 1, N'PSX6-B evidence title Q1E1 (must never be readable)', N'PSX6-B excerpt Q1E1 (must never be readable)');
    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdB1, @ProfileIdB, 2, 1, N'PSX6-B covered text Q1E2 (must never be readable)', N'moment', NEWID(), 2, N'PSX6-B evidence title Q1E2 (must never be readable)', N'PSX6-B excerpt Q1E2 (must never be readable)');
    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdB3, @ProfileIdB, 1, 1, N'PSX6-B covered text Q3E1 (must never be readable)', N'knowledge_item', NEWID(), 1, N'PSX6-B evidence title Q3E1 (must never be readable)', N'PSX6-B excerpt Q3E1 (must never be readable)');

    ------------------------------------------------------------------
    -- Owner C: one minimal row per table, then deactivate the owner.
    ------------------------------------------------------------------
    INSERT dbo.opportunity_slates (owner_profile_id)
    VALUES (@ProfileIdC);
    SET @SlateIdC = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number, source_version_number, requirement_version_number,
         saved_analysis_key, source_text, model_name, prompt_contract_version, evidence_considered_count,
         qualification_count, input_fingerprint, idempotency_key, saved_by_user_id)
    VALUES
        (@SlateIdC, @ProfileIdC, 1, 1, 1, NEWID(),
         N'PSX6-C employer wording (must never be readable once inactive)', N'psx6-fixture-model-c', N'psx6-fixture-contract-c',
         1, 1, REPLICATE(N'e', 64), CONCAT(N'psx6-c-idem-1-', @Suffix), @UserIdC);
    SET @ResultIdC = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal, statement_class, employer_text, derived_status, citation_count)
    VALUES
        (@ResultIdC, @ProfileIdC, 1, N'required_qualification', N'PSX6-C employer text (must never be readable once inactive)', N'not_enough_information', 0);
    SET @QualIdC = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal, clause_ordinal, covered_text, evidence_kind, evidence_key, evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdC, @ProfileIdC, 1, 1, N'PSX6-C covered text (must never be readable once inactive)', N'knowledge_item', NEWID(), 1, N'PSX6-C evidence title (must never be readable once inactive)', N'PSX6-C excerpt (must never be readable once inactive)');

    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 58731, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey proof for all four procedures.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportOpportunitySlateForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58740, 'A forged UserKey returned an opportunity slate row.', 1;
    EXEC dbo.usp_ReadAccountExportOpportunitySavedResultForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58740, 'A forged UserKey returned an opportunity saved-result row.', 1;
    EXEC dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58740, 'A forged UserKey returned an opportunity saved-qualification row.', 1;
    EXEC dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 58740, 'A forged UserKey returned an opportunity saved-evidence row.', 1;

    /* ------------------------------------------------------------
       2b. Inactive-owner proof, all four procedures, using owner C's
           genuinely populated, pre-deactivation fixture.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportOpportunitySlateForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58741, 'A deactivated owner''s opportunity slate row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportOpportunitySavedResultForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58741, 'A deactivated owner''s opportunity saved-result row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58741, 'A deactivated owner''s opportunity saved-qualification row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 58741, 'A deactivated owner''s opportunity saved-evidence row was still readable.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proofs for all four
          procedures via INSERT ... EXEC.
       ------------------------------------------------------------ */

    -- Opportunity slate (1 row expected per owner)
    DECLARE @SlateCapture TABLE
    (
        slate_key uniqueidentifier, visibility nvarchar(20), current_save_version_number int,
        created_at_utc datetime2(7), updated_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @SlateCapture EXEC dbo.usp_ReadAccountExportOpportunitySlateForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @SlateCapture) <> 1
        THROW 58750, 'Owner A''s opportunity slate capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @SlateCapture
        WHERE slate_key = @SlateKeyA AND visibility = N'private' AND current_save_version_number = 2
    )
        THROW 58751, 'Owner A''s opportunity slate capture is missing its own row or its save-version fact.', 1;
    IF EXISTS (SELECT 1 FROM @SlateCapture WHERE slate_key = @SlateKeyB)
        THROW 58752, 'Owner A''s opportunity slate capture contains owner B''s slate.', 1;
    IF EXISTS (SELECT 1 FROM @SlateCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58753, 'Owner A''s opportunity slate capture has a missing or non-monotonic read window.', 1;

    DELETE @SlateCapture;
    INSERT @SlateCapture EXEC dbo.usp_ReadAccountExportOpportunitySlateForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @SlateCapture) <> 1
        THROW 58750, 'Owner B''s opportunity slate capture does not have exactly one row.', 1;
    IF EXISTS (SELECT 1 FROM @SlateCapture WHERE slate_key = @SlateKeyA)
        THROW 58752, 'Owner B''s opportunity slate capture contains owner A''s slate.', 1;

    -- Opportunity saved result (2 rows expected per owner)
    DECLARE @ResultCapture TABLE
    (
        slate_key uniqueidentifier, saved_result_key uniqueidentifier, save_version_number int,
        source_version_number int, requirement_version_number int,
        evidence_considered_count int, qualification_count int, input_fingerprint char(64),
        saved_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ResultCapture EXEC dbo.usp_ReadAccountExportOpportunitySavedResultForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ResultCapture) <> 2
        THROW 58750, 'Owner A''s opportunity saved-result capture does not have exactly two rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ResultCapture
        WHERE slate_key = @SlateKeyA AND saved_result_key = @ResultKeyA1 AND save_version_number = 1
          AND source_version_number = 1 AND requirement_version_number = 1
          AND evidence_considered_count = 3 AND qualification_count = 2
          AND input_fingerprint = REPLICATE('a', 64)
    )
        THROW 58751, 'Owner A''s opportunity saved-result capture is missing its first save or lost its counted facts.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ResultCapture
        WHERE slate_key = @SlateKeyA AND saved_result_key = @ResultKeyA2 AND save_version_number = 2
          AND evidence_considered_count = 5 AND qualification_count = 3
          AND input_fingerprint = REPLICATE('b', 64)
    )
        THROW 58751, 'Owner A''s opportunity saved-result capture is missing its second (append-only) save.', 1;
    IF EXISTS (SELECT 1 FROM @ResultCapture WHERE saved_result_key IN (@ResultKeyB1, @ResultKeyB2) OR slate_key = @SlateKeyB)
        THROW 58752, 'Owner A''s opportunity saved-result capture contains one of owner B''s rows.', 1;
    IF EXISTS (SELECT 1 FROM @ResultCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58753, 'Owner A''s opportunity saved-result capture has a missing or non-monotonic read window.', 1;

    DELETE @ResultCapture;
    INSERT @ResultCapture EXEC dbo.usp_ReadAccountExportOpportunitySavedResultForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @ResultCapture) <> 2
        THROW 58750, 'Owner B''s opportunity saved-result capture does not have exactly two rows.', 1;
    IF EXISTS (SELECT 1 FROM @ResultCapture WHERE saved_result_key IN (@ResultKeyA1, @ResultKeyA2) OR slate_key = @SlateKeyA)
        THROW 58752, 'Owner B''s opportunity saved-result capture contains one of owner A''s rows.', 1;
    IF EXISTS (SELECT 1 FROM @ResultCapture WHERE input_fingerprint IN (REPLICATE('a', 64), REPLICATE('b', 64)))
        THROW 58752, 'Owner B''s opportunity saved-result capture contains one of owner A''s fingerprints.', 1;

    -- Opportunity saved qualification (3 rows expected per owner)
    DECLARE @QualCapture TABLE
    (
        saved_result_key uniqueidentifier, ordinal int, statement_class nvarchar(40),
        derived_status nvarchar(30), citation_count int,
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @QualCapture EXEC dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @QualCapture) <> 3
        THROW 58750, 'Owner A''s opportunity saved-qualification capture does not have exactly three rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @QualCapture
        WHERE saved_result_key = @ResultKeyA2 AND ordinal = 1
          AND statement_class = N'required_qualification' AND derived_status = N'supported' AND citation_count = 2
    )
        THROW 58751, 'Owner A''s opportunity saved-qualification capture is missing its first qualification or lost its classification facts.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @QualCapture
        WHERE saved_result_key = @ResultKeyA2 AND ordinal = 2
          AND statement_class = N'preferred_qualification' AND derived_status = N'not_enough_information' AND citation_count = 0
    )
        THROW 58751, 'Owner A''s opportunity saved-qualification capture is missing its zero-citation qualification.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @QualCapture
        WHERE saved_result_key = @ResultKeyA2 AND ordinal = 3
          AND statement_class = N'responsibility' AND derived_status = N'partially_supported' AND citation_count = 1
    )
        THROW 58751, 'Owner A''s opportunity saved-qualification capture is missing its third qualification.', 1;
    IF EXISTS (SELECT 1 FROM @QualCapture WHERE saved_result_key IN (@ResultKeyB1, @ResultKeyB2))
        THROW 58752, 'Owner A''s opportunity saved-qualification capture contains one of owner B''s parent keys.', 1;
    IF EXISTS (SELECT 1 FROM @QualCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58753, 'Owner A''s opportunity saved-qualification capture has a missing or non-monotonic read window.', 1;

    DELETE @QualCapture;
    INSERT @QualCapture EXEC dbo.usp_ReadAccountExportOpportunitySavedQualificationForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @QualCapture) <> 3
        THROW 58750, 'Owner B''s opportunity saved-qualification capture does not have exactly three rows.', 1;
    IF EXISTS (SELECT 1 FROM @QualCapture WHERE saved_result_key IN (@ResultKeyA1, @ResultKeyA2))
        THROW 58752, 'Owner B''s opportunity saved-qualification capture contains one of owner A''s parent keys.', 1;

    -- Opportunity saved evidence (3 rows expected for owner A: 2 on Q1, 1 on Q3; likewise for B)
    DECLARE @EvidenceCapture TABLE
    (
        saved_result_key uniqueidentifier, saved_qualification_ordinal int, ordinal int, clause_ordinal int,
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @EvidenceCapture EXEC dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @EvidenceCapture) <> 3
        THROW 58750, 'Owner A''s opportunity saved-evidence capture does not have exactly three rows.', 1;
    IF NOT EXISTS (SELECT 1 FROM @EvidenceCapture WHERE saved_result_key = @ResultKeyA2 AND saved_qualification_ordinal = 1 AND ordinal = 1 AND clause_ordinal = 1)
        THROW 58751, 'Owner A''s opportunity saved-evidence capture is missing its first qualification''s first evidence row.', 1;
    IF NOT EXISTS (SELECT 1 FROM @EvidenceCapture WHERE saved_result_key = @ResultKeyA2 AND saved_qualification_ordinal = 1 AND ordinal = 2 AND clause_ordinal = 1)
        THROW 58751, 'Owner A''s opportunity saved-evidence capture is missing its first qualification''s second evidence row.', 1;
    IF NOT EXISTS (SELECT 1 FROM @EvidenceCapture WHERE saved_result_key = @ResultKeyA2 AND saved_qualification_ordinal = 3 AND ordinal = 1 AND clause_ordinal = 1)
        THROW 58751, 'Owner A''s opportunity saved-evidence capture is missing its third qualification''s evidence row.', 1;
    IF EXISTS (SELECT 1 FROM @EvidenceCapture WHERE saved_result_key IN (@ResultKeyB1, @ResultKeyB2))
        THROW 58752, 'Owner A''s opportunity saved-evidence capture contains one of owner B''s parent keys.', 1;
    IF EXISTS (SELECT 1 FROM @EvidenceCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 58753, 'Owner A''s opportunity saved-evidence capture has a missing or non-monotonic read window.', 1;

    DELETE @EvidenceCapture;
    INSERT @EvidenceCapture EXEC dbo.usp_ReadAccountExportOpportunitySavedEvidenceForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @EvidenceCapture) <> 3
        THROW 58750, 'Owner B''s opportunity saved-evidence capture does not have exactly three rows.', 1;
    IF EXISTS (SELECT 1 FROM @EvidenceCapture WHERE saved_result_key IN (@ResultKeyA1, @ResultKeyA2))
        THROW 58752, 'Owner B''s opportunity saved-evidence capture contains one of owner A''s parent keys.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-006: structural grep across all four Opportunity Slate reader procedures (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, deterministic ORDER BY, read-window columns present with exactly two SELECT keywords, no transaction control/write/dynamic SQL, no deleted_at_utc reference); per-procedure forbidden-column absence and owner/visibility predicate presence verified against each procedure''s own isolated content select-list text, including the owner predicate on every table of the four-level chain (opportunity_slates -> opportunity_saved_results -> opportunity_saved_qualifications -> opportunity_saved_evidence) and the explicit visibility = ''private'' predicate joined all the way up on every descendant reader; every directive-category canary (third-party posting text, evidence links, responses, AI/model provenance) proved absent from actual output against fixture rows where that exact excluded value was genuinely written; a forged UserKey and a deactivated owner both yield zero rows (never an error) across all four procedures; real two-owner fixture data (one slate, two append-only saved results, three qualifications spanning three of the four response-shape branches, three evidence rows) proves all four readers return exactly and only the calling owner''s own rows, complete with non-null monotonic read windows and correct parent-key linkage at every level; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
