/*
Structural verifier for the proposed PS-RESUME-MEDIA-001 migration.

This does not claim SQL runtime, transaction, concurrency, driver, permission,
or rollback proof. Those require a separately authorized disposable SQL Server
run before any schema application. It returns verified = 1 only for the
expected installed object shape when run after the forward migration.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Failures TABLE (failure nvarchar(500) NOT NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-MEDIA-001')
    INSERT @Failures VALUES (N'Migration ledger row is absent.');
IF OBJECT_ID(N'dbo.resume_media_placements', N'U') IS NULL
    INSERT @Failures VALUES (N'Resume media placement table is absent.');
IF OBJECT_ID(N'dbo.resume_media_command_receipts', N'U') IS NULL
    INSERT @Failures VALUES (N'Resume media command receipt table is absent.');
IF OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner media command procedure is absent.');
IF OBJECT_ID(N'dbo.usp_GetResumeMediaDraftForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner media read procedure is absent.');
IF OBJECT_ID(N'dbo.trg_resume_media_command_receipts_immutable', N'TR') IS NULL
    INSERT @Failures VALUES (N'Immutable media receipt trigger is absent.');
IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.resume_media_placements')
      AND name = N'CK_resume_media_placements_slot'
)
    INSERT @Failures VALUES (N'Slot vocabulary constraint is absent.');

DECLARE @CommandDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwner'));
DECLARE @ReadDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetResumeMediaDraftForOwner'));
IF @CommandDefinition NOT LIKE N'%SET TRANSACTION ISOLATION LEVEL SERIALIZABLE%'
    INSERT @Failures VALUES (N'Command boundary is not serializable.');
-- The connection is autocommit: each procedure must open and close its own
-- transaction and roll it back on failure, or nothing commits at all.
IF @CommandDefinition NOT LIKE N'%BEGIN TRANSACTION%'
   OR @CommandDefinition NOT LIKE N'%COMMIT TRANSACTION%'
   OR @CommandDefinition NOT LIKE N'%BEGIN CATCH%'
   OR @CommandDefinition NOT LIKE N'%ROLLBACK TRANSACTION%'
    INSERT @Failures VALUES (N'Command procedure lacks its own transaction and rollback.');
IF @ReadDefinition NOT LIKE N'%BEGIN TRANSACTION%'
   OR @ReadDefinition NOT LIKE N'%COMMIT TRANSACTION%'
   OR @ReadDefinition NOT LIKE N'%BEGIN CATCH%'
    INSERT @Failures VALUES (N'Read procedure lacks its own transaction and rollback.');
IF @CommandDefinition NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
    INSERT @Failures VALUES (N'Command receipt, placement and draft locks are absent.');
IF @CommandDefinition NOT LIKE N'%@UserKey%'
   OR @CommandDefinition LIKE N'%@OwnerProfileId%'
    INSERT @Failures VALUES (N'Command identity boundary is not server-derived.');
IF @CommandDefinition NOT LIKE N'%resume_drafts%'
    INSERT @Failures VALUES (N'Command does not fence the shared Resume draft version.');
IF @CommandDefinition NOT LIKE N'%RESUME_MEDIA_IDEMPOTENCY_CONFLICT%'
    INSERT @Failures VALUES (N'Payload-aware idempotency conflict is absent.');
IF @CommandDefinition LIKE N'%usp_Publish%'
    INSERT @Failures VALUES (N'Publication procedure must not be part of this media migration.');
IF @CommandDefinition NOT LIKE N'%story_banner%'
   OR @CommandDefinition NOT LIKE N'%experience_support%'
    INSERT @Failures VALUES (N'Named decorative slot vocabulary is absent.');
IF @CommandDefinition LIKE N'%portrait%'
    INSERT @Failures VALUES (N'Portrait must never be a media placement slot.');
IF @CommandDefinition NOT LIKE N'%HAVING COUNT(*) > 1%'
    INSERT @Failures VALUES (N'Duplicate-slot payload validation is absent.');
IF @CommandDefinition NOT LIKE N'%RESUME_MEDIA_VALIDATION%'
    INSERT @Failures VALUES (N'Payload validation refusal is absent.');
-- The authoritative source fence has to be inside this procedure's own
-- transaction, and the receipt digest has to be one vocabulary: a JSON hash
-- would never equal the semantic digest an exact retry carries.
IF @CommandDefinition NOT LIKE N'%capture_media_sources%'
   OR @CommandDefinition NOT LIKE N'%source_changed%'
   OR @CommandDefinition NOT LIKE N'%source.row_version%'
    INSERT @Failures VALUES (N'Authoritative photo-source fence is absent.');
IF @CommandDefinition LIKE N'%HASHBYTES%'
    INSERT @Failures VALUES (N'Receipt digest must be the semantic digest, not a JSON hash.');
IF @CommandDefinition NOT LIKE N'%@IncomingDigest IS NULL%'
   OR @CommandDefinition NOT LIKE N'%idempotency_conflict%'
    INSERT @Failures VALUES (N'Receipt replay validation is not fail closed.');
IF @CommandDefinition NOT LIKE N'%source_unavailable%'
    INSERT @Failures VALUES (N'Unverifiable catalog source refusal is absent.');
IF OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NULL
    INSERT @Failures VALUES (N'Authoritative photo source table is absent.');

IF EXISTS (SELECT 1 FROM @Failures)
BEGIN
    SELECT failure FROM @Failures ORDER BY failure;
    THROW 52310, 'PS-RESUME-MEDIA-001 structural verification failed.', 1;
END;

SELECT CONVERT(bit, 1) AS verified,
       N'PS-RESUME-MEDIA-001 structural object contract only; runtime proof remains outstanding.' AS verification_scope;
