/* Read-only F verifier; actual behavior is established by the isolated engine proof. */
SET NOCOUNT ON;
IF OBJECT_ID(N'dbo.usp_GetMemberVisitorAiBySlug',N'P') IS NULL
 OR OBJECT_ID(N'dbo.usp_GetMemberVisitorAiPreviewForOwner',N'P') IS NULL
 OR OBJECT_ID(N'dbo.usp_MemberVisitorAiSnapshotInternal',N'P') IS NULL
 THROW 54210, 'Visitor AI reader is missing.', 1;
IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-VISITOR-AI-001')
 THROW 54211, 'Visitor AI migration record is missing.', 1;
IF NOT EXISTS(SELECT 1 FROM sys.database_permissions
 WHERE major_id=OBJECT_ID(N'dbo.usp_MemberVisitorAiSnapshotInternal')
 AND grantee_principal_id=DATABASE_PRINCIPAL_ID(N'public') AND permission_name=N'EXECUTE' AND state=N'D')
 THROW 54212, 'Internal visitor AI reader must be denied.', 1;
IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetMemberVisitorAiBySlug')) NOT LIKE N'%@OwnerPreview=0%'
 OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetMemberVisitorAiPreviewForOwner')) NOT LIKE N'%@OwnerPreview=1%'
 THROW 54213, 'Visitor AI wrapper use boundary is missing.', 1;
SELECT N'PS-VISITOR-AI-001' migration_id,N'passed' verification_status,CAST(1 AS bit) AS verified;
