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
   procedures first, then role members (generated from the catalog, so
   no knowledge of apply-time identity binding is needed), then roles,
   then the empty table. The ledger row is removed last so a database
   can never claim a migration it no longer carries.
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

    /* Any identities bound into the roles at apply time must leave first,
       or DROP ROLE refuses; the removal is generated from the catalog so
       the rollback needs no knowledge of which identities were bound. */
    DECLARE @DropMembers NVARCHAR(MAX) = N'';
    SELECT @DropMembers = @DropMembers
        + N'ALTER ROLE ' + QUOTENAME(roles.name)
        + N' DROP MEMBER ' + QUOTENAME(members.name) + N';'
    FROM sys.database_role_members AS role_members
    JOIN sys.database_principals AS roles
        ON roles.principal_id = role_members.role_principal_id
    JOIN sys.database_principals AS members
        ON members.principal_id = role_members.member_principal_id
    WHERE roles.name IN
        (N'interview_telemetry_append', N'interview_telemetry_maintenance');
    IF LEN(@DropMembers) > 0
        EXEC(@DropMembers);

    IF DATABASE_PRINCIPAL_ID(N'interview_telemetry_append') IS NOT NULL
        DROP ROLE interview_telemetry_append;
    IF DATABASE_PRINCIPAL_ID(N'interview_telemetry_maintenance') IS NOT NULL
        DROP ROLE interview_telemetry_maintenance;

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
