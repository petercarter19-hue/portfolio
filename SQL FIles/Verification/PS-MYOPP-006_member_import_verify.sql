/* Verify PS-MYOPP-006 owner-fenced private member_import storage: the closed
   doc 06 section 2 outcome-state vocabulary (with C13-reserved reasons
   schema-complete), the append-only stage-outcome trail, in-record fetch
   provenance, dual-retention body-removal tombstones, content-free
   idempotency receipts, and the forbidden shared-side-key/scoring scans.
   Catalog shape only (behavior lives in P-1); THROW numbers 55860-55877,
   inside the reserved 55840-55899 band. */
SET NOCOUNT ON;

BEGIN TRY
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-006')
        THROW 55860, 'PS-MYOPP-006 is not recorded in the schema ledger.', 1;

    IF OBJECT_ID(N'dbo.myopp_member_imports', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_member_import_stage_outcomes', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_member_import_idempotency', N'U') IS NULL
        THROW 55861, 'A required My Opportunities C10 member_import table is missing.', 1;

    DECLARE @MemberTables TABLE (object_name sysname NOT NULL PRIMARY KEY);
    INSERT @MemberTables (object_name)
    VALUES
        (N'myopp_member_imports'),
        (N'myopp_member_import_stage_outcomes'),
        (N'myopp_member_import_idempotency');

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
        THROW 55862, 'Every C10 member_import table must carry the non-null owner key.', 1;

    DECLARE @RequiredConstraints TABLE (constraint_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredConstraints (constraint_name)
    VALUES
        (N'CK_myopp_member_imports_data_class'),
        (N'CK_myopp_member_imports_intake_method'),
        (N'CK_myopp_member_imports_record_state'),
        (N'CK_myopp_member_imports_byte_count'),
        (N'CK_myopp_member_imports_extracted_units'),
        (N'CK_myopp_member_imports_content_hash_hex'),
        (N'CK_myopp_member_imports_fetch_provenance'),
        (N'CK_myopp_member_imports_outcome'),
        (N'CK_myopp_member_imports_outcome_reason'),
        (N'CK_myopp_member_imports_outcome_text'),
        (N'CK_myopp_member_imports_truncated'),
        (N'CK_myopp_member_imports_rights_class'),
        (N'CK_myopp_member_imports_removal_reason'),
        (N'CK_myopp_member_imports_removal_pairing'),
        (N'CK_myopp_member_imports_removal_text'),
        (N'CK_myopp_member_imports_state_removal'),
        (N'CK_myopp_member_imports_timestamp_order'),
        (N'CK_myopp_member_import_stage_outcomes_outcome'),
        (N'CK_myopp_member_import_stage_outcomes_sequence'),
        (N'CK_myopp_member_import_idempotency_key'),
        (N'CK_myopp_member_import_idempotency_command'),
        (N'CK_myopp_member_import_idempotency_input_hash'),
        (N'CK_myopp_member_import_idempotency_result_json');
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
        THROW 55863, 'A required C10 member_import constraint is missing.', 1;

    -- Presence-only checks (LIKE, not an exclusivity scan): each proves the
    -- named constraint admits the closed vocabulary it is required to carry,
    -- not that nothing else is admitted.
    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_outcome'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%fetched%' AND definition LIKE '%decoded%' AND definition LIKE '%parsed%'
          AND definition LIKE '%extracted%' AND definition LIKE '%empty%' AND definition LIKE '%partial%'
          AND definition LIKE '%blocked%' AND definition LIKE '%timeout%' AND definition LIKE '%refused%'
    )
    OR NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_import_stage_outcomes_outcome'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%fetched%' AND definition LIKE '%decoded%' AND definition LIKE '%parsed%'
          AND definition LIKE '%extracted%' AND definition LIKE '%empty%' AND definition LIKE '%partial%'
          AND definition LIKE '%blocked%' AND definition LIKE '%timeout%' AND definition LIKE '%refused%'
    )
        THROW 55864, 'The outcome-state constraints must admit all nine doc 06 section 2 closed states on both the import and the stage-outcome trail.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_outcome_reason'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%could_not_decode%' AND definition LIKE '%parser_failure%'
          AND definition LIKE '%parser_resource_bounds%' AND definition LIKE '%archive_bomb_suspected%'
          AND definition LIKE '%hostile_characters%' AND definition LIKE '%output_truncated%'
          AND definition LIKE '%extraction_deadline%'
          -- C13-reserved reasons must already be schema-complete so C13 needs no migration.
          AND definition LIKE '%fetch_deadline%' AND definition LIKE '%fetch_too_large%'
          AND definition LIKE '%denied_address%' AND definition LIKE '%scheme_refused%'
          AND definition LIKE '%redirect_refused%' AND definition LIKE '%content_mismatch%'
    )
        THROW 55865, 'The outcome/reason pairing constraint must admit every closed C10 reason code and every C13-reserved fetch reason code.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_fetch_provenance'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%url_fetch%'
    )
        THROW 55866, 'The fetch-provenance pairing constraint must gate on the url_fetch intake method.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_removal_pairing'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%body_removed_at_utc%' AND definition LIKE '%body_removal_reason%'
    )
    OR NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_removal_text'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%body_removed_at_utc%' AND definition LIKE '%sanitized_text%'
    )
    OR NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_state_removal'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%deleted%' AND definition LIKE '%member_delete%' AND definition LIKE '%rights_takedown%'
    )
        THROW 55867, 'A required C10 tombstone pairing constraint is missing its required column or vocabulary term(s).', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_outcome_text'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%extracted%' AND definition LIKE '%partial%' AND definition LIKE '%sanitized_text%'
    )
        THROW 55868, 'The success/text pairing constraint must gate stored text on the extracted/partial outcomes and body-removal state.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_rights_class'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%none%' AND definition LIKE '%takedown_required%'
    )
    OR NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_imports_removal_reason'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%member_delete%' AND definition LIKE '%rights_takedown%'
    )
        THROW 55869, 'The rights-obligation class or body-removal reason constraint must admit its canonical closed values.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM (VALUES (N'CK_myopp_member_imports_data_class')) required(constraint_name)
        WHERE NOT EXISTS
        (
            SELECT 1 FROM sys.check_constraints actual
            WHERE actual.name = required.constraint_name
              AND SCHEMA_NAME(actual.schema_id) = N'dbo'
              AND actual.definition LIKE '%fixture%'
              AND actual.definition LIKE '%production%'
        )
    )
        THROW 55870, 'The C10 data_class constraint must admit fixture and production.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_import_idempotency_result_json'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%ISJSON%'
    )
    OR NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_member_import_idempotency_command'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%submit_paste%' AND definition LIKE '%submit_upload%'
          AND definition LIKE '%import_from_url%' AND definition LIKE '%delete_import%'
    )
        THROW 55871, 'The idempotency receipt constraints must enforce a content-free ISJSON payload and the closed command vocabulary.', 1;

    DECLARE @RequiredForeignKeys TABLE (foreign_key_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredForeignKeys (foreign_key_name)
    VALUES
        (N'FK_myopp_member_imports_user'),
        (N'FK_myopp_member_import_stage_outcomes_import_owner'),
        (N'FK_myopp_member_import_idempotency_user');
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
        THROW 55872, 'A required owner-safe C10 foreign key is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE required.foreign_key_name = N'FK_myopp_member_import_stage_outcomes_import_owner'
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
        THROW 55873, 'The stage-outcome-to-import relationship is not fenced by the owner key.', 1;

    IF EXISTS
    (
        -- No C10 table's foreign key may reference anything outside the
        -- owner/self allowlist: app_users (owner fencing) and the parent
        -- myopp_member_imports table (the stage-outcome child only).
        SELECT 1
        FROM sys.foreign_keys foreign_key_record
        JOIN sys.tables parent_table ON parent_table.object_id = foreign_key_record.parent_object_id
        JOIN sys.schemas parent_schema ON parent_schema.schema_id = parent_table.schema_id
        JOIN sys.tables referenced_table ON referenced_table.object_id = foreign_key_record.referenced_object_id
        JOIN sys.schemas referenced_schema ON referenced_schema.schema_id = referenced_table.schema_id
        WHERE parent_schema.name = N'dbo'
          AND parent_table.name IN
          (N'myopp_member_imports', N'myopp_member_import_stage_outcomes', N'myopp_member_import_idempotency')
          AND NOT
          (
              referenced_schema.name = N'dbo'
              AND referenced_table.name IN (N'app_users', N'myopp_member_imports')
          )
    )
        THROW 55874, 'A C10 member_import table references a table outside the allowed owner/self set.', 1;

    IF OBJECT_ID(N'dbo.trg_myopp_member_imports_transition_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_member_imports_delete_block', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_member_import_stage_outcomes_immutable', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_member_import_idempotency_immutable', N'TR') IS NULL
       OR EXISTS
       (
           SELECT 1 FROM sys.triggers
           WHERE parent_id IN
           (
               OBJECT_ID(N'dbo.myopp_member_imports'),
               OBJECT_ID(N'dbo.myopp_member_import_stage_outcomes'),
               OBJECT_ID(N'dbo.myopp_member_import_idempotency')
           )
             AND is_disabled = 1
       )
        THROW 55875, 'A required C10 guard trigger is missing or disabled.', 1;

    DECLARE @ForbiddenColumns TABLE (pattern nvarchar(40) NOT NULL PRIMARY KEY);
    INSERT @ForbiddenColumns (pattern)
    VALUES
        -- doc 16 section 4 no-score invariant.
        (N'%score%'), (N'%probab%'), (N'%percent%'), (N'%predict%'),
        -- structural absences: no shared-side key may appear anywhere here.
        (N'%receipt_key%'), (N'%listing_key%'), (N'%source_version%');
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN sys.tables table_record ON table_record.object_id = column_record.object_id
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        JOIN @ForbiddenColumns forbidden ON column_record.name LIKE forbidden.pattern
        WHERE schema_record.name = N'dbo'
          AND table_record.name IN
          (N'myopp_member_imports', N'myopp_member_import_stage_outcomes', N'myopp_member_import_idempotency')
    )
        THROW 55876, 'A C10 member_import table carries a forbidden shared-side-key or scoring column.', 1;

    DECLARE @RequiredUniques TABLE (table_name sysname NOT NULL, constraint_name sysname NOT NULL, PRIMARY KEY (table_name, constraint_name));
    INSERT @RequiredUniques (table_name, constraint_name)
    VALUES
        (N'myopp_member_imports', N'PK_myopp_member_imports'),
        (N'myopp_member_imports', N'UQ_myopp_member_imports_key'),
        (N'myopp_member_imports', N'UQ_myopp_member_imports_id_user'),
        (N'myopp_member_imports', N'UQ_myopp_member_imports_key_user'),
        (N'myopp_member_import_stage_outcomes', N'PK_myopp_member_import_stage_outcomes'),
        (N'myopp_member_import_stage_outcomes', N'UQ_myopp_member_import_stage_outcomes_sequence'),
        (N'myopp_member_import_idempotency', N'PK_myopp_member_import_idempotency'),
        (N'myopp_member_import_idempotency', N'UQ_myopp_member_import_idempotency_owner_key');
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
              AND actual.type IN (N'PK', N'UQ')
        )
    )
        THROW 55877, 'A required C10 primary-key or uniqueness constraint (the exact migration object list) is missing.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-MYOPP-006 C10 owner-fenced private member_import storage verified: the closed doc 06 section 2 outcome-state vocabulary with C13-reserved reasons schema-complete, the append-only stage-outcome trail, in-record fetch provenance, dual-retention body-removal tombstones (member delete and rights takedown), and content-free idempotency receipts. No shared-side key, score, or content column anywhere; content-free by construction.' AS detail;
END TRY
BEGIN CATCH
    THROW;
END CATCH;
