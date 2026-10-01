SET NOCOUNT ON;
IF OBJECT_ID(N'dbo.resume_original_files',N'U') IS NULL OR
 OBJECT_ID(N'dbo.resume_hosted_extraction_budgets',N'U') IS NULL OR
 OBJECT_ID(N'dbo.resume_hosted_extraction_reservations',N'U') IS NULL OR
 OBJECT_ID(N'dbo.usp_ReserveResumeHostedExtractionForOwner',N'P') IS NULL OR
 OBJECT_ID(N'dbo.usp_FinishResumeHostedExtractionForOwner',N'P') IS NULL OR
 OBJECT_ID(N'dbo.usp_GetResumeOriginalFilesForOwner',N'P') IS NULL OR
 OBJECT_ID(N'dbo.usp_CommitResumeOriginalFileForOwner',N'P') IS NULL OR
 OBJECT_ID(N'dbo.usp_ClaimResumeOriginalCleanup',N'P') IS NULL OR
 OBJECT_ID(N'dbo.usp_CompleteResumeOriginalCleanup',N'P') IS NULL OR
 OBJECT_ID(N'dbo.usp_GetResumeHostedReadiness',N'P') IS NULL OR
 NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-HOSTED-001')
 THROW 52611,'ORIGINAL_SCHEMA_VERIFY_FAILED',1;
SELECT CAST(1 AS bit) AS verified;
