/* ============================================================
   PS-SETTINGS-EXPORT-010 - account export domain-ledger writer

   Fills the export program's last structural gap. C1
   (PS-SETTINGS-EXPORT-001) created dbo.account_export_job_domains --
   the per-domain truth ledger for every export archive -- explicitly
   "written by no procedure", deferring population to a future,
   separately claimed slice. Repository-wide, nothing has ever
   inserted a row into it. This migration is that slice.

   ONE new procedure, dbo.usp_CompleteAccountExportWithDomains,
   created ALONGSIDE C1's dbo.usp_CompleteAccountExportJob, which is
   deliberately left byte-untouched: C1 is a closed, gate-pinned
   artifact with its own text assertions, and this package's rollback
   must be a clean DROP that restores the world exactly (see the
   paired rollback file). The worker calls only the new procedure; the
   old one remains as C1 shipped it.

   THE ATOMIC CONTRACT. The worker cannot open a client-side
   transaction (its connection is autocommit by design), so
   both-or-neither lives entirely inside this one call: validate the
   complete canonical 30-domain payload, insert exactly 30 ledger
   rows, and transition the parent job to ready, in one transaction.
   A failure at any row leaves the job running and the ledger empty.

   IDENTITY IS DERIVED, NEVER SUPPLIED. The procedure takes no owner
   parameter of any kind. account_export_job_id and owner_profile_id
   come from the locked job row selected under the same four-way
   lease fence C1's procedures use (job_key + running + lease_token +
   unexpired). The schema alone would accept a foreign
   owner_profile_id on a ledger row (the FK is to member_profiles,
   not to the parent job's owner); derivation from the locked row is
   the defence, and the paired verification file proves it live with
   two owners.

   OWNER-ACTIVE IS RE-CHECKED INSIDE THE TRANSACTION. C1's Complete
   has no owner-active predicate (a recorded C1->C2 obligation the
   worker discharges in Python, outside the transaction). That check
   is re-run here under the lock, closing the
   deactivation-between-read-and-promotion window for the completion
   itself.

   VALIDATION ORDER MATTERS ELSEWHERE TOO. The worker validates the
   full 30-domain payload BEFORE staging or promoting the archive, so
   the only failures possible after the final object exists are
   infrastructure failures, not payload defects -- the
   storage-conflict trap the preactivation review documented (a
   post-promote payload failure would strand the job permanently,
   because the final object name is job-scoped and promote refuses
   overwrite). This procedure still validates everything itself; the
   worker's pre-promote check is the belt, this is the braces.

   PER-DOMAIN VALUES THE PIPELINE DOES NOT PRODUCE. schema_identifier
   is computed here as the stable domain-level id
   'peerslate.account_export.<domain_code>.v1' (an included domain
   has many per-file schema ids; the ledger row is per-domain).
   source_change_marker is the job's cutoff consistency marker for
   every row; no per-domain marker exists and none is invented.

   THROW numbers: 57230-57235 are reused VERBATIM for the identical
   argument validations C1's Complete performs, so the two procedures
   refuse malformed completions identically. 57270+ are new:
     57270 forward guard - ledger table absent
     57271 payload missing or not valid JSON
     57272 payload is not exactly the canonical 30-domain set
     57273 duplicate domain_code in payload
     57274 disposition outside included/excluded/unavailable
     57275 disposition shape violated (per-arm field rules)
     57276 content_sha256 not 64 lowercase hex
     57277 negative record_count or byte_count
     57278 read window out of order
     57279 lease fence refused (the 57236 analogue, distinct so logs
           distinguish which completion path refused)
     57280 owner no longer active at completion time
     57281 a domain reason exceeds the 200-character ledger bound --
           the worker sends a bounded excerpt (full text stays in the
           manifest); silent engine narrowing is structurally impossible
           because the payload parses wide and is checked loudly
   ============================================================ */

