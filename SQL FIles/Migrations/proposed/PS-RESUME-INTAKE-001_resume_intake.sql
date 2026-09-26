/*
PS-RESUME-INTAKE-001 — proposed owner-scoped Resume composer intake.

PROPOSED ONLY. This file has not been applied to any database. Its registry
gate is null. Disposable SQL Server execution, concurrency, rollback and driver
serialization proof remain required before any separately authorized schema
application. Allowlisting procedure names does not apply this file.

One member action is one transaction. An explicit Add stages canonical intents
in the command JSON and this procedure executes each one against the EXISTING
closed canonical boundary INSIDE this transaction:

  * boundary N'living_resume' -> dbo.usp_CommitLivingResumeCommandForOwner
    (PS-RESUME-EDIT-002) creates a brand-new private canonical fact. Its closed
    key set is {command_id,type,record_key,parent_key,expected_version,values}
    and its type vocabulary is create_/update_/remove_ per record type.
  * boundary N'resume_draft' -> dbo.usp_CommitResumeDraftCommandForOwner
    (PS-RESUME-DRAFT-001) merges a member-confirmed change into the private
    draft overlay. It never writes canonical/shared truth and never restores
    permissions.

Calling the draft procedure for a new fact would be wrong: its
create_private_item branch writes only a draft receipt. Calling the editor
procedure with a draft payload would be wrong too: it rejects unknown keys.

The immutable stored receipt NEVER contains the member's words (quotes,
proposed/confirmed values, transcripts). Those live only in the mutable source
and proposal rows, which is what source purge redacts -- so an immutable
receipt row never has to be updated and no receipt copy can resurrect purged
text.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-DRAFT-001')
        THROW 52300, 'PS-RESUME-DRAFT-001 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.resume_intake_owner_state', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_owner_state
        (
            owner_profile_id bigint NOT NULL,
            lifecycle_epoch int NOT NULL CONSTRAINT DF_resume_intake_state_epoch DEFAULT 0,
            policy_version int NOT NULL CONSTRAINT DF_resume_intake_state_policy DEFAULT 0,
            guide_status nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_state_guide DEFAULT N'not_started',
            guide_status_source nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_state_source DEFAULT N'default_unstarted',
            last_receipt_json nvarchar(max) NULL,
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_state_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_owner_state PRIMARY KEY (owner_profile_id),
            CONSTRAINT FK_resume_intake_owner_state_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_state_guide CHECK
                (guide_status IN (N'not_started', N'in_progress', N'paused', N'completed', N'skipped')),
            CONSTRAINT CK_resume_intake_state_source CHECK (guide_status_source IN (N'default_unstarted', N'member')),
            CONSTRAINT CK_resume_intake_state_epoch CHECK (lifecycle_epoch >= 0 AND policy_version >= 0),
            CONSTRAINT CK_resume_intake_state_last_receipt CHECK
                (last_receipt_json IS NULL OR ISJSON(last_receipt_json) = 1)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_submissions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_submissions
        (
            submission_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            submission_key uniqueidentifier NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            submission_version int NOT NULL CONSTRAINT DF_resume_intake_submissions_version DEFAULT 1,
            state nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_submissions_state DEFAULT N'active',
            entrance nvarchar(40) NOT NULL,
            policy_version int NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_submissions_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_submissions PRIMARY KEY (submission_id),
            CONSTRAINT UQ_resume_intake_submissions_key UNIQUE (submission_key),
            CONSTRAINT UQ_resume_intake_submissions_owner_request UNIQUE (owner_profile_id, request_id),
            CONSTRAINT FK_resume_intake_submissions_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_submissions_digest
                CHECK (request_digest NOT LIKE '%[^0-9a-f]%' AND LEN(request_digest) = 64),
            CONSTRAINT CK_resume_intake_submissions_state CHECK (state IN (N'active', N'superseded')),
            CONSTRAINT CK_resume_intake_submissions_version CHECK (submission_version >= 1)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_sources', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_sources
        (
            source_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            -- NULL is the honest binding for a pre-Add recording source: it is
            -- intake material that belongs to no submission yet.
            submission_key uniqueidentifier NULL,
            source_key uniqueidentifier NOT NULL,
            kind nvarchar(20) NOT NULL,
            state nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_sources_state DEFAULT N'active',
            source_version int NOT NULL CONSTRAINT DF_resume_intake_sources_version DEFAULT 1,
            entrance nvarchar(40) NOT NULL,
            policy_version int NOT NULL,
            content_type nvarchar(200) NULL,
            byte_length bigint NULL,
            sha256 char(64) NULL,
            structured_values_json nvarchar(max) NULL,
            -- Purged sources keep provenance rows but this column is nulled;
            -- deleted source text is never resurrected.
            source_text nvarchar(max) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_sources_created DEFAULT SYSUTCDATETIME(),
            purged_at_utc datetime2(7) NULL,
            CONSTRAINT PK_resume_intake_sources PRIMARY KEY (source_id),
            CONSTRAINT UQ_resume_intake_sources_key UNIQUE (source_key),
            CONSTRAINT FK_resume_intake_sources_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_sources_kind CHECK (kind IN (N'text', N'document', N'recording', N'structured')),
            CONSTRAINT CK_resume_intake_sources_state CHECK (state IN (N'active', N'purged')),
            CONSTRAINT CK_resume_intake_sources_version CHECK (source_version >= 1),
            CONSTRAINT CK_resume_intake_sources_binding CHECK
                ((kind = N'recording' AND submission_key IS NULL) OR submission_key IS NOT NULL),
            CONSTRAINT CK_resume_intake_sources_purged CHECK
                ((state = N'purged' AND source_text IS NULL AND purged_at_utc IS NOT NULL)
                 OR (state = N'active' AND purged_at_utc IS NULL)),
            CONSTRAINT CK_resume_intake_sources_structured CHECK
                (structured_values_json IS NULL OR ISJSON(structured_values_json) = 1)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_jobs', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_jobs
        (
            job_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            job_key uniqueidentifier NOT NULL,
            source_key uniqueidentifier NOT NULL,
            source_version int NOT NULL,
            submission_key uniqueidentifier NULL,
            submission_version int NOT NULL,
            policy_version int NOT NULL,
            lifecycle_epoch int NOT NULL,
            kind nvarchar(40) NOT NULL,
            state nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_jobs_state DEFAULT N'queued',
            lease_id uniqueidentifier NULL,
            attempts int NOT NULL CONSTRAINT DF_resume_intake_jobs_attempts DEFAULT 0,
            result nvarchar(20) NULL,
            outcome_code nvarchar(60) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_jobs_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_jobs_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_jobs PRIMARY KEY (job_id),
            CONSTRAINT UQ_resume_intake_jobs_key UNIQUE (job_key),
            CONSTRAINT FK_resume_intake_jobs_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_jobs_kind CHECK
                (kind IN (N'document_parse', N'voice_transcription', N'text_interpretation')),
            CONSTRAINT CK_resume_intake_jobs_state CHECK
                (state IN (N'queued', N'leased', N'completed', N'failed', N'refused', N'stale')),
            CONSTRAINT CK_resume_intake_jobs_result CHECK
                (result IS NULL OR result IN (N'saved', N'unresolved', N'failed', N'skipped')),
            CONSTRAINT CK_resume_intake_jobs_fence CHECK
                (source_version >= 1 AND submission_version >= 1 AND policy_version >= 1 AND lifecycle_epoch >= 0)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_proposals', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_proposals
        (
            proposal_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            proposal_key uniqueidentifier NOT NULL,
            source_key uniqueidentifier NOT NULL,
            source_version int NOT NULL,
            submission_key uniqueidentifier NOT NULL,
            submission_version int NOT NULL,
            lifecycle_epoch int NOT NULL,
            policy_version int NOT NULL,
            kind nvarchar(40) NOT NULL,
            record_type nvarchar(40) NOT NULL,
            confidence nvarchar(20) NULL,
            -- The versions captured when the proposal was made. Acceptance is
            -- checked against THESE, never a fresh re-read.
            target_key uniqueidentifier NULL,
            target_content_token nvarchar(64) NULL,
            target_access_revision int NULL,
            quote nvarchar(1000) NULL,
            span_start int NOT NULL,
            span_end int NOT NULL,
            proposed_values_json nvarchar(max) NOT NULL,
            confirmed_values_json nvarchar(max) NULL,
            provided_fields_json nvarchar(max) NULL,
            explicit_clears_json nvarchar(max) NULL,
            command_digest char(64) NULL,
            requires_member_wording bit NOT NULL CONSTRAINT DF_resume_intake_proposals_requires DEFAULT 1,
            state nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_proposals_state DEFAULT N'pending',
            decision nvarchar(20) NULL,
            source_purged bit NOT NULL CONSTRAINT DF_resume_intake_proposals_purged DEFAULT 0,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_proposals_created DEFAULT SYSUTCDATETIME(),
            decided_at_utc datetime2(7) NULL,
            CONSTRAINT PK_resume_intake_proposals PRIMARY KEY (proposal_id),
            CONSTRAINT UQ_resume_intake_proposals_key UNIQUE (proposal_key),
            CONSTRAINT FK_resume_intake_proposals_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_proposals_kind CHECK
                (kind IN (N'new_fact', N'change_existing', N'ambiguous_match', N'additional_detail',
                          N'contradiction', N'inferred_wording')),
            CONSTRAINT CK_resume_intake_proposals_record CHECK
                (record_type IN (N'role', N'education', N'credential', N'skill', N'accomplishment', N'unspecified')),
            CONSTRAINT CK_resume_intake_proposals_state CHECK
                (state IN (N'pending', N'accepted', N'rejected', N'invalidated')),
            CONSTRAINT CK_resume_intake_proposals_span CHECK (span_start >= 0 AND span_end >= span_start),
            CONSTRAINT CK_resume_intake_proposals_values CHECK (ISJSON(proposed_values_json) = 1),
            CONSTRAINT CK_resume_intake_proposals_confirmed CHECK
                (confirmed_values_json IS NULL OR ISJSON(confirmed_values_json) = 1)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_results', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_results
        (
            result_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            submission_key uniqueidentifier NOT NULL,
            client_key nvarchar(200) NOT NULL,
            kind nvarchar(20) NOT NULL,
            outcome nvarchar(20) NOT NULL,
            record_type nvarchar(40) NULL,
            proposal_key uniqueidentifier NULL,
            record_key uniqueidentifier NULL,
            message nvarchar(500) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_results_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_results PRIMARY KEY (result_id),
            CONSTRAINT UQ_resume_intake_results_client UNIQUE (owner_profile_id, submission_key, client_key),
            CONSTRAINT FK_resume_intake_results_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_results_outcome CHECK (outcome IN (N'saved', N'unresolved', N'failed'))
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_command_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_command_receipts
        (
            command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            command_type nvarchar(40) NOT NULL,
            outcome nvarchar(40) NOT NULL,
            submission_key uniqueidentifier NULL,
            -- The service's own payload digest. A same-key retry compares this,
            -- not the database command hash, so replay/conflict is exact.
            service_digest char(64) NOT NULL,
            -- Structural outcome only: never the member's words.
            result_json nvarchar(max) NOT NULL,
            committed_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_receipts_committed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_command_receipts PRIMARY KEY (command_receipt_id),
            CONSTRAINT UQ_resume_intake_command_receipts_owner_request UNIQUE (owner_profile_id, request_id),
            CONSTRAINT FK_resume_intake_command_receipts_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_command_receipts_digest
                CHECK (request_digest NOT LIKE '%[^0-9a-f]%' AND LEN(request_digest) = 64
                       AND service_digest NOT LIKE '%[^0-9a-f]%' AND LEN(service_digest) = 64),
            CONSTRAINT CK_resume_intake_command_receipts_type CHECK
                (command_type IN (N'add_submission', N'transcribe_recording', N'decide_proposal',
                                  N'purge_source', N'set_guide_status')),
            CONSTRAINT CK_resume_intake_command_receipts_json CHECK (ISJSON(result_json) = 1)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_intake_recording_claims', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_intake_recording_claims
        (
            recording_claim_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            lease_id uniqueidentifier NOT NULL,
            source_key uniqueidentifier NOT NULL,
            client_key nvarchar(200) NOT NULL,
            entrance nvarchar(40) NOT NULL,
            policy_version int NOT NULL,
            lifecycle_epoch int NOT NULL,
            audio_sha256 char(64) NOT NULL,
            byte_length bigint NOT NULL,
            content_type nvarchar(200) NOT NULL,
            duration_seconds decimal(10,3) NOT NULL,
            state nvarchar(20) NOT NULL CONSTRAINT DF_resume_intake_recording_claim_state DEFAULT N'leased',
            leased_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_recording_claim_leased DEFAULT SYSUTCDATETIME(),
            lease_expires_at_utc datetime2(7) NOT NULL,
            completed_at_utc datetime2(7) NULL,
            CONSTRAINT PK_resume_intake_recording_claims PRIMARY KEY (recording_claim_id),
            CONSTRAINT UQ_resume_intake_recording_claims_owner_request UNIQUE (owner_profile_id, request_id),
            CONSTRAINT UQ_resume_intake_recording_claims_lease UNIQUE (lease_id),
            CONSTRAINT UQ_resume_intake_recording_claims_source UNIQUE (source_key),
            CONSTRAINT FK_resume_intake_recording_claims_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_recording_claims_digest CHECK
                (request_digest NOT LIKE '%[^0-9a-f]%' AND LEN(request_digest) = 64
                 AND audio_sha256 NOT LIKE '%[^0-9a-f]%' AND LEN(audio_sha256) = 64),
            CONSTRAINT CK_resume_intake_recording_claims_state CHECK
                ((state IN (N'leased', N'recovery_required') AND completed_at_utc IS NULL)
                 OR (state = N'completed' AND completed_at_utc IS NOT NULL)),
            CONSTRAINT CK_resume_intake_recording_claims_bounds CHECK
                (policy_version >= 1 AND lifecycle_epoch >= 0 AND byte_length > 0
                 AND duration_seconds > 0 AND lease_expires_at_utc > leased_at_utc)
        );
    END;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_resume_intake_submissions_immutable
        ON dbo.resume_intake_submissions
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 52301, ''Resume intake submissions are immutable.'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_resume_intake_receipts_immutable
        ON dbo.resume_intake_command_receipts
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 52302, ''Resume intake command receipts are immutable.'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ResumeIntakeResolveOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
            SELECT @ProfileId AS profile_id;
        END;
    ');

    -- Shared helpers. A payload-aware idempotency check that replays the stored
    -- structural receipt, and one canonical-intent applier that dispatches to
    -- the correct EXISTING boundary with its own declared command contract.
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ResumeIntakeApplyCanonicalIntents
            @UserKey nvarchar(300),
            @IntentsJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            IF @IntentsJson IS NULL OR ISJSON(@IntentsJson) <> 1 RETURN;
            DECLARE @Intents nvarchar(max) = JSON_QUERY(@IntentsJson, ''$.canonical_intents'');
            IF @Intents IS NULL OR ISJSON(@Intents) <> 1 RETURN;
            IF (SELECT COUNT(*) FROM OPENJSON(@Intents)) = 0 RETURN;

            DECLARE @Boundary nvarchar(40);
            DECLARE @IntentRequestId uniqueidentifier;
            DECLARE @IntentCommand nvarchar(max);
            DECLARE @IntentType nvarchar(40);
            DECLARE @IntentKeyCount int;

            DECLARE intent_cursor CURSOR LOCAL FAST_FORWARD FOR
                SELECT JSON_VALUE(intent.value, ''$.boundary''),
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(intent.value, ''$.request_id'')),
                       JSON_QUERY(intent.value, ''$.command'')
                FROM OPENJSON(@Intents) AS intent;

            OPEN intent_cursor;
            FETCH NEXT FROM intent_cursor INTO @Boundary, @IntentRequestId, @IntentCommand;
            WHILE @@FETCH_STATUS = 0
            BEGIN
                IF @IntentCommand IS NULL OR ISJSON(@IntentCommand) <> 1
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                IF @IntentRequestId IS NULL
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                SET @IntentType = JSON_VALUE(@IntentCommand, ''$.type'');

                IF @Boundary = N''living_resume''
                BEGIN
                    -- PS-RESUME-EDIT-002 rejects any key outside this closed set.
                    SET @IntentKeyCount = (SELECT COUNT(*) FROM OPENJSON(@IntentCommand));
                    IF @IntentKeyCount <> 6
                       OR EXISTS (
                            SELECT 1 FROM OPENJSON(@IntentCommand) AS supplied
                            WHERE supplied.[key] NOT IN
                                (N''command_id'', N''type'', N''record_key'', N''parent_key'',
                                 N''expected_version'', N''values'')
                       )
                        THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                    IF @IntentType NOT IN
                        (N''create_role'', N''update_role'', N''remove_role'',
                         N''create_accomplishment'', N''update_accomplishment'', N''remove_accomplishment'',
                         N''create_skill'', N''update_skill'', N''remove_skill'',
                         N''create_credential'', N''update_credential'', N''remove_credential'',
                         N''create_education'', N''update_education'', N''remove_education'')
                        THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                    IF TRY_CONVERT(uniqueidentifier, JSON_VALUE(@IntentCommand, ''$.command_id'')) <> @IntentRequestId
                        THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                    EXEC dbo.usp_CommitLivingResumeCommandForOwner
                        @UserKey = @UserKey,
                        @CommandId = @IntentRequestId,
                        @CommandJson = @IntentCommand;
                END
                ELSE IF @Boundary = N''resume_draft''
                BEGIN
                    IF @IntentType NOT IN
                        (N''save_item'', N''discard_item'', N''create_private_item'', N''review_candidate'')
                        THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                    EXEC dbo.usp_CommitResumeDraftCommandForOwner
                        @UserKey = @UserKey,
                        @RequestId = @IntentRequestId,
                        @CommandJson = @IntentCommand;
                END
                ELSE
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                FETCH NEXT FROM intent_cursor INTO @Boundary, @IntentRequestId, @IntentCommand;
            END;
            CLOSE intent_cursor;
            DEALLOCATE intent_cursor;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ClaimResumeIntakeRecordingForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
                IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
                IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                IF (SELECT COUNT(*) FROM OPENJSON(@CommandJson)) <> 11
                   OR EXISTS (
                        SELECT 1 FROM OPENJSON(@CommandJson) AS supplied
                        WHERE supplied.[key] NOT IN
                            (N''type'', N''request_id'', N''request_digest'', N''client_key'',
                             N''entrance'', N''policy_version'', N''lifecycle_epoch'',
                             N''audio_sha256'', N''byte_length'', N''content_type'',
                             N''duration_seconds'')
                   )
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                DECLARE @ClaimRequestId uniqueidentifier =
                    TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.request_id''));
                IF JSON_VALUE(@CommandJson, ''$.type'') <> N''claim_recording''
                   OR @ClaimRequestId IS NULL OR @ClaimRequestId <> @RequestId
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                DECLARE @ServiceDigest char(64) = JSON_VALUE(@CommandJson, ''$.request_digest'');
                DECLARE @ClientKey nvarchar(200) = JSON_VALUE(@CommandJson, ''$.client_key'');
                DECLARE @Entrance nvarchar(40) = JSON_VALUE(@CommandJson, ''$.entrance'');
                DECLARE @PolicyVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.policy_version''));
                DECLARE @LifecycleEpoch int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.lifecycle_epoch''));
                DECLARE @AudioSha256 char(64) = JSON_VALUE(@CommandJson, ''$.audio_sha256'');
                DECLARE @ByteLength bigint = TRY_CONVERT(bigint, JSON_VALUE(@CommandJson, ''$.byte_length''));
                DECLARE @ContentType nvarchar(200) = JSON_VALUE(@CommandJson, ''$.content_type'');
                DECLARE @DurationSeconds decimal(10,3) =
                    TRY_CONVERT(decimal(10,3), JSON_VALUE(@CommandJson, ''$.duration_seconds''));
                IF @ServiceDigest IS NULL OR LEN(@ServiceDigest) <> 64 OR @ClientKey IS NULL
                   OR @Entrance IS NULL OR @PolicyVersion IS NULL OR @PolicyVersion < 1
                   OR @LifecycleEpoch IS NULL OR @LifecycleEpoch < 0
                   OR @AudioSha256 IS NULL OR LEN(@AudioSha256) <> 64
                   OR @ByteLength IS NULL OR @ByteLength < 1 OR @ContentType IS NULL
                   OR @DurationSeconds IS NULL OR @DurationSeconds <= 0
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                DECLARE @ReceiptDigest char(64);
                DECLARE @ReceiptResult nvarchar(max);
                SELECT @ReceiptDigest = receipt.service_digest,
                       @ReceiptResult = receipt.result_json
                FROM dbo.resume_intake_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
                WHERE receipt.owner_profile_id = @ProfileId AND receipt.request_id = @RequestId;
                IF @ReceiptDigest IS NOT NULL
                BEGIN
                    IF @ReceiptDigest <> @ServiceDigest
                    BEGIN
                        SELECT N''conflict'' AS outcome, @ServiceDigest AS request_digest;
                        COMMIT TRANSACTION;
                        RETURN;
                    END;
                    SELECT N''replay'' AS outcome, @ReceiptDigest AS request_digest,
                           @ReceiptResult AS result_json;
                    COMMIT TRANSACTION;
                    RETURN;
                END;

                DECLARE @ExistingDigest char(64);
                DECLARE @ExistingLease uniqueidentifier;
                DECLARE @ExistingSource uniqueidentifier;
                DECLARE @ExistingClient nvarchar(200);
                DECLARE @ExistingEntrance nvarchar(40);
                DECLARE @ExistingPolicy int;
                DECLARE @ExistingEpoch int;
                DECLARE @ExistingAudio char(64);
                DECLARE @ExistingLength bigint;
                DECLARE @ExistingType nvarchar(200);
                DECLARE @ExistingDuration decimal(10,3);
                DECLARE @ExistingExpiry datetime2(7);
                DECLARE @ExistingState nvarchar(20);
                SELECT @ExistingDigest = claim.request_digest,
                       @ExistingLease = claim.lease_id,
                       @ExistingSource = claim.source_key,
                       @ExistingClient = claim.client_key,
                       @ExistingEntrance = claim.entrance,
                       @ExistingPolicy = claim.policy_version,
                       @ExistingEpoch = claim.lifecycle_epoch,
                       @ExistingAudio = claim.audio_sha256,
                       @ExistingLength = claim.byte_length,
                       @ExistingType = claim.content_type,
                       @ExistingDuration = claim.duration_seconds,
                       @ExistingExpiry = claim.lease_expires_at_utc,
                       @ExistingState = claim.state
                FROM dbo.resume_intake_recording_claims AS claim WITH (UPDLOCK, HOLDLOCK)
                WHERE claim.owner_profile_id = @ProfileId AND claim.request_id = @RequestId;
                IF @ExistingDigest IS NOT NULL
                BEGIN
                    IF @ExistingDigest <> @ServiceDigest OR @ExistingClient <> @ClientKey
                       OR @ExistingEntrance <> @Entrance OR @ExistingPolicy <> @PolicyVersion
                       OR @ExistingEpoch <> @LifecycleEpoch OR @ExistingAudio <> @AudioSha256
                       OR @ExistingLength <> @ByteLength OR @ExistingType <> @ContentType
                       OR @ExistingDuration <> @DurationSeconds
                    BEGIN
                        SELECT N''conflict'' AS outcome, @ServiceDigest AS request_digest;
                        COMMIT TRANSACTION;
                        RETURN;
                    END;
                    -- Expiry never transfers provider custody automatically.
                    -- It only records that the stuck/ambiguous claim needs an
                    -- explicit recovery decision outside this browser command.
                    IF @ExistingState = N''leased'' AND @ExistingExpiry <= SYSUTCDATETIME()
                    BEGIN
                        UPDATE dbo.resume_intake_recording_claims
                        SET state = N''recovery_required''
                        WHERE owner_profile_id = @ProfileId AND request_id = @RequestId
                          AND state = N''leased'';
                        SET @ExistingState = N''recovery_required'';
                    END;
                    SELECT N''pending'' AS outcome, @ExistingDigest AS request_digest,
                           CONVERT(bit, CASE WHEN @ExistingState <> N''leased'' THEN 1 ELSE 0 END)
                               AS recovery_required,
                           @ExistingExpiry AS lease_expires_at_utc;
                    COMMIT TRANSACTION;
                    RETURN;
                END;

                DECLARE @CurrentEpoch int;
                SELECT @CurrentEpoch = state.lifecycle_epoch
                FROM dbo.resume_intake_owner_state AS state WITH (UPDLOCK, HOLDLOCK)
                WHERE state.owner_profile_id = @ProfileId;
                IF @CurrentEpoch IS NOT NULL AND @CurrentEpoch <> @LifecycleEpoch
                BEGIN
                    SELECT N''conflict'' AS outcome, @ServiceDigest AS request_digest;
                    COMMIT TRANSACTION;
                    RETURN;
                END;

                MERGE dbo.resume_intake_owner_state WITH (UPDLOCK, HOLDLOCK) AS target
                USING (SELECT @ProfileId AS owner_profile_id) AS source
                   ON target.owner_profile_id = source.owner_profile_id
                WHEN MATCHED THEN
                    UPDATE SET policy_version = @PolicyVersion, updated_at_utc = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT (owner_profile_id, lifecycle_epoch, policy_version)
                    VALUES (@ProfileId, @LifecycleEpoch, @PolicyVersion);

                DECLARE @LeaseId uniqueidentifier = NEWID();
                DECLARE @SourceKey uniqueidentifier = NEWID();
                DECLARE @LeaseExpires datetime2(7) = DATEADD(minute, 5, SYSUTCDATETIME());
                INSERT dbo.resume_intake_recording_claims
                    (owner_profile_id, request_id, request_digest, lease_id, source_key,
                     client_key, entrance, policy_version, lifecycle_epoch, audio_sha256,
                     byte_length, content_type, duration_seconds, lease_expires_at_utc)
                VALUES
                    (@ProfileId, @RequestId, @ServiceDigest, @LeaseId, @SourceKey,
                     @ClientKey, @Entrance, @PolicyVersion, @LifecycleEpoch, @AudioSha256,
                     @ByteLength, @ContentType, @DurationSeconds, @LeaseExpires);

                SELECT N''claimed'' AS outcome, @ServiceDigest AS request_digest,
                       @LeaseId AS lease_id, @SourceKey AS source_key,
                       @LeaseExpires AS lease_expires_at_utc;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeIntakeCommandForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            -- db.py opens this connection in AUTOCOMMIT, so XACT_ABORT and the
            -- isolation level alone would commit each statement independently.
            -- The member action owns this runtime transaction explicitly.
            BEGIN TRY
                BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;

            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2));
            DECLARE @ServiceDigest char(64) = JSON_VALUE(@CommandJson, ''$.request_digest'');
            IF @ServiceDigest IS NULL OR LEN(@ServiceDigest) <> 64
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingResult nvarchar(max);
            SELECT @ExistingDigest = receipt.service_digest,
                   @ExistingResult = receipt.result_json
            FROM dbo.resume_intake_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId AND receipt.request_id = @RequestId;
            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @ServiceDigest THROW 52303, ''RESUME_INTAKE_IDEMPOTENCY_CONFLICT'', 1;
                SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 1) AS replayed,
                       @ExistingDigest AS request_digest, @ExistingResult AS result_json,
                       CONVERT(bit, 0) AS publishes;
                COMMIT TRANSACTION;
                RETURN;
            END;

            DECLARE @CommandType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
            IF @CommandType NOT IN (N''add_submission'', N''transcribe_recording'')
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            IF @CommandType = N''add_submission''
            BEGIN
                -- The declared key set is enforced here, not merely asserted in
                -- Python: exactly these 16 keys, no more and no fewer.
                IF (SELECT COUNT(*) FROM OPENJSON(@CommandJson)) <> 16
                   OR EXISTS (
                        SELECT 1 FROM OPENJSON(@CommandJson) AS supplied
                        WHERE supplied.[key] NOT IN
                            (N''type'', N''request_id'', N''submission_key'', N''submission_version'',
                             N''entrance'', N''policy_version'', N''lifecycle_epoch'', N''request_digest'',
                             N''sources'', N''jobs'', N''proposals'', N''results'', N''summary'',
                             N''receipt'', N''last_receipt'', N''canonical_intents'')
                   )
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
                IF JSON_QUERY(@CommandJson, ''$.sources'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.jobs'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.proposals'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.results'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.summary'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.receipt'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.last_receipt'') IS NULL
                   OR JSON_QUERY(@CommandJson, ''$.canonical_intents'') IS NULL
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                DECLARE @SubmissionKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.submission_key''));
                DECLARE @SubmissionVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.submission_version''));
                DECLARE @Entrance nvarchar(40) = JSON_VALUE(@CommandJson, ''$.entrance'');
                DECLARE @PolicyVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.policy_version''));
                DECLARE @Epoch int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.lifecycle_epoch''));
                IF @SubmissionKey IS NULL OR @SubmissionVersion IS NULL OR @Entrance IS NULL
                   OR @PolicyVersion IS NULL OR @Epoch IS NULL
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                MERGE dbo.resume_intake_owner_state WITH (UPDLOCK, HOLDLOCK) AS target
                USING (SELECT @ProfileId AS owner_profile_id) AS source
                   ON target.owner_profile_id = source.owner_profile_id
                WHEN MATCHED THEN
                    UPDATE SET lifecycle_epoch = @Epoch,
                               policy_version = @PolicyVersion,
                               last_receipt_json = JSON_QUERY(@CommandJson, ''$.last_receipt''),
                               updated_at_utc = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT (owner_profile_id, lifecycle_epoch, policy_version, last_receipt_json)
                    VALUES (@ProfileId, @Epoch, @PolicyVersion, JSON_QUERY(@CommandJson, ''$.last_receipt''));

                INSERT dbo.resume_intake_submissions
                    (owner_profile_id, submission_key, request_id, request_digest,
                     submission_version, entrance, policy_version)
                VALUES
                    (@ProfileId, @SubmissionKey, @RequestId, @ServiceDigest,
                     @SubmissionVersion, @Entrance, @PolicyVersion);

                -- Canonical writes happen INSIDE this transaction, through the
                -- existing closed boundaries. A THROW anywhere rolls back the
                -- canonical write and every intake row together.
                EXEC dbo.usp_ResumeIntakeApplyCanonicalIntents
                    @UserKey = @UserKey,
                    @IntentsJson = @CommandJson;

                INSERT dbo.resume_intake_sources
                    (owner_profile_id, submission_key, source_key, kind, state, source_version,
                     entrance, policy_version, content_type, byte_length, sha256,
                     structured_values_json, source_text)
                SELECT @ProfileId, @SubmissionKey,
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(source.value, ''$.source_key'')),
                       JSON_VALUE(source.value, ''$.kind''),
                       JSON_VALUE(source.value, ''$.state''),
                       TRY_CONVERT(int, JSON_VALUE(source.value, ''$.version'')),
                       @Entrance, @PolicyVersion,
                       JSON_VALUE(source.value, ''$.content_type''),
                       TRY_CONVERT(bigint, JSON_VALUE(source.value, ''$.byte_length'')),
                       JSON_VALUE(source.value, ''$.sha256''),
                       JSON_QUERY(source.value, ''$.structured_values''),
                       JSON_VALUE(source.value, ''$.text'')
                FROM OPENJSON(@CommandJson, ''$.sources'') AS source;

                INSERT dbo.resume_intake_jobs
                    (owner_profile_id, job_key, source_key, source_version, submission_key,
                     submission_version, policy_version, lifecycle_epoch, kind, state, attempts,
                     result, outcome_code, created_at_utc, updated_at_utc)
                SELECT @ProfileId,
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(job.value, ''$.job_key'')),
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(job.value, ''$.source_key'')),
                       TRY_CONVERT(int, JSON_VALUE(job.value, ''$.source_version'')),
                       @SubmissionKey,
                       TRY_CONVERT(int, JSON_VALUE(job.value, ''$.submission_version'')),
                       TRY_CONVERT(int, JSON_VALUE(job.value, ''$.policy_version'')),
                       TRY_CONVERT(int, JSON_VALUE(job.value, ''$.lifecycle_epoch'')),
                       JSON_VALUE(job.value, ''$.kind''),
                       JSON_VALUE(job.value, ''$.state''),
                       ISNULL(TRY_CONVERT(int, JSON_VALUE(job.value, ''$.attempts'')), 1),
                       JSON_VALUE(job.value, ''$.result''),
                       JSON_VALUE(job.value, ''$.outcome''),
                       SYSUTCDATETIME(), SYSUTCDATETIME()
                FROM OPENJSON(@CommandJson, ''$.jobs'') AS job;

                INSERT dbo.resume_intake_proposals
                    (owner_profile_id, proposal_key, source_key, source_version, submission_key,
                     submission_version, lifecycle_epoch, policy_version, kind, record_type,
                     confidence, target_key, target_content_token, target_access_revision,
                     quote, span_start, span_end, proposed_values_json, provided_fields_json,
                     explicit_clears_json, command_digest, requires_member_wording)
                SELECT @ProfileId,
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(proposal.value, ''$.proposal_key'')),
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(proposal.value, ''$.binding.source_key'')),
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.binding.source_version'')),
                       @SubmissionKey,
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.binding.submission_version'')),
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.binding.lifecycle_epoch'')),
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.binding.policy_version'')),
                       JSON_VALUE(proposal.value, ''$.kind''),
                       JSON_VALUE(proposal.value, ''$.record_type''),
                       JSON_VALUE(proposal.value, ''$.confidence''),
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(proposal.value, ''$.target_key'')),
                       JSON_VALUE(proposal.value, ''$.target_content_token''),
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.target_access_revision'')),
                       JSON_VALUE(proposal.value, ''$.quote''),
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.span_start'')),
                       TRY_CONVERT(int, JSON_VALUE(proposal.value, ''$.span_end'')),
                       ISNULL(JSON_QUERY(proposal.value, ''$.proposed_values''), N''{}''),
                       ISNULL(JSON_QUERY(proposal.value, ''$.provided_fields''), N''[]''),
                       ISNULL(JSON_QUERY(proposal.value, ''$.explicit_clears''), N''[]''),
                       JSON_VALUE(proposal.value, ''$.command_digest''),
                       ISNULL(TRY_CONVERT(bit, JSON_VALUE(proposal.value, ''$.requires_member_wording'')), 1)
                FROM OPENJSON(@CommandJson, ''$.proposals'') AS proposal;

                INSERT dbo.resume_intake_results
                    (owner_profile_id, submission_key, client_key, kind, outcome,
                     record_type, proposal_key, record_key, message)
                SELECT @ProfileId, @SubmissionKey,
                       JSON_VALUE(result.value, ''$.client_key''),
                       JSON_VALUE(result.value, ''$.kind''),
                       JSON_VALUE(result.value, ''$.outcome''),
                       JSON_VALUE(result.value, ''$.record_type''),
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(result.value, ''$.proposal_key'')),
                       TRY_CONVERT(uniqueidentifier, JSON_VALUE(result.value, ''$.record_key'')),
                       JSON_VALUE(result.value, ''$.message'')
                FROM OPENJSON(@CommandJson, ''$.results'') AS result;
            END
            ELSE
            BEGIN
                -- Pre-Add transcription: intake material only. No submission,
                -- no canonical fact, and the entrance/policy travel so the
                -- source row satisfies its NOT NULL columns and retention fence.
                IF (SELECT COUNT(*) FROM OPENJSON(@CommandJson)) <> 17
                   OR EXISTS (
                        SELECT 1 FROM OPENJSON(@CommandJson) AS supplied
                        WHERE supplied.[key] NOT IN
                            (N''type'', N''request_id'', N''client_key'', N''entrance'', N''policy_version'',
                             N''audio_sha256'', N''byte_length'', N''content_type'',
                             N''outcome'', N''transcript'', N''source_key'', N''source_version'',
                             N''receipt'', N''request_digest'', N''lease_id'',
                             N''lifecycle_epoch'', N''duration_seconds'')
                   )
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                DECLARE @RecEntrance nvarchar(40) = JSON_VALUE(@CommandJson, ''$.entrance'');
                DECLARE @RecPolicy int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.policy_version''));
                DECLARE @RecSourceKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.source_key''));
                DECLARE @RecOutcome nvarchar(40) = JSON_VALUE(@CommandJson, ''$.outcome'');
                DECLARE @RecLease uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.lease_id''));
                DECLARE @RecEpoch int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.lifecycle_epoch''));
                DECLARE @RecDuration decimal(10,3) =
                    TRY_CONVERT(decimal(10,3), JSON_VALUE(@CommandJson, ''$.duration_seconds''));
                IF @RecEntrance IS NULL OR @RecPolicy IS NULL OR @RecOutcome IS NULL
                   OR @RecSourceKey IS NULL OR @RecLease IS NULL OR @RecEpoch IS NULL
                   OR @RecDuration IS NULL
                    THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

                DECLARE @ClaimState nvarchar(20);
                SELECT @ClaimState = claim.state
                FROM dbo.resume_intake_recording_claims AS claim WITH (UPDLOCK, HOLDLOCK)
                WHERE claim.owner_profile_id = @ProfileId
                  AND claim.request_id = @RequestId
                  AND claim.request_digest = @ServiceDigest
                  AND claim.lease_id = @RecLease
                  AND claim.source_key = @RecSourceKey
                  AND claim.client_key = JSON_VALUE(@CommandJson, ''$.client_key'')
                  AND claim.entrance = @RecEntrance
                  AND claim.policy_version = @RecPolicy
                  AND claim.lifecycle_epoch = @RecEpoch
                  AND claim.audio_sha256 = JSON_VALUE(@CommandJson, ''$.audio_sha256'')
                  AND claim.byte_length = TRY_CONVERT(bigint, JSON_VALUE(@CommandJson, ''$.byte_length''))
                  AND claim.content_type = JSON_VALUE(@CommandJson, ''$.content_type'')
                  AND claim.duration_seconds = @RecDuration
                  AND claim.lease_expires_at_utc > SYSUTCDATETIME();
                IF @ClaimState <> N''leased'' OR @ClaimState IS NULL
                    THROW 52317, ''RESUME_INTAKE_RECORDING_CLAIM_CHANGED'', 1;

                IF NOT EXISTS (
                    SELECT 1 FROM dbo.resume_intake_owner_state AS state WITH (UPDLOCK, HOLDLOCK)
                    WHERE state.owner_profile_id = @ProfileId
                      AND state.lifecycle_epoch = @RecEpoch
                      AND state.policy_version = @RecPolicy
                )
                    THROW 52317, ''RESUME_INTAKE_RECORDING_CLAIM_CHANGED'', 1;

                IF @RecOutcome = N''transcribed''
                BEGIN
                    INSERT dbo.resume_intake_sources
                        (owner_profile_id, submission_key, source_key, kind, state, source_version,
                         entrance, policy_version, content_type, byte_length, sha256, source_text)
                    VALUES
                        (@ProfileId, NULL, @RecSourceKey, N''recording'', N''active'', 1,
                         @RecEntrance, @RecPolicy,
                         JSON_VALUE(@CommandJson, ''$.content_type''),
                         TRY_CONVERT(bigint, JSON_VALUE(@CommandJson, ''$.byte_length'')),
                         JSON_VALUE(@CommandJson, ''$.audio_sha256''),
                         JSON_VALUE(@CommandJson, ''$.transcript''));
                END

                UPDATE dbo.resume_intake_owner_state
                SET policy_version = @RecPolicy, updated_at_utc = SYSUTCDATETIME()
                WHERE owner_profile_id = @ProfileId;

                UPDATE dbo.resume_intake_recording_claims
                SET state = N''completed'', completed_at_utc = SYSUTCDATETIME()
                WHERE owner_profile_id = @ProfileId AND request_id = @RequestId
                  AND lease_id = @RecLease AND state = N''leased'';
            END;

            INSERT dbo.resume_intake_command_receipts
                (owner_profile_id, request_id, request_digest, command_type, outcome,
                 submission_key, service_digest, result_json)
            VALUES
                (@ProfileId, @RequestId, @Digest, @CommandType,
                 ISNULL(JSON_VALUE(@CommandJson, ''$.outcome''), JSON_VALUE(@CommandJson, ''$.summary.outcome'')),
                 CASE WHEN @CommandType = N''add_submission'' THEN @SubmissionKey ELSE NULL END,
                 @ServiceDigest,
                 JSON_QUERY(@CommandJson, ''$.receipt''));

            SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 0) AS replayed,
                   @ServiceDigest AS request_digest, CONVERT(bit, 0) AS publishes;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeIntakeSubmissionForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            EXEC dbo.usp_CommitResumeIntakeCommandForOwner
                @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeIntakeRecordingForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            EXEC dbo.usp_CommitResumeIntakeCommandForOwner
                @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeIntakeProposalDecisionForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            -- The decision writes intake state and, for an accepted change, the
            -- canonical overlay in one autocommit-environment transaction.
            BEGIN TRY
                BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            DECLARE @ServiceDigest char(64) = JSON_VALUE(@CommandJson, ''$.request_digest'');
            IF @ServiceDigest IS NULL OR LEN(@ServiceDigest) <> 64
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
            DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2));

            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingResult nvarchar(max);
            SELECT @ExistingDigest = receipt.service_digest,
                   @ExistingResult = receipt.result_json
            FROM dbo.resume_intake_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId AND receipt.request_id = @RequestId;
            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @ServiceDigest THROW 52303, ''RESUME_INTAKE_IDEMPOTENCY_CONFLICT'', 1;
                SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 1) AS replayed,
                       @ExistingDigest AS request_digest, @ExistingResult AS result_json;
                COMMIT TRANSACTION;
                RETURN;
            END;

            DECLARE @ProposalKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.proposal_key''));
            DECLARE @Decision nvarchar(20) = JSON_VALUE(@CommandJson, ''$.decision'');
            DECLARE @Outcome nvarchar(40) = JSON_VALUE(@CommandJson, ''$.outcome'');
            IF @ProposalKey IS NULL OR @Decision NOT IN (N''accept'', N''reject'', N''edit'')
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            DECLARE @State nvarchar(20);
            DECLARE @SourceKey uniqueidentifier;
            DECLARE @SourceVersion int;
            DECLARE @FenceEpoch int;
            SELECT @State = proposal.state, @SourceKey = proposal.source_key,
                   @SourceVersion = proposal.source_version,
                   @FenceEpoch = proposal.lifecycle_epoch
            FROM dbo.resume_intake_proposals AS proposal WITH (UPDLOCK, HOLDLOCK)
            WHERE proposal.owner_profile_id = @ProfileId AND proposal.proposal_key = @ProposalKey;
            IF @State IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
            IF @State = N''invalidated'' THROW 52305, ''RESUME_INTAKE_CHANGED'', 1;
            IF @State <> N''pending'' THROW 52306, ''RESUME_INTAKE_ALREADY_DECIDED'', 1;

            IF @Decision IN (N''accept'', N''edit'')
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM dbo.resume_intake_sources AS source WITH (UPDLOCK, HOLDLOCK)
                               WHERE source.owner_profile_id = @ProfileId
                                 AND source.source_key = @SourceKey
                                 AND source.state = N''active''
                                 AND source.source_version = @SourceVersion)
                    THROW 52305, ''RESUME_INTAKE_CHANGED'', 1;
                IF EXISTS (SELECT 1 FROM dbo.resume_intake_owner_state AS state WITH (UPDLOCK, HOLDLOCK)
                           WHERE state.owner_profile_id = @ProfileId
                             AND state.lifecycle_epoch <> @FenceEpoch)
                    THROW 52305, ''RESUME_INTAKE_CHANGED'', 1;

                DECLARE @TargetKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.target_key''));
                DECLARE @TargetAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.target_access_revision''));
                IF @TargetKey IS NOT NULL AND @TargetAccess IS NOT NULL
                   AND EXISTS (SELECT 1 FROM dbo.entry_policy_records AS record WITH (UPDLOCK, HOLDLOCK)
                               WHERE record.owner_profile_id = @ProfileId
                                 AND record.entry_key = @TargetKey
                                 AND record.access_revision <> @TargetAccess)
                    THROW 52305, ''RESUME_INTAKE_CHANGED'', 1;

                -- Only after every fence check: the accepted change is written
                -- by the SAME canonical boundary, inside this transaction.
                EXEC dbo.usp_ResumeIntakeApplyCanonicalIntents
                    @UserKey = @UserKey,
                    @IntentsJson = @CommandJson;
            END;

            UPDATE dbo.resume_intake_proposals
            SET state = CASE WHEN @Decision = N''reject'' THEN N''rejected'' ELSE N''accepted'' END,
                decision = @Decision,
                -- Accepted wording stays in this source-bound, purgeable row.
                -- It is not copied into the immutable receipt, and source purge
                -- clears it alongside quote/proposed values.
                confirmed_values_json = CASE WHEN @Decision IN (N''accept'', N''edit'')
                                             THEN JSON_QUERY(@CommandJson, ''$.confirmed_values'')
                                             ELSE NULL END,
                command_digest = @ServiceDigest,
                decided_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND proposal_key = @ProposalKey;

            INSERT dbo.resume_intake_command_receipts
                (owner_profile_id, request_id, request_digest, command_type, outcome,
                 submission_key, service_digest, result_json)
            VALUES
                (@ProfileId, @RequestId, @Digest, N''decide_proposal'',
                 ISNULL(@Outcome, CASE WHEN @Decision = N''reject'' THEN N''rejected'' ELSE N''accepted'' END),
                 NULL, @ServiceDigest, JSON_QUERY(@CommandJson, ''$.receipt''));

            SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 0) AS replayed, @ServiceDigest AS request_digest;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SetResumeGuideStatusForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            BEGIN TRY
                BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            DECLARE @ServiceDigest char(64) = JSON_VALUE(@CommandJson, ''$.request_digest'');
            DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2));
            DECLARE @Status nvarchar(20) = JSON_VALUE(@CommandJson, ''$.status'');
            DECLARE @StatusSource nvarchar(20) = ISNULL(JSON_VALUE(@CommandJson, ''$.status_source''), N''member'');
            IF @ServiceDigest IS NULL OR LEN(@ServiceDigest) <> 64
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
            IF @Status NOT IN (N''in_progress'', N''paused'', N''completed'', N''skipped'')
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
            IF @StatusSource <> N''member''
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            -- Idempotent on the request id as well, so a replayed guide status
            -- returns the stored outcome instead of violating the unique key.
            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingResult nvarchar(max);
            SELECT @ExistingDigest = receipt.service_digest,
                   @ExistingResult = receipt.result_json
            FROM dbo.resume_intake_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId AND receipt.request_id = @RequestId;
            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @ServiceDigest THROW 52303, ''RESUME_INTAKE_IDEMPOTENCY_CONFLICT'', 1;
                SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 1) AS replayed,
                       @ExistingDigest AS request_digest, @ExistingResult AS result_json,
                       @Status AS guide_status;
                COMMIT TRANSACTION;
                RETURN;
            END;

            MERGE dbo.resume_intake_owner_state WITH (UPDLOCK, HOLDLOCK) AS target
            USING (SELECT @ProfileId AS owner_profile_id) AS source
               ON target.owner_profile_id = source.owner_profile_id
            WHEN MATCHED THEN
                UPDATE SET guide_status = @Status, guide_status_source = @StatusSource, updated_at_utc = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (owner_profile_id, guide_status, guide_status_source)
                VALUES (@ProfileId, @Status, @StatusSource);

            INSERT dbo.resume_intake_command_receipts
                (owner_profile_id, request_id, request_digest, command_type, outcome,
                 submission_key, service_digest, result_json)
            VALUES
                (@ProfileId, @RequestId, @Digest, N''set_guide_status'', @Status, NULL,
                 @ServiceDigest, JSON_QUERY(@CommandJson, ''$.receipt''));

            SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 0) AS replayed,
                   @ServiceDigest AS request_digest, @Status AS guide_status;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeResumeIntakeSourceForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            BEGIN TRY
                BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            DECLARE @ServiceDigest char(64) = JSON_VALUE(@CommandJson, ''$.request_digest'');
            DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2));
            IF @ServiceDigest IS NULL OR LEN(@ServiceDigest) <> 64
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            -- Purge is idempotent: a repeated request replays its stored receipt.
            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingResult nvarchar(max);
            SELECT @ExistingDigest = receipt.service_digest,
                   @ExistingResult = receipt.result_json
            FROM dbo.resume_intake_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId AND receipt.request_id = @RequestId;
            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @ServiceDigest THROW 52303, ''RESUME_INTAKE_IDEMPOTENCY_CONFLICT'', 1;
                SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 1) AS replayed,
                       @ExistingDigest AS request_digest, @ExistingResult AS result_json,
                       CONVERT(bit, 1) AS provenance_retained;
                COMMIT TRANSACTION;
                RETURN;
            END;

            DECLARE @SourceKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.source_key''));
            IF @SourceKey IS NULL THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
            IF NOT EXISTS (SELECT 1 FROM dbo.resume_intake_sources WITH (UPDLOCK, HOLDLOCK)
                           WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey)
                THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;

            -- Purge drops the member''s words and advances the source version so
            -- late work is fenced. Independently accepted canonical content
            -- survives its source and is never modified by this purge. The immutable receipts are untouched
            -- because they never carried the words in the first place.
            UPDATE dbo.resume_intake_sources
            SET state = N''purged'', source_text = NULL, structured_values_json = NULL,
                purged_at_utc = SYSUTCDATETIME(), source_version = source_version + 1
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey AND state = N''active'';

            UPDATE dbo.resume_intake_jobs
            SET state = N''stale'', lease_id = NULL, updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey
              AND state IN (N''queued'', N''leased'');

            UPDATE dbo.resume_intake_proposals
            SET source_purged = 1,
                quote = NULL,
                proposed_values_json = N''{"redacted":true}'',
                confirmed_values_json = NULL,
                state = CASE WHEN state = N''pending'' THEN N''invalidated'' ELSE state END,
                decided_at_utc = CASE WHEN state = N''pending'' THEN SYSUTCDATETIME() ELSE decided_at_utc END
            WHERE owner_profile_id = @ProfileId AND source_key = @SourceKey;

            UPDATE dbo.resume_intake_owner_state
            SET lifecycle_epoch = lifecycle_epoch + 1, updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId;

            INSERT dbo.resume_intake_command_receipts
                (owner_profile_id, request_id, request_digest, command_type, outcome,
                 submission_key, service_digest, result_json)
            VALUES
                (@ProfileId, @RequestId, @Digest, N''purge_source'', N''purged'', NULL,
                 @ServiceDigest, JSON_QUERY(@CommandJson, ''$.receipt''));

            SELECT CONVERT(bit, 1) AS committed, CONVERT(bit, 0) AS replayed,
                   @ServiceDigest AS request_digest, CONVERT(bit, 1) AS provenance_retained;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetResumeIntakeWorkspaceForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;

            -- One row, one nvarchar(max) column. Every column selected here is
            -- declared by this migration (or a predecessor) and mapped by
            -- SqlResumeIntakeRepository.map_declared_workspace.
            SELECT (
                SELECT
                    ISNULL(state.lifecycle_epoch, 0) AS lifecycle_epoch,
                    ISNULL(state.policy_version, 0) AS policy_version,
                    JSON_QUERY((
                        SELECT guide_status AS [status], guide_status_source AS [status_source]
                        FROM dbo.resume_intake_owner_state AS guide
                        WHERE guide.owner_profile_id = @ProfileId
                        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
                    )) AS guide,
                    JSON_QUERY((
                        SELECT last_receipt_json
                        FROM dbo.resume_intake_owner_state AS owner_state
                        WHERE owner_state.owner_profile_id = @ProfileId
                    )) AS last_receipt_json,
                    JSON_QUERY((
                        SELECT CONVERT(nvarchar(36), submission_key) AS submission_key,
                               submission_version AS version, state, entrance,
                               policy_version, CONVERT(nvarchar(36), request_id) AS request_id,
                               request_digest, created_at_utc
                        FROM dbo.resume_intake_submissions
                        WHERE owner_profile_id = @ProfileId
                        FOR JSON PATH
                    )) AS submissions,
                    JSON_QUERY((
                        SELECT CONVERT(nvarchar(36), source_key) AS source_key, kind, state,
                               source_version AS version, source_text AS text,
                               structured_values_json,
                               CONVERT(nvarchar(36), submission_key) AS submission_key,
                               content_type, byte_length, sha256, created_at_utc
                        FROM dbo.resume_intake_sources
                        WHERE owner_profile_id = @ProfileId
                        FOR JSON PATH
                    )) AS sources,
                    JSON_QUERY((
                        SELECT CONVERT(nvarchar(36), job_key) AS job_key, kind, state, result,
                               outcome_code AS outcome, attempts,
                               CONVERT(nvarchar(36), source_key) AS source_key, source_version,
                               CONVERT(nvarchar(36), submission_key) AS submission_key,
                               submission_version, policy_version, lifecycle_epoch,
                               created_at_utc, updated_at_utc
                        FROM dbo.resume_intake_jobs
                        WHERE owner_profile_id = @ProfileId
                        FOR JSON PATH
                    )) AS jobs,
                    JSON_QUERY((
                        SELECT CONVERT(nvarchar(36), proposal_key) AS proposal_key, state, kind,
                               record_type, confidence,
                               CONVERT(nvarchar(36), target_key) AS target_key,
                               target_content_token, target_access_revision,
                               quote, span_start, span_end, proposed_values_json,
                               provided_fields_json, explicit_clears_json,
                               confirmed_values_json, requires_member_wording,
                               command_digest, source_purged, decision, decided_at_utc,
                               CONVERT(nvarchar(36), source_key) AS source_key, source_version,
                               CONVERT(nvarchar(36), submission_key) AS submission_key,
                               submission_version, lifecycle_epoch, policy_version,
                               created_at_utc
                        FROM dbo.resume_intake_proposals
                        WHERE owner_profile_id = @ProfileId
                        FOR JSON PATH
                    )) AS proposals,
                    JSON_QUERY((
                        SELECT CONVERT(nvarchar(36), request_id) AS request_id, request_digest,
                               service_digest,
                               CONVERT(nvarchar(36), submission_key) AS submission_key,
                               outcome, result_json
                        FROM dbo.resume_intake_command_receipts
                        WHERE owner_profile_id = @ProfileId
                        FOR JSON PATH
                    )) AS receipts
                FROM (SELECT 1 AS one) AS anchor
                LEFT JOIN dbo.resume_intake_owner_state AS state
                       ON state.owner_profile_id = @ProfileId
                FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
            ) AS workspace_json;
        END;
    ');

    -- Worker-only procedures. They take no browser request identity, run out of
    -- process under a separate worker identity, and are deliberately NOT in the
    -- application procedure allowlist.
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ClaimResumeIntakeJobsForOwner
            @UserKey nvarchar(300),
            @MaxJobs int
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
            BEGIN TRY
                BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;

            UPDATE TOP (@MaxJobs) dbo.resume_intake_jobs
            SET state = N''leased'', lease_id = NEWID(), attempts = attempts + 1, updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId AND state = N''queued'';

            SELECT job_key, kind, lease_id, source_key, source_version, submission_key,
                   submission_version, policy_version, lifecycle_epoch
            FROM dbo.resume_intake_jobs
            WHERE owner_profile_id = @ProfileId AND state = N''leased'';
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CompleteResumeIntakeJobForOwner
            @UserKey nvarchar(300),
            @JobKey uniqueidentifier,
            @LeaseId uniqueidentifier,
            @Result nvarchar(20),
            @OutcomeCode nvarchar(60)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
            BEGIN TRY
                BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
            IF @Result NOT IN (N''saved'', N''unresolved'', N''failed'', N''skipped'')
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            UPDATE dbo.resume_intake_jobs
            SET state = CASE WHEN @Result = N''failed'' THEN N''failed'' ELSE N''completed'' END,
                result = @Result, outcome_code = @OutcomeCode, lease_id = NULL,
                updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId
              AND job_key = @JobKey
              AND lease_id = @LeaseId
              AND state = N''leased''
              AND EXISTS (SELECT 1 FROM dbo.resume_intake_sources AS source
                          WHERE source.owner_profile_id = @ProfileId
                            AND source.source_key = dbo.resume_intake_jobs.source_key
                            AND source.state = N''active''
                            AND source.source_version = dbo.resume_intake_jobs.source_version)
              AND EXISTS (SELECT 1 FROM dbo.resume_intake_owner_state AS state
                          WHERE state.owner_profile_id = @ProfileId
                            AND state.lifecycle_epoch = dbo.resume_intake_jobs.lifecycle_epoch);

            IF @@ROWCOUNT = 0
            BEGIN
                UPDATE dbo.resume_intake_jobs
                SET state = N''stale'', lease_id = NULL, updated_at_utc = SYSUTCDATETIME()
                WHERE owner_profile_id = @ProfileId AND job_key = @JobKey AND state = N''leased'';
                THROW 52307, ''RESUME_INTAKE_STALE_JOB'', 1;
            END;

            SELECT CONVERT(bit, 1) AS completed;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SweepExpiredResumeIntakeSources
            @Entrance nvarchar(40),
            @InactivityDays int,
            @PolicySelected bit,
            @NowUtc datetime2(7)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
            BEGIN TRY
                BEGIN TRANSACTION;


            -- Retention is an entrance-specific promise. While an entrance''s
            -- policy is unselected this refuses rather than applying a
            -- universal timed sweep to everyone.
            IF @PolicySelected <> 1 THROW 52308, ''RESUME_INTAKE_POLICY_NOT_SELECTED'', 1;
            IF @Entrance NOT IN (N''resume_onboarding'', N''my_data'')
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;
            IF @InactivityDays IS NULL OR @InactivityDays <= 0
                THROW 52304, ''RESUME_INTAKE_VALIDATION'', 1;

            -- Retention keys on DRAFT ACTIVITY, not on how old a source is: an
            -- owner whose newest submitted work for this entrance is inside the
            -- inactivity window keeps every source. The candidates are scoped
            -- by owner, entrance and policy version.
            DECLARE @StaleOwners TABLE (owner_profile_id bigint NOT NULL PRIMARY KEY);
            INSERT @StaleOwners (owner_profile_id)
            SELECT source.owner_profile_id
            FROM dbo.resume_intake_sources AS source
            WHERE source.entrance = @Entrance
              AND source.state = N''active''
            GROUP BY source.owner_profile_id
            HAVING MAX(source.created_at_utc) < DATEADD(day, -@InactivityDays, @NowUtc)
               AND ISNULL((
                        SELECT MAX(submission.created_at_utc)
                        FROM dbo.resume_intake_submissions AS submission
                        WHERE submission.owner_profile_id = source.owner_profile_id
                          AND submission.entrance = @Entrance
                   ), CONVERT(datetime2(7), ''19000101'')) < DATEADD(day, -@InactivityDays, @NowUtc);

            UPDATE dbo.resume_intake_sources
            SET state = N''purged'', source_text = NULL, structured_values_json = NULL,
                purged_at_utc = @NowUtc, source_version = source_version + 1
            WHERE state = N''active''
              AND entrance = @Entrance
              AND owner_profile_id IN (SELECT owner_profile_id FROM @StaleOwners);

            UPDATE dbo.resume_intake_jobs
            SET state = N''stale'', lease_id = NULL, updated_at_utc = @NowUtc
            WHERE state IN (N''queued'', N''leased'')
              AND owner_profile_id IN (SELECT owner_profile_id FROM @StaleOwners)
              AND source_key IN (SELECT source_key FROM dbo.resume_intake_sources
                                 WHERE state = N''purged''
                                   AND entrance = @Entrance
                                   AND owner_profile_id IN (SELECT owner_profile_id FROM @StaleOwners));

            SELECT @@ROWCOUNT AS fenced_jobs;
                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-INTAKE-001')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description)
        VALUES (N'PS-RESUME-INTAKE-001', N'Proposed owner-scoped Resume composer intake and reviewed canonical intents');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
