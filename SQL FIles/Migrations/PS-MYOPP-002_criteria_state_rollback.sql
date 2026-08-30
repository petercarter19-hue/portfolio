/* PS-MYOPP-002 rollback. Refuses with C3 member data or any later ledger row. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-MYOPP-002'
    );
    IF @AppliedAtUtc IS NULL
        THROW 55620, 'PS-MYOPP-002 is not recorded in the schema ledger.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id <> N'PS-MYOPP-002'
          AND applied_at_utc > @AppliedAtUtc
    )
        THROW 55621, 'PS-MYOPP-002 rollback refused because a later migration is recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.myopp_criteria_commands)
       OR EXISTS (SELECT 1 FROM dbo.myopp_criteria_draft_versions)
       OR EXISTS (SELECT 1 FROM dbo.myopp_applied_criteria_snapshots)
       OR EXISTS (SELECT 1 FROM dbo.myopp_criteria_drafts)
        THROW 55622, 'PS-MYOPP-002 rollback refused because C3 member data exists.', 1;

    DROP TRIGGER dbo.trg_myopp_criteria_commands_immutable;
    DROP TRIGGER dbo.trg_myopp_applied_criteria_snapshots_immutable;
    DROP TRIGGER dbo.trg_myopp_criteria_draft_versions_immutable;
    DROP TRIGGER dbo.trg_myopp_criteria_drafts_transition_guard;
    DROP TABLE dbo.myopp_criteria_commands;
    ALTER TABLE dbo.myopp_criteria_drafts DROP CONSTRAINT FK_myopp_criteria_drafts_terminal_snapshot_owner;
    ALTER TABLE dbo.myopp_criteria_drafts DROP CONSTRAINT FK_myopp_criteria_drafts_parent_snapshot_owner;
    ALTER TABLE dbo.myopp_applied_criteria_snapshots DROP CONSTRAINT FK_myopp_applied_criteria_snapshots_source_draft_owner;
    DROP TABLE dbo.myopp_criteria_draft_versions;
    DROP TABLE dbo.myopp_applied_criteria_snapshots;
    DROP TABLE dbo.myopp_criteria_drafts;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