SET XACT_ABORT ON;
SET NOCOUNT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-010'
    )
    BEGIN
        COMMIT TRANSACTION;
        RETURN;
    END;

    /* C1 creates the child table only inside its parent-absent guard;
       a database where the parent exists but the child does not would
       otherwise fail obscurely at first insert. Assert loudly. */
    IF OBJECT_ID(N'dbo.account_export_job_domains', N'U') IS NULL
        THROW 57270, 'PS-SETTINGS-EXPORT-010 requires dbo.account_export_job_domains (PS-SETTINGS-EXPORT-001).', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CompleteAccountExportWithDomains
            @JobKey uniqueidentifier,
            @LeaseToken uniqueidentifier,
            @AssemblyStartedAtUtc datetime2(7),
            @AssemblyCutoffAtUtc datetime2(7),
            @ConsistencyMarkerStart varbinary(8),
            @ConsistencyMarkerCutoff varbinary(8),
            @FinalArtifactReference nvarchar(500),
            @FinalArtifactSha256 char(64),
            @CompressedSizeBytes bigint,
            @UncompressedSizeBytes bigint,
            @DomainLedgerJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @ReadyWindowDays int = 7; /* owner-approved constant; not caller-configurable */

            SET @FinalArtifactReference = NULLIF(LTRIM(RTRIM(@FinalArtifactReference)), N'''');
            SET @FinalArtifactSha256 = NULLIF(LTRIM(RTRIM(@FinalArtifactSha256)), N'''');

            IF @JobKey IS NULL OR @LeaseToken IS NULL
                THROW 57230, ''The job key and lease token are required.'', 1;
            IF @AssemblyStartedAtUtc IS NULL OR @AssemblyCutoffAtUtc IS NULL
                OR @AssemblyCutoffAtUtc < @AssemblyStartedAtUtc
                THROW 57231, ''The assembly window is required and must be ordered.'', 1;
            IF @FinalArtifactReference IS NULL
                THROW 57232, ''The final artifact reference is required.'', 1;
            IF LEFT(LOWER(@FinalArtifactReference), 7) = N''http://''
               OR LEFT(LOWER(@FinalArtifactReference), 8) = N''https://''
                THROW 57233, ''The artifact reference must never be a URL.'', 1;
            IF @FinalArtifactSha256 IS NULL
                OR LEN(@FinalArtifactSha256) <> 64
                OR @FinalArtifactSha256 COLLATE Latin1_General_BIN2 LIKE N''%[^0123456789abcdef]%''
                THROW 57234, ''The artifact digest must be 64 lowercase hex characters.'', 1;
            IF @CompressedSizeBytes IS NULL OR @CompressedSizeBytes <= 0
                OR @UncompressedSizeBytes IS NULL OR @UncompressedSizeBytes <= 0
                THROW 57235, ''Both artifact sizes must be positive.'', 1;
            IF @DomainLedgerJson IS NULL OR ISJSON(@DomainLedgerJson) <> 1
                THROW 57271, ''The domain ledger payload is required and must be JSON.'', 1;

            /* ---- payload into a typed table, before any lock ---- */
            DECLARE @Payload TABLE
            (
                domain_code        nvarchar(60)  NOT NULL,
                disposition        nvarchar(20)  NOT NULL,
                record_count       bigint        NULL,
                byte_count         bigint        NULL,
                content_sha256     char(64)      NULL,
                read_started_at_utc datetime2(7) NULL,
                read_ended_at_utc  datetime2(7)  NULL,
                omission_reason    nvarchar(max) NULL,
                failure_reason     nvarchar(max) NULL,
                provenance_json    nvarchar(max) NULL
            );

            INSERT @Payload
            SELECT
                LTRIM(RTRIM(p.domain_code)),
                LTRIM(RTRIM(p.disposition)),
                p.record_count,
                p.byte_count,
                LOWER(NULLIF(LTRIM(RTRIM(p.content_sha256)), N'''')),
                p.read_started_at_utc,
                p.read_ended_at_utc,
                NULLIF(LTRIM(RTRIM(p.omission_reason)), N''''),
                NULLIF(LTRIM(RTRIM(p.failure_reason)), N''''),
                p.provenance_json
            FROM OPENJSON(@DomainLedgerJson)
            WITH
            (
                domain_code         nvarchar(60)   ''$.domain_code'',
                disposition         nvarchar(20)   ''$.disposition'',
                record_count        bigint         ''$.record_count'',
                byte_count          bigint         ''$.byte_count'',
                content_sha256      char(64)       ''$.content_sha256'',
                read_started_at_utc datetime2(7)   ''$.read_started_at_utc'',
                read_ended_at_utc   datetime2(7)   ''$.read_ended_at_utc'',
                omission_reason     nvarchar(max)  ''$.omission_reason'',
                failure_reason      nvarchar(max)  ''$.failure_reason'',
                provenance_json     nvarchar(max)  ''$.provenance_json'' AS JSON
            ) AS p;

            /* ---- the canonical 30, pinned; an offline test asserts this
                    list equals DOMAINS in the reader module exactly ---- */
            DECLARE @Canonical TABLE (domain_code nvarchar(60) NOT NULL PRIMARY KEY);
            INSERT @Canonical (domain_code) VALUES
                (N''account''), (N''ai_proposals''), (N''ask_pete_direct''),
                (N''ask_pete_public''), (N''audit_events''),
                (N''browser_local_interview_history''), (N''capture''),
                (N''career_skill_links''), (N''community_authored_content''),
                (N''connection_preferences''), (N''connection_records''),
                (N''consent_history''), (N''file_evidence_metadata''),
                (N''home''), (N''indexes_caches_provider_backups''),
                (N''interview_telemetry''), (N''journal''), (N''living_resume''),
                (N''moment''), (N''my_opportunities''),
                (N''notification_preferences''), (N''notifications_inbox''),
                (N''opportunity_slate''), (N''own_publication_versions''),
                (N''profile''), (N''profile_publication_foundation''),
                (N''projects''), (N''voice_photo''),
                (N''workshop_knowledge_save_requests''), (N''workshop_my_knowledge'');

            IF EXISTS
            (
                SELECT domain_code FROM @Payload GROUP BY domain_code HAVING COUNT(*) > 1
            )
                THROW 57273, ''The domain ledger payload repeats a domain.'', 1;

            IF EXISTS (SELECT domain_code FROM @Payload EXCEPT SELECT domain_code FROM @Canonical)
                OR EXISTS (SELECT domain_code FROM @Canonical EXCEPT SELECT domain_code FROM @Payload)
                THROW 57272, ''The domain ledger payload must be exactly the canonical domain set.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM @Payload
                WHERE disposition NOT IN (N''included'', N''excluded'', N''unavailable'')
            )
                THROW 57274, ''A domain disposition is outside the closed vocabulary.'', 1;

            /* per-arm shape, mirroring CK_account_export_job_domains_shape so
               refusals carry a clean number instead of a constraint error */
            IF EXISTS
            (
                SELECT 1 FROM @Payload
                WHERE
                (
                    disposition = N''included'' AND
                    (
                        read_started_at_utc IS NULL OR read_ended_at_utc IS NULL
                        OR record_count IS NULL OR byte_count IS NULL
                        OR content_sha256 IS NULL
                        OR omission_reason IS NOT NULL OR failure_reason IS NOT NULL
                    )
                )
                OR
                (
                    disposition = N''excluded'' AND
                    (
                        read_started_at_utc IS NOT NULL OR read_ended_at_utc IS NOT NULL
                        OR record_count IS NOT NULL OR byte_count IS NOT NULL
                        OR content_sha256 IS NOT NULL
                        OR omission_reason IS NULL OR failure_reason IS NOT NULL
                    )
                )
                OR
                (
                    disposition = N''unavailable'' AND
                    (
                        read_started_at_utc IS NOT NULL OR read_ended_at_utc IS NOT NULL
                        OR record_count IS NOT NULL OR byte_count IS NOT NULL
                        OR content_sha256 IS NOT NULL
                        OR NOT
                        (
                            (omission_reason IS NULL AND failure_reason IS NOT NULL)
                            OR (omission_reason IS NOT NULL AND failure_reason IS NULL)
                        )
                    )
                )
            )
                THROW 57275, ''A domain row violates its disposition shape.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM @Payload
                WHERE content_sha256 IS NOT NULL
                  AND
                  (
                      LEN(content_sha256) <> 64
                      OR content_sha256 COLLATE Latin1_General_BIN2 LIKE N''%[^0123456789abcdef]%''
                  )
            )
                THROW 57276, ''A domain digest must be 64 lowercase hex characters.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM @Payload
                WHERE (record_count IS NOT NULL AND record_count < 0)
                   OR (byte_count IS NOT NULL AND byte_count < 0)
            )
                THROW 57277, ''Domain counts must be non-negative.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM @Payload
                WHERE read_started_at_utc IS NOT NULL
                  AND read_ended_at_utc IS NOT NULL
                  AND read_ended_at_utc < read_started_at_utc
            )
                THROW 57278, ''A domain read window is out of order.'', 1;

            /* the ledger column is nvarchar(200); a longer reason must be
               bounded EXPLICITLY by the caller (the worker keeps the full
               text in the manifest and sends a bounded excerpt here) --
               never narrowed silently by the engine into a record that
               disagrees mid-sentence with the archive */
            IF EXISTS
            (
                SELECT 1 FROM @Payload
                WHERE LEN(omission_reason) > 200 OR LEN(failure_reason) > 200
            )
                THROW 57281, ''A domain reason exceeds the ledger bound; the caller must bound it explicitly.'', 1;

            /* captured after every validation, immediately before the lock,
               so the lease-expiry predicate is as tight as C1 keeps it */
            DECLARE @Now datetime2(7) = SYSUTCDATETIME();

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @JobId bigint;
                DECLARE @OwnerProfileId bigint;
                DECLARE @OwnerUserId int;
                SELECT
                    @JobId = job.account_export_job_id,
                    @OwnerProfileId = job.owner_profile_id,
                    @OwnerUserId = job.owner_user_id
                FROM dbo.account_export_jobs AS job WITH (UPDLOCK, HOLDLOCK)
                WHERE job.job_key = @JobKey
                  AND job.state = N''running''
                  AND job.lease_token = @LeaseToken
                  AND job.lease_expires_at_utc > @Now;

                IF @JobId IS NULL
                    THROW 57279, ''The export job no longer holds this lease; the completion is refused.'', 1;

                /* the deactivation-between-read-and-promotion window,
                   closed under the lock */
                IF NOT EXISTS
                (
                    SELECT 1
                    FROM dbo.member_profiles AS profile
                    JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                    WHERE profile.profile_id = @OwnerProfileId
                      AND app_user.id = @OwnerUserId
                      AND app_user.active = 1
                      AND profile.active = 1
                )
                    THROW 57280, ''The owner is no longer active; the completion is refused.'', 1;

                INSERT dbo.account_export_job_domains
                (
                    account_export_job_id, owner_profile_id, domain_code,
                    schema_identifier, schema_version, disposition,
                    read_started_at_utc, read_ended_at_utc,
                    source_change_marker, record_count, byte_count,
                    content_sha256, provenance_json,
                    omission_reason, failure_reason
                )
                SELECT
                    @JobId,
                    @OwnerProfileId,
                    p.domain_code,
                    N''peerslate.account_export.'' + p.domain_code + N''.v1'',
                    1,
                    p.disposition,
                    p.read_started_at_utc,
                    p.read_ended_at_utc,
                    CASE WHEN p.disposition = N''included''
                         THEN @ConsistencyMarkerCutoff ELSE NULL END,
                    p.record_count,
                    p.byte_count,
                    p.content_sha256,
                    p.provenance_json,
                    p.omission_reason,
                    p.failure_reason
                FROM @Payload AS p
                ORDER BY p.domain_code;

                UPDATE dbo.account_export_jobs
                SET state = N''ready'',
                    completed_at_utc = @Now,
                    ready_expires_at_utc = DATEADD(DAY, @ReadyWindowDays, @Now),
                    assembly_started_at_utc = @AssemblyStartedAtUtc,
                    assembly_cutoff_at_utc = @AssemblyCutoffAtUtc,
                    consistency_marker_start = @ConsistencyMarkerStart,
                    consistency_marker_cutoff = @ConsistencyMarkerCutoff,
                    final_artifact_reference = @FinalArtifactReference,
                    final_artifact_sha256 = @FinalArtifactSha256,
                    compressed_size_bytes = @CompressedSizeBytes,
                    uncompressed_size_bytes = @UncompressedSizeBytes,
                    cleanup_state = N''pending'',
                    failure_code = NULL,
                    lease_token = NULL,
                    lease_expires_at_utc = NULL
                WHERE account_export_job_id = @JobId;

                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActionType = N''account_export.ready'',
                    @EntityType = N''account_export_job'',
                    @EntityKey = @JobKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{"state":"ready","domain_rows":30}'';

                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;

            SELECT @JobKey AS job_key, N''ready'' AS state, 30 AS domain_rows;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-010'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-010',
            N'Account-export domain-ledger writer: one worker-only, lease-fenced atomic completion procedure (usp_CompleteAccountExportWithDomains, added alongside C1''s untouched usp_CompleteAccountExportJob) that derives job/owner identity from the locked row, re-checks owner-active under the lock, validates the canonical 30-domain payload, inserts the per-domain ledger rows, and transitions the job to ready in one transaction - both succeed or neither.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-010"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
