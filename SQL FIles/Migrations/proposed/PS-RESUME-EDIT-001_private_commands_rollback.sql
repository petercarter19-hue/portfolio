/*
Rollback for proposed PS-RESUME-EDIT-001. This file has not been executed.
It removes only objects and the nullable column introduced by the proposal.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.living_resume_command_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.living_resume_command_receipts)
        THROW 52011, 'Rollback refused: Living Resume command receipts are stored.', 1;
    IF COL_LENGTH(N'dbo.career_credentials', N'credential_completion_status') IS NOT NULL
       AND EXISTS
           (SELECT 1 FROM dbo.career_credentials WHERE credential_completion_status IS NOT NULL)
        THROW 52012, 'Rollback refused: explicit credential completion states are stored.', 1;

    DROP PROCEDURE IF EXISTS dbo.usp_CommitLivingResumeCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetOwnerLivingResumeEditor;
    DROP TRIGGER IF EXISTS dbo.trg_living_resume_command_receipts_immutable;
    DROP TABLE IF EXISTS dbo.living_resume_command_receipts;

    IF COL_LENGTH(N'dbo.career_credentials', N'credential_completion_status') IS NOT NULL
    BEGIN
        IF EXISTS
        (
            SELECT 1
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID(N'dbo.career_credentials')
              AND name = N'CK_career_credentials_completion_status'
        )
            ALTER TABLE dbo.career_credentials
                DROP CONSTRAINT CK_career_credentials_completion_status;
        ALTER TABLE dbo.career_credentials
            DROP COLUMN credential_completion_status;
    END;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-RESUME-EDIT-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
