/* ============================================================
   PS-OPPSLATE-001 ROLLBACK - guarded Opportunity Slate working-store removal

   Refuses to discard any member opportunity_working_sessions,
   opportunity_sources, or opportunity_source_versions record, any later
   migration, or any protected procedure that changed after this migration
   was applied. Removes only the six Opportunity Slate procedures and the
   three tables this migration added.

   The working store is ephemeral by design, but "ephemeral" is not
   "disposable on an operator's behalf": a member with an open working
   session has un-re-creatable pasted employer wording in it. This rollback
   refuses on data exactly like PS-WORKSHOP-001's does. Purge the expired
   rows (dbo.usp_PurgeExpiredOpportunityWorkingData, per owner) and let
   live sessions expire before rolling back.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53500, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @OppSlateAppliedAtUtc datetime2(7);
    SELECT @OppSlateAppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-OPPSLATE-001';

    IF @OppSlateAppliedAtUtc IS NULL
       AND
       (
           OBJECT_ID(N'dbo.opportunity_working_sessions', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_sources', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_source_versions', N'U') IS NOT NULL
       )
        THROW 53501, 'Rollback refused: Opportunity Slate objects exist without their migration record.', 1;

    IF @OppSlateAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM dbo.schema_migrations AS migration
           WHERE migration.applied_at_utc > @OppSlateAppliedAtUtc
       )
        THROW 53502, 'Rollback refused: a migration later than PS-OPPSLATE-001 is present.', 1;

    DECLARE @ProcedureHashPropertyName sysname = N'PS_OPPSLATE_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_GetOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunitySourceForOwner'),
        (N'usp_CorrectOpportunitySourceForOwner'),
        (N'usp_ConfirmOpportunitySourceForOwner'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner');

    IF @OppSlateAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM @ProtectedProcedures AS protected_procedure
           LEFT JOIN sys.procedures AS procedure_object
             ON procedure_object.schema_id = SCHEMA_ID(N'dbo')
            AND procedure_object.name = protected_procedure.procedure_name
           LEFT JOIN sys.extended_properties AS property
             ON property.class = 1
            AND property.major_id = procedure_object.object_id
            AND property.minor_id = 0
            AND property.name = @ProcedureHashPropertyName
           WHERE procedure_object.object_id IS NULL
              OR property.major_id IS NULL
              OR CONVERT(nvarchar(64), property.value) <>
                 CONVERT
                 (
                     nvarchar(64),
                     HASHBYTES
                     (
                         'SHA2_256',
                         OBJECT_DEFINITION(procedure_object.object_id)
                     ),
                     2
                 )
       )
        THROW 53503, 'Rollback refused: a protected Opportunity Slate procedure changed after PS-OPPSLATE-001.', 1;

    IF OBJECT_ID(N'dbo.opportunity_source_versions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_source_versions)
        THROW 53504, 'Rollback refused: opportunity_source_versions contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_sources', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_sources)
        THROW 53505, 'Rollback refused: opportunity_sources contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_working_sessions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions)
        THROW 53506, 'Rollback refused: opportunity_working_sessions contains member records.', 1;

    /* Procedures first, then child tables, then the parent, so no drop
       ever runs against an object something else still references. */
    IF OBJECT_ID(N'dbo.usp_PurgeExpiredOpportunityWorkingData', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_PurgeExpiredOpportunityWorkingData;
    IF OBJECT_ID(N'dbo.usp_GetOpportunityWorkingSessionForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunityWorkingSessionForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunitySourceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunitySourceForOwner;
    IF OBJECT_ID(N'dbo.usp_CorrectOpportunitySourceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CorrectOpportunitySourceForOwner;
    IF OBJECT_ID(N'dbo.usp_ConfirmOpportunitySourceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ConfirmOpportunitySourceForOwner;
    IF OBJECT_ID(N'dbo.usp_DeleteOpportunityWorkingSessionForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_DeleteOpportunityWorkingSessionForOwner;

    IF OBJECT_ID(N'dbo.opportunity_source_versions', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_source_versions;
    IF OBJECT_ID(N'dbo.opportunity_sources', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_sources;
    IF OBJECT_ID(N'dbo.opportunity_working_sessions', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_working_sessions;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-OPPSLATE-001';

    IF OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NOT NULL
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-OPPSLATE-001"}';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
