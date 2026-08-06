/* ============================================================
   PS-WORKSHOP-002 - gated in-place knowledge backlog confirmation (leg 9)

   Owner ruling (Pete, 2026-08-06, recorded in
   docs/governance/CURRENT_LANES.json leg 9): "anything in your knowledge
   database is confirmed. You put it there... It's when you have new stuff
   that gets confirmed, not existing stuff." Leg 8 (main 75faf4b2) already
   made every NEW member-authored Workshop save confirm at save time. This
   migration is the standing rule applied ONCE to the pre-existing backlog:
   every existing member-authored dbo.knowledge_items row this owner still
   carries at item_status = N'unfinished' becomes N'confirmed', with ZERO
   member action and ZERO alteration of the member's canonical content.

   REFUSED PRIOR ATTEMPT. An earlier app-side design was refused by
   independent review for three defects this migration's shape exists to
   make structurally impossible, not merely avoid by convention:
     1. It reused usp_UpdateKnowledgeItemForOwner's new-version INSERT path,
        which rewrites authored_via to N'typed' and original_member_wording
        to the approved wording. The member's own provenance and verbatim
        original are canonical truth (architecture doc 17 section 5.2) and
        may never be rewritten by a reconciliation the member did not ask
        for.
     2. It reset updated_at_utc. That column is the SOLE ordering of both
        usp_ListOpportunityEvidenceForOwner's TOP (24) AI evidence window
        (PS-OPPSLATE-002) and this migration's own
        usp_ListKnowledgeItemsForOwner's TOP (200) library read
        (PS-WORKSHOP-001). Resetting it on every backlog row would silently
        reorder both to put the entire backlog ahead of a member's
        genuinely recent work.
     3. It wrote a member-attributed audit/version row for a page the
        member merely opened, misrepresenting a standing-rule
        reconciliation as a member edit in the permanent audit trail.

   THE FIX, structurally:
     (a) dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner is new and does
         exactly one thing: UPDATE item_status, confirmed_version_number,
         confirmed_by_user_id, confirmed_at_utc on rows already
         item_status = N'unfinished' AND archived_at_utc IS NULL for this
         owner. Nothing else is in its SET list -- updated_at_utc is
         syntactically absent, so it is not merely left equal by
         coincidence, it cannot be written by this statement at all. It
         inserts nothing into dbo.knowledge_item_versions, so
         authored_via, original_member_wording, title, and approved_wording
         are untouched everywhere in this file. It writes one audit row per
         confirmed item under the DISTINCT action name
         N'knowledge_item.backlog_confirmed' (never
         N'knowledge_item.updated'), so the trail reads honestly as the
         standing-rule reconciliation it is, never as a member edit.
     (b) item_status = N'unfinished' in both the candidate read and the
         UPDATE's own WHERE clause structurally excludes N'suggested' (an
         unaccepted AI proposal) and N'archived'; the redundant
         archived_at_utc IS NULL predicate is defense in depth. Neither
         value can reach this procedure's SET list under any input.

   CARRIED REVIEW FINDING, CLOSED HERE. Before this migration,
   usp_ArchiveKnowledgeItemForOwner (PS-WORKSHOP-001) accepted any
   item_status <> N'archived', including N'suggested', and
   usp_RestoreKnowledgeItemForOwner returns a never-confirmed archived row
   as N'unfinished' (by design, so a genuinely unfinished member draft
   restores to unfinished rather than jumping to suggested). The moment an
   auto-confirmation procedure exists, that combination is a laundering
   path: archive an unaccepted N'suggested' draft, restore it, and it comes
   back N'unfinished' -- indistinguishable from a member's own draft, and
   the next backlog sweep (or a future one, since new N'unfinished' rows
   from Spark-style suggestions are not ruled out later) would auto-confirm
   an AI proposal the member never reviewed.

   FIX CHOSEN: usp_ArchiveKnowledgeItemForOwner is revised, in this
   migration, to accept only item_status IN (N'unfinished', N'confirmed').
   A N'suggested' row can therefore never become N'archived', so it can
   never reach usp_RestoreKnowledgeItemForOwner's status-recovery branch,
   so it can never come back as N'unfinished', so
   usp_ConfirmAuthoredKnowledgeBacklogForOwner can never touch it -- closed
   at the earliest possible point, structurally, rather than patched at
   every later consumer. usp_RestoreKnowledgeItemForOwner is NOT changed:
   once archive refuses N'suggested', every archived row restore ever sees
   originated as N'unfinished' or N'confirmed', so its existing
   confirmed-vs-unfinished recovery logic is already exactly correct for
   every case it can still reach. The alternative this migration's task
   brief also authorized -- an additive shadow column on
   usp_RestoreKnowledgeItemForOwner's side preserving pre-archive status --
   was not needed: it would add a schema column and a second code path to
   solve a problem the one-line archive predicate already closes
   completely, and no production code path writes item_status = N'suggested'
   today (grep the Python modules under services/; the checkpoint dev fixture and
   workshop_demo_library are the only source of that string, and neither
   calls a real procedure), so the change costs nothing operationally and
   forecloses the laundering path before any AI-suggestion write path ships.
   A restored member-authored N'unfinished' item (never N'suggested') IS
   correctly eligible for the next backlog sweep under the owner's own
   rule -- it is still something the member authored and put there.

   TWO NAMED CARRIED RISKS (Opus review, 2026-08-06). Independent review
   affirmed the design and this fix, but declined to record the finding as
   fully closed without naming what remains open:

   (a) THE ARCHIVE REFUSAL IS PROCEDURAL, NOT STRUCTURAL. It is one WHERE
       predicate inside one procedure, not a schema-level guarantee (no
       CHECK constraint makes a N'suggested' row impossible to archive; the
       procedure simply declines to select one). A future migration that
       ships a real suggestion queue MUST re-verify this exact boundary
       before it ships, not assume this comment still describes the live
       procedure. It must also NOT let a "dismiss suggestion" feature reuse
       this Archive action: workshop_routes.py's real-item detail view
       (_real_detail_view, "archive_url") offers Archive on every detail
       row today regardless of status, so a future N'suggested' row would
       show an Archive control that this procedure now silently refuses
       (outcome 'changed') rather than a working dismiss action --
       unwired today (no live path renders a N'suggested' detail row), but
       the affordance is already present and must not be repurposed as
       "dismiss" without its own review.
   (b) A PS-WORKSHOP-002 ROLLBACK RE-OPENS THIS BOUNDARY. Rolling back this
       migration restores usp_ArchiveKnowledgeItemForOwner to its exact
       PS-WORKSHOP-001 predicate (item_status <> N'archived', which again
       admits N'suggested') and drops
       usp_ConfirmAuthoredKnowledgeBacklogForOwner outright -- while, by
       this same header's own design decision, every row the backlog
       procedure already confirmed LEGITIMATELY remains confirmed (see the
       rollback file's own header). Rollback does not itself launder
       anything, because the confirming procedure is gone with it, but the
       two facts together mean the database can be in a state where the
       archive predicate no longer refuses N'suggested' AND rows exist that
       were confirmed by a mechanism the schema currently lacks. Any later
       migration that re-adds an auto-confirmation procedure after a
       PS-WORKSHOP-002 rollback must re-close the archive boundary itself;
       it must not assume this migration's fix is still in effect.

   Immutable follow-on to the production-ledgered PS-WORKSHOP-001 baseline.
   Purely additive to the object inventory (one new procedure); revises
   exactly one existing procedure (usp_ArchiveKnowledgeItemForOwner) with
   the definition-hash discipline PS-OPPSLATE-002 established for its own
   revised procedures. A missing, older, or drifted PS-WORKSHOP-001
   baseline -- including a hand-edited protected procedure whose live
   definition no longer matches its own gated hash -- fails before the
   first DDL statement.

   ORDERING (state explicitly, per the task brief): the degrade-safe
   application wiring (services/knowledge_service.py, workshop_routes.py,
   opportunity_slate_routes.py) has already shipped and remains dormant.
   This migration, rollback, and verifier passed the owner's disposable-
   database gate before their proof branch merges. The production apply is
   then queued on that exact merged SHA through the separately governed
   schema path. Until that apply completes, the application wiring's own
   DatabaseServiceError handling (including "procedure does not exist yet")
   degrades to skip-not-fail, so the deployed wiring changes no live behavior.

   Rollback: PS-WORKSHOP-002_knowledge_confirmation_rollback.sql
   Verification: ../../Verification/PS-WORKSHOP-002_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53300, 'PS-WORKSHOP-002 requires the migration ledger.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-WORKSHOP-001')
        THROW 53301, 'PS-WORKSHOP-001 must be applied before PS-WORKSHOP-002.', 1;

    /* Missing baseline: every W1 table and procedure must exist. */
    DECLARE @RequiredBaselineObjects TABLE
        (object_name nvarchar(300) NOT NULL, object_type char(1) NOT NULL);
    INSERT @RequiredBaselineObjects (object_name, object_type)
    VALUES
        (N'dbo.knowledge_items', N'U'),
        (N'dbo.knowledge_item_versions', N'U'),
        (N'dbo.knowledge_item_save_requests', N'U'),
        (N'dbo.usp_ListKnowledgeItemsForOwner', N'P'),
        (N'dbo.usp_GetKnowledgeItemForOwner', N'P'),
        (N'dbo.usp_SaveKnowledgeItemForOwner', N'P'),
        (N'dbo.usp_UpdateKnowledgeItemForOwner', N'P'),
        (N'dbo.usp_ArchiveKnowledgeItemForOwner', N'P'),
        (N'dbo.usp_RestoreKnowledgeItemForOwner', N'P'),
        (N'dbo.usp_DeleteKnowledgeItemForOwner', N'P');
    IF EXISTS (SELECT 1 FROM @RequiredBaselineObjects
               WHERE OBJECT_ID(object_name, object_type) IS NULL)
        THROW 53302, 'PS-WORKSHOP-001 does not match the required knowledge-item object baseline.', 1;

    /* Older/incompatible baseline: the exact columns this migration reads
       and writes must exist, mirroring PS-WORKSHOP-001's own COL_LENGTH
       compatibility guard. */
    IF COL_LENGTH(N'dbo.knowledge_items', N'item_status') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'current_version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'confirmed_version_number') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'confirmed_by_user_id') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'confirmed_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'archived_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'updated_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_items', N'created_at_utc') IS NULL
        THROW 53303, 'Existing Knowledge tables are incompatible with the backlog confirmation.', 1;

    /* Older/incompatible baseline: the exact CHECK constraints this
       migration's correctness argument depends on must still carry their
       original names. */
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
                   WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_items')
                     AND name = N'CK_knowledge_items_confirmation_state')
       OR NOT EXISTS (SELECT 1 FROM sys.check_constraints
                      WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_items')
                        AND name = N'CK_knowledge_items_archive_pair')
       OR NOT EXISTS (SELECT 1 FROM sys.check_constraints
                      WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_items')
                        AND name = N'CK_knowledge_items_status')
       -- The candidate read and the UPDATE below both assert
       -- item.visibility = N'private' explicitly rather than relying on
       -- every row already being hard-locked to it; this is the guard that
       -- makes trusting that omission-proof predicate safe -- if
       -- CK_knowledge_items_visibility is ever missing or renamed, a
       -- second, non-private visibility value could exist undetected.
       OR NOT EXISTS (SELECT 1 FROM sys.check_constraints
                      WHERE parent_object_id = OBJECT_ID(N'dbo.knowledge_items')
                        AND name = N'CK_knowledge_items_visibility')
        THROW 53304, 'PS-WORKSHOP-001''s knowledge_items constraint baseline is missing or renamed.', 1;

    /* Drifted baseline. The SIX W1 procedures this migration does not
       revise must still match the executable-body hash PS-WORKSHOP-001
       recorded on each at gate time -- this migration's whole safety
       argument rests on them still enforcing the invariants PS-WORKSHOP-001
       proved (the confirmation-state CHECK, the archive/restore state
       machine), untouched. An ungoverned hand-edit to any of them must
       refuse rather than be silently trusted.

       usp_ArchiveKnowledgeItemForOwner is deliberately EXCLUDED from this
       set, not merely forgotten: it is the one procedure this migration
       itself revises a few statements below. Checking its CURRENT
       definition against the W1 hash here would pass on a genuine first
       apply, but the governed gate proves every migration idempotent by
       running the forward script TWICE against the same database
       (scripts/govern_sql_migrations.py `gate`). After the first apply
       this procedure's live definition is legitimately the REVISED body,
       which no longer matches the W1 hash -- that is success, not drift,
       and including it here would make the second apply THROW on its own
       correct output. Its own drift protection is the
       PS_WORKSHOP_002_DEFINITION_HASH fingerprint this migration stamps on
       it below, checked by this migration's own rollback. */
    DECLARE @BaselineHashPropertyName sysname = N'PS_WORKSHOP_001_DEFINITION_HASH';
    DECLARE @BaselineProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @BaselineProcedures (procedure_name)
    VALUES
        (N'usp_ListKnowledgeItemsForOwner'),
        (N'usp_GetKnowledgeItemForOwner'),
        (N'usp_SaveKnowledgeItemForOwner'),
        (N'usp_UpdateKnowledgeItemForOwner'),
        (N'usp_RestoreKnowledgeItemForOwner'),
        (N'usp_DeleteKnowledgeItemForOwner');
    IF EXISTS
    (
        SELECT 1 FROM @BaselineProcedures AS baseline_procedure
        LEFT JOIN sys.extended_properties AS property
          ON property.class = 1
         AND property.major_id = OBJECT_ID(N'dbo.' + baseline_procedure.procedure_name, N'P')
         AND property.minor_id = 0
         AND property.name = @BaselineHashPropertyName
        WHERE property.major_id IS NULL
           OR CONVERT(nvarchar(64), property.value) <> CONVERT(nvarchar(64),
              HASHBYTES('SHA2_256',
                  OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + baseline_procedure.procedure_name, N'P'))), 2)
    )
        THROW 53305, 'PS-WORKSHOP-001''s procedures have drifted from their gated baseline; refusing to build the backlog confirmation on an unverified foundation.', 1;

    /* ============================================================
       NEW PROCEDURE: the bounded, in-place backlog confirmation.
       ============================================================ */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ConfirmAuthoredKnowledgeBacklogForOwner
            @UserKey nvarchar(300),
            /* Bounds one call to a deterministic, oldest-first slice of
               this owner''s standing backlog -- the same 200-row size as
               usp_ListKnowledgeItemsForOwner''s own TOP (200) read window,
               so one call is enough to clear everything the library page
               can ever show at once. A caller does not need to loop under
               ordinary use: leg 8''s save-time confirmation rule means no
               NEW N''unfinished'' row is ever created going forward, so
               each owner has at most one finite backlog to sweep, ever. */
            @MaxItems int = 200
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @MaxItems IS NULL OR @MaxItems < 1 SET @MaxItems = 200;
            IF @MaxItems > 200 SET @MaxItems = 200;

            IF @UserKey IS NULL
            BEGIN
                SELECT CAST(0 AS int) AS confirmed_count, CAST(0 AS int) AS remaining_count;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT
                @ProfileId = profile.profile_id,
                @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT CAST(0 AS int) AS confirmed_count, CAST(0 AS int) AS remaining_count;
                RETURN;
            END;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @Now datetime2(7) = SYSUTCDATETIME();
                -- Declared here, WITHOUT an initializer, and left untouched
                -- by any statement between the UPDATE below and its own
                -- @@ROWCOUNT capture. DECLARE ... = <value> executes as an
                -- assignment in its own right and resets @@ROWCOUNT, so a
                -- DECLARE-with-initializer placed between the UPDATE and the
                -- capture would silently clobber the UPDATE''s row count
                -- with whatever the DECLARE itself reports -- the repo''s
                -- own idiom (PS-OPPSLATE-001''s and PS-OPPSLATE-002''s
                -- @DeletedVersionCount / @PurgedVersionCount) always
                -- declares the counter first and assigns @@ROWCOUNT as the
                -- very next statement after the row-affecting one.
                DECLARE @ConfirmedCount int;
                DECLARE @Candidates TABLE
                (
                    knowledge_item_id bigint NOT NULL PRIMARY KEY,
                    knowledge_item_key uniqueidentifier NOT NULL,
                    confirmed_version_number int NOT NULL
                );

                /* The bounded, deterministic candidate set this call will
                   confirm, oldest-authored first. UPDLOCK+HOLDLOCK holds
                   the range so two concurrent calls for the same owner
                   (two tabs, or this call racing itself) cannot select
                   overlapping rows. Structurally impossible to select a
                   N''suggested'' or archived row: item_status = N''unfinished''
                   already excludes both (an archived item''s item_status is
                   always N''archived'', never N''unfinished'', by
                   CK_knowledge_items_archive_pair), and
                   archived_at_utc IS NULL is asserted again as defense in
                   depth against a future change to that invariant.
                   item.visibility = N''private'' is asserted too, even
                   though CK_knowledge_items_visibility hard-locks every row
                   to N''private'' today (checked in this migration''s own
                   baseline guard above) -- the same explicit,
                   never-trust-the-default discipline
                   usp_ListKnowledgeItemsForOwner and
                   usp_GetKnowledgeItemForOwner already apply to this exact
                   table. */
                INSERT @Candidates (knowledge_item_id, knowledge_item_key, confirmed_version_number)
                SELECT TOP (@MaxItems)
                    item.knowledge_item_id,
                    item.knowledge_item_key,
                    item.current_version_number
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.visibility = N''private''
                  AND item.item_status = N''unfinished''
                  AND item.archived_at_utc IS NULL
                ORDER BY item.created_at_utc ASC, item.knowledge_item_id ASC;

                /* The mutation. Every predicate re-asserts the same
                   scope the candidate read used, so this UPDATE cannot
                   touch a suggested, archived, or non-private row even if
                   @Candidates were ever populated differently -- it is
                   impossible by construction, not only by the read that
                   built the candidate set. Exactly four columns change.
                   updated_at_utc is syntactically absent from this SET
                   list, so it cannot be written here under any input, and
                   no knowledge_item_versions row is inserted or updated by
                   this procedure anywhere -- title, approved_wording,
                   original_member_wording, and authored_via are therefore
                   untouched by construction, not merely left equal. */
                UPDATE item
                SET item.item_status = N''confirmed'',
                    item.confirmed_version_number = item.current_version_number,
                    item.confirmed_by_user_id = @UserId,
                    item.confirmed_at_utc = @Now
                FROM dbo.knowledge_items AS item
                JOIN @Candidates AS candidate
                  ON candidate.knowledge_item_id = item.knowledge_item_id
                WHERE item.owner_profile_id = @ProfileId
                  AND item.visibility = N''private''
                  AND item.item_status = N''unfinished''
                  AND item.archived_at_utc IS NULL;
                SET @ConfirmedCount = @@ROWCOUNT;

                /* One audit row per confirmed item, in the exact shape
                   every other Workshop procedure writes it (see
                   usp_ArchiveKnowledgeItemForOwner below), but under its
                   own distinct action name so the permanent trail reads
                   honestly: this is the standing-rule reconciliation
                   running because the member opened a page, never a
                   member edit and never a member confirm action. */
                DECLARE @AuditItemId bigint;
                DECLARE @AuditItemKey uniqueidentifier;
                DECLARE @AuditVersionNumber int;
                DECLARE @AuditMetadataJson nvarchar(max);
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                WHILE EXISTS (SELECT 1 FROM @Candidates)
                BEGIN
                    SELECT TOP (1)
                        @AuditItemId = knowledge_item_id,
                        @AuditItemKey = knowledge_item_key,
                        @AuditVersionNumber = confirmed_version_number
                    FROM @Candidates
                    ORDER BY knowledge_item_id;

                    SET @AuditMetadataJson = CONCAT(N''{"confirmed_version_number":'', @AuditVersionNumber,
                        N'',"reconciliation":"owner_standing_rule_2026_08_06"}'');

                    INSERT @AuditResult
                    EXEC dbo.usp_AppendAuditEvent
                        @ActorUserId = @UserId,
                        @ActorUserKeySnapshot = @UserKey,
                        @ActionType = N''knowledge_item.backlog_confirmed'',
                        @EntityType = N''knowledge_item'',
                        @EntityKey = @AuditItemKey,
                        @Outcome = N''success'',
                        @MetadataJson = @AuditMetadataJson;

                    DELETE @Candidates WHERE knowledge_item_id = @AuditItemId;
                END;

                DECLARE @RemainingCount int;
                SELECT @RemainingCount = COUNT(*)
                FROM dbo.knowledge_items AS item
                WHERE item.owner_profile_id = @ProfileId
                  AND item.visibility = N''private''
                  AND item.item_status = N''unfinished''
                  AND item.archived_at_utc IS NULL;

                COMMIT TRANSACTION;

                SELECT @ConfirmedCount AS confirmed_count, @RemainingCount AS remaining_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* ============================================================
       REVISED PROCEDURE: usp_ArchiveKnowledgeItemForOwner now accepts
       only item_status IN (N'unfinished', N'confirmed') -- closing the
       carried finding. Every other line is byte-identical to the
       PS-WORKSHOP-001 definition; the rollback below restores that exact
       original text.
       ============================================================ */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ArchiveKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53030, ''Owner, knowledge item, and expected version are required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                DECLARE @KnowledgeItemId bigint;
                /* PS-WORKSHOP-002 revision: item_status <> N''archived''
                   (which admitted N''suggested'') narrowed to
                   IN (N''unfinished'', N''confirmed''). An unaccepted AI
                   suggestion can no longer be archived, so it can never
                   reach usp_RestoreKnowledgeItemForOwner''s
                   confirmed-vs-unfinished recovery and come back as
                   N''unfinished'' -- closing the path by which it could
                   later be auto-confirmed by
                   usp_ConfirmAuthoredKnowledgeBacklogForOwner. */
                SELECT @KnowledgeItemId = item.knowledge_item_id
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status IN (N''unfinished'', N''confirmed'')
                  AND item.row_version = @ExpectedRowVersion;

                IF @KnowledgeItemId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                UPDATE dbo.knowledge_items
                SET item_status = N''archived'',
                    archived_at_utc = SYSUTCDATETIME(),
                    archived_by_user_id = @UserId,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE knowledge_item_id = @KnowledgeItemId;

                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''knowledge_item.archived'',
                    @EntityType = N''knowledge_item'',
                    @EntityKey = @KnowledgeItemKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{}'';

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, item.row_version
                FROM dbo.knowledge_items AS item
                WHERE item.knowledge_item_id = @KnowledgeItemId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* Fingerprint every procedure this migration created or revised, the
       PS_OPPSLATE_002_DEFINITION_HASH idiom PS-OPPSLATE-002 established:
       the new procedure and the one revised procedure both get this
       migration's own hash label. usp_ArchiveKnowledgeItemForOwner keeps
       its now-stale PS_WORKSHOP_001_DEFINITION_HASH property too (never
       removed here) -- deliberately unused by any guard once this
       migration is applied (see the drift-guard comment above: that
       property is intentionally excluded from PS-WORKSHOP-001-baseline
       drift checking from here on, because it correctly stops matching
       the moment this migration revises the procedure). It becomes
       meaningful again on its own if this migration is ever rolled back
       and the byte-identical original body is restored. */
    DECLARE @ProcedureHashPropertyName sysname = N'PS_WORKSHOP_002_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_ConfirmAuthoredKnowledgeBacklogForOwner'),
        (N'usp_ArchiveKnowledgeItemForOwner');
    DECLARE @ProtectedProcedureName sysname, @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures ORDER BY procedure_name;
        IF OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P') IS NULL
            THROW 53306, 'A required PS-WORKSHOP-002 procedure was not created.', 1;
        SELECT @ProtectedProcedureHash = CONVERT(nvarchar(64),
            HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P'))), 2);
        IF EXISTS (SELECT 1 FROM sys.extended_properties
                   WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
                     AND minor_id = 0 AND name = @ProcedureHashPropertyName)
            EXEC sys.sp_updateextendedproperty @name=@ProcedureHashPropertyName,
                @value=@ProtectedProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty @name=@ProcedureHashPropertyName,
                @value=@ProtectedProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@ProtectedProcedureName;
        DELETE @ProtectedProcedures WHERE procedure_name = @ProtectedProcedureName;
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-WORKSHOP-002')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-WORKSHOP-002', N'Leg 9: gated in-place confirmation of the pre-existing member-authored Workshop knowledge backlog (usp_ConfirmAuthoredKnowledgeBacklogForOwner), bounded and audited under a distinct action name, with zero content/version/updated_at mutation; and the closing fix to usp_ArchiveKnowledgeItemForOwner so an unaccepted suggested item can never launder into auto-confirmed truth via archive/restore. Requires the PS-WORKSHOP-001 baseline.', N'PeerSlate Bible and Roadmap v3.0');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied',
            @EntityType=N'database_migration', @Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-WORKSHOP-002"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
