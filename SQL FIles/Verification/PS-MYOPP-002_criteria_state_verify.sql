/* Verify PS-MYOPP-002 owner isolation, immutable snapshots, and content-free command receipts. */
SET NOCOUNT ON;

BEGIN TRY
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002')
        THROW 55640, 'PS-MYOPP-002 is not recorded in the schema ledger.', 1;

    IF OBJECT_ID(N'dbo.myopp_criteria_drafts', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_criteria_draft_versions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_applied_criteria_snapshots', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_criteria_commands', N'U') IS NULL
        THROW 55641, 'A required My Opportunities C3 table is missing.', 1;

    DECLARE @MemberTables TABLE (object_name sysname NOT NULL PRIMARY KEY);
    INSERT @MemberTables (object_name)
    VALUES
        (N'myopp_criteria_drafts'),
        (N'myopp_criteria_draft_versions'),
        (N'myopp_applied_criteria_snapshots'),
        (N'myopp_criteria_commands');

    IF EXISTS
    (
        SELECT 1
        FROM @MemberTables required
        WHERE NOT EXISTS
        (
            SELECT 1
            FROM sys.columns column_record
            JOIN sys.tables table_record ON table_record.object_id = column_record.object_id
            JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
            WHERE schema_record.name = N'dbo'
              AND table_record.name = required.object_name
              AND column_record.name = N'user_key'
              AND TYPE_NAME(column_record.user_type_id) = N'nvarchar'
              AND column_record.max_length = 600
              AND column_record.is_nullable = 0
        )
    )
        THROW 55642, 'Every C3 criteria table must carry the non-null owner key.', 1;

    DECLARE @RequiredConstraints TABLE (constraint_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredConstraints (constraint_name)
    VALUES
        (N'CK_myopp_criteria_drafts_status'),
        (N'CK_myopp_criteria_drafts_terminal'),
        (N'CK_myopp_criteria_drafts_criteria_json'),
        (N'CK_myopp_criteria_drafts_filters_json'),
        (N'CK_myopp_criteria_drafts_clarification_json'),
        (N'CK_myopp_criteria_draft_versions_criteria_json'),
        (N'CK_myopp_applied_criteria_snapshots_criteria_json'),
        (N'CK_myopp_criteria_commands_idempotency_hash'),
        (N'CK_myopp_criteria_commands_input_hash'),
        (N'CK_myopp_criteria_commands_result'),
        (N'CK_myopp_criteria_commands_expiry');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredConstraints required
        WHERE NOT EXISTS
        (
            SELECT 1 FROM sys.check_constraints actual
            WHERE actual.name = required.constraint_name
              AND SCHEMA_NAME(actual.schema_id) = N'dbo'
        )
    )
        THROW 55643, 'A required C3 criteria constraint is missing.', 1;

    DECLARE @RequiredForeignKeys TABLE (foreign_key_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredForeignKeys (foreign_key_name)
    VALUES
        (N'FK_myopp_criteria_drafts_user'),
        (N'FK_myopp_criteria_drafts_parent_snapshot_owner'),
        (N'FK_myopp_criteria_drafts_terminal_snapshot_owner'),
        (N'FK_myopp_criteria_draft_versions_draft_owner'),
        (N'FK_myopp_applied_criteria_snapshots_user'),
        (N'FK_myopp_applied_criteria_snapshots_source_draft_owner'),
        (N'FK_myopp_applied_criteria_snapshots_previous_owner'),
        (N'FK_myopp_criteria_commands_user'),
        (N'FK_myopp_criteria_commands_draft_owner'),
        (N'FK_myopp_criteria_commands_version_owner'),
        (N'FK_myopp_criteria_commands_snapshot_owner');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE NOT EXISTS
        (
            SELECT 1 FROM sys.foreign_keys actual
            WHERE actual.name = required.foreign_key_name
              AND SCHEMA_NAME(actual.schema_id) = N'dbo'
        )
    )
        THROW 55644, 'A required owner-safe C3 foreign key is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE required.foreign_key_name NOT IN
        (
            N'FK_myopp_criteria_drafts_user',
            N'FK_myopp_applied_criteria_snapshots_user',
            N'FK_myopp_criteria_commands_user'
        )
          AND NOT EXISTS
          (
              SELECT 1
              FROM sys.foreign_keys foreign_key_record
              JOIN sys.foreign_key_columns member_column
                ON member_column.constraint_object_id = foreign_key_record.object_id
              JOIN sys.columns parent_column
                ON parent_column.object_id = member_column.parent_object_id
               AND parent_column.column_id = member_column.parent_column_id
              JOIN sys.columns referenced_column
                ON referenced_column.object_id = member_column.referenced_object_id
               AND referenced_column.column_id = member_column.referenced_column_id
              WHERE foreign_key_record.name = required.foreign_key_name
                AND SCHEMA_NAME(foreign_key_record.schema_id) = N'dbo'
                AND parent_column.name = N'user_key'
                AND referenced_column.name = N'user_key'
          )
    )
        THROW 55645, 'A C3 relationship is not fenced by the owner key.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        WHERE column_record.object_id = OBJECT_ID(N'dbo.myopp_criteria_commands')
          AND column_record.name IN
          (
              N'idempotency_key', N'request_text', N'criteria_json',
              N'direct_filters_json', N'clarification_json', N'member_message'
          )
    )
        THROW 55646, 'C3 command receipts must remain content-free hashes and references.', 1;

    IF COL_LENGTH(N'dbo.myopp_criteria_commands', N'idempotency_key_sha256') IS NULL
       OR COL_LENGTH(N'dbo.myopp_criteria_commands', N'canonical_input_sha256') IS NULL
       OR COL_LENGTH(N'dbo.myopp_criteria_commands', N'expires_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.myopp_criteria_drafts', N'draft_version_token') IS NULL
       OR COL_LENGTH(N'dbo.myopp_criteria_drafts', N'terminal_execution_key') IS NULL
       OR COL_LENGTH(N'dbo.myopp_criteria_drafts', N'terminal_receipt_at_utc') IS NULL
        THROW 55647, 'A required C3 concurrency or terminal-receipt column is missing.', 1;

    IF OBJECT_ID(N'dbo.trg_myopp_criteria_drafts_transition_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_criteria_draft_versions_immutable', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_applied_criteria_snapshots_immutable', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_criteria_commands_immutable', N'TR') IS NULL
        THROW 55648, 'A required C3 transition or immutability trigger is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.myopp_criteria_commands')
          AND name = N'UQ_myopp_criteria_commands_owner_key'
          AND is_unique = 1
    )
        THROW 55649, 'Owner-scoped C3 idempotency uniqueness is missing.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-MYOPP-002 C3 owner-scoped drafts, immutable versions/snapshots, token transitions, terminal receipts, content-free idempotency, and ledger row verified.' AS detail;
END TRY
BEGIN CATCH
    THROW;
END CATCH;
