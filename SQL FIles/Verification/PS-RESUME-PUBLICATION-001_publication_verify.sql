/*
Read-only verification for proposed PS-RESUME-PUBLICATION-001.
*/
SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.resume_sharing_state', N'U') IS NULL
    THROW 54100, 'resume_sharing_state is missing.', 1;
IF OBJECT_ID(N'dbo.resume_publication_revisions', N'U') IS NULL
    THROW 54101, 'resume_publication_revisions is missing.', 1;
IF OBJECT_ID(N'dbo.resume_publication_evidence', N'U') IS NULL
    THROW 54102, 'resume_publication_evidence is missing.', 1;
IF OBJECT_ID(N'dbo.resume_publication_receipts', N'U') IS NULL
    THROW 54103, 'resume_publication_receipts is missing.', 1;
IF OBJECT_ID(N'dbo.resume_publication_core_execute_permissions', N'U') IS NULL
    THROW 54112, 'Predecessor execute permission snapshot is missing.', 1;
IF OBJECT_ID(N'dbo.usp_CommitResumePublicationCommandForOwner', N'P') IS NULL
    THROW 54104, 'Complete publication command is missing.', 1;
IF OBJECT_ID(N'dbo.usp_GetPublicResumePublicationBySlug', N'P') IS NULL
    THROW 54105, 'Public publication reader is missing.', 1;
IF OBJECT_ID(N'dbo.usp_GetResumePublicationMediaAuthorization', N'P') IS NULL
    THROW 54106, 'Media authorization reader is missing.', 1;
IF OBJECT_ID(N'dbo.usp_ListResumePublicationPolicyForOwner', N'P') IS NULL
    THROW 54110, 'Owner publication policy reader is missing.', 1;
IF OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwnerCore', N'P') IS NULL
   OR OBJECT_ID(N'dbo.usp_ListEntryPolicyEntriesForOwnerCore', N'P') IS NULL
   OR OBJECT_ID(N'dbo.usp_GetEntryPolicyEntryForOwnerCore', N'P') IS NULL
   OR OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwner', N'P') IS NULL
   OR OBJECT_ID(N'dbo.usp_ListEntryPolicyEntriesForOwner', N'P') IS NULL
   OR OBJECT_ID(N'dbo.usp_GetEntryPolicyEntryForOwner', N'P') IS NULL
    THROW 54111, 'My Data publication bridge is missing.', 1;
IF OBJECT_ID(N'dbo.usp_ResumePublicationEncodeSourceInternal', N'P') IS NULL
    THROW 54107, 'UTF-8 codec helper is missing.', 1;
IF OBJECT_ID(N'dbo.fn_ResumePublicationUtf8', N'FN') IS NULL
    THROW 54108, 'UTF-8 conversion helper is missing.', 1;
IF COL_LENGTH(N'dbo.resume_publication_evidence', N'content_bytes') IS NULL
    THROW 54109, 'Committed evidence bytes are missing.', 1;

-- The bridge must retain its publication refusal and projection protections.
DECLARE @Guard nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ResumePublicationGuardLegacyMutator'));
IF @Guard IS NULL
   OR @Guard NOT LIKE N'%THROW 54050,%'
   OR @Guard NOT LIKE N'%THROW 54051,%'
   OR @Guard NOT LIKE N'%THROW 54052,%'
   OR @Guard NOT LIKE N'%THROW 54053,%'
   OR @Guard NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
   OR @Guard NOT LIKE N'%owner_profile_id = @ProfileId%'
   OR NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies
       WHERE referencing_id=OBJECT_ID(N'dbo.usp_ResumePublicationGuardLegacyMutator')
         AND referenced_id=OBJECT_ID(N'dbo.resume_sharing_state'))
   OR NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies
       WHERE referencing_id=OBJECT_ID(N'dbo.usp_ResumePublicationGuardLegacyMutator')
         AND referenced_id=OBJECT_ID(N'dbo.resume_publication_revisions'))
    THROW 54113, 'Publication legacy guard protection is incomplete.', 1;
DECLARE @AfterPolicy nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ResumePublicationApplyAfterPolicyInternal'));
IF @AfterPolicy IS NULL
   OR @AfterPolicy NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
   OR @AfterPolicy NOT LIKE N'%owner_profile_id = @ProfileId%'
   OR NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies
       WHERE referencing_id=OBJECT_ID(N'dbo.usp_ResumePublicationApplyAfterPolicyInternal')
         AND referenced_id=OBJECT_ID(N'dbo.usp_ResumePublicationBuildManifestsInternal'))
   OR NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies
       WHERE referencing_id=OBJECT_ID(N'dbo.usp_ResumePublicationApplyAfterPolicyInternal')
         AND referenced_id=OBJECT_ID(N'dbo.usp_ResumePublicationRefreshProjectionInternal'))
    THROW 54114, 'Publication policy projection protection is incomplete.', 1;

SELECT
    N'PS-RESUME-PUBLICATION-001' AS check_name,
    N'verified' AS verified,
    N'present; runtime proof remains outstanding' AS status;
