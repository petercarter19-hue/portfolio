/*
PS-RESUME-DRAFT-001 — proposed owner-scoped Resume draft overlay.

PROPOSED ONLY. This file has not been applied to any database. Its registry
gate is null. Disposable SQL Server execution, concurrency, rollback, and
driver serialization proof remain required before any separately authorized
schema application. Allowlisting procedure names does not apply this file.
Publication procedures are out of scope.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-ENTRY-POLICY-001')
        THROW 52200, 'PS-ENTRY-POLICY-001 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.resume_drafts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_drafts
        (
            resume_draft_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            draft_version int NOT NULL CONSTRAINT DF_resume_drafts_version DEFAULT 0,
            base_publication_version nvarchar(64) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_drafts_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_drafts_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_drafts PRIMARY KEY (resume_draft_id),
            CONSTRAINT UQ_resume_drafts_owner UNIQUE (owner_profile_id),
            CONSTRAINT FK_resume_drafts_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_drafts_version CHECK (draft_version >= 0)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_draft_items', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_draft_items
        (
            resume_draft_item_id bigint IDENTITY(1,1) NOT NULL,
            resume_draft_id bigint NOT NULL,
            record_key uniqueidentifier NOT NULL,
            record_type nvarchar(40) NOT NULL,
            base_content_token nvarchar(64) NOT NULL,
            base_access_revision int NOT NULL,
            proposed_values_json nvarchar(max) NOT NULL,
            intended_permission_expansions_json nvarchar(max) NULL,
            is_new bit NOT NULL CONSTRAINT DF_resume_draft_items_new DEFAULT 0,
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_draft_items_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_draft_items PRIMARY KEY (resume_draft_item_id),
            CONSTRAINT UQ_resume_draft_items_draft_record UNIQUE (resume_draft_id, record_key),
            CONSTRAINT FK_resume_draft_items_draft
                FOREIGN KEY (resume_draft_id) REFERENCES dbo.resume_drafts(resume_draft_id),
            CONSTRAINT CK_resume_draft_items_type CHECK
                (record_type IN (N'role', N'education', N'credential', N'skill', N'accomplishment')),
            CONSTRAINT CK_resume_draft_items_access CHECK (base_access_revision >= 1),
            CONSTRAINT CK_resume_draft_items_json CHECK (ISJSON(proposed_values_json) = 1),
            CONSTRAINT CK_resume_draft_items_intent CHECK
                (intended_permission_expansions_json IS NULL
                 OR ISJSON(intended_permission_expansions_json) = 1)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_draft_command_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_draft_command_receipts
        (
            command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            command_type nvarchar(40) NOT NULL,
            outcome nvarchar(40) NOT NULL,
            committed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_resume_draft_command_receipts_committed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_draft_command_receipts PRIMARY KEY (command_receipt_id),
            CONSTRAINT UQ_resume_draft_command_receipts_owner_request
                UNIQUE (owner_profile_id, request_id),
            CONSTRAINT FK_resume_draft_command_receipts_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_draft_command_receipts_digest
                CHECK (request_digest NOT LIKE '%[^0-9a-f]%' AND LEN(request_digest) = 64),
            CONSTRAINT CK_resume_draft_command_receipts_type CHECK
                (command_type IN (N'save_item', N'discard_item', N'create_private_item', N'review_candidate')),
            CONSTRAINT CK_resume_draft_command_receipts_outcome CHECK
                (outcome IN (N'saved', N'discarded', N'created', N'reviewed'))
        );
    END;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_resume_draft_command_receipts_immutable
        ON dbo.resume_draft_command_receipts
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 52201, ''Resume draft command receipts are immutable.'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetResumeDraftForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* db.py uses an autocommit connection. Own the transaction inside
               the procedure so the two result sets are one consistent read
               and every lock is released by this procedure. */
            BEGIN TRY
            BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;

            /* Fix the shared-resource lock order explicitly: owner draft,
               receipt range, then items. Keep the public reader at exactly two
               result sets by carrying receipts in the header JSON column. */
            DECLARE @ReadDraftId bigint;
            DECLARE @ReadDraftVersion int;
            DECLARE @ReadBasePublicationVersion nvarchar(64);
            SELECT @ReadDraftId = draft.resume_draft_id,
                   @ReadDraftVersion = draft.draft_version,
                   @ReadBasePublicationVersion = draft.base_publication_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            DECLARE @CommandReceiptsJson nvarchar(max);
            SELECT @CommandReceiptsJson = (
                SELECT
                    CONVERT(nvarchar(36), receipt.request_id) AS request_id,
                    receipt.request_digest,
                    receipt.outcome
                FROM dbo.resume_draft_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
                WHERE receipt.owner_profile_id = @ProfileId
                ORDER BY receipt.committed_at_utc, receipt.request_id
                FOR JSON PATH
            );

            SELECT
                @ReadDraftVersion AS draft_version,
                @ReadBasePublicationVersion AS base_publication_version,
                JSON_QUERY(COALESCE(@CommandReceiptsJson, N''[]'')) AS command_receipts_json
            WHERE @ReadDraftId IS NOT NULL;

            SELECT
                item.record_key,
                item.record_type,
                item.base_content_token,
                item.base_access_revision,
                item.proposed_values_json,
                item.intended_permission_expansions_json,
                item.is_new
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.resume_draft_items AS item WITH (UPDLOCK, HOLDLOCK)
              ON item.resume_draft_id = draft.resume_draft_id
            WHERE draft.owner_profile_id = @ProfileId
            ORDER BY item.record_type, item.record_key;

            COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeDraftCommandForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* The driver is autocommit, so receipt arbitration, the shared
               draft-version fence, item mutation and receipt insertion must be
               owned by one internal transaction. A nested intake call already
               owns the outer transaction, so this callee participates in it
               and never commits or rolls the caller back. */
            DECLARE @OwnTransaction bit = 0;
            IF @@TRANCOUNT = 0
            BEGIN
                BEGIN TRANSACTION;
                SET @OwnTransaction = 1;
            END;

            BEGIN TRY

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;

            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            /* The application computes the receipt digest from the normalized
               command semantics. Use that exact digest for both first commit
               and replay; hashing this transport envelope is not equivalent. */
            DECLARE @IncomingDigest nvarchar(128) = JSON_VALUE(@CommandJson, ''$.request_digest'');
            IF @IncomingDigest IS NULL
               OR LEN(@IncomingDigest) <> 64
               OR @IncomingDigest COLLATE Latin1_General_100_BIN2 LIKE ''%[^0-9a-f]%''
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;
            DECLARE @Digest char(64) = CONVERT(char(64), @IncomingDigest);
            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingOutcome nvarchar(40);

            /* Every reader and both text/media writers acquire the shared
               owner draft before a receipt row. The version is intentionally
               not evaluated yet: an exact receipt replay still wins before
               the expected-version fence below. */
            DECLARE @DraftId bigint;
            DECLARE @DraftVersion int;
            SELECT @DraftId = draft.resume_draft_id,
                   @DraftVersion = draft.draft_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            SELECT @ExistingDigest = receipt.request_digest,
                   @ExistingOutcome = receipt.outcome
            FROM dbo.resume_draft_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId
              AND receipt.request_id = @RequestId;

            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @Digest
                BEGIN
                    /* RESUME_DRAFT_IDEMPOTENCY_CONFLICT is returned as a
                       stable outcome row so adapters do not parse engine
                       error text and can map the conflict deterministically. */
                    IF @OwnTransaction = 1 COMMIT TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed,
                           CONVERT(bit, 0) AS replayed,
                           N''idempotency_conflict'' AS outcome,
                           @ExistingDigest AS request_digest,
                           CONVERT(bit, 0) AS publishes;
                    RETURN;
                END;
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 1) AS replayed,
                       @ExistingOutcome AS outcome,
                       @ExistingDigest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            DECLARE @CommandType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
            DECLARE @ExpectedDraftVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_draft_version''));
            IF @CommandType NOT IN (N''save_item'', N''discard_item'', N''create_private_item'', N''review_candidate'')
               OR @ExpectedDraftVersion IS NULL
               OR @ExpectedDraftVersion < 0
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            /* Both text and media commands acquire this same owner draft row
               before their domain-specific writes. Exact replay was resolved
               above, so only a genuinely new command reaches the fence. */
            IF @DraftId IS NULL AND @ExpectedDraftVersion = 0
            BEGIN
                INSERT dbo.resume_drafts (owner_profile_id, draft_version)
                VALUES (@ProfileId, 0);
                SELECT @DraftId = SCOPE_IDENTITY(), @DraftVersion = 0;
            END;

            IF ISNULL(@DraftVersion, 0) <> @ExpectedDraftVersion
               OR @DraftId IS NULL
            BEGIN
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 0) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''stale_draft'' AS outcome,
                       @DraftVersion AS current_draft_version,
                       @ExpectedDraftVersion AS expected_draft_version,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''review_candidate''
            BEGIN
                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''reviewed'');
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''reviewed'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            DECLARE @RecordKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.record_key''));
            DECLARE @RecordType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.record_type'');
            DECLARE @ExpectedToken nvarchar(64) = JSON_VALUE(@CommandJson, ''$.expected_content_token'');
            DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision''));
            DECLARE @Proposed nvarchar(max) = JSON_QUERY(@CommandJson, ''$.values'');
            DECLARE @Intended nvarchar(max) = JSON_QUERY(@CommandJson, ''$.intended_permission_expansions'');

            IF @CommandType IN (N''save_item'', N''discard_item'', N''create_private_item'')
               AND @RecordKey IS NULL
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            IF @CommandType = N''save_item''
               AND (
                    @ExpectedToken IS NULL
                    OR @ExpectedAccess IS NULL
                    OR ISJSON(ISNULL(@Proposed, N''{}'')) <> 1
               )
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            IF @Intended IS NOT NULL AND ISJSON(@Intended) <> 1
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            IF @CommandType = N''save_item''
            BEGIN
                DECLARE @PolicyContent int;
                DECLARE @PolicyAccess int;
                SELECT @PolicyContent = record.content_version,
                       @PolicyAccess = record.access_revision
                FROM dbo.entry_policy_records AS record WITH (UPDLOCK, HOLDLOCK)
                WHERE record.owner_profile_id = @ProfileId
                  AND record.entry_key = @RecordKey
                  AND record.lifecycle <> N''permanently_deleted'';

                IF @PolicyAccess IS NOT NULL AND @PolicyAccess <> @ExpectedAccess
                    THROW 52205, ''RESUME_DRAFT_CHANGED'', 1;
                IF @PolicyContent IS NOT NULL
                   AND @ExpectedToken NOT LIKE ''%[^0-9]%''
                   AND CONVERT(int, @ExpectedToken) <> @PolicyContent
                    THROW 52205, ''RESUME_DRAFT_CHANGED'', 1;
            END;

            IF @CommandType = N''save_item''
            BEGIN
                MERGE dbo.resume_draft_items WITH (UPDLOCK, HOLDLOCK) AS target
                USING (SELECT @DraftId AS resume_draft_id, @RecordKey AS record_key) AS source
                   ON target.resume_draft_id = source.resume_draft_id
                  AND target.record_key = source.record_key
                WHEN MATCHED THEN
                    UPDATE SET
                        record_type = @RecordType,
                        base_content_token = @ExpectedToken,
                        base_access_revision = @ExpectedAccess,
                        proposed_values_json = ISNULL(@Proposed, N''{}''),
                        intended_permission_expansions_json = @Intended,
                        is_new = 0,
                        updated_at_utc = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT
                        (resume_draft_id, record_key, record_type, base_content_token,
                         base_access_revision, proposed_values_json,
                         intended_permission_expansions_json, is_new)
                    VALUES
                        (@DraftId, @RecordKey, @RecordType, @ExpectedToken,
                         @ExpectedAccess, ISNULL(@Proposed, N''{}''), @Intended, 0);

                UPDATE dbo.resume_drafts
                SET draft_version = @DraftVersion + 1,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE resume_draft_id = @DraftId;

                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''saved'');

                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''saved'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''discard_item''
            BEGIN
                DELETE dbo.resume_draft_items
                WHERE resume_draft_id = @DraftId
                  AND record_key = @RecordKey;
                IF @@ROWCOUNT > 0
                    UPDATE dbo.resume_drafts
                    SET draft_version = @DraftVersion + 1,
                        updated_at_utc = SYSUTCDATETIME()
                    WHERE resume_draft_id = @DraftId;

                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''discarded'');

                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''discarded'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''create_private_item''
            BEGIN
                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''created'');
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''created'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;
            END TRY
            BEGIN CATCH
                IF @OwnTransaction = 1 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-DRAFT-001')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description)
        VALUES (N'PS-RESUME-DRAFT-001', N'Proposed owner-scoped private Resume draft overlay and command receipts');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
