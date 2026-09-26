/* Proposed PS-RESUME-EDIT-002 structural verification; never executed here.
   This does not replace engine-backed CRUD, rollback or concurrency proof. */
SET NOCOUNT ON;
IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-EDIT-002')
    THROW 52022, 'PS-RESUME-EDIT-002 is not registered.', 1;
IF OBJECT_ID(N'dbo.career_education', N'U') IS NULL
   OR OBJECT_ID(N'dbo.usp_GetOwnerLivingResumeEditor', N'P') IS NULL
   OR OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner', N'P') IS NULL
    THROW 52022, 'Education editor objects are missing.', 1;
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE parent_object_id=OBJECT_ID(N'dbo.living_resume_command_receipts')
                 AND name=N'CK_living_resume_command_receipts_type'
                 AND is_disabled=0 AND is_not_trusted=0
                 AND definition LIKE N'%create_education%'
                 AND definition LIKE N'%update_education%'
                 AND definition LIKE N'%remove_education%')
   OR NOT EXISTS (SELECT 1 FROM sys.check_constraints
                  WHERE parent_object_id=OBJECT_ID(N'dbo.living_resume_command_receipts')
                    AND name=N'CK_living_resume_command_receipts_record_type'
                    AND is_disabled=0 AND is_not_trusted=0
                    AND definition LIKE N'%education%')
    THROW 52022, 'Education receipt constraints are missing or untrusted.', 1;
DECLARE @Reader nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetOwnerLivingResumeEditor')),
        @Writer nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner'));
-- Publication retains the predecessor implementation in Core. Check the real
-- public dependency chain before applying the unchanged predecessor checks there.
DECLARE @PublicationInstalled bit = CASE WHEN EXISTS
    (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-PUBLICATION-001') THEN 1 ELSE 0 END;
IF @PublicationInstalled=1
BEGIN
    IF @Writer IS NULL
       OR OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'P') IS NULL
       OR OBJECT_ID(N'dbo.usp_ResumePublicationGuardLegacyMutator', N'P') IS NULL
       OR NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies
           WHERE referencing_id=OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner')
             AND referenced_id=OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore'))
       OR NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies
           WHERE referencing_id=OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner')
             AND referenced_id=OBJECT_ID(N'dbo.usp_ResumePublicationGuardLegacyMutator'))
       OR @Writer NOT LIKE N'%SET TRANSACTION ISOLATION LEVEL SERIALIZABLE%'
       OR @Writer NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
       OR @Writer NOT LIKE N'%app_user.user_key = @UserKey%'
       OR @Writer LIKE N'%@OwnerProfileId%'
        THROW 52022, 'Publication wrapper or retained predecessor linkage is invalid.', 1;
    SET @Writer=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore'));
END
ELSE IF OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'P') IS NOT NULL
    THROW 52022, 'Unexpected retained Core without Publication.', 1;
IF @Writer IS NULL
    THROW 52022, 'Predecessor command definition is inaccessible.', 1;

IF @Reader IS NULL OR @Writer IS NULL
   OR @Reader NOT LIKE N'%JOIN dbo.career_education AS education%'
   OR @Writer NOT LIKE N'%INSERT dbo.career_education%'
   OR @Writer NOT LIKE N'%UPDATE dbo.career_education%'
   OR @Writer NOT LIKE N'%RESUME_EDITOR_PROTECTED%'
    THROW 52022, 'Education procedures are missing or inaccessible.', 1;
SELECT CAST(1 AS bit) AS verified, N'PS-RESUME-EDIT-002' AS migration_id;
