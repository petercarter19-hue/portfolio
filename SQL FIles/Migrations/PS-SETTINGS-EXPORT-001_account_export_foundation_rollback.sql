/* ============================================================
   PS-SETTINGS-EXPORT-001 ROLLBACK - account export foundation (C1)

   Data-safe by default: this rollback refuses to remove a job ledger
   row (or its domain rows) once any exists, and refuses if a later
   object depends on either table. Export/review retention before
   deliberately clearing account-export ledger rows for a destructive
   rollback; a ledger row here is never exported member content, but it
   is still real request/operational history and is treated with the
   same care as every other data-safe rollback in this repository.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.account_export_job_domains', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.account_export_job_domains)
        THROW 57260, 'Rollback blocked: account_export_job_domains contains data.', 1;

    IF OBJECT_ID(N'dbo.account_export_jobs', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.account_export_jobs)
        THROW 57261, 'Rollback blocked: account_export_jobs contains data.', 1;

    IF OBJECT_ID(N'dbo.trg_account_export_jobs_cleanup_guard', N'TR') IS NOT NULL
        DROP TRIGGER dbo.trg_account_export_jobs_cleanup_guard;
    IF OBJECT_ID(N'dbo.usp_CleanupAccountExportJob', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CleanupAccountExportJob;
    IF OBJECT_ID(N'dbo.usp_ExpireAccountExportJobs', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ExpireAccountExportJobs;
    IF OBJECT_ID(N'dbo.usp_FailAccountExportJob', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_FailAccountExportJob;
    IF OBJECT_ID(N'dbo.usp_CompleteAccountExportJob', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CompleteAccountExportJob;
    IF OBJECT_ID(N'dbo.usp_ClaimAccountExportJob', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ClaimAccountExportJob;
    IF OBJECT_ID(N'dbo.usp_GetAccountExportDownloadMetadataForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetAccountExportDownloadMetadataForOwner;
    IF OBJECT_ID(N'dbo.usp_GetAccountExportStatusForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetAccountExportStatusForOwner;
    IF OBJECT_ID(N'dbo.usp_RequestAccountExportForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_RequestAccountExportForOwner;

    IF OBJECT_ID(N'dbo.trg_account_export_jobs_cleanup_guard', N'TR') IS NOT NULL
        DROP TRIGGER dbo.trg_account_export_jobs_cleanup_guard;

    IF OBJECT_ID(N'dbo.account_export_job_domains', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.foreign_keys
           WHERE referenced_object_id = OBJECT_ID(N'dbo.account_export_job_domains')
       )
        THROW 57262, 'Rollback blocked: a later table depends on account_export_job_domains.', 1;
    IF OBJECT_ID(N'dbo.account_export_job_domains', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.sql_expression_dependencies AS d
           JOIN sys.objects AS o ON o.object_id = d.referencing_id
           /* A table's own CHECK constraints and triggers register as
              referencing objects in sys.sql_expression_dependencies; only
              objects outside this table are genuinely "later" dependents. */
           WHERE d.referenced_id = OBJECT_ID(N'dbo.account_export_job_domains')
             AND ISNULL(o.parent_object_id, 0) <> OBJECT_ID(N'dbo.account_export_job_domains')
             AND d.referencing_id <> OBJECT_ID(N'dbo.account_export_job_domains')
       )
        THROW 57263, 'Rollback blocked: a later programmable object depends on account_export_job_domains.', 1;
    IF OBJECT_ID(N'dbo.account_export_job_domains', N'U') IS NOT NULL
        DROP TABLE dbo.account_export_job_domains;

    IF OBJECT_ID(N'dbo.account_export_jobs', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.foreign_keys
           WHERE referenced_object_id = OBJECT_ID(N'dbo.account_export_jobs')
       )
        THROW 57264, 'Rollback blocked: a later table depends on account_export_jobs.', 1;
    IF OBJECT_ID(N'dbo.account_export_jobs', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM sys.sql_expression_dependencies AS d
           JOIN sys.objects AS o ON o.object_id = d.referencing_id
           /* Same self-reference exclusion as the domains guard above. */
           WHERE d.referenced_id = OBJECT_ID(N'dbo.account_export_jobs')
             AND ISNULL(o.parent_object_id, 0) <> OBJECT_ID(N'dbo.account_export_jobs')
             /* A computed column registers its own table as a referencing
                object (no parent), so the table must not count as its own
                later dependent. */
             AND d.referencing_id <> OBJECT_ID(N'dbo.account_export_jobs')
       )
        THROW 57265, 'Rollback blocked: a later programmable object depends on account_export_jobs.', 1;
    IF OBJECT_ID(N'dbo.account_export_jobs', N'U') IS NOT NULL
        DROP TABLE dbo.account_export_jobs;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-SETTINGS-EXPORT-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
