/* PS-MYOPP-001 structural verification. It creates no fixture or member data. */
SET NOCOUNT ON;

BEGIN TRY
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
        THROW 55520, 'PS-MYOPP-001 is not recorded in the schema ledger.', 1;

    DECLARE @RequiredObjects TABLE (object_name sysname NOT NULL PRIMARY KEY, object_type char(2) NOT NULL);
    INSERT @RequiredObjects (object_name, object_type) VALUES
        (N'myopp_source_policies', N'U'), (N'myopp_source_receipts', N'U'),
        (N'myopp_source_listings', N'U'), (N'myopp_source_versions', N'U'),
        (N'myopp_source_version_receipt_links', N'U'),
        (N'myopp_canonical_opportunities', N'U'), (N'myopp_requirement_versions', N'U'),
        (N'myopp_requirement_items', N'U'), (N'myopp_canonical_field_attributions', N'U'),
        (N'myopp_canonical_events', N'U'), (N'myopp_content_tombstones', N'U'),
        (N'trg_myopp_source_policies_revision_guard', N'TR'),
        (N'trg_myopp_source_receipts_terminal_guard', N'TR'),
        (N'trg_myopp_source_listings_terminal_guard', N'TR'),
        (N'trg_myopp_source_versions_terminal_guard', N'TR'),
        (N'trg_myopp_requirement_versions_terminal_guard', N'TR'),
        (N'trg_myopp_requirement_items_terminal_guard', N'TR'),
        (N'trg_myopp_canonical_field_attributions_terminal_guard', N'TR'),
        (N'trg_myopp_source_version_receipt_links_immutable', N'TR'),
        (N'trg_myopp_content_tombstones_immutable', N'TR'),
        (N'trg_myopp_canonical_events_guard', N'TR'),
        (N'usp_myopp_tombstone_listing_content', N'P');
    IF EXISTS
    (
        SELECT 1 FROM @RequiredObjects required_object
        WHERE OBJECT_ID(N'dbo.' + required_object.object_name, required_object.object_type) IS NULL
    )
        THROW 55521, 'A required My Opportunities C2 object is missing.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN sys.tables table_record ON table_record.object_id = column_record.object_id
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        WHERE schema_record.name = N'dbo' AND table_record.name LIKE N'myopp[_]%'
          AND column_record.name IN (N'user_key', N'owner_profile_id', N'owner_user_id')
    )
        THROW 55522, 'C2 shared-side schema contains a prohibited member identity column.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM sys.foreign_keys foreign_key_record
        JOIN sys.tables child_table ON child_table.object_id = foreign_key_record.parent_object_id
        JOIN sys.schemas child_schema ON child_schema.schema_id = child_table.schema_id
        JOIN sys.tables parent_table ON parent_table.object_id = foreign_key_record.referenced_object_id
        JOIN sys.schemas parent_schema ON parent_schema.schema_id = parent_table.schema_id
        WHERE child_schema.name = N'dbo' AND child_table.name LIKE N'myopp[_]%'
          AND (parent_schema.name <> N'dbo' OR parent_table.name NOT LIKE N'myopp[_]%')
    )
        THROW 55523, 'C2 shared-side schema has a forbidden cross-schema or external foreign-key dependency.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM sys.tables table_record
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        WHERE schema_record.name = N'dbo' AND table_record.name LIKE N'myopp[_]%'
          AND NOT EXISTS
          (
              SELECT 1 FROM sys.columns column_record
              WHERE column_record.object_id = table_record.object_id
                AND column_record.name = N'data_class'
          )
    )
        THROW 55524, 'A C2 shared-side table is missing its fixture/production class boundary.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM sys.foreign_keys foreign_key_record
        JOIN sys.tables child_table ON child_table.object_id = foreign_key_record.parent_object_id
        JOIN sys.schemas child_schema ON child_schema.schema_id = child_table.schema_id
        JOIN sys.tables parent_table ON parent_table.object_id = foreign_key_record.referenced_object_id
        JOIN sys.schemas parent_schema ON parent_schema.schema_id = parent_table.schema_id
        WHERE child_schema.name = N'dbo' AND parent_schema.name = N'dbo'
          AND child_table.name LIKE N'myopp[_]%' AND parent_table.name LIKE N'myopp[_]%'
          AND NOT EXISTS
          (
              SELECT 1
              FROM sys.foreign_key_columns foreign_key_column
              JOIN sys.columns child_column
                ON child_column.object_id = foreign_key_column.parent_object_id
               AND child_column.column_id = foreign_key_column.parent_column_id
              JOIN sys.columns parent_column
                ON parent_column.object_id = foreign_key_column.referenced_object_id
               AND parent_column.column_id = foreign_key_column.referenced_column_id
              WHERE foreign_key_column.constraint_object_id = foreign_key_record.object_id
                AND child_column.name = N'data_class' AND parent_column.name = N'data_class'
          )
    )
        THROW 55525, 'A C2 shared-side foreign key permits a cross-class join.', 1;
    IF NOT EXISTS
    (
        SELECT 1
        FROM sys.check_constraints check_constraint
        JOIN sys.tables table_record ON table_record.object_id = check_constraint.parent_object_id
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        -- SQL Server catalog output brackets identifiers and can retain layout
        -- whitespace. Normalize only that formatting, then require the exact
        -- two-target AND expression rather than a permissive text fragment.
        CROSS APPLY
        (
            VALUES (LOWER(check_constraint.definition))
        ) catalog_constraint(definition_text)
        CROSS APPLY
        (
            VALUES
            (
                REPLACE(REPLACE(catalog_constraint.definition_text, N'[', N''), N']', N'')
            )
        ) unbracketed_constraint(definition_text)
        CROSS APPLY
        (
            VALUES
            (
                REPLACE(REPLACE(REPLACE(REPLACE(unbracketed_constraint.definition_text, N' ', N''), NCHAR(9), N''), NCHAR(10), N''), NCHAR(13), N'')
            )
        ) compact_constraint(definition_text)
        CROSS APPLY
        (
            VALUES
            (
                REPLACE(REPLACE(compact_constraint.definition_text, N'(', N''), N')', N'')
            )
        ) normalized_constraint(normalized_definition)
        WHERE schema_record.name = N'dbo'
          AND table_record.name = N'myopp_content_tombstones'
          AND check_constraint.name = N'CK_myopp_content_tombstones_target'
          AND normalized_constraint.normalized_definition = N'myopp_source_receipt_idisnotnullandmyopp_source_version_idisnotnull'
    )
        THROW 55526, 'A C2 content tombstone must pair one receipt with one source version.', 1;

    DECLARE @RequiredNotNullColumns TABLE
    (
        table_name sysname NOT NULL,
        column_name sysname NOT NULL,
        PRIMARY KEY (table_name, column_name)
    );
    INSERT @RequiredNotNullColumns (table_name, column_name) VALUES
        (N'myopp_source_policies', N'allowed_actions_json'),
        (N'myopp_source_policies', N'retained_source_fields_json'),
        (N'myopp_source_version_receipt_links', N'myopp_source_version_id'),
        (N'myopp_source_version_receipt_links', N'myopp_source_receipt_id'),
        (N'myopp_source_version_receipt_links', N'data_class'),
        (N'myopp_content_tombstones', N'myopp_source_receipt_id'),
        (N'myopp_content_tombstones', N'myopp_source_version_id'),
        (N'myopp_content_tombstones', N'data_class'),
        (N'myopp_content_tombstones', N'myopp_source_policy_id'),
        (N'myopp_content_tombstones', N'policy_version'),
        (N'myopp_content_tombstones', N'disposition'),
        (N'myopp_content_tombstones', N'removal_reason'),
        (N'myopp_content_tombstones', N'actor_ref'),
        (N'myopp_content_tombstones', N'retained_source_fields_json'),
        (N'myopp_content_tombstones', N'actioned_at_utc');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredNotNullColumns required_column
        LEFT JOIN sys.tables table_record
          ON table_record.name = required_column.table_name
        LEFT JOIN sys.schemas schema_record
          ON schema_record.schema_id = table_record.schema_id
         AND schema_record.name = N'dbo'
        LEFT JOIN sys.columns column_record
          ON column_record.object_id = table_record.object_id
         AND column_record.name = required_column.column_name
        WHERE column_record.column_id IS NULL OR column_record.is_nullable <> 0
    )
        THROW 55527, 'A required C2 terminal or policy column is missing or nullable.', 1;

    DECLARE @RequiredConstraints TABLE (constraint_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredConstraints (constraint_name) VALUES
        (N'CK_myopp_source_policies_allowed_actions_json'),
        (N'CK_myopp_source_policies_retained_fields_json'),
        (N'CK_myopp_source_policies_strict_false_retention'),
        (N'CK_myopp_source_receipts_tombstone'),
        (N'CK_myopp_source_listings_tombstone'),
        (N'CK_myopp_source_versions_tombstone'),
        (N'CK_myopp_requirement_versions_tombstone'),
        (N'CK_myopp_requirement_items_tombstone'),
        (N'CK_myopp_canonical_field_attributions_tombstone'),
        (N'UQ_myopp_source_version_receipt_links_pair_class'),
        (N'UQ_myopp_source_version_receipt_links_receipt_class'),
        (N'FK_myopp_source_version_receipt_links_version_class'),
        (N'FK_myopp_source_version_receipt_links_receipt_class'),
        (N'UQ_myopp_content_tombstones_pair_class'),
        (N'FK_myopp_content_tombstones_pair_link_class'),
        (N'FK_myopp_content_tombstones_receipt_class'),
        (N'FK_myopp_content_tombstones_version_class'),
        (N'FK_myopp_content_tombstones_policy_class');
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredConstraints required_constraint
        WHERE OBJECT_ID(N'dbo.' + required_constraint.constraint_name) IS NULL
    )
        THROW 55528, 'A required C2 terminal, link, or paired-tombstone constraint is missing.', 1;

    DECLARE @RequiredFilteredIndexes TABLE
    (
        table_name sysname NOT NULL,
        index_name sysname NOT NULL PRIMARY KEY,
        key_columns nvarchar(500) NOT NULL,
        normalized_filter nvarchar(500) NOT NULL
    );
    INSERT @RequiredFilteredIndexes (table_name, index_name, key_columns, normalized_filter) VALUES
        (N'myopp_source_listings', N'UX_myopp_source_listings_active_source_reference', N'data_class|source_id|external_reference', N'source_idisnotnullandexternal_referenceisnotnull'),
        (N'myopp_source_versions', N'UX_myopp_source_versions_active_listing_hash', N'myopp_source_listing_id|data_class|content_sha256', N'content_sha256isnotnull'),
        (N'myopp_requirement_versions', N'UX_myopp_requirement_versions_active_opportunity_fingerprint', N'myopp_canonical_opportunity_id|data_class|clause_fingerprint', N'clause_fingerprintisnotnull'),
        (N'myopp_requirement_items', N'UX_myopp_requirement_items_active_version_ordinal', N'myopp_requirement_version_id|data_class|ordinal', N'ordinalisnotnull'),
        (N'myopp_canonical_field_attributions', N'UX_myopp_canonical_field_attributions_active_opportunity_field', N'myopp_canonical_opportunity_id|data_class|field_name', N'field_nameisnotnull');
    DECLARE @FilteredIndexFacts TABLE
    (
        table_name sysname NOT NULL,
        index_name sysname NOT NULL PRIMARY KEY,
        is_unique bit NOT NULL,
        has_filter bit NOT NULL,
        key_columns nvarchar(500) NOT NULL,
        normalized_filter nvarchar(500) NULL
    );
    INSERT @FilteredIndexFacts (table_name, index_name, is_unique, has_filter, key_columns, normalized_filter)
    SELECT table_record.name, index_record.name, index_record.is_unique, index_record.has_filter,
           STRING_AGG(column_record.name, N'|') WITHIN GROUP (ORDER BY index_column.key_ordinal),
           normalized_filter.normalized_definition
    FROM sys.indexes index_record
    JOIN sys.tables table_record ON table_record.object_id = index_record.object_id
    JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
    JOIN sys.index_columns index_column
      ON index_column.object_id = index_record.object_id AND index_column.index_id = index_record.index_id
     AND index_column.is_included_column = 0
    JOIN sys.columns column_record
      ON column_record.object_id = index_column.object_id AND column_record.column_id = index_column.column_id
    CROSS APPLY (VALUES (LOWER(index_record.filter_definition))) raw_filter(definition_text)
    CROSS APPLY (VALUES (REPLACE(REPLACE(raw_filter.definition_text, N'[', N''), N']', N''))) unbracketed_filter(definition_text)
    CROSS APPLY (VALUES (REPLACE(REPLACE(REPLACE(REPLACE(unbracketed_filter.definition_text, N' ', N''), NCHAR(9), N''), NCHAR(10), N''), NCHAR(13), N''))) compact_filter(definition_text)
    CROSS APPLY (VALUES (REPLACE(REPLACE(compact_filter.definition_text, N'(', N''), N')', N''))) normalized_filter(normalized_definition)
    WHERE schema_record.name = N'dbo' AND table_record.name LIKE N'myopp[_]%'
      AND index_record.name IS NOT NULL
    GROUP BY table_record.name, index_record.name, index_record.is_unique, index_record.has_filter, normalized_filter.normalized_definition;
    IF EXISTS
    (
        SELECT 1
        FROM @RequiredFilteredIndexes required_index
        LEFT JOIN @FilteredIndexFacts index_fact ON index_fact.index_name = required_index.index_name
        WHERE index_fact.index_name IS NULL
           OR index_fact.table_name <> required_index.table_name
           OR index_fact.is_unique <> 1 OR index_fact.has_filter <> 1
           OR index_fact.key_columns <> required_index.key_columns
           OR index_fact.normalized_filter <> required_index.normalized_filter
    )
        THROW 55529, 'A required C2 active-row filtered unique index is missing or malformed.', 1;

    IF NOT EXISTS
    (
        SELECT 1
        FROM sys.sql_modules module_record
        JOIN sys.objects object_record ON object_record.object_id = module_record.object_id
        WHERE object_record.schema_id = SCHEMA_ID(N'dbo')
          AND object_record.name = N'trg_myopp_source_policies_revision_guard'
          AND module_record.definition LIKE N'%OPENJSON(i.allowed_actions_json)%'
          AND module_record.definition LIKE N'%OPENJSON(prior.allowed_actions_json)%'
          AND module_record.definition LIKE N'%N''acquire'', N''ai'', N''cache'', N''display'', N''export''%'
          AND module_record.definition LIKE N'%prior.policy_version = i.policy_version - 1%'
    )
        THROW 55530, 'The C2 source policy action/revision guard is incomplete.', 1;
    IF NOT EXISTS
    (
        SELECT 1
        FROM sys.sql_modules module_record
        JOIN sys.objects object_record ON object_record.object_id = module_record.object_id
        WHERE object_record.schema_id = SCHEMA_ID(N'dbo')
          AND object_record.name = N'usp_myopp_tombstone_listing_content'
          AND module_record.definition LIKE N'%BEGIN TRANSACTION%'
          AND module_record.definition LIKE N'%myopp_source_version_receipt_links%'
          AND module_record.definition LIKE N'%myopp_content_tombstones%'
          AND module_record.definition LIKE N'%myopp_requirement_items%'
          AND module_record.definition LIKE N'%myopp_canonical_field_attributions%'
          AND module_record.definition LIKE N'%content_tombstoned%'
    )
        THROW 55531, 'The C2 atomic terminal takedown procedure is incomplete.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-MYOPP-001 C2 objects, policy actions, terminal guards, paired tombstones, filtered active identities, ledger row, and class-safe dbo-only foreign-key dependencies verified.' AS detail;
END TRY
BEGIN CATCH
    THROW;
END CATCH;
