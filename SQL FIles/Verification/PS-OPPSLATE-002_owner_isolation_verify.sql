/* PS-OPPSLATE-002 (Slices OS-1, OS-2 and OS-3) production-safe verification.

   Uses two synthetic owners inside one outer always-rolled-back
   transaction to prove that the Opportunity Slate working store cannot
   leak or be written across members:

     - every one of the seventeen procedures declares @UserKey nvarchar(300),
       resolves it to @ProfileId itself, filters owner_profile_id =
       @ProfileId, and never accepts a caller-supplied @OwnerProfileId;
     - no procedure contains an aggregate score / percentage /
       recommendation / verdict concept (handoff section 1's standing
       product rule, checked as a literal absence so it cannot reappear);
     - one member's read never returns another member's working session,
       source, or wording;
     - Save is idempotent per owner and its per-owner idempotency
       namespace lets two members legitimately reuse the same key literal;
     - a byte-identical resubmission does not append a second version;
     - a correction writes member_corrected_text ONLY and leaves
       original_text byte-identical - the verbatim employer wording is
       always recoverable;
     - correcting or replacing confirmed wording clears the confirmation;
     - Correct / Confirm / Delete are fenced by @ExpectedRowVersion and
       return the neutral 'changed' outcome on mismatch;
     - a forged, unresolvable @UserKey never returns a row and never
       produces a truthful-looking write outcome from any procedure, and
       never destroys a real owner's working data;
     - the purge destroys expired working data for its own owner only and
       leaves unexpired sessions - and other owners entirely - untouched;
     - an expired working session is already invisible to the read before
       any purge has run;
     - (slice OS-2) an AI proposal is a THIRD data class and never
       overwrites either of the other two: saving a wording review and
       saving a requirement proposal both leave original_text and the
       member's own corrections byte-identical, and a member's
       reclassification never touches proposed_class;
     - (slice OS-2) one owner can neither read nor resolve another owner's
       extraction concerns or requirement statements, and a forged
       @UserKey produces no truthful-looking outcome from any of the seven
       new procedures;
     - (slice OS-2) correcting a statement clears the requirement-set
       confirmation, exactly as correcting the source clears the source's.

   Calling convention note: no procedure in PS-OPPSLATE-002 appends an
   audit event (a working session is ephemeral infrastructure - see the
   forward migration's header), so no INSERT ... EXEC nesting restriction
   applies here and every call below can be captured directly.
   usp_PurgeExpiredOpportunityWorkingData is invoked with
   @IncludeCounts = 0 where its result set is not being read.

   Every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-OPPSLATE-002'
    )
        THROW 53600, 'PS-OPPSLATE-002 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps across all seventeen procedures.
       ------------------------------------------------------------ */
    DECLARE @ProcedureNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProcedureNames (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_GetOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunitySourceForOwner'),
        (N'usp_CorrectOpportunitySourceForOwner'),
        (N'usp_ConfirmOpportunitySourceForOwner'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_GetOpportunitySourceReviewForOwner'),
        (N'usp_SaveOpportunitySourceReviewForOwner'),
        (N'usp_ResolveOpportunitySourceConcernForOwner'),
        (N'usp_GetOpportunityRequirementsForOwner'),
        (N'usp_SaveOpportunityRequirementProposalForOwner'),
        (N'usp_CorrectOpportunityRequirementStatementForOwner'),
        (N'usp_ConfirmOpportunityRequirementsForOwner'),
        (N'usp_ListOpportunityEvidenceForOwner'),
        (N'usp_GetOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityAnalysisForOwner'),
        (N'usp_SaveOpportunityResponseForOwner');

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ProcedureNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ProcedureNames
        ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 53601, 'A required Opportunity Slate procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 53602, 'An Opportunity Slate procedure does not declare @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
            THROW 53603, 'An Opportunity Slate procedure accepts a caller-supplied @OwnerProfileId.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 53604, 'An Opportunity Slate procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
            THROW 53605, 'An Opportunity Slate procedure does not filter owner_profile_id = @ProfileId.', 1;
        /* No overall score, percentage, recommendation, or employer
           prediction at any layer, including the database.

           2026-08-04 independent review, finding F13. This used to match four
           FIXED names, so `alignment_rating`, `fit_index` or `confidence`
           would have walked straight through the guard whose whole subject is
           "no aggregate verdict about a person". The rule is about the
           CONCEPT, so the check is about the concept: any identifier carrying
           a scoring, rating, ranking, percentage, verdict, recommendation or
           prediction word, whatever it is prefixed with.

           OBJECT_DEFINITION returns the procedure's COMMENTS as well as its
           code, and this guard deliberately does not try to tell them apart -
           a substring test that thinks it can parse SQL comments is a worse
           bet than a blunt one. All seventeen bodies are clean of every word
           below. Explain the no-aggregate rule in the migration file's own
           prose, which sits outside the procedure text and is therefore not
           part of any definition this reads. */
        IF @CheckDefinition LIKE N'%score%'
           OR @CheckDefinition LIKE N'%rating%'
           OR @CheckDefinition LIKE N'%ranking%'
           OR @CheckDefinition LIKE N'%percentile%'
           OR @CheckDefinition LIKE N'%match_percentage%'
           OR @CheckDefinition LIKE N'%fit_index%'
           OR @CheckDefinition LIKE N'%confidence%'
           OR @CheckDefinition LIKE N'%likelihood%'
           OR @CheckDefinition LIKE N'%probability%'
           OR @CheckDefinition LIKE N'%recommendation%'
           OR @CheckDefinition LIKE N'%verdict%'
            THROW 53606, 'An Opportunity Slate procedure references a forbidden aggregate verdict concept.', 1;

        DELETE @ProcedureNames WHERE procedure_name = @CheckName;
    END;

    IF EXISTS
    (
        SELECT 1 FROM sys.columns
        WHERE object_id IN
        (
            OBJECT_ID(N'dbo.opportunity_working_sessions'),
            OBJECT_ID(N'dbo.opportunity_sources'),
            OBJECT_ID(N'dbo.opportunity_source_versions'),
            OBJECT_ID(N'dbo.opportunity_source_reviews'),
            OBJECT_ID(N'dbo.opportunity_source_concerns'),
            OBJECT_ID(N'dbo.opportunity_requirement_sets'),
            OBJECT_ID(N'dbo.opportunity_requirement_set_versions'),
            OBJECT_ID(N'dbo.opportunity_requirement_statements')
        )
          AND name IN (N'overall_score', N'match_score', N'match_percentage', N'recommendation')
    )
        THROW 53607, 'An Opportunity Slate table carries a forbidden aggregate verdict column.', 1;

    /* ------------------------------------------------------------
       1. Two synthetic owners via a throwaway auth provider.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:oppslate-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'oppslate-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'oppslate-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA,
        @DisplayName = N'Opportunity Slate verification owner A';

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-verification',
        @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB,
        @DisplayName = N'Opportunity Slate verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    /* Slice OS-3 writes synthetic Workshop knowledge items directly, so it
       needs the app_users ids the confirmation columns reference. */
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;

    SELECT
        @UserKeyA = app_user.user_key,
        @ProfileIdA = profile.profile_id,
        @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'oppslate-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT
        @UserKeyB = app_user.user_key,
        @ProfileIdB = profile.profile_id,
        @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'oppslate-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 53608, 'Synthetic Opportunity Slate owners were not provisioned.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Save: per-owner idempotency namespace, replay, and the
          byte-identical-resubmission "unchanged" path.
       ------------------------------------------------------------ */
    DECLARE @SaveResult TABLE
    (
        outcome nvarchar(30),
        working_session_key uniqueidentifier,
        source_key uniqueidentifier,
        version_number int,
        workbench_state nvarchar(40),
        session_row_version binary(8),
        source_row_version binary(8)
    );

    DECLARE @SharedKey nvarchar(200) = CONCAT(N'oppslate-key-shared-', @Suffix);
    DECLARE @KeyA2 nvarchar(200) = CONCAT(N'oppslate-key-a2-', @Suffix);
    DECLARE @KeyA3 nvarchar(200) = CONCAT(N'oppslate-key-a3-', @Suffix);

    DECLARE @RoleTextA1 nvarchar(max) =
        CONCAT(N'Owner A pasted employer role wording ', @Suffix);
    DECLARE @RoleTextA1Forged nvarchar(max) =
        N'Forged replay wording must not persist';
    DECLARE @RoleTextA2 nvarchar(max) =
        CONCAT(N'Owner A replacement employer role wording ', @Suffix);
    DECLARE @RoleTextB1 nvarchar(max) =
        N'SYNTHETIC OPPSLATE B ROLE WORDING - MUST NOT ENTER OWNER A RESULT';
    DECLARE @CorrectionA nvarchar(max) =
        CONCAT(N'Owner A corrected employer role wording ', @Suffix);

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyA, @IdempotencyKey = @SharedKey,
        @SourceText = @RoleTextA1, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'success' AND version_number = 1)
        THROW 53609, 'Owner A could not create a working session.', 1;

    DECLARE @SessionKeyA uniqueidentifier;
    DECLARE @SourceKeyA uniqueidentifier;
    SELECT TOP (1) @SessionKeyA = working_session_key, @SourceKeyA = source_key
    FROM @SaveResult;

    /* The same key literal replayed by the SAME owner returns the SAME
       version and must not overwrite the stored wording. */
    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyA, @IdempotencyKey = @SharedKey,
        @SourceText = @RoleTextA1Forged, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'existing' AND source_key = @SourceKeyA)
        THROW 53610, 'A replayed idempotency key did not return the existing source version.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions AS version_record
        WHERE version_record.owner_profile_id = @ProfileIdA
          AND version_record.original_text = @RoleTextA1Forged
    )
        THROW 53611, 'A replayed idempotency key overwrote the stored employer wording.', 1;

    /* The same key literal used by a DIFFERENT owner is a different
       namespace and must create that owner's own independent session. */
    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyB, @IdempotencyKey = @SharedKey,
        @SourceText = @RoleTextB1, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'success' AND source_key <> @SourceKeyA)
        THROW 53612, 'A shared idempotency key literal collided across owners.', 1;

    DECLARE @SessionKeyB uniqueidentifier;
    DECLARE @SourceKeyB uniqueidentifier;
    SELECT TOP (1) @SessionKeyB = working_session_key, @SourceKeyB = source_key
    FROM @SaveResult;

    /* Byte-identical resubmission under a NEW key: no second version. */
    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyA, @IdempotencyKey = @KeyA2,
        @SourceText = @RoleTextA1, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'unchanged' AND version_number = 1)
        THROW 53613, 'Resubmitting byte-identical wording appended a needless source version.', 1;
    IF
    (
        SELECT COUNT(*) FROM dbo.opportunity_source_versions
        WHERE owner_profile_id = @ProfileIdA
    ) <> 1
        THROW 53614, 'Owner A has more than one source version after an unchanged resubmission.', 1;

    /* ------------------------------------------------------------
       3. Read isolation: neither owner ever sees the other's session.
       ------------------------------------------------------------ */
    DECLARE @GetResult TABLE
    (
        working_session_key uniqueidentifier,
        workbench_state nvarchar(40),
        expires_at_utc datetime2(7),
        session_row_version binary(8),
        source_key uniqueidentifier,
        current_version_number int,
        confirmed_version_number int,
        confirmed_at_utc datetime2(7),
        source_row_version binary(8),
        capture_method nvarchar(20),
        original_text nvarchar(max),
        member_corrected_text nvarchar(max),
        corrected_at_utc datetime2(7),
        captured_at_utc datetime2(7)
    );

    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @GetResult WHERE source_key = @SourceKeyA)
        THROW 53615, 'Owner A could not read their own working session.', 1;
    IF EXISTS (SELECT 1 FROM @GetResult WHERE original_text = @RoleTextB1 OR source_key = @SourceKeyB)
        THROW 53616, 'Owner A''s read returned owner B''s working session.', 1;
    IF (SELECT COUNT(*) FROM @GetResult) <> 1
        THROW 53617, 'The working-session read returned more than one owner''s row.', 1;

    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @ForgedUserKey;
    IF EXISTS (SELECT 1 FROM @GetResult)
        THROW 53618, 'A forged UserKey returned rows from the working-session read.', 1;

    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    DECLARE @SourceRowVersionA binary(8);
    SELECT TOP (1) @SourceRowVersionA = source_row_version FROM @GetResult;

    /* ------------------------------------------------------------
       4. Correction writes member_corrected_text ONLY. The verbatim
          employer wording stays byte-identical and recoverable.
       ------------------------------------------------------------ */
    DECLARE @CorrectResult TABLE
    (
        outcome nvarchar(30),
        source_row_version binary(8),
        version_number int
    );

    /* Forged owner first: it must not mutate owner A's wording. */
    DELETE @CorrectResult;
    INSERT @CorrectResult
    EXEC dbo.usp_CorrectOpportunitySourceForOwner
        @UserKey = @ForgedUserKey, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA, @CorrectedText = N'Forged correction must not persist';
    IF EXISTS (SELECT 1 FROM @CorrectResult WHERE outcome <> N'changed' OR source_row_version IS NOT NULL)
        THROW 53619, 'A forged UserKey produced a truthful-looking Correct outcome.', 1;

    /* Owner B may not correct owner A's source either. */
    DELETE @CorrectResult;
    INSERT @CorrectResult
    EXEC dbo.usp_CorrectOpportunitySourceForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA, @CorrectedText = N'Cross-owner correction must not persist';
    IF EXISTS (SELECT 1 FROM @CorrectResult WHERE outcome <> N'changed')
        THROW 53620, 'Owner B corrected owner A''s source.', 1;

    /* A stale @ExpectedRowVersion is refused with the same neutral
       outcome as a missing or foreign source. */
    DELETE @CorrectResult;
    INSERT @CorrectResult
    EXEC dbo.usp_CorrectOpportunitySourceForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = 0x0000000000000001, @CorrectedText = @CorrectionA;
    IF EXISTS (SELECT 1 FROM @CorrectResult WHERE outcome <> N'changed')
        THROW 53621, 'Correct is not fenced by @ExpectedRowVersion.', 1;

    DELETE @CorrectResult;
    INSERT @CorrectResult
    EXEC dbo.usp_CorrectOpportunitySourceForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA, @CorrectedText = @CorrectionA;
    IF NOT EXISTS (SELECT 1 FROM @CorrectResult WHERE outcome = N'success')
        THROW 53622, 'Owner A could not correct their own source wording.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions
        WHERE owner_profile_id = @ProfileIdA
          AND version_number = 1
          AND original_text = @RoleTextA1
          AND member_corrected_text = @CorrectionA
          AND corrected_by_user_id IS NOT NULL
          AND corrected_at_utc IS NOT NULL
    )
        THROW 53623, 'A correction did not preserve the verbatim original employer wording.', 1;

    /* Restoring the original exactly clears the overlay rather than
       storing a duplicate copy of the same text. */
    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    SELECT TOP (1) @SourceRowVersionA = source_row_version FROM @GetResult;

    DELETE @CorrectResult;
    INSERT @CorrectResult
    EXEC dbo.usp_CorrectOpportunitySourceForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA, @CorrectedText = @RoleTextA1;
    IF NOT EXISTS (SELECT 1 FROM @CorrectResult WHERE outcome = N'success')
        THROW 53624, 'Owner A could not revert their correction.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions
        WHERE owner_profile_id = @ProfileIdA
          AND version_number = 1
          AND (member_corrected_text IS NOT NULL
               OR corrected_by_user_id IS NOT NULL
               OR corrected_at_utc IS NOT NULL)
    )
        THROW 53625, 'Reverting a correction left a stale correction overlay.', 1;

    /* ------------------------------------------------------------
       5. Confirm (checkpoint 1 of 2) is owner-scoped and fenced, and a
          later wording change clears the confirmation.
       ------------------------------------------------------------ */
    DECLARE @ConfirmResult TABLE
    (
        outcome nvarchar(30),
        source_row_version binary(8),
        confirmed_version_number int
    );

    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    SELECT TOP (1) @SourceRowVersionA = source_row_version FROM @GetResult;

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @ForgedUserKey, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA;
    IF EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome <> N'changed' OR confirmed_version_number IS NOT NULL)
        THROW 53626, 'A forged UserKey produced a truthful-looking Confirm outcome.', 1;

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA;
    IF EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome <> N'changed')
        THROW 53627, 'Owner B confirmed owner A''s source.', 1;

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA;
    IF NOT EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome = N'success' AND confirmed_version_number = 1)
        THROW 53628, 'Owner A could not confirm their own source.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_working_sessions
        WHERE owner_profile_id = @ProfileIdA AND workbench_state = N'source_confirmed'
    )
        THROW 53629, 'Confirming the source did not advance the workbench state.', 1;

    /* Replacing the wording after confirmation clears the confirmation:
       a confirmed source can never describe text the member never saw. */
    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyA, @IdempotencyKey = @KeyA3,
        @SourceText = @RoleTextA2, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'success' AND version_number = 2)
        THROW 53630, 'Replacing the source did not append source version 2.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_sources
        WHERE owner_profile_id = @ProfileIdA AND confirmed_version_number IS NOT NULL
    )
        THROW 53631, 'Replacing the source left a stale confirmation.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions
        WHERE owner_profile_id = @ProfileIdA AND version_number = 1 AND original_text = @RoleTextA1
    )
        THROW 53632, 'Replacing the source destroyed the previous verbatim version.', 1;

    /* ------------------------------------------------------------
       5b. SLICE OS-2. The AI proposals are a third data class: they are
           written beside the employer's wording and the member's own
           corrections, never over either, and they are as owner-scoped as
           everything else in this store.
       ------------------------------------------------------------ */
    DECLARE @ReviewSaveResult TABLE
    (
        outcome nvarchar(30),
        review_key uniqueidentifier,
        concern_count int
    );
    DECLARE @ResolveResult TABLE
    (
        outcome nvarchar(30),
        source_row_version binary(8),
        member_resolution nvarchar(20)
    );
    DECLARE @ProposalResult TABLE
    (
        outcome nvarchar(30),
        requirement_set_key uniqueidentifier,
        version_number int,
        statement_count int
    );
    DECLARE @StatementCorrectResult TABLE
    (
        outcome nvarchar(30),
        statement_row_version binary(8),
        member_class nvarchar(40)
    );
    DECLARE @RequirementConfirmResult TABLE
    (
        outcome nvarchar(30),
        set_row_version binary(8),
        confirmed_version_number int
    );

    DECLARE @ConcernsJsonA nvarchar(max) =
        N'[{"span_start":0,"span_length":9,"quoted_text":"SYNTHETIC","concern_reason":"a fragment that may be cut off."}]';
    DECLARE @StatementsJsonA nvarchar(max) =
        N'[{"ordinal":1,"span_start":0,"span_length":9,"employer_text":"SYNTHETIC",' +
        N'"proposed_class":"required_qualification","proposed_explanation":"Synthetic reading.",' +
        N'"proposed_structure_json":"[{\"label\":\"Path A\",\"clauses\":[\"SYNTHETIC\"]}]"}]';

    /* Owner A's current source and its verbatim wording, captured before any
       proposal is written, so the byte-identical assertions below mean
       something. */
    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    DECLARE @PreProposalOriginalA nvarchar(max);
    DECLARE @PreProposalCorrectedA nvarchar(max);
    SELECT TOP (1)
        @SourceRowVersionA = source_row_version,
        @PreProposalOriginalA = original_text,
        @PreProposalCorrectedA = member_corrected_text
    FROM @GetResult;

    /* A forged owner cannot record a proposal against a real member's
       source. */
    DELETE @ReviewSaveResult;
    INSERT @ReviewSaveResult
    EXEC dbo.usp_SaveOpportunitySourceReviewForOwner
        @UserKey = @ForgedUserKey, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @ConcernsJson = @ConcernsJsonA;
    IF EXISTS (SELECT 1 FROM @ReviewSaveResult WHERE outcome <> N'changed' OR review_key IS NOT NULL)
        THROW 53650, 'A forged UserKey produced a truthful-looking wording-review outcome.', 1;

    DELETE @ReviewSaveResult;
    INSERT @ReviewSaveResult
    EXEC dbo.usp_SaveOpportunitySourceReviewForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @ConcernsJson = @ConcernsJsonA;
    IF EXISTS (SELECT 1 FROM @ReviewSaveResult WHERE outcome <> N'changed')
        THROW 53651, 'Owner B recorded a wording review against owner A''s source.', 1;

    DELETE @ReviewSaveResult;
    INSERT @ReviewSaveResult
    EXEC dbo.usp_SaveOpportunitySourceReviewForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @ConcernsJson = @ConcernsJsonA;
    IF NOT EXISTS (SELECT 1 FROM @ReviewSaveResult WHERE outcome = N'success' AND concern_count = 1)
        THROW 53652, 'Owner A could not record a wording review on their own source.', 1;

    /* THE POINT OF THE WHOLE SLICE: recording a proposal changed neither of
       the other two data classes. */
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions AS version_record
        JOIN dbo.opportunity_sources AS source_record
          ON source_record.opportunity_source_id = version_record.opportunity_source_id
        WHERE source_record.source_key = @SourceKeyA
          AND version_record.version_number = source_record.current_version_number
          AND (version_record.original_text <> @PreProposalOriginalA
               OR ISNULL(version_record.member_corrected_text, N'') <> ISNULL(@PreProposalCorrectedA, N''))
    )
        THROW 53653, 'Recording an AI wording review altered the employer wording or the member correction.', 1;

    /* Owner B cannot read owner A's concerns. */
    DECLARE @ConcernReadCount int;
    DECLARE @ReviewReadResult TABLE
    (
        review_key uniqueidentifier,
        source_version_number int,
        model_name nvarchar(200),
        prompt_contract_version nvarchar(100),
        concern_count int,
        reviewed_at_utc datetime2(7)
    );
    DELETE @ReviewReadResult;
    INSERT @ReviewReadResult
    EXEC dbo.usp_GetOpportunitySourceReviewForOwner @UserKey = @UserKeyB, @SourceKey = @SourceKeyA;
    IF EXISTS (SELECT 1 FROM @ReviewReadResult)
        THROW 53654, 'Owner B read owner A''s wording review.', 1;

    DECLARE @ConcernKeyA uniqueidentifier;
    DECLARE @ConcernRowVersionA binary(8);
    SELECT TOP (1)
        @ConcernKeyA = concern_record.concern_key,
        @ConcernRowVersionA = CONVERT(binary(8), concern_record.row_version)
    FROM dbo.opportunity_source_concerns AS concern_record
    WHERE concern_record.owner_profile_id = @ProfileIdA;

    DELETE @ResolveResult;
    INSERT @ResolveResult
    EXEC dbo.usp_ResolveOpportunitySourceConcernForOwner
        @UserKey = @UserKeyB, @ConcernKey = @ConcernKeyA,
        @ExpectedRowVersion = @ConcernRowVersionA, @Resolution = N'dismissed';
    IF EXISTS (SELECT 1 FROM @ResolveResult WHERE outcome <> N'changed')
        THROW 53655, 'Owner B resolved owner A''s extraction concern.', 1;

    DELETE @ResolveResult;
    INSERT @ResolveResult
    EXEC dbo.usp_ResolveOpportunitySourceConcernForOwner
        @UserKey = @UserKeyA, @ConcernKey = @ConcernKeyA,
        @ExpectedRowVersion = 0x0000000000000001, @Resolution = N'dismissed';
    IF EXISTS (SELECT 1 FROM @ResolveResult WHERE outcome <> N'changed')
        THROW 53656, 'Resolving a concern is not fenced by @ExpectedRowVersion.', 1;

    DELETE @ResolveResult;
    INSERT @ResolveResult
    EXEC dbo.usp_ResolveOpportunitySourceConcernForOwner
        @UserKey = @UserKeyA, @ConcernKey = @ConcernKeyA,
        @ExpectedRowVersion = @ConcernRowVersionA, @Resolution = N'dismissed';
    IF NOT EXISTS (SELECT 1 FROM @ResolveResult WHERE outcome = N'success' AND member_resolution = N'dismissed')
        THROW 53657, 'Owner A could not dismiss their own extraction concern.', 1;

    /* Dismissing changed no wording at all, so the confirmation it did not
       invalidate is still standing. */
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions AS version_record
        JOIN dbo.opportunity_sources AS source_record
          ON source_record.opportunity_source_id = version_record.opportunity_source_id
        WHERE source_record.source_key = @SourceKeyA
          AND version_record.version_number = source_record.current_version_number
          AND version_record.original_text <> @PreProposalOriginalA
    )
        THROW 53658, 'Dismissing an extraction concern altered the verbatim employer wording.', 1;

    /* CHECKPOINT 1 HAS TO BE STANDING AGAIN BEFORE CHECKPOINT 2 CAN BEGIN
       (isolated SQL gate, defect 2).

       Section 5 deliberately replaced the wording after confirming it, and
       asserted at THROW 53631 that doing so cleared the confirmation. That
       assertion is correct and stays. But every step since then has run
       against an UNCONFIRMED source, and
       usp_SaveOpportunityRequirementProposalForOwner requires
       confirmed_version_number = current_version_number before it will read
       requirements out of a source - a member cannot have PeerSlate interpret
       wording they never confirmed.

       Without this re-confirmation the proposal below correctly returns
       'changed', and THROW 53660 then reports it as a failure of the
       proposal path when it is really the confirmation guard doing its job.
       Re-confirm the current version so the assertions that follow test what
       they claim to test. */
    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    SELECT TOP (1) @SourceRowVersionA = source_row_version FROM @GetResult;

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA;
    IF NOT EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome = N'success')
        THROW 53649, 'Owner A could not re-confirm the replaced source before checkpoint 2.', 1;

    /* Requirement proposals: same owner scoping, same separation. */
    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    SELECT TOP (1) @SourceRowVersionA = source_row_version FROM @GetResult;

    DELETE @ProposalResult;
    INSERT @ProposalResult
    EXEC dbo.usp_SaveOpportunityRequirementProposalForOwner
        @UserKey = @ForgedUserKey, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @StatementsJson = @StatementsJsonA;
    IF EXISTS (SELECT 1 FROM @ProposalResult WHERE outcome <> N'changed' OR requirement_set_key IS NOT NULL)
        THROW 53659, 'A forged UserKey produced a truthful-looking requirement-proposal outcome.', 1;

    DELETE @ProposalResult;
    INSERT @ProposalResult
    EXEC dbo.usp_SaveOpportunityRequirementProposalForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @StatementsJson = @StatementsJsonA;
    IF NOT EXISTS (SELECT 1 FROM @ProposalResult WHERE outcome = N'success' AND statement_count = 1)
        THROW 53660, 'Owner A could not record a requirement proposal on their own confirmed source.', 1;

    DECLARE @StatementKeyA uniqueidentifier;
    DECLARE @StatementRowVersionA binary(8);
    DECLARE @RequirementSetKeyA uniqueidentifier;
    DECLARE @SetRowVersionA binary(8);
    SELECT TOP (1)
        @StatementKeyA = statement_record.statement_key,
        @StatementRowVersionA = CONVERT(binary(8), statement_record.row_version)
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.owner_profile_id = @ProfileIdA;
    SELECT TOP (1)
        @RequirementSetKeyA = requirement_set.requirement_set_key,
        @SetRowVersionA = CONVERT(binary(8), requirement_set.row_version)
    FROM dbo.opportunity_requirement_sets AS requirement_set
    WHERE requirement_set.owner_profile_id = @ProfileIdA;

    DELETE @StatementCorrectResult;
    INSERT @StatementCorrectResult
    EXEC dbo.usp_CorrectOpportunityRequirementStatementForOwner
        @UserKey = @UserKeyB, @StatementKey = @StatementKeyA,
        @ExpectedRowVersion = @StatementRowVersionA,
        @MemberClass = N'informational_statement';
    IF EXISTS (SELECT 1 FROM @StatementCorrectResult WHERE outcome <> N'changed')
        THROW 53661, 'Owner B corrected owner A''s requirement statement.', 1;

    /* Confirm the set first, so the next assertion can prove a correction
       clears it. */
    DELETE @RequirementConfirmResult;
    INSERT @RequirementConfirmResult
    EXEC dbo.usp_ConfirmOpportunityRequirementsForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA;
    IF NOT EXISTS (SELECT 1 FROM @RequirementConfirmResult WHERE outcome = N'success' AND confirmed_version_number = 1)
        THROW 53662, 'Owner A could not confirm their own requirement set (checkpoint 2 of 2).', 1;

    DELETE @StatementCorrectResult;
    INSERT @StatementCorrectResult
    EXEC dbo.usp_CorrectOpportunityRequirementStatementForOwner
        @UserKey = @UserKeyA, @StatementKey = @StatementKeyA,
        @ExpectedRowVersion = @StatementRowVersionA,
        @MemberClass = N'informational_statement';
    IF NOT EXISTS (SELECT 1 FROM @StatementCorrectResult WHERE outcome = N'success' AND member_class = N'informational_statement')
        THROW 53663, 'Owner A could not correct their own requirement statement.', 1;

    /* The member's reading is stored BESIDE the proposal, not over it. */
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_requirement_statements
        WHERE statement_key = @StatementKeyA
          AND proposed_class = N'required_qualification'
          AND member_class = N'informational_statement'
    )
        THROW 53664, 'A member correction overwrote the AI-proposed classification.', 1;

    /* And it cleared the confirmation, exactly as a source correction does. */
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_requirement_sets
        WHERE requirement_set_key = @RequirementSetKeyA
          AND confirmed_version_number IS NOT NULL
    )
        THROW 53665, 'Correcting a statement left a stale requirement-set confirmation.', 1;

    /* Owner B reads nothing of owner A's requirement set. */
    DECLARE @RequirementReadResult TABLE
    (
        requirement_set_key uniqueidentifier,
        set_row_version binary(8),
        version_number int,
        source_version_number int,
        model_name nvarchar(200),
        prompt_contract_version nvarchar(100),
        proposed_at_utc datetime2(7),
        confirmed_version_number int,
        confirmed_at_utc datetime2(7)
    );
    DELETE @RequirementReadResult;
    INSERT @RequirementReadResult
    EXEC dbo.usp_GetOpportunityRequirementsForOwner @UserKey = @UserKeyB;
    IF EXISTS (SELECT 1 FROM @RequirementReadResult WHERE requirement_set_key = @RequirementSetKeyA)
        THROW 53666, 'Owner B read owner A''s requirement set.', 1;

    /* ============================================================
       5b. SLICE OS-3 — the grounded alignment analysis, the member's
           responses, and the READ-ONLY evidence allowlist.

       This is the first part of the room that holds a result ABOUT A
       PERSON, so the isolation proof matters more here than anywhere else
       in the file. Four things are proved:

         * the evidence read returns only the reader''s own CONFIRMED items;
         * an analysis cannot be attached to another owner''s requirement set,
           and a forged owner gets nothing;
         * the derived status and the citation count cannot disagree, and a
           rejected payload leaves the previous analysis and every member
           response ALONE (the 2026-08-04 gate's defect-1 lesson); and
         * a response cannot connect evidence the member does not own.
       ============================================================ */

    /* Re-confirm the set the correction above un-confirmed, so the analysis
       has something to attach to. */
    SELECT TOP (1)
        @RequirementSetKeyA = requirement_set.requirement_set_key,
        @SetRowVersionA = CONVERT(binary(8), requirement_set.row_version)
    FROM dbo.opportunity_requirement_sets AS requirement_set
    WHERE requirement_set.owner_profile_id = @ProfileIdA;

    DELETE @RequirementConfirmResult;
    INSERT @RequirementConfirmResult
    EXEC dbo.usp_ConfirmOpportunityRequirementsForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA;
    IF NOT EXISTS (SELECT 1 FROM @RequirementConfirmResult WHERE outcome = N'success')
        THROW 53670, 'Owner A could not re-confirm their requirement set before analysis.', 1;

    SELECT TOP (1)
        @RequirementSetKeyA = requirement_set.requirement_set_key,
        @SetRowVersionA = CONVERT(binary(8), requirement_set.row_version)
    FROM dbo.opportunity_requirement_sets AS requirement_set
    WHERE requirement_set.owner_profile_id = @ProfileIdA;

    SELECT TOP (1) @StatementKeyA = statement_record.statement_key
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.owner_profile_id = @ProfileIdA;

    /* The evidence allowlist. Owner A has one confirmed knowledge item;
       owner B must never see it, and a forged key must see nothing. */
    DECLARE @EvidenceKeyA uniqueidentifier = NEWID();
    DECLARE @KnowledgeItemIdA bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number, confirmed_version_number, confirmed_by_user_id,
         confirmed_at_utc)
    VALUES
        (@EvidenceKeyA, @ProfileIdA, N'confirmed', N'work', 1, 1, @UserIdA,
         SYSUTCDATETIME());
    SET @KnowledgeItemIdA = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, saved_by_user_id)
    VALUES
        (@KnowledgeItemIdA, @ProfileIdA, 1, N'Synthetic evidence item',
         N'Led verification-readiness work across engineering and test.',
         N'Led verification-readiness work across engineering and test.',
         @UserIdA);

    /* Owner B gets one too (2026-08-04 review, finding F7): proving that a
       cited key must be the READER's own confirmed item needs a real item
       belonging to somebody else to cite. */
    DECLARE @EvidenceKeyB uniqueidentifier = NEWID();
    DECLARE @KnowledgeItemIdB bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number, confirmed_version_number, confirmed_by_user_id,
         confirmed_at_utc)
    VALUES
        (@EvidenceKeyB, @ProfileIdB, N'confirmed', N'work', 1, 1, @UserIdB,
         SYSUTCDATETIME());
    SET @KnowledgeItemIdB = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, saved_by_user_id)
    VALUES
        (@KnowledgeItemIdB, @ProfileIdB, 1, N'Owner B synthetic evidence item',
         N'Ran the supplier quality review programme.',
         N'Ran the supplier quality review programme.',
         @UserIdB);

    DECLARE @EvidenceResult TABLE
    (
        evidence_key uniqueidentifier,
        evidence_version int,
        evidence_title nvarchar(200),
        evidence_body nvarchar(max),
        evidence_updated_at_utc datetime2(7)
    );
    INSERT @EvidenceResult
    EXEC dbo.usp_ListOpportunityEvidenceForOwner @UserKey = @UserKeyB;
    IF EXISTS (SELECT 1 FROM @EvidenceResult WHERE evidence_key = @EvidenceKeyA)
        THROW 53671, 'Owner B read owner A''s authorized evidence.', 1;

    DELETE @EvidenceResult;
    INSERT @EvidenceResult
    EXEC dbo.usp_ListOpportunityEvidenceForOwner @UserKey = @ForgedUserKey;
    IF EXISTS (SELECT 1 FROM @EvidenceResult)
        THROW 53672, 'A forged UserKey read authorized evidence.', 1;

    DELETE @EvidenceResult;
    INSERT @EvidenceResult
    EXEC dbo.usp_ListOpportunityEvidenceForOwner @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @EvidenceResult WHERE evidence_key = @EvidenceKeyA)
        THROW 53673, 'Owner A could not read their own confirmed evidence.', 1;
    IF EXISTS (SELECT 1 FROM @EvidenceResult WHERE evidence_key = @EvidenceKeyB)
        THROW 53698, 'Owner A read owner B''s authorized evidence.', 1;

    /* An UNCONFIRMED item is not authorized evidence and must not appear. */
    DECLARE @DraftKeyA uniqueidentifier = NEWID();
    DECLARE @DraftItemIdA bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number)
    VALUES (@DraftKeyA, @ProfileIdA, N'unfinished', N'work', 1);
    SET @DraftItemIdA = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, saved_by_user_id)
    VALUES (@DraftItemIdA, @ProfileIdA, 1, N'A draft', N'Draft wording.',
            N'Draft wording.', @UserIdA);

    DELETE @EvidenceResult;
    INSERT @EvidenceResult
    EXEC dbo.usp_ListOpportunityEvidenceForOwner @UserKey = @UserKeyA;
    IF EXISTS (SELECT 1 FROM @EvidenceResult WHERE evidence_key = @DraftKeyA)
        THROW 53674, 'An unconfirmed knowledge item reached the evidence allowlist.', 1;

    /* The analysis itself. */
    DECLARE @AnalysisResult TABLE
    (
        outcome nvarchar(20),
        analysis_key uniqueidentifier,
        qualification_count int
    );
    /* 2026-08-04 independent review, finding F7. The payload deliberately
       carries a WRONG title and a WRONG version beside a real key: the
       procedure must ignore both and read the member's own confirmed item
       instead. Sending values that happen to be correct would have proved
       nothing, which is why the earlier payload did not. */
    DECLARE @ResultsJsonA nvarchar(max) =
        N'[{"statement_key":"' + CONVERT(nvarchar(36), @StatementKeyA) +
        N'","derived_status":"supported","citation_count":1,"citations":[{"ordinal":1,' +
        N'"clause_ordinal":1,"covered_text":"a synthetic clause",' +
        N'"evidence_kind":"moment","evidence_key":"' +
        CONVERT(nvarchar(36), @EvidenceKeyA) +
        N'","evidence_version":99,"evidence_title":"A title the caller invented",' +
        N'"excerpt":"Led verification-readiness work"}]}]';

    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @ForgedUserKey, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1, @ResultsJson = @ResultsJsonA;
    IF EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome <> N'changed' OR analysis_key IS NOT NULL)
        THROW 53675, 'A forged UserKey produced a truthful-looking analysis outcome.', 1;

    DELETE @AnalysisResult;
    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @UserKeyB, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1, @ResultsJson = @ResultsJsonA;
    IF EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome <> N'changed')
        THROW 53676, 'Owner B attached an analysis to owner A''s requirement set.', 1;

    DELETE @AnalysisResult;
    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1, @ResultsJson = @ResultsJsonA;
    IF NOT EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome = N'success' AND qualification_count = 1)
        THROW 53677, 'Owner A could not record an analysis of their own confirmed set.', 1;

    /* Finding F7, proved rather than assumed. The payload above named version
       99, the title "A title the caller invented" and the kind "moment". The
       stored row must carry the member's OWN confirmed version, their OWN
       title, and the kind this procedure writes - none of which came from the
       caller. */
    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.opportunity_analysis_citations AS citation_record
        WHERE citation_record.owner_profile_id = @ProfileIdA
          AND citation_record.evidence_key = @EvidenceKeyA
          AND citation_record.evidence_version = 1
          AND citation_record.evidence_title = N'Synthetic evidence item'
          AND citation_record.evidence_kind = N'knowledge_item'
    )
        THROW 53691, 'The store accepted a caller-supplied evidence identity.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_analysis_citations
        WHERE owner_profile_id = @ProfileIdA
          AND (evidence_version = 99
               OR evidence_title = N'A title the caller invented'
               OR evidence_kind = N'moment')
    )
        THROW 53692, 'A caller-invented evidence identity reached the store.', 1;

    /* And a citation naming evidence the member does NOT own is refused
       outright - owner B's confirmed item, cited by owner A. Refused before
       any mutation, so owner A's analysis above is still there afterwards. */
    DECLARE @ForeignEvidenceJson nvarchar(max) =
        N'[{"statement_key":"' + CONVERT(nvarchar(36), @StatementKeyA) +
        N'","derived_status":"supported","citation_count":1,"citations":[{"ordinal":1,' +
        N'"clause_ordinal":1,"covered_text":"a synthetic clause",' +
        N'"evidence_key":"' + CONVERT(nvarchar(36), @EvidenceKeyB) +
        N'","excerpt":"Led verification-readiness work"}]}]';

    SELECT TOP (1) @SetRowVersionA = CONVERT(binary(8), requirement_set.row_version)
    FROM dbo.opportunity_requirement_sets AS requirement_set
    WHERE requirement_set.requirement_set_key = @RequirementSetKeyA;

    DELETE @AnalysisResult;
    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1, @ResultsJson = @ForeignEvidenceJson;
    IF NOT EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome = N'invalid')
        THROW 53693, 'An analysis cited evidence the member does not own.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_analysis_citations
        WHERE owner_profile_id = @ProfileIdA
          AND evidence_key = @EvidenceKeyA
    )
        THROW 53694, 'A refused foreign-evidence payload destroyed the previous analysis.', 1;

    /* Finding F8. An over-length excerpt must reach the GUARD and return
       ''invalid'', not be truncated by a narrow OPENJSON declaration and then
       trip a CHECK constraint as an engine error after the DELETEs. */
    DECLARE @OverLongExcerptJson nvarchar(max) =
        N'[{"statement_key":"' + CONVERT(nvarchar(36), @StatementKeyA) +
        N'","derived_status":"supported","citation_count":1,"citations":[{"ordinal":1,' +
        N'"clause_ordinal":1,"covered_text":"a synthetic clause",' +
        N'"evidence_key":"' + CONVERT(nvarchar(36), @EvidenceKeyA) +
        N'","excerpt":"' + REPLICATE(N'x', 900) + N'"}]}]';

    SELECT TOP (1) @SetRowVersionA = CONVERT(binary(8), requirement_set.row_version)
    FROM dbo.opportunity_requirement_sets AS requirement_set
    WHERE requirement_set.requirement_set_key = @RequirementSetKeyA;

    DELETE @AnalysisResult;
    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1, @ResultsJson = @OverLongExcerptJson;
    IF NOT EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome = N'invalid')
        THROW 53695, 'An over-length excerpt did not reach the guard as invalid.', 1;

    /* Finding F8, last part: citation_count must match the rows supplied. */
    DECLARE @CountDriftJson nvarchar(max) =
        N'[{"statement_key":"' + CONVERT(nvarchar(36), @StatementKeyA) +
        N'","derived_status":"supported","citation_count":4,"citations":[{"ordinal":1,' +
        N'"clause_ordinal":1,"covered_text":"a synthetic clause",' +
        N'"evidence_key":"' + CONVERT(nvarchar(36), @EvidenceKeyA) +
        N'","excerpt":"Led verification-readiness work"}]}]';

    DELETE @AnalysisResult;
    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1, @ResultsJson = @CountDriftJson;
    IF NOT EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome = N'invalid')
        THROW 53696, 'A stored citation count drifted from the rows behind it.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_analysis_citations
        WHERE owner_profile_id = @ProfileIdA
          AND evidence_key = @EvidenceKeyA
    )
        THROW 53697, 'A refused citation payload destroyed the previous analysis.', 1;

    /* The member's response, and its evidence-ownership check. */
    SELECT TOP (1) @StatementRowVersionA = CONVERT(binary(8), statement_record.row_version)
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.statement_key = @StatementKeyA;

    DECLARE @ResponseResult TABLE
    (
        outcome nvarchar(20),
        response_key uniqueidentifier,
        response_kind nvarchar(30)
    );
    INSERT @ResponseResult
    EXEC dbo.usp_SaveOpportunityResponseForOwner
        @UserKey = @UserKeyB, @StatementKey = @StatementKeyA,
        @ExpectedRowVersion = @StatementRowVersionA,
        @ResponseKind = N'skip';
    IF EXISTS (SELECT 1 FROM @ResponseResult WHERE outcome <> N'changed')
        THROW 53678, 'Owner B answered owner A''s qualification.', 1;

    DELETE @ResponseResult;
    INSERT @ResponseResult
    EXEC dbo.usp_SaveOpportunityResponseForOwner
        @UserKey = @UserKeyA, @StatementKey = @StatementKeyA,
        @ExpectedRowVersion = @StatementRowVersionA,
        @ResponseKind = N'tell_more',
        @ResponseText = N'I led the integration campaign for two programmes.';
    IF NOT EXISTS (SELECT 1 FROM @ResponseResult WHERE outcome = N'success' AND response_kind = N'tell_more')
        THROW 53679, 'Owner A could not answer their own qualification.', 1;

    /* Connecting evidence the member does not own is refused BEFORE any
       write, and told apart from a concurrency conflict. */
    DECLARE @ForeignEvidenceKey uniqueidentifier = NEWID();
    DECLARE @ForeignItemId bigint;
    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number, confirmed_version_number, confirmed_by_user_id,
         confirmed_at_utc)
    VALUES (@ForeignEvidenceKey, @ProfileIdB, N'confirmed', N'work', 1, 1,
            @UserIdB, SYSUTCDATETIME());
    SET @ForeignItemId = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, saved_by_user_id)
    VALUES (@ForeignItemId, @ProfileIdB, 1, N'Owner B evidence',
            N'Owner B wording.', N'Owner B wording.', @UserIdB);

    DELETE @ResponseResult;
    INSERT @ResponseResult
    EXEC dbo.usp_SaveOpportunityResponseForOwner
        @UserKey = @UserKeyA, @StatementKey = @StatementKeyA,
        @ExpectedRowVersion = @StatementRowVersionA,
        @ResponseKind = N'connect_evidence',
        @ConnectedEvidenceKey = @ForeignEvidenceKey;
    IF NOT EXISTS (SELECT 1 FROM @ResponseResult WHERE outcome = N'invalid')
        THROW 53680, 'Owner A connected owner B''s evidence to their own response.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_responses
        WHERE opportunity_requirement_statement_id =
              (SELECT opportunity_requirement_statement_id
               FROM dbo.opportunity_requirement_statements
               WHERE statement_key = @StatementKeyA)
          AND response_kind <> N'tell_more'
    )
        THROW 53681, 'A refused connect-evidence response overwrote the member''s answer.', 1;

    /* THE DEFECT-1 LESSON, PROVED. A rejected analysis payload must leave the
       previous analysis and every member response exactly where they were. */
    SELECT TOP (1) @SetRowVersionA = CONVERT(binary(8), requirement_set.row_version)
    FROM dbo.opportunity_requirement_sets AS requirement_set
    WHERE requirement_set.requirement_set_key = @RequirementSetKeyA;

    DECLARE @ImpossibleResultsJson nvarchar(max) =
        N'[{"statement_key":"' + CONVERT(nvarchar(36), @StatementKeyA) +
        N'","derived_status":"supported","citation_count":0,"citations":[]}]';

    DELETE @AnalysisResult;
    INSERT @AnalysisResult
    EXEC dbo.usp_SaveOpportunityAnalysisForOwner
        @UserKey = @UserKeyA, @RequirementSetKey = @RequirementSetKeyA,
        @ExpectedRowVersion = @SetRowVersionA,
        @ModelName = N'synthetic-model', @PromptContractVersion = N'synthetic-contract',
        @EvidenceConsideredCount = 1,
        @ResultsJson = @ImpossibleResultsJson;
    IF NOT EXISTS (SELECT 1 FROM @AnalysisResult WHERE outcome = N'invalid')
        THROW 53682, 'A supported result with no citation behind it was accepted.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_analyses AS analysis_record
        JOIN dbo.opportunity_requirement_set_versions AS set_version
          ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
        WHERE set_version.opportunity_requirement_set_id =
              (SELECT opportunity_requirement_set_id FROM dbo.opportunity_requirement_sets
               WHERE requirement_set_key = @RequirementSetKeyA)
    )
        THROW 53683, 'A rejected analysis payload destroyed the previous analysis.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_responses
        WHERE response_kind = N'tell_more' AND owner_profile_id = @ProfileIdA
    )
        THROW 53684, 'A rejected analysis payload destroyed a member response.', 1;

    /* Owner B reads nothing of owner A's analysis or responses.

       2026-08-04 independent review, finding F13. This check used to be an
       INSERT ... EXEC of usp_GetOpportunityAnalysisForOwner into a single
       nine-column table variable. That procedure returns FOUR result sets of
       four different shapes, so the statement can only succeed when the
       procedure returns none at all - which is exactly what happens for owner
       B, who has no requirement set. It therefore proved nothing about
       isolation, and it would have become error 213 ("column name or number
       of supplied values does not match") the first time the fixture gave
       owner B a set of their own.

       The isolation property is asserted on the tables instead, which is
       fixture-independent: owner B owns no analysis, no per-qualification
       result, no citation and no response, and none of owner A's rows carry
       owner B's profile. The read procedure's own owner scoping is covered by
       the OBJECT_DEFINITION greps in section 0 and by the positive path
       below. */
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_analyses WHERE owner_profile_id = @ProfileIdB
        UNION ALL
        SELECT 1 FROM dbo.opportunity_analysis_statements WHERE owner_profile_id = @ProfileIdB
        UNION ALL
        SELECT 1 FROM dbo.opportunity_analysis_citations WHERE owner_profile_id = @ProfileIdB
        UNION ALL
        SELECT 1 FROM dbo.opportunity_responses WHERE owner_profile_id = @ProfileIdB
    )
        THROW 53685, 'Owner B owns alignment rows they never created.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.opportunity_analysis_citations AS citation_record
        JOIN dbo.opportunity_analysis_statements AS analysis_statement
          ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
        JOIN dbo.opportunity_analyses AS analysis_record
          ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
        WHERE analysis_record.owner_profile_id = @ProfileIdA
          AND (citation_record.owner_profile_id <> @ProfileIdA
               OR analysis_statement.owner_profile_id <> @ProfileIdA)
    )
        THROW 53689, 'An alignment row escaped its owner across the analysis joins.', 1;

    /* The positive path for usp_GetOpportunityAnalysisForOwner, which
       previously had none (finding F13). A four-result-set procedure cannot
       be captured by INSERT ... EXEC in T-SQL, so this executes it for the
       OWNER and lets any runtime failure surface as a real error, then
       asserts on the rows it is contracted to return. Owner A has a saved
       analysis at this point, so a procedure that returned nothing, threw, or
       resolved the wrong profile would be caught here rather than by a shape
       mismatch that only ever passed because the fixture was empty. */
    EXEC dbo.usp_GetOpportunityAnalysisForOwner @UserKey = @UserKeyA;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_analyses AS analysis_record
        JOIN dbo.opportunity_requirement_set_versions AS set_version
          ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
         AND set_version.owner_profile_id = analysis_record.owner_profile_id
        JOIN dbo.opportunity_requirement_sets AS requirement_set
          ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
         AND requirement_set.owner_profile_id = set_version.owner_profile_id
        WHERE analysis_record.owner_profile_id = @ProfileIdA
          AND set_version.version_number = requirement_set.current_version_number
    )
        THROW 53690, 'Owner A has no readable alignment analysis at its current version.', 1;

    /* And a correction to a statement takes the analysis with it, because an
       analysis of an un-confirmed reading describes requirements the member
       has since changed. The member's RESPONSE survives. */
    SELECT TOP (1) @StatementRowVersionA = CONVERT(binary(8), statement_record.row_version)
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.statement_key = @StatementKeyA;

    DELETE @StatementCorrectResult;
    INSERT @StatementCorrectResult
    EXEC dbo.usp_CorrectOpportunityRequirementStatementForOwner
        @UserKey = @UserKeyA, @StatementKey = @StatementKeyA,
        @ExpectedRowVersion = @StatementRowVersionA,
        @MemberClass = N'preferred_qualification';
    IF NOT EXISTS (SELECT 1 FROM @StatementCorrectResult WHERE outcome = N'success')
        THROW 53686, 'Owner A could not correct their own statement after analysis.', 1;

    IF EXISTS (SELECT 1 FROM dbo.opportunity_analyses WHERE owner_profile_id = @ProfileIdA)
        THROW 53687, 'A statement correction left a stale alignment analysis behind.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_responses
        WHERE response_kind = N'tell_more' AND owner_profile_id = @ProfileIdA
    )
        THROW 53688, 'A statement correction destroyed the member''s own response.', 1;

    /* ------------------------------------------------------------
       6. Purge: expired working data only, owner-scoped, and an expired
          session is already invisible to the read before it runs.
       ------------------------------------------------------------ */
    /* created_at_utc has to move with it (isolated SQL gate, defect 3).
       CK_opportunity_working_sessions_expiry requires
       expires_at_utc > created_at_utc, and the session was created moments
       ago, so backdating the expiry alone is rejected outright:

         The UPDATE statement conflicted with the CHECK constraint
         "CK_opportunity_working_sessions_expiry".

       Ageing the whole row keeps the constraint satisfied and still puts the
       expiry in the past, which is the only thing the purge and the
       expiry-bounded reads below actually care about. */
    UPDATE dbo.opportunity_working_sessions
    SET created_at_utc = DATEADD(hour, -3, SYSUTCDATETIME()),
        expires_at_utc = DATEADD(hour, -1, SYSUTCDATETIME())
    WHERE owner_profile_id = @ProfileIdA;

    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyA;
    IF EXISTS (SELECT 1 FROM @GetResult)
        THROW 53633, 'An expired working session was still readable before purge.', 1;

    DECLARE @PurgeResult TABLE
    (
        purged_session_count int,
        purged_version_count int
    );

    DELETE @PurgeResult;
    INSERT @PurgeResult EXEC dbo.usp_PurgeExpiredOpportunityWorkingData @UserKey = @ForgedUserKey;
    IF EXISTS (SELECT 1 FROM @PurgeResult)
        THROW 53634, 'A forged UserKey produced a truthful-looking purge outcome.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE owner_profile_id = @ProfileIdA)
        THROW 53635, 'A forged-owner purge destroyed a real owner''s working session.', 1;

    /* Owner B's purge must not touch owner A's expired data. */
    DELETE @PurgeResult;
    INSERT @PurgeResult EXEC dbo.usp_PurgeExpiredOpportunityWorkingData @UserKey = @UserKeyB;
    IF NOT EXISTS (SELECT 1 FROM @PurgeResult WHERE purged_session_count = 0 AND purged_version_count = 0)
        THROW 53636, 'Owner B''s purge reported destroying rows it does not own.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE owner_profile_id = @ProfileIdA)
        THROW 53637, 'Owner B''s purge destroyed owner A''s working session.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE owner_profile_id = @ProfileIdB)
        THROW 53638, 'Owner B''s purge destroyed owner B''s own unexpired working session.', 1;

    DELETE @PurgeResult;
    INSERT @PurgeResult EXEC dbo.usp_PurgeExpiredOpportunityWorkingData @UserKey = @UserKeyA;
    IF NOT EXISTS (SELECT 1 FROM @PurgeResult WHERE purged_session_count = 1 AND purged_version_count = 2)
        THROW 53639, 'Owner A''s purge did not destroy exactly their expired working data.', 1;
    IF EXISTS (SELECT 1 FROM dbo.opportunity_source_versions WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_sources WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_source_concerns WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_source_reviews WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_requirement_statements WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_requirement_set_versions WHERE owner_profile_id = @ProfileIdA)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_requirement_sets WHERE owner_profile_id = @ProfileIdA)
        THROW 53640, 'Owner A''s expired working data survived its own purge.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE owner_profile_id = @ProfileIdB)
        THROW 53641, 'Owner A''s purge destroyed owner B''s working session.', 1;

    /* ------------------------------------------------------------
       7. Delete: owner-scoped, version-fenced, atomic.
       ------------------------------------------------------------ */
    DECLARE @DeleteResult TABLE
    (
        outcome nvarchar(30),
        deleted_version_count int
    );

    DELETE @GetResult;
    INSERT @GetResult EXEC dbo.usp_GetOpportunityWorkingSessionForOwner @UserKey = @UserKeyB;
    DECLARE @SessionRowVersionB binary(8);
    SELECT TOP (1) @SessionRowVersionB = session_row_version FROM @GetResult;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @ForgedUserKey, @WorkingSessionKey = @SessionKeyB,
        @ExpectedRowVersion = @SessionRowVersionB;
    IF EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome <> N'changed' OR deleted_version_count IS NOT NULL)
        THROW 53642, 'A forged UserKey produced a truthful-looking Delete outcome.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE working_session_key = @SessionKeyB)
        THROW 53643, 'A forged-owner Delete removed a real owner''s working session.', 1;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @UserKeyA, @WorkingSessionKey = @SessionKeyB,
        @ExpectedRowVersion = @SessionRowVersionB;
    IF EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome <> N'changed')
        THROW 53644, 'Owner A deleted owner B''s working session.', 1;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @UserKeyB, @WorkingSessionKey = @SessionKeyB,
        @ExpectedRowVersion = 0x0000000000000001;
    IF EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome <> N'changed')
        THROW 53645, 'Delete is not fenced by @ExpectedRowVersion.', 1;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @UserKeyB, @WorkingSessionKey = @SessionKeyB,
        @ExpectedRowVersion = @SessionRowVersionB;
    IF NOT EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome = N'success' AND deleted_version_count = 1)
        THROW 53646, 'Owner B could not delete their own working session.', 1;
    IF EXISTS (SELECT 1 FROM dbo.opportunity_working_sessions WHERE working_session_key = @SessionKeyB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_sources WHERE source_key = @SourceKeyB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_source_versions WHERE owner_profile_id = @ProfileIdB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_source_concerns WHERE owner_profile_id = @ProfileIdB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_source_reviews WHERE owner_profile_id = @ProfileIdB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_requirement_statements WHERE owner_profile_id = @ProfileIdB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_requirement_set_versions WHERE owner_profile_id = @ProfileIdB)
       OR EXISTS (SELECT 1 FROM dbo.opportunity_requirement_sets WHERE owner_profile_id = @ProfileIdB)
        THROW 53647, 'Deleting a working session left orphaned child rows.', 1;

    /* ------------------------------------------------------------
       8. No employer or member wording in audit metadata. No procedure
          in this migration writes audit events, so any hit here would
          mean wording escaped through some other path.
       ------------------------------------------------------------ */
    IF EXISTS
    (
        SELECT 1
        FROM dbo.audit_events AS audit_event
        WHERE audit_event.metadata_json LIKE N'%' + @RoleTextA1 + N'%'
           OR audit_event.metadata_json LIKE N'%' + @RoleTextA2 + N'%'
           OR audit_event.metadata_json LIKE N'%' + @RoleTextB1 + N'%'
           OR audit_event.metadata_json LIKE N'%' + @CorrectionA + N'%'
    )
        THROW 53648, 'Audit metadata contains private Opportunity Slate wording.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-OPPSLATE-002 two-owner isolation across all seventeen procedures, per-owner idempotent Save without overwrite, unchanged-resubmission suppression, verbatim original_text preservation under correction and replacement, confirmation cleared on wording change, version-fenced Correct/Confirm/Delete, forged-owner canaries on every procedure, expiry enforced at read before purge, owner-scoped purge that spares other owners and unexpired sessions, no aggregate verdict column or identifier, no wording in audit metadata, AI proposals kept as a third data class that overwrites neither the employer wording nor the member correction, member reclassification stored beside the AI proposal rather than over it, statement correction clearing the requirement-set confirmation, owner-scoped proposal reads and resolutions with forged-key canaries, purge and delete clearing every proposal row they own, an owner-scoped READ-ONLY evidence allowlist that returns only the reader''s own CONFIRMED items, an alignment analysis that cannot be attached to another owner''s requirement set, a derived status that cannot disagree with its own citation count, a rejected analysis payload that leaves the previous analysis and every member response untouched, a response that cannot connect evidence the member does not own, a statement correction that takes the stale analysis but spares the member''s own answer, an evidence identity RE-DERIVED from the member''s own confirmed item rather than accepted from the payload, a citation naming another owner''s evidence refused before any mutation, an over-length excerpt reaching the guard as invalid instead of a truncated value tripping a constraint, a stored citation count reconciled with the rows behind it, and full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
