/*
Rollback for proposed PS-RESUME-INTAKE-001. This file has not been executed.
It removes only objects introduced by the proposal, and refuses while member
rows exist so a rollback can never discard stored submissions.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.resume_intake_command_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_command_receipts WITH (UPDLOCK, HOLDLOCK))
        THROW 52311, 'Rollback refused: resume intake command receipts are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_intake_recording_claims', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_recording_claims WITH (UPDLOCK, HOLDLOCK))
        THROW 52318, 'Rollback refused: resume intake recording claims are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_intake_results', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_results WITH (UPDLOCK, HOLDLOCK))
        THROW 52316, 'Rollback refused: resume intake results are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_intake_proposals', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_proposals WITH (UPDLOCK, HOLDLOCK))
        THROW 52312, 'Rollback refused: resume intake proposals are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_intake_jobs', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_jobs WITH (UPDLOCK, HOLDLOCK))
        THROW 52313, 'Rollback refused: resume intake jobs are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_intake_sources', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_sources WITH (UPDLOCK, HOLDLOCK))
        THROW 52314, 'Rollback refused: resume intake sources are stored.', 1;
    IF OBJECT_ID(N'dbo.resume_intake_submissions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_intake_submissions WITH (UPDLOCK, HOLDLOCK))
        THROW 52315, 'Rollback refused: resume intake submissions are stored.', 1;

    DROP PROCEDURE IF EXISTS dbo.usp_SweepExpiredResumeIntakeSources;
    DROP PROCEDURE IF EXISTS dbo.usp_CompleteResumeIntakeJobForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_ClaimResumeIntakeJobsForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_PurgeResumeIntakeSourceForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_SetResumeGuideStatusForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeIntakeProposalDecisionForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeIntakeRecordingForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_ClaimResumeIntakeRecordingForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeIntakeSubmissionForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeIntakeCommandForOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_ResumeIntakeApplyCanonicalIntents;
    DROP PROCEDURE IF EXISTS dbo.usp_ResumeIntakeResolveOwner;
    DROP PROCEDURE IF EXISTS dbo.usp_GetResumeIntakeWorkspaceForOwner;
    DROP TRIGGER IF EXISTS dbo.trg_resume_intake_receipts_immutable;
    DROP TRIGGER IF EXISTS dbo.trg_resume_intake_submissions_immutable;
    DROP TABLE IF EXISTS dbo.resume_intake_command_receipts;
    DROP TABLE IF EXISTS dbo.resume_intake_recording_claims;
    DROP TABLE IF EXISTS dbo.resume_intake_results;
    DROP TABLE IF EXISTS dbo.resume_intake_proposals;
    DROP TABLE IF EXISTS dbo.resume_intake_jobs;
    DROP TABLE IF EXISTS dbo.resume_intake_sources;
    DROP TABLE IF EXISTS dbo.resume_intake_submissions;
    DROP TABLE IF EXISTS dbo.resume_intake_owner_state;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-RESUME-INTAKE-001';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
