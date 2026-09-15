/*
Rollback for proposed PS-RESUME-MEDIA-001. This file has not been executed.
It removes only objects introduced by the proposal, and it refuses to remove
anything while member media placements or command receipts are stored.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.resume_media_command_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_media_command_receipts WITH (UPDLOCK, HOLDLOCK))
        THROW 52311, 'Rollback refused: resume media command receipts are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_media_placements', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_media_placements WITH (UPDLOCK, HOLDLOCK))
        THROW 52312, 'Rollback refused: resume media placements are stored.', 1;

    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeMediaCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetResumeMediaDraftForOwner;
    DROP TRIGGER IF EXISTS dbo.trg_resume_media_command_receipts_immutable;
    DROP TABLE IF EXISTS dbo.resume_media_command_receipts;
    DROP TABLE IF EXISTS dbo.resume_media_placements;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-RESUME-MEDIA-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
