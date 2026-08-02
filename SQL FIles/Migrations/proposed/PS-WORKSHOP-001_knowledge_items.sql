/* ============================================================
   PS-WORKSHOP-001 - private member knowledge store (Slice W1)

   Adds the Workshop / My Information foundation: one canonical
   knowledge_items row per thing a member knows or has said about
   themselves, an append-in-practice knowledge_item_versions table
   holding the member-approved wording (canonical, D1) alongside the
   original member wording (retained, never overwritten), and an
   idempotency ledger for one-step Save. No AI proposal is ever
   written here (architecture doc 17 section 4.2 - a proposal
   round-trips through a signed token and never reaches this store).

   Per doc 20 section 6a (owner decision, 2026-08-01), AI use of
   confirmed information is always on with no per-item permission
   control: there is no per-item AI-use permission column, no
   permission procedure, and no permission predicate anywhere in
   this file. Archiving or deleting an item is the member's only
   removal control from future AI grounding.

   visibility is hard-locked to N'private' in v1 (CHECK, not a
   default that could silently change). knowledge_item_uses (the
   downstream "use elsewhere" reference) is out of scope for W1 per
   architecture doc 17 section 5.4/5.5 and sequence doc 18 slice W4;
   usp_DeleteKnowledgeItemForOwner below is a plain hard delete of
   item + versions because no downstream use table exists yet. W4
   must change delete into a guarded, affected-use-aware flow before
   any knowledge_item_uses row can reference a deleted item.

   Dependency note: the task brief that authorized this slice named
   PS-PLAT-002 (member_profiles) and PS-PLAT-001 (migration ledger +
   usp_AppendAuditEvent) as the required guards. This file also
   requires PS-AUTH-001, because every procedure below resolves
   @UserKey against app_users.user_key, and that column is added by
   PS-AUTH-001 (confirmed by inspecting PS-MOMENT-001, PS-HOME-001,
   and PS-JOURNAL-001, which all guard PS-AUTH-001 for the identical
   reason). This is a necessary completion of an underspecified
   dependency, not an architectural change.

   Rollback: PS-WORKSHOP-001_knowledge_items_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53000, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-001')
        THROW 53001, 'PS-PLAT-001 must be applied before PS-WORKSHOP-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002')
        THROW 53002, 'PS-PLAT-002 must be applied before PS-WORKSHOP-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 53003, 'PS-AUTH-001 must be applied before PS-WORKSHOP-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 53004, 'The owner, profile, or audit foundation is missing.', 1;

    IF OBJECT_ID(N'dbo.knowledge_items', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.knowledge_items
        (
            knowledge_item_id bigint IDENTITY(1,1) NOT NULL,
            knowledge_item_key uniqueidentifier NOT NULL
                CONSTRAINT DF_knowledge_items_key DEFAULT NEWSEQUENTIALID(),
            owner_profile_id bigint NOT NULL,
            item_status nvarchar(30) NOT NULL
                CONSTRAINT DF_knowledge_items_status DEFAULT N'unfinished',
            classification nvarchar(20) NOT NULL
                CONSTRAINT DF_knowledge_items_classification DEFAULT N'unclassified',
            visibility nvarchar(20) NOT NULL
                CONSTRAINT DF_knowledge_items_visibility DEFAULT N'private',
            current_version_number int NOT NULL
                CONSTRAINT DF_knowledge_items_current_version DEFAULT 1,
            confirmed_version_number int NULL,
            confirmed_by_user_id int NULL,
            confirmed_at_utc datetime2(7) NULL,
            archived_at_utc datetime2(7) NULL,
            archived_by_user_id int NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_knowledge_items_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_knowledge_items_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_knowledge_items PRIMARY KEY (knowledge_item_id),
            CONSTRAINT UQ_knowledge_items_key UNIQUE (knowledge_item_key),
            CONSTRAINT UQ_knowledge_items_id_owner UNIQUE (knowledge_item_id, owner_profile_id),
            CONSTRAINT FK_knowledge_items_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_knowledge_items_confirmer FOREIGN KEY (confirmed_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_knowledge_items_archiver FOREIGN KEY (archived_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_knowledge_items_status CHECK
                (item_status IN (N'suggested', N'unfinished', N'confirmed', N'archived')),
            CONSTRAINT CK_knowledge_items_classification CHECK
                (classification IN (N'work', N'personal', N'both', N'unclassified')),
            CONSTRAINT CK_knowledge_items_visibility CHECK (visibility = N'private'),
            CONSTRAINT CK_knowledge_items_current_version CHECK (current_version_number > 0),
            /* Modeled on CK_moments_confirmation_state (PS-MOMENT-001), extended
               for the fourth (archived) item_status value that Moments does not
               have. suggested/unfinished can never carry confirmation data;
               confirmed strictly requires all three fields set and the
               confirmed version to equal the current version (D1's canonical
               wording lives on the confirmed current version); archived may
               carry either the fully-null triple (never confirmed before
               archiving) or the fully-set triple (archived after being
               confirmed) so that restoring an item can recover which state it
               came from without a separate shadow column. */
            CONSTRAINT CK_knowledge_items_confirmation_state CHECK
            (
                (
                    item_status IN (N'suggested', N'unfinished')
                    AND confirmed_version_number IS NULL
                    AND confirmed_by_user_id IS NULL
                    AND confirmed_at_utc IS NULL
                )
                OR
                (
                    item_status = N'confirmed'
                    AND confirmed_version_number = current_version_number
                    AND confirmed_by_user_id IS NOT NULL
                    AND confirmed_at_utc IS NOT NULL
                )
                OR
                (
                    item_status = N'archived'
                    AND
                    (
                        (confirmed_version_number IS NULL AND confirmed_by_user_id IS NULL AND confirmed_at_utc IS NULL)
                        OR
                        (confirmed_version_number IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at_utc IS NOT NULL)
                    )
                )
            ),
            CONSTRAINT CK_knowledge_items_archive_pair CHECK
            (
                (item_status <> N'archived' AND archived_at_utc IS NULL AND archived_by_user_id IS NULL)
                OR
                (item_status = N'archived' AND archived_at_utc IS NOT NULL AND archived_by_user_id IS NOT NULL)
            )
        );

        CREATE INDEX IX_knowledge_items_owner_updated
            ON dbo.knowledge_items(owner_profile_id, updated_at_utc DESC, knowledge_item_id DESC)
            INCLUDE (knowledge_item_key, item_status, classification, current_version_number);
    END;

    IF OBJECT_ID(N'dbo.knowledge_item_versions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.knowledge_item_versions
        (
            knowledge_item_version_id bigint IDENTITY(1,1) NOT NULL,
            knowledge_item_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            version_number int NOT NULL,
            title nvarchar(160) NOT NULL,
            approved_wording nvarchar(max) NOT NULL,
            original_member_wording nvarchar(max) NOT NULL,
            body_format nvarchar(20) NOT NULL
                CONSTRAINT DF_knowledge_item_versions_format DEFAULT N'plain',
            authored_via nvarchar(30) NOT NULL
                CONSTRAINT DF_knowledge_item_versions_authored_via DEFAULT N'typed',
            saved_by_user_id int NOT NULL,
            saved_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_knowledge_item_versions_saved DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_knowledge_item_versions PRIMARY KEY (knowledge_item_version_id),
            CONSTRAINT UQ_knowledge_item_versions_number UNIQUE (knowledge_item_id, version_number),
            CONSTRAINT FK_knowledge_item_versions_item FOREIGN KEY (knowledge_item_id, owner_profile_id)
                REFERENCES dbo.knowledge_items(knowledge_item_id, owner_profile_id),
            CONSTRAINT FK_knowledge_item_versions_actor FOREIGN KEY (saved_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_knowledge_item_versions_number CHECK (version_number > 0),
            CONSTRAINT CK_knowledge_item_versions_format CHECK (body_format IN (N'plain', N'rich')),
            CONSTRAINT CK_knowledge_item_versions_authored_via CHECK
                (authored_via IN (N'typed', N'spoken', N'ai_assisted_approved')),
            /* UTF-16 code-unit length limits (DATALENGTH/2), matching the
               moment_versions idiom (PS-MOMENT-001) and services/moment_service.py
               utf16_length. approved_wording and original_member_wording are
               both required and both bounded 1..8000, exactly as architecture
               doc 17 section 5.2 specifies for the canonical and retained
               member wording respectively. */
            CONSTRAINT CK_knowledge_item_versions_title_length CHECK
                (DATALENGTH(title) / 2 BETWEEN 1 AND 160),
            CONSTRAINT CK_knowledge_item_versions_approved_length CHECK
                (DATALENGTH(approved_wording) / 2 BETWEEN 1 AND 8000),
            CONSTRAINT CK_knowledge_item_versions_original_length CHECK
                (DATALENGTH(original_member_wording) / 2 BETWEEN 1 AND 8000)
        );

        CREATE INDEX IX_knowledge_item_versions_current
            ON dbo.knowledge_item_versions(knowledge_item_id, version_number DESC)
            INCLUDE (title, body_format, authored_via, saved_at_utc);
    END;

    /* Idempotency ledger for one-step Save, in the exact moment_save_requests
       shape (PS-JOURNAL-001): an owner-scoped replay key and the resulting
       knowledge item reference only - no title, wording, or other content. */
    IF OBJECT_ID(N'dbo.knowledge_item_save_requests', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.knowledge_item_save_requests
        (
            knowledge_item_save_request_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            idempotency_key nvarchar(200) NOT NULL,
            knowledge_item_id bigint NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_knowledge_item_save_requests_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_knowledge_item_save_requests PRIMARY KEY (knowledge_item_save_request_id),
            CONSTRAINT UQ_knowledge_item_save_requests_owner_key
                UNIQUE (owner_profile_id, idempotency_key),
            CONSTRAINT FK_knowledge_item_save_requests_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_knowledge_item_save_requests_item FOREIGN KEY (knowledge_item_id)
                REFERENCES dbo.knowledge_items(knowledge_item_id)
        );

        CREATE INDEX IX_knowledge_item_save_requests_item
            ON dbo.knowledge_item_save_requests(knowledge_item_id);
    END;

    IF COL_LENGTH(N'dbo.knowledge_items', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_versions', N'approved_wording') IS NULL
       OR COL_LENGTH(N'dbo.knowledge_item_save_requests', N'idempotency_key') IS NULL
        THROW 53005, 'Existing Knowledge tables are incompatible.', 1;

    /* ------------------------------------------------------------
       Stored procedures. Application access goes ONLY through these
       (services/database_service.py's allowlist pattern). Every
       procedure resolves @UserKey -> @ProfileId itself and returns
       empty/changed/not_found rather than accepting an owner id from
       the caller; every predicate re-asserts owner_profile_id.
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListKnowledgeItemsForOwner
            @UserKey nvarchar(300),
            @IncludeArchived bit = 0,
            /* Defaults to 1 (unchanged behavior: both result sets, exactly
               as services/knowledge_service.py already calls this today).
               T-SQL''s INSERT ... EXEC requires every result set a target
               procedure returns to match the INSERT target''s column list -
               it does not silently keep only the first, despite what an
               earlier version of this comment claimed (that claim was never
               exercised against a real database until the first live
               staging rehearsal, which is how this got caught). The
               owner-isolation verifier passes @IncludeTotalCount = 0 so its
               INSERT ... EXEC captures work; it does not assert on
               total_count today. */
            @IncludeTotalCount bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;
            IF @IncludeArchived IS NULL SET @IncludeArchived = 0;
            IF @IncludeTotalCount IS NULL SET @IncludeTotalCount = 1;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT TOP (200)
                item.knowledge_item_key,
                item.item_status,
                item.classification,
                item.current_version_number,
                item.confirmed_version_number,
                item.confirmed_at_utc,
                item.archived_at_utc,
                item.created_at_utc,
                item.updated_at_utc,
                CONVERT(binary(8), item.row_version) AS row_version,
                version_record.title,
                version_record.body_format,
                version_record.authored_via
            FROM dbo.knowledge_items AS item
            JOIN dbo.knowledge_item_versions AS version_record
              ON version_record.knowledge_item_id = item.knowledge_item_id
             AND version_record.owner_profile_id = item.owner_profile_id
             AND version_record.version_number = item.current_version_number
            WHERE item.owner_profile_id = @ProfileId
              AND item.visibility = N''private''
              AND (@IncludeArchived = 1 OR item.item_status <> N''archived'')
            ORDER BY item.updated_at_utc DESC, item.knowledge_item_id DESC;

            /* Second result set (opt-out via @IncludeTotalCount): the
               owner''s TRUE count matching this exact scope (same predicate
               as the TOP (200) read above, minus the ordering/cap), so a
               caller whose owner has more than 200 items can render an
               honest "Showing 200 of <true total>" instead of silently
               implying 200 is everything. A stored procedure returning a
               second, differently-shaped result set after the first is an
               established pattern here already (usp_GetKnowledgeItemForOwner''s
               item + TOP (50) history result sets, gated the same way by
               @IncludeHistory). */
            IF @IncludeTotalCount = 1
            BEGIN
                SELECT COUNT(*) AS total_count
                FROM dbo.knowledge_items AS item
                WHERE item.owner_profile_id = @ProfileId
                  AND item.visibility = N''private''
                  AND (@IncludeArchived = 1 OR item.item_status <> N''archived'');
            END;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            /* Defaults to 1 (unchanged behavior: both result sets, exactly
               as services/knowledge_service.py already calls this today -
               it requires exactly two result sets back). T-SQL''s
               INSERT ... EXEC requires every result set a target procedure
               returns to match the INSERT target''s column list, so a
               caller that only wants the item row (the owner-isolation
               verifier, via INSERT ... EXEC) passes
               @IncludeHistory = 0 to suppress the differently-shaped
               history result set rather than have the capture fail. */
            @IncludeHistory bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL RETURN;
            IF @IncludeHistory IS NULL SET @IncludeHistory = 1;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @KnowledgeItemId bigint;
            SELECT @KnowledgeItemId = item.knowledge_item_id
            FROM dbo.knowledge_items AS item
            WHERE item.owner_profile_id = @ProfileId
              AND item.knowledge_item_key = @KnowledgeItemKey
              AND item.visibility = N''private'';

            IF @KnowledgeItemId IS NULL RETURN;

            SELECT
                item.knowledge_item_key,
                item.item_status,
                item.classification,
                item.current_version_number,
                item.confirmed_version_number,
                item.confirmed_at_utc,
                item.archived_at_utc,
                item.created_at_utc,
                item.updated_at_utc,
                CONVERT(binary(8), item.row_version) AS row_version,
                version_record.version_number,
                version_record.title,
                version_record.approved_wording,
                version_record.original_member_wording,
                version_record.body_format,
                version_record.authored_via,
                version_record.saved_at_utc
            FROM dbo.knowledge_items AS item
            JOIN dbo.knowledge_item_versions AS version_record
              ON version_record.knowledge_item_id = item.knowledge_item_id
             AND version_record.owner_profile_id = item.owner_profile_id
             AND version_record.version_number = item.current_version_number
            WHERE item.knowledge_item_id = @KnowledgeItemId
              AND item.owner_profile_id = @ProfileId;

            IF @IncludeHistory = 1
            BEGIN
                SELECT TOP (50)
                    history.version_number,
                    history.title,
                    history.body_format,
                    history.authored_via,
                    history.saved_at_utc
                FROM dbo.knowledge_item_versions AS history
                WHERE history.knowledge_item_id = @KnowledgeItemId
                  AND history.owner_profile_id = @ProfileId
                ORDER BY history.version_number DESC;
            END;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveKnowledgeItemForOwner
            @UserKey nvarchar(300),
            /* MINOR 11 correction: widened from nvarchar(200) so the
               DATALENGTH-based length guard below can actually observe (and
               reject) an over-length caller-supplied key rather than have
               the parameter itself silently truncate it to 200 characters
               before the guard ever runs. The idempotency_key COLUMN stays
               nvarchar(200) — the real, enforced limit is unchanged, just
               now actually enforced instead of silently pre-truncated. */
            @IdempotencyKey nvarchar(4000),
            @Title nvarchar(160),
            @ApprovedWording nvarchar(max),
            @OriginalWording nvarchar(max),
            @BodyFormat nvarchar(20),
            @Classification nvarchar(20),
            @AuthoredVia nvarchar(30),
            @Confirm bit
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @IdempotencyKey = NULLIF(LTRIM(RTRIM(@IdempotencyKey)), N'''');
            SET @Title = NULLIF(LTRIM(RTRIM(@Title)), N'''');
            SET @ApprovedWording = NULLIF(LTRIM(RTRIM(@ApprovedWording)), N'''');
            SET @OriginalWording = NULLIF(LTRIM(RTRIM(@OriginalWording)), N'''');
            SET @BodyFormat = NULLIF(LTRIM(RTRIM(@BodyFormat)), N'''');
            SET @Classification = NULLIF(LTRIM(RTRIM(@Classification)), N'''');
            SET @AuthoredVia = NULLIF(LTRIM(RTRIM(@AuthoredVia)), N'''');
            IF @Confirm IS NULL SET @Confirm = 0;

            IF @UserKey IS NULL OR @IdempotencyKey IS NULL
                THROW 53010, ''Owner and idempotency key are required.'', 1;
            IF DATALENGTH(@IdempotencyKey) / 2 > 200
                THROW 53011, ''Idempotency key exceeds its limit.'', 1;
            IF @Classification IS NULL OR @Classification NOT IN (N''work'', N''personal'', N''both'', N''unclassified'')
                THROW 53012, ''Classification is invalid.'', 1;
            IF @BodyFormat IS NULL OR @BodyFormat NOT IN (N''plain'', N''rich'')
                THROW 53013, ''Body format is invalid.'', 1;
            IF @AuthoredVia IS NULL OR @AuthoredVia NOT IN (N''typed'', N''spoken'', N''ai_assisted_approved'')
                THROW 53014, ''Authored-via provenance is invalid.'', 1;
            IF @Title IS NULL OR @ApprovedWording IS NULL OR @OriginalWording IS NULL
                THROW 53015, ''Title, approved wording, and original wording are required.'', 1;
            IF DATALENGTH(@Title) / 2 > 160
               OR DATALENGTH(@ApprovedWording) / 2 > 8000
               OR DATALENGTH(@OriginalWording) / 2 > 8000
                THROW 53016, ''One or more knowledge item fields exceeds its limit.'', 1;

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

                IF @ProfileId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS knowledge_item_key,
                           CAST(NULL AS nvarchar(30)) AS item_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                /* Idempotent replay: a repeated key for this owner always
                   returns the SAME item, never a second one. The range lock
                   on the unique (owner, key) index serializes any concurrent
                   replay of the same key. */
                DECLARE @ExistingItemId bigint;
                SELECT @ExistingItemId = request.knowledge_item_id
                FROM dbo.knowledge_item_save_requests AS request
                     WITH (UPDLOCK, HOLDLOCK, INDEX(UQ_knowledge_item_save_requests_owner_key))
                WHERE request.owner_profile_id = @ProfileId
                  AND request.idempotency_key = @IdempotencyKey;

                IF @ExistingItemId IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome,
                           item.knowledge_item_key,
                           item.item_status,
                           item.row_version
                    FROM dbo.knowledge_items AS item
                    WHERE item.knowledge_item_id = @ExistingItemId
                      AND item.owner_profile_id = @ProfileId;
                    RETURN;
                END;

                DECLARE @ItemStatus nvarchar(30) = CASE WHEN @Confirm = 1 THEN N''confirmed'' ELSE N''unfinished'' END;

                INSERT dbo.knowledge_items
                (
                    owner_profile_id, item_status, classification,
                    current_version_number, confirmed_version_number,
                    confirmed_by_user_id, confirmed_at_utc
                )
                VALUES
                (
                    @ProfileId, @ItemStatus, @Classification,
                    1,
                    CASE WHEN @Confirm = 1 THEN 1 ELSE NULL END,
                    CASE WHEN @Confirm = 1 THEN @UserId ELSE NULL END,
                    CASE WHEN @Confirm = 1 THEN SYSUTCDATETIME() ELSE NULL END
                );
                DECLARE @KnowledgeItemId bigint = CONVERT(bigint, SCOPE_IDENTITY());
                DECLARE @KnowledgeItemKey uniqueidentifier;
                SELECT @KnowledgeItemKey = knowledge_item_key
                FROM dbo.knowledge_items
                WHERE knowledge_item_id = @KnowledgeItemId AND owner_profile_id = @ProfileId;

                INSERT dbo.knowledge_item_versions
                (
                    knowledge_item_id, owner_profile_id, version_number, title,
                    approved_wording, original_member_wording, body_format,
                    authored_via, saved_by_user_id
                )
                VALUES
                (
                    @KnowledgeItemId, @ProfileId, 1, @Title,
                    @ApprovedWording, @OriginalWording, @BodyFormat,
                    @AuthoredVia, @UserId
                );

                INSERT dbo.knowledge_item_save_requests
                (
                    owner_profile_id, idempotency_key, knowledge_item_id
                )
                VALUES
                (
                    @ProfileId, @IdempotencyKey, @KnowledgeItemId
                );

                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"classification":"'', @Classification,
                    N''","authored_via":"'', @AuthoredVia,
                    N''","confirmed":'', CASE WHEN @Confirm = 1 THEN N''true'' ELSE N''false'' END,
                    N''}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''knowledge_item.saved'',
                    @EntityType = N''knowledge_item'',
                    @EntityKey = @KnowledgeItemKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       item.knowledge_item_key,
                       item.item_status,
                       item.row_version
                FROM dbo.knowledge_items AS item
                WHERE item.knowledge_item_id = @KnowledgeItemId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_UpdateKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @Title nvarchar(160),
            @ApprovedWording nvarchar(max),
            @BodyFormat nvarchar(20),
            @Classification nvarchar(20),
            @Confirm bit
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @Title = NULLIF(LTRIM(RTRIM(@Title)), N'''');
            SET @ApprovedWording = NULLIF(LTRIM(RTRIM(@ApprovedWording)), N'''');
            SET @BodyFormat = NULLIF(LTRIM(RTRIM(@BodyFormat)), N'''');
            SET @Classification = NULLIF(LTRIM(RTRIM(@Classification)), N'''');
            IF @Confirm IS NULL SET @Confirm = 0;

            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53020, ''Owner, knowledge item, and expected version are required.'', 1;
            IF @Classification IS NULL OR @Classification NOT IN (N''work'', N''personal'', N''both'', N''unclassified'')
                THROW 53021, ''Classification is invalid.'', 1;
            IF @BodyFormat IS NULL OR @BodyFormat NOT IN (N''plain'', N''rich'')
                THROW 53022, ''Body format is invalid.'', 1;
            IF @Title IS NULL OR @ApprovedWording IS NULL
                THROW 53023, ''Title and approved wording are required.'', 1;
            IF DATALENGTH(@Title) / 2 > 160 OR DATALENGTH(@ApprovedWording) / 2 > 8000
                THROW 53024, ''One or more knowledge item fields exceeds its limit.'', 1;

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

                /* Editing an archived item is refused (surfaced as ''changed''
                   exactly like any other not-found/mismatch case): a member
                   restores it first. This keeps the archive/restore/edit
                   state machine deterministic without a separate error code. */
                DECLARE @KnowledgeItemId bigint;
                DECLARE @CurrentVersionNumber int;
                SELECT
                    @KnowledgeItemId = item.knowledge_item_id,
                    @CurrentVersionNumber = item.current_version_number
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status <> N''archived''
                  AND item.row_version = @ExpectedRowVersion;

                IF @KnowledgeItemId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome,
                           CAST(NULL AS int) AS version_number,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                DECLARE @NextVersionNumber int = @CurrentVersionNumber + 1;

                /* original_member_wording of the NEW version is the new
                   approved wording itself: an edit made directly in My
                   Information is always the member''s own typed words (there
                   is no AI-assisted edit path in W1), so the member-typed
                   source and the canonical wording are identical for this
                   version, exactly as architecture doc 17 section 5.2/9.1
                   requires for a directly authored version. authored_via is
                   fixed to ''typed'' for the same reason. */
                INSERT dbo.knowledge_item_versions
                (
                    knowledge_item_id, owner_profile_id, version_number, title,
                    approved_wording, original_member_wording, body_format,
                    authored_via, saved_by_user_id
                )
                VALUES
                (
                    @KnowledgeItemId, @ProfileId, @NextVersionNumber, @Title,
                    @ApprovedWording, @ApprovedWording, @BodyFormat,
                    N''typed'', @UserId
                );

                UPDATE dbo.knowledge_items
                SET current_version_number = @NextVersionNumber,
                    classification = @Classification,
                    item_status = CASE WHEN @Confirm = 1 THEN N''confirmed'' ELSE N''unfinished'' END,
                    confirmed_version_number = CASE WHEN @Confirm = 1 THEN @NextVersionNumber ELSE NULL END,
                    confirmed_by_user_id = CASE WHEN @Confirm = 1 THEN @UserId ELSE NULL END,
                    confirmed_at_utc = CASE WHEN @Confirm = 1 THEN SYSUTCDATETIME() ELSE NULL END,
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
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"version_number":'', @NextVersionNumber,
                    N'',"classification":"'', @Classification,
                    N''","confirmed":'', CASE WHEN @Confirm = 1 THEN N''true'' ELSE N''false'' END,
                    N''}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''knowledge_item.updated'',
                    @EntityType = N''knowledge_item'',
                    @EntityKey = @KnowledgeItemKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       @NextVersionNumber AS version_number,
                       item.row_version
                FROM dbo.knowledge_items AS item
                WHERE item.knowledge_item_id = @KnowledgeItemId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

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
                SELECT @KnowledgeItemId = item.knowledge_item_id
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status <> N''archived''
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

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_RestoreKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53031, ''Owner, knowledge item, and expected version are required.'', 1;

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
                DECLARE @CurrentVersionNumber int;
                DECLARE @ConfirmedVersionNumber int;
                SELECT
                    @KnowledgeItemId = item.knowledge_item_id,
                    @CurrentVersionNumber = item.current_version_number,
                    @ConfirmedVersionNumber = item.confirmed_version_number
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.item_status = N''archived''
                  AND item.row_version = @ExpectedRowVersion;

                IF @KnowledgeItemId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                /* Restore recovers confirmed vs. unfinished from the retained
                   confirmation triple rather than a separate shadow column:
                   if the item was confirmed at exactly its current version
                   when it was archived, it comes back confirmed; otherwise it
                   comes back unfinished (never back to suggested - a
                   suggestion is not a state a member''s own archive/restore
                   action can produce). */
                UPDATE dbo.knowledge_items
                SET item_status = CASE
                        WHEN @ConfirmedVersionNumber IS NOT NULL AND @ConfirmedVersionNumber = @CurrentVersionNumber
                            THEN N''confirmed''
                        ELSE N''unfinished''
                    END,
                    archived_at_utc = NULL,
                    archived_by_user_id = NULL,
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
                    @ActionType = N''knowledge_item.restored'',
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

    /* W1 has no downstream use table (knowledge_item_uses arrives in W4,
       architecture doc 17 section 5.4). Delete is therefore a plain hard
       delete of the item and its versions. Before W4 ships, this procedure
       MUST be changed into a guarded flow that checks knowledge_item_uses
       and shows the member affected uses before deleting - exactly as the
       procedure header for usp_DeleteCapture warns for its own later
       Moment-source dependency. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteKnowledgeItemForOwner
            @UserKey nvarchar(300),
            @KnowledgeItemKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53032, ''Owner, knowledge item, and expected version are required.'', 1;

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
                DECLARE @PreviousStatus nvarchar(30);
                SELECT
                    @KnowledgeItemId = item.knowledge_item_id,
                    @PreviousStatus = item.item_status
                FROM dbo.knowledge_items AS item WITH (UPDLOCK, HOLDLOCK)
                WHERE item.owner_profile_id = @ProfileId
                  AND item.knowledge_item_key = @KnowledgeItemKey
                  AND item.visibility = N''private''
                  AND item.row_version = @ExpectedRowVersion;

                IF @KnowledgeItemId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                    RETURN;
                END;

                DECLARE @VersionCount int =
                (
                    SELECT COUNT(*) FROM dbo.knowledge_item_versions
                    WHERE knowledge_item_id = @KnowledgeItemId
                );

                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"previous_status":"'', @PreviousStatus,
                    N''","deleted_version_count":'', @VersionCount, N''}''
                );
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
                    @ActionType = N''knowledge_item.deleted'',
                    @EntityType = N''knowledge_item'',
                    @EntityKey = @KnowledgeItemKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                /* MINOR 8 correction: every predicate in this file re-asserts
                   owner_profile_id (see the header comment above) — these two
                   child deletes previously scoped only on knowledge_item_id.
                   @KnowledgeItemId is already owner-verified by the SELECT
                   above, so this was not an exploitable gap, but the explicit
                   re-assertion is the consistent, defense-in-depth pattern
                   every other predicate in this procedure follows. */
                DELETE dbo.knowledge_item_save_requests
                WHERE knowledge_item_id = @KnowledgeItemId AND owner_profile_id = @ProfileId;
                DELETE dbo.knowledge_item_versions
                WHERE knowledge_item_id = @KnowledgeItemId AND owner_profile_id = @ProfileId;
                DELETE dbo.knowledge_items
                WHERE knowledge_item_id = @KnowledgeItemId AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT <> 1
                    THROW 53033, ''Knowledge item delete did not complete atomically.'', 1;

                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome, @VersionCount AS deleted_version_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_WORKSHOP_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_ListKnowledgeItemsForOwner'),
        (N'usp_GetKnowledgeItemForOwner'),
        (N'usp_SaveKnowledgeItemForOwner'),
        (N'usp_UpdateKnowledgeItemForOwner'),
        (N'usp_ArchiveKnowledgeItemForOwner'),
        (N'usp_RestoreKnowledgeItemForOwner'),
        (N'usp_DeleteKnowledgeItemForOwner');

    DECLARE @ProtectedProcedureName sysname;
    DECLARE @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures
        ORDER BY procedure_name;

        SELECT @ProtectedProcedureHash = CONVERT
        (
            nvarchar(64),
            HASHBYTES
            (
                'SHA2_256',
                OBJECT_DEFINITION
                (
                    OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
                )
            ),
            2
        );

        IF EXISTS
        (
            SELECT 1
            FROM sys.extended_properties AS property
            WHERE property.class = 1
              AND property.major_id =
                  OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
              AND property.minor_id = 0
              AND property.name = @ProcedureHashPropertyName
        )
            EXEC sys.sp_updateextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;

        DELETE @ProtectedProcedures
        WHERE procedure_name = @ProtectedProcedureName;
    END;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-WORKSHOP-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-WORKSHOP-001',
            N'Slice W1: private member knowledge store (knowledge_items / knowledge_item_versions), owner-scoped list/get/save/update/archive/restore/delete procedures, and an idempotent Save ledger',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-WORKSHOP-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
