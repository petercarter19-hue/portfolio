/* Rollback only F readers. Existing member, publication and evidence rows remain. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
DROP PROCEDURE IF EXISTS dbo.usp_GetMemberVisitorAiBySlug;
DROP PROCEDURE IF EXISTS dbo.usp_GetMemberVisitorAiPreviewForOwner;
DROP PROCEDURE IF EXISTS dbo.usp_MemberVisitorAiSnapshotInternal;
DELETE dbo.schema_migrations WHERE migration_id=N'PS-VISITOR-AI-001';
COMMIT;
END TRY
BEGIN CATCH
IF XACT_STATE()<>0 ROLLBACK;
THROW;
END CATCH;
