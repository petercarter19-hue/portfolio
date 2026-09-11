/*
Rollback for proposed PS-ENTRY-POLICY-001. This file has not been executed.
It removes only objects introduced by the proposal. It does not restore
career_achievements.chapter_id to NOT NULL if standalone rows exist.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.entry_policy_command_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.entry_policy_command_receipts WITH (UPDLOCK, HOLDLOCK))
        THROW 52111, 'Rollback refused: entry policy command receipts are stored.', 1;
    IF OBJECT_ID(N'dbo.entry_policy_records', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK))
        THROW 52112, 'Rollback refused: entry policy records are stored.', 1;

    DROP PROCEDURE IF EXISTS dbo.usp_SweepExpiredEntryPolicyForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitEntryPolicyCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_ListEntryPolicyEntriesForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetEntryPolicyEntryForOwner;
    DROP TRIGGER IF EXISTS dbo.trg_entry_policy_command_receipts_immutable;
    DROP TABLE IF EXISTS dbo.entry_policy_command_receipts;
    DROP TABLE IF EXISTS dbo.entry_policy_records;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-ENTRY-POLICY-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
