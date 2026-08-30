/* ============================================================
   PS-SETTINGS-EXPORT-008 - account export preferences and consent
   readers

   Read-only, owner-scoped SQL reader procedures executing the owner's
   accepted 2026-08-30 "Paper 2" and "Paper 3" rulings over EXACTLY
   three PS-PLAT-004 tables: dbo.connection_preferences,
   dbo.notification_preferences, dbo.user_consents. This migration
   creates ONLY procedures. It creates no table, no trigger, no index,
   and writes nothing anywhere except its own ledger row.

   IDENTITY -- THE ONE STRUCTURAL NUANCE OF THIS PACKAGE. All three
   tables key on dbo.app_users.id via their own user_id column, NOT
   owner_profile_id -- the first tables this reader program has read
   whose CLAIMED TABLE itself carries an explicit user_id foreign-key
   column (confirmed by reading PS-PLAT-004_connections_notifications.sql''s
   own DDL: all three carry "user_id int NOT NULL" with a foreign key
   straight to dbo.app_users(id), never a member_profiles.profile_id
   column). This is NOT a new IDENTITY pattern for the program, only a
   new TABLE shape: usp_ReadAccountExportAccountForOwner
   (PS-SETTINGS-EXPORT-003) already filters "WHERE app_user.id =
   @UserId" for the identical reason (dbo.app_users itself keys on id,
   not profile_id) -- but that reader''s claimed table IS dbo.app_users
   itself, matched on its own primary key, never a separate user_id
   column on some other table. This migration''s three readers are the
   second, third, and fourth readers in the program to filter on
   @UserId instead of @ProfileId, and the first three whose own claimed
   table carries a distinct user_id column rather than being
   dbo.app_users itself.
   Every reader below still resolves the full, BYTE-IDENTICAL identity
   header every prior package uses (@UserKey -> an active dbo.app_users
   row -> its active dbo.member_profiles row, capturing BOTH @ProfileId
   and @UserId even though only @UserId is used downstream) rather than
   a shortened header that skips the member_profiles join. Rationale,
   recorded because a reviewer will ask why an unused @ProfileId is
   still resolved: this program enforces one identity contract everywhere
   -- a member without an ACTIVE profile gets NOTHING from ANY reader,
   including these three -- and the identity-header byte-consistency
   test (test_identity_header_is_byte_identical_across_every_account_
   export_reader_in_the_program) requires exactly ONE distinct header
   variant across the whole program. A shortened, profile-skipping
   header would both break that invariant and quietly create a second,
   weaker identity contract (member active, profile status ignored) for
   exactly these three readers.

   PAPER 2 -- BOTH PREFERENCE TABLES INCLUDED, LABELED DORMANT. C0''s own
   V1 domain matrix already called this disposition for both tables
   ("Connection preferences: Included, labeled dormant"; "Notification
   preferences: Included after owner-scoped/dormant field allowlist").
   Both dbo.connection_preferences and dbo.notification_preferences are
   real, safely-bounded member field sets with NO live enforcement path
   anywhere in this codebase today (confirmed by a repository-wide grep
   for any INSERT/UPDATE against either table outside PS-PLAT-004''s own
   backfill and PS-AUTH-001''s own per-signup seed for
   dbo.connection_preferences -- zero results for dbo.
   notification_preferences at all: it has no writer of any kind
   anywhere, so a real export legitimately returns zero rows for it
   today; docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/B0_PREFERENCES_
   CONSENTS_TAXONOMY_SCHEMA_FIT.md''s own schema-fit table independently
   confirms both findings). Exporting either table''s stored values
   without saying so would let an all-defaults row masquerade as live
   product behavior the member actually configured and the product
   actually honors. Both readers therefore emit an explicit constant
   disclosure column, feature_status = ''dormant_not_yet_enforced'', on
   every row -- a projection-truth statement about the FEATURE (no
   runtime path reads or acts on these columns today), never a stored
   member fact and never a value a member set. dbo.connection_preferences
   is additionally auto-seeded, all-defaults, for every member (PS-PLAT-
   004''s own backfill INSERT plus PS-AUTH-001''s usp_UpsertAppUserFromAuth
   per-signup INSERT: "IF NOT EXISTS (SELECT 1 FROM dbo.
   connection_preferences WHERE user_id = @UserId) INSERT dbo.
   connection_preferences(user_id) VALUES (@UserId);") -- a real export
   for any member returns exactly one row here today, always at column
   defaults, which is precisely the scenario the dormant label exists to
   disclose truthfully.

   PAPER 3 -- THE MEMBER''S OWN CONSENT HISTORY INCLUDED; evidence_json
   EXCLUDED WHOLE; NO THIRD-PARTY CONSENT READ. dbo.user_consents is an
   append-only history ledger (consent_code, policy_version,
   consent_status, and a server-defaulted recorded_at_utc per event);
   C0''s own V1 domain matrix already called this disposition ("Consent
   history: Included, evidence-minimized... exclude raw claims, secrets,
   excessive evidence, and third-party content"). consent_status'' own
   CHECK constraint (CK_user_consents_status) allows ''accepted'',
   ''declined'', AND ''withdrawn'' -- this is genuine history semantics, not
   a single current-state flag, and a withdrawal is its own later ledger
   ROW, never an update or deletion of the earlier accepted event (per
   B0_PREFERENCES_CONSENTS_TAXONOMY_SCHEMA_FIT.md''s own "withdrawn means
   a member has rescinded an earlier accepted instance... a new ledger
   event, never an update or deletion" rule). This reader includes EVERY
   row for the member, at every status, so a member''s export shows their
   full consent history including any withdrawal -- never only the
   latest or only the accepted ones. evidence_json is EXCLUDED WHOLE,
   category UNCONSTRAINED_EVIDENCE: it is a schema-free nvarchar(max)
   column (CK_user_consents_evidence only requires valid JSON, never a
   bounded shape) that could hold anything a future writer chooses to
   put there, up to and including network addresses or device details --
   excluded until a future package performs the field-by-field review
   the owner''s ruling requires before any of it could be disclosed.
   source_context (nvarchar(100), a plain scalar column distinct from
   evidence_json) is ALSO excluded, but for a different, disclosed
   reason: a repository-wide search confirms NO procedure anywhere
   writes to dbo.user_consents at all today (PS-ASK-PETE-DIRECT-001''s
   own consent value has its own separate, feature-owned storage
   contract and never touches this table) -- there is no procedure body
   to trace the way this program''s own "trace actual writes" discipline
   requires (the precedent PS-SETTINGS-EXPORT-007 set for
   deletion_capture_row_version/scan_result: classify a column by
   reading what actually writes it, never by name or type alone), so
   source_context''s real-world population cannot be verified as a
   bounded, non-PII label today. Excluded pending a future package that
   actually defines a consent-writing contract, at which point this
   column can be reclassified against real procedure bodies. Finally,
   NO third-party consent is read: dbo.recruiter_questions is untouched
   and unread by this migration, by any reader it creates, and by its
   paired verification script -- stated here explicitly per the owner''s
   ruling, not merely true by omission.

   Every procedure:
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, table name, or
       dynamic SQL built from any argument;
     - resolves identity with the byte-identical header every reader in
       this program shares: @UserKey -> an ACTIVE dbo.app_users row ->
       its ACTIVE dbo.member_profiles row. An unresolved identity
       RETURNs before any SELECT -- no result set at all;
     - filters its one claimed table by preference.user_id = @UserId /
       consent.user_id = @UserId (never owner_profile_id -- these three
       tables have no such column);
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *) -- no user_id, no user_consent_id, no row_version (the
       two preference tables have none), no evidence_json, no
       source_context;
     - orders its result set deterministically: the two preference
       readers order by their own internal user_id (connection_
       preferences, one row per owner, mirrors usp_ReadAccountExport
       AccountForOwner''s own "ORDER BY app_user.id" idiom of ordering by
       an excluded internal column) or by notification_type (unique
       within one owner''s rows once user_id is fixed by the WHERE
       predicate, per PK_notification_preferences (user_id,
       notification_type)); the consent reader orders by consent_code,
       then recorded_at_utc, then its own internal user_consent_id --
       IX_user_consents_history (user_id, consent_code, recorded_at_utc
       DESC) is NOT a unique index, so consent_code + recorded_at_utc
       alone cannot be proven collision-free (two events for the same
       code could in principle share one recorded_at_utc tick); the
       trailing user_consent_id tiebreak (excluded from output, exactly
       like every other reader in the program that orders by an
       excluded internal id) makes the order fully deterministic even
       in that case;
     - returns the read window as two TRAILING COLUMNS on the single
       content result set, identical mechanism to every prior package;
     - contains NO transaction control of any kind, no write, and no
       nested EXEC/dynamic SQL.

   Requires PS-PLAT-004 (creates all three tables) directly; PS-AUTH-001
   is a registry-level requirement only (its usp_UpsertAppUserFromAuth is
   the paired verification script''s own owner-provisioning dependency,
   exactly the same reasoning PS-SETTINGS-EXPORT-003 through -007 each
   already recorded for the identical omission from this migration
   body''s own guard checks) -- app_users/member_profiles'' identity-
   resolution columns predate PS-AUTH-001 and this migration''s guard
   checks them directly instead.

   Grant model: identical to every prior package in this program. The
   governed apply identity holds db_ddladmin only and cannot GRANT
   EXECUTE; no GRANT, CREATE ROLE, CREATE USER, or sp_addrolemember
   statement appears anywhere in this file. The intended production
   grant -- EXECUTE on these three procedures for the existing web-app
   principal role -- is a separate, later, administrator-run authority
   operation, not created here and not authorized by a repository merge
   of this file. Design only; nothing applied.

   THROW range: 59000-59099 (this migration; forward uses 59000-59007,
   rollback continues at 59008). Verified clear of every sibling
   migration/rollback/verification file''s range: a repository-wide scan
   of every .sql file under SQL FIles/ found the highest prior THROW
   number anywhere to be 58953 (PS-SETTINGS-EXPORT-007''s own
   verification script).

   No production apply is authorized by this file. No container,
   worker, schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-008_preferences_consent_reader_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 59000, 'PS-SETTINGS-EXPORT-008 requires the migration ledger.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-PLAT-004')
        THROW 59001, 'PS-PLAT-004 must be applied before PS-SETTINGS-EXPORT-008.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 59002, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 59003, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.connection_preferences', N'U') IS NULL
       OR OBJECT_ID(N'dbo.notification_preferences', N'U') IS NULL
       OR OBJECT_ID(N'dbo.user_consents', N'U') IS NULL
        THROW 59004, 'The PeerSlate connections/notifications/consent schema is missing.', 1;

    IF COL_LENGTH(N'dbo.connection_preferences', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.connection_preferences', N'discovery_opt_in') IS NULL
       OR COL_LENGTH(N'dbo.connection_preferences', N'goal_matching_opt_in') IS NULL
       OR COL_LENGTH(N'dbo.connection_preferences', N'recruiter_discovery_opt_in') IS NULL
       OR COL_LENGTH(N'dbo.connection_preferences', N'discoverable_audience') IS NULL
       OR COL_LENGTH(N'dbo.connection_preferences', N'updated_at_utc') IS NULL
        THROW 59005, 'The connection_preferences columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.notification_preferences', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.notification_preferences', N'notification_type') IS NULL
       OR COL_LENGTH(N'dbo.notification_preferences', N'in_app_enabled') IS NULL
       OR COL_LENGTH(N'dbo.notification_preferences', N'email_enabled') IS NULL
       OR COL_LENGTH(N'dbo.notification_preferences', N'quiet_hours_start') IS NULL
       OR COL_LENGTH(N'dbo.notification_preferences', N'quiet_hours_end') IS NULL
       OR COL_LENGTH(N'dbo.notification_preferences', N'updated_at_utc') IS NULL
        THROW 59006, 'The notification_preferences columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.user_consents', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'consent_code') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'policy_version') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'consent_status') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'recorded_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'source_context') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'evidence_json') IS NULL
       OR COL_LENGTH(N'dbo.user_consents', N'user_consent_id') IS NULL
        THROW 59007, 'The user_consents columns are incompatible.', 1;

    /* ============================================================
       READER 1: dbo.connection_preferences (5 content columns plus the
       dormant-feature disclosure constant; no parent; PK is user_id
       alone, so at most one row can exist per member)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportConnectionPreferenceForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                preference.discovery_opt_in,
                preference.goal_matching_opt_in,
                preference.recruiter_discovery_opt_in,
                preference.discoverable_audience,
                preference.updated_at_utc,
                N''dormant_not_yet_enforced'' AS feature_status,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.connection_preferences AS preference
            WHERE preference.user_id = @UserId
            ORDER BY preference.user_id;
        END;
    ');

    /* ============================================================
       READER 2: dbo.notification_preferences (6 content columns plus
       the dormant-feature disclosure constant; no parent; PK is
       (user_id, notification_type), so notification_type alone is
       unique once user_id is fixed by the WHERE predicate. This table
       has NO writer anywhere in this codebase -- a real export
       legitimately returns zero rows for every member today.)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportNotificationPreferenceForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                preference.notification_type,
                preference.in_app_enabled,
                preference.email_enabled,
                preference.quiet_hours_start,
                preference.quiet_hours_end,
                preference.updated_at_utc,
                N''dormant_not_yet_enforced'' AS feature_status,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.notification_preferences AS preference
            WHERE preference.user_id = @UserId
            ORDER BY preference.notification_type;
        END;
    ');

    /* ============================================================
       READER 3: dbo.user_consents (4 content columns; no parent; no
       dormant-feature label -- consent records are real, live facts,
       not an unenforced switch. evidence_json and source_context are
       both excluded (see this file''s own header for the two distinct
       reasons); consent_status includes ''withdrawn'' and every status
       is returned, so a member''s full history -- including any
       withdrawal -- is exported, never only the latest event.)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportUserConsentForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                consent.consent_code,
                consent.policy_version,
                consent.consent_status,
                consent.recorded_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.user_consents AS consent
            WHERE consent.user_id = @UserId
            ORDER BY consent.consent_code, consent.recorded_at_utc, consent.user_consent_id;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-008'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-008',
            N'Read-only owner-scoped account-export preference/consent readers: three @UserKey-only procedures over connection_preferences, notification_preferences, user_consents. Both preference readers add a dormant-feature disclosure column since neither is enforced today. The consent reader returns the member''s full history including withdrawn; evidence_json and source_context are excluded. No third-party consent (recruiter_questions) is read.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-008"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
