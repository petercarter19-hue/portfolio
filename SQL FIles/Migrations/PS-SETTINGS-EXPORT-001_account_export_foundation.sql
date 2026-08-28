/* ============================================================
   PS-SETTINGS-EXPORT-001 - account export foundation (C1)

   Additive-only job/domain ledger and owner/worker procedures for the
   future member account export defined by
   docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md
   (main 8cb633895c6df5b9b09e0e9f46922fdc60550e49). This migration creates
   schema and procedures only. It stores no exported member content
   anywhere: dbo.account_export_jobs and dbo.account_export_job_domains
   hold identifiers, states, timestamps, counts, byte sizes, and hashes
   about a request and its derived artifact, never the artifact bytes or
   any domain record body.

   Scope boundary: no domain-reader procedure is created here -- no V1
   domain has an approved field allowlist yet (C0 section "V1 domain
   matrix"), so dbo.account_export_job_domains is schema-only in this
   slice, written by no procedure. No container, workload identity,
   scheduler, or worker runtime is created or implied; no production
   apply is authorized by this file.

   Grant model (follows the PS-INTERVIEW-AI-EXTRACT-001 house pattern):
   the governed apply identity that runs this migration holds
   db_ddladmin only and cannot create a database role or grant EXECUTE,
   so no GRANT statement appears in this file. The owner procedures
   below are intended for the existing web-app principal role; the
   worker procedures are reserved for a future dedicated worker identity
   that this migration does not create. Both grants are a separate,
   later, administrator-run authority operation, exactly like
   scripts/configure_interview_telemetry_sql_authority.py and
   scripts/configure_community_maintenance_sql_authority.py.

   Provisional owner-approved limits enforced procedurally below (owner
   direction 2026-08-28, PS-SETTINGS-ACCOUNT-EXPORT-C1-C4-END-TO-END):
   one active job per owner across queued, running, and ready-before-
   expiry; one request per owner per rolling 24 hours; three bounded
   worker attempts; a seven-day ready window; a 15-minute worker lease.
   These are the same values C0 recorded as provisional C2 planning
   controls -- not current product policy, not caller-configurable.

   Requires PS-AUTH-001 (dbo.app_users, dbo.member_profiles).

   Rollback: PS-SETTINGS-EXPORT-001_account_export_foundation_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 57200, 'PS-SETTINGS-EXPORT-001 requires the migration ledger.', 1;
    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
        WHERE migration_id = N'PS-AUTH-001'
    )
        THROW 57201, 'PS-AUTH-001 must be applied before PS-SETTINGS-EXPORT-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 57202, 'The PeerSlate identity and audit foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 57203, 'The PeerSlate identity columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.account_export_jobs', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.account_export_jobs
        (
            account_export_job_id      bigint IDENTITY(1,1) NOT NULL,
            job_key                    uniqueidentifier NOT NULL
                CONSTRAINT DF_account_export_jobs_key DEFAULT NEWID(),
            owner_user_id              int NOT NULL,
            owner_profile_id           bigint NOT NULL,
            state                      nvarchar(20) NOT NULL
                CONSTRAINT DF_account_export_jobs_state DEFAULT N'queued',
            requested_at_utc           datetime2(7) NOT NULL
                CONSTRAINT DF_account_export_jobs_requested DEFAULT SYSUTCDATETIME(),
            started_at_utc             datetime2(7) NULL,
            completed_at_utc           datetime2(7) NULL,
            expired_at_utc             datetime2(7) NULL,
            ready_expires_at_utc       datetime2(7) NULL,
            attempt_count              int NOT NULL
                CONSTRAINT DF_account_export_jobs_attempts DEFAULT 0,
            lease_token                uniqueidentifier NULL,
            lease_expires_at_utc       datetime2(7) NULL,
            failure_code               nvarchar(40) NULL,
            idempotency_fingerprint    char(64) NULL,
            request_correlation_id     uniqueidentifier NOT NULL
                CONSTRAINT DF_account_export_jobs_correlation DEFAULT NEWID(),
            assembly_started_at_utc    datetime2(7) NULL,
            assembly_cutoff_at_utc     datetime2(7) NULL,
            consistency_marker_start   varbinary(8) NULL,
            consistency_marker_cutoff  varbinary(8) NULL,
            final_artifact_reference   nvarchar(500) NULL,
            final_artifact_sha256      char(64) NULL,
            compressed_size_bytes      bigint NULL,
            uncompressed_size_bytes    bigint NULL,
            cleanup_state              nvarchar(20) NOT NULL
                CONSTRAINT DF_account_export_jobs_cleanup DEFAULT N'not_required',
            updated_at_utc             datetime2(7) NOT NULL
                CONSTRAINT DF_account_export_jobs_updated DEFAULT SYSUTCDATETIME(),
            row_version                rowversion NOT NULL,
            CONSTRAINT PK_account_export_jobs PRIMARY KEY (account_export_job_id),
            CONSTRAINT UQ_account_export_jobs_key UNIQUE (job_key),
            CONSTRAINT FK_account_export_jobs_owner_user FOREIGN KEY (owner_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT FK_account_export_jobs_owner_profile FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_account_export_jobs_state CHECK
                (state IN (N'queued', N'running', N'ready', N'failed', N'expired')),
            CONSTRAINT CK_account_export_jobs_cleanup_state CHECK
                (cleanup_state IN (N'not_required', N'pending', N'cleaned')),
            CONSTRAINT CK_account_export_jobs_attempts CHECK
                (attempt_count BETWEEN 0 AND 3),
            CONSTRAINT CK_account_export_jobs_failure_code CHECK
                (failure_code IS NULL OR failure_code IN
                 (N'domain_unavailable', N'assembly_timeout', N'hash_mismatch',
                  N'oversize_compressed', N'oversize_uncompressed',
                  N'internal_error', N'worker_unavailable', N'attempts_exhausted')),
            /* Compare-and-set lease fencing: a leased row always carries a
               token and expiry; a non-leased row carries neither. Every
               worker mutation is fenced by matching this pair, never by
               trusting the caller's claim alone. */
            CONSTRAINT CK_account_export_jobs_lease_pair CHECK
                ((state = N'running' AND lease_token IS NOT NULL AND lease_expires_at_utc IS NOT NULL)
                 OR (state <> N'running' AND lease_token IS NULL AND lease_expires_at_utc IS NULL)),
            /* "Ready" means a verified complete artifact: the final
               reference, hash, both byte counts, and the ready deadline
               are committed together, never individually, and never for
               any other state. They persist through the ready -> expired
               transition so a reauthorized owner's status read stays
               truthful. */
            CONSTRAINT CK_account_export_jobs_ready_artifact CHECK
                ((state IN (N'ready', N'expired')
                  AND final_artifact_reference IS NOT NULL AND final_artifact_sha256 IS NOT NULL
                  AND compressed_size_bytes IS NOT NULL AND uncompressed_size_bytes IS NOT NULL
                  AND ready_expires_at_utc IS NOT NULL AND completed_at_utc IS NOT NULL)
                 OR (state NOT IN (N'ready', N'expired')
                     AND final_artifact_reference IS NULL AND final_artifact_sha256 IS NULL
                     AND compressed_size_bytes IS NULL AND uncompressed_size_bytes IS NULL)),
            /* Ready/expired always carry a real cleanup state, because
               CK_account_export_jobs_ready_artifact already guarantees a
               ready row has a committed artifact. Failed also may -- a
               terminal failure can still leave behind per-attempt C2
               staging objects that need the same pending -> cleaned
               lifecycle, so 'failed' is deliberately widened to allow
               (not require) a real cleanup state rather than being
               forced to 'not_required' like queued/running, which never
               had a concluded attempt to leave anything behind. */
            CONSTRAINT CK_account_export_jobs_cleanup_pair CHECK
                ((state IN (N'ready', N'expired') AND cleanup_state IN (N'pending', N'cleaned'))
                 OR (state = N'failed' AND cleanup_state IN (N'not_required', N'pending', N'cleaned'))
                 OR (state IN (N'queued', N'running') AND cleanup_state = N'not_required')),
            CONSTRAINT CK_account_export_jobs_expired_pair CHECK
                ((state = N'expired' AND expired_at_utc IS NOT NULL)
                 OR (state <> N'expired' AND expired_at_utc IS NULL)),
            /* A queued/running row may still carry the failure_code of an
               earlier exhausted attempt for operational visibility; a
               ready/expired row never does, because completion clears it. */
            CONSTRAINT CK_account_export_jobs_failure_code_state CHECK
                ((state = N'failed' AND failure_code IS NOT NULL)
                 OR (state IN (N'ready', N'expired') AND failure_code IS NULL)
                 OR state IN (N'queued', N'running')),
            CONSTRAINT CK_account_export_jobs_sha256 CHECK
                (final_artifact_sha256 IS NULL
                 OR (LEN(final_artifact_sha256) = 64
                     AND final_artifact_sha256 COLLATE Latin1_General_BIN2
                         NOT LIKE N'%[^0-9a-f]%' COLLATE Latin1_General_BIN2)),
            CONSTRAINT CK_account_export_jobs_fingerprint CHECK
                (idempotency_fingerprint IS NULL
                 OR (LEN(idempotency_fingerprint) = 64
                     AND idempotency_fingerprint COLLATE Latin1_General_BIN2
                         NOT LIKE N'%[^0-9a-f]%' COLLATE Latin1_General_BIN2)),
            CONSTRAINT CK_account_export_jobs_sizes CHECK
                ((compressed_size_bytes IS NULL OR compressed_size_bytes > 0)
                 AND (uncompressed_size_bytes IS NULL OR uncompressed_size_bytes > 0)),
            /* Defense in depth: the private artifact reference must never
               be a URL. It is a server-only locator consumed by a future
               private-container adapter, never returned to a browser and
               never a SAS/provider/direct-container URL. */
            CONSTRAINT CK_account_export_jobs_artifact_not_url CHECK
                (final_artifact_reference IS NULL
                 OR (LEFT(LOWER(final_artifact_reference), 7) <> N'http://'
                     AND LEFT(LOWER(final_artifact_reference), 8) <> N'https://')),
            /* Deliberately no expired_at_utc >= ready_expires_at_utc
               clause: C0's expired state covers BOTH "the ready window
               elapsed" and "authorization is no longer valid" (owner
               deletion/deactivation, security revocation). A future
               authorized revocation process must be able to expire a
               still-unexpired ready job early; forcing expiry to be no
               earlier than the ready deadline would make that
               unrepresentable. */
            CONSTRAINT CK_account_export_jobs_time_order CHECK
                ((started_at_utc IS NULL OR started_at_utc >= requested_at_utc)
                 AND (completed_at_utc IS NULL OR started_at_utc IS NULL OR completed_at_utc >= started_at_utc)
                 AND (ready_expires_at_utc IS NULL OR completed_at_utc IS NULL OR ready_expires_at_utc >= completed_at_utc))
        );

        /* DB-level race guard for the two contended active states. The
           third active condition -- ready before its expiry -- depends on
           the clock and cannot be a static filtered-index predicate, so it
           is fenced transactionally inside usp_RequestAccountExportForOwner
           instead (the C0-permitted alternative to a filtered constraint). */
        CREATE UNIQUE INDEX UX_account_export_jobs_owner_active
            ON dbo.account_export_jobs(owner_profile_id)
            WHERE state IN (N'queued', N'running');

        CREATE INDEX IX_account_export_jobs_owner_lookup
            ON dbo.account_export_jobs(owner_profile_id, state)
            INCLUDE (job_key, ready_expires_at_utc, requested_at_utc);

        CREATE INDEX IX_account_export_jobs_claimable
            ON dbo.account_export_jobs(lease_expires_at_utc)
            INCLUDE (state, attempt_count, requested_at_utc)
            WHERE state IN (N'queued', N'running');

        /* No cleanup_state may ever move backward off 'cleaned'. Physical
           deletion (a future C2 concern) is irreversible, so the ledger
           that records it must be too -- this is enforced at the schema
           level, not only by procedure care. */
        EXEC(N'
            CREATE TRIGGER dbo.trg_account_export_jobs_cleanup_guard
            ON dbo.account_export_jobs
            AFTER UPDATE
            AS
            BEGIN
                SET NOCOUNT ON;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted AS d
                    JOIN inserted AS i ON i.account_export_job_id = d.account_export_job_id
                    WHERE d.cleanup_state = N''cleaned'' AND i.cleanup_state <> N''cleaned''
                )
                    THROW 57204, ''A cleaned account export artifact cannot be resurrected.'', 1;
            END');

        /* No table, column, row, or existing-procedure change belongs
           here: the child ledger records only domain-level manifest
           facts, never a domain body. No procedure in this migration
           writes to it -- no V1 domain has an approved field allowlist
           yet, so population is deferred to a future, separately claimed
           domain-reader slice. */
        CREATE TABLE dbo.account_export_job_domains
        (
            account_export_job_domain_id  bigint IDENTITY(1,1) NOT NULL,
            account_export_job_id         bigint NOT NULL,
            owner_profile_id              bigint NOT NULL,
            domain_code                   nvarchar(60) NOT NULL,
            schema_identifier              nvarchar(120) NOT NULL,
            schema_version                 int NOT NULL,
            disposition                     nvarchar(20) NOT NULL,
            read_started_at_utc             datetime2(7) NULL,
            read_ended_at_utc               datetime2(7) NULL,
            source_change_marker            varbinary(8) NULL,
            record_count                     bigint NULL,
            byte_count                       bigint NULL,
            content_sha256                    char(64) NULL,
            provenance_json                    nvarchar(max) NULL,
            omission_reason                     nvarchar(200) NULL,
            failure_reason                       nvarchar(200) NULL,
            created_at_utc                        datetime2(7) NOT NULL
                CONSTRAINT DF_account_export_job_domains_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_account_export_job_domains PRIMARY KEY (account_export_job_domain_id),
            CONSTRAINT UQ_account_export_job_domains_job_domain UNIQUE (account_export_job_id, domain_code),
            CONSTRAINT FK_account_export_job_domains_job FOREIGN KEY (account_export_job_id)
                REFERENCES dbo.account_export_jobs(account_export_job_id),
            CONSTRAINT FK_account_export_job_domains_owner_profile FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_account_export_job_domains_disposition CHECK
                (disposition IN (N'included', N'excluded', N'unavailable')),
            CONSTRAINT CK_account_export_job_domains_domain_code CHECK
                (LEN(LTRIM(RTRIM(domain_code))) > 0),
            CONSTRAINT CK_account_export_job_domains_schema_id CHECK
                (LEN(LTRIM(RTRIM(schema_identifier))) > 0),
            CONSTRAINT CK_account_export_job_domains_schema_version CHECK
                (schema_version > 0),
            CONSTRAINT CK_account_export_job_domains_read_order CHECK
                (read_ended_at_utc IS NULL OR read_started_at_utc IS NULL OR read_ended_at_utc >= read_started_at_utc),
            CONSTRAINT CK_account_export_job_domains_counts CHECK
                ((record_count IS NULL OR record_count >= 0) AND (byte_count IS NULL OR byte_count >= 0)),
            CONSTRAINT CK_account_export_job_domains_sha256 CHECK
                (content_sha256 IS NULL
                 OR (LEN(content_sha256) = 64
                     AND content_sha256 COLLATE Latin1_General_BIN2
                         NOT LIKE N'%[^0-9a-f]%' COLLATE Latin1_General_BIN2)),
            CONSTRAINT CK_account_export_job_domains_provenance_json CHECK
                (provenance_json IS NULL OR ISJSON(provenance_json) = 1),
            /* Included carries real read facts and no reason; excluded
               carries only a planned/policy omission_reason; unavailable
               carries exactly one of omission_reason (structural) or
               failure_reason (a read was attempted and failed) -- never
               both, and never any read fact, since it never yielded
               trustworthy data. */
            CONSTRAINT CK_account_export_job_domains_shape CHECK
                ((disposition = N'included'
                  AND read_started_at_utc IS NOT NULL AND read_ended_at_utc IS NOT NULL
                  AND record_count IS NOT NULL AND byte_count IS NOT NULL AND content_sha256 IS NOT NULL
                  AND omission_reason IS NULL AND failure_reason IS NULL)
                 OR (disposition = N'excluded'
                     AND read_started_at_utc IS NULL AND read_ended_at_utc IS NULL
                     AND record_count IS NULL AND byte_count IS NULL AND content_sha256 IS NULL
                     AND omission_reason IS NOT NULL AND failure_reason IS NULL)
                 OR (disposition = N'unavailable'
                     AND read_started_at_utc IS NULL AND read_ended_at_utc IS NULL
                     AND record_count IS NULL AND byte_count IS NULL AND content_sha256 IS NULL
                     AND (omission_reason IS NOT NULL OR failure_reason IS NOT NULL)
                     AND NOT (omission_reason IS NOT NULL AND failure_reason IS NOT NULL)))
        );
    END;

    /* -----------------------------------------------------------
       Owner procedures. Each accepts only a trusted server-derived
       @UserKey (+ an opaque @JobKey where needed), resolves
       app_users.id -> the active member_profiles.profile_id
       internally, and enforces an owner_profile_id predicate on every
       read and write. None accepts a caller-selected owner id, table
       name, URL, or artifact reference.
       ----------------------------------------------------------- */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_RequestAccountExportForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL
                THROW 57210, ''Authenticated user key is required.'', 1;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT
                @ProfileId = profile.profile_id,
                @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL OR @UserId IS NULL
                THROW 57211, ''Authenticated owner profile not found.'', 1;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();

            BEGIN TRY
                BEGIN TRANSACTION;

                /* One active job per owner: queued, running, or ready
                   before its expiry all count as active. The filtered
                   unique index fences queued/running at the engine
                   level; this locked read fences the ready-before-expiry
                   case, which depends on the clock and cannot be a
                   static filtered-index predicate. */
                DECLARE @ExistingJobKey uniqueidentifier;
                DECLARE @ExistingState nvarchar(20);
                DECLARE @ExistingRequestedAtUtc datetime2(7);
                DECLARE @ExistingReadyExpiresAtUtc datetime2(7);
                SELECT TOP (1)
                    @ExistingJobKey = job.job_key,
                    @ExistingState = job.state,
                    @ExistingRequestedAtUtc = job.requested_at_utc,
                    @ExistingReadyExpiresAtUtc = job.ready_expires_at_utc
                FROM dbo.account_export_jobs AS job WITH (UPDLOCK, HOLDLOCK)
                WHERE job.owner_profile_id = @ProfileId
                  AND
                  (
                      job.state IN (N''queued'', N''running'')
                      OR (job.state = N''ready'' AND job.ready_expires_at_utc > @Now)
                  )
                ORDER BY job.requested_at_utc DESC;

                IF @ExistingJobKey IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''existing'' AS outcome,
                        @ExistingJobKey AS job_key,
                        @ExistingState AS state,
                        @ExistingRequestedAtUtc AS requested_at_utc,
                        @ExistingReadyExpiresAtUtc AS ready_expires_at_utc,
                        CAST(NULL AS datetime2(7)) AS retry_after_utc;
                    RETURN;
                END;

                /* One request per owner per rolling 24 hours, counted
                   from the most recent request regardless of its
                   eventual outcome (owner direction 2026-08-28). */
                DECLARE @LastRequestedAtUtc datetime2(7);
                SELECT @LastRequestedAtUtc = MAX(job.requested_at_utc)
                FROM dbo.account_export_jobs AS job WITH (UPDLOCK, HOLDLOCK)
                WHERE job.owner_profile_id = @ProfileId
                  AND job.requested_at_utc > DATEADD(HOUR, -24, @Now);

                IF @LastRequestedAtUtc IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT
                        N''rate_limited'' AS outcome,
                        CAST(NULL AS uniqueidentifier) AS job_key,
                        CAST(NULL AS nvarchar(20)) AS state,
                        @LastRequestedAtUtc AS requested_at_utc,
                        CAST(NULL AS datetime2(7)) AS ready_expires_at_utc,
                        DATEADD(HOUR, 24, @LastRequestedAtUtc) AS retry_after_utc;
                    RETURN;
                END;

                /* A safe, non-reversible dedup fingerprint derived only
                   from the server-known owner and calendar day -- never
                   from a client-supplied secret, header, or identity
                   material. CONVERT(..., 2) is wrapped in LOWER() so the
                   stored value always matches the strict lowercase-hex
                   CK_account_export_jobs_fingerprint CHECK below and the
                   app-side hexdigest convention used elsewhere in this
                   repository -- an uppercase digit here would fail the
                   INSERT with a CHECK violation (error 547), which is
                   outside the 2627/2601 unique-violation CATCH branch. */
                DECLARE @Fingerprint char(64) = LOWER(CONVERT
                (
                    char(64),
                    HASHBYTES
                    (
                        ''SHA2_256'',
                        CONVERT(varchar(20), @ProfileId) + N''|'' + CONVERT(varchar(8), CAST(@Now AS date), 112)
                    ),
                    2
                ));
                DECLARE @NewJobKey uniqueidentifier = NEWID();

                INSERT dbo.account_export_jobs
                (
                    job_key, owner_user_id, owner_profile_id, state,
                    requested_at_utc, idempotency_fingerprint
                )
                VALUES
                (
                    @NewJobKey, @UserId, @ProfileId, N''queued'',
                    @Now, @Fingerprint
                );

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
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''account_export.requested'',
                    @EntityType = N''account_export_job'',
                    @EntityKey = @NewJobKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{"state":"queued"}'';

                COMMIT TRANSACTION;

                SELECT
                    N''created'' AS outcome,
                    @NewJobKey AS job_key,
                    N''queued'' AS state,
                    @Now AS requested_at_utc,
                    CAST(NULL AS datetime2(7)) AS ready_expires_at_utc,
                    CAST(NULL AS datetime2(7)) AS retry_after_utc;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                /* A concurrent request racing past the read above can
                   still collide on the filtered unique index; treat
                   that race as the same neutral "existing" outcome
                   instead of surfacing an engine constraint error. */
                IF ERROR_NUMBER() IN (2627, 2601)
                BEGIN
                    DECLARE @RaceJobKey uniqueidentifier;
                    DECLARE @RaceState nvarchar(20);
                    DECLARE @RaceRequestedAtUtc datetime2(7);
                    DECLARE @RaceReadyExpiresAtUtc datetime2(7);
                    SELECT TOP (1)
                        @RaceJobKey = job.job_key,
                        @RaceState = job.state,
                        @RaceRequestedAtUtc = job.requested_at_utc,
                        @RaceReadyExpiresAtUtc = job.ready_expires_at_utc
                    FROM dbo.account_export_jobs AS job
                    WHERE job.owner_profile_id = @ProfileId
                      AND job.state IN (N''queued'', N''running'')
                    ORDER BY job.requested_at_utc DESC;
                    IF @RaceJobKey IS NOT NULL
                    BEGIN
                        SELECT
                            N''existing'' AS outcome,
                            @RaceJobKey AS job_key,
                            @RaceState AS state,
                            @RaceRequestedAtUtc AS requested_at_utc,
                            @RaceReadyExpiresAtUtc AS ready_expires_at_utc,
                            CAST(NULL AS datetime2(7)) AS retry_after_utc;
                        RETURN;
                    END;
                END;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetAccountExportStatusForOwner
            @UserKey nvarchar(300),
            @JobKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @JobKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;
            IF @ProfileId IS NULL RETURN;

            /* Unknown, foreign, or unresolved-owner keys all produce the
               same zero-row result as an unrecognized job; a
               reauthorized owner reading their own retained row may see
               a truthful expired state -- there is no separate branch
               for it here, the owner predicate alone decides. */
            SELECT
                job.job_key,
                job.state,
                job.requested_at_utc,
                job.started_at_utc,
                job.completed_at_utc,
                job.expired_at_utc,
                job.ready_expires_at_utc,
                job.attempt_count,
                job.failure_code,
                job.compressed_size_bytes,
                CAST
                (
                    CASE WHEN job.state = N''ready'' AND job.ready_expires_at_utc > SYSUTCDATETIME()
                         THEN 1 ELSE 0
                    END AS bit
                ) AS download_available
            FROM dbo.account_export_jobs AS job
            WHERE job.job_key = @JobKey
              AND job.owner_profile_id = @ProfileId;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetAccountExportDownloadMetadataForOwner
            @UserKey nvarchar(300),
            @JobKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @JobKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;
            IF @ProfileId IS NULL RETURN;

            /* The ONLY procedure that returns the private artifact
               reference, and only for the reauthorized owner''s own
               ready, unexpired job. It exists for the trusted
               application server''s internal proxy fetch, never for
               direct return to a browser: nothing stored here is a URL,
               container name, or SAS token. Any other job -- unknown,
               foreign, not yet ready, or past its expiry -- returns no
               rows and discloses nothing about why. */
            SELECT
                job.job_key,
                job.final_artifact_reference,
                job.final_artifact_sha256,
                job.compressed_size_bytes
            FROM dbo.account_export_jobs AS job
            WHERE job.job_key = @JobKey
              AND job.owner_profile_id = @ProfileId
              AND job.state = N''ready''
              AND job.ready_expires_at_utc > SYSUTCDATETIME();
        END;
    ');

    /* -----------------------------------------------------------
       Worker procedures, reserved for a future dedicated worker
       identity (see the grant-model note above). None accepts a
       member @UserKey; each operates system-wide across owners and is
       fenced by lease token and attempt, never by trusting a caller
       claim alone.
       ----------------------------------------------------------- */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ClaimAccountExportJob
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Provisional owner-approved constants (2026-08-28): a
               15-minute lease and a 3-attempt cap. Not caller-configurable. */
            DECLARE @LeaseDurationSeconds int = 900;
            DECLARE @MaxAttempts int = 3;
            DECLARE @Now datetime2(7) = SYSUTCDATETIME();

            BEGIN TRY
                BEGIN TRANSACTION;

                /* Reap attempt-exhausted stale leases first: a running
                   job whose lease expired and that has already used
                   every attempt can never be claimed again: it becomes
                   terminally failed here instead of unclaimable forever. */
                UPDATE dbo.account_export_jobs
                SET state = N''failed'',
                    failure_code = N''attempts_exhausted'',
                    completed_at_utc = @Now,
                    lease_token = NULL,
                    lease_expires_at_utc = NULL
                WHERE state = N''running''
                  AND lease_expires_at_utc <= @Now
                  AND attempt_count >= @MaxAttempts;

                DECLARE @JobId bigint;
                SELECT TOP (1) @JobId = job.account_export_job_id
                FROM dbo.account_export_jobs AS job WITH (ROWLOCK, UPDLOCK, READPAST)
                WHERE
                (
                    (job.state = N''queued'')
                    OR (job.state = N''running'' AND job.lease_expires_at_utc <= @Now)
                )
                AND job.attempt_count < @MaxAttempts
                ORDER BY job.requested_at_utc ASC;

                IF @JobId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    RETURN;
                END;

                DECLARE @LeaseToken uniqueidentifier = NEWID();
                DECLARE @LeaseExpiresAtUtc datetime2(7) = DATEADD(SECOND, @LeaseDurationSeconds, @Now);

                UPDATE dbo.account_export_jobs
                SET state = N''running'',
                    started_at_utc = @Now,
                    attempt_count = attempt_count + 1,
                    lease_token = @LeaseToken,
                    lease_expires_at_utc = @LeaseExpiresAtUtc
                WHERE account_export_job_id = @JobId;

                COMMIT TRANSACTION;

                SELECT
                    job.job_key,
                    job.owner_user_id,
                    job.owner_profile_id,
                    job.attempt_count,
                    @LeaseToken AS lease_token,
                    @LeaseExpiresAtUtc AS lease_expires_at_utc
                FROM dbo.account_export_jobs AS job
                WHERE job.account_export_job_id = @JobId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CompleteAccountExportJob
            @JobKey uniqueidentifier,
            @LeaseToken uniqueidentifier,
            @AssemblyStartedAtUtc datetime2(7),
            @AssemblyCutoffAtUtc datetime2(7),
            @ConsistencyMarkerStart varbinary(8),
            @ConsistencyMarkerCutoff varbinary(8),
            @FinalArtifactReference nvarchar(500),
            @FinalArtifactSha256 char(64),
            @CompressedSizeBytes bigint,
            @UncompressedSizeBytes bigint
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* Provisional owner-approved constant (2026-08-28): a
               seven-day ready window. Not caller-configurable. */
            DECLARE @ReadyWindowDays int = 7;

            SET @FinalArtifactReference = NULLIF(LTRIM(RTRIM(@FinalArtifactReference)), N'''');
            SET @FinalArtifactSha256 = NULLIF(LTRIM(RTRIM(@FinalArtifactSha256)), N'''');

            IF @JobKey IS NULL OR @LeaseToken IS NULL
                THROW 57230, ''Job key and lease token are required.'', 1;
            IF @AssemblyStartedAtUtc IS NULL OR @AssemblyCutoffAtUtc IS NULL
               OR @AssemblyCutoffAtUtc < @AssemblyStartedAtUtc
                THROW 57231, ''Assembly start and cutoff must form a valid window.'', 1;
            IF @FinalArtifactReference IS NULL
                THROW 57232, ''A final artifact reference is required.'', 1;
            IF LEFT(LOWER(@FinalArtifactReference), 7) = N''http://''
               OR LEFT(LOWER(@FinalArtifactReference), 8) = N''https://''
                THROW 57233, ''The artifact reference must never be a URL.'', 1;
            IF @FinalArtifactSha256 IS NULL
               OR LEN(@FinalArtifactSha256) <> 64
               OR @FinalArtifactSha256 COLLATE Latin1_General_BIN2 LIKE N''%[^0-9a-f]%'' COLLATE Latin1_General_BIN2
                THROW 57234, ''The final artifact hash must be 64 lowercase hex characters.'', 1;
            IF ISNULL(@CompressedSizeBytes, 0) <= 0 OR ISNULL(@UncompressedSizeBytes, 0) <= 0
                THROW 57235, ''The final artifact byte sizes must be positive.'', 1;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();

            BEGIN TRY
                BEGIN TRANSACTION;

                /* Fenced by state, lease token, AND lease expiry together:
                   a stale or foreign completion updates zero rows and is
                   refused below rather than silently accepted. */
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
                WHERE job_key = @JobKey
                  AND state = N''running''
                  AND lease_token = @LeaseToken
                  AND lease_expires_at_utc > @Now;

                IF @@ROWCOUNT <> 1
                    THROW 57236, ''The export job no longer holds this lease; the completion is refused.'', 1;

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
                    @MetadataJson = N''{"state":"ready"}'';

                COMMIT TRANSACTION;

                SELECT @JobKey AS job_key, N''ready'' AS state;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_FailAccountExportJob
            @JobKey uniqueidentifier,
            @LeaseToken uniqueidentifier,
            @FailureCode nvarchar(40)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @MaxAttempts int = 3;

            SET @FailureCode = NULLIF(LTRIM(RTRIM(@FailureCode)), N'''');
            IF @JobKey IS NULL OR @LeaseToken IS NULL
                THROW 57240, ''Job key and lease token are required.'', 1;
            IF @FailureCode IS NULL OR @FailureCode NOT IN
            (
                N''domain_unavailable'', N''assembly_timeout'', N''hash_mismatch'',
                N''oversize_compressed'', N''oversize_uncompressed'',
                N''internal_error'', N''worker_unavailable''
            )
                THROW 57241, ''The failure code is outside the closed enum.'', 1;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @JobId bigint;
                DECLARE @AttemptCount int;
                SELECT
                    @JobId = job.account_export_job_id,
                    @AttemptCount = job.attempt_count
                FROM dbo.account_export_jobs AS job WITH (UPDLOCK, HOLDLOCK)
                WHERE job.job_key = @JobKey
                  AND job.state = N''running''
                  AND job.lease_token = @LeaseToken
                  AND job.lease_expires_at_utc > @Now;

                IF @JobId IS NULL
                    THROW 57242, ''The export job no longer holds this lease; the failure is refused.'', 1;

                IF @AttemptCount < @MaxAttempts
                BEGIN
                    /* Attempts remain: requeue for another worker claim
                       rather than terminate. The failure code is
                       retained for visibility while the job is retried. */
                    UPDATE dbo.account_export_jobs
                    SET state = N''queued'',
                        failure_code = @FailureCode,
                        lease_token = NULL,
                        lease_expires_at_utc = NULL
                    WHERE account_export_job_id = @JobId;

                    COMMIT TRANSACTION;
                    SELECT @JobKey AS job_key, N''queued'' AS state, @FailureCode AS failure_code;
                END
                ELSE
                BEGIN
                    UPDATE dbo.account_export_jobs
                    SET state = N''failed'',
                        failure_code = @FailureCode,
                        completed_at_utc = @Now,
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
                    /* T-SQL forbids expressions as EXEC arguments, so the
                       failure metadata must be materialized first. */
                    DECLARE @FailureMetadataJson nvarchar(max) =
                        N''{"failure_code":"'' + @FailureCode + N''"}'';
                    INSERT @AuditResult
                    EXEC dbo.usp_AppendAuditEvent
                        @ActionType = N''account_export.failed'',
                        @EntityType = N''account_export_job'',
                        @EntityKey = @JobKey,
                        @Outcome = N''failure'',
                        @MetadataJson = @FailureMetadataJson;

                    COMMIT TRANSACTION;
                    SELECT @JobKey AS job_key, N''failed'' AS state, @FailureCode AS failure_code;
                END;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ExpireAccountExportJobs
            @BatchSize int = 500
        AS
        BEGIN
            SET NOCOUNT ON;

            IF @BatchSize IS NULL OR @BatchSize < 1 OR @BatchSize > 5000
                THROW 57250, ''Batch size must be between 1 and 5000.'', 1;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @Expired int = 1;
            DECLARE @TotalExpired int = 0;

            /* Flips readiness to expired before any physical artifact is
               ever removed. usp_GetAccountExportDownloadMetadataForOwner
               already refuses a non-ready job, so this transition alone
               blocks download; physical cleanup is a separate later
               step gated on state = ''expired''. */
            WHILE @Expired > 0
            BEGIN
                UPDATE TOP (@BatchSize) dbo.account_export_jobs
                SET state = N''expired'',
                    expired_at_utc = @Now
                WHERE state = N''ready''
                  AND ready_expires_at_utc <= @Now;

                SET @Expired = @@ROWCOUNT;
                SET @TotalExpired = @TotalExpired + @Expired;
            END;

            SELECT @TotalExpired AS expired_count;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CleanupAccountExportJob
            @JobKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            IF @JobKey IS NULL
                THROW 57255, ''A job key is required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @State nvarchar(20);
                DECLARE @CleanupState nvarchar(20);
                SELECT
                    @State = job.state,
                    @CleanupState = job.cleanup_state
                FROM dbo.account_export_jobs AS job WITH (UPDLOCK, HOLDLOCK)
                WHERE job.job_key = @JobKey;

                IF @State IS NULL
                    THROW 57256, ''Unknown export job.'', 1;

                /* Physical deletion of the FINAL artifact may only follow
                   the expiry transition, never precede or substitute for
                   it: a still-ready job keeps its artifact downloadable,
                   so only ''ready'' is refused here. ''failed'' is
                   deliberately NOT refused: a terminal failure can still
                   owe cleanup of a per-attempt C2 staging object that was
                   never a downloadable final artifact and was never
                   gated by readiness/expiry in the first place -- the
                   same pending -> cleaned transition below handles both
                   the expired-final-artifact case and the failed-staging
                   case identically, driven only by cleanup_state, not by
                   which terminal state produced it. The trigger on the
                   table additionally refuses any attempt to move a
                   cleaned row backward, for either case. */
                IF @State = N''ready''
                    THROW 57257, ''Refusing cleanup: the export job is still ready and has not expired.'', 1;

                IF @CleanupState = N''cleaned'' OR @CleanupState = N''not_required''
                BEGIN
                    /* Idempotent no-op: already cleaned, or never had
                       anything to clean -- including a failed job whose
                       cleanup_state stayed the default ''not_required''
                       because no per-attempt staging was ever created. */
                    COMMIT TRANSACTION;
                    SELECT @JobKey AS job_key, @CleanupState AS cleanup_state;
                    RETURN;
                END;

                UPDATE dbo.account_export_jobs
                SET cleanup_state = N''cleaned''
                WHERE job_key = @JobKey
                  AND cleanup_state = N''pending'';

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
                    @ActionType = N''account_export.cleaned'',
                    @EntityType = N''account_export_job'',
                    @EntityKey = @JobKey,
                    @Outcome = N''success'',
                    @MetadataJson = N''{"cleanup_state":"cleaned"}'';

                COMMIT TRANSACTION;
                SELECT @JobKey AS job_key, N''cleaned'' AS cleanup_state;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-001'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-001',
            N'Additive account-export job/domain ledger (C1 of the Settings account-export program): dbo.account_export_jobs and dbo.account_export_job_domains, three owner-scoped request/status/download-metadata procedures with server-derived identity, and five lease-fenced worker procedures (claim/complete/fail/expire/cleanup) enforcing one active job per owner, one request per 24 hours, and three bounded attempts. No domain-reader procedure, container, workload identity, scheduler, or production apply.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
