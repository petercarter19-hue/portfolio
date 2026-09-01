/* PS-SETTINGS-EXPORT-010 (account-export domain-ledger writer)
   production-safe owner-isolation and atomicity verification.

   STRUCTURE, learned from C1's own gate round
   (PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql, "CORRECTION
   (gate round)"): T-SQL forbids ROLLBACK inside a procedure invoked
   with INSERT ... EXEC, and every write procedure this script touches
   (usp_RequestAccountExportForOwner, usp_ClaimAccountExportJob, and
   the new usp_CompleteAccountExportWithDomains) carries a CATCH-block
   ROLLBACK. All three are therefore called BARE, their result sets
   discarded, and every fact confirmed with plain SELECTs afterward.
   For the same reason there is NO outer transaction: the new
   procedure's own refusal-path ROLLBACK would unwind it, voiding every
   subsequent assertion against silently-vanished fixtures. Cleanup is
   an explicit final section instead. Run ONLY on a disposable
   migration-gate database.

   Fresh THROW numbers in the 59400-59499 block. What is proven live:
   structural facts about the procedure body; both-or-neither (a
   refused payload leaves the job running and the ledger at zero rows);
   the exact refusal numbers 57272/57273/57275/57279/57280/57281; owner
   isolation (thirty rows, all the completing owner's, other owner
   untouched); replay fencing after ready; the explicit reason bound;
   deactivation between claim and completion. */

SET XACT_ABORT OFF;
SET NOCOUNT ON;

DECLARE @Thrown int, @Detail nvarchar(400);

