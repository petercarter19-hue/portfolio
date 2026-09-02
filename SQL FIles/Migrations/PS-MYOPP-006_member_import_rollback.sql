/* PS-MYOPP-006 rollback. Refuses with C10 member data in any of the three
   tables or any later ledger row. THROW numbers 55880-55882, inside the
   reserved 55840-55899 band. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-MYOPP-006'
    );
    IF @AppliedAtUtc IS NULL
        THROW 55880, 'PS-MYOPP-006 is not recorded in the schema ledger.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id <> N'PS-MYOPP-006'
          AND applied_at_utc > @AppliedAtUtc
    )
        THROW 55881, 'PS-MYOPP-006 rollback refused because a later migration is recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.myopp_member_imports)
       OR EXISTS (SELECT 1 FROM dbo.myopp_member_import_stage_outcomes)
       OR EXISTS (SELECT 1 FROM dbo.myopp_member_import_idempotency)
        THROW 55882, 'PS-MYOPP-006 rollback refused because C10 member data exists.', 1;

    DROP TRIGGER dbo.trg_myopp_member_import_idempotency_immutable;
    DROP TRIGGER dbo.trg_myopp_member_import_stage_outcomes_immutable;
    DROP TRIGGER dbo.trg_myopp_member_imports_delete_block;
    DROP TRIGGER dbo.trg_myopp_member_imports_transition_guard;

    DROP TABLE dbo.myopp_member_import_idempotency;        -- no FK to imports; drop order fixed for review determinism
    DROP TABLE dbo.myopp_member_import_stage_outcomes;      -- FKs to imports; must drop before the parent
    DROP TABLE dbo.myopp_member_imports;                    -- parent, dropped last

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-006';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
