/* Structural verification is also used by the actual generic migration gate.
   The separately authorized Python engine oracle runs two-connection races;
   this script alone never establishes concurrency or rollback acceptance. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-INTAKE-002')
    THROW 52320,'INTAKE_DURABLE_LEDGER_ABSENT',1;
IF OBJECT_ID(N'dbo.resume_intake_composer_state',N'U') IS NULL
    OR OBJECT_ID(N'dbo.resume_intake_extracted_actions',N'U') IS NULL
    OR COL_LENGTH(N'dbo.resume_intake_composer_state',N'revision') IS NULL
    OR COL_LENGTH(N'dbo.resume_intake_composer_state',N'drafts_json') IS NULL
    OR COL_LENGTH(N'dbo.resume_intake_extracted_actions',N'service_digest') IS NULL
    THROW 52320,'INTAKE_DURABLE_TABLE_SHAPE',1;
DECLARE @Procedures TABLE(name sysname NOT NULL);
INSERT @Procedures VALUES(N'usp_GetResumeIntakeDurableWorkspaceForOwner'),
    (N'usp_ReplaceResumeIntakeDraftsForOwner'),(N'usp_CommitResumeIntakeExtractedSourceForOwner');
IF EXISTS(SELECT 1 FROM @Procedures p
    WHERE OBJECT_ID(N'dbo.'+p.name,N'P') IS NULL
        OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.'+p.name)) NOT LIKE N'%SERIALIZABLE%'
        OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.'+p.name)) NOT LIKE N'%UPDLOCK%'
        OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.'+p.name)) NOT LIKE N'%ROLLBACK TRANSACTION%')
    THROW 52320,'INTAKE_DURABLE_OWNER_TRANSACTION',1;
IF EXISTS(SELECT 1 FROM @Procedures p JOIN sys.parameters a
    ON a.object_id=OBJECT_ID(N'dbo.'+p.name)
    WHERE a.name NOT IN(N'@UserKey',N'@RequestId',N'@CommandJson'))
    OR EXISTS(SELECT 1 FROM @Procedures p WHERE
        (SELECT COUNT(*) FROM sys.parameters a WHERE a.object_id=OBJECT_ID(N'dbo.'+p.name))<>
        CASE WHEN p.name=N'usp_GetResumeIntakeDurableWorkspaceForOwner' THEN 1 ELSE 3 END)
    THROW 52320,'INTAKE_DURABLE_CLOSED_OWNER_PARAMETERS',1;
DECLARE @Draft nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReplaceResumeIntakeDraftsForOwner'));
DECLARE @Source nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeIntakeExtractedSourceForOwner'));
IF @Draft NOT LIKE N'%expected_revision%' OR @Draft NOT LIKE N'%expected_lifecycle_epoch%'
    OR @Source NOT LIKE N'%canonical_values%' OR @Source NOT LIKE N'%Latin1_General_100_BIN2%'
    OR @Source NOT LIKE N'%usp_CommitResumeIntakeSubmissionForOwner%'
    OR @Source NOT LIKE N'%consumed_request_id%'
    THROW 52320,'INTAKE_DURABLE_CAS_SOURCE_FENCES',1;
SELECT CONVERT(bit,1) AS verified;