BEGIN TRY
    /* ---------- 0. structural checks ---------- */
    IF OBJECT_ID(N'dbo.usp_CompleteAccountExportWithDomains', N'P') IS NULL
        THROW 59400, 'The domain-ledger completion procedure is absent.', 1;

    DECLARE @Body nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CompleteAccountExportWithDomains'));
    IF @Body LIKE N'%@UserKey%'
        THROW 59401, 'The worker procedure must not take a member user key.', 1;
    IF @Body NOT LIKE N'%UPDLOCK, HOLDLOCK%' OR @Body NOT LIKE N'%lease_expires_at_utc > @Now%'
        THROW 59402, 'The locked four-way lease fence is missing.', 1;
    IF @Body NOT LIKE N'%app_user.active = 1%' OR @Body NOT LIKE N'%profile.active = 1%'
        THROW 59403, 'The in-transaction owner-active re-check is missing.', 1;
    IF @Body NOT LIKE N'%ORDER BY p.domain_code%'
        THROW 59404, 'Deterministic insert ordering is missing.', 1;

    /* ---------- 1. synthetic owners, jobs (bare EXECs), leases ---------- */
    INSERT dbo.app_users (user_key, auth_provider, auth_issuer, auth_subject, email, display_name, active)
    VALUES
        (N'verify59400-owner-a', N'verify59400', N'urn:verify59400', N'a', N'a@verify59400.invalid', N'Verify A', 1),
        (N'verify59400-owner-b', N'verify59400', N'urn:verify59400', N'b', N'b@verify59400.invalid', N'Verify B', 1);
    DECLARE @UserA int = (SELECT id FROM dbo.app_users WHERE user_key = N'verify59400-owner-a');
    DECLARE @UserB int = (SELECT id FROM dbo.app_users WHERE user_key = N'verify59400-owner-b');
    INSERT dbo.member_profiles (user_id, profile_slug, display_name, active)
    VALUES (@UserA, N'verify59400-a', N'Verify A', 1), (@UserB, N'verify59400-b', N'Verify B', 1);
    DECLARE @ProfileA bigint = (SELECT profile_id FROM dbo.member_profiles WHERE user_id = @UserA);
    DECLARE @ProfileB bigint = (SELECT profile_id FROM dbo.member_profiles WHERE user_id = @UserB);

    EXEC dbo.usp_RequestAccountExportForOwner @UserKey = N'verify59400-owner-a';
    EXEC dbo.usp_RequestAccountExportForOwner @UserKey = N'verify59400-owner-b';
    DECLARE @JobA uniqueidentifier = (SELECT job_key FROM dbo.account_export_jobs WHERE owner_profile_id = @ProfileA);
    DECLARE @JobB uniqueidentifier = (SELECT job_key FROM dbo.account_export_jobs WHERE owner_profile_id = @ProfileB);
    IF @JobA IS NULL OR @JobB IS NULL THROW 59405, 'Fixture job creation failed.', 1;

    EXEC dbo.usp_ClaimAccountExportJob;   /* oldest first: A */
    EXEC dbo.usp_ClaimAccountExportJob;   /* then B */
    DECLARE @LeaseA uniqueidentifier = (SELECT lease_token FROM dbo.account_export_jobs WHERE job_key = @JobA AND state = N'running');
    DECLARE @LeaseB uniqueidentifier = (SELECT lease_token FROM dbo.account_export_jobs WHERE job_key = @JobB AND state = N'running');
    IF @LeaseA IS NULL OR @LeaseB IS NULL THROW 59406, 'Fixture lease claim failed.', 1;

    /* ---------- 2. a complete, shape-valid canonical payload ---------- */
    DECLARE @P TABLE
    (
        domain_code nvarchar(60) PRIMARY KEY, disposition nvarchar(20),
        record_count bigint, byte_count bigint, content_sha256 char(64),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7),
        omission_reason nvarchar(400), failure_reason nvarchar(400)
    );
    INSERT @P (domain_code, disposition, omission_reason) VALUES
        (N'ai_proposals', N'excluded', N'synthetic'), (N'ask_pete_direct', N'excluded', N'synthetic'),
        (N'ask_pete_public', N'excluded', N'synthetic'), (N'audit_events', N'excluded', N'synthetic'),
        (N'browser_local_interview_history', N'excluded', N'synthetic'), (N'capture', N'excluded', N'synthetic'),
        (N'career_skill_links', N'excluded', N'synthetic'), (N'community_authored_content', N'excluded', N'synthetic'),
        (N'connection_preferences', N'excluded', N'synthetic'), (N'connection_records', N'excluded', N'synthetic'),
        (N'consent_history', N'excluded', N'synthetic'), (N'file_evidence_metadata', N'excluded', N'synthetic'),
        (N'home', N'excluded', N'synthetic'), (N'indexes_caches_provider_backups', N'excluded', N'synthetic'),
        (N'interview_telemetry', N'excluded', N'synthetic'), (N'journal', N'excluded', N'synthetic'),
        (N'living_resume', N'excluded', N'synthetic'), (N'moment', N'excluded', N'synthetic'),
        (N'my_opportunities', N'excluded', N'synthetic'), (N'notification_preferences', N'excluded', N'synthetic'),
        (N'notifications_inbox', N'excluded', N'synthetic'), (N'opportunity_slate', N'excluded', N'synthetic'),
        (N'own_publication_versions', N'excluded', N'synthetic'), (N'profile', N'excluded', N'synthetic'),
        (N'profile_publication_foundation', N'excluded', N'synthetic'), (N'projects', N'excluded', N'synthetic'),
        (N'voice_photo', N'excluded', N'synthetic'), (N'workshop_knowledge_save_requests', N'excluded', N'synthetic'),
        (N'workshop_my_knowledge', N'excluded', N'synthetic');
    INSERT @P (domain_code, disposition, record_count, byte_count, content_sha256, read_started_at_utc, read_ended_at_utc)
    VALUES (N'account', N'included', 1, 17, REPLICATE(N'a', 64), SYSUTCDATETIME(), SYSUTCDATETIME());

    DECLARE @Json nvarchar(max) =
        (SELECT domain_code, disposition, record_count, byte_count, content_sha256,
                read_started_at_utc, read_ended_at_utc, omission_reason, failure_reason
         FROM @P ORDER BY domain_code FOR JSON PATH, INCLUDE_NULL_VALUES);
    DECLARE @Sha char(64) = REPLICATE(N'b', 64);
    DECLARE @Started datetime2(7) = DATEADD(MINUTE, -5, SYSUTCDATETIME());
    DECLARE @Cutoff datetime2(7) = SYSUTCDATETIME();
    DECLARE @Marker varbinary(8) = 0x0000000000000001;

    /* ---------- 3. refusals, each proven to write nothing ---------- */
    /* 3a. incomplete set -> 57272 */
    DECLARE @JsonMissing nvarchar(max) =
        (SELECT domain_code, disposition, record_count, byte_count, content_sha256,
                read_started_at_utc, read_ended_at_utc, omission_reason, failure_reason
         FROM @P WHERE domain_code <> N'journal' ORDER BY domain_code FOR JSON PATH, INCLUDE_NULL_VALUES);
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobA, @LeaseToken = @LeaseA,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @JsonMissing;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57272 THROW 59410, 'Incomplete canonical set must refuse with 57272.', 1;
    IF EXISTS (SELECT 1 FROM dbo.account_export_job_domains WHERE owner_profile_id = @ProfileA)
        THROW 59411, 'A refused completion must leave zero ledger rows.', 1;
    IF (SELECT state FROM dbo.account_export_jobs WHERE job_key = @JobA) <> N'running'
        THROW 59412, 'A refused completion must leave the job running.', 1;

    /* 3b. duplicate domain -> 57273 */
    DECLARE @JsonDup nvarchar(max) = REPLACE(@Json, N'"domain_code":"account"', N'"domain_code":"journal"');
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobA, @LeaseToken = @LeaseA,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @JsonDup;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57273 THROW 59413, 'A duplicated domain must refuse with 57273.', 1;

    /* 3c. shape violation -> 57275 */
    DECLARE @JsonBadShape nvarchar(max) = REPLACE(@Json, REPLICATE(N'a', 64), N'');
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobA, @LeaseToken = @LeaseA,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @JsonBadShape;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57275 THROW 59414, 'A shape-violating row must refuse with 57275.', 1;

    /* 3d. over-long reason -> 57281 (the explicit bound, F1) */
    DECLARE @JsonLongReason nvarchar(max) = REPLACE(@Json, N'"omission_reason":"synthetic"',
        N'"omission_reason":"' + REPLICATE(N'z', 201) + N'"');
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobA, @LeaseToken = @LeaseA,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @JsonLongReason;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57281 THROW 59417, 'An over-long reason must refuse loudly with 57281, never truncate.', 1;

    /* 3e. foreign lease -> 57279, nothing written for B */
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobB, @LeaseToken = @LeaseA,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @Json;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57279 THROW 59415, 'A foreign lease must refuse with 57279.', 1;
    IF EXISTS (SELECT 1 FROM dbo.account_export_job_domains WHERE owner_profile_id = @ProfileB)
        THROW 59416, 'A foreign-lease refusal must write nothing.', 1;

    /* ---------- 4. owner A completes (bare); isolation proven ---------- */
    EXEC dbo.usp_CompleteAccountExportWithDomains
        @JobKey = @JobA, @LeaseToken = @LeaseA,
        @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
        @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
        @FinalArtifactReference = N'export/v1/final/verify.zip',
        @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
        @UncompressedSizeBytes = 200, @DomainLedgerJson = @Json;

    IF (SELECT state FROM dbo.account_export_jobs WHERE job_key = @JobA) <> N'ready'
        THROW 59420, 'The successful completion must leave the job ready.', 1;
    IF (SELECT COUNT(*) FROM dbo.account_export_job_domains WHERE owner_profile_id = @ProfileA) <> 30
        THROW 59421, 'Exactly thirty ledger rows must exist for the completed job.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.account_export_job_domains d
        JOIN dbo.account_export_jobs j ON j.account_export_job_id = d.account_export_job_id
        WHERE j.job_key = @JobA AND d.owner_profile_id <> @ProfileA
    )
        THROW 59422, 'Every ledger row must carry the completing owner''s own profile id.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.account_export_job_domains
        WHERE owner_profile_id = @ProfileA
          AND schema_identifier <> N'peerslate.account_export.' + domain_code + N'.v1'
    )
        THROW 59423, 'The stable per-domain schema identifier rule must hold.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.account_export_job_domains
        WHERE owner_profile_id = @ProfileA AND disposition = N'included'
          AND source_change_marker <> @Marker
    )
        THROW 59424, 'Included rows must carry the job cutoff marker.', 1;
    IF EXISTS (SELECT 1 FROM dbo.account_export_job_domains WHERE owner_profile_id = @ProfileB)
        THROW 59425, 'Owner B''s ledger must remain untouched by A''s completion.', 1;

    /* ---------- 5. replay fencing ---------- */
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobA, @LeaseToken = @LeaseA,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @Json;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57279 THROW 59426, 'A replayed completion must refuse with 57279.', 1;
    IF (SELECT COUNT(*) FROM dbo.account_export_job_domains WHERE owner_profile_id = @ProfileA) <> 30
        THROW 59427, 'A refused replay must leave the original thirty rows untouched.', 1;

    /* ---------- 6. deactivation between claim and completion ---------- */
    UPDATE dbo.app_users SET active = 0 WHERE id = @UserB;
    SET @Thrown = 0;
    BEGIN TRY
        EXEC dbo.usp_CompleteAccountExportWithDomains
            @JobKey = @JobB, @LeaseToken = @LeaseB,
            @AssemblyStartedAtUtc = @Started, @AssemblyCutoffAtUtc = @Cutoff,
            @ConsistencyMarkerStart = @Marker, @ConsistencyMarkerCutoff = @Marker,
            @FinalArtifactReference = N'export/v1/final/verify-b.zip',
            @FinalArtifactSha256 = @Sha, @CompressedSizeBytes = 100,
            @UncompressedSizeBytes = 200, @DomainLedgerJson = @Json;
    END TRY
    BEGIN CATCH SET @Thrown = ERROR_NUMBER(); END CATCH;
    IF @Thrown <> 57280 THROW 59428, 'A deactivated owner must refuse with 57280.', 1;
    IF EXISTS (SELECT 1 FROM dbo.account_export_job_domains WHERE owner_profile_id = @ProfileB)
        THROW 59429, 'A deactivated-owner refusal must write nothing.', 1;
    IF (SELECT state FROM dbo.account_export_jobs WHERE job_key = @JobB) <> N'running'
        THROW 59430, 'The refused job must remain running for the reaper, not become ready.', 1;

    /* ---------- 7. explicit synthetic cleanup (no outer txn to roll back) */
    DELETE d FROM dbo.account_export_job_domains d WHERE d.owner_profile_id IN (@ProfileA, @ProfileB);
    DELETE FROM dbo.account_export_jobs WHERE owner_profile_id IN (@ProfileA, @ProfileB);
    DELETE FROM dbo.member_profiles WHERE profile_id IN (@ProfileA, @ProfileB);
    /* the bare request calls durably committed audit rows naming these
       users (FK_audit_events_app_users, no cascade) -- delete them first
       or the app_users delete hits FK 547 and the proof can never finish */
    DELETE FROM dbo.audit_events WHERE actor_user_id IN (@UserA, @UserB);
    DELETE FROM dbo.app_users WHERE id IN (@UserA, @UserB);

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-010: structural checks against the live procedure body; jobs and leases minted through BARE calls to the real request/claim procedures (INSERT...EXEC is illegal against CATCH-ROLLBACK procedures -- C1''s own recorded gate lesson) with facts confirmed by plain SELECTs; no outer transaction, so refusal-path rollbacks cannot void later assertions; refusals proven with exact numbers -- 57272 incomplete set (zero rows, job left running), 57273 duplicate, 57275 shape, 57281 over-long reason refused loudly rather than truncated, 57279 foreign lease and replay-after-ready (thirty original rows untouched), 57280 owner deactivated between claim and completion (nothing written, job left running); the successful completion produced exactly thirty rows all carrying the completing owner''s own profile id, the stable per-domain schema identifier, and the job cutoff marker on included rows, the other owner''s ledger untouched; explicit synthetic cleanup completed.' AS detail;
END TRY
BEGIN CATCH
    /* best-effort cleanup, then surface the real failure */
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    SET @Detail = ERROR_MESSAGE();
    BEGIN TRY
        DELETE d FROM dbo.account_export_job_domains d
        WHERE d.owner_profile_id IN (SELECT profile_id FROM dbo.member_profiles WHERE profile_slug LIKE N'verify59400-%');
        DELETE FROM dbo.account_export_jobs
        WHERE owner_profile_id IN (SELECT profile_id FROM dbo.member_profiles WHERE profile_slug LIKE N'verify59400-%');
        DELETE FROM dbo.member_profiles WHERE profile_slug LIKE N'verify59400-%';
        DELETE FROM dbo.audit_events
        WHERE actor_user_id IN (SELECT id FROM dbo.app_users WHERE user_key LIKE N'verify59400-%');
        DELETE FROM dbo.app_users WHERE user_key LIKE N'verify59400-%';
    END TRY
    BEGIN CATCH END CATCH;
    THROW 59499, @Detail, 1;
END CATCH;
