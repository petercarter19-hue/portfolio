/* Verify PS-MYOPP-005 owner isolation, the closed save/remove/undo machine
   with terminal removed rows, one active save per member and opportunity,
   owner-fenced Slate links with one active link per member and opportunity,
   and the forbidden-scoring/copied-content/overlay-column scans. */
SET NOCOUNT ON;

BEGIN TRY
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-005')
        THROW 55810, 'PS-MYOPP-005 is not recorded in the schema ledger.', 1;

    IF OBJECT_ID(N'dbo.myopp_saved_opportunities', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_slate_links', N'U') IS NULL
        THROW 55811, 'A required My Opportunities C6 table is missing.', 1;

    DECLARE @MemberTables TABLE (object_name sysname NOT NULL PRIMARY KEY);
    INSERT @MemberTables (object_name)
    VALUES
        (N'myopp_saved_opportunities'),
        (N'myopp_slate_links');

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
        THROW 55812, 'Every C6 saves/links table must carry the non-null owner key.', 1;

    DECLARE @RequiredConstraints TABLE (constraint_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredConstraints (constraint_name)
    VALUES
        (N'CK_myopp_saved_opportunities_data_class'),
        (N'CK_myopp_saved_opportunities_state'),
        (N'CK_myopp_saved_opportunities_state_timestamps'),
        (N'CK_myopp_saved_opportunities_removal_after_save'),
        (N'CK_myopp_slate_links_data_class'),
        (N'CK_myopp_slate_links_state'),
        (N'CK_myopp_slate_links_created_from'),
        (N'CK_myopp_slate_links_state_timestamps'),
        (N'CK_myopp_slate_links_workspace_ref');
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
        THROW 55813, 'A required C6 saves/links constraint is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_saved_opportunities_state'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%saved%'
          AND definition LIKE '%removing%'
          AND definition LIKE '%removed%'
    )
        -- Presence-only check (LIKE, not an exclusivity scan): proves the
        -- three canonical save states are admitted.
        THROW 55814, 'The saved opportunity state constraint must admit the canonical states.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_slate_links_state'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%linked%'
          AND definition LIKE '%unlinked%'
    )
        THROW 55815, 'The Slate link state constraint must admit the canonical states.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_slate_links_created_from'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%result%'
          AND definition LIKE '%saved%'
    )
        THROW 55816, 'The Slate link created_from constraint must admit result and saved.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM (VALUES (N'CK_myopp_saved_opportunities_data_class'), (N'CK_myopp_slate_links_data_class'))
            required(constraint_name)
        WHERE NOT EXISTS
        (
            SELECT 1 FROM sys.check_constraints actual
            WHERE actual.name = required.constraint_name
              AND SCHEMA_NAME(actual.schema_id) = N'dbo'
              AND actual.definition LIKE '%fixture%'
              AND actual.definition LIKE '%production%'
        )
    )
        THROW 55817, 'Every C6 data_class constraint must admit fixture and production.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_saved_opportunities_state_timestamps'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%removal_requested%'
          AND definition LIKE '%removed_at%'
    )
    OR NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_slate_links_state_timestamps'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%unlinked_at%'
    )
        THROW 55818, 'A required C6 state/timestamp pairing constraint is missing its required timestamp term(s).', 1;

    -- IMPORTANT 4: filter_definition byte-equality is fragile (SQL Server's
    -- own pretty-printing of a filtered-index predicate is not guaranteed
    -- byte-stable). Adopt PS-MYOPP-001's normalization idiom instead:
    -- lowercase, strip brackets/parens/whitespace, then compare.
    DECLARE @RequiredFilteredIndexes TABLE
    (
        table_name sysname NOT NULL,
        index_name sysname NOT NULL PRIMARY KEY,
        normalized_filter nvarchar(200) NOT NULL
    );
    INSERT @RequiredFilteredIndexes (table_name, index_name, normalized_filter) VALUES
        (N'myopp_saved_opportunities', N'UX_myopp_saved_opportunities_active', N'state<>n''removed'''),
        (N'myopp_slate_links', N'UX_myopp_slate_links_active', N'state=n''linked''');
    DECLARE @FilteredIndexFacts TABLE
    (
        index_name sysname NOT NULL PRIMARY KEY,
        table_name sysname NOT NULL,
        is_unique bit NOT NULL,
        has_filter bit NOT NULL,
        normalized_filter nvarchar(200) NULL
    );
    INSERT @FilteredIndexFacts (index_name, table_name, is_unique, has_filter, normalized_filter)
    SELECT index_record.name, table_record.name, index_record.is_unique, index_record.has_filter,
           normalized_filter.normalized_definition
    FROM sys.indexes index_record
    JOIN sys.tables table_record ON table_record.object_id = index_record.object_id
    JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
    CROSS APPLY (VALUES (LOWER(ISNULL(index_record.filter_definition, N'')))) raw_filter(definition_text)
    CROSS APPLY (VALUES (REPLACE(REPLACE(raw_filter.definition_text, N'[', N''), N']', N''))) unbracketed_filter(definition_text)
    CROSS APPLY (VALUES (REPLACE(REPLACE(REPLACE(REPLACE(unbracketed_filter.definition_text, N' ', N''), NCHAR(9), N''), NCHAR(10), N''), NCHAR(13), N''))) compact_filter(definition_text)
    CROSS APPLY (VALUES (REPLACE(REPLACE(compact_filter.definition_text, N'(', N''), N')', N''))) normalized_filter(normalized_definition)
    WHERE schema_record.name = N'dbo'
      AND table_record.name IN (N'myopp_saved_opportunities', N'myopp_slate_links')
      AND index_record.name IN (N'UX_myopp_saved_opportunities_active', N'UX_myopp_slate_links_active');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredFilteredIndexes required_index
        LEFT JOIN @FilteredIndexFacts index_fact ON index_fact.index_name = required_index.index_name
        WHERE index_fact.index_name IS NULL
           OR index_fact.table_name <> required_index.table_name
           OR index_fact.is_unique <> 1 OR index_fact.has_filter <> 1
           OR index_fact.normalized_filter <> required_index.normalized_filter
    )
        THROW 55819, 'A required one-active-row-per-member-and-opportunity filtered unique index is missing or malformed.', 1;

    IF OBJECT_ID(N'dbo.trg_myopp_saved_opportunities_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_slate_links_guard', N'TR') IS NULL
       OR EXISTS
       (
           SELECT 1 FROM sys.triggers
           WHERE parent_id IN (OBJECT_ID(N'dbo.myopp_saved_opportunities'), OBJECT_ID(N'dbo.myopp_slate_links'))
             AND is_disabled = 1
       )
        THROW 55820, 'A required C6 guard trigger is missing or disabled.', 1;

    DECLARE @RequiredForeignKeys TABLE (foreign_key_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredForeignKeys (foreign_key_name)
    VALUES
        (N'FK_myopp_saved_opportunities_user'),
        (N'FK_myopp_saved_opportunities_opportunity_class'),
        (N'FK_myopp_saved_opportunities_reviewed_version_class'),
        (N'FK_myopp_slate_links_user'),
        (N'FK_myopp_slate_links_opportunity_class'),
        (N'FK_myopp_slate_links_handoff_version_class');
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
    OR EXISTS
    (
        -- No C6 table FK may reference anything outside the owner/shared-
        -- truth allowlist: app_users (owner fencing) and the two shared
        -- canonical tables C6 references by (id, data_class).
        SELECT 1
        FROM sys.foreign_keys foreign_key_record
        JOIN sys.tables parent_table ON parent_table.object_id = foreign_key_record.parent_object_id
        JOIN sys.schemas parent_schema ON parent_schema.schema_id = parent_table.schema_id
        JOIN sys.tables referenced_table ON referenced_table.object_id = foreign_key_record.referenced_object_id
        JOIN sys.schemas referenced_schema ON referenced_schema.schema_id = referenced_table.schema_id
        WHERE parent_schema.name = N'dbo'
          AND parent_table.name IN (N'myopp_saved_opportunities', N'myopp_slate_links')
          AND NOT
          (
              -- MINOR 13: schema-qualify the allowlist comparison -- a
              -- same-named table in a DIFFERENT schema must not silently
              -- satisfy this scan.
              referenced_schema.name = N'dbo'
              AND referenced_table.name IN (N'app_users', N'myopp_canonical_opportunities', N'myopp_source_versions')
          )
    )
        THROW 55821, 'A required owner-safe C6 foreign key is missing, or a C6 table references a table outside the allowed owner/shared-truth set.', 1;

    DECLARE @ForbiddenColumns TABLE (pattern nvarchar(40) NOT NULL PRIMARY KEY);
    INSERT @ForbiddenColumns (pattern)
    VALUES
        (N'%title%'), (N'%employer%'), (N'%company%'), (N'%description%'), (N'%content%'),
        (N'%text%'), (N'%overlay%'), (N'%score%'), (N'%probability%'), (N'%rank%'), (N'%relevance%');
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN sys.tables table_record ON table_record.object_id = column_record.object_id
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        JOIN @ForbiddenColumns forbidden ON column_record.name LIKE forbidden.pattern
        WHERE schema_record.name = N'dbo'
          AND table_record.name IN (N'myopp_saved_opportunities', N'myopp_slate_links')
    )
        -- Reference-only and derived-overlay discipline made catalog-
        -- checkable: no C6 table may carry copied content, a persisted
        -- overlay, or any score/probability/rank/relevance column.
        THROW 55822, 'A C6 table carries a forbidden copied-content, overlay, or scoring column.', 1;

    DECLARE @RequiredUniques TABLE (table_name sysname NOT NULL, constraint_name sysname NOT NULL, PRIMARY KEY (table_name, constraint_name));
    INSERT @RequiredUniques (table_name, constraint_name)
    VALUES
        (N'myopp_saved_opportunities', N'UQ_myopp_saved_opportunities_id_user'),
        (N'myopp_saved_opportunities', N'UQ_myopp_saved_opportunities_id_user_class'),
        (N'myopp_slate_links', N'UQ_myopp_slate_links_id_user'),
        (N'myopp_slate_links', N'UQ_myopp_slate_links_id_user_class');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredUniques required
        WHERE NOT EXISTS
        (
            SELECT 1 FROM sys.key_constraints actual
            WHERE actual.name = required.constraint_name
              AND SCHEMA_NAME(actual.schema_id) = N'dbo'
              AND actual.parent_object_id = OBJECT_ID(N'dbo.' + required.table_name)
              AND actual.type = N'UQ'
        )
    )
        THROW 55823, 'A required C6 id/user/data_class composite uniqueness (the downstream composite-FK pairing surface) is missing.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-MYOPP-005 C6 owner-fenced saved opportunities (closed save/remove/undo machine, terminal removed rows, one active save per member and opportunity) and owner-fenced Slate links (one active link per member and opportunity, unlinked history labels) verified. Reference-only; no overlay, score, or copied-content column; content-free by construction.' AS detail;
END TRY
BEGIN CATCH
    THROW;
END CATCH;
