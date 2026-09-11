/*
Rollback for proposed PS-RESUME-DRAFT-001. This file has not been executed.
It removes only objects introduced by the proposal.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.resume_draft_command_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_draft_command_receipts WITH (UPDLOCK, HOLDLOCK))
        THROW 52211, 'Rollback refused: resume draft command receipts are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_draft_items', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_draft_items WITH (UPDLOCK, HOLDLOCK))
        THROW 52212, 'Rollback refused: resume draft items are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_drafts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_drafts WITH (UPDLOCK, HOLDLOCK))
        THROW 52213, 'Rollback refused: resume drafts are stored.', 1;

    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeDraftCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetResumeDraftForOwner;
    DROP TRIGGER IF EXISTS dbo.trg_resume_draft_command_receipts_immutable;
    DROP TABLE IF EXISTS dbo.resume_draft_command_receipts;
    DROP TABLE IF EXISTS dbo.resume_draft_items;
    DROP TABLE IF EXISTS dbo.resume_drafts;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-RESUME-DRAFT-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
