/* ============================================================
   PS-INTERVIEW-AI-EXTRACT-001 - content-free Interview AI telemetry

   PROPOSAL ONLY. This file is registered and gate-provable but is never
   applied by the extraction slice itself; applying it is a separately
   authorized protected operation.

   Adds the slice-1 half of telemetry-contract@1 (architecture section 7,
   frozen in docs/initiatives/PS-INTERVIEW-AI-EXTRACT-001/
   01_FROZEN_CONTRACTS.md, hardened per correction B4): one append-only
   table for server_call rows, one allowlisted append procedure, one
   bounded 90-day purge procedure. The two database roles separating
   those paths are created by the administrator-run authority script
   (scripts/configure_interview_telemetry_sql_authority.py), not here.

   Correction B4 - SQL enforces the SAME closed contract as the Python
   sentinel; a trusted caller is never a substitute:

   * Numeric bounds: http_status 100-599; retry_ordinal 0-15; every
     duration 0-86,400,000 ms with total >= each stage (sum equality is
     NOT required); source counts 0-32; provider tokens 0-2,147,483,647;
     reply_chars 0-100,000; exception status_code 100-599; cost_microusd
     0-(2^63-1).
   * Source-count JSON: exactly the six source classes, each exactly
     once, every value a JSON integer 0-32 - missing, duplicate, and
     unknown keys are rejected even at six total entries; strings,
     floats, booleans, nulls, arrays, and objects are rejected.
   * Exception classes closed to nine values; the four validation classes
     may carry only provider_stop_reason (closed enum) and reply_chars;
     provider_rejected only status_code; every other class requires an
     empty attribute map. Duplicate keys, unknown keys, wrong-class
     attributes, wrong types, and out-of-range values are rejected.
   * Canonical identities: every nonnull SHA field must be exactly 64
     LOWERCASE hexadecimal characters (case-sensitive check).
   * Parent/child relationships are enforced transactionally in the
     procedure with locks, beyond the self-referencing foreign key: a
     Compare child must reference an existing composition_parent row with
     composition = compare and the SAME release identity; a child can
     never point at a standalone specialist or at another child; a parent
     carries no parent, bundle, tokens, cost, pricing, exception, or
     nonzero source counts; a resolved specialist row carries release AND
     bundle identity; the pre-resolution service_not_configured row
     carries neither.
   * Duplicate attempt_uuid appends are concurrency-safe silent no-ops
     that never mutate the first stored row, even when the duplicate
     carries a different payload.

   Once the authority script has run, the application identity holds
   EXECUTE on the append procedure only; the separately named maintenance
   identity holds EXECUTE on the purge procedure only; neither role has
   any direct table permission. There is
   no free-text column anywhere; raw SDK/Python class names, messages,
   tracebacks, URLs, bodies, headers, provider ids, member text, and
   model output are structurally unstorable.

   Dependency note: PS-PLAT-001 provides dbo.schema_migrations and
   dbo.usp_AppendAuditEvent.

   Rollback: PS-INTERVIEW-AI-EXTRACT-001_telemetry_rollback.sql
   (retention-safe: it refuses to drop a nonempty table - correction C9).
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.interview_ai_server_calls', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.interview_ai_server_calls
        (
            attempt_uuid            UNIQUEIDENTIFIER NOT NULL
                CONSTRAINT PK_interview_ai_server_calls PRIMARY KEY,
            event_type              VARCHAR(16) NOT NULL
                CONSTRAINT DF_iasc_event_type DEFAULT 'server_call',
            recorded_at             DATETIME2(3) NOT NULL
                CONSTRAINT DF_interview_ai_server_calls_recorded_at
                    DEFAULT SYSUTCDATETIME(),
            event_kind              VARCHAR(20) NOT NULL,
            outcome                 VARCHAR(16) NOT NULL,
            http_status             INT NOT NULL,
            retry_ordinal           INT NOT NULL,
            dur_receive_ms          BIGINT NOT NULL,
            dur_retrieval_ms        BIGINT NOT NULL,
            dur_manifest_ms         BIGINT NOT NULL,
            dur_provider_ms         BIGINT NOT NULL,
            dur_validate_ms         BIGINT NOT NULL,
            dur_respond_ms          BIGINT NOT NULL,
            dur_total_server_ms     BIGINT NOT NULL,
            specialist              VARCHAR(20) NULL,
            bundle_label            VARCHAR(40) NULL,
            bundle_content_sha256   CHAR(64) NULL,
            composition             VARCHAR(16) NULL,
            release_set_id          CHAR(64) NULL,
            parent_attempt_uuid     UNIQUEIDENTIFIER NULL
                CONSTRAINT FK_iasc_parent REFERENCES
                    dbo.interview_ai_server_calls (attempt_uuid),
            operation_id            UNIQUEIDENTIFIER NULL,
            failure_state           VARCHAR(32) NULL,
            failure_reason          VARCHAR(48) NULL,
            guardian_rejections     NVARCHAR(400) NOT NULL,
            validation_result       VARCHAR(16) NOT NULL,
            source_class_counts     NVARCHAR(400) NOT NULL,
            provider_input_tokens   INT NULL,
            provider_output_tokens  INT NULL,
            cost_microusd           BIGINT NULL,
            pricing_schedule_id     CHAR(64) NULL,
            exception_class         VARCHAR(40) NULL,
            exception_attrs         NVARCHAR(400) NULL,

            CONSTRAINT CK_iasc_event_type CHECK (event_type = 'server_call'),
            CONSTRAINT CK_iasc_event_kind CHECK
                (event_kind IN ('specialist_call', 'composition_parent')),
            CONSTRAINT CK_iasc_outcome CHECK
                (outcome IN ('success', 'computed_outcome', 'refused', 'failed')),
            /* Consolidated B4: 'refused' is the reserved later-slice value;
               no slice-1 runtime path emits it. */
            CONSTRAINT CK_iasc_outcome_reserved_slice1 CHECK
                (outcome <> 'refused'),
            CONSTRAINT CK_iasc_http_status CHECK
                (http_status BETWEEN 100 AND 599),
            CONSTRAINT CK_iasc_retry_ordinal CHECK
                (retry_ordinal BETWEEN 0 AND 15),
            CONSTRAINT CK_iasc_durations CHECK
                (dur_receive_ms BETWEEN 0 AND 86400000
                 AND dur_retrieval_ms BETWEEN 0 AND 86400000
                 AND dur_manifest_ms BETWEEN 0 AND 86400000
                 AND dur_provider_ms BETWEEN 0 AND 86400000
                 AND dur_validate_ms BETWEEN 0 AND 86400000
                 AND dur_respond_ms BETWEEN 0 AND 86400000
                 AND dur_total_server_ms BETWEEN 0 AND 86400000),
            CONSTRAINT CK_iasc_duration_total CHECK
                (dur_total_server_ms >= dur_receive_ms
                 AND dur_total_server_ms >= dur_retrieval_ms
                 AND dur_total_server_ms >= dur_manifest_ms
                 AND dur_total_server_ms >= dur_provider_ms
                 AND dur_total_server_ms >= dur_validate_ms
                 AND dur_total_server_ms >= dur_respond_ms),
            CONSTRAINT CK_iasc_specialist CHECK
                (specialist IS NULL OR specialist IN
                 ('coach', 'revision', 'grounded_example', 'generic_example',
                  'planning_hints')),
            CONSTRAINT CK_iasc_composition CHECK
                (composition IS NULL OR composition = 'compare'),
            CONSTRAINT CK_iasc_kind_shape CHECK
                ((event_kind = 'specialist_call' AND specialist IS NOT NULL
                  AND composition IS NULL)
                 OR (event_kind = 'composition_parent' AND specialist IS NULL
                     AND composition IS NOT NULL AND bundle_label IS NULL
                     AND bundle_content_sha256 IS NULL
                     AND provider_input_tokens IS NULL
                     AND provider_output_tokens IS NULL
                     AND cost_microusd IS NULL
                     AND pricing_schedule_id IS NULL
                     AND exception_class IS NULL
                     AND exception_attrs IS NULL
                     AND parent_attempt_uuid IS NULL)),
            CONSTRAINT CK_iasc_bundle_pair CHECK
                ((bundle_label IS NULL AND bundle_content_sha256 IS NULL)
                 OR (bundle_label IS NOT NULL
                     AND bundle_content_sha256 IS NOT NULL)),
            /* Correction C2 (runtime-compatible form): bundle_label is a
               canonical identity, not a text channel. The STORED label is
               <semver>+<sha8> - exactly what the runtime's release
               registry records - and the specialist remains its own
               column, so the validated COMBINED identity is
               specialist@bundle_label. The version is the frozen numeric
               major.minor.patch grammar and the eight-character suffix
               equals the first eight characters of this row's content
               hash (which CK_iasc_sha_bundle already pins to lowercase
               hex). Comparisons are Latin1_General_BIN2 so a re-cased
               label cannot slip through a case-insensitive default
               collation. There is deliberately no free-form fallback. */
            CONSTRAINT CK_iasc_bundle_label_canonical CHECK
                (bundle_label IS NULL
                 OR (specialist IS NOT NULL
                     AND bundle_content_sha256 IS NOT NULL
                     /* n.n.n + '+' + 8 hex = at least 14 characters. */
                     AND LEN(bundle_label) >= 14
                     AND RIGHT(bundle_label, 9)
                         COLLATE Latin1_General_BIN2
                         = ('+' + LEFT(bundle_content_sha256, 8))
                           COLLATE Latin1_General_BIN2
                     /* The version segment: digits and dots only, exactly
                        two dots, and no empty component. */
                     AND SUBSTRING(
                             bundle_label, 1, LEN(bundle_label) - 9
                         ) NOT LIKE '%[^0-9.]%'
                     AND LEN(SUBSTRING(
                             bundle_label, 1, LEN(bundle_label) - 9
                         ))
                       - LEN(REPLACE(SUBSTRING(
                             bundle_label, 1, LEN(bundle_label) - 9
                         ), '.', '')) = 2
                     AND SUBSTRING(
                             bundle_label, 1, LEN(bundle_label) - 9
                         ) NOT LIKE '.%'
                     AND SUBSTRING(
                             bundle_label, 1, LEN(bundle_label) - 9
                         ) NOT LIKE '%.'
                     AND SUBSTRING(
                             bundle_label, 1, LEN(bundle_label) - 9
                         ) NOT LIKE '%..%')),
            CONSTRAINT CK_iasc_specialist_resolution CHECK
                (event_kind <> 'specialist_call'
                 OR (bundle_content_sha256 IS NOT NULL
                     AND release_set_id IS NOT NULL)
                 OR (bundle_content_sha256 IS NULL
                     AND release_set_id IS NULL
                     AND outcome = 'failed'
                     AND failure_state = 'service_not_configured'
                     AND failure_reason = 'active_release_unresolved')),
            CONSTRAINT CK_iasc_sha_bundle CHECK
                (bundle_content_sha256 IS NULL
                 OR (LEN(bundle_content_sha256) = 64
                     AND bundle_content_sha256 COLLATE Latin1_General_BIN2
                         NOT LIKE '%[^0-9a-f]%' COLLATE Latin1_General_BIN2)),
            CONSTRAINT CK_iasc_sha_release CHECK
                (release_set_id IS NULL
                 OR (LEN(release_set_id) = 64
                     AND release_set_id COLLATE Latin1_General_BIN2
                         NOT LIKE '%[^0-9a-f]%' COLLATE Latin1_General_BIN2)),
            CONSTRAINT CK_iasc_sha_pricing CHECK
                (pricing_schedule_id IS NULL
                 OR (LEN(pricing_schedule_id) = 64
                     AND pricing_schedule_id COLLATE Latin1_General_BIN2
                         NOT LIKE '%[^0-9a-f]%' COLLATE Latin1_General_BIN2)),
            CONSTRAINT CK_iasc_failure_state CHECK
                ((outcome IN ('refused', 'failed')
                  AND failure_state IS NOT NULL)
                 OR (outcome IN ('success', 'computed_outcome')
                     AND failure_state IS NULL)),
            CONSTRAINT CK_iasc_failure_state_enum CHECK
                (failure_state IS NULL OR failure_state IN
                 ('invalid_output', 'provider_failure', 'internal_error',
                  'service_not_configured')),
            CONSTRAINT CK_iasc_failure_reason CHECK
                ((outcome = 'failed' AND failure_reason IS NOT NULL)
                 OR (outcome <> 'failed' AND failure_reason IS NULL)),
            CONSTRAINT CK_iasc_failure_reason_enum CHECK
                (failure_reason IS NULL OR failure_reason IN
                 ('no_json_object', 'not_an_object', 'wrong_field_type',
                  'empty_required_field', 'incomplete_dimensions',
                  'invalid_dimension_shape', 'invalid_dimension_status',
                  'duplicate_dimensions', 'numeric_universal_field',
                  'numeric_dimension_score', 'invalid_review_shape',
                  'duplicate_review_list_item',
                  'invalid_evidence_suggestion_shape',
                  'duplicate_evidence_suggestions', 'duplicate_json_field',
                  'opportunity_context_too_long', 'unauthorized_evidence',
                  'no_evidence_reference', 'duplicate_evidence',
                  'invalid_status', 'unparseable_json', 'unexpected_shape',
                  'unclassified',
                  'transport', 'timeout', 'rejected', 'abandoned',
                  'unexpected_server_fault', 'active_release_unresolved')),
            /* Consolidated B4: ONE closed state matrix — the same table
               the Python sentinel enforces. Semantically impossible
               state/reason pairs cannot be persisted. 'abandoned' is the
               reserved orphan-reaper value; no slice-1 path emits it. */
            CONSTRAINT CK_iasc_reason_reserved_slice1 CHECK
                (failure_reason IS NULL OR failure_reason <> 'abandoned'),
            CONSTRAINT CK_iasc_state_reason_matrix CHECK
                (failure_state IS NULL
                 OR (failure_state = 'provider_failure'
                     AND failure_reason IN ('transport', 'timeout', 'rejected'))
                 OR (failure_state = 'internal_error'
                     AND failure_reason = 'unexpected_server_fault')
                 OR (failure_state = 'service_not_configured'
                     AND failure_reason = 'active_release_unresolved')
                 OR (failure_state = 'invalid_output'
                     AND failure_reason NOT IN
                     ('transport', 'timeout', 'rejected', 'abandoned',
                      'unexpected_server_fault', 'active_release_unresolved'))),
            CONSTRAINT CK_iasc_state_validation_matrix CHECK
                ((event_kind = 'composition_parent'
                  AND validation_result = 'not_applicable')
                 OR (event_kind = 'specialist_call'
                     AND ((outcome IN ('success', 'computed_outcome')
                           AND validation_result = 'passed')
                          OR (outcome = 'failed'
                              AND failure_state = 'invalid_output'
                              AND validation_result = 'rejected')
                          OR (outcome = 'failed'
                              AND failure_state <> 'invalid_output'
                              AND validation_result = 'not_applicable')))),
            CONSTRAINT CK_iasc_state_exception_matrix CHECK
                (event_kind <> 'specialist_call'
                 OR (failure_state IS NULL AND exception_class IS NULL)
                 OR (failure_state = 'invalid_output'
                     AND exception_class IN
                     ('validation_json_decode', 'validation_value',
                      'validation_key', 'validation_type'))
                 OR (failure_state = 'provider_failure'
                     AND ((failure_reason = 'transport'
                           AND exception_class = 'provider_transport')
                          OR (failure_reason = 'timeout'
                              AND exception_class = 'provider_timeout')
                          OR (failure_reason = 'rejected'
                              AND exception_class = 'provider_rejected')))
                 OR (failure_state = 'internal_error'
                     AND exception_class IN
                     ('runtime_unexpected', 'provider_response_shape'))
                 OR (failure_state = 'service_not_configured'
                     AND exception_class IS NULL)),
            CONSTRAINT CK_iasc_release_state_matrix CHECK
                ((failure_state = 'service_not_configured'
                  AND release_set_id IS NULL)
                 OR (release_set_id IS NOT NULL
                     AND (failure_state IS NULL
                          OR failure_state <> 'service_not_configured'))),
            CONSTRAINT CK_iasc_usage_state_matrix CHECK
                (provider_input_tokens IS NULL
                 OR failure_state IS NULL
                 OR failure_state = 'invalid_output'
                 OR failure_state = 'internal_error'),
            CONSTRAINT CK_iasc_operation_id_slice1 CHECK
                (operation_id IS NULL),
            CONSTRAINT CK_iasc_validation_result CHECK
                (validation_result IN ('passed', 'rejected', 'not_applicable')),
            CONSTRAINT CK_iasc_guardian_json CHECK
                (ISJSON(guardian_rejections) = 1),
            CONSTRAINT CK_iasc_guardian_legacy_empty CHECK
                (guardian_rejections = N'[]'),
            CONSTRAINT CK_iasc_source_counts_json CHECK
                (ISJSON(source_class_counts) = 1),
            CONSTRAINT CK_iasc_usage_pair CHECK
                ((provider_input_tokens IS NULL
                  AND provider_output_tokens IS NULL)
                 OR (provider_input_tokens IS NOT NULL
                     AND provider_output_tokens IS NOT NULL
                     AND provider_input_tokens >= 0
                     AND provider_output_tokens >= 0)),
            CONSTRAINT CK_iasc_cost_pair CHECK
                ((cost_microusd IS NULL AND pricing_schedule_id IS NULL)
                 OR (cost_microusd IS NOT NULL AND cost_microusd >= 0
                     AND pricing_schedule_id IS NOT NULL
                     AND provider_input_tokens IS NOT NULL)),
            /* B4 item 3: class and attrs are null or non-null TOGETHER. */
            CONSTRAINT CK_iasc_exception CHECK
                ((exception_class IS NULL AND exception_attrs IS NULL)
                 OR (exception_class IS NOT NULL
                     AND exception_attrs IS NOT NULL
                     AND outcome = 'failed')),
            CONSTRAINT CK_iasc_exception_class_enum CHECK
                (exception_class IS NULL OR exception_class IN
                 ('validation_json_decode', 'validation_value',
                  'validation_key', 'validation_type',
                  'provider_timeout', 'provider_transport',
                  'provider_rejected', 'provider_response_shape',
                  'runtime_unexpected')),
            /* B4 item 4: attrs must be a JSON OBJECT — ISJSON alone also
               accepts arrays, so the leading brace is checked too. */
            CONSTRAINT CK_iasc_exception_attrs_json CHECK
                (exception_attrs IS NULL
                 OR (ISJSON(exception_attrs) = 1
                     AND LEFT(LTRIM(exception_attrs), 1) = '{'))
        );

        /* The purge deletes strictly by age; recorded_at is its key. */
        CREATE INDEX IX_interview_ai_server_calls_recorded_at
            ON dbo.interview_ai_server_calls (recorded_at);
    END;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_AppendInterviewAIServerCall
            @AttemptUuid            UNIQUEIDENTIFIER,
            @EventKind              VARCHAR(20),
            @Outcome                VARCHAR(16),
            @HttpStatus             INT,
            @RetryOrdinal           INT,
            @DurReceiveMs           BIGINT,
            @DurRetrievalMs         BIGINT,
            @DurManifestMs          BIGINT,
            @DurProviderMs          BIGINT,
            @DurValidateMs          BIGINT,
            @DurRespondMs           BIGINT,
            @DurTotalServerMs       BIGINT,
            @Specialist             VARCHAR(20)      = NULL,
            /* VARCHAR(80), not 40: an overlong label must arrive intact
               and be rejected by the explicit guard below, never silently
               truncated into a value that could pass the shape check
               (the same truncation-into-validity defence the identity
               parameters use). */
            @BundleLabel            VARCHAR(80)      = NULL,
            @BundleContentSha256    VARCHAR(80)        = NULL,
            @Composition            VARCHAR(16)      = NULL,
            @ReleaseSetId           VARCHAR(80)        = NULL,
            @ParentAttemptUuid      UNIQUEIDENTIFIER = NULL,
            @OperationId            UNIQUEIDENTIFIER = NULL,
            @FailureState           VARCHAR(32)      = NULL,
            @FailureReason          VARCHAR(48)      = NULL,
            @GuardianRejectionsJson NVARCHAR(400),
            @ValidationResult       VARCHAR(16),
            @SourceClassCountsJson  NVARCHAR(400),
            @ProviderInputTokens    INT              = NULL,
            @ProviderOutputTokens   INT              = NULL,
            @CostMicrousd           BIGINT           = NULL,
            @PricingScheduleId      VARCHAR(80)        = NULL,
            @ExceptionClass         VARCHAR(40)      = NULL,
            @ExceptionAttrsJson     NVARCHAR(400)    = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            /* B4 numeric bounds, enforced procedurally with named errors
               (the table constraints repeat them declaratively). */
            IF @HttpStatus NOT BETWEEN 100 AND 599
                THROW 50020, N''http_status must be 100-599.'', 1;
            IF @RetryOrdinal NOT BETWEEN 0 AND 15
                THROW 50021, N''retry_ordinal must be 0-15.'', 1;
            IF @DurReceiveMs  NOT BETWEEN 0 AND 86400000
               OR @DurRetrievalMs NOT BETWEEN 0 AND 86400000
               OR @DurManifestMs  NOT BETWEEN 0 AND 86400000
               OR @DurProviderMs  NOT BETWEEN 0 AND 86400000
               OR @DurValidateMs  NOT BETWEEN 0 AND 86400000
               OR @DurRespondMs   NOT BETWEEN 0 AND 86400000
               OR @DurTotalServerMs NOT BETWEEN 0 AND 86400000
                THROW 50022, N''durations must be 0-86400000 ms.'', 1;
            IF @DurTotalServerMs < @DurReceiveMs
               OR @DurTotalServerMs < @DurRetrievalMs
               OR @DurTotalServerMs < @DurManifestMs
               OR @DurTotalServerMs < @DurProviderMs
               OR @DurTotalServerMs < @DurValidateMs
               OR @DurTotalServerMs < @DurRespondMs
                THROW 50023, N''total duration must cover every stage.'', 1;
            IF (@ProviderInputTokens IS NOT NULL AND @ProviderInputTokens < 0)
               OR (@ProviderOutputTokens IS NOT NULL AND @ProviderOutputTokens < 0)
                THROW 50024, N''provider tokens must be non-negative.'', 1;
            IF @CostMicrousd IS NOT NULL AND @CostMicrousd < 0
                THROW 50025, N''cost_microusd must be non-negative.'', 1;

            /* Canonical identities: exactly 64 LOWERCASE hex characters. */
            IF @BundleContentSha256 IS NOT NULL AND
               (LEN(@BundleContentSha256) <> 64
                OR @BundleContentSha256 COLLATE Latin1_General_BIN2
                   LIKE ''%[^0-9a-f]%'' COLLATE Latin1_General_BIN2)
                THROW 50026, N''bundle_content_sha256 must be 64 lowercase hex characters.'', 1;
            IF @ReleaseSetId IS NOT NULL AND
               (LEN(@ReleaseSetId) <> 64
                OR @ReleaseSetId COLLATE Latin1_General_BIN2
                   LIKE ''%[^0-9a-f]%'' COLLATE Latin1_General_BIN2)
                THROW 50027, N''release_set_id must be 64 lowercase hex characters.'', 1;
            IF @PricingScheduleId IS NOT NULL AND
               (LEN(@PricingScheduleId) <> 64
                OR @PricingScheduleId COLLATE Latin1_General_BIN2
                   LIKE ''%[^0-9a-f]%'' COLLATE Latin1_General_BIN2)
                THROW 50028, N''pricing_schedule_id must be 64 lowercase hex characters.'', 1;

            /* Correction C2 (runtime-compatible form): bundle_label
               carries no free text. The stored label is <semver>+<sha8>
               and the specialist stays in its own parameter, so the
               validated COMBINED identity is specialist@bundle_label:
               both halves must be present, the version is numeric
               major.minor.patch, and the suffix equals the first eight
               characters of @BundleContentSha256. All comparisons are
               Latin1_General_BIN2, so case games are rejected. */
            IF @BundleLabel IS NOT NULL
            BEGIN
                IF @Specialist IS NULL OR @BundleContentSha256 IS NULL
                    THROW 50050, N''bundle_label requires its specialist and content hash.'', 1;
                IF LEN(@BundleLabel) > 40 OR LEN(@BundleLabel) < 14
                    THROW 50051, N''bundle_label must be <semver>+<sha8>.'', 1;
                IF RIGHT(@BundleLabel, 9) COLLATE Latin1_General_BIN2
                   <> (''+'' + LEFT(@BundleContentSha256, 8))
                      COLLATE Latin1_General_BIN2
                    THROW 50053, N''bundle_label suffix must be the first eight characters of bundle_content_sha256.'', 1;
                DECLARE @LabelVersion VARCHAR(40) =
                    SUBSTRING(@BundleLabel, 1, LEN(@BundleLabel) - 9);
                IF @LabelVersion LIKE ''%[^0-9.]%''
                   OR LEN(@LabelVersion) - LEN(REPLACE(@LabelVersion, ''.'', '''')) <> 2
                   OR @LabelVersion LIKE ''.%''
                   OR @LabelVersion LIKE ''%.''
                   OR @LabelVersion LIKE ''%..%''
                    THROW 50054, N''bundle_label version must be numeric major.minor.patch.'', 1;
            END;

            /* Guardian list is pinned empty under guardian-runtime-legacy@1. */
            IF @GuardianRejectionsJson <> N''[]''
                THROW 50010, N''guardian_rejections must be the empty list under guardian-runtime-legacy@1.'', 1;

            /* Source-count shape closure: exactly the six classes, each
               exactly once, every value a JSON integer 0-32. */
            IF ISJSON(@SourceClassCountsJson) <> 1
                THROW 50011, N''source_class_counts must be a JSON object.'', 1;
            IF (SELECT COUNT(*) FROM OPENJSON(@SourceClassCountsJson)) <> 6
               OR (SELECT COUNT(DISTINCT [key])
                   FROM OPENJSON(@SourceClassCountsJson)) <> 6
                THROW 50012, N''source_class_counts must carry exactly the six source classes exactly once.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM OPENJSON(@SourceClassCountsJson)
                WHERE [key] NOT IN
                      (''question'', ''answer'', ''role_context'',
                       ''member_evidence'', ''history_selection'',
                       ''confirmed_context'')
                   OR [type] <> 2
                   OR TRY_CAST([value] AS INT) IS NULL
                   OR TRY_CAST([value] AS INT) < 0
                   OR TRY_CAST([value] AS INT) > 32
            )
                THROW 50013, N''source_class_counts keys, types, or bounds are outside the allowlist.'', 1;

            /* Composition parents carry no counts, usage, cost, pricing,
               exception, bundle, or parent - and all-zero source counts. */
            IF @EventKind = ''composition_parent'' AND EXISTS
            (
                SELECT 1 FROM OPENJSON(@SourceClassCountsJson)
                WHERE TRY_CAST([value] AS INT) <> 0
            )
                THROW 50029, N''a composition parent carries all-zero source counts.'', 1;

            /* Exception classes are closed to nine values with per-class
               attribute allowlists (B4). */
            IF @ExceptionClass IS NOT NULL AND @ExceptionClass NOT IN
               (''validation_json_decode'', ''validation_value'',
                ''validation_key'', ''validation_type'',
                ''provider_timeout'', ''provider_transport'',
                ''provider_rejected'', ''provider_response_shape'',
                ''runtime_unexpected'')
                THROW 50030, N''exception_class is outside the closed enum.'', 1;

            /* Consolidated B4 item 3: class and attrs travel together. */
            IF (@ExceptionClass IS NULL AND @ExceptionAttrsJson IS NOT NULL)
               OR (@ExceptionClass IS NOT NULL AND @ExceptionAttrsJson IS NULL)
                THROW 50045, N''exception class and attrs must be null or non-null together.'', 1;

            IF @ExceptionAttrsJson IS NOT NULL
            BEGIN
                /* B4 item 4: a JSON OBJECT, never an array or scalar —
                   ISJSON alone also accepts arrays. */
                IF ISJSON(@ExceptionAttrsJson) <> 1
                   OR LEFT(LTRIM(@ExceptionAttrsJson), 1) <> ''{''
                    THROW 50014, N''exception_attrs must be a JSON object.'', 1;
                IF (SELECT COUNT(*) FROM OPENJSON(@ExceptionAttrsJson))
                   <> (SELECT COUNT(DISTINCT [key])
                       FROM OPENJSON(@ExceptionAttrsJson))
                    THROW 50031, N''exception_attrs carries a duplicate key.'', 1;
                IF @ExceptionClass IN
                   (''validation_json_decode'', ''validation_value'',
                    ''validation_key'', ''validation_type'')
                BEGIN
                    IF EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] NOT IN
                              (''provider_stop_reason'', ''reply_chars'')
                    )
                        THROW 50015, N''exception_attrs carries a key outside the allowlist for this class.'', 1;
                    /* Consolidated B4: both attributes are REQUIRED for a
                       validation class, not merely permitted. */
                    IF NOT EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] = ''provider_stop_reason''
                    )
                       OR NOT EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] = ''reply_chars''
                    )
                        THROW 50049, N''a validation exception requires both provider_stop_reason and reply_chars.'', 1;
                    IF EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] = ''provider_stop_reason''
                          AND ([type] <> 1 OR [value] NOT IN
                               (''end_turn'', ''max_tokens'', ''stop_sequence'',
                                ''tool_use'', ''pause_turn'', ''refusal'',
                                ''unknown''))
                    )
                        THROW 50018, N''provider_stop_reason is outside the closed enum.'', 1;
                    IF EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] = ''reply_chars''
                          AND ([type] <> 2
                               OR TRY_CAST([value] AS INT) IS NULL
                               OR TRY_CAST([value] AS INT) < 0
                               OR TRY_CAST([value] AS INT) > 100000)
                    )
                        THROW 50017, N''reply_chars must be an integer 0-100000.'', 1;
                END
                ELSE IF @ExceptionClass = ''provider_rejected''
                BEGIN
                    IF EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] <> ''status_code''
                    )
                        THROW 50015, N''exception_attrs carries a key outside the allowlist for this class.'', 1;
                    IF EXISTS
                    (
                        SELECT 1 FROM OPENJSON(@ExceptionAttrsJson)
                        WHERE [key] = ''status_code''
                          AND ([type] <> 2
                               OR TRY_CAST([value] AS INT) IS NULL
                               OR TRY_CAST([value] AS INT) < 100
                               OR TRY_CAST([value] AS INT) > 599)
                    )
                        THROW 50016, N''exception status_code must be an integer 100-599.'', 1;
                END
                ELSE
                BEGIN
                    IF EXISTS (SELECT 1 FROM OPENJSON(@ExceptionAttrsJson))
                        THROW 50032, N''this exception class requires an empty attribute map.'', 1;
                END;
            END;

            /* Consolidated B4: the ONE closed state matrix, enforced with
               named errors exactly as telemetry.validate_event enforces it
               (the table constraints repeat it declaratively). */
            IF @Outcome = ''refused''
                THROW 50040, N''outcome refused is reserved for a later slice.'', 1;
            IF @FailureReason = ''abandoned''
                THROW 50041, N''failure_reason abandoned is reserved for a later slice.'', 1;
            IF @Outcome = ''failed''
            BEGIN
                IF @FailureState IS NULL OR @FailureReason IS NULL
                    THROW 50042, N''a failed row names its failure_state and failure_reason.'', 1;
                IF (@FailureState = ''provider_failure''
                    AND @FailureReason NOT IN (''transport'', ''timeout'', ''rejected''))
                   OR (@FailureState = ''internal_error''
                       AND @FailureReason <> ''unexpected_server_fault'')
                   OR (@FailureState = ''service_not_configured''
                       AND @FailureReason <> ''active_release_unresolved'')
                   OR (@FailureState = ''invalid_output''
                       AND @FailureReason IN
                       (''transport'', ''timeout'', ''rejected'', ''abandoned'',
                        ''unexpected_server_fault'', ''active_release_unresolved''))
                    THROW 50042, N''failure_reason is impossible under this failure_state.'', 1;
                IF (@EventKind = ''composition_parent''
                    AND @ValidationResult <> ''not_applicable'')
                   OR (@EventKind = ''specialist_call''
                       AND @FailureState = ''invalid_output''
                       AND @ValidationResult <> ''rejected'')
                   OR (@EventKind = ''specialist_call''
                       AND @FailureState <> ''invalid_output''
                       AND @ValidationResult <> ''not_applicable'')
                    THROW 50043, N''validation_result is impossible under this failure_state.'', 1;
                IF @EventKind = ''specialist_call''
                BEGIN
                    IF (@FailureState = ''invalid_output''
                        AND (@ExceptionClass IS NULL OR @ExceptionClass NOT IN
                             (''validation_json_decode'', ''validation_value'',
                              ''validation_key'', ''validation_type'')))
                       OR (@FailureState = ''provider_failure''
                           AND (@ExceptionClass IS NULL
                                OR @ExceptionClass <> CASE @FailureReason
                                       WHEN ''transport'' THEN ''provider_transport''
                                       WHEN ''timeout''   THEN ''provider_timeout''
                                       WHEN ''rejected''  THEN ''provider_rejected''
                                   END))
                       OR (@FailureState = ''internal_error''
                           AND (@ExceptionClass IS NULL OR @ExceptionClass NOT IN
                                (''runtime_unexpected'', ''provider_response_shape'')))
                       OR (@FailureState = ''service_not_configured''
                           AND @ExceptionClass IS NOT NULL)
                        THROW 50044, N''exception class is impossible under this failure_state.'', 1;
                END;
                IF (@FailureState = ''service_not_configured''
                    AND @ReleaseSetId IS NOT NULL)
                   OR (@FailureState <> ''service_not_configured''
                       AND @ReleaseSetId IS NULL)
                    THROW 50047, N''release identity nullability is fixed by the failure_state.'', 1;
                IF @FailureState IN (''provider_failure'', ''service_not_configured'')
                   AND (@ProviderInputTokens IS NOT NULL
                        OR @ProviderOutputTokens IS NOT NULL)
                    THROW 50048, N''provider usage is impossible under this failure_state.'', 1;
            END
            ELSE
            BEGIN
                IF @FailureState IS NOT NULL OR @FailureReason IS NOT NULL
                    THROW 50042, N''failure fields must be null on a non-failed row.'', 1;
                IF @ExceptionClass IS NOT NULL
                    THROW 50044, N''exception requires a failed outcome.'', 1;
                IF @ReleaseSetId IS NULL
                    THROW 50047, N''a non-failed row always carries release identity.'', 1;
                IF (@EventKind = ''specialist_call''
                    AND @ValidationResult <> ''passed'')
                   OR (@EventKind = ''composition_parent''
                       AND @ValidationResult <> ''not_applicable'')
                    THROW 50043, N''validation_result is impossible on this non-failed row.'', 1;
            END;

            /* Written once by the server at response time; at most one row
               per attempt, and the parent/child relationship is validated
               transactionally under locks so a standalone row, another
               child, a mismatched-release parent, or a race can never
               satisfy it. */
            BEGIN TRY
                BEGIN TRANSACTION;

                IF EXISTS (SELECT 1 FROM dbo.interview_ai_server_calls
                             WITH (UPDLOCK, HOLDLOCK)
                           WHERE attempt_uuid = @AttemptUuid)
                BEGIN
                    /* Concurrency-safe duplicate: silent no-op; the first
                       stored row is never mutated. */
                    COMMIT TRANSACTION;
                    RETURN;
                END;

                IF @ParentAttemptUuid IS NOT NULL
                BEGIN
                    DECLARE @ParentKind VARCHAR(20), @ParentComposition VARCHAR(16),
                            @ParentRelease CHAR(64);
                    SELECT @ParentKind = event_kind,
                           @ParentComposition = composition,
                           @ParentRelease = release_set_id
                    FROM dbo.interview_ai_server_calls
                        WITH (UPDLOCK, HOLDLOCK)
                    WHERE attempt_uuid = @ParentAttemptUuid;
                    IF @ParentKind IS NULL
                        THROW 50033, N''a Compare child must reference an existing parent row.'', 1;
                    IF @ParentKind <> ''composition_parent''
                       OR @ParentComposition <> ''compare''
                        THROW 50034, N''a Compare child must reference a composition_parent row with composition = compare.'', 1;
                    IF @ParentRelease IS NULL OR @ReleaseSetId IS NULL
                       OR @ParentRelease <> @ReleaseSetId
                        THROW 50035, N''parent and child must carry the same release identity.'', 1;
                END;

                INSERT dbo.interview_ai_server_calls
                (
                    attempt_uuid, event_kind, outcome, http_status,
                    retry_ordinal, dur_receive_ms, dur_retrieval_ms,
                    dur_manifest_ms, dur_provider_ms, dur_validate_ms,
                    dur_respond_ms, dur_total_server_ms, specialist,
                    bundle_label, bundle_content_sha256, composition,
                    release_set_id, parent_attempt_uuid, operation_id,
                    failure_state, failure_reason, guardian_rejections,
                    validation_result, source_class_counts,
                    provider_input_tokens, provider_output_tokens,
                    cost_microusd, pricing_schedule_id, exception_class,
                    exception_attrs
                )
                VALUES
                (
                    @AttemptUuid, @EventKind, @Outcome, @HttpStatus,
                    @RetryOrdinal, @DurReceiveMs, @DurRetrievalMs,
                    @DurManifestMs, @DurProviderMs, @DurValidateMs,
                    @DurRespondMs, @DurTotalServerMs, @Specialist,
                    @BundleLabel, @BundleContentSha256, @Composition,
                    @ReleaseSetId, @ParentAttemptUuid, @OperationId,
                    @FailureState, @FailureReason, @GuardianRejectionsJson,
                    @ValidationResult, @SourceClassCountsJson,
                    @ProviderInputTokens, @ProviderOutputTokens,
                    @CostMicrousd, @PricingScheduleId, @ExceptionClass,
                    @ExceptionAttrsJson
                );

                COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                IF ERROR_NUMBER() IN (2627, 2601)
                    RETURN;  /* racing duplicate: silent no-op */
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeInterviewAIServerCalls
            @BatchSize  INT = 1000,
            @MaxBatches INT = 10
        AS
        BEGIN
            SET NOCOUNT ON;

            /* Retention is exactly 90 days, enforced in bounded deletion
               batches so the purge can never monopolize the database. The
               procedure returns row counts only. Batch size is bounded
               1..5000 (frozen contract, correction C3). */
            IF @BatchSize IS NULL OR @BatchSize < 1 OR @BatchSize > 5000
                THROW 50001, N''Purge batch size must be between 1 and 5000.'', 1;
            IF @MaxBatches IS NULL OR @MaxBatches < 1 OR @MaxBatches > 1000
                THROW 50002, N''Purge batch count must be between 1 and 1000.'', 1;

            DECLARE @Cutoff DATETIME2(3) =
                DATEADD(DAY, -90, SYSUTCDATETIME());
            DECLARE @TotalDeleted BIGINT = 0;
            DECLARE @Batch INT = 0;
            DECLARE @Deleted INT = 1;

            WHILE @Batch < @MaxBatches AND @Deleted > 0
            BEGIN
                /* Children reference parents, so aged rows delete
                   children-first inside one batch predicate. */
                DELETE TOP (@BatchSize)
                FROM dbo.interview_ai_server_calls
                WHERE recorded_at < @Cutoff
                  AND (parent_attempt_uuid IS NOT NULL
                       OR NOT EXISTS
                          (SELECT 1 FROM dbo.interview_ai_server_calls AS child
                           WHERE child.parent_attempt_uuid =
                                 dbo.interview_ai_server_calls.attempt_uuid));
                SET @Deleted = @@ROWCOUNT;
                SET @TotalDeleted = @TotalDeleted + @Deleted;
                SET @Batch = @Batch + 1;
            END;

            SELECT
                deleted_rows   = @TotalDeleted,
                batches_run    = @Batch,
                batch_size     = @BatchSize,
                more_remaining = CASE WHEN EXISTS
                    (SELECT 1 FROM dbo.interview_ai_server_calls
                     WHERE recorded_at < @Cutoff) THEN 1 ELSE 0 END;
        END;
    ');

    /* Two roles, two paths, no shared identity - but NOT created here.
       The governed apply identity (peerslate-ado-schema) holds
       db_ddladmin only: it can create tables and procedures and cannot
       create database roles or grant execute permission. Run 1419
       (2026-08-22) proved this transactionally - the statement block
       that used to live here was refused and nothing was written.
       Following the house pattern already used for Community
       maintenance, security-principal work is a separate protected
       authorization operation run by an administrator:
         scripts/configure_interview_telemetry_sql_authority.py
       creates interview_telemetry_append (execute on the append
       procedure only; member: the application identity) and
       interview_telemetry_maintenance (execute on the purge procedure
       only; member: the separately named Interview maintenance
       identity, never the Community one). Neither role receives any
       direct table permission. This migration carries schema only. */

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-INTERVIEW-AI-EXTRACT-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-INTERVIEW-AI-EXTRACT-001',
            N'Content-free Interview AI server_call telemetry: one append-only table with enum, bound, null-pairing, and JSON shape-closure enforcement, one allowlisted concurrency-safe append procedure with transactional parent/child validation, one bounded 90-day purge procedure. Schema only: the two execute-only roles separating the append and purge paths are bound by the administrator-run authority script.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-INTERVIEW-AI-EXTRACT-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
