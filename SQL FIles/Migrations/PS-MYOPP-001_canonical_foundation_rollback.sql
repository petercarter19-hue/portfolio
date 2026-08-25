/* PS-MYOPP-001 rollback. Refuses when C2 data or a later ledger row exists. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @AppliedAtUtc datetime2(7) =
    (
        SELECT applied_at_utc
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-MYOPP-001'
    );
    IF @AppliedAtUtc IS NULL
        THROW 55510, 'PS-MYOPP-001 is not recorded in the schema ledger.', 1;
    IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id <> N'PS-MYOPP-001' AND applied_at_utc > @AppliedAtUtc)
        THROW 55511, 'PS-MYOPP-001 rollback refused because a later migration is recorded.', 1;
    IF EXISTS (SELECT 1 FROM dbo.myopp_source_policies)
       OR EXISTS (SELECT 1 FROM dbo.myopp_source_receipts)
       OR EXISTS (SELECT 1 FROM dbo.myopp_source_listings)
       OR EXISTS (SELECT 1 FROM dbo.myopp_source_versions)
       OR EXISTS (SELECT 1 FROM dbo.myopp_source_version_receipt_links)
       OR EXISTS (SELECT 1 FROM dbo.myopp_canonical_opportunities)
       OR EXISTS (SELECT 1 FROM dbo.myopp_requirement_versions)
       OR EXISTS (SELECT 1 FROM dbo.myopp_requirement_items)
       OR EXISTS (SELECT 1 FROM dbo.myopp_canonical_field_attributions)
       OR EXISTS (SELECT 1 FROM dbo.myopp_canonical_events)
       OR EXISTS (SELECT 1 FROM dbo.myopp_content_tombstones)
        THROW 55512, 'PS-MYOPP-001 rollback refused because C2 data exists.', 1;

    DROP PROCEDURE dbo.usp_myopp_tombstone_listing_content;
    DROP TRIGGER dbo.trg_myopp_canonical_events_guard;
    DROP TRIGGER dbo.trg_myopp_content_tombstones_immutable;
    DROP TRIGGER dbo.trg_myopp_source_version_receipt_links_immutable;
    DROP TRIGGER dbo.trg_myopp_canonical_field_attributions_terminal_guard;
    DROP TRIGGER dbo.trg_myopp_requirement_items_terminal_guard;
    DROP TRIGGER dbo.trg_myopp_requirement_versions_terminal_guard;
    DROP TRIGGER dbo.trg_myopp_source_listings_terminal_guard;
    DROP TRIGGER dbo.trg_myopp_source_versions_terminal_guard;
    DROP TRIGGER dbo.trg_myopp_source_receipts_terminal_guard;
    DROP TRIGGER dbo.trg_myopp_source_policies_revision_guard;
    DROP TABLE dbo.myopp_content_tombstones;
    DROP TABLE dbo.myopp_canonical_events;
    DROP TABLE dbo.myopp_canonical_field_attributions;
    ALTER TABLE dbo.myopp_canonical_opportunities DROP CONSTRAINT FK_myopp_canonical_opportunities_requirement_version_class;
    ALTER TABLE dbo.myopp_canonical_opportunities DROP CONSTRAINT FK_myopp_canonical_opportunities_governing_version_class;
    ALTER TABLE dbo.myopp_canonical_opportunities DROP CONSTRAINT FK_myopp_canonical_opportunities_governing_listing_class;
    ALTER TABLE dbo.myopp_canonical_opportunities DROP CONSTRAINT FK_myopp_canonical_opportunities_tombstone_class;
    DROP TABLE dbo.myopp_requirement_items;
    DROP TABLE dbo.myopp_requirement_versions;
    ALTER TABLE dbo.myopp_source_listings DROP CONSTRAINT FK_myopp_source_listings_current_version_class;
    DROP TABLE dbo.myopp_source_version_receipt_links;
    DROP TABLE dbo.myopp_source_versions;
    DROP TABLE dbo.myopp_source_listings;
    DROP TABLE dbo.myopp_source_receipts;
    DROP TABLE dbo.myopp_canonical_opportunities;
    DROP TABLE dbo.myopp_source_policies;
    DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
