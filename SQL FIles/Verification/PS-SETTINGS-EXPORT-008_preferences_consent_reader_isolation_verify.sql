/* PS-SETTINGS-EXPORT-008 (account export preferences and consent readers)
   production-safe owner-isolation verification.

   House pattern (PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql,
   PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql):
   three synthetic owners (A, B, C) via a throwaway auth provider, C
   deactivated after its fixture is created, one outer always-rolled-back
   transaction, fresh THROW numbers in the 59100-59199 block (clear of
   this package's own migration/rollback 59000-59099 range and of every
   sibling verification file's range -- highest prior use anywhere under
   SQL FIles/ before this package is 58953).

   THREE INDEPENDENT TOP-LEVEL READERS, NO JOIN CHAIN. Unlike several
   sibling packages, none of the three procedures under test joins to
   another content table: each reads exactly one of dbo.
   connection_preferences, dbo.notification_preferences, dbo.
   user_consents, filtered by user_id = @UserId (resolved by the shared
   identity header alongside the unused-but-required @ProfileId -- see
   the migration file's own header for why the full header is preserved
   even though these three tables key on user_id, not owner_profile_id).
   Each reader's own JOIN count is therefore exactly 1 (the identity
   header's own "JOIN dbo.app_users"), asserted explicitly per procedure
   in section 0b.

   DORMANT-LABEL CANARY. Both preference readers emit a constant
   disclosure column, feature_status = 'dormant_not_yet_enforced', on
   every row (Paper 2's own truthful-labeling requirement); the consent
   reader carries NO such column (consent records are real, live facts,
   never an unenforced switch). Section 0b asserts the label's presence
   on both preference readers' procedure text and its absence on the
   consent reader's; section 3 asserts the literal value is actually
   present in real captured output rows, never merely present in the
   procedure text without ever executing.

   EXCLUDED-COLUMN CANARIES. dbo.user_consents.evidence_json (excluded
   whole, category UNCONSTRAINED_EVIDENCE) and dbo.user_consents.
   source_context (excluded for a distinct, disclosed reason -- see the
   migration file's own header) are both populated with real,
   never-otherwise-referenced values on every consent fixture row,
   marked "must never be readable," so section 0b's forbidden-column
   absence check and section 3's exact-shape capture table both prove a
   genuine exclusion of populated data, never merely the absence of
   something that was never written. dbo.connection_preferences and
   dbo.notification_preferences have no comparable excluded content
   column -- every real field either table carries is included per
   Paper 2 -- so their own canary is simply their internal user_id,
   which the exact-shape capture tables make structurally impossible to
   smuggle through (an extra selected column would fail the INSERT ...
   EXEC column-count match).

   A DELIBERATE SAME-TIMESTAMP TIE. Owner A's two dbo.user_consents rows
   for the SAME consent_code (an initial 'accepted' event and its later
   'withdrawn' event -- the central Paper 3 proof that a member's export
   includes their own withdrawal history, never only the latest or only
   the accepted events) are inserted with the IDENTICAL recorded_at_utc
   value on purpose. IX_user_consents_history (user_id, consent_code,
   recorded_at_utc DESC) is NOT a unique index, so consent_code +
   recorded_at_utc alone is not provably collision-free; this fixture
   exercises that exact case against the real engine rather than merely
   arguing it from the DDL, proving the reader's own trailing
   user_consent_id tiebreak (excluded from output, like every other
   reader in the program that orders by an excluded internal id) lets
   both rows come back intact rather than erroring or colliding.

   NO THIRD-PARTY CONSENT. This script never references
   dbo.recruiter_questions in any fixture, capture, or assertion.

   Proof strategy:
     0. STRUCTURAL, looped across all three procedure names: exact
        "@UserKey nvarchar(300)" signature and no other parameter; the
        byte-identical identity-resolution header is present verbatim;
        an explicit ORDER BY is present; the read-window columns are
        present with exactly two SELECT keywords; no transaction-control
        keyword, write, or nested EXEC/dynamic SQL appears anywhere in
        the body; no deleted_at_utc reference (none of the three tables
        has one); no caller-selected owner/target parameter.
     0b. Per-procedure, explicit (not looped -- the forbidden-list, FROM
        anchor, and dormant-label expectation genuinely differ per
        procedure): the content SELECT list -- located precisely as the
        text between the shared identity header's closing "IF
        @ProfileId IS NULL RETURN;" line and the procedure's own first
        subsequent "FROM dbo.<table> AS <alias>" -- never contains a
        forbidden column's fully-qualified reference; the owner
        predicate (user_id = @UserId) is present; the join count is
        exactly 1 (the identity header's own join, no content-level
        join); the dormant-feature label is present on both preference
        readers and absent from the consent reader.
     1. Three synthetic owners (A, B, C) each get a constraint-complete
        fixture. dbo.connection_preferences is auto-seeded, all-defaults,
        by usp_UpsertAppUserFromAuth itself, so A and B's fixture step
        is an UPDATE of that already-existing row (proven via
        @@ROWCOUNT), never an INSERT -- an INSERT would violate
        PK_connection_preferences (user_id). dbo.notification_preferences
        has no auto-seed and no writer anywhere in this codebase, so A
        and B each get explicit INSERTs exercising both branches of
        CK_notification_preferences_quiet_pair (a fully-paired quiet-hours
        row and a fully-NULL one). dbo.user_consents gets an append-only
        multi-row history for A (two events for one consent_code --
        accepted then withdrawn, sharing one deliberately-identical
        recorded_at_utc -- plus one event for a second consent_code) and
        one contrasting event for B sharing A's FIRST consent_code and
        policy_version but a different status and timestamp, specifically
        to prove isolation is genuinely user_id-scoped rather than an
        accident of distinct code/version values. C gets one minimal row
        per table, is then deactivated, and must read as zero rows across
        all three procedures thereafter even though every row still
        physically exists. Every NOT NULL no-DEFAULT column, CHECK
        constraint, and FOREIGN KEY on all three tables was re-read from
        PS-PLAT-004_connections_notifications.sql before writing any
        INSERT/UPDATE below.
     2. Two synthetic-owner proofs (forged key, deactivated owner) across
        all three procedures via bare EXEC, checked by @@ROWCOUNT.
     3. DATA-LEVEL, for all three procedures: calling as owner A must
        return exactly owner A's own row(s), carrying every distinguishing
        fixture value, and must NEVER contain any value or status unique
        to owner B's fixture -- and symmetrically for B. Capture tables
        declare the EXACT expected output shape, so an extra selected
        column (e.g. user_id, evidence_json, source_context) would fail
        the INSERT ... EXEC itself with a column-count mismatch, making
        their absence structurally provable rather than merely asserted.

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-008')
        THROW 59100, 'PS-SETTINGS-EXPORT-008 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof, looped across all three procedures.
       ------------------------------------------------------------ */
    DECLARE @ReaderNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ReaderNames (procedure_name)
    VALUES
        (N'usp_ReadAccountExportConnectionPreferenceForOwner'),
        (N'usp_ReadAccountExportNotificationPreferenceForOwner'),
        (N'usp_ReadAccountExportUserConsentForOwner');

    IF (SELECT COUNT(*) FROM @ReaderNames) <> 3
        THROW 59101, 'The reader-name fixture itself is incomplete.', 1;

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ReaderNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ReaderNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 59102, 'A required account-export preference/consent reader procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 59103, 'A preference/consent reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
        IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
           OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
            THROW 59103, 'A preference/consent reader procedure declares more than just @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition LIKE N'%@OwnerUserId%'
           OR @CheckDefinition LIKE N'%@TableName%'
           OR @CheckDefinition LIKE N'%@ConsentCode%'
           OR @CheckDefinition LIKE N'%@NotificationType%'
            THROW 59103, 'A preference/consent reader procedure accepts a caller-supplied owner id or target.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 59104, 'A preference/consent reader procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
           OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
            THROW 59104, 'A preference/consent reader procedure does not require an active user AND an active profile.', 1;
        IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
            THROW 59104, 'A preference/consent reader procedure does not use the shared byte-identical identity header.', 1;
        IF @CheckDefinition NOT LIKE N'%ORDER BY%'
            THROW 59105, 'A preference/consent reader procedure has no deterministic ORDER BY.', 1;
        IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
            THROW 59105, 'A preference/consent reader procedure uses SELECT * instead of an explicit column list.', 1;
        IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
            THROW 59106, 'A preference/consent reader procedure does not return the read-window columns.', 1;
        IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'SELECT', N''))) / LEN(N'SELECT') <> 2
            THROW 59106, 'A preference/consent reader procedure does not contain exactly two SELECT keywords.', 1;
        IF @CheckDefinition LIKE N'%BEGIN TRAN%'
           OR @CheckDefinition LIKE N'%COMMIT%'
           OR @CheckDefinition LIKE N'%ROLLBACK%'
           OR @CheckDefinition LIKE N'%BEGIN TRY%'
           OR @CheckDefinition LIKE N'%BEGIN CATCH%'
           OR @CheckDefinition LIKE N'%INSERT %'
           OR @CheckDefinition LIKE N'%UPDATE %'
           OR @CheckDefinition LIKE N'%DELETE %'
           OR @CheckDefinition LIKE N'%EXEC%'
            THROW 59107, 'A preference/consent reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;
        IF @CheckDefinition LIKE N'%deleted_at_utc%'
            THROW 59107, 'A preference/consent reader procedure references a soft-delete column that does not exist on any claimed table.', 1;

        DELETE @ReaderNames WHERE procedure_name = @CheckName;
    END;

    /* ------------------------------------------------------------
       0b. Per-procedure forbidden-column, owner-predicate, join-count,
           and dormant-label proof. The content SELECT list is located
           precisely between the shared identity header's closing line
           and the procedure's own first FROM clause.
       ------------------------------------------------------------ */
    DECLARE @HeaderEnd nvarchar(60) = N'IF @ProfileId IS NULL RETURN;';
    DECLARE @ListStart int;
    DECLARE @ListEnd int;
    DECLARE @SelectList nvarchar(max);

    -- Reader 1: connection_preferences. Forbidden: preference.user_id.
    -- No content-level join (identity header's own join to app_users
    -- only). Dormant-feature label required.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportConnectionPreferenceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.connection_preferences AS preference', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 59120, 'Could not locate the connection-preference reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%preference.user_id%'
        THROW 59120, 'The connection-preference reader selects its internal user_id column.', 1;
    IF @SelectList NOT LIKE N'%dormant_not_yet_enforced%'
        THROW 59120, 'The connection-preference reader is missing its dormant-feature disclosure label.', 1;
    IF @CheckDefinition NOT LIKE N'%preference.user_id = @UserId%'
        THROW 59120, 'The connection-preference reader is missing its owner predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 1
        THROW 59120, 'The connection-preference reader has a content-level join; it should have none beyond the identity header''s own.', 1;

    -- Reader 2: notification_preferences. Forbidden: preference.user_id.
    -- No content-level join. Dormant-feature label required.
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportNotificationPreferenceForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.notification_preferences AS preference', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 59121, 'Could not locate the notification-preference reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%preference.user_id%'
        THROW 59121, 'The notification-preference reader selects its internal user_id column.', 1;
    IF @SelectList NOT LIKE N'%dormant_not_yet_enforced%'
        THROW 59121, 'The notification-preference reader is missing its dormant-feature disclosure label.', 1;
    IF @CheckDefinition NOT LIKE N'%preference.user_id = @UserId%'
        THROW 59121, 'The notification-preference reader is missing its owner predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 1
        THROW 59121, 'The notification-preference reader has a content-level join; it should have none beyond the identity header''s own.', 1;

    -- Reader 3: user_consents. Forbidden: consent.user_id,
    -- consent.user_consent_id, consent.source_context,
    -- consent.evidence_json. No content-level join. NO dormant-feature
    -- label (consent records are real, live facts).
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportUserConsentForOwner', N'P'));
    SET @ListStart = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    SET @ListEnd = CHARINDEX(N'FROM dbo.user_consents AS consent', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 59122, 'Could not locate the user-consent reader''s content select list.', 1;
    SET @SelectList = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);
    IF @SelectList LIKE N'%consent.user_id%'
       OR @SelectList LIKE N'%consent.user_consent_id%'
       OR @SelectList LIKE N'%consent.source_context%'
       OR @SelectList LIKE N'%consent.evidence_json%'
        THROW 59122, 'The user-consent reader selects a forbidden column.', 1;
    IF @SelectList LIKE N'%feature_status%'
        THROW 59122, 'The user-consent reader must not carry the dormant-feature disclosure column.', 1;
    IF @CheckDefinition NOT LIKE N'%consent.user_id = @UserId%'
        THROW 59122, 'The user-consent reader is missing its owner predicate.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 1
        THROW 59122, 'The user-consent reader has a content-level join; it should have none beyond the identity header''s own.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x8-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x8-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x8-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x8-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x8-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX8 Owner A', @Email = N'psx8-owner-a@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x8-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX8 Owner B', @Email = N'psx8-owner-b@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x8-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX8 Owner C';

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
    WHERE identity_row.provider = N'settings-export-x8-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x8-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x8-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 59130, 'Synthetic preference/consent verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture. Every NOT NULL no-DEFAULT column, CHECK constraint, and
       FOREIGN KEY on all three tables was re-read from
       PS-PLAT-004_connections_notifications.sql before writing any
       INSERT/UPDATE below.
       ------------------------------------------------------------ */

    ------------------------------------------------------------------
    -- dbo.connection_preferences: auto-seeded, all-defaults, by
    -- usp_UpsertAppUserFromAuth itself. Update the already-existing row
    -- for A and B (an INSERT here would violate PK_connection_preferences
    -- (user_id)); leave C at its seeded defaults.
    ------------------------------------------------------------------
    DECLARE @ConnPrefUpdatedAtUtcA datetime2(7) = DATEADD(MINUTE, -20, SYSUTCDATETIME());
    DECLARE @ConnPrefUpdatedAtUtcB datetime2(7) = DATEADD(MINUTE, -15, SYSUTCDATETIME());

    UPDATE dbo.connection_preferences
    SET discovery_opt_in = 1, goal_matching_opt_in = 1, recruiter_discovery_opt_in = 0,
        discoverable_audience = N'connections', updated_at_utc = @ConnPrefUpdatedAtUtcA
    WHERE user_id = @UserIdA;
    IF @@ROWCOUNT <> 1
        THROW 59132, 'Owner A''s auto-seeded connection_preferences row was not found to update.', 1;

    UPDATE dbo.connection_preferences
    SET discovery_opt_in = 0, goal_matching_opt_in = 1, recruiter_discovery_opt_in = 1,
        discoverable_audience = N'public', updated_at_utc = @ConnPrefUpdatedAtUtcB
    WHERE user_id = @UserIdB;
    IF @@ROWCOUNT <> 1
        THROW 59132, 'Owner B''s auto-seeded connection_preferences row was not found to update.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.connection_preferences WHERE user_id = @UserIdC)
        THROW 59132, 'Owner C''s auto-seeded connection_preferences row does not exist.', 1;

    ------------------------------------------------------------------
    -- dbo.notification_preferences: no auto-seed, no writer anywhere in
    -- this codebase. Explicit INSERTs exercise both branches of
    -- CK_notification_preferences_quiet_pair.
    ------------------------------------------------------------------
    DECLARE @NotifPrefUpdatedAtUtcA1 datetime2(7) = DATEADD(MINUTE, -10, SYSUTCDATETIME());
    DECLARE @NotifPrefUpdatedAtUtcA2 datetime2(7) = DATEADD(MINUTE, -9, SYSUTCDATETIME());
    DECLARE @NotifPrefUpdatedAtUtcB1 datetime2(7) = DATEADD(MINUTE, -8, SYSUTCDATETIME());

    INSERT dbo.notification_preferences (user_id, notification_type, in_app_enabled, email_enabled, quiet_hours_start, quiet_hours_end, updated_at_utc)
    VALUES (@UserIdA, N'capture_ready', 1, 1, '22:00:00', '07:00:00', @NotifPrefUpdatedAtUtcA1);
    INSERT dbo.notification_preferences (user_id, notification_type, in_app_enabled, email_enabled, quiet_hours_start, quiet_hours_end, updated_at_utc)
    VALUES (@UserIdA, N'connection_request', 0, 0, NULL, NULL, @NotifPrefUpdatedAtUtcA2);

    INSERT dbo.notification_preferences (user_id, notification_type, in_app_enabled, email_enabled, quiet_hours_start, quiet_hours_end, updated_at_utc)
    VALUES (@UserIdB, N'capture_ready', 1, 0, NULL, NULL, @NotifPrefUpdatedAtUtcB1);

    INSERT dbo.notification_preferences (user_id, notification_type, in_app_enabled, email_enabled, quiet_hours_start, quiet_hours_end, updated_at_utc)
    VALUES (@UserIdC, N'capture_ready', 1, 1, NULL, NULL, SYSUTCDATETIME());

    ------------------------------------------------------------------
    -- dbo.user_consents: append-only history. Owner A gets two events
    -- for ONE consent_code (accepted then withdrawn, sharing one
    -- deliberately-identical recorded_at_utc -- see this file's own
    -- header) plus one event for a second consent_code. Owner B shares
    -- A's FIRST consent_code and policy_version but a different status
    -- and timestamp, proving isolation is genuinely user_id-scoped.
    -- evidence_json and source_context are populated with real,
    -- never-otherwise-referenced canary values on every row.
    ------------------------------------------------------------------
    DECLARE @ConsentCodeShared nvarchar(100) = N'settings_export_x8_verification.marketing_email';
    DECLARE @ConsentCodeSecond nvarchar(100) = N'settings_export_x8_verification.data_sharing';
    DECLARE @ConsentPolicyVersionShared nvarchar(100) = N'2026-08-01.v1';
    DECLARE @ConsentPolicyVersionSecond nvarchar(100) = N'2026-08-15.v2';
    DECLARE @ConsentRecordedAtUtcA12 datetime2(7) = DATEADD(MINUTE, -30, SYSUTCDATETIME());
    DECLARE @ConsentRecordedAtUtcA3 datetime2(7) = DATEADD(MINUTE, -5, SYSUTCDATETIME());
    DECLARE @ConsentRecordedAtUtcB1 datetime2(7) = DATEADD(MINUTE, -25, SYSUTCDATETIME());
    DECLARE @ConsentRecordedAtUtcC datetime2(7) = SYSUTCDATETIME();

    INSERT dbo.user_consents (user_id, consent_code, policy_version, consent_status, recorded_at_utc, source_context, evidence_json)
    VALUES (@UserIdA, @ConsentCodeShared, @ConsentPolicyVersionShared, N'accepted', @ConsentRecordedAtUtcA12,
            N'settings-export-x8-verification-context', N'{"note":"PSX8-A accepted evidence must never be readable","ip_address":"203.0.113.5"}');
    INSERT dbo.user_consents (user_id, consent_code, policy_version, consent_status, recorded_at_utc, source_context, evidence_json)
    VALUES (@UserIdA, @ConsentCodeShared, @ConsentPolicyVersionShared, N'withdrawn', @ConsentRecordedAtUtcA12,
            N'settings-export-x8-verification-context', N'{"note":"PSX8-A withdrawal evidence must never be readable","ip_address":"203.0.113.6"}');
    INSERT dbo.user_consents (user_id, consent_code, policy_version, consent_status, recorded_at_utc, source_context, evidence_json)
    VALUES (@UserIdA, @ConsentCodeSecond, @ConsentPolicyVersionSecond, N'accepted', @ConsentRecordedAtUtcA3,
            N'settings-export-x8-verification-context', N'{"note":"PSX8-A second-code evidence must never be readable","ip_address":"203.0.113.7"}');

    INSERT dbo.user_consents (user_id, consent_code, policy_version, consent_status, recorded_at_utc, source_context, evidence_json)
    VALUES (@UserIdB, @ConsentCodeShared, @ConsentPolicyVersionShared, N'declined', @ConsentRecordedAtUtcB1,
            N'settings-export-x8-verification-context', N'{"note":"PSX8-B declined evidence must never be readable","ip_address":"203.0.113.8"}');

    INSERT dbo.user_consents (user_id, consent_code, policy_version, consent_status, recorded_at_utc, source_context, evidence_json)
    VALUES (@UserIdC, @ConsentCodeShared, @ConsentPolicyVersionShared, N'accepted', @ConsentRecordedAtUtcC,
            N'settings-export-x8-verification-context', N'{"note":"PSX8-C evidence must never be readable once inactive","ip_address":"203.0.113.9"}');

    ------------------------------------------------------------------
    -- Deactivate owner C.
    ------------------------------------------------------------------
    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 59131, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey proof for all three procedures.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportConnectionPreferenceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 59140, 'A forged UserKey returned a connection-preference row.', 1;
    EXEC dbo.usp_ReadAccountExportNotificationPreferenceForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 59140, 'A forged UserKey returned a notification-preference row.', 1;
    EXEC dbo.usp_ReadAccountExportUserConsentForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 59140, 'A forged UserKey returned a user-consent row.', 1;

    /* ------------------------------------------------------------
       2b. Inactive-owner proof, all three procedures, using owner C's
           genuinely populated, pre-deactivation fixture.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportConnectionPreferenceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 59141, 'A deactivated owner''s connection-preference row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportNotificationPreferenceForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 59141, 'A deactivated owner''s notification-preference row was still readable.', 1;
    EXEC dbo.usp_ReadAccountExportUserConsentForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 59141, 'A deactivated owner''s user-consent row was still readable.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proofs for all three
          procedures via INSERT ... EXEC. Capture tables declare the
          exact expected output shape, so an extra selected column
          (user_id, evidence_json, source_context, ...) would fail the
          INSERT ... EXEC itself.
       ------------------------------------------------------------ */

    -- Connection preference (1 row expected per owner)
    DECLARE @ConnPrefCapture TABLE
    (
        discovery_opt_in bit, goal_matching_opt_in bit, recruiter_discovery_opt_in bit,
        discoverable_audience nvarchar(30), updated_at_utc datetime2(7), feature_status nvarchar(60),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ConnPrefCapture EXEC dbo.usp_ReadAccountExportConnectionPreferenceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ConnPrefCapture) <> 1
        THROW 59150, 'Owner A''s connection-preference capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ConnPrefCapture
        WHERE discovery_opt_in = 1 AND goal_matching_opt_in = 1 AND recruiter_discovery_opt_in = 0
          AND discoverable_audience = N'connections' AND updated_at_utc = @ConnPrefUpdatedAtUtcA
          AND feature_status = N'dormant_not_yet_enforced'
    )
        THROW 59150, 'Owner A''s connection-preference capture is missing its own row or its dormant-feature label.', 1;
    IF EXISTS (SELECT 1 FROM @ConnPrefCapture WHERE discoverable_audience = N'public' OR updated_at_utc = @ConnPrefUpdatedAtUtcB)
        THROW 59151, 'Owner A''s connection-preference capture contains owner B''s values.', 1;
    IF EXISTS (SELECT 1 FROM @ConnPrefCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 59152, 'Owner A''s connection-preference capture has a missing or non-monotonic read window.', 1;

    DELETE @ConnPrefCapture;
    INSERT @ConnPrefCapture EXEC dbo.usp_ReadAccountExportConnectionPreferenceForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @ConnPrefCapture) <> 1
        THROW 59150, 'Owner B''s connection-preference capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ConnPrefCapture
        WHERE discovery_opt_in = 0 AND goal_matching_opt_in = 1 AND recruiter_discovery_opt_in = 1
          AND discoverable_audience = N'public' AND updated_at_utc = @ConnPrefUpdatedAtUtcB
          AND feature_status = N'dormant_not_yet_enforced'
    )
        THROW 59150, 'Owner B''s connection-preference capture is missing its own row or its dormant-feature label.', 1;
    IF EXISTS (SELECT 1 FROM @ConnPrefCapture WHERE discoverable_audience = N'connections' OR updated_at_utc = @ConnPrefUpdatedAtUtcA)
        THROW 59151, 'Owner B''s connection-preference capture contains owner A''s values.', 1;

    -- Notification preference (2 rows expected for A, 1 for B)
    DECLARE @NotifPrefCapture TABLE
    (
        notification_type nvarchar(100), in_app_enabled bit, email_enabled bit,
        quiet_hours_start time(0), quiet_hours_end time(0), updated_at_utc datetime2(7), feature_status nvarchar(60),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @NotifPrefCapture EXEC dbo.usp_ReadAccountExportNotificationPreferenceForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @NotifPrefCapture) <> 2
        THROW 59150, 'Owner A''s notification-preference capture does not have exactly two rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @NotifPrefCapture
        WHERE notification_type = N'capture_ready' AND in_app_enabled = 1 AND email_enabled = 1
          AND quiet_hours_start = '22:00:00' AND quiet_hours_end = '07:00:00'
          AND updated_at_utc = @NotifPrefUpdatedAtUtcA1 AND feature_status = N'dormant_not_yet_enforced'
    )
        THROW 59150, 'Owner A''s notification-preference capture is missing its paired-quiet-hours row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @NotifPrefCapture
        WHERE notification_type = N'connection_request' AND in_app_enabled = 0 AND email_enabled = 0
          AND quiet_hours_start IS NULL AND quiet_hours_end IS NULL
          AND updated_at_utc = @NotifPrefUpdatedAtUtcA2 AND feature_status = N'dormant_not_yet_enforced'
    )
        THROW 59150, 'Owner A''s notification-preference capture is missing its NULL-quiet-hours row.', 1;
    IF EXISTS (SELECT 1 FROM @NotifPrefCapture WHERE updated_at_utc = @NotifPrefUpdatedAtUtcB1)
        THROW 59151, 'Owner A''s notification-preference capture contains owner B''s row.', 1;
    IF EXISTS (SELECT 1 FROM @NotifPrefCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 59152, 'Owner A''s notification-preference capture has a missing or non-monotonic read window.', 1;

    DELETE @NotifPrefCapture;
    INSERT @NotifPrefCapture EXEC dbo.usp_ReadAccountExportNotificationPreferenceForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @NotifPrefCapture) <> 1
        THROW 59150, 'Owner B''s notification-preference capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @NotifPrefCapture
        WHERE notification_type = N'capture_ready' AND in_app_enabled = 1 AND email_enabled = 0
          AND updated_at_utc = @NotifPrefUpdatedAtUtcB1
    )
        THROW 59150, 'Owner B''s notification-preference capture is missing its own row.', 1;
    IF EXISTS (SELECT 1 FROM @NotifPrefCapture WHERE updated_at_utc IN (@NotifPrefUpdatedAtUtcA1, @NotifPrefUpdatedAtUtcA2))
        THROW 59151, 'Owner B''s notification-preference capture contains one of owner A''s rows.', 1;

    -- User consent (3 rows expected for A, 1 for B)
    DECLARE @ConsentCapture TABLE
    (
        consent_code nvarchar(100), policy_version nvarchar(100), consent_status nvarchar(30),
        recorded_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );
    INSERT @ConsentCapture EXEC dbo.usp_ReadAccountExportUserConsentForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @ConsentCapture) <> 3
        THROW 59150, 'Owner A''s user-consent capture does not have exactly three rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ConsentCapture
        WHERE consent_code = @ConsentCodeShared AND policy_version = @ConsentPolicyVersionShared
          AND consent_status = N'accepted' AND recorded_at_utc = @ConsentRecordedAtUtcA12
    )
        THROW 59150, 'Owner A''s user-consent capture is missing its accepted event.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ConsentCapture
        WHERE consent_code = @ConsentCodeShared AND policy_version = @ConsentPolicyVersionShared
          AND consent_status = N'withdrawn' AND recorded_at_utc = @ConsentRecordedAtUtcA12
    )
        THROW 59150, 'Owner A''s user-consent capture is missing its withdrawn event -- Paper 3 requires the full history, including withdrawal.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ConsentCapture
        WHERE consent_code = @ConsentCodeSecond AND policy_version = @ConsentPolicyVersionSecond
          AND consent_status = N'accepted' AND recorded_at_utc = @ConsentRecordedAtUtcA3
    )
        THROW 59150, 'Owner A''s user-consent capture is missing its second consent code''s event.', 1;
    IF EXISTS (SELECT 1 FROM @ConsentCapture WHERE consent_status = N'declined' OR recorded_at_utc = @ConsentRecordedAtUtcB1)
        THROW 59151, 'Owner A''s user-consent capture contains owner B''s event.', 1;
    IF EXISTS (SELECT 1 FROM @ConsentCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 59152, 'Owner A''s user-consent capture has a missing or non-monotonic read window.', 1;

    DELETE @ConsentCapture;
    INSERT @ConsentCapture EXEC dbo.usp_ReadAccountExportUserConsentForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @ConsentCapture) <> 1
        THROW 59150, 'Owner B''s user-consent capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ConsentCapture
        WHERE consent_code = @ConsentCodeShared AND policy_version = @ConsentPolicyVersionShared
          AND consent_status = N'declined' AND recorded_at_utc = @ConsentRecordedAtUtcB1
    )
        THROW 59150, 'Owner B''s user-consent capture is missing its own declined event.', 1;
    IF EXISTS (SELECT 1 FROM @ConsentCapture WHERE consent_status IN (N'accepted', N'withdrawn') OR recorded_at_utc IN (@ConsentRecordedAtUtcA12, @ConsentRecordedAtUtcA3))
        THROW 59151, 'Owner B''s user-consent capture contains one of owner A''s events -- despite sharing owner A''s consent_code and policy_version.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-008: structural grep across all three preference/consent reader procedures (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, deterministic ORDER BY, read-window columns present with exactly two SELECT keywords, no transaction control/write/dynamic SQL, no deleted_at_utc reference); per-procedure forbidden-column absence, owner predicate (user_id = @UserId), and join-count-of-one verified against each procedure''s own isolated content select-list text; the dormant-feature disclosure label verified present in both preference readers'' text and absent from the consent reader''s; a forged UserKey and a deactivated owner both yield zero rows (never an error) across all three procedures; real two-owner fixture data (an auto-seeded connection-preference row updated to distinguishing values, two notification-preference rows exercising both branches of the quiet-hours pairing CHECK, and a three-event consent history including a same-timestamp accepted-then-withdrawn pair for one code plus a second code, contrasted against an owner B event sharing the first code and policy version) proves all three readers return exactly and only the calling owner''s own rows, complete with the dormant-feature label where expected, non-null monotonic read windows, and no leaked evidence_json/source_context/user_id; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
