/* Guarded rollback. Never erase a retained original, tombstone or member metadata. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
 BEGIN TRANSACTION;
 IF OBJECT_ID(N'dbo.resume_original_files',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.resume_original_files)
  THROW 52610,'ORIGINAL_ROLLBACK_HAS_MEMBER_DATA',1;
 IF OBJECT_ID(N'dbo.resume_hosted_extraction_reservations',N'U') IS NOT NULL AND EXISTS(SELECT 1 FROM dbo.resume_hosted_extraction_reservations)
  THROW 52610,'ORIGINAL_ROLLBACK_HAS_MEMBER_DATA',1;
 DROP PROCEDURE IF EXISTS dbo.usp_FinishResumeHostedExtractionForOwner;
 DROP PROCEDURE IF EXISTS dbo.usp_ReserveResumeHostedExtractionForOwner;
 DROP TABLE IF EXISTS dbo.resume_hosted_extraction_reservations;
 DROP TABLE IF EXISTS dbo.resume_hosted_extraction_budgets;
 DROP PROCEDURE IF EXISTS dbo.usp_GetResumeHostedReadiness;
 DROP PROCEDURE IF EXISTS dbo.usp_CompleteResumeOriginalCleanup;
 DROP PROCEDURE IF EXISTS dbo.usp_ClaimResumeOriginalCleanup;
 DROP PROCEDURE IF EXISTS dbo.usp_CommitResumeOriginalFileForOwner;
 DROP PROCEDURE IF EXISTS dbo.usp_GetResumeOriginalFilesForOwner;
 DROP TABLE IF EXISTS dbo.resume_original_files;
 DELETE FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-HOSTED-001';
 COMMIT TRANSACTION;
END TRY
BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK TRANSACTION; THROW; END CATCH;
