/*
Structural verifier for the proposed PS-RESUME-INTAKE-001 migration.

This does not claim SQL runtime, transaction, concurrency, driver, or rollback
proof. Those require a separately authorized disposable SQL Server run before
any schema application. It returns verified = 1 only for the expected installed
object shape when run after the forward migration.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Failures TABLE (failure nvarchar(500) NOT NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-INTAKE-001')
    INSERT @Failures VALUES (N'Migration ledger row is absent.');
IF OBJECT_ID(N'dbo.resume_intake_owner_state', N'U') IS NULL
    INSERT @Failures VALUES (N'Owner state table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_submissions', N'U') IS NULL
    INSERT @Failures VALUES (N'Submission table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_sources', N'U') IS NULL
    INSERT @Failures VALUES (N'Source table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_jobs', N'U') IS NULL
    INSERT @Failures VALUES (N'Job table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_proposals', N'U') IS NULL
    INSERT @Failures VALUES (N'Proposal table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_results', N'U') IS NULL
    INSERT @Failures VALUES (N'Per-item result table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_command_receipts', N'U') IS NULL
    INSERT @Failures VALUES (N'Command receipt table is absent.');
IF OBJECT_ID(N'dbo.resume_intake_recording_claims', N'U') IS NULL
    INSERT @Failures VALUES (N'Recording provider claim table is absent.');
IF OBJECT_ID(N'dbo.usp_GetResumeIntakeWorkspaceForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner workspace read procedure is absent.');
IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeSubmissionForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner submission procedure is absent.');
IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeRecordingForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner recording procedure is absent.');
IF OBJECT_ID(N'dbo.usp_ClaimResumeIntakeRecordingForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner recording claim procedure is absent.');
IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeProposalDecisionForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner proposal decision procedure is absent.');
IF OBJECT_ID(N'dbo.usp_SetResumeGuideStatusForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner guide status procedure is absent.');
IF OBJECT_ID(N'dbo.usp_PurgeResumeIntakeSourceForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Owner source purge procedure is absent.');
IF OBJECT_ID(N'dbo.usp_CompleteResumeIntakeJobForOwner', N'P') IS NULL
    INSERT @Failures VALUES (N'Worker job completion procedure is absent.');
IF OBJECT_ID(N'dbo.trg_resume_intake_submissions_immutable', N'TR') IS NULL
    INSERT @Failures VALUES (N'Immutable submission trigger is absent.');
IF OBJECT_ID(N'dbo.trg_resume_intake_receipts_immutable', N'TR') IS NULL
    INSERT @Failures VALUES (N'Immutable receipt trigger is absent.');

-- The receipts carry the service digest and a structural result.
IF COL_LENGTH(N'dbo.resume_intake_command_receipts', N'service_digest') IS NULL
    INSERT @Failures VALUES (N'Receipt service digest column is absent.');
IF COL_LENGTH(N'dbo.resume_intake_command_receipts', N'result_json') IS NULL
    INSERT @Failures VALUES (N'Receipt result column is absent.');
IF COL_LENGTH(N'dbo.resume_intake_owner_state', N'last_receipt_json') IS NULL
    INSERT @Failures VALUES (N'Owner state has no durable last receipt.');
IF COL_LENGTH(N'dbo.resume_intake_proposals', N'confidence') IS NULL
    INSERT @Failures VALUES (N'Proposal confidence column is absent.');
IF COL_LENGTH(N'dbo.resume_intake_recording_claims', N'lease_id') IS NULL
   OR COL_LENGTH(N'dbo.resume_intake_recording_claims', N'source_key') IS NULL
   OR COL_LENGTH(N'dbo.resume_intake_recording_claims', N'lease_expires_at_utc') IS NULL
    INSERT @Failures VALUES (N'Recording claim lease/source fence is absent.');

DECLARE @ApplyDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ResumeIntakeApplyCanonicalIntents'));
IF @ApplyDefinition NOT LIKE N'%usp_CommitLivingResumeCommandForOwner%'
    INSERT @Failures VALUES (N'The new-fact canonical boundary is not called.');
IF @ApplyDefinition NOT LIKE N'%usp_CommitResumeDraftCommandForOwner%'
    INSERT @Failures VALUES (N'The private draft overlay boundary is not called.');
IF @ApplyDefinition NOT LIKE N'%living_resume%'
   OR @ApplyDefinition NOT LIKE N'%resume_draft%'
    INSERT @Failures VALUES (N'The canonical boundary dispatch is absent.');
IF @ApplyDefinition LIKE N'%resume_display = 1%'
    INSERT @Failures VALUES (N'An intake path must never grant display permission.');

DECLARE @SubmissionDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwner'));
IF @SubmissionDefinition NOT LIKE N'%SET TRANSACTION ISOLATION LEVEL SERIALIZABLE%'
    INSERT @Failures VALUES (N'Submission boundary is not serializable.');
IF @SubmissionDefinition NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
    INSERT @Failures VALUES (N'Submission receipt locks are absent.');
IF @SubmissionDefinition NOT LIKE N'%@UserKey%'
   OR @SubmissionDefinition LIKE N'%@OwnerProfileId%'
    INSERT @Failures VALUES (N'Submission identity boundary is not server-derived.');
IF @SubmissionDefinition NOT LIKE N'%RESUME_INTAKE_IDEMPOTENCY_CONFLICT%'
    INSERT @Failures VALUES (N'Payload-aware idempotency conflict is absent.');
IF @SubmissionDefinition NOT LIKE N'%$.canonical_intents%'
    INSERT @Failures VALUES (N'The declared submission command does not read $.canonical_intents.');
IF @SubmissionDefinition NOT LIKE N'%$.sources%'
   OR @SubmissionDefinition NOT LIKE N'%$.jobs%'
   OR @SubmissionDefinition NOT LIKE N'%$.proposals%'
   OR @SubmissionDefinition NOT LIKE N'%$.results%'
    INSERT @Failures VALUES (N'The declared submission command does not persist sources/jobs/proposals/results.');
IF @SubmissionDefinition NOT LIKE N'%$.last_receipt%'
    INSERT @Failures VALUES (N'The durable last receipt is not persisted.');
IF @SubmissionDefinition NOT LIKE N'%submission_key, source_key, kind%'
    INSERT @Failures VALUES (N'The recording source binding is not declared.');
IF @SubmissionDefinition NOT LIKE N'%$.entrance%'
    INSERT @Failures VALUES (N'The recording command does not carry its entrance.');
IF @SubmissionDefinition NOT LIKE N'%resume_intake_recording_claims%'
   OR @SubmissionDefinition NOT LIKE N'%$.lease_id%'
   OR @SubmissionDefinition NOT LIKE N'%$.lifecycle_epoch%'
    INSERT @Failures VALUES (N'Recording finalization is not bound to its durable claim fence.');

DECLARE @RecordingClaimDefinition nvarchar(max) =
    OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ClaimResumeIntakeRecordingForOwner'));
IF @RecordingClaimDefinition NOT LIKE N'%SET TRANSACTION ISOLATION LEVEL SERIALIZABLE%'
   OR @RecordingClaimDefinition NOT LIKE N'%WITH (UPDLOCK, HOLDLOCK)%'
    INSERT @Failures VALUES (N'Recording provider claim is not atomically owner scoped.');
IF @RecordingClaimDefinition NOT LIKE N'%recovery_required%'
   OR @RecordingClaimDefinition LIKE N'%SET lease_id = NEWID%'
    INSERT @Failures VALUES (N'Recording claim does not preserve ambiguous provider custody.');

DECLARE @ReadDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetResumeIntakeWorkspaceForOwner'));
IF @ReadDefinition NOT LIKE N'%workspace_json%'
   OR @ReadDefinition NOT LIKE N'%lifecycle_epoch%'
   OR @ReadDefinition NOT LIKE N'%proposals%'
   OR @ReadDefinition NOT LIKE N'%receipts%'
   OR @ReadDefinition NOT LIKE N'%last_receipt_json%'
    INSERT @Failures VALUES (N'The workspace read does not return the declared snapshot JSON.');

DECLARE @DecisionDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitResumeIntakeProposalDecisionForOwner'));
IF @DecisionDefinition NOT LIKE N'%RESUME_INTAKE_CHANGED%'
    INSERT @Failures VALUES (N'Stale proposal decision refusal is absent.');
IF @DecisionDefinition NOT LIKE N'%target_access_revision%'
    INSERT @Failures VALUES (N'Proposal acceptance does not check the captured target access revision.');
IF @DecisionDefinition NOT LIKE N'%service_digest%'
    INSERT @Failures VALUES (N'Decision replay does not use the service digest.');

DECLARE @CompletionDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CompleteResumeIntakeJobForOwner'));
IF @CompletionDefinition NOT LIKE N'%RESUME_INTAKE_STALE_JOB%'
    INSERT @Failures VALUES (N'Late-job fence refusal is absent.');
IF @CompletionDefinition NOT LIKE N'%source_version%'
    INSERT @Failures VALUES (N'Job completion does not re-prove the source version fence.');

DECLARE @PurgeDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_PurgeResumeIntakeSourceForOwner'));
IF @PurgeDefinition NOT LIKE N'%source_text = NULL%'
    INSERT @Failures VALUES (N'Source purge does not clear the stored text.');
IF @PurgeDefinition NOT LIKE N'%structured_values_json = NULL%'
    INSERT @Failures VALUES (N'Source purge does not clear structured member values.');
IF @PurgeDefinition NOT LIKE N'%{"redacted":true}%'
    INSERT @Failures VALUES (N'Source purge does not redact retained proposal copies.');
IF @PurgeDefinition NOT LIKE N'%service_digest%'
    INSERT @Failures VALUES (N'Purge is not idempotent on the service digest.');
IF @PurgeDefinition LIKE N'%slate_entities%'
   OR @PurgeDefinition LIKE N'%career_%'
   OR @PurgeDefinition LIKE N'%entry_policy_records%'
    INSERT @Failures VALUES (N'Purge must not touch independently accepted canonical content.');

DECLARE @SweepDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_SweepExpiredResumeIntakeSources'));
IF @SweepDefinition NOT LIKE N'%@Entrance%'
    INSERT @Failures VALUES (N'Retention sweep is not entrance-specific.');
IF @SweepDefinition NOT LIKE N'%RESUME_INTAKE_POLICY_NOT_SELECTED%'
    INSERT @Failures VALUES (N'Retention sweep does not refuse an unselected policy.');
IF @SweepDefinition NOT LIKE N'%owner_profile_id IN (SELECT owner_profile_id FROM @StaleOwners)%'
    INSERT @Failures VALUES (N'Retention sweep is not owner-qualified.');
IF @SweepDefinition NOT LIKE N'%created_at_utc%'
    INSERT @Failures VALUES (N'Retention sweep does not reason about draft activity.');

-- Runtime transaction ownership. db.py connects with setautocommit(True), so
-- each compound member action must open and commit its own transaction inside
-- the procedure body; SET XACT_ABORT and SERIALIZABLE do not do this.
DECLARE @TransactionBodies TABLE (name sysname NOT NULL);
INSERT @TransactionBodies (name) VALUES
    (N'usp_ClaimResumeIntakeRecordingForOwner'),
    (N'usp_CommitResumeIntakeCommandForOwner'),
    (N'usp_CommitResumeIntakeProposalDecisionForOwner'),
    (N'usp_SetResumeGuideStatusForOwner'),
    (N'usp_PurgeResumeIntakeSourceForOwner'),
    (N'usp_ClaimResumeIntakeJobsForOwner'),
    (N'usp_CompleteResumeIntakeJobForOwner'),
    (N'usp_SweepExpiredResumeIntakeSources');

DECLARE @BodyName sysname;
DECLARE @BodyDefinition nvarchar(max);
DECLARE body_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT name FROM @TransactionBodies;
OPEN body_cursor;
FETCH NEXT FROM body_cursor INTO @BodyName;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @BodyDefinition = OBJECT_DEFINITION(OBJECT_ID(@BodyName));
    IF @BodyDefinition IS NULL
        INSERT @Failures VALUES (N'A compound procedure body is absent.');
    ELSE IF @BodyDefinition NOT LIKE N'%BEGIN TRANSACTION%'
         OR @BodyDefinition NOT LIKE N'%COMMIT TRANSACTION%'
         OR @BodyDefinition NOT LIKE N'%BEGIN CATCH%'
        INSERT @Failures VALUES (N'A compound procedure body owns no runtime transaction.');
    FETCH NEXT FROM body_cursor INTO @BodyName;
END;
CLOSE body_cursor;
DEALLOCATE body_cursor;

IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ResumeIntakeApplyCanonicalIntents')) LIKE N'%BEGIN TRANSACTION%'
    INSERT @Failures VALUES (N'The canonical intent helper must not commit independently.');
IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ResumeIntakeApplyCanonicalIntents')) NOT LIKE N'%usp_CommitLivingResumeCommandForOwner%'
    INSERT @Failures VALUES (N'The helper does not call the canonical editor boundary.');

IF EXISTS (SELECT 1 FROM @Failures)
BEGIN
    SELECT failure FROM @Failures ORDER BY failure;
    THROW 52320, 'PS-RESUME-INTAKE-001 structural verification failed.', 1;
END;

SELECT CONVERT(bit, 1) AS verified,
       N'PS-RESUME-INTAKE-001 structural object contract only; runtime proof remains outstanding.' AS verification_scope;
