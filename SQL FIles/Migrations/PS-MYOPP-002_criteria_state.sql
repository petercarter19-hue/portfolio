/*
 PS-MYOPP-002 — My Opportunities C3 owner-scoped criteria state.

 Additive member-side persistence for visible criteria drafts, immutable draft
 versions, immutable applied snapshots, and content-free idempotency receipts.
 AI output is not canonical authority: application code validates proposals and
 deterministic commands own every write and token transition.  This migration
 creates no route, search execution, retrieval, provider, fixture row, job, or
 production action.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002')
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
            THROW 55600, 'PS-MYOPP-002 requires PS-MYOPP-001.', 1;

        CREATE TABLE dbo.myopp_criteria_drafts
        (
            myopp_criteria_draft_id bigint IDENTITY(1,1) NOT NULL,
            draft_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_criteria_drafts_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            draft_status nvarchar(20) NOT NULL CONSTRAINT DF_myopp_criteria_drafts_status DEFAULT N'live',
            version_number int NOT NULL CONSTRAINT DF_myopp_criteria_drafts_version DEFAULT 1,
            draft_version_token uniqueidentifier NULL CONSTRAINT DF_myopp_criteria_drafts_token DEFAULT NEWID(),
            criteria_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_criteria_drafts_criteria DEFAULT N'[]',
            verification_scope nvarchar(30) NOT NULL CONSTRAINT DF_myopp_criteria_drafts_scope DEFAULT N'both',
            direct_filters_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_criteria_drafts_filters DEFAULT N'{}',
            request_text nvarchar(4000) NULL,
            interpretation_provenance nvarchar(30) NOT NULL,
            interpretation_status nvarchar(30) NOT NULL,
            parent_snapshot_id bigint NULL,
            clarification_json nvarchar(max) NULL,
            terminal_outcome nvarchar(20) NULL,
            terminal_snapshot_id bigint NULL,
            terminal_execution_key uniqueidentifier NULL,
            terminal_receipt_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_criteria_drafts_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_criteria_drafts_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_criteria_drafts PRIMARY KEY (myopp_criteria_draft_id),
            CONSTRAINT UQ_myopp_criteria_drafts_key UNIQUE (draft_key),
            CONSTRAINT UQ_myopp_criteria_drafts_id_user UNIQUE (myopp_criteria_draft_id, user_key),
            CONSTRAINT UQ_myopp_criteria_drafts_key_user UNIQUE (draft_key, user_key),
            CONSTRAINT FK_myopp_criteria_drafts_user FOREIGN KEY (user_key) REFERENCES dbo.app_users (user_key),
            CONSTRAINT CK_myopp_criteria_drafts_status CHECK (draft_status IN (N'live', N'applied', N'discarded')),
            CONSTRAINT CK_myopp_criteria_drafts_version CHECK (version_number > 0),
            CONSTRAINT CK_myopp_criteria_drafts_criteria_json CHECK (ISJSON(criteria_json) = 1 AND LEFT(LTRIM(criteria_json), 1) = N'['),
            CONSTRAINT CK_myopp_criteria_drafts_scope CHECK (verification_scope IN (N'fully_verified', N'not_fully_verified', N'both')),
            CONSTRAINT CK_myopp_criteria_drafts_filters_json CHECK (ISJSON(direct_filters_json) = 1 AND LEFT(LTRIM(direct_filters_json), 1) = N'{'),
            CONSTRAINT CK_myopp_criteria_drafts_provenance CHECK (interpretation_provenance IN (N'ai_interpreted', N'member_edited', N'manual')),
            CONSTRAINT CK_myopp_criteria_drafts_interpretation_status CHECK (interpretation_status IN (N'ai_interpreted', N'manual_required', N'manual')),
            CONSTRAINT CK_myopp_criteria_drafts_clarification_json CHECK (clarification_json IS NULL OR (ISJSON(clarification_json) = 1 AND LEFT(LTRIM(clarification_json), 1) = N'{')),
            CONSTRAINT CK_myopp_criteria_drafts_terminal CHECK
            (
                (draft_status = N'live' AND draft_version_token IS NOT NULL AND terminal_outcome IS NULL AND terminal_snapshot_id IS NULL AND terminal_execution_key IS NULL AND terminal_receipt_at_utc IS NULL)
                OR
                (draft_status = N'applied' AND draft_version_token IS NULL AND terminal_outcome = N'applied' AND terminal_snapshot_id IS NOT NULL AND terminal_execution_key IS NOT NULL AND terminal_receipt_at_utc IS NOT NULL)
                OR
                (draft_status = N'discarded' AND draft_version_token IS NULL AND terminal_outcome = N'discarded' AND terminal_snapshot_id IS NULL AND terminal_execution_key IS NULL AND terminal_receipt_at_utc IS NOT NULL)
            ),
            CONSTRAINT CK_myopp_criteria_drafts_timestamp_order CHECK (updated_at_utc >= created_at_utc)
        );

        CREATE TABLE dbo.myopp_criteria_draft_versions
        (
            myopp_criteria_draft_version_id bigint IDENTITY(1,1) NOT NULL,
            myopp_criteria_draft_id bigint NOT NULL,
            user_key nvarchar(300) NOT NULL,
            version_number int NOT NULL,
            draft_version_token uniqueidentifier NOT NULL CONSTRAINT DF_myopp_criteria_draft_versions_token DEFAULT NEWID(),
            criteria_json nvarchar(max) NOT NULL,
            verification_scope nvarchar(30) NOT NULL,
            direct_filters_json nvarchar(max) NOT NULL,
            request_text nvarchar(4000) NULL,
            interpretation_provenance nvarchar(30) NOT NULL,
            interpretation_status nvarchar(30) NOT NULL,
            clarification_json nvarchar(max) NULL,
            recorded_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_criteria_draft_versions_recorded DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_criteria_draft_versions PRIMARY KEY (myopp_criteria_draft_version_id),
            CONSTRAINT UQ_myopp_criteria_draft_versions_id_user UNIQUE (myopp_criteria_draft_version_id, user_key),
            CONSTRAINT UQ_myopp_criteria_draft_versions_number UNIQUE (myopp_criteria_draft_id, version_number),
            CONSTRAINT UQ_myopp_criteria_draft_versions_token_user UNIQUE (draft_version_token, user_key),
            CONSTRAINT FK_myopp_criteria_draft_versions_draft_owner FOREIGN KEY (myopp_criteria_draft_id, user_key) REFERENCES dbo.myopp_criteria_drafts (myopp_criteria_draft_id, user_key),
            CONSTRAINT CK_myopp_criteria_draft_versions_version CHECK (version_number > 0),
            CONSTRAINT CK_myopp_criteria_draft_versions_criteria_json CHECK (ISJSON(criteria_json) = 1 AND LEFT(LTRIM(criteria_json), 1) = N'['),
            CONSTRAINT CK_myopp_criteria_draft_versions_scope CHECK (verification_scope IN (N'fully_verified', N'not_fully_verified', N'both')),
            CONSTRAINT CK_myopp_criteria_draft_versions_filters_json CHECK (ISJSON(direct_filters_json) = 1 AND LEFT(LTRIM(direct_filters_json), 1) = N'{'),
            CONSTRAINT CK_myopp_criteria_draft_versions_provenance CHECK (interpretation_provenance IN (N'ai_interpreted', N'member_edited', N'manual')),
            CONSTRAINT CK_myopp_criteria_draft_versions_interpretation_status CHECK (interpretation_status IN (N'ai_interpreted', N'manual_required', N'manual')),
            CONSTRAINT CK_myopp_criteria_draft_versions_clarification_json CHECK (clarification_json IS NULL OR (ISJSON(clarification_json) = 1 AND LEFT(LTRIM(clarification_json), 1) = N'{'))
        );

        CREATE TABLE dbo.myopp_applied_criteria_snapshots
        (
            myopp_applied_criteria_snapshot_id bigint IDENTITY(1,1) NOT NULL,
            snapshot_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_applied_criteria_snapshots_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            source_draft_id bigint NOT NULL,
            previous_snapshot_id bigint NULL,
            criteria_json nvarchar(max) NOT NULL,
            verification_scope nvarchar(30) NOT NULL,
            direct_filters_json nvarchar(max) NOT NULL,
            interpretation_provenance nvarchar(30) NOT NULL,
            applied_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_applied_criteria_snapshots_applied DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_applied_criteria_snapshots PRIMARY KEY (myopp_applied_criteria_snapshot_id),
            CONSTRAINT UQ_myopp_applied_criteria_snapshots_key UNIQUE (snapshot_key),
            CONSTRAINT UQ_myopp_applied_criteria_snapshots_id_user UNIQUE (myopp_applied_criteria_snapshot_id, user_key),
            CONSTRAINT UQ_myopp_applied_criteria_snapshots_key_user UNIQUE (snapshot_key, user_key),
            CONSTRAINT FK_myopp_applied_criteria_snapshots_user FOREIGN KEY (user_key) REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_applied_criteria_snapshots_source_draft_owner FOREIGN KEY (source_draft_id, user_key) REFERENCES dbo.myopp_criteria_drafts (myopp_criteria_draft_id, user_key),
            CONSTRAINT FK_myopp_applied_criteria_snapshots_previous_owner FOREIGN KEY (previous_snapshot_id, user_key) REFERENCES dbo.myopp_applied_criteria_snapshots (myopp_applied_criteria_snapshot_id, user_key),
            CONSTRAINT CK_myopp_applied_criteria_snapshots_no_self_parent CHECK (previous_snapshot_id IS NULL OR previous_snapshot_id <> myopp_applied_criteria_snapshot_id),
            CONSTRAINT CK_myopp_applied_criteria_snapshots_criteria_json CHECK (ISJSON(criteria_json) = 1 AND LEFT(LTRIM(criteria_json), 1) = N'['),
            CONSTRAINT CK_myopp_applied_criteria_snapshots_scope CHECK (verification_scope IN (N'fully_verified', N'not_fully_verified', N'both')),
            CONSTRAINT CK_myopp_applied_criteria_snapshots_filters_json CHECK (ISJSON(direct_filters_json) = 1 AND LEFT(LTRIM(direct_filters_json), 1) = N'{'),
            CONSTRAINT CK_myopp_applied_criteria_snapshots_provenance CHECK (interpretation_provenance IN (N'ai_interpreted', N'member_edited', N'manual'))
        );

        ALTER TABLE dbo.myopp_criteria_drafts ADD
            CONSTRAINT FK_myopp_criteria_drafts_parent_snapshot_owner FOREIGN KEY (parent_snapshot_id, user_key) REFERENCES dbo.myopp_applied_criteria_snapshots (myopp_applied_criteria_snapshot_id, user_key),
            CONSTRAINT FK_myopp_criteria_drafts_terminal_snapshot_owner FOREIGN KEY (terminal_snapshot_id, user_key) REFERENCES dbo.myopp_applied_criteria_snapshots (myopp_applied_criteria_snapshot_id, user_key);

        CREATE TABLE dbo.myopp_criteria_commands
        (
            myopp_criteria_command_id bigint IDENTITY(1,1) NOT NULL,
            user_key nvarchar(300) NOT NULL,
            idempotency_key_sha256 char(64) NOT NULL,
            command_name nvarchar(40) NOT NULL,
            canonical_input_sha256 char(64) NOT NULL,
            result_kind nvarchar(20) NOT NULL,
            result_draft_id bigint NOT NULL,
            result_draft_version_id bigint NULL,
            result_snapshot_id bigint NULL,
            result_execution_key uniqueidentifier NULL,
            result_outcome nvarchar(20) NULL,
            receipt_at_utc datetime2(7) NOT NULL,
            expires_at_utc datetime2(7) NOT NULL,
            CONSTRAINT PK_myopp_criteria_commands PRIMARY KEY (myopp_criteria_command_id),
            CONSTRAINT UQ_myopp_criteria_commands_owner_key UNIQUE (user_key, idempotency_key_sha256),
            CONSTRAINT FK_myopp_criteria_commands_user FOREIGN KEY (user_key) REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_criteria_commands_draft_owner FOREIGN KEY (result_draft_id, user_key) REFERENCES dbo.myopp_criteria_drafts (myopp_criteria_draft_id, user_key),
            CONSTRAINT FK_myopp_criteria_commands_version_owner FOREIGN KEY (result_draft_version_id, user_key) REFERENCES dbo.myopp_criteria_draft_versions (myopp_criteria_draft_version_id, user_key),
            CONSTRAINT FK_myopp_criteria_commands_snapshot_owner FOREIGN KEY (result_snapshot_id, user_key) REFERENCES dbo.myopp_applied_criteria_snapshots (myopp_applied_criteria_snapshot_id, user_key),
            CONSTRAINT CK_myopp_criteria_commands_idempotency_hash CHECK (LEN(idempotency_key_sha256) = 64 AND idempotency_key_sha256 NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_criteria_commands_input_hash CHECK (LEN(canonical_input_sha256) = 64 AND canonical_input_sha256 NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_criteria_commands_name CHECK (command_name IN (N'create_draft', N'interpret', N'edit_draft', N'answer_clarification', N'dismiss_clarification', N'refine_from_results', N'keep_current_criteria', N'discard_draft', N'apply')),
            CONSTRAINT CK_myopp_criteria_commands_result CHECK
            (
                (result_kind = N'live_draft' AND result_draft_version_id IS NOT NULL AND result_snapshot_id IS NULL AND result_execution_key IS NULL AND result_outcome IS NULL)
                OR
                (result_kind = N'terminal' AND result_draft_version_id IS NULL AND result_outcome = N'discarded' AND result_snapshot_id IS NULL AND result_execution_key IS NULL)
                OR
                (result_kind = N'terminal' AND result_draft_version_id IS NULL AND result_outcome = N'applied' AND result_snapshot_id IS NOT NULL AND result_execution_key IS NOT NULL)
            ),
            CONSTRAINT CK_myopp_criteria_commands_expiry CHECK (expires_at_utc > receipt_at_utc)
        );

        CREATE INDEX IX_myopp_criteria_drafts_owner_status
            ON dbo.myopp_criteria_drafts (user_key, draft_status, updated_at_utc DESC);
        CREATE INDEX IX_myopp_applied_criteria_snapshots_owner_applied
            ON dbo.myopp_applied_criteria_snapshots (user_key, applied_at_utc DESC);
        CREATE INDEX IX_myopp_criteria_commands_expiry
            ON dbo.myopp_criteria_commands (expires_at_utc);

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_criteria_drafts_transition_guard
        ON dbo.myopp_criteria_drafts
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM deleted d LEFT JOIN inserted i ON i.myopp_criteria_draft_id = d.myopp_criteria_draft_id WHERE i.myopp_criteria_draft_id IS NULL AND d.draft_status <> N''discarded'')
                THROW 55601, ''Only discarded criteria drafts may be removed by bounded cleanup.'', 1;
            IF EXISTS
            (
                SELECT 1
                FROM inserted i
                JOIN deleted d ON d.myopp_criteria_draft_id = i.myopp_criteria_draft_id
                WHERE i.draft_key <> d.draft_key OR i.user_key <> d.user_key OR i.created_at_utc <> d.created_at_utc
            )
                THROW 55602, ''Criteria draft identity is immutable.'', 1;
            IF EXISTS
            (
                SELECT 1
                FROM inserted i
                JOIN deleted d ON d.myopp_criteria_draft_id = i.myopp_criteria_draft_id
                WHERE d.draft_status <> N''live''
                   OR (i.draft_status = N''live'' AND (i.version_number <> d.version_number + 1 OR i.draft_version_token = d.draft_version_token))
                   OR (i.draft_status IN (N''applied'', N''discarded'') AND i.version_number <> d.version_number)
            )
                THROW 55603, ''Invalid criteria draft token or terminal transition.'', 1;
        END');

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_criteria_draft_versions_immutable
        ON dbo.myopp_criteria_draft_versions
        AFTER UPDATE
        AS
        BEGIN
            THROW 55604, ''Criteria draft versions are immutable.'', 1;
        END');

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_applied_criteria_snapshots_immutable
        ON dbo.myopp_applied_criteria_snapshots
        AFTER UPDATE, DELETE
        AS
        BEGIN
            THROW 55605, ''Applied criteria snapshots are immutable.'', 1;
        END');

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_criteria_commands_immutable
        ON dbo.myopp_criteria_commands
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM inserted)
                THROW 55606, ''Criteria command receipts are immutable.'', 1;
            IF EXISTS (SELECT 1 FROM deleted WHERE expires_at_utc > SYSUTCDATETIME())
                THROW 55607, ''Unexpired criteria command receipts cannot be removed.'', 1;
        END');

        INSERT dbo.schema_migrations
            (migration_id, description, application_version)
        VALUES
            (N'PS-MYOPP-002', N'My Opportunities C3 owner-scoped criteria drafts, immutable applied snapshots, and content-free command receipts', N'PeerSlate My Opportunities C3 v0.1');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
