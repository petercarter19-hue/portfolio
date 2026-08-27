/* PS-OPPSLATE-USE-001 (Workshop D saved-slate use disclosure read)
   production-safe verification. Uses three synthetic owners inside one outer
   always-rolled-back transaction to prove:

     1. usp_GetOpportunitySlateUseForOwner resolves @UserKey -> @ProfileId
        itself, never accepts @OwnerProfileId, re-asserts owner_profile_id,
        and filters evidence_kind = N'knowledge_item' (the F6-coupled
        predicate).
     2. The supporting index IX_opportunity_saved_evidence_owner_use exists
        on dbo.opportunity_saved_evidence.
     3. A cited item returns exactly one aggregate row with the correct
        citing_version_count across ALL saved versions, the correct
        latest_save_version_number/latest_saved_at_utc, and a truthful
        cites_latest_saved_version bit — including an item cited ONLY by an
        older saved version (count 1, bit 0), proving any-version scope.
     4. Zero-row neutrality: a foreign owner's key, a forged @UserKey, an
        unknown key, an owner with no slate, and a key cited only with
        evidence_kind = N'moment' all return zero rows, indistinguishable
        from one another — the read never confirms or denies existence.
     5. Cross-owner isolation both directions: neither owner's read ever
        reflects the other's saved slate.
     6. A citation of a since-DELETED knowledge item still reports: the
        procedure reads the member's saved snapshot, not the library, so a
        dangling reference remains a named use.
     7. The result carries counts, a version number, and a timestamp only —
        the result-set shape has no text columns to leak bodies, excerpts,
        or employer wording.

   Owners A and B have saved slates; owner C is deliberately left with no
   slate so the no-slate neutrality claim is exercised rather than inferred.
   Seeding writes the saved-slate chain directly (the established idiom:
   PS-OPPSLATE-003's verifier writes synthetic knowledge_items directly,
   PS-OPPSLATE-004's verifier builds the saved child-row shape directly for
   its second owner) because this verification proves the new READ, not the
   already-proven save procedure. Every synthetic row is rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-OPPSLATE-USE-001')
        THROW 56201, 'PS-OPPSLATE-USE-001 is not registered.', 1;

    /* ------------------------------------------------------------
       0. OBJECT_DEFINITION greps and the index.
       ------------------------------------------------------------ */
    DECLARE @UseDefinition nvarchar(max) =
        OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetOpportunitySlateUseForOwner', N'P'));
    IF @UseDefinition IS NULL
        THROW 56202, 'usp_GetOpportunitySlateUseForOwner does not exist.', 1;
    IF @UseDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
       OR @UseDefinition LIKE N'%@OwnerProfileId%'
       OR @UseDefinition NOT LIKE N'%owner_profile_id = @ProfileId%'
        THROW 56203, 'usp_GetOpportunitySlateUseForOwner is not owner-resolving or leaks a forbidden identifier.', 1;
    IF @UseDefinition NOT LIKE N'%evidence_kind = N''knowledge_item''%'
        THROW 56204, 'usp_GetOpportunitySlateUseForOwner does not filter evidence_kind (F6 coupling).', 1;
    IF @UseDefinition LIKE N'%INSERT %' OR @UseDefinition LIKE N'%UPDATE %'
       OR @UseDefinition LIKE N'%DELETE %'
        THROW 56205, 'usp_GetOpportunitySlateUseForOwner is not read-only.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE name = N'IX_opportunity_saved_evidence_owner_use'
          AND object_id = OBJECT_ID(N'dbo.opportunity_saved_evidence', N'U')
    )
        THROW 56206, 'IX_opportunity_saved_evidence_owner_use is missing.', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners; C deliberately receives no slate.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:oppslate-use-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'oppslate-use-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'oppslate-use-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'oppslate-use-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-use-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectA,
        @DisplayName = N'Slate use verification owner A';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-use-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectB,
        @DisplayName = N'Slate use verification owner B';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'oppslate-use-verification',
        @AuthIssuer = @Issuer, @AuthSubject = @SubjectC,
        @DisplayName = N'Slate use verification owner C with no slate';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @UserKeyC nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    DECLARE @ProfileIdC bigint;
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;

    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id, @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'oppslate-use-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'oppslate-use-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_record ON identity_record.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_record.provider = N'oppslate-use-verification'
      AND identity_record.issuer = @Issuer
      AND identity_record.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @UserKeyA = @UserKeyB OR @UserKeyA = @UserKeyC OR @UserKeyB = @UserKeyC
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdA = @ProfileIdC OR @ProfileIdB = @ProfileIdC
        THROW 56207, 'Synthetic slate-use owners were not provisioned.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Seed. Owner A: one knowledge item cited in BOTH saved
          versions (@EvidenceKeyA), one cited ONLY in the older
          version (@OldOnlyKeyA), one moment-kind citation
          (@MomentKeyA), and a knowledge item that is never cited
          (@UncitedKeyA). Owner B: one item cited in their own one
          saved version (@EvidenceKeyB) — MUST NOT ENTER OWNER A
          RESULT.
       ------------------------------------------------------------ */
    DECLARE @EvidenceKeyA uniqueidentifier = NEWID();
    DECLARE @OldOnlyKeyA uniqueidentifier = NEWID();
    DECLARE @MomentKeyA uniqueidentifier = NEWID();
    DECLARE @UncitedKeyA uniqueidentifier = NEWID();
    DECLARE @EvidenceKeyB uniqueidentifier = NEWID();
    DECLARE @UnknownKey uniqueidentifier = NEWID();

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
        (@KnowledgeItemIdA, @ProfileIdA, 1, N'Synthetic cited item',
         N'Led the verification-readiness programme.',
         N'Led the verification-readiness programme.', @UserIdA);

    /* Owner A's slate with two saved versions; v1 is ten minutes older. */
    DECLARE @SlateIdA bigint;
    INSERT dbo.opportunity_slates (owner_profile_id, current_save_version_number)
    VALUES (@ProfileIdA, 2);
    SET @SlateIdA = SCOPE_IDENTITY();

    DECLARE @SavedAtV1 datetime2(7) = DATEADD(minute, -10, SYSUTCDATETIME());
    DECLARE @SavedAtV2 datetime2(7) = SYSUTCDATETIME();

    DECLARE @ResultIdA1 bigint;
    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number,
         source_version_number, requirement_version_number, saved_analysis_key,
         source_text, model_name, prompt_contract_version,
         evidence_considered_count, qualification_count, input_fingerprint,
         idempotency_key, saved_by_user_id, saved_at_utc)
    VALUES
        (@SlateIdA, @ProfileIdA, 1, 1, 1, NEWID(),
         N'Synthetic employer wording v1.', N'synthetic-model', N'synthetic-contract',
         1, 1, REPLICATE(N'a', 64),
         CONCAT(N'oppslate-use-a1-', @Suffix), @UserIdA, @SavedAtV1);
    SET @ResultIdA1 = SCOPE_IDENTITY();

    DECLARE @QualIdA1 bigint;
    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal,
         statement_class, employer_text, derived_status, citation_count)
    VALUES
        (@ResultIdA1, @ProfileIdA, 1, N'required_qualification',
         N'Synthetic requirement v1.', N'supported', 2);
    SET @QualIdA1 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal,
         clause_ordinal, covered_text, evidence_kind, evidence_key,
         evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdA1, @ProfileIdA, 1, 1, N'a synthetic clause',
         N'knowledge_item', @EvidenceKeyA, 1, N'Synthetic cited item',
         N'Led the verification-readiness programme.'),
        (@QualIdA1, @ProfileIdA, 2, 1, N'an older-version-only clause',
         N'knowledge_item', @OldOnlyKeyA, 1, N'Older-version-only item',
         N'Ran the archived initiative.');

    DECLARE @ResultIdA2 bigint;
    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number,
         source_version_number, requirement_version_number, saved_analysis_key,
         source_text, model_name, prompt_contract_version,
         evidence_considered_count, qualification_count, input_fingerprint,
         idempotency_key, saved_by_user_id, saved_at_utc)
    VALUES
        (@SlateIdA, @ProfileIdA, 2, 2, 1, NEWID(),
         N'Synthetic employer wording v2.', N'synthetic-model', N'synthetic-contract',
         1, 1, REPLICATE(N'b', 64),
         CONCAT(N'oppslate-use-a2-', @Suffix), @UserIdA, @SavedAtV2);
    SET @ResultIdA2 = SCOPE_IDENTITY();

    DECLARE @QualIdA2 bigint;
    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal,
         statement_class, employer_text, derived_status, citation_count)
    VALUES
        (@ResultIdA2, @ProfileIdA, 1, N'required_qualification',
         N'Synthetic requirement v2.', N'supported', 2);
    SET @QualIdA2 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal,
         clause_ordinal, covered_text, evidence_kind, evidence_key,
         evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdA2, @ProfileIdA, 1, 1, N'a synthetic clause again',
         N'knowledge_item', @EvidenceKeyA, 1, N'Synthetic cited item',
         N'Led the verification-readiness programme.'),
        (@QualIdA2, @ProfileIdA, 2, 1, N'a moment-kind clause',
         N'moment', @MomentKeyA, 1, N'A synthetic moment',
         N'A timestamped event excerpt.');

    /* Owner B's slate: one saved version citing owner B's own item. */
    DECLARE @SlateIdB bigint;
    INSERT dbo.opportunity_slates (owner_profile_id, current_save_version_number)
    VALUES (@ProfileIdB, 1);
    SET @SlateIdB = SCOPE_IDENTITY();

    DECLARE @ResultIdB1 bigint;
    INSERT dbo.opportunity_saved_results
        (opportunity_slate_id, owner_profile_id, save_version_number,
         source_version_number, requirement_version_number, saved_analysis_key,
         source_text, model_name, prompt_contract_version,
         evidence_considered_count, qualification_count, input_fingerprint,
         idempotency_key, saved_by_user_id, saved_at_utc)
    VALUES
        (@SlateIdB, @ProfileIdB, 1, 1, 1, NEWID(),
         N'SYNTHETIC OPPSLATE B WORDING - MUST NOT ENTER OWNER A RESULT',
         N'synthetic-model', N'synthetic-contract',
         1, 1, REPLICATE(N'c', 64),
         CONCAT(N'oppslate-use-b1-', @Suffix), @UserIdB, SYSUTCDATETIME());
    SET @ResultIdB1 = SCOPE_IDENTITY();

    DECLARE @QualIdB1 bigint;
    INSERT dbo.opportunity_saved_qualifications
        (opportunity_saved_result_id, owner_profile_id, ordinal,
         statement_class, employer_text, derived_status, citation_count)
    VALUES
        (@ResultIdB1, @ProfileIdB, 1, N'required_qualification',
         N'Synthetic requirement B.', N'supported', 1);
    SET @QualIdB1 = SCOPE_IDENTITY();

    INSERT dbo.opportunity_saved_evidence
        (opportunity_saved_qualification_id, owner_profile_id, ordinal,
         clause_ordinal, covered_text, evidence_kind, evidence_key,
         evidence_version, evidence_title, excerpt)
    VALUES
        (@QualIdB1, @ProfileIdB, 1, 1, N'owner B clause',
         N'knowledge_item', @EvidenceKeyB, 1, N'Owner B cited item',
         N'Ran the supplier quality review programme.');

    /* ------------------------------------------------------------
       3. The read. One aggregate row when cited; zero otherwise.
       ------------------------------------------------------------ */
    DECLARE @UseResult TABLE
    (
        citing_version_count int,
        latest_saved_at_utc datetime2(7),
        latest_save_version_number int,
        cites_latest_saved_version bit
    );

    /* Cited in both versions: count 2, latest 2, bit 1. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @EvidenceKeyA;
    IF (SELECT COUNT(*) FROM @UseResult) <> 1
        THROW 56208, 'A cited item did not return exactly one aggregate row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @UseResult
        WHERE citing_version_count = 2
          AND latest_save_version_number = 2
          AND cites_latest_saved_version = 1
          AND latest_saved_at_utc = @SavedAtV2
    )
        THROW 56209, 'The cited-in-both-versions aggregates are wrong.', 1;

    /* Cited ONLY by the older version: count 1, latest 1, bit 0 — the
       any-version scope, not latest-only. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @OldOnlyKeyA;
    IF NOT EXISTS
    (
        SELECT 1 FROM @UseResult
        WHERE citing_version_count = 1
          AND latest_save_version_number = 1
          AND cites_latest_saved_version = 0
          AND latest_saved_at_utc = @SavedAtV1
    )
        THROW 56210, 'An item cited only by an older saved version was not truthfully reported.', 1;

    /* A moment-kind citation must NOT report as knowledge-item use. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @MomentKeyA;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56211, 'A moment-kind citation leaked through the knowledge_item filter.', 1;

    /* Owner A probing owner B's key: zero rows, no existence signal. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @EvidenceKeyB;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56212, 'Owner A''s read reflected owner B''s saved slate.', 1;

    /* Owner B probing owner A's key: zero rows. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyB, @KnowledgeItemKey = @EvidenceKeyA;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56213, 'Owner B''s read reflected owner A''s saved slate.', 1;

    /* Owner B reading their own citation. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyB, @KnowledgeItemKey = @EvidenceKeyB;
    IF NOT EXISTS
    (
        SELECT 1 FROM @UseResult
        WHERE citing_version_count = 1 AND cites_latest_saved_version = 1
    )
        THROW 56214, 'Owner B could not read their own citation state.', 1;

    /* Owner C is a real active owner with deliberately no opportunity_slates
       row. Their read is the same zero-row shape as uncited, unknown,
       foreign, and forged inputs. */
    IF EXISTS
    (
        SELECT 1 FROM dbo.opportunity_slates
        WHERE owner_profile_id = @ProfileIdC
    )
        THROW 56219, 'The no-slate owner unexpectedly has a slate row.', 1;
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyC, @KnowledgeItemKey = @EvidenceKeyA;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56220, 'An owner with no slate returned a use row.', 1;

    /* Forged key, unknown key, uncited key: all zero rows, all identical
       in shape. */
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @ForgedUserKey, @KnowledgeItemKey = @EvidenceKeyA;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56215, 'A forged UserKey returned a use row.', 1;

    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @UnknownKey;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56216, 'An unknown key returned a use row.', 1;

    INSERT dbo.knowledge_items
        (knowledge_item_key, owner_profile_id, item_status, classification,
         current_version_number)
    VALUES (@UncitedKeyA, @ProfileIdA, N'unfinished', N'work', 1);
    DECLARE @UncitedItemIdA bigint = SCOPE_IDENTITY();
    INSERT dbo.knowledge_item_versions
        (knowledge_item_id, owner_profile_id, version_number, title,
         approved_wording, original_member_wording, saved_by_user_id)
    VALUES (@UncitedItemIdA, @ProfileIdA, 1, N'Uncited item',
            N'Uncited wording.', N'Uncited wording.', @UserIdA);
    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @UncitedKeyA;
    IF EXISTS (SELECT 1 FROM @UseResult)
        THROW 56217, 'An uncited knowledge item returned a use row.', 1;

    /* ------------------------------------------------------------
       4. A deleted item's citation still reports: the snapshot is the
          truth source, not the library.
       ------------------------------------------------------------ */
    DELETE dbo.knowledge_item_versions WHERE knowledge_item_id = @KnowledgeItemIdA;
    DELETE dbo.knowledge_items WHERE knowledge_item_id = @KnowledgeItemIdA;

    DELETE @UseResult;
    INSERT @UseResult
    EXEC dbo.usp_GetOpportunitySlateUseForOwner
        @UserKey = @UserKeyA, @KnowledgeItemKey = @EvidenceKeyA;
    IF NOT EXISTS
    (
        SELECT 1 FROM @UseResult
        WHERE citing_version_count = 2 AND cites_latest_saved_version = 1
    )
        THROW 56218, 'A deleted item''s saved-slate citation stopped reporting.', 1;

    ROLLBACK TRANSACTION;
    SELECT CAST(1 AS bit) AS verified;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
