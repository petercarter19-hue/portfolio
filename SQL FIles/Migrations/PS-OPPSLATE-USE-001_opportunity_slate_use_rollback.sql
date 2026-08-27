/* PS-OPPSLATE-USE-001 rollback. Drops the read-only procedure and the
   supporting index, and removes the ledger row. Nothing here owns member
   data, so there is no data-presence refusal: rolling this back removes a
   disclosure read path and nothing else. It still refuses out-of-order
   rollback, like every governed rollback. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-OPPSLATE-USE-001'
    );
    IF @AppliedAtUtc IS NULL
        THROW 56110, 'PS-OPPSLATE-USE-001 is not recorded in the schema ledger.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id <> N'PS-OPPSLATE-USE-001'
          AND applied_at_utc > @AppliedAtUtc
    )
        THROW 56111, 'PS-OPPSLATE-USE-001 rollback refused because a later migration is recorded.', 1;

    DROP PROCEDURE dbo.usp_GetOpportunitySlateUseForOwner;
    DROP INDEX IX_opportunity_saved_evidence_owner_use ON dbo.opportunity_saved_evidence;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-OPPSLATE-USE-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
