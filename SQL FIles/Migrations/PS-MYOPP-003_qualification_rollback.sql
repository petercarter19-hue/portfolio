/* PS-MYOPP-003 rollback. Refuses with C5 member data or any later ledger row. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-MYOPP-003'
    );
    IF @AppliedAtUtc IS NULL
        THROW 55680, 'PS-MYOPP-003 is not recorded in the schema ledger.', 1;
    IF EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations
        WHERE migration_id <> N'PS-MYOPP-003'
          AND applied_at_utc > @AppliedAtUtc
    )
        THROW 55681, 'PS-MYOPP-003 rollback refused because a later migration is recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.myopp_qualification_commands)
       OR EXISTS (SELECT 1 FROM dbo.myopp_assessment_evidence_links)
       OR EXISTS (SELECT 1 FROM dbo.myopp_assessment_revisions)
       OR EXISTS (SELECT 1 FROM dbo.myopp_assessments)
       OR EXISTS (SELECT 1 FROM dbo.myopp_practical_fit_observations)
       OR EXISTS (SELECT 1 FROM dbo.myopp_evidence_grants)
        THROW 55682, 'PS-MYOPP-003 rollback refused because C5 member data exists.', 1;

    DROP TRIGGER dbo.trg_myopp_qualification_commands_immutable;
    DROP TRIGGER dbo.trg_myopp_assessment_evidence_links_immutable;
    DROP TRIGGER dbo.trg_myopp_assessment_revisions_immutable;
    DROP TRIGGER dbo.trg_myopp_assessments_head_guard;
    DROP TRIGGER dbo.trg_myopp_assessments_requirement_consistency;
    DROP TRIGGER dbo.trg_myopp_practical_fit_observations_guard;
    DROP TRIGGER dbo.trg_myopp_evidence_grants_transition_guard;

    DROP TABLE dbo.myopp_qualification_commands;
    DROP TABLE dbo.myopp_assessment_evidence_links;
    DROP TABLE dbo.myopp_assessment_revisions;
    DROP TABLE dbo.myopp_assessments;
    DROP TABLE dbo.myopp_practical_fit_observations;
    DROP TABLE dbo.myopp_evidence_grants;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
