/* ============================================================
   PS-ASK-PETE-DIRECT-001 - private recruiter question inbox

   Adds the storage half of the Ask Pete direct-question path: one
   dbo.recruiter_questions row per question a visitor chose to send
   privately to one PeerSlate member, plus a
   dbo.recruiter_question_save_requests idempotency ledger in the exact
   knowledge_item_save_requests shape (PS-WORKSHOP-001) so a double
   submit can never create a second question.

   Owner decision, 2026-08-08 (Pete's standing full approval for the
   remaining packages, recorded in docs/governance/CURRENT_LANES.json for
   PS-ASK-PETE-DIRECT-001): build the private recruiter-question path
   dark. The retention defaults quoted to the sender (archive at 90 days,
   remove at 180) are conservative drafts Pete revises before the feature
   flag is ever turned on.

   What this file deliberately does NOT contain:

   * No hard delete. Removal is archive-only in v1, so no destructive
     operation gate is triggered and no procedure here executes a DELETE
     against either new table. The 180-day removal half of the retention
     policy is NOT implemented by this migration; it is a separate,
     independently scheduled maintenance leg (the
     usp_PurgeCommunityContent pattern), and the package README records
     that the consent copy's retention sentence and that leg must be
     reconciled before the flag turns on.
   * No AI, no proposal, and no knowledge write. A question stored here
     never becomes Ask Pete grounding; the two stores share no table,
     column, or procedure.
   * No publication. There is no public read procedure, no visibility
     column that could widen, and no public predicate anywhere below.
   * No sender identity. The submitter is anonymous by design: the only
     personal data stored is exactly the text the sender typed into the
     bounded contact field, and consent to store it is required by the
     procedure itself rather than by the caller.

   Ownership model. dbo.recruiter_questions.owner_profile_id is the
   member the question was addressed to - never the sender. Every
   procedure below resolves its own @UserKey/@OwnerUserKey to that
   profile id and re-asserts owner_profile_id on every predicate, exactly
   as the PS-WORKSHOP-001 procedures do; none of them accepts an owner id
   from the caller. That keeps the store reusable for any member rather
   than special-casing one person.

   Dependency note: PS-PLAT-001 provides the migration ledger and
   usp_AppendAuditEvent, PS-PLAT-002 provides member_profiles, and
   PS-AUTH-001 provides app_users.user_key, which every procedure below
   resolves against - the same three guards PS-WORKSHOP-001 carries for
   the identical reason.

   Rollback: PS-ASK-PETE-DIRECT-001_recruiter_questions_rollback.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53950, 'The PeerSlate migration ledger is missing.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-001')
        THROW 53951, 'PS-PLAT-001 must be applied before PS-ASK-PETE-DIRECT-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-002')
        THROW 53952, 'PS-PLAT-002 must be applied before PS-ASK-PETE-DIRECT-001.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 53953, 'PS-AUTH-001 must be applied before PS-ASK-PETE-DIRECT-001.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
       OR OBJECT_ID(N'dbo.usp_AppendAuditEvent', N'P') IS NULL
        THROW 53954, 'The owner, profile, or audit foundation is missing.', 1;

    IF OBJECT_ID(N'dbo.recruiter_questions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.recruiter_questions
        (
            recruiter_question_id bigint IDENTITY(1,1) NOT NULL,
            /* NEWID(), not NEWSEQUENTIALID(). knowledge_items can use a
               sequential key because only its own signed-in owner ever
               writes one. Every row here is created by an anonymous
               request, so an unpredictable external key is worth more
               than index locality - and this column is a UNIQUE
               constraint, not the clustered key, so there is no page-split
               cost to pay for it. */
            recruiter_question_key uniqueidentifier NOT NULL
                CONSTRAINT DF_recruiter_questions_key DEFAULT NEWID(),
            /* The member the question was ADDRESSED TO. Never the sender:
               the sender is anonymous and is never resolved, stored, or
               joined to an account anywhere in this file. */
            owner_profile_id bigint NOT NULL,
            question_text nvarchar(2000) NOT NULL,
            /* Optional, and entirely the sender's choice: whatever they
               typed so the member can reply off-platform. No structure is
               imposed or parsed, because guessing at "name" vs "email" vs
               "company" would invent personal data the sender did not
               agree to give. */
            contact_text nvarchar(300) NULL,
            /* Which consent wording the sender actually agreed to. Stamped
               by the procedure's caller from a server-side constant, never
               from the submitted payload. */
            consent_version nvarchar(60) NOT NULL,
            question_status nvarchar(20) NOT NULL
                CONSTRAINT DF_recruiter_questions_status DEFAULT N'new',
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_recruiter_questions_created DEFAULT SYSUTCDATETIME(),
            status_changed_at_utc datetime2(7) NULL,
            status_changed_by_user_id int NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_recruiter_questions PRIMARY KEY (recruiter_question_id),
            CONSTRAINT UQ_recruiter_questions_key UNIQUE (recruiter_question_key),
            CONSTRAINT UQ_recruiter_questions_id_owner
                UNIQUE (recruiter_question_id, owner_profile_id),
            CONSTRAINT FK_recruiter_questions_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_recruiter_questions_status_actor FOREIGN KEY (status_changed_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_recruiter_questions_status CHECK
                (question_status IN (N'new', N'read', N'archived')),
            /* UTF-16 code-unit bounds (DATALENGTH/2), the moment_versions /
               knowledge_item_versions idiom, mirrored app-side by
               services/ask_pete_direct_service.py's utf16_length checks so a
               malformed request is refused before any database round trip. */
            CONSTRAINT CK_recruiter_questions_question_length CHECK
                (DATALENGTH(question_text) / 2 BETWEEN 1 AND 2000),
            CONSTRAINT CK_recruiter_questions_contact_length CHECK
                (contact_text IS NULL OR DATALENGTH(contact_text) / 2 BETWEEN 1 AND 300),
            CONSTRAINT CK_recruiter_questions_consent_version_length CHECK
                (DATALENGTH(consent_version) / 2 BETWEEN 1 AND 60),
            /* Who last changed the status, and when, travel together or not
               at all. Deliberately independent of the status VALUE so a
               member can move a question back to new (unread) without the
               store forgetting that a change happened - and so no status
               transition is one-way. */
            CONSTRAINT CK_recruiter_questions_status_change_pair CHECK
            (
                (status_changed_at_utc IS NULL AND status_changed_by_user_id IS NULL)
                OR
                (status_changed_at_utc IS NOT NULL AND status_changed_by_user_id IS NOT NULL)
            )
        );

        CREATE INDEX IX_recruiter_questions_owner_created
            ON dbo.recruiter_questions(owner_profile_id, created_at_utc DESC, recruiter_question_id DESC)
            INCLUDE (recruiter_question_key, question_status, status_changed_at_utc);
    END;

    /* Idempotency ledger in the exact knowledge_item_save_requests shape
       (PS-WORKSHOP-001, itself the moment_save_requests shape): a replay
       key and the resulting question reference only - no question text, no
       contact text, no sender fingerprint of any kind. */
    IF OBJECT_ID(N'dbo.recruiter_question_save_requests', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.recruiter_question_save_requests
        (
            recruiter_question_save_request_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            idempotency_key nvarchar(200) NOT NULL,
            recruiter_question_id bigint NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_recruiter_question_save_requests_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_recruiter_question_save_requests
                PRIMARY KEY (recruiter_question_save_request_id),
            CONSTRAINT UQ_recruiter_question_save_requests_owner_key
                UNIQUE (owner_profile_id, idempotency_key),
            CONSTRAINT FK_recruiter_question_save_requests_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_recruiter_question_save_requests_question
                FOREIGN KEY (recruiter_question_id, owner_profile_id)
                REFERENCES dbo.recruiter_questions(recruiter_question_id, owner_profile_id)
        );

        CREATE INDEX IX_recruiter_question_save_requests_question
            ON dbo.recruiter_question_save_requests(recruiter_question_id);
    END;

    IF COL_LENGTH(N'dbo.recruiter_questions', N'row_version') IS NULL
       OR COL_LENGTH(N'dbo.recruiter_questions', N'consent_version') IS NULL
       OR COL_LENGTH(N'dbo.recruiter_question_save_requests', N'idempotency_key') IS NULL
        THROW 53955, 'Existing recruiter question tables are incompatible.', 1;

    /* ------------------------------------------------------------
       Stored procedures. Application access goes ONLY through these
       (services/database_service.py's allowlist pattern). Each one
       resolves its own owner key to @ProfileId and re-asserts
       owner_profile_id on every predicate; none accepts an owner id
       from the caller, and none executes a DELETE.
       ------------------------------------------------------------ */

    /* The public-side write. It is the ONE procedure in this file whose
       caller is not the owner, so it is also the one that must not leak:
       it returns an outcome word and nothing else. In particular it never
       returns the recruiter_question_key, so a caller replaying somebody
       else's idempotency key learns only that the key was used - not the
       identifier, text, or contact details of the question behind it. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SubmitRecruiterQuestion
            @OwnerUserKey nvarchar(300),
            /* Widened past the 200-unit ledger column deliberately (the
               PS-WORKSHOP-001 MINOR 11 correction): a parameter declared at
               the column width would silently TRUNCATE an over-length key
               before the guard below could observe and reject it. */
            @IdempotencyKey nvarchar(4000),
            @QuestionText nvarchar(max),
            @ContactText nvarchar(max),
            @ConsentVersion nvarchar(60),
            @ConsentGiven bit
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @OwnerUserKey = NULLIF(LTRIM(RTRIM(@OwnerUserKey)), N'''');
            SET @IdempotencyKey = NULLIF(LTRIM(RTRIM(@IdempotencyKey)), N'''');
            SET @QuestionText = NULLIF(LTRIM(RTRIM(@QuestionText)), N'''');
            SET @ContactText = NULLIF(LTRIM(RTRIM(@ContactText)), N'''');
            SET @ConsentVersion = NULLIF(LTRIM(RTRIM(@ConsentVersion)), N'''');

            IF @OwnerUserKey IS NULL OR @IdempotencyKey IS NULL
                THROW 53956, ''Recipient and idempotency key are required.'', 1;
            IF DATALENGTH(@IdempotencyKey) / 2 > 200
                THROW 53957, ''Idempotency key exceeds its limit.'', 1;
            /* Consent is enforced here, not only at the route. Storage
               without an explicit yes is impossible even for a caller that
               skipped every layer above this one. */
            IF @ConsentGiven IS NULL OR @ConsentGiven <> 1
                THROW 53958, ''Consent is required before a question can be stored.'', 1;
            IF @QuestionText IS NULL
                THROW 53959, ''A question is required.'', 1;
            IF DATALENGTH(@QuestionText) / 2 > 2000
                THROW 53960, ''The question exceeds its limit.'', 1;
            IF @ContactText IS NOT NULL AND DATALENGTH(@ContactText) / 2 > 300
                THROW 53961, ''The contact details exceed their limit.'', 1;
            /* The consent version is concatenated into audit metadata JSON
               below, so it is constrained to an identifier charset here as
               well as bounded - a quote or backslash arriving from a future
               caller would otherwise produce malformed metadata. */
            IF @ConsentVersion IS NULL
               OR DATALENGTH(@ConsentVersion) / 2 > 60
               OR PATINDEX(N''%[^a-zA-Z0-9._-]%'', @ConsentVersion) > 0
                THROW 53962, ''A consent version is required.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

                DECLARE @ProfileId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @OwnerUserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

                IF @ProfileId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found'' AS outcome;
                    RETURN;
                END;

                /* Idempotent replay: a repeated key for this recipient
                   always resolves to the SAME question and never creates a
                   second one. The range lock on the unique (owner, key)
                   index serializes concurrent replays of one key. */
                DECLARE @ExistingQuestionId bigint;
                SELECT @ExistingQuestionId = request.recruiter_question_id
                FROM dbo.recruiter_question_save_requests AS request
                     WITH (UPDLOCK, HOLDLOCK, INDEX(UQ_recruiter_question_save_requests_owner_key))
                WHERE request.owner_profile_id = @ProfileId
                  AND request.idempotency_key = @IdempotencyKey;

                IF @ExistingQuestionId IS NOT NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''existing'' AS outcome;
                    RETURN;
                END;

                INSERT dbo.recruiter_questions
                (
                    owner_profile_id, question_text, contact_text,
                    consent_version, question_status
                )
                VALUES
                (
                    @ProfileId, @QuestionText, @ContactText,
                    @ConsentVersion, N''new''
                );

                DECLARE @RecruiterQuestionId bigint = CONVERT(bigint, SCOPE_IDENTITY());
                DECLARE @RecruiterQuestionKey uniqueidentifier;
                SELECT @RecruiterQuestionKey = recruiter_question_key
                FROM dbo.recruiter_questions
                WHERE recruiter_question_id = @RecruiterQuestionId
                  AND owner_profile_id = @ProfileId;

                INSERT dbo.recruiter_question_save_requests
                (
                    owner_profile_id, idempotency_key, recruiter_question_id
                )
                VALUES
                (
                    @ProfileId, @IdempotencyKey, @RecruiterQuestionId
                );

                /* Audit metadata carries no question text, no contact text,
                   and no sender fingerprint - only whether a contact field
                   was supplied at all and which consent wording applied.
                   The actor is deliberately null: the sender is anonymous
                   and this store never manufactures an identity for them. */
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"has_contact":'',
                    CASE WHEN @ContactText IS NULL THEN N''false'' ELSE N''true'' END,
                    N'',"consent_version":"'', @ConsentVersion, N''"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActionType = N''recruiter_question.submitted'',
                    @EntityType = N''recruiter_question'',
                    @EntityKey = @RecruiterQuestionKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListRecruiterQuestionsForOwner
            @UserKey nvarchar(300),
            @IncludeArchived bit = 0,
            /* Defaults to 1 (the application always wants the honest total
               alongside the bounded page). A caller that captures this
               procedure with INSERT ... EXEC - the owner-isolation verifier -
               passes 0, because T-SQL requires every result set a target
               procedure returns to match the INSERT target''s column list.
               Exactly the PS-WORKSHOP-001 @IncludeTotalCount arrangement,
               including the reason it exists. */
            @IncludeTotalCount bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL RETURN;
            IF @IncludeArchived IS NULL SET @IncludeArchived = 0;
            IF @IncludeTotalCount IS NULL SET @IncludeTotalCount = 1;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT TOP (200)
                question.recruiter_question_key,
                question.question_status,
                question.question_text,
                question.contact_text,
                question.consent_version,
                question.created_at_utc,
                question.status_changed_at_utc,
                CONVERT(binary(8), question.row_version) AS row_version
            FROM dbo.recruiter_questions AS question
            WHERE question.owner_profile_id = @ProfileId
              AND (@IncludeArchived = 1 OR question.question_status <> N''archived'')
            ORDER BY question.created_at_utc DESC, question.recruiter_question_id DESC;

            /* Second result set (opt-out via @IncludeTotalCount): the true
               count matching this exact scope and the true unread count, so
               a page reading 200 rows can say honestly how many there are
               rather than implying 200 is everything. */
            IF @IncludeTotalCount = 1
            BEGIN
                SELECT
                    COUNT(*) AS total_count,
                    ISNULL(SUM(CASE WHEN question.question_status = N''new'' THEN 1 ELSE 0 END), 0) AS new_count
                FROM dbo.recruiter_questions AS question
                WHERE question.owner_profile_id = @ProfileId
                  AND (@IncludeArchived = 1 OR question.question_status <> N''archived'');
            END;
        END;
    ');

    /* Read / archive / restore-to-unread, version-fenced. There is no
       delete procedure in this file and no DELETE statement in any
       procedure body: archiving is the only removal control v1 gives the
       member, exactly as the package's recorded exclusions require. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SetRecruiterQuestionStatusForOwner
            @UserKey nvarchar(300),
            @RecruiterQuestionKey uniqueidentifier,
            @Status nvarchar(20),
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @Status = NULLIF(LTRIM(RTRIM(@Status)), N'''');

            IF @UserKey IS NULL OR @RecruiterQuestionKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 53963, ''Owner, question, and expected version are required.'', 1;
            IF @Status IS NULL OR @Status NOT IN (N''new'', N''read'', N''archived'')
                THROW 53964, ''The requested question status is invalid.'', 1;

            BEGIN TRY
                BEGIN TRANSACTION;

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

                DECLARE @RecruiterQuestionId bigint;
                SELECT @RecruiterQuestionId = question.recruiter_question_id
                FROM dbo.recruiter_questions AS question WITH (UPDLOCK, HOLDLOCK)
                WHERE question.owner_profile_id = @ProfileId
                  AND question.recruiter_question_key = @RecruiterQuestionKey
                  AND question.row_version = @ExpectedRowVersion;

                IF @RecruiterQuestionId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome,
                           CAST(NULL AS nvarchar(20)) AS question_status,
                           CAST(NULL AS binary(8)) AS row_version;
                    RETURN;
                END;

                UPDATE dbo.recruiter_questions
                SET question_status = @Status,
                    status_changed_at_utc = SYSUTCDATETIME(),
                    status_changed_by_user_id = @UserId
                WHERE recruiter_question_id = @RecruiterQuestionId
                  AND owner_profile_id = @ProfileId;

                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100),
                    metadata_json nvarchar(max)
                );
                DECLARE @AuditMetadataJson nvarchar(max) = CONCAT
                (
                    N''{"question_status":"'', @Status, N''"}''
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId,
                    @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''recruiter_question.status_changed'',
                    @EntityType = N''recruiter_question'',
                    @EntityKey = @RecruiterQuestionKey,
                    @Outcome = N''success'',
                    @MetadataJson = @AuditMetadataJson;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome,
                       question.question_status,
                       question.row_version
                FROM dbo.recruiter_questions AS question
                WHERE question.recruiter_question_id = @RecruiterQuestionId
                  AND question.owner_profile_id = @ProfileId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_ASK_PETE_DIRECT_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_SubmitRecruiterQuestion'),
        (N'usp_ListRecruiterQuestionsForOwner'),
        (N'usp_SetRecruiterQuestionStatusForOwner');

    DECLARE @ProtectedProcedureName sysname;
    DECLARE @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures
        ORDER BY procedure_name;

        SELECT @ProtectedProcedureHash = CONVERT
        (
            nvarchar(64),
            HASHBYTES
            (
                'SHA2_256',
                OBJECT_DEFINITION
                (
                    OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
                )
            ),
            2
        );

        IF EXISTS
        (
            SELECT 1
            FROM sys.extended_properties AS property
            WHERE property.class = 1
              AND property.major_id =
                  OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
              AND property.minor_id = 0
              AND property.name = @ProcedureHashPropertyName
        )
            EXEC sys.sp_updateextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = @ProcedureHashPropertyName,
                @value = @ProtectedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @ProtectedProcedureName;

        DELETE @ProtectedProcedures
        WHERE procedure_name = @ProtectedProcedureName;
    END;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-ASK-PETE-DIRECT-001'
    )
    BEGIN
        INSERT dbo.schema_migrations
        (
            migration_id, description, application_version
        )
        VALUES
        (
            N'PS-ASK-PETE-DIRECT-001',
            N'Private recruiter question inbox: recruiter_questions, an idempotent submission ledger, one anonymous-capable consent-required submit procedure, and two owner-scoped read/status procedures. Archive-only; no delete procedure.',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-ASK-PETE-DIRECT-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
