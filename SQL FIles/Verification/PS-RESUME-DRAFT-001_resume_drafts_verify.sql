/*
Structural verifier for the proposed PS-RESUME-DRAFT-001 migration.

This does not claim SQL runtime, transaction, concurrency, driver, or rollback
proof. Those require a separately authorized disposable SQL Server run before
any schema application. It returns verified = 1 only for the expected installed
object shape when run after the forward migration.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Failures TABLE (failure nvarchar(500) NOT NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-DRAFT-001')
    INSERT @Failures VALUES (N'Migration ledger row is absent.');
IF OBJECT_ID(N'dbo.resume_drafts', N'U') IS NULL
    INSERT @Failures VALUES (N'Resume draft table is absent.');
IF OBJECT_ID(N'dbo.resume_draft_items', N'U') IS NULL
    INSERT @Failures VALUES (N'Resume draft item table is absent.');
IF OBJECT_ID(N'dbo.resume_draft_command_receipts', N'U') IS NULL
    INSERT @Failures VALUES (N'Command receipt table is absent.');
IF OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner command procedure is absent.');
IF OBJECT_ID(N'dbo.usp_GetResumeDraftForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner read procedure is absent.');
IF OBJECT_ID(N'dbo.trg_resume_draft_command_receipts_immutable', N'TR') IS NULL
    INSERT @Failures VALUES (N'Immutable command receipt trigger is absent.');

DECLARE @CommandDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner'));
IF @CommandDefinition NOT LIKE N'%SET TRANSACTION ISOLATION LEVEL SERIALIZABLE%'
    INSERT @Failures VALUES (N'Command boundary is not serializable.');
IF @CommandDefinition NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
    INSERT @Failures VALUES (N'Command receipt and record locks are absent.');
IF @CommandDefinition NOT LIKE N'%@UserKey%'
   OR @CommandDefinition LIKE N'%@OwnerProfileId%'
    INSERT @Failures VALUES (N'Command identity boundary is not server-derived.');
IF @CommandDefinition NOT LIKE N'%RESUME_DRAFT_IDEMPOTENCY_CONFLICT%'
    INSERT @Failures VALUES (N'Payload-aware idempotency conflict is absent.');
IF @CommandDefinition LIKE N'%usp_Publish%'
    INSERT @Failures VALUES (N'Publication procedure must not be part of this draft migration.');

IF EXISTS (SELECT 1 FROM @Failures)
BEGIN
    SELECT failure FROM @Failures ORDER BY failure;
    THROW 52210, 'PS-RESUME-DRAFT-001 structural verification failed.', 1;
END;

SELECT CONVERT(bit, 1) AS verified,
       N'PS-RESUME-DRAFT-001 structural object contract only; runtime proof remains outstanding.' AS verification_scope;
