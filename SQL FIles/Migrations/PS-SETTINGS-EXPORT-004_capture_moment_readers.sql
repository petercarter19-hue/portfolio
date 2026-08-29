/* ============================================================
   PS-SETTINGS-EXPORT-004 - account export capture/moment readers
   (replacement package 2 of the 2026-08-29 reader topology)

   Read-only, owner-scoped SQL reader procedures for EXACTLY the C0
   V1-matrix "Capture/revisions" and "Moments/versions/sources/
   placements" rows (docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
   C0_ACCOUNT_EXPORT_ARCHITECTURE.md): dbo.captures, dbo.capture_revisions,
   dbo.moments, dbo.moment_versions, dbo.moment_sources, and
   dbo.moment_placements -- one procedure per table, six total. This
   migration creates ONLY procedures. It creates no table, no trigger,
   no index, and writes nothing anywhere except its own ledger row.

   Text truth only -- this package's defining boundary: every content
   hash, checksum, media/photo/voice/blob/file reference, transcript
   linkage, storage locator, and URL to stored media is excluded from
   every allowlist below, along with every internal integer id/surrogate,
   every created-by/approved-by/reactivated-by/removed-by user id, every
   row_version, and every column carrying its OWN row's soft-delete
   state (used only as a WHERE predicate, never selected). None of the
   six tables here actually has a media/hash/transcript column of its
   own -- that boundary is recorded because it governs this package's
   field decisions generally (and binds the future voice/photo/media
   reader packages), not because a row here needed one excluded.

   Modeled directly on PS-SETTINGS-EXPORT-003_core_readers.sql
   (replacement package 1, applied at main cc5174da after independent
   review): identical identity-resolution header, one-procedure-per-table
   split (T-SQL's INSERT ... EXEC requires every result set returned to a
   capturing table to be column-compatible with it, not merely the
   first one, so a genuinely single, uniformly shaped content SELECT per
   procedure keeps every reader here INSERT-EXEC-safe by construction),
   the read window as two trailing columns on that single result set,
   and the "owner predicate on both sides of a parent join" defense in
   depth that package's own independent review added (its correction
   round, finding 3).

   Every procedure:
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, no table
       name, no dynamic SQL built from any argument;
     - resolves identity internally, BYTE-IDENTICALLY across all six,
       exactly like PS-SETTINGS-EXPORT-003's own ten readers: @UserKey
       -> an ACTIVE dbo.app_users row -> its ACTIVE dbo.member_profiles
       row. An unresolved identity RETURNs before any SELECT (no result
       set at all) -- the caller-side adapter treats that as zero rows,
       never an error;
     - filters every row by the resolved owner profile. dbo.moment_sources
       and dbo.moment_placements carry their own owner_profile_id
       column, so both it AND the joined dbo.moments parent's
       owner_profile_id are independently asserted against @ProfileId
       (the package-1-review "both sides" pattern, applied here from the
       start). dbo.capture_revisions and dbo.moment_versions carry no
       owner_profile_id column of their own -- only a bare *_id foreign
       key to their parent -- so ownership is asserted once, through the
       joined parent; that parent predicate is the only column that
       exists to check, not an incomplete application of the pattern;
     - replaces every internal integer id with the row's own opaque
       *_key uniqueidentifier, plus the parent's opaque key
       (capture_key / moment_key) for intra-export linkage wherever the
       table carries a parent id, resolved through an owner-predicated
       join -- never the raw internal id;
     - dbo.moment_sources additionally carries its own source_capture_key
       and nullable source_revision_key: opaque, strictly-intra-export
       linkage to the exact dbo.captures / dbo.capture_revisions row a
       Moment was sourced from. No media column of any kind exists on
       this table, and both keys resolve only for the calling owner's
       own moment_sources row (never a caller-supplied capture);
     - dbo.moment_placements' target_entity_id (a foreign key to
       dbo.slate_entities, the Opportunity Slate destination) is
       DELIBERATELY EXCLUDED -- unlike every other parent-id column
       here, it does not point at one of this package's six claimed
       tables. dbo.slate_entities belongs to the separate Opportunity
       Slate C0 V1-matrix row, which has its own future, separately
       claimed reader; this migration adds no dependency on
       PS-PLAT-002/PS-PLAT-005 (the migrations that create
       dbo.slate_entities) precisely because it never reads that table.
       The placement row still exports its own lifecycle facts (status,
       moment_version_number, and every timestamp) through its
       dbo.moments parent link; only the cross-domain destination
       identity is deferred;
     - excludes soft-deleted content: dbo.captures.deleted_at_utc IS
       NULL (its own, only, soft-delete column among these six tables).
       dbo.moments, dbo.moment_versions, dbo.moment_sources, and
       dbo.moment_placements have no deleted_at_utc column of their own
       -- discarding a Moment proposal is a real DELETE
       (usp_DiscardMomentProposal), not a soft-delete flag, so there is
       no such predicate to add for them. dbo.moment_sources' own
       source_deleted_at_utc and source_state columns are a DIFFERENT
       fact: whether the LINKED CAPTURE was later deleted out from under
       an already-confirmed Moment, not a flag on the moment_source
       row's own existence (that row is 1:1 with its Moment via
       UQ_moment_sources_moment and is never itself soft-deleted) -- so
       both are INCLUDED as content, never treated as a presence
       predicate;
     - does not filter dbo.captures by active or status: an archived
       capture (status = 'archived', active = 0) is real, undeleted,
       member-authored content the owner would expect in their own
       export, so only the true soft-delete column gates row presence.
       capture.active itself is excluded from the output as a redundant
       encoding of status -- the same reasoning PS-SETTINGS-EXPORT-003
       applied to app_user.active/profile.active (implied by the
       identity-resolution precondition, not independently informative);
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *), matching this package's lane-claim contract exactly;
     - orders its result set deterministically: dbo.captures and
       dbo.moments (no parent, no per-parent sequence column) order by
       their own created_at_utc then their own opaque key. Their
       per-parent-sequenced children (dbo.capture_revisions'
       revision_number; dbo.moment_versions' version_number) order by
       the PARENT's created_at_utc then the parent's opaque key -- so
       every owner's revisions/versions group by their capture/Moment in
       creation order -- then the child's own sequence number as the
       final tiebreak, because that sequence number is only unique
       within one parent, never globally. dbo.moment_sources (1:1 with
       its Moment) and dbo.moment_placements (their own creation
       timeline; a Moment may have several over time) instead order by
       their own created_at_utc then their own opaque key directly --
       see the per-procedure ORDER BY below for the exact column list;
     - returns a read window (SYSUTCDATETIME() captured at the top of
       the procedure as @ReadStartedAtUtc, and again inline in the
       content SELECT as read_ended_at_utc) as two TRAILING COLUMNS on
       the single content result set -- identical mechanism and
       rationale to PS-SETTINGS-EXPORT-003 (see that migration's own
       header and CR1_ACCOUNT_EXPORT_CORE_READERS.md's "Read window
       mechanism" section: OUTPUT parameters would violate the pinned
       "@UserKey-only signature" test, and a second, differently-shaped
       result set would make INSERT ... EXEC unsafe per Microsoft's own
       documented requirement that every result set, not merely the
       first, be column-compatible with the capturing table);
     - contains NO transaction control of any kind -- no BEGIN
       TRANSACTION, COMMIT, ROLLBACK, or TRY/CATCH, and no nested EXEC or
       dynamic SQL of its own. Every procedure here is a single
       read-only SELECT, so it is safe to call with a bare EXEC and can
       never trip T-SQL's "Cannot use the ROLLBACK statement within an
       INSERT-EXEC statement" refusal.

   Requires PS-CAPTURE-001, PS-CAPTURE-002, PS-MOMENT-001, and
   PS-PLACEMENT-001 (the migrations that create this package's six
   tables; all four are applied in production per
   docs/governance/PRODUCTION_SCHEMA_STATE.md despite living under
   SQL FIles/Migrations/proposed/, and this package reads them as
   schema truth on that basis, exactly as this package's own writer
   brief directs). PS-AUTH-001 is named in the registry's own requires
   list too, for the paired verification script's
   usp_UpsertAppUserFromAuth dependency -- exactly the omission
   PS-SETTINGS-EXPORT-003's own gate round caught and corrected after
   the fact; named here from the start instead -- NOT because this
   migration's own guards below check for it: every column these guards
   or procedures touch on dbo.app_users/dbo.member_profiles already
   exists as of PS-PLAT-000/PS-PLAT-002, predating PS-AUTH-001, exactly
   like PS-SETTINGS-EXPORT-003's own recorded reasoning for the same
   omission. This migration does not require PS-PLAT-002 or PS-PLAT-005
   (which together create dbo.slate_entities): it never reads that
   table, per the target_entity_id exclusion above.

   Grant model: identical to PS-SETTINGS-EXPORT-001 and
   PS-SETTINGS-EXPORT-003. The governed apply identity holds
   db_ddladmin only and cannot GRANT EXECUTE; no GRANT, CREATE ROLE,
   CREATE USER, or sp_addrolemember statement appears anywhere in this
   file. The intended production grant -- EXECUTE on these six
   procedures for the existing web-app principal role -- is a separate,
   later, administrator-run authority operation, not created here and
   not authorized by a repository merge of this file.

   THROW range: 58200-58299 (this migration; the rollback file continues
   within the same block at 58214). Verified clear of every sibling
   migration/rollback/verification file's range: the highest prior THROW
   number anywhere under SQL FIles/ is 58161
   (PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql).

   No production apply is authorized by this file. No container,
   worker, schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-004_capture_moment_readers_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-004_capture_moment_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58200, 'PS-SETTINGS-EXPORT-004 requires the migration ledger.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-CAPTURE-001')
        THROW 58201, 'PS-CAPTURE-001 must be applied before PS-SETTINGS-EXPORT-004.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-CAPTURE-002')
        THROW 58202, 'PS-CAPTURE-002 must be applied before PS-SETTINGS-EXPORT-004.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-MOMENT-001')
        THROW 58203, 'PS-MOMENT-001 must be applied before PS-SETTINGS-EXPORT-004.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-PLACEMENT-001')
        THROW 58204, 'PS-PLACEMENT-001 must be applied before PS-SETTINGS-EXPORT-004.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 58205, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 58206, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.captures', N'U') IS NULL
       OR OBJECT_ID(N'dbo.capture_revisions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moments', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.moment_placements', N'U') IS NULL
        THROW 58207, 'The Capture or Moment schema is missing.', 1;

    IF COL_LENGTH(N'dbo.captures', N'capture_key') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'capture_type') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'body') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'status') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'deleted_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.captures', N'updated_at_utc') IS NULL
        THROW 58208, 'The captures columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.capture_revisions', N'revision_key') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'capture_id') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'revision_number') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'body') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'correction_note') IS NULL
       OR COL_LENGTH(N'dbo.capture_revisions', N'corrected_at_utc') IS NULL
        THROW 58209, 'The capture_revisions columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.moments', N'moment_key') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'status') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'current_version_number') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'confirmed_version_number') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'confirmed_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.moments', N'updated_at_utc') IS NULL
        THROW 58210, 'The moments columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.moment_versions', N'moment_version_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'moment_id') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'version_number') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'moment_kind') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'title') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'occurred_on') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'occurred_precision') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'narrative') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'why_it_matters') IS NULL
       OR COL_LENGTH(N'dbo.moment_versions', N'saved_at_utc') IS NULL
        THROW 58211, 'The moment_versions columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.moment_sources', N'moment_source_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'moment_id') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_capture_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_revision_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_revision_number') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_state') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'source_deleted_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.moment_sources', N'created_at_utc') IS NULL
        THROW 58212, 'The moment_sources columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.moment_placements', N'placement_key') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'moment_id') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'moment_version_number') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'placement_status') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'reactivated_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'removed_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.moment_placements', N'updated_at_utc') IS NULL
        THROW 58213, 'The moment_placements columns are incompatible.', 1;

    /* ============================================================
       READER 1: dbo.captures (7 content columns)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCaptureForOwner
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
                capture.capture_key,
                capture.capture_type,
                capture.body,
                capture.visibility,
                capture.status,
                capture.created_at_utc,
                capture.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.captures AS capture
            WHERE capture.owner_profile_id = @ProfileId
              AND capture.deleted_at_utc IS NULL
            ORDER BY capture.created_at_utc, capture.capture_key;
        END;
    ');

    /* ============================================================
       READER 2: dbo.capture_revisions (6 content columns; parent
       linkage via dbo.captures.capture_key, single-sided owner
       predicate -- capture_revisions has no owner_profile_id column
       of its own)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCaptureRevisionForOwner
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
                revision.revision_key,
                capture.capture_key,
                revision.revision_number,
                revision.body,
                revision.correction_note,
                revision.corrected_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.capture_revisions AS revision
            JOIN dbo.captures AS capture
              ON capture.capture_id = revision.capture_id
            WHERE capture.owner_profile_id = @ProfileId
              AND capture.deleted_at_utc IS NULL
            ORDER BY capture.created_at_utc, capture.capture_key, revision.revision_number;
        END;
    ');

    /* ============================================================
       READER 3: dbo.moments (8 content columns)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportMomentForOwner
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
                moment.moment_key,
                moment.visibility,
                moment.status,
                moment.current_version_number,
                moment.confirmed_version_number,
                moment.confirmed_at_utc,
                moment.created_at_utc,
                moment.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.moments AS moment
            WHERE moment.owner_profile_id = @ProfileId
            ORDER BY moment.created_at_utc, moment.moment_key;
        END;
    ');

    /* ============================================================
       READER 4: dbo.moment_versions (10 content columns; parent
       linkage via dbo.moments.moment_key, single-sided owner
       predicate -- moment_versions has no owner_profile_id column of
       its own)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportMomentVersionForOwner
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
                moment_version.moment_version_key,
                moment.moment_key,
                moment_version.version_number,
                moment_version.moment_kind,
                moment_version.title,
                moment_version.occurred_on,
                moment_version.occurred_precision,
                moment_version.narrative,
                moment_version.why_it_matters,
                moment_version.saved_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.moment_versions AS moment_version
            JOIN dbo.moments AS moment
              ON moment.moment_id = moment_version.moment_id
            WHERE moment.owner_profile_id = @ProfileId
            ORDER BY moment.created_at_utc, moment.moment_key, moment_version.version_number;
        END;
    ');

    /* ============================================================
       READER 5: dbo.moment_sources (8 content columns; parent
       linkage via dbo.moments.moment_key, owner predicate on BOTH
       sides -- moment_sources carries its own owner_profile_id)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportMomentSourceForOwner
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
                moment_source.moment_source_key,
                moment.moment_key,
                moment_source.source_capture_key,
                moment_source.source_revision_key,
                moment_source.source_revision_number,
                moment_source.source_state,
                moment_source.source_deleted_at_utc,
                moment_source.created_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.moment_sources AS moment_source
            JOIN dbo.moments AS moment
              ON moment.moment_id = moment_source.moment_id
            WHERE moment_source.owner_profile_id = @ProfileId
              AND moment.owner_profile_id = @ProfileId
            ORDER BY moment_source.created_at_utc, moment_source.moment_source_key;
        END;
    ');

    /* ============================================================
       READER 6: dbo.moment_placements (8 content columns; parent
       linkage via dbo.moments.moment_key, owner predicate on BOTH
       sides -- moment_placements carries its own owner_profile_id.
       target_entity_id/dbo.slate_entities deliberately excluded, see
       header)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportMomentPlacementForOwner
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
                placement.placement_key,
                moment.moment_key,
                placement.moment_version_number,
                placement.placement_status,
                placement.created_at_utc,
                placement.reactivated_at_utc,
                placement.removed_at_utc,
                placement.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.moment_placements AS placement
            JOIN dbo.moments AS moment
              ON moment.moment_id = placement.moment_id
            WHERE placement.owner_profile_id = @ProfileId
              AND moment.owner_profile_id = @ProfileId
            ORDER BY placement.created_at_utc, placement.placement_key;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-004'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-004',
            N'Read-only owner-scoped account-export Capture/Moment readers (replacement package 2, 2026-08-29 topology): six @UserKey-only procedures over captures, capture_revisions, moments, moment_versions, moment_sources, and moment_placements, each with an exact text-truth allowlist, owner predicate, deterministic order, and trailing read-window columns. Media, hash, and target_entity_id/Slate linkage deliberately excluded.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-004"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
