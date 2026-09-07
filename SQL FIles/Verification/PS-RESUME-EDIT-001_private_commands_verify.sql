/*
Structural verifier for the proposed PS-RESUME-EDIT-001 migration.

This does not claim SQL runtime, transaction, concurrency, driver, or rollback
proof. Those require a separately authorized disposable SQL Server run before
any schema application. It returns verified = 1 only for the expected installed
object shape when run after the forward migration.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Failures TABLE (failure nvarchar(500) NOT NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-EDIT-001')
    INSERT @Failures VALUES (N'Migration ledger row is absent.');
IF COL_LENGTH(N'dbo.career_credentials', N'credential_completion_status') IS NULL
    INSERT @Failures VALUES (N'Credential completion status column is absent.');
IF OBJECT_ID(N'dbo.living_resume_command_receipts', N'U') IS NULL
    INSERT @Failures VALUES (N'Command receipt table is absent.');
IF OBJECT_ID(N'dbo.usp_GetOwnerLivingResumeEditor', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner editor read procedure is absent.');
IF OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner command procedure is absent.');
IF OBJECT_ID(N'dbo.trg_living_resume_command_receipts_immutable', N'TR') IS NULL
    INSERT @Failures VALUES (N'Immutable command receipt trigger is absent.');
IF NOT EXISTS
(
    SELECT 1 FROM sys.key_constraints
    WHERE parent_object_id=OBJECT_ID(N'dbo.living_resume_command_receipts')
      AND name=N'UQ_living_resume_command_receipts_owner_command'
)
    INSERT @Failures VALUES (N'Owner and command id uniqueness is absent.');
IF NOT EXISTS
(
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id=OBJECT_ID(N'dbo.career_credentials')
      AND name=N'CK_career_credentials_completion_status'
)
    INSERT @Failures VALUES (N'Credential completion status check is absent.');

DECLARE @CommandDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner'));
IF @CommandDefinition NOT LIKE N'%SET TRANSACTION ISOLATION LEVEL SERIALIZABLE%'
    INSERT @Failures VALUES (N'Command boundary is not serializable.');
IF @CommandDefinition NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
    INSERT @Failures VALUES (N'Command receipt and record locks are absent.');
IF @CommandDefinition NOT LIKE N'%@UserKey%'
   OR @CommandDefinition LIKE N'%@OwnerProfileId%'
    INSERT @Failures VALUES (N'Command identity boundary is not server-derived.');
IF @CommandDefinition NOT LIKE N'%entity_publication_versions%'
   OR @CommandDefinition NOT LIKE N'%entity_access_grants%'
   OR @CommandDefinition NOT LIKE N'%content_approval_events%'
    INSERT @Failures VALUES (N'Published and history-bearing protection is incomplete.');

IF EXISTS (SELECT 1 FROM @Failures)
BEGIN
    SELECT failure FROM @Failures ORDER BY failure;
    THROW 52010, 'PS-RESUME-EDIT-001 structural verification failed.', 1;
END;

SELECT CONVERT(bit, 1) AS verified,
       N'PS-RESUME-EDIT-001 structural object contract only; runtime proof remains outstanding.' AS verification_scope;
