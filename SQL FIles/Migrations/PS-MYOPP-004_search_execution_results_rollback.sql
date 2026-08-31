/* PS-MYOPP-004 rollback. Refuses with C4 member data or any later ledger row. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-MYOPP-004'
    );
    IF @AppliedAtUtc IS NULL
        THROW 55750, 'PS-MYOPP-004 is not recorded in the schema ledger.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id <> N'PS-MYOPP-004'
          AND applied_at_utc > @AppliedAtUtc
    )
        THROW 55751, 'PS-MYOPP-004 rollback refused because a later migration is recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.myopp_result_entries)
       OR EXISTS (SELECT 1 FROM dbo.myopp_result_snapshots)
       OR EXISTS (SELECT 1 FROM dbo.myopp_search_executions)
        THROW 55752, 'PS-MYOPP-004 rollback refused because C4 member data exists.', 1;

    DROP TRIGGER dbo.trg_myopp_result_entries_immutable;
    DROP TRIGGER dbo.trg_myopp_result_snapshots_immutable;
    DROP TRIGGER dbo.trg_myopp_search_executions_transition_guard;

    DROP TABLE dbo.myopp_result_entries;
    DROP TABLE dbo.myopp_result_snapshots;
    DROP TABLE dbo.myopp_search_executions;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-004';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
