/* Verify PS-MYOPP-003 owner isolation, four-state assessments, append-only
   revisions, reference-only evidence links, gate separation, and
   content-free command receipts. */
SET NOCOUNT ON;

BEGIN TRY
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003')
        THROW 55690, 'PS-MYOPP-003 is not recorded in the schema ledger.', 1;

    IF OBJECT_ID(N'dbo.myopp_evidence_grants', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_assessments', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_assessment_revisions', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_assessment_evidence_links', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_practical_fit_observations', N'U') IS NULL
       OR OBJECT_ID(N'dbo.myopp_qualification_commands', N'U') IS NULL
        THROW 55691, 'A required My Opportunities C5 table is missing.', 1;

    DECLARE @MemberTables TABLE (object_name sysname NOT NULL PRIMARY KEY);
    INSERT @MemberTables (object_name)
    VALUES
        (N'myopp_evidence_grants'),
        (N'myopp_assessments'),
        (N'myopp_assessment_revisions'),
        (N'myopp_assessment_evidence_links'),
        (N'myopp_practical_fit_observations'),
        (N'myopp_qualification_commands');

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
        THROW 55692, 'Every C5 qualification table must carry the non-null owner key.', 1;

    DECLARE @RequiredConstraints TABLE (constraint_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredConstraints (constraint_name)
    VALUES
        (N'CK_myopp_evidence_grants_purpose'),
        (N'CK_myopp_evidence_grants_scope_classes_json'),
        (N'CK_myopp_evidence_grants_scope_records_json'),
        (N'CK_myopp_evidence_grants_expiry'),
        (N'CK_myopp_evidence_grants_revocation'),
        (N'CK_myopp_assessments_state'),
        (N'CK_myopp_assessments_state_reason'),
        (N'CK_myopp_assessment_revisions_state'),
        (N'CK_myopp_assessment_revisions_state_reason'),
        (N'CK_myopp_assessment_revisions_cause'),
        (N'CK_myopp_assessment_revisions_actor'),
        (N'CK_myopp_assessment_evidence_links_relation'),
        (N'CK_myopp_assessment_evidence_links_span'),
        (N'CK_myopp_assessment_evidence_links_version'),
        (N'CK_myopp_assessments_data_class'),
        (N'CK_myopp_assessment_evidence_links_class'),
        (N'CK_myopp_practical_fit_observations_data_class'),
        (N'CK_myopp_qualification_commands_idempotency_hash'),
        (N'CK_myopp_qualification_commands_input_hash'),
        (N'CK_myopp_qualification_commands_result'),
        (N'CK_myopp_qualification_commands_expiry'),
        (N'CK_myopp_practical_fit_observations_archive'),
        (N'CK_myopp_practical_fit_observations_note');
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
        THROW 55693, 'A required C5 qualification constraint is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_assessments_state'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%verified%'
          AND definition LIKE '%not_established%'
          AND definition LIKE '%appears_unmet%'
          AND definition LIKE '%review_unavailable%'
    )
        -- Presence-only check (LIKE, not an exclusivity scan): this proves
        -- the four canonical states are admitted, not that nothing else is.
        THROW 55694, 'The assessment state constraint must admit the canonical states.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_assessments_state_reason'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%direct_evidence%'
          AND definition LIKE '%corroborated%'
          AND definition LIKE '%alternative_path_met%'
          AND definition LIKE '%no_evidence_in_scope%'
          AND definition LIKE '%ambiguous_evidence%'
          AND definition LIKE '%partial_evidence%'
          AND definition LIKE '%temporal_mismatch%'
          AND definition LIKE '%evidence_revoked%'
          AND definition LIKE '%classification_ambiguous%'
          AND definition LIKE '%candidate_evidence_only%'
          AND definition LIKE '%affirmative_contradiction%'
          AND definition LIKE '%ai_unavailable%'
          AND definition LIKE '%evidence_source_unavailable%'
          AND definition LIKE '%timeout%'
          AND definition LIKE '%assessment_error%'
    )
        -- Presence-only check, as above: proves the fifteen canonical
        -- reason codes are admitted, not that the list is closed to them.
        THROW 55695, 'The assessment state/reason pairing constraint must admit the canonical reason codes.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_myopp_evidence_grants_purpose'
          AND SCHEMA_NAME(schema_id) = N'dbo'
          AND definition LIKE '%=%qualification_verification%'
    )
        THROW 55696, 'Evidence grants must be fixed to the qualification_verification purpose.', 1;

    DECLARE @RequiredForeignKeys TABLE (foreign_key_name sysname NOT NULL PRIMARY KEY);
    INSERT @RequiredForeignKeys (foreign_key_name)
    VALUES
        (N'FK_myopp_evidence_grants_user'),
        (N'FK_myopp_assessments_user'),
        (N'FK_myopp_assessments_requirement_item_class'),
        (N'FK_myopp_assessments_requirement_version_class'),
        (N'FK_myopp_assessment_revisions_assessment_owner'),
        (N'FK_myopp_assessment_evidence_links_revision_owner'),
        (N'FK_myopp_assessment_evidence_links_grant_owner'),
        (N'FK_myopp_practical_fit_observations_user'),
        (N'FK_myopp_practical_fit_observations_opportunity_class'),
        (N'FK_myopp_qualification_commands_user'),
        (N'FK_myopp_qualification_commands_grant_owner'),
        (N'FK_myopp_qualification_commands_observation_owner');
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
        THROW 55697, 'A required owner-safe C5 foreign key is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE required.foreign_key_name NOT IN
        (
            N'FK_myopp_evidence_grants_user',
            N'FK_myopp_assessments_user',
            N'FK_myopp_practical_fit_observations_user',
            N'FK_myopp_qualification_commands_user',
            N'FK_myopp_assessments_requirement_item_class',
            N'FK_myopp_assessments_requirement_version_class',
            N'FK_myopp_practical_fit_observations_opportunity_class'
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
        THROW 55698, 'A C5 member-to-member relationship is not fenced by the owner key.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredForeignKeys required
        WHERE required.foreign_key_name IN
        (
            N'FK_myopp_assessments_requirement_item_class',
            N'FK_myopp_assessments_requirement_version_class',
            N'FK_myopp_practical_fit_observations_opportunity_class'
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
        THROW 55699, 'A required C5 shared-side data_class relationship is missing.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.myopp_assessments')
          AND name = N'UQ_myopp_assessments_identity'
          AND is_unique = 1
    )
        THROW 55700, 'The one-current-assessment-per-member-item-version uniqueness is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.index_columns index_column_record
        JOIN sys.indexes index_record
          ON index_record.object_id = index_column_record.object_id
         AND index_record.index_id = index_column_record.index_id
        JOIN sys.columns column_record
          ON column_record.object_id = index_column_record.object_id
         AND column_record.column_id = index_column_record.column_id
        WHERE index_record.object_id = OBJECT_ID(N'dbo.myopp_assessments')
          AND index_record.name = N'UQ_myopp_assessments_identity'
          AND index_column_record.key_ordinal = 1
          AND column_record.name <> N'user_key'
    )
        THROW 55701, 'The assessment identity uniqueness must lead on the owner key.', 1;

    -- Exact key-column set (minor f): not just "leads on user_key", but
    -- precisely the three identity columns, no more and no fewer.
    IF
    (
        SELECT COUNT(*)
        FROM sys.index_columns index_column_record
        WHERE index_column_record.object_id = OBJECT_ID(N'dbo.myopp_assessments')
          AND index_column_record.index_id =
          (
              SELECT index_id FROM sys.indexes
              WHERE object_id = OBJECT_ID(N'dbo.myopp_assessments') AND name = N'UQ_myopp_assessments_identity'
          )
          AND index_column_record.is_included_column = 0
    ) <> 3
        THROW 55713, 'The assessment identity uniqueness must have exactly three key columns.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM (VALUES (N'user_key'), (N'myopp_requirement_item_id'), (N'myopp_requirement_version_id'))
            required(column_name)
        WHERE NOT EXISTS
        (
            SELECT 1
            FROM sys.index_columns index_column_record
            JOIN sys.columns column_record
              ON column_record.object_id = index_column_record.object_id
             AND column_record.column_id = index_column_record.column_id
            WHERE index_column_record.object_id = OBJECT_ID(N'dbo.myopp_assessments')
              AND index_column_record.index_id =
              (
                  SELECT index_id FROM sys.indexes
                  WHERE object_id = OBJECT_ID(N'dbo.myopp_assessments') AND name = N'UQ_myopp_assessments_identity'
              )
              AND index_column_record.is_included_column = 0
              AND column_record.name = required.column_name
        )
    )
        THROW 55714, 'The assessment identity uniqueness must include user_key, myopp_requirement_item_id, and myopp_requirement_version_id.', 1;

    DECLARE @ForbiddenLinkColumns TABLE (column_name sysname NOT NULL PRIMARY KEY);
    INSERT @ForbiddenLinkColumns (column_name)
    VALUES
        (N'evidence_title'), (N'evidence_body'), (N'evidence_excerpt'),
        (N'excerpt'), (N'wording'), (N'content'), (N'body'), (N'title');
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN @ForbiddenLinkColumns forbidden ON forbidden.column_name = column_record.name
        WHERE column_record.object_id = OBJECT_ID(N'dbo.myopp_assessment_evidence_links')
    )
        THROW 55702, 'Evidence links must remain references, never copies of evidence content.', 1;

    IF COL_LENGTH(N'dbo.myopp_assessment_evidence_links', N'evidence_key') IS NULL
       OR COL_LENGTH(N'dbo.myopp_assessment_evidence_links', N'evidence_version') IS NULL
       OR COL_LENGTH(N'dbo.myopp_assessment_evidence_links', N'myopp_evidence_grant_id') IS NULL
        THROW 55703, 'Evidence links must carry key, version, and admitting-grant references.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        WHERE column_record.object_id = OBJECT_ID(N'dbo.myopp_qualification_commands')
          AND column_record.name IN
          (
              N'idempotency_key', N'scope_classes_json', N'scope_record_keys_json',
              N'note_text', N'member_message', N'request_text'
          )
    )
        THROW 55704, 'C5 command receipts must remain content-free hashes and references.', 1;

    IF COL_LENGTH(N'dbo.myopp_qualification_commands', N'idempotency_key_sha256') IS NULL
       OR COL_LENGTH(N'dbo.myopp_qualification_commands', N'canonical_input_sha256') IS NULL
       OR COL_LENGTH(N'dbo.myopp_qualification_commands', N'expires_at_utc') IS NULL
        THROW 55705, 'A required C5 command receipt hash or expiry column is missing.', 1;

    IF COL_LENGTH(N'dbo.myopp_evidence_grants', N'expires_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.myopp_evidence_grants', N'revoked_at_utc') IS NULL
        THROW 55706, 'A required grant expiry or revocation column is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        WHERE column_record.object_id = OBJECT_ID(N'dbo.myopp_evidence_grants')
          AND column_record.name = N'expires_at_utc'
          AND column_record.is_nullable = 1
    )
       OR NOT EXISTS
       (
           SELECT 1
           FROM sys.columns column_record
           WHERE column_record.object_id = OBJECT_ID(N'dbo.myopp_evidence_grants')
             AND column_record.name = N'revoked_at_utc'
             AND column_record.is_nullable = 1
       )
        THROW 55707, 'Grant expiry must be required and revocation must be nullable.', 1;

    IF OBJECT_ID(N'dbo.trg_myopp_evidence_grants_transition_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_assessments_requirement_consistency', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_assessments_head_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_assessment_revisions_immutable', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_assessment_evidence_links_immutable', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_practical_fit_observations_guard', N'TR') IS NULL
       OR OBJECT_ID(N'dbo.trg_myopp_qualification_commands_immutable', N'TR') IS NULL
        THROW 55708, 'A required C5 transition or immutability trigger is missing.', 1;

    DECLARE @RequiredIndexes TABLE (table_name sysname NOT NULL, index_name sysname NOT NULL, leading_column sysname NOT NULL, PRIMARY KEY (table_name, index_name));
    INSERT @RequiredIndexes (table_name, index_name, leading_column)
    VALUES
        (N'myopp_evidence_grants', N'IX_myopp_evidence_grants_owner_live', N'user_key'),
        (N'myopp_evidence_grants', N'IX_myopp_evidence_grants_expiry', N'expires_at_utc'),
        (N'myopp_assessments', N'IX_myopp_assessments_owner_version', N'user_key'),
        (N'myopp_assessment_evidence_links', N'IX_myopp_assessment_evidence_links_grant', N'myopp_evidence_grant_id'),
        (N'myopp_practical_fit_observations', N'IX_myopp_practical_fit_observations_owner', N'user_key'),
        (N'myopp_qualification_commands', N'IX_myopp_qualification_commands_expiry', N'expires_at_utc');
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
        THROW 55709, 'A required C5 index is missing.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @RequiredIndexes required
        WHERE required.index_name IN
            (N'IX_myopp_evidence_grants_owner_live', N'IX_myopp_assessments_owner_version', N'IX_myopp_practical_fit_observations_owner')
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
                AND column_record.name = required.leading_column
          )
    )
        THROW 55710, 'An owner-scoped C5 index must lead on the owner key.', 1;

    DECLARE @ScoringPatterns TABLE (pattern nvarchar(40) NOT NULL PRIMARY KEY);
    INSERT @ScoringPatterns (pattern)
    VALUES (N'%score%'), (N'%probab%'), (N'%percent%'), (N'%rank%'), (N'%predict%'), (N'%confidence%'), (N'%match_rate%');
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns column_record
        JOIN sys.tables table_record ON table_record.object_id = column_record.object_id
        JOIN sys.schemas schema_record ON schema_record.schema_id = table_record.schema_id
        JOIN @ScoringPatterns pattern_record ON column_record.name LIKE pattern_record.pattern
        WHERE schema_record.name = N'dbo'
          AND table_record.name IN
          (
              N'myopp_evidence_grants', N'myopp_assessments', N'myopp_assessment_revisions',
              N'myopp_assessment_evidence_links', N'myopp_practical_fit_observations',
              N'myopp_qualification_commands'
          )
    )
        THROW 55711, 'No C5 table may carry a score, probability, ranking, or confidence column.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.foreign_keys foreign_key_record
        WHERE SCHEMA_NAME(foreign_key_record.schema_id) = N'dbo'
          AND
          (
              (OBJECT_NAME(foreign_key_record.parent_object_id) = N'myopp_practical_fit_observations'
               AND OBJECT_NAME(foreign_key_record.referenced_object_id) LIKE N'myopp_assessment%')
              OR
              (OBJECT_NAME(foreign_key_record.referenced_object_id) = N'myopp_practical_fit_observations'
               AND OBJECT_NAME(foreign_key_record.parent_object_id) LIKE N'myopp_assessment%')
          )
    )
        THROW 55712, 'Practical fit must remain structurally separate from the qualification gate.', 1;

    SELECT CAST(1 AS bit) AS verified,
           N'PS-MYOPP-003 C5 owner-scoped grants, four-state assessments, append-only revisions, reference-only evidence links, gate-separated practical fit, and content-free command receipts verified.' AS detail;
END TRY
BEGIN CATCH
    THROW;
END CATCH;
