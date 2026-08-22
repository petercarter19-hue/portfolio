/* ============================================================
   PS-INTERVIEW-AI-EXTRACT-001 - retention-safe rollback

   Correction C9: ordinary application rollback NEVER runs this file -
   code rolls back to the prior known-good artifact/commit and existing
   telemetry rows stay in place with the 90-day purge still operating.
   Compatible configuration rollback follows architecture D8 only. A
   production retirement of a table that holds rows requires its own
   separately authorized retention-safe schema operation.

   This file is therefore guarded by an EMPTY-TABLE condition: it refuses
   - loudly, transactionally - to drop a telemetry table that contains
   any rows. It may complete only against an empty table, which in
   practice means a disposable/preproduction proof database or a
   production apply that was never exercised. Nothing here can destroy
   recorded operational telemetry.

   When the guard passes, teardown runs in reverse dependency order:
   procedures first, then the empty table. The ledger row is removed
   last so a database can never claim a migration it no longer carries.
   The two execute-only roles are NOT touched here: they are created
   by the administrator-run authority script
   (scripts/configure_interview_telemetry_sql_authority.py), not by the
   forward migration, because the governed apply identity holds
   db_ddladmin only and can neither create nor drop roles. Dropping a
   procedure or table removes its grants and DENYs with it, so after
   this rollback the roles, the maintenance user and their memberships
   persist holding no object permission at all; removing them is a
   separate administrator operation (ALTER ROLE ... DROP MEMBER, DROP
   ROLE, DROP USER), recorded in 11_DARK_TELEMETRY_INFRASTRUCTURE_
   EVIDENCE.md section 5a and deliberately not automated.

   Who runs this file: the empty-table guard below READS the table, and
   db_ddladmin carries no data access, so the governed apply identity
   cannot execute this rollback (it would be refused before the guard
   is evaluated - the same shape as every other guarded rollback in
   this repository). This rollback therefore runs as the administrator
   through the governor, as recorded in 10_RELEASE_PLAN.md section 6.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.interview_ai_server_calls', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.interview_ai_server_calls)
        THROW 50090,
            N'Refusing rollback: dbo.interview_ai_server_calls holds telemetry rows under a 90-day retention promise. Roll application code back to the prior artifact instead; retiring a nonempty table requires its own retention-safe schema operation.',
            1;

    IF OBJECT_ID(N'dbo.usp_PurgeInterviewAIServerCalls', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_PurgeInterviewAIServerCalls;
    IF OBJECT_ID(N'dbo.usp_AppendInterviewAIServerCall', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_AppendInterviewAIServerCall;

    IF OBJECT_ID(N'dbo.interview_ai_server_calls', N'U') IS NOT NULL
        DROP TABLE dbo.interview_ai_server_calls;

    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.rolled_back',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-INTERVIEW-AI-EXTRACT-001"}';

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-INTERVIEW-AI-EXTRACT-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
