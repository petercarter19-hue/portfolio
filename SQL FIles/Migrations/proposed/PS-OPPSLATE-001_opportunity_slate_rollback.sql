/* ============================================================
   PS-OPPSLATE-001 ROLLBACK - guarded Opportunity Slate working-store removal

   Refuses to discard any member Opportunity Slate record - working
   sessions, sources, captured versions, AI-proposal reviews, extraction
   concerns, requirement sets, requirement-set versions, requirement
   statements, alignment analyses, per-qualification results, evidence
   citations, or the member's own responses - any later migration, or any
   protected procedure that changed after this migration was applied. Removes
   only the seventeen Opportunity Slate procedures and the twelve tables this
   migration added.

   SLICE OS-2 extended every list below. The proposal tables hold employer
   wording and the member's own corrections just as the OS-1 tables do, so
   they get exactly the same refusal: a rollback that quietly discarded
   PeerSlate's readings and a member's decisions about them would be a data
   loss dressed up as a schema change.

   SLICE OS-3 extended them again and this header did not follow (2026-08-04
   independent review, finding F12): the counts still read "thirteen
   procedures and the eight tables" after four procedures and four tables had
   been added. The lists below were correct throughout; the summary was not.
   A member RESPONSE is the strongest case in the file for the refusal - it is
   the member's own words about their own experience, and nothing else in this
   store re-creates it.

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
           OR OBJECT_ID(N'dbo.opportunity_source_reviews', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_source_concerns', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_requirement_sets', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_requirement_set_versions', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_requirement_statements', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_analyses', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_analysis_statements', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_analysis_citations', N'U') IS NOT NULL
           OR OBJECT_ID(N'dbo.opportunity_responses', N'U') IS NOT NULL
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
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_GetOpportunitySourceReviewForOwner'),
        (N'usp_SaveOpportunitySourceReviewForOwner'),
        (N'usp_ResolveOpportunitySourceConcernForOwner'),
        (N'usp_GetOpportunityRequirementsForOwner'),
        (N'usp_SaveOpportunityRequirementProposalForOwner'),
        (N'usp_CorrectOpportunityRequirementStatementForOwner'),
        (N'usp_ConfirmOpportunityRequirementsForOwner'),
        (N'usp_ListOpportunityEvidenceForOwner'),
        (N'usp_GetOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityResponseForOwner');

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

    /* SLICE OS-3. Refuse before the children the analysis owns, in the
       same order the drops below take, so an operator is told about the
       innermost member record rather than about a table that only fails
       later on a foreign key. opportunity_responses is listed first among
       these because it is the only one of the four that holds text the
       MEMBER wrote. */
    IF OBJECT_ID(N'dbo.opportunity_responses', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_responses)
        THROW 53512, 'Rollback refused: opportunity_responses contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_analysis_citations', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_analysis_citations)
        THROW 53513, 'Rollback refused: opportunity_analysis_citations contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_analysis_statements', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_analysis_statements)
        THROW 53514, 'Rollback refused: opportunity_analysis_statements contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_analyses', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_analyses)
        THROW 53515, 'Rollback refused: opportunity_analyses contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_source_concerns', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_source_concerns)
        THROW 53507, 'Rollback refused: opportunity_source_concerns contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_source_reviews', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_source_reviews)
        THROW 53508, 'Rollback refused: opportunity_source_reviews contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_requirement_statements', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_requirement_statements)
        THROW 53509, 'Rollback refused: opportunity_requirement_statements contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_requirement_set_versions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_requirement_set_versions)
        THROW 53510, 'Rollback refused: opportunity_requirement_set_versions contains member records.', 1;
    IF OBJECT_ID(N'dbo.opportunity_requirement_sets', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.opportunity_requirement_sets)
        THROW 53511, 'Rollback refused: opportunity_requirement_sets contains member records.', 1;
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
    IF OBJECT_ID(N'dbo.usp_GetOpportunitySourceReviewForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunitySourceReviewForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunitySourceReviewForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunitySourceReviewForOwner;
    IF OBJECT_ID(N'dbo.usp_ResolveOpportunitySourceConcernForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResolveOpportunitySourceConcernForOwner;
    IF OBJECT_ID(N'dbo.usp_GetOpportunityRequirementsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunityRequirementsForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunityRequirementProposalForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunityRequirementProposalForOwner;
    IF OBJECT_ID(N'dbo.usp_CorrectOpportunityRequirementStatementForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CorrectOpportunityRequirementStatementForOwner;
    IF OBJECT_ID(N'dbo.usp_ConfirmOpportunityRequirementsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ConfirmOpportunityRequirementsForOwner;
    IF OBJECT_ID(N'dbo.usp_ListOpportunityEvidenceForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListOpportunityEvidenceForOwner;
    IF OBJECT_ID(N'dbo.usp_GetOpportunityAnalysisForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetOpportunityAnalysisForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunityAnalysisForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunityAnalysisForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveOpportunityResponseForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveOpportunityResponseForOwner;

    /* Children before parents, so no drop ever runs against an object a
       foreign key still points at. */
    IF OBJECT_ID(N'dbo.opportunity_responses', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_responses;
    IF OBJECT_ID(N'dbo.opportunity_analysis_citations', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_analysis_citations;
    IF OBJECT_ID(N'dbo.opportunity_analysis_statements', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_analysis_statements;
    IF OBJECT_ID(N'dbo.opportunity_analyses', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_analyses;
    IF OBJECT_ID(N'dbo.opportunity_source_concerns', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_source_concerns;
    IF OBJECT_ID(N'dbo.opportunity_source_reviews', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_source_reviews;
    IF OBJECT_ID(N'dbo.opportunity_requirement_statements', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_requirement_statements;
    IF OBJECT_ID(N'dbo.opportunity_requirement_set_versions', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_requirement_set_versions;
    IF OBJECT_ID(N'dbo.opportunity_requirement_sets', N'U') IS NOT NULL
        DROP TABLE dbo.opportunity_requirement_sets;
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
