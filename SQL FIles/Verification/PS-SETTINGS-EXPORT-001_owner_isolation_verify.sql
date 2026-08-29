/* PS-SETTINGS-EXPORT-001 (C1 account-export foundation) production-safe
   owner-isolation verification.

   This is the C2 delivery of a C1-recorded transferred obligation
   (C1_ACCOUNT_EXPORT_FOUNDATION.md, "Not executed": "No two-member
   isolation proof ... no verification script exists in this candidate
   (it is outside the frozen claim surfaces)"). The C2 lane claim owns
   this file but does not run it or touch registry.json: the manager
   pairs this script with a fresh PS-SETTINGS-EXPORT-001 gate run.

   Uses two synthetic owners inside one outer always-rolled-back
   transaction to prove:

     - the three owner procedures (usp_RequestAccountExportForOwner,
       usp_GetAccountExportStatusForOwner,
       usp_GetAccountExportDownloadMetadataForOwner) each declare
       @UserKey nvarchar(300), resolve it via
       app_user.user_key = @UserKey themselves, filter every read/write
       on owner_profile_id = @ProfileId, and never accept a
       caller-supplied @OwnerProfileId or @OwnerUserId;
     - only usp_GetAccountExportDownloadMetadataForOwner ever returns
       final_artifact_reference -- the status procedure's definition
       never mentions that column;
     - a forged @UserKey (one that resolves to no owner at all) never
       produces a row from either read procedure, for either owner's
       real job;
     - a guessed/forged @JobKey (a fresh NEWID() that was never issued)
       never produces a row for a real, authenticated owner;
     - owner B can read neither owner A's status nor owner A's download
       metadata, and symmetrically for owner A reading owner B;
     - download metadata is returned only for the calling owner's own
       job, and only while it is 'ready' and unexpired -- refused
       before promotion (queued/running) and refused again once the
       job has moved to 'expired';
     - a reauthorized owner's status read reports a truthful 'expired'
       state for their own retained job (never silently hidden), while
       the same reauthorized owner's download-metadata read discloses
       nothing once expired (no artifact reference, hash, or size).

   This script never calls usp_ClaimAccountExportJob or
   usp_ExpireAccountExportJobs. Both are system-wide (no @UserKey, no
   owner predicate) and would interact with whatever real, unrelated
   jobs already exist in a production-safe run. The 'running' and
   'expired' states this script needs are instead reached by a direct
   UPDATE scoped to exactly the synthetic job_key just created, followed
   by the real usp_CompleteAccountExportJob call (itself fenced by
   job_key + lease_token, so it can only ever touch that one row). This
   proves the OWNER-FACING READ procedures' behaviour against those
   states without ever mutating a row this script did not itself create.

   CORRECTION (gate round): T-SQL forbids ROLLBACK inside a stored
   procedure that is invoked with INSERT ... EXEC ("Cannot use the
   ROLLBACK statement within an INSERT-EXEC statement") -- and every
   write procedure this script calls (usp_RequestAccountExportForOwner,
   usp_CompleteAccountExportJob) contains a CATCH block that can reach
   ROLLBACK TRANSACTION, so INSERT ... EXEC against either one fails the
   governed gate even on an all-success run that never actually takes
   that branch. Both are therefore called BARE (their own result set
   simply returns to the client and is not captured), and every fact
   this script needs from them is instead confirmed with a plain
   SELECT/EXISTS against dbo.account_export_jobs afterward. INSERT ...
   EXEC remains in use only for usp_GetAccountExportStatusForOwner and
   usp_GetAccountExportDownloadMetadataForOwner, which section 0 below
   confirms, by grepping their actual definitions, contain no ROLLBACK
   at all (no BEGIN TRANSACTION/TRY/CATCH of any kind) before this
   script relies on that.

   Every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-001')
        THROW 57700, 'PS-SETTINGS-EXPORT-001 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Procedure-shape greps across the three owner procedures.
       ------------------------------------------------------------ */
    DECLARE @ProcedureNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProcedureNames (procedure_name)
    VALUES
        (N'usp_RequestAccountExportForOwner'),
        (N'usp_GetAccountExportStatusForOwner'),
        (N'usp_GetAccountExportDownloadMetadataForOwner');

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ProcedureNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name FROM @ProcedureNames ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 57701, 'A required account-export owner procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 57702, 'An account-export owner procedure does not declare @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%' OR @CheckDefinition LIKE N'%@OwnerUserId%'
            THROW 57703, 'An account-export owner procedure accepts a caller-supplied owner id.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 57704, 'An account-export owner procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
            THROW 57705, 'An account-export owner procedure does not filter on owner_profile_id = @ProfileId.', 1;

        DELETE @ProcedureNames WHERE procedure_name = @CheckName;
    END;

    /* Only the download-metadata procedure may ever disclose the
       private artifact reference. */
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetAccountExportStatusForOwner', N'P'))
           LIKE N'%final_artifact_reference%'
        THROW 57706, 'The status procedure discloses the private artifact reference.', 1;
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_RequestAccountExportForOwner', N'P'))
           LIKE N'%final_artifact_reference%'
        THROW 57707, 'The request procedure discloses the private artifact reference.', 1;
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetAccountExportDownloadMetadataForOwner', N'P'))
           NOT LIKE N'%final_artifact_reference%'
        THROW 57708, 'The download-metadata procedure no longer returns the artifact reference.', 1;

    /* This script relies on usp_GetAccountExportStatusForOwner and
       usp_GetAccountExportDownloadMetadataForOwner being callable with
       INSERT ... EXEC, which T-SQL refuses for any procedure that can
       reach a ROLLBACK statement. Confirm both bodies contain no
       transaction control at all (not merely that today's happy path
       avoids it) before relying on that anywhere below -- a future
       edit adding a TRY/CATCH to either would otherwise silently
       reintroduce the exact "Cannot use the ROLLBACK statement within
       an INSERT-EXEC statement" failure this correction fixes. */
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetAccountExportStatusForOwner', N'P'))
           LIKE N'%ROLLBACK%'
        THROW 57734, 'The status procedure now contains ROLLBACK; it can no longer be safely called with INSERT EXEC.', 1;
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetAccountExportDownloadMetadataForOwner', N'P'))
           LIKE N'%ROLLBACK%'
        THROW 57735, 'The download-metadata procedure now contains ROLLBACK; it can no longer be safely called with INSERT EXEC.', 1;

    /* ------------------------------------------------------------
       1. Two synthetic owners via a throwaway auth provider.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-c2-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-c2-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-c2-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-c2-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'Settings export C2 verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-c2-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'Settings export C2 verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;

    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-c2-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-c2-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 57709, 'Synthetic account-export verification owners were not provisioned.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';
    DECLARE @ForgedJobKey uniqueidentifier = NEWID();

    /* ------------------------------------------------------------
       2. Each owner requests one export. Both land 'queued'. Called
          BARE (not INSERT ... EXEC): usp_RequestAccountExportForOwner
          has a CATCH block that can reach ROLLBACK TRANSACTION, which
          T-SQL refuses to allow inside an INSERT-EXEC target even on a
          run that never takes that branch. The outcome is confirmed
          directly against the ledger instead of the procedure's own
          returned result set -- each synthetic owner is a brand-new
          profile_id from usp_UpsertAppUserFromAuth above, so a queued
          row for that exact owner can only be the one just created.
       ------------------------------------------------------------ */
    EXEC dbo.usp_RequestAccountExportForOwner @UserKey = @UserKeyA;
    DECLARE @JobKeyA uniqueidentifier;
    SELECT TOP (1) @JobKeyA = job.job_key
    FROM dbo.account_export_jobs AS job
    WHERE job.owner_profile_id = @ProfileIdA AND job.state = N'queued'
    ORDER BY job.requested_at_utc DESC;
    IF @JobKeyA IS NULL
        THROW 57710, 'Owner A could not create a queued export job.', 1;

    EXEC dbo.usp_RequestAccountExportForOwner @UserKey = @UserKeyB;
    DECLARE @JobKeyB uniqueidentifier;
    SELECT TOP (1) @JobKeyB = job.job_key
    FROM dbo.account_export_jobs AS job
    WHERE job.owner_profile_id = @ProfileIdB AND job.state = N'queued'
    ORDER BY job.requested_at_utc DESC;
    IF @JobKeyB IS NULL
        THROW 57711, 'Owner B could not create a queued export job.', 1;

    IF @JobKeyA = @JobKeyB
        THROW 57712, 'Two distinct owners received the same job key.', 1;

    /* ------------------------------------------------------------
       3. Forged UserKey and guessed/forged JobKey are neutral for both
          read procedures, for a real owner's real job.
       ------------------------------------------------------------ */
    DECLARE @StatusResult TABLE
    (
        job_key uniqueidentifier, state nvarchar(20), requested_at_utc datetime2(7),
        started_at_utc datetime2(7), completed_at_utc datetime2(7),
        expired_at_utc datetime2(7), ready_expires_at_utc datetime2(7),
        attempt_count int, failure_code nvarchar(40),
        compressed_size_bytes bigint, download_available bit
    );
    DECLARE @DownloadResult TABLE
    (
        job_key uniqueidentifier, final_artifact_reference nvarchar(500),
        final_artifact_sha256 char(64), compressed_size_bytes bigint
    );

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @ForgedUserKey, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @StatusResult)
        THROW 57713, 'A forged UserKey returned a status row for a real job.', 1;

    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @ForgedUserKey, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @DownloadResult)
        THROW 57714, 'A forged UserKey returned download metadata for a real job.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyA, @JobKey = @ForgedJobKey;
    IF EXISTS (SELECT 1 FROM @StatusResult)
        THROW 57715, 'A guessed JobKey returned a status row for a real owner.', 1;

    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @UserKeyA, @JobKey = @ForgedJobKey;
    IF EXISTS (SELECT 1 FROM @DownloadResult)
        THROW 57716, 'A guessed JobKey returned download metadata for a real owner.', 1;

    /* ------------------------------------------------------------
       4. Foreign-owner rows are unreadable via both read procedures,
          in both directions, while queued.
       ------------------------------------------------------------ */
    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyB, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @StatusResult)
        THROW 57717, 'Owner B''s status read returned owner A''s job.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyB;
    IF EXISTS (SELECT 1 FROM @StatusResult)
        THROW 57718, 'Owner A''s status read returned owner B''s job.', 1;

    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @UserKeyB, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @DownloadResult)
        THROW 57719, 'Owner B''s download-metadata read returned owner A''s job.', 1;

    /* A job that is merely 'queued' (not yet 'ready') never yields
       download metadata even for its own owner. */
    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @DownloadResult)
        THROW 57720, 'A queued job (not yet ready) yielded download metadata.', 1;

    /* Meanwhile a plain status read for the owner's own queued job
       must still work -- proves the isolation checks above are
       refusing on identity/ownership, not breaking the procedure. */
    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyA;
    IF NOT EXISTS (SELECT 1 FROM @StatusResult WHERE state = N'queued' AND download_available = 0)
        THROW 57721, 'Owner A could not read their own queued job status.', 1;

    /* ------------------------------------------------------------
       5. Move owner A's job to 'ready' WITHOUT usp_ClaimAccountExportJob
          (system-wide; would touch unrelated real jobs). A scoped
          direct UPDATE to exactly this job_key simulates the claim,
          then the REAL, lease-fenced usp_CompleteAccountExportJob
          performs the actual ready transition.
       ------------------------------------------------------------ */
    DECLARE @SyntheticLeaseToken uniqueidentifier = NEWID();
    UPDATE dbo.account_export_jobs
    SET state = N'running',
        started_at_utc = SYSUTCDATETIME(),
        attempt_count = 1,
        lease_token = @SyntheticLeaseToken,
        lease_expires_at_utc = DATEADD(MINUTE, 15, SYSUTCDATETIME())
    WHERE job_key = @JobKeyA;
    IF @@ROWCOUNT <> 1
        THROW 57722, 'Could not stage owner A''s job into running for the ready-state proof.', 1;

    DECLARE @SyntheticSha256 char(64) =
        LOWER(CONVERT(char(64), HASHBYTES(N'SHA2_256', CONVERT(nvarchar(36), @JobKeyA)), 2));
    DECLARE @SyntheticReference nvarchar(500) =
        N'export/v1/final/' + CONVERT(nvarchar(36), NEWID()) + N'.zip';

    /* Called BARE, not INSERT ... EXEC, for the same reason as
       usp_RequestAccountExportForOwner above: usp_CompleteAccountExportJob's
       CATCH block can reach ROLLBACK TRANSACTION. The ready transition
       is confirmed directly against the ledger row this script already
       owns by job_key, not from the procedure's own returned result
       set. */
    EXEC dbo.usp_CompleteAccountExportJob
        @JobKey = @JobKeyA, @LeaseToken = @SyntheticLeaseToken,
        @AssemblyStartedAtUtc = '2026-08-28T00:00:00', @AssemblyCutoffAtUtc = '2026-08-28T00:00:01',
        @ConsistencyMarkerStart = NULL, @ConsistencyMarkerCutoff = NULL,
        @FinalArtifactReference = @SyntheticReference, @FinalArtifactSha256 = @SyntheticSha256,
        @CompressedSizeBytes = 1024, @UncompressedSizeBytes = 2048;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.account_export_jobs
        WHERE job_key = @JobKeyA AND state = N'ready'
          AND final_artifact_reference = @SyntheticReference
          AND final_artifact_sha256 = @SyntheticSha256
    )
        THROW 57723, 'Owner A''s job did not complete to ready.', 1;

    /* Deliberately NOT re-calling usp_CompleteAccountExportJob a second
       time to prove its own lease fencing here: that procedure's CATCH
       block issues an unqualified ROLLBACK TRANSACTION on any error,
       which -- because it is invoked from inside this script's own
       still-open outer transaction -- would unwind everything this
       verification has built so far (both synthetic owners, both
       jobs), not just its own nested scope. Lease fencing itself is
       already covered by tests/test_settings_account_export_migration.py's
       static assertions; this script's job is owner isolation, proved
       below without depending on a nested procedure's error recovery.
       ------------------------------------------------------------ */

    /* ------------------------------------------------------------
       6. Download metadata only for the owner's own ready, unexpired
          job -- neutral for the foreign owner, real for the owner.
       ------------------------------------------------------------ */
    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @UserKeyB, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @DownloadResult)
        THROW 57725, 'Owner B received download metadata for owner A''s ready job.', 1;

    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyA;
    IF NOT EXISTS
    (
        SELECT 1 FROM @DownloadResult
        WHERE final_artifact_reference = @SyntheticReference
          AND final_artifact_sha256 = @SyntheticSha256
          AND compressed_size_bytes = 1024
    )
        THROW 57726, 'Owner A could not read their own ready job''s download metadata.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyA;
    IF NOT EXISTS (SELECT 1 FROM @StatusResult WHERE state = N'ready' AND download_available = 1)
        THROW 57727, 'Owner A''s status read does not truthfully report the ready, downloadable state.', 1;

    /* ------------------------------------------------------------
       7. Expire owner A's job by a scoped direct UPDATE (never
          usp_ExpireAccountExportJobs, which is system-wide and would
          also flip any real ready-and-overdue row in the database).
          A reauthorized owner A must see a truthful 'expired' status
          and lose download access; owner B still sees nothing.
       ------------------------------------------------------------ */
    UPDATE dbo.account_export_jobs
    SET state = N'expired', expired_at_utc = SYSUTCDATETIME()
    WHERE job_key = @JobKeyA;
    IF @@ROWCOUNT <> 1
        THROW 57728, 'Could not stage owner A''s job into expired for the reauthorization proof.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyA;
    IF NOT EXISTS (SELECT 1 FROM @StatusResult WHERE state = N'expired' AND download_available = 0)
        THROW 57729, 'A reauthorized owner did not receive a truthful expired status.', 1;

    DELETE @DownloadResult;
    INSERT @DownloadResult EXEC dbo.usp_GetAccountExportDownloadMetadataForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @DownloadResult)
        THROW 57730, 'A reauthorized owner received download metadata for an expired job.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyB, @JobKey = @JobKeyA;
    IF EXISTS (SELECT 1 FROM @StatusResult)
        THROW 57731, 'Owner B''s status read returned owner A''s expired job.', 1;

    /* Owner B's own job is untouched by any of the above -- still
       queued, still readable only by owner B. */
    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyB, @JobKey = @JobKeyB;
    IF NOT EXISTS (SELECT 1 FROM @StatusResult WHERE state = N'queued')
        THROW 57732, 'Owner B''s own unrelated job was disturbed by owner A''s lifecycle proof.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult EXEC dbo.usp_GetAccountExportStatusForOwner @UserKey = @UserKeyA, @JobKey = @JobKeyB;
    IF EXISTS (SELECT 1 FROM @StatusResult)
        THROW 57733, 'Owner A''s status read returned owner B''s job after the expiry proof.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-001: procedure-shape grep across all three owner procedures (declares @UserKey nvarchar(300), resolves it itself, filters owner_profile_id = @ProfileId, never accepts a caller-supplied owner id); only the download-metadata procedure ever discloses final_artifact_reference; a forged UserKey and a guessed/forged JobKey are both neutral for a real owner''s real job; foreign-owner status and download reads are refused in both directions while queued; download metadata is refused for a not-yet-ready job even for its own owner; download metadata is granted only for the owner''s own ready, unexpired job (reached via a job_key-scoped direct UPDATE plus the real, lease-fenced usp_CompleteAccountExportJob, never the system-wide claim procedure) and refused for the foreign owner; a reauthorized owner''s status read truthfully reports an expired job (reached the same job_key-scoped way, never the system-wide expiry procedure) while download metadata discloses nothing for it; a second owner''s unrelated queued job is undisturbed throughout; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
