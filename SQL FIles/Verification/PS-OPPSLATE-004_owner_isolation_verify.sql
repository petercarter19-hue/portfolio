/* PS-OPPSLATE-004 (Opportunity Slate replacement R1) production-safe
   verification.

   Uses two synthetic owners inside one outer always-rolled-back transaction
   to prove:

     - every procedure PS-OPPSLATE-004 adds declares @UserKey nvarchar(300),
       resolves it to @ProfileId itself, filters owner_profile_id =
       @ProfileId, and never accepts a caller-supplied @OwnerProfileId --
       the same generic grep PS-OPPSLATE-001/002/003 apply to their own
       procedures, re-run here across the full accumulated set so a future
       migration cannot narrow it by omission;
     - no table this migration touches carries a forbidden aggregate
       verdict column;
     - usp_SaveOpportunitySourceIdentityForOwner is fenced by the SAME
       opportunity_sources.row_version token usp_CorrectOpportunitySourceFor-
       Owner already uses, is idempotent-safe (a second save updates the
       one identity row for that source version rather than creating a
       second one), and neither a forged @UserKey nor a cross-owner
       @SourceKey ever reads or writes another owner's identity;
     - usp_GetOpportunitySourceIdentityForOwner returns nothing for a
       version with no saved identity, and never returns another owner's
       row;
     - saving an identity never touches original_text, original_sha256, or
       the source's confirmation triple -- identity is member metadata, not
       employer wording (architecture section 6.1);
     - the takeover of usp_PurgeExpiredOpportunityWorkingData and
       usp_DeleteOpportunityWorkingSessionForOwner actually reaches the
       three new v2 child tables: an owner's expired-and-purged (or
       explicitly deleted) working data leaves no opportunity_source_
       identities, opportunity_requirement_review_events, or opportunity_
       member_takes row behind, while a second owner's unexpired,
       undeleted data of the same three shapes is dynamically proved to
       remain completely untouched during each operation;
     - both taken-over procedure bodies literally contain the three new
       DELETE blocks (a textual proof the takeover is not a no-op re-stamp);
     - no employer or member wording, and no employer/role-title identity
       value, ever reaches dbo.audit_events.

   Calling convention note: no procedure PS-OPPSLATE-004 adds appends an
   audit event, matching PS-OPPSLATE-001/002/003's own procedures, so no
   INSERT ... EXEC nesting restriction applies here.

   Every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-OPPSLATE-004')
        THROW 53880, 'PS-OPPSLATE-004 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps across the full accumulated set of
          twenty-two Opportunity Slate procedures.
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
        (N'usp_SaveOpportunityResponseForOwner'),
        (N'usp_GetOpportunitySavedSlateForOwner'),
        (N'usp_SaveOpportunitySlateForOwner'),
        (N'usp_DeleteOpportunitySavedSlateForOwner'),
        (N'usp_SaveOpportunitySourceIdentityForOwner'),
        (N'usp_GetOpportunitySourceIdentityForOwner');

    DECLARE @CheckName sysname;
    DECLARE @CheckDefinition nvarchar(max);
    WHILE EXISTS (SELECT 1 FROM @ProcedureNames)
    BEGIN
        SELECT TOP (1) @CheckName = procedure_name
        FROM @ProcedureNames
        ORDER BY procedure_name;

        IF OBJECT_ID(N'dbo.' + @CheckName, N'P') IS NULL
            THROW 53881, 'A required Opportunity Slate procedure is missing.', 1;

        SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @CheckName, N'P'));

        IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
            THROW 53882, 'An Opportunity Slate procedure does not declare @UserKey nvarchar(300).', 1;
        IF @CheckDefinition LIKE N'%@OwnerProfileId%'
            THROW 53883, 'An Opportunity Slate procedure accepts a caller-supplied @OwnerProfileId.', 1;
        IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
            THROW 53884, 'An Opportunity Slate procedure does not resolve @UserKey itself.', 1;
        IF @CheckDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
            THROW 53885, 'An Opportunity Slate procedure does not filter on owner_profile_id = @ProfileId.', 1;

        DELETE @ProcedureNames WHERE procedure_name = @CheckName;
    END;

    /* The two taken-over procedures must literally contain the new DELETE
       blocks -- a textual proof the CREATE OR ALTER is not a no-op
       re-stamp of the OS-3 body. */
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_PurgeExpiredOpportunityWorkingData', N'P'))
           NOT LIKE N'%opportunity_source_identities%'
       OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_PurgeExpiredOpportunityWorkingData', N'P'))
           NOT LIKE N'%opportunity_requirement_review_events%'
       OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_PurgeExpiredOpportunityWorkingData', N'P'))
           NOT LIKE N'%opportunity_member_takes%'
        THROW 53886, 'The purge takeover does not reach all three new v2 tables.', 1;
    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_DeleteOpportunityWorkingSessionForOwner', N'P'))
           NOT LIKE N'%opportunity_source_identities%'
       OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_DeleteOpportunityWorkingSessionForOwner', N'P'))
           NOT LIKE N'%opportunity_requirement_review_events%'
       OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_DeleteOpportunityWorkingSessionForOwner', N'P'))
           NOT LIKE N'%opportunity_member_takes%'
        THROW 53887, 'The delete takeover does not reach all three new v2 tables.', 1;

    /* ------------------------------------------------------------
       0b. No table this migration touches carries a forbidden aggregate
           verdict column (handoff section 1's standing product rule).
       ------------------------------------------------------------ */
    IF EXISTS
    (
        SELECT 1
        FROM sys.columns AS column_record
        JOIN sys.tables AS table_record ON table_record.object_id = column_record.object_id
        WHERE table_record.name IN
        (
            N'opportunity_source_identities',
            N'opportunity_requirement_review_events',
            N'opportunity_member_takes',
            N'opportunity_analyses',
            N'opportunity_requirement_sets'
        )
        AND
        (
               column_record.name LIKE N'%score%'
            OR column_record.name LIKE N'%rating%'
            OR column_record.name LIKE N'%ranking%'
            OR column_record.name LIKE N'%percentile%'
            OR column_record.name LIKE N'%percentage%'
            OR column_record.name LIKE N'%fit\_index%' ESCAPE N'\'
            OR column_record.name LIKE N'%confidence%'
            OR column_record.name LIKE N'%likelihood%'
            OR column_record.name LIKE N'%probability%'
            OR column_record.name LIKE N'%recommend%'
            OR column_record.name LIKE N'%verdict%'
        )
    )
        THROW 53888, 'An Opportunity Slate table carries a forbidden aggregate verdict column.', 1;

    /* ------------------------------------------------------------
       1. Two synthetic owners via a throwaway auth provider.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:oppslate-v2-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'oppslate-v2-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'oppslate-v2-b-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-v2-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'Opportunity Slate v2 verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-v2-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'Opportunity Slate v2 verification owner B';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;

    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id, @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'oppslate-v2-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'oppslate-v2-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL
       OR @UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB
        THROW 53889, 'Synthetic Opportunity Slate v2 owners were not provisioned.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Owner A brings a source and confirms it (unchanged OS-1
          procedures), then saves and reads back their source identity.
       ------------------------------------------------------------ */
    DECLARE @SaveResult TABLE
    (
        outcome nvarchar(30), working_session_key uniqueidentifier,
        source_key uniqueidentifier, version_number int,
        workbench_state nvarchar(40), session_row_version binary(8),
        source_row_version binary(8)
    );
    DECLARE @RoleTextA nvarchar(max) = CONCAT(N'Owner A employer role wording ', @Suffix);
    DECLARE @RoleTextB nvarchar(max) = N'SYNTHETIC OPPSLATE V2 B ROLE WORDING - MUST NOT LEAK TO OWNER A';
    DECLARE @ResponseTextA nvarchar(max) = N'Owner A verification response text';
    DECLARE @ResponseTextB nvarchar(max) = N'Owner B verification response text';
    DECLARE @IdempotencyKeyA nvarchar(200) = CONCAT(N'oppslate-v2-key-a-', @Suffix);
    DECLARE @IdempotencyKeyB nvarchar(200) = CONCAT(N'oppslate-v2-key-b-', @Suffix);

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyA, @IdempotencyKey = @IdempotencyKeyA,
        @SourceText = @RoleTextA, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'success')
        THROW 53890, 'Owner A could not create a working session.', 1;

    DECLARE @SourceKeyA uniqueidentifier;
    DECLARE @SourceRowVersionA binary(8);
    SELECT TOP (1) @SourceKeyA = source_key, @SourceRowVersionA = source_row_version FROM @SaveResult;

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyB, @IdempotencyKey = @IdempotencyKeyB,
        @SourceText = @RoleTextB, @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'success')
        THROW 53891, 'Owner B could not create a working session.', 1;

    DECLARE @SourceKeyB uniqueidentifier;
    DECLARE @SourceRowVersionB binary(8);
    SELECT TOP (1) @SourceKeyB = source_key, @SourceRowVersionB = source_row_version FROM @SaveResult;

    DECLARE @IdentityResult TABLE (outcome nvarchar(30), source_row_version binary(8));

    /* A forged @UserKey never writes a truthful-looking identity outcome. */
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @ForgedUserKey, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @SourceRowVersionA,
        @EmployerName = N'Forged Employer', @RoleTitle = N'Forged Role';
    IF EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome <> N'changed')
        THROW 53892, 'A forged UserKey produced a truthful-looking identity save outcome.', 1;

    /* Owner B may not save identity against owner A's source. */
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @SourceRowVersionA,
        @EmployerName = N'Cross Owner Employer', @RoleTitle = N'Cross Owner Role';
    IF EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome <> N'changed')
        THROW 53893, 'Owner B saved identity against owner A''s source.', 1;

    /* A stale @ExpectedRowVersion is refused with the same neutral outcome. */
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @ExpectedRowVersion = 0x0000000000000001,
        @EmployerName = N'Stale Token Employer', @RoleTitle = N'Stale Token Role';
    IF EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome <> N'changed')
        THROW 53894, 'Identity save is not fenced by @ExpectedRowVersion.', 1;

    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_identities
        WHERE owner_profile_id = @ProfileIdA
    )
        THROW 53895, 'A refused identity save left a row behind.', 1;

    /* Owner A's own save succeeds. */
    DECLARE @EmployerNameA nvarchar(200) = CONCAT(N'Meridian Verification ', @Suffix);
    DECLARE @RoleTitleA nvarchar(200) = N'Senior Systems Verification Manager';
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @SourceRowVersionA,
        @EmployerName = @EmployerNameA, @RoleTitle = @RoleTitleA;
    IF NOT EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome = N'success')
        THROW 53896, 'Owner A could not save their own source identity.', 1;

    DECLARE @IdentityRowVersionA binary(8) =
        (SELECT TOP (1) source_row_version FROM @IdentityResult WHERE outcome = N'success');
    IF @IdentityRowVersionA IS NULL OR @IdentityRowVersionA = @SourceRowVersionA
        THROW 53897, 'Identity save did not advance its shared source concurrency token.', 1;

    /* Reusing the pre-save token is now stale and must be refused. */
    DECLARE @EmployerNameA2 nvarchar(200) = CONCAT(N'Meridian Verification Revised ', @Suffix);
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @SourceRowVersionA,
        @EmployerName = @EmployerNameA2, @RoleTitle = @RoleTitleA;
    IF NOT EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome = N'changed')
        THROW 53898, 'A stale second identity save was not refused.', 1;

    /* The fresh token upserts the SAME row rather than creating a second
       one, and the source's confirmation/original wording stay untouched. */
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @IdentityRowVersionA,
        @EmployerName = @EmployerNameA2, @RoleTitle = @RoleTitleA;
    IF NOT EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome = N'success')
        THROW 53899, 'Owner A could not update their own source identity with the fresh token.', 1;
    SELECT TOP (1) @SourceRowVersionA = source_row_version
    FROM @IdentityResult
    WHERE outcome = N'success';
    IF (SELECT COUNT(*) FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdA) <> 1
        THROW 53930, 'A repeated identity save created a second row instead of updating.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.opportunity_source_versions
        WHERE owner_profile_id = @ProfileIdA AND original_text = @RoleTextA
          AND member_corrected_text IS NULL
    )
        THROW 53931, 'Saving identity altered the write-once employer wording.', 1;
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_sources
        WHERE owner_profile_id = @ProfileIdA AND confirmed_version_number IS NOT NULL
    )
        THROW 53932, 'Saving identity confirmed a source the member never confirmed.', 1;

    /* ------------------------------------------------------------
       3. Read isolation on the new Get procedure.
       ------------------------------------------------------------ */
    DECLARE @IdentityReadResult TABLE
    (
        employer_name nvarchar(200), role_title nvarchar(200), source_type nvarchar(30)
    );

    DELETE @IdentityReadResult;
    INSERT @IdentityReadResult
    EXEC dbo.usp_GetOpportunitySourceIdentityForOwner @UserKey = @UserKeyA, @SourceKey = @SourceKeyA;
    IF NOT EXISTS (SELECT 1 FROM @IdentityReadResult WHERE employer_name = @EmployerNameA2 AND role_title = @RoleTitleA)
        THROW 53933, 'Owner A could not read back their own saved identity.', 1;

    DELETE @IdentityReadResult;
    INSERT @IdentityReadResult
    EXEC dbo.usp_GetOpportunitySourceIdentityForOwner @UserKey = @UserKeyB, @SourceKey = @SourceKeyA;
    IF EXISTS (SELECT 1 FROM @IdentityReadResult)
        THROW 53902, 'Owner B''s read returned owner A''s source identity.', 1;

    DELETE @IdentityReadResult;
    INSERT @IdentityReadResult
    EXEC dbo.usp_GetOpportunitySourceIdentityForOwner @UserKey = @ForgedUserKey, @SourceKey = @SourceKeyA;
    IF EXISTS (SELECT 1 FROM @IdentityReadResult)
        THROW 53903, 'A forged UserKey returned a source identity row.', 1;

    /* Owner B has confirmed no identity of their own yet: the honest
       empty-placeholder state (architecture section 4.2). */
    DELETE @IdentityReadResult;
    INSERT @IdentityReadResult
    EXEC dbo.usp_GetOpportunitySourceIdentityForOwner @UserKey = @UserKeyB, @SourceKey = @SourceKeyB;
    IF EXISTS (SELECT 1 FROM @IdentityReadResult)
        THROW 53904, 'An owner with no saved identity yet received a row.', 1;

    /* Give owner B the same child-row shape used by the later purge and
       explicit-delete isolation checks. The identity write advances the
       shared source token, so confirmation must use the returned token. */
    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyB, @ExpectedRowVersion = @SourceRowVersionB,
        @EmployerName = N'Owner B Verification Employer', @RoleTitle = N'Owner B Verification Role';
    IF NOT EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome = N'success')
        THROW 53934, 'Owner B could not create the identity row required by the isolation checks.', 1;
    SELECT TOP (1) @SourceRowVersionB = source_row_version
    FROM @IdentityResult
    WHERE outcome = N'success';

    /* ------------------------------------------------------------
       4. Confirm both sources, propose one requirement statement each
          (the unchanged OS-2 procedure), and attach synthetic v2 child
          rows directly -- there is no R1 procedure that writes these two
          tables yet (by design; see the forward migration's header) so
          this verification proves their SHAPE and the takeover cascade
          the same way an R2 caller eventually will.
       ------------------------------------------------------------ */
    DECLARE @ConfirmResult TABLE (outcome nvarchar(30), source_row_version binary(8), confirmed_version_number int);

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @SourceRowVersionA;
    IF NOT EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome = N'success')
        THROW 53905, 'Owner A could not confirm their own source.', 1;
    SELECT TOP (1) @SourceRowVersionA = source_row_version FROM @ConfirmResult;

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyB, @ExpectedRowVersion = @SourceRowVersionB;
    IF NOT EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome = N'success')
        THROW 53906, 'Owner B could not confirm their own source.', 1;
    SELECT TOP (1) @SourceRowVersionB = source_row_version FROM @ConfirmResult;

    DECLARE @ProposalResult TABLE
    (
        outcome nvarchar(30), requirement_set_key uniqueidentifier,
        version_number int, statement_count int
    );
    DECLARE @StatementsJson nvarchar(max) = N'[{"ordinal":1,"span_start":0,"span_length":10,'
        + N'"employer_text":"Verification requirement text",'
        + N'"proposed_class":"required_qualification",'
        + N'"proposed_explanation":"Verification explanation",'
        + N'"proposed_structure_json":"{}"}]';

    DELETE @ProposalResult;
    INSERT @ProposalResult
    EXEC dbo.usp_SaveOpportunityRequirementProposalForOwner
        @UserKey = @UserKeyA, @SourceKey = @SourceKeyA, @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'verification-model', @PromptContractVersion = N'verification-1',
        @StatementsJson = @StatementsJson;
    IF NOT EXISTS (SELECT 1 FROM @ProposalResult WHERE outcome = N'success')
        THROW 53907, 'Owner A could not propose a requirement statement.', 1;

    DELETE @ProposalResult;
    INSERT @ProposalResult
    EXEC dbo.usp_SaveOpportunityRequirementProposalForOwner
        @UserKey = @UserKeyB, @SourceKey = @SourceKeyB, @ExpectedRowVersion = @SourceRowVersionB,
        @ModelName = N'verification-model', @PromptContractVersion = N'verification-1',
        @StatementsJson = @StatementsJson;
    IF NOT EXISTS (SELECT 1 FROM @ProposalResult WHERE outcome = N'success')
        THROW 53908, 'Owner B could not propose a requirement statement.', 1;

    DECLARE @StatementIdA bigint;
    DECLARE @StatementIdB bigint;
    SELECT TOP (1) @StatementIdA = statement_record.opportunity_requirement_statement_id
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.owner_profile_id = @ProfileIdA;
    SELECT TOP (1) @StatementIdB = statement_record.opportunity_requirement_statement_id
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.owner_profile_id = @ProfileIdB;
    IF @StatementIdA IS NULL OR @StatementIdB IS NULL
        THROW 53909, 'A synthetic requirement statement was not created for both owners.', 1;

    INSERT dbo.opportunity_requirement_review_events
        (opportunity_requirement_statement_id, owner_profile_id, event_ordinal,
         review_decision, decided_by_user_id)
    VALUES
        (@StatementIdA, @ProfileIdA, 1, N'accurate', @UserIdA),
        (@StatementIdB, @ProfileIdB, 1, N'accurate', @UserIdB);

    INSERT dbo.opportunity_member_takes
        (opportunity_requirement_statement_id, owner_profile_id, take, response_text,
         authored_via, response_reviewed_at_utc, created_by_user_id)
    VALUES
        (@StatementIdA, @ProfileIdA, N'done_this', @ResponseTextA,
         N'typed', SYSUTCDATETIME(), @UserIdA),
        (@StatementIdB, @ProfileIdB, N'done_related', @ResponseTextB,
         N'typed', SYSUTCDATETIME(), @UserIdB);

    /* ------------------------------------------------------------
       5. Purge takeover: expire owner A's working session and prove the
          purge removes all three new v2 rows for owner A while owner B's
          (unexpired) rows of the same three shapes survive untouched.
       ------------------------------------------------------------ */
    UPDATE dbo.opportunity_working_sessions
    SET created_at_utc = DATEADD(HOUR, -3, SYSUTCDATETIME()),
        expires_at_utc = DATEADD(HOUR, -1, SYSUTCDATETIME())
    WHERE owner_profile_id = @ProfileIdA;

    EXEC dbo.usp_PurgeExpiredOpportunityWorkingData @UserKey = @UserKeyA, @IncludeCounts = 0;

    IF EXISTS (SELECT 1 FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdA)
        THROW 53910, 'The purge takeover left a source identity row behind for its own owner.', 1;
    IF EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events WHERE owner_profile_id = @ProfileIdA)
        THROW 53911, 'The purge takeover left a requirement review event behind for its own owner.', 1;
    IF EXISTS (SELECT 1 FROM dbo.opportunity_member_takes WHERE owner_profile_id = @ProfileIdA)
        THROW 53912, 'The purge takeover left a member take behind for its own owner.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdB)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events WHERE owner_profile_id = @ProfileIdB)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_member_takes WHERE owner_profile_id = @ProfileIdB)
        THROW 53913, 'Owner A''s purge removed owner B''s unexpired v2 rows.', 1;

    /* Recreate a complete unexpired owner A working-data shape after A's
       purge. It must survive owner B's legitimate explicit delete below;
       otherwise that delete has reached across its owner boundary. */
    DECLARE @RoleTextADeleteSurvivor nvarchar(max) =
        CONCAT(N'Owner A explicit-delete survivor wording ', @Suffix);
    DECLARE @ResponseTextADeleteSurvivor nvarchar(max) =
        N'Owner A explicit-delete survivor response text';
    DECLARE @EmployerNameADeleteSurvivor nvarchar(200) =
        CONCAT(N'Owner A Delete Survivor Employer ', @Suffix);
    DECLARE @RoleTitleADeleteSurvivor nvarchar(200) =
        N'Owner A Delete Survivor Role';
    DECLARE @IdempotencyKeyADeleteSurvivor nvarchar(200) =
        CONCAT(N'oppslate-v2-key-a-delete-survivor-', @Suffix);

    DELETE @SaveResult;
    INSERT @SaveResult
    EXEC dbo.usp_SaveOpportunitySourceForOwner
        @UserKey = @UserKeyA,
        @IdempotencyKey = @IdempotencyKeyADeleteSurvivor,
        @SourceText = @RoleTextADeleteSurvivor,
        @CaptureMethod = N'pasted';
    IF NOT EXISTS (SELECT 1 FROM @SaveResult WHERE outcome = N'success')
        THROW 53935, 'Owner A could not recreate working data for the explicit-delete survivor check.', 1;
    SELECT TOP (1)
        @SourceKeyA = source_key,
        @SourceRowVersionA = source_row_version
    FROM @SaveResult
    WHERE outcome = N'success';

    DELETE @IdentityResult;
    INSERT @IdentityResult
    EXEC dbo.usp_SaveOpportunitySourceIdentityForOwner
        @UserKey = @UserKeyA,
        @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @EmployerName = @EmployerNameADeleteSurvivor,
        @RoleTitle = @RoleTitleADeleteSurvivor;
    IF NOT EXISTS (SELECT 1 FROM @IdentityResult WHERE outcome = N'success')
        THROW 53936, 'Owner A could not create the identity row for the explicit-delete survivor check.', 1;
    SELECT TOP (1) @SourceRowVersionA = source_row_version
    FROM @IdentityResult
    WHERE outcome = N'success';

    DELETE @ConfirmResult;
    INSERT @ConfirmResult
    EXEC dbo.usp_ConfirmOpportunitySourceForOwner
        @UserKey = @UserKeyA,
        @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA;
    IF NOT EXISTS (SELECT 1 FROM @ConfirmResult WHERE outcome = N'success')
        THROW 53937, 'Owner A could not confirm the source for the explicit-delete survivor check.', 1;
    SELECT TOP (1) @SourceRowVersionA = source_row_version
    FROM @ConfirmResult
    WHERE outcome = N'success';

    DELETE @ProposalResult;
    INSERT @ProposalResult
    EXEC dbo.usp_SaveOpportunityRequirementProposalForOwner
        @UserKey = @UserKeyA,
        @SourceKey = @SourceKeyA,
        @ExpectedRowVersion = @SourceRowVersionA,
        @ModelName = N'verification-model',
        @PromptContractVersion = N'verification-1',
        @StatementsJson = @StatementsJson;
    IF NOT EXISTS (SELECT 1 FROM @ProposalResult WHERE outcome = N'success')
        THROW 53938, 'Owner A could not recreate a requirement for the explicit-delete survivor check.', 1;

    SET @StatementIdA = NULL;
    SELECT TOP (1) @StatementIdA = statement_record.opportunity_requirement_statement_id
    FROM dbo.opportunity_requirement_statements AS statement_record
    WHERE statement_record.owner_profile_id = @ProfileIdA;
    IF @StatementIdA IS NULL
        THROW 53939, 'Owner A has no requirement statement for the explicit-delete survivor check.', 1;

    INSERT dbo.opportunity_requirement_review_events
        (opportunity_requirement_statement_id, owner_profile_id, event_ordinal,
         review_decision, decided_by_user_id)
    VALUES
        (@StatementIdA, @ProfileIdA, 1, N'accurate', @UserIdA);

    INSERT dbo.opportunity_member_takes
        (opportunity_requirement_statement_id, owner_profile_id, take, response_text,
         authored_via, response_reviewed_at_utc, created_by_user_id)
    VALUES
        (@StatementIdA, @ProfileIdA, N'done_this', @ResponseTextADeleteSurvivor,
         N'typed', SYSUTCDATETIME(), @UserIdA);

    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdA)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events WHERE owner_profile_id = @ProfileIdA)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_member_takes WHERE owner_profile_id = @ProfileIdA)
        THROW 53940, 'Owner A explicit-delete survivor rows were not fully established.', 1;

    /* ------------------------------------------------------------
       6. Delete takeover: owner B explicitly deletes their own working
       session and the same three new tables are fully cleared for
       owner B, atomically, while owner A's newly recreated rows survive.
       ------------------------------------------------------------ */
    DECLARE @WorkingSessionKeyB uniqueidentifier;
    DECLARE @SessionRowVersionB binary(8);
    SELECT @WorkingSessionKeyB = working_session_key, @SessionRowVersionB = CONVERT(binary(8), row_version)
    FROM dbo.opportunity_working_sessions
    WHERE owner_profile_id = @ProfileIdB;

    DECLARE @DeleteResult TABLE (outcome nvarchar(30), deleted_version_count int);

    /* A forged UserKey and a stale row version must not reach owner B's
       working data before the real delete does. */
    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @ForgedUserKey, @WorkingSessionKey = @WorkingSessionKeyB,
        @ExpectedRowVersion = @SessionRowVersionB;
    IF EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome <> N'changed')
        THROW 53914, 'A forged UserKey produced a truthful-looking delete outcome.', 1;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @UserKeyB,
        @WorkingSessionKey = @WorkingSessionKeyB,
        @ExpectedRowVersion = 0x0000000000000000;
    IF NOT EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome = N'changed')
        THROW 53941, 'A stale row version was not refused before explicit delete.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdB)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events WHERE owner_profile_id = @ProfileIdB)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_member_takes WHERE owner_profile_id = @ProfileIdB)
        THROW 53942, 'A refused explicit delete changed owner B''s v2 rows.', 1;

    DELETE @DeleteResult;
    INSERT @DeleteResult
    EXEC dbo.usp_DeleteOpportunityWorkingSessionForOwner
        @UserKey = @UserKeyB, @WorkingSessionKey = @WorkingSessionKeyB, @ExpectedRowVersion = @SessionRowVersionB;
    IF NOT EXISTS (SELECT 1 FROM @DeleteResult WHERE outcome = N'success')
        THROW 53915, 'Owner B could not delete their own working session.', 1;

    IF EXISTS (SELECT 1 FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdB)
        THROW 53916, 'The delete takeover left a source identity row behind.', 1;
    IF EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events WHERE owner_profile_id = @ProfileIdB)
        THROW 53917, 'The delete takeover left a requirement review event behind.', 1;
    IF EXISTS (SELECT 1 FROM dbo.opportunity_member_takes WHERE owner_profile_id = @ProfileIdB)
        THROW 53918, 'The delete takeover left a member take behind.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.opportunity_source_identities WHERE owner_profile_id = @ProfileIdA)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_requirement_review_events WHERE owner_profile_id = @ProfileIdA)
       OR NOT EXISTS (SELECT 1 FROM dbo.opportunity_member_takes WHERE owner_profile_id = @ProfileIdA)
        THROW 53943, 'Owner B''s explicit delete removed owner A''s undeleted v2 rows.', 1;

    /* ------------------------------------------------------------
       7. No employer wording, member response text, or identity value in
          audit metadata. Neither procedure PS-OPPSLATE-004 adds nor either
          takeover writes an audit event; any hit means wording escaped
          through some other path.
       ------------------------------------------------------------ */
    IF EXISTS
    (
        SELECT 1 FROM dbo.audit_events AS audit_event
        WHERE audit_event.metadata_json LIKE N'%' + @RoleTextA + N'%'
           OR audit_event.metadata_json LIKE N'%' + @RoleTextB + N'%'
           OR audit_event.metadata_json LIKE N'%' + @RoleTextADeleteSurvivor + N'%'
           OR audit_event.metadata_json LIKE N'%' + @ResponseTextA + N'%'
           OR audit_event.metadata_json LIKE N'%' + @ResponseTextB + N'%'
           OR audit_event.metadata_json LIKE N'%' + @ResponseTextADeleteSurvivor + N'%'
           OR audit_event.metadata_json LIKE N'%' + @EmployerNameA2 + N'%'
           OR audit_event.metadata_json LIKE N'%' + @EmployerNameADeleteSurvivor + N'%'
           OR audit_event.metadata_json LIKE N'%' + @RoleTitleA + N'%'
           OR audit_event.metadata_json LIKE N'%' + @RoleTitleADeleteSurvivor + N'%'
    )
        THROW 53919, 'Audit metadata contains private Opportunity Slate v2 wording.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-OPPSLATE-004: full accumulated procedure-shape grep across all twenty-two Opportunity Slate procedures; no forbidden aggregate verdict column on any new or altered table; identity save fenced by the existing opportunity_sources.row_version token with forged-key and cross-owner canaries and a stale-token refusal; a repeated save upserts one row per source version rather than duplicating; identity save never touches write-once employer wording or the confirmation triple; identity read is owner-scoped with a forged-key canary and an honest empty result for an owner with nothing saved; the takeover of the purge and explicit-delete procedures textually contains and functionally reaches all three new v2 child tables, removing only the acting owner''s rows while a second owner''s equivalent rows dynamically survive each operation; forged-key and stale-token explicit deletes are refused without changing the target owner''s rows; no employer, response, or identity wording in audit metadata; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
