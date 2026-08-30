/* ============================================================
   PS-SETTINGS-EXPORT-009 - account export evidence-rule reader
   (career_skill_links)

   Read-only, owner-scoped SQL reader procedure executing the owner's
   accepted 2026-08-30 Papers 4-7 rulings: THE SAFE-REFERENCES-ONLY
   EVIDENCE RULE. Titles, types, statuses, and dates may export;
   storage locators, container names, object keys, URLs, hashes/
   digests, and verifier identity may NEVER export, from this table or
   any evidence-adjacent table anywhere in this reader program, until a
   dedicated future package performs the field-by-field review that
   rule requires. This migration adopts the rule and applies it now to
   the ONE reader it unblocks: dbo.career_skill_links, excluded by
   PS-SETTINGS-EXPORT-003's own core-readers package solely because
   this rule was undecided at the time ("Its rows reference
   evidence_item_id, whose disclosure rules are undecided; it is
   deferred to a future evidence-decision package"). This migration
   creates ONLY one procedure. It creates no table, no trigger, no
   index, and writes nothing anywhere except its own ledger row.

   THE READER: dbo.career_skill_links links a member's own career skill
   (dbo.career_skills) to a source that demonstrates it
   (source_entity_id, a dbo.slate_entities reference) and, optionally,
   to a piece of evidence (evidence_item_id, a dbo.evidence_items
   reference). This migration exports the member's own link facts --
   relationship_type, approval_status, strength_rank, created_at_utc --
   plus the skill_id reference resolved to career_skills' own skill_key
   (career_skills is PS-SETTINGS-EXPORT-003's own included
   "living_resume" domain; this mirrors that package's own
   chapter_id -> chapter_key intra-export-linkage idiom exactly, and
   never re-selects skill_name/skill_summary/etc., which the
   career_skill reader already exports -- no double export of skill
   content).

   source_entity_id IS EXCLUDED OUTRIGHT, NEVER RESOLVED. dbo.
   slate_entities is the polymorphic identity table underneath EVERY
   Living Resume row (career_chapters/achievements/skills/timeline_events
   all key an entity_id off it) and this whole reader program has never
   once resolved an entity_id or a *_entity_id reference to anything,
   anywhere -- PS-SETTINGS-EXPORT-003's own ten readers forbid
   "chapter_id, entity_id, any *_id surrogate column" outright, and
   PS-SETTINGS-EXPORT-004 drew the identical boundary for
   dbo.moment_placements.target_entity_id ("dbo.slate_entities is not
   one of PS-SETTINGS-EXPORT-004's six claimed tables"). This
   migration's own reader never joins dbo.slate_entities and never
   selects source_entity_id in any form, opaque or otherwise --
   consistent with that program-wide boundary, not a new one.

   evidence_item_id IS EXCLUDED OUTRIGHT; A DERIVED evidence_linked
   FLAG IS DISCLOSED INSTEAD. dbo.evidence_items is NOT one of this
   migration's claimed tables (this migration creates no reader that
   selects from it, and never joins it), so resolving evidence_item_id
   to any evidence_items field -- even an opaque key -- is out of
   scope by construction, the same reasoning that already excludes
   source_entity_id above. The safe-references-only rule's forbidden
   list (locators/keys/URLs/hashes/verifier identity) is absolute, so
   even the raw evidence_item_id surrogate is never selected. What IS
   disclosed is a single derived bit, computed entirely from this
   migration's own claimed column (no join, no evidence_items read):
   evidence_linked = 1 when the member's own link row names an
   evidence item, 0 when it does not. This is a member-authored fact
   about the member's OWN row (did they back this skill claim with
   evidence when they created the link), not a locator, key, hash, URL,
   or any fact about evidence_items' content -- squarely within the
   rule's safe territory (a "status"-shaped fact), not its forbidden
   one.

   Ownership: dbo.career_skill_links carries its own owner_profile_id
   column directly (NOT NULL, no inheritance through a parent row
   required) -- confirmed by reading PS-PLAT-006_living_resume_domain.sql's
   own DDL. The joined dbo.career_skills row is independently
   owner-predicated too (defense in depth beyond the composite
   FK_career_skill_links_skill_owner FOREIGN KEY (skill_id,
   owner_profile_id) that already ties them to the same owner), the
   identical "predicate every joined table" discipline
   PS-SETTINGS-EXPORT-003 already applies to its own chapter-joined
   extension readers.

   PRACTICALLY EMPTY TODAY, HANDLED AS AN HONEST EMPTY. dbo.
   career_skill_links' evidence_item_id FK target (dbo.evidence_items)
   is a dormant table with no writer anywhere in this codebase; most
   members will legitimately export zero rows from this reader today.
   This is disclosed, not hidden: the reader still exists so the
   export's own manifest can truthfully report this domain as
   included-but-usually-empty rather than silently absent, and the
   adapter's own offline tests model the resolved-owner-with-an-
   empty-table cursor shape precisely (a real column description, zero
   rows) -- never the description-less shape an unresolved identity
   produces, which is a different case entirely.

   Soft-delete: dbo.career_skill_links carries NEITHER a deleted_at_utc
   column NOR a row_version column of its own (confirmed by reading its
   own DDL) -- there is nothing on this table itself to filter. The
   joined dbo.career_skills row DOES carry deleted_at_utc, and this
   reader filters skill.deleted_at_utc IS NULL: if the referenced skill
   is soft-deleted, its link must not surface through this back door,
   the identical "extension content must not surface if its parent was
   soft-deleted" widening PS-SETTINGS-EXPORT-003's own header already
   documents for its own chapter-joined extension readers.

   Every procedure:
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, table name, or
       dynamic SQL built from any argument;
     - resolves identity with the byte-identical header every reader in
       this program shares: @UserKey -> an ACTIVE dbo.app_users row ->
       its ACTIVE dbo.member_profiles row. An unresolved identity
       RETURNs before any SELECT -- no result set at all;
     - filters its claimed table by link.owner_profile_id = @ProfileId
       AND the joined skill.owner_profile_id = @ProfileId (career
       tables always key by profile, never by the internal user id);
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *) -- no skill_link_id, owner_profile_id, skill_id,
       source_entity_id, evidence_item_id, or created_by_user_id;
     - orders its result set deterministically: link.created_at_utc
       then link.skill_link_id (career_skill_links has no opaque *_key
       column and no display_order of its own, so the trailing,
       excluded-from-output internal id is the tiebreak -- the same
       "order by an excluded internal id" idiom
       usp_ReadAccountExportAccountForOwner and
       usp_ReadAccountExportConnectionPreferenceForOwner already use);
     - returns the read window as two TRAILING COLUMNS on the single
       content result set, identical mechanism to every prior package;
     - contains NO transaction control of any kind, no write, and no
       nested EXEC/dynamic SQL.

   THE OTHER FOUR RULINGS THIS PACKAGE RECORDS. services/
   account_export_domain_readers.py's own DOMAINS reason strings for
   ai_proposals, own_publication_versions/profile_publication_foundation,
   community_authored_content, and file_evidence_metadata are updated in
   the SAME commit as this migration to record the owner's accepted
   2026-08-30 rulings durably (ai_proposals closed -- nothing additional
   to export today; publication deferred with the future package
   shipping its own reader; Community honestly omitted from v1 with a
   future own-words-only package queued; the safe-references-only rule
   now binding whichever package first builds a file/evidence reader).
   None of those four domains has a reader in this migration; see that
   module's own docstring and DOMAINS dict for the exact updated
   reasons.

   Requires PS-PLAT-006 (creates dbo.career_skill_links and
   dbo.career_skills) directly. PS-AUTH-001 is a registry-level
   requirement only (its usp_UpsertAppUserFromAuth is the paired
   verification script's own owner-provisioning dependency, the same
   reasoning every prior package in this program has recorded for the
   identical omission from this migration body's own guard checks).
   PS-PLAT-003 (creates dbo.evidence_items) is ALREADY a transitive
   ancestor of PS-PLAT-006 (PS-PLAT-006 -> 005 -> 004 -> 003) and is
   therefore not required for apply ORDERING, but is named directly and
   conservatively in the registry's own requires list because this
   migration's paired verification script inserts real rows into
   dbo.evidence_items to satisfy career_skill_links' own FK -- the same
   "a registry-level requirement can cover the verification script's
   own direct dependency, not merely the migration body's guard checks"
   reasoning already used for PS-AUTH-001 program-wide.

   Grant model: identical to every prior package in this program. The
   governed apply identity holds db_ddladmin only and cannot GRANT
   EXECUTE; no GRANT, CREATE ROLE, CREATE USER, or sp_addrolemember
   statement appears anywhere in this file. The intended production
   grant -- EXECUTE on this procedure for the existing web-app principal
   role -- is a separate, later, administrator-run authority operation,
   not created here and not authorized by a repository merge of this
   file. Design only; nothing applied.

   THROW range: 59200-59299 (this migration; forward uses 59200-59206,
   rollback continues at 59207). Verified clear of every sibling
   migration/rollback/verification file's range: a repository-wide scan
   of every .sql file under SQL FIles/ found the highest prior THROW
   number anywhere to be 59152
   (PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql).

   No production apply is authorized by this file. No container,
   worker, schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-009_evidence_rule_reader_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-009_evidence_rule_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 59200, 'PS-SETTINGS-EXPORT-009 requires the migration ledger.', 1;

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-PLAT-006'
    )
        THROW 59201, 'PS-PLAT-006 must be applied before PS-SETTINGS-EXPORT-009.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 59202, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 59203, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.career_skills', N'U') IS NULL
       OR OBJECT_ID(N'dbo.career_skill_links', N'U') IS NULL
        THROW 59204, 'The PeerSlate career skill or skill-link schema is missing.', 1;

    IF COL_LENGTH(N'dbo.career_skills', N'skill_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'skill_key') IS NULL
       OR COL_LENGTH(N'dbo.career_skills', N'deleted_at_utc') IS NULL
        THROW 59205, 'The career_skills columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.career_skill_links', N'skill_link_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'skill_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'evidence_item_id') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'relationship_type') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'approval_status') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'strength_rank') IS NULL
       OR COL_LENGTH(N'dbo.career_skill_links', N'created_at_utc') IS NULL
        THROW 59206, 'The career_skill_links columns are incompatible.', 1;

    /* ============================================================
       READER: dbo.career_skill_links (4 member-authored content
       columns plus the resolved skill_key linkage and the derived
       evidence_linked flag; source_entity_id and evidence_item_id are
       excluded outright -- see this file's own header)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCareerSkillLinkForOwner
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
                link.relationship_type,
                link.approval_status,
                link.strength_rank,
                CAST
                (
                    CASE WHEN link.evidence_item_id IS NOT NULL THEN 1 ELSE 0
                    END AS bit
                ) AS evidence_linked,
                link.created_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.career_skill_links AS link
            JOIN dbo.career_skills AS skill ON skill.skill_id = link.skill_id
            WHERE link.owner_profile_id = @ProfileId
              AND skill.owner_profile_id = @ProfileId
              AND skill.deleted_at_utc IS NULL
            ORDER BY link.created_at_utc, link.skill_link_id;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-009'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-009',
            N'Read-only owner-scoped account-export reader for dbo.career_skill_links, applying the safe-references-only evidence rule (titles/types/statuses/dates; never locators, object keys, URLs, hashes, or verifier identity): one @UserKey-only procedure resolving skill_id to career_skills'' skill_key and disclosing a derived evidence_linked flag; source_entity_id and evidence_item_id are excluded outright. No evidence_items content is read.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-009"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
