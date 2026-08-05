/* ============================================================
   PS-OPPSLATE-003 ROLLBACK - guarded OS-4 additive reversal

   Refuses to discard any saved slate, saved result, saved qualification or
   pinned saved evidence row, any later migration, or a drifted owned
   procedure. This migration revised no existing procedure (see the forward
   file's header), so there is nothing to restore to a prior definition -
   unlike PS-OPPSLATE-002's rollback, which had to reinstate four OS-2
   procedure bodies OS-3 had changed. This rollback only ever has to DROP
   what PS-OPPSLATE-003 created: three procedures, then four tables (children
   before parents), and remove only the PS-OPPSLATE-003 ledger row.
   PS-OPPSLATE-001 and PS-OPPSLATE-002 objects and data remain untouched.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53740, 'Rollback refused: the migration ledger is missing.', 1;
    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc=applied_at_utc FROM dbo.schema_migrations WITH (UPDLOCK,HOLDLOCK)
    WHERE migration_id=N'PS-OPPSLATE-003';
    IF @AppliedAtUtc IS NULL
        THROW 53741, 'Rollback refused: PS-OPPSLATE-003 is not recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc>@AppliedAtUtc)
        THROW 53742, 'Rollback refused: a migration later than PS-OPPSLATE-003 is present.', 1;

    /* Every procedure PS-OPPSLATE-003 owns must still carry the exact body it
       was fingerprinted with at apply time. A drifted body means an operator
       hand-patched or otherwise changed a procedure this rollback is about to
       drop - the same protection PS-OPPSLATE-002's rollback applies to its
       own four owned procedures. */
    DECLARE @ProcedureHashPropertyName sysname=N'PS_OPPSLATE_003_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_GetOpportunitySavedSlateForOwner'),
        (N'usp_SaveOpportunitySlateForOwner'),
        (N'usp_DeleteOpportunitySavedSlateForOwner');
    IF EXISTS
    (
        SELECT 1 FROM @ProtectedProcedures p
        LEFT JOIN sys.procedures o ON o.schema_id=SCHEMA_ID(N'dbo') AND o.name=p.procedure_name
        LEFT JOIN sys.extended_properties x ON x.class=1 AND x.major_id=o.object_id
             AND x.minor_id=0 AND x.name=@ProcedureHashPropertyName
        WHERE o.object_id IS NULL OR x.major_id IS NULL
           OR CONVERT(nvarchar(64),x.value)<>CONVERT(nvarchar(64),
              HASHBYTES('SHA2_256',OBJECT_DEFINITION(o.object_id)),2)
    )
        THROW 53743, 'Rollback refused: a protected OS-4 procedure changed after PS-OPPSLATE-003.', 1;

    /* Refuse while a member record exists in any table this migration owns.
       Children before parents, so an operator hears about the innermost
       record first - the same ordering PS-OPPSLATE-002's rollback uses. */
    IF OBJECT_ID(N'dbo.opportunity_saved_evidence',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_saved_evidence)
        THROW 53744, 'Rollback refused: opportunity_saved_evidence contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_saved_qualifications',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_saved_qualifications)
        THROW 53745, 'Rollback refused: opportunity_saved_qualifications contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_saved_results',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_saved_results)
        THROW 53746, 'Rollback refused: opportunity_saved_results contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_slates',N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_slates)
        THROW 53747, 'Rollback refused: opportunity_slates contains member records.', 1;

    IF OBJECT_ID(N'dbo.usp_GetOpportunitySavedSlateForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunitySavedSlateForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunitySlateForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunitySlateForOwner;
    IF OBJECT_ID(N'dbo.usp_DeleteOpportunitySavedSlateForOwner',N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_DeleteOpportunitySavedSlateForOwner;

    /* Children before parents, so no drop ever runs against an object a
       foreign key still points at. */
    IF OBJECT_ID(N'dbo.opportunity_saved_evidence',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_saved_evidence;
    IF OBJECT_ID(N'dbo.opportunity_saved_qualifications',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_saved_qualifications;
    IF OBJECT_ID(N'dbo.opportunity_saved_results',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_saved_results;
    IF OBJECT_ID(N'dbo.opportunity_slates',N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_slates;

    DELETE dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-003';
    IF OBJECT_ID(N'dbo.usp_AppendAuditEvent',N'P') IS NOT NULL
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.rolled_back',
            @EntityType=N'database_migration',@Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-OPPSLATE-003"}';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
