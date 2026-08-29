/* ============================================================
   PS-SETTINGS-EXPORT-005 - account export Workshop / My Knowledge reader
   (replacement package 3 of the 2026-08-29 reader topology)

   Read-only, owner-scoped SQL reader procedures for EXACTLY the C0
   V1-matrix "Workshop / My Knowledge" row
   (docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
   C0_ACCOUNT_EXPORT_ARCHITECTURE.md), re-validated against the applied
   PS-WORKSHOP-001/PS-WORKSHOP-002 schema files at write time per C0's
   own caveat ("Included after schema revalidation -- allowlisted
   private knowledge/version records only; current schema, owner reads,
   and use-disclosure dependencies must be rechecked"): dbo.knowledge_items
   and dbo.knowledge_item_versions -- one procedure per table, two total.
   This migration creates ONLY procedures. It creates no table, no
   trigger, no index, and writes nothing anywhere except its own ledger
   row.

   THREE tables exist under PS-WORKSHOP-001, not two.
   dbo.knowledge_item_save_requests (PS-WORKSHOP-001's idempotency
   ledger for one-step Save) is DELIBERATELY EXCLUDED: it carries only
   an owner-scoped replay key and the resulting knowledge_item_id --
   no title, wording, status, or any other member-authored fact. It is
   machinery, not knowledge content, exactly the same class of decision
   this program already made for career_skill_links (PS-SETTINGS-EXPORT-003)
   and target_entity_id/dbo.slate_entities (PS-SETTINGS-EXPORT-004):
   recorded in services/account_export_domain_readers.py as its OWN
   named, excluded DOMAINS entry (never silently folded into
   "workshop_my_knowledge"), so a future reader of that dict never has
   to guess whether the omission was deliberate. This migration does
   not reference it anywhere and builds no reader for it.

   PS-WORKSHOP-002 added no table of its own -- only a new procedure
   (usp_ConfirmAuthoredKnowledgeBacklogForOwner) and a revision to
   usp_ArchiveKnowledgeItemForOwner's admission predicate. There is
   therefore no PS-WORKSHOP-002 "confirmation-machinery table" to
   exclude; the confirmation FACTS this migration exports
   (item_status, confirmed_version_number, confirmed_at_utc) are
   dbo.knowledge_items columns PS-WORKSHOP-001 itself created, in the
   same shape PS-SETTINGS-EXPORT-004 already exported for
   dbo.moments (status, confirmed_version_number, confirmed_at_utc).
   PS-WORKSHOP-003 (usp_ListKnowledgeItemVersionsForOwner) and
   PS-WORKSHOP-004 (edit-provenance retention in
   usp_UpdateKnowledgeItemForOwner) were re-read before writing this
   migration and confirmed to add ONLY procedures -- neither adds,
   renames, or drops a column or table on dbo.knowledge_items or
   dbo.knowledge_item_versions -- so the column/constraint enumeration
   below, read from PS-WORKSHOP-001_knowledge_items.sql and
   PS-WORKSHOP-002_knowledge_confirmation.sql, remains the accurate
   current schema; this migration does not require either of them and
   depends on neither's procedures. At the time of writing, no Workshop
   lane (PS-WORKSHOP-PROVENANCE-001, -EDGE-001, -VISIBILITY-001,
   -SURFACE-TRUTH-001, -USE-DISCLOSURE-001, -USE-DISCLOSURE-PRODUCTION-
   TRUTH-001, -EDIT-PROVENANCE-001, -FG-PRODUCTION-TRUTH-001, or
   -DELIVERY-CONTINUITY-001) is active in
   docs/governance/lane_claims/ -- every one of them is `"state":
   "closed"` -- so there is no live Workshop lane whose claimed
   surfaces this migration's allowlist reasoning could collide with;
   PS-OPPSLATE-USE-001 (the applied "use-disclosure" migration that
   tags Opportunity Slate evidence with a bare `evidence_kind =
   N'knowledge_item'` string) was also re-read and confirmed to hold no
   foreign key, joined column, or schema dependency on
   dbo.knowledge_items/dbo.knowledge_item_versions at all -- it is
   "deliberately NOT joined to dbo.knowledge_items" by its own header.

   Text truth only -- this package's defining boundary, identical in
   spirit to PS-SETTINGS-EXPORT-004's: every content hash, checksum,
   media/photo/voice/blob/file reference, transcript linkage, storage
   locator, and URL to stored media is excluded from every allowlist
   below, along with every internal integer id/surrogate, every
   created-by/approved-by/confirmed-by/archived-by user id, every
   row_version, and every soft-delete column. Neither
   dbo.knowledge_items nor dbo.knowledge_item_versions has a
   media/hash/transcript column of its own, and NEITHER TABLE HAS A
   deleted_at_utc COLUMN AT ALL -- dbo.knowledge_items' own
   usp_DeleteKnowledgeItemForOwner is a plain hard DELETE of the item
   and its versions (PS-WORKSHOP-001's own header: "W1 has no
   downstream use table... Delete is therefore a plain hard delete"),
   never a flag, so there is no soft-delete predicate to add to either
   reader below -- confirmed structurally by the paired verification
   script's own grep tripwire (neither procedure body may reference
   "deleted_at_utc" at all) and recorded here because it governs this
   package's field decisions, not because a row here needed a predicate
   it turned out to lack. dbo.knowledge_items' own archived_at_utc/
   archived_by_user_id are a REAL, undeleted item state (exactly like
   PS-SETTINGS-EXPORT-004's captures.status = 'archived' and
   moment_placements.removed_at_utc) -- an archived item is not
   filtered out, only its actor id is excluded from the output.

   Modeled directly on PS-SETTINGS-EXPORT-004_capture_moment_readers.sql
   (replacement package 2, applied at main 1f701263 after its gate
   passed on the first run): identical identity-resolution header,
   one-procedure-per-table split, the read window as two trailing
   columns on that single result set, and the "owner predicate on both
   sides of a parent join" defense in depth wherever the child table
   itself carries owner_profile_id.

   Every procedure:
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, no table
       name, no dynamic SQL built from any argument;
     - resolves identity internally, BYTE-IDENTICALLY across both,
       exactly like every prior package''s readers: @UserKey -> an
       ACTIVE dbo.app_users row -> its ACTIVE dbo.member_profiles row.
       An unresolved identity RETURNs before any SELECT (no result set
       at all) -- the caller-side adapter treats that as zero rows,
       never an error;
     - filters every row by the resolved owner profile, with the exact
       shape each table''s own schema supports rather than a single
       assumed pattern:
         * dbo.knowledge_items carries its own owner_profile_id, so its
           reader asserts item.owner_profile_id = @ProfileId directly
           (the same single-table shape as PS-SETTINGS-EXPORT-004''s
           captures/moments readers). It also asserts
           item.visibility = N''private'' explicitly, even though
           CK_knowledge_items_visibility hard-locks every row to that
           value today -- the identical "never trust the default"
           discipline usp_ListKnowledgeItemsForOwner and
           usp_GetKnowledgeItemForOwner (PS-WORKSHOP-001) already apply
           to this exact table, and PS-WORKSHOP-002''s own header calls
           out by name as the reason that discipline is safe to rely on;
         * dbo.knowledge_item_versions is DIFFERENT FROM every version-
           history table PS-SETTINGS-EXPORT-004 read
           (dbo.capture_revisions, dbo.moment_versions): unlike those
           two, it carries its OWN owner_profile_id column (required by
           FK_knowledge_item_versions_item''s composite foreign key,
           (knowledge_item_id, owner_profile_id) ->
           dbo.knowledge_items(knowledge_item_id, owner_profile_id)).
           This migration was written by deriving that fact from the
           schema, not assuming it -- so its reader uses the
           BOTH-SIDED owner predicate
           (version_record.owner_profile_id = @ProfileId AND
           item.owner_profile_id = @ProfileId), the same defense in
           depth PS-SETTINGS-EXPORT-004 applied to
           dbo.moment_sources/dbo.moment_placements, never the
           single-sided, parent-only shape that table''s sibling
           packages needed for capture_revisions/moment_versions;
     - replaces every internal integer id with the row''s own opaque
       *_key uniqueidentifier where the table has one, plus the
       parent''s opaque knowledge_item_key for intra-export linkage.
       dbo.knowledge_item_versions has NO opaque key column of its own
       (unlike dbo.capture_revisions.revision_key or
       dbo.moment_versions.moment_version_key) -- its own identifying
       tuple is (knowledge_item_id, version_number), already unique per
       UQ_knowledge_item_versions_number, so its reader exports the
       joined parent''s knowledge_item_key plus its own version_number
       as that tuple''s exported form, and manufactures no surrogate
       key that does not exist in the schema;
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *), matching this package''s lane-claim contract exactly;
     - orders its result set deterministically: dbo.knowledge_items (no
       parent, no per-parent sequence column) orders by its own
       created_at_utc then its own opaque key -- the same "own
       timestamp, own key" idiom PS-SETTINGS-EXPORT-004 used for
       dbo.captures/dbo.moments, and deliberately NOT
       usp_ListKnowledgeItemsForOwner''s own updated_at_utc DESC list
       order (that is the live UI''s "recently edited first" order;
       this export uses the same stable creation-chronological order
       every other top-level reader in this program uses).
       dbo.knowledge_item_versions orders by the PARENT''s
       created_at_utc then the parent''s opaque key, then the child''s
       own version_number -- version_number is only unique WITHIN one
       item (UQ_knowledge_item_versions_number UNIQUE (knowledge_item_id,
       version_number)), so a flat reader over every owner''s versions
       must group by the parent first, exactly the
       capture_revisions/moment_versions idiom;
     - returns a read window (SYSUTCDATETIME() captured at the top of
       the procedure as @ReadStartedAtUtc, and again inline in the
       content SELECT as read_ended_at_utc) as two TRAILING COLUMNS on
       the single content result set -- identical mechanism and
       rationale to every prior package in this program (OUTPUT
       parameters would violate the pinned "@UserKey-only signature"
       test; a second, differently-shaped result set would make
       INSERT ... EXEC unsafe per Microsoft''s own documented
       requirement that every result set, not merely the first, be
       column-compatible with the capturing table);
     - contains NO transaction control of any kind -- no BEGIN
       TRANSACTION, COMMIT, ROLLBACK, or TRY/CATCH, and no nested EXEC or
       dynamic SQL of its own. Every procedure here is a single
       read-only SELECT, so it is safe to call with a bare EXEC and can
       never trip T-SQL''s "Cannot use the ROLLBACK statement within an
       INSERT-EXEC statement" refusal.

   Requires PS-WORKSHOP-001 and PS-WORKSHOP-002 -- both migrations this
   package''s own guards below check the ledger for, matching the
   lane claim''s own framing of "the applied PS-WORKSHOP-001/002
   knowledge tables" as the schema baseline this package targets, even
   though the columns/constraints read below are all PS-WORKSHOP-001''s
   own (PS-WORKSHOP-002 revised a procedure, not a column). PS-AUTH-001
   is named in the registry''s own requires list too, for the paired
   verification script''s usp_UpsertAppUserFromAuth dependency -- named
   here from the start, exactly the omission PS-SETTINGS-EXPORT-003''s
   own gate round had to correct after the fact and every later package
   in this program has since avoided repeating. This migration''s own
   guards do not check for PS-AUTH-001 directly: every column they
   touch on dbo.app_users/dbo.member_profiles already exists as of
   PS-PLAT-000/PS-PLAT-002, predating PS-AUTH-001, identically to every
   prior package''s recorded reasoning for the same omission.

   Grant model: identical to PS-SETTINGS-EXPORT-001/003/004. The
   governed apply identity holds db_ddladmin only and cannot GRANT
   EXECUTE; no GRANT, CREATE ROLE, CREATE USER, or sp_addrolemember
   statement appears anywhere in this file. The intended production
   grant -- EXECUTE on these two procedures for the existing web-app
   principal role -- is a separate, later, administrator-run authority
   operation, not created here and not authorized by a repository merge
   of this file.

   THROW range: 58400-58499 (this migration; the rollback file continues
   within the same block at 58408). Verified clear of every sibling
   migration/rollback/verification file's range: the highest prior THROW
   number anywhere under SQL FIles/ is 58362
   (PS-SETTINGS-EXPORT-004_capture_moment_reader_isolation_verify.sql).

   No production apply is authorized by this file. No container,
   worker, schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-005_workshop_reader_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-005_workshop_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58400, 'PS-SETTINGS-EXPORT-005 requires the migration ledger.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-WORKSHOP-001')
        THROW 58401, 'PS-WORKSHOP-001 must be applied before PS-SETTINGS-EXPORT-005.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-WORKSHOP-002')
        THROW 58402, 'PS-WORKSHOP-002 must be applied before PS-SETTINGS-EXPORT-005.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 58403, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 58404, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.knowledge_items', N'U') IS NULL
       OR OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NULL
        THROW 58405, 'The Workshop knowledge schema is missing.', 1;

    IF COL_LENGTH(N'dbo.knowledge_items', N'knowledge_item_key') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'item_status') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'classification') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'visibility') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'current_version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'confirmed_version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'confirmed_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'archived_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'updated_at_utc') IS NULL
        THROW 58406, 'The knowledge_items columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.knowledge_item_versions', N'knowledge_item_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'title') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'approved_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'original_member_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'body_format') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'authored_via') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'saved_at_utc') IS NULL
        THROW 58407, 'The knowledge_item_versions columns are incompatible.', 1;

    /* ============================================================
       READER 1: dbo.knowledge_items (10 content columns)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportKnowledgeItemForOwner
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
                item.knowledge_item_key,
                item.item_status,
                item.classification,
                item.visibility,
                item.current_version_number,
                item.confirmed_version_number,
                item.confirmed_at_utc,
                item.archived_at_utc,
                item.created_at_utc,
                item.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.knowledge_items AS item
            WHERE item.owner_profile_id = @ProfileId
              AND item.visibility = N''private''
            ORDER BY item.created_at_utc, item.knowledge_item_key;
        END;
    ');

    /* ============================================================
       READER 2: dbo.knowledge_item_versions (8 content columns; parent
       linkage via dbo.knowledge_items.knowledge_item_key, owner
       predicate on BOTH sides -- knowledge_item_versions carries its
       own owner_profile_id, unlike dbo.capture_revisions/
       dbo.moment_versions in the sibling packages. No own opaque key
       column exists on this table; (knowledge_item_key, version_number)
       is its exported identifying tuple.)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportKnowledgeItemVersionForOwner
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
                item.knowledge_item_key,
                version_record.version_number,
                version_record.title,
                version_record.approved_wording,
                version_record.original_member_wording,
                version_record.body_format,
                version_record.authored_via,
                version_record.saved_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.knowledge_item_versions AS version_record
            JOIN dbo.knowledge_items AS item
              ON item.knowledge_item_id = version_record.knowledge_item_id
            WHERE version_record.owner_profile_id = @ProfileId
              AND item.owner_profile_id = @ProfileId
              AND item.visibility = N''private''
            ORDER BY item.created_at_utc, item.knowledge_item_key, version_record.version_number;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-005'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-005',
            N'Read-only owner-scoped account-export Workshop/My Knowledge readers (replacement package 3, 2026-08-29 topology): two @UserKey-only procedures over knowledge_items and knowledge_item_versions, each with an exact text-truth allowlist, owner predicate (both-sided on the versions reader), deterministic order, and trailing read-window columns. knowledge_item_save_requests deliberately excluded (idempotency machinery, not content).',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-005"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
