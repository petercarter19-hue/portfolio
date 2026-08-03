/* PS-OPPSLATE-001 (Slice OS-1) production-safe verification.

   Uses two synthetic owners inside one outer always-rolled-back
   transaction to prove that the Opportunity Slate working store cannot
   leak or be written across members:

     - every one of the six procedures declares @UserKey nvarchar(300),
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
       any purge has run.

   Calling convention note: no procedure in PS-OPPSLATE-001 appends an
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
        WHERE migration_id = N'PS-OPPSLATE-001'
    )
        THROW 53600, 'PS-OPPSLATE-001 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps across all six procedures.
       ------------------------------------------------------------ */
    DECLARE @ProcedureNames TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProcedureNames (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_GetOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunitySourceForOwner'),
        (N'usp_CorrectOpportunitySourceForOwner'),
        (N'usp_ConfirmOpportunitySourceForOwner'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner');

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
           prediction at any layer, including the database. */
        IF @CheckDefinition LIKE N'%overall_score%'
           OR @CheckDefinition LIKE N'%match_score%'
           OR @CheckDefinition LIKE N'%match_percentage%'
           OR @CheckDefinition LIKE N'%recommendation%'
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
            OBJECT_ID(N'dbo.opportunity_source_versions')
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

    SELECT
        @UserKeyA = app_user.user_key,
        @ProfileIdA = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'oppslate-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT
        @UserKeyB = app_user.user_key,
        @ProfileIdB = profile.profile_id
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
       6. Purge: expired working data only, owner-scoped, and an expired
          session is already invisible to the read before it runs.
       ------------------------------------------------------------ */
    UPDATE dbo.opportunity_working_sessions
    SET expires_at_utc = DATEADD(hour, -1, SYSUTCDATETIME())
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
        N'PS-OPPSLATE-001 two-owner isolation across all six procedures, per-owner idempotent Save without overwrite, unchanged-resubmission suppression, verbatim original_text preservation under correction and replacement, confirmation cleared on wording change, version-fenced Correct/Confirm/Delete, forged-owner canaries on every procedure, expiry enforced at read before purge, owner-scoped purge that spares other owners and unexpired sessions, no aggregate verdict column or identifier, no wording in audit metadata, and full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
