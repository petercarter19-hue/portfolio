/* Verify PS-MYOPP-004 owner isolation, the search-execution lifecycle state
   machine, one immutable result snapshot per execution, reference-only
   ordered result entries, and the forbidden-scoring/copied-content scans. */
SET NOCOUNT ON;

BEGIN TRY
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-004')
        THROW 55760, 'PS-MYOPP-004 is not recorded in the schema ledger.', 1;

    IF OBJECT_ID(N'dbo.myopp_search_executions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_result_snapshots', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_result_entries', N'U') IS NULL
        THROW 55761, 'A required My Opportunities C4 table is missing.', 1;

    DECLARE @MemberTables TABLE (object_name sysname NOT NULL PRIMARY KEY);
    INSERT @MemberTables (object_name)
    VALUES
        (N'myopp_search_executions'),
        (N'myopp_result_snapshots'),
        (N'myopp_result_entries');

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
        THROW 55762, 'Every C4 search/result table must carry the non-null owner key.', 1;

    DECLARE @RequiredConstraints TABLE (constraint_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredConstraints (constraint_name)
    VALUES
        (N'CK_myopp_search_executions_data_class'),
        (N'CK_myopp_search_executions_state'),
        (N'CK_myopp_search_executions_path'),
        (N'CK_myopp_search_executions_coverage'),
        (N'CK_myopp_search_executions_checks_json'),
        (N'CK_myopp_search_executions_state_reason'),
        (N'CK_myopp_search_executions_timestamp_order'),
        (N'CK_myopp_result_snapshots_data_class'),
        (N'CK_myopp_result_snapshots_completeness'),
        (N'CK_myopp_result_snapshots_completeness_reason'),
        (N'CK_myopp_result_snapshots_coverage'),
        (N'CK_myopp_result_snapshots_disclosures_json'),
        (N'CK_myopp_result_snapshots_total_qualified'),
        (N'CK_myopp_result_snapshots_total_broader'),
        (N'CK_myopp_result_snapshots_lower_bound'),
        (N'CK_myopp_result_entries_data_class'),
        (N'CK_myopp_result_entries_partition'),
        (N'CK_myopp_result_entries_ordinal'),
        (N'CK_myopp_result_entries_gate_outcome'),
        (N'CK_myopp_result_entries_partition_gate'),
        (N'CK_myopp_result_entries_required_sum'),
        (N'CK_myopp_result_entries_preferred'),
        (N'CK_myopp_result_entries_attribution_json'),
        (N'CK_myopp_result_entries_ordering_inputs_json');
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
        THROW 55763, 'A required C4 search/result constraint is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_search_executions_state'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%submitted%'
          AND definition LIKE '%retrieving%'
          AND definition LIKE '%assessing%'
          AND definition LIKE '%ordering%'
          AND definition LIKE '%complete%'
          AND definition LIKE '%partial%'
          AND definition LIKE '%failed%'
          AND definition LIKE '%cancelled%'
    )
        -- Presence-only check (LIKE, not an exclusivity scan): this proves
        -- the eight canonical states are admitted, not that nothing else is.
        THROW 55764, 'The search execution state constraint must admit the canonical states.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_search_executions_state_reason'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%stale_criteria%'
          AND definition LIKE '%index_unavailable%'
          AND definition LIKE '%authorization_changed%'
          AND definition LIKE '%snapshot_persistence_failure%'
          AND definition LIKE '%timeout%'
          AND definition LIKE '%provider_failure%'
          AND definition LIKE '%index_failure%'
          AND definition LIKE '%budget_exhausted%'
          AND definition LIKE '%assessment_persistence_failure%'
          AND definition LIKE '%member_cancelled%'
          AND definition LIKE '%superseded%'
    )
        -- Presence-only check, as above: proves the four failed, five
        -- partial, and two cancel reason codes are admitted.
        THROW 55765, 'The search execution state/reason pairing constraint must admit the canonical reason codes.', 1;

    DECLARE @RequiredForeignKeys TABLE (foreign_key_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredForeignKeys (foreign_key_name)
    VALUES
        (N'FK_myopp_search_executions_user'),
        (N'FK_myopp_search_executions_snapshot_owner'),
        (N'FK_myopp_result_snapshots_user'),
        (N'FK_myopp_result_snapshots_execution_owner'),
        (N'FK_myopp_result_snapshots_criteria_owner'),
        (N'FK_myopp_result_entries_snapshot_owner'),
        (N'FK_myopp_result_entries_opportunity_class'),
        (N'FK_myopp_result_entries_requirement_version_class'),
        (N'FK_myopp_result_entries_source_version_class');
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
        THROW 55766, 'A required owner-safe C4 foreign key is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE required.foreign_key_name IN
        (
            N'FK_myopp_search_executions_snapshot_owner',
            N'FK_myopp_result_snapshots_execution_owner',
            N'FK_myopp_result_snapshots_criteria_owner',
            N'FK_myopp_result_entries_snapshot_owner'
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
        THROW 55767, 'A C4 member-to-member relationship is not fenced by the owner key.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE required.foreign_key_name IN
        (
            N'FK_myopp_result_entries_opportunity_class',
            N'FK_myopp_result_entries_requirement_version_class',
            N'FK_myopp_result_entries_source_version_class',
            -- MINOR 13: these member-to-member FKs are now ALSO paired on
            -- data_class (in addition to their own separate user_key
            -- pairing checked above), so they belong in both scans.
            N'FK_myopp_result_snapshots_execution_owner',
            N'FK_myopp_result_entries_snapshot_owner'
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
                AND parent_column.name = N'data_class'
                AND referenced_column.name = N'data_class'
          )
    )
        THROW 55768, 'A required C4 shared-side data_class relationship is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.myopp_result_snapshots')
          AND name = N'UQ_myopp_result_snapshots_execution'
          AND is_unique = 1
    )
        THROW 55769, 'The one-snapshot-per-execution uniqueness is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.myopp_result_entries')
          AND name = N'UQ_myopp_result_entries_order'
          AND is_unique = 1
    )
        THROW 55770, 'The per-snapshot ordinal uniqueness is missing.', 1;

    -- Exact key-column set, C5 55713/55714 idiom: precisely the three
    -- ordering columns, no more and no fewer.
    IF
    (
        SELECT COUNT(*)
        FROM sys.index_columns index_column_record
        WHERE index_column_record.object_id = OBJECT_ID(N'dbo.myopp_result_entries')
          AND index_column_record.index_id =
          (
              SELECT index_id FROM sys.indexes
              WHERE object_id = OBJECT_ID(N'dbo.myopp_result_entries') AND name = N'UQ_myopp_result_entries_order'
          )
          AND index_column_record.is_included_column = 0
    ) <> 3
        -- MINOR 11: distinct from 55770/55778 -- three separate assertions
        -- must never share a THROW number.
        THROW 55777, 'The result entry ordering uniqueness must have exactly three key columns.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM (VALUES (N'myopp_result_snapshot_id'), (N'partition_name'), (N'ordinal')) required(column_name)
        WHERE NOT EXISTS
        (
            SELECT 1
            FROM sys.index_columns index_column_record
            JOIN sys.columns column_record
              ON column_record.object_id = index_column_record.object_id
             AND column_record.column_id = index_column_record.column_id
            WHERE index_column_record.object_id = OBJECT_ID(N'dbo.myopp_result_entries')
              AND index_column_record.index_id =
              (
                  SELECT index_id FROM sys.indexes
                  WHERE object_id = OBJECT_ID(N'dbo.myopp_result_entries') AND name = N'UQ_myopp_result_entries_order'
              )
              AND index_column_record.is_included_column = 0
              AND column_record.name = required.column_name
        )
    )
        -- MINOR 11: distinct from 55770/55777.
        THROW 55778, 'The result entry ordering uniqueness must include the snapshot, partition, and ordinal columns.', 1;

    IF OBJECT_ID(N'dbo.trg_myopp_search_executions_transition_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_result_snapshots_immutable', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_result_entries_immutable', N'TR') IS NULL
        THROW 55771, 'A required C4 transition or immutability trigger is missing.', 1;

    DECLARE @RequiredIndexes TABLE (table_name sysname NOT NULL, index_name sysname NOT NULL, PRIMARY KEY (table_name, index_name));
    INSERT @RequiredIndexes (table_name, index_name)
    VALUES
        (N'myopp_search_executions', N'IX_myopp_search_executions_owner_state'),
        (N'myopp_search_executions', N'IX_myopp_search_executions_ttl'),
        (N'myopp_result_snapshots', N'IX_myopp_result_snapshots_owner'),
        (N'myopp_result_entries', N'IX_myopp_result_entries_snapshot');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredIndexes required
        WHERE NOT EXISTS
        (
            SELECT 1 FROM sys.indexes actual
            WHERE actual.object_id = OBJECT_ID(N'dbo.' + required.table_name)
              AND actual.name = required.index_name
        )
    )
        THROW 55772, 'A required C4 index is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredIndexes required
        WHERE required.index_name IN (N'IX_myopp_search_executions_owner_state', N'IX_myopp_result_snapshots_owner')
          AND NOT EXISTS
          (
              SELECT 1
              FROM sys.index_columns index_column_record
              JOIN sys.columns column_record
                ON column_record.object_id = index_column_record.object_id
               AND column_record.column_id = index_column_record.column_id
              WHERE index_column_record.object_id = OBJECT_ID(N'dbo.' + required.table_name)
                AND index_column_record.index_id = (SELECT index_id FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.' + required.table_name) AND name = required.index_name)
                AND index_column_record.key_ordinal = 1
                AND column_record.name = N'user_key'
          )
    )
        THROW 55773, 'An owner-scoped C4 index must lead on the owner key.', 1;

    DECLARE @ForbiddenContentColumns TABLE (column_name sysname NOT NULL PRIMARY KEY);
    INSERT @ForbiddenContentColumns (column_name)
    VALUES
        (N'title'), (N'employer'), (N'location'), (N'locations'), (N'description'),
        (N'compensation'), (N'content'), (N'body'), (N'excerpt'), (N'wording');
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN @ForbiddenContentColumns forbidden ON forbidden.column_name = column_record.name
        WHERE column_record.object_id = OBJECT_ID(N'dbo.myopp_result_entries')
    )
        THROW 55774, 'Result entries must remain references, never copies of listing content.', 1;

    DECLARE @ScoringPatterns TABLE (pattern nvarchar(40) NOT NULL PRIMARY KEY);
    INSERT @ScoringPatterns (pattern)
    VALUES (N'%score%'), (N'%probab%'), (N'%percent%'), (N'%rank%'), (N'%predict%'),
           (N'%confidence%'), (N'%match_rate%'), (N'%relevance%');
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN sys.tables table_record ON table_record.object_id = column_record.object_id
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        JOIN @ScoringPatterns pattern_record ON column_record.name LIKE pattern_record.pattern
        WHERE schema_record.name = N'dbo'
          AND table_record.name IN
          (N'myopp_search_executions', N'myopp_result_snapshots', N'myopp_result_entries')
    )
        THROW 55775, 'No C4 table may carry a score, probability, ranking, or relevance column.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.tables table_record
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        WHERE schema_record.name = N'dbo'
          AND (table_record.name LIKE N'%myopp%index%' OR table_record.name LIKE N'%myopp%projection%')
    )
        THROW 55776, 'No discovery index or projection table may exist; the index is a rebuildable external projection, never schema.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-MYOPP-004 C4 owner-fenced search executions, one immutable result snapshot per execution, and reference-only ordered result entries verified. No copied content; content-free by construction.' AS detail;
END TRY
BEGIN CATCH
    THROW;
END CATCH;
