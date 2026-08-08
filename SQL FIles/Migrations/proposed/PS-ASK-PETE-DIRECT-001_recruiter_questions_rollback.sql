/* ============================================================
   PS-ASK-PETE-DIRECT-001 ROLLBACK - guarded recruiter inbox reversal

   Refuses to run if PS-ASK-PETE-DIRECT-001 is not recorded, if a
   migration applied later than it is present, if any of the three
   procedures this migration owns has drifted since it applied, or - the
   rule that matters most here - if EITHER new table still holds a row.

   THIS ROLLBACK NEVER DELETES A RECRUITER QUESTION. A stored question is
   something a real person chose to send privately; discarding it because
   an operator is reversing a schema change would destroy their message
   without their knowledge and without the member ever reading it. So the
   drop path is refused outright while any row exists, and the operator is
   told to make the removal an explicit, separately decided act instead.
   The same rule the PS-WORKSHOP-002 rollback applies to already-confirmed
   knowledge, applied to a store whose content came from outside.

   Structurally: this script executes no DELETE and no UPDATE against
   dbo.recruiter_questions or dbo.recruiter_question_save_requests
   anywhere in its own control flow. Nothing it runs could remove a
   question; an empty-table DROP is the only removal it can perform.

   Forward: PS-ASK-PETE-DIRECT-001_recruiter_questions.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53970, 'Rollback refused: the migration ledger is missing.', 1;

    DECLARE @AppliedAtUtc datetime2(7);
    SELECT @AppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-ASK-PETE-DIRECT-001';

    IF @AppliedAtUtc IS NULL
       AND OBJECT_ID(N'dbo.recruiter_questions', N'U') IS NOT NULL
        THROW 53971, 'Rollback refused: the recruiter question store exists without its migration record.', 1;

    IF @AppliedAtUtc IS NULL
        THROW 53972, 'Rollback refused: PS-ASK-PETE-DIRECT-001 is not recorded.', 1;

    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE applied_at_utc > @AppliedAtUtc)
        THROW 53973, 'Rollback refused: a migration later than PS-ASK-PETE-DIRECT-001 is present.', 1;

    /* Content guard. Reversing the schema must never be the thing that
       destroys somebody's message. */
    IF OBJECT_ID(N'dbo.recruiter_questions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.recruiter_questions)
        THROW 53974, 'Rollback refused: recruiter questions are stored. Removing real messages is a separate, explicit decision.', 1;

    IF OBJECT_ID(N'dbo.recruiter_question_save_requests', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.recruiter_question_save_requests)
        THROW 53975, 'Rollback refused: the recruiter question idempotency ledger is not empty.', 1;

    /* Drift guard on the three procedures this migration owns. If any
       changed after it applied - by any path other than this migration's
       own forward script - dropping them would silently discard an
       ungoverned edit no proof here can vouch for. */
    DECLARE @ProcedureHashPropertyName sysname = N'PS_ASK_PETE_DIRECT_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_SubmitRecruiterQuestion'),
        (N'usp_ListRecruiterQuestionsForOwner'),
        (N'usp_SetRecruiterQuestionStatusForOwner');
    IF EXISTS
    (
        SELECT 1 FROM @ProtectedProcedures p
        LEFT JOIN sys.procedures o ON o.schema_id = SCHEMA_ID(N'dbo') AND o.name = p.procedure_name
        LEFT JOIN sys.extended_properties x ON x.class = 1 AND x.major_id = o.object_id
             AND x.minor_id = 0 AND x.name = @ProcedureHashPropertyName
        WHERE o.object_id IS NULL OR x.major_id IS NULL
           OR CONVERT(nvarchar(64), x.value) <> CONVERT(nvarchar(64),
              HASHBYTES('SHA2_256', OBJECT_DEFINITION(o.object_id)), 2)
    )
        THROW 53976, 'Rollback refused: a protected PS-ASK-PETE-DIRECT-001 procedure changed after it applied.', 1;

    IF OBJECT_ID(N'dbo.usp_SetRecruiterQuestionStatusForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SetRecruiterQuestionStatusForOwner;
    IF OBJECT_ID(N'dbo.usp_ListRecruiterQuestionsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListRecruiterQuestionsForOwner;
    IF OBJECT_ID(N'dbo.usp_SubmitRecruiterQuestion', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SubmitRecruiterQuestion;

    /* Child first: the ledger's foreign key points at the question table. */
    IF OBJECT_ID(N'dbo.recruiter_question_save_requests', N'U') IS NOT NULL
        DROP TABLE dbo.recruiter_question_save_requests;
    IF OBJECT_ID(N'dbo.recruiter_questions', N'U') IS NOT NULL
        DROP TABLE dbo.recruiter_questions;

    EXEC dbo.usp_AppendAuditEvent
        @ActionType = N'schema.migration.rolled_back',
        @EntityType = N'database_migration',
        @Outcome = N'success',
        @MetadataJson = N'{"migration_id":"PS-ASK-PETE-DIRECT-001"}';

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-ASK-PETE-DIRECT-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
