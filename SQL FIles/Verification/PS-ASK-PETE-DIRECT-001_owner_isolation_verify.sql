/* PS-ASK-PETE-DIRECT-001 production-safe verification.

   Two synthetic recipients inside one outer always-rolled-back
   transaction prove that: all three procedures resolve their own owner
   key to @ProfileId and re-assert owner_profile_id on every predicate;
   none accepts a caller-supplied @OwnerProfileId; NONE OF THEM CONTAINS
   A DELETE STATEMENT AT ALL, so archive really is the only removal
   control v1 has; the anonymous submit is idempotent per recipient and
   never returns the question key to its anonymous caller; the same
   idempotency-key literal used against two recipients creates two
   independent questions; the owner list read is bounded TOP (200),
   excludes archived rows by default, still returns them on request, and
   never leaks another recipient's question; the status change is
   version-fenced and owner-isolated; a forged, unresolvable owner key
   never returns a row or a truthful-looking write outcome from any of
   the three; and no question or contact text ever reaches audit metadata
   or the idempotency ledger. Every synthetic row is rolled back.

   Calling convention (the PS-WORKSHOP-001 rehearsal discovery, which
   applies identically here): usp_SubmitRecruiterQuestion and
   usp_SetRecruiterQuestionStatusForOwner each record their audit event
   with INSERT ... EXEC dbo.usp_AppendAuditEvent once they reach a real
   state change, and T-SQL forbids nesting one INSERT ... EXEC inside
   another. The application never hits this (services/database_service.py
   always uses a bare EXEC). Here, any call expected to reach a success
   path is issued with a bare EXEC and its result confirmed by reading
   the tables directly; only calls that stay on an early-return branch
   ('existing' / 'not_found' / 'changed', all of which return before the
   audit call) capture their outcome row with INSERT ... EXEC.
   usp_ListRecruiterQuestionsForOwner is captured with
   @IncludeTotalCount = 0 for the same reason PS-WORKSHOP-001 does it:
   INSERT ... EXEC requires every returned result set to match the
   INSERT target's column list.

   One guard is checked by definition text rather than by execution: the
   consent requirement (@ConsentGiven <> 1 THROWs before anything is
   stored). The procedure raises that error while XACT_ABORT is ON, which
   dooms the enclosing transaction, so a live call to it cannot be caught
   and recovered from inside this single-transaction verifier. The
   executable coverage of that path lives in
   tests/ask_pete_direct/, which drives the service and the endpoint with
   consent absent, false, and non-boolean and asserts nothing is stored.
   The text check below still proves the guard is present and precedes
   every INSERT in the procedure body. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-ASK-PETE-DIRECT-001'
    )
        THROW 54000, 'PS-ASK-PETE-DIRECT-001 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps.
       ------------------------------------------------------------ */
    DECLARE @ProcedureNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProcedureNames (procedure_name)
    VALUES
        (N'usp_SubmitRecruiterQuestion'),
        (N'usp_ListRecruiterQuestionsForOwner'),
        (N'usp_SetRecruiterQuestionStatusForOwner');

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ProcedureNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ProcedureNames
        ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 54001, 'A required recruiter question procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
           OR @CheckDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
            THROW 54002, 'A recruiter question procedure is not owner-resolving or accepts an owner id from its caller.', 1;

        /* Archive-only is structural, not a convention: no procedure this
           migration owns may contain a DELETE at all. */
        IF @CheckDefinition LIKE N'%DELETE%'
            THROW 54003, 'A recruiter question procedure contains a DELETE statement.', 1;

        DELETE @ProcedureNames WHERE procedure_name = @CheckName;
    END;

    DECLARE @SubmitDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_SubmitRecruiterQuestion', N'P'));
    IF @SubmitDefinition NOT LIKE N'%@OwnerUserKey nvarchar(300)%'
        THROW 54004, 'usp_SubmitRecruiterQuestion does not take a bounded recipient key.', 1;
    /* Consent guard present, and ahead of the first INSERT in the body. */
    IF @SubmitDefinition NOT LIKE N'%@ConsentGiven IS NULL OR @ConsentGiven <> 1%'
        THROW 54005, 'usp_SubmitRecruiterQuestion does not require consent.', 1;
    IF CHARINDEX(N'@ConsentGiven <> 1', @SubmitDefinition)
       > CHARINDEX(N'INSERT dbo.recruiter_questions', @SubmitDefinition)
        THROW 54006, 'usp_SubmitRecruiterQuestion checks consent after it stores.', 1;
    /* The anonymous caller must never be handed the question identifier. */
    IF @SubmitDefinition LIKE N'%SELECT N''success'' AS outcome, %'
       OR @SubmitDefinition LIKE N'%AS outcome, recruiter_question_key%'
        THROW 54007, 'usp_SubmitRecruiterQuestion returns more than an outcome to its anonymous caller.', 1;

    DECLARE @ListDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListRecruiterQuestionsForOwner', N'P'));
    IF @ListDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @ListDefinition NOT LIKE N'%TOP (200)%'
        THROW 54008, 'usp_ListRecruiterQuestionsForOwner is not owner-keyed and bounded.', 1;

    DECLARE @StatusDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_SetRecruiterQuestionStatusForOwner', N'P'));
    IF @StatusDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @StatusDefinition NOT LIKE N'%row_version = @ExpectedRowVersion%'
        THROW 54009, 'usp_SetRecruiterQuestionStatusForOwner is not owner-keyed and version-fenced.', 1;

    IF OBJECT_ID(N'dbo.usp_DeleteRecruiterQuestionForOwner', N'P') IS NOT NULL
       OR OBJECT_ID(N'dbo.usp_PurgeRecruiterQuestions', N'P') IS NOT NULL
        THROW 54010, 'A recruiter question delete or purge procedure exists; v1 is archive-only.', 1;

    /* ------------------------------------------------------------
       1. Two synthetic recipients via a throwaway auth provider.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:ask-pete-direct-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'ask-pete-direct-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'ask-pete-direct-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'ask-pete-direct-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Ask Pete direct verification recipient A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'ask-pete-direct-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Ask Pete direct verification recipient B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;

    SELECT
        @UserKeyA = app_user.user_key,
        @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'ask-pete-direct-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT
        @UserKeyB = app_user.user_key,
        @ProfileIdB = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'ask-pete-direct-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 54011, 'Synthetic recruiter question recipients were not provisioned.', 1;

    /* ------------------------------------------------------------
       2. Anonymous submit: idempotent per recipient, key never
          returned, and the per-recipient namespace does not collide.
       ------------------------------------------------------------ */
    DECLARE @SubmitResult TABLE (outcome nvarchar(30));
    DECLARE @ConsentVersion nvarchar(60) = N'ask-pete-direct-consent.v1';

    DECLARE @IdempotencyKeyShared nvarchar(200) = CONCAT(N'direct-key-shared-', @Suffix);
    DECLARE @IdempotencyKeySecond nvarchar(200) = CONCAT(N'direct-key-a2-', @Suffix);

    DECLARE @QuestionA1 nvarchar(2000) = CONCAT(N'Recipient A first question ', @Suffix);
    DECLARE @ContactA1 nvarchar(300) = CONCAT(N'A sender contact ', LEFT(@Suffix, 20));
    DECLARE @QuestionA1Replay nvarchar(2000) = N'Replayed question text must not persist';
    DECLARE @QuestionA2 nvarchar(2000) = CONCAT(N'Recipient A second question ', @Suffix);
    DECLARE @QuestionB1 nvarchar(2000) =
        N'SYNTHETIC RECIPIENT B QUESTION - MUST NOT ENTER RECIPIENT A RESULT';
    DECLARE @ContactB1 nvarchar(300) =
        N'SYNTHETIC RECIPIENT B CONTACT - MUST NOT ENTER RECIPIENT A RESULT';

    -- Bare EXEC: this call reaches the success path, which nests its own
    -- INSERT ... EXEC audit call (see the calling-convention note above).
    EXEC dbo.usp_SubmitRecruiterQuestion
        @OwnerUserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyShared,
        @QuestionText = @QuestionA1,
        @ContactText = @ContactA1,
        @ConsentVersion = @ConsentVersion,
        @ConsentGiven = 1;

    DECLARE @QuestionKeyA1 uniqueidentifier;
    DECLARE @QuestionIdA1 bigint;
    DECLARE @RowVersionA1 binary(8);
    SELECT
        @QuestionKeyA1 = question.recruiter_question_key,
        @QuestionIdA1 = question.recruiter_question_id,
        @RowVersionA1 = question.row_version
    FROM dbo.recruiter_question_save_requests AS request
    JOIN dbo.recruiter_questions AS question
      ON question.recruiter_question_id = request.recruiter_question_id
     AND question.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdA
      AND request.idempotency_key = @IdempotencyKeyShared;

    IF @QuestionKeyA1 IS NULL
        THROW 54012, 'The first anonymous submit did not store a question.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions
        WHERE recruiter_question_id = @QuestionIdA1
          AND question_status = N'new'
          AND status_changed_at_utc IS NULL
          AND status_changed_by_user_id IS NULL
          AND consent_version = @ConsentVersion
    )
        THROW 54013, 'A stored question did not start unread with its consent version recorded.', 1;

    DELETE @SubmitResult;
    INSERT @SubmitResult
    EXEC dbo.usp_SubmitRecruiterQuestion
        @OwnerUserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyShared,
        @QuestionText = @QuestionA1Replay,
        @ContactText = NULL,
        @ConsentVersion = @ConsentVersion,
        @ConsentGiven = 1;

    IF NOT EXISTS (SELECT 1 FROM @SubmitResult WHERE outcome = N'existing')
        THROW 54014, 'A repeated idempotency key did not report an existing question.', 1;
    IF (SELECT COUNT(*) FROM dbo.recruiter_questions WHERE owner_profile_id = @ProfileIdA) <> 1
        THROW 54015, 'A replayed submit created a second question.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions
        WHERE recruiter_question_id = @QuestionIdA1 AND question_text = @QuestionA1Replay
    )
        THROW 54016, 'A replayed submit overwrote the original question text.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions
        WHERE recruiter_question_id = @QuestionIdA1
          AND question_text = @QuestionA1
          AND contact_text = @ContactA1
    )
        THROW 54017, 'The original question and contact text did not persist.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.recruiter_question_save_requests
        WHERE owner_profile_id = @ProfileIdA AND idempotency_key = @IdempotencyKeyShared
    ) <> 1
        THROW 54018, 'The idempotency ledger recorded more than one replay row.', 1;

    -- Bare EXEC: reaches the success path.
    EXEC dbo.usp_SubmitRecruiterQuestion
        @OwnerUserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeySecond,
        @QuestionText = @QuestionA2,
        @ContactText = NULL,
        @ConsentVersion = @ConsentVersion,
        @ConsentGiven = 1;

    DECLARE @QuestionKeyA2 uniqueidentifier;
    SELECT @QuestionKeyA2 = question.recruiter_question_key
    FROM dbo.recruiter_question_save_requests AS request
    JOIN dbo.recruiter_questions AS question
      ON question.recruiter_question_id = request.recruiter_question_id
     AND question.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdA
      AND request.idempotency_key = @IdempotencyKeySecond;

    IF @QuestionKeyA2 IS NULL OR @QuestionKeyA2 = @QuestionKeyA1
        THROW 54019, 'A distinct idempotency key did not create a distinct second question.', 1;

    -- Bare EXEC: reaches the success path. Same key literal, different
    -- recipient: the namespace is per recipient, so this is a new question.
    EXEC dbo.usp_SubmitRecruiterQuestion
        @OwnerUserKey = @UserKeyB,
        @IdempotencyKey = @IdempotencyKeyShared,
        @QuestionText = @QuestionB1,
        @ContactText = @ContactB1,
        @ConsentVersion = @ConsentVersion,
        @ConsentGiven = 1;

    DECLARE @QuestionKeyB1 uniqueidentifier;
    SELECT @QuestionKeyB1 = question.recruiter_question_key
    FROM dbo.recruiter_question_save_requests AS request
    JOIN dbo.recruiter_questions AS question
      ON question.recruiter_question_id = request.recruiter_question_id
     AND question.owner_profile_id = request.owner_profile_id
    WHERE request.owner_profile_id = @ProfileIdB
      AND request.idempotency_key = @IdempotencyKeyShared;

    IF @QuestionKeyB1 IS NULL OR @QuestionKeyB1 IN (@QuestionKeyA1, @QuestionKeyA2)
        THROW 54020, 'The same idempotency-key literal collided across two recipients.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.recruiter_question_save_requests
        WHERE idempotency_key = @IdempotencyKeyShared
    ) <> 2
        THROW 54021, 'The per-recipient idempotency ledger did not scope by recipient.', 1;

    /* ------------------------------------------------------------
       3. Owner-isolated list read, archived excluded by default.
       ------------------------------------------------------------ */
    DECLARE @ListRead TABLE
    (
        recruiter_question_key uniqueidentifier,
        question_status nvarchar(20),
        question_text nvarchar(2000),
        contact_text nvarchar(300),
        consent_version nvarchar(60),
        created_at_utc datetime2(7),
        status_changed_at_utc datetime2(7),
        row_version binary(8)
    );

    INSERT @ListRead
    EXEC dbo.usp_ListRecruiterQuestionsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 0, @IncludeTotalCount = 0;

    IF (SELECT COUNT(*) FROM @ListRead) <> 2
        THROW 54022, 'Recipient A default list did not return exactly their two questions.', 1;
    IF EXISTS (SELECT 1 FROM @ListRead WHERE recruiter_question_key = @QuestionKeyB1)
        THROW 54023, 'A cross-recipient question leaked into the recipient A list read.', 1;
    IF EXISTS (SELECT 1 FROM @ListRead WHERE question_text = @QuestionB1 OR contact_text = @ContactB1)
        THROW 54024, 'Recipient B sentinel text leaked into the recipient A list read.', 1;

    /* ------------------------------------------------------------
       4. Status change: version-fenced, owner-isolated, archive keeps
          the question retrievable rather than removing it.
       ------------------------------------------------------------ */
    DECLARE @StatusResult TABLE
    (
        outcome nvarchar(30),
        question_status nvarchar(20),
        row_version binary(8)
    );
    DECLARE @StaleRowVersion binary(8) = 0x0000000000000001;

    INSERT @StatusResult
    EXEC dbo.usp_SetRecruiterQuestionStatusForOwner
        @UserKey = @UserKeyA,
        @RecruiterQuestionKey = @QuestionKeyA1,
        @Status = N'read',
        @ExpectedRowVersion = @StaleRowVersion;

    IF EXISTS (SELECT 1 FROM @StatusResult WHERE outcome <> N'changed' OR question_status IS NOT NULL)
        THROW 54025, 'A stale expected version did not produce a changed outcome.', 1;
    IF (SELECT question_status FROM dbo.recruiter_questions WHERE recruiter_question_id = @QuestionIdA1) <> N'new'
        THROW 54026, 'A stale expected version still changed the question status.', 1;

    DELETE @StatusResult;
    INSERT @StatusResult
    EXEC dbo.usp_SetRecruiterQuestionStatusForOwner
        @UserKey = @UserKeyB,
        @RecruiterQuestionKey = @QuestionKeyA1,
        @Status = N'archived',
        @ExpectedRowVersion = @RowVersionA1;

    IF EXISTS (SELECT 1 FROM @StatusResult WHERE outcome <> N'changed')
        THROW 54027, 'Recipient B changed the status of recipient A''s question.', 1;

    -- Bare EXEC: reaches the success path.
    EXEC dbo.usp_SetRecruiterQuestionStatusForOwner
        @UserKey = @UserKeyA,
        @RecruiterQuestionKey = @QuestionKeyA1,
        @Status = N'read',
        @ExpectedRowVersion = @RowVersionA1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions
        WHERE recruiter_question_id = @QuestionIdA1
          AND question_status = N'read'
          AND status_changed_at_utc IS NOT NULL
          AND status_changed_by_user_id IS NOT NULL
    )
        THROW 54028, 'A correctly fenced status change did not mark the question read.', 1;

    DECLARE @RowVersionA1Read binary(8) =
        (SELECT row_version FROM dbo.recruiter_questions WHERE recruiter_question_id = @QuestionIdA1);

    -- Bare EXEC: reaches the success path.
    EXEC dbo.usp_SetRecruiterQuestionStatusForOwner
        @UserKey = @UserKeyA,
        @RecruiterQuestionKey = @QuestionKeyA1,
        @Status = N'archived',
        @ExpectedRowVersion = @RowVersionA1Read;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions
        WHERE recruiter_question_id = @QuestionIdA1 AND question_status = N'archived'
    )
        THROW 54029, 'A correctly fenced archive did not archive the question.', 1;

    DELETE @ListRead;
    INSERT @ListRead
    EXEC dbo.usp_ListRecruiterQuestionsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 0, @IncludeTotalCount = 0;
    IF EXISTS (SELECT 1 FROM @ListRead WHERE recruiter_question_key = @QuestionKeyA1)
        THROW 54030, 'An archived question leaked into the default list read.', 1;

    DELETE @ListRead;
    INSERT @ListRead
    EXEC dbo.usp_ListRecruiterQuestionsForOwner
        @UserKey = @UserKeyA, @IncludeArchived = 1, @IncludeTotalCount = 0;
    IF NOT EXISTS
    (
        SELECT 1 FROM @ListRead
        WHERE recruiter_question_key = @QuestionKeyA1
          AND question_status = N'archived'
          AND question_text = @QuestionA1
    )
        THROW 54031, 'Archiving removed the question instead of keeping it retrievable.', 1;

    /* Archiving is reversible: nothing in v1 is one-way except storage
       itself, which the sender consented to. */
    DECLARE @RowVersionA1Archived binary(8) =
        (SELECT row_version FROM dbo.recruiter_questions WHERE recruiter_question_id = @QuestionIdA1);

    -- Bare EXEC: reaches the success path.
    EXEC dbo.usp_SetRecruiterQuestionStatusForOwner
        @UserKey = @UserKeyA,
        @RecruiterQuestionKey = @QuestionKeyA1,
        @Status = N'new',
        @ExpectedRowVersion = @RowVersionA1Archived;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions
        WHERE recruiter_question_id = @QuestionIdA1
          AND question_status = N'new'
          AND status_changed_at_utc IS NOT NULL
          AND status_changed_by_user_id IS NOT NULL
    )
        THROW 54032, 'An archived question could not be returned to the unread state.', 1;

    /* ------------------------------------------------------------
       5. Reverse-direction isolation on the read.
       ------------------------------------------------------------ */
    DECLARE @ListReadB TABLE
    (
        recruiter_question_key uniqueidentifier,
        question_status nvarchar(20),
        question_text nvarchar(2000),
        contact_text nvarchar(300),
        consent_version nvarchar(60),
        created_at_utc datetime2(7),
        status_changed_at_utc datetime2(7),
        row_version binary(8)
    );
    INSERT @ListReadB
    EXEC dbo.usp_ListRecruiterQuestionsForOwner
        @UserKey = @UserKeyB, @IncludeArchived = 1, @IncludeTotalCount = 0;

    IF (SELECT COUNT(*) FROM @ListReadB) <> 1
       OR NOT EXISTS (SELECT 1 FROM @ListReadB WHERE recruiter_question_key = @QuestionKeyB1)
        THROW 54033, 'Recipient B list did not return exactly their own question.', 1;
    IF EXISTS (SELECT 1 FROM @ListReadB WHERE recruiter_question_key IN (@QuestionKeyA1, @QuestionKeyA2))
        THROW 54034, 'A cross-recipient question leaked into the recipient B list read.', 1;

    /* ------------------------------------------------------------
       6. Forged / unresolvable owner key against all three.
       ------------------------------------------------------------ */
    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';
    DECLARE @IdempotencyKeyForged nvarchar(200) = CONCAT(N'direct-key-forged-', @Suffix);
    DECLARE @QuestionForged nvarchar(2000) =
        CONCAT(N'Forged recipient submit must not persist ', @Suffix);

    DELETE @SubmitResult;
    INSERT @SubmitResult
    EXEC dbo.usp_SubmitRecruiterQuestion
        @OwnerUserKey = @ForgedUserKey,
        @IdempotencyKey = @IdempotencyKeyForged,
        @QuestionText = @QuestionForged,
        @ContactText = NULL,
        @ConsentVersion = @ConsentVersion,
        @ConsentGiven = 1;

    IF NOT EXISTS (SELECT 1 FROM @SubmitResult WHERE outcome = N'not_found')
        THROW 54035, 'A forged recipient key produced a truthful-looking submit outcome.', 1;
    /* Scoped to this run's own sentinel text rather than to "any row
       outside the two synthetic profiles": this script is production-safe
       and must not fail merely because a real recipient legitimately has
       questions of their own. */
    IF EXISTS
    (
        SELECT 1 FROM dbo.recruiter_questions WHERE question_text = @QuestionForged
    )
       OR EXISTS
    (
        SELECT 1 FROM dbo.recruiter_question_save_requests
        WHERE idempotency_key = @IdempotencyKeyForged
    )
        THROW 54036, 'A forged-recipient submit created an orphaned question or ledger row.', 1;

    DECLARE @ListReadForged TABLE
    (
        recruiter_question_key uniqueidentifier,
        question_status nvarchar(20),
        question_text nvarchar(2000),
        contact_text nvarchar(300),
        consent_version nvarchar(60),
        created_at_utc datetime2(7),
        status_changed_at_utc datetime2(7),
        row_version binary(8)
    );
    INSERT @ListReadForged
    EXEC dbo.usp_ListRecruiterQuestionsForOwner
        @UserKey = @ForgedUserKey, @IncludeArchived = 1, @IncludeTotalCount = 0;
    IF EXISTS (SELECT 1 FROM @ListReadForged)
        THROW 54037, 'A forged owner key returned rows from the list read.', 1;

    DECLARE @RowVersionA1Current binary(8) =
        (SELECT row_version FROM dbo.recruiter_questions WHERE recruiter_question_id = @QuestionIdA1);

    DELETE @StatusResult;
    INSERT @StatusResult
    EXEC dbo.usp_SetRecruiterQuestionStatusForOwner
        @UserKey = @ForgedUserKey,
        @RecruiterQuestionKey = @QuestionKeyA1,
        @Status = N'archived',
        @ExpectedRowVersion = @RowVersionA1Current;
    IF EXISTS (SELECT 1 FROM @StatusResult WHERE outcome <> N'changed' OR question_status IS NOT NULL)
        THROW 54038, 'A forged owner key produced a truthful-looking status outcome.', 1;
    IF (SELECT question_status FROM dbo.recruiter_questions WHERE recruiter_question_id = @QuestionIdA1) <> N'new'
        THROW 54039, 'A forged owner key changed a real recipient''s question status.', 1;

    /* ------------------------------------------------------------
       7. No question or contact text in audit metadata, and no content
          column on the idempotency ledger.
       ------------------------------------------------------------ */
    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.entity_type = N'recruiter_question'
          AND audit_event.entity_key IN (@QuestionKeyA1, @QuestionKeyA2, @QuestionKeyB1)
          AND
          (
              audit_event.metadata_json LIKE N'%' + @QuestionA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @QuestionA2 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @QuestionB1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @ContactA1 + N'%'
              OR audit_event.metadata_json LIKE N'%' + @ContactB1 + N'%'
          )
    )
        THROW 54040, 'Audit metadata contains recruiter question or contact text.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.action_type = N'recruiter_question.submitted'
          AND audit_event.entity_key IN (@QuestionKeyA1, @QuestionKeyA2, @QuestionKeyB1)
          AND (audit_event.actor_user_id IS NOT NULL OR audit_event.actor_user_key_snapshot IS NOT NULL)
    )
        THROW 54041, 'An anonymous submission was audited against a manufactured actor identity.', 1;

    IF EXISTS
    (
        SELECT 1 FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.recruiter_question_save_requests')
          AND name IN (N'question_text', N'contact_text', N'body', N'sender_ip', N'sender_email')
    )
        THROW 54042, 'The idempotency ledger contains a question, contact, or sender column.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-ASK-PETE-DIRECT-001 two-recipient isolation across all three procedures, per-recipient idempotent anonymous submit without overwrite or key disclosure, version-fenced owner status changes with forged-owner canaries, archived questions retrievable and restorable, TOP (200) list bound, no DELETE statement in any procedure and no delete/purge procedure at all, no question or contact text in audit metadata, no manufactured actor for an anonymous submission, and full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
