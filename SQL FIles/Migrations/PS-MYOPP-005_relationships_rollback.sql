/* PS-MYOPP-005 rollback. Refuses with C6 member data or any later ledger row. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-MYOPP-005'
    );
    IF @AppliedAtUtc IS NULL
        THROW 55800, 'PS-MYOPP-005 is not recorded in the schema ledger.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id <> N'PS-MYOPP-005'
          AND applied_at_utc > @AppliedAtUtc
    )
        THROW 55801, 'PS-MYOPP-005 rollback refused because a later migration is recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.myopp_slate_links)
       OR EXISTS (SELECT 1 FROM dbo.myopp_saved_opportunities)
        THROW 55802, 'PS-MYOPP-005 rollback refused because C6 member data exists.', 1;

    DROP TRIGGER dbo.trg_myopp_slate_links_guard;
    DROP TRIGGER dbo.trg_myopp_saved_opportunities_guard;

    DROP TABLE dbo.myopp_slate_links;          -- no inter-table FK between the two;
    DROP TABLE dbo.myopp_saved_opportunities;  -- drop order fixed anyway for review determinism

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-005';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
