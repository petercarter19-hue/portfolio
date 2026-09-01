/* ============================================================
   PS-SETTINGS-EXPORT-010 rollback - domain-ledger writer

   A clean DROP: this migration created exactly one procedure and
   touched nothing else, so removing it restores the world C1 shipped.
   dbo.usp_CompleteAccountExportJob (C1's) was never modified and
   needs no restoration.

   Deliberately NOT conditioned on ledger data. Rows already written
   to dbo.account_export_job_domains are member-facing truth records
   attached to completed jobs; dropping the writer does not orphan or
   damage them, it only prevents new completions through this path
   (the worker would fail loudly at its next completion, which is the
   correct behaviour for a rolled-back writer). Deleting those rows is
   C1-rollback territory and remains blocked by C1's own data guard.
   ============================================================ */

SET XACT_ABORT ON;
SET NOCOUNT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-010'
    )
    BEGIN
        COMMIT TRANSACTION;
        RETURN;
    END;

    IF OBJECT_ID(N'dbo.usp_CompleteAccountExportWithDomains', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CompleteAccountExportWithDomains;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-010';

    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.rolled_back',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-010"}';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
