/* ============================================================
   PS-SETTINGS-EXPORT-003 - account export core readers (replacement
   package 1 of the 2026-08-29 reader topology)

   Read-only, owner-scoped SQL reader procedures for EXACTLY three C0
   V1-matrix domains (docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
   C0_ACCOUNT_EXPORT_ARCHITECTURE.md "Account, profile, Living Resume"
   row): the member's own dbo.app_users row, the member's own active
   dbo.member_profiles row, and the eight PS-PLAT-006 Living Resume
   tables (career_chapters, career_experiences, career_education,
   career_credentials, career_projects, career_achievements,
   career_skills, career_timeline_events) -- one procedure per table.
   This migration creates ONLY procedures. It creates no table, no
   trigger, no index, and writes nothing anywhere.

   Scope note: dbo.career_skill_links is deliberately NOT read here.
   Its rows reference evidence_item_id, whose disclosure rules are
   undecided; it is deferred to a future evidence-decision package and
   recorded as "excluded" (not silently omitted) in the DOMAINS registry
   of services/account_export_domain_readers.py.

   History this migration corrects: a broader package
   (PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-READERS-001, all 13 C0 domains at
   once, branch work/2026-08-29-settings-account-export-domain-readers-001,
   tip ecfa4754) failed independent pre-activation review. Its C1-style
   procedure mechanics (identity resolution, EXEC(N'CREATE OR ALTER...')
   wrapping, one-procedure-per-table split to keep every result set
   uniformly shaped) were sound and are reused below. Its scope and some
   inclusions were not: that package's account reader selected
   app_user.active (this package's contract forbids it -- implied by the
   active=1 precondition already enforced during identity resolution)
   and its profile reader selected profile.profile_key and
   profile.active (this package's contract forbids both -- an opaque
   internal key never disclosed as identity, and an implied
   precondition, respectively); its Living Resume coverage collapsed
   career_experiences/career_education/career_credentials/career_projects
   into inline joined columns on a single "chapter" reader rather than
   one genuinely independent reader per table. This package builds
   fresh and narrower: exactly the columns the CORE-READERS-001 lane
   claim enumerates, one reader per Living Resume table (ten procedures
   total), nothing folded together.

   Every procedure:
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, no table
       name, no dynamic SQL built from any argument (a pinned,
       exact-signature test asserts this: "@UserKey-only signatures");
     - resolves identity internally, BYTE-IDENTICALLY across all ten,
       exactly like PS-SETTINGS-EXPORT-001's owner procedures and every
       existing *ForOwner procedure in this repository: @UserKey -> an
       ACTIVE dbo.app_users row -> its ACTIVE dbo.member_profiles row.
       An unresolved identity RETURNs before any SELECT (no result set
       at all) -- the caller-side adapter treats that as zero rows, not
       an error;
     - filters every row by the resolved owner: id = @UserId for the
       account reader, profile_id = @ProfileId
       for the profile reader, owner_profile_id = @ProfileId for every
       Living Resume reader (career tables always key by profile, never
       by the internal user id);
     - for a Living Resume table with a chapter_id column
       (career_experiences, career_education, career_credentials,
       career_projects, career_achievements, career_timeline_events),
       joins dbo.career_chapters for the table's own opaque *_key
       uniqueidentifier where it has one plus the parent chapter_key
       for intra-export linkage, owner-predicated on BOTH the child and
       the parent (defense in depth beyond the composite FK that already
       ties them to the same owner_profile_id);
     - excludes soft-deleted rows: its own deleted_at_utc IS NULL where
       the table has that column (career_chapters, career_achievements,
       career_skills), AND, for every reader that joins career_chapters
       for parent linkage, ALSO chapter.deleted_at_utc IS NULL -- a
       DELIBERATE widening beyond the literal "every table that has the
       column" wording, documented here as the one contract
       interpretation this migration makes: career_experiences,
       career_education, career_credentials, career_projects, and
       career_timeline_events have no deleted_at_utc column of their
       own, but each is a 1:1 (or chapter-owned) extension of a chapter
       row; if that chapter was soft-deleted, its extension content must
       not surface through this back door even though the extension
       table itself carries no deletion flag to filter on;
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *), matching this package's lane-claim contract exactly --
       no internal integer id (chapter_id, entity_id, any *_id surrogate
       column), no created_by_user_id/approved_by_user_id, no
       user_key/auth_subject/row_version/profile_key, and never another
       member's data;
     - orders its result set deterministically: display_order then
       created_at_utc then the table's own (or, for a chapter-less
       extension table, the joined chapter's) opaque key -- never
       engine-default order;
     - returns a read window (SYSUTCDATETIME() captured at the top of
       the procedure as @ReadStartedAtUtc, and again inline in the
       content SELECT as read_ended_at_utc) as two TRAILING COLUMNS on
       the single content result set, not a second result set and not
       OUTPUT parameters. Both alternatives were considered and
       rejected for concrete, testable reasons recorded in
       CR1_ACCOUNT_EXPORT_CORE_READERS.md's "Read window mechanism"
       section: OUTPUT parameters would violate the pinned
       "@UserKey-only signature" test, and a genuinely separate second
       result set of a different shape would make every one of these
       procedures UNSAFE to call with INSERT ... EXEC -- Microsoft's own
       INSERT (Transact-SQL) reference is explicit that "each result set
       must be compatible with the columns in the table," not merely the
       first one, which is exactly the trap the paused DOMAIN-READERS-001
       package's own header comment independently records having hit.
       Columns-on-the-content-row keep every procedure here genuinely
       "INSERT-EXEC-safe by construction" (this package's own contract
       phrase) at the cost of the read window being absent, not merely
       zero, on a legitimate zero-row result (a member with no
       career_skills, for example); the calling adapter
       (services/account_export_domain_readers.py) independently
       brackets SYSUTCDATETIME() around its own call on the same
       connection as the documented fallback for exactly that case;
     - contains NO transaction control of any kind -- no BEGIN
       TRANSACTION, COMMIT, ROLLBACK, or TRY/CATCH, and no nested EXEC or
       dynamic SQL of its own. Every procedure here is a single read-only
       SELECT, so it can never reach a ROLLBACK, which is exactly why it
       is safe to call with a bare EXEC (asserted in this program's own
       tests and grepped in the paired verification script's own header)
       and, independently, why it never trips T-SQL's "Cannot use the
       ROLLBACK statement within an INSERT-EXEC statement" refusal either
       -- proven working for exactly this class of procedure by the
       already-gated PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql,
       whose two read-only procedures (usp_GetAccountExportStatusForOwner,
       usp_GetAccountExportDownloadMetadataForOwner) are captured with
       INSERT ... EXEC throughout.

   Requires PS-PLAT-006 (Living Resume schema); the PLAT chain that
   PS-PLAT-006 itself requires (PS-PLAT-000 through PS-PLAT-005, which
   between them establish dbo.app_users and dbo.member_profiles) arrives
   transitively through the registry's own linear ordering -- exactly
   the shorthand PS-SETTINGS-EXPORT-001 already uses by naming only
   PS-AUTH-001. This migration does not touch dbo.account_export_jobs or
   dbo.account_export_job_domains and does not require
   PS-SETTINGS-EXPORT-001 at all: it has no functional dependency on the
   job ledger, only on identity and Living Resume schema.

   Grant model: identical to PS-SETTINGS-EXPORT-001 and the paused
   DOMAIN-READERS-001 package (see PS-SETTINGS-EXPORT-001's own "Grant
   model" note). The governed apply identity holds db_ddladmin only and
   cannot GRANT EXECUTE; no GRANT, CREATE ROLE, CREATE USER, or
   sp_addrolemember statement appears anywhere in this file. The
   intended production grant -- EXECUTE on these ten procedures for the
   existing web-app principal role -- is a separate, later,
   administrator-run authority operation, not created here and not
   authorized by a repository merge of this file.

   THROW range: 58000-58099 (this migration). Verified clear of every
   sibling migration/rollback/verification file's range: the highest
   prior THROW number anywhere under SQL FIles/ (excluding the paused,
   unmerged DOMAIN-READERS-001 branch, which does not exist in this
   worktree) is 57735.

   No production apply is authorized by this file. No container,
   worker, schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-003_core_readers_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58000, 'PS-SETTINGS-EXPORT-003 requires the migration ledger.', 1;
    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-PLAT-006'
    )
        THROW 58001, 'PS-PLAT-006 must be applied before PS-SETTINGS-EXPORT-003.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 58002, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'display_name') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'email') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'auth_provider') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'profile_image_url') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'timezone_name') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_role') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'created_at') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'last_seen_at') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'updated_at') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_slug') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'display_name') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'headline') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'bio') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'location_text') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'updated_at_utc') IS NULL
        THROW 58003, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.career_chapters', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_experiences', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_education', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_credentials', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_projects', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_achievements', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_skills', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_timeline_events', N'U') IS NULL
        THROW 58004, 'The Living Resume (PS-PLAT-006) schema is missing.', 1;

    IF COL_LENGTH(N'dbo.career_chapters', N'chapter_key') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'chapter_type') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'title') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'organization_name') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'location_text') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'summary') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'original_member_wording') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'approved_wording') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'start_date') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'end_date') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'date_precision') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'approval_status') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'publication_status') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'featured') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'display_order') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'approved_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'updated_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_chapters', N'deleted_at_utc') IS NULL
        THROW 58005, 'The career_chapters columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_experiences', N'chapter_id') IS NULL
       OR COL_LENGTH(N'dbo.career_experiences', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_experiences', N'role_title') IS NULL
       OR COL_LENGTH(N'dbo.career_experiences', N'employer_name') IS NULL
       OR COL_LENGTH(N'dbo.career_experiences', N'employment_type') IS NULL
       OR COL_LENGTH(N'dbo.career_experiences', N'current_role') IS NULL
        THROW 58006, 'The career_experiences columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_education', N'chapter_id') IS NULL
       OR COL_LENGTH(N'dbo.career_education', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_education', N'institution_name') IS NULL
       OR COL_LENGTH(N'dbo.career_education', N'degree_name') IS NULL
       OR COL_LENGTH(N'dbo.career_education', N'field_of_study') IS NULL
       OR COL_LENGTH(N'dbo.career_education', N'education_status') IS NULL
       OR COL_LENGTH(N'dbo.career_education', N'grade_text') IS NULL
        THROW 58007, 'The career_education columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_credentials', N'chapter_id') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'credential_name') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'issuer_name') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'credential_identifier') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'issue_date') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'expiration_date') IS NULL
       OR COL_LENGTH(N'dbo.career_credentials', N'verification_url') IS NULL
        THROW 58008, 'The career_credentials columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_projects', N'chapter_id') IS NULL
       OR COL_LENGTH(N'dbo.career_projects', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_projects', N'project_name') IS NULL
       OR COL_LENGTH(N'dbo.career_projects', N'project_role') IS NULL
       OR COL_LENGTH(N'dbo.career_projects', N'project_status') IS NULL
       OR COL_LENGTH(N'dbo.career_projects', N'project_url') IS NULL
        THROW 58009, 'The career_projects columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_achievements', N'achievement_key') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'chapter_id') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'original_member_wording') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'approved_wording') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'metric_value') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'metric_label') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'approval_status') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'featured') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'display_order') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'approved_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'updated_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_achievements', N'deleted_at_utc') IS NULL
        THROW 58010, 'The career_achievements columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_skills', N'skill_key') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'skill_name') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'skill_summary') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'approval_status') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'featured') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'display_order') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'updated_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'deleted_at_utc') IS NULL
        THROW 58011, 'The career_skills columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_timeline_events', N'timeline_event_key') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'chapter_id') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'event_label') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'event_type') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'start_date') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'end_date') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'date_precision') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'approval_status') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'constellation_featured') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'display_order') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.career_timeline_events', N'updated_at_utc') IS NULL
        THROW 58012, 'The career_timeline_events columns are incompatible.', 1;

    /* ============================================================
       DOMAIN 1: own dbo.app_users row (9 content columns)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportAccountForOwner
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
                app_user.display_name,
                app_user.email,
                app_user.auth_provider,
                app_user.profile_image_url,
                app_user.timezone_name,
                app_user.user_role,
                app_user.created_at AS created_at_utc,
                app_user.last_seen_at AS last_seen_at_utc,
                app_user.updated_at AS updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.app_users AS app_user
            WHERE app_user.id = @UserId
            ORDER BY app_user.id;
        END;
    ');

    /* ============================================================
       DOMAIN 2: own active dbo.member_profiles row (8 content columns)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportProfileForOwner
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
                profile.profile_slug,
                profile.display_name,
                profile.headline,
                profile.bio,
                profile.location_text,
                profile.visibility,
                profile.created_at_utc,
                profile.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.member_profiles AS profile
            WHERE profile.profile_id = @ProfileId
            ORDER BY profile.profile_id;
        END;
    ');

    /* ============================================================
       DOMAIN 3: Living Resume -- one reader per PS-PLAT-006 table
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerChapterForOwner
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
                chapter.chapter_key,
                chapter.chapter_type,
                chapter.title,
                chapter.organization_name,
                chapter.location_text,
                chapter.summary,
                chapter.original_member_wording,
                chapter.approved_wording,
                chapter.start_date,
                chapter.end_date,
                chapter.date_precision,
                chapter.visibility,
                chapter.approval_status,
                chapter.publication_status,
                chapter.featured,
                chapter.display_order,
                chapter.approved_at_utc,
                chapter.created_at_utc,
                chapter.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_chapters AS chapter
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.created_at_utc, chapter.chapter_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerExperienceForOwner
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
                chapter.chapter_key,
                experience.role_title,
                experience.employer_name,
                experience.employment_type,
                experience.current_role,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_experiences AS experience
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = experience.chapter_id
            WHERE experience.owner_profile_id = @ProfileId
              AND chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.created_at_utc, chapter.chapter_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerEducationForOwner
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
                chapter.chapter_key,
                education.institution_name,
                education.degree_name,
                education.field_of_study,
                education.education_status,
                education.grade_text,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_education AS education
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = education.chapter_id
            WHERE education.owner_profile_id = @ProfileId
              AND chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.created_at_utc, chapter.chapter_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerCredentialForOwner
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
                chapter.chapter_key,
                credential.credential_name,
                credential.issuer_name,
                credential.credential_identifier,
                credential.issue_date,
                credential.expiration_date,
                credential.verification_url,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_credentials AS credential
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = credential.chapter_id
            WHERE credential.owner_profile_id = @ProfileId
              AND chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.created_at_utc, chapter.chapter_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerProjectForOwner
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
                chapter.chapter_key,
                project.project_name,
                project.project_role,
                project.project_status,
                project.project_url,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_projects AS project
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = project.chapter_id
            WHERE project.owner_profile_id = @ProfileId
              AND chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.created_at_utc, chapter.chapter_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerAchievementForOwner
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
                achievement.achievement_key,
                chapter.chapter_key,
                achievement.original_member_wording,
                achievement.approved_wording,
                achievement.metric_value,
                achievement.metric_label,
                achievement.visibility,
                achievement.approval_status,
                achievement.featured,
                achievement.display_order,
                achievement.approved_at_utc,
                achievement.created_at_utc,
                achievement.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_achievements AS achievement
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = achievement.chapter_id
            WHERE achievement.owner_profile_id = @ProfileId
              AND achievement.deleted_at_utc IS NULL
              AND chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY achievement.display_order, achievement.created_at_utc, achievement.achievement_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerSkillForOwner
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
                skill.skill_key,
                skill.skill_name,
                skill.skill_summary,
                skill.visibility,
                skill.approval_status,
                skill.featured,
                skill.display_order,
                skill.created_at_utc,
                skill.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_skills AS skill
            WHERE skill.owner_profile_id = @ProfileId
              AND skill.deleted_at_utc IS NULL
            ORDER BY skill.display_order, skill.created_at_utc, skill.skill_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerTimelineEventForOwner
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
                timeline_event.timeline_event_key,
                chapter.chapter_key,
                timeline_event.event_label,
                timeline_event.event_type,
                timeline_event.start_date,
                timeline_event.end_date,
                timeline_event.date_precision,
                timeline_event.visibility,
                timeline_event.approval_status,
                timeline_event.constellation_featured,
                timeline_event.display_order,
                timeline_event.created_at_utc,
                timeline_event.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_timeline_events AS timeline_event
            JOIN dbo.career_chapters AS chapter ON chapter.chapter_id = timeline_event.chapter_id
            WHERE timeline_event.owner_profile_id = @ProfileId
              AND chapter.owner_profile_id = @ProfileId
              AND chapter.deleted_at_utc IS NULL
            ORDER BY timeline_event.display_order, timeline_event.created_at_utc, timeline_event.timeline_event_key;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-003'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-003',
            N'Read-only owner-scoped account-export core readers (replacement package 1, 2026-08-29 topology): ten @UserKey-only procedures over the own account row, active profile, and the eight PS-PLAT-006 Living Resume tables, each with an exact allowlist, owner predicate, soft-delete exclusion, deterministic order, and trailing read-window columns. career_skill_links deliberately not read. No table, trigger, index, or runtime wiring changed.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-003"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
